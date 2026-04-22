"""Thin shim: re-export ProgressoUnificado from Fix.progress.

This file exists to preserve legacy import locations (`from Fix.progresso_unificado
import ProgressoUnificado`) while centralizing the implementation in
`Fix.progress.monitoramento`.
"""
import warnings
warnings.warn(
    "Fix.progresso_unificado está obsoleto; importe de Fix.progress",
    DeprecationWarning,
    stacklevel=2,
)

from Fix.progress.monitoramento import ProgressoUnificado  # noqa: F401,E402

__all__ = ["ProgressoUnificado"]
