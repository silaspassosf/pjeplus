"""Triagem/api.py — LEGADO: thin shim de compatibilidade.

O código ativo foi consolidado em runtime_triagem.py.
"""
from .runtime_triagem import (  # noqa: F401
    buscar_lista_triagem,
    buscar_painel_com_filtros,
    _is_triagem_inicial,
    enriquecer_processo,
    _numero_cnj,
    _normalizar_lista,
)
