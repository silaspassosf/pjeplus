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

pec_ordc2 = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='ordc2',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios='polo_passivo',  # Adicionado para clicar no polo passivo
    cliques_polo_passivo=1,  # Notificação Inicial já adiciona 1x automaticamente
    endereco_tipo='correios'  # Adicionado para alterar expediente para correios
)

pec_sumc2 = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='sumc2',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios='polo_passivo',  # Adicionado para clicar no polo passivo
    cliques_polo_passivo=1,  # Notificação Inicial já adiciona 1x automaticamente
    endereco_tipo='correios'  # Adicionado para alterar expediente para correios
)


# ====================================================
# WRAPPERS COM DOMICÍLIO ELETRÔNICO - xs ord / xs sum
# ====================================================

def wrapper_pec_ord_com_domicilio(driver, debug=False, **kwargs):
    """Wrapper para xs ord com decisão por domicílio eletrônico.
    
    Lógica:
    - SÓ COM domicílio: executa pec_ord
    - SÓ SEM domicílio: executa pec_ordc
    - MISTURADO: executa pec_ord + pec_ordc
    """
    from Fix.variaveis import session_from_driver, PjeApiClient
    from Fix.core import extrair_id_processo
    
    try:
        id_processo = extrair_id_processo(driver)
        if not id_processo:
            return pec_ord(driver, debug=debug, **kwargs)
        
        sess, trt = session_from_driver(driver)
        client = PjeApiClient(sess, trt)
        partes = client.partes(id_processo)
        
        if not partes:
            return pec_ord(driver, debug=debug, **kwargs)
        
        # Contar domicílio nas reclamadas
        reclamadas = [p for p in partes if p.get('poloProcessual', '').lower() in ['passivo', 'reclamada']]
        if not reclamadas:
            return pec_ord(driver, debug=debug, **kwargs)
        
        com_domicilio = sum(
            1 for p in reclamadas 
            if client.domicilio_eletronico(str(p.get('id') or p.get('idParte'))) is True
        )
        sem_domicilio = len(reclamadas) - com_domicilio
        
        logger.info(f"[PEC_ORD]  {com_domicilio} com domicílio, {sem_domicilio} sem")
        
        if sem_domicilio == 0:
            logger.info("[PEC_ORD] → Executa pec_ord")
            pec_ord(driver, debug=debug, **kwargs)
        elif com_domicilio == 0:
            logger.info("[PEC_ORD] → Executa pec_ordc")
            pec_ordc(driver, debug=debug, **kwargs)
        else:
            logger.info("[PEC_ORD] → Executa pec_ord + pec_ordc")
            pec_ord(driver, debug=debug, **kwargs)
            pec_ordc(driver, debug=debug, **kwargs)
        
        from .wrappers_mov import mov_aud
        logger.info("[PEC_ORD] → Executa mov_aud")
        return mov_aud(driver, debug=debug)
            
    except Exception as e:
        logger.info(f"[PEC_ORD] Erro: {e} → pec_ord")
        pec_ord(driver, debug=debug, **kwargs)
        from .wrappers_mov import mov_aud
        logger.info("[PEC_ORD] → Fallback: Executa mov_aud")
        return mov_aud(driver, debug=debug)


def wrapper_pec_sum_com_domicilio(driver, debug=False, **kwargs):
    """Wrapper para xs sum com decisão por domicílio eletrônico.
    
    Lógica:
    - SÓ COM domicílio: executa pec_sum
    - SÓ SEM domicílio: executa pec_sumc
    - MISTURADO: executa pec_sum + pec_sumc
    """
    from Fix.variaveis import session_from_driver, PjeApiClient
    from Fix.core import extrair_id_processo
    
    try:
        id_processo = extrair_id_processo(driver)
        if not id_processo:
            return pec_sum(driver, debug=debug, **kwargs)
        
        sess, trt = session_from_driver(driver)
        client = PjeApiClient(sess, trt)
        partes = client.partes(id_processo)
        
        if not partes:
            return pec_sum(driver, debug=debug, **kwargs)
        
        # Contar domicílio nas reclamadas
        reclamadas = [p for p in partes if p.get('poloProcessual', '').lower() in ['passivo', 'reclamada']]
        if not reclamadas:
            return pec_sum(driver, debug=debug, **kwargs)
        
        com_domicilio = sum(
            1 for p in reclamadas 
            if client.domicilio_eletronico(str(p.get('id') or p.get('idParte'))) is True
        )
        sem_domicilio = len(reclamadas) - com_domicilio
        
        logger.info(f"[PEC_SUM]  {com_domicilio} com domicílio, {sem_domicilio} sem")
        
        if sem_domicilio == 0:
            logger.info("[PEC_SUM] → Executa pec_sum")
            pec_sum(driver, debug=debug, **kwargs)
        elif com_domicilio == 0:
            logger.info("[PEC_SUM] → Executa pec_sumc")
            pec_sumc(driver, debug=debug, **kwargs)
        else:
            logger.info("[PEC_SUM] → Executa pec_sum + pec_sumc")
            pec_sum(driver, debug=debug, **kwargs)
            pec_sumc(driver, debug=debug, **kwargs)
        
        from .wrappers_mov import mov_aud
        logger.info("[PEC_SUM] → Executa mov_aud")
        return mov_aud(driver, debug=debug)
            
    except Exception as e:
        logger.info(f"[PEC_SUM] Erro: {e} → pec_sum")
        pec_sum(driver, debug=debug, **kwargs)
        from .wrappers_mov import mov_aud
        logger.info("[PEC_SUM] → Fallback: Executa mov_aud")
        return mov_aud(driver, debug=debug)
