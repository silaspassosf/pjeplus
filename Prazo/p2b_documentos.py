"""Prazo P2B - Documentos (Extracao + Regras)

Consolidado de: p2b_fluxo_documentos.py, p2b_fluxo_regras.py
"""

# ── Imports ──
import logging
import re
import time
from typing import Any, List, Optional, Tuple

from Fix import espera

from .p2b_core import gerar_regex_geral, parse_gigs_param, checar_prox, calc1
from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve
from Fix.core import medir_tempo

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 1. p2b_fluxo_documentos.py
# ═══════════════════════════════════════════


def _encontrar_documento_relevante(driver: Any) -> Tuple[Optional[Any], Optional[Any], int]:
    """
    Helper: Encontra documento relevante (decisão/despacho/sentença) na timeline.

     CORRIGIDO: Busca APENAS no tipo real do documento (primeiro <span> dentro do link),
    não na descrição completa que pode conter termos enganosos.

    Exemplo correto: <span>Sentença</span><span>(Prescrição...)</span>
    Exemplo incorreto: <span>Edital</span><span>(Decisão/Sentença)</span> <- o tipo é EDITAL, não Decisão

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx)
    """
    # Heurística DOM: itera a timeline completa e filtra pelo tipo real do documento.
    # NÃO depende de buscar_documentos_sequenciais (ARGOS) — o fluxo P2B/PEC já tem
    # API própria (obter_chave_ultimo_despacho_decisao_sentenca) como caminho primário,
    # que inclui filtro de exceção (comunique-se por edital, concomitante) via
    # PADROES_EXCECAO_LINK_VALIDACAO com leitura de conteúdo via API.
    # A heurística DOM aqui é fallback — filtra apenas por tipo_real.
    # Múltiplos seletores de container — diferentes versões do PJe
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
            itens = espera.elementos(driver, sel, teto=0.5)
            if itens:
                break
        except Exception:
            continue

    # Busca do mais antigo para o mais recente
    for idx, item in enumerate(itens):
        try:
            # Preferir link com classe 'tl-documento', fallback para qualquer <a> dentro do item
            link = espera.elemento(item, 'a.tl-documento:not([target="_blank"])', teto=0.1)
            if not link:
                link = espera.elemento(item, 'a[href*="/documento/"]', teto=0.1)
            if not link:
                links = espera.elementos(item, 'a', teto=0.1)
                for l in links:
                    try:
                        if getattr(l, 'is_displayed', lambda: True)():
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
                        candidate = espera.elemento(link, q, teto=0.1)
                        if candidate and getattr(candidate, 'text', '') and candidate.text.strip():
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
        item = espera.elemento(doc_link, './ancestor::li[contains(@class,"tl-item-container")]', teto=0.1)
        if item:
            icones = espera.elementos(item, 'i.documento-nao-assinado.fa-unlock', teto=0.1)
            for icone in icones:
                try:
                    if getattr(icone, 'is_displayed', lambda: True)():
                        return True
                except Exception:
                    pass
            # Fallback: aria-label direto no ícone (mais restrito)
            icones_label = espera.elementos(item, 'i.documento-nao-assinado[aria-label="Documento não assinado"]', teto=0.1)
            for icone in icones_label:
                try:
                    if getattr(icone, 'is_displayed', lambda: True)():
                        return True
                except Exception:
                    pass
    except Exception:
        pass
    return False


def _extrair_texto_documento(driver: Any, doc_link: Any) -> Optional[str]:
    """
    Helper: Extrai texto do documento usando múltiplas estratégias.

    Args:
        driver: conexao/driver PJe
        doc_link: Link do documento

    Returns:
        Texto extraído ou None se falhar
    """
    doc_link.click()
    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
    except Exception:
        espera.ate_aparecer(driver, '.timeline, .document-viewer, div.tl-item-container', teto=2)

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


def _extrair_com_extrair_direto(driver: Any) -> Optional[str]:
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


def _extrair_com_extrair_documento(driver: Any) -> Optional[str]:
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


