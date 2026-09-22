# -*- coding: utf-8 -*-
"""
bianca/selenium_utils.py - Selenium WebDriver utility functions for PJe automation.

Extracted from Fix.core, Fix.browser_suporte, Fix.abas, Fix.headless_helpers.
Provides core interaction primitives used by triagem_engine and dom_engine.

Functions:
  esperar_elemento, safe_click, preencher_campo, selecionar_opcao,
  com_retry, buscar_seletor_robusto, aguardar_renderizacao_nativa,
  aplicar_filtro_100, filtrofases, resetar_driver,
  aguardar_e_clicar, safe_click_no_scroll, fechar_abas_extras,
  trocar_para_nova_aba, limpar_overlays_headless
"""

import time
import re
from typing import Any, Callable, Dict, List, Optional, Union

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)

from bianca.utils import logger


# =============================================================================
# JavaScript base helpers (MutationObserver pattern)
# =============================================================================

def js_base() -> str:
    """
    JavaScript utility functions using MutationObserver.

    Provides esperarElemento, triggerEvent, esperarOpcoes for
    async JS DOM waiting operations used by preencher_campo and
    aguardar_e_clicar.

    Returns:
        String with JavaScript code for execute_async_script.
    """
    return (
        """
    function esperarElemento(seletor, timeout) {
        timeout = timeout || 5000;
        return new Promise(function(resolve) {
            var elemento = document.querySelector(seletor);
            var disabled = (elemento && elemento.disabled === undefined)
                ? false : elemento.disabled;
            if (elemento && !disabled) {
                resolve(elemento);
                return;
            }
            var observer = new MutationObserver(function() {
                var elem = document.querySelector(seletor);
                var d = (elem && elem.disabled === undefined)
                    ? false : elem.disabled;
                if (elem && !d) {
                    observer.disconnect();
                    resolve(elem);
                }
            });
            observer.observe(document.body, {childList: true, subtree: true});
            setTimeout(function() {
                observer.disconnect();
                resolve(null);
            }, timeout);
        });
    }
    function triggerEvent(elemento, tipo) {
        if (!elemento) return;
        if ('createEvent' in document) {
            var e = document.createEvent('HTMLEvents');
            e.initEvent(tipo, true, true);
            elemento.dispatchEvent(e);
        } else {
            elemento.dispatchEvent(new Event(tipo, {bubbles: true}));
        }
    }
    function esperarOpcoes(seletor, timeout) {
        seletor = seletor || 'mat-option[role="option"]';
        timeout = timeout || 5000;
        return new Promise(function(resolve) {
            var opcoes = document.querySelectorAll(seletor);
            if (opcoes.length > 0) { resolve(opcoes); return; }
            var observer = new MutationObserver(function() {
                var opts = document.querySelectorAll(seletor);
                if (opts.length > 0) {
                    observer.disconnect();
                    resolve(opts);
                }
            });
            observer.observe(document.body, {childList: true, subtree: true});
            setTimeout(function() {
                observer.disconnect();
                resolve([]);
            }, timeout);
        });
    }
    """
    )


# =============================================================================
# Click helpers
# =============================================================================

def safe_click_no_scroll(driver: WebDriver, element: WebElement) -> bool:
    """
    Dispara click via JavaScript dispatchEvent sem scroll previo.

    Args:
        driver: WebDriver instance.
        element: Elemento alvo do clique.

    Returns:
        True se o clique foi disparado, False em caso de erro.
    """
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('click', "
            "{view: window, bubbles: true, cancelable: true}))",
            element,
        )
        return True
    except Exception as e:
        logger.debug("safe_click_no_scroll falhou: %s", e)
        return False


# =============================================================================
# Overlay / headless helpers
# =============================================================================

def limpar_overlays_headless(driver: WebDriver) -> bool:
    """
    Remove modals, tooltips e overlays que bloqueiam cliques.
    Executado via JavaScript para maxima confiabilidade.

    Returns:
        True se a limpeza foi executada com sucesso.
    """
    script = """
        try {
            document.querySelectorAll(
                '.modal-backdrop, .cdk-overlay-backdrop, .fade.show'
            ).forEach(function(el) { el.remove(); });

            document.querySelectorAll(
                '[role="tooltip"], .tooltip, .popover'
            ).forEach(function(el) { el.remove(); });

            document.querySelectorAll('.dropdown-menu.show')
                .forEach(function(el) { el.classList.remove('show'); });

            document.querySelectorAll('div[style*="z-index"]')
                .forEach(function(el) {
                    var z = parseInt(window.getComputedStyle(el).zIndex);
                    if (z > 1000) { el.style.display = 'none'; }
                });
            return true;
        } catch(e) { return false; }
    """
    try:
        driver.execute_script(script)
        return True
    except Exception as e:
        logger.warning("Nao foi possivel limpar overlays: %s", e)
        return False


# =============================================================================
# Wait / Render functions
# =============================================================================

