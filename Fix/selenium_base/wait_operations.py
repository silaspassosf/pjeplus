import logging
logger = logging.getLogger(__name__)

"""
@module: Fix.selenium_base.wait_operations
@responsibility: Operações de espera e sincronização Selenium
@depends_on: selenium.webdriver, selenium.webdriver.support
@used_by: Todos os módulos do projeto (base fundamental)
@entry_points: aguardar_e_clicar, esperar_elemento, wait, wait_for_visible, wait_for_clickable, esperar_url_conter
@tags: #selenium #wait #sync #webdriver #timeout
@created: 2026-01-29
@refactored_from: Fix/core.py lines 44-103, 288-364, 366-461, 2248-2268
"""

import os
import time
from typing import Optional, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ..log import logger

# Variáveis de compatibilidade
DEBUG = os.getenv('PJEPLUS_DEBUG', '0').lower() in ('1', 'true', 'on')

def _log_info(msg: str) -> None:
    """Compatibilidade com logs antigos"""
    logger.info(msg)

def wait(driver: WebDriver, selector: str, timeout: int = 10, by: By = By.CSS_SELECTOR) -> Optional[WebElement]:
    """
    DEPRECATED: Use aguardar_e_clicar() ou esperar_elemento() para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Espera até que um elemento esteja visível na página.
    
    Args:
        driver: WebDriver Selenium
        selector: Seletor CSS/XPATH do elemento
        timeout: Tempo máximo de espera em segundos (default: 10)
        by: Tipo de seletor (default: By.CSS_SELECTOR)
        
    Returns:
        WebElement se encontrado, None se timeout
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        logger.error(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None

def wait_for_visible(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[By] = None) -> Optional[WebElement]:
    """
    DEPRECATED: Use aguardar_e_clicar(usar_js=False) para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Wait for an element to be visible in the DOM.
    
    Args:
        driver: WebDriver Selenium
        selector: Seletor CSS/XPATH do elemento
        timeout: Tempo máximo de espera em segundos (default: 10)
        by: Tipo de seletor (default: By.CSS_SELECTOR)
        
    Returns:
        WebElement se visível, None se timeout
    """
    if by is None:
        by = By.CSS_SELECTOR
        
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        if isinstance(selector, str):
            logger.info(f"[WAIT_VISIBLE] Elemento não visível: {selector}")
        return None

def wait_for_clickable(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[By] = None) -> Optional[WebElement]:
    """
    DEPRECATED: Use aguardar_e_clicar() para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Wait for an element to be clickable in the DOM.
    
    Args:
        driver: WebDriver Selenium
        selector: Seletor CSS/XPATH do elemento
        timeout: Tempo máximo de espera em segundos (default: 10)
        by: Tipo de seletor (default: By.CSS_SELECTOR)
        
    Returns:
        WebElement se clicável, None se timeout
    """
    if by is None:
        by = By.CSS_SELECTOR
        
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        if isinstance(selector, str):
            logger.info(f"[WAIT_CLICKABLE] Elemento não clicável: {selector}")
        return None

def esperar_elemento(
    driver: WebDriver, 
    seletor: str, 
    texto: Optional[str] = None, 
    timeout: int = 10, 
    by: By = By.CSS_SELECTOR, 
    log: bool = False
) -> Optional[WebElement]:
    """
    Versão aprimorada - Espera até que um elemento esteja presente (e opcionalmente contenha texto), 
    com logs detalhados e ajuste automático para modo headless.
    
    HEADLESS AUTO-TUNING:
    - Detecta modo headless automaticamente
    - Aumenta timeout em 50% (headless é mais lento)
    - Retry automático com limpar overlays
    - Log detalhado apenas em falhas
    
    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS/XPATH do elemento
        texto: Texto opcional que deve estar contido no elemento
        timeout: Tempo máximo de espera em segundos (default: 10)
        by: Tipo de seletor (default: By.CSS_SELECTOR)
        log: Se True, loga operação (default: False)
        
    Returns:
        WebElement se encontrado, None se timeout
        
    Raises:
        ValueError: Se seletor ou texto não forem strings
    """
    # Detectar headless e ajustar timeout
    is_headless = False
    try:
        from Fix.headless_helpers import is_headless_mode
        is_headless = is_headless_mode(driver)
        if is_headless:
            original_timeout = timeout
            timeout = int(timeout * 1.5)  # 50% mais tempo em headless
            if DEBUG:
                logger.info(f"[HEADLESS] Timeout ajustado: {original_timeout}s -> {timeout}s para '{seletor}'")
    except ImportError:
        pass
    
    try:
        if not isinstance(seletor, str):
            raise ValueError(f"Seletor deve ser string, recebido: {type(seletor)}")
        if texto and not isinstance(texto, str):
            raise ValueError(f"Text must be a string, got: {type(texto)}")
        if DEBUG:
            _log_info(f"[ESPERAR] Aguardando elemento: '{seletor}' (by={by}, timeout={timeout}, texto={texto})")
        
        t0 = time.time()
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )
        t1 = time.time()
        if DEBUG:
            logger.info(f"[ESPERAR][OK] Elemento encontrado: '{seletor}' em {t1-t0:.2f}s" + (f" (texto='{texto}')" if texto else ""))
        return el
        
    except Exception as e:
        # HEADLESS RETRY: Tentar limpar overlays e retry uma vez
        if is_headless and by == By.CSS_SELECTOR:
            try:
                from Fix.headless_helpers import limpar_overlays_headless
                logger.warning(f"[HEADLESS][RETRY] Elemento '{seletor}' não encontrado, limpando overlays e tentando novamente...")
                limpar_overlays_headless(driver)
                time.sleep(0.5)
                
                # Segunda tentativa (timeout menor - metade do ajustado)
                el = WebDriverWait(driver, timeout // 2).until(
                    EC.presence_of_element_located((by, seletor))
                )
                if texto:
                    WebDriverWait(driver, timeout // 2).until(
                        lambda d: texto in el.text
                    )
                logger.info(f"[HEADLESS][RETRY] Sucesso após limpar overlays: '{seletor}'")
                return el
            except Exception:
                pass  # Falhou mesmo com retry
        
        logger.error(f"[ESPERAR][ERRO] Falha ao esperar elemento: '{seletor}' (by={by}, timeout={timeout}, texto={texto}) -> {e}")
        return None

def aguardar_e_clicar(
    driver: WebDriver, 
    seletor: str, 
    log: bool = False, 
    timeout: int = 10, 
    by: By = By.CSS_SELECTOR, 
    usar_js: bool = True, 
    retornar_elemento: bool = False, 
    debug: Optional[bool] = None
) -> Union[bool, Optional[WebElement]]:
    """
     FUNÇÃO MAIS USADA DO PROJETO 
    
    Aguarda elemento aparecer e clica nele (1 requisição vs 2-3 separadas)
    Padrão repetitivo consolidado: esperar_elemento() + safe_click()
    
    MELHORADO: Adiciona múltiplas estratégias para botões PJe que podem ter diferentes estruturas
     OTIMIZADO: Suporte para modo headless com fallback automático
    
    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS ou XPath
        timeout: Timeout em segundos (default: 10)
        by: Tipo de seletor (default: By.CSS_SELECTOR)
        usar_js: Se True usa MutationObserver, se False usa Python (default: True)
        log: Ativa logging (default: False)
        retornar_elemento: Se True, retorna o elemento em vez de True/False (default: False)
        debug: Se especificado, sobrescreve 'log'
    
    Returns:
        Se retornar_elemento=True: WebElement encontrado ou None
        Se retornar_elemento=False: True se clicou com sucesso, False caso contrário
    """
    if debug is not None:
        log = debug
    
    #  NOVO: Detectar headless e usar estratégia otimizada se disponível
    try:
        if by == By.CSS_SELECTOR and not retornar_elemento:
            from Fix.headless_helpers import click_headless_safe, is_headless_mode
            if is_headless_mode(driver):
                if log:
                    logger.info(f"[HEADLESS] Usando click_headless_safe para: {seletor}")
                return click_headless_safe(driver, seletor, timeout=timeout)
    except ImportError:
        pass  # headless_helpers não disponível, continuar normal
    
    if retornar_elemento:
        # Modo busca de elemento - usar esperar_elemento existente
        return esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
    
    # Estratégia especial para botões PJe - tentar múltiplas variações
    if "movimentar processos" in seletor.lower():
        # NOTE: _clicar_botao_movimentar será extraído para element_interaction.py
        # Por ora, importar de core.py
        from ..core import _clicar_botao_movimentar
        return _clicar_botao_movimentar(driver, timeout, log)
    
    # Estratégia especial para botão "Abrir tarefa do processo" - problema contextual no Mandado
    if seletor == 'button[mattooltip="Abre a tarefa do processo"]':
        # NOTE: _clicar_botao_tarefa_processo será extraído para element_interaction.py
        from ..core import _clicar_botao_tarefa_processo
        return _clicar_botao_tarefa_processo(driver, timeout, log)
    
    # Modo click original
    if usar_js and by == By.CSS_SELECTOR:
        try:
            # NOTE: js_base() será extraído para utils_refactored/javascript.py
            from ..core import js_base
            
            # execute_async_script: callback automático via 'arguments[arguments.length - 1]'
            script = f"""
            {js_base()}
            const callback = arguments[arguments.length - 1];
            esperarElemento('{seletor}', {timeout*1000})
                .then(el => {{
                    if (el) {{
                        el.click();
                        callback(true);
                    }} else {{
                        callback(false);
                    }}
                }})
                .catch(err => {{
                    console.error('Erro aguardar_e_clicar:', err);
                    callback(false);
                }});
            """
            resultado = driver.execute_async_script(script)
            if log:
                status = "" if resultado else ""
                logger.info(f"{status} aguardar_e_clicar JS: {seletor}")
            return resultado
        except Exception as e:
            if log:
                pass
            # Fallback para Python
            usar_js = False
    
    # Fallback Python (ou escolha explícita)
    if not usar_js:
        elemento = esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
        if elemento:
            try:
                elemento.click()
                if log:
                    pass
                return True
            except Exception as e:
                if log:
                    pass
                return False
        else:
            if log:
                pass
            return False

def esperar_url_conter(driver: WebDriver, substring: str, timeout: int = 10) -> bool:
    """
    Espera até que a URL atual contenha a substring especificada.

    Args:
        driver: WebDriver instance
        substring: String a ser encontrada na URL
        timeout: Tempo máximo de espera em segundos (default: 10)

    Returns:
        bool: True se encontrou, False se timeout
    """
    import time as _t
    deadline = _t.monotonic() + timeout
    intervalo = 0.2
    while _t.monotonic() < deadline:
        try:
            if substring in driver.current_url:
                return True
        except Exception:
            pass
        remaining = deadline - _t.monotonic()
        if remaining <= 0:
            break
        _t.sleep(min(intervalo, remaining))
        intervalo = min(intervalo * 1.5, 0.5)
    try:
        current_url = driver.current_url
    except Exception:
        current_url = '<inacessível>'
    logger.error(f'[URL][ERRO] Timeout esperando URL conter: "{substring}". URL atual: {current_url}')
    return False

def _aguardar_loader_painel(driver: WebDriver, timeout: int = 10) -> None:
    """Espera loader (mat-progress-bar) sumir antes de seguir."""
    loader_selector = ".mat-progress-bar-primary.mat-progress-bar-fill"
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, loader_selector))
        )
    except TimeoutException:
        pass
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, loader_selector))
        )
        time.sleep(0.3)
    except TimeoutException:
        pass

# Exportações públicas
__all__ = [
    'wait',
    'wait_for_visible',
    'wait_for_clickable',
    'esperar_elemento',
    'aguardar_e_clicar',
    'esperar_url_conter'
]
