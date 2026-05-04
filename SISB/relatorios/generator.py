"""
SISB Relatorios Generator - Thin shim LEGADO.

LEGADO: Conteudo movido para SISB/relatorios_integracao.py (SX4).
Mantido para compatibilidade de import.
"""
from ..relatorios_integracao import (  # noqa: E402, F401
    _agrupar_dados_bloqueios,
    extrair_dados_bloqueios_processados,
    gerar_relatorio_bloqueios_processados,
    gerar_relatorio_bloqueios_conciso,
    _gerar_relatorio_ordem,
)

__all__ = [
    '_agrupar_dados_bloqueios',
    'extrair_dados_bloqueios_processados',
    'gerar_relatorio_bloqueios_processados',
    'gerar_relatorio_bloqueios_conciso',
    '_gerar_relatorio_ordem',
]
