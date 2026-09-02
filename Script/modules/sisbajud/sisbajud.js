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

    var containerBotoes = null;
    var badgeEl = null;
    var toastTimer = null;

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

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

    async function _resolverSenhaSisb() {
        // 1. Tampermonkey storage (GM_getValue)
        try {
            if (typeof GM_getValue !== 'undefined') {
                var v = GM_getValue('BP_PASS');
                if (v) return String(v);
                v = GM_getValue('sisbajud_senha');
                if (v) return String(v);
            }
        } catch (e) {}

        // 2. Server local (le .env da raiz do projeto, com CORS)
        try {
            var resp = await fetch('http://127.0.0.1:8000/api/env/BP_PASS');
            if (resp.ok) {
                var txt = await resp.text();
                if (txt && txt.trim()) return txt.trim();
            }
        } catch (e) {}
        try {
            var resp = await fetch('http://127.0.0.1:8000/.env');
            if (resp.ok) {
                var txt = await resp.text();
                var m = txt.match(/BP_PASS\s*=\s*(.+)/i);
                if (m && m[1]) return m[1].trim();
            }
        } catch (e) {}

        // 3. Fallback: window globals
        try {
            if (typeof process !== 'undefined' && process && process.env) {
                if (process.env.BP_PASS) return String(process.env.BP_PASS);
                if (process.env.bp_pass) return String(process.env.bp_pass);
            }
        } catch (e) {}

        if (window.__sisbSenha) return String(window.__sisbSenha);
        if (window.BP_PASS) return String(window.BP_PASS);
        if (window.__BP_PASS) return String(window.__BP_PASS);
        if (window.__env && window.__env.BP_PASS) return String(window.__env.BP_PASS);
        if (window.__env && window.__env.bp_pass) return String(window.__env.bp_pass);
        if (window.__ENV__ && window.__ENV__.BP_PASS) return String(window.__ENV__.BP_PASS);
        if (window.__ENV__ && window.__ENV__.bp_pass) return String(window.__ENV__.bp_pass);

        return '';
    }

    // ── Extrair TODAS as ordens da tabela (com valores e situacao) ──
    // Espelha SISB/processamento/ordens_dados.py:_extrair_ordens_da_serie
    function _sisbExtrairTodasOrdens() {
        var container = document.querySelector('SISBAJUD-DETALHES-TEIMOSINHA');
        if (!container) return [];

        var rows = container.querySelectorAll('tbody tr');
        var ordens = [];

        rows.forEach(function(row) {
            var menuBtn = row.querySelector('button.mat-menu-trigger');
            if (!menuBtn) return;

            var cells = row.querySelectorAll('td');
            var sequencial = 0;
            var dataRaw = '';
            var valor = 0;
            var protocolo = '';
            var situacao = '';
            var nome = '';

            cells.forEach(function(cell, idx) {
                var text = (cell.textContent || '').trim().replace(/\u00a0/g, ' ');

                // Sequencial (cols[0])
                if (idx === 0) {
                    var seq = parseInt(text, 10);
                    if (!isNaN(seq)) sequencial = seq;
                }
                // Data (cols[2])
                else if (idx === 2) {
                    dataRaw = text;
                }
                // Valor a bloquear (cols[4])
                else if (idx === 4) {
                    var m = text.match(/R\$\s*([0-9.,]+)/);
                    if (m) {
                        valor = parseFloat(m[1].replace(/\./g, '').replace(',', '.'));
                    }
                }
                // Protocolo (cols[5])
                else if (idx === 5) {
                    if (/^\d{10,}$/.test(text)) protocolo = text;
                }

                // Nome (fallback catch-all)
                if (text.length > 3 && !/^\d{10,}$/.test(text) && !/R\$/.test(text) && text !== 'Detalhar') {
                    if (!nome) nome = text.substring(0, 60);
                }
            });

            // Extrair situacao do texto completo da linha
            var allText = Array.from(cells).map(function(c) { return (c.textContent || '').trim(); }).join(' ');
            if (allText.indexOf('Respondida com minuta') > -1) {
                situacao = 'Respondida com minuta';
            } else if (allText.indexOf('Respondida') > -1) {
                situacao = 'Respondida';
            } else if (allText.indexOf('Não enviado') > -1 || allText.indexOf('Nao enviado') > -1 || allText.indexOf('não enviado') > -1 || allText.indexOf('nao enviado') > -1) {
                situacao = 'Não enviado';
            }

            ordens.push({
                row: row,
                menuBtn: menuBtn,
                sequencial: sequencial,
                dataRaw: dataRaw,
                valor_bloquear: valor,
                protocolo: protocolo,
                situacao: situacao,
                nome: nome
            });
        });

        // Ordenar por sequencial (garantir ordem cronologica)
        ordens.sort(function(a, b) { return a.sequencial - b.sequencial; });

        return ordens;
    }

    // ── Identificar ordens COM BLOQUEIO EFETIVO ──
    // Espelha EXATAMENTE SISB/processamento/ordens_dados.py:_identificar_ordens_com_bloqueio
    // Logica: 1) diferenca valores consecutivos 2) fallback ultima ordem 3) fallback valor total
    var _sisbProtocolosProcessados = {};

    function _sisbPossuiBloqueio(ordem, valorBloqueio) {
        ordem.valor_bloqueio_esperado = valorBloqueio;
        ordem._relatorio = {
            protocolo: ordem.protocolo || 'N/A',
            valor_esperado: valorBloqueio,
            status: 'pendente',
            discriminacao: null
        };
        return ordem;
    }

    function _sisbIdentificarOrdensComBloqueio(ordens) {
        if (!ordens || ordens.length === 0) return [];

        var bloqueios = [];

        // 1 ordem: filtro simples valor > 0.01
        if (ordens.length === 1) {
            if (ordens[0].valor_bloquear > 0.01) {
                bloqueios.push(_sisbPossuiBloqueio(ordens[0], ordens[0].valor_bloquear));
            }
            return bloqueios;
        }

        // 2+ ordens: diferenca de valores consecutivos
        for (var i = 0; i < ordens.length - 1; i++) {
            if (ordens[i].valor_bloquear > ordens[i + 1].valor_bloquear) {
                bloqueios.push(_sisbPossuiBloqueio(ordens[i], ordens[i].valor_bloquear - ordens[i + 1].valor_bloquear));
            }
        }

        // Se nenhuma diferenca detectada, pega a ultima com valor > 0.01
        if (bloqueios.length === 0) {
            for (var j = ordens.length - 1; j >= 0; j--) {
                if (ordens[j].valor_bloquear > 0.01) {
                    bloqueios.push(_sisbPossuiBloqueio(ordens[j], ordens[j].valor_bloquear));
                    break;
                }
            }
        }

        return bloqueios;
    }

    // ── Varrer ordens COM BLOQUEIO (wrapper, espelha series_fluxo.py) ──
    function _sisbObterOrdensComBloqueio() {
        var todas = _sisbExtrairTodasOrdens();
        var bloqueios = _sisbIdentificarOrdensComBloqueio(todas);

        // Filtro pos-identificacao (espelha series_fluxo.py: checa situacao no loop)
        // Remove ja processadas, respondidas e nao enviadas
        bloqueios = bloqueios.filter(function(o) {
            if (_sisbProtocolosProcessados[o.protocolo]) {
                console.log('[SISB Fluxo] Pulando ja processada:', o.protocolo);
                return false;
            }
            if (o.situacao === 'Respondida com minuta') {
                console.log('[SISB Fluxo] Pulando ja respondida (com minuta):', o.protocolo);
                return false;
            }
            if (o.situacao === 'Não enviado') {
                console.log('[SISB Fluxo] Pulando nao enviada:', o.protocolo);
                return false;
            }
            return true;
        });

        return bloqueios;
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
        console.log('[SISB Fluxo] Ordem:', ordem.protocolo, 'tipo:', tipo, 'valor:', ordem.valor_bloquear);

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

        // 6. PROTOCULAR (probe: button.mat-fab.mat-button-base.mat-primary)
        var btnProtocolar = await _sisbWait(function() {
            // Seletor exato do probe: FAB button primary com texto "Protocolar"
            var btns = document.querySelectorAll('button.mat-fab.mat-button-base.mat-primary');
            for (var g = 0; g < btns.length; g++) {
                if ((btns[g].textContent || '').indexOf('Protocolar') > -1 && !btns[g].hasAttribute('disabled')) {
                    return btns[g];
                }
            }
            // Fallback: qualquer botao com "Protocolar"
            var allBtns = document.querySelectorAll('button');
            for (var j = 0; j < allBtns.length; j++) {
                if ((allBtns[j].textContent || '').indexOf('Protocolar') > -1 && !allBtns[j].hasAttribute('disabled')) return allBtns[j];
            }
            return null;
        }, 8000);

        if (btnProtocolar) {
            btnProtocolar.click();
            console.log('[SISB Fluxo] Protocolar clicado');
            await sleep(1500);

            // 7. Modal de senha (probe: mat-dialog-container "Digite sua senha")
            // Aumentar timeout pois o dialog pode demorar para renderizar
            var dialogSenha = await _sisbWait('mat-dialog-container.mat-dialog-container', 8000);
            if (dialogSenha && (dialogSenha.textContent || '').indexOf('senha') > -1) {
                // Campo de senha (probe: input.mat-input-element.mat-form-field-autofill-control)
                var campo_senha = dialogSenha.querySelector('input.mat-input-element');
                if (!campo_senha) campo_senha = dialogSenha.querySelector('input[type="password"]');
                if (!campo_senha) campo_senha = dialogSenha.querySelector('input');

                if (campo_senha) {
                    campo_senha.focus();
                    await sleep(300);

                    var senha = await _resolverSenhaSisb();
                    if (!senha) {
                        console.warn('[SISB Fluxo] Nenhuma senha BP_PASS encontrada; o protocolo pode falhar.');
                    }

                    // Usar execCommand (simula typing real) + fallback nativo para Angular Material
                    // Angular Material (MatInput) escuta Event('input') com inputType
                    campo_senha.select();
                    if (document.execCommand('insertText', false, senha)) {
                        console.log('[SISB Fluxo] Senha digitada via execCommand');
                    } else {
                        // Fallback: nativeInputValueSetter (React/Angular update detector)
                        var nativeSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeSetter.call(campo_senha, senha);
                        campo_senha.dispatchEvent(new Event('input', { bubbles: true }));
                        console.log('[SISB Fluxo] Senha digitada via nativeSetter');
                    }

                    campo_senha.dispatchEvent(new Event('change', { bubbles: true }));
                    await sleep(500);

                    // Confirmar (probe: button.mat-raised-button.mat-button-base.mat-primary)
                    var btnConfirmarSenha = await _sisbWait(function() {
                        var btns = document.querySelectorAll('button.mat-raised-button.mat-button-base.mat-primary');
                        for (var k = 0; k < btns.length; k++) {
                            if ((btns[k].textContent || '').trim() === 'Confirmar') return btns[k];
                        }
                        var allBtns = document.querySelectorAll('button');
                        for (var l = 0; l < allBtns.length; l++) {
                            if ((allBtns[l].textContent || '').indexOf('Confirmar') > -1) return allBtns[l];
                        }
                        return null;
                    }, 6000);
                    if (btnConfirmarSenha) { btnConfirmarSenha.click(); await sleep(3000); }
                }
            } else {
                console.warn('[SISB Fluxo] Modal de senha nao encontrado');
            }

            // 8. Fechar snack de sucesso
            var snackOk = await _sisbWait('button.snack-messenger-close-button', 4000);
            if (snackOk) { snackOk.click(); await sleep(500); }

            // 9. Extrair dados ANTES de voltar (overlay ainda visivel)
            try {
                var dados = await window.SisbCore.extrairDadosBloqueios(ordem.protocolo);
                if (dados && Object.keys(dados.executados).length > 0) {
                    window.SisbCore.agruparDados(dados);
                    console.log('[SISB Fluxo] Dados acumulados');
                }
            } catch(ex) { console.warn('[SISB Fluxo] Erro extracao:', ex); }

            // 10. VOLTAR para a lista (history.back)
            window.history.back();
            await sleep(2000);

            // Aguardar tabela de ordens reaparecer
            await _sisbWait('SISBAJUD-DETALHES-TEIMOSINHA', 10000);
            await sleep(500);
        } else {
            console.warn('[SISB Fluxo] Botao Protocolar nao encontrado — pulando protocolo');
            // Fallback: tenta snack OK + Gerar Recibo (fluxo antigo)
            var snackOkFallback = await _sisbWait('button.snack-messenger-close-button', 3000);
            if (snackOkFallback) { snackOkFallback.click(); await sleep(500); }
            var btnRecibo = await _sisbWait(function() {
                var btns = document.querySelectorAll('button.mat-fab.mat-button-base');
                for (var m = 0; m < btns.length; m++) {
                    if ((btns[m].textContent || '').indexOf('Gerar Recibo') > -1) return btns[m];
                }
                return null;
            }, 4000);
            if (btnRecibo) { btnRecibo.click(); await sleep(1500); }
            window.history.back();
            await sleep(2000);
            await _sisbWait('SISBAJUD-DETALHES-TEIMOSINHA', 10000);
            await sleep(500);
        }

        // Marcar como processada (evita loop infinito no re-scan)
        _sisbProtocolosProcessados[ordem.protocolo] = true;
        return { ok: true };
    }

    // ── Executar fluxo (re-scan apos cada history.back) ──────────────
    async function _sisbExecutarFluxo(tipo) {
        var totalProcessados = 0;

        while (_sisbFluxoAtivo) {
            // Re-scan: apos history.back(), o DOM se renova
            var ordens = _sisbObterOrdensComBloqueio();
            if (ordens.length === 0) break;

            var ordem = ordens[0];
            totalProcessados++;
            _sisbOrdensProcessadas = totalProcessados;

            mostrarToast(totalProcessados + 'ª: ' + (ordem.protocolo || ordem.nome), 'aviso');
            console.log('[SISB Fluxo] Ordem ' + totalProcessados + ':', ordem.protocolo);

            var resultado = await _sisbProcessarOrdem(ordem, tipo);

            if (!resultado.ok) {
                console.warn('[SISB Fluxo] Erro:', ordem.protocolo, resultado.erro);
                mostrarToast('Erro: ' + resultado.erro + ' — continuando...', 'erro');
            }

            // Marcar como processada (sucesso ou erro — evita loop infinito)
            _sisbProtocolosProcessados[ordem.protocolo] = true;

            await sleep(1000);
        }

        _sisbFluxoAtivo = false;
        atualizarBadge();
        var totalFmt = window.SisbCore.formatarValor(window.SisbCore.acumulador.total_geral);
        mostrarToast('Concluido! ' + totalProcessados + ' ordens. Total acumulado: ' + totalFmt, 'ok');
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

    // ── Injetar UI ───────────────────────────────────────────────────
    function injetarUI() {
        var href = window.location.href;
        var isTeimosinhaDetalhes = href.indexOf('/teimosinha/') > -1 && href.indexOf('/detalhes') > -1;
        var isOrdemDesdobrar = href.indexOf('/ordem-judicial/') > -1 && href.indexOf('/desdobrar') > -1;

        var containerAtivo = document.getElementById('pjetools-sisb-container');
        var containerDesdobrar = document.getElementById('pjetools-sisb-desdobrar-container');

        // Lidar com Teimosinha
        if (isTeimosinhaDetalhes) {
            if (containerDesdobrar) containerDesdobrar.style.display = 'none';
            if (containerAtivo) {
                containerAtivo.style.display = 'flex';
                if (!document.getElementById('btn-sisb-transferir')) {
                    containerAtivo.innerHTML = '';
                    _injetarBotoes(containerAtivo);
                }
            } else {
                var container = criarContainer();
                _injetarBotoes(container);
            }
        } else {
            if (containerAtivo) containerAtivo.style.display = 'none';
        }

        // Lidar com Desdobrar
        if (isOrdemDesdobrar) {
            if (containerDesdobrar) {
                containerDesdobrar.style.display = 'flex';
            } else {
                injetarBotoesDesdobrar();
            }
        } else {
            if (containerDesdobrar) containerDesdobrar.style.display = 'none';
        }
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

    // ── Extração Desdobrar (HTML) ────────────────────────────────────
    window._sisbajudDesdobrarState = window._sisbajudDesdobrarState || {
        qtdExtraida: 0,
        protocolos: new Set(),
        bloqueios: {}
    };

    function extrairDesdobrarHtml() {
        var protocolo = '';
        var labels = document.querySelectorAll('.sisbajud-label');
        for (var i = 0; i < labels.length; i++) {
            if (labels[i].textContent.indexOf('Número do Protocolo') > -1) {
                var valSpan = labels[i].nextElementSibling;
                if (valSpan && valSpan.classList.contains('sisbajud-label-valor')) {
                    protocolo = valSpan.textContent.trim();
                    break;
                }
            }
        }
        
        var panels = document.querySelectorAll('mat-expansion-panel');
        var foundAny = false;
        panels.forEach(function(panel) {
            var colReu = panel.querySelector('.col-reu-dados-nome-pessoa');
            var desc = panel.querySelector('.div-description-reu');
            // Verificar se é painel de réu (tem .col-reu)
            if (colReu && desc && panel.querySelector('.col-reu')) {
                var nome = colReu.textContent.trim();
                var textDesc = desc.textContent || '';
                var match = textDesc.match(/R\$\s*([\d\.,]+)/);
                if (match) {
                    var valorStr = match[1];
                    if (valorStr !== '0,00' && valorStr !== '0.00' && valorStr !== '0') {
                        var valorNum = parseFloat(valorStr.replace(/\./g, '').replace(',', '.'));
                        if (!isNaN(valorNum)) {
                            window._sisbajudDesdobrarState.bloqueios[nome] = (window._sisbajudDesdobrarState.bloqueios[nome] || 0) + valorNum;
                        }
                    }
                }
                foundAny = true;
            }
        });
        
        if (protocolo) window._sisbajudDesdobrarState.protocolos.add(protocolo);
        if (foundAny || protocolo) {
            window._sisbajudDesdobrarState.qtdExtraida++;
            return true;
        }
        return false;
    }

    function copyToClipboardHtml(content) {
        var container = document.createElement('div');
        container.innerHTML = content;
        container.style.position = 'absolute';
        container.style.left = '-9999px';
        document.body.appendChild(container);
        
        var range = document.createRange();
        range.selectNodeContents(container);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        
        try {
            var success = document.execCommand('copy');
            document.body.removeChild(container);
            selection.removeAllRanges();
            return success;
        } catch (err) {
            if (document.body.contains(container)) document.body.removeChild(container);
            return false;
        }
    }

    function injetarBotoesDesdobrar() {
        var container = document.createElement('div');
        container.id = 'pjetools-sisb-desdobrar-container';
        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(container);
        
        var btnExtrair = criarBotao('btn-sisb-desdobrar-extrair', '📄 Extrair dados', '#1e88e5', async function() {
            btnExtrair.textContent = 'Extraindo...';
            btnExtrair.style.background = '#f39c12';
            
            await sleep(300); // delay angular
            
            var ok = extrairDesdobrarHtml();
            if (ok) {
                btnExtrair.style.display = 'none';
                
                var btnProx = document.getElementById('btn-sisb-desdobrar-prox');
                if (!btnProx) {
                    btnProx = criarBotao('btn-sisb-desdobrar-prox', 'Extrair próxima', '#f39c12', async function() {
                        btnProx.textContent = 'Extraindo...';
                        await sleep(300);
                        extrairDesdobrarHtml();
                        btnProx.textContent = 'Extrair próxima';
                        var btnFin = document.getElementById('btn-sisb-desdobrar-fin');
                        if (btnFin) btnFin.textContent = '✅ Finalizar (' + window._sisbajudDesdobrarState.qtdExtraida + ')';
                    });
                    container.appendChild(btnProx);
                } else {
                    btnProx.style.display = 'block';
                }
                
                var btnFin = document.getElementById('btn-sisb-desdobrar-fin');
                if (!btnFin) {
                    btnFin = criarBotao('btn-sisb-desdobrar-fin', '✅ Finalizar (' + window._sisbajudDesdobrarState.qtdExtraida + ')', '#27ae60', function() {
                        var _st = window._sisbajudDesdobrarState;
                        var protocolosStr = Array.from(_st.protocolos).join(', ');
                        
                        var pJustifyImp = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';
                        
                        var saida = "";
                        saida += "<p " + pJustifyImp + ">Ordens com bloqueio: <strong>" + (protocolosStr || "Nenhuma") + "</strong></p>";
                        saida += "<p " + pJustifyImp + ">Discriminação de partes e respectivos valores totais<u> já transferidos à conta do juízo</u>:</p>";
                        
                        var somaTotal = 0;
                        for (var nome in _st.bloqueios) {
                            var num = _st.bloqueios[nome];
                            somaTotal += num;
                            var valFormatado = num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                            saida += "<p " + pJustifyImp + ">-" + nome + " - R$ " + valFormatado + "</p>";
                        }
                        
                        var totalFormatado = somaTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        saida += "<p " + pJustifyImp + ">(total de bloqueios esperado na conta judicial, sem considerar atualizações = R$ <strong>" + totalFormatado + "</strong>)<br><br><br data-cke-filler=\"true\"></p>";
                        
                        var okCopy = copyToClipboardHtml(saida);
                        if (okCopy) {
                            btnFin.textContent = 'Copiado!';
                            window._sisbajudDesdobrarState.qtdExtraida = 0;
                            window._sisbajudDesdobrarState.protocolos = new Set();
                            window._sisbajudDesdobrarState.bloqueios = {};
                            setTimeout(function() {
                                btnFin.style.display = 'none';
                                btnProx.style.display = 'none';
                                btnExtrair.textContent = '📄 Extrair dados';
                                btnExtrair.style.background = '#1e88e5';
                                btnExtrair.style.display = 'block';
                            }, 2000);
                        } else {
                            alert('Falha ao copiar html.');
                        }
                    });
                    container.appendChild(btnFin);
                } else {
                    btnFin.style.display = 'block';
                    btnFin.textContent = '✅ Finalizar (' + window._sisbajudDesdobrarState.qtdExtraida + ')';
                }
            } else {
                btnExtrair.textContent = 'Falhou (tente denovo)';
                setTimeout(function(){ 
                    btnExtrair.textContent = '📄 Extrair dados'; 
                    btnExtrair.style.background = '#1e88e5'; 
                }, 2000);
            }
        });
        
        container.appendChild(btnExtrair);
    }

    setInterval(injetarUI, 1500);

})();
