import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_campos - Módulo de processamento de campos SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
Subdivide em:
- processamento_campos_principais.py: Campos principais da minuta
- processamento_campos_reus.py: Processamento de réus e configurações adicionais
"""

# Re-exportar funções dos submódulos para compatibilidade
from .processamento_campos_principais import _preencher_campos_principais
from .processamento_campos_reus import _processar_reus_otimizado, _configurar_valor, _configurar_opcoes_adicionais