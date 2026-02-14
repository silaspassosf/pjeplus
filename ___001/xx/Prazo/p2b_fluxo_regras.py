import logging
import re
import time
from typing import List, Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .p2b_core import gerar_regex_geral, parse_gigs_param, ato_pesqliq_callback
from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve

logger = logging.getLogger(__name__)


def _definir_regras_processamento() -> List[Tuple]:
    """
    Helper: Define lista de regras SEQUENCIAIS baseada no p2b.py ORIGINAL.
    Mantém EXATAMENTE os mesmos termos e ordem de precedência.

    Returns:
        Lista de tuplas (keywords, tipo_acao, params, acao_secundaria)
    """
    # Lazy load modules necessários para as regras
    m = _lazy_import()
    mov_arquivar = m['mov_arquivar']
    ato_180 = m['ato_180']
    ato_calc2 = m['ato_calc2']
    ato_prev = m['ato_prev']
    ato_meios = m['ato_meios']
    ato_sobrestamento = m['ato_sobrestamento']
    
    return [
        # REGRA DE PRESCRIÇÃO - MÁXIMA PRIORIDADE
        ([re.compile(r'A pronúncia da', re.IGNORECASE)],
         None, None, None),  # prescreve será chamado separadamente

        # REGRA DE BLOQUEIO - DEVE VIR ANTES PARA TER PRIORIDADE
        ([gerar_regex_geral(k) for k in ['sob pena de bloqueio']],
         'checar_cabecalho_impugnacoes', None, None),

        # REGRAS DE SOBRESTAMENTO
        ([gerar_regex_geral(k) for k in [
            '05 dias para a apresentação',
            'suspensão da execução, com fluência',
            '05 dias para oferta',
            'concede-se 05 dias para oferta',
            'cinco dias para apresentação',
            'cinco dias para oferta',
            'cinco dias para apresentacao',
            'concedo o prazo de oito dias',
            'meios  efetivos  para  o prosseguimento da execução',
            'visibilidade aos advogados',
            'início da fluência',
            'oito dias para apresentação',
            'oito dias para apresentacao',
            'Reitere-se a intimação para que o(a) reclamante apresente cálculos',
            'remessa ao sobrestamento, com fluência',
            'sob pena de sobrestamento e fluência do prazo prescricional',
        ]],
         'gigs', '1//xs sob 24', ato_sobrestamento),

        # REGRAS DE HOMOLOGAÇÃO
        ([gerar_regex_geral(k) for k in [
            'é revel, não',
            'concorda com homologação',
            'concorda com homologacao',
            'tomarem ciência dos esclarecimentos apresentados',
            'no prazo de oito dias, impugnar',
            'concordância quanto à imediata homologação da conta',
            'conclusos para homologação de cálculos',
            'ciência do laudo técnico apresentado',
            'homologação imediata',
            'aceita a imediata homologação',
            'aceita a imediata homologacao',
            'informar se aceita a imediata homologação',
            'apresentar impugnação, querendo',            
        ]],
         'gigs', '-1//SILVIA - Homologação', None),

        # REGRA DE EMBARGOS
        ([gerar_regex_geral('exequente, ora embargado')],
         'gigs', '1/fernanda/julgamento embargos', None),

        # REGRA DE PEC
        ([gerar_regex_geral(k) for k in ['hasta', 'saldo devedor']],
         'gigs', '1//xs saldo', None),

        # REGRA DE DESCUMPRIMENTO
        ([gerar_regex_geral('Ante a notícia de descumprimento')],
         'checar_cabecalho', None, None),

        # REGRA DE IMPUGNAÇÕES
        ([gerar_regex_geral(k) for k in ['impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes', 'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro', 'comprovar a quitação', 'comprovar o pagamento', 'a reclamada para pagamento da parcela pendente', 'intime-se a reclamada para pagamento das', 'homologo os calculos']],
         'checar_cabecalho_impugnacoes', None, None),

        # REGRA DE ARQUIVAMENTO
        ([gerar_regex_geral(k) for k in ['arquivem-se os autos', 'remetam-se os autos ao aquivo', 'A pronúncia da prescrição intercorrente se trata', 'Se revê o novo sobrestamento', 'cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']],
         'movimentar', mov_arquivar, None),

        # REGRA DE BLOQUEIO CONVERTIDO
        ([gerar_regex_geral('bloqueio realizado, ora convertido')], 'gigs', '-1//Bruna - Liberação', None),

        # REGRA DE PARCELAMENTO
        ([gerar_regex_geral('sobre o preenchimento dos pressupostos legais para concessão do parcelamento')],
         'gigs', '1/Bruna/Liberação', None),

        # REGRA DE RECOLHIMENTO
        ([gerar_regex_geral(k) for k in ['comprovar recolhimento', 'comprovar recolhimentos']],
         'gigs', '1/Silvia/Argos', ato_pesqliq_callback),

        # REGRA DE BAIXA/AGUARDE-SE (Conjunto específico que chama checar_prox)
        ([gerar_regex_geral(k) for k in ['determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição', 'art. 112 do CPC', 'comunique-se por Edital', 'Aguarde-se', 'mantenho o despacho', 'mantenho a decisão', 'edital de intimação de decisão', 'sob pena de preclusão']],
         'checar_prox', None, None),

        # REGRA DE PENHORA
        ([gerar_regex_geral('Defiro a penhora no rosto dos autos')],
         'gigs', '1//xs sob 6', ato_180),

        # REGRA DE CÁLCULOS
        ([gerar_regex_geral('RECLAMANTE para apresentar cálculos de liquidação')],
         None, None, ato_calc2),

        # REGRA DE TENTATIVAS
        ([gerar_regex_geral('deverá realizar tentativas')],
         None, None, ato_prev),

        # REGRA DE INSTAURAÇÃO
        ([gerar_regex_geral('defiro a instauração')],
         'checar_anexos_instauracao', None, None),

        # REGRA DE TENDO EM VISTA
        ([gerar_regex_geral(k) for k in ['tendo em vista que', 'pagamento da parcela pendente', 'sob pena de sequestro']],
         'checar_anexos_tendo_em_vista', None, None),

        # REGRA DE NÃO AMPARADA
        ([gerar_regex_geral('não está amparada')],
         None, None, ato_meios),

        # REGRA DE INSTAURADO EM FACE
        ([gerar_regex_geral('instaurado em face')],
         None, None, 'idpj'),
    ]


