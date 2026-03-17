import logging
logger = logging.getLogger(__name__)

"""
Wrappers para atos judiciais - Instâncias da factory make_ato_wrapper
"""

from .judicial_fluxo import make_ato_wrapper


# ====================================================
# WRAPPER FUNCTIONS - ATO_JUDICIAL DERIVATIVES
# ====================================================

ato_meios = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsmeios',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    Assinar=False
)

ato_100 = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='aud100',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    Assinar=False
)

ato_ratif = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xratif',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    Assinar=False
)

ato_unap = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='aud una presenc',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    Assinar=False
)

ato_crda = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='a reclda',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_crte = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xreit',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

# Função auxiliar para inserir relatório conciso SISBAJUD no modelo xsparcial
def _inserir_relatorio_conciso_sisbajud(driver, numero_processo=None, conteudo_relatorio=None, debug=True):
    """
    Insere o relatório conciso do SISBAJUD no marcador SISBAJUD do modelo xsparcial.
    Usa a mesma lógica do wrapper de juntada.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo (opcional, usado para buscar do clipboard)
        conteudo_relatorio: Conteúdo HTML do relatório (se fornecido, usa direto sem buscar clipboard)
        debug: Habilitar logs
    """
    try:
        from PEC.anexos import substituir_marcador_por_conteudo
        import os
        
        # Se conteúdo foi fornecido diretamente, usar ele
        if conteudo_relatorio:
            conteudo = conteudo_relatorio
        else:
            # Ler do arquivo específico PEC/sisbajud_conciso_ultimo.txt
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pasta raiz
            arquivo_conciso = os.path.join(base_dir, "PEC", "sisbajud_conciso_ultimo.txt")
            
            if not os.path.exists(arquivo_conciso):
                return False
            
            with open(arquivo_conciso, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
        if not conteudo:
            return False
        
        if debug:
            pass
        
        # Substituir marcador -- pelo conteúdo conciso
        resultado = substituir_marcador_por_conteudo(
            driver=driver,
            conteudo_customizado=conteudo,
            debug=debug,
            marcador='--'
        )
        
        return resultado
        
    except Exception as e:
        if debug:
            logger.error(f'[ATO_BLOQ]  Erro ao inserir relatório conciso: {e}')
            import traceback
            traceback.print_exc()
        return False

ato_bloq = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsparcial',
    prazo=None,
    marcar_pec=True,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    inserir_conteudo=_inserir_relatorio_conciso_sisbajud
)

ato_idpj = make_ato_wrapper(
    conclusao_tipo='IDPJ',
    modelo_nome='pjsem',
    prazo=8,
    marcar_pec=True,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_termoE = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xempre',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_termoS = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsocio',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_edital = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsedit',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_sobrestamento = make_ato_wrapper(
    conclusao_tipo='Suspensão',
    modelo_nome='suspf',
    prazo=0,
    marcar_pec='nao',
    movimento='12259',
    gigs=None,
    marcar_primeiro_destinatario=False,
    perito=True,
    descricao='Sobrestamento',
    Assinar=False
)

ato_prov = make_ato_wrapper(
    conclusao_tipo='Suspensão',
    modelo_nome='suspprov',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs="1/xs sob chip (sem responsavel)",
    marcar_primeiro_destinatario=False,
    perito=False,
    descricao='Aguarda principal',
    Assinar=False
)

ato_180 = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='x180',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_x90 = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='x90',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs="1/xs chip rosto",
    marcar_primeiro_destinatario=False,
    descricao='Aguarda reserva'
)

ato_pesqliq_original = make_ato_wrapper(
    conclusao_tipo='Homologação de Cálculos',
    modelo_nome='xsbacen',
    prazo=30,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='pesquisas para execucao',
    sigilo=True,
    intimar=False
)

ato_pesqliq = make_ato_wrapper(
    conclusao_tipo='Homologação de Cálculos',
    modelo_nome='xsbacen',
    prazo=30,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    sigilo=True,
    descricao='pesquisas para execucao',
    intimar=False
)

ato_calc2 = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xscalc2',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_meiosub = make_ato_wrapper(
    conclusao_tipo='Decisão Geral',
    modelo_nome='meiosub',
    prazo=None,
    marcar_pec=False,
    movimento='50071',
    gigs=None,
    marcar_primeiro_destinatario=False,
    sigilo=False
)

ato_presc = make_ato_wrapper(
    conclusao_tipo='Extinção',
    modelo_nome='ao-in',
    prazo=8,
    marcar_pec=True,
    movimento='7595',
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Prescrição Intercorrente'
)

ato_fal = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='xsfal',
    prazo=0,
    marcar_pec=False,
    movimento='50142',
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Falência'
)

ato_parcela = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsparcof',
    prazo=12,
    marcar_pec=True,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_prev = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xprev',
    prazo=10,
    marcar_pec=False,
    marcar_primeiro_destinatario=True,
    descricao='tentativa prevjud'
)
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

#  NOVO: ato_ceju para Habilitação com CEJU
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

#  NOVO: ato_respcalc para Apresentação de Cálculos
ato_respcalc = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xrespcalc',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Despacho - Apresentação de Cálculos'
)

#  NOVO: ato_assistente para Admissão de Assistentes
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

#  NOVO: ato_concor para Concordância (Liquidação)
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

#  NOVO: ato_prevjud para CAGED (Previdenciário)
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

#  NOVO: ato_ed para Embargos de Declaração
ato_ed = make_ato_wrapper(
    conclusao_tipo='Embargos',
    modelo_nome=None,
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Sentença de ED'
)