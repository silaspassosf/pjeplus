// =====================================================================
// EXTRATOR SISCON - Console JavaScript
// =====================================================================
// Baseado na função def_siscon e extrair_dados_siscon do pec.py
// Uso: Copie e cole no console do navegador na página do Alvará Eletrônico
// URL: https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar

(function() {
    'use strict';
    
    // ===== VERIFICAR URL =====
    function verificarURL() {
        const urlAtual = window.location.href;
        const urlEsperada = 'https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar';
        
        if (!urlAtual.includes('alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar')) {
            console.warn('⚠️ SISCON EXTRACTOR: URL incorreta!');
            console.warn('📍 Navegue para: ' + urlEsperada);
            return false;
        }
        
        console.log('✅ SISCON EXTRACTOR: URL correta detectada');
        return true;
    }
    
    // ===== CRIAR BOTÃO EXTRAIR =====
    function criarBotaoExtrair() {
        // Remove botão existente se houver
        const botaoExistente = document.getElementById('botaoExtrairSiscon');
        if (botaoExistente) {
            botaoExistente.remove();
        }
        
        // Criar botão
        const botao = document.createElement('button');
        botao.id = 'botaoExtrairSiscon';
        botao.innerHTML = '📊 Extrair Dados SISCON';
        botao.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 12px 20px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        `;
        
        // Hover effects
        botao.onmouseover = function() {
            this.style.transform = 'scale(1.05)';
            this.style.boxShadow = '0 6px 12px rgba(0,0,0,0.3)';
                            const colunas = linha.querySelectorAll('td');
                            // Data do depósito
                            const dataDeposito = colunas[3]?.textContent.trim() || '';
                            // Depositante
                            const depositante = colunas[4]?.textContent.trim() || '';
                            // Valor disponível individualizado
                            let valorDisponivelTexto = '';
                            // Busca célula pelo id correto
                            for (const td of colunas) {
                                if (td.id && td.id.startsWith('td_saldo_parcela_saldo_')) {
                                    valorDisponivelTexto = td.textContent.trim();
                                    break;
                                }
                            }
                            // Se não achou pelo id, tenta pela posição padrão (coluna 9 ou 10)
                            if (!valorDisponivelTexto && colunas.length >= 10) {
                                valorDisponivelTexto = colunas[9]?.textContent.trim() || colunas[10]?.textContent.trim() || '';
                            }
                            const valorDeposito = converterValorParaFloat(valorDisponivelTexto);
                            // Só adiciona se valor disponível > 0
                            if (valorDeposito > 0 && dataDeposito && depositante) {
                                depositos.push({
                                    data: dataDeposito,
                                    depositante: depositante,
                                    valor_disponivel: valorDeposito
                                });
                                console.log(`✅ Depósito adicionado: ${dataDeposito} | ${depositante} | ${formatarValorBrasil(valorDeposito)}`);
                            }
        } catch (e) {
            console.error('Erro ao formatar valor:', valor, e);
            return `R$ ${valor.toFixed(2).replace('.', ',')}`;
        }
    }
    
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    function mostrarProgresso(mensagem) {
        console.log(`🔄 ${mensagem}`);
        
        // Atualizar botão com progresso
        const botao = document.getElementById('botaoExtrairSiscon');
        if (botao) {
            botao.innerHTML = `⏳ ${mensagem}`;
            botao.style.background = 'linear-gradient(45deg, #ff9800, #f57c00)';
        }
    }
    
    function restaurarBotao() {
        const botao = document.getElementById('botaoExtrairSiscon');
        if (botao) {
            botao.innerHTML = '📊 Extrair Dados SISCON';
            botao.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
        }
    }
    
    // ===== EXPANDIR CONTA =====
    async function expandirConta(linhaConta, numeroConta) {
        try {
            console.log(`🔽 Expandindo conta: ${numeroConta}`);
            
            // Procura ícone de expansão (subtracao-ico.png) - conta já expandida ou (soma-ico.png) - conta fechada
            let iconeExpansao = linhaConta.querySelector('img[src*="soma-ico.png"]');
            if (!iconeExpansao) {
                // Se não encontrou soma, pode ser que já esteja expandida (subtracao-ico.png)
                iconeExpansao = linhaConta.querySelector('img[src*="subtracao-ico.png"]');
                if (iconeExpansao) {
                    console.log(`✅ Conta ${numeroConta} já está expandida`);
                    return true;
                }
            }
            
            if (iconeExpansao) {
                // Clica no ícone
                iconeExpansao.click();
                console.log(`✅ Ícone de expansão clicado para conta ${numeroConta}`);
                
                // Aguarda um pouco para a expansão acontecer
                await sleep(1500);
                return true;
            } else {
                console.log(`⚠️ Ícone de expansão não encontrado para conta ${numeroConta}`);
                return false;
            }
        } catch (e) {
            console.error(`❌ Erro ao expandir conta ${numeroConta}:`, e);
            return false;
        }
    }
    
    // ===== EXTRAIR DEPÓSITOS =====
    function extrairDepositosExpandidos(indiceConta) {
        try {
            console.log(`📋 Extraindo depósitos da conta índice ${indiceConta}`);
            
            const depositos = [];
            
            // Busca tabela de parcelas específica da conta expandida
            const tabelaParcelas = document.getElementById(`tabela_parcelas_conta_${indiceConta}`);
            if (!tabelaParcelas) {
                console.log(`⚠️ Tabela de parcelas não encontrada para conta ${indiceConta}`);
                return depositos;
            }
            
            console.log(`✅ Tabela de parcelas localizada: tabela_parcelas_conta_${indiceConta}`);
            
            // Busca linhas de depósito (pula o cabeçalho)
            const todasLinhas = tabelaParcelas.querySelectorAll('tr');
            const linhasDeposito = Array.from(todasLinhas).slice(1); // Pula o cabeçalho
            console.log(`📊 Total de linhas na tabela: ${todasLinhas.length}, linhas de depósito: ${linhasDeposito.length}`);
            
            for (let i = 0; i < linhasDeposito.length; i++) {
                const linha = linhasDeposito[i];
                try {
                    const colunas = linha.querySelectorAll('td');
                    console.log(`🔍 Linha ${i + 1}: ${colunas.length} colunas`);
                    
                    if (colunas.length < 10) {
                        console.log(`⚠️ Linha ${i + 1}: Insuficientes colunas (${colunas.length}), pulando`);
                        continue; // Precisa ter todas as colunas esperadas
                    }
                    
                    // Estrutura das colunas baseada no HTML e imagem:
                    // [0,1] = espaços, [2] = nº parcela, [3] = data, [4] = depositante, [5] = cpf/cnpj, 
                    // [6] = valor depositado, [7] = agendado, [8] = bloqueado, [9] = disponível, [10] = ações, [11,12] = espaços
                    
                    const numeroParcelaTexto = colunas[2]?.textContent.trim() || '';
                    const dataDeposito = colunas[3]?.textContent.trim() || '';
                    const depositante = colunas[4]?.textContent.trim() || '';
                    const cpfCnpj = colunas[5]?.textContent.trim() || '';
                    const valorDepositadoTexto = colunas[6]?.textContent.trim() || '';
                    const valorDisponivelTexto = colunas[9]?.textContent.trim() || '';
                    
                    console.log(`📋 Linha ${i + 1}: Parcela=${numeroParcelaTexto}, Data=${dataDeposito}, Depositante=${depositante}`);
                    console.log(`💰 Linha ${i + 1}: Depositado=${valorDepositadoTexto}, Disponível=${valorDisponivelTexto}`);
                    
                    const valorDeposito = converterValorParaFloat(valorDisponivelTexto);
                    console.log(`🔢 Linha ${i + 1}: Valor convertido=${valorDeposito}`);
                    
                    // Registra todos os depósitos, mesmo com valor 0 (para debug)
                    // Mas só adiciona à lista final se valor > 0
                    if (dataDeposito && depositante) {
                        if (valorDeposito > 0) {
                            depositos.push({
                                data: dataDeposito,
                                depositante: depositante,
                                valor_disponivel: valorDeposito
                            });
                            console.log(`✅ Depósito adicionado: ${dataDeposito} | ${depositante} | ${formatarValorBrasil(valorDeposito)}`);
                        } else {
                            console.log(`ℹ️ Depósito sem valor: ${dataDeposito} | ${depositante} | ${formatarValorBrasil(valorDeposito)}`);
                        }
                    } else {
                        console.log(`⚠️ Linha ${i + 1}: Dados incompletos - Data: "${dataDeposito}", Depositante: "${depositante}"`);
                    }
                    
                } catch (e) {
                    console.error(`❌ Erro ao processar linha ${i + 1} de depósito:`, e);
                    continue;
                }
            }
            
            console.log(`📊 Total de depósitos com valor > 0: ${depositos.length}`);
            return depositos;
            
        } catch (e) {
            console.error('❌ Erro ao extrair depósitos:', e);
            return [];
        }
    }
    
    // ===== EXECUÇÃO PRINCIPAL =====
    async function executarExtracao() {
        try {
            console.log('🚀 INICIANDO EXTRAÇÃO SISCON...');
            mostrarProgresso('Iniciando...');
            
            // Verificar se tem dados pesquisados
            const dadosPesquisados = document.getElementById('dados_pesquisados');
            if (!dadosPesquisados) {
                alert('❌ Faça uma busca primeiro!\nPreencha o número do processo e clique em "Buscar".');
                restaurarBotao();
                return;
            }
            
            mostrarProgresso('Localizando tabela...');
            
            // Localizar tabela de contas
            const tabelaContas = document.getElementById('table_contas');
            if (!tabelaContas) {
                alert('❌ Tabela de contas não encontrada!');
                restaurarBotao();
                return;
            }
            
            console.log('✅ Tabela de contas localizada');
            
            // Extrair número do processo
            const campoProcesso = document.getElementById('numeroProcesso');
            const numeroProcesso = campoProcesso ? campoProcesso.value : 'Não informado';
            console.log(`📂 Processo: ${numeroProcesso}`);
            
            mostrarProgresso('Processando contas...');
            
            // Localizar linhas de conta com saldo disponível
            const linhasTodasContas = tabelaContas.querySelectorAll('tr[id^="linhaConta_"]');
            console.log(`📊 Total de contas encontradas: ${linhasTodasContas.length}`);
            
            const dadosExtraidos = {
                numero_processo: numeroProcesso,
                timestamp: new Date().toLocaleString('pt-BR'),
                contas: []
            };
            
            let contasProcessadas = 0;
            
            for (let idx = 0; idx < linhasTodasContas.length; idx++) {
                const linha = linhasTodasContas[idx];
                
                try {
                    console.log(`\n🏦 Processando conta ${idx + 1}/${linhasTodasContas.length}...`);
                    mostrarProgresso(`Conta ${idx + 1}/${linhasTodasContas.length}`);
                    
                    // Extrair número da conta (2ª coluna)
                    const celulaConta = linha.querySelector('td:nth-child(2)');
                    const numeroConta = celulaConta ? celulaConta.textContent.trim() : `Conta_${idx + 1}`;
                    
                    // Extrair valor disponível
                    const celulaDisponivel = linha.querySelector('td[id*="td_saldo_corrigido_conta_"]');
                    if (!celulaDisponivel) {
                        console.log(`⚠️ Célula de valor disponível não encontrada para conta ${numeroConta}`);
                        continue;
                    }
                    
                    const valorDisponivelTexto = celulaDisponivel.textContent.trim();
                    const totalDisponivel = converterValorParaFloat(valorDisponivelTexto);
                    
                    console.log(`💰 Conta: ${numeroConta} | Disponível: ${formatarValorBrasil(totalDisponivel)}`);
                    
                    // Só processa contas com saldo > 0
                    if (totalDisponivel > 0) {
                        console.log(`✅ Conta ${numeroConta} tem saldo, processando...`);
                        
                        const contaDados = {
                            numero_conta: numeroConta,
                            total_disponivel: totalDisponivel,
                            depositos: []
                        };
                        
                        // Expandir para ver os depósitos
                        const expandiuSucesso = await expandirConta(linha, numeroConta);
                        
                        if (expandiuSucesso) {
                            // Aguardar um pouco mais para garantir que a expansão foi processada
                            await sleep(1000);
                            
                            // Extrair depósitos expandidos usando o ID correto da linha
                            const idLinhaConta = linha.id.replace('linhaConta_', ''); // Extrai o ID numérico
                            console.log(`🔍 ID da linha extraído: ${idLinhaConta}`);
                            
                            // Verificar se a tabela de parcelas existe
                            const tabelaParcelasCheck = document.getElementById(`tabela_parcelas_conta_${idLinhaConta}`);
                            if (tabelaParcelasCheck) {
                                console.log(`✅ Tabela de parcelas encontrada: tabela_parcelas_conta_${idLinhaConta}`);
                                contaDados.depositos = extrairDepositosExpandidos(idLinhaConta);
                            } else {
                                console.log(`❌ Tabela de parcelas NÃO encontrada: tabela_parcelas_conta_${idLinhaConta}`);
                                // Tentar listar todas as tabelas de parcelas existentes
                                const todasTabelasParcelas = document.querySelectorAll('table[id*="tabela_parcelas_conta_"]');
                                console.log(`🔍 Tabelas de parcelas existentes:`, Array.from(todasTabelasParcelas).map(t => t.id));
                            }
                        } else {
                            console.log(`⚠️ Não foi possível expandir conta ${numeroConta}`);
                        }
                        
                        dadosExtraidos.contas.push(contaDados);
                        contasProcessadas++;
                        
                        console.log(`✅ Conta ${numeroConta} processada com ${contaDados.depositos.length} depósitos`);
                        
                    } else {
                        console.log(`⏭️ Conta ${numeroConta} sem saldo, ignorando`);
                    }
                    
                } catch (e) {
                    console.error(`❌ Erro ao processar conta ${idx + 1}:`, e);
                    continue;
                }
            }
            
            mostrarProgresso('Formatando dados...');
            
            // ===== FORMATAR E EXIBIR RESULTADOS =====
            console.log('\n='.repeat(60));
            console.log('📊 EXTRAÇÃO SISCON CONCLUÍDA');
            console.log('='.repeat(60));
            console.log(`📂 Processo: ${dadosExtraidos.numero_processo}`);
            console.log(`⏰ Timestamp: ${dadosExtraidos.timestamp}`);
            console.log(`💰 Contas com saldo: ${dadosExtraidos.contas.length}`);
            console.log(`📋 Total processado: ${contasProcessadas}/${linhasTodasContas.length}`);
            
            // Calcular total geral
            let totalGeral = 0;
            for (const conta of dadosExtraidos.contas) {
                totalGeral += conta.total_disponivel;
            }
            console.log(`💸 Total geral disponível: ${formatarValorBrasil(totalGeral)}`);
            
            // Exibir detalhes das contas
            if (dadosExtraidos.contas.length > 0) {
                console.log('\n🏛️ DETALHES DAS CONTAS:');
                console.log('-'.repeat(60));
                
                for (const conta of dadosExtraidos.contas) {
                    console.log(`\n🏦 ${conta.numero_conta}`);
                    console.log(`💰 Total: ${formatarValorBrasil(conta.total_disponivel)}`);
                    
                    if (conta.depositos.length > 0) {
                        console.log('📋 Depósitos:');
                        for (const dep of conta.depositos) {
                            console.log(`  📅 ${dep.data} | 👤 ${dep.depositante} | 💵 ${formatarValorBrasil(dep.valor_disponivel)}`);
                        }
                    } else {
                        console.log('📋 Depósitos: (não expandidos ou sem detalhes)');
                    }
                }
            }
            
            // Formatatar para clipboard com novo formato
            let textoClipboard = `Data da conferência: ${new Date().toLocaleDateString('pt-BR')}\n\n`;
            
            for (const conta of dadosExtraidos.contas) {
                textoClipboard += `Conta judicial: ${conta.numero_conta}\n`;
                textoClipboard += `Total disponível: ${formatarValorBrasil(conta.total_disponivel)}\n`;
                textoClipboard += `Discriminação de depósitos disponíveis\n`;
                textoClipboard += `Data do depósito\tDepositante\tValor disponível\n`;
                
                if (conta.depositos.length > 0) {
                    for (const dep of conta.depositos) {
                        textoClipboard += `${dep.data}\t${dep.depositante}\t${formatarValorBrasil(dep.valor_disponivel)}\n`;
                    }
                } else {
                    // Se não há depósitos expandidos, mostrar apenas o total da conta
                    textoClipboard += `(Total da conta)\t(Valores agrupados)\t${formatarValorBrasil(conta.total_disponivel)}\n`;
                }
                textoClipboard += '\n';
            }
            
            // Tentar copiar para clipboard
            try {
                await navigator.clipboard.writeText(textoClipboard);
                console.log('📋 Dados copiados para o clipboard!');
                
                // Mostrar confirmação no botão
                const botao = document.getElementById('botaoExtrairSiscon');
                if (botao) {
                    botao.innerHTML = '✅ Dados copiados';
                    botao.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
                    
                    // Restaurar botão após 3 segundos
                    setTimeout(() => {
                        botao.innerHTML = '📊 Extrair Dados SISCON';
                    }, 3000);
                }
                
            } catch (e) {
                console.error('❌ Erro ao copiar para clipboard:', e);
                
                // Mostrar erro no botão
                const botao = document.getElementById('botaoExtrairSiscon');
                if (botao) {
                    botao.innerHTML = '❌ Erro na cópia';
                    botao.style.background = 'linear-gradient(45deg, #f44336, #d32f2f)';
                    
                    // Restaurar botão após 3 segundos
                    setTimeout(() => {
                        botao.innerHTML = '📊 Extrair Dados SISCON';
                        botao.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
                    }, 3000);
                }
            }
            
            // Salvar dados em variável global para acesso
            window.dadosSisconExtraidos = dadosExtraidos;
            console.log('\n💾 Dados salvos em: window.dadosSisconExtraidos');
            
        } catch (e) {
            console.error('❌ ERRO GERAL na extração:', e);
            
            // Mostrar erro no botão
            const botao = document.getElementById('botaoExtrairSiscon');
            if (botao) {
                botao.innerHTML = '❌ Erro na extração';
                botao.style.background = 'linear-gradient(45deg, #f44336, #d32f2f)';
                
                // Restaurar botão após 3 segundos
                setTimeout(() => {
                    botao.innerHTML = '📊 Extrair Dados SISCON';
                    botao.style.background = 'linear-gradient(45deg, #4CAF50, #45a049)';
                }, 3000);
            }
        }
    }
    
    // ===== INICIALIZAÇÃO =====
    function inicializar() {
        console.log('🚀 SISCON EXTRACTOR carregado!');
        
        if (verificarURL()) {
            criarBotaoExtrair();
            console.log('✅ Use o botão "Extrair Dados SISCON" no canto superior direito');
            console.log('📋 Ou chame: executarExtracao() no console');
            
            // Disponibilizar função no escopo global
            window.executarExtracaoSiscon = executarExtracao;
            
        } else {
            console.log('❌ Navegue para a página correta primeiro');
        }
    }
    
    // Executar inicialização
    inicializar();
    
})();

console.log('📊 SISCON EXTRACTOR v1.0 - Carregado com sucesso!');
console.log('📍 Funciona apenas na URL: https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar');
console.log('🔘 Após fazer uma busca, clique no botão "Extrair Dados SISCON" ou execute: executarExtracaoSiscon()');