def _fechar_aba_processo(driver: Any) -> None:
    """
    Helper: Fecha aba do processo e volta para lista de forma segura.
    """
    try:
        from Fix.abas import fechar_abas_extras
        fechar_abas_extras(driver)
    except Exception as e:
        logger.warning(f"[LIMPEZA] Falha segura ao alternar abas: {e}")


# ═══════════════════════════════════════════
# 2. p2b_fluxo_regras.py
# ═══════════════════════════════════════════


def _gigs_com_prazo_pendente(driver: Any) -> bool:
    """True se o processo tiver QUALQUER atividade GIGS além do gatilho `xs1`.

    Regra: o arquivamento só é liberado quando a ÚNICA atividade encontrada é a
    `xs1`. Havendo outra atividade — inclusive comentário, e mesmo sem prazo —
    devolve True (bloqueia).

    Lê o painel já renderizado na página do processo (`pje-gigs-atividades`) e,
    se ele não estiver na página, cai na checagem pela API.

    O `xs1` é o marcador que faz o processo entrar no P2B (ver testar_gigs_xs1)
    e carrega prazo próprio; contá-lo bloqueava o arquivamento em 100% dos
    casos (log 12/11: 13 de 13 "Arquivamento PULADO" com o mesmo `Prazo: xs1`).
    """
    try:
        linhas = espera.elementos(driver, 'pje-gigs-atividades tbody tr', teto=3)
    except Exception as e:
        logger.warning('[FLUXO_PZ][GIGS] falha ao ler o painel (%s: %s)', type(e).__name__, e)
        linhas = []

    if linhas:
        ignoradas = 0
        for linha in linhas:
            try:
                texto_linha = (getattr(linha, 'text', '') or '').lower()
            except Exception:
                texto_linha = ''
            # A própria atividade `xs1` é o gatilho do P2B (ver testar_gigs_xs1)
            # e vem com prazo próprio; ela não conta como bloqueio.
            if 'xs1' in texto_linha:
                ignoradas += 1
                continue
            # Qualquer OUTRA atividade — inclusive comentário, e mesmo sem
            # prazo — bloqueia: o arquivamento só é liberado quando xs1 é a
            # única atividade encontrada.
            descricao = ''
            try:
                el_desc = espera.elemento(linha, 'span.descricao', teto=0.1)
                descricao = (el_desc.text if el_desc else '') or ''
            except Exception:
                pass
            logger.info('[FLUXO_PZ][GIGS] outra atividade no painel (arquivamento PULADO): %s',
                        (descricao or texto_linha or '?')[:80])
            return True
        logger.info('[FLUXO_PZ][GIGS] painel sem outra atividade (%d xs1 ignorada(s)) — '
                    'arquivamento liberado', ignoradas)
        return False

    return _gigs_com_prazo_pendente_api(driver)


def _gigs_com_prazo_pendente_api(driver: Any) -> bool:
    """Fallback da guarda: confere as atividades GIGS pela API do processo.

    Mesma regra do painel: só libera quando a única atividade é `xs1`. Qualquer
    outra (inclusive comentário) bloqueia. Erro na consulta devolve True —
    não arquivar sem conferir.
    """
    try:
        from Fix.navegacao_espera import extrair_id_processo
        id_processo = extrair_id_processo(driver)
        if not id_processo:
            logger.warning('[FLUXO_PZ][GIGS] id do processo ausente na URL — atividades nao conferidas')
            return True
        from .p2b_gateway import _criar_api_client
        client = _criar_api_client(driver)
        atividades = client.atividades_gigs(id_processo) or []
        ignoradas = 0
        for atv in atividades:
            tipo_atv = str(atv.get('tipoAtividade') or '')
            observacao = str(atv.get('observacao') or '')
            if 'xs1' in f'{tipo_atv} {observacao}'.lower():
                ignoradas += 1
                continue
            logger.info('[FLUXO_PZ][GIGS] outra atividade (API) — arquivamento PULADO: tipo=%s status=%s data=%s',
                        tipo_atv or '?', atv.get('statusAtividade') or '?', atv.get('dataPrazo') or '-')
            return True
        logger.info('[FLUXO_PZ][GIGS] (API) sem outra atividade (%d xs1 ignorada(s)) — '
                    'arquivamento liberado', ignoradas)
        return False
    except Exception as e:
        logger.warning('[FLUXO_PZ][GIGS] falha ao conferir prazos (%s: %s) — nao arquiva por seguranca',
                       type(e).__name__, e)
        return True


