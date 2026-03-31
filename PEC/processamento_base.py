# =====================================================================
# HELPERS DE DIAGNÓSTICO – API GIGS + BUCKETS PEC
# Definidas em escopo de módulo para permitir importação direta.
# =====================================================================

from typing import Any

from .regras import determinar_acoes_por_observacao


def _acaonome_para_bucket_pec(acaonome: str) -> str:
    """
    Mesma lógica de classificação usada por indexarecriarbucketsunico.
    Centralizada aqui para não duplicar.
    """
    SISBAJUD = {"minutabloqueio", "minutabloqueio60", "processarordemsisbajud", "processarordemsisbajudwrapper"}
    CARTA = {"carta", "analisardocumentosposcarta"}
    SOB = {"movsob", "defchip", "movaud"}
    SOBREST = {"defsob"}

    name = (acaonome or "").lower()

    if name in SISBAJUD:
        return "sisbajud"
    if name in CARTA:
        return "carta"
    if name in SOB:
        return "sob"
    if name in SOBREST:
        return "sobrestamento"
    if "comunic" in name:
        return "comunicacoes"
    return "outros"


def _resolver_acaonome(acaofunc: Any) -> str:
    """Retorna um nome legível para a ação (aceita callable ou string)."""
    if not acaofunc:
        return ""
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
    JS = """
const callback = arguments[0];
const xsrf = document.cookie.split(';')
  .map(c => c.trim()).find(c => c.toLowerCase().startsWith('xsrf-token='))
  ?.split('=').slice(1).join('=');
const base = location.origin;
const params = 'filtrarVencidas=true&ordenacaoCrescente=true'
             + '&filtrarPorDestinatario=false&filtrarPorLocalizacao=false';
const hdrs = { 'Accept': 'application/json', 'X-XSRF-TOKEN': xsrf };

(async () => {
  const getPage = async (pagina) => {
    const r = await fetch(
      `${base}/pje-gigs-api/api/relatorioatividades/?${params}&pagina=${pagina}&tamanhoPagina=TAMANHO}`,
      { credentials: 'include', headers: hdrs }
    );
    if (!r.ok) return { erro: r.status, resultado: [] };
    return r.json();
  };
  try {
    const p1 = await getPage(1);
    if (p1.erro) { callback({ erro: p1.erro, resultado: [] }); return; }
    let todos = [...(p1.resultado || [])];
    const total = p1.qtdPaginas || 1;
    if (total > 1) {
      const rest = await Promise.all(
        Array.from({ length: total - 1 }, (_, i) => getPage(i + 2))
      );
      rest.forEach(p => todos.push(...(p.resultado || [])));
    }
    callback({ qtdPaginas: total, totalRegistros: p1.totalRegistros, resultado: todos });
  } catch(e) {
    callback({ erro: e.message, resultado: [] });
  }
})();
""".replace("TAMANHO", str(tamanho_pagina))

    resultado = driver.execute_async_script(JS)
    if not resultado or resultado.get("erro"):
        print(f"PEC_GIGS_JS: ❌ erro={resultado}")
        return []
    total = resultado.get("totalRegistros", 0)
    dados = resultado.get("resultado", [])
    print(f"PEC_GIGS_JS: {len(dados)}/{total} atividades carregadas")
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
    Busca GIGS vencidos via API REST sem navegação nem cliques.

    Estratégia: execute_async_script injeta fetch com cookies da sessão ativa.
    Endpoint real: GET /pje-gigs-api/api/relatorioatividades/
    Campos aninhados: processo.numero, tipoAtividade.descricao

    Uso:
        from PEC.processamento_base import testar_api_gigs_e_buckets_pec
        buckets = testar_api_gigs_e_buckets_pec(driver)
    """
    buckets: dict = {
        "sisbajud":      [],
        "carta":         [],
        "sob":           [],
        "sobrestamento": [],
        "comunicacoes":  [],
        "outros":        [],
        "sem_acao":      [],
        "sem_observacao":[],
    }
    STATUS_IGNORADOS = ("CONCLU", "CANCELA")

    atividades_raw = _gigs_vencidos_via_js(driver, tamanho_pagina)
    if not atividades_raw:
        print("PEC_TESTE_API: ❌ Nenhuma atividade retornada")
        return buckets

    for ativ_raw in atividades_raw:
        ativ = _extrair_campos_atividade(ativ_raw)
        numero = ativ["numero"]
        status = ativ["status"]
        obs_raw = ativ["observacao"]
        dataprazo = ativ["dataPrazo"]
        tipo_gigs = ativ["tipoGigs"]

        if filtrar_concluidos and any(s in status for s in STATUS_IGNORADOS):
            continue

        info = {
            "numero":     numero,
            "observacao": obs_raw,
            "status":     status,
            "dataPrazo":  dataprazo,
            "tipoGigs":   tipo_gigs,
        }

        if not obs_raw:
            buckets["sem_observacao"].append(info)
            print(f"PEC_TESTE_API: {numero} → sem observacao (status={status})")
            continue

        acoes = determinar_acoes_por_observacao(obs_raw)
        if not acoes:
            buckets["sem_acao"].append(info)
            print(f"PEC_TESTE_API: {numero} → obs={obs_raw!r} → SEM REGRA")
            continue

        first = acoes[0] if isinstance(acoes, (list, tuple)) and acoes else acoes
        acaonome = _resolver_acaonome(first)
        bucket = _acaonome_para_bucket_pec(acaonome)
        buckets[bucket].append(info)
        print(
            f"PEC_TESTE_API: {numero} → bucket={bucket} "
            f"tipo={tipo_gigs} acao={acaonome} status={status} "
            f"dataPrazo={dataprazo} obs={obs_raw[:80]}"
        )

    print("\nPEC_TESTE_API: ── RESUMO ──")
    total = sum(len(v) for v in buckets.values())
    for nome, itens in buckets.items():
        if not itens:
            continue
        print(f"  {nome.upper():15s} {len(itens):>3} atividades")
        for proc in itens[:3]:
            print(f"    · {proc['numero']} {proc['observacao'][:60]}")
    print(f"  {'TOTAL':15s} {total:>3}")

    return buckets


def processar_processo_pec_individual(driver):
    """
    Callback específico para processar um processo individual no PEC
    Usado pelo sistema centralizado de retry do PJE.PY

    Esta função foca APENAS na lógica específica do PEC,
    sem se preocupar com retry, progresso ou navegação para /detalhe
    """
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

        destinatarios_override = None
        try:
            import re
            m = re.match(r'^(?:pec\s*(?:dec|edital|idpj)\b)\s+(.+)$', observacao.strip(), re.I)
            if m:
                nome_cand = m.group(1).strip()
                nome_cand = re.split(r'[,:\-\(\)]', nome_cand)[0].strip()
                nome_cand = re.sub(r'^(sr\.?|sra\.?|dr\.?|dra\.?|srta\.?|srta)\s+', '', nome_cand, flags=re.I).strip()
                if len(nome_cand) >= 3 and re.search('[A-Za-zÀ-ÖØ-öø-ÿ]', nome_cand):
                    destinatarios_override = {'nome': nome_cand}
                    print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE] Nome extraído para override: '{nome_cand}'")
        except Exception as e_parse:
            print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE][WARN] Falha ao tentar extrair nome da observação: {e_parse}")

        driver_sisb = getattr(driver, '_driver_sisb_compartilhado', None)

        sucesso_acao = executar_acao_pec(
            driver,
            acao,
            numero_processo=numero_processo,
            observacao=observacao,
            debug=True,
            driver_sisb=driver_sisb,
        )

        if sucesso_acao:
            print(f"[PEC_INDIVIDUAL] ✅ Ação executada com sucesso")
            return True
        else:
            print(f"[PEC_INDIVIDUAL] ❌ Falha na execução da ação '{acao}'")
            return False

    except Exception as e:
        print(f"[PEC_INDIVIDUAL] ❌ Erro no processamento: {e}")
        return False
