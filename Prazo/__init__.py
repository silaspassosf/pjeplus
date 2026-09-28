"""
Prazo — modulo de processamento de prazos PJe.

Duas superficies ativas (consumidas por x.py):
  Handler C: Prazo.loop_prazo          (loop_orquestrador)
  Handler D: Prazo.fluxo_api.*          (fluxo_api → p2b_gateway)

Estrutura consolidada (6 arquivos raiz):
  loop_orquestrador.py  554 linhas — prelude do loop
  loop_lote.py          553 linhas — movimentacao em lote
  loop_execucao_final.py 514 linhas — fechamento do loop
  p2b_gateway.py        506 linhas — gateway / API do P2B
  p2b_regras_execucao.py 527 linhas — regras de execucao
  p2b_documentos.py     633 linhas — extracao documental e regras
"""

import logging
logger = logging.getLogger(__name__)

# Superficie publica do loop (handler C do x.py)
from Prazo.loop_orquestrador import loop_prazo, ciclo1
from Prazo.loop_execucao_final import ciclo2, ciclo3

__all__ = [
    'loop_prazo',
    'ciclo1', 'ciclo2', 'ciclo3',
]
