from Fix.gigs import criar_gigs
from .comunicacao_fluxo import comunicacao_judicial


def make_comunicacao_wrapper(
    tipo_expediente, 
    prazo, 
    nome_comunicacao, 
    sigilo, 
    modelo_nome, 
    subtipo=None, 
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None,
    coleta_conteudo=None,  # NOVO: parâmetro para coleta
    inserir_conteudo=None,  # NOVO: função opcional de inserção no editor
    cliques_polo_passivo=1,  # NOVO: número de cliques no polo passivo
    destinatarios='extraido',  # NOVO: seleção de destinatários
    # NOVOS: controle opcional de ações do fluxo
    mudar_expediente=None,
    checar_sp=None,
    endereco_tipo=None  # NOVO: tipo de endereço ('correios' para mudar para correios)
):
    def wrapper(driver, debug=False, **overrides):
        """
        Wrapper que aceita overrides genéricos e repassa quaisquer parâmetros fornecidos
        diretamente para `comunicacao_judicial`, tratando `mudar_expediente` como um
        parâmetro comum (como `descricao`, `prazo`, etc.).
        """
        # Resolve destinatários override explicitamente se presente
        destinatarios_param = overrides.get('destinatarios') if 'destinatarios' in overrides else destinatarios

        # Se o wrapper foi configurado com gigs_extra, executá-lo ANTES do início do fluxo
        if gigs_extra:
            try:
                if gigs_extra is True:
                    criar_gigs(driver, prazo, '', nome_comunicacao)
                elif isinstance(gigs_extra, (tuple, list)):
                    if len(gigs_extra) >= 3:
                        dias_uteis, responsavel, observacao = gigs_extra[:3]
                        criar_gigs(driver, dias_uteis, responsavel, observacao)
                    elif len(gigs_extra) == 2:
                        dias_uteis, observacao = gigs_extra
                        criar_gigs(driver, dias_uteis, '', observacao)
                    else:
                        criar_gigs(driver, gigs_extra)
                else:
                    criar_gigs(driver, gigs_extra)
            except Exception as e:
                try:
                    print(f'[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs antes do fluxo: {e}')
                except Exception:
                    pass

        # Construir kwargs a serem repassados para comunicacao_judicial
        call_kwargs = {
            'driver': driver,
            'tipo_expediente': tipo_expediente,
            'prazo': prazo,
            'nome_comunicacao': nome_comunicacao,
            'sigilo': sigilo,
            'modelo_nome': modelo_nome,
            'subtipo': overrides.get('subtipo', subtipo),
            'descricao': overrides.get('descricao', descricao if descricao else nome_comunicacao),
            'tipo_prazo': overrides.get('tipo_prazo', tipo_prazo),
            # Evitar repassar gigs_extra para não duplicar criação
            'gigs_extra': None,
            'coleta_conteudo': overrides.get('coleta_conteudo', overrides.get('coleta_conteudo_', coleta_conteudo)),
            'inserir_conteudo': overrides.get('inserir_conteudo', overrides.get('inserir_conteudo_', inserir_conteudo)),
            'cliques_polo_passivo': overrides.get('cliques_polo_passivo', cliques_polo_passivo),
            'destinatarios': destinatarios_param,
            # Passa adiante quaisquer flags de controle (mudar_expediente, checar_sp) diretamente
            'mudar_expediente': mudar_expediente,
            'checar_sp': overrides.get('checar_sp', overrides.get('checar_sp_', checar_sp)),
            'endereco_tipo': endereco_tipo,
            'debug': debug,
            'terceiro': overrides.get('terceiro', False)
        }

        return comunicacao_judicial(**call_kwargs)
    return wrapper

pec_bloqueio = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=7,
    nome_comunicacao='ciência bloqueio',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    gigs_extra=(7, 'xs - carta'),
    destinatarios='extraido'
)
pec_decisao = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=10,
    nome_comunicacao='intimação de decisão',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    # Criar GIGS na minuta (detalhe=False) -> usar tupla com 3 itens: (dias, responsavel, observacao)
    gigs_extra=(7, 'xs carta'),
    coleta_conteudo="link_ato",  # NOVO: Coleta automática de link da timeline
    inserir_conteudo='link_ato',  # NOVO: Insere link coletado no marcador '--'
    destinatarios='extraido'
)
pec_idpj = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=17,
    nome_comunicacao='defesa IDPJ',
    sigilo=False,
    modelo_nome='xidpj c',
    subtipo="Intimação",  # Adicionando subtipo explícito
    descricao="Intimação para manifestação sobre IDPJ",  # Descrição mais detalhada
    tipo_prazo='dias uteis',
    # Criar GIGS na minuta (detalhe=False)
    gigs_extra=(7, 'xs carta'),
    cliques_polo_passivo=2,  # ESPECIAL: pec_idpj precisa de 2 cliques no polo passivo
    destinatarios='extraido'
)
pec_editalidpj = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=15,
    nome_comunicacao='Defesa IDPJ',
    sigilo=False,
    modelo_nome='IDPJ (edital)',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_editaldec = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=8,
    nome_comunicacao='Decisão/Sentença',
    sigilo=False,
    modelo_nome='3Decisão (Edital)',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    coleta_conteudo="link_ato",  # NOVO: Coleta automática de link da timeline
    inserir_conteudo='link_ato',  # NOVO: Insere link coletado no marcador '--'
    destinatarios='extraido'  # CORRIGIDO: 'extraido' para selecionar destinatários do polo passivo
)
pec_cpgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado CP',
    sigilo=False,
    modelo_nome='mdd cp geral',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_mddgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=8,
    nome_comunicacao='Mandado',
    sigilo=False,
    modelo_nome='02 - gené',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_mddaud = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado citação',
    sigilo=False,
    modelo_nome='xmdd aud',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_editalaud = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=1,
    nome_comunicacao='Citação',
    sigilo=False,
    modelo_nome='1cit',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_sigilo = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=30,
    nome_comunicacao='ciência decisão',
    sigilo=True,
    modelo_nome='xdecsig',
    subtipo="Intimação",  # Adicionando subtipo explícito
    descricao="decisão sigilosa",
    destinatarios='polo_ativo'  # MODIFICADO: Define destinatário como polo ativo
)

# Novos wrappers solicitados: pec_ord e pec_sum
pec_ord = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zordd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None
)

pec_sum = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zsumd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None
)

# ====================================================
# BLOCO 3 - MOVIMENTOS (importado de mov.py)
# ====================================================
