import logging
logger = logging.getLogger(__name__)

"""
@module: PEC.anexos
@responsibility: Processamento de anexos de petições
@depends_on: Fix.selenium_base, Fix.documents
@used_by: PEC.processamento
@entry_points: processar_anexos, validar_anexos
@tags: #anexos #peticao #validacao #upload
@created: 2026-01-29
@refactored_from: PEC/anexos.py (1284 linhas)
"""

# Arquivo movido de PEC/anexos.py → PEC/anexos/core.py
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
