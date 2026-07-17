"""
Mandado/atos_wrapper.py - Wrapper para importar funções de atos

Importa funções ato_* do módulo atos/ (modularizado)
"""

# Re-exporta funções do módulo atos/
from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub,
)

__all__ = [
    'ato_judicial',
    'ato_meios',
    'ato_pesquisas',
    'ato_crda',
    'ato_crte',
    'ato_bloq',
    'ato_idpj',
    'ato_termoE',
    'ato_termoS',
    'ato_edital',
    'pec_idpj',
    'mov_arquivar',
    'ato_meiosub',
]
