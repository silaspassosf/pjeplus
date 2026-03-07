// ==UserScript==
// @name         PJeTools — Orquestrador
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Infojud + Lista Geral + Atalhos integrados com boas práticas
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt2.jus.br/pjekz/processo/*/comunicacoesprocessuais/minutas*
// @match        https://pje.trt2.jus.br/pjekz/pagamento/*/cadastro*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    if (window.self !== window.top) return;

    const url = window.location.href;

    const isMinutas    = /\/comunicacoesprocessuais\/minutas/.test(url);
    const isPagamento  = /\/pagamento\/\d+\/cadastro/.test(url);
    const isWorkerTab  = isMinutas &&
        new URLSearchParams(location.search).get('maispje_worker') === '1';

    if (isPagamento) {
        waitElement('mat-card').then(() => {
            console.log('[PJeTools] Página de pagamento detectada');
        });
        return;
    }

    if (isWorkerTab) {
        if (document.documentElement.hasAttribute('data-pjetools-worker')) return;
        document.documentElement.setAttribute('data-pjetools-worker', '1');
        window.addEventListener('load', () => setTimeout(runWorker, 2000));
        return;
    }

    if (!antiDuplicacao('data-pjetools-boot')) return;

    monitorarSPA(() => {
        PJeState.dispose();
        setTimeout(boot, 300);
    });

    boot();

    function boot() {
        if (!antiDuplicacao('data-pjetools-boot')) return;

        const currentUrl = window.location.href;
        const onDetalhe = /\/processo\/\d+\/detalhe/.test(currentUrl);

        if (onDetalhe && !PJeState._iniciado) {
            PJeState._iniciado = true;
            inicializarPainel();
            initAtalhos();
        }
    }

})();