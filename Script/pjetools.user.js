// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.0.7
// @description  Suite de ferramentas para PJe (Lista + Atalhos + Infojud)
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt2.jus.br/pjekz/processo/*/comunicacoesprocessuais/minutas*
// @match        https://pje.trt2.jus.br/pjekz/pagamento/*/cadastro*
// @match        https://sisbajud.cnj.jus.br/*
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp*
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.timeline.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.pgto.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.legacy.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/core.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/relatorios.js?v=221
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbajud.js?v=221
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

    const isReceita = url.includes('cav.receita.fazenda.gov.br');
    const isSisbajud = url.includes('sisbajud.cnj.jus.br') || url.includes('sisbajud.pdpj.jus.br');
    const isMinutas = url.includes('/comunicacoesprocessuais/minutas');
    const isPagamento = url.includes('/pagamento/') && url.includes('/cadastro');
    const isDetalhe = /\/processo\/\d+\/detalhe/.test(url);

    if (isReceita) return;
    if (isSisbajud) return;

    if (isMinutas) {
        if (new URLSearchParams(location.search).get('maispje_worker') === '1') {
            if (document.documentElement.hasAttribute('data-pjetools-worker')) return;
            document.documentElement.setAttribute('data-pjetools-worker', '1');
            window.addEventListener('load', () =>
                setTimeout(() => window.runWorker && window.runWorker(), 2000));
        }
        return;
    }

    if (isPagamento) return;
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
