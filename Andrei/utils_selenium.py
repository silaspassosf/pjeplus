"""
Andrei/utils_selenium.py - Utilitarios Selenium para automacao PJe.

Fornece funcoes de espera, clique e preenchimento de formularios
web sem dependencias de outros modulos do projeto.

Uso:
    from Andrei.utils_selenium import (
        esperar_elemento, wait_for_clickable, esperar_url_conter,
        aguardar_renderizacao_nativa, safe_click, aguardar_e_clicar,
        preencher_multiplos_campos, fechar_abas_extras
    )
"""

import logging
import time
from typing import Optional, Union, Dict

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Andrei.config import DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


# ==============================================================================
# FUNCOES BASE (privadas)
# ==============================================================================


def _js_base() -> str:
    """Funcoes JavaScript base usando MutationObserver.

    Funcoes disponiveis:
    - esperarElemento(seletor, timeout): Aguarda elemento aparecer
    - triggerEvent(elemento, tipo): Dispara evento (input, change, blur)

    Returns:
        String com codigo JavaScript pronto para execute_async_script.
    """
    return """
    function esperarElemento(seletor, timeout) {
        timeout = timeout || 5000;
        return new Promise(function(resolve) {
            var elemento = document.querySelector(seletor);
            if (elemento && elemento.disabled === false) {
                resolve(elemento);
                return;
            }
            var observer = new MutationObserver(function() {
                var elem = document.querySelector(seletor);
                if (elem && elem.disabled === false) {
                    observer.disconnect();
                    resolve(elem);
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
            setTimeout(function() {
                observer.disconnect();
                resolve(null);
            }, timeout);
        });
    }
    function triggerEvent(elemento, tipo) {
        if (!elemento) return;
        if ('createEvent' in document) {
            var evento = document.createEvent('HTMLEvents');
            evento.initEvent(tipo, true, true);
            elemento.dispatchEvent(evento);
        } else {
            elemento.dispatchEvent(new Event(tipo, { bubbles: true }));
        }
    }
    """


# ==============================================================================
# 1. ESPERAR ELEMENTO
# ==============================================================================


def esperar_elemento(
    driver: WebDriver,
    seletor: str,
    texto: Optional[str] = None,
    timeout: Union[int, float] = DEFAULT_TIMEOUT,
    by=By.CSS_SELECTOR,
) -> Optional[WebElement]:
    """Espera ate que um elemento esteja presente (e opcionalmente contenha texto).

    Args:
        driver: WebDriver Selenium.
        seletor: Seletor CSS ou XPath.
        texto: Se fornecido, aguarda ate que o texto esteja presente no elemento.
        timeout: Tempo maximo de espera em segundos.
        by: Tipo de seletor (By.CSS_SELECTOR ou By.XPATH).

    Returns:
        WebElement se encontrado, None em caso de timeout/erro.
    """
    try:
        if not isinstance(seletor, str):
            raise ValueError("Seletor deve ser string, recebido: %s" % type(seletor))
        if texto is not None and not isinstance(texto, str):
            raise ValueError("Texto deve ser string, recebido: %s" % type(texto))

        t0 = time.time()
        el = WebDriverWait(driver, float(timeout)).until(
            EC.presence_of_element_located((by, seletor))
        )
        if texto:
            WebDriverWait(driver, float(timeout)).until(lambda d: texto in el.text)
        t1 = time.time()
        logger.debug("Elemento encontrado: '%s' em %.2fs", seletor, t1 - t0)
        return el

    except ValueError as e:
        logger.error("esperar_elemento: erro de valor: %s", e)
        return None
    except Exception as e:
        logger.error(
            "Falha ao esperar elemento: '%s' (by=%s, timeout=%s): %s",
            seletor,
            by,
            timeout,
            e,
        )
        return None


# ==============================================================================
# 2. WAIT FOR CLICKABLE
# ==============================================================================


