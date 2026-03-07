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
(function() {
    'use strict';
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
    // Centraliza todas as vari├íveis de estado do script
    // Permite dispose() completo para evitar vazamentos de mem├│ria
    if (!window.hcalcState) {
        window.hcalcState = {
            // Cache de partes (limitado a 5 entradas)
            calcPartesCache: {},

            // Flags de execu├º├úo
            prepRunning: false,

            // Resultados do prep
            prepResult: null,
            timelineData: null,

            // Dados detectados
            peritosConhecimento: [],
            partesData: null,

            // AbortController para cancelamento de opera├º├Áes
            abortController: null,

            // FASE 1: Dados da planilha PJe-Calc (extra├º├úo PDF)
            planilhaExtracaoData: null,  // {verbas, fgts, inss, data, id, ...}
            planilhaCarregada: false,
            pdfjsLoaded: false,

            // FASE 2: M├║ltiplos dep├│sitos
            depositosRecursais: [],  // [{idx, tipo, depositante, id, isPrincipal, liberacao}]
            pagamentosAntecipados: [],  // [{idx, id, tipoLib, remValor, remTitulo, devValor}]
            nextDepositoIdx: 0,
            nextPagamentoIdx: 0,

            // FASE 3: Planilhas extras para per├¡odos diversos
            planilhasDisponiveis: [],  // [{id, label, dados}]

            // M├®todo de limpeza completa
            dispose() {
                dbg('Executando dispose() - limpando estado hcalc');

                // Abortar opera├º├Áes em andamento
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
                this.planilhaExtracaoData = null;
                this.planilhaCarregada = false;
                this.planilhasDisponiveis = [];
                this.depositosRecursais = [];
                this.pagamentosAntecipados = [];
                this.nextDepositoIdx = 0;
                this.nextPagamentoIdx = 0;
                if (this._pdfWorkerUrl) {
                    URL.revokeObjectURL(this._pdfWorkerUrl);
                    this._pdfWorkerUrl = null;
                }
                dbg('Estado hcalc limpo');
            },

            // M├®todo de reset parcial (mant├®m cache)
            resetPrep() {
                // Abortar prep em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.prepResult = null;
                this.timelineData = null;
                this.prepRunning = false;
                this.planilhaExtracaoData = null;
                this.planilhaCarregada = false;
            }
        };
    }

    // Aliases de retrocompatibilidade (apontam para hcalcState)
    // Permite que c├│digo existente continue funcionando sem modifica├º├úo
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
    // MONITOR DE NAVEGA├ç├âO SPA
    // ==========================================
    // Detecta mudan├ºa de URL no PJe (SPA) e limpa estado automaticamente
    // Previne vazamento de mem├│ria ao trocar de processo sem fechar overlay
    // OTIMIZA├ç├âO: History API hooks ao inv├®s de MutationObserver pesado
    let lastUrl = location.href;

    function handleSpaNavigation() {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            dbg('Navega├º├úo SPA detectada, limpando estado...');

            // Dispose completo
            if (window.hcalcState) {
                window.hcalcState.dispose();
            }

            // Ocultar overlay se estiver aberto
            const overlay = document.getElementById('homologacao-overlay');
            if (overlay) overlay.style.display = 'none';
        }
    }

    // Intercepta pushState (navega├º├úo program├ítica Angular)
    const _pushState = history.pushState.bind(history);
    history.pushState = function(...args) {
        _pushState(...args);
        handleSpaNavigation();
    };

    // Intercepta popstate (bot├úo voltar/avan├ºar)
    window.addEventListener('popstate', handleSpaNavigation);


    // prep.js ÔÇö Prepara├º├úo pr├®-overlay para hcalc.js
    // Varre timeline, extrai dados da senten├ºa, cruza peritos com AJ-JT, monta dep├│sitos.
    // Uso: const result = await window.executarPrep(partesData, peritosConhecimento);

    // (IIFE removida para escopo ├║nico)

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
        // Padr├úo: "17 nov. 2025" ou "17 nov 2025"
        const match = dataStr.match(/(\d{1,2})\s+(\w{3})\.?\s+(\d{4})/);
        if (match) {
            const dia = match[1].padStart(2, '0');
            const mes = meses[match[2].toLowerCase()] || '00';
            const ano = match[3];
            return `${dia}/${mes}/${ano}`;
        }
        return dataStr; // Retorna original se n├úo reconhecer
    }

    // Destaca um elemento na timeline (usado por links de recursos)
    function destacarElementoNaTimeline(href) {
        try {
            // Tentar encontrar o elemento pelo href
            const link = document.querySelector(`a[href="${href}"]`);
            if (!link) {
                console.warn('[hcalc] Elemento n├úo encontrado na timeline:', href);
                return;
            }

            // Encontrar o container do item na timeline
            let container = link.closest('li.tl-item-container') ||
                           link.closest('.tl-item-container') ||
                           link.closest('.timeline-item');
           
            if (!container) {
                console.warn('[hcalc] Container do item n├úo encontrado');
                return;
            }

            // Scroll suave at├® o elemento
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Salvar estilo original
            const originalBorder = container.style.border;
            const originalBackground = container.style.background;
            const originalTransition = container.style.transition;

            // Aplicar destaque
            container.style.transition = 'all 0.3s ease';
            container.style.border = '2px solid #fbbf24';
            container.style.background = '#fffbeb';

            // Remover destaque ap├│s 3 segundos
            setTimeout(() => {
                container.style.transition = 'all 0.5s ease';
                container.style.border = originalBorder;
                container.style.background = originalBackground;
               
                // Restaurar transition original ap├│s anima├º├úo
                setTimeout(() => {
                    container.style.transition = originalTransition;
                }, 500);
            }, 3000);

            console.log('[hcalc] Elemento destacado na timeline:', href);
        } catch (error) {
            console.error('[hcalc] Erro ao destacar elemento:', error);
        }
    }

    // ==========================================
    // TIMELINE: VARREDURA ├ÜNICA
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
        const m = ariaLabel.match(/T├¡tulo:\s*\(([^)]+)\)/i);
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
       
        // ESTRAT├ëGIA PRINCIPAL: aria-label do ├¡cone do polo
        const seletores = [
            'div[name="tipoItemTimeline"][aria-label]',
            '[name="tipoItemTimeline"][aria-label]',
            'div.tl-icon[aria-label]',
            '[role="img"][aria-label]'
        ];
       
        for (const sel of seletores) {
            const elemento = container.querySelector(sel);
            if (elemento) {
                const ariaLabel = elemento.getAttribute('aria-label')?.trim();
                if (ariaLabel && ariaLabel.length > 3) {
                    if (!ariaLabel.toLowerCase().includes('advogado') &&
                        !ariaLabel.toLowerCase().includes('tipo do documento')) {
                        return ariaLabel;
                    }
                }
            }
        }
       
        // FALLBACK rec.js v1.0: extrair do texto do documento
        const textoDoc = textoDoItem(item);
        const matchEmpresa = textoDoc.match(/^([^-:\n]+)/);
        if (matchEmpresa && matchEmpresa[1].trim().length > 10) {
            const nomeExtraido = matchEmpresa[1].trim();
            if (!/^(recurso|ordin├írio|revista|ro|rr|documento)$/i.test(nomeExtraido)) {
                return nomeExtraido;
            }
        }
       
        return 'Reclamada n├úo identificada';
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

    // Varredura ├║nica: classifica todos os items da timeline
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

            // Senten├ºa
            if (textoNorm.includes('sentenca') || textoNorm.includes('senten├ºa')) {
                resultado.sentencas.push({ ...base, tipo: 'sentenca' });
                return;
            }

            // Ac├│rd├úo - CAPTURA ID
            if (textoNorm.includes('acordao') && !textoNorm.includes('intima')) {
                const idDoc = idDocumentoDoItem(item);
                resultado.acordaos.push({ ...base, id: idDoc, tipo: 'acordao' });
                return;
            }

            // Recurso Ordin├írio / Recurso de Revista (polo passivo + anexo)
            if ((tipoDoc === 'recurso ordinario' || tipoDoc === 'recurso de revista'
                || tipoDoc.includes('recurso ordinario') || tipoDoc.includes('recurso de revista'))
                && isPoloPassivoNoItem(item) && hasAnexoNoItem(item)) {
                const tipoRec = tipoDoc.includes('revista') ? 'RR' : 'RO';
                const depositante = nomePassivoDoItem(item);
                resultado.recursosPassivo.push({ ...base, tipoRec, depositante, _itemRef: item });
                return;
            }

            // Honor├írios Periciais AJ-JT - CAPTURA ID
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

        // Senten├ºa alvo = mais antiga (├║ltima no array, pois timeline ├® desc)
        return resultado;
    }

    // ==========================================
    // EXTRA├ç├âO VIA HTML ORIGINAL
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

    // Recaptura elemento da timeline pelo href (evita guardar refer├¬ncias DOM)
    function encontrarItemTimeline(href) {
        if (!href) return null;
        const items = getTimelineItems();
        for (const item of items) {
            const link = item.querySelector('a.tl-documento[target="_blank"]');
            if (link && link.href === href) return item;
        }
        return null;
    }

    // ========== INTEGRADO DE rec.js v1.0 ==========
   
    // Classifica├º├úo por tipo de anexo
    function classificarAnexo(textoAnexo) {
        const t = textoAnexo.toLowerCase();
        if (/dep├│sito|deposito|preparo/.test(t)) return { tipo: 'Dep├│sito', ordem: 1 };
        if (/garantia|seguro|susep/.test(t)) return { tipo: 'Garantia', ordem: 2 };
        if (/gru|custas/.test(t)) return { tipo: 'Custas', ordem: 3 };
        return { tipo: 'Anexo', ordem: 4 };
    }

    // Expande anexos e retorna lista estruturada
    async function extrairAnexosDoItem(item) {
        const anexos = [];
        try {
            const anexosRoot = item.querySelector('pje-timeline-anexos');
            if (!anexosRoot) return anexos;
           
            const toggle = anexosRoot.querySelector('div[name="mostrarOuOcultarAnexos"]');
            let anexoLinks = anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]');
           
            if ((!anexoLinks || anexoLinks.length === 0) && toggle) {
                try { toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); } catch(e) {}
                await sleep(350);
                anexoLinks = anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]');
            }
           
            if (anexoLinks && anexoLinks.length) {
                Array.from(anexoLinks).forEach(anexo => {
                    const texto = (anexo.textContent || '').trim();
                    let id = '';
                    const match = texto.match(/\s-\s([a-f0-9]{7})\s*$/i);
                    if (match) {
                        id = match[1];
                    } else {
                        id = anexo.id || anexo.getAttribute('id') || '';
                    }
                    const { tipo, ordem } = classificarAnexo(texto);
                    anexos.push({ texto, id, tipo, ordem, elemento: anexo });
                });
                anexos.sort((a, b) => a.ordem - b.ordem);
            }
        } catch (error) {
            err('Erro ao extrair anexos:', error);
        }
        return anexos;
    }

    // Expande o toggle de anexos se n├úo estiver expandido
    async function expandirAnexos(container) {
        try {
            const anexosRoot = container.querySelector('pje-timeline-anexos');
            if (!anexosRoot) return false;
           
            const toggle = anexosRoot.querySelector('div[name="mostrarOuOcultarAnexos"]');
            if (!toggle) return false;
           
            const jaExpandido = toggle.getAttribute('aria-pressed') === 'true';
            if (jaExpandido) return true;
           
            toggle.click();
            await sleep(400);
            return true;
        } catch (error) {
            err('Erro ao expandir anexos:', error);
            return false;
        }
    }

    // Destaca elemento na timeline (recebe href, localiza e aplica visual)
    function destacarElementoNaTimeline(href) {
        const container = encontrarItemTimeline(href);
        if (!container) {
            warn('Elemento n├úo encontrado para href:', href);
            return;
        }
        try {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
           
            const originalBorder = container.style.border;
            const originalBackground = container.style.background;
            const originalTransition = container.style.transition;
           
            container.style.transition = 'all 0.3s ease';
            container.style.border = '2px solid #fbbf24';
            container.style.background = '#fffbeb';
           
            // Expandir anexos ap├│s scroll completar
            setTimeout(async () => { await expandirAnexos(container); }, 500);
           
            // Remover destaque ap├│s 3s
            setTimeout(() => {
                container.style.transition = 'all 0.5s ease';
                container.style.border = originalBorder;
                container.style.background = originalBackground;
                setTimeout(() => { container.style.transition = originalTransition; }, 500);
            }, 3000);
        } catch (error) {
            err('Erro ao destacar elemento:', error);
        }
    }

    // Abre documento inline via href (recaptura elemento dinamicamente)
    function abrirDocumentoInlineViaHref(href) {
        const item = encontrarItemTimeline(href);
        if (!item) return false;
        abrirDocumentoInline(item);
        return true;
    }

    // Clica em "Visualizar HTML original" e l├¬ #previewModeloDocumento
    async function lerHtmlOriginal(timeoutMs = 5000, abortSignal = null) {
        const started = Date.now();

        // 1. Espera o bot├úo aparecer (com suporte a cancelamento)
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

        // 2. Espera o conte├║do carregar (com suporte a cancelamento)
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
    // EXTRA├ç├âO DE DADOS DA SENTEN├çA
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

        // Custas: padr├úo amplo com flexibilidade para "m├¡nimo", "m├íximo", "total", etc.
        // Aceita: "no importe [m├¡nimo/m├íximo/total] de R$ X, calculadas sobre"
        // ou "Custas, pela Reclamada, no importe de R$ 300,00"
        // ou "Custas de R$ 200,00"
        const custasMatch = texto.match(
            /no\s+importe\s+(?:m[i├¡]nim[oa]\s+|m[├ía]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+),?\s*calculadas\s+sobre/i
        ) || texto.match(
            /[Cc]ustas[^,]*,\s*(?:pela\s+)?[Rr]eclamad[ao][^,]*,\s*no\s+importe\s+(?:m[i├¡]nim[oa]\s+|m[├ía]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+)/i
        ) || texto.match(
            /[Cc]ustas[^,]*de\s+R\$\s*([\d.,]+)/i
        );
        if (custasMatch) {
            // Remove v├¡rgulas/pontos extras no final
            result.custas = custasMatch[1].replace(/[.,]+$/, '');
        }

        // Condi├º├úo suspensiva
        result.hsusp = /obriga[c├º][a├ú]o\s+ficar[a├í]\s+sob\s+condi[c├º][a├ú]o\s+suspensiva/i.test(texto);

        // Per├¡cia TRT engenharia
        result.trteng = /honor[a├í]rios\s+periciais\s+t[e├®]cnicos.*pagos\s+pelo\s+Tribunal/i.test(texto)
            || /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+t[e├®]cnicos/i.test(texto);

        // Per├¡cia TRT m├®dica
        result.trtmed = /honor[a├í]rios\s+periciais\s+m[e├®]dicos.*pagos\s+pelo\s+Tribunal/i.test(texto)
            || /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+m[e├®]dicos/i.test(texto);

        // Responsabilidade
        if (/condenar\s+(de\s+forma\s+)?subsidi[a├í]ri/i.test(texto)) {
            result.responsabilidade = 'subsidiaria';
        } else if (/condenar\s+(de\s+forma\s+)?solid[a├í]ri/i.test(texto)) {
            result.responsabilidade = 'solidaria';
        }

        // Honor├írios periciais: buscar todos os trechos com valor + se ├® TRT
        // Padr├úo: "honor├írios periciais ... em R$ 800,00 ... pagos pelo Tribunal"
        const regexHon = /honor[a├í]rios\s+periciais[^.]*?R\$\s*([\d.,]+)[^.]*?\./gi;
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
    // CRUZAMENTO AJ-JT ├ù PERITOS
    // ==========================================
    async function buscarAjJtPeritos(honAjJtItems, peritosConhecimento) {
        const resultados = []; // { nome, trt: true, idAjJt }

        // Set de peritos j├í encontrados ÔÇö evita abrir mais docs desnecess├írios
        const peritosEncontrados = new Set();

        for (const ajjt of honAjJtItems) {
            // Se todos os peritos j├í foram encontrados, para
            if (peritosEncontrados.size >= peritosConhecimento.length) break;

            // Abre documento via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(ajjt.href)) {
                console.warn('[prep] Falha ao abrir AJ-JT:', ajjt.href);
                continue;
            }
            await sleep(600);

            // L├¬ HTML original
            const resHtml = await lerHtmlOriginal(5000);
            fecharViewer();
            await sleep(300);

            if (!resHtml || !resHtml.texto) continue;

            const textoNorm = normalizeText(resHtml.texto);

            // Procura cada perito de conhecimento no texto
            for (const perito of peritosConhecimento) {
                if (peritosEncontrados.has(perito)) continue;

                const peritoNorm = normalizeText(perito);
                // Match parcial: primeiro nome + ├║ltimo nome
                const partes = peritoNorm.split(/\s+/).filter(Boolean);
                const primeiroNome = partes[0] || '';
                const ultimoNome = partes.length > 1 ? partes[partes.length - 1] : '';

                const found = textoNorm.includes(peritoNorm)
                    || (primeiroNome && ultimoNome && textoNorm.includes(primeiroNome) && textoNorm.includes(ultimoNome));

                if (found) {
                    // Usar ID j├í extra├¡do da timeline
                    const idAjJt = ajjt.id || ajjt.texto;

                    resultados.push({ nome: perito, trt: true, idAjJt });
                    peritosEncontrados.add(perito);
                }
            }
        }

        return resultados;
    }

    // ==========================================
    // NOTIFICA├ç├òES EDITAL
    // ==========================================
    async function buscarPartesEdital(editaisItems, passivo) {
        // Regra maior: se h├í apenas uma reclamada e h├í edital, ├® ela.
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
        // FLAG ANTI-EXECU├ç├âO-DUPLA: Previne loops de polling acumulando timers
        if (window.hcalcPrepRunning) {
            console.log('[prep.js] ÔÜá´©Å Prep j├í em execu├º├úo, ignorando chamada duplicada');
            return;
        }

        // Abortar prep anterior se existir
        if (window.hcalcState.abortController) {
            dbg('[prep] Abortando execu├º├úo anterior antes de iniciar nova');
            window.hcalcState.abortController.abort();
        }

        // Criar novo AbortController para esta execu├º├úo
        window.hcalcState.abortController = new AbortController();
        const signal = window.hcalcState.abortController.signal;

        window.hcalcPrepRunning = true;

        try {
            console.log('[prep.js] Iniciando prepara├º├úo pr├®-overlay...');
            const partesSafe = partesData && typeof partesData === 'object' ? partesData : {};

        // Resultado padr├úo
        const prepResult = {
            sentenca: {
                data: null,
                href: null,
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

        // ÔöÇÔöÇ ETAPA 1: Varrer timeline (s├¡ncrona) ÔöÇÔöÇ
        const timeline = varrerTimeline();
        console.log('[prep.js] Timeline varrida:', {
            sentencas: timeline.sentencas.length,
            acordaos: timeline.acordaos.length,
            editais: timeline.editais.length,
            recursosPassivo: timeline.recursosPassivo.length,
            honAjJt: timeline.honAjJt.length
        });

        // ÔöÇÔöÇ ETAPA 1.5: Enriquecer recursos com anexos (integrado rec.js) ÔöÇÔöÇ
        if (timeline.recursosPassivo.length > 0) {
            dbg('prep', 'Extraindo anexos de', timeline.recursosPassivo.length, 'recursos...');
            for (const rec of timeline.recursosPassivo) {
                if (rec._itemRef) {
                    rec.anexos = await extrairAnexosDoItem(rec._itemRef);
                    delete rec._itemRef;
                } else {
                    rec.anexos = [];
                }
            }
            dbg('prep', 'Anexos extra├¡dos');
        }
        // Garantir limpeza de _itemRef mesmo se n├úo processou
        timeline.recursosPassivo.forEach(r => { delete r._itemRef; });

        // Mapear ac├│rd├úos e editais para resultado
        prepResult.acordaos = timeline.acordaos.map(a => ({ data: a.data, href: a.href, id: a.id }));
        prepResult.editais = timeline.editais.map(e => ({ data: e.data, href: e.href }));

        // Dep├│sitos recursais = recursos passivo (s├│ se tem ac├│rd├úo)
        if (timeline.acordaos.length > 0) {
            prepResult.depositos = timeline.recursosPassivo.map(r => ({
                tipo: r.tipoRec,
                texto: r.texto,
                href: r.href,
                data: r.data,
                depositante: r.depositante || '',
                anexos: r.anexos || []
            }));
        }

        // ÔöÇÔöÇ ETAPA 2: AJ-JT ÔÇö s├│ se tem perito de conhecimento ÔöÇÔöÇ
        // ORDEM INVERTIDA: AJ-JT antes de senten├ºa para manter senten├ºa selecionada
        const peritosConh = Array.isArray(peritosConhecimento) ? peritosConhecimento.filter(Boolean) : [];

        if (peritosConh.length > 0 && timeline.honAjJt.length > 0) {
            console.log('[prep.js] Buscando AJ-JT para peritos:', peritosConh);
            prepResult.pericia.peritosComAjJt = await buscarAjJtPeritos(timeline.honAjJt, peritosConh);
            console.log('[prep.js] AJ-JT encontrados:', prepResult.pericia.peritosComAjJt);
        } else if (peritosConh.length > 0) {
            console.log('[prep.js] Peritos de conhecimento detectados mas nenhum AJ-JT na timeline.');
        }

        // ÔöÇÔöÇ ETAPA 3: Senten├ºa ÔÇö abrir e extrair tudo ÔöÇÔöÇ
        // MOVIDO PARA DEPOIS DE AJ-JT para ficar selecionada por ├║ltimo
        const sentencaAlvo = timeline.sentencas.length > 0
            ? timeline.sentencas[timeline.sentencas.length - 1]  // mais antiga (├║ltima no array)
            : null;

        if (sentencaAlvo) {
            prepResult.sentenca.data = sentencaAlvo.data;
            prepResult.sentenca.href = sentencaAlvo.href;

            // Abrir documento via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(sentencaAlvo.href)) {
                console.warn('[prep] Falha ao abrir senten├ºa:', sentencaAlvo.href);
            } else {
                await sleep(600);

                // Ler HTML original
                const resSent = await lerHtmlOriginal(6000, signal);
                fecharViewer();
                await sleep(300);

                if (resSent && resSent.texto) {
                    const textoSentenca = resSent.texto;
                    console.log('[prep.js] Senten├ºa lida:', textoSentenca.length, 'chars');

                    const dados = extrairDadosSentenca(textoSentenca);
                    prepResult.sentenca.custas = dados.custas;
                    prepResult.sentenca.hsusp = dados.hsusp;
                    prepResult.sentenca.responsabilidade = dados.responsabilidade;
                    prepResult.sentenca.honorariosPericiais = dados.honorariosPericiais;
                    prepResult.pericia.trteng = dados.trteng;
                    prepResult.pericia.trtmed = dados.trtmed;
                } else {
                    console.warn('[prep.js] Falha ao ler senten├ºa via HTML original.');
                }
            }
        } else {
            console.warn('[prep.js] Nenhuma senten├ºa encontrada na timeline.');
        }

        // ÔöÇÔöÇ ETAPA 4: EDITAL ÔÇö extrair partes intimadas ÔöÇÔöÇ
        const passivoArray = Array.isArray(partesSafe.passivo) ? partesSafe.passivo : [];
        if (timeline.editais.length > 0 && passivoArray.length > 0) {
            console.log('[prep.js] Buscando partes intimadas nos editais...');
            prepResult.partesIntimadasEdital = await buscarPartesEdital(timeline.editais, passivoArray);
            console.log('[prep.js] Partes intimadas por edital:', prepResult.partesIntimadasEdital);
        }

        console.log('[prep.js] Prepara├º├úo conclu├¡da:', prepResult);

        // Disponibilizar globalmente
        window.hcalcPrepResult = prepResult;

        // Liberar flag de execu├º├úo
        window.hcalcPrepRunning = false;

        return prepResult;

        } catch (error) {
            console.error('[prep.js] Erro durante prepara├º├úo:', error);
            // Garantir que flag seja liberada mesmo em caso de erro
            window.hcalcPrepRunning = false;
            throw error;
        }
    }

    // Expor prep no escopo global para integra├º├úo/depura├º├úo.
    const prepGlobalObj = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    prepGlobalObj.executarPrep = executarPrep;
    if (prepGlobalObj !== window) {
        window.executarPrep = executarPrep;
    }
    window.destacarElementoNaTimeline = destacarElementoNaTimeline;
    window.encontrarItemTimeline       = encontrarItemTimeline;
    window.expandirAnexos              = expandirAnexos;

    // Fim prep (agora global no escopo do arquivo)


    // ==========================================
    // ESTRAT├ëGIA 4: LAZY INIT ÔÇö Fase A (leve)
    // Injeta apenas o bot├úo (~200 bytes CSS). Todo o overlay ├® criado no primeiro clique.

    // window.executarPrep ja exposta no corpo acima
})();


