/**
 * CARTA BOOKMARKLET - Análise eCarta via JavaScript
 * Replica funcionalidade do carta.py corrigido
 * 
 * INSTRUÇÕES:
 * 1. Acesse página de processo no PJe  
 * 2. Execute este bookmarklet
 * 3. Aguarde processamento automático
 */

(function() {
    'use strict';
    
    // Configurações
    const ECARTA_USER = 's164283';
    const ECARTA_PASS = '59Justdoit!1';
    const DEBUG = true;
    
    function log(msg) {
        if (DEBUG) console.log(`[CARTA] ${msg}`);
    }
    
    function showMessage(msg, type = 'info') {
        const colors = { error: '#dc3545', success: '#28a745', info: '#007bff', warning: '#ffc107' };
        const div = document.createElement('div');
        div.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 10000;
            background: ${colors[type]}; color: white; padding: 12px 16px;
            border-radius: 6px; font-family: Arial; font-size: 14px;
            max-width: 350px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-left: 4px solid rgba(255,255,255,0.3);
        `;
        div.textContent = msg;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), type === 'error' ? 8000 : 5000);
    }
      // Solicitar data específica do usuário
    function askForDate() {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.8); z-index: 10000;
                display: flex; align-items: center; justify-content: center;
            `;
            
            const content = document.createElement('div');
            content.style.cssText = `
                background: white; padding: 30px; border-radius: 10px;
                text-align: center; font-family: Arial, sans-serif;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            `;
            
            content.innerHTML = `
                <h3 style="margin-top: 0; color: #333;">Qual a data?</h3>
                <p style="margin: 15px 0; color: #666;">Digite apenas 2 dígitos do dia (ex: 15)<br>
                Deixe vazio para usar a data mais recente</p>
                <input type="text" id="dayInput" maxlength="2" 
                       style="padding: 10px; border: 2px solid #ddd; border-radius: 5px; 
                              text-align: center; font-size: 16px; width: 60px; margin: 10px;">
                <br>
                <button id="confirmBtn" style="margin: 15px 5px; padding: 10px 20px; 
                       background: #007cba; color: white; border: none; border-radius: 5px; 
                       cursor: pointer; font-size: 14px;">OK</button>
                <button id="cancelBtn" style="margin: 15px 5px; padding: 10px 20px; 
                       background: #666; color: white; border: none; border-radius: 5px; 
                       cursor: pointer; font-size: 14px;">Cancelar</button>
            `;
            
            const input = content.querySelector('#dayInput');
            const confirmBtn = content.querySelector('#confirmBtn');
            const cancelBtn = content.querySelector('#cancelBtn');
            
            // Foca no input
            setTimeout(() => input.focus(), 100);
            
            // Aceitar apenas números
            input.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
            
            // Enter para confirmar
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') confirmBtn.click();
            });
            
            confirmBtn.onclick = () => {
                const day = input.value.trim();
                modal.remove();
                resolve(day);
            };
            
            cancelBtn.onclick = () => {
                modal.remove();
                resolve(null); // Cancela operação
            };
            
            modal.appendChild(content);
            document.body.appendChild(modal);
        });
    }

    // ETAPA 1: Buscar intimações na timeline (data específica ou mais recente)
    async function getIntimationIds(targetDay = null) {
        log(`Iniciando busca de intimações na timeline${targetDay ? ` para o dia ${targetDay}` : ' (data mais recente)'}...`);
        showMessage(`Buscando intimações na timeline${targetDay ? ` para o dia ${targetDay}` : ''}...`, 'info');
        
        const timeline = document.querySelector('ul.pje-timeline');
        if (!timeline) {
            throw new Error('Timeline não encontrada. Certifique-se de estar na página de detalhes do processo.');
        }
        
        const items = Array.from(timeline.querySelectorAll('li'));
        const intimationIds = [];
        let processNumber = null;
        let dateFound = false;
        let currentDateDiv = null;
        
        for (const item of items) {
            // Detecta mudança de data
            const dateDiv = item.querySelector('div.tl-data');
            if (dateDiv) {
                const dateText = dateDiv.textContent.trim();
                
                if (targetDay) {
                    // Procura data específica (formato: "DD/MM/AAAA" ou similar)
                    const dayMatch = dateText.match(/^(\d{2})/);
                    if (dayMatch && dayMatch[1] === targetDay.padStart(2, '0')) {
                        log(`Data encontrada: ${dateText}`);
                        dateFound = true;
                        currentDateDiv = dateDiv;
                    } else if (dateFound) {
                        // Para quando encontra próxima data após a desejada
                        break;
                    } else {
                        // Continua procurando a data específica
                        continue;
                    }
                } else {
                    // Usa primeira data (mais recente)
                    if (dateFound) break;
                    dateFound = true;
                    currentDateDiv = dateDiv;
                    log(`Usando data mais recente: ${dateText}`);
                }
                continue;
            }
            
            // Só processa itens se uma data foi encontrada
            if (!dateFound) continue;
            
            // Busca intimações
            const link = item.querySelector('a.tl-documento:not([target="_blank"])');
            if (!link) continue;
            
            const aria = link.getAttribute('aria-label') || '';
            const linkText = link.textContent.trim().toLowerCase();
            
            if (linkText.includes('intimação') || aria.toLowerCase().includes('intimação')) {
                // Simula clique para ativar documento (sem abrir nova aba)
                link.click();
                
                // Aguarda um pouco para o documento carregar
                setTimeout(() => {
                    // Procura pelo botão HTML para extrair conteúdo
                    const htmlButton = document.querySelector('.fa-file-code');
                    if (htmlButton) {
                        htmlButton.click();
                        
                        // Aguarda modal aparecer e extrai texto
                        setTimeout(() => {
                            const preview = document.querySelector('#previewModeloDocumento');
                            if (preview) {
                                const texto = preview.textContent || preview.innerText || '';
                                
                                // Verifica se é intimação de correio
                                if (texto.toUpperCase().includes('NAO APAGAR NENHUM CARACTERE')) {
                                    // Extrai ID da intimação
                                    const idMatch = aria.match(/Id: ([a-f0-9]+)/);
                                    const idCurto = idMatch ? idMatch[1] : item.id;
                                    intimationIds.push(idCurto);
                                    
                                    // Extrai número do processo (primeira vez)
                                    if (!processNumber) {
                                        const procMatch = texto.match(/(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})/);
                                        if (procMatch) processNumber = procMatch[1];
                                    }
                                    
                                    log(`ID da intimação encontrado: ${idCurto}`);
                                }
                                
                                // Fecha modal
                                document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
                            }
                        }, 1000);
                    }
                }, 500);
            }
        }
        
        return { intimationIds, processNumber };
    }
    
    // ETAPA 2: Abrir eCarta com login
    function openECarta(processNumber) {
        if (!processNumber) {
            throw new Error('Número do processo não encontrado');
        }
        
        log(`Abrindo eCarta para processo: ${processNumber}`);
        const eCartaUrl = `https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo=${processNumber}`;
        
        // Abre em nova aba
        const newWindow = window.open(eCartaUrl, '_blank');
        
        // Aguarda carregar e faz login se necessário
        newWindow.onload = function() {
            setTimeout(() => {
                const userField = newWindow.document.querySelector('#input_user');
                if (userField) {
                    log('Fazendo login no eCarta...');
                    userField.value = ECARTA_USER;
                    newWindow.document.querySelector('#input_password').value = ECARTA_PASS;
                    newWindow.document.querySelector('input.btn').click();
                    
                    // Após login, recarrega a página do processo
                    setTimeout(() => {
                        newWindow.location.href = eCartaUrl;
                    }, 3000);
                } else {
                    log('Já logado no eCarta');
                }
            }, 2000);
        };
        
        return newWindow;
    }
    
    // ETAPA 3: Buscar IDs e fazer tabela
    function extractTableData(eCartaWindow, intimationIds) {
        return new Promise((resolve) => {
            setTimeout(() => {
                try {
                    const table = eCartaWindow.document.querySelector("table[id*='tabDoc']");
                    if (!table) {
                        throw new Error('Tabela do eCarta não encontrada');
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
                            for (const intimationId of intimationIds) {
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
                    
                    resolve(tableData);
                } catch (error) {
                    resolve([]);
                }
            }, 5000); // Aguarda 5s para tabela carregar
        });
    }
    
    // Gerar tabela HTML
    function generateHtmlTable(data) {
        if (!data.length) return '<p>Nenhum dado encontrado</p>';
        
        let html = `
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; margin: 20px 0;">
                <thead style="background-color: #f0f0f0;">
                    <tr>
                        <th>ID</th>
                        <th>DESTINATARIO</th>
                        <th>RESULTADO</th>
                        <th>RASTREAMENTO</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        for (const row of data) {
            html += `
                <tr>
                    <td>${row.ID}</td>
                    <td>${row.DESTINATARIO}</td>
                    <td>${row.RESULTADO}</td>
                    <td>${row.RASTREAMENTO}</td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
        return html;
    }
    
    // Mostrar resultado em modal
    function showResult(htmlTable) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); z-index: 10000;
            display: flex; align-items: center; justify-content: center;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: white; padding: 20px; border-radius: 10px;
            max-width: 90%; max-height: 90%; overflow: auto;
            position: relative;
        `;
        
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.style.cssText = `
            position: absolute; top: 10px; right: 15px;
            background: none; border: none; font-size: 24px;
            cursor: pointer; color: #666;
        `;
        closeBtn.onclick = () => modal.remove();
        
        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Copiar Tabela';
        copyBtn.style.cssText = `
            margin-bottom: 15px; padding: 8px 15px;
            background: #007cba; color: white; border: none;
            border-radius: 4px; cursor: pointer;
        `;
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(htmlTable).then(() => {
                showMessage('Tabela copiada para área de transferência!', 'success');
            });
        };
        
        content.appendChild(closeBtn);
        content.appendChild(copyBtn);
        content.innerHTML += '<h3>Resultado da Análise eCarta:</h3>' + htmlTable;
        modal.appendChild(content);
        document.body.appendChild(modal);
    }
      // FUNÇÃO PRINCIPAL
    async function main() {
        try {
            // Primeiro, pergunta ao usuário qual data analisar
            const targetDay = await askForDate();
            if (targetDay === null) {
                showMessage('Operação cancelada pelo usuário', 'warning');
                return;
            }
            
            showMessage('Iniciando análise eCarta...', 'info');
            
            // Etapa 1: Buscar intimações (com data específica ou mais recente)
            const { intimationIds, processNumber } = await getIntimationIds(targetDay);
            
            // Aguarda um pouco para garantir que todas as intimações foram processadas
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            if (!intimationIds.length) {
                throw new Error('Nenhuma intimação de correio encontrada na timeline');
            }
            
            log(`${intimationIds.length} intimações encontradas: ${intimationIds.join(', ')}`);
            
            // Etapa 2: Abrir eCarta
            const eCartaWindow = openECarta(processNumber);
            
            // Etapa 3: Aguardar e extrair dados
            const tableData = await extractTableData(eCartaWindow, intimationIds);
            
            if (!tableData.length) {
                throw new Error('Nenhum dado correlacionado encontrado na tabela eCarta');
            }
            
            // Mostrar resultado
            const htmlTable = generateHtmlTable(tableData);
            showResult(htmlTable);
            
            showMessage(`Análise concluída! ${tableData.length} registros encontrados.`, 'success');
            
        } catch (error) {
            log(`Erro: ${error.message}`);
            showMessage(`Erro: ${error.message}`, 'error');
        }
    }
    
    // Executar
    main();
    
})();
