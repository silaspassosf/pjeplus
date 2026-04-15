// ==UserScript==
// @name         Suite 1
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Orquestrador mínimo de funções.
// @author       Silas
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-idle
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.js
// ==/UserScript==

(function () {
    'use strict';

    if (window.self !== window.top) return;

    const isPjeDomain = location.href.includes('pje.trt2.jus.br') || location.href.includes('pje1g.trt2.jus.br');
    if (!isPjeDomain) return;

    const shouldRun = () => location.href.includes('/comunicacoesprocessuais/minutas');

    const runWorker = () => {
        if (!shouldRun()) return;
        if (window.__infojudWorkerRodando) return;
        if (typeof window.runInfojudWorker !== 'function') {
            console.error('[Infojud Only] runInfojudWorker não encontrado. Verifique @require de infojud.js');
            return;
        }
        window.__infojudWorkerRodando = true;
        console.log('[Infojud Only] Iniciando worker Infojud mínimo');
        setTimeout(() => {
            try {
                window.runInfojudWorker();
            } catch (err) {
                console.error('[Infojud Only] Falha ao iniciar runInfojudWorker:', err);
            } finally {
                window.__infojudWorkerRodando = false;
            }
        }, 1500);
    };

    const checkRoute = () => {
        if (shouldRun()) runWorker();
    };

    const hookHistory = (original) => function (...args) {
        const returnValue = original.apply(this, args);
        setTimeout(checkRoute, 100);
        return returnValue;
    };

    history.pushState = hookHistory(history.pushState.bind(history));
    history.replaceState = hookHistory(history.replaceState.bind(history));
    window.addEventListener('popstate', () => setTimeout(checkRoute, 100));

    checkRoute();
})();
