# -*- coding: utf-8 -*-
"""Prazo P2B — etapa pós-xs1: CPcumprir (processos na tarefa 'Iniciar Execução').

Sequência por processo:
1. API lista os processos atualmente na tarefa 'Iniciar Execução'
   (via PATCH /pje-comum-api/api/agrupamentotarefas/10/processos — mesma lógica
   rápida de bianca/triagem, com fallback Playwright fetch e diagnóstico completo).
2. Para cada processo (aberto em /detalhe pelo Fix.motor_fluxo):
   - Abre a tarefa em nova aba, clica em 'Iniciar execução' e fecha a aba da tarefa.
   - De volta em /detalhe (recarregado com a nova tarefa ativa):
     a) criar_gigs('1', '', 'xs1')
     b) criar_gigs('1', '', 'xs pec cp')
     c) ato_cp1(driver)
"""

import logging
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Optional

from Fix import espera
from Fix.abas import fechar_abas_extras
from Fix.browser_suporte import abrir_url_nova_aba
from Fix.core import aguardar_renderizacao_nativa, garantir_carregamento_pagina, safe_click_no_scroll
from Fix.motor_fluxo import FluxoSpec, executar_fluxo_lote, extrair_id_numero
from Fix.variaveis import url_processo_detalhe
from Prazo.p2b_gateway import SessaoExpiradaError, _criar_api_client
from utilitarios_processamento import resultado_falha, resultado_ok

logger = logging.getLogger(__name__)

TAREFA_INICIAR_EXECUCAO = "Iniciar Execução"
AGRUPAMENTO_NOVOS_PROCESSOS = 10
GIGS_XS1_DIAS = "1"
GIGS_XS1_RESPONSAVEL = ""
GIGS_XS1_OBSERVACAO = "xs1"
GIGS_CP_DIAS = "1"
GIGS_CP_RESPONSAVEL = ""
GIGS_CP_OBSERVACAO = "xs pec cp"

_SEL_BTN_INICIAR_EXEC = "button[aria-label='Iniciar execução'], button[aria-label='Iniciar execucao']"
_SEL_TAREFA_PRONTA = (
    "pje-cabecalho-tarefa h1.titulo-tarefa, pje-cabecalho-tarefa h1, "
    "nav.container-botoes button, pje-botoes-transicao button"
)
_SEL_DETALHE_PRONTO = "pje-cabecalho-processo,pje-timeline"

_JS_FETCH_AGRUPAMENTO = """async ({agrupamentoId, tamPag, maxPags}) => {
    const base = location.origin;
    const path = (agrupamentoId === 'todos' || agrupamentoId == null)
        ? '/pje-comum-api/api/agrupamentotarefas/processos/todos'
        : `/pje-comum-api/api/agrupamentotarefas/${agrupamentoId}/processos`;
    const url = base + path;
    const xsrfCookie = document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.toLowerCase().startsWith('xsrf-token='));
    const xsrf = xsrfCookie ? decodeURIComponent(xsrfCookie.split('=').slice(1).join('=')) : '';

    const normalizar = (d) => {
        if (!d) return [];
        if (Array.isArray(d)) return d;
        for (const k of ['resultado', 'content', 'data', 'conteudo', 'items', 'processos']) {
            if (Array.isArray(d[k])) return d[k];
        }
        return [];
    };

    const todos = [];
    for (let pg = 1; pg <= maxPags; pg++) {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 20000);
        try {
            const r = await window.fetch(url, {
                method: 'PATCH',
                credentials: 'include',
                signal: ctrl.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Grau-Instancia': '1',
                    'X-XSRF-TOKEN': xsrf
                },
                body: JSON.stringify({
                    pagina: pg, tamanhoPagina: tamPag,
                    subCaixa: null, tipoAtividade: null, processos: null,
                    nomeConclusoMagistrado: null, usuarioResponsavel: null,
                    faseProcessualString: null, numeroProcesso: null,
                    juizoDigital: null
                })
            });
            clearTimeout(timer);
            if (!r.ok) {
                const txt = await r.text().catch(() => '');
                return { ok: false, status: r.status, erro: txt.slice(0, 300), resultado: todos, pagina: pg, path };
            }
            const data = await r.json();
            const lista = normalizar(data);
            if (!lista.length) {
                return { ok: true, status: r.status, resultado: todos, total: data.totalRegistros || todos.length, paginas: pg, path };
            }
            todos.push(...lista);
            const totalPags = data.qtdPaginas || data.totalPaginas || 1;
            if (pg >= totalPags || lista.length < tamPag) {
                return { ok: true, status: r.status, resultado: todos, total: data.totalRegistros || todos.length, paginas: pg, path };
            }
        } catch (e) {
            clearTimeout(timer);
            return { ok: false, status: 0, erro: String(e && e.message || e), resultado: todos, pagina: pg, path };
        }
    }
    return { ok: true, status: 200, resultado: todos, aviso: 'limite_paginas', paginas: maxPags, path };
}"""


