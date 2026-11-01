from typing import Any, List, Optional
import logging
import re
import unicodedata
from Fix import espera
from Fix.core import _executar_js, safe_click_no_scroll
from Fix.selectors_pje import BTN_EXPANDIR_CHIPS, CHIPS_LISTA

logger = logging.getLogger(__name__)


def normalizar_chip_texto(txt: str) -> str:
    """Normaliza texto de chip para comparação:
    - remove acentos / diacríticos
    - converte para minúsculas
    - substitui traços, hifens (inclusive en-dash/em-dash), pontuação por espaço
    - colapsa múltiplos espaços em branco
    """
    if not txt:
        return ""
    s = unicodedata.normalize("NFD", str(txt))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def chip_corresponde_padrao(chip_norm: str, padrao_norm: str) -> bool:
    """Verifica se o chip normalizado contém o padrão normalizado (nomes fixos)."""
    if not chip_norm or not padrao_norm:
        return False
    return padrao_norm in chip_norm


def def_chip(driver: Any, numero_processo: str = '', observacao: str = '', chips_para_remover: Optional[List[str]] = None, debug: bool = False, timeout: int = 10) -> bool:
    chips_removidos = 0

    try:
        if chips_para_remover is None:
            chips_para_remover = ["Prazo vencido", "pós sentença"]

        btn_expandir = espera.elemento(driver, BTN_EXPANDIR_CHIPS, teto=2)
        if btn_expandir:
            safe_click_no_scroll(driver, btn_expandir)
            espera.assentar(driver, 1)

        chip_elements = espera.elementos(driver, CHIPS_LISTA, teto=timeout)
        if not chip_elements:
            chip_elements = espera.elementos(
                driver,
                "pje-lista-etiquetas mat-chip, mat-chip-list mat-chip, .mat-chip",
                teto=2,
            )

        # Coleta os textos brutos de todos os chips na tela para log e análise
        chips_brutos = []
        for el in chip_elements:
            try:
                t = (getattr(el, 'text', '') or '').strip()
                chips_brutos.append(t)
            except Exception:
                chips_brutos.append('<erro leitura>')

        logger.info(
            "[CHIPS] #%s: %d chip(s) na tela: %s",
            numero_processo,
            len(chip_elements),
            chips_brutos,
        )

        padroes_norm = [normalizar_chip_texto(p) for p in chips_para_remover if p]

        itens_a_remover = []
        for idx, chip_element in enumerate(chip_elements):
            try:
                raw_text = chips_brutos[idx] if idx < len(chips_brutos) else (getattr(chip_element, 'text', '') or '').strip()
                chip_norm = normalizar_chip_texto(raw_text)
                if any(chip_corresponde_padrao(chip_norm, pn) for pn in padroes_norm):
                    itens_a_remover.append((chip_element, raw_text))
            except Exception as e_match:
                logger.debug("[CHIPS] Falha ao verificar chip #%d: %s", idx, e_match)
                continue

        if not itens_a_remover:
            logger.info(
                "[CHIPS] #%s: nenhum chip correspondente aos padroes %s (chips na tela: %d)",
                numero_processo,
                chips_para_remover,
                len(chip_elements),
            )
            return True

        for chip_element, raw_text in itens_a_remover:
            try:
                # 1. Tentar encontrar o botão de remoção diretamente no elemento do chip
                btn_remover = None
                seletor_btn = "button[mattooltip*='Remover' i], button[aria-label*='Remover' i], button.etq-botao-excluir, button.mat-chip-remove, mat-icon[mattooltip*='Remover' i], .mat-chip-remove, button"

                if hasattr(chip_element, "_handle") and chip_element._handle:
                    try:
                        h = chip_element._handle.query_selector(seletor_btn)
                        if h:
                            from Play.pjeplay.element import PWElement
                            btn_remover = PWElement(h, getattr(chip_element, "_page", None))
                    except Exception:
                        pass

                if not btn_remover:
                    try:
                        fn_find = getattr(chip_element, "find_element", None)
                        if fn_find:
                            btn_remover = fn_find("css selector", seletor_btn)
                    except Exception:
                        pass

                # Fallback via XPath usando trecho limpo
                if not btn_remover:
                    trecho = raw_text.splitlines()[0].strip() if raw_text else ""
                    if trecho:
                        trecho_limpo = trecho.replace('"', '').replace("'", "")[:20]
                        xpath_fallback = f"{CHIPS_LISTA}[contains(., '{trecho_limpo}')]//button"
                        btn_remover = espera.elemento(driver, xpath_fallback, teto=2)

                if not btn_remover:
                    logger.warning(
                        "[CHIPS][REMOVER] #%s: chip '%s' encontrado, mas o botao de remover nao apareceu",
                        numero_processo,
                        raw_text,
                    )
                    continue

                safe_click_no_scroll(driver, btn_remover)
                espera.assentar(driver, 0.4)

                # Dialogo de confirmacao ("Sim") — padrão exato de movimentos_fimsob (def_sob/PEC):
                # espera o span/botao 'Sim' aparecer, clica e espera sumir.
                sel_sim_txt = "//span[contains(text(),'Sim')] | //button[contains(.,'Sim')]"
                xpath_sim = '//button[.//span[contains(text(), "Sim")]]'

                confirmou = False
                if espera.ate_aparecer(driver, sel_sim_txt, teto=timeout):
                    botao_sim = espera.elemento(driver, xpath_sim, teto=2)
                    if not botao_sim:
                        botao_sim = espera.elemento(
                            driver,
                            '//mat-dialog-container//button[contains(., "Sim")]'
                            ' | //div[contains(@class,"cdk-overlay-pane")]//button[contains(., "Sim")]'
                            ' | //button[contains(., "Sim")]',
                            teto=2,
                        )
                    if not botao_sim:
                        botao_sim = espera.elemento(
                            driver,
                            'button[mat-button][color="primary"] span.mat-button-wrapper',
                            teto=2,
                        )

                    if botao_sim:
                        safe_click_no_scroll(driver, botao_sim)
                        espera.ate_sumir(driver, "//span[contains(text(),'Sim')]", teto=timeout)
                        confirmou = True
                    else:
                        # Fallback JS direto no container do diálogo
                        res_js = _executar_js(driver, """
                            const btn = Array.from(document.querySelectorAll('mat-dialog-container button, .cdk-overlay-pane button, button')).find(b => {
                                const t = (b.textContent || '').trim();
                                return t === 'Sim' || t.startsWith('Sim') || b.querySelector('span')?.textContent?.trim() === 'Sim';
                            });
                            if (btn) { btn.click(); return true; }
                            return false;
                        """)
                        if res_js:
                            espera.ate_sumir(driver, "//span[contains(text(),'Sim')]", teto=timeout)
                            confirmou = True
                        else:
                            logger.warning(
                                "[CHIPS][REMOVER] #%s: botao 'Sim' apareceu mas nao foi localizado (chip '%s')",
                                numero_processo, raw_text,
                            )
                else:
                    logger.warning(
                        "[CHIPS][REMOVER] #%s: dialogo de confirmacao nao apareceu para o chip '%s'",
                        numero_processo, raw_text,
                    )

                if confirmou:
                    espera.assentar(driver, 0.5)
                    chips_removidos += 1
                    logger.info(
                        "[CHIPS][REMOVER] #%s: chip '%s' removido com sucesso",
                        numero_processo,
                        raw_text,
                    )
            except Exception as e:
                logger.warning("[CHIPS][REMOVER] #%s: falha ao remover chip '%s': %s", numero_processo, raw_text, e)
                continue

        return chips_removidos > 0
    except Exception as e:
        logger.warning("[CHIPS][ERRO] #%s: erro geral na remocao de chips: %s", numero_processo, e)
        return False
