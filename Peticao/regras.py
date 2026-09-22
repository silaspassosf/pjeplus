"""
Thin shim — consolidado em Peticao/regras_execucao.py
Mantido para compatibilidade retroativa.
"""
from .regras_execucao import (
    classificar,
    resolver_acao,
    peticao_registry,
    _Dados,
    _dados,
    _detectar_acao_analise,
    _executar_acao,
)
