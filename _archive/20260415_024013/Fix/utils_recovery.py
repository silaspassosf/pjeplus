import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_recovery - Recuperacao automatica de driver.

Extraido do monolito Fix/utils.py para manter o shim fino.
"""

_driver_recovery_config = {
    'enabled': False,
    'criar_driver': None,
    'login_func': None
}


def configurar_recovery_driver(criar_driver_func, login_func):
    """
    Configura funcoes globais para recuperacao automatica de driver.
    """
    _driver_recovery_config['criar_driver'] = criar_driver_func
    _driver_recovery_config['login_func'] = login_func


def verificar_e_tratar_acesso_negado_global(driver):
    """
    Verifica automaticamente se driver esta em /acesso-negado e tenta recuperar.
    """
    if not _driver_recovery_config['enabled']:
        return None

    try:
        url_atual = driver.current_url
        if 'acesso-negado' not in url_atual.lower() and 'login.jsp' not in url_atual.lower():
            return None

        try:
            driver.quit()
        except Exception as e:
            logger.error(f"[RECOVERY_GLOBAL]  Erro ao fechar driver: {e}")

        if not _driver_recovery_config['criar_driver'] or not _driver_recovery_config['login_func']:
            logger.error("Funcoes de recuperacao nao configuradas!")
            raise Exception("Recovery nao configurado - use configurar_recovery_driver()")

        novo_driver = _driver_recovery_config['criar_driver'](headless=False)
        if not novo_driver:
            logger.error("Falha ao criar novo driver")
            raise Exception("Falha ao criar driver na recuperacao")

        if not _driver_recovery_config['login_func'](novo_driver):
            logger.error("Falha ao fazer login")
            novo_driver.quit()
            raise Exception("Falha no login durante recuperacao")

        return novo_driver

    except Exception as e:
        logger.error(f"[RECOVERY_GLOBAL]  ERRO CRITICO NA RECUPERACAO: {e}")
        raise


def handle_exception_with_recovery(e, driver, funcao_nome=""):
    """
    Trata excecao verificando se e acesso negado e tentando recuperar driver.
    """
    prefixo = f"[{funcao_nome}]" if funcao_nome else "[EXCEPTION]"

    try:
        novo_driver = verificar_e_tratar_acesso_negado_global(driver)
        if novo_driver:
            return novo_driver
    except Exception as recovery_error:
        logger.error(f"{prefixo}  Falha na recuperacao automatica: {recovery_error}")

    logger.error(f"{prefixo}  Erro: {e}")
    return None