"""
Fix.utils - Wrapper de compatibilidade para módulos especializados.

Este arquivo foi convertido para wrapper durante a refatoração modular.
Todas as funções são importadas dos módulos especializados para manter
100% de compatibilidade com código existente.

Módulos especializados:
- utils_error.py: ErroCollector e funções de tratamento de erros
- utils_formatting.py: Funções de formatação (moeda, data, CPF/CNPJ)
- utils_login.py: Funções de autenticação e login
- utils_cookies.py: Gerenciamento de cookies
- utils_drivers.py: Criação e configuração de drivers
- utils_collect.py: Funções de coleta de dados
- utils_sleep.py: Funções de espera e sleep
- utils_angular.py: Funções específicas para Angular
- utils_selectors.py: Seletores CSS e estratégias

IMPORTANTE: Este arquivo NÃO deve ser editado diretamente.
Modificações devem ser feitas nos módulos especializados correspondentes.
"""

# Imports dos módulos especializados
from .utils_error import ErroCollector
from .utils_formatting import (
    formatar_moeda_brasileira, formatar_data_brasileira,
    normalizar_cpf_cnpj, extrair_raiz_cnpj, identificar_tipo_documento
)
from .utils_login import (
    login_manual, login_automatico, login_automatico_direto,
    login_cpf, exibir_configuracao_ativa, login_pc
)
from .utils_cookies import (
    verificar_e_aplicar_cookies, salvar_cookies_sessao,
    limpar_cookies_antigos, listar_cookies_salvos, USAR_COOKIES_AUTOMATICO, COOKIES_DIR,
    SimpleConfig, config
)
from .utils_drivers import (
    criar_driver_firefox, criar_driver_PC, criar_driver_VT,
    criar_driver_notebook, criar_driver_sisb_pc, criar_driver_sisb_notebook,
    configurar_driver_avancado, verificar_driver_ativo, fechar_driver_safely,
    fechar_driver_imediato,
    _obter_caminhos_ahk, limpar_temp_selenium
)
from .utils_collect import (
    coletar_texto_seletor, coletar_valor_atributo,
    coletar_multiplos_elementos, coletar_tabela_como_lista,
    coletar_links_pagina, coletar_dados_formulario,
    extrair_numero_processo, extrair_cpf_cnpj, coletar_dados_pagina
)
from .utils_collect_content import (
    coletar_conteudo_js,
    coletar_elemento_css,
    executar_coleta_parametrizavel,
)
from .utils_collect_timeline import (
    coletar_link_ato_timeline,
)
from .utils_sleep import (
    sleep_random, sleep_fixed, sleep_progressivo,
    aguardar_url_mudar, aguardar_elemento_sumir,
    aguardar_texto_mudar, aguardar_loading_sumir,
    sleep_condicional, aguardar_pagina_carregar,
    sleep_com_logging, aguardar_multiplas_condicoes, sleep_adaptativo,
    sleep, smart_sleep
)
from .utils_angular import (
    aguardar_angular_carregar, aguardar_angular_requests,
    clicar_elemento_angular, preencher_campo_angular,
    aguardar_elemento_angular_visivel, verificar_angular_app,
    aguardar_angular_digest, obter_angular_scope, executar_angular_expressao,
    criar_js_otimizado, esperar_elemento_angular
)
from .utils_selectors import (
    SELECTORS_PJE, obter_seletor_pje, buscar_seletor_robusto,
    gerar_seletor_dinamico, detectar_seletor_elemento,
    validar_seletor, encontrar_seletor_estavel,
    criar_seletor_fallback, aplicar_estrategia_seletor
)
from .utils_editor import (
    inserir_html_editor,
    inserir_texto_editor,
    inserir_html_no_editor_apos_marcador,
    substituir_marcador_por_conteudo,
    obter_ultimo_conteudo_clipboard,
    inserir_link_ato,
    inserir_link_ato_validacao,
)

# Re-exportar configurações globais dos módulos
from .utils_login import (
    PROFILE_PATH, FIREFOX_BINARY, AHK_EXE_PC, AHK_SCRIPT_PC,
    AHK_EXE_NOTEBOOK, AHK_SCRIPT_NOTEBOOK, AHK_EXE_ACTIVE, AHK_SCRIPT_ACTIVE,
    login_func, criar_driver, criar_driver_sisb
)
from .utils_cookies import USAR_COOKIES_AUTOMATICO, COOKIES_DIR

# Para compatibilidade, manter imports antigos que podem estar sendo usados
import logging
logger = logging.getLogger(__name__)

# Imports de dependências externas (mantidos para compatibilidade)
import os
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
import re, time, datetime, json, pyperclip, logging, glob
from datetime import timedelta, datetime
from pathlib import Path

# Configuração global para recuperação automática de driver (mantida para compatibilidade)
_driver_recovery_config = {
    'enabled': False,
    'criar_driver': None,
    'login_func': None
}

def configurar_recovery_driver(criar_driver_func, login_func):
    """
    Configura funções globais para recuperação automática de driver.
    Deve ser chamado no início do script principal.
    
    Args:
        criar_driver_func: Função que cria novo driver (ex: criar_driver do driver_config)
        login_func: Função que faz login no sistema (ex: login_pje, login_siscon, etc)
        
    Exemplo:
        from Fix import configurar_recovery_driver
        from driver_config import criar_driver
        from Fix import login_pje
        
        configurar_recovery_driver(criar_driver, login_pje)
    """
    _driver_recovery_config['criar_driver'] = criar_driver_func
    _driver_recovery_config['login_func'] = login_func
    logger.info("Configuração de recuperação automática ativada")


