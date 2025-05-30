// BOOKMARKLETS SIMPLES - ATOS JUDICIAIS (CORRIGIDOS)
// ====================================================
// Cada bookmarklet executa apenas: PEC, Prazo e Movimento
// Para usar na tela de minuta do PJe após inserir o modelo
// SELETORES CORRIGIDOS baseados no atos.py que funciona

// ====================================================
// FUNÇÕES UTILITÁRIAS
// ====================================================

    // 1. PEC: Marcar/desmarcar PEC
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[BOOKMARKLET] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[BOOKMARKLET] PEC desmarcado');
                }
                return true;
            } else {
                console.error('[BOOKMARKLET] Checkbox PEC não encontrado');
                return false;
            }
        } catch (error) {
            console.error('[BOOKMARKLET] Erro ao configurar PEC:', error);
            return false;
        }
    }

    // 2. PRAZO: Define os dias de prazo usando seletores corretos do atos.py
    function setPrazo(dias) {
        try {
            // Seleciona campos de prazo usando os mesmos seletores do atos.py
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            
            for (const tr of linhas) {
                try {
                    // Verifica se o destinatário está marcado
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        // Preenche o campo de prazo desta linha
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {
                    // Ignora erros de linha individual
                }
            }
            
            if (preenchidos > 0) {
                console.log(`[BOOKMARKLET] Prazo definido: ${dias} dias (${preenchidos} destinatários)`);
                return true;
            } else {
                console.error('[BOOKMARKLET] Nenhum campo de prazo encontrado ou destinatário marcado');
                return false;
            }
        } catch (error) {
            console.error('[BOOKMARKLET] Erro ao definir prazo:', error);
            return false;
        }
    }

    // 3. MOVIMENTO: Selecionar movimento específico
    function setMovimento(textoMovimento) {
        try {
            // Ativar aba de movimentos se necessário
            const abaMovimentos = Array.from(document.querySelectorAll('.mat-tab-label'))
                .find(tab => tab.textContent.toLowerCase().includes('movimentos'));
            
            if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                abaMovimentos.click();
                
                setTimeout(() => {
                    // Buscar e marcar movimento
                    const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
                    for (const checkbox of checkboxes) {
                        const label = checkbox.querySelector('.mat-checkbox-label');
                        if (label && label.textContent.toLowerCase().includes(textoMovimento.toLowerCase())) {
                            const input = checkbox.querySelector('input[type="checkbox"]');
                            if (input && !input.checked) {
                                input.click();
                                console.log(`[BOOKMARKLET] Movimento "${textoMovimento}" marcado`);
                                return true;
                            }
                        }
                    }
                    console.error(`[BOOKMARKLET] Movimento "${textoMovimento}" não encontrado`);
                    return false;
                }, 700);
            }
        } catch (error) {
            console.error('[BOOKMARKLET] Erro ao selecionar movimento:', error);
            return false;
        }
    }

// ====================================================
// 1. ATO MEIOS - Meios de Execução
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_meios = `javascript:(function(){
    console.log('[ATO MEIOS] Configurando PEC, prazo e movimento...');
    
    // Função PEC
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO MEIOS] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO MEIOS] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO MEIOS] Erro PEC:', error);
            return false;
        }
    }

    // Função Prazo corrigida
    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO MEIOS] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO MEIOS] Erro prazo:', error);
            return false;
        }
    }

    // Executar ações
    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(5); }, 500); // Prazo: 5 dias
    console.log('[ATO MEIOS] Configuração completa!');
})();`;

// ====================================================
// 2. ATO CRDA - Carta de Reclamada
// ====================================================
// PEC: Não, Prazo: 15 dias, Movimento: Nenhum
const ato_crda = `javascript:(function(){
    console.log('[ATO CRDA] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO CRDA] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO CRDA] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO CRDA] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO CRDA] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO CRDA] Erro prazo:', error);
            return false;
        }
    }

    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(15); }, 500); // Prazo: 15 dias
    console.log('[ATO CRDA] Configuração completa!');
})();`;

// ====================================================
// 3. ATO CRTE - Carta de Reclamante
// ====================================================
// PEC: Não, Prazo: 15 dias, Movimento: Nenhum
const ato_crte = `javascript:(function(){
    console.log('[ATO CRTE] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO CRTE] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO CRTE] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO CRTE] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO CRTE] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO CRTE] Erro prazo:', error);
            return false;
        }
    }

    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(15); }, 500); // Prazo: 15 dias
    console.log('[ATO CRTE] Configuração completa!');
})();`;

