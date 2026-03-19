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
