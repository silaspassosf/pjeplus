"""
Fix.core - Módulo de core para PJe automação.

Migrado automaticamente de Fix.py (PARTE 5 - Modularização).
"""

import os
from typing import Optional, Union, Any
from Play.pjeplay.locators import By, Keys
from Play.pjeplay.errors import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException, ElementClickInterceptedException,
    ElementNotInteractableException
)
import re, time, datetime, json, unicodedata
from .log import logger
from Fix import espera


# =============================================================================
# F7 — implementação decomposta; os nomes continuam disponíveis aqui
# =============================================================================
# Os corpos foram movidos verbatim para os módulos abaixo (grafo sem ciclos:
# espera <- drivers <- entrada; documentos e filtros são folhas).
# Re-export mantém os 76 importadores de `Fix.core` intactos.
from .navegacao_espera import (
    medir_tempo, aguardar_renderizacao_nativa, wait, garantir_carregamento_pagina, wait_for_page_load, extrair_id_processo,
    wait_for_visible, wait_for_clickable, esperar_elemento, esperar_url_conter, sleep,
)  # noqa: F401
from .navegacao import (
    _log_info, _log_error, _audit, safe_click, safe_click_no_scroll, aguardar_e_clicar,
    _clicar_botao_movimentar, _clicar_botao_tarefa_processo, ErroCollector, js_base, _buscar_filho, _buscar_filhos,
    _executar_js, _tentar_click_padrao, _tentar_click_javascript, _tentar_click_actionchains, _tentar_click_javascript_avancado,
)  # noqa: F401
from .entrada_campos import (
    buscar_seletor_robusto, selecionar_opcao, preencher_campo, preencher_campos_prazo, preencher_multiplos_campos, escolher_opcao_inteligente,
    encontrar_elemento_inteligente, _fechar_dropdown_ou_esc,
)  # noqa: F401
from .documentos_cp import (
    verificar_documento_decisao_sentenca, visibilidade_sigilosos, criar_botoes_detalhes, buscar_ultimo_mandado, buscar_mandado_autor, buscar_documentos_sequenciais,
    _norm, _normalizar_para_cp, _extrair_texto_item_api, _cp_eh_cdist, _cp_eh_despacho, _cp_eh_mandado,
    _cp_eh_certidao_oj, _cp_eh_certidao_geral, _obter_timeline_via_api, _encontrar_documento_na_timeline_api, _contar_documentos_na_timeline_api, _cp_texto_documento,
    _cp_marcar_checkbox, contar_mandados_e_certidoes_oficial, baixarCP, buscar_documentos_polo_ativo, buscar_documento_argos,
)  # noqa: F401
from .filtros_painel import (
    aplicar_filtro_100, filtro_fase, _aguardar_loader_painel, filtrofases,
)  # noqa: F401
from .config_simples import (
    SimpleConfig,
)  # noqa: F401

from .navegacao_espera import TIME_ENABLED  # noqa: F401
from .documentos_cp import _CP_DESPACHO  # noqa: F401

# Alias de compatibilidade de tipo
WebDriver = Any

# Variáveis de compatibilidade para logs antigos
DEBUG = os.getenv('PJEPLUS_DEBUG', '0').lower() in ('1', 'true', 'on')






# =========================
# 4. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

# Função para extrair documento


# ====================================================================
# SEÇÃO 7: CONFIGURAÇÃO DE DRIVERS E LOGIN
# ====================================================================
# As fábricas de driver foram movidas para Fix.driver_factory.
# Este bloco re-exporta tudo para compatibilidade com importadores existentes.
# Referência canônica: Fix/driver_factory.py
# ====================================================================

from Fix.driver_factory import (  # noqa: E402, F401
    GECKODRIVER_PATH,
    FIREFOX_BINARY_PADRAO,
    FIREFOX_BINARY_PADRAO_ALT,
    SISB_PROFILE_PC,
    SISB_PROFILE_NOTEBOOK,
    _aplicar_preferencias,
    _configurar_driver_pos_criacao,
    _criar_driver_firefox,
    _resolver_binario_firefox_padrao,
    _montar_options_pc,
    _montar_options_vt,
    com_retry,
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_pc,
    criar_driver_vt,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_vt,
    criar_driver_sisb_notebook,
    finalizar_driver,
)

if not os.path.exists(GECKODRIVER_PATH):
    import sys
    if getattr(webdriver, '__version__', None) != 'pjeplay' and 'pjeplay' not in sys.modules:
        logger.warning(f'AVISO: Geckodriver não encontrado em {GECKODRIVER_PATH}')
else:
    logger.info(f'Geckodriver encontrado: {GECKODRIVER_PATH}')

# --- HELPERS DE DRIVER: implementação em Fix.driver_factory (re-exportados acima) ---


# =============================
# COLETOR DE ERROS (ex-Core)
# =============================


# Instância global do coletor de erros
coletor_erros = ErroCollector()


# =============================
# BIBLIOTECA JAVASCRIPT BASE (MutationObserver Pattern)
# =============================


# =========================
# EXTRAÇÃO DIRETA DE DOCUMENTOS PJE
# =========================


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
    
    logger.info("[CONFIG] Login: %s | Driver: %s", login_nome, driver_nome)
    return login_nome, driver_nome



# Função para processar lista de processos

# =========================
# 3. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

# Função de espera robusta



# =========================
# 11. FUNÇÕES DE BUSCA E PESQUISA
# =========================


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


_CP_ANCORA = 'certidao de distribuicao'
_CP_MANDADO = 'mandado'
_CP_CERTIDAO_OJ = 'certidao de oficial de justica'


# ===================== FUNÇÕES CONSOLIDADAS PARA SISBAJUD =====================


# ===================== FUNÇÕES PARA ANÁLISE DE PRESCRIÇÃO =====================


# =============================
# SMART SLEEP - DELAYS INTELIGENTES
# =============================


config = SimpleConfig()

def smart_sleep(t='default', multiplier=1.0):
    espera.pausa(config.get_delay(t) * multiplier)


