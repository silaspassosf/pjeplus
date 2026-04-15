"""Fix.extraction — Extração e indexação de processos.

API pública:
    from Fix.extraction import (
        filtrofases,
        indexar_processos,
        reindexar_linha,
        abrir_detalhes_processo,
        trocar_para_nova_aba,
        indexar_e_processar_lista,
        reindexar_e_processar_item,
    )
"""

from Fix.extraction.indexacao import (
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
