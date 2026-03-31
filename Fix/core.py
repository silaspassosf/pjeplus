
from Fix.exceptions import TimeoutFluxoError
import logging
logger = logging.getLogger(__name__)

"""
Fix.core - Módulo de core para PJe automação.

Migrado automaticamente de Fix.py (PARTE 5 - Modularização).
"""


import os
import re
import time
import datetime
import json
import pyperclip
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Union, Callable

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException, NoSuchWindowException, ElementClickInterceptedException,
    ElementNotInteractableException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .log import logger, _log_info, _log_error, _audit
from Fix.selenium_base.wait_operations import wait as _wait_impl, wait_for_visible as _wait_for_visible_impl, wait_for_clickable as _wait_for_clickable_impl, esperar_elemento as _esperar_elemento_impl, esperar_url_conter as _esperar_url_conter_impl
from Fix.selenium_base.retry_logic import buscar_seletor_robusto as _buscar_seletor_robusto_impl, com_retry as _com_retry_impl
from Fix.extracao import safe_click as _safe_click_impl, selecionar_opcao as _selecionar_opcao_impl, preencher_campo as _preencher_campo_impl, preencher_campos_prazo as _preencher_campos_prazo_impl, preencher_multiplos_campos as _preencher_multiplos_campos_impl, escolher_opcao_inteligente as _escolher_opcao_inteligente_impl, encontrar_elemento_inteligente as _encontrar_elemento_inteligente_impl
from Fix.selenium_base.click_operations import aguardar_e_clicar as _aguardar_e_clicar_impl, safe_click_no_scroll as _safe_click_no_scroll_impl
from Fix.drivers.lifecycle import criar_driver_PC as _criar_driver_PC_impl, criar_driver_VT as _criar_driver_VT_impl, criar_driver_notebook as _criar_driver_notebook_impl, criar_driver_sisb_pc as _criar_driver_sisb_pc_impl, criar_driver_sisb_notebook as _criar_driver_sisb_notebook_impl
from Fix.utils import finalizar_driver as _finalizar_driver_impl, fechar_driver_imediato as _fechar_driver_imediato_impl, salvar_cookies_sessao as _salvar_cookies_sessao_impl, carregar_cookies_sessao as _carregar_cookies_sessao_impl, verificar_e_aplicar_cookies as _verificar_e_aplicar_cookies_impl, criar_botoes_detalhes as _criar_botoes_detalhes_impl, smart_sleep as _smart_sleep_impl, sleep as _sleep_impl, ErroCollector, SimpleConfig, config
from Fix.utils_observer import aguardar_renderizacao_nativa as _aguardar_renderizacao_nativa_impl
from Fix.navigation.filters import aplicar_filtro_100 as _aplicar_filtro_100_impl, filtro_fase as _filtro_fase_impl, filtrofases as _filtrofases_impl
from Fix.documents.search import verificar_documento_decisao_sentenca as _verificar_documento_decisao_sentenca_impl, buscar_ultimo_mandado as _buscar_ultimo_mandado_impl, buscar_mandado_autor as _buscar_mandado_autor_impl, buscar_documentos_sequenciais as _buscar_documentos_sequenciais_impl, buscar_documentos_polo_ativo as _buscar_documentos_polo_ativo_impl, buscar_documento_argos as _buscar_documento_argos_impl
from atos.wrappers_utils import visibilidade_sigilosos as _visibilidade_sigilosos_impl


# Variáveis de compatibilidade para logs antigos
DEBUG = os.getenv('PJEPLUS_DEBUG', '0').lower() in ('1', 'true', 'on')


def wait(driver: WebDriver, selector: str, timeout: int = 10, by: str = By.CSS_SELECTOR) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.wait."""
    return _wait_impl(driver, selector, timeout=timeout, by=by)


def wait_for_visible(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[str] = None) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.wait_for_visible."""
    return _wait_for_visible_impl(driver, selector, timeout=timeout, by=by)


