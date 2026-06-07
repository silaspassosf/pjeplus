"""Prazo P2B - Documentos (Extracao + Regras)

Consolidado de: p2b_fluxo_documentos.py, p2b_fluxo_regras.py
"""

# ── Imports ──
import logging
import re
import time
from typing import Any, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .p2b_core import gerar_regex_geral, parse_gigs_param, checar_prox, calc1
from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve
from Fix.core import medir_tempo
from core.rule_registry import RuleRegistry

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 1. p2b_fluxo_documentos.py
# ═══════════════════════════════════════════


def _encontrar_documento_relevante(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], int]:
    """
    Helper: Encontra documento relevante (decisão/despacho/sentença) na timeline.

     CORRIGIDO: Busca APENAS no tipo real do documento (primeiro <span> dentro do link),
    não na descrição completa que pode conter termos enganosos.

    Exemplo correto: <span>Sentença</span><span>(Prescrição...)</span>
    Exemplo incorreto: <span>Edital</span><span>(Decisão/Sentença)</span> <- o tipo é EDITAL, não Decisão

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx)
    """
    # Preferir funções já existentes no projeto (Fix.documents) — comportamento legado
    try:
        from Fix.core import buscar_documentos_sequenciais, verificar_documento_decisao_sentenca

        # Se existir um bloco sequencial (ARGOS), ele já retorna os elementos na ordem correta
        try:
            docs = buscar_documentos_sequenciais(driver, log=False)
            if docs:
                # Retornar o primeiro elemento que possua um link clicável
                for idx, elem in enumerate(docs):
                    try:
                        try:
                            link = elem.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        except Exception:
                            links = elem.find_elements(By.TAG_NAME, 'a')
                            link = None
                            for l in links:
                                try:
                                    if l.is_displayed():
                                        link = l
                                        break
                                except Exception:
                                    continue
                        if link:
                            return elem, link, idx
                    except Exception:
                        continue
        except Exception:
            # Se a busca sequencial falhar, continuar para heurística DOM abaixo
            pass

        # Se não encontrou via sequencial, tentar apenas verificar se existe decisão/sentença
        try:
            if verificar_documento_decisao_sentenca(driver):
                # fallback para heurística DOM se a verificação retorna True
                pass
        except Exception:
            pass
    except Exception:
        # se Fix.documents não estiver disponível, continuar com heurística DOM
        pass

    # Heurística DOM (fallback): múltiplos seletores de container — diferentes versões do PJe
    container_selectors = [
        'li.tl-item-container',
        'div.tl-item-container',
        'li.timeline-item',
        'div.timeline-item',
        'li.tl-item',
    ]

    # Coletar itens encontrando o primeiro seletor válido
    itens = []
    for sel in container_selectors:
        try:
            itens = driver.find_elements(By.CSS_SELECTOR, sel)
            if itens:
                break
        except Exception:
            continue

    # Busca do mais antigo para o mais recente
    for idx, item in enumerate(itens):
        try:
            # Preferir link com classe 'tl-documento', fallback para qualquer <a> dentro do item
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            except Exception:
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a[href*="/documento/"]')
                except Exception:
                    # último recurso: qualquer link clicável dentro do item
                    links = item.find_elements(By.TAG_NAME, 'a')
                    link = None
                    for l in links:
                        try:
                            if l.is_displayed():
                                link = l
                                break
                        except Exception:
                            continue
                    if link is None:
                        continue

            # Tentar obter o tipo real do documento a partir do primeiro elemento textual
            tipo_real = ''
            try:
                # procurar primeiro span/strong/b que contenha texto legível
                for q in ['span:not(.sr-only)', 'strong', 'b', 'em', 'span']:
                    try:
                        candidate = link.find_element(By.CSS_SELECTOR, q)
                        if candidate and candidate.text and candidate.text.strip():
                            tipo_real = candidate.text.lower().strip()
                            break
                    except Exception:
                        continue
                # fallback: usar texto do link inteiro (removendo descrição entre parênteses)
                if not tipo_real:
                    raw = link.text or ''
                    # pegar a parte antes de '(' se existir
                    tipo_real = raw.split('(')[0].strip().lower()
            except Exception:
                tipo_real = ''

            # Verificar se o tipo REAL é um dos procurados
            if tipo_real and re.search(r'^(despacho|decis[oã]o|senten[çc]a|conclus[oã]o|conclusao)', tipo_real):
                return item, link, idx

        except Exception:
            continue

    return None, None, 0


