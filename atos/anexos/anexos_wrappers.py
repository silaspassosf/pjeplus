"""atos.anexos.anexos_wrappers — Shim retrocompatível para atos.wrappers_anex.

As definições canônicas dos wrappers de juntada agora vivem em ``atos/wrappers_anex.py``
usando a factory ``make_juntada_wrapper`` (mesmo padrão de ``wrappers_ato.py`` e ``wrappers_pec.py``).
"""
from ..wrappers_anex import (
    make_juntada_wrapper,
    anex_carta,
    anex_sisbconsulta,
    anex_bloqneg,
    anex_parcial,
    anex_retifidpj,
    anex_devcp,
    anex_poupa,
    poupa,
)

__all__ = [
    'make_juntada_wrapper',
    'anex_carta',
    'anex_sisbconsulta',
    'anex_bloqneg',
    'anex_parcial',
    'anex_retifidpj',
    'anex_devcp',
    'anex_poupa',
    'poupa',
]
