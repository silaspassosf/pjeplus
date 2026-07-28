'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — Botões Transferir / Desbloquear (teimosinha/*/detalhes)
// Baseado em SISB/processamento/ordens_acao.py + probe SISBAJUD
// Requer: core.js (SisbCore), relatorios.js (SisbRelatorios)
// ═══════════════════════════════════════════════════════════════════

(function() {
if (window.location.href.indexOf('sisbajud.cnj.jus.br') === -1 && window.location.href.indexOf('sisbajud.pdpj.jus.br') === -1) return;

    var _sisbFluxoAtivo = false;
    var _sisbFluxoTipo = null;
    var _sisbOrdensProcessadas = 0;
    var _sisbTotalOrdens = 0;

    // ── UI ───────────────────────────────────────────────────────────
    var containerBotoes = null;
    var badgeEl = null;
    var toastTimer = null;

    function atualizarBadge() {
        var numExec = Object.keys(window.SisbCore.acumulador.executados).length;
        if (!badgeEl) {
            badgeEl = document.createElement('div');
            badgeEl.id = 'pjetools-sisb-badge';
            badgeEl.style.cssText = 'position:fixed;bottom:160px;right:20px;z-index:999998;background:#1b1b2f;color:#e0e0e0;padding:8px 14px;border-radius:6px;font-size:12px;font-family:sans-serif;font-weight:bold;box-shadow:0 3px 10px rgba(0,0,0,0.3);border-left:4px solid #2196f3;display:none;';
            document.body.appendChild(badgeEl);
        }
        if (numExec === 0) { badgeEl.style.display = 'none'; return; }
        var total = window.SisbCore.formatarValor(window.SisbCore.acumulador.total_geral);
        badgeEl.textContent = numExec + ' executados | Total: ' + total;
        badgeEl.style.display = 'block';
    }

    function mostrarToast(mensagem, tipo) {
        var prev = document.getElementById('pjetools-sisb-toast');
        if (prev) prev.remove();
        if (toastTimer) clearTimeout(toastTimer);
        var toast = document.createElement('div');
        toast.id = 'pjetools-sisb-toast';
        var cores = { ok: '#28a745', erro: '#dc3545', aviso: '#ffc107' };
        var icones = { ok: '✅', erro: '❌', aviso: '⚠' };
        toast.style.cssText = 'position:fixed;bottom:160px;right:20px;z-index:9999999;background:' + (cores[tipo] || '#333') + ';color:#fff;padding:10px 16px;border-radius:6px;font-size:13px;font-family:sans-serif;max-width:360px;box-shadow:0 4px 14px rgba(0,0,0,0.3);transition:opacity 0.3s;opacity:1;';
        toast.textContent = (icones[tipo] || '') + ' ' + mensagem;
        document.body.appendChild(toast);
        toastTimer = setTimeout(function() {
            toast.style.opacity = '0';
            setTimeout(function() { if (toast.parentNode) toast.remove(); }, 300);
        }, tipo === 'erro' ? 5000 : 3000);
    }

    function criarContainer() {
        if (containerBotoes) return containerBotoes;
        containerBotoes = document.createElement('div');
        containerBotoes.id = 'pjetools-sisb-container';
        containerBotoes.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(containerBotoes);
        return containerBotoes;
    }

    function criarBotao(id, texto, cor, onclick) {
        var btn = document.createElement('button');
        btn.id = id;
        btn.textContent = texto;
        btn.style.cssText = 'background:' + cor + ';color:#fff;border:none;border-radius:4px;padding:10px 16px;font-weight:bold;font-size:13px;cursor:pointer;box-shadow:0 3px 8px rgba(0,0,0,0.25);transition:transform 0.2s,box-shadow 0.2s;min-width:200px;text-align:left;';
        btn.onmouseover = function() { btn.style.transform = 'translateY(-2px)'; btn.style.boxShadow = '0 5px 12px rgba(0,0,0,0.35)'; };
        btn.onmouseout = function() { btn.style.transform = 'translateY(0)'; btn.style.boxShadow = '0 3px 8px rgba(0,0,0,0.25)'; };
        btn.onclick = onclick;
        return btn;
    }

    var _resetClickTime = 0;
    async function resetarDados() {
        var agora = Date.now();
        if (agora - _resetClickTime > 1500) {
            _resetClickTime = agora;
            mostrarToast('Clique novamente em Reset para confirmar', 'aviso');
            return;
        }
        _resetClickTime = 0;
        window.SisbCore.reset();
        mostrarToast('Dados resetados!', 'ok');
        atualizarBadge();
    }

    // ── Helpers ──────────────────────────────────────────────────────
    async function _sisbWait(selectorOrFn, timeoutMs) {
        timeoutMs = timeoutMs || 10000;
        var start = Date.now();
        while (Date.now() - start < timeoutMs) {
            var el;
            if (typeof selectorOrFn === 'function') { el = selectorOrFn(); }
            else { el = document.querySelector(selectorOrFn); }
            if (el) return el;
            await sleep(200);
        }
        return null;
    }

    async function _sisbClick(selectorOrEl, timeoutMs) {
        timeoutMs = timeoutMs || 5000;
        var el = typeof selectorOrEl === 'string' ? await _sisbWait(selectorOrEl, timeoutMs) : selectorOrEl;
        if (!el) { console.warn('[SISB] Elemento nao encontrado:', selectorOrEl); return false; }
        try { el.scrollIntoView({ block: 'center', behavior: 'instant' }); } catch(e) {}
        await sleep(300);
        el.click();
        return true;
    }

    // ── Varrer ordens COM BLOQUEIO (inspirado em SISB/_identificar_ordens_com_bloqueio) ──
    function _sisbObterOrdensComBloqueio() {
        var container = document.querySelector('SISBAJUD-DETALHES-TEIMOSINHA');
        if (!container) return [];
        var rows = container.querySelectorAll('tbody tr');
        var ordens = [];

        rows.forEach(function(row) {
            var menuBtn = row.querySelector('button.mat-menu-trigger');
            if (!menuBtn) return;

            var cells = row.querySelectorAll('td');
            var protocolo = '';
            var valor = 0;
            var nome = '';

            cells.forEach(function(cell) {
                var text = (cell.textContent || '').trim();
                if (/^\d{10,}$/.test(text)) protocolo = text;
                var m = text.match(/R\$\s*([0-9.,]+)/);
                if (m) valor = parseFloat(m[1].replace(/\./g, '').replace(',', '.'));
                if (text.length > 3 && !/^\d{10,}$/.test(text) && !/R\$/.test(text) && text !== 'Detalhar') {
                    if (!nome) nome = text.substring(0, 60);
                }
            });

            // ── FILTRO: só ordens com bloqueio efetivo (> 0,01) ──
            // Espelha _identificar_ordens_com_bloqueio + JS_SELS do ordens_acao.py
            if (valor <= 0.01) return;

            ordens.push({ row: row, menuBtn: menuBtn, protocolo: protocolo, valor: valor, nome: nome });
        });

        return ordens;
    }

    // ── Selecionar ação nos dropdowns com-saldo (inspirado em _aplicar_acao_por_fluxo) ──
    async function _sisbSelecionarAcao(overlay, tipo) {
        // Espelha JS_SELS: filtra selects em painéis com saldo (com-acoes, sem nao-resposta)
        var selects = overlay.querySelectorAll('mat-select[name="assessor"]');
        if (!selects || selects.length === 0) {
            // Fallback: qualquer mat-select no overlay
            selects = overlay.querySelectorAll('mat-select[role="listbox"], mat-select[role="combobox"]');
        }

        var textoAlvo = tipo === 'transferir' ? 'Transferir valor' : 'Desbloquear valor';
        var processados = 0;

        for (var i = 0; i < selects.length; i++) {
            var sel = selects[i];

            // Pular selects em painéis sem saldo (com-acoes-nao-resposta ou collapsed)
            var panelBody = sel.closest('.mat-expansion-panel-body');
            if (panelBody) {
                if (panelBody.querySelector('.com-acoes-nao-resposta')) continue;
                if (!panelBody.querySelector('.com-acoes')) continue;
                // Verificar saldo (espelha JS_SELS: saldo 0,01 → pular)
                var saldoCell = panelBody.querySelector('td.cdk-column-saldoRemanescente');
                if (saldoCell && (saldoCell.textContent || '').indexOf('0,01') > -1) continue;
            }

            sel.click();
            await sleep(700);

            var opcoes = document.querySelectorAll('mat-option[role="option"].mat-option');
            var opcaoAlvo = null;

            // Match exato primeiro
            for (var j = 0; j < opcoes.length; j++) {
                if ((opcoes[j].textContent || '').trim() === textoAlvo) { opcaoAlvo = opcoes[j]; break; }
            }
            // Match parcial
            if (!opcaoAlvo) {
                for (var k = 0; k < opcoes.length; k++) {
                    if ((opcoes[k].textContent || '').toLowerCase().indexOf(textoAlvo.toLowerCase()) > -1) {
                        opcaoAlvo = opcoes[k]; break;
                    }
                }
            }

            if (opcaoAlvo) {
                opcaoAlvo.click();
                processados++;
                await sleep(300);
            } else {
                document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
                await sleep(200);
            }
        }

        return processados > 0;
    }

    // ── Processar uma ordem individual ───────────────────────────────
    async function _sisbProcessarOrdem(ordem, tipo) {
        console.log('[SISB Fluxo] Ordem:', ordem.protocolo, 'tipo:', tipo, 'valor:', ordem.valor);

        // 1. Menu 3 pontinhos → "Detalhar"
        await _sisbClick(ordem.menuBtn);
        await sleep(600);

        var detalharBtn = await _sisbWait(function() {
            var items = document.querySelectorAll('button[role="menuitem"].mat-menu-item');
            for (var i = 0; i < items.length; i++) {
                if ((items[i].textContent || '').trim() === 'Detalhar') return items[i];
            }
            return null;
        }, 3000);

        if (!detalharBtn) {
            document.body.click();
            return { ok: false, erro: 'Menu Detalhar nao encontrado' };
        }
        detalharBtn.click();
        await sleep(2000);

        // 2. Aguardar overlay SISBAJUD-INCLUSAO-DESDOBRAMENTO
        var overlay = await _sisbWait('SISBAJUD-INCLUSAO-DESDOBRAMENTO', 12000);
        if (!overlay) return { ok: false, erro: 'Overlay de desdobramento nao abriu' };

        // 3. Selecionar ação nos dropdowns com-saldo (NÃO definir valor manualmente)
        await _sisbSelecionarAcao(overlay, tipo);
        await sleep(500);

        // 4. Salvar (botão com ícone fa-save, igual SISB/scripts/salvar_minuta.js)
        var btnSalvar = await _sisbWait(function() {
            var iconSave = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save');
            if (iconSave) return iconSave.closest('button');
            var allBtns = document.querySelectorAll('button');
            for (var c = 0; c < allBtns.length; c++) {
                if ((allBtns[c].textContent || '').trim() === 'Salvar' && !allBtns[c].hasAttribute('disabled')) return allBtns[c];
            }
            return null;
        }, 8000);
        if (!btnSalvar) return { ok: false, erro: 'Botao Salvar nao encontrado' };
        btnSalvar.click();
        await sleep(2500);

        // 5. Se TRANSFERIR: modal "Dados para Depósito Judicial (Transferência)"
        if (tipo === 'transferir') {
            var dialog = await _sisbWait('mat-dialog-container[role="dialog"], mat-dialog-container.mat-dialog-container', 8000);
            if (dialog) {
                var dialogText = dialog.textContent || '';
                console.log('[SISB Fluxo] Dialog:', dialogText.substring(0, 80));

                if (dialogText.indexOf('Depósito Judicial') > -1 || dialogText.indexOf('Transferência') > -1) {
                    // Preencher selects do modal (instituição financeira, etc.)
                    var selectsModal = dialog.querySelectorAll('mat-select');
                    for (var s = 0; s < selectsModal.length; s++) {
                        try {
                            selectsModal[s].click();
                            await sleep(500);
                            var opts = document.querySelectorAll('mat-option[role="option"]');
                            for (var o = 0; o < opts.length; o++) {
                                var txt = (opts[o].textContent || '').trim();
                                if (txt && txt !== 'Selecione') { opts[o].click(); break; }
                            }
                            await sleep(300);
                        } catch(e) {}
                    }

                    // Confirmar (button.mat-raised-button.mat-button-base.mat-primary)
                    var btnConfirmar = await _sisbWait(function() {
                        var btns = document.querySelectorAll('button.mat-raised-button.mat-button-base.mat-primary');
                        for (var d = 0; d < btns.length; d++) {
                            if ((btns[d].textContent || '').trim() === 'Confirmar') return btns[d];
                        }
                        var allBtns2 = document.querySelectorAll('button');
                        for (var e = 0; e < allBtns2.length; e++) {
                            if ((allBtns2[e].textContent || '').indexOf('Confirmar') > -1) return allBtns2[e];
                        }
                        return null;
                    }, 8000);
                    if (btnConfirmar) { btnConfirmar.click(); await sleep(2000); }
                }
            }
        }

        // 6. Fechar snack OK
        var snackOk = await _sisbWait('button.snack-messenger-close-button', 4000);
        if (snackOk) { snackOk.click(); await sleep(500); }

        // 7. Gerar Recibo (protocola)
        var btnRecibo = await _sisbWait(function() {
            var btns = document.querySelectorAll('button.mat-fab.mat-button-base');
            for (var f = 0; f < btns.length; f++) {
                if ((btns[f].textContent || '').indexOf('Gerar Recibo') > -1) return btns[f];
            }
            return null;
        }, 6000);
        if (btnRecibo) { btnRecibo.click(); await sleep(1500); }

        // 8. Extrair dados e acumular (passa protocolo da tabela)
        try {
            var dados = await window.SisbCore.extrairDadosBloqueios(ordem.protocolo);
            if (dados && Object.keys(dados.executados).length > 0) {
                window.SisbCore.agruparDados(dados);
                console.log('[SISB Fluxo] Dados acumulados');
            }
        } catch(ex) { console.warn('[SISB Fluxo] Erro extracao:', ex); }

        return { ok: true };
    }

    // ── Executar fluxo ───────────────────────────────────────────────
    async function _sisbExecutarFluxo(tipo) {
        var ordens = _sisbObterOrdensComBloqueio();
        _sisbTotalOrdens = ordens.length;

        if (ordens.length === 0) {
            mostrarToast('Nenhuma ordem com bloqueio (> R$ 0,01) encontrada na tabela', 'aviso');
            return;
        }

        mostrarToast('Iniciando ' + tipo + ' de ' + ordens.length + ' ordens...', 'ok');
        console.log('[SISB Fluxo] Ordens com bloqueio:', ordens.length);

        for (var i = 0; i < ordens.length; i++) {
            if (!_sisbFluxoAtivo) break;

            var ordem = ordens[i];
            _sisbOrdensProcessadas = i + 1;

            mostrarToast((i + 1) + '/' + ordens.length + ': ' + (ordem.protocolo || ordem.nome), 'aviso');

            var resultado = await _sisbProcessarOrdem(ordem, tipo);

            if (!resultado.ok) {
                console.warn('[SISB Fluxo] Erro:', ordem.protocolo, resultado.erro);
                mostrarToast('Erro: ' + resultado.erro + ' — continuando...', 'erro');
            }

            await sleep(1500);
        }

        _sisbFluxoAtivo = false;
        atualizarBadge();
        var totalFmt = window.SisbCore.formatarValor(window.SisbCore.acumulador.total_geral);
        mostrarToast('Concluido! ' + _sisbOrdensProcessadas + ' ordens. Total acumulado: ' + totalFmt, 'ok');
    }

    // ── Transferir ───────────────────────────────────────────────────
    async function _sisbFluxoTransferir() {
        var btn = document.getElementById('btn-sisb-transferir');
        var isConsolidar = btn && (btn.textContent || '').indexOf('Consolidar') > -1;

        if (isConsolidar) {
            await _sisbConsolidarRelatorio();
            return;
        }

        _sisbFluxoAtivo = true;
        _sisbFluxoTipo = 'transferir';
        _sisbOrdensProcessadas = 0;

        btn.textContent = '⏳ Transferindo...';
        btn.style.background = '#bf360c';
        btn.disabled = true;

        var btnDesbloq = document.getElementById('btn-sisb-desbloquear');
        if (btnDesbloq) btnDesbloq.style.display = 'none';

        await _sisbExecutarFluxo('transferir');

        btn.textContent = '📊 Consolidar Relatório';
        btn.style.background = '#4caf50';
        btn.disabled = false;
    }

    // ── Desbloquear ──────────────────────────────────────────────────
    async function _sisbFluxoDesbloquear() {
        var btn = document.getElementById('btn-sisb-desbloquear');

        _sisbFluxoAtivo = true;
        _sisbFluxoTipo = 'desbloquear';
        _sisbOrdensProcessadas = 0;

        btn.textContent = '⏳ Desbloqueando...';
        btn.style.background = '#bf360c';
        btn.disabled = true;

        var btnTransf = document.getElementById('btn-sisb-transferir');
        if (btnTransf) btnTransf.style.display = 'none';

        await _sisbExecutarFluxo('desbloquear');

        btn.textContent = '🔓 Desbloquear';
        btn.style.background = '#d84315';
        btn.disabled = false;

        if (btnTransf) btnTransf.style.display = '';
    }

    // ── Consolidar Relatório ─────────────────────────────────────────
    async function _sisbConsolidarRelatorio() {
        var numExec = Object.keys(window.SisbCore.acumulador.executados).length;
        if (numExec === 0) {
            mostrarToast('Nenhum dado acumulado para gerar relatorio', 'aviso');
            return;
        }

        try {
            var resultado = await window.SisbRelatorios.gerarECopiarDetalhado();
            mostrarToast(resultado.mensagem, 'ok');

            var btn = document.getElementById('btn-sisb-transferir');
            if (btn) { btn.textContent = '💸 Transferir'; btn.style.background = '#e65100'; }

            var btnDesbloq = document.getElementById('btn-sisb-desbloquear');
            if (btnDesbloq) btnDesbloq.style.display = '';

            window.SisbCore.reset();
            atualizarBadge();

        } catch (err) {
            mostrarToast('Erro ao gerar relatorio: ' + err.message, 'erro');
        }
    }

    // ── Injetar UI (apenas teimosinha/*/detalhes) ────────────────────
    function injetarUI() {
        var isTeimosinhaDetalhes = window.location.href.indexOf('/teimosinha/') > -1 && window.location.href.indexOf('/detalhes') > -1;
        var containerAtivo = document.getElementById('pjetools-sisb-container');

        if (!isTeimosinhaDetalhes) {
            if (containerAtivo) containerAtivo.style.display = 'none';
            return;
        }

        if (containerAtivo) {
            containerAtivo.style.display = 'flex';
            if (!document.getElementById('btn-sisb-transferir')) {
                containerAtivo.innerHTML = '';
                _injetarBotoes(containerAtivo);
            }
            return;
        }

        var container = criarContainer();
        _injetarBotoes(container);
    }

    function _injetarBotoes(container) {
        var btnTransferir = criarBotao('btn-sisb-transferir', '💸 Transferir', '#e65100', _sisbFluxoTransferir);
        container.appendChild(btnTransferir);

        var btnDesbloquear = criarBotao('btn-sisb-desbloquear', '🔓 Desbloquear', '#d84315', _sisbFluxoDesbloquear);
        container.appendChild(btnDesbloquear);

        var btnReset = criarBotao('btn-sisb-reset', '🔄 Reset', '#757575', resetarDados);
        btnReset.style.fontSize = '11px';
        btnReset.style.padding = '6px 12px';
        btnReset.style.minWidth = '100px';
        btnReset.style.textAlign = 'center';
        container.appendChild(btnReset);

        atualizarBadge();
        console.log('[SISB] Botoes injetados: Transferir + Desbloquear');
    }

    setInterval(injetarUI, 1500);

})();