def _documento_nao_assinado(doc_link: Any) -> bool:
    """
    Helper: Detecta se o documento na timeline está marcado como não assinado.
    """
    try:
        item = doc_link.find_element(By.XPATH, './ancestor::li[contains(@class,"tl-item-container")]')
        icones = item.find_elements(By.CSS_SELECTOR, 'i.documento-nao-assinado.fa-unlock')
        for icone in icones:
            try:
                if icone.is_displayed():
                    return True
            except Exception:
                pass
        # Fallback: aria-label direto no ícone (mais restrito)
        icones_label = item.find_elements(By.CSS_SELECTOR, 'i.documento-nao-assinado[aria-label="Documento não assinado"]')
        for icone in icones_label:
            try:
                if icone.is_displayed():
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _extrair_texto_documento(driver: WebDriver, doc_link: Any) -> Optional[str]:
    """
    Helper: Extrai texto do documento usando múltiplas estratégias.

    Args:
        driver: WebDriver instance
        doc_link: Link do documento

    Returns:
        Texto extraído ou None se falhar
    """
    doc_link.click()
    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
    except Exception:
        try:
            WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.timeline, .document-viewer, div.tl-item-container')))
        except Exception:
            pass

    # Estratégia 1: extrair_direto (otimizada)
    texto = _extrair_com_extrair_direto(driver)
    if texto:
        return texto

    # Estratégia 2: extrair_documento (fallback)
    texto = _extrair_com_extrair_documento(driver)
    if texto:
        return texto

    # Se falhou, verificar se o documento está não assinado
    if _documento_nao_assinado(doc_link):
        return "__DOC_NAO_ASSINADO__"

    return None


def _extrair_com_extrair_direto(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_direto."""
    m = _lazy_import()
    extrair_direto = m['extrair_direto']

    try:
        # Não ativar debug detalhado do cabeçalho aqui (evita logs verbosos)
        logger.info('[FLUXO_PZ] Tentando extração DIRETA com extrair_direto...')
        resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=True)

        if resultado_direto and resultado_direto.get('sucesso'):
            if resultado_direto.get('conteudo'):
                raw = resultado_direto['conteudo']
                texto = raw.lower()
                snippet = ' '.join(raw.strip().splitlines())[:200]
                logger.info('[FLUXO_PZ]  Extração DIRETA bem-sucedida (snippet=%s...)', snippet)
                return texto
            elif resultado_direto.get('conteudo_bruto'):
                raw = resultado_direto['conteudo_bruto']
                texto = raw.lower()
                snippet = ' '.join(raw.strip().splitlines())[:200]
                logger.info('[FLUXO_PZ]  Extração DIRETA bem-sucedida (bruto snippet=%s...)', snippet)
                return texto

    except Exception as e_direto:
        logger.error(f'[FLUXO_PZ] Erro na extração DIRETA: {e_direto}')

    return None


def _extrair_com_extrair_documento(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_documento (fallback)."""
    m = _lazy_import()
    extrair_documento = m['extrair_documento']

    try:
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True)

        if texto_tuple and texto_tuple[0]:
            texto = texto_tuple[0].lower()
            return texto

    except Exception as e_extrair:
        logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')

    return None


