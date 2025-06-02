/**
 * BOOKMARKLET CARTA - Versão Testável
 * Use este código para testar no console primeiro
 */

(function() {
    'use strict';
    
    const ECARTA_USER = 's164283';
    const ECARTA_PASS = '59Justdoit!1';
    
    function showMessage(text, color = '#007bff') {
        const div = document.createElement('div');
        div.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            background: ${color}; color: white; padding: 10px 15px;
            border-radius: 5px; font-family: Arial; font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        div.textContent = text;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 4000);
    }
    
    function askForDate() {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.8); z-index: 9999;
                display: flex; align-items: center; justify-content: center;
            `;
            
            const content = document.createElement('div');
            content.style.cssText = `
                background: white; padding: 25px; border-radius: 10px;
                text-align: center; font-family: Arial, sans-serif;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            `;
            
            content.innerHTML = `
                <h3 style="margin-top: 0; color: #333;">Qual dia analisar?</h3>
                <p style="color: #666; margin: 15px 0;">
                    Digite 2 dígitos do dia (ex: 15)<br>
                    Deixe vazio para usar data mais recente
                </p>
                <input type="text" id="dayInput" maxlength="2" 
                       style="padding: 8px; border: 2px solid #ddd; border-radius: 4px; 
                              text-align: center; width: 60px; font-size: 16px; margin: 10px;">
                <br>
                <button id="okBtn" style="margin: 10px 5px; padding: 8px 15px; 
                       background: #007cba; color: white; border: none; border-radius: 4px; 
                       cursor: pointer; font-size: 14px;">OK</button>
                <button id="cancelBtn" style="margin: 10px 5px; padding: 8px 15px; 
                       background: #666; color: white; border: none; border-radius: 4px; 
                       cursor: pointer; font-size: 14px;">Cancelar</button>
            `;
            
            const input = content.querySelector('#dayInput');
            const okBtn = content.querySelector('#okBtn');
            const cancelBtn = content.querySelector('#cancelBtn');
            
            // Só aceitar números
            input.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
            
            // Enter para confirmar
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') okBtn.click();
            });
            
            okBtn.onclick = () => {
                const day = input.value.trim();
                modal.remove();
                resolve(day);
            };
            
            cancelBtn.onclick = () => {
                modal.remove();
                resolve(null);
            };
            
            modal.appendChild(content);
            document.body.appendChild(modal);
            
            // Foco no input
            setTimeout(() => input.focus(), 100);
        });
    }
    
    async function getIntimationIds(targetDay) {
        showMessage('Buscando intimações na timeline...');
        
        const timeline = document.querySelector('ul.pje-timeline');
        if (!timeline) {
            throw new Error('Timeline não encontrada. Abra a página de detalhes do processo.');
        }
        
        const items = Array.from(timeline.querySelectorAll('li'));
        const intimationIds = [];
        let processNumber = null;
        let dateFound = false;
        
        for (const item of items) {
            // Verifica se é uma data
            const dateDiv = item.querySelector('div.tl-data');
            if (dateDiv) {
                const dateText = dateDiv.textContent.trim();
                
                if (targetDay) {
                    // Busca data específica
                    const dayMatch = dateText.match(/^(\d{2})/);
                    if (dayMatch && dayMatch[1] === targetDay.padStart(2, '0')) {
                        dateFound = true;
                        console.log('Data encontrada:', dateText);
                    } else if (dateFound) {
                        // Saiu da data desejada
                        break;
                    } else {
                        // Continua procurando
                        continue;
                    }
                } else {
                    // Primeira data (mais recente)
                    if (dateFound) break;
                    dateFound = true;
                    console.log('Usando data mais recente:', dateText);
                }
                continue;
            }
            
            // Só processa se encontrou a data
            if (!dateFound) continue;
            
            // Busca por intimações
            const link = item.querySelector('a.tl-documento:not([target="_blank"])');
            if (!link) continue;
            
            const aria = link.getAttribute('aria-label') || '';
            const linkText = link.textContent.trim().toLowerCase();
            
            if (linkText.includes('intimação') || aria.toLowerCase().includes('intimação')) {
                console.log('Intimação encontrada:', linkText);
                
                // Clica no documento
                link.click();
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Procura botão HTML
                const htmlButton = document.querySelector('.fa-file-code');
                if (htmlButton) {
                    htmlButton.click();
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Extrai conteúdo
                    const preview = document.querySelector('#previewModeloDocumento');
                    if (preview) {
                        const texto = preview.textContent || preview.innerText || '';
                        
                        // Verifica se é correio
                        if (texto.toUpperCase().includes('NAO APAGAR NENHUM CARACTERE')) {
                            const idMatch = aria.match(/Id: ([a-f0-9]+)/);
                            const idCurto = idMatch ? idMatch[1] : item.id;
                            intimationIds.push(idCurto);
                            
                            // Extrai número do processo
                            if (!processNumber) {
                                const procMatch = texto.match(/(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})/);
                                if (procMatch) processNumber = procMatch[1];
                            }
                            
                            console.log('ID correio encontrado:', idCurto);
                        }
                        
                        // Fecha modal (ESC)
                        document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
                    }
                }
            }
        }
        
        return { intimationIds, processNumber };
    }
      function openECarta(processNumber) {
        if (!processNumber) {
            throw new Error('Número do processo não encontrado');
        }
        
        console.log('Abrindo eCarta para processo:', processNumber);
        const eCartaUrl = `https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo=${processNumber}`;
        
        const newWindow = window.open(eCartaUrl, '_blank');
        
        // Função para verificar se a página carregou e fazer login
        function checkAndLogin() {
            try {
                // Verifica se consegue acessar o documento da nova janela
                if (newWindow.document.readyState === 'complete') {
                    const userField = newWindow.document.querySelector('#input_user');
                    if (userField && userField.offsetParent !== null) {
                        console.log('Fazendo login no eCarta...');
                        showMessage('Fazendo login no eCarta...', '#ffc107');
                        
                        userField.value = ECARTA_USER;
                        const passField = newWindow.document.querySelector('#input_password');
                        const loginBtn = newWindow.document.querySelector('input.btn');
                        
                        if (passField && loginBtn) {
                            passField.value = ECARTA_PASS;
                            loginBtn.click();
                            
                            // Aguarda login e recarrega
                            setTimeout(() => {
                                newWindow.location.href = eCartaUrl;
                                showMessage('Login realizado! Aguarde carregar...', '#28a745');
                            }, 3000);
                        }
                    } else {
                        console.log('Já logado no eCarta ou página ainda carregando');
                        // Se não encontrou campo de login, assume que já está logado
                        showMessage('eCarta carregado!', '#28a745');
                    }
                } else {
                    // Página ainda não carregou completamente
                    setTimeout(checkAndLogin, 1000);
                }
            } catch (e) {
                console.log('Erro ao acessar eCarta (normal em cross-origin):', e.message);
                // Em caso de erro de CORS/cross-origin, apenas informa que abriu
                showMessage('eCarta aberto! Verifique login manualmente se necessário.', '#ffc107');
            }
        }
        
        // Inicia verificação após um tempo para a janela carregar
        setTimeout(checkAndLogin, 2000);
        
        return newWindow;
    }
      async function main() {
        try {
            // Pergunta a data
            const targetDay = await askForDate();
            if (targetDay === null) {
                showMessage('Operação cancelada', '#ffc107');
                return;
            }
            
            // Busca intimações
            const { intimationIds, processNumber } = await getIntimationIds(targetDay);
            
            if (!intimationIds.length) {
                throw new Error('Nenhuma intimação de correio encontrada');
            }
            
            showMessage(`${intimationIds.length} intimações encontradas!`, '#28a745');
            console.log('IDs encontrados:', intimationIds);
            console.log('Número do processo:', processNumber);
            
            // Abre eCarta
            showMessage('Abrindo eCarta...', '#007bff');
            const eCartaWindow = openECarta(processNumber);
            
            // Informa ao usuário para verificar a nova aba
            setTimeout(() => {
                showMessage('Verifique a aba do eCarta para ver os resultados!', '#28a745');
            }, 5000);
            
        } catch (error) {
            console.error('Erro:', error);
            showMessage(`Erro: ${error.message}`, '#dc3545');
        }
    }
    
    // Executa
    main();
    
})();
