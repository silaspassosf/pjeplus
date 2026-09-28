'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — Módulo Ordens (Transferir / Desbloquear / Reiteração)
// Baseado em SISB/processamento/ordens_acao.py + probe SISBAJUD
// Requer: core.js (SisbCore), relatorios.js (SisbRelatorios)
// ═══════════════════════════════════════════════════════════════════

(function() {
    if (window.location.href.indexOf('sisbajud.cnj.jus.br') === -1 && window.location.href.indexOf('sisbajud.pdpj.jus.br') === -1) return;

    var _sisbFluxoAtivo = false;
    var _sisbFluxoTipo = null;
    var _sisbOrdensProcessadas = 0;
    var _sisbTotalOrdens = 0;
    var badgeEl = null;

    const C = window.SisbCore;

    function atualizarBadge() {
        var numExec = Object.keys(C.acumulador.executados).length;
        if (!badgeEl) {
            badgeEl = document.createElement('div');
            badgeEl.id = 'pjetools-sisb-badge';
            badgeEl.style.cssText = 'position:fixed;bottom:160px;right:20px;z-index:999998;background:#1b1b2f;color:#e0e0e0;padding:8px 14px;border-radius:6px;font-size:12px;font-family:sans-serif;font-weight:bold;box-shadow:0 3px 10px rgba(0,0,0,0.3);border-left:4px solid #2196f3;display:none;';
            document.body.appendChild(badgeEl);
        }
        if (numExec === 0) { badgeEl.style.display = 'none'; return; }
        var total = C.formatarValor(C.acumulador.total_geral);
        badgeEl.textContent = numExec + ' executados | Total: ' + total;
        badgeEl.style.display = 'block';
    }

    var _resetClickTime = 0;
    async function resetarDados() {
        var agora = Date.now();
        if (agora - _resetClickTime > 1500) {
            _resetClickTime = agora;
            C.mostrarToast('Clique novamente em Reset para confirmar', 'aviso');
            return;
        }
        _resetClickTime = 0;
        C.reset();
        C.mostrarToast('Dados resetados!', 'ok');
        atualizarBadge();
    }

    // ── Extrair TODAS as ordens da tabela (com valores e situacao) ──
    function extrairTodasOrdens() {
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

                if (idx === 0) {
                    var seq = parseInt(text, 10);
                    if (!isNaN(seq)) sequencial = seq;
                } else if (idx === 2) {
                    dataRaw = text;
                } else if (idx === 4) {
                    var m = text.match(/R\$\s*([0-9.,]+)/);
                    if (m) valor = parseFloat(m[1].replace(/\./g, '').replace(',', '.'));
                } else if (idx === 5) {
                    if (/^\d{10,}$/.test(text)) protocolo = text;
                }

                if (text.length > 3 && !/^\d{10,}$/.test(text) && !/R\$/.test(text) && text !== 'Detalhar') {
                    if (!nome) nome = text.substring(0, 60);
                }
            });

            var allText = Array.from(cells).map(function(c) { return (c.textContent || '').trim(); }).join(' ');
            if (allText.indexOf('Respondida com minuta') > -1) {
                situacao = 'Respondida com minuta';
            } else if (allText.indexOf('Respondida') > -1) {
                situacao = 'Respondida';
            } else if (allText.indexOf('Protocolada') > -1) {
                situacao = 'Protocolada';
            } else if (allText.indexOf('Em processamento') > -1) {
                situacao = 'Em processamento';
            } else if (allText.indexOf('Cancelada') > -1) {
                situacao = 'Cancelada';
            }

            ordens.push({
                sequencial: sequencial,
                data: dataRaw,
                valor: valor,
                protocolo: protocolo,
                situacao: situacao,
                nome: nome,
                menuBtn: menuBtn,
                row: row
            });
        });

        ordens.sort(function(a, b) { return a.sequencial - b.sequencial; });
        return ordens;
    }

    function extrairValorTotalBloqueadoSerie() {
        try {
            // 1. Labels estruturados do Sisbajud
            var labels = document.querySelectorAll('.sisbajud-label, label, mat-label, dt, .col-form-label');
            for (var i = 0; i < labels.length; i++) {
                var txt = (labels[i].textContent || '').trim().toLowerCase();
                if (txt.includes('valor bloqueado') || txt.includes('total bloqueado')) {
                    var elVal = labels[i].nextElementSibling || (labels[i].parentElement && labels[i].parentElement.querySelector('.sisbajud-label-valor, dd, span, strong'));
                    if (elVal) {
                        var m = (elVal.textContent || '').match(/R\$\s*([0-9.,]+)/i);
                        if (m) return parseFloat(m[1].replace(/\./g, '').replace(',', '.'));
                    }
                }
            }

            // 2. Procura em mat-card ou containers de resumo
            var cards = document.querySelectorAll('mat-card, .mat-card, sisbajud-detalhes-teimosinha .card, .row');
            for (var j = 0; j < cards.length; j++) {
                var cTxt = (cards[j].textContent || '').replace(/\u00a0/g, ' ');
                var mCard = cTxt.match(/Valor\s+Bloqueado\s*:\s*R\$\s*([0-9.,]+)/i) ||
                            cTxt.match(/Total\s+Bloqueado\s*:\s*R\$\s*([0-9.,]+)/i) ||
                            cTxt.match(/Bloqueado\s*:\s*R\$\s*([0-9.,]+)/i);
                if (mCard) {
                    return parseFloat(mCard[1].replace(/\./g, '').replace(',', '.'));
                }
            }

            // 3. Fallback no body
            var bodyText = document.body ? document.body.innerText.replace(/\u00a0/g, ' ') : '';
            var mBody = bodyText.match(/Valor\s+Bloqueado\s*:\s*R\$\s*([0-9.,]+)/i) ||
                        bodyText.match(/Total\s+Bloqueado\s*:\s*R\$\s*([0-9.,]+)/i);
            if (mBody) {
                return parseFloat(mBody[1].replace(/\./g, '').replace(',', '.'));
            }
        } catch(e) {
            console.warn('[SISB Ordens] Erro ao extrair valor bloqueado da série:', e);
        }
        return null;
    }

    function identificarOrdensComBloqueio(ordens) {
        var bloqueios = [];
        if (!ordens || ordens.length === 0) {
            return { ordens: [], comBloqueio: [], totalOrdens: 0, totalComBloqueio: 0, totalValor: 0 };
        }

        // Garante ordenação por sequencial crescente (1, 2, 3...)
        ordens.sort(function(a, b) { return a.sequencial - b.sequencial; });

        var valorTotalBloqueadoSerie = extrairValorTotalBloqueadoSerie();
        console.log('[SISB Ordens] Valor total bloqueado da série no cabeçalho:', valorTotalBloqueadoSerie);

        var somaBloqueiosConsecutivos = 0;

        // 1. Detectar bloqueios pela redução de valor entre ordens consecutivas:
        // Se a ordem i tinha R$ 10.000 e a ordem i+1 tem R$ 8.000,
        // o bloqueio de R$ 2.000 ocorreu na ordem i (a primeira)!
        for (var i = 0; i < ordens.length - 1; i++) {
            var valorAtual = ordens[i].valor;
            var valorPosterior = ordens[i + 1].valor;

            if (valorAtual > valorPosterior + 0.01) {
                var valorDiferenca = valorAtual - valorPosterior;
                var ordemBloqueada = Object.assign({}, ordens[i]);
                ordemBloqueada.valorBloqueioEsperado = valorDiferenca;
                bloqueios.push(ordemBloqueada);
                somaBloqueiosConsecutivos += valorDiferenca;
                console.log('[SISB Ordens] Bloqueio detectado na ordem seq=' + ordens[i].sequencial +
                            ' (proto=' + ordens[i].protocolo + ') pela redução de R$ ' +
                            valorAtual.toFixed(2) + ' para R$ ' + valorPosterior.toFixed(2) +
                            '. Valor bloqueado: R$ ' + valorDiferenca.toFixed(2));
            }
        }

        // 2. Verificar a última ordem:
        // Se houver valor total bloqueado na série maior que a soma dos bloqueios anteriores:
        var ultimaOrdem = ordens[ordens.length - 1];
        if (valorTotalBloqueadoSerie !== null && valorTotalBloqueadoSerie !== undefined) {
            var saldoUltimaOrdem = valorTotalBloqueadoSerie - somaBloqueiosConsecutivos;
            if (saldoUltimaOrdem > 0.01) {
                var jaEstaNaLista = bloqueios.some(function(b) { return b.sequencial === ultimaOrdem.sequencial; });
                if (!jaEstaNaLista) {
                    var ordemUltimaBloqueada = Object.assign({}, ultimaOrdem);
                    ordemUltimaBloqueada.valorBloqueioEsperado = saldoUltimaOrdem;
                    bloqueios.push(ordemUltimaBloqueada);
                    console.log('[SISB Ordens] Bloqueio detectado na última ordem seq=' + ultimaOrdem.sequencial +
                                ' (proto=' + ultimaOrdem.protocolo + ') pelo saldo da série: R$ ' +
                                saldoUltimaOrdem.toFixed(2));
                }
            }
        } else if (ordens.length === 1) {
            if (ultimaOrdem.situacao === 'Respondida') {
                var oUnica = Object.assign({}, ultimaOrdem);
                oUnica.valorBloqueioEsperado = ultimaOrdem.valor;
                bloqueios.push(oUnica);
            }
        }

        var totalValor = bloqueios.reduce(function(acc, o) { return acc + (o.valorBloqueioEsperado || o.valor || 0); }, 0);

        console.log('[SISB Ordens] Total ordens:', ordens.length,
                    '| Com bloqueio identificadas:', bloqueios.length,
                    '| Total bloqueado calculado R$:', totalValor.toFixed(2));

        return {
            ordens: ordens,
            comBloqueio: bloqueios,
            totalOrdens: ordens.length,
            totalComBloqueio: bloqueios.length,
            totalValor: totalValor
        };
    }

    function obterOrdensComBloqueio() {
        var ordens = extrairTodasOrdens();
        var resultado = identificarOrdensComBloqueio(ordens);
        var bloqueios = resultado.comBloqueio;

        var D = window.SisbDetalhes;
        var numProc = D && D.extrairNumeroProcesso ? D.extrairNumeroProcesso() : null;
        var procNorm = numProc ? numProc.replace(/\D/g, '') : '';

        bloqueios = bloqueios.filter(function(o) {
            if (o.situacao === 'Respondida com minuta') {
                console.log('[SISB Fluxo] Pulando já respondida (com minuta):', o.protocolo);
                return false;
            }
            if (o.situacao !== 'Respondida') {
                console.log('[SISB Fluxo] Pulando ordem não respondida (' + o.situacao + '):', o.protocolo);
                return false;
            }
            if (D && D.ordemJaProcessada && procNorm && D.ordemJaProcessada(procNorm, o.protocolo)) {
                console.log('[SISB Fluxo] Pulando ordem já processada anteriormente (' + procNorm + '_' + o.protocolo + ')');
                return false;
            }
            return true;
        });

        return bloqueios;
    }

    async function selecionarAcao(overlay, tipo) {
        var radioGroup = overlay.querySelector('mat-radio-group');
        if (!radioGroup) {
            console.warn('[SISB Fluxo] mat-radio-group não encontrado no overlay');
            return false;
        }

        var radios = radioGroup.querySelectorAll('mat-radio-button');
        var alvo = null;

        radios.forEach(function(r) {
            var txt = (r.textContent || '').trim().toLowerCase();
            if (tipo === 'transferir' && txt.indexOf('transferir') > -1) {
                alvo = r;
            } else if (tipo === 'desbloquear' && txt.indexOf('desbloquear') > -1) {
                alvo = r;
            }
        });

        if (!alvo) {
            console.warn('[SISB Fluxo] Radio para', tipo, 'não encontrado');
            return false;
        }

        var labelOrInput = alvo.querySelector('label') || alvo.querySelector('input') || alvo;
        labelOrInput.click();
        console.log('[SISB Fluxo] Ação selecionada:', tipo);
        await C.sleep(300);

        if (tipo === 'transferir') {
            var chk = overlay.querySelector('mat-checkbox[formcontrolname="dadosTransferenciaUnica"]');
            if (chk) {
                var chkInput = chk.querySelector('input');
                if (chkInput && !chkInput.checked) {
                    (chk.querySelector('label') || chkInput).click();
                    console.log('[SISB Fluxo] Marcado: Dados de transferência únicos para todas as contas');
                    await C.sleep(200);
                }
            }
        }

        return true;
    }

    async function processarOrdem(ordem, tipo) {
        console.log('[SISB Fluxo] Processando ordem seq=' + ordem.sequencial + ' proto=' + ordem.protocolo);

        // Guarda o protocolo esperado para bater na tela /detalhar
        C.salvarEstado('sisb_protocolo_esperado', ordem.protocolo);

        ordem.menuBtn.click();
        await C.sleep(400);

        var detalharBtn = await C.wait(function() {
            var items = document.querySelectorAll('.cdk-overlay-pane button.mat-menu-item');
            for (var i = 0; i < items.length; i++) {
                if ((items[i].textContent || '').trim().indexOf('Detalhar') > -1) {
                    return items[i];
                }
            }
            return null;
        }, 3000);

        if (!detalharBtn) {
            console.warn('[SISB Fluxo] Botão Detalhar não encontrado no menu');
            return false;
        }
        detalharBtn.click();
        await C.sleep(800);

        var overlay = await C.wait('SISBAJUD-INCLUSAO-DESDOBRAMENTO', 5000);
        if (!overlay) {
            console.warn('[SISB Fluxo] Overlay de desdobramento não apareceu');
            return false;
        }

        var okAcao = await selecionarAcao(overlay, tipo);
        if (!okAcao) return false;

        var btnSalvar = await C.wait(function() {
            var btns = overlay.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var ic = btns[i].querySelector('mat-icon.fa-save');
                if (ic) return btns[i];
                var t = (btns[i].textContent || '').trim().toLowerCase();
                if (t === 'salvar') return btns[i];
            }
            return null;
        }, 3000);

        if (!btnSalvar) {
            console.warn('[SISB Fluxo] Botão Salvar não encontrado no overlay');
            return false;
        }
        btnSalvar.click();
        console.log('[SISB Fluxo] Clicou Salvar');
        await C.sleep(600);

        var modalConfirm = await C.wait(function() {
            var dialogs = document.querySelectorAll('.cdk-overlay-container mat-dialog-container, .cdk-overlay-pane');
            for (var i = 0; i < dialogs.length; i++) {
                var t = (dialogs[i].textContent || '').toLowerCase();
                if (t.indexOf('confirma') > -1 || t.indexOf('salvar') > -1) {
                    var btns = dialogs[i].querySelectorAll('button');
                    for (var j = 0; j < btns.length; j++) {
                        var bt = (btns[j].textContent || '').trim().toLowerCase();
                        if (bt.indexOf('sim') > -1 || bt.indexOf('confirmar') > -1) {
                            return btns[j];
                        }
                    }
                }
            }
            return null;
        }, 3000);

        if (modalConfirm) {
            modalConfirm.click();
            console.log('[SISB Fluxo] Confirmou modal de salvar');
            await C.sleep(400);
        }

        if (tipo === 'transferir') {
            var dialogTransf = await C.wait('SISBAJUD-DETALHE-ORDEM-TRANSFERIR-CONTA-UNICA', 3000);
            if (dialogTransf) {
                console.log('[SISB Fluxo] Modal conta única apareceu — confirmando...');
                var btnConfirmar = await C.wait(function() {
                    var btns = dialogTransf.querySelectorAll('button');
                    for (var i = 0; i < btns.length; i++) {
                        var t = (btns[i].textContent || '').trim().toLowerCase();
                        if (t.indexOf('confirmar') > -1 || t.indexOf('salvar') > -1) {
                            return btns[i];
                        }
                    }
                    return null;
                }, 2000);
                if (btnConfirmar) {
                    btnConfirmar.click();
                    await C.sleep(400);
                }
            }
        }

        // NÃO CLICA EM PROTOCOLAR NEM PREENCHE SENHA (ação exclusiva do usuário)
        C.mostrarToast('Ordem seq=' + ordem.sequencial + ' preenchida e salva! Favor protocolar e assinar.', 'ok', 4000);

        // Aguarda passivamente o usuário protocolar e o Sisbajud navegar para a tela /detalhar

        // Aguarda a tela de detalhar (URL /detalhar ou /detalhe)
        console.log('[SISB Fluxo] Aguardando tela /detalhar para bater o protocolo:', ordem.protocolo);
        var chegouDetalhar = await C.wait(function() {
            var u = window.location.href;
            return (u.indexOf('/detalhar') > -1 || u.indexOf('/detalhe') > -1) && !document.querySelector('SISBAJUD-INCLUSAO-DESDOBRAMENTO');
        }, 15000);

        if (chegouDetalhar) {
            console.log('[SISB Fluxo] Tela /detalhar carregada. Disparando extração consolidada...');
            await C.sleep(1200);
            if (window.SisbDetalhes && typeof window.SisbDetalhes.extrairOrdemDetalharAuto === 'function') {
                window.SisbDetalhes.extrairOrdemDetalharAuto();
            }
            await C.sleep(800);

            // Clica em voltar ou history.back() para retornar à lista de teimosinha
            var btnVoltar = document.querySelector('button[aria-label*="Voltar"], button.btn-voltar, mat-icon.fa-arrow-left');
            if (btnVoltar) {
                (btnVoltar.closest('button') || btnVoltar).click();
            } else {
                window.history.back();
            }
            await C.wait('SISBAJUD-DETALHES-TEIMOSINHA', 10000);
            await C.sleep(600);
        } else {
            console.warn('[SISB Fluxo] Não redirecionou para /detalhar no tempo limite');
        }

        console.log('[SISB Fluxo] Ordem seq=' + ordem.sequencial + ' finalizada com sucesso');
        return true;
    }

    async function executarFluxo(tipo) {
        if (_sisbFluxoAtivo) {
            C.mostrarToast('Fluxo já em andamento!', 'aviso');
            return;
        }

        var bloqueios = obterOrdensComBloqueio();
        if (bloqueios.length === 0) {
            C.mostrarToast('Nenhuma ordem com bloqueio encontrada para ' + tipo + '.', 'aviso');
            return;
        }

        _sisbFluxoAtivo = true;
        _sisbFluxoTipo = tipo;
        _sisbOrdensProcessadas = 0;
        _sisbTotalOrdens = bloqueios.length;

        var labelAcao = tipo === 'transferir' ? 'Transferência' : 'Desbloqueio';
        C.mostrarToast('Iniciando ' + labelAcao + ' de ' + _sisbTotalOrdens + ' ordens...', 'ok');

        for (var i = 0; i < bloqueios.length; i++) {
            var o = bloqueios[i];
            C.mostrarToast(labelAcao + ' (' + (i + 1) + '/' + _sisbTotalOrdens + ') — seq=' + o.sequencial, 'ok');

            var ok = await processarOrdem(o, tipo);
            if (ok) {
                _sisbOrdensProcessadas++;
            } else {
                console.warn('[SISB Fluxo] Falha na ordem seq=' + o.sequencial);
                var parar = !confirm('Falha na ordem ' + o.sequencial + ' (' + o.protocolo + '). Continuar com as próximas?');
                if (parar) break;
            }

            await C.sleep(1000);
        }

        C.mostrarToast(labelAcao + ' concluída! ' + _sisbOrdensProcessadas + '/' + _sisbTotalOrdens + ' processadas.', 'ok');
        _sisbFluxoAtivo = false;
        _sisbFluxoTipo = null;

        await consolidarRelatorio();
    }

    async function consolidarRelatorio() {
        if (typeof window.SisbRelatorios === 'undefined' || typeof window.SisbRelatorios.gerarRelatorio !== 'function') {
            console.log('[SISB Fluxo] SisbRelatorios não disponível');
            return;
        }
        var resultado = window.SisbRelatorios.gerarRelatorio();
        if (!resultado || !resultado.sucesso) {
            console.log('[SISB Fluxo] Relatório vazio ou falha:', resultado ? resultado.erro : 'sem dados');
            return;
        }
        if (resultado.copiado) {
            C.mostrarToast('Relatório copiado para o clipboard! (' + resultado.total_formatado + ')', 'ok');
        }
    }

    function injetarBotoes(container) {
        if (document.getElementById('btn-sisb-transferir')) return;

        var btnTransferir = C.criarBotao('btn-sisb-transferir', '🏦 Transferir', '#1565c0', function() {
            executarFluxo('transferir');
        });

        var btnDesbloquear = C.criarBotao('btn-sisb-desbloquear', '🔓 Desbloquear', '#d32f2f', function() {
            executarFluxo('desbloquear');
        });

        var btnReset = C.criarBotao('btn-sisb-reset', '🗑 Reset', '#546e7a', resetarDados);

        container.appendChild(btnTransferir);
        container.appendChild(btnDesbloquear);
        container.appendChild(btnReset);
    }

    window.SisbOrdens = {
        extrairTodasOrdens: extrairTodasOrdens,
        identificarOrdensComBloqueio: identificarOrdensComBloqueio,
        obterOrdensComBloqueio: obterOrdensComBloqueio,
        executarFluxo: executarFluxo,
        processarOrdem: processarOrdem,
        injetarBotoes: injetarBotoes,
        atualizarBadge: atualizarBadge,
        resetarDados: resetarDados
    };

})();
