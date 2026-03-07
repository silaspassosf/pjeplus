import logging
logger = logging.getLogger(__name__)

"""
Fix/headless_helpers.py
Funções otimizadas para execução headless - resolve click intercepted e timing issues
Estratégia: múltiplas tentativas com fallbacks progressivos
"""
import time
from typing import Optional, Callable, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    NoSuchElementException,
)

def limpar_overlays_headless(driver: WebDriver) -> bool:
    """
    Remove modals, tooltips e overlays que bloqueiam cliques em modo headless.
    Executado via JavaScript para máxima confiabilidade.
    
    Returns:
        bool: True se limpeza foi executada com sucesso
    """
    script = """
        try {
            // Remover modals backdrop
            document.querySelectorAll('.modal-backdrop, .cdk-overlay-backdrop, .fade.show').forEach(el => {
                el.remove();
            });
            
            // Remover tooltips
            document.querySelectorAll('[role="tooltip"], .tooltip, .popover').forEach(el => {
                el.remove();
            });
            
            // Fechar dropdowns abertos
            document.querySelectorAll('.dropdown-menu.show').forEach(el => {
                el.classList.remove('show');
            });
            
            // Remover overlays genéricos com z-index alto
            document.querySelectorAll('div[style*="z-index"]').forEach(el => {
                const zIndex = parseInt(window.getComputedStyle(el).zIndex);
                if (zIndex > 1000) {
                    el.style.display = 'none';
                }
            });
            
            return true;
        } catch(e) {
            return false;
        }
    """
    try:
        driver.execute_script(script)
        return True
    except Exception as e:
        return False

def scroll_to_element_safe(driver: WebDriver, element: WebElement) -> bool:
    """
    Scroll seguro para elemento com múltiplas estratégias.
    
    Args:
        driver: WebDriver instance
        element: Elemento para scrollar
        
    Returns:
        bool: True se scroll foi bem-sucedido
    """
    try:
        # Estratégia 1: scrollIntoView com comportamento suave
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", 
            element
        )
        return True
    except:
        try:
            # Estratégia 2: scroll manual baseado em posição
            driver.execute_script(
                "window.scrollTo(0, arguments[0].getBoundingClientRect().top + window.pageYOffset - 200);",
                element
            )
            return True
        except:
            return False

def click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
    """
    Click ultra-seguro para modo headless com 3 estratégias progressivas.
    
    Estratégia 1: Wait padrão + click normal
    Estratégia 2: Limpar overlays + scroll + wait + click
    Estratégia 3: JavaScript click direto (último recurso)
    
    Args:
        driver: WebDriver instance
        selector: Seletor CSS ou XPath
        by: Tipo de seletor (padrão CSS_SELECTOR)
        timeout: Timeout em segundos
        
    Returns:
        bool: True se click foi bem-sucedido
    """
    
    # Estratégia 1: Wait padrão element_to_be_clickable
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
        element.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        pass
    
    # Estratégia 2: Limpar overlays + scroll + wait + click
    try:
        limpar_overlays_headless(driver)
        element = WebDriverWait(driver, timeout // 2).until(
            EC.presence_of_element_located((by, selector))
        )
        scroll_to_element_safe(driver, element)
        element.click()
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        pass
    
    # Estratégia 3: JavaScript click (fallback final)
    try:
        element = driver.find_element(by, selector)
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
                return False

def wait_and_click_headless(driver: WebDriver, selector: str, timeout: int = 10) -> bool:
    """
    Wrapper de conveniência para click_headless_safe.
    Compatível com assinatura de funções Fix existentes.
    """
    return click_headless_safe(driver, selector, By.CSS_SELECTOR, timeout)

def find_element_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> Optional[WebElement]:
    """
    Busca elemento com retry e limpeza de overlays.
    
    Args:
        driver: WebDriver instance
        selector: Seletor CSS ou XPath
        by: Tipo de seletor
        timeout: Timeout em segundos
        
    Returns:
        WebElement ou None se não encontrado
    """
    try:
        # Tentativa 1: Wait padrão
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        # Tentativa 2: Limpar overlays e tentar novamente
        try:
            limpar_overlays_headless(driver)
            element = WebDriverWait(driver, timeout // 2).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except:
            return None

def executar_com_retry_headless(
    func: Callable,
    max_retries: int = 3,
    delay: float = 0.5,
    cleanup_between: bool = True,
    driver: Optional[WebDriver] = None
) -> Any:
    """
    Executa função com retry automático e limpeza de overlays.
    
    Args:
        func: Função a executar (pode receber driver como 1º arg)
        max_retries: Número máximo de tentativas
        delay: Delay entre tentativas (segundos)
        cleanup_between: Se True, limpa overlays entre retries
        driver: WebDriver instance (necessário se cleanup_between=True)
        
    Returns:
        Resultado da função
        
    Raises:
        Exception da última tentativa se todas falharem
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            if cleanup_between and driver and attempt > 0:
                limpar_overlays_headless(driver)
                time.sleep(delay * attempt)  # Backoff progressivo
            
            return func()
            
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise last_exception

def is_headless_mode(driver: WebDriver) -> bool:
    """
    Detecta se driver está em modo headless.
    
    Returns:
        bool: True se headless
    """
    try:
        result = driver.execute_script("return navigator.webdriver;")
        # Heurística: headless geralmente tem window.outerWidth == 0
        outer_width = driver.execute_script("return window.outerWidth;")
        return outer_width == 0 or result is True
    except:
        return False

def aguardar_elemento_headless_safe(driver: WebDriver, selector: str, timeout: int = 10) -> Optional[WebElement]:
    """
    Aguarda elemento estar presente e visível com estratégias headless-safe.
    Compatível com funções Fix existentes.
    
    Args:
        driver: WebDriver instance
        selector: Seletor CSS
        timeout: Timeout em segundos
        
    Returns:
        WebElement ou None
    """
    try:
        # Wait para elemento visível
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
        )
        return element
    except TimeoutException:
        # Fallback: limpar overlays e retry
        try:
            limpar_overlays_headless(driver)
            element = WebDriverWait(driver, timeout // 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element if element.is_displayed() else None
        except:
            return None

# Aliases para compatibilidade com código existente
esperar_elemento_headless = aguardar_elemento_headless_safe
wait_headless = wait_and_click_headless
