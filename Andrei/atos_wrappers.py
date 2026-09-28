"""
Andrei/atos_wrappers.py - Wrappers pre-configurados de atos judiciais PJe.

Fornece todas as instancias ato_* pre-configuradas via make_ato_wrapper
para uso direto no orquestrador de peticoes.

Uso:
    from Andrei.atos_wrappers import ato_instc, ato_laudo, ...
    sucesso, sigilo = ato_instc(driver)
"""

import logging

from Andrei.atos_judicial import make_ato_wrapper

logger = logging.getLogger(__name__)

__all__ = [
    "ato_instc",
    "ato_inste",
    "ato_gen",
    "ato_laudo",
    "ato_esc",
    "ato_escliq",
    "ato_datalocal",
    "ato_ceju",
    "ato_respcalc",
    "ato_contestar",
    "ato_revel",
    "ato_concor",
    "ato_prevjud",
    "ato_naocoaf",
    "ato_naosimba",
    "ato_teim",
    "ato_adesivo",
    "ato_agpetidpj",
    "ato_agpet",
    "ato_agpinter",
    "ato_assistente",
    "ato_homacordo",
    "ato_uber",
    "ato_ccs",
    "ato_censec",
    "ato_serp",
    "ato_conv",
]

# ==============================================================================
# RECURSOS - Agravo de Instrumento
# ==============================================================================

ato_instc = make_ato_wrapper(
    conclusao_tipo="Admissibilidade",
    modelo_nome="instrumento em r",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Recebimento de agravo de Instrumento",
)

ato_inste = make_ato_wrapper(
    conclusao_tipo="Admissibilidade",
    modelo_nome="instrumento em a",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Recebimento de agravo de Instrumento",
)

# ==============================================================================
# DESPACHOS GERAIS
# ==============================================================================

ato_gen = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome=None,
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="Despacho",
)

# ==============================================================================
# PERICIAS
# ==============================================================================

ato_laudo = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="Geral - Ciencia do laudo pericial",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Ciencia Laudo",
)

ato_esc = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="Conhecimento - Ciencia dos esclarecimentos do Perito",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Ciencia esclarecimentos",
)

ato_escliq = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="aos esclare",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Ciencia esclarecimentos",
)

ato_datalocal = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="data da pericia",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Ciencia dados pericia",
)

ato_ceju = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="sse na rem",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Interesse CEJUSC",
)

# ==============================================================================
# CALCULOS / CONTESTACAO
# ==============================================================================

ato_respcalc = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="xrespcalc",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Contestar Calculos",
)

ato_contestar = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome=None,
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Contestar Calculos de Liquidacao",
)

ato_revel = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome=None,
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Revel - Apresentar Calculos",
)

# ==============================================================================
# CONCORDANCIA / PREVIDENCIARIO
# ==============================================================================

ato_concor = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="cia com os c",
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Informar Concordancia",
)

ato_prevjud = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="ere prevjud",
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Defere Previdenciario",
)

# ==============================================================================
# INDEFERIMENTOS (COAF, SIMBA)
# ==============================================================================

ato_naocoaf = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="ere coaf",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="Indefere COAF",
)

ato_naosimba = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="a - indeferime",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="Indefere Simba",
)

# ==============================================================================
# TEIMOSINHA
# ==============================================================================

ato_teim = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="e teimosinha",
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    descricao="Teimosinha",
    intimar=False,
    sigilo=True,
)

# ==============================================================================
# RECURSOS - Adesivo, Agravo de Peticao, Agravo de Instrumento
# ==============================================================================

ato_adesivo = make_ato_wrapper(
    conclusao_tipo="Admissibilidade",
    modelo_nome="recebade",
    prazo=8,
    marcar_pec=False,
    movimento=1059,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Recebimento de Recurso Adesivo",
)

ato_agpetidpj = make_ato_wrapper(
    conclusao_tipo="Admissibilidade",
    modelo_nome="o em idpj",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Recebimento de agravo de Peticao em IDPJ",
)

ato_agpet = make_ato_wrapper(
    conclusao_tipo="Admissibilidade",
    modelo_nome="recebagp",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Recebimento de agravo de Peticao",
)

ato_agpinter = make_ato_wrapper(
    conclusao_tipo="Admissibilidade",
    modelo_nome="o interloc",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Nao-Recebimento de agravo de Peticao",
)

# ==============================================================================
# ASSISTENTE / HOMOLOGACAO
# ==============================================================================

ato_assistente = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="de assis",
    prazo=1,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao="Admissao de Assistentes",
)

ato_homacordo = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="homaco",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="Homologacao de Acordo",
)

# ==============================================================================
# OFICIOS ESPECIFICOS
# ==============================================================================

ato_uber = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="uberoficio",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="Oficio Uber",
)

ato_ccs = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="e ccs",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="defere ccs",
)

ato_censec = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="e censec",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="defere censec",
)

ato_serp = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="xserp",
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="defere SERP",
)

ato_conv = make_ato_wrapper(
    conclusao_tipo="Despacho",
    modelo_nome="xconvx",
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao="despacho",
)
