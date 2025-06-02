// ====================================================
// BOOKMARKLETS SIMPLES - ATOS JUDICIAIS
// ====================================================
// Cada bookmarklet executa apenas: PEC, Prazo e Movimento
// Para usar na tela de minuta do PJe após inserir o modelo

// ====================================================
// 1. ATO MEIOS - Meios de Execução
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_meios = `javascript:(function(){
    console.log('[ATO MEIOS] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO MEIOS] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO MEIOS] Erro PEC:', e); }
    
    // Prazo - 5 dias para primeiro destinatário
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '5';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO MEIOS] Prazo 5 dias definido');
            }
        } catch(e) { console.log('[ATO MEIOS] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO MEIOS] Configuração completa!');
})();`;

// ====================================================
// 2. ATO CRDA - Carta de Reclamada
// ====================================================
// PEC: Não, Prazo: 15 dias, Movimento: Nenhum
const ato_crda = `javascript:(function(){
    console.log('[ATO CRDA] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO CRDA] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO CRDA] Erro PEC:', e); }
    
    // Prazo - 15 dias
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '15';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO CRDA] Prazo 15 dias definido');
            }
        } catch(e) { console.log('[ATO CRDA] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO CRDA] Configuração completa!');
})();`;

// ====================================================
// 3. ATO CRTE - Carta de Reclamante
// ====================================================
// PEC: Não, Prazo: 15 dias, Movimento: Nenhum
const ato_crte = `javascript:(function(){
    console.log('[ATO CRTE] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO CRTE] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO CRTE] Erro PEC:', e); }
    
    // Prazo - 15 dias
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '15';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO CRTE] Prazo 15 dias definido');
            }
        } catch(e) { console.log('[ATO CRTE] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO CRTE] Configuração completa!');
})();`;

// ====================================================
// 4. ATO BLOQ - Bloqueio
// ====================================================
// PEC: Sim, Prazo: Não altera, Movimento: Nenhum
const ato_bloq = `javascript:(function(){
    console.log('[ATO BLOQ] Configurando PEC, prazo e movimento...');
    
    // PEC - Marcar se não estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && !pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO BLOQ] PEC marcado');
        }
    } catch(e) { console.log('[ATO BLOQ] Erro PEC:', e); }
    
    console.log('[ATO BLOQ] Configuração completa!');
})();`;

// ====================================================
// 5. ATO IDPJ - IDPJ
// ====================================================
// PEC: Sim, Prazo: 8 dias, Movimento: Nenhum
const ato_idpj = `javascript:(function(){
    console.log('[ATO IDPJ] Configurando PEC, prazo e movimento...');
    
    // PEC - Marcar se não estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && !pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO IDPJ] PEC marcado');
        }
    } catch(e) { console.log('[ATO IDPJ] Erro PEC:', e); }
    
    // Prazo - 8 dias
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '8';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO IDPJ] Prazo 8 dias definido');
            }
        } catch(e) { console.log('[ATO IDPJ] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO IDPJ] Configuração completa!');
})();`;

// ====================================================
// 6. ATO TERMO E - Termo de Empresa
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_termoE = `javascript:(function(){
    console.log('[ATO TERMO E] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO TERMO E] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO TERMO E] Erro PEC:', e); }
    
    // Prazo - 5 dias para primeiro destinatário
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '5';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO TERMO E] Prazo 5 dias definido');
            }
        } catch(e) { console.log('[ATO TERMO E] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO TERMO E] Configuração completa!');
})();`;

// ====================================================
// 7. ATO TERMO S - Termo de Sócio
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_termoS = `javascript:(function(){
    console.log('[ATO TERMO S] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO TERMO S] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO TERMO S] Erro PEC:', e); }
    
    // Prazo - 5 dias para primeiro destinatário
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '5';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO TERMO S] Prazo 5 dias definido');
            }
        } catch(e) { console.log('[ATO TERMO S] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO TERMO S] Configuração completa!');
})();`;

// ====================================================
// 8. ATO EDITAL - Edital
// ====================================================
// PEC: Não, Prazo: 5 dias (primeiro destinatário), Movimento: Nenhum
const ato_edital = `javascript:(function(){
    console.log('[ATO EDITAL] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO EDITAL] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO EDITAL] Erro PEC:', e); }
    
    // Prazo - 5 dias para primeiro destinatário
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '5';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO EDITAL] Prazo 5 dias definido');
            }
        } catch(e) { console.log('[ATO EDITAL] Erro prazo:', e); }
    }, 500);
    
    console.log('[ATO EDITAL] Configuração completa!');
})();`;

