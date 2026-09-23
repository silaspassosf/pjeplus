import re
import logging
from typing import Any

from Fix.core import safe_click_no_scroll, safe_click, preencher_campo, esperar_elemento
from Fix.browser_suporte import abrir_em_nova_aba
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix import espera

logger = logging.getLogger(__name__)


def mov_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 15) -> bool:
    try:
        obs_lower = (observacao or '').lower()
        numero_match = re.search(r'\bsob\s+(\d+)', obs_lower)
        if not numero_match:
            numero_match = re.search(r'\bxs\s+(\d+)', obs_lower)
        if not numero_match:
            logger.warning("[SOBRESTAMENTO] #%s: numero de prazo nao encontrado na observacao: %s", numero_processo, observacao)
            return False

        prazo_meses = numero_match.group(1)

        url_atual = getattr(driver, 'current_url', '') or ''
        if '/aguardandofinal' not in url_atual:
            btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=max(2, timeout // 3))
            if not btn_abrir_tarefa:
                candidates = espera.elementos(driver, 'button[mattooltip*="tarefa"], button[aria-label*="tarefa"], button[title*="tarefa"]', teto=2)
                for c in candidates:
                    try:
                        if getattr(c, 'is_displayed', lambda: True)() and getattr(c, 'is_enabled', lambda: True)():
                            btn_abrir_tarefa = c
                            break
                    except Exception:
                        continue

            if not btn_abrir_tarefa:
                try:
                    from Fix.selectors_pje import buscar_seletor_robusto as buscar_robusto
                    btn_abrir_tarefa = buscar_robusto(driver, [
                        "Abre a tarefa do processo",
                        "Abrir tarefa do processo",
                        "Abrir tarefa",
                        "Abrir a tarefa do processo"
                    ], timeout=3, log=debug)
                except Exception:
                    btn_abrir_tarefa = None

            if not btn_abrir_tarefa:
                logger.warning("[SOBRESTAMENTO] #%s: botao 'Abrir tarefa' nao encontrado", numero_processo)
                return False

            tarefa_texto = (getattr(btn_abrir_tarefa, 'text', '') or '').strip().lower()
            if 'aguardando prazo' in tarefa_texto:
                return True

            nova_aba = abrir_em_nova_aba(driver, lambda: safe_click(driver, btn_abrir_tarefa), timeout=timeout)
            if nova_aba:
                driver.switch_to.window(nova_aba)

        espera.assentar(driver, 0.8)

        url_ok = False
        current = ''
        for _ in range(24):
            try:
                current = (driver.current_url or '')
            except Exception:
                current = ''
            if '/sobrestamento/aguardandofinal' in current:
                url_ok = True
                break
            espera.assentar(driver, 0.3)
        if not url_ok:
            return True

        btn_calendario = espera.elemento(driver, 'button[mattooltip="Definir prazo para este motivo de sobrestamento"]', teto=timeout)
        if not btn_calendario:
            btn_calendario = espera.elemento(driver, 'i.fas.fa-calendar-alt', teto=5)
            if btn_calendario:
                safe_click_no_scroll(driver, btn_calendario, log=False)
            else:
                logger.warning("[SOBRESTAMENTO] #%s: botao de calendario nao encontrado", numero_processo)
                return False
        else:
            try:
                btn_calendario.click()
            except Exception:
                safe_click_no_scroll(driver, btn_calendario)

        if not espera.ate_aparecer(driver, 'pje-dialog-prazo-sobrestamento', teto=timeout):
            logger.warning("[SOBRESTAMENTO] #%s: modal de prazo nao apareceu", numero_processo)
            return False

        if not espera.ate_habilitar(driver, "input[formcontrolname='mesesPrazoControl']", teto=timeout):
            logger.warning("[SOBRESTAMENTO] #%s: campo de prazo nao habilitou", numero_processo)
            return False

        if not preencher_campo(driver, "input[formcontrolname='mesesPrazoControl']", prazo_meses, log=debug):
            logger.warning("[SOBRESTAMENTO] #%s: falha ao preencher prazo", numero_processo)
            return False

        campo_prazo = espera.elemento(driver, "input[formcontrolname='mesesPrazoControl']", teto=2)
        valor_no_campo = (getattr(campo_prazo, 'get_attribute', lambda a: '')('value') or '').strip() if campo_prazo else ''
        if valor_no_campo and str(prazo_meses) not in valor_no_campo:
            logger.warning("[SOBRESTAMENTO] #%s: valor no campo '%s' diferente do esperado '%s'", numero_processo, valor_no_campo, prazo_meses)
            return False

        espera.pausa(driver, 0.5, 'prazo do sobrestamento preenchido')

        btn_prosseguir = espera.elemento(driver, "//pje-dialog-prazo-sobrestamento//button[.//span[contains(text(), 'Prosseguir')] or contains(., 'Prosseguir')]", teto=timeout)
        if not btn_prosseguir:
            logger.warning("[SOBRESTAMENTO] #%s: botao 'Prosseguir' nao encontrado", numero_processo)
            return False

        try:
            btn_prosseguir.click()
        except Exception:
            safe_click_no_scroll(driver, btn_prosseguir)

        for _ in range(20):
            try:
                for barra in espera.elementos(driver, 'snack-bar-container.success, simple-snack-bar', teto=0.1):
                    txt = (getattr(barra, 'text', '') or '').strip().lower()
                    if 'falha ao tentar registrar' in txt or 'erro ao persistir' in txt:
                        logger.error("[SOBRESTAMENTO] #%s: PJe recusou registro do prazo: %s", numero_processo, txt)
                        return False
                    if 'com sucesso' in txt or 'sucesso' in txt or 'registrado' in txt:
                        btn_fecha = espera.elemento(driver, 'snack-bar-container button', teto=0.5)
                        if btn_fecha:
                            try:
                                safe_click_no_scroll(driver, btn_fecha)
                            except Exception:
                                pass
                        return True
            except Exception:
                pass

            try:
                modais = espera.elementos(driver, 'pje-dialog-prazo-sobrestamento', teto=0.1)
                if not modais or not any(getattr(m, 'is_displayed', lambda: False)() for m in modais):
                    return True
            except Exception:
                pass

            espera.pausa(driver, 0.3, 'aguardando confirmacao')

        return True

    except Exception as e:
        logger.error("[SOBRESTAMENTO] #%s: erro geral: %s", numero_processo, e)
        return False

