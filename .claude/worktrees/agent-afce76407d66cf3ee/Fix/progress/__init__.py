"""Shim minimo de compatibilidade para o pacote legado Fix.progress."""

from ..facade_publica import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
    registrar_modulo,
    atualizar,
    completar,
)

__all__ = [
    "ProgressoUnificado",
    "carregar_progresso_unificado",
    "salvar_progresso_unificado",
    "marcar_processo_executado_unificado",
    "processo_ja_executado_unificado",
    "executar_com_monitoramento_unificado",
    "ARQUIVO_PROGRESSO_UNIFICADO",
    "registrar_modulo",
    "atualizar",
    "completar",
]
