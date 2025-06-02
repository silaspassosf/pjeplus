// ==UserScript==
// @name         Triagem Petição Inicial Trabalhista - IA Direta (Zona Sul SP)
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Extrai texto do PDF e envia para análise IA (GPT-3.5), seguindo roteiro do TRT2 Zona Sul SP. Não faz análise local, apenas IA. Interface simples, detalha como a resposta foi elaborada.
// @author       GPT-4
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Carrega pdf.js se necessário
    function loadPdfJs(callback) {
        if (window.pdfjsLib) return callback();
        let script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }

    let textoExtraidoGlobal = '';

    // Cria interface principal
    function createUI() {
        if (document.getElementById('trg-peticao-root')) return;
        let root = document.createElement('div');
        root.id = 'trg-peticao-root';
        root.style = 'position:fixed;top:30px;right:30px;z-index:99999;background:#fff;border:2px solid #333;border-radius:8px;padding:24px 20px 16px 20px;box-shadow:0 4px 16px rgba(0,0,0,0.18);font-family:Segoe UI,Arial,sans-serif;max-width:420px;min-width:340px;';
        root.innerHTML = `
            <b style="font-size:18px;">Triagem Petição Inicial - IA Direta (Zona Sul SP)</b>
            <div id="trg-status" style="margin:10px 0 12px 0;color:#444;">Aguardando upload do PDF...</div>
            <input type="file" id="trg-file" accept="application/pdf" style="margin-bottom:10px;">
            <button id="trg-save-txt" style="display:none;margin-bottom:8px;">Salvar texto extraído (.txt)</button>
            <div id="trg-progress" style="margin:8px 0 8px 0;font-size:13px;color:#2e7d32;"></div>
            <button id="trg-openai-review" style="font-size:13px;margin-bottom:8px;">Analisar com IA</button>
            <input id="trg-openai-key" type="password" placeholder="Chave OpenAI (sk-...)" style="width:70%;font-size:13px;margin-bottom:6px;" />
            <button id="trg-openai-save" style="font-size:13px;">Salvar chave</button>
            <div id="trg-openai-status" style="font-size:13px;color:#2e7d32;margin-top:4px;"></div>
            <div id="trg-openai-result" style="margin-top:10px;font-size:14px;background:#f7f7fa;padding:8px 10px;border-radius:6px;display:none;white-space:pre-wrap;"></div>
        `;
        document.body.appendChild(root);
        // Carrega chave salva
        let key = localStorage.getItem('trg-openai-key') || '';
        document.getElementById('trg-openai-key').value = key;
        document.getElementById('trg-openai-save').onclick = function() {
            let k = document.getElementById('trg-openai-key').value.trim();
            if (k.startsWith('sk-')) {
                localStorage.setItem('trg-openai-key', k);
                document.getElementById('trg-openai-status').textContent = 'Chave salva.';
            } else {
                document.getElementById('trg-openai-status').textContent = 'Chave inválida.';
            }
        };
    }

    // Função para extrair texto do PDF
    async function extrairTextoPDF(file, onProgress) {
        return new Promise((resolve, reject) => {
            let reader = new FileReader();
            reader.onload = async function() {
                try {
                    let pdf = await window.pdfjsLib.getDocument({data: new Uint8Array(reader.result)}).promise;
                    let texto = '';
                    for (let i = 1; i <= pdf.numPages; i++) {
                        let page = await pdf.getPage(i);
                        let content = await page.getTextContent();
                        texto += content.items.map(item => item.str).join(' ') + '\n';
                        if (onProgress) onProgress(i, pdf.numPages);
                    }
                    resolve(texto);
                } catch (e) {
                    reject(e);
                }
            };
            reader.onerror = reject;
            reader.readAsArrayBuffer(file);
        });
    }

    // Função para resumir texto extraído antes da análise IA
    function resumirTextoPorChave(texto) {
        const chaves = ['competência', 'reclamante', 'reclamada', 'cnpj', 'pedido', 'valor', 'cep', 'rito', 'parte', 'procurador', 'advogado', 'segredo', 'urgente', 'digital'];
        let linhas = texto.split('\n');
        let blocos = linhas.filter(l => chaves.some(c => l.toLowerCase().includes(c)));
        // Se o resumo ficar muito pequeno, pega também os 10 primeiros parágrafos relevantes
        if (blocos.length < 10) {
            let paragrafos = linhas.filter(p => p.trim().length > 30);
            blocos = blocos.concat(paragrafos.slice(0, 10));
        }
        // Remove duplicados
        return [...new Set(blocos)].join('\n');
    }

    // Monta prompt para OpenAI
    function montarPromptIA(texto) {
        // Aplica resumo automático antes de montar o prompt
        let textoResumido = resumirTextoPorChave(texto);
        const maxLen = 6000; // Reduzido para evitar erro 400
        let avisoTrunc = 'Resumo automático aplicado antes da análise IA.';
        let textoTrunc = textoResumido;
        
        if (textoResumido.length > maxLen) {
            textoTrunc = textoResumido.substring(0, maxLen) + '\n[TRUNCADO]';
            avisoTrunc += '\nAviso: O texto extraído foi truncado para análise IA devido ao limite de tamanho.';
        }
        
        // Monta o prompt de forma mais estruturada
        const prompt = [
            '🧑‍⚖️ Perfil do Assistente Jurídico',
            '',
            'Você atua como assessor jurídico de juiz do trabalho, especializado em análise técnica de petições iniciais no âmbito da Justiça do Trabalho, com foco na competência territorial do Fórum Trabalhista da Zona Sul de São Paulo/SP.',
            '',
            'Domina: legislação trabalhista, CLT, CPC, súmulas, jurisprudência, etc.',
            '',
            'Ao responder:',
            '- Use português técnico e formal, padrão Justiça do Trabalho.',
            '- Não substitui análise de mérito, apenas triagem formal.',
            '- Prefira respostas diretas: "sim", "não", "incompleto", etc.',
            '- Utilize 🔔 ALERTA para vícios, inconsistências ou ausência de dados obrigatórios.',
            '- Liste os itens do roteiro de triagem (competência territorial, rito, partes, CNPJ, etc.) e analise cada um.',
            '- Para cada alerta, cite o trecho relevante do texto extraído.',
            '- Ao final, explique resumidamente como elaborou a resposta, citando critérios, padrões e limitações da análise automática.',
            '',
            'Texto extraído da petição inicial (PDF):',
            textoTrunc,
            '',
            'Responda com uma tabela de alertas (item, alerta, trecho relevante) e, ao final, um parágrafo explicando como a análise foi feita e eventuais limitações.'
        ].join('\n');

        return { prompt, avisoTrunc };
    }

    // Chama OpenAI API
    async function chamarOpenAI(prompt, onStatus, model = 'gpt-3.5-turbo-1106') {
        let key = localStorage.getItem('trg-openai-key') || '';
        if (!key) throw new Error('Chave OpenAI não informada.');
        onStatus('Enviando para OpenAI...');

        // Garante que o prompt seja uma string
        if (typeof prompt !== 'string') {
            console.error('Tipo do prompt:', typeof prompt);
            throw new Error('Prompt deve ser uma string');
        }

        // Constrói messages como um array literal
        const messages = [
            {
                role: "system",
                content: "Você é um assistente jurídico especializado em triagem de petições iniciais trabalhistas."
            },
            {
                role: "user",
                content: prompt
            }
        ];

        // Constrói o payload garantindo que messages seja um array
        const payload = {
            model,
            messages,  // Aqui messages é passado diretamente como array, não como string
            max_tokens: 2048,
            temperature: 0.2
        };

        // Debug do payload
        console.log('Payload antes de JSON.stringify:', {
            ...payload,
            messages: payload.messages.map(m => ({...m}))  // Copia profunda para debug
        });

        try {
            const response = await fetch('https://api.openai.com/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${key}`
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Erro OpenAI:', errorText);
                throw new Error('Erro na API OpenAI: ' + response.status + '\n' + errorText);
            }

            const data = await response.json();
            if (!data.choices?.[0]?.message?.content) {
                console.error('Resposta OpenAI sem conteúdo:', data);
                throw new Error('Resposta da API sem conteúdo válido');
            }
            return data.choices[0].message.content;
        } catch (error) {
            console.error('Erro na chamada OpenAI:', error);
            throw error;
        }
    }

    // Execução principal
    loadPdfJs(() => {
        createUI();
        let fileInput = document.getElementById('trg-file');
        let status = document.getElementById('trg-status');
        let progress = document.getElementById('trg-progress');
        let btnSaveTxt = document.getElementById('trg-save-txt');
        let btnReview = document.getElementById('trg-openai-review');
        let resultDiv = document.getElementById('trg-openai-result');
        let statusDiv = document.getElementById('trg-openai-status');
        fileInput.onchange = async function() {
            let file = fileInput.files[0];
            if (!file) return;
            status.textContent = 'Extraindo o PDF...';
            progress.textContent = '';
            btnSaveTxt.style.display = 'none';
            try {
                let texto = await extrairTextoPDF(file, (pg, total) => {
                    progress.textContent = `Extraindo página ${pg} de ${total}...`;
                });
                textoExtraidoGlobal = texto;
                status.textContent = 'PDF extraído. Pronto para análise IA.';
                btnSaveTxt.style.display = '';
            } catch (e) {
                status.textContent = 'Erro ao extrair o PDF: ' + e;
            }
        };
        btnSaveTxt.onclick = function() {
            const blob = new Blob([textoExtraidoGlobal], {type: 'text/plain'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'texto_extraido_peticao.txt';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 100);
        };
        btnReview.onclick = async function() {
            resultDiv.style.display = 'none';
            resultDiv.textContent = '';
            statusDiv.textContent = '';
            if (!textoExtraidoGlobal || textoExtraidoGlobal.length < 100) {
                statusDiv.textContent = 'Faça upload de um PDF válido primeiro.';
                return;
            }
            let promptObj = montarPromptIA(textoExtraidoGlobal);
            let promptStr = promptObj.prompt;
            try {
                statusDiv.textContent = `Enviando para OpenAI... (prompt: ${promptStr.length} caracteres)`;
                // Corrige: passar apenas promptStr (string), não promptObj (objeto), para chamarOpenAI
                let resposta = await chamarOpenAI(promptStr, msg => statusDiv.textContent = msg);
                resultDiv.textContent = (promptObj.avisoTrunc ? promptObj.avisoTrunc + '\n\n' : '') + resposta;
                resultDiv.style.display = '';
                statusDiv.textContent = 'Análise IA concluída.';
            } catch (e) {
                statusDiv.textContent = 'Erro: ' + e.message + '\n---\nPrompt enviado:\n' + (promptStr ? promptStr.slice(0, 1000) + (promptStr.length > 1000 ? '\n[TRUNCADO]' : '') : '');
            }
        };
    });
})();
