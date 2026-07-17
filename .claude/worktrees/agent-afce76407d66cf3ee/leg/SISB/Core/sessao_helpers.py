import logging
import time

from .driver import driver_sisbajud
from .login import login_automatico_sisbajud, login_manual_sisbajud

logger = logging.getLogger(__name__)

"""
SISB Core - Helpers de sessao
"""


def _extrair_dados_pje(driver_pje):
    """Helper para extrair dados do processo PJe."""
    try:
        from Fix.extracao import extrair_dados_processo
        processo_dados_extraidos = extrair_dados_processo(driver_pje)
        if processo_dados_extraidos:
            numero_lista = processo_dados_extraidos.get("numero", [])
            _ = numero_lista[0] if numero_lista else "N/A"
            return processo_dados_extraidos
        return None
    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao extrair dados do PJe: {e}')
        return None


def _criar_driver_sisbajud():
    """Helper para criar driver Firefox SISBAJUD."""
    try:
        driver = driver_sisbajud()
        if not driver:
            return None
        return driver
    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao criar driver SISBAJUD: {e}')
        return None


def _realizar_login(driver):
    """Helper para realizar login automatizado no SISBAJUD."""
    try:
        cookie_restored = False
        try:
            from bacen import carregar_cookies_sisbajud
            try:
                if carregar_cookies_sisbajud(driver):
                    return True
            except Exception:
                cookie_restored = False
        except Exception:
            cookie_restored = False

        try:
            from driver_config import criar_driver_sisb, criar_driver_sisb_notebook, salvar_cookies_sessao, salvar_cookies_sisbajud, SALVAR_COOKIES_AUTOMATICO
        except Exception:
            criar_driver_sisb = None
            criar_driver_sisb_notebook = None
            salvar_cookies_sessao = None
            salvar_cookies_sisbajud = None
            SALVAR_COOKIES_AUTOMATICO = False

        if not cookie_restored and salvar_cookies_sisbajud:
            try:
                if salvar_cookies_sisbajud(driver):
                    return True
            except Exception:
                cookie_restored = False

        try:
            if login_automatico_sisbajud(driver):
                try:
                    if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                        salvar_cookies_sisbajud(driver, info_extra='login_automatico_sisbajud')
                except Exception:
                    cookie_restored = True
                return True
            return False
        except Exception as e:
            logger.error(f'[SISBAJUD] Erro no login automatico SISBAJUD: {e}')

        try:
            if login_manual_sisbajud(driver):
                try:
                    if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                        salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                except Exception:
                    pass
                return True
            return False
        except Exception as e:
            logger.error(f'[SISBAJUD] Erro durante login manual SISBAJUD: {e}')

        return False

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro durante login: {e}')
        return False


def _navegar_minuta(driver):
    """Helper para navegar para a pagina /minuta e clicar em Nova Minuta."""
    try:
        minuta_indicator = 'sisbajud.cnj.jus.br/minuta'
        url_timeout = 120
        inicio_url = time.time()
        url_ready = False
        while time.time() - inicio_url < url_timeout:
            try:
                current = driver.current_url.lower()
                if minuta_indicator in current:
                    url_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not url_ready:
            return False

        time.sleep(2)

        try:
            driver.maximize_window()
        except Exception:
            pass

        script = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary');
        }
        if (botaoNova) {
            if (botaoNova.tagName === 'MAT-ICON') {
                botaoNova = botaoNova.closest('button');
            }
            botaoNova.click();
            return true;
        }
        return false;
        """

        sucesso = driver.execute_script(script)
        if sucesso:
            time.sleep(1)
            return True
        return False

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro durante navegacao para minuta: {e}')
        return False