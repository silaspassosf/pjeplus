"""Shim de compatibilidade: re-exporta de Fix.facade_publica."""

from .facade_publica import (
    BTN_TAREFA_PROCESSO,
    EDITOR_AREA_CONTEUDO,
    BTN_GRAVAR_MOVIMENTOS,
    BTN_EXPANDIR_CHIPS,
    CHIPS_LISTA,
    DIALOG_PRAZO_SOBRESTAMENTO,
    buscar_seletor_robusto,
)

__all__ = [
    "BTN_TAREFA_PROCESSO",
    "EDITOR_AREA_CONTEUDO",
    "BTN_GRAVAR_MOVIMENTOS",
    "BTN_EXPANDIR_CHIPS",
    "CHIPS_LISTA",
    "DIALOG_PRAZO_SOBRESTAMENTO",
    "buscar_seletor_robusto",
]