def aguardar_renderizacao_nativa(
    driver: WebDriver,
    seletor: Optional[str] = None,
    modo: str = "aparecer",
    timeout: Union[int, float] = 10,
) -> bool:
    """
    Aguarda renderizacao e transicao de DOM.

    Args:
        driver: WebDriver Selenium.
        seletor: Se None, aguarda document.readyState == complete.
        modo: "aparecer" (default), "sumir" ou "habilitado".
        timeout: Tempo maximo de espera em segundos.

    Returns:
        True se a condicao foi satisfeita, False em timeout/erro.
    """

    def _coletar_elementos(web_driver: WebDriver) -> List[WebElement]:
        if not seletor:
            return []
        try:
            return web_driver.find_elements(By.CSS_SELECTOR, seletor)
        except Exception as e:
            logger.debug("_coletar_elementos: %s", e)
            return []

    def _elemento_visivel(element: WebElement) -> bool:
        try:
            return element.is_displayed()
        except Exception as e:
            logger.debug("_elemento_visivel: %s", e)
            return False

    timeout_segundos = float(timeout)

    try:
        if not seletor:
            WebDriverWait(driver, timeout_segundos).until(
                lambda d: d.execute_script("return document.readyState")
                == "complete"
            )
            return True

        if modo == "sumir":
            WebDriverWait(driver, timeout_segundos).until(
                lambda d: not any(
                    _elemento_visivel(el) for el in _coletar_elementos(d)
                )
            )
            return True

        if modo == "habilitado":
            WebDriverWait(driver, timeout_segundos).until(
                lambda d: any(
                    _elemento_visivel(el) and el.is_enabled()
                    for el in _coletar_elementos(d)
                )
            )
            return True

        # modo "aparecer" (default)
        WebDriverWait(driver, timeout_segundos).until(
            lambda d: any(
                _elemento_visivel(el) for el in _coletar_elementos(d)
            )
        )
        return True

    except TimeoutException:
        return False
    except Exception as e:
        logger.warning("aguardar_renderizacao_nativa: %s", e)
        return False


def esperar_elemento(
    driver: WebDriver,
    seletor: str,
    texto: Optional[str] = None,
    timeout: int = 10,
    by: By = By.CSS_SELECTOR,
    log: bool = False,
) -> Optional[WebElement]:
    """
    Espera ate que um elemento esteja presente (e opcionalmente contenha texto).

    Args:
        driver: WebDriver Selenium.
        seletor: Seletor CSS ou XPath.
        texto: Se fornecido, aguarda ate que o texto apareca no elemento.
        timeout: Tempo maximo de espera em segundos.
        by: Tipo do seletor (By.CSS_SELECTOR default).
        log: Ativa logging.

    Returns:
        WebElement se encontrado, None caso contrario.
    """
    try:
        if not isinstance(seletor, str):
            raise ValueError(
                f"Seletor deve ser string, recebido: {type(seletor)}"
            )

        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )

        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )

        if log:
            logger.debug("Elemento encontrado: '%s'", seletor)
        return el

    except TimeoutException:
        if log:
            logger.error("Timeout esperando elemento: '%s'", seletor)
        return None
    except Exception as e:
        if log:
            logger.error("Erro ao esperar elemento '%s': %s", seletor, e)
        return None


# =============================================================================
# Internal helpers for aguardar_e_clicar
# =============================================================================

def _aguardar_loader_painel(driver: WebDriver, timeout: int = 10) -> None:
    """Aguarda loader (mat-progress-bar) sumir antes de seguir."""
    loader_selector = ".mat-progress-bar-primary.mat-progress-bar-fill"
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, loader_selector)
            )
        )
    except TimeoutException:
        pass  # loader nunca apareceu, ok
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, loader_selector)
            )
        )
        time.sleep(0.3)
    except TimeoutException:
        logger.warning("Loader nao desapareceu dentro do timeout.")


def _clicar_botao_movimentar(
    driver: WebDriver, timeout: int = 10, log: bool = False
) -> bool:
    """Estrategia especializada para clicar em 'Movimentar processos'."""
    seletores = [
        "button.mat-raised-button",
        "//button[.//span[contains(text(),'Movimentar processos')]]",
        "//button[contains(., 'Movimentar processos')]",
    ]

    for sel in seletores:
        try:
            by_type = (
                By.XPATH if ("//" in sel or "contains(" in sel) else By.CSS_SELECTOR
            )
            elemento = esperar_elemento(
                driver, sel, timeout=min(timeout, 8), by=by_type
            )
            if elemento:
                elemento.click()
                if log:
                    logger.debug("Movimentar clicado com: %s", sel)
                time.sleep(0.5)
                return True
        except Exception as e:
            if log:
                logger.warning("Seletor '%s' falhou: %s", sel, e)
            continue

    if log:
        logger.error("Todas as estrategias para Movimentar falharam")
    return False


