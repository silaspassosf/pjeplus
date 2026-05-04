import logging
logger = logging.getLogger(__name__)

"""
SISBAJUD Helpers - Re-exports para compatibilidade
Arquivo refatorado seguindo padrão Fix/PEC
Funções movidas para submódulos especializados
"""

# ===== VALIDATION =====
from .ordens_execucao import _validar_dados

# ===== MINUTAS =====
from .facades_contratos import (
    _preencher_campos_iniciais,
    _processar_reus_otimizado,
    _salvar_minuta,
    _gerar_relatorio_minuta,
)

# ===== ORDENS =====
from .ordens_dados_navegacao import _carregar_dados_ordem

# ===== SERIES =====
from .facades_contratos import (
    _filtrar_series,
    _processar_series,
    _calcular_estrategia_bloqueio,
)

# ===== RELATORIOS =====
from .relatorios_integracao import _gerar_relatorio_ordem

# ===== INTEGRATION =====
from .relatorios_integracao import _executar_juntada_pje

# ===== EXPORTS COMPLETOS =====
__all__ = [
    # Validation
    '_validar_dados',

    # Minutas
    '_preencher_campos_iniciais',
    '_processar_reus_otimizado',
    '_salvar_minuta',
    '_gerar_relatorio_minuta',

    # Ordens
    '_carregar_dados_ordem',

    # Series
    '_filtrar_series',
    '_processar_series',
    '_calcular_estrategia_bloqueio',

    # Relatorios
    '_gerar_relatorio_ordem',

    # Integration
    '_executar_juntada_pje',
]
