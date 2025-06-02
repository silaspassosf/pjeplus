// BOOKMARKLET CARTA - VERSÃO CORRIGIDA PARA PROBLEMAS DE CORS
// Esta versão resolve o problema de cross-origin entre PJe e eCarta

(function() {
    'use strict';
    
    // Configurações
    const CONFIG = {
        ECARTA_USER: 's164283',
        ECARTA_PASS: '59Justdoit!1',
        STORAGE_KEY: 'cartaBookmarkletData',
        TIMEOUT: 10000
    };
    
    // Função para mostrar mensagens
    function showMessage(text, color = '#007bff', duration = 4000) {
        const div = document.createElement('div');
        div.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            background: ${color}; color: white; padding: 10px 15px;
            border-radius: 5px; font-family: Arial; font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); max-width: 400px;
        `;
        div.textContent = text;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), duration);
    }
    
    // Função para detectar o site atual
    function detectSite() {
        const url = window.location.href;
        console.log('🔍 URL atual:', url);
        
        const isPje = url.includes('pje.') || url.includes('trt') && url.includes('jus.br');
        const isEcarta = url.includes('eCarta-web') || url.includes('aplicacoes1.trt2.jus.br');
        
        console.log('📍 Detecção de site:', { isPje, isEcarta });
        return { isPje, isEcarta };
    }
    
    // Função para pedir o dia
    function askDay() {
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
                <h3 style="margin-top: 0; color: #333;">📅 Qual dia analisar?</h3>
                <p style="color: #666; margin: 15px 0;">
                    Digite 2 dígitos do dia (ex: 15)<br>
                    Deixe vazio para usar data mais recente
                </p>
                <input type="text" id="dayInput" maxlength="2" 
                       style="padding: 8px; border: 2px solid #ddd; border-radius: 4px;
                              text-align: center; width: 60px; font-size: 16px; margin: 10px;">
                <br>
                <button id="okBtn" style="margin: 10px 5px; padding: 8px 15px; 
                                         background: #007cba; color: white; border: none;
                                         border-radius: 4px; cursor: pointer; font-size: 14px;">OK</button>
                <button id="cancelBtn" style="margin: 10px 5px; padding: 8px 15px;
                                             background: #666; color: white; border: none;
                                             border-radius: 4px; cursor: pointer; font-size: 14px;">Cancelar</button>
            `;
            
            const input = content.querySelector('#dayInput');
            const okBtn = content.querySelector('#okBtn');
            const cancelBtn = content.querySelector('#cancelBtn');
            
            // Só permite números
            input.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
            
            // Enter confirma
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') okBtn.click();
            });
            
            okBtn.onclick = () => {
                const value = input.value.trim();
                modal.remove();
                resolve(value);
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
    
    // Função para buscar intimações no PJe
    async function getIntimationsFromPje(targetDay) {
        showMessage('🔍 Buscando intimações na timeline...');
        
        const timeline = document.querySelector('ul.pje-timeline');
        if (!timeline) {
            throw new Error('Timeline não encontrada. Abra a página de detalhes do processo.');
        }
        
        const items = Array.from(timeline.querySelectorAll('li'));
        const intimationIds = [];
        let processNumber = null;
        let foundTargetDate = false;
        
        console.log('📋 Analisando', items.length, 'itens da timeline');
        
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            
            // Verifica se é um marcador de data
            const dateDiv = item.querySelector('div.tl-data');
            if (dateDiv) {
                const dateText = dateDiv.textContent.trim();
                console.log('📅 Data encontrada:', dateText);
                
                if (targetDay) {
                    // Procura dia específico
                    const dayMatch = dateText.match(/^(\d{2})/);
                    if (dayMatch && dayMatch[1] === targetDay.padStart(2, '0')) {
                        foundTargetDate = true;
                        console.log('✅ Data alvo encontrada:', dateText);
                    } else if (foundTargetDate) {
                        console.log('🛑 Saindo da data alvo');
                        break;
                    } else {
                        continue;
                    }
                } else {
                    // Primeira data encontrada
                    if (foundTargetDate) {
                        break;
                    }
                    foundTargetDate = true;
                    console.log('✅ Usando data mais recente:', dateText);
                }
                continue;
            }
            
            // Se ainda não encontrou a data alvo, continua
            if (!foundTargetDate) continue;
            
            // Procura por links de intimação
            const link = item.querySelector('a.tl-documento:not([target="_blank"])');
            if (!link) continue;
            
            const ariaLabel = link.getAttribute('aria-label') || '';
            const linkText = link.textContent.trim().toLowerCase();
            
            if (linkText.includes('intimação') || ariaLabel.toLowerCase().includes('intimação')) {
                console.log('📬 Intimação encontrada:', linkText);
                
                // Clica na intimação para abrir
                link.click();
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Verifica se tem o botão de visualizar HTML
                const htmlButton = document.querySelector('.fa-file-code');
                if (htmlButton) {
                    htmlButton.click();
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Busca o preview do documento
                    const preview = document.querySelector('#previewModeloDocumento');
                    if (preview) {
                        const text = preview.textContent || preview.innerText || '';
                        
                        // Verifica se é intimação de correio
                        if (text.toUpperCase().includes('NAO APAGAR NENHUM CARACTERE')) {
                            const idMatch = ariaLabel.match(/Id: ([a-f0-9]+)/);
                            const id = idMatch ? idMatch[1] : item.id;
                            intimationIds.push(id);
                            
                            // Extrai número do processo (primeira vez)
                            if (!processNumber) {
                                const procMatch = text.match(/(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})/);
                                if (procMatch) {
                                    processNumber = procMatch[1];
                                }
                            }
                            
                            console.log('✅ ID correio encontrado:', id);
                        }
                        
                        // Fecha o preview
                        document.body.dispatchEvent(new KeyboardEvent('keydown', {
                            key: 'Escape'
                        }));
                    }
                }
            }
        }
        
        return { intimationIds, processNumber };
    }
    
    // Função para salvar dados e abrir eCarta
    function saveDataAndOpenEcarta(intimationIds, processNumber) {
        const data = {
            intimationIds,
            processNumber,
            timestamp: Date.now()
        };
        
        localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(data));
        console.log('💾 Dados salvos:', data);
        
        const eCartaUrl = `https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo=${processNumber}`;
        window.open(eCartaUrl, '_blank');
        
        showMessage('💾 Dados salvos! Aguarde a aba do eCarta abrir e execute o bookmarklet lá.', '#28a745', 6000);
    }
    
    // Função para executar no eCarta
    async function executeEcartaPart() {
        console.log('🎯 Executando parte eCarta...');
        
        // Recupera dados salvos
        const savedData = localStorage.getItem(CONFIG.STORAGE_KEY);
        if (!savedData) {
            showMessage('❌ Dados não encontrados! Execute primeiro no PJe.', '#dc3545');
            return;
        }
        
        const cartaData = JSON.parse(savedData);
        console.log('📥 Dados recuperados:', cartaData);
        
        // Verifica se precisa fazer login
        const userField = document.querySelector('#input_user');
        if (userField && userField.offsetParent !== null) {
            console.log('🔐 Fazendo login no eCarta...');
            showMessage('🔐 Fazendo login no eCarta...', '#ffc107');
            
            userField.value = CONFIG.ECARTA_USER;
            const passField = document.querySelector('#input_password');
            const loginBtn = document.querySelector('input.btn');
            
            if (passField && loginBtn) {
                passField.value = CONFIG.ECARTA_PASS;
                
                // Dispara eventos para garantir que os campos sejam reconhecidos
                [userField, passField].forEach(field => {
                    field.dispatchEvent(new Event('input', { bubbles: true }));
                    field.dispatchEvent(new Event('change', { bubbles: true }));
                });
                
                loginBtn.click();
                
                showMessage('⏳ Login enviado. Aguarde e execute o bookmarklet novamente após o carregamento.', '#007bff', 8000);
                return;
            }
        }
        
        // Se já logado, busca dados na tabela
        showMessage('🔍 Buscando dados na tabela eCarta...', '#007bff');
        
        setTimeout(() => {
            try {
                const table = document.querySelector("table[id*='tabDoc']");
                if (!table) {
                    showMessage('⚠️ Tabela não encontrada. Aguarde a página carregar e tente novamente.', '#ffc107');
                    return;
                }
                
                const rows = Array.from(table.querySelectorAll('tr'));
                const tableData = [];
                
                console.log('📊 Processando', rows.length - 1, 'linhas da tabela');
                
                for (let i = 1; i < rows.length; i++) { // Pula cabeçalho
                    const cells = rows[i].querySelectorAll('td');
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
                        
                        // Verifica se ID está na nossa lista
                        for (const intimationId of cartaData.intimationIds) {
                            if (idPje.includes(intimationId) || intimationId.includes(idPje)) {
                                tableData.push({
                                    ID: intimationId,
                                    DESTINATARIO: destinatario,
                                    RESULTADO: status,
                                    RASTREAMENTO: rastreamento
                                });
                                console.log('✅ Correlação encontrada:', intimationId, '->', destinatario);
                                break;
                            }
                        }
                    }
                }
                
                if (tableData.length > 0) {
                    showMessage(`✅ ${tableData.length} registros correlacionados encontrados!`, '#28a745');
                    console.log('📋 Dados correlacionados:', tableData);
                    
                    // Cria tabela HTML para exibição
                    let html = `
                        <table border="1" cellpadding="5" cellspacing="0" 
                               style="border-collapse: collapse; font-family: Arial; margin: 20px 0; width: 100%;">
                            <thead style="background-color: #f0f0f0;">
                                <tr>
                                    <th>ID</th>
                                    <th>DESTINATÁRIO</th>
                                    <th>RESULTADO</th>
                                    <th>RASTREAMENTO</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    
                    for (const row of tableData) {
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
                    
                    // Mostra resultado em modal
                    const resultDiv = document.createElement('div');
                    resultDiv.style.cssText = `
                        position: fixed; top: 50px; right: 20px; z-index: 9999;
                        background: white; border: 2px solid #007bff; border-radius: 10px;
                        padding: 20px; max-width: 700px; max-height: 500px; overflow: auto;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    `;
                    
                    resultDiv.innerHTML = `
                        <h3 style="margin-top: 0; color: #007bff;">📊 Resultado da Análise eCarta</h3>
                        <p><strong>Processo:</strong> ${cartaData.processNumber}</p>
                        <p><strong>Intimações encontradas:</strong> ${tableData.length} de ${cartaData.intimationIds.length} buscadas</p>
                        ${html}
                        <div style="margin-top: 15px; text-align: right;">
                            <button onclick="navigator.clipboard.writeText(\`${html.replace(/`/g, '\\`')}\`).then(() => alert('Tabela HTML copiada para a área de transferência!'))" 
                                    style="margin-right: 10px; padding: 8px 15px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                📋 Copiar HTML
                            </button>
                            <button onclick="this.parentElement.parentElement.remove()" 
                                    style="padding: 8px 15px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                ❌ Fechar
                            </button>
                        </div>
                    `;
                    
                    document.body.appendChild(resultDiv);
                    
                    // Limpa os dados salvos após o uso
                    localStorage.removeItem(CONFIG.STORAGE_KEY);
                    
                } else {
                    showMessage('⚠️ Nenhum registro correlacionado encontrado na tabela eCarta', '#ffc107');
                }
                
            } catch (error) {
                console.error('❌ Erro ao processar tabela eCarta:', error);
                showMessage(`❌ Erro: ${error.message}`, '#dc3545');
            }
        }, 2000);
    }
    
    // Função principal
    async function main() {
        try {
            const { isPje, isEcarta } = detectSite();
            
            if (!isPje && !isEcarta) {
                showMessage('⚠️ Site não reconhecido! Este bookmarklet deve ser executado no PJe ou eCarta dos Correios.', '#dc3545', 8000);
                console.log('❌ URL não reconhecida:', window.location.href);
                return;
            }
            
            if (isPje) {
                showMessage('🎯 Sistema PJe detectado - Iniciando coleta de dados...');
                
                const targetDay = await askDay();
                if (targetDay === null) {
                    showMessage('❌ Operação cancelada', '#ffc107');
                    return;
                }
                
                const { intimationIds, processNumber } = await getIntimationsFromPje(targetDay);
                
                if (!intimationIds.length) {
                    throw new Error('Nenhuma intimação de correio encontrada');
                }
                
                showMessage(`✅ ${intimationIds.length} intimações encontradas!`, '#28a745');
                console.log('📋 IDs encontrados:', intimationIds);
                console.log('📋 Número do processo:', processNumber);
                
                saveDataAndOpenEcarta(intimationIds, processNumber);
                
            } else if (isEcarta) {
                showMessage('🎯 Sistema eCarta detectado - Processando dados salvos...');
                await executeEcartaPart();
            }
            
        } catch (error) {
            console.error('❌ Erro:', error);
            showMessage(`❌ Erro: ${error.message}`, '#dc3545');
        }
    }
    
    // Executa função principal
    main();
    
})();
