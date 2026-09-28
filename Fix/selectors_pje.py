"""Shim de compatibilidade: re-exporta de Fix.facade_publica."""

from .facade_publica import BTN_TAREFA_PROCESSO, buscar_seletor_robusto

__all__ = ["BTN_TAREFA_PROCESSO", "buscar_seletor_robusto"]
