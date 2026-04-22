"""Fix.extracao_indexacao_fluxo — stub de compatibilidade.

Conteúdo consolidado em Fix.extraction.indexacao.
Imports daqui continuam funcionando mas emitem DeprecationWarning.
"""
import warnings
warnings.warn(
    "Fix.extracao_indexacao_fluxo está obsoleto; importe de Fix.extraction",
    DeprecationWarning,
    stacklevel=2,
)

from Fix.extraction.indexacao import (  # noqa: F401,E402
    indexar_e_processar_lista,
)

__all__ = [
    "indexar_e_processar_lista",
]
