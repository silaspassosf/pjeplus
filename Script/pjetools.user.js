// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.1.6
// @description  Suite de ferramentas para PJe
// @author       Silas
// ── PJe (cobre todas as rotas com um único match)
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
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
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.timeline.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.pgto.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/core.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/relatorios.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbajud.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/debito/registrar_debito.js
// ==/UserScript==

(async function () {
    'use strict';
    if (window.self !== window.top) return;

    // W = window real da página (unsafeWindow quando disponível)
    const W = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

    const url = window.location.href;

    const isReceita  = url.includes('cav.receita.fazenda.gov.br');
    const isSisbajud = url.includes('sisbajud.cnj.jus.br') || url.includes('sisbajud.pdpj.jus.br');
    const isPjeDomain = url.includes('pje.trt2.jus.br') || url.includes('pje1g.trt2.jus.br');

    // (No match da Receita, content scripts já estão via @require em header)
    if (isSisbajud) return;

    // ── Roteamento (roda depois de todos os @require carregados)
    if (isPjeDomain || isReceita) {
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

        // Carrega todos os módulos diretamente, sem loader
        for (const path of MODULES) {
            try {
                const res = await fetch(BASE + path + CB);
                if (!res.ok) throw new Error('HTTP ' + res.status + ' — ' + path);
                const code = await res.text();
                const s = document.createElement('script');
                s.textContent = code;
                document.head.appendChild(s);
                console.log('[PJeTools] ✓', path);
            } catch (e) {
                console.error('[PJeTools] ✗', path, e.message || e);
            }
        }
        console.log('[PJeTools] ✅ Módulos carregados.');

        // ── Roteamento (só roda DEPOIS de tudo carregado)
        const isMinutas  = url.includes('/comunicacoesprocessuais/minutas');
        const isDetalhe  = /\/processo\/\d+\/detalhe/.test(url);
        const isObrigacao = url.includes('/obrigacao-pagar/');

        if (isMinutas) {
            if (document.documentElement.hasAttribute('data-pjetools-worker')) return;
            document.documentElement.setAttribute('data-pjetools-worker', '1');
            console.log('[Loader] Iniciando Worker Infojud...');
            window.addEventListener('load', () => setTimeout(() => {
                W.runInfojudWorker && W.runInfojudWorker();
            }, 2500));
            return;
        }

        if (isObrigacao) {
            setTimeout(() => {
                try {
                    if (/\/obrigacao-pagar\/\d+\/cadastro/.test(url)) {
                        W.PjeRegistrarDebito?.onCadastro();
                    } else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(url)) {
                        W.PjeRegistrarDebito?.onInclusao();
                    }
                } catch (e) { console.error('[Loader] erro ao iniciar PjeRegistrarDebito:', e); }
            }, 1500);
            return;
        }

        if (!isDetalhe) return;

        // ── Detalhe: registrar SPA monitor uma vez e inicializar
        if (!window.__pjeToolsLoaded) {
            window.__pjeToolsLoaded = true;

            window.monitorarSPA && window.monitorarSPA(() => {
                W.PJeState && W.PJeState.dispose();
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
            if (!W.PJeState || W.PJeState._iniciado) return;
            W.PJeState._iniciado = true;
            W.inicializarPainel && W.inicializarPainel();
            W.initAtalhos && W.initAtalhos();
        }
    }
})();