// ====================================================
// 4. ATO BLOQ - Bloqueio
// ====================================================
// PEC: Sim, Prazo: Não altera, Movimento: Nenhum
const ato_bloq = `javascript:(function(){
    console.log('[ATO BLOQ] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO BLOQ] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO BLOQ] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO BLOQ] Erro PEC:', error);
            return false;
        }
    }

    setPEC(true); // PEC: Sim
    console.log('[ATO BLOQ] Configuração completa!');
})();`;

// ====================================================
// 5. ATO IDPJ - IDPJ
// ====================================================
// PEC: Sim, Prazo: 8 dias, Movimento: Nenhum
const ato_idpj = `javascript:(function(){
    console.log('[ATO IDPJ] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO IDPJ] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO IDPJ] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO IDPJ] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO IDPJ] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO IDPJ] Erro prazo:', error);
            return false;
        }
    }

    setPEC(true); // PEC: Sim
    setTimeout(() => { setPrazo(8); }, 500); // Prazo: 8 dias
    console.log('[ATO IDPJ] Configuração completa!');
})();`;

// ====================================================
// 6. ATO TERMO E - Termo de Empresa
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_termoE = `javascript:(function(){
    console.log('[ATO TERMO E] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO TERMO E] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO TERMO E] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO TERMO E] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO TERMO E] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO TERMO E] Erro prazo:', error);
            return false;
        }
    }

    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(5); }, 500); // Prazo: 5 dias
    console.log('[ATO TERMO E] Configuração completa!');
})();`;

// ====================================================
// 7. ATO TERMO S - Termo de Sócio
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_termoS = `javascript:(function(){
    console.log('[ATO TERMO S] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO TERMO S] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO TERMO S] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO TERMO S] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO TERMO S] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO TERMO S] Erro prazo:', error);
            return false;
        }
    }

    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(5); }, 500); // Prazo: 5 dias
    console.log('[ATO TERMO S] Configuração completa!');
})();`;

// ====================================================
// 8. ATO EDITAL - Edital
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_edital = `javascript:(function(){
    console.log('[ATO EDITAL] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO EDITAL] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO EDITAL] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO EDITAL] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO EDITAL] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO EDITAL] Erro prazo:', error);
            return false;
        }
    }

    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(5); }, 500); // Prazo: 5 dias
    console.log('[ATO EDITAL] Configuração completa!');
})();`;

// ====================================================
// 9. ATO SOBRESTAMENTO - Sobrestamento
// ====================================================
// PEC: Não, Prazo: 0 dias, Movimento: frustrada
const ato_sobrestamento = `javascript:(function(){
    console.log('[ATO SOBRESTAMENTO] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO SOBRESTAMENTO] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO SOBRESTAMENTO] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO SOBRESTAMENTO] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO SOBRESTAMENTO] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO SOBRESTAMENTO] Erro prazo:', error);
            return false;
        }
    }

    function setMovimento(textoMovimento) {
        try {
            const abaMovimentos = Array.from(document.querySelectorAll('.mat-tab-label'))
                .find(tab => tab.textContent.toLowerCase().includes('movimentos'));
            
            if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                abaMovimentos.click();
                
                setTimeout(() => {
                    const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
                    for (const checkbox of checkboxes) {
                        const label = checkbox.querySelector('.mat-checkbox-label');
                        if (label && label.textContent.toLowerCase().includes(textoMovimento.toLowerCase())) {
                            const input = checkbox.querySelector('input[type="checkbox"]');
                            if (input && !input.checked) {
                                input.click();
                                console.log('[ATO SOBRESTAMENTO] Movimento "' + textoMovimento + '" marcado');
                                return true;
                            }
                        }
                    }
                    console.error('[ATO SOBRESTAMENTO] Movimento "' + textoMovimento + '" não encontrado');
                    return false;
                }, 700);
            }
        } catch (error) {
            console.error('[ATO SOBRESTAMENTO] Erro movimento:', error);
            return false;
        }
    }

    setPEC(false); // PEC: Não
    setTimeout(() => { setPrazo(0); }, 500); // Prazo: 0 dias
    setTimeout(() => { setMovimento('frustrada'); }, 1000); // Movimento: frustrada
    console.log('[ATO SOBRESTAMENTO] Configuração completa!');
})();`;

