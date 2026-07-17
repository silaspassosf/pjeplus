"""PEC.anexos - Processamento de anexos de petições."""

import logging
logger = logging.getLogger(__name__)

from .core import substituir_marcador_por_conteudo, salvar_conteudo_clipboard
from .anexos_wrappers import consulta_wrapper, wrapper_bloqneg, wrapper_parcial, carta_wrapper

__all__ = [
    'substituir_marcador_por_conteudo',
    'consulta_wrapper',
    'wrapper_bloqneg',
    'wrapper_parcial',
    'carta_wrapper',
    'salvar_conteudo_clipboard',
]
