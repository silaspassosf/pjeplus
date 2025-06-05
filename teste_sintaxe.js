// Teste de sintaxe para o bookmarklet
(function(){
    console.log('Teste de sintaxe JavaScript');
    
    // Simulando estrutura principal do bookmarklet
    var old = document.getElementById('maisPjeBox');
    if(old) old.remove();
    
    if(!window.fluxoDespacho) {
        window.fluxoDespacho = function(config) {
            console.log('[DESPACHO] Iniciando fluxo:', config);
            try {
                var btnAnalise = document.querySelector('button[title*="Análise"], button[aria-label*="Análise"]');
                if(btnAnalise) {
                    btnAnalise.click();
                    console.log('[DESPACHO] Movimentado para Análise.');
                }
                setTimeout(function(){
                    var btnConclusao = document.querySelector('button[title*="Conclusão"], button[aria-label*="Conclusão"]');
                    if(btnConclusao) {
                        btnConclusao.click();
                        console.log('[DESPACHO] Movimentado para Conclusão ao Magistrado.');
                    }
                    setTimeout(function(){
                        var modelo = config.modelo || '';
                        if(modelo) {
                            var campoFiltro = document.querySelector('#inputFiltro[aria-label]');
                            if(campoFiltro) {
                                campoFiltro.click();
                                campoFiltro.value = '';
                                campoFiltro.value = modelo;
                                campoFiltro.dispatchEvent(new Event('input', {bubbles:true}));
                                console.log('[DESPACHO] Modelo preenchido:', modelo);
                            }
                        }
                    }, 1000);
                }, 1000);
            } catch(e) {
                console.error('[DESPACHO] Erro:', e);
                alert('Erro no fluxo Despacho: ' + e.message);
            }
        };
        
        window.fluxoGigs = function(config) {
            console.log('[AUTOGIGS] Iniciando:', config.nm_botao, '- Tipo:', config.tipo);
            try {
                var gigsFechado = !document.querySelector('pje-gigs-ficha-processo');
                if(gigsFechado) {
                    var btnMostrar = document.querySelector('button[aria-label="Mostrar o GIGS"]');
                    if(btnMostrar) {
                        btnMostrar.click();
                        console.log('[AUTOGIGS] GIGS aberto');
                    }
                }
                setTimeout(function(){
                    if(config.tipo === 'chip') {
                        var nomeChip = config.tipo_atividade || config.nm_botao;
                        var chips = document.querySelectorAll('button[mattooltip*="' + nomeChip + '"], button[title*="' + nomeChip + '"]');
                        if(chips.length > 0) {
                            chips[0].click();
                            console.log('[AUTOGIGS] Chip aplicado:', nomeChip);
                        } else {
                            alert('Chip não encontrado: ' + nomeChip);
                        }
                    } else if(config.tipo === 'comentario') {
                        var btnComentario = document.querySelector('button[aria-label*="comentário"], button[title*="comentário"]');
                        if(btnComentario) {
                            btnComentario.click();
                            setTimeout(function(){
                                var campoObs = document.querySelector('textarea[formcontrolname="observacao"]');
                                if(campoObs) {
                                    campoObs.value = config.observacao || '';
                                    campoObs.dispatchEvent(new Event('input', {bubbles:true}));
                                    console.log('[AUTOGIGS] Comentário adicionado');
                                }
                            }, 500);
                        }
                    } else {
                        // Buscar botão "Nova atividade" manualmente
                        var btnNova = null;
                        var botoes = document.querySelectorAll('button');
                        for(var i = 0; i < botoes.length; i++) {
                            if(botoes[i].textContent.includes('Nova atividade') || 
                               (botoes[i].getAttribute('aria-label') && botoes[i].getAttribute('aria-label').includes('Nova'))) {
                                btnNova = botoes[i];
                                break;
                            }
                        }
                        if(btnNova) {
                            btnNova.click();
                            setTimeout(function(){
                                if(config.tipo_atividade) {
                                    var campoTipo = document.querySelector('input[formcontrolname="tipoAtividade"]');
                                    if(campoTipo) {
                                        campoTipo.value = config.tipo_atividade;
                                        campoTipo.dispatchEvent(new Event('input', {bubbles:true}));
                                    }
                                }
                                if(config.observacao) {
                                    var campoObs = document.querySelector('textarea[formcontrolname="observacao"]');
                                    if(campoObs) {
                                        campoObs.value = config.observacao;
                                        campoObs.dispatchEvent(new Event('input', {bubbles:true}));
                                    }
                                }
                                if(config.responsavel) {
                                    var campoResp = document.querySelector('input[aria-label*="Responsável pela atividade"]');
                                    if(campoResp) {
                                        campoResp.value = config.responsavel;
                                        campoResp.dispatchEvent(new Event('input', {bubbles:true}));
                                    }
                                }
                                if(config.prazo) {
                                    var campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
                                    if(campoPrazo) {
                                        campoPrazo.value = config.prazo;
                                        campoPrazo.dispatchEvent(new Event('input', {bubbles:true}));
                                    }
                                }
                                console.log('[AUTOGIGS] Atividade GIGS criada');
                            }, 1000);
                        }
                    }
                }, 1000);
            } catch(e) {
                console.error('[AUTOGIGS] Erro:', e);
                alert('Erro no fluxo AutoGigs: ' + e.message);
            }
        };
        
        window.fluxoAnexar = function(config) {
            console.log('[ANEXAR] Iniciando:', config.tipo || '', '-', config.modelo || '');
            try {
                setTimeout(function(){
                    var btnAnexar = document.querySelector('#pjextension_bt_detalhes_4') || 
                                   document.querySelector('button[aria-label*="anexar"], button[title*="anexar"]') || 
                                   document.querySelector('button i.fa-paperclip');
                    if(btnAnexar) {
                        if(btnAnexar.tagName !== 'BUTTON') btnAnexar = btnAnexar.closest('button');
                        btnAnexar.click();
                        console.log('[ANEXAR] Botão de anexar clicado');
                    }
                    setTimeout(function(){
                        if(config.modelo && config.modelo.toLowerCase() === 'pdf') {
                            var switchPdf = document.querySelector('input[role="switch"]');
                            if(switchPdf && !switchPdf.checked) {
                                switchPdf.click();
                                console.log('[ANEXAR] Switch PDF ativado');
                            }
                        }
                        setTimeout(function(){
                            var tipo = config.tipo || 'Certidão';
                            var campoTipo = document.querySelector('input[aria-label="Tipo de Documento"]');
                            if(campoTipo) {
                                campoTipo.value = '';
                                campoTipo.value = tipo;
                                campoTipo.dispatchEvent(new Event('input', {bubbles:true}));
                                var enterEvent = new KeyboardEvent('keydown', {
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true
                                });
                                campoTipo.dispatchEvent(enterEvent);
                                console.log('[ANEXAR] Tipo selecionado:', tipo);
                            }
                            if(config.descricao) {
                                setTimeout(function(){
                                    var campoDesc = document.querySelector('input[aria-label="Descrição"]');
                                    if(campoDesc) {
                                        campoDesc.value = config.descricao;
                                        campoDesc.dispatchEvent(new Event('input', {bubbles:true}));
                                        console.log('[ANEXAR] Descrição preenchida:', config.descricao);
                                    }
                                }, 500);
                            }
                        }, 1000);
                    }, 1000);
                }, 500);
            } catch(e) {
                console.error('[ANEXAR] Erro:', e);
                alert('Erro no fluxo Anexar: ' + e.message);
            }
        };
    }
    
    console.log('Sintaxe JavaScript validada com sucesso!');
})();