// ====================================================
// 9. ATO SOBRESTAMENTO - Sobrestamento
// ====================================================
// PEC: Não, Prazo: 0 dias, Movimento: frustrada
const ato_sobrestamento = `javascript:(function(){
    console.log('[ATO SOBRESTAMENTO] Configurando PEC, prazo e movimento...');
    
    // PEC - Desmarcar se estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO SOBRESTAMENTO] PEC desmarcado');
        }
    } catch(e) { console.log('[ATO SOBRESTAMENTO] Erro PEC:', e); }
    
    // Prazo - 0 dias
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '0';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO SOBRESTAMENTO] Prazo 0 dias definido');
            }
        } catch(e) { console.log('[ATO SOBRESTAMENTO] Erro prazo:', e); }
    }, 500);
    
    // Movimento - frustrada
    setTimeout(() => {
        try {
            // Ativar aba de movimentos se necessário
            const abaMovimentos = Array.from(document.querySelectorAll('.mat-tab-label'))
                .find(tab => tab.textContent.toLowerCase().includes('movimentos'));
            
            if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                abaMovimentos.click();
                
                setTimeout(() => {
                    // Buscar e marcar movimento "frustrada"
                    const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
                    for (const checkbox of checkboxes) {
                        const label = checkbox.querySelector('.mat-checkbox-label');
                        if (label && label.textContent.toLowerCase().includes('frustrada')) {
                            const input = checkbox.querySelector('input[type="checkbox"]');
                            if (input && !input.checked) {
                                input.click();
                                console.log('[ATO SOBRESTAMENTO] Movimento "frustrada" marcado');
                                break;
                            }
                        }
                    }
                }, 700);
            }
        } catch(e) { console.log('[ATO SOBRESTAMENTO] Erro movimento:', e); }
    }, 1000);
    
    console.log('[ATO SOBRESTAMENTO] Configuração completa!');
})();`;

// ====================================================
// 10. ATO PESQUISAS - Pesquisas BACEN/BNDT
// ====================================================
// PEC: Sim, Prazo: 30 dias (primeiro destinatário), Movimento: bloqueio
const ato_pesquisas = `javascript:(function(){
    console.log('[ATO PESQUISAS] Configurando PEC, prazo e movimento...');
    
    // PEC - Marcar se não estiver marcado
    try {
        const pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"] input');
        if (pecCheckbox && !pecCheckbox.checked) {
            pecCheckbox.click();
            console.log('[ATO PESQUISAS] PEC marcado');
        }
    } catch(e) { console.log('[ATO PESQUISAS] Erro PEC:', e); }
    
    // Prazo - 30 dias para primeiro destinatário
    setTimeout(() => {
        try {
            const campoPrazo = document.querySelector('input[formcontrolname="prazo"]');
            if (campoPrazo) {
                campoPrazo.value = '30';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                console.log('[ATO PESQUISAS] Prazo 30 dias definido');
            }
        } catch(e) { console.log('[ATO PESQUISAS] Erro prazo:', e); }
    }, 500);
    
    // Movimento - bloqueio
    setTimeout(() => {
        try {
            // Ativar aba de movimentos se necessário
            const abaMovimentos = Array.from(document.querySelectorAll('.mat-tab-label'))
                .find(tab => tab.textContent.toLowerCase().includes('movimentos'));
            
            if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                abaMovimentos.click();
                
                setTimeout(() => {
                    // Buscar e marcar movimento "bloqueio"
                    const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
                    for (const checkbox of checkboxes) {
                        const label = checkbox.querySelector('.mat-checkbox-label');
                        if (label && label.textContent.toLowerCase().includes('bloqueio')) {
                            const input = checkbox.querySelector('input[type="checkbox"]');
                            if (input && !input.checked) {
                                input.click();
                                console.log('[ATO PESQUISAS] Movimento "bloqueio" marcado');
                                break;
                            }
                        }
                    }
                }, 700);
            }
        } catch(e) { console.log('[ATO PESQUISAS] Erro movimento:', e); }
    }, 1000);
    
    console.log('[ATO PESQUISAS] Configuração completa!');
})();`;

// ====================================================
// INSTRUÇÕES DE USO
// ====================================================
/*
COMO USAR OS BOOKMARKLETS:

1. Copie o código de cada ato (entre as aspas) 
2. Crie um favorito/marcador no navegador
3. Cole o código como URL do favorito
4. Nomeie o favorito (ex: "Ato Meios", "Ato IDPJ", etc.)

QUANDO USAR:
- Na tela de minuta do PJe
- APÓS inserir o modelo do ato
- Clique no bookmarklet para configurar automaticamente PEC, prazo e movimento

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
