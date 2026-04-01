import logging
import re
import time
from typing import List, Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .p2b_core import gerar_regex_geral, parse_gigs_param, checar_prox
from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve
from Fix.core import medir_tempo

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
    ato_pesqliq = m.get('ato_pesqliq')
    ato_reitmeios = m.get('ato_reitmeios')
    # wrappers/from PEC
    retifidpj_wrapper = m.get('retifidpj_wrapper')
    pec_excluiargos = m.get('pec_excluiargos')
    # helper callable for phase routing (creates initial gigs then routes)
    try:
        from .p2b_fluxo_helpers import inicar_exec as _inicar_exec
    except Exception:
        _inicar_exec = None
    
    return [
        # REGRA DE PRESCRIÇÃO - MÁXIMA PRIORIDADE
        ([re.compile(r'A pronúncia da', re.IGNORECASE)],
         (), (), ()),  # prescreve será chamado separadamente

        # REGRA DE DESCUMPRIMENTO - executar gigs1, gigs2, ato_pesqliq (sem tentar mov_exec)
        ([gerar_regex_geral('Ante a notícia de descumprimento')], ("criar_gigs[1/Ana Lucia/Argos]", "criar_gigs[1//xs sigilo]", ato_pesqliq)),
         # REGRA DE RECURSAL - executar gigs1
        ([gerar_regex_geral('Libere-se o depósito recursal')], ("criar_gigs[-1/Ana Lucia/Alvará recursal]",)),
        # REGRA DE BLOQUEIO / IMPUGNAÇÕES - DEVE VIR ANTES PARA TER PRIORIDADE
        ([gerar_regex_geral(k) for k in [
            'sob pena de bloqueio',
            'impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes',
            'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro',
            'comprovar a quitação', 'comprovar o pagamento', 'comprovar recolhimento', 'comprovar recolhimentos',
            'a reclamada para pagamento da parcela pendente',
            'intime-se a reclamada para pagamento das', 'homologo os calculos'
        ]],
         (_inicar_exec,),),

        # REGRAS DE SOBRESTAMENTO
        ([gerar_regex_geral(k) for k in [
        'Abre-se, como reiteração',
        ]],
         ("criar_gigs[1//xs sob 24]", ato_sobrestamento)),

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
         (ato_reitmeios,)),

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
         ("criar_gigs[1/Ana Lucia do A/Homologação]",),),

        # REGRA DE EMBARGOS
        ([gerar_regex_geral('exequente, ora embargado')], ("criar_gigs[1/fernanda/julgamento embargos]",)),

        # REGRA DE EMBARGOS - quando decidido procedentes os embargos -> executar ato_meios
        ([gerar_regex_geral('procedentes os embargos'), gerar_regex_geral('procedente os embargos')], (ato_meios,),),

        # REGRA DE PEC
        ([gerar_regex_geral(k) for k in ['saldo devedor']],
         ("criar_gigs[1//xs saldo]",),),

       

        # REGRA DE ARQUIVAMENTO
        ([gerar_regex_geral(k) for k in ['arquivem-se os autos', 'remetam-se os autos ao aquivo', 'A pronúncia da prescrição intercorrente se trata', 'Se revê o novo sobrestamento', 'cumprido o acordo homologado', 'julgo extinta a presente execução, nos termos do art. 924']], (mov_arquivar,),),

        # REGRA DE BLOQUEIO CONVERTIDO
        ([gerar_regex_geral('bloqueio realizado, ora convertido')], ("criar_gigs[-1//Bruna - Liberação]",)),

        # REGRA DE PARCELAMENTO
        ([gerar_regex_geral('sobre o preenchimento dos pressupostos legais para concessão do parcelamento')], ("criar_gigs[1/Bruna/Liberação]",)),
  
        # REGRA DE PENHORA
        ([gerar_regex_geral('Defiro a penhora no rosto dos autos')], ("criar_gigs[1//xs sob 6]", ato_180)),

        # REGRA DE CÁLCULOS
        ([gerar_regex_geral('RECLAMANTE para apresentar cálculos de liquidação')], (ato_calc2,),),

        # REGRA DE TENTATIVAS
        ([gerar_regex_geral('deverá realizar tentativas')], (ato_prev,),),

        # REGRA DE INSTAURAÇÃO
        ([gerar_regex_geral('defiro a instauração')], ('checar_anexos_instauracao',)),

        # REGRA DE TENDO EM VISTA
        ([gerar_regex_geral(k) for k in ['tendo em vista que', 'pagamento da parcela pendente', 'sob pena de sequestro']], ('checar_anexos_tendo_em_vista',)),

        # REGRA DE NÃO AMPARADA
        ([gerar_regex_geral('não está amparada')], (ato_meios,),),

        # REGRA DE INSTAURADO EM FACE
        ([gerar_regex_geral('instaurado em face')], ('idpj',)),

        # REGRA ESPECIAL: pagamento da próxima parcela -> criar gigs saldo
        ([gerar_regex_geral('pagamento da próxima parcela')], ("criar_gigs[5//xs saldo]",)),

        # REGRA: INDEFIRO o pedido de desconsideração -> juntada retificação + exclusão Argos + ato_meios
        ([gerar_regex_geral('INDEFIRO o pedido de desconsideração')], (retifidpj_wrapper, pec_excluiargos, ato_meios)),

        # REGRA DE BAIXA/AGUARDE-SE (Conjunto que aciona checar_prox como helper)
        ([gerar_regex_geral(k) for k in ['determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição', 'art. 112 do CPC', 'comunique-se por Edital', 'Aguarde-se', 'mantenho o despacho', 'mantenho a decisão', 'edital de intimação de decisão', 'sob pena de preclusão', 'embargos de declaração', 'Registre-se o movimento processual adequado'] ], (checar_prox,)),
    ]