def _norm_tarefa(txt: Any) -> str:
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def _extrair_nome_tarefa(item: Dict[str, Any]) -> str:
    val = item.get("nomeTarefa") or item.get("descricaoTarefa") or item.get("tarefa")
    if isinstance(val, dict):
        val = val.get("nome") or val.get("descricao") or val.get("nomeTarefa") or ""
    return str(val or "").strip()


def _filtrar_por_tarefa(itens: List[Dict[str, Any]], nome_tarefa: str) -> List[Dict[str, Any]]:
    alvo = _norm_tarefa(nome_tarefa)
    return [i for i in itens if isinstance(i, dict) and _norm_tarefa(_extrair_nome_tarefa(i)) == alvo]


def _buscar_via_browser_fetch(driver: Any, agrupamento_id: Any = AGRUPAMENTO_NOVOS_PROCESSOS,
                              tamanho_pagina: int = 100, max_paginas: int = 50) -> Optional[Dict[str, Any]]:
    """Fallback Playwright-nativo usando fetch() no contexto da página (mesmo padrão de bianca/triagem)."""
    page = getattr(driver, "page", None)
    if page is None or not hasattr(page, "evaluate"):
        return None
    try:
        return page.evaluate(
            _JS_FETCH_AGRUPAMENTO,
            {"agrupamentoId": agrupamento_id, "tamPag": tamanho_pagina, "maxPags": max_paginas},
        )
    except Exception as e:
        logger.warning("[CPCUMPRIR][API] Fallback fetch no browser falhou: %s", e)
        return None


def _diagnosticar_agrupamentos_disponiveis(client: Any) -> List[Dict[str, Any]]:
    """Consulta rápida GET /pje-comum-api/api/agrupamentotarefas para descobrir IDs se 10 não tiver a tarefa."""
    res = client.gateway_get("/pje-comum-api/api/agrupamentotarefas", timeout=(5, 10))
    if not res.get("ok"):
        logger.info("[CPCUMPRIR][API] GET /agrupamentotarefas HTTP=%s (%s)", res.get("status"), res.get("error"))
        return []
    dados = res.get("data")
    lista = dados if isinstance(dados, list) else (dados.get("resultado") if isinstance(dados, dict) else [])
    if not isinstance(lista, list):
        return []
    resumo = [
        {
            "id": a.get("id") or a.get("idAgrupamento"),
            "nome": a.get("nome") or a.get("descricao") or a.get("titulo"),
            "qtd": a.get("quantidadeProcessos") or a.get("totalProcessos") or a.get("total"),
        }
        for a in lista if isinstance(a, dict)
    ]
    logger.info("[CPCUMPRIR][API] Agrupamentos do Painel Global: %s", resumo)
    return resumo


def _obter_id_tarefa_atual_api(driver: Any, id_processo: Any) -> Optional[str]:
    """Obtém o idTarefa mais recente do processo via API sem navegar o browser."""
    client = _criar_api_client(driver)
    res = client.gateway_get(
        f"/pje-comum-api/api/processos/id/{id_processo}/tarefas",
        params={"maisRecente": "true"},
        timeout=10,
    )
    if not res.get("ok"):
        if res.get("status") == 401:
            raise SessaoExpiradaError("API retornou 401 ao consultar tarefa do processo")
        logger.warning("[CPCUMPRIR] Falha ao consultar tarefa do processo %s: %s", id_processo, res.get("error"))
        return None

    dados = res.get("data")
    registro = dados[0] if (isinstance(dados, list) and dados) else (dados if isinstance(dados, dict) else None)
    if not isinstance(registro, dict):
        return None
    id_tarefa = registro.get("idTarefa") or registro.get("id")
    return str(id_tarefa) if id_tarefa else None


