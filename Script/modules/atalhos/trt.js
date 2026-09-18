// Módulo TRT - Botão injetado no modal de endereços
(function () {
    'use strict';

    const URL_ATUAL = window.location.href;
    if (!URL_ATUAL.includes('/comunicacoesprocessuais/minutas')) return;

    // Observa a abertura do modal
    const observer = new MutationObserver((mutations) => {
        for (let m of mutations) {
            for (let n of m.addedNodes) {
                if (n.nodeType === 1 && n.classList && n.classList.contains('pec-dialogo-endereco')) {
                    injectButton(n);
                } else if (n.nodeType === 1 && n.querySelector('.pec-dialogo-endereco')) {
                    injectButton(n.querySelector('.pec-dialogo-endereco'));
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    function injectButton(modal) {
        if (modal.querySelector('#btn-trt-injetado')) return;
        
        let container = document.createElement('div');
        container.style.cssText = 'padding: 10px; text-align: center; border-top: 1px solid #ccc; background: #f9f9f9;';
        
        let btn = document.createElement('button');
        btn.id = 'btn-trt-injetado';
        btn.textContent = 'TRIBUNAL';
        btn.className = 'mat-raised-button mat-button-base mat-primary';
        btn.style.cssText = 'padding: 8px 16px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 14px;';
        
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            btn.textContent = 'Buscando...';
            btn.style.opacity = '0.7';
            btn.disabled = true;
            await executarFluxoTribunal(modal);
            btn.textContent = 'TRIBUNAL';
            btn.style.opacity = '1';
            btn.disabled = false;
        });

        container.appendChild(btn);
        modal.appendChild(container);
    }

    async function executarFluxoTribunal(modal) {
        // 1. Procura na tabela atual
        if (await selecionarTribunalNaTabela(modal)) return;

        // 2. Não achou, filtra por TRI
        let inputLogradouro = modal.querySelector('input#logradouro');
        if (inputLogradouro) {
            preencherValor(inputLogradouro, 'TRI');
            let btnFiltrar = modal.querySelector('button[mattooltip="Filtrar"], button.botao-filtro');
            if (btnFiltrar) {
                btnFiltrar.click();
                await sleep(1500); // Aguarda a busca
                if (await selecionarTribunalNaTabela(modal)) return;
            }
        }

        // 3. Não achou, inclui via CEP 01302906
        let inputCep = modal.querySelector('input#inputCep');
        if (inputCep) {
            inputCep.focus();
            inputCep.value = '';
            inputCep.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
            await sleep(200);
            
            let cep_str = '01302906';
            for (let char of cep_str) {
                inputCep.dispatchEvent(new KeyboardEvent('keydown',  { key: char, bubbles: true, cancelable: true }));
                inputCep.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true, cancelable: true, charCode: char.charCodeAt(0) }));
                inputCep.value += char;
                inputCep.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: char }));
                inputCep.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
                await sleep(50);
            }
            inputCep.dispatchEvent(new Event('change', { bubbles: true }));
            inputCep.dispatchEvent(new Event('blur', { bubbles: true }));
            
            await sleep(2000); // Aguarda o PJe consultar os correios e preencher estado/cidade/rua
            
            let btnSalvar = modal.querySelector('button.botao-salvar');
            if (btnSalvar && !btnSalvar.disabled) {
                btnSalvar.click();
                await sleep(1500); // Aguarda salvar o endereço no backend
                
                // Tenta selecionar após salvar
                let selecionou = await selecionarTribunalNaTabela(modal);
                if (!selecionou) {
                    // Se não apareceu de primeira, clica em filtrar sem termo para recarregar a tabela
                    let inputLogradouro2 = modal.querySelector('input#logradouro');
                    if (inputLogradouro2) {
                        preencherValor(inputLogradouro2, '');
                        let btnFiltrar2 = modal.querySelector('button[mattooltip="Filtrar"], button.botao-filtro');
                        if (btnFiltrar2) btnFiltrar2.click();
                        await sleep(1500);
                        await selecionarTribunalNaTabela(modal);
                    }
                }
            } else {
                console.error('[TRT] Botão salvar não habilitou. Verifique se o CEP foi preenchido corretamente.');
            }
        }
    }

    async function selecionarTribunalNaTabela(modal) {
        let tabela = modal.querySelector('table[name="Endereços do destinatário no sistema"]');
        if (!tabela) return false;
        
        let linhas = tabela.querySelectorAll('tbody tr');
        for (let tr of linhas) {
            let texto = tr.textContent.toUpperCase();
            if (texto.includes('TRIBUNAL') || 
                texto.includes('01302-906') || 
                texto.includes('01302906') ||
                texto.includes('CONSOLACAO') ||
                texto.includes('CONSOLAÇÃO')) {
                
                let btnSelecionar = tr.querySelector('button[aria-label="Selecionar endereço"]');
                if (btnSelecionar) {
                    btnSelecionar.click();
                    return true;
                }
            }
        }
        return false;
    }

    function preencherValor(el, valor) {
        el.value = valor;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

})();
