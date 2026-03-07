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

    OTIMIZADO: Sem scrollIntoView agressivo (causa layout shift)
    Estratégias:
      1. Element.click() direto (espera clicável)
      2. JS dispatchEvent (padrão gigs-plugin)
      3. ActionChains (último recurso)
    """
    if debug is not None:
        log = debug

    try:
        # Estratégia 1: Elemento clicável direto (wait até estar clicável)
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, seletor))
        )

        if usar_js:
            # JS click - usar dispatchEvent ao invés de .click() nativo
            # (evita side-effects tipo navegação indesejada)
            driver.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));",
                element
            )
        else:
            # Click tradicional
            element.click()

        if log:
            logger.info(f'[AGUARDAR_E_CLICAR] Sucesso: {seletor}')

        return element if retornar_elemento else True

    except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException) as e:
        if log:
            logger.warning(f'[AGUARDAR_E_CLICAR] Tentativa padrão falhou: {seletor} - {str(e)[:100]}')

        # Estratégia 2: Scroll MÍNIMO (nearest) + retry
        # Obs: Usamos 'nearest' em vez de 'center' para evitar layout shift
        try:
            element = driver.find_element(by, seletor)
            # Scroll apenas o mínimo necessário (nearest = scroll apenas se fora de viewport)
            driver.execute_script("arguments[0].scrollIntoView({block: 'nearest', behavior: 'smooth'});", element)
            time.sleep(0.3)

            if usar_js:
                driver.execute_script(
                    "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));",
                    element
                )
            else:
                element.click()

            if log:
                logger.info(f'[AGUARDAR_E_CLICAR] Sucesso na estratégia 2: {seletor}')
            return element if retornar_elemento else True

        except Exception as e2:
            if log:
                logger.error(f'[AGUARDAR_E_CLICAR] Falhou todas estratégias: {seletor} - {str(e2)[:100]}')
            return False


def safe_click_no_scroll(driver: WebDriver, element: WebElement, log: bool = False) -> bool:
    """
    Click sem scrollIntoView (evita layout shifts e problemas com header dinâmico).
    Baseado na estratégia robusta do gigs-plugin (maisPje).
    
    Estratégias:
      1. Focus window + dispatchEvent (padrão gigs-plugin) - mais seguro
      2. JS click() nativo (fallback)
    
    Args:
        driver: WebDriver
        element: WebElement para clicar
        log: Se True, loga operação
    
    Returns:
        True se clicou com sucesso, False caso contrário
    """
    try:
        # 1. Garantir foco na window (importante para cliques automáticos)
        driver.execute_script("window.focus();")
        time.sleep(0.1)
        
        # 2. Usar dispatchEvent em vez de .click() (evita navegação indesejada)
        driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));",
            element
        )
        
        if log:
            logger.info(f'[SAFE_CLICK_NO_SCROLL] Sucesso com dispatchEvent')
        return True
        
    except Exception as e:
        if log:
            logger.warning(f'[SAFE_CLICK_NO_SCROLL] Falhou dispatchEvent: {str(e)[:80]}')
        
        # Fallback: JS click nativo
        try:
            driver.execute_script("arguments[0].click();", element)
            if log:
                logger.info(f'[SAFE_CLICK_NO_SCROLL] Sucesso com .click()')
            return True
        except Exception as e2:
            if log:
                logger.error(f'[SAFE_CLICK_NO_SCROLL] Todas estratégias falharam: {str(e2)[:80]}')
            return False


__all__ = [
    'aguardar_e_clicar',
    'safe_click_no_scroll'
]