def wait_for_clickable(
    driver: WebDriver,
    selector: str,
    timeout: Union[int, float] = DEFAULT_TIMEOUT,
    by=None,
) -> Optional[WebElement]:
    """Aguarda ate que um elemento esteja clicavel.

    Args:
        driver: WebDriver Selenium.
        selector: Seletor CSS ou XPath.
        timeout: Tempo maximo de espera em segundos.
        by: Tipo de seletor (By.CSS_SELECTOR padrao se None).

    Returns:
        WebElement se encontrado e clicavel, None em caso de timeout/erro.
    """
    if by is None:
        by = By.CSS_SELECTOR
    try:
        element = WebDriverWait(driver, float(timeout)).until(
            EC.element_to_be_clickable((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        logger.warning("Elemento nao clicavel: %s", selector)
        return None
    except Exception as e:
        logger.warning(
            "wait_for_clickable: erro ao esperar elemento '%s': %s", selector, e
        )
        return None


# ==============================================================================
# 3. ESPERAR URL CONTER
# ==============================================================================


def esperar_url_conter(
    driver: WebDriver,
    substring: str,
    timeout: Union[int, float] = 15,
) -> bool:
    """Espera ate que a URL atual contenha a substring especificada.

    Args:
        driver: WebDriver Selenium.
        substring: String a ser encontrada na URL.
        timeout: Tempo maximo de espera em segundos (padrao 15).

    Returns:
        True se encontrou a substring na URL, False em caso de timeout/erro.
    """
    try:
        WebDriverWait(driver, float(timeout)).until(
            lambda d: substring in d.current_url
        )
        return True
    except TimeoutException:
        logger.error(
            "Timeout esperando URL conter: '%s'. URL atual: %s",
            substring,
            driver.current_url,
        )
        return False
    except Exception as e:
        logger.error("Erro ao esperar URL conter '%s': %s", substring, e)
        return False


# ==============================================================================
# 4. AGUARDAR RENDERIZACAO NATIVA
# ==============================================================================


def aguardar_renderizacao_nativa(
    driver: WebDriver,
    seletor: Optional[str] = None,
    modo: str = "aparecer",
    timeout: Union[int, float] = DEFAULT_TIMEOUT,
) -> bool:
    """Aguarda renderizacao e transicao de DOM.

    Suporta os modos:
    - sem seletor: aguarda document.readyState == complete
    - modo='aparecer': algum elemento visivel encontrado
    - modo='sumir': nenhum elemento visivel encontrado
    - modo='habilitado': algum elemento visivel e habilitado

    Args:
        driver: WebDriver Selenium.
        seletor: Seletor CSS. Se None, aguarda readyState.
        modo: 'aparecer', 'sumir', ou 'habilitado'.
        timeout: Tempo maximo de espera em segundos.

    Returns:
        True se condicao atendida, False em caso de timeout/erro.
    """

    def _coletar_elementos(web_driver):
        if not seletor:
            return []
        try:
            return web_driver.find_elements(By.CSS_SELECTOR, seletor)
        except Exception as e:
            logger.debug("_coletar_elementos: %s", e)
            return []

    def _elemento_visivel(element):
        try:
            return element.is_displayed()
        except Exception as e:
            logger.debug("_elemento_visivel: %s", e)
            return False

    try:
        if not seletor:
            WebDriverWait(driver, float(timeout)).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True

        if modo == "sumir":
            WebDriverWait(driver, float(timeout)).until(
                lambda d: not any(
                    _elemento_visivel(el) for el in _coletar_elementos(d)
                )
            )
            return True

        if modo == "habilitado":
            WebDriverWait(driver, float(timeout)).until(
                lambda d: any(
                    _elemento_visivel(el) and el.is_enabled()
                    for el in _coletar_elementos(d)
                )
            )
            return True

        # modo 'aparecer' (padrao)
        WebDriverWait(driver, float(timeout)).until(
            lambda d: any(_elemento_visivel(el) for el in _coletar_elementos(d))
        )
        return True

    except TimeoutException:
        return False
    except Exception as e:
        logger.warning("aguardar_renderizacao_nativa: %s", e)
        return False


# ==============================================================================
# 5. SAFE CLICK
# ==============================================================================


def safe_click(
    driver: WebDriver,
    selector_or_element: Union[str, WebElement],
    timeout: Union[int, float] = DEFAULT_TIMEOUT,
    by=None,
) -> bool:
    """Clica em um elemento de forma segura.

    Aceita seletor (string) ou instancia de WebElement.
    Tenta scrollIntoView + JS click com fallbacks de zoom.

    Args:
        driver: WebDriver Selenium.
        selector_or_element: Seletor CSS ou WebElement para clicar.
        timeout: Tempo maximo de espera em segundos.
        by: Tipo de seletor (By.CSS_SELECTOR padrao se None).

    Returns:
        True se clicou com sucesso, False caso contrario.
    """
    if by is None:
        by = By.CSS_SELECTOR

    try:
        # Obter elemento a partir do seletor ou usar diretamente
        if isinstance(selector_or_element, str):
            element = esperar_elemento(
                driver, selector_or_element, timeout=timeout, by=by
            )
        else:
            element = selector_or_element

        if element is None:
            logger.warning(
                "safe_click: elemento nao encontrado: %s", selector_or_element
            )
            return False

        # Elemento visivel: scrollIntoView + JS click
        if element.is_displayed():
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    element,
                )
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e_click:
                # Fallback: reduzir zoom e tentar novamente
                try:
                    prev_zoom = driver.execute_script(
                        "return document.body.style.zoom || '';"
                    )
                    driver.execute_script("document.body.style.zoom = '60%';")
                    time.sleep(0.12)
                    driver.execute_script("arguments[0].click();", element)
                    try:
                        driver.execute_script(
                            "document.body.style.zoom = '%s';" % prev_zoom
                        )
                    except Exception:
                        pass
                    return True
                except Exception as e_fallback:
                    logger.warning(
                        "safe_click: fallback zoom falhou: %s", e_fallback
                    )
                    try:
                        driver.execute_script(
                            "document.body.style.zoom = '%s';" % prev_zoom
                        )
                    except Exception:
                        pass
                    return False

        # Elemento nao visivel: tentar JS click direto
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e_hidden:
            try:
                prev_zoom = driver.execute_script(
                    "return document.body.style.zoom || '';"
                )
                driver.execute_script("document.body.style.zoom = '60%';")
                time.sleep(0.12)
                driver.execute_script("arguments[0].click();", element)
                try:
                    driver.execute_script(
                        "document.body.style.zoom = '%s';" % prev_zoom
                    )
                except Exception:
                    pass
                return True
            except Exception as e_final:
                logger.warning(
                    "safe_click: clique em elemento oculto falhou: %s", e_final
                )
                return False

    except Exception as e:
        logger.warning("safe_click: erro geral: %s", e)
        return False


# ==============================================================================
# 6. AGUARDAR E CLICAR
# ==============================================================================


def aguardar_e_clicar(
    driver: WebDriver,
    seletor: str,
    timeout: Union[int, float] = DEFAULT_TIMEOUT,
    by=By.CSS_SELECTOR,
) -> bool:
    """Aguarda elemento aparecer e clica nele.

    Usa MutationObserver via JavaScript para maxima performance.
    Fallback para implementacao Python quando JS falha.

    Args:
        driver: WebDriver Selenium.
        seletor: Seletor CSS ou XPath.
        timeout: Tempo maximo de espera em segundos.
        by: Tipo de seletor (By.CSS_SELECTOR padrao).

    Returns:
        True se clicou com sucesso, False caso contrario.
    """
    if by == By.CSS_SELECTOR:
        try:
            script = (
                """
            %s
            var callback = arguments[arguments.length - 1];
            esperarElemento('%s', %d)
                .then(function(el) {
                    if (el) {
                        el.click();
                        callback(true);
                    } else {
                        callback(false);
                    }
                })
                .catch(function(err) {
                    console.error('Erro aguardar_e_clicar:', err);
                    callback(false);
                });
            """
                % (_js_base(), seletor, int(timeout * 1000))
            )
            resultado = driver.execute_async_script(script)
            return bool(resultado)
        except Exception as e:
            logger.debug("aguardar_e_clicar JS falhou: %s", e)

    # Fallback Python
    elemento = esperar_elemento(driver, seletor, timeout=timeout, by=by)
    if elemento:
        try:
            elemento.click()
            return True
        except Exception as e:
            logger.warning("aguardar_e_clicar click falhou: %s", e)
            return False

    logger.warning("aguardar_e_clicar elemento nao encontrado: %s", seletor)
    return False


# ==============================================================================
# 7. PREENCHER MULTIPLOS CAMPOS
# ==============================================================================


def preencher_multiplos_campos(
    driver: WebDriver,
    campos_dict: Dict[str, str],
) -> Dict[str, bool]:
    """Preenche multiplos campos em uma unica operacao JavaScript.

    Args:
        driver: WebDriver Selenium.
        campos_dict: Dict {seletor: valor} com os campos a preencher.

    Returns:
        Dict {seletor: True/False} indicando sucesso de cada campo.

    Exemplo:
        resultado = preencher_multiplos_campos(driver, {
            '#nome': 'Joao Silva',
            '#email': 'joao@email.com'
        })
    """
    try:
        campos_js = []
        for seletor, valor in campos_dict.items():
            valor_escapado = (
                str(valor)
                .replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace('"', '\\"')
            )
            campos_js.append(
                "{'seletor': '%s', 'valor': '%s'}" % (seletor, valor_escapado)
            )

        campos_array = "[" + ", ".join(campos_js) + "]"

        script = """
        %s
        var campos = %s;
        var resultados = {};
        for (var i = 0; i < campos.length; i++) {
            try {
                var campo = campos[i];
                var elemento = document.querySelector(campo.seletor);
                if (elemento) {
                    elemento.value = campo.valor;
                    triggerEvent(elemento, 'input');
                    triggerEvent(elemento, 'change');
                    resultados[campo.seletor] = true;
                } else {
                    resultados[campo.seletor] = false;
                }
            } catch(e) {
                resultados[campos[i].seletor] = false;
            }
        }
        return resultados;
        """ % (
            _js_base(),
            campos_array,
        )

        resultado = driver.execute_script(script)
        logger.debug("preencher_multiplos_campos: %s", resultado)
        return resultado

    except Exception as e:
        logger.warning("preencher_multiplos_campos falhou: %s", e)
        return {seletor: False for seletor in campos_dict.keys()}


# ==============================================================================
# 8. FECHAR ABAS EXTRAS
# ==============================================================================


def fechar_abas_extras(
    driver: WebDriver, handle_principal: Optional[str] = None
) -> bool:
    """Fecha todas as abas abertas exceto a aba principal.

    Args:
        driver: WebDriver Selenium.
        handle_principal: Handle da aba a preservar. Se None, usa
                          driver.current_window_handle.

    Returns:
        True se limpeza foi bem-sucedida (ou nao havia abas extras),
        False em caso de erro.
    """
    try:
        principal = handle_principal or driver.current_window_handle
        abas_atuais = driver.window_handles
        logger.debug("Total de abas abertas: %s", len(abas_atuais))

        abas_extras = [aba for aba in abas_atuais if aba != principal]

        if not abas_extras:
            logger.debug("Nenhuma aba extra para fechar")
            return True

        logger.debug("Fechando %s aba(s) extra(s)", len(abas_extras))
        for idx, aba in enumerate(abas_extras, 1):
            for tentativa in range(3):
                try:
                    driver.switch_to.window(aba)
                    time.sleep(0.3)
                    driver.close()
                    logger.debug("Aba %s/%s fechada", idx, len(abas_extras))
                    break
                except Exception as e:
                    logger.warning(
                        "Tentativa %s/3 ao fechar aba: %s", tentativa + 1, e
                    )
                    time.sleep(0.5)

        # Retornar para a aba principal
        if principal in driver.window_handles:
            driver.switch_to.window(principal)
        elif driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])

        logger.debug("Abas restantes: %s", len(driver.window_handles))
        return True

    except Exception as e:
        logger.error("Erro ao fechar abas extras: %s", e)
        return False


__all__ = [
    "esperar_elemento",
    "wait_for_clickable",
    "esperar_url_conter",
    "aguardar_renderizacao_nativa",
    "safe_click",
    "aguardar_e_clicar",
    "preencher_multiplos_campos",
    "fechar_abas_extras",
]
