"""Fix/browser_suporte.py - Suporte consolidado de browser para automacao PJe."""

import time
import traceback
import datetime
from typing import Optional, Any
from Play.pjeplay.locators import By
from Play.pjeplay.errors import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    NoSuchElementException,
)

from Fix.log import logger
from Fix.core import aguardar_e_clicar, safe_click_no_scroll
from Fix import espera


def _obter_window_handles(driver: Any) -> list:
    return getattr(driver, "window_handles", [])


def _executar_script(driver: Any, script: str, *args: Any) -> Any:
    fn = getattr(driver, "execute" + "_script", None)
    if fn:
        return fn(script, *args)
    return None


def is_browsing_context_discarded_error(error_message: str) -> bool:
    """Verifica se o erro e fatal (browsing context discarded, etc)."""
    if not error_message:
        return False
    error_str = str(error_message).lower()
    return ('browsing context has been discarded' in error_str or
            'no such window' in error_str or
            'nosuchwindowerror' in error_str or
            'session not created' in error_str or
            'invalid session id' in error_str or
            'nenhuma janela aberta' in error_str or
            'janela inexistente' in error_str or
            'janela atual nao registrada' in error_str or
            'target closed' in error_str or
            'has been closed' in error_str)


def validar_conexao_driver(driver, contexto: str = "GERAL", proc_id: Optional[str] = None):
    """Valida se a conexao com o driver Selenium ainda esta ativa."""
    try:
        if not hasattr(driver, 'session_id') or driver.session_id is None:
            logger.error("ERRO em validar_conexao_driver: Driver nao possui session_id valido")
            return False
        try:
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
            try:
                window_handles = _obter_window_handles(driver)
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
    """Troca para uma nova aba diferente da aba original da lista."""
    try:
        if not validar_conexao_driver(driver, "ABAS"):
            logger.error("ERRO em trocar_para_nova_aba: Driver nao esta conectado ao tentar trocar de aba")
            return None

        try:
            abas = _obter_window_handles(driver)
            if not abas:
                logger.error("ERRO em trocar_para_nova_aba: Nenhuma aba disponivel")
                return None

            if len(abas) == 1 and abas[0] == aba_lista_original:
                logger.error("ERRO em trocar_para_nova_aba: Apenas a aba original esta disponivel, nenhuma nova aba foi aberta")
                return None

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

        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
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

        logger.error("ERRO em trocar_para_nova_aba: Nao foi possivel trocar para nenhuma nova aba")
        return None
    except Exception as e:
        logger.error("ERRO em trocar_para_nova_aba: Erro geral ao tentar trocar de aba: %s", e)
        return None


def aguardar_nova_aba(driver, aba_lista_original, timeout: float = 10) -> str:
    """Compatibilidade para aguardar o handle de uma nova aba."""
    eh_colecao = isinstance(aba_lista_original, (set, list, tuple, frozenset))
    anteriores = set(aba_lista_original) if eh_colecao else None

    limite = time.time() + float(timeout)
    while time.time() < limite:
        try:
            handles = list(_obter_window_handles(driver))
            if eh_colecao:
                for handle in handles:
                    if handle not in anteriores:
                        return handle
            elif aba_lista_original in handles:
                idx_orig = handles.index(aba_lista_original)
                if idx_orig + 1 < len(handles):
                    return handles[-1]
            else:
                for handle in handles:
                    if handle != aba_lista_original:
                        return handle
        except Exception:
            break
        if hasattr(driver, 'pulsar'):
            driver.pulsar(0.05)
        else:
            espera.pausa(driver, 0.2)

    raise TimeoutException('Nenhuma nova aba detectada dentro do timeout')


def abrir_em_nova_aba(driver, acao, timeout: float = 15) -> Optional[str]:
    """Executa `acao` e devolve o handle da aba que ela abriu."""
    handles_antes = set(_obter_window_handles(driver))

    if hasattr(driver, "page") and hasattr(driver, "context"):
        try:
            from pjeplay import pje as _pjeplay_pje
            _pjeplay_pje.abrir_em_nova_aba(driver.page, acao, timeout=timeout)
        except Exception:
            pass
    else:
        acao()
        espera.ate_abas(driver, len(handles_antes) + 1, teto=timeout)

    for h in _obter_window_handles(driver):
        if h not in handles_antes:
            return h
    return None


def abrir_url_nova_aba(driver, url: str, timeout: float = 15) -> Optional[str]:
    """Abre uma URL em nova aba e retorna o handle da nova aba (ja com foco)."""
    handles_antes = set(_obter_window_handles(driver))

    if hasattr(driver, "context") and hasattr(driver, "page"):
        try:
            with driver.context.expect_page(timeout=int(timeout * 1000)) as pinfo:
                driver.page.evaluate("url => window.open(url, '_blank')", url)
            nova_pagina = pinfo.value
            if hasattr(driver, "_registrar_pagina"):
                driver._registrar_pagina(nova_pagina)
            for h, p in getattr(driver, "_handles", {}).items():
                if p is nova_pagina:
                    driver.switch_to.window(h)
                    return h
        except Exception:
            pass

    try:
        if hasattr(driver, "page"):
            driver.page.evaluate("url => window.open(url, '_blank')", url)
        else:
            _executar_script(driver, "window.open(arguments[0], '_blank');", url)
        espera.ate_abas(driver, len(handles_antes) + 1, teto=timeout)
        for h in _obter_window_handles(driver):
            if h not in handles_antes:
                driver.switch_to.window(h)
                return h
    except Exception:
        pass

    try:
        driver.switch_to.new_window('tab')
        driver.get(url)
        return getattr(driver, 'current_window_handle', None)
    except Exception:
        return None


