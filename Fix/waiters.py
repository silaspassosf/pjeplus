#!/usr/bin/env python3
"""
Waiters - Utilitários centralizados de espera Selenium
Substitui time.sleep() por WebDriverWait inteligente
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def wait_for_element_visible(driver, locator: Tuple[str, str], timeout: int = 10) -> bool:
    """
    Aguarda elemento ficar visível.

    Args:
        driver: WebDriver Selenium
        locator: Tupla (By.TYPE, "selector")
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se elemento ficou visível

    Raises:
        TimeoutException: Se timeout expirar
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
        return True
    except TimeoutException:
        logger.warning(f"Elemento não ficou visível em {timeout}s: {locator}")
        raise


def wait_for_element_clickable(driver, locator: Tuple[str, str], timeout: int = 10) -> bool:
    """
    Aguarda elemento ficar clicável.

    Args:
        driver: WebDriver Selenium
        locator: Tupla (By.TYPE, "selector")
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se elemento ficou clicável

    Raises:
        TimeoutException: Se timeout expirar
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        return True
    except TimeoutException:
        logger.warning(f"Elemento não ficou clicável em {timeout}s: {locator}")
        raise


def wait_for_element_present(driver, locator: Tuple[str, str], timeout: int = 10) -> bool:
    """
    Aguarda elemento estar presente no DOM.

    Args:
        driver: WebDriver Selenium
        locator: Tupla (By.TYPE, "selector")
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se elemento está presente

    Raises:
        TimeoutException: Se timeout expirar
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        return True
    except TimeoutException:
        logger.warning(f"Elemento não encontrado em {timeout}s: {locator}")
        raise


def wait_for_text_in_element(driver, locator: Tuple[str, str], text: str, timeout: int = 10) -> bool:
    """
    Aguarda texto específico aparecer em elemento.

    Args:
        driver: WebDriver Selenium
        locator: Tupla (By.TYPE, "selector")
        text: Texto esperado
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se texto apareceu

    Raises:
        TimeoutException: Se timeout expirar
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.text_to_be_present_in_element(locator, text)
        )
        return True
    except TimeoutException:
        logger.warning(f"Texto '{text}' não apareceu em {timeout}s: {locator}")
        raise


def wait_for_url_contains(driver, url_fragment: str, timeout: int = 10) -> bool:
    """
    Aguarda URL conter fragmento específico.

    Args:
        driver: WebDriver Selenium
        url_fragment: Fragmento esperado na URL
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se URL contém fragmento

    Raises:
        TimeoutException: Se timeout expirar
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.url_contains(url_fragment)
        )
        return True
    except TimeoutException:
        logger.warning(f"URL não contém '{url_fragment}' em {timeout}s")
        raise


def wait_for_page_load(driver, timeout: int = 30) -> bool:
    """
    Aguarda página carregar completamente.

    Args:
        driver: WebDriver Selenium
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se página carregou

    Raises:
        TimeoutException: Se timeout expirar
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return True
    except TimeoutException:
        logger.warning(f"Página não carregou em {timeout}s")
        raise


def safe_wait_and_click(driver, locator: Tuple[str, str], timeout: int = 10) -> bool:
    """
    Aguarda elemento e clica com segurança.

    Args:
        driver: WebDriver Selenium
        locator: Tupla (By.TYPE, "selector")
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se clicou com sucesso

    Raises:
        TimeoutException: Se não conseguiu clicar
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        element.click()
        return True
    except TimeoutException:
        logger.warning(f"Não conseguiu clicar no elemento em {timeout}s: {locator}")
        raise


def safe_wait_and_fill(driver, locator: Tuple[str, str], text: str, timeout: int = 10) -> bool:
    """
    Aguarda elemento e preenche com texto.

    Args:
        driver: WebDriver Selenium
        locator: Tupla (By.TYPE, "selector")
        text: Texto a preencher
        timeout: Tempo máximo de espera em segundos

    Returns:
        bool: True se preencheu com sucesso

    Raises:
        TimeoutException: Se não conseguiu preencher
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        element.clear()
        element.send_keys(text)
        return True
    except TimeoutException:
        logger.warning(f"Não conseguiu preencher elemento em {timeout}s: {locator}")
        raise


def wait_for_any_element(driver, locators: list, timeout: int = 10) -> Optional[Tuple[str, str]]:
    """
    Aguarda qualquer um dos elementos aparecer.

    Args:
        driver: WebDriver Selenium
        locators: Lista de tuplas (By.TYPE, "selector")
        timeout: Tempo máximo de espera em segundos

    Returns:
        Tupla do locator que apareceu primeiro, ou None

    Raises:
        TimeoutException: Se nenhum elemento aparecer
    """
    try:
        def any_element_present(driver):
            for locator in locators:
                try:
                    driver.find_element(*locator)
                    return locator
                except NoSuchElementException:
                    continue
            return False

        return WebDriverWait(driver, timeout).until(any_element_present)
    except TimeoutException:
        logger.warning(f"Nenhum dos elementos apareceu em {timeout}s: {locators}")
        raise