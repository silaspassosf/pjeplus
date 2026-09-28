"""Thin shim: re-exports destinatarios/extracao functions from Fix.extracao."""

from .extracao import extrair_dados_processo, salvar_destinatarios_cache, carregar_destinatarios_cache

__all__ = ["extrair_dados_processo", "salvar_destinatarios_cache", "carregar_destinatarios_cache"]
