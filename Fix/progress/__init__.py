"""Fix.progress — Sistema unificado de monitoramento de progresso.

Este pacote consolida:
  - monitoramento_progresso_unificado (implementação principal)
  - progress_models (StatusModulo, NivelLog, Checkpoint, etc.)
  - progress.py (shim legado, re-exporta API unificada)
  - progresso_unificado.py (shim de 7 linhas)

API pública:
    from Fix.progress import ProgressoUnificado, carregar_progresso_unificado, ...
    from Fix.progress import StatusModulo, NivelLog, Checkpoint, ...
"""

from Fix.progress.monitoramento import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
    CONFIGURACOES_EXECUCAO,
)

from Fix.progress.models import (
    StatusModulo,
    NivelLog,
    Checkpoint,
    StatusModuloData,
    RegistroLog,
)

__all__ = [
    # Monitoramento
    "ProgressoUnificado",
    "carregar_progresso_unificado",
    "salvar_progresso_unificado",
    "marcar_processo_executado_unificado",
    "processo_ja_executado_unificado",
    "executar_com_monitoramento_unificado",
    "ARQUIVO_PROGRESSO_UNIFICADO",
    "CONFIGURACOES_EXECUCAO",
    # Models
    "StatusModulo",
    "NivelLog",
    "Checkpoint",
    "StatusModuloData",
    "RegistroLog",
    # Legacy stubs (compatibilidade)
    "registrar_modulo",
    "atualizar",
    "completar",
]


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