@medir_tempo('_processar_regras_gerais')
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
    mov_arquivar = m.get('mov_arquivar')
    criar_gigs = m.get('criar_gigs')
    regras = _definir_regras_processamento()

    # Prioridade absoluta: prescrição
    if gerar_regex_geral('A pronúncia da').search(texto_normalizado):
        try:
            prescreve(driver)
            return
        except Exception as e:
            logger.error('[FLUXO_PZ] prescreve falhou: %s', e)

    # Prioridade alta: arquivamento
    if gerar_regex_geral('julgo extinta a presente execução, nos termos do art. 924').search(texto_normalizado):
        try:
            if mov_arquivar:
                if mov_arquivar(driver):
                    return
        except Exception as e:
            logger.error('[FLUXO_PZ] falha em mov_arquivar: %s', e)

    # Motor simples: iterar regras em ordem e executar ações da primeira regra que casar
    for rule in regras:
        # suporte a tupla de regra com tamanho variável: (keywords, tipo_acao[, params[, acao_sec]])
        keywords = rule[0]
        tipo_acao = rule[1] if len(rule) > 1 else ()
        params = rule[2] if len(rule) > 2 else ()
        acao_sec = rule[3] if len(rule) > 3 else ()
        for regex in keywords:
            if regex.search(texto_normalizado):
                # Log
                try:
                    span = regex.search(texto_normalizado).span()
                    start = max(0, span[0] - 40)
                    end = min(len(texto_normalizado), span[1] + 40)
                    snippet = texto_normalizado[start:end].replace('\n', ' ')
                    logger.info('[FLUXO_PZ] Regra casou: pattern=%s tipo_acao=%s snippet=%s', regex.pattern, tipo_acao, snippet[:180])
                except Exception:
                    logger.info('[FLUXO_PZ] Regra casou: pattern=%s tipo_acao=%s', getattr(regex, 'pattern', str(regex)), tipo_acao)

                # Executar ação primária(s) - suporta string ou lista/tupla de ações em sequência
                try:
                    # normalizar para lista de ações e params correspondentes
                    if isinstance(tipo_acao, (list, tuple)):
                        acoes = list(tipo_acao)
                    else:
                        acoes = [tipo_acao]

                    if isinstance(params, (list, tuple)):
                        params_list = list(params)
                        # estender params_list se necessário
                        if len(params_list) < len(acoes):
                            params_list.extend([None] * (len(acoes) - len(params_list)))
                    else:
                        params_list = [params] * len(acoes)

                    def _executar_acao(action, action_param):
                        try:
                            # suporte para ação passada diretamente como callable
                            if callable(action) and not isinstance(action, str):
                                try:
                                    # Special-case: if the callable is checar_prox, provide the
                                    # full signature it expects (itens, doc_idx, regras, texto_normalizado)
                                    try:
                                        is_checar = (action is checar_prox) or (getattr(action, '__name__', '') == 'checar_prox')
                                    except Exception:
                                        is_checar = False
                                    if is_checar:
                                        try:
                                            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                                            return checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                                        except Exception:
                                            return None
                                    # Generic callable: call with driver only
                                    return action(driver)
                                except Exception as e:
                                    logger.error('[FLUXO_PZ] Erro ao executar action callable: %s', e)
                                    return None

                            # suporte à sintaxe string criar_gigs[param]
                            if isinstance(action, str):
                                try:
                                    m_g = re.match(r'^criar_gigs\[(.*)\]$', action)
                                except Exception:
                                    m_g = None
                                if m_g:
                                    param_str = m_g.group(1)
                                    try:
                                        dias, responsavel, observacao = parse_gigs_param(param_str)
                                        if criar_gigs:
                                            criar_gigs(driver, dias, responsavel, observacao)
                                    except Exception as e:
                                        logger.error('[FLUXO_PZ] criar_gigs sintaxe falhou: %s', e)
                                    return None

                            if action == 'gigs':
                                dias, responsavel, observacao = parse_gigs_param(action_param)
                                if criar_gigs:
                                    criar_gigs(driver, dias, responsavel, observacao)
                                return None

                            if action == 'movimentar':
                                try:
                                    action_param(driver)
                                except Exception as e:
                                    logger.error('[FLUXO_PZ] Erro ao movimentar: %s', e)
                                return None

                            if action == 'gigs_then_fase':
                                try:
                                    # Executa duas GIGS padrão antes do roteamento por fase
                                    try:
                                        if criar_gigs:
                                            d, r, o = parse_gigs_param('1/Ana Lucia/Argos')
                                            criar_gigs(driver, d, r, o)
                                            d2, r2, o2 = parse_gigs_param('1//xs sigilo')
                                            criar_gigs(driver, d2, r2, o2)
                                    except Exception as e_gigs:
                                        logger.error('[FLUXO_PZ] falha ao criar GIGS antes do roteamento: %s', e_gigs)

                                    from .p2b_fluxo_helpers import rotear_por_fase
                                    resultado = rotear_por_fase(driver, texto_normalizado)
                                    if isinstance(resultado, tuple) and len(resultado) == 3:
                                        return resultado
                                except Exception as e:
                                    logger.error('[FLUXO_PZ] gigs_then_fase falhou: %s', e)
                                return None

                            if action in ('fase_roteamento', 'inicar_exec'):
                                try:
                                    from .p2b_fluxo_helpers import inicar_exec
                                    resultado = inicar_exec(driver, texto_normalizado)
                                    if isinstance(resultado, tuple) and len(resultado) == 3:
                                        return resultado
                                except Exception as e:
                                    logger.error('[FLUXO_PZ] inicar_exec/fase_roteamento falhou: %s', e)
                                return None

                            if action == 'checar_prox':
                                try:
                                    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                                    prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                                    if prox_doc_encontrado and prox_doc_link:
                                        return prox_doc_encontrado, prox_doc_link, prox_doc_idx
                                except Exception:
                                    pass
                                return None

                            # desconhecido ou None -> nada
                            return None
                        except Exception as e:
                            logger.error('[FLUXO_PZ] Erro em _executar_acao(%s): %s', str(action), e)
                            return None

                    # executar ações em sequência; se alguma retornar prox_doc, propagar
                    for idx_action, act in enumerate(acoes):
                        res = _executar_acao(act, params_list[idx_action] if idx_action < len(params_list) else None)
                        if isinstance(res, tuple) and len(res) == 3:
                            return res

                except Exception as e:
                    logger.error('[FLUXO_PZ] Erro ao executar ação primária(s): %s', e)

                # Executar ação secundária (se existir)
                try:
                    if acao_sec:
                        if callable(acao_sec):
                            res = acao_sec(driver)
                            # se acao_sec retornar prox_doc, propagar
                            if isinstance(res, tuple) and len(res) == 3:
                                return res
                        elif isinstance(acao_sec, str) and acao_sec == 'idpj':
                            try:
                                from atos import idpj
                                idpj(driver, debug=True)
                            except Exception as e:
                                logger.error('[FLUXO_PZ] Falha ao executar idpj: %s', e)
                        else:
                            # tentativa genérica
                            try:
                                acao_sec(driver)
                            except Exception:
                                pass
                except Exception as e:
                    logger.error('[FLUXO_PZ] Erro ao executar ação secundária: %s', e)

                # Executou ações da primeira regra que casou — manter precedência e retornar
                return None

    # Nenhuma regra casou
    return None