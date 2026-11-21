"""Módulo Prazo - Orquestrador de 7 etapas (Prazos vencidos + Cumprimento) e P2B."""
from Prazo.loop_orquestrador import (
    URL_PAINEL_CUMPRIMENTO,
    URL_PAINEL_PRAZOS_VENCIDOS,
    ciclo0,
    ciclo3,
    loop_prazo,
)

__all__ = [
    "URL_PAINEL_PRAZOS_VENCIDOS",
    "URL_PAINEL_CUMPRIMENTO",
    "loop_prazo",
    "ciclo0",
    "ciclo3",
]
