import logging
logger = logging.getLogger(__name__)

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
from .log import logger, _log_info, _log_error, _audit

# Variáveis de compatibilidade para logs antigos
DEBUG = os.getenv('PJEPLUS_DEBUG', '0').lower() in ('1', 'true', 'on')

def wait(driver: WebDriver, selector: str, timeout: int = 10, by: str = By.CSS_SELECTOR) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.wait."""
    from Fix.selenium_base.wait_operations import wait as _impl
    return _impl(driver, selector, timeout=timeout, by=by)

def wait_for_visible(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[str] = None) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.wait_for_visible."""
    from Fix.selenium_base.wait_operations import wait_for_visible as _impl
    return _impl(driver, selector, timeout=timeout, by=by)

def wait_for_clickable(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[str] = None) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.wait_for_clickable."""
    from Fix.selenium_base.wait_operations import wait_for_clickable as _impl
    return _impl(driver, selector, timeout=timeout, by=by)

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
    from Fix.selenium_base.retry_logic import buscar_seletor_robusto as _impl
    return _impl(driver, textos, contexto=contexto, timeout=timeout, log=log)

def esperar_elemento(driver: WebDriver, seletor: str, texto: Optional[str] = None, timeout: int = 10, by: str = By.CSS_SELECTOR, log: bool = False) -> Any:
    """Wrapper para Fix.selenium_base.wait_operations.esperar_elemento."""
    from Fix.selenium_base.wait_operations import esperar_elemento as _impl
    return _impl(driver, seletor, texto=texto, timeout=timeout, by=by, log=log)

# =========================
# 4. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

# Funções migradas para Fix.extracao (wrappers mantidos aqui para compatibilidade)

def safe_click(driver: WebDriver, selector_or_element: Union[str, WebElement], timeout: int = 10, by: Optional[str] = None, log: bool = False) -> bool:
    """Wrapper para Fix.extracao.safe_click."""
    from Fix.extracao import safe_click as _impl
    return _impl(driver, selector_or_element, timeout=timeout, by=by, log=log)

def aguardar_e_clicar(driver: WebDriver, seletor: str, log: bool = False, timeout: int = 10, by: str = By.CSS_SELECTOR, usar_js: bool = True, retornar_elemento: bool = False, debug: Optional[bool] = None) -> Union[bool, WebElement]:
    """Wrapper para Fix.selenium_base.click_operations.aguardar_e_clicar."""
    from Fix.selenium_base.click_operations import aguardar_e_clicar as _impl
    return _impl(driver, seletor, log=log, timeout=timeout, by=by, usar_js=usar_js, retornar_elemento=retornar_elemento, debug=debug)

def safe_click_no_scroll(driver: WebDriver, element: WebElement, log: bool = False) -> bool:
    """Wrapper para Fix.selenium_base.click_operations.safe_click_no_scroll.
    
    Click SEM scrollIntoView (evita layout shifts que quebram header dinâmico).
    Usa dispatchEvent - padrão gigs-plugin.
    """
    from Fix.selenium_base.click_operations import safe_click_no_scroll as _impl
    return _impl(driver, element, log=log)

def selecionar_opcao(driver: WebDriver, seletor_dropdown: str, texto_opcao: str, timeout: int = 10, exato: bool = False, log: bool = False) -> bool:
    """Wrapper para Fix.extracao.selecionar_opcao."""
    from Fix.extracao import selecionar_opcao as _impl
    return _impl(driver, seletor_dropdown, texto_opcao, timeout=timeout, exato=exato, log=log)

def preencher_campo(driver: WebDriver, seletor: str, valor: str, trigger_events: bool = True, limpar: bool = True, log: bool = False) -> bool:
    """Wrapper para Fix.extracao.preencher_campo."""
    from Fix.extracao import preencher_campo as _impl
    return _impl(driver, seletor, valor, trigger_events=trigger_events, limpar=limpar, log=log)

def preencher_campos_prazo(driver: WebDriver, valor: int = 0, timeout: int = 10, log: bool = True) -> bool:
    """Wrapper para Fix.extracao.preencher_campos_prazo."""
    from Fix.extracao import preencher_campos_prazo as _impl
    return _impl(driver, valor=valor, timeout=timeout, log=log)

def preencher_multiplos_campos(driver: WebDriver, campos_dict: Dict[str, str], log: bool = False) -> bool:
    """Wrapper para Fix.extracao.preencher_multiplos_campos."""
    from Fix.extracao import preencher_multiplos_campos as _impl
    return _impl(driver, campos_dict, log=log)

def com_retry(func: Callable, max_tentativas: int = 3, backoff_base: int = 2, log: bool = False, *args: Any, **kwargs: Any) -> Any:
    """Wrapper para Fix.selenium_base.retry_logic.com_retry."""
    from Fix.selenium_base.retry_logic import com_retry as _impl
    return _impl(func, max_tentativas=max_tentativas, backoff_base=backoff_base, log_enabled=log, *args, **kwargs)

def escolher_opcao_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """Wrapper para Fix.extracao.escolher_opcao_inteligente."""
    from Fix.extracao import escolher_opcao_inteligente as _impl
    return _impl(driver, valor, estrategias_custom=estrategias_custom, debug=debug)

def encontrar_elemento_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """Wrapper para Fix.extracao.encontrar_elemento_inteligente."""
    from Fix.extracao import encontrar_elemento_inteligente as _impl
    return _impl(driver, valor, estrategias_custom=estrategias_custom, debug=debug)

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

# =============================
# FUNÇÕES CONSOLIDADAS PARAMETRIZÁVEIS
# =============================

def criar_driver_PC(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_PC."""
    from Fix.drivers.lifecycle import criar_driver_PC as _impl
    return _impl(headless=headless)

