"""
Wrappers para atos judiciais - Instâncias da factory make_ato_wrapper
"""

from ..core.log import get_module_logger

logger = get_module_logger(__name__)

# Import necessário para os wrappers - esta função provavelmente está em judicial_fluxo
try:
    from atos.judicial_fluxo import make_ato_wrapper
except ImportError:
    # Placeholder para manter a compatibilidade caso judicial_fluxo não esteja disponível
    def make_ato_wrapper(**kwargs):
        def wrapper(driver):
            logger.warning(f"[ATO_WRAPPER] Função make_ato_wrapper não disponível. Parâmetros: {kwargs}")
            return False
        return wrapper


# ====================================================
# WRAPPER FUNCTIONS - ATO_JUDICIAL DERIVATIVES
# ====================================================

ato_instc = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='instrumento em r',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Instrumento'
)

ato_inste = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='instrumento em a',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Instrumento'
)

ato_gen = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome=None,
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Despacho'
)

ato_laudo = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='Geral - Ciência do laudo pericial',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciência Laudo'
)

ato_esc = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='Conhecimento - Ciência dos esclarecimentos do Perito',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciência esclarecimentos'
)

ato_escliq = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='aos esclare',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciência esclarecimentos'
)

ato_datalocal = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='data da pericia',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciência dados perícia'
)

ato_ceju = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='sse na rem',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Interesse CEJUSC'
)

ato_respcalc = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xrespcalc',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Contestar Cálculos'
)

ato_concor = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='cia com os c',
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Informar Concordância'
)

ato_prevjud = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='ere prevjud',
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Defere Previdenciário'
)

ato_naocoaf = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='ere coaf',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Indefere COAF'
)

ato_naosimba = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='a - indeferime',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Indefere Simba'
)

ato_teim = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='e teimosinha',
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    descricao='Teimosinha',
    intimar=False,
    sigilo=True
)

ato_adesivo = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='recebade',
    prazo=8,
    marcar_pec=False,
    movimento=1059,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de Recurso Adesivo'
)

ato_agpetidpj = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='o em idpj',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Petição em IDPJ'
)

ato_agpet = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='recebagp',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Petição'
)

ato_agpinter = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='o interloc',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Não-Recebimento de agravo de Petição'
)

ato_assistente = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='de assis',
    prazo=1,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Admissão de Assistentes'
)

ato_homacordo = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='homaco',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Homologação de Acordo'
)

ato_uber = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='uberoficio',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Ofício Uber'
)

ato_ccs = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='e ccs',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='defere ccs'
)

ato_censec = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='e censec',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='defere censec'
)

ato_serp = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xserp',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='defere SERP'
)

ato_conv = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xconvx',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='despacho'
)