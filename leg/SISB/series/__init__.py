"""
SISB Series - Módulo de processamento de séries
Gerencia filtragem, navegação e processamento de séries SISBAJUD
"""

from .processor import (
    _filtrar_series,
    _navegar_e_extrair_ordens_serie,
    _extrair_nome_executado_serie,
    _processar_series,
    _calcular_estrategia_bloqueio
)

__all__ = [
    '_filtrar_series',
    '_navegar_e_extrair_ordens_serie',
    '_extrair_nome_executado_serie',
    '_processar_series',
    '_calcular_estrategia_bloqueio'
]
