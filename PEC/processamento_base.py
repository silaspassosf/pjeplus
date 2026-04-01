# =====================================================================
# HELPERS DE DIAGNÓSTICO – API GIGS + BUCKETS PEC
# Definidas em escopo de módulo para permitir importação direta.
# =====================================================================

from typing import Any

from Fix.core import aguardar_e_clicar, esperar_elemento
from Fix.extracao import extrair_dados_processo, abrir_detalhes_processo, trocar_para_nova_aba, reindexar_linha
from atos import pec_excluiargos
from .executor import executar_acao
from .api_client import AtividadePEC, PECAPIClient
from .classificador import PECClassificador
from .executor_individual import PECExecutorIndividual
from .orquestrador import PECOrquestrador, executar_fluxo_novo_simplificado

_pec_modules_cache = {
    'aguardar_e_clicar': aguardar_e_clicar,
    'esperar_elemento': esperar_elemento,
    'extrair_dados_processo': extrair_dados_processo,
    'abrir_detalhes_processo': abrir_detalhes_processo,
    'trocar_para_nova_aba': trocar_para_nova_aba,
    'reindexar_linha': reindexar_linha,
    'pec_excluiargos': pec_excluiargos,
}


def _lazy_import_pec():
    """Compatibilidade: retorna cache de módulos PEC (sem lazy import)."""
    return _pec_modules_cache


def _acaonome_para_bucket_pec(acaonome: str) -> str:
    """
    Lógica de classificação alinhada com agruparembuckets de produção.
    Fonte: PEC/processamento_indexacao.py — agruparembuckets
    """
    SISBAJUD = {
        "minuta_bloqueio", "minuta_bloqueio_60",
        "processar_ordem_sisbajud", "processar_ordem_sisbajud_wrapper",
    }
    CARTA = {"carta", "analisar_documentos_pos_carta"}
    SOB   = {"mov_aud"}
    SOBREST = {"def_sob", "def_chip", "mov_sob"}
    COMUNICACOES = {
        "pec_sigilo", "pec_cpgeral", "pec_excluiargos", "pec_bloqueio",
        "pec_decisao", "pec_editaldec", "pec_editalidpj", "pec_ord", "pec_sum",
        "pec_editalaud", "ato_citacao", "ato_intimacao",
        "wrapper_pec_ord_com_domicilio", "wrapper_pec_sum_com_domicilio",
    }

    name = (acaonome or "").lower()

    if name in SISBAJUD:
        return "sisbajud"
    if name in CARTA:
        return "carta"
    if name in SOB:
        return "sob"
    if name in SOBREST:
        return "sobrestamento"
    if name in COMUNICACOES or name.startswith("pec_") or "wrapper" in name:
        return "comunicacoes"
    return "outros"


def _resolver_acaonome(acaofunc: Any) -> str:
    """
    Retorna nome legível para a ação.
    Aceita: callable, lista de callables/tuplas, string.
    """
    if not acaofunc and acaofunc != 0:
        return ""
    if isinstance(acaofunc, (list, tuple)):
        nomes = []
        for item in acaofunc:
            if isinstance(item, tuple) and item:
                item = item[0]
            if callable(item):
                nomes.append(getattr(item, "__name__", str(item)))
        return "+".join(nomes) if nomes else str(acaofunc)
    if callable(acaofunc):
        return getattr(acaofunc, "__name__", str(acaofunc))
    return str(acaofunc)


