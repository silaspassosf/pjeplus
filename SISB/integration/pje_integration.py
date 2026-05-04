"""
SISB Integration PJe - Thin shim LEGADO.

LEGADO: Conteudo movido para SISB/relatorios_integracao.py (SX4).
Mantido para compatibilidade de import.
"""
from ..relatorios_integracao import (  # noqa: E402, F401
    _atualizar_relatorio_com_segundo_protocolo,
    _executar_juntada_pje,
)

__all__ = [
    '_atualizar_relatorio_com_segundo_protocolo',
    '_executar_juntada_pje',
]
