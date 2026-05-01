"""Shim mínimo de compatibilidade para o pacote legado Fix.progress."""

from .monitoramento import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
)


def registrar_modulo(nome_modulo: str, total_items: int) -> None:
    """Compatibilidade legada: no-op."""


def atualizar(
    nome_modulo: str,
    processados: int = None,
    item_atual: str = None,
    proximo_item: str = None,
    erro: bool = False,
) -> None:
    """Compatibilidade legada: no-op."""


def completar(nome_modulo: str, sucesso: bool = True) -> None:
    """Compatibilidade legada: no-op."""


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