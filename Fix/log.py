"""Shim de compatibilidade — reexporta de Fix.diagnostico_runtime.

Commited e pushed para o repositório online.
"""
from Fix.diagnostico_runtime import (
    logger, PJELogger,
    log_start, log_item, log_sucesso, log_erro, log_fim,
    get_module_logger, getmodulelogger,
    _log_info, _log_error,
    log_seletor_multiplo,
)

__all__ = [
    'logger', 'PJELogger',
    'log_start', 'log_item', 'log_sucesso', 'log_erro', 'log_fim',
    'get_module_logger', 'getmodulelogger',
    '_log_info', '_log_error',
    'log_seletor_multiplo',
]