def _clicar_botao_tarefa_processo(
    driver: WebDriver, timeout: int = 10, log: bool = False
) -> bool:
    """Estrategia especializada para clicar em 'Abrir tarefa do processo'."""
    seletor = 'button[mattooltip="Abre a tarefa do processo"]'

    try:
        elemento = esperar_elemento(
            driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, log=log
        )
        if not elemento:
            if log:
                logger.error("Botao 'Abre a tarefa do processo' nao encontrado")
            return False

        # Verificar overlays
        try:
            overlays = driver.find_elements(
                By.CSS_SELECTOR,
                ".cdk-overlay-backdrop, .mat-overlay-transparent-backdrop, "
                ".mat-menu-panel",
            )
            if overlays:
                WebDriverWait(driver, 5).until(
                    lambda d: len(
                        d.find_elements(
                            By.CSS_SELECTOR,
                            ".cdk-overlay-backdrop, "
                            ".mat-overlay-transparent-backdrop, "
                            ".mat-menu-panel",
                        )
                    )
                    == 0
                )
        except Exception:
            pass

        # Scroll para o elemento
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                elemento,
            )
            time.sleep(0.5)
        except Exception:
            pass

        # Tentativa 1: click direto
        try:
            elemento.click()
            if log:
                logger.debug("Tarefa processo: clique direto ok")
            time.sleep(1)
            return True
        except ElementClickInterceptedException:
            if log:
                logger.debug("Tarefa processo: clique interceptado")
        except Exception:
            pass

        # Tentativa 2: JS click
        try:
            driver.execute_script("arguments[0].click();", elemento)
            if log:
                logger.debug("Tarefa processo: JS click ok")
            time.sleep(1)
            return True
        except Exception:
            pass

        # Tentativa 3: ActionChains
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            ActionChains(driver).move_to_element(elemento).click().perform()
            if log:
                logger.debug("Tarefa processo: ActionChains ok")
            time.sleep(1)
            return True
        except Exception:
            pass

        if log:
            logger.error("Todas as estrategias para tarefa processo falharam")
        return False

    except Exception as e:
        if log:
            logger.error("Erro em _clicar_botao_tarefa_processo: %s", e)
        return False


# =============================================================================
# aguardar_e_clicar
# =============================================================================

def aguardar_e_clicar(
    driver: WebDriver,
    seletor: str,
    log: bool = False,
    timeout: int = 10,
    by: By = By.CSS_SELECTOR,
    usar_js: bool = True,
    retornar_elemento: bool = False,
) -> Union[bool, Optional[WebElement]]:
    """
    Aguarda elemento aparecer e clica nele.

    Args:
        driver: WebDriver Selenium.
        seletor: Seletor CSS ou XPath.
        timeout: Timeout em segundos.
        by: Tipo do seletor (By.CSS_SELECTOR default).
        usar_js: Se True usa MutationObserver via JS.
        log: Ativa logging.
        retornar_elemento: Se True retorna o elemento em vez de bool.

    Returns:
        Se retornar_elemento=True: WebElement ou None.
        Se retornar_elemento=False: True se clicou, False caso contrario.
    """
    if retornar_elemento:
        return esperar_elemento(
            driver, seletor, timeout=timeout, by=by, log=log
        )

    # Estrategia especial para "Movimentar processos"
    if "movimentar processos" in seletor.lower():
        return _clicar_botao_movimentar(driver, timeout, log)

    # Estrategia especial para "Abre a tarefa do processo"
    if seletor == 'button[mattooltip="Abre a tarefa do processo"]':
        return _clicar_botao_tarefa_processo(driver, timeout, log)

    # Modo JS (async script com MutationObserver)
    if usar_js and by == By.CSS_SELECTOR:
        try:
            script = (
                js_base()
                + """
            var callback = arguments[arguments.length - 1];
            esperarElemento('"""
                + seletor
                + """', """
                + str(timeout * 1000)
                + """)
                .then(function(el) {
                    if (el) { el.click(); callback(true); }
                    else { callback(false); }
                })
                .catch(function(err) {
                    console.error('aguardar_e_clicar:', err);
                    callback(false);
                });
            """
            )
            resultado = driver.execute_async_script(script)
            if log:
                logger.debug(
                    "aguardar_e_clicar JS: %s -> %s", seletor, resultado
                )
            return bool(resultado)
        except Exception as e:
            if log:
                logger.warning("aguardar_e_clicar JS falhou: %s", e)
            usar_js = False  # fallback para Python

    # Fallback Python
    elemento = esperar_elemento(
        driver, seletor, timeout=timeout, by=by, log=log
    )
    if elemento:
        try:
            elemento.click()
            if log:
                logger.debug("aguardar_e_clicar (Python): %s", seletor)
            return True
        except Exception as e:
            if log:
                logger.warning("aguardar_e_clicar click falhou: %s", e)
            return False

    if log:
        logger.warning("aguardar_e_clicar elemento nao encontrado: %s", seletor)
    return False


# =============================================================================
# safe_click (com fallbacks)
# =============================================================================

