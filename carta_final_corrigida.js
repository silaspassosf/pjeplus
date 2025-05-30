/**
 * BOOKMARKLET CARTA - VERSÃO FINAL CORRIGIDA V2
 * 
 * Este bookmarklet funciona automaticamente em 2 partes:
 * 1) No PJe: coleta intimações e abre eCarta
 * 2) No eCarta: faz login automático e consulta os dados
 * 
 * NOVA VERSÃO COM LOGIN MELHORADO E DETECÇÃO ROBUSTA
 */

(function() {
    'use strict';
    
    // Configurações
    const CONFIG = {
        ECARTA_USER: 's164283',
        ECARTA_PASS: '59Justdoit!1',
        STORAGE_KEY: 'carta_bookmarklet_dados_v3',
        MAX_RETRY_LOGIN: 3,
        DELAY_BETWEEN_QUERIES: 2500,
        TIMEOUT_LOGIN: 8000
    };
    
    // Detecta site atual com mais precisão
    const currentHost = window.location.hostname.toLowerCase();
    const currentUrl = window.location.href.toLowerCase();
    const isPje = currentHost.includes('pje') || currentHost.includes('trt') || currentUrl.includes('pje');
    const isEcarta = currentHost.includes('correios') || currentUrl.includes('ecarta') || currentUrl.includes('2.correios');
    
    console.log('🔍 Detecção de site:', {
        host: currentHost,
        url: currentUrl,
        isPje: isPje,
        isEcarta: isEcarta
    });
    
    // Função universal para mostrar mensagens
    function showMessage(text, type = 'info', duration = 5000) {
        const colors = {
            info: '#17a2b8',
            success: '#28a745', 
            warning: '#ffc107',
            error: '#dc3545'
        };
        
        const icons = {
            info: '🔍',
            success: '✅',
            warning: '⚠️', 
            error: '❌'
        };
        
        const div = document.createElement('div');
        div.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 999999;
            background: ${colors[type]}; color: white; padding: 15px 20px;
            border-radius: 8px; font-family: Arial, sans-serif; font-size: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4); font-weight: 500;
            max-width: 400px; word-wrap: break-word; line-height: 1.4;
            border: 2px solid rgba(255,255,255,0.3);
        `;
        
        div.innerHTML = `${icons[type]} ${text}`;
        document.body.appendChild(div);
        
        // Remove automaticamente
        setTimeout(() => {
            if (div.parentNode) div.remove();
        }, duration);
        
        console.log(`📢 ${type.toUpperCase()}: ${text}`);
    }
    
    // Função para criar modal de seleção de data
    function askForDate() {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.85); z-index: 1000000;
                display: flex; align-items: center; justify-content: center;
                font-family: Arial, sans-serif;
            `;
            
            const content = document.createElement('div');
            content.style.cssText = `
                background: white; padding: 35px; border-radius: 15px;
                text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                border: 2px solid #007bff; min-width: 350px;
            `;
            
            content.innerHTML = `
                <h3 style="margin: 0 0 25px 0; color: #333; font-size: 20px;">
                    📅 Seleção de Data para Análise
                </h3>
                <p style="color: #666; margin: 0 0 25px 0; line-height: 1.6;">
                    Digite apenas os <strong>2 dígitos do dia</strong> (exemplo: <code>15</code>)<br>
                    <small style="color: #999;">Deixe vazio para analisar a data mais recente da timeline</small>
                </p>
                <input type="text" id="dayInput" maxlength="2" placeholder="DD"
                       style="padding: 15px; border: 3px solid #ddd; border-radius: 8px; 
                              text-align: center; width: 100px; font-size: 20px; 
                              font-weight: bold; margin-bottom: 25px;">
                <br>
                <button id="okBtn" style="margin: 0 10px; padding: 15px 30px;
                                          background: #28a745; color: white; border: none;
                                          border-radius: 8px; cursor: pointer; font-size: 16px;
                                          font-weight: bold;">
                    ✅ Buscar Intimações
                </button>
                <button id="cancelBtn" style="margin: 0 10px; padding: 15px 30px;
                                              background: #dc3545; color: white; border: none;
                                              border-radius: 8px; cursor: pointer; font-size: 16px;
                                              font-weight: bold;">
                    ❌ Cancelar
                </button>
            `;
            
            modal.appendChild(content);
            document.body.appendChild(modal);
            
            const input = content.querySelector('#dayInput');
            const okBtn = content.querySelector('#okBtn');
            const cancelBtn = content.querySelector('#cancelBtn');
            
            // Foca no input
            setTimeout(() => input.focus(), 100);
            
            // Eventos
            input.addEventListener('input', (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            });
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') okBtn.click();
                if (e.key === 'Escape') cancelBtn.click();
            });
            
            okBtn.addEventListener('click', () => {
                const day = input.value.trim();
                modal.remove();
                resolve(day);
            });
            
            cancelBtn.addEventListener('click', () => {
                modal.remove();
                resolve(null);
            });
        });
    }
    
    // ==========================================
    // PARTE 1: EXECUÇÃO NO PJE
    // ==========================================
    async function executePjeScript() {
        showMessage('Iniciando busca por intimações no sistema PJe...', 'info');
        
        try {
            const selectedDay = await askForDate();
            if (selectedDay === null) {
                showMessage('Operação cancelada pelo usuário', 'warning');
                return;
            }
            
            // Busca elementos da timeline com múltiplos seletores
            let timelineItems = document.querySelectorAll('td.rich-table-cell[id*="timeline"]');
            
            if (timelineItems.length === 0) {
                // Tenta outros seletores para timeline
                timelineItems = document.querySelectorAll('.timeline-item, .entry, .movimento');
            }
            
            if (timelineItems.length === 0) {
                throw new Error('Timeline não encontrada. Verifique se está na página correta do processo.');
            }
            
            const intimacoes = [];
            let processNumber = null;
            
            // Busca número do processo em vários lugares
            const procSelectors = [
                '[title*="-"]', '.processo', '#processoTitulo', 
                '.numero-processo', '[data-processo]'
            ];
            
            for (const selector of procSelectors) {
                const elem = document.querySelector(selector);
                if (elem) {
                    const match = elem.textContent.match(/(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})/);
                    if (match) {
                        processNumber = match[1];
                        break;
                    }
                }
            }
            
            showMessage(`Analisando ${timelineItems.length} itens da timeline...`, 'info');
            
            for (const item of timelineItems) {
                const text = item.textContent || item.innerText || '';
                
                // Verifica se contém data (se dia especificado)
                if (selectedDay) {
                    const dayPattern = new RegExp(`\\b${selectedDay.padStart(2, '0')}/\\d{2}/\\d{4}\\b`);
                    if (!dayPattern.test(text)) continue;
                }
                
                // Procura por IDs de intimação (vários padrões)
                const idMatches = text.match(/(\d{13})/g) || text.match(/(\d{12})/g) || text.match(/(\d{10,15})/g);
                if (!idMatches) continue;
                
                // Verifica se é intimação por correio com termos mais abrangentes
                const textLower = text.toLowerCase();
                const hasCorreio = /correio|postal|sedex|carta|correspondência|endereço|cep|nao apagar|não apagar|via postal/i.test(text);
                
                if (hasCorreio) {
                    for (const intimacaoId of idMatches) {
                        // Extrai informações adicionais
                        const dateMatch = text.match(/(\d{2}\/\d{2}\/\d{4})/);
                        const date = dateMatch ? dateMatch[1] : 'N/A';
                        
                        intimacoes.push({
                            id: intimacaoId,
                            text: text.trim().substring(0, 300) + '...',
                            date: date,
                            processNumber: processNumber,
                            found: new Date().toISOString()
                        });
                    }
                }
            }
            
            if (intimacoes.length === 0) {
                const dayText = selectedDay ? `para o dia ${selectedDay}` : '';
                throw new Error(`Nenhuma intimação por correio encontrada ${dayText}. Verifique se há intimações com termos como "correio", "postal" ou "endereço".`);
            }
            
            // Remove duplicatas
            const uniqueIntimacoes = intimacoes.filter((item, index, self) => 
                index === self.findIndex(t => t.id === item.id)
            );
            
            // Salva no localStorage
            const data = {
                intimacoes: uniqueIntimacoes,
                selectedDay,
                processNumber,
                timestamp: new Date().toISOString(),
                source: window.location.href,
                version: 'v3'
            };
            
            localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(data));
            
            showMessage(`${uniqueIntimacoes.length} intimações por correio encontradas! Abrindo eCarta...`, 'success', 4000);
            
            // Abre eCarta em nova aba
            setTimeout(() => {
                const eCartaUrl = 'https://www2.correios.com.br/sistemas/ecommerce/';
                const newWindow = window.open(eCartaUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
                
                if (newWindow) {
                    showMessage('eCarta aberto em nova aba! Execute o bookmarklet novamente na aba do eCarta para processar os dados.', 'info', 10000);
                } else {
                    showMessage('Pop-up bloqueado! Permita pop-ups para este site e tente novamente.', 'warning', 8000);
                }
            }, 2000);
            
        } catch (error) {
            console.error('Erro no PJe:', error);
            showMessage(`Erro: ${error.message}`, 'error', 8000);
        }
    }
    
    // ==========================================
    // PARTE 2: EXECUÇÃO NO ECARTA
    // ==========================================
    async function executeEcartaScript() {
        showMessage('Iniciando processamento no sistema eCarta...', 'info');
        
        try {
            // Verifica dados salvos
            const savedData = localStorage.getItem(CONFIG.STORAGE_KEY);
            if (!savedData) {
                throw new Error('Nenhum dado encontrado no localStorage. Execute primeiro o bookmarklet no PJe.');
            }
            
            const data = JSON.parse(savedData);
            const { intimacoes, processNumber } = data;
            
            if (!intimacoes || intimacoes.length === 0) {
                throw new Error('Nenhuma intimação encontrada nos dados salvos.');
            }
            
            showMessage(`${intimacoes.length} intimações carregadas para processamento`, 'success');
            
            // Aguarda página carregar completamente
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // Tenta fazer login com retry
            let loginSuccess = false;
            for (let attempt = 1; attempt <= CONFIG.MAX_RETRY_LOGIN; attempt++) {
                showMessage(`Tentativa de login ${attempt}/${CONFIG.MAX_RETRY_LOGIN}...`, 'info');
                loginSuccess = await performLogin();
                
                if (loginSuccess) break;
                
                if (attempt < CONFIG.MAX_RETRY_LOGIN) {
                    showMessage(`Falha no login. Tentando novamente em 5 segundos...`, 'warning');
                    await new Promise(resolve => setTimeout(resolve, 5000));
                }
            }
            
            if (!loginSuccess) {
                throw new Error('Falha no login após todas as tentativas. Verifique as credenciais ou faça login manualmente.');
            }
            
            // Aguarda após login bem-sucedido
            await new Promise(resolve => setTimeout(resolve, 5000));
            
            // Processa intimações
            await processIntimacoes(intimacoes);
            
        } catch (error) {
            console.error('Erro no eCarta:', error);
            showMessage(`Erro: ${error.message}`, 'error', 10000);
        }
    }
    
    // Função de login muito mais robusta
    async function performLogin() {
        showMessage('Analisando página para realizar login...', 'info');
        
        return new Promise((resolve) => {
            try {
                // Verifica se já está logado (múltiplas verificações)
                const loggedInIndicators = [
                    'a[href*="logout"]', 'a[href*="sair"]', '.logout', '.sair',
                    '.user-info', '.usuario-logado', '.menu-usuario',
                    'form[action*="logout"]', '[title*="sair"]'
                ];
                
                for (const indicator of loggedInIndicators) {
                    if (document.querySelector(indicator)) {
                        showMessage('Usuário já está logado no sistema!', 'success');
                        resolve(true);
                        return;
                    }
                }
                
                // Procura campos de login com seletores muito amplos
                const userSelectors = [
                    'input[name*="usuario"]', 'input[name*="user"]', 'input[name*="login"]',
                    'input[id*="user"]', 'input[id*="usuario"]', 'input[id*="login"]',
                    'input[type="text"]:not([readonly]):not([disabled])',
                    'input[placeholder*="usuário"]', 'input[placeholder*="user"]',
                    '.user-input', '.usuario-input', '#input_user', '#user',
                    'input.form-control[type="text"]'
                ];
                
                const passSelectors = [
                    'input[name*="senha"]', 'input[name*="pass"]', 'input[name*="password"]',
                    'input[id*="pass"]', 'input[id*="senha"]', 'input[id*="password"]',
                    'input[type="password"]', 'input[placeholder*="senha"]',
                    '.password-input', '.senha-input', '#input_password', '#password',
                    'input.form-control[type="password"]'
                ];
                
                const submitSelectors = [
                    'input[type="submit"]', 'button[type="submit"]',
                    'input[value*="Entrar"]', 'input[value*="Login"]', 'input[value*="Acessar"]',
                    'button[value*="Entrar"]', 'button[value*="Login"]', 'button[value*="Acessar"]',
                    'button:contains("Entrar")', 'button:contains("Login")', 'button:contains("Acessar")',
                    '.btn-login', '.login-btn', '#login-btn', '#entrar', '.entrar'
                ];
                
                let userField = null;
                let passField = null;
                let submitBtn = null;
                
                // Busca campos de usuário
                for (const selector of userSelectors) {
                    const field = document.querySelector(selector);
                    if (field && field.offsetParent !== null && !field.disabled && !field.readOnly) {
                        userField = field;
                        console.log('Campo usuário encontrado:', selector);
                        break;
                    }
                }
                
                // Busca campos de senha
                for (const selector of passSelectors) {
                    const field = document.querySelector(selector);
                    if (field && field.offsetParent !== null && !field.disabled && !field.readOnly) {
                        passField = field;
                        console.log('Campo senha encontrado:', selector);
                        break;
                    }
                }
                
                // Busca botão de submit
                for (const selector of submitSelectors) {
                    const btn = document.querySelector(selector);
                    if (btn && btn.offsetParent !== null && !btn.disabled) {
                        submitBtn = btn;
                        console.log('Botão submit encontrado:', selector);
                        break;
                    }
                }
                
                // Se não encontrou botão específico, busca de forma mais ampla
                if (!submitBtn) {
                    const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
                    for (const btn of buttons) {
                        const text = (btn.textContent || btn.value || '').toLowerCase();
                        if (text.includes('entrar') || text.includes('login') || text.includes('acessar')) {
                            submitBtn = btn;
                            console.log('Botão genérico encontrado:', text);
                            break;
                        }
                    }
                }
                
                if (userField && passField) {
                    showMessage('Campos de login encontrados! Preenchendo credenciais...', 'info');
                    
                    // Limpa campos primeiro
                    userField.value = '';
                    passField.value = '';
                    
                    // Aguarda um pouco antes de preencher
                    setTimeout(() => {
                        // Preenche campos
                        userField.value = CONFIG.ECARTA_USER;
                        passField.value = CONFIG.ECARTA_PASS;
                        
                        // Dispara múltiplos eventos para garantir reconhecimento
                        [userField, passField].forEach(field => {
                            field.dispatchEvent(new Event('input', {bubbles: true}));
                            field.dispatchEvent(new Event('change', {bubbles: true}));
                            field.dispatchEvent(new Event('blur', {bubbles: true}));
                            field.dispatchEvent(new Event('keyup', {bubbles: true}));
                        });
                        
                        showMessage('Credenciais preenchidas! Enviando formulário...', 'success');
                        
                        setTimeout(() => {
                            let submitted = false;
                            
                            if (submitBtn) {
                                submitBtn.click();
                                submitted = true;
                                showMessage('Login enviado via botão. Aguardando resposta...', 'info');
                            } else {
                                // Tenta submeter via formulário
                                const form = userField.closest('form') || passField.closest('form');
                                if (form) {
                                    form.submit();
                                    submitted = true;
                                    showMessage('Login enviado via formulário. Aguardando resposta...', 'info');
                                } else {
                                    // Tenta pressionar Enter
                                    passField.dispatchEvent(new KeyboardEvent('keydown', {
                                        key: 'Enter',
                                        keyCode: 13,
                                        which: 13,
                                        bubbles: true
                                    }));
                                    submitted = true;
                                    showMessage('Login enviado via Enter. Aguardando resposta...', 'info');
                                }
                            }
                            
                            if (submitted) {
                                // Aguarda resposta do login
                                setTimeout(() => {
                                    // Verifica se o login foi bem-sucedido
                                    const stillHasPasswordField = document.querySelector('input[type="password"]');
                                    if (!stillHasPasswordField) {
                                        showMessage('Login realizado com sucesso!', 'success');
                                        resolve(true);
                                    } else {
                                        showMessage('Login falhou - campos ainda visíveis', 'warning');
                                        resolve(false);
                                    }
                                }, CONFIG.TIMEOUT_LOGIN);
                            } else {
                                showMessage('Não foi possível enviar o formulário de login', 'error');
                                resolve(false);
                            }
                        }, 1500);
                    }, 1000);
                    
                } else {
                    const missingFields = [];
                    if (!userField) missingFields.push('usuário');
                    if (!passField) missingFields.push('senha');
                    
                    showMessage(`Campos não encontrados: ${missingFields.join(', ')}. Verifique se a página carregou completamente.`, 'warning');
                    
                    // Verifica se pode estar já logado de outra forma
                    const hasPasswordField = document.querySelector('input[type="password"]');
                    if (!hasPasswordField) {
                        showMessage('Nenhum campo de senha encontrado - pode já estar logado', 'info');
                        resolve(true);
                    } else {
                        resolve(false);
                    }
                }
                
            } catch (error) {
                console.error('Erro durante login:', error);
                showMessage(`Erro durante login: ${error.message}`, 'error');
                resolve(false);
            }
        });
    }
    
    // Processa as intimações uma por uma
    async function processIntimacoes(intimacoes) {
        showMessage('Iniciando consulta individual das intimações...', 'info');
        
        const results = [];
        const total = intimacoes.length;
        
        for (let i = 0; i < total; i++) {
            const intimacao = intimacoes[i];
            const progress = `${i + 1}/${total}`;
            
            showMessage(`Consultando ${progress}: ID ${intimacao.id}`, 'info');
            
            try {
                const result = await queryIntimacao(intimacao.id);
                results.push({
                    ...intimacao,
                    status: result.found ? 'ENCONTRADO' : 'NÃO ENCONTRADO',
                    details: result.details || 'N/A',
                    rastreamento: result.tracking || 'N/A',
                    preview: result.preview || 'N/A'
                });
                
            } catch (error) {
                results.push({
                    ...intimacao,
                    status: 'ERRO',
                    details: error.message,
                    rastreamento: 'N/A',
                    preview: 'N/A'
                });
            }
            
            // Pausa entre consultas
            if (i < total - 1) {
                await new Promise(resolve => setTimeout(resolve, CONFIG.DELAY_BETWEEN_QUERIES));
            }
        }
        
        displayResults(results);
    }
    
    // Consulta individual de intimação via iframe
    async function queryIntimacao(id) {
        return new Promise((resolve) => {
            const iframe = document.createElement('iframe');
            iframe.style.cssText = 'position: absolute; left: -9999px; width: 1px; height: 1px;';
            
            let resolved = false;
            
            // URLs para tentar
            const urls = [
                `https://www2.correios.com.br/sistemas/rastreamento/resultado.cfm?objetos=${id}`,
                `https://www2.correios.com.br/sistemas/rastreamento/ctrl/ctrlRastreamento.cfm?acao=track&objetos=${id}`,
                `https://rastreamento.correios.com.br/app/resultado.php?objeto=${id}`
            ];
            
            let urlIndex = 0;
            
            function tryNextUrl() {
                if (urlIndex >= urls.length || resolved) {
                    if (!resolved) {
                        resolved = true;
                        resolve({
                            found: false,
                            details: 'Todas as URLs de rastreamento falharam',
                            tracking: 'N/A',
                            preview: 'N/A'
                        });
                        iframe.remove();
                    }
                    return;
                }
                
                iframe.src = urls[urlIndex];
                urlIndex++;
            }
            
            iframe.onload = () => {
                if (resolved) return;
                
                try {
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!doc || !doc.body) {
                        tryNextUrl();
                        return;
                    }
                    
                    const text = doc.body.textContent || doc.body.innerText || '';
                    const textLower = text.toLowerCase();
                    
                    const found = textLower.includes('objeto entregue') || 
                                 textLower.includes('entregue ao destinatário') ||
                                 textLower.includes('destinatário') ||
                                 textLower.includes('status') ||
                                 textLower.includes('situação') ||
                                 text.length > 100; // Se tem conteúdo substancial
                    
                    let details = 'Sem informações disponíveis';
                    let tracking = 'N/A';
                    let preview = text.substring(0, 200);
                    
                    if (found) {
                        if (textLower.includes('objeto entregue')) {
                            details = 'Objeto entregue com sucesso';
                        } else if (textLower.includes('entregue ao destinatário')) {
                            details = 'Entregue ao destinatário';
                        } else if (textLower.includes('destinatário')) {
                            details = 'Informações de destinatário encontradas';
                        } else if (textLower.includes('status') || textLower.includes('situação')) {
                            details = 'Status de rastreamento disponível';
                        } else {
                            details = 'Objeto encontrado no sistema';
                        }
                        
                        // Tenta extrair código de rastreamento
                        const trackMatch = text.match(/([A-Z]{2}\d{9}[A-Z]{2})/);
                        if (trackMatch) {
                            tracking = trackMatch[1];
                        }
                    } else {
                        details = 'Objeto não encontrado ou informações indisponíveis';
                        tryNextUrl();
                        return;
                    }
                    
                    resolved = true;
                    resolve({
                        found,
                        details,
                        tracking,
                        preview
                    });
                    
                    iframe.remove();
                    
                } catch (error) {
                    console.error('Erro ao processar iframe:', error);
                    tryNextUrl();
                }
            };
            
            iframe.onerror = () => {
                if (resolved) return;
                console.error('Erro ao carregar iframe');
                tryNextUrl();
            };
            
            document.body.appendChild(iframe);
            
            // Inicia primeira tentativa
            tryNextUrl();
            
            // Timeout geral
            setTimeout(() => {
                if (resolved) return;
                resolved = true;
                
                resolve({
                    found: false,
                    details: 'Timeout na consulta - demorou mais de 10 segundos',
                    tracking: 'N/A',
                    preview: 'N/A'
                });
                
                iframe.remove();
            }, 10000);
        });
    }
    
    // Exibe resultados finais em modal elegante
    function displayResults(results) {
        // Remove modal anterior se existir
        const existingModal = document.getElementById('cartaResultsModal');
        if (existingModal) existingModal.remove();
        
        const modal = document.createElement('div');
        modal.id = 'cartaResultsModal';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.9); z-index: 1000001;
            display: flex; align-items: center; justify-content: center;
            padding: 20px; font-family: Arial, sans-serif;
            overflow-y: auto;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: white; padding: 30px; border-radius: 15px;
            width: 100%; max-width: 1200px; max-height: 90%;
            overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            border: 3px solid #007bff;
        `;
        
        const found = results.filter(r => r.status === 'ENCONTRADO').length;
        const notFound = results.filter(r => r.status === 'NÃO ENCONTRADO').length;
        const errors = results.filter(r => r.status === 'ERRO').length;
        
        content.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 3px solid #eee; padding-bottom: 20px;">
                <h2 style="margin: 0; color: #333; font-size: 24px;">
                    📊 Relatório Final - Consulta eCarta
                </h2>
                <button onclick="this.closest('#cartaResultsModal').remove()" 
                        style="background: #dc3545; color: white; border: none; 
                               padding: 12px 18px; border-radius: 8px; cursor: pointer;
                               font-weight: bold; font-size: 14px;">❌ Fechar</button>
            </div>
            
            <div style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 10px; margin-bottom: 25px;">
                <h3 style="margin: 0 0 20px 0; color: #495057; font-size: 18px;">📈 Estatísticas da Consulta</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px;">
                    <div style="text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 2px solid #28a745;">
                        <div style="font-size: 32px; font-weight: bold; color: #28a745; margin-bottom: 5px;">✅ ${found}</div>
                        <div style="font-size: 14px; color: #666; font-weight: bold;">Encontrados</div>
                    </div>
                    <div style="text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 2px solid #dc3545;">
                        <div style="font-size: 32px; font-weight: bold; color: #dc3545; margin-bottom: 5px;">❌ ${notFound}</div>
                        <div style="font-size: 14px; color: #666; font-weight: bold;">Não Encontrados</div>
                    </div>
                    <div style="text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 2px solid #ffc107;">
                        <div style="font-size: 32px; font-weight: bold; color: #ffc107; margin-bottom: 5px;">⚠️ ${errors}</div>
                        <div style="font-size: 14px; color: #666; font-weight: bold;">Erros</div>
                    </div>
                    <div style="text-align: center; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 2px solid #17a2b8;">
                        <div style="font-size: 32px; font-weight: bold; color: #17a2b8; margin-bottom: 5px;">📦 ${results.length}</div>
                        <div style="font-size: 14px; color: #666; font-weight: bold;">Total Consultado</div>
                    </div>
                </div>
            </div>
            
            <div style="overflow-x: auto; border-radius: 10px; border: 1px solid #ddd;">
                <table style="width: 100%; border-collapse: collapse; font-size: 13px; background: white;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #007bff, #0056b3); color: white;">
                            <th style="padding: 15px 10px; border: 1px solid #dee2e6; text-align: left; font-weight: bold;">ID Intimação</th>
                            <th style="padding: 15px 10px; border: 1px solid #dee2e6; text-align: left; font-weight: bold;">Data</th>
                            <th style="padding: 15px 10px; border: 1px solid #dee2e6; text-align: center; font-weight: bold;">Status</th>
                            <th style="padding: 15px 10px; border: 1px solid #dee2e6; text-align: left; font-weight: bold;">Detalhes</th>
                            <th style="padding: 15px 10px; border: 1px solid #dee2e6; text-align: left; font-weight: bold;">Código Rastreamento</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${results.map((r, index) => `
                            <tr style="border-bottom: 1px solid #dee2e6; ${index % 2 === 0 ? 'background: #f8f9fa;' : 'background: white;'}">
                                <td style="padding: 12px 10px; border: 1px solid #dee2e6; font-family: monospace; font-weight: bold; color: #495057; font-size: 12px;">${r.id}</td>
                                <td style="padding: 12px 10px; border: 1px solid #dee2e6; color: #495057;">${r.date}</td>
                                <td style="padding: 12px 10px; border: 1px solid #dee2e6; text-align: center;">
                                    <span style="padding: 8px 15px; border-radius: 20px; font-size: 11px; font-weight: bold; white-space: nowrap;
                                                 background: ${r.status === 'ENCONTRADO' ? '#d4edda' : r.status === 'ERRO' ? '#f8d7da' : '#fff3cd'};
                                                 color: ${r.status === 'ENCONTRADO' ? '#155724' : r.status === 'ERRO' ? '#721c24' : '#856404'};
                                                 border: 2px solid ${r.status === 'ENCONTRADO' ? '#28a745' : r.status === 'ERRO' ? '#dc3545' : '#ffc107'};">
                                        ${r.status === 'ENCONTRADO' ? '✅' : r.status === 'ERRO' ? '⚠️' : '❌'} ${r.status}
                                    </span>
                                </td>
                                <td style="padding: 12px 10px; border: 1px solid #dee2e6; font-size: 12px; color: #495057; max-width: 300px; word-wrap: break-word;">${r.details}</td>
                                <td style="padding: 12px 10px; border: 1px solid #dee2e6; font-size: 12px; font-family: monospace; color: #495057;">${r.rastreamento}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            <div style="margin-top: 25px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666; font-size: 13px; line-height: 1.5;">
                🕒 Consulta realizada em <strong>${new Date().toLocaleString('pt-BR')}</strong><br>
                💾 Dados temporários serão limpos automaticamente em 10 segundos<br>
                📊 Bookmarklet Carta v3 - Sistema de Consulta Automatizada
            </div>
        `;
        
        modal.appendChild(content);
        document.body.appendChild(modal);
        
        showMessage('Consulta finalizada com sucesso! Confira o relatório completo.', 'success', 5000);
        
        // Limpa dados salvos após um tempo
        setTimeout(() => {
            localStorage.removeItem(CONFIG.STORAGE_KEY);
            console.log('🧹 Dados temporários limpos do localStorage');
        }, 10000);
    }
    
    // ==========================================
    // EXECUÇÃO PRINCIPAL
    // ==========================================
    console.log('🚀 Bookmarklet Carta v3 iniciado');
    console.log('📍 Site detectado:', {
        host: currentHost,
        url: currentUrl.substring(0, 100),
        isPje: isPje,
        isEcarta: isEcarta
    });
    
    if (isPje) {
        showMessage('Sistema PJe detectado - Iniciando coleta de dados...', 'info');
        executePjeScript();
    } else if (isEcarta) {
        showMessage('Sistema eCarta detectado - Processando dados salvos...', 'info');
        executeEcartaScript();
    } else {
        showMessage('⚠️ Site não reconhecido! Este bookmarklet deve ser executado no PJe ou eCarta dos Correios.', 'error', 10000);
        console.log('❌ URL não reconhecida:', currentUrl);
        console.log('💡 URLs suportadas: pje.*.jus.br, *.correios.com.br, ecarta.*');
    }
    
})();
    
    const ECARTA_USER = 's164283';
    const ECARTA_PASS = '59Justdoit!1';
    
    function showMessage(text, color = '#007bff') {
        const div = document.createElement('div');
        div.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            background: ${color}; color: white; padding: 10px 15px;
            border-radius: 5px; font-family: Arial; font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            max-width: 300px; word-wrap: break-word;
        `;
        div.textContent = text;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 5000);
    }
    
    // Detecta o site atual
    const currentUrl = window.location.href;
    const isPje = currentUrl.includes('pje.trt2.jus.br');
    const isEcarta = currentUrl.includes('ecarta.trt2.jus.br');
    
    if (isPje) {
        executarPartePje();
    } else if (isEcarta) {
        executarParteEcarta();
    } else {
        showMessage('Este bookmarklet deve ser executado no PJe ou eCarta do TRT2!', '#dc3545');
    }
    
    function executarPartePje() {
        showMessage('🔍 Iniciando busca no PJe...', '#28a745');
        
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
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3); min-width: 300px;
                `;
                
                content.innerHTML = `
                    <h3 style="margin-top: 0; color: #333;">📅 Qual dia analisar?</h3>
                    <p style="color: #666; margin: 15px 0;">
                        Digite apenas 2 dígitos do dia (ex: 15)<br>
                        <small>Deixe vazio para usar a data mais recente</small>
                    </p>
                    <input type="text" id="dayInput" maxlength="2" 
                           style="padding: 10px; border: 2px solid #ddd; border-radius: 4px; 
                                  text-align: center; width: 80px; font-size: 18px; margin: 10px;"
                           placeholder="DD">
                    <br>
                    <button id="okBtn" style="margin: 15px 5px; padding: 10px 20px;
                                               background: #007bff; color: white; border: none;
                                               border-radius: 5px; cursor: pointer; font-size: 14px;">
                        ✅ Buscar
                    </button>
                    <button id="cancelBtn" style="margin: 15px 5px; padding: 10px 20px;
                                                   background: #6c757d; color: white; border: none;
                                                   border-radius: 5px; cursor: pointer; font-size: 14px;">
                        ❌ Cancelar
                    </button>
                `;
                
                modal.appendChild(content);
                document.body.appendChild(modal);
                
                const input = content.querySelector('#dayInput');
                const okBtn = content.querySelector('#okBtn');
                const cancelBtn = content.querySelector('#cancelBtn');
                
                input.focus();
                
                // Permite apenas números
                input.addEventListener('input', (e) => {
                    e.target.value = e.target.value.replace(/[^0-9]/g, '');
                });
                
                function finish(day) {
                    modal.remove();
                    resolve(day);
                }
                
                okBtn.onclick = () => finish(input.value.trim());
                cancelBtn.onclick = () => finish(null);
                
                input.onkeypress = (e) => {
                    if (e.key === 'Enter') finish(input.value.trim());
                    if (e.key === 'Escape') finish(null);
                };
            });
        }
        
        function parseTimeline(selectedDay) {
            const timeline = document.querySelector('#timeline');
            if (!timeline) {
                throw new Error('Timeline não encontrada! Certifique-se de estar na aba "Linha do Tempo" do processo.');
            }
            
            const entries = Array.from(timeline.querySelectorAll('.entry'));
            if (entries.length === 0) {
                throw new Error('Nenhuma entrada encontrada na timeline.');
            }
            
            // Filtra entradas por data se especificada
            let filteredEntries = entries;
            if (selectedDay) {
                const dayPattern = new RegExp(`\\b${selectedDay.padStart(2, '0')}/\\d{2}/\\d{4}\\b`);
                filteredEntries = entries.filter(entry => {
                    const dateText = entry.textContent;
                    return dayPattern.test(dateText);
                });
                
                if (filteredEntries.length === 0) {
                    throw new Error(`Nenhuma entrada encontrada para o dia ${selectedDay}. Verifique se a data está correta.`);
                }
            } else {
                // Usa apenas a entrada mais recente
                filteredEntries = entries.slice(0, 1);
            }
            
            const intimacaoIds = [];
            
            filteredEntries.forEach(entry => {
                const links = entry.querySelectorAll('a[href*="intimacao"]');
                links.forEach(link => {
                    const href = link.href;
                    const match = href.match(/idIntimacao=(\d+)/);
                    if (match) {
                        intimacaoIds.push(match[1]);
                    }
                });
            });
            
            return intimacaoIds;
        }
        
        async function main() {
            try {
                const selectedDay = await askForDate();
                if (selectedDay === null) {
                    showMessage('❌ Operação cancelada pelo usuário', '#6c757d');
                    return;
                }
                
                showMessage('🔍 Analisando timeline...', '#17a2b8');
                const intimacaoIds = parseTimeline(selectedDay);
                
                if (intimacaoIds.length === 0) {
                    throw new Error('Nenhuma intimação encontrada na timeline para o período selecionado.');
                }
                
                showMessage(`✅ Encontradas ${intimacaoIds.length} intimações. Abrindo eCarta...`, '#28a745');
                
                // Salva dados no localStorage
                const dados = {
                    intimacaoIds: intimacaoIds,
                    timestamp: Date.now(),
                    sourceUrl: window.location.href,
                    selectedDay: selectedDay || 'mais_recente'
                };
                
                localStorage.setItem('carta_bookmarklet_data', JSON.stringify(dados));
                
                // Abre eCarta em nova aba
                setTimeout(() => {
                    window.open('https://ecarta.trt2.jus.br/ecarta/', '_blank');
                    showMessage('📧 eCarta aberto! Execute o bookmarklet novamente na nova aba.', '#ffc107');
                }, 1000);
                
            } catch (error) {
                showMessage(`❌ Erro: ${error.message}`, '#dc3545');
                console.error('Erro no PJe:', error);
            }
        }
        
        main();
    }
    
    function executarParteEcarta() {
        showMessage('📧 Iniciando processamento no eCarta...', '#28a745');
        
        // Recupera dados salvos
        const dadosString = localStorage.getItem('carta_bookmarklet_data');
        if (!dadosString) {
            showMessage('❌ Nenhum dado encontrado! Execute primeiro no PJe.', '#dc3545');
            return;
        }
        
        const dados = JSON.parse(dadosString);
        const intimacaoIds = dados.intimacaoIds;
        
        showMessage(`📊 Processando ${intimacaoIds.length} intimações...`, '#17a2b8');
        
        async function fazerLogin() {
            try {
                // Verifica se já está logado
                const logoutLink = document.querySelector('a[href*="logout"], a[href*="sair"]');
                if (logoutLink) {
                    showMessage('✅ Usuário já logado no eCarta!', '#28a745');
                    return true;
                }
                
                // Aguarda a página carregar
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Procura campos de login
                const userField = document.querySelector('input[name="usuario"], input[name="login"], input[type="text"]:not([readonly])');
                const passField = document.querySelector('input[name="senha"], input[name="password"], input[type="password"]');
                
                if (!userField || !passField) {
                    showMessage('⏳ Aguardando campos de login aparecerem...', '#ffc107');
                    setTimeout(() => fazerLogin(), 3000);
                    return false;
                }
                
                showMessage('🔐 Preenchendo dados de login...', '#17a2b8');
                
                // Preenche campos
                userField.value = ECARTA_USER;
                passField.value = ECARTA_PASS;
                
                // Dispara eventos para garantir reconhecimento
                userField.dispatchEvent(new Event('input', { bubbles: true }));
                userField.dispatchEvent(new Event('change', { bubbles: true }));
                passField.dispatchEvent(new Event('input', { bubbles: true }));
                passField.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Procura botão de login
                const loginBtn = document.querySelector('input[type="submit"], button[type="submit"]') ||
                                Array.from(document.querySelectorAll('button, input[type="button"]')).find(btn => 
                                    btn.textContent.toLowerCase().includes('entrar') || 
                                    btn.textContent.toLowerCase().includes('login') ||
                                    btn.value?.toLowerCase().includes('entrar'));
                
                if (loginBtn) {
                    showMessage('🚀 Enviando login...', '#17a2b8');
                    loginBtn.click();
                    return true;
                } else {
                    // Tenta submeter formulário diretamente
                    const form = userField.closest('form');
                    if (form) {
                        form.submit();
                        return true;
                    } else {
                        throw new Error('Botão de login não encontrado!');
                    }
                }
            } catch (error) {
                showMessage(`❌ Erro no login: ${error.message}`, '#dc3545');
                console.error('Erro de login:', error);
                return false;
            }
        }
        
        async function consultarIntimacao(id) {
            return new Promise((resolve) => {
                const timeoutId = setTimeout(() => {
                    resolve({
                        id: id,
                        encontrada: false,
                        erro: 'Timeout - consulta demorou mais de 15 segundos'
                    });
                }, 15000);
                
                const iframe = document.createElement('iframe');
                iframe.style.cssText = 'display: none; width: 0; height: 0;';
                iframe.src = `https://ecarta.trt2.jus.br/ecarta/consultarintimacao.do?idIntimacao=${id}`;
                
                iframe.onload = () => {
                    clearTimeout(timeoutId);
                    try {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (!iframeDoc || !iframeDoc.body) {
                            throw new Error('Não foi possível acessar o conteúdo da página');
                        }
                        
                        const bodyText = iframeDoc.body.textContent.toLowerCase();
                        
                        // Verifica múltiplos indicadores de correio
                        const temCorreio = bodyText.includes('nao apagar nenhum caractere') || 
                                          bodyText.includes('não apagar nenhum caractere') ||
                                          bodyText.includes('correio') ||
                                          bodyText.includes('postal') ||
                                          bodyText.includes('cep') ||
                                          bodyText.includes('endereço');
                        
                        resolve({
                            id: id,
                            encontrada: temCorreio,
                            preview: bodyText.substring(0, 200) + '...'
                        });
                        
                    } catch (error) {
                        resolve({
                            id: id,
                            encontrada: false,
                            erro: `Erro ao processar: ${error.message}`
                        });
                    } finally {
                        iframe.remove();
                    }
                };
                
                iframe.onerror = () => {
                    clearTimeout(timeoutId);
                    iframe.remove();
                    resolve({
                        id: id,
                        encontrada: false,
                        erro: 'Erro ao carregar página da intimação'
                    });
                };
                
                document.body.appendChild(iframe);
            });
        }
        
        function criarRelatorioFinal(resultados) {
            const encontradas = resultados.filter(r => r.encontrada);
            const comErro = resultados.filter(r => r.erro);
            const naoEncontradas = resultados.filter(r => !r.encontrada && !r.erro);
            
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.9); z-index: 10000;
                overflow: auto; padding: 20px; font-family: Arial, sans-serif;
            `;
            
            const content = document.createElement('div');
            content.style.cssText = `
                background: white; max-width: 1000px; margin: 0 auto;
                border-radius: 10px; padding: 30px; position: relative;
            `;
            
            content.innerHTML = `
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #333; margin: 0 0 10px 0;">📊 Relatório Final - eCarta</h2>
                    <p style="color: #666; margin: 0;">Análise concluída em ${new Date().toLocaleString('pt-BR')}</p>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                    <div style="background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <h3 style="margin: 0 0 10px 0; font-size: 24px;">${encontradas.length}</h3>
                        <p style="margin: 0; opacity: 0.9;">📧 Com Correio</p>
                    </div>
                    <div style="background: linear-gradient(135deg, #ffc107, #fd7e14); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <h3 style="margin: 0 0 10px 0; font-size: 24px;">${naoEncontradas.length}</h3>
                        <p style="margin: 0; opacity: 0.9;">❌ Sem Correio</p>
                    </div>
                    <div style="background: linear-gradient(135deg, #dc3545, #e83e8c); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <h3 style="margin: 0 0 10px 0; font-size: 24px;">${comErro.length}</h3>
                        <p style="margin: 0; opacity: 0.9;">⚠️ Com Erro</p>
                    </div>
                    <div style="background: linear-gradient(135deg, #007bff, #6f42c1); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <h3 style="margin: 0 0 10px 0; font-size: 24px;">${resultados.length}</h3>
                        <p style="margin: 0; opacity: 0.9;">📝 Total</p>
                    </div>
                </div>
                
                ${encontradas.length > 0 ? `
                <div style="margin-bottom: 25px;">
                    <h3 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 5px;">
                        ✅ Intimações com Correio (${encontradas.length})
                    </h3>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; margin-top: 15px; background: white;">
                            <thead>
                                <tr style="background: #28a745; color: white;">
                                    <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">ID Intimação</th>
                                    <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${encontradas.map(r => `
                                    <tr style="background: #f8fff8;">
                                        <td style="border: 1px solid #ddd; padding: 12px; font-family: monospace;">${r.id}</td>
                                        <td style="border: 1px solid #ddd; padding: 12px;">
                                            <a href="https://ecarta.trt2.jus.br/ecarta/consultarintimacao.do?idIntimacao=${r.id}" 
                                               target="_blank" 
                                               style="background: #007bff; color: white; padding: 5px 10px; 
                                                      text-decoration: none; border-radius: 3px; font-size: 12px;">
                                                📧 Abrir no eCarta
                                            </a>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                ` : ''}
                
                ${comErro.length > 0 ? `
                <div style="margin-bottom: 25px;">
                    <h3 style="color: #dc3545; border-bottom: 2px solid #dc3545; padding-bottom: 5px;">
                        ⚠️ Erros durante Consulta (${comErro.length})
                    </h3>
                    <div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin-top: 15px;">
                        ${comErro.map(r => `
                            <p style="margin: 5px 0; font-size: 14px;">
                                <strong>ID ${r.id}:</strong> ${r.erro}
                            </p>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                    <button onclick="localStorage.removeItem('carta_bookmarklet_data'); this.closest('.modal').remove();" 
                            style="background: #28a745; color: white; border: none; padding: 12px 25px; 
                                   border-radius: 5px; cursor: pointer; margin-right: 10px; font-size: 14px;">
                        ✅ Concluir e Limpar Dados
                    </button>
                    <button onclick="window.location.reload();" 
                            style="background: #6c757d; color: white; border: none; padding: 12px 25px; 
                                   border-radius: 5px; cursor: pointer; margin-right: 10px; font-size: 14px;">
                        🔄 Tentar Novamente
                    </button>
                    <button onclick="this.closest('.modal').remove();" 
                            style="background: #dc3545; color: white; border: none; padding: 12px 25px; 
                                   border-radius: 5px; cursor: pointer; font-size: 14px;">
                        ❌ Fechar
                    </button>
                </div>
                
                <button onclick="this.closest('.modal').remove();" 
                        style="position: absolute; top: 15px; right: 15px; background: #dc3545; 
                               color: white; border: none; width: 30px; height: 30px; 
                               border-radius: 50%; cursor: pointer; font-size: 16px;">×</button>
            `;
            
            modal.className = 'modal';
            modal.appendChild(content);
            document.body.appendChild(modal);
        }
        
        async function processarIntimacoes() {
            try {
                showMessage('⏳ Aguardando estabilização da página...', '#17a2b8');
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                showMessage('🔍 Iniciando consultas das intimações...', '#17a2b8');
                
                const resultados = [];
                const total = intimacaoIds.length;
                
                for (let i = 0; i < total; i++) {
                    const id = intimacaoIds[i];
                    const progresso = `${i + 1}/${total}`;
                    
                    showMessage(`📋 Consultando ${progresso}: ${id}`, '#17a2b8');
                    
                    const resultado = await consultarIntimacao(id);
                    resultados.push(resultado);
                    
                    // Pausa entre consultas para não sobrecarregar
                    if (i < total - 1) {
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }
                }
                
                showMessage('✅ Todas as consultas concluídas!', '#28a745');
                criarRelatorioFinal(resultados);
                
            } catch (error) {
                showMessage(`❌ Erro no processamento: ${error.message}`, '#dc3545');
                console.error('Erro no processamento:', error);
            }
        }
        
        // Inicia o processo
        fazerLogin().then((sucesso) => {
            if (sucesso) {
                processarIntimacoes();
            }
        });
    }
    
})();
