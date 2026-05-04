"""Triagem/runner.py — LEGADO: thin shim de compatibilidade.

O código ativo foi consolidado em runtime_triagem.py.
Mantém o contrato de import: `from Triagem.runner import run_triagem`.
"""
from .runtime_triagem import run_triagem  # noqa: F401