def _safe_click_kz_fallback(driver: WebDriver, log: bool = False) -> bool:
    """Fallback para clicar no icone KZ (Detalhes do Processo)."""
    try:
        elemento = driver.find_element(
            By.CSS_SELECTOR,
            'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]',
        )
        driver.execute_script("arguments[0].click();", elemento)
        if log:
            logger.debug("KZ icon clicado (img)")
        return True
    except Exception:
        pass

    try:
        img = driver.find_element(
            By.CSS_SELECTOR,
            'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]',
        )
        button = img.find_element(By.XPATH, './ancestor::button[1]')
        driver.execute_script("arguments[0].click();", button)
        if log:
            logger.debug("KZ icon clicado (parent button)")
        return True
    except Exception as e:
        logger.debug("KZ fallback falhou: %s", e)
        return False


def safe_click(
    driver: WebDriver,
    selector_or_element: Union[str, WebElement],
    timeout: int = 10,
    by: Optional[By] = None,
    log: bool = False,
) -> bool:
    """
    Clica em elemento de forma segura, com fallbacks.

    Aceita selector (string) ou WebElement. Se selector string,
    primeiro encontra o elemento. Tenta JS click com fallback de zoom.

    Args:
        driver: WebDriver Selenium.
        selector_or_element: Seletor CSS ou WebElement.
        timeout: Timeout em segundos.
        by: Tipo do seletor (By.CSS_SELECTOR se None).
        log: Ativa logging.

    Returns:
        True se clicou com sucesso, False caso contrario.
    """
    if by is None:
        by = By.CSS_SELECTOR

    try:
        if isinstance(selector_or_element, str):
            elemento = esperar_elemento(
                driver, selector_or_element, timeout=timeout, by=by
            )
        else:
            elemento = selector_or_element

        if elemento is None:
            # Fallback para icone KZ (Detalhes do Processo)
            if isinstance(selector_or_element, str) and (
                "Detalhes do Processo" in selector_or_element
                or "detalhes do processo" in selector_or_element.lower()
            ):
                return _safe_click_kz_fallback(driver, log)
            if log:
                logger.error(
                    "Elemento nao encontrado: %s", selector_or_element
                )
            return False

        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                elemento,
            )
            driver.execute_script("arguments[0].click();", elemento)
            if log:
                logger.debug("Click via JS: %s", selector_or_element)
            return True
        except Exception as e_click:
            # Fallback: reduzir zoom e tentar novamente
            try:
                prev_zoom = driver.execute_script(
                    "return document.body.style.zoom || '';"
                )
                driver.execute_script("document.body.style.zoom = '60%';")
                time.sleep(0.12)
                driver.execute_script("arguments[0].click();", elemento)
                try:
                    driver.execute_script(
                        "document.body.style.zoom = '%s';" % prev_zoom
                    )
                except Exception:
                    pass
                if log:
                    logger.debug(
                        "Click com zoom reduzido: %s", selector_or_element
                    )
                return True
            except Exception as e_fallback:
                if log:
                    logger.error("Fallback click falhou: %s", e_fallback)
                try:
                    driver.execute_script(
                        "document.body.style.zoom = '%s';" % prev_zoom
                    )
                except Exception:
                    pass
                return False

    except Exception as e:
        if log:
            logger.error("safe_click falhou: %s", e)
        return False


# =============================================================================
# com_retry
# =============================================================================

