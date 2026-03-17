import logging
logger = logging.getLogger(__name__)

"""
Fix.selenium_base.field_operations - Módulo de operações de preenchimento de campos.

Parte da refatoração do Fix/core.py para melhor granularidade IA.
Nível 1 (Primitivos): Funções básicas de preenchimento de formulários.
"""

from typing import Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By


def preencher_campo(driver: WebDriver, seletor: str, valor: Union[str, int], trigger_events: bool = True, limpar: bool = True, log: bool = False) -> bool:
    """
    Preenche campo de formulário com triggers (1 script vs 3-4 requisições)
    Padrão repetitivo consolidado: clear + send_keys + trigger events

    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS do campo
        valor: Valor a preencher
        trigger_events: Se True, dispara input/change/blur
        limpar: Se True, limpa campo antes de preencher
        log: Ativa logging
    """
    try:
        element = driver.find_element(By.CSS_SELECTOR, seletor)

        if limpar:
            element.clear()

        element.send_keys(valor)

        if trigger_events:
            # Disparar eventos para frameworks reativos (Angular, React, Vue)
            driver.execute_script("""
                var element = arguments[0];
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                element.dispatchEvent(new Event('blur', { bubbles: true }));
            """, element)

        if log:
            logger.info(f'[PREENCHER_CAMPO] Sucesso: {seletor} = "{valor[:50]}..."')

        return True

    except Exception as e:
        if log:
            logger.error(f'[PREENCHER_CAMPO] Falhou: {seletor} - {str(e)[:100]}')
        return False


__all__ = [
    'preencher_campo'
]