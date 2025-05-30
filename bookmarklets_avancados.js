// ====================================================
// BOOKMARKLET AVANÇADO - ATO JUDICIAL COMPLETO
// ====================================================
// Este bookmarklet simula o fluxo completo da função ato_judicial
// Baseado no código Python do atos.py

const bookmarklet_ato_judicial_completo = `javascript:(function(){
    // Configuração dos atos disponíveis
    const ATOS = {
        'meios': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'xsmeios',
            prazo: 5,
            marcar_pec: false,
            movimento: null,
            marcar_primeiro_destinatario: true,
            nome: 'Meios de Execução'
        },
        'crda': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'a reclda',
            prazo: 15,
            marcar_pec: false,
            movimento: null,
            marcar_primeiro_destinatario: false,
            nome: 'Carta de Reclamada'
        },
        'crte': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'xreit',
            prazo: 15,
            marcar_pec: false,
            movimento: null,
            marcar_primeiro_destinatario: false,
            nome: 'Carta de Reclamante'
        },
        'bloq': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'xsparcial',
            prazo: null,
            marcar_pec: true,
            movimento: null,
            marcar_primeiro_destinatario: false,
            nome: 'Bloqueio'
        },
        'idpj': {
            conclusao_tipo: 'IDPJ',
            modelo_nome: 'pjsem',
            prazo: 8,
            marcar_pec: true,
            movimento: null,
            marcar_primeiro_destinatario: false,
            nome: 'IDPJ'
        },
        'termoE': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'xempre',
            prazo: 5,
            marcar_pec: false,
            movimento: null,
            marcar_primeiro_destinatario: true,
            nome: 'Termo de Empresa'
        },
        'termoS': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'xsocio',
            prazo: 5,
            marcar_pec: false,
            movimento: null,
            marcar_primeiro_destinatario: true,
            nome: 'Termo de Sócio'
        },
        'edital': {
            conclusao_tipo: 'Despacho',
            modelo_nome: 'xsedit',
            prazo: 5,
            marcar_pec: false,
            movimento: null,
            marcar_primeiro_destinatario: true,
            nome: 'Edital'
        },
        'sobrestamento': {
            conclusao_tipo: '/ Susp',
            modelo_nome: 'suspf',
            prazo: 0,
            marcar_pec: false,
            movimento: 'frustrada',
            marcar_primeiro_destinatario: false,
            nome: 'Sobrestamento'
        },
        'pesquisas': {
            conclusao_tipo: 'BNDT',
            modelo_nome: 'xsbacen',
            prazo: 30,
            marcar_pec: true,
            movimento: 'bloqueio',
            marcar_primeiro_destinatario: true,
            sigilo: true,
            nome: 'Pesquisas BACEN/BNDT'
        }
    };

    // Função para aguardar elemento aparecer
    function waitForElement(selector, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            const checkElement = () => {
                const element = document.querySelector(selector);
                if (element) {
                    resolve(element);
                } else if (Date.now() - startTime > timeout) {
                    reject(new Error('Timeout aguardando elemento: ' + selector));
                } else {
                    setTimeout(checkElement, 100);
                }
            };
            checkElement();
        });
    }

    // Função para aguardar um tempo
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Função para simular eventos de teclado
    function triggerKeyboardEvent(element, eventType, key, keyCode) {
        const event = new KeyboardEvent(eventType, {
            key: key,
            keyCode: keyCode,
            which: keyCode,
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(event);
    }

    // Função para simular clique
    function clickElement(element) {
        if (element) {
            element.scrollIntoView({behavior: 'smooth', block: 'center'});
            element.click();
            return true;
        }
        return false;
    }

    // Função principal para executar ato judicial
    async function executarAtoJudicial(tipoAto) {
        const config = ATOS[tipoAto];
        if (!config) {
            console.error('[BOOKMARKLET] Tipo de ato não encontrado:', tipoAto);
            return false;
        }

        console.log('[BOOKMARKLET] Iniciando execução do ato:', config.nome);

        try {
            // 1. Verificar se está na tela de minuta
            if (!window.location.href.includes('/minutar')) {
                alert('❌ Este bookmarklet deve ser usado na tela de minuta do PJe!');
                return false;
            }

            // 2. Preencher modelo
            console.log('[BOOKMARKLET] Etapa 1: Preenchendo modelo');
            const campoModelo = await waitForElement('#inputFiltro');
            
            campoModelo.focus();
            campoModelo.value = '';
            campoModelo.value = config.modelo_nome;
            
            // Disparar eventos para o Angular detectar a mudança
            campoModelo.dispatchEvent(new Event('input', {bubbles: true}));
            campoModelo.dispatchEvent(new Event('change', {bubbles: true}));
            campoModelo.dispatchEvent(new Event('keyup', {bubbles: true}));
            
            // Pressionar Enter
            triggerKeyboardEvent(campoModelo, 'keydown', 'Enter', 13);
            
            await sleep(800);

            // 3. Clicar no modelo filtrado
            console.log('[BOOKMARKLET] Etapa 2: Selecionando modelo filtrado');
            const nodoFiltrado = await waitForElement('.nodo-filtrado');
            clickElement(nodoFiltrado);
            
            await sleep(500);

            // 4. Clicar em Inserir
            console.log('[BOOKMARKLET] Etapa 3: Inserindo modelo');
            const btnInserir = await waitForElement('pje-dialogo-visualizar-modelo button');
            clickElement(btnInserir);
            
            await sleep(1000);

            // 5. Clicar em Salvar
            console.log('[BOOKMARKLET] Etapa 4: Salvando');
            const btnSalvar = await waitForElement('button[aria-label="Salvar"]');
            clickElement(btnSalvar);
            
            await sleep(1500);

            // 6. Configurar Sigilo (se necessário)
            if (config.sigilo) {
                console.log('[BOOKMARKLET] Etapa 5: Configurando sigilo');
                try {
                    const sigiloInput = document.querySelector('input.mat-slide-toggle-input[name="sigiloso"]');
                    if (sigiloInput) {
                        const isChecked = sigiloInput.getAttribute('aria-checked') === 'true';
                        if (!isChecked) {
                            clickElement(sigiloInput);
                            await sleep(300);
                        }
                    }
                } catch (e) {
                    console.warn('[BOOKMARKLET] Erro ao configurar sigilo:', e);
                }
            }

            // 7. Configurar PEC
            if (config.marcar_pec !== null) {
                console.log('[BOOKMARKLET] Etapa 6: Configurando PEC');
                try {
                    const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
                    if (pecCheckbox) {
                        const isChecked = pecCheckbox.checked || pecCheckbox.getAttribute('aria-checked') === 'true';
                        
                        if (config.marcar_pec && !isChecked) {
                            clickElement(pecCheckbox);
                            await sleep(300);
                        } else if (!config.marcar_pec && isChecked) {
                            clickElement(pecCheckbox);
                            await sleep(300);
                        }
                    }
                } catch (e) {
                    console.warn('[BOOKMARKLET] Erro ao configurar PEC:', e);
                }
            }

            // 8. Configurar Prazo
            if (config.prazo !== null && config.prazo > 0) {
                console.log('[BOOKMARKLET] Etapa 7: Configurando prazo');
                try {
                    // Primeiro marcar "dias úteis" se disponível
                    const diasUteisSpan = document.querySelector('span.mat-radio-label-content');
                    if (diasUteisSpan && diasUteisSpan.textContent.toLowerCase().includes('dias úteis')) {
                        clickElement(diasUteisSpan);
                        await sleep(200);
                    }

                    // Preencher campo de prazo
                    const campoPrazo = document.querySelector('input[formcontrolname="prazo"]') || 
                                     document.querySelector('input[type="number"]');
                    
                    if (campoPrazo) {
                        campoPrazo.focus();
                        campoPrazo.value = '';
                        campoPrazo.value = config.prazo.toString();
                        campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                        campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                        
                        await sleep(500);
                        
                        // Clicar em Gravar (prazo)
                        const btnGravarPrazo = document.querySelector('button:not([aria-label*="movimentos"])');
                        if (btnGravarPrazo && btnGravarPrazo.textContent.includes('Gravar')) {
                            clickElement(btnGravarPrazo);
                            await sleep(1000);
                        }
                    }
                } catch (e) {
                    console.warn('[BOOKMARKLET] Erro ao configurar prazo:', e);
                }
            }

            // 9. Configurar Movimento
            if (config.movimento) {
                console.log('[BOOKMARKLET] Etapa 8: Configurando movimento');
                try {
                    // Ativar aba de movimentos
                    const abaMovimentos = Array.from(document.querySelectorAll('.mat-tab-label'))
                        .find(tab => tab.textContent.toLowerCase().includes('movimentos'));
                    
                    if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                        clickElement(abaMovimentos);
                        await sleep(700);
                    }

                    // Buscar e marcar o movimento
                    const movimentoText = config.movimento.toLowerCase().replace(/\\s+/g, ' ');
                    const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
                    
                    for (const checkbox of checkboxes) {
                        const label = checkbox.querySelector('.mat-checkbox-label');
                        if (label && label.textContent.toLowerCase().includes(movimentoText)) {
                            const input = checkbox.querySelector('input[type="checkbox"]');
                            if (input && !input.checked) {
                                clickElement(input);
                                await sleep(300);
                                break;
                            }
                        }
                    }

                    await sleep(500);

                    // Gravar movimento
                    const btnGravarMov = document.querySelector('button[aria-label*="Gravar os movimentos"]');
                    if (btnGravarMov) {
                        clickElement(btnGravarMov);
                        await sleep(1000);
                        
                        // Confirmar no modal se aparecer
                        const btnSim = document.querySelector('mat-dialog-container button .mat-button-wrapper:contains("Sim")');
                        if (btnSim) {
                            clickElement(btnSim.parentElement);
                            await sleep(1000);
                        }
                        
                        // Salvar
                        const btnSalvarMov = document.querySelector('button[aria-label="Salvar"]:not([aria-label*="movimentos"])');
                        if (btnSalvarMov) {
                            clickElement(btnSalvarMov);
                            await sleep(1000);
                        }
                    }
                } catch (e) {
                    console.warn('[BOOKMARKLET] Erro ao configurar movimento:', e);
                }
            }

            console.log('✅ [BOOKMARKLET] Ato judicial executado com sucesso:', config.nome);
            alert('✅ Ato "' + config.nome + '" executado com sucesso!\\n\\nParâmetros aplicados:\\n' + 
                  '• Modelo: ' + config.modelo_nome + '\\n' +
                  '• Prazo: ' + (config.prazo || 'Não alterado') + '\\n' +
                  '• PEC: ' + (config.marcar_pec ? 'Sim' : 'Não') + '\\n' +
                  '• Movimento: ' + (config.movimento || 'Nenhum'));

            return true;

        } catch (error) {
            console.error('[BOOKMARKLET] Erro na execução:', error);
            alert('❌ Erro na execução do ato: ' + error.message);
            return false;
        }
    }

    // Interface para seleção do ato
    const tipoAto = prompt(
        '🏛️ SELETOR DE ATOS JUDICIAIS\\n\\n' +
        'Digite o código do ato desejado:\\n\\n' +
        '📋 ATOS DISPONÍVEIS:\\n' +
        '• meios - Meios de Execução\\n' +
        '• crda - Carta de Reclamada\\n' +
        '• crte - Carta de Reclamante\\n' +
        '• bloq - Bloqueio\\n' +
        '• idpj - IDPJ\\n' +
        '• termoE - Termo de Empresa\\n' +
        '• termoS - Termo de Sócio\\n' +
        '• edital - Edital\\n' +
        '• sobrestamento - Sobrestamento\\n' +
        '• pesquisas - Pesquisas BACEN/BNDT\\n\\n' +
        'Digite o código:'
    );

    if (tipoAto && ATOS[tipoAto.toLowerCase()]) {
        executarAtoJudicial(tipoAto.toLowerCase());
    } else if (tipoAto) {
        alert('❌ Código de ato inválido: ' + tipoAto);
    }

})();`;

// ====================================================
// BOOKMARKLETS INDIVIDUAIS SIMPLIFICADOS 
// ====================================================

const bookmarklet_meios = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xsmeios";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_crda = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="a reclda";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_crte = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xreit";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_bloq = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xsparcial";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_idpj = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="pjsem";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_termoE = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xempre";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_termoS = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xsocio";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_edital = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xsedit";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_sobrestamento = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="suspf";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

const bookmarklet_pesquisas = 'javascript:(function(){const c=document.querySelector("#inputFiltro");if(c){c.value="xsbacen";c.dispatchEvent(new Event("input",{bubbles:!0}));c.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,bubbles:!0}));setTimeout(()=>{const n=document.querySelector(".nodo-filtrado");n&&n.click()},500)}})();';

console.log('📋 Bookmarklets carregados! Use as constantes bookmarklet_* ou o bookmarklet_ato_judicial_completo');
