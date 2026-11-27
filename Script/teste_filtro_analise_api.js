// Script/teste_filtro_analise_api.js
// Filtro via API do PJe (para console / Tampermonkey / cdp_lab):
//   0) Fase Liquidação ou Execução, tarefa Análise (idTarefa 500)
//   1) Sem GIGS (sem atividades abertas)
//   2) Sem comentário
//   3) Sem responsável
//   4) Sem documento não apreciado (peticaoNaoApreciada / isPeticaoNaoApreciada / escaninho)
//   5) Estado da transição "Aguardando prazo" (disponível ou não)
//
// Uso no console do PJe:
//   const res = await window.pjeFiltrarAnaliseLivres();
//   console.table(res.processos);
(function () {
    'use strict';

    const BASE = window.location.origin;
    const FASES_ALVO = ['Liquidação', 'Execução'];
    const ID_TAREFA_ANALISE = 500;
    const TAMANHO_PAGINA = 100;
    const LOTE_IDS_GIGS = 80;

    function getXsrf() {
        const c = document.cookie
            .split(';')
            .map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function buildHeaders(extra) {
        const h = Object.assign({
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1',
        }, extra || {});
        const xsrf = getXsrf();
        if (xsrf) h['X-XSRF-TOKEN'] = xsrf;
        return h;
    }

    function norm(s) {
        return String(s || '')
            .normalize('NFKD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    async function reqJson(method, path, body) {
        const opts = {
            method,
            credentials: 'include',
            headers: buildHeaders(),
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const r = await fetch(BASE + path, opts);
        let data = null;
        try { data = await r.json(); } catch (_) { data = await r.text().catch(() => null); }
        return { ok: r.ok, status: r.status, data };
    }

    async function buscarProcessosAnaliseLiqExec(opts) {
        const maxPaginas = (opts && opts.maxPaginas) || 50;
        const todos = [];
        for (let pagina = 1; pagina <= maxPaginas; pagina++) {
            const r = await reqJson('PATCH', '/pje-comum-api/api/agrupamentotarefas/processos/todos', {
                pagina,
                tamanhoPagina: TAMANHO_PAGINA,
                subCaixa: null,
                tipoAtividade: null,
                processos: null,
                nomeConclusoMagistrado: null,
                usuarioResponsavel: null,
                faseProcessualString: FASES_ALVO,
                idTarefa: [ID_TAREFA_ANALISE],
                numeroProcesso: null,
                juizoDigital: null,
            });
            if (!r.ok) {
                throw new Error(`HTTP ${r.status} em agrupamentotarefas/processos/todos p${pagina}`);
            }
            const data = r.data || {};
            const lista = Array.isArray(data.resultado) ? data.resultado : [];
            todos.push(...lista);
            const qtdPaginas = data.qtdPaginas || data.totalPaginas || 1;
            if (!lista.length || pagina >= qtdPaginas || lista.length < TAMANHO_PAGINA) {
                break;
            }
        }
        return todos.filter(p => {
            const fase = norm(p.faseProcessual || p.labelFaseProcessual);
            const tarefa = norm(p.tarefa || p.nomeTarefa);
            const faseOk = fase === 'liquidacao' || fase === 'execucao';
            const tarefaOk = Number(p.idTarefa) === ID_TAREFA_ANALISE || tarefa === 'analise';
            return faseOk && tarefaOk;
        });
    }

    async function buscarIdsComGigsEmLote(idsProcessos) {
        const mapa = new Map();
        for (let i = 0; i < idsProcessos.length; i += LOTE_IDS_GIGS) {
            const lote = idsProcessos.slice(i, i + LOTE_IDS_GIGS);
            if (!lote.length) continue;
            const qs = lote.map(id => 'idsProcessos=' + encodeURIComponent(id)).join('&');
            const r = await reqJson('GET', '/pje-gigs-api/api/tiposatividades/poridsprocessos?' + qs);
            if (!r.ok) {
                throw new Error(`HTTP ${r.status} em tiposatividades/poridsprocessos`);
            }
            const arr = Array.isArray(r.data) ? r.data : [];
            for (const item of arr) {
                const pid = item && item.idProcesso;
                if (pid == null) continue;
                if (!mapa.has(pid)) mapa.set(pid, []);
                mapa.get(pid).push(item.descricao || item.id);
            }
        }
        return mapa;
    }

    async function buscarIdsComDocNaoApreciadoEscaninho() {
        const ids = new Set();
        for (let pagina = 1; pagina <= 50; pagina++) {
            const r = await reqJson(
                'GET',
                `/pje-comum-api/api/escaninhos/peticoesjuntadas?pagina=${pagina}&tamanhoPagina=${TAMANHO_PAGINA}&naoApreciados=true`
            );
            if (!r.ok) break;
            const data = r.data || {};
            const lista = Array.isArray(data.resultado) ? data.resultado : (Array.isArray(data) ? data : []);
            for (const item of lista) {
                if (item && item.idProcesso != null) ids.add(Number(item.idProcesso));
            }
            const qtdPaginas = data.qtdPaginas || data.totalPaginas || 1;
            if (!lista.length || pagina >= qtdPaginas || lista.length < TAMANHO_PAGINA) break;
        }
        return ids;
    }

    function temComentario(p) {
        return Boolean(
            p.temComentario ||
            p.temComentarioSecretaria ||
            (typeof p.ultimoComentario === 'string' && p.ultimoComentario.trim().length > 0) ||
            Number(p.numComentariosNaoLidos || 0) > 0
        );
    }

    function temResponsavel(p) {
        return Boolean(
            p.idUsuarioResponsavel ||
            (typeof p.nomeUsuarioResponsavel === 'string' && p.nomeUsuarioResponsavel.trim().length > 0)
        );
    }

    function temDocNaoApreciadoCampo(p) {
        return Boolean(p.isPeticaoNaoApreciada || p.peticaoNaoApreciada);
    }

    async function checarTransicaoAguardandoPrazo(idProcesso, idTarefa) {
        const tid = idTarefa || ID_TAREFA_ANALISE;
        const r = await reqJson('GET', `/pje-comum-api/api/processos/id/${idProcesso}/tarefas/${tid}/transicoes`);
        if (!r.ok || !Array.isArray(r.data)) {
            return { ok: false, status: r.status, disponivel: null, transicao: null };
        }
        const alvo = r.data.find(t => norm(t.nomeTransicaoDestino) === 'aguardando prazo');
        return {
            ok: true,
            status: r.status,
            disponivel: alvo ? Boolean(alvo.transicaoDisponivel) : false,
            transicao: alvo || null,
        };
    }

    async function confirmarSemGigsIndiv(idProcesso) {
        const r = await reqJson('GET', `/pje-gigs-api/api/atividade/processo/${idProcesso}`);
        if (!r.ok) return { ok: false, status: r.status, qtd: null, atividades: [] };
        const arr = Array.isArray(r.data) ? r.data : [];
        return { ok: true, status: r.status, qtd: arr.length, atividades: arr };
    }

    async function filtrarAnaliseLivres(opts) {
        opts = opts || {};
        const confirmarGigsIndividual = opts.confirmarGigsIndividual !== false;
        const consultarEscaninho = opts.consultarEscaninho !== false;
        const filtroAguardandoPrazo = opts.aguardandoPrazoDisponivel; // undefined/null = ambos, true, false
        const t0 = performance.now();

        const base = await buscarProcessosAnaliseLiqExec(opts);
        const idsBase = base.map(p => p.id);

        const [mapaGigsLote, idsEscaninho] = await Promise.all([
            buscarIdsComGigsEmLote(idsBase),
            consultarEscaninho ? buscarIdsComDocNaoApreciadoEscaninho() : Promise.resolve(new Set()),
        ]);

        const descartados = {
            comGigsLote: 0,
            comGigsIndividual: 0,
            comComentario: 0,
            comResponsavel: 0,
            comDocNaoApreciado: 0,
        };

        const preFiltrados = [];
        for (const p of base) {
            const temGigsLote = mapaGigsLote.has(p.id) || Boolean(p.dataPrazoFinal);
            if (temGigsLote) { descartados.comGigsLote++; continue; }
            if (temComentario(p)) { descartados.comComentario++; continue; }
            if (temResponsavel(p)) { descartados.comResponsavel++; continue; }
            if (temDocNaoApreciadoCampo(p) || idsEscaninho.has(Number(p.id))) {
                descartados.comDocNaoApreciado++;
                continue;
            }
            preFiltrados.push(p);
        }

        const processos = [];
        for (const p of preFiltrados) {
            if (confirmarGigsIndividual) {
                const indiv = await confirmarSemGigsIndiv(p.id);
                if (indiv.ok && indiv.qtd > 0) {
                    descartados.comGigsIndividual++;
                    continue;
                }
            }
            const tr = await checarTransicaoAguardandoPrazo(p.id, p.idTarefa);
            if (typeof filtroAguardandoPrazo === 'boolean' && tr.disponivel !== filtroAguardandoPrazo) {
                continue;
            }
            processos.push({
                id: p.id,
                numeroProcesso: p.numeroProcesso,
                faseProcessual: p.faseProcessual,
                idTarefa: p.idTarefa,
                tarefa: p.tarefa,
                dataEntradaTarefa: p.dataEntradaTarefa || null,
                aguardandoPrazoDisponivel: tr.disponivel,
                estadoAguardandoPrazo: tr.disponivel === true ? 'disponivel' : (tr.disponivel === false ? 'indisponivel' : 'erro'),
            });
        }

        const resultado = {
            ok: true,
            ms: Math.round(performance.now() - t0),
            totalAnaliseLiqExec: base.length,
            preFiltradosSemGigsComRespDoc: preFiltrados.length,
            totalFiltrados: processos.length,
            aguardandoPrazoDisponivelCount: processos.filter(x => x.aguardandoPrazoDisponivel === true).length,
            aguardandoPrazoIndisponivelCount: processos.filter(x => x.aguardandoPrazoDisponivel === false).length,
            descartados,
            escaninhoIdsCount: idsEscaninho.size,
            processos,
        };
        window.__PJE_FILTRO_ANALISE__ = resultado;
        return resultado;
    }

    window.pjeFiltrarAnaliseLivres = filtrarAnaliseLivres;
    window.__PJE_FILTRO_ANALISE_DONE__ = false;
    filtrarAnaliseLivres().then(
        res => {
            window.__PJE_FILTRO_ANALISE__ = res;
            window.__PJE_FILTRO_ANALISE_DONE__ = true;
            console.log('[PJeFiltroAnalise] Concluído:', res);
        },
        err => {
            window.__PJE_FILTRO_ANALISE__ = { ok: false, erro: String(err && err.stack || err) };
            window.__PJE_FILTRO_ANALISE_DONE__ = true;
            console.error('[PJeFiltroAnalise] Erro:', err);
        }
    );
})();
