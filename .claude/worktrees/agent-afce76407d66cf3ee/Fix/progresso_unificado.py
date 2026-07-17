"""Thin shim: re-export ProgressoUnificado do modulo de monitoramento unificado.

Este arquivo preserva imports legados (``from Fix.progresso_unificado import
ProgressoUnificado``) enquanto a implementacao fica centralizada em
``Fix.monitoramento_progresso_unificado`` (via ``Fix.facade_publica``).
"""

from .facade_publica import ProgressoUnificado

__all__ = ["ProgressoUnificado"]
