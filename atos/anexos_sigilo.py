from typing import Any, Optional
import logging
from Fix.core import safe_click_no_scroll
from Fix import espera

logger = logging.getLogger(__name__)


def inserir_sigilo_individual(elemento: Any, driver: Any = None, debug: bool = False) -> bool:
    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    def _tem_sigilo() -> bool:
        try:
            if hasattr(elemento, 'query_selector'):
                return elemento.query_selector('i.tl-sigiloso, a.is-sigiloso') is not None
            cls = (getattr(elemento, 'get_attribute', lambda a: '')('class') or '')
            return 'is-sigiloso' in cls or 'tl-sigiloso' in cls
        except Exception:
            return False

    try:
        if _tem_sigilo():
            return True

        btn_sigilo = None
        for seletor in [
            'button[name="Inserir sigilo"]',
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
        ]:
            try:
                if hasattr(elemento, 'query_selector'):
                    candidato = elemento.query_selector(seletor)
                    if candidato:
                        btn_sigilo = candidato
                        break
            except Exception:
                continue

        if not btn_sigilo:
            logger.warning('[SIGILO_INSERIR] Botao de sigilo nao encontrado')
            return False

        safe_click_no_scroll(driver, btn_sigilo)

        for _ in range(8):
            espera.assentar(driver, 0.25)
            if _tem_sigilo():
                return True

        logger.warning('[SIGILO_INSERIR] Clique executado, mas sigilo nao foi detectado')
        return False
    except Exception as e:
        logger.warning('[SIGILO_INSERIR] Erro geral: %s', e)
        return False


def visibilidade_sigilosos_lote_apenas(driver: Any, polo: str = 'ativo', log: bool = False) -> bool:
    try:
        sel_vis = 'button[mattooltip="Visibilidade para Sigilo"]'
        if not espera.ate_habilitar(driver, sel_vis, teto=5):
            logger.warning('[VISIBILIDADE_LOTE] Botao de visibilidade nao habilitou')
            return False

        btn_vis = espera.elemento(driver, sel_vis, teto=2)
        if not btn_vis:
            return False
        safe_click_no_scroll(driver, btn_vis)

        modal_container = '.cdk-overlay-container .mat-dialog-container'
        modal = espera.elemento(driver, modal_container, teto=4, visivel=False)
        if modal:
            espera.elemento(driver, f'{modal_container} tr.cdk-drag', teto=5, visivel=False)

        seletor_marcar = 'button[aria-label="Marcar todas"], i.fa.fa-check.botao-icone-titulo-coluna'
        if not espera.ate_habilitar(driver, seletor_marcar, teto=5):
            logger.warning('[VISIBILIDADE_LOTE] Botao Marcar todas nao habilitou')
            return False

        icone_header = espera.elemento(driver, seletor_marcar, teto=2)
        if not icone_header:
            return False
        safe_click_no_scroll(driver, icone_header)

        xpath_salvar = '//button[.//span[contains(text(),"Salvar")]]'
        if not espera.ate_habilitar(driver, xpath_salvar, teto=10):
            logger.warning('[VISIBILIDADE_LOTE] Botao Salvar nao habilitou')
            return False

        btn_salvar = espera.elemento(driver, xpath_salvar, teto=2)
        if not btn_salvar:
            return False
        safe_click_no_scroll(driver, btn_salvar)

        return True
    except Exception as e:
        logger.warning('[VISIBILIDADE_LOTE][ERRO] Falha ao aplicar visibilidade em lote: %s', e)
        return False
