// ==UserScript==
// @name         SISBAJUD - Extrator de Ordens com Bloqueio Positivo
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Extrai dados de ordens processadas do SISBAJUD com bloqueio positivo, acumulando extrações por executado
// @author       PjePlus
// @match        *://sisbajud.pdpj.jus.br/ordem-judicial/*/detalhar*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';

    // Armazenamento global de dados acumulados
    let ordensAcumuladas = {
        executados: {},
        totalGeral: 0.0,
        ultimaExtracao: null
    };

    // Função para converter valor BRL para float
    function brlToFloat(txt) {
        if (!txt) return 0;
        const n = txt.replace(/R\$/g, '').replace(/\./g, '').replace(',', '.').replace(/\s/g, '').trim();
        const v = parseFloat(n);
        return Number.isFinite(v) ? v : 0;
    }

    // Função para formatar float para BRL
    function toBRL(n) {
        try {
            return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch {
            return `R$ ${(Number(n) || 0).toFixed(2).replace('.', ',')}`;
        }
    }

    // Função para mostrar notificação
    function mostrarNotificacao(mensagem, tipo = 'info') {
        const cores = {
            success: '#4CAF50',
            error: '#f44336',
            info: '#2196F3',
            warning: '#FF9800'
        };

        const notificacao = document.createElement('div');
        notificacao.textContent = mensagem;
        notificacao.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${cores[tipo]};
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            z-index: 99999;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            font-family: Arial, sans-serif;
            max-width: 400px;
            word-wrap: break-word;
        `;

        document.body.appendChild(notificacao);

        setTimeout(() => {
            if (notificacao.parentNode) {
                notificacao.parentNode.removeChild(notificacao);
            }
        }, 4000);
    }

    // Função para extrair dados da ordem atual
    function extrairOrdemAtual() {
        try {
            console.log('[SISBAJUD_EXTRATOR] Iniciando extração da ordem atual...');

            // Verificar se estamos na página correta
            if (!window.location.href.includes('ordem-judicial') || !window.location.href.includes('detalhar')) {
                console.warn('[SISBAJUD_EXTRATOR] Não estamos na página correta de detalhamento de ordem');
                return null;
            }

            // Aguardar um pouco para garantir que a página carregou completamente
            // Isso ajuda a prevenir erros de elementos não encontrados
            setTimeout(() => { }, 1000);

            // Buscar dados da ordem na página
            const dadosOrdem = {
                numeroOrdem: null,
                dataProcessamento: new Date().toLocaleDateString('pt-BR'),
                executados: []
            };

            // 1. Extrair número do protocolo principal
            try {
                const protocoloElement = document.querySelector('div.col-md-3 .sisbajud-label-valor');
                if (protocoloElement && protocoloElement.textContent) {
                    dadosOrdem.numeroOrdem = protocoloElement.textContent.trim();
                    console.log('[SISBAJUD_EXTRATOR] Protocolo principal encontrado:', dadosOrdem.numeroOrdem);
                }
            } catch (e) {
                console.warn('[SISBAJUD_EXTRATOR] Erro ao extrair protocolo:', e);
            }

            // Se não encontrou protocolo, tentar extrair da URL
            if (!dadosOrdem.numeroOrdem) {
                const urlMatch = window.location.href.match(/ordem-judicial\/(\d+)/);
                if (urlMatch) {
                    dadosOrdem.numeroOrdem = urlMatch[1];
                }
            }

            // 2. Buscar todos os cabeçalhos de executados (seguindo exatamente o padrão do sisb.py)
            const headersExecutados = document.querySelectorAll('mat-expansion-panel-header.sisbajud-mat-expansion-panel-header');
            console.log(`[SISBAJUD_EXTRATOR] Encontrados ${headersExecutados.length} executados`);

            if (headersExecutados.length === 0) {
                console.warn('[SISBAJUD_EXTRATOR] Nenhum cabeçalho de executado encontrado. Verifique se a página carregou completamente.');
                return null;
            }

            headersExecutados.forEach((header, idx) => {
                try {
                    if (!header) {
                        console.warn(`[SISBAJUD_EXTRATOR] Cabeçalho ${idx + 1} é null/undefined`);
                        return;
                    }

                    // Extrair nome do executado
                    const nomeElement = header.querySelector('.col-reu-dados-nome-pessoa');
                    const nomeExecutado = nomeElement ? nomeElement.textContent.trim() : '';

                    // Extrair documento do executado
                    const documentoElement = header.querySelector('.col-reu-dados a');
                    const documentoExecutado = documentoElement ? documentoElement.textContent.trim() : 'Documento não identificado';

                    // Extrair valor bloqueado do executado
                    const valorElement = header.querySelector('.div-description-reu span');
                    const valorText = valorElement ? valorElement.textContent.trim() : '';

                    // Processar valor (remover texto e converter para float)
                    // Exemplo: "Valor bloqueado (bloqueio original e reiterações): R$ 244,05"
                    const valorMatch = valorText.match(/R\$\s*([0-9.,]+)/);
                    let valorFloat = 0.0;
                    if (valorMatch) {
                        const valorStr = valorMatch[1];
                        // Converter formato brasileiro para float
                        valorFloat = parseFloat(valorStr.replace(/\./g, '').replace(',', '.'));
                    }

                    if (nomeExecutado && valorFloat > 0) {
                        dadosOrdem.executados.push({
                            nome: nomeExecutado,
                            documento: documentoExecutado,
                            valorBloqueado: valorFloat
                        });

                        console.log(`[SISBAJUD_EXTRATOR] Executado ${idx + 1}: ${nomeExecutado} (${documentoExecutado}) - R$ ${valorFloat.toFixed(2)}`);
                    } else {
                        console.warn(`[SISBAJUD_EXTRATOR] Dados insuficientes para executado ${idx + 1}: nome="${nomeExecutado}", valor=${valorFloat}`);
                    }

                } catch (erro) {
                    console.warn(`[SISBAJUD_EXTRATOR] Erro ao processar executado ${idx + 1}:`, erro);
                }
            });

            if (dadosOrdem.executados.length === 0) {
                console.warn('[SISBAJUD_EXTRATOR] Nenhum executado válido encontrado na página');
                return null;
            }

            console.log(`[SISBAJUD_EXTRATOR] Extração concluída: ${dadosOrdem.executados.length} executados válidos`);
            return dadosOrdem;

        } catch (erro) {
            console.error('[SISBAJUD_EXTRATOR] Erro geral na extração:', erro);
            return null;
        }
    }

    // Função para acumular ordem extraída
    function acumularOrdem() {
        try {
            console.log('[SISBAJUD_EXTRATOR] Iniciando acumulação de ordem...');

            const dadosOrdem = extrairOrdemAtual();

            if (!dadosOrdem) {
                mostrarNotificacao('❌ Erro na extração: verifique se está na página correta e aguarde o carregamento completo', 'error');
                console.error('[SISBAJUD_EXTRATOR] Dados da ordem não foram extraídos');
                return;
            }

            if (!dadosOrdem.executados || dadosOrdem.executados.length === 0) {
                mostrarNotificacao('❌ Nenhum dado de bloqueio encontrado na página atual', 'error');
                console.warn('[SISBAJUD_EXTRATOR] Nenhum executado encontrado nos dados extraídos');
                return;
            }

            console.log(`[SISBAJUD_EXTRATOR] Processando ${dadosOrdem.executados.length} executados...`);

            let novosExecutados = 0;
            let valorTotal = 0;

            dadosOrdem.executados.forEach(executado => {
                try {
                    // Validações de segurança
                    if (!executado || !executado.nome || typeof executado.valorBloqueado !== 'number') {
                        console.warn('[SISBAJUD_EXTRATOR] Executado com dados inválidos:', executado);
                        return;
                    }

                    const chave = `${executado.nome}_${executado.documento || 'sem_documento'}`;

                    if (!ordensAcumuladas.executados[chave]) {
                        ordensAcumuladas.executados[chave] = {
                            nome: executado.nome,
                            documento: executado.documento || 'Documento não identificado',
                            valorTotal: 0,
                            ordens: []
                        };
                        novosExecutados++;
                    }

                    ordensAcumuladas.executados[chave].valorTotal += executado.valorBloqueado;
                    ordensAcumuladas.executados[chave].ordens.push({
                        numeroOrdem: dadosOrdem.numeroOrdem || 'Ordem não identificada',
                        dataProcessamento: dadosOrdem.dataProcessamento,
                        valorBloqueado: executado.valorBloqueado
                    });

                    valorTotal += executado.valorBloqueado;

                } catch (erro) {
                    console.warn('[SISBAJUD_EXTRATOR] Erro ao processar executado individual:', erro, executado);
                }
            });

            ordensAcumuladas.totalGeral += valorTotal;
            ordensAcumuladas.ultimaExtracao = new Date().toLocaleString('pt-BR');

            const totalExecutados = Object.keys(ordensAcumuladas.executados).length;
            mostrarNotificacao(`✅ Ordem adicionada! Total: ${totalExecutados} executados - ${toBRL(ordensAcumuladas.totalGeral)}`, 'success');

            console.log('[SISBAJUD_EXTRATOR] Ordem acumulada com sucesso:', {
                novosExecutados,
                valorTotal,
                totalGeral: ordensAcumuladas.totalGeral,
                totalExecutados
            });

        } catch (erro) {
            console.error('[SISBAJUD_EXTRATOR] Erro geral na acumulação:', erro);
            mostrarNotificacao('❌ Erro interno ao acumular ordem', 'error');
        }
    }

    // Função para gerar relatório final
    function gerarRelatorioFinal() {
        if (Object.keys(ordensAcumuladas.executados).length === 0) {
            mostrarNotificacao('❌ Nenhum dado acumulado para gerar relatório', 'error');
            return;
        }

        // Estrutura HTML seguindo o padrão do sisb.py
        const pStyle = 'font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;';
        let relatorioHTML = '';

        // Percorrer cada executado
        Object.values(ordensAcumuladas.executados).forEach(executado => {
            const nome = executado.nome;
            const documento = executado.documento;
            const ordens = executado.ordens;
            const totalExecutado = executado.valorTotal;

            // Cabeçalho do executado
            relatorioHTML += `<p class="corpo" style="${pStyle}"><strong>Executado: ${nome} - ${documento}</strong></p>`;

            // Listar protocolos do executado
            ordens.forEach(ordem => {
                const numeroProtocolo = ordem.numeroOrdem;
                const valorFormatado = toBRL(ordem.valorBloqueado);
                relatorioHTML += `<p class="corpo" style="${pStyle}">Protocolo ${numeroProtocolo} - Valor: ${valorFormatado}</p>`;
            });

            // Total do executado
            const totalFormatado = toBRL(totalExecutado);
            relatorioHTML += `<p class="corpo" style="${pStyle}"><strong>Total do executado: ${totalFormatado}</strong></p>`;
            relatorioHTML += '<br>'; // Espaço entre executados
        });

        // Total geral do processo
        const totalGeralFormatado = toBRL(ordensAcumuladas.totalGeral);
        relatorioHTML += `<p class="corpo" style="${pStyle}"><strong>TOTAL BLOQUEADO NO PROCESSO: ${totalGeralFormatado}</strong></p>`;

        // Criar container temporário para converter HTML em conteúdo visual
        const containerTemp = document.createElement('div');
        containerTemp.innerHTML = relatorioHTML;
        containerTemp.style.cssText = 'position: absolute; left: -9999px; top: -9999px;';
        document.body.appendChild(containerTemp);

        // Selecionar todo o conteúdo HTML renderizado
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(containerTemp);
        selection.removeAllRanges();
        selection.addRange(range);

        // Copiar o conteúdo formatado
        try {
            const success = document.execCommand('copy');
            if (success) {
                mostrarNotificacao('✅ Relatório HTML formatado copiado!', 'success');
            } else {
                throw new Error('execCommand falhou');
            }
        } catch (error) {
            // Fallback: copiar como texto HTML
            navigator.clipboard.writeText(relatorioHTML).then(() => {
                mostrarNotificacao('✅ Relatório HTML copiado como código!', 'warning');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = relatorioHTML;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                mostrarNotificacao('✅ Relatório copiado!', 'success');
            });
        } finally {
            // Limpar seleção e remover container temporário
            selection.removeAllRanges();
            document.body.removeChild(containerTemp);
        }

        console.log('[SISBAJUD_EXTRATOR] Relatório HTML gerado:', relatorioHTML);
    }

    // Função para limpar dados acumulados
    function limparDados() {
        ordensAcumuladas = {
            executados: {},
            totalGeral: 0.0,
            ultimaExtracao: null
        };
        mostrarNotificacao('🔄 Dados limpos - nova sessão iniciada', 'info');
    }

    // Criar interface dos botões
    function criarInterface() {
        // Verificar se a interface já existe
        if (document.getElementById('sisbajud-extrator-interface')) {
            return;
        }

        const container = document.createElement('div');
        container.id = 'sisbajud-extrator-interface';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 99999;
            font-family: Arial, sans-serif;
        `;

        // Botão 1: Extrair Ordem
        const btnExtrair = document.createElement('button');
        btnExtrair.textContent = '📊 Extrair Ordem';
        btnExtrair.style.cssText = `
            display: block;
            margin-bottom: 10px;
            padding: 12px 20px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: background 0.3s;
        `;
        btnExtrair.onmouseover = () => btnExtrair.style.background = '#1976D2';
        btnExtrair.onmouseout = () => btnExtrair.style.background = '#2196F3';
        btnExtrair.onclick = acumularOrdem;

        // Botão 2: Finalizar e Gerar Relatório
        const btnFinalizar = document.createElement('button');
        btnFinalizar.textContent = '📄 Gerar Relatório';
        btnFinalizar.style.cssText = `
            display: block;
            margin-bottom: 10px;
            padding: 12px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: background 0.3s;
        `;
        btnFinalizar.onmouseover = () => btnFinalizar.style.background = '#388E3C';
        btnFinalizar.onmouseout = () => btnFinalizar.style.background = '#4CAF50';
        btnFinalizar.onclick = gerarRelatorioFinal;

        // Botão 3: Limpar Dados
        const btnLimpar = document.createElement('button');
        btnLimpar.textContent = '🔄 Limpar';
        btnLimpar.style.cssText = `
            display: block;
            padding: 8px 16px;
            background: #FF9800;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: background 0.3s;
        `;
        btnLimpar.onmouseover = () => btnLimpar.style.background = '#F57C00';
        btnLimpar.onmouseout = () => btnLimpar.style.background = '#FF9800';
        btnLimpar.onclick = limparDados;

        // Contador de dados acumulados
        const contador = document.createElement('div');
        contador.id = 'contador-dados';
        contador.style.cssText = `
            margin-top: 10px;
            padding: 8px 12px;
            background: rgba(0,0,0,0.8);
            color: white;
            border-radius: 4px;
            font-size: 12px;
            text-align: center;
        `;
        contador.textContent = 'Nenhum dado acumulado';

        container.appendChild(btnExtrair);
        container.appendChild(btnFinalizar);
        container.appendChild(btnLimpar);
        container.appendChild(contador);

        document.body.appendChild(container);

        // Atualizar contador periodicamente
        setInterval(() => {
            const totalExecutados = Object.keys(ordensAcumuladas.executados).length;
            const contadorEl = document.getElementById('contador-dados');
            if (contadorEl) {
                if (totalExecutados > 0) {
                    contadorEl.textContent = `${totalExecutados} executados\n${toBRL(ordensAcumuladas.totalGeral)}`;
                } else {
                    contadorEl.textContent = 'Nenhum dado acumulado';
                }
            }
        }, 1000);
    }

    // Inicializar quando a página carregar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', criarInterface);
    } else {
        criarInterface();
    }

    // Recriar interface se necessário após mudanças de página
    let ultimaUrl = location.href;
    new MutationObserver(() => {
        if (location.href !== ultimaUrl) {
            ultimaUrl = location.href;
            setTimeout(criarInterface, 1000);
        }
    }).observe(document, { subtree: true, childList: true });

})();
