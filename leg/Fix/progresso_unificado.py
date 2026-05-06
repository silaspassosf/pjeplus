"""Thin shim: re-export ProgressoUnificado from the unified monitor module.

This file exists to preserve legacy import locations (`from Fix.progresso_unificado
import ProgressoUnificado`) while centralizing the implementation in
`Fix.monitoramento_progresso_unificado`.
"""

from Fix.monitoramento_progresso_unificado import ProgressoUnificado

__all__ = ["ProgressoUnificado"]