def _processar_regras_gerais(driver: WebDriver, texto_normalizado: str, doc_idx: int = 0):
    """
    Helper: Processa regras gerais usando abordagem SEQUENCIAL do p2b.py ORIGINAL.
    Mantém ordem de precedência: prescrição > arquivamento > bloqueio > regras gerais

    Args:
        driver: WebDriver instance
        texto_normalizado: Texto normalizado para análise
        doc_idx: Índice atual do documento na timeline (para checar_prox)

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx) se checar_prox encontrou próximo documento,
        None caso contrário
    """
    # Lazy load modules
    m = _lazy_import()
    mov_arquivar = m['mov_arquivar']
    criar_gigs = m['criar_gigs']
    
    regras = _definir_regras_processamento()

    # 5. VERIFICAÇÃO DE PREVALÊNCIA: prescreve tem prioridade absoluta
    regex_prescreve = gerar_regex_geral('A pronúncia da')
    if regex_prescreve.search(texto_normalizado):
        pass
        try:
            prescreve(driver)  # Será implementado quando necessário
            pass
            return  # SAIR imediatamente
        except Exception as prescreve_error:
            logger.error(f'[FLUXO_PZ]  Erro na execução de prescreve: {prescreve_error}')
            # Continua com regras normais se prescreve falhar

    # 5.1. VERIFICAÇÃO DE PREVALÊNCIA: arquivamento tem prioridade máxima sobre outras regras
    regex_arquivamento = gerar_regex_geral('julgo extinta a presente execução, nos termos do art. 924')
    if regex_arquivamento.search(texto_normalizado):
        pass
        try:
            resultado_arquivamento = mov_arquivar(driver)
            if resultado_arquivamento:
                pass
                return  # SAIR imediatamente
            else:
                pass
        except Exception as arquivamento_error:
            logger.error(f'[FLUXO_PZ]  Erro na execução de arquivamento: {arquivamento_error}')
            # Continua com regras normais se arquivamento falhar

    # 6. Iterate through rules and keywords to find the first match
    acao_definida = None
    parametros_acao = None
    termo_encontrado = None
    acao_secundaria = None  # Reset before checking rules

    pass

    for idx, (keywords, tipo_acao, params, acao_sec) in enumerate(regras):
        for regex in keywords:
            match = regex.search(texto_normalizado)
            if match:
                # Log da regra encontrada
                pass
                pass
                pass
                pass
                acao_definida = tipo_acao
                parametros_acao = params
                acao_secundaria = acao_sec
                termo_encontrado = regex.pattern
                # NOVA REGRA: se acao_definida == 'checar_prox', chamar checar_prox imediatamente
                if acao_definida == 'checar_prox':
                    from Prazo.p2b_core import checar_prox
                    # Obter itens da timeline para checar_prox
                    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                    pass
                    prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                    if prox_doc_encontrado and prox_doc_link:
                        pass
                        # Retornar os valores encontrados para que o fluxo continue com o próximo documento
                        return prox_doc_encontrado, prox_doc_link, prox_doc_idx
                    else:
                        pass
                break
        if acao_definida:
            break

    # Log se nenhuma regra foi encontrada
    if not acao_definida:
        pass
        pass
        pass
        # Buscar especificamente por "comprovar" para debug
        if 'comprovar' in texto_normalizado:
            idx = texto_normalizado.find('comprovar')
            pass
            pass
        else:
            pass

    # 6. Perform action(s) based on the matched rule (or default)
    import datetime
    gigs_aplicado = False
    if acao_definida == 'gigs':
        # parametros_acao já está no formato 'dias/responsavel/observacao'
        try:
            pass
            pass

            dias, responsavel, observacao = parse_gigs_param(parametros_acao)
            criar_gigs(driver, dias, responsavel, observacao)
            gigs_aplicado = True
            pass

            if acao_secundaria:
                # Tratamento especial para função 'idpj'
                if acao_secundaria == 'idpj':
                    pass
                    try:
                        from atos import idpj
                        resultado_idpj = idpj(driver, debug=True)
                        pass
                    except Exception as idpj_error:
                        logger.error(f'[FLUXO_PZ] Falha ao executar IDPJ: {idpj_error}')
                else:
                    pass
                    try:
                        resultado_callback = acao_secundaria(driver)
                        pass
                    except TypeError:
                        acao_secundaria(driver)
                time.sleep(1)
        except Exception as gigs_error:
            logger.error(f'[FLUXO_PZ] Falha ao criar GIGS ou na ação secundária: {gigs_error}')

    elif acao_definida == 'movimentar':
         func_movimento = parametros_acao
         pass
         try:
             resultado_movimento = func_movimento(driver)
             if resultado_movimento:
                 pass
             else:
                 logger.error(f'[FLUXO_PZ] Movimentação {func_movimento.__name__} FALHOU (retornou False).')
         except Exception as mov_error:
             logger.error(f'[FLUXO_PZ] Falha ao executar movimentação {func_movimento.__name__}: {mov_error}')

    elif acao_definida == 'checar_cabecalho':
        from .p2b_fluxo_cabecalho import _processar_checar_cabecalho
        _processar_checar_cabecalho(driver)

    elif acao_definida == 'checar_cabecalho_impugnacoes':
        from .p2b_fluxo_cabecalho import _processar_cabecalho_impugnacoes
        _processar_cabecalho_impugnacoes(driver)

    # Se não há ação primária mas existe ação secundária, trate a secundária como primária
    if acao_definida is None and acao_secundaria:
        # Tratamento especial para função 'idpj'
        if acao_secundaria == 'idpj':
            pass
            try:
                from atos import idpj
                resultado_idpj = idpj(driver, debug=True)
                if resultado_idpj:
                    pass
                else:
                    pass
            except Exception as idpj_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar função IDPJ: {idpj_error}')
        else:
            pass
            try:
                acao_secundaria(driver)
                time.sleep(1)
            except Exception as sec_error:
                logger.error(f'[FLUXO_PZ] Falha ao executar ação {acao_secundaria.__name__}: {sec_error}')