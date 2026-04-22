"""
PEC.anexos.core - Módulo principal de anexos PEC (refatorado).

Este módulo agora serve como wrapper que importa e reexporta todas as funções
dos módulos especializados criados durante a refatoração.

Módulos especializados:
- anexos_extracao: Funções de extração de dados
- anexos_wrappers: Wrappers específicos para diferentes tipos de juntada
- anexos_formatacao: Funções de formatação de conteúdo
- anexos_sisbajud: Funções específicas SISBAJUD
- anexos_juntador: Classe Juntador e métodos de juntada automática
- anexos_gigs: Funções específicas do GIGS plugin
- anexos_configuracao: Funções de configuração e utilitários
"""

import logging
logger = logging.getLogger(__name__)

# Imports dos módulos refatorados - ATOS (mantidos para compatibilidade)
from atos import (
    fluxo_cls,
    ato_judicial,
    mov,
    idpj,
    make_ato_wrapper,
    make_comunicacao_wrapper,
    selecionar_opcao_select
)

# Imports dos módulos refatorados - PEC (compatibilidade opcional)
# Temporariamente desabilitado - as funções serão importadas diretamente dos módulos
# try:
#     from PEC import (
#         analisar_documentos_pos_carta,
#         aplicar_filtro_xs,
#         carregar_progresso_pec,
#         extrair_numero_processo_pec,
#         indexar_processo_atual_gigs,
#         listar_processos_pec,
#         make_pec_wrapper,
#         pec,
#         pec2,
#         pec_novo,
#         pec_novo_v2,
#         pec_novo_v3,
#         pec_novo_v4,
#         salvar_progresso_pec,
#         verificar_pec_concluido,
#     )
# except Exception as e:
#     logger.error(f"[ANEXOS][PEC] Falha ao importar PEC: {e}")

# Imports dos módulos especializados de anexos
from .anexos_extracao import (
    extrair_numero_processo_da_pagina,
    extrair_numero_processo_da_url
)

from .anexos_wrappers import (
    carta_wrapper,
    consulta_wrapper,
    wrapper_bloqneg,
    wrapper_parcial
)

from .anexos_formatacao import (
    formatar_conteudo_ecarta
)

from .anexos_sisbajud import (
    _obter_conteudo_relatorio_sisbajud,
    _wrapper_sisbajud_generico
)

from .anexos_juntador_base import (
    wrapper_juntada_geral,
    create_juntador,
    executar_juntada_ate_editor,
    executar_juntada
)

from .anexos_juntador_helpers import (
    substituir_marcador_por_conteudo
)

from .anexos_configuracao import (
    salvar_conteudo_clipboard
)

# Re-exportar funções principais para manter compatibilidade
__all__ = [
    # Funções de extração
    "extrair_numero_processo_da_pagina",
    "extrair_numero_processo_da_url",

    # Wrappers específicos
    "carta_wrapper",
    "consulta_wrapper", 
    "wrapper_bloqneg",
    "wrapper_parcial",

    # Formatação
    "formatar_conteudo_ecarta",

    # SISBAJUD
    "_obter_conteudo_relatorio_sisbajud",
    "_wrapper_sisbajud_generico",

    # Juntador
    "wrapper_juntada_geral",
    "create_juntador",
    "executar_juntada_ate_editor",
    "executar_juntada",
    "substituir_marcador_por_conteudo",

    # Configuração
    "salvar_conteudo_clipboard"
]
