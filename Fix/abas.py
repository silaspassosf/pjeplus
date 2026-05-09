"""Shim de compatibilidade — reexporta de Fix.browser_suporte."""
from Fix.browser_suporte import (  # noqa: F401
    validar_conexao_driver,
    trocar_para_nova_aba,
    forcar_fechamento_abas_extras,
    is_browsing_context_discarded_error,
    aguardar_nova_aba,
)


def fechar_abas_extras(driver, handle_principal=None):
    """Fecha todas as abas abertas exceto a aba principal.

    Args:
        driver: instancia Selenium WebDriver
        handle_principal: handle da aba a preservar; se None, usa driver.current_window_handle
    """
    principal = handle_principal or driver.current_window_handle
    forcar_fechamento_abas_extras(driver, principal)


__all__ = [
    'validar_conexao_driver',
    'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'fechar_abas_extras',
    'is_browsing_context_discarded_error',
]