def _clicar_iniciar_execucao(driver: Any, timeout: int = 10) -> bool:
    """Clica no botão 'Iniciar execução' na aba da tarefa e aguarda a transição."""
    try:
        aguardar_renderizacao_nativa(driver, _SEL_BTN_INICIAR_EXEC, modo="aparecer", timeout=min(8, timeout))
    except Exception:
        pass

    clicou = False
    btn = espera.elemento(driver, _SEL_BTN_INICIAR_EXEC, teto=min(6, timeout))
    if btn:
        is_disabled = (
            btn.get_attribute("disabled") is not None
            or "mat-button-disabled" in (btn.get_attribute("class") or "")
            or getattr(btn, "is_enabled", lambda: True)() is False
        )
        if not is_disabled:
            clicou = bool(safe_click_no_scroll(driver, btn))
        else:
            logger.warning("[CPCUMPRIR] Botão 'Iniciar execução' encontrado, porém inativo")
            return False

    if not clicou:
        from atos.movimentos_navegacao import clicar_botao_por_texto
        clicou = bool(clicar_botao_por_texto(driver, "Iniciar execução", timeout=min(5, timeout), debug=True))

    if not clicou:
        logger.warning("[CPCUMPRIR] Botão 'Iniciar execução' não encontrado na tarefa")
        return False

    espera.ate_sumir(driver, _SEL_BTN_INICIAR_EXEC, teto=6.0)
    espera.assentar(driver, 0.8, motivo="[CPCUMPRIR] transição pós-Iniciar execução")
    return True


def _abrir_tarefa_iniciar_execucao_e_fechar_aba(driver: Any, id_processo: Any, timeout: int = 10) -> bool:
    """Passo 2: abre tarefa em nova aba, clica em 'Iniciar execução' e fecha a aba voltando para /detalhe."""
    aba_detalhe = getattr(driver, "current_window_handle", None)
    id_tarefa = _obter_id_tarefa_atual_api(driver, id_processo)
    if not id_tarefa:
        logger.warning("[CPCUMPRIR] idTarefa não encontrado para processo %s", id_processo)
        return False

    client = _criar_api_client(driver)
    url_tarefa = f"https://{client.trt_host}/pjekz/processo/{id_processo}/tarefa/{id_tarefa}"

    try:
        nova_aba = abrir_url_nova_aba(driver, url_tarefa, timeout=float(timeout))
        if not nova_aba:
            logger.warning("[CPCUMPRIR] Não foi possível abrir nova aba da tarefa %s", url_tarefa)
            return False

        garantir_carregamento_pagina(
            driver,
            seletor_esperado=_SEL_TAREFA_PRONTA,
            timeout_refresh=float(min(10, timeout)),
            url_alvo=url_tarefa,
        )
        return _clicar_iniciar_execucao(driver, timeout=timeout)
    finally:
        if aba_detalhe is not None:
            try:
                fechar_abas_extras(driver, aba_detalhe)
            except Exception as e:
                logger.warning("[CPCUMPRIR] Erro ao fechar aba da tarefa: %s", e)
            try:
                if getattr(driver, "current_window_handle", None) != aba_detalhe:
                    driver.switch_to.window(aba_detalhe)
            except Exception:
                pass