def _mov_arquivar_se_sem_prazo(driver: Any) -> bool:
    """Regra de arquivamento do P2B: só arquiva quando a única GIGS é `xs1`.

    A atividade `xs1` (gatilho do P2B) não conta como bloqueio. Havendo outra
    atividade — inclusive comentário — a regra APENAS PULA e devolve True, para
    o processo não ser marcado como falha.
    """
    if _gigs_com_prazo_pendente(driver):
        logger.info('[FLUXO_PZ] Arquivamento PULADO: processo tem GIGS com prazo pendente')
        return True
    mov_arquivar = _lazy_import().get('mov_arquivar')
    if not mov_arquivar:
        logger.error('[FLUXO_PZ] mov_arquivar indisponivel no lazy import')
        return False
    return bool(mov_arquivar(driver))


def _definir_regras_processamento() -> List[Tuple[list, tuple]]:
    """
    Tabela do motor de regras do P2B: cada entrada é (trechos, ações).

    trechos: lista de strings de texto (compiladas via gerar_regex_geral em tempo de
             match, tolerando pontuação/espaços entre palavras) ou, nos raros casos que
             precisam de regex exato, um re.Pattern já compilado.
    ações:   uma ação ou tupla de ações executadas em sequência quando QUALQUER trecho
             da regra casar com o texto. Formatos aceitos: callable(driver) -> Any, ou
             string "criar_gigs[dias/responsavel/observacao]".

    Ordem = prioridade: a primeira regra cujo trecho casar com o texto decide a ação e
    encerra o processamento. Para adicionar/remover/reordenar uma regra, edite só esta
    lista — não há índice paralelo nem registro para manter sincronizado.
    """
    # Lazy load modules necessários para as regras
    m = _lazy_import()
    ato_180 = m['ato_180']
    ato_calc2 = m['ato_calc2']
    ato_prev = m['ato_prev']
    ato_meios = m['ato_meios']
    ato_sobrestamento = m['ato_sobrestamento']
    ato_pesqliq = m.get('ato_pesqliq')
    ato_reitmeios = m.get('ato_reitmeios')
    ato_idpj = m.get('ato_idpj')
    ato_HCL = m.get('ato_HCL')
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
        (['A pronúncia da'], (prescreve,)),

        # REGRA DE ARQUIVAMENTO - MÁXIMA PRIORIDADE (logo após prescrição)
        # Só arquiva quando a ÚNICA atividade GIGS é a `xs1` (gatilho do P2B).
        # Qualquer outra atividade ou comentário faz a regra apenas pular
        # (_mov_arquivar_se_sem_prazo).
        ([
            'julgo extinta a presente execução, nos termos do art. 924',
            'autos ao arquivo',
            'devendo diligenciar junto ao cartório',
        ], (_mov_arquivar_se_sem_prazo,)),

        # REGRA DE DESCUMPRIMENTO - executar gigs1, gigs2, ato_pesqliq (sem tentar mov_exec)
        (['Ante a notícia de descumprimento'], ("criar_gigs[1/Ana Lucia/Argos]", "criar_gigs[1//xs sigilo]", ato_pesqliq)),

        # REGRA DE RECURSAL - executar gigs1
        (['Libere-se o depósito recursal'], ("criar_gigs[-1/Ana Lucia/Alvará recursal]",)),

        # REGRA DE SALDO / PARCELAMENTO (xs saldo) - PREVALÊNCIA SOBRE INICIAR EXECUÇÃO
        ([
            'saldo devedor',
            'admito o parcelamento',
        ], ("criar_gigs[1//xs saldo]",)),

        # REGRA ESPECIAL: pagamento da próxima parcela -> criar gigs saldo
        (['pagamento da próxima parcela'], ("criar_gigs[5//xs saldo]",)),

        # REGRA DE BLOQUEIO / IMPUGNAÇÕES - DEVE VIR ANTES PARA TER PRIORIDADE
        ([
            'sob pena de bloqueio',
            'sob pena de penhora',
            'sob pena de execução', 'sob pena de execucao',
            'impugnações apresentadas', 'impugnacoes apresentadas', 'homologo estes',
            'fixando o crédito do autor em', 'referente ao principal', 'sob pena de sequestro',
            'atestar a quitação', 'comprovar o pagamento',
            'comprovar recolhimento', 'comprovar recolhimentos', 'comprovar o recolhimento',
            'a reclamada para pagamento da parcela pendente',
            'intime-se a reclamada para pagamento das', 'homologo os calculos',
            'sob pena de prosseguimento da execução',
            'líquida a sentença, intime-se',
        ], (_inicar_exec,)),

        # REGRA ESPECIAL: TRÂNSITO EM JULGADO COM SENTENÇA LÍQUIDA - iniciar execução
        (['Diante do trânsito em julgado, líquida a sentença'], (_inicar_exec,)),

        # REGRAS DE SOBRESTAMENTO
        (['Abre-se, como reiteração'], ("criar_gigs[1//xs sob 24]", "criar_gigs[1//xs pec exequente pessoal]", ato_sobrestamento)),

        ([
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
            'ausências de fundamentação fática e jurídica',
        ], (ato_reitmeios,)),

        # REGRAS DE HOMOLOGAÇÃO
        ([
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
        ], ("criar_gigs[1/Ana Lucia do A/Homologação]", ato_HCL)),

        # REGRA DE EMBARGOS
        (['exequente, ora embargado'], ("criar_gigs[1/fernanda/julgamento embargos]",)),

        # REGRA DE EMBARGOS - quando decidido procedentes os embargos -> executar ato_meios
        (['procedentes os embargos', 'procedente os embargos'], (ato_meios,)),

        # REGRA DE DESIGNAÇÃO DE PERITO ROGÉRIO
        (['designo o expert rogerio'], ("criar_gigs[6//xs prazo]",)),

        # REGRA DE BLOQUEIO CONVERTIDO
        (['bloqueio realizado, ora convertido'], ("criar_gigs[-1//Bruna - Liberação]",)),

        # REGRA DE CONCLUSOS PARA LIBERAÇÃO (restaurada do legado — LEGADO.md L49555)
        (['conclusos para liberação'], ("criar_gigs[-1//Bruna - Liberação]",)),

        # REGRA DE PARCELAMENTO
        (['sobre o preenchimento dos pressupostos legais para concessão do parcelamento'], ("criar_gigs[1/Bruna/Liberação]",)),

        # REGRA DE OPOSIÇÃO DE EMBARGOS
        (['para oposição de embargos'], ("criar_gigs[-1//Bruna - Liberação]",)),

        # REGRA DE PENHORA
        (['Defiro a penhora no rosto dos autos'], ("criar_gigs[1//xs sob 6]", ato_180)),

        # REGRA DE CÁLCULOS
        (['RECLAMANTE para apresentar cálculos de liquidação'], (calc1,)),

        # REGRA DE TENTATIVAS
        (['deverá realizar tentativas'], (ato_prev,)),

        # REGRA DE INSTAURAÇÃO (desativada temporariamente)
        # (['defiro a instauração'], ('criar_gigs[1//xs pec dec]', 'criar_gigs[10//xs mdd edital pgto]', ato_idpj)),

        # REGRA DE INCIDENTE IDPJ — decisão que defere a desconsideração em face de
        # sócio(s).
        (['Incidente de Desconsideração da Personalidade Jurídica instaurado em face'], (ato_meios,)),

        # REGRA DE INSTAURADO EM FACE
        (['instaurado em face'], (idpj,)),

        # REGRA DE SUSEP — garantia/securitária
        (['Tendo em vista que a SUSEP'], (ato_meios,)),

        # REGRA DE INICIAR EXECUÇÃO / PARCELA PENDENTE
        (['pagamento da parcela pendente', 'sob pena de sequestro'], (_inicar_exec,)),

        # REGRA DE NÃO AMPARADA
        (['não está amparada'], (ato_meios,)),

        # REGRA: a Justiça do Trabalho não possui competência -> ato_meios
        (['a Justiça do Trabalho não possui competência'], (ato_meios,)),

        # REGRA DE AGRAVO EXEQUENTE E INTERLOCUTÓRIA (regex exato — não é trecho literal)
        ([re.compile(r'(?=[\s\S]*interlocutoria)(?=[\s\S]*interposto[\s\n\r]*agravo[\s\n\r]*de[\s\n\r]*peticao[\s\n\r]*pela[\s\n\r]*parte[\s\n\r]*exequente)', re.IGNORECASE)], (ato_meios,)),

        # REGRA: INDEFIRO o pedido de desconsideração -> juntada retificação + exclusão Argos + ato_meios
        (['INDEFIRO o pedido de desconsideração'], (anex_retifidpj, pec_excluiargos, ato_meios)),

        # REGRA DE BAIXA/AGUARDE-SE (Conjunto que aciona checar_prox como helper)
        ([
            'inoportuna petição', 'determinar cancelamento/baixa', 'deixo de receber o Agravo', 'quanto à petição',
            'art. 112 do CPC', 'comunique-se por Edital', 'comunique-se de forma concomitante',
            'Aguarde-se', 'Aguarde-se o prazo', 'Aguarde-se resposta',
            'mantenho o despacho', 'mantenho a decisão', 'edital de intimação de decisão',
            'sob pena de preclusão', 'embargos de declaração', 'Registre-se o movimento processual adequado',
            'decisão com força de alvará',
        ], (checar_prox,)),

        # REGRA DE DADOS BANCÁRIOS / ENDEREÇO (fuzzy, mesma linha — aceita termos interpostos)
        # 1º token "in<...>r" cobre indicar/incluir/inserir/incar; [^\n]*? entre
        # tokens impede cruzamento de linha.
        ([
            re.compile(r'\bin\w*r\b[^\n]*?\bseus\b[^\n]*?\bdados\b[^\n]*?\bbancari\w*\b', re.IGNORECASE),
            re.compile(r'\bindicac\w*\b[^\n]*?\bdados\b[^\n]*?\bbancari\w*\b', re.IGNORECASE),
            re.compile(r'\bindic\w*\b[^\n]*?\bendereco\b[^\n]*?\bcomplet\w*\b', re.IGNORECASE),
        ], (checar_prox,)),
    ]


