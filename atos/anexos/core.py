"""
atos.anexos.core - Módulo principal de anexos (landing zone).

Reexporta funções dos submódulos especializados,
espelhando a API de PEC/anexos.
"""

import logging
logger = logging.getLogger(__name__)

from .anexos_extracao import (
    extrair_numero_processo_da_url,
)

from .anexos_wrappers import (
    anex_carta,
    anex_sisbconsulta,
    anex_bloqneg,
    anex_parcial,
)

from .anexos_formatacao import (
    formatar_conteudo_ecarta,
)

from PEC.anexos.anexos_sisbajud import (
    _obter_conteudo_relatorio_sisbajud,
    _wrapper_sisbajud_generico,
)

from PEC.anexos.anexos_juntador_base import (
    wrapper_juntada_geral,
    create_juntador,
    executar_juntada_ate_editor,
    executar_juntada,
)

from PEC.anexos.anexos_juntador_helpers import (
    substituir_marcador_por_conteudo,
)

from PEC.anexos.anexos_configuracao import (
    salvar_conteudo_clipboard,
)

__all__ = [
    "extrair_numero_processo_da_url",
    "anex_carta",
    "anex_sisbconsulta",
    "anex_bloqneg",
    "anex_parcial",
    "formatar_conteudo_ecarta",
    "_obter_conteudo_relatorio_sisbajud",
    "_wrapper_sisbajud_generico",
    "wrapper_juntada_geral",
    "create_juntador",
    "executar_juntada_ate_editor",
    "executar_juntada",
    "substituir_marcador_por_conteudo",
    "salvar_conteudo_clipboard",
]
