"""Fix.extracao_processo — stub de compatibilidade.

Conteudo consolidado em Fix.extracao_conteudo.
Imports daqui continuam funcionando.
"""
import warnings
warnings.warn(
    "Fix.extracao_processo esta obsoleto; importe de Fix.extracao_conteudo",
    DeprecationWarning,
    stacklevel=2,
)
from Fix.extracao_conteudo import (  # noqa: F401,E402
    extrair_dados_processo,
    extrair_destinatarios_decisao,
    salvar_destinatarios_cache,
    carregar_destinatarios_cache,
    DESTINATARIOS_CACHE_PATH,
)

__all__ = ["extrair_dados_processo", "extrair_destinatarios_decisao", "salvar_destinatarios_cache", "carregar_destinatarios_cache", "DESTINATARIOS_CACHE_PATH"]