// ── hcalc-pdf.js ──────────────────────────────────
(function() {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg  = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err  = (...args) => console.error('[hcalc]', ...args);
    // ==========================================
    // EXTRA├ç├âO DE PLANILHA PJE-CALC (FASE 1)
    // ==========================================
    // PDF.js carregado via @require (s├│ executa se abrir p├ígina PJe)
    // Worker configurado sob demanda (primeira vez que processar PDF)

    function carregarPDFJSSeNecessario() {
        // Estrat├®gia 3: PDF.js carrega dentro do Worker via importScripts.
        // Main thread n├úo precisa do pdfjsLib ÔÇö sempre retorna true.
        return true;
    }

    // ==========================================
    // VALIDA├ç├âO DE DADOS EXTRA├ìDOS (FASE 2)
    // ==========================================
   
    // Fun├º├úo utilit├íria para normalizar nomes (compara├º├úo de peritos/advogados)
    function normalizarNomeParaComparacao(nome) {
        if (!nome) return '';
        // Remove acentos, pontos, transforma em mai├║sculas para compara├º├úo
        return nome.normalize('NFD')
                   .replace(/[\u0300-\u036f]/g, '')
                   .replace(/[.]/g, '')
                   .toUpperCase()
                   .trim();
    }
   
    function validarValor(valor) {
        if (!valor || valor === '0,00') return false;
        // Formato v├ílido: 1.234,56 ou 123,45 ou 1,23
        const regex = /^\d{1,3}(\.\d{3})*,\d{2}$/;
        return regex.test(valor);
    }

    function validarData(data) {
        if (!data) return false;
        const match = data.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (!match) return false;
       
        const dia = parseInt(match[1]);
        const mes = parseInt(match[2]);
        const ano = parseInt(match[3]);
       
        // Valida├º├Áes b├ísicas
        if (mes < 1 || mes > 12) return false;
        if (dia < 1 || dia > 31) return false;
        if (ano < 2020 || ano > 2030) return false; // Range razo├ível para planilhas
       
        return true;
    }

    function calcularQualidadeExtracao(dados) {
        const campos = [
            { nome: 'idPlanilha', label: 'ID', validar: (v) => v && v.length > 3 },
            { nome: 'verbas', label: 'Cr├®dito', validar: validarValor },
            { nome: 'fgts', label: 'FGTS', validar: (v) => !v || v === '0,00' || validarValor(v) }, // Opcional
            { nome: 'inssTotal', label: 'INSS Total', validar: validarValor },
            { nome: 'inssAutor', label: 'INSS Rec', validar: (v) => !v || v === '0,00' || validarValor(v) }, // Opcional
            { nome: 'custas', label: 'Custas', validar: (v) => !v || v === '0,00' || validarValor(v) }, // Opcional
            { nome: 'dataAtualizacao', label: 'Data', validar: validarData }
        ];
       
        let extraidos = 0;
        let validos = 0;
        const faltando = [];
        const invalidos = [];
       
        campos.forEach(campo => {
            const valor = dados[campo.nome];
            const temValor = valor && valor !== '' && valor !== '0,00';
           
            if (temValor) {
                extraidos++;
                if (campo.validar(valor)) {
                    validos++;
                } else {
                    invalidos.push({ campo: campo.label, valor });
                }
            } else if (campo.nome === 'verbas' || campo.nome === 'idPlanilha' || campo.nome === 'dataAtualizacao') {
                // Campos obrigat├│rios
                faltando.push(campo.label);
            }
        });
       
        return {
            percentual: Math.round((validos / campos.length) * 100),
            extraidos,
            validos,
            total: campos.length,
            faltando,
            invalidos
        };
    }

    function validarDadosExtraidos(dados) {
        // Validar formatos
        if (dados.verbas && !validarValor(dados.verbas)) {
            warn('Valor de cr├®dito com formato suspeito:', dados.verbas);
            dados._avisoCredito = true;
        }
       
        if (dados.fgts && dados.fgts !== '0,00' && !validarValor(dados.fgts)) {
            warn('Valor de FGTS com formato suspeito:', dados.fgts);
            dados._avisoFgts = true;
        }
       
        if (dados.dataAtualizacao && !validarData(dados.dataAtualizacao)) {
            warn('Data extra├¡da inv├ílida:', dados.dataAtualizacao);
            dados._avisoData = true;
        }
       
        return dados;
    }

    // ==========================================
    // ESTRAT├ëGIA 3: WEB WORKER PDF
    // PDF.js roda em Worker isolado ÔÇö zero bloqueio no thread principal.
    // ==========================================

    function criarPdfWorkerBlob() {
        const workerCode = `
importScripts('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js');
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

function normalizarNome(nome) {
    if (!nome) return '';
    return nome.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').replace(/[.]/g, '').toUpperCase().trim();
}

async function extrair(arrayBuffer, idNomeArquivo, peritosConhecidos) {
    var pdf = null; var page = null;
    try {
        var task = pdfjsLib.getDocument({ data: arrayBuffer });
        pdf = await task.promise;
        page = await pdf.getPage(1);
        var tc = await page.getTextContent();
        var txt = tc.items.map(function(i) { return i.str.trim(); }).filter(function(s) { return s !== ''; }).join(' ');

        var regexVerbas    = /VERBAS\\s+([\\d.,]+)/i;
        var regexFGTS      = /VERBAS\\s+[\\d.,]+\\s+FGTS\\s+([\\d.,]+)/i;
        var regexDepFGTS   = /DEP[O├ô]SITO FGTS\\s*[.,]?\\s*([\\d.,]+)/i;
        var regexINSSTotal = /CONTRIBUI├ç├âO SOCIAL SOBRE SAL├üRIOS DEVIDOS\\s+([\\d.,]+)/i;
        var regexINSSAutor = /DEDU├ç├âO DE CONTRIBUI├ç├âO SOCIAL\\s+(?:\\(\\s*)?([\\d.,]+)(?:\\s*\\))?/i;
        var regexCustas    = /CUSTAS JUDICIAIS DEVIDAS PELO RECLAMADO\\s+([\\d.,]+)/i;
        var regexData      = /(?:Data\\s+Liquida[├ºc][├úa]o\\s*[:\\-]?\\s*(\\d{2}\\/\\d{2}\\/\\d{4}))|(?:(\\d{2}\\/\\d{2}\\/\\d{4})\\s*Data\\s+Liquida[├ºc][├úa]o)/i;
        var regexDataFB    = /([0-3][0-9]\\/[0-1][0-9]\\/20[2-9][0-9])\\s+[A-Z├Ç-┼©\\s]+Data\\s+Liquida[├ºc][├úa]o/i;
        var regexIdAssin   = /Documento assinado eletronicamente[\\s\\S]*?-\\s*([a-zA-Z0-9]+)(?:\\s|$)/i;
        var regexHonAutor  = /HONOR├üRIOS L├ìQUIDOS PARA PATRONO DO RECLAMANTE\\s+([\\d.,]+)/i;
        var regexHonPerito = /HONOR├üRIOS L├ìQUIDOS PARA\\s+(?!PATRONO DO RECLAMANTE)(.+?)\\s+([\\d.,]{3,})/i;
        var regexPeriodo   = /(\\d{2}[/]?\\d{2}[/]?\\d{4})\\s+a\\s+(\\d{2}[/]?\\d{2}[/]?\\d{4})/;
        var regexIRPF      = /IRPF\\s+DEVIDO\\s+PELO\\s+RECLAMANTE\\s+([\\d.,]+)/i;

        var verbas    = (txt.match(regexVerbas)    || [])[1] || '';
        var fgts      = (txt.match(regexFGTS)      || [])[1] || '';
        var inssTotal = (txt.match(regexINSSTotal)  || [])[1] || '';
        var inssAutor = (txt.match(regexINSSAutor)  || [])[1] || '';
        var custas    = (txt.match(regexCustas)     || [])[1] || '';
        var honAutor  = (txt.match(regexHonAutor)   || [])[1] || '';
        var mPerito   = txt.match(regexHonPerito);
        var peritoNome  = mPerito ? mPerito[1].trim() : '';
        var peritoValor = mPerito ? mPerito[2] : '';

        if (peritoNome && peritoValor && peritosConhecidos && peritosConhecidos.length) {
            var ehPerito = peritosConhecidos.some(function(p) {
                return normalizarNome(p).includes(normalizarNome(peritoNome)) ||
                       normalizarNome(peritoNome).includes(normalizarNome(p));
            });
            if (!ehPerito) { honAutor = peritoValor; peritoNome = ''; peritoValor = ''; }
        }

        var dataAtualizacao = (txt.match(regexData) || [])[1] || (txt.match(regexData) || [])[2];
        if (!dataAtualizacao) { var fb = txt.match(regexDataFB); if (fb) dataAtualizacao = fb[1]; }

        var idPlanilha = idNomeArquivo || (txt.match(regexIdAssin) || [])[1] || '';
        var pm = txt.match(regexPeriodo);
        var periodoCalculo = null;
        if (pm) {
            var fmt = function(s) { return s.indexOf('/') !== -1 ? s : s.substr(0,2)+'/'+s.substr(2,2)+'/'+s.substr(4,4); };
            periodoCalculo = fmt(pm[1]) + ' a ' + fmt(pm[2]);
        }
        var irpfM = txt.match(regexIRPF);
        var irpfIsento = !irpfM || parseFloat(irpfM[1].replace(/\\./g,'').replace(',','.')) === 0;
        var fgtsDepositado = false;
        if (fgts) { var mDep = txt.match(regexDepFGTS); if (mDep && mDep[1]) fgtsDepositado = fgts.replace(/[\\.,]/g,'') === mDep[1].replace(/[\\.,]/g,''); }

        return { sucesso: true, verbas, fgts, fgtsDepositado, inssTotal, inssAutor, custas,
                 dataAtualizacao, idPlanilha, honAutor, peritoNome, peritoValor, periodoCalculo, irpfIsento };
    } catch(e) {
        return { sucesso: false, erro: e.message };
    } finally {
        try { if (page) page.cleanup(); } catch(e) {}
        try { if (pdf) await pdf.destroy(); } catch(e) {}
    }
}

self.onmessage = async function(e) {
    var d = e.data;
    var resultado = await extrair(d.arrayBuffer, d.idNomeArquivo, d.peritosConhecidos);
    self.postMessage(resultado);
};
`;
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        return URL.createObjectURL(blob);
    }

    // Placeholder para compatibilidade com hcalc-overlay.js
    async function extrairDadosPlanilha(arrayBuffer, idNomeArquivo = '') {
        let loadingTask = null;
        let pdf = null;
        let page = null;

        try {
            if (!window.pdfjsLib) {
                throw new Error('PDF.js n├úo est├í carregado');
            }
           
            loadingTask = window.pdfjsLib.getDocument({ data: arrayBuffer });
            pdf = await loadingTask.promise;
            page = await pdf.getPage(1);
            const textContent = await page.getTextContent();
           
            const textosBrutos = textContent.items.map(item => item.str.trim());
            const textoCompleto = textosBrutos.filter(str => str !== "").join(' ');

            // Regex otimizadas (copiadas de ext.js v4.2)
            const regexVerbas = /VERBAS\s+([\d.,]+)/i;
            const regexFGTS = /VERBAS\s+[\d.,]+\s+FGTS\s+([\d.,]+)/i;
            const regexDepositoFGTS = /DEP[O├ô]SITO FGTS\s*[\.,]?\s*([\d\.,]+)/i;
            const regexINSSTotal = /CONTRIBUI├ç├âO SOCIAL SOBRE SAL├üRIOS DEVIDOS\s+([\d.,]+)/i;
            const regexINSSAutor = /DEDU├ç├âO DE CONTRIBUI├ç├âO SOCIAL\s+(?:\(\s*)?([\d.,]+)(?:\s*\))?/i;
            const regexCustas = /CUSTAS JUDICIAIS DEVIDAS PELO RECLAMADO\s+([\d.,]+)/i;
            const regexData = /(?:Data\s+Liquida[├ºc][├úa]o\s*[:\-]?\s*(\d{2}\/\d{2}\/\d{4}))|(?:(\d{2}\/\d{2}\/\d{4})\s*Data\s+Liquida[├ºc][├úa]o)/i;
            const regexDataFallback = /([0-3][0-9]\/[0-1][0-9]\/20[2-9][0-9])\s+[A-Z├Ç-┼©\s]+Data\s+Liquida[├ºc][├úa]o/i;
            const regexIdAssinatura = /Documento assinado eletronicamente[\s\S]*?-\s*([a-zA-Z0-9]+)(?:\s|$)/i;
            const regexHonAutor = /HONOR├üRIOS L├ìQUIDOS PARA PATRONO DO RECLAMANTE\s+([\d.,]+)/i;
            const regexHonPerito = /HONOR├üRIOS L├ìQUIDOS PARA\s+(?!PATRONO DO RECLAMANTE)(.+?)\s+([\d.,]{3,})/i;
            const regexPeriodo = /(\d{2}[\/]?\d{2}[\/]?\d{4})\s+a\s+(\d{2}[\/]?\d{2}[\/]?\d{4})/;
            const regexIRPF = /IRPF\s+DEVIDO\s+PELO\s+RECLAMANTE\s+([\d.,]+)/i;

            // Extra├º├úo
            const verbas = (textoCompleto.match(regexVerbas) || [])[1] || "";
            const fgts = (textoCompleto.match(regexFGTS) || [])[1] || "";
            const inssTotal = (textoCompleto.match(regexINSSTotal) || [])[1] || "";
            const inssAutor = (textoCompleto.match(regexINSSAutor) || [])[1] || "";
            const custas = (textoCompleto.match(regexCustas) || [])[1] || "";
            let honAutor = (textoCompleto.match(regexHonAutor) || [])[1] || "";
           
            const matchPerito = textoCompleto.match(regexHonPerito);
            let peritoNome = matchPerito ? matchPerito[1].trim() : "";
            let peritoValor = matchPerito ? matchPerito[2] : "";

            // VALIDA├ç├âO: Verificar se "honor├írio para..." ├® perito ou advogado autor
            // REGRA: Default = honor├írio advogado autor
            //        S├│ registra como perito se nome bater com perito detectado
            // PREVAL├èNCIA: Valor da planilha prevalece sobre valor da senten├ºa (mais atualizado)
            if (peritoNome && peritoValor) {
                const peritosConhecidos = window.hcalcPeritosDetectados || [];
               
                // Verificar se nome bate com perito j├í detectado no processo
                const ehPerito = peritosConhecidos.some(p =>
                    normalizarNomeParaComparacao(p).includes(normalizarNomeParaComparacao(peritoNome)) ||
                    normalizarNomeParaComparacao(peritoNome).includes(normalizarNomeParaComparacao(p))
                );
               
                if (ehPerito) {
                    // Nome bate com perito detectado ÔåÆ honor├írio pericial
                    console.log(`hcalc: "${peritoNome}" confirmado como PERITO (match detectado)`);
                    // Mant├®m peritoNome e peritoValor
                } else {
                    // DEFAULT: Qualquer outro caso = honor├írio advogado autor
                    console.log(`hcalc: "${peritoNome}" ÔåÆ DEFAULT: honor├írio advogado autor`);
                    // Transferir para honor├írios do autor
                    honAutor = peritoValor;
                    peritoNome = "";
                    peritoValor = "";
                }
            }

            let dataAtualizacao = (textoCompleto.match(regexData) || [])[1] ||
                                   (textoCompleto.match(regexData) || [])[2];
            if (!dataAtualizacao) {
                const fallback = textoCompleto.match(regexDataFallback);
                if (fallback) dataAtualizacao = fallback[1];
            }
           
            const idPlanilha = idNomeArquivo || (textoCompleto.match(regexIdAssinatura) || [])[1] || "";

            // Extrair per├¡odo do c├ílculo
            const periodoMatch = textoCompleto.match(regexPeriodo);
            let periodoCalculo = null;
            if (periodoMatch) {
                const fmt = s => s.includes('/') ? s : `${s.substr(0,2)}/${s.substr(2,2)}/${s.substr(4,4)}`;
                periodoCalculo = `${fmt(periodoMatch[1])} a ${fmt(periodoMatch[2])}`;
            }

            // Extrair IRPF e determinar se ├® tribut├ível
            const irpfMatch = textoCompleto.match(regexIRPF);
            const irpfIsento = !irpfMatch || parseFloat(
                irpfMatch[1].replace(/\./g, '').replace(',', '.')
            ) === 0;

            // Detectar se FGTS foi depositado (comparando valores)
            let fgtsDepositado = false;
            if (fgts) {
                const matchDepositoFGTS = textoCompleto.match(regexDepositoFGTS);
                if (matchDepositoFGTS && matchDepositoFGTS[1]) {
                    // Normalizar valores para compara├º├úo (remover pontos/v├¡rgulas)
                    const valorFgts = fgts.replace(/[\.,]/g, '');
                    const valorDeposito = matchDepositoFGTS[1].replace(/[\.,]/g, '');
                   
                    if (valorFgts === valorDeposito) {
                        fgtsDepositado = true;
                        console.log(`hcalc: FGTS identificado como DEPOSITADO (valor: ${fgts})`);
                    }
                }
            }

            const dadosBrutos = {
                verbas,
                fgts,
                fgtsDepositado,
                inssTotal,
                inssAutor,
                custas,
                dataAtualizacao,
                idPlanilha,
                honAutor,
                peritoNome,
                peritoValor,
                periodoCalculo,
                irpfIsento,
                sucesso: true
            };

            // Aplicar valida├º├úo (Fase 2)
            const dadosValidados = validarDadosExtraidos(dadosBrutos);
            const qualidade = calcularQualidadeExtracao(dadosValidados);
           
            console.log(`[HCalc] Extra├º├úo conclu├¡da - Qualidade: ${qualidade.percentual}% (${qualidade.validos}/${qualidade.total} v├ílidos)`);
            if (qualidade.faltando.length > 0) {
                warn('Campos n├úo extra├¡dos:', qualidade.faltando.join(', '));
            }
            if (qualidade.invalidos.length > 0) {
                warn('Campos com formato suspeito:', qualidade.invalidos.map(i => `${i.campo}: ${i.valor}`).join(', '));
            }

            return dadosValidados;

        } catch (error) {
            console.error('[HCalc] Erro na extra├º├úo:', error.message);
            return { sucesso: false, erro: error.message };
        } finally {
            // Limpeza de mem├│ria (previne leak)
            if (page) {
                try { page.cleanup(); } catch (e) {}
            }
            if (pdf) {
                try { await pdf.destroy(); } catch (e) {}
            }
            if (loadingTask && typeof loadingTask.destroy === 'function') {
                try { await loadingTask.destroy(); } catch (e) {}
            }
        }
    }

    async function processarPlanilhaPDF(file) {
        let idNomeArquivo = '';
        const matchNome = file.name.match(/Documento_([a-zA-Z0-9]+)\.pdf/i);
        if (matchNome) idNomeArquivo = matchNome[1];

        // Transfere ArrayBuffer para Worker (zero-copy)
        const arrayBuffer = await file.arrayBuffer();
        const peritosConhecidos = window.hcalcPeritosDetectados || [];

        return new Promise((resolve, reject) => {
            if (!window.hcalcState._pdfWorkerUrl) {
                window.hcalcState._pdfWorkerUrl = criarPdfWorkerBlob();
            }
            const worker = new Worker(window.hcalcState._pdfWorkerUrl);
            worker.onmessage = (e) => {
                worker.terminate();
                const dados = e.data;
                if (!dados.sucesso) { resolve(dados); return; }
                const dadosValidados = validarDadosExtraidos(dados);
                const qualidade = calcularQualidadeExtracao(dadosValidados);
                console.log('[HCalc Worker] Qualidade: ' + qualidade.percentual + '% (' + qualidade.validos + '/' + qualidade.total + ' v├ílidos)');
                if (qualidade.faltando.length > 0) warn('Campos n├úo extra├¡dos:', qualidade.faltando.join(', '));
                if (qualidade.invalidos.length > 0) warn('Campos suspeitos:', qualidade.invalidos.map(i => i.campo + ': ' + i.valor).join(', '));
                resolve(dadosValidados);
            };
            worker.onerror = (e) => { worker.terminate(); reject(new Error(e.message)); };
            worker.postMessage({ arrayBuffer, idNomeArquivo, peritosConhecidos }, [arrayBuffer]);
        });
    }

    // Expor para hcalc-overlay.js
    window.normalizarNomeParaComparacao = normalizarNomeParaComparacao;
    window.carregarPDFJSSeNecessario   = carregarPDFJSSeNecessario;
    window.processarPlanilhaPDF        = processarPlanilhaPDF;
})();


