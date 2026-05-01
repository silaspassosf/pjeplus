"""
Fix.core - Módulo de core para PJe automação.

Migrado automaticamente de Fix.py (PARTE 5 - Modularização).
"""

import os
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException, NoSuchWindowException, ElementClickInterceptedException, 
    ElementNotInteractableException
)
from typing import Optional, Dict, Any, List, Union, Callable
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re, time, datetime, json, pyperclip, logging
from pathlib import Path
from .log import logger

# Variáveis de compatibilidade para logs antigos
DEBUG = os.getenv('PJEPLUS_DEBUG', '0').lower() in ('1', 'true', 'on')

TIME_ENABLED = True

def medir_tempo(label: str = None):
    """Decorator simples para medir tempo de funções de alto nível."""
    def _decorator(func):
        def _wrapper(*args, **kwargs):
            if not TIME_ENABLED:
                return func(*args, **kwargs)
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                logger.info('[TEMPO] %s.%s: %.3fs', func.__name__, label or func.__name__, elapsed)
        try:
            _wrapper.__name__ = func.__name__
            _wrapper.__doc__ = func.__doc__
        except Exception:
            pass
        return _wrapper
    return _decorator

def _log_info(msg):
    """Compatibilidade com logs antigos"""
    logger.info(msg)

def _log_error(msg):
    """Compatibilidade com logs antigos"""
    logger.error(msg)

def _audit(action, target, status, extra=None):
    """Compatibilidade com auditoria antiga - agora usa logger"""
    if extra:
        logger.debug(f"[AUDIT] {action}:{target}:{status} {extra}")
    else:
        logger.debug(f"[AUDIT] {action}:{target}:{status}")


def aguardar_renderizacao_nativa(
    driver,
    seletor: Optional[str] = None,
    modo: str = "aparecer",
    timeout: Union[int, float] = 10,
):
    """Contrato estável para espera de renderização e transição de DOM.

    Suporta os usos ativos do projeto:
    - sem seletor: aguarda document.readyState == complete
    - modo='aparecer': algum elemento visível encontrado
    - modo='sumir': nenhum elemento visível encontrado
    - modo='habilitado': algum elemento visível e habilitado
    """

    def _coletar_elementos(web_driver):
        if not seletor:
            return []
        try:
            return web_driver.find_elements(By.CSS_SELECTOR, seletor)
        except Exception:
            return []

    def _elemento_visivel(element):
        try:
            return element.is_displayed()
        except Exception:
            return False

    timeout_segundos = float(timeout)

    try:
        if not seletor:
            WebDriverWait(driver, timeout_segundos).until(
                lambda current_driver: current_driver.execute_script("return document.readyState") == "complete"
            )
            return True

        if modo == "sumir":
            WebDriverWait(driver, timeout_segundos).until(
                lambda current_driver: not any(
                    _elemento_visivel(element)
                    for element in _coletar_elementos(current_driver)
                )
            )
            return True

        if modo == "habilitado":
            WebDriverWait(driver, timeout_segundos).until(
                lambda current_driver: any(
                    _elemento_visivel(element) and element.is_enabled()
                    for element in _coletar_elementos(current_driver)
                )
            )
            return True

        WebDriverWait(driver, timeout_segundos).until(
            lambda current_driver: any(
                _elemento_visivel(element)
                for element in _coletar_elementos(current_driver)
            )
        )
        return True
    except TimeoutException:
        return False
    except Exception:
        return False

