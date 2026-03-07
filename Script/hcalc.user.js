// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.17.0
// @description  Assistente de homologação PJe-Calc
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @connect      cdnjs.cloudflare.com
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==


// ── lib.js ──────────────────────────────────
// ==UserScript==
// @name         PJe - Biblioteca de Parsing de Homologação
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Parser reverso: extrai dados de homologação e gera decisão de liberação automática
// @author       VaraTrabalho
// @match        https://pje.trt2.jus.br/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ==========================================
    // UTILITÁRIOS
    // ==========================================
    
    const bold = (text) => `<strong>${text}</strong>`;
    const u = (text) => `<u>${text}</u>`;
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    
    /**
     * Limpa e normaliza valor monetário extraído
     * @param {string} valor - "1.234,56" ou "R$ 1.234,56"
     * @returns {string} - "1.234,56"
     */
    function normalizarValor(valor) {
        if (!valor) return '0,00';
        return valor.replace(/R\$/g, '').trim();
    }

    /**
     * Converte valor string para número
     * @param {string} valor - "1.234,56"
     * @returns {number}
     */
    function parseMoney(valor) {
        if (!valor) return 0;
        const cleaned = valor.replace(/[^\d,]/g, '').replace(',', '.');
        return parseFloat(cleaned) || 0;
    }

    /**
     * Converte número para string formatada
     * @param {number} num
     * @returns {string} - "1.234,56"
     */
    function formatMoney(num) {
        if (isNaN(num)) return '0,00';
        return num.toFixed(2)
            .replace('.', ',')
            .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    // ==========================================
    // REGEX PATTERNS PARA EXTRAÇÃO
    // ==========================================
    
    const PATTERNS = {
        // Valores principais
        credito: /crédito\s+(?:em|do\s+autor)?\s*(?:em)?\s*(?:R\$|de)?\s*R?\$?\s*([\d.,]+)/i,
        creditoPrincipal: /principal.*?R\$\s*([\d.,]+)/i,
        fgts: /FGTS.*?(?:em|de)?\s*R\$\s*([\d.,]+)/i,
        
        // INSS
        inssEmpregado: /(?:cota do reclamante|desconto.*?previdenciário.*?reclamante).*?R\$\s*([\d.,]+)/i,
        inssPatronal: /(?:cota-parte no INSS|contribuições patronais).*?R\$\s*([\d.,]+)/i,
        inssTotal: /total.*?R\$\s*([\d.,]+)(?=\))/i,
        
        // Honorários
        honAutor: /Honorários advocatícios sucumbenciais.*?pela reclamada.*?(?:importe|valor)\s+(?:de|em)?\s*R\$\s*([\d.,]+)/i,
        honPerito: /(?:perito|honorários.*?perito)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç\s]+?)(?:,|\s+seus).*?R\$\s*([\d.,]+)/ig,
        honPeritoContabil: /(?:perito|honorários\s+contábeis).*?(?:em favor de|ao)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç\s]+?).*?R\$\s*([\d.,]+)/i,
        
        // Datas
        dataAtualizacao: /(?:atualizado|para)\s+(\d{2}\/\d{2}\/\d{4})/i,
        
        // IDs
        idPlanilha: /#(\d+)/,
        
        // Depósito/Pagamento
        depositoRecursal: /depósito recursal.*?#.*?(\d+)/i,
        pagamentoAntecipado: /(?:depósito pela reclamada|Realizado depósito).*?#.*?(\d+)/i
    };

    // ==========================================
    // EXTRAÇÃO DE DADOS
    // ==========================================
    
    /**
     * Extrai todos os dados relevantes de uma homologação
     * @param {string} textoHTML - HTML da homologação
     * @returns {Object} - Objeto com todos os dados extraídos
     */
    function extrairDadosHomologacao(textoHTML) {
        const dados = {
            credito: '',
            fgts: '',
            inss: {
                empregado: '',
                patronal: '',
                total: ''
            },
            honorarios: {
                autor: '',
                peritos: [],
                peritoContabil: null
            },
            data: '',
            deposito: {
                tipo: '', // 'recursal' ou 'pagamento'
                id: ''
            }
        };

        // Extrair crédito (tentar principal primeiro, depois geral)
        let matchCredito = textoHTML.match(PATTERNS.creditoPrincipal);
        if (!matchCredito) {
            matchCredito = textoHTML.match(PATTERNS.credito);
        }
        if (matchCredito) {
            dados.credito = normalizarValor(matchCredito[1]);
        }

        // Extrair FGTS
        const matchFgts = textoHTML.match(PATTERNS.fgts);
        if (matchFgts) {
            dados.fgts = normalizarValor(matchFgts[1]);
        }

        // Extrair INSS
        const matchInssEmp = textoHTML.match(PATTERNS.inssEmpregado);
        if (matchInssEmp) {
            dados.inss.empregado = normalizarValor(matchInssEmp[1]);
        }

        const matchInssPatr = textoHTML.match(PATTERNS.inssPatronal);
        if (matchInssPatr) {
            dados.inss.patronal = normalizarValor(matchInssPatr[1]);
        }

        const matchInssTotal = textoHTML.match(PATTERNS.inssTotal);
        if (matchInssTotal) {
            dados.inss.total = normalizarValor(matchInssTotal[1]);
        }

        // Extrair honorários do autor
        const matchHonAutor = textoHTML.match(PATTERNS.honAutor);
        if (matchHonAutor) {
            dados.honorarios.autor = normalizarValor(matchHonAutor[1]);
        }

        // Extrair perito contábil
        const matchPeritoContabil = textoHTML.match(PATTERNS.honPeritoContabil);
        if (matchPeritoContabil) {
            dados.honorarios.peritoContabil = {
                nome: matchPeritoContabil[1].trim(),
                valor: normalizarValor(matchPeritoContabil[2])
            };
        }

        // Extrair peritos de conhecimento (pode haver múltiplos)
        let matchPerito;
        const regexPerito = new RegExp(PATTERNS.honPerito.source, PATTERNS.honPerito.flags);
        while ((matchPerito = regexPerito.exec(textoHTML)) !== null) {
            const nome = matchPerito[1].trim();
            const valor = normalizarValor(matchPerito[2]);
            
            // Evitar duplicatas e perito contábil
            if (!dados.honorarios.peritos.some(p => p.nome === nome) &&
                (!dados.honorarios.peritoContabil || dados.honorarios.peritoContabil.nome !== nome)) {
                dados.honorarios.peritos.push({ nome, valor });
            }
        }

        // Extrair data de atualização
        const matchData = textoHTML.match(PATTERNS.dataAtualizacao);
        if (matchData) {
            dados.data = matchData[1];
        }

        // Extrair depósito/pagamento antecipado
        const matchPagamento = textoHTML.match(PATTERNS.pagamentoAntecipado);
        if (matchPagamento) {
            dados.deposito.tipo = 'pagamento';
            dados.deposito.id = matchPagamento[1];
        } else {
            const matchDeposito = textoHTML.match(PATTERNS.depositoRecursal);
            if (matchDeposito) {
                dados.deposito.tipo = 'recursal';
                dados.deposito.id = matchDeposito[1];
            }
        }

        return dados;
    }

    // ==========================================
    // GERAÇÃO DE DECISÃO DE LIBERAÇÃO
    // ==========================================
    
    /**
     * Gera HTML da decisão de liberação a partir dos dados extraídos
     * @param {Object} dados - Dados extraídos da homologação
     * @param {string} valorDepositado - Valor depositado pela reclamada (opcional)
     * @returns {string} - HTML da decisão de liberação
     */
    function gerarDecisaoLiberacao(dados, valorDepositado = null) {
        let texto = `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Vistos.</p>`;
        let numLiberacao = 1;

        // Calcular total devido
        let totalDevido = 0;
        if (dados.credito) totalDevido += parseMoney(dados.credito);
        if (dados.inss.total) totalDevido += parseMoney(dados.inss.total);
        if (dados.honorarios.peritoContabil) totalDevido += parseMoney(dados.honorarios.peritoContabil.valor);
        dados.honorarios.peritos.forEach(p => totalDevido += parseMoney(p.valor));
        if (dados.honorarios.autor) totalDevido += parseMoney(dados.honorarios.autor);
        
        // Calcular tipo de liberação baseado no depósito
        let tipoLiberacao = 'padrao'; // padrao | devolucao | remanescente
        let valorDiferenca = 0;
        
        if (valorDepositado) {
            const depositadoNum = parseMoney(valorDepositado);
            const diferencaNum = depositadoNum - totalDevido;
            valorDiferenca = Math.abs(diferencaNum);
            
            if (diferencaNum > 0.02) { // tolerância de 2 centavos
                tipoLiberacao = 'devolucao';
            } else if (diferencaNum < -0.02) {
                tipoLiberacao = 'remanescente';
            }
        }

        // Introdução baseada no tipo de depósito
        if (dados.deposito.tipo === 'pagamento') {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada, #${bold(dados.deposito.id)}.</p>`;
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Passo à liberação de valores:</p>`;
        } else if (dados.deposito.tipo === 'recursal') {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Tendo em vista o depósito recursal #${bold(dados.deposito.id)}, procedo à liberação detalhada dos valores:</p>`;
        } else {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Procedo à liberação dos valores homologados:</p>`;
        }

        // 1) Crédito do reclamante
        if (dados.credito) {
            if (dados.deposito.tipo === 'recursal') {
                texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante o depósito recursal, no valor de ${bold('R$ ' + dados.credito)}, expedindo-se alvará eletrônico.</p>`;
            } else {
                texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante seu crédito, no valor de ${bold('R$ ' + dados.credito)}, expedindo-se alvará eletrônico.</p>`;
            }
            numLiberacao++;
        }

        // 2) INSS
        if (dados.inss.total && dados.inss.empregado && dados.inss.patronal) {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Proceda a Secretaria à transferência de valores ao órgão competente, via Siscondj, sendo: ${bold('R$ ' + dados.inss.empregado)} referente às contribuições previdenciárias parte empregado e ${bold('R$ ' + dados.inss.patronal)} no que concernem às contribuições patronais (total de ${bold('R$ ' + dados.inss.total)}).</p>`;
            numLiberacao++;
        }

        // 3) Honorários periciais - CONTÁBIL PRIMEIRO
        if (dados.honorarios.peritoContabil) {
            const { nome, valor } = dados.honorarios.peritoContabil;
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(nome)} seus honorários, no valor de ${bold('R$ ' + valor)}.</p>`;
            numLiberacao++;
        }

        // 4) Honorários periciais - CONHECIMENTO
        dados.honorarios.peritos.forEach(perito => {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(perito.nome)} seus honorários, no valor de ${bold('R$ ' + perito.valor)}.</p>`;
            numLiberacao++;
        });

        // 5) Honorários do patrono do autor
        if (dados.honorarios.autor) {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao patrono da parte autora seus honorários, no valor de ${bold('R$ ' + dados.honorarios.autor)}.</p>`;
            numLiberacao++;
        }

        // 6) Devolução (se valor depositado foi maior)
        if (tipoLiberacao === 'devolucao') {
            const valorDevolucaoStr = formatMoney(valorDiferenca);
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Devolva-se à reclamada o valor pago a maior, no montante de ${bold('R$ ' + valorDevolucaoStr)}, expedindo-se o competente alvará.</p>`;
        }

        // Linha final baseada no tipo de liberação
        if (tipoLiberacao === 'devolucao') {
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestação das partes.</p>`;
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após, tornem conclusos para extinção da execução.</p>`;
        } else if (tipoLiberacao === 'remanescente') {
            const valorRemanescente = formatMoney(valorDiferenca);
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem prejuízo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + valorRemanescente)} em 15 dias, sob pena de execução.</p>`;
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
        } else {
            // Padrão
            texto += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestações. Silentes, cumpra-se e, após, tornem conclusos para extinção da execução.</p>`;
        }

        return texto;
    }

    // ==========================================
    // VALIDAÇÃO DE DADOS
    // ==========================================
    
    /**
     * Valida se os dados extraídos são suficientes para gerar liberação
     * @param {Object} dados
     * @returns {Object} - { valido: boolean, erros: string[] }
     */
    function validarDadosExtraidos(dados) {
        const erros = [];

        if (!dados.credito) {
            erros.push('❌ Crédito do reclamante não identificado');
        }

        if (dados.inss.total && (!dados.inss.empregado || !dados.inss.patronal)) {
            erros.push('⚠️ INSS total identificado, mas parcelas empregado/patronal incompletas');
        }

        // Validar soma do INSS
        if (dados.inss.empregado && dados.inss.patronal && dados.inss.total) {
            const somaCalculada = parseMoney(dados.inss.empregado) + parseMoney(dados.inss.patronal);
            const totalDeclarado = parseMoney(dados.inss.total);
            const diferenca = Math.abs(somaCalculada - totalDeclarado);
            
            if (diferenca > 0.02) { // tolerância de 2 centavos
                erros.push(`⚠️ Soma INSS inconsistente: ${formatMoney(somaCalculada)} ≠ ${dados.inss.total}`);
            }
        }

        return {
            valido: erros.length === 0,
            erros
        };
    }

    // ==========================================
    // DEBUG E RELATÓRIO
    // ==========================================
    
    /**
     * Gera relatório dos dados extraídos para conferência
     * @param {Object} dados
     * @returns {string} - Texto formatado
     */
    function gerarRelatorioExtracao(dados) {
        let relatorio = '📊 DADOS EXTRAÍDOS DA HOMOLOGAÇÃO\n\n';
        
        // Calcular total devido
        let totalDevido = 0;
        if (dados.credito) totalDevido += parseMoney(dados.credito);
        if (dados.inss.total) totalDevido += parseMoney(dados.inss.total);
        if (dados.honorarios.peritoContabil) totalDevido += parseMoney(dados.honorarios.peritoContabil.valor);
        dados.honorarios.peritos.forEach(p => totalDevido += parseMoney(p.valor));
        if (dados.honorarios.autor) totalDevido += parseMoney(dados.honorarios.autor);
        
        relatorio += '💰 VALORES:\n';
        relatorio += `   Crédito: R$ ${dados.credito || 'NÃO ENCONTRADO'}\n`;
        if (dados.fgts) relatorio += `   FGTS: R$ ${dados.fgts}\n`;
        
        relatorio += '\n🏛️ INSS:\n';
        relatorio += `   Empregado: R$ ${dados.inss.empregado || '-'}\n`;
        relatorio += `   Patronal: R$ ${dados.inss.patronal || '-'}\n`;
        relatorio += `   Total: R$ ${dados.inss.total || '-'}\n`;
        
        if (dados.honorarios.autor || dados.honorarios.peritos.length > 0 || dados.honorarios.peritoContabil) {
            relatorio += '\n💼 HONORÁRIOS:\n';
            if (dados.honorarios.autor) {
                relatorio += `   Autor: R$ ${dados.honorarios.autor}\n`;
            }
            if (dados.honorarios.peritoContabil) {
                relatorio += `   Perito Contábil (${dados.honorarios.peritoContabil.nome}): R$ ${dados.honorarios.peritoContabil.valor}\n`;
            }
            dados.honorarios.peritos.forEach(p => {
                relatorio += `   Perito (${p.nome}): R$ ${p.valor}\n`;
            });
        }
        
        // Total devido
        relatorio += `\n💵 TOTAL DEVIDO: R$ ${formatMoney(totalDevido)}\n`;
        
        if (dados.deposito.tipo) {
            relatorio += '\n💵 DEPÓSITO:\n';
            relatorio += `   Tipo: ${dados.deposito.tipo === 'pagamento' ? 'Pagamento Antecipado' : 'Recursal'}\n`;
            relatorio += `   ID: #${dados.deposito.id}\n`;
        }
        
        if (dados.data) {
            relatorio += `\n📅 Data: ${dados.data}\n`;
        }
        
        return relatorio;
    }

    // ==========================================
    // INTERFACE PÚBLICA (API)
    // ==========================================
    
    /**
     * Função principal: processa homologação e gera liberação
     * @param {string} textoHomologacao - HTML da homologação
     * @param {Object} opcoes - { debug: boolean, validar: boolean, valorDepositado: string }
     * @returns {Object} - { sucesso, html, dados, validacao, relatorio, tipoLiberacao }
     */
    function processarHomologacao(textoHomologacao, opcoes = {}) {
        const { debug = false, validar = true, valorDepositado = null } = opcoes;
        
        // 1. Extrair dados
        const dados = extrairDadosHomologacao(textoHomologacao);
        
        // 2. Validar (opcional)
        let validacao = { valido: true, erros: [] };
        if (validar) {
            validacao = validarDadosExtraidos(dados);
        }
        
        // 3. Gerar decisão
        const html = gerarDecisaoLiberacao(dados, valorDepositado);
        
        // 4. Relatório (se debug)
        const relatorio = debug ? gerarRelatorioExtracao(dados) : null;
        
        // 5. Calcular tipo de liberação (para relatório)
        let tipoLiberacao = 'padrao';
        if (valorDepositado) {
            let totalDevido = 0;
            if (dados.credito) totalDevido += parseMoney(dados.credito);
            if (dados.inss.total) totalDevido += parseMoney(dados.inss.total);
            if (dados.honorarios.peritoContabil) totalDevido += parseMoney(dados.honorarios.peritoContabil.valor);
            dados.honorarios.peritos.forEach(p => totalDevido += parseMoney(p.valor));
            if (dados.honorarios.autor) totalDevido += parseMoney(dados.honorarios.autor);
            
            const depositadoNum = parseMoney(valorDepositado);
            const diferencaNum = depositadoNum - totalDevido;
            
            if (diferencaNum > 0.02) tipoLiberacao = 'devolucao';
            else if (diferencaNum < -0.02) tipoLiberacao = 'remanescente';
        }
        
        return {
            sucesso: validacao.valido,
            html,
            dados,
            validacao,
            relatorio,
            tipoLiberacao
        };
    }

    // ==========================================
    // LEITURA DO HTML DO DOCUMENTO ATIVO
    // ==========================================
    
    /**
     * Lê o HTML do documento ativo no PJe (modal de visualização)
     * @param {number} timeoutMs - Timeout máximo
     * @returns {Object|null} - { texto, html } ou null
     */
    async function lerHtmlOriginal(timeoutMs = 5000) {
        const started = Date.now();

        // 1. Espera o botão aparecer
        let htmlBtn = null;
        while ((Date.now() - started) < timeoutMs) {
            htmlBtn = document.querySelector('button[aria-label="Visualizar HTML original"]');
            if (htmlBtn) break;
            await sleep(150);
        }
        if (!htmlBtn) {
            console.warn('[lib.js] Botão "Visualizar HTML original" não encontrado');
            return null;
        }

        htmlBtn.click();

        // 2. Espera o conteúdo carregar
        let previewEl = null;
        const started2 = Date.now();
        while ((Date.now() - started2) < timeoutMs) {
            previewEl = document.getElementById('previewModeloDocumento');
            if (previewEl && (previewEl.innerText || '').trim().length > 200) break;
            await sleep(150);
        }

        const texto = (previewEl?.innerText || '').trim();
        const html = (previewEl?.innerHTML || '').trim();
        return texto.length > 200 ? { texto, html } : null;
    }

    /**
     * Fecha o modal/viewer atual
     */
    function fecharViewer() {
        const closeBtns = document.querySelectorAll(
            'button[aria-label="Fechar"], .mat-dialog-close, mat-dialog-container button.close, .cdk-overlay-backdrop'
        );
        closeBtns.forEach(b => { try { b.click(); } catch (_) { } });
    }

    // ==========================================
    // PROCESSAMENTO AUTOMÁTICO DO DOCUMENTO ATIVO
    // ==========================================
    
    /**
     * Processa o documento ativo (homologação) e gera liberação automaticamente
     */
    async function processarDocumentoAtivo() {
        try {
            console.log('[lib.js] 🔄 Iniciando leitura do documento ativo...');
            
            // 0. Solicitar valor depositado (ANTES de ler o documento)
            const valorDepositado = prompt(
                '💰 VALOR DEPOSITADO (OPCIONAL)\n\n' +
                '⚠️ DEIXE EM BRANCO para liberação PADRÃO (sem cálculo de diferença)\n\n' +
                'OU\n\n' +
                'Informe o valor depositado para cálculo automático:\n' +
                '  • Se valor = total devido → Liberação padrão\n' +
                '  • Se valor > total devido → Devolução à reclamada\n' +
                '  • Se valor < total devido → Remanescente a pagar\n\n' +
                'Formato: 1234.56 ou 1.234,56',
                ''
            );
            
            // 1. Ler HTML do documento ativo
            const resultado = await lerHtmlOriginal(8000);
            
            if (!resultado || !resultado.texto) {
                alert('❌ Não foi possível ler o documento ativo.\n\n' +
                      'Certifique-se de que:\n' +
                      '1. Há um documento aberto no PJe\n' +
                      '2. O modal de visualização está disponível');
                return;
            }
            
            console.log('[lib.js] ✅ Documento lido com sucesso');
            
            // 2. Fechar viewer
            fecharViewer();
            await sleep(300);
            
            // 3. Processar homologação com valor depositado
            const processado = processarHomologacao(resultado.texto, { 
                debug: true, 
                validar: true,
                valorDepositado: valorDepositado || null
            });
            
            // 4. Validar
            if (!processado.sucesso) {
                const confirmar = confirm(
                    '⚠️ AVISOS DE VALIDAÇÃO:\n\n' +
                    processado.validacao.erros.join('\n') +
                    '\n\nDeseja continuar mesmo assim?'
                );
                if (!confirmar) {
                    console.log('[lib.js] Processamento cancelado pelo usuário');
                    return;
                }
            }
            
            // 5. Mostrar relatório
            if (processado.relatorio) {
                console.log('\n' + processado.relatorio);
            }
            
            // 6. Copiar para clipboard
            const blob = new Blob([processado.html], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            await navigator.clipboard.write([clipboardItem]);
            
            // Mensagem de sucesso baseada no tipo de liberação
            let mensagemTipo = '';
            if (processado.tipoLiberacao === 'devolucao') {
                mensagemTipo = '\n💸 Tipo: COM DEVOLUÇÃO (valor pago a maior)';
            } else if (processado.tipoLiberacao === 'remanescente') {
                mensagemTipo = '\n📋 Tipo: COM REMANESCENTE (falta pagar)';
            } else {
                // Padrão - verificar se foi por não informar valor ou por valor correto
                if (!valorDepositado || valorDepositado.trim() === '') {
                    mensagemTipo = '\n✓ Tipo: PADRÃO (sem cálculo de diferença)';
                } else {
                    mensagemTipo = '\n✓ Tipo: PADRÃO (valor depositado correto)';
                }
            }
            
            alert('✅ Decisão de liberação gerada com sucesso!' +
                  mensagemTipo +
                  '\n\nVá ao editor do PJe e cole (Ctrl+V).\n\n' +
                  'Veja o console (F12) para detalhes dos dados extraídos.');
            
            console.log('[lib.js] ✅ Processo concluído');
            console.log(`[lib.js] 📊 Tipo de liberação: ${processado.tipoLiberacao.toUpperCase()}`);
            
        } catch (erro) {
            console.error('[lib.js] ❌ Erro ao processar documento:', erro);
            alert('❌ Erro ao processar documento:\n\n' + erro.message);
        }
    }

    /**
     * Função auxiliar: copia da área de transferência, processa e cola resultado
     */
    async function processarDaAreaTransferencia() {
        try {
            // Ler clipboard
            const textoCopiado = await navigator.clipboard.readText();
            
            if (!textoCopiado || textoCopiado.length < 100) {
                alert('❌ Nenhum texto válido encontrado na área de transferência.\n\nCopie a homologação completa primeiro.');
                return;
            }
            
            // Solicitar valor depositado
            const valorDepositado = prompt(
                '💰 VALOR DEPOSITADO (OPCIONAL)\n\n' +
                '⚠️ DEIXE EM BRANCO para liberação PADRÃO (sem cálculo de diferença)\n\n' +
                'OU\n\n' +
                'Informe o valor depositado para cálculo automático:\n' +
                '  • Se valor = total devido → Liberação padrão\n' +
                '  • Se valor > total devido → Devolução à reclamada\n' +
                '  • Se valor < total devido → Remanescente a pagar\n\n' +
                'Formato: 1234.56 ou 1.234,56',
                ''
            );
            
            // Processar com valor depositado
            const resultado = processarHomologacao(textoCopiado, { 
                debug: true, 
                validar: true,
                valorDepositado: valorDepositado || null
            });
            
            // Validar
            if (!resultado.sucesso) {
                const confirmar = confirm(
                    '⚠️ AVISOS DE VALIDAÇÃO:\n\n' +
                    resultado.validacao.erros.join('\n') +
                    '\n\nDeseja continuar mesmo assim?'
                );
                if (!confirmar) return;
            }
            
            // Mostrar relatório
            if (resultado.relatorio) {
                console.log(resultado.relatorio);
            }
            
            // Copiar para clipboard
            const blob = new Blob([resultado.html], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            await navigator.clipboard.write([clipboardItem]);
            
            // Mensagem de sucesso baseada no tipo de liberação
            let mensagemTipo = '';
            if (resultado.tipoLiberacao === 'devolucao') {
                mensagemTipo = '\n💸 Tipo: COM DEVOLUÇÃO (valor pago a maior)';
            } else if (resultado.tipoLiberacao === 'remanescente') {
                mensagemTipo = '\n📋 Tipo: COM REMANESCENTE (falta pagar)';
            } else {
                // Padrão - verificar se foi por não informar valor ou por valor correto
                if (!valorDepositado || valorDepositado.trim() === '') {
                    mensagemTipo = '\n✓ Tipo: PADRÃO (sem cálculo de diferença)';
                } else {
                    mensagemTipo = '\n✓ Tipo: PADRÃO (valor depositado correto)';
                }
            }
            
            alert('✅ Decisão de liberação gerada com sucesso!' +
                  mensagemTipo +
                  '\n\nVá ao editor do PJe e cole (Ctrl+V).\n\n' +
                  (resultado.relatorio ? 'Veja o console (F12) para detalhes.' : ''));
            
        } catch (erro) {
            console.error('Erro ao processar homologação:', erro);
            alert('❌ Erro ao processar:\n\n' + erro.message);
        }
    }

    // ==========================================
    // INTERFACE VISUAL - BOTÃO FLUTUANTE
    // ==========================================
    
    /**
     * Cria botão flutuante para geração de liberação
     */
    function criarBotaoFlutuante() {
        // Verificar se já existe
        if (document.getElementById('lib-btn-gerar-liberacao')) return;
        
        // Criar botão
        const btn = document.createElement('button');
        btn.id = 'lib-btn-gerar-liberacao';
        btn.innerHTML = '🔄 Gerar Liberação';
        btn.title = 'Gerar decisão de liberação a partir da homologação atual';
        
        // Estilos
        Object.assign(btn.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            zIndex: '99999',
            padding: '12px 20px',
            backgroundColor: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: 'bold',
            cursor: 'pointer',
            boxShadow: '0 4px 8px rgba(0,0,0,0.3)',
            transition: 'all 0.3s ease',
            fontFamily: 'Arial, sans-serif'
        });
        
        // Hover effect
        btn.addEventListener('mouseenter', () => {
            btn.style.backgroundColor = '#1976D2';
            btn.style.transform = 'scale(1.05)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.backgroundColor = '#2196F3';
            btn.style.transform = 'scale(1)';
        });
        
        // Click handler
        btn.addEventListener('click', async () => {
            btn.disabled = true;
            btn.innerHTML = '⏳ Processando...';
            
            try {
                await processarDocumentoAtivo();
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔄 Gerar Liberação';
            }
        });
        
        // Adicionar ao DOM
        document.body.appendChild(btn);
        console.log('[lib.js] ✅ Botão flutuante criado');
    }
    
    /**
     * Inicializa o botão quando a página estiver pronta
     */
    function inicializar() {
        // Aguardar DOM estar pronto
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', criarBotaoFlutuante);
        } else {
            criarBotaoFlutuante();
        }
        
        // Recriar botão se necessário (mudanças de página SPA)
        const observer = new MutationObserver(() => {
            if (!document.getElementById('lib-btn-gerar-liberacao')) {
                criarBotaoFlutuante();
            }
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // ==========================================
    // EXPORTAR API GLOBAL
    // ==========================================
    
    window.PjeLibParser = {
        // Funções principais
        extrairDados: extrairDadosHomologacao,
        gerarLiberacao: gerarDecisaoLiberacao,
        processar: processarHomologacao,
        processarDocumentoAtivo,
        processarClipboard: processarDaAreaTransferencia,
        
        // Validação e relatório
        validar: validarDadosExtraidos,
        relatorio: gerarRelatorioExtracao,
        
        // Controle de UI
        criarBotao: criarBotaoFlutuante,
        
        // Utilitários auxiliares
        utils: {
            normalizarValor,
            parseMoney,
            formatMoney,
            bold,
            u,
            sleep,
            lerHtmlOriginal,
            fecharViewer
        }
    };

    // Inicializar automaticamente
    inicializar();

    console.log('✅ PjeLibParser carregado!');
    console.log('📌 Botão "🔄 Gerar Liberação" disponível no canto inferior direito');
    console.log('🔧 API disponível em window.PjeLibParser');
    
})();


// ── hcalc-core.js ──────────────────────────────────
( f u n c t i o n ( )   { 
 
         ' u s e   s t r i c t ' ; 
 
         c o n s t   H C A L C _ D E B U G   =   f a l s e ; 
 
         c o n s t   d b g   =   ( . . . a r g s )   = >   {   i f   ( H C A L C _ D E B U G )   c o n s o l e . l o g ( ' [ h c a l c ] ' ,   . . . a r g s ) ;   } ; 
 
         c o n s t   w a r n   =   ( . . . a r g s )   = >   c o n s o l e . w a r n ( ' [ h c a l c ] ' ,   . . . a r g s ) ; 
 
         c o n s t   e r r   =   ( . . . a r g s )   = >   c o n s o l e . e r r o r ( ' [ h c a l c ] ' ,   . . . a r g s ) ; 
 
         i f   ( H C A L C _ D E B U G )   d b g ( ' S c r i p t   c a r r e g a d o   e m : ' ,   w i n d o w . l o c a t i o n . h r e f ) ; 
 
 
 
         i f   ( ! w i n d o w . _ _ h c a l c G l o b a l E r r o r H o o k s I n s t a l l e d )   { 
 
                 w i n d o w . _ _ h c a l c G l o b a l E r r o r H o o k s I n s t a l l e d   =   t r u e ; 
 
                 w i n d o w . a d d E v e n t L i s t e n e r ( ' e r r o r ' ,   ( e v e n t )   = >   { 
 
                         e r r ( ' E r r o   g l o b a l   c a p t u r a d o : ' ,   e v e n t ? . m e s s a g e ,   e v e n t ? . f i l e n a m e ,   e v e n t ? . l i n e n o ,   e v e n t ? . c o l n o ,   e v e n t ? . e r r o r ) ; 
 
                 } ) ; 
 
                 w i n d o w . a d d E v e n t L i s t e n e r ( ' u n h a n d l e d r e j e c t i o n ' ,   ( e v e n t )   = >   { 
 
                         e r r ( ' P r o m i s e   r e j e i t a d a   s e m   t r a t a m e n t o : ' ,   e v e n t ? . r e a s o n ) ; 
 
                 } ) ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   E S T A D O   C E N T R A L   H C A L C 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   C e n t r a l i z a   t o d a s   a s   v a r i % v e i s   d e   e s t a d o   d o   s c r i p t 
 
         / /   P e r m i t e   d i s p o s e ( )   c o m p l e t o   p a r a   e v i t a r   v a z a m e n t o s   d e   m e m %%r i a 
 
         i f   ( ! w i n d o w . h c a l c S t a t e )   { 
 
                 w i n d o w . h c a l c S t a t e   =   { 
 
                         / /   C a c h e   d e   p a r t e s   ( l i m i t a d o   a   5   e n t r a d a s ) 
 
                         c a l c P a r t e s C a c h e :   { } , 
 
 
 
                         / /   F l a g s   d e   e x e c u % % o 
 
                         p r e p R u n n i n g :   f a l s e , 
 
 
 
                         / /   R e s u l t a d o s   d o   p r e p 
 
                         p r e p R e s u l t :   n u l l , 
 
                         t i m e l i n e D a t a :   n u l l , 
 
 
 
                         / /   D a d o s   d e t e c t a d o s 
 
                         p e r i t o s C o n h e c i m e n t o :   [ ] , 
 
                         p a r t e s D a t a :   n u l l , 
 
 
 
                         / /   A b o r t C o n t r o l l e r   p a r a   c a n c e l a m e n t o   d e   o p e r a % % e s 
 
                         a b o r t C o n t r o l l e r :   n u l l , 
 
 
 
                         / /   F A S E   1 :   D a d o s   d a   p l a n i l h a   P J e - C a l c   ( e x t r a % % o   P D F ) 
 
                         p l a n i l h a E x t r a c a o D a t a :   n u l l ,     / /   { v e r b a s ,   f g t s ,   i n s s ,   d a t a ,   i d ,   . . . } 
 
                         p l a n i l h a C a r r e g a d a :   f a l s e , 
 
                         p d f j s L o a d e d :   f a l s e , 
 
 
 
                         / /   F A S E   2 :   M %Q%l t i p l o s   d e p %%s i t o s 
 
                         d e p o s i t o s R e c u r s a i s :   [ ] ,     / /   [ { i d x ,   t i p o ,   d e p o s i t a n t e ,   i d ,   i s P r i n c i p a l ,   l i b e r a c a o } ] 
 
                         p a g a m e n t o s A n t e c i p a d o s :   [ ] ,     / /   [ { i d x ,   i d ,   t i p o L i b ,   r e m V a l o r ,   r e m T i t u l o ,   d e v V a l o r } ] 
 
                         n e x t D e p o s i t o I d x :   0 , 
 
                         n e x t P a g a m e n t o I d x :   0 , 
 
 
 
                         / /   F A S E   3 :   P l a n i l h a s   e x t r a s   p a r a   p e r % o d o s   d i v e r s o s 
 
                         p l a n i l h a s D i s p o n i v e i s :   [ ] ,     / /   [ { i d ,   l a b e l ,   d a d o s } ] 
 
 
 
                         / /   M % t o d o   d e   l i m p e z a   c o m p l e t a 
 
                         d i s p o s e ( )   { 
 
                                 d b g ( ' E x e c u t a n d o   d i s p o s e ( )   -   l i m p a n d o   e s t a d o   h c a l c ' ) ; 
 
 
 
                                 / /   A b o r t a r   o p e r a % % e s   e m   a n d a m e n t o 
 
                                 i f   ( t h i s . a b o r t C o n t r o l l e r )   { 
 
                                         t h i s . a b o r t C o n t r o l l e r . a b o r t ( ) ; 
 
                                         t h i s . a b o r t C o n t r o l l e r   =   n u l l ; 
 
                                 } 
 
 
 
                                 t h i s . c a l c P a r t e s C a c h e   =   { } ; 
 
                                 t h i s . p r e p R u n n i n g   =   f a l s e ; 
 
                                 t h i s . p r e p R e s u l t   =   n u l l ; 
 
                                 t h i s . t i m e l i n e D a t a   =   n u l l ; 
 
                                 t h i s . p e r i t o s C o n h e c i m e n t o   =   [ ] ; 
 
                                 t h i s . p a r t e s D a t a   =   n u l l ; 
 
                                 t h i s . p l a n i l h a E x t r a c a o D a t a   =   n u l l ; 
 
                                 t h i s . p l a n i l h a C a r r e g a d a   =   f a l s e ; 
 
                                 t h i s . p l a n i l h a s D i s p o n i v e i s   =   [ ] ; 
 
                                 t h i s . d e p o s i t o s R e c u r s a i s   =   [ ] ; 
 
                                 t h i s . p a g a m e n t o s A n t e c i p a d o s   =   [ ] ; 
 
                                 t h i s . n e x t D e p o s i t o I d x   =   0 ; 
 
                                 t h i s . n e x t P a g a m e n t o I d x   =   0 ; 
 
                                 i f   ( t h i s . _ p d f W o r k e r U r l )   { 
 
                                         U R L . r e v o k e O b j e c t U R L ( t h i s . _ p d f W o r k e r U r l ) ; 
 
                                         t h i s . _ p d f W o r k e r U r l   =   n u l l ; 
 
                                 } 
 
                                 d b g ( ' E s t a d o   h c a l c   l i m p o ' ) ; 
 
                         } , 
 
 
 
                         / /   M % t o d o   d e   r e s e t   p a r c i a l   ( m a n t % m   c a c h e ) 
 
                         r e s e t P r e p ( )   { 
 
                                 / /   A b o r t a r   p r e p   e m   a n d a m e n t o 
 
                                 i f   ( t h i s . a b o r t C o n t r o l l e r )   { 
 
                                         t h i s . a b o r t C o n t r o l l e r . a b o r t ( ) ; 
 
                                         t h i s . a b o r t C o n t r o l l e r   =   n u l l ; 
 
                                 } 
 
 
 
                                 t h i s . p r e p R e s u l t   =   n u l l ; 
 
                                 t h i s . t i m e l i n e D a t a   =   n u l l ; 
 
                                 t h i s . p r e p R u n n i n g   =   f a l s e ; 
 
                                 t h i s . p l a n i l h a E x t r a c a o D a t a   =   n u l l ; 
 
                                 t h i s . p l a n i l h a C a r r e g a d a   =   f a l s e ; 
 
                         } 
 
                 } ; 
 
         } 
 
 
 
         / /   A l i a s e s   d e   r e t r o c o m p a t i b i l i d a d e   ( a p o n t a m   p a r a   h c a l c S t a t e ) 
 
         / /   P e r m i t e   q u e   c %%d i g o   e x i s t e n t e   c o n t i n u e   f u n c i o n a n d o   s e m   m o d i f i c a % % o 
 
         O b j e c t . d e f i n e P r o p e r t y ( w i n d o w ,   ' c a l c P a r t e s C a c h e ' ,   { 
 
                 g e t ( )   {   r e t u r n   w i n d o w . h c a l c S t a t e . c a l c P a r t e s C a c h e ;   } , 
 
                 s e t ( v a l )   {   w i n d o w . h c a l c S t a t e . c a l c P a r t e s C a c h e   =   v a l ;   } , 
 
                 c o n f i g u r a b l e :   t r u e 
 
         } ) ; 
 
         O b j e c t . d e f i n e P r o p e r t y ( w i n d o w ,   ' h c a l c P r e p R u n n i n g ' ,   { 
 
                 g e t ( )   {   r e t u r n   w i n d o w . h c a l c S t a t e . p r e p R u n n i n g ;   } , 
 
                 s e t ( v a l )   {   w i n d o w . h c a l c S t a t e . p r e p R u n n i n g   =   v a l ;   } , 
 
                 c o n f i g u r a b l e :   t r u e 
 
         } ) ; 
 
         O b j e c t . d e f i n e P r o p e r t y ( w i n d o w ,   ' h c a l c P r e p R e s u l t ' ,   { 
 
                 g e t ( )   {   r e t u r n   w i n d o w . h c a l c S t a t e . p r e p R e s u l t ;   } , 
 
                 s e t ( v a l )   {   w i n d o w . h c a l c S t a t e . p r e p R e s u l t   =   v a l ;   } , 
 
                 c o n f i g u r a b l e :   t r u e 
 
         } ) ; 
 
         O b j e c t . d e f i n e P r o p e r t y ( w i n d o w ,   ' h c a l c T i m e l i n e D a t a ' ,   { 
 
                 g e t ( )   {   r e t u r n   w i n d o w . h c a l c S t a t e . t i m e l i n e D a t a ;   } , 
 
                 s e t ( v a l )   {   w i n d o w . h c a l c S t a t e . t i m e l i n e D a t a   =   v a l ;   } , 
 
                 c o n f i g u r a b l e :   t r u e 
 
         } ) ; 
 
         O b j e c t . d e f i n e P r o p e r t y ( w i n d o w ,   ' h c a l c P e r i t o s C o n h e c i m e n t o D e t e c t a d o s ' ,   { 
 
                 g e t ( )   {   r e t u r n   w i n d o w . h c a l c S t a t e . p e r i t o s C o n h e c i m e n t o ;   } , 
 
                 s e t ( v a l )   {   w i n d o w . h c a l c S t a t e . p e r i t o s C o n h e c i m e n t o   =   v a l ;   } , 
 
                 c o n f i g u r a b l e :   t r u e 
 
         } ) ; 
 
         O b j e c t . d e f i n e P r o p e r t y ( w i n d o w ,   ' h c a l c P a r t e s D a t a ' ,   { 
 
                 g e t ( )   {   r e t u r n   w i n d o w . h c a l c S t a t e . p a r t e s D a t a ;   } , 
 
                 s e t ( v a l )   {   w i n d o w . h c a l c S t a t e . p a r t e s D a t a   =   v a l ;   } , 
 
                 c o n f i g u r a b l e :   t r u e 
 
         } ) ; 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   M O N I T O R   D E   N A V E G A % % O   S P A 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   D e t e c t a   m u d a n % a   d e   U R L   n o   P J e   ( S P A )   e   l i m p a   e s t a d o   a u t o m a t i c a m e n t e 
 
         / /   P r e v i n e   v a z a m e n t o   d e   m e m %%r i a   a o   t r o c a r   d e   p r o c e s s o   s e m   f e c h a r   o v e r l a y 
 
         / /   O T I M I Z A % % O :   H i s t o r y   A P I   h o o k s   a o   i n v % s   d e   M u t a t i o n O b s e r v e r   p e s a d o 
 
         l e t   l a s t U r l   =   l o c a t i o n . h r e f ; 
 
 
 
         f u n c t i o n   h a n d l e S p a N a v i g a t i o n ( )   { 
 
                 c o n s t   u r l   =   l o c a t i o n . h r e f ; 
 
                 i f   ( u r l   ! = =   l a s t U r l )   { 
 
                         l a s t U r l   =   u r l ; 
 
                         d b g ( ' N a v e g a % % o   S P A   d e t e c t a d a ,   l i m p a n d o   e s t a d o . . . ' ) ; 
 
 
 
                         / /   D i s p o s e   c o m p l e t o 
 
                         i f   ( w i n d o w . h c a l c S t a t e )   { 
 
                                 w i n d o w . h c a l c S t a t e . d i s p o s e ( ) ; 
 
                         } 
 
 
 
                         / /   O c u l t a r   o v e r l a y   s e   e s t i v e r   a b e r t o 
 
                         c o n s t   o v e r l a y   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' h o m o l o g a c a o - o v e r l a y ' ) ; 
 
                         i f   ( o v e r l a y )   o v e r l a y . s t y l e . d i s p l a y   =   ' n o n e ' ; 
 
                 } 
 
         } 
 
 
 
         / /   I n t e r c e p t a   p u s h S t a t e   ( n a v e g a % % o   p r o g r a m % t i c a   A n g u l a r ) 
 
         c o n s t   _ p u s h S t a t e   =   h i s t o r y . p u s h S t a t e . b i n d ( h i s t o r y ) ; 
 
         h i s t o r y . p u s h S t a t e   =   f u n c t i o n ( . . . a r g s )   { 
 
                 _ p u s h S t a t e ( . . . a r g s ) ; 
 
                 h a n d l e S p a N a v i g a t i o n ( ) ; 
 
         } ; 
 
 
 
         / /   I n t e r c e p t a   p o p s t a t e   ( b o t % o   v o l t a r / a v a n % a r ) 
 
         w i n d o w . a d d E v e n t L i s t e n e r ( ' p o p s t a t e ' ,   h a n d l e S p a N a v i g a t i o n ) ; 
 
 
 
 
 
         / /   p r e p . j s        P r e p a r a % % o   p r % - o v e r l a y   p a r a   h c a l c . j s 
 
         / /   V a r r e   t i m e l i n e ,   e x t r a i   d a d o s   d a   s e n t e n % a ,   c r u z a   p e r i t o s   c o m   A J - J T ,   m o n t a   d e p %%s i t o s . 
 
         / /   U s o :   c o n s t   r e s u l t   =   a w a i t   w i n d o w . e x e c u t a r P r e p ( p a r t e s D a t a ,   p e r i t o s C o n h e c i m e n t o ) ; 
 
 
 
         / /   ( I I F E   r e m o v i d a   p a r a   e s c o p o   %Q%n i c o ) 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   U T I L I D A D E S 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         f u n c t i o n   s l e e p ( m s )   {   r e t u r n   n e w   P r o m i s e ( r   = >   s e t T i m e o u t ( r ,   m s ) ) ;   } 
 
 
 
         f u n c t i o n   n o r m a l i z e T e x t ( s t r )   { 
 
                 r e t u r n   ( s t r   | |   ' ' ) . n o r m a l i z e ( ' N F D ' ) . r e p l a c e ( / [ \ u 0 3 0 0 - \ u 0 3 6 f ] / g ,   ' ' ) . t o L o w e r C a s e ( ) . t r i m ( ) ; 
 
         } 
 
 
 
         / /   N o r m a l i z a   d a t a   d e   " 1 7   n o v .   2 0 2 5 "   p a r a   " 1 7 / 1 1 / 2 0 2 5 " 
 
         f u n c t i o n   n o r m a l i z a r D a t a T i m e l i n e ( d a t a S t r )   { 
 
                 i f   ( ! d a t a S t r )   r e t u r n   ' ' ; 
 
                 c o n s t   m e s e s   =   { 
 
                         ' j a n ' :   ' 0 1 ' ,   ' f e v ' :   ' 0 2 ' ,   ' m a r ' :   ' 0 3 ' ,   ' a b r ' :   ' 0 4 ' ,   ' m a i ' :   ' 0 5 ' ,   ' j u n ' :   ' 0 6 ' , 
 
                         ' j u l ' :   ' 0 7 ' ,   ' a g o ' :   ' 0 8 ' ,   ' s e t ' :   ' 0 9 ' ,   ' o u t ' :   ' 1 0 ' ,   ' n o v ' :   ' 1 1 ' ,   ' d e z ' :   ' 1 2 ' 
 
                 } ; 
 
                 / /   P a d r % o :   " 1 7   n o v .   2 0 2 5 "   o u   " 1 7   n o v   2 0 2 5 " 
 
                 c o n s t   m a t c h   =   d a t a S t r . m a t c h ( / ( \ d { 1 , 2 } ) \ s + ( \ w { 3 } ) \ . ? \ s + ( \ d { 4 } ) / ) ; 
 
                 i f   ( m a t c h )   { 
 
                         c o n s t   d i a   =   m a t c h [ 1 ] . p a d S t a r t ( 2 ,   ' 0 ' ) ; 
 
                         c o n s t   m e s   =   m e s e s [ m a t c h [ 2 ] . t o L o w e r C a s e ( ) ]   | |   ' 0 0 ' ; 
 
                         c o n s t   a n o   =   m a t c h [ 3 ] ; 
 
                         r e t u r n   ` $ { d i a } / $ { m e s } / $ { a n o } ` ; 
 
                 } 
 
                 r e t u r n   d a t a S t r ;   / /   R e t o r n a   o r i g i n a l   s e   n % o   r e c o n h e c e r 
 
         } 
 
 
 
         / /   D e s t a c a   u m   e l e m e n t o   n a   t i m e l i n e   ( u s a d o   p o r   l i n k s   d e   r e c u r s o s ) 
 
         f u n c t i o n   d e s t a c a r E l e m e n t o N a T i m e l i n e ( h r e f )   { 
 
                 t r y   { 
 
                         / /   T e n t a r   e n c o n t r a r   o   e l e m e n t o   p e l o   h r e f 
 
                         c o n s t   l i n k   =   d o c u m e n t . q u e r y S e l e c t o r ( ` a [ h r e f = " $ { h r e f } " ] ` ) ; 
 
                         i f   ( ! l i n k )   { 
 
                                 c o n s o l e . w a r n ( ' [ h c a l c ]   E l e m e n t o   n % o   e n c o n t r a d o   n a   t i m e l i n e : ' ,   h r e f ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         / /   E n c o n t r a r   o   c o n t a i n e r   d o   i t e m   n a   t i m e l i n e 
 
                         l e t   c o n t a i n e r   =   l i n k . c l o s e s t ( ' l i . t l - i t e m - c o n t a i n e r ' )   | | 
 
                                                       l i n k . c l o s e s t ( ' . t l - i t e m - c o n t a i n e r ' )   | | 
 
                                                       l i n k . c l o s e s t ( ' . t i m e l i n e - i t e m ' ) ; 
 
                       
 
                         i f   ( ! c o n t a i n e r )   { 
 
                                 c o n s o l e . w a r n ( ' [ h c a l c ]   C o n t a i n e r   d o   i t e m   n % o   e n c o n t r a d o ' ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         / /   S c r o l l   s u a v e   a t %   o   e l e m e n t o 
 
                         c o n t a i n e r . s c r o l l I n t o V i e w ( {   b e h a v i o r :   ' s m o o t h ' ,   b l o c k :   ' c e n t e r '   } ) ; 
 
 
 
                         / /   S a l v a r   e s t i l o   o r i g i n a l 
 
                         c o n s t   o r i g i n a l B o r d e r   =   c o n t a i n e r . s t y l e . b o r d e r ; 
 
                         c o n s t   o r i g i n a l B a c k g r o u n d   =   c o n t a i n e r . s t y l e . b a c k g r o u n d ; 
 
                         c o n s t   o r i g i n a l T r a n s i t i o n   =   c o n t a i n e r . s t y l e . t r a n s i t i o n ; 
 
 
 
                         / /   A p l i c a r   d e s t a q u e 
 
                         c o n t a i n e r . s t y l e . t r a n s i t i o n   =   ' a l l   0 . 3 s   e a s e ' ; 
 
                         c o n t a i n e r . s t y l e . b o r d e r   =   ' 2 p x   s o l i d   # f b b f 2 4 ' ; 
 
                         c o n t a i n e r . s t y l e . b a c k g r o u n d   =   ' # f f f b e b ' ; 
 
 
 
                         / /   R e m o v e r   d e s t a q u e   a p %%s   3   s e g u n d o s 
 
                         s e t T i m e o u t ( ( )   = >   { 
 
                                 c o n t a i n e r . s t y l e . t r a n s i t i o n   =   ' a l l   0 . 5 s   e a s e ' ; 
 
                                 c o n t a i n e r . s t y l e . b o r d e r   =   o r i g i n a l B o r d e r ; 
 
                                 c o n t a i n e r . s t y l e . b a c k g r o u n d   =   o r i g i n a l B a c k g r o u n d ; 
 
                               
 
                                 / /   R e s t a u r a r   t r a n s i t i o n   o r i g i n a l   a p %%s   a n i m a % % o 
 
                                 s e t T i m e o u t ( ( )   = >   { 
 
                                         c o n t a i n e r . s t y l e . t r a n s i t i o n   =   o r i g i n a l T r a n s i t i o n ; 
 
                                 } ,   5 0 0 ) ; 
 
                         } ,   3 0 0 0 ) ; 
 
 
 
                         c o n s o l e . l o g ( ' [ h c a l c ]   E l e m e n t o   d e s t a c a d o   n a   t i m e l i n e : ' ,   h r e f ) ; 
 
                 }   c a t c h   ( e r r o r )   { 
 
                         c o n s o l e . e r r o r ( ' [ h c a l c ]   E r r o   a o   d e s t a c a r   e l e m e n t o : ' ,   e r r o r ) ; 
 
                 } 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   T I M E L I N E :   V A R R E D U R A   % N I C A 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         f u n c t i o n   g e t T i m e l i n e I t e m s ( )   { 
 
                 c o n s t   s e l e c t o r s   =   [ ' l i . t l - i t e m - c o n t a i n e r ' ,   ' . t l - d a t a   . t l - i t e m - c o n t a i n e r ' ,   ' . t i m e l i n e - i t e m ' ] ; 
 
                 f o r   ( c o n s t   s e l   o f   s e l e c t o r s )   { 
 
                         c o n s t   i t e m s   =   A r r a y . f r o m ( d o c u m e n t . q u e r y S e l e c t o r A l l ( s e l ) ) ; 
 
                         i f   ( i t e m s . l e n g t h   >   0 )   r e t u r n   i t e m s ; 
 
                 } 
 
                 r e t u r n   [ ] ; 
 
         } 
 
 
 
         f u n c t i o n   e x t r a c t D a t a F r o m I t e m ( i t e m )   { 
 
                 l e t   e l   =   n u l l ; 
 
                 l e t   p r e v   =   i t e m . p r e v i o u s E l e m e n t S i b l i n g ; 
 
                 w h i l e   ( p r e v )   { 
 
                         e l   =   p r e v . q u e r y S e l e c t o r ( ' . t l - d a t a [ n a m e = " d a t a I t e m T i m e l i n e " ] ' )   | |   p r e v . q u e r y S e l e c t o r ( ' . t l - d a t a ' ) ; 
 
                         i f   ( e l )   b r e a k ; 
 
                         p r e v   =   p r e v . p r e v i o u s E l e m e n t S i b l i n g ; 
 
                 } 
 
                 i f   ( ! e l )   e l   =   i t e m . q u e r y S e l e c t o r ( ' . t l - d a t a [ n a m e = " d a t a I t e m T i m e l i n e " ] ' )   | |   i t e m . q u e r y S e l e c t o r ( ' . t l - d a t a ' ) ; 
 
                 c o n s t   d a t a O r i g i n a l   =   ( e l ? . t e x t C o n t e n t   | |   ' ' ) . t r i m ( ) ; 
 
                 r e t u r n   n o r m a l i z a r D a t a T i m e l i n e ( d a t a O r i g i n a l ) ; 
 
         } 
 
 
 
         f u n c t i o n   t i p o D o c u m e n t o D o I t e m ( i t e m )   { 
 
                 c o n s t   l i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ t a r g e t = " _ b l a n k " ] ' ) ; 
 
                 i f   ( ! l i n k )   r e t u r n   ' ' ; 
 
                 c o n s t   a r i a L a b e l   =   l i n k . g e t A t t r i b u t e ( ' a r i a - l a b e l ' )   | |   ' ' ; 
 
                 c o n s t   m   =   a r i a L a b e l . m a t c h ( / T i p o   d o   d o c u m e n t o : \ s * ( [ ^ . ] + ) / i ) ; 
 
                 r e t u r n   m   ?   n o r m a l i z e T e x t ( m [ 1 ] . t r i m ( ) )   :   ' ' ; 
 
         } 
 
 
 
         f u n c t i o n   t i t u l o D o c u m e n t o D o I t e m ( i t e m )   { 
 
                 c o n s t   l i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ t a r g e t = " _ b l a n k " ] ' ) ; 
 
                 i f   ( ! l i n k )   r e t u r n   ' ' ; 
 
                 c o n s t   a r i a L a b e l   =   l i n k . g e t A t t r i b u t e ( ' a r i a - l a b e l ' )   | |   ' ' ; 
 
                 c o n s t   m   =   a r i a L a b e l . m a t c h ( / T % t u l o : \ s * \ ( ( [ ^ ) ] + ) \ ) / i ) ; 
 
                 r e t u r n   m   ?   n o r m a l i z e T e x t ( m [ 1 ] . t r i m ( ) )   :   ' ' ; 
 
         } 
 
 
 
         f u n c t i o n   h a s A n e x o N o I t e m ( i t e m )   { 
 
                 i f   ( ! i t e m )   r e t u r n   f a l s e ; 
 
                 c o n s t   s e l s   =   [ 
 
                         ' d i v [ n a m e = " m o s t r a r O u O c u l t a r A n e x o s " ] ' , 
 
                         ' p j e - t i m e l i n e - a n e x o s   d i v [ n a m e = " a r e a A n e x o s " ] ' , 
 
                         ' . f a - p a p e r c l i p ' 
 
                 ] ; 
 
                 r e t u r n   s e l s . s o m e ( s   = >   i t e m . q u e r y S e l e c t o r ( s ) ) ; 
 
         } 
 
 
 
         f u n c t i o n   i s P o l o P a s s i v o N o I t e m ( i t e m )   { 
 
                 i f   ( ! i t e m )   r e t u r n   f a l s e ; 
 
                 c o n s t   c o n t a i n e r   =   i t e m . c l o s e s t ( ' l i . t l - i t e m - c o n t a i n e r ' )   | |   i t e m ; 
 
                 r e t u r n   ! ! c o n t a i n e r . q u e r y S e l e c t o r ( ' . i c o n e - p o l o - p a s s i v o ,   [ c l a s s * = " p o l o - p a s s i v o " ] ' ) ; 
 
         } 
 
 
 
         / /   E x t r a i   o   n o m e   d a   p a r t e   d o   p o l o   p a s s i v o   a   p a r t i r   d o   a r i a - l a b e l   d o   d i v   t i p o I t e m T i m e l i n e 
 
         / /   E x :   a r i a - l a b e l = " V I B R A S I L   I N D U S T R I A   D E   A R T E F A T O S   D E   B O R R A C H A   L T D A " 
 
         f u n c t i o n   n o m e P a s s i v o D o I t e m ( i t e m )   { 
 
                 i f   ( ! i t e m )   r e t u r n   ' ' ; 
 
                 c o n s t   c o n t a i n e r   =   i t e m . c l o s e s t ( ' l i . t l - i t e m - c o n t a i n e r ' )   | |   i t e m ; 
 
               
 
                 / /   E S T R A T % G I A   P R I N C I P A L :   a r i a - l a b e l   d o   % c o n e   d o   p o l o 
 
                 c o n s t   s e l e t o r e s   =   [ 
 
                         ' d i v [ n a m e = " t i p o I t e m T i m e l i n e " ] [ a r i a - l a b e l ] ' , 
 
                         ' [ n a m e = " t i p o I t e m T i m e l i n e " ] [ a r i a - l a b e l ] ' , 
 
                         ' d i v . t l - i c o n [ a r i a - l a b e l ] ' , 
 
                         ' [ r o l e = " i m g " ] [ a r i a - l a b e l ] ' 
 
                 ] ; 
 
               
 
                 f o r   ( c o n s t   s e l   o f   s e l e t o r e s )   { 
 
                         c o n s t   e l e m e n t o   =   c o n t a i n e r . q u e r y S e l e c t o r ( s e l ) ; 
 
                         i f   ( e l e m e n t o )   { 
 
                                 c o n s t   a r i a L a b e l   =   e l e m e n t o . g e t A t t r i b u t e ( ' a r i a - l a b e l ' ) ? . t r i m ( ) ; 
 
                                 i f   ( a r i a L a b e l   & &   a r i a L a b e l . l e n g t h   >   3 )   { 
 
                                         i f   ( ! a r i a L a b e l . t o L o w e r C a s e ( ) . i n c l u d e s ( ' a d v o g a d o ' )   & & 
 
                                                 ! a r i a L a b e l . t o L o w e r C a s e ( ) . i n c l u d e s ( ' t i p o   d o   d o c u m e n t o ' ) )   { 
 
                                                 r e t u r n   a r i a L a b e l ; 
 
                                         } 
 
                                 } 
 
                         } 
 
                 } 
 
               
 
                 / /   F A L L B A C K   r e c . j s   v 1 . 0 :   e x t r a i r   d o   t e x t o   d o   d o c u m e n t o 
 
                 c o n s t   t e x t o D o c   =   t e x t o D o I t e m ( i t e m ) ; 
 
                 c o n s t   m a t c h E m p r e s a   =   t e x t o D o c . m a t c h ( / ^ ( [ ^ - : \ n ] + ) / ) ; 
 
                 i f   ( m a t c h E m p r e s a   & &   m a t c h E m p r e s a [ 1 ] . t r i m ( ) . l e n g t h   >   1 0 )   { 
 
                         c o n s t   n o m e E x t r a i d o   =   m a t c h E m p r e s a [ 1 ] . t r i m ( ) ; 
 
                         i f   ( ! / ^ ( r e c u r s o | o r d i n % r i o | r e v i s t a | r o | r r | d o c u m e n t o ) $ / i . t e s t ( n o m e E x t r a i d o ) )   { 
 
                                 r e t u r n   n o m e E x t r a i d o ; 
 
                         } 
 
                 } 
 
               
 
                 r e t u r n   ' R e c l a m a d a   n % o   i d e n t i f i c a d a ' ; 
 
         } 
 
 
 
         f u n c t i o n   h r e f D o I t e m ( i t e m )   { 
 
                 c o n s t   l i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ t a r g e t = " _ b l a n k " ] ' ) ; 
 
                 r e t u r n   l i n k ? . h r e f   | |   n u l l ; 
 
         } 
 
 
 
         f u n c t i o n   t e x t o D o I t e m ( i t e m )   { 
 
                 c o n s t   p r e v i e w L i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ r o l e = " b u t t o n " ] : n o t ( [ t a r g e t ] ) ' ) 
 
                         | |   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o : n o t ( [ t a r g e t ] ) ' ) ; 
 
                 r e t u r n   ( p r e v i e w L i n k ? . t e x t C o n t e n t   | |   i t e m . t e x t C o n t e n t   | |   ' ' ) . r e p l a c e ( / \ s + / g ,   '   ' ) . t r i m ( ) ; 
 
         } 
 
 
 
         f u n c t i o n   i d D o c u m e n t o D o I t e m ( i t e m )   { 
 
                 / /   E x t r a i   I D   d o   f o r m a t o :   < s p a n   c l a s s = " n g - s t a r - i n s e r t e d " >   -   4 4 7 0 9 e 4 < / s p a n > 
 
                 c o n s t   p r e v i e w L i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ r o l e = " b u t t o n " ] : n o t ( [ t a r g e t ] ) ' ) 
 
                         | |   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o : n o t ( [ t a r g e t ] ) ' ) ; 
 
                 i f   ( ! p r e v i e w L i n k )   r e t u r n   n u l l ; 
 
 
 
                 c o n s t   s p a n s   =   p r e v i e w L i n k . q u e r y S e l e c t o r A l l ( ' s p a n . n g - s t a r - i n s e r t e d ' ) ; 
 
                 f o r   ( l e t   i   =   s p a n s . l e n g t h   -   1 ;   i   > =   0 ;   i - - )   { 
 
                         c o n s t   t e x t o   =   s p a n s [ i ] . t e x t C o n t e n t . t r i m ( ) ; 
 
                         c o n s t   m a t c h   =   t e x t o . m a t c h ( / ^ \ s * - \ s * ( [ a - f 0 - 9 ] { 7 } ) $ / i ) ; 
 
                         i f   ( m a t c h )   r e t u r n   m a t c h [ 1 ] ; 
 
                 } 
 
                 r e t u r n   n u l l ; 
 
         } 
 
 
 
         / /   V a r r e d u r a   %Q%n i c a :   c l a s s i f i c a   t o d o s   o s   i t e m s   d a   t i m e l i n e 
 
         f u n c t i o n   v a r r e r T i m e l i n e ( )   { 
 
                 c o n s t   i t e m s   =   g e t T i m e l i n e I t e m s ( ) ; 
 
                 c o n s t   r e s u l t a d o   =   { 
 
                         s e n t e n c a s :   [ ] , 
 
                         a c o r d a o s :   [ ] , 
 
                         e d i t a i s :   [ ] , 
 
                         r e c u r s o s P a s s i v o :   [ ] ,     / /   R O / R R   +   p o l o   p a s s i v o   +   a n e x o 
 
                         h o n A j J t :   [ ] 
 
                 } ; 
 
 
 
                 i t e m s . f o r E a c h ( ( i t e m ,   i d x )   = >   { 
 
                         c o n s t   t e x t o   =   t e x t o D o I t e m ( i t e m ) ; 
 
                         c o n s t   t e x t o N o r m   =   n o r m a l i z e T e x t ( t e x t o ) ; 
 
                         c o n s t   t i p o D o c   =   t i p o D o c u m e n t o D o I t e m ( i t e m ) ; 
 
                         c o n s t   t i t u l o D o c   =   t i t u l o D o c u m e n t o D o I t e m ( i t e m ) ; 
 
                         c o n s t   d a t a   =   e x t r a c t D a t a F r o m I t e m ( i t e m ) ; 
 
                         c o n s t   h r e f   =   h r e f D o I t e m ( i t e m ) ; 
 
 
 
                         / /   B A S E :   A p e n a s   d a d o s   e s s e n c i a i s   ( S E M   e l e m e n t :   i t e m   p a r a   e v i t a r   v a z a m e n t o   D O M ) 
 
                         c o n s t   b a s e   =   { 
 
                                 i d x , 
 
                                 t e x t o :   t e x t o . s u b s t r i n g ( 0 ,   3 0 0 ) ,   / /   L i m i t a r   t a m a n h o   d o   t e x t o 
 
                                 d a t a , 
 
                                 h r e f 
 
                         } ; 
 
 
 
                         / /   S e n t e n % a 
 
                         i f   ( t e x t o N o r m . i n c l u d e s ( ' s e n t e n c a ' )   | |   t e x t o N o r m . i n c l u d e s ( ' s e n t e n % a ' ) )   { 
 
                                 r e s u l t a d o . s e n t e n c a s . p u s h ( {   . . . b a s e ,   t i p o :   ' s e n t e n c a '   } ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         / /   A c %%r d % o   -   C A P T U R A   I D 
 
                         i f   ( t e x t o N o r m . i n c l u d e s ( ' a c o r d a o ' )   & &   ! t e x t o N o r m . i n c l u d e s ( ' i n t i m a ' ) )   { 
 
                                 c o n s t   i d D o c   =   i d D o c u m e n t o D o I t e m ( i t e m ) ; 
 
                                 r e s u l t a d o . a c o r d a o s . p u s h ( {   . . . b a s e ,   i d :   i d D o c ,   t i p o :   ' a c o r d a o '   } ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         / /   R e c u r s o   O r d i n % r i o   /   R e c u r s o   d e   R e v i s t a   ( p o l o   p a s s i v o   +   a n e x o ) 
 
                         i f   ( ( t i p o D o c   = = =   ' r e c u r s o   o r d i n a r i o '   | |   t i p o D o c   = = =   ' r e c u r s o   d e   r e v i s t a ' 
 
                                 | |   t i p o D o c . i n c l u d e s ( ' r e c u r s o   o r d i n a r i o ' )   | |   t i p o D o c . i n c l u d e s ( ' r e c u r s o   d e   r e v i s t a ' ) ) 
 
                                 & &   i s P o l o P a s s i v o N o I t e m ( i t e m )   & &   h a s A n e x o N o I t e m ( i t e m ) )   { 
 
                                 c o n s t   t i p o R e c   =   t i p o D o c . i n c l u d e s ( ' r e v i s t a ' )   ?   ' R R '   :   ' R O ' ; 
 
                                 c o n s t   d e p o s i t a n t e   =   n o m e P a s s i v o D o I t e m ( i t e m ) ; 
 
                                 r e s u l t a d o . r e c u r s o s P a s s i v o . p u s h ( {   . . . b a s e ,   t i p o R e c ,   d e p o s i t a n t e ,   _ i t e m R e f :   i t e m   } ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         / /   H o n o r % r i o s   P e r i c i a i s   A J - J T   -   C A P T U R A   I D 
 
                         i f   ( / p e r i c [ i a ] * . * a j [ \ s - ] * j t / i . t e s t ( t i t u l o D o c )   | |   / p e r i c [ i a ] * . * a j [ \ s - ] * j t / i . t e s t ( t e x t o ) )   { 
 
                                 c o n s t   i d D o c   =   i d D o c u m e n t o D o I t e m ( i t e m ) ; 
 
                                 r e s u l t a d o . h o n A j J t . p u s h ( {   . . . b a s e ,   i d :   i d D o c ,   t i p o :   ' h o n _ a j j t '   } ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         / /   E d i t a l 
 
                         i f   ( t e x t o N o r m . i n c l u d e s ( ' e d i t a l ' ) )   { 
 
                                 r e s u l t a d o . e d i t a i s . p u s h ( {   . . . b a s e ,   t i p o :   ' e d i t a l '   } ) ; 
 
                         } 
 
                 } ) ; 
 
 
 
                 / /   S e n t e n % a   a l v o   =   m a i s   a n t i g a   ( %Q%l t i m a   n o   a r r a y ,   p o i s   t i m e l i n e   %   d e s c ) 
 
                 r e t u r n   r e s u l t a d o ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   E X T R A % % O   V I A   H T M L   O R I G I N A L 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 
 
         / /   A b r e   o   d o c u m e n t o   i n l i n e   ( c l i c a   n o   p r e v i e w   l i n k ) 
 
         f u n c t i o n   a b r i r D o c u m e n t o I n l i n e ( i t e m )   { 
 
                 c o n s t   p r e v i e w L i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ a c c e s s k e y = " v " ] : n o t ( [ t a r g e t ] ) ' ) 
 
                         | |   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ r o l e = " b u t t o n " ] : n o t ( [ t a r g e t ] ) ' ) 
 
                         | |   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o : n o t ( [ t a r g e t ] ) ' ) ; 
 
                 i f   ( p r e v i e w L i n k )   { 
 
                         t r y   {   p r e v i e w L i n k . d i s p a t c h E v e n t ( n e w   M o u s e E v e n t ( ' c l i c k ' ,   {   b u b b l e s :   t r u e ,   c a n c e l a b l e :   t r u e   } ) ) ;   } 
 
                         c a t c h   ( _ )   {   t r y   {   p r e v i e w L i n k . c l i c k ( ) ;   }   c a t c h   ( _ 2 )   {   }   } 
 
                 } 
 
         } 
 
 
 
         / /   R e c a p t u r a   e l e m e n t o   d a   t i m e l i n e   p e l o   h r e f   ( e v i t a   g u a r d a r   r e f e r % n c i a s   D O M ) 
 
         f u n c t i o n   e n c o n t r a r I t e m T i m e l i n e ( h r e f )   { 
 
                 i f   ( ! h r e f )   r e t u r n   n u l l ; 
 
                 c o n s t   i t e m s   =   g e t T i m e l i n e I t e m s ( ) ; 
 
                 f o r   ( c o n s t   i t e m   o f   i t e m s )   { 
 
                         c o n s t   l i n k   =   i t e m . q u e r y S e l e c t o r ( ' a . t l - d o c u m e n t o [ t a r g e t = " _ b l a n k " ] ' ) ; 
 
                         i f   ( l i n k   & &   l i n k . h r e f   = = =   h r e f )   r e t u r n   i t e m ; 
 
                 } 
 
                 r e t u r n   n u l l ; 
 
         } 
 
 
 
         / /   = = = = = = = = = =   I N T E G R A D O   D E   r e c . j s   v 1 . 0   = = = = = = = = = = 
 
       
 
         / /   C l a s s i f i c a % % o   p o r   t i p o   d e   a n e x o 
 
         f u n c t i o n   c l a s s i f i c a r A n e x o ( t e x t o A n e x o )   { 
 
                 c o n s t   t   =   t e x t o A n e x o . t o L o w e r C a s e ( ) ; 
 
                 i f   ( / d e p %%s i t o | d e p o s i t o | p r e p a r o / . t e s t ( t ) )   r e t u r n   {   t i p o :   ' D e p %%s i t o ' ,   o r d e m :   1   } ; 
 
                 i f   ( / g a r a n t i a | s e g u r o | s u s e p / . t e s t ( t ) )   r e t u r n   {   t i p o :   ' G a r a n t i a ' ,   o r d e m :   2   } ; 
 
                 i f   ( / g r u | c u s t a s / . t e s t ( t ) )   r e t u r n   {   t i p o :   ' C u s t a s ' ,   o r d e m :   3   } ; 
 
                 r e t u r n   {   t i p o :   ' A n e x o ' ,   o r d e m :   4   } ; 
 
         } 
 
 
 
         / /   E x p a n d e   a n e x o s   e   r e t o r n a   l i s t a   e s t r u t u r a d a 
 
         a s y n c   f u n c t i o n   e x t r a i r A n e x o s D o I t e m ( i t e m )   { 
 
                 c o n s t   a n e x o s   =   [ ] ; 
 
                 t r y   { 
 
                         c o n s t   a n e x o s R o o t   =   i t e m . q u e r y S e l e c t o r ( ' p j e - t i m e l i n e - a n e x o s ' ) ; 
 
                         i f   ( ! a n e x o s R o o t )   r e t u r n   a n e x o s ; 
 
                       
 
                         c o n s t   t o g g l e   =   a n e x o s R o o t . q u e r y S e l e c t o r ( ' d i v [ n a m e = " m o s t r a r O u O c u l t a r A n e x o s " ] ' ) ; 
 
                         l e t   a n e x o L i n k s   =   a n e x o s R o o t . q u e r y S e l e c t o r A l l ( ' a . t l - d o c u m e n t o [ i d ^ = " a n e x o _ " ] ' ) ; 
 
                       
 
                         i f   ( ( ! a n e x o L i n k s   | |   a n e x o L i n k s . l e n g t h   = = =   0 )   & &   t o g g l e )   { 
 
                                 t r y   {   t o g g l e . d i s p a t c h E v e n t ( n e w   M o u s e E v e n t ( ' c l i c k ' ,   {   b u b b l e s :   t r u e   } ) ) ;   }   c a t c h ( e )   { } 
 
                                 a w a i t   s l e e p ( 3 5 0 ) ; 
 
                                 a n e x o L i n k s   =   a n e x o s R o o t . q u e r y S e l e c t o r A l l ( ' a . t l - d o c u m e n t o [ i d ^ = " a n e x o _ " ] ' ) ; 
 
                         } 
 
                       
 
                         i f   ( a n e x o L i n k s   & &   a n e x o L i n k s . l e n g t h )   { 
 
                                 A r r a y . f r o m ( a n e x o L i n k s ) . f o r E a c h ( a n e x o   = >   { 
 
                                         c o n s t   t e x t o   =   ( a n e x o . t e x t C o n t e n t   | |   ' ' ) . t r i m ( ) ; 
 
                                         l e t   i d   =   ' ' ; 
 
                                         c o n s t   m a t c h   =   t e x t o . m a t c h ( / \ s - \ s ( [ a - f 0 - 9 ] { 7 } ) \ s * $ / i ) ; 
 
                                         i f   ( m a t c h )   { 
 
                                                 i d   =   m a t c h [ 1 ] ; 
 
                                         }   e l s e   { 
 
                                                 i d   =   a n e x o . i d   | |   a n e x o . g e t A t t r i b u t e ( ' i d ' )   | |   ' ' ; 
 
                                         } 
 
                                         c o n s t   {   t i p o ,   o r d e m   }   =   c l a s s i f i c a r A n e x o ( t e x t o ) ; 
 
                                         a n e x o s . p u s h ( {   t e x t o ,   i d ,   t i p o ,   o r d e m ,   e l e m e n t o :   a n e x o   } ) ; 
 
                                 } ) ; 
 
                                 a n e x o s . s o r t ( ( a ,   b )   = >   a . o r d e m   -   b . o r d e m ) ; 
 
                         } 
 
                 }   c a t c h   ( e r r o r )   { 
 
                         e r r ( ' E r r o   a o   e x t r a i r   a n e x o s : ' ,   e r r o r ) ; 
 
                 } 
 
                 r e t u r n   a n e x o s ; 
 
         } 
 
 
 
         / /   E x p a n d e   o   t o g g l e   d e   a n e x o s   s e   n % o   e s t i v e r   e x p a n d i d o 
 
         a s y n c   f u n c t i o n   e x p a n d i r A n e x o s ( c o n t a i n e r )   { 
 
                 t r y   { 
 
                         c o n s t   a n e x o s R o o t   =   c o n t a i n e r . q u e r y S e l e c t o r ( ' p j e - t i m e l i n e - a n e x o s ' ) ; 
 
                         i f   ( ! a n e x o s R o o t )   r e t u r n   f a l s e ; 
 
                       
 
                         c o n s t   t o g g l e   =   a n e x o s R o o t . q u e r y S e l e c t o r ( ' d i v [ n a m e = " m o s t r a r O u O c u l t a r A n e x o s " ] ' ) ; 
 
                         i f   ( ! t o g g l e )   r e t u r n   f a l s e ; 
 
                       
 
                         c o n s t   j a E x p a n d i d o   =   t o g g l e . g e t A t t r i b u t e ( ' a r i a - p r e s s e d ' )   = = =   ' t r u e ' ; 
 
                         i f   ( j a E x p a n d i d o )   r e t u r n   t r u e ; 
 
                       
 
                         t o g g l e . c l i c k ( ) ; 
 
                         a w a i t   s l e e p ( 4 0 0 ) ; 
 
                         r e t u r n   t r u e ; 
 
                 }   c a t c h   ( e r r o r )   { 
 
                         e r r ( ' E r r o   a o   e x p a n d i r   a n e x o s : ' ,   e r r o r ) ; 
 
                         r e t u r n   f a l s e ; 
 
                 } 
 
         } 
 
 
 
         / /   D e s t a c a   e l e m e n t o   n a   t i m e l i n e   ( r e c e b e   h r e f ,   l o c a l i z a   e   a p l i c a   v i s u a l ) 
 
         f u n c t i o n   d e s t a c a r E l e m e n t o N a T i m e l i n e ( h r e f )   { 
 
                 c o n s t   c o n t a i n e r   =   e n c o n t r a r I t e m T i m e l i n e ( h r e f ) ; 
 
                 i f   ( ! c o n t a i n e r )   { 
 
                         w a r n ( ' E l e m e n t o   n % o   e n c o n t r a d o   p a r a   h r e f : ' ,   h r e f ) ; 
 
                         r e t u r n ; 
 
                 } 
 
                 t r y   { 
 
                         c o n t a i n e r . s c r o l l I n t o V i e w ( {   b e h a v i o r :   ' s m o o t h ' ,   b l o c k :   ' c e n t e r '   } ) ; 
 
                       
 
                         c o n s t   o r i g i n a l B o r d e r   =   c o n t a i n e r . s t y l e . b o r d e r ; 
 
                         c o n s t   o r i g i n a l B a c k g r o u n d   =   c o n t a i n e r . s t y l e . b a c k g r o u n d ; 
 
                         c o n s t   o r i g i n a l T r a n s i t i o n   =   c o n t a i n e r . s t y l e . t r a n s i t i o n ; 
 
                       
 
                         c o n t a i n e r . s t y l e . t r a n s i t i o n   =   ' a l l   0 . 3 s   e a s e ' ; 
 
                         c o n t a i n e r . s t y l e . b o r d e r   =   ' 2 p x   s o l i d   # f b b f 2 4 ' ; 
 
                         c o n t a i n e r . s t y l e . b a c k g r o u n d   =   ' # f f f b e b ' ; 
 
                       
 
                         / /   E x p a n d i r   a n e x o s   a p %%s   s c r o l l   c o m p l e t a r 
 
                         s e t T i m e o u t ( a s y n c   ( )   = >   {   a w a i t   e x p a n d i r A n e x o s ( c o n t a i n e r ) ;   } ,   5 0 0 ) ; 
 
                       
 
                         / /   R e m o v e r   d e s t a q u e   a p %%s   3 s 
 
                         s e t T i m e o u t ( ( )   = >   { 
 
                                 c o n t a i n e r . s t y l e . t r a n s i t i o n   =   ' a l l   0 . 5 s   e a s e ' ; 
 
                                 c o n t a i n e r . s t y l e . b o r d e r   =   o r i g i n a l B o r d e r ; 
 
                                 c o n t a i n e r . s t y l e . b a c k g r o u n d   =   o r i g i n a l B a c k g r o u n d ; 
 
                                 s e t T i m e o u t ( ( )   = >   {   c o n t a i n e r . s t y l e . t r a n s i t i o n   =   o r i g i n a l T r a n s i t i o n ;   } ,   5 0 0 ) ; 
 
                         } ,   3 0 0 0 ) ; 
 
                 }   c a t c h   ( e r r o r )   { 
 
                         e r r ( ' E r r o   a o   d e s t a c a r   e l e m e n t o : ' ,   e r r o r ) ; 
 
                 } 
 
         } 
 
 
 
         / /   A b r e   d o c u m e n t o   i n l i n e   v i a   h r e f   ( r e c a p t u r a   e l e m e n t o   d i n a m i c a m e n t e ) 
 
         f u n c t i o n   a b r i r D o c u m e n t o I n l i n e V i a H r e f ( h r e f )   { 
 
                 c o n s t   i t e m   =   e n c o n t r a r I t e m T i m e l i n e ( h r e f ) ; 
 
                 i f   ( ! i t e m )   r e t u r n   f a l s e ; 
 
                 a b r i r D o c u m e n t o I n l i n e ( i t e m ) ; 
 
                 r e t u r n   t r u e ; 
 
         } 
 
 
 
         / /   C l i c a   e m   " V i s u a l i z a r   H T M L   o r i g i n a l "   e   l %   # p r e v i e w M o d e l o D o c u m e n t o 
 
         a s y n c   f u n c t i o n   l e r H t m l O r i g i n a l ( t i m e o u t M s   =   5 0 0 0 ,   a b o r t S i g n a l   =   n u l l )   { 
 
                 c o n s t   s t a r t e d   =   D a t e . n o w ( ) ; 
 
 
 
                 / /   1 .   E s p e r a   o   b o t % o   a p a r e c e r   ( c o m   s u p o r t e   a   c a n c e l a m e n t o ) 
 
                 l e t   h t m l B t n   =   n u l l ; 
 
                 w h i l e   ( ( D a t e . n o w ( )   -   s t a r t e d )   <   t i m e o u t M s )   { 
 
                         i f   ( a b o r t S i g n a l ? . a b o r t e d )   { 
 
                                 c o n s o l e . l o g ( ' [ h c a l c ]   l e r H t m l O r i g i n a l   c a n c e l a d o   ( a b o r t e d ) ' ) ; 
 
                                 r e t u r n   n u l l ; 
 
                         } 
 
                         h t m l B t n   =   d o c u m e n t . q u e r y S e l e c t o r ( ' b u t t o n [ a r i a - l a b e l = " V i s u a l i z a r   H T M L   o r i g i n a l " ] ' ) ; 
 
                         i f   ( h t m l B t n )   b r e a k ; 
 
                         a w a i t   s l e e p ( 1 5 0 ) ;   / /   R e d u z i d o   d e   2 0 0 m s   p a r a   1 5 0 m s 
 
                 } 
 
                 i f   ( ! h t m l B t n )   r e t u r n   n u l l ; 
 
 
 
                 h t m l B t n . c l i c k ( ) ; 
 
 
 
                 / /   2 .   E s p e r a   o   c o n t e %Q%d o   c a r r e g a r   ( c o m   s u p o r t e   a   c a n c e l a m e n t o ) 
 
                 l e t   p r e v i e w E l   =   n u l l ; 
 
                 c o n s t   s t a r t e d 2   =   D a t e . n o w ( ) ; 
 
                 w h i l e   ( ( D a t e . n o w ( )   -   s t a r t e d 2 )   <   t i m e o u t M s )   { 
 
                         i f   ( a b o r t S i g n a l ? . a b o r t e d )   { 
 
                                 c o n s o l e . l o g ( ' [ h c a l c ]   l e r H t m l O r i g i n a l   c a n c e l a d o   ( a b o r t e d ) ' ) ; 
 
                                 r e t u r n   n u l l ; 
 
                         } 
 
                         p r e v i e w E l   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' p r e v i e w M o d e l o D o c u m e n t o ' ) ; 
 
                         i f   ( p r e v i e w E l   & &   ( p r e v i e w E l . i n n e r T e x t   | |   ' ' ) . t r i m ( ) . l e n g t h   >   2 0 0 )   b r e a k ; 
 
                         a w a i t   s l e e p ( 1 5 0 ) ;   / /   R e d u z i d o   d e   2 0 0 m s   p a r a   1 5 0 m s 
 
                 } 
 
 
 
                 c o n s t   t e x t o   =   ( p r e v i e w E l ? . i n n e r T e x t   | |   ' ' ) . t r i m ( ) ; 
 
                 c o n s t   h t m l   =   ( p r e v i e w E l ? . i n n e r H T M L   | |   ' ' ) . t r i m ( ) ; 
 
                 r e t u r n   t e x t o . l e n g t h   >   2 0 0   ?   {   t e x t o ,   h t m l   }   :   n u l l ; 
 
         } 
 
 
 
         / /   F e c h a   o   m o d a l / v i e w e r   a t u a l   ( s e   h o u v e r ) 
 
         f u n c t i o n   f e c h a r V i e w e r ( )   { 
 
                 / /   T e n t a   f e c h a r   o   m o d a l   d e   p r e v i e w 
 
                 c o n s t   c l o s e B t n s   =   d o c u m e n t . q u e r y S e l e c t o r A l l ( 
 
                         ' b u t t o n [ a r i a - l a b e l = " F e c h a r " ] ,   . m a t - d i a l o g - c l o s e ,   m a t - d i a l o g - c o n t a i n e r   b u t t o n . c l o s e ,   . c d k - o v e r l a y - b a c k d r o p ' 
 
                 ) ; 
 
                 c l o s e B t n s . f o r E a c h ( b   = >   {   t r y   {   b . c l i c k ( ) ;   }   c a t c h   ( _ )   {   }   } ) ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   E X T R A % % O   D E   D A D O S   D A   S E N T E N % A 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         f u n c t i o n   e x t r a i r D a d o s S e n t e n c a ( t e x t o )   { 
 
                 c o n s t   r e s u l t   =   { 
 
                         c u s t a s :   n u l l , 
 
                         h s u s p :   f a l s e , 
 
                         t r t e n g :   f a l s e , 
 
                         t r t m e d :   f a l s e , 
 
                         r e s p o n s a b i l i d a d e :   n u l l ,       / /   ' s u b s i d i a r i a '   |   ' s o l i d a r i a '   |   n u l l 
 
                         h o n o r a r i o s P e r i c i a i s :   [ ]         / /   {   v a l o r ,   t r t   } 
 
                 } ; 
 
 
 
                 / /   C u s t a s :   p a d r % o   a m p l o   c o m   f l e x i b i l i d a d e   p a r a   " m % n i m o " ,   " m % x i m o " ,   " t o t a l " ,   e t c . 
 
                 / /   A c e i t a :   " n o   i m p o r t e   [ m % n i m o / m % x i m o / t o t a l ]   d e   R $   X ,   c a l c u l a d a s   s o b r e " 
 
                 / /   o u   " C u s t a s ,   p e l a   R e c l a m a d a ,   n o   i m p o r t e   d e   R $   3 0 0 , 0 0 " 
 
                 / /   o u   " C u s t a s   d e   R $   2 0 0 , 0 0 " 
 
                 c o n s t   c u s t a s M a t c h   =   t e x t o . m a t c h ( 
 
                         / n o \ s + i m p o r t e \ s + ( ? : m [ i % ] n i m [ o a ] \ s + | m [ % a ] x i m [ o a ] \ s + | t o t a l \ s + ) ? d e \ s + R \ $ \ s * ( [ \ d . , ] + ) , ? \ s * c a l c u l a d a s \ s + s o b r e / i 
 
                 )   | |   t e x t o . m a t c h ( 
 
                         / [ C c ] u s t a s [ ^ , ] * , \ s * ( ? : p e l a \ s + ) ? [ R r ] e c l a m a d [ a o ] [ ^ , ] * , \ s * n o \ s + i m p o r t e \ s + ( ? : m [ i % ] n i m [ o a ] \ s + | m [ % a ] x i m [ o a ] \ s + | t o t a l \ s + ) ? d e \ s + R \ $ \ s * ( [ \ d . , ] + ) / i 
 
                 )   | |   t e x t o . m a t c h ( 
 
                         / [ C c ] u s t a s [ ^ , ] * d e \ s + R \ $ \ s * ( [ \ d . , ] + ) / i 
 
                 ) ; 
 
                 i f   ( c u s t a s M a t c h )   { 
 
                         / /   R e m o v e   v % r g u l a s / p o n t o s   e x t r a s   n o   f i n a l 
 
                         r e s u l t . c u s t a s   =   c u s t a s M a t c h [ 1 ] . r e p l a c e ( / [ . , ] + $ / ,   ' ' ) ; 
 
                 } 
 
 
 
                 / /   C o n d i % % o   s u s p e n s i v a 
 
                 r e s u l t . h s u s p   =   / o b r i g a [ c % ] [ a % ] o \ s + f i c a r [ a % ] \ s + s o b \ s + c o n d i [ c % ] [ a % ] o \ s + s u s p e n s i v a / i . t e s t ( t e x t o ) ; 
 
 
 
                 / /   P e r % c i a   T R T   e n g e n h a r i a 
 
                 r e s u l t . t r t e n g   =   / h o n o r [ a % ] r i o s \ s + p e r i c i a i s \ s + t [ e % ] c n i c o s . * p a g o s \ s + p e l o \ s + T r i b u n a l / i . t e s t ( t e x t o ) 
 
                         | |   / p a g o s \ s + p e l o \ s + T r i b u n a l \ s + R e g i o n a l . * p e r i c i a i s \ s + t [ e % ] c n i c o s / i . t e s t ( t e x t o ) ; 
 
 
 
                 / /   P e r % c i a   T R T   m % d i c a 
 
                 r e s u l t . t r t m e d   =   / h o n o r [ a % ] r i o s \ s + p e r i c i a i s \ s + m [ e % ] d i c o s . * p a g o s \ s + p e l o \ s + T r i b u n a l / i . t e s t ( t e x t o ) 
 
                         | |   / p a g o s \ s + p e l o \ s + T r i b u n a l \ s + R e g i o n a l . * p e r i c i a i s \ s + m [ e % ] d i c o s / i . t e s t ( t e x t o ) ; 
 
 
 
                 / /   R e s p o n s a b i l i d a d e 
 
                 i f   ( / c o n d e n a r \ s + ( d e \ s + f o r m a \ s + ) ? s u b s i d i [ a % ] r i / i . t e s t ( t e x t o ) )   { 
 
                         r e s u l t . r e s p o n s a b i l i d a d e   =   ' s u b s i d i a r i a ' ; 
 
                 }   e l s e   i f   ( / c o n d e n a r \ s + ( d e \ s + f o r m a \ s + ) ? s o l i d [ a % ] r i / i . t e s t ( t e x t o ) )   { 
 
                         r e s u l t . r e s p o n s a b i l i d a d e   =   ' s o l i d a r i a ' ; 
 
                 } 
 
 
 
                 / /   H o n o r % r i o s   p e r i c i a i s :   b u s c a r   t o d o s   o s   t r e c h o s   c o m   v a l o r   +   s e   %   T R T 
 
                 / /   P a d r % o :   " h o n o r % r i o s   p e r i c i a i s   . . .   e m   R $   8 0 0 , 0 0   . . .   p a g o s   p e l o   T r i b u n a l " 
 
                 c o n s t   r e g e x H o n   =   / h o n o r [ a % ] r i o s \ s + p e r i c i a i s [ ^ . ] * ? R \ $ \ s * ( [ \ d . , ] + ) [ ^ . ] * ? \ . / g i ; 
 
                 l e t   m a t c h ; 
 
                 w h i l e   ( ( m a t c h   =   r e g e x H o n . e x e c ( t e x t o ) )   ! = =   n u l l )   { 
 
                         c o n s t   t r e c h o   =   m a t c h [ 0 ] ; 
 
                         c o n s t   v a l o r   =   m a t c h [ 1 ] ; 
 
                         c o n s t   t r t   =   / p a g o s ? \ s + p e l o \ s + T r i b u n a l / i . t e s t ( t r e c h o ) 
 
                                 | |   / T r i b u n a l \ s + R e g i o n a l / i . t e s t ( t r e c h o ) 
 
                                 | |   / T R T / i . t e s t ( t r e c h o ) ; 
 
                         r e s u l t . h o n o r a r i o s P e r i c i a i s . p u s h ( {   v a l o r ,   t r t   } ) ; 
 
                 } 
 
 
 
                 r e t u r n   r e s u l t ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   C R U Z A M E N T O   A J - J T   %   P E R I T O S 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         a s y n c   f u n c t i o n   b u s c a r A j J t P e r i t o s ( h o n A j J t I t e m s ,   p e r i t o s C o n h e c i m e n t o )   { 
 
                 c o n s t   r e s u l t a d o s   =   [ ] ;   / /   {   n o m e ,   t r t :   t r u e ,   i d A j J t   } 
 
 
 
                 / /   S e t   d e   p e r i t o s   j %   e n c o n t r a d o s        e v i t a   a b r i r   m a i s   d o c s   d e s n e c e s s % r i o s 
 
                 c o n s t   p e r i t o s E n c o n t r a d o s   =   n e w   S e t ( ) ; 
 
 
 
                 f o r   ( c o n s t   a j j t   o f   h o n A j J t I t e m s )   { 
 
                         / /   S e   t o d o s   o s   p e r i t o s   j %   f o r a m   e n c o n t r a d o s ,   p a r a 
 
                         i f   ( p e r i t o s E n c o n t r a d o s . s i z e   > =   p e r i t o s C o n h e c i m e n t o . l e n g t h )   b r e a k ; 
 
 
 
                         / /   A b r e   d o c u m e n t o   v i a   h r e f   ( r e c a p t u r a   e l e m e n t o   d i n a m i c a m e n t e ) 
 
                         i f   ( ! a b r i r D o c u m e n t o I n l i n e V i a H r e f ( a j j t . h r e f ) )   { 
 
                                 c o n s o l e . w a r n ( ' [ p r e p ]   F a l h a   a o   a b r i r   A J - J T : ' ,   a j j t . h r e f ) ; 
 
                                 c o n t i n u e ; 
 
                         } 
 
                         a w a i t   s l e e p ( 6 0 0 ) ; 
 
 
 
                         / /   L %   H T M L   o r i g i n a l 
 
                         c o n s t   r e s H t m l   =   a w a i t   l e r H t m l O r i g i n a l ( 5 0 0 0 ) ; 
 
                         f e c h a r V i e w e r ( ) ; 
 
                         a w a i t   s l e e p ( 3 0 0 ) ; 
 
 
 
                         i f   ( ! r e s H t m l   | |   ! r e s H t m l . t e x t o )   c o n t i n u e ; 
 
 
 
                         c o n s t   t e x t o N o r m   =   n o r m a l i z e T e x t ( r e s H t m l . t e x t o ) ; 
 
 
 
                         / /   P r o c u r a   c a d a   p e r i t o   d e   c o n h e c i m e n t o   n o   t e x t o 
 
                         f o r   ( c o n s t   p e r i t o   o f   p e r i t o s C o n h e c i m e n t o )   { 
 
                                 i f   ( p e r i t o s E n c o n t r a d o s . h a s ( p e r i t o ) )   c o n t i n u e ; 
 
 
 
                                 c o n s t   p e r i t o N o r m   =   n o r m a l i z e T e x t ( p e r i t o ) ; 
 
                                 / /   M a t c h   p a r c i a l :   p r i m e i r o   n o m e   +   %Q%l t i m o   n o m e 
 
                                 c o n s t   p a r t e s   =   p e r i t o N o r m . s p l i t ( / \ s + / ) . f i l t e r ( B o o l e a n ) ; 
 
                                 c o n s t   p r i m e i r o N o m e   =   p a r t e s [ 0 ]   | |   ' ' ; 
 
                                 c o n s t   u l t i m o N o m e   =   p a r t e s . l e n g t h   >   1   ?   p a r t e s [ p a r t e s . l e n g t h   -   1 ]   :   ' ' ; 
 
 
 
                                 c o n s t   f o u n d   =   t e x t o N o r m . i n c l u d e s ( p e r i t o N o r m ) 
 
                                         | |   ( p r i m e i r o N o m e   & &   u l t i m o N o m e   & &   t e x t o N o r m . i n c l u d e s ( p r i m e i r o N o m e )   & &   t e x t o N o r m . i n c l u d e s ( u l t i m o N o m e ) ) ; 
 
 
 
                                 i f   ( f o u n d )   { 
 
                                         / /   U s a r   I D   j %   e x t r a % d o   d a   t i m e l i n e 
 
                                         c o n s t   i d A j J t   =   a j j t . i d   | |   a j j t . t e x t o ; 
 
 
 
                                         r e s u l t a d o s . p u s h ( {   n o m e :   p e r i t o ,   t r t :   t r u e ,   i d A j J t   } ) ; 
 
                                         p e r i t o s E n c o n t r a d o s . a d d ( p e r i t o ) ; 
 
                                 } 
 
                         } 
 
                 } 
 
 
 
                 r e t u r n   r e s u l t a d o s ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   N O T I F I C A % % E S   E D I T A L 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         a s y n c   f u n c t i o n   b u s c a r P a r t e s E d i t a l ( e d i t a i s I t e m s ,   p a s s i v o )   { 
 
                 / /   R e g r a   m a i o r :   s e   h %   a p e n a s   u m a   r e c l a m a d a   e   h %   e d i t a l ,   %   e l a . 
 
                 i f   ( p a s s i v o . l e n g t h   = = =   1 )   { 
 
                         r e t u r n   [ p a s s i v o [ 0 ] . n o m e ] ; 
 
                 } 
 
 
 
                 c o n s t   i n t i m a d a s   =   n e w   S e t ( ) ; 
 
                 c o n s t   r e c l a m a d a s   =   p a s s i v o . m a p ( p   = >   ( {   n o m e :   p . n o m e ,   n o m N o r m :   n o r m a l i z e T e x t ( p . n o m e )   } ) ) ; 
 
 
 
                 f o r   ( c o n s t   e d i t a l   o f   e d i t a i s I t e m s )   { 
 
                         i f   ( i n t i m a d a s . s i z e   > =   p a s s i v o . l e n g t h )   b r e a k ; 
 
 
 
                         / /   A b r e   e d i t a l   v i a   h r e f   ( r e c a p t u r a   e l e m e n t o   d i n a m i c a m e n t e ) 
 
                         i f   ( ! a b r i r D o c u m e n t o I n l i n e V i a H r e f ( e d i t a l . h r e f ) )   { 
 
                                 c o n s o l e . w a r n ( ' [ p r e p ]   F a l h a   a o   a b r i r   e d i t a l : ' ,   e d i t a l . h r e f ) ; 
 
                                 c o n t i n u e ; 
 
                         } 
 
                         a w a i t   s l e e p ( 6 0 0 ) ; 
 
 
 
                         c o n s t   r e s H t m l   =   a w a i t   l e r H t m l O r i g i n a l ( 6 0 0 0 ,   s i g n a l ,   s i g n a l ) ; 
 
                         f e c h a r V i e w e r ( ) ; 
 
                         a w a i t   s l e e p ( 3 0 0 ) ; 
 
 
 
                         i f   ( ! r e s H t m l   | |   ! r e s H t m l . h t m l )   c o n t i n u e ; 
 
 
 
                         c o n s t   h t m l   =   r e s H t m l . h t m l ; 
 
 
 
                         c o n s t   m a t c h C o m e c o   =   h t m l . m a t c h ( / < s t r o n g [ ^ > ] * > \ s * E D I T A L \ s + D . * ? < \ / s t r o n g > / i ) ; 
 
                         c o n s t   m a t c h F i m   =   h t m l . m a t c h ( / < s t r o n g [ ^ > ] * > \ s * \ ( h t t p : \ / \ / p j e \ . t r t s p \ . j u s \ . b r \ / d o c u m e n t o s \ ) \ s * < \ / s t r o n g > / i ) ; 
 
 
 
                         l e t   t e x t o A l v o   =   ' ' ; 
 
 
 
                         i f   ( m a t c h C o m e c o   & &   m a t c h F i m   & &   m a t c h F i m . i n d e x   >   m a t c h C o m e c o . i n d e x )   { 
 
                                 c o n s t   b l o c o H t m l   =   h t m l . s u b s t r i n g ( m a t c h C o m e c o . i n d e x ,   m a t c h F i m . i n d e x   +   m a t c h F i m [ 0 ] . l e n g t h ) ; 
 
                                 c o n s t   d i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                                 d i v . i n n e r H T M L   =   b l o c o H t m l ; 
 
                                 t e x t o A l v o   =   n o r m a l i z e T e x t ( d i v . i n n e r T e x t   | |   d i v . t e x t C o n t e n t   | |   ' ' ) ; 
 
                         }   e l s e   i f   ( m a t c h C o m e c o )   { 
 
                                 c o n s t   b l o c o H t m l   =   h t m l . s u b s t r i n g ( m a t c h C o m e c o . i n d e x ,   m a t c h C o m e c o . i n d e x   +   1 0 0 0 ) ; 
 
                                 c o n s t   d i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                                 d i v . i n n e r H T M L   =   b l o c o H t m l ; 
 
                                 t e x t o A l v o   =   n o r m a l i z e T e x t ( d i v . i n n e r T e x t   | |   d i v . t e x t C o n t e n t   | |   ' ' ) ; 
 
                         }   e l s e   { 
 
                                 t e x t o A l v o   =   n o r m a l i z e T e x t ( r e s H t m l . t e x t o ) ; 
 
                         } 
 
 
 
                         f o r   ( c o n s t   r   o f   r e c l a m a d a s )   { 
 
                                 i f   ( i n t i m a d a s . h a s ( r . n o m e ) )   c o n t i n u e ; 
 
                                 i f   ( t e x t o A l v o . i n c l u d e s ( r . n o m N o r m ) )   { 
 
                                         i n t i m a d a s . a d d ( r . n o m e ) ; 
 
                                 } 
 
                         } 
 
                 } 
 
                 r e t u r n   A r r a y . f r o m ( i n t i m a d a s ) ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   O R Q U E S T R A D O R   P R I N C I P A L 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         a s y n c   f u n c t i o n   e x e c u t a r P r e p ( p a r t e s D a t a ,   p e r i t o s C o n h e c i m e n t o )   { 
 
                 / /   F L A G   A N T I - E X E C U % % O - D U P L A :   P r e v i n e   l o o p s   d e   p o l l i n g   a c u m u l a n d o   t i m e r s 
 
                 i f   ( w i n d o w . h c a l c P r e p R u n n i n g )   { 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]           P r e p   j %   e m   e x e c u % % o ,   i g n o r a n d o   c h a m a d a   d u p l i c a d a ' ) ; 
 
                         r e t u r n ; 
 
                 } 
 
 
 
                 / /   A b o r t a r   p r e p   a n t e r i o r   s e   e x i s t i r 
 
                 i f   ( w i n d o w . h c a l c S t a t e . a b o r t C o n t r o l l e r )   { 
 
                         d b g ( ' [ p r e p ]   A b o r t a n d o   e x e c u % % o   a n t e r i o r   a n t e s   d e   i n i c i a r   n o v a ' ) ; 
 
                         w i n d o w . h c a l c S t a t e . a b o r t C o n t r o l l e r . a b o r t ( ) ; 
 
                 } 
 
 
 
                 / /   C r i a r   n o v o   A b o r t C o n t r o l l e r   p a r a   e s t a   e x e c u % % o 
 
                 w i n d o w . h c a l c S t a t e . a b o r t C o n t r o l l e r   =   n e w   A b o r t C o n t r o l l e r ( ) ; 
 
                 c o n s t   s i g n a l   =   w i n d o w . h c a l c S t a t e . a b o r t C o n t r o l l e r . s i g n a l ; 
 
 
 
                 w i n d o w . h c a l c P r e p R u n n i n g   =   t r u e ; 
 
 
 
                 t r y   { 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]   I n i c i a n d o   p r e p a r a % % o   p r % - o v e r l a y . . . ' ) ; 
 
                         c o n s t   p a r t e s S a f e   =   p a r t e s D a t a   & &   t y p e o f   p a r t e s D a t a   = = =   ' o b j e c t '   ?   p a r t e s D a t a   :   { } ; 
 
 
 
                 / /   R e s u l t a d o   p a d r % o 
 
                 c o n s t   p r e p R e s u l t   =   { 
 
                         s e n t e n c a :   { 
 
                                 d a t a :   n u l l , 
 
                                 h r e f :   n u l l , 
 
                                 c u s t a s :   n u l l , 
 
                                 h s u s p :   f a l s e , 
 
                                 r e s p o n s a b i l i d a d e :   n u l l , 
 
                                 h o n o r a r i o s P e r i c i a i s :   [ ] 
 
                         } , 
 
                         p e r i c i a :   { 
 
                                 t r t e n g :   f a l s e , 
 
                                 t r t m e d :   f a l s e , 
 
                                 p e r i t o s C o m A j J t :   [ ] 
 
                         } , 
 
                         a c o r d a o s :   [ ] , 
 
                         d e p o s i t o s :   [ ] , 
 
                         e d i t a i s :   [ ] , 
 
                         p a r t e s I n t i m a d a s E d i t a l :   [ ] 
 
                 } ; 
 
 
 
                 / /           E T A P A   1 :   V a r r e r   t i m e l i n e   ( s % n c r o n a )         
 
                 c o n s t   t i m e l i n e   =   v a r r e r T i m e l i n e ( ) ; 
 
                 c o n s o l e . l o g ( ' [ p r e p . j s ]   T i m e l i n e   v a r r i d a : ' ,   { 
 
                         s e n t e n c a s :   t i m e l i n e . s e n t e n c a s . l e n g t h , 
 
                         a c o r d a o s :   t i m e l i n e . a c o r d a o s . l e n g t h , 
 
                         e d i t a i s :   t i m e l i n e . e d i t a i s . l e n g t h , 
 
                         r e c u r s o s P a s s i v o :   t i m e l i n e . r e c u r s o s P a s s i v o . l e n g t h , 
 
                         h o n A j J t :   t i m e l i n e . h o n A j J t . l e n g t h 
 
                 } ) ; 
 
 
 
                 / /           E T A P A   1 . 5 :   E n r i q u e c e r   r e c u r s o s   c o m   a n e x o s   ( i n t e g r a d o   r e c . j s )         
 
                 i f   ( t i m e l i n e . r e c u r s o s P a s s i v o . l e n g t h   >   0 )   { 
 
                         d b g ( ' p r e p ' ,   ' E x t r a i n d o   a n e x o s   d e ' ,   t i m e l i n e . r e c u r s o s P a s s i v o . l e n g t h ,   ' r e c u r s o s . . . ' ) ; 
 
                         f o r   ( c o n s t   r e c   o f   t i m e l i n e . r e c u r s o s P a s s i v o )   { 
 
                                 i f   ( r e c . _ i t e m R e f )   { 
 
                                         r e c . a n e x o s   =   a w a i t   e x t r a i r A n e x o s D o I t e m ( r e c . _ i t e m R e f ) ; 
 
                                         d e l e t e   r e c . _ i t e m R e f ; 
 
                                 }   e l s e   { 
 
                                         r e c . a n e x o s   =   [ ] ; 
 
                                 } 
 
                         } 
 
                         d b g ( ' p r e p ' ,   ' A n e x o s   e x t r a % d o s ' ) ; 
 
                 } 
 
                 / /   G a r a n t i r   l i m p e z a   d e   _ i t e m R e f   m e s m o   s e   n % o   p r o c e s s o u 
 
                 t i m e l i n e . r e c u r s o s P a s s i v o . f o r E a c h ( r   = >   {   d e l e t e   r . _ i t e m R e f ;   } ) ; 
 
 
 
                 / /   M a p e a r   a c %%r d % o s   e   e d i t a i s   p a r a   r e s u l t a d o 
 
                 p r e p R e s u l t . a c o r d a o s   =   t i m e l i n e . a c o r d a o s . m a p ( a   = >   ( {   d a t a :   a . d a t a ,   h r e f :   a . h r e f ,   i d :   a . i d   } ) ) ; 
 
                 p r e p R e s u l t . e d i t a i s   =   t i m e l i n e . e d i t a i s . m a p ( e   = >   ( {   d a t a :   e . d a t a ,   h r e f :   e . h r e f   } ) ) ; 
 
 
 
                 / /   D e p %%s i t o s   r e c u r s a i s   =   r e c u r s o s   p a s s i v o   ( s %%  s e   t e m   a c %%r d % o ) 
 
                 i f   ( t i m e l i n e . a c o r d a o s . l e n g t h   >   0 )   { 
 
                         p r e p R e s u l t . d e p o s i t o s   =   t i m e l i n e . r e c u r s o s P a s s i v o . m a p ( r   = >   ( { 
 
                                 t i p o :   r . t i p o R e c , 
 
                                 t e x t o :   r . t e x t o , 
 
                                 h r e f :   r . h r e f , 
 
                                 d a t a :   r . d a t a , 
 
                                 d e p o s i t a n t e :   r . d e p o s i t a n t e   | |   ' ' , 
 
                                 a n e x o s :   r . a n e x o s   | |   [ ] 
 
                         } ) ) ; 
 
                 } 
 
 
 
                 / /           E T A P A   2 :   A J - J T        s %%  s e   t e m   p e r i t o   d e   c o n h e c i m e n t o         
 
                 / /   O R D E M   I N V E R T I D A :   A J - J T   a n t e s   d e   s e n t e n % a   p a r a   m a n t e r   s e n t e n % a   s e l e c i o n a d a 
 
                 c o n s t   p e r i t o s C o n h   =   A r r a y . i s A r r a y ( p e r i t o s C o n h e c i m e n t o )   ?   p e r i t o s C o n h e c i m e n t o . f i l t e r ( B o o l e a n )   :   [ ] ; 
 
 
 
                 i f   ( p e r i t o s C o n h . l e n g t h   >   0   & &   t i m e l i n e . h o n A j J t . l e n g t h   >   0 )   { 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]   B u s c a n d o   A J - J T   p a r a   p e r i t o s : ' ,   p e r i t o s C o n h ) ; 
 
                         p r e p R e s u l t . p e r i c i a . p e r i t o s C o m A j J t   =   a w a i t   b u s c a r A j J t P e r i t o s ( t i m e l i n e . h o n A j J t ,   p e r i t o s C o n h ) ; 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]   A J - J T   e n c o n t r a d o s : ' ,   p r e p R e s u l t . p e r i c i a . p e r i t o s C o m A j J t ) ; 
 
                 }   e l s e   i f   ( p e r i t o s C o n h . l e n g t h   >   0 )   { 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]   P e r i t o s   d e   c o n h e c i m e n t o   d e t e c t a d o s   m a s   n e n h u m   A J - J T   n a   t i m e l i n e . ' ) ; 
 
                 } 
 
 
 
                 / /           E T A P A   3 :   S e n t e n % a        a b r i r   e   e x t r a i r   t u d o         
 
                 / /   M O V I D O   P A R A   D E P O I S   D E   A J - J T   p a r a   f i c a r   s e l e c i o n a d a   p o r   %Q%l t i m o 
 
                 c o n s t   s e n t e n c a A l v o   =   t i m e l i n e . s e n t e n c a s . l e n g t h   >   0 
 
                         ?   t i m e l i n e . s e n t e n c a s [ t i m e l i n e . s e n t e n c a s . l e n g t h   -   1 ]     / /   m a i s   a n t i g a   ( %Q%l t i m a   n o   a r r a y ) 
 
                         :   n u l l ; 
 
 
 
                 i f   ( s e n t e n c a A l v o )   { 
 
                         p r e p R e s u l t . s e n t e n c a . d a t a   =   s e n t e n c a A l v o . d a t a ; 
 
                         p r e p R e s u l t . s e n t e n c a . h r e f   =   s e n t e n c a A l v o . h r e f ; 
 
 
 
                         / /   A b r i r   d o c u m e n t o   v i a   h r e f   ( r e c a p t u r a   e l e m e n t o   d i n a m i c a m e n t e ) 
 
                         i f   ( ! a b r i r D o c u m e n t o I n l i n e V i a H r e f ( s e n t e n c a A l v o . h r e f ) )   { 
 
                                 c o n s o l e . w a r n ( ' [ p r e p ]   F a l h a   a o   a b r i r   s e n t e n % a : ' ,   s e n t e n c a A l v o . h r e f ) ; 
 
                         }   e l s e   { 
 
                                 a w a i t   s l e e p ( 6 0 0 ) ; 
 
 
 
                                 / /   L e r   H T M L   o r i g i n a l 
 
                                 c o n s t   r e s S e n t   =   a w a i t   l e r H t m l O r i g i n a l ( 6 0 0 0 ,   s i g n a l ) ; 
 
                                 f e c h a r V i e w e r ( ) ; 
 
                                 a w a i t   s l e e p ( 3 0 0 ) ; 
 
 
 
                                 i f   ( r e s S e n t   & &   r e s S e n t . t e x t o )   { 
 
                                         c o n s t   t e x t o S e n t e n c a   =   r e s S e n t . t e x t o ; 
 
                                         c o n s o l e . l o g ( ' [ p r e p . j s ]   S e n t e n % a   l i d a : ' ,   t e x t o S e n t e n c a . l e n g t h ,   ' c h a r s ' ) ; 
 
 
 
                                         c o n s t   d a d o s   =   e x t r a i r D a d o s S e n t e n c a ( t e x t o S e n t e n c a ) ; 
 
                                         p r e p R e s u l t . s e n t e n c a . c u s t a s   =   d a d o s . c u s t a s ; 
 
                                         p r e p R e s u l t . s e n t e n c a . h s u s p   =   d a d o s . h s u s p ; 
 
                                         p r e p R e s u l t . s e n t e n c a . r e s p o n s a b i l i d a d e   =   d a d o s . r e s p o n s a b i l i d a d e ; 
 
                                         p r e p R e s u l t . s e n t e n c a . h o n o r a r i o s P e r i c i a i s   =   d a d o s . h o n o r a r i o s P e r i c i a i s ; 
 
                                         p r e p R e s u l t . p e r i c i a . t r t e n g   =   d a d o s . t r t e n g ; 
 
                                         p r e p R e s u l t . p e r i c i a . t r t m e d   =   d a d o s . t r t m e d ; 
 
                                 }   e l s e   { 
 
                                         c o n s o l e . w a r n ( ' [ p r e p . j s ]   F a l h a   a o   l e r   s e n t e n % a   v i a   H T M L   o r i g i n a l . ' ) ; 
 
                                 } 
 
                         } 
 
                 }   e l s e   { 
 
                         c o n s o l e . w a r n ( ' [ p r e p . j s ]   N e n h u m a   s e n t e n % a   e n c o n t r a d a   n a   t i m e l i n e . ' ) ; 
 
                 } 
 
 
 
                 / /           E T A P A   4 :   E D I T A L        e x t r a i r   p a r t e s   i n t i m a d a s         
 
                 c o n s t   p a s s i v o A r r a y   =   A r r a y . i s A r r a y ( p a r t e s S a f e . p a s s i v o )   ?   p a r t e s S a f e . p a s s i v o   :   [ ] ; 
 
                 i f   ( t i m e l i n e . e d i t a i s . l e n g t h   >   0   & &   p a s s i v o A r r a y . l e n g t h   >   0 )   { 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]   B u s c a n d o   p a r t e s   i n t i m a d a s   n o s   e d i t a i s . . . ' ) ; 
 
                         p r e p R e s u l t . p a r t e s I n t i m a d a s E d i t a l   =   a w a i t   b u s c a r P a r t e s E d i t a l ( t i m e l i n e . e d i t a i s ,   p a s s i v o A r r a y ) ; 
 
                         c o n s o l e . l o g ( ' [ p r e p . j s ]   P a r t e s   i n t i m a d a s   p o r   e d i t a l : ' ,   p r e p R e s u l t . p a r t e s I n t i m a d a s E d i t a l ) ; 
 
                 } 
 
 
 
                 c o n s o l e . l o g ( ' [ p r e p . j s ]   P r e p a r a % % o   c o n c l u % d a : ' ,   p r e p R e s u l t ) ; 
 
 
 
                 / /   D i s p o n i b i l i z a r   g l o b a l m e n t e 
 
                 w i n d o w . h c a l c P r e p R e s u l t   =   p r e p R e s u l t ; 
 
 
 
                 / /   L i b e r a r   f l a g   d e   e x e c u % % o 
 
                 w i n d o w . h c a l c P r e p R u n n i n g   =   f a l s e ; 
 
 
 
                 r e t u r n   p r e p R e s u l t ; 
 
 
 
                 }   c a t c h   ( e r r o r )   { 
 
                         c o n s o l e . e r r o r ( ' [ p r e p . j s ]   E r r o   d u r a n t e   p r e p a r a % % o : ' ,   e r r o r ) ; 
 
                         / /   G a r a n t i r   q u e   f l a g   s e j a   l i b e r a d a   m e s m o   e m   c a s o   d e   e r r o 
 
                         w i n d o w . h c a l c P r e p R u n n i n g   =   f a l s e ; 
 
                         t h r o w   e r r o r ; 
 
                 } 
 
         } 
 
 
 
         / /   E x p o r   p r e p   n o   e s c o p o   g l o b a l   p a r a   i n t e g r a % % o / d e p u r a % % o . 
 
         c o n s t   p r e p G l o b a l O b j   =   t y p e o f   u n s a f e W i n d o w   ! = =   ' u n d e f i n e d '   ?   u n s a f e W i n d o w   :   w i n d o w ; 
 
         p r e p G l o b a l O b j . e x e c u t a r P r e p   =   e x e c u t a r P r e p ; 
 
         i f   ( p r e p G l o b a l O b j   ! = =   w i n d o w )   { 
 
                 w i n d o w . e x e c u t a r P r e p   =   e x e c u t a r P r e p ; 
 
         } 
 
         w i n d o w . d e s t a c a r E l e m e n t o N a T i m e l i n e   =   d e s t a c a r E l e m e n t o N a T i m e l i n e ; 
 
         w i n d o w . e n c o n t r a r I t e m T i m e l i n e               =   e n c o n t r a r I t e m T i m e l i n e ; 
 
         w i n d o w . e x p a n d i r A n e x o s                             =   e x p a n d i r A n e x o s ; 
 
 
 
         / /   F i m   p r e p   ( a g o r a   g l o b a l   n o   e s c o p o   d o   a r q u i v o ) 
 
 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   E S T R A T % G I A   4 :   L A Z Y   I N I T        F a s e   A   ( l e v e ) 
 
         / /   I n j e t a   a p e n a s   o   b o t % o   ( ~ 2 0 0   b y t e s   C S S ) .   T o d o   o   o v e r l a y   %   c r i a d o   n o   p r i m e i r o   c l i q u e . 
 
 
 
         / /   w i n d o w . e x e c u t a r P r e p   j a   e x p o s t a   n o   c o r p o   a c i m a 
 
 } ) ( ) ; 
 
 

// ── hcalc-pdf.js ──────────────────────────────────
( f u n c t i o n ( )   { 
 
         ' u s e   s t r i c t ' ; 
 
         c o n s t   H C A L C _ D E B U G   =   f a l s e ; 
 
         c o n s t   d b g     =   ( . . . a r g s )   = >   {   i f   ( H C A L C _ D E B U G )   c o n s o l e . l o g ( ' [ h c a l c ] ' ,   . . . a r g s ) ;   } ; 
 
         c o n s t   w a r n   =   ( . . . a r g s )   = >   c o n s o l e . w a r n ( ' [ h c a l c ] ' ,   . . . a r g s ) ; 
 
         c o n s t   e r r     =   ( . . . a r g s )   = >   c o n s o l e . e r r o r ( ' [ h c a l c ] ' ,   . . . a r g s ) ; 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   E X T R A % % O   D E   P L A N I L H A   P J E - C A L C   ( F A S E   1 ) 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   P D F . j s   c a r r e g a d o   v i a   @ r e q u i r e   ( s %%  e x e c u t a   s e   a b r i r   p % g i n a   P J e ) 
 
         / /   W o r k e r   c o n f i g u r a d o   s o b   d e m a n d a   ( p r i m e i r a   v e z   q u e   p r o c e s s a r   P D F ) 
 
 
 
         f u n c t i o n   c a r r e g a r P D F J S S e N e c e s s a r i o ( )   { 
 
                 / /   E s t r a t % g i a   3 :   P D F . j s   c a r r e g a   d e n t r o   d o   W o r k e r   v i a   i m p o r t S c r i p t s . 
 
                 / /   M a i n   t h r e a d   n % o   p r e c i s a   d o   p d f j s L i b        s e m p r e   r e t o r n a   t r u e . 
 
                 r e t u r n   t r u e ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   V A L I D A % % O   D E   D A D O S   E X T R A % D O S   ( F A S E   2 ) 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
       
 
         / /   F u n % % o   u t i l i t % r i a   p a r a   n o r m a l i z a r   n o m e s   ( c o m p a r a % % o   d e   p e r i t o s / a d v o g a d o s ) 
 
         f u n c t i o n   n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( n o m e )   { 
 
                 i f   ( ! n o m e )   r e t u r n   ' ' ; 
 
                 / /   R e m o v e   a c e n t o s ,   p o n t o s ,   t r a n s f o r m a   e m   m a i %Q%s c u l a s   p a r a   c o m p a r a % % o 
 
                 r e t u r n   n o m e . n o r m a l i z e ( ' N F D ' ) 
 
                                       . r e p l a c e ( / [ \ u 0 3 0 0 - \ u 0 3 6 f ] / g ,   ' ' ) 
 
                                       . r e p l a c e ( / [ . ] / g ,   ' ' ) 
 
                                       . t o U p p e r C a s e ( ) 
 
                                       . t r i m ( ) ; 
 
         } 
 
       
 
         f u n c t i o n   v a l i d a r V a l o r ( v a l o r )   { 
 
                 i f   ( ! v a l o r   | |   v a l o r   = = =   ' 0 , 0 0 ' )   r e t u r n   f a l s e ; 
 
                 / /   F o r m a t o   v % l i d o :   1 . 2 3 4 , 5 6   o u   1 2 3 , 4 5   o u   1 , 2 3 
 
                 c o n s t   r e g e x   =   / ^ \ d { 1 , 3 } ( \ . \ d { 3 } ) * , \ d { 2 } $ / ; 
 
                 r e t u r n   r e g e x . t e s t ( v a l o r ) ; 
 
         } 
 
 
 
         f u n c t i o n   v a l i d a r D a t a ( d a t a )   { 
 
                 i f   ( ! d a t a )   r e t u r n   f a l s e ; 
 
                 c o n s t   m a t c h   =   d a t a . m a t c h ( / ^ ( \ d { 2 } ) \ / ( \ d { 2 } ) \ / ( \ d { 4 } ) $ / ) ; 
 
                 i f   ( ! m a t c h )   r e t u r n   f a l s e ; 
 
               
 
                 c o n s t   d i a   =   p a r s e I n t ( m a t c h [ 1 ] ) ; 
 
                 c o n s t   m e s   =   p a r s e I n t ( m a t c h [ 2 ] ) ; 
 
                 c o n s t   a n o   =   p a r s e I n t ( m a t c h [ 3 ] ) ; 
 
               
 
                 / /   V a l i d a % % e s   b % s i c a s 
 
                 i f   ( m e s   <   1   | |   m e s   >   1 2 )   r e t u r n   f a l s e ; 
 
                 i f   ( d i a   <   1   | |   d i a   >   3 1 )   r e t u r n   f a l s e ; 
 
                 i f   ( a n o   <   2 0 2 0   | |   a n o   >   2 0 3 0 )   r e t u r n   f a l s e ;   / /   R a n g e   r a z o % v e l   p a r a   p l a n i l h a s 
 
               
 
                 r e t u r n   t r u e ; 
 
         } 
 
 
 
         f u n c t i o n   c a l c u l a r Q u a l i d a d e E x t r a c a o ( d a d o s )   { 
 
                 c o n s t   c a m p o s   =   [ 
 
                         {   n o m e :   ' i d P l a n i l h a ' ,   l a b e l :   ' I D ' ,   v a l i d a r :   ( v )   = >   v   & &   v . l e n g t h   >   3   } , 
 
                         {   n o m e :   ' v e r b a s ' ,   l a b e l :   ' C r % d i t o ' ,   v a l i d a r :   v a l i d a r V a l o r   } , 
 
                         {   n o m e :   ' f g t s ' ,   l a b e l :   ' F G T S ' ,   v a l i d a r :   ( v )   = >   ! v   | |   v   = = =   ' 0 , 0 0 '   | |   v a l i d a r V a l o r ( v )   } ,   / /   O p c i o n a l 
 
                         {   n o m e :   ' i n s s T o t a l ' ,   l a b e l :   ' I N S S   T o t a l ' ,   v a l i d a r :   v a l i d a r V a l o r   } , 
 
                         {   n o m e :   ' i n s s A u t o r ' ,   l a b e l :   ' I N S S   R e c ' ,   v a l i d a r :   ( v )   = >   ! v   | |   v   = = =   ' 0 , 0 0 '   | |   v a l i d a r V a l o r ( v )   } ,   / /   O p c i o n a l 
 
                         {   n o m e :   ' c u s t a s ' ,   l a b e l :   ' C u s t a s ' ,   v a l i d a r :   ( v )   = >   ! v   | |   v   = = =   ' 0 , 0 0 '   | |   v a l i d a r V a l o r ( v )   } ,   / /   O p c i o n a l 
 
                         {   n o m e :   ' d a t a A t u a l i z a c a o ' ,   l a b e l :   ' D a t a ' ,   v a l i d a r :   v a l i d a r D a t a   } 
 
                 ] ; 
 
               
 
                 l e t   e x t r a i d o s   =   0 ; 
 
                 l e t   v a l i d o s   =   0 ; 
 
                 c o n s t   f a l t a n d o   =   [ ] ; 
 
                 c o n s t   i n v a l i d o s   =   [ ] ; 
 
               
 
                 c a m p o s . f o r E a c h ( c a m p o   = >   { 
 
                         c o n s t   v a l o r   =   d a d o s [ c a m p o . n o m e ] ; 
 
                         c o n s t   t e m V a l o r   =   v a l o r   & &   v a l o r   ! = =   ' '   & &   v a l o r   ! = =   ' 0 , 0 0 ' ; 
 
                       
 
                         i f   ( t e m V a l o r )   { 
 
                                 e x t r a i d o s + + ; 
 
                                 i f   ( c a m p o . v a l i d a r ( v a l o r ) )   { 
 
                                         v a l i d o s + + ; 
 
                                 }   e l s e   { 
 
                                         i n v a l i d o s . p u s h ( {   c a m p o :   c a m p o . l a b e l ,   v a l o r   } ) ; 
 
                                 } 
 
                         }   e l s e   i f   ( c a m p o . n o m e   = = =   ' v e r b a s '   | |   c a m p o . n o m e   = = =   ' i d P l a n i l h a '   | |   c a m p o . n o m e   = = =   ' d a t a A t u a l i z a c a o ' )   { 
 
                                 / /   C a m p o s   o b r i g a t %%r i o s 
 
                                 f a l t a n d o . p u s h ( c a m p o . l a b e l ) ; 
 
                         } 
 
                 } ) ; 
 
               
 
                 r e t u r n   { 
 
                         p e r c e n t u a l :   M a t h . r o u n d ( ( v a l i d o s   /   c a m p o s . l e n g t h )   *   1 0 0 ) , 
 
                         e x t r a i d o s , 
 
                         v a l i d o s , 
 
                         t o t a l :   c a m p o s . l e n g t h , 
 
                         f a l t a n d o , 
 
                         i n v a l i d o s 
 
                 } ; 
 
         } 
 
 
 
         f u n c t i o n   v a l i d a r D a d o s E x t r a i d o s ( d a d o s )   { 
 
                 / /   V a l i d a r   f o r m a t o s 
 
                 i f   ( d a d o s . v e r b a s   & &   ! v a l i d a r V a l o r ( d a d o s . v e r b a s ) )   { 
 
                         w a r n ( ' V a l o r   d e   c r % d i t o   c o m   f o r m a t o   s u s p e i t o : ' ,   d a d o s . v e r b a s ) ; 
 
                         d a d o s . _ a v i s o C r e d i t o   =   t r u e ; 
 
                 } 
 
               
 
                 i f   ( d a d o s . f g t s   & &   d a d o s . f g t s   ! = =   ' 0 , 0 0 '   & &   ! v a l i d a r V a l o r ( d a d o s . f g t s ) )   { 
 
                         w a r n ( ' V a l o r   d e   F G T S   c o m   f o r m a t o   s u s p e i t o : ' ,   d a d o s . f g t s ) ; 
 
                         d a d o s . _ a v i s o F g t s   =   t r u e ; 
 
                 } 
 
               
 
                 i f   ( d a d o s . d a t a A t u a l i z a c a o   & &   ! v a l i d a r D a t a ( d a d o s . d a t a A t u a l i z a c a o ) )   { 
 
                         w a r n ( ' D a t a   e x t r a % d a   i n v % l i d a : ' ,   d a d o s . d a t a A t u a l i z a c a o ) ; 
 
                         d a d o s . _ a v i s o D a t a   =   t r u e ; 
 
                 } 
 
               
 
                 r e t u r n   d a d o s ; 
 
         } 
 
 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         / /   E S T R A T % G I A   3 :   W E B   W O R K E R   P D F 
 
         / /   P D F . j s   r o d a   e m   W o r k e r   i s o l a d o        z e r o   b l o q u e i o   n o   t h r e a d   p r i n c i p a l . 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 
 
         f u n c t i o n   c r i a r P d f W o r k e r B l o b ( )   { 
 
                 c o n s t   w o r k e r C o d e   =   ` 
 
 i m p o r t S c r i p t s ( ' h t t p s : / / c d n j s . c l o u d f l a r e . c o m / a j a x / l i b s / p d f . j s / 2 . 1 6 . 1 0 5 / p d f . m i n . j s ' ) ; 
 
 p d f j s L i b . G l o b a l W o r k e r O p t i o n s . w o r k e r S r c   =   ' h t t p s : / / c d n j s . c l o u d f l a r e . c o m / a j a x / l i b s / p d f . j s / 2 . 1 6 . 1 0 5 / p d f . w o r k e r . m i n . j s ' ; 
 
 
 
 f u n c t i o n   n o r m a l i z a r N o m e ( n o m e )   { 
 
         i f   ( ! n o m e )   r e t u r n   ' ' ; 
 
         r e t u r n   n o m e . n o r m a l i z e ( ' N F D ' ) . r e p l a c e ( / [ \ \ u 0 3 0 0 - \ \ u 0 3 6 f ] / g ,   ' ' ) . r e p l a c e ( / [ . ] / g ,   ' ' ) . t o U p p e r C a s e ( ) . t r i m ( ) ; 
 
 } 
 
 
 
 a s y n c   f u n c t i o n   e x t r a i r ( a r r a y B u f f e r ,   i d N o m e A r q u i v o ,   p e r i t o s C o n h e c i d o s )   { 
 
         v a r   p d f   =   n u l l ;   v a r   p a g e   =   n u l l ; 
 
         t r y   { 
 
                 v a r   t a s k   =   p d f j s L i b . g e t D o c u m e n t ( {   d a t a :   a r r a y B u f f e r   } ) ; 
 
                 p d f   =   a w a i t   t a s k . p r o m i s e ; 
 
                 p a g e   =   a w a i t   p d f . g e t P a g e ( 1 ) ; 
 
                 v a r   t c   =   a w a i t   p a g e . g e t T e x t C o n t e n t ( ) ; 
 
                 v a r   t x t   =   t c . i t e m s . m a p ( f u n c t i o n ( i )   {   r e t u r n   i . s t r . t r i m ( ) ;   } ) . f i l t e r ( f u n c t i o n ( s )   {   r e t u r n   s   ! = =   ' ' ;   } ) . j o i n ( '   ' ) ; 
 
 
 
                 v a r   r e g e x V e r b a s         =   / V E R B A S \ \ s + ( [ \ \ d . , ] + ) / i ; 
 
                 v a r   r e g e x F G T S             =   / V E R B A S \ \ s + [ \ \ d . , ] + \ \ s + F G T S \ \ s + ( [ \ \ d . , ] + ) / i ; 
 
                 v a r   r e g e x D e p F G T S       =   / D E P [ O % ] S I T O   F G T S \ \ s * [ . , ] ? \ \ s * ( [ \ \ d . , ] + ) / i ; 
 
                 v a r   r e g e x I N S S T o t a l   =   / C O N T R I B U I % % O   S O C I A L   S O B R E   S A L % R I O S   D E V I D O S \ \ s + ( [ \ \ d . , ] + ) / i ; 
 
                 v a r   r e g e x I N S S A u t o r   =   / D E D U % % O   D E   C O N T R I B U I % % O   S O C I A L \ \ s + ( ? : \ \ ( \ \ s * ) ? ( [ \ \ d . , ] + ) ( ? : \ \ s * \ \ ) ) ? / i ; 
 
                 v a r   r e g e x C u s t a s         =   / C U S T A S   J U D I C I A I S   D E V I D A S   P E L O   R E C L A M A D O \ \ s + ( [ \ \ d . , ] + ) / i ; 
 
                 v a r   r e g e x D a t a             =   / ( ? : D a t a \ \ s + L i q u i d a [ % c ] [ % a ] o \ \ s * [ : \ \ - ] ? \ \ s * ( \ \ d { 2 } \ \ / \ \ d { 2 } \ \ / \ \ d { 4 } ) ) | ( ? : ( \ \ d { 2 } \ \ / \ \ d { 2 } \ \ / \ \ d { 4 } ) \ \ s * D a t a \ \ s + L i q u i d a [ % c ] [ % a ] o ) / i ; 
 
                 v a r   r e g e x D a t a F B         =   / ( [ 0 - 3 ] [ 0 - 9 ] \ \ / [ 0 - 1 ] [ 0 - 9 ] \ \ / 2 0 [ 2 - 9 ] [ 0 - 9 ] ) \ \ s + [ A - Z % - <% \ \ s ] + D a t a \ \ s + L i q u i d a [ % c ] [ % a ] o / i ; 
 
                 v a r   r e g e x I d A s s i n       =   / D o c u m e n t o   a s s i n a d o   e l e t r o n i c a m e n t e [ \ \ s \ \ S ] * ? - \ \ s * ( [ a - z A - Z 0 - 9 ] + ) ( ? : \ \ s | $ ) / i ; 
 
                 v a r   r e g e x H o n A u t o r     =   / H O N O R % R I O S   L % Q U I D O S   P A R A   P A T R O N O   D O   R E C L A M A N T E \ \ s + ( [ \ \ d . , ] + ) / i ; 
 
                 v a r   r e g e x H o n P e r i t o   =   / H O N O R % R I O S   L % Q U I D O S   P A R A \ \ s + ( ? ! P A T R O N O   D O   R E C L A M A N T E ) ( . + ? ) \ \ s + ( [ \ \ d . , ] { 3 , } ) / i ; 
 
                 v a r   r e g e x P e r i o d o       =   / ( \ \ d { 2 } [ / ] ? \ \ d { 2 } [ / ] ? \ \ d { 4 } ) \ \ s + a \ \ s + ( \ \ d { 2 } [ / ] ? \ \ d { 2 } [ / ] ? \ \ d { 4 } ) / ; 
 
                 v a r   r e g e x I R P F             =   / I R P F \ \ s + D E V I D O \ \ s + P E L O \ \ s + R E C L A M A N T E \ \ s + ( [ \ \ d . , ] + ) / i ; 
 
 
 
                 v a r   v e r b a s         =   ( t x t . m a t c h ( r e g e x V e r b a s )         | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   f g t s             =   ( t x t . m a t c h ( r e g e x F G T S )             | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   i n s s T o t a l   =   ( t x t . m a t c h ( r e g e x I N S S T o t a l )     | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   i n s s A u t o r   =   ( t x t . m a t c h ( r e g e x I N S S A u t o r )     | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   c u s t a s         =   ( t x t . m a t c h ( r e g e x C u s t a s )           | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   h o n A u t o r     =   ( t x t . m a t c h ( r e g e x H o n A u t o r )       | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   m P e r i t o       =   t x t . m a t c h ( r e g e x H o n P e r i t o ) ; 
 
                 v a r   p e r i t o N o m e     =   m P e r i t o   ?   m P e r i t o [ 1 ] . t r i m ( )   :   ' ' ; 
 
                 v a r   p e r i t o V a l o r   =   m P e r i t o   ?   m P e r i t o [ 2 ]   :   ' ' ; 
 
 
 
                 i f   ( p e r i t o N o m e   & &   p e r i t o V a l o r   & &   p e r i t o s C o n h e c i d o s   & &   p e r i t o s C o n h e c i d o s . l e n g t h )   { 
 
                         v a r   e h P e r i t o   =   p e r i t o s C o n h e c i d o s . s o m e ( f u n c t i o n ( p )   { 
 
                                 r e t u r n   n o r m a l i z a r N o m e ( p ) . i n c l u d e s ( n o r m a l i z a r N o m e ( p e r i t o N o m e ) )   | | 
 
                                               n o r m a l i z a r N o m e ( p e r i t o N o m e ) . i n c l u d e s ( n o r m a l i z a r N o m e ( p ) ) ; 
 
                         } ) ; 
 
                         i f   ( ! e h P e r i t o )   {   h o n A u t o r   =   p e r i t o V a l o r ;   p e r i t o N o m e   =   ' ' ;   p e r i t o V a l o r   =   ' ' ;   } 
 
                 } 
 
 
 
                 v a r   d a t a A t u a l i z a c a o   =   ( t x t . m a t c h ( r e g e x D a t a )   | |   [ ] ) [ 1 ]   | |   ( t x t . m a t c h ( r e g e x D a t a )   | |   [ ] ) [ 2 ] ; 
 
                 i f   ( ! d a t a A t u a l i z a c a o )   {   v a r   f b   =   t x t . m a t c h ( r e g e x D a t a F B ) ;   i f   ( f b )   d a t a A t u a l i z a c a o   =   f b [ 1 ] ;   } 
 
 
 
                 v a r   i d P l a n i l h a   =   i d N o m e A r q u i v o   | |   ( t x t . m a t c h ( r e g e x I d A s s i n )   | |   [ ] ) [ 1 ]   | |   ' ' ; 
 
                 v a r   p m   =   t x t . m a t c h ( r e g e x P e r i o d o ) ; 
 
                 v a r   p e r i o d o C a l c u l o   =   n u l l ; 
 
                 i f   ( p m )   { 
 
                         v a r   f m t   =   f u n c t i o n ( s )   {   r e t u r n   s . i n d e x O f ( ' / ' )   ! = =   - 1   ?   s   :   s . s u b s t r ( 0 , 2 ) + ' / ' + s . s u b s t r ( 2 , 2 ) + ' / ' + s . s u b s t r ( 4 , 4 ) ;   } ; 
 
                         p e r i o d o C a l c u l o   =   f m t ( p m [ 1 ] )   +   '   a   '   +   f m t ( p m [ 2 ] ) ; 
 
                 } 
 
                 v a r   i r p f M   =   t x t . m a t c h ( r e g e x I R P F ) ; 
 
                 v a r   i r p f I s e n t o   =   ! i r p f M   | |   p a r s e F l o a t ( i r p f M [ 1 ] . r e p l a c e ( / \ \ . / g , ' ' ) . r e p l a c e ( ' , ' , ' . ' ) )   = = =   0 ; 
 
                 v a r   f g t s D e p o s i t a d o   =   f a l s e ; 
 
                 i f   ( f g t s )   {   v a r   m D e p   =   t x t . m a t c h ( r e g e x D e p F G T S ) ;   i f   ( m D e p   & &   m D e p [ 1 ] )   f g t s D e p o s i t a d o   =   f g t s . r e p l a c e ( / [ \ \ . , ] / g , ' ' )   = = =   m D e p [ 1 ] . r e p l a c e ( / [ \ \ . , ] / g , ' ' ) ;   } 
 
 
 
                 r e t u r n   {   s u c e s s o :   t r u e ,   v e r b a s ,   f g t s ,   f g t s D e p o s i t a d o ,   i n s s T o t a l ,   i n s s A u t o r ,   c u s t a s , 
 
                                   d a t a A t u a l i z a c a o ,   i d P l a n i l h a ,   h o n A u t o r ,   p e r i t o N o m e ,   p e r i t o V a l o r ,   p e r i o d o C a l c u l o ,   i r p f I s e n t o   } ; 
 
         }   c a t c h ( e )   { 
 
                 r e t u r n   {   s u c e s s o :   f a l s e ,   e r r o :   e . m e s s a g e   } ; 
 
         }   f i n a l l y   { 
 
                 t r y   {   i f   ( p a g e )   p a g e . c l e a n u p ( ) ;   }   c a t c h ( e )   { } 
 
                 t r y   {   i f   ( p d f )   a w a i t   p d f . d e s t r o y ( ) ;   }   c a t c h ( e )   { } 
 
         } 
 
 } 
 
 
 
 s e l f . o n m e s s a g e   =   a s y n c   f u n c t i o n ( e )   { 
 
         v a r   d   =   e . d a t a ; 
 
         v a r   r e s u l t a d o   =   a w a i t   e x t r a i r ( d . a r r a y B u f f e r ,   d . i d N o m e A r q u i v o ,   d . p e r i t o s C o n h e c i d o s ) ; 
 
         s e l f . p o s t M e s s a g e ( r e s u l t a d o ) ; 
 
 } ; 
 
 ` ; 
 
                 c o n s t   b l o b   =   n e w   B l o b ( [ w o r k e r C o d e ] ,   {   t y p e :   ' a p p l i c a t i o n / j a v a s c r i p t '   } ) ; 
 
                 r e t u r n   U R L . c r e a t e O b j e c t U R L ( b l o b ) ; 
 
         } 
 
 
 
         / /   P l a c e h o l d e r   p a r a   c o m p a t i b i l i d a d e   c o m   h c a l c - o v e r l a y . j s 
 
         a s y n c   f u n c t i o n   e x t r a i r D a d o s P l a n i l h a ( a r r a y B u f f e r ,   i d N o m e A r q u i v o   =   ' ' )   { 
 
                 l e t   l o a d i n g T a s k   =   n u l l ; 
 
                 l e t   p d f   =   n u l l ; 
 
                 l e t   p a g e   =   n u l l ; 
 
 
 
                 t r y   { 
 
                         i f   ( ! w i n d o w . p d f j s L i b )   { 
 
                                 t h r o w   n e w   E r r o r ( ' P D F . j s   n % o   e s t %   c a r r e g a d o ' ) ; 
 
                         } 
 
                       
 
                         l o a d i n g T a s k   =   w i n d o w . p d f j s L i b . g e t D o c u m e n t ( {   d a t a :   a r r a y B u f f e r   } ) ; 
 
                         p d f   =   a w a i t   l o a d i n g T a s k . p r o m i s e ; 
 
                         p a g e   =   a w a i t   p d f . g e t P a g e ( 1 ) ; 
 
                         c o n s t   t e x t C o n t e n t   =   a w a i t   p a g e . g e t T e x t C o n t e n t ( ) ; 
 
                       
 
                         c o n s t   t e x t o s B r u t o s   =   t e x t C o n t e n t . i t e m s . m a p ( i t e m   = >   i t e m . s t r . t r i m ( ) ) ; 
 
                         c o n s t   t e x t o C o m p l e t o   =   t e x t o s B r u t o s . f i l t e r ( s t r   = >   s t r   ! = =   " " ) . j o i n ( '   ' ) ; 
 
 
 
                         / /   R e g e x   o t i m i z a d a s   ( c o p i a d a s   d e   e x t . j s   v 4 . 2 ) 
 
                         c o n s t   r e g e x V e r b a s   =   / V E R B A S \ s + ( [ \ d . , ] + ) / i ; 
 
                         c o n s t   r e g e x F G T S   =   / V E R B A S \ s + [ \ d . , ] + \ s + F G T S \ s + ( [ \ d . , ] + ) / i ; 
 
                         c o n s t   r e g e x D e p o s i t o F G T S   =   / D E P [ O % ] S I T O   F G T S \ s * [ \ . , ] ? \ s * ( [ \ d \ . , ] + ) / i ; 
 
                         c o n s t   r e g e x I N S S T o t a l   =   / C O N T R I B U I % % O   S O C I A L   S O B R E   S A L % R I O S   D E V I D O S \ s + ( [ \ d . , ] + ) / i ; 
 
                         c o n s t   r e g e x I N S S A u t o r   =   / D E D U % % O   D E   C O N T R I B U I % % O   S O C I A L \ s + ( ? : \ ( \ s * ) ? ( [ \ d . , ] + ) ( ? : \ s * \ ) ) ? / i ; 
 
                         c o n s t   r e g e x C u s t a s   =   / C U S T A S   J U D I C I A I S   D E V I D A S   P E L O   R E C L A M A D O \ s + ( [ \ d . , ] + ) / i ; 
 
                         c o n s t   r e g e x D a t a   =   / ( ? : D a t a \ s + L i q u i d a [ % c ] [ % a ] o \ s * [ : \ - ] ? \ s * ( \ d { 2 } \ / \ d { 2 } \ / \ d { 4 } ) ) | ( ? : ( \ d { 2 } \ / \ d { 2 } \ / \ d { 4 } ) \ s * D a t a \ s + L i q u i d a [ % c ] [ % a ] o ) / i ; 
 
                         c o n s t   r e g e x D a t a F a l l b a c k   =   / ( [ 0 - 3 ] [ 0 - 9 ] \ / [ 0 - 1 ] [ 0 - 9 ] \ / 2 0 [ 2 - 9 ] [ 0 - 9 ] ) \ s + [ A - Z % - <% \ s ] + D a t a \ s + L i q u i d a [ % c ] [ % a ] o / i ; 
 
                         c o n s t   r e g e x I d A s s i n a t u r a   =   / D o c u m e n t o   a s s i n a d o   e l e t r o n i c a m e n t e [ \ s \ S ] * ? - \ s * ( [ a - z A - Z 0 - 9 ] + ) ( ? : \ s | $ ) / i ; 
 
                         c o n s t   r e g e x H o n A u t o r   =   / H O N O R % R I O S   L % Q U I D O S   P A R A   P A T R O N O   D O   R E C L A M A N T E \ s + ( [ \ d . , ] + ) / i ; 
 
                         c o n s t   r e g e x H o n P e r i t o   =   / H O N O R % R I O S   L % Q U I D O S   P A R A \ s + ( ? ! P A T R O N O   D O   R E C L A M A N T E ) ( . + ? ) \ s + ( [ \ d . , ] { 3 , } ) / i ; 
 
                         c o n s t   r e g e x P e r i o d o   =   / ( \ d { 2 } [ \ / ] ? \ d { 2 } [ \ / ] ? \ d { 4 } ) \ s + a \ s + ( \ d { 2 } [ \ / ] ? \ d { 2 } [ \ / ] ? \ d { 4 } ) / ; 
 
                         c o n s t   r e g e x I R P F   =   / I R P F \ s + D E V I D O \ s + P E L O \ s + R E C L A M A N T E \ s + ( [ \ d . , ] + ) / i ; 
 
 
 
                         / /   E x t r a % % o 
 
                         c o n s t   v e r b a s   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x V e r b a s )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
                         c o n s t   f g t s   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x F G T S )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
                         c o n s t   i n s s T o t a l   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x I N S S T o t a l )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
                         c o n s t   i n s s A u t o r   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x I N S S A u t o r )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
                         c o n s t   c u s t a s   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x C u s t a s )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
                         l e t   h o n A u t o r   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x H o n A u t o r )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
                       
 
                         c o n s t   m a t c h P e r i t o   =   t e x t o C o m p l e t o . m a t c h ( r e g e x H o n P e r i t o ) ; 
 
                         l e t   p e r i t o N o m e   =   m a t c h P e r i t o   ?   m a t c h P e r i t o [ 1 ] . t r i m ( )   :   " " ; 
 
                         l e t   p e r i t o V a l o r   =   m a t c h P e r i t o   ?   m a t c h P e r i t o [ 2 ]   :   " " ; 
 
 
 
                         / /   V A L I D A % % O :   V e r i f i c a r   s e   " h o n o r % r i o   p a r a . . . "   %   p e r i t o   o u   a d v o g a d o   a u t o r 
 
                         / /   R E G R A :   D e f a u l t   =   h o n o r % r i o   a d v o g a d o   a u t o r 
 
                         / /                 S %%  r e g i s t r a   c o m o   p e r i t o   s e   n o m e   b a t e r   c o m   p e r i t o   d e t e c t a d o 
 
                         / /   P R E V A L % N C I A :   V a l o r   d a   p l a n i l h a   p r e v a l e c e   s o b r e   v a l o r   d a   s e n t e n % a   ( m a i s   a t u a l i z a d o ) 
 
                         i f   ( p e r i t o N o m e   & &   p e r i t o V a l o r )   { 
 
                                 c o n s t   p e r i t o s C o n h e c i d o s   =   w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   | |   [ ] ; 
 
                               
 
                                 / /   V e r i f i c a r   s e   n o m e   b a t e   c o m   p e r i t o   j %   d e t e c t a d o   n o   p r o c e s s o 
 
                                 c o n s t   e h P e r i t o   =   p e r i t o s C o n h e c i d o s . s o m e ( p   = > 
 
                                         n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( p ) . i n c l u d e s ( n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( p e r i t o N o m e ) )   | | 
 
                                         n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( p e r i t o N o m e ) . i n c l u d e s ( n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( p ) ) 
 
                                 ) ; 
 
                               
 
                                 i f   ( e h P e r i t o )   { 
 
                                         / /   N o m e   b a t e   c o m   p e r i t o   d e t e c t a d o        h o n o r % r i o   p e r i c i a l 
 
                                         c o n s o l e . l o g ( ` h c a l c :   " $ { p e r i t o N o m e } "   c o n f i r m a d o   c o m o   P E R I T O   ( m a t c h   d e t e c t a d o ) ` ) ; 
 
                                         / /   M a n t % m   p e r i t o N o m e   e   p e r i t o V a l o r 
 
                                 }   e l s e   { 
 
                                         / /   D E F A U L T :   Q u a l q u e r   o u t r o   c a s o   =   h o n o r % r i o   a d v o g a d o   a u t o r 
 
                                         c o n s o l e . l o g ( ` h c a l c :   " $ { p e r i t o N o m e } "        D E F A U L T :   h o n o r % r i o   a d v o g a d o   a u t o r ` ) ; 
 
                                         / /   T r a n s f e r i r   p a r a   h o n o r % r i o s   d o   a u t o r 
 
                                         h o n A u t o r   =   p e r i t o V a l o r ; 
 
                                         p e r i t o N o m e   =   " " ; 
 
                                         p e r i t o V a l o r   =   " " ; 
 
                                 } 
 
                         } 
 
 
 
                         l e t   d a t a A t u a l i z a c a o   =   ( t e x t o C o m p l e t o . m a t c h ( r e g e x D a t a )   | |   [ ] ) [ 1 ]   | | 
 
                                                                       ( t e x t o C o m p l e t o . m a t c h ( r e g e x D a t a )   | |   [ ] ) [ 2 ] ; 
 
                         i f   ( ! d a t a A t u a l i z a c a o )   { 
 
                                 c o n s t   f a l l b a c k   =   t e x t o C o m p l e t o . m a t c h ( r e g e x D a t a F a l l b a c k ) ; 
 
                                 i f   ( f a l l b a c k )   d a t a A t u a l i z a c a o   =   f a l l b a c k [ 1 ] ; 
 
                         } 
 
                       
 
                         c o n s t   i d P l a n i l h a   =   i d N o m e A r q u i v o   | |   ( t e x t o C o m p l e t o . m a t c h ( r e g e x I d A s s i n a t u r a )   | |   [ ] ) [ 1 ]   | |   " " ; 
 
 
 
                         / /   E x t r a i r   p e r % o d o   d o   c % l c u l o 
 
                         c o n s t   p e r i o d o M a t c h   =   t e x t o C o m p l e t o . m a t c h ( r e g e x P e r i o d o ) ; 
 
                         l e t   p e r i o d o C a l c u l o   =   n u l l ; 
 
                         i f   ( p e r i o d o M a t c h )   { 
 
                                 c o n s t   f m t   =   s   = >   s . i n c l u d e s ( ' / ' )   ?   s   :   ` $ { s . s u b s t r ( 0 , 2 ) } / $ { s . s u b s t r ( 2 , 2 ) } / $ { s . s u b s t r ( 4 , 4 ) } ` ; 
 
                                 p e r i o d o C a l c u l o   =   ` $ { f m t ( p e r i o d o M a t c h [ 1 ] ) }   a   $ { f m t ( p e r i o d o M a t c h [ 2 ] ) } ` ; 
 
                         } 
 
 
 
                         / /   E x t r a i r   I R P F   e   d e t e r m i n a r   s e   %   t r i b u t % v e l 
 
                         c o n s t   i r p f M a t c h   =   t e x t o C o m p l e t o . m a t c h ( r e g e x I R P F ) ; 
 
                         c o n s t   i r p f I s e n t o   =   ! i r p f M a t c h   | |   p a r s e F l o a t ( 
 
                                 i r p f M a t c h [ 1 ] . r e p l a c e ( / \ . / g ,   ' ' ) . r e p l a c e ( ' , ' ,   ' . ' ) 
 
                         )   = = =   0 ; 
 
 
 
                         / /   D e t e c t a r   s e   F G T S   f o i   d e p o s i t a d o   ( c o m p a r a n d o   v a l o r e s ) 
 
                         l e t   f g t s D e p o s i t a d o   =   f a l s e ; 
 
                         i f   ( f g t s )   { 
 
                                 c o n s t   m a t c h D e p o s i t o F G T S   =   t e x t o C o m p l e t o . m a t c h ( r e g e x D e p o s i t o F G T S ) ; 
 
                                 i f   ( m a t c h D e p o s i t o F G T S   & &   m a t c h D e p o s i t o F G T S [ 1 ] )   { 
 
                                         / /   N o r m a l i z a r   v a l o r e s   p a r a   c o m p a r a % % o   ( r e m o v e r   p o n t o s / v % r g u l a s ) 
 
                                         c o n s t   v a l o r F g t s   =   f g t s . r e p l a c e ( / [ \ . , ] / g ,   ' ' ) ; 
 
                                         c o n s t   v a l o r D e p o s i t o   =   m a t c h D e p o s i t o F G T S [ 1 ] . r e p l a c e ( / [ \ . , ] / g ,   ' ' ) ; 
 
                                       
 
                                         i f   ( v a l o r F g t s   = = =   v a l o r D e p o s i t o )   { 
 
                                                 f g t s D e p o s i t a d o   =   t r u e ; 
 
                                                 c o n s o l e . l o g ( ` h c a l c :   F G T S   i d e n t i f i c a d o   c o m o   D E P O S I T A D O   ( v a l o r :   $ { f g t s } ) ` ) ; 
 
                                         } 
 
                                 } 
 
                         } 
 
 
 
                         c o n s t   d a d o s B r u t o s   =   { 
 
                                 v e r b a s , 
 
                                 f g t s , 
 
                                 f g t s D e p o s i t a d o , 
 
                                 i n s s T o t a l , 
 
                                 i n s s A u t o r , 
 
                                 c u s t a s , 
 
                                 d a t a A t u a l i z a c a o , 
 
                                 i d P l a n i l h a , 
 
                                 h o n A u t o r , 
 
                                 p e r i t o N o m e , 
 
                                 p e r i t o V a l o r , 
 
                                 p e r i o d o C a l c u l o , 
 
                                 i r p f I s e n t o , 
 
                                 s u c e s s o :   t r u e 
 
                         } ; 
 
 
 
                         / /   A p l i c a r   v a l i d a % % o   ( F a s e   2 ) 
 
                         c o n s t   d a d o s V a l i d a d o s   =   v a l i d a r D a d o s E x t r a i d o s ( d a d o s B r u t o s ) ; 
 
                         c o n s t   q u a l i d a d e   =   c a l c u l a r Q u a l i d a d e E x t r a c a o ( d a d o s V a l i d a d o s ) ; 
 
                       
 
                         c o n s o l e . l o g ( ` [ H C a l c ]   E x t r a % % o   c o n c l u % d a   -   Q u a l i d a d e :   $ { q u a l i d a d e . p e r c e n t u a l } %   ( $ { q u a l i d a d e . v a l i d o s } / $ { q u a l i d a d e . t o t a l }   v % l i d o s ) ` ) ; 
 
                         i f   ( q u a l i d a d e . f a l t a n d o . l e n g t h   >   0 )   { 
 
                                 w a r n ( ' C a m p o s   n % o   e x t r a % d o s : ' ,   q u a l i d a d e . f a l t a n d o . j o i n ( ' ,   ' ) ) ; 
 
                         } 
 
                         i f   ( q u a l i d a d e . i n v a l i d o s . l e n g t h   >   0 )   { 
 
                                 w a r n ( ' C a m p o s   c o m   f o r m a t o   s u s p e i t o : ' ,   q u a l i d a d e . i n v a l i d o s . m a p ( i   = >   ` $ { i . c a m p o } :   $ { i . v a l o r } ` ) . j o i n ( ' ,   ' ) ) ; 
 
                         } 
 
 
 
                         r e t u r n   d a d o s V a l i d a d o s ; 
 
 
 
                 }   c a t c h   ( e r r o r )   { 
 
                         c o n s o l e . e r r o r ( ' [ H C a l c ]   E r r o   n a   e x t r a % % o : ' ,   e r r o r . m e s s a g e ) ; 
 
                         r e t u r n   {   s u c e s s o :   f a l s e ,   e r r o :   e r r o r . m e s s a g e   } ; 
 
                 }   f i n a l l y   { 
 
                         / /   L i m p e z a   d e   m e m %%r i a   ( p r e v i n e   l e a k ) 
 
                         i f   ( p a g e )   { 
 
                                 t r y   {   p a g e . c l e a n u p ( ) ;   }   c a t c h   ( e )   { } 
 
                         } 
 
                         i f   ( p d f )   { 
 
                                 t r y   {   a w a i t   p d f . d e s t r o y ( ) ;   }   c a t c h   ( e )   { } 
 
                         } 
 
                         i f   ( l o a d i n g T a s k   & &   t y p e o f   l o a d i n g T a s k . d e s t r o y   = = =   ' f u n c t i o n ' )   { 
 
                                 t r y   {   a w a i t   l o a d i n g T a s k . d e s t r o y ( ) ;   }   c a t c h   ( e )   { } 
 
                         } 
 
                 } 
 
         } 
 
 
 
         a s y n c   f u n c t i o n   p r o c e s s a r P l a n i l h a P D F ( f i l e )   { 
 
                 l e t   i d N o m e A r q u i v o   =   ' ' ; 
 
                 c o n s t   m a t c h N o m e   =   f i l e . n a m e . m a t c h ( / D o c u m e n t o _ ( [ a - z A - Z 0 - 9 ] + ) \ . p d f / i ) ; 
 
                 i f   ( m a t c h N o m e )   i d N o m e A r q u i v o   =   m a t c h N o m e [ 1 ] ; 
 
 
 
                 / /   T r a n s f e r e   A r r a y B u f f e r   p a r a   W o r k e r   ( z e r o - c o p y ) 
 
                 c o n s t   a r r a y B u f f e r   =   a w a i t   f i l e . a r r a y B u f f e r ( ) ; 
 
                 c o n s t   p e r i t o s C o n h e c i d o s   =   w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   | |   [ ] ; 
 
 
 
                 r e t u r n   n e w   P r o m i s e ( ( r e s o l v e ,   r e j e c t )   = >   { 
 
                         i f   ( ! w i n d o w . h c a l c S t a t e . _ p d f W o r k e r U r l )   { 
 
                                 w i n d o w . h c a l c S t a t e . _ p d f W o r k e r U r l   =   c r i a r P d f W o r k e r B l o b ( ) ; 
 
                         } 
 
                         c o n s t   w o r k e r   =   n e w   W o r k e r ( w i n d o w . h c a l c S t a t e . _ p d f W o r k e r U r l ) ; 
 
                         w o r k e r . o n m e s s a g e   =   ( e )   = >   { 
 
                                 w o r k e r . t e r m i n a t e ( ) ; 
 
                                 c o n s t   d a d o s   =   e . d a t a ; 
 
                                 i f   ( ! d a d o s . s u c e s s o )   {   r e s o l v e ( d a d o s ) ;   r e t u r n ;   } 
 
                                 c o n s t   d a d o s V a l i d a d o s   =   v a l i d a r D a d o s E x t r a i d o s ( d a d o s ) ; 
 
                                 c o n s t   q u a l i d a d e   =   c a l c u l a r Q u a l i d a d e E x t r a c a o ( d a d o s V a l i d a d o s ) ; 
 
                                 c o n s o l e . l o g ( ' [ H C a l c   W o r k e r ]   Q u a l i d a d e :   '   +   q u a l i d a d e . p e r c e n t u a l   +   ' %   ( '   +   q u a l i d a d e . v a l i d o s   +   ' / '   +   q u a l i d a d e . t o t a l   +   '   v % l i d o s ) ' ) ; 
 
                                 i f   ( q u a l i d a d e . f a l t a n d o . l e n g t h   >   0 )   w a r n ( ' C a m p o s   n % o   e x t r a % d o s : ' ,   q u a l i d a d e . f a l t a n d o . j o i n ( ' ,   ' ) ) ; 
 
                                 i f   ( q u a l i d a d e . i n v a l i d o s . l e n g t h   >   0 )   w a r n ( ' C a m p o s   s u s p e i t o s : ' ,   q u a l i d a d e . i n v a l i d o s . m a p ( i   = >   i . c a m p o   +   ' :   '   +   i . v a l o r ) . j o i n ( ' ,   ' ) ) ; 
 
                                 r e s o l v e ( d a d o s V a l i d a d o s ) ; 
 
                         } ; 
 
                         w o r k e r . o n e r r o r   =   ( e )   = >   {   w o r k e r . t e r m i n a t e ( ) ;   r e j e c t ( n e w   E r r o r ( e . m e s s a g e ) ) ;   } ; 
 
                         w o r k e r . p o s t M e s s a g e ( {   a r r a y B u f f e r ,   i d N o m e A r q u i v o ,   p e r i t o s C o n h e c i d o s   } ,   [ a r r a y B u f f e r ] ) ; 
 
                 } ) ; 
 
         } 
 
 
 
         / /   E x p o r   p a r a   h c a l c - o v e r l a y . j s 
 
         w i n d o w . n o r m a l i z a r N o m e P a r a C o m p a r a c a o   =   n o r m a l i z a r N o m e P a r a C o m p a r a c a o ; 
 
         w i n d o w . c a r r e g a r P D F J S S e N e c e s s a r i o       =   c a r r e g a r P D F J S S e N e c e s s a r i o ; 
 
         w i n d o w . p r o c e s s a r P l a n i l h a P D F                 =   p r o c e s s a r P l a n i l h a P D F ; 
 
 } ) ( ) ; 
 
 

// ── hcalc-overlay.js ──────────────────────────────────
( f u n c t i o n ( )   { 
 
         ' u s e   s t r i c t ' ; 
 
         c o n s t   H C A L C _ D E B U G   =   f a l s e ; 
 
         c o n s t   d b g     =   ( . . . a r g s )   = >   {   i f   ( H C A L C _ D E B U G )   c o n s o l e . l o g ( ' [ h c a l c ] ' ,   . . . a r g s ) ;   } ; 
 
         c o n s t   w a r n   =   ( . . . a r g s )   = >   c o n s o l e . w a r n ( ' [ h c a l c ] ' ,   . . . a r g s ) ; 
 
         c o n s t   e r r     =   ( . . . a r g s )   = >   c o n s o l e . e r r o r ( ' [ h c a l c ] ' ,   . . . a r g s ) ; 
 
         / /   P r o x i e s   p a r a   d e p e n d e n c i a s   d e   h c a l c - c o r e . j s   e   h c a l c - p d f . j s 
 
         c o n s t   n o r m a l i z a r N o m e P a r a C o m p a r a c a o   =   n           = >   w i n d o w . n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( n ) ; 
 
         c o n s t   c a r r e g a r P D F J S S e N e c e s s a r i o       =   ( )           = >   w i n d o w . c a r r e g a r P D F J S S e N e c e s s a r i o ( ) ; 
 
         c o n s t   p r o c e s s a r P l a n i l h a P D F                 =   ( . . . a )   = >   w i n d o w . p r o c e s s a r P l a n i l h a P D F ( . . . a ) ; 
 
         c o n s t   e x e c u t a r P r e p                                 =   ( . . . a )   = >   w i n d o w . e x e c u t a r P r e p ( . . . a ) ; 
 
         c o n s t   d e s t a c a r E l e m e n t o N a T i m e l i n e     =   ( . . . a )   = >   w i n d o w . d e s t a c a r E l e m e n t o N a T i m e l i n e ( . . . a ) ; 
 
         c o n s t   e n c o n t r a r I t e m T i m e l i n e                 =   ( h r e f )   = >   w i n d o w . e n c o n t r a r I t e m T i m e l i n e   & &   w i n d o w . e n c o n t r a r I t e m T i m e l i n e ( h r e f ) ; 
 
         c o n s t   e x p a n d i r A n e x o s                               =   ( i t e m )   = >   w i n d o w . e x p a n d i r A n e x o s   & &   w i n d o w . e x p a n d i r A n e x o s ( i t e m ) ; 
 
         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
         f u n c t i o n   i n i t i a l i z e B o t a o ( )   { 
 
                 i f   ( w i n d o w . _ _ h c a l c B o t a o I n i t i a l i z e d )   { 
 
                         d b g ( ' i n i t i a l i z e B o t a o   i g n o r a d o :   b o t % o   j %   i n i c i a l i z a d o . ' ) ; 
 
                         r e t u r n ; 
 
                 } 
 
                 d b g ( ' i n i t i a l i z e B o t a o   i n i c i a d o   ( F A S E   A   -   l e v e ) . ' ) ; 
 
                 w i n d o w . _ _ h c a l c B o t a o I n i t i a l i z e d   =   t r u e ; 
 
 
 
                 / /   C S S   m % n i m o        a p e n a s   o   b o t % o   ( ~ 2 0 0   b y t e s ) 
 
                 i f   ( ! d o c u m e n t . g e t E l e m e n t B y I d ( ' h c a l c - b t n - s t y l e ' ) )   { 
 
                         c o n s t   s   =   d o c u m e n t . c r e a t e E l e m e n t ( ' s t y l e ' ) ; 
 
                         s . i d   =   ' h c a l c - b t n - s t y l e ' ; 
 
                         s . i n n e r T e x t   =   ` 
 
                 # b t n - a b r i r - h o m o l o g a c a o   { 
 
                         p o s i t i o n :   f i x e d ;   b o t t o m :   2 0 p x ;   r i g h t :   2 0 p x ;   z - i n d e x :   9 9 9 9 9 ; 
 
                         b a c k g r o u n d :   # 0 0 5 0 9 e ;   c o l o r :   w h i t e ;   b o r d e r :   n o n e ;   b o r d e r - r a d i u s :   6 p x ; 
 
                         p a d d i n g :   1 0 p x   1 8 p x ;   f o n t - s i z e :   1 3 p x ;   f o n t - w e i g h t :   b o l d ;   c u r s o r :   p o i n t e r ; 
 
                         b o x - s h a d o w :   0   3 p x   5 p x   r g b a ( 0 , 0 , 0 , 0 . 3 ) ; 
 
                 } 
 
                 # b t n - a b r i r - h o m o l o g a c a o : h o v e r   {   b a c k g r o u n d :   # 0 0 3 d 7 a ;   } ` ; 
 
                         d o c u m e n t . h e a d . a p p e n d C h i l d ( s ) ; 
 
                 } 
 
 
 
                 / /   I n j e t a   A P E N A S   b o t % o   +   i n p u t   f i l e   ( s e m   o v e r l a y ) 
 
                 d o c u m e n t . b o d y . i n s e r t A d j a c e n t H T M L ( ' b e f o r e e n d ' ,   ` 
 
         < b u t t o n   i d = " b t n - a b r i r - h o m o l o g a c a o " > \ u D 8 3 D \ u D C C 4   C a r r e g a r   P l a n i l h a < / b u t t o n > 
 
         < i n p u t   t y p e = " f i l e "   i d = " i n p u t - p l a n i l h a - p d f "   a c c e p t = " . p d f "   s t y l e = " d i s p l a y :   n o n e ; " > ` ) ; 
 
 
 
                 c o n s t   b t n   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' b t n - a b r i r - h o m o l o g a c a o ' ) ; 
 
 
 
                 / /   H a n d l e r   d o   b o t % o        i n i c i a l i z a   o v e r l a y   l a z y   n a   p r i m e i r a   v e z 
 
                 b t n . o n c l i c k   =   a s y n c   ( )   = >   { 
 
                         i f   ( ! w i n d o w . _ _ h c a l c O v e r l a y I n i t i a l i z e d )   { 
 
                                 d b g ( ' P r i m e i r o   c l i q u e :   c a r r e g a n d o   o v e r l a y   c o m p l e t o   ( l a z y   i n i t ) . . . ' ) ; 
 
                                 i n i t i a l i z e O v e r l a y ( ) ; 
 
                                 / /   i n i t i a l i z e O v e r l a y ( )   s u b s t i t u i u   b t n . o n c l i c k   c o m   o   h a n d l e r   c o m p l e t o 
 
                         } 
 
                         / /   E x e c u t a r   f a s e   c o r r e t a 
 
                         i f   ( ! w i n d o w . h c a l c S t a t e . p l a n i l h a C a r r e g a d a )   { 
 
                                 d b g ( ' F A S E   1 :   a b r i n d o   f i l e   p i c k e r . ' ) ; 
 
                                 d o c u m e n t . g e t E l e m e n t B y I d ( ' i n p u t - p l a n i l h a - p d f ' ) . c l i c k ( ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
                         / /   F A S E   3 :   r e - d e s p a c h a   p a r a   o   h a n d l e r   c o m p l e t o   ( o v e r l a y   j %   i n i c i a l i z a d o ) 
 
                         b t n . c l i c k ( ) ; 
 
                 } ; 
 
                 d b g ( ' B o t % o   f l u t u a n t e   i n j e t a d o   ( l a z y   i n i t   a t i v o ) . ' ) ; 
 
         } 
 
 
 
 
 
         f u n c t i o n   i n i t i a l i z e O v e r l a y ( )   { 
 
                 i f   ( w i n d o w . _ _ h c a l c O v e r l a y I n i t i a l i z e d )   { 
 
                         d b g ( ' i n i t i a l i z e O v e r l a y   i g n o r a d o :   o v e r l a y   j a   i n i c i a l i z a d o . ' ) ; 
 
                         r e t u r n ; 
 
                 } 
 
                 d b g ( ' i n i t i a l i z e O v e r l a y   i n i c i a d o . ' ) ; 
 
                 w i n d o w . _ _ h c a l c O v e r l a y I n i t i a l i z e d   =   t r u e ; 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   1 .   E S T I L O S   D O   O V E R L A Y   E   B O T % O   ( v 1 . 9   -   U I   C o m p a c t a ) 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 c o n s t   s t y l e s   =   ` 
 
                 # h o m o l o g a c a o - o v e r l a y   { 
 
                         d i s p l a y :   n o n e ;   p o s i t i o n :   f i x e d ;   t o p :   0 ;   l e f t :   0 ;   w i d t h :   1 0 0 v w ;   h e i g h t :   1 0 0 v h ; 
 
                         b a c k g r o u n d :   t r a n s p a r e n t ;   z - i n d e x :   1 0 0 0 0 0 ;   j u s t i f y - c o n t e n t :   f l e x - e n d ;   a l i g n - i t e m s :   f l e x - s t a r t ; 
 
                         f o n t - f a m i l y :   A r i a l ,   s a n s - s e r i f ;   p o i n t e r - e v e n t s :   n o n e ; 
 
                 } 
 
 
 
                 # h o m o l o g a c a o - m o d a l   { 
 
                         b a c k g r o u n d :   # f f f ;   w i d t h :   6 3 0 p x ;   m a x - w i d t h :   6 3 0 p x ;   h e i g h t :   1 0 0 v h ;   m a x - h e i g h t :   1 0 0 v h ;   o v e r f l o w - y :   a u t o ; 
 
                         b o r d e r - r a d i u s :   0 ;   b o x - s h a d o w :   - 4 p x   0   2 0 p x   r g b a ( 0 , 0 , 0 , 0 . 2 5 ) ;   p a d d i n g :   1 0 p x ;   m a r g i n :   0 ; 
 
                         d i s p l a y :   f l e x ;   f l e x - d i r e c t i o n :   c o l u m n ;   g a p :   5 p x ;   c o l o r :   # 3 3 3 ;   p o i n t e r - e v e n t s :   a l l ; 
 
                 } 
 
 
 
                 . m o d a l - h e a d e r   {   d i s p l a y :   f l e x ;   j u s t i f y - c o n t e n t :   s p a c e - b e t w e e n ;   a l i g n - i t e m s :   c e n t e r ;   b o r d e r - b o t t o m :   1 p x   s o l i d   # d d d ;   p a d d i n g - b o t t o m :   6 p x ;   m a r g i n - b o t t o m :   3 p x ;   } 
 
                 . m o d a l - h e a d e r   h 2   {   m a r g i n :   0 ;   c o l o r :   # 0 0 5 0 9 e ;   f o n t - s i z e :   1 5 p x ;   } 
 
                 . b t n - c l o s e   {   b a c k g r o u n d :   # c c 0 0 0 0 ;   c o l o r :   w h i t e ;   b o r d e r :   n o n e ;   p a d d i n g :   3 p x   1 0 p x ;   c u r s o r :   p o i n t e r ;   b o r d e r - r a d i u s :   3 p x ;   f o n t - w e i g h t :   b o l d ;   f o n t - s i z e :   1 1 p x ;   } 
 
 
 
                 f i e l d s e t   {   b o r d e r :   1 p x   s o l i d   # d d d ;   b o r d e r - r a d i u s :   4 p x ;   p a d d i n g :   6 p x ;   m a r g i n - b o t t o m :   4 p x ;   b a c k g r o u n d :   # f f f ;   } 
 
                 l e g e n d   {   b a c k g r o u n d :   # 0 0 5 0 9 e ;   c o l o r :   w h i t e ;   p a d d i n g :   2 p x   6 p x ;   b o r d e r - r a d i u s :   3 p x ;   f o n t - s i z e :   1 2 p x ;   f o n t - w e i g h t :   b o l d ;   } 
 
 
 
                 . r o w   {   d i s p l a y :   f l e x ;   g a p :   6 p x ;   f l e x - w r a p :   w r a p ;   m a r g i n - b o t t o m :   4 p x ;   a l i g n - i t e m s :   c e n t e r ;   } 
 
                 . c o l   {   d i s p l a y :   f l e x ;   f l e x - d i r e c t i o n :   c o l u m n ;   f l e x :   1 ;   m i n - w i d t h :   1 4 0 p x ;   } 
 
 
 
                 l a b e l   {   f o n t - s i z e :   1 1 p x ;   f o n t - w e i g h t :   b o l d ;   m a r g i n - b o t t o m :   3 p x ;   c o l o r :   # 5 5 5 ;   } 
 
                 i n p u t [ t y p e = " t e x t " ] ,   i n p u t [ t y p e = " d a t e " ]   {   p a d d i n g :   6 p x ;   b o r d e r :   1 p x   s o l i d   # a a a ;   b o r d e r - r a d i u s :   3 p x ;   f o n t - s i z e :   1 3 p x ;   } 
 
                 t e x t a r e a   {   p a d d i n g :   6 p x ;   b o r d e r :   1 p x   s o l i d   # a a a ;   b o r d e r - r a d i u s :   3 p x ;   f o n t - s i z e :   1 2 p x ;   r e s i z e :   v e r t i c a l ;   f o n t - f a m i l y :   A r i a l ,   s a n s - s e r i f ;   } 
 
                 s e l e c t   {   p a d d i n g :   6 p x ;   b o r d e r :   1 p x   s o l i d   # a a a ;   b o r d e r - r a d i u s :   3 p x ;   f o n t - s i z e :   1 3 p x ;   } 
 
 
 
                 . h i d d e n   {   d i s p l a y :   n o n e   ! i m p o r t a n t ;   } 
 
                 / *   D e s t a q u e   p a r a   o   c a m p o   a t u a l   d a   c o l e t a   * / 
 
                 . h i g h l i g h t   {   b o r d e r :   2 p x   s o l i d   # f f 9 8 0 0   ! i m p o r t a n t ;   b a c k g r o u n d :   # f f f d e 7   ! i m p o r t a n t ;   b o x - s h a d o w :   0   0   6 p x   r g b a ( 2 5 5 , 1 5 2 , 0 , 0 . 4 ) ;   } 
 
 
 
                 / *   B a d g e s   p a r a   p a r t e s   d e t e c t a d a s   ( v 1 . 9 )   * / 
 
                 . p a r t e s - b a d g e s   {   d i s p l a y :   f l e x ;   f l e x - w r a p :   w r a p ;   g a p :   5 p x ;   m a r g i n :   6 p x   0 ;   } 
 
                 . b a d g e   { 
 
                         d i s p l a y :   i n l i n e - b l o c k ; 
 
                         p a d d i n g :   4 p x   1 0 p x ; 
 
                         b o r d e r - r a d i u s :   1 2 p x ; 
 
                         f o n t - s i z e :   1 1 p x ; 
 
                         f o n t - w e i g h t :   6 0 0 ; 
 
                         w h i t e - s p a c e :   n o w r a p ; 
 
                 } 
 
                 . b a d g e - b l u e   {   b a c k g r o u n d :   # e 0 f 2 f e ;   c o l o r :   # 0 3 6 9 a 1 ;   b o r d e r :   1 p x   s o l i d   # b a e 6 f d ;   } 
 
                 . b a d g e - g r a y   {   b a c k g r o u n d :   # f 3 f 4 f 6 ;   c o l o r :   # 6 b 7 2 8 0 ;   b o r d e r :   1 p x   s o l i d   # e 5 e 7 e b ;   } 
 
                 . b a d g e - g r e e n   {   b a c k g r o u n d :   # d 1 f a e 5 ;   c o l o r :   # 0 4 7 8 5 7 ;   b o r d e r :   1 p x   s o l i d   # a 7 f 3 d 0 ;   } 
 
 
 
                 . b t n - a c t i o n   {   b a c k g r o u n d :   # 2 8 a 7 4 5 ;   c o l o r :   w h i t e ;   b o r d e r :   n o n e ;   p a d d i n g :   8 p x   1 2 p x ;   b o r d e r - r a d i u s :   3 p x ;   c u r s o r :   p o i n t e r ;   f o n t - w e i g h t :   b o l d ;   f o n t - s i z e :   1 3 p x ;   } 
 
                 . b t n - a c t i o n : h o v e r   {   b a c k g r o u n d :   # 2 1 8 8 3 8 ;   } 
 
                 . b t n - g r a v a r   {   b a c k g r o u n d :   # 0 0 5 0 9 e ;   w i d t h :   1 0 0 % ;   p a d d i n g :   1 2 p x ;   f o n t - s i z e :   1 6 p x ;   m a r g i n - t o p :   1 0 p x ;   } 
 
 
 
                 / *   C o m p a c t a r   e s p a % a m e n t o   i n t e r n o   p a r a   c a b e r   n a   t e l a   * / 
 
                 # h o m o l o g a c a o - m o d a l   f i e l d s e t   {   p a d d i n g :   8 p x   1 0 p x ;   m a r g i n - b o t t o m :   6 p x ;   } 
 
                 # h o m o l o g a c a o - m o d a l   . r o w   {   m a r g i n - b o t t o m :   6 p x ;   g a p :   8 p x ;   } 
 
                 # h o m o l o g a c a o - m o d a l   i n p u t [ t y p e = t e x t ] , 
 
                 # h o m o l o g a c a o - m o d a l   i n p u t [ t y p e = d a t e ] , 
 
                 # h o m o l o g a c a o - m o d a l   s e l e c t , 
 
                 # h o m o l o g a c a o - m o d a l   t e x t a r e a   {   p a d d i n g :   5 p x   7 p x ;   f o n t - s i z e :   1 2 p x ;   } 
 
                 # h o m o l o g a c a o - m o d a l   l a b e l   {   f o n t - s i z e :   1 1 p x ;   m a r g i n - b o t t o m :   2 p x ;   } 
 
                 # h o m o l o g a c a o - m o d a l   l e g e n d   {   f o n t - s i z e :   1 2 p x ;   p a d d i n g :   3 p x   8 p x ;   } 
 
                 # h o m o l o g a c a o - m o d a l   . b t n - g r a v a r   {   p a d d i n g :   1 0 p x ;   f o n t - s i z e :   1 5 p x ;   m a r g i n - t o p :   1 0 p x ;   } 
 
 
 
                 / *   E s t i l o s   d o   C a r d   d e   R e s u m o   d a   P l a n i l h a   ( F A S E   1 )   * / 
 
                 # r e s u m o - e x t r a c a o - c a r d   { 
 
                         w i d t h :   2 6 0 p x ; 
 
                         b a c k g r o u n d :   # f 8 f 9 f a ; 
 
                         b o r d e r :   2 p x   s o l i d   # 1 0 b 9 8 1 ; 
 
                         b o r d e r - r a d i u s :   8 p x ; 
 
                         p a d d i n g :   0 ; 
 
                         b o x - s h a d o w :   0   4 p x   6 p x   r g b a ( 0 , 0 , 0 , 0 . 1 ) ; 
 
                         p o i n t e r - e v e n t s :   a l l ; 
 
                         a l i g n - s e l f :   f l e x - s t a r t ; 
 
                         m a r g i n - r i g h t :   8 p x ; 
 
                         o v e r f l o w :   h i d d e n ; 
 
                         f l e x - s h r i n k :   0 ; 
 
                 } 
 
                 # r e s u m o - e x t r a c a o - c a r d   h 4   { 
 
                         m a r g i n :   0 ; 
 
                         p a d d i n g :   1 0 p x   1 2 p x ; 
 
                         b o r d e r - b o t t o m :   1 p x   s o l i d   # 1 0 b 9 8 1 ; 
 
                         c u r s o r :   p o i n t e r ; 
 
                         u s e r - s e l e c t :   n o n e ; 
 
                         d i s p l a y :   f l e x ; 
 
                         j u s t i f y - c o n t e n t :   s p a c e - b e t w e e n ; 
 
                         a l i g n - i t e m s :   c e n t e r ; 
 
                         f o n t - s i z e :   1 3 p x ; 
 
                         c o l o r :   # 1 6 a 3 4 a ; 
 
                         b a c k g r o u n d :   # f 0 f d f 4 ; 
 
                 } 
 
                 # r e s u m o - e x t r a c a o - c a r d   h 4 : h o v e r   {   b a c k g r o u n d :   # d c f c e 7 ;   } 
 
                 # r e s u m o - b o d y   { 
 
                         p a d d i n g :   1 0 p x   1 2 p x ; 
 
                         d i s p l a y :   n o n e ; 
 
                 } 
 
                 # r e s u m o - c o n t e u d o   {   d i s p l a y :   f l e x ;   f l e x - d i r e c t i o n :   c o l u m n ;   g a p :   6 p x ;   } 
 
                 . r e s u m o - i t e m   { 
 
                         p a d d i n g :   4 p x   6 p x ; 
 
                         b a c k g r o u n d :   w h i t e ; 
 
                         b o r d e r - r a d i u s :   4 p x ; 
 
                         b o r d e r :   1 p x   s o l i d   # e 5 e 7 e b ; 
 
                         f o n t - s i z e :   1 2 p x ; 
 
                 } 
 
                 . r e s u m o - i t e m   s t r o n g   {   c o l o r :   # 1 6 a 3 4 a ;   } 
 
                 # b t n - r e l o a d - p l a n i l h a   { 
 
                         m a r g i n - t o p :   8 p x ; 
 
                         w i d t h :   1 0 0 % ; 
 
                         p a d d i n g :   5 p x   1 0 p x ; 
 
                         f o n t - s i z e :   1 1 p x ; 
 
                         b o r d e r - r a d i u s :   4 p x ; 
 
                         b o r d e r :   1 p x   s o l i d   # 1 0 b 9 8 1 ; 
 
                         b a c k g r o u n d :   # f f f ; 
 
                         c o l o r :   # 1 0 b 9 8 1 ; 
 
                         c u r s o r :   p o i n t e r ; 
 
                 } 
 
                 # b t n - r e l o a d - p l a n i l h a : h o v e r   {   b a c k g r o u n d :   # 1 0 b 9 8 1 ;   c o l o r :   w h i t e ;   } 
 
 
 
                 / *   R e c u r s o s   c o m   a n e x o s        i n t e g r a d o   d e   r e c . j s   v 1 . 0   * / 
 
                 . r e c - r e c u r s o - c a r d   { 
 
                         p a d d i n g :   8 p x   1 0 p x ;   m a r g i n - b o t t o m :   6 p x ; 
 
                         b o r d e r :   1 p x   s o l i d   # e 5 e 7 e b ;   b o r d e r - r a d i u s :   5 p x ; 
 
                         b a c k g r o u n d :   w h i t e ;   c u r s o r :   p o i n t e r ;   t r a n s i t i o n :   a l l   0 . 2 s ; 
 
                 } 
 
                 . r e c - r e c u r s o - c a r d : h o v e r   {   b a c k g r o u n d :   # f 0 f 9 f f ;   b o r d e r - c o l o r :   # 3 b 8 2 f 6 ;   } 
 
                 . r e c - t i p o - b a d g e   { 
 
                         d i s p l a y :   i n l i n e - b l o c k ;   p a d d i n g :   1 p x   7 p x ;   b o r d e r - r a d i u s :   3 p x ; 
 
                         f o n t - s i z e :   1 0 p x ;   f o n t - w e i g h t :   7 0 0 ;   c o l o r :   w h i t e ; 
 
                         b a c k g r o u n d :   # 3 b 8 2 f 6 ;   m a r g i n - r i g h t :   6 p x ; 
 
                 } 
 
                 . r e c - a n e x o s - l i s t a   {   m a r g i n - t o p :   6 p x ;   p a d d i n g - t o p :   5 p x ;   b o r d e r - t o p :   1 p x   s o l i d   # e 5 e 7 e b ;   d i s p l a y :   n o n e ;   } 
 
                 . r e c - r e c u r s o - c a r d . e x p a n d i d o   . r e c - a n e x o s - l i s t a   {   d i s p l a y :   b l o c k ;   } 
 
                 . r e c - a n e x o - i t e m   { 
 
                         d i s p l a y :   f l e x ;   a l i g n - i t e m s :   c e n t e r ;   g a p :   6 p x ; 
 
                         p a d d i n g :   3 p x   4 p x ;   b o r d e r - r a d i u s :   3 p x ;   c u r s o r :   p o i n t e r ; 
 
                         f o n t - s i z e :   1 1 p x ;   t r a n s i t i o n :   b a c k g r o u n d   0 . 1 5 s ; 
 
                 } 
 
                 . r e c - a n e x o - i t e m : h o v e r   {   b a c k g r o u n d :   # f 3 f 4 f 6 ;   } 
 
                 . r e c - a n e x o - b a d g e   { 
 
                         p a d d i n g :   1 p x   5 p x ;   b o r d e r - r a d i u s :   2 p x ; 
 
                         f o n t - s i z e :   1 0 p x ;   f o n t - w e i g h t :   6 0 0 ;   c o l o r :   w h i t e ;   w h i t e - s p a c e :   n o w r a p ; 
 
                 } 
 
                 . r e c - a n e x o - i d   { 
 
                         f o n t - s i z e :   1 0 p x ;   b a c k g r o u n d :   # f 3 f 4 f 6 ; 
 
                         p a d d i n g :   1 p x   4 p x ;   b o r d e r - r a d i u s :   2 p x ; 
 
                         f o n t - f a m i l y :   m o n o s p a c e ;   c o l o r :   # 3 7 4 1 5 1 ;   u s e r - s e l e c t :   a l l ; 
 
                 } 
 
                 . r e c - s e t a - t o g g l e   {   f o n t - s i z e :   1 0 p x ;   c o l o r :   # 9 c a 3 a f ;   m a r g i n - l e f t :   a u t o ;   } 
 
         ` ; 
 
                 i f   ( ! d o c u m e n t . g e t E l e m e n t B y I d ( ' h c a l c - o v e r l a y - s t y l e ' ) )   { 
 
                         c o n s t   s t y l e S h e e t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' s t y l e ' ) ; 
 
                         s t y l e S h e e t . i d   =   ' h c a l c - o v e r l a y - s t y l e ' ; 
 
                         s t y l e S h e e t . i n n e r T e x t   =   s t y l e s ; 
 
                         d o c u m e n t . h e a d . a p p e n d C h i l d ( s t y l e S h e e t ) ; 
 
                 } 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   2 .   H T M L   D O   O V E R L A Y   ( E S T R U T U R A ) 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 c o n s t   h t m l M o d a l   =   ` 
 
         < d i v   i d = " h o m o l o g a c a o - o v e r l a y " > 
 
                 < ! - -   C a r d   d e   R e s u m o   d a   P l a n i l h a   E x t r a % d a   ( %   e s q u e r d a )   - - > 
 
                 < d i v   i d = " r e s u m o - e x t r a c a o - c a r d "   s t y l e = " d i s p l a y : n o n e " > 
 
                         < h 4   i d = " r e s u m o - t o g g l e " > 
 
                                 < s p a n >      P l a n i l h a   C a r r e g a d a < / s p a n > 
 
                                 < s p a n   i d = " r e s u m o - s e t a " >    < / s p a n > 
 
                         < / h 4 > 
 
                         < d i v   i d = " r e s u m o - b o d y " > 
 
                                 < d i v   i d = " r e s u m o - c o n t e u d o " > < / d i v > 
 
                                 < b u t t o n   i d = " b t n - r e l o a d - p l a n i l h a " >      R e c a r r e g a r   P D F < / b u t t o n > 
 
                         < / d i v > 
 
                 < / d i v > 
 
               
 
                 < d i v   i d = " h o m o l o g a c a o - m o d a l " > 
 
                         < d i v   c l a s s = " m o d a l - h e a d e r " > 
 
                                 < h 2 > A s s i s t e n t e   d e   H o m o l o g a % % o < / h 2 > 
 
                                 < b u t t o n   c l a s s = " b t n - c l o s e "   i d = " b t n - f e c h a r " > X   F e c h a r < / b u t t o n > 
 
                         < / d i v > 
 
 
 
 
 
 
 
                         < ! - -   S E % % O   1   e   2 :   B A S E   E   P A R T E   - - > 
 
                         < f i e l d s e t > 
 
                                 < l e g e n d > C % l c u l o   B a s e   e   A u t o r i a < / l e g e n d > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < d i v   c l a s s = " c o l " > 
 
                                                 < l a b e l > O r i g e m   d o   C % l c u l o < / l a b e l > 
 
                                                 < s e l e c t   i d = " c a l c - o r i g e m " > 
 
                                                         < o p t i o n   v a l u e = " p j e c a l c "   s e l e c t e d > P J e C a l c < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " o u t r o s " > O u t r o s < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " c o l "   i d = " c o l - p j c " > 
 
                                                 < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " c a l c - p j c "   c h e c k e d >   A c o m p a n h a   a r q u i v o   . P J C ? < / l a b e l > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " c o l " > 
 
                                                 < l a b e l > A u t o r   d o   C % l c u l o < / l a b e l > 
 
                                                 < s e l e c t   i d = " c a l c - a u t o r " > 
 
                                                         < o p t i o n   v a l u e = " a u t o r "   s e l e c t e d > R e c l a m a n t e   ( A u t o r ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " r e c l a m a d a " > R e c l a m a d a < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " p e r i t o " > P e r i t o < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " c o l   h i d d e n "   i d = " c o l - e s c l a r e c i m e n t o s " > 
 
                                                 < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " c a l c - e s c l a r e c i m e n t o s "   c h e c k e d >   E s c l a r e c i m e n t o s   d o   P e r i t o ? < / l a b e l > 
 
                                                 < i n p u t   t y p e = " t e x t "   i d = " c a l c - p e c a - p e r i t o "   p l a c e h o l d e r = " I d   d a   P e % a " > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   S E % % O   3 :   A T U A L I Z A % % O   - - > 
 
                         < f i e l d s e t > 
 
                                 < l e g e n d > A t u a l i z a % % o < / l e g e n d > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < d i v   c l a s s = " c o l " > 
 
                                                 < l a b e l > % n d i c e   d e   A t u a l i z a % % o < / l a b e l > 
 
                                                 < s e l e c t   i d = " c a l c - i n d i c e " > 
 
                                                         < o p t i o n   v a l u e = " a d c 5 8 "   s e l e c t e d > S E L I C   /   I P C A - E   ( A D C   5 8 ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " t r " > T R   /   I P C A - E   ( C a s o s   A n t i g o s ) < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   S E % % O   5 :   D A D O S   C O P I A D O S   D A   P L A N I L H A   ( % N I C O   F I E L D S E T )   - - > 
 
                         < f i e l d s e t > 
 
                                 < l e g e n d > D a d o s   C o p i a d o s   d a   P l a n i l h a < / l e g e n d > 
 
 
 
                                 < d i v   s t y l e = " p a d d i n g :   8 p x ;   b o r d e r :   1 p x   d a s h e d   # d 9 d 9 d 9 ;   b o r d e r - r a d i u s :   4 p x ;   m a r g i n - b o t t o m :   6 p x ;   b a c k g r o u n d :   # f f f ; " > 
 
                                         < l a b e l   s t y l e = " d i s p l a y : b l o c k ;   m a r g i n - b o t t o m :   5 p x ;   c o l o r : # 0 0 5 0 9 e ;   f o n t - s i z e :   1 2 p x ; " > 1 )   I d e n t i f i c a % % o ,   D a t a s ,   P r i n c i p a l   e   F G T S < / l a b e l > 
 
                                         < d i v   c l a s s = " r o w " > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   0   0   1 4 0 p x ; " > 
 
                                                         < l a b e l > I d   d a   P l a n i l h a < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - i d "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " I d   # X X X X " > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   0   0   1 4 0 p x ; " > 
 
                                                         < l a b e l > D a t a   d a   A t u a l i z a % % o < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - d a t a "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " D D / M M / A A A A " > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   1 ; " > 
 
                                                         < l a b e l > C r % d i t o   P r i n c i p a l   ( o u   T o t a l ) < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - c r e d i t o "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " R $   C r % d i t o   P r i n c i p a l " > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " r o w "   s t y l e = " a l i g n - i t e m s :   c e n t e r ;   g a p :   1 0 p x ;   m a r g i n - b o t t o m :   5 p x ; " > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   0   0   a u t o ; " > 
 
                                                         < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " c a l c - f g t s "   c h e c k e d >   F G T S   a p u r a d o   s e p a r a d o ? < / l a b e l > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l "   i d = " f g t s - r a d i o s "   s t y l e = " f l e x :   0   0   a u t o ;   d i s p l a y :   f l e x ;   g a p :   1 2 p x ; " > 
 
                                                         < l a b e l   s t y l e = " m a r g i n :   0 ; " > < i n p u t   t y p e = " r a d i o "   n a m e = " f g t s - t i p o "   v a l u e = " d e v i d o "   c h e c k e d >   D e v i d o < / l a b e l > 
 
                                                         < l a b e l   s t y l e = " m a r g i n :   0 ; " > < i n p u t   t y p e = " r a d i o "   n a m e = " f g t s - t i p o "   v a l u e = " d e p o s i t a d o " >   D e p o s i t a d o < / l a b e l > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " r o w "   i d = " r o w - f g t s - v a l o r " > 
 
                                                 < d i v   c l a s s = " c o l "   i d = " c o l - f g t s - v a l "   s t y l e = " f l e x :   0   0   a u t o ; " > 
 
                                                         < l a b e l   s t y l e = " f o n t - s i z e :   1 1 p x ;   m a r g i n - b o t t o m :   2 p x ; " > V a l o r   F G T S   S e p a r a d o < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - f g t s "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " R $   F G T S "   s t y l e = " w i d t h :   1 4 0 p x ; " > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " r o w   h i d d e n "   i d = " c o l - j u r o s - v a l " > 
 
                                                 < d i v   c l a s s = " c o l " > 
 
                                                         < l a b e l > J u r o s < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - j u r o s "   p l a c e h o l d e r = " R $   J u r o s " > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l " > 
 
                                                         < l a b e l > D a t a   d e   I n g r e s s o < / l a b e l > 
 
                                                         < i n p u t   t y p e = " d a t e "   i d = " d a t a - i n g r e s s o " > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
 
 
                                 < d i v   s t y l e = " p a d d i n g :   8 p x ;   b o r d e r :   1 p x   d a s h e d   # d 9 d 9 d 9 ;   b o r d e r - r a d i u s :   4 p x ;   m a r g i n - b o t t o m :   6 p x ;   b a c k g r o u n d :   # f f f ; " > 
 
                                         < l a b e l   s t y l e = " d i s p l a y : b l o c k ;   m a r g i n - b o t t o m :   5 p x ;   c o l o r : # 0 0 5 0 9 e ;   f o n t - s i z e :   1 2 p x ; " > 2 )   I N S S   ( A u t o r   e   R e c l a m a d a )   e   I R < / l a b e l > 
 
                                         < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - b o t t o m :   0 ; " > 
 
                                                 < d i v   c l a s s = " c o l " > 
 
                                                         < l a b e l > I N S S   -   D e s c o n t o   ( R e c l a m a n t e ) < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - i n s s - r e c "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " R $   I N S S   R e c l a m a n t e   ( D e s c o n t o ) " > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l " > 
 
                                                         < l a b e l > I N S S   -   T o t a l   d a   E m p r e s a   ( R e c l a m a d a ) < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - i n s s - t o t a l "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " R $   I N S S   T o t a l   /   R e c l a m a d a " > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - t o p :   5 p x ; " > 
 
                                                 < d i v   c l a s s = " c o l " > 
 
                                                         < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " i g n o r a r - i n s s " >   N % o   h %   I N S S < / l a b e l > 
 
                                                         < s m a l l   s t y l e = " c o l o r :   # 6 6 6 ;   d i s p l a y :   b l o c k ; " > * I N S S   R e c l a m a d a   =   S u b t r a % % o   a u t o m % t i c a   s e   P J e C a l c   m a r c a d o . < / s m a l l > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l " > 
 
                                                         < l a b e l > I m p o s t o   d e   R e n d a < / l a b e l > 
 
                                                         < s e l e c t   i d = " i r p f - t i p o "   s t y l e = " m a r g i n - b o t t o m :   5 p x ;   w i d t h :   1 0 0 % ; " > 
 
                                                                 < o p t i o n   v a l u e = " i s e n t o "   s e l e c t e d > N % o   h % < / o p t i o n > 
 
                                                                 < o p t i o n   v a l u e = " i n f o r m a r " > I n f o r m a r   V a l o r e s < / o p t i o n > 
 
                                                         < / s e l e c t > 
 
                                                         < d i v   i d = " i r p f - c a m p o s "   c l a s s = " h i d d e n "   s t y l e = " d i s p l a y : f l e x ;   g a p :   5 p x ; " > 
 
                                                                 < i n p u t   t y p e = " t e x t "   i d = " v a l - i r p f - b a s e "   p l a c e h o l d e r = " B a s e   ( R $ ) "   s t y l e = " f l e x : 1 ; " > 
 
                                                                 < i n p u t   t y p e = " t e x t "   i d = " v a l - i r p f - m e s e s "   p l a c e h o l d e r = " M e s e s "   s t y l e = " f l e x : 1 ; " > 
 
                                                         < / d i v > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
 
 
                                 < d i v   s t y l e = " p a d d i n g :   8 p x ;   b o r d e r :   1 p x   d a s h e d   # d 9 d 9 d 9 ;   b o r d e r - r a d i u s :   4 p x ;   m a r g i n - b o t t o m :   6 p x ;   b a c k g r o u n d :   # f f f ; " > 
 
                                         < l a b e l   s t y l e = " d i s p l a y : b l o c k ;   m a r g i n - b o t t o m :   5 p x ;   c o l o r : # 0 0 5 0 9 e ;   f o n t - s i z e :   1 2 p x ; " > 3 )   H o n o r % r i o s   A d v o c a t % c i o s < / l a b e l > 
 
                                         < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - b o t t o m :   0 ;   a l i g n - i t e m s :   f l e x - s t a r t ; " > 
 
 
 
                                                 < ! - -   C o l u n a   A U T O R   - - > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   1 ;   m i n - w i d t h :   1 6 0 p x ; " > 
 
                                                         < l a b e l > H o n o r % r i o s   A d v   A u t o r < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - h o n - a u t o r "   c l a s s = " c o l e t a - i n p u t   h i g h l i g h t "   p l a c e h o l d e r = " R $   H o n o r % r i o s   A u t o r " > 
 
                                                         < l a b e l   s t y l e = " f o n t - s i z e :   1 1 p x ;   m a r g i n - t o p :   4 p x ;   d i s p l a y :   b l o c k ; " > 
 
                                                                 < i n p u t   t y p e = " c h e c k b o x "   i d = " i g n o r a r - h o n - a u t o r " >   N % o   h %   h o n o r % r i o s   a u t o r 
 
                                                         < / l a b e l > 
 
                                                 < / d i v > 
 
 
 
                                                 < ! - -   C o l u n a   R % U   - - > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   1 ;   m i n - w i d t h :   1 6 0 p x ; " > 
 
                                                         < l a b e l > 
 
                                                                 < i n p u t   t y p e = " c h e c k b o x "   i d = " c h k - h o n - r e u "   c h e c k e d   s t y l e = " m a r g i n - r i g h t :   5 p x ; " > N % o   h %   H o n o r % r i o s   A d v   R % u 
 
                                                         < / l a b e l > 
 
                                                         < d i v   i d = " h o n - r e u - c a m p o s "   c l a s s = " h i d d e n "   s t y l e = " m a r g i n - t o p :   6 p x ; " > 
 
                                                                 < l a b e l   s t y l e = " f o n t - s i z e :   1 1 p x ;   d i s p l a y :   b l o c k ;   m a r g i n - b o t t o m :   6 p x ; " > 
 
                                                                         < i n p u t   t y p e = " c h e c k b o x "   i d = " c h k - h o n - r e u - s u s p e n s i v a "   c h e c k e d >   C o n d i % % o   S u s p e n s i v a 
 
                                                                 < / l a b e l > 
 
                                                                 < d i v   s t y l e = " d i s p l a y :   f l e x ;   g a p :   8 p x ;   f l e x - d i r e c t i o n :   c o l u m n ;   m a r g i n - b o t t o m :   6 p x ; " > 
 
                                                                         < l a b e l   s t y l e = " f o n t - s i z e :   1 1 p x ; " > 
 
                                                                                 < i n p u t   t y p e = " r a d i o "   n a m e = " r a d - h o n - r e u - t i p o "   v a l u e = " p e r c e n t u a l "   c h e c k e d >   P e r c e n t u a l 
 
                                                                         < / l a b e l > 
 
                                                                         < l a b e l   s t y l e = " f o n t - s i z e :   1 1 p x ; " > 
 
                                                                                 < i n p u t   t y p e = " r a d i o "   n a m e = " r a d - h o n - r e u - t i p o "   v a l u e = " v a l o r " >   V a l o r   I n f o r m a d o 
 
                                                                         < / l a b e l > 
 
                                                                 < / d i v > 
 
                                                                 < d i v   i d = " h o n - r e u - p e r c - c a m p o "   s t y l e = " m a r g i n - b o t t o m :   4 p x ; " > 
 
                                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - h o n - r e u - p e r c "   c l a s s = " c o l e t a - i n p u t "   v a l u e = " 5 % "   p l a c e h o l d e r = " % "   s t y l e = " w i d t h :   8 0 p x ; " > 
 
                                                                 < / d i v > 
 
                                                                 < d i v   i d = " h o n - r e u - v a l o r - c a m p o "   c l a s s = " h i d d e n "   s t y l e = " m a r g i n - b o t t o m :   4 p x ; " > 
 
                                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - h o n - r e u "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " R $   H o n o r % r i o s   R % u "   s t y l e = " w i d t h :   1 4 0 p x ; " > 
 
                                                                 < / d i v > 
 
                                                         < / d i v > 
 
                                                 < / d i v > 
 
 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
 
 
                                 < d i v   s t y l e = " p a d d i n g :   8 p x ;   b o r d e r :   1 p x   d a s h e d   # d 9 d 9 d 9 ;   b o r d e r - r a d i u s :   4 p x ;   b a c k g r o u n d :   # f f f ; " > 
 
                                         < l a b e l   s t y l e = " d i s p l a y : b l o c k ;   m a r g i n - b o t t o m :   5 p x ;   c o l o r : # 0 0 5 0 9 e ;   f o n t - s i z e :   1 2 p x ; " > 4 )   C u s t a s < / l a b e l > 
 
                                         < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - b o t t o m :   5 p x ; " > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   0   0   1 4 0 p x ; " > 
 
                                                         < l a b e l > V a l o r < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - c u s t a s "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " R $   C u s t a s " > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   0   0   1 4 0 p x ; " > 
 
                                                         < l a b e l > S t a t u s < / l a b e l > 
 
                                                         < s e l e c t   i d = " c u s t a s - s t a t u s " > 
 
                                                                 < o p t i o n   v a l u e = " d e v i d a s "   s e l e c t e d > D e v i d a s < / o p t i o n > 
 
                                                                 < o p t i o n   v a l u e = " p a g a s " > J %   P a g a s < / o p t i o n > 
 
                                                         < / s e l e c t > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l "   s t y l e = " f l e x :   0   0   1 4 0 p x ; " > 
 
                                                         < l a b e l > O r i g e m < / l a b e l > 
 
                                                         < s e l e c t   i d = " c u s t a s - o r i g e m " > 
 
                                                                 < o p t i o n   v a l u e = " s e n t e n c a "   s e l e c t e d > S e n t e n % a < / o p t i o n > 
 
                                                                 < o p t i o n   v a l u e = " a c o r d a o " > A c %%r d % o < / o p t i o n > 
 
                                                         < / s e l e c t > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                         < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - b o t t o m :   0 ; " > 
 
                                                 < d i v   c l a s s = " c o l "   i d = " c u s t a s - d a t a - c o l "   s t y l e = " f l e x :   1 ; " > 
 
                                                         < l a b e l > D a t a   C u s t a s   < s m a l l   s t y l e = " c o l o r :   # 6 6 6 ; " > ( v a z i o   =   m e s m a   p l a n i l h a ) < / s m a l l > < / l a b e l > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " c u s t a s - d a t a - o r i g e m "   c l a s s = " c o l e t a - i n p u t "   p l a c e h o l d e r = " D D / M M / A A A A " > 
 
                                                 < / d i v > 
 
                                                 < d i v   c l a s s = " c o l   h i d d e n "   i d = " c u s t a s - a c o r d a o - c o l "   s t y l e = " f l e x :   1 ; " > 
 
                                                         < l a b e l > A c %%r d % o < / l a b e l > 
 
                                                         < s e l e c t   i d = " c u s t a s - a c o r d a o - s e l e c t " > 
 
                                                                 < o p t i o n   v a l u e = " " > S e l e c i o n e   o   a c %%r d % o < / o p t i o n > 
 
                                                         < / s e l e c t > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   S E % % O   6 :   R E S P O N S A B I L I D A D E   - - > 
 
                         < f i e l d s e t > 
 
                                 < l e g e n d > R e s p o n s a b i l i d a d e < / l e g e n d > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < s e l e c t   i d = " r e s p - t i p o " > 
 
                                                 < o p t i o n   v a l u e = " u n i c a " > R e c l a m a d a   % n i c a < / o p t i o n > 
 
                                                 < o p t i o n   v a l u e = " s o l i d a r i a s " > D e v e d o r a s   S o l i d % r i a s < / o p t i o n > 
 
                                                 < o p t i o n   v a l u e = " s u b s i d i a r i a s "   s e l e c t e d > D e v e d o r a s   S u b s i d i % r i a s < / o p t i o n > 
 
                                         < / s e l e c t > 
 
                                 < / d i v > 
 
                                 < d i v   i d = " r e s p - s u b - o p c o e s "   c l a s s = " r o w " > 
 
                                         < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " r e s p - i n t e g r a l "   c h e c k e d >   R e s p o n d e   p e l o   p e r % o d o   t o t a l < / l a b e l > 
 
                                         < l a b e l   s t y l e = " m a r g i n - l e f t :   1 5 p x ; " > < i n p u t   t y p e = " c h e c k b o x "   i d = " r e s p - d i v e r s o s " >   P e r % o d o s   D i v e r s o s   ( G e r a   e s t r u t u r a   p a r a   p r e e n c h e r ) < / l a b e l > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   S E % % O   6 . 1 :   P E R % O D O S   D I V E R S O S   ( D i n % m i c o )   - - > 
 
                         < f i e l d s e t   i d = " r e s p - d i v e r s o s - f i e l d s e t "   c l a s s = " h i d d e n " > 
 
                                 < l e g e n d > P e r % o d o s   D i v e r s o s   -   C % l c u l o s   S e p a r a d o s   p o r   R e c l a m a d a < / l e g e n d > 
 
                                 < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - b o t t o m :   1 5 p x ; " > 
 
                                         < d i v   c l a s s = " c o l " > 
 
                                                 < l a b e l   s t y l e = " f o n t - w e i g h t :   b o l d ; " > D e v e d o r a   P r i n c i p a l < / l a b e l > 
 
                                                 < s e l e c t   i d = " r e s p - d e v e d o r a - p r i n c i p a l "   s t y l e = " w i d t h :   1 0 0 % ;   p a d d i n g :   8 p x ; " > 
 
                                                         < o p t i o n   v a l u e = " " > S e l e c i o n e   a   d e v e d o r a   p r i n c i p a l . . . < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                                 < s m a l l   s t y l e = " c o l o r :   # 6 6 6 ;   d i s p l a y :   b l o c k ;   m a r g i n - t o p :   5 p x ; " > * P a d r % o :   p r i m e i r a   r e c l a m a d a < / s m a l l > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w "   s t y l e = " m a r g i n - b o t t o m :   1 5 p x ;   f o n t - s i z e :   1 3 p x ;   c o l o r :   # 5 5 5 ; " > 
 
                                         < l a b e l > P r e e n c h a   p e r % o d o ,   p l a n i l h a   e   t i p o   ( P r i n c i p a l / S u b s i d i % r i a )   p a r a   c a d a   r e c l a m a d a   c o m   r e s p o n s a b i l i d a d e   d i v e r s a : < / l a b e l > 
 
                                 < / d i v > 
 
                                 < d i v   i d = " r e s p - d i v e r s o s - c o n t a i n e r " > < / d i v > 
 
                                 < b u t t o n   t y p e = " b u t t o n "   c l a s s = " b t n - a c t i o n "   i d = " b t n - a d i c i o n a r - p e r i o d o "   s t y l e = " m a r g i n - t o p :   1 0 p x ; " > +   A d i c i o n a r   P e r % o d o   D i v e r s o < / b u t t o n > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   L i n k s   d e   S e n t e n % a   e   A c %%r d % o   - - > 
 
                         < f i e l d s e t   s t y l e = " b o r d e r :   n o n e ;   p a d d i n g :   8 p x   0 ;   m a r g i n :   8 p x   0 ; " > 
 
                                 < d i v   i d = " l i n k - s e n t e n c a - a c o r d a o - c o n t a i n e r " > < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   S E % % O   7 B :   H O N O R % R I O S   P E R I C I A I S   ( a u t o - e s c o n d e   s e   n % o   d e t e c t a r   p e r i t o )   - - > 
 
                         < f i e l d s e t   i d = " f i e l d s e t - p e r i c i a - c o n h "   c l a s s = " h i d d e n " > 
 
                                 < l e g e n d > H o n o r % r i o s   P e r i c i a i s   < s p a n   i d = " l i n k - s e n t e n c a - c o n t a i n e r " > < / s p a n > < / l e g e n d > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < d i v   c l a s s = " c o l " > 
 
                                                 < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " c h k - p e r i t o - c o n h " >   H o n o r % r i o s   P e r i c i a i s   ( C o n h e c i m e n t o ) < / l a b e l > 
 
                                                 < d i v   i d = " p e r i t o - c o n h - c a m p o s "   c l a s s = " h i d d e n "   s t y l e = " m a r g i n - t o p :   5 p x ;   d i s p l a y :   f l e x ;   g a p :   1 0 p x ; " > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - p e r i t o - n o m e "   p l a c e h o l d e r = " N o m e   d o   P e r i t o " > 
 
                                                         < s e l e c t   i d = " p e r i t o - t i p o - p a g " > 
 
                                                                 < o p t i o n   v a l u e = " r e c l a m a d a "   s e l e c t e d > P a g o   p e l a   R e c l a m a d a   ( V a l o r ) < / o p t i o n > 
 
                                                                 < o p t i o n   v a l u e = " t r t " > P a g o   p e l o   T R T   ( A u t o r   S u c u m b e n t e ) < / o p t i o n > 
 
                                                         < / s e l e c t > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - p e r i t o - v a l o r "   p l a c e h o l d e r = " R $   V a l o r   o u   I D   T R T " > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - p e r i t o - d a t a "   p l a c e h o l d e r = " D a t a   d a   S e n t e n % a " > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w   h i d d e n "   i d = " r o w - p e r i t o - c o n t a b i l " > 
 
                                         < d i v   c l a s s = " c o l " > 
 
                                                 < l a b e l > H o n o r % r i o s   P e r i c i a i s   ( C o n t % b i l   -   R o g % r i o ) < / l a b e l > 
 
                                                 < d i v   i d = " p e r i t o - c o n t a b i l - c a m p o s "   s t y l e = " m a r g i n - t o p :   5 p x ;   d i s p l a y :   f l e x ;   g a p :   1 0 p x ; " > 
 
                                                         < i n p u t   t y p e = " t e x t "   i d = " v a l - p e r i t o - c o n t a b i l - v a l o r "   p l a c e h o l d e r = " V a l o r   d o s   h o n o r % r i o s   c o n t % b e i s " > 
 
                                                 < / d i v > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   C u s t a s   j %   f o r a m   m o v i d a s   p a r a   o   c a r d   4   a c i m a   - - > 
 
 
 
                         < ! - -   S E % % O   8 :   D E P % S I T O S   - - > 
 
                         < f i e l d s e t   i d = " f i e l d s e t - d e p o s i t o " > 
 
                                 < l e g e n d > D e p %%s i t o s < / l e g e n d > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < l a b e l   i d = " l a b e l - c h k - d e p o s i t o " > < i n p u t   t y p e = " c h e c k b o x "   i d = " c h k - d e p o s i t o " >   H %   D e p %%s i t o   R e c u r s a l ? < / l a b e l > 
 
                                         < l a b e l   s t y l e = " m a r g i n - l e f t :   2 0 p x ; " > < i n p u t   t y p e = " c h e c k b o x "   i d = " c h k - p a g - a n t e c i p a d o " >   P a g a m e n t o   A n t e c i p a d o < / l a b e l > 
 
                                 < / d i v > 
 
 
 
                                 < ! - -   C O N T A I N E R   D E   D E P % S I T O S   R E C U R S A I S   ( d i n % m i c o )   - - > 
 
                                 < d i v   i d = " d e p o s i t o - c a m p o s "   c l a s s = " h i d d e n " > 
 
                                         < d i v   i d = " d e p o s i t o s - c o n t a i n e r " > < / d i v > 
 
                                         < b u t t o n   t y p e = " b u t t o n "   i d = " b t n - a d d - d e p o s i t o "   c l a s s = " b t n - a c t i o n "   s t y l e = " m a r g i n - t o p :   8 p x ;   p a d d i n g :   4 p x   1 2 p x ;   f o n t - s i z e :   1 1 p x ; " > +   A d i c i o n a r   D e p %%s i t o   R e c u r s a l < / b u t t o n > 
 
                                 < / d i v > 
 
 
 
                                 < ! - -   C O N T A I N E R   D E   P A G A M E N T O S   A N T E C I P A D O S   ( d i n % m i c o )   - - > 
 
                                 < d i v   i d = " p a g - a n t e c i p a d o - c a m p o s "   c l a s s = " h i d d e n " > 
 
                                         < d i v   i d = " p a g a m e n t o s - c o n t a i n e r " > < / d i v > 
 
                                         < b u t t o n   t y p e = " b u t t o n "   i d = " b t n - a d d - p a g a m e n t o "   c l a s s = " b t n - a c t i o n "   s t y l e = " m a r g i n - t o p :   8 p x ;   p a d d i n g :   4 p x   1 2 p x ;   f o n t - s i z e :   1 1 p x ; " > +   A d i c i o n a r   P a g a m e n t o < / b u t t o n > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < ! - -   S E % % O   9 :   I N T I M A % % E S   - - > 
 
                         < f i e l d s e t   i d = " f i e l d s e t - i n t i m a c o e s " > 
 
                                 < l e g e n d > I n t i m a % % e s < / l e g e n d > 
 
                                 < d i v   i d = " l i s t a - i n t i m a c o e s - c o n t a i n e r " > 
 
                                         < s m a l l   s t y l e = " c o l o r : # 6 6 6 ;   f o n t - s t y l e : i t a l i c ; " > A g u a r d a n d o   l e i t u r a   d a s   p a r t e s . . . < / s m a l l > 
 
                                 < / d i v > 
 
                                 < d i v   i d = " l i n k s - e d i t a i s - c o n t a i n e r "   c l a s s = " h i d d e n "   s t y l e = " m a r g i n - t o p :   1 0 p x ;   b o r d e r - t o p :   1 p x   d a s h e d   # c c c ;   p a d d i n g - t o p :   1 0 p x ; " > 
 
                                         < l a b e l   s t y l e = " f o n t - w e i g h t : b o l d ;   f o n t - s i z e : 1 2 p x ;   c o l o r : # 5 b 2 1 b 6 ; " > E d i t a i s   D e t e c t a d o s   n a   T i m e l i n e : < / l a b e l > 
 
                                         < d i v   i d = " l i n k s - e d i t a i s - l i s t a " > < / d i v > 
 
                                 < / d i v > 
 
                         < / f i e l d s e t > 
 
 
 
                         < b u t t o n   c l a s s = " b t n - a c t i o n   b t n - g r a v a r "   i d = " b t n - g r a v a r " > G R A V A R   D E C I S % O   ( C o p i a r   p /   P J e ) < / b u t t o n > 
 
                 < / d i v > 
 
         < / d i v > 
 
         ` ; 
 
                 / /   C h e c k   r o b u s t o :   R e m o v e r   o v e r l a y   a n t i g o   s e   e x i s t i r   ( p r e v i n e   d u p l i c a % % o ) 
 
                 c o n s t   e x i s t i n g O v e r l a y   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' h o m o l o g a c a o - o v e r l a y ' ) ; 
 
                 i f   ( e x i s t i n g O v e r l a y )   { 
 
                         d b g ( ' O v e r l a y   j %   e x i s t e ,   r e m o v e n d o   v e r s % o   a n t i g a   a n t e s   d e   r e c r i a r ' ) ; 
 
                         e x i s t i n g O v e r l a y . r e m o v e ( ) ; 
 
                 } 
 
 
 
                 / /   I n s e r i r   H T M L   l i m p o 
 
                 d o c u m e n t . b o d y . i n s e r t A d j a c e n t H T M L ( ' b e f o r e e n d ' ,   h t m l M o d a l ) ; 
 
                 d b g ( ' O v e r l a y   H T M L   i n s e r i d o   n o   D O M . ' ) ; 
 
 
 
                 / /   T o g g l e   c o l a p s o / e x p a n s % o   d o   c a r d   d e   r e s u m o 
 
                 c o n s t   r e s u m o T o g g l e   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' r e s u m o - t o g g l e ' ) ; 
 
                 c o n s t   r e s u m o B o d y       =   d o c u m e n t . g e t E l e m e n t B y I d ( ' r e s u m o - b o d y ' ) ; 
 
                 c o n s t   r e s u m o S e t a       =   d o c u m e n t . g e t E l e m e n t B y I d ( ' r e s u m o - s e t a ' ) ; 
 
                 i f   ( r e s u m o T o g g l e   & &   r e s u m o B o d y )   { 
 
                         r e s u m o T o g g l e . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   ( )   = >   { 
 
                                 c o n s t   a b e r t o   =   r e s u m o B o d y . s t y l e . d i s p l a y   ! = =   ' n o n e ' ; 
 
                                 r e s u m o B o d y . s t y l e . d i s p l a y   =   a b e r t o   ?   ' n o n e '   :   ' b l o c k ' ; 
 
                                 i f   ( r e s u m o S e t a )   r e s u m o S e t a . t e x t C o n t e n t   =   a b e r t o   ?   '    '   :   '   ]%' ; 
 
                         } ) ; 
 
                 } 
 
 
 
                 i f   ( ! d o c u m e n t . g e t E l e m e n t B y I d ( ' h o m o l o g a c a o - o v e r l a y ' ) )   { 
 
                         e r r ( ' F a l h a   a p o s   i n s e r c a o :   h o m o l o g a c a o - o v e r l a y   n a o   e n c o n t r a d o . ' ) ; 
 
                         r e t u r n ; 
 
                 } 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   3 .   L % G I C A   D E   I N T E R F A C E   E   E V E N T O S   ( T O G G L E S ) 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 c o n s t   $   =   ( i d )   = >   d o c u m e n t . g e t E l e m e n t B y I d ( i d ) ; 
 
                 d b g ( ' B i n d i n g   d e   e v e n t o s   i n i c i a d o . ' ) ; 
 
               
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   F A S E   1 :   S i s t e m a   d e   F a s e s   d o   B o t % o 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 $ ( ' b t n - a b r i r - h o m o l o g a c a o ' ) . o n c l i c k   =   a s y n c   ( )   = >   { 
 
                         c o n s t   b t n   =   $ ( ' b t n - a b r i r - h o m o l o g a c a o ' ) ; 
 
                         c o n s t   i n p u t F i l e   =   $ ( ' i n p u t - p l a n i l h a - p d f ' ) ; 
 
                       
 
                         / /   F A S E   1 :   C a r r e g a r   P l a n i l h a   ( e s t a d o   i n i c i a l ) 
 
                         i f   ( ! w i n d o w . h c a l c S t a t e . p l a n i l h a C a r r e g a d a )   { 
 
                                 d b g ( ' F A S E   1 :   C l i q u e   e m   C a r r e g a r   P l a n i l h a ' ) ; 
 
                                 i n p u t F i l e . c l i c k ( ) ;   / /   A b r e   f i l e   p i c k e r 
 
                                 r e t u r n ; 
 
                         } 
 
                       
 
                         / /   F A S E   3 :   G e r a r   H o m o l o g a % % o   ( a p %%s   p l a n i l h a   c a r r e g a d a ) 
 
                         d b g ( ' F A S E   3 :   C l i q u e   e m   G e r a r   H o m o l o g a % % o ' ) ; 
 
                         t r y   { 
 
                                 / /   E x e c u t a r   p r e p . j s :   v a r r e d u r a   +   e x t r a % % o   d a   s e n t e n % a   +   A J - J T 
 
                                 c o n s t   p e r i t o s C o n h   =   w i n d o w . h c a l c P e r i t o s C o n h e c i m e n t o D e t e c t a d o s   | |   [ ] ; 
 
                                 c o n s t   p a r t e s D a t a   =   w i n d o w . h c a l c P a r t e s D a t a   | |   { } ; 
 
                                 c o n s t   p r e p   =   a w a i t   e x e c u t a r P r e p ( p a r t e s D a t a ,   p e r i t o s C o n h ) ; 
 
                               
 
                                 / /   C O R R E % % O   1 :   S a l v a r   g l o b a l m e n t e   p a r a   p r e e n c h e r D e p o s i t o s A u t o m a t i c o s 
 
                                 w i n d o w . h c a l c L a s t P r e p R e s u l t   =   p r e p ; 
 
 
 
                         / /   R e t r o c o m p a t :   m a n t e r   w i n d o w . h c a l c T i m e l i n e D a t a   p a r a   c o n s t r u i r S e c a o I n t i m a c o e s 
 
                         w i n d o w . h c a l c T i m e l i n e D a t a   =   { 
 
                                 s e n t e n c a :   p r e p . s e n t e n c a . d a t a   ?   {   d a t a :   p r e p . s e n t e n c a . d a t a ,   h r e f :   p r e p . s e n t e n c a . h r e f   }   :   n u l l , 
 
                                 a c o r d a o s :   p r e p . a c o r d a o s , 
 
                                 e d i t a i s :   p r e p . e d i t a i s 
 
                         } ; 
 
 
 
                         / /   S t r i k e t h r o u g h   n o   l a b e l   d e   d e p %%s i t o   r e c u r s a l   s e   n % o   h %   a c %%r d % o 
 
                         c o n s t   l a b e l D e p o s i t o   =   $ ( ' l a b e l - c h k - d e p o s i t o ' ) ; 
 
                         i f   ( l a b e l D e p o s i t o )   { 
 
                                 l a b e l D e p o s i t o . s t y l e . t e x t D e c o r a t i o n   =   p r e p . a c o r d a o s . l e n g t h   = = =   0   ?   ' l i n e - t h r o u g h '   :   ' n o n e ' ; 
 
                         } 
 
 
 
                         / /   L i n k   s e n t e n % a   ( i n f o   i n l i n e   n o   c a r d   d e   c u s t a s ) 
 
                         c o n s t   l i n k S e n t e n c a C o n t a i n e r   =   $ ( ' l i n k - s e n t e n c a - c o n t a i n e r ' ) ; 
 
                         i f   ( l i n k S e n t e n c a C o n t a i n e r )   { 
 
                                 l i n k S e n t e n c a C o n t a i n e r . i n n e r H T M L   =   ' ' ; 
 
                                 i f   ( p r e p . s e n t e n c a . d a t a )   { 
 
                                         c o n s t   i n f o   =   [ ] ; 
 
                                         i f   ( p r e p . s e n t e n c a . c u s t a s )   i n f o . p u s h ( ` C u s t a s :   R $ $ { p r e p . s e n t e n c a . c u s t a s } ` ) ; 
 
                                         i f   ( p r e p . s e n t e n c a . r e s p o n s a b i l i d a d e )   i n f o . p u s h ( ` R e s p :   $ { p r e p . s e n t e n c a . r e s p o n s a b i l i d a d e } ` ) ; 
 
 
 
                                         / /   H o n o r % r i o s   p e r i c i a i s :   p r i o r i z a   A J - J T ,   s %%  m o s t r a   s e n t e n % a   s e   n % o   t i v e r   A J - J T 
 
                                         i f   ( p r e p . p e r i c i a . p e r i t o s C o m A j J t . l e n g t h   >   0 )   { 
 
                                                 i n f o . p u s h ( ` H o n . P e r i c i a i s :   $ { p r e p . p e r i c i a . p e r i t o s C o m A j J t . l e n g t h }   A J - J T   d e t e c t a d o ( s ) ` ) ; 
 
                                         }   e l s e   i f   ( p r e p . s e n t e n c a . h o n o r a r i o s P e r i c i a i s . l e n g t h   >   0 )   { 
 
                                                 i n f o . p u s h ( ` H o n . P e r i c i a i s :   $ { p r e p . s e n t e n c a . h o n o r a r i o s P e r i c i a i s . m a p ( h   = >   ' R $ '   +   h . v a l o r   +   ( h . t r t   ?   '   ( T R T ) '   :   ' ' ) ) . j o i n ( ' ,   ' ) } ` ) ; 
 
                                         } 
 
 
 
                                         l i n k S e n t e n c a C o n t a i n e r . i n n e r H T M L   =   ` < s p a n   s t y l e = " f o n t - s i z e : 1 2 p x ;   c o l o r : # 1 6 a 3 4 a ; " >      S e n t e n % a :   $ { p r e p . s e n t e n c a . d a t a } $ { i n f o . l e n g t h   ?   '   |   '   +   i n f o . j o i n ( '   |   ' )   :   ' ' } < / s p a n > ` ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   L i n k s   c l i c % v e i s   d e   S e n t e n % a   e   A c %%r d % o   ( f i e l d s e t   s e p a r a d o ) 
 
                         c o n s t   l i n k S e n t e n c a A c o r d a o C o n t a i n e r   =   $ ( ' l i n k - s e n t e n c a - a c o r d a o - c o n t a i n e r ' ) ; 
 
                         i f   ( l i n k S e n t e n c a A c o r d a o C o n t a i n e r )   { 
 
                                 l i n k S e n t e n c a A c o r d a o C o n t a i n e r . i n n e r H T M L   =   ' ' ; 
 
                               
 
                                 / /   L i n k   d a   S e n t e n % a   ( f o c a   n a   t i m e l i n e ) 
 
                                 i f   ( p r e p . s e n t e n c a . h r e f )   { 
 
                                         c o n s t   s e n t e n c a L i n k   =   d o c u m e n t . c r e a t e E l e m e n t ( ' a ' ) ; 
 
                                         s e n t e n c a L i n k . h r e f   =   ' # ' ; 
 
                                         s e n t e n c a L i n k . i n n e r H T M L   =   ` < i   c l a s s = " f a s   f a - c r o s s h a i r s " > < / i >   S e n t e n % a $ { p r e p . s e n t e n c a . d a t a   ?   '   -   '   +   p r e p . s e n t e n c a . d a t a   :   ' ' } ` ; 
 
                                         s e n t e n c a L i n k . s t y l e . c s s T e x t   =   ' d i s p l a y : b l o c k ;   c o l o r : # 1 6 a 3 4 a ;   f o n t - s i z e : 1 2 p x ;   m a r g i n - b o t t o m : 5 p x ;   t e x t - d e c o r a t i o n : n o n e ;   f o n t - w e i g h t : 6 0 0 ;   c u r s o r : p o i n t e r ; ' ; 
 
                                         s e n t e n c a L i n k . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   ( e )   = >   { 
 
                                                 e . p r e v e n t D e f a u l t ( ) ; 
 
                                                 d e s t a c a r E l e m e n t o N a T i m e l i n e ( p r e p . s e n t e n c a . h r e f ) ; 
 
                                         } ) ; 
 
                                         l i n k S e n t e n c a A c o r d a o C o n t a i n e r . a p p e n d C h i l d ( s e n t e n c a L i n k ) ; 
 
                                 } 
 
                               
 
                                 / /   L i n k s   d e   A c %%r d % o s 
 
                                 i f   ( p r e p . a c o r d a o s . l e n g t h   >   0 )   { 
 
                                         p r e p . a c o r d a o s . f o r E a c h ( ( a c o r d a o ,   i )   = >   { 
 
                                                 i f   ( a c o r d a o . h r e f )   { 
 
                                                         c o n s t   l b l   =   p r e p . a c o r d a o s . l e n g t h   >   1   ?   ` A c %%r d % o   $ { i   +   1 } `   :   ` A c %%r d % o ` ; 
 
                                                         c o n s t   a   =   d o c u m e n t . c r e a t e E l e m e n t ( ' a ' ) ; 
 
                                                         a . h r e f   =   ' # ' ; 
 
                                                         a . i n n e r H T M L   =   ` < i   c l a s s = " f a s   f a - c r o s s h a i r s " > < / i >   $ { l b l } $ { a c o r d a o . d a t a   ?   '   -   '   +   a c o r d a o . d a t a   :   ' ' } ` ; 
 
                                                         a . s t y l e . c s s T e x t   =   " d i s p l a y : b l o c k ;   c o l o r : # 0 0 5 0 9 e ;   f o n t - s i z e : 1 2 p x ;   m a r g i n - t o p : 5 p x ;   t e x t - d e c o r a t i o n : n o n e ;   c u r s o r : p o i n t e r ; " ; 
 
                                                         a . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   ( e )   = >   { 
 
                                                                 e . p r e v e n t D e f a u l t ( ) ; 
 
                                                                 d e s t a c a r E l e m e n t o N a T i m e l i n e ( a c o r d a o . h r e f ) ; 
 
                                                         } ) ; 
 
                                                         l i n k S e n t e n c a A c o r d a o C o n t a i n e r . a p p e n d C h i l d ( a ) ; 
 
                                                 } 
 
                                         } ) ; 
 
                                       
 
                                         / /   R E C U R S O S   C O M   A N E X O S   ( i n t e g r a d o   d e   r e c . j s   v 1 . 0 ) 
 
                                         i f   ( p r e p . d e p o s i t o s . l e n g t h   >   0 )   { 
 
                                                 c o n s t   r e c D i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                                                 r e c D i v . s t y l e . c s s T e x t   =   ' m a r g i n - t o p : 8 p x ;   p a d d i n g : 6 p x ;   b a c k g r o u n d : # f f f d e 7 ;   b o r d e r : 1 p x   s o l i d   # f b b f 2 4 ;   b o r d e r - r a d i u s : 4 p x ; ' ; 
 
                                                 r e c D i v . i n n e r H T M L   =   ` < s t r o n g   s t y l e = " f o n t - s i z e : 1 1 p x ; c o l o r : # 9 2 4 0 0 e " >      R e c u r s o s   d a s   R e c l a m a d a s   ( $ { p r e p . d e p o s i t o s . l e n g t h } ) < / s t r o n g > ` ; 
 
 
 
                                                 p r e p . d e p o s i t o s . f o r E a c h ( ( d e p ,   d e p I d x )   = >   { 
 
                                                         c o n s t   c a r d   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                                                         c a r d . c l a s s N a m e   =   ' r e c - r e c u r s o - c a r d ' ; 
 
                                                         c a r d . d a t a s e t . h r e f   =   d e p . h r e f   | |   ' ' ; 
 
 
 
                                                         c o n s t   c o r B a d g e   =   {   ' D e p %%s i t o ' :   ' # 1 0 b 9 8 1 ' ,   ' G a r a n t i a ' :   ' # f 5 9 e 0 b ' ,   ' C u s t a s ' :   ' # e f 4 4 4 4 ' ,   ' A n e x o ' :   ' # 6 b 7 2 8 0 '   } ; 
 
 
 
                                                         l e t   a n e x o s H t m l   =   ' ' ; 
 
                                                         i f   ( d e p . a n e x o s   & &   d e p . a n e x o s . l e n g t h   >   0 )   { 
 
                                                                 a n e x o s H t m l   =   ` < d i v   c l a s s = " r e c - a n e x o s - l i s t a " > `   + 
 
                                                                         d e p . a n e x o s . m a p ( ( a x ,   a x I d x )   = > 
 
                                                                                 ` < d i v   c l a s s = " r e c - a n e x o - i t e m "   d a t a - d e p - i d x = " $ { d e p I d x } "   d a t a - a x - i d x = " $ { a x I d x } " > 
 
                                                                                         < s p a n   c l a s s = " r e c - a n e x o - b a d g e "   s t y l e = " b a c k g r o u n d : $ { c o r B a d g e [ a x . t i p o ]   | |   ' # 6 b 7 2 8 0 ' } " > $ { a x . t i p o } < / s p a n > 
 
                                                                                         < c o d e   c l a s s = " r e c - a n e x o - i d " > $ { a x . i d   | |   ' s e m   i d ' } < / c o d e > 
 
                                                                                         < s p a n   s t y l e = " f o n t - s i z e : 1 0 p x ; c o l o r : # 6 b 7 2 8 0 ; o v e r f l o w : h i d d e n ; t e x t - o v e r f l o w : e l l i p s i s ; w h i t e - s p a c e : n o w r a p ; m a x - w i d t h : 1 2 0 p x "   t i t l e = " $ { a x . t e x t o } " > $ { a x . t e x t o . s u b s t r i n g ( 0 , 4 0 ) } < / s p a n > 
 
                                                                                 < / d i v > ` 
 
                                                                         ) . j o i n ( ' ' )   + 
 
                                                                 ` < / d i v > ` ; 
 
                                                         } 
 
 
 
                                                         c a r d . i n n e r H T M L   =   ` 
 
                                                                 < d i v   s t y l e = " d i s p l a y : f l e x ; a l i g n - i t e m s : c e n t e r ; g a p : 6 p x ; m a r g i n - b o t t o m : 3 p x " > 
 
                                                                         < s p a n   c l a s s = " r e c - t i p o - b a d g e " > $ { d e p . t i p o   | |   ' R O ' } < / s p a n > 
 
                                                                         < s p a n   s t y l e = " f o n t - s i z e : 1 1 p x ; c o l o r : # 9 2 4 0 0 e ; f o n t - w e i g h t : 6 0 0 ; f l e x : 1 " > $ { d e p . d e p o s i t a n t e   | |   ' P a r t e   n % o   i d e n t i f i c a d a ' } < / s p a n > 
 
                                                                         < s p a n   s t y l e = " f o n t - s i z e : 1 0 p x ; c o l o r : # 6 b 7 2 8 0 " > $ { d e p . d a t a   | |   ' s e m   d a t a ' } < / s p a n > 
 
                                                                         $ { d e p . a n e x o s   & &   d e p . a n e x o s . l e n g t h   >   0   ?   ` < s p a n   c l a s s = " r e c - s e t a - t o g g l e " >      $ { d e p . a n e x o s . l e n g t h }   a n e x o $ { d e p . a n e x o s . l e n g t h   >   1   ?   ' s '   :   ' ' } < / s p a n > `   :   ' ' } 
 
                                                                 < / d i v > 
 
                                                                 $ { a n e x o s H t m l } ` ; 
 
 
 
                                                         c a r d . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   e   = >   { 
 
                                                                 c o n s t   a x I t e m   =   e . t a r g e t . c l o s e s t ( ' . r e c - a n e x o - i t e m ' ) ; 
 
                                                                 i f   ( a x I t e m )   { 
 
                                                                         e . s t o p P r o p a g a t i o n ( ) ; 
 
                                                                         c o n s t   a x I d x   =   p a r s e I n t ( a x I t e m . d a t a s e t . a x I d x ,   1 0 ) ; 
 
                                                                         c o n s t   a x   =   d e p . a n e x o s [ a x I d x ] ; 
 
                                                                         i f   ( ! a x )   r e t u r n ; 
 
 
 
                                                                         / /   1 .   D e s t a c a r   o   r e c u r s o   n a   t i m e l i n e 
 
                                                                         i f   ( d e p . h r e f )   t r y   {   d e s t a c a r E l e m e n t o N a T i m e l i n e ( d e p . h r e f ) ;   }   c a t c h ( e 2 )   {   c o n s o l e . e r r o r ( ' [ h c a l c ] ' ,   e 2 ) ;   } 
 
 
 
                                                                         / /   2 .   R e - e n c o n t r a r   e   c l i c a r   n o   a n e x o   ( e v i t a   r e f e r % n c i a   s t a l e   d o   A n g u l a r ) 
 
                                                                         s e t T i m e o u t ( a s y n c   ( )   = >   { 
 
                                                                                 t r y   { 
 
                                                                                         c o n s t   i t e m   =   e n c o n t r a r I t e m T i m e l i n e ( d e p . h r e f ) ; 
 
                                                                                         i f   ( i t e m )   { 
 
                                                                                                 a w a i t   e x p a n d i r A n e x o s ( i t e m ) ; 
 
                                                                                                 c o n s t   l i n k s   =   i t e m . q u e r y S e l e c t o r A l l ( ' a . t l - d o c u m e n t o [ i d ^ = " a n e x o _ " ] ' ) ; 
 
                                                                                                 l e t   a l v o   =   n u l l ; 
 
                                                                                                 i f   ( a x . i d )   { 
 
                                                                                                         a l v o   =   A r r a y . f r o m ( l i n k s ) . f i n d ( l   = >   l . t e x t C o n t e n t . i n c l u d e s ( a x . i d ) ) ; 
 
                                                                                                 } 
 
                                                                                                 a l v o   =   a l v o   | |   l i n k s [ a x I d x ]   | |   l i n k s [ 0 ] ; 
 
                                                                                                 i f   ( a l v o )   a l v o . d i s p a t c h E v e n t ( n e w   M o u s e E v e n t ( ' c l i c k ' ,   {   b u b b l e s :   t r u e ,   c a n c e l a b l e :   t r u e   } ) ) ; 
 
                                                                                         }   e l s e   i f   ( a x . e l e m e n t o   & &   a x . e l e m e n t o . i s C o n n e c t e d )   { 
 
                                                                                                 a x . e l e m e n t o . d i s p a t c h E v e n t ( n e w   M o u s e E v e n t ( ' c l i c k ' ,   {   b u b b l e s :   t r u e ,   c a n c e l a b l e :   t r u e   } ) ) ; 
 
                                                                                         } 
 
                                                                                 }   c a t c h ( e 3 )   {   c o n s o l e . e r r o r ( ' [ h c a l c ]   E r r o   a o   c l i c a r   n o   a n e x o : ' ,   e 3 ) ;   } 
 
                                                                         } ,   6 0 0 ) ; 
 
                                                                         r e t u r n ; 
 
                                                                 } 
 
 
 
                                                                 c a r d . c l a s s L i s t . t o g g l e ( ' e x p a n d i d o ' ) ; 
 
                                                                 c o n s t   s e t a   =   c a r d . q u e r y S e l e c t o r ( ' . r e c - s e t a - t o g g l e ' ) ; 
 
                                                                 i f   ( s e t a )   s e t a . t e x t C o n t e n t   =   c a r d . c l a s s L i s t . c o n t a i n s ( ' e x p a n d i d o ' ) 
 
                                                                         ?   ` \ u 2 5 b c   $ { d e p . a n e x o s . l e n g t h }   a n e x o $ { d e p . a n e x o s . l e n g t h   >   1   ?   ' s '   :   ' ' } ` 
 
                                                                         :   ` \ u 2 5 b 6   $ { d e p . a n e x o s . l e n g t h }   a n e x o $ { d e p . a n e x o s . l e n g t h   >   1   ?   ' s '   :   ' ' } ` ; 
 
                                                                 i f   ( d e p . h r e f )   t r y   {   d e s t a c a r E l e m e n t o N a T i m e l i n e ( d e p . h r e f ) ;   }   c a t c h ( e 2 )   {   c o n s o l e . e r r o r ( ' [ h c a l c ] ' ,   e 2 ) ;   } 
 
                                                         } ) ; 
 
 
 
                                                         r e c D i v . a p p e n d C h i l d ( c a r d ) ; 
 
                                                 } ) ; 
 
 
 
                                                 l i n k S e n t e n c a A c o r d a o C o n t a i n e r . a p p e n d C h i l d ( r e c D i v ) ; 
 
                                         } 
 
                                 }   e l s e   { 
 
                                         / /   A v i s o   q u a n d o   n % o   h %   a c %%r d % o 
 
                                         c o n s t   a v i s o D i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                                         a v i s o D i v . s t y l e . c s s T e x t   =   ' m a r g i n - t o p : 8 p x ;   p a d d i n g : 8 p x ;   b a c k g r o u n d : # f e f 2 f 2 ;   b o r d e r : 1 p x   s o l i d   # e f 4 4 4 4 ;   b o r d e r - r a d i u s : 4 p x ; ' ; 
 
                                         a v i s o D i v . i n n e r H T M L   =   ` < s p a n   s t y l e = " f o n t - s i z e : 1 2 p x ;   c o l o r : # d c 2 6 2 6 ;   f o n t - w e i g h t : 6 0 0 ; " >      N % o   h %   A c %%r d % o < / s p a n > ` ; 
 
                                         l i n k S e n t e n c a A c o r d a o C o n t a i n e r . a p p e n d C h i l d ( a v i s o D i v ) ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   P r e e n c h e r   c u s t a s   a u t o m a t i c a m e n t e   -   P R I O R I Z A   P L A N I L H A 
 
                         i f   ( w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ? . c u s t a s   & &   $ ( ' v a l - c u s t a s ' ) )   { 
 
                                 $ ( ' v a l - c u s t a s ' ) . v a l u e   =   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a . c u s t a s ; 
 
                                 / /   F I X :   s e m   a c %%r d % o        c u s t a s   s % o   d a   s e n t e n % a        d a t a   =   s e n t e n % a 
 
                                 c o n s t   s e m A c o r d a o   =   p r e p . a c o r d a o s . l e n g t h   = = =   0 ; 
 
                                 i f   ( s e m A c o r d a o   & &   p r e p . s e n t e n c a . d a t a   & &   $ ( ' c u s t a s - d a t a - o r i g e m ' ) )   { 
 
                                         $ ( ' c u s t a s - d a t a - o r i g e m ' ) . v a l u e   =   p r e p . s e n t e n c a . d a t a ; 
 
                                 }   e l s e   i f   ( w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a . d a t a A t u a l i z a c a o   & &   $ ( ' c u s t a s - d a t a - o r i g e m ' ) )   { 
 
                                         $ ( ' c u s t a s - d a t a - o r i g e m ' ) . v a l u e   =   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a . d a t a A t u a l i z a c a o ; 
 
                                 } 
 
                         }   e l s e   i f   ( p r e p . s e n t e n c a . c u s t a s   & &   $ ( ' v a l - c u s t a s ' ) )   { 
 
                                 $ ( ' v a l - c u s t a s ' ) . v a l u e   =   p r e p . s e n t e n c a . c u s t a s ; 
 
                                 / /   D a t a   d a s   c u s t a s   =   d a t a   d a   s e n t e n % a   ( a p e n a s   s e   n % o   h %   p l a n i l h a ) 
 
                                 i f   ( p r e p . s e n t e n c a . d a t a   & &   $ ( ' c u s t a s - d a t a - o r i g e m ' ) )   { 
 
                                         $ ( ' c u s t a s - d a t a - o r i g e m ' ) . v a l u e   =   p r e p . s e n t e n c a . d a t a ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   D e p %%s i t o   r e c u r s a l :   v i s % v e l   s e   t e m   a c %%r d % o s 
 
                         c o n s t   f i e l d s e t D e p o s i t o   =   $ ( ' f i e l d s e t - d e p o s i t o ' ) ; 
 
                         i f   ( p r e p . a c o r d a o s . l e n g t h   = = =   0 )   { 
 
                                 i f   ( f i e l d s e t D e p o s i t o )   f i e l d s e t D e p o s i t o . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                         }   e l s e   { 
 
                                 i f   ( f i e l d s e t D e p o s i t o )   f i e l d s e t D e p o s i t o . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                         } 
 
 
 
                         / /   P o v o a r   s e l e c t   d e   a c %%r d % o s   s e   e x i s t i r e m 
 
                         c o n s t   c u s t a s A c o r d a o S e l e c t   =   $ ( ' c u s t a s - a c o r d a o - s e l e c t ' ) ; 
 
                         i f   ( c u s t a s A c o r d a o S e l e c t   & &   p r e p . a c o r d a o s . l e n g t h   >   0 )   { 
 
                                 c u s t a s A c o r d a o S e l e c t . i n n e r H T M L   =   ' < o p t i o n   v a l u e = " " > S e l e c i o n e   o   a c %%r d % o < / o p t i o n > ' ; 
 
                                 p r e p . a c o r d a o s . f o r E a c h ( ( a c o r d a o ,   i )   = >   { 
 
                                         c o n s t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ; 
 
                                         o p t . v a l u e   =   i ; 
 
                                         o p t . t e x t C o n t e n t   =   ` A c %%r d % o   $ { i   +   1 } $ { a c o r d a o . d a t a   ?   '   -   '   +   a c o r d a o . d a t a   :   ' ' } ` ; 
 
                                         o p t . d a t a s e t . d a t a   =   a c o r d a o . d a t a   | |   ' ' ; 
 
                                         o p t . d a t a s e t . i d   =   a c o r d a o . i d   | |   ' ' ; 
 
                                         c u s t a s A c o r d a o S e l e c t . a p p e n d C h i l d ( o p t ) ; 
 
                                 } ) ; 
 
                         } 
 
 
 
                         / /   E d i t a i s 
 
                         c o n s t   e d i t a i s C o n t a i n e r   =   $ ( ' l i n k s - e d i t a i s - c o n t a i n e r ' ) ; 
 
                         c o n s t   e d i t a i s L i s t a   =   $ ( ' l i n k s - e d i t a i s - l i s t a ' ) ; 
 
                         i f   ( e d i t a i s C o n t a i n e r   & &   e d i t a i s L i s t a )   { 
 
                                 e d i t a i s L i s t a . i n n e r H T M L   =   ' ' ; 
 
                                 i f   ( p r e p . e d i t a i s . l e n g t h   >   0 )   { 
 
                                         e d i t a i s C o n t a i n e r . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                         p r e p . e d i t a i s . f o r E a c h ( ( e d i t a l ,   i )   = >   { 
 
                                                 i f   ( e d i t a l . h r e f )   { 
 
                                                         c o n s t   b t n   =   d o c u m e n t . c r e a t e E l e m e n t ( ' a ' ) ; 
 
                                                         b t n . h r e f   =   e d i t a l . h r e f ; 
 
                                                         b t n . t a r g e t   =   " _ b l a n k " ; 
 
                                                         b t n . i n n e r H T M L   =   ` < i   c l a s s = " f a s   f a - e x t e r n a l - l i n k - a l t " > < / i >   E d i t a l   $ { i   +   1 } ` ; 
 
                                                         b t n . s t y l e . c s s T e x t   =   " d i s p l a y : i n l i n e - b l o c k ;   m a r g i n - r i g h t : 1 0 p x ;   c o l o r : # 0 0 5 0 9 e ;   f o n t - s i z e : 1 2 p x ;   t e x t - d e c o r a t i o n : n o n e ; " ; 
 
                                                         e d i t a i s L i s t a . a p p e n d C h i l d ( b t n ) ; 
 
                                                 } 
 
                                         } ) ; 
 
                                 }   e l s e   { 
 
                                         e d i t a i s C o n t a i n e r . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                         / /   R E G R A S   A U T O - P R E E N C H I M E N T O   ( p r e p   s o b r e p % e   d e f a u l t s ) 
 
                         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 
 
                         / /   R E G R A   1 :   D e p %%s i t o   r e c u r s a l        d i s p a r a r   e v e n t o   o n C h a n g e   p a r a   u n i f i c a r   f l u x o 
 
                         / /   C O R R E % % O   2 :   U s a r   d i s p a t c h E v e n t   e m   v e z   d e   m a n i p u l a % % o   d i r e t a   d o   D O M 
 
                         i f   ( p r e p . d e p o s i t o s . l e n g t h   >   0 )   { 
 
                                 c o n s o l e . l o g ( ' [ I N I C I A L I Z A % % O ]   D e t e c t a d o s ' ,   p r e p . d e p o s i t o s . l e n g t h ,   ' r e c u r s o s   c o m   d e p %%s i t o / g a r a n t i a ' ) ; 
 
                               
 
                                 c o n s t   c h k D e p   =   $ ( ' c h k - d e p o s i t o ' ) ; 
 
                                 i f   ( c h k D e p )   { 
 
                                         c h k D e p . c h e c k e d   =   t r u e ; 
 
                                         / /   D i s p a r a r   o n C h a n g e   s i n t % t i c o        a c i o n a   v i s i b i l i d a d e   E   p r e e n c h e r D e p o s i t o s A u t o m a t i c o s 
 
                                         / /   d e   f o r m a   u n i f i c a d a ,   e l i m i n a n d o   d e s s i n c r o n i z a % % o 
 
                                         c h k D e p . d i s p a t c h E v e n t ( n e w   E v e n t ( ' c h a n g e ' ,   {   b u b b l e s :   t r u e   } ) ) ; 
 
                                         c o n s o l e . l o g ( ' [ I N I C I A L I Z A % % O ]   E v e n t o   c h a n g e   d i s p a r a d o ' ) ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   R E G R A   2 :   P e r i t o   c o n h e c i m e n t o   +   T R T   /   A J - J T   m a t c h 
 
                         c o n s t   p e r i t o T i p o E l   =   $ ( ' p e r i t o - t i p o - p a g ' ) ; 
 
                         c o n s t   p e r i t o V a l o r E l   =   $ ( ' v a l - p e r i t o - v a l o r ' ) ; 
 
                         c o n s t   p e r i t o D a t a E l   =   $ ( ' v a l - p e r i t o - d a t a ' ) ; 
 
                         i f   ( p r e p . p e r i c i a . p e r i t o s C o m A j J t . l e n g t h   >   0 )   { 
 
                                 / /   P e r i t o   c a s o u   c o m   A J - J T        p a g o   p e l o   T R T 
 
                                 c o n s t   m a t c h   =   p r e p . p e r i c i a . p e r i t o s C o m A j J t [ 0 ] ; 
 
                                 i f   ( p e r i t o T i p o E l )   p e r i t o T i p o E l . v a l u e   =   ' t r t ' ; 
 
                                 i f   ( p e r i t o V a l o r E l )   p e r i t o V a l o r E l . v a l u e   =   m a t c h . i d A j J t   | |   ' ' ; 
 
                         }   e l s e   i f   ( p r e p . s e n t e n c a . h o n o r a r i o s P e r i c i a i s . l e n g t h   >   0 )   { 
 
                                 / /   H o n o r % r i o s   p e r i c i a i s   n a   s e n t e n % a 
 
                                 c o n s t   h o n   =   p r e p . s e n t e n c a . h o n o r a r i o s P e r i c i a i s [ 0 ] ; 
 
                                 i f   ( h o n . t r t   & &   p e r i t o T i p o E l )   { 
 
                                         p e r i t o T i p o E l . v a l u e   =   ' t r t ' ; 
 
                                 } 
 
                                 / /   S e m p r e   p r e e n c h e r   v a l o r   s e   d e t e c t a d o 
 
                                 i f   ( p e r i t o V a l o r E l   & &   ! p e r i t o V a l o r E l . v a l u e )   { 
 
                                         p e r i t o V a l o r E l . v a l u e   =   ' R $ '   +   h o n . v a l o r ; 
 
                                 } 
 
                         } 
 
                         / /   D a t a   d a   s e n t e n % a   n o   c a m p o   d e   d a t a   d o   p e r i t o 
 
                         i f   ( p r e p . s e n t e n c a . d a t a   & &   p e r i t o D a t a E l   & &   ! p e r i t o D a t a E l . v a l u e )   { 
 
                                 p e r i t o D a t a E l . v a l u e   =   p r e p . s e n t e n c a . d a t a ; 
 
                         } 
 
 
 
                         / /   R E G R A   3   e   4 :   R e s p o n s a b i l i d a d e   ( s u b s i d i % r i a   /   s o l i d % r i a ) 
 
                         c o n s t   r e s p T i p o E l   =   $ ( ' r e s p - t i p o ' ) ; 
 
                         c o n s t   r e s p S u b O p c o e s   =   $ ( ' r e s p - s u b - o p c o e s ' ) ; 
 
                         c o n s t   p a s s i v o   =   w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o   | |   [ ] ; 
 
                         i f   ( p r e p . s e n t e n c a . r e s p o n s a b i l i d a d e   & &   r e s p T i p o E l )   { 
 
                                 i f   ( p r e p . s e n t e n c a . r e s p o n s a b i l i d a d e   = = =   ' s u b s i d i a r i a ' )   { 
 
                                         r e s p T i p o E l . v a l u e   =   ' s u b s i d i a r i a s ' ; 
 
                                         i f   ( r e s p S u b O p c o e s )   r e s p S u b O p c o e s . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                 }   e l s e   i f   ( p r e p . s e n t e n c a . r e s p o n s a b i l i d a d e   = = =   ' s o l i d a r i a ' )   { 
 
                                         r e s p T i p o E l . v a l u e   =   ' s o l i d a r i a s ' ; 
 
                                         i f   ( r e s p S u b O p c o e s )   r e s p S u b O p c o e s . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                                 } 
 
                         }   e l s e   i f   ( p a s s i v o . l e n g t h   < =   1   & &   r e s p T i p o E l )   { 
 
                                 r e s p T i p o E l . v a l u e   =   ' u n i c a ' ; 
 
                                 i f   ( r e s p S u b O p c o e s )   r e s p S u b O p c o e s . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                         } 
 
 
 
                         / /   R E G R A   5 :   C u s t a s 
 
                         / /   S e m p r e   p a d r % o   =   s e n t e n % a   ( u s u % r i o   p o d e   m u d a r   p a r a   a c %%r d % o   s e   n e c e s s % r i o ) 
 
                         c o n s t   c u s t a s S t a t u s E l   =   $ ( ' c u s t a s - s t a t u s ' ) ; 
 
                         c o n s t   c u s t a s O r i g e m E l   =   $ ( ' c u s t a s - o r i g e m ' ) ; 
 
                         i f   ( p r e p . s e n t e n c a . c u s t a s )   { 
 
                                 / /   A T E N % % O :   N % o   s o b r e p % e   s e   p l a n i l h a   j %   p r e e n c h e u   c u s t a s 
 
                                 i f   ( $ ( ' v a l - c u s t a s ' )   & &   ! w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ? . c u s t a s )   { 
 
                                         $ ( ' v a l - c u s t a s ' ) . v a l u e   =   p r e p . s e n t e n c a . c u s t a s ; 
 
                                 } 
 
                                 / /   S e m p r e   u s a   s e n t e n % a   c o m o   p a d r % o 
 
                                 i f   ( c u s t a s S t a t u s E l )   c u s t a s S t a t u s E l . v a l u e   =   ' d e v i d a s ' ; 
 
                                 i f   ( c u s t a s O r i g e m E l )   c u s t a s O r i g e m E l . v a l u e   =   ' s e n t e n c a ' ; 
 
                                 / /   A T E N % % O :   N % o   s o b r e p % e   d a t a   s e   p l a n i l h a   j %   p r e e n c h e u 
 
                                 i f   ( $ ( ' c u s t a s - d a t a - o r i g e m ' )   & &   p r e p . s e n t e n c a . d a t a   & &   ! w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ? . c u s t a s )   { 
 
                                         $ ( ' c u s t a s - d a t a - o r i g e m ' ) . v a l u e   =   p r e p . s e n t e n c a . d a t a ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   R E G R A   6 :   h s u s p        H o n o r % r i o s   A d v .   R % u   c o m   c o n d i % % o   s u s p e n s i v a 
 
                         c o n s t   c h k H o n R e u   =   $ ( ' c h k - h o n - r e u ' ) ; 
 
                         c o n s t   h o n R e u C a m p o s   =   $ ( ' h o n - r e u - c a m p o s ' ) ; 
 
                         i f   ( p r e p . s e n t e n c a . h s u s p )   { 
 
                                 / /   L %%g i c a   i n v e r t i d a :   d e s m a r c a r   " N % o   h % "   p a r a   m o s t r a r   c a m p o s 
 
                                 i f   ( c h k H o n R e u )   c h k H o n R e u . c h e c k e d   =   f a l s e ; 
 
                                 i f   ( h o n R e u C a m p o s )   h o n R e u C a m p o s . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
 
 
                                 c o n s t   r a d S u s p   =   d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " r a d - h o n - r e u " ] [ v a l u e = " s u s p e n s i v a " ] ' ) ; 
 
                                 i f   ( r a d S u s p )   r a d S u s p . c h e c k e d   =   t r u e ; 
 
                         }   e l s e   { 
 
                                 / /   E s t a d o   p a d r % o :   c h e c k b o x   m a r c a d o ,   c a m p o s   o c u l t o s 
 
                                 i f   ( c h k H o n R e u )   c h k H o n R e u . c h e c k e d   =   t r u e ; 
 
                                 i f   ( h o n R e u C a m p o s )   h o n R e u C a m p o s . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                         } 
 
 
 
                                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                                 / /   P R E E N C H E R   C O M   D A D O S   D A   P L A N I L H A   ( P R I O R I D A D E ) 
 
                                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                                 i f   ( w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a )   { 
 
                                         c o n s t   d a d o s   =   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ; 
 
                                       
 
                                         i f   ( d a d o s . i d P l a n i l h a   & &   $ ( ' v a l - i d ' ) )   $ ( ' v a l - i d ' ) . v a l u e   =   d a d o s . i d P l a n i l h a ; 
 
                                         i f   ( d a d o s . v e r b a s   & &   $ ( ' v a l - c r e d i t o ' ) )   $ ( ' v a l - c r e d i t o ' ) . v a l u e   =   d a d o s . v e r b a s ; 
 
                                       
 
                                         / /   F G T S :   p r e e n c h e r   v a l o r   +   a j u s t a r   c h e c k b o x   +   m a r c a r   s t a t u s   d e p o s i t a d o   c o n f o r m e   e x t r a % % o 
 
                                         i f   ( $ ( ' v a l - f g t s ' )   & &   $ ( ' c a l c - f g t s ' ) )   { 
 
                                                 c o n s t   t e m F g t s   =   d a d o s . f g t s   & &   d a d o s . f g t s   ! = =   ' 0 , 0 0 '   & &   d a d o s . f g t s   ! = =   ' 0 ' ; 
 
                                               
 
                                                 i f   ( t e m F g t s )   { 
 
                                                         $ ( ' v a l - f g t s ' ) . v a l u e   =   d a d o s . f g t s ; 
 
                                                         $ ( ' c a l c - f g t s ' ) . c h e c k e d   =   t r u e ; 
 
                                                       
 
                                                         / /   M a r c a r   r a d i o   b u t t o n   c o r r e t o   ( d e p o s i t a d o   o u   d e v i d o ) 
 
                                                         i f   ( d a d o s . f g t s D e p o s i t a d o )   { 
 
                                                                 c o n s t   r a d D e p o s i t a d o   =   d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " f g t s - t i p o " ] [ v a l u e = " d e p o s i t a d o " ] ' ) ; 
 
                                                                 i f   ( r a d D e p o s i t a d o )   r a d D e p o s i t a d o . c h e c k e d   =   t r u e ; 
 
                                                         }   e l s e   { 
 
                                                                 c o n s t   r a d D e v i d o   =   d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " f g t s - t i p o " ] [ v a l u e = " d e v i d o " ] ' ) ; 
 
                                                                 i f   ( r a d D e v i d o )   r a d D e v i d o . c h e c k e d   =   t r u e ; 
 
                                                         } 
 
                                                 }   e l s e   { 
 
                                                         / /   S e m   F G T S   d e t e c t a d o        d e s m a r c a r   c h e c k b o x   ( q u e   v e m   m a r c a d o   p o r   p a d r % o ) 
 
                                                         $ ( ' c a l c - f g t s ' ) . c h e c k e d   =   f a l s e ; 
 
                                                 } 
 
                                                 $ ( ' c a l c - f g t s ' ) . d i s p a t c h E v e n t ( n e w   E v e n t ( ' c h a n g e ' ,   {   b u b b l e s :   t r u e   } ) ) ; 
 
                                         } 
 
                                       
 
                                         / /   I N S S :   p r e e n c h e r   v a l o r e s   +   a j u s t a r   c h e c k b o x   s e   n % o   h %   n e n h u m 
 
                                         i f   ( d a d o s . i n s s T o t a l   & &   $ ( ' v a l - i n s s - t o t a l ' ) )   $ ( ' v a l - i n s s - t o t a l ' ) . v a l u e   =   d a d o s . i n s s T o t a l ; 
 
                                         i f   ( d a d o s . i n s s A u t o r   & &   $ ( ' v a l - i n s s - r e c ' ) )   $ ( ' v a l - i n s s - r e c ' ) . v a l u e   =   d a d o s . i n s s A u t o r ; 
 
                                       
 
                                         / /   V e r i f i c a r   s e   n % o   h %   I N S S   n e n h u m 
 
                                         c o n s t   s e m I n s s T o t a l   =   ! d a d o s . i n s s T o t a l   | |   d a d o s . i n s s T o t a l   = = =   ' 0 , 0 0 '   | |   d a d o s . i n s s T o t a l   = = =   ' 0 ' ; 
 
                                         c o n s t   s e m I n s s A u t o r   =   ! d a d o s . i n s s A u t o r   | |   d a d o s . i n s s A u t o r   = = =   ' 0 , 0 0 '   | |   d a d o s . i n s s A u t o r   = = =   ' 0 ' ; 
 
                                       
 
                                         i f   ( s e m I n s s T o t a l   & &   s e m I n s s A u t o r   & &   $ ( ' i g n o r a r - i n s s ' ) )   { 
 
                                                 $ ( ' i g n o r a r - i n s s ' ) . c h e c k e d   =   t r u e ; 
 
                                                 $ ( ' i g n o r a r - i n s s ' ) . d i s p a t c h E v e n t ( n e w   E v e n t ( ' c h a n g e ' ,   {   b u b b l e s :   t r u e   } ) ) ; 
 
                                         } 
 
                                       
 
                                         / /   C u s t a s :   v a l o r   e   d a t a   d a   p l a n i l h a   ( p r e v a l e c e   s o b r e   s e n t e n % a ) 
 
                                         i f   ( d a d o s . c u s t a s   & &   $ ( ' v a l - c u s t a s ' ) )   { 
 
                                                 $ ( ' v a l - c u s t a s ' ) . v a l u e   =   d a d o s . c u s t a s ; 
 
                                                 / /   D a t a   d a s   c u s t a s   =   d a t a   d e   l i q u i d a % % o   d a   p l a n i l h a 
 
                                                 i f   ( d a d o s . d a t a A t u a l i z a c a o   & &   $ ( ' c u s t a s - d a t a - o r i g e m ' ) )   { 
 
                                                         $ ( ' c u s t a s - d a t a - o r i g e m ' ) . v a l u e   =   d a d o s . d a t a A t u a l i z a c a o ; 
 
                                                 } 
 
                                         } 
 
                                       
 
                                         i f   ( d a d o s . d a t a A t u a l i z a c a o   & &   $ ( ' v a l - d a t a ' ) )   $ ( ' v a l - d a t a ' ) . v a l u e   =   d a d o s . d a t a A t u a l i z a c a o ; 
 
                                         i f   ( d a d o s . h o n A u t o r   & &   $ ( ' v a l - h o n - a u t o r ' ) )   $ ( ' v a l - h o n - a u t o r ' ) . v a l u e   =   d a d o s . h o n A u t o r ; 
 
                                       
 
                                         / /   A p l i c a r   I R P F   s e   t r i b u t % v e l 
 
                                         i f   ( d a d o s . i r p f I s e n t o   = = =   f a l s e )   { 
 
                                                 c o n s t   i r p f T i p o E l   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i r p f - t i p o ' ) ; 
 
                                                 i f   ( i r p f T i p o E l   & &   i r p f T i p o E l . o p t i o n s . l e n g t h   >   1 )   { 
 
                                                         i r p f T i p o E l . v a l u e   =   i r p f T i p o E l . o p t i o n s [ 1 ] . v a l u e ;   / /   p r i m e i r o   ! =   ' i s e n t o ' 
 
                                                         i r p f T i p o E l . d i s p a t c h E v e n t ( n e w   E v e n t ( ' c h a n g e ' ,   {   b u b b l e s :   t r u e   } ) ) ; 
 
                                                 } 
 
                                         } 
 
                                       
 
                                         / /   A u t o - s e l e c i o n a r   o r i g e m   c o m o   P J e C a l c 
 
                                         i f   ( $ ( ' c a l c - o r i g e m ' ) )   $ ( ' c a l c - o r i g e m ' ) . v a l u e   =   ' p j e c a l c ' ; 
 
                                 } 
 
 
 
                                 / /   M o s t r a r   c a r d   c o l a p s a d o   s e   p l a n i l h a   f o i   c a r r e g a d a   ( F a s e   3 ) 
 
                                 c o n s t   r e s u m o C a r d   =   $ ( ' r e s u m o - e x t r a c a o - c a r d ' ) ; 
 
                                 i f   ( r e s u m o C a r d   & &   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a )   { 
 
                                         r e s u m o C a r d . s t y l e . d i s p l a y   =   ' b l o c k ' ; 
 
                                         / /   P r e e n c h e r   c o n t e %Q%d o   d o   c a r d 
 
                                         c o n s t   d a d o s   =   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ; 
 
                                         c o n s t   r e s u m o C o n t e u d o   =   $ ( ' r e s u m o - c o n t e u d o ' ) ; 
 
                                         i f   ( r e s u m o C o n t e u d o )   { 
 
                                                 r e s u m o C o n t e u d o . i n n e r H T M L   =   ` 
 
                                                         < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > I D : < / s t r o n g >   $ { d a d o s . i d P l a n i l h a   | |   ' N / A ' } < / d i v > 
 
                                                         < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > C r % d i t o : < / s t r o n g >   R $   $ { d a d o s . v e r b a s   | |   ' 0 , 0 0 ' } < / d i v > 
 
                                                         $ { d a d o s . f g t s   ?   ` < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > F G T S : < / s t r o n g >   R $   $ { d a d o s . f g t s } < / d i v > `   :   ' ' } 
 
                                                         < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > I N S S   T o t a l : < / s t r o n g >   R $   $ { d a d o s . i n s s T o t a l   | |   ' 0 , 0 0 ' } < / d i v > 
 
                                                         < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > I N S S   R e c : < / s t r o n g >   R $   $ { d a d o s . i n s s A u t o r   | |   ' 0 , 0 0 ' } < / d i v > 
 
                                                         $ { d a d o s . c u s t a s   ?   ` < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > C u s t a s : < / s t r o n g >   R $   $ { d a d o s . c u s t a s } < / d i v > `   :   ' ' } 
 
                                                         < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > D a t a : < / s t r o n g >   $ { d a d o s . d a t a A t u a l i z a c a o   | |   ' N / A ' } < / d i v > 
 
                                                         $ { d a d o s . p e r i o d o C a l c u l o   ?   ` < d i v   c l a s s = " r e s u m o - i t e m " > < s t r o n g > P e r % o d o : < / s t r o n g >   $ { d a d o s . p e r i o d o C a l c u l o } < / d i v > `   :   ' ' } 
 
                                                         $ { d a d o s . i r p f I s e n t o   = = =   f a l s e   ?   ` < d i v   c l a s s = " r e s u m o - i t e m "   s t y l e = " c o l o r : # b 4 5 3 0 9 " > < s t r o n g > I R P F : < / s t r o n g >   T r i b u t % v e l < / d i v > `   :   ' ' } 
 
                                                 ` ; 
 
                                         } 
 
                                 } 
 
 
 
                                 $ ( ' h o m o l o g a c a o - o v e r l a y ' ) . s t y l e . d i s p l a y   =   ' f l e x ' ; 
 
                                 d b g ( ' O v e r l a y   e x i b i d o   p a r a   o   u s u a r i o . ' ) ; 
 
                               
 
                                 / /   F a l l b a c k :   t e n t a r   c l i p b o a r d   s e   n % o   t e m   I D   d a   p l a n i l h a 
 
                                 i f   ( ! w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ? . i d P l a n i l h a )   { 
 
                                         t r y   { 
 
                                                 c o n s t   t x t   =   a w a i t   n a v i g a t o r . c l i p b o a r d . r e a d T e x t ( ) ; 
 
                                                 i f   ( t x t   & &   t x t . t r i m ( ) . l e n g t h   >   0 )   { 
 
                                                         $ ( ' v a l - i d ' ) . v a l u e   =   t x t . t r i m ( ) ; 
 
                                                 } 
 
                                         }   c a t c h   ( e )   {   c o n s o l e . w a r n ( ' C l i p b o a r d   i g n o r a d o   o u   b l o q u e a d o ' ,   e ) ;   } 
 
                                 } 
 
                               
 
                                 u p d a t e H i g h l i g h t ( ) ; 
 
                         }   c a t c h   ( e )   { 
 
                                 e r r ( ' E r r o   n o   h a n d l e r   d o   b o t a o   G e r a r   H o m o l o g a c a o : ' ,   e ) ; 
 
                                 a l e r t ( ' E r r o   a o   a b r i r   a s s i s t e n t e .   V e r i f i q u e   o   c o n s o l e   ( F 1 2 ) . ' ) ; 
 
                                 r e t u r n ; 
 
                                 } 
 
                 } ; 
 
               
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   F A S E   2 :   H a n d l e r   d o   I n p u t   F i l e   ( C a r r e g a r   P l a n i l h a ) 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 $ ( ' i n p u t - p l a n i l h a - p d f ' ) . o n c h a n g e   =   a s y n c   ( e )   = >   { 
 
                         c o n s t   f i l e   =   e . t a r g e t . f i l e s [ 0 ] ; 
 
                         i f   ( ! f i l e )   r e t u r n ; 
 
                       
 
                         c o n s t   b t n   =   $ ( ' b t n - a b r i r - h o m o l o g a c a o ' ) ; 
 
                         b t n . t e x t C o n t e n t   =   '   %  P r o c e s s a n d o . . . ' ; 
 
                         b t n . d i s a b l e d   =   t r u e ; 
 
                       
 
                         t r y   { 
 
                                 / /   C o n f i g u r a r   P D F . j s   ( p r i m e i r a   v e z ) 
 
                                 c o n s t   l o a d e d   =   c a r r e g a r P D F J S S e N e c e s s a r i o ( ) ; 
 
                                 i f   ( ! l o a d e d )   { 
 
                                         t h r o w   n e w   E r r o r ( ' P D F . j s   n % o   d i s p o n % v e l ' ) ; 
 
                                 } 
 
                               
 
                                 / /   P r o c e s s a r   p l a n i l h a 
 
                                 c o n s t   d a d o s   =   a w a i t   p r o c e s s a r P l a n i l h a P D F ( f i l e ) ; 
 
                               
 
                                 i f   ( d a d o s . s u c e s s o )   { 
 
                                         / /   S a l v a r   n o   s t a t e 
 
                                         w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a   =   d a d o s ; 
 
                                         w i n d o w . h c a l c S t a t e . p l a n i l h a C a r r e g a d a   =   t r u e ; 
 
                                       
 
                                         / /   A t u a l i z a r   d r o p d o w n s   d e   l i n h a s   e x t r a s   c o m   a   p l a n i l h a   p r i n c i p a l   r e c % m - c a r r e g a d a 
 
                                         a t u a l i z a r D r o p d o w n s P l a n i l h a s ( ) ; 
 
                                       
 
                                         / /   A t u a l i z a r   b o t % o 
 
                                         b t n . t e x t C o n t e n t   =   '      D a d o s   E x t r a % d o s ' ; 
 
                                         b t n . s t y l e . b a c k g r o u n d   =   ' # 1 0 b 9 8 1 ' ; 
 
                                         b t n . d i s a b l e d   =   f a l s e ; 
 
                                       
 
                                         d b g ( ' P l a n i l h a   e x t r a % d a : ' ,   d a d o s ) ; 
 
                                       
 
                                         / /   F e e d b a c k   v i s u a l   m o m e n t % n e o 
 
                                         s e t T i m e o u t ( ( )   = >   { 
 
                                                 b t n . t e x t C o n t e n t   =   ' G e r a r   H o m o l o g a % % o ' ; 
 
                                                 b t n . s t y l e . b a c k g r o u n d   =   ' # 0 0 5 0 9 e ' ; 
 
                                         } ,   2 0 0 0 ) ; 
 
                                 }   e l s e   { 
 
                                         t h r o w   n e w   E r r o r ( d a d o s . e r r o   | |   ' E r r o   d e s c o n h e c i d o ' ) ; 
 
                                 } 
 
                         }   c a t c h   ( e r r o r )   { 
 
                                 c o n s o l e . e r r o r ( ' [ H C a l c ]   E r r o   a o   p r o c e s s a r   P D F : ' ,   e r r o r . m e s s a g e ) ; 
 
                                 a l e r t ( ' E r r o   a o   p r o c e s s a r   P D F :   '   +   e r r o r . m e s s a g e ) ; 
 
                                 b t n . t e x t C o n t e n t   =   '      C a r r e g a r   P l a n i l h a ' ; 
 
                                 b t n . d i s a b l e d   =   f a l s e ; 
 
                         } 
 
                 } ; 
 
               
 
                 / /   H a n d l e r   d o   b o t % o   R e l o a d   ( r e c a r r e g a r   p l a n i l h a ) 
 
                 $ ( ' b t n - r e l o a d - p l a n i l h a ' ) . o n c l i c k   =   ( )   = >   { 
 
                         c o n s t   i n p u t F i l e   =   $ ( ' i n p u t - p l a n i l h a - p d f ' ) ; 
 
                         i n p u t F i l e . c l i c k ( ) ; 
 
                 } ; 
 
               
 
                 $ ( ' b t n - f e c h a r ' ) . o n c l i c k   =   ( e )   = >   { 
 
                         e . p r e v e n t D e f a u l t ( ) ;     / /   P r e v i n e   s c r o l l   i n d e s e j a d o 
 
                         c o n s t   m o d a l   =   $ ( ' h o m o l o g a c a o - m o d a l ' ) ; 
 
                         c o n s t   o v e r l a y   =   $ ( ' h o m o l o g a c a o - o v e r l a y ' ) ; 
 
                         m o d a l . s t y l e . o p a c i t y   =   ' 1 ' ; 
 
                         m o d a l . s t y l e . p o i n t e r E v e n t s   =   ' a l l ' ; 
 
                         m o d a l . d a t a s e t . g h o s t   =   ' f a l s e ' ; 
 
                         o v e r l a y . s t y l e . d i s p l a y   =   ' n o n e ' ; 
 
                         o v e r l a y . s t y l e . p o i n t e r E v e n t s   =   ' n o n e ' ; 
 
                         / /   L I M P A R   R E F E R % N C I A S   D O M :   v 1 . 8   u s a   m % t o d o   c e n t r a l i z a d o 
 
                         w i n d o w . h c a l c S t a t e . r e s e t P r e p ( ) ; 
 
                         c o n s o l e . l o g ( ' [ h c a l c ]   E s t a d o   r e s e t a d o   v i a   h c a l c S t a t e . r e s e t P r e p ( ) ' ) ; 
 
                 } ; 
 
                 $ ( ' h o m o l o g a c a o - o v e r l a y ' ) . o n c l i c k   =   ( e )   = >   { 
 
                         i f   ( e . t a r g e t . i d   = = =   ' h o m o l o g a c a o - o v e r l a y ' )   { 
 
                                 / /   N % o   f e c h a        t o r n a   t r a n s p a r e n t e   e   " f a n t a s m a " 
 
                                 c o n s t   m o d a l   =   $ ( ' h o m o l o g a c a o - m o d a l ' ) ; 
 
                                 c o n s t   o v e r l a y   =   $ ( ' h o m o l o g a c a o - o v e r l a y ' ) ; 
 
                                 c o n s t   i s G h o s t   =   m o d a l . d a t a s e t . g h o s t   = = =   ' t r u e ' ; 
 
                                 i f   ( i s G h o s t )   { 
 
                                         / /   S e g u n d o   c l i q u e   f o r a :   v o l t a   a o   n o r m a l 
 
                                         m o d a l . s t y l e . o p a c i t y   =   ' 1 ' ; 
 
                                         m o d a l . s t y l e . p o i n t e r E v e n t s   =   ' a l l ' ; 
 
                                         o v e r l a y . s t y l e . p o i n t e r E v e n t s   =   ' n o n e ' ; 
 
                                         m o d a l . d a t a s e t . g h o s t   =   ' f a l s e ' ; 
 
                                 }   e l s e   { 
 
                                         / /   P r i m e i r o   c l i q u e   f o r a :   v i r a   f a n t a s m a 
 
                                         m o d a l . s t y l e . o p a c i t y   =   ' 0 . 2 5 ' ; 
 
                                         m o d a l . s t y l e . t r a n s i t i o n   =   ' o p a c i t y   0 . 3 s ' ; 
 
                                         m o d a l . s t y l e . p o i n t e r E v e n t s   =   ' n o n e ' ; 
 
                                         / /   M a n t % m   o v e r l a y   t r a n s p a r e n t e   p a r a   d e t e c t a r   c l i q u e   d e   r e t o r n o 
 
                                         o v e r l a y . s t y l e . p o i n t e r E v e n t s   =   ' a l l ' ; 
 
                                         m o d a l . d a t a s e t . g h o s t   =   ' t r u e ' ; 
 
                                 } 
 
                         } 
 
                 } ; 
 
 
 
                 $ ( ' c a l c - o r i g e m ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' c o l - p j c ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   ! = =   ' p j e c a l c ' ) ;   } ; 
 
                 $ ( ' c a l c - a u t o r ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' c o l - e s c l a r e c i m e n t o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   ! = =   ' p e r i t o ' ) ;   } ; 
 
                 $ ( ' c a l c - e s c l a r e c i m e n t o s ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' c a l c - p e c a - p e r i t o ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! e . t a r g e t . c h e c k e d ) ;   } ; 
 
 
 
                 $ ( ' c a l c - f g t s ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         c o n s t   i s C h e c k e d   =   e . t a r g e t . c h e c k e d ; 
 
                         $ ( ' f g t s - r a d i o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! i s C h e c k e d ) ; 
 
                         $ ( ' r o w - f g t s - v a l o r ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! i s C h e c k e d ) ; 
 
                         u p d a t e H i g h l i g h t ( ) ; 
 
                 } ; 
 
                 $ ( ' c a l c - i n d i c e ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' c o l - j u r o s - v a l ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   ! = =   ' t r ' ) ;   } ; 
 
                 $ ( ' i g n o r a r - h o n - a u t o r ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' v a l - h o n - a u t o r ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . c h e c k e d ) ;   u p d a t e H i g h l i g h t ( ) ;   } ; 
 
                 $ ( ' i g n o r a r - i n s s ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         $ ( ' v a l - i n s s - r e c ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . c h e c k e d ) ; 
 
                         $ ( ' v a l - i n s s - t o t a l ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . c h e c k e d ) ; 
 
                         u p d a t e H i g h l i g h t ( ) ; 
 
                 } ; 
 
                 $ ( ' i r p f - t i p o ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' i r p f - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   = = =   ' i s e n t o ' ) ;   } ; 
 
 
 
                 $ ( ' r e s p - t i p o ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         $ ( ' r e s p - s u b - o p c o e s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   ! = =   ' s u b s i d i a r i a s ' ) ; 
 
                       
 
                         / /   A t u a l i z a r   v i s i b i l i d a d e   d e   c h e c k b o x e s   " D e p o s i t a d o   p e l a   P r i n c i p a l "   e m   t o d o s   o s   d e p %%s i t o s 
 
                         w i n d o w . h c a l c S t a t e . d e p o s i t o s R e c u r s a i s . f o r E a c h ( d   = >   { 
 
                                 i f   ( ! d . r e m o v e d )   { 
 
                                         a t u a l i z a r V i s i b i l i d a d e D e p o s i t o P r i n c i p a l ( d . i d x ) ; 
 
                                 } 
 
                         } ) ; 
 
                 } ; 
 
 
 
                 / /   L %%g i c a   p a r a   P e r % o d o s   D i v e r s o s 
 
                 $ ( ' r e s p - d i v e r s o s ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         c o n s t   f i e l d s e t   =   $ ( ' r e s p - d i v e r s o s - f i e l d s e t ' ) ; 
 
                         c o n s t   c o n t a i n e r   =   $ ( ' r e s p - d i v e r s o s - c o n t a i n e r ' ) ; 
 
                         c o n s t   s e l e c t P r i n c i p a l   =   $ ( ' r e s p - d e v e d o r a - p r i n c i p a l ' ) ; 
 
                         c o n s t   r e c l a m a d a s   =   w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o ? . m a p ( r   = >   r . n o m e )   | |   [ ] ; 
 
 
 
                         i f   ( e . t a r g e t . c h e c k e d )   { 
 
                                 f i e l d s e t . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
 
 
                                 / /   P r e e n c h e r   d r o p d o w n   d e   D e v e d o r a   P r i n c i p a l 
 
                                 s e l e c t P r i n c i p a l . i n n e r H T M L   =   ' ' ; 
 
                                 r e c l a m a d a s . f o r E a c h ( ( r e c ,   i d x )   = >   { 
 
                                         c o n s t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ; 
 
                                         o p t . v a l u e   =   r e c ; 
 
                                         o p t . t e x t C o n t e n t   =   r e c ; 
 
                                         i f   ( i d x   = = =   0 )   o p t . s e l e c t e d   =   t r u e ;   / /   P r i m e i r a   c o m o   p a d r % o 
 
                                         s e l e c t P r i n c i p a l . a p p e n d C h i l d ( o p t ) ; 
 
                                 } ) ; 
 
 
 
                                 / /   V e r i f i q u e   s e   j %   e x i s t e   u m   f o r m u l % r i o ,   s e n % o   c r i e   u m 
 
                                 i f   ( c o n t a i n e r . c h i l d r e n . l e n g t h   = = =   0 )   { 
 
                                         a d i c i o n a r L i n h a P e r i d o D i v e r s o ( ) ; 
 
                                 } 
 
                         }   e l s e   { 
 
                                 f i e l d s e t . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                                 c o n t a i n e r . i n n e r H T M L   =   ' ' ; 
 
                         } 
 
                 } ; 
 
 
 
                 / /   A t u a l i z a r   l i s t a s   q u a n d o   p r i n c i p a l   m u d a r 
 
                 $ ( ' r e s p - d e v e d o r a - p r i n c i p a l ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         / /   A t u a l i z a r   t o d o s   o s   d r o p d o w n s   d e   r e c l a m a d a s   ( c e n t r a l i z a d o ) 
 
                         a t u a l i z a r D r o p d o w n s R e c l a m a d a s ( ) ; 
 
                 } ; 
 
 
 
                 $ ( ' b t n - a d i c i o n a r - p e r i o d o ' ) . o n c l i c k   =   ( e )   = >   { 
 
                         e . p r e v e n t D e f a u l t ( ) ; 
 
                         a d i c i o n a r L i n h a P e r i d o D i v e r s o ( ) ; 
 
                 } ; 
 
 
 
                 / /              P L A N I L H A S   E X T R A S :   R E G I S T R O   E   S I N C R O N I Z A % % O                                                                                    
 
                 f u n c t i o n   r e g i s t r a r P l a n i l h a D i s p o n i v e l ( i d ,   l a b e l ,   d a d o s )   { 
 
                         i f   ( ! w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s )   w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s   =   [ ] ; 
 
                         / /   S u b s t i t u i   e n t r a d a   c o m   m e s m o   i d   ( r e - u p l o a d   d a   m e s m a   l i n h a ) 
 
                         w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s   = 
 
                                 w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s . f i l t e r ( p   = >   p . i d   ! = =   i d ) ; 
 
                         w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s . p u s h ( {   i d ,   l a b e l ,   d a d o s   } ) ; 
 
                         a t u a l i z a r D r o p d o w n s P l a n i l h a s ( ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   a t u a l i z a r D r o p d o w n s P l a n i l h a s ( )   { 
 
                         c o n s t   e x t r a s   =   w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s   | |   [ ] ; 
 
                         d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . p e r i o d o - p l a n i l h a - s e l e c t ' ) . f o r E a c h ( s e l   = >   { 
 
                                 c o n s t   c u r r e n t V a l   =   s e l . v a l u e ; 
 
                                 / /   R e m o v e   t o d a s   a s   o p % % e s   e x t r a s   ( m a n t % m   a p e n a s   ' p r i n c i p a l ' ) 
 
                                 A r r a y . f r o m ( s e l . o p t i o n s ) . f i l t e r ( o   = >   o . v a l u e   ! = =   ' p r i n c i p a l ' ) . f o r E a c h ( o   = >   o . r e m o v e ( ) ) ; 
 
                                 / /   R e - a d i c i o n a   a s   d i s p o n % v e i s 
 
                                 e x t r a s . f o r E a c h ( p   = >   { 
 
                                         c o n s t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ; 
 
                                         o p t . v a l u e   =   p . i d ; 
 
                                         o p t . t e x t C o n t e n t   =   `      $ { p . l a b e l } ` ; 
 
                                         s e l . a p p e n d C h i l d ( o p t ) ; 
 
                                 } ) ; 
 
                                 / /   R e s t a u r a   s e l e % % o   a n t e r i o r   s e   a i n d a   v % l i d a 
 
                                 i f   ( A r r a y . f r o m ( s e l . o p t i o n s ) . s o m e ( o   = >   o . v a l u e   = = =   c u r r e n t V a l ) )   s e l . v a l u e   =   c u r r e n t V a l ; 
 
                         } ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   a t u a l i z a r D r o p d o w n s R e c l a m a d a s ( )   { 
 
                         c o n s t   t o d a s R e c l a m a d a s   =   w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o ? . m a p ( r   = >   r . n o m e )   | |   [ ] ; 
 
                         c o n s t   p r i n c i p a l I n t e g r a l   =   $ ( ' r e s p - d e v e d o r a - p r i n c i p a l ' ) ? . v a l u e   | |   ' ' ; 
 
                       
 
                         / /   C o l e t a r   t o d a s   a s   r e c l a m a d a s   j %   s e l e c i o n a d a s   e m   l i n h a s   e x i s t e n t e s 
 
                         c o n s t   j a U s a d a s   =   n e w   S e t ( [ p r i n c i p a l I n t e g r a l ] ) ; 
 
                         d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . p e r i o d o - r e c l a m a d a ' ) . f o r E a c h ( s e l e c t   = >   { 
 
                                 i f   ( s e l e c t . v a l u e )   j a U s a d a s . a d d ( s e l e c t . v a l u e ) ; 
 
                         } ) ; 
 
                       
 
                         / /   A t u a l i z a r   c a d a   d r o p d o w n 
 
                         d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . p e r i o d o - r e c l a m a d a ' ) . f o r E a c h ( s e l e c t   = >   { 
 
                                 c o n s t   v a l o r A t u a l   =   s e l e c t . v a l u e ; 
 
                               
 
                                 / /   R e c o n s t r u i r   o p % % e s   e x c l u i n d o   a s   j %   u s a d a s   ( e x c e t o   a   p r %%p r i a   s e l e % % o ) 
 
                                 s e l e c t . i n n e r H T M L   =   ' < o p t i o n   v a l u e = " " > S e l e c i o n e   a   r e c l a m a d a . . . < / o p t i o n > ' ; 
 
                                 t o d a s R e c l a m a d a s . f o r E a c h ( r e c   = >   { 
 
                                         i f   ( ! j a U s a d a s . h a s ( r e c )   | |   r e c   = = =   v a l o r A t u a l )   { 
 
                                                 c o n s t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ; 
 
                                                 o p t . v a l u e   =   r e c ; 
 
                                                 o p t . t e x t C o n t e n t   =   r e c ; 
 
                                                 i f   ( r e c   = = =   v a l o r A t u a l )   o p t . s e l e c t e d   =   t r u e ; 
 
                                                 s e l e c t . a p p e n d C h i l d ( o p t ) ; 
 
                                         } 
 
                                 } ) ; 
 
                         } ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   a d i c i o n a r L i n h a P e r i d o D i v e r s o ( )   { 
 
                         c o n s t   c o n t a i n e r   =   $ ( ' r e s p - d i v e r s o s - c o n t a i n e r ' ) ; 
 
                         c o n s t   r e c l a m a d a s   =   w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o ? . m a p ( r   = >   r . n o m e )   | |   [ ] ; 
 
                         c o n s t   p r i n c i p a l I n t e g r a l   =   $ ( ' r e s p - d e v e d o r a - p r i n c i p a l ' ) ? . v a l u e   | |   ' ' ; 
 
                         c o n s t   i d x   =   c o n t a i n e r . c h i l d r e n . l e n g t h ; 
 
                         c o n s t   r o w I d   =   ` p e r i o d o - d i v e r s o - $ { i d x } ` ; 
 
                         c o n s t   n u m e r o D e v e d o r a   =   i d x   +   2 ;   / /   # 1   %   a   p r i n c i p a l ,   e n t % o   c o m e % a   d o   # 2 
 
 
 
                         c o n s t   d i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                         d i v . i d   =   r o w I d ; 
 
                         d i v . c l a s s N a m e   =   ' r o w ' ; 
 
                         d i v . s t y l e . m a r g i n B o t t o m   =   ' 1 5 p x ' ; 
 
                         d i v . s t y l e . p a d d i n g   =   ' 1 2 p x ' ; 
 
                         d i v . s t y l e . b a c k g r o u n d C o l o r   =   ' # f 5 f 5 f 5 ' ; 
 
                         d i v . s t y l e . b o r d e r R a d i u s   =   ' 4 p x ' ; 
 
 
 
                         / /   F i l t r a r :   r e m o v e r   a   p r i n c i p a l   i n t e g r a l   E   a s   j %   s e l e c i o n a d a s   e m   o u t r a s   l i n h a s 
 
                         c o n s t   j a U s a d a s   =   n e w   S e t ( [ p r i n c i p a l I n t e g r a l ] ) ; 
 
                         d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . p e r i o d o - r e c l a m a d a ' ) . f o r E a c h ( s e l e c t   = >   { 
 
                                 i f   ( s e l e c t . v a l u e )   j a U s a d a s . a d d ( s e l e c t . v a l u e ) ; 
 
                         } ) ; 
 
                       
 
                         l e t   s e l e c t O p t i o n s   =   ' < o p t i o n   v a l u e = " " > S e l e c i o n e   a   r e c l a m a d a . . . < / o p t i o n > ' ; 
 
                         r e c l a m a d a s . f o r E a c h ( r e c   = >   { 
 
                                 i f   ( ! j a U s a d a s . h a s ( r e c ) )   { 
 
                                         s e l e c t O p t i o n s   + =   ` < o p t i o n   v a l u e = " $ { r e c } " > $ { r e c } < / o p t i o n > ` ; 
 
                                 } 
 
                         } ) ; 
 
 
 
                         d i v . i n n e r H T M L   =   ` 
 
                                 < d i v   s t y l e = " m a r g i n - b o t t o m :   1 0 p x ; " > 
 
                                         < l a b e l   s t y l e = " f o n t - w e i g h t :   b o l d ; " > D e v e d o r a   # $ { n u m e r o D e v e d o r a } < / l a b e l > 
 
                                         < s e l e c t   c l a s s = " p e r i o d o - r e c l a m a d a "   d a t a - i d x = " $ { i d x } "   s t y l e = " w i d t h :   1 0 0 % ;   p a d d i n g :   8 p x ; " > 
 
                                                 $ { s e l e c t O p t i o n s } 
 
                                         < / s e l e c t > 
 
                                 < / d i v > 
 
                                 < d i v   s t y l e = " m a r g i n - b o t t o m :   1 0 p x ; " > 
 
                                         < l a b e l   s t y l e = " f o n t - w e i g h t :   b o l d ; " > T i p o   d e   R e s p o n s a b i l i d a d e < / l a b e l > 
 
                                         < d i v   s t y l e = " d i s p l a y :   f l e x ;   g a p :   1 5 p x ; " > 
 
                                                 < l a b e l > < i n p u t   t y p e = " r a d i o "   n a m e = " p e r i o d o - t i p o - $ { i d x } "   c l a s s = " p e r i o d o - t i p o "   d a t a - i d x = " $ { i d x } "   v a l u e = " s u b s i d i a r i a "   c h e c k e d >   S u b s i d i % r i a < / l a b e l > 
 
                                                 < l a b e l > < i n p u t   t y p e = " r a d i o "   n a m e = " p e r i o d o - t i p o - $ { i d x } "   c l a s s = " p e r i o d o - t i p o "   d a t a - i d x = " $ { i d x } "   v a l u e = " p r i n c i p a l " >   P r i n c i p a l   ( P e r % o d o   P a r c i a l ) < / l a b e l > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                                 < d i v   s t y l e = " d i s p l a y :   f l e x ;   g a p :   1 0 p x ;   m a r g i n - b o t t o m :   1 0 p x ; " > 
 
                                         < d i v   s t y l e = " f l e x :   1 ; " > 
 
                                                 < l a b e l > P e r % o d o   ( v a z i o   =   i n t e g r a l ) < / l a b e l > 
 
                                                 < i n p u t   t y p e = " t e x t "   c l a s s = " p e r i o d o - p e r i o d o "   d a t a - i d x = " $ { i d x } "   p l a c e h o l d e r = " D e i x e   v a z i o   p a r a   p e r % o d o   i n t e g r a l "   s t y l e = " w i d t h :   1 0 0 % ;   p a d d i n g :   8 p x ; " > 
 
                                         < / d i v > 
 
                                         < d i v   s t y l e = " f l e x :   1 ; " > 
 
                                                 < l a b e l > I D   C % l c u l o   S e p a r a d o < / l a b e l > 
 
                                                 < i n p u t   t y p e = " t e x t "   c l a s s = " p e r i o d o - i d "   d a t a - i d x = " $ { i d x } "   p l a c e h o l d e r = " I D   # X X X X "   s t y l e = " w i d t h :   1 0 0 % ;   p a d d i n g :   8 p x ; " > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                                 < d i v   s t y l e = " m a r g i n - b o t t o m :   1 0 p x ; " > 
 
                                         < l a b e l   s t y l e = " f o n t - w e i g h t :   b o l d ;   f o n t - s i z e :   1 2 p x ; " > P l a n i l h a   d e s t a   D e v e d o r a < / l a b e l > 
 
                                         < d i v   s t y l e = " d i s p l a y :   f l e x ;   g a p :   8 p x ;   a l i g n - i t e m s :   c e n t e r ;   m a r g i n - t o p :   4 p x ; " > 
 
                                                 < s e l e c t   c l a s s = " p e r i o d o - p l a n i l h a - s e l e c t "   d a t a - i d x = " $ { i d x } " 
 
                                                                 s t y l e = " f l e x :   1 ;   p a d d i n g :   6 p x ;   f o n t - s i z e :   1 2 p x ;   b o r d e r :   1 p x   s o l i d   # c c c ;   b o r d e r - r a d i u s :   4 p x ; " > 
 
                                                         < o p t i o n   v a l u e = " p r i n c i p a l " >      M e s m a   p l a n i l h a   p r i n c i p a l < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                                 < b u t t o n   t y p e = " b u t t o n "   c l a s s = " b t n - c a r r e g a r - p l a n i l h a - e x t r a   b t n - a c t i o n " 
 
                                                                 d a t a - i d x = " $ { i d x } " 
 
                                                                 s t y l e = " f o n t - s i z e :   1 1 p x ;   p a d d i n g :   6 p x   1 0 p x ;   w h i t e - s p a c e :   n o w r a p ;   b a c k g r o u n d :   # 7 c 3 a e d ; " > 
 
                                                              C a r r e g a r   N o v a 
 
                                                 < / b u t t o n > 
 
                                                 < i n p u t   t y p e = " f i l e "   c l a s s = " i n p u t - p l a n i l h a - e x t r a - p d f "   d a t a - i d x = " $ { i d x } " 
 
                                                               a c c e p t = " . p d f "   s t y l e = " d i s p l a y :   n o n e ; " > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                                 < d i v   s t y l e = " d i s p l a y :   f l e x ;   g a p :   1 0 p x ;   a l i g n - i t e m s :   c e n t e r ;   m a r g i n - b o t t o m :   1 0 p x ; " > 
 
                                         < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   c l a s s = " p e r i o d o - t o t a l "   d a t a - i d x = " $ { i d x } " >   P e r % o d o   T o t a l < / l a b e l > 
 
                                         < b u t t o n   t y p e = " b u t t o n "   c l a s s = " b t n - r e m o v e r - p e r i o d o   b t n - a c t i o n "   d a t a - i d x = " $ { i d x } "   d a t a - r o w - i d = " $ { r o w I d } "   s t y l e = " p a d d i n g :   8 p x ;   m a r g i n - l e f t :   a u t o ;   b a c k g r o u n d :   # d 3 2 f 2 f ; " > R e m o v e r < / b u t t o n > 
 
                                 < / d i v > 
 
                         ` ; 
 
                         c o n t a i n e r . a p p e n d C h i l d ( d i v ) ; 
 
                       
 
                         / /              B O T % O   R E M O V E R :   a t u a l i z a r   d r o p d o w n s   a p %%s   r e m o % % o                                                                     
 
                         c o n s t   b t n R e m o v e r   =   d i v . q u e r y S e l e c t o r ( ` . b t n - r e m o v e r - p e r i o d o [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
                         b t n R e m o v e r . o n c l i c k   =   ( )   = >   { 
 
                                 d o c u m e n t . g e t E l e m e n t B y I d ( r o w I d ) . r e m o v e ( ) ; 
 
                                 a t u a l i z a r D r o p d o w n s R e c l a m a d a s ( ) ;   / /   L i b e r a r   r e c l a m a d a   d e   v o l t a 
 
                         } ; 
 
                       
 
                         / /              A U T O - P R E E N C H E R   C A M P O S   c o m   p l a n i l h a   p r i n c i p a l   ( p a d r % o )                                                   
 
                         c o n s t   p e r i o d o I n p u t   =   d i v . q u e r y S e l e c t o r ( ` . p e r i o d o - p e r i o d o [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
                         c o n s t   i d I n p u t             =   d i v . q u e r y S e l e c t o r ( ` . p e r i o d o - i d [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
 
 
                         i f   ( w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a )   { 
 
                                 c o n s t   p d   =   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ; 
 
                                 i f   ( p e r i o d o I n p u t   & &   p d . p e r i o d o C a l c u l o )   p e r i o d o I n p u t . v a l u e   =   p d . p e r i o d o C a l c u l o ; 
 
                                 i f   ( i d I n p u t   & &   p d . i d P l a n i l h a )                     i d I n p u t . v a l u e             =   p d . i d P l a n i l h a ; 
 
                         } 
 
 
 
                         / /              S E L E C T   R E C L A M A D A :   a t u a l i z a r   d r o p d o w n s   q u a n d o   s e l e c i o n a d a                                          
 
                         c o n s t   s e l e c t R e c l a m a d a   =   d i v . q u e r y S e l e c t o r ( ` . p e r i o d o - r e c l a m a d a [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
                         s e l e c t R e c l a m a d a . o n c h a n g e   =   ( )   = >   { 
 
                                 / /   A t u a l i z a r   t o d o s   o s   d r o p d o w n s   p a r a   r e f l e t i r   n o v a   s e l e % % o 
 
                                 a t u a l i z a r D r o p d o w n s R e c l a m a d a s ( ) ; 
 
                         } ; 
 
 
 
                         / /              S E L E C T :   t r o c a r   p l a n i l h a                                                                                                                                             
 
                         c o n s t   s e l e c t P l a n i l h a   =   d i v . q u e r y S e l e c t o r ( ` . p e r i o d o - p l a n i l h a - s e l e c t [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
 
 
                         / /   I n j e t a r   p l a n i l h a s   j %   d i s p o n % v e i s   n e s t e   d r o p d o w n 
 
                         a t u a l i z a r D r o p d o w n s P l a n i l h a s ( ) ; 
 
 
 
                         s e l e c t P l a n i l h a . o n c h a n g e   =   ( e )   = >   { 
 
                                 c o n s t   v a l   =   e . t a r g e t . v a l u e ; 
 
                                 c o n s t   p d   =   v a l   = = =   ' p r i n c i p a l ' 
 
                                         ?   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a 
 
                                         :   ( w i n d o w . h c a l c S t a t e . p l a n i l h a s D i s p o n i v e i s   | |   [ ] ) . f i n d ( p   = >   p . i d   = = =   v a l ) ? . d a d o s ; 
 
                                 i f   ( ! p d )   r e t u r n ; 
 
                                 i f   ( p d . i d P l a n i l h a   & &   i d I n p u t )                       i d I n p u t . v a l u e             =   p d . i d P l a n i l h a ; 
 
                                 i f   ( p d . p e r i o d o C a l c u l o   & &   p e r i o d o I n p u t )     p e r i o d o I n p u t . v a l u e   =   p d . p e r i o d o C a l c u l o ; 
 
                         } ; 
 
 
 
                         / /              B O T % O   C A R R E G A R   N O V A   P L A N I L H A                                                                                                                              
 
                         c o n s t   b t n C a r r e g a r     =   d i v . q u e r y S e l e c t o r ( ` . b t n - c a r r e g a r - p l a n i l h a - e x t r a [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
                         c o n s t   i n p u t E x t r a       =   d i v . q u e r y S e l e c t o r ( ` . i n p u t - p l a n i l h a - e x t r a - p d f [ d a t a - i d x = " $ { i d x } " ] ` ) ; 
 
 
 
                         b t n C a r r e g a r . o n c l i c k   =   ( )   = >   i n p u t E x t r a . c l i c k ( ) ; 
 
 
 
                         i n p u t E x t r a . o n c h a n g e   =   a s y n c   ( e )   = >   { 
 
                                 c o n s t   f i l e   =   e . t a r g e t . f i l e s [ 0 ] ; 
 
                                 i f   ( ! f i l e )   r e t u r n ; 
 
                                 i n p u t E x t r a . v a l u e   =   ' ' ;     / /   r e s e t        p e r m i t e   r e - u p l o a d   d o   m e s m o   a r q u i v o 
 
 
 
                                 c o n s t   o r i g i n a l T e x t   =   b t n C a r r e g a r . t e x t C o n t e n t ; 
 
                                 b t n C a r r e g a r . t e x t C o n t e n t   =   '   %. . . ' ; 
 
                                 b t n C a r r e g a r . d i s a b l e d   =   t r u e ; 
 
 
 
                                 t r y   { 
 
                                         c o n s t   l o a d e d   =   c a r r e g a r P D F J S S e N e c e s s a r i o ( ) ; 
 
                                         i f   ( ! l o a d e d )   t h r o w   n e w   E r r o r ( ' P D F . j s   n % o   d i s p o n % v e l ' ) ; 
 
 
 
                                         c o n s t   d a d o s   =   a w a i t   p r o c e s s a r P l a n i l h a P D F ( f i l e ) ; 
 
                                         i f   ( ! d a d o s . s u c e s s o )   t h r o w   n e w   E r r o r ( d a d o s . e r r o   | |   ' E r r o   d e s c o n h e c i d o ' ) ; 
 
 
 
                                         / /   P r e e n c h e r   c a m p o s   d a   l i n h a   c o m   d a d o s   e x t r a % d o s 
 
                                         i f   ( d a d o s . i d P l a n i l h a   & &   i d I n p u t )                     i d I n p u t . v a l u e             =   d a d o s . i d P l a n i l h a ; 
 
                                         i f   ( d a d o s . p e r i o d o C a l c u l o   & &   p e r i o d o I n p u t )   p e r i o d o I n p u t . v a l u e   =   d a d o s . p e r i o d o C a l c u l o ; 
 
 
 
                                         / /   R e g i s t r a r   c o m o   p l a n i l h a   d i s p o n % v e l   p a r a   a s   d e m a i s   l i n h a s 
 
                                         c o n s t   e x t r a I d         =   ` e x t r a _ $ { i d x } ` ; 
 
                                         c o n s t   e x t r a L a b e l   =   ` $ { d a d o s . i d P l a n i l h a   | |   ' E x t r a ' }   ( D e v . $ { i d x   +   2 } ) ` ; 
 
                                         r e g i s t r a r P l a n i l h a D i s p o n i v e l ( e x t r a I d ,   e x t r a L a b e l ,   d a d o s ) ; 
 
 
 
                                         / /   S e l e c i o n a r   e s t a   p l a n i l h a   n o   d r o p d o w n   d e s t a   l i n h a 
 
                                         s e l e c t P l a n i l h a . v a l u e   =   e x t r a I d ; 
 
 
 
                                         / /   F e e d b a c k   v i s u a l 
 
                                         b t n C a r r e g a r . t e x t C o n t e n t             =   '      A n a l i s a d a ' ; 
 
                                         b t n C a r r e g a r . s t y l e . b a c k g r o u n d   =   ' # 1 0 b 9 8 1 ' ; 
 
                                         b t n C a r r e g a r . d i s a b l e d                   =   f a l s e ; 
 
 
 
                                 }   c a t c h   ( e r r )   { 
 
                                         a l e r t ( ' E r r o   a o   p r o c e s s a r   p l a n i l h a :   '   +   e r r . m e s s a g e ) ; 
 
                                         b t n C a r r e g a r . t e x t C o n t e n t   =   o r i g i n a l T e x t ; 
 
                                         b t n C a r r e g a r . d i s a b l e d         =   f a l s e ; 
 
                                 } 
 
                         } ; 
 
                 } 
 
 
 
                 $ ( ' c h k - h o n - r e u ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         / /   L %%g i c a   i n v e r t i d a :   m a r c a d o   =   " N % o   h % "   =   e s c o n d e   c a m p o s 
 
                         $ ( ' h o n - r e u - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . c h e c k e d ) ; 
 
                 } ; 
 
               
 
                 / /   C o n t r o l a r   e x i b i % % o   d e   c a m p o   p e r c e n t u a l   v s   v a l o r 
 
                 d o c u m e n t . q u e r y S e l e c t o r A l l ( ' i n p u t [ n a m e = " r a d - h o n - r e u - t i p o " ] ' ) . f o r E a c h ( r a d i o   = >   { 
 
                         r a d i o . a d d E v e n t L i s t e n e r ( ' c h a n g e ' ,   ( e )   = >   { 
 
                                 c o n s t   i s P e r c e n t u a l   =   e . t a r g e t . v a l u e   = = =   ' p e r c e n t u a l ' ; 
 
                                 $ ( ' h o n - r e u - p e r c - c a m p o ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! i s P e r c e n t u a l ) ; 
 
                                 $ ( ' h o n - r e u - v a l o r - c a m p o ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   i s P e r c e n t u a l ) ; 
 
                         } ) ; 
 
                 } ) ; 
 
               
 
                 $ ( ' c h k - p e r i t o - c o n h ' ) . o n c h a n g e   =   ( e )   = >   {   $ ( ' p e r i t o - c o n h - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! e . t a r g e t . c h e c k e d ) ;   } ; 
 
 
 
                 / /   C O R R E % % O   4 :   E v e n t   l i s t e n e r   s i m p l i f i c a d o   -   g u a r d   i n t e r n o   e m   p r e e n c h e r D e p o s i t o s A u t o m a t i c o s 
 
                 $ ( ' c h k - d e p o s i t o ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         / /   T o g g l e   v i s i b i l i d a d e 
 
                         $ ( ' d e p o s i t o - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! e . t a r g e t . c h e c k e d ) ; 
 
                       
 
                         / /   P r e e n c h e r   a u t o m a t i c a m e n t e   s e   m a r c a d o   ( s a f e :   t e m   g u a r d   p a r a   j a T e m C a m p o s ) 
 
                         i f   ( e . t a r g e t . c h e c k e d )   { 
 
                                 p r e e n c h e r D e p o s i t o s A u t o m a t i c o s ( ) ; 
 
                         } 
 
                 } ; 
 
               
 
                 $ ( ' c h k - p a g - a n t e c i p a d o ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         $ ( ' p a g - a n t e c i p a d o - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! e . t a r g e t . c h e c k e d ) ; 
 
                         i f   ( e . t a r g e t . c h e c k e d   & &   w i n d o w . h c a l c S t a t e . p a g a m e n t o s A n t e c i p a d o s . l e n g t h   = = =   0 )   { 
 
                                 a d i c i o n a r P a g a m e n t o A n t e c i p a d o ( ) ;   / /   A d i c i o n a   p r i m e i r o   p a g a m e n t o   a u t o m a t i c a m e n t e 
 
                         } 
 
                 } ; 
 
 
 
                 / /   E v e n t   l i s t e n e r s   p a r a   r a d i o s   d e   t i p o   d e   l i b e r a % % o 
 
                 d o c u m e n t . q u e r y S e l e c t o r A l l ( ' i n p u t [ n a m e = " l i b - t i p o " ] ' ) . f o r E a c h ( r a d i o   = >   { 
 
                         r a d i o . a d d E v e n t L i s t e n e r ( ' c h a n g e ' ,   ( e )   = >   { 
 
                                 c o n s t   v a l o r   =   e . t a r g e t . v a l u e ; 
 
                                 $ ( ' l i b - r e m a n e s c e n t e - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   v a l o r   ! = =   ' r e m a n e s c e n t e ' ) ; 
 
                                 $ ( ' l i b - d e v o l u c a o - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   v a l o r   ! = =   ' d e v o l u c a o ' ) ; 
 
                         } ) ; 
 
                 } ) ; 
 
 
 
                 d o c u m e n t . g e t E l e m e n t s B y N a m e ( ' r a d - i n t i m a c a o ' ) . f o r E a c h ( ( r a d )   = >   { 
 
                         r a d . o n c h a n g e   =   ( e )   = >   {   $ ( ' i n t i m a c a o - m a n d a d o - c a m p o s ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   = = =   ' d i a r i o ' ) ;   } ; 
 
                 } ) ; 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   F U N % % E S   D E   G E R E N C I A M E N T O   D E   M % L T I P L O S   D E P % S I T O S 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
               
 
                 / /   P r e e n c h e   d e p %%s i t o s   a u t o m a t i c a m e n t e   c o m   r e c u r s o s   d e t e c t a d o s   ( D e p %%s i t o / G a r a n t i a ) 
 
                 f u n c t i o n   p r e e n c h e r D e p o s i t o s A u t o m a t i c o s ( )   { 
 
                         c o n s t   p r e p   =   w i n d o w . h c a l c L a s t P r e p R e s u l t ; 
 
                         i f   ( ! p r e p   | |   ! p r e p . d e p o s i t o s   | |   p r e p . d e p o s i t o s . l e n g t h   = = =   0 )   { 
 
                                 c o n s o l e . l o g ( ' [ A U T O - D E P O S I T O S ]   S e m   d a d o s   d e   p r e p ' ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
                       
 
                         c o n s t   c o n t a i n e r   =   $ ( ' d e p o s i t o s - c o n t a i n e r ' ) ; 
 
                         i f   ( ! c o n t a i n e r )   { 
 
                                 c o n s o l e . e r r o r ( ' [ A U T O - D E P O S I T O S ]   C o n t a i n e r   n % o   e n c o n t r a d o ! ' ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
                       
 
                         / /   S e   j %   t e m   c a m p o s ,   n % o   l i m p a r   ( p e r m i t e   a d i c i o n a r   m a n u a l m e n t e ) 
 
                         c o n s t   j a T e m C a m p o s   =   c o n t a i n e r . c h i l d r e n . l e n g t h   >   0 ; 
 
                         i f   ( j a T e m C a m p o s )   { 
 
                                 c o n s o l e . l o g ( ' [ A U T O - D E P O S I T O S ]   C o n t a i n e r   j %   p o s s u i   c a m p o s ,   p u l a n d o ' ) ; 
 
                                 r e t u r n ; 
 
                         } 
 
                       
 
                         / /   L i m p a r   d e p %%s i t o s   e x i s t e n t e s   a p e n a s   s e   e s t i v e r   v a z i o 
 
                         c o n t a i n e r . i n n e r H T M L   =   ' ' ; 
 
                         w i n d o w . h c a l c S t a t e . n e x t D e p o s i t o I d x   =   0 ; 
 
                         w i n d o w . h c a l c S t a t e . d e p o s i t o s R e c u r s a i s   =   [ ] ; 
 
                       
 
                         c o n s o l e . l o g ( ' [ A U T O - D E P O S I T O S ]   I n i c i a n d o   p r e e n c h i m e n t o   c o m ' ,   p r e p . d e p o s i t o s . l e n g t h ,   ' r e c u r s o s ' ) ; 
 
                       
 
                         / /   P r e e n c h e r   c o m   T O D O S   o s   d e p %%s i t o s / g a r a n t i a s   d o s   r e c u r s o s   d e t e c t a d o s 
 
                         f o r   ( c o n s t   d e p o s i t o   o f   p r e p . d e p o s i t o s )   { 
 
                                 / /   F i l t r a r   a n e x o s   d e   t i p o   D e p %%s i t o   o u   G a r a n t i a 
 
                                 c o n s t   a n e x o s R e l e v a n t e s   =   ( d e p o s i t o . a n e x o s   | |   [ ] ) . f i l t e r ( a x   = > 
 
                                         a x . t i p o   = = =   ' D e p %%s i t o '   | |   a x . t i p o   = = =   ' G a r a n t i a ' 
 
                                 ) ; 
 
                               
 
                                 / /   C O R R E % % O   3 :   F a l l b a c k   p a r a   r e c u r s o s   s e m   a n e x o s   e x p a n d i d o s 
 
                                 i f   ( a n e x o s R e l e v a n t e s . l e n g t h   >   0 )   { 
 
                                         f o r   ( c o n s t   a n e x o   o f   a n e x o s R e l e v a n t e s )   { 
 
                                                 a d i c i o n a r D e p o s i t o R e c u r s a l ( ) ; 
 
                                                 c o n s t   i d x   =   w i n d o w . h c a l c S t a t e . n e x t D e p o s i t o I d x   -   1 ; 
 
                                               
 
                                                 c o n s t   t i p o S e l e c t   =   $ ( ` d e p - t i p o - $ { i d x } ` ) ; 
 
                                                 c o n s t   d e p o s i t a n t e S e l e c t   =   $ ( ` d e p - d e p o s i t a n t e - $ { i d x } ` ) ; 
 
                                                 c o n s t   i d I n p u t   =   $ ( ` d e p - i d - $ { i d x } ` ) ; 
 
                                               
 
                                                 i f   ( t i p o S e l e c t )   { 
 
                                                         t i p o S e l e c t . v a l u e   =   a n e x o . t i p o   = = =   ' D e p %%s i t o '   ?   ' b b '   :   ' g a r a n t i a ' ; 
 
                                                         t i p o S e l e c t . d i s p a t c h E v e n t ( n e w   E v e n t ( ' c h a n g e ' ,   {   b u b b l e s :   t r u e   } ) ) ; 
 
                                                 } 
 
                                               
 
                                                 i f   ( d e p o s i t a n t e S e l e c t )   { 
 
                                                         d e p o s i t a n t e S e l e c t . v a l u e   =   d e p o s i t o . d e p o s i t a n t e ; 
 
                                                 } 
 
                                               
 
                                                 i f   ( i d I n p u t )   { 
 
                                                         i d I n p u t . v a l u e   =   a n e x o . i d   | |   ' ' ; 
 
                                                 } 
 
                                         } 
 
                                         c o n s o l e . l o g ( ' [ A U T O - D E P O S I T O S ] ' ,   a n e x o s R e l e v a n t e s . l e n g t h ,   ' d e p %%s i t o ( s )   d e ' ,   d e p o s i t o . d e p o s i t a n t e ) ; 
 
                                 }   e l s e   { 
 
                                         / /   F A L L B A C K :   R e c u r s o   d e t e c t a d o   m a s   s e m   a n e x o s   e x p a n d i d o s 
 
                                         c o n s o l e . w a r n ( ' [ A U T O - D E P O S I T O S ]   R e c u r s o   s e m   a n e x o s   p a r a ' ,   d e p o s i t o . d e p o s i t a n t e ,   '      c r i a n d o   l i n h a   s e m   I D ' ) ; 
 
                                         a d i c i o n a r D e p o s i t o R e c u r s a l ( ) ; 
 
                                         c o n s t   i d x   =   w i n d o w . h c a l c S t a t e . n e x t D e p o s i t o I d x   -   1 ; 
 
                                         c o n s t   d e p o s i t a n t e S e l e c t   =   $ ( ` d e p - d e p o s i t a n t e - $ { i d x } ` ) ; 
 
                                         i f   ( d e p o s i t a n t e S e l e c t )   { 
 
                                                 d e p o s i t a n t e S e l e c t . v a l u e   =   d e p o s i t o . d e p o s i t a n t e   | |   ' ' ; 
 
                                         } 
 
                                 } 
 
                         } 
 
                 } 
 
               
 
                 f u n c t i o n   a d i c i o n a r D e p o s i t o R e c u r s a l ( )   { 
 
                         c o n s t   i d x   =   w i n d o w . h c a l c S t a t e . n e x t D e p o s i t o I d x + + ; 
 
                         c o n s t   c o n t a i n e r   =   $ ( ' d e p o s i t o s - c o n t a i n e r ' ) ; 
 
                       
 
                         / /   B u s c a r   T O D A S   a s   r e c l a m a d a s   d o   p r o c e s s o   ( n % o   s %%  a s   c o m   r e c u r s o s ) 
 
                         c o n s t   r e c l a m a d a s   =   w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o ? . m a p ( r   = >   r . n o m e )   | |   [ ] ; 
 
                       
 
                         c o n s t   d e p o s i t o D i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                         d e p o s i t o D i v . i d   =   ` d e p o s i t o - i t e m - $ { i d x } ` ; 
 
                         d e p o s i t o D i v . c l a s s N a m e   =   ' d e p o s i t o - i t e m ' ; 
 
                         d e p o s i t o D i v . s t y l e . c s s T e x t   =   ' b o r d e r :   1 p x   s o l i d   # d d d ;   p a d d i n g :   8 p x ;   m a r g i n - b o t t o m :   8 p x ;   b o r d e r - r a d i u s :   4 p x ;   b a c k g r o u n d :   # f 9 f 9 f 9 ; ' ; 
 
                       
 
                         / /   C o n s t r u i r   o p % % e s   d o   s e l e c t   d e   d e p o s i t a n t e   c o m   T O D A S   a s   r e c l a m a d a s   d o   p r o c e s s o 
 
                         l e t   o p t i o n s H t m l   =   ' < o p t i o n   v a l u e = " " > - -   S e l e c i o n e   R e c l a m a d a   - - < / o p t i o n > ' ; 
 
                         f o r   ( c o n s t   n o m e   o f   r e c l a m a d a s )   { 
 
                                 o p t i o n s H t m l   + =   ` < o p t i o n   v a l u e = " $ { n o m e } " > $ { n o m e } < / o p t i o n > ` ; 
 
                         } 
 
                       
 
                         d e p o s i t o D i v . i n n e r H T M L   =   ` 
 
                                 < d i v   s t y l e = " d i s p l a y :   f l e x ;   j u s t i f y - c o n t e n t :   s p a c e - b e t w e e n ;   a l i g n - i t e m s :   c e n t e r ;   m a r g i n - b o t t o m :   8 p x ; " > 
 
                                         < s t r o n g   s t y l e = " f o n t - s i z e :   1 1 p x ;   c o l o r :   # 6 6 6 ; " > D e p %%s i t o   R e c u r s a l   # $ { i d x   +   1 } < / s t r o n g > 
 
                                         < b u t t o n   t y p e = " b u t t o n "   i d = " b t n - r e m o v e r - d e p - $ { i d x } "   s t y l e = " p a d d i n g :   2 p x   8 p x ;   f o n t - s i z e :   1 0 p x ;   c o l o r :   # d c 2 6 2 6 ;   b a c k g r o u n d :   # f e e ;   b o r d e r :   1 p x   s o l i d   # f c a ;   b o r d e r - r a d i u s :   3 p x ;   c u r s o r :   p o i n t e r ; " >      R e m o v e r < / b u t t o n > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < s e l e c t   i d = " d e p - t i p o - $ { i d x } "   d a t a - d e p - i d x = " $ { i d x } " > 
 
                                                 < o p t i o n   v a l u e = " b b "   s e l e c t e d > B a n c o   d o   B r a s i l < / o p t i o n > 
 
                                                 < o p t i o n   v a l u e = " s i f " > C E F   ( S I F ) < / o p t i o n > 
 
                                                 < o p t i o n   v a l u e = " g a r a n t i a " > S e g u r o   G a r a n t i a < / o p t i o n > 
 
                                         < / s e l e c t > 
 
                                         < s e l e c t   i d = " d e p - d e p o s i t a n t e - $ { i d x } "   d a t a - d e p - i d x = " $ { i d x } " > 
 
                                                 $ { o p t i o n s H t m l } 
 
                                         < / s e l e c t > 
 
                                         < i n p u t   t y p e = " t e x t "   i d = " d e p - i d - $ { i d x } "   p l a c e h o l d e r = " I D   d a   G u i a "   d a t a - d e p - i d x = " $ { i d x } " > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w "   i d = " d e p - p r i n c i p a l - r o w - $ { i d x } " > 
 
                                         < l a b e l > < i n p u t   t y p e = " c h e c k b o x "   i d = " d e p - p r i n c i p a l - $ { i d x } "   c h e c k e d   d a t a - d e p - i d x = " $ { i d x } " >   D e p o s i t a d o   p e l a   D e v e d o r a   P r i n c i p a l ? < / l a b e l > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w   h i d d e n "   i d = " d e p - s o l i d a r i a - i n f o - $ { i d x } "   s t y l e = " f o n t - s i z e :   1 1 p x ;   c o l o r :   # 0 5 9 6 6 9 ;   f o n t - s t y l e :   i t a l i c ; " > 
 
                                              D e v e d o r a s   s o l i d % r i a s :   q u a l q u e r   d e p %%s i t o   p o d e   s e r   l i b e r a d o 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w "   i d = " d e p - l i b e r a c a o - r o w - $ { i d x } " > 
 
                                         < l a b e l > < i n p u t   t y p e = " r a d i o "   n a m e = " r a d - d e p - l i b - $ { i d x } "   v a l u e = " r e c l a m a n t e "   c h e c k e d   d a t a - d e p - i d x = " $ { i d x } " >   L i b e r a % % o   s i m p l e s   ( R e c l a m a n t e ) < / l a b e l > 
 
                                         < l a b e l   s t y l e = " m a r g i n - l e f t :   1 0 p x ; " > < i n p u t   t y p e = " r a d i o "   n a m e = " r a d - d e p - l i b - $ { i d x } "   v a l u e = " d e t a l h a d a "   d a t a - d e p - i d x = " $ { i d x } " >   L i b e r a % % o   d e t a l h a d a   ( C r % d i t o ,   I N S S ,   H o n . ) < / l a b e l > 
 
                                 < / d i v > 
 
                         ` ; 
 
                       
 
                         c o n t a i n e r . a p p e n d C h i l d ( d e p o s i t o D i v ) ; 
 
                       
 
                         / /   E v e n t   l i s t e n e r s   p a r a   e s t e   d e p %%s i t o   e s p e c % f i c o 
 
                         c o n s t   t i p o E l   =   $ ( ` d e p - t i p o - $ { i d x } ` ) ; 
 
                         c o n s t   p r i n c i p a l E l   =   $ ( ` d e p - p r i n c i p a l - $ { i d x } ` ) ; 
 
                         c o n s t   l i b e r a c a o R o w   =   $ ( ` d e p - l i b e r a c a o - r o w - $ { i d x } ` ) ; 
 
                       
 
                         t i p o E l . o n c h a n g e   =   ( e )   = >   { 
 
                                 l i b e r a c a o R o w . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   e . t a r g e t . v a l u e   = = =   ' g a r a n t i a ' ) ; 
 
                         } ; 
 
                       
 
                         p r i n c i p a l E l . o n c h a n g e   =   ( e )   = >   { 
 
                                 l i b e r a c a o R o w . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! e . t a r g e t . c h e c k e d ) ; 
 
                         } ; 
 
                       
 
                         / /   A t u a l i z a r   v i s i b i l i d a d e   i n i c i a l   b a s e a d o   e m   t i p o   d e   r e s p o n s a b i l i d a d e 
 
                         a t u a l i z a r V i s i b i l i d a d e D e p o s i t o P r i n c i p a l ( i d x ) ; 
 
                       
 
                         / /   E v e n t   l i s t e n e r   p a r a   b o t % o   r e m o v e r   ( e v i t a   p r o b l e m a   s a n d b o x   T a m p e r M o n k e y ) 
 
                         c o n s t   b t n R e m o v e r D e p   =   d e p o s i t o D i v . q u e r y S e l e c t o r ( ` # b t n - r e m o v e r - d e p - $ { i d x } ` ) ; 
 
                         i f   ( b t n R e m o v e r D e p )   { 
 
                                 b t n R e m o v e r D e p . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   ( )   = >   { 
 
                                         d e p o s i t o D i v . r e m o v e ( ) ; 
 
                                         c o n s t   d e p   =   w i n d o w . h c a l c S t a t e . d e p o s i t o s R e c u r s a i s . f i n d ( d   = >   d . i d x   = = =   i d x ) ; 
 
                                         i f   ( d e p )   d e p . r e m o v e d   =   t r u e ; 
 
                                 } ) ; 
 
                         } 
 
                       
 
                         / /   A r m a z e n a r   r e f e r % n c i a   n o   e s t a d o 
 
                         w i n d o w . h c a l c S t a t e . d e p o s i t o s R e c u r s a i s . p u s h ( {   i d x ,   r e m o v e d :   f a l s e   } ) ; 
 
                 } 
 
               
 
                 f u n c t i o n   a t u a l i z a r V i s i b i l i d a d e D e p o s i t o P r i n c i p a l ( i d x )   { 
 
                         c o n s t   t i p o R e s p   =   $ ( ' r e s p - t i p o ' ) ? . v a l u e   | |   ' u n i c a ' ; 
 
                         c o n s t   i s S o l i d a r i a   =   t i p o R e s p   = = =   ' s o l i d a r i a s ' ; 
 
                       
 
                         c o n s t   p r i n c i p a l R o w   =   $ ( ` d e p - p r i n c i p a l - r o w - $ { i d x } ` ) ; 
 
                         c o n s t   s o l i d a r i a I n f o   =   $ ( ` d e p - s o l i d a r i a - i n f o - $ { i d x } ` ) ; 
 
                         c o n s t   p r i n c i p a l C h k   =   $ ( ` d e p - p r i n c i p a l - $ { i d x } ` ) ; 
 
                       
 
                         i f   ( p r i n c i p a l R o w   & &   s o l i d a r i a I n f o )   { 
 
                                 i f   ( i s S o l i d a r i a )   { 
 
                                         / /   O c u l t a r   c h e c k b o x ,   m o s t r a r   i n f o ,   f o r % a r   c h e c k e d 
 
                                         p r i n c i p a l R o w . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                                         s o l i d a r i a I n f o . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                         i f   ( p r i n c i p a l C h k )   p r i n c i p a l C h k . c h e c k e d   =   t r u e ; 
 
                                 }   e l s e   { 
 
                                         / /   M o s t r a r   c h e c k b o x ,   o c u l t a r   i n f o 
 
                                         p r i n c i p a l R o w . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                         s o l i d a r i a I n f o . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                                 } 
 
                         } 
 
                 } 
 
               
 
                 f u n c t i o n   a d i c i o n a r P a g a m e n t o A n t e c i p a d o ( )   { 
 
                         c o n s t   i d x   =   w i n d o w . h c a l c S t a t e . n e x t P a g a m e n t o I d x + + ; 
 
                         c o n s t   c o n t a i n e r   =   $ ( ' p a g a m e n t o s - c o n t a i n e r ' ) ; 
 
                       
 
                         c o n s t   p a g a m e n t o D i v   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                         p a g a m e n t o D i v . i d   =   ` p a g a m e n t o - i t e m - $ { i d x } ` ; 
 
                         p a g a m e n t o D i v . c l a s s N a m e   =   ' p a g a m e n t o - i t e m ' ; 
 
                         p a g a m e n t o D i v . s t y l e . c s s T e x t   =   ' b o r d e r :   1 p x   s o l i d   # d d d ;   p a d d i n g :   8 p x ;   m a r g i n - b o t t o m :   8 p x ;   b o r d e r - r a d i u s :   4 p x ;   b a c k g r o u n d :   # f 9 f 9 f 9 ; ' ; 
 
                       
 
                         p a g a m e n t o D i v . i n n e r H T M L   =   ` 
 
                                 < d i v   s t y l e = " d i s p l a y :   f l e x ;   j u s t i f y - c o n t e n t :   s p a c e - b e t w e e n ;   a l i g n - i t e m s :   c e n t e r ;   m a r g i n - b o t t o m :   8 p x ; " > 
 
                                         < s t r o n g   s t y l e = " f o n t - s i z e :   1 1 p x ;   c o l o r :   # 6 6 6 ; " > P a g a m e n t o   A n t e c i p a d o   # $ { i d x   +   1 } < / s t r o n g > 
 
                                         < b u t t o n   t y p e = " b u t t o n "   i d = " b t n - r e m o v e r - p a g - $ { i d x } "   s t y l e = " p a d d i n g :   2 p x   8 p x ;   f o n t - s i z e :   1 0 p x ;   c o l o r :   # d c 2 6 2 6 ;   b a c k g r o u n d :   # f e e ;   b o r d e r :   1 p x   s o l i d   # f c a ;   b o r d e r - r a d i u s :   3 p x ;   c u r s o r :   p o i n t e r ; " >      R e m o v e r < / b u t t o n > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < i n p u t   t y p e = " t e x t "   i d = " p a g - i d - $ { i d x } "   p l a c e h o l d e r = " I D   d o   D e p %%s i t o "   d a t a - p a g - i d x = " $ { i d x } " > 
 
                                 < / d i v > 
 
                                 < d i v   c l a s s = " r o w " > 
 
                                         < l a b e l > < i n p u t   t y p e = " r a d i o "   n a m e = " l i b - t i p o - $ { i d x } "   v a l u e = " n e n h u m "   c h e c k e d   d a t a - p a g - i d x = " $ { i d x } " >   P a d r % o   ( e x t i n % % o ) < / l a b e l > 
 
                                         < l a b e l   s t y l e = " m a r g i n - l e f t :   1 5 p x ; " > < i n p u t   t y p e = " r a d i o "   n a m e = " l i b - t i p o - $ { i d x } "   v a l u e = " r e m a n e s c e n t e "   d a t a - p a g - i d x = " $ { i d x } " >   C o m   R e m a n e s c e n t e < / l a b e l > 
 
                                         < l a b e l   s t y l e = " m a r g i n - l e f t :   1 5 p x ; " > < i n p u t   t y p e = " r a d i o "   n a m e = " l i b - t i p o - $ { i d x } "   v a l u e = " d e v o l u c a o "   d a t a - p a g - i d x = " $ { i d x } " >   C o m   D e v o l u % % o < / l a b e l > 
 
                                 < / d i v > 
 
                                 < d i v   i d = " l i b - r e m a n e s c e n t e - c a m p o s - $ { i d x } "   c l a s s = " h i d d e n " > 
 
                                         < d i v   c l a s s = " r o w " > 
 
                                                 < i n p u t   t y p e = " t e x t "   i d = " l i b - r e m - v a l o r - $ { i d x } "   p l a c e h o l d e r = " V a l o r   R e m a n e s c e n t e   ( e x :   1 . 2 3 4 , 5 6 ) "   d a t a - p a g - i d x = " $ { i d x } " > 
 
                                                 < i n p u t   t y p e = " t e x t "   i d = " l i b - r e m - t i t u l o - $ { i d x } "   p l a c e h o l d e r = " T % t u l o   ( e x :   c u s t a s   p r o c e s s u a i s ) "   d a t a - p a g - i d x = " $ { i d x } " > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                                 < d i v   i d = " l i b - d e v o l u c a o - c a m p o s - $ { i d x } "   c l a s s = " h i d d e n " > 
 
                                         < d i v   c l a s s = " r o w " > 
 
                                                 < i n p u t   t y p e = " t e x t "   i d = " l i b - d e v - v a l o r - $ { i d x } "   p l a c e h o l d e r = " V a l o r   D e v o l u % % o   ( e x :   1 . 2 3 4 , 5 6 ) "   d a t a - p a g - i d x = " $ { i d x } " > 
 
                                         < / d i v > 
 
                                 < / d i v > 
 
                         ` ; 
 
                       
 
                         c o n t a i n e r . a p p e n d C h i l d ( p a g a m e n t o D i v ) ; 
 
                       
 
                         / /   E v e n t   l i s t e n e r s   p a r a   o s   r a d i o s   d e s t e   p a g a m e n t o 
 
                         d o c u m e n t . q u e r y S e l e c t o r A l l ( ` i n p u t [ n a m e = " l i b - t i p o - $ { i d x } " ] ` ) . f o r E a c h ( r a d i o   = >   { 
 
                                 r a d i o . a d d E v e n t L i s t e n e r ( ' c h a n g e ' ,   ( e )   = >   { 
 
                                         c o n s t   v a l o r   =   e . t a r g e t . v a l u e ; 
 
                                         $ ( ` l i b - r e m a n e s c e n t e - c a m p o s - $ { i d x } ` ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   v a l o r   ! = =   ' r e m a n e s c e n t e ' ) ; 
 
                                         $ ( ` l i b - d e v o l u c a o - c a m p o s - $ { i d x } ` ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   v a l o r   ! = =   ' d e v o l u c a o ' ) ; 
 
                                 } ) ; 
 
                         } ) ; 
 
                       
 
                         / /   E v e n t   l i s t e n e r   p a r a   b o t % o   r e m o v e r   ( e v i t a   p r o b l e m a   s a n d b o x   T a m p e r M o n k e y ) 
 
                         c o n s t   b t n R e m o v e r P a g   =   p a g a m e n t o D i v . q u e r y S e l e c t o r ( ` # b t n - r e m o v e r - p a g - $ { i d x } ` ) ; 
 
                         i f   ( b t n R e m o v e r P a g )   { 
 
                                 b t n R e m o v e r P a g . a d d E v e n t L i s t e n e r ( ' c l i c k ' ,   ( )   = >   { 
 
                                         p a g a m e n t o D i v . r e m o v e ( ) ; 
 
                                         c o n s t   p a g   =   w i n d o w . h c a l c S t a t e . p a g a m e n t o s A n t e c i p a d o s . f i n d ( p   = >   p . i d x   = = =   i d x ) ; 
 
                                         i f   ( p a g )   p a g . r e m o v e d   =   t r u e ; 
 
                                 } ) ; 
 
                         } 
 
                       
 
                         / /   A r m a z e n a r   r e f e r % n c i a   n o   e s t a d o 
 
                         w i n d o w . h c a l c S t a t e . p a g a m e n t o s A n t e c i p a d o s . p u s h ( {   i d x ,   r e m o v e d :   f a l s e   } ) ; 
 
                 } 
 
               
 
                 / /   B i n d   d o s   b o t % e s   d e   a d i c i o n a r 
 
                 $ ( ' b t n - a d d - d e p o s i t o ' ) . o n c l i c k   =   a d i c i o n a r D e p o s i t o R e c u r s a l ; 
 
                 $ ( ' b t n - a d d - p a g a m e n t o ' ) . o n c l i c k   =   a d i c i o n a r P a g a m e n t o A n t e c i p a d o ; 
 
 
 
                 / /   M % s c a r a   d e   d a t a   D D / M M / Y Y Y Y   p a r a   c a m p o s   d e   d a t a 
 
                 c o n s t   a p l i c a r M a s c a r a D a t a   =   ( i n p u t )   = >   { 
 
                         i n p u t . a d d E v e n t L i s t e n e r ( ' i n p u t ' ,   ( e )   = >   { 
 
                                 l e t   v a l o r   =   e . t a r g e t . v a l u e . r e p l a c e ( / \ D / g ,   ' ' ) ;   / /   R e m o v e   n % o - d % g i t o s 
 
                                 i f   ( v a l o r . l e n g t h   > =   2 )   { 
 
                                         v a l o r   =   v a l o r . s l i c e ( 0 ,   2 )   +   ' / '   +   v a l o r . s l i c e ( 2 ) ; 
 
                                 } 
 
                                 i f   ( v a l o r . l e n g t h   > =   5 )   { 
 
                                         v a l o r   =   v a l o r . s l i c e ( 0 ,   5 )   +   ' / '   +   v a l o r . s l i c e ( 5 ) ; 
 
                                 } 
 
                                 e . t a r g e t . v a l u e   =   v a l o r . s l i c e ( 0 ,   1 0 ) ;   / /   L i m i t a   a   D D / M M / Y Y Y Y 
 
                         } ) ; 
 
                 } ; 
 
 
 
                 / /   A p l i c a r   m % s c a r a   a o s   c a m p o s   d e   d a t a 
 
                 [ ' v a l - d a t a ' ,   ' c u s t a s - d a t a - o r i g e m ' ,   ' v a l - p e r i t o - d a t a ' ] . f o r E a c h ( i d   = >   { 
 
                         c o n s t   c a m p o   =   $ ( i d ) ; 
 
                         i f   ( c a m p o )   a p l i c a r M a s c a r a D a t a ( c a m p o ) ; 
 
                 } ) ; 
 
 
 
                 / /   T o g g l e   o r i g e m   c u s t a s :   S e n t e n % a   v s   A c %%r d % o 
 
                 $ ( ' c u s t a s - o r i g e m ' ) . o n c h a n g e   =   ( e )   = >   { 
 
                         c o n s t   i s A c o r d a o   =   e . t a r g e t . v a l u e   = = =   ' a c o r d a o ' ; 
 
                         $ ( ' c u s t a s - d a t a - c o l ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   i s A c o r d a o ) ; 
 
                         $ ( ' c u s t a s - a c o r d a o - c o l ' ) . c l a s s L i s t . t o g g l e ( ' h i d d e n ' ,   ! i s A c o r d a o ) ; 
 
                 } ; 
 
 
 
                 c o n s t   o r d e m C o p i a L a b e l s   =   { 
 
                         ' v a l - i d ' :   ' 1 )   I d   d a   P l a n i l h a ' , 
 
                         ' v a l - d a t a ' :   ' 1 )   D a t a   d a   A t u a l i z a % % o ' , 
 
                         ' v a l - c r e d i t o ' :   ' 1 )   C r % d i t o   P r i n c i p a l ' , 
 
                         ' v a l - f g t s ' :   ' 1 )   F G T S   S e p a r a d o ' , 
 
                         ' v a l - i n s s - r e c ' :   ' 2 )   I N S S   -   D e s c o n t o   R e c l a m a n t e ' , 
 
                         ' v a l - i n s s - t o t a l ' :   ' 2 )   I N S S   -   T o t a l   E m p r e s a ' , 
 
                         ' v a l - h o n - a u t o r ' :   ' 3 )   H o n o r % r i o s   d o   A u t o r ' , 
 
                         ' v a l - c u s t a s ' :   ' 4 )   C u s t a s ' 
 
                 } ; 
 
 
 
                 w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   =   [ ] ; 
 
                 w i n d o w . h c a l c P e r i t o s C o n h e c i m e n t o D e t e c t a d o s   =   [ ] ; 
 
 
 
                 f u n c t i o n   i s N o m e R o g e r i o ( n o m e )   { 
 
                         r e t u r n   / r o g e r i o | r o g % r i o / i . t e s t ( n o m e   | |   ' ' ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   a p l i c a r R e g r a s P e r i t o s D e t e c t a d o s ( p e r i t o s D e t e c t a d o s )   { 
 
                         c o n s t   n o m e s   =   A r r a y . i s A r r a y ( p e r i t o s D e t e c t a d o s )   ?   p e r i t o s D e t e c t a d o s . f i l t e r ( B o o l e a n )   :   [ ] ; 
 
                         c o n s t   t e m R o g e r i o   =   n o m e s . s o m e ( ( n o m e )   = >   i s N o m e R o g e r i o ( n o m e ) ) ; 
 
                         c o n s t   p e r i t o s C o n h e c i m e n t o   =   n o m e s . f i l t e r ( ( n o m e )   = >   ! i s N o m e R o g e r i o ( n o m e ) ) ; 
 
 
 
                         w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   =   n o m e s ; 
 
                         w i n d o w . h c a l c P e r i t o s C o n h e c i m e n t o D e t e c t a d o s   =   p e r i t o s C o n h e c i m e n t o ; 
 
 
 
                         c o n s t   o r i g e m E l   =   $ ( ' c a l c - o r i g e m ' ) ; 
 
                         c o n s t   p j c E l   =   $ ( ' c a l c - p j c ' ) ; 
 
                         c o n s t   a u t o r E l   =   $ ( ' c a l c - a u t o r ' ) ; 
 
                         c o n s t   c o l E s c l a r e c i m e n t o s E l   =   $ ( ' c o l - e s c l a r e c i m e n t o s ' ) ; 
 
                         c o n s t   r o w P e r i t o C o n t a b i l E l   =   $ ( ' r o w - p e r i t o - c o n t a b i l ' ) ; 
 
                         c o n s t   c h k P e r i t o C o n h E l   =   $ ( ' c h k - p e r i t o - c o n h ' ) ; 
 
                         c o n s t   p e r i t o C o n h C a m p o s E l   =   $ ( ' p e r i t o - c o n h - c a m p o s ' ) ; 
 
                         c o n s t   v a l P e r i t o N o m e E l   =   $ ( ' v a l - p e r i t o - n o m e ' ) ; 
 
                         c o n s t   v a l P e r i t o C o n t a b i l V a l o r E l   =   $ ( ' v a l - p e r i t o - c o n t a b i l - v a l o r ' ) ; 
 
 
 
                         i f   ( t e m R o g e r i o )   { 
 
                                 o r i g e m E l . v a l u e   =   ' p j e c a l c ' ; 
 
                                 o r i g e m E l . d i s a b l e d   =   t r u e ; 
 
                                 p j c E l . c h e c k e d   =   t r u e ; 
 
                                 p j c E l . d i s a b l e d   =   t r u e ; 
 
                                 a u t o r E l . v a l u e   =   ' p e r i t o ' ; 
 
                                 a u t o r E l . d i s a b l e d   =   t r u e ; 
 
                                 c o l E s c l a r e c i m e n t o s E l . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                 r o w P e r i t o C o n t a b i l E l . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                         }   e l s e   { 
 
                                 o r i g e m E l . d i s a b l e d   =   f a l s e ; 
 
                                 p j c E l . d i s a b l e d   =   f a l s e ; 
 
                                 a u t o r E l . d i s a b l e d   =   f a l s e ; 
 
                                 r o w P e r i t o C o n t a b i l E l . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                                 i f   ( v a l P e r i t o C o n t a b i l V a l o r E l )   { 
 
                                         v a l P e r i t o C o n t a b i l V a l o r E l . v a l u e   =   ' ' ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   C o n t r o l a r   v i s i b i l i d a d e   d o   f i e l d s e t   d e   p e r % c i a   c o n h e c i m e n t o 
 
                         c o n s t   f i e l d s e t P e r i c i a C o n h   =   $ ( ' f i e l d s e t - p e r i c i a - c o n h ' ) ; 
 
                         i f   ( p e r i t o s C o n h e c i m e n t o . l e n g t h   >   0 )   { 
 
                                 i f   ( f i e l d s e t P e r i c i a C o n h )   f i e l d s e t P e r i c i a C o n h . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                 c h k P e r i t o C o n h E l . c h e c k e d   =   t r u e ; 
 
                                 p e r i t o C o n h C a m p o s E l . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                                 v a l P e r i t o N o m e E l . v a l u e   =   p e r i t o s C o n h e c i m e n t o . j o i n ( '   |   ' ) ; 
 
                         }   e l s e   { 
 
                                 / /   E s c o n d e r   c a r d   d e   p e r % c i a   s e   n % o   h %   p e r i t o   d e   c o n h e c i m e n t o 
 
                                 i f   ( f i e l d s e t P e r i c i a C o n h )   f i e l d s e t P e r i c i a C o n h . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                         } 
 
                 } 
 
 
 
                 f u n c t i o n   a t u a l i z a r S t a t u s P r o x i m o C a m p o ( n e x t I n p u t I d   =   n u l l )   { 
 
                         / /   F u n % % o   s i m p l i f i c a d a   -   s t a t u s   r e m o v i d o   d a   i n t e r f a c e 
 
                         / /   M a n t i d a   p a r a   c o m p a t i b i l i d a d e   c o m   c %%d i g o   e x i s t e n t e 
 
                 } 
 
 
 
                 / /   T i m e l i n e   f u n c t i o n s   m o v e d   t o   p r e p . j s 
 
                 / /   r e a d T i m e l i n e B a s i c   /   e x t r a c t D a t a F r o m T i m e l i n e I t e m   /   g e t T i m e l i n e I t e m s 
 
                 / /   n o w   h a n d l e d   b y   w i n d o w . e x e c u t a r P r e p ( ) 
 
 
 
                 f u n c t i o n   c o n s t r u i r S e c a o I n t i m a c o e s ( )   { 
 
                         c o n s t   c o n t a i n e r   =   $ ( ' l i s t a - i n t i m a c o e s - c o n t a i n e r ' ) ; 
 
                         i f   ( ! c o n t a i n e r )   r e t u r n ; 
 
 
 
                         c o n s t   p a s s i v o   =   w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o   | |   [ ] ; 
 
                         c o n s t   a d v M a p   =   w i n d o w . h c a l c S t a t u s A d v o g a d o s   | |   { } ; 
 
                         c o n s t   p a r t e s I n t i m a d a s E d i t a l   =   w i n d o w . h c a l c P r e p R e s u l t ? . p a r t e s I n t i m a d a s E d i t a l   | |   [ ] ; 
 
 
 
                         c o n t a i n e r . i n n e r H T M L   =   ' ' ; 
 
 
 
                         i f   ( p a s s i v o . l e n g t h   = = =   0 )   { 
 
                                 c o n t a i n e r . i n n e r H T M L   =   ` 
 
                                         < d i v   s t y l e = " m a r g i n - b o t t o m :   5 p x ; " > 
 
                                                 < i n p u t   t y p e = " t e x t "   i d = " i n t - n o m e - p a r t e - m a n u a l "   p l a c e h o l d e r = " N o m e   d a   R e c l a m a d a "   s t y l e = " w i d t h :   1 0 0 % ;   p a d d i n g :   6 p x ;   b o x - s i z i n g :   b o r d e r - b o x ;   m a r g i n - b o t t o m :   5 p x ; " > 
 
                                                 < s e l e c t   i d = " s e l - i n t i m a c a o - m a n u a l "   s t y l e = " w i d t h :   1 0 0 % ;   p a d d i n g :   4 p x ; " > 
 
                                                         < o p t i o n   v a l u e = " d i a r i o " > D i % r i o   ( A d v o g a d o   -   A r t .   5 2 3 ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " m a n d a d o " > M a n d a d o   ( A r t .   8 8 0   -   4 8 h ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " e d i t a l " > E d i t a l   ( A r t .   8 8 0   -   4 8 h ) < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                         < / d i v > ` ; 
 
                                 r e t u r n ; 
 
                         } 
 
 
 
                         p a s s i v o . f o r E a c h ( ( p a r t e ,   i d x )   = >   { 
 
                                 c o n s t   t e m A d v o g a d o   =   a d v M a p [ p a r t e . n o m e ]   = = =   t r u e ; 
 
                                 l e t   m o d o D e f a u l t   =   ' m a n d a d o ' ; 
 
 
 
                                 i f   ( t e m A d v o g a d o )   m o d o D e f a u l t   =   ' d i a r i o ' ; 
 
                                 e l s e   i f   ( p a r t e s I n t i m a d a s E d i t a l . i n c l u d e s ( p a r t e . n o m e ) )   m o d o D e f a u l t   =   ' e d i t a l ' ; 
 
 
 
                                 c o n s t   d i v R o w   =   d o c u m e n t . c r e a t e E l e m e n t ( ' d i v ' ) ; 
 
                                 d i v R o w . c l a s s N a m e   =   ' i n t i m a c a o - r o w ' ; 
 
                                 d i v R o w . s t y l e . c s s T e x t   =   " d i s p l a y :   f l e x ;   a l i g n - i t e m s :   c e n t e r ;   j u s t i f y - c o n t e n t :   s p a c e - b e t w e e n ;   m a r g i n - b o t t o m :   6 p x ;   p a d d i n g :   6 p x ;   b a c k g r o u n d :   # f 9 f 9 f 9 ;   b o r d e r :   1 p x   s o l i d   # d d d ;   b o r d e r - r a d i u s :   4 p x ; " ; 
 
 
 
                                 / /   C h e c k b o x   p a r a   m a r c a r   c o m o   p r i n c i p a l   ( p r i m e i r a   %   m a r c a d a   p o r   p a d r % o ) 
 
                                 c o n s t   i s P r i m e i r a P o r P a d r a o   =   i d x   = = =   0 ; 
 
                               
 
                                 d i v R o w . i n n e r H T M L   =   ` 
 
                                         < d i v   s t y l e = " f l e x :   1 ;   f o n t - s i z e :   1 3 p x ;   f o n t - w e i g h t :   b o l d ;   c o l o r :   # 3 3 3 ;   o v e r f l o w :   h i d d e n ;   t e x t - o v e r f l o w :   e l l i p s i s ;   w h i t e - s p a c e :   n o w r a p ;   p a d d i n g - r i g h t :   1 0 p x ; "   t i t l e = " $ { p a r t e . n o m e } " > 
 
                                                 $ { p a r t e . n o m e } 
 
                                         < / d i v > 
 
                                         < d i v   s t y l e = " f l e x - s h r i n k :   0 ;   d i s p l a y :   f l e x ;   a l i g n - i t e m s :   c e n t e r ;   g a p :   8 p x ; " > 
 
                                                 < l a b e l   s t y l e = " f o n t - s i z e :   1 1 p x ;   m a r g i n :   0 ;   d i s p l a y :   f l e x ;   a l i g n - i t e m s :   c e n t e r ;   g a p :   3 p x ;   c o l o r :   # 6 6 6 ; " > 
 
                                                         < i n p u t   t y p e = " c h e c k b o x "   c l a s s = " c h k - p a r t e - p r i n c i p a l "   d a t a - n o m e = " $ { p a r t e . n o m e } "   $ { i s P r i m e i r a P o r P a d r a o   ?   ' c h e c k e d '   :   ' ' } > 
 
                                                         P r i n c i p a l 
 
                                                 < / l a b e l > 
 
                                                 < s e l e c t   c l a s s = " s e l - m o d o - i n t i m a c a o "   d a t a - n o m e = " $ { p a r t e . n o m e } "   s t y l e = " p a d d i n g :   4 p x ;   f o n t - s i z e :   1 2 p x ;   b o r d e r :   1 p x   s o l i d   # c c c ;   b o r d e r - r a d i u s :   4 p x ; " > 
 
                                                         < o p t i o n   v a l u e = " d i a r i o "   $ { m o d o D e f a u l t   = = =   ' d i a r i o '   ?   ' s e l e c t e d '   :   ' ' } > D i % r i o   ( A d v o g a d o   -   A r t   5 2 3 ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " m a n d a d o "   $ { m o d o D e f a u l t   = = =   ' m a n d a d o '   ?   ' s e l e c t e d '   :   ' ' } > M a n d a d o   ( A r t   8 8 0   -   4 8 h ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " e d i t a l "   $ { m o d o D e f a u l t   = = =   ' e d i t a l '   ?   ' s e l e c t e d '   :   ' ' } > E d i t a l   ( A r t   8 8 0   -   4 8 h ) < / o p t i o n > 
 
                                                         < o p t i o n   v a l u e = " i g n o r a r " > N % o   I n t i m a r < / o p t i o n > 
 
                                                 < / s e l e c t > 
 
                                         < / d i v > 
 
                                 ` ; 
 
                                 c o n t a i n e r . a p p e n d C h i l d ( d i v R o w ) ; 
 
                         } ) ; 
 
                 } 
 
 
 
                 a s y n c   f u n c t i o n   r e f r e s h D e t e c t e d P a r t e s ( )   { 
 
                         c o n s t   p a r t e s   =   a w a i t   d e r i v e P a r t e s D a t a ( ) ; 
 
 
 
                         / /   A r m a z e n a r   g l o b a l m e n t e   p a r a   u s o   e m   g e r a % % o   d e   t e x t o s 
 
                         w i n d o w . h c a l c P a r t e s D a t a   =   p a r t e s ; 
 
 
 
                         c o n s t   r e c l a m a d a s   =   ( p a r t e s ? . p a s s i v o   | |   [ ] ) . m a p ( p   = >   p . n o m e ) . f i l t e r ( B o o l e a n ) ; 
 
                         c o n s t   p e r i t o s   =   o r d e n a r C o m R o g e r i o P r i m e i r o ( e x t r a c t P e r i t o s ( p a r t e s ) ) ; 
 
                         c o n s t   a d v o g a d o s M a p   =   e x t r a c t A d v o g a d o s P o r R e c l a m a d a ( p a r t e s ) ; 
 
                         c o n s t   s t a t u s A d v M a p   =   e x t r a c t S t a t u s A d v o g a d o P o r R e c l a m a d a ( p a r t e s ) ; 
 
                         c o n s t   a d v o g a d o s A u t o r   =   e x t r a c t A d v o g a d o s D o A u t o r ( p a r t e s ) ; 
 
 
 
                         w i n d o w . h c a l c S t a t u s A d v o g a d o s   =   s t a t u s A d v M a p ; 
 
                         w i n d o w . h c a l c A d v o g a d o s A u t o r   =   a d v o g a d o s A u t o r ;   / /   C a c h e   g l o b a l   p a r a   v a l i d a % % o   d e   h o n o r % r i o s 
 
                         w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   =   p e r i t o s ;   / /   C a c h e   g l o b a l   p a r a   v a l i d a % % o   d e   h o n o r % r i o s 
 
 
 
                         / /   L o g   p a r a   d e b u g 
 
                         c o n s o l e . l o g ( ' h c a l c :   a d v o g a d o s   p o r   r e c l a m a d a ' ,   a d v o g a d o s M a p ) ; 
 
                         c o n s o l e . l o g ( ' h c a l c :   s t a t u s   a d v o g a d o   p o r   r e c l a m a d a ' ,   s t a t u s A d v M a p ) ; 
 
                         c o n s o l e . l o g ( ` [ h c a l c ]   D e t e c % % o   a t u a l i z a d a :   $ { r e c l a m a d a s . l e n g t h }   r e c l a m a d a ( s ) ,   $ { p e r i t o s . l e n g t h }   p e r i t o ( s ) ` ) ; 
 
 
 
                         a p l i c a r R e g r a s P e r i t o s D e t e c t a d o s ( p e r i t o s ) ; 
 
 
 
                         / /   L o g   d e   d e b u g 
 
                         c o n s o l e . l o g ( ` [ h c a l c ]   D e t e c % % o   a t u a l i z a d a :   $ { r e c l a m a d a s . l e n g t h }   r e c l a m a d a ( s ) ,   $ { p e r i t o s . l e n g t h }   p e r i t o ( s ) ` ) ; 
 
 
 
                         / /   L % G I C A   D E   R E S P O N S A B I L I D A D E   D I N % M I C A 
 
                         c o n s t   r e s p F i e l d s e t   =   d o c u m e n t . q u e r y S e l e c t o r ( ' f i e l d s e t   # r e s p - t i p o ' ) ? . c l o s e s t ( ' f i e l d s e t ' ) ; 
 
                         i f   ( r e c l a m a d a s . l e n g t h   < =   1   & &   r e s p F i e l d s e t )   { 
 
                                 r e s p F i e l d s e t . c l a s s L i s t . a d d ( ' h i d d e n ' ) ; 
 
                         }   e l s e   i f   ( r e c l a m a d a s . l e n g t h   >   1   & &   r e s p F i e l d s e t )   { 
 
                                 r e s p F i e l d s e t . c l a s s L i s t . r e m o v e ( ' h i d d e n ' ) ; 
 
                         } 
 
 
 
                         / /   A U T O - P R E E N C H E R   D E P O S I T A N T E   C O M   R E C L A M A D A   E X T R A I D A 
 
                         c o n s t   d e p D e p o s i t a n t e   =   $ ( ' d e p - d e p o s i t a n t e ' ) ; 
 
                         i f   ( d e p D e p o s i t a n t e   & &   r e c l a m a d a s . l e n g t h   >   0 )   { 
 
                                 i f   ( r e c l a m a d a s . l e n g t h   = = =   1 )   { 
 
                                         / /   S %%  1   r e c l a m a d a :   p r e e n c h e r   e   t r a v a r 
 
                                         d e p D e p o s i t a n t e . v a l u e   =   r e c l a m a d a s [ 0 ] ; 
 
                                         d e p D e p o s i t a n t e . d i s a b l e d   =   t r u e ; 
 
                                 }   e l s e   { 
 
                                         / /   2 +   r e c l a m a d a s :   t r a n s f o r m a r   e m   d r o p d o w n 
 
                                         c o n s t   s e l e c t E l   =   d o c u m e n t . c r e a t e E l e m e n t ( ' s e l e c t ' ) ; 
 
                                         s e l e c t E l . i d   =   ' d e p - d e p o s i t a n t e ' ; 
 
                                         s e l e c t E l . s t y l e . c s s T e x t   =   d e p D e p o s i t a n t e . s t y l e . c s s T e x t   | |   ' p a d d i n g :   8 p x ;   b o r d e r :   1 p x   s o l i d   # a a a ;   b o r d e r - r a d i u s :   4 p x ;   f o n t - s i z e :   1 4 p x ; ' ; 
 
                                         r e c l a m a d a s . f o r E a c h ( ( r e c ,   i d x )   = >   { 
 
                                                 c o n s t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ; 
 
                                                 o p t . v a l u e   =   r e c ; 
 
                                                 o p t . t e x t C o n t e n t   =   r e c ; 
 
                                                 i f   ( i d x   = = =   0 )   o p t . s e l e c t e d   =   t r u e ; 
 
                                                 s e l e c t E l . a p p e n d C h i l d ( o p t ) ; 
 
                                         } ) ; 
 
                                         d e p D e p o s i t a n t e . r e p l a c e W i t h ( s e l e c t E l ) ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   C O N S T R U I R   S E % % O   D E   I N T I M A % % E S 
 
                         c o n s t r u i r S e c a o I n t i m a c o e s ( ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   g e t P r o c e s s I d F r o m U r l ( )   { 
 
                         c o n s t   m a t c h   =   w i n d o w . l o c a t i o n . h r e f . m a t c h ( / \ / p r o c e s s o \ / ( \ d + ) / ) ; 
 
                         r e t u r n   m a t c h   ?   m a t c h [ 1 ]   :   n u l l ; 
 
                 } 
 
 
 
                 f u n c t i o n   s h a p e P a r t e s P a y l o a d ( d a d o s )   { 
 
                         c o n s t   b u i l d R e c o r d   =   ( p a r t e ,   t i p o ,   i d x ,   t o t a l )   = >   { 
 
                                 l e t   n o m e   =   p a r t e . n o m e . t r i m ( ) ; 
 
                                 r e t u r n   { 
 
                                         n o m e , 
 
                                         c p f c n p j :   p a r t e . d o c u m e n t o   | |   ' d e s c o n h e c i d o ' , 
 
                                         t i p o , 
 
                                         t e l e f o n e :   f o r m a t T e l e f o n e s ( p a r t e . p e s s o a F i s i c a ) , 
 
                                         r e p r e s e n t a n t e s :   ( p a r t e . r e p r e s e n t a n t e s   | |   [ ] ) . m a p ( r e p   = >   ( { 
 
                                                 n o m e :   r e p . n o m e . t r i m ( ) , 
 
                                                 c p f c n p j :   r e p . d o c u m e n t o   | |   ' d e s c o n h e c i d o ' , 
 
                                                 o a b :   r e p . n u m e r o O a b   | |   ' ' , 
 
                                                 t i p o :   r e p . t i p o 
 
                                         } ) ) 
 
                                 } ; 
 
                         } ; 
 
 
 
                         c o n s t   f o r m a t T e l e f o n e s   =   ( p e s s o a F i s i c a )   = >   { 
 
                                 i f   ( ! p e s s o a F i s i c a )   {   r e t u r n   ' d e s c o n h e c i d o ' ;   } 
 
                                 c o n s t   n u m b e r s   =   [ ] ; 
 
                                 i f   ( p e s s o a F i s i c a . d d d C e l u l a r   & &   p e s s o a F i s i c a . n u m e r o C e l u l a r )   { 
 
                                         n u m b e r s . p u s h ( ` ( $ { p e s s o a F i s i c a . d d d C e l u l a r } )   $ { p e s s o a F i s i c a . n u m e r o C e l u l a r } ` ) ; 
 
                                 } 
 
                                 i f   ( p e s s o a F i s i c a . d d d R e s i d e n c i a l   & &   p e s s o a F i s i c a . n u m e r o R e s i d e n c i a l )   { 
 
                                         n u m b e r s . p u s h ( ` ( $ { p e s s o a F i s i c a . d d d R e s i d e n c i a l } )   $ { p e s s o a F i s i c a . n u m e r o R e s i d e n c i a l } ` ) ; 
 
                                 } 
 
                                 i f   ( p e s s o a F i s i c a . d d d C o m e r c i a l   & &   p e s s o a F i s i c a . n u m e r o C o m e r c i a l )   { 
 
                                         n u m b e r s . p u s h ( ` ( $ { p e s s o a F i s i c a . d d d C o m e r c i a l } )   $ { p e s s o a F i s i c a . n u m e r o C o m e r c i a l } ` ) ; 
 
                                 } 
 
                                 r e t u r n   n u m b e r s . j o i n ( '   |   ' )   | |   ' d e s c o n h e c i d o ' ; 
 
                         } ; 
 
 
 
                         c o n s t   a t i v o   =   ( d a d o s ? . A T I V O   | |   [ ] ) . m a p ( ( p a r t e ,   i d x )   = >   b u i l d R e c o r d ( p a r t e ,   ' A U T O R ' ,   i d x ,   d a d o s . A T I V O . l e n g t h ) ) ; 
 
                         c o n s t   p a s s i v o   =   ( d a d o s ? . P A S S I V O   | |   [ ] ) . m a p ( ( p a r t e ,   i d x )   = >   b u i l d R e c o r d ( p a r t e ,   ' R % U ' ,   i d x ,   d a d o s . P A S S I V O . l e n g t h ) ) ; 
 
                         c o n s t   o u t r o s   =   ( d a d o s ? . T E R C E I R O S   | |   [ ] ) . m a p ( ( p a r t e ,   i d x )   = >   b u i l d R e c o r d ( p a r t e ,   p a r t e . t i p o   | |   ' T E R C E I R O ' ,   i d x ,   d a d o s . T E R C E I R O S . l e n g t h ) ) ; 
 
 
 
                         r e t u r n   {   a t i v o ,   p a s s i v o ,   o u t r o s   } ; 
 
                 } 
 
 
 
                 a s y n c   f u n c t i o n   f e t c h P a r t e s V i a A p i ( )   { 
 
                         c o n s t   t r t H o s t   =   w i n d o w . l o c a t i o n . h o s t ; 
 
                         c o n s t   b a s e U r l   =   ` h t t p s : / / $ { t r t H o s t } ` ; 
 
                         c o n s t   i d P r o c e s s o   =   g e t P r o c e s s I d F r o m U r l ( ) ; 
 
                         i f   ( ! i d P r o c e s s o )   { 
 
                                 c o n s o l e . w a r n ( ' h c a l c :   i d P r o c e s s o   n % o   d e t e c t a d o   n a   U R L . ' ) ; 
 
                                 r e t u r n   n u l l ; 
 
                         } 
 
                         c o n s t   u r l   =   ` $ { b a s e U r l } / p j e - c o m u m - a p i / a p i / p r o c e s s o s / i d / $ { i d P r o c e s s o } / p a r t e s ` ; 
 
                         t r y   { 
 
                                 c o n s t   r e s p o n s e   =   a w a i t   f e t c h ( u r l ,   {   c r e d e n t i a l s :   ' i n c l u d e '   } ) ; 
 
                                 i f   ( ! r e s p o n s e . o k )   { 
 
                                         t h r o w   n e w   E r r o r ( ` A P I   r e t o r n o u   $ { r e s p o n s e . s t a t u s } ` ) ; 
 
                                 } 
 
                                 c o n s t   j s o n   =   a w a i t   r e s p o n s e . j s o n ( ) ; 
 
                                 c o n s t   p a r t e s   =   s h a p e P a r t e s P a y l o a d ( j s o n ) ; 
 
                                 / /   A r m a z e n a r   n o   c a c h e 
 
                                 c o n s t   P R O C E S S _ C A C H E   =   w i n d o w . c a l c P a r t e s C a c h e   | |   { } ; 
 
                                 P R O C E S S _ C A C H E [ i d P r o c e s s o ]   =   p a r t e s ; 
 
                                 w i n d o w . c a l c P a r t e s C a c h e   =   P R O C E S S _ C A C H E ; 
 
 
 
                                 / /   L I M I T A R   C A C H E :   M a n t e r   a p e n a s   %Q%l t i m a s   5   e n t r a d a s   p a r a   p r e v e n i r   c r e s c i m e n t o   i l i m i t a d o 
 
                                 c o n s t   k e y s   =   O b j e c t . k e y s ( w i n d o w . c a l c P a r t e s C a c h e ) ; 
 
                                 i f   ( k e y s . l e n g t h   >   5 )   { 
 
                                         d e l e t e   w i n d o w . c a l c P a r t e s C a c h e [ k e y s [ 0 ] ] ; 
 
                                         c o n s o l e . l o g ( ' h c a l c :   c a c h e   l i m i t a d o   a   5   e n t r a d a s ,   r e m o v i d a   m a i s   a n t i g a ' ) ; 
 
                                 } 
 
 
 
                                 c o n s o l e . l o g ( ' h c a l c :   p a r t e s   e x t r a % d a s   v i a   A P I ' ,   p a r t e s ) ; 
 
                                 r e t u r n   p a r t e s ; 
 
                         }   c a t c h   ( e r r o r )   { 
 
                                 c o n s o l e . e r r o r ( ' h c a l c :   f a l h a   a o   b u s c a r   p a r t e s   v i a   A P I ' ,   e r r o r ) ; 
 
                                 r e t u r n   n u l l ; 
 
                         } 
 
                 } 
 
 
 
                 a s y n c   f u n c t i o n   d e r i v e P a r t e s D a t a ( )   { 
 
                         / /   I n i c i a l i z a r   c a c h e   s e   n % o   e x i s t i r 
 
                         i f   ( ! w i n d o w . c a l c P a r t e s C a c h e )   { 
 
                                 w i n d o w . c a l c P a r t e s C a c h e   =   { } ; 
 
                         } 
 
                         c o n s t   c a c h e   =   w i n d o w . c a l c P a r t e s C a c h e ; 
 
                         c o n s t   p r o c e s s I d   =   g e t P r o c e s s I d F r o m U r l ( ) ; 
 
 
 
                         / /   1 .   T e n t a r   c a c h e   p r i m e i r o 
 
                         i f   ( p r o c e s s I d   & &   c a c h e [ p r o c e s s I d ] )   { 
 
                                 c o n s o l e . l o g ( ' h c a l c :   u s a n d o   d a d o s   d o   c a c h e ' ,   c a c h e [ p r o c e s s I d ] ) ; 
 
                                 r e t u r n   c a c h e [ p r o c e s s I d ] ; 
 
                         } 
 
 
 
                         / /   2 .   T e n t a r   b u s c a r   v i a   A P I 
 
                         i f   ( p r o c e s s I d )   { 
 
                                 c o n s t   a p i D a t a   =   a w a i t   f e t c h P a r t e s V i a A p i ( ) ; 
 
                                 i f   ( a p i D a t a )   { 
 
                                         r e t u r n   a p i D a t a ; 
 
                                 } 
 
                         } 
 
 
 
                         / /   3 .   F a l l b a c k :   b u s c a r   q u a l q u e r   c a c h e   d i s p o n % v e l 
 
                         c o n s t   f a l l b a c k K e y   =   p r o c e s s I d   ?   O b j e c t . k e y s ( c a c h e ) . f i n d ( ( k e y )   = >   k e y . i n c l u d e s ( p r o c e s s I d ) )   :   n u l l ; 
 
                         i f   ( f a l l b a c k K e y )   { 
 
                                 c o n s o l e . l o g ( ' h c a l c :   u s a n d o   c a c h e   a l t e r n a t i v o ' ,   c a c h e [ f a l l b a c k K e y ] ) ; 
 
                                 r e t u r n   c a c h e [ f a l l b a c k K e y ] ; 
 
                         } 
 
 
 
                         c o n s t   c a c h e d V a l u e s   =   O b j e c t . v a l u e s ( c a c h e ) ; 
 
                         i f   ( c a c h e d V a l u e s . l e n g t h   >   0 )   { 
 
                                 c o n s o l e . l o g ( ' h c a l c :   u s a n d o   p r i m e i r o   c a c h e   d i s p o n % v e l ' ,   c a c h e d V a l u e s [ 0 ] ) ; 
 
                                 r e t u r n   c a c h e d V a l u e s [ 0 ] ; 
 
                         } 
 
 
 
                         / /   4 .   % l t i m o   r e c u r s o :   p a r s e a r   D O M 
 
                         c o n s o l e . w a r n ( ' h c a l c :   u s a n d o   p a r s e a m e n t o   d o   D O M   ( p o d e   s e r   i m p r e c i s o ) ' ) ; 
 
                         r e t u r n   p a r s e P a r t e s F r o m D o m ( ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   p a r s e P a r t e s F r o m D o m ( )   { 
 
                         c o n s t   r o w s   =   d o c u m e n t . q u e r y S e l e c t o r A l l ( ' d i v [ c l a s s * = " b l o c o - p a r t i c i p a n t e " ]   t b o d y   t r ' ) ; 
 
                         c o n s t   d a t a   =   {   a t i v o :   [ ] ,   p a s s i v o :   [ ] ,   o u t r o s :   [ ]   } ; 
 
                         r o w s . f o r E a c h ( ( r o w )   = >   { 
 
                                 c o n s t   t e x t   =   r o w . i n n e r T e x t   | |   ' ' ; 
 
                                 c o n s t   v a l u e   =   t e x t . s p l i t ( ' \ n ' ) . m a p ( ( l )   = >   l . t r i m ( ) ) . f i n d ( B o o l e a n )   | |   t e x t . t r i m ( ) ; 
 
                                 i f   ( ! v a l u e )   {   r e t u r n ;   } 
 
                                 i f   ( / r e c l a m a n t e | e x e q u e n t e | a u t o r / i . t e s t ( t e x t ) )   { 
 
                                         d a t a . a t i v o . p u s h ( {   n o m e :   v a l u e   } ) ; 
 
                                 }   e l s e   i f   ( / r e c l a m a d o | r % u | e x e c u t a d o / i . t e s t ( t e x t ) )   { 
 
                                         d a t a . p a s s i v o . p u s h ( {   n o m e :   v a l u e   } ) ; 
 
                                 }   e l s e   { 
 
                                         d a t a . o u t r o s . p u s h ( {   n o m e :   v a l u e ,   t i p o :   ' O U T R O '   } ) ; 
 
                                 } 
 
                         } ) ; 
 
                         r e t u r n   d a t a ; 
 
                 } 
 
 
 
                 f u n c t i o n   e x t r a c t P e r i t o s ( p a r t e s )   { 
 
                         c o n s t   o u t r o s   =   p a r t e s ? . o u t r o s   | |   [ ] ; 
 
                         / /   F i l t r a r   p o r   t i p o   ' P E R I T O '   o u   q u a l q u e r   v a r i a % % o   n o   n o m e / t i p o 
 
                         r e t u r n   o u t r o s . f i l t e r ( ( p a r t )   = >   { 
 
                                 c o n s t   t i p o   =   ( p a r t . t i p o   | |   ' ' ) . t o U p p e r C a s e ( ) ; 
 
                                 c o n s t   n o m e   =   ( p a r t . n o m e   | |   ' ' ) . t o U p p e r C a s e ( ) ; 
 
                                 r e t u r n   t i p o . i n c l u d e s ( ' P E R I T O ' )   | |   n o m e . i n c l u d e s ( ' P E R I T O ' ) ; 
 
                         } ) . m a p ( ( p a r t )   = >   p a r t . n o m e ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   o r d e n a r C o m R o g e r i o P r i m e i r o ( n o m e s )   { 
 
                         i f   ( ! A r r a y . i s A r r a y ( n o m e s )   | |   n o m e s . l e n g t h   = = =   0 )   {   r e t u r n   [ ] ;   } 
 
                         c o n s t   r o g e r i o   =   [ ] ; 
 
                         c o n s t   d e m a i s   =   [ ] ; 
 
                         n o m e s . f o r E a c h ( ( n o m e )   = >   { 
 
                                 i f   ( / r o g e r i o / i . t e s t ( n o m e   | |   ' ' ) )   { 
 
                                         r o g e r i o . p u s h ( n o m e ) ; 
 
                                 }   e l s e   { 
 
                                         d e m a i s . p u s h ( n o m e ) ; 
 
                                 } 
 
                         } ) ; 
 
                         r e t u r n   [ . . . r o g e r i o ,   . . . d e m a i s ] ; 
 
                 } 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   F U N % % E S   D E   E X T R A % % O   D E   R E P R E S E N T A N T E S 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 w i n d o w . h c a l c P a r t e s D a t a   =   n u l l ;   / /   C a c h e   g l o b a l   d e   p a r t e s   p a r a   u s o   e m   g e r a % % o   d e   t e x t o s 
 
 
 
                 f u n c t i o n   e x t r a c t A d v o g a d o s P o r R e c l a m a d a ( p a r t e s )   { 
 
                         c o n s t   m a p   =   { } ; 
 
                         i f   ( ! p a r t e s ? . p a s s i v o )   {   r e t u r n   m a p ;   } 
 
                         p a r t e s . p a s s i v o . f o r E a c h ( ( r e c l a m a d a )   = >   { 
 
                                 c o n s t   r e p s   =   r e c l a m a d a . r e p r e s e n t a n t e s   | |   [ ] ; 
 
                                 c o n s t   a d v o g a d o s   =   r e p s . f i l t e r ( r e p   = >   { 
 
                                         c o n s t   t i p o   =   ( r e p . t i p o   | |   ' ' ) . t o U p p e r C a s e ( ) ; 
 
                                         r e t u r n   t i p o . i n c l u d e s ( ' A D V O G A D O ' )   | |   t i p o . i n c l u d e s ( ' O A B ' ) ; 
 
                                 } ) . m a p ( r e p   = >   ( { 
 
                                         n o m e :   r e p . n o m e , 
 
                                         o a b :   r e p . o a b   | |   ' ' 
 
                                 } ) ) ; 
 
                                 m a p [ r e c l a m a d a . n o m e ]   =   a d v o g a d o s ; 
 
                         } ) ; 
 
                         r e t u r n   m a p ; 
 
                 } 
 
 
 
                 f u n c t i o n   e x t r a c t A d v o g a d o s D o A u t o r ( p a r t e s )   { 
 
                         c o n s t   a d v o g a d o s   =   [ ] ; 
 
                         i f   ( ! p a r t e s ? . a t i v o )   {   r e t u r n   a d v o g a d o s ;   } 
 
                         p a r t e s . a t i v o . f o r E a c h ( ( r e c l a m a n t e )   = >   { 
 
                                 c o n s t   r e p s   =   r e c l a m a n t e . r e p r e s e n t a n t e s   | |   [ ] ; 
 
                                 c o n s t   a d v s   =   r e p s . f i l t e r ( r e p   = >   { 
 
                                         c o n s t   t i p o   =   ( r e p . t i p o   | |   ' ' ) . t o U p p e r C a s e ( ) ; 
 
                                         r e t u r n   t i p o . i n c l u d e s ( ' A D V O G A D O ' )   | |   t i p o . i n c l u d e s ( ' O A B ' ) ; 
 
                                 } ) . m a p ( r e p   = >   ( { 
 
                                         n o m e :   r e p . n o m e , 
 
                                         o a b :   r e p . o a b   | |   ' ' , 
 
                                         n o m e N o r m a l i z a d o :   n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( r e p . n o m e ) 
 
                                 } ) ) ; 
 
                                 a d v o g a d o s . p u s h ( . . . a d v s ) ; 
 
                         } ) ; 
 
                         c o n s o l e . l o g ( ' h c a l c :   a d v o g a d o s   d o   a u t o r   e x t r a % d o s : ' ,   a d v o g a d o s ) ; 
 
                         r e t u r n   a d v o g a d o s ; 
 
                 } 
 
 
 
                 f u n c t i o n   v e r i f i c a r S e N o m e E A d v o g a d o A u t o r ( n o m e P a r a V e r i f i c a r ,   a d v o g a d o s A u t o r )   { 
 
                         i f   ( ! n o m e P a r a V e r i f i c a r   | |   ! a d v o g a d o s A u t o r   | |   a d v o g a d o s A u t o r . l e n g t h   = = =   0 )   { 
 
                                 r e t u r n   f a l s e ; 
 
                         } 
 
                         c o n s t   n o m e N o r m   =   n o r m a l i z a r N o m e P a r a C o m p a r a c a o ( n o m e P a r a V e r i f i c a r ) ; 
 
                         r e t u r n   a d v o g a d o s A u t o r . s o m e ( a d v   = >   { 
 
                                 c o n s t   m a t c h   =   a d v . n o m e N o r m a l i z a d o   = = =   n o m e N o r m   | | 
 
                                                             n o m e N o r m . i n c l u d e s ( a d v . n o m e N o r m a l i z a d o )   | | 
 
                                                             a d v . n o m e N o r m a l i z a d o . i n c l u d e s ( n o m e N o r m ) ; 
 
                                 i f   ( m a t c h )   { 
 
                                         c o n s o l e . l o g ( ` h c a l c :   m a t c h   e n c o n t r a d o   -   " $ { n o m e P a r a V e r i f i c a r } "   =   a d v o g a d o   a u t o r   " $ { a d v . n o m e } " ` ) ; 
 
                                 } 
 
                                 r e t u r n   m a t c h ; 
 
                         } ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   e x t r a c t S t a t u s A d v o g a d o P o r R e c l a m a d a ( p a r t e s )   { 
 
                         c o n s t   m a p   =   { } ; 
 
                         i f   ( ! p a r t e s ? . p a s s i v o )   {   r e t u r n   m a p ;   } 
 
 
 
                         p a r t e s . p a s s i v o . f o r E a c h ( ( r e c l a m a d a )   = >   { 
 
                                 c o n s t   r e p s   =   A r r a y . i s A r r a y ( r e c l a m a d a . r e p r e s e n t a n t e s )   ?   r e c l a m a d a . r e p r e s e n t a n t e s   :   [ ] ; 
 
                                 c o n s t   t e m R e p r e s e n t a n t e   =   r e p s . l e n g t h   >   0 ; 
 
 
 
                                 c o n s t   t e m I n d i c a d o r A d v   =   r e p s . s o m e ( ( r e p )   = >   { 
 
                                         c o n s t   t i p o   =   ( r e p ? . t i p o   | |   ' ' ) . t o U p p e r C a s e ( ) ; 
 
                                         c o n s t   o a b   =   ( r e p ? . o a b   | |   r e p ? . n u m e r o O a b   | |   ' ' ) . t o S t r i n g ( ) . t r i m ( ) ; 
 
                                         r e t u r n   t i p o . i n c l u d e s ( ' A D V O G A D O ' )   | |   t i p o . i n c l u d e s ( ' O A B ' )   | |   o a b   ! = =   ' ' ; 
 
                                 } ) ; 
 
 
 
                                 m a p [ r e c l a m a d a . n o m e ]   =   t e m R e p r e s e n t a n t e   | |   t e m I n d i c a d o r A d v ; 
 
                         } ) ; 
 
 
 
                         r e t u r n   m a p ; 
 
                 } 
 
 
 
                 f u n c t i o n   t e m A d v o g a d o ( n o m e R e c l a m a d a ,   a d v o g a d o s M a p )   { 
 
                         i f   ( ! a d v o g a d o s M a p   | |   ! n o m e R e c l a m a d a )   {   r e t u r n   f a l s e ;   } 
 
                         c o n s t   r e p s   =   a d v o g a d o s M a p [ n o m e R e c l a m a d a ]   | |   [ ] ; 
 
                         r e t u r n   r e p s . l e n g t h   >   0 ; 
 
                 } 
 
 
 
                 f u n c t i o n   o b t e r R e c l a m a d a s S e m A d v o g a d o ( p a r t e s ,   a d v o g a d o s M a p )   { 
 
                         i f   ( ! p a r t e s ? . p a s s i v o )   {   r e t u r n   [ ] ;   } 
 
                         r e t u r n   p a r t e s . p a s s i v o . f i l t e r ( r e c   = >   ! t e m A d v o g a d o ( r e c . n o m e ,   a d v o g a d o s M a p ) ) . m a p ( r e c   = >   r e c . n o m e ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   o b t e r R e c l a m a d a s C o m A d v o g a d o ( p a r t e s ,   a d v o g a d o s M a p )   { 
 
                         i f   ( ! p a r t e s ? . p a s s i v o )   {   r e t u r n   [ ] ;   } 
 
                         r e t u r n   p a r t e s . p a s s i v o . f i l t e r ( r e c   = >   t e m A d v o g a d o ( r e c . n o m e ,   a d v o g a d o s M a p ) ) . m a p ( r e c   = >   r e c . n o m e ) ; 
 
                 } 
 
 
 
                 / /   O T I M I Z A % % O :   a d i a r   r e f r e s h   a t %   b r o w s e r   e s t a r   o c i o s o   ( n % o   c o m p e t e   c o m   c a r r e g a m e n t o ) 
 
                 i f   ( t y p e o f   r e q u e s t I d l e C a l l b a c k   = = =   ' f u n c t i o n ' )   { 
 
                         r e q u e s t I d l e C a l l b a c k ( ( )   = >   r e f r e s h D e t e c t e d P a r t e s ( ) ,   {   t i m e o u t :   3 0 0 0   } ) ; 
 
                 }   e l s e   { 
 
                         s e t T i m e o u t ( r e f r e s h D e t e c t e d P a r t e s ,   1 5 0 0 ) ;   / /   f a l l b a c k   p a r a   b r o w s e r s   s e m   r I C 
 
                 } 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   4 .   L % G I C A   D E   N A V E G A % % O   " C O L E T A   I N T E L I G E N T E " 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 c o n s t   o r d e r S e q u e n c e   =   [ 
 
                         ' v a l - i d ' ,   ' v a l - d a t a ' ,   ' v a l - c r e d i t o ' ,   ' v a l - f g t s ' , 
 
                         ' v a l - i n s s - r e c ' ,   ' v a l - i n s s - t o t a l ' ,   ' v a l - h o n - a u t o r ' ,   ' v a l - c u s t a s ' 
 
                 ] ; 
 
 
 
                 f u n c t i o n   u p d a t e H i g h l i g h t ( c u r r e n t I d   =   n u l l )   { 
 
                         o r d e r S e q u e n c e . f o r E a c h ( ( i d )   = >   $ ( i d ) . c l a s s L i s t . r e m o v e ( ' h i g h l i g h t ' ) ) ; 
 
                         c o n s t   v i s i b l e I n p u t s   =   o r d e r S e q u e n c e . f i l t e r ( ( i d )   = >   ! $ ( i d ) . c l a s s L i s t . c o n t a i n s ( ' h i d d e n ' ) ) ; 
 
                         i f   ( v i s i b l e I n p u t s . l e n g t h   = = =   0 )   r e t u r n ; 
 
                         l e t   n e x t I n d e x   =   0 ; 
 
                         i f   ( c u r r e n t I d )   { 
 
                                 c o n s t   c u r r e n t I n d e x   =   v i s i b l e I n p u t s . i n d e x O f ( c u r r e n t I d ) ; 
 
                                 i f   ( c u r r e n t I n d e x   ! = =   - 1   & &   c u r r e n t I n d e x   <   v i s i b l e I n p u t s . l e n g t h   -   1 )   { 
 
                                         n e x t I n d e x   =   c u r r e n t I n d e x   +   1 ; 
 
                                 }   e l s e   i f   ( c u r r e n t I n d e x   = = =   v i s i b l e I n p u t s . l e n g t h   -   1 )   { 
 
                                         r e t u r n ; 
 
                                 } 
 
                         } 
 
                         c o n s t   n e x t I n p u t I d   =   v i s i b l e I n p u t s [ n e x t I n d e x ] ; 
 
                         $ ( n e x t I n p u t I d ) . c l a s s L i s t . a d d ( ' h i g h l i g h t ' ) ; 
 
                         $ ( n e x t I n p u t I d ) . f o c u s ( ) ; 
 
                         a t u a l i z a r S t a t u s P r o x i m o C a m p o ( n e x t I n p u t I d ) ; 
 
                 } 
 
 
 
                 o r d e r S e q u e n c e . f o r E a c h ( ( i d )   = >   { 
 
                         c o n s t   e l   =   $ ( i d ) ; 
 
                         e l . a d d E v e n t L i s t e n e r ( ' p a s t e ' ,   ( )   = >   { 
 
                                 s e t T i m e o u t ( ( )   = >   { 
 
                                         e l . v a l u e   =   e l . v a l u e . t r i m ( ) ; 
 
                                         u p d a t e H i g h l i g h t ( i d ) ; 
 
                                 } ,   1 0 ) ; 
 
                         } ) ; 
 
                         e l . a d d E v e n t L i s t e n e r ( ' f o c u s ' ,   ( )   = >   { 
 
                                 o r d e r S e q u e n c e . f o r E a c h ( ( i )   = >   $ ( i ) . c l a s s L i s t . r e m o v e ( ' h i g h l i g h t ' ) ) ; 
 
                                 e l . c l a s s L i s t . a d d ( ' h i g h l i g h t ' ) ; 
 
                         } ) ; 
 
                 } ) ; 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   5 .   F U N % % E S   A U X I L I A R E S   D E   C % L C U L O   E   T E X T O 
 
                 f u n c t i o n   p a r s e M o n e y ( s t r )   { 
 
                         i f   ( ! s t r )   r e t u r n   0 ; 
 
                         s t r   =   s t r . r e p l a c e ( / [ R $ \ s ] / g ,   ' ' ) . r e p l a c e ( / \ . / g ,   ' ' ) . r e p l a c e ( ' , ' ,   ' . ' ) ; 
 
                         c o n s t   n u m   =   p a r s e F l o a t ( s t r ) ; 
 
                         r e t u r n   i s N a N ( n u m )   ?   0   :   n u m ; 
 
                 } 
 
 
 
                 f u n c t i o n   f o r m a t M o n e y ( n u m )   { 
 
                         r e t u r n   n u m . t o L o c a l e S t r i n g ( ' p t - B R ' ,   {   s t y l e :   ' c u r r e n c y ' ,   c u r r e n c y :   ' B R L '   } ) . r e p l a c e ( / \ s / g ,   ' ' ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   n o r m a l i z e M o n e y I n p u t ( v a l )   { 
 
                         i f   ( ! v a l   | |   v a l   = = =   ' [ V A L O R ] ' )   r e t u r n   v a l ; 
 
                         c o n s t   p a r s e d   =   p a r s e M o n e y ( v a l ) ; 
 
                         i f   ( p a r s e d   = = =   0   & &   ! / ^ \ s * 0 / . t e s t ( v a l ) )   r e t u r n   v a l ; 
 
                         r e t u r n   f o r m a t M o n e y ( p a r s e d ) ; 
 
                 } 
 
 
 
                 f u n c t i o n   b o l d ( t e x t )   {   r e t u r n   ` < s t r o n g > $ { t e x t } < / s t r o n g > ` ;   } 
 
                 f u n c t i o n   u ( t e x t )   {   r e t u r n   ` < u > $ { t e x t } < / u > ` ;   } 
 
 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 / /   6 .   G E R A D O R   D E   D E C I S % O   H T M L   ( O   C O R E ) 
 
                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                 $ ( ' b t n - g r a v a r ' ) . o n c l i c k   =   ( )   = >   { 
 
                         d b g ( ' C l i q u e   e m   G r a v a r   D e c i s a o   d e t e c t a d o . ' ) ; 
 
                         l e t   t e x t   =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > V i s t o s . < / p > ` ; 
 
                         l e t   h o u v e D e p o s i t o D i r e t o   =   f a l s e ; 
 
                         l e t   h o u v e L i b e c a o D e t a l h a d a   =   f a l s e ; 
 
                         c o n s t   p a s s i v o T o t a l   =   ( w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o   | |   [ ] ) . l e n g t h ; 
 
 
 
                         c o n s t   a u t o r i a   =   $ ( ' c a l c - a u t o r ' ) . o p t i o n s [ $ ( ' c a l c - a u t o r ' ) . s e l e c t e d I n d e x ] . t e x t ; 
 
                         c o n s t   i d P l a n i l h a   =   $ ( ' v a l - i d ' ) . v a l u e   | |   ' [ I D   D A   P L A N I L H A ] ' ; 
 
                         c o n s t   v a l D a t a   =   $ ( ' v a l - d a t a ' ) . v a l u e   | |   ' [ D A T A ] ' ; 
 
                         c o n s t   v a l C r e d i t o   =   $ ( ' v a l - c r e d i t o ' ) . v a l u e   | |   ' [ V A L O R ] ' ; 
 
                         c o n s t   v a l F g t s   =   $ ( ' v a l - f g t s ' ) . v a l u e   | |   ' [ V A L O R   F G T S ] ' ; 
 
                         c o n s t   i s P e r i t o   =   $ ( ' c a l c - a u t o r ' ) . v a l u e   = = =   ' p e r i t o ' ; 
 
                         c o n s t   p e r i t o E s c l a r e c e u   =   $ ( ' c a l c - e s c l a r e c i m e n t o s ' ) . c h e c k e d ; 
 
                         c o n s t   p e c a P e r i t o   =   $ ( ' c a l c - p e c a - p e r i t o ' ) . v a l u e   | |   ' [ I D   P E % A ] ' ; 
 
                         c o n s t   i n d i c e   =   $ ( ' c a l c - i n d i c e ' ) . v a l u e ; 
 
                         c o n s t   i s F g t s S e p   =   $ ( ' c a l c - f g t s ' ) . c h e c k e d ; 
 
                         c o n s t   i g n o r a r I n s s   =   $ ( ' i g n o r a r - i n s s ' ) . c h e c k e d ; 
 
 
 
                         c o n s t   x x x   =   ( )   = >   u ( b o l d ( ' X X X ' ) ) ; 
 
 
 
                         c o n s t   a p p e n d B a s e A t e A n t e s P e r i c i a i s   =   ( { 
 
                                 i d C a l c u l o , 
 
                                 u s a r P l a c e h o l d e r   =   f a l s e , 
 
                                 r e c l a m a d a L a b e l   =   ' ' 
 
                         } )   = >   { 
 
                                 l e t   i n t r o T x t   =   ' ' ; 
 
                                 c o n s t   v C r e d i t o   =   u s a r P l a c e h o l d e r   ?   ' R $ X X X '   :   ` R $ $ { v a l C r e d i t o } ` ; 
 
                                 c o n s t   v F g t s   =   u s a r P l a c e h o l d e r   ?   ' R $ X X X '   :   ` R $ $ { v a l F g t s } ` ; 
 
                                 c o n s t   v D a t a   =   u s a r P l a c e h o l d e r   ?   ' X X X '   :   v a l D a t a ; 
 
 
 
                                 i f   ( i s P e r i t o   & &   p e r i t o E s c l a r e c e u )   { 
 
                                         i n t r o T x t   + =   ` A s   i m p u g n a % % e s   a p r e s e n t a d a s   j %   f o r a m   o b j e t o   d e   e s c l a r e c i m e n t o s   p e l o   S r .   P e r i t o   s o b   o   # $ { b o l d ( p e c a P e r i t o ) } ,   n a d a   h a v e n d o   a   s e r   r e p a r a d o   n o   l a u d o .   P o r t a n t o ,   H O M O L O G O   o s   c % l c u l o s   d o   e x p e r t   ( # $ { b o l d ( i d C a l c u l o ) } ) ,   ` ; 
 
                                 }   e l s e   { 
 
                                         i n t r o T x t   + =   ` T e n d o   e m   v i s t a   a   c o n c o r d % n c i a   d a s   p a r t e s ,   H O M O L O G O   o s   c % l c u l o s   a p r e s e n t a d o s   p e l o ( a )   $ { u ( a u t o r i a ) }   ( # $ { b o l d ( i d C a l c u l o ) } ) ,   ` ; 
 
                                 } 
 
 
 
                                 / /   V e r i f i c a r   s e   F G T S   f o i   d e p o s i t a d o   ( p a r a   e v i t a r   c o n t r a d i % % o ) 
 
                                 c o n s t   f g t s T i p o   =   i s F g t s S e p   ?   ( d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " f g t s - t i p o " ] : c h e c k e d ' ) ? . v a l u e   | |   ' d e v i d o ' )   :   ' d e v i d o ' ; 
 
                                 c o n s t   f g t s J a D e p o s i t a d o   =   f g t s T i p o   = = =   ' d e p o s i t a d o ' ; 
 
 
 
                                 i f   ( i s F g t s S e p   & &   ! f g t s J a D e p o s i t a d o )   { 
 
                                         / /   F G T S   d e v i d o   ( a   s e r   r e c o l h i d o ) 
 
                                         i n t r o T x t   + =   ` f i x a n d o   o   c r % d i t o   d o   a u t o r   e m   $ { b o l d ( v C r e d i t o ) }   r e l a t i v o   a o   p r i n c i p a l ,   e   $ { b o l d ( v F g t s ) }   r e l a t i v o   a o   $ { b o l d ( ' F G T S ' ) }   a   s e r   r e c o l h i d o   e m   c o n t a   v i n c u l a d a ,   a t u a l i z a d o s   p a r a   $ { b o l d ( v D a t a ) } .   ` ; 
 
                                 }   e l s e   i f   ( i s F g t s S e p   & &   f g t s J a D e p o s i t a d o )   { 
 
                                         / /   F G T S   d e p o s i t a d o   ( n % o   m e n c i o n a   " a   s e r   r e c o l h i d o " ) 
 
                                         i n t r o T x t   + =   ` f i x a n d o   o   c r % d i t o   d o   a u t o r   e m   $ { b o l d ( v C r e d i t o ) } ,   a t u a l i z a d o   p a r a   $ { b o l d ( v D a t a ) } .   ` ; 
 
                                 }   e l s e   { 
 
                                         / /   S e m   F G T S   s e p a r a d o 
 
                                         i n t r o T x t   + =   ` f i x a n d o   o   c r % d i t o   e m   $ { b o l d ( v C r e d i t o ) } ,   r e f e r e n t e   a o   v a l o r   p r i n c i p a l ,   a t u a l i z a d o   p a r a   $ { b o l d ( v D a t a ) } .   ` ; 
 
                                 } 
 
 
 
                                 i f   ( i n d i c e   = = =   ' a d c 5 8 ' )   { 
 
                                         i f   ( i s F g t s S e p )   { 
 
                                                 i n t r o T x t   + =   ` A   a t u a l i z a % % o   f o i   f e i t a   n a   f o r m a   d a   L e i   1 4 . 9 0 5 / 2 0 2 4   e   d a   d e c i s % o   d a   S D I - 1   d o   C .   T S T   ( I P C A - E   a t %   a   d i s t r i b u i % % o ;   t a x a   S e l i c   a t %   2 9 / 0 8 / 2 0 2 4 ,   e   I P C A   +   j u r o s   d e   m o r a   a   p a r t i r   d e   3 0 / 0 8 / 2 0 2 4 ) . ` ; 
 
                                         }   e l s e   { 
 
                                                 i n t r o T x t   + =   ` A   c o r r e % % o   m o n e t % r i a   f o i   r e a l i z a d a   p e l o   I P C A - E   n a   f a s e   p r % - j u d i c i a l   e ,   a   p a r t i r   d o   a j u i z a m e n t o ,   p e l a   t a x a   S E L I C   ( A D C   5 8 ) . ` ; 
 
                                         } 
 
                                 }   e l s e   { 
 
                                         c o n s t   v a l J u r o s   =   u s a r P l a c e h o l d e r   ?   ' X X X '   :   ( $ ( ' v a l - j u r o s ' ) . v a l u e   | |   ' [ J U R O S ] ' ) ; 
 
                                         c o n s t   d t I n g r e s s o   =   u s a r P l a c e h o l d e r   ?   ' X X X '   :   ( $ ( ' d a t a - i n g r e s s o ' ) . v a l u e   | |   ' [ D A T A   I N G R E S S O ] ' ) ; 
 
                                         i n t r o T x t   + =   ` A t u a l i z % v e i s   p e l a   T R / I P C A - E ,   c o n f o r m e   s e n t e n % a .   J u r o s   l e g a i s   d e   $ { b o l d ( ' R $ '   +   v a l J u r o s ) }   a   p a r t i r   d e   $ { b o l d ( d t I n g r e s s o ) } . ` ; 
 
                                 } 
 
 
 
                                 i f   ( r e c l a m a d a L a b e l )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > $ { r e c l a m a d a L a b e l } < / s t r o n g > < / p > ` ; 
 
                                 } 
 
                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { i n t r o T x t } < / p > ` ; 
 
 
 
                                 / /   2 ,%Q%  p a r % g r a f o :   F G T S   d e p o s i t a d o   ( c o m   v a l o r ) 
 
                                 i f   ( i s F g t s S e p   & &   f g t s J a D e p o s i t a d o )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < u > O   F G T S   d e v i d o ,   $ { b o l d ( v F g t s ) } ,   j %   f o i   d e p o s i t a d o ,   p o r t a n t o   d e d u z i d o . < / u > < / p > ` ; 
 
                                 } 
 
 
 
                                 i f   ( ! u s a r P l a c e h o l d e r   & &   $ ( ' c a l c - o r i g e m ' ) . v a l u e   = = =   ' p j e c a l c '   & &   ! $ ( ' c a l c - p j c ' ) . c h e c k e d )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C o n s i d e r a n d o   a   a u s % n c i a   d o   a r q u i v o   d e   o r i g e m ,   < u > d e v e r %   a   p a r t e   a p r e s e n t a r   n o v a m e n t e   a   p l a n i l h a   o r a   h o m o l o g a d a ,   a c o m p a n h a d a   o b r i g a t o r i a m e n t e   d o   r e s p e c t i v o   a r q u i v o   $ { b o l d ( ' . P J C ' ) }   n o   p r a z o   d e   0 5   d i a s < / u > . < / p > ` ; 
 
                                 } 
 
 
 
                                 i f   ( u s a r P l a c e h o l d e r )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > D e s d e   j % ,   f i c a m   a u t o r i z a d o s   o s   d e s c o n t o s   p r e v i d e n c i % r i o s   ( c o t a   d o   r e c l a m a n t e )   o r a   f i x a d o s   e m   $ { x x x ( ) } ,   p a r a   $ { x x x ( ) } . < / p > ` ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A   r e c l a m a d a ,   a i n d a ,   d e v e r %   p a g a r   o   v a l o r   d e   s u a   c o t a - p a r t e   n o   I N S S ,   a   s a b e r ,   $ { x x x ( ) } ,   p a r a   $ { x x x ( ) } . < / p > ` ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P a r a   a s   d e d u % % e s   f i s c a i s   d e   I m p o s t o   d e   R e n d a ,   f i x a d a s   e m   $ { x x x ( ) }   p a r a   $ { x x x ( ) } ,   o b s e r v e m - s e   a   S %Q%m u l a   3 6 8   d o   T S T   e   I N   R F B   1 5 0 0 / 2 0 1 4 . < / p > ` ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   p e l a   r e c l a m a d a ,   n o   i m p o r t e   d e   $ { x x x ( ) } ,   p a r a   $ { x x x ( ) } . < / p > ` ; 
 
                                         i f   ( $ ( ' c h k - h o n - r e u ' ) . c h e c k e d )   { 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > N % o   f o r a m   a r b i t r a d o s   h o n o r % r i o s   a o   a d v o g a d o   d o   r % u . < / p > ` ; 
 
                                         }   e l s e   { 
 
                                                 c o n s t   r d H o n R e u   =   d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " r a d - h o n - r e u " ] : c h e c k e d ' ) . v a l u e ; 
 
                                                 i f   ( r d H o n R e u   = = =   ' s u s p e n s i v a ' )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   p e l a   r e c l a m a n t e   s o b   c o n d i % % o   s u s p e n s i v a ,   d i a n t e   d a   g r a t u i d a d e   d e f e r i d a . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   e m   f a v o r   d a   r e c l a m a d a   n a   o r d e m   d e   $ { x x x ( ) } . < / p > ` ; 
 
                                                 } 
 
                                         } 
 
                                         r e t u r n ; 
 
                                 } 
 
 
 
                                 i f   ( i g n o r a r I n s s )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P e l a   n a t u r e z a   d o   c r % d i t o ,   n % o   h %   c o n t r i b u i % % e s   p r e v i d e n c i % r i a s   d e v i d a s . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   v a l I n s s R e c S t r   =   $ ( ' v a l - i n s s - r e c ' ) . v a l u e   | |   ' 0 ' ; 
 
                                         c o n s t   v a l I n s s T o t a l S t r   =   $ ( ' v a l - i n s s - t o t a l ' ) . v a l u e   | |   ' 0 ' ; 
 
                                         c o n s t   v a l I n s s R e c   =   p a r s e M o n e y ( v a l I n s s R e c S t r ) ; 
 
                                         c o n s t   v a l I n s s T o t a l   =   p a r s e M o n e y ( v a l I n s s T o t a l S t r ) ; 
 
                                         l e t   v a l I n s s R e c l a m a d a S t r   =   v a l I n s s T o t a l S t r ; 
 
                                         i f   ( $ ( ' c a l c - o r i g e m ' ) . v a l u e   = = =   ' p j e c a l c ' )   { 
 
                                                 c o n s t   r e c R e s u l t   =   v a l I n s s T o t a l   -   v a l I n s s R e c ; 
 
                                                 v a l I n s s R e c l a m a d a S t r   =   f o r m a t M o n e y ( r e c R e s u l t ) ; 
 
                                         } 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A   r e c l a m a d a   d e v e r %   p a g a r   o   v a l o r   d e   s u a   c o t a - p a r t e   n o   I N S S ,   a   s a b e r ,   $ { b o l d ( v a l I n s s R e c l a m a d a S t r ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } . < / p > ` ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > D e s d e   j % ,   f i c a m   a u t o r i z a d o s   o s   d e s c o n t o s   p r e v i d e n c i % r i o s   ( c o t a   d o   r e c l a m a n t e )   o r a   f i x a d o s   e m   $ { b o l d ( ' R $ '   +   v a l I n s s R e c S t r ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } . < / p > ` ; 
 
                                 } 
 
 
 
                                 i f   ( $ ( ' i r p f - t i p o ' ) . v a l u e   = = =   ' i s e n t o ' )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > N % o   h %   d e d u % % e s   f i s c a i s   c a b % v e i s . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   v B a s e   =   $ ( ' v a l - i r p f - b a s e ' ) . v a l u e   | |   ' [ V A L O R ] ' ; 
 
                                         i f   ( $ ( ' c a l c - o r i g e m ' ) . v a l u e   = = =   ' p j e c a l c ' )   { 
 
                                                 c o n s t   v M e s   =   $ ( ' v a l - i r p f - m e s e s ' ) . v a l u e   | |   ' [ X ] ' ; 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > F i c a m   a u t o r i z a d o s   o s   d e s c o n t o s   f i s c a i s ,   c a l c u l a d o s   s o b r e   a s   v e r b a s   t r i b u t % v e i s   ( $ { b o l d ( ' R $ '   +   v B a s e ) } ) ,   p e l o   p e r % o d o   d e   $ { b o l d ( v M e s   +   '   m e s e s ' ) } . < / p > ` ; 
 
                                         }   e l s e   { 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P a r a   a s   d e d u % % e s   f i s c a i s   d e   I m p o s t o   d e   R e n d a ,   f i x a d a s   e m   $ { b o l d ( ' R $ '   +   v B a s e ) }   p a r a   $ { b o l d ( v a l D a t a ) } ,   o b s e r v e m - s e   a   S %Q%m u l a   3 6 8   d o   T S T   e   I N   R F B   1 5 0 0 / 2 0 1 4 . < / p > ` ; 
 
                                         } 
 
                                 } 
 
 
 
                                 i f   ( ! $ ( ' i g n o r a r - h o n - a u t o r ' ) . c h e c k e d )   { 
 
                                         c o n s t   v H o n A   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - h o n - a u t o r ' ) . v a l u e   | |   ' [ V A L O R ] ' ) ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   p e l a   r e c l a m a d a ,   n o   i m p o r t e   d e   $ { b o l d ( v H o n A ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } . < / p > ` ; 
 
                                 } 
 
 
 
                                 i f   ( $ ( ' c h k - h o n - r e u ' ) . c h e c k e d )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > N % o   f o r a m   a r b i t r a d o s   h o n o r % r i o s   a o   a d v o g a d o   d o   r % u . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   t i p o H o n R e u   =   d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " r a d - h o n - r e u - t i p o " ] : c h e c k e d ' ) . v a l u e ; 
 
                                         c o n s t   t e m S u s p e n s i v a   =   $ ( ' c h k - h o n - r e u - s u s p e n s i v a ' ) . c h e c k e d ; 
 
                                       
 
                                         i f   ( t i p o H o n R e u   = = =   ' p e r c e n t u a l ' )   { 
 
                                                 c o n s t   p   =   $ ( ' v a l - h o n - r e u - p e r c ' ) . v a l u e ; 
 
                                                 i f   ( t e m S u s p e n s i v a )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   p e l a   r e c l a m a n t e   s o b   c o n d i % % o   s u s p e n s i v a ,   n a   o r d e m   d e   $ { b o l d ( p ) } ,   d i a n t e   d a   g r a t u i d a d e   d e f e r i d a . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   e m   f a v o r   d a   r e c l a m a d a   n a   o r d e m   d e   $ { b o l d ( p ) } ,   a   s e r e m   d e s c o n t a d o s   d o   c r % d i t o   d o   a u t o r . < / p > ` ; 
 
                                                 } 
 
                                         }   e l s e   { 
 
                                                 c o n s t   v H o n R   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - h o n - r e u ' ) . v a l u e   | |   ' [ V A L O R ] ' ) ; 
 
                                                 i f   ( t e m S u s p e n s i v a )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   p e l a   r e c l a m a n t e   s o b   c o n d i % % o   s u s p e n s i v a ,   n o   i m p o r t e   d e   $ { b o l d ( v H o n R ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } ,   d i a n t e   d a   g r a t u i d a d e   d e f e r i d a . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   e m   f a v o r   d a   r e c l a m a d a ,   n o   i m p o r t e   d e   $ { b o l d ( v H o n R ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } ,   a   s e r e m   d e s c o n t a d o s   d o   c r % d i t o   d o   a u t o r . < / p > ` ; 
 
                                                 } 
 
                                         } 
 
                                 } 
 
                         } ; 
 
 
 
                         / /   F u n % % o   u n i f i c a d a   p a r a   l i b e r a % % o   d e t a l h a d a   ( d e p %%s i t o   r e c u r s a l   o u   p a g a m e n t o   a n t e c i p a d o ) 
 
                         c o n s t   g e r a r L i b e r a c a o D e t a l h a d a   =   ( c o n t e x t o )   = >   { 
 
                                 c o n s t   {   p r e f i x o   =   ' ' ,   d e p o s i t o I n f o   =   ' '   }   =   c o n t e x t o ; 
 
 
 
                                 / /   L i n h a   i n i c i a l   c o m   r e f e r % n c i a   %   p l a n i l h a 
 
                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P a s s o   %   l i b e r a % % o   d e   v a l o r e s   c o n f o r m e   p l a n i l h a   # $ { b o l d ( i d P l a n i l h a ) } : < / p > ` ; 
 
 
 
                                 l e t   n u m L i b e r a c a o   =   1 ; 
 
 
 
                                 / /   1 )   C r % d i t o   d o   r e c l a m a n t e 
 
                                 i f   ( d e p o s i t o I n f o )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { n u m L i b e r a c a o } )   L i b e r e - s e   a o   r e c l a m a n t e   $ { d e p o s i t o I n f o } ,   n o   v a l o r   d e   $ { b o l d ( ' R $ '   +   v a l C r e d i t o ) } ,   e x p e d i n d o - s e   a l v a r %   e l e t r %$%n i c o . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { n u m L i b e r a c a o } )   L i b e r e - s e   a o   r e c l a m a n t e   s e u   c r % d i t o ,   n o   v a l o r   d e   $ { b o l d ( ' R $ '   +   v a l C r e d i t o ) } ,   e x p e d i n d o - s e   a l v a r %   e l e t r %$%n i c o . < / p > ` ; 
 
                                 } 
 
                                 n u m L i b e r a c a o + + ; 
 
 
 
                                 / /   2 )   I N S S   ( s e   n % o   i g n o r a d o ) 
 
                                 i f   ( ! i g n o r a r I n s s )   { 
 
                                         c o n s t   v a l I n s s R e c   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - i n s s - r e c ' ) . v a l u e   | |   ' 0 , 0 0 ' ) ; 
 
                                         c o n s t   v a l I n s s T o t a l   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - i n s s - t o t a l ' ) . v a l u e   | |   ' 0 , 0 0 ' ) ; 
 
 
 
                                         / /   C a l c u l a r   I N S S   p a t r o n a l 
 
                                         c o n s t   i s P j e C a l c   =   $ ( ' c a l c - p j c ' ) . c h e c k e d ; 
 
                                         l e t   i n s s E m p r e g a d o   =   v a l I n s s R e c ;   / /   p a r t e   e m p r e g a d o   -   s e m p r e   v a l o r   d o   r e c l a m a n t e 
 
                                         l e t   i n s s P a t r o n a l   =   v a l I n s s T o t a l ;   / /   p a r t e   p a t r o n a l / r e c l a m a d a 
 
 
 
                                         / /   S e   %   P J C :   p a t r o n a l   =   t o t a l   -   e m p r e g a d o 
 
                                         i f   ( i s P j e C a l c   & &   v a l I n s s T o t a l   & &   v a l I n s s R e c )   { 
 
                                                 c o n s t   t o t a l N u m   =   p a r s e M o n e y ( v a l I n s s T o t a l ) ; 
 
                                                 c o n s t   r e c N u m   =   p a r s e M o n e y ( v a l I n s s R e c ) ; 
 
                                                 c o n s t   p a t r o n a l N u m   =   t o t a l N u m   -   r e c N u m ; 
 
                                                 i n s s P a t r o n a l   =   f o r m a t M o n e y ( p a t r o n a l N u m ) ; 
 
                                         } 
 
                                         / /   S e   n % o   %   P J C :   u s a   d i r e t o   o   v a l I n s s T o t a l 
 
 
 
                                         c o n s t   t o t a l I n s s   =   v a l I n s s T o t a l ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { n u m L i b e r a c a o } )   P r o c e d a   a   S e c r e t a r i a   %   t r a n s f e r % n c i a   d e   v a l o r e s   a o   %%r g % o   c o m p e t e n t e ,   v i a   S i s c o n d j ,   s e n d o :   $ { b o l d ( ' R $   '   +   i n s s E m p r e g a d o ) }   r e f e r e n t e   % s   c o n t r i b u i % % e s   p r e v i d e n c i % r i a s   p a r t e   e m p r e g a d o   e   $ { b o l d ( ' R $   '   +   i n s s P a t r o n a l ) }   n o   q u e   c o n c e r n e m   % s   c o n t r i b u i % % e s   p a t r o n a i s   ( t o t a l   d e   $ { b o l d ( ' R $   '   +   t o t a l I n s s ) } ) . < / p > ` ; 
 
                                         n u m L i b e r a c a o + + ; 
 
                                 } 
 
 
 
                                 / /   3 )   H o n o r % r i o s   p e r i c i a i s   ( s e   h o u v e r ) 
 
                                 c o n s t   p e r i t o C o n t a b i l D e t e c t a d o   =   ( w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   | |   [ ] ) . f i n d ( ( n o m e )   = >   i s N o m e R o g e r i o ( n o m e ) ) ; 
 
                                 c o n s t   v a l o r P e r i t o C o n t a b i l   =   $ ( ' v a l - p e r i t o - c o n t a b i l - v a l o r ' ) ? . v a l u e   | |   ' ' ; 
 
 
 
                                 / /   P e r i t o   c o n t % b i l   ( R o g % r i o )   -   s e   h o u v e r 
 
                                 i f   ( p e r i t o C o n t a b i l D e t e c t a d o   & &   v a l o r P e r i t o C o n t a b i l )   { 
 
                                         c o n s t   v C o n t a b i l   =   n o r m a l i z e M o n e y I n p u t ( v a l o r P e r i t o C o n t a b i l ) ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { n u m L i b e r a c a o } )   L i b e r e - s e   a o   p e r i t o   $ { b o l d ( p e r i t o C o n t a b i l D e t e c t a d o ) }   s e u s   h o n o r % r i o s ,   n o   v a l o r   d e   $ { b o l d ( ' R $ '   +   v C o n t a b i l ) } . < / p > ` ; 
 
                                         n u m L i b e r a c a o + + ; 
 
                                 } 
 
 
 
                                 / /   P e r i t o s   d e   c o n h e c i m e n t o   -   s e   h o u v e r 
 
                                 c o n s t   p e r i t o s C o n h e c i m e n t o D e t e c t a d o s   =   w i n d o w . h c a l c P e r i t o s C o n h e c i m e n t o D e t e c t a d o s   | |   [ ] ; 
 
                                 c o n s t   n o m e s I n p u t C o n h e c i m e n t o   =   ( $ ( ' v a l - p e r i t o - n o m e ' ) . v a l u e   | |   ' ' ) 
 
                                         . s p l i t ( / \ | | , | ; | \ n / g ) 
 
                                         . m a p ( ( n )   = >   n . t r i m ( ) ) 
 
                                         . f i l t e r ( B o o l e a n ) ; 
 
                                 c o n s t   n o m e s C o n h e c i m e n t o   =   p e r i t o s C o n h e c i m e n t o D e t e c t a d o s . l e n g t h 
 
                                         ?   p e r i t o s C o n h e c i m e n t o D e t e c t a d o s 
 
                                         :   n o m e s I n p u t C o n h e c i m e n t o ; 
 
 
 
                                 c o n s t   v a l o r P e r i t o C o n h   =   $ ( ' v a l - p e r i t o - v a l o r ' ) ? . v a l u e   | |   ' ' ; 
 
                                 c o n s t   t i p o P a g P e r i c i a   =   $ ( ' p e r i t o - t i p o - p a g ' ) ? . v a l u e   | |   ' r e c l a m a d a ' ; 
 
 
 
                                 i f   ( $ ( ' c h k - p e r i t o - c o n h ' ) . c h e c k e d   & &   n o m e s C o n h e c i m e n t o . l e n g t h   >   0   & &   v a l o r P e r i t o C o n h )   { 
 
                                         n o m e s C o n h e c i m e n t o . f o r E a c h ( ( n o m e P e r i t o )   = >   { 
 
                                                 i f   ( t i p o P a g P e r i c i a   ! = =   ' t r t ' )   { 
 
                                                         c o n s t   v P   =   n o r m a l i z e M o n e y I n p u t ( v a l o r P e r i t o C o n h ) ; 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { n u m L i b e r a c a o } )   L i b e r e - s e   a o   p e r i t o   $ { b o l d ( n o m e P e r i t o ) }   s e u s   h o n o r % r i o s ,   n o   v a l o r   d e   $ { b o l d ( ' R $ '   +   v P ) } . < / p > ` ; 
 
                                                         n u m L i b e r a c a o + + ; 
 
                                                 } 
 
                                         } ) ; 
 
                                 } 
 
 
 
                                 / /   4 )   H o n o r % r i o s   d o   a d v o g a d o   d o   a u t o r   ( s e   n % o   i g n o r a d o ) 
 
                                 i f   ( ! $ ( ' i g n o r a r - h o n - a u t o r ' ) . c h e c k e d )   { 
 
                                         c o n s t   v H o n A   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - h o n - a u t o r ' ) . v a l u e   | |   ' [ V A L O R ] ' ) ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { n u m L i b e r a c a o } )   L i b e r e - s e   a o   p a t r o n o   d a   p a r t e   a u t o r a   s e u s   h o n o r % r i o s ,   n o   v a l o r   d e   $ { b o l d ( ' R $ '   +   v H o n A ) } . < / p > ` ; 
 
                                         n u m L i b e r a c a o + + ; 
 
                                 } 
 
 
 
                                 / /   R e t o r n a r   o   n %Q%m e r o   d a   p r %%x i m a   l i b e r a % % o   ( p a r a   d e v o l u % % o ) 
 
                                 r e t u r n   n u m L i b e r a c a o ; 
 
                         } ; 
 
 
 
                         c o n s t   a p p e n d D i s p o s i c o e s F i n a i s   =   ( )   = >   { 
 
                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > D i s p o s i % % e s   f i n a i s : < / s t r o n g > < / p > ` ; 
 
 
 
                                 / /   C O N T % B I L   P R I M E I R O   ( R o g % r i o ) 
 
                                 c o n s t   p e r i t o C o n t a b i l D e t e c t a d o   =   ( w i n d o w . h c a l c P e r i t o s D e t e c t a d o s   | |   [ ] ) . f i n d ( ( n o m e )   = >   i s N o m e R o g e r i o ( n o m e ) ) ; 
 
                                 c o n s t   v a l o r P e r i t o C o n t a b i l   =   $ ( ' v a l - p e r i t o - c o n t a b i l - v a l o r ' ) ? . v a l u e   | |   ' ' ; 
 
                                 i f   ( p e r i t o C o n t a b i l D e t e c t a d o   & &   v a l o r P e r i t o C o n t a b i l )   { 
 
                                         c o n s t   v C o n t a b i l   =   n o r m a l i z e M o n e y I n p u t ( v a l o r P e r i t o C o n t a b i l ) ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   c o n t % b e i s   e m   f a v o r   d e   $ { b o l d ( p e r i t o C o n t a b i l D e t e c t a d o ) } ,   o r a   a r b i t r a d o s   e m   $ { b o l d ( v C o n t a b i l ) } . < / p > ` ; 
 
                                 } 
 
 
 
                                 / /   C O N H E C I M E N T O   D E P O I S 
 
                                 c o n s t   p e r i t o s C o n h e c i m e n t o D e t e c t a d o s   =   w i n d o w . h c a l c P e r i t o s C o n h e c i m e n t o D e t e c t a d o s   | |   [ ] ; 
 
                                 c o n s t   n o m e s I n p u t C o n h e c i m e n t o   =   ( $ ( ' v a l - p e r i t o - n o m e ' ) . v a l u e   | |   ' ' ) 
 
                                         . s p l i t ( / \ | | , | ; | \ n / g ) 
 
                                         . m a p ( ( n )   = >   n . t r i m ( ) ) 
 
                                         . f i l t e r ( B o o l e a n ) ; 
 
                                 c o n s t   n o m e s C o n h e c i m e n t o   =   p e r i t o s C o n h e c i m e n t o D e t e c t a d o s . l e n g t h 
 
                                         ?   p e r i t o s C o n h e c i m e n t o D e t e c t a d o s 
 
                                         :   n o m e s I n p u t C o n h e c i m e n t o ; 
 
 
 
                                 i f   ( $ ( ' c h k - p e r i t o - c o n h ' ) . c h e c k e d   & &   n o m e s C o n h e c i m e n t o . l e n g t h   >   0 )   { 
 
                                         c o n s t   v P   =   $ ( ' v a l - p e r i t o - v a l o r ' ) . v a l u e   | |   ' [ V A L O R / I D ] ' ; 
 
                                         c o n s t   d t P   =   $ ( ' v a l - p e r i t o - d a t a ' ) . v a l u e   | |   $ ( ' v a l - d a t a ' ) . v a l u e   | |   ' [ D A T A ] ' ; 
 
                                         c o n s t   t i p o P a g P e r i c i a   =   $ ( ' p e r i t o - t i p o - p a g ' ) . v a l u e ; 
 
 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   p e r i c i a i s   d a   f a s e   d e   c o n h e c i m e n t o   a s s i m   e s t a b e l e c i d o s : < / p > ` ; 
 
 
 
                                         n o m e s C o n h e c i m e n t o . f o r E a c h ( ( n o m e P e r i t o )   = >   { 
 
                                                 i f   ( t i p o P a g P e r i c i a   = = =   ' t r t ' )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > -   E m   f a v o r   d e   $ { b o l d ( n o m e P e r i t o ) } ,   p a g o s   p e l o   T R T ,   c o n s i d e r a n d o   a   s u c u m b % n c i a   d o   a u t o r   n o   o b j e t o   d a   p e r % c i a   ( # $ { b o l d ( v P ) } ) . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > -   E m   f a v o r   d e   $ { b o l d ( n o m e P e r i t o ) } ,   p a g a m e n t o   d e   $ { b o l d ( ' R $ '   +   v P ) }   p e l a   r e c l a m a d a ,   p a r a   $ { b o l d ( d t P ) } . < / p > ` ; 
 
                                                 } 
 
                                         } ) ; 
 
                                 } 
 
 
 
                                 i f   ( $ ( ' c u s t a s - s t a t u s ' ) . v a l u e   = = =   ' p a g a s ' )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C u s t a s   p a g a s   e m   r a z % o   d e   r e c u r s o . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   v a l C   =   $ ( ' v a l - c u s t a s ' ) . v a l u e   | |   ' [ V A L O R ] ' ; 
 
                                         c o n s t   o r i g e m C u s t a s   =   $ ( ' c u s t a s - o r i g e m ' ) . v a l u e ; 
 
 
 
                                         i f   ( v a l C   & &   v a l C   ! = =   ' 0 , 0 0 '   & &   v a l C   ! = =   ' 0 ' )   { 
 
                                                 i f   ( o r i g e m C u s t a s   = = =   ' a c o r d a o ' )   { 
 
                                                         / /   C u s t a s   p o r   a c %%r d % o   ( i n c l u i   I D   d o   a c %%r d % o   n o   t e x t o ) 
 
                                                         c o n s t   a c o r d a o I d x   =   $ ( ' c u s t a s - a c o r d a o - s e l e c t ' ) . v a l u e ; 
 
                                                         c o n s t   a c o r d a o S e l   =   $ ( ' c u s t a s - a c o r d a o - s e l e c t ' ) . s e l e c t e d O p t i o n s [ 0 ] ; 
 
                                                         c o n s t   d a t a A c o r d a o   =   a c o r d a o S e l ? . d a t a s e t ? . d a t a   | |   ' [ D A T A   A C % R D % O ] ' ; 
 
                                                         c o n s t   i d A c o r d a o   =   a c o r d a o S e l ? . d a t a s e t ? . i d   | |   ' ' ; 
 
                                                         c o n s t   i d T e x t o   =   i d A c o r d a o   ?   `   # $ { b o l d ( i d A c o r d a o ) } `   :   ' ' ; 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C u s t a s   d e f i n i d a s   e m   a c %%r d % o $ { i d T e x t o } ,   p e l a   r e c l a m a d a ,   n o   v a l o r   d e   $ { b o l d ( ' R $ '   +   v a l C ) }   p a r a   $ { b o l d ( d a t a A c o r d a o ) } . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         / /   C u s t a s   p o r   s e n t e n % a   ( p a d r % o ) 
 
                                                         c o n s t   d a t a C u s t a s   =   $ ( ' c u s t a s - d a t a - o r i g e m ' ) . v a l u e   | |   v a l D a t a ; 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C u s t a s   d e   $ { b o l d ( ' R $ '   +   v a l C ) }   p e l a   r e c l a m a d a ,   p a r a   $ { b o l d ( d a t a C u s t a s ) } . < / p > ` ; 
 
                                                 } 
 
                                         } 
 
                                 } 
 
 
 
                                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                                 / /   D E P % S I T O S   R E C U R S A I S   ( m %Q%l t i p l o s ) 
 
                                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                                 i f   ( $ ( ' c h k - d e p o s i t o ' ) . c h e c k e d )   { 
 
                                         c o n s t   p a s s i v o D e t e c t a d o   =   ( w i n d o w . h c a l c P a r t e s D a t a ? . p a s s i v o   | |   [ ] ) . m a p ( ( p )   = >   p ? . n o m e ) . f i l t e r ( B o o l e a n ) ; 
 
                                         c o n s t   p r i m e i r a R e c l a m a d a   =   p a s s i v o D e t e c t a d o [ 0 ]   | |   ' ' ; 
 
                                         c o n s t   t i p o R e s p A t u a l   =   $ ( ' r e s p - t i p o ' ) ? . v a l u e   | |   ' u n i c a ' ; 
 
                                       
 
                                         / /   C o l e t a r   t o d o s   o s   d e p %%s i t o s   v % l i d o s   ( n % o   r e m o v i d o s ) 
 
                                         c o n s t   d e p o s i t o s V a l i d o s   =   w i n d o w . h c a l c S t a t e . d e p o s i t o s R e c u r s a i s 
 
                                                 . f i l t e r ( d   = >   ! d . r e m o v e d ) 
 
                                                 . m a p ( d   = >   { 
 
                                                         c o n s t   i d x   =   d . i d x ; 
 
                                                         c o n s t   t D e p   =   $ ( ` d e p - t i p o - $ { i d x } ` ) ? . v a l u e   | |   ' b b ' ; 
 
                                                         c o n s t   d N o m e   =   $ ( ` d e p - d e p o s i t a n t e - $ { i d x } ` ) ? . v a l u e   | |   ' [ R E C L A M A D A ] ' ; 
 
                                                         c o n s t   d I d   =   $ ( ` d e p - i d - $ { i d x } ` ) ? . v a l u e   | |   ' [ I D ] ' ; 
 
                                                         l e t   i s P r i n   =   $ ( ` d e p - p r i n c i p a l - $ { i d x } ` ) ? . c h e c k e d   ? ?   t r u e ; 
 
                                                         c o n s t   l i b e r a c a o   =   d o c u m e n t . q u e r y S e l e c t o r ( ` i n p u t [ n a m e = " r a d - d e p - l i b - $ { i d x } " ] : c h e c k e d ` ) ? . v a l u e   | |   ' r e c l a m a n t e ' ; 
 
                                                       
 
                                                         c o n s t   i s D e p o s i t o J u d i c i a l   =   t D e p   ! = =   ' g a r a n t i a ' ; 
 
                                                         l e t   c r i t e r i o L i b e r a c a o D e p o s i t o   =   ' m a n u a l ' ; 
 
                                                         l e t   d e p o s i t a n t e R e s o l v i d a   =   d N o m e ; 
 
                                                       
 
                                                         / /   A u t o - r e s o l v e r   d e p o s i t a n t e   b a s e a d o   e m   p a r t e s   d e t e c t a d a s 
 
                                                         i f   ( p a s s i v o D e t e c t a d o . l e n g t h   = = =   1 )   { 
 
                                                                 d e p o s i t a n t e R e s o l v i d a   =   p a s s i v o D e t e c t a d o [ 0 ] ; 
 
                                                                 i s P r i n   =   t r u e ; 
 
                                                                 c r i t e r i o L i b e r a c a o D e p o s i t o   =   ' r e c l a m a d a - u n i c a ' ; 
 
                                                         }   e l s e   i f   ( t i p o R e s p A t u a l   = = =   ' s u b s i d i a r i a s '   & &   p r i m e i r a R e c l a m a d a   & &   i s P r i n )   { 
 
                                                                 d e p o s i t a n t e R e s o l v i d a   =   p r i m e i r a R e c l a m a d a ; 
 
                                                                 c r i t e r i o L i b e r a c a o D e p o s i t o   =   ' s u b s i d i a r i a - p r i n c i p a l ' ; 
 
                                                         }   e l s e   i f   ( t i p o R e s p A t u a l   = = =   ' s o l i d a r i a s ' )   { 
 
                                                                 / /   S o l i d % r i a s :   q u a l q u e r   d e p %%s i t o   p o d e   s e r   l i b e r a d o 
 
                                                                 d e p o s i t a n t e R e s o l v i d a   =   d e p o s i t a n t e R e s o l v i d a   | |   p r i m e i r a R e c l a m a d a   | |   ' [ R E C L A M A D A ] ' ; 
 
                                                                 i s P r i n   =   t r u e ;   / /   F o r % a r   c o m o   p r i n c i p a l   ( t o d a s   s % o   p r i n c i p a i s   e m   s o l i d % r i a ) 
 
                                                                 c r i t e r i o L i b e r a c a o D e p o s i t o   =   ' s o l i d a r i a ' ; 
 
                                                         } 
 
                                                       
 
                                                         c o n s t   d e v e L i b e r a r D e p o s i t o   =   i s D e p o s i t o J u d i c i a l   & &   ( 
 
                                                                 c r i t e r i o L i b e r a c a o D e p o s i t o   = = =   ' r e c l a m a d a - u n i c a '   | | 
 
                                                                 c r i t e r i o L i b e r a c a o D e p o s i t o   = = =   ' s u b s i d i a r i a - p r i n c i p a l '   | | 
 
                                                                 c r i t e r i o L i b e r a c a o D e p o s i t o   = = =   ' s o l i d a r i a '   | | 
 
                                                                 ( c r i t e r i o L i b e r a c a o D e p o s i t o   = = =   ' m a n u a l '   & &   i s P r i n ) 
 
                                                         ) ; 
 
                                                       
 
                                                         c o n s t   n a t u r e z a D e v e d o r a   =   c r i t e r i o L i b e r a c a o D e p o s i t o   = = =   ' s o l i d a r i a ' 
 
                                                                 ?   ' s o l i d % r i a ' 
 
                                                                 :   ( i s P r i n   ?   ' p r i n c i p a l '   :   ' s u b s i d i % r i a ' ) ; 
 
                                                       
 
                                                         c o n s t   b a n c o T x t   =   t D e p   = = =   ' b b '   ?   ' B a n c o   d o   B r a s i l '   :   ( t D e p   = = =   ' s i f '   ?   ' C a i x a   E c o n %$%m i c a   F e d e r a l   ( S I F ) '   :   ' s e g u r o   g a r a n t i a   r e g u l a r ' ) ; 
 
                                                       
 
                                                         r e t u r n   { 
 
                                                                 i d x ,   t D e p ,   d e p o s i t a n t e R e s o l v i d a ,   d I d ,   i s P r i n ,   l i b e r a c a o , 
 
                                                                 i s D e p o s i t o J u d i c i a l ,   n a t u r e z a D e v e d o r a ,   b a n c o T x t ,   d e v e L i b e r a r D e p o s i t o 
 
                                                         } ; 
 
                                                 } ) ; 
 
                                       
 
                                         i f   ( d e p o s i t o s V a l i d o s . l e n g t h   = = =   0 )   { 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H %   d e p %%s i t o   r e c u r s a l .   ( C o n f i g u r e   o s   d a d o s ) < / p > ` ; 
 
                                         }   e l s e   { 
 
                                                 / /   A g r u p a r   d e p %%s i t o s   p o r   d e p o s i t a n t e   +   t i p o 
 
                                                 c o n s t   g r u p o s   =   { } ; 
 
                                                 d e p o s i t o s V a l i d o s . f o r E a c h ( d e p   = >   { 
 
                                                         c o n s t   c h a v e   =   ` $ { d e p . d e p o s i t a n t e R e s o l v i d a } | $ { d e p . n a t u r e z a D e v e d o r a } | $ { d e p . b a n c o T x t } ` ; 
 
                                                         i f   ( ! g r u p o s [ c h a v e ] )   { 
 
                                                                 g r u p o s [ c h a v e ]   =   { 
 
                                                                         d e p o s i t a n t e :   d e p . d e p o s i t a n t e R e s o l v i d a , 
 
                                                                         n a t u r e z a :   d e p . n a t u r e z a D e v e d o r a , 
 
                                                                         b a n c o :   d e p . b a n c o T x t , 
 
                                                                         d e p o s i t o s :   [ ] , 
 
                                                                         t o d o s G a r a n t i a :   t r u e , 
 
                                                                         t o d o s L i b e r a c a o D i r e t a :   t r u e 
 
                                                                 } ; 
 
                                                         } 
 
                                                         g r u p o s [ c h a v e ] . d e p o s i t o s . p u s h ( d e p ) ; 
 
                                                         i f   ( d e p . i s D e p o s i t o J u d i c i a l )   g r u p o s [ c h a v e ] . t o d o s G a r a n t i a   =   f a l s e ; 
 
                                                         i f   ( d e p . l i b e r a c a o   ! = =   ' r e c l a m a n t e ' )   g r u p o s [ c h a v e ] . t o d o s L i b e r a c a o D i r e t a   =   f a l s e ; 
 
                                                 } ) ; 
 
                                               
 
                                                 c o n s t   f o r m a t a r L i s t a   =   ( i t e n s )   = >   { 
 
                                                         i f   ( ! i t e n s   | |   i t e n s . l e n g t h   = = =   0 )   {   r e t u r n   ' ' ;   } 
 
                                                         i f   ( i t e n s . l e n g t h   = = =   1 )   {   r e t u r n   i t e n s [ 0 ] ;   } 
 
                                                         i f   ( i t e n s . l e n g t h   = = =   2 )   {   r e t u r n   ` $ { i t e n s [ 0 ] }   e   $ { i t e n s [ 1 ] } ` ;   } 
 
                                                         r e t u r n   ` $ { i t e n s . s l i c e ( 0 ,   - 1 ) . j o i n ( ' ,   ' ) }   e   $ { i t e n s [ i t e n s . l e n g t h   -   1 ] } ` ; 
 
                                                 } ; 
 
                                               
 
                                                 / /   G e r a r   t e x t o   p a r a   c a d a   g r u p o 
 
                                                 O b j e c t . v a l u e s ( g r u p o s ) . f o r E a c h ( g r u p o   = >   { 
 
                                                         c o n s t   i d s   =   g r u p o . d e p o s i t o s . m a p ( d   = >   ` $ { b o l d ( d . d I d ) } ` ) ; 
 
                                                         c o n s t   i d s T e x t o   =   i d s . l e n g t h   >   1   ?   ` ( I d s   $ { f o r m a t a r L i s t a ( i d s ) } ) `   :   ` ( I d   $ { i d s [ 0 ] } ) ` ; 
 
                                                       
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H %   d e p %%s i t o $ { g r u p o . d e p o s i t o s . l e n g t h   >   1   ?   ' s '   :   ' ' }   r e c u r s a l $ { g r u p o . d e p o s i t o s . l e n g t h   >   1   ?   ' i s '   :   ' ' }   d a   d e v e d o r a   $ { g r u p o . n a t u r e z a }   ( $ { g r u p o . d e p o s i t a n t e }   $ { i d s T e x t o } )   v i a   $ { g r u p o . b a n c o } . < / p > ` ; 
 
                                                       
 
                                                         i f   ( g r u p o . t o d o s G a r a n t i a )   { 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > T r a t a n d o - s e   d e   s e g u r o   g a r a n t i a ,   n % o   h %   l i b e r a % % o   i m e d i a t a   d e   v a l o r e s   n e s t a   o p o r t u n i d a d e . < / p > ` ; 
 
                                                         }   e l s e   { 
 
                                                                 / /   P r o c e s s a r   l i b e r a % % e s 
 
                                                                 c o n s t   d e p s L i b e r a v e i s   =   g r u p o . d e p o s i t o s . f i l t e r ( d   = >   d . d e v e L i b e r a r D e p o s i t o   & &   d . i s D e p o s i t o J u d i c i a l ) ; 
 
                                                               
 
                                                                 i f   ( d e p s L i b e r a v e i s . l e n g t h   >   0 )   { 
 
                                                                         c o n s t   d e p s D i r e t o s   =   d e p s L i b e r a v e i s . f i l t e r ( d   = >   d . l i b e r a c a o   = = =   ' r e c l a m a n t e ' ) ; 
 
                                                                         c o n s t   d e p s D e t a l h a d o s   =   d e p s L i b e r a v e i s . f i l t e r ( d   = >   d . l i b e r a c a o   = = =   ' d e t a l h a d a ' ) ; 
 
                                                                       
 
                                                                         i f   ( d e p s D i r e t o s . l e n g t h   >   0 )   { 
 
                                                                                 h o u v e D e p o s i t o D i r e t o   =   t r u e ; 
 
                                                                                 c o n s t   t x t P l u r a l   =   d e p s D i r e t o s . l e n g t h   >   1   ?   ' o s   d e p %%s i t o s   r e c u r s a i s '   :   ' o   d e p %%s i t o   r e c u r s a l ' ; 
 
                                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > L i b e r e - s e   $ { t x t P l u r a l }   e m   f a v o r   d o   r e c l a m a n t e .   A p %%s ,   a p u r e - s e   o   r e m a n e s c e n t e   d e v i d o . < / p > ` ; 
 
                                                                         } 
 
                                                                       
 
                                                                         i f   ( d e p s D e t a l h a d o s . l e n g t h   >   0 )   { 
 
                                                                                 c o n s t   i d s D e t a l h a d o s   =   d e p s D e t a l h a d o s . m a p ( d   = >   ` $ { g r u p o . d e p o s i t a n t e }   # $ { b o l d ( d . d I d ) } ` ) ; 
 
                                                                                 c o n s t   l i s t a D e p s   =   f o r m a t a r L i s t a ( i d s D e t a l h a d o s ) ; 
 
                                                                               
 
                                                                                 h o u v e L i b e c a o D e t a l h a d a   =   t r u e ; 
 
                                                                                 g e r a r L i b e r a c a o D e t a l h a d a ( { 
 
                                                                                         d e p o s i t o I n f o :   ` o $ { d e p s D e t a l h a d o s . l e n g t h   >   1   ?   ' s '   :   ' ' }   d e p %%s i t o $ { d e p s D e t a l h a d o s . l e n g t h   >   1   ?   ' s '   :   ' ' }   r e c u r s a l $ { d e p s D e t a l h a d o s . l e n g t h   >   1   ?   ' i s '   :   ' ' }   ( $ { l i s t a D e p s }   v i a   $ { g r u p o . b a n c o } ) ` 
 
                                                                                 } ) ; 
 
                                                                         } 
 
                                                                 }   e l s e   { 
 
                                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P o r   o r a ,   n % o   h %   l i b e r a % % o   a u t o m % t i c a   d o $ { g r u p o . d e p o s i t o s . l e n g t h   >   1   ?   ' s '   :   ' ' }   d e p %%s i t o $ { g r u p o . d e p o s i t o s . l e n g t h   >   1   ?   ' s '   :   ' ' }   r e c u r s a l $ { g r u p o . d e p o s i t o s . l e n g t h   >   1   ?   ' i s '   :   ' ' }   i n f o r m a d o $ { g r u p o . d e p o s i t o s . l e n g t h   >   1   ?   ' s '   :   ' ' } . < / p > ` ; 
 
                                                                 } 
 
                                                         } 
 
                                                 } ) ; 
 
                                         } 
 
                                 } 
 
 
 
                                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                                 / /   P A G A M E N T O S   A N T E C I P A D O S   ( m %Q%l t i p l o s ) 
 
                                 / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                                 c o n s t   i s P a g a m e n t o A n t e c i p a d o   =   $ ( ' c h k - p a g - a n t e c i p a d o ' ) . c h e c k e d ; 
 
                                 i f   ( i s P a g a m e n t o A n t e c i p a d o )   { 
 
                                         c o n s t   p a g a m e n t o s V a l i d o s   =   w i n d o w . h c a l c S t a t e . p a g a m e n t o s A n t e c i p a d o s 
 
                                                 . f i l t e r ( p   = >   ! p . r e m o v e d ) 
 
                                                 . m a p ( p   = >   { 
 
                                                         c o n s t   i d x   =   p . i d x ; 
 
                                                         r e t u r n   { 
 
                                                                 i d x , 
 
                                                                 i d :   $ ( ` p a g - i d - $ { i d x } ` ) ? . v a l u e   | |   ' [ I D ] ' , 
 
                                                                 t i p o L i b :   d o c u m e n t . q u e r y S e l e c t o r ( ` i n p u t [ n a m e = " l i b - t i p o - $ { i d x } " ] : c h e c k e d ` ) ? . v a l u e   | |   ' n e n h u m ' , 
 
                                                                 r e m V a l o r :   $ ( ` l i b - r e m - v a l o r - $ { i d x } ` ) ? . v a l u e   | |   ' ' , 
 
                                                                 r e m T i t u l o :   $ ( ` l i b - r e m - t i t u l o - $ { i d x } ` ) ? . v a l u e   | |   ' ' , 
 
                                                                 d e v V a l o r :   $ ( ` l i b - d e v - v a l o r - $ { i d x } ` ) ? . v a l u e   | |   ' ' 
 
                                                         } ; 
 
                                                 } ) ; 
 
                                       
 
                                         i f   ( p a g a m e n t o s V a l i d o s . l e n g t h   = = =   0 )   { 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > R e a l i z a d o   d e p %%s i t o   p e l a   r e c l a m a d a .   ( C o n f i g u r e   o s   d a d o s ) < / p > ` ; 
 
                                         }   e l s e   { 
 
                                                 p a g a m e n t o s V a l i d o s . f o r E a c h ( p a g   = >   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > R e a l i z a d o   d e p %%s i t o   p e l a   r e c l a m a d a ,   # $ { b o l d ( p a g . i d ) } . < / p > ` ; 
 
                                                       
 
                                                         h o u v e L i b e c a o D e t a l h a d a   =   t r u e ; 
 
                                                         l e t   p r o x i m o N u m   =   g e r a r L i b e r a c a o D e t a l h a d a ( { } ) ; 
 
                                                       
 
                                                         i f   ( p a g . t i p o L i b   = = =   ' d e v o l u c a o ' )   { 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { p r o x i m o N u m } )   D e v o l v a - s e   %   r e c l a m a d a   o   v a l o r   p a g o   a   m a i o r ,   n o   m o n t a n t e   d e   $ { b o l d ( ' R $   '   +   ( p a g . d e v V a l o r   | |   ' [ V A L O R ] ' ) ) } ,   e x p e d i n d o - s e   o   c o m p e t e n t e   a l v a r % . < / p > ` ; 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C o n c e d e - s e   0 5   d i a s   p a r a   m a n i f e s t a % % o   d a s   p a r t e s . < / p > ` ; 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A p %%s ,   t o r n e m   c o n c l u s o s   p a r a   e x t i n % % o   d a   e x e c u % % o . < / p > ` ; 
 
                                                         }   e l s e   i f   ( p a g . t i p o L i b   = = =   ' r e m a n e s c e n t e ' )   { 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > S e m   p r e j u % z o ,   f i c a   a   r e c l a m a d a   i n t i m a d a   a   p a g a r   o   v a l o r   r e m a n e s c e n t e   d e   $ { b o l d ( ' R $   '   +   ( p a g . r e m V a l o r   | |   ' [ V A L O R ] ' ) ) }   d e v i d o s   a   t % t u l o   d e   $ { b o l d ( p a g . r e m T i t u l o   | |   ' [ T % T U L O ] ' ) } ,   e m   1 5   d i a s ,   s o b   p e n a   d e   e x e c u % % o . < / p > ` ; 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C i e n t e s   a s   p a r t e s . < / p > ` ; 
 
                                                         }   e l s e   { 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C o n c e d e - s e   0 5   d i a s   p a r a   m a n i f e s t a % % e s .   S i l e n t e s ,   c u m p r a - s e   e ,   a p %%s ,   t o r n e m   c o n c l u s o s   p a r a   e x t i n % % o   d a   e x e c u % % o . < / p > ` ; 
 
                                                         } 
 
                                                 } ) ; 
 
                                         } 
 
                                 } 
 
                               
 
                                 / /   I N T I M A % % E S   ( a p e n a s   s e   N % O   h o u v e r   p a g a m e n t o   a n t e c i p a d o ) 
 
                                 i f   ( ! i s P a g a m e n t o A n t e c i p a d o )   { 
 
                                         c o n s t   f o r m a t a r L i s t a P a r t e s   =   ( n o m e s )   = >   { 
 
                                                 i f   ( ! n o m e s   | |   n o m e s . l e n g t h   = = =   0 )   {   r e t u r n   ' ' ;   } 
 
                                                 i f   ( n o m e s . l e n g t h   = = =   1 )   {   r e t u r n   n o m e s [ 0 ] ;   } 
 
                                                 i f   ( n o m e s . l e n g t h   = = =   2 )   {   r e t u r n   ` $ { n o m e s [ 0 ] }   e   $ { n o m e s [ 1 ] } ` ;   } 
 
                                                 r e t u r n   ` $ { n o m e s . s l i c e ( 0 ,   - 1 ) . j o i n ( ' ,   ' ) }   e   $ { n o m e s [ n o m e s . l e n g t h   -   1 ] } ` ; 
 
                                         } ; 
 
 
 
                                         c o n s t   e l s O p c o e s   =   d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . s e l - m o d o - i n t i m a c a o ' ) ; 
 
                                         c o n s t   g r p D i a r i o   =   [ ] ; 
 
                                         c o n s t   g r p M a n d a d o   =   [ ] ; 
 
                                         c o n s t   g r p E d i t a l   =   [ ] ; 
 
 
 
                                         / /   V e r i f i c a r   s e   %   r e s p o n s a b i l i d a d e   s u b s i d i % r i a 
 
                                         c o n s t   i s S u b s i d i a r i a   =   $ ( ' r e s p - t i p o ' ) ? . v a l u e   = = =   ' s u b s i d i a r i a s ' ; 
 
                                       
 
                                         / /   O b t e r   l i s t a   d e   p r i n c i p a i s   ( m a r c a d a s   c o m o   p r i n c i p a l ) 
 
                                         c o n s t   p r i n c i p a i s S e t   =   n e w   S e t ( ) ; 
 
                                         i f   ( i s S u b s i d i a r i a )   { 
 
                                                 d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . c h k - p a r t e - p r i n c i p a l : c h e c k e d ' ) . f o r E a c h ( c h k   = >   { 
 
                                                         p r i n c i p a i s S e t . a d d ( c h k . g e t A t t r i b u t e ( ' d a t a - n o m e ' ) ) ; 
 
                                                 } ) ; 
 
                                         } 
 
 
 
                                         i f   ( e l s O p c o e s . l e n g t h   >   0 )   { 
 
                                                 e l s O p c o e s . f o r E a c h ( ( s e l )   = >   { 
 
                                                         c o n s t   n o m e   =   s e l . g e t A t t r i b u t e ( ' d a t a - n o m e ' ) ; 
 
                                                         c o n s t   v   =   s e l . v a l u e ; 
 
                                                       
 
                                                         / /   F I L T R O :   S e   s u b s i d i % r i a ,   i n t i m a   a p e n a s   p r i n c i p a i s 
 
                                                         i f   ( i s S u b s i d i a r i a   & &   ! p r i n c i p a i s S e t . h a s ( n o m e ) )   { 
 
                                                                 r e t u r n ;   / /   P u l a   s u b s i d i % r i a s 
 
                                                         } 
 
                                                       
 
                                                         i f   ( v   = = =   ' d i a r i o ' )   g r p D i a r i o . p u s h ( n o m e ) ; 
 
                                                         e l s e   i f   ( v   = = =   ' m a n d a d o ' )   g r p M a n d a d o . p u s h ( n o m e ) ; 
 
                                                         e l s e   i f   ( v   = = =   ' e d i t a l ' )   g r p E d i t a l . p u s h ( n o m e ) ; 
 
                                                 } ) ; 
 
                                         }   e l s e   { 
 
                                                 c o n s t   v a l M a n u a l   =   $ ( ' s e l - i n t i m a c a o - m a n u a l ' ) ? . v a l u e   | |   ' d i a r i o ' ; 
 
                                                 c o n s t   n o m e M a n u a l   =   $ ( ' i n t - n o m e - p a r t e - m a n u a l ' ) ? . v a l u e   | |   ' [ R E C L A M A D A ] ' ; 
 
                                                 i f   ( v a l M a n u a l   = = =   ' d i a r i o ' )   g r p D i a r i o . p u s h ( n o m e M a n u a l ) ; 
 
                                                 e l s e   i f   ( v a l M a n u a l   = = =   ' m a n d a d o ' )   g r p M a n d a d o . p u s h ( n o m e M a n u a l ) ; 
 
                                                 e l s e   i f   ( v a l M a n u a l   = = =   ' e d i t a l ' )   g r p E d i t a l . p u s h ( n o m e M a n u a l ) ; 
 
                                         } 
 
 
 
                                         i f   ( g r p D i a r i o . l e n g t h   >   0 )   { 
 
                                                 c o n s t   a l v o C o m A d v   =   f o r m a t a r L i s t a P a r t e s ( g r p D i a r i o ) ; 
 
                                                 c o n s t   v e r b o C o m A d v   =   g r p D i a r i o . l e n g t h   >   1   ?   ' I n t i m e m - s e   a s   r e c l a m a d a s '   :   ' I n t i m e - s e   a   r e c l a m a d a ' ; 
 
                                                 c o n s t   p a t r o n o T x t   =   g r p D i a r i o . l e n g t h   >   1   ?   ' s e u s   p a t r o n o s '   :   ' s e u   p a t r o n o ' ; 
 
                                                 c o n s t   t i p o V a l o r e s   =   h o u v e D e p o s i t o D i r e t o   ?   ' v a l o r e s   r e m a n e s c e n t e s '   :   ' v a l o r e s   a c i m a   i n d i c a d o s ' ; 
 
 
 
                                                 i f   ( h o u v e D e p o s i t o D i r e t o )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A p %%s   r e f e r i d a   a t u a l i z a % % o ,   $ { v e r b o C o m A d v }   $ { b o l d ( a l v o C o m A d v ) } ,   n a   p e s s o a   d e   $ { p a t r o n o T x t } ,   p a r a   q u e   p a g u e ( m )   o s   $ { t i p o V a l o r e s }   e m   1 5   d i a s ,   n a   f o r m a   d o   a r t .   5 2 3 ,   c a p u t ,   d o   C P C ,   s o b   p e n a   d e   p e n h o r a . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { v e r b o C o m A d v }   $ { b o l d ( a l v o C o m A d v ) } ,   n a   p e s s o a   d e   $ { p a t r o n o T x t } ,   p a r a   q u e   p a g u e ( m )   o s   $ { t i p o V a l o r e s }   e m   1 5   d i a s ,   n a   f o r m a   d o   a r t .   5 2 3 ,   c a p u t ,   d o   C P C ,   s o b   p e n a   d e   p e n h o r a . < / p > ` ; 
 
                                                 } 
 
                                         } 
 
 
 
                                         i f   ( g r p M a n d a d o . l e n g t h   >   0 )   { 
 
                                                 c o n s t   a l v o M a n d   =   f o r m a t a r L i s t a P a r t e s ( g r p M a n d a d o ) ; 
 
                                                 c o n s t   v e r b o M a n d   =   g r p M a n d a d o . l e n g t h   >   1   ?   ' I n t i m e m - s e   a s   r e c l a m a d a s '   :   ' I n t i m e - s e   a   r e c l a m a d a ' ; 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { v e r b o M a n d }   $ { b o l d ( a l v o M a n d ) }   p a r a   p a g a m e n t o   d o s   v a l o r e s   a c i m a   e m   4 8   ( q u a r e n t a   e   o i t o )   h o r a s ,   s o b   p e n a   d e   p e n h o r a ,   e x p e d i n d o - s e   o   c o m p e t e n t e   $ { b o l d ( " m a n d a d o " ) } . < / p > ` ; 
 
                                         } 
 
 
 
                                         i f   ( g r p E d i t a l . l e n g t h   >   0 )   { 
 
                                                 c o n s t   a l v o E d i t   =   f o r m a t a r L i s t a P a r t e s ( g r p E d i t a l ) ; 
 
                                                 c o n s t   v e r b o E d i t   =   g r p E d i t a l . l e n g t h   >   1   ?   ' C i t e m - s e   a s   r e c l a m a d a s '   :   ' C i t e - s e   a   r e c l a m a d a ' ; 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { v e r b o E d i t }   $ { b o l d ( a l v o E d i t ) } ,   p o r   $ { b o l d ( " e d i t a l " ) } ,   p a r a   p a g a m e n t o   d o s   v a l o r e s   a c i m a   e m   4 8   ( q u a r e n t a   e   o i t o )   h o r a s ,   s o b   p e n a   d e   p e n h o r a . < / p > ` ; 
 
                                         } 
 
                                 } 
 
                         } ; 
 
 
 
                         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                         / /   G E R A % % O   D E   T E X T O   -   R E S P O N S A B I L I D A D E S 
 
                         / /   = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
 
                         f u n c t i o n   g e r a r T e x t o R e s p o n s a b i l i d a d e s ( )   { 
 
                                 c o n s t   f o r m a t a r L i s t a   =   ( n o m e s )   = >   { 
 
                                         i f   ( n o m e s . l e n g t h   = = =   0 )   r e t u r n   ' ' ; 
 
                                         i f   ( n o m e s . l e n g t h   = = =   1 )   r e t u r n   b o l d ( n o m e s [ 0 ] ) ; 
 
                                         i f   ( n o m e s . l e n g t h   = = =   2 )   r e t u r n   ` $ { b o l d ( n o m e s [ 0 ] ) }   e   $ { b o l d ( n o m e s [ 1 ] ) } ` ; 
 
                                         c o n s t   u l t i m o s   =   n o m e s . s l i c e ( - 2 ) ; 
 
                                         c o n s t   a n t e r i o r e s   =   n o m e s . s l i c e ( 0 ,   - 2 ) ; 
 
                                         r e t u r n   ` $ { a n t e r i o r e s . m a p ( n   = >   b o l d ( n ) ) . j o i n ( ' ,   ' ) } ,   $ { b o l d ( u l t i m o s [ 0 ] ) }   e   $ { b o l d ( u l t i m o s [ 1 ] ) } ` ; 
 
                                 } ; 
 
 
 
                                 c o n s t   l i n h a s P e r i o d o s   =   A r r a y . f r o m ( d o c u m e n t . q u e r y S e l e c t o r A l l ( ' # r e s p - d i v e r s o s - c o n t a i n e r   [ i d ^ = " p e r i o d o - d i v e r s o - " ] ' ) ) ; 
 
                                 i f   ( l i n h a s P e r i o d o s . l e n g t h   = = =   0 )   r e t u r n   n u l l ; 
 
 
 
                                 c o n s t   p r i n c i p a l S e l e c i o n a d a   =   $ ( ' r e s p - d e v e d o r a - p r i n c i p a l ' ) ? . v a l u e   | |   ' 1 ' ; 
 
                                 c o n s t   p e r i o d o C o m p l e t o   =   w i n d o w . h c a l c S t a t e . p l a n i l h a E x t r a c a o D a t a ? . p e r i o d o C a l c u l o   | |   ' ' ; 
 
                                 c o n s t   p r i n c i p a i s P a r c i a i s   =   [ ] ; 
 
                                 c o n s t   s u b s i d i a r i a s C o m P e r i o d o   =   [ ] ; 
 
                               
 
                                 l i n h a s P e r i o d o s . f o r E a c h ( ( l i n h a )   = >   { 
 
                                         c o n s t   i d x   =   l i n h a . i d . r e p l a c e ( ' p e r i o d o - d i v e r s o - ' ,   ' ' ) ; 
 
                                         c o n s t   n o m e R e c   =   d o c u m e n t . q u e r y S e l e c t o r ( ` . p e r i o d o - r e c l a m a d a [ d a t a - i d x = " $ { i d x } " ] ` ) ? . v a l u e   | |   ' ' ; 
 
                                         c o n s t   p e r i o d o T e x t o   =   d o c u m e n t . q u e r y S e l e c t o r ( ` . p e r i o d o - p e r i o d o [ d a t a - i d x = " $ { i d x } " ] ` ) ? . v a l u e   | |   ' ' ; 
 
                                         c o n s t   i d P l a n i l h a   =   d o c u m e n t . q u e r y S e l e c t o r ( ` . p e r i o d o - i d [ d a t a - i d x = " $ { i d x } " ] ` ) ? . v a l u e   | |   ' ' ; 
 
                                         c o n s t   t i p o R a d i o   =   d o c u m e n t . q u e r y S e l e c t o r ( ` i n p u t [ n a m e = " p e r i o d o - t i p o - $ { i d x } " ] : c h e c k e d ` ) ? . v a l u e   | |   ' p r i n c i p a l ' ; 
 
                                       
 
                                         / /   N O V O :   d e t e c t a r   s e   u s a   m e s m a   p l a n i l h a   d a   p r i n c i p a l 
 
                                         c o n s t   p l a n i l h a S e l   =   d o c u m e n t . q u e r y S e l e c t o r ( ` . p e r i o d o - p l a n i l h a - s e l e c t [ d a t a - i d x = " $ { i d x } " ] ` ) ? . v a l u e   | |   ' p r i n c i p a l ' ; 
 
                                         c o n s t   u s a r M e s m a P l a n i l h a   =   p l a n i l h a S e l   = = =   ' p r i n c i p a l ' ; 
 
                                       
 
                                         / /   P e r % o d o   v a z i o   o u   i g u a l   a o   p e r % o d o   c o m p l e t o   =   i n t e g r a l 
 
                                         c o n s t   i s P e r i o d o I n t e g r a l   =   ! p e r i o d o T e x t o   | |   p e r i o d o T e x t o   = = =   p e r i o d o C o m p l e t o ; 
 
                                       
 
                                         i f   ( n o m e R e c   & &   ! i s P e r i o d o I n t e g r a l )   { 
 
                                                 i f   ( t i p o R a d i o   = = =   ' p r i n c i p a l ' )   { 
 
                                                         p r i n c i p a i s P a r c i a i s . p u s h ( {   n o m e :   n o m e R e c ,   p e r i o d o :   p e r i o d o T e x t o ,   i d P l a n i l h a :   i d P l a n i l h a   | |   ' ' ,   u s a r M e s m a P l a n i l h a   } ) ; 
 
                                                 }   e l s e   { 
 
                                                         s u b s i d i a r i a s C o m P e r i o d o . p u s h ( {   n o m e :   n o m e R e c ,   p e r i o d o :   p e r i o d o T e x t o ,   i d P l a n i l h a :   i d P l a n i l h a   | |   ' ' ,   u s a r M e s m a P l a n i l h a   } ) ; 
 
                                                 } 
 
                                         } 
 
                                 } ) ; 
 
 
 
                                 / /   I d e n t i f i c a r   s u b s i d i % r i a s   i n t e g r a i s   ( r e c l a m a d a s   q u e   N % O   s % o   p r i n c i p a i s   e   N % O   e s t % o   e m   p e r % o d o s ) 
 
                                 c o n s t   p r i n c i p a i s N o m e s   =   n e w   S e t ( [ p r i n c i p a l S e l e c i o n a d a ,   . . . p r i n c i p a i s P a r c i a i s . m a p ( p   = >   p . n o m e ) ] ) ; 
 
                                 c o n s t   s u b s i d i a r i a s C o m P e r i o d o N o m e s   =   n e w   S e t ( s u b s i d i a r i a s C o m P e r i o d o . m a p ( s   = >   s . n o m e ) ) ; 
 
                                 c o n s t   t o d a s R e c l a m a d a s   =   A r r a y . f r o m ( d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . c h k - p a r t e - p r i n c i p a l ' ) ) 
 
                                         . m a p ( c h k   = >   c h k . g e t A t t r i b u t e ( ' d a t a - n o m e ' ) ) 
 
                                         . f i l t e r ( n   = >   n ) ; 
 
                               
 
                                 c o n s t   s u b s i d i a r i a s I n t e g r a i s   =   t o d a s R e c l a m a d a s . f i l t e r ( n o m e   = > 
 
                                         ! p r i n c i p a i s N o m e s . h a s ( n o m e )   & &   ! s u b s i d i a r i a s C o m P e r i o d o N o m e s . h a s ( n o m e ) 
 
                                 ) ; 
 
 
 
                                 l e t   t e x t o I n t r o   =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > S o b r e   a   r e s p o n s a b i l i d a d e   p e l o   c r % d i t o ,   t e m - s e   o   s e g u i n t e : < / p > ' ; 
 
                                 t e x t o I n t r o   + =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > 1   -   D e v e d o r a s   P r i n c i p a i s : < / s t r o n g > < / p > ' ; 
 
                                 t e x t o I n t r o   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > -   $ { b o l d ( p r i n c i p a l S e l e c i o n a d a ) }   %   d e v e d o r a   p r i n c i p a l   p e l o   p e r % o d o   i n t e g r a l   d o   c o n t r a t o . < / p > ` ; 
 
                               
 
                                 p r i n c i p a i s P a r c i a i s . f o r E a c h ( p r i n   = >   { 
 
                                         t e x t o I n t r o   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > -   $ { b o l d ( p r i n . n o m e ) }   t a m b % m   %   p r i n c i p a l ,   m a s   p e l o   p e r % o d o   p a r c i a l   d e   $ { p r i n . p e r i o d o } . < / p > ` ; 
 
                                 } ) ; 
 
 
 
                                 c o n s t   t o d a s S u b s i d i a r i a s   =   [ . . . s u b s i d i a r i a s I n t e g r a i s ,   . . . s u b s i d i a r i a s C o m P e r i o d o ] ; 
 
                                 i f   ( t o d a s S u b s i d i a r i a s . l e n g t h   >   0 )   { 
 
                                         t e x t o I n t r o   + =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > 2   -   D e v e d o r a s   S u b s i d i % r i a s : < / s t r o n g > < / p > ' ; 
 
                                       
 
                                         / /   S u b s i d i % r i a s   i n t e g r a i s   ( a g r u p a d a s ) 
 
                                         i f   ( s u b s i d i a r i a s I n t e g r a i s . l e n g t h   >   0 )   { 
 
                                                 c o n s t   l i s t a F o r m a t a d a   =   f o r m a t a r L i s t a ( s u b s i d i a r i a s I n t e g r a i s ) ; 
 
                                                 c o n s t   v e r b o   =   s u b s i d i a r i a s I n t e g r a i s . l e n g t h   = = =   1   ?   ' %   r e s p o n s % v e l   s u b s i d i % r i a '   :   ' s % o   r e s p o n s % v e i s   s u b s i d i % r i a s ' ; 
 
                                                 t e x t o I n t r o   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > -   $ { l i s t a F o r m a t a d a }   $ { v e r b o }   p e l o   p e r % o d o   i n t e g r a l   d o   c o n t r a t o . < / p > ` ; 
 
                                         } 
 
                                       
 
                                         / /   S u b s i d i % r i a s   c o m   p e r % o d o   e s p e c % f i c o   ( i n d i v i d u a i s ) 
 
                                         s u b s i d i a r i a s C o m P e r i o d o . f o r E a c h ( s u b   = >   { 
 
                                                 t e x t o I n t r o   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > -   $ { b o l d ( s u b . n o m e ) }   %   r e s p o n s % v e l   s u b s i d i % r i a   p e l o   p e r % o d o   d e   $ { s u b . p e r i o d o } . < / p > ` ; 
 
                                         } ) ; 
 
                                 } 
 
 
 
                                 t e x t o I n t r o   + =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A p %%s   i s s o ,   p a s s o   % s   h o m o l o g a % % e s   e s p e c % f i c a s : < / p > ' ; 
 
 
 
                                 r e t u r n   { 
 
                                         t e x t o I n t r o , 
 
                                         p r i n c i p a l I n t e g r a l :   p r i n c i p a l S e l e c i o n a d a , 
 
                                         p r i n c i p a i s P a r c i a i s , 
 
                                         s u b s i d i a r i a s :   t o d a s S u b s i d i a r i a s , 
 
                                         s u b s i d i a r i a s I n t e g r a i s , 
 
                                         s u b s i d i a r i a s C o m P e r i o d o , 
 
                                         t o d a s P r i n c i p a i s :   [ 
 
                                                 {   n o m e :   p r i n c i p a l S e l e c i o n a d a ,   p e r i o d o :   ' i n t e g r a l ' ,   i d P l a n i l h a :   ' '   } , 
 
                                                 . . . p r i n c i p a i s P a r c i a i s 
 
                                         ] 
 
                                 } ; 
 
                         } 
 
 
 
                                                 c o n s t   l i n h a s P e r i o d o s   =   A r r a y . f r o m ( d o c u m e n t . q u e r y S e l e c t o r A l l ( ' # r e s p - d i v e r s o s - c o n t a i n e r   [ i d ^ = " p e r i o d o - d i v e r s o - " ] ' ) ) ; 
 
                         c o n s t   u s a r D u p l i c a c a o   =   $ ( ' r e s p - d i v e r s o s ' ) . c h e c k e d   & &   l i n h a s P e r i o d o s . l e n g t h   >   0 ; 
 
 
 
                         i f   ( u s a r D u p l i c a c a o   & &   p a s s i v o T o t a l   >   1 )   { 
 
                                 c o n s t   d a d o s R e s p   =   g e r a r T e x t o R e s p o n s a b i l i d a d e s ( ) ; 
 
                               
 
                                 i f   ( d a d o s R e s p )   { 
 
                                         c o n s t   {   t e x t o I n t r o ,   t o d a s P r i n c i p a i s ,   s u b s i d i a r i a s I n t e g r a i s ,   s u b s i d i a r i a s C o m P e r i o d o   }   =   d a d o s R e s p ; 
 
                                         c o n s t   p r i n c i p a l I n t e g r a l   =   t o d a s P r i n c i p a i s [ 0 ] ; 
 
                                       
 
                                         t e x t   + =   t e x t o I n t r o ; 
 
                                       
 
                                         t e x t   + =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > 1   -   D e v e d o r a s   P r i n c i p a i s : < / s t r o n g > < / p > ' ; 
 
                                       
 
                                         t o d a s P r i n c i p a i s . f o r E a c h ( ( p r i n ,   i )   = >   { 
 
                                                 c o n s t   l e t r a   =   S t r i n g . f r o m C h a r C o d e ( 9 7   +   i ) ; 
 
                                                 c o n s t   l a b e l P r i n   =   p r i n . p e r i o d o   = = =   ' i n t e g r a l ' 
 
                                                         ?   ` $ { b o l d ( p r i n . n o m e ) }   ( P e r % o d o   I n t e g r a l ) ` 
 
                                                         :   ` $ { b o l d ( p r i n . n o m e ) }   ( $ { p r i n . p e r i o d o } ) ` ; 
 
                                               
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > $ { l e t r a } )   R e c l a m a d a   $ { l a b e l P r i n } : < / s t r o n g > < / p > ` ; 
 
                                               
 
                                                 c o n s t   i d P a r a U s a r   =   p r i n . p e r i o d o   = = =   ' i n t e g r a l ' 
 
                                                         ?   i d P l a n i l h a 
 
                                                         :   ( p r i n . u s a r M e s m a P l a n i l h a   | |   ! p r i n . i d P l a n i l h a   ?   i d P l a n i l h a   :   p r i n . i d P l a n i l h a ) ; 
 
 
 
                                                 / /   p l a c e h o l d e r = f a l s e   s e   u s a   m e s m a   p l a n i l h a   ( v a l o r e s   j %   e s t % o   n o   f o r m   p r i n c i p a l ) 
 
                                                 / /   p l a c e h o l d e r = t r u e     s e   t e m   p e r % o d o   p a r c i a l   m a s   s e m   p l a n i l h a   p r %%p r i a   n e m   p r i n c i p a l 
 
                                                 c o n s t   u s a r P l a c e h o l d e r   =   p r i n . p e r i o d o   ! = =   ' i n t e g r a l '   & &   ! p r i n . u s a r M e s m a P l a n i l h a   & &   ! p r i n . i d P l a n i l h a ; 
 
 
 
                                                 a p p e n d B a s e A t e A n t e s P e r i c i a i s ( { 
 
                                                         i d C a l c u l o :   i d P a r a U s a r , 
 
                                                         u s a r P l a c e h o l d e r :   u s a r P l a c e h o l d e r , 
 
                                                         r e c l a m a d a L a b e l :   ' ' 
 
                                                 } ) ; 
 
                                         } ) ; 
 
                                       
 
                                         c o n s t   t o t a l S u b s i d i a r i a s   =   s u b s i d i a r i a s I n t e g r a i s . l e n g t h   +   s u b s i d i a r i a s C o m P e r i o d o . l e n g t h ; 
 
                                         i f   ( t o t a l S u b s i d i a r i a s   >   0 )   { 
 
                                                 t e x t   + =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > 2   -   D e v e d o r a s   S u b s i d i % r i a s : < / s t r o n g > < / p > ' ; 
 
                                                 t e x t   + =   ' < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > ( R e s p o n d e m   a p e n a s   e m   c a s o   d e   i n s u f i c i % n c i a   p a t r i m o n i a l   d a s   p r i n c i p a i s ) < / p > ' ; 
 
                                               
 
                                                 l e t   l e t r a I d x   =   0 ; 
 
                                               
 
                                                 / /   S u b s i d i % r i a s   i n t e g r a i s   ( a g r u p a d a s ) 
 
                                                 s u b s i d i a r i a s I n t e g r a i s . f o r E a c h ( ( n o m e S u b )   = >   { 
 
                                                         c o n s t   l e t r a   =   S t r i n g . f r o m C h a r C o d e ( 9 7   +   l e t r a I d x ) ; 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { l e t r a } )   R e c l a m a d a   $ { b o l d ( n o m e S u b ) } : < / p > ` ; 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < e m > S u b s i d i % r i a   p e l o   p e r % o d o   i n t e g r a l   d o   c o n t r a t o ,   c o m   o s   m e s m o s   v a l o r e s   d e f i n i d o s   p a r a   a   d e v e d o r a   p r i n c i p a l   < s t r o n g > $ { p r i n c i p a l I n t e g r a l . n o m e } < / s t r o n g > ,   c o n f o r m e   p l a n i l h a   < s t r o n g > $ { i d P l a n i l h a } < / s t r o n g > . < / e m > < / p > ` ; 
 
                                                         l e t r a I d x + + ; 
 
                                                 } ) ; 
 
                                               
 
                                                 / /   S u b s i d i % r i a s   c o m   p e r % o d o   e s p e c % f i c o 
 
                                                 s u b s i d i a r i a s C o m P e r i o d o . f o r E a c h ( ( s u b )   = >   { 
 
                                                         c o n s t   l e t r a   =   S t r i n g . f r o m C h a r C o d e ( 9 7   +   l e t r a I d x ) ; 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < s t r o n g > $ { l e t r a } )   R e c l a m a d a   $ { b o l d ( s u b . n o m e ) } < / s t r o n g > < / p > ` ; 
 
 
 
                                                         i f   ( s u b . u s a r M e s m a P l a n i l h a )   { 
 
                                                                 / /           C A S O   1 :   m e s m a   p l a n i l h a   d a   p r i n c i p a l        t e x t o   s i m p l i f i c a d o         
 
                                                                 c o n s t   n o m e P r i n c i p a l   =   p r i n c i p a l I n t e g r a l ; 
 
                                                                 c o n s t   i d P r i n c i p a l U s a r   =   i d P l a n i l h a ;   / /   v a l - i d . v a l u e        p l a n i l h a   p r i n c i p a l 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > 
 
                                                                         < e m > S u b s i d i % r i a   p e l o   p e r % o d o   d e   < s t r o n g > $ { s u b . p e r i o d o } < / s t r o n g > . 
 
                                                                         O s   v a l o r e s   s % o   o s   m e s m o s   d e f i n i d o s   p a r a   a   d e v e d o r a   p r i n c i p a l 
 
                                                                         < s t r o n g > $ { n o m e P r i n c i p a l } < / s t r o n g > ,   c o n f o r m e   p l a n i l h a   < s t r o n g > $ { i d P r i n c i p a l U s a r } < / s t r o n g > , 
 
                                                                         n % o   s e n d o   n e c e s s % r i a   h o m o l o g a % % o   e m   s e p a r a d o . < / e m > < / p > ` ; 
 
                                                         }   e l s e   { 
 
                                                                 / /           C A S O   2 :   p l a n i l h a   p r %%p r i a   c a r r e g a d a   o u   s e m   p l a n i l h a         
 
                                                                 c o n s t   i d S u b P l a n i l h a   =   s u b . i d P l a n i l h a   | |   i d P l a n i l h a ; 
 
                                                                 c o n s t   c o m P l a c e h o l d e r   =   ! s u b . i d P l a n i l h a ;   / /   s e m   p l a n i l h a   p r %%p r i a   =   p l a c e h o l d e r 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > 
 
                                                                         < e m > S u b s i d i % r i a   p e l o   p e r % o d o   d e   < s t r o n g > $ { s u b . p e r i o d o } < / s t r o n g > . < / e m > < / p > ` ; 
 
                                                                 a p p e n d B a s e A t e A n t e s P e r i c i a i s ( { 
 
                                                                         i d C a l c u l o :   i d S u b P l a n i l h a , 
 
                                                                         u s a r P l a c e h o l d e r :   c o m P l a c e h o l d e r , 
 
                                                                         r e c l a m a d a L a b e l :   s u b . n o m e 
 
                                                                 } ) ; 
 
                                                         } 
 
                                                         l e t r a I d x + + ; 
 
                                                 } ) ; 
 
                                         } 
 
                                 } 
 
 
 
                                 a p p e n d D i s p o s i c o e s F i n a i s ( ) ; 
 
                         }   e l s e   { 
 
                                 l e t   i n t r o T x t   =   ' ' ; 
 
                                 i f   ( i s P e r i t o   & &   p e r i t o E s c l a r e c e u )   { 
 
                                         i n t r o T x t   + =   ` A s   i m p u g n a % % e s   a p r e s e n t a d a s   j %   f o r a m   o b j e t o   d e   e s c l a r e c i m e n t o s   p e l o   S r .   P e r i t o   s o b   o   # $ { b o l d ( p e c a P e r i t o ) } ,   n a d a   h a v e n d o   a   s e r   r e p a r a d o   n o   l a u d o .   P o r t a n t o ,   H O M O L O G O   o s   c % l c u l o s   d o   e x p e r t   ( # $ { b o l d ( i d P l a n i l h a ) } ) ,   ` ; 
 
                                 }   e l s e   { 
 
                                         i n t r o T x t   + =   ` T e n d o   e m   v i s t a   a   c o n c o r d % n c i a   d a s   p a r t e s ,   H O M O L O G O   o s   c % l c u l o s   a p r e s e n t a d o s   p e l o ( a )   $ { u ( a u t o r i a ) }   ( # $ { b o l d ( i d P l a n i l h a ) } ) ,   ` ; 
 
                                 } 
 
 
 
                                 / /   V e r i f i c a r   s e   F G T S   f o i   d e p o s i t a d o   ( p a r a   e v i t a r   c o n t r a d i % % o ) 
 
                                 c o n s t   f g t s T i p o   =   i s F g t s S e p   ?   ( d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " f g t s - t i p o " ] : c h e c k e d ' ) ? . v a l u e   | |   ' d e v i d o ' )   :   ' d e v i d o ' ; 
 
                                 c o n s t   f g t s J a D e p o s i t a d o   =   f g t s T i p o   = = =   ' d e p o s i t a d o ' ; 
 
 
 
                                 i f   ( i s F g t s S e p   & &   ! f g t s J a D e p o s i t a d o )   { 
 
                                         / /   F G T S   d e v i d o   ( a   s e r   r e c o l h i d o ) 
 
                                         i n t r o T x t   + =   ` f i x a n d o   o   c r % d i t o   d o   a u t o r   e m   $ { b o l d ( ' R $ '   +   v a l C r e d i t o ) }   r e l a t i v o   a o   p r i n c i p a l ,   e   $ { b o l d ( ' R $ '   +   v a l F g t s ) }   r e l a t i v o   a o   $ { b o l d ( ' F G T S ' ) }   a   s e r   r e c o l h i d o   e m   c o n t a   v i n c u l a d a ,   a t u a l i z a d o s   p a r a   $ { b o l d ( v a l D a t a ) } .   ` ; 
 
                                 }   e l s e   i f   ( i s F g t s S e p   & &   f g t s J a D e p o s i t a d o )   { 
 
                                         / /   F G T S   d e p o s i t a d o   ( n % o   m e n c i o n a   " a   s e r   r e c o l h i d o " ) 
 
                                         i n t r o T x t   + =   ` f i x a n d o   o   c r % d i t o   d o   a u t o r   e m   $ { b o l d ( ' R $ '   +   v a l C r e d i t o ) } ,   a t u a l i z a d o   p a r a   $ { b o l d ( v a l D a t a ) } .   ` ; 
 
                                 }   e l s e   { 
 
                                         i n t r o T x t   + =   ` f i x a n d o   o   c r % d i t o   e m   $ { b o l d ( ' R $ '   +   v a l C r e d i t o ) } ,   r e f e r e n t e   a o   v a l o r   p r i n c i p a l ,   a t u a l i z a d o   p a r a   $ { b o l d ( v a l D a t a ) } .   ` ; 
 
                                 } 
 
                                 i f   ( i n d i c e   = = =   ' a d c 5 8 ' )   { 
 
                                         i f   ( i s F g t s S e p )   { 
 
                                                 i n t r o T x t   + =   ` A   a t u a l i z a % % o   f o i   f e i t a   n a   f o r m a   d a   L e i   1 4 . 9 0 5 / 2 0 2 4   e   d a   d e c i s % o   d a   S D I - 1   d o   C .   T S T   ( I P C A - E   a t %   a   d i s t r i b u i % % o ;   t a x a   S e l i c   a t %   2 9 / 0 8 / 2 0 2 4 ,   e   I P C A   +   j u r o s   d e   m o r a   a   p a r t i r   d e   3 0 / 0 8 / 2 0 2 4 ) . ` ; 
 
                                         }   e l s e   { 
 
                                                 i n t r o T x t   + =   ` A   c o r r e % % o   m o n e t % r i a   f o i   r e a l i z a d a   p e l o   I P C A - E   n a   f a s e   p r % - j u d i c i a l   e ,   a   p a r t i r   d o   a j u i z a m e n t o ,   p e l a   t a x a   S E L I C   ( A D C   5 8 ) . ` ; 
 
                                         } 
 
                                 }   e l s e   { 
 
                                         c o n s t   v a l J u r o s   =   $ ( ' v a l - j u r o s ' ) . v a l u e   | |   ' [ J U R O S ] ' ; 
 
                                         c o n s t   d t I n g r e s s o   =   $ ( ' d a t a - i n g r e s s o ' ) . v a l u e   | |   ' [ D A T A   I N G R E S S O ] ' ; 
 
                                         i n t r o T x t   + =   ` A t u a l i z % v e i s   p e l a   T R / I P C A - E ,   c o n f o r m e   s e n t e n % a .   J u r o s   l e g a i s   d e   $ { b o l d ( ' R $ '   +   v a l J u r o s ) }   a   p a r t i r   d e   $ { b o l d ( d t I n g r e s s o ) } . ` ; 
 
                                 } 
 
                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { i n t r o T x t } < / p > ` ; 
 
 
 
                                 / /   2 ,%Q%  p a r % g r a f o :   F G T S   d e p o s i t a d o   ( c o m   v a l o r ) 
 
                                 i f   ( i s F g t s S e p   & &   f g t s J a D e p o s i t a d o )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > < u > O   F G T S   d e v i d o ,   $ { b o l d ( ' R $ '   +   v a l F g t s ) } ,   j %   f o i   d e p o s i t a d o ,   p o r t a n t o   d e d u z i d o . < / u > < / p > ` ; 
 
                                 } 
 
 
 
                                 i f   ( p a s s i v o T o t a l   >   1 )   { 
 
                                         i f   ( $ ( ' r e s p - t i p o ' ) . v a l u e   = = =   ' s o l i d a r i a s ' )   { 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > D e c l a r o   q u e   a s   r e c l a m a d a s   r e s p o n d e m   d e   f o r m a   s o l i d % r i a   p e l a   p r e s e n t e   e x e c u % % o . < / p > ` ; 
 
                                         }   e l s e   i f   ( $ ( ' r e s p - t i p o ' ) . v a l u e   = = =   ' s u b s i d i a r i a s ' )   { 
 
                                                 i f   ( $ ( ' r e s p - i n t e g r a l ' ) . c h e c k e d )   { 
 
                                                         / /   O b t e r   l i s t a   d e   p r i n c i p a i s   e   s u b s i d i % r i a s 
 
                                                         c o n s t   p r i n c i p a i s   =   [ ] ; 
 
                                                         c o n s t   s u b s i d i a r i a s   =   [ ] ; 
 
                                                       
 
                                                         d o c u m e n t . q u e r y S e l e c t o r A l l ( ' . c h k - p a r t e - p r i n c i p a l ' ) . f o r E a c h ( c h k   = >   { 
 
                                                                 c o n s t   n o m e   =   c h k . g e t A t t r i b u t e ( ' d a t a - n o m e ' ) ; 
 
                                                                 i f   ( c h k . c h e c k e d )   { 
 
                                                                         p r i n c i p a i s . p u s h ( n o m e ) ; 
 
                                                                 }   e l s e   { 
 
                                                                         s u b s i d i a r i a s . p u s h ( n o m e ) ; 
 
                                                                 } 
 
                                                         } ) ; 
 
                                                       
 
                                                         / /   T e x t o   e s p e c % f i c o   n o m e a n d o   p r i n c i p a i s   e   s u b s i d i % r i a s 
 
                                                         i f   ( p r i n c i p a i s . l e n g t h   >   0   & &   s u b s i d i a r i a s . l e n g t h   >   0 )   { 
 
                                                                 c o n s t   f o r m a t a r L i s t a   =   ( n o m e s )   = >   { 
 
                                                                         i f   ( n o m e s . l e n g t h   = = =   1 )   r e t u r n   b o l d ( n o m e s [ 0 ] ) ; 
 
                                                                         i f   ( n o m e s . l e n g t h   = = =   2 )   r e t u r n   ` $ { b o l d ( n o m e s [ 0 ] ) }   e   $ { b o l d ( n o m e s [ 1 ] ) } ` ; 
 
                                                                         r e t u r n   n o m e s . s l i c e ( 0 ,   - 1 ) . m a p ( n   = >   b o l d ( n ) ) . j o i n ( ' ,   ' )   +   '   e   '   +   b o l d ( n o m e s [ n o m e s . l e n g t h   -   1 ] ) ; 
 
                                                                 } ; 
 
                                                               
 
                                                                 c o n s t   t x t P r i n c i p a i s   =   f o r m a t a r L i s t a ( p r i n c i p a i s ) ; 
 
                                                                 c o n s t   t x t S u b s i d i a r i a s   =   f o r m a t a r L i s t a ( s u b s i d i a r i a s ) ; 
 
                                                                 c o n s t   v e r b o P r i n   =   p r i n c i p a i s . l e n g t h   >   1   ?   ' s % o   d e v e d o r a s   p r i n c i p a i s '   :   ' %   d e v e d o r a   p r i n c i p a l ' ; 
 
                                                                 c o n s t   v e r b o S u b   =   s u b s i d i a r i a s . l e n g t h   >   1   ?   ' s % o   s u b s i d i % r i a s '   :   ' %   s u b s i d i % r i a ' ; 
 
                                                               
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { t x t P r i n c i p a i s }   $ { v e r b o P r i n } ,   $ { t x t S u b s i d i a r i a s }   $ { v e r b o S u b }   p e l o   p e r % o d o   i n t e g r a l   d o   c o n t r a t o ,   p o r t a n t o ,   o s   v a l o r e s   n e s t e   m o m e n t o   s % o   d e v i d o s   a p e n a s   p e l a s   p r i n c i p a i s . < / p > ` ; 
 
                                                         }   e l s e   { 
 
                                                                 / /   F a l l b a c k   s e   n % o   h o u v e r   c h e c k b o x e s   m a r c a d o s 
 
                                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A   p r i m e i r a   r e c l a m a d a   %   d e v e d o r a   p r i n c i p a l ,   a s   d e m a i s   s % o   s u b s i d i % r i a s   p e l o   p e r % o d o   i n t e g r a l   d o   c o n t r a t o ,   p o r t a n t o ,   o s   v a l o r e s   n e s t e   m o m e n t o   s % o   d e v i d o s   a p e n a s   p e l a   p r i m e i r a . < / p > ` ; 
 
                                                         } 
 
                                                 } 
 
                                         } 
 
                                 } 
 
                                 i f   ( $ ( ' c a l c - o r i g e m ' ) . v a l u e   = = =   ' p j e c a l c '   & &   ! $ ( ' c a l c - p j c ' ) . c h e c k e d )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > C o n s i d e r a n d o   a   a u s % n c i a   d o   a r q u i v o   d e   o r i g e m ,   < u > d e v e r %   a   p a r t e   a p r e s e n t a r   n o v a m e n t e   a   p l a n i l h a   o r a   h o m o l o g a d a ,   a c o m p a n h a d a   o b r i g a t o r i a m e n t e   d o   r e s p e c t i v o   a r q u i v o   $ { b o l d ( ' . P J C ' ) }   n o   p r a z o   d e   0 5   d i a s < / u > . < / p > ` ; 
 
                                 } 
 
                                 i f   ( i g n o r a r I n s s )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P e l a   n a t u r e z a   d o   c r % d i t o ,   n % o   h %   c o n t r i b u i % % e s   p r e v i d e n c i % r i a s   d e v i d a s . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   v a l I n s s R e c S t r   =   $ ( ' v a l - i n s s - r e c ' ) . v a l u e   | |   ' 0 ' ; 
 
                                         c o n s t   v a l I n s s T o t a l S t r   =   $ ( ' v a l - i n s s - t o t a l ' ) . v a l u e   | |   ' 0 ' ; 
 
                                         c o n s t   v a l I n s s R e c   =   p a r s e M o n e y ( v a l I n s s R e c S t r ) ; 
 
                                         c o n s t   v a l I n s s T o t a l   =   p a r s e M o n e y ( v a l I n s s T o t a l S t r ) ; 
 
                                         l e t   v a l I n s s R e c l a m a d a S t r   =   v a l I n s s T o t a l S t r ; 
 
                                         i f   ( $ ( ' c a l c - o r i g e m ' ) . v a l u e   = = =   ' p j e c a l c ' )   { 
 
                                                 c o n s t   r e c R e s u l t   =   v a l I n s s T o t a l   -   v a l I n s s R e c ; 
 
                                                 v a l I n s s R e c l a m a d a S t r   =   f o r m a t M o n e y ( r e c R e s u l t ) ; 
 
                                         } 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > A   r e c l a m a d a   d e v e r %   p a g a r   o   v a l o r   d e   s u a   c o t a - p a r t e   n o   I N S S ,   a   s a b e r ,   $ { b o l d ( v a l I n s s R e c l a m a d a S t r ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } . < / p > ` ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > D e s d e   j % ,   f i c a m   a u t o r i z a d o s   o s   d e s c o n t o s   p r e v i d e n c i % r i o s   ( c o t a   d o   r e c l a m a n t e )   o r a   f i x a d o s   e m   $ { b o l d ( ' R $ '   +   v a l I n s s R e c S t r ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } . < / p > ` ; 
 
                                 } 
 
                                 i f   ( $ ( ' i r p f - t i p o ' ) . v a l u e   = = =   ' i s e n t o ' )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > N % o   h %   d e d u % % e s   f i s c a i s   c a b % v e i s . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   v B a s e   =   $ ( ' v a l - i r p f - b a s e ' ) . v a l u e   | |   ' [ V A L O R ] ' ; 
 
                                         i f   ( $ ( ' c a l c - o r i g e m ' ) . v a l u e   = = =   ' p j e c a l c ' )   { 
 
                                                 c o n s t   v M e s   =   $ ( ' v a l - i r p f - m e s e s ' ) . v a l u e   | |   ' [ X ] ' ; 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > F i c a m   a u t o r i z a d o s   o s   d e s c o n t o s   f i s c a i s ,   c a l c u l a d o s   s o b r e   a s   v e r b a s   t r i b u t % v e i s   ( $ { b o l d ( ' R $ '   +   v B a s e ) } ) ,   p e l o   p e r % o d o   d e   $ { b o l d ( v M e s   +   '   m e s e s ' ) } . < / p > ` ; 
 
                                         }   e l s e   { 
 
                                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > P a r a   a s   d e d u % % e s   f i s c a i s   d e   I m p o s t o   d e   R e n d a ,   f i x a d a s   e m   $ { b o l d ( ' R $ '   +   v B a s e ) }   p a r a   $ { b o l d ( v a l D a t a ) } ,   o b s e r v e m - s e   a   S %Q%m u l a   3 6 8   d o   T S T   e   I N   R F B   1 5 0 0 / 2 0 1 4 . < / p > ` ; 
 
                                         } 
 
                                 } 
 
                                 i f   ( ! $ ( ' i g n o r a r - h o n - a u t o r ' ) . c h e c k e d )   { 
 
                                         c o n s t   v H o n A   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - h o n - a u t o r ' ) . v a l u e   | |   ' [ V A L O R ] ' ) ; 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   p e l a   r e c l a m a d a ,   n o   i m p o r t e   d e   $ { b o l d ( v H o n A ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } . < / p > ` ; 
 
                                 } 
 
                                 i f   ( $ ( ' c h k - h o n - r e u ' ) . c h e c k e d )   { 
 
                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > N % o   f o r a m   a r b i t r a d o s   h o n o r % r i o s   a o   a d v o g a d o   d o   r % u . < / p > ` ; 
 
                                 }   e l s e   { 
 
                                         c o n s t   t i p o H o n R e u   =   d o c u m e n t . q u e r y S e l e c t o r ( ' i n p u t [ n a m e = " r a d - h o n - r e u - t i p o " ] : c h e c k e d ' ) . v a l u e ; 
 
                                         c o n s t   t e m S u s p e n s i v a   =   $ ( ' c h k - h o n - r e u - s u s p e n s i v a ' ) . c h e c k e d ; 
 
                                       
 
                                         i f   ( t i p o H o n R e u   = = =   ' p e r c e n t u a l ' )   { 
 
                                                 c o n s t   p   =   $ ( ' v a l - h o n - r e u - p e r c ' ) . v a l u e ; 
 
                                                 i f   ( t e m S u s p e n s i v a )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   p e l a   r e c l a m a n t e   s o b   c o n d i % % o   s u s p e n s i v a ,   n a   o r d e m   d e   $ { b o l d ( p ) } ,   d i a n t e   d a   g r a t u i d a d e   d e f e r i d a . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   e m   f a v o r   d a   r e c l a m a d a   n a   o r d e m   d e   $ { b o l d ( p ) } ,   a   s e r e m   d e s c o n t a d o s   d o   c r % d i t o   d o   a u t o r . < / p > ` ; 
 
                                                 } 
 
                                         }   e l s e   { 
 
                                                 c o n s t   v H o n R   =   n o r m a l i z e M o n e y I n p u t ( $ ( ' v a l - h o n - r e u ' ) . v a l u e   | |   ' [ V A L O R ] ' ) ; 
 
                                                 i f   ( t e m S u s p e n s i v a )   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   p e l a   r e c l a m a n t e   s o b   c o n d i % % o   s u s p e n s i v a ,   n o   i m p o r t e   d e   $ { b o l d ( v H o n R ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } ,   d i a n t e   d a   g r a t u i d a d e   d e f e r i d a . < / p > ` ; 
 
                                                 }   e l s e   { 
 
                                                         t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > H o n o r % r i o s   a d v o c a t % c i o s   s u c u m b e n c i a i s   e m   f a v o r   d a   r e c l a m a d a ,   n o   i m p o r t e   d e   $ { b o l d ( v H o n R ) } ,   p a r a   $ { b o l d ( v a l D a t a ) } ,   a   s e r e m   d e s c o n t a d o s   d o   c r % d i t o   d o   a u t o r . < / p > ` ; 
 
                                                 } 
 
                                         } 
 
                                 } 
 
                                 a p p e n d D i s p o s i c o e s F i n a i s ( ) ; 
 
                         } 
 
 
 
                         / /   L i n h a   f i n a l   -   O M I T I R   s e   h o u v e r   l i b e r a % % o   d e t a l h a d a   ( d e p %%s i t o   r e c u r s a l   o u   p a g a m e n t o   a n t e c i p a d o ) 
 
                         i f   ( ! h o u v e L i b e c a o D e t a l h a d a )   { 
 
                                 t e x t   + =   ` < p   s t y l e = " t e x t - a l i g n : j u s t i f y ;   t e x t - i n d e n t :   4 . 5 c m ;   f o n t - s i z e : 1 2 p t ; " > $ { u ( ' F i c a m   a s   p a r t e s   c i e n t e s   d e   q u e   q u a l q u e r   q u e s t i o n a m e n t o   a c e r c a   d e s t a   d e c i s % o ,   s a l v o   e r r o   m a t e r i a l ,   s e r %   a p r e c i a d o   a p %%s   a   g a r a n t i a   d o   j u % z o . ' ) } < / p > ` ; 
 
                         } 
 
                         c o n s t   b l o b   =   n e w   B l o b ( [ t e x t ] ,   {   t y p e :   ' t e x t / h t m l '   } ) ; 
 
                         c o n s t   c l i p b o a r d I t e m   =   n e w   w i n d o w . C l i p b o a r d I t e m ( {   ' t e x t / h t m l ' :   b l o b   } ) ; 
 
                         n a v i g a t o r . c l i p b o a r d . w r i t e ( [ c l i p b o a r d I t e m ] ) . t h e n ( ( )   = >   { 
 
                                 a l e r t ( ' D e c i s % o   c o p i a d a   c o m   s u c e s s o !   V %   a o   e d i t o r   d o   P J e   e   c o l e   ( C t r l + V ) . ' ) ; 
 
                                 $ ( ' h o m o l o g a c a o - o v e r l a y ' ) . s t y l e . d i s p l a y   =   ' n o n e ' ; 
 
                                 d b g ( ' D e c i s a o   c o p i a d a   p a r a   a r e a   d e   t r a n s f e r e n c i a   c o m   s u c e s s o . ' ) ; 
 
                         } ) . c a t c h ( ( e r r )   = >   { 
 
                                 a l e r t ( ' E r r o   a o   c o p i a r .   O   n a v e g a d o r   p o d e   t e r   b l o q u e a d o . ' ) ; 
 
                                 c o n s o l e . e r r o r ( e r r ) ; 
 
                                 e r r ( ' F a l h a   a o   c o p i a r   d e c i s a o   p a r a   c l i p b o a r d : ' ,   e r r ) ; 
 
                         } ) ; 
 
                 } ; 
 
 
 
                 d b g ( ' i n i t i a l i z e O v e r l a y   f i n a l i z a d o   c o m   s u c e s s o . ' ) ; 
 
         } 
 
 
 
         / /   P o n t o   d e   e n t r a d a   e x p o s t o   p a r a   h c a l c . u s e r . j s 
 
         w i n d o w . h c a l c I n i t B o t a o   =   i n i t i a l i z e B o t a o ; 
 
 } ) ( ) ; 
 
 

// ── hcalc.js ──────────────────────────────────
// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.10.6
// @description  Pagamento antecipado substitui intimações, adiciona texto de manifestação
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==


(function () {
    'use strict';

    // FILTRO ANTI-IFRAME: Impede execução em iframes (PDF viewer, etc)
    if (window.self !== window.top) {
        return;
    }

    // Marcador de execução
    document.documentElement.setAttribute('data-hcalc-boot', '1');

    // DEBUG: false em produção para reduzir I/O do console
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);
    if (HCALC_DEBUG) dbg('Script carregado em:', window.location.href);

    if (!window.__hcalcGlobalErrorHooksInstalled) {
        window.__hcalcGlobalErrorHooksInstalled = true;
        window.addEventListener('error', (event) => {
            err('Erro global capturado:', event?.message, event?.filename, event?.lineno, event?.colno, event?.error);
        });
        window.addEventListener('unhandledrejection', (event) => {
            err('Promise rejeitada sem tratamento:', event?.reason);
        });
    }

    // ==========================================
    // ESTADO CENTRAL HCALC
    // ==========================================
    // Centraliza todas as variáveis de estado do script
    // Permite dispose() completo para evitar vazamentos de memória
    if (!window.hcalcState) {
        window.hcalcState = {
            // Cache de partes (limitado a 5 entradas)
            calcPartesCache: {},

            // Flags de execução
            prepRunning: false,

            // Resultados do prep
            prepResult: null,
            timelineData: null,

            // Dados detectados
            peritosConhecimento: [],
            partesData: null,

            // AbortController para cancelamento de operações
            abortController: null,

            // Método de limpeza completa
            dispose() {
                dbg('Executando dispose() - limpando estado hcalc');

                // Abortar operações em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.calcPartesCache = {};
                this.prepRunning = false;
                this.prepResult = null;
                this.timelineData = null;
                this.peritosConhecimento = [];
                this.partesData = null;
                dbg('Estado hcalc limpo');
            },

            // Método de reset parcial (mantém cache)
            resetPrep() {
                // Abortar prep em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.prepResult = null;
                this.timelineData = null;
                this.prepRunning = false;
            }
        };
    }

    // Aliases de retrocompatibilidade (apontam para hcalcState)
    // Permite que código existente continue funcionando sem modificação
    Object.defineProperty(window, 'calcPartesCache', {
        get() { return window.hcalcState.calcPartesCache; },
        set(val) { window.hcalcState.calcPartesCache = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPrepRunning', {
        get() { return window.hcalcState.prepRunning; },
        set(val) { window.hcalcState.prepRunning = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPrepResult', {
        get() { return window.hcalcState.prepResult; },
        set(val) { window.hcalcState.prepResult = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcTimelineData', {
        get() { return window.hcalcState.timelineData; },
        set(val) { window.hcalcState.timelineData = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPeritosConhecimentoDetectados', {
        get() { return window.hcalcState.peritosConhecimento; },
        set(val) { window.hcalcState.peritosConhecimento = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPartesData', {
        get() { return window.hcalcState.partesData; },
        set(val) { window.hcalcState.partesData = val; },
        configurable: true
    });

    // ==========================================
    // MONITOR DE NAVEGAÇÃO SPA
    // ==========================================
    // Detecta mudança de URL no PJe (SPA) e limpa estado automaticamente
    // Previne vazamento de memória ao trocar de processo sem fechar overlay
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            dbg('Navegação SPA detectada, limpando estado...');

            // Dispose completo
            if (window.hcalcState) {
                window.hcalcState.dispose();
            }

            // Ocultar overlay se estiver aberto
            const overlay = document.getElementById('homologacao-overlay');
            if (overlay) overlay.style.display = 'none';
        }
    }).observe(document, { subtree: true, childList: true });

    // prep.js — Preparação pré-overlay para hcalc.js
    // Varre timeline, extrai dados da sentença, cruza peritos com AJ-JT, monta depósitos.
    // Uso: const result = await window.executarPrep(partesData, peritosConhecimento);

    // (IIFE removida para escopo único)

    // ==========================================
    // UTILIDADES
    // ==========================================
    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    function normalizeText(str) {
        return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    // Normaliza data de "17 nov. 2025" para "17/11/2025"
    function normalizarDataTimeline(dataStr) {
        if (!dataStr) return '';
        const meses = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
            'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        };
        // Padrão: "17 nov. 2025" ou "17 nov 2025"
        const match = dataStr.match(/(\d{1,2})\s+(\w{3})\.?\s+(\d{4})/);
        if (match) {
            const dia = match[1].padStart(2, '0');
            const mes = meses[match[2].toLowerCase()] || '00';
            const ano = match[3];
            return `${dia}/${mes}/${ano}`;
        }
        return dataStr; // Retorna original se não reconhecer
    }

    // ==========================================
    // TIMELINE: VARREDURA ÚNICA
    // ==========================================
    function getTimelineItems() {
        const selectors = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item'];
        for (const sel of selectors) {
            const items = Array.from(document.querySelectorAll(sel));
            if (items.length > 0) return items;
        }
        return [];
    }

    function extractDataFromItem(item) {
        let el = null;
        let prev = item.previousElementSibling;
        while (prev) {
            el = prev.querySelector('.tl-data[name="dataItemTimeline"]') || prev.querySelector('.tl-data');
            if (el) break;
            prev = prev.previousElementSibling;
        }
        if (!el) el = item.querySelector('.tl-data[name="dataItemTimeline"]') || item.querySelector('.tl-data');
        const dataOriginal = (el?.textContent || '').trim();
        return normalizarDataTimeline(dataOriginal);
    }

    function tipoDocumentoDoItem(item) {
        const link = item.querySelector('a.tl-documento[target="_blank"]');
        if (!link) return '';
        const ariaLabel = link.getAttribute('aria-label') || '';
        const m = ariaLabel.match(/Tipo do documento:\s*([^.]+)/i);
        return m ? normalizeText(m[1].trim()) : '';
    }

    function tituloDocumentoDoItem(item) {
        const link = item.querySelector('a.tl-documento[target="_blank"]');
        if (!link) return '';
        const ariaLabel = link.getAttribute('aria-label') || '';
        const m = ariaLabel.match(/Título:\s*\(([^)]+)\)/i);
        return m ? normalizeText(m[1].trim()) : '';
    }

    function hasAnexoNoItem(item) {
        if (!item) return false;
        const sels = [
            'div[name="mostrarOuOcultarAnexos"]',
            'pje-timeline-anexos div[name="areaAnexos"]',
            '.fa-paperclip'
        ];
        return sels.some(s => item.querySelector(s));
    }

    function isPoloPassivoNoItem(item) {
        if (!item) return false;
        const container = item.closest('li.tl-item-container') || item;
        return !!container.querySelector('.icone-polo-passivo, [class*="polo-passivo"]');
    }

    // Extrai o nome da parte do polo passivo a partir do aria-label do div tipoItemTimeline
    // Ex: aria-label="VIBRASIL INDUSTRIA DE ARTEFATOS DE BORRACHA LTDA"
    function nomePassivoDoItem(item) {
        if (!item) return '';
        const container = item.closest('li.tl-item-container') || item;
        const tipoDiv = container.querySelector('div[name="tipoItemTimeline"]');
        return tipoDiv?.getAttribute('aria-label')?.trim() || '';
    }

    function hrefDoItem(item) {
        const link = item.querySelector('a.tl-documento[target="_blank"]');
        return link?.href || null;
    }

    function textoDoItem(item) {
        const previewLink = item.querySelector('a.tl-documento[role="button"]:not([target])')
            || item.querySelector('a.tl-documento:not([target])');
        return (previewLink?.textContent || item.textContent || '').replace(/\s+/g, ' ').trim();
    }

    function idDocumentoDoItem(item) {
        // Extrai ID do formato: <span class="ng-star-inserted"> - 44709e4</span>
        const previewLink = item.querySelector('a.tl-documento[role="button"]:not([target])')
            || item.querySelector('a.tl-documento:not([target])');
        if (!previewLink) return null;

        const spans = previewLink.querySelectorAll('span.ng-star-inserted');
        for (let i = spans.length - 1; i >= 0; i--) {
            const texto = spans[i].textContent.trim();
            const match = texto.match(/^\s*-\s*([a-f0-9]{7})$/i);
            if (match) return match[1];
        }
        return null;
    }

    // Varredura única: classifica todos os items da timeline
    function varrerTimeline() {
        const items = getTimelineItems();
        const resultado = {
            sentencas: [],
            acordaos: [],
            editais: [],
            recursosPassivo: [],  // RO/RR + polo passivo + anexo
            honAjJt: []
        };

        items.forEach((item, idx) => {
            const texto = textoDoItem(item);
            const textoNorm = normalizeText(texto);
            const tipoDoc = tipoDocumentoDoItem(item);
            const tituloDoc = tituloDocumentoDoItem(item);
            const data = extractDataFromItem(item);
            const href = hrefDoItem(item);

            // BASE: Apenas dados essenciais (SEM element: item para evitar vazamento DOM)
            const base = {
                idx,
                texto: texto.substring(0, 300), // Limitar tamanho do texto
                data,
                href
            };

            // Sentença
            if (textoNorm.includes('sentenca') || textoNorm.includes('sentença')) {
                resultado.sentencas.push({ ...base, tipo: 'sentenca' });
                return;
            }

            // Acórdão - CAPTURA ID
            if (textoNorm.includes('acordao') && !textoNorm.includes('intima')) {
                const idDoc = idDocumentoDoItem(item);
                resultado.acordaos.push({ ...base, id: idDoc, tipo: 'acordao' });
                return;
            }

            // Recurso Ordinário / Recurso de Revista (polo passivo + anexo)
            if ((tipoDoc === 'recurso ordinario' || tipoDoc === 'recurso de revista'
                || tipoDoc.includes('recurso ordinario') || tipoDoc.includes('recurso de revista'))
                && isPoloPassivoNoItem(item) && hasAnexoNoItem(item)) {
                const tipoRec = tipoDoc.includes('revista') ? 'RR' : 'RO';
                const depositante = nomePassivoDoItem(item);
                resultado.recursosPassivo.push({ ...base, tipoRec, depositante });
                return;
            }

            // Honorários Periciais AJ-JT - CAPTURA ID
            if (/peric[ia]*.*aj[\s-]*jt/i.test(tituloDoc) || /peric[ia]*.*aj[\s-]*jt/i.test(texto)) {
                const idDoc = idDocumentoDoItem(item);
                resultado.honAjJt.push({ ...base, id: idDoc, tipo: 'hon_ajjt' });
                return;
            }

            // Edital
            if (textoNorm.includes('edital')) {
                resultado.editais.push({ ...base, tipo: 'edital' });
            }
        });

        // Sentença alvo = mais antiga (última no array, pois timeline é desc)
        return resultado;
    }

    // ==========================================
    // EXTRAÇÃO VIA HTML ORIGINAL
    // ==========================================

    // Abre o documento inline (clica no preview link)
    function abrirDocumentoInline(item) {
        const previewLink = item.querySelector('a.tl-documento[accesskey="v"]:not([target])')
            || item.querySelector('a.tl-documento[role="button"]:not([target])')
            || item.querySelector('a.tl-documento:not([target])');
        if (previewLink) {
            try { previewLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }
            catch (_) { try { previewLink.click(); } catch (_2) { } }
        }
    }

    // Recaptura elemento da timeline pelo href (evita guardar referências DOM)
    function encontrarItemTimeline(href) {
        if (!href) return null;
        const items = getTimelineItems();
        for (const item of items) {
            const link = item.querySelector('a.tl-documento[target="_blank"]');
            if (link && link.href === href) return item;
        }
        return null;
    }

    // Abre documento inline via href (recaptura elemento dinamicamente)
    function abrirDocumentoInlineViaHref(href) {
        const item = encontrarItemTimeline(href);
        if (!item) return false;
        abrirDocumentoInline(item);
        return true;
    }

    // Clica em "Visualizar HTML original" e lê #previewModeloDocumento
    async function lerHtmlOriginal(timeoutMs = 5000, abortSignal = null) {
        const started = Date.now();

        // 1. Espera o botão aparecer (com suporte a cancelamento)
        let htmlBtn = null;
        while ((Date.now() - started) < timeoutMs) {
            if (abortSignal?.aborted) {
                console.log('[hcalc] lerHtmlOriginal cancelado (aborted)');
                return null;
            }
            htmlBtn = document.querySelector('button[aria-label="Visualizar HTML original"]');
            if (htmlBtn) break;
            await sleep(150); // Reduzido de 200ms para 150ms
        }
        if (!htmlBtn) return null;

        htmlBtn.click();

        // 2. Espera o conteúdo carregar (com suporte a cancelamento)
        let previewEl = null;
        const started2 = Date.now();
        while ((Date.now() - started2) < timeoutMs) {
            if (abortSignal?.aborted) {
                console.log('[hcalc] lerHtmlOriginal cancelado (aborted)');
                return null;
            }
            previewEl = document.getElementById('previewModeloDocumento');
            if (previewEl && (previewEl.innerText || '').trim().length > 200) break;
            await sleep(150); // Reduzido de 200ms para 150ms
        }

        const texto = (previewEl?.innerText || '').trim();
        const html = (previewEl?.innerHTML || '').trim();
        return texto.length > 200 ? { texto, html } : null;
    }

    // Fecha o modal/viewer atual (se houver)
    function fecharViewer() {
        // Tenta fechar o modal de preview
        const closeBtns = document.querySelectorAll(
            'button[aria-label="Fechar"], .mat-dialog-close, mat-dialog-container button.close, .cdk-overlay-backdrop'
        );
        closeBtns.forEach(b => { try { b.click(); } catch (_) { } });
    }

    // ==========================================
    // EXTRAÇÃO DE DADOS DA SENTENÇA
    // ==========================================
    function extrairDadosSentenca(texto) {
        const result = {
            custas: null,
            hsusp: false,
            trteng: false,
            trtmed: false,
            responsabilidade: null,   // 'subsidiaria' | 'solidaria' | null
            honorariosPericiais: []    // { valor, trt }
        };

        // Custas: padrão amplo com flexibilidade para "mínimo", "máximo", "total", etc.
        // Aceita: "no importe [mínimo/máximo/total] de R$ X, calculadas sobre"
        // ou "Custas, pela Reclamada, no importe de R$ 300,00"
        // ou "Custas de R$ 200,00"
        const custasMatch = texto.match(
            /no\s+importe\s+(?:m[ií]nim[oa]\s+|m[áa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+),?\s*calculadas\s+sobre/i
        ) || texto.match(
            /[Cc]ustas[^,]*,\s*(?:pela\s+)?[Rr]eclamad[ao][^,]*,\s*no\s+importe\s+(?:m[ií]nim[oa]\s+|m[áa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+)/i
        ) || texto.match(
            /[Cc]ustas[^,]*de\s+R\$\s*([\d.,]+)/i
        );
        if (custasMatch) {
            // Remove vírgulas/pontos extras no final
            result.custas = custasMatch[1].replace(/[.,]+$/, '');
        }

        // Condição suspensiva
        result.hsusp = /obriga[cç][aã]o\s+ficar[aá]\s+sob\s+condi[cç][aã]o\s+suspensiva/i.test(texto);

        // Perícia TRT engenharia
        result.trteng = /honor[aá]rios\s+periciais\s+t[eé]cnicos.*pagos\s+pelo\s+Tribunal/i.test(texto)
            || /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+t[eé]cnicos/i.test(texto);

        // Perícia TRT médica
        result.trtmed = /honor[aá]rios\s+periciais\s+m[eé]dicos.*pagos\s+pelo\s+Tribunal/i.test(texto)
            || /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+m[eé]dicos/i.test(texto);

        // Responsabilidade
        if (/condenar\s+(de\s+forma\s+)?subsidi[aá]ri/i.test(texto)) {
            result.responsabilidade = 'subsidiaria';
        } else if (/condenar\s+(de\s+forma\s+)?solid[aá]ri/i.test(texto)) {
            result.responsabilidade = 'solidaria';
        }

        // Honorários periciais: buscar todos os trechos com valor + se é TRT
        // Padrão: "honorários periciais ... em R$ 800,00 ... pagos pelo Tribunal"
        const regexHon = /honor[aá]rios\s+periciais[^.]*?R\$\s*([\d.,]+)[^.]*?\./gi;
        let match;
        while ((match = regexHon.exec(texto)) !== null) {
            const trecho = match[0];
            const valor = match[1];
            const trt = /pagos?\s+pelo\s+Tribunal/i.test(trecho)
                || /Tribunal\s+Regional/i.test(trecho)
                || /TRT/i.test(trecho);
            result.honorariosPericiais.push({ valor, trt });
        }

        return result;
    }

    // ==========================================
    // CRUZAMENTO AJ-JT × PERITOS
    // ==========================================
    async function buscarAjJtPeritos(honAjJtItems, peritosConhecimento) {
        const resultados = []; // { nome, trt: true, idAjJt }

        // Set de peritos já encontrados — evita abrir mais docs desnecessários
        const peritosEncontrados = new Set();

        for (const ajjt of honAjJtItems) {
            // Se todos os peritos já foram encontrados, para
            if (peritosEncontrados.size >= peritosConhecimento.length) break;

            // Abre documento via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(ajjt.href)) {
                console.warn('[prep] Falha ao abrir AJ-JT:', ajjt.href);
                continue;
            }
            await sleep(600);

            // Lê HTML original
            const resHtml = await lerHtmlOriginal(5000);
            fecharViewer();
            await sleep(300);

            if (!resHtml || !resHtml.texto) continue;

            const textoNorm = normalizeText(resHtml.texto);

            // Procura cada perito de conhecimento no texto
            for (const perito of peritosConhecimento) {
                if (peritosEncontrados.has(perito)) continue;

                const peritoNorm = normalizeText(perito);
                // Match parcial: primeiro nome + último nome
                const partes = peritoNorm.split(/\s+/).filter(Boolean);
                const primeiroNome = partes[0] || '';
                const ultimoNome = partes.length > 1 ? partes[partes.length - 1] : '';

                const found = textoNorm.includes(peritoNorm)
                    || (primeiroNome && ultimoNome && textoNorm.includes(primeiroNome) && textoNorm.includes(ultimoNome));

                if (found) {
                    // Usar ID já extraído da timeline
                    const idAjJt = ajjt.id || ajjt.texto;

                    resultados.push({ nome: perito, trt: true, idAjJt });
                    peritosEncontrados.add(perito);
                }
            }
        }

        return resultados;
    }

    // ==========================================
    // NOTIFICAÇÕES EDITAL
    // ==========================================
    async function buscarPartesEdital(editaisItems, passivo) {
        // Regra maior: se há apenas uma reclamada e há edital, é ela.
        if (passivo.length === 1) {
            return [passivo[0].nome];
        }

        const intimadas = new Set();
        const reclamadas = passivo.map(p => ({ nome: p.nome, nomNorm: normalizeText(p.nome) }));

        for (const edital of editaisItems) {
            if (intimadas.size >= passivo.length) break;

            // Abre edital via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(edital.href)) {
                console.warn('[prep] Falha ao abrir edital:', edital.href);
                continue;
            }
            await sleep(600);

            const resHtml = await lerHtmlOriginal(6000, signal, signal);
            fecharViewer();
            await sleep(300);

            if (!resHtml || !resHtml.html) continue;

            const html = resHtml.html;

            const matchComeco = html.match(/<strong[^>]*>\s*EDITAL\s+D.*?<\/strong>/i);
            const matchFim = html.match(/<strong[^>]*>\s*\(http:\/\/pje\.trtsp\.jus\.br\/documentos\)\s*<\/strong>/i);

            let textoAlvo = '';

            if (matchComeco && matchFim && matchFim.index > matchComeco.index) {
                const blocoHtml = html.substring(matchComeco.index, matchFim.index + matchFim[0].length);
                const div = document.createElement('div');
                div.innerHTML = blocoHtml;
                textoAlvo = normalizeText(div.innerText || div.textContent || '');
            } else if (matchComeco) {
                const blocoHtml = html.substring(matchComeco.index, matchComeco.index + 1000);
                const div = document.createElement('div');
                div.innerHTML = blocoHtml;
                textoAlvo = normalizeText(div.innerText || div.textContent || '');
            } else {
                textoAlvo = normalizeText(resHtml.texto);
            }

            for (const r of reclamadas) {
                if (intimadas.has(r.nome)) continue;
                if (textoAlvo.includes(r.nomNorm)) {
                    intimadas.add(r.nome);
                }
            }
        }
        return Array.from(intimadas);
    }

    // ==========================================
    // ORQUESTRADOR PRINCIPAL
    // ==========================================
    async function executarPrep(partesData, peritosConhecimento) {
        // FLAG ANTI-EXECUÇÃO-DUPLA: Previne loops de polling acumulando timers
        if (window.hcalcPrepRunning) {
            console.log('[prep.js] ⚠️ Prep já em execução, ignorando chamada duplicada');
            return;
        }

        // Abortar prep anterior se existir
        if (window.hcalcState.abortController) {
            dbg('[prep] Abortando execução anterior antes de iniciar nova');
            window.hcalcState.abortController.abort();
        }

        // Criar novo AbortController para esta execução
        window.hcalcState.abortController = new AbortController();
        const signal = window.hcalcState.abortController.signal;

        window.hcalcPrepRunning = true;

        try {
            console.log('[prep.js] Iniciando preparação pré-overlay...');
            const partesSafe = partesData && typeof partesData === 'object' ? partesData : {};

        // Resultado padrão
        const prepResult = {
            sentenca: {
                data: null,
                custas: null,
                hsusp: false,
                responsabilidade: null,
                honorariosPericiais: []
            },
            pericia: {
                trteng: false,
                trtmed: false,
                peritosComAjJt: []
            },
            acordaos: [],
            depositos: [],
            editais: [],
            partesIntimadasEdital: []
        };

        // ── ETAPA 1: Varrer timeline (síncrona) ──
        const timeline = varrerTimeline();
        console.log('[prep.js] Timeline varrida:', {
            sentencas: timeline.sentencas.length,
            acordaos: timeline.acordaos.length,
            editais: timeline.editais.length,
            recursosPassivo: timeline.recursosPassivo.length,
            honAjJt: timeline.honAjJt.length
        });

        // Mapear acórdãos e editais para resultado
        prepResult.acordaos = timeline.acordaos.map(a => ({ data: a.data, href: a.href, id: a.id }));
        prepResult.editais = timeline.editais.map(e => ({ data: e.data, href: e.href }));

        // Depósitos recursais = recursos passivo (só se tem acórdão)
        if (timeline.acordaos.length > 0) {
            prepResult.depositos = timeline.recursosPassivo.map(r => ({
                tipo: r.tipoRec,
                texto: r.texto,
                href: r.href,
                data: r.data,
                depositante: r.depositante || ''
            }));
        }

        // ── ETAPA 2: AJ-JT — só se tem perito de conhecimento ──
        // ORDEM INVERTIDA: AJ-JT antes de sentença para manter sentença selecionada
        const peritosConh = Array.isArray(peritosConhecimento) ? peritosConhecimento.filter(Boolean) : [];

        if (peritosConh.length > 0 && timeline.honAjJt.length > 0) {
            console.log('[prep.js] Buscando AJ-JT para peritos:', peritosConh);
            prepResult.pericia.peritosComAjJt = await buscarAjJtPeritos(timeline.honAjJt, peritosConh);
            console.log('[prep.js] AJ-JT encontrados:', prepResult.pericia.peritosComAjJt);
        } else if (peritosConh.length > 0) {
            console.log('[prep.js] Peritos de conhecimento detectados mas nenhum AJ-JT na timeline.');
        }

        // ── ETAPA 3: Sentença — abrir e extrair tudo ──
        // MOVIDO PARA DEPOIS DE AJ-JT para ficar selecionada por último
        const sentencaAlvo = timeline.sentencas.length > 0
            ? timeline.sentencas[timeline.sentencas.length - 1]  // mais antiga (última no array)
            : null;

        if (sentencaAlvo) {
            prepResult.sentenca.data = sentencaAlvo.data;

            // Abrir documento via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(sentencaAlvo.href)) {
                console.warn('[prep] Falha ao abrir sentença:', sentencaAlvo.href);
            } else {
                await sleep(600);

                // Ler HTML original
                const resSent = await lerHtmlOriginal(6000, signal);
                fecharViewer();
                await sleep(300);

                if (resSent && resSent.texto) {
                    const textoSentenca = resSent.texto;
                    console.log('[prep.js] Sentença lida:', textoSentenca.length, 'chars');

                    const dados = extrairDadosSentenca(textoSentenca);
                    prepResult.sentenca.custas = dados.custas;
                    prepResult.sentenca.hsusp = dados.hsusp;
                    prepResult.sentenca.responsabilidade = dados.responsabilidade;
                    prepResult.sentenca.honorariosPericiais = dados.honorariosPericiais;
                    prepResult.pericia.trteng = dados.trteng;
                    prepResult.pericia.trtmed = dados.trtmed;
                } else {
                    console.warn('[prep.js] Falha ao ler sentença via HTML original.');
                }
            }
        } else {
            console.warn('[prep.js] Nenhuma sentença encontrada na timeline.');
        }

        // ── ETAPA 4: EDITAL — extrair partes intimadas ──
        const passivoArray = Array.isArray(partesSafe.passivo) ? partesSafe.passivo : [];
        if (timeline.editais.length > 0 && passivoArray.length > 0) {
            console.log('[prep.js] Buscando partes intimadas nos editais...');
            prepResult.partesIntimadasEdital = await buscarPartesEdital(timeline.editais, passivoArray);
            console.log('[prep.js] Partes intimadas por edital:', prepResult.partesIntimadasEdital);
        }

        console.log('[prep.js] Preparação concluída:', prepResult);

        // Disponibilizar globalmente
        window.hcalcPrepResult = prepResult;

        // Liberar flag de execução
        window.hcalcPrepRunning = false;

        return prepResult;

        } catch (error) {
            console.error('[prep.js] Erro durante preparação:', error);
            // Garantir que flag seja liberada mesmo em caso de erro
            window.hcalcPrepRunning = false;
            throw error;
        }
    }

    // Expor prep no escopo global para integração/depuração.
    const prepGlobalObj = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    prepGlobalObj.executarPrep = executarPrep;
    if (prepGlobalObj !== window) {
        window.executarPrep = executarPrep;
    }

    // Fim prep (agora global no escopo do arquivo)


    function initializeOverlay() {
        if (window.__hcalcOverlayInitialized) {
            dbg('initializeOverlay ignorado: overlay ja inicializado.');
            return;
        }
        dbg('initializeOverlay iniciado.');
        window.__hcalcOverlayInitialized = true;

        // ==========================================
        // 1. ESTILOS DO OVERLAY E BOTÃO (v1.9 - UI Compacta)
        // ==========================================
        const styles = `
        #btn-abrir-homologacao {
            position: fixed; bottom: 20px; right: 20px; z-index: 99999;
            background: #00509e; color: white; border: none; border-radius: 6px;
            padding: 10px 18px; font-size: 13px; font-weight: bold; cursor: pointer;
            box-shadow: 0 3px 5px rgba(0,0,0,0.3);
        }
        #btn-abrir-homologacao:hover { background: #003d7a; }

        #homologacao-overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: transparent; z-index: 100000; justify-content: flex-end; align-items: flex-start;
            font-family: Arial, sans-serif; pointer-events: none;
        }

        #homologacao-modal {
            background: #fff; width: 630px; max-width: 630px; height: 100vh; max-height: 100vh; overflow-y: auto;
            border-radius: 0; box-shadow: -4px 0 20px rgba(0,0,0,0.25); padding: 10px; margin: 0;
            display: flex; flex-direction: column; gap: 5px; color: #333; pointer-events: all;
        }

        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-bottom: 3px; }
        .modal-header h2 { margin: 0; color: #00509e; font-size: 15px; }
        .btn-close { background: #cc0000; color: white; border: none; padding: 3px 10px; cursor: pointer; border-radius: 3px; font-weight: bold; font-size: 11px; }

        fieldset { border: 1px solid #ddd; border-radius: 4px; padding: 6px; margin-bottom: 4px; background: #fff; }
        legend { background: #00509e; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: bold; }

        .row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; align-items: center; }
        .col { display: flex; flex-direction: column; flex: 1; min-width: 140px; }

        label { font-size: 11px; font-weight: bold; margin-bottom: 3px; color: #555; }
        input[type="text"], input[type="date"] { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }
        textarea { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 12px; resize: vertical; font-family: Arial, sans-serif; }
        select { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }

        .hidden { display: none !important; }
        /* Destaque para o campo atual da coleta */
        .highlight { border: 2px solid #ff9800 !important; background: #fffde7 !important; box-shadow: 0 0 6px rgba(255,152,0,0.4); }

        /* Badges para partes detectadas (v1.9) */
        .partes-badges { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
        }
        .badge-blue { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        .badge-gray { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
        .badge-green { background: #d1fae5; color: #047857; border: 1px solid #a7f3d0; }

        .btn-action { background: #28a745; color: white; border: none; padding: 8px 12px; border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn-action:hover { background: #218838; }
        .btn-gravar { background: #00509e; width: 100%; padding: 12px; font-size: 16px; margin-top: 10px; }

        /* Compactar espaçamento interno para caber na tela */
        #homologacao-modal fieldset { padding: 8px 10px; margin-bottom: 6px; }
        #homologacao-modal .row { margin-bottom: 6px; gap: 8px; }
        #homologacao-modal input[type=text],
        #homologacao-modal input[type=date],
        #homologacao-modal select,
        #homologacao-modal textarea { padding: 5px 7px; font-size: 12px; }
        #homologacao-modal label { font-size: 11px; margin-bottom: 2px; }
        #homologacao-modal legend { font-size: 12px; padding: 3px 8px; }
        #homologacao-modal .btn-gravar { padding: 10px; font-size: 15px; margin-top: 10px; }
    `;
        if (!document.getElementById('hcalc-overlay-style')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'hcalc-overlay-style';
            styleSheet.innerText = styles;
            document.head.appendChild(styleSheet);
        }

        // ==========================================
        // 2. HTML DO OVERLAY (ESTRUTURA)
        // ==========================================
        const htmlModal = `
    <button id="btn-abrir-homologacao">Gerar Homologação</button>
    <div id="homologacao-overlay">
        <div id="homologacao-modal">
            <div class="modal-header">
                <h2>Assistente de Homologação</h2>
                <button class="btn-close" id="btn-fechar">X Fechar</button>
            </div>



            <!-- SEÇÃO 1 e 2: BASE E PARTE -->
            <fieldset>
                <legend>Cálculo Base e Autoria</legend>
                <div class="row">
                    <div class="col">
                        <label>Origem do Cálculo</label>
                        <select id="calc-origem">
                            <option value="pjecalc" selected>PJeCalc</option>
                            <option value="outros">Outros</option>
                        </select>
                    </div>
                    <div class="col" id="col-pjc">
                        <label><input type="checkbox" id="calc-pjc" checked> Acompanha arquivo .PJC?</label>
                    </div>
                    <div class="col">
                        <label>Autor do Cálculo</label>
                        <select id="calc-autor">
                            <option value="autor" selected>Reclamante (Autor)</option>
                            <option value="reclamada">Reclamada</option>
                            <option value="perito">Perito</option>
                        </select>
                    </div>
                    <div class="col hidden" id="col-esclarecimentos">
                        <label><input type="checkbox" id="calc-esclarecimentos" checked> Esclarecimentos do Perito?</label>
                        <input type="text" id="calc-peca-perito" placeholder="Id da Peça">
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 3: ATUALIZAÇÃO -->
            <fieldset>
                <legend>Atualização</legend>
                <div class="row">
                    <div class="col">
                        <label>Índice de Atualização</label>
                        <select id="calc-indice">
                            <option value="adc58" selected>SELIC / IPCA-E (ADC 58)</option>
                            <option value="tr">TR / IPCA-E (Casos Antigos)</option>
                        </select>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 5: DADOS COPIADOS DA PLANILHA (ÚNICO FIELDSET) -->
            <fieldset>
                <legend>Dados Copiados da Planilha</legend>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">1) Identificação, Datas, Principal e FGTS</label>
                    <div class="row">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Id da Planilha</label>
                            <input type="text" id="val-id" class="coleta-input" placeholder="Id #XXXX">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Data da Atualização</label>
                            <input type="text" id="val-data" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label>Crédito Principal (ou Total)</label>
                            <input type="text" id="val-credito" class="coleta-input" placeholder="R$ Crédito Principal">
                        </div>
                        <div class="col hidden" id="col-fgts-val" style="flex: 0 0 140px;">
                            <label>FGTS Separado</label>
                            <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS">
                        </div>
                    </div>
                    <div class="row">
                        <div class="col">
                            <label><input type="checkbox" id="calc-fgts"> FGTS apurado separado?</label>
                        </div>
                    </div>
                    <div class="row hidden" id="col-juros-val">
                        <div class="col">
                            <label>Juros</label>
                            <input type="text" id="val-juros" placeholder="R$ Juros">
                        </div>
                        <div class="col">
                            <label>Data de Ingresso</label>
                            <input type="date" id="data-ingresso">
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">2) INSS (Autor e Reclamada) e IR</label>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col">
                            <label>INSS - Desconto (Reclamante)</label>
                            <input type="text" id="val-inss-rec" class="coleta-input" placeholder="R$ INSS Reclamante (Desconto)">
                        </div>
                        <div class="col">
                            <label>INSS - Total da Empresa (Reclamada)</label>
                            <input type="text" id="val-inss-total" class="coleta-input" placeholder="R$ INSS Total / Reclamada">
                        </div>
                    </div>
                    <div class="row" style="margin-top: 5px;">
                        <div class="col">
                            <label><input type="checkbox" id="ignorar-inss"> Não há INSS</label>
                            <small style="color: #666; display: block;">*INSS Reclamada = Subtração automática se PJeCalc marcado.</small>
                        </div>
                        <div class="col">
                            <label>Imposto de Renda</label>
                            <select id="irpf-tipo" style="margin-bottom: 5px; width: 100%;">
                                <option value="isento" selected>Não há</option>
                                <option value="informar">Informar Valores</option>
                            </select>
                            <div id="irpf-campos" class="hidden" style="display:flex; gap: 5px;">
                                <input type="text" id="val-irpf-base" placeholder="Base (R$)" style="flex:1;">
                                <input type="text" id="val-irpf-meses" placeholder="Meses" style="flex:1;">
                            </div>
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">3) Honorários Advocatícios</label>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" style="flex: 0 0 220px;">
                            <label>Honorários Adv Autor</label>
                            <input type="text" id="val-hon-autor" class="coleta-input highlight" placeholder="R$ Honorários Autor">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label><input type="checkbox" id="chk-hon-reu" checked style="margin-right: 5px;">Não há Honorários Adv Réu</label>
                            <div id="hon-reu-campos" class="hidden" style="margin-top: 6px;">
                                <input type="text" id="val-hon-reu" class="coleta-input" placeholder="R$ Honorários Réu" style="margin-bottom: 4px;">
                                <div style="display: flex; gap: 8px; flex-direction: column;">
                                    <label style="font-size: 11px;"><input type="radio" name="rad-hon-reu" value="suspensiva" checked> Condição Suspensiva</label>
                                    <label style="font-size: 11px;"><input type="radio" name="rad-hon-reu" value="percentual"> Percentual: <input type="text" id="val-hon-reu-perc" value="5%" style="width: 50px; margin-left: 5px;"></label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="row">
                        <label style="font-size: 11px;"><input type="checkbox" id="ignorar-hon-autor"> Não há honorários autor</label>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">4) Custas</label>
                    <div class="row" style="margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Valor</label>
                            <input type="text" id="val-custas" class="coleta-input" placeholder="R$ Custas">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Status</label>
                            <select id="custas-status">
                                <option value="devidas" selected>Devidas</option>
                                <option value="pagas">Já Pagas</option>
                            </select>
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Origem</label>
                            <select id="custas-origem">
                                <option value="sentenca" selected>Sentença</option>
                                <option value="acordao">Acórdão</option>
                            </select>
                        </div>
                    </div>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" id="custas-data-col" style="flex: 1;">
                            <label>Data Custas <small style="color: #666;">(vazio = mesma planilha)</small></label>
                            <input type="text" id="custas-data-origem" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col hidden" id="custas-acordao-col" style="flex: 1;">
                            <label>Acórdão</label>
                            <select id="custas-acordao-select">
                                <option value="">Selecione o acórdão</option>
                            </select>
                        </div>
                    </div>
                    <div id="link-acordao-container" style="margin-top: 4px;"></div>
                </div>
            </fieldset>

            <!-- SEÇÃO 6: RESPONSABILIDADE -->
            <fieldset>
                <legend>Responsabilidade</legend>
                <div class="row">
                    <select id="resp-tipo">
                        <option value="unica">Reclamada Única</option>
                        <option value="solidarias">Devedoras Solidárias</option>
                        <option value="subsidiarias" selected>Devedoras Subsidiárias</option>
                    </select>
                </div>
                <div id="resp-sub-opcoes" class="row">
                    <label><input type="checkbox" id="resp-integral" checked> Responde pelo período total</label>
                    <label style="margin-left: 15px;"><input type="checkbox" id="resp-diversos"> Períodos Diversos (Gera estrutura para preencher)</label>
                </div>
            </fieldset>

            <!-- SEÇÃO 6.1: PERÍODOS DIVERSOS (Dinâmico) -->
            <fieldset id="resp-diversos-fieldset" class="hidden">
                <legend>Períodos Diversos - Cálculos Separados por Reclamada</legend>
                <div class="row" style="margin-bottom: 15px;">
                    <div class="col">
                        <label style="font-weight: bold;">Devedora Principal</label>
                        <select id="resp-devedora-principal" style="width: 100%; padding: 8px;">
                            <option value="">Selecione a devedora principal...</option>
                        </select>
                        <small style="color: #666; display: block; margin-top: 5px;">*Padrão: primeira reclamada</small>
                    </div>
                </div>
                <div class="row" style="margin-bottom: 15px; font-size: 13px; color: #555;">
                    <label>Preencha período, planilha e escolha se é período total para cada reclamada subsidiária:</label>
                </div>
                <div id="resp-diversos-container"></div>
                <button type="button" class="btn-action" id="btn-adicionar-periodo" style="margin-top: 10px;">+ Adicionar Reclamada Subsidiária</button>
            </fieldset>

            <!-- DETECÇÃO INICIAL (movido para depois de Custas) -->
            <fieldset>
                <legend>Detectados</legend>
                <div class="row">
                    <div class="col">
                        <label>Reclamadas</label>
                        <div id="det-reclamadas" class="partes-badges" style="min-height: 24px; padding: 3px; border: 1px solid #ddd; border-radius: 3px; background: #fafafa;"></div>
                    </div>
                    <div class="col">
                        <label>Peritos</label>
                        <div id="det-peritos" class="partes-badges" style="min-height: 24px; padding: 3px; border: 1px solid #ddd; border-radius: 3px; background: #fafafa;"></div>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 7B: HONORÁRIOS PERICIAIS (auto-esconde se não detectar perito) -->
            <fieldset id="fieldset-pericia-conh" class="hidden">
                <legend>Honorários Periciais <span id="link-sentenca-container"></span></legend>
                <div class="row">
                    <div class="col">
                        <label><input type="checkbox" id="chk-perito-conh"> Honorários Periciais (Conhecimento)</label>
                        <div id="perito-conh-campos" class="hidden" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-nome" placeholder="Nome do Perito">
                            <select id="perito-tipo-pag">
                                <option value="reclamada" selected>Pago pela Reclamada (Valor)</option>
                                <option value="trt">Pago pelo TRT (Autor Sucumbente)</option>
                            </select>
                            <input type="text" id="val-perito-valor" placeholder="R$ Valor ou ID TRT">
                            <input type="text" id="val-perito-data" placeholder="Data da Sentença">
                        </div>
                    </div>
                </div>
                <div class="row hidden" id="row-perito-contabil">
                    <div class="col">
                        <label>Honorários Periciais (Contábil - Rogério)</label>
                        <div id="perito-contabil-campos" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-contabil-valor" placeholder="Valor dos honorários contábeis">
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 9: INTIMAÇÕES -->
            <fieldset id="fieldset-intimacoes">
                <legend>Intimações</legend>
                <div id="lista-intimacoes-container">
                    <small style="color:#666; font-style:italic;">Aguardando leitura das partes...</small>
                </div>
                <div id="links-editais-container" class="hidden" style="margin-top: 10px; border-top: 1px dashed #ccc; padding-top: 10px;">
                    <label style="font-weight:bold; font-size:12px; color:#5b21b6;">Editais Detectados na Timeline:</label>
                    <div id="links-editais-lista"></div>
                </div>
            </fieldset>

            <!-- Custas já foram movidas para o card 4 acima -->

            <!-- SEÇÃO 8: DEPÓSITO RECURSAL -->
            <fieldset id="fieldset-deposito">
                <legend>Depósito Recursal</legend>
                <div class="row">
                    <label><input type="checkbox" id="chk-deposito"> Há Depósito Recursal?</label>
                    <label style="margin-left: 20px;"><input type="checkbox" id="chk-pag-antecipado"> Pagamento Antecipado</label>
                </div>
                <div id="pag-antecipado-campos" class="hidden">
                    <div class="row">
                        <input type="text" id="pag-antecipado-id" placeholder="ID do Depósito">
                    </div>
                    <div class="row">
                        <label><input type="radio" name="lib-tipo" value="nenhum" checked> Padrão (extinção)</label>
                        <label style="margin-left: 15px;"><input type="radio" name="lib-tipo" value="remanescente"> Com Remanescente</label>
                        <label style="margin-left: 15px;"><input type="radio" name="lib-tipo" value="devolucao"> Com Devolução</label>
                    </div>
                    <div id="lib-remanescente-campos" class="hidden">
                        <div class="row">
                            <input type="text" id="lib-rem-valor" placeholder="Valor Remanescente (ex: 1.234,56)">
                            <input type="text" id="lib-rem-titulo" placeholder="Título (ex: custas processuais)">
                        </div>
                    </div>
                    <div id="lib-devolucao-campos" class="hidden">
                        <div class="row">
                            <input type="text" id="lib-dev-valor" placeholder="Valor Devolução (ex: 1.234,56)">
                        </div>
                    </div>
                </div>
                <div id="deposito-campos" class="hidden">
                    <div class="row">
                        <select id="dep-tipo">
                            <option value="bb" selected>Banco do Brasil</option>
                            <option value="sif">CEF (SIF)</option>
                            <option value="garantia">Seguro Garantia</option>
                        </select>
                        <input type="text" id="dep-depositante" placeholder="Depositante (Reclamada)">
                        <input type="text" id="dep-id" placeholder="ID da Guia">
                    </div>
                    <div class="row">
                        <label><input type="checkbox" id="dep-principal" checked> Depositado pela Devedora Principal?</label>
                    </div>
                    <div class="row" id="dep-liberacao-row">
                        <label><input type="radio" name="rad-dep-lib" value="reclamante" checked> Liberação simples (Reclamante)</label>
                        <label style="margin-left: 10px;"><input type="radio" name="rad-dep-lib" value="detalhada"> Liberação detalhada (Crédito, INSS, Hon.)</label>
                    </div>
                </div>
            </fieldset>

            <button class="btn-action btn-gravar" id="btn-gravar">GRAVAR DECISÃO (Copiar p/ PJe)</button>
        </div>
    </div>
    `;
        // Check robusto: Remover overlay antigo se existir (previne duplicação)
        const existingOverlay = document.getElementById('homologacao-overlay');
        const existingBtn = document.getElementById('btn-abrir-homologacao');

        if (existingOverlay || existingBtn) {
            dbg('Overlay já existe, removendo versão antiga antes de recriar');
            existingOverlay?.remove();
            existingBtn?.remove();
        }

        // Inserir HTML limpo
        document.body.insertAdjacentHTML('beforeend', htmlModal);
        dbg('Overlay HTML inserido no DOM.');

        if (!document.getElementById('btn-abrir-homologacao') || !document.getElementById('homologacao-overlay')) {
            err('Falha apos insercao: elementos principais do overlay nao encontrados.');
            return;
        }

        // ==========================================
        // 3. LÓGICA DE INTERFACE E EVENTOS (TOGGLES)
        // ==========================================
        const $ = (id) => document.getElementById(id);
        dbg('Binding de eventos iniciado.');
        $('btn-abrir-homologacao').onclick = async () => {
            dbg('Clique em Gerar Homologacao detectado.');
            try {
                // Executar prep.js: varredura + extração da sentença + AJ-JT
                const peritosConh = window.hcalcPeritosConhecimentoDetectados || [];
                const partesData = window.hcalcPartesData || {};
                const prep = await executarPrep(partesData, peritosConh);

            // Retrocompat: manter window.hcalcTimelineData para construirSecaoIntimacoes
            window.hcalcTimelineData = {
                sentenca: prep.sentenca.data ? { data: prep.sentenca.data, href: null } : null,
                acordaos: prep.acordaos,
                editais: prep.editais
            };

            // Link sentença
            const linkSentencaContainer = $('link-sentenca-container');
            if (linkSentencaContainer) {
                linkSentencaContainer.innerHTML = '';
                if (prep.sentenca.data) {
                    const info = [];
                    if (prep.sentenca.custas) info.push(`Custas: R$${prep.sentenca.custas}`);
                    if (prep.sentenca.responsabilidade) info.push(`Resp: ${prep.sentenca.responsabilidade}`);

                    // Honorários periciais: prioriza AJ-JT, só mostra sentença se não tiver AJ-JT
                    if (prep.pericia.peritosComAjJt.length > 0) {
                        info.push(`Hon.Periciais: ${prep.pericia.peritosComAjJt.length} AJ-JT detectado(s)`);
                    } else if (prep.sentenca.honorariosPericiais.length > 0) {
                        info.push(`Hon.Periciais: ${prep.sentenca.honorariosPericiais.map(h => 'R$' + h.valor + (h.trt ? ' (TRT)' : '')).join(', ')}`);
                    }

                    linkSentencaContainer.innerHTML = `<span style="font-size:12px; color:#16a34a;">✔ Sentença: ${prep.sentenca.data}${info.length ? ' | ' + info.join(' | ') : ''}</span>`;
                }
            }

            // Preencher custas automaticamente se extraídas
            if (prep.sentenca.custas && $('val-custas')) {
                $('val-custas').value = prep.sentenca.custas;
            }

            // Depósito recursal: visível se tem acórdãos
            const fieldsetDeposito = $('fieldset-deposito');
            const linkAcordaoContainer = $('link-acordao-container');
            if (linkAcordaoContainer) linkAcordaoContainer.innerHTML = '';

            // Povoar select de acórdãos se existirem
            const custasAcordaoSelect = $('custas-acordao-select');
            if (custasAcordaoSelect && prep.acordaos.length > 0) {
                custasAcordaoSelect.innerHTML = '<option value="">Selecione o acórdão</option>';
                prep.acordaos.forEach((acordao, i) => {
                    const opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = `Acórdão ${i + 1}${acordao.data ? ' - ' + acordao.data : ''}`;
                    opt.dataset.data = acordao.data || '';
                    opt.dataset.id = acordao.id || '';
                    custasAcordaoSelect.appendChild(opt);
                });
            }

            if (prep.acordaos.length === 0) {
                if (fieldsetDeposito) fieldsetDeposito.classList.add('hidden');
            } else {
                if (fieldsetDeposito) fieldsetDeposito.classList.remove('hidden');
                if (linkAcordaoContainer) {
                    prep.acordaos.forEach((acordao, i) => {
                        if (acordao.href) {
                            const lbl = prep.acordaos.length > 1 ? `Acórdão ${i + 1}` : `Acórdão`;
                            const a = document.createElement('a');
                            a.href = acordao.href;
                            a.target = "_blank";
                            a.innerHTML = `<i class="fas fa-external-link-alt"></i> ${lbl}`;
                            a.style.cssText = "display:block; color:#00509e; font-size:12px; margin-top:5px; text-decoration:none;";
                            linkAcordaoContainer.appendChild(a);
                        }
                    });
                    // RO/RR com depósito recursal
                    if (prep.depositos.length > 0) {
                        const depDiv = document.createElement('div');
                        depDiv.style.cssText = 'margin-top:8px; padding:6px; background:#fffde7; border:1px solid #fbbf24; border-radius:4px;';
                        depDiv.innerHTML = `<strong style="font-size:11px; color:#92400e;">📎 Depósitos Recursais (${prep.depositos.length}):</strong>`;
                        prep.depositos.forEach(dep => {
                            if (dep.href) {
                                const a = document.createElement('a');
                                a.href = dep.href;
                                a.target = '_blank';
                                a.innerHTML = `<i class="fas fa-external-link-alt"></i> ${dep.tipo} - ${dep.data || 'sem data'}`;
                                a.style.cssText = 'display:block; color:#92400e; font-size:11px; margin-top:3px; text-decoration:none;';
                                depDiv.appendChild(a);
                            }
                        });
                        linkAcordaoContainer.appendChild(depDiv);
                    }
                }
            }

            // Editais
            const editaisContainer = $('links-editais-container');
            const editaisLista = $('links-editais-lista');
            if (editaisContainer && editaisLista) {
                editaisLista.innerHTML = '';
                if (prep.editais.length > 0) {
                    editaisContainer.classList.remove('hidden');
                    prep.editais.forEach((edital, i) => {
                        if (edital.href) {
                            const btn = document.createElement('a');
                            btn.href = edital.href;
                            btn.target = "_blank";
                            btn.innerHTML = `<i class="fas fa-external-link-alt"></i> Edital ${i + 1}`;
                            btn.style.cssText = "display:inline-block; margin-right:10px; color:#00509e; font-size:12px; text-decoration:none;";
                            editaisLista.appendChild(btn);
                        }
                    });
                } else {
                    editaisContainer.classList.add('hidden');
                }
            }

            // ==========================================
            // REGRAS AUTO-PREENCHIMENTO (prep sobrepõe defaults)
            // ==========================================

            // REGRA 1: Depósito recursal — depositante da RO/RR polo passivo
            if (prep.depositos.length > 0) {
                const chkDep = $('chk-deposito');
                const depCampos = $('deposito-campos');
                const depDepositante = $('dep-depositante');
                if (chkDep) { chkDep.checked = true; }
                if (depCampos) { depCampos.classList.remove('hidden'); }
                // Usar o nome do primeiro depositante encontrado
                if (depDepositante && prep.depositos[0].depositante) {
                    depDepositante.value = prep.depositos[0].depositante;
                }
            }

            // REGRA 2: Perito conhecimento + TRT / AJ-JT match
            const peritoTipoEl = $('perito-tipo-pag');
            const peritoValorEl = $('val-perito-valor');
            const peritoDataEl = $('val-perito-data');
            if (prep.pericia.peritosComAjJt.length > 0) {
                // Perito casou com AJ-JT — pago pelo TRT
                const match = prep.pericia.peritosComAjJt[0];
                if (peritoTipoEl) peritoTipoEl.value = 'trt';
                if (peritoValorEl) peritoValorEl.value = match.idAjJt || '';
            } else if (prep.sentenca.honorariosPericiais.length > 0) {
                // Honorários periciais na sentença
                const hon = prep.sentenca.honorariosPericiais[0];
                if (hon.trt && peritoTipoEl) {
                    peritoTipoEl.value = 'trt';
                }
                // Sempre preencher valor se detectado
                if (peritoValorEl && !peritoValorEl.value) {
                    peritoValorEl.value = 'R$' + hon.valor;
                }
            }
            // Data da sentença no campo de data do perito
            if (prep.sentenca.data && peritoDataEl && !peritoDataEl.value) {
                peritoDataEl.value = prep.sentenca.data;
            }

            // REGRA 3 e 4: Responsabilidade (subsidiária / solidária)
            const respTipoEl = $('resp-tipo');
            const respSubOpcoes = $('resp-sub-opcoes');
            const passivo = window.hcalcPartesData?.passivo || [];
            if (prep.sentenca.responsabilidade && respTipoEl) {
                if (prep.sentenca.responsabilidade === 'subsidiaria') {
                    respTipoEl.value = 'subsidiarias';
                    if (respSubOpcoes) respSubOpcoes.classList.remove('hidden');
                } else if (prep.sentenca.responsabilidade === 'solidaria') {
                    respTipoEl.value = 'solidarias';
                    if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                }
            } else if (passivo.length <= 1 && respTipoEl) {
                respTipoEl.value = 'unica';
                if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
            }

            // REGRA 5: Custas
            // Sempre padrão = sentença (usuário pode mudar para acórdão se necessário)
            const custasStatusEl = $('custas-status');
            const custasOrigemEl = $('custas-origem');
            if (prep.sentenca.custas) {
                if ($('val-custas')) $('val-custas').value = prep.sentenca.custas;
                // Sempre usa sentença como padrão
                if (custasStatusEl) custasStatusEl.value = 'devidas';
                if (custasOrigemEl) custasOrigemEl.value = 'sentenca';
                if ($('custas-data-origem') && prep.sentenca.data) {
                    $('custas-data-origem').value = prep.sentenca.data;
                }
            }

            // REGRA 6: hsusp → Honorários Adv. Réu com condição suspensiva
            const chkHonReu = $('chk-hon-reu');
            const honReuCampos = $('hon-reu-campos');
            if (prep.sentenca.hsusp) {
                // Lógica invertida: desmarcar "Não há" para mostrar campos
                if (chkHonReu) chkHonReu.checked = false;
                if (honReuCampos) honReuCampos.classList.remove('hidden');

                const radSusp = document.querySelector('input[name="rad-hon-reu"][value="suspensiva"]');
                if (radSusp) radSusp.checked = true;
            } else {
                // Estado padrão: checkbox marcado, campos ocultos
                if (chkHonReu) chkHonReu.checked = true;
                if (honReuCampos) honReuCampos.classList.add('hidden');
            }


                $('homologacao-overlay').style.display = 'flex';
                dbg('Overlay exibido para o usuario.');
                try {
                    const txt = await navigator.clipboard.readText();
                    if (txt && txt.trim().length > 0) {
                        $('val-id').value = txt.trim();
                    }
                } catch (e) { console.warn('Clipboard ignorado ou bloqueado', e); }
                updateHighlight();
            } catch (e) {
                err('Erro no handler do botao Gerar Homologacao:', e);
                alert('Erro ao abrir assistente. Verifique o console (F12).');
                return;
                }
        };
        $('btn-fechar').onclick = (e) => {
            e.preventDefault();  // Previne scroll indesejado
            const modal = $('homologacao-modal');
            const overlay = $('homologacao-overlay');
            modal.style.opacity = '1';
            modal.style.pointerEvents = 'all';
            modal.dataset.ghost = 'false';
            overlay.style.display = 'none';
            overlay.style.pointerEvents = 'none';
            // LIMPAR REFERÊNCIAS DOM: v1.8 usa método centralizado
            window.hcalcState.resetPrep();
            console.log('[hcalc] Estado resetado via hcalcState.resetPrep()');
        };
        $('homologacao-overlay').onclick = (e) => {
            if (e.target.id === 'homologacao-overlay') {
                // Não fecha — torna transparente e "fantasma"
                const modal = $('homologacao-modal');
                const overlay = $('homologacao-overlay');
                const isGhost = modal.dataset.ghost === 'true';
                if (isGhost) {
                    // Segundo clique fora: volta ao normal
                    modal.style.opacity = '1';
                    modal.style.pointerEvents = 'all';
                    overlay.style.pointerEvents = 'none';
                    modal.dataset.ghost = 'false';
                } else {
                    // Primeiro clique fora: vira fantasma
                    modal.style.opacity = '0.25';
                    modal.style.transition = 'opacity 0.3s';
                    modal.style.pointerEvents = 'none';
                    // Mantém overlay transparente para detectar clique de retorno
                    overlay.style.pointerEvents = 'all';
                    modal.dataset.ghost = 'true';
                }
            }
        };

        $('calc-origem').onchange = (e) => { $('col-pjc').classList.toggle('hidden', e.target.value !== 'pjecalc'); };
        $('calc-autor').onchange = (e) => { $('col-esclarecimentos').classList.toggle('hidden', e.target.value !== 'perito'); };
        $('calc-esclarecimentos').onchange = (e) => { $('calc-peca-perito').classList.toggle('hidden', !e.target.checked); };

        $('calc-fgts').onchange = (e) => {
            $('col-fgts-val').classList.toggle('hidden', !e.target.checked);
            updateHighlight();
        };
        $('calc-indice').onchange = (e) => { $('col-juros-val').classList.toggle('hidden', e.target.value !== 'tr'); };
        $('ignorar-hon-autor').onchange = (e) => { $('val-hon-autor').classList.toggle('hidden', e.target.checked); updateHighlight(); };
        $('ignorar-inss').onchange = (e) => {
            $('val-inss-rec').classList.toggle('hidden', e.target.checked);
            $('val-inss-total').classList.toggle('hidden', e.target.checked);
            updateHighlight();
        };
        $('irpf-tipo').onchange = (e) => { $('irpf-campos').classList.toggle('hidden', e.target.value === 'isento'); };

        $('resp-tipo').onchange = (e) => { $('resp-sub-opcoes').classList.toggle('hidden', e.target.value !== 'subsidiarias'); };

        // Lógica para Períodos Diversos
        $('resp-diversos').onchange = (e) => {
            const fieldset = $('resp-diversos-fieldset');
            const container = $('resp-diversos-container');
            const selectPrincipal = $('resp-devedora-principal');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            if (e.target.checked) {
                fieldset.classList.remove('hidden');

                // Preencher dropdown de Devedora Principal
                selectPrincipal.innerHTML = '';
                reclamadas.forEach((rec, idx) => {
                    const opt = document.createElement('option');
                    opt.value = rec;
                    opt.textContent = rec;
                    if (idx === 0) opt.selected = true; // Primeira como padrão
                    selectPrincipal.appendChild(opt);
                });

                // Verifique se já existe um formulário, senão crie um
                if (container.children.length === 0) {
                    adicionarLinhaPeridoDiverso();
                }
            } else {
                fieldset.classList.add('hidden');
                container.innerHTML = '';
            }
        };

        $('btn-adicionar-periodo').onclick = (e) => {
            e.preventDefault();
            adicionarLinhaPeridoDiverso();
        };

        function adicionarLinhaPeridoDiverso() {
            const container = $('resp-diversos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const idx = container.children.length;
            const rowId = `periodo-diverso-${idx}`;

            const div = document.createElement('div');
            div.id = rowId;
            div.className = 'row';
            div.style.marginBottom = '15px';
            div.style.padding = '12px';
            div.style.backgroundColor = '#f5f5f5';
            div.style.borderRadius = '4px';

            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                selectOptions += `<option value="${rec}">${rec}</option>`;
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Reclamada Subsidiária ${idx + 1}</label>
                    <select class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <label>Período</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Ex: 01/01/2020 a 31/12/2020" style="width: 100%; padding: 8px;">
                    </div>
                    <div style="flex: 1;">
                        <label>ID Cálculo Separado</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="ID #XXXX" style="width: 100%; padding: 8px;">
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <label><input type="checkbox" class="periodo-total" data-idx="${idx}"> Período Total</label>
                    <button type="button" class="btn-action" style="padding: 8px; margin-left: auto; background: #d32f2f;" onclick="document.getElementById('${rowId}').remove();">Remover</button>
                </div>
            `;
            container.appendChild(div);
        }

        $('chk-hon-reu').onchange = (e) => {
            // Lógica invertida: marcado = "Não há" = esconde campos
            $('hon-reu-campos').classList.toggle('hidden', e.target.checked);
        };
        $('chk-perito-conh').onchange = (e) => { $('perito-conh-campos').classList.toggle('hidden', !e.target.checked); };

        $('chk-deposito').onchange = (e) => { $('deposito-campos').classList.toggle('hidden', !e.target.checked); };
        $('dep-tipo').onchange = (e) => { $('dep-liberacao-row').classList.toggle('hidden', e.target.value === 'garantia'); };
        $('dep-principal').onchange = (e) => { $('dep-liberacao-row').classList.toggle('hidden', !e.target.checked); };
        $('chk-pag-antecipado').onchange = (e) => { $('pag-antecipado-campos').classList.toggle('hidden', !e.target.checked); };

        // Event listeners para radios de tipo de liberação
        document.querySelectorAll('input[name="lib-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const valor = e.target.value;
                $('lib-remanescente-campos').classList.toggle('hidden', valor !== 'remanescente');
                $('lib-devolucao-campos').classList.toggle('hidden', valor !== 'devolucao');
            });
        });

        document.getElementsByName('rad-intimacao').forEach((rad) => {
            rad.onchange = (e) => { $('intimacao-mandado-campos').classList.toggle('hidden', e.target.value === 'diario'); };
        });

        // Máscara de data DD/MM/YYYY para campos de data
        const aplicarMascaraData = (input) => {
            input.addEventListener('input', (e) => {
                let valor = e.target.value.replace(/\D/g, ''); // Remove não-dígitos
                if (valor.length >= 2) {
                    valor = valor.slice(0, 2) + '/' + valor.slice(2);
                }
                if (valor.length >= 5) {
                    valor = valor.slice(0, 5) + '/' + valor.slice(5);
                }
                e.target.value = valor.slice(0, 10); // Limita a DD/MM/YYYY
            });
        };

        // Aplicar máscara aos campos de data
        ['val-data', 'custas-data-origem', 'val-perito-data'].forEach(id => {
            const campo = $(id);
            if (campo) aplicarMascaraData(campo);
        });

        // Toggle origem custas: Sentença vs Acórdão
        $('custas-origem').onchange = (e) => {
            const isAcordao = e.target.value === 'acordao';
            $('custas-data-col').classList.toggle('hidden', isAcordao);
            $('custas-acordao-col').classList.toggle('hidden', !isAcordao);
        };

        const detReclamadasEl = $('det-reclamadas');
        const detPeritosEl = $('det-peritos');

        const ordemCopiaLabels = {
            'val-id': '1) Id da Planilha',
            'val-data': '1) Data da Atualização',
            'val-credito': '1) Crédito Principal',
            'val-fgts': '1) FGTS Separado',
            'val-inss-rec': '2) INSS - Desconto Reclamante',
            'val-inss-total': '2) INSS - Total Empresa',
            'val-hon-autor': '3) Honorários do Autor',
            'val-custas': '4) Custas'
        };

        window.hcalcPeritosDetectados = [];
        window.hcalcPeritosConhecimentoDetectados = [];

        function isNomeRogerio(nome) {
            return /rogerio|rogério/i.test(nome || '');
        }

        function aplicarRegrasPeritosDetectados(peritosDetectados) {
            const nomes = Array.isArray(peritosDetectados) ? peritosDetectados.filter(Boolean) : [];
            const temRogerio = nomes.some((nome) => isNomeRogerio(nome));
            const peritosConhecimento = nomes.filter((nome) => !isNomeRogerio(nome));

            window.hcalcPeritosDetectados = nomes;
            window.hcalcPeritosConhecimentoDetectados = peritosConhecimento;

            const origemEl = $('calc-origem');
            const pjcEl = $('calc-pjc');
            const autorEl = $('calc-autor');
            const colEsclarecimentosEl = $('col-esclarecimentos');
            const rowPeritoContabilEl = $('row-perito-contabil');
            const chkPeritoConhEl = $('chk-perito-conh');
            const peritoConhCamposEl = $('perito-conh-campos');
            const valPeritoNomeEl = $('val-perito-nome');
            const valPeritoContabilValorEl = $('val-perito-contabil-valor');

            if (temRogerio) {
                origemEl.value = 'pjecalc';
                origemEl.disabled = true;
                pjcEl.checked = true;
                pjcEl.disabled = true;
                autorEl.value = 'perito';
                autorEl.disabled = true;
                colEsclarecimentosEl.classList.remove('hidden');
                rowPeritoContabilEl.classList.remove('hidden');
            } else {
                origemEl.disabled = false;
                pjcEl.disabled = false;
                autorEl.disabled = false;
                rowPeritoContabilEl.classList.add('hidden');
                if (valPeritoContabilValorEl) {
                    valPeritoContabilValorEl.value = '';
                }
            }

            // Controlar visibilidade do fieldset de perícia conhecimento
            const fieldsetPericiaConh = $('fieldset-pericia-conh');
            if (peritosConhecimento.length > 0) {
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.remove('hidden');
                chkPeritoConhEl.checked = true;
                peritoConhCamposEl.classList.remove('hidden');
                valPeritoNomeEl.value = peritosConhecimento.join(' | ');
            } else {
                // Esconder card de perícia se não há perito de conhecimento
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.add('hidden');
            }
        }

        function atualizarStatusProximoCampo(nextInputId = null) {
            // Função simplificada - status removido da interface
            // Mantida para compatibilidade com código existente
        }

        // Timeline functions moved to prep.js
        // readTimelineBasic / extractDataFromTimelineItem / getTimelineItems
        // now handled by window.executarPrep()

        function construirSecaoIntimacoes() {
            const container = $('lista-intimacoes-container');
            if (!container) return;

            const passivo = window.hcalcPartesData?.passivo || [];
            const advMap = window.hcalcStatusAdvogados || {};
            const partesIntimadasEdital = window.hcalcPrepResult?.partesIntimadasEdital || [];

            container.innerHTML = '';

            if (passivo.length === 0) {
                container.innerHTML = `
                    <div style="margin-bottom: 5px;">
                        <input type="text" id="int-nome-parte-manual" placeholder="Nome da Reclamada" style="width: 100%; padding: 6px; box-sizing: border-box; margin-bottom: 5px;">
                        <select id="sel-intimacao-manual" style="width: 100%; padding: 4px;">
                            <option value="diario">Diário (Advogado - Art. 523)</option>
                            <option value="mandado">Mandado (Art. 880 - 48h)</option>
                            <option value="edital">Edital (Art. 880 - 48h)</option>
                        </select>
                    </div>`;
                return;
            }

            passivo.forEach((parte, idx) => {
                const temAdvogado = advMap[parte.nome] === true;
                let modoDefault = 'mandado';

                if (temAdvogado) modoDefault = 'diario';
                else if (partesIntimadasEdital.includes(parte.nome)) modoDefault = 'edital';

                const divRow = document.createElement('div');
                divRow.className = 'intimacao-row';
                divRow.style.cssText = "display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; padding: 6px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;";

                divRow.innerHTML = `
                    <div style="flex: 1; font-size: 13px; font-weight: bold; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px;" title="${parte.nome}">
                        ${parte.nome}
                    </div>
                    <div style="flex-shrink: 0;">
                        <select class="sel-modo-intimacao" data-nome="${parte.nome}" style="padding: 4px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="diario" ${modoDefault === 'diario' ? 'selected' : ''}>Diário (Advogado - Art 523)</option>
                            <option value="mandado" ${modoDefault === 'mandado' ? 'selected' : ''}>Mandado (Art 880 - 48h)</option>
                            <option value="edital" ${modoDefault === 'edital' ? 'selected' : ''}>Edital (Art 880 - 48h)</option>
                            <option value="ignorar">Não Intimar</option>
                        </select>
                    </div>
                `;
                container.appendChild(divRow);
            });
        }

        async function refreshDetectedPartes() {
            if (!detReclamadasEl || !detPeritosEl) { return; }
            const partes = await derivePartesData();

            // Armazenar globalmente para uso em geração de textos
            window.hcalcPartesData = partes;

            const reclamadas = (partes?.passivo || []).map(p => p.nome).filter(Boolean);
            const peritos = ordenarComRogerioPrimeiro(extractPeritos(partes));
            const advogadosMap = extractAdvogadosPorReclamada(partes);
            const statusAdvMap = extractStatusAdvogadoPorReclamada(partes);

            window.hcalcStatusAdvogados = statusAdvMap;

            const reclamadasComStatus = (partes?.passivo || []).map((parte) => {
                const nome = parte?.nome || '';
                if (!nome) { return null; }
                const comAdv = statusAdvMap[nome] === true;
                return { nome, comAdv };
            }).filter(Boolean);

            const qtdComAdv = reclamadas.filter((nome) => statusAdvMap[nome] === true).length;
            const qtdSemAdv = reclamadas.length - qtdComAdv;

            // Log para debug
            console.log('hcalc: advogados por reclamada', advogadosMap);
            console.log('hcalc: status advogado por reclamada', statusAdvMap);

            // BADGES: Reclamadas
            if (reclamadasComStatus.length) {
                detReclamadasEl.innerHTML = reclamadasComStatus.map(r =>
                    `<span class="badge ${r.comAdv ? 'badge-blue' : 'badge-gray'}" title="${r.comAdv ? 'Com advogado' : 'Sem advogado'}">${r.nome}</span>`
                ).join('');
            } else {
                detReclamadasEl.innerHTML = '<span style="font-size: 11px; color: #999; font-style: italic;">Nenhuma reclamada detectada</span>';
            }

            // BADGES: Peritos
            if (peritos.length) {
                detPeritosEl.innerHTML = peritos.map(p =>
                    `<span class="badge badge-green">${p}</span>`
                ).join('');
            } else {
                detPeritosEl.innerHTML = '<span style="font-size: 11px; color: #999; font-style: italic;">Não há perícias</span>';
            }

            aplicarRegrasPeritosDetectados(peritos);

            // Log de debug
            console.log(`[hcalc] Detecção atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            // LÓGICA DE RESPONSABILIDADE DINÂMICA
            const respFieldset = document.querySelector('fieldset #resp-tipo')?.closest('fieldset');
            if (reclamadas.length <= 1 && respFieldset) {
                respFieldset.classList.add('hidden');
            } else if (reclamadas.length > 1 && respFieldset) {
                respFieldset.classList.remove('hidden');
            }

            // AUTO-PREENCHER DEPOSITANTE COM RECLAMADA EXTRAIDA
            const depDepositante = $('dep-depositante');
            if (depDepositante && reclamadas.length > 0) {
                if (reclamadas.length === 1) {
                    // Só 1 reclamada: preencher e travar
                    depDepositante.value = reclamadas[0];
                    depDepositante.disabled = true;
                } else {
                    // 2+ reclamadas: transformar em dropdown
                    const selectEl = document.createElement('select');
                    selectEl.id = 'dep-depositante';
                    selectEl.style.cssText = depDepositante.style.cssText || 'padding: 8px; border: 1px solid #aaa; border-radius: 4px; font-size: 14px;';
                    reclamadas.forEach((rec, idx) => {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (idx === 0) opt.selected = true;
                        selectEl.appendChild(opt);
                    });
                    depDepositante.replaceWith(selectEl);
                }
            }

            // CONSTRUIR SEÇÃO DE INTIMAÇÕES
            construirSecaoIntimacoes();
        }

        function getProcessIdFromUrl() {
            const match = window.location.href.match(/\/processo\/(\d+)/);
            return match ? match[1] : null;
        }

        function shapePartesPayload(dados) {
            const buildRecord = (parte, tipo, idx, total) => {
                let nome = parte.nome.trim();
                return {
                    nome,
                    cpfcnpj: parte.documento || 'desconhecido',
                    tipo,
                    telefone: formatTelefones(parte.pessoaFisica),
                    representantes: (parte.representantes || []).map(rep => ({
                        nome: rep.nome.trim(),
                        cpfcnpj: rep.documento || 'desconhecido',
                        oab: rep.numeroOab || '',
                        tipo: rep.tipo
                    }))
                };
            };

            const formatTelefones = (pessoaFisica) => {
                if (!pessoaFisica) { return 'desconhecido'; }
                const numbers = [];
                if (pessoaFisica.dddCelular && pessoaFisica.numeroCelular) {
                    numbers.push(`(${pessoaFisica.dddCelular}) ${pessoaFisica.numeroCelular}`);
                }
                if (pessoaFisica.dddResidencial && pessoaFisica.numeroResidencial) {
                    numbers.push(`(${pessoaFisica.dddResidencial}) ${pessoaFisica.numeroResidencial}`);
                }
                if (pessoaFisica.dddComercial && pessoaFisica.numeroComercial) {
                    numbers.push(`(${pessoaFisica.dddComercial}) ${pessoaFisica.numeroComercial}`);
                }
                return numbers.join(' | ') || 'desconhecido';
            };

            const ativo = (dados?.ATIVO || []).map((parte, idx) => buildRecord(parte, 'AUTOR', idx, dados.ATIVO.length));
            const passivo = (dados?.PASSIVO || []).map((parte, idx) => buildRecord(parte, 'RÉU', idx, dados.PASSIVO.length));
            const outros = (dados?.TERCEIROS || []).map((parte, idx) => buildRecord(parte, parte.tipo || 'TERCEIRO', idx, dados.TERCEIROS.length));

            return { ativo, passivo, outros };
        }

        async function fetchPartesViaApi() {
            const trtHost = window.location.host;
            const baseUrl = `https://${trtHost}`;
            const idProcesso = getProcessIdFromUrl();
            if (!idProcesso) {
                console.warn('hcalc: idProcesso não detectado na URL.');
                return null;
            }
            const url = `${baseUrl}/pje-comum-api/api/processos/id/${idProcesso}/partes`;
            try {
                const response = await fetch(url, { credentials: 'include' });
                if (!response.ok) {
                    throw new Error(`API retornou ${response.status}`);
                }
                const json = await response.json();
                const partes = shapePartesPayload(json);
                // Armazenar no cache
                const PROCESS_CACHE = window.calcPartesCache || {};
                PROCESS_CACHE[idProcesso] = partes;
                window.calcPartesCache = PROCESS_CACHE;

                // LIMITAR CACHE: Manter apenas últimas 5 entradas para prevenir crescimento ilimitado
                const keys = Object.keys(window.calcPartesCache);
                if (keys.length > 5) {
                    delete window.calcPartesCache[keys[0]];
                    console.log('hcalc: cache limitado a 5 entradas, removida mais antiga');
                }

                console.log('hcalc: partes extraídas via API', partes);
                return partes;
            } catch (error) {
                console.error('hcalc: falha ao buscar partes via API', error);
                return null;
            }
        }

        async function derivePartesData() {
            // Inicializar cache se não existir
            if (!window.calcPartesCache) {
                window.calcPartesCache = {};
            }
            const cache = window.calcPartesCache;
            const processId = getProcessIdFromUrl();

            // 1. Tentar cache primeiro
            if (processId && cache[processId]) {
                console.log('hcalc: usando dados do cache', cache[processId]);
                return cache[processId];
            }

            // 2. Tentar buscar via API
            if (processId) {
                const apiData = await fetchPartesViaApi();
                if (apiData) {
                    return apiData;
                }
            }

            // 3. Fallback: buscar qualquer cache disponível
            const fallbackKey = processId ? Object.keys(cache).find((key) => key.includes(processId)) : null;
            if (fallbackKey) {
                console.log('hcalc: usando cache alternativo', cache[fallbackKey]);
                return cache[fallbackKey];
            }

            const cachedValues = Object.values(cache);
            if (cachedValues.length > 0) {
                console.log('hcalc: usando primeiro cache disponível', cachedValues[0]);
                return cachedValues[0];
            }

            // 4. Último recurso: parsear DOM
            console.warn('hcalc: usando parseamento do DOM (pode ser impreciso)');
            return parsePartesFromDom();
        }

        function parsePartesFromDom() {
            const rows = document.querySelectorAll('div[class*="bloco-participante"] tbody tr');
            const data = { ativo: [], passivo: [], outros: [] };
            rows.forEach((row) => {
                const text = row.innerText || '';
                const value = text.split('\n').map((l) => l.trim()).find(Boolean) || text.trim();
                if (!value) { return; }
                if (/reclamante|exequente|autor/i.test(text)) {
                    data.ativo.push({ nome: value });
                } else if (/reclamado|réu|executado/i.test(text)) {
                    data.passivo.push({ nome: value });
                } else {
                    data.outros.push({ nome: value, tipo: 'OUTRO' });
                }
            });
            return data;
        }

        function extractPeritos(partes) {
            const outros = partes?.outros || [];
            // Filtrar por tipo 'PERITO' ou qualquer variação no nome/tipo
            return outros.filter((part) => {
                const tipo = (part.tipo || '').toUpperCase();
                const nome = (part.nome || '').toUpperCase();
                return tipo.includes('PERITO') || nome.includes('PERITO');
            }).map((part) => part.nome);
        }

        function ordenarComRogerioPrimeiro(nomes) {
            if (!Array.isArray(nomes) || nomes.length === 0) { return []; }
            const rogerio = [];
            const demais = [];
            nomes.forEach((nome) => {
                if (/rogerio/i.test(nome || '')) {
                    rogerio.push(nome);
                } else {
                    demais.push(nome);
                }
            });
            return [...rogerio, ...demais];
        }

        // ==========================================
        // FUNÇÕES DE EXTRAÇÃO DE REPRESENTANTES
        // ==========================================
        window.hcalcPartesData = null; // Cache global de partes para uso em geração de textos

        function extractAdvogadosPorReclamada(partes) {
            const map = {};
            if (!partes?.passivo) { return map; }
            partes.passivo.forEach((reclamada) => {
                const reps = reclamada.representantes || [];
                const advogados = reps.filter(rep => {
                    const tipo = (rep.tipo || '').toUpperCase();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB');
                }).map(rep => ({
                    nome: rep.nome,
                    oab: rep.oab || ''
                }));
                map[reclamada.nome] = advogados;
            });
            return map;
        }

        function extractStatusAdvogadoPorReclamada(partes) {
            const map = {};
            if (!partes?.passivo) { return map; }

            partes.passivo.forEach((reclamada) => {
                const reps = Array.isArray(reclamada.representantes) ? reclamada.representantes : [];
                const temRepresentante = reps.length > 0;

                const temIndicadorAdv = reps.some((rep) => {
                    const tipo = (rep?.tipo || '').toUpperCase();
                    const oab = (rep?.oab || rep?.numeroOab || '').toString().trim();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB') || oab !== '';
                });

                map[reclamada.nome] = temRepresentante || temIndicadorAdv;
            });

            return map;
        }

        function temAdvogado(nomeReclamada, advogadosMap) {
            if (!advogadosMap || !nomeReclamada) { return false; }
            const reps = advogadosMap[nomeReclamada] || [];
            return reps.length > 0;
        }

        function obterReclamadasSemAdvogado(partes, advogadosMap) {
            if (!partes?.passivo) { return []; }
            return partes.passivo.filter(rec => !temAdvogado(rec.nome, advogadosMap)).map(rec => rec.nome);
        }

        function obterReclamadasComAdvogado(partes, advogadosMap) {
            if (!partes?.passivo) { return []; }
            return partes.passivo.filter(rec => temAdvogado(rec.nome, advogadosMap)).map(rec => rec.nome);
        }

        refreshDetectedPartes();

        // ==========================================
        // 4. LÓGICA DE NAVEGAÇÃO "COLETA INTELIGENTE"
        // ==========================================
        const orderSequence = [
            'val-id', 'val-data', 'val-credito', 'val-fgts',
            'val-inss-rec', 'val-inss-total', 'val-hon-autor', 'val-custas'
        ];

        function updateHighlight(currentId = null) {
            orderSequence.forEach((id) => $(id).classList.remove('highlight'));
            const visibleInputs = orderSequence.filter((id) => !$(id).classList.contains('hidden'));
            if (visibleInputs.length === 0) return;
            let nextIndex = 0;
            if (currentId) {
                const currentIndex = visibleInputs.indexOf(currentId);
                if (currentIndex !== -1 && currentIndex < visibleInputs.length - 1) {
                    nextIndex = currentIndex + 1;
                } else if (currentIndex === visibleInputs.length - 1) {
                    return;
                }
            }
            const nextInputId = visibleInputs[nextIndex];
            $(nextInputId).classList.add('highlight');
            $(nextInputId).focus();
            atualizarStatusProximoCampo(nextInputId);
        }

        orderSequence.forEach((id) => {
            const el = $(id);
            el.addEventListener('paste', () => {
                setTimeout(() => {
                    el.value = el.value.trim();
                    updateHighlight(id);
                }, 10);
            });
            el.addEventListener('focus', () => {
                orderSequence.forEach((i) => $(i).classList.remove('highlight'));
                el.classList.add('highlight');
            });
        });

        // ==========================================
        // 5. FUNÇÕES AUXILIARES DE CÁLCULO E TEXTO
        function parseMoney(str) {
            if (!str) return 0;
            str = str.replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
            const num = parseFloat(str);
            return isNaN(num) ? 0 : num;
        }

        function formatMoney(num) {
            return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }).replace(/\s/g, '');
        }

        function normalizeMoneyInput(val) {
            if (!val || val === '[VALOR]') return val;
            const parsed = parseMoney(val);
            if (parsed === 0 && !/^\s*0/.test(val)) return val;
            return formatMoney(parsed);
        }

        function bold(text) { return `<strong>${text}</strong>`; }
        function u(text) { return `<u>${text}</u>`; }

        // ==========================================
        // 6. GERADOR DE DECISÃO HTML (O CORE)
        // ==========================================
        $('btn-gravar').onclick = () => {
            dbg('Clique em Gravar Decisao detectado.');
            let text = `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Vistos.</p>`;
            let houveDepositoDireto = false;
            let houveLibecaoDetalhada = false;
            const passivoTotal = (window.hcalcPartesData?.passivo || []).length;

            const autoria = $('calc-autor').options[$('calc-autor').selectedIndex].text;
            const idPlanilha = $('val-id').value || '[ID DA PLANILHA]';
            const valData = $('val-data').value || '[DATA]';
            const valCredito = $('val-credito').value || '[VALOR]';
            const valFgts = $('val-fgts').value || '[VALOR FGTS]';
            const isPerito = $('calc-autor').value === 'perito';
            const peritoEsclareceu = $('calc-esclarecimentos').checked;
            const pecaPerito = $('calc-peca-perito').value || '[ID PEÇA]';
            const indice = $('calc-indice').value;
            const isFgtsSep = $('calc-fgts').checked;
            const ignorarInss = $('ignorar-inss').checked;

            const xxx = () => u(bold('XXX'));

            const appendBaseAteAntesPericiais = ({
                idCalculo,
                usarPlaceholder = false,
                reclamadaLabel = ''
            }) => {
                let introTxt = '';
                const vCredito = usarPlaceholder ? 'R$XXX' : `R$${valCredito}`;
                const vFgts = usarPlaceholder ? 'R$XXX' : `R$${valFgts}`;
                const vData = usarPlaceholder ? 'XXX' : valData;

                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idCalculo)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idCalculo)}), `;
                }

                if (isFgtsSep) {
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)} relativo ao principal, e ${bold(vFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(vData)}. `;
                } else {
                    introTxt += `fixando o crédito em ${bold(vCredito)}, referente ao valor principal, atualizado para ${bold(vData)}. `;
                }

                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualização foi feita na forma da Lei 14.905/2024 e da decisão da SDI-1 do C. TST (IPCA-E até a distribuição; taxa Selic até 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A correção monetária foi realizada pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = usarPlaceholder ? 'XXX' : ($('val-juros').value || '[JUROS]');
                    const dtIngresso = usarPlaceholder ? 'XXX' : ($('data-ingresso').value || '[DATA INGRESSO]');
                    introTxt += `Atualizáveis pela TR/IPCA-E, conforme sentença. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }

                if (reclamadaLabel) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${reclamadaLabel}</strong></p>`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                if (!usarPlaceholder && $('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }

                if (usarPlaceholder) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada, ainda, deverá pagar o valor de sua cota-parte no INSS, a saber, ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${xxx()} para ${xxx()}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${xxx()}, para ${xxx()}.</p>`;
                    if ($('chk-hon-reu').checked) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                    } else {
                        const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                        if (rdHonReu === 'suspensiva') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${xxx()}.</p>`;
                        }
                    }
                    return;
                }

                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}.</p>`;
                }

                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }

                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }

                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                    if (rdHonReu === 'suspensiva') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                    } else {
                        const p = $('val-hon-reu-perc').value;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}.</p>`;
                    }
                }
            };

            // Função unificada para liberação detalhada (depósito recursal ou pagamento antecipado)
            const gerarLiberacaoDetalhada = (contexto) => {
                const { prefixo = '', depositoInfo = '' } = contexto;

                // Linha inicial com referência à planilha
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Passo à liberação de valores conforme planilha #${bold(idPlanilha)}:</p>`;

                let numLiberacao = 1;

                // 1) Crédito do reclamante
                if (depositoInfo) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante ${depositoInfo}, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                } else {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante seu crédito, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                }
                numLiberacao++;

                // 2) INSS (se não ignorado)
                if (!ignorarInss) {
                    const valInssRec = normalizeMoneyInput($('val-inss-rec').value || '0,00');
                    const valInssTotal = normalizeMoneyInput($('val-inss-total').value || '0,00');

                    // Calcular INSS patronal
                    const isPjeCalc = $('calc-pjc').checked;
                    let inssEmpregado = valInssRec; // parte empregado - sempre valor do reclamante
                    let inssPatronal = valInssTotal; // parte patronal/reclamada

                    // Se é PJC: patronal = total - empregado
                    if (isPjeCalc && valInssTotal && valInssRec) {
                        const totalNum = parseMoney(valInssTotal);
                        const recNum = parseMoney(valInssRec);
                        const patronalNum = totalNum - recNum;
                        inssPatronal = formatMoney(patronalNum);
                    }
                    // Se não é PJC: usa direto o valInssTotal

                    const totalInss = valInssTotal;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Proceda a Secretaria à transferência de valores ao órgão competente, via Siscondj, sendo: ${bold('R$ ' + inssEmpregado)} referente às contribuições previdenciárias parte empregado e ${bold('R$ ' + inssPatronal)} no que concernem às contribuições patronais (total de ${bold('R$ ' + totalInss)}).</p>`;
                    numLiberacao++;
                }

                // 3) Honorários periciais (se houver)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';

                // Perito contábil (Rogério) - se houver
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(peritoContabilDetectado)} seus honorários, no valor de ${bold('R$' + vContabil)}.</p>`;
                    numLiberacao++;
                }

                // Peritos de conhecimento - se houver
                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((n) => n.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                const valorPeritoConh = $('val-perito-valor')?.value || '';
                const tipoPagPericia = $('perito-tipo-pag')?.value || 'reclamada';

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0 && valorPeritoConh) {
                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia !== 'trt') {
                            const vP = normalizeMoneyInput(valorPeritoConh);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(nomePerito)} seus honorários, no valor de ${bold('R$' + vP)}.</p>`;
                            numLiberacao++;
                        }
                    });
                }

                // 4) Honorários do advogado do autor (se não ignorado)
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao patrono da parte autora seus honorários, no valor de ${bold('R$' + vHonA)}.</p>`;
                    numLiberacao++;
                }

                // Retornar o número da próxima liberação (para devolução)
                return numLiberacao;
            };

            const appendDisposicoesFinais = () => {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>Disposições finais:</strong></p>`;

                // CONTÁBIL PRIMEIRO (Rogério)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários contábeis em favor de ${bold(peritoContabilDetectado)}, ora arbitrados em ${bold(vContabil)}.</p>`;
                }

                // CONHECIMENTO DEPOIS
                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((n) => n.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0) {
                    const vP = $('val-perito-valor').value || '[VALOR/ID]';
                    const dtP = $('val-perito-data').value || $('val-data').value || '[DATA]';
                    const tipoPagPericia = $('perito-tipo-pag').value;

                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários periciais da fase de conhecimento assim estabelecidos:</p>`;

                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia === 'trt') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagos pelo TRT, considerando a sucumbência do autor no objeto da perícia (#${bold(vP)}).</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagamento de ${bold('R$' + vP)} pela reclamada, para ${bold(dtP)}.</p>`;
                        }
                    });
                }

                if ($('custas-status').value === 'pagas') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas pagas em razão de recurso.</p>`;
                } else {
                    const valC = $('val-custas').value || '[VALOR]';
                    const origemCustas = $('custas-origem').value;

                    if (valC && valC !== '0,00' && valC !== '0') {
                        if (origemCustas === 'acordao') {
                            // Custas por acórdão (inclui ID do acórdão no texto)
                            const acordaoIdx = $('custas-acordao-select').value;
                            const acordaoSel = $('custas-acordao-select').selectedOptions[0];
                            const dataAcordao = acordaoSel?.dataset?.data || '[DATA ACÓRDÃO]';
                            const idAcordao = acordaoSel?.dataset?.id || '';
                            const idTexto = idAcordao ? ` #${bold(idAcordao)}` : '';
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas definidas em acórdão${idTexto}, pela reclamada, no valor de ${bold('R$' + valC)} para ${bold(dataAcordao)}.</p>`;
                        } else {
                            // Custas por sentença (padrão)
                            const dataCustas = $('custas-data-origem').value || valData;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas de ${bold('R$' + valC)} pela reclamada, para ${bold(dataCustas)}.</p>`;
                        }
                    }
                }

                if ($('chk-deposito').checked) {
                    const tDep = $('dep-tipo').value;
                    const dNome = $('dep-depositante').value || '[RECLAMADA]';
                    const dId = $('dep-id').value || '[ID]';
                    let isPrin = $('dep-principal').checked;

                    const passivoDetectado = (window.hcalcPartesData?.passivo || []).map((p) => p?.nome).filter(Boolean);
                    const primeiraReclamada = passivoDetectado[0] || '';
                    const tipoRespAtual = $('resp-tipo')?.value || 'unica';
                    const isDepositoJudicial = tDep !== 'garantia';

                    let criterioLiberacaoDeposito = 'manual';
                    let depositanteResolvida = dNome;

                    if (passivoDetectado.length === 1) {
                        depositanteResolvida = passivoDetectado[0];
                        isPrin = true;
                        criterioLiberacaoDeposito = 'reclamada-unica';
                    } else if (tipoRespAtual === 'subsidiarias' && primeiraReclamada) {
                        depositanteResolvida = primeiraReclamada;
                        isPrin = true;
                        criterioLiberacaoDeposito = 'subsidiaria-principal';
                    } else if (tipoRespAtual === 'solidarias') {
                        depositanteResolvida = depositanteResolvida || primeiraReclamada || '[RECLAMADA]';
                        criterioLiberacaoDeposito = 'solidaria';
                    }

                    const deveLiberarDeposito = isDepositoJudicial && (
                        criterioLiberacaoDeposito === 'reclamada-unica' ||
                        criterioLiberacaoDeposito === 'subsidiaria-principal' ||
                        criterioLiberacaoDeposito === 'solidaria' ||
                        (criterioLiberacaoDeposito === 'manual' && isPrin)
                    );

                    const naturezaDevedora = criterioLiberacaoDeposito === 'solidaria'
                        ? 'solidária'
                        : (isPrin ? 'principal' : 'subsidiária');

                    const bancoTxt = tDep === 'bb' ? 'Banco do Brasil' : (tDep === 'sif' ? 'Caixa Econômica Federal (SIF)' : 'seguro garantia regular');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito recursal da devedora ${naturezaDevedora} (${depositanteResolvida} - Id ${bold(dId)}) via ${bancoTxt}.</p>`;
                    if (!isDepositoJudicial) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Tratando-se de seguro garantia, não há liberação imediata de valores nesta oportunidade.</p>`;
                    } else {
                        const modoSelecionado = (document.querySelector('input[name="rad-dep-lib"]:checked')?.value === 'detalhada')
                            ? 'detalhada'
                            : 'direta';

                        const depositosLiberaveis = deveLiberarDeposito
                            ? [{ depositante: depositanteResolvida, id: dId, banco: bancoTxt, modo: modoSelecionado }]
                            : [];

                        const formatarLista = (itens) => {
                            if (!itens || itens.length === 0) { return ''; }
                            if (itens.length === 1) { return itens[0]; }
                            if (itens.length === 2) { return `${itens[0]} e ${itens[1]}`; }
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };

                        const montarListaDepositos = (deps) => {
                            const itens = deps.map((d) => `${d.depositante} #${bold(d.id)}`);
                            return formatarLista(itens);
                        };

                        const montarListaBancos = (deps) => {
                            const unicos = [...new Set(deps.map((d) => d.banco))];
                            return formatarLista(unicos);
                        };

                        const depsDiretos = depositosLiberaveis.filter((d) => d.modo === 'direta');
                        const depsDetalhados = depositosLiberaveis.filter((d) => d.modo === 'detalhada');

                        if (depsDiretos.length > 0) {
                            houveDepositoDireto = true;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Libere-se o depósito recursal em favor do reclamante. Após, apure-se o remanescente devido.</p>`;
                        }

                        if (depsDetalhados.length > 0) {
                            const listaDeps = montarListaDepositos(depsDetalhados);
                            const listaBancos = montarListaBancos(depsDetalhados);

                            // Usar função unificada de liberação detalhada
                            houveLibecaoDetalhada = true;
                            gerarLiberacaoDetalhada({
                                depositoInfo: `o depósito recursal (${listaDeps} via ${listaBancos})`
                            });
                        }

                        if (!deveLiberarDeposito) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Por ora, não há liberação automática do depósito recursal informado.</p>`;
                        }
                    }
                }

                // PAGAMENTO ANTECIPADO - Substitui intimações completamente
                const isPagamentoAntecipado = $('chk-pag-antecipado').checked;
                if (isPagamentoAntecipado) {
                    const idPagAntecipado = $('pag-antecipado-id').value || '[ID]';
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada, #${bold(idPagAntecipado)}.</p>`;

                    // Usar função unificada de liberação detalhada
                    houveLibecaoDetalhada = true;
                    let proximoNum = gerarLiberacaoDetalhada({});

                    // Verificar tipo de liberação
                    const tipoLib = document.querySelector('input[name="lib-tipo"]:checked')?.value || 'nenhum';

                    if (tipoLib === 'devolucao') {
                        // Adicionar item de devolução
                        const valDev = $('lib-dev-valor').value || '[VALOR]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${proximoNum}) Devolva-se à reclamada o valor pago a maior, no montante de ${bold('R$ ' + valDev)}, expedindo-se o competente alvará.</p>`;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestação das partes.</p>`;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após, tornem conclusos para extinção da execução.</p>`;
                    } else if (tipoLib === 'remanescente') {
                        // Adicionar intimação de remanescente
                        const valRem = $('lib-rem-valor').value || '[VALOR]';
                        const tituloRem = $('lib-rem-titulo').value || '[TÍTULO]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem prejuízo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + valRem)} devidos a título de ${bold(tituloRem)}, em 15 dias, sob pena de execução.</p>`;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
                    } else {
                        // Padrão (nenhum)
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestações. Silentes, cumpra-se e, após, tornem conclusos para extinção da execução.</p>`;
                    }
                } else {
                    // INTIMAÇÕES (apenas se NÃO houver pagamento antecipado)
                    const formatarListaPartes = (nomes) => {
                        if (!nomes || nomes.length === 0) { return ''; }
                        if (nomes.length === 1) { return nomes[0]; }
                        if (nomes.length === 2) { return `${nomes[0]} e ${nomes[1]}`; }
                        return `${nomes.slice(0, -1).join(', ')} e ${nomes[nomes.length - 1]}`;
                    };

                    const elsOpcoes = document.querySelectorAll('.sel-modo-intimacao');
                    const grpDiario = [];
                    const grpMandado = [];
                    const grpEdital = [];

                    if (elsOpcoes.length > 0) {
                        elsOpcoes.forEach((sel) => {
                            const nome = sel.getAttribute('data-nome');
                            const v = sel.value;
                            if (v === 'diario') grpDiario.push(nome);
                            else if (v === 'mandado') grpMandado.push(nome);
                            else if (v === 'edital') grpEdital.push(nome);
                        });
                    } else {
                        const valManual = $('sel-intimacao-manual')?.value || 'diario';
                        const nomeManual = $('int-nome-parte-manual')?.value || '[RECLAMADA]';
                        if (valManual === 'diario') grpDiario.push(nomeManual);
                        else if (valManual === 'mandado') grpMandado.push(nomeManual);
                        else if (valManual === 'edital') grpEdital.push(nomeManual);
                    }

                    if (grpDiario.length > 0) {
                        const alvoComAdv = formatarListaPartes(grpDiario);
                        const verboComAdv = grpDiario.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        const patronoTxt = grpDiario.length > 1 ? 'seus patronos' : 'seu patrono';
                        const tipoValores = houveDepositoDireto ? 'valores remanescentes' : 'valores acima indicados';

                        if (houveDepositoDireto) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após referida atualização, ${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                        }
                    }

                    if (grpMandado.length > 0) {
                        const alvoMand = formatarListaPartes(grpMandado);
                        const verboMand = grpMandado.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboMand} ${bold(alvoMand)} para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora, expedindo-se o competente ${bold("mandado")}.</p>`;
                    }

                    if (grpEdital.length > 0) {
                        const alvoEdit = formatarListaPartes(grpEdital);
                        const verboEdit = grpEdital.length > 1 ? 'Citem-se as reclamadas' : 'Cite-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboEdit} ${bold(alvoEdit)}, por ${bold("edital")}, para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora.</p>`;
                    }
                }
            };

            const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
            const usarDuplicacao = $('resp-diversos').checked && linhasPeriodos.length > 0;

            if (usarDuplicacao && passivoTotal > 1) {
                const principalSelecionada = $('resp-devedora-principal')?.value || '1';
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A ${bold(principalSelecionada)} é devedora principal, as demais são subsidiárias.</p>`;

                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>A - A devedora principal, ${bold(principalSelecionada)}, deverá ainda:</strong></p>`;
                appendBaseAteAntesPericiais({ idCalculo: idPlanilha, usarPlaceholder: false });

                linhasPeriodos.forEach((linha, i) => {
                    const idx = linha.id.replace('periodo-diverso-', '');
                    const nomeSub = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || `[RECLAMADA ${i + 1}]`;
                    const idSub = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || `[ID ${i + 1}]`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${String.fromCharCode(66 + i)} - Já em relação à reclamada subsidiária ${bold(nomeSub)}:</strong></p>`;
                    appendBaseAteAntesPericiais({ idCalculo: idSub, usarPlaceholder: true });
                });

                appendDisposicoesFinais();
            } else {
                let introTxt = '';
                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idPlanilha)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idPlanilha)}), `;
                }
                if (isFgtsSep) {
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)} relativo ao principal, e ${bold('R$' + valFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(valData)}. `;
                } else {
                    introTxt += `fixando o crédito em ${bold('R$' + valCredito)}, referente ao valor principal, atualizado para ${bold(valData)}. `;
                }
                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualização foi feita na forma da Lei 14.905/2024 e da decisão da SDI-1 do C. TST (IPCA-E até a distribuição; taxa Selic até 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A correção monetária foi realizada pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = $('val-juros').value || '[JUROS]';
                    const dtIngresso = $('data-ingresso').value || '[DATA INGRESSO]';
                    introTxt += `Atualizáveis pela TR/IPCA-E, conforme sentença. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;
                if (passivoTotal > 1) {
                    if ($('resp-tipo').value === 'solidarias') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Declaro que as reclamadas respondem de forma solidária pela presente execução.</p>`;
                    } else if ($('resp-tipo').value === 'subsidiarias') {
                        if ($('resp-integral').checked) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A primeira reclamada é devedora principal, as demais são subsidiárias pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pela primeira.</p>`;
                        }
                    }
                }
                if ($('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }
                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}.</p>`;
                }
                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }
                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                    if (rdHonReu === 'suspensiva') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                    } else {
                        const p = $('val-hon-reu-perc').value;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}.</p>`;
                    }
                }
                appendDisposicoesFinais();
            }

            // Linha final - OMITIR se houver liberação detalhada (depósito recursal ou pagamento antecipado)
            if (!houveLibecaoDetalhada) {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${u('Ficam as partes cientes de que qualquer questionamento acerca desta decisão, salvo erro material, será apreciado após a garantia do juízo.')}</p>`;
            }
            const blob = new Blob([text], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            navigator.clipboard.write([clipboardItem]).then(() => {
                alert('Decisão copiada com sucesso! Vá ao editor do PJe e cole (Ctrl+V).');
                $('homologacao-overlay').style.display = 'none';
                dbg('Decisao copiada para area de transferencia com sucesso.');
            }).catch((err) => {
                alert('Erro ao copiar. O navegador pode ter bloqueado.');
                console.error(err);
                err('Falha ao copiar decisao para clipboard:', err);
            });
        };

        dbg('initializeOverlay finalizado com sucesso.');
    }

    if (document.readyState === 'loading') {
        dbg('Documento em loading, aguardando DOMContentLoaded para iniciar overlay.');
        document.addEventListener('DOMContentLoaded', () => {
            try {
                initializeOverlay();
            } catch (e) {
                err('Erro ao iniciar overlay no DOMContentLoaded:', e);
            }
        }, { once: true });
    } else {
        dbg('Documento ja pronto, iniciando overlay imediatamente.');
        try {
            initializeOverlay();
        } catch (e) {
            err('Erro ao iniciar overlay imediatamente:', e);
        }
    }
})();
