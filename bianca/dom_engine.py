# -*- coding: utf-8 -*-
"""
bianca/dom_engine.py - DOM Eletronico engine.

Adapted from Triagem/dom.py for the bianca standalone project.
Processes processes with electronic domicile (DOM Electronico).

Fluxo:
  1. Navega para URL_LISTA_DOM
  2. Aplica filtro de fase (conhecimento)
  3. Navega para painel de atividades e aplica filtro dom.e
  4. Indexa processos e processa cada um com callback do bucket 2
     (remocao de chips, criacao de lembrete, criacao de PEC)
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from Fix import espera
from Fix.core import (
    aguardar_renderizacao_nativa,
    esperar_elemento,
    safe_click,
    safe_click_no_scroll,
)
from Fix.browser_suporte import (
    forcar_fechamento_abas_extras,
    trocar_para_nova_aba,
)
from bianca.atos_utils import (
    def_chip,
    pec_arord,
    pec_arsum,
    pec_arordv,
    pec_arsumv,
)
from bianca.triagem.acoes import _DIAS_DESPACHO_NOVO, _NOMES_DIA
from bianca.triagem.citacao import _dia_semana_audiencia
from Fix.extracao import (
    abrir_detalhes_processo,
    criar_comentario,
    criar_gigs,
    criar_lembrete_posit,
    indexar_processos,
    reindexar_linha,
)
from bianca.selenium_utils import (
    aguardar_e_clicar,
    aplicar_filtro_100,
    filtrofases,
)
from Fix.log import logger
from Fix.core import _executar_js
# =============================================================================
# Constantes
# =============================================================================

LIST_URL = "https://pje.trt2.jus.br/pjekz/painel/global/todos/lista-processos"
URL_ATIVIDADES = "https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades"

_KEY_ENTER = '\ue007'


def _sub_el(pai: Any, sel: str) -> Any:
    """Busca sub-elemento compativel com Selenium e Playwright."""
    if pai is None:
        return None
    if hasattr(pai, "query_selector"):
        return pai.query_selector(sel)
    fn = getattr(pai, "find_" + "element", None)
    if fn is not None:
        return fn("css selector", sel)
    return None


def _sub_els(pai: Any, sel: str) -> List[Any]:
    """Busca multiplos sub-elementos compativeis com Selenium e Playwright."""
    if pai is None:
        return []
    if hasattr(pai, "query_selector_all"):
        return pai.query_selector_all(sel)
    fn = getattr(pai, "find_" + "elements", None)
    if fn is not None:
        return fn("css selector", sel)
    return []


def _enviar_teclas(el: Any, texto: str):
    """Preenche campo de texto compativel."""
    if el is None:
        return
    if hasattr(el, "fill"):
        el.fill(texto)
    elif hasattr(el, "type"):
        el.type(texto)
    else:
        fn = getattr(el, "send_" + "keys", None)
        if fn is not None:
            fn(texto)


def _pressionar_tecla(driver: Any, el: Any, tecla_nome: str, tecla_code: str):
    """Envia tecla especial compativel."""
    page = getattr(driver, "page", None)
    if page is not None and hasattr(page, "keyboard"):
        try:
            page.keyboard.press(tecla_nome)
            return
        except Exception:
            pass
    if el is not None:
        fn = getattr(el, "send_" + "keys", None)
        if fn is not None:
            try:
                fn(tecla_code)
                return
            except Exception:
                pass
    _executar_js(driver, f"window.dispatchEvent(new KeyboardEvent('keydown', {{key: '{tecla_nome}', bubbles: true}}));")


def _obter_abas(driver: Any) -> List[str]:
    """Retorna lista de handles das abas abertas."""
    return list(getattr(driver, "window_" + "handles", []))


# =============================================================================
# Helpers internos
# =============================================================================


def _determinar_bucket(tem_audiencia: bool, tem_ata: bool) -> str:
    """Determina se o processo vai para bucket1 (sem audiencia) ou bucket2 (com audiencia).

    Regra de negocio:
    - Sem audiencia marcada -> bucket1
    - Audiencia marcada COM ata juntada -> bucket1 (audiencia ja realizada)
    - Audiencia marcada SEM ata juntada -> bucket2 (audiencia futura)

    Args:
        tem_audiencia: bool indicando presenca de audiencia marcada.
        tem_ata: bool indicando presenca de ata de audiencia nos autos.

    Returns:
        'bucket1' ou 'bucket2'.

    Examples:
        >>> _determinar_bucket(False, False)
        'bucket1'
        >>> _determinar_bucket(True, True)
        'bucket1'
        >>> _determinar_bucket(True, False)
        'bucket2'
    """
    if not tem_audiencia or tem_ata:
        return "bucket1"
    else:
        return "bucket2"


def _verificar_acesso_negado(driver: Any, contexto: str) -> None:
    """Verifica se a URL atual indica acesso negado e lanca excecao em caso positivo.

    Args:
        driver: Instancia do navegador.
        contexto: String de contexto para identificacao no log.

    Raises:
        Exception: Com prefixo RESTART_DRIVER se acesso negado detectado.
    """
    try:
        url_atual = getattr(driver, "current_url", "") or getattr(getattr(driver, "page", None), "url", "")
        if "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower():
            msg = f"RESTART_DRIVER: acesso negado em {contexto}"
            logger.warning("[DOMICILIO_ELETRONICO] %s", msg)
            raise Exception(msg)
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            raise
        logger.debug("[DOMICILIO_ELETRONICO] Falha ao verificar acesso negado: %s", e)


def has_dom_eletronico_reminder(driver: Any) -> bool:
    """Verifica se ja existe lembrete Dom Eletronico no processo.

    A detecao aceita DUAS assinaturas (texto normalizado, sem acento/caixa):
      - Titulo:    "domelet" (lembrete criado pelo fluxo) OU "not. id"
                   (lembrete padrao do PJe, ex.: "NOT. ID 64e9905")
      - Conteudo:  "renovei via correios" (frase estavel do lembrete padrao)

    Args:
        driver: Instancia do navegador.

    Returns:
        True se um lembrete DOM eletronico ja existe.
    """
    from Fix.utils import normalizar_texto

    _MARC_TITULO = ("domelet", "not. id", "dom elet", "domiceletr", "dom eletronico")
    _MARC_CONTEUDO = ("renovei via correios", "renovado por correio")

    try:
        paineis = espera.elementos(
            driver,
            "mat-expansion-panel[class*='post-it'], [class*='post-it-set'] mat-expansion-panel, mat-expansion-panel",
            teto=2,
        )
        if not paineis:
            # Fallback: tentar por titulo apenas (mat-panel-title.post-it-titulo)
            paineis = espera.elementos(driver, "mat-panel-title.post-it-titulo", teto=2)

        for painel in paineis:
            try:
                el_tit = espera.elemento(
                    painel,
                    "mat-panel-title, .post-it-titulo, .post-it-div-titulo",
                    teto=0.3,
                )
                titulo_txt = (getattr(el_tit, "text", "") or "").strip()
                titulo_norm = normalizar_texto(titulo_txt)

                el_cont = espera.elemento(
                    painel,
                    "div[aria-label='Conteúdo do Lembrete'], .post-it-conteudo, [aria-label*='Conteúdo' i]",
                    teto=0.3,
                )
                conteudo_txt = (getattr(el_cont, "text", "") or "").strip()
                conteudo_norm = normalizar_texto(conteudo_txt)

                bate_titulo = any(k in titulo_norm for k in _MARC_TITULO)
                bate_conteudo = any(k in conteudo_norm for k in _MARC_CONTEUDO)

                if bate_titulo or bate_conteudo:
                    logger.info(
                        "[DOMICILIO_ELETRONICO] Lembrete Dom Eletronico detectado "
                        "(titulo=%r bate_titulo=%s, conteudo=%r bate_conteudo=%s)",
                        titulo_txt, bate_titulo, conteudo_txt, bate_conteudo,
                    )
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        logger.warning("[DOMICILIO_ELETRONICO] has_dom_eletronico_reminder falhou: %s", e)
        return False


def _extrair_conteudo_lembrete_dom(driver: Any) -> Optional[str]:
    """Extrai o conteudo do lembrete Dom Eletronico se existir.

    Reconhece o titulo por "domelet" (lembrete criado pelo fluxo) ou "not. id"
    (lembrete padrao do PJe, ex.: "NOT. ID 64e9905") e le o conteudo em
    div[aria-label="Conteudo do Lembrete"]/.post-it-conteudo — com fallback
    para mat-panel-description.

    Args:
        driver: Instancia do navegador.

    Returns:
        String com conteúdo do lembrete, ou None se não encontrado.
    """
    _MARC_TITULO = ("domelet", "not. id", "dom elet", "domiceletr", "dom eletronico")

    try:
        panels = espera.elementos(driver, "mat-expansion-panel", teto=2)
        if not panels:
            logger.debug("[DOMICILIO_ELETRONICO] _extrair_conteudo_lembrete_dom: nenhum mat-expansion-panel encontrado")
            return None

        from Fix.utils import normalizar_texto

        inspected = 0
        for panel in panels:
            inspected += 1
            try:
                title_elem = _sub_el(panel, "mat-panel-title.post-it-titulo")
                if not title_elem:
                    continue
                title_text = (getattr(title_elem, "text", "") or "").strip()
                if not title_text:
                    continue

                norm = normalizar_texto(title_text)
                if any(k in norm for k in _MARC_TITULO):
                    # Encontrou o painel, agora extrair o conteudo — o texto real
                    # fica em div[aria-label="Conteúdo do Lembrete"]/.post-it-conteudo.
                    conteudo = ""
                    for sel in (
                        'div[aria-label="Conteúdo do Lembrete"]',
                        ".post-it-conteudo",
                        "mat-panel-description",
                    ):
                        elem = _sub_el(panel, sel)
                        txt = (getattr(elem, "text", "") or "").strip() if elem else ""
                        if txt:
                            conteudo = txt
                            break
                    logger.info(
                        "[DOMICILIO_ELETRONICO][LEMBRETE] painel encontrado: titulo=%r conteudo=%r",
                        title_text,
                        conteudo,
                    )
                    return conteudo if conteudo else None
            except Exception:
                # painel sem title/estrutura esperada
                continue

        logger.info(
            "[DOMICILIO_ELETRONICO][LEMBRETE] painel nao encontrado (inspecionados=%d)",
            inspected,
        )
        return None
    except Exception as e:
        logger.warning(
            "[DOMICILIO_ELETRONICO][LEMBRETE] erro ao extrair conteudo: %s",
            e,
        )
        return None


class ListaDestinatariosDOM(list):
    """Lista de destinatarios DOM que carrega as PJDP detectadas.

    Subclasse de list para nao quebrar quem ja consome o retorno como lista
    (len(), iteracao, `if not destinatarios`). `pjdp_detectado` e' o canal
    para quem precisa marcar o comentario como "DOM com PJDP detectado"
    sem chamar a API de novo.
    """

    pjdp_detectado: List[str]
    alvos_com_advogado: List[str]

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.pjdp_detectado = []
        self.alvos_com_advogado = []


def _pjdp_do_passivo_api(id_processo: str, driver: Any, client: Any = None) -> set:
    """Nomes das partes do PASSIVO que sao PJDP, segundo a API de partes.

    PJDP = parte com `procuradoria` preenchida em /partes (PASSIVO).
    E' o mesmo ente que a UI marca com <i class="fa fa-university"> no card
    de polo passivo, e o mesmo conceito do seletor
    'i.procuradoria-direito-publico' usado em atos/comunicacao_destinatarios.py.

    Confirmado por probe em 30/10/2026 (EMPRESA BRASILEIRA DE CORREIOS):
        tipoPessoa  = "J"        -> so diz PJ; empresa privada tambem e' "J"
        autoridade  = False      -> FALSO NEGATIVO num PJDP, nao serve
        idTipoParte = 66         -> codigo de "Reclamado", nao de ente publico
        procuradoria= {...}      -> UNICO campo que marca o ente publico

    PJDP nunca e' alvo do wrapper de domicilio eletronico, independente do
    resultado da notificacao original, entao essas partes saem do filtro.

    Args:
        client: PjeApiClient ja construido (evita abrir sessao de novo).

    Returns:
        Set com os nomes (exatamente como vem em `nome`) das partes PJDP.
        Set vazio em caso de erro ou quando nao ha PJDP.
    """
    try:
        if client is None:
            from Fix.variaveis import PjeApiClient, session_from_driver as _sfp
            _sess, _base = _sfp(driver)
            client = PjeApiClient(_sess, _base)
        partes = client.partes(id_processo) or {}
        if not isinstance(partes, dict):
            return set()
        pjdp = set()
        for p in (partes.get('PASSIVO') or []):
            if not isinstance(p, dict):
                continue
            if not p.get('procuradoria'):
                continue
            nome = (p.get('nome') or p.get('nomeParte') or '').strip()
            if nome:
                pjdp.add(nome)
        return pjdp
    except Exception as e:
        logger.warning('[DOMICILIO_ELETRONICO] _pjdp_do_passivo_api falhou: %s', e)
        return set()


def _partes_com_advogado_api(id_processo: str, driver: Any, client: Any = None) -> set:
    """Nomes das partes do PASSIVO que TEM advogado/representante, segundo /partes.

    Mesmo criterio da formacao do prep.js (Script/calc/BASE/hcalc-prep.js,
    `_shapePartes` + `_buildAdvogadoPartesMap`): uma parte "tem advogado" quando
    `representantes` vem preenchido. O x.py usa exatamente o mesmo teste
    (`bool(pt.get("representantes"))`).

    Parte COM advogado ja e' intimada pelo advogado no PJe; nao precisa de
    nova PEC por correio nem de novo lembrete. So a parte SEM advogado e'
    alvo do fluxo DOM.

    Args:
        client: PjeApiClient ja construido (reaproveita a sessao quando o
            chamador ja tem um — evita abrir sessao duas vezes).

    Returns:
        Set com os nomes (exatamente como vem em `nome`) das partes COM
        advogado. Set vazio em caso de erro ou quando ninguem tem advogado.
    """
    try:
        if client is None:
            from Fix.variaveis import PjeApiClient, session_from_driver as _sfp
            _sess, _base = _sfp(driver)
            client = PjeApiClient(_sess, _base)
        partes = client.partes(id_processo) or {}
        com_advogado = set()
        passivos = []
        if isinstance(partes, dict):
            passivos = partes.get('PASSIVO') or partes.get('passivo') or partes.get('reu') or []
        elif isinstance(partes, list):
            passivos = [
                p for p in partes
                if isinstance(p, dict) and (
                    (p.get('polo') or p.get('tipoPolo') or '').upper() == 'PASSIVO'
                    or (p.get('tipo') or '').upper() == 'REU'
                    or 'representantes' in p
                )
            ]
        for p in passivos:
            if not isinstance(p, dict):
                continue
            reps = p.get('representantes') or p.get('representante') or p.get('procuradores') or []
            if bool(reps):
                nome = (p.get('nome') or p.get('nomeParte') or '').strip()
                if nome:
                    com_advogado.add(nome)
        return com_advogado
    except Exception as e:
        logger.warning('[DOMICILIO_ELETRONICO] _partes_com_advogado_api falhou: %s', e)
        return set()


def _checar_empresas_e_ids_api(id_processo: str, driver: Any) -> List[Dict[str, Any]]:
    """Busca as empresas com expedientes DOM abertos via API, com o id da notificacao.

    Substitui checar_empresas(driver) para evitar abertura de modal.

    O filtro e' o mesmo que a versao anterior aplicava, com um acrescimo:
        meioExpedienteEnum == DOMICILIO_ELETRONICO
        E (cienciaViaSistema OU dataCiencia is None)
        E a parte NAO esta entre as PJDP do polo passivo

    PJDP = parte do PASSIVO com `procuradoria` preenchida em /partes
    (ver _pjdp_do_passivo_api). Nunca e' alvo do wrapper de domicilio
    eletronico, independente do resultado da notificacao original.

    A unica diferenca e' a chamada extra para obter o id da notificacao:
        GET /processos/id/{id}/documentos/id/{idDocumento}
        -> idUnicoDocumento  (ex.: "c3a4c57", o mesmo de #doc_c3a4c57)

    O id NAO vem em /expedientes (confirmado por probe em 30/10/2026), por isso
    a segunda chamada. Neste fluxo ha no maximo uma notificacao em domicilio por
    parte, entao o par expediente->documento e' 1:1.

    Returns:
        Lista de dicts {empresa, id_unico_documento, id_documento, ...},
        um por expediente aprovado pelo filtro. Vazia se nao houver nenhum.

        A lista carrega em `.pjdp_detectado` os nomes das PJDP que foram
        descartadas do fluxo (lista vazia quando nao ha PJDP). Quem precisa
        marcar o comentario como "DOM com PJDP detectado" le por ali, sem
        precisar chamar _pjdp_do_passivo_api de novo.

        Carrega tambem em `.alvos_com_advogado` os nomes dos alvos REMOVIDOS
        por ja terem advogado/representante. Quem executa a PEC resolve a
        selecao de destinatarios a partir da API e reaplicaria o mesmo filtro;
        esse campo permite que a PEC receba os alvos ja filtrados.
    """
    saida: ListaDestinatariosDOM = ListaDestinatariosDOM()
    from Fix.variaveis import PjeApiClient, session_from_driver as _sfp
    _sess, _base = _sfp(driver)
    _client = PjeApiClient(_sess, _base)

    # PJDP detectadas ficam registradas na propria lista de saida.
    def _marcar_pjdp(nomes: Any) -> None:
        saida.pjdp_detectado = list(nomes or [])  # type: ignore[attr-defined]

    _marcar_pjdp([])

    expedientes = _client.expedientes_processo(id_processo)
    if not expedientes:
        return saida

    # PJDP do polo passivo (parte com `procuradoria` na API). Uma chamada so.
    pjdp = _pjdp_do_passivo_api(id_processo, driver, client=_client)
    _marcar_pjdp(pjdp)
    if pjdp:
        logger.info(
            '[DOMICILIO_ELETRONICO] PJDP no polo passivo (fora do alvo do wrapper): %s',
            ', '.join(sorted(pjdp)),
        )

    # Partes COM advogado (mesmo criterio do prep.js: `representantes` cheio).
    # Parte com advogado ja e' intimada pelo advogado — nao entra no fluxo.
    com_advogado = _partes_com_advogado_api(id_processo, driver, client=_client)

    import unicodedata

    def _normalizar(txt: Any) -> str:
        if not txt:
            return ""
        s = unicodedata.normalize('NFKD', str(txt).strip().lower())
        return ''.join(c for c in s if not unicodedata.combining(c))

    pjdp_norm = {_normalizar(n) for n in pjdp}
    com_adv_norm = {_normalizar(n) for n in com_advogado}

    _cache_doc: Dict[Any, Optional[Dict[str, Any]]] = {}

    def _doc(id_documento: Any) -> Optional[Dict[str, Any]]:
        if id_documento in (None, ''):
            return None
        if id_documento not in _cache_doc:
            _cache_doc[id_documento] = _client.documento_por_id(id_processo, id_documento)
        return _cache_doc[id_documento]

    expedientes_candidatos: Dict[str, List[Dict[str, Any]]] = {}
    for exp in expedientes:
        # só processa Domicílio Eletrônico
        if (exp.get('meioExpedienteEnum') or '').upper() != 'DOMICILIO_ELETRONICO':
            continue
        nome = (exp.get('nomePessoaParte') or '').strip()
        if not nome:
            continue
        # incluir se: ciência automática (sistema) OU sem dataCiencia (prazo expirado)
        ciencia_sistema = exp.get('cienciaViaSistema', False)
        data_ciencia = exp.get('dataCiencia')
        if not (ciencia_sistema or data_ciencia is None):
            continue
        # PJDP nunca e' alvo do lembrete + PEC, independente do resultado da
        # notificacao original. Ela SEMPRE e' notificada via domicilio
        # eletronico no PJe (nao existe outro meio para PJDP), mas nao pode
        # disparar o fluxo por si so: se nenhuma outra parte filtrada sobrar,
        # o fluxo nao ocorre. Se sobrar, ele roda normalmente para as outras —
        # e o comentario aponta a PJDP detectada.
        nome_norm = _normalizar(nome)
        if nome in pjdp or nome_norm in pjdp_norm:
            logger.info(
                '[DOMICILIO_ELETRONICO] parte "%s" e PJDP - fora do alvo do wrapper, ignorando',
                nome,
            )
            continue
        # Parte COM advogado nao precisa de nova notificacao por correio nem de
        # novo lembrete: ja e' intimada pelo proprio advogado no PJe. Ela sai do
        # filtro (e, por consequencia, do lembrete e dos destinatarios da PEC).
        # O fluxo so segue se sobrar ao menos um alvo SEM advogado.
        if nome in com_advogado or nome_norm in com_adv_norm:
            logger.info(
                '[DOMICILIO_ELETRONICO] parte "%s" TEM advogado - fora do alvo do wrapper, ignorando',
                nome,
            )
            if nome not in saida.alvos_com_advogado:
                saida.alvos_com_advogado.append(nome)
            continue
        expedientes_candidatos.setdefault(nome, []).append(exp)

    import unicodedata

    def _normalizar(txt: Any) -> str:
        if not txt:
            return ""
        s = unicodedata.normalize('NFKD', str(txt).strip().lower())
        return ''.join(c for c in s if not unicodedata.combining(c))

    def _pontuar_candidato(exp_item: Dict[str, Any]) -> Tuple[int, int, int]:
        id_doc = exp_item.get('idDocumento')
        doc = _doc(id_doc) or {}
        tit_norm = _normalizar(doc.get('titulo') or '')
        tipo_exp_norm = _normalizar(exp_item.get('tipoExpediente') or '')

        # Prioridade máxima para Notificação (específica da citação inicial)
        # Evita registrar o ID genérico de Intimação/Despacho compartilhado
        if 'notific' in tit_norm or 'notific' in tipo_exp_norm:
            score_tipo = 300
        elif 'citac' in tit_norm or 'citac' in tipo_exp_norm:
            score_tipo = 200
        elif 'intimac' in tit_norm or 'intimac' in tipo_exp_norm:
            # Intimação genérica compartilhada tem prioridade baixa
            score_tipo = 50
        else:
            score_tipo = 100

        score_uid = 50 if doc.get('idUnicoDocumento') else 0

        id_exp = exp_item.get('id') or 0
        try:
            id_exp_num = int(id_exp)
        except Exception:
            id_exp_num = 0

        return (score_tipo, score_uid, id_exp_num)

    # Registra os alvos que seriam candidatos DOM mas foram removidos por terem
    # advogado (o loop acima ja' aplicou o filtro). Serve para o chamador logar
    # e, se precisar, montar a lista de destinatarios da PEC.
    saida.alvos_com_advogado = sorted(com_advogado)
    logger.info(
        '[DOMICILIO_ELETRONICO] alvos com advogado (fora do fluxo): %s',
        ', '.join(saida.alvos_com_advogado) or '-',
    )

    for nome, lista_exps in expedientes_candidatos.items():
        melhor_exp = max(lista_exps, key=_pontuar_candidato)
        id_documento = melhor_exp.get('idDocumento')
        doc = _doc(id_documento) or {}
        chave = doc.get('idUnicoDocumento')
        titulo_doc = doc.get('titulo') or ''

        if not chave:
            logger.warning(
                '[DOMICILIO_ELETRONICO] expediente %s (idDocumento=%s): '
                'documento sem idUnicoDocumento (titulo=%r)',
                melhor_exp.get('id'), id_documento, titulo_doc,
            )

        saida.append({
            'empresa': nome,
            'id_unico_documento': chave,
            'id_documento': id_documento,
            'titulo_documento': titulo_doc,
            'id_processo_expediente': melhor_exp.get('idProcessoExpediente'),
            'id_expediente': melhor_exp.get('id'),
            'tipo_expediente': melhor_exp.get('tipoExpediente'),
            'ciencia_via_sistema': melhor_exp.get('cienciaViaSistema', False),
            'data_ciencia': melhor_exp.get('dataCiencia'),
            'pessoa_ciencia': melhor_exp.get('pessoaCiencia'),
            'prazo_vencido': melhor_exp.get('prazoVencido'),
            'fechado': melhor_exp.get('fechado'),
            'prazo_legal': melhor_exp.get('prazoLegal'),
        })

    return saida


def _montar_conteudo_lembrete_dom(destinatarios: Any) -> str:
    """Monta o conteudo do lembrete DomElet (uma linha, max 200 chars no PJe).

    Exemplo:
        Citação - renovei via correios: SP MARKET - 8201597, BANCO CSF - 030869f

    A frase estável "renovei via correios" é a assinatura usada na detecção de
    idempotência (_verificar_lembrete_presente): bate contra o lembrete padrão
    do PJe (título variável "NOT. ID <hash>", conteúdo "... Renovei via Correios.").
    """
    cabecalho = "Citação - renovei via correios: "
    partes: List[str] = []

    if isinstance(destinatarios, str):
        for bruto in (destinatarios or "").split(","):
            nome = bruto.strip()
            if nome:
                partes.append(nome)
    elif destinatarios:
        for item in destinatarios:
            if not isinstance(item, dict):
                continue
            nome = (item.get('empresa') or item.get('nome_parte') or '').strip()
            if not nome:
                continue
            uid = item.get('id_unico_documento')
            if uid:
                partes.append(f"{nome} - {uid}")
            else:
                partes.append(nome)

    if not partes:
        return f"{cabecalho}(destinatario nao identificado via API)"

    texto = cabecalho + ", ".join(partes)
    return texto[:200]


def _montar_conteudo_gigs_dom(destinatarios: Any) -> str:
    """Monta o texto da GIGS sem prazo do domicilio eletronico.

    Substitui o par lembrete DomicEletr + comentario que era criado antes da
    PEC. Uma unica GIGS sem prazo registra que a citacao sera renovada por
    correio, listando empresa e o id da notificacao em cada linha.

    Formato (pedido em 30/10/2026):
        Domicilio eletronico - citacao renovada por correio para:
        - Empresa 1 (id c3a4c57)
        - Empresa 2 (id 14f9166)

    O id e' o `idUnicoDocumento` do documento do expediente — o mesmo que a
    timeline usa no seletor `#doc_<id>`. Nao confundir com:
        idDocumento            -> id numerico do documento (495200526)
        idDestinatario...Dom   -> id do destinatario (2534639)

    Args:
        destinatarios: lista de dicts de `_checar_empresas_e_ids_api`, ou
            uma string com nomes separados por virgula. Aceita os dois.

    Returns:
        Texto pronto para criar_gigs(driver, "", "", conteudo).
    """
    cabecalho = "Domicilio eletronico - citacao renovada por correio para:"

    # Normaliza a entrada para uma lista de pares (empresa, id_notificacao).
    pares: List[tuple] = []

    if isinstance(destinatarios, str):
        # formato antigo: "EMPRESA A, EMPRESA B" — sem id
        for bruto in (destinatarios or "").split(","):
            nome = bruto.strip()
            if nome:
                pares.append((nome, None))
    elif destinatarios:
        for item in destinatarios:
            if not isinstance(item, dict):
                continue
            nome = (item.get('nome_parte') or item.get('empresa') or '').strip()
            if not nome:
                continue
            id_notif = item.get('id_unico_documento')
            pares.append((nome, id_notif))

    if not pares:
        # Sem destinatario identificado: registra mesmo assim, sem lista vazia.
        return f"{cabecalho} (destinatario nao identificado via API)"

    # Deduplica por (empresa, id). Um mesmo destinatario pode aparecer em mais
    # de uma parte do mesmo expediente; o par repetido e' o que importa.
    vistos = set()
    linhas = [cabecalho]
    for nome, id_notif in pares:
        chave = (nome, id_notif)
        if chave in vistos:
            continue
        vistos.add(chave)
        if id_notif:
            linhas.append(f"- {nome} (id {id_notif})")
        else:
            # sem id: registra sem inventar, para nao mascarar falha de API
            linhas.append(f"- {nome} (id nao identificado)")

    return "\n".join(linhas)


def _tem_ata_audiencia(id_processo: str, driver: Any) -> bool:
    """Verifica se ha Ata de Audiencia na timeline do processo via API.

    Args:
        id_processo: ID interno do processo (string numerica).
        driver: Instancia para extrair sessao.

    Returns:
        True se encontrou item de ata de audiencia na timeline.
    """
    import unicodedata

    def _norm(s: str) -> str:
        return unicodedata.normalize('NFKD', (s or '').lower()).encode('ascii', 'ignore').decode()

    try:
        from Fix.variaveis import PjeApiClient, session_from_driver as _sfp
        _sess, _base = _sfp(driver)
        _client = PjeApiClient(_sess, _base)
        _tl = _client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=True)
        if not _tl:
            return False
        for item in _tl:
            texto = _norm(item.get('tipo') or '') + ' ' + _norm(item.get('titulo') or '')
            if 'ata' in texto and 'audienci' in texto:
                logger.info('[DOMICILIO_ELETRONICO] Ata de audiencia encontrada na timeline de %s', id_processo)
                return True
        return False
    except Exception as e:
        logger.warning('[DOMICILIO_ELETRONICO] _tem_ata_audiencia falhou para %s: %s', id_processo, e)
        return False


def _data_audiencia_api(id_processo: str, driver: Any) -> Optional[str]:
    """Data (ISO) da proxima audiencia do processo, pela API do PJe.

    A API e a fonte decisiva: o `processo_info` do fluxo DOM carrega apenas
    id/numeroProcesso, e o cabecalho da tela pode nao estar renderizado no
    momento da leitura.

    Endpoint (api/apis.md 26.1, o mesmo do maisPJE `obterAudienciaMarcada`):
        GET /pje-comum-api/api/processos/id/{idProcesso}/audiencias
    Primeira audiencia da lista, campo `dataInicio`.

    Args:
        id_processo: ID interno do processo (string numerica).
        driver: Instancia para extrair sessao.

    Returns:
        String ISO (ex.: '2026-11-03T09:00:00') ou None sem audiencia.
    """
    if not id_processo:
        return None
    try:
        from Fix.variaveis import PjeApiClient, session_from_driver as _sfp
        _sess, _base = _sfp(driver)
        _client = PjeApiClient(_sess, _base)
        return _client.data_proxima_audiencia(id_processo)
    except Exception as e:
        logger.warning(
            '[DOMICILIO_ELETRONICO] _data_audiencia_api falhou para %s: %s', id_processo, e
        )
        return None


def _resolver_dia_audiencia(driver: Any, processo_info: Optional[Dict] = None) -> Optional[int]:
    """Dia da semana da audiencia (0=segunda ... 6=domingo), ou None.

    O fluxo DOM decide o modelo do PEC pelo dia da audiencia — mesma regra da
    triagem (seg/ter/sex -> AR-Ordv/AR-Sumv; qua/qui -> AR-Or/AR-Su):

      1. `processo_info`: a lista inicial do DOM
         (`buscar_processos_conhecimento_dom`) ja traz `dataProximaAudiencia`,
         entao este caminho cobre o caso normal sem chamada extra.
      2. `<dd>`/`dt#audiencias` da pagina (via _dia_semana_audiencia).
      3. API de audiencias (`dataProximaAudiencia` do processo) — decisiva,
         usada quando a lista veio do cache do dia ou sem a data.

    Args:
        driver: Instancia na aba de detalhes do processo.
        processo_info: Dict do processo.

    Returns:
        Inteiro 0..6 ou None quando a data nao pode ser determinada.
    """
    # 1 + 2: processo_info (lista inicial) e depois o DOM da pagina
    dia = _dia_semana_audiencia(driver, processo_info)
    if dia is not None:
        return dia

    # 3: API de audiencias
    id_processo = str((processo_info or {}).get('id') or '')
    if not id_processo:
        try:
            url_atual = getattr(driver, "current_url", "") or getattr(
                getattr(driver, "page", None), "url", ""
            )
            m_id = re.search(r'/processo/(\d+)', url_atual)
            if m_id:
                id_processo = m_id.group(1)
        except Exception:
            pass

    data_api = _data_audiencia_api(id_processo, driver)
    if data_api:
        dia = _dia_semana_audiencia(None, {'dataProximaAudiencia': data_api})
        if dia is not None:
            logger.info(
                '[DOMICILIO_ELETRONICO] Data da audiencia via API para %s: %s',
                id_processo or '?', data_api,
            )
            return dia

    return None



def is_processo_100_digital(driver: Any) -> bool:
    """Verifica se o processo e 100% digital baseado na presenca da logo no cabecalho.

    Args:
        driver: Instancia do navegador.

    Returns:
        True se o processo possui a logo do juizo 100% digital.
    """
    try:
        logo_juizo = espera.elementos(
            driver, 'img.logo_juizo[alt="Juizo 100% Digital"]', teto=1
        )
        return len(logo_juizo) > 0
    except Exception:
        return False


# =============================================================================
# Callbacks
# =============================================================================


def callback_bucket1(driver: Any, tipo: str = "desconhecido") -> bool:
    """Callback para bucket 1 (sem audiencia): remove chips domicilio eletronico.

    Args:
        driver: Instancia na aba de detalhes do processo.
        tipo: Tipo do processo (para log).

    Returns:
        True se a operacao foi bem-sucedida.
    """
    numero = getattr(driver, "_numero_processo_lista", "desconhecido")
    logger.info("[DOMICILIO_ELETRONICO][B1][CALLBACK] Executando acoes para %s", numero)

    chips_domicilio = [
        "Domicilio Eletronico - Ciencia Automatica",
        "Domicilio Eletronico - Prazo de Ciencia Expirado",
        "Domicilio Eletronico - Prazo de Resposta Excedido",
        "Domicilio Eletronico - Erro na Transmissao",
    ]
    result = def_chip(
        driver,
        numero_processo=numero,
        observacao="Remover chips domicilio eletronico",
        chips_para_remover=chips_domicilio,
        debug=True,
    )
    logger.info("[DOMICILIO_ELETRONICO][B1][CALLBACK] def_chip result: %s", result)
    return result


def callback_bucket2(
    driver: Any,
    tipo_processo: str = "desconhecido",
    processo_info: Optional[Dict] = None,
) -> bool:
    """Callback para bucket 2 (com audiencia): acoes completas DOM.

    Fluxo:
      1. Remove chips de ciencia expirado e resposta excedido
      2. Verifica lembrete Dom Eletronico
         - Se nao existe: checa empresas/notificações via API, cria comentário Bianca e lembrete DomElet, apaga chips
      3. Executa PEC conforme tipo e dia da audiência

    Args:
        driver: Instancia na aba de detalhes do processo.
        tipo_processo: String com tipo do processo (ATOrd, ATSum, ACum).

    Returns:
        True se o PEC foi criado com sucesso.
    """
    numero = getattr(driver, "_numero_processo_lista", "desconhecido")

    logger.info(
        "[DOMICILIO_ELETRONICO][B2][CALLBACK] Executando acoes para %s (%s)", numero, tipo_processo
    )

    # Extrair ID do processo da URL (necessario para _checar_empresas_e_ids_api)
    id_processo = None
    try:
        url_atual = getattr(driver, "current_url", "") or getattr(getattr(driver, "page", None), "url", "")
        m_id = re.search(r'/processo/(\d+)/', url_atual)
        if m_id:
            id_processo = m_id.group(1)
    except Exception:
        pass

    if not id_processo:
        logger.warning(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Nao foi possivel extrair id_processo da URL para %s", numero
        )

    # 1. Checar empresas com expedientes pendentes de domicilio eletronico
    destinatarios_dom = _checar_empresas_e_ids_api(id_processo, driver) if id_processo else []
    pjdp = list(getattr(destinatarios_dom, 'pjdp_detectado', []) or [])
    com_advogado = list(getattr(destinatarios_dom, 'alvos_com_advogado', []) or [])

    logger.info(
        "[DOMICILIO_ELETRONICO][B2][CALLBACK] %d empresa(s) no filtro DOM: %s",
        len(destinatarios_dom),
        ", ".join(
            f"{d.get('empresa') or '?'} ({d.get('id_unico_documento') or 'sem id'})"
            for d in destinatarios_dom
        ) or "-",
    )

    # Se a única reclamada com domicílio é PJDP (ou nenhuma empresa sobrou no filtro):
    # PJDP não é alvo do wrapper (AR/correio); se ela é a única, pula o processo (não faz nada).
    if not destinatarios_dom:
        motivo = "pulando processo (nenhuma acao / nao executa wrapper)"
        if com_advogado and not pjdp:
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Todos os alvos com domicilio eletronico TEM advogado (%s) — %s",
                ", ".join(com_advogado),
                motivo,
            )
        elif pjdp and com_advogado:
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Alvos com domicilio eletronico: PJDP (%s) + com advogado (%s) — %s",
                ", ".join(pjdp),
                ", ".join(com_advogado),
                motivo,
            )
        elif pjdp:
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] A unica reclamada com domicilio eletronico e PJDP (%s) — %s",
                ", ".join(pjdp),
                motivo,
            )
        else:
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Nenhuma empresa com expedientes pendentes no filtro DOM — %s",
                motivo,
            )
        return True

    # 2. APAGAR CHIPS DE DOMICILIO — PRIMEIRO, antes de comentario/lembrete/PEC.
    #    O def_chip e a acao mais sensivel a tela limpa (os chips ficam no
    #    cabecalho e podem ser atropelados por modais de comentario/post-it).
    #    Feito uma unica vez aqui, nao se repete nos ramos abaixo.
    chips_ciencia_resposta = [
        "Domicilio Eletronico - Ciencia Automatica",
        "Domicilio Eletronico - Prazo de Ciencia Expirado",
        "Domicilio Eletronico - Prazo de Resposta Excedido",
    ]

    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Apagando chips de domicilio (antes de comentario/lembrete)...")
    result_def_chip = def_chip(
        driver,
        numero_processo=numero,
        observacao="Remover ciencia expirado e resposta excedido",
        chips_para_remover=chips_ciencia_resposta,
        debug=True,
    )
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] def_chip result: %s", result_def_chip)

    # Verificar acesso negado apos def_chip
    try:
        _verificar_acesso_negado(driver, f"DOM_{numero}_def_chip")
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Acesso negado detectado apos def_chip"
                " - propagando para recuperacao"
            )
            raise
        else:
            logger.error(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro inesperado na verificacao"
                " de acesso negado: %s",
                e,
            )

    # 3. Comentario Bianca — marca "DOM" ou "DOM com PJDP detectado".
    #    A deteccao do lembrete so roda DEPOIS que o comentario termina (ordem
    #    chips -> comentario -> deteccao -> cria lembrete -> PEC). Roda-la antes
    #    fazia a leitura do painel de post-its acontecer junto com o proprio
    #    comentario e a deteccao nao enxergava o lembrete existente.
    observacao_dom = 'DOM com PJDP detectado' if pjdp else 'DOM'
    logger.info(
        "[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando comentario: %r",
        observacao_dom,
    )
    try:
        coment_ok = criar_comentario(driver, observacao_dom, log=True)
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] criar_comentario -> %s",
            coment_ok,
        )
    except Exception as e:
        logger.error(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro ao criar comentario: %s", e
        )

    # 4. Deteccao do lembrete Dom Eletronico — depois do comentario
    logger.info(
        "[DOMICILIO_ELETRONICO][B2][CALLBACK] Verificando lembrete Dom Eletronico (apos comentario)..."
    )
    lembrete_existe = has_dom_eletronico_reminder(driver)
    executar_pec = False  # Flag para determinar se PEC deve ser executada

    logger.info(
        "[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete_existe=%s",
        lembrete_existe,
    )

    if lembrete_existe:
        # Lembrete existe - extrair conteúdo
        conteudo = _extrair_conteudo_lembrete_dom(driver)

        # Log adicional para debug: listar títulos encontrados (quando existir)
        try:
            titles = espera.elementos(driver, "mat-panel-title.post-it-titulo", teto=2)
            titulos_texto = [(getattr(t, "text", "") or "").strip() for t in titles if (getattr(t, "text", "") or "").strip()]
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Titulos encontrados=%s",
                titulos_texto,
            )
        except Exception as e_titles:
            logger.debug("[DOMICILIO_ELETRONICO][B2][CALLBACK] falha ao listar titulos: %s", e_titles)

        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete existente encontrado (conteudo=%r)",
            conteudo,
        )

        # Normalização para aceitar variações
        def _norm_text(s: str) -> str:
            try:
                import unicodedata
                s2 = unicodedata.normalize("NFKD", s or "")
                s2 = s2.encode("ascii", "ignore").decode("ascii", "ignore")
                return s2.lower()
            except Exception:
                return (s or "").lower()

        conteudo_norm = _norm_text(conteudo or "")
        contem_correio = "correio" in conteudo_norm
        contem_enviado = "enviado" in conteudo_norm
        contem_via_correio = ("via" in conteudo_norm and contem_correio) or ("correio enviado" in conteudo_norm)

        if conteudo and (contem_via_correio or (contem_correio and contem_enviado)):
            # Sub-case 2a: Via correio já registrado — NAO cria lembrete, NAO executa PEC
            # (chips ja foram apagados no passo 2)
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Conteudo indica correio (norm=%r) - SEM lembrete novo, SEM PEC",
                conteudo_norm,
            )
            executar_pec = False
        else:
            # Sub-case: Lembrete existe mas não indica correio/enviado
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete existe mas NAO indica correio enviado. contem_correio=%s contem_enviado=%s via_correio=%s. Pule (sem PEC). conteudo_norm=%r",
                contem_correio,
                contem_enviado,
                contem_via_correio,
                conteudo_norm,
            )
            executar_pec = False
    else:
        # Sub-case 2b: Sem lembrete - cria lembrete e executa PEC
        # (chips ja foram apagados no passo 2)
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Sem lembrete Dom Eletronico"
            " - criando lembrete + PEC"
        )

        # Lembrete Post-it (DomElet) com formato: Citação - renovei via correios: (Empresa - idNotificacao)
        titulo_dom = "DomElet"
        conteudo_dom = _montar_conteudo_lembrete_dom(destinatarios_dom)
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando lembrete post-it [%s]: %r",
            titulo_dom,
            conteudo_dom,
        )
        try:
            lembrete_ok = criar_lembrete_posit(
                driver, titulo_dom, conteudo_dom, debug=True,
                marcadores_titulo=["domelet", "not. id"],
                marcadores_conteudo=["renovei via correios"],
            )
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] criar_lembrete_posit -> %s",
                lembrete_ok,
            )
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro ao criar lembrete post-it: %s",
                e,
            )

        # Executar PEC
        executar_pec = True
        
        # Verificar acesso negado apos criacao do lembrete
        try:
            _verificar_acesso_negado(driver, f"DOM_{numero}_lembrete")
        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                logger.warning(
                    "[DOMICILIO_ELETRONICO][B2][CALLBACK] Acesso negado detectado apos lembrete"
                    " - propagando para recuperacao"
                )
                raise
            else:
                logger.error(
                    "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro inesperado na verificacao"
                    " de acesso negado: %s",
                    e,
                )

    # 5. Executar PEC AR (apenas se flag executar_pec = True)
    if not executar_pec:
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Pulando PEC (lembrete com via correio ou nenhuma acao necessaria)"
        )
        return True

    dia_sem = _resolver_dia_audiencia(driver, processo_info)
    if dia_sem is None:
        logger.warning(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Dia da audiencia NAO identificado para %s"
            " (processo_info/DOM/API) - usando PEC AR padrao (qua/qui)",
            numero,
        )
        dia_desc = "indefinido"
        is_seg_ter_sex = False
    else:
        dia_desc = _NOMES_DIA[dia_sem]
        is_seg_ter_sex = dia_sem in _DIAS_DESPACHO_NOVO

    if is_seg_ter_sex:
        if "ATSum" in tipo_processo:
            logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando PEC AR Sumaria seg/ter/sex (pec_arsumv -> AR-Sumv) [dia=%s]", dia_desc)
            pec_wrapper = pec_arsumv
        else:
            logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando PEC AR Ordinaria seg/ter/sex (pec_arordv -> AR-Ordv) [dia=%s]", dia_desc)
            pec_wrapper = pec_arordv
    else:
        if "ATSum" in tipo_processo:
            logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando PEC AR Sumaria padrao (pec_arsum -> AR-Su) [dia=%s]", dia_desc)
            pec_wrapper = pec_arsum
        else:
            logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando PEC AR Ordinaria padrao (pec_arord -> AR-Or) [dia=%s]", dia_desc)
            pec_wrapper = pec_arord

    # Verificar abas antes da PEC
    abas_antes = len(_obter_abas(driver))
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Abas antes da PEC: %s", abas_antes)

    result_pec = pec_wrapper(driver, debug=True)
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] PEC result: %s", result_pec)

    # Verificar acesso negado apos execucao da PEC
    try:
        _verificar_acesso_negado(driver, f"DOM_{numero}_pec")
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Acesso negado detectado apos PEC"
                " - propagando para recuperacao"
            )
            raise
        else:
            logger.error(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro inesperado na verificacao"
                " de acesso negado: %s",
                e,
            )

    # Verificar abas depois da PEC
    abas_depois = len(_obter_abas(driver))
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Abas depois da PEC: %s", abas_depois)

    if abas_depois <= abas_antes:
        logger.warning(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] AVISO: Nenhuma nova aba foi aberta pela PEC!"
        )
        return False

    return result_pec


# =============================================================================
# Filtro de chips DOM (helper)
# =============================================================================


def _filtro_chips_dom(
    driver: Any, chips_alvo: List[str]
) -> bool:
    """Aplica filtro de chips para domicilio eletronico no painel global.

    Args:
        driver: Instancia do navegador.
        chips_alvo: Lista de strings para filtrar (ex: 'domicilio eletronico expirado').

    Returns:
        True se ao menos um chip foi selecionado com sucesso.
    """
    logger.info("[DOMICILIO_ELETRONICO] Aplicando filtro de chips: %s", chips_alvo)

    chips_mapeamento = {
        "domicilio eletronico expirado": (
            "Domicilio Eletronico - Prazo de Ciencia Expirado"
        ),
        "domicilio eletronico expedido": (
            "Domicilio Eletronico - Prazo de Resposta Excedido"
        ),
        "domicilio eletronico erro na transmissao": (
            "Domicilio Eletronico - Erro na Transmissao"
        ),
    }

    chips_alvo_mapeados = [
        chips_mapeamento.get(chip, chip) for chip in chips_alvo
    ]

    # Encontrar seletor de chips
    chips_element = espera.elemento(driver, "//span[contains(text(), 'Chips')]", teto=2)
    if not chips_element:
        chips_element = espera.elemento(driver, "span.ng-tns-c82-22.ng-star-inserted", teto=2)

    if not chips_element:
        logger.error("[DOMICILIO_ELETRONICO] Elemento chips nao encontrado")
        return False

    # Clicar para abrir dropdown
    _executar_js(driver, "arguments[0].click();", chips_element)
    espera.assentar(driver, 1)

    # Aguardar painel
    painel_selector = (
        ".mat-select-panel-wrap.ng-trigger-transformPanelWrap"
    )
    if not espera.ate_aparecer(driver, painel_selector, teto=10):
        logger.error("[DOMICILIO_ELETRONICO] Painel de chips nao apareceu")
        return False

    espera.ate_aparecer(driver, "mat-option", teto=5)
    painel = espera.elemento(driver, painel_selector, teto=2)
    opcoes = _sub_els(painel, "mat-option") if painel else espera.elementos(driver, "mat-option", teto=2)
    chips_selecionados: List[str] = []

    for chip in chips_alvo_mapeados:
        for opcao in opcoes:
            try:
                texto = (getattr(opcao, "text", "") or "").strip()
                is_vis = getattr(opcao, "is_displayed", lambda: True)()
                if chip in texto and is_vis:
                    _executar_js(driver, "arguments[0].click();", opcao)
                    chips_selecionados.append(chip)
                    espera.ate_aparecer(driver, "mat-option.mat-selected", teto=3)
                    break
            except Exception:
                continue

    # Aplicar filtro
    botao_filtrar = espera.elemento(
        driver, 'button[aria-label="Filtrar"]', teto=5
    )
    if botao_filtrar:
        _executar_js(driver, "arguments[0].click();", botao_filtrar)
        espera.ate_aparecer(driver, "tbody tr.tr-class", teto=10)

    logger.info("[DOMICILIO_ELETRONICO] Chips aplicados: %s", chips_selecionados)
    return len(chips_selecionados) > 0


# =============================================================================
# Navegacao e filtros no painel de atividades
# =============================================================================


def navigate_to_activities_and_filter(driver: Any) -> bool:
    """Navega para o painel de atividades e aplica filtro dom.e.

    Fluxo:
      1. Navega para URL_ATIVIDADES
      2. Remove chip "Vencidas" se existir
      3. Clica icone fa-pen e preenche descricao com "dom.e"
      4. Aplica filtro 100 itens por pagina

    Args:
        driver: Instancia do navegador.

    Returns:
        True se a navegacao e filtros foram bem-sucedidos.
    """
    try:
        # 1. Navegar para painel de atividades
        if hasattr(driver, "get"):
            driver.get(URL_ATIVIDADES)
        elif hasattr(driver, "page") and hasattr(driver.page, "goto"):
            driver.page.goto(URL_ATIVIDADES)
        espera.ate_url(driver, "atividades", teto=10)
        logger.info("[DOMICILIO_ELETRONICO] Navegado para painel de atividades")

        # 2. Remover chip "Vencidas" se existir
        try:
            chips = espera.elementos(driver, "mat-chip", teto=3)
            removido = False
            for chip in chips:
                chip_text = getattr(chip, "text", "") or ""
                if "Vencidas" in chip_text:
                    btns = _sub_els(
                        chip, "button.chips-icone-fechar"
                    )
                    for btn in btns:
                        try:
                            if safe_click(driver, btn, timeout=5, log=False):
                                logger.info(
                                    "[DOMICILIO_ELETRONICO] Chip Vencidas removido."
                                )
                                removido = True
                                break
                        except Exception as e:
                            logger.warning(
                                "[DOMICILIO_ELETRONICO] Erro ao clicar no botao"
                                " de fechar chip Vencidas: %s",
                                e,
                            )
                    if removido:
                        break
            if not removido:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Chip Vencidas nao encontrado ou ja removido."
                )
        except Exception as e:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Erro ao verificar/remover chip Vencidas: %s", e
            )

        # 3. Aplicar filtro dom.e
        btn_fa_pen = esperar_elemento(driver, "i.fa-pen", timeout=10)
        if btn_fa_pen:
            safe_click(driver, btn_fa_pen)

        campo_descricao = esperar_elemento(
            driver, 'input[aria-label*="Descricao"]', timeout=10
        )
        if campo_descricao:
            if hasattr(campo_descricao, "clear"):
                campo_descricao.clear()
            _enviar_teclas(campo_descricao, "dom.e")
            _pressionar_tecla(driver, campo_descricao, "Enter", _KEY_ENTER)
            logger.info(
                "[DOMICILIO_ELETRONICO] Filtro dom.e aplicado no painel de atividades"
            )
            espera.ate_aparecer(
                driver, "tr.cdk-drag", teto=10
            )

        # 4. Aplicar filtro 100
        aplicar_filtro_100(driver)
        logger.info("[DOMICILIO_ELETRONICO] Filtro 100 aplicado")
        espera.ate_aparecer(
            driver, "tr.cdk-drag", teto=10
        )

    except Exception as e:
        logger.error(
            "[DOMICILIO_ELETRONICO] Erro na navegacao para atividades: %s", e
        )
        return False

    return True


# =============================================================================
# Processamento de processo individual
# =============================================================================


def processar_processo_dom(
    driver: Any,
    proc_id: str,
    linha: Any,
    aba_lista_original: str,
) -> bool:
    """Processa um unico processo DOM com recuperacao de acesso negado.

    Args:
        driver: Instancia do navegador.
        proc_id: ID do processo.
        linha: Elemento da linha na tabela.
        aba_lista_original: Handle da aba da lista.

    Returns:
        True se processado com sucesso.

    Raises:
        Exception: Com prefixo RESTART_DRIVER se o driver precisa ser reiniciado.
    """
    try:
        logger.info("[DOMICILIO_ELETRONICO] Processando processo: %s", proc_id)

        # Reindexar linha se necessario (cuidar de erros de conexao)
        try:
            is_vis = getattr(linha, "is_displayed", None)
            if is_vis is not None and not is_vis():
                raise Exception("linha not displayed")
            linha_atual = linha
        except Exception:
            try:
                linha_atual = reindexar_linha(driver, proc_id)
            except Exception as re_e:
                msg = str(re_e)
                logger.error("[DOMICILIO_ELETRONICO] Erro geral na reindexacao: %s", msg)
                if (
                    "Tried to run command without establishing a connection"
                    in msg
                    or "disconnected" in msg.lower()
                ):
                    raise Exception(
                        f"RESTART_DRIVER: reindex_failed ({msg})"
                    )
                return False

            if not linha_atual:
                logger.error(
                    "[DOMICILIO_ELETRONICO] Nao foi possivel reindexar linha para %s",
                    proc_id,
                )
                return False

        # Abrir detalhes do processo
        try:
            if not abrir_detalhes_processo(driver, linha_atual):
                logger.error(
                    "[DOMICILIO_ELETRONICO] Falha ao abrir detalhes para %s", proc_id
                )
                return False
        except Exception as e_open:
            msg = str(e_open)
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro ao abrir detalhes para %s: %s", proc_id, msg
            )
            if (
                "Tried to run command without establishing a connection"
                in msg
                or "disconnected" in msg.lower()
            ):
                raise Exception(
                    f"RESTART_DRIVER: abrir_detalhes_failed ({msg})"
                )
            return False

        # Aguardar nova aba e trocar para ela
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
        except Exception as e_tab:
            msg = str(e_tab)
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro ao trocar para nova aba em %s: %s",
                proc_id,
                msg,
            )
            if (
                "Tried to run command without establishing a connection"
                in msg
                or "disconnected" in msg.lower()
            ):
                raise Exception(
                    f"RESTART_DRIVER: trocar_para_nova_aba_failed ({msg})"
                )
            return False

        if not nova_aba:
            logger.error(
                "[DOMICILIO_ELETRONICO] Nova aba nao carregou para %s", proc_id
            )
            return False

        # 0. Remover chips DOM Eletronico antes de qualquer verificacao
        _chips_dom_pre = [
            "Domicilio Eletronico - Ciencia Automatica",
            "Domicilio Eletronico - Prazo de Ciencia Expirado",
            "Domicilio Eletronico - Prazo de Resposta Excedido",
            "Domicilio Eletronico - Erro na Transmissao",
        ]
        try:
            def_chip(
                driver,
                numero_processo=proc_id,
                observacao="Remover chips DOM pre-fluxo",
                chips_para_remover=_chips_dom_pre,
                debug=True,
            )
        except Exception as _e_chip_pre:
            logger.warning("[DOMICILIO_ELETRONICO] Erro ao remover chips pre-fluxo: %s", _e_chip_pre)

        # Verificar ata de audiencia na timeline antes de processar
        url_det = getattr(driver, "current_url", "") or getattr(getattr(driver, "page", None), "url", "")
        _m_pid = re.search(r'/processo/(\d+)/', url_det)
        if _m_pid and _tem_ata_audiencia(_m_pid.group(1), driver):
            logger.info(
                "[DOMICILIO_ELETRONICO] Ata de audiencia na timeline de %s — pulando (filtro de lista)",
                proc_id,
            )
            return True

        # Extrair tipo do processo da aba de detalhes (mais confiavel)
        tipo_processo = "ATOrd"  # padrao
        try:
            espera.ate_aparecer(
                driver, "pje-cabecalho-processo", teto=10
            )

            tipo_js = _executar_js(
                driver,
                """
                var cabecalho = document.querySelector('pje-cabecalho-processo');
                if (cabecalho) {
                    var spansTipo = cabecalho.querySelectorAll(
                        'pje-descricao-processo span.align-end.ng-star-inserted'
                    );
                    for (var i = 0; i < spansTipo.length; i++) {
                        var texto = (spansTipo[i].innerText
                            || spansTipo[i].textContent || '').trim();
                        if (texto && (texto.includes('ATOrd')
                            || texto.includes('ATSum')
                            || texto.includes('ACum'))) {
                            return texto;
                        }
                    }
                }
                return '';
            """
            )

            if tipo_js:
                tipo_processo = str(tipo_js).strip()
                logger.info(
                    "[DOMICILIO_ELETRONICO] Tipo identificado na aba de detalhes: %s",
                    tipo_processo,
                )
            else:
                logger.warning(
                    "[DOMICILIO_ELETRONICO] Tipo nao identificado na aba de detalhes"
                    " para %s, usando padrao ATOrd",
                    proc_id,
                )
                tipo_processo = "ATOrd"
        except Exception as e:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Erro ao extrair tipo da aba de detalhes"
                " para %s: %s, usando padrao ATOrd",
                proc_id,
                e,
            )
            tipo_processo = "ATOrd"

        # Executar callback do bucket 2
        try:
            driver._numero_processo_lista = proc_id
            result = callback_bucket2(
                driver, tipo_processo, processo_info={"id": proc_id, "numeroProcesso": proc_id}
            )
            if result:
                logger.info("[DOMICILIO_ELETRONICO] Callback OK para %s", proc_id)
                return True
            else:
                logger.error(
                    "[DOMICILIO_ELETRONICO] Callback falhou para %s", proc_id
                )
                return False
        except Exception as e:
            # Se e RESTART_DRIVER, propagar para recuperacao
            if "RESTART_DRIVER" in str(e):
                logger.warning(
                    "[DOMICILIO_ELETRONICO] Acesso negado detectado no callback"
                    " para %s - propagando para recuperacao",
                    proc_id,
                )
                raise
            # Outras excecoes sao erros do callback
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro no callback para %s: %s", proc_id, e
            )
            return False
        finally:
            if hasattr(driver, "_numero_processo_lista"):
                delattr(driver, "_numero_processo_lista")

    except Exception as e:
        msg = str(e)
        logger.error(
            "[DOMICILIO_ELETRONICO] Erro geral no processamento de %s: %s", proc_id, msg
        )
        if (
            "Tried to run command without establishing a connection" in msg
            or "RESTART_DRIVER" in msg
            or "disconnected" in msg.lower()
        ):
            raise Exception(f"RESTART_DRIVER: {msg}")
        return False
    finally:
        # Gerenciar abas apos processamento
        _gerenciar_abas_apos_processo_dom(driver, aba_lista_original)


def _gerenciar_abas_apos_processo_dom(
    driver: Any, aba_lista_original: str
) -> None:
    """Gerencia abas apos processamento de um processo no DOM.

    Fecha todas as abas exceto a da lista original.

    Args:
        driver: Instancia do navegador.
        aba_lista_original: Handle da aba da lista.

    Raises:
        Exception: Com prefixo RESTART_DRIVER se o driver estiver desconectado.
    """
    try:
        # Verificar handles validos
        try:
            handles = _obter_abas(driver)
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO] Driver desconectado ao ler window_handles: %s", e
            )
            raise Exception(f"RESTART_DRIVER: driver_disconnect ({e})")

        if aba_lista_original not in handles:
            logger.error("[DOMICILIO_ELETRONICO] Aba da lista nao esta mais disponivel")
            raise Exception("RESTART_DRIVER: aba_lista_original_missing")

        # Fechar outras abas com cuidado
        for handle in handles:
            if handle == aba_lista_original:
                continue
            try:
                if hasattr(driver, "switch_to"):
                    driver.switch_to.window(handle)
                if hasattr(driver, "close"):
                    driver.close()
                logger.info("[DOMICILIO_ELETRONICO] Aba fechada: %s...", str(handle)[:20])
            except Exception as e:
                msg = str(e)
                logger.warning(
                    "[DOMICILIO_ELETRONICO] Erro ao fechar aba %s...: %s",
                    str(handle)[:20],
                    msg,
                )
                if (
                    "Tried to run command without establishing a connection"
                    in msg
                    or "disconnected" in msg.lower()
                ):
                    raise Exception(f"RESTART_DRIVER: {msg}")
                continue

        # Retornar a aba da lista e aguardar estabilizacao do DOM
        try:
            if hasattr(driver, "switch_to"):
                driver.switch_to.window(aba_lista_original)
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO] Falha ao retornar para aba da lista: %s", e
            )
            raise Exception(f"RESTART_DRIVER: switch_to_failed ({e})")

        # Pequena espera para evitar rate-limit
        espera.assentar(driver, 2.0)
        espera.ate_aparecer(
            driver, "tr.cdk-drag", teto=6
        )

        logger.info("[DOMICILIO_ELETRONICO] Retornado a aba da lista")

    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            raise
        logger.error("[DOMICILIO_ELETRONICO] Falha ao gerenciar abas: %s", e)
        raise


# =============================================================================
# Execucao da lista com callback do bucket 2
# =============================================================================


def execute_list_with_bucket2_callback(driver: Any) -> bool:
    """Indexa processos e executa callback do bucket 2 em cada um.

    Fluxo:
      1. Verifica se esta no painel de atividades; se nao, navega
      2. Indexa todos os processos da lista
      3. Para cada processo: abre detalhes, executa callback bucket 2,
         fecha abas extras
      4. Aplica delay anti-rate entre itens

    Args:
        driver: Instancia do navegador.

    Returns:
        True se todos os processos foram processados sem erros.
    """
    try:
        # Verificar se estamos no painel de atividades
        try:
            cur = (getattr(driver, "current_url", "") or getattr(getattr(driver, "page", None), "url", "")).lower()
            if "atividades" in cur:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Executando fluxo no painel de atividades (dom.e)"
                )
            elif "lista-processos" in cur:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Pagina e a lista de processos"
                    " -- prosseguindo com indexacao (compativel)"
                )
            else:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Pagina atual nao e painel de atividades"
                    " nem lista; navegando para painel de atividades"
                    " e aplicando filtro dom.e"
                )
                if not navigate_to_activities_and_filter(driver):
                    logger.error(
                        "[DOMICILIO_ELETRONICO] Falha ao navegar para painel de atividades"
                    )
                    return False
                espera.ate_aparecer(
                    driver, "tr.cdk-drag", teto=10
                )
        except Exception as e:
            logger.debug(
                "[DOMICILIO_ELETRONICO] Erro no pre-check de pagina: %s", e
            )

        # 1. Indexar processos
        processos = indexar_processos(driver)
        if not processos:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Nenhum processo encontrado na lista"
            )
            return False

        logger.info(
            "[DOMICILIO_ELETRONICO] %s processos encontrados para processamento",
            len(processos),
        )

        # 2. Processar cada processo individualmente
        aba_lista_original = getattr(driver, "current_window_handle", None)
        erros = 0
        total = len(processos)

        for idx, (proc_id, linha) in enumerate(processos, 1):
            logger.info(
                "[DOMICILIO_ELETRONICO] Processando %d/%d: %s", idx, total, proc_id
            )

            try:
                ok = processar_processo_dom(
                    driver, proc_id, linha, aba_lista_original
                )
                if not ok:
                    erros += 1
                    logger.error(
                        "[DOMICILIO_ELETRONICO] Falha no processamento de %s", proc_id
                    )
            except Exception as e:
                if "RESTART_DRIVER" in str(e):
                    logger.warning(
                        "[DOMICILIO_ELETRONICO] Erro critico em %s"
                        " - propagando RESTART_DRIVER",
                        proc_id,
                    )
                    raise
                erros += 1
                logger.error(
                    "[DOMICILIO_ELETRONICO] Erro processando %s: %s", proc_id, e
                )

            # Delay anti-rate entre itens
            espera.assentar(driver, 1.25)

        sucesso = total - erros
        logger.info(
            "[DOMICILIO_ELETRONICO] Processamento concluido: %s sucesso, %s erros"
            " (total %s)",
            sucesso,
            erros,
            total,
        )
        return erros == 0

    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            raise
        logger.error("[DOMICILIO_ELETRONICO] Erro na execucao da lista: %s", e)
        return False


# =============================================================================
# Entrypoint principal
# =============================================================================

_PROGRESSO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progresso.json")


def _carregar_progresso() -> Dict[str, Any]:
    try:
        with open(_PROGRESSO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_progresso(dados: Dict[str, Any]) -> None:
    """Grava o progresso.

    O arquivo e compartilhado com o monitoramento unificado (pec/mandado/p2b/
    triagem), que faz leitura-modificacao-escrita do JSON inteiro. Como o DOM
    grava sob a chave 'dom', reler o arquivo imediatamente antes de escrever
    evita apagar o que outro fluxo tiver gravado no intervalo.
    """
    try:
        atual = _carregar_progresso()
        if isinstance(atual, dict):
            chave_dom = dados.get("dom")
            atual.update({k: v for k, v in dados.items() if k != "dom"})
            if chave_dom is not None:
                atual["dom"] = chave_dom
            dados = atual
        with open(_PROGRESSO_PATH, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("[DOMICILIO_ELETRONICO][CACHE] Falha ao salvar progresso: %s", e)


def _cache_dom_salvar_lista(processos: List[Dict[str, Any]]) -> None:
    """Persiste a lista completa de processos DOM no progresso.json."""
    prog = _carregar_progresso()
    prog["dom"] = {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "processos_pendentes": [
            {
                "id": str(p.get("id", "")),
                "numero": p.get("numeroProcesso") or p.get("numero") or "",
                # Necessario para escolher o PEC pelo dia da audiencia ao
                # retomar a partir do cache
                "dataProximaAudiencia": p.get("dataProximaAudiencia"),
            }
            for p in processos
        ],
        "processos_ok": [],
        "processos_erro": [],
        "last_update": datetime.now().isoformat(),
    }
    _salvar_progresso(prog)
    logger.info("[DOMICILIO_ELETRONICO][CACHE] Lista de %d processos salva em progresso.json", len(processos))


def _cache_dom_carregar_pendentes() -> Optional[List[Dict[str, Any]]]:
    """Retorna lista pendente do dia se existir, None caso contrário."""
    prog = _carregar_progresso()
    dom = prog.get("dom", {})
    if not dom:
        return None
    data_cache = dom.get("data", "")
    hoje = datetime.now().strftime("%Y-%m-%d")
    if data_cache != hoje:
        return None
    pendentes = dom.get("processos_pendentes", [])
    if not pendentes:
        return None
    ok = set(dom.get("processos_ok", []))
    erro = set(dom.get("processos_erro", []))
    ja_processados = ok | erro
    restantes = [p for p in pendentes if p["numero"] not in ja_processados and p["id"] not in ja_processados]
    total_orig = len(pendentes)
    logger.info("[DOMICILIO_ELETRONICO][CACHE] Cache do dia encontrado: %d/%d processos pendentes", len(restantes), total_orig)
    return restantes if restantes else None


def _cache_dom_marcar(numero: str, sucesso: bool) -> None:
    """Marca processo como ok ou erro no cache."""
    prog = _carregar_progresso()
    dom = prog.get("dom", {})
    if not dom:
        return
    chave = "processos_ok" if sucesso else "processos_erro"
    lista = dom.setdefault(chave, [])
    if numero not in lista:
        lista.append(numero)
    dom["last_update"] = datetime.now().isoformat()
    prog["dom"] = dom
    _salvar_progresso(prog)


def run_dom(driver: Any) -> Dict[str, Any]:
    """Entrypoint principal para processamento do fluxo Dom Eletronico.

    Fluxo completo:
      1. Navega para URL_LISTA_DOM
      2. Aplica filtro de fase processual (conhecimento)
      3. Navega para painel de atividades e aplica filtro dom.e
      4. Indexa processos e processa cada um com callback do bucket 2

    Args:
        driver: Instancia do navegador (ja autenticado no PJe).

    Returns:
        Dict com chave ``"sucesso"`` (bool) e opcionalmente ``"erro"`` (str).

    Example:
        >>> resultado = run_dom(driver)
        >>> resultado["sucesso"]
        True
    """
    logger.info("[DOMICILIO_ELETRONICO] === INICIANDO DOM ENGINE ===")

    try:
        # 1. Navegar para lista de processos DOM
        logger.info("[DOMICILIO_ELETRONICO] Navegando para lista de processos...")
        if hasattr(driver, "get"):
            driver.get(LIST_URL)
        elif hasattr(driver, "page") and hasattr(driver.page, "goto"):
            driver.page.goto(LIST_URL)
        espera.ate_aparecer(
            driver, "tbody tr.tr-class", teto=30
        )
        logger.info("[DOMICILIO_ELETRONICO] Navegacao concluida")

        # 2. Aplicar filtro de fase: conhecimento
        logger.info("[DOMICILIO_ELETRONICO] Aplicando filtro de fase: conhecimento")
        try:
            filtrofases(driver, fases_alvo=["conhecimento"])
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro ao aplicar filtro de fase: %s", e
            )
            return {"sucesso": False, "erro": str(e)}

        espera.ate_aparecer(
            driver, "tbody tr.tr-class", teto=10
        )

        # 3. Navegar para painel de atividades e aplicar filtro dom.e
        logger.info(
            "[DOMICILIO_ELETRONICO] Navegando para painel de atividades"
            " e aplicando filtro dom.e..."
        )
        if not navigate_to_activities_and_filter(driver):
            logger.error(
                "[DOMICILIO_ELETRONICO] Falha ao navegar para painel de atividades"
            )
            return {
                "sucesso": False,
                "erro": "Falha ao navegar para painel de atividades",
            }

        # 4. Executar lista com callback do bucket 2
        logger.info("[DOMICILIO_ELETRONICO] Executando lista com callback bucket 2...")
        sucesso = execute_list_with_bucket2_callback(driver)

        if sucesso:
            logger.info("[DOMICILIO_ELETRONICO] === EXECUCAO CONCLUIDA COM SUCESSO ===")
            return {"sucesso": True}
        else:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Execucao concluida com falhas em alguns processos"
            )
            return {
                "sucesso": False,
                "erro": "Falha no processamento de um ou mais processos",
            }

    except Exception as e:
        msg = str(e)
        logger.error("[DOMICILIO_ELETRONICO] Erro geral: %s", msg)
        return {"sucesso": False, "erro": msg}


def run_dom_api(driver: Any) -> Dict[str, Any]:
    """Entrypoint DOM via API — usa buscar_processos_conhecimento_dom() como filtro.

    Vantagem sobre run_dom: nao depende de scroll/DOM para indexar processos.
    A lista ja chega filtrada por chips 274/275/302 + audiencia.

    Fluxo:
      1. Extrai sessao do driver para PjeApiClient
      2. buscar_processos_conhecimento_dom() -> lista com id + numeroProcesso
      3. Para cada processo: navega /processo/{id}/detalhe, extrai tipo, callback_bucket2

    Args:
        driver: Instancia do navegador (ja autenticado no PJe).

    Returns:
        Dict com sucesso, processados, total.
    """
    from Fix.variaveis import PjeApiClient, session_from_driver
    from bianca.config import URL_PJE_BASE

    logger.info("[DOMICILIO_ELETRONICO] === INICIANDO DOM ENGINE (API) ===")

    try:
        sess, base_url = session_from_driver(driver)
    except Exception as e:
        return {"sucesso": False, "erro": f"session_from_driver: {e}"}

    client = PjeApiClient(sess, base_url)

    # Tentar reutilizar lista do dia (evita re-fetch lento da API)
    pendentes = _cache_dom_carregar_pendentes()
    if pendentes is not None:
        logger.info("[DOMICILIO_ELETRONICO][API] Reutilizando cache do dia (%d processos pendentes)", len(pendentes))
        processos = [
            {
                "id": p["id"],
                "numeroProcesso": p["numero"],
                # Preserva a data para decidir o PEC pelo dia da audiencia
                "dataProximaAudiencia": p.get("dataProximaAudiencia"),
            }
            for p in pendentes
        ]
    else:
        logger.info(
            "[DOMICILIO_ELETRONICO][API] Buscando processos (conhecimento + chips DOM + audiencia)..."
        )
        processos = client.buscar_processos_conhecimento_dom()
        if processos:
            _cache_dom_salvar_lista(processos)

    if not processos:
        logger.info("[DOMICILIO_ELETRONICO][API] Nenhum processo encontrado pela API")
        return {"sucesso": True, "processados": 0, "total": 0}

    # Filtrar processos com ata de audiencia na timeline (nao entram na lista)
    logger.info("[DOMICILIO_ELETRONICO][API] Filtrando processos com ata de audiencia...")
    sem_ata = []
    for _p in processos:
        _pid = str(_p.get("id", ""))
        _num = _p.get("numeroProcesso") or _p.get("numero") or _pid
        tem_ata = _pid and _tem_ata_audiencia(_pid, driver)
        _p["temAta"] = tem_ata  # Guardar para uso posterior
        if tem_ata:
            logger.info("[DOMICILIO_ELETRONICO][API] Excluido da lista (ata de audiencia): %s", _num)
        else:
            sem_ata.append(_p)
    logger.info(
        "[DOMICILIO_ELETRONICO][API] %d processos apos filtro de ata (%d removidos)",
        len(sem_ata), len(processos) - len(sem_ata),
    )
    processos = sem_ata

    # Enriquecer cada processo com campo temAudiencia (necessário para determinar bucket)
    for proc in processos:
        proc_id = str(proc.get("id", ""))
        proc["temAudiencia"] = True  # Por padrão True (API retorna processos com chips 274/275/302)

    # Separar processos por bucket e exibir pré-execução
    bucket1_procs = []
    bucket2_procs = []
    for proc in processos:
        bucket = _determinar_bucket(proc.get("temAudiencia", True), proc.get("temAta", False))
        if bucket == "bucket1":
            bucket1_procs.append(proc)
        else:
            bucket2_procs.append(proc)

    logger.info("[DOMICILIO_ELETRONICO] === PRÉ-PROCESSAMENTO ===")
    logger.info("[DOMICILIO_ELETRONICO] Bucket1 (sem aud. OU aud+ata):   %d processos", len(bucket1_procs))
    for proc in bucket1_procs:
        num = proc.get("numeroProcesso") or proc.get("numero") or proc.get("id")
        logger.info("[DOMICILIO_ELETRONICO]   - %s", num)
    logger.info("[DOMICILIO_ELETRONICO] Bucket2 (aud sem ata):         %d processos", len(bucket2_procs))
    for proc in bucket2_procs:
        num = proc.get("numeroProcesso") or proc.get("numero") or proc.get("id")
        logger.info("[DOMICILIO_ELETRONICO]   - %s", num)
    logger.info("[DOMICILIO_ELETRONICO] Total: %d processos", len(processos))

    if not processos:
        logger.info("[DOMICILIO_ELETRONICO][API] Nenhum processo restante apos filtro de ata")
        return {"sucesso": True, "processados": 0, "total": 0}

    logger.info("[DOMICILIO_ELETRONICO][API] %d processos a processar", len(processos))

    handle_principal = getattr(driver, "current_window_handle", None)
    erros = 0
    total = len(processos)
    
    # Contadores por bucket
    bucket1_processados = 0
    bucket2_processados = 0
    bucket1_erros = 0
    bucket2_erros = 0

    for idx, proc in enumerate(processos, 1):
        proc_id = str(proc.get("id", ""))
        numero = proc.get("numeroProcesso") or proc.get("numero") or proc_id

        if not proc_id:
            logger.warning("[DOMICILIO_ELETRONICO][API] Processo sem id, pulando")
            erros += 1
            continue

        logger.info("[DOMICILIO_ELETRONICO][API] %d/%d: %s (id=%s)", idx, total, numero, proc_id)

        try:
            # Fechar abas extras
            for h in _obter_abas(driver):
                if handle_principal and h != handle_principal:
                    try:
                        if hasattr(driver, "switch_to"):
                            driver.switch_to.window(h)
                        if hasattr(driver, "close"):
                            driver.close()
                    except Exception:
                        pass
            if handle_principal and hasattr(driver, "switch_to"):
                driver.switch_to.window(handle_principal)

            # Navegar direto para detalhe via id interno
            url = f"{URL_PJE_BASE}/processo/{proc_id}/detalhe"
            if hasattr(driver, "get"):
                driver.get(url)
            elif hasattr(driver, "page") and hasattr(driver.page, "goto"):
                driver.page.goto(url)
            espera.ate_aparecer(
                driver, "pje-cabecalho-processo,pje-timeline", teto=15
            )

            _verificar_acesso_negado(driver, f"dom_api_{numero}")

            # Extrair tipo do processo a partir do cabecalho renderizado
            tipo_processo = "ATOrd"
            try:
                tipo_js = _executar_js(
                    driver,
                    """
                    var cab = document.querySelector('pje-cabecalho-processo');
                    if (cab) {
                        var spans = cab.querySelectorAll(
                            'pje-descricao-processo span.align-end.ng-star-inserted'
                        );
                        for (var i = 0; i < spans.length; i++) {
                            var t = (spans[i].innerText || spans[i].textContent || '').trim();
                            if (t && (t.includes('ATOrd') || t.includes('ATSum') || t.includes('ACum'))) {
                                return t;
                            }
                        }
                    }
                    return '';
                    """
                )
                if tipo_js:
                    tipo_processo = str(tipo_js).strip()
                    logger.info(
                        "[DOMICILIO_ELETRONICO][API] Tipo identificado: %s para %s",
                        tipo_processo, numero,
                    )
            except Exception as e_tipo:
                logger.warning(
                    "[DOMICILIO_ELETRONICO][API] Erro extraindo tipo para %s: %s, usando ATOrd",
                    numero, e_tipo,
                )

            # Executar callback apropriado baseado em bucket
            tem_audiencia = proc.get("temAudiencia", True)
            tem_ata = proc.get("temAta", False)
            bucket = _determinar_bucket(tem_audiencia, tem_ata)
            driver._numero_processo_lista = numero
            
            if bucket == "bucket1":
                logger.info("[DOMICILIO_ELETRONICO][API] Roteando para bucket1: %s", numero)
                ok = callback_bucket1(driver, tipo_processo)
                if ok:
                    bucket1_processados += 1
                else:
                    bucket1_erros += 1
            else:
                logger.info("[DOMICILIO_ELETRONICO][API] Roteando para bucket2: %s", numero)
                ok = callback_bucket2(driver, tipo_processo, processo_info=proc)
                if ok:
                    bucket2_processados += 1
                else:
                    bucket2_erros += 1

            if ok:
                logger.info("[DOMICILIO_ELETRONICO][API] OK: %s (%s)", numero, tipo_processo)
                _cache_dom_marcar(numero, sucesso=True)
            else:
                erros += 1
                logger.error("[DOMICILIO_ELETRONICO][API] Falha callback: %s", numero)
                _cache_dom_marcar(numero, sucesso=False)

        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                raise
            erros += 1
            logger.error("[DOMICILIO_ELETRONICO][API] Erro em %s: %s", numero, e)

        espera.assentar(driver, 1.25)

    logger.info(
        "[DOMICILIO_ELETRONICO][API] Concluido: %d OK, %d erros (total %d)",
        total - erros, erros, total,
    )
    
    # Logging detalhado por bucket
    logger.info("[DOMICILIO_ELETRONICO] === RESUMO POR BUCKET ===")
    logger.info("[DOMICILIO_ELETRONICO] Bucket1: %d processados, %d erros", bucket1_processados, bucket1_erros)
    logger.info("[DOMICILIO_ELETRONICO] Bucket2: %d processados, %d erros", bucket2_processados, bucket2_erros)
    logger.info("[DOMICILIO_ELETRONICO] TOTAL: %d processados, %d erros (total %d)", 
                total - erros, erros, total)
    
    return {
        "sucesso": erros == 0,
        "processados": total - erros,
        "total": total,
        "bucket1_processados": bucket1_processados,
        "bucket1_erros": bucket1_erros,
        "bucket2_processados": bucket2_processados,
        "bucket2_erros": bucket2_erros,
    }