def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """
    DEPRECATED: Use aguardar_e_clicar() ou js_base() para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Espera até que um elemento esteja visível na página.
    """
    try:
        _t0 = time.time()
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        logger.error(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None


def wait_for_page_load(driver, timeout=10):
    """Compatibilidade para esperar o carregamento básico da página."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda current_driver: current_driver.execute_script("return document.readyState") == "complete"
        )
        return True
    except TimeoutException:
        return False
    except Exception:
        return False

# Função de clique seguro

def wait_for_visible(driver, selector, timeout=10, by=None):
    """
    DEPRECATED: Use aguardar_e_clicar(usar_js=False) para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Wait for an element to be visible in the DOM.
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
            print(f"[WAIT_VISIBLE] Elemento não visível: {selector}")
        return None


def wait_for_clickable(driver, selector, timeout=10, by=None):
    """
    DEPRECATED: Use aguardar_e_clicar() para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Wait for an element to be clickable in the DOM.
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
            print(f"[WAIT_CLICKABLE] Elemento não clicável: {selector}")
        return None


def safe_click(driver, selector_or_element, timeout=10, by=None, log=False):
    """
    DEPRECATED: Use aguardar_e_clicar() para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Clicks safely. Accepts selector (string) or element.
    """
    try:
        from selenium.webdriver.common.by import By
        if isinstance(selector_or_element, str):
            element = wait(driver, selector_or_element, timeout, by)
        else:
            element = selector_or_element
        # Fallback for KZ details icon (robust selector)
        if element is None and isinstance(selector_or_element, str) and (
            'Detalhes do Processo' in selector_or_element or 'detalhes do processo' in selector_or_element.lower()
        ):
            try:
                # Try clicking the KZ icon directly
                element = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]')
                driver.execute_script("arguments[0].click();", element)
                if DEBUG:
                    _log_info('[CLICK] Clicked KZ details icon (img.mat-tooltip-trigger)')
                _audit('click', 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]', 'ok')
                return True
            except Exception:
                element = None
            # Try clicking the parent button if img not clickable
            try:
                img = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]')
                button = img.find_element(By.XPATH, './ancestor::button[1]')
                driver.execute_script("arguments[0].click();", button)
                if DEBUG:
                    _log_info('[CLICK] Clicked parent button of KZ details icon')
                _audit('click', 'button(parentOf: img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"])', 'ok')
                return True
            except Exception:
                pass
        if element and element.is_displayed():
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
                    driver.execute_script("arguments[0].click();", element)
                    if DEBUG:
                        _log_info(f'[CLICK] Clicked: {element.text if hasattr(element, "text") else selector_or_element}')
                    _audit('click', selector_or_element, 'ok')
                    return True
                except Exception as e_click:
                    # Tentativa de fallback: reduzir zoom temporariamente e tentar JS click novamente
                    try:
                        if log:
                            print(f'[CLICK][WARN] JS click falhou: {e_click} - tentando fallback de zoom')
                        prev_zoom = driver.execute_script("return document.body.style.zoom || '';")
                        driver.execute_script("document.body.style.zoom = '60%';")
                        time.sleep(0.12)
                        driver.execute_script("arguments[0].click();", element)
                        # restaurar zoom
                        try:
                            driver.execute_script(f"document.body.style.zoom = '{prev_zoom}';")
                        except Exception:
                            pass
                        if DEBUG:
                            _log_info(f'[CLICK] Click via JS com zoom reduzido: {selector_or_element}')
                        _audit('click', selector_or_element, 'ok-fallback-zoom')
                        return True
                    except Exception as e_fallback:
                        if log:
                            print(f'[CLICK][ERROR] Fallback click falhou: {e_fallback}')
                        try:
                            # tentar restaurar zoom mesmo em caso de erro
                            driver.execute_script(f"document.body.style.zoom = '{prev_zoom}';")
                        except Exception:
                            pass
                        _log_error(f'[CLICK][ERROR] Failed to click after fallback: {e_fallback}')
                        _audit('click', selector_or_element, 'fail', {'error': str(e_fallback)[:300]})
                        return False
        # Se o elemento não estiver visível, tentar um click via JS (pode funcionar mesmo se is_displayed() for False)
        try:
            driver.execute_script("arguments[0].click();", element)
            if DEBUG:
                _log_info(f'[CLICK] Click via JS em elemento não visível: {selector_or_element}')
            _audit('click', selector_or_element, 'ok-js-hidden')
            return True
        except Exception as e_hidden:
            # Última tentativa: reduzir zoom e tentar novamente
            try:
                prev_zoom = driver.execute_script("return document.body.style.zoom || '';")
                driver.execute_script("document.body.style.zoom = '60%';")
                time.sleep(0.12)
                driver.execute_script("arguments[0].click();", element)
                try:
                    driver.execute_script(f"document.body.style.zoom = '{prev_zoom}';")
                except Exception:
                    pass
                if DEBUG:
                    _log_info(f'[CLICK] Click via JS com zoom reduzido em elemento não visível: {selector_or_element}')
                _audit('click', selector_or_element, 'ok-js-hidden-zoom')
                return True
            except Exception as e_final:
                _log_error(f'[CLICK][ERROR] Failed to click hidden element: {e_final}')
                _audit('click', selector_or_element, 'fail-hidden', {'error': str(e_final)[:300]})
                return False
    except Exception as e:
        _log_error(f'[CLICK][ERROR] Failed to click: {e}')
        _audit('click', selector_or_element, 'fail', {'error': str(e)[:300]})
        return False


def safe_click_no_scroll(driver, element, log=False):
    """Compatibilidade: dispara o click direto sem scroll prévio."""
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))",
            element,
        )
        return True
    except Exception as e:
        if log:
            print(f'[CLICK][ERROR] safe_click_no_scroll falhou: {e}')
        return False


def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5, log=False):
    # Versão 3.1 - Busca robusta com logs detalhados e timeout reduzido
    def buscar_input_associado(elemento):
        try:
            input_associado = elemento.find_element(By.XPATH, 
                './following-sibling::input|./preceding-sibling::input|'
                './ancestor::*[contains(@class,"form-group")]//input|'
                './ancestor::*[contains(@class,"mat-form-field")]//input'
            )
            return input_associado
        except Exception as e:
            if log:
                print(f'[ROBUSTO][DEBUG] Falha ao buscar input associado: {e}')
            return None
    try:
        # Fase 1: Busca direta por inputs editáveis
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE1] Buscando input com texto/atributo: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, 
                    f'input[placeholder*="{texto}"], '
                    f'input[aria-label*="{texto}"], '
                    f'input[name*="{texto}"]'
                )
                for el in elementos:
                    if el.is_displayed() and el.is_enabled():
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Input direto: {el}')
                        return el
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase1: {e}')
                continue
        # Fase 2: Busca hierárquica se não encontrar diretamente
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE2] Buscando por texto visível: {texto}')
            try:
                elementos = driver.find_elements(By.XPATH, 
                    f'//*[contains(text(), "{texto}")]'
                )
                for el in elementos:
                    if DEBUG:
                        _log_info(f'[ROBUSTO][FASE2] Elemento com texto encontrado: {el}')
                    input_assoc = buscar_input_associado(el)
                    if input_assoc:
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Input associado: {input_assoc}')
                        return input_assoc
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase2: {e}')
                continue
        # Fase 3: Busca por ícone/fa
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE3] Buscando ícone/fa: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all')
                for el in elementos:
                    if el.is_displayed():
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Ícone/fa: {el}')
                        return el
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase3: {e}')
                continue
        if DEBUG:
            _log_info('[ROBUSTO][FIM] Nenhum elemento encontrado com os critérios fornecidos.')
        return None
    except Exception as e:
        _log_error(f'[ROBUSTO][ERRO GERAL] {e}')
        return None

def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR, log=False):
    """
    Versão aprimorada - Espera até que um elemento esteja presente (e opcionalmente contenha texto), 
    com logs detalhados e ajuste automático para modo headless.
    
    HEADLESS AUTO-TUNING:
    - Detecta modo headless automaticamente
    - Aumenta timeout em 50% (headless é mais lento)
    - Retry automático com limpar overlays
    - Log detalhado apenas em falhas
    """
    import time as _time
    
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
        
        t0 = _time.time()
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )
        t1 = _time.time()
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
                _time.sleep(0.5)
                
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

# =========================
# 4. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

# Função para extrair documento

def aguardar_e_clicar(driver, seletor, log=False, timeout=10, by=By.CSS_SELECTOR, usar_js=True, retornar_elemento=False, debug=None):
    if debug is not None:
        log = debug
    """
    Aguarda elemento aparecer e clica nele (1 requisição vs 2-3 separadas)
    Padrão repetitivo consolidado: esperar_elemento() + safe_click()
    
    MELHORADO: Adiciona múltiplas estratégias para botões PJe que podem ter diferentes estruturas
    ✨ OTIMIZADO: Suporte para modo headless com fallback automático
    
    Args:
        driver: WebDriver Selenium
        seletor: Seletor CSS ou XPath
        timeout: Timeout em segundos
        by: Tipo de seletor (By.CSS_SELECTOR padrão)
        usar_js: Se True usa MutationObserver, se False usa Python
        log: Ativa logging
        retornar_elemento: Se True, retorna o elemento em vez de True/False
    
    Returns:
        Se retornar_elemento=True: Elemento encontrado ou None
        Se retornar_elemento=False: True se clicou com sucesso, False caso contrário
    """
    # ✨ NOVO: Detectar headless e usar estratégia otimizada se disponível
    try:
        if by == By.CSS_SELECTOR and not retornar_elemento:
            from Fix.headless_helpers import click_headless_safe, is_headless_mode
            if is_headless_mode(driver):
                if log:
                    print(f"[HEADLESS] Usando click_headless_safe para: {seletor}")
                return click_headless_safe(driver, seletor, timeout=timeout)
    except ImportError:
        pass  # headless_helpers não disponível, continuar normal
    
    if retornar_elemento:
        # Modo busca de elemento - usar esperar_elemento existente
        return esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
    
    # Estratégia especial para botões PJe - tentar múltiplas variações
    if "movimentar processos" in seletor.lower():
        return _clicar_botao_movimentar(driver, timeout, log)
    
    # Estratégia especial para botão "Abrir tarefa do processo" - problema contextual no Mandado
    if seletor == 'button[mattooltip="Abre a tarefa do processo"]':
        return _clicar_botao_tarefa_processo(driver, timeout, log)
    
    # Modo click original
    if usar_js and by == By.CSS_SELECTOR:
        try:
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
                status = "✅" if resultado else "❌"
                print(f"{status} aguardar_e_clicar JS: {seletor}")
            return resultado
        except Exception as e:
            if log:
                print(f"⚠️ aguardar_e_clicar JS falhou: {e}")
            # Fallback para Python
            usar_js = False
    
    # Fallback Python (ou escolha explícita) - usar safe_click existente
    if not usar_js:
        elemento = esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
        if elemento:
            try:
                elemento.click()
                if log:
                    print(f"✅ aguardar_e_clicar (Python): {seletor}")
                return True
            except Exception as e:
                if log:
                    print(f"❌ aguardar_e_clicar click falhou: {e}")
                return False
        else:
            if log:
                print(f"❌ aguardar_e_clicar elemento não encontrado: {seletor}")
            return False


def _clicar_botao_movimentar(driver, timeout=10, log=False):
    """
    Estratégia especializada para clicar no botão "Movimentar processos" do PJe
    Usa apenas seletores XPath válidos que funcionam
    """
    seletores_prioridade = [
        # Prioridade máxima: seletor funcional validado
        "button.mat-raised-button",
        # XPath de fallback
        "//button[.//span[contains(text(),'Movimentar processos')]]",
        "//button[contains(., 'Movimentar processos')]",
    ]

    for seletor in seletores_prioridade:
        try:
            if log:
                print(f" Tentando seletor: {seletor}")

            if "//" in seletor or "contains(" in seletor:
                by_type = By.XPATH
            else:
                by_type = By.CSS_SELECTOR

            elemento = esperar_elemento(driver, seletor, timeout=min(timeout, 8), by=by_type, log=False)
            if elemento:
                elemento.click()
                if log:
                    print(f"✅ Botão 'Movimentar processos' clicado com: {seletor}")
                time.sleep(0.5)
                return True

        except Exception as e:
            if log:
                print(f"⚠️ Seletor {seletor} falhou: {e}")
            continue

    if log:
        print("❌ Todos os seletores para 'Movimentar processos' falharam")
    return False


def _clicar_botao_tarefa_processo(driver, timeout=10, log=False):
    """
    Estratégia especializada para clicar no botão "Abrir tarefa do processo" do PJe
    Problema: Falha no contexto Mandado após buscar_documento_argos, mas funciona no Prazo
    Solução: Verificar overlays, tentar múltiplas abordagens de clique
    """
    seletor = 'button[mattooltip="Abre a tarefa do processo"]'
    
    try:
        # Passo 1: Aguardar elemento aparecer
        elemento = esperar_elemento(driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, log=log)
        if not elemento:
            if log:
                print("❌ Botão 'Abrir tarefa do processo' não encontrado")
            return False
        
        if log:
            print("✅ Botão 'Abrir tarefa do processo' encontrado")
        
        # Passo 2: Verificar se há overlays que podem interceptar o clique
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-overlay-transparent-backdrop, .mat-menu-panel')
            if overlays:
                if log:
                    print(f"⚠️ {len(overlays)} overlay(s) detectado(s) - aguardando desaparecer...")
                # Aguardar overlays desaparecerem
                WebDriverWait(driver, 5).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-overlay-transparent-backdrop, .mat-menu-panel')) == 0
                )
                if log:
                    print("✅ Overlays desapareceram")
        except Exception as e:
            if log:
                print(f"⚠️ Erro ao verificar overlays: {e}")
        
        # Passo 3: Scroll para o elemento
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", elemento)
            time.sleep(0.5)
        except Exception as e:
            if log:
                print(f"⚠️ Erro no scroll: {e}")
        
        # Passo 4: Tentar clique direto primeiro
        try:
            elemento.click()
            if log:
                print("✅ Clique direto no botão 'Abrir tarefa do processo' realizado")
            time.sleep(1)  # Aguardar navegação
            return True
        except ElementClickInterceptedException:
            if log:
                print("⚠️ Clique interceptado - tentando alternativas...")
        except Exception as e:
            if log:
                print(f"⚠️ Clique direto falhou: {e}")
        
        # Passo 5: Tentar JavaScript click
        try:
            driver.execute_script("arguments[0].click();", elemento)
            if log:
                print("✅ JavaScript click no botão 'Abrir tarefa do processo' realizado")
            time.sleep(1)
            return True
        except Exception as e:
            if log:
                print(f"⚠️ JavaScript click falhou: {e}")
        
        # Passo 6: Tentar ActionChains com move e click
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            actions.move_to_element(elemento).click().perform()
            if log:
                print("✅ ActionChains click no botão 'Abrir tarefa do processo' realizado")
            time.sleep(1)
            return True
        except Exception as e:
            if log:
                print(f"⚠️ ActionChains click falhou: {e}")
        
        # Passo 7: Último recurso - tentar parent element se existir
        try:
            parent = elemento.find_element(By.XPATH, "./ancestor::button[1]") if elemento != elemento.find_element(By.XPATH, "./ancestor::button[1]") else elemento
            if parent != elemento:
                parent.click()
                if log:
                    print("✅ Clique no parent button realizado")
                time.sleep(1)
                return True
        except Exception as e:
            if log:
                print(f"⚠️ Parent click falhou: {e}")
        
        if log:
            print("❌ Todas as estratégias para 'Abrir tarefa do processo' falharam")
        return False
        
    except Exception as e:
        if log:
            print(f"❌ Erro geral no _clicar_botao_tarefa_processo: {e}")
        return False



def selecionar_opcao(driver, seletor_dropdown, texto_opcao, timeout=10, exato=False, log=False):
    """
    Abre dropdown e seleciona opção por texto (1 script vs 5+ requisições)
    Padrão repetitivo consolidado: click dropdown + wait options + click option

    MELHORADO: Baseado no código original ORIGINAIS/loop.py + inspiração do a.py validado
    Usa múltiplas estratégias para localizar dropdown e opções, mantendo mínimo de requisições.

    Args:
        driver: WebDriver Selenium
        seletor_dropdown: Seletor CSS do dropdown OU nome conhecido do dropdown:
            - None: auto-detecção automática
            - CSS selector: seletor direto (ex: 'mat-select[formcontrolname="destinos"]')
            - Nome conhecido: 'destino', 'fase', 'tipo', 'tarefa', 'situacao', etc.
        texto_opcao: Texto da opção a selecionar
        timeout: Timeout em segundos
        exato: Se True, texto deve ser exato; se False, usa contains
        log: Ativa logging

    Returns:
        True se selecionou, False caso contrário

    Exemplos:
        # Auto-detecção
        selecionar_opcao(driver, None, 'Análise')

        # Seletor CSS direto
        selecionar_opcao(driver, 'mat-select[formcontrolname="destinos"]', 'Transferir valor')

        # Nome conhecido (mais genérico)
        selecionar_opcao(driver, 'destino', 'Análise')
        selecionar_opcao(driver, 'fase', 'Execução')
        selecionar_opcao(driver, 'tipo', 'Geral')
    """
    # MAPEAMENTO DE NOMES CONHECIDOS PARA SELETORES CSS
    # Permite usar nomes genéricos em vez de seletores específicos
    mapeamento_dropdowns = {
        'destino': [
            'mat-select[aria-placeholder*="destino"]'
        ],
        'fase': [
            'mat-select[formcontrolname="fpglobal_faseProcessual"]',
            'mat-select[placeholder*="Fase processual"]',
            'mat-select[aria-label*="Fase"]'
        ],
        'tipo': [
            'mat-select[formcontrolname="tipoCredito"]',
            'mat-select[formcontrolname="tipo"]',
            'mat-select[aria-label*="Tipo"]'
        ],
        'tarefa': [
            'mat-select[formcontrolname="tarefa"]',
            'mat-select[aria-label*="Tarefa"]',
            'mat-select[placeholder*="Tarefa"]'
        ],
        'situacao': [
            'mat-select[formcontrolname="situacao"]',
            'mat-select[aria-label*="Situação"]',
            'mat-select[placeholder*="Situação"]'
        ],
        'prioridade': [
            'mat-select[formcontrolname="prioridade"]',
            'mat-select[aria-label*="Prioridade"]'
        ],
        'status': [
            'mat-select[formcontrolname="status"]',
            'mat-select[aria-label*="Status"]'
        ]
    }

    # RESOLVE SELETOR: Converte nome conhecido em lista de seletores CSS
    if isinstance(seletor_dropdown, str) and seletor_dropdown in mapeamento_dropdowns:
        # Nome conhecido -> lista de seletores possíveis
        seletores_possiveis = mapeamento_dropdowns[seletor_dropdown]
        if log:
            print(f"[SELECIONAR_OPCAO] Nome conhecido '{seletor_dropdown}' -> tentando {len(seletores_possiveis)} seletores")
    elif isinstance(seletor_dropdown, str):
        # Seletor CSS direto -> lista com um item
        seletores_possiveis = [seletor_dropdown]
    else:
        # None ou inválido -> manter como None para auto-detecção
        seletores_possiveis = None

    try:
        # AUTO-DETECÇÃO: Se seletor_dropdown for None ou não resolveu para seletores
        # ✅ FUNCIONANDO BEM - Manter esta lógica principal
        if seletores_possiveis is None:
            if log:
                print(f"[SELECIONAR_OPCAO] Auto-detecção ativada para '{texto_opcao}'")

            # Estratégias de auto-detecção em ordem de prioridade
            estrategias_auto = [
                'mat-select[formcontrolname="destinos"]',  # Padrão do código original
                'mat-select[aria-label*="Tarefa destino"]',  # Aria-label comum
                'mat-select[aria-label*="destino"]',  # Aria-label genérico
                'mat-select[placeholder*="destino"]',  # Placeholder
                'mat-select[formcontrolname*="destino"]',  # Formcontrolname parcial
                'mat-select'  # Último recurso: qualquer mat-select
            ]

            for seletor_auto in estrategias_auto:
                try:
                    if log:
                        print(f"[SELECIONAR_OPCAO] Tentando seletor auto-detectado: {seletor_auto}")

                    dropdown = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_auto))
                    )

                    # MELHORIA: Tentar múltiplas formas de abrir dropdown (inspiração do a.py)
                    dropdown_aberto = False

                    # Tentativa 1: Click direto
                    try:
                        dropdown.click()
                        time.sleep(0.5)
                        dropdown_aberto = True
                    except:
                        pass

                    # Tentativa 2: Focus + Enter (inspiração escolherOpcaoTeste2)
                    if not dropdown_aberto:
                        try:
                            driver.execute_script("arguments[0].focus();", dropdown)
                            dropdown.send_keys(Keys.ENTER)
                            time.sleep(0.5)
                            dropdown_aberto = True
                        except:
                            pass

                    # Tentativa 3: Focus + seta para baixo
                    if not dropdown_aberto:
                        try:
                            driver.execute_script("arguments[0].focus();", dropdown)
                            dropdown.send_keys(Keys.ARROW_DOWN)
                            time.sleep(0.5)
                            dropdown_aberto = True
                        except:
                            pass

                    if not dropdown_aberto:
                        continue

                    # MELHORIA: Aguardar opções aparecerem (inspiração esperarColecao do a.py)
                    try:
                        WebDriverWait(driver, 3).until(
                            lambda d: len(d.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"], option')) >= 1
                        )
                    except:
                        continue

                    # Procurar opção dentro do overlay ou painel
                    opcao_seletor = 'mat-option[role="option"] span.mat-option-text, option'
                    opcoes = driver.find_elements(By.CSS_SELECTOR, opcao_seletor)

                    for opcao in opcoes:
                        try:
                            texto = opcao.text.strip().lower()
                            if exato:
                                encontrado = texto == texto_opcao.lower()
                            else:
                                encontrado = texto_opcao.lower() in texto

                            if encontrado:
                                if log:
                                    print(f"[SELECIONAR_OPCAO] ✅ Opção '{texto_opcao}' selecionada via auto-detecção (seletor: {seletor_auto})")
                                opcao.click()
                                time.sleep(0.3)
                                return True
                        except StaleElementReferenceException:
                            continue

                    continue

                except Exception as e_auto:
                    if log:
                        print(f"[SELECIONAR_OPCAO] Seletor auto-detectado {seletor_auto} falhou: {e_auto}")
                    continue

            if log:
                print(f"[SELECIONAR_OPCAO] ❌ Auto-detecção falhou para '{texto_opcao}'")
            return False

        # SELEÇÃO POR SELETORES RESOLVIDOS: Tenta cada seletor possível
        # ✅ FUNCIONANDO BEM - Lógica aprimorada para nomes conhecidos
        for seletor_atual in seletores_possiveis:
            try:
                if log:
                    print(f"[SELECIONAR_OPCAO] Tentando seletor: {seletor_atual}")

                dropdown = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_atual))
                )

                # MELHORIA: Múltiplas tentativas de abrir dropdown
                dropdown_aberto = False

                # Tentativa 1: Click direto
                try:
                    dropdown.click()
                    time.sleep(0.5)
                    dropdown_aberto = True
                except:
                    pass

                # Tentativa 2: Focus + Enter
                if not dropdown_aberto:
                    try:
                        driver.execute_script("arguments[0].focus();", dropdown)
                        from selenium.webdriver.common.keys import Keys
                        dropdown.send_keys(Keys.ENTER)
                        time.sleep(0.5)
                        dropdown_aberto = True
                    except:
                        pass

                # Tentativa 3: Focus + seta para baixo
                if not dropdown_aberto:
                    try:
                        driver.execute_script("arguments[0].focus();", dropdown)
                        dropdown.send_keys(Keys.ARROW_DOWN)
                        time.sleep(0.5)
                        dropdown_aberto = True
                    except:
                        pass

                if not dropdown_aberto:
                    continue

                # MELHORIA: Aguardar opções aparecerem
                try:
                    WebDriverWait(driver, 3).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"], option')) >= 1
                    )
                except:
                    continue

                # Procurar opção usando seletor mais robusto (inspiração do a.py)
                opcao_seletor = 'mat-option[role="option"] span.mat-option-text, option'
                opcoes = driver.find_elements(By.CSS_SELECTOR, opcao_seletor)

                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if exato:
                            encontrado = texto == texto_opcao.lower()
                        else:
                            encontrado = texto_opcao.lower() in texto

                        if encontrado:
                            if log:
                                print(f"[SELECIONAR_OPCAO] ✅ Opção '{texto_opcao}' selecionada (seletor: {seletor_atual})")
                            opcao.click()
                            time.sleep(0.3)
                            return True
                    except StaleElementReferenceException:
                        continue

                continue

            except Exception as e_seletor:
                if log:
                    print(f"[SELECIONAR_OPCAO] Seletor {seletor_atual} falhou: {e_seletor}")
                continue

        # FALLBACK: Estratégia 2 (padrão do código original) - pode ser removida futuramente
        # ⚠️ PODE SER REMOVIDO - Esta lógica está duplicada na auto-detecção
        try:
            if log:
                print("[SELECIONAR_OPCAO] Tentando estratégia 2: formcontrolname='destinos'")

            select = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-select[formcontrolname="destinos"]'))
            )
            select.click()
            time.sleep(1)

            # Aguardar painel aparecer
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            painel = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, painel_selector))
            )

            # Procurar opção no painel
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if texto_opcao.lower() in texto:
                        driver.execute_script("arguments[0].click();", opcao)
                        if log:
                            print(f"[SELECIONAR_OPCAO] ✅ Opção '{texto_opcao}' selecionada via painel (estratégia 2)")
                        return True
                except Exception:
                    continue

        except Exception as e2:
            if log:
                print(f"[SELECIONAR_OPCAO] Estratégia 2 falhou: {e2}")

        # FALLBACK: Estratégia 3 (JavaScript direto) - pode ser simplificada
        # ⚠️ PODE SER SIMPLIFICADO - Script JS muito complexo
        try:
            if log:
                print("[SELECIONAR_OPCAO] Tentando estratégia 3: JavaScript direto")

            script = f"""
            try {{
                // Procurar dropdown por múltiplos seletores
                let dropdown = document.querySelector('{seletores_possiveis[0] if seletores_possiveis else "mat-select"}') ||
                              document.querySelector('mat-select[formcontrolname="destinos"]') ||
                              document.querySelector('mat-select[aria-label*="Tarefa destino"]') ||
                              document.querySelector('mat-select');

                if (dropdown) {{
                    dropdown.click();

                    // Aguardar opções aparecerem
                    setTimeout(() => {{
                        let opcoes = document.querySelectorAll('mat-option span.mat-option-text, .mat-option-text');
                        for (let opcao of opcoes) {{
                            let texto = opcao.textContent.trim().toLowerCase();
                            if (texto.includes('{texto_opcao.lower()}')) {{
                                opcao.click();
                                return true;
                            }}
                        }}

                        // Fallback: primeira opção
                        if (opcoes.length > 0) {{
                            opcoes[0].click();
                            return true;
                        }}
                    }}, 500);

                    return true;
                }}
                return false;
            }} catch(e) {{
                return false;
            }}
            """

            resultado = driver.execute_script(script)
            if resultado:
                if log:
                    print(f"[SELECIONAR_OPCAO] ✅ Opção '{texto_opcao}' selecionada via JavaScript (estratégia 3)")
                return True

        except Exception as e3:
            if log:
                print(f"[SELECIONAR_OPCAO] Estratégia 3 falhou: {e3}")

        if log:
            print(f"[SELECIONAR_OPCAO] ❌ Todas as estratégias falharam para '{texto_opcao}'")
        return False

    except Exception as e:
        if log:
            print(f"[SELECIONAR_OPCAO] ❌ Erro geral: {e}")
        return False



def preencher_campo(driver, seletor, valor, trigger_events=True, limpar=True, log=False):
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
    
    Returns:
        True se preencheu, False caso contrário
    
    Exemplo:
        # Ao invés de:
        # campo = driver.find_element(By.ID, 'nome')
        # campo.clear()
        # campo.send_keys('João')
        # campo.send_keys(Keys.TAB)
        
        # Usar:
        preencher_campo(driver, '#nome', 'João')
    """
    try:
        # Escapar valor para JavaScript
        valor_escapado = str(valor).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n")
        
        # execute_async_script: callback automático
        script = f"""
        {js_base()}
        const callback = arguments[arguments.length - 1];
        
        esperarElemento('{seletor}', 5000)
            .then(campo => {{
                if (!campo) {{
                    callback(false);
                    return;
                }}
                
                if ({str(limpar).lower()}) {{
                    campo.value = '';
                }}
                
                campo.value = '{valor_escapado}';
                
                if ({str(trigger_events).lower()}) {{
                    triggerEvent(campo, 'input');
                    triggerEvent(campo, 'change');
                    triggerEvent(campo, 'blur');
                }}
                
                callback(true);
            }})
            .catch(err => {{
                console.error('Erro preencher_campo:', err);
                callback(false);
            }});
        """
        
        resultado = driver.execute_async_script(script)
        if log:
            status = "✅" if resultado else "❌"
            # Garantir que o valor é string antes de fatiar (evita TypeError se for int/None)
            try:
                val_preview = str(valor)[:50]
            except Exception:
                val_preview = '[unrepresentable]'
            print(f"{status} preencher_campo: {seletor} = '{val_preview}'")
        return resultado
    except Exception as e:
        if log:
            print(f"⚠️ preencher_campo falhou: {e}")
        return False


def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    """Preenche todos os campos de prazo (input[type=text].mat-input-element) dentro do formulário."""
    try:
        form = wait(driver, '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form', timeout)
        if not form:
            if log:
                print('[Fix.core] Formulário de minuta/comunicação não encontrado.')
            return False
        
        inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="text"].mat-input-element')
        if not inputs:
            if log:
                print('[Fix.core] Nenhum campo de prazo encontrado.')
            return False
        
        for campo in inputs:
            driver.execute_script("arguments[0].focus();", campo)
            campo.clear()
            campo.send_keys(str(valor))
            driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
            driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
            
            if log:
                print(f'[Fix.core] Campo de prazo preenchido com {valor}')
        
        return True
    except Exception as e:
        if log:
            print(f'[Fix.core] Erro ao preencher campos de prazo: {e}')
        return False



