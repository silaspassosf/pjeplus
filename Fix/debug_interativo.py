"""Shim de compatibilidade — reexporta de Fix.diagnostico_runtime."""
from Fix.diagnostico_runtime import DebugInterativo, get_debug_interativo, on_erro_critico

__all__ = ['DebugInterativo', 'get_debug_interativo', 'on_erro_critico']
