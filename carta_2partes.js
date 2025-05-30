/**
 * BOOKMARKLET CARTA - Versão em 2 Partes
 * Parte 1: Executa no PJe para encontrar intimações
 * Parte 2: Executa no eCarta para fazer login e buscar dados
 */

// =================
// PARTE 1: PJE
// =================
(function() {
    'use strict';
    
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
            
            input.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
            
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
            const dateDiv = item.querySelector('div.tl-data');
            if (dateDiv) {
                const dateText = dateDiv.textContent.trim();
                
                if (targetDay) {
                    const dayMatch = dateText.match(/^(\d{2})/);
                    if (dayMatch && dayMatch[1] === targetDay.padStart(2, '0')) {
                        dateFound = true;
                        console.log('Data encontrada:', dateText);
                    } else if (dateFound) {
                        break;
                    } else {
                        continue;
                    }
                } else {
                    if (dateFound) break;
                    dateFound = true;
                    console.log('Usando data mais recente:', dateText);
                }
                continue;
            }
            
            if (!dateFound) continue;
            
            const link = item.querySelector('a.tl-documento:not([target="_blank"])');
            if (!link) continue;
            
            const aria = link.getAttribute('aria-label') || '';
            const linkText = link.textContent.trim().toLowerCase();
            
            if (linkText.includes('intimação') || aria.toLowerCase().includes('intimação')) {
                console.log('Intimação encontrada:', linkText);
                
                link.click();
                await new Promise(resolve => setTimeout(resolve, 500));
                
                const htmlButton = document.querySelector('.fa-file-code');
                if (htmlButton) {
                    htmlButton.click();
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    const preview = document.querySelector('#previewModeloDocumento');
                    if (preview) {
                        const texto = preview.textContent || preview.innerText || '';
                        
                        if (texto.toUpperCase().includes('NAO APAGAR NENHUM CARACTERE')) {
                            const idMatch = aria.match(/Id: ([a-f0-9]+)/);
                            const idCurto = idMatch ? idMatch[1] : item.id;
                            intimationIds.push(idCurto);
                            
                            if (!processNumber) {
                                const procMatch = texto.match(/(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})/);
                                if (procMatch) processNumber = procMatch[1];
                            }
                            
                            console.log('ID correio encontrado:', idCurto);
                        }
                        
                        document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
                    }
                }
            }
        }
        
        return { intimationIds, processNumber };
    }
    
    function saveDataAndOpenECarta(intimationIds, processNumber) {
        // Salva dados no localStorage para usar no eCarta
        const cartaData = {
            intimationIds: intimationIds,
            processNumber: processNumber,
            timestamp: Date.now()
        };
        
        localStorage.setItem('cartaBookmarkletData', JSON.stringify(cartaData));
        console.log('Dados salvos:', cartaData);
        
        // Abre eCarta
        const eCartaUrl = `https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo=${processNumber}`;
        window.open(eCartaUrl, '_blank');
        
        showMessage('Dados salvos! Agora execute o bookmarklet na aba do eCarta.', '#28a745');
    }
    
    async function main() {
        try {
            // Verifica se está no PJe ou eCarta
            const currentUrl = window.location.href;
            
            if (currentUrl.includes('aplicacoes1.trt2.jus.br/eCarta-web')) {
                // PARTE 2: EXECUÇÃO NO ECARTA
                executeECartaPart();
                return;
            }
            
            // PARTE 1: EXECUÇÃO NO PJE
            const targetDay = await askForDate();
            if (targetDay === null) {
                showMessage('Operação cancelada', '#ffc107');
                return;
            }
            
            const { intimationIds, processNumber } = await getIntimationIds(targetDay);
            
            if (!intimationIds.length) {
                throw new Error('Nenhuma intimação de correio encontrada');
            }
            
            showMessage(`${intimationIds.length} intimações encontradas!`, '#28a745');
            console.log('IDs encontrados:', intimationIds);
            console.log('Número do processo:', processNumber);
            
            saveDataAndOpenECarta(intimationIds, processNumber);
            
        } catch (error) {
            console.error('Erro:', error);
            showMessage(`Erro: ${error.message}`, '#dc3545');
        }
    }
    
    // PARTE 2: FUNÇÃO PARA EXECUTAR NO ECARTA
    function executeECartaPart() {
        const ECARTA_USER = 's164283';
        const ECARTA_PASS = '59Justdoit!1';
        
        console.log('Executando parte eCarta do bookmarklet...');
        
        // Recupera dados salvos
        const savedData = localStorage.getItem('cartaBookmarkletData');
        if (!savedData) {
            showMessage('Dados não encontrados! Execute primeiro no PJe.', '#dc3545');
            return;
        }
        
        const cartaData = JSON.parse(savedData);
        console.log('Dados recuperados:', cartaData);
        
        // Verifica se precisa fazer login
        const userField = document.querySelector('#input_user');
        if (userField && userField.offsetParent !== null) {
            console.log('Fazendo login no eCarta...');
            showMessage('Fazendo login no eCarta...', '#ffc107');
            
            userField.value = ECARTA_USER;
            const passField = document.querySelector('#input_password');
            const loginBtn = document.querySelector('input.btn');
            
            if (passField && loginBtn) {
                passField.value = ECARTA_PASS;
                loginBtn.click();
                
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
            }
            return;
        }
        
        // Se já logado, busca a tabela
        showMessage('Buscando dados na tabela eCarta...', '#007bff');
        
        setTimeout(() => {
            try {
                const table = document.querySelector("table[id*='tabDoc']");
                if (!table) {
                    showMessage('Tabela do eCarta não encontrada. Aguarde carregar...', '#ffc107');
                    return;
                }
                
                const rows = Array.from(table.querySelectorAll('tr'));
                const tableData = [];
                
                for (const row of rows.slice(1)) { // Pula cabeçalho
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 7) {
                        const idPje = cells[3].textContent.trim();
                        const destinatario = cells[6].textContent.trim();
                        const status = cells[5].textContent.trim();
                        
                        // Busca link de rastreamento
                        let rastreamento = status;
                        const link = cells[5].querySelector('a');
                        if (link) {
                            rastreamento = link.href || link.textContent.trim();
                        }
                        
                        // Verifica se ID está na lista
                        for (const intimationId of cartaData.intimationIds) {
                            if (idPje.includes(intimationId) || intimationId.includes(idPje)) {
                                tableData.push({
                                    ID: intimationId,
                                    DESTINATARIO: destinatario,
                                    RESULTADO: status,
                                    RASTREAMENTO: rastreamento
                                });
                                break;
                            }
                        }
                    }
                }
                
                if (tableData.length > 0) {
                    showMessage(`${tableData.length} registros correlacionados encontrados!`, '#28a745');
                    console.log('Dados correlacionados:', tableData);
                    
                    // Cria tabela HTML
                    let html = `
                        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial; margin: 20px 0;">
                            <thead style="background-color: #f0f0f0;">
                                <tr><th>ID</th><th>DESTINATARIO</th><th>RESULTADO</th><th>RASTREAMENTO</th></tr>
                            </thead>
                            <tbody>
                    `;
                    
                    for (const row of tableData) {
                        html += `<tr><td>${row.ID}</td><td>${row.DESTINATARIO}</td><td>${row.RESULTADO}</td><td>${row.RASTREAMENTO}</td></tr>`;
                    }
                    
                    html += '</tbody></table>';
                    
                    // Mostra resultado
                    const resultDiv = document.createElement('div');
                    resultDiv.style.cssText = `
                        position: fixed; top: 50px; right: 20px; z-index: 9999;
                        background: white; border: 2px solid #007bff; border-radius: 10px;
                        padding: 20px; max-width: 600px; max-height: 400px; overflow: auto;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    `;
                    
                    resultDiv.innerHTML = `
                        <h3 style="margin-top: 0;">Resultado da Análise eCarta</h3>
                        ${html}
                        <button onclick="this.parentElement.remove()" style="margin-top: 10px; padding: 5px 10px; background: #dc3545; color: white; border: none; border-radius: 3px; cursor: pointer;">Fechar</button>
                        <button onclick="navigator.clipboard.writeText('${html.replace(/'/g, "\\'")}').then(() => alert('Tabela copiada!'))" style="margin-top: 10px; margin-left: 10px; padding: 5px 10px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">Copiar HTML</button>
                    `;
                    
                    document.body.appendChild(resultDiv);
                    
                } else {
                    showMessage('Nenhum registro correlacionado encontrado na tabela eCarta', '#ffc107');
                }
                
            } catch (error) {
                console.error('Erro ao processar tabela eCarta:', error);
                showMessage(`Erro: ${error.message}`, '#dc3545');
            }
        }, 2000);
    }
    
    // Executa função principal
    main();
    
})();