def preencher_multiplos_campos(driver, campos_dict, log=False):
    """
    Preenche múltiplos campos em uma única operação JavaScript
    Otimização extra: N campos = 1 requisição (vs N requisições)

    Args:
        driver: WebDriver Selenium
        campos_dict: Dict {seletor: valor}
        log: Ativa logging

    Returns:
        Dict {seletor: True/False} indicando sucesso de cada campo

    Exemplo:
        resultado = preencher_multiplos_campos(driver, {
            '#nome': 'João Silva',
            '#email': 'joao@email.com',
            '#telefone': '11999999999'
        })
    """
    try:
        # Construir array JavaScript de campos
        campos_js = []
        for seletor, valor in campos_dict.items():
            valor_escapado = str(valor).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            campos_js.append(f"{{'seletor': '{seletor}', 'valor': '{valor_escapado}'}}")

        campos_array = "[" + ", ".join(campos_js) + "]"

        script = f"""
        {js_base()}

        let campos = {campos_array};
        let resultados = {{}};

        for (let campo of campos) {{
            try {{
                let elemento = document.querySelector(campo.seletor);
                if (elemento) {{
                    elemento.value = campo.valor;
                    triggerEvent(elemento, 'input');
                    triggerEvent(elemento, 'change');
                    resultados[campo.seletor] = true;
                }} else {{
                    resultados[campo.seletor] = false;
                }}
            }} catch(e) {{
                resultados[campo.seletor] = false;
            }}
        }}

        return resultados;
        """

        resultado = driver.execute_script(script)

        if log:
            for seletor, sucesso in resultado.items():
                status = "" if sucesso else ""
                print(f"{status} {seletor}")

        return resultado
    except Exception as e:
        if log:
            print(f" preencher_multiplos_campos falhou: {e}")
        return {seletor: False for seletor in campos_dict.keys()}