# Compatibilidade: finalizar_driver usado em vários pontos do código legado
def finalizar_driver(driver, log=True):
    """Fecha o driver de forma segura (compatibilidade com API antiga).

    Delegates to `fechar_driver_safely` in `utils_drivers`.
    """
    try:
        from .utils_drivers import fechar_driver_safely as _impl
        return _impl(driver)
    except Exception as e:
        if log:
            logger.info(f'[UTILS] finalizar_driver falhou: {e}')
        return False


def verificar_e_tratar_acesso_negado_global(driver):
    """
    Verifica automaticamente se driver está em /acesso-negado e tenta recuperar.
    
    Args:
        driver: WebDriver atual
        
    Returns:
        novo_driver: Novo driver se recuperado, ou None se não foi acesso negado
        
    Raises:
        Exception: Se falhar na recuperação
    """
    if not _driver_recovery_config['enabled']:
        return None
    
    try:
        url_atual = driver.current_url
        if 'acesso-negado' not in url_atual.lower() and 'login.jsp' not in url_atual.lower():
            return None
        
        logger.info(f"[RECOVERY_GLOBAL]  ACESSO NEGADO DETECTADO: {url_atual}")
        logger.info("[RECOVERY_GLOBAL]  Iniciando recuperação automática...")
        
        # Fechar driver atual
        try:
            driver.quit()
            logger.info("Driver anterior fechado")
        except Exception as e:
            logger.info(f"[RECOVERY_GLOBAL]  Erro ao fechar driver: {e}")
        
        # Verificar se temos funções configuradas
        if not _driver_recovery_config['criar_driver'] or not _driver_recovery_config['login_func']:
            logger.error("Funções de recuperação não configuradas!")
            raise Exception("Recovery não configurado - use configurar_recovery_driver()")
        
        # Criar novo driver
        novo_driver = _driver_recovery_config['criar_driver'](headless=False)
        if not novo_driver:
            logger.error("Falha ao criar novo driver")
            raise Exception("Falha ao criar driver na recuperação")
        
        logger.info("Novo driver criado")
        
        # Fazer login
        if not _driver_recovery_config['login_func'](novo_driver):
            logger.error("Falha ao fazer login")
            novo_driver.quit()
            raise Exception("Falha no login durante recuperação")
        
        logger.info("Login efetuado com sucesso")
        logger.info("[RECOVERY_GLOBAL]  RECUPERAÇÃO COMPLETA!")
        
        return novo_driver
        
    except Exception as e:
        logger.info(f"[RECOVERY_GLOBAL]  ERRO CRÍTICO NA RECUPERAÇÃO: {e}")
        logger.info(f"[RECOVERY_GLOBAL]  Driver será encerrado")
        raise


def handle_exception_with_recovery(e, driver, funcao_nome=""):
    """
    Trata exceção verificando se é acesso negado e tentando recuperar driver.
    Deve ser chamado em TODOS os blocos except Exception.
    
    Args:
        e: Exceção capturada
        driver: Driver atual
        funcao_nome: Nome da função onde ocorreu erro (para log)
        
    Returns:
        novo_driver se recuperado, None se não foi acesso negado ou falhou
        
    Exemplo de uso:
        try:
            # código que pode falhar
            fazer_algo(driver)
        except Exception as e:
            novo_driver = handle_exception_with_recovery(e, driver, "FAZER_ALGO")
            if novo_driver:
                driver = novo_driver
                # tentar novamente ou continuar
            else:
                return False  # ou raise
    """
    prefixo = f"[{funcao_nome}]" if funcao_nome else "[EXCEPTION]"
    
    try:
        # Verifica se é acesso negado
        novo_driver = verificar_e_tratar_acesso_negado_global(driver)
        if novo_driver:
            logger.info(f"{prefixo}  Driver recuperado automaticamente após acesso negado")
            return novo_driver
    except Exception as recovery_error:
        logger.info(f"{prefixo}  Falha na recuperação automática: {recovery_error}")
    
    # Se não foi acesso negado ou falhou a recuperação, apenas loga o erro original
    logger.info(f"{prefixo}  Erro: {e}")
    return None


def obter_driver_padronizado(headless=False):
    """Retorna um driver Firefox padronizado para TRT2."""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    GECKODRIVER_PATH = r"d:\PjePlus\Fix\geckodriver.exe"

    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)

    service = Service(executable_path=GECKODRIVER_PATH)

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.info(f"[DRIVER] Erro ao iniciar Firefox: {e}")
        raise


def driver_pc(headless=False):
    """Perfil PC: C:/Users/Silas/AppData/Roaming/Mozilla/Dev"""
    return obter_driver_padronizado(headless=headless)


def navegar_para_tela(driver, url=None, seletor=None, delay=2, timeout=30, log=True):
    """Navega para URL ou clica em seletor."""
    from selenium.webdriver.common.by import By
    import time
    try:
        if log:
            logger.info(f'[NAVEGAR] Iniciando navegação...')
        if url:
            driver.get(url)
            if log:
                logger.info(f'[NAVEGAR] URL: {url}')
        if seletor:
            element = driver.find_element(By.CSS_SELECTOR, seletor)
            driver.execute_script('arguments[0].scrollIntoView(true);', element)
            element.click()
            
            if log:
                logger.info(f'[NAVEGAR] Clicou: {seletor}')
        return True
    except Exception as e:
        if log:
            logger.info(f'[NAVEGAR][ERRO] {str(e)}')
        return False

# Função de compatibilidade para código legado
def configurar_driver_recovery(enabled=False, criar_driver_func=None, login_func_param=None):
    """Configura recuperação automática de driver (compatibilidade)"""
    global _driver_recovery_config
    _driver_recovery_config['enabled'] = enabled
    _driver_recovery_config['criar_driver'] = criar_driver_func
    _driver_recovery_config['login_func'] = login_func_param
