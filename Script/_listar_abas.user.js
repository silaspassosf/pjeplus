// ==UserScript==
// @name         PJe Abas (teste — só listar)
// @namespace    pjeplus.teste
// @version      0.2.0
// @description  Lista as abas do navegador onde este script roda (GM_getTabs), com título, URL e idade do último sinal
// @author       Silas
// @match        https://pje.trt2.jus.br/*
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://sisbajud.cnj.jus.br/*
// @match        https://alvaraeletronico.trt2.jus.br/*
// @match        https://aplicacoes1.trt2.jus.br/eCarta-web/*
// @match        https://www3.bcb.gov.br/saj/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// @grant        GM_getTab
// @grant        GM_saveTab
// @grant        GM_getTabs
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_addValueChangeListener
// @grant        GM_registerMenuCommand
// @grant        GM_info
// @grant        unsafeWindow
// @run-at       document-idle
// ==/UserScript==

/* ═══════════════════════════════════════════════════════════════════
   TESTE ISOLADO — LISTAR ABAS

   Diferença para a versão de console: aqui usamos GM_getTabs/GM_saveTab,
   que o Tampermonkey mantém por script e enxerga TODAS as abas onde este
   script roda — inclusive de domínios diferentes (PJe e SISBAJUD juntos).

   FRESCOR: cada aba se recarimba a cada 5s e, sob demanda, quando recebe
   um "ping" por GM_addValueChangeListener (canal que não é estrangulado
   em aba de segundo plano).

   ⚠️ Userscript instalado AGORA não é injetado em aba já aberta:
      recarregue as abas (F5) uma vez para entrarem na lista.

   USO (console de qualquer aba que rode este script):
     PjeAbas.listar()          → array com id, title, url, host, idadeMs
     PjeAbas.listar('10015')   → filtra por trecho do título/URL
     PjeAbas.imprimir()        → console.table da lista
     PjeAbas.imprimir('sisb')  → idem, filtrado
     PjeAbas.diagnostico()     → versão, APIs e registro cru
     PjeAbas.ajuda()           → lembrete

   ATENÇÃO: o Tampermonkey mantém o objeto da aba mesmo depois de fechá-la.
   Por isso cada linha traz idadeMs e a marca "parada" (sem sinal há >20s).
   ═══════════════════════════════════════════════════════════════════ */
