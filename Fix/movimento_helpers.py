"""Shim de compatibilidade: re-exporta de Fix.facade_publica."""

from .facade_publica import (
    selecionar_movimento_dois_estagios,
    selecionar_movimento_auto,
    executar_movimento_judicial,
    _normalize_text,
)

__all__ = [
    "selecionar_movimento_dois_estagios",
    "selecionar_movimento_auto",
    "executar_movimento_judicial",
]