def _gigs_vencidos_via_js(driver, tamanho_pagina: int = 100) -> list:
    """
    Busca GIGS vencidos via execute_script — usa cookies e XSRF já presentes
    na sessão autenticada do browser. Retorna lista bruta de atividades.

    Endpoint real (confirmado em produção TRT2):
        GET /pje-gigs-api/api/relatorioatividades/
            ?filtrarVencidas=true&ordenacaoCrescente=true
            &filtrarPorDestinatario=false&filtrarPorLocalizacao=false
            &pagina=N&tamanhoPagina=N
    """
    JS = f'''
const callback = arguments[0];

const rawCookie = document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.toLowerCase().startsWith('xsrf-token='));
const xsrf = rawCookie ? rawCookie.split('=').slice(1).join('=') : null;

if (!xsrf) {{
    callback({{
        erro: 'XSRF_NOT_FOUND',
        href: location.href,
        cookieCount: document.cookie.split(';').filter(c => c.trim()).length,
        resultado: []
    }});
    return;
}}

const base = location.origin;
const params = 'filtrarVencidas=true&ordenacaoCrescente=true'
             + '&filtrarPorDestinatario=false&filtrarPorLocalizacao=false';
const hdrs = {{
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-XSRF-TOKEN': xsrf
}};

(async () => {{
    const getPage = async (pagina) => {{
        const url = `${{base}}/pje-gigs-api/api/relatorioatividades/?${{params}}&pagina=${{pagina}}&tamanhoPagina={tamanho_pagina}`;
        const r = await fetch(url, {{ credentials: 'include', headers: hdrs }});
        if (!r.ok) return {{ erro: r.status, url: url, resultado: [] }};
        return r.json();
    }};
    try {{
        const p1 = await getPage(1);
        if (p1.erro) {{
            callback({{ erro: p1.erro, url: p1.url, xsrfLen: xsrf.length, resultado: [] }});
            return;
        }}
        let todos = [...(p1.resultado || [])];
        const total = p1.qtdPaginas || 1;
        if (total > 1) {{
            const rest = await Promise.all(
                Array.from({{ length: total - 1 }}, (_, i) => getPage(i + 2))
            );
            rest.forEach(p => todos.push(...(p.resultado || [])));
        }}
        callback({{ qtdPaginas: total, totalRegistros: p1.totalRegistros, resultado: todos }});
    }} catch(e) {{
        callback({{ erro: e.message, resultado: [] }});
    }}
}})();
'''

    try:
        driver.set_script_timeout(60)
        resultado = driver.execute_async_script(JS)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass

    if not resultado or resultado.get("erro"):
        erro = (resultado or {}).get("erro", "sem_resposta")
        if erro == "XSRF_NOT_FOUND":
            print(
                f"PEC_GIGS_JS: ❌ XSRF não encontrado em document.cookie — "
                f"cookies={resultado.get('cookieCount', 0)}, "
                f"href={resultado.get('href', '?')}"
            )
            print("PEC_GIGS_JS: ⚠  Certifique-se de que o driver está em uma página PJe autenticada.")
        else:
            print(
                f"PEC_GIGS_JS: ❌ HTTP {erro} — "
                f"url={resultado.get('url', '?')} "
                f"xsrfLen={resultado.get('xsrfLen', '?')}"
            )
        return []

    total = resultado.get("totalRegistros", 0)
    dados = resultado.get("resultado", [])
    print(
        f"PEC_GIGS_JS: ✅ {len(dados)}/{total} atividades carregadas "
        f"({resultado.get('qtdPaginas', 1)} página(s))"
    )
    return dados


def _extrair_campos_atividade(ativ: dict) -> dict:
    """Normaliza campos aninhados da resposta real de relatorioatividades/."""
    proc = ativ.get("processo") or {}
    tipo = ativ.get("tipoAtividade") or {}
    return {
        "id": ativ.get("id"),
        "idProcesso": ativ.get("idProcesso") or proc.get("id"),
        "numero": proc.get("numero") or proc.get("numeroProcesso") or "",
        "tipoGigs": tipo.get("descricao") or tipo.get("nome") or "",
        "observacao": (ativ.get("observacao") or "").strip(),
        "status": (ativ.get("statusAtividade") or "").upper(),
        "dataPrazo": (ativ.get("dataPrazo") or "")[:10],
    }


