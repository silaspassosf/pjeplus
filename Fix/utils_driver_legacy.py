import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_driver_legacy - Helpers legados de driver e navegacao.

Extraido do monolito Fix/utils.py para manter o shim fino.
"""

import time
from selenium.webdriver.common.by import By


def obter_driver_padronizado(headless=False):
    """Retorna um driver Firefox padronizado para TRT2."""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from Fix.variaveis import GECKODRIVER_PATH

    profile_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    firefox_binary = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = firefox_binary
    options.set_preference('profile', profile_path)

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


def navegar_para_tela(driver, url=None, seletor=None, delay=2, timeout=30, log=True):
    """Navega para URL ou clica em seletor."""
    try:
        if url:
            driver.get(url)
            if log:
                logger.info(f"[NAVEGAR] URL: {url}")
        if seletor:
            element = driver.find_element(By.CSS_SELECTOR, seletor)
            driver.execute_script('arguments[0].scrollIntoView(true);', element)
            element.click()
            time.sleep(delay)
            if log:
                logger.info(f"[NAVEGAR] Clicou: {seletor}")
        return True
    except Exception as e:
        if log:
            logger.info(f"[NAVEGAR][ERRO] {str(e)}")
        return False