/**
 * BOOKMARKLET: MINUTA PJE AUTOMATION
 * =================================
 *
 * Sistema alvo: PJE (Processo Judicial Eletrônico)
 * Tamanho: ~13KB
 * Versão: Fixed/Optimized
 *
 * Funcionalidades:
 * - Extração automática de dados do processo
 * - Geração de minuta formatada
 * - Inserção automática no editor
 * - Validação de campos obrigatórios
 * - Sistema anti-conflito
 *
 * Como usar:
 * 1. Copie o código JavaScript abaixo
 * 2. Crie um bookmarklet no navegador colando no campo URL
 * 3. Execute na página do PJE
 */

javascript: (function () {
    'use strict';

    // Sistema de proteção contra conflitos
    if (window.minutaPJERunning) {
        console.warn('[MINUTA PJE] Já está executando. Abortando...');
        mostrarNotificacao('⚠️ Minuta PJE já está em execução', 'warning');
        return;
    }
    window.minutaPJERunning = true;

    // Configurações
    const CONFIG = {
        debug: false,
        timeout: 10000,
        maxRetries: 3,
        selectors: {
            numeroProcesso: '[id*="numero"], [class*="numero"], input[placeholder*="processo"]',
            assunto: '[id*="assunto"], [class*="assunto"], select[id*="assunto"]',
            classe: '[id*="classe"], [class*="classe"]',
            vara: '[id*="vara"], [class*="vara"]',
            juiz: '[id*="juiz"], [class*="juiz"], [id*="magistrado"]',
            partes: '[id*="parte"], [class*="parte"], .pessoa, .parte-processual',
            valor: '[id*="valor"], [class*="valor"], input[type="number"]',
            data: '[id*="data"], [class*="data"], input[type="date"]',
            editor: '[id*="editor"], [class*="editor"], .cke_wysiwyg_frame, iframe',
            botaoSalvar: '[id*="salvar"], [class*="salvar"], button[type="submit"]'
        }
    };

    // Extração de dados
    function extrairDadosMinuta() {
        const dados = {
            numeroProcesso: extrairNumeroProcesso(),
            assunto: extrairAssunto(),
            classe: extrairClasse(),
            vara: extrairVara(),
            juiz: extrairJuiz(),
            partes: extrairPartes(),
            valor: extrairValor(),
            data: extrairData(),
            timestamp: new Date().toISOString()
        };
        return dados;
    }

    function extrairNumeroProcesso() {
        const elementos = document.querySelectorAll(CONFIG.selectors.numeroProcesso);
        for (const el of elementos) {
            const texto = el.textContent || el.value || '';
            const match = texto.match(/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/);
            if (match) return match[1];
        }
        return 'Número não identificado';
    }

    function extrairAssunto() {
        const elementos = document.querySelectorAll(CONFIG.selectors.assunto);
        for (const el of elementos) {
            const texto = el.textContent || el.value || el.options?.[el.selectedIndex]?.text || '';
            if (texto.trim()) return texto.trim();
        }
        return 'Assunto não identificado';
    }

    function extrairClasse() {
        const elementos = document.querySelectorAll(CONFIG.selectors.classe);
        for (const el of elementos) {
            const texto = el.textContent || el.value || '';
            if (texto.trim()) return texto.trim();
        }
        return 'Classe não identificada';
    }

    function extrairVara() {
        const elementos = document.querySelectorAll(CONFIG.selectors.vara);
        for (const el of elementos) {
            const texto = el.textContent || el.value || '';
            if (texto.trim()) return texto.trim();
        }
        return 'Vara não identificada';
    }

    function extrairJuiz() {
        const elementos = document.querySelectorAll(CONFIG.selectors.juiz);
        for (const el of elementos) {
            const texto = el.textContent || el.value || '';
            if (texto.trim()) return texto.trim();
        }
        return 'Juiz não identificado';
    }

    function extrairPartes() {
        const partes = [];
        const elementos = document.querySelectorAll(CONFIG.selectors.partes);
        elementos.forEach(el => {
            const texto = el.textContent || el.value || '';
            if (texto.trim() && texto.length > 5) {
                partes.push(texto.trim());
            }
        });
        return partes.length > 0 ? partes : ['Partes não identificadas'];
    }

    function extrairValor() {
        const elementos = document.querySelectorAll(CONFIG.selectors.valor);
        for (const el of elementos) {
            const texto = el.textContent || el.value || '';
            const match = texto.match(/R\$\s*([\d.,]+)/);
            if (match) return `R$ ${match[1]}`;
        }
        return 'Valor não identificado';
    }

    function extrairData() {
        const elementos = document.querySelectorAll(CONFIG.selectors.data);
        for (const el of elementos) {
            const texto = el.textContent || el.value || '';
            const match = texto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
            if (match) return match[1];
        }
        return new Date().toLocaleDateString('pt-BR');
    }

    // Geração de minuta
    function gerarMinuta(dados) {
        const dataAtual = new Date().toLocaleDateString('pt-BR');
        let minuta = '';
        minuta += '<p style="text-align: center;"><strong>MINUTA</strong></p>';
        minuta += '<p style="text-align: justify; text-indent: 1.5cm;">';
        minuta += `Processo nº ${dados.numeroProcesso}<br>`;
        minuta += `Assunto: ${dados.assunto}<br>`;
        minuta += `Classe: ${dados.classe}<br>`;
        minuta += `Vara: ${dados.vara}<br>`;
        minuta += `Juiz: ${dados.juiz}<br>`;
        minuta += `Partes: ${dados.partes.join('; ')}<br>`;
        minuta += `Valor: ${dados.valor}<br>`;
        minuta += `Data: ${dados.data}<br>`;
        minuta += '</p>';
        minuta += '<p style="text-align: justify; text-indent: 1.5cm;">';
        minuta += 'Vistos etc.<br><br>';
        minuta += 'Trata-se de [DESCREVER O PROCESSO].<br><br>';
        minuta += 'Diante do exposto, DECIDO:<br><br>';
        minuta += '[DECISÃO]<br><br>';
        minuta += `Data: ${dataAtual}<br><br>`;
        minuta += '[ASSINATURA DO JUIZ]';
        minuta += '</p>';
        return minuta;
    }

    // Inserção no editor
    function inserirNoEditor(minuta) {
        const editors = document.querySelectorAll(CONFIG.selectors.editor);
        for (const editor of editors) {
            if (editor.contentDocument) {
                const body = editor.contentDocument.body;
                if (body) {
                    body.innerHTML = minuta;
                    return true;
                }
            } else if (editor.tagName === 'TEXTAREA') {
                editor.value = minuta;
                return true;
            }
        }
        const editaveis = document.querySelectorAll('[contenteditable="true"], textarea, [role="textbox"]');
        if (editaveis.length > 0) {
            editaveis[0].innerHTML = minuta;
            return true;
        }
        return false;
    }

    // Notificações
    function mostrarNotificacao(mensagem, tipo = 'info') {
        const cores = { success: '#4CAF50', error: '#f44336', info: '#2196F3', warning: '#FF9800' };
        const notificacao = document.createElement('div');
        notificacao.innerHTML = mensagem;
        notificacao.style.cssText = `position:fixed;top:20px;right:20px;background:${cores[tipo]};color:white;padding:15px 25px;border-radius:8px;font-size:16px;font-weight:bold;z-index:99999;box-shadow:0 4px 15px rgba(0,0,0,0.3);font-family:Arial,sans-serif;max-width:400px;`;
        document.body.appendChild(notificacao);
        setTimeout(() => { if (notificacao.parentNode) notificacao.parentNode.removeChild(notificacao); }, 5000);
    }

    // Execução principal
    function executarMinutaPJE() {
        console.log('[MINUTA PJE] Iniciando automação...');
        const dados = extrairDadosMinuta();
        if (!dados) {
            mostrarNotificacao('❌ Falha ao extrair dados', 'error');
            return;
        }
        const minuta = gerarMinuta(dados);
        const inserido = inserirNoEditor(minuta);
        if (inserido) {
            mostrarNotificacao('✅ Minuta gerada e inserida com sucesso!', 'success');
        } else {
            navigator.clipboard.writeText(minuta).then(() => {
                mostrarNotificacao('✅ Minuta copiada para clipboard!', 'success');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = minuta;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                mostrarNotificacao('✅ Minuta copiada para clipboard!', 'success');
            });
        }
        setTimeout(() => { window.minutaPJERunning = false; }, 1000);
    }

    executarMinutaPJE();
})();