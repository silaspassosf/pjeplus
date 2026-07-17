import logging
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


def main(driver: Optional[WebDriver] = None, tipo_driver: str = 'PC', tipo_login: str = 'CPF', headless: bool = False) -> bool:
    """
    Função principal - executa o novo fluxo.

    Args:
        driver: Driver existente (opcional)
        tipo_driver: Tipo de driver ('PC', 'VT', etc.) - usado se driver=None
        tipo_login: Tipo de login ('CPF', 'PC') - usado se driver=None
        headless: Executar em modo headless - usado se driver=None

    Se driver não for fornecido, cria automaticamente usando credencial().
    """
    if driver is None:
        from Fix.core import credencial

        driver = credencial(
            tipo_driver=tipo_driver,
            tipo_login=tipo_login,
            headless=headless,
        )

        if not driver:
            logger.error('[PEC][ERRO] Falha ao criar driver com credencial()')
            return False

        def recovery_credencial() -> WebDriver:
            return credencial(tipo_driver=tipo_driver, tipo_login=tipo_login, headless=headless)

        try:
            if 'configurar_recovery_driver' in globals():
                configurar_recovery_driver(recovery_credencial, lambda d: True)
        except Exception:
            pass

    from PEC.processamento import executar_fluxo_novo
    return executar_fluxo_novo(driver)
