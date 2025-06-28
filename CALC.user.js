// ==UserScript==
// @name         CALC - Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Análise automática de sentenças e acórdãos para homologação de cálculos trabalhistas - TRT2 Zona Sul SP
// @author       PjePlus
// @match        *://pje.trt2.jus.br/*/detalhe*
// @match        *://pje.trt2.jus.br/primeirograu/Processo/ConsultaProcesso/Detalhe/list.seam*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('[CALC] Script iniciado');
    
    // Detecta qual página está carregada
    const urlAtual = window.location.href;
    const isPaginaDetalhe = urlAtual.includes('/detalhe');
    const isPaginaDownload = urlAtual.includes('/ConsultaProcesso/Detalhe/list.seam');
    
    console.log('[CALC] URL:', urlAtual);
    console.log('[CALC] Página detalhe:', isPaginaDetalhe);
    console.log('[CALC] Página download:', isPaginaDownload);
    
    if (!isPaginaDetalhe && !isPaginaDownload) {
        console.log('[CALC] Script não aplicável para esta página');
        return;
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
            rog: null,      // Assinatura eletrônica de ROGERIO APARECIDO ROSA
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
    
    // Se for página de download, executa automação
    if (isPaginaDownload) {
        executarAutomacaoDownload();
        return;
    }
    
    // Se for página de detalhe, carrega interface
    if (isPaginaDetalhe) {
        inicializarInterface();
        return;
    }
    
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
        statusExtracao.innerHTML = '✨ Seleciona automaticamente sentenças/acórdãos.<br/>Você ainda pode selecionar outros documentos manualmente.';
        
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
    
    // Função para seleção automática de sentenças e acórdãos (sem gerar PDF)
    function extrairDocumentosAutomaticamente() {
        console.log('[CALC] Extraindo documentos automaticamente...');
        
        const statusEl = document.getElementById('calc-status-extracao');
        if (statusEl) {
            statusEl.textContent = '⏳ Extraindo documentos...';
            statusEl.style.color = '#ffc107';
        }
        
        // Extrai ID da URL atual
        const urlAtual = window.location.pathname;
        const match = urlAtual.match(/\/processo\/(\d+)\/detalhe/);
        
        if (!match) {
            console.error('[CALC] Não foi possível extrair ID da URL:', urlAtual);
            if (statusEl) {
                statusEl.textContent = '❌ Erro: ID do processo não encontrado';
                statusEl.style.color = '#dc3545';
            }
            return;
        }
        
        const processoId = match[1];
        console.log('[CALC] ID do processo extraído:', processoId);
        
        // Define instrução de automação no localStorage
        localStorage.setItem('calc_automate_download', 'true');
        localStorage.setItem('calc_process_id', processoId);
        
        // Monta URL da nova janela
        const novaUrl = `https://pje.trt2.jus.br/primeirograu/Processo/ConsultaProcesso/Detalhe/list.seam?id=${processoId}`;
        console.log('[CALC] Abrindo nova janela:', novaUrl);
        
        // Abre nova janela
        const novaJanela = window.open(novaUrl, '_blank');
        
        // Monitora status do PDF
        const intervalo = setInterval(() => {
            const status = localStorage.getItem('calc_pdf_status');
            
            if (status === 'ready_for_manual') {
                console.log('[CALC] ✅ Sentenças/acórdãos selecionados automaticamente!');
                localStorage.removeItem('calc_pdf_status');
                clearInterval(intervalo);
                
                if (statusEl) {
                    statusEl.textContent = '✅ Sentenças/acórdãos selecionados! Selecione outros documentos manualmente e gere o PDF.';
                    statusEl.style.color = '#28a745';
                }
            } else if (status === 'error') {
                console.error('[CALC] ❌ Erro na seleção dos documentos');
                localStorage.removeItem('calc_pdf_status');
                clearInterval(intervalo);
                
                if (statusEl) {
                    statusEl.textContent = '❌ Erro na seleção dos documentos';
                    statusEl.style.color = '#dc3545';
                }
            }
        }, 1000);
        
        // Para de monitorar após 30 segundos
        setTimeout(() => {
            clearInterval(intervalo);
            if (statusEl && statusEl.textContent.includes('⏳')) {
                statusEl.textContent = '⚠️ Timeout na extração';
                statusEl.style.color = '#ffc107';
            }
        }, 30000);
    }
    
    // Função para automação na página de download
    function executarAutomacaoDownload() {
        console.log('[CALC] 🤖 Executando automação na página de download...');
        
        // Verifica se há instrução para executar automação
        const shouldAutomate = localStorage.getItem('calc_automate_download');
        if (!shouldAutomate) {
            console.log('[CALC] Nenhuma instrução de automação encontrada');
            return;
        }
        
        // Remove a instrução
        localStorage.removeItem('calc_automate_download');
        
        // Aguarda carregar e executa as ações
        setTimeout(() => {
            executarAcoesAutomaticas();
        }, 2000);
    }
    
    // Executa ações automáticas na página de download
    function executarAcoesAutomaticas() {
        try {
            console.log('[CALC] Executando ações automáticas...');
            
            // 1. Clica no ícone PDF
            const iconePdf = document.querySelector('img[src="/primeirograu/img/cp/pdf.png"]');
            if (iconePdf) {
                console.log('[CALC] Clicando no ícone PDF...');
                iconePdf.click();
                
                // 2. Aguarda e executa seleção de documentos
                setTimeout(() => {
                    selecionarSentencasEAcordaos();
                }, 3000);
                
            } else {
                console.error('[CALC] Ícone PDF não encontrado');
                localStorage.setItem('calc_pdf_status', 'error');
            }
            
        } catch (error) {
            console.error('[CALC] Erro ao executar ações automáticas:', error);
            localStorage.setItem('calc_pdf_status', 'error');
        }
    }
    
    // Seleciona sentenças e acórdãos (e permite seleção adicional manual)
    function selecionarSentencasEAcordaos() {
        try {
            console.log('[CALC] Selecionando sentenças e acórdãos...');
            
            // 1. Primeiro desmarcar todos
            const checkboxTodos = document.getElementById('tbdownloadDocumentos:downloadDocumentosModal_checkAll');
            if (checkboxTodos && checkboxTodos.checked) {
                console.log('[CALC] Desmarcando todos os checkboxes...');
                checkboxTodos.click();
            }
            
            // 2. Aguarda e seleciona documentos específicos
            setTimeout(() => {
                const tabela = document.getElementById('tbdownloadDocumentos');
                if (!tabela) {
                    console.error('[CALC] Tabela de documentos não encontrada');
                    localStorage.setItem('calc_pdf_status', 'error');
                    return;
                }
                
                // Busca por linhas que contenham "Sentença" ou "Acórdão"
                const linhas = tabela.querySelectorAll('tbody tr');
                let documentosSelecionados = 0;
                
                linhas.forEach((linha, index) => {
                    const textoDocumento = linha.querySelector('.texto-doc');
                    if (textoDocumento) {
                        const texto = textoDocumento.textContent.trim().toLowerCase();
                        
                        // Verifica se é Sentença ou Acórdão
                        if (texto.includes('sentença') || 
                            texto.includes('acórdão') ||
                            texto.includes('acordao')) {
                            
                            const checkbox = linha.querySelector('input[type="checkbox"][name*="selecaoBox"]');
                            if (checkbox && !checkbox.checked) {
                                console.log(`[CALC] Selecionando: ${textoDocumento.textContent.trim()}`);
                                checkbox.click();
                                documentosSelecionados++;
                            }
                        }
                    }
                });
                
                console.log(`[CALC] ${documentosSelecionados} documentos selecionados automaticamente`);
                
                if (documentosSelecionados === 0) {
                    console.log('[CALC] ⚠️ Nenhuma sentença ou acórdão encontrado');
                    localStorage.setItem('calc_pdf_status', 'error');
                    return;
                }
                
                // 3. Marca como pronto para seleção manual adicional
                localStorage.setItem('calc_pdf_status', 'ready_for_manual');
                console.log('[CALC] ✅ Sentenças/acórdãos selecionados. Aguardando seleção manual de outros documentos...');
                
            }, 500);
            
        } catch (error) {
            console.error('[CALC] Erro ao selecionar documentos:', error);
            localStorage.setItem('calc_pdf_status', 'error');
        }
    }
    
    // Função removida - não será mais necessária pois não geramos PDF automaticamente
    
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
            
            for (let i = 1; i <= numPages; i++) {
                pdf.getPage(i).then(page => {
                    page.getTextContent().then(textContent => {
                        const textosPagina = textContent.items.map(item => item.str).join(' ');
                        textoCompleto += `\n=== PÁGINA ${i} ===\n` + textosPagina + '\n';
                        paginasProcessadas++;
                        
                        console.log(`[CALC] Página ${i} processada - ${textosPagina.length} caracteres`);
                        
                        if (paginasProcessadas === numPages) {
                            console.log(`[CALC] ✅ Texto completo extraído de ${nomeArquivo}:`);
                            console.log('='.repeat(50));
                            console.log(textoCompleto.substring(0, 1000) + '...');
                            console.log('='.repeat(50));
                            
                            // Salva texto extraído para debug
                            localStorage.setItem(`calc_texto_extraido_${Date.now()}`, textoCompleto);
                            
                            processarTextoExtraido(textoCompleto, nomeArquivo);
                        }
                    });
                });
            }
        }).catch(error => {
            console.error(`[CALC] Erro ao extrair texto do PDF ${nomeArquivo}:`, error);
        });
    }
    
    // Processa texto extraído e analisa
    function processarTextoExtraido(texto, nomeArquivo) {
        console.log(`[CALC] Processando texto extraído de ${nomeArquivo}...`);
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
                planilha: { rog: null, total: null, y: null, hav: null, mm: null, irr: null, irpf: null, data: null, idd: null, inr: null }
            };
        }
        
        // Analisa o texto conforme orientações do calc.md
        analisarSentenca(texto);
        analisarAcordao(texto);
        analisarPlanilha(texto);
        
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
        
        // custas - Valor das custas arbitradas (múltiplos padrões)
        const custasMatch = texto.match(/custas.*?arbitradas.*?([r\$\s]*[\d.,]+)/i) ||
                           texto.match(/custas.*?([r\$\s]*[\d.,]+)/i) ||
                           texto.match(/arbitro.*?custas.*?([r\$\s]*[\d.,]+)/i) ||
                           texto.match(/taxa.*?judiciária.*?([r\$\s]*[\d.,]+)/i) ||
                           texto.match(/custas.*?processo.*?([r\$\s]*[\d.,]+)/i);
        if (custasMatch) {
            dadosExtraidos.sentenca.custas = custasMatch[1].replace(/[^\d.,]/g, '');
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
        
        const textoLower = texto.toLowerCase();
        
        // rec - Recurso das reclamadas
        if (textoLower.includes('recurso') && (textoLower.includes('reclamada') || textoLower.includes('ré'))) {
            dadosExtraidos.acordao.rec = true;
        }
        
        // custasAc - Rearbitramento de custas
        const custasAcMatch = texto.match(/rearbitramento.*?custas.*?([r\$\s]*[\d.,]+)/i);
        if (custasAcMatch) {
            dadosExtraidos.acordao.custasAc = custasAcMatch[1];
        }
        
        console.log('[CALC] Análise do acórdão concluída');
    }
    
    // Analisa planilha conforme calc.md
    function analisarPlanilha(texto) {
        console.log('[CALC] === INICIANDO ANÁLISE DA PLANILHA ===');
        // --- INÍCIO REFINO vtotal (valor bruto devido ao reclamante) ---
        // Normaliza texto para busca robusta
        function normalizar(str) {
            return str
                .toLowerCase()
                .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove acentos
                .replace(/[^a-z0-9\s,.:]/gi, ' ')
                .replace(/\s+/g, ' ');
        }
        // Extrai todos os valores monetários de uma string
        function extrairValores(str) {
            return (str.match(/\d{1,3}(?:\.\d{3})*,\d{2}/g) || []);
        }
        // Busca linha alvo e contexto
        const textoNorm = normalizar(texto);
        const linhas = textoNorm.split(/\n|=== pagina \d+ ===/i);
        let idxLinhaBruto = -1;
        for (let i = 0; i < linhas.length; i++) {
            if (linhas[i].includes('bruto devido ao reclamante')) {
                idxLinhaBruto = i;
                break;
            }
        }
        let valorBruto = null;
        if (idxLinhaBruto !== -1) {
            // 1. Valor na mesma linha
            let valores = extrairValores(linhas[idxLinhaBruto]);
            if (valores.length > 0) {
                valorBruto = valores[valores.length - 1];
                console.log('[CALC] vtotal: valor na mesma linha:', valorBruto);
            }
            // 2. Linha abaixo
            if (!valorBruto && linhas[idxLinhaBruto + 1]) {
                valores = extrairValores(linhas[idxLinhaBruto + 1]);
                if (valores.length > 0) {
                    valorBruto = valores[valores.length - 1];
                    console.log('[CALC] vtotal: valor na linha abaixo:', valorBruto);
                }
            }
            // 3. Linha acima
            if (!valorBruto && linhas[idxLinhaBruto - 1]) {
                valores = extrairValores(linhas[idxLinhaBruto - 1]);
                if (valores.length > 0) {
                    valorBruto = valores[valores.length - 1];
                    console.log('[CALC] vtotal: valor na linha acima:', valorBruto);
                }
            }
            // 4. Maior valor em bloco de 3 linhas (acima, alvo, abaixo)
            if (!valorBruto) {
                let bloco = [];
                if (linhas[idxLinhaBruto - 1]) bloco.push(linhas[idxLinhaBruto - 1]);
                bloco.push(linhas[idxLinhaBruto]);
                if (linhas[idxLinhaBruto + 1]) bloco.push(linhas[idxLinhaBruto + 1]);
                valores = bloco.map(extrairValores).flat();
                if (valores.length > 0) {
                    valorBruto = valores.reduce((a, b) => parseFloat(a.replace('.', '').replace(',', '.')) > parseFloat(b.replace('.', '').replace(',', '.')) ? a : b);
                    console.log('[CALC] vtotal: maior valor no bloco:', valorBruto);
                }
            }
        }
        // Filtro para evitar valores de FGTS, INSS, etc (opcional: pode ser ajustado)
        if (valorBruto && parseFloat(valorBruto.replace('.', '').replace(',', '.')) < 1000) {
            console.log('[CALC] vtotal: valor muito baixo, descartando:', valorBruto);
            valorBruto = null;
        }
        // Fallback: maior valor do texto inteiro
        if (!valorBruto) {
            const todosValores = extrairValores(textoNorm);
            if (todosValores.length > 0) {
                valorBruto = todosValores.reduce((a, b) => parseFloat(a.replace('.', '').replace(',', '.')) > parseFloat(b.replace('.', '').replace(',', '.')) ? a : b);
                console.log('[CALC] vtotal: fallback maior valor do texto:', valorBruto);
            }
        }
        if (valorBruto) {
            dadosExtraidos.planilha.total = valorBruto;
        }
        // --- FIM REFINO vtotal ---
        // y - INSS do autor (APENAS padrões específicos determinados)
        console.log('[CALC] Buscando INSS do autor...');
        const padroesINSSAutor = [
            // Padrão específico do PJe-Calc Cidadão
            /dedução\s+de\s+contribuição\s+social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i
        ];
        
        let inssMatch = null;
        for (let i = 0; i < padroesINSSAutor.length; i++) {
            inssMatch = texto.match(padroesINSSAutor[i]);
            if (inssMatch) {
                console.log(`[CALC] ✅ INSS autor encontrado com padrão ${i + 1}: "${inssMatch[0]}" -> Valor: "${inssMatch[1]}"`);
                dadosExtraidos.planilha.y = inssMatch[1].replace(/[^\d.,]/g, '');
                break;
            }
        }
        if (!inssMatch) {
            console.log('[CALC] ❌ INSS do autor NÃO encontrado com nenhum padrão');
        }
        
        // hav - Honorários advocatícios (APENAS padrões específicos determinados)
        console.log('[CALC] Buscando honorários advocatícios...');
        const padroesHonorarios = [
            // Padrão específico do PJe-Calc Cidadão
            /honorários\s+líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i
        ];
        
        let havMatch = null;
        for (let i = 0; i < padroesHonorarios.length; i++) {
            havMatch = texto.match(padroesHonorarios[i]);
            if (havMatch) {
                console.log(`[CALC] ✅ Honorários encontrados com padrão ${i + 1}: "${havMatch[0]}" -> Valor: "${havMatch[1]}"`);
                dadosExtraidos.planilha.hav = havMatch[1].replace(/[^\d.,]/g, '');
                break;
            }
        }
        if (!havMatch) {
            console.log('[CALC] ❌ Honorários advocatícios NÃO encontrados com nenhum padrão');
            
            // Fallback: calcula 10% do total bruto se disponível
            if (dadosExtraidos.planilha.total) {
                const totalNumerico = parseFloat(dadosExtraidos.planilha.total.replace(',', '.'));
                const honorarios10pct = (totalNumerico * 0.1).toFixed(2).replace('.', ',');
                dadosExtraidos.planilha.hav = honorarios10pct;
                console.log(`[CALC] ✅ Honorários calculados como 10% do total: ${honorarios10pct}`);
            }
        }
        
        // data - Data de liquidação (01/04/2025 - deve buscar especificamente "Data Liquidação:")
        console.log('[CALC] Buscando data de liquidação...');
        
        // Busca específica por "Data Liquidação:" seguido da data
        const dataLiquidacaoMatch = texto.match(/data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i);
        if (dataLiquidacaoMatch) {
            console.log(`[CALC] ✅ Data encontrada com padrão específico: "${dataLiquidacaoMatch[0]}" -> Data: "${dataLiquidacaoMatch[1]}"`);
            dadosExtraidos.planilha.data = dataLiquidacaoMatch[1];
        } else {
            // Fallback: procura por "Data Liquidação" no texto e pega a data mais próxima
            const textoLower = texto.toLowerCase();
            const indiceLiquidacao = textoLower.indexOf('data liquidação');
            if (indiceLiquidacao !== -1) {
                // Pega um pedaço do texto ao redor de "Data Liquidação"
                const contexto = texto.substring(indiceLiquidacao - 50, indiceLiquidacao + 100);
                const dataContexto = contexto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
                if (dataContexto) {
                    console.log(`[CALC] ✅ Data encontrada no contexto de Data Liquidação: "${dataContexto[1]}"`);
                    dadosExtraidos.planilha.data = dataContexto[1];
                } else {
                    console.log('[CALC] ❌ Data não encontrada no contexto de Data Liquidação');
                }
            } else {
                console.log('[CALC] ❌ Texto "Data Liquidação" não encontrado');
            }
        }
        
        // idd - ID da planilha já extraído junto com assinatura do Rogério acima
        // (código removido pois já é tratado na seção anterior)
        
        // irpf - IRPF DEVIDO PELO RECLAMANTE (nova variável para determinar regra A ou B)
        console.log('[CALC] Buscando IRPF DEVIDO PELO RECLAMANTE...');
        const padroesIRPF = [
            // Padrão específico para IRPF devido pelo reclamante
            /irpf\s+devido\s+pelo\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i
        ];
        
        let irpfMatch = null;
        for (let i = 0; i < padroesIRPF.length; i++) {
            irpfMatch = texto.match(padroesIRPF[i]);
            if (irpfMatch) {
                console.log(`[CALC] ✅ IRPF devido encontrado com padrão ${i + 1}: "${irpfMatch[0]}" -> Valor: "${irpfMatch[1]}"`);
                dadosExtraidos.planilha.irpf = irpfMatch[1].replace(/[^\d.,]/g, '');
                break;
            }
        }
        if (!irpfMatch) {
            console.log('[CALC] ❌ IRPF DEVIDO PELO RECLAMANTE NÃO encontrado');
        }

        // inr - INSS Bruto da Reclamada (extrair para cálculo posterior)
        console.log('[CALC] Buscando INSS Bruto da Reclamada para cálculo...');
        const padroesINSSReclamada = [
            // Padrão específico para INSS Bruto da Reclamada na planilha
            /contribuição\s+social\s+sobre\s+salários\s+devidos\s*[:\s]*([r\$\s]*[\d.,]+)/i
        ];
        
        let inrBrutoMatch = null;
        for (let i = 0; i < padroesINSSReclamada.length; i++) {
            inrBrutoMatch = texto.match(padroesINSSReclamada[i]);
            if (inrBrutoMatch) {
                console.log(`[CALC] ✅ INSS Bruto Reclamada encontrado com padrão ${i + 1}: "${inrBrutoMatch[0]}" -> Valor: "${inrBrutoMatch[1]}"`);
                const inssBrutoReclamada = parseFloat(inrBrutoMatch[1].replace(/[^\d.,]/g, '').replace(',', '.'));
                
                // Calcula INR = INSS Bruto Reclamada - INSS Autor (conforme calc.md: [x menos y])
                if (dadosExtraidos.planilha.y) {
                    const inssAutor = parseFloat(dadosExtraidos.planilha.y.replace(',', '.'));
                    const inrCalculado = (inssBrutoReclamada - inssAutor).toFixed(2).replace('.', ',');
                    dadosExtraidos.planilha.inr = inrCalculado;
                    console.log(`[CALC] ✅ INR calculado: ${inssBrutoReclamada} - ${inssAutor} = ${inrCalculado}`);
                } else {
                    console.log('[CALC] ⚠️ INSS do autor não encontrado, não é possível calcular INR');
                }
                break;
            }
        }
        if (!inrBrutoMatch) {
            console.log('[CALC] ❌ INSS Bruto da Reclamada NÃO encontrado - INR não será calculado');
        }
        
        console.log('[CALC] === ANÁLISE DA PLANILHA CONCLUÍDA ===');
        console.log('[CALC] Dados da planilha extraídos:', dadosExtraidos.planilha);
        
        // Fallback para campos críticos não encontrados
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
        
        // Fallback para ID da planilha
        if (!dadosExtraidos.planilha.idd) {
            console.log('[CALC] Aplicando fallback para ID...');
            const idFallback = texto.match(/([A-Z0-9]{4,})/g);
            if (idFallback && idFallback.length > 0) {
                console.log('[CALC] IDs candidatos encontrados:', idFallback.slice(0, 10));
                // Procura por padrões que parecem IDs
                for (let potencialId of idFallback) {
                    if (potencialId.length >= 6 && potencialId.length <= 15) {
                        dadosExtraidos.planilha.idd = potencialId;
                        console.log('[CALC] ✅ ID extraído via fallback:', dadosExtraidos.planilha.idd);
                        break;
                    }
                }
            } else {
                console.log('[CALC] ❌ Nenhum ID encontrado no fallback');
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
        
        // Cabeçalho condicional: se rog é true (assinatura ROGERIO encontrada), usa formato alternativo
        if (dadosExtraidos.planilha.rog) {
            // Cabeçalho para documentos assinados por Rogério (formato correto)
            decisao = `As impugnações apresentadas pela reclamada já foram objeto de esclarecimentos pelo sr. Perito nos Id. ZZZZ, nada havendo a ser reparado no laudo.\n\nDestarte, dou por encerradas as impugnações ao laudo e HOMOLOGO os cálculos de liquidação elaborados pelo sr. Perito (${idd}), fixando o crédito do autor em R$ ${total}, referente ao principal acrescido do FGTS, para ${data}, atualizado pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. STF nas ADCs 58 e 59 e ADI 5867.\n\n`;
        } else {
            // Cabeçalho padrão
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
        
        // Contribuições previdenciárias - APENAS se encontrou variáveis de INSS
        const temINSSAutor = dadosExtraidos.planilha.y;
        const temINSSReclamada = dadosExtraidos.planilha.inr && dadosExtraidos.planilha.inr !== '[INSS NÃO ENCONTRADO]';
        
        if (temINSSAutor || temINSSReclamada) {
            console.log('[CALC] ✅ Variáveis de INSS encontradas - incluindo trecho de contribuições previdenciárias');
            decisao += `Os valores relativos às contribuições previdenciárias devidas em decorrência de decisões proferidas pela Justiça do Trabalho a partir de 1º de outubro de 2023, inclusive acordos homologados, devem ser recolhidos pelo(a) reclamado(a) por meio da DCTFWeb, depois de serem informados os dados da reclamatória trabalhista no eSocial. Atente que os registros no eSocial serão feitos por meio dos eventos: "S-2500 - Processos Trabalhistas" e "S-2501- Informações de Tributos Decorrentes de Processo Trabalhista".\n\n`;
            
            decisao += `Nos casos em que os recolhimentos forem efetuados diretamente pela Justiça do Trabalho, o reclamado deverá enviar através do eSocial somente o evento "S-2500 – Processos Trabalhistas".\n\n`;
        } else {
            console.log('[CALC] ❌ Nenhuma variável de INSS encontrada - EXCLUINDO trecho de contribuições previdenciárias');
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
        
        if (dadosExtraidos.planilha.rog) {
            decisao += `${dadosExtraidos.planilha.rog}\n\n`;
        }
        
        if (dadosExtraidos.planilha.hav) {
            decisao += `Honorários advocatícios sucumbenciais pela reclamada, no importe de R$ ${dadosExtraidos.planilha.hav}, para ${data}.\n\n`;
        }
        
        // Custas
        const custas = dadosExtraidos.acordao.custasAc || dadosExtraidos.sentenca.custas;
        const dataCustas = dadosExtraidos.sentenca.ds || data;
        const statusCustas = dadosExtraidos.acordao.rec ? 'Custas pagas' : `Custas de R$ ${custas}`;
        
        if (custas) {
            decisao += `${statusCustas}, pela reclamada, para ${dataCustas}.\n\n`;
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
        
        btnCopiar.addEventListener('click', () => {
            textareaCopia.select();
            document.execCommand('copy');
            btnCopiar.innerHTML = '✅ Copiado!';
            setTimeout(() => {
                btnCopiar.innerHTML = '📋 Copiar';
            }, 2000);
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
