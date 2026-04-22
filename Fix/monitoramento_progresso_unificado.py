"""Fix.monitoramento_progresso_unificado — stub de compatibilidade.

O conteúdo deste módulo foi movido para Fix.progress.monitoramento.
Imports daqui continuam funcionando mas emitem DeprecationWarning.
"""
import warnings
warnings.warn(
    "Fix.monitoramento_progresso_unificado está obsoleto; importe de Fix.progress",
    DeprecationWarning,
    stacklevel=2,
)

from Fix.progress.monitoramento import (  # noqa: F401,E402
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
    CONFIGURACOES_EXECUCAO,
    extrair_numero_processo_unificado,
    verificar_acesso_negado_unificado,
    limpar_progresso_corrompido,
    # Legacy aliases
    carregar_progresso_p2b, salvar_progresso_p2b, extrair_numero_processo_p2b,
    verificar_acesso_negado_p2b, processo_ja_executado_p2b, marcar_processo_executado_p2b,
    carregar_progresso, salvar_progresso, extrair_numero_processo, verificar_acesso_negado,
    processo_ja_executado, marcar_processo_executado,
    carregar_progresso_mandado, salvar_progresso_mandado, extrair_numero_processo_mandado,
    verificar_acesso_negado_mandado, processo_ja_executado_mandado, marcar_processo_executado_mandado,
)

__all__ = [
    "ProgressoUnificado",
    "carregar_progresso_unificado",
    "salvar_progresso_unificado",
    "marcar_processo_executado_unificado",
    "processo_ja_executado_unificado",
    "executar_com_monitoramento_unificado",
    "ARQUIVO_PROGRESSO_UNIFICADO",
    "CONFIGURACOES_EXECUCAO",
    "extrair_numero_processo_unificado",
    "verificar_acesso_negado_unificado",
    "limpar_progresso_corrompido",
]
