"""Fix.extracao_documento — stub de compatibilidade.

Conteudo consolidado em Fix.extracao_conteudo.
Imports daqui continuam funcionando.
"""
import warnings
warnings.warn(
    "Fix.extracao_documento esta obsoleto; importe de Fix.extracao_conteudo",
    DeprecationWarning,
    stacklevel=2,
)
from Fix.extracao_conteudo import (  # noqa: F401,E402
    extrair_direto,
    extrair_documento,
    extrair_pdf,
    _extrair_formatar_texto,
    _normalizar_texto_decisao,
)

__all__ = ["extrair_direto", "extrair_documento", "extrair_pdf", "_extrair_formatar_texto", "_normalizar_texto_decisao"]
