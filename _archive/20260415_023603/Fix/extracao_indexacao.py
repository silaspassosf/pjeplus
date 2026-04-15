"""Fix.extracao_indexacao — stub de compatibilidade.

O conteúdo deste módulo foi movido para Fix.extraction.indexacao.
Imports daqui continuam funcionando mas emitem DeprecationWarning.
"""
import warnings
warnings.warn(
    "Fix.extracao_indexacao está obsoleto; importe de Fix.extraction",
    DeprecationWarning,
    stacklevel=2,
)

from Fix.extraction.indexacao import (  # noqa: F401,E402
    filtrofases,
    indexar_processos,
    reindexar_linha,
    abrir_detalhes_processo,
    trocar_para_nova_aba,
    _indexar_preparar_contexto,
    _indexar_tentar_reindexar,
    _indexar_tentar_trocar_aba,
    _indexar_processar_item,
    indexar_e_processar_lista,
)

__all__ = [
    "filtrofases",
    "indexar_processos",
    "reindexar_linha",
    "abrir_detalhes_processo",
    "trocar_para_nova_aba",
    "_indexar_preparar_contexto",
    "_indexar_tentar_reindexar",
    "_indexar_tentar_trocar_aba",
    "_indexar_processar_item",
    "indexar_e_processar_lista",
]