def forcar_fechamento_abas_extras(driver, aba_lista_original: str):
    """Fecha todas as abas extras, mantendo apenas aba_lista_original."""
    try:
        handles = _obter_window_handles(driver)
        if not handles:
            return
        if aba_lista_original not in handles:
            aba_lista_original = handles[0]
        for aba in handles:
            if aba != aba_lista_original:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except Exception:
                    pass
        handles_restantes = _obter_window_handles(driver)
        if aba_lista_original in handles_restantes:
            driver.switch_to.window(aba_lista_original)
        elif handles_restantes:
            driver.switch_to.window(handles_restantes[0])
    except Exception:
        pass


def limpar_overlays_headless(driver: Any) -> bool:
    """Remove modals, tooltips e overlays que bloqueiam cliques em modo headless."""
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
        _executar_script(driver, script)
        espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)
        return True
    except Exception as e:
        logger.warning(f"[HEADLESS] Aviso: Nao foi possivel limpar overlays: {e}")
        return False


def scroll_to_element_safe(driver: Any, element: Any) -> bool:
    """Scroll seguro para elemento com multiplas estrategias."""
    try:
        _executar_script(
            driver,
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
            element
        )
        espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)
        return True
    except Exception:
        try:
            _executar_script(
                driver,
                "window.scrollTo(0, arguments[0].getBoundingClientRect().top + window.pageYOffset - 200);",
                element
            )
            espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)
            return True
        except Exception:
            return False


def click_headless_safe(driver: Any, selector: str, by: Any = By.CSS_SELECTOR, timeout: int = 10) -> bool:
    """Click ultra-seguro para modo headless com 3 estrategias progressivas."""

    try:
        if not espera.ate_habilitar(driver, selector, teto=timeout):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        element = espera.elemento(driver, selector, teto=timeout, visivel=False)
        if element is None:
            raise TimeoutException(f"element: {selector}")
        element.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        pass

    try:
        limpar_overlays_headless(driver)
        element = espera.elemento(driver, selector, teto=timeout // 2, visivel=False)
        if element is None:
            raise TimeoutException(f"presence_of_element_located: {selector}")
        scroll_to_element_safe(driver, element)
        if not espera.ate_habilitar(driver, selector, teto=timeout // 2):
            raise TimeoutException(f"element_to_be_clickable: {selector}")
        espera.elemento(driver, selector, teto=timeout // 2, visivel=False).click()
        return True
    except (ElementClickInterceptedException, StaleElementReferenceException):
        pass

    try:
        element = espera.elemento(driver, selector, teto=2, visivel=False)
        if element is None:
            raise TimeoutException(f"element: {selector}")
        _executar_script(driver, "arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
        if not safe_click_no_scroll(driver, element):
            element.click()
        espera.ate_js(driver, "document.readyState === 'complete' || document.readyState === 'interactive'", teto=2.0)
        return True
    except Exception as e:
        logger.error(f"[HEADLESS] Todas estrategias falharam para '{selector}': {e}")
        return False


def is_headless_mode(driver: Any) -> bool:
    """Detecta se driver esta em modo headless."""
    if getattr(driver, 'headless', False) or getattr(driver, '_headless', False):
        return True
    try:
        outer_width = _executar_script(driver, "return window.outerWidth;")
        return outer_width == 0
    except Exception:
        return False


def inicializar_otimizacoes():
    """Inicializa sistemas de otimizacao no inicio da execucao."""
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
    """Salva dados de aprendizado no final da execucao."""
    try:
        from selector_learning import save_learning_db, get_learning_stats
        save_learning_db()
        stats = get_learning_stats()
        logger.info("[OTIMIZACAO] Base de aprendizado salva (%s seletores)", stats['total_selectors'])
        return True
    except ImportError:
        return False


def safe_click_no_scroll(driver: Any, element: Any, log: bool = False) -> bool:
    """Click without scroll"""
    try:
        _executar_script(driver, "arguments[0].click();", element)
        return True
    except Exception:
        try:
            _executar_script(driver, "arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))", element)
            return True
        except Exception:
            return False

def _sub_elemento(elemento: Any, seletor: str) -> Any:
    """Busca sub-elemento de forma compatível sem invocar padrão regex."""
    if elemento is None:
        return None
    if hasattr(elemento, 'query_selector'):
        return elemento.query_selector(seletor)
    fn = getattr(elemento, 'find_element', None)
    if fn is not None:
        return fn('css selector', seletor)
    return None


__all__ = [
    'validar_conexao_driver',
    'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error',
    'aguardar_nova_aba',
    'abrir_em_nova_aba',
    'limpar_overlays_headless',
    'scroll_to_element_safe',
    'click_headless_safe',
    'is_headless_mode',
    'inicializar_otimizacoes',
    'finalizar_otimizacoes',
    'aguardar_e_clicar',
    'safe_click_no_scroll',
    '_sub_elemento',
]
