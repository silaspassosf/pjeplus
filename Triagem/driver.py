"""Triagem/driver.py
Driver e login para o fluxo de Triagem Inicial.
"""
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.utils import driver_pc, login_cpf


def criar_driver_e_logar(driver: Optional[WebDriver] = None) -> Optional[WebDriver]:
    if driver:
        return driver

    drv = driver_pc()
    if not drv:
        return None

    if not login_cpf(drv):
        try:
            drv.quit()
        except Exception:
            pass
        return None

    return drv


__all__ = ['criar_driver_e_logar']
