"""Shim de compatibilidade — reexporta de Fix.diagnostico_runtime."""
from Fix.diagnostico_runtime import medir_tempo, TIME_ENABLED

__all__ = ['medir_tempo', 'TIME_ENABLED']
