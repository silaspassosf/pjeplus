"""
PEC.anexos.anexos_juntador - Reexporta funções de anexos_juntador_base.

Garante compatibilidade e ponto único de verdade para funções de juntada.
"""

from .anexos_juntador_base import (
    wrapper_juntada_geral,
    make_juntada_wrapper,
    create_juntador,
    executar_juntada_ate_editor,
    executar_juntada,
    wrapper_juntada_com_navegacao,
)

__all__ = [
    "wrapper_juntada_geral",
    "make_juntada_wrapper",
    "create_juntador",
    "executar_juntada_ate_editor",
    "executar_juntada",
    "wrapper_juntada_com_navegacao",
]
