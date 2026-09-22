// Script/alvara/utils.js - utilidades, log e constantes compartilhadas.
// Parte do pacote Alvara (alv.user.js). Registra window.Alv.
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});
    const STORAGE_KEY = 'pje_elaboracao_alvara_v1';
    const BUTTON_ID = 'pje-btn-alvara';
    const BUTTON_HOST_ID = 'pje-alvara-button-host';
    const OVERLAY_ID = 'pje-alvara-overlay';

    function isPaginaDetalhe() {
        return /^\/pjekz\/processo\/\d+\/detalhe(?:\/.*)?$/i
            .test(location.pathname);
    }

    // Desativado temporariamente: por enquanto so os logs de extracao ficam ativos.
    function logDiagnostico() { }

    function logAviso(...args) {
        console.warn('[PjeAlvara]', ...args);
    }

    const utils = {
        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        parseMoney(value) {
            if (value === null || value === undefined) return 0;

            let text = String(value)
                .replace(/R\$\s*/gi, '')
                .replace(/\s/g, '')
                .trim();

            if (!text) return 0;

            text = text.replace(/\./g, '').replace(',', '.');

            const number = parseFloat(text);
            return Number.isFinite(number) ? number : 0;
        },

        formatMoney(value) {
            const number = typeof value === 'number'
                ? value
                : utils.parseMoney(value);

            return number.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        },

        moneyWithSymbol(value) {
            return `R$ ${utils.formatMoney(value)}`;
        },

        normalizeText(text) {
            return String(text || '')
                .replace(/\u00a0/g, ' ')
                .replace(/\s{2,}/g, ' ')
                .trim();
        },

        escapeHtml(value) {
            return String(value ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    };

    Alv.utils = utils;
    Alv.log = { diag: logDiagnostico, aviso: logAviso };
    Alv.const = {
        STORAGE_KEY: STORAGE_KEY,
        BUTTON_ID: BUTTON_ID,
        BUTTON_HOST_ID: BUTTON_HOST_ID,
        OVERLAY_ID: OVERLAY_ID
    };
})();