def listar_processos_iniciar_execucao(
    driver: Any,
    tamanho_pagina: int = 100,
    agrupamento_id: Any = AGRUPAMENTO_NOVOS_PROCESSOS,
) -> List[Dict[str, Any]]:
    """Passo 1: consulta via API os processos atualmente na tarefa 'Iniciar Execução'.

    Usa PATCH /pje-comum-api/api/agrupamentotarefas/10/processos (mesma fila rápida de bianca/triagem).
    Se a chamada via requests.Session falhar, tenta fallback fetch() no browser (Playwright).
    """
    logger.info(
        "[CPCUMPRIR][API] Consultando tarefa '%s' (agrupamento=%s, url_atual=%s)...",
        TAREFA_INICIAR_EXECUCAO, agrupamento_id, getattr(driver, "current_url", ""),
    )
    client = _criar_api_client(driver)
    try:
        encontrados, diag = client.buscar_processos_por_tarefa(
            TAREFA_INICIAR_EXECUCAO,
            tamanho_pagina=tamanho_pagina,
            agrupamento_id=agrupamento_id,
            max_paginas=50,
            timeout=(10, 20),
            retornar_diagnostico=True,
        )
    except PermissionError as e:
        raise SessaoExpiradaError(str(e)) from e

    logger.info(
        "[CPCUMPRIR][API] Gateway %s -> ok=%s HTTP=%s paginas=%s brutos=%s match=%d | tarefas=%s",
        diag.get("path"), diag.get("ok"), diag.get("status"),
        diag.get("paginas"), diag.get("total_varrido"), len(encontrados), diag.get("tarefas"),
    )

    if not diag.get("ok"):
        logger.warning(
            "[CPCUMPRIR][API] Gateway falhou (%s) — tentando fallback fetch() no browser (padrão bianca/triagem)...",
            diag.get("erro"),
        )
        res_js = _buscar_via_browser_fetch(driver, agrupamento_id=agrupamento_id, tamanho_pagina=tamanho_pagina)
        if res_js is None:
            logger.error("[CPCUMPRIR][API] Fallback fetch indisponível (driver sem page.evaluate)")
            return []
        if res_js.get("status") == 401:
            raise SessaoExpiradaError("sessao_expirada_401 (browser fetch)")
        if not res_js.get("ok"):
            logger.error(
                "[CPCUMPRIR][API] Fallback fetch falhou em %s: HTTP=%s erro=%s",
                res_js.get("path"), res_js.get("status"), res_js.get("erro"),
            )
            return []
        brutos = res_js.get("resultado") or []
        tarefas_js = dict(Counter(_extrair_nome_tarefa(i) for i in brutos if isinstance(i, dict)).most_common(15))
        encontrados = _filtrar_por_tarefa(brutos, TAREFA_INICIAR_EXECUCAO)
        logger.info(
            "[CPCUMPRIR][API] Browser fetch %s -> paginas=%s brutos=%d match=%d | tarefas=%s",
            res_js.get("path"), res_js.get("paginas"), len(brutos), len(encontrados), tarefas_js,
        )

    if not encontrados and agrupamento_id == AGRUPAMENTO_NOVOS_PROCESSOS:
        agrupamentos = _diagnosticar_agrupamentos_disponiveis(client)
        alvo_norm = _norm_tarefa(TAREFA_INICIAR_EXECUCAO)
        for agr in agrupamentos:
            agr_id = agr.get("id")
            agr_nome = _norm_tarefa(agr.get("nome"))
            if agr_id and str(agr_id) != str(agrupamento_id) and (
                alvo_norm in agr_nome or "iniciar execucao" in agr_nome
            ):
                logger.info("[CPCUMPRIR][API] Testando agrupamento dedicado id=%s (%s)...", agr_id, agr.get("nome"))
                extras, diag2 = client.buscar_processos_por_tarefa(
                    TAREFA_INICIAR_EXECUCAO,
                    tamanho_pagina=tamanho_pagina,
                    agrupamento_id=agr_id,
                    max_paginas=50,
                    timeout=(10, 20),
                    retornar_diagnostico=True,
                )
                logger.info(
                    "[CPCUMPRIR][API] Agrupamento %s -> ok=%s brutos=%s match=%d | tarefas=%s",
                    agr_id, diag2.get("ok"), diag2.get("total_varrido"), len(extras), diag2.get("tarefas"),
                )
                if extras:
                    encontrados = extras
                    break

    return encontrados


def _recarregar_detalhe(driver: Any, id_processo: Any) -> bool:
    """Recarrega /detalhe após iniciar execução para atualizar o botão de tarefa ativa."""
    url_detalhe = url_processo_detalhe(id_processo)
    driver.get(url_detalhe)
    return bool(
        garantir_carregamento_pagina(
            driver,
            seletor_esperado=_SEL_DETALHE_PRONTO,
            timeout_refresh=5.0,
            url_alvo=url_detalhe,
        )
    )


