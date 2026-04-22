"""Compatibility shim: re-export exceptions from `Fix.log`.

This file exists so older imports `from Fix.exceptions import ...`
continue to work after consolidation into `Fix.log`.
"""
from Fix.log import (
    PJePlusError,
    DriverFatalError,
    ElementoNaoEncontradoError,
    TimeoutFluxoError,
    NavegacaoError,
    LoginError,
)

__all__ = [
    "PJePlusError",
    "DriverFatalError",
    "ElementoNaoEncontradoError",
    "TimeoutFluxoError",
    "NavegacaoError",
    "LoginError",
]