def testar_api_gigs_e_buckets_pec(
    driver,
    filtrar_concluidos: bool = True,
    tamanho_pagina: int = 100,
) -> dict:
    """
    Busca GIGS vencidos via API REST e agrupa em buckets de execução.

    Estratégia: execute_async_script injeta fetch com cookies da sessão ativa.
    Endpoint real: GET /pje-gigs-api/api/relatorioatividades/
    Campos aninhados: processo.numero, tipoAtividade.descricao

    Uso:
        from PEC.processamento_base import testar_api_gigs_e_buckets_pec
        buckets = testar_api_gigs_e_buckets_pec(driver)
    """
    buckets: dict = {
        "sisbajud":       [],
        "carta":          [],
        "sob":            [],
        "sobrestamento":  [],
        "comunicacoes":   [],
        "outros":         [],
        "sem_acao":       [],
        "sem_observacao": [],
    }
    STATUS_IGNORADOS = ("CONCLU", "CANCELA")

    atividades_raw = _gigs_vencidos_via_js(driver, tamanho_pagina)
    if not atividades_raw:
        print("PEC_GIGS: ❌ Nenhuma atividade retornada")
        return buckets

    for ativ_raw in atividades_raw:
        ativ = _extrair_campos_atividade(ativ_raw)
        numero  = ativ["numero"]
        status  = ativ["status"]
        obs_raw = ativ["observacao"]

        if filtrar_concluidos and any(s in status for s in STATUS_IGNORADOS):
            continue

        info = {
            "numero":     numero,
            "observacao": obs_raw,
            "status":     status,
            "dataPrazo":  ativ["dataPrazo"],
            "acao":       "",
        }

        if not obs_raw:
            buckets["sem_observacao"].append(info)
            continue

        acoes = determinar_acoes_por_observacao(obs_raw)
        if not acoes:
            buckets["sem_acao"].append(info)
            continue

        first    = acoes[0] if acoes else None
        acaonome = _resolver_acaonome(first)
        bucket   = _acaonome_para_bucket_pec(acaonome)
        info["acao"] = acaonome
        buckets[bucket].append(info)

    # ── saída formatada ───────────────────────────────────────────────────
    ORDEM = (
        "sisbajud", "carta", "sob", "sobrestamento",
        "comunicacoes", "outros", "sem_observacao"
    )
    total_acionavel = 0
    for nome in ORDEM:
        itens = buckets[nome]
        if not itens:
            continue
        print(f"\n[{nome.upper()}]")
        for p in itens:
            obs = (p["observacao"] or "")[:70]
            print(f"  {p['numero']} - {obs} - {p['acao'] or '—'}")
        total_acionavel += len(itens)

    sem_acao_count  = len(buckets["sem_acao"])
    sem_obs_count   = len(buckets["sem_observacao"])
    total_geral     = total_acionavel + sem_acao_count + sem_obs_count
    print(
        f"\nTotal: {total_geral} GIGS vencidos"
        f" | acionáveis: {total_acionavel}"
        f" | sem regra: {sem_acao_count}"
        f" | sem obs: {sem_obs_count}"
    )

    return buckets
    
def processar_processo_pec_individual(driver):
    from Fix.variaveis import session_from_driver, PjeApiClient, obter_gigs_com_fase
    from PEC.core_navegacao import indexar_processo_atual_gigs
    from PEC.executor import executar_acao_pec

    try:
        # Tentar obter número diretamente da URL atual (evita interface gráfica)
        from urllib.parse import urlparse, parse_qs

        current_url = getattr(driver, 'current_url', '')
        parsed = urlparse(current_url)
        query_params = parse_qs(parsed.query)
        numero_processo = query_params.get('numero', [None])[0] or query_params.get('cnj', [None])[0]
        if not numero_processo:
            print("[PEC_INDIVIDUAL] ❌ Não foi possível extrair número do processo da URL")
            return False

        # API GIGS via PjeApiClient prima pelo uso de dados sem UI
        sess, base_url = session_from_driver(driver, grau=1)
        client = PjeApiClient(sess, base_url)
        gigs_data = obter_gigs_com_fase(client, numero_processo)

        observacao = ''
        if gigs_data and gigs_data.get('atividadesgigs'):
            atividade = gigs_data['atividadesgigs'][0]
            observacao = (atividade.get('observacao') or '').strip()
            print(f"[PEC_INDIVIDUAL] Processo: {numero_processo} | Observação (API): {observacao}")
        else:
            print("[PEC_INDIVIDUAL] [FALLBACK] Usando funções visuais")
            processo_atual = indexar_processo_atual_gigs(driver)
            if not processo_atual:
                print("[PEC_INDIVIDUAL] ❌ Falha ao extrair dados do processo atual")
                return False
            _, observacao = processo_atual
            observacao = (observacao or '').strip()

        if not observacao:
            print(f"[PEC_INDIVIDUAL] ❌ Observação vazia para processo {numero_processo}")
            return False

        acoes = determinar_acoes_por_observacao(observacao)
        acao = acoes[0] if acoes else None
        print(f"[PEC_INDIVIDUAL] Ações determinadas: {[a.__name__ if callable(a) else str(a) for a in acoes]}")

        if acao is None:
            print(f"[PEC_INDIVIDUAL] ⏭️ Pulando processo (ação não definida)")
            return True

        # ...existing code...
    except Exception as e:
        print(f"[PEC_INDIVIDUAL] ❌ Erro no processamento: {e}")
        return False
