// ==UserScript==
// @name         SISBAJUD — Séries da Teimosinha por API
// @namespace    pjeplus.sisb.teste
// @version      0.3.0
// @description  Lê as séries da Teimosinha por API (/v1/serie) e mostra só o que a leitura de séries entrega: id, início, fim, valor a bloquear e valor bloqueado.
// @author       Hermes (PJE Watcher)
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://sisbajud.cnj.jus.br/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

/*
 * SAÍDA: 5 campos por série, nada mais.
 *   id da série ............ codSerie
 *   data de início ......... ordemOriginal.dataProgramadaEnvio (fallback: ordemOriginal.dataProtocolo)
 *   data de fim ............ dataLimite (fallback: dataEncerramento)
 *   valor a bloquear ....... valorBloqueioTotal
 *   valor bloqueado ........ valorBloqueioRealizado
 *
 * Rodar numa aba JÁ LOGADA em https://sisbajud.pdpj.jus.br/ (ou sisbajud.cnj.jus.br).
 * Same-origin é obrigatório: é o que dá cookie de sessão + acesso ao localStorage.
 *
 * Console (F12):
 *   SisbSerie.serie('1000991-07.2020.5.02.0703')   // GET /v1/serie?codProcesso=10009910720205020703
 *   SisbSerie.seriePorId(22511091)                 // GET /v1/serie/22511091
 *   SisbSerie.get('/v1/serie?codProcesso=...')     // resposta crua, para inspecionar
 */

