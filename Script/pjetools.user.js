// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.0.0
// @description  Suite de ferramentas para PJe (Lista + Atalhos + Infojud)
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt2.jus.br/pjekz/processo/*/comunicacoesprocessuais/minutas*
// @match        https://pje.trt2.jus.br/pjekz/pagamento/*/cadastro*
// @match        https://sisbajud.cnj.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-idle
// ==/UserScript==

(async function () {
    'use strict';

    if (window.self !== window.top) return;

    const url = window.location.href;
    const GITHUB_BASE = 'https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/';
    const V = '?v=205';

    // Roteador de injeção assíncrona (Lazy Loader no contexto do sandbox)
    async function load(paths) {
        for (const p of paths) {
            try {
                const res = await fetch(GITHUB_BASE + p + V);
                const code = await res.text();
                // O eval executará a IIFE no contexto do Tampermonkey Sandbox
                // Garantindo o acesso ao GM_setValue, GM_getValue, etc.
                eval(code);
            } catch (e) {
                console.error(`[PJeTools] Erro ao carregar o módulo ${p}:`, e);
            }
        }
    }

    async function injectLogic() {
        // --- 1. Infojud CROSS-DOMAIN (Receita Federal) ---
        if (url.includes('cav.receita.fazenda.gov.br')) {
            await load(['modules/infojud/infojud.legacy.js']);
            return;
        }

        // --- 2. SISBAJUD Standalone ---
        if (url.includes('sisbajud.cnj.jus.br')) {
            await load([
                'core/utils.js', // Necessário para utils (sleep, showToast, etc)
                'core/state.js', // Necessário para PJeState
                'modules/lista/lista.pgto.js'
            ]);
            return;
        }

        // --- 3. PJe PAGAMENTOS ---
        if (url.includes('/pagamento/') && url.includes('/cadastro')) {
            console.log('[PJeTools] Página de pagamento detectada');
            return;
        }

        // --- 4. PJe MINUTAS ---
        if (url.includes('/comunicacoesprocessuais/minutas')) {
            // Worker Sub-Tool (MaisePJe)
            if (new URLSearchParams(location.search).get('maispje_worker') === '1') {
                if (document.documentElement.hasAttribute('data-pjetools-worker')) return;
                document.documentElement.setAttribute('data-pjetools-worker', '1');
                await load([
                    'core/utils.js',
                    'core/state.js',
                    'modules/atalhos/atalhos.worker.js'
                ]);
                window.addEventListener('load', () => setTimeout(() => window.runWorker && window.runWorker(), 2000));
                return;
            }

            // Infojud PJe (nativo)
            await load(['modules/infojud/infojud.legacy.js']);
            return;
        }

        // --- 5. PJe DETALHE (Painel Principal) ---
        const isPJe = url.includes('pje.trt2.jus.br');
        const isAbaDetalhe = /\/processo\/\d+\/detalhe/.test(url) && !url.includes('/minutas');

        if (isPJe && isAbaDetalhe) {
            await load([
                'core/utils.js',
                'core/state.js',
                'modules/lista/lista.timeline.js',
                'modules/lista/lista.check.js',
                'modules/lista/lista.edital.js',
                'modules/lista/lista.pgto.js',
                'modules/atalhos/atalhos.js',
                'ui/painel.js'
            ]);

            if (window.antiDuplicacao && !window.antiDuplicacao('data-pjetools-boot')) return;

            if (window.monitorarSPA) {
                window.monitorarSPA(() => {
                    window.PJeState && window.PJeState.dispose();
                    setTimeout(bootDetalhe, 300);
                });
            }

            bootDetalhe();

            function bootDetalhe() {
                if (!window.PJeState || window.PJeState._iniciado) return;
                window.PJeState._iniciado = true;
                if (window.inicializarPainel) window.inicializarPainel();
                if (window.initAtalhos) window.initAtalhos();
            }
            return;
        }
    }

    injectLogic();
})();
