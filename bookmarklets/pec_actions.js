// ====================
// BOOKMARKLET PEC - Ações para Processo Eletrônico Colaborativo
// ====================

javascript:(function(){
    // Funções auxiliares comuns
    function esperarElemento(seletor, timeout = 5000) {
        return new Promise((resolve) => {
            const start = Date.now();
            const check = () => {
                const element = document.querySelector(seletor);
                if (element) {
                    resolve(element);
                } else if (Date.now() - start < timeout) {
                    setTimeout(check, 100);
                } else {
                    resolve(null);
                }
            };
            check();
        });
    }

    function clicarElemento(elemento) {
        if (elemento) {
            elemento.scrollIntoView({block: 'center'});
            elemento.click();
            return true;
        }
        return false;
    }

    function criarBotaoFlutuante() {
        if (document.getElementById('pje-bookmarklet-pec')) return;
        
        const botao = document.createElement('div');
        botao.id = 'pje-bookmarklet-pec';
        botao.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; z-index: 99999; background: #2196F3; color: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); font-family: Arial, sans-serif; cursor: move;">
                <div style="font-weight: bold; margin-bottom: 10px; text-align: center;">PJe Plus - PEC</div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <button onclick="executarPecBloqueio()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #FF9800; color: white; cursor: pointer; font-size: 12px;">PEC Bloqueio</button>
                    <button onclick="executarPecDecisao()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #4CAF50; color: white; cursor: pointer; font-size: 12px;">PEC Decisão</button>
                    <button onclick="executarPecIdpj()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #9C27B0; color: white; cursor: pointer; font-size: 12px;">PEC IDPJ</button>
                    <button onclick="executarPecGeral()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #607D8B; color: white; cursor: pointer; font-size: 12px;">PEC Geral</button>
                    <button onclick="document.getElementById('pje-bookmarklet-pec').remove()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #f44336; color: white; cursor: pointer; font-size: 12px;">Fechar</button>
                </div>
            </div>
        `;
        document.body.appendChild(botao);

        // Tornar o botão arrastável
        let isDragging = false;
        let currentX, currentY, initialX, initialY;
        const header = botao.firstElementChild;
        
        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            initialX = e.clientX - botao.offsetLeft;
            initialY = e.clientY - botao.offsetTop;
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                header.style.left = currentX + 'px';
                header.style.top = currentY + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    // Função para marcar/desmarcar PEC
    async function alterarPec(marcar = true) {
        try {
            let pecCheckbox = null;
            let pecInput = null;

            // Busca o checkbox PEC
            const seletores = [
                'mat-checkbox[aria-label="Enviar para PEC"]',
                'div.checkbox-pec mat-checkbox',
                'input[type="checkbox"][aria-label="Enviar para PEC"]'
            ];

            for (const seletor of seletores) {
                const elemento = await esperarElemento(seletor);
                if (elemento) {
                    if (elemento.tagName === 'MAT-CHECKBOX') {
                        pecCheckbox = elemento;
                        pecInput = elemento.querySelector('input[type="checkbox"]');
                    } else if (elemento.tagName === 'INPUT') {
                        pecInput = elemento;
                        pecCheckbox = elemento.closest('mat-checkbox');
                    }
                    break;
                }
            }

            if (!pecCheckbox || !pecInput) {
                console.log('[PEC] Checkbox PEC não encontrado');
                return false;
            }

            // Verifica estado atual
            const checked = pecInput.checked || 
                          pecInput.getAttribute('aria-checked') === 'true' ||
                          pecCheckbox.classList.contains('mat-checkbox-checked');

            console.log(`[PEC] Estado atual: ${checked ? 'marcado' : 'desmarcado'}, alvo: ${marcar ? 'marcar' : 'desmarcar'}`);

            // Executa ação se necessário
            if ((marcar && !checked) || (!marcar && checked)) {
                const label = pecCheckbox.querySelector('label.mat-checkbox-layout');
                if (label) {
                    clicarElemento(label);
                } else {
                    clicarElemento(pecCheckbox);
                }
                console.log(`[PEC] Checkbox ${marcar ? 'marcado' : 'desmarcado'}`);
                return true;
            }

            console.log('[PEC] Nenhuma ação necessária');
            return true;

        } catch (error) {
            console.error('[PEC] Erro ao alterar PEC:', error);
            return false;
        }
    }

    // Executa comunicação PEC para bloqueio
    window.executarPecBloqueio = async function() {
        console.log('[PEC BLOQUEIO] Iniciando...');
        
        try {
            // Marcar PEC
            await alterarPec(true);
            
            // Definir prazo de 7 dias para intimação
            const campoPrazo = await esperarElemento('input[formcontrolname="prazo"], input[type="number"]');
            if (campoPrazo) {
                campoPrazo.value = '7';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                console.log('[PEC BLOQUEIO] Prazo definido: 7 dias');
            }

            alert('PEC Bloqueio configurado!\n- PEC: Marcado\n- Prazo: 7 dias\n- Modelo sugerido: zzintbloq');
            
        } catch (error) {
            console.error('[PEC BLOQUEIO] Erro:', error);
            alert('Erro ao configurar PEC Bloqueio: ' + error.message);
        }
    };

    // Executa comunicação PEC para decisão
    window.executarPecDecisao = async function() {
        console.log('[PEC DECISÃO] Iniciando...');
        
        try {
            // Marcar PEC
            await alterarPec(true);
            
            // Definir prazo de 10 dias para intimação
            const campoPrazo = await esperarElemento('input[formcontrolname="prazo"], input[type="number"]');
            if (campoPrazo) {
                campoPrazo.value = '10';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                console.log('[PEC DECISÃO] Prazo definido: 10 dias');
            }

            alert('PEC Decisão configurado!\n- PEC: Marcado\n- Prazo: 10 dias\n- Modelo sugerido: xs dec reg');
            
        } catch (error) {
            console.error('[PEC DECISÃO] Erro:', error);
            alert('Erro ao configurar PEC Decisão: ' + error.message);
        }
    };

    // Executa comunicação PEC para IDPJ
    window.executarPecIdpj = async function() {
        console.log('[PEC IDPJ] Iniciando...');
        
        try {
            // Marcar PEC
            await alterarPec(true);
            
            // Definir prazo de 17 dias para defesa IDPJ
            const campoPrazo = await esperarElemento('input[formcontrolname="prazo"], input[type="number"]');
            if (campoPrazo) {
                campoPrazo.value = '17';
                campoPrazo.dispatchEvent(new Event('input', {bubbles: true}));
                campoPrazo.dispatchEvent(new Event('change', {bubbles: true}));
                console.log('[PEC IDPJ] Prazo definido: 17 dias');
            }

            alert('PEC IDPJ configurado!\n- PEC: Marcado\n- Prazo: 17 dias\n- Modelo sugerido: xidpj c');
            
        } catch (error) {
            console.error('[PEC IDPJ] Erro:', error);
            alert('Erro ao configurar PEC IDPJ: ' + error.message);
        }
    };

    // Executa PEC geral (apenas marca/desmarca)
    window.executarPecGeral = async function() {
        const opcao = confirm('Marcar PEC?\n\nOK = Marcar PEC\nCancelar = Desmarcar PEC');
        
        try {
            await alterarPec(opcao);
            alert(`PEC ${opcao ? 'marcado' : 'desmarcado'} com sucesso!`);
        } catch (error) {
            console.error('[PEC GERAL] Erro:', error);
            alert('Erro ao alterar PEC: ' + error.message);
        }
    };

    // Criar interface
    criarBotaoFlutuante();
    
})();