(function () {
    'use strict';

    const CAMINHO_SERIE = '/v1/serie';
    const TIMEOUT_MS = 20000;

    function normalizarNumero(v) {
        return String(v == null ? '' : v).replace(/\D/g, '');
    }

    function expDoJwt(token) {
        try {
            const p = String(token).split('.');
            if (p.length < 2) return 0;
            let b = p[1].replace(/-/g, '+').replace(/_/g, '/');
            while (b.length % 4) b += '=';
            return Number(JSON.parse(atob(b)).exp) || 0;
        } catch (e) {
            return 0;
        }
    }

    // Chave usada pelo bot: SISB/core.py grava/injeta 'sisbajud-token' e 'LS.sisbajud-token'.
    function token() {
        const chaves = [];
        try {
            for (let i = 0; i < localStorage.length; i++) chaves.push(localStorage.key(i));
        } catch (e) {
            return null;
        }
        const preferidas = ['sisbajud-token', 'LS.sisbajud-token', 'access_token', 'LS.access_token'];
        const ordem = preferidas.filter((k) => chaves.indexOf(k) >= 0)
            .concat(chaves.filter((k) => preferidas.indexOf(k) < 0 && /token/i.test(k)));

        for (const chave of ordem) {
            let valor = null;
            try { valor = localStorage.getItem(chave); } catch (e) { continue; }
            if (!valor) continue;
            let t = valor;
            if (/^\s*[{"]/.test(valor)) {
                try {
                    const j = JSON.parse(valor);
                    t = j.access_token || j.token || j.accessToken || j.value || valor;
                } catch (e) { /* cru */ }
            }
            if (typeof t !== 'string') continue;
            t = t.replace(/^"|"$/g, '').trim();
            if (t.length < 20) continue;
            return { chave: chave, valor: t, exp: expDoJwt(t) };
        }
        return null;
    }

    /** GET cru. Se vier 401/403 com Bearer, repete uma vez sem header (só cookie). */
    async function get(caminho, opcoes) {
        opcoes = opcoes || {};
        const url = /^https?:/i.test(caminho) ? caminho : location.origin + caminho;
        const t = token();

        async function dispara(comHeader) {
            const headers = { Accept: 'application/json' };
            if (comHeader && t) headers.Authorization = 'Bearer ' + t.valor;

            const t0 = performance.now();
            const ctrl = new AbortController();
            const timer = setTimeout(() => ctrl.abort(), opcoes.timeout || TIMEOUT_MS);
            let resp = null, texto = '', erro = null;
            try {
                resp = await fetch(url, { method: 'GET', headers: headers, credentials: 'include', signal: ctrl.signal });
                texto = await resp.text();
            } catch (e) {
                erro = String((e && e.message) || e);
            } finally {
                clearTimeout(timer);
            }

            let json = null;
            try { json = JSON.parse(texto); } catch (e) { /* não-JSON */ }

            return {
                url: url,
                status: resp ? resp.status : 0,
                ms: Math.round(performance.now() - t0),
                comHeader: !!comHeader,
                texto: texto,
                json: json,
                erro: erro
            };
        }

        let r = await dispara(true);
        if ((r.status === 401 || r.status === 403) && t) {
            const semHeader = await dispara(false);
            semHeader.tentativaAnterior = { status: r.status, comHeader: true };
            r = semHeader;
        }
        r.token = t ? { chave: t.chave, exp: t.exp } : null;
        return r;
    }

    function serie(codProcesso, opcoes) {
        const num = normalizarNumero(codProcesso);
        if (num.length < 15) {
            return Promise.resolve({ url: null, status: 0, erro: 'número inválido: ' + codProcesso });
        }
        return get(CAMINHO_SERIE + '?codProcesso=' + encodeURIComponent(num), opcoes);
    }

    function seriePorId(id, opcoes) {
        const limpo = String(id == null ? '' : id).trim();
        if (!limpo) return Promise.resolve({ url: null, status: 0, erro: 'id vazio' });
        return get(CAMINHO_SERIE + '/' + encodeURIComponent(limpo), opcoes);
    }

    // ── extração dos 5 campos ────────────────────────────────────────────────

    function primeiroNaoNulo() {
        for (let i = 0; i < arguments.length; i++) {
            const v = arguments[i];
            if (v !== undefined && v !== null && v !== '') return v;
        }
        return null;
    }

    /** Aceita tanto o array do endpoint de lista quanto o objeto do endpoint por id. */
    function extrairSeries(json) {
        if (!json) return [];
        const lista = Array.isArray(json) ? json : [json];
        return lista.map(function (s) {
            const ordem = s.ordemOriginal || {};
            return {
                id: s.codSerie,
                inicio: primeiroNaoNulo(ordem.dataProgramadaEnvio, ordem.dataProtocolo),
                fim: primeiroNaoNulo(s.dataLimite, s.dataEncerramento),
                aBloquear: s.valorBloqueioTotal,
                bloqueado: s.valorBloqueioRealizado
            };
        });
    }

    function data(ms) {
        if (ms === null || ms === undefined || ms === '') return '-';
        const d = new Date(Number(ms));
        if (isNaN(d.getTime())) return '-';
        return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }

    function moeda(v) {
        if (v === null || v === undefined || v === '') return '-';
        return Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function tabela(series) {
        const cab = ['SÉRIE', 'INÍCIO', 'FIM', 'A BLOQUEAR', 'BLOQUEADO'];
        const linhas = series.map(function (s) {
            return [String(s.id == null ? '-' : s.id), data(s.inicio), data(s.fim), moeda(s.aBloquear), moeda(s.bloqueado)];
        });
        const larguras = cab.map(function (c, i) {
            return Math.max.apply(null, [c.length].concat(linhas.map(function (l) { return l[i].length; })));
        });
        const fmt = function (cols) {
            return cols.map(function (c, i) { return c.padEnd(larguras[i]); }).join('  ').replace(/\s+$/, '');
        };
        return [fmt(cab)].concat(linhas.map(fmt)).join('\n');
    }

    function render(r) {
        if (r.erro && !r.status) return 'ERRO: ' + r.erro;
        if (r.status !== 200) {
            return 'HTTP ' + r.status + ' — ' + String(r.texto || '(sem corpo)').slice(0, 300);
        }
        const series = extrairSeries(r.json);
        if (!series.length) return 'HTTP 200, nenhuma série no retorno.';

        const total = series.reduce(function (a, s) { return a + (Number(s.bloqueado) || 0); }, 0);
        const cabecalho = series.length + ' série(s) | ' + r.ms + 'ms | ' +
            (r.comHeader ? 'Bearer' : 'cookie') + ' | total bloqueado ' + moeda(total);

        return cabecalho + '\n\n' + tabela(series);
    }

    const API = {
        get: get,
        serie: serie,
        seriePorId: seriePorId,
        extrairSeries: extrairSeries,
        token: token,
        CAMINHO_SERIE: CAMINHO_SERIE
    };
    if (typeof window !== 'undefined') window.SisbSerie = API;
    if (typeof module !== 'undefined' && module.exports) module.exports = API;

    if (typeof document === 'undefined') return; // ambiente de teste

    // ── painel ───────────────────────────────────────────────────────────────
    function criarUI() {
        if (document.getElementById('sisb-serie')) return;

        const st = document.createElement('style');
        st.textContent = [
            '#sisb-serie{position:fixed;right:16px;bottom:16px;width:560px;max-height:70vh;z-index:2147483647;',
            'background:#1e1e1e;color:#e6e6e6;border:1px solid #444;border-radius:8px;display:flex;',
            'flex-direction:column;font:12px/1.4 system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.5)}',
            '#sisb-serie header{display:flex;justify-content:space-between;padding:7px 10px;',
            'border-bottom:1px solid #444;font-weight:600}',
            '#sisb-serie .c{padding:9px;display:flex;flex-direction:column;gap:7px;overflow:auto}',
            '#sisb-serie .l{display:flex;gap:6px}',
            '#sisb-serie input{flex:1;background:#111;color:#e6e6e6;border:1px solid #444;border-radius:4px;',
            'padding:5px 7px;font:12px ui-monospace,monospace}',
            '#sisb-serie button{background:#333;color:#e6e6e6;border:1px solid #555;border-radius:4px;',
            'padding:5px 9px;cursor:pointer;font:12px system-ui,sans-serif}',
            '#sisb-serie button.p{background:#0b5cad;border-color:#0b5cad}',
            '#sisb-serie pre{white-space:pre;overflow:auto;background:#111;border:1px solid #444;',
            'border-radius:4px;padding:8px;margin:0;max-height:44vh;',
            'font:11px/1.5 ui-monospace,monospace;color:#d6d6d6}'
        ].join('');
        document.head.appendChild(st);

        const p = document.createElement('div');
        p.id = 'sisb-serie';
        p.innerHTML = [
            '<header><span>Séries da Teimosinha</span><button id="ss-x">×</button></header>',
            '<div class="c">',
            '  <div class="l"><input id="ss-proc" placeholder="Número do processo"><button id="ss-go1" class="p">por processo</button></div>',
            '  <div class="l"><input id="ss-id" placeholder="id da série"><button id="ss-go2" class="p">por id</button></div>',
            '  <pre id="ss-out">Cole o número do processo e clique.</pre>',
            '</div>'
        ].join('');
        document.body.appendChild(p);

        const out = document.getElementById('ss-out');

        document.getElementById('ss-x').addEventListener('click', () => { p.style.display = 'none'; });
        document.getElementById('ss-go1').addEventListener('click', async () => {
            out.textContent = 'GET...';
            out.textContent = render(await serie(document.getElementById('ss-proc').value));
        });
        document.getElementById('ss-go2').addEventListener('click', async () => {
            out.textContent = 'GET...';
            out.textContent = render(await seriePorId(document.getElementById('ss-id').value));
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', criarUI);
    else criarUI();
})();
