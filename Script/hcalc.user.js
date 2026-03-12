// ==UserScript==
// @name         HomologaÃ§Ã£o de CÃ¡lculos
// @namespace    http://tampermonkey.net/
// @version      3.1.9
// @description  Assistente de homologaÃ§Ã£o PJe-Calc
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @updateURL    https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/hcalc.user.js
// @downloadURL  https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/hcalc.user.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js

// ====== REFATORADO (LOAD MODULAR) ======
// carregar mÃ³dulos refatorados (overlay dividido)
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-core.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-pdf.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-prep.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-draft.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-depositos.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-responsabilidades.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-partes.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-decisao.js?v=319&t=202603122050
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay.js?v=319&t=202603122050

// @connect      cdnjs.cloudflare.com
// @connect      raw.githubusercontent.com
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==

(function () {
    'use strict';

    // Anti-iframe
    if (window.self !== window.top) return;

    // Evitar dupla execuÃ§Ã£o
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

    // Chama init do overlay/botÃ£o depois que o PJe estiver pronto
    aguardarPJe(function () {
        console.log('[hcalc] boot callback disparado. hcalcInitBotao =', typeof window.hcalcInitBotao);
        if (typeof window.hcalcInitBotao === 'function') {
            window.hcalcInitBotao();
        } else {
            console.error('[hcalc] hcalcInitBotao nÃ£o encontrado â€” verifique @require e se hcalc-overlay.js expÃµe window.hcalcInitBotao');
        }
    });
})();

