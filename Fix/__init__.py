"""Fix - Pacote modular para automação PJe.

Uso recomendado:
    from Fix import aguardar_e_clicar, criar_gigs, login_cpf, validar_conexao_driver
"""

from .facade_publica import *
from .facade_publica import __all__ as _PUBLIC_ALL
from .errors import PJePlusError, ElementoNaoEncontradoError, NavegacaoError
from .diagnostico_runtime import (
    logger, PJELogger,
    log_start, log_item, log_sucesso, log_erro, log_fim,
    get_module_logger, getmodulelogger,
    _log_info, _log_error,
    log_seletor_multiplo,
    DebugInterativo, get_debug_interativo, on_erro_critico,
    aguardar_renderizacao_nativa, medir_tempo, TIME_ENABLED,
)

__version__ = "2.0.0"

_DIAG_ALL = [
    'logger', 'PJELogger',
    'log_start', 'log_item', 'log_sucesso', 'log_erro', 'log_fim',
    'get_module_logger', 'getmodulelogger',
    '_log_info', '_log_error',
    'log_seletor_multiplo',
    'DebugInterativo', 'get_debug_interativo', 'on_erro_critico',
    'aguardar_renderizacao_nativa', 'medir_tempo', 'TIME_ENABLED',
]

__all__ = list(_PUBLIC_ALL) + ["PJePlusError", "ElementoNaoEncontradoError", "NavegacaoError"] + _DIAG_ALL

