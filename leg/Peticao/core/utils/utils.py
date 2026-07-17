"""
Utils module for Peticao - contains driver and login utilities
"""

import logging
logger = logging.getLogger(__name__)

def configurar_recovery_driver(criar_driver_func, login_func):
    """
    Configura funções globais para recuperação automática de driver.
    Deve ser chamado no início do script principal.

    Args:
        criar_driver_func: Função que cria novo driver (ex: criar_driver do driver_config)
        login_func: Função que faz login no sistema (ex: login_pje, login_siscon, etc)

    Exemplo:
        from Fix import configurar_recovery_driver
        from driver_config import criar_driver
        from Fix import login_pje

        configurar_recovery_driver(criar_driver, login_pje)
    """
    _driver_recovery_config['criar_driver'] = criar_driver_func
    _driver_recovery_config['login_func'] = login_func
    logger.info("Configuração de recuperação automática ativada")


# Configuração global para recuperação automática de driver (mantida para compatibilidade)
_driver_recovery_config = {
    'enabled': False,
    'criar_driver': None,
    'login_func': None
}


def obter_driver_padronizado(headless=False):
    """Retorna um driver Firefox padronizado para TRT2."""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    from Fix.utils_paths import (
        obter_caminho_perfil_firefox,
        obter_caminho_firefox_executavel,
        obter_caminho_geckodriver
    )

    PROFILE_PATH = obter_caminho_perfil_firefox()
    FIREFOX_BINARY = obter_caminho_firefox_executavel()
    GECKODRIVER_PATH = obter_caminho_geckodriver()

    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)

    service = Service(executable_path=GECKODRIVER_PATH)

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.info(f"[DRIVER] Erro ao iniciar Firefox: {e}")
        raise


def driver_pc(headless=False):
    """Perfil PC: C:/Users/Silas/AppData/Roaming/Mozilla/Dev"""
    return obter_driver_padronizado(headless=headless)


def criar_driver_e_logar(driver=None, log=True):
    """Cria driver PC e faz login. Retorna driver pronto ou None em falha.
    Se driver já fornecido, reutiliza sem novo login (padrão aud.py).
    """
    import traceback as _tb
    if driver is not None:
        if log:
            print('[PET] Usando driver fornecido')
        return driver

    try:
        from Fix.utils import driver_pc as _driver_pc, login_cpf as _login_cpf
    except Exception as e:
        print(f'[PET] Erro ao importar Fix.utils: {e}')
        return None

    if log:
        print('[PET] Criando driver...')
    drv = _driver_pc()
    if not drv:
        print('[PET] Falha ao criar driver')
        return None

    ok = False
    try:
        ok = _login_cpf(drv)
    except Exception as e:
        print(f'[PET] Erro ao executar login_cpf: {e}')
        ok = False

    if not ok:
        try:
            drv.quit()
        except Exception:
            pass
        print('[PET] Login falhou')
        return None

    # Verificar se realmente estamos na sessão correta (não em acesso-negado)
    try:
        url = (drv.current_url or '').lower()
        if any(k in url for k in ['acesso-negado', 'access-denied', 'login.jsp']):
            print(f'[PET] Login retornou OK mas URL indica bloqueio: {url}')
            try:
                drv.quit()
            except Exception:
                pass
            return None
    except Exception:
        pass

    if log:
        print('[PET] Login OK')
    return drv


# Alias de compatibilidade
completo_driver_pc = criar_driver_e_logar


def login_cpf(driver, url_login=None, cpf=None, senha=None, aguardar_url_final=True):
    """
    Performs CPF login in PJe system
    """
    from .utils_login import login_cpf as actual_login_cpf
    return actual_login_cpf(driver, url_login, cpf, senha, aguardar_url_final)