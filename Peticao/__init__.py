"""
Peticao — Analise e processamento de peticoes eletronicas.

Estrutura principal (5 unidades):
  - runtime_pet.py     : run_pet, executar_fluxo_pet, PeticaoAPIClient
  - regras_execucao.py : classificacao, resolucao de acao, wrappers de atos
  - suporte_pet.py      : logging centralizado, multi-seletor, consolida delete
  - core/extracao/      : extracao de documentos (congelado)
  - helpers/             : helpers de validacao (congelado)
"""

from . import helpers
from .runtime_pet import run_pet, executar_fluxo_pet
from . import regras_execucao
from . import suporte_pet
