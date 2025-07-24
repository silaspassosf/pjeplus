// ==UserScript==
// @name         Lista Exec
// @namespace    http://tampermonkey.net/
// @version      1.4
// @description  Lista medidas executórias realizadas nos autos do PJe - APRIMORADO: Clique automático nos anexos + seleção inteligente
// @author       PjePlus
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('[LISTA-EXEC] Script iniciado - v1.4');
    
    /*
     * MELHORIAS IMPLEMENTADAS:
     * 1. INFOJUD, IRPF e DOI só são logados quando encontrados como ANEXOS (não como documento principal)
     * 2. Campo "id" padronizado: "doc-${index}" para documentos principais, "anexos-${index}" para anexos
     * 3. Busca automática em anexos de "Certidão de oficial" e "Pesquisa patrimonial"
     * 4. Clique automático no botão de anexos para verificar conteúdo
     * 5. Identificação específica de documentos alvo (INFOJUD, IRPF, DOI, etc.) dentro dos anexos
     * 6. Processamento assíncrono para aguardar carregamento dos anexos
     * 7. Clique inteligente em anexos - expande automaticamente e destaca documento específico
     * 8. Indicadores visuais na tabela para distinguir anexos (📎) de documentos principais
     * 9. Destaque diferenciado para anexos (laranja) vs documentos principais (verde)
     * 10. NOVA FUNCIONALIDADE: Clique automático nos links dos anexos para abrir/selecionar documento
     * 11. Tratamento especial para diferentes tipos de anexos (específicos vs grupos)
     * 12. Feedback visual diferenciado para sucesso/erro no clique dos anexos
     */
    
    // Criar botão de ativação
    function criarBotaoPesquisas() {
        console.log('[LISTA-EXEC] Criando botão...');
        
        // Verificar se o botão já existe
        const botaoExistente = document.getElementById('btnListaExec');
        if (botaoExistente) {
            botaoExistente.remove();
        }
        
        try {
            const botao = document.createElement('button');
            botao.id = 'btnListaExec';
            botao.textContent = '🔍 Pesquisas';
            
            botao.style.cssText = `
                position: fixed !important;
                bottom: 140px !important;
                right: 20px !important;
                z-index: 99999 !important;
                background-color: #28a745 !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 12px 16px !important;
                font-size: 14px !important;
                font-weight: bold !important;
                cursor: pointer !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
                transition: all 0.3s ease !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            `;
            
            // Efeitos hover
            botao.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#218838 !important';
                this.style.transform = 'scale(1.05) translateY(-2px)';
                this.style.boxShadow = '0 6px 20px rgba(0,0,0,0.4) !important';
            });
            
            botao.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '#28a745 !important';
                this.style.transform = 'scale(1) translateY(0)';
                this.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3) !important';
            });
            
            // Evento de clique
            botao.addEventListener('click', function() {
                console.log('[LISTA-EXEC] Botão clicado');
                executarPesquisaTimeline();
            });
            
            document.body.appendChild(botao);
            console.log('[LISTA-EXEC] ✅ Botão criado com sucesso');
            return true;
            
        } catch (error) {
            console.error('[LISTA-EXEC] Erro ao criar botão:', error);
            return false;
        }
    }
    
    // Função para extrair data do item da timeline
    function extrairDataItem(item) {
        try {
            console.log('[LISTA-EXEC] Extraindo data do item:', item);
            
            // Estratégia 1: Buscar o elemento .tl-data que está ACIMA do documento atual
            // O HTML mostra: <div class="tl-data">01 mar. 2019</div>
            let dataElement = null;
            
            // Primeiro, tenta buscar .tl-data dentro do próprio item
            dataElement = item.querySelector('.tl-data[name="dataItemTimeline"]');
            if (!dataElement) {
                dataElement = item.querySelector('.tl-data');
            }
            
            // Se não encontrou dentro do item, busca no elemento anterior (irmão anterior)
            if (!dataElement) {
                let elementoAnterior = item.previousElementSibling;
                while (elementoAnterior) {
                    dataElement = elementoAnterior.querySelector('.tl-data[name="dataItemTimeline"]');
                    if (!dataElement) {
                        dataElement = elementoAnterior.querySelector('.tl-data');
                    }
                    if (dataElement) break;
                    elementoAnterior = elementoAnterior.previousElementSibling;
                }
            }
            
            // Se encontrou o elemento de data, processa o texto
            if (dataElement) {
                const dataTexto = dataElement.textContent.trim();
                console.log('[LISTA-EXEC] Elemento .tl-data encontrado, texto:', dataTexto);
                
                // Converte formato "01 mar. 2019" para "01/03/2019"
                const dataConvertida = converterDataTextoParaNumerico(dataTexto);
                if (dataConvertida) {
                    console.log('[LISTA-EXEC] Data convertida:', dataConvertida);
                    return dataConvertida;
                }
                
                // Fallback: tentar regex direta para formato dd/mm/yyyy
                const matchData = dataTexto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
                if (matchData) {
                    console.log('[LISTA-EXEC] Data encontrada via regex:', matchData[1]);
                    return matchData[1];
                }
            }
            
            // Estratégia 2: Fallback - buscar qualquer texto que contenha data no item inteiro
            const textoCompleto = item.textContent;
            console.log('[LISTA-EXEC] Fallback - texto completo do item:', textoCompleto.substring(0, 200) + '...');
            
            const matchDataFallback = textoCompleto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
            if (matchDataFallback) {
                console.log('[LISTA-EXEC] Data encontrada no fallback:', matchDataFallback[1]);
                return matchDataFallback[1];
            }
            
            console.log('[LISTA-EXEC] Nenhuma data encontrada no item');
            return 'Data não encontrada';
        } catch (e) {
            console.error('[LISTA-EXEC] Erro ao extrair data:', e);
            return 'Erro na data';
        }
    }
    
    // Função auxiliar para converter texto de data (ex: "01 mar. 2019") para formato numérico (ex: "01/03/2019")
    function converterDataTextoParaNumerico(dataTexto) {
        try {
            // Mapeamento de meses em português
            const meses = {
                'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
            };
            
            // Regex para capturar formato "01 mar. 2019" ou "1 mar 2019"
            const match = dataTexto.match(/(\d{1,2})\s+(\w{3})\.?\s+(\d{4})/);
            if (match) {
                const dia = match[1].padStart(2, '0');
                const mesTexto = match[2].toLowerCase();
                const ano = match[3];
                
                const mesNumero = meses[mesTexto];
                if (mesNumero) {
                    const dataFormatada = `${dia}/${mesNumero}/${ano}`;
                    console.log('[LISTA-EXEC] Data convertida de texto para numérico:', dataTexto, '->', dataFormatada);
                    return dataFormatada;
                }
            }
            
            console.log('[LISTA-EXEC] Não foi possível converter a data:', dataTexto);
            return null;
        } catch (e) {
            console.error('[LISTA-EXEC] Erro ao converter data:', e);
            return null;
        }
    }
    
    // Função para converter data para objeto Date para ordenação
    function converterData(dataStr) {
        if (dataStr === 'Data não encontrada' || dataStr === 'Erro na data') {
            return new Date(0); // Data muito antiga para ordenação
        }
        
        try {
            const [dia, mes, ano] = dataStr.split('/');
            return new Date(parseInt(ano), parseInt(mes) - 1, parseInt(dia));
        } catch (e) {
            return new Date(0);
        }
    }
    
    // Função para verificar se a data é até maio de 2024
    function isDataAteMaximo(dataStr) {
        const data = converterData(dataStr);
        const dataMaxima = new Date(2024, 4, 31); // Maio de 2024 (mês 4 = maio)
        return data <= dataMaxima;
    }
    
    // Função para extrair UID real do documento a partir do nome completo
    function extrairUidDocumento(link) {
        try {
            const nomeCompleto = link.textContent.trim();
            // Buscar padrão " - [códigoUID]" no final do nome
            // Exemplo: "Certidão(resposta serasajud APJUR 3691652018) - cd7753f"
            const match = nomeCompleto.match(/\s-\s([a-zA-Z0-9]+)$/);
            if (match && match[1]) {
                console.log(`[LISTA-EXEC] UID extraído: ${match[1]} do nome: ${nomeCompleto}`);
                return match[1];
            }
            
            // Fallback: buscar qualquer código alfanumérico no final (sem o " - ")
            const fallbackMatch = nomeCompleto.match(/([a-zA-Z0-9]{6,})$/);
            if (fallbackMatch && fallbackMatch[1]) {
                console.log(`[LISTA-EXEC] UID extraído (fallback): ${fallbackMatch[1]} do nome: ${nomeCompleto}`);
                return fallbackMatch[1];
            }
            
            console.log(`[LISTA-EXEC] Nenhum UID encontrado no nome: ${nomeCompleto}`);
            return null;
        } catch (e) {
            console.error('[LISTA-EXEC] Erro ao extrair UID:', e);
            return null;
        }
    }
    
    // Função para verificar anexos em documentos específicos
    async function verificarAnexosDocumento(item, nomeDocumento, data, index) {
        console.log(`[LISTA-EXEC] Verificando anexos para: ${nomeDocumento}`);
        
        const anexosEncontrados = [];
        
        // Buscar o botão de anexos usando múltiplos seletores
        let btnAnexos = item.querySelector('pje-timeline-anexos div[name="mostrarOuOcultarAnexos"]');
        
        if (!btnAnexos) {
            // Seletor alternativo baseado no HTML fornecido
            btnAnexos = item.querySelector('pje-timeline-anexos div[role="button"]');
        }
        
        if (!btnAnexos) {
            // Seletor genérico
            btnAnexos = item.querySelector('pje-timeline-anexos .header-documento');
        }
        
        if (!btnAnexos) {
            console.log('[LISTA-EXEC] Botão de anexos não encontrado');
            return anexosEncontrados;
        }
        
        // Verificar se os anexos já estão visíveis
        const anexosContainer = item.querySelector('pje-timeline-anexos');
        let anexosJaVisiveis = false;
        
        if (anexosContainer) {
            // Verificar se há conteúdo de anexos visível
            const anexosVisiveis = anexosContainer.querySelectorAll('a.tl-documento');
            anexosJaVisiveis = anexosVisiveis.length > 0;
        }
        
        if (!anexosJaVisiveis) {
            console.log('[LISTA-EXEC] Clicando no botão de anexos...');
            
            // Clicar no botão de anexos
            try {
                btnAnexos.click();
                console.log('[LISTA-EXEC] Clique executado com sucesso');
            } catch (e) {
                console.error('[LISTA-EXEC] Erro ao clicar no botão de anexos:', e);
                return anexosEncontrados;
            }
            
            // Aguardar um pouco para os anexos carregarem
            await new Promise(resolve => setTimeout(resolve, 1500));
        }
        
        // Buscar pelos anexos após expandir
        const anexosLinks = item.querySelectorAll('pje-timeline-anexos a.tl-documento');
        console.log(`[LISTA-EXEC] Encontrados ${anexosLinks.length} anexos`);
        
        // Itens a serem buscados nos anexos
        const itensAnexo = [
            { nome: 'SISBAJUD', termos: ['sisbajud'] },
            { nome: 'Serasa', termos: ['serasa'] },
            { nome: 'CNIB', termos: ['cnib'] },
        ];
        
        anexosLinks.forEach((anexoLink, anexoIndex) => {
            const textoAnexo = anexoLink.textContent.trim().toLowerCase();
            
            for (const itemAnexo of itensAnexo) {
                const encontrado = itemAnexo.termos.some(termo => textoAnexo.includes(termo));
                if (encontrado) {
                    const uid = extrairUidDocumento(anexoLink);
                    const anexoId = uid ? `anexo-${uid}` : `anexo-${index}-${anexoIndex}`;
                    
                    anexosEncontrados.push({
                        nome: itemAnexo.nome,
                        texto: `${itemAnexo.nome} (anexo de ${nomeDocumento})`,
                        data: data,
                        dataObj: converterData(data),
                        id: anexoId,
                        elemento: item,
                        link: anexoLink,
                        index: index,
                        tipoItem: 'anexo',
                        documentoPai: nomeDocumento
                    });
                    
                    registrarDataTimeline(data, 'anexo', itemAnexo.nome, anexoId);
                    console.log(`[LISTA-EXEC] ✅ ${itemAnexo.nome} encontrado em anexo: ${anexoLink.textContent.trim()} (${data})`);
                    break;
                }
            }
        });
        
        return anexosEncontrados;
    }

    // Função para ler a timeline e encontrar medidas executórias
    async function lerMedidasExecutorias() {
        console.log('[LISTA-EXEC] Lendo timeline...');
        
        const seletoresTimeline = [
            'li.tl-item-container',
            '.tl-data .tl-item-container',
            '.timeline-item'
        ];
        
        let itens = [];
        let seletorUsado = '';
        for (const seletor of seletoresTimeline) {
            itens = document.querySelectorAll(seletor);
            if (itens.length > 0) {
                seletorUsado = seletor;
                console.log(`[LISTA-EXEC] Encontrados ${itens.length} itens com: ${seletor}`);
                console.log('[LISTA-EXEC] Primeiro item para debug:', itens[0]);
                console.log('[LISTA-EXEC] HTML do primeiro item:', itens[0].outerHTML.substring(0, 500) + '...');
                break;
            }
        }
        
        if (itens.length === 0) {
            console.log('[LISTA-EXEC] Nenhum item encontrado na timeline');
            return [];
        }
        
        const medidas = [];
        
        // Itens a serem filtrados
        const itensAlvo = [
            { nome: 'Certidão de pesquisa patrimonial', termos: ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial'] },
            { nome: 'SISBAJUD', termos: ['sisbajud'] },
            { nome: 'INFOJUD', termos: ['infojud'] },
            { nome: 'IRPF', termos: ['irpf', 'imposto de renda'] },
            { nome: 'DOI', termos: ['doi'] },
            { nome: 'Mandado de livre penhora', termos: ['mandado de livre penhora', 'mandado de penhora', 'livre penhora'] },
            { nome: 'Serasa', termos: ['serasa'] },
            { nome: 'CNIB', termos: ['cnib'] },
            { nome: 'CAGED', termos: ['caged'] },
            { nome: 'PREVJUD', termos: ['prevjud'] },
            { nome: 'SNIPER', termos: ['sniper'] },
            { nome: 'CCS', termos: ['ccs'] },
            { nome: 'CENSEC', termos: ['censec'] }
        ];
        
        
        // Processar itens da timeline
        for (let index = 0; index < itens.length; index++) {
            const item = itens[index];
            try {
                // Verificar documento principal
                const link = item.querySelector('a.tl-documento:not([target="_blank"])');
                
                if (link) {
                    const textoDoc = link.textContent.trim().toLowerCase();
                    const data = extrairDataItem(item);
                    
                    // Definir itens que só devem ser logados como anexos
                    const itensSomenteAnexos = ['INFOJUD', 'IRPF', 'DOI'];
                    
                    for (const itemAlvo of itensAlvo) {
                        const encontrado = itemAlvo.termos.some(termo => textoDoc.includes(termo));
                        if (encontrado) {
                            // Verificar se é um item que só deve ser logado como anexo
                            if (itensSomenteAnexos.includes(itemAlvo.nome)) {
                                console.log(`[LISTA-EXEC] ⚠️ ${itemAlvo.nome} encontrado como documento principal - não será logado (deve ser apenas anexo)`);
                                break; // Pular este item
                            }
                            
                            const uid = extrairUidDocumento(link);
                            const documentoId = uid || `doc-${index}`;
                            
                            medidas.push({
                                nome: itemAlvo.nome,
                                texto: link.textContent.trim(),
                                data: data,
                                dataObj: converterData(data),
                                id: documentoId,
                                elemento: item,
                                link: link,
                                index: index,
                                tipoItem: 'documento'
                            });
                            // Loga a data, seletor, nome e id
                            registrarDataTimeline(data, seletorUsado, itemAlvo.nome, documentoId);
                            console.log(`[LISTA-EXEC] ✅ ${itemAlvo.nome}: ${link.textContent.trim()} (${data})`);
                            break; // Sair do loop após encontrar a primeira correspondência
                        }
                    }
                    
                    // Verificar se é Certidão de oficial ou Pesquisa patrimonial para buscar anexos
                    const isCertidaoOficial = textoDoc.includes('certidão de oficial') || textoDoc.includes('certidao de oficial');
                    const isPesquisaPatrimonial = textoDoc.includes('pesquisa patrimonial');
                    
                    if (isCertidaoOficial || isPesquisaPatrimonial) {
                        const tipoDocumento = isCertidaoOficial ? 'Certidão de oficial' : 'Pesquisa patrimonial';
                        console.log(`[LISTA-EXEC] Verificando anexos para ${tipoDocumento}...`);
                        
                        // Verificar anexos específicos para este tipo de documento
                        const anexosEncontrados = await verificarAnexosDocumento(item, tipoDocumento, data, index);
                        
                        // Adicionar os anexos encontrados às medidas
                        medidas.push(...anexosEncontrados);
                    }
                }
                
                // Verificar anexos gerais para Pesquisa Patrimonial (lógica original mantida)
                const btnAnexos = item.querySelector('pje-timeline-anexos > div > div');
                if (btnAnexos && link) {
                    const textoDoc = link.textContent.trim().toLowerCase();
                    const data = extrairDataItem(item);
                    
                    // Verificar se é Certidão de pesquisa patrimonial (lógica original mantida)
                    if (textoDoc.includes('pesquisa patrimonial')) {
                        const uid = extrairUidDocumento(link);
                        const anexoId = uid ? `anexos-${uid}` : `anexos-${index}`;
                        
                        medidas.push({
                            nome: 'Anexos da Pesquisa Patrimonial',
                            texto: `Anexos: ${link.textContent.trim()}`,
                            data: data,
                            dataObj: converterData(data),
                            id: anexoId,
                            elemento: item,
                            link: btnAnexos,
                            index: index,
                            tipoItem: 'anexos',
                            documentoPai: link.textContent.trim()
                        });
                        // Loga a data, seletor, nome e id para anexos
                        registrarDataTimeline(data, seletorUsado, 'Anexos da Pesquisa Patrimonial', anexoId);
                        console.log(`[LISTA-EXEC] ✅ Anexos de Pesquisa Patrimonial: ${data}`);
                    }
                }
                
            } catch (e) {
                console.error(`[LISTA-EXEC] Erro ao processar item ${index}:`, e);
            }
        }
        
        // Ordenar do mais recente para o mais antigo
        medidas.sort((a, b) => b.dataObj - a.dataObj);
        
        console.log(`[LISTA-EXEC] Total de medidas encontradas: ${medidas.length}`);
        return medidas;
    }
    
    // Função para gerar tabela de medidas
    function gerarTabelaMedidas(medidas) {
        // Filtrar apenas medidas até maio de 2024
        const medidasFiltradas = medidas.filter(medida => isDataAteMaximo(medida.data));
        
        // Remover tabela anterior
        const tabelaExistente = document.getElementById('tabelaListaExec');
        if (tabelaExistente) {
            tabelaExistente.remove();
        }
        const container = document.createElement('div');
        container.id = 'tabelaListaExec';
        // Calcular posição relativa ao botão de pesquisas
        const btnPesquisas = document.getElementById('btnListaExec') || 
                              Array.from(document.querySelectorAll('button')).find(btn => btn.textContent.includes('🔍'));
        
        let topPosition = '15%';
        let leftPosition = '26%';
        
        if (btnPesquisas) {
            const rect = btnPesquisas.getBoundingClientRect();
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const buttonTop = rect.top + scrollTop;
            
            // Posicionar a caixa acima do botão com margem de segurança
            const dialogHeight = window.innerHeight * 0.48; // 48% da altura da tela
            const calculatedTop = (buttonTop - dialogHeight - 20) / window.innerHeight * 100;
            
            // Garantir que a caixa fique visível (mínimo 5%, máximo 40%)
            topPosition = Math.max(5, Math.min(40, calculatedTop)) + '%';
        }
        
        container.style.cssText = `
            position: fixed;
            top: ${topPosition};
            left: ${leftPosition};
            width: 48%;
            height: 48%;
            z-index: 100000;
            background: white;
            border: 2px solid #28a745;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            overflow-y: auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        // Cabeçalho
        const cabecalho = document.createElement('div');
        cabecalho.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #28a745;
            padding-bottom: 15px;
        `;
        
        const titulo = document.createElement('h3');
        titulo.innerHTML = '🔍 Medidas Executórias Encontradas';
        titulo.style.cssText = 'margin: 0; color: #28a745; font-size: 18px;';
        
        const btnFechar = document.createElement('button');
        btnFechar.innerHTML = '✕';
        btnFechar.style.cssText = `
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s ease;
        `;
        btnFechar.addEventListener('click', () => container.remove());
        
        cabecalho.appendChild(titulo);
        cabecalho.appendChild(btnFechar);
        container.appendChild(cabecalho);
        
        if (medidasFiltradas.length === 0) {
            const mensagem = document.createElement('div');
            mensagem.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                    <h4 style="margin: 0 0 8px 0; color: #333;">Não há pesquisas com menos de um ano</h4>
                    <p style="margin: 0; font-style: italic;">Não foram encontradas medidas executórias até maio de 2024.</p>
                </div>
            `;
            container.appendChild(mensagem);
        } else {
            // Botão Gerar Relatório
            const btnRelatorio = document.createElement('button');
            btnRelatorio.innerHTML = '📋 Gerar Relatório';
            btnRelatorio.style.cssText = `
                background: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                margin-bottom: 20px;
                transition: all 0.2s ease;
            `;
            
            btnRelatorio.addEventListener('click', () => gerarRelatorioTexto(medidasFiltradas));
            btnRelatorio.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#0056b3';
            });
            btnRelatorio.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '#007bff';
            });
            
            container.appendChild(btnRelatorio);
            
            // Lista simples numerada
            const lista = document.createElement('div');
            lista.style.cssText = `
                font-size: 14px;
                line-height: 1.2;
                display: flex;
                flex-direction: column;
                align-items: flex-start;
                width: fit-content;
                max-width: 100%;
            `;
            
            medidasFiltradas.forEach((medida, index) => {
                const item = document.createElement('div');
                item.style.cssText = `
                    padding: 4px 8px;
                    margin: 1px 0;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    background-color: ${index % 2 === 0 ? '#f8f9fa' : 'white'};
                    white-space: nowrap;
                    display: inline-block;
                    width: fit-content;
                    min-width: 0;
                `;
                
                item.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#e7f3ff';
                    this.style.transform = 'translateX(5px)';
                });
                item.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = index % 2 === 0 ? '#f8f9fa' : 'white';
                    this.style.transform = 'translateX(0)';
                });
                
                // Evento de clique no item
                item.addEventListener('click', async function() {
                    await selecionarMedidaTimeline(medida, this);
                });
                
                // Formatação do texto com indicador visual para anexos
                let textoItem = `${index + 1} - ${medida.nome}, ${medida.id}, ${medida.data}`;
                
                // Adicionar indicador visual para anexos
                if (medida.tipoItem === 'anexo') {
                    textoItem = `📎 ${textoItem}`;
                    item.style.cssText += `
                        border-left: 4px solid #f39c12 !important;
                        padding-left: 12px !important;
                        font-style: italic !important;
                    `;
                } else if (medida.tipoItem === 'anexos') {
                    textoItem = `📎 ${textoItem}`;
                    item.style.cssText += `
                        border-left: 4px solid #17a2b8 !important;
                        padding-left: 12px !important;
                    `;
                }
                
                item.textContent = textoItem;
                lista.appendChild(item);
            });
            
            container.appendChild(lista);
        }
        
        document.body.appendChild(container);
        console.log('[LISTA-EXEC] Tabela exibida');
    }
    
    // Função para selecionar medida na timeline
    async function selecionarMedidaTimeline(medida, elemento) {
        try {
            console.log(`[LISTA-EXEC] Selecionando: ${medida.nome} (Tipo: ${medida.tipoItem})`);
            
            // Feedback visual na linha
            const corOriginal = elemento.style.backgroundColor;
            elemento.style.backgroundColor = '#ffc107';
            elemento.style.color = '#000';
            
            // Rolar até o elemento
            medida.elemento.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            
            // Se for um anexo, primeiro expandir os anexos
            if (medida.tipoItem === 'anexo') {
                console.log('[LISTA-EXEC] Item é um anexo, expandindo anexos...');
                
                // Buscar o botão de anexos usando múltiplos seletores
                let btnAnexos = medida.elemento.querySelector('pje-timeline-anexos div[name="mostrarOuOcultarAnexos"]');
                
                if (!btnAnexos) {
                    btnAnexos = medida.elemento.querySelector('pje-timeline-anexos div[role="button"]');
                }
                
                if (!btnAnexos) {
                    btnAnexos = medida.elemento.querySelector('pje-timeline-anexos .header-documento');
                }
                
                if (btnAnexos) {
                    // Verificar se os anexos já estão visíveis
                    const anexosVisiveis = medida.elemento.querySelectorAll('pje-timeline-anexos a.tl-documento');
                    
                    if (anexosVisiveis.length === 0) {
                        console.log('[LISTA-EXEC] Clicando no botão de anexos para expandir...');
                        
                        // Destacar o botão de anexos temporariamente
                        const estiloOriginalBtn = btnAnexos.style.cssText;
                        btnAnexos.style.cssText += `
                            background: #ffc107 !important;
                            border: 2px solid #e0a800 !important;
                            border-radius: 4px !important;
                            transition: all 0.3s ease !important;
                        `;
                        
                        // Clicar no botão
                        btnAnexos.click();
                        
                        // Aguardar expansão dos anexos
                        await new Promise(resolve => setTimeout(resolve, 1500));
                        
                        // Restaurar estilo do botão
                        btnAnexos.style.cssText = estiloOriginalBtn;
                    }
                    
                    // Aguardar um pouco mais para garantir que os anexos carregaram
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // Destacar o anexo específico
                    if (medida.link) {
                        console.log('[LISTA-EXEC] Destacando anexo específico...');
                        
                        const estiloOriginalAnexo = medida.link.style.cssText;
                        medida.link.style.cssText += `
                            background: linear-gradient(45deg, #fff3cd, #ffeaa7) !important;
                            border: 3px solid #f39c12 !important;
                            border-radius: 6px !important;
                            transform: scale(1.05) !important;
                            transition: all 0.3s ease !important;
                            box-shadow: 0 4px 15px rgba(243,156,18,0.4) !important;
                            color: #d68910 !important;
                            font-weight: bold !important;
                        `;
                        
                        // Piscar destaque no anexo
                        let piscarAnexo = 0;
                        const intervaloAnexo = setInterval(() => {
                            medida.link.style.opacity = piscarAnexo % 2 === 0 ? '0.7' : '1';
                            piscarAnexo++;
                            if (piscarAnexo > 8) {
                                clearInterval(intervaloAnexo);
                                medida.link.style.opacity = '1';
                            }
                        }, 250);
                        
                        // Aguardar um pouco e depois clicar no link do anexo
                        setTimeout(() => {
                            console.log('[LISTA-EXEC] Clicando no link do anexo para abrir/selecionar...');
                            try {
                                // Simular clique no link do anexo
                                medida.link.click();
                                console.log('[LISTA-EXEC] ✅ Clique no anexo executado com sucesso');
                                
                                // Feedback visual adicional após o clique
                                setTimeout(() => {
                                    medida.link.style.cssText += `
                                        background: linear-gradient(45deg, #d4edda, #c3e6cb) !important;
                                        border: 3px solid #28a745 !important;
                                        color: #155724 !important;
                                    `;
                                }, 500);
                                
                            } catch (clickError) {
                                console.error('[LISTA-EXEC] Erro ao clicar no anexo:', clickError);
                                
                                // Feedback visual de erro
                                medida.link.style.cssText += `
                                    background: linear-gradient(45deg, #f8d7da, #f5c6cb) !important;
                                    border: 3px solid #dc3545 !important;
                                    color: #721c24 !important;
                                `;
                            }
                        }, 1000);
                        
                        // Remover destaque do anexo após 6 segundos
                        setTimeout(() => {
                            medida.link.style.cssText = estiloOriginalAnexo;
                        }, 6000);
                    }
                } else {
                    console.log('[LISTA-EXEC] ⚠️ Botão de anexos não encontrado');
                }
            }
            
            // Se for um grupo de anexos (tipo "Anexos da Pesquisa Patrimonial")
            if (medida.tipoItem === 'anexos') {
                console.log('[LISTA-EXEC] Item é um grupo de anexos, clicando no botão...');
                
                if (medida.link) {
                    // Destacar o botão de anexos
                    const estiloOriginalBtn = medida.link.style.cssText;
                    medida.link.style.cssText += `
                        background: linear-gradient(45deg, #d1ecf1, #b8daff) !important;
                        border: 3px solid #17a2b8 !important;
                        border-radius: 6px !important;
                        transform: scale(1.05) !important;
                        transition: all 0.3s ease !important;
                        box-shadow: 0 4px 15px rgba(23,162,184,0.4) !important;
                        color: #0c5460 !important;
                        font-weight: bold !important;
                    `;
                    
                    // Aguardar um pouco e depois clicar no botão de anexos
                    setTimeout(() => {
                        console.log('[LISTA-EXEC] Clicando no botão de anexos para expandir...');
                        try {
                            medida.link.click();
                            console.log('[LISTA-EXEC] ✅ Clique no botão de anexos executado com sucesso');
                            
                            // Feedback visual adicional após o clique
                            setTimeout(() => {
                                medida.link.style.cssText += `
                                    background: linear-gradient(45deg, #d4edda, #c3e6cb) !important;
                                    border: 3px solid #28a745 !important;
                                    color: #155724 !important;
                                `;
                            }, 500);
                            
                        } catch (clickError) {
                            console.error('[LISTA-EXEC] Erro ao clicar no botão de anexos:', clickError);
                            
                            // Feedback visual de erro
                            medida.link.style.cssText += `
                                background: linear-gradient(45deg, #f8d7da, #f5c6cb) !important;
                                border: 3px solid #dc3545 !important;
                                color: #721c24 !important;
                            `;
                        }
                    }, 800);
                    
                    // Remover destaque após 6 segundos
                    setTimeout(() => {
                        medida.link.style.cssText = estiloOriginalBtn;
                    }, 6000);
                }
            }
            
            // Destacar elemento principal (container do item)
            setTimeout(() => {
                const estiloOriginal = medida.elemento.style.cssText;
                medida.elemento.style.cssText += `
                    background: linear-gradient(45deg, #d4edda, #c3e6cb) !important;
                    border: 3px solid #28a745 !important;
                    border-radius: 8px !important;
                    transform: scale(1.02) !important;
                    transition: all 0.3s ease !important;
                    box-shadow: 0 4px 15px rgba(40,167,69,0.3) !important;
                `;
                
                // Piscar destaque no container
                let piscar = 0;
                const intervalo = setInterval(() => {
                    medida.elemento.style.opacity = piscar % 2 === 0 ? '0.8' : '1';
                    piscar++;
                    if (piscar > 6) {
                        clearInterval(intervalo);
                        medida.elemento.style.opacity = '1';
                    }
                }, 400);
                
                // Remover destaque após 5 segundos
                setTimeout(() => {
                    medida.elemento.style.cssText = estiloOriginal;
                }, 5000);
                
                // Restaurar linha da tabela
                elemento.style.backgroundColor = '#28a745';
                elemento.style.color = 'white';
                
                setTimeout(() => {
                    elemento.style.backgroundColor = corOriginal;
                    elemento.style.color = '';
                }, 3000);
                
            }, medida.tipoItem === 'anexo' ? 1000 : 500);
            
        } catch (e) {
            console.error('[LISTA-EXEC] Erro ao selecionar medida:', e);
            elemento.style.backgroundColor = '#dc3545';
            elemento.style.color = 'white';
            setTimeout(() => {
                elemento.style.backgroundColor = '';
                elemento.style.color = '';
            }, 3000);
        }
    }
    
    // Função para gerar relatório em texto
    function gerarRelatorioTexto(medidas) {
        try {
            console.log('[LISTA-EXEC] Gerando relatório...');
            
            let relatorio = 'Verifica-se que nos autos já foram realizadas as seguintes medidas executórias:\n\n';
            
            medidas.forEach((medida, index) => {
                relatorio += `- ${medida.nome} (${medida.id}, ${medida.data})\n`;
            });
            
            if (medidas.length === 0) {
                relatorio += '- Nenhuma medida executória encontrada até maio de 2024.\n';
            }
            
            // Copiar para área de transferência
            navigator.clipboard.writeText(relatorio).then(() => {
                console.log('[LISTA-EXEC] ✅ Relatório copiado para área de transferência');
                
                // Feedback visual
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 999999;
                    background: #28a745;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    font-weight: bold;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                `;
                notification.textContent = '✅ Relatório copiado para área de transferência!';
                
                document.body.appendChild(notification);
                
                // Animação
                setTimeout(() => notification.style.opacity = '1', 100);
                setTimeout(() => {
                    notification.style.opacity = '0';
                    setTimeout(() => document.body.removeChild(notification), 300);
                }, 3000);
                
            }).catch(err => {
                console.error('[LISTA-EXEC] Erro ao copiar relatório:', err);
                alert('Erro ao copiar relatório para área de transferência. Texto gerado:\n\n' + relatorio);
            });
            
        } catch (e) {
            console.error('[LISTA-EXEC] Erro ao gerar relatório:', e);
            alert('Erro ao gerar relatório: ' + e.message);
        }
    }
    
    // Função principal de pesquisa
    async function executarPesquisaTimeline() {
        try {
            console.log('[LISTA-EXEC] Executando pesquisa...');
            
            // Feedback visual no botão
            const botao = document.getElementById('btnListaExec');
            const textoOriginal = botao.textContent;
            botao.textContent = '⏳ Pesquisando...';
            botao.style.backgroundColor = '#ffc107';
            
            // Ler timeline e gerar tabela
            const medidas = await lerMedidasExecutorias();
            gerarTabelaMedidas(medidas);
            
            // Restaurar botão
            setTimeout(() => {
                botao.textContent = textoOriginal;
                botao.style.backgroundColor = '#28a745';
            }, 1500);
            
        } catch (e) {
            console.error('[LISTA-EXEC] Erro na pesquisa:', e);
            alert('Erro durante a pesquisa: ' + e.message);
            
            const botao = document.getElementById('btnListaExec');
            if (botao) {
                botao.textContent = '❌ Erro';
                botao.style.backgroundColor = '#dc3545';
                setTimeout(() => {
                    botao.textContent = '🔍 Pesquisas';
                    botao.style.backgroundColor = '#28a745';
                }, 3000);
            }
        }
    }
    
    // Função para registrar log de data da timeline
    function registrarDataTimeline(data, seletor, nome, id) {
        const logEntry = `${data}\t${seletor}\t${nome}\t${id}`;
        // Salva no localStorage (simulando timeline.txt)
        let log = localStorage.getItem('timeline_log') || '';
        log += logEntry + '\n';
        localStorage.setItem('timeline_log', log);
        // Também exibe no console
        console.log(`[TIMELINE-LOG] ${logEntry}`);
    }
    
    // Inicialização
    function inicializar() {
        console.log('[LISTA-EXEC] Inicializando...');
        
        if (window.location.href.includes('/detalhe')) {
            console.log('[LISTA-EXEC] ✅ URL válida (/detalhe), criando botão...');
            criarBotaoPesquisas();
        } else {
            console.log('[LISTA-EXEC] ❌ URL não contém /detalhe');
        }
    }
    
    // Executar após carregamento
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log('[LISTA-EXEC] Página já carregada, executando imediatamente');
        inicializar();
    } else {
        console.log('[LISTA-EXEC] Aguardando carregamento da página');
        document.addEventListener('DOMContentLoaded', inicializar);
    }
    
})();