def wait_for_clickable(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[str] = None) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.wait_for_clickable."""
    return _wait_for_clickable_impl(driver, selector, timeout=timeout, by=by)

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


def buscar_seletor_robusto(driver: WebDriver, textos: List[str], contexto: Optional[WebElement] = None, timeout: int = 5, log: bool = False) -> Optional[WebElement]:
    """Wrapper para Fix.selenium_base.retry_logic.buscar_seletor_robusto."""
    return _buscar_seletor_robusto_impl(driver, textos, contexto=contexto, timeout=timeout, log=log)


def esperar_elemento(driver: WebDriver, seletor: str, texto: Optional[str] = None, timeout: int = 10, by: str = By.CSS_SELECTOR, log: bool = False) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.esperar_elemento."""
    return _esperar_elemento_impl(driver, seletor, texto=texto, timeout=timeout, by=by, log=log)

# =========================
# 4. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

# Funções migradas para Fix.extracao (wrappers mantidos aqui para compatibilidade)


def safe_click(driver: WebDriver, selector_or_element: Union[str, WebElement], timeout: int = 10, by: Optional[str] = None, log: bool = False) -> bool:
    """Wrapper para Fix.extracao.safe_click."""
    return _safe_click_impl(driver, selector_or_element, timeout=timeout, by=by, log=log)


def aguardar_e_clicar(driver: WebDriver, seletor: str, log: bool = False, timeout: int = 10, by: str = By.CSS_SELECTOR, usar_js: bool = True, retornar_elemento: bool = False, debug: Optional[bool] = None) -> Union[bool, WebElement]:
    """Wrapper para Fix.selenium_base.click_operations.aguardar_e_clicar."""
    return _aguardar_e_clicar_impl(driver, seletor, log=log, timeout=timeout, by=by, usar_js=usar_js, retornar_elemento=retornar_elemento, debug=debug)


def safe_click_no_scroll(driver: WebDriver, element: WebElement, log: bool = False) -> bool:
    """Wrapper para Fix.selenium_base.click_operations.safe_click_no_scroll.
    
    Click SEM scrollIntoView (evita layout shifts que quebram header dinâmico).
    Usa dispatchEvent - padrão gigs-plugin.
    """
    return _safe_click_no_scroll_impl(driver, element, log=log)


def selecionar_opcao(driver: WebDriver, seletor_dropdown: str, texto_opcao: str, timeout: int = 10, exato: bool = False, log: bool = False) -> bool:
    """Wrapper para Fix.extracao.selecionar_opcao."""
    return _selecionar_opcao_impl(driver, seletor_dropdown, texto_opcao, timeout=timeout, exato=exato, log=log)


def preencher_campo(driver: WebDriver, seletor: str, valor: str, trigger_events: bool = True, limpar: bool = True, log: bool = False) -> bool:
    """Wrapper para Fix.extracao.preencher_campo."""
    return _preencher_campo_impl(driver, seletor, valor, trigger_events=trigger_events, limpar=limpar, log=log)


def preencher_campos_prazo(driver: WebDriver, valor: int = 0, timeout: int = 10, log: bool = True) -> bool:
    """Wrapper para Fix.extracao.preencher_campos_prazo."""
    return _preencher_campos_prazo_impl(driver, valor=valor, timeout=timeout, log=log)


def preencher_multiplos_campos(driver: WebDriver, campos_dict: Dict[str, str], log: bool = False) -> bool:
    """Wrapper para Fix.extracao.preencher_multiplos_campos."""
    return _preencher_multiplos_campos_impl(driver, campos_dict, log=log)


def com_retry(func: Callable, max_tentativas: int = 3, backoff_base: int = 2, log: bool = False, *args: Any, **kwargs: Any) -> Any:
    """Wrapper para Fix.selenium_base.retry_logic.com_retry."""
    return _com_retry_impl(func, max_tentativas=max_tentativas, backoff_base=backoff_base, log_enabled=log, *args, **kwargs)


def escolher_opcao_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """Wrapper para Fix.extracao.escolher_opcao_inteligente."""
    return _escolher_opcao_inteligente_impl(driver, valor, estrategias_custom=estrategias_custom, debug=debug)


def encontrar_elemento_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """Wrapper para Fix.extracao.encontrar_elemento_inteligente."""
    return _encontrar_elemento_inteligente_impl(driver, valor, estrategias_custom=estrategias_custom, debug=debug)