def com_retry(
    func: Callable,
    max_tentativas: int = 3,
    backoff_base: float = 2,
    log: bool = False,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Executa funcao com retry e backoff exponencial.

    Args:
        func: Funcao a executar.
        max_tentativas: Numero maximo de tentativas.
        backoff_base: Base para calculo exponencial (2^tentativa).
        log: Ativa logging.
        *args, **kwargs: Argumentos para a funcao.

    Returns:
        Resultado da funcao se sucesso, None se todas falharam.
    """
    for tentativa in range(max_tentativas):
        try:
            resultado = func(*args, **kwargs)
            if resultado or resultado == 0:  # 0 e valido
                if log:
                    logger.debug(
                        "com_retry: sucesso na tentativa %d", tentativa + 1
                    )
                return resultado
        except Exception as e:
            if log:
                logger.warning(
                    "com_retry tentativa %d/%d: %s",
                    tentativa + 1,
                    max_tentativas,
                    e,
                )
            if tentativa < max_tentativas - 1:
                delay = backoff_base**tentativa
                if log:
                    logger.debug(
                        "com_retry: aguardando %ds...", delay
                    )
                time.sleep(delay)
            else:
                if log:
                    logger.error(
                        "com_retry: todas %d tentativas falharam",
                        max_tentativas,
                    )
                return None

    return None


# =============================================================================
# preencher_campo
# =============================================================================

def preencher_campo(
    driver: WebDriver,
    seletor: str,
    valor: str,
    trigger_events: bool = True,
    limpar: bool = True,
    log: bool = False,
) -> bool:
    """
    Preenche campo de formulario com triggers via JavaScript.

    Args:
        driver: WebDriver Selenium.
        seletor: Seletor CSS do campo.
        valor: Valor a preencher.
        trigger_events: Se True, dispara input/change/blur.
        limpar: Se True, limpa campo antes de preencher.
        log: Ativa logging.

    Returns:
        True se preencheu, False caso contrario.
    """
    try:
        valor_escapado = (
            str(valor)
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )

        script = (
            js_base()
            + """
        var callback = arguments[arguments.length - 1];
        esperarElemento('"""
            + seletor
            + """', 5000)
            .then(function(campo) {
                if (!campo) { callback(false); return; }
                var isTA = campo instanceof HTMLTextAreaElement;
                var proto = isTA ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                var setter = Object.getOwnPropertyDescriptor(proto, 'value') &&
                             Object.getOwnPropertyDescriptor(proto, 'value').set;
                if ("""
            + str(limpar).lower()
            + """) {
                    if (setter) setter.call(campo, '');
                    else campo.value = '';
                }
                if (setter) setter.call(campo, '"""
            + valor_escapado
            + """');
                else campo.value = '"""
            + valor_escapado
            + """';
                if ("""
            + str(trigger_events).lower()
            + """) {
                    triggerEvent(campo, 'input');
                    triggerEvent(campo, 'change');
                    triggerEvent(campo, 'blur');
                }
                callback(true);
            })
            .catch(function(err) {
                console.error('preencher_campo:', err);
                callback(false);
            });
        """
        )

        resultado = driver.execute_async_script(script)
        if log:
            val_preview = str(valor)[:50]
            logger.debug(
                "preencher_campo: %s = '%s' -> %s",
                seletor,
                val_preview,
                resultado,
            )
        return bool(resultado)

    except Exception as e:
        if log:
            logger.warning("preencher_campo falhou: %s", e)
        return False


# =============================================================================
# selecionar_opcao
# =============================================================================

def _abrir_e_selecionar_opcao(
    driver: WebDriver,
    dropdown: WebElement,
    texto_opcao: str,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Abre dropdown e seleciona opcao pelo texto."""
    dropdown_aberto = False

    for tentativa in range(3):
        try:
            if tentativa == 0:
                dropdown.click()
            elif tentativa == 1:
                driver.execute_script("arguments[0].focus();", dropdown)
                dropdown.send_keys(Keys.ENTER)
            else:
                driver.execute_script("arguments[0].focus();", dropdown)
                dropdown.send_keys(Keys.ARROW_DOWN)
            dropdown_aberto = True
            break
        except Exception:
            continue

    if not dropdown_aberto:
        return False

    try:
        WebDriverWait(driver, 3).until(
            lambda d: len(
                d.find_elements(
                    By.CSS_SELECTOR,
                    'mat-option[role="option"], option',
                )
            )
            >= 1
        )
    except Exception:
        return False

    opcoes = driver.find_elements(
        By.CSS_SELECTOR,
        'mat-option[role="option"] span.mat-option-text, option',
    )
    for opcao in opcoes:
        try:
            texto = opcao.text.strip().lower()
            if exato:
                encontrado = texto == texto_opcao.lower()
            else:
                encontrado = texto_opcao.lower() in texto
            if encontrado:
                opcao.click()
                time.sleep(0.3)
                if log:
                    logger.debug("Opcao '%s' selecionada", texto_opcao)
                return True
        except StaleElementReferenceException:
            continue

    return False


def _selecionar_opcao_auto(
    driver: WebDriver,
    texto_opcao: str,
    timeout: int = 10,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Auto-detecao de dropdown para selecionar_opcao."""
    estrategias = [
        'mat-select[formcontrolname="destinos"]',
        'mat-select[aria-label*="Tarefa destino"]',
        'mat-select[aria-label*="destino"]',
        'mat-select[placeholder*="destino"]',
        'mat-select[formcontrolname*="destino"]',
        "mat-select",
    ]

    for seletor_auto in estrategias:
        try:
            dropdown = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, seletor_auto)
                )
            )
            if _abrir_e_selecionar_opcao(
                driver, dropdown, texto_opcao, exato, log
            ):
                if log:
                    logger.debug(
                        "Auto-seletor '%s' funcionou", seletor_auto
                    )
                return True
        except Exception as e_auto:
            if log:
                logger.debug(
                    "Auto-seletor '%s' falhou: %s", seletor_auto, e_auto
                )
            continue

    if log:
        logger.error("Auto-detecao falhou para '%s'", texto_opcao)
    return False


def _selecionar_opcao_por_seletores(
    driver: WebDriver,
    texto_opcao: str,
    seletores: List[str],
    timeout: int = 10,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """Seleciona opcao tentando cada seletor da lista."""
    for seletor_atual in seletores:
        try:
            dropdown = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, seletor_atual)
                )
            )
            if _abrir_e_selecionar_opcao(
                driver, dropdown, texto_opcao, exato, log
            ):
                return True
        except Exception as e:
            if log:
                logger.debug(
                    "Seletor '%s' falhou: %s", seletor_atual, e
                )
            continue

    if log:
        logger.error(
            "Nenhum seletor funcionou para '%s'", texto_opcao
        )
    return False


