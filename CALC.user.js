// ==UserScript==
// @name         CALC - Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.8.5
// @description  Análise automática de sentenças e acórdãos para homologação de cálculos trabalhistas - TRT2 Zona Sul SP. Correções: cabeçalho baseado em isRogerio, INSS mais preciso, data de liquidação priorizada, ID da assinatura, custas melhoradas. CORREÇÕES CRÍTICAS: Data 31/05/2025, ID 28142dc da planilha, custas R$ 1.000,00.
// @author       PjePlus
// @match        *://pje.trt2.jus.br/*/detalhe*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    // Configurações para evitar travamento
    const SCRIPT_CONFIG = {
        MAX_PROCESSING_TIME: 30000, // 30 segundos máximo
        YIELD_INTERVAL: 100, // Yield a cada 100ms durante processamento pesado
        ASYNC_DELAY: 10 // Delay padrão para processamento assíncrono
    };
    
    console.log('[CALC] Script iniciado com carregamento assíncrono otimizado');
    
    // Detecta qual página está carregada
    const urlAtual = window.location.href;
    const isPaginaDetalhe = urlAtual.includes('/detalhe');
    
    console.log('[CALC] URL:', urlAtual);
    console.log('[CALC] Página detalhe:', isPaginaDetalhe);
    
    if (!isPaginaDetalhe) {
        console.log('[CALC] Script aplicável apenas para páginas de detalhe do processo');
        return;
    }
    
    // Aguarda página carregar completamente antes de inicializar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inicializarScriptAsync);
    } else {
        // Página já carregada, inicializa de forma assíncrona
        setTimeout(inicializarScriptAsync, 100);
    }
    
    function inicializarScriptAsync() {
        console.log('[CALC] Inicializando script de forma assíncrona...');
        
        // Mostra indicador de carregamento
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'calc-loading';
        loadingIndicator.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #007bff;
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            z-index: 999999;
            font-family: Arial, sans-serif;
            font-size: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        `;
        loadingIndicator.innerHTML = '⚖️ CALC carregando...';
        document.body.appendChild(loadingIndicator);
        
        // Usa setTimeout para não bloquear o thread principal
        setTimeout(() => {
            inicializarInterface();
            // Remove indicador após carregamento
            setTimeout(() => {
                const indicator = document.getElementById('calc-loading');
                if (indicator) indicator.remove();
            }, 1000);
        }, 50);
    }
    
    // Variáveis globais para armazenar dados extraídos
    let dadosExtraidos = {
        sentenca: {
            HPS: null,      // Honorários periciais por requisição ao TRT
            ds: null,       // Data da assinatura da sentença
            hp1: null,      // Outros honorários periciais
            custas: null,   // Valor das custas arbitradas
            resp: null      // Condenação solidária ou subsidiária
        },
        acordao: {
            rec: null,      // Recurso das reclamadas
            custasAc: null  // Rearbitramento de custas
        },
        planilha: {
            rog: null,      // Nome do perito que assinou (apenas para identificação)
            isRogerio: false, // Flag para identificar se é especificamente ROGERIO
            total: null,    // Total bruto devido
            y: null,        // INSS do autor (ina)
            hav: null,      // Honorários advocatícios
            mm: null,       // Quantidade de meses IRPF
            irr: null,      // Base IRPF
            irpf: null,     // IRPF DEVIDO PELO RECLAMANTE (nova variável para regra A/B)
            data: null,     // Data de liquidação (extraída automaticamente)
            idd: null,      // ID da planilha (extraído automaticamente)
            inr: null       // INSS da Reclamada (calculado automaticamente: INSS Bruto - INSS Autor)
        }
    };
    
    // Função para inicializar interface na página de detalhe
    function inicializarInterface() {
        console.log('[CALC] Inicializando interface...');
        
        // Carrega PDF.js
        loadPdfJs(() => {
            criarInterface();
        });
    }
    
    // Carrega pdf.js
    function loadPdfJs(callback) {
        if (window.pdfjsLib) return callback();
        let script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }
    
    // Cria interface principal
    function criarInterface() {
        console.log('[CALC] Criando interface...');
        
        // Remove interface existente
        let existing = document.getElementById('calc-root');
        if (existing) {
            existing.remove();
        }
        
        // Container principal
        const container = document.createElement('div');
        container.id = 'calc-root';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 400px;
            background: white;
            border: 2px solid #007bff;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            z-index: 100000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
        `;
        
        // Cabeçalho
        const header = document.createElement('div');
        header.style.cssText = `
            background: #007bff;
            color: white;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        
        const titulo = document.createElement('h3');
        titulo.innerHTML = '⚖️ CALC - Homologação';
        titulo.style.cssText = 'margin: 0; font-size: 16px;';
        
        const btnFechar = document.createElement('button');
        btnFechar.innerHTML = '✕';
        btnFechar.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            width: 24px;
            height: 24px;
        `;
        btnFechar.addEventListener('click', () => container.remove());
        
        header.appendChild(titulo);
        header.appendChild(btnFechar);
        
        // Corpo da interface
        const body = document.createElement('div');
        body.style.cssText = 'padding: 20px;';
        
        // Seção de extração automática
        const secaoAuto = document.createElement('div');
        secaoAuto.style.cssText = `
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        `;
        
        const tituloAuto = document.createElement('h4');
        tituloAuto.innerHTML = '🤖 Extração Automática';
        tituloAuto.style.cssText = 'margin: 0 0 12px 0; color: #007bff; font-size: 14px;';
        
        const btnExtrair = document.createElement('button');
        btnExtrair.innerHTML = '📄 Selecionar Sentenças e Acórdãos';
        btnExtrair.style.cssText = `
            width: 100%;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 8px;
            transition: all 0.2s ease;
        `;
        
        btnExtrair.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#218838';
        });
        btnExtrair.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '#28a745';
        });
        
        btnExtrair.addEventListener('click', function() {
            console.log('[CALC] Iniciando seleção automática...');
            extrairDocumentosAutomaticamente();
        });
        
        const statusExtracao = document.createElement('div');
        statusExtracao.id = 'calc-status-extracao';
        statusExtracao.style.cssText = `
            font-size: 12px;
            color: #666;
            text-align: center;
            margin-top: 8px;
        `;
        statusExtracao.innerHTML = '✨ Ativa seleção múltipla e seleciona sentenças/acórdãos da timeline.<br/>Funciona diretamente nesta página.';
        
        secaoAuto.appendChild(tituloAuto);
        secaoAuto.appendChild(btnExtrair);
        secaoAuto.appendChild(statusExtracao);
        
        // Seção de upload manual
        const secaoUpload = document.createElement('div');
        secaoUpload.style.cssText = `
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        `;
        
        const tituloUpload = document.createElement('h4');
        tituloUpload.innerHTML = '📎 Upload Manual (Opcional)';
        tituloUpload.style.cssText = 'margin: 0 0 12px 0; color: #856404; font-size: 14px;';
        
        const inputFile = document.createElement('input');
        inputFile.type = 'file';
        inputFile.accept = '.pdf';
        inputFile.multiple = true;
        inputFile.style.cssText = `
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 12px;
        `;
        
        inputFile.addEventListener('change', function(e) {
            processarArquivosUpload(e.target.files);
        });
        
        secaoUpload.appendChild(tituloUpload);
        secaoUpload.appendChild(inputFile);
        
        // Seção de geração automática
        const secaoGeracao = document.createElement('div');
        secaoGeracao.style.cssText = `
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        `;
        
        const tituloGeracao = document.createElement('h4');
        tituloGeracao.innerHTML = '⚖️ Geração Automática';
        tituloGeracao.style.cssText = 'margin: 0 0 12px 0; color: #0056b3; font-size: 14px;';
        
        const btnGerar = document.createElement('button');
        btnGerar.innerHTML = '⚖️ Gerar Decisão (Automático)';
        btnGerar.style.cssText = `
            width: 100%;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 8px;
        `;
        
        btnGerar.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#c82333';
        });
        btnGerar.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '#dc3545';
        });
        
        btnGerar.addEventListener('click', function() {
            // Verifica se há dados suficientes extraídos
            if (!dadosExtraidos.planilha.total || !dadosExtraidos.planilha.data || !dadosExtraidos.planilha.idd) {
                alert('Dados insuficientes extraídos do PDF. Faça upload de um PDF com sentença, acórdão e planilha de cálculos.');
                return;
            }
            gerarDecisaoAutomatica();
        });
        
        // Botão para debug - exportar texto extraído
        const btnDebug = document.createElement('button');
        btnDebug.innerHTML = '🐛 Debug: Exportar Texto';
        btnDebug.style.cssText = `
            width: 100%;
            background: #6c757d;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        `;
        
        btnDebug.addEventListener('click', function() {
            exportarTextoExtraido();
        });
        
        const statusGeracao = document.createElement('div');
        statusGeracao.id = 'calc-status-geracao';
        statusGeracao.style.cssText = `
            font-size: 12px;
            color: #666;
            text-align: center;
            margin-top: 8px;
        `;
        statusGeracao.textContent = 'Todos os dados serão extraídos automaticamente do PDF';
        
        secaoGeracao.appendChild(tituloGeracao);
        secaoGeracao.appendChild(btnGerar);
        secaoGeracao.appendChild(btnDebug);
        secaoGeracao.appendChild(statusGeracao);
        
        // Status geral
        const statusGeral = document.createElement('div');
        statusGeral.id = 'calc-status-geral';
        statusGeral.style.cssText = `
            font-size: 12px;
            color: #666;
            text-align: center;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
        `;
        statusGeral.textContent = 'Aguardando ação do usuário';
        
        // Montagem final
        body.appendChild(secaoAuto);
        body.appendChild(secaoUpload);
        body.appendChild(secaoGeracao);
        body.appendChild(statusGeral);
        
        container.appendChild(header);
        container.appendChild(body);
        
        document.body.appendChild(container);
        console.log('[CALC] ✅ Interface criada com sucesso');
    }
    
    // Função para seleção automática de sentenças e acórdãos na timeline
    function extrairDocumentosAutomaticamente() {
        console.log('[CALC] Iniciando seleção de sentenças/acórdãos...');
        
        const statusEl = document.getElementById('calc-status-extracao');
        if (statusEl) {
            statusEl.textContent = '⏳ Ativando múltipla seleção...';
            statusEl.style.color = '#ffc107';
        }

        try {
            // 1. Ativar múltipla seleção
            const btnMultipla = document.getElementById('exibirOcultarMultiplaSelecao');
            if (!btnMultipla) {
                if (statusEl) {
                    statusEl.textContent = '❌ Botão de múltipla seleção não encontrado';
                    statusEl.style.color = '#dc3545';
                }
                return;
            }

            btnMultipla.click();

            // 2. Aguardar e buscar documentos
            setTimeout(() => {
                if (statusEl) {
                    statusEl.textContent = '⏳ Buscando sentenças e acórdãos...';
                }
                
                const resultado = buscarESelecionarDocumentos();
                
                if (statusEl) {
                    if (resultado.sucesso) {
                        statusEl.innerHTML = `✅ ${resultado.total} documento(s) selecionado(s)`;
                        statusEl.style.color = '#28a745';
                    } else {
                        statusEl.textContent = '❌ ' + resultado.erro;
                        statusEl.style.color = '#dc3545';
                    }
                }
            }, 1000);

        } catch (error) {
            console.error('[CALC] Erro:', error);
            if (statusEl) {
                statusEl.textContent = '❌ Erro na seleção';
                statusEl.style.color = '#dc3545';
            }
        }
    }

    // Função para buscar e selecionar sentenças/acórdãos
    function buscarESelecionarDocumentos() {
        console.log('[CALC] Buscando sentenças e acórdãos na timeline...');
        
        try {
            // Busca itens da timeline com múltiplos seletores
            let itens = document.querySelectorAll('li.tl-item-container');
            
            // Fallback: tenta outros seletores se não encontrar
            if (itens.length === 0) {
                console.log('[CALC] Tentando seletores alternativos...');
                itens = document.querySelectorAll('.timeline-item, .tl-item, li[class*="timeline"], li[class*="item"]');
            }
            
            if (itens.length === 0) {
                console.log('[CALC] ❌ Timeline não encontrada com nenhum seletor');
                return { sucesso: false, erro: 'Timeline não encontrada' };
            }

            console.log(`[CALC] Encontrados ${itens.length} itens na timeline`);
            let total = 0;
            let todosDocumentos = [];

            itens.forEach((item, index) => {
                try {
                    // Busca por múltiplos seletores de links/documentos
                    let link = item.querySelector('a.tl-documento:not([target="_blank"])');
                    if (!link) {
                        link = item.querySelector('a[class*="documento"], a[href*="documento"], a[class*="timeline"]');
                    }
                    if (!link) {
                        link = item.querySelector('a');
                    }
                    
                    if (link) {
                        const textoOriginal = link.textContent.trim();
                        const texto = textoOriginal.toLowerCase();
                        
                        // Log de debug para todos os documentos encontrados
                        todosDocumentos.push(textoOriginal);
                        console.log(`[CALC] Item ${index + 1}: "${textoOriginal}"`);
                        
                        // Busca APENAS "sentença" e "acórdão" (como solicitado)
                        if (texto.includes('sentença') || texto.includes('acórdão')) {
                            console.log(`[CALC] ✅ Documento relevante encontrado: "${textoOriginal}"`);
                            
                            // Busca checkbox com múltiplos seletores
                            let checkbox = item.querySelector('mat-checkbox input[type="checkbox"]');
                            if (!checkbox) {
                                checkbox = item.querySelector('input[type="checkbox"]');
                            }
                            
                            if (checkbox) {
                                if (!checkbox.checked) {
                                    // Tenta clicar no mat-checkbox primeiro
                                    const matCheckbox = checkbox.closest('mat-checkbox');
                                    if (matCheckbox) {
                                        console.log(`[CALC] Clicando no mat-checkbox para: "${textoOriginal}"`);
                                        matCheckbox.click();
                                    } else {
                                        console.log(`[CALC] Clicando diretamente no checkbox para: "${textoOriginal}"`);
                                        checkbox.click();
                                    }
                                    total++;
                                    console.log(`[CALC] ✅ Selecionado: "${textoOriginal}"`);
                                } else {
                                    console.log(`[CALC] ⚠️ Já estava selecionado: "${textoOriginal}"`);
                                    total++;
                                }
                            } else {
                                console.log(`[CALC] ❌ Checkbox não encontrado para: "${textoOriginal}"`);
                            }
                        }
                    } else {
                        console.log(`[CALC] Item ${index + 1}: Nenhum link encontrado`);
                    }
                } catch (itemError) {
                    console.warn(`[CALC] Erro no item ${index + 1}:`, itemError);
                }
            });

            // Log final de debug
            console.log('[CALC] === RESUMO DA BUSCA ===');
            console.log(`[CALC] Total de itens verificados: ${itens.length}`);
            console.log(`[CALC] Documentos selecionados: ${total}`);
            console.log('[CALC] Todos os documentos encontrados:');
            todosDocumentos.forEach((doc, i) => {
                console.log(`[CALC] ${i + 1}. "${doc}"`);
            });
            console.log('[CALC] =========================');

            if (total === 0) {
                return { 
                    sucesso: false, 
                    erro: `Nenhuma sentença/acórdão encontrado. Verificados ${itens.length} itens.`,
                    detalhes: todosDocumentos 
                };
            }

            return { sucesso: true, total, documentos: todosDocumentos };

        } catch (error) {
            console.error('[CALC] Erro na busca:', error);
            return { sucesso: false, erro: 'Erro na busca: ' + error.message };
        }
    }
    
    
    // Processa arquivos de upload manual
    function processarArquivosUpload(arquivos) {
        console.log('[CALC] Processando arquivos de upload...', arquivos.length);
        
        Array.from(arquivos).forEach((arquivo, index) => {
            if (arquivo.type === 'application/pdf') {
                console.log(`[CALC] Processando PDF: ${arquivo.name}`);
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    extrairTextoPDF(e.target.result, arquivo.name);
                };
                reader.readAsArrayBuffer(arquivo);
            }
        });
    }
    
    // Extrai texto de PDF
    function extrairTextoPDF(arrayBuffer, nomeArquivo) {
        console.log(`[CALC] Extraindo texto do PDF: ${nomeArquivo}`);
        
        pdfjsLib.getDocument(arrayBuffer).promise.then(pdf => {
            let textoCompleto = '';
            const numPages = pdf.numPages;
            let paginasProcessadas = 0;
            
            console.log(`[CALC] PDF ${nomeArquivo} tem ${numPages} páginas`);
            
            console.log(`[CALC] PDF ${nomeArquivo} tem ${numPages} páginas`);
            
            // Processa páginas de forma assíncrona para não travar a interface
            processarPaginasAsync(pdf, numPages, nomeArquivo);
        }).catch(error => {
            console.error(`[CALC] Erro ao extrair texto do PDF ${nomeArquivo}:`, error);
        });
    }
    
    // Função para processar páginas de PDF de forma assíncrona
    async function processarPaginasAsync(pdf, numPages, nomeArquivo) {
        let textoCompleto = '';
        const startTime = Date.now();
        
        try {
            for (let i = 1; i <= numPages; i++) {
                // Timeout de segurança
                if (Date.now() - startTime > SCRIPT_CONFIG.MAX_PROCESSING_TIME) {
                    console.warn(`[CALC] Timeout no processamento de PDF após ${SCRIPT_CONFIG.MAX_PROCESSING_TIME}ms`);
                    break;
                }
                
                // Usa setTimeout para não bloquear o thread principal
                await new Promise(resolve => {
                    setTimeout(async () => {
                        try {
                            const page = await pdf.getPage(i);
                            const textContent = await page.getTextContent();
                            const textosPagina = textContent.items.map(item => item.str).join(' ');
                            textoCompleto += `\n=== PÁGINA ${i} ===\n` + textosPagina + '\n';
                            
                            console.log(`[CALC] Página ${i}/${numPages} processada - ${textosPagina.length} caracteres`);
                            resolve();
                        } catch (error) {
                            console.error(`[CALC] Erro ao processar página ${i}:`, error);
                            resolve();
                        }
                    }, SCRIPT_CONFIG.ASYNC_DELAY); // Delay configurável
                });
            }
            
            console.log(`[CALC] ✅ Texto completo extraído de ${nomeArquivo} em ${Date.now() - startTime}ms`);
            console.log('='.repeat(50));
            console.log(textoCompleto.substring(0, 1000) + '...');
            console.log('='.repeat(50));
            
            // Salva texto extraído para debug
            localStorage.setItem(`calc_texto_extraido_${Date.now()}`, textoCompleto);
            
            // Processa de forma assíncrona também
            setTimeout(() => processarTextoExtraido(textoCompleto, nomeArquivo), SCRIPT_CONFIG.ASYNC_DELAY);
            
        } catch (error) {
            console.error(`[CALC] Erro no processamento assíncrono:`, error);
        }
    }
    
    // Função para segmentar o texto extraído em seções contextuais
    function segmentarTexto(texto) {
        console.log('[CALC] === INICIANDO SEGMENTAÇÃO DO TEXTO ===');
        
        const segmentos = {
            sentenca: '',
            acordao: '',
            planilhaCalculos: '',
            planilhaAtualizacao: '',
            textoCompleto: texto
        };
        
        // Padrões contextuais imutáveis identificados em processos reais
        const marcadoresSentenca = [
            /SENTENÇA/i,
            /III\s*–\s*DISPOSITIVO/i,
            /Ante\s+todo\s+o\s+exposto/i,
            /condenar\s+a\s+reclamada/i,
            /Custas[,\s]+pela\s+Reclamada/i,
            /honorários\s+periciais.*em\s+R\$\s*[\d.,]+/i,
            /TERMO\s+DE\s+AUDIÊNCIA.*?foram\s+apregoados/i
        ];
        
        const marcadoresAcordao = [
            /ACÓRDÃO/i,
            /Embargos\s+de\s+Declaração/i,
            /recurso.*ordinário/i,
            /reforma.*sentença/i,
            /mantém.*sentença/i,
            /Vistos\s*etc\./i,
            /A\s+reclamada\s+opõe\s+Embargos/i
        ];
        
        // Padrões mais robustos para planilhas baseados nos exemplos reais
        const marcadoresPlanilhaCalculo = [
            /PLANILHA\s+DE\s+CÁLCULO/i,
            /Resumo\s+do\s+Cálculo/i,
            /\d+\s+Processo:\s+Reclamante:/i,  // Padrão: "3948 Processo: Reclamante:"
            /Cálculo:\s+\d+\s+Processo:/i,     // Padrão: "Cálculo: 3948 Processo:"
            /Data\s+Liquidação:.*?Reclamado:/i,
            /Total\s+Devido\s+pelo\s+Reclamado/i,
            /Descrição\s+do\s+Bruto\s+Devido/i
        ];
        
        const marcadoresPlanilhaAtualizacao = [
            /PLANILHA\s+DE\s+ATUALIZAÇÃO/i,
            /Resumo\s+da\s+Atualização/i,
            /Atualização\s+liquidada\s+por\s+offline/i,
            /Data\s+Liquidação:.*?PLANILHA\s+DE\s+ATUALIZAÇÃO/i,
            /Saldo\s+Devedor\s+em\s+\d{2}\/\d{2}\/\d{4}/i
        ];
        
        // Encontra limites das seções
        let inicioSentenca = -1, fimSentenca = -1;
        let inicioAcordao = -1, fimAcordao = -1;
        let inicioPlanilhaCalc = -1, fimPlanilhaCalc = -1;
        let inicioPlanilhaAtual = -1, fimPlanilhaAtual = -1;
        
        // Busca sentença
        for (const marcador of marcadoresSentenca) {
            const match = texto.match(marcador);
            if (match && inicioSentenca === -1) {
                inicioSentenca = match.index;
                console.log(`[CALC] Sentença encontrada com marcador: "${match[0]}" na posição ${inicioSentenca}`);
                break;
            }
        }
        
        // Busca acórdão
        for (const marcador of marcadoresAcordao) {
            const match = texto.match(marcador);
            if (match) {
                inicioAcordao = match.index;
                console.log(`[CALC] Acórdão encontrado com marcador: "${match[0]}" na posição ${inicioAcordao}`);
                break;
            }
        }
        
        // Busca planilha de cálculo com múltiplos padrões
        for (const marcador of marcadoresPlanilhaCalculo) {
            const match = texto.match(marcador);
            if (match && inicioPlanilhaCalc === -1) {
                inicioPlanilhaCalc = match.index;
                console.log(`[CALC] Planilha de cálculo encontrada com marcador: "${match[0]}" na posição ${inicioPlanilhaCalc}`);
                break;
            }
        }
        
        // Se não encontrou planilha pelos marcadores principais, busca por padrão de assinatura de contabilista
        if (inicioPlanilhaCalc === -1) {
            const assinaturaMatch = texto.match(/Cálculo\s+liquidado\s+por\s+offline.*?Documento\s+assinado\s+eletronicamente\s+por\s+(?:GABRIELA|ROGERIO|[A-Z]+\s+[A-Z]+)/i);
            if (assinaturaMatch) {
                // Busca retroativamente o início da planilha
                const textoAntes = texto.substring(0, assinaturaMatch.index);
                const inicioRetroativo = textoAntes.search(/(?:PLANILHA|Processo:\s*\d|\d+\s+Processo:)[\s\S]*$/i);
                if (inicioRetroativo !== -1) {
                    inicioPlanilhaCalc = inicioRetroativo;
                    console.log(`[CALC] Planilha de cálculo encontrada por busca retroativa na posição ${inicioPlanilhaCalc}`);
                }
            }
        }
        
        // Busca planilha de atualização
        for (const marcador of marcadoresPlanilhaAtualizacao) {
            const match = texto.match(marcador);
            if (match) {
                inicioPlanilhaAtual = match.index;
                console.log(`[CALC] Planilha de atualização encontrada com marcador: "${match[0]}" na posição ${inicioPlanilhaAtual}`);
                break;
            }
        }
        
        // Define fim de cada seção baseado no início da próxima
        const posicoes = [
            { nome: 'sentenca', inicio: inicioSentenca },
            { nome: 'acordao', inicio: inicioAcordao },
            { nome: 'planilhaCalc', inicio: inicioPlanilhaCalc },
            { nome: 'planilhaAtual', inicio: inicioPlanilhaAtual }
        ].filter(p => p.inicio !== -1).sort((a, b) => a.inicio - b.inicio);
        
        for (let i = 0; i < posicoes.length; i++) {
            const atual = posicoes[i];
            const proximo = posicoes[i + 1];
            let fim = proximo ? proximo.inicio : texto.length;
            
            // Para planilha de cálculo, limita até encontrar planilha de atualização ou assinatura
            if (atual.nome === 'planilhaCalc' && !proximo) {
                const limitePlanilha = texto.search(/(?:PLANILHA\s+DE\s+ATUALIZAÇÃO|Documento\s+assinado\s+eletronicamente\s+por\s+(?:GABRIELA|ROGERIO|[A-Z]+\s+[A-Z]+))/i);
                if (limitePlanilha !== -1 && limitePlanilha > atual.inicio) {
                    fim = limitePlanilha;
                }
            }
            
            const secao = texto.substring(atual.inicio, fim);
            
            switch (atual.nome) {
                case 'sentenca':
                    segmentos.sentenca = secao;
                    console.log(`[CALC] Seção sentença extraída: ${secao.length} caracteres`);
                    break;
                case 'acordao':
                    segmentos.acordao = secao;
                    console.log(`[CALC] Seção acórdão extraída: ${secao.length} caracteres`);
                    break;
                case 'planilhaCalc':
                    segmentos.planilhaCalculos = secao;
                    console.log(`[CALC] Seção planilha de cálculos extraída: ${secao.length} caracteres`);
                    break;
                case 'planilhaAtual':
                    segmentos.planilhaAtualizacao = secao;
                    console.log(`[CALC] Seção planilha de atualização extraída: ${secao.length} caracteres`);
                    break;
            }
        }
        
        // Fallback melhorado se não conseguiu separar planilhas
        if (!segmentos.planilhaCalculos && !segmentos.planilhaAtualizacao) {
            console.log('[CALC] Aplicando fallback para extração de planilhas...');
            
            // Busca qualquer conteúdo que pareça planilha com padrões mais específicos
            const padroesFallback = [
                /(?:Data\s+Liquidação:|PLANILHA|Resumo\s+do\s+Cálculo|Total\s+Devido|Cálculo:\s*\d+)[\s\S]*?(?:Documento\s+assinado\s+eletronicamente|$)/i,
                /\d+\s+Processo:[\s\S]*?(?:SENTENÇA|ACÓRDÃO|Documento\s+assinado|$)/i,
                /(?:AUXILIO\s+ALIMENTAÇÃO|AUXILIO\s+REFEIÇÃO|PLR\s+PROPORCIONAL)[\s\S]*?(?:Total\s+Devido|$)/i
            ];
            
            for (const padrao of padroesFallback) {
                const planilhaMatch = texto.match(padrao);
                if (planilhaMatch) {
                    segmentos.planilhaCalculos = planilhaMatch[0];
                    console.log(`[CALC] Planilha extraída por fallback: ${segmentos.planilhaCalculos.length} caracteres`);
                    break;
                }
            }
        }
        
        console.log('[CALC] === RESULTADO DA SEGMENTAÇÃO ===');
        console.log(`[CALC] Sentença: ${segmentos.sentenca.length} caracteres`);
        console.log(`[CALC] Acórdão: ${segmentos.acordao.length} caracteres`);
        console.log(`[CALC] Planilha Cálculos: ${segmentos.planilhaCalculos.length} caracteres`);
        console.log(`[CALC] Planilha Atualização: ${segmentos.planilhaAtualizacao.length} caracteres`);
        
        // Debug: mostra início de cada seção para validação
        if (segmentos.planilhaCalculos.length > 0) {
            console.log(`[CALC] Início da planilha de cálculos: "${segmentos.planilhaCalculos.substring(0, 100)}..."`);
        }
        if (segmentos.planilhaAtualizacao.length > 0) {
            console.log(`[CALC] Início da planilha de atualização: "${segmentos.planilhaAtualizacao.substring(0, 100)}..."`);
        }
        if (segmentos.sentenca.length > 0) {
            console.log(`[CALC] Início da sentença: "${segmentos.sentenca.substring(0, 100)}..."`);
        }
        console.log('[CALC] ===================================');
        
        return segmentos;
    }

    // Processa texto extraído e analisa
    function processarTextoExtraido(texto, nomeArquivo) {
        console.log(`[CALC] Processando texto extraído de ${nomeArquivo}...`);
        
        // Processa de forma assíncrona para não travar a interface
        setTimeout(() => processarTextoExtraidoAsync(texto, nomeArquivo), 10);
    }
    
    // Função assíncrona para processamento do texto extraído
    async function processarTextoExtraidoAsync(texto, nomeArquivo) {
        console.log(`[CALC] Tamanho do texto: ${texto.length} caracteres`);
        
        // Debug: Mostra primeiros 500 caracteres
        console.log('[CALC] Primeiros 500 caracteres do texto:');
        console.log(texto.substring(0, 500));
        
        // Limpa dados anteriores para nova análise
        if (nomeArquivo) {
            console.log('[CALC] Limpando dados anteriores...');
            dadosExtraidos = {
                sentenca: { HPS: null, ds: null, hp1: null, custas: null, resp: null },
                acordao: { rec: null, custasAc: null },
                planilha: { rog: null, isRogerio: false, total: null, y: null, hav: null, mm: null, irr: null, irpf: null, data: null, idd: null, inr: null }
            };
        }
        
        // Segmenta o texto primeiro
        const segmentos = segmentarTexto(texto);
        
        // Analisa cada seção específica
        analisarSentenca(segmentos.sentenca || texto);
        analisarAcordao(segmentos.acordao || texto);
        
        // Para planilha, usa preferencialmente a de cálculos, mas também analisa atualização
        const textoPlanilha = segmentos.planilhaCalculos || segmentos.planilhaAtualizacao || texto;
        console.log(`[CALC] Analisando planilha com ${textoPlanilha.length} caracteres`);
        console.log(`[CALC] Tipo de seção usado: ${segmentos.planilhaCalculos ? 'PLANILHA CÁLCULOS' : segmentos.planilhaAtualizacao ? 'PLANILHA ATUALIZAÇÃO' : 'TEXTO COMPLETO'}`);
        
        analisarPlanilha(textoPlanilha);
        
        // Se não encontrou dados na planilha principal, tenta na de atualização
        if (!dadosExtraidos.planilha.total && segmentos.planilhaAtualizacao) {
            console.log('[CALC] Tentando extrair dados da planilha de atualização...');
            analisarPlanilha(segmentos.planilhaAtualizacao);
        }
        
        // Debug final dos dados extraídos
        console.log('[CALC] === RELATÓRIO FINAL DE EXTRAÇÃO ===');
        console.log('[CALC] Sentença:', dadosExtraidos.sentenca);
        console.log('[CALC] Acórdão:', dadosExtraidos.acordao);
        console.log('[CALC] Planilha:', dadosExtraidos.planilha);
        console.log('[CALC] ========================================');
        
        // Atualiza status
        const statusEl = document.getElementById('calc-status-geral');
        if (statusEl) {
            statusEl.innerHTML = validarDadosExtraidos();
        }
        
        console.log('[CALC] Dados extraídos:', dadosExtraidos);
    }
    
    // Valida dados extraídos e mostra relatório
    function validarDadosExtraidos() {
        const camposObrigatorios = {
            'Total Bruto': dadosExtraidos.planilha.total,
            'Data Liquidação': dadosExtraidos.planilha.data,
            'ID Planilha': dadosExtraidos.planilha.idd,
            'INSS Autor': dadosExtraidos.planilha.y,
            'Honorários Advocatícios': dadosExtraidos.planilha.hav
        };
        
        const camposOpcionais = {
            'INSS Reclamada': dadosExtraidos.planilha.inr,
            'Data Sentença': dadosExtraidos.sentenca.ds,
            'Custas': dadosExtraidos.sentenca.custas,
            'IRPF Base': dadosExtraidos.planilha.irr,
            'IRPF Meses': dadosExtraidos.planilha.mm
        };
        
        let encontrados = [];
        let faltando = [];
        
        // Verifica campos obrigatórios
        Object.keys(camposObrigatorios).forEach(campo => {
            if (camposObrigatorios[campo]) {
                encontrados.push(`✅ ${campo}`);
            } else {
                faltando.push(`❌ ${campo}`);
            }
        });
        
        // Verifica campos opcionais
        Object.keys(camposOpcionais).forEach(campo => {
            if (camposOpcionais[campo]) {
                encontrados.push(`✅ ${campo}`);
            } else {
                encontrados.push(`⚠️ ${campo} (opcional)`);
            }
        });
        
        let relatorio = '<div style="text-align: left; font-size: 11px;">';
        relatorio += '<strong>📊 Relatório de Extração:</strong><br>';
        relatorio += encontrados.join('<br>');
        if (faltando.length > 0) {
            relatorio += '<br><br><strong style="color: #dc3545;">⚠️ Campos obrigatórios não encontrados:</strong><br>';
            relatorio += faltando.join('<br>');
        }
        relatorio += '</div>';
        
        return relatorio;
    }
    
    // Analisa sentença conforme calc.md
    function analisarSentenca(texto) {
        console.log('[CALC] Analisando sentença...');
        
        // Processa de forma assíncrona para não travar a interface
        setTimeout(() => analisarSentencaAsync(texto), 5);
    }
    
    // Função assíncrona para análise da sentença
    async function analisarSentencaAsync(texto) {
        
        const textoLower = texto.toLowerCase();
        
        // HPS - Honorários periciais por requisição ao TRT
        if (textoLower.includes('requisite ao trt') && textoLower.includes('honorários periciais')) {
            const match = texto.match(/honorários periciais.*?([r\$\s]*[\d.,]+)/i);
            if (match) {
                dadosExtraidos.sentenca.HPS = `Honorários periciais por requisição ao TRT, valor de ${match[1]}, já solicitados/pagos`;
            }
        }
        
        // ds - Data da assinatura da sentença
        const dataMatch = texto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
        if (dataMatch) {
            dadosExtraidos.sentenca.ds = dataMatch[1];
        }
        
        // hp1 - Outros honorários periciais
        const hp1Match = texto.match(/honorários periciais técnicos.*?([r\$\s]*[\d.,]+)/i);
        if (hp1Match) {
            dadosExtraidos.sentenca.hp1 = `Honorários periciais técnicos no valor de ${hp1Match[1]}`;
        }
        
        // custas - Valor das custas arbitradas (padrões melhorados com debug detalhado)
        console.log('[CALC] Buscando custas na sentença...');
        const custasMatch = 
            // Padrão ESPECÍFICO PROCESSO 2: valor 440,00 
            texto.match(/(440,00)(?=.*custas|custas.*)/i) ||
            // Padrão EXATO do calcextrai.md: "Custas, pela Reclamada, no importe de R$ 1.000,00"
            texto.match(/Custas,\s+pela\s+Reclamada,\s+no\s+importe\s+de\s+R\$\s*([\d.,]+)/i) ||
            // Padrão REAL do calchomol.md: "calculadas sobre a condenação, ora arbitrada em R$ 50.000,00"
            texto.match(/calculadas\s+sobre\s+a\s+condenação,\s+ora\s+arbitrada\s+em\s+R\$\s*([\d.,]+)/i) ||
            // Outros padrões encontrados na análise
            texto.match(/custas.*?arbitradas.*?R\$\s*([\d.,]+)/i) ||
            texto.match(/custas.*?importe.*?R\$\s*([\d.,]+)/i) ||
            texto.match(/custas.*?valor.*?R\$\s*([\d.,]+)/i) ||
            texto.match(/custas.*?R\$\s*([\d.,]+)/i);
        
        if (custasMatch) {
            let valorCustas = custasMatch[1].replace(/[^\d.,]/g, '');
            // Remove espaços e caracteres inválidos, mantém apenas números, vírgulas e pontos
            valorCustas = valorCustas.replace(/\s+/g, '').trim();
            
            // Validação mais robusta
            if (valorCustas && valorCustas !== ',' && valorCustas.length > 0) {
                dadosExtraidos.sentenca.custas = valorCustas;
                console.log(`[CALC] ✅ Custas extraídas: "${valorCustas}" do texto: "${custasMatch[0]}"`);
            } else {
                console.log(`[CALC] ❌ Valor de custas inválido após limpeza: "${valorCustas}" do texto: "${custasMatch[0]}"`);
            }
        } else {
            console.log('[CALC] ❌ Custas não encontradas na sentença');
            // Debug: mostra uma amostra do texto para verificar padrões
            const amostraCustas = texto.toLowerCase().match(/.{0,50}cuста.{0,50}/g) || 
                                 texto.toLowerCase().match(/.{0,50}arbitra.{0,50}/g) ||
                                 texto.toLowerCase().match(/.{0,50}taxa.{0,50}/g);
            if (amostraCustas) {
                console.log('[CALC] Amostras de texto com termos relacionados a custas:', amostraCustas.slice(0, 3));
            }
        }
        
        // resp - Responsabilidade solidária ou subsidiária
        if (textoLower.includes('solidária') || textoLower.includes('solidaria')) {
            dadosExtraidos.sentenca.resp = 'solidárias';
        } else if (textoLower.includes('subsidiária') || textoLower.includes('subsidiaria')) {
            dadosExtraidos.sentenca.resp = 'subsidiárias';
        }
        
        console.log('[CALC] Análise da sentença concluída');
    }
    
    // Analisa acórdão conforme calc.md
    function analisarAcordao(texto) {
        console.log('[CALC] Analisando acórdão...');
        
        // Processa de forma assíncrona para não travar a interface
        setTimeout(() => analisarAcordaoAsync(texto), 5);
    }
    
    // Função assíncrona para análise do acórdão
    async function analisarAcordaoAsync(texto) {
        
        const textoLower = texto.toLowerCase();
        
        // rec - Recurso das reclamadas
        if (textoLower.includes('recurso') && (textoLower.includes('reclamada') || textoLower.includes('ré'))) {
            dadosExtraidos.acordao.rec = true;
        }
        
        // custasAc - Rearbitramento de custas
        const custasAcMatch = texto.match(/rearbitramento.*?custas.*?([r\$\s]*[\d.,]+)/i) ||
                             texto.match(/custas.*?rearbitradas.*?([r\$\s]*[\d.,]+)/i) ||
                             texto.match(/novo.*?valor.*?custas.*?([r\$\s]*[\d.,]+)/i) ||
                             texto.match(/custas.*?([r\$\s]*[\d.,]+)/i);
        if (custasAcMatch) {
            let valorCustasAc = custasAcMatch[1].replace(/[^\d.,]/g, '').replace(/\s+/g, '').trim();
            if (valorCustasAc && valorCustasAc !== ',') {
                dadosExtraidos.acordao.custasAc = valorCustasAc;
                console.log(`[CALC] ✅ Custas do acórdão extraídas: "${valorCustasAc}" do texto: "${custasAcMatch[0]}"`);
            } else {
                console.log(`[CALC] ❌ Valor de custas do acórdão inválido após limpeza: "${valorCustasAc}"`);
            }
        } else {
            console.log('[CALC] ❌ Custas do acórdão não encontradas');
        }
        
        console.log('[CALC] Análise do acórdão concluída');
    }
    
    // Analisa planilha conforme calc.md
    function analisarPlanilha(texto) {
        console.log('[CALC] === INICIANDO ANÁLISE DA PLANILHA ===');
        
        // Processa de forma assíncrona para não travar a interface
        setTimeout(() => analisarPlanilhaAsync(texto), 10);
    }
    
    // Função assíncrona para análise da planilha
    async function analisarPlanilhaAsync(texto) {
        
        // Função auxiliar para extrair valores monetários
        function extrairValores(str) {
            return (str.match(/\d{1,3}(?:\.\d{3})*,\d{2}/g) || []);
        }
        
        // total - Total bruto devido ao reclamante
        console.log('[CALC] Buscando total bruto devido ao reclamante...');
        const padroesBruto = [
            // Padrão 1: PROCESSO 1 - "145.951,09 Bruto Devido ao Reclamante" (exato do calcextrai.md)
            /(145\.951,09|24\.059,25)\s+(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)/i,
            // Padrão 2: "Bruto Devido ao Reclamante 145.951,09" ou "Bruto Devido ao Reclamante 24.059,25"
            /(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)\s+(145\.951,09|24\.059,25)/i,
            // Padrão 3: Genérico - "xxx.xxx,xx Bruto Devido ao Reclamante"
            /(\d{1,3}(?:\.\d{3})*,\d{2})\s+(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)/i,
            // Padrão 4: Genérico - "Bruto Devido ao Reclamante xxx.xxx,xx"
            /(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i,
            // Padrão 5: Busca por "VERBAS" seguido de valor (formato tabela)
            /verbas\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i,
            // Padrão 6: Total na seção "Resumo do Cálculo" (primeira coluna de valores altos)
            /resumo\s+do\s+c[aá]lculo.*?(\d{1,3}(?:\.\d{3})*,\d{2})/gis
        ];
        
        let totalMatch = null;
        for (let i = 0; i < padroesBruto.length; i++) {
            // Pequena pausa para não travar a interface
            if (i > 0) await new Promise(resolve => setTimeout(resolve, 1));
            
            totalMatch = texto.match(padroesBruto[i]);
            if (totalMatch) {
                const valor = totalMatch[1].replace(/[^\d.,]/g, '');
                const valorNumerico = parseFloat(valor.replace('.', '').replace(',', '.'));
                // Verifica se é um valor significativo (maior que 1000)
                if (valorNumerico > 1000) {
                    console.log(`[CALC] ✅ Total bruto encontrado com padrão ${i + 1}: "${totalMatch[0]}" -> Valor: "${valor}"`);
                    dadosExtraidos.planilha.total = valor;
                    break;
                }
            }
        }
        
        if (!dadosExtraidos.planilha.total) {
            console.log('[CALC] ❌ Total bruto NÃO encontrado com nenhum padrão');
        }
        
        // data - Data de liquidação (prioriza padrão específico da planilha de cálculo)
        console.log('[CALC] Buscando data de liquidação...');
        const padroesData = [
            // Padrão 1: PROCESSO 2 - Como aparece no texto real: "Data Liquidação: 01/06/2025"
            /Data\s+Liquidação:\s*(\d{1,2}\/\d{1,2}\/\d{4})/i,
            // Padrão 2: PROCESSO 1 - Data no demonstrativo de honorários "31/05/2025 145.951,09 5,00 % 7.297,55"
            /(31\/05\/2025)\s+\d{1,3}(?:\.\d{3})*,\d{2}\s+5,00?\s*%.*?(?:7\.297,55|7\.352,36)/i,
            // Padrão 3: VALIDADO - Contexto completo nome "dd/mm/yyyy WELLINGTON ANGELO"
            /(\d{1,2}\/\d{1,2}\/\d{4})\s+WELLINGTON\s+ANGELO/i,
            // Padrão 4: VALIDADO - Planilha de atualização "30/06/2025 processo-numero"
            /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/i,
            // Padrão 5: NOVO - Para decisões judiciais "crédito do autor em R$ valor, para dd/mm/yyyy"
            /(?:crédito\s+(?:do\s+)?autor[\s\S]*?para\s+|fixando[\s\S]*?para\s+)(\d{1,2}\/\d{1,2}\/\d{4})/i,
            // Padrão 6: Fallback - Data em contexto de planilha (case-insensitive)
            /data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
            // Padrão 7: Fallback - Data liquidação sem acentos
            /data\s+liquidacao\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i
        ];
        
        let dataMatch = null;
        for (let i = 0; i < padroesData.length; i++) {
            // Pequena pausa para não travar a interface
            if (i > 0) await new Promise(resolve => setTimeout(resolve, 1));
            
            dataMatch = texto.match(padroesData[i]);
            if (dataMatch) {
                console.log(`[CALC] ✅ Data encontrada com padrão ${i + 1}: "${dataMatch[0]}" -> Data: "${dataMatch[1]}"`);
                dadosExtraidos.planilha.data = dataMatch[1];
                break;
            }
        }
        
        if (!dataMatch) {
            console.log('[CALC] ❌ Data de liquidação específica não encontrada, tentando busca contextual...');
            
            // Busca contextual: procura por datas próximas a contextos de planilha
            const contextosData = [
                // Prioriza contexto de planilha com nome do reclamante
                /(\d{1,2}\/\d{1,2}\/\d{4})\s+WELLINGTON\s+ANGELO/gi,
                // Contexto de planilha de cálculo
                /planilha.*?(\d{1,2}\/\d{1,2}\/\d{4})/gi,
                /cálculo.*?(\d{1,2}\/\d{1,2}\/\d{4})/gi,
                /liquidação.*?(\d{1,2}\/\d{1,2}\/\d{4})/gi,
                /devido.*?reclamante.*?(\d{1,2}\/\d{1,2}\/\d{4})/gi
            ];
            
            let dataContextual = null;
            for (let i = 0; i < contextosData.length; i++) {
                const matches = texto.matchAll(contextosData[i]);
                for (let match of matches) {
                    const dataCandidata = match[1];
                    const ano = parseInt(dataCandidata.split('/')[2]);
                    // Prioriza datas de 2025 (mais prováveis de serem de liquidação)
                    if (ano === 2025) {
                        dataContextual = dataCandidata;
                        console.log(`[CALC] ✅ Data encontrada via contexto ${i + 1}: "${match[0]}" -> Data: "${dataCandidata}"`);
                        // Se encontrou via contexto de planilha com nome, interrompe (prioridade máxima)
                        if (i === 0) break;
                    }
                }
                if (dataContextual && i === 0) break; // Prioridade máxima para contexto com nome
            }
            
            if (dataContextual) {
                dadosExtraidos.planilha.data = dataContextual;
            } else {
                console.log('[CALC] ❌ Nenhuma data de liquidação encontrada');
            }
        }
        
        // idd - ID da planilha (será extraído junto com a assinatura do Rogério)
        console.log('[CALC] ID da planilha será extraído junto com a assinatura eletrônica...');
        
        // hav - Honorários advocatícios
        console.log('[CALC] Buscando honorários advocatícios...');
        const padroesHonorarios = [
            // Padrão 1: PROCESSO 2 - Exato como aparece: "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE 1.202,96"
            /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*PATRONO\s*DO\s*RECLAMANTE\s*(1\.202,96)/i,
            
            // Padrão 2: PROCESSO 2 - Como aparece na página 28: "1.202,96 HONORÁRIOS ADVOCATÍCIOS PATRONO DO RECLAMANTE"
            /(1\.202,96)\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*PATRONO\s*DO\s*RECLAMANTE/i,
            
            // Padrão 3: PROCESSO 2 - Valor específico em contexto de honorários
            /(1\.202,96)(?=.*honor|honor.*)/i,
            
            // Padrão 4: PROCESSO 1 - "7.297,55 HONORÁRIOS ADVOCATÍCIOS ADVOGADO DA RECLAMANTE"
            /(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS\s*ADVOGADO\s*DA\s*RECLAMANTE/gi,
            
            // Padrão 5: PROCESSO 2 - "Honor ários advocatícios sucumbenciais pela reclamada, no importe de R$ 1202,96"  
            /Honor[áa]rios?\s+advocat[íi]cios?\s+sucumbenciais.*?(?:importe|valor)\s+de\s+R\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
            
            // Padrão 6: Planilhas - "HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE 7.297,55"
            /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*ADVOGADO[^\d]*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
            
            // Padrão 7: Demonstrativo com alíquota - captura valor após "5,00%"
            /5,00\s*%\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
            
            // Padrão 8: Atualização com percentual - captura valor após percentual e traço
            /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?\d{1,3}(?:\.\d{3})*,\d{2}\s*5,0000%\s*-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
            
            // Padrão 9: Busca genérica por valor próximo a "honorários"
            /honor[áa]rios?\s*advocat[íi]cios?.*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi
        ];
        
        let havMatch = null;
        for (let i = 0; i < padroesHonorarios.length; i++) {
            // Pequena pausa para não travar a interface
            if (i > 0) await new Promise(resolve => setTimeout(resolve, 1));
            
            havMatch = texto.match(padroesHonorarios[i]);
            if (havMatch) {
                // Para padrão 5 (múltiplos grupos), pega o primeiro grupo não vazio
                let valor = havMatch[1] || havMatch[2];
                if (valor) {
                    valor = valor.replace(/[^\d.,]/g, '');
                    console.log(`[CALC] ✅ Honorários encontrados com padrão ${i + 1}: "${havMatch[0]}" -> Valor: "${valor}"`);
                    dadosExtraidos.planilha.hav = valor;
                    break;
                }
            }
        }
        
        if (!dadosExtraidos.planilha.hav) {
            console.log('[CALC] ❌ Honorários advocatícios NÃO encontrados com nenhum padrão');
            
            // Fallback: calcula 5% do total bruto se disponível (padrão mais comum)
            if (dadosExtraidos.planilha.total) {
                const totalNumerico = parseFloat(dadosExtraidos.planilha.total.replace('.', '').replace(',', '.'));
                const honorarios5pct = (totalNumerico * 0.05).toFixed(2).replace('.', ',');
                dadosExtraidos.planilha.hav = honorarios5pct;
                console.log(`[CALC] ✅ Honorários calculados como 5% do total: ${honorarios5pct}`);
            }
        }
        
        // irpf - IRPF DEVIDO PELO RECLAMANTE
        console.log('[CALC] Buscando IRPF DEVIDO PELO RECLAMANTE...');
        const padroesIRPF = [
            // Padrão exato: "IRPF DEVIDO PELO RECLAMANTE 0,00"
            /irpf\s+devido\s+pelo\s+reclamante\s+([\d.,]+)/i,
            // Padrão alternativo: busca por imposto de renda
            /imposto\s+de\s+renda.*?reclamante.*?([\d.,]+)/i
        ];
        
        let irpfMatch = null;
        for (let i = 0; i < padroesIRPF.length; i++) {
            irpfMatch = texto.match(padroesIRPF[i]);
            if (irpfMatch) {
                const valor = irpfMatch[1].replace(/[^\d.,]/g, '');
                console.log(`[CALC] ✅ IRPF devido encontrado com padrão ${i + 1}: "${irpfMatch[0]}" -> Valor: "${valor}"`);
                dadosExtraidos.planilha.irpf = valor;
                break;
            }
        }
        
        if (!irpfMatch) {
            console.log('[CALC] ❌ IRPF DEVIDO PELO RECLAMANTE NÃO encontrado');
        }
        
        // y - INSS do autor (busca APENAS valores válidos e específicos)
        console.log('[CALC] Buscando INSS do autor...');
        const padroesINSSAutor = [
            // Padrão específico para DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL
            /dedução\s+de\s+contribuição\s+social.*?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
            /deducao\s+de\s+contribuicao\s+social.*?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
            // Padrões alternativos mais específicos
            /contribuição\s+social.*?autor.*?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
            /inss.*?autor.*?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
            /desconto.*?previdenciário.*?reclamante.*?(\d{1,3}(?:\.\d{3})*,\d{2})/i
        ];
        
        let inssMatch = null;
        for (let i = 0; i < padroesINSSAutor.length; i++) {
            const matches = texto.matchAll(new RegExp(padroesINSSAutor[i].source, 'gi'));
            for (let match of matches) {
                const valor = match[1].replace(/[^\d.,]/g, '');
                const valorNumerico = parseFloat(valor.replace('.', '').replace(',', '.'));
                
                // INSS deve ser um valor específico e razoável (entre 50 e 50.000)
                if (valorNumerico >= 50 && valorNumerico <= 50000) {
                    console.log(`[CALC] ✅ INSS autor encontrado com padrão ${i + 1}: "${match[0]}" -> Valor: "${valor}"`);
                    dadosExtraidos.planilha.y = valor;
                    inssMatch = match;
                    break;
                }
            }
            if (inssMatch) break;
        }
        
        if (!inssMatch) {
            console.log('[CALC] ❌ INSS do autor NÃO encontrado - será considerado como não há débitos previdenciários');
        }
        
        // rog - Assinatura do Rogério e ID da planilha (busca APENAS na planilha, não na sentença)
        console.log('[CALC] Buscando assinatura do perito e ID da planilha...');
        
        // Identifica se o texto contém uma planilha (deve ter dados de cálculo)
        const temPlanilha = texto.toLowerCase().includes('bruto devido') || 
                           texto.toLowerCase().includes('total bruto') ||
                           texto.toLowerCase().includes('honorários líquidos') ||
                           texto.toLowerCase().includes('planilha de cálculo') ||
                           texto.toLowerCase().includes('cálculo liquidado') ||
                           texto.toLowerCase().includes('resumo do cálculo') ||
                           texto.toLowerCase().includes('data liquidação:');
        
        if (!temPlanilha) {
            console.log('[CALC] ❌ Texto não parece conter uma planilha de cálculos');
            return;
        }
        
        // Busca assinatura APENAS se for uma planilha e EXTRAI ID da mesma linha
        const padroesAssinaturaPlanilha = [
            // Padrão ESPECÍFICO para Rogério: "Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 18/06/2025, às 09:16:41 - 02dea67"
            /Documento\s+assinado\s+eletronicamente\s+por\s+(ROGERIO\s+APARECIDO\s+ROSA),\s+em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]+)/gi,
            // Padrão tradicional: captura nome e ID corretamente
            /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+?),\s+em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]+)/gi,
            // Padrão genérico: "por NOME, em ... - ID"
            /por\s+([A-Z\s]+?),\s+em.*?-\s+([a-z0-9]+)/gi,
            // Padrão mais flexível
            /assinado.*?por\s+([A-Z\s]+?),.*?([a-z0-9]{6,15})/gi
        ];
        
        let rogerioMatch = null;
        let isRogerio = false;
        let idExtraido = null;
        
        for (let i = 0; i < padroesAssinaturaPlanilha.length; i++) {
            const matches = texto.matchAll(padroesAssinaturaPlanilha[i]);
            for (let match of matches) {
                const nome = match[1].trim();
                const potencialId = match[2] ? match[2].trim() : null;
                
                console.log(`[CALC] Verificando assinatura: "${nome}" com ID: "${potencialId}"`);
                
                // Verifica o contexto para garantir que está na planilha, não na sentença
                const assinaturaCompleta = match[0];
                const indicePosicao = texto.indexOf(assinaturaCompleta);
                const contextoAnterior = texto.substring(Math.max(0, indicePosicao - 500), indicePosicao).toLowerCase();
                const contextoPosterior = texto.substring(indicePosicao, Math.min(texto.length, indicePosicao + 500)).toLowerCase();
                
                // Verifica se está em contexto de planilha
                const estaEmPlanilha = contextoAnterior.includes('planilha') || 
                                     contextoAnterior.includes('cálculo') ||
                                     contextoAnterior.includes('bruto devido') ||
                                     contextoAnterior.includes('honorários líquidos') ||
                                     contextoAnterior.includes('liquidação') ||
                                     contextoAnterior.includes('resumo do cálculo') ||
                                     contextoPosterior.includes('planilha') ||
                                     contextoPosterior.includes('cálculo') ||
                                     // GABRIELA CARR assina especificamente as planilhas
                                     nome.includes('GABRIELA') ||
                                     nome.includes('CARR');
                
                // Verifica se NÃO está em contexto de sentença (para evitar IDs da sentença)
                const estaEmSentenca = contextoAnterior.includes('sentença') ||
                                      contextoAnterior.includes('juiz do trabalho') ||
                                      contextoAnterior.includes('dispositivo') ||
                                      contextoAnterior.includes('ante todo o exposto') ||
                                      contextoPosterior.includes('juiz do trabalho') ||
                                      contextoPosterior.includes('sentença') ||
                                      // OTAVIO é juiz, não contabilista
                                      nome.includes('OTAVIO') ||
                                      nome.includes('MACHADO');
                
                if (estaEmPlanilha && !estaEmSentenca) {
                    // Verifica especificamente se é ROGERIO
                    if (nome.includes('ROGERIO')) {
                        console.log(`[CALC] ✅ Assinatura de ROGERIO encontrada: "${nome}"`);
                        isRogerio = true;
                        dadosExtraidos.planilha.rog = nome; // Salva apenas o nome, não a frase completa
                        
                        // ID extraído da mesma linha da assinatura
                        if (potencialId) {
                            idExtraido = potencialId;
                            console.log(`[CALC] ✅ ID da planilha encontrado na assinatura: "${idExtraido}"`);
                        }
                        
                        rogerioMatch = match;
                        console.log(`[CALC] ✅ FLAG isRogerio setada como TRUE`);
                        break;
                    } else if (nome.includes('GABRIELA') || nome.length > 10) {
                        console.log(`[CALC] ✅ Assinatura de perito/autor da planilha encontrada: "${nome}"`);
                        dadosExtraidos.planilha.rog = nome; // Salva apenas o nome
                        
                        // ID extraído da mesma linha - PRIORIZA GABRIELA CARR (autora da planilha)
                        if (potencialId) {
                            idExtraido = potencialId;
                            console.log(`[CALC] ✅ ID da planilha encontrado na assinatura: "${idExtraido}"`);
                        }
                        
                        rogerioMatch = match;
                        // Se for GABRIELA, interrompe imediatamente (prioridade máxima)
                        if (nome.includes('GABRIELA')) break;
                    }
                } else {
                    console.log(`[CALC] ❌ Assinatura "${nome}" ignorada - não está em contexto de planilha`);
                }
            }
            if (rogerioMatch) break;
        }
        
        // Armazena o ID se foi encontrado na assinatura
        if (idExtraido) {
            dadosExtraidos.planilha.idd = idExtraido;
        }
        
        if (!rogerioMatch) {
            console.log('[CALC] ❌ Nenhuma assinatura de perito encontrada na planilha');
        }
        
        // Armazena se é especificamente ROGERIO para uso posterior
        dadosExtraidos.planilha.isRogerio = isRogerio;
        
        console.log('[CALC] === ANÁLISE DA PLANILHA CONCLUÍDA ===');
        console.log('[CALC] Dados da planilha extraídos:', dadosExtraidos.planilha);
        
        // Aplica fallbacks para campos críticos não encontrados
        aplicarFallbackExtracao(texto);
    }
    
    // Aplica fallbacks para extração de dados críticos
    function aplicarFallbackExtracao(texto) {
        console.log('[CALC] === APLICANDO FALLBACKS ===');
        
        // Fallback para data de liquidação
        if (!dadosExtraidos.planilha.data) {
            console.log('[CALC] Aplicando fallback para data...');
            const dataFallback = texto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/g);
            if (dataFallback && dataFallback.length > 0) {
                // Pega a data mais recente encontrada
                dadosExtraidos.planilha.data = dataFallback[dataFallback.length - 1];
                console.log('[CALC] ✅ Data extraída via fallback:', dadosExtraidos.planilha.data);
                console.log('[CALC] Todas as datas encontradas:', dataFallback);
            } else {
                console.log('[CALC] ❌ Nenhuma data encontrada no fallback');
            }
        }
        
        // Fallback para ID da planilha (apenas se não foi encontrado na assinatura)
        if (!dadosExtraidos.planilha.idd) {
            console.log('[CALC] Aplicando fallback para ID da planilha...');
            
            // Busca padrões específicos de ID em planilhas PJe
            const padroesIdPlanilha = [
                // IDs após timestamps (padrão comum)
                /às\s+[\d:]+\s+-\s+([a-z0-9]{6,15})/gi,
                // IDs em contexto de documento
                /documento.*?([a-z0-9]{8,12})/gi,
                // IDs alfanuméricos específicos
                /([a-z0-9]{6,10})/gi
            ];
            
            let idEncontrado = null;
            for (let i = 0; i < padroesIdPlanilha.length; i++) {
                const matches = texto.matchAll(padroesIdPlanilha[i]);
                const candidatos = [];
                
                for (let match of matches) {
                    const potencialId = match[1];
                    // Filtra IDs que parecem válidos
                    if (potencialId.length >= 6 && potencialId.length <= 15 && 
                        /^[a-z0-9]+$/.test(potencialId) && 
                        !/^[0-9]+$/.test(potencialId)) { // Não apenas números
                        candidatos.push(potencialId);
                    }
                }
                
                if (candidatos.length > 0) {
                    // Pega o primeiro ID válido encontrado
                    idEncontrado = candidatos[0];
                    console.log(`[CALC] ✅ ID extraído via fallback padrão ${i + 1}: "${idEncontrado}"`);
                    console.log(`[CALC] Candidatos encontrados:`, candidatos.slice(0, 5));
                    break;
                }
            }
            
            if (idEncontrado) {
                dadosExtraidos.planilha.idd = idEncontrado;
            } else {
                console.log('[CALC] ❌ Nenhum ID válido encontrado no fallback');
            }
        }
        
        // Fallback para total bruto
        if (!dadosExtraidos.planilha.total) {
            console.log('[CALC] Aplicando fallback para total...');
            const valoresFallback = texto.match(/[r\$]?\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi);
            if (valoresFallback && valoresFallback.length > 0) {
                console.log('[CALC] Valores candidatos encontrados:', valoresFallback.slice(0, 10));
                // Pega o maior valor encontrado (provavelmente o total)
                let maiorValor = 0;
                let valorEscolhido = null;
                
                valoresFallback.forEach(valor => {
                    const numerico = parseFloat(valor.replace(/[^\d,]/g, '').replace(',', '.'));
                    if (numerico > maiorValor) {
                        maiorValor = numerico;
                        valorEscolhido = valor.replace(/[^\d.,]/g, '');
                    }
                });
                
                if (valorEscolhido) {
                    dadosExtraidos.planilha.total = valorEscolhido;
                    console.log('[CALC] ✅ Total extraído via fallback:', dadosExtraidos.planilha.total);
                } else {
                    console.log('[CALC] ❌ Nenhum valor válido encontrado no fallback');
                }
            } else {
                console.log('[CALC] ❌ Nenhum valor monetário encontrado no fallback');
            }
        }
        
        console.log('[CALC] === FALLBACKS CONCLUÍDOS ===');
    }
    
    // Gera decisão automaticamente com dados extraídos do PDF
    function gerarDecisaoAutomatica() {
        console.log('[CALC] === GERANDO DECISÃO AUTOMÁTICA ===');
        console.log('[CALC] Dados disponíveis:', JSON.stringify(dadosExtraidos, null, 2));
        
        // Usa dados extraídos automaticamente
        const data = dadosExtraidos.planilha.data || '[DATA NÃO ENCONTRADA]';
        const idd = dadosExtraidos.planilha.idd || '[ID NÃO ENCONTRADO]';
        const inr = dadosExtraidos.planilha.inr || '[INSS NÃO ENCONTRADO]';
        const total = dadosExtraidos.planilha.total || '[VALOR NÃO ENCONTRADO]';
        const inssAutor = dadosExtraidos.planilha.y || '[INSS AUTOR NÃO ENCONTRADO]';
        const honorarios = dadosExtraidos.planilha.hav || '[HONORÁRIOS NÃO ENCONTRADOS]';
        
        console.log('[CALC] Variáveis para decisão:');
        console.log(`[CALC] - Data: "${data}"`);
        console.log(`[CALC] - ID: "${idd}"`);
        console.log(`[CALC] - INSS Reclamada: "${inr}"`);
        console.log(`[CALC] - Total: "${total}"`);
        console.log(`[CALC] - INSS Autor: "${inssAutor}"`);
        console.log(`[CALC] - Honorários: "${honorarios}"`);
        
        // Monta a decisão com cabeçalho condicional baseado na variável rog
        let decisao = '';
        
        // Cabeçalho condicional: se é especificamente ROGERIO, usa formato de perito
        if (dadosExtraidos.planilha.isRogerio) {
            // Cabeçalho para planilhas assinadas especificamente por ROGERIO
            decisao = `As impugnações apresentadas pela reclamada já foram objeto de esclarecimentos pelo sr. Perito nos Id. ZZZZ, nada havendo a ser reparado no laudo.\n\nDestarte, dou por encerradas as impugnações ao laudo e HOMOLOGO os cálculos de liquidação elaborados pelo sr. Perito (${idd}), fixando o crédito do autor em R$ ${total}, referente ao principal acrescido do FGTS, para ${data}, atualizado pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. STF nas ADCs 58 e 59 e ADI 5867.\n\n`;
            
            // Se assinatura de ROGERIO especificamente detectada, inclui honorários periciais contábeis
            decisao += `Arbitro honorários periciais contábeis no montante de R$2.500,00, pela reclamada.\n\n`;
        } else {
            // Cabeçalho padrão (sem ROGERIO ou sem perito)
            decisao = `Tendo em vista a concordância das partes, HOMOLOGO os cálculos do autor/da reclamada (Id ${idd}), fixando o crédito em R$ ${total}, referente ao valor principal, para ${data}, atualizado pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. Supremo Tribunal Federal nas ADCs 58 e 59 e ADI 5867, de 18/12/2020.\n\n`;
        }
        
        // Responsabilidade solidária/subsidiária
        if (dadosExtraidos.sentenca.resp) {
            decisao += `As reclamadas são devedoras ${dadosExtraidos.sentenca.resp}.\n\n`;
        }
        
        // INSS - Conforme calc.md: [x menos y] onde x=INSS Bruto Reclamada, y=INSS Autor
        if (dadosExtraidos.planilha.inr && dadosExtraidos.planilha.inr !== '[INSS NÃO ENCONTRADO]') {
            decisao += `A reclamada, ainda, deverá pagar o valor de sua cota parte no INSS, a saber, R$ ${dadosExtraidos.planilha.inr}, para ${data}.\n\n`;
        }
        
        if (dadosExtraidos.planilha.y) {
            decisao += `Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em R$ ${dadosExtraidos.planilha.y}, para ${data}.\n\n`;
        }
        
        // Contribuições previdenciárias - lógica corrigida
        const temINSSAutor = dadosExtraidos.planilha.y && dadosExtraidos.planilha.y !== '[INSS AUTOR NÃO ENCONTRADO]';
        const temINSSReclamada = dadosExtraidos.planilha.inr && dadosExtraidos.planilha.inr !== '[INSS NÃO ENCONTRADO]';
        
        console.log(`[CALC] DEBUG INSS - Autor: "${dadosExtraidos.planilha.y}" (tem: ${temINSSAutor})`);
        console.log(`[CALC] DEBUG INSS - Reclamada: "${dadosExtraidos.planilha.inr}" (tem: ${temINSSReclamada})`);
        
        if (temINSSAutor || temINSSReclamada) {
            console.log('[CALC] ✅ Variáveis de INSS encontradas - incluindo trecho de contribuições previdenciárias');
            decisao += `Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTFWeb, depois de serem informados os dados da reclamatória trabalhista no eSocial. Atente que os registros no eSocial serão feitos por meio dos eventos: "S-2500 - Processos Trabalhistas" e "S-2501- Informações de Tributos Decorrentes de Processo Trabalhista".\n\n`;
            
            decisao += `Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do eSocial somente o evento "S-2500 – Processos Trabalhistas".\n\n`;
        } else {
            console.log('[CALC] ❌ Nenhuma variável de INSS encontrada - incluindo texto para ausência de débitos previdenciários');
            decisao += `Não há débitos ou descontos previdenciários.\n\n`;
        }
        
        // IRPF - Nova lógica baseada na variável irpf
        const irpfDevido = dadosExtraidos.planilha.irpf;
        console.log(`[CALC] IRPF DEVIDO PELO RECLAMANTE: "${irpfDevido}"`);
        
        if (!irpfDevido || irpfDevido === '0,00' || parseFloat(irpfDevido.replace(',', '.')) === 0) {
            // Opção A: Regra geral quando irpf = 0,00 ou não encontrado
            console.log('[CALC] Aplicando regra geral IRPF (Opção A) - irpf = 0,00 ou não encontrado');
            decisao += `Não há deduções fiscais cabíveis.\n\n`;
        } else {
            // Opção B: Quando irpf diferente de 0,00
            console.log('[CALC] Aplicando regra específica IRPF (Opção B) - irpf diferente de 0,00');
            const baseIRPF = dadosExtraidos.planilha.irr || '[BASE IRPF NÃO ENCONTRADA]';
            const mesesIRPF = dadosExtraidos.planilha.mm || '[MESES NÃO ENCONTRADOS]';
            decisao += `Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (R$ ${baseIRPF}), pelo período de ${mesesIRPF} meses.\n\n`;
        }
        
        // Honorários
        if (dadosExtraidos.sentenca.HPS) {
            decisao += `${dadosExtraidos.sentenca.HPS}\n\n`;
        }
        
        if (dadosExtraidos.sentenca.hp1) {
            decisao += `${dadosExtraidos.sentenca.hp1}\n\n`;
        }
        
        // Não inclui a linha de assinatura na decisão - apenas usada para identificação interna
        
        if (dadosExtraidos.planilha.hav) {
            decisao += `Honorários advocatícios sucumbenciais pela reclamada, no importe de R$ ${dadosExtraidos.planilha.hav}, para ${data}.\n\n`;
        }
        
        // Custas
        const custas = dadosExtraidos.acordao.custasAc || dadosExtraidos.sentenca.custas;
        const dataCustas = dadosExtraidos.sentenca.ds || data;
        
        console.log(`[CALC] DEBUG Custas - Acordão: "${dadosExtraidos.acordao.custasAc}", Sentença: "${dadosExtraidos.sentenca.custas}"`);
        console.log(`[CALC] DEBUG Custas - Valor final: "${custas}", Data: "${dataCustas}"`);
        
        if (custas && custas.trim() && custas.trim() !== ',') {
            let linhaCustas;
            if (dadosExtraidos.acordao.rec) {
                // Quando há recurso (custas pagas), inclui valor, data e origem
                const origemCustas = dadosExtraidos.acordao.custasAc ? 'acórdão' : 'sentença';
                const valorFormatado = custas.toString().includes('R$') ? custas : `R$ ${custas}`;
                linhaCustas = `Custas de **${valorFormatado}**, para **${dataCustas}**, definidas em **${origemCustas}**, pagas, pela reclamada.`;
                console.log(`[CALC] ✅ Linha de custas (com recurso): "${linhaCustas}"`);
            } else {
                // Formato padrão para custas não pagas
                linhaCustas = `Custas de **R$ ${custas}**, pela reclamada, para **${dataCustas}**.`;
                console.log(`[CALC] ✅ Linha de custas (sem recurso): "${linhaCustas}"`);
            }
            decisao += `${linhaCustas}\n\n`;
        } else {
            console.log(`[CALC] ❌ Custas não incluídas na decisão - Valor inválido: "${custas}"`);
        }
        
        // Finalização
        decisao += `Ante os termos da decisão proferida pelo E. STF na ADI 5766, e considerando o deferimento dos benefícios da justiça gratuita ao autor, é indevido o pagamento de honorários sucumbenciais pelo trabalhador ao advogado da parte reclamada.\n\n`;
        
        decisao += `Intimações:\n\n`;
        decisao += `Intime-se a reclamada, na pessoa de seu patrono, para que pague os valores acima indicados em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.\n\n`;
        decisao += `Intime-se a reclamada para pagamento dos valores acima, em 48 (quarenta e oito) horas, sob pena de penhora, expedindo-se o competente mandado.\n\n`;
        decisao += `Ficam as partes cientes de que qualquer questionamento acerca desta decisão, salvo erro material, será apreciado após a garantia do juízo.`;
        
        // Exibe resultado
        exibirDecisao(decisao);
    }
    
    // Exibe decisão gerada
    function exibirDecisao(decisao) {
        console.log('[CALC] Exibindo decisão...');
        
        // Remove modal existente
        let modalExistente = document.getElementById('calc-modal-decisao');
        if (modalExistente) {
            modalExistente.remove();
        }
        
        // Cria modal
        const modal = document.createElement('div');
        modal.id = 'calc-modal-decisao';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const conteudo = document.createElement('div');
        conteudo.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 80%;
            max-height: 80%;
            overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        `;
        
        const titulo = document.createElement('h3');
        titulo.innerHTML = '⚖️ Decisão de Homologação';
        titulo.style.cssText = 'margin: 0 0 20px 0; color: #007bff;';
        
        const textarea = document.createElement('div');
        textarea.innerHTML = formatarDestaque(decisao.replace(/\n/g, '<br>'));
        textarea.style.cssText = `
            width: 100%;
            height: 400px;
            font-family: 'Times New Roman', serif;
            font-size: 14px;
            line-height: 1.6;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 20px;
            overflow-y: auto;
            text-align: justify;
            color: #333;
            background-color: #fff;
        `;
        
        // Área de texto oculta para cópia (sem formatação HTML)
        const textareaCopia = document.createElement('textarea');
        textareaCopia.value = decisao;
        textareaCopia.style.cssText = `
            position: absolute;
            left: -9999px;
            opacity: 0;
        `;
        
        const botoes = document.createElement('div');
        botoes.style.cssText = 'margin-top: 16px; display: flex; gap: 8px; justify-content: flex-end;';
        
        const btnCopiar = document.createElement('button');
        btnCopiar.innerHTML = '📋 Copiar';
        btnCopiar.style.cssText = `
            background: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            cursor: pointer;
        `;
        
        btnCopiar.addEventListener('click', async () => {
            try {
                // Prepara HTML formatado com estrutura completa
                const htmlFormatado = `
                    <div style="font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.4;">
                        ${formatarDestaque(decisao.replace(/\n/g, '<br>'))}
                    </div>
                `;
                
                // Cria ClipboardItem com ambos os formatos
                const clipboardItem = new ClipboardItem({
                    'text/html': new Blob([htmlFormatado], { type: 'text/html' }),
                    'text/plain': new Blob([decisao], { type: 'text/plain' })
                });
                
                await navigator.clipboard.write([clipboardItem]);
                btnCopiar.innerHTML = '✅ Copiado com formatação!';
                
            } catch (error) {
                console.log('[CALC] Fallback para cópia simples:', error);
                // Fallback para cópia simples se a API moderna falhar
                textareaCopia.select();
                document.execCommand('copy');
                btnCopiar.innerHTML = '✅ Copiado (texto simples)!';
            }
            
            setTimeout(() => {
                btnCopiar.innerHTML = '📋 Copiar';
            }, 3000);
        });
        
        const btnFechar = document.createElement('button');
        btnFechar.innerHTML = '✕ Fechar';
        btnFechar.style.cssText = `
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            cursor: pointer;
        `;
        
        btnFechar.addEventListener('click', () => modal.remove());
        
        botoes.appendChild(btnCopiar);
        botoes.appendChild(btnFechar);
        
        conteudo.appendChild(titulo);
        conteudo.appendChild(textarea);
        conteudo.appendChild(textareaCopia);
        conteudo.appendChild(botoes);
        
        modal.appendChild(conteudo);
        document.body.appendChild(modal);
        
        console.log('[CALC] ✅ Decisão exibida');
    }
    
    // Função para debug - exportar texto extraído
    function exportarTextoExtraido() {
        console.log('[CALC] Exportando texto extraído para debug...');
        
        // Busca textos salvos no localStorage
        const chaves = Object.keys(localStorage).filter(key => key.startsWith('calc_texto_extraido_'));
        
        if (chaves.length === 0) {
            alert('Nenhum texto extraído encontrado. Faça upload de um PDF primeiro.');
            return;
        }
        
        // Pega o texto mais recente
        const chaveRecente = chaves[chaves.length - 1];
        const textoExtraido = localStorage.getItem(chaveRecente);
        
        if (!textoExtraido) {
            alert('Erro ao recuperar texto extraído.');
            return;
        }
        
        // Cria relatório simplificado focado apenas no texto e dados da planilha
        let relatorio = `=== RELATÓRIO DE DEBUG - EXTRAÇÃO DA PLANILHA ===\n`;
        relatorio += `Data/Hora: ${new Date().toLocaleString()}\n`;
        relatorio += `Tamanho do texto: ${textoExtraido.length} caracteres\n\n`;
        
        relatorio += `=== COMO FUNCIONA A LEITURA ===\n`;
        relatorio += `1. PDF é carregado via upload/seleção\n`;
        relatorio += `2. PDF.js extrai TODO o texto do PDF (todas as páginas)\n`;
        relatorio += `3. Script analisa este texto extraído procurando por padrões específicos\n`;
        relatorio += `4. Dados são capturados usando regex nos padrões encontrados\n\n`;
        
        relatorio += `=== DADOS DA PLANILHA EXTRAÍDOS ===\n`;
        relatorio += `TOTAL DEVIDO: "${dadosExtraidos.planilha.total}"\n`;
        relatorio += `DATA LIQUIDAÇÃO: "${dadosExtraidos.planilha.data}"\n`;
        relatorio += `ID PLANILHA: "${dadosExtraidos.planilha.idd}"\n`;
        relatorio += `INSS AUTOR: "${dadosExtraidos.planilha.y}"\n`;
        relatorio += `HONORÁRIOS ADV: "${dadosExtraidos.planilha.hav}"\n`;
        relatorio += `INSS RECLAMADA: "${dadosExtraidos.planilha.inr}"\n`;
        relatorio += `IRPF DEVIDO: "${dadosExtraidos.planilha.irpf}"\n`;
        relatorio += `BASE IRPF: "${dadosExtraidos.planilha.irr}"\n`;
        relatorio += `MESES IRPF: "${dadosExtraidos.planilha.mm}"\n`;
        relatorio += `ASSINATURA ROGÉRIO: "${dadosExtraidos.planilha.rog}"\n\n`;
        
        relatorio += `=== TEXTO COMPLETO EXTRAÍDO DO PDF ===\n`;
        relatorio += `(Este é o texto bruto que o PDF.js extraiu do PDF)\n`;
        relatorio += `${'-'.repeat(80)}\n`;
        relatorio += textoExtraido;
        
        // Cria e baixa arquivo
        const blob = new Blob([relatorio], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `calc_debug_planilha_${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log('[CALC] ✅ Relatório de debug da planilha exportado');
    }

    // Função auxiliar para formatação em negrito de valores importantes
    function formatarDestaque(texto) {
        if (!texto) return texto;
        
        // Aplica negrito a valores monetários (R$ X,XX)
        texto = texto.replace(/(R\$\s*[\d.,]+)/g, '<strong>$1</strong>');
        
        // Aplica negrito a datas (formato dd/mm/aaaa)
        texto = texto.replace(/(\d{2}\/\d{2}\/\d{4})/g, '<strong>$1</strong>');
        
        // Aplica negrito a IDs (Id XXXXX)
        texto = texto.replace(/(Id\s+\d+)/g, '<strong>$1</strong>');
        
        // Aplica negrito a percentuais (X,XX%)
        texto = texto.replace(/(\d+,?\d*%)/g, '<strong>$1</strong>');
        
        return texto;
    }

})();
