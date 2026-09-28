"""Shim de compatibilidade: re-exporta de Fix.facade_publica."""

from .facade_publica import criar_gigs, criar_comentario, criar_lembrete_posit

__all__ = ["criar_gigs", "criar_comentario", "criar_lembrete_posit"]
