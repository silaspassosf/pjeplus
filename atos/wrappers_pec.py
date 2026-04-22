import logging
logger = logging.getLogger(__name__)

"""
Wrappers para comunicações processuais - Instâncias da factory make_comunicacao_wrapper
"""

from .comunicacao import make_comunicacao_wrapper


# ====================================================
# WRAPPER FUNCTIONS - COMUNICACAO_JUDICIAL DERIVATIVES
# ====================================================

pec_bloqueio = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=7,
    nome_comunicacao='Intimação de bloqueio',
    sigilo=False,
    modelo_nome='xpecbloq',
    subtipo='Intimação',
    descricao='Intimação de bloqueio',
    gigs_extra=(7, 'xs - carta'),
    coleta_conteudo="conteudo_formatado",
    inserir_conteudo='conteudo_formatado',
    destinatarios='polo_passivo_2x',
    wrapper_name='pec_bloqueio'
)

pec_decisao = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=10,
    nome_comunicacao='intimação de decisão',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',
    gigs_extra=(7, 'xs carta'),
    coleta_conteudo="link_ato",
    inserir_conteudo='link_ato',
    destinatarios='informado',
    endereco_tipo='correios',
    wrapper_name='pec_decisao'
)

pec_idpj = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=17,
    nome_comunicacao='defesa IDPJ',
    sigilo=False,
    modelo_nome='xidpj c',
    subtipo="Intimação",
    descricao="Intimação para manifestação sobre IDPJ",
    tipo_prazo='dias uteis',
    gigs_extra=(7, 'xs carta'),
    destinatarios='extraido',
    cliques_polo_passivo=2,
    endereco_tipo='correios'  # Alterado de mudar_expediente=True
)

pec_editalidpj = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=15,
    nome_comunicacao='Defesa IDPJ',
    sigilo=False,
    modelo_nome='IDPJ (edital)',
    subtipo='Edital',
    gigs_extra=None,
    destinatarios='polo_passivo',  # Clique no botão polo passivo 1x
    wrapper_name='pec_editalidpj'
)

pec_editaldec = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=8,
    nome_comunicacao='Decisão/Sentença',
    sigilo=False,
    modelo_nome='3Decisão (Edital)',
    subtipo='Edital',
    gigs_extra=None,
    coleta_conteudo="link_ato",
    inserir_conteudo='link_ato',
    destinatarios='',
    wrapper_name='pec_editaldec'
)

pec_cpgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado CP',
    sigilo=False,
    modelo_nome='mdd cp geral',
    subtipo='Mandado',
    gigs_extra=None,
    destinatarios='terceiros',
    wrapper_name='pec_cpgeral',
    terceiro_default=True
)

pec_excluiargos = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Exclusão de convênios',
    sigilo=False,
    modelo_nome='asa/cnib',
    subtipo='Mandado',
    gigs_extra=None,
    destinatarios='primeiro',
    wrapper_name='pec_excluiargos'
)

pec_mddgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=8,
    nome_comunicacao='Mandado',
    sigilo=False,
    modelo_nome='02 - gené',
    subtipo='Mandado',
    gigs_extra=None,
    destinatarios='polo_passivo'
)

pec_mddaud = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado citação',
    sigilo=False,
    modelo_nome='xmdd aud',
    subtipo='Mandado',
    gigs_extra=None,
    destinatarios='polo_passivo'
)

pec_editalaud = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=1,
    nome_comunicacao='Citação',
    sigilo=False,
    modelo_nome='1cit',
    subtipo='Edital',
    gigs_extra=None,
    destinatarios='polo_passivo',
    wrapper_name='pec_editalaud'
)

pec_sigilo = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=30,
    nome_comunicacao='ciência decisão',
    sigilo=True,
    modelo_nome='xdecsig',
    subtipo="Intimação",
    descricao="decisão sigilosa",
    destinatarios='polo_ativo',
    assinar=True,
    wrapper_name='pec_sigilo'
)

pec_ord = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zordd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name='pec_ord'
)

pec_sum = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zsumd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None,
    trocar_modelo=True,
    wrapper_name='pec_sum'
)

pec_ordc = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zordc',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios='polo_passivo',  # Alterado de 'polo_passivo_2x' para 'polo_passivo'
    cliques_polo_passivo=1,  # Notificação Inicial já adiciona 1x automaticamente
    endereco_tipo='correios'  # Alterado de mudar_expediente=True para endereco_tipo
)

pec_sumc = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zsumc',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios='polo_passivo',  # Alterado de 'polo_passivo_2x' para 'polo_passivo'
    cliques_polo_passivo=1,  # Notificação Inicial já adiciona 1x automaticamente
    endereco_tipo='correios'  # Alterado de mudar_expediente=True para endereco_tipo
)




