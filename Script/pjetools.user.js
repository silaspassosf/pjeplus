// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.1.1
// @description  Suite de ferramentas para PJe
// @author       Silas
// ── PJe (cobre todas as rotas com um único match)
// @match        https://pje.trt2.jus.br/pjekz/*
// @match        https://pje1g.trt2.jus.br/pjekz/*
// ── Externos (domínios distintos mantidos individuais)
// @match        https://sisbajud.cnj.jus.br/*
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// ── Único require: o loader (bumpar só ele ao adicionar módulos)
// (loader injetado inline — remove dependência externa)
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-idle
// ==/UserScript==

(async function () {
    'use strict';
    // Inline dynamic loader: carrega módulos em runtime (cache-bust automático)
    if (window.self !== window.top) return;

    const url = window.location.href;
    const isPjeDomain = url.includes('pje.trt2.jus.br') || url.includes('pje1g.trt2.jus.br');

    if (isPjeDomain) {
        const BASE = 'https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/';
        const CB   = '?cb=' + Date.now();
        const MODULES = [
            'core/utils.js',
            'core/state.js',
            'core/extrair.js',
            'modules/lista/lista.timeline.js',
            'modules/lista/lista.check.js',
            'modules/lista/lista.edital.js',
            'modules/lista/lista.pgto.js',
            'modules/atalhos/atalhos.js',
            'modules/atalhos/atalhos.worker.js',
            'ui/painel.js',
            'modules/infojud/infojud.js',
            'modules/sisbajud/core.js',
            'modules/sisbajud/relatorios.js',
            'modules/sisbajud/sisbajud.js',
            'modules/debito/registrar_debito.js',
        ];

        async function loadScript(path) {
            try {
                const res = await fetch(BASE + path + CB);
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const code = await res.text();
                const fn = new Function(code);
                fn();
                console.log('[PJeLoader] loaded:', path);
            } catch (e) {
                console.error('[PJeLoader] Falha ao carregar:', path, e);
            }
        }

        // Carrega em série para respeitar dependências
        for (const path of MODULES) {
            // pequeno await para evitar throttling em alguns ambientes
            // e garantir ordem determinística
            // eslint-disable-next-line no-await-in-loop
            await loadScript(path);
        }

        console.log('[PJeLoader] ✅ Todos os módulos carregados.');
    }

    const isReceita = url.includes('cav.receita.fazenda.gov.br');
    const isSisbajud = url.includes('sisbajud.cnj.jus.br') || url.includes('sisbajud.pdpj.jus.br');
    const isMinutas = url.includes('/comunicacoesprocessuais/minutas');
    const isPagamento = url.includes('/pagamento/') && url.includes('/cadastro');
    const isDetalhe = /\/processo\/\d+\/detalhe/.test(url);
    const isObrigacao = url.includes('/obrigacao-pagar/');

    if (isReceita) return;
    if (isSisbajud) return;

    if (isMinutas) {
        // Bloqueio de execução múltipla
        if (document.documentElement.hasAttribute('data-pjetools-worker')) return;
        document.documentElement.setAttribute('data-pjetools-worker', '1');

        console.log('[Loader] Iniciando Worker Infojud...');
        
        window.addEventListener('load', () => {
            setTimeout(() => {
                // Chama a função exposta no infojud.js refatorado
                if (typeof window.runInfojudWorker === 'function') {
                    window.runInfojudWorker();
                } else {
                    console.error('[Loader] Falha: Módulo Infojud não responde.');
                }
            }, 2500); // Aguarda carregamento do Angular/PJe
        });
        return;
    }

    if (isPagamento) return;
    if (isObrigacao) {
        window.addEventListener('load', () => {
            setTimeout(() => {
                try {
                    if (/\/obrigacao-pagar\/\d+\/cadastro/.test(url)) {
                        if (window.PjeRegistrarDebito && typeof window.PjeRegistrarDebito.onCadastro === 'function') {
                            window.PjeRegistrarDebito.onCadastro();
                        }
                    } else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(url)) {
                        if (window.PjeRegistrarDebito && typeof window.PjeRegistrarDebito.onInclusao === 'function') {
                            window.PjeRegistrarDebito.onInclusao();
                        }
                    }
                } catch (e) { console.error('[Loader] erro ao iniciar PjeRegistrarDebito:', e); }
            }, 600);
        });
        return;
    }
    if (!isDetalhe) return;

    // ── Detalhe: registrar SPA monitor uma vez e inicializar ──────
    if (!window.__pjeToolsLoaded) {
        window.__pjeToolsLoaded = true;

        window.monitorarSPA && window.monitorarSPA(() => {
            window.PJeState && window.PJeState.dispose();
            setTimeout(() => {
                if (/\/processo\/\d+\/detalhe/.test(window.location.href)) {
                    bootDetalhe();
                }
            }, 300);
        });
    }

    bootDetalhe();

    function bootDetalhe() {
        if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) return;
        if (!window.PJeState || window.PJeState._iniciado) return;
        window.PJeState._iniciado = true;
        window.inicializarPainel && window.inicializarPainel();
        window.initAtalhos && window.initAtalhos();
    }
})();