def selecionar_opcao(
    driver: WebDriver,
    seletor_dropdown: Optional[str],
    texto_opcao: str,
    timeout: int = 10,
    exato: bool = False,
    log: bool = False,
) -> bool:
    """
    Abre dropdown e seleciona opcao por texto.

    Suporta:
    - seletor CSS direto (ex: 'mat-select[formcontrolname="destinos"]')
    - nomes conhecidos: 'destino', 'fase', 'tipo', 'tarefa', etc.
    - None: auto-detecao

    Args:
        driver: WebDriver Selenium.
        seletor_dropdown: Seletor CSS, nome conhecido ou None.
        texto_opcao: Texto da opcao a selecionar.
        timeout: Timeout em segundos.
        exato: Se True, texto deve ser exato; se False, usa contains.
        log: Ativa logging.

    Returns:
        True se selecionou, False caso contrario.
    """
    mapeamento = {
        "destino": ['mat-select[aria-placeholder*="destino"]'],
        "fase": [
            'mat-select[formcontrolname="fpglobal_faseProcessual"]',
            'mat-select[placeholder*="Fase processual"]',
            'mat-select[aria-label*="Fase"]',
        ],
        "tipo": [
            'mat-select[formcontrolname="tipoCredito"]',
            'mat-select[formcontrolname="tipo"]',
            'mat-select[aria-label*="Tipo"]',
        ],
        "tarefa": [
            'mat-select[formcontrolname="tarefa"]',
            'mat-select[aria-label*="Tarefa"]',
            'mat-select[placeholder*="Tarefa"]',
        ],
        "situacao": [
            'mat-select[formcontrolname="situacao"]',
            'mat-select[aria-label*="Situacao"]',
            'mat-select[placeholder*="Situacao"]',
        ],
        "prioridade": [
            'mat-select[formcontrolname="prioridade"]',
            'mat-select[aria-label*="Prioridade"]',
        ],
        "status": [
            'mat-select[formcontrolname="status"]',
            'mat-select[aria-label*="Status"]',
        ],
    }

    if isinstance(seletor_dropdown, str) and seletor_dropdown in mapeamento:
        seletores = mapeamento[seletor_dropdown]
    elif isinstance(seletor_dropdown, str):
        seletores = [seletor_dropdown]
    else:
        seletores = None

    try:
        if seletores is None:
            return _selecionar_opcao_auto(
                driver, texto_opcao, timeout, exato, log
            )

        return _selecionar_opcao_por_seletores(
            driver, texto_opcao, seletores, timeout, exato, log
        )

    except Exception as e:
        if log:
            logger.error("selecionar_opcao: %s", e)
        return False


# =============================================================================
# buscar_seletor_robusto
# =============================================================================

def buscar_seletor_robusto(
    driver: WebDriver,
    textos: List[str],
    contexto: Optional[str] = None,
    timeout: int = 5,
    log: bool = False,
) -> Optional[WebElement]:
    """
    Busca elemento por multiplas estrategias de seletor.

    Fases:
      1. Inputs diretos por placeholder/aria-label/name
      2. Busca por texto visivel + input associado
      3. Icones/fa

    Args:
        driver: WebDriver Selenium.
        textos: Lista de textos para busca.
        contexto: Contexto para logging (opcional).
        timeout: Timeout em segundos (reservado).
        log: Ativa logging.

    Returns:
        WebElement se encontrado, None caso contrario.
    """
    _ctx = f"[{contexto}] " if contexto else ""

    def _buscar_input_associado(
        elemento: WebElement,
    ) -> Optional[WebElement]:
        try:
            return elemento.find_element(
                By.XPATH,
                "./following-sibling::input|./preceding-sibling::input|"
                "./ancestor::*[contains(@class,'form-group')]//input|"
                "./ancestor::*[contains(@class,'mat-form-field')]//input",
            )
        except Exception as e:
            if log:
                logger.debug(
                    "%sFalha ao buscar input associado: %s", _ctx, e
                )
            return None

    # Fase 1: Inputs diretos
    for texto in textos:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                'input[placeholder*="%s"], '
                'input[aria-label*="%s"], '
                'input[name*="%s"]' % (texto, texto, texto),
            )
            for el in elementos:
                if el.is_displayed() and el.is_enabled():
                    if log:
                        logger.debug(
                            "%sInput direto encontrado: %s", _ctx, texto
                        )
                    return el
        except Exception as e:
            if log:
                logger.debug("%sFase1 erro: %s", _ctx, e)
            continue

    # Fase 2: Texto visivel + input associado
    for texto in textos:
        try:
            elementos = driver.find_elements(
                By.XPATH, '//*[contains(text(), "%s")]' % texto
            )
            for el in elementos:
                input_assoc = _buscar_input_associado(el)
                if input_assoc:
                    if log:
                        logger.debug(
                            "%sInput associado encontrado: %s", _ctx, texto
                        )
                    return input_assoc
        except Exception as e:
            if log:
                logger.debug("%sFase2 erro: %s", _ctx, e)
            continue

    # Fase 3: Icones/fa
    for texto in textos:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                'i[mattooltip*="%s"], i[aria-label*="%s"], i.fa-reply-all'
                % (texto, texto),
            )
            for el in elementos:
                if el.is_displayed():
                    if log:
                        logger.debug(
                            "%sIcone encontrado: %s", _ctx, texto
                        )
                    return el
        except Exception as e:
            if log:
                logger.debug("%sFase3 erro: %s", _ctx, e)
            continue

    if log:
        logger.debug(
            "%sNenhum elemento encontrado com os criterios.", _ctx
        )
    return None


