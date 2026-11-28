'use strict';

// ═══════════════════════════════════════════════════════════════════
// GIGS — atividades.js (API sem UI): listar/excluir atividades e limpar
// as vencidas que contenham "teimosinha".
// Endpoints validados no probe:
//   GET    /pje-gigs-api/api/atividade/processo/{idProcesso}   → Array[atividade]
//   DELETE /pje-gigs-api/api/atividade/{idAtividade}           → 204
// Campos: id, idProcesso, tipoAtividade, dataPrazo, statusAtividade, observacao...
//
// Uso principal (sem clique, sem botão):
//   Atalhos.abrir_processo_direto(numero, { rota: 'anexar', limparGigsTeimosinha: true })
//   → apaga as GIGS vencidas com "teimosinha" ANTES de abrir a aba do processo.
//
// Também funciona em aba do PJe com `?pjetools=gigs-teimosinha` na URL
// (fallback same-origin, quando o pré-bloqueio CSRF impede o DELETE cross-site).
//
// API:
//   PjeGigsAtividades.listar(idProcesso, basePje)
//   PjeGigsAtividades.excluir(idAtividade, basePje)
//   PjeGigsAtividades.teimosinhaVencidas(idProcesso, basePje)
//   PjeGigsAtividades.limparTeimosinhaVencidas(idProcesso, {base, seco, onProgresso})
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.PjeGigsAtividades) return;

    var API = '/pje-gigs-api/api';
    var VERSAO = '1.2.0';
    var PJE_PADRAO = 'https://pje.trt2.jus.br';
    var PARAM = 'pjetools';
    var VALOR_PARAM = 'gigs-teimosinha';
    var RE_TEIMOSINHA = /teimosinha/i;

    // ── utilidades ──────────────────────────────────────────────────
    function naTelaPje() {
        var h = window.location.hostname || '';
        return /(^|\.)pje[a-z0-9-]*\./i.test(h) && /\.jus\.br$/i.test(h);
    }

    function basePje(explicito) {
        if (explicito) return String(explicito).replace(/\/+$/, '');
        return naTelaPje() ? window.location.origin : PJE_PADRAO;
    }

    function idProcessoDaUrl() {
        var m = (window.location.pathname || '').match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }

    function norm(s) {
        return String(s === null || s === undefined ? '' : s).replace(/\s+/g, ' ').trim();
    }

    function confirmar(msg) {
        var w = (typeof unsafeWindow !== 'undefined' && unsafeWindow) ? unsafeWindow : window;
        var fn = (w && w.confirm) || window.confirm;
        return typeof fn === 'function' ? fn.call(w || window, msg) : false;
    }

    // XSRF só é legível na própria origem do PJe (no SISBAJUD o cookie não existe)
    function headersJson() {
        var h = { 'Accept': 'application/json', 'Content-Type': 'application/json' };
        var m = String(document.cookie || '').match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
        if (m) h['X-XSRF-TOKEN'] = decodeURIComponent(m[1]);
        return h;
    }

    // GM_xmlhttpRequest quando disponível (sem CORS, funciona do SISBAJUD);
    // fetch como reserva (mesma origem).
    function req(method, url) {
        if (typeof GM_xmlhttpRequest === 'function') {
            return new Promise(function (resolve, reject) {
                try {
                    GM_xmlhttpRequest({
                        method: method,
                        url: url,
                        headers: headersJson(),
                        timeout: 20000,
                        onload: function (r) { resolve({ status: r.status, texto: r.responseText || '' }); },
                        onerror: function () { reject(new Error('rede (GM_xhr)')); },
                        ontimeout: function () { reject(new Error('timeout (GM_xhr)')); }
                    });
                } catch (e) { reject(e); }
            });
        }
        return fetch(url, { method: method, credentials: 'include', headers: headersJson() })
            .then(function (r) {
                return r.text().then(function (t) { return { status: r.status, texto: t }; });
            });
    }

    // ── regra ───────────────────────────────────────────────────────
    function textoAtividade(a) {
        if (!a) return '';
        return norm([a.tipoAtividade, a.observacao, a.descricao, a.processo, a.nome].join(' '));
    }

    function ehTeimosinha(a) {
        return RE_TEIMOSINHA.test(textoAtividade(a));
    }

    // dataPrazo vem como 'YYYY-MM-DD' (ou ISO); sem hora, vence no fim do dia
    function dataPrazoMs(a) {
        var v = a && (a.dataPrazo || a.dataPrazoFinal);
        if (v === null || v === undefined || v === '') return NaN;
        if (typeof v === 'number') return v;
        var s = String(v).trim();
        var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return new Date(+m[1], +m[2] - 1, +m[3], 23, 59, 59, 999).getTime();
        m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
        if (m) return new Date(+m[3], +m[2] - 1, +m[1], 23, 59, 59, 999).getTime();
        var t = Date.parse(s);
        return isNaN(t) ? NaN : t;
    }

    function vencida(a, agora) {
        var t = dataPrazoMs(a);
        return isFinite(t) && t < (agora || Date.now());
    }

    function aberta(a) {
        var st = norm(a && a.statusAtividade).toUpperCase();
        if (!st) return true;
        return st.indexOf('CONCLU') === -1 && st.indexOf('CANCEL') === -1 && st.indexOf('EXCLU') === -1;
    }

    function descrever(a) {
        return {
            id: a.id,
            tipo: norm(a.tipoAtividade),
            prazo: norm(a.dataPrazo),
            status: norm(a.statusAtividade)
        };
    }

    // ── API ─────────────────────────────────────────────────────────
    async function listar(idProcesso, base) {
        var id = idProcesso || idProcessoDaUrl();
        if (!id) throw new Error('sem idProcesso');
        var r = await req('GET', basePje(base) + API + '/atividade/processo/' + encodeURIComponent(id));
        if (r.status < 200 || r.status >= 300) throw new Error('GET atividades HTTP ' + r.status);
        var dados;
        try { dados = JSON.parse(r.texto || '[]'); } catch (e) { throw new Error('resposta não-JSON'); }
        return Array.isArray(dados) ? dados : [];
    }

    async function excluir(idAtividade, base) {
        if (!idAtividade) return { ok: false, status: 0, erro: 'idAtividade vazio' };
        try {
            var r = await req('DELETE', basePje(base) + API + '/atividade/' + encodeURIComponent(idAtividade));
            var ok = (r.status >= 200 && r.status < 300) || r.status === 204;
            if (!ok) console.warn('[PjeGigsAtividades] DELETE', idAtividade, 'HTTP', r.status);
            return { ok: ok, status: r.status, id: idAtividade };
        } catch (e) {
            console.warn('[PjeGigsAtividades] DELETE falhou', idAtividade, e);
            return { ok: false, status: 0, id: idAtividade, erro: String((e && e.message) || e) };
        }
    }

    async function teimosinhaVencidas(idProcesso, base) {
        var lista = await listar(idProcesso, base);
        var agora = Date.now();
        var alvo = lista.filter(function (a) {
            return aberta(a) && ehTeimosinha(a) && vencida(a, agora);
        });
        console.log('[PjeGigsAtividades] ' + alvo.length + ' de ' + lista.length +
            ' atividade(s) vencida(s) com "teimosinha"', alvo.map(descrever));
        return alvo;
    }

    // Apaga (sem UI). seco:true apenas lista. confirmar:true pede confirm().
    async function limparTeimosinhaVencidas(idProcesso, opcoes) {
        var opts = Object.assign({ base: null, seco: false, confirmar: false, onProgresso: null }, opcoes || {});
        var id = idProcesso || idProcessoDaUrl();
        if (!id) return { ok: false, motivo: 'sem idProcesso' };

        var alvo = await teimosinhaVencidas(id, opts.base);
        if (!alvo.length) return { ok: true, total: 0, excluidas: 0, falhas: 0, itens: [] };
        if (opts.seco) return { ok: true, seco: true, total: alvo.length, itens: alvo.map(descrever) };

        if (opts.confirmar) {
            var resumo = alvo.slice(0, 10).map(function (a) {
                return '• ' + a.id + ' — ' + norm(a.tipoAtividade) + ' — prazo ' + norm(a.dataPrazo);
            }).join('\n');
            var msg = 'Excluir ' + alvo.length + ' GIGS vencida(s) com "teimosinha" do processo ' +
                id + '?\n\n' + resumo + (alvo.length > 10 ? '\n… e mais ' + (alvo.length - 10) : '');
            if (!confirmar(msg)) return { ok: false, cancelado: true, total: alvo.length };
        }

        var excluidas = 0;
        var falhas = [];
        for (var i = 0; i < alvo.length; i++) {
            var a = alvo[i];
            var r = await excluir(a.id, opts.base);
            if (r.ok) excluidas++;
            else falhas.push({ id: a.id, status: r.status, erro: r.erro || '' });
            if (typeof opts.onProgresso === 'function') {
                try { opts.onProgresso(i + 1, alvo.length, a, r); } catch (e) { }
            }
        }
        console.log('[PjeGigsAtividades] limpeza: ' + excluidas + '/' + alvo.length + ' excluída(s)', falhas);
        return { ok: falhas.length === 0, total: alvo.length, excluidas: excluidas, falhas: falhas.length, erros: falhas };
    }

    // ── Fallback: aba do PJe aberta com ?pjetools=gigs-teimosinha ────
    function marcadoNaUrl() {
        try {
            var u = new URL(window.location.href);
            return u.searchParams.get(PARAM) === VALOR_PARAM;
        } catch (e) { return false; }
    }

    function limparParametroUrl() {
        try {
            var u = new URL(window.location.href);
            if (u.searchParams.get(PARAM) !== VALOR_PARAM) return;
            u.searchParams.delete(PARAM);
            var qs = u.searchParams.toString();
            window.history.replaceState(window.history.state, '', u.pathname + (qs ? '?' + qs : '') + u.hash);
        } catch (e) { }
    }

    async function tratarParametroUrl() {
        if (!naTelaPje() || !marcadoNaUrl()) return null;
        var id = idProcessoDaUrl();
        if (!id) return null;
        var res;
        try {
            res = await limparTeimosinhaVencidas(id, { base: window.location.origin });
        } finally {
            limparParametroUrl();
        }
        return res;
    }

    window.PjeGigsAtividades = {
        listar: listar,
        excluir: excluir,
        teimosinhaVencidas: teimosinhaVencidas,
        limparTeimosinhaVencidas: limparTeimosinhaVencidas,
        tratarParametroUrl: tratarParametroUrl,
        idProcessoDaUrl: idProcessoDaUrl
    };

    if (naTelaPje() && /\/pjekz\/processo\/\d+/.test(window.location.pathname || '')) {
        tratarParametroUrl().catch(function (e) {
            console.warn('[PjeGigsAtividades] limpeza por parâmetro falhou:', e);
        });
    }

    console.log('[PjeGigsAtividades] módulo v' + VERSAO + ' carregado em',
        window.location.host + window.location.pathname);
})();