// ── hcalc-overlay.js ──────────────────────────────────
(function() {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg  = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err  = (...args) => console.error('[hcalc]', ...args);
    // Proxies para dependencias de hcalc-core.js e hcalc-pdf.js
    const normalizarNomeParaComparacao = n     => window.normalizarNomeParaComparacao(n);
    const carregarPDFJSSeNecessario   = ()     => window.carregarPDFJSSeNecessario();
    const processarPlanilhaPDF        = (...a) => window.processarPlanilhaPDF(...a);
    const executarPrep                = (...a) => window.executarPrep(...a);
    const destacarElementoNaTimeline  = (...a) => window.destacarElementoNaTimeline(...a);
    const encontrarItemTimeline        = (href) => window.encontrarItemTimeline && window.encontrarItemTimeline(href);
    const expandirAnexos               = (item) => window.expandirAnexos && window.expandirAnexos(item);
    // ==========================================
    function initializeBotao() {
        if (window.__hcalcBotaoInitialized) {
            dbg('initializeBotao ignorado: bot├úo j├í inicializado.');
            return;
        }
        dbg('initializeBotao iniciado (FASE A - leve).');
        window.__hcalcBotaoInitialized = true;

        // CSS m├¡nimo ÔÇö apenas o bot├úo (~200 bytes)
        if (!document.getElementById('hcalc-btn-style')) {
            const s = document.createElement('style');
            s.id = 'hcalc-btn-style';
            s.innerText = `
        #btn-abrir-homologacao {
            position: fixed; bottom: 20px; right: 20px; z-index: 99999;
            background: #00509e; color: white; border: none; border-radius: 6px;
            padding: 10px 18px; font-size: 13px; font-weight: bold; cursor: pointer;
            box-shadow: 0 3px 5px rgba(0,0,0,0.3);
        }
        #btn-abrir-homologacao:hover { background: #003d7a; }`;
            document.head.appendChild(s);
        }

        // Injeta APENAS bot├úo + input file (sem overlay)
        document.body.insertAdjacentHTML('beforeend', `
    <button id="btn-abrir-homologacao">\uD83D\uDCC4 Carregar Planilha</button>
    <input type="file" id="input-planilha-pdf" accept=".pdf" style="display: none;">`);

        const btn = document.getElementById('btn-abrir-homologacao');

        // Handler do bot├úo ÔÇö inicializa overlay lazy na primeira vez
        btn.onclick = async () => {
            if (!window.__hcalcOverlayInitialized) {
                dbg('Primeiro clique: carregando overlay completo (lazy init)...');
                initializeOverlay();
                // initializeOverlay() substituiu btn.onclick com o handler completo
            }
            // Executar fase correta
            if (!window.hcalcState.planilhaCarregada) {
                dbg('FASE 1: abrindo file picker.');
                document.getElementById('input-planilha-pdf').click();
                return;
            }
            // FASE 3: re-despacha para o handler completo (overlay j├í inicializado)
            btn.click();
        };
        dbg('Bot├úo flutuante injetado (lazy init ativo).');
    }


    function initializeOverlay() {
        if (window.__hcalcOverlayInitialized) {
            dbg('initializeOverlay ignorado: overlay ja inicializado.');
            return;
        }
        dbg('initializeOverlay iniciado.');
        window.__hcalcOverlayInitialized = true;

        // ==========================================
        // 1. ESTILOS DO OVERLAY E BOT├âO (v1.9 - UI Compacta)
        // ==========================================
        const styles = `
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

        /* Compactar espa├ºamento interno para caber na tela */
        #homologacao-modal fieldset { padding: 8px 10px; margin-bottom: 6px; }
        #homologacao-modal .row { margin-bottom: 6px; gap: 8px; }
        #homologacao-modal input[type=text],
        #homologacao-modal input[type=date],
        #homologacao-modal select,
        #homologacao-modal textarea { padding: 5px 7px; font-size: 12px; }
        #homologacao-modal label { font-size: 11px; margin-bottom: 2px; }
        #homologacao-modal legend { font-size: 12px; padding: 3px 8px; }
        #homologacao-modal .btn-gravar { padding: 10px; font-size: 15px; margin-top: 10px; }

        /* Estilos do Card de Resumo da Planilha (FASE 1) */
        #resumo-extracao-card {
            width: 260px;
            background: #f8f9fa;
            border: 2px solid #10b981;
            border-radius: 8px;
            padding: 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            pointer-events: all;
            align-self: flex-start;
            margin-right: 8px;
            overflow: hidden;
            flex-shrink: 0;
        }
        #resumo-extracao-card h4 {
            margin: 0;
            padding: 10px 12px;
            border-bottom: 1px solid #10b981;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #16a34a;
            background: #f0fdf4;
        }
        #resumo-extracao-card h4:hover { background: #dcfce7; }
        #resumo-body {
            padding: 10px 12px;
            display: none;
        }
        #resumo-conteudo { display: flex; flex-direction: column; gap: 6px; }
        .resumo-item {
            padding: 4px 6px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            font-size: 12px;
        }
        .resumo-item strong { color: #16a34a; }
        #btn-reload-planilha {
            margin-top: 8px;
            width: 100%;
            padding: 5px 10px;
            font-size: 11px;
            border-radius: 4px;
            border: 1px solid #10b981;
            background: #fff;
            color: #10b981;
            cursor: pointer;
        }
        #btn-reload-planilha:hover { background: #10b981; color: white; }

        /* Recursos com anexos ÔÇö integrado de rec.js v1.0 */
        .rec-recurso-card {
            padding: 8px 10px; margin-bottom: 6px;
            border: 1px solid #e5e7eb; border-radius: 5px;
            background: white; cursor: pointer; transition: all 0.2s;
        }
        .rec-recurso-card:hover { background: #f0f9ff; border-color: #3b82f6; }
        .rec-tipo-badge {
            display: inline-block; padding: 1px 7px; border-radius: 3px;
            font-size: 10px; font-weight: 700; color: white;
            background: #3b82f6; margin-right: 6px;
        }
        .rec-anexos-lista { margin-top: 6px; padding-top: 5px; border-top: 1px solid #e5e7eb; display: none; }
        .rec-recurso-card.expandido .rec-anexos-lista { display: block; }
        .rec-anexo-item {
            display: flex; align-items: center; gap: 6px;
            padding: 3px 4px; border-radius: 3px; cursor: pointer;
            font-size: 11px; transition: background 0.15s;
        }
        .rec-anexo-item:hover { background: #f3f4f6; }
        .rec-anexo-badge {
            padding: 1px 5px; border-radius: 2px;
            font-size: 10px; font-weight: 600; color: white; white-space: nowrap;
        }
        .rec-anexo-id {
            font-size: 10px; background: #f3f4f6;
            padding: 1px 4px; border-radius: 2px;
            font-family: monospace; color: #374151; user-select: all;
        }
        .rec-seta-toggle { font-size: 10px; color: #9ca3af; margin-left: auto; }
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
    <div id="homologacao-overlay">
        <!-- Card de Resumo da Planilha Extra├¡da (├á esquerda) -->
        <div id="resumo-extracao-card" style="display:none">
            <h4 id="resumo-toggle">
                <span>­ƒôï Planilha Carregada</span>
                <span id="resumo-seta">ÔûÂ</span>
            </h4>
            <div id="resumo-body">
                <div id="resumo-conteudo"></div>
                <button id="btn-reload-planilha">­ƒöä Recarregar PDF</button>
            </div>
        </div>
       
        <div id="homologacao-modal">
            <div class="modal-header">
                <h2>Assistente de Homologa├º├úo</h2>
                <button class="btn-close" id="btn-fechar">X Fechar</button>
            </div>



            <!-- SE├ç├âO 1 e 2: BASE E PARTE -->
            <fieldset>
                <legend>C├ílculo Base e Autoria</legend>
                <div class="row">
                    <div class="col">
                        <label>Origem do C├ílculo</label>
                        <select id="calc-origem">
                            <option value="pjecalc" selected>PJeCalc</option>
                            <option value="outros">Outros</option>
                        </select>
                    </div>
                    <div class="col" id="col-pjc">
                        <label><input type="checkbox" id="calc-pjc" checked> Acompanha arquivo .PJC?</label>
                    </div>
                    <div class="col">
                        <label>Autor do C├ílculo</label>
                        <select id="calc-autor">
                            <option value="autor" selected>Reclamante (Autor)</option>
                            <option value="reclamada">Reclamada</option>
                            <option value="perito">Perito</option>
                        </select>
                    </div>
                    <div class="col hidden" id="col-esclarecimentos">
                        <label><input type="checkbox" id="calc-esclarecimentos" checked> Esclarecimentos do Perito?</label>
                        <input type="text" id="calc-peca-perito" placeholder="Id da Pe├ºa">
                    </div>
                </div>
            </fieldset>

            <!-- SE├ç├âO 3: ATUALIZA├ç├âO -->
            <fieldset>
                <legend>Atualiza├º├úo</legend>
                <div class="row">
                    <div class="col">
                        <label>├ìndice de Atualiza├º├úo</label>
                        <select id="calc-indice">
                            <option value="adc58" selected>SELIC / IPCA-E (ADC 58)</option>
                            <option value="tr">TR / IPCA-E (Casos Antigos)</option>
                        </select>
                    </div>
                </div>
            </fieldset>

            <!-- SE├ç├âO 5: DADOS COPIADOS DA PLANILHA (├ÜNICO FIELDSET) -->
            <fieldset>
                <legend>Dados Copiados da Planilha</legend>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">1) Identifica├º├úo, Datas, Principal e FGTS</label>
                    <div class="row">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Id da Planilha</label>
                            <input type="text" id="val-id" class="coleta-input" placeholder="Id #XXXX">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Data da Atualiza├º├úo</label>
                            <input type="text" id="val-data" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label>Cr├®dito Principal (ou Total)</label>
                            <input type="text" id="val-credito" class="coleta-input" placeholder="R$ Cr├®dito Principal">
                        </div>
                    </div>
                    <div class="row" style="align-items: center; gap: 10px; margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 auto;">
                            <label><input type="checkbox" id="calc-fgts" checked> FGTS apurado separado?</label>
                        </div>
                        <div class="col" id="fgts-radios" style="flex: 0 0 auto; display: flex; gap: 12px;">
                            <label style="margin: 0;"><input type="radio" name="fgts-tipo" value="devido" checked> Devido</label>
                            <label style="margin: 0;"><input type="radio" name="fgts-tipo" value="depositado"> Depositado</label>
                        </div>
                    </div>
                    <div class="row" id="row-fgts-valor">
                        <div class="col" id="col-fgts-val" style="flex: 0 0 auto;">
                            <label style="font-size: 11px; margin-bottom: 2px;">Valor FGTS Separado</label>
                            <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS" style="width: 140px;">
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
                            <label><input type="checkbox" id="ignorar-inss"> N├úo h├í INSS</label>
                            <small style="color: #666; display: block;">*INSS Reclamada = Subtra├º├úo autom├ítica se PJeCalc marcado.</small>
                        </div>
                        <div class="col">
                            <label>Imposto de Renda</label>
                            <select id="irpf-tipo" style="margin-bottom: 5px; width: 100%;">
                                <option value="isento" selected>N├úo h├í</option>
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
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">3) Honor├írios Advocat├¡cios</label>
                    <div class="row" style="margin-bottom: 0; align-items: flex-start;">

                        <!-- Coluna AUTOR -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>Honor├írios Adv Autor</label>
                            <input type="text" id="val-hon-autor" class="coleta-input highlight" placeholder="R$ Honor├írios Autor">
                            <label style="font-size: 11px; margin-top: 4px; display: block;">
                                <input type="checkbox" id="ignorar-hon-autor"> N├úo h├í honor├írios autor
                            </label>
                        </div>

                        <!-- Coluna R├ëU -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>
                                <input type="checkbox" id="chk-hon-reu" checked style="margin-right: 5px;">N├úo h├í Honor├írios Adv R├®u
                            </label>
                            <div id="hon-reu-campos" class="hidden" style="margin-top: 6px;">
                                <label style="font-size: 11px; display: block; margin-bottom: 6px;">
                                    <input type="checkbox" id="chk-hon-reu-suspensiva" checked> Condi├º├úo Suspensiva
                                </label>
                                <div style="display: flex; gap: 8px; flex-direction: column; margin-bottom: 6px;">
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="percentual" checked> Percentual
                                    </label>
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="valor"> Valor Informado
                                    </label>
                                </div>
                                <div id="hon-reu-perc-campo" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu-perc" class="coleta-input" value="5%" placeholder="%" style="width: 80px;">
                                </div>
                                <div id="hon-reu-valor-campo" class="hidden" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu" class="coleta-input" placeholder="R$ Honor├írios R├®u" style="width: 140px;">
                                </div>
                            </div>
                        </div>

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
                                <option value="pagas">J├í Pagas</option>
                            </select>
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Origem</label>
                            <select id="custas-origem">
                                <option value="sentenca" selected>Senten├ºa</option>
                                <option value="acordao">Ac├│rd├úo</option>
                            </select>
                        </div>
                    </div>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" id="custas-data-col" style="flex: 1;">
                            <label>Data Custas <small style="color: #666;">(vazio = mesma planilha)</small></label>
                            <input type="text" id="custas-data-origem" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col hidden" id="custas-acordao-col" style="flex: 1;">
                            <label>Ac├│rd├úo</label>
                            <select id="custas-acordao-select">
                                <option value="">Selecione o ac├│rd├úo</option>
                            </select>
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- SE├ç├âO 6: RESPONSABILIDADE -->
            <fieldset>
                <legend>Responsabilidade</legend>
                <div class="row">
                    <select id="resp-tipo">
                        <option value="unica">Reclamada ├Ünica</option>
                        <option value="solidarias">Devedoras Solid├írias</option>
                        <option value="subsidiarias" selected>Devedoras Subsidi├írias</option>
                    </select>
                </div>
                <div id="resp-sub-opcoes" class="row">
                    <label><input type="checkbox" id="resp-integral" checked> Responde pelo per├¡odo total</label>
                    <label style="margin-left: 15px;"><input type="checkbox" id="resp-diversos"> Per├¡odos Diversos (Gera estrutura para preencher)</label>
                </div>
            </fieldset>

            <!-- SE├ç├âO 6.1: PER├ìODOS DIVERSOS (Din├ómico) -->
            <fieldset id="resp-diversos-fieldset" class="hidden">
                <legend>Per├¡odos Diversos - C├ílculos Separados por Reclamada</legend>
                <div class="row" style="margin-bottom: 15px;">
                    <div class="col">
                        <label style="font-weight: bold;">Devedora Principal</label>
                        <select id="resp-devedora-principal" style="width: 100%; padding: 8px;">
                            <option value="">Selecione a devedora principal...</option>
                        </select>
                        <small style="color: #666; display: block; margin-top: 5px;">*Padr├úo: primeira reclamada</small>
                    </div>
                </div>
                <div class="row" style="margin-bottom: 15px; font-size: 13px; color: #555;">
                    <label>Preencha per├¡odo, planilha e tipo (Principal/Subsidi├íria) para cada reclamada com responsabilidade diversa:</label>
                </div>
                <div id="resp-diversos-container"></div>
                <button type="button" class="btn-action" id="btn-adicionar-periodo" style="margin-top: 10px;">+ Adicionar Per├¡odo Diverso</button>
            </fieldset>

            <!-- Links de Senten├ºa e Ac├│rd├úo -->
            <fieldset style="border: none; padding: 8px 0; margin: 8px 0;">
                <div id="link-sentenca-acordao-container"></div>
            </fieldset>

            <!-- SE├ç├âO 7B: HONOR├üRIOS PERICIAIS (auto-esconde se n├úo detectar perito) -->
            <fieldset id="fieldset-pericia-conh" class="hidden">
                <legend>Honor├írios Periciais <span id="link-sentenca-container"></span></legend>
                <div class="row">
                    <div class="col">
                        <label><input type="checkbox" id="chk-perito-conh"> Honor├írios Periciais (Conhecimento)</label>
                        <div id="perito-conh-campos" class="hidden" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-nome" placeholder="Nome do Perito">
                            <select id="perito-tipo-pag">
                                <option value="reclamada" selected>Pago pela Reclamada (Valor)</option>
                                <option value="trt">Pago pelo TRT (Autor Sucumbente)</option>
                            </select>
                            <input type="text" id="val-perito-valor" placeholder="R$ Valor ou ID TRT">
                            <input type="text" id="val-perito-data" placeholder="Data da Senten├ºa">
                        </div>
                    </div>
                </div>
                <div class="row hidden" id="row-perito-contabil">
                    <div class="col">
                        <label>Honor├írios Periciais (Cont├íbil - Rog├®rio)</label>
                        <div id="perito-contabil-campos" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-contabil-valor" placeholder="Valor dos honor├írios cont├íbeis">
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- Custas j├í foram movidas para o card 4 acima -->

            <!-- SE├ç├âO 8: DEP├ôSITOS -->
            <fieldset id="fieldset-deposito">
                <legend>Dep├│sitos</legend>
                <div class="row">
                    <label id="label-chk-deposito"><input type="checkbox" id="chk-deposito"> H├í Dep├│sito Recursal?</label>
                    <label style="margin-left: 20px;"><input type="checkbox" id="chk-pag-antecipado"> Pagamento Antecipado</label>
                </div>

                <!-- CONTAINER DE DEP├ôSITOS RECURSAIS (din├ómico) -->
                <div id="deposito-campos" class="hidden">
                    <div id="depositos-container"></div>
                    <button type="button" id="btn-add-deposito" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Dep├│sito Recursal</button>
                </div>

                <!-- CONTAINER DE PAGAMENTOS ANTECIPADOS (din├ómico) -->
                <div id="pag-antecipado-campos" class="hidden">
                    <div id="pagamentos-container"></div>
                    <button type="button" id="btn-add-pagamento" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Pagamento</button>
                </div>
            </fieldset>

            <!-- SE├ç├âO 9: INTIMA├ç├òES -->
            <fieldset id="fieldset-intimacoes">
                <legend>Intima├º├Áes</legend>
                <div id="lista-intimacoes-container">
                    <small style="color:#666; font-style:italic;">Aguardando leitura das partes...</small>
                </div>
                <div id="links-editais-container" class="hidden" style="margin-top: 10px; border-top: 1px dashed #ccc; padding-top: 10px;">
                    <label style="font-weight:bold; font-size:12px; color:#5b21b6;">Editais Detectados na Timeline:</label>
                    <div id="links-editais-lista"></div>
                </div>
            </fieldset>

            <button class="btn-action btn-gravar" id="btn-gravar">GRAVAR DECIS├âO (Copiar p/ PJe)</button>
        </div>
    </div>
    `;
        // Check robusto: Remover overlay antigo se existir (previne duplica├º├úo)
        const existingOverlay = document.getElementById('homologacao-overlay');
        if (existingOverlay) {
            dbg('Overlay j├í existe, removendo vers├úo antiga antes de recriar');
            existingOverlay.remove();
        }

        // Inserir HTML limpo
        document.body.insertAdjacentHTML('beforeend', htmlModal);
        dbg('Overlay HTML inserido no DOM.');

        // Toggle colapso/expans├úo do card de resumo
        const resumoToggle = document.getElementById('resumo-toggle');
        const resumoBody   = document.getElementById('resumo-body');
        const resumoSeta   = document.getElementById('resumo-seta');
        if (resumoToggle && resumoBody) {
            resumoToggle.addEventListener('click', () => {
                const aberto = resumoBody.style.display !== 'none';
                resumoBody.style.display = aberto ? 'none' : 'block';
                if (resumoSeta) resumoSeta.textContent = aberto ? 'ÔûÂ' : 'Ôû╝';
            });
        }

        if (!document.getElementById('homologacao-overlay')) {
            err('Falha apos insercao: homologacao-overlay nao encontrado.');
            return;
        }

        // ==========================================
        // 3. L├ôGICA DE INTERFACE E EVENTOS (TOGGLES)
        // ==========================================
        const $ = (id) => document.getElementById(id);
        dbg('Binding de eventos iniciado.');
       
        // ==========================================
        // FASE 1: Sistema de Fases do Bot├úo
        // ==========================================
        $('btn-abrir-homologacao').onclick = async () => {
            const btn = $('btn-abrir-homologacao');
            const inputFile = $('input-planilha-pdf');
           
            // FASE 1: Carregar Planilha (estado inicial)
            if (!window.hcalcState.planilhaCarregada) {
                dbg('FASE 1: Clique em Carregar Planilha');
                inputFile.click(); // Abre file picker
                return;
            }
           
            // FASE 3: Gerar Homologa├º├úo (ap├│s planilha carregada)
            dbg('FASE 3: Clique em Gerar Homologa├º├úo');
            try {
                // Executar prep.js: varredura + extra├º├úo da senten├ºa + AJ-JT
                const peritosConh = window.hcalcPeritosConhecimentoDetectados || [];
                const partesData = window.hcalcPartesData || {};
                const prep = await executarPrep(partesData, peritosConh);
               
                // CORRE├ç├âO 1: Salvar globalmente para preencherDepositosAutomaticos
                window.hcalcLastPrepResult = prep;

            // Retrocompat: manter window.hcalcTimelineData para construirSecaoIntimacoes
            window.hcalcTimelineData = {
                sentenca: prep.sentenca.data ? { data: prep.sentenca.data, href: prep.sentenca.href } : null,
                acordaos: prep.acordaos,
                editais: prep.editais
            };

            // Strikethrough no label de dep├│sito recursal se n├úo h├í ac├│rd├úo
            const labelDeposito = $('label-chk-deposito');
            if (labelDeposito) {
                labelDeposito.style.textDecoration = prep.acordaos.length === 0 ? 'line-through' : 'none';
            }

            // Link senten├ºa (info inline no card de custas)
            const linkSentencaContainer = $('link-sentenca-container');
            if (linkSentencaContainer) {
                linkSentencaContainer.innerHTML = '';
                if (prep.sentenca.data) {
                    const info = [];
                    if (prep.sentenca.custas) info.push(`Custas: R$${prep.sentenca.custas}`);
                    if (prep.sentenca.responsabilidade) info.push(`Resp: ${prep.sentenca.responsabilidade}`);

                    // Honor├írios periciais: prioriza AJ-JT, s├│ mostra senten├ºa se n├úo tiver AJ-JT
                    if (prep.pericia.peritosComAjJt.length > 0) {
                        info.push(`Hon.Periciais: ${prep.pericia.peritosComAjJt.length} AJ-JT detectado(s)`);
                    } else if (prep.sentenca.honorariosPericiais.length > 0) {
                        info.push(`Hon.Periciais: ${prep.sentenca.honorariosPericiais.map(h => 'R$' + h.valor + (h.trt ? ' (TRT)' : '')).join(', ')}`);
                    }

                    linkSentencaContainer.innerHTML = `<span style="font-size:12px; color:#16a34a;">Ô£ö Senten├ºa: ${prep.sentenca.data}${info.length ? ' | ' + info.join(' | ') : ''}</span>`;
                }
            }

            // Links clic├íveis de Senten├ºa e Ac├│rd├úo (fieldset separado)
            const linkSentencaAcordaoContainer = $('link-sentenca-acordao-container');
            if (linkSentencaAcordaoContainer) {
                linkSentencaAcordaoContainer.innerHTML = '';
               
                // Link da Senten├ºa (foca na timeline)
                if (prep.sentenca.href) {
                    const sentencaLink = document.createElement('a');
                    sentencaLink.href = '#';
                    sentencaLink.innerHTML = `<i class="fas fa-crosshairs"></i> Senten├ºa${prep.sentenca.data ? ' - ' + prep.sentenca.data : ''}`;
                    sentencaLink.style.cssText = 'display:block; color:#16a34a; font-size:12px; margin-bottom:5px; text-decoration:none; font-weight:600; cursor:pointer;';
                    sentencaLink.addEventListener('click', (e) => {
                        e.preventDefault();
                        destacarElementoNaTimeline(prep.sentenca.href);
                    });
                    linkSentencaAcordaoContainer.appendChild(sentencaLink);
                }
               
                // Links de Ac├│rd├úos
                if (prep.acordaos.length > 0) {
                    prep.acordaos.forEach((acordao, i) => {
                        if (acordao.href) {
                            const lbl = prep.acordaos.length > 1 ? `Ac├│rd├úo ${i + 1}` : `Ac├│rd├úo`;
                            const a = document.createElement('a');
                            a.href = '#';
                            a.innerHTML = `<i class="fas fa-crosshairs"></i> ${lbl}${acordao.data ? ' - ' + acordao.data : ''}`;
                            a.style.cssText = "display:block; color:#00509e; font-size:12px; margin-top:5px; text-decoration:none; cursor:pointer;";
                            a.addEventListener('click', (e) => {
                                e.preventDefault();
                                destacarElementoNaTimeline(acordao.href);
                            });
                            linkSentencaAcordaoContainer.appendChild(a);
                        }
                    });
                   
                    // RECURSOS COM ANEXOS (integrado de rec.js v1.0)
                    if (prep.depositos.length > 0) {
                        const recDiv = document.createElement('div');
                        recDiv.style.cssText = 'margin-top:8px; padding:6px; background:#fffde7; border:1px solid #fbbf24; border-radius:4px;';
                        recDiv.innerHTML = `<strong style="font-size:11px;color:#92400e">­ƒôÄ Recursos das Reclamadas (${prep.depositos.length})</strong>`;

                        prep.depositos.forEach((dep, depIdx) => {
                            const card = document.createElement('div');
                            card.className = 'rec-recurso-card';
                            card.dataset.href = dep.href || '';

                            const corBadge = { 'Dep├│sito': '#10b981', 'Garantia': '#f59e0b', 'Custas': '#ef4444', 'Anexo': '#6b7280' };

                            let anexosHtml = '';
                            if (dep.anexos && dep.anexos.length > 0) {
                                anexosHtml = `<div class="rec-anexos-lista">` +
                                    dep.anexos.map((ax, axIdx) =>
                                        `<div class="rec-anexo-item" data-dep-idx="${depIdx}" data-ax-idx="${axIdx}">
                                            <span class="rec-anexo-badge" style="background:${corBadge[ax.tipo] || '#6b7280'}">${ax.tipo}</span>
                                            <code class="rec-anexo-id">${ax.id || 'sem id'}</code>
                                            <span style="font-size:10px;color:#6b7280;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px" title="${ax.texto}">${ax.texto.substring(0,40)}</span>
                                        </div>`
                                    ).join('') +
                                `</div>`;
                            }

                            card.innerHTML = `
                                <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
                                    <span class="rec-tipo-badge">${dep.tipo || 'RO'}</span>
                                    <span style="font-size:11px;color:#92400e;font-weight:600;flex:1">${dep.depositante || 'Parte n├úo identificada'}</span>
                                    <span style="font-size:10px;color:#6b7280">${dep.data || 'sem data'}</span>
                                    ${dep.anexos && dep.anexos.length > 0 ? `<span class="rec-seta-toggle">ÔûÂ ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}</span>` : ''}
                                </div>
                                ${anexosHtml}`;

                            card.addEventListener('click', e => {
                                const axItem = e.target.closest('.rec-anexo-item');
                                if (axItem) {
                                    e.stopPropagation();
                                    const axIdx = parseInt(axItem.dataset.axIdx, 10);
                                    const ax = dep.anexos[axIdx];
                                    if (!ax) return;

                                    // 1. Destacar o recurso na timeline
                                    if (dep.href) try { destacarElementoNaTimeline(dep.href); } catch(e2) { console.error('[hcalc]', e2); }

                                    // 2. Re-encontrar e clicar no anexo (evita refer├¬ncia stale do Angular)
                                    setTimeout(async () => {
                                        try {
                                            const item = encontrarItemTimeline(dep.href);
                                            if (item) {
                                                await expandirAnexos(item);
                                                const links = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                                                let alvo = null;
                                                if (ax.id) {
                                                    alvo = Array.from(links).find(l => l.textContent.includes(ax.id));
                                                }
                                                alvo = alvo || links[axIdx] || links[0];
                                                if (alvo) alvo.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                            } else if (ax.elemento && ax.elemento.isConnected) {
                                                ax.elemento.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                            }
                                        } catch(e3) { console.error('[hcalc] Erro ao clicar no anexo:', e3); }
                                    }, 600);
                                    return;
                                }

                                card.classList.toggle('expandido');
                                const seta = card.querySelector('.rec-seta-toggle');
                                if (seta) seta.textContent = card.classList.contains('expandido')
                                    ? `\u25bc ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`
                                    : `\u25b6 ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`;
                                if (dep.href) try { destacarElementoNaTimeline(dep.href); } catch(e2) { console.error('[hcalc]', e2); }
                            });

                            recDiv.appendChild(card);
                        });

                        linkSentencaAcordaoContainer.appendChild(recDiv);
                    }
                } else {
                    // Aviso quando n├úo h├í ac├│rd├úo
                    const avisoDiv = document.createElement('div');
                    avisoDiv.style.cssText = 'margin-top:8px; padding:8px; background:#fef2f2; border:1px solid #ef4444; border-radius:4px;';
                    avisoDiv.innerHTML = `<span style="font-size:12px; color:#dc2626; font-weight:600;">ÔÜá N├úo h├í Ac├│rd├úo</span>`;
                    linkSentencaAcordaoContainer.appendChild(avisoDiv);
                }
            }

            // Preencher custas automaticamente - PRIORIZA PLANILHA
            if (window.hcalcState.planilhaExtracaoData?.custas && $('val-custas')) {
                $('val-custas').value = window.hcalcState.planilhaExtracaoData.custas;
                // FIX: sem ac├│rd├úo ÔåÆ custas s├úo da senten├ºa ÔåÆ data = senten├ºa
                const semAcordao = prep.acordaos.length === 0;
                if (semAcordao && prep.sentenca.data && $('custas-data-origem')) {
                    $('custas-data-origem').value = prep.sentenca.data;
                } else if (window.hcalcState.planilhaExtracaoData.dataAtualizacao && $('custas-data-origem')) {
                    $('custas-data-origem').value = window.hcalcState.planilhaExtracaoData.dataAtualizacao;
                }
            } else if (prep.sentenca.custas && $('val-custas')) {
                $('val-custas').value = prep.sentenca.custas;
                // Data das custas = data da senten├ºa (apenas se n├úo h├í planilha)
                if (prep.sentenca.data && $('custas-data-origem')) {
                    $('custas-data-origem').value = prep.sentenca.data;
                }
            }

            // Dep├│sito recursal: vis├¡vel se tem ac├│rd├úos
            const fieldsetDeposito = $('fieldset-deposito');
            if (prep.acordaos.length === 0) {
                if (fieldsetDeposito) fieldsetDeposito.classList.add('hidden');
            } else {
                if (fieldsetDeposito) fieldsetDeposito.classList.remove('hidden');
            }

            // Povoar select de ac├│rd├úos se existirem
            const custasAcordaoSelect = $('custas-acordao-select');
            if (custasAcordaoSelect && prep.acordaos.length > 0) {
                custasAcordaoSelect.innerHTML = '<option value="">Selecione o ac├│rd├úo</option>';
                prep.acordaos.forEach((acordao, i) => {
                    const opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = `Ac├│rd├úo ${i + 1}${acordao.data ? ' - ' + acordao.data : ''}`;
                    opt.dataset.data = acordao.data || '';
                    opt.dataset.id = acordao.id || '';
                    custasAcordaoSelect.appendChild(opt);
                });
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
            // REGRAS AUTO-PREENCHIMENTO (prep sobrep├Áe defaults)
            // ==========================================

            // REGRA 1: Dep├│sito recursal ÔÇö disparar evento onChange para unificar fluxo
            // CORRE├ç├âO 2: Usar dispatchEvent em vez de manipula├º├úo direta do DOM
            if (prep.depositos.length > 0) {
                console.log('[INICIALIZA├ç├âO] Detectados', prep.depositos.length, 'recursos com dep├│sito/garantia');
               
                const chkDep = $('chk-deposito');
                if (chkDep) {
                    chkDep.checked = true;
                    // Disparar onChange sint├®tico ÔÇö aciona visibilidade E preencherDepositosAutomaticos
                    // de forma unificada, eliminando dessincroniza├º├úo
                    chkDep.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('[INICIALIZA├ç├âO] Evento change disparado');
                }
            }

            // REGRA 2: Perito conhecimento + TRT / AJ-JT match
            const peritoTipoEl = $('perito-tipo-pag');
            const peritoValorEl = $('val-perito-valor');
            const peritoDataEl = $('val-perito-data');
            if (prep.pericia.peritosComAjJt.length > 0) {
                // Perito casou com AJ-JT ÔÇö pago pelo TRT
                const match = prep.pericia.peritosComAjJt[0];
                if (peritoTipoEl) peritoTipoEl.value = 'trt';
                if (peritoValorEl) peritoValorEl.value = match.idAjJt || '';
            } else if (prep.sentenca.honorariosPericiais.length > 0) {
                // Honor├írios periciais na senten├ºa
                const hon = prep.sentenca.honorariosPericiais[0];
                if (hon.trt && peritoTipoEl) {
                    peritoTipoEl.value = 'trt';
                }
                // Sempre preencher valor se detectado
                if (peritoValorEl && !peritoValorEl.value) {
                    peritoValorEl.value = 'R$' + hon.valor;
                }
            }
            // Data da senten├ºa no campo de data do perito
            if (prep.sentenca.data && peritoDataEl && !peritoDataEl.value) {
                peritoDataEl.value = prep.sentenca.data;
            }

            // REGRA 3 e 4: Responsabilidade (subsidi├íria / solid├íria)
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
            // Sempre padr├úo = senten├ºa (usu├írio pode mudar para ac├│rd├úo se necess├írio)
            const custasStatusEl = $('custas-status');
            const custasOrigemEl = $('custas-origem');
            if (prep.sentenca.custas) {
                // ATEN├ç├âO: N├úo sobrep├Áe se planilha j├í preencheu custas
                if ($('val-custas') && !window.hcalcState.planilhaExtracaoData?.custas) {
                    $('val-custas').value = prep.sentenca.custas;
                }
                // Sempre usa senten├ºa como padr├úo
                if (custasStatusEl) custasStatusEl.value = 'devidas';
                if (custasOrigemEl) custasOrigemEl.value = 'sentenca';
                // ATEN├ç├âO: N├úo sobrep├Áe data se planilha j├í preencheu
                if ($('custas-data-origem') && prep.sentenca.data && !window.hcalcState.planilhaExtracaoData?.custas) {
                    $('custas-data-origem').value = prep.sentenca.data;
                }
            }

            // REGRA 6: hsusp ÔåÆ Honor├írios Adv. R├®u com condi├º├úo suspensiva
            const chkHonReu = $('chk-hon-reu');
            const honReuCampos = $('hon-reu-campos');
            if (prep.sentenca.hsusp) {
                // L├│gica invertida: desmarcar "N├úo h├í" para mostrar campos
                if (chkHonReu) chkHonReu.checked = false;
                if (honReuCampos) honReuCampos.classList.remove('hidden');

                const radSusp = document.querySelector('input[name="rad-hon-reu"][value="suspensiva"]');
                if (radSusp) radSusp.checked = true;
            } else {
                // Estado padr├úo: checkbox marcado, campos ocultos
                if (chkHonReu) chkHonReu.checked = true;
                if (honReuCampos) honReuCampos.classList.add('hidden');
            }

                // ==========================================
                // PREENCHER COM DADOS DA PLANILHA (PRIORIDADE)
                // ==========================================
                if (window.hcalcState.planilhaExtracaoData) {
                    const dados = window.hcalcState.planilhaExtracaoData;
                   
                    if (dados.idPlanilha && $('val-id')) $('val-id').value = dados.idPlanilha;
                    if (dados.verbas && $('val-credito')) $('val-credito').value = dados.verbas;
                   
                    // FGTS: preencher valor + ajustar checkbox + marcar status depositado conforme extra├º├úo
                    if ($('val-fgts') && $('calc-fgts')) {
                        const temFgts = dados.fgts && dados.fgts !== '0,00' && dados.fgts !== '0';
                       
                        if (temFgts) {
                            $('val-fgts').value = dados.fgts;
                            $('calc-fgts').checked = true;
                           
                            // Marcar radio button correto (depositado ou devido)
                            if (dados.fgtsDepositado) {
                                const radDepositado = document.querySelector('input[name="fgts-tipo"][value="depositado"]');
                                if (radDepositado) radDepositado.checked = true;
                            } else {
                                const radDevido = document.querySelector('input[name="fgts-tipo"][value="devido"]');
                                if (radDevido) radDevido.checked = true;
                            }
                        } else {
                            // Sem FGTS detectado ÔåÆ desmarcar checkbox (que vem marcado por padr├úo)
                            $('calc-fgts').checked = false;
                        }
                        $('calc-fgts').dispatchEvent(new Event('change', { bubbles: true }));
                    }
                   
                    // INSS: preencher valores + ajustar checkbox se n├úo h├í nenhum
                    if (dados.inssTotal && $('val-inss-total')) $('val-inss-total').value = dados.inssTotal;
                    if (dados.inssAutor && $('val-inss-rec')) $('val-inss-rec').value = dados.inssAutor;
                   
                    // Verificar se n├úo h├í INSS nenhum
                    const semInssTotal = !dados.inssTotal || dados.inssTotal === '0,00' || dados.inssTotal === '0';
                    const semInssAutor = !dados.inssAutor || dados.inssAutor === '0,00' || dados.inssAutor === '0';
                   
                    if (semInssTotal && semInssAutor && $('ignorar-inss')) {
                        $('ignorar-inss').checked = true;
                        $('ignorar-inss').dispatchEvent(new Event('change', { bubbles: true }));
                    }
                   
                    // Custas: valor e data da planilha (prevalece sobre senten├ºa)
                    if (dados.custas && $('val-custas')) {
                        $('val-custas').value = dados.custas;
                        // Data das custas = data de liquida├º├úo da planilha
                        if (dados.dataAtualizacao && $('custas-data-origem')) {
                            $('custas-data-origem').value = dados.dataAtualizacao;
                        }
                    }
                   
                    if (dados.dataAtualizacao && $('val-data')) $('val-data').value = dados.dataAtualizacao;
                    if (dados.honAutor && $('val-hon-autor')) $('val-hon-autor').value = dados.honAutor;
                   
                    // Aplicar IRPF se tribut├ível
                    if (dados.irpfIsento === false) {
                        const irpfTipoEl = document.getElementById('irpf-tipo');
                        if (irpfTipoEl && irpfTipoEl.options.length > 1) {
                            irpfTipoEl.value = irpfTipoEl.options[1].value; // primeiro != 'isento'
                            irpfTipoEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                   
                    // Auto-selecionar origem como PJeCalc
                    if ($('calc-origem')) $('calc-origem').value = 'pjecalc';
                }

                // Mostrar card colapsado se planilha foi carregada (Fase 3)
                const resumoCard = $('resumo-extracao-card');
                if (resumoCard && window.hcalcState.planilhaExtracaoData) {
                    resumoCard.style.display = 'block';
                    // Preencher conte├║do do card
                    const dados = window.hcalcState.planilhaExtracaoData;
                    const resumoConteudo = $('resumo-conteudo');
                    if (resumoConteudo) {
                        resumoConteudo.innerHTML = `
                            <div class="resumo-item"><strong>ID:</strong> ${dados.idPlanilha || 'N/A'}</div>
                            <div class="resumo-item"><strong>Cr├®dito:</strong> R$ ${dados.verbas || '0,00'}</div>
                            ${dados.fgts ? `<div class="resumo-item"><strong>FGTS:</strong> R$ ${dados.fgts}</div>` : ''}
                            <div class="resumo-item"><strong>INSS Total:</strong> R$ ${dados.inssTotal || '0,00'}</div>
                            <div class="resumo-item"><strong>INSS Rec:</strong> R$ ${dados.inssAutor || '0,00'}</div>
                            ${dados.custas ? `<div class="resumo-item"><strong>Custas:</strong> R$ ${dados.custas}</div>` : ''}
                            <div class="resumo-item"><strong>Data:</strong> ${dados.dataAtualizacao || 'N/A'}</div>
                            ${dados.periodoCalculo ? `<div class="resumo-item"><strong>Per├¡odo:</strong> ${dados.periodoCalculo}</div>` : ''}
                            ${dados.irpfIsento === false ? `<div class="resumo-item" style="color:#b45309"><strong>IRPF:</strong> Tribut├ível</div>` : ''}
                        `;
                    }
                }

                $('homologacao-overlay').style.display = 'flex';
                dbg('Overlay exibido para o usuario.');
               
                // Fallback: tentar clipboard se n├úo tem ID da planilha
                if (!window.hcalcState.planilhaExtracaoData?.idPlanilha) {
                    try {
                        const txt = await navigator.clipboard.readText();
                        if (txt && txt.trim().length > 0) {
                            $('val-id').value = txt.trim();
                        }
                    } catch (e) { console.warn('Clipboard ignorado ou bloqueado', e); }
                }
               
                updateHighlight();
            } catch (e) {
                err('Erro no handler do botao Gerar Homologacao:', e);
                alert('Erro ao abrir assistente. Verifique o console (F12).');
                return;
                }
        };
       
        // ==========================================
        // FASE 2: Handler do Input File (Carregar Planilha)
        // ==========================================
        $('input-planilha-pdf').onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
           
            const btn = $('btn-abrir-homologacao');
            btn.textContent = 'ÔÅ│ Processando...';
            btn.disabled = true;
           
            try {
                // Configurar PDF.js (primeira vez)
                const loaded = carregarPDFJSSeNecessario();
                if (!loaded) {
                    throw new Error('PDF.js n├úo dispon├¡vel');
                }
               
                // Processar planilha
                const dados = await processarPlanilhaPDF(file);
               
                if (dados.sucesso) {
                    // Salvar no state
                    window.hcalcState.planilhaExtracaoData = dados;
                    window.hcalcState.planilhaCarregada = true;
                   
                    // Atualizar dropdowns de linhas extras com a planilha principal rec├®m-carregada
                    atualizarDropdownsPlanilhas();
                   
                    // Atualizar bot├úo
                    btn.textContent = 'Ô£ô Dados Extra├¡dos';
                    btn.style.background = '#10b981';
                    btn.disabled = false;
                   
                    dbg('Planilha extra├¡da:', dados);
                   
                    // Feedback visual moment├óneo
                    setTimeout(() => {
                        btn.textContent = 'Gerar Homologa├º├úo';
                        btn.style.background = '#00509e';
                    }, 2000);
                } else {
                    throw new Error(dados.erro || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('[HCalc] Erro ao processar PDF:', error.message);
                alert('Erro ao processar PDF: ' + error.message);
                btn.textContent = '­ƒôä Carregar Planilha';
                btn.disabled = false;
            }
        };
       
        // Handler do bot├úo Reload (recarregar planilha)
        $('btn-reload-planilha').onclick = () => {
            const inputFile = $('input-planilha-pdf');
            inputFile.click();
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
            // LIMPAR REFER├èNCIAS DOM: v1.8 usa m├®todo centralizado
            window.hcalcState.resetPrep();
            console.log('[hcalc] Estado resetado via hcalcState.resetPrep()');
        };
        $('homologacao-overlay').onclick = (e) => {
            if (e.target.id === 'homologacao-overlay') {
                // N├úo fecha ÔÇö torna transparente e "fantasma"
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
                    // Mant├®m overlay transparente para detectar clique de retorno
                    overlay.style.pointerEvents = 'all';
                    modal.dataset.ghost = 'true';
                }
            }
        };

        $('calc-origem').onchange = (e) => { $('col-pjc').classList.toggle('hidden', e.target.value !== 'pjecalc'); };
        $('calc-autor').onchange = (e) => { $('col-esclarecimentos').classList.toggle('hidden', e.target.value !== 'perito'); };
        $('calc-esclarecimentos').onchange = (e) => { $('calc-peca-perito').classList.toggle('hidden', !e.target.checked); };

        $('calc-fgts').onchange = (e) => {
            const isChecked = e.target.checked;
            $('fgts-radios').classList.toggle('hidden', !isChecked);
            $('row-fgts-valor').classList.toggle('hidden', !isChecked);
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

        $('resp-tipo').onchange = (e) => {
            $('resp-sub-opcoes').classList.toggle('hidden', e.target.value !== 'subsidiarias');
           
            // Atualizar visibilidade de checkboxes "Depositado pela Principal" em todos os dep├│sitos
            window.hcalcState.depositosRecursais.forEach(d => {
                if (!d.removed) {
                    atualizarVisibilidadeDepositoPrincipal(d.idx);
                }
            });
        };

        // L├│gica para Per├¡odos Diversos
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
                    if (idx === 0) opt.selected = true; // Primeira como padr├úo
                    selectPrincipal.appendChild(opt);
                });

                // Verifique se j├í existe um formul├írio, sen├úo crie um
                if (container.children.length === 0) {
                    adicionarLinhaPeridoDiverso();
                }
            } else {
                fieldset.classList.add('hidden');
                container.innerHTML = '';
            }
        };

        // Atualizar listas quando principal mudar
        $('resp-devedora-principal').onchange = (e) => {
            // Atualizar todos os dropdowns de reclamadas (centralizado)
            atualizarDropdownsReclamadas();
        };

        $('btn-adicionar-periodo').onclick = (e) => {
            e.preventDefault();
            adicionarLinhaPeridoDiverso();
        };

        // ÔöÇÔöÇÔöÇ PLANILHAS EXTRAS: REGISTRO E SINCRONIZA├ç├âO ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
        function registrarPlanilhaDisponivel(id, label, dados) {
            if (!window.hcalcState.planilhasDisponiveis) window.hcalcState.planilhasDisponiveis = [];
            // Substitui entrada com mesmo id (re-upload da mesma linha)
            window.hcalcState.planilhasDisponiveis =
                window.hcalcState.planilhasDisponiveis.filter(p => p.id !== id);
            window.hcalcState.planilhasDisponiveis.push({ id, label, dados });
            atualizarDropdownsPlanilhas();
        }

        function atualizarDropdownsPlanilhas() {
            const extras = window.hcalcState.planilhasDisponiveis || [];
            document.querySelectorAll('.periodo-planilha-select').forEach(sel => {
                const currentVal = sel.value;
                // Remove todas as op├º├Áes extras (mant├®m apenas 'principal')
                Array.from(sel.options).filter(o => o.value !== 'principal').forEach(o => o.remove());
                // Re-adiciona as dispon├¡veis
                extras.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `­ƒôè ${p.label}`;
                    sel.appendChild(opt);
                });
                // Restaura sele├º├úo anterior se ainda v├ílida
                if (Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
            });
        }

        function atualizarDropdownsReclamadas() {
            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';
           
            // Coletar todas as reclamadas j├í selecionadas em linhas existentes
            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });
           
            // Atualizar cada dropdown
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                const valorAtual = select.value;
               
                // Reconstruir op├º├Áes excluindo as j├í usadas (exceto a pr├│pria sele├º├úo)
                select.innerHTML = '<option value="">Selecione a reclamada...</option>';
                todasReclamadas.forEach(rec => {
                    if (!jaUsadas.has(rec) || rec === valorAtual) {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (rec === valorAtual) opt.selected = true;
                        select.appendChild(opt);
                    }
                });
            });
        }

        function adicionarLinhaPeridoDiverso() {
            const container = $('resp-diversos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';
            const idx = container.children.length;
            const rowId = `periodo-diverso-${idx}`;
            const numeroDevedora = idx + 2; // #1 ├® a principal, ent├úo come├ºa do #2

            const div = document.createElement('div');
            div.id = rowId;
            div.className = 'row';
            div.style.marginBottom = '15px';
            div.style.padding = '12px';
            div.style.backgroundColor = '#f5f5f5';
            div.style.borderRadius = '4px';

            // Filtrar: remover a principal integral E as j├í selecionadas em outras linhas
            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });
           
            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                if (!jaUsadas.has(rec)) {
                    selectOptions += `<option value="${rec}">${rec}</option>`;
                }
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Devedora #${numeroDevedora}</label>
                    <select class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Tipo de Responsabilidade</label>
                    <div style="display: flex; gap: 15px;">
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="subsidiaria" checked> Subsidi├íria</label>
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="principal"> Principal (Per├¡odo Parcial)</label>
                    </div>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <label>Per├¡odo (vazio = integral)</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Deixe vazio para per├¡odo integral" style="width: 100%; padding: 8px;">
                    </div>
                    <div style="flex: 1;">
                        <label>ID C├ílculo Separado</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="ID #XXXX" style="width: 100%; padding: 8px;">
                    </div>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold; font-size: 12px;">Planilha desta Devedora</label>
                    <div style="display: flex; gap: 8px; align-items: center; margin-top: 4px;">
                        <select class="periodo-planilha-select" data-idx="${idx}"
                                style="flex: 1; padding: 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="principal">­ƒôï Mesma planilha principal</option>
                        </select>
                        <button type="button" class="btn-carregar-planilha-extra btn-action"
                                data-idx="${idx}"
                                style="font-size: 11px; padding: 6px 10px; white-space: nowrap; background: #7c3aed;">
                            ­ƒôä Carregar Nova
                        </button>
                        <input type="file" class="input-planilha-extra-pdf" data-idx="${idx}"
                               accept=".pdf" style="display: none;">
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <label><input type="checkbox" class="periodo-total" data-idx="${idx}"> Per├¡odo Total</label>
                    <button type="button" class="btn-remover-periodo btn-action" data-idx="${idx}" data-row-id="${rowId}" style="padding: 8px; margin-left: auto; background: #d32f2f;">Remover</button>
                </div>
            `;
            container.appendChild(div);
           
            // ÔöÇÔöÇÔöÇ BOT├âO REMOVER: atualizar dropdowns ap├│s remo├º├úo ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            const btnRemover = div.querySelector(`.btn-remover-periodo[data-idx="${idx}"]`);
            btnRemover.onclick = () => {
                document.getElementById(rowId).remove();
                atualizarDropdownsReclamadas(); // Liberar reclamada de volta
            };
           
            // ÔöÇÔöÇÔöÇ AUTO-PREENCHER CAMPOS com planilha principal (padr├úo) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            const periodoInput = div.querySelector(`.periodo-periodo[data-idx="${idx}"]`);
            const idInput      = div.querySelector(`.periodo-id[data-idx="${idx}"]`);

            if (window.hcalcState.planilhaExtracaoData) {
                const pd = window.hcalcState.planilhaExtracaoData;
                if (periodoInput && pd.periodoCalculo) periodoInput.value = pd.periodoCalculo;
                if (idInput && pd.idPlanilha)          idInput.value      = pd.idPlanilha;
            }

            // ÔöÇÔöÇÔöÇ SELECT RECLAMADA: atualizar dropdowns quando selecionada ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            const selectReclamada = div.querySelector(`.periodo-reclamada[data-idx="${idx}"]`);
            selectReclamada.onchange = () => {
                // Atualizar todos os dropdowns para refletir nova sele├º├úo
                atualizarDropdownsReclamadas();
            };

            // ÔöÇÔöÇÔöÇ SELECT: trocar planilha ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            const selectPlanilha = div.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`);

            // Injetar planilhas j├í dispon├¡veis neste dropdown
            atualizarDropdownsPlanilhas();

            selectPlanilha.onchange = (e) => {
                const val = e.target.value;
                const pd = val === 'principal'
                    ? window.hcalcState.planilhaExtracaoData
                    : (window.hcalcState.planilhasDisponiveis || []).find(p => p.id === val)?.dados;
                if (!pd) return;
                if (pd.idPlanilha && idInput)           idInput.value      = pd.idPlanilha;
                if (pd.periodoCalculo && periodoInput)  periodoInput.value = pd.periodoCalculo;
            };

            // ÔöÇÔöÇÔöÇ BOT├âO CARREGAR NOVA PLANILHA ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
            const btnCarregar  = div.querySelector(`.btn-carregar-planilha-extra[data-idx="${idx}"]`);
            const inputExtra   = div.querySelector(`.input-planilha-extra-pdf[data-idx="${idx}"]`);

            btnCarregar.onclick = () => inputExtra.click();

            inputExtra.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                inputExtra.value = '';  // reset ÔÇö permite re-upload do mesmo arquivo

                const originalText = btnCarregar.textContent;
                btnCarregar.textContent = 'ÔÅ│...';
                btnCarregar.disabled = true;

                try {
                    const loaded = carregarPDFJSSeNecessario();
                    if (!loaded) throw new Error('PDF.js n├úo dispon├¡vel');

                    const dados = await processarPlanilhaPDF(file);
                    if (!dados.sucesso) throw new Error(dados.erro || 'Erro desconhecido');

                    // Preencher campos da linha com dados extra├¡dos
                    if (dados.idPlanilha && idInput)          idInput.value      = dados.idPlanilha;
                    if (dados.periodoCalculo && periodoInput) periodoInput.value = dados.periodoCalculo;

                    // Registrar como planilha dispon├¡vel para as demais linhas
                    const extraId    = `extra_${idx}`;
                    const extraLabel = `${dados.idPlanilha || 'Extra'} (Dev.${idx + 2})`;
                    registrarPlanilhaDisponivel(extraId, extraLabel, dados);

                    // Selecionar esta planilha no dropdown desta linha
                    selectPlanilha.value = extraId;

                    // Feedback visual
                    btnCarregar.textContent      = 'Ô£ô Analisada';
                    btnCarregar.style.background = '#10b981';
                    btnCarregar.disabled         = false;

                } catch (err) {
                    alert('Erro ao processar planilha: ' + err.message);
                    btnCarregar.textContent = originalText;
                    btnCarregar.disabled    = false;
                }
            };
        }

        $('chk-hon-reu').onchange = (e) => {
            // L├│gica invertida: marcado = "N├úo h├í" = esconde campos
            $('hon-reu-campos').classList.toggle('hidden', e.target.checked);
        };
       
        // Controlar exibi├º├úo de campo percentual vs valor
        document.querySelectorAll('input[name="rad-hon-reu-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const isPercentual = e.target.value === 'percentual';
                $('hon-reu-perc-campo').classList.toggle('hidden', !isPercentual);
                $('hon-reu-valor-campo').classList.toggle('hidden', isPercentual);
            });
        });
       
        $('chk-perito-conh').onchange = (e) => { $('perito-conh-campos').classList.toggle('hidden', !e.target.checked); };

        // CORRE├ç├âO 4: Event listener simplificado - guard interno em preencherDepositosAutomaticos
        $('chk-deposito').onchange = (e) => {
            // Toggle visibilidade
            $('deposito-campos').classList.toggle('hidden', !e.target.checked);
           
            // Preencher automaticamente se marcado (safe: tem guard para jaTemCampos)
            if (e.target.checked) {
                preencherDepositosAutomaticos();
            }
        };
       
        $('chk-pag-antecipado').onchange = (e) => {
            $('pag-antecipado-campos').classList.toggle('hidden', !e.target.checked);
            if (e.target.checked && window.hcalcState.pagamentosAntecipados.length === 0) {
                adicionarPagamentoAntecipado(); // Adiciona primeiro pagamento automaticamente
            }
        };

        // Event listeners para radios de tipo de libera├º├úo
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

        // ==========================================
        // ==========================================
        // FUN├ç├òES DE GERENCIAMENTO DE M├ÜLTIPLOS DEP├ôSITOS
        // ==========================================
       
        // Preenche dep├│sitos automaticamente com recursos detectados (Dep├│sito/Garantia)
        function preencherDepositosAutomaticos() {
            const prep = window.hcalcLastPrepResult;
            if (!prep || !prep.depositos || prep.depositos.length === 0) {
                console.log('[AUTO-DEPOSITOS] Sem dados de prep');
                return;
            }
           
            const container = $('depositos-container');
            if (!container) {
                console.error('[AUTO-DEPOSITOS] Container n├úo encontrado!');
                return;
            }
           
            // Se j├í tem campos, n├úo limpar (permite adicionar manualmente)
            const jaTemCampos = container.children.length > 0;
            if (jaTemCampos) {
                console.log('[AUTO-DEPOSITOS] Container j├í possui campos, pulando');
                return;
            }
           
            // Limpar dep├│sitos existentes apenas se estiver vazio
            container.innerHTML = '';
            window.hcalcState.nextDepositoIdx = 0;
            window.hcalcState.depositosRecursais = [];
           
            console.log('[AUTO-DEPOSITOS] Iniciando preenchimento com', prep.depositos.length, 'recursos');
           
            // Preencher com TODOS os dep├│sitos/garantias dos recursos detectados
            for (const deposito of prep.depositos) {
                // Filtrar anexos de tipo Dep├│sito ou Garantia
                const anexosRelevantes = (deposito.anexos || []).filter(ax =>
                    ax.tipo === 'Dep├│sito' || ax.tipo === 'Garantia'
                );
               
                // CORRE├ç├âO 3: Fallback para recursos sem anexos expandidos
                if (anexosRelevantes.length > 0) {
                    for (const anexo of anexosRelevantes) {
                        adicionarDepositoRecursal();
                        const idx = window.hcalcState.nextDepositoIdx - 1;
                       
                        const tipoSelect = $(`dep-tipo-${idx}`);
                        const depositanteSelect = $(`dep-depositante-${idx}`);
                        const idInput = $(`dep-id-${idx}`);
                       
                        if (tipoSelect) {
                            tipoSelect.value = anexo.tipo === 'Dep├│sito' ? 'bb' : 'garantia';
                            tipoSelect.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                       
                        if (depositanteSelect) {
                            depositanteSelect.value = deposito.depositante;
                        }
                       
                        if (idInput) {
                            idInput.value = anexo.id || '';
                        }
                    }
                    console.log('[AUTO-DEPOSITOS]', anexosRelevantes.length, 'dep├│sito(s) de', deposito.depositante);
                } else {
                    // FALLBACK: Recurso detectado mas sem anexos expandidos
                    console.warn('[AUTO-DEPOSITOS] Recurso sem anexos para', deposito.depositante, 'ÔÇö criando linha sem ID');
                    adicionarDepositoRecursal();
                    const idx = window.hcalcState.nextDepositoIdx - 1;
                    const depositanteSelect = $(`dep-depositante-${idx}`);
                    if (depositanteSelect) {
                        depositanteSelect.value = deposito.depositante || '';
                    }
                }
            }
        }
       
        function adicionarDepositoRecursal() {
            const idx = window.hcalcState.nextDepositoIdx++;
            const container = $('depositos-container');
           
            // Buscar TODAS as reclamadas do processo (n├úo s├│ as com recursos)
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
           
            const depositoDiv = document.createElement('div');
            depositoDiv.id = `deposito-item-${idx}`;
            depositoDiv.className = 'deposito-item';
            depositoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';
           
            // Construir op├º├Áes do select de depositante com TODAS as reclamadas do processo
            let optionsHtml = '<option value="">-- Selecione Reclamada --</option>';
            for (const nome of reclamadas) {
                optionsHtml += `<option value="${nome}">${nome}</option>`;
            }
           
            depositoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Dep├│sito Recursal #${idx + 1}</strong>
                    <button type="button" id="btn-remover-dep-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">Ô£ò Remover</button>
                </div>
                <div class="row">
                    <select id="dep-tipo-${idx}" data-dep-idx="${idx}">
                        <option value="bb" selected>Banco do Brasil</option>
                        <option value="sif">CEF (SIF)</option>
                        <option value="garantia">Seguro Garantia</option>
                    </select>
                    <select id="dep-depositante-${idx}" data-dep-idx="${idx}">
                        ${optionsHtml}
                    </select>
                    <input type="text" id="dep-id-${idx}" placeholder="ID da Guia" data-dep-idx="${idx}">
                </div>
                <div class="row" id="dep-principal-row-${idx}">
                    <label><input type="checkbox" id="dep-principal-${idx}" checked data-dep-idx="${idx}"> Depositado pela Devedora Principal?</label>
                </div>
                <div class="row hidden" id="dep-solidaria-info-${idx}" style="font-size: 11px; color: #059669; font-style: italic;">
                    Ô£ô Devedoras solid├írias: qualquer dep├│sito pode ser liberado
                </div>
                <div class="row" id="dep-liberacao-row-${idx}">
                    <label><input type="radio" name="rad-dep-lib-${idx}" value="reclamante" checked data-dep-idx="${idx}"> Libera├º├úo simples (Reclamante)</label>
                    <label style="margin-left: 10px;"><input type="radio" name="rad-dep-lib-${idx}" value="detalhada" data-dep-idx="${idx}"> Libera├º├úo detalhada (Cr├®dito, INSS, Hon.)</label>
                </div>
            `;
           
            container.appendChild(depositoDiv);
           
            // Event listeners para este dep├│sito espec├¡fico
            const tipoEl = $(`dep-tipo-${idx}`);
            const principalEl = $(`dep-principal-${idx}`);
            const liberacaoRow = $(`dep-liberacao-row-${idx}`);
           
            tipoEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', e.target.value === 'garantia');
            };
           
            principalEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', !e.target.checked);
            };
           
            // Atualizar visibilidade inicial baseado em tipo de responsabilidade
            atualizarVisibilidadeDepositoPrincipal(idx);
           
            // Event listener para bot├úo remover (evita problema sandbox TamperMonkey)
            const btnRemoverDep = depositoDiv.querySelector(`#btn-remover-dep-${idx}`);
            if (btnRemoverDep) {
                btnRemoverDep.addEventListener('click', () => {
                    depositoDiv.remove();
                    const dep = window.hcalcState.depositosRecursais.find(d => d.idx === idx);
                    if (dep) dep.removed = true;
                });
            }
           
            // Armazenar refer├¬ncia no estado
            window.hcalcState.depositosRecursais.push({ idx, removed: false });
        }
       
        function atualizarVisibilidadeDepositoPrincipal(idx) {
            const tipoResp = $('resp-tipo')?.value || 'unica';
            const isSolidaria = tipoResp === 'solidarias';
           
            const principalRow = $(`dep-principal-row-${idx}`);
            const solidariaInfo = $(`dep-solidaria-info-${idx}`);
            const principalChk = $(`dep-principal-${idx}`);
           
            if (principalRow && solidariaInfo) {
                if (isSolidaria) {
                    // Ocultar checkbox, mostrar info, for├ºar checked
                    principalRow.classList.add('hidden');
                    solidariaInfo.classList.remove('hidden');
                    if (principalChk) principalChk.checked = true;
                } else {
                    // Mostrar checkbox, ocultar info
                    principalRow.classList.remove('hidden');
                    solidariaInfo.classList.add('hidden');
                }
            }
        }
       
        function adicionarPagamentoAntecipado() {
            const idx = window.hcalcState.nextPagamentoIdx++;
            const container = $('pagamentos-container');
           
            const pagamentoDiv = document.createElement('div');
            pagamentoDiv.id = `pagamento-item-${idx}`;
            pagamentoDiv.className = 'pagamento-item';
            pagamentoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';
           
            pagamentoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Pagamento Antecipado #${idx + 1}</strong>
                    <button type="button" id="btn-remover-pag-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">Ô£ò Remover</button>
                </div>
                <div class="row">
                    <input type="text" id="pag-id-${idx}" placeholder="ID do Dep├│sito" data-pag-idx="${idx}">
                </div>
                <div class="row">
                    <label><input type="radio" name="lib-tipo-${idx}" value="nenhum" checked data-pag-idx="${idx}"> Padr├úo (extin├º├úo)</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="remanescente" data-pag-idx="${idx}"> Com Remanescente</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="devolucao" data-pag-idx="${idx}"> Com Devolu├º├úo</label>
                </div>
                <div id="lib-remanescente-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-rem-valor-${idx}" placeholder="Valor Remanescente (ex: 1.234,56)" data-pag-idx="${idx}">
                        <input type="text" id="lib-rem-titulo-${idx}" placeholder="T├¡tulo (ex: custas processuais)" data-pag-idx="${idx}">
                    </div>
                </div>
                <div id="lib-devolucao-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-dev-valor-${idx}" placeholder="Valor Devolu├º├úo (ex: 1.234,56)" data-pag-idx="${idx}">
                    </div>
                </div>
            `;
           
            container.appendChild(pagamentoDiv);
           
            // Event listeners para os radios deste pagamento
            document.querySelectorAll(`input[name="lib-tipo-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const valor = e.target.value;
                    $(`lib-remanescente-campos-${idx}`).classList.toggle('hidden', valor !== 'remanescente');
                    $(`lib-devolucao-campos-${idx}`).classList.toggle('hidden', valor !== 'devolucao');
                });
            });
           
            // Event listener para bot├úo remover (evita problema sandbox TamperMonkey)
            const btnRemoverPag = pagamentoDiv.querySelector(`#btn-remover-pag-${idx}`);
            if (btnRemoverPag) {
                btnRemoverPag.addEventListener('click', () => {
                    pagamentoDiv.remove();
                    const pag = window.hcalcState.pagamentosAntecipados.find(p => p.idx === idx);
                    if (pag) pag.removed = true;
                });
            }
           
            // Armazenar refer├¬ncia no estado
            window.hcalcState.pagamentosAntecipados.push({ idx, removed: false });
        }
       
        // Bind dos bot├Áes de adicionar
        $('btn-add-deposito').onclick = adicionarDepositoRecursal;
        $('btn-add-pagamento').onclick = adicionarPagamentoAntecipado;

        // M├íscara de data DD/MM/YYYY para campos de data
        const aplicarMascaraData = (input) => {
            input.addEventListener('input', (e) => {
                let valor = e.target.value.replace(/\D/g, ''); // Remove n├úo-d├¡gitos
                if (valor.length >= 2) {
                    valor = valor.slice(0, 2) + '/' + valor.slice(2);
                }
                if (valor.length >= 5) {
                    valor = valor.slice(0, 5) + '/' + valor.slice(5);
                }
                e.target.value = valor.slice(0, 10); // Limita a DD/MM/YYYY
            });
        };

        // Aplicar m├íscara aos campos de data
        ['val-data', 'custas-data-origem', 'val-perito-data'].forEach(id => {
            const campo = $(id);
            if (campo) aplicarMascaraData(campo);
        });

        // Toggle origem custas: Senten├ºa vs Ac├│rd├úo
        $('custas-origem').onchange = (e) => {
            const isAcordao = e.target.value === 'acordao';
            $('custas-data-col').classList.toggle('hidden', isAcordao);
            $('custas-acordao-col').classList.toggle('hidden', !isAcordao);
        };

        const ordemCopiaLabels = {
            'val-id': '1) Id da Planilha',
            'val-data': '1) Data da Atualiza├º├úo',
            'val-credito': '1) Cr├®dito Principal',
            'val-fgts': '1) FGTS Separado',
            'val-inss-rec': '2) INSS - Desconto Reclamante',
            'val-inss-total': '2) INSS - Total Empresa',
            'val-hon-autor': '3) Honor├írios do Autor',
            'val-custas': '4) Custas'
        };

        window.hcalcPeritosDetectados = [];
        window.hcalcPeritosConhecimentoDetectados = [];

        function isNomeRogerio(nome) {
            return /rogerio|rog├®rio/i.test(nome || '');
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

            // Controlar visibilidade do fieldset de per├¡cia conhecimento
            const fieldsetPericiaConh = $('fieldset-pericia-conh');
            if (peritosConhecimento.length > 0) {
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.remove('hidden');
                chkPeritoConhEl.checked = true;
                peritoConhCamposEl.classList.remove('hidden');
                valPeritoNomeEl.value = peritosConhecimento.join(' | ');
            } else {
                // Esconder card de per├¡cia se n├úo h├í perito de conhecimento
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.add('hidden');
            }
        }

        function atualizarStatusProximoCampo(nextInputId = null) {
            // Fun├º├úo simplificada - status removido da interface
            // Mantida para compatibilidade com c├│digo existente
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
                            <option value="diario">Di├írio (Advogado - Art. 523)</option>
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

                // Checkbox para marcar como principal (primeira ├® marcada por padr├úo)
                const isPrimeiraPorPadrao = idx === 0;
               
                divRow.innerHTML = `
                    <div style="flex: 1; font-size: 13px; font-weight: bold; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px;" title="${parte.nome}">
                        ${parte.nome}
                    </div>
                    <div style="flex-shrink: 0; display: flex; align-items: center; gap: 8px;">
                        <label style="font-size: 11px; margin: 0; display: flex; align-items: center; gap: 3px; color: #666;">
                            <input type="checkbox" class="chk-parte-principal" data-nome="${parte.nome}" ${isPrimeiraPorPadrao ? 'checked' : ''}>
                            Principal
                        </label>
                        <select class="sel-modo-intimacao" data-nome="${parte.nome}" style="padding: 4px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="diario" ${modoDefault === 'diario' ? 'selected' : ''}>Di├írio (Advogado - Art 523)</option>
                            <option value="mandado" ${modoDefault === 'mandado' ? 'selected' : ''}>Mandado (Art 880 - 48h)</option>
                            <option value="edital" ${modoDefault === 'edital' ? 'selected' : ''}>Edital (Art 880 - 48h)</option>
                            <option value="ignorar">N├úo Intimar</option>
                        </select>
                    </div>
                `;
                container.appendChild(divRow);
            });
        }

        async function refreshDetectedPartes() {
            const partes = await derivePartesData();

            // Armazenar globalmente para uso em gera├º├úo de textos
            window.hcalcPartesData = partes;

            const reclamadas = (partes?.passivo || []).map(p => p.nome).filter(Boolean);
            const peritos = ordenarComRogerioPrimeiro(extractPeritos(partes));
            const advogadosMap = extractAdvogadosPorReclamada(partes);
            const statusAdvMap = extractStatusAdvogadoPorReclamada(partes);
            const advogadosAutor = extractAdvogadosDoAutor(partes);

            window.hcalcStatusAdvogados = statusAdvMap;
            window.hcalcAdvogadosAutor = advogadosAutor; // Cache global para valida├º├úo de honor├írios
            window.hcalcPeritosDetectados = peritos; // Cache global para valida├º├úo de honor├írios

            // Log para debug
            console.log('hcalc: advogados por reclamada', advogadosMap);
            console.log('hcalc: status advogado por reclamada', statusAdvMap);
            console.log(`[hcalc] Detec├º├úo atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            aplicarRegrasPeritosDetectados(peritos);

            // Log de debug
            console.log(`[hcalc] Detec├º├úo atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            // L├ôGICA DE RESPONSABILIDADE DIN├éMICA
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
                    // S├│ 1 reclamada: preencher e travar
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

            // CONSTRUIR SE├ç├âO DE INTIMA├ç├òES
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
            const passivo = (dados?.PASSIVO || []).map((parte, idx) => buildRecord(parte, 'R├ëU', idx, dados.PASSIVO.length));
            const outros = (dados?.TERCEIROS || []).map((parte, idx) => buildRecord(parte, parte.tipo || 'TERCEIRO', idx, dados.TERCEIROS.length));

            return { ativo, passivo, outros };
        }

        async function fetchPartesViaApi() {
            const trtHost = window.location.host;
            const baseUrl = `https://${trtHost}`;
            const idProcesso = getProcessIdFromUrl();
            if (!idProcesso) {
                console.warn('hcalc: idProcesso n├úo detectado na URL.');
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

                // LIMITAR CACHE: Manter apenas ├║ltimas 5 entradas para prevenir crescimento ilimitado
                const keys = Object.keys(window.calcPartesCache);
                if (keys.length > 5) {
                    delete window.calcPartesCache[keys[0]];
                    console.log('hcalc: cache limitado a 5 entradas, removida mais antiga');
                }

                console.log('hcalc: partes extra├¡das via API', partes);
                return partes;
            } catch (error) {
                console.error('hcalc: falha ao buscar partes via API', error);
                return null;
            }
        }

        async function derivePartesData() {
            // Inicializar cache se n├úo existir
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

            // 3. Fallback: buscar qualquer cache dispon├¡vel
            const fallbackKey = processId ? Object.keys(cache).find((key) => key.includes(processId)) : null;
            if (fallbackKey) {
                console.log('hcalc: usando cache alternativo', cache[fallbackKey]);
                return cache[fallbackKey];
            }

            const cachedValues = Object.values(cache);
            if (cachedValues.length > 0) {
                console.log('hcalc: usando primeiro cache dispon├¡vel', cachedValues[0]);
                return cachedValues[0];
            }

            // 4. ├Ültimo recurso: parsear DOM
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
                } else if (/reclamado|r├®u|executado/i.test(text)) {
                    data.passivo.push({ nome: value });
                } else {
                    data.outros.push({ nome: value, tipo: 'OUTRO' });
                }
            });
            return data;
        }

        function extractPeritos(partes) {
            const outros = partes?.outros || [];
            // Filtrar por tipo 'PERITO' ou qualquer varia├º├úo no nome/tipo
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
        // FUN├ç├òES DE EXTRA├ç├âO DE REPRESENTANTES
        // ==========================================
        window.hcalcPartesData = null; // Cache global de partes para uso em gera├º├úo de textos

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

        function extractAdvogadosDoAutor(partes) {
            const advogados = [];
            if (!partes?.ativo) { return advogados; }
            partes.ativo.forEach((reclamante) => {
                const reps = reclamante.representantes || [];
                const advs = reps.filter(rep => {
                    const tipo = (rep.tipo || '').toUpperCase();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB');
                }).map(rep => ({
                    nome: rep.nome,
                    oab: rep.oab || '',
                    nomeNormalizado: normalizarNomeParaComparacao(rep.nome)
                }));
                advogados.push(...advs);
            });
            console.log('hcalc: advogados do autor extra├¡dos:', advogados);
            return advogados;
        }

        function verificarSeNomeEAdvogadoAutor(nomeParaVerificar, advogadosAutor) {
            if (!nomeParaVerificar || !advogadosAutor || advogadosAutor.length === 0) {
                return false;
            }
            const nomeNorm = normalizarNomeParaComparacao(nomeParaVerificar);
            return advogadosAutor.some(adv => {
                const match = adv.nomeNormalizado === nomeNorm ||
                              nomeNorm.includes(adv.nomeNormalizado) ||
                              adv.nomeNormalizado.includes(nomeNorm);
                if (match) {
                    console.log(`hcalc: match encontrado - "${nomeParaVerificar}" = advogado autor "${adv.nome}"`);
                }
                return match;
            });
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

        // OTIMIZA├ç├âO: adiar refresh at├® browser estar ocioso (n├úo compete com carregamento)
        if (typeof requestIdleCallback === 'function') {
            requestIdleCallback(() => refreshDetectedPartes(), { timeout: 3000 });
        } else {
            setTimeout(refreshDetectedPartes, 1500); // fallback para browsers sem rIC
        }

        // ==========================================
        // 4. L├ôGICA DE NAVEGA├ç├âO "COLETA INTELIGENTE"
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
        // 5. FUN├ç├òES AUXILIARES DE C├üLCULO E TEXTO
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
        // 6. GERADOR DE DECIS├âO HTML (O CORE)
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
            const pecaPerito = $('calc-peca-perito').value || '[ID PE├çA]';
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
                    introTxt += `As impugna├º├Áes apresentadas j├í foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os c├ílculos do expert (#${bold(idCalculo)}), `;
                } else {
                    introTxt += `Tendo em vista a concord├óncia das partes, HOMOLOGO os c├ílculos apresentados pelo(a) ${u(autoria)} (#${bold(idCalculo)}), `;
                }

                // Verificar se FGTS foi depositado (para evitar contradi├º├úo)
                const fgtsTipo = isFgtsSep ? (document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido') : 'devido';
                const fgtsJaDepositado = fgtsTipo === 'depositado';

                if (isFgtsSep && !fgtsJaDepositado) {
                    // FGTS devido (a ser recolhido)
                    introTxt += `fixando o cr├®dito do autor em ${bold(vCredito)} relativo ao principal, e ${bold(vFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(vData)}. `;
                } else if (isFgtsSep && fgtsJaDepositado) {
                    // FGTS depositado (n├úo menciona "a ser recolhido")
                    introTxt += `fixando o cr├®dito do autor em ${bold(vCredito)}, atualizado para ${bold(vData)}. `;
                } else {
                    // Sem FGTS separado
                    introTxt += `fixando o cr├®dito em ${bold(vCredito)}, referente ao valor principal, atualizado para ${bold(vData)}. `;
                }

                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualiza├º├úo foi feita na forma da Lei 14.905/2024 e da decis├úo da SDI-1 do C. TST (IPCA-E at├® a distribui├º├úo; taxa Selic at├® 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A corre├º├úo monet├íria foi realizada pelo IPCA-E na fase pr├®-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = usarPlaceholder ? 'XXX' : ($('val-juros').value || '[JUROS]');
                    const dtIngresso = usarPlaceholder ? 'XXX' : ($('data-ingresso').value || '[DATA INGRESSO]');
                    introTxt += `Atualiz├íveis pela TR/IPCA-E, conforme senten├ºa. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }

                if (reclamadaLabel) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${reclamadaLabel}</strong></p>`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                // 2┬║ par├ígrafo: FGTS depositado (com valor)
                if (isFgtsSep && fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><u>O FGTS devido, ${bold(vFgts)}, j├í foi depositado, portanto deduzido.</u></p>`;
                }

                if (!usarPlaceholder && $('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a aus├¬ncia do arquivo de origem, <u>dever├í a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }

                if (usarPlaceholder) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde j├í, ficam autorizados os descontos previdenci├írios (cota do reclamante) ora fixados em ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada, ainda, dever├í pagar o valor de sua cota-parte no INSS, a saber, ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as dedu├º├Áes fiscais de Imposto de Renda, fixadas em ${xxx()} para ${xxx()}, observem-se a S├║mula 368 do TST e IN RFB 1500/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais pela reclamada, no importe de ${xxx()}, para ${xxx()}.</p>`;
                    if ($('chk-hon-reu').checked) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">N├úo foram arbitrados honor├írios ao advogado do r├®u.</p>`;
                    } else {
                        const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                        if (rdHonReu === 'suspensiva') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios pela reclamante sob condi├º├úo suspensiva, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais em favor da reclamada na ordem de ${xxx()}.</p>`;
                        }
                    }
                    return;
                }

                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do cr├®dito, n├úo h├í contribui├º├Áes previdenci├írias devidas.</p>`;
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
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada dever├í pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde j├í, ficam autorizados os descontos previdenci├írios (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}.</p>`;
                }

                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">N├úo h├í dedu├º├Áes fiscais cab├¡veis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tribut├íveis (${bold('R$' + vBase)}), pelo per├¡odo de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as dedu├º├Áes fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a S├║mula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }

                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }

                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">N├úo foram arbitrados honor├írios ao advogado do r├®u.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;
                   
                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios pela reclamante sob condi├º├úo suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do cr├®dito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios pela reclamante sob condi├º├úo suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do cr├®dito do autor.</p>`;
                        }
                    }
                }
            };

            // Fun├º├úo unificada para libera├º├úo detalhada (dep├│sito recursal ou pagamento antecipado)
            const gerarLiberacaoDetalhada = (contexto) => {
                const { prefixo = '', depositoInfo = '' } = contexto;

                // Linha inicial com refer├¬ncia ├á planilha
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Passo ├á libera├º├úo de valores conforme planilha #${bold(idPlanilha)}:</p>`;

                let numLiberacao = 1;

                // 1) Cr├®dito do reclamante
                if (depositoInfo) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante ${depositoInfo}, no valor de ${bold('R$' + valCredito)}, expedindo-se alvar├í eletr├┤nico.</p>`;
                } else {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante seu cr├®dito, no valor de ${bold('R$' + valCredito)}, expedindo-se alvar├í eletr├┤nico.</p>`;
                }
                numLiberacao++;

                // 2) INSS (se n├úo ignorado)
                if (!ignorarInss) {
                    const valInssRec = normalizeMoneyInput($('val-inss-rec').value || '0,00');
                    const valInssTotal = normalizeMoneyInput($('val-inss-total').value || '0,00');

                    // Calcular INSS patronal
                    const isPjeCalc = $('calc-pjc').checked;
                    let inssEmpregado = valInssRec; // parte empregado - sempre valor do reclamante
                    let inssPatronal = valInssTotal; // parte patronal/reclamada

                    // Se ├® PJC: patronal = total - empregado
                    if (isPjeCalc && valInssTotal && valInssRec) {
                        const totalNum = parseMoney(valInssTotal);
                        const recNum = parseMoney(valInssRec);
                        const patronalNum = totalNum - recNum;
                        inssPatronal = formatMoney(patronalNum);
                    }
                    // Se n├úo ├® PJC: usa direto o valInssTotal

                    const totalInss = valInssTotal;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Proceda a Secretaria ├á transfer├¬ncia de valores ao ├│rg├úo competente, via Siscondj, sendo: ${bold('R$ ' + inssEmpregado)} referente ├ás contribui├º├Áes previdenci├írias parte empregado e ${bold('R$ ' + inssPatronal)} no que concernem ├ás contribui├º├Áes patronais (total de ${bold('R$ ' + totalInss)}).</p>`;
                    numLiberacao++;
                }

                // 3) Honor├írios periciais (se houver)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';

                // Perito cont├íbil (Rog├®rio) - se houver
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(peritoContabilDetectado)} seus honor├írios, no valor de ${bold('R$' + vContabil)}.</p>`;
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
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(nomePerito)} seus honor├írios, no valor de ${bold('R$' + vP)}.</p>`;
                            numLiberacao++;
                        }
                    });
                }

                // 4) Honor├írios do advogado do autor (se n├úo ignorado)
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao patrono da parte autora seus honor├írios, no valor de ${bold('R$' + vHonA)}.</p>`;
                    numLiberacao++;
                }

                // Retornar o n├║mero da pr├│xima libera├º├úo (para devolu├º├úo)
                return numLiberacao;
            };

            const appendDisposicoesFinais = () => {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>Disposi├º├Áes finais:</strong></p>`;

                // CONT├üBIL PRIMEIRO (Rog├®rio)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios cont├íbeis em favor de ${bold(peritoContabilDetectado)}, ora arbitrados em ${bold(vContabil)}.</p>`;
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

                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios periciais da fase de conhecimento assim estabelecidos:</p>`;

                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia === 'trt') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagos pelo TRT, considerando a sucumb├¬ncia do autor no objeto da per├¡cia (#${bold(vP)}).</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagamento de ${bold('R$' + vP)} pela reclamada, para ${bold(dtP)}.</p>`;
                        }
                    });
                }

                if ($('custas-status').value === 'pagas') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas pagas em raz├úo de recurso.</p>`;
                } else {
                    const valC = $('val-custas').value || '[VALOR]';
                    const origemCustas = $('custas-origem').value;

                    if (valC && valC !== '0,00' && valC !== '0') {
                        if (origemCustas === 'acordao') {
                            // Custas por ac├│rd├úo (inclui ID do ac├│rd├úo no texto)
                            const acordaoIdx = $('custas-acordao-select').value;
                            const acordaoSel = $('custas-acordao-select').selectedOptions[0];
                            const dataAcordao = acordaoSel?.dataset?.data || '[DATA AC├ôRD├âO]';
                            const idAcordao = acordaoSel?.dataset?.id || '';
                            const idTexto = idAcordao ? ` #${bold(idAcordao)}` : '';
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas definidas em ac├│rd├úo${idTexto}, pela reclamada, no valor de ${bold('R$' + valC)} para ${bold(dataAcordao)}.</p>`;
                        } else {
                            // Custas por senten├ºa (padr├úo)
                            const dataCustas = $('custas-data-origem').value || valData;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas de ${bold('R$' + valC)} pela reclamada, para ${bold(dataCustas)}.</p>`;
                        }
                    }
                }

                // ==========================================
                // DEP├ôSITOS RECURSAIS (m├║ltiplos)
                // ==========================================
                if ($('chk-deposito').checked) {
                    const passivoDetectado = (window.hcalcPartesData?.passivo || []).map((p) => p?.nome).filter(Boolean);
                    const primeiraReclamada = passivoDetectado[0] || '';
                    const tipoRespAtual = $('resp-tipo')?.value || 'unica';
                   
                    // Coletar todos os dep├│sitos v├ílidos (n├úo removidos)
                    const depositosValidos = window.hcalcState.depositosRecursais
                        .filter(d => !d.removed)
                        .map(d => {
                            const idx = d.idx;
                            const tDep = $(`dep-tipo-${idx}`)?.value || 'bb';
                            const dNome = $(`dep-depositante-${idx}`)?.value || '[RECLAMADA]';
                            const dId = $(`dep-id-${idx}`)?.value || '[ID]';
                            let isPrin = $(`dep-principal-${idx}`)?.checked ?? true;
                            const liberacao = document.querySelector(`input[name="rad-dep-lib-${idx}"]:checked`)?.value || 'reclamante';
                           
                            const isDepositoJudicial = tDep !== 'garantia';
                            let criterioLiberacaoDeposito = 'manual';
                            let depositanteResolvida = dNome;
                           
                            // Auto-resolver depositante baseado em partes detectadas
                            if (passivoDetectado.length === 1) {
                                depositanteResolvida = passivoDetectado[0];
                                isPrin = true;
                                criterioLiberacaoDeposito = 'reclamada-unica';
                            } else if (tipoRespAtual === 'subsidiarias' && primeiraReclamada && isPrin) {
                                depositanteResolvida = primeiraReclamada;
                                criterioLiberacaoDeposito = 'subsidiaria-principal';
                            } else if (tipoRespAtual === 'solidarias') {
                                // Solid├írias: qualquer dep├│sito pode ser liberado
                                depositanteResolvida = depositanteResolvida || primeiraReclamada || '[RECLAMADA]';
                                isPrin = true; // For├ºar como principal (todas s├úo principais em solid├íria)
                                criterioLiberacaoDeposito = 'solidaria';
                            }
                           
                            const deveLiberarDeposito = isDepositoJudicial && (
                                criterioLiberacaoDeposito === 'reclamada-unica' ||
                                criterioLiberacaoDeposito === 'subsidiaria-principal' ||
                                criterioLiberacaoDeposito === 'solidaria' ||
                                (criterioLiberacaoDeposito === 'manual' && isPrin)
                            );
                           
                            const naturezaDevedora = criterioLiberacaoDeposito === 'solidaria'
                                ? 'solid├íria'
                                : (isPrin ? 'principal' : 'subsidi├íria');
                           
                            const bancoTxt = tDep === 'bb' ? 'Banco do Brasil' : (tDep === 'sif' ? 'Caixa Econ├┤mica Federal (SIF)' : 'seguro garantia regular');
                           
                            return {
                                idx, tDep, depositanteResolvida, dId, isPrin, liberacao,
                                isDepositoJudicial, naturezaDevedora, bancoTxt, deveLiberarDeposito
                            };
                        });
                   
                    if (depositosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">H├í dep├│sito recursal. (Configure os dados)</p>`;
                    } else {
                        // Agrupar dep├│sitos por depositante + tipo
                        const grupos = {};
                        depositosValidos.forEach(dep => {
                            const chave = `${dep.depositanteResolvida}|${dep.naturezaDevedora}|${dep.bancoTxt}`;
                            if (!grupos[chave]) {
                                grupos[chave] = {
                                    depositante: dep.depositanteResolvida,
                                    natureza: dep.naturezaDevedora,
                                    banco: dep.bancoTxt,
                                    depositos: [],
                                    todosGarantia: true,
                                    todosLiberacaoDireta: true
                                };
                            }
                            grupos[chave].depositos.push(dep);
                            if (dep.isDepositoJudicial) grupos[chave].todosGarantia = false;
                            if (dep.liberacao !== 'reclamante') grupos[chave].todosLiberacaoDireta = false;
                        });
                       
                        const formatarLista = (itens) => {
                            if (!itens || itens.length === 0) { return ''; }
                            if (itens.length === 1) { return itens[0]; }
                            if (itens.length === 2) { return `${itens[0]} e ${itens[1]}`; }
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };
                       
                        // Gerar texto para cada grupo
                        Object.values(grupos).forEach(grupo => {
                            const ids = grupo.depositos.map(d => `${bold(d.dId)}`);
                            const idsTexto = ids.length > 1 ? `(Ids ${formatarLista(ids)})` : `(Id ${ids[0]})`;
                           
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">H├í dep├│sito${grupo.depositos.length > 1 ? 's' : ''} recursal${grupo.depositos.length > 1 ? 'is' : ''} da devedora ${grupo.natureza} (${grupo.depositante} ${idsTexto}) via ${grupo.banco}.</p>`;
                           
                            if (grupo.todosGarantia) {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Tratando-se de seguro garantia, n├úo h├í libera├º├úo imediata de valores nesta oportunidade.</p>`;
                            } else {
                                // Processar libera├º├Áes
                                const depsLiberaveis = grupo.depositos.filter(d => d.deveLiberarDeposito && d.isDepositoJudicial);
                               
                                if (depsLiberaveis.length > 0) {
                                    const depsDiretos = depsLiberaveis.filter(d => d.liberacao === 'reclamante');
                                    const depsDetalhados = depsLiberaveis.filter(d => d.liberacao === 'detalhada');
                                   
                                    if (depsDiretos.length > 0) {
                                        houveDepositoDireto = true;
                                        const txtPlural = depsDiretos.length > 1 ? 'os dep├│sitos recursais' : 'o dep├│sito recursal';
                                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Libere-se ${txtPlural} em favor do reclamante. Ap├│s, apure-se o remanescente devido.</p>`;
                                    }
                                   
                                    if (depsDetalhados.length > 0) {
                                        const idsDetalhados = depsDetalhados.map(d => `${grupo.depositante} #${bold(d.dId)}`);
                                        const listaDeps = formatarLista(idsDetalhados);
                                       
                                        houveLibecaoDetalhada = true;
                                        gerarLiberacaoDetalhada({
                                            depositoInfo: `o${depsDetalhados.length > 1 ? 's' : ''} dep├│sito${depsDetalhados.length > 1 ? 's' : ''} recursal${depsDetalhados.length > 1 ? 'is' : ''} (${listaDeps} via ${grupo.banco})`
                                        });
                                    }
                                } else {
                                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Por ora, n├úo h├í libera├º├úo autom├ítica do${grupo.depositos.length > 1 ? 's' : ''} dep├│sito${grupo.depositos.length > 1 ? 's' : ''} recursal${grupo.depositos.length > 1 ? 'is' : ''} informado${grupo.depositos.length > 1 ? 's' : ''}.</p>`;
                                }
                            }
                        });
                    }
                }

                // ==========================================
                // PAGAMENTOS ANTECIPADOS (m├║ltiplos)
                // ==========================================
                const isPagamentoAntecipado = $('chk-pag-antecipado').checked;
                if (isPagamentoAntecipado) {
                    const pagamentosValidos = window.hcalcState.pagamentosAntecipados
                        .filter(p => !p.removed)
                        .map(p => {
                            const idx = p.idx;
                            return {
                                idx,
                                id: $(`pag-id-${idx}`)?.value || '[ID]',
                                tipoLib: document.querySelector(`input[name="lib-tipo-${idx}"]:checked`)?.value || 'nenhum',
                                remValor: $(`lib-rem-valor-${idx}`)?.value || '',
                                remTitulo: $(`lib-rem-titulo-${idx}`)?.value || '',
                                devValor: $(`lib-dev-valor-${idx}`)?.value || ''
                            };
                        });
                   
                    if (pagamentosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado dep├│sito pela reclamada. (Configure os dados)</p>`;
                    } else {
                        pagamentosValidos.forEach(pag => {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado dep├│sito pela reclamada, #${bold(pag.id)}.</p>`;
                           
                            houveLibecaoDetalhada = true;
                            let proximoNum = gerarLiberacaoDetalhada({});
                           
                            if (pag.tipoLib === 'devolucao') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${proximoNum}) Devolva-se ├á reclamada o valor pago a maior, no montante de ${bold('R$ ' + (pag.devValor || '[VALOR]'))}, expedindo-se o competente alvar├í.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifesta├º├úo das partes.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ap├│s, tornem conclusos para extin├º├úo da execu├º├úo.</p>`;
                            } else if (pag.tipoLib === 'remanescente') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem preju├¡zo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + (pag.remValor || '[VALOR]'))} devidos a t├¡tulo de ${bold(pag.remTitulo || '[T├ìTULO]')}, em 15 dias, sob pena de execu├º├úo.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
                            } else {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifesta├º├Áes. Silentes, cumpra-se e, ap├│s, tornem conclusos para extin├º├úo da execu├º├úo.</p>`;
                            }
                        });
                    }
                }
               
                // INTIMA├ç├òES (apenas se N├âO houver pagamento antecipado)
                if (!isPagamentoAntecipado) {
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

                    // Verificar se ├® responsabilidade subsidi├íria
                    const isSubsidiaria = $('resp-tipo')?.value === 'subsidiarias';
                   
                    // Obter lista de principais (marcadas como principal)
                    const principaisSet = new Set();
                    if (isSubsidiaria) {
                        document.querySelectorAll('.chk-parte-principal:checked').forEach(chk => {
                            principaisSet.add(chk.getAttribute('data-nome'));
                        });
                    }

                    if (elsOpcoes.length > 0) {
                        elsOpcoes.forEach((sel) => {
                            const nome = sel.getAttribute('data-nome');
                            const v = sel.value;
                           
                            // FILTRO: Se subsidi├íria, intima apenas principais
                            if (isSubsidiaria && !principaisSet.has(nome)) {
                                return; // Pula subsidi├írias
                            }
                           
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
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ap├│s referida atualiza├º├úo, ${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
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

            // ==========================================
            // GERA├ç├âO DE TEXTO - RESPONSABILIDADES
            // ==========================================
            function gerarTextoResponsabilidades() {
                const formatarLista = (nomes) => {
                    if (nomes.length === 0) return '';
                    if (nomes.length === 1) return bold(nomes[0]);
                    if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                    const ultimos = nomes.slice(-2);
                    const anteriores = nomes.slice(0, -2);
                    return `${anteriores.map(n => bold(n)).join(', ')}, ${bold(ultimos[0])} e ${bold(ultimos[1])}`;
                };

                const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
                if (linhasPeriodos.length === 0) return null;

                const principalSelecionada = $('resp-devedora-principal')?.value || '1';
                const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
                const principaisParciais = [];
                const subsidiariasComPeriodo = [];
               
                linhasPeriodos.forEach((linha) => {
                    const idx = linha.id.replace('periodo-diverso-', '');
                    const nomeRec = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || '';
                    const periodoTexto = document.querySelector(`.periodo-periodo[data-idx="${idx}"]`)?.value || '';
                    const idPlanilha = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || '';
                    const tipoRadio = document.querySelector(`input[name="periodo-tipo-${idx}"]:checked`)?.value || 'principal';
                   
                    // NOVO: detectar se usa mesma planilha da principal
                    const planilhaSel = document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`)?.value || 'principal';
                    const usarMesmaPlanilha = planilhaSel === 'principal';
                   
                    // Per├¡odo vazio ou igual ao per├¡odo completo = integral
                    const isPeriodoIntegral = !periodoTexto || periodoTexto === periodoCompleto;
                   
                    if (nomeRec && !isPeriodoIntegral) {
                        if (tipoRadio === 'principal') {
                            principaisParciais.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilha || '', usarMesmaPlanilha });
                        } else {
                            subsidiariasComPeriodo.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilha || '', usarMesmaPlanilha });
                        }
                    }
                });

                // Identificar subsidi├írias integrais (reclamadas que N├âO s├úo principais e N├âO est├úo em per├¡odos)
                const principaisNomes = new Set([principalSelecionada, ...principaisParciais.map(p => p.nome)]);
                const subsidiariasComPeriodoNomes = new Set(subsidiariasComPeriodo.map(s => s.nome));
                const todasReclamadas = Array.from(document.querySelectorAll('.chk-parte-principal'))
                    .map(chk => chk.getAttribute('data-nome'))
                    .filter(n => n);
               
                const subsidiariasIntegrais = todasReclamadas.filter(nome =>
                    !principaisNomes.has(nome) && !subsidiariasComPeriodoNomes.has(nome)
                );

                let textoIntro = '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sobre a responsabilidade pelo cr├®dito, tem-se o seguinte:</p>';
                textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>1 - Devedoras Principais:</strong></p>';
                textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(principalSelecionada)} ├® devedora principal pelo per├¡odo integral do contrato.</p>`;
               
                principaisParciais.forEach(prin => {
                    textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(prin.nome)} tamb├®m ├® principal, mas pelo per├¡odo parcial de ${prin.periodo}.</p>`;
                });

                const todasSubsidiarias = [...subsidiariasIntegrais, ...subsidiariasComPeriodo];
                if (todasSubsidiarias.length > 0) {
                    textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>2 - Devedoras Subsidi├írias:</strong></p>';
                   
                    // Subsidi├írias integrais (agrupadas)
                    if (subsidiariasIntegrais.length > 0) {
                        const listaFormatada = formatarLista(subsidiariasIntegrais);
                        const verbo = subsidiariasIntegrais.length === 1 ? '├® respons├ível subsidi├íria' : 's├úo respons├íveis subsidi├írias';
                        textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${listaFormatada} ${verbo} pelo per├¡odo integral do contrato.</p>`;
                    }
                   
                    // Subsidi├írias com per├¡odo espec├¡fico (individuais)
                    subsidiariasComPeriodo.forEach(sub => {
                        textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(sub.nome)} ├® respons├ível subsidi├íria pelo per├¡odo de ${sub.periodo}.</p>`;
                    });
                }

                textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ap├│s isso, passo ├ás homologa├º├Áes espec├¡ficas:</p>';

                return {
                    textoIntro,
                    principalIntegral: principalSelecionada,
                    principaisParciais,
                    subsidiarias: todasSubsidiarias,
                    subsidiariasIntegrais,
                    subsidiariasComPeriodo,
                    todasPrincipais: [
                        { nome: principalSelecionada, periodo: 'integral', idPlanilha: '' },
                        ...principaisParciais
                    ]
                };
            }

                        const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
            const usarDuplicacao = $('resp-diversos').checked && linhasPeriodos.length > 0;

            if (usarDuplicacao && passivoTotal > 1) {
                const dadosResp = gerarTextoResponsabilidades();
               
                if (dadosResp) {
                    const { textoIntro, todasPrincipais, subsidiariasIntegrais, subsidiariasComPeriodo } = dadosResp;
                    const principalIntegral = todasPrincipais[0];
                   
                    text += textoIntro;
                   
                    text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>1 - Devedoras Principais:</strong></p>';
                   
                    todasPrincipais.forEach((prin, i) => {
                        const letra = String.fromCharCode(97 + i);
                        const labelPrin = prin.periodo === 'integral'
                            ? `${bold(prin.nome)} (Per├¡odo Integral)`
                            : `${bold(prin.nome)} (${prin.periodo})`;
                       
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${letra}) Reclamada ${labelPrin}:</strong></p>`;
                       
                        const idParaUsar = prin.periodo === 'integral'
                            ? idPlanilha
                            : (prin.usarMesmaPlanilha || !prin.idPlanilha ? idPlanilha : prin.idPlanilha);

                        // placeholder=false se usa mesma planilha (valores j├í est├úo no form principal)
                        // placeholder=true  se tem per├¡odo parcial mas sem planilha pr├│pria nem principal
                        const usarPlaceholder = prin.periodo !== 'integral' && !prin.usarMesmaPlanilha && !prin.idPlanilha;

                        appendBaseAteAntesPericiais({
                            idCalculo: idParaUsar,
                            usarPlaceholder: usarPlaceholder,
                            reclamadaLabel: ''
                        });
                    });
                   
                    const totalSubsidiarias = subsidiariasIntegrais.length + subsidiariasComPeriodo.length;
                    if (totalSubsidiarias > 0) {
                        text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>2 - Devedoras Subsidi├írias:</strong></p>';
                        text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">(Respondem apenas em caso de insufici├¬ncia patrimonial das principais)</p>';
                       
                        let letraIdx = 0;
                       
                        // Subsidi├írias integrais (agrupadas)
                        subsidiariasIntegrais.forEach((nomeSub) => {
                            const letra = String.fromCharCode(97 + letraIdx);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${letra}) Reclamada ${bold(nomeSub)}:</p>`;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><em>Subsidi├íria pelo per├¡odo integral do contrato, com os mesmos valores definidos para a devedora principal <strong>${principalIntegral.nome}</strong>, conforme planilha <strong>${idPlanilha}</strong>.</em></p>`;
                            letraIdx++;
                        });
                       
                        // Subsidi├írias com per├¡odo espec├¡fico
                        subsidiariasComPeriodo.forEach((sub) => {
                            const letra = String.fromCharCode(97 + letraIdx);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${letra}) Reclamada ${bold(sub.nome)}</strong></p>`;

                            if (sub.usarMesmaPlanilha) {
                                // ÔöÇÔöÇ CASO 1: mesma planilha da principal ÔåÆ texto simplificado ÔöÇÔöÇ
                                const nomePrincipal = principalIntegral;
                                const idPrincipalUsar = idPlanilha; // val-id.value ÔÇö planilha principal
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">
                                    <em>Subsidi├íria pelo per├¡odo de <strong>${sub.periodo}</strong>.
                                    Os valores s├úo os mesmos definidos para a devedora principal
                                    <strong>${nomePrincipal}</strong>, conforme planilha <strong>${idPrincipalUsar}</strong>,
                                    n├úo sendo necess├íria homologa├º├úo em separado.</em></p>`;
                            } else {
                                // ÔöÇÔöÇ CASO 2: planilha pr├│pria carregada ou sem planilha ÔöÇÔöÇ
                                const idSubPlanilha = sub.idPlanilha || idPlanilha;
                                const comPlaceholder = !sub.idPlanilha; // sem planilha pr├│pria = placeholder
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">
                                    <em>Subsidi├íria pelo per├¡odo de <strong>${sub.periodo}</strong>.</em></p>`;
                                appendBaseAteAntesPericiais({
                                    idCalculo: idSubPlanilha,
                                    usarPlaceholder: comPlaceholder,
                                    reclamadaLabel: sub.nome
                                });
                            }
                            letraIdx++;
                        });
                    }
                }

                appendDisposicoesFinais();
            } else {
                let introTxt = '';
                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugna├º├Áes apresentadas j├í foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os c├ílculos do expert (#${bold(idPlanilha)}), `;
                } else {
                    introTxt += `Tendo em vista a concord├óncia das partes, HOMOLOGO os c├ílculos apresentados pelo(a) ${u(autoria)} (#${bold(idPlanilha)}), `;
                }

                // Verificar se FGTS foi depositado (para evitar contradi├º├úo)
                const fgtsTipo = isFgtsSep ? (document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido') : 'devido';
                const fgtsJaDepositado = fgtsTipo === 'depositado';

                if (isFgtsSep && !fgtsJaDepositado) {
                    // FGTS devido (a ser recolhido)
                    introTxt += `fixando o cr├®dito do autor em ${bold('R$' + valCredito)} relativo ao principal, e ${bold('R$' + valFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(valData)}. `;
                } else if (isFgtsSep && fgtsJaDepositado) {
                    // FGTS depositado (n├úo menciona "a ser recolhido")
                    introTxt += `fixando o cr├®dito do autor em ${bold('R$' + valCredito)}, atualizado para ${bold(valData)}. `;
                } else {
                    introTxt += `fixando o cr├®dito em ${bold('R$' + valCredito)}, referente ao valor principal, atualizado para ${bold(valData)}. `;
                }
                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualiza├º├úo foi feita na forma da Lei 14.905/2024 e da decis├úo da SDI-1 do C. TST (IPCA-E at├® a distribui├º├úo; taxa Selic at├® 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A corre├º├úo monet├íria foi realizada pelo IPCA-E na fase pr├®-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = $('val-juros').value || '[JUROS]';
                    const dtIngresso = $('data-ingresso').value || '[DATA INGRESSO]';
                    introTxt += `Atualiz├íveis pela TR/IPCA-E, conforme senten├ºa. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                // 2┬║ par├ígrafo: FGTS depositado (com valor)
                if (isFgtsSep && fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><u>O FGTS devido, ${bold('R$' + valFgts)}, j├í foi depositado, portanto deduzido.</u></p>`;
                }

                if (passivoTotal > 1) {
                    if ($('resp-tipo').value === 'solidarias') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Declaro que as reclamadas respondem de forma solid├íria pela presente execu├º├úo.</p>`;
                    } else if ($('resp-tipo').value === 'subsidiarias') {
                        if ($('resp-integral').checked) {
                            // Obter lista de principais e subsidi├írias
                            const principais = [];
                            const subsidiarias = [];
                           
                            document.querySelectorAll('.chk-parte-principal').forEach(chk => {
                                const nome = chk.getAttribute('data-nome');
                                if (chk.checked) {
                                    principais.push(nome);
                                } else {
                                    subsidiarias.push(nome);
                                }
                            });
                           
                            // Texto espec├¡fico nomeando principais e subsidi├írias
                            if (principais.length > 0 && subsidiarias.length > 0) {
                                const formatarLista = (nomes) => {
                                    if (nomes.length === 1) return bold(nomes[0]);
                                    if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                                    return nomes.slice(0, -1).map(n => bold(n)).join(', ') + ' e ' + bold(nomes[nomes.length - 1]);
                                };
                               
                                const txtPrincipais = formatarLista(principais);
                                const txtSubsidiarias = formatarLista(subsidiarias);
                                const verboPrin = principais.length > 1 ? 's├úo devedoras principais' : '├® devedora principal';
                                const verboSub = subsidiarias.length > 1 ? 's├úo subsidi├írias' : '├® subsidi├íria';
                               
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${txtPrincipais} ${verboPrin}, ${txtSubsidiarias} ${verboSub} pelo per├¡odo integral do contrato, portanto, os valores neste momento s├úo devidos apenas pelas principais.</p>`;
                            } else {
                                // Fallback se n├úo houver checkboxes marcados
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A primeira reclamada ├® devedora principal, as demais s├úo subsidi├írias pelo per├¡odo integral do contrato, portanto, os valores neste momento s├úo devidos apenas pela primeira.</p>`;
                            }
                        }
                    }
                }
                if ($('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a aus├¬ncia do arquivo de origem, <u>dever├í a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }
                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do cr├®dito, n├úo h├í contribui├º├Áes previdenci├írias devidas.</p>`;
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
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada dever├í pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde j├í, ficam autorizados os descontos previdenci├írios (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}.</p>`;
                }
                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">N├úo h├í dedu├º├Áes fiscais cab├¡veis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tribut├íveis (${bold('R$' + vBase)}), pelo per├¡odo de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as dedu├º├Áes fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a S├║mula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }
                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">N├úo foram arbitrados honor├írios ao advogado do r├®u.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;
                   
                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios pela reclamante sob condi├º├úo suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do cr├®dito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios pela reclamante sob condi├º├úo suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honor├írios advocat├¡cios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do cr├®dito do autor.</p>`;
                        }
                    }
                }
                appendDisposicoesFinais();
            }

            // Linha final - OMITIR se houver libera├º├úo detalhada (dep├│sito recursal ou pagamento antecipado)
            if (!houveLibecaoDetalhada) {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${u('Ficam as partes cientes de que qualquer questionamento acerca desta decis├úo, salvo erro material, ser├í apreciado ap├│s a garantia do ju├¡zo.')}</p>`;
            }
            const blob = new Blob([text], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            navigator.clipboard.write([clipboardItem]).then(() => {
                alert('Decis├úo copiada com sucesso! V├í ao editor do PJe e cole (Ctrl+V).');
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

    // Ponto de entrada exposto para hcalc.user.js
    window.hcalcInitBotao = initializeBotao;
})();


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
    async function buscarPartesEdital(editaisItems, passivo, signal) {
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

            const resHtml = await lerHtmlOriginal(6000, signal);
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
                prepResult.partesIntimadasEdital = await buscarPartesEdital(timeline.editais, passivoArray, signal);
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