def _fechar_aba_processo(driver: WebDriver) -> None:
    """
    Helper: Fecha aba do processo e volta para lista.
    """
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            logger.error(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida: {e}")
            try:
                driver.current_url  # Testa se aba está acessível
            except Exception:
                logger.error("[LIMPEZA][ERRO] Tentou acessar aba já fechada.")


# ═══════════════════════════════════════════
# 2. p2b_fluxo_regras.py
# ═══════════════════════════════════════════

# --- Rule Registry ---

prazo_registry = RuleRegistry("prazo", [
    "descumprimento",
    "recursal",
    "bloqueio_impugnacoes",
    "transito_julgado_liquida",
    "sobrestamento_reiteracao",
    "sobrestamento_prazos",
    "homologacao",
    "embargos",
    "embargos_procedentes",
    "pec",
    "perito_rogerio",
    "bloqueio_convertido",
    "parcelamento",
    "penhora",
    "calculos",
    "tentativas",
    "instauracao",
    "susep",
    "tendo_em_vista",
    "nao_amparada",
    "instaurado_em_face",
    "parcela_proxima",
    "indeferimento_desconsideracao",
    "baixa_aguarde_se",
])

_registry_populated = False


def _make_marker(rule_idx: int):
    """Create a callable that returns the rule index when called by the registry."""
    def marker(driver=None, atv=None):
        return rule_idx
    return marker


def _popular_registry():
    """Populate prazo_registry from _definir_regras_processamento()."""
    global _registry_populated
    if _registry_populated:
        return
    regras = _definir_regras_processamento()
    bucket_names = prazo_registry.bucket_order
    # Skip rule 0 (prescricao -- handled hardcoded in _processar_regras_gerais)
    for i, rule in enumerate(regras[1:], start=1):
        keywords = rule[0]
        bucket = bucket_names[i - 1]
        marker = _make_marker(i)
        for regex in keywords:
            prazo_registry.register(regex.pattern, bucket, marker)
    _registry_populated = True


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
    ato_idpj = m.get('ato_idpj')
    idpj = m.get('idpj')
    # wrappers/from PEC
    anex_retifidpj = m.get('anex_retifidpj')
    pec_excluiargos = m.get('pec_excluiargos')
    # helper callable for phase routing (creates initial gigs then routes)
    try:
        from .p2b_gateway import inicar_exec as _inicar_exec
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
            'intime-se a reclamada para pagamento das', 'homologo os calculos',
            'sob pena de prosseguimento da execução',
            'líquida a sentença, intime-se'
        ]],
         (_inicar_exec,),),

        # REGRA ESPECIAL: TRÂNSITO EM JULGADO COM SENTENÇA LÍQUIDA - iniciar execução
        ([gerar_regex_geral('Diante do trânsito em julgado, líquida a sentença')],
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
            'cinco dias para a parte exequente apresentar',
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

        # REGRA DE DESIGNAÇÃO DE PERITO ROGÉRIO
        ([gerar_regex_geral('designo o expert rogerio')],
         ("criar_gigs[6//xs prazo]",),),

        # REGRA DE BLOQUEIO CONVERTIDO
        ([gerar_regex_geral('bloqueio realizado, ora convertido')], ("criar_gigs[-1//Bruna - Liberação]",)),

        # REGRA DE PARCELAMENTO
        ([gerar_regex_geral('sobre o preenchimento dos pressupostos legais para concessão do parcelamento')], ("criar_gigs[1/Bruna/Liberação]",)),

        # REGRA DE PENHORA
        ([gerar_regex_geral('Defiro a penhora no rosto dos autos')], ("criar_gigs[1//xs sob 6]", ato_180)),

        # REGRA DE CÁLCULOS
        ([gerar_regex_geral('RECLAMANTE para apresentar cálculos de liquidação')], (calc1,),),

        # REGRA DE TENTATIVAS
        ([gerar_regex_geral('deverá realizar tentativas')], (ato_prev,),),

        # REGRA DE INSTAURAÇÃO
        ([gerar_regex_geral('defiro a instauração')], ('criar_gigs[1//xs pec dec]', 'criar_gigs[10//xs mdd edital pgto]', ato_idpj)),

        # REGRA DE SUSEP — garantia/securitária, acima de tendo em vista
        ([gerar_regex_geral('Tendo em vista que a SUSEP')], (ato_meios,),),

        # REGRA DE TENDO EM VISTA
        ([gerar_regex_geral(k) for k in ['tendo em vista que', 'pagamento da parcela pendente', 'sob pena de sequestro']], (_inicar_exec,)),

        # REGRA DE NÃO AMPARADA
        ([gerar_regex_geral('não está amparada')], (ato_meios,),),

        # REGRA DE INSTAURADO EM FACE
        ([gerar_regex_geral('instaurado em face')], (idpj,)),

        # REGRA ESPECIAL: pagamento da próxima parcela -> criar gigs saldo
        ([gerar_regex_geral('pagamento da próxima parcela')], ("criar_gigs[5//xs saldo]",)),

        # REGRA: INDEFIRO o pedido de desconsideração -> juntada retificação + exclusão Argos + ato_meios
        ([gerar_regex_geral('INDEFIRO o pedido de desconsideração')], (anex_retifidpj, pec_excluiargos, ato_meios)),

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

    # aba principal antes de executar ações — usada para garantir foco e cleanup
    try:
        aba_principal = driver.current_window_handle
    except Exception:
        aba_principal = None

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

    # Usar RuleRegistry para matching
    _popular_registry()
    bucket, marker = prazo_registry.match(texto_normalizado)
    if marker:
        rule_idx = marker()
        rule = regras[rule_idx]
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
                                    res = action(driver)
                                except Exception as e:
                                    logger.error('[FLUXO_PZ] Erro ao executar action callable: %s', e)
                                    res = None

                                # Cleanup: fechar abas extras que a action possa ter aberto
                                try:
                                    if aba_principal:
                                        handles = driver.window_handles
                                        for h in handles:
                                            if h != aba_principal:
                                                try:
                                                    driver.switch_to.window(h)
                                                    driver.close()
                                                except Exception:
                                                    pass
                                        try:
                                            driver.switch_to.window(aba_principal)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                                return res

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
