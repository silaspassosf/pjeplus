import logging

logger = logging.getLogger(__name__)

"""
SISB Core - Login e simulacao humana
"""


def simular_movimento_humano(driver, elemento=None):
    """Simula movimento de mouse humano antes de clicar em elemento."""
    try:
        from SISB.core import simular_movimento_humano as _impl
        return _impl(driver, elemento)
    except Exception:
        pass


def login_automatico_sisbajud(driver):
    """Login automatizado no SISBAJUD delegando para SISB.core."""
    from SISB.core import login_automatico_sisbajud as _impl
    return _impl(driver)


def login_manual_sisbajud(driver, aguardar_url_final=True):
    """Login manual para SISBAJUD delegando para SISB.core."""
    from SISB.core import login_manual_sisbajud as _impl
    return _impl(driver, aguardar_url_final=aguardar_url_final)