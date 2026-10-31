from typing import Any, List, Optional
import logging
from Fix import espera
from Fix.core import safe_click_no_scroll
from Fix.selectors_pje import BTN_EXPANDIR_CHIPS, CHIPS_LISTA

logger = logging.getLogger(__name__)


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
        chips_encontrados = []

        # Os padroes e o texto do chip sao comparados SEM acento e em minusculas.
        # Antes a comparacao era substring crua (`rem_text in chip_text`) e por isso
        # falhava em silencio: o chamador passava "Domicilio Eletronico - Ciencia
        # Automatica" (sem acento) enquanto a tela mostra "Domicílio Eletrônico -
        # Ciência Automática" -> nenhum chip casava, `chips_encontrados` ficava vazio
        # e a funcao retornava True na linha abaixo, como se tivesse removido.
        # A referencia funcional (PEC/regras_execucao.py:757, def_sob) so' funcionava
        # porque passa nomes que existem literalmente na tela ("Prazo vencido").
        from Fix.utils import normalizar_texto

        padroes_norm = [(p, normalizar_texto(p)) for p in chips_para_remover]

        for chip_element in chip_elements:
            try:
                chip_text = (getattr(chip_element, 'text', '') or '').strip()
                chip_norm = normalizar_texto(chip_text)
                if any(pn and pn in chip_norm for _p, pn in padroes_norm):
                    chips_encontrados.append(chip_text)
            except Exception:
                continue

        if not chips_encontrados:
            # Nao havia chip correspondente. Retornar True continua correto (nada a
            # fazer), mas agora fica registrado — antes era indistinguivel de "havia
            # chip e nao reconheci".
            logger.info(
                "[CHIPS] #%s: nenhum chip correspondente aos padroes %s (chips na tela: %d)",
                numero_processo,
                chips_para_remover,
                len(chip_elements),
            )
            return True

        for chip_text in chips_encontrados:
            try:
                # O texto do chip pode conter apostrofo (ex.: "D'AVILA"), o que
                # quebraria o literal do XPath. Escapa ': concat() nao e' necessario
                # aqui — basta o literal com aspas duplas quando houver apostrofo.
                if "'" in chip_text:
                    btn_remover_xpath = (
                        f'{CHIPS_LISTA}[contains(., "{chip_text}")]'
                        "//button[contains(@mattooltip, 'Remover Chip') or contains(@class, 'etq-botao-excluir')]"
                    )
                else:
                    btn_remover_xpath = (
                        f"{CHIPS_LISTA}[contains(., '{chip_text}')]"
                        "//button[contains(@mattooltip, 'Remover Chip') or contains(@class, 'etq-botao-excluir')]"
                    )
                botao_remover = espera.elemento(driver, btn_remover_xpath, teto=3)
                if not botao_remover:
                    logger.warning(
                        "[CHIPS][REMOVER] #%s: chip '%s' encontrado, mas o botao de remover nao apareceu",
                        numero_processo,
                        chip_text,
                    )
                    continue
                safe_click_no_scroll(driver, botao_remover)
                espera.assentar(driver, 1)

                btn_sim_xpath = "//button[.//span[contains(text(), 'Sim')]]"
                if espera.ate_habilitar(driver, btn_sim_xpath, teto=5):
                    botao_sim = espera.elemento(driver, btn_sim_xpath, teto=2)
                    if botao_sim:
                        safe_click_no_scroll(driver, botao_sim)
                        espera.assentar(driver, 2)
                        chips_removidos += 1
                    else:
                        logger.warning(
                            "[CHIPS][REMOVER] #%s: botao 'Sim' habilitou mas nao foi localizado (chip '%s')",
                            numero_processo, chip_text,
                        )
                else:
                    logger.warning(
                        "[CHIPS][REMOVER] #%s: dialogo de confirmacao nao habilitou para o chip '%s'",
                        numero_processo, chip_text,
                    )
            except Exception as e:
                logger.warning("[CHIPS][REMOVER] #%s: falha ao remover chip '%s': %s", numero_processo, chip_text, e)
                continue

        return chips_removidos > 0
    except Exception as e:
        logger.warning("[CHIPS][ERRO] #%s: erro geral na remocao de chips: %s", numero_processo, e)
        return False
