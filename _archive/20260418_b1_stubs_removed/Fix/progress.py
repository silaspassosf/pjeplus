"""Fix/progress.py — shim de compatibilidade.

Todo o rastreamento de progresso é feito exclusivamente por
Fix.progress.monitoramento, que persiste em progresso.json.

Este módulo re-exporta a API do sistema unificado e fornece stubs no-op
para nomes legados (registrar_modulo, atualizar, completar).
"""
import warnings
warnings.warn(
    "Fix.progress está obsoleto; importe de Fix.progress (pacote)",
    DeprecationWarning,
    stacklevel=2,
)

from Fix.progress import (  # noqa: F401,E402
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
    StatusModulo,
    NivelLog,
    Checkpoint,
    StatusModuloData,
    RegistroLog,
)


# Stubs no-op — compatibilidade com código que usava o sistema antigo

def registrar_modulo(nome_modulo: str, total_items: int) -> None:
    """No-op: compatibilidade legada."""


def atualizar(
    nome_modulo: str,
    processados: int = None,
    item_atual: str = None,
    proximo_item: str = None,
    erro: bool = False,
) -> None:
    """No-op: compatibilidade legada."""


def completar(nome_modulo: str, sucesso: bool = True) -> None:
    """No-op: compatibilidade legada."""


__all__ = [
    "ProgressoUnificado",
    "carregar_progresso_unificado",
    "salvar_progresso_unificado",
    "marcar_processo_executado_unificado",
    "processo_ja_executado_unificado",
    "executar_com_monitoramento_unificado",
    "ARQUIVO_PROGRESSO_UNIFICADO",
    "StatusModulo",
    "NivelLog",
    "Checkpoint",
    "StatusModuloData",
    "RegistroLog",
    "registrar_modulo",
    "atualizar",
    "completar",
]
