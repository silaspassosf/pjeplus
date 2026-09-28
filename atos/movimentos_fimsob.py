from typing import Any
import logging
from Fix import espera
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.core import safe_click, safe_click_no_scroll
from Fix.browser_suporte import abrir_em_nova_aba, forcar_fechamento_abas_extras

logger = logging.getLogger(__name__)


def mov_fimsob(driver: Any, debug: bool = False, timeout: int = 15) -> bool:
    try:
        url_atual = getattr(driver, 'current_url', '') or ''
        tarefa_aberta = False
        aba_detalhe = None

        if '/aguardandofinal' not in url_atual:
            aba_detalhe = getattr(driver, 'current_window_handle', None)
            btn_abrir_tarefa = espera.elemento(driver, BTN_TAREFA_PROCESSO, teto=timeout)
            if not btn_abrir_tarefa:
                return False

            nova_aba = abrir_em_nova_aba(driver, lambda: safe_click(driver, btn_abrir_tarefa), timeout=timeout)
            if nova_aba:
                driver.switch_to.window(nova_aba)
                if not espera.ate_url(driver, '/aguardandofinal', teto=6):
                    return False
                tarefa_aberta = True
            else:
                if not espera.ate_url(driver, '/aguardandofinal', teto=3):
                    return False

        btn_encerrar = espera.elemento(
            driver,
            'button[mattooltip="Encerrar sobrestamento"][aria-label="Encerrar todos os motivos de sobrestamento"]',
            teto=timeout
        )
        if not btn_encerrar:
            btn_encerrar = espera.elemento(
                driver,
                '//button[contains(.//div[@class="texto-botao-skinny"], "Encerrar sobrestamento")]',
                teto=timeout
            )
        if not btn_encerrar:
            return False

        safe_click_no_scroll(driver, btn_encerrar)
        espera.ate_aparecer(driver, "//span[contains(text(),'Sim')]", teto=timeout)

        btn_sim = espera.elemento(driver, '//button[.//span[contains(text(), "Sim")]]', teto=timeout)
        if not btn_sim:
            btn_sim = espera.elemento(driver, 'button[mat-button][color="primary"] span.mat-button-wrapper', teto=timeout)
        if not btn_sim:
            return False

        safe_click_no_scroll(driver, btn_sim)
        espera.ate_sumir(driver, "//span[contains(text(),'Sim')]", teto=timeout)

        if tarefa_aberta and aba_detalhe:
            try:
                forcar_fechamento_abas_extras(driver, aba_detalhe)
                try:
                    driver.refresh()
                except Exception:
                    pass
            except Exception as e_close:
                logger.warning("[FIMSOB][FECHAR_ABA] falha ao retornar para aba principal: %s", e_close)

        return True
    except Exception as e:
        logger.warning("[FIMSOB][FALHA] erro ao encerrar sobrestamento: %s", e)
        return False
