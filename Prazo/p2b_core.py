"""Shim — re-exporta do modulo consolidado p2b_regras_execucao para compatibilidade.

Importado por: p2b_gateway.py, p2b_documentos.py, carta/anexos.py, Mandado/regras.py
"""
from Prazo.p2b_regras_execucao import (
    carregar_progresso_p2b,
    salvar_progresso_p2b,
    marcar_processo_executado_p2b,
    processo_ja_executado_p2b,
    normalizar_texto,
    parse_gigs_param,
    gerar_regex_geral,
    checar_prox,
    calc1,
    remover_acentos,
    RegraProcessamento,
    REGEX_PATTERNS,
    SCRIPT_ANALISE_TIMELINE,
)

__all__ = [
    'carregar_progresso_p2b', 'salvar_progresso_p2b',
    'marcar_processo_executado_p2b', 'processo_ja_executado_p2b',
    'normalizar_texto', 'parse_gigs_param', 'gerar_regex_geral',
    'checar_prox', 'calc1', 'remover_acentos',
    'RegraProcessamento', 'REGEX_PATTERNS', 'SCRIPT_ANALISE_TIMELINE',
]
