# -*- coding: utf-8 -*-
"""Fix.driver_factory — Fábricas de driver para o PJePlus sobre Playwright."""

import os
from .log import logger
from Fix import espera
from Play.pjeplay.launcher import (
    criar_driver,
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_vt,
    finalizar_driver,
)

# Constantes mantidas para compatibilidade com chamadores legados
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')
FIREFOX_BINARY_PADRAO = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
FIREFOX_BINARY_PADRAO_ALT = r"C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe"
SISB_PROFILE_PC = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
SISB_PROFILE_NOTEBOOK = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'

criar_driver_pc = criar_driver_PC
criar_driver_vt = criar_driver_VT
criar_driver_sisb_notebook = criar_driver_sisb_vt


def _aplicar_preferencias(options, preferencias):
    pass


def _configurar_driver_pos_criacao(driver, headless=False):
    pass


def _criar_driver_firefox(options=None, service=None, headless=False):
    return criar_driver(headless=headless)


def _resolver_binario_firefox_padrao():
    for caminho in (FIREFOX_BINARY_PADRAO, FIREFOX_BINARY_PADRAO_ALT):
        if os.path.exists(caminho):
            return caminho
    return None


def _montar_options_pc(headless=False):
    return None


def _montar_options_vt(headless=False, usar_perfil_vt=False, modo_fallback=False):
    return None


def com_retry(func, max_tentativas=3, delay_base=2):
    def wrapper(*args, **kwargs):
        for tentativa in range(1, max_tentativas + 1):
            try:
                driver = func(*args, **kwargs)
                if driver:
                    return driver
            except Exception as e:
                logger.warning(f"Tentativa {tentativa}/{max_tentativas} falhou: {e}")
                if tentativa < max_tentativas:
                    espera.pausa(None, delay_base * tentativa)
        return None
    return wrapper


def fechar_janelas_extras(driver):
    handles = getattr(driver, "window_handles", [])
    if len(handles) > 1:
        janela_principal = handles[0]
        for handle in handles[1:]:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except Exception:
                pass
        try:
            driver.switch_to.window(janela_principal)
        except Exception:
            pass