# =============================================================================
# PJe-specific filters
# =============================================================================

def aplicar_filtro_100(driver: WebDriver) -> bool:
    """
    Aplica filtro para exibir 100 itens por pagina no painel global.

    Clica no mat-select mostrando "20" e seleciona a opcao "100".
    Usa com_retry com ate 3 tentativas.

    Returns:
        True se o filtro foi aplicado, False caso contrario.
    """

    def _selecionar() -> bool:
        try:
            span_20 = driver.find_element(
                By.XPATH,
                "//span[contains(@class,'mat-select-min-line') "
                "and normalize-space(text())='20']",
            )
            mat_select = span_20.find_element(
                By.XPATH, "ancestor::mat-select[@role='combobox']"
            )
            safe_click_no_scroll(driver, mat_select)
            aguardar_renderizacao_nativa(driver)

            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".cdk-overlay-pane")
                )
            )
            opcao_100 = overlay.find_element(
                By.XPATH,
                ".//mat-option[.//span[normalize-space(text())='100']]",
            )
            safe_click_no_scroll(driver, opcao_100)
            aguardar_renderizacao_nativa(driver)
            logger.debug("Clique na opcao 100 confirmado.")
            return True
        except Exception as e:
            logger.warning("Falha ao clicar em 100: %s", e)
            return False

    resultado = com_retry(
        _selecionar, max_tentativas=3, backoff_base=1.5, log=True
    )

    if resultado:
        logger.info("Filtro lista 100 aplicado")
    else:
        logger.error("Filtro lista 100 falhou apos todas tentativas")

    return resultado


def filtrofases(
    driver: WebDriver,
    fases_alvo: Optional[List[str]] = None,
    tarefas_alvo: Optional[List[str]] = None,
    seletor_tarefa: str = "Tarefa do processo",
) -> bool:
    """
    Aplica filtros de fase processual e tarefa no painel global.

    Args:
        driver: WebDriver Selenium.
        fases_alvo: Lista de fases (ex: ['liquidacao', 'execucao']).
                    Default: ['liquidacao', 'execucao'].
        tarefas_alvo: Lista de tarefas (opcional).
        seletor_tarefa: Texto do label da tarefa.

    Returns:
        True se filtros aplicados com sucesso.
    """
    if fases_alvo is None:
        fases_alvo = ["liquidacao", "execucao"]

    fases = [f.strip().capitalize() for f in fases_alvo]

    logger.info(
        "Filtrando fase processual: %s...", ", ".join(fases)
    )

    # 1. Filtro de fase processual
    try:
        seletor_fase = (
            'mat-select[formcontrolname="fpglobal_faseProcessual"], '
            'mat-select[placeholder*="Fase processual"]'
        )
        if not aguardar_e_clicar(
            driver, seletor_fase, timeout=5, usar_js=True
        ):
            logger.error("Dropdown de fase nao encontrado.")
            return False

        aguardar_renderizacao_nativa(driver)

        script_fases = """
        var fases = arguments[0];
        var sucesso = 0;
        for (var i = 0; i < fases.length; i++) {
            var opcoes = document.querySelectorAll(
                'mat-option span.mat-option-text'
            );
            for (var j = 0; j < opcoes.length; j++) {
                if (opcoes[j].textContent.trim() === fases[i]) {
                    opcoes[j].parentElement.click();
                    sucesso++;
                    break;
                }
            }
        }
        return sucesso;
        """
        selecionadas = driver.execute_script(script_fases, fases)
        if selecionadas < 1:
            logger.error(
                "Nao encontrou opcoes %s no painel.", fases_alvo
            )
            return False

        logger.debug(
            "%d/%d fases selecionadas.", selecionadas, len(fases)
        )
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        aguardar_renderizacao_nativa(driver)

    except Exception as e:
        logger.error("Erro no filtro de fase: %s", e)
        return False

    # 2. Filtro de tarefa (opcional)
    if tarefas_alvo:
        logger.info(
            "Filtrando tarefa: %s...", ", ".join(tarefas_alvo)
        )
        try:
            tarefa_element = None
            for xpath in [
                "//span[contains(text(), '%s')]" % seletor_tarefa,
                "//mat-label[contains(text(), 'Tarefa')]",
                "//label[contains(text(), 'Tarefa')]",
            ]:
                try:
                    tarefa_element = driver.find_element(By.XPATH, xpath)
                    if tarefa_element and tarefa_element.is_displayed():
                        break
                except Exception:
                    continue

            if not tarefa_element:
                logger.warning(
                    "Seletor de tarefa '%s' nao encontrado -- pulando.",
                    seletor_tarefa,
                )
            else:
                safe_click_no_scroll(driver, tarefa_element)
                aguardar_renderizacao_nativa(driver)

                script_tarefas = """
                var tarefas = arguments[0];
                var sucesso = 0;
                for (var i = 0; i < tarefas.length; i++) {
                    var opcoes = document.querySelectorAll(
                        'mat-option span.mat-option-text'
                    );
                    for (var j = 0; j < opcoes.length; j++) {
                        if (opcoes[j].textContent.trim().toLowerCase()
                            === tarefas[i].toLowerCase()) {
                            opcoes[j].parentElement.click();
                            sucesso++;
                            break;
                        }
                    }
                }
                return sucesso;
                """
                selecionadas = driver.execute_script(
                    script_tarefas, tarefas_alvo
                )
                if selecionadas < 1:
                    logger.warning(
                        "Nao encontrou opcoes %s no painel de tarefas.",
                        tarefas_alvo,
                    )
                else:
                    logger.debug(
                        "%d/%d tarefas selecionadas.",
                        selecionadas,
                        len(tarefas_alvo),
                    )
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                aguardar_renderizacao_nativa(driver)
        except Exception as e:
            logger.error("Erro no filtro de tarefa: %s", e)
            return False

    # 3. Clicar no botao de filtrar
    try:
        botao = driver.find_element(
            By.CSS_SELECTOR, "i.fas.fa-filter"
        )
        safe_click_no_scroll(driver, botao)
        logger.debug("Filtros aplicados.")
        _aguardar_loader_painel(driver)
    except Exception as e:
        logger.warning(
            "Nao conseguiu clicar no botao de filtrar: %s", e
        )

    logger.info("Filtros aplicados com sucesso.")
    return True


