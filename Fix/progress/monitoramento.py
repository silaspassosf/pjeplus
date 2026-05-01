"""Compatibilidade para o namespace legado Fix.progress.monitoramento."""

from Fix.monitoramento_progresso_unificado import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
)

__all__ = [
    "ProgressoUnificado",
    "carregar_progresso_unificado",
    "salvar_progresso_unificado",
    "marcar_processo_executado_unificado",
    "processo_ja_executado_unificado",
    "executar_com_monitoramento_unificado",
    "ARQUIVO_PROGRESSO_UNIFICADO",
]