# =============================
# COLETOR DE ERROS (ex-Core)
# =============================
from Fix.utils import ErroCollector as ErroCollector

# BIBLIOTECA JAVASCRIPT BASE (MutationObserver Pattern)
# =============================


def js_base():
    """Wrapper para Fix.selenium_base.element_interaction.js_base."""
    from Fix.selenium_base.element_interaction import js_base as _impl
    return _impl()



def aguardar_renderizacao_nativa(driver: WebDriver, seletor: str, modo: str = "aparecer", timeout: int = 10) -> bool:
    """
    Wrapper para Fix.utils_observer.aguardar_renderizacao_nativa — injeta
    um MutationObserver no browser e espera por mudanças no DOM.
    """
    try:
        return _aguardar_renderizacao_nativa_impl(driver, seletor, modo=modo, timeout=timeout)
    except Exception as e:
        logger.warning(f"[core][OBSERVER] Falha ao usar aguardar_renderizacao_nativa: {e}")
        raise TimeoutFluxoError(f'Falha ao aguardar renderizacao nativa: {e}', timeout)

# =============================
# FUNÇÕES CONSOLIDADAS PARAMETRIZÁVEIS
# =============================


def criar_driver_PC(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_PC."""
    return _criar_driver_PC_impl(headless=headless)


def criar_driver_VT(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_VT."""
    return _criar_driver_VT_impl(headless=headless)


def criar_driver_notebook(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_notebook."""
    return _criar_driver_notebook_impl(headless=headless)


def criar_driver_sisb_pc(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_sisb_pc."""
    return _criar_driver_sisb_pc_impl(headless=headless)


def criar_driver_sisb_notebook(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_sisb_notebook."""
    return _criar_driver_sisb_notebook_impl(headless=headless)

# --- SISTEMA DE COOKIES ---


def finalizar_driver(driver, log=True):
    """Wrapper para Fix.utils.finalizar_driver."""
    return _finalizar_driver_impl(driver, log=log)



def finalizar_driver_imediato(driver, log=True):
    """Wrapper que delega para o fechamento imediato do driver.

    Mantém compatibilidade com código que espera `finalizar_driver_*` no core.
    """
    try:
        return _fechar_driver_imediato_impl(driver)
    except Exception as e:
        if log:
            logger.info(f'[CORE] finalizar_driver_imediato falhou: {e}')
        raise TimeoutFluxoError(f'Falha ao finalizar driver imediatamente: {e}', 0)

# =========================
# EXTRAÇÃO DIRETA DE DOCUMENTOS PJE
# =========================


def salvar_cookies_sessao(driver, caminho_arquivo=None, info_extra=None):
    """Wrapper para Fix.utils.salvar_cookies_sessao."""
    return _salvar_cookies_sessao_impl(driver, caminho_arquivo=caminho_arquivo, info_extra=info_extra)


from Fix.session import credencial as _credencial_impl
def credencial(tipo_driver='PC', tipo_login='CPF', headless=False, cpf=None, senha=None, url_login=None, max_idade_cookies=24):
    """Wrapper para Fix.session.credencial."""
    return _credencial_impl(
        tipo_driver=tipo_driver,
        tipo_login=tipo_login,
        headless=headless,
        cpf=cpf,
        senha=senha,
        url_login=url_login,
        max_idade_cookies=max_idade_cookies
    )


def carregar_cookies_sessao(driver, max_idade_horas=24):
    """Wrapper para Fix.utils.carregar_cookies_sessao."""
    return _carregar_cookies_sessao_impl(driver, max_idade_horas=max_idade_horas)


def verificar_e_aplicar_cookies(driver):
    """Wrapper para Fix.utils.verificar_e_aplicar_cookies."""
    return _verificar_e_aplicar_cookies_impl(driver)

# --- CONFIGURAÇÕES ATIVAS ---

from Fix.utils import (
    AHK_EXE_PC,
    AHK_SCRIPT_PC,
    AHK_EXE_NOTEBOOK,
    AHK_SCRIPT_NOTEBOOK,
    AHK_EXE_ACTIVE,
    AHK_SCRIPT_ACTIVE,
    USAR_COOKIES_AUTOMATICO,
    login_func,
    criar_driver,
    criar_driver_sisb,
    exibir_configuracao_ativa,
)


def aplicar_filtro_100(driver):
    """Wrapper para Fix.navigation.filters.aplicar_filtro_100."""
    return _aplicar_filtro_100_impl(driver)


def filtro_fase(driver):
    """Wrapper para Fix.navigation.filters.filtro_fase."""
    return _filtro_fase_impl(driver)


def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    """Wrapper para Fix.navigation.filters.filtrofases."""
    return _filtrofases_impl(driver, fases_alvo=fases_alvo, tarefas_alvo=tarefas_alvo, seletor_tarefa=seletor_tarefa)

# Função para processar lista de processos

# =========================
# 3. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

# Função de espera robusta


def esperar_url_conter(driver, substring, timeout=10):
    """Wrapper para Fix.selenium_base.wait_operations.esperar_url_conter."""
    return _esperar_url_conter_impl(driver, substring, timeout=timeout)


def verificar_documento_decisao_sentenca(driver):
    """Wrapper para Fix.documents.search.verificar_documento_decisao_sentenca."""
    return _verificar_documento_decisao_sentenca_impl(driver)


def visibilidade_sigilosos(driver, polo='ativo', log=True):
    """Wrapper para atos.wrappers_utils.visibilidade_sigilosos."""
    return _visibilidade_sigilosos_impl(driver, polo=polo, log=log)


def criar_botoes_detalhes(driver):
    """Wrapper para Fix.utils.criar_botoes_detalhes."""
    return _criar_botoes_detalhes_impl(driver)

# =========================
# 11. FUNÇÕES DE BUSCA E PESQUISA
# =========================


def buscar_ultimo_mandado(driver, log=True):
    """Wrapper para Fix.documents.search.buscar_ultimo_mandado."""
    return _buscar_ultimo_mandado_impl(driver, log=log)


def buscar_mandado_autor(driver, log=True):
    """Wrapper para Fix.documents.search.buscar_mandado_autor."""
    return _buscar_mandado_autor_impl(driver, log=log)
# =========================

def buscar_documentos_sequenciais(driver, log=True):
    """Wrapper para Fix.documents.search.buscar_documentos_sequenciais."""
    return _buscar_documentos_sequenciais_impl(driver, log=log)


def buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=None, debug=False, data_decisao_str=None):
    """Wrapper para Fix.documents.search.buscar_documentos_polo_ativo."""
    return _buscar_documentos_polo_ativo_impl(driver, polo=polo, limite_dias=limite_dias, debug=debug, data_decisao_str=data_decisao_str)

# ===================== FUNÇÕES CONSOLIDADAS PARA SISBAJUD =====================

# ===================== FUNÇÕES PARA ANÁLISE DE PRESCRIÇÃO =====================

def buscar_documento_argos(driver, log=True, **kwargs):
    """Wrapper para Fix.documents.search.buscar_documento_argos."""
    return _buscar_documento_argos_impl(driver, log=log, **kwargs)

# =============================
# SMART SLEEP - DELAYS INTELIGENTES
# =============================

from Fix.utils import SimpleConfig as SimpleConfig
from Fix.utils import config as config


def smart_sleep(t='default', multiplier=1.0):
    """Wrapper para Fix.utils.smart_sleep."""
    return _smart_sleep_impl(t=t, multiplier=multiplier)


def sleep(ms):
    """Wrapper para Fix.utils.sleep."""
    return _sleep_impl(ms)


# -------------------------
# Instrumentação de tempo
# -------------------------
TIME_ENABLED = os.getenv('PJEPLUS_TIME', '0').lower() in ('1', 'true', 'on')

@contextmanager
def tempo_execucao(label: str = None):
    """Context manager para medir tempo de execução de um bloco.

    Ativado quando a variável de ambiente `PJEPLUS_TIME` for verdadeira.
    """
    if not TIME_ENABLED:
        yield
        return
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.info('[TEMPO] %s: %.3fs', label or 'execucao', elapsed)


def medir_tempo(label: str = None):
    """Decorator simples para medir tempo de funções de alto nível.

    Usage:
        @medir_tempo('nome')
        def func(...):
            ...
    """
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

