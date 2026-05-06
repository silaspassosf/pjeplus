"""
SISB Integration - Módulo de integração com PJE
Funções para juntada automática e atualização de relatórios
"""

from .pje_integration import (
    _atualizar_relatorio_com_segundo_protocolo,
    _executar_juntada_pje
)

__all__ = [
    '_atualizar_relatorio_com_segundo_protocolo',
    '_executar_juntada_pje'
]
