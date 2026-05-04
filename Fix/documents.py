"""Shim de compatibilidade: re-exporta de Fix.facade_publica."""

from .facade_publica import (
    buscar_documentos_sequenciais,
    indexar_e_processar_lista,
    extrair_dados_processo,
    carregar_destinatarios_cache,
)

__all__ = [
    "buscar_documentos_sequenciais",
    "indexar_e_processar_lista",
    "extrair_dados_processo",
    "carregar_destinatarios_cache",
]
