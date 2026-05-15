"""
Fix/browser_suporte.py - Suporte consolidado de browser para automacao PJe.

Consolidado de: Fix/abas.py, Fix/headless_helpers.py, Fix/otimizacao_wrapper.py.
Fornece funcoes para gerenciamento de abas, validacao de driver,
click headless e otimizacoes. FX2 (16-granular-fix.md).
"""

import time
import traceback
import datetime
from typing import Optional

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

from Fix.log import logger
from Fix.core import aguardar_e_clicar


# ============================================================
# Funcoes de abas (originalmente em Fix/abas.py)
# ============================================================


def is_browsing_context_discarded_error(error_message: str) -> bool:
    """
    Verifica se o erro e fatal (browsing context discarded, etc).

    Args:
        error_message: Mensagem de erro a verificar

    Returns:
        bool: True se e erro fatal, False caso contrario
    """
    if not error_message:
        return False
    error_str = str(error_message).lower()
    return ('browsing context has been discarded' in error_str or
            'no such window' in error_str or
            'nosuchwindowerror' in error_str or
            'session not created' in error_str or
            'invalid session id' in error_str)


def validar_conexao_driver(driver, contexto: str = "GERAL", proc_id: Optional[str] = None):
    """
    Valida se a conexao com o driver Selenium ainda esta ativa.

    Args:
        driver: WebDriver do Selenium
        contexto: Contexto da validacao para logs
        proc_id: ID do processo (opcional)

    Returns:
        bool | str: True se conectado, False se erro recuperavel, "FATAL" se irrecuperavel
    """
    try:
        if not hasattr(driver, 'session_id') or driver.session_id is None:
            logger.error("ERRO em validar_conexao_driver: Driver nao possui session_id valido")
            return False
        try:
            # Teste 1: Verificar se podemos acessar current_url
            try:
                current_url = driver.current_url
            except Exception as url_err:
                if is_browsing_context_discarded_error(url_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.error("ERRO em validar_conexao_driver: Contexto do navegador foi descartado - driver inutilizavel [%s]", timestamp)
                    logger.error("ERRO em validar_conexao_driver: %s", url_err)
                    logger.error("ERRO em validar_conexao_driver: %s", traceback.format_exc())
                    if proc_id:
                        logger.error("ERRO em validar_conexao_driver: Processo afetado: %s", proc_id)
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{url_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        logger.error("ERRO em validar_conexao_driver: Falha ao registrar erro fatal em arquivo: %s", logerr)
                    return "FATAL"
                else:
                    logger.error("ERRO em validar_conexao_driver: Falha ao acessar URL atual: %s", url_err)
                    return False
            # Teste 2: Verificar se podemos acessar window_handles
            try:
                window_handles = driver.window_handles
            except Exception as handles_err:
                if is_browsing_context_discarded_error(handles_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.error("ERRO em validar_conexao_driver: Contexto do navegador foi descartado - driver inutilizavel [%s]", timestamp)
                    logger.error("ERRO em validar_conexao_driver: %s", handles_err)
                    logger.error("ERRO em validar_conexao_driver: %s", traceback.format_exc())
                    if proc_id:
                        logger.error("ERRO em validar_conexao_driver: Processo afetado: %s", proc_id)
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{handles_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        logger.error("ERRO em validar_conexao_driver: Falha ao registrar erro fatal em arquivo: %s", logerr)
                    return "FATAL"
                else:
                    logger.error("ERRO em validar_conexao_driver: Falha ao acessar handles: %s", handles_err)
                    return False
            # Se ambos os testes passaram, o driver esta OK
            if contexto and 'DEBUG' in contexto.upper():
                logger.debug("Driver conectado - URL: %s... | Abas: %s", current_url[:50], len(window_handles))
            return True
        except Exception as connection_test_err:
            if is_browsing_context_discarded_error(connection_test_err):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.error("ERRO em validar_conexao_driver: Contexto do navegador foi descartado - driver inutilizavel [%s]", timestamp)
                logger.error("ERRO em validar_conexao_driver: %s", connection_test_err)
                logger.error("ERRO em validar_conexao_driver: %s", traceback.format_exc())
                if proc_id:
                    logger.error("ERRO em validar_conexao_driver: Processo afetado: %s", proc_id)
                try:
                    with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{connection_test_err}\n{traceback.format_exc()}\n\n")
                except Exception as logerr:
                    logger.error("ERRO em validar_conexao_driver: Falha ao registrar erro fatal em arquivo: %s", logerr)
                return "FATAL"
            else:
                logger.error("ERRO em validar_conexao_driver: Falha no teste de conexao: %s", connection_test_err)
                return False
    except Exception as validation_err:
        if is_browsing_context_discarded_error(validation_err):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.error("ERRO em validar_conexao_driver: Contexto do navegador foi descartado - driver inutilizavel [%s]", timestamp)
            logger.error("ERRO em validar_conexao_driver: %s", validation_err)
            logger.error("ERRO em validar_conexao_driver: %s", traceback.format_exc())
            if proc_id:
                logger.error("ERRO em validar_conexao_driver: Processo afetado: %s", proc_id)
            try:
                with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{validation_err}\n{traceback.format_exc()}\n\n")
            except Exception as logerr:
                logger.error("ERRO em validar_conexao_driver: Falha ao registrar erro fatal em arquivo: %s", logerr)
            return "FATAL"
        else:
            logger.error("ERRO em validar_conexao_driver: Falha na validacao de conexao: %s", validation_err)
            return False


def trocar_para_nova_aba(driver, aba_lista_original: str) -> Optional[str]:
    """
    Troca para uma nova aba diferente da aba original da lista.
    Inclui tratamento robusto de erros e verificacoes adicionais.

    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista

    Returns:
        str: O handle da nova aba se foi bem-sucedido, None caso contrario
    """
    try:
        # Verificar se o driver esta conectado
        if not validar_conexao_driver(driver, "ABAS"):
            logger.error("ERRO em trocar_para_nova_aba: Driver nao esta conectado ao tentar trocar de aba")
            return None

        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                logger.error("ERRO em trocar_para_nova_aba: Nenhuma aba disponivel")
                return None

            if len(abas) == 1 and abas[0] == aba_lista_original:
                logger.error("ERRO em trocar_para_nova_aba: Apenas a aba original esta disponivel, nenhuma nova aba foi aberta")
                return None

            # Mostrar informacao util das abas ao inves de IDs longos
            if len(abas) > 1:
                try:
                    aba_atual = driver.current_window_handle
                    outras_abas = [h for h in abas if h != aba_lista_original]
                    logger.debug("%s abas detectadas - %s nova(s) disponivel(is)", len(abas), len(outras_abas))
                except Exception:
                    logger.debug("%s abas detectadas", len(abas))
        except Exception as e:
            logger.error("ERRO em trocar_para_nova_aba: Falha ao obter lista de abas: %s", e)
            return None

        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    # Verificar se realmente trocamos de aba
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        # Log simplificado com URL util
                        try:
                            url_atual = driver.current_url
                            from urllib.parse import urlparse
                            parsed = urlparse(url_atual)
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                            else:
                                url_legivel = parsed.path or url_atual[-30:]
                            logger.debug('Nova aba aberta: %s', url_legivel)
                        except Exception:
                            logger.debug('Nova aba aberta')
                        return h
                    else:
                        logger.warning('Falha na troca de aba')
                except Exception as e:
                    logger.error("ERRO em trocar_para_nova_aba: Erro ao trocar para aba %s...: %s", h[:8], e)
                    continue

        # Se chegou aqui, nao conseguiu trocar para nenhuma nova aba
        logger.error("ERRO em trocar_para_nova_aba: Nao foi possivel trocar para nenhuma nova aba")
        return None
    except Exception as e:
        logger.error("ERRO em trocar_para_nova_aba: Erro geral ao tentar trocar de aba: %s", e)
        return None


def aguardar_nova_aba(driver, aba_lista_original: str, timeout: float = 10) -> str:
    """Compatibilidade para aguardar o handle de uma nova aba."""
    limite = time.time() + float(timeout)
    while time.time() < limite:
        try:
            for handle in driver.window_handles:
                if handle != aba_lista_original:
                    return handle
        except Exception:
            break
        time.sleep(0.2)  # rate-limit

    raise TimeoutException('Nenhuma nova aba detectada dentro do timeout')


def forcar_fechamento_abas_extras(driver, aba_lista_original: str):
    """Fecha todas as abas extras, mantendo apenas aba_lista_original."""
    try:
        for aba in driver.window_handles:
            if aba != aba_lista_original:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except Exception:
                    pass
        driver.switch_to.window(aba_lista_original)
    except Exception:
        pass


# ============================================================
# Funcoes headless (originalmente em Fix/headless_helpers.py)
# ============================================================


def limpar_overlays_headless(driver: WebDriver) -> bool:
    """
    Remove modals, tooltips e overlays que bloqueiam cliques em modo headless.
    Executado via JavaScript para maxima confiabilidade.

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

            // Remover overlays genericos com z-index alto
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
        WebDriverWait(driver, 2).until(lambda d: d.execute_script("return document.readyState") in ("complete", "interactive"))  # DOM-settle apos remover overlays
        return True
    except Exception as e:
        logger.warning(f"[HEADLESS] Aviso: Nao foi possivel limpar overlays: {e}")
        return False


def scroll_to_element_safe(driver: WebDriver, element: WebElement) -> bool:
    """
    Scroll seguro para elemento com multiplas estrategias.

    Args:
        driver: WebDriver instance
        element: Elemento para scrollar

    Returns:
        bool: True se scroll foi bem-sucedido
    """
    try:
        # Estrategia 1: scrollIntoView com comportamento suave
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
            element
        )
        WebDriverWait(driver, 2).until(lambda d: d.execute_script("return document.readyState") in ("complete", "interactive"))  # DOM-settle apos scroll
        return True
    except Exception:
        try:
            # Estrategia 2: scroll manual baseado em posicao
            driver.execute_script(
                "window.scrollTo(0, arguments[0].getBoundingClientRect().top + window.pageYOffset - 200);",
                element
            )
            WebDriverWait(driver, 2).until(lambda d: d.execute_script("return document.readyState") in ("complete", "interactive"))  # DOM-settle apos scroll
            return True
        except Exception:
            return False


def click_headless_safe(driver: WebDriver, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
    """
    Click ultra-seguro para modo headless com 3 estrategias progressivas.

    Estrategia 1: Wait padrao + click normal
    Estrategia 2: Limpar overlays + scroll + wait + click
    Estrategia 3: JavaScript click direto (ultimo recurso)

    Args:
        driver: WebDriver instance
        selector: Seletor CSS ou XPath
        by: Tipo de seletor (padrao CSS_SELECTOR)
        timeout: Timeout em segundos

    Returns:
        bool: True se click foi bem-sucedido
    """

    # Estrategia 1: Wait padrao element_to_be_clickable
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
        element.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        pass

    # Estrategia 2: Limpar overlays + scroll + wait + click
    try:
        limpar_overlays_headless(driver)
        element = WebDriverWait(driver, timeout // 2).until(
            EC.presence_of_element_located((by, selector))
        )
        scroll_to_element_safe(driver, element)
        # Aguarda elemento estar clicavel apos scroll (DOM-settle)
        WebDriverWait(driver, timeout // 2).until(EC.element_to_be_clickable((by, selector)))
        driver.find_element(by, selector).click()
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        pass

    # Estrategia 3: JavaScript click (fallback final)
    try:
        element = driver.find_element(by, selector)
        driver.execute_script("arguments[0].click();", element)
        WebDriverWait(driver, 2).until(lambda d: d.execute_script("return document.readyState") in ("complete", "interactive"))  # DOM-settle apos click JS
        return True
    except Exception as e:
        logger.error(f"[HEADLESS] Todas estrategias falharam para '{selector}': {e}")
        return False


def is_headless_mode(driver: WebDriver) -> bool:
    """
    Detecta se driver esta em modo headless.

    Returns:
        bool: True se headless
    """
    try:
        result = driver.execute_script("return navigator.webdriver;")
        # Heuristica: headless geralmente tem window.outerWidth == 0
        outer_width = driver.execute_script("return window.outerWidth;")
        return outer_width == 0 or result is True
    except Exception:
        return False


# ============================================================
# Funcoes de otimizacao (originalmente em Fix/otimizacao_wrapper.py)
# ============================================================


def inicializar_otimizacoes():
    """
    Inicializa sistemas de otimizacao no inicio da execucao.
    Chamar uma vez no inicio do script principal.
    """
    try:
        from selector_learning import get_learning_stats
        stats = get_learning_stats()
        logger.info("[OTIMIZACAO] Sistema de aprendizado ativo:")
        logger.info("  - Seletores conhecidos: %s", stats['total_selectors'])
        logger.info(f"  - Taxa de sucesso: {stats['success_rate']:.1%}")
        logger.info(f"  - Score medio: {stats['avg_score']:.2f}")
        return True
    except ImportError:
        logger.info("[OTIMIZACAO] Sistema de aprendizado nao disponivel")
        return False


def finalizar_otimizacoes():
    """
    Salva dados de aprendizado no final da execucao.
    Chamar no finally do script principal.
    """
    try:
        from selector_learning import save_learning_db, get_learning_stats
        save_learning_db()
        stats = get_learning_stats()
        logger.info("[OTIMIZACAO] Base de aprendizado salva (%s seletores)", stats['total_selectors'])
        return True
    except ImportError:
        return False


# ============================================================
# Funcoes de click (originalmente em Fix/selenium_base/click_operations.py)
# ============================================================


def safe_click_no_scroll(driver, element, log=False):
    """Click without scroll"""
    try:
        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))", element)
        return True
    except Exception:
        return False


# ============================================================
# Public API
# ============================================================

__all__ = [
    # abas
    'validar_conexao_driver',
    'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error',
    'aguardar_nova_aba',
    # headless
    'limpar_overlays_headless',
    'scroll_to_element_safe',
    'click_headless_safe',
    'is_headless_mode',
    # otimizacao
    'inicializar_otimizacoes',
    'finalizar_otimizacoes',
    # click_operations
    'aguardar_e_clicar',
    'safe_click_no_scroll',
]