# =============================================================================
# Aba management
# =============================================================================

def fechar_abas_extras(
    driver: WebDriver, handle_principal: Optional[str] = None
) -> bool:
    """
    Fecha todas as abas abertas exceto a aba principal.

    Args:
        driver: WebDriver Selenium.
        handle_principal: Handle da aba a preservar.
                         Se None, usa a primeira aba disponivel.

    Returns:
        True se bem-sucedido, False em caso de erro.
    """
    try:
        abas = driver.window_handles
        if not abas:
            logger.warning("Nenhuma aba disponivel.")
            return False

        principal = handle_principal or abas[0]

        abas_extras = [h for h in abas if h != principal]
        if not abas_extras:
            logger.debug("Nenhuma aba extra para fechar.")
            return True

        logger.debug(
            "Fechando %d aba(s) extra(s)...", len(abas_extras)
        )

        for aba in abas_extras:
            try:
                driver.switch_to.window(aba)
                driver.close()
            except Exception as e:
                logger.warning("Erro ao fechar aba: %s", e)

        if principal in driver.window_handles:
            driver.switch_to.window(principal)
        else:
            restantes = driver.window_handles
            if restantes:
                driver.switch_to.window(restantes[0])

        logger.debug("Abas extras fechadas.")
        return True

    except Exception as e:
        logger.error("Erro ao fechar abas extras: %s", e)
        return False


def trocar_para_nova_aba(
    driver: WebDriver, aba_original: Optional[str] = None
) -> Optional[str]:
    """
    Troca para a aba mais recentemente aberta (diferente da original).

    Args:
        driver: WebDriver Selenium.
        aba_original: Handle da aba original.
                     Se None, usa driver.current_window_handle.

    Returns:
        Handle da nova aba se bem-sucedido, None caso contrario.
    """
    try:
        abas = driver.window_handles
        if not abas:
            logger.error("Nenhuma aba disponivel.")
            return None

        original = aba_original or driver.current_window_handle

        if len(abas) == 1 and abas[0] == original:
            logger.warning("Apenas a aba original disponivel.")
            return None

        novas = [h for h in abas if h != original]
        if not novas:
            logger.warning("Nenhuma nova aba encontrada.")
            return None

        nova_aba = novas[0]
        driver.switch_to.window(nova_aba)

        if driver.current_window_handle == nova_aba:
            try:
                url_atual = driver.current_url
                logger.debug(
                    "Nova aba aberta: %s",
                    url_atual[:60] if url_atual else "?",
                )
            except Exception:
                logger.debug("Nova aba aberta.")
            return nova_aba

        logger.warning("Falha na troca de aba.")
        return None

    except Exception as e:
        logger.error("Erro ao trocar de aba: %s", e)
        return None


# =============================================================================
# Driver management
# =============================================================================

def resetar_driver(driver: WebDriver) -> bool:
    """
    Reseta o driver entre modulos:
    - Fecha abas extras
    - Restaura zoom
    - Navega para pagina inicial do PJe

    Args:
        driver: WebDriver Selenium.

    Returns:
        True se resetado com sucesso, False caso contrario.
    """
    try:
        logger.debug("Resetando driver...")

        fechar_abas_extras(driver)

        try:
            driver.execute_script("document.body.style.zoom='100%'")
        except Exception as e:
            logger.warning("Erro ao resetar zoom: %s", e)

        driver.get("https://pje.trt2.jus.br/pjekz/")
        try:
            WebDriverWait(driver, 5).until(EC.url_contains("pjekz"))
        except Exception:
            pass

        logger.debug("Driver resetado")
        return True

    except Exception as e:
        logger.error("Erro ao resetar driver: %s", e)
        return False
