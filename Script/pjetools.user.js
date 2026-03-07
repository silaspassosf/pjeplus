// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.0.0
// @description  Suite de ferramentas para PJe (Lista + Atalhos + Infojud)
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/*
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/core/utils.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/core/state.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/lista/lista.timeline.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/lista/lista.check.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/lista/lista.edital.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/lista/lista.sibajud.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/lista/lista.sigilo.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/atalhos/atalhos.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/atalhos/atalhos.worker.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/infojud/infojud.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/modules/infojud/infojud.ui.js?v=200
// @require      https://raw.githubusercontent.com/silaspassosf/scp/main/ui/painel.js?v=200
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    if (window.self !== window.top) return;

    const url = window.location.href;

    const isMinutas = /\/comunicacoesprocessuais\/minutas/.test(url);
    const isPagamento = /\/pagamento\/\d+\/cadastro/.test(url);
    const isWorkerTab = isMinutas &&
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
        const currentUrl = window.location.href;
        const onDetalhe = /\/processo\/\d+\/detalhe/.test(currentUrl);

        if (onDetalhe && !PJeState._iniciado) {
            PJeState._iniciado = true;
            inicializarPainel();
            initAtalhos();
        }
    }
})();
