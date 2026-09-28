'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — Orquestrador Principal (Entry Point)
// Coordena os submódulos:
//   - core.js (SisbCore, PjeSisbajudAuto)
//   - relatorios.js (SisbRelatorios)
//   - ordens.js (SisbOrdens)
//   - detalhes.js (SisbDetalhes)
//   - minuta.js (SisbMinuta)
// ═══════════════════════════════════════════════════════════════════

(function() {
    var href = window.location.href;
    if (href.indexOf('sisbajud.cnj.jus.br') === -1 && href.indexOf('sisbajud.pdpj.jus.br') === -1) return;

    var containerBotoes = null;

    function criarContainer() {
        if (containerBotoes) return containerBotoes;
        containerBotoes = document.createElement('div');
        containerBotoes.id = 'pjetools-sisb-container';
        containerBotoes.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(containerBotoes);
        return containerBotoes;
    }

    function injetarUI() {
        var url = window.location.href;

        // 1. Tela de Detalhe da Ordem / Teimosinha
        var isDetalhes = url.indexOf('/detalhe') > -1;
        var isTeimosinhaDetalhes = url.indexOf('/teimosinha/') > -1 && url.indexOf('/detalhes') > -1;

        if (isDetalhes || isTeimosinhaDetalhes) {
            if (window.SisbDetalhes && typeof window.SisbDetalhes.extrairOrdemDetalharAuto === 'function') {
                window.SisbDetalhes.extrairOrdemDetalharAuto();
            }
            if (window.SisbMinuta && typeof window.SisbMinuta.injetarBotaoOrdem2 === 'function') {
                window.SisbMinuta.injetarBotaoOrdem2();
            }
        }

        // 2. Tela de Desdobramento (não precisa de botão extrair, fluxo automático)
        var isDesdobrar = url.indexOf('/desdobramento') > -1 || document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO');
        if (isDesdobrar) {
            var elResidual = document.getElementById('pjetools-sisb-desdobrar-container');
            if (elResidual) elResidual.remove();
        }

        // 3. Tela de Ordens (Transferir / Desbloquear / Reiteração)
        var isTeimosinhaLista = document.querySelector('SISBAJUD-DETALHES-TEIMOSINHA');
        if (isTeimosinhaLista) {
            var container = criarContainer();
            if (window.SisbOrdens && typeof window.SisbOrdens.injetarBotoes === 'function') {
                window.SisbOrdens.injetarBotoes(container);
                window.SisbOrdens.atualizarBadge();
            }
        } else {
            if (containerBotoes) {
                containerBotoes.remove();
                containerBotoes = null;
            }
            var badgeEl = document.getElementById('pjetools-sisb-badge');
            if (badgeEl) badgeEl.style.display = 'none';
        }

        // 4. Tela de Cadastro de Minuta (/minuta/cadastrar)
        var isMinutaCadastrar = url.indexOf('/minuta/cadastrar') > -1;
        if (isMinutaCadastrar) {
            if (window.SisbMinuta && typeof window.SisbMinuta.autoRunMinuta === 'function') {
                window.SisbMinuta.autoRunMinuta();
            }
        }
    }

    // Loops de injeção e observação
    setInterval(injetarUI, 1500);

    setTimeout(function() {
        if (window.SisbMinuta && typeof window.SisbMinuta.autoRunMinuta === 'function') {
            window.SisbMinuta.autoRunMinuta();
        }
    }, 2000);

})();
