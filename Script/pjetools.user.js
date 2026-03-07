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
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.timeline.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.sibajud.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.legacy.js?v=204
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js?v=204
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

        // Ignora boot do painel se estiver em domínios extrínsecos
        if (currentUrl.includes('sisbajud.cnj.jus.br') || currentUrl.includes('cav.receita.fazenda.gov.br')) {
            return;
        }

        // Garante que o painel só injeta se a URL pertencer ao TRT2 e for estritamente a aba de detalhes
        const isPJe = currentUrl.includes('pje.trt2.jus.br');
        const isAbaDetalhe = /\/processo\/\d+\/detalhe/.test(currentUrl) && !currentUrl.includes('/minutas');

        if (isPJe && isAbaDetalhe && !PJeState._iniciado) {
            PJeState._iniciado = true;
            inicializarPainel();
            initAtalhos();
        }
    }
})();
