"""Compatibilidade para o namespace legado Fix.variaveis_helpers."""

from api.variaveis_helpers import (
    obter_gigs_com_fase,
    obter_texto_documento,
    buscar_atividade_gigs_por_observacao,
    obter_todas_atividades_gigs_com_observacao,
    padrao_liq,
    verificar_bndt,
)

__all__ = [
    "obter_gigs_com_fase",
    "obter_texto_documento",
    "buscar_atividade_gigs_por_observacao",
    "obter_todas_atividades_gigs_com_observacao",
    "padrao_liq",
    "verificar_bndt",
]