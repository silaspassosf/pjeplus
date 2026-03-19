import logging
logger = logging.getLogger(__name__)

"""
SISBAJUD Helpers - Re-exports para compatibilidade
Arquivo refatorado seguindo padrão Fix/PEC
Funções movidas para submódulos especializados
"""

# ===== VALIDATION =====
from .validation import (
    _validar_dados
)

# ===== MINUTAS =====
from .minutas import (
    _selecionar_prazo_bloqueio,
    _preencher_campos_iniciais,
    _processar_reus_otimizado,
    _salvar_minuta,
    _gerar_relatorio_minuta,
    _protocolar_minuta,
    _criar_minuta_agendada_por_copia,
    _criar_minuta_agendada
)

# ===== ORDENS =====
from .ordens import (
    _carregar_dados_ordem,
    _extrair_ordens_da_serie,
    _aplicar_acao_por_fluxo,
    _identificar_ordens_com_bloqueio
)

# ===== SERIES ===== 
from .series import (
    _filtrar_series,
    _navegar_e_extrair_ordens_serie,
    _extrair_nome_executado_serie,
    _processar_series,
    _calcular_estrategia_bloqueio
)

# ===== NAVIGATION =====
from .navigation import (
    _voltar_para_lista_ordens_serie,
    _voltar_para_lista_principal
)

# ===== RELATORIOS =====
from .relatorios import (
    _agrupar_dados_bloqueios,
    extrair_dados_bloqueios_processados,
    gerar_relatorio_bloqueios_processados,
    gerar_relatorio_bloqueios_conciso,
    _gerar_relatorio_ordem
)

# ===== INTEGRATION =====
from .integration import (
    _atualizar_relatorio_com_segundo_protocolo,
    _executar_juntada_pje
)

# ===== EXPORTS COMPLETOS =====
__all__ = [
    # Validation
    '_validar_dados',
    
    # Minutas
    '_selecionar_prazo_bloqueio',
    '_preencher_campos_iniciais',
    '_processar_reus_otimizado',
    '_salvar_minuta',
    '_gerar_relatorio_minuta',
    '_protocolar_minuta',
    '_criar_minuta_agendada_por_copia',
    '_criar_minuta_agendada',
    
    # Ordens
    '_carregar_dados_ordem',
    '_extrair_ordens_da_serie',
    '_aplicar_acao_por_fluxo',
    '_identificar_ordens_com_bloqueio',
    
    # Series
    '_filtrar_series',
    '_navegar_e_extrair_ordens_serie',
    '_extrair_nome_executado_serie',
    '_processar_series',
    '_calcular_estrategia_bloqueio',
    
    # Navigation
    '_voltar_para_lista_ordens_serie',
    '_voltar_para_lista_principal',
    
    # Relatórios
    '_agrupar_dados_bloqueios',
    'extrair_dados_bloqueios_processados',
    'gerar_relatorio_bloqueios_processados',
    'gerar_relatorio_bloqueios_conciso',
    '_gerar_relatorio_ordem',
    
    # Integration
    '_atualizar_relatorio_com_segundo_protocolo',
    '_executar_juntada_pje'
]
