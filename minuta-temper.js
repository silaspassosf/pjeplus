// ==UserScript==
// @name         Minuta Overlay Atos TRT2
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  Overlay de botões para atos judiciais na tela /minutar do TRT2
// @author       Copilot
// @match        https://*.trt2.jus.br/*/minutar*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // --- Funções JS que replicam as ações de ato_judicial (apenas PEC, SIGILO, PRAZO, MOVIMENTO) ---
    function setSigilo(sigilo) {
        return new Promise((resolve, reject) => {
            try {
                const sigiloInput = document.querySelector('input.mat-slide-toggle-input[name="sigiloso"]');
                if (sigiloInput) {
                    if (sigiloInput.checked !== sigilo) {
                        sigiloInput.click();
                        // Aguarda a mudança ser aplicada
                        setTimeout(() => {
                            resolve(sigiloInput.checked === sigilo);
                        }, 300);
                    } else {
                        resolve(true);
                    }
                } else {
                    resolve(true); // Não encontrou o input, consideramos ok
                }
            } catch(e) {
                reject(e);
            }
        });
    }

    function setPEC(marcar_pec) {
        return new Promise((resolve, reject) => {
            try {
                const pecInput = document.querySelector('input[aria-label*="PEC"]');
                if (pecInput) {
                    if (pecInput.checked !== marcar_pec) {
                        pecInput.click();
                        // Aguarda a mudança ser aplicada
                        setTimeout(() => {
                            resolve(pecInput.checked === marcar_pec);
                        }, 300);
                    } else {
                        resolve(true);
                    }
                } else {
                    resolve(true); // Não encontrou o input, consideramos ok
                }
            } catch(e) {
                reject(e);
            }
        });
    }

    function setPrazo(prazo, marcar_primeiro_destinatario) {
        return new Promise((resolve, reject) => {
            try {
                console.log('[DEBUG][setPrazo] Iniciando preenchimento de prazo:', prazo, 'primeiro destinatário:', marcar_primeiro_destinatario);
                if (typeof prazo !== 'number' || prazo <= 0) {
                    console.log('[DEBUG][setPrazo] Prazo inválido:', prazo);
                    resolve(true);
                    return;
                }
                // Busca todos os campos de prazo e checkboxes
                const prazoInputs = Array.from(document.querySelectorAll('mat-form-field.prazo input[type="text"].mat-input-element'));
                const checkboxes = Array.from(document.querySelectorAll('mat-checkbox input.mat-checkbox-input'));
                console.log('[DEBUG][setPrazo] Campos de prazo encontrados:', prazoInputs.length, prazoInputs);
                console.log('[DEBUG][setPrazo] Checkboxes encontrados:', checkboxes.length, checkboxes);
                
                if (prazoInputs.length === 0 || checkboxes.length === 0) {
                    console.log('[DEBUG][setPrazo] Nenhum campo de prazo ou checkbox encontrado.');
                    resolve(false);
                    return;
                }

                if (marcar_primeiro_destinatario) {
                    // Se é para marcar só o primeiro:
                    // 1. Preenche prazo apenas do primeiro destinatário
                    const primeiroPrazo = prazoInputs[0];
                    primeiroPrazo.focus();
                    primeiroPrazo.value = prazo;
                    primeiroPrazo.dispatchEvent(new Event('input', {bubbles:true}));
                    primeiroPrazo.dispatchEvent(new Event('change', {bubbles:true}));

                    // 2. Desmarca as checkboxes dos demais (mantém o primeiro como está)
                    checkboxes.forEach((cb, idx) => {
                        if (idx > 0 && cb.checked) {
                            cb.click();
                        }
                    });
                    
                    console.log('[DEBUG][setPrazo] Modo primeiro destinatário: prazo preenchido e demais desmarcados');
                } else {
                    // Se é para marcar todos:
                    // 1. Marca todas as checkboxes que não estiverem marcadas
                    checkboxes.forEach(cb => { 
                        if (!cb.checked) cb.click();
                    });

                    // 2. Preenche o prazo em todos os inputs
                    prazoInputs.forEach(inp => {
                        inp.focus();
                        inp.value = prazo;
                        inp.dispatchEvent(new Event('input', {bubbles:true}));
                        inp.dispatchEvent(new Event('change', {bubbles:true}));
                    });
                    
                    console.log('[DEBUG][setPrazo] Modo todos: prazo preenchido em todos e todos marcados');
                }

                // Verifica se as ações foram aplicadas corretamente
                setTimeout(() => {
                    const prazoOk = marcar_primeiro_destinatario ? 
                        prazoInputs[0].value == prazo : 
                        prazoInputs.every(inp => inp.value == prazo);
                    
                    const checkboxesOk = marcar_primeiro_destinatario ?
                        checkboxes[0].checked && checkboxes.slice(1).every(cb => !cb.checked) :
                        checkboxes.every(cb => cb.checked);
                    
                    resolve(prazoOk && checkboxesOk);
                }, 500);

            } catch(e) {
                reject(e);
            }
        });
    }

    function setMovimento(movimento) {
        return new Promise((resolve, reject) => {
            try {
                if (!movimento) {
                    resolve(true);
                    return;
                }
                const tabMov = Array.from(document.querySelectorAll('.mat-tab-label-content')).find(e => e.textContent.includes('Movimentos'));
                if (tabMov) {
                    tabMov.click();
                    setTimeout(() => {
                        const movInput = document.querySelector('input[aria-label*="Movimento"]');
                        if (movInput) {
                            movInput.value = movimento;
                            movInput.dispatchEvent(new Event('input', {bubbles:true}));
                            // Aguarda um pouco mais para o movimento ser processado
                            setTimeout(() => {
                                resolve(movInput.value === movimento);
                            }, 600);
                        } else {
                            resolve(false);
                        }
                    }, 400);
                } else {
                    resolve(false);
                }
            } catch(e) {
                reject(e);
            }
        });
    }

    function clicarFaAngleRight() {
        return new Promise((resolve, reject) => {
            try {
                const el = document.querySelector('em.fa-angle-right.fas');
                if (el) {
                    el.click();
                    console.log('[DEBUG] Clique em .fa-angle-right.fas realizado');
                    resolve(true);
                } else {
                    console.log('[DEBUG] Elemento .fa-angle-right.fas não encontrado para clique');
                    resolve(false);
                }
            } catch(e) {
                console.error('[ERRO] Falha ao clicar em .fa-angle-right.fas:', e);
                reject(e);
            }
        });
    }

    // --- Função principal para executar o ato judicial (chama as ações acima) ---
    async function executarAto(params) {
        try {
            // Executa as ações em sequência, verificando o resultado de cada uma
            const sigiloOk = await setSigilo(params.sigilo);
            if (!sigiloOk) {
                console.error('[ERRO] Falha ao configurar sigilo');
                return;
            }

            const pecOk = await setPEC(params.marcar_pec);
            if (!pecOk) {
                console.error('[ERRO] Falha ao configurar PEC');
                return;
            }

            const prazoOk = await setPrazo(params.prazo, params.marcar_primeiro_destinatario);
            if (!prazoOk) {
                console.error('[ERRO] Falha ao configurar prazo');
                return;
            }

            const movimentoOk = await setMovimento(params.movimento);
            if (!movimentoOk && params.movimento) {
                console.error('[ERRO] Falha ao configurar movimento');
                return;
            }

            // Aguarda um pouco para garantir que todas as mudanças foram aplicadas
            setTimeout(async () => {
                // Só clica se todas as configurações foram bem sucedidas
                const clicado = await clicarFaAngleRight();
                if (!clicado) {
                    console.error('[ERRO] Falha ao clicar no botão final');
                }
            }, 800);

        } catch (error) {
            console.error('[ERRO] Falha na execução do ato:', error);
        }
    }

    // --- Parâmetros dos wrappers (espelhe os de atos.py) ---
    const wrappers = [
        {
            nome: 'Ato Meios',
            descricao: 'Meios executivos típicos',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'xsmeios', prazo: 5, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: true
            }
        },
        {
            nome: 'Ato CRDA',
            descricao: 'Intimação da reclamada',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'a reclda', prazo: 15, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: false
            }
        },
        {
            nome: 'Ato CRTE',
            descricao: 'Intimação do reclamante',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'xreit', prazo: 15, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: false
            }
        },
        {
            nome: 'Ato BLOQ',
            descricao: 'Bloqueio de valores',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'xsparcial', prazo: null, marcar_pec: true, movimento: null, sigilo: false, marcar_primeiro_destinatario: false
            }
        },
        {
            nome: 'Ato IDPJ',
            descricao: 'IDPJ - Desconsideração',
            params: {
                conclusao_tipo: 'IDPJ', modelo_nome: 'pjsem', prazo: 8, marcar_pec: true, movimento: null, sigilo: false, marcar_primeiro_destinatario: false
            }
        },
        {
            nome: 'Ato Termo E',
            descricao: 'Termo empresa',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'xempre', prazo: 5, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: true
            }
        },
        {
            nome: 'Ato Termo S',
            descricao: 'Termo sócio',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'xsocio', prazo: 5, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: true
            }
        },
        {
            nome: 'Ato Edital',
            descricao: 'Edital de citação/intimação',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: 'xsedit', prazo: 5, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: true
            }
        },
        {
            nome: 'Ato 180',
            descricao: 'Art. 180 - Sobrestar execução',
            params: {
                conclusao_tipo: 'sobrest', modelo_nome: 'x180', prazo: 0, marcar_pec: false, movimento: null, sigilo: false, marcar_primeiro_destinatario: false
            }
        },
        {
            nome: 'Ato Suspf',
            descricao: 'Suspensão por tentativa frustrada',
            params: {
                conclusao_tipo: 'Despacho', modelo_nome: '', prazo: 0, marcar_pec: false, movimento: 'frustrada', sigilo: false, marcar_primeiro_destinatario: false
            }
        }
    ];

    // --- Aguarda DOM pronto e elemento alvo ---
    function waitForElement(selector, fn) {
        const el = document.querySelector(selector);
        if (el) return fn(el);
        setTimeout(() => waitForElement(selector, fn), 400);
    }

    // --- Cria overlay de botões ---
    function criarOverlay() {
        // Evita múltiplas criações e múltiplos waits concorrentes
        if (window._overlayCriando || document.getElementById('overlay-atos-judiciais')) return;
        window._overlayCriando = true;
        waitForElement('button.botao-salvar', function(btnSalvar) {
            // Garante que não foi criado por outra chamada concorrente
            if (document.getElementById('overlay-atos-judiciais')) {
                window._overlayCriando = false;
                return;
            }
            // Busca o container lateral correto
            const lateral = btnSalvar.closest('.coluna.direita');
            if (!lateral) {
                window._overlayCriando = false;
                return;
            }
            let overlay = document.createElement('div');
            overlay.id = 'overlay-atos-judiciais';
            overlay.style.position = 'relative';
            overlay.style.margin = '16px 0 8px 0';
            overlay.style.padding = '8px 8px 8px 0';
            overlay.style.background = 'rgba(255,255,255,0.95)';
            overlay.style.border = '1px solid #1976d2';
            overlay.style.borderRadius = '8px';
            overlay.style.display = 'grid';
            overlay.style.gridTemplateColumns = 'repeat(4, 1fr)'; // 4 colunas por linha
            overlay.style.gap = '8px';
            overlay.style.zIndex = 1000;
            overlay.style.width = '35%'; // Cumprimento de 35% da caixa
            wrappers.forEach((w, idx) => {
                let b = document.createElement('button');
                // Nome do botão: apenas o sufixo após 'Ato '
                let nome = w.nome.replace(/^Ato\s+/i, '');
                b.textContent = nome;
                b.title = w.descricao || '';
                b.style.background = '#1976d2';
                b.style.color = '#fff';
                b.style.border = 'none';
                b.style.borderRadius = '4px';
                b.style.padding = '6px 14px';
                b.style.fontWeight = 'bold';
                b.style.cursor = 'pointer';
                b.style.fontSize = '14px';
                b.onclick = () => executarAto(w.params);
                overlay.appendChild(b);
            });
            // Botão para criar novo ato
            let novoBtn = document.createElement('button');
            novoBtn.textContent = '+ Novo Ato';
            novoBtn.title = 'Adicionar novo ato judicial';
            novoBtn.style.background = '#fff';
            novoBtn.style.color = '#1976d2';
            novoBtn.style.border = '1px solid #1976d2';
            novoBtn.style.borderRadius = '4px';
            novoBtn.style.padding = '6px 14px';
            novoBtn.style.fontWeight = 'bold';
            novoBtn.style.cursor = 'pointer';
            novoBtn.style.fontSize = '14px';
            novoBtn.onclick = function() {
                // Coleta parâmetros via prompt
                const nome = prompt('Nome do botão (ex: Ato Pesquisa):');
                if (!nome) return;
                const descricao = prompt('Descrição do ato:');
                const conclusao_tipo = prompt('Tipo de conclusão (ex: Despacho, IDPJ):');
                const modelo_nome = prompt('Nome do modelo (ex: xsmeios):');
                let prazo = prompt('Prazo (em dias, deixe vazio para nenhum):');
                prazo = prazo ? parseInt(prazo) : null;
                const marcar_pec = confirm('Marcar PEC? (OK=Sim, Cancel=Não)');
                const sigilo = confirm('Sigiloso? (OK=Sim, Cancel=Não)');
                const marcar_primeiro_destinatario = confirm('Apenas primeiro destinatário? (OK=Sim, Cancel=Não)');
                const movimento = prompt('Movimento (deixe vazio para nenhum):') || null;
                // Adiciona botão dinâmico
                const params = { conclusao_tipo, modelo_nome, prazo, marcar_pec, movimento, sigilo, marcar_primeiro_destinatario };
                let b = document.createElement('button');
                b.textContent = nome.replace(/^Ato\s+/i, '');
                b.title = descricao || '';
                b.style.background = '#1976d2';
                b.style.color = '#fff';
                b.style.border = 'none';
                b.style.borderRadius = '4px';
                b.style.padding = '6px 14px';
                b.style.fontWeight = 'bold';
                b.style.cursor = 'pointer';
                b.style.fontSize = '14px';
                b.onclick = () => executarAto(params);
                overlay.appendChild(b);
                // Gera código pronto para colar
                const code = `,\n    {\n        nome: '${nome}',\n        descricao: '${descricao}',\n        params: {\n            conclusao_tipo: '${conclusao_tipo}', modelo_nome: '${modelo_nome}', prazo: ${prazo}, marcar_pec: ${marcar_pec}, movimento: ${movimento ? `'${movimento}'` : null}, sigilo: ${sigilo}, marcar_primeiro_destinatario: ${marcar_primeiro_destinatario}\n        }\n    }`;
                // Copia para clipboard e mostra para o usuário
                navigator.clipboard.writeText(code).then(() => {
                    alert('Trecho para colar no array wrappers copiado para a área de transferência!\nCole no script para tornar o botão permanente.\n\n' + code);
                }, () => {
                    alert('Trecho para colar no array wrappers:\n' + code);
                });
            };
            overlay.appendChild(novoBtn);
            btnSalvar.parentElement.insertBefore(overlay, btnSalvar.nextSibling);
            window._overlayCriando = false;
        });
    }

    // --- Ativação automática do overlay usando MutationObserver ---
    function ativarOverlayAutomatico() {
        // Cria overlay se já estamos na tela /minutar e não existe overlay
        if (location.pathname.includes('/minutar')) {
            criarOverlay();
        }
        // Observa mudanças no body para detectar navegação SPA
        const observer = new MutationObserver(() => {
            if (location.pathname.includes('/minutar')) {
                if (!document.getElementById('overlay-atos-judiciais') && document.querySelector('button.botao-salvar')) {
                    criarOverlay();
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    ativarOverlayAutomatico();

    // Removido setInterval redundante que causava overlay duplo
})();