// ====================================================
// 10. ATO PESQUISAS - Pesquisas BACEN/BNDT
// ====================================================
// PEC: Sim, Prazo: 30 dias (primeiro destinatário), Movimento: bloqueio
const ato_pesquisas = `javascript:(function(){
    console.log('[ATO PESQUISAS] Configurando PEC, prazo e movimento...');
    
    function setPEC(marcar) {
        try {
            const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
            if (pecCheckbox) {
                if (marcar && !pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO PESQUISAS] PEC marcado');
                } else if (!marcar && pecCheckbox.checked) {
                    pecCheckbox.click();
                    console.log('[ATO PESQUISAS] PEC desmarcado');
                }
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO PESQUISAS] Erro PEC:', error);
            return false;
        }
    }

    function setPrazo(dias) {
        try {
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');
            let preenchidos = 0;
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    if (checkbox && checkbox.getAttribute('aria-checked') === 'true') {
                        const campoPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');
                        if (campoPrazo) {
                            campoPrazo.focus();
                            campoPrazo.value = dias.toString();
                            campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                            campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                            preenchidos++;
                        }
                    }
                } catch (e) {}
            }
            if (preenchidos > 0) {
                console.log('[ATO PESQUISAS] Prazo ' + dias + ' dias definido (' + preenchidos + ' destinatários)');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ATO PESQUISAS] Erro prazo:', error);
            return false;
        }
    }

    function setMovimento(textoMovimento) {
        try {
            const abaMovimentos = Array.from(document.querySelectorAll('.mat-tab-label'))
                .find(tab => tab.textContent.toLowerCase().includes('movimentos'));
            
            if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                abaMovimentos.click();
                
                setTimeout(() => {
                    const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
                    for (const checkbox of checkboxes) {
                        const label = checkbox.querySelector('.mat-checkbox-label');
                        if (label && label.textContent.toLowerCase().includes(textoMovimento.toLowerCase())) {
                            const input = checkbox.querySelector('input[type="checkbox"]');
                            if (input && !input.checked) {
                                input.click();
                                console.log('[ATO PESQUISAS] Movimento "' + textoMovimento + '" marcado');
                                return true;
                            }
                        }
                    }
                    console.error('[ATO PESQUISAS] Movimento "' + textoMovimento + '" não encontrado');
                    return false;
                }, 700);
            }
        } catch (error) {
            console.error('[ATO PESQUISAS] Erro movimento:', error);
            return false;
        }
    }

    setPEC(true); // PEC: Sim
    setTimeout(() => { setPrazo(30); }, 500); // Prazo: 30 dias
    setTimeout(() => { setMovimento('bloqueio'); }, 1000); // Movimento: bloqueio
    console.log('[ATO PESQUISAS] Configuração completa!');
})();`;

// ====================================================
// INSTRUÇÕES DE USO
// ====================================================
/*
BOOKMARKLETS CORRIGIDOS - SELETORES BASEADOS NO ATOS.PY QUE FUNCIONA

COMO USAR OS BOOKMARKLETS:
1. Copie o código de cada ato (entre as aspas) 
2. Crie um favorito/marcador no navegador
3. Cole o código como URL do favorito
4. Nomeie o favorito (ex: "Ato Meios", "Ato IDPJ", etc.)

QUANDO USAR:
- Na tela de minuta do PJe
- APÓS inserir o modelo do ato
- Clique no bookmarklet para configurar automaticamente PEC, prazo e movimento

CORREÇÃO APLICADA:
- Seletor de prazo corrigido: table.t-class tr.ng-star-inserted → mat-form-field.prazo input[type="text"].mat-input-element
- Agora usa os mesmos seletores que funcionam no atos.py

ATOS DISPONÍVEIS:
• ato_meios - Meios de Execução (PEC: Não, Prazo: 5 dias primeiro dest.)
• ato_crda - Carta de Reclamada (PEC: Não, Prazo: 15 dias)
• ato_crte - Carta de Reclamante (PEC: Não, Prazo: 15 dias)
• ato_bloq - Bloqueio (PEC: Sim, Prazo: não altera)
• ato_idpj - IDPJ (PEC: Sim, Prazo: 8 dias)
• ato_termoE - Termo de Empresa (PEC: Não, Prazo: 5 dias primeiro dest.)
• ato_termoS - Termo de Sócio (PEC: Não, Prazo: 5 dias primeiro dest.)
• ato_edital - Edital (PEC: Não, Prazo: 5 dias primeiro dest.)
• ato_sobrestamento - Sobrestamento (PEC: Não, Prazo: 0, Movimento: frustrada)
• ato_pesquisas - Pesquisas BACEN/BNDT (PEC: Sim, Prazo: 30 dias primeiro dest., Movimento: bloqueio)
*/