def _executar_processo_cpcumprir(driver: Any, item: Dict[str, Any]) -> Dict[str, Any]:
    """Executa passos 2 e 3 para um único processo já aberto em /detalhe."""
    from Fix.extracao import criar_gigs
    from atos.wrappers_ato import ato_cp1

    id_processo = item.get("id")
    numero = item.get("numero") or str(id_processo)

    logger.info("[CPCUMPRIR] %s — passo 2: abrir tarefa e clicar 'Iniciar execução'", numero)
    if not _abrir_tarefa_iniciar_execucao_e_fechar_aba(driver, id_processo, timeout=10):
        return resultado_falha("falha_iniciar_execucao")

    logger.info("[CPCUMPRIR] %s — passo 3: recarregando /detalhe", numero)
    if not _recarregar_detalhe(driver, id_processo):
        return resultado_falha("detalhe_nao_recarregou")

    logger.info("[CPCUMPRIR] %s — passo 3a: criar_gigs(1, '', 'xs1')", numero)
    gigs_xs1_ok = criar_gigs(
        driver,
        dias_uteis=GIGS_XS1_DIAS,
        responsavel=GIGS_XS1_RESPONSAVEL,
        observacao=GIGS_XS1_OBSERVACAO,
    )
    if not gigs_xs1_ok:
        logger.warning("[CPCUMPRIR] criar_gigs xs1 retornou False para %s", numero)
        return resultado_falha("falha_criar_gigs_xs1")

    logger.info("[CPCUMPRIR] %s — passo 3b: criar_gigs(1, '', 'xs pec cp')", numero)
    gigs_ok = criar_gigs(
        driver,
        dias_uteis=GIGS_CP_DIAS,
        responsavel=GIGS_CP_RESPONSAVEL,
        observacao=GIGS_CP_OBSERVACAO,
    )
    if not gigs_ok:
        logger.warning("[CPCUMPRIR] criar_gigs retornou False para %s", numero)
        return resultado_falha("falha_criar_gigs")

    logger.info("[CPCUMPRIR] %s — passo 3c: ato_cp1", numero)
    res_ato = ato_cp1(driver)
    ato_ok = res_ato[0] if isinstance(res_ato, tuple) else bool(res_ato)
    if not ato_ok:
        logger.warning("[CPCUMPRIR] ato_cp1 retornou falha (%s) para %s", res_ato, numero)
        return resultado_falha("falha_ato_cp1")

    logger.info("[CPCUMPRIR] Processo %s concluído com sucesso", numero)
    return resultado_ok()


def executar_cpcumprir(
    driver: Any,
    tamanho_pagina: int = 100,
    max_processos: int = 0,
    processos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Executa o lote CPcumprir (processos da tarefa 'Iniciar Execução') sobre Fix.motor_fluxo."""
    try:
        lista_api = processos if processos is not None else listar_processos_iniciar_execucao(
            driver, tamanho_pagina=tamanho_pagina
        )
    except SessaoExpiradaError as e:
        logger.warning("[CPCUMPRIR] Sessão expirada (401) ao listar processos: %s", e)
        return {
            "sucesso": False,
            "total": 0,
            "processados": 0,
            "falhas": [],
            "critical_stop": True,
            "critical_reason": "sessao_expirada_401",
        }

    total_encontrado = len(lista_api)
    if total_encontrado == 0:
        logger.info("[CPCUMPRIR] Nenhum processo encontrado na tarefa '%s'", TAREFA_INICIAR_EXECUCAO)
        return {"sucesso": True, "total": 0, "processados": 0, "falhas": []}

    logger.info("[CPCUMPRIR] Processos na tarefa '%s': %d", TAREFA_INICIAR_EXECUCAO, total_encontrado)
    itens: List[Dict[str, Any]] = []
    for idx, raw in enumerate(lista_api, start=1):
        if max_processos and idx > max_processos:
            break
        id_processo, numero = extrair_id_numero(raw)
        if not id_processo:
            logger.warning("[CPCUMPRIR] Item %d sem id_processo, pulando (numero=%s)", idx, numero)
            continue
        itens.append({"id": id_processo, "numero": numero, "chave": numero or str(id_processo)})

    logger.info("[CPCUMPRIR] Processos a executar: %s", [p.get("numero") for p in itens])

    def _executar(drv: Any, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return _executar_processo_cpcumprir(drv, item)
        except SessaoExpiradaError as e:
            logger.warning("[CPCUMPRIR] Sessão expirada (401) em %s: %s", item.get("numero"), e)
            return resultado_falha("sessao_expirada_401", critical=True)

    spec = FluxoSpec(
        nome="cpcumprir",
        tag_log="[CPCUMPRIR]",
        executar=_executar,
        seletor_pronto=_SEL_DETALHE_PRONTO,
        seletor_pos_load="#botao-menu, i.fa-bars",
        usar_garantir_carregamento=True,
        fechar_abas_ao_final=True,
        on_critical_exception=lambda exc: isinstance(exc, SessaoExpiradaError),
    )
    res = executar_fluxo_lote(driver, itens, spec)
    return {
        "sucesso": res["sucesso"],
        "total": total_encontrado,
        "processados": res["processados"],
        "falhas": res["falhas"],
        "critical_stop": res["critical_stop"],
        "critical_reason": res["critical_reason"],
    }
