import logging
logger = logging.getLogger(__name__)

"""
@module: Peticao
@responsibility: Analise e processamento de peticoes eletronicas
@depends_on: Fix, atos
@used_by: Workflows de triagem de peticoes
@entry_points: analisar_peticao, processar_peticao
@tags: #peticao #analise #processamento #triagem
@created: 2026-01-29
@note: Modulo consolidado — runtime principal em runtime_pet.py
"""

from . import helpers
from .runtime_pet import run_pet, executar_fluxo_pet

__all__ = ['helpers', 'run_pet', 'executar_fluxo_pet']
