"""
SISB.processamento_ordens - Wrapper para processamento de ordens SISBAJUD.

Parte da refatoracao do SISB/processamento.py para melhor granularidade IA.
Importa e coordena os submodulos de processamento.
"""

from .processamento_ordens_processamento import _processar_ordem
