// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.17.0
// @description  Assistente de homologação PJe-Calc (loader @require — Estratégia 2)
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/calc/hcalc-core.js?v=118
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/calc/hcalc-pdf.js?v=118
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/calc/hcalc-overlay.js?v=118
// @connect      cdnjs.cloudflare.com
// @connect      raw.githubusercontent.com
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==

(function () {
    'use strict';

    // Anti-iframe
    if (window.self !== window.top) return;

    // Evitar dupla execução
    if (document.documentElement.getAttribute('data-hcalc-boot')) return;
    document.documentElement.setAttribute('data-hcalc-boot', '1');

    // Aguarda Angular/DOM do PJe estabilizar
    function aguardarPJe(cb, tentativas) {
        tentativas = tentativas || 0;
        if (tentativas > 40) return; // timeout ~8s

        var pronto =
            document.querySelector('pje-cabecalho') ||
            document.querySelector('li.tl-item-container') ||
            document.querySelector('[class*="processo"]');

        if (pronto) {
            cb();
        } else {
            setTimeout(function () {
                aguardarPJe(cb, tentativas + 1);
            }, 200);
        }
    }

    // Chama init do overlay/botão depois que o PJe estiver pronto
    aguardarPJe(function () {
        if (window.hcalcInitBotao) {
            window.hcalcInitBotao();
        } else {
            console.error('[hcalc] hcalcInitBotao não encontrado — verifique @require / ordem dos arquivos');
        }
    });
})();
