"""Tipos compartilhados do projeto PjePlus."""
from typing import TypedDict, Optional, Dict, Any


class ResultadoFluxo(TypedDict, total=False):
    """Contrato padronizado de resultado de execucao de fluxo."""
    sucesso: bool
    status: str             # "OK" | "ERRO" | "AVISO"
    erro: Optional[str]     # presente quando sucesso=False
    dados: Optional[Dict[str, Any]]  # payload opcional
