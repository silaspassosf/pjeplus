"""
Fix.extracao - Compat shim that re-exports functions from the refactored
Fix/extracao_* modules and Fix/gigs.

This file is intentionally thin: it only imports and exposes the public API
expected by the rest of the codebase so the refactor is backwards-compatible.
"""

from .extracao_documento import (
    extrair_direto,
    extrair_documento,
    extrair_pdf,
    _extrair_formatar_texto,
)

from .extracao_processo import (
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
from .extracao_analise import analise_argos, tratar_anexos_argos, analise_outros
from .extracao_processo import salvar_destinatarios_cache, carregar_destinatarios_cache


def abrir_detalhes_processo(driver, *args, **kwargs):
    """Compatibility wrapper: opens detalhes/processo if implementation exists elsewhere.
    Falls back to no-op returning False if not available.
    """
    try:
        from .extracao_indexacao import abrir_detalhes_processo as _impl
        return _impl(driver, *args, **kwargs)
    except Exception:
        return False


def indexar_e_processar_lista(driver, callback, *args, **kwargs):
    """Compatibility wrapper for the legacy indexar_e_processar_lista fluxo."""
    try:
        from .extracao_indexacao_fluxo import indexar_e_processar_lista as _impl
        return _impl(driver, callback, *args, **kwargs)
    except Exception:
        return None

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
