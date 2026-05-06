"""
Monitoramento de progresso para Petição (PET)
Inspirado no padrão de Prazo/p2b_core.py
"""

from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
)

def carregar_progresso_pet() -> dict:
    """Carrega progresso salvo do PET."""
    try:
        return carregar_progresso_unificado('pet')
    except Exception:
        return {}

def salvar_progresso_pet(progresso: dict) -> None:
    """Salva progresso do PET."""
    try:
        salvar_progresso_unificado('pet', progresso)
    except Exception:
        pass

def marcar_processo_executado_pet(processo_id: str, progresso: dict) -> None:
    """Marca processo como executado no progresso PET."""
    try:
        marcar_processo_executado_unificado('pet', processo_id, progresso, sucesso=True)
    except Exception:
        pass

def processo_ja_executado_pet(processo_id: str, progresso: dict) -> bool:
    """Verifica se processo já foi executado no PET."""
    try:
        return processo_ja_executado_unificado(processo_id, progresso)
    except Exception:
        return False
