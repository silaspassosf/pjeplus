'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — protocolos.js (botão "Copiar protocolo")
// Onde: https://sisbajud.pdpj.jus.br/minuta (e também o host cnj)
// O que faz, ao clicar:
//   1. Lê a dialog "Relação de protocolos" (h1.h1-title + .span-protocolo)
//   2. Copia os protocolos — só os números, separados por ';' — para a
//      área de transferência
//   3. O botão vira "Copiado!" por 2s
//   4. Clica em "Voltar" para fechar a dialog
// Injetado pelo orquestrador (sisbajud.js → injetarUI), sem timer próprio.
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.SisbProtocolos) return;

    var ID_BOTAO = 'pjetools-sisb-protocolos';
    var TEXTO_PADRAO = 'Copiar protocolo';

    function hostSisbajud() {
        var h = window.location.hostname || '';
        return h.indexOf('sisbajud.') === 0;
    }

    function naRotaMinuta() {
        var p = window.location.pathname || '';
        return p === '/minuta' || p === '/minuta/';
    }

    // ── Clipboard: GM_setClipboard → navigator.clipboard → textarea ──
    function copiarFallback(texto) {
        try {
            var ta = document.createElement('textarea');
            ta.value = texto;
            ta.style.cssText = 'position:fixed;top:-1000px;left:-1000px;opacity:0;';
            document.body.appendChild(ta);
            ta.select();
            var ok = document.execCommand('copy');
            ta.remove();
            return ok;
        } catch (e) {
            return false;
        }
    }

    function copiar(texto) {
        return new Promise(function (resolve) {
            try {
                if (typeof GM_setClipboard === 'function') {
                    GM_setClipboard(texto, 'text');
                    return resolve(true);
                }
            } catch (e) { /* segue */ }

            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(texto).then(
                        function () { resolve(true); },
                        function () { resolve(copiarFallback(texto)); }
                    );
                    return;
                }
            } catch (e) { /* segue */ }

            resolve(copiarFallback(texto));
        });
    }

    // ── Leitura da dialog ────────────────────────────────────────────
    function acharDialogProtocolos() {
        var titulos = document.querySelectorAll('h1.h1-title');
        for (var i = 0; i < titulos.length; i++) {
            if ((titulos[i].textContent || '').indexOf('Relação de protocolos') > -1) {
                return titulos[i].closest('form') || titulos[i].parentElement;
            }
        }
        var span = document.querySelector('.span-protocolo');
        if (span) return span.closest('form') || span.parentElement;
        return null;
    }

    function lerProtocolos(escopo) {
        var spans = escopo.querySelectorAll('.span-protocolo');
        var nums = [];
        for (var i = 0; i < spans.length; i++) {
            var n = (spans[i].textContent || '').replace(/\D+/g, '');
            if (n) nums.push(n);
        }
        return nums;
    }

    function clicarVoltar(escopo) {
        var area = escopo.querySelector('.mat-dialog-actions') || escopo;
        var botoes = area.querySelectorAll('button');
        for (var i = 0; i < botoes.length; i++) {
            if (((botoes[i].textContent || '').trim().toLowerCase()) === 'voltar') {
                botoes[i].click();
                return true;
            }
        }
        return false;
    }

    // ── Ação do botão ────────────────────────────────────────────────
    function avisar(btn, texto, ms) {
        btn.textContent = texto;
        setTimeout(function () { btn.textContent = TEXTO_PADRAO; }, ms || 2000);
    }

    function aoClicar(btn) {
        var dlg = acharDialogProtocolos();
        if (!dlg) return avisar(btn, 'Dialog não encontrada');

        var nums = lerProtocolos(dlg);
        if (!nums.length) return avisar(btn, 'Nenhum protocolo');

        copiar(nums.join(';')).then(function (ok) {
            if (!ok) return avisar(btn, 'Falha ao copiar');
            avisar(btn, 'Copiado!', 2000);
            setTimeout(function () { clicarVoltar(dlg); }, 250);
        });
    }

    // ── Injeção do botão (inferior direito) ──────────────────────────
    function injetarBotao() {
        if (!hostSisbajud() || !document.body) return;

        var existente = document.getElementById(ID_BOTAO);
        if (!naRotaMinuta()) {
            if (existente) existente.remove();
            return;
        }
        if (existente) return;

        var btn = document.createElement('button');
        btn.id = ID_BOTAO;
        btn.type = 'button';
        btn.textContent = TEXTO_PADRAO;
        btn.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;' +
            'padding:10px 18px;border:none;border-radius:8px;background:#1976d2;color:#fff;' +
            'font:bold 14px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
        btn.addEventListener('click', function () { aoClicar(btn); });
        document.body.appendChild(btn);
    }

    window.SisbProtocolos = {
        injetarBotao: injetarBotao,
        lerProtocolos: function () {
            var dlg = acharDialogProtocolos();
            return dlg ? lerProtocolos(dlg) : [];
        }
    };
})();
