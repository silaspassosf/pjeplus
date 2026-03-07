import logging
logger = logging.getLogger(__name__)

"""
Fix.selenium_base.click_operations - Módulo de operações de clique.

Parte da refatoração do Fix/core.py para melhor granularidade IA.
Nível 1 (Primitivos): Funções básicas de clique em elementos.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, ElementClickInterceptedException, ElementNotInteractableException
)
from typing import Union, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

def aguardar_e_clicar(driver: WebDriver, seletor: str, log: bool = False, timeout: int = 10, by: By = By.CSS_SELECTOR,
                     usar_js: bool = True, retornar_elemento: bool = False, debug: Optional[bool] = None) -> Union[bool, Optional[WebElement]]:
    """
    Aguarda elemento aparecer e clica nele (1 requisição vs 2-3 separadas)
    Padrão repetitivo consolidado: esperar_elemento() + safe_click()

    MELHORADO: Adiciona múltiplas estratégias para botões PJe que podem ter diferentes estruturas
     OTIMIZADO: Suporte para modo headless com fallback automático
    """
    if debug is not None:
        log = debug

    try:
        # Estratégia 1: Elemento clicável direto
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, seletor))
        )

        if usar_js:
            # JS click (mais confiável em headless)
            driver.execute_script("arguments[0].click();", element)
        else:
            # Click tradicional
            element.click()

        if log:
            logger.info(f'[AGUARDAR_E_CLICAR] Sucesso: {seletor}')

        return element if retornar_elemento else True

    except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException) as e:
        if log:
            logger.warning(f'[AGUARDAR_E_CLICAR] Tentativa padrão falhou: {seletor} - {str(e)[:100]}')

        # Estratégia 2: Scroll + retry
        try:
            element = driver.find_element(by, seletor)
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)

            if usar_js:
                driver.execute_script("arguments[0].click();", element)
            else:
                element.click()

            if log:
                logger.info(f'[AGUARDAR_E_CLICAR] Sucesso na estratégia 2: {seletor}')
            return element if retornar_elemento else True

        except Exception as e2:
            if log:
                logger.error(f'[AGUARDAR_E_CLICAR] Falhou todas estratégias: {seletor} - {str(e2)[:100]}')
            return False


__all__ = [
    'aguardar_e_clicar'
]