"""
Fix.extracao - Compat shim that re-exports functions from the refactored
Fix/extracao_* modules and Fix/gigs.

This file is intentionally thin: it only imports and exposes the public API
expected by the rest of the codebase so the refactor is backwards-compatible.
"""

from typing import Any, Callable
from selenium.webdriver.remote.webdriver import WebDriver

from .extracao_conteudo import (
    extrair_direto,
    extrair_documento,
    extrair_pdf,
    _extrair_formatar_texto,
)

from .extracao_conteudo import (
    extrair_dados_processo,
    extrair_destinatarios_decisao,
)

from .extracao_indexacao import (
    filtrofases,
    indexar_processos,
    reindexar_linha,
    trocar_para_nova_aba,
)

from Fix.selenium_base import (
    safe_click,
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    preencher_campos_prazo,
    com_retry,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente,
)
from Fix.selenium_base.element_interaction import preencher_multiplos_campos

from Fix.gigs import (
    criar_gigs,
    criar_lembrete_posit,
)

# Reexports / compatibility aliases
from .extracao_bndt import bndt
from .extracao_processo import salvar_destinatarios_cache, carregar_destinatarios_cache



# --- Funções de analise (anterior extracao_analise.py — 31 linhas, inlined) ---
def analise_argos(driver):
    """Fluxo para análise de mandados Argos (Pesquisa Patrimonial)."""
    try:
        pass
    except Exception as e:
        _logger.error(f'[ARGOS][ERRO] Falha na análise Argos: {e}')


def tratar_anexos_argos(driver, log=True):
    """Placeholder — lógica removida conforme solicitado."""
    pass


def analise_outros(driver):
    """Fluxo para análise de mandados Outros (Oficial de Justiça)."""
    from Fix.extracao_conteudo import extrair_documento as _extrair_doc
    from Fix.gigs import criar_gigs as _criar_gigs
    texto = _extrair_doc(driver, regras_analise=lambda texto: _criar_gigs(driver, 0, 'Pz mdd'))
    if not texto:
        _logger.error("[OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
    return texto



from .extracao_indexacao import abrir_detalhes_processo as _abrir_detalhes_processo_impl

def abrir_detalhes_processo(driver: WebDriver, *args: Any, **kwargs: Any) -> bool:
    """Compatibility wrapper: opens detalhes/processo if implementation exists elsewhere.
    Falls back to no-op returning False if not available.
    """
    try:
        return _abrir_detalhes_processo_impl(driver, *args, **kwargs)
    except Exception:
        return False



from .extracao_indexacao import indexar_e_processar_lista as _indexar_e_processar_lista_impl
from Fix.log import logger as _logger

def indexar_e_processar_lista(driver: WebDriver, callback: Callable, *args: Any, **kwargs: Any) -> bool:
    """Compatibility wrapper for the legacy indexar_e_processar_lista fluxo."""
    try:
        return _indexar_e_processar_lista_impl(driver, callback, *args, **kwargs)
    except Exception as e:
        # Não engolir exceções silenciosamente — registrar e retornar False
        _logger.exception(f'[EXTRACAO_WRAP] Falha ao chamar indexar_e_processar_lista: {e}')
        return False

__all__ = [
    'extrair_direto',
    'extrair_documento',
    'extrair_pdf',
    '_extrair_formatar_texto',
    'extrair_dados_processo',
    'extrair_destinatarios_decisao',
    'filtrofases',
    'indexar_processos',
    'reindexar_linha',
    'safe_click',
    'aguardar_e_clicar',
    'selecionar_opcao',
    'preencher_campo',
    'preencher_campos_prazo',
    'preencher_multiplos_campos',
    'com_retry',
    'escolher_opcao_inteligente',
    'encontrar_elemento_inteligente',
    'criar_gigs',
    'criar_lembrete_posit',
    'bndt',
    'analise_argos',
    'tratar_anexos_argos',
    'analise_outros',
    'salvar_destinatarios_cache',
    'carregar_destinatarios_cache',
    'abrir_detalhes_processo',
    'indexar_e_processar_lista',
]