def _casas_regra(texto_normalizado: str):
    """Primeira regra que casa com o texto — SEM executar nenhuma ação.

    Returns:
        (trechos, tipo_acao, match) ou None se nenhuma regra casar.

    Usado pelo motor API-first (`Prazo/p2b_engine_api.py`) para decidir se o
    processo tem ação aplicável antes de abrir a página.
    """
    for trechos, tipo_acao in _definir_regras_processamento():
        for trecho in trechos:
            padrao = trecho if hasattr(trecho, 'search') else gerar_regex_geral(trecho)
            encontrado = padrao.search(texto_normalizado)
            if encontrado:
                return trechos, tipo_acao, encontrado
    return None


@medir_tempo('_processar_regras_gerais')
def _processar_regras_gerais(driver: Any, texto_normalizado: str, doc_idx: int = 0):
    """
    Helper: varre _definir_regras_processamento() em ordem — trechos -> ações.
    A primeira regra cujo trecho casar com o texto decide a(s) ação(ões) e encerra
    (prescrição e arquivamento são só as duas primeiras entradas da mesma lista).

    Args:
        driver: conexao/driver PJe
        texto_normalizado: Texto normalizado para análise
        doc_idx: Índice atual do documento na timeline (para checar_prox)

    Returns:
        - Tupla (doc_encontrado, doc_link, doc_idx) se checar_prox encontrou próximo documento
        - True se regra casou e todas as ações completaram com sucesso
        - False se alguma ação retornou False (movimento falhou, etc.)
        - None se nenhuma regra casou
    """
    m = _lazy_import()
    criar_gigs = m.get('criar_gigs')
    regras = _definir_regras_processamento()

    # aba principal antes de executar ações — usada para garantir foco e cleanup
    try:
        aba_principal = driver.current_window_handle
    except Exception:
        aba_principal = None

    def _executar_acao(action):
        try:
            # sintaxe string 'criar_gigs[dias/responsavel/observacao]'
            if isinstance(action, str):
                m_g = re.match(r'^criar_gigs\[(.*)\]$', action)
                if m_g:
                    try:
                        dias, responsavel, observacao = parse_gigs_param(m_g.group(1))
                        if criar_gigs:
                            if criar_gigs(driver, dias, responsavel, observacao) is False:
                                logger.warning('[FLUXO_PZ] criar_gigs falhou: %s', m_g.group(1))
                    except Exception as e:
                        logger.error('[FLUXO_PZ] criar_gigs sintaxe falhou: %s', e)
                return None

            # ação callable(driver)
            if callable(action):
                try:
                    # Special-case: checar_prox espera (driver, itens, doc_idx, regras, texto_normalizado)
                    is_checar = (action is checar_prox) or (getattr(action, '__name__', '') == 'checar_prox')
                    if is_checar:
                        try:
                            itens = espera.elementos(driver, 'li.tl-item-container', teto=1)
                            return checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                        except Exception:
                            return None
                    res = action(driver)
                except Exception as e:
                    logger.error('[FLUXO_PZ] Erro ao executar action callable: %s', e)
                    res = None
                
                # Logar se ação retorna False (falha sem exceção)
                if res is False:
                    action_name = getattr(action, '__name__', str(action))
                    logger.warning('[FLUXO_PZ] Ação retornou False: %s', action_name)

                # Cleanup: fechar abas extras que a action possa ter aberto
                try:
                    if aba_principal:
                        from Fix.abas import forcar_fechamento_abas_extras
                        forcar_fechamento_abas_extras(driver, aba_principal)
                except Exception:
                    pass
                return res

            return None
        except Exception as e:
            logger.error('[FLUXO_PZ] Erro em _executar_acao(%s): %s', action, e)
            return None

    # Varredura sequencial: primeira regra cujo trecho casar decide a ação.
    # `_casas_regra` faz só o match (sem executar) — mesma varredura, reusada pelo
    # motor API-first.
    casada = _casas_regra(texto_normalizado)
    for trechos, tipo_acao, match in ([casada] if casada else []):
        try:
            span = match.span()
            start = max(0, span[0] - 40)
            end = min(len(texto_normalizado), span[1] + 40)
            snippet = texto_normalizado[start:end].replace('\n', ' ')
            logger.info('[FLUXO_PZ] Regra casou: pattern=%s tipo_acao=%s snippet=%s', match.re.pattern, tipo_acao, snippet[:180])
        except Exception:
            logger.info('[FLUXO_PZ] Regra casou: tipo_acao=%s', tipo_acao)

        acoes = list(tipo_acao) if isinstance(tipo_acao, (list, tuple)) else [tipo_acao]
        resultado_acoes = True  # Assume sucesso até que ação falhe
        
        for acao in acoes:
            res = _executar_acao(acao)
            # Se retorna tupla, é resultado de checar_prox — passa adiante
            if isinstance(res, tuple) and len(res) == 3:
                return res
            # Tupla de resultado de wrapper de ato (ex.: make_ato_wrapper ->
            # (ok_fluxo, ok_final)): sucesso se o PRIMEIRO item é True. O segundo
            # item é flag auxiliar (ex.: sigilo ativado) — atos sem sigilo retornam
            # (True, False) e NÃO devem ser tratados como falha.
            if isinstance(res, tuple):
                if not res or not res[0]:
                    resultado_acoes = False
            # Se retorna False, regra falhou
            elif res is False:
                resultado_acoes = False
        
        # Regra executada (resultou em True/False), não procura mais regras
        return resultado_acoes

    # Nenhuma regra casou
    return None
