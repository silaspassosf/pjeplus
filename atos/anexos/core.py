"""atos.anexos.core - API pública do motor único de anexos/juntada."""

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
    anex_retifidpj,
    anex_devcp,
)

from .anexos_formatacao import (
    formatar_conteudo_ecarta,
)

from .anexos_sisbajud import (
    _obter_conteudo_relatorio_sisbajud,
    _wrapper_sisbajud_generico,
    executar_juntada_pje,
)

from .anexos_juntador_base import (
    wrapper_juntada_geral,
    wrapper_juntada_com_navegacao,
    create_juntador,
    executar_juntada_ate_editor,
    executar_juntada,
)

from .anexos_juntador_helpers import (
    substituir_marcador_por_conteudo,
)

from .anexos_configuracao import (
    salvar_conteudo_clipboard,
)

__all__ = [
    "extrair_numero_processo_da_url",
    "anex_carta",
    "anex_sisbconsulta",
    "anex_bloqneg",
    "anex_parcial",
    "anex_retifidpj",
    "anex_devcp",
    "formatar_conteudo_ecarta",
    "_obter_conteudo_relatorio_sisbajud",
    "_wrapper_sisbajud_generico",
    "wrapper_juntada_geral",
    "wrapper_juntada_com_navegacao",
    "create_juntador",
    "executar_juntada_ate_editor",
    "executar_juntada",
    "executar_juntada_pje",
    "substituir_marcador_por_conteudo",
    "salvar_conteudo_clipboard"
]
