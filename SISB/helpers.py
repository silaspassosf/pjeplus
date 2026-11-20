import logging
logger = logging.getLogger(__name__)

"""
SISBAJUD Helpers - Re-exports para compatibilidade
Arquivo refatorado seguindo padrão Fix/PEC
Funções movidas para submódulos especializados
"""

from .ordens_execucao import _validar_dados

from .facades_contratos import (
    _preencher_campos_iniciais,
    _processar_reus_otimizado,
    _salvar_minuta,
    _gerar_relatorio_minuta,
    _protocolar_minuta,
)

from .ordens_dados_navegacao import _carregar_dados_ordem

from .facades_contratos import (
    _filtrar_series,
    _processar_series,
    _calcular_estrategia_bloqueio,
)

from .relatorios_integracao import _gerar_relatorio_ordem

from atos.anexos import executar_juntada_pje as _executar_juntada_pje

__all__ = [
    '_validar_dados',

    '_preencher_campos_iniciais',
    '_processar_reus_otimizado',
    '_salvar_minuta',
    '_gerar_relatorio_minuta',

    '_carregar_dados_ordem',

    '_filtrar_series',
    '_processar_series',
    '_calcular_estrategia_bloqueio',

    '_gerar_relatorio_ordem',

    '_executar_juntada_pje',
]