(() => {
    'use strict';

    const VERSAO = '0.2.0';
    const BATIDA_MS = 5000;
    const LIMITE_MS = 20000;     // sem sinal por 20s = provavelmente fechada
    const CHAVE_PING = 'pjeabas_ping';

    let MEU_ID = null;
    let timer = null;
    let ultimoCarimbo = 0;

    const aleat = () => Math.random().toString(36).slice(2, 8);
    const normalizar = (s) => (s || '')
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().replace(/\s+/g, ' ').trim();

    // ── carimba esta aba no registro do Tampermonkey ─────────────────
    function carimbar() {
        return new Promise((resolve) => {
            try {
                GM_getTab((tab) => {
                    tab = tab || {};
                    tab.id = tab.id || ('aba_' + aleat());
                    tab.title = document.title || '';
                    tab.url = location.href;
                    tab.host = location.host;
                    tab.ts = Date.now();
                    tab.visivel = document.visibilityState === 'visible';
                    tab.script = VERSAO;
                    MEU_ID = tab.id;
                    ultimoCarimbo = tab.ts;
                    try { GM_saveTab(tab); } catch (e) { }
                    resolve(tab);
                });
            } catch (e) {
                resolve(null);
            }
        });
    }

    // ── ping: pede que TODAS as abas se recarimbem ───────────────────
    // Canal do Tampermonkey: cruza abas e domínios e NÃO é estrangulado
    // em aba de segundo plano (diferente de setInterval).
    function ping(esperaMs) {
        return new Promise((resolve) => {
            try { GM_setValue(CHAVE_PING, { n: Date.now() + aleat(), de: MEU_ID }); } catch (e) { }
            setTimeout(resolve, esperaMs || 300);
        });
    }

    let ultimoPingVisto = null;
    try {
        GM_addValueChangeListener(CHAVE_PING, (nome, antes, agora, remoto) => {
            if (!remoto || !agora) return;
            if (agora.n === ultimoPingVisto) return;   // mesmo pedido, já respondido
            ultimoPingVisto = agora.n;
            carimbar();
        });
    } catch (e) { }

    // ── lista ────────────────────────────────────────────────────────
    async function listar(filtro, opcoes) {
        const opts = Object.assign({ ping: true, espera: 300 }, opcoes || {});
        if (opts.ping) await ping(opts.espera);

        return new Promise((resolve) => {
            const termos = normalizar(filtro).split(' ').filter(Boolean);
            try {
                GM_getTabs((tabs) => {
                    const agora = Date.now();
                    const lista = [];
                    Object.entries(tabs || {}).forEach(([tabId, t]) => {
                        const d = t || {};
                        const idade = d.ts ? agora - d.ts : null;
                        const item = {
                            id: d.id || ('tab_' + tabId),
                            title: d.title || '(sem titulo)',
                            host: d.host || '',
                            url: d.url || '',
                            idadeMs: idade,
                            visto: idade === null ? 'nunca'
                                : idade < 6000 ? 'agora'
                                : Math.round(idade / 1000) + 's',
                            parada: idade === null || idade > LIMITE_MS,
                            eu: d.id === MEU_ID
                        };
                        if (termos.length) {
                            const alvo = normalizar(item.title + ' ' + item.url + ' ' + item.host);
                            if (!termos.every((x) => alvo.indexOf(x) > -1)) return;
                        }
                        lista.push(item);
                    });
                    lista.sort((a, b) => (a.eu ? -1 : b.eu ? 1
                        : a.parada !== b.parada ? (a.parada ? 1 : -1)
                            : a.title.localeCompare(b.title, 'pt-BR')));
                    resolve(lista);
                });
            } catch (e) {
                resolve([]);
            }
        });
    }

    async function imprimir(filtro) {
        const lista = await listar(filtro);
        const linhas = lista.map((a) => ({
            eu: a.eu ? 'EU' : '',
            id: a.id,
            visto: a.visto,
            parada: a.parada ? 'SIM' : '',
            host: a.host,
            titulo: a.title,
            caminho: (() => { try { return new URL(a.url).pathname; } catch (e) { return a.url; } })()
        }));
        console.log('%c[PjeAbas] ' + lista.length + ' aba(s)' + (filtro ? ' com "' + filtro + '"' : ''),
            'font-weight:bold;color:#1976d2');
        if (console.table) console.table(linhas);
        else console.log(linhas);

        if (lista.length <= 1) {
            console.warn('[PjeAbas] só esta aba apareceu. Userscript recém-instalado não é ' +
                'injetado em aba já aberta — recarregue as outras abas (F5) uma vez. ' +
                'Confira com PjeAbas.diagnostico().');
        }
        return lista;
    }

    function diagnostico() {
        return new Promise((resolve) => {
            const info = {};
            try {
                info.script = (GM_info && GM_info.script)
                    ? GM_info.script.name + ' v' + GM_info.script.version : '?';
                info.handler = (GM_info && GM_info.scriptHandler)
                    ? GM_info.scriptHandler + ' ' + GM_info.version : '?';
            } catch (e) { }
            info.estaAba = { id: MEU_ID, title: document.title, url: location.href, host: location.host };
            info.apis = {
                GM_getTabs: typeof GM_getTabs,
                GM_saveTab: typeof GM_saveTab,
                GM_addValueChangeListener: typeof GM_addValueChangeListener,
                unsafeWindow: typeof unsafeWindow
            };
            try {
                GM_getTabs((tabs) => {
                    const ids = Object.entries(tabs || {}).map(([k, v]) => ({
                        tabId: k,
                        id: (v && v.id) || null,
                        host: (v && v.host) || null,
                        titulo: (v && v.title) || null,
                        visto: v && v.ts ? Math.round((Date.now() - v.ts) / 1000) + 's' : 'nunca'
                    }));
                    info.abasNoRegistro = ids.length;
                    info.abas = ids;
                    console.log('%c[PjeAbas] diagnostico', 'font-weight:bold;color:#1976d2', info);
                    if (console.table && ids.length) console.table(ids);
                    resolve(info);
                });
            } catch (e) {
                info.erro = String(e);
                resolve(info);
            }
        });
    }

    function ajuda() {
        console.log('%cPjeAbas ' + VERSAO + ' (GM_getTabs)',
            'font:bold 13px monospace;color:#1976d2',
            '\n  PjeAbas.listar()          → array de abas',
            '\n  PjeAbas.listar("10015")   → filtrado por título/URL',
            '\n  PjeAbas.imprimir()        → console.table',
            '\n  PjeAbas.existe("sisb")    → true/false',
            '\n  esta aba: ' + MEU_ID + ' — "' + document.title + '"');
        return MEU_ID;
    }

    // ── exposição no console da página ───────────────────────────────
    const api = {
        versao: VERSAO,
        meuId: () => MEU_ID,
        listar,
        imprimir,
        existe: async (f) => (await listar(f)).length > 0,
        diagnostico,
        ajuda,
        ping: () => ping(0),
        recarimbar: carimbar
    };

    function expor() {
        try { unsafeWindow.PjeAbas = api; return 'unsafeWindow'; } catch (e) { }
        try {
            if (typeof cloneInto === 'function') {
                unsafeWindow.PjeAbas = cloneInto(api, unsafeWindow, { cloneFunctions: true });
                return 'cloneInto';
            }
        } catch (e) { }
        try { window.PjeAbas = api; return 'window'; } catch (e) { }
        return null;
    }

    // ── ciclo de vida ────────────────────────────────────────────────
    function iniciar() {
        carimbar();
        timer = setInterval(carimbar, BATIDA_MS);
        window.addEventListener('focus', carimbar);
        window.addEventListener('blur', carimbar);
        document.addEventListener('visibilitychange', carimbar);
        window.addEventListener('pagehide', () => {
            clearInterval(timer);
            carimbar();   // último sinal antes de sair
        });
    }

    iniciar();
    const via = expor();

    try {
        GM_registerMenuCommand('PjeAbas: listar abas (console)', () => imprimir());
    } catch (e) { }

    setTimeout(() => {
        if (via) {
            console.log('%c[PjeAbas] pronto nesta aba — ' + MEU_ID +
                ' ("' + document.title + '") — use PjeAbas.imprimir()',
                'color:#1976d2;font-weight:bold');
        } else {
            console.warn('[PjeAbas] não consegui expor no console; use o menu do Tampermonkey');
        }
    }, 300);
})();