# ====================================================================
# SEÇÃO 7: CONFIGURAÇÃO DE DRIVERS E LOGIN (driver_config.py integrado)
# ====================================================================

# GECKODRIVER_PATH
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')

if not os.path.exists(GECKODRIVER_PATH):
    logger.warning(f'AVISO: Geckodriver não encontrado em {GECKODRIVER_PATH}')
else:
    logger.info(f'Geckodriver encontrado: {GECKODRIVER_PATH}')

# --- FUNÇÕES DE LOGIN ---


def com_retry(func, max_tentativas=3, backoff_base=2, log=False, *args, **kwargs):
    """
    Executa função com retry e backoff exponencial
    Padrão repetitivo consolidado: for tentativa + try/except + sleep
    
    Args:
        func: Função a executar
        max_tentativas: Número máximo de tentativas
        backoff_base: Base para cálculo exponencial (2^tentativa)
        log: Ativa logging
        *args, **kwargs: Argumentos para a função
    
    Returns:
        Resultado da função se sucesso, None se todas tentativas falharam
    
    Exemplo:
        # Ao invés de:
        # for tentativa in range(3):
        #     try:
        #         resultado = minha_funcao()
        #         if resultado: break
        #     except: time.sleep(2 ** tentativa)
        
        # Usar:
        resultado = com_retry(minha_funcao, max_tentativas=3)
    """
    import time
    
    for tentativa in range(max_tentativas):
        try:
            resultado = func(*args, **kwargs)
            if resultado or resultado == 0:  # Permite 0 como resultado válido
                if log:
                    print(f" com_retry: sucesso na tentativa {tentativa + 1}")
                return resultado
        except Exception as e:
            if log:
                print(f" com_retry tentativa {tentativa + 1}/{max_tentativas}: {e}")
            
            if tentativa < max_tentativas - 1:
                delay = backoff_base ** tentativa
                if log:
                    print(f"⏳ Aguardando {delay}s antes da próxima tentativa...")
                time.sleep(delay)
            else:
                if log:
                    print(f" com_retry: todas {max_tentativas} tentativas falharam")
                return None
    
    return None



def escolher_opcao_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """
    DEPRECATED: Use selecionar_opcao() ou aguardar_e_clicar() para melhor performance
    Mantido apenas para compatibilidade com código legado
    
    Tenta múltiplos seletores com early return na primeira que funcionar
    Reduz código repetitivo de tentativas múltiplas
    
    Args:
        driver: WebDriver Selenium
        valor: Valor a procurar (texto, id, etc)
        estrategias_custom: Lista de tuplas (By, seletor) customizadas
        debug: Ativa logging detalhado
    
    Returns:
        True se encontrou e clicou, False caso contrário
    """
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
        (By.XPATH, f"//*[contains(text(), '{valor}')]"),
    ]
    
    for by, seletor in estrategias:
        try:
            elem = driver.find_element(by, seletor)
            elem.click()
            if debug:
                print(f" Seletor {by} funcionou para '{valor}'")
            return True
        except (NoSuchElementException, TimeoutException):
            if debug:
                print(f" Seletor {by} falhou")
            continue
        except Exception as e:
            if debug:
                print(f" Erro inesperado em {by}: {e}")
            continue
    
    if debug:
        print(f" NENHUM seletor funcionou para: '{valor}'")
    return False



def encontrar_elemento_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """
    Similar a escolher_opcao_inteligente mas retorna o elemento ao invés de clicar
    
    Returns:
        WebElement se encontrou, None caso contrário
    """
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
    ]
    
    for by, seletor in estrategias:
        try:
            elem = driver.find_element(by, seletor)
            if debug:
                print(f" Encontrado com {by}")
            return elem
        except (NoSuchElementException, TimeoutException):
            continue
    
    if debug:
        print(f" Elemento não encontrado: '{valor}'")
    return None


