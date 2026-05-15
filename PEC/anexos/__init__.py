"""PEC.anexos - Processamento de anexos de petições."""

import logging
logger = logging.getLogger(__name__)

from .core import substituir_marcador_por_conteudo, salvar_conteudo_clipboard
from .anexos_wrappers import anex_sisbconsulta, anex_bloqneg, anex_parcial, anex_carta
from .anexos_juntador_base import wrapper_juntada_com_navegacao
from .anexos_sisbajud import executar_juntada_pje

__all__ = [
    'substituir_marcador_por_conteudo',
    'anex_sisbconsulta',
    'anex_bloqneg',
    'anex_parcial',
    'anex_carta',
    'salvar_conteudo_clipboard',
    'wrapper_juntada_com_navegacao',
    'executar_juntada_pje',
]