def criar_driver_VT(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_VT."""
    from Fix.drivers.lifecycle import criar_driver_VT as _impl
    return _impl(headless=headless)

def criar_driver_notebook(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_notebook."""
    from Fix.drivers.lifecycle import criar_driver_notebook as _impl
    return _impl(headless=headless)

def criar_driver_sisb_pc(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_sisb_pc."""
    from Fix.drivers.lifecycle import criar_driver_sisb_pc as _impl
    return _impl(headless=headless)

def criar_driver_sisb_notebook(headless=False):
    """Wrapper para Fix.drivers.lifecycle.criar_driver_sisb_notebook."""
    from Fix.drivers.lifecycle import criar_driver_sisb_notebook as _impl
    return _impl(headless=headless)

# --- SISTEMA DE COOKIES ---

def finalizar_driver(driver, log=True):
    """Wrapper para Fix.utils.finalizar_driver."""
    from Fix.utils import finalizar_driver as _impl
    return _impl(driver, log=log)

# =========================
# EXTRAÇÃO DIRETA DE DOCUMENTOS PJE
# =========================

def salvar_cookies_sessao(driver, caminho_arquivo=None, info_extra=None):
    """Wrapper para Fix.utils.salvar_cookies_sessao."""
    from Fix.utils import salvar_cookies_sessao as _impl
    return _impl(driver, caminho_arquivo=caminho_arquivo, info_extra=info_extra)

def credencial(tipo_driver='PC', tipo_login='CPF', headless=False, cpf=None, senha=None, url_login=None, max_idade_cookies=24):
    """Wrapper para Fix.utils.credencial."""
    from Fix.utils import credencial as _impl
    return _impl(
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
    from Fix.utils import carregar_cookies_sessao as _impl
    return _impl(driver, max_idade_horas=max_idade_horas)

def verificar_e_aplicar_cookies(driver):
    """Wrapper para Fix.utils.verificar_e_aplicar_cookies."""
    from Fix.utils import verificar_e_aplicar_cookies as _impl
    return _impl(driver)

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
    from Fix.navigation.filters import aplicar_filtro_100 as _impl
    return _impl(driver)

def filtro_fase(driver):
    """Wrapper para Fix.navigation.filters.filtro_fase."""
    from Fix.navigation.filters import filtro_fase as _impl
    return _impl(driver)

def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    """Wrapper para Fix.navigation.filters.filtrofases."""
    from Fix.navigation.filters import filtrofases as _impl
    return _impl(driver, fases_alvo=fases_alvo, tarefas_alvo=tarefas_alvo, seletor_tarefa=seletor_tarefa)

# Função para processar lista de processos

# =========================
# 3. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

# Função de espera robusta

def esperar_url_conter(driver, substring, timeout=10):
    """Wrapper para Fix.selenium_base.wait_operations.esperar_url_conter."""
    from Fix.selenium_base.wait_operations import esperar_url_conter as _impl
    return _impl(driver, substring, timeout=timeout)

def verificar_documento_decisao_sentenca(driver):
    """Wrapper para Fix.documents.search.verificar_documento_decisao_sentenca."""
    from Fix.documents.search import verificar_documento_decisao_sentenca as _impl
    return _impl(driver)

def visibilidade_sigilosos(driver, polo='ativo', log=True):
    """Wrapper para atos.wrappers_utils.visibilidade_sigilosos."""
    from atos.wrappers_utils import visibilidade_sigilosos as _impl
    return _impl(driver, polo=polo, log=log)

def criar_botoes_detalhes(driver):
    """Wrapper para Fix.utils.criar_botoes_detalhes."""
    from Fix.utils import criar_botoes_detalhes as _impl
    return _impl(driver)

# =========================
# 11. FUNÇÕES DE BUSCA E PESQUISA
# =========================

def buscar_ultimo_mandado(driver, log=True):
    """Wrapper para Fix.documents.search.buscar_ultimo_mandado."""
    from Fix.documents.search import buscar_ultimo_mandado as _impl
    return _impl(driver, log=log)

def buscar_mandado_autor(driver, log=True):
    """Wrapper para Fix.documents.search.buscar_mandado_autor."""
    from Fix.documents.search import buscar_mandado_autor as _impl
    return _impl(driver, log=log)
# =========================
def buscar_documentos_sequenciais(driver, log=True):
    """Wrapper para Fix.documents.search.buscar_documentos_sequenciais."""
    from Fix.documents.search import buscar_documentos_sequenciais as _impl
    return _impl(driver, log=log)

def buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=None, debug=False, data_decisao_str=None):
    """Wrapper para Fix.documents.search.buscar_documentos_polo_ativo."""
    from Fix.documents.search import buscar_documentos_polo_ativo as _impl
    return _impl(driver, polo=polo, limite_dias=limite_dias, debug=debug, data_decisao_str=data_decisao_str)

# ===================== FUNÇÕES CONSOLIDADAS PARA SISBAJUD =====================

# ===================== FUNÇÕES PARA ANÁLISE DE PRESCRIÇÃO =====================
def buscar_documento_argos(driver, log=True, **kwargs):
    """Wrapper para Fix.documents.search.buscar_documento_argos."""
    from Fix.documents.search import buscar_documento_argos as _impl
    return _impl(driver, log=log, **kwargs)

# =============================
# SMART SLEEP - DELAYS INTELIGENTES
# =============================

from Fix.utils import SimpleConfig as SimpleConfig
from Fix.utils import config as config

def smart_sleep(t='default', multiplier=1.0):
    """Wrapper para Fix.utils.smart_sleep."""
    from Fix.utils import smart_sleep as _impl
    return _impl(t=t, multiplier=multiplier)

def sleep(ms):
    """Wrapper para Fix.utils.sleep."""
    from Fix.utils import sleep as _impl
    return _impl(ms)