# =============================
# COLETOR DE ERROS (ex-Core)
# =============================
class ErroCollector:
    """
    Coleta erros sem interromper execução
    Permite processar tudo e gerar relatório completo no final
    """
    
    def __init__(self):
        self.erros = []
        self.sucessos = []
    
    def registrar_erro(self, processo, erro, modulo=""):
        """Registra erro mas NÃO interrompe execução"""
        self.erros.append({
            'processo': processo,
            'erro': str(erro),
            'modulo': modulo,
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
        })
        print(f" Erro em {processo}: {str(erro)[:100]}")
    
    def registrar_sucesso(self, processo):
        """Registra processamento bem-sucedido"""
        self.sucessos.append(processo)
        print(f" Sucesso: {processo}")
    
    def gerar_relatorio(self):
        """Imprime relatório completo de execução"""
        total = len(self.sucessos) + len(self.erros)
        taxa_sucesso = (len(self.sucessos) / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print(" RELATÓRIO DE EXECUÇÃO")
        print("="*70)
        print(f"Total processados: {total}")
        print(f" Sucessos: {len(self.sucessos)} ({taxa_sucesso:.1f}%)")
        print(f" Erros: {len(self.erros)} ({100-taxa_sucesso:.1f}%)")
        
        if self.erros:
            print("\n" + "="*70)
            print("DETALHES DOS ERROS:")
            print("="*70)
            for erro in self.erros:
                print(f"\n Processo: {erro['processo']}")
                if erro['modulo']:
                    print(f"   Módulo: {erro['modulo']}")
                print(f"   Erro: {erro['erro'][:200]}")
                print(f"   Horário: {erro['timestamp']}")
        
        print("\n" + "="*70)
    
    def exportar_csv(self, arquivo='erros.csv'):
        """Exporta erros para CSV para análise posterior"""
        if not self.erros:
            print("Nenhum erro para exportar")
            return
        
        import csv
        with open(arquivo, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Processo', 'Módulo', 'Erro', 'Timestamp'])
            for erro in self.erros:
                writer.writerow([
                    erro['processo'],
                    erro['modulo'],
                    erro['erro'],
                    erro['timestamp']
                ])
        
        print(f" Erros exportados para: {arquivo}")
    
    def limpar(self):
        """Limpa todos os registros"""
        self.erros.clear()
        self.sucessos.clear()
    
    def tem_erros(self):
        """Verifica se há erros registrados"""
        return len(self.erros) > 0
    
    def get_taxa_sucesso(self):
        """Retorna taxa de sucesso em percentual"""
        total = len(self.sucessos) + len(self.erros)
        return (len(self.sucessos) / total * 100) if total > 0 else 0


# Instância global do coletor de erros
coletor_erros = ErroCollector()


# =============================
# BIBLIOTECA JAVASCRIPT BASE (MutationObserver Pattern)
# =============================

def js_base():
    """
    Funções JavaScript base usando MutationObserver (padrão gigs.py)
    Substitui polling Python por espera passiva no browser
    
    Funções disponíveis:
    - esperarElemento(seletor, timeout): Aguarda elemento aparecer
    - triggerEvent(elemento, tipo): Dispara evento (input, change, blur)
    - esperarOpcoes(seletor, timeout): Aguarda opções de dropdown
    
    Returns:
        String com código JavaScript pronto para execute_script/execute_async_script
    
    Exemplo:
        script = f"{js_base()}; return await esperarElemento('#meuId', 5000);"
        elemento = driver.execute_async_script(script)
    """
    # Usar implementação mais avançada do SISB se disponível
    try:
        from SISB.utils import criar_js_otimizado
        return criar_js_otimizado()
    except ImportError:
        # Fallback para implementação original
        return """
        function esperarElemento(seletor, timeout = 5000) {
            return new Promise(resolve => {
                let elemento = document.querySelector(seletor);
                let disabled = (elemento && elemento.disabled === undefined) ? false : elemento.disabled;
                if (elemento && !disabled) {
                    resolve(elemento);
                    return;
                }
                
                let observer = new MutationObserver(mutations => {
                    let elem = document.querySelector(seletor);
                    let disabled = (elem && elem.disabled === undefined) ? false : elem.disabled;
                    if (elem && !disabled) {
                        observer.disconnect();
                        resolve(elem);
                    }
                });
                
                observer.observe(document.body, { childList: true, subtree: true });
                setTimeout(() => { 
                    observer.disconnect(); 
                    resolve(null); 
                }, timeout);
            });
        }
        
        function triggerEvent(elemento, tipo) {
            if (!elemento) return;
            if ('createEvent' in document) {
                let evento = document.createEvent('HTMLEvents');
                evento.initEvent(tipo, true, true);
                elemento.dispatchEvent(evento);
            } else {
                elemento.dispatchEvent(new Event(tipo, { bubbles: true }));
            }
        }
        
        function esperarOpcoes(seletor = 'mat-option[role="option"]', timeout = 5000) {
            return new Promise(resolve => {
                let opcoes = document.querySelectorAll(seletor);
                if (opcoes.length > 0) {
                    resolve(opcoes);
                    return;
                }
                
                let observer = new MutationObserver(mutations => {
                    let opts = document.querySelectorAll(seletor);
                    if (opts.length > 0) {
                        observer.disconnect();
                        resolve(opts);
                    }
                });
                
                observer.observe(document.body, { childList: true, subtree: true });
                setTimeout(() => { 
                    observer.disconnect(); 
                    resolve([]); 
                }, timeout);
            });
        }
        """


# =============================
# FUNÇÕES CONSOLIDADAS PARAMETRIZÁVEIS
# =============================


def criar_driver_PC(headless=False):
    """Driver PC - Firefox Developer Edition com configurações otimizadas"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
    options = Options()
    if headless:
        options.add_argument('-headless')
    
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    options.set_preference("browser.cache.offline.enable", True)
    options.set_preference("network.http.use-cache", True)
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")
    
    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)  # Não reduzir velocidade de timers em background
    options.set_preference("dom.timeout.throttling_delay", 0)  # Não atrasar execução em abas inativas
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)  # Sem delay de budget
    options.set_preference("page.load.animation.disabled", True)  # Desabilitar animações de carregamento
    options.set_preference("dom.disable_window_move_resize", False)  # Permitir resize mesmo em background
    
    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_PC] Driver PC (Firefox Developer Edition) criado com sucesso")
    return driver


def criar_driver_VT(headless=False):
    """Driver VT - Perfil padrão"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
    
    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_VT] Driver VT criado com sucesso")
    return driver


def criar_driver_notebook(headless=False):
    """Driver Notebook - Firefox Developer Edition"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    
    USE_USER_PROFILE_NOTEBOOK = False
    if USE_USER_PROFILE_NOTEBOOK:
        options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
    
    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_NOTEBOOK] Driver NOTEBOOK criado com sucesso")
    return driver

# --- DRIVERS SISBAJUD ---

SISB_PROFILE_PC = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
SISB_PROFILE_NOTEBOOK = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'


def criar_driver_sisb_pc(headless=False):
    """Driver SISBAJUD - PC (Firefox Developer Edition com configurações robustas)"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
    
    options = Options()
    if headless:
        options.add_argument('--headless')
    
    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("startup.homepage_welcome_url", "about:blank")
    options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
    options.set_preference("browser.startup.page", 0)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    options.set_preference("browser.safebrowsing.enabled", False)
    options.set_preference("browser.safebrowsing.malware.enabled", False)
    options.set_preference("datareporting.healthreport.uploadEnabled", False)
    options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
    options.set_preference("toolkit.telemetry.enabled", False)
    
    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    try:
        if os.path.exists(SISB_PROFILE_PC):
            profile = FirefoxProfile(SISB_PROFILE_PC)
            options.profile = profile
            print(f"[DRIVER_SISB_PC] Usando perfil: {SISB_PROFILE_PC}")
        else:
            print(f"[DRIVER_SISB_PC] Perfil não encontrado: {SISB_PROFILE_PC}, usando perfil temporário")
    except Exception as e:
        print(f"[DRIVER_SISB_PC] Erro ao carregar perfil: {e}, usando perfil temporário")
    
    service = Service(executable_path=GECKODRIVER_PATH)
    
    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        print("[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition) criado com sucesso")
        return driver
    except Exception as e:
        print(f"[DRIVER_SISB_PC] Erro ao criar driver: {e}")
        try:
            options_fallback = Options()
            if headless:
                options_fallback.add_argument('--headless')
            options_fallback.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
            driver = webdriver.Firefox(service=service, options=options_fallback)
            driver.implicitly_wait(10)
            print("[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition - fallback) criado com sucesso")
            return driver
        except Exception as e2:
            print(f"[DRIVER_SISB_PC] Falha total ao criar driver: {e2}")
            return None


def criar_driver_sisb_notebook(headless=False):
    """Driver SISBAJUD - Notebook"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = SISB_PROFILE_NOTEBOOK
    
    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_SISB_NOTEBOOK] Driver SISBAJUD NOTEBOOK criado com sucesso")
    return driver

# --- SISTEMA DE COOKIES ---


def finalizar_driver(driver, log=True):
    """Finaliza o driver de forma segura, aguardando operações pendentes"""
    import time
    try:
        # Fecha todas as janelas exceto a principal
        if len(driver.window_handles) > 1:
            janela_principal = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(janela_principal)
        
        # Pequeno delay para operações pendentes
        time.sleep(0.5)
        
        # Fecha o driver
        driver.quit()
        
        if log:
            print('[DRIVER] Driver finalizado com sucesso')
        return True
    except Exception as e:
        if log:
            print(f'[DRIVER][AVISO] Erro ao finalizar driver: {e}')
        return False

# =========================
# EXTRAÇÃO DIRETA DE DOCUMENTOS PJE
# =========================


def salvar_cookies_sessao(driver, caminho_arquivo=None, info_extra=None):
    """Salva todos os cookies da sessão Selenium em um arquivo JSON"""
    try:
        cookies = driver.get_cookies()
        if not cookies:
            print('[COOKIES] Nenhum cookie encontrado para salvar.')
            return False
        
        if not caminho_arquivo:
            pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
            os.makedirs(pasta, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            info = f'_{info_extra}' if info_extra else ''
            caminho_arquivo = os.path.join(pasta, f'cookies_sessao{info}_{timestamp}.json')
        
        dados_cookies = {
            'timestamp': datetime.now().isoformat(),
            'url_base': driver.current_url,
            'cookies': cookies
        }
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_cookies, f, ensure_ascii=False, indent=2)
        print(f'[COOKIES] Cookies salvos em: {caminho_arquivo}')
        return True
    except Exception as e:
        print(f'[COOKIES][ERRO] Falha ao salvar cookies: {e}')
        return False


def credencial(tipo_driver='PC', tipo_login='CPF', headless=False, cpf=None, senha=None, url_login=None, max_idade_cookies=24):
    """
    Função unificada para criação de driver + login + gerenciamento de cookies.
    
    Args:
        tipo_driver (str): 'PC', 'VT', 'notebook', 'sisb_pc', 'sisb_notebook'
        tipo_login (str): 'PC' (certificado) ou 'CPF' (cpf/senha)
        headless (bool): Executar em modo headless
        cpf (str): CPF para login (se tipo_login='CPF')
        senha (str): Senha para login (se tipo_login='CPF')
        url_login (str): URL de login customizada
        max_idade_cookies (int): Idade máxima dos cookies em horas
    
    Returns:
        driver: Driver configurado e logado, ou None se falhar
    """
    try:
        # 1. CRIAR DRIVER baseado no tipo
        print(f"[CREDENCIAL] Criando driver tipo: {tipo_driver}")
        
        if tipo_driver.upper() == 'PC':
            driver = criar_driver_PC(headless=headless)
        elif tipo_driver.upper() == 'VT':
            driver = criar_driver_VT(headless=headless)
        elif tipo_driver.lower() == 'notebook':
            driver = criar_driver_notebook(headless=headless)
        elif tipo_driver.lower() == 'sisb_pc':
            driver = criar_driver_sisb_pc(headless=headless)
        elif tipo_driver.lower() == 'sisb_notebook':
            driver = criar_driver_sisb_notebook(headless=headless)
        else:
            print(f"[CREDENCIAL] ❌ Tipo de driver inválido: {tipo_driver}")
            return None
        
        if not driver:
            print("[CREDENCIAL] ❌ Falha ao criar driver")
            return None
        
        print(f"[CREDENCIAL] ✅ Driver {tipo_driver} criado")
        
        # 2. CARREGAR COOKIES (sempre ativo)
        print("[CREDENCIAL] Tentando carregar cookies existentes...")
        cookies_carregados = carregar_cookies_sessao(driver, max_idade_horas=max_idade_cookies)
        
        if cookies_carregados:
            print("[CREDENCIAL] ✅ Cookies carregados - login desnecessário")
            return driver
        
        # 3. FAZER LOGIN baseado no tipo
        print(f"[CREDENCIAL] Fazendo login tipo: {tipo_login}")
        
        if tipo_login.upper() == 'PC':
            # Login por certificado
            from Fix.utils import login_pc
            sucesso_login = login_pc(driver)
            
        elif tipo_login.upper() == 'CPF':
            # Login por CPF/senha
            from Fix.utils import login_cpf
            
            # Usar valores padrão se não fornecidos
            if not cpf:
                cpf = '35305203813'
            if not senha:
                senha = 'SpF59866'
            
            sucesso_login = login_cpf(
                driver, 
                url_login=url_login, 
                cpf=cpf, 
                senha=senha, 
                aguardar_url_final=True
            )
        else:
            print(f"[CREDENCIAL] ❌ Tipo de login inválido: {tipo_login}")
            driver.quit()
            return None
        
        if not sucesso_login:
            print(f"[CREDENCIAL] ❌ Falha no login {tipo_login}")
            driver.quit()
            return None
        
        print(f"[CREDENCIAL] ✅ Login {tipo_login} realizado")
        
        # 4. SALVAR COOKIES (sempre ativo)
        print("[CREDENCIAL] Salvando cookies da sessão...")
        try:
            info_extra = f"credencial_{tipo_driver}_{tipo_login}"
            salvar_cookies_sessao(driver, info_extra=info_extra)
            print("[CREDENCIAL] ✅ Cookies salvos")
        except Exception as e:
            print(f"[CREDENCIAL] ⚠️ Erro ao salvar cookies: {e}")
        
        print("[CREDENCIAL] ✅ Processo completo finalizado")
        return driver
        
    except Exception as e:
        print(f"[CREDENCIAL] ❌ Erro geral: {e}")
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        return None


def carregar_cookies_sessao(driver, max_idade_horas=24):
    """Carrega cookies de sessão mais recentes e válidos automaticamente"""
    try:
        pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
        if not os.path.exists(pasta):
            print('[COOKIES] Pasta de cookies não encontrada.')
            return False
        
        import glob
        arquivos_cookies = glob.glob(os.path.join(pasta, 'cookies_sessao*.json'))
        if not arquivos_cookies:
            print('[COOKIES] Nenhum arquivo de cookies encontrado.')
            return False
        
        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados['cookies']
        else:
            from datetime import datetime
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados

        from datetime import datetime, timedelta
        timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.now() - timestamp_cookies

        if idade > timedelta(hours=max_idade_horas):
            print(f'[COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h). Pulando.')
            return False

        driver.get('https://pje.trt2.jus.br/primeirograu/')

        cookies_carregados = 0
        for cookie in cookies:
            try:
                cookie_limpo = {k: v for k, v in cookie.items() if k not in ['expiry', 'httpOnly', 'secure', 'sameSite']}
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
            except Exception as e:
                print(f'[COOKIES] Erro ao carregar cookie {cookie.get("name", "unknown")}: {e}')

        print(f'[COOKIES] {cookies_carregados} cookies carregados de {os.path.basename(arquivo_mais_recente)}')

        driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        time.sleep(3)

        if 'acesso-negado' in driver.current_url.lower():
            print('[COOKIES] URL de acesso negado detectada. Apagando cookies carregados.')
            try:
                driver.delete_all_cookies()
                print('[COOKIES] Cookies apagados do navegador.')
            except Exception as e:
                print(f'[COOKIES] Erro ao apagar cookies: {e}')
            return False
        
        if 'login' in driver.current_url.lower():
            print('[COOKIES] Cookies inválidos - ainda redirecionando para login.')
            return False
        else:
            logger.info('Cookies válidos! Login automático realizado.')
            return True
            
    except Exception as e:
        print(f'[COOKIES][ERRO] Falha ao carregar cookies: {e}')
        return False


def verificar_e_aplicar_cookies(driver):
    """Função integrada que verifica e aplica cookies automaticamente"""
    if not USAR_COOKIES_AUTOMATICO:
        return False
    
    print('[COOKIES] Tentando login automático via cookies salvos...')
    sucesso = carregar_cookies_sessao(driver)
    
    if sucesso:
        try:
            current_url = driver.current_url
            if 'acesso-negado' in current_url:
                logger.warning('Acesso negado detectado após aplicar cookies - forçando login CPF...')
                
                url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
                print(f"[COOKIES][LOGIN_FORCE] Navegando para: {url_login}")
                driver.get(url_login)
                time.sleep(1.2)
                
                try:
                    username_field = driver.find_element(By.NAME, 'username')
                    password_field = driver.find_element(By.NAME, 'password')
                    submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
                    
                    username_field.clear()
                    username_field.send_keys('35305203813')
                    time.sleep(0.3)
                    
                    password_field.clear()
                    password_field.send_keys('SpF59866')
                    time.sleep(0.3)
                    
                    submit_button.click()
                    time.sleep(3)
                    
                    if SALVAR_COOKIES_AUTOMATICO:
                        salvar_cookies_sessao(driver, info_extra='login_forcado_apos_acesso_negado')
                    
                    logger.info('Login forçado realizado após acesso negado!')
                    return True
                    
                except Exception as e:
                    print(f'[COOKIES][ERRO] Falha no login forçado: {e}')
                    return False
            else:
                logger.info('Login realizado via cookies! Pularemos a tela de login.')
        except Exception as e:
            print(f'[COOKIES][WARN] Erro ao verificar URL atual: {e}')
    else:
        logger.error('Cookies inválidos ou inexistentes. Login manual necessário.')
    
    return sucesso

# --- CONFIGURAÇÕES ATIVAS ---

# Configuração AutoHotkey
AHK_EXE_PC = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
AHK_SCRIPT_PC = r'D:\PjePlus\Login.ahk'
AHK_EXE_NOTEBOOK = r'C:\Users\s164283\Downloads\AHK\AutoHotkey64.exe'
AHK_SCRIPT_NOTEBOOK = r'C:\Users\s164283\Desktop\pjeplus\login.ahk'
AHK_EXE_ACTIVE = None
AHK_SCRIPT_ACTIVE = None

# Configuração de cookies
USAR_COOKIES_AUTOMATICO = True
SALVAR_COOKIES_AUTOMATICO = True

# Import local de funções de utils para evitar circular imports
from .utils import login_cpf, login_manual, login_automatico

# SELEÇÃO ATIVA (descomente apenas uma de cada)
login_func = login_cpf            # ← ATIVO: Login por CPF/senha
criar_driver = criar_driver_PC    # ← ATIVO: Driver PC (Firefox)
criar_driver_sisb = criar_driver_sisb_pc  # ← ATIVO: Driver SISBAJUD PC


def exibir_configuracao_ativa():
    """Exibe qual configuração está ativa"""
    login_nome = "Manual" if login_func == login_manual else "CPF" if login_func == login_cpf else "Automático"
    
    if criar_driver == criar_driver_PC:
        driver_nome = "PC"
    elif criar_driver == criar_driver_VT:
        driver_nome = "VT"
    else:
        driver_nome = "Notebook"
    
    print(f"[CONFIG] Login: {login_nome}")
    print(f"[CONFIG] Driver: {driver_nome}")
    return login_nome, driver_nome





def aplicar_filtro_100(driver):
    """
    Aplica filtro para exibir 100 itens por página no painel global.
    OTIMIZADO: Usa selecionar_opcao() + com_retry() - 1 requisição vs 8-12 anteriores.
    """
    from selenium.webdriver.common.by import By
    import time
    
    try:
        # Zoom out para facilitar cliques
        driver.execute_script("document.body.style.zoom='50%'")
        time.sleep(0.3)
        

        # Função interna para selecionar com múltiplos seletores
        def _selecionar():
            try:
                from selenium.webdriver.common.by import By
                span_20 = driver.find_element(By.XPATH, "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
                mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
                mat_select.click()
                time.sleep(0.5)
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                opcao_100 = overlay.find_element(By.XPATH, ".//mat-option[.//span[normalize-space(text())='100']]")
                opcao_100.click()
                time.sleep(1)
                print('[FILTRO_LISTA_100] Clique real na opção 100 confirmado.')
                return True
            except Exception as e:
                print(f'[FILTRO_LISTA_100][ERRO] Falha ao clicar em 100: {e}')
                return False

        # Aplica com retry automático
        resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)

        if resultado:
            logger.info('Filtro lista 100 aplicado')
        else:
            logger.error('Filtro lista 100 falhou após todas tentativas')

        return resultado
        
    except Exception as e:
        print(f'[FILTRO_LISTA_100][ERRO] Falha geral: {e}')
        return False


def filtro_fase(driver):
    """
    Seleciona fases 'Execução' e 'Liquidação' no filtro global.
    OTIMIZADO: Usa aguardar_e_clicar() + js_base() - 3 req vs 10-15 anteriores.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    import time
    
    try:
        seletor = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'
        
        # Abre dropdown com aguardar_e_clicar (MutationObserver)
        if not aguardar_e_clicar(driver, seletor, timeout=5, usar_js=True):
            print('[FILTRO_FASE][ERRO] Dropdown não encontrado.')
            return False
        
        time.sleep(0.3)
        
        # Seleciona ambas fases usando JavaScript (1 requisição)
        script = f"""
        {js_base()}
        
        const fases = ['Execução', 'Liquidação'];
        let sucesso = 0;
        
        for (const fase of fases) {{
            const opcao = Array.from(document.querySelectorAll('mat-option span.mat-option-text'))
                .find(el => el.textContent.trim() === fase);
            
            if (opcao && opcao.parentElement) {{
                opcao.parentElement.click();
                sucesso++;
            }}
        }}
        
        return sucesso;
        """
        
        selecionadas = driver.execute_script(script)
        
        if selecionadas != 2:
            print(f'[FILTRO_FASE][AVISO] Apenas {selecionadas}/2 fases selecionadas')
        
        # Fecha dropdown
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        
        logger.info('Filtro aplicado com sucesso!')
        return True
        
    except Exception as e:
        logger.error(f'Falha no filtro de fase: {e}')
        return False

def _aguardar_loader_painel(driver, timeout=10):
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
        print('[FILTRO] Loader não desapareceu dentro do timeout.')


def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                print('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            print('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            print('[ERRO] Painel de opções não apareceu.')
            return False
        # Aguardar opções reais aparecerem no painel
        opcoes = []
        for _ in range(20):
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            textos = [o.text.strip().lower() for o in opcoes if o.text.strip()]
            if any(fase in texto for fase in fases_alvo for texto in textos):
                break
            if textos and not any(t in ['nenhuma opção', 'carregando itens...'] for t in textos):
                break
            time.sleep(0.3)
        fases_clicadas = set()
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        print(f'[OK] Fase "{fase}" selecionada.')
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            print(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[OK] Fases selecionadas e filtro aplicado (botão filtrar).')
            time.sleep(1)
            _aguardar_loader_painel(driver)
        except Exception as e:
            print(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        # Generalização da seleção de tarefa
        if tarefas_alvo:
            print(f'Filtrando tarefa: {", ".join(tarefas_alvo).title()}...')
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(By.XPATH, f"//span[contains(text(), '{seletor_tarefa}')]")
            except Exception:
                try:
                    seletor = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                        if seletor_tarefa in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    print(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                    return False
            if not tarefa_element:
                print(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                return False
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            painel = None
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            if not painel or not painel.is_displayed():
                print('[ERRO] Painel de opções de tarefa não apareceu.')
                return False
            # Aguardar opções reais de tarefa aparecerem
            opcoes = []
            for _ in range(20):
                opcoes = painel.find_elements(By.XPATH, ".//mat-option")
                textos = [o.text.strip().lower() for o in opcoes if o.text.strip()]
                if any(tarefa.lower() in texto for tarefa in tarefas_alvo for texto in textos):
                    break
                if textos and not any(t in ['nenhuma opção', 'carregando itens...'] for t in textos):
                    break
                time.sleep(0.3)
            tarefas_clicadas = set()
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if tarefa.lower() in texto and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            print(f'[OK] Tarefa "{tarefa}" selecionada.')
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            if len(tarefas_clicadas) == 0:
                print(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                print('[OK] Tarefas selecionadas e filtro aplicado (botão filtrar).')
                time.sleep(1)
                _aguardar_loader_painel(driver)
            except Exception as e:
                print(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    return True

# Função para processar lista de processos

# =========================
# 3. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

# Função de espera robusta

def esperar_url_conter(driver, substring, timeout=10):
    """
    Espera até que a URL atual contenha a substring especificada.
    Args:
        driver: WebDriver instance
        substring: String a ser encontrada na URL
        timeout: Tempo máximo de espera em segundos
    Returns:
        bool: True se encontrou, False se timeout
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: substring in d.current_url
        )
        return True
    except TimeoutException:
        print(f'[URL][ERRO] Timeout esperando URL conter: "{substring}". URL atual: {driver.current_url}')
        return False
    except Exception as e:
        print(f'[URL][ERRO] Erro ao esperar URL: {e}')
        return False

def verificar_documento_decisao_sentenca(driver):
    """Verifica se existe um documento com 'decisão' ou 'sentença' no nome."""
    try:
        seletor_nomes_docs = 'pje-arvore-documento .node-content-wrapper span'
        nomes_docs = driver.find_elements(By.CSS_SELECTOR, seletor_nomes_docs)

        for nome_element in nomes_docs:
            doc_text = nome_element.text.lower()
            if 'decisão' in doc_text or 'sentença' in doc_text:
                print(f'[DOC CHECK] Documento encontrado: "{doc_text}"')
                return True

        print('[DOC CHECK] Nenhum documento de decisão/sentença encontrado.')
        return False
    except Exception as e:
        print(f'[DOC CHECK][ERRO] Falha ao verificar documentos: {e}')
        return False


def visibilidade_sigilosos(driver, polo='ativo', log=True):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente, conforme lógica do gigs-plugin.js.
    polo: 'ambos', 'ativo', 'passivo' ou 'nenhum'
    """
    try:
        # ✨ OTIMIZADO: Limpar overlays antes de buscar documento
        try:
            from Fix.headless_helpers import limpar_overlays_headless
            limpar_overlays_headless(driver)
        except ImportError:
            pass
        
        # 1. Seleciona o último documento sigiloso na timeline
        sigiloso_link = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline a.tl-documento.is-sigiloso:last-child')
        if not sigiloso_link:
            if log:
                print('[VISIBILIDADE][ERRO] Documento sigiloso não encontrado na timeline.')
            return False
        # Extrai id do documento
        aria_label = sigiloso_link.get_attribute('aria-label')
        import re
        m = re.search(r'Id[:\.\s]+([A-Za-z0-9]{6,8})', aria_label or '')
        if not m:
            if log:
                print('[VISIBILIDADE][ERRO] Não foi possível extrair o ID do documento.')
            return False
        id_documento = m.group(1)
        if log:
            print(f'[VISIBILIDADE] Documento sigiloso encontrado: {id_documento}')
        # 2. Ativa múltipla seleção
        btn_multi = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]')
        # ✨ OTIMIZADO: Click headless-safe
        try:
            btn_multi.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", btn_multi)
        time.sleep(0.5)
        # 3. Marca o checkbox do documento
        mat_checkbox = driver.find_element(By.CSS_SELECTOR, f'mat-card[id*="{id_documento}"] mat-checkbox label')
        # ✨ OTIMIZADO: Click headless-safe
        try:
            mat_checkbox.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", mat_checkbox)
        time.sleep(0.5)
        # 4. Clica no botão de visibilidade
        btn_visibilidade = driver.find_element(By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
        # ✨ OTIMIZADO: Click headless-safe
        try:
            btn_visibilidade.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", btn_visibilidade)
        time.sleep(1)
        # 5. No modal, seleciona o polo desejado
        if polo == 'ativo':
            icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo')
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'passivo':
            icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo')
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'ambos':
            # Marca todos
            btn_todos = driver.find_element(By.CSS_SELECTOR, 'th button')
            btn_todos.click()
        # 6. Confirma no botão Salvar
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
        )
        btn_salvar.click()
        time.sleep(1)
        # 7. Oculta múltipla seleção
        try:
            btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
            btn_ocultar.click()
        except:
            pass
        if log:
            print('[VISIBILIDADE] Visibilidade aplicada com sucesso.')
        return True
    except Exception as e:
        if log:
            print(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}')
        return False


def criar_botoes_detalhes(driver):
    """
    Cria botões com ícones e ações específicas, replicando a funcionalidade do MaisPje, usando o driver já autenticado.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        base_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pjextension_bt_detalhes_base"))
        )
    except:
        base_element = driver.find_element(By.TAG_NAME, "body")

    # Cria o container se não existir
    if not driver.find_elements(By.ID, "pjextension_bt_detalhes_base"):
        container = driver.execute_script(
            "var div = document.createElement('div');"
            "div.id = 'pjextension_bt_detalhes_base';"
            "div.style = 'float: left';"
            "div.setAttribute('role', 'toolbar');"
            "document.body.appendChild(div);"
            "return div;"
        )
    else:
        container = driver.find_element(By.ID, "pjextension_bt_detalhes_base")

    # Configuração dos botões
    buttons = [
        {"title": "Abrir o Gigs", "icon": "fa fa-tag", "action": "abrir_gigs"},
        {"title": "Expedientes", "icon": "fa fa-envelope", "action": "acao_botao_detalhes('Expedientes')"},
        {"title": "Lembretes", "icon": "fas fa-thumbtack", "action": "acao_botao_detalhes('Lembretes')"},
    ]

    for button in buttons:
        driver.execute_script(
            f"var a = document.createElement('a');"
            f"a.title = '{button['title']}';"
            f"a.style = 'cursor: pointer; position: relative; vertical-align: middle; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;';"
            f"a.onmouseover = function() {{ a.style.opacity = 0.5; }};"
            f"a.onmouseleave = function() {{ a.style.opacity = 1; }};"
            f"var i = document.createElement('i');"
            f"i.className = '{button['icon']}';"
            f"a.appendChild(i);"
            f"a.onclick = function() {{ {button['action']} }};"
            f"document.getElementById('pjextension_bt_detalhes_base').appendChild(a);"
        )
    driver.execute_script(
        "setTimeout(function() {"
        "  var div = document.getElementById('pjextension_bt_detalhes_base');"
        "  if (div) { div.style.display='none'; div.offsetHeight; div.style.display=''; }"
        "}, 100);"
    )

# =========================
# 11. FUNÇÕES DE BUSCA E PESQUISA
# =========================


def buscar_ultimo_mandado(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Retorna o texto do documento e seu tipo, ou None se não encontrado.
    """
    try:
        # Espera a timeline carregar
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                print('[MANDADO] Nenhum item encontrado na timeline.')
            return None, None

        # Procura pelo último documento do tipo 'mandado'
        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()

                # Verifica se é do tipo 'mandado'
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)

                    # Extrai o texto do documento
                    texto = item.text
                    if log:
                        print(f'[MANDADO] Documento encontrado: {doc_text}')
                    return texto, 'mandado'

            except Exception as e:
                if log:
                    print(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue

        if log:
            print('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None, None

    except Exception as e:
        if log:
            print(f'[MANDADO][ERRO] Falha geral: {e}')
        return None, None


def buscar_mandado_autor(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Após localizar, busca o ícone de martelo (gavel) e registra o autor: 'SILAS PASSOS' ou outro.
    Retorna um dicionário com texto, tipo e autor, ou None se não encontrado.
    """
    try:
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                print('[MANDADO] Nenhum item encontrado na timeline.')
            return None

        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)
                    texto = item.text
                    autor = 'DESCONHECIDO'
                    # Busca o ícone de martelo (gavel) e extrai o nome do autor
                    try:
                        gavel_icon = item.find_element(By.CSS_SELECTOR, 'i.fa-gavel, i.fas.fa-gavel')
                        # O nome do autor pode estar em um elemento próximo ao ícone
                        parent = gavel_icon.find_element(By.XPATH, './ancestor::*[1]')
                        autor_text = parent.text.strip().upper()
                        if 'SILAS PASSOS' in autor_text:
                            autor = 'SILAS PASSOS'
                        else:
                            autor = autor_text
                        if log:
                            print(f'[MANDADO] Autor identificado: {autor}')
                    except Exception:
                        if log:
                            print('[MANDADO] Ícone gavel ou autor não localizado.')
                    if log:
                        print(f'[MANDADO] Documento encontrado: {doc_text}')
                    return {'texto': texto, 'tipo': 'mandado', 'autor': autor}
            except Exception as e:
                if log:
                    print(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue
        if log:
            print('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None
    except Exception as e:
        if log:
            print(f'[MANDADO][ERRO] Falha geral: {e}')
        return None

# =========================
# 12. FUNÇÕES DE PROCESSAMENTO DE MINUTAS
# =========================

# =========================
# 13. FUNÇÕES DE GESTÃO DE COOKIES E SESSÃO
# =========================

# =========================
# 14. FUNÇÕES DE TRATAMENTO DE ERROS
# =========================

# =========================
# 15. FUNÇÕES DE VALIDAÇÃO E VERIFICAÇÃO
# =========================

# =========================
# 16. FUNÇÕES DE AUTOMAÇÃO DE INTERFACE
# =========================

# =========================
# 17. FUNÇÕES DE TRATAMENTO DE MODELOS
# =========================

# =========================
# 18. FUNÇÕES DE PROCESSAMENTO DE DOCUMENTOS
# =========================

# =========================
# 19. FUNÇÕES DE LOGGING E DEPURAÇÃO
# =========================

# =========================
def buscar_documentos_sequenciais(driver, log=True):
    """
    ✅ BUSCA DOCUMENTOS DO BLOCO ARGOS NA ORDEM CORRETA
    
    Bloco ARGOS (ordem cronológica - mais recente para mais antiga):
    0. Certidão de devolução (mais recente)
    1-3. Documentos do meio: certidão expedição, intimação, planilha
    4. Decisão (mais antiga - fim do bloco)
    
    IMPORTANTE: Intimação deve estar ENTRE certidão devolução e decisão
    """
    try:
        if log:
            print(f'[DOCUMENTOS_SEQUENCIAIS] Buscando documentos do bloco ARGOS')

        # Aguardar timeline
        time.sleep(2)
        elementos = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")
        
        if not elementos:
            if log:
                print('[DOCUMENTOS_SEQUENCIAIS][ERRO] Timeline vazia')
            return []
        
        # ETAPA 1: Encontrar certidão de devolução (início do bloco)
        idx_cert_devolucao = None
        for idx, elem in enumerate(elementos):
            texto = elem.text.strip().lower()
            if "certidão de devolução" in texto or "certidao de devolucao" in texto:
                idx_cert_devolucao = idx
                if log:
                    print(f'[DOCUMENTOS_SEQUENCIAIS] ✅ Encontrado: "Certidão de devolução" - {texto[:50]}...')
                break
        
        if idx_cert_devolucao is None:
            if log:
                print('[DOCUMENTOS_SEQUENCIAIS][ERRO] Certidão de devolução não encontrada')
            return []
        
        # ETAPA 2: Encontrar decisão (fim do bloco) APÓS certidão devolução
        idx_decisao = None
        for idx in range(idx_cert_devolucao + 1, len(elementos)):
            texto = elementos[idx].text.strip().lower()
            if "decisão(" in texto or "decisao(" in texto:
                idx_decisao = idx
                if log:
                    print(f'[DOCUMENTOS_SEQUENCIAIS] ✅ Encontrado: "Decisão" - {texto[:50]}...')
                break
        
        if idx_decisao is None:
            if log:
                print('[DOCUMENTOS_SEQUENCIAIS][ERRO] Decisão não encontrada após certidão')
            return []
        
        # ETAPA 3: Buscar documentos do meio APENAS entre certidão e decisão
        resultados = [elementos[idx_cert_devolucao]]  # Adicionar certidão
        
        tipos_meio = {
            'Certidão de expedição': ['certidão de expedição', 'certidao de expedicao'],
            'Planilha': ['planilha de atualização', 'planilha de atualizacao'],
            'Intimação': ['intimação(', 'intimacao(']
        }
        
        for idx in range(idx_cert_devolucao + 1, idx_decisao):
            elem = elementos[idx]
            texto = elem.text.strip().lower()
            
            for tipo_nome, palavras in tipos_meio.items():
                for palavra in palavras:
                    if palavra in texto:
                        resultados.append(elem)
                        if log:
                            print(f'[DOCUMENTOS_SEQUENCIAIS] ✅ Encontrado: "{tipo_nome}" - {texto[:50]}...')
                        break
        
        # ETAPA 4: Adicionar decisão (fim do bloco)
        resultados.append(elementos[idx_decisao])
        
        if log:
            print(f'[DOCUMENTOS_SEQUENCIAIS] ✅ RESULTADO: {len(resultados)} documentos encontrados (máximo 5)')
        
        return resultados
        
    except Exception as e:
        if log:
            print(f'[DOCUMENTOS_SEQUENCIAIS][ERRO] {str(e)}')
        return []


def buscar_documentos_polo_ativo(driver, data_decisao_str=None, debug=False):
    """
    Busca documentos do polo ativo (autor) na timeline.
    Retorna lista de dicionários com informações dos documentos encontrados.

    Args:
        driver: WebDriver do Selenium
        data_decisao_str: String da data da decisão (formato DD/MM/YYYY) - opcional
        debug: Se True, exibe logs detalhados

    Returns:
        list: Lista de dicionários com chaves 'data', 'nome', 'index'
    """
    try:
        if debug:
            print("[BUSCAR_DOCUMENTOS_POLO_ATIVO] Iniciando busca de documentos do polo ativo...")

        # Aguardar timeline carregar
        time.sleep(2)

        # Encontrar todos os itens da timeline
        elementos = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")

        if debug:
            print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] Encontrados {len(elementos)} itens na timeline")

        documentos_encontrados = []

        for idx, elemento in enumerate(elementos):
            try:
                # Verificar se é documento do polo ativo (autor)
                # Procurar por ícones ou indicadores do polo ativo
                polos_ativos = elemento.find_elements(By.CSS_SELECTOR, 'i.icone-polo-ativo, .polo-ativo, [aria-label*="Ativo"], [title*="Ativo"]')

                if not polos_ativos:
                    # Tentar outras formas de identificar polo ativo
                    texto_elemento = elemento.text.lower()
                    if 'autor' in texto_elemento or 'ativo' in texto_elemento:
                        pass  # Considerar como polo ativo
                    else:
                        continue  # Pular se não for polo ativo

                # Extrair nome do documento
                try:
                    link_doc = elemento.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                    nome_doc = link_doc.text.strip()
                except:
                    # Fallback: tentar pegar do texto geral
                    nome_doc = elemento.text.split('\n')[0].strip()

                # Extrair data do documento
                data_doc = ""
                try:
                    # Procurar por elementos de data na timeline
                    data_elements = elemento.find_elements(By.CSS_SELECTOR, '.tl-data, .data-documento, time, [datetime]')
                    if data_elements:
                        data_doc = data_elements[0].text.strip() or data_elements[0].get_attribute('datetime') or ""

                    # Se não encontrou, tentar extrair do texto
                    if not data_doc:
                        texto_completo = elemento.text
                        # Procurar padrões de data no texto
                        import re
                        padroes_data = [
                            r'(\d{1,2}/\d{1,2}/\d{4})',  # DD/MM/YYYY
                            r'(\d{1,2}\s+\w{3}\.?\s+\d{4})',  # DD MMM YYYY
                            r'(\d{4}-\d{2}-\d{2})'  # YYYY-MM-DD
                        ]

                        for padrao in padroes_data:
                            match = re.search(padrao, texto_completo)
                            if match:
                                data_doc = match.group(1)
                                break

                except Exception as e:
                    if debug:
                        print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] Erro ao extrair data do documento {idx}: {e}")

                # Adicionar documento encontrado
                if nome_doc:
                    doc_info = {
                        'data': data_doc,
                        'nome': nome_doc,
                        'index': idx
                    }
                    documentos_encontrados.append(doc_info)

                    if debug:
                        print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] Documento encontrado: {nome_doc} ({data_doc})")

            except Exception as e:
                if debug:
                    print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] Erro ao processar item {idx}: {e}")
                continue

        if debug:
            print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] Total de documentos do polo ativo encontrados: {len(documentos_encontrados)}")

        return documentos_encontrados

    except Exception as e:
        if debug:
            print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] Erro geral: {e}")
        return []

def _tentar_click_padrao(driver, element, log, attempt):
    """Estratégia 1: Click padrão."""
    try:
        if log and attempt == 0:
            print(f"[SAFE_CLICK] Tentando click padrão")
        element.click()
        if log:
            print(f"[SAFE_CLICK] Click bem sucedido!")
        return True
    except (ElementClickInterceptedException, ElementNotInteractableException, WebDriverException) as e:
        if log:
            print(f"[SAFE_CLICK] Click padrão falhou: {str(e)}")
        return False
    except:
        return False



def _tentar_click_javascript(driver, element, log):
    """Estratégia 2: JavaScript click."""
    try:
        if log:
            print(f"[SAFE_CLICK] Tentando click via JavaScript")
        driver.execute_script("arguments[0].click();", element)
        if log:
            print(f"[SAFE_CLICK] Click JavaScript bem sucedido!")
        return True
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Click JavaScript falhou: {str(e)}")
        return False



def _tentar_click_actionchains(driver, element, log):
    """Estratégia 3: ActionChains click."""
    try:
        if log:
            print(f"[SAFE_CLICK] Tentando click via ActionChains")
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()
        if log:
            print(f"[SAFE_CLICK] Click ActionChains bem sucedido!")
        return True
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Click ActionChains falhou: {str(e)}")
        return False



def _tentar_click_javascript_avancado(driver, element, log):
    """Estratégia 4: Advanced JavaScript click."""
    try:
        if log:
            print(f"[SAFE_CLICK] Tentando click JavaScript avançado")
        script = """
            var element = arguments[0];
            var e = document.createEvent('MouseEvents');
            e.initEvent('mousedown', true, true);
            element.dispatchEvent(e);
            e.initEvent('mouseup', true, true);
            element.dispatchEvent(e);
            e.initEvent('click', true, true);
            element.dispatchEvent(e);
            return true;
        """
        driver.execute_script(script, element)
        if log:
            print(f"[SAFE_CLICK] Click JavaScript avançado bem sucedido!")
        return True
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Click JavaScript avançado falhou: {str(e)}")
        return False


# ===================== FUNÇÕES CONSOLIDADAS PARA SISBAJUD =====================


# ===================== FUNÇÕES PARA ANÁLISE DE PRESCRIÇÃO =====================

def buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=None, debug=False):
    """
    Busca documentos na timeline do processo filtrando por polo ativo (autor/réu).

    Args:
        driver: Instância do WebDriver
        polo: "autor" ou "reu" (padrão: "autor")
        limite_dias: Se informado, filtra documentos dos últimos N dias
        debug: Se True, exibe logs detalhados

    Returns:
        list: Lista de dicionários com informações dos documentos encontrados
    """
    try:
        if debug:
            print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO]  Buscando documentos do polo {polo} na timeline...")

        # Aguardar timeline carregar
        esperar_elemento(driver, "li.tl-item-container", timeout=10)

        # Usar JavaScript para extrair dados da timeline de forma otimizada
        script = """
            var poloTarget = arguments[0];
            var limiteDias = arguments[1];

            // Função para determinar se é polo ativo baseado no texto
            function isPoloAtivo(texto, polo) {
                if (!texto) return false;

                texto = texto.toLowerCase();
                if (polo === 'autor') {
                    // Polo ativo para autor: contém "autor" mas não "réu" ou indica movimento do autor
                    return (texto.includes('autor') && !texto.includes('réu')) ||
                           texto.includes('reclamante') ||
                           texto.includes('exequente');
                } else if (polo === 'reu') {
                    // Polo ativo para réu: contém "réu" mas não "autor" ou indica movimento do réu
                    return (texto.includes('réu') && !texto.includes('autor')) ||
                           texto.includes('reclamado') ||
                           texto.includes('executado');
                }
                return false;
            }

            // Coletar todos os itens da timeline
            var itens = document.querySelectorAll('li.tl-item-container');
            var documentos = [];

            for (var i = 0; i < itens.length; i++) {
                var item = itens[i];

                try {
                    // Extrair data
                    var dataElement = item.querySelector('.tl-item-date');
                    var data = dataElement ? dataElement.textContent.trim() : '';

                    // Extrair título/ação
                    var tituloElement = item.querySelector('.tl-item-title, .tl-item-header');
                    var titulo = tituloElement ? tituloElement.textContent.trim() : '';

                    // Extrair descrição completa
                    var descElement = item.querySelector('.tl-item-description, .tl-item-content');
                    var descricao = descElement ? descElement.textContent.trim() : '';

                    // Combinar título e descrição para análise
                    var textoCompleto = (titulo + ' ' + descricao).toLowerCase();

                    // Verificar se é do polo ativo
                    if (isPoloAtivo(textoCompleto, poloTarget)) {
                        // Verificar limite de dias se informado
                        var documentoValido = true;
                        if (limiteDias) {
                            try {
                                var dataObj = new Date(data.split('/').reverse().join('-'));
                                var hoje = new Date();
                                var diffTime = Math.abs(hoje - dataObj);
                                var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                                if (diffDays > limiteDias) {
                                    documentoValido = false;
                                }
                            } catch (e) {
                                // Se não conseguir parsear data, considera válido
                                documentoValido = true;
                            }
                        }

                        if (documentoValido) {
                            documentos.push({
                                'data': data,
                                'titulo': titulo,
                                'descricao': descricao,
                                'texto_completo': textoCompleto,
                                'polo': poloTarget
                            });
                        }
                    }
                } catch (e) {
                    // Ignorar erros em itens individuais
                    continue;
                }
            }

            return documentos;
        """

        documentos = driver.execute_script(script, polo, limite_dias)

        if debug:
            print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] ✅ Encontrados {len(documentos)} documentos do polo {polo}")
        return documentos

    except Exception as e:
        if debug:
            print(f"[BUSCAR_DOCUMENTOS_POLO_ATIVO] ❌ Erro ao buscar documentos do polo ativo: {str(e)}")
        return []


def buscar_documento_argos(driver, log=True):
    """✅ CORRIGIDO: Busca PRÓXIMO documento (decisão/despacho) que contenha REGRAS ARGOS.

    Estratégia (mesma de checar_prox em p2b):
    1. Buscar todos os itens da timeline (despacho/decisão/sentença/conclusão)
    2. Manter índice persistente em atributo do driver
    3. A cada chamada, procurar NO ÍNDICE SEGUINTE (não refazer do zero)
    4. Verificar se documento contém REGRAS ARGOS
    5. Se contém, retornar; se não, avançar para próximo
    
    Retorna (texto, tipo) ou (None, None).
    """
    # Importar localmente para evitar import circular entre Fix.core <-> Fix.extracao
    try:
        from .extracao import extrair_direto, extrair_documento
    except Exception:
        # Fallback para import via package
        from Fix.extracao import extrair_direto, extrair_documento
    
    # ✅ REGRAS ARGOS que o documento deve conter
    REGRAS_ARGOS = [
        'defiro a instauração',
        'defiro a instauracao',  # Normalizado (sem acento)
        'argos',
        'realize-se a pesquisa infojud',
        'realize se a pesquisa infojud',  # Sem acento
    ]
    
    try:
        if log:
            print('[ARGOS][DOC] Buscando próximo documento com REGRAS ARGOS na timeline...')

        # ✨ USAR ÍNDICE PERSISTENTE (como em checar_prox)
        # Inicializar índice se não existir
        if not hasattr(driver, '_argos_doc_idx'):
            driver._argos_doc_idx = -1  # Começar em -1 para que primeira busca comece em 0
            if log:
                print('[ARGOS][DOC] Inicializando índice persistente')

        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            if log:
                print('[ARGOS][DOC] Nenhum item na timeline')
            return None, None

        # Localizar índice da primeira planilha (se houver) - LIMITE DE BUSCA
        planilha_idx = len(itens)  # Default: buscar até o final
        for i, it in enumerate(itens):
            try:
                link = it.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                txt = (link.text or '').lower()
                if 'planilha de atualização' in txt or 'planilha de atuali' in txt:
                    planilha_idx = i
                    break
            except Exception:
                continue

        # ✅ ITERAR A PARTIR DO PRÓXIMO ÍNDICE (como checar_prox faz)
        start_idx = driver._argos_doc_idx + 1
        if log:
            print(f'[ARGOS][DOC] Começando busca do índice {start_idx} (limite planilha: {planilha_idx})')

        for idx in range(start_idx, planilha_idx):
            try:
                item = itens[idx]
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = (link.text or '').lower()
                
                # ✅ Validar se é despacho/decisão/sentença/conclusão
                if not re.search(r'^(despacho|decisão|sentença|conclusão)', doc_text.strip()):
                    if log:
                        print(f'[ARGOS][DOC] Índice {idx}: "{doc_text[:30]}" - não é documento relevante, continuando...')
                    continue
                
                if log:
                    print(f'[ARGOS][DOC] Índice {idx}: "{doc_text[:50]}" - documento relevante encontrado, abrindo...')
                
            except Exception as e:
                if log:
                    print(f'[ARGOS][DOC] Erro ao validar elemento {idx}: {e}')
                continue
            
            # ✨ CLICAR NO DOCUMENTO
            try:
                try:
                    from Fix.headless_helpers import limpar_overlays_headless, scroll_to_element_safe
                    limpar_overlays_headless(driver)
                    scroll_to_element_safe(driver, link)
                    time.sleep(0.3)
                except ImportError:
                    pass
                
                # Tentar click normal primeiro
                try:
                    link.click()
                except ElementClickInterceptedException:
                    if log:
                        print(f'[ARGOS][DOC] Click intercepted, usando JS fallback')
                    driver.execute_script("arguments[0].click();", link)
                
                time.sleep(2)  # Aguardar carregamento
            except Exception as e:
                if log:
                    print(f'[ARGOS][DOC] Falha ao clicar no documento: {e}')
                continue

            # ✨ EXTRAIR TEXTO
            time.sleep(1.5)
            texto = None
            try:
                if log:
                    print('[ARGOS][DOC] Extraindo conteúdo...')
                resultado = extrair_direto(driver, timeout=10, debug=log, formatar=True)
                texto = resultado.get('conteudo') if resultado and resultado.get('sucesso') else None
            except Exception as e:
                if log:
                    print(f'[ARGOS][DOC] extrair_direto falhou: {e}')

            if not texto:
                try:
                    texto = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
                except Exception as e:
                    if log:
                        print(f'[ARGOS][DOC] extrair_documento falhou: {e}')
            
            # ✅ VERIFICAR REGRAS ARGOS
            if texto:
                if log:
                    print(f'[ARGOS][DOC] Texto extraído: {len(texto)} chars. Verificando regras...')
                
                texto_lower = texto.lower()
                encontrou_regra = False
                regra_encontrada = None
                
                # Verificar regras principais ARGOS
                for regra in REGRAS_ARGOS:
                    if regra in texto_lower:
                        encontrou_regra = True
                        regra_encontrada = regra
                        break
                
                # FALLBACK: Se não encontrou regra ARGOS mas tem sigilo, tratar como ARGOS
                if not encontrou_regra:
                    if 'este despacho permanecerá em sigilo' in texto_lower or \
                       'este despacho permanecera em sigilo' in texto_lower:
                        encontrou_regra = True
                        regra_encontrada = 'sigilo (fallback)'
                        if log:
                            print('[ARGOS][DOC] ℹ️ Encontrado sigilo - tratando como ARGOS')
                
                if encontrou_regra:
                    # ✅ SALVAR ÍNDICE ATUAL PARA PRÓXIMA BUSCA
                    driver._argos_doc_idx = idx
                    if log:
                        print(f'[ARGOS][DOC] ✅ REGRA "{regra_encontrada}" no índice {idx} - USANDO ESTE DOCUMENTO')
                    tipo = 'decisao' if 'decisão' in doc_text or 'sentença' in doc_text else 'despacho'
                    return texto, tipo
                else:
                    # REGRA NÃO ENCONTRADA - VOLTAR À TIMELINE E CONTINUAR COM PRÓXIMO
                    if log:
                        print(f'[ARGOS][DOC] ⚠️ Sem REGRA ARGOS no índice {idx} - voltando à timeline para próximo...')
                    
                    # ✅ VOLTAR À TIMELINE (fechar detalhe)
                    try:
                        driver.back()  # Usar back() para voltar à página anterior
                        time.sleep(1)  # Aguardar timeline recarregar
                    except Exception as back_err:
                        if log:
                            print(f'[ARGOS][DOC] Erro ao voltar: {back_err}')
                    
                    # Continuar para próxima iteração
                    continue
            else:
                if log:
                    print(f'[ARGOS][DOC] ⚠️ Falha ao extrair texto do índice {idx} - continuando...')
                
                # Voltar à timeline
                try:
                    driver.back()
                    time.sleep(1)
                except Exception:
                    pass
                
                continue

        # ✅ FIM: Nenhum documento teve regra
        if log:
            print('[ARGOS][DOC] ❌ Nenhum despacho/decisão com REGRAS ARGOS encontrado (fim da timeline)')
        return None, None

    except Exception as e:
        if log:
            print(f'[ARGOS][DOC][ERRO] buscar_documento_argos falhou: {e}')
        return None, None


# =============================
# SMART SLEEP - DELAYS INTELIGENTES
# =============================

class SimpleConfig:
    def __init__(self):
        self.stats = {'consecutive_errors': 0, 'total_actions': 0, 'rate_limit_detected': False}
        self.delays = {
            'default': 0.3,
            'click': 0.3,
            'navigation': 0.6,
            'form_fill': 0.8,
            'api_call': 1.0,
            'page_load': 2.0,
            'retry_base': 1.5,
        }
    
    def get_delay(self, t='default'):
        base = self.delays.get(t, 0.6)
        if self.stats['rate_limit_detected']:
            return base * 5.0
        elif self.stats['consecutive_errors'] > 5:
            return base * 3.0
        elif self.stats['consecutive_errors'] > 2:
            return base * 2.0
        return base

config = SimpleConfig()

def smart_sleep(t='default', multiplier=1.0):
    time.sleep(config.get_delay(t) * multiplier)

def sleep(ms):
    """Compatibilidade: converte milissegundos para segundos"""
    time.sleep(ms / 1000.0)


