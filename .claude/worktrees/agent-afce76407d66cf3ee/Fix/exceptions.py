"""Shim de compatibilidade: re-exporta excecoes de Fix.errors via Fix.facade_publica."""

from .facade_publica import PJePlusError, ElementoNaoEncontradoError, NavegacaoError

__all__ = ["PJePlusError", "ElementoNaoEncontradoError", "NavegacaoError"]
