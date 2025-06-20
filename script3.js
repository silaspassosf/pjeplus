// ==UserScript==
// @name         Triagem Petição Inicial Trabalhista - Relatório Completo - Zona Sul SP
// @namespace    http://tampermonkey.net/
// @version      3.0
// @description  Análise automática completa de petição inicial trabalhista conforme roteiro do TRT2 Zona Sul SP - Relatório detalhado de todas as regras
// @author       GPT-4
// @match        *://pje.trt2.jus.br/*/detalhe*
// @match        *://pje.trt2.jus.br/primeirograu/Processo/ConsultaProcesso/Detalhe/list.seam*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    // Detecta qual página está carregada
    const urlAtual = window.location.href;
    const isPaginaDetalhe = urlAtual.includes('/detalhe');
    const isPaginaDownload = urlAtual.includes('/ConsultaProcesso/Detalhe/list.seam');
    
    console.log('Script Triagem PJe V3 - URL:', urlAtual);
    console.log('Página detalhe:', isPaginaDetalhe);
    console.log('Página download:', isPaginaDownload);
      if (!isPaginaDetalhe && !isPaginaDownload) {
        console.log('Script não aplicável para esta página, saindo...');
        return;
    }
      // Variável global para armazenar texto extraído
    let textoExtraidoGlobal = '';
      // Array de análises para execução
    const analises = [
        {bloco: 1, nome: 'Competência Territorial (CEP)', func: analisarCompetenciaTerritorial},
        {bloco: 2, nome: 'Análise das Partes', func: analisarPartes},
        {bloco: 3, nome: 'Segredo de Justiça', func: analisarSegredoJustica},
        {bloco: 4, nome: 'CNPJs das Reclamadas', func: analisarCNPJReclamadas},
        {bloco: 5, nome: 'Tutelas Provisórias', func: analisarTutelasProvisionais},
        {bloco: 6, nome: 'Juízo 100% Digital', func: analisarJuizo100Digital},
        {bloco: 7, nome: 'Valor da Causa e Pedidos Liquidados', func: analisarValorCausa},
        {bloco: 8, nome: 'Pessoas Físicas no Polo Passivo', func: analisarPessoasFisicas},
        {bloco: 9, nome: 'Existência de Outros Processos', func: analisarOutrosProcessos},
        {bloco: 10, nome: 'Responsabilidade Subsidiária/Solidária', func: analisarResponsabilidade},
        {bloco: 11, nome: 'Endereço da Parte Reclamante', func: analisarEnderecoReclamante},
        {bloco: 12, nome: 'Rito Processual', func: analisarRitoProcessual},
        {bloco: 13, nome: 'Menção ao Art. 611-B da CLT', func: analisarArt611BCLT},
        {bloco: 15, nome: 'Análise de Procuração', func: analisarProcuracao}
    ];
    
    // Se for página de download, executa automação
    if (isPaginaDownload) {
        executarAutomacaoDownload();
        return;
    }
    
    // Se for página de detalhe, carrega interface normal
    if (isPaginaDetalhe) {
        inicializarPaginaDetalhe();
        return;
    }

    // Função AUTOMATIZADA para extrair ID e abrir janela com automação
    function extrairIdEAbrirJanelaAutomatizada() {
        // Extrai ID da URL atual
        const urlAtual = window.location.pathname;
        const match = urlAtual.match(/\/processo\/(\d+)\/detalhe/);
        
        if (!match) {
            console.error('Não foi possível extrair ID da URL:', urlAtual);
            return null;
        }
        
        const processoId = match[1];
        console.log('🎯 ID do processo extraído:', processoId);
        
        // Define instrução de automação no localStorage
        localStorage.setItem('pje_automate_download', 'true');
        localStorage.setItem('pje_process_id', processoId);
        
        // Monta URL da nova janela
        const novaUrl = `https://pje.trt2.jus.br/primeirograu/Processo/ConsultaProcesso/Detalhe/list.seam?id=${processoId}`;
        console.log('🚀 Abrindo nova janela automatizada:', novaUrl);
        
        // Abre nova janela
        const novaJanela = window.open(novaUrl, '_blank');
        
        // Monitora status do PDF
        const intervalo = setInterval(() => {
            const status = localStorage.getItem('pje_pdf_status');
            if (status === 'generated') {
                console.log('✅ PDF gerado com sucesso na outra janela!');
                localStorage.removeItem('pje_pdf_status');
                clearInterval(intervalo);
                
                // Atualiza status na interface
                const statusEl = document.getElementById('trg-status-v3');
                if (statusEl) {
                    statusEl.textContent = '✅ PDF gerado automaticamente!';
                }
            }
        }, 1000);
        
        // Para de monitorar após 30 segundos
        setTimeout(() => {
            clearInterval(intervalo);
        }, 30000);
        
        return {
            processoId: processoId,
            janela: novaJanela,
            url: novaUrl
        };
    }
    function extrairIdEAbrirJanela() {
        // Extrai ID da URL atual (padrão: /processo/ID/detalhe)
        const urlAtual = window.location.pathname;
        const match = urlAtual.match(/\/processo\/(\d+)\/detalhe/);
        
        if (!match) {
            console.error('Não foi possível extrair ID da URL:', urlAtual);
            return null;
        }
        
        const processoId = match[1];
        console.log('ID do processo extraído:', processoId);
        
        // Monta URL da nova janela
        const novaUrl = `https://pje.trt2.jus.br/primeirograu/Processo/ConsultaProcesso/Detalhe/list.seam?id=${processoId}`;
        console.log('Abrindo nova janela:', novaUrl);
        
        // Abre nova janela (headless)
        const novaJanela = window.open(novaUrl, '_blank', 'width=1,height=1,toolbar=no,menubar=no,scrollbars=no,resizable=no');
        
        // Aguarda carregar e executa ações na nova janela
        if (novaJanela) {
            novaJanela.addEventListener('load', function() {
                executarAcoesNaNovaJanela(novaJanela);
            });
        }
        
        return {
            processoId: processoId,
            janela: novaJanela,
            url: novaUrl
        };
    }

    // Função para executar ações na nova janela headless
    function executarAcoesNaNovaJanela(janela) {
        try {
            console.log('Executando ações na janela headless...');
            
            // 1. Clica no ícone PDF
            const iconePdf = janela.document.querySelector('img[src="/primeirograu/img/cp/pdf.png"]');
            if (iconePdf) {
                console.log('Clicando no ícone PDF...');
                iconePdf.click();
                  // 2. Aguarda e foca na tabela de documentos
                setTimeout(() => {
                    const tabelaDocumentos = janela.document.getElementById('resultadoJulgamentoPanel_body');
                    if (tabelaDocumentos) {
                        console.log('Focando na tabela de documentos...');
                        tabelaDocumentos.focus();
                        tabelaDocumentos.scrollIntoView({ behavior: 'smooth' });
                        console.log('Foco estabelecido na área de documentos');
                        
                        // 3. Executa seleção de documentos
                        setTimeout(() => {
                            selecionarDocumentosEspecificos(janela);
                        }, 1000); // Aguarda mais 1 segundo
                        
                    } else {
                        console.error('Área de documentos não encontrada');
                    }
                }, 2000); // Aguarda 2 segundos para carregar
                
            } else {
                console.error('Ícone PDF não encontrado');
            }
            
        } catch (error) {
            console.error('Erro ao executar ações na janela headless:', error);
        }
    }

    // Carrega pdf.js se necessário
    function loadPdfJs(callback) {
        if (window.pdfjsLib) return callback();
        let script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = callback;        document.head.appendChild(script);
    }

    // Cria interface principal
    function createUI() {
        console.log('Criando interface do relatório completo...');
        
        // Remove interface existente
        let existing = document.getElementById('trg-peticao-root-v3');
        if (existing) {
            existing.remove();
            console.log('Interface existente removida');
        }
        
        let root = document.createElement('div');
        root.id = 'trg-peticao-root-v3';
        
        // Posiciona no lado direito, abaixo de "Novo Executado"
        root.style = 'position:fixed;bottom:50px;right:20px;z-index:99999;background:#1e3a8a;color:white;border:2px solid #1e40af;border-radius:8px;padding:16px;box-shadow:0 4px 16px rgba(0,0,0,0.18);font-family:Segoe UI,Arial,sans-serif;max-width:500px;max-height:80vh;overflow-y:auto;box-sizing:border-box;';
        document.body.appendChild(root);
        console.log('Interface V3 inserida na região direita');
        
        root.innerHTML = `
            <div style="background:#1e3a8a;margin:-16px;padding:16px;border-radius:8px;">
                <b style="font-size:18px;color:white;">📋 Triagem Completa - Zona Sul SP</b>
                <button id="trg-close-v3" style="background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;float:right;margin-top:-5px;">Fechar</button>
                <div style="clear:both;margin-top:10px;"></div>
                <div id="trg-status-v3" style="margin:10px 0 12px 0;color:#e5e7eb;">Aguardando upload do PDF...</div>                <button id="trg-open-headless-v3" style="margin-bottom:8px;background:#7c3aed;color:white;border:none;padding:8px 12px;border-radius:4px;cursor:pointer;width:100%;">� Criar PDF</button>
                <input type="file" id="trg-file-v3" accept="application/pdf" style="margin-bottom:10px;width:100%;padding:8px;border-radius:4px;border:1px solid #3b82f6;background:white;color:black;">
                <button id="trg-save-txt-v3" style="display:none;margin-bottom:8px;background:#3b82f6;color:white;border:none;padding:8px 12px;border-radius:4px;cursor:pointer;width:100%;">Salvar texto extraído (.txt)</button>
                <button id="trg-save-report-v3" style="display:none;margin-bottom:8px;background:#059669;color:white;border:none;padding:8px 12px;border-radius:4px;cursor:pointer;width:100%;">Salvar relatório completo (.txt)</button>
                <div id="trg-progress-v3" style="margin:8px 0 8px 0;font-size:13px;color:#bfdbfe;"></div>
                <div id="trg-table-v3" style="color:white;"></div>
            </div>
        `;
        
        // Adiciona evento de fechar
        document.getElementById('trg-close-v3').onclick = function() {
            root.remove();
        };        // Adiciona evento para teste da janela headless
        document.getElementById('trg-open-headless-v3').onclick = function() {
            const resultado = extrairIdEAbrirJanelaAutomatizada();
            if (resultado) {
                const statusEl = document.getElementById('trg-status-v3');
                if (statusEl) {
                    statusEl.textContent = `🤖 Automação iniciada para processo ${resultado.processoId}`;
                }
                console.log('Resultado da abertura automatizada:', resultado);
            } else {
                const statusEl = document.getElementById('trg-status-v3');
                if (statusEl) {
                    statusEl.textContent = 'Erro: não foi possível extrair ID da URL';
                }
            }
        };        // Adiciona evento de upload
        document.getElementById('trg-file-v3').onchange = async function() {
            let file = this.files[0];
            if (!file) return;
            
            // Verifica se os elementos ainda existem (pode ter mudado de página)
            let status = document.getElementById('trg-status-v3');
            let progress = document.getElementById('trg-progress-v3');
            let btnSaveTxt = document.getElementById('trg-save-txt-v3');
            let btnSaveReport = document.getElementById('trg-save-report-v3');
            
            if (!status || !progress || !btnSaveTxt || !btnSaveReport) {
                console.error('Interface não encontrada - pode ter mudado de página');
                alert('Interface não encontrada. Recarregue a página e tente novamente.');
                return;
            }
            
            status.textContent = 'Extraindo o PDF...';
            progress.textContent = '';
            btnSaveTxt.style.display = 'none';
            btnSaveReport.style.display = 'none';
            
            try {
                let texto = await extrairTextoPDF(file, (pg, total) => {
                    progress.textContent = `Extraindo página ${pg} de ${total}...`;
                });
                
                textoExtraidoGlobal = texto;
                status.textContent = 'PDF extraído. Executando análise completa...';
                progress.textContent = '';
                
                // Executa todas as análises
                let resultados = [];
                let totalAnalises = analises.length;
                
                for (let i = 0; i < analises.length; i++) {
                    let a = analises[i];
                    progress.textContent = `Analisando ${a.nome} (${i+1}/${totalAnalises})...`;
                    
                    try {
                        let result = a.func(texto);
                        resultados.push({
                            bloco: a.bloco,
                            nome: a.nome,
                            result: result,
                            status: result.status || (result.alerta.includes('🔔') ? 'ALERTA' : result.alerta.includes('⚠️') ? 'ATENÇÃO' : 'OK')
                        });
                    } catch (e) {
                        console.error(`Erro na análise ${a.nome}:`, e);
                        resultados.push({
                            bloco: a.bloco,
                            nome: a.nome,
                            result: {alerta: `❌ Erro na análise: ${e.message}`, trecho: '', detalhe: ''},
                            status: 'ERRO'
                        });
                    }
                    
                    // Pequena pausa para não travar a interface
                    await new Promise(resolve => setTimeout(resolve, 50));
                }
                  // Verifica se a interface ainda existe antes de mostrar resultados
                status = document.getElementById('trg-status-v3');
                progress = document.getElementById('trg-progress-v3');
                btnSaveTxt = document.getElementById('trg-save-txt-v3');
                btnSaveReport = document.getElementById('trg-save-report-v3');
                
                if (!status || !progress || !btnSaveTxt || !btnSaveReport) {
                    console.error('Interface removida durante processamento');
                    alert('Interface foi removida. Os resultados foram processados mas não podem ser exibidos.');
                    return;
                }
                
                status.textContent = 'Análise completa finalizada.';
                progress.textContent = '';
                mostrarRelatorioCompleto(resultados);
                
                btnSaveTxt.style.display = 'block';
                btnSaveTxt.onclick = function() {
                    salvarArquivo(textoExtraidoGlobal, 'texto_extraido_peticao.txt', 'text/plain');
                };
                
                btnSaveReport.style.display = 'block';
                btnSaveReport.onclick = function() {
                    let relatorio = gerarRelatorioTexto(resultados);
                    salvarArquivo(relatorio, 'relatorio_triagem_completo.txt', 'text/plain');
                };
                
            } catch (e) {
                status.textContent = 'Erro ao extrair/analisar o PDF: ' + e.message;
                console.error('Erro:', e);
            }
        };
        
        console.log('Interface V3 criada com sucesso!');
    }

    // Função para tentar criar interface
    function tryCreateInterface() {
        if (!document.getElementById('trg-peticao-root-v3')) {
            createUI();
            return true;
        }
        return false;
    }    // Utilitário: normaliza CEP
    function normalizarCEP(cep) {
        return cep.replace(/[^0-9]/g, '');
    }

    // Utilitário: valida CEP nos intervalos da Zona Sul
    function validarCEP(cep) {
        const n = parseInt(cep, 10);
        if (cep.length !== 8 || isNaN(n)) return false;
        const faixas = [
            [4307000, 4314999], [4316000, 4477999], [4603000, 4620999],
            [4624000, 4703999], [4708000, 4967999], [5640000, 5642999],
            [5657000, 5665999], [5692000, 5692999], [5703000, 5743999],
            [5745000, 5750999], [5752000, 5895999]
        ];
        return faixas.some(([ini, fim]) => n >= ini && n <= fim);
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
    }    // BLOCO 1: Análise de Competência Territorial (CEP)
    function analisarCompetenciaTerritorial(texto) {
        let ceps_do_reclamante = [];
        let ceps_ignorados = [];
        
        // Primeiro: identifica as reclamadas na capa para focar na análise
        let reclamadasNaCapa = [];
        let matchesCapa = [...texto.matchAll(/RECLAMAD[AO]:\s*([^-\n]+(?:\s*-\s*CNPJ:\s*[\d\.\/-]+)?)/gi)];
        for (let match of matchesCapa) {
            reclamadasNaCapa.push(match[1].trim());
        }
          // Padrões para CEPs do reclamante (a serem ignorados) + exclusões de números que não são CEPs
        let contextos_reclamante = [
            /reclamante[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /residente[\s\S]{0,100}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /domiciliad[ao][\s\S]{0,100}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /RESIDENTE E DOMICILIADA[\s\S]{0,100}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /OUTORGANTE[\s\S]{0,200}?CEP:?\s*(\d{5}\s?\d{3})/gi
        ];
        
        // Padrões de exclusão - números que NÃO são CEPs
        let padroes_exclusao = [
            /CTPS\s+n[°ºª]?\s*(\d{8})/gi,  // CTPS
            /RG\.?\s+n[°ºª]?\s*(\d{5,15})/gi,  // RG
            /CPF[\/\s]*n[°ºª]?\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})/gi,  // CPF
            /CNPJ[\/\s]*n[°ºª]?\s*(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2})/gi,  // CNPJ
            /PIS[\/\s]*n[°ºª]?\s*(\d{3}\.?\d{5}\.?\d{2}\.?\d{1})/gi,  // PIS
            /OAB[\/\s]*n[°ºª]?\s*(\d+)/gi  // OAB
        ];
        
        let numeros_excluidos = [];
        for (let regex of padroes_exclusao) {
            let match;
            while ((match = regex.exec(texto)) !== null) {
                numeros_excluidos.push(normalizarCEP(match[1]));
            }
        }
        
        for (let regex of contextos_reclamante) {
            let match;
            while ((match = regex.exec(texto)) !== null) {
                let cep = normalizarCEP(match[1]);
                ceps_do_reclamante.push(cep);
                ceps_ignorados.push({cep, contexto: match[0].trim().slice(0, 120)});
            }
        }
        
        ceps_do_reclamante = [...new Set(ceps_do_reclamante)];
          // BUSCA HIERÁRQUICA PELO CEP DA RECLAMADA (COM PARADA AUTOMÁTICA SE VÁLIDO)
        let ceps_prioritarios = [];
        let contexto_ceps = [];
        let cep_encontrado_valido = false; // Flag para parar busca se CEP válido for encontrado
        
        // ETAPA 1: Busca CEP especificamente das reclamadas identificadas na capa
        for (let reclamada of reclamadasNaCapa) {
            if (cep_encontrado_valido) break; // PARA se já encontrou CEP válido
            
            let nomeReclamada = reclamada.split(' - ')[0].trim(); // Remove CNPJ se estiver junto
            let palavrasChave = nomeReclamada.split(' ').slice(0, 3).join('|'); // Primeiras 3 palavras
            
            // Busca CEP próximo ao nome/CNPJ da reclamada específica
            let regexReclamada = new RegExp(`(${palavrasChave})[\\s\\S]{0,300}?CEP:?\\s*(\\d{5}\\s?-?\\s?\\d{3})`, 'gi');
            let match;            while ((match = regexReclamada.exec(texto)) !== null) {
                let cep = normalizarCEP(match[2]);
                if (!ceps_do_reclamante.includes(cep) && !numeros_excluidos.includes(cep)) {
                    ceps_prioritarios.push(cep);
                    contexto_ceps.push({cep, contexto: `${nomeReclamada}: ${match[0].trim().slice(0, 120)}`});
                    
                    // VERIFICA SE O CEP É VÁLIDO E PARA A BUSCA
                    if (validarCEP(cep)) {
                        cep_encontrado_valido = true;
                        break; // Para de buscar mais CEPs
                    }
                }
            }
        }
        
        // ETAPA 2: Se não encontrou CEP válido, busca por CNPJ + CEP (apenas das reclamadas da capa)
        if (!cep_encontrado_valido && ceps_prioritarios.length === 0) {
            let cnpjsReclamadas = [];
            for (let reclamada of reclamadasNaCapa) {
                let matchCNPJ = reclamada.match(/CNPJ:\s*([\d\.\/-]+)/);
                if (matchCNPJ) {
                    cnpjsReclamadas.push(matchCNPJ[1].replace(/[^0-9]/g, ''));
                }
            }
            
            if (cnpjsReclamadas.length > 0) {
                for (let cnpj of cnpjsReclamadas) {
                    if (cep_encontrado_valido) break; // PARA se já encontrou CEP válido
                    
                    let cnpjFormatado = cnpj.substring(0, 2) + '\\.' + cnpj.substring(2, 5) + '\\.' + cnpj.substring(5, 8) + '\\/' + cnpj.substring(8, 12) + '\\-' + cnpj.substring(12);
                    let regexCNPJ = new RegExp(`${cnpjFormatado}[\\s\\S]{0,200}?CEP:?\\s*(\\d{5}\\s?-?\\s?\\d{3})`, 'gi');
                    let match;                    while ((match = regexCNPJ.exec(texto)) !== null) {
                        let cep = normalizarCEP(match[1]);
                        if (!ceps_do_reclamante.includes(cep) && !numeros_excluidos.includes(cep)) {
                            ceps_prioritarios.push(cep);
                            contexto_ceps.push({cep, contexto: `CNPJ ${cnpj}: ${match[0].trim().slice(0, 120)}`});
                            
                            // VERIFICA SE O CEP É VÁLIDO E PARA A BUSCA
                            if (validarCEP(cep)) {
                                cep_encontrado_valido = true;
                                break; // Para de buscar mais CEPs
                            }
                        }
                    }
                }
            }
        }
        
        // ETAPA 3: Se não encontrou CEP válido, busca por sede da reclamada
        if (!cep_encontrado_valido && ceps_prioritarios.length === 0) {
            let matchSede = texto.match(/com sede[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi);
            if (matchSede) {
                for (let m of matchSede) {
                    if (cep_encontrado_valido) break; // PARA se já encontrou CEP válido
                    
                    let ceps = [...m.matchAll(/(\d{5}\s?-?\s?\d{3})/g)].map(c => normalizarCEP(c[1]));
                    if (ceps.length) {                        for (let cep of ceps) {
                            if (!ceps_do_reclamante.includes(cep) && !numeros_excluidos.includes(cep)) {
                                ceps_prioritarios.push(cep);
                                contexto_ceps.push({cep, contexto: 'com sede: ' + m.trim().slice(0, 120)});
                                
                                // VERIFICA SE O CEP É VÁLIDO E PARA A BUSCA
                                if (validarCEP(cep)) {
                                    cep_encontrado_valido = true;
                                    break; // Para de buscar mais CEPs
                                }
                            }
                        }
                    }
                }
            }
        }
        
        // ETAPA 4: Se CEP da reclamada NÃO ESTÁ na jurisdição, aí sim busca por "local de prestação de serviços"
        if (!cep_encontrado_valido) {
            let padroesPrestacao = [
                /último\s+local\s+(?:da\s+)?prestação\s+(?:de\s+)?serviços?[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /local\s+(?:da\s+)?prestação\s+(?:de\s+)?serviços?[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /prestação\s+(?:de\s+)?serviços?[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /trabalho\s+(?:foi\s+)?executado[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /serviços?\s+(?:foram\s+)?prestados?[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /atividades?\s+(?:foram\s+)?(?:desenvolvidas?|realizadas?)[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi
            ];
            
            for (let padrao of padroesPrestacao) {
                if (cep_encontrado_valido) break; // PARA se já encontrou CEP válido
                
                let match;                while ((match = padrao.exec(texto)) !== null) {
                    let cep = normalizarCEP(match[1]);
                    if (!ceps_do_reclamante.includes(cep) && !numeros_excluidos.includes(cep)) {
                        ceps_prioritarios.push(cep);
                        contexto_ceps.push({cep, contexto: 'prestação de serviços: ' + match[0].trim().slice(0, 120)});
                        
                        // VERIFICA SE O CEP É VÁLIDO E PARA A BUSCA
                        if (validarCEP(cep)) {
                            cep_encontrado_valido = true;
                            break; // Para de buscar mais CEPs
                        }
                    }
                }
            }
        }
        
        // ETAPA 5: Se ainda não encontrou CEP válido, busca por menções de "competência territorial"
        if (!cep_encontrado_valido) {
            let padroesCompetencia = [
                /competência\s+territorial[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /competente\s+(?:este\s+)?ju[íi]zo[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /foro\s+competente[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /jurisdição[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /art\.?\s*651[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /artigo\s+651[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
                /651.*CLT[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi
            ];
            
            for (let padrao of padroesCompetencia) {
                if (cep_encontrado_valido) break; // PARA se já encontrou CEP válido
                
                let match;                while ((match = padrao.exec(texto)) !== null) {
                    let cep = normalizarCEP(match[1]);
                    if (!ceps_do_reclamante.includes(cep) && !numeros_excluidos.includes(cep)) {
                        ceps_prioritarios.push(cep);
                        contexto_ceps.push({cep, contexto: 'competência territorial: ' + match[0].trim().slice(0, 120)});
                        
                        // VERIFICA SE O CEP É VÁLIDO E PARA A BUSCA
                        if (validarCEP(cep)) {
                            cep_encontrado_valido = true;
                            break; // Para de buscar mais CEPs
                        }
                    }
                }
            }
        }
          // ETAPA 6: ÚLTIMO FALLBACK: CEPs gerais exceto do reclamante (só se não encontrou nada válido)
        if (!cep_encontrado_valido && ceps_prioritarios.length === 0) {
            // Busca apenas CEPs com formato correto e que estejam próximos da palavra "CEP"
            let ceps_com_contexto = [...texto.matchAll(/CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi)];
            let ceps_nao_reclamante = [];
              for (let match of ceps_com_contexto) {
                let cep = normalizarCEP(match[1]);
                if (!ceps_do_reclamante.includes(cep) && !numeros_excluidos.includes(cep)) {
                    ceps_nao_reclamante.push(cep);
                }
            }
            
            ceps_prioritarios = [...new Set(ceps_nao_reclamante)];
            
            if (ceps_prioritarios.length > 0) {
                contexto_ceps.push({cep: ceps_prioritarios.join(','), contexto: 'fallback: CEPs formatados encontrados no documento'});
            }
        }        ceps_prioritarios = [...new Set(ceps_prioritarios)];
        
        // Determina qual regra foi usada e o CEP principal
        // PRIORIZA CEPs válidos (dentro da jurisdição) sobre inválidos
        let cep_usado = null;
        let indice_usado = 0;
        
        if (ceps_prioritarios.length > 0) {
            // Procura primeiro por um CEP válido
            for (let i = 0; i < ceps_prioritarios.length; i++) {
                if (validarCEP(ceps_prioritarios[i])) {
                    cep_usado = ceps_prioritarios[i];
                    indice_usado = i;
                    break;
                }
            }
            // Se não encontrou CEP válido, usa o primeiro mesmo
            if (!cep_usado) {
                cep_usado = ceps_prioritarios[0];
                indice_usado = 0;
            }
        }
        
        let regra_usada = '';
        
        if (cep_usado && contexto_ceps.length > indice_usado) {
            let contexto = contexto_ceps[indice_usado].contexto.toLowerCase();
            if (contexto.includes('cnpj') || contexto.includes('sede')) {
                regra_usada = 'CEP da reclamada';
            } else if (contexto.includes('prestação') || contexto.includes('serviços') || contexto.includes('trabalho')) {
                regra_usada = 'CEP do local de prestação de serviços';
            } else {
                regra_usada = 'CEP da reclamada';
            }
        }
        
        let detalhe = '';
        detalhe += `Reclamadas identificadas na capa: ${reclamadasNaCapa.length}\n`;
        if (reclamadasNaCapa.length > 0) {
            detalhe += `Nomes: ${reclamadasNaCapa.map(r => r.split(' - ')[0]).join(', ')}\n`;
        }
        detalhe += `CEPs encontrados na petição: ${[...texto.matchAll(/\b\d{5}\s?-?\s?\d{3}\b/g)].length}\n\n`;
        
        if (cep_usado) {
            detalhe += `📍 CEP USADO: ${cep_usado}\n`;
            detalhe += `📋 REGRA: ${regra_usada}\n\n`;
        }
        
        detalhe += `🔍 ESTRATÉGIA DE BUSCA HIERÁRQUICA (com parada automática):\n`;
        detalhe += `1. CEPs específicos das reclamadas identificadas na capa\n`;
        detalhe += `2. CEPs associados aos CNPJs das reclamadas\n`;
        detalhe += `3. CEPs mencionados com "sede" das empresas\n`;
        detalhe += `🛑 REGRA: Se encontrar CEP válido da reclamada, PARA a busca!\n`;
        detalhe += `4. (Só se CEP da reclamada NÃO estiver na jurisdição)\n`;
        detalhe += `   - CEPs do último local de prestação de serviços\n`;
        detalhe += `   - CEPs próximos a menções de "competência territorial"\n`;
        detalhe += `   - Outros CEPs (exceto do reclamante)\n\n`;
        
        if (cep_encontrado_valido) {
            detalhe += `✅ CEP VÁLIDO ENCONTRADO - Busca interrompida!\n`;
        }
        
        if (ceps_prioritarios.length) {
            detalhe += 'CEPs das reclamadas: ' + ceps_prioritarios.join(', ') + '\n';
            if (contexto_ceps.length) {
                detalhe += 'Contextos encontrados:\n';
                contexto_ceps.forEach(obj => {
                    detalhe += `- ${obj.cep}: ${obj.contexto}\n`;
                });
            }
        }
        if (ceps_do_reclamante.length) {
            detalhe += 'CEPs ignorados (reclamante): ' + ceps_do_reclamante.join(', ') + '\n';
        }        let alerta = null, trecho = '';
        if (ceps_prioritarios.length === 0) {
            alerta = '🔔 ALERTA: Não foi possível identificar o CEP das reclamadas para análise de competência territorial.';
        } else {
            // Verifica especificamente se o CEP USADO (primeiro da lista) é válido
            let cepUsadoValido = validarCEP(cep_usado);
            if (!cepUsadoValido) {
                alerta = `🔔 ALERTA: CEP ${cep_usado} (${regra_usada}) não está na jurisdição da Zona Sul de São Paulo.`;
                trecho = `${cep_usado} (${regra_usada})`;
            } else {
                alerta = `✅ CEP ${cep_usado} (${regra_usada}) está na jurisdição da Zona Sul de São Paulo.`;
                trecho = `${cep_usado} (${regra_usada})`;
            }
        }
        
        return {alerta: alerta || '✅ Análise de CEP concluída.', trecho, detalhe};
    }// BLOCO 2: Análise das Partes
    function analisarPartes(texto) {
        let detalhe = '';
        let alertas = [];
        
        // Busca por partes na capa/seção específica de partes
        let reclamantes = [];
        let reclamadas = [];
        
        // Padrões mais precisos para identificar partes na seção específica
        let matchReclamante = texto.match(/RECLAMANTE:\s*([A-ZÁÊÔÂÀÍÉÇ\s\-\.]+)/i);
        if (matchReclamante) {
            reclamantes.push(matchReclamante[1].trim());
        }
          // Busca reclamadas APENAS na seção de partes da capa (não no corpo da petição)
        let matchesReclamada = [...texto.matchAll(/RECLAMAD[AO]:\s*([A-ZÁÊÔÂÀÍÉÇ\s\&\-\.\d]+)(?=\s+PAGINA_CAPA|$|\n)/gi)];
        
        // Fallback: busca na seção inicial do documento (primeira parte antes do texto da petição)
        if (matchesReclamada.length === 0) {
            let secaoInicial = texto.substring(0, Math.min(2000, texto.length));
            matchesReclamada = [...secaoInicial.matchAll(/RECLAMAD[AO]:\s*([A-ZÁÊÔÂÀÍÉÇ\s\&\-\.\d]+)/gi)];
        }
        
        reclamadas = matchesReclamada.map(m => m[1].trim());
        
        // Se não encontrou na seção de partes, tenta fallback com CNPJ único
        if (reclamadas.length === 0) {
            let cnpjs = [...texto.matchAll(/CNPJ[\s:]*(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2})/gi)];
            let cnpjsUnicos = new Set(cnpjs.map(m => m[1].replace(/[^0-9]/g, '')));
            reclamadas = Array.from(cnpjsUnicos).map(cnpj => `Empresa CNPJ ${cnpj}`);
        }
        
        detalhe += `Reclamantes identificados: ${reclamantes.length}\n`;
        detalhe += `Reclamadas identificadas: ${reclamadas.length}\n`;
        
        // Verifica dados mínimos
        let temCPF = /CPF[\s:]*\d{3}\.?\d{3}\.?\d{3}\-?\d{2}/.test(texto);
        let temCNPJ = /CNPJ[\s:]*\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}/.test(texto);
        
        detalhe += `CPF encontrado: ${temCPF ? 'Sim' : 'Não'}\n`;
        detalhe += `CNPJ encontrado: ${temCNPJ ? 'Sim' : 'Não'}\n`;        // Verifica pessoa jurídica de direito público (busca mais específica no contexto das reclamadas)
        let secaoReclamadas = texto.match(/RECLAMAD[AO]S?:\s*([^\.]+\.?)/gi);
        let pessoaPublica = false;
        
        if (secaoReclamadas) {
            let textoReclamadas = secaoReclamadas.join(' ');
            pessoaPublica = /MUNICÍPIO|ESTADO\s+DE|UNIÃO|AUTARQUIA|FUNDAÇÃO\s+PÚBLICA|PREFEITURA\s+MUNICIPAL|GOVERNO\s+DO\s+ESTADO/i.test(textoReclamadas);
        } else {
            // Fallback: busca em contexto mais restrito
            pessoaPublica = /(?:RECLAMAD[AO]|em\s+face\s+de|contra)[^\.]*(?:MUNICÍPIO|ESTADO\s+DE|UNIÃO|AUTARQUIA|FUNDAÇÃO\s+PÚBLICA|PREFEITURA\s+MUNICIPAL|GOVERNO\s+DO\s+ESTADO)/i.test(texto);
        }
        
        if (pessoaPublica) {
            alertas.push('Pessoa jurídica de direito público identificada');
            detalhe += 'Pessoa jurídica de direito público: Sim\n';
        } else {
            detalhe += 'Pessoa jurídica de direito público: Não\n';
        }
        
        let alerta = '';
        if (!temCPF && !temCNPJ) {
            alerta = '🔔 ALERTA: Dados de identificação incompletos (CPF/CNPJ não encontrados).';
        } else if (pessoaPublica) {
            alerta = '⚠️ ATENÇÃO: Pessoa jurídica de direito público no polo passivo (Rito Ordinário obrigatório).';
        } else {
            alerta = '✅ Partes adequadamente identificadas.';
        }
        
        return {alerta, trecho: alertas.join(', '), detalhe};
    }

    // BLOCO 3: Segredo de Justiça
    function analisarSegredoJustica(texto) {
        let pedidoSegredo = /segredo de justi[çc]a|tramita[çc][ãa]o sigilosa|processo sigiloso/i.test(texto);
        let fundamentacao = /art\.?\s*189|artigo 189|CPC.*189/i.test(texto);
        
        let detalhe = `Pedido de segredo de justiça: ${pedidoSegredo ? 'Encontrado' : 'Não encontrado'}\n`;
        detalhe += `Fundamentação legal: ${fundamentacao ? 'Presente' : 'Ausente'}\n`;
        
        let alerta = '';
        if (pedidoSegredo && !fundamentacao) {
            alerta = '🔔 ALERTA: Pedido de segredo de justiça sem fundamentação legal adequada.';
        } else if (pedidoSegredo && fundamentacao) {
            alerta = '⚠️ ATENÇÃO: Pedido de segredo de justiça devidamente fundamentado.';
        } else {
            alerta = '✅ Processo sem pedido de segredo de justiça.';
        }
        
        return {alerta, trecho: pedidoSegredo ? 'Pedido identificado' : '', detalhe};
    }    // BLOCO 4: Verificação de CNPJs das Reclamadas
    function analisarCNPJReclamadas(texto) {
        // Primeiro: identifica as reclamadas na capa
        let reclamadasNaCapa = [];
        let matchesCapa = [...texto.matchAll(/RECLAMAD[AO]:\s*([^-\n]+(?:\s*-\s*CNPJ:\s*[\d\.\/-]+)?)/gi)];
        for (let match of matchesCapa) {
            reclamadasNaCapa.push(match[1].trim());
        }
        
        // Busca CNPJs especificamente das reclamadas identificadas na capa
        let cnpjsReclamadas = [];
        let detalhe = `Reclamadas identificadas na capa: ${reclamadasNaCapa.length}\n`;
        
        for (let reclamada of reclamadasNaCapa) {
            // Busca CNPJ diretamente na linha da capa
            let matchCNPJCapa = reclamada.match(/CNPJ:\s*([\d\.\/-]+)/);
            if (matchCNPJCapa) {
                cnpjsReclamadas.push(matchCNPJCapa[1]);
                detalhe += `CNPJ da capa: ${matchCNPJCapa[1]}\n`;
            } else {
                // Se não encontrou na capa, busca no corpo da petição pelo nome da reclamada
                let nomeReclamada = reclamada.split(' - ')[0].trim();
                let palavrasChave = nomeReclamada.split(' ').slice(0, 3).join('|');
                let regexCorpo = new RegExp(`(${palavrasChave})[\\s\\S]{0,300}?CNPJ[\\s:]*([\\d\\.\\/-]+)`, 'gi');
                let matchCorpo = regexCorpo.exec(texto);
                if (matchCorpo) {
                    cnpjsReclamadas.push(matchCorpo[2]);
                    detalhe += `CNPJ encontrado no corpo: ${matchCorpo[2]} (para ${nomeReclamada})\n`;
                } else {
                    detalhe += `CNPJ não encontrado para: ${nomeReclamada}\n`;
                }
            }
        }
        
        let alertas = [];
        let cnpjsValidos = 0;
        let filiais = 0;
        
        detalhe += `CNPJs das reclamadas encontrados: ${cnpjsReclamadas.length}\n`;
        
        for (let cnpj of cnpjsReclamadas) {
            let cnpjLimpo = cnpj.replace(/[^0-9]/g, '');
            detalhe += `CNPJ: ${cnpj} (${cnpjLimpo.length} dígitos)\n`;
            
            if (cnpjLimpo.length === 14) {
                cnpjsValidos++;
                // Verifica se é filial
                if (!cnpjLimpo.endsWith('0001')) {
                    filiais++;
                }
            } else {
                alertas.push(`CNPJ incompleto: ${cnpj}`);
            }
        }
        
        detalhe += `CNPJs válidos: ${cnpjsValidos}\n`;
        detalhe += `Filiais identificadas: ${filiais}\n`;
        
        let alerta = '';
        if (alertas.length > 0) {
            alerta = '🔔 ALERTA: ' + alertas.join('; ');
        } else if (cnpjsReclamadas.length === 0) {
            alerta = '🔔 ALERTA: Nenhum CNPJ encontrado para as reclamadas identificadas na capa.';
        } else {
            alerta = '✅ CNPJs das reclamadas adequadamente informados.';
        }
        
        return {alerta, trecho: alertas.join(', '), detalhe};
    }

    // BLOCO 5: Tutelas Provisórias
    function analisarTutelasProvisionais(texto) {
        let tutolaUrgencia = /tutela.*urg[êe]ncia|liminar|tutela.*antecipada|art\.?\s*300|artigo 300/i.test(texto);
        let tutelaCautelar = /tutela.*cautelar|art\.?\s*305|artigo 305/i.test(texto);
        let tutelaEvidencia = /tutela.*evid[êe]ncia|art\.?\s*311|artigo 311/i.test(texto);
        
        let temTutela = tutolaUrgencia || tutelaCautelar || tutelaEvidencia;
        
        let detalhe = `Tutela de urgência: ${tutolaUrgencia ? 'Identificada' : 'Não identificada'}\n`;
        detalhe += `Tutela cautelar: ${tutelaCautelar ? 'Identificada' : 'Não identificada'}\n`;
        detalhe += `Tutela de evidência: ${tutelaEvidencia ? 'Identificada' : 'Não identificada'}\n`;
        
        let alerta = '';
        if (temTutela) {
            alerta = '🔔 ALERTA: Pedido de tutela provisória identificado - necessário encaminhamento imediato para despacho.';
        } else {
            alerta = '✅ Sem pedidos de tutela provisória.';
        }
        
        return {alerta, trecho: temTutela ? 'Tutela provisória requerida' : '', detalhe};
    }

    // BLOCO 6: Juízo 100% Digital
    function analisarJuizo100Digital(texto) {
        let adesao100Digital = /ju[íi]zo 100%.*digital|100%.*digital|adesão.*digital|processo.*eletr[ôo]nico.*integral/i.test(texto);
        
        let detalhe = `Manifestação de adesão ao Juízo 100% Digital: ${adesao100Digital ? 'Encontrada' : 'Não encontrada'}\n`;
        
        let alerta = '';
        if (adesao100Digital) {
            alerta = '⚠️ ATENÇÃO: Manifestação expressa de adesão ao Juízo 100% Digital.';
        } else {
            alerta = '✅ Sem manifestação de adesão ao Juízo 100% Digital.';
        }
        
        return {alerta, trecho: adesao100Digital ? 'Adesão identificada' : '', detalhe};
    }

    // BLOCO 7: Análise de Valor da Causa e Pedidos Liquidados
    function analisarValorCausa(texto) {
        let valorCapa = (texto.match(/valor da causa[^\d]{0,20}([\d\.,]+)/i) || [])[1];
        
        // Busca pelo valor total dos pedidos no final da petição
        let valorTotal = null;
        let contextoValorTotal = '';
        
        // Padrões para encontrar o valor total dos pedidos
        let padroes = [
            /total\s+devido\s+líquido[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i,
            /total\s+bruto\s+estimado[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i,
            /total\s+(dos\s+)?pedidos[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i,
            /valor\s+total[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i,
            /total\s+(das\s+)?verbas[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i,
            /valor\s+(das\s+)?verbas[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i,
            /(total|valor)\s+(estimado|requerido|devido)[^\d]{0,50}R\$\s?([\d\.]+,[\d]{2})/i
        ];
        
        for (let padrao of padroes) {
            let match = texto.match(padrao);
            if (match) {
                let valor = match[match.length - 1]; // Pega o último grupo capturado (o valor)
                valorTotal = parseFloat(valor.replace(/\./g, '').replace(',', '.'));
                contextoValorTotal = match[0].trim().slice(0, 80);
                break;
            }
        }
        
        // Verifica se pedidos estão liquidados
        let pedidosLiquidados = /R\$\s*[\d\.,]+/g.test(texto);
        let quantidadeValores = (texto.match(/R\$\s*[\d\.,]+/g) || []).length;
        
        let detalhe = '';
        if (valorCapa) detalhe += `Valor da causa (capa): R$ ${valorCapa}\n`;
        if (valorTotal) {
            detalhe += `Valor total encontrado: R$ ${valorTotal.toFixed(2)}\n`;
            detalhe += `Contexto: "${contextoValorTotal}"\n`;
        }
        detalhe += `Pedidos com valores (liquidados): ${pedidosLiquidados ? 'Sim' : 'Não'}\n`;
        detalhe += `Quantidade de valores R$ encontrados: ${quantidadeValores}\n`;
        
        let alertas = [];
        if (!valorCapa && !valorTotal) {
            alertas.push('Valor da causa não informado e valor total dos pedidos não encontrado');
        } else if (!valorTotal) {
            alertas.push('Valor total dos pedidos não encontrado');
        } else if (!valorCapa) {
            alertas.push('Valor da causa não informado na capa');
        } else {
            // Compara valor da capa com total dos pedidos
            let valorCapaNum = parseFloat(valorCapa.replace(/\./g, '').replace(',', '.'));
            let diferenca = Math.abs(valorCapaNum - valorTotal);
            
            if (diferenca > valorCapaNum * 0.1) { // Diferença maior que 10%
                alertas.push('Divergência significativa entre valor da causa e valor total dos pedidos (> 10%)');
            }
        }
        
        if (!pedidosLiquidados) {
            alertas.push('Pedidos não liquidados (sem valores específicos)');
        }
        
        let alerta = '';
        if (alertas.length > 0) {
            alerta = '🔔 ALERTA: ' + alertas.join('; ');
        } else {
            alerta = '✅ Valores verificados e pedidos adequadamente liquidados.';
        }
        
        return {alerta, trecho: alertas.join(', '), detalhe};
    }

    // BLOCO 8: Inclusão de Pessoas Físicas no Polo Passivo
    function analisarPessoasFisicas(texto) {
        let pessoasFisicas = /CPF.*pessoa.*física|sócio.*administrador|representante.*legal/i.test(texto);
        let fundamentacao = /responsabilidade.*pessoal|desconsideração.*personalidade|art\.?\s*50|teoria.*ultra.*vires/i.test(texto);
        
        let detalhe = `Pessoas físicas no polo passivo: ${pessoasFisicas ? 'Identificadas' : 'Não identificadas'}\n`;
        detalhe += `Fundamentação para inclusão: ${fundamentacao ? 'Presente' : 'Ausente'}\n`;
        
        let alerta = '';
        if (pessoasFisicas && !fundamentacao) {
            alerta = '🔔 ALERTA: Inclusão de pessoa física no polo passivo sem fundamentação jurídica adequada.';
        } else if (pessoasFisicas && fundamentacao) {
            alerta = '✅ Pessoa física no polo passivo devidamente fundamentada.';
        } else {
            alerta = '✅ Sem inclusão de pessoas físicas no polo passivo.';
        }
        
        return {alerta, trecho: pessoasFisicas ? 'Pessoa física identificada' : '', detalhe};
    }

    // BLOCO 9: Existência de Outros Processos
    function analisarOutrosProcessos(texto) {
        let outroProcesso = /processo.*anterior|ação.*anterior|processo.*n[úu]mero|litispend[êe]ncia|coisa julgada|prevenção/i.test(texto);
        let numeroProcesso = /\d{7}\-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/.test(texto);
        
        let detalhe = `Menção a outros processos: ${outroProcesso ? 'Encontrada' : 'Não encontrada'}\n`;
        detalhe += `Número de processo identificado: ${numeroProcesso ? 'Sim' : 'Não'}\n`;
        
        let alerta = '';
        if (outroProcesso) {
            alerta = '🔔 ALERTA: Possível litispendência, coisa julgada ou prevenção - verificar necessidade de redistribuição.';
        } else {
            alerta = '✅ Sem menção a outros processos relacionados.';
        }
        
        return {alerta, trecho: outroProcesso ? 'Outro processo mencionado' : '', detalhe};
    }    // BLOCO 10: Responsabilidade Subsidiária/Solidária
    function analisarResponsabilidade(texto) {
        // Conta quantas reclamadas na seção de partes (mais preciso)
        let reclamadas = 0;
        
        // Tenta identificar reclamadas na capa/seção de partes
        let secaoPartes = texto.match(/RECLAMAD[AO]:\s*([^\n]+)/gi);
        if (secaoPartes) {
            reclamadas = secaoPartes.length;
        } else {
            // Fallback: busca por padrões de CNPJ únicos como indicativo
            let cnpjs = [...texto.matchAll(/CNPJ[\s:]*(\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2})/gi)];
            let cnpjsUnicos = new Set(cnpjs.map(m => m[1].replace(/[^0-9]/g, '')));
            reclamadas = cnpjsUnicos.size || 1; // Pelo menos 1 se não encontrar nada
        }
        
        // Conforme pet.md: "caso só exista uma reclamada, não há necessidade de analisar e emitir alerta"
        if (reclamadas === 1) {
            let detalhe = `Número de reclamadas: ${reclamadas}\n`;
            detalhe += `Análise: Dispensada - apenas uma reclamada conforme roteiro pet.md\n`;
            
            return {
                alerta: '✅ Análise dispensada - apenas uma reclamada identificada.',
                trecho: '',
                detalhe
            };
        }
        
        // Análise para múltiplas reclamadas
        let responsabilidadeSubsidiaria = /responsabilidade.*subsidi[áa]ria|subsidi[áa]riamente/i.test(texto);
        let responsabilidadeSolidaria = /responsabilidade.*solid[áa]ria|solidariamente/i.test(texto);
        let fundamentacao = /grupo.*econ[ôo]mico|confusão.*patrimonial|terceirização|tomador.*serviços/i.test(texto);
        
        let detalhe = `Número de reclamadas: ${reclamadas}\n`;
        detalhe += `Responsabilidade subsidiária: ${responsabilidadeSubsidiaria ? 'Requerida' : 'Não requerida'}\n`;
        detalhe += `Responsabilidade solidária: ${responsabilidadeSolidaria ? 'Requerida' : 'Não requerida'}\n`;
        detalhe += `Fundamentação presente: ${fundamentacao ? 'Sim' : 'Não'}\n`;
        
        let alerta = '';
        if (!responsabilidadeSubsidiaria && !responsabilidadeSolidaria) {
            alerta = '🔔 ALERTA: Múltiplas reclamadas sem pedido de responsabilidade subsidiária/solidária - necessário emenda.';
        } else if ((responsabilidadeSubsidiaria || responsabilidadeSolidaria) && !fundamentacao) {
            alerta = '🔔 ALERTA: Pedido de responsabilidade sem fundamentação adequada - necessário emenda.';
        } else {
            alerta = '✅ Responsabilidade adequadamente tratada.';
        }
        
        return {alerta, trecho: '', detalhe};
    }

    // BLOCO 11: Endereço da Parte Reclamante
    function analisarEnderecoReclamante(texto) {
        let enderecoSP = /São Paulo.*SP|S[ãa]o Paulo.*S\.?P\.?/i.test(texto);
        let enderecoForaSP = /[A-ZÁÊÔÂÀÍÉ]+.*[A-Z]{2}(?!.*São Paulo)/i.test(texto) && !enderecoSP;
        let audienciaVirtual = /audi[êe]ncia.*virtual|audi[êe]ncia.*telepresencial|audi[êe]ncia.*h[íi]brida|videoconfer[êe]ncia/i.test(texto);
        
        let detalhe = `Endereço em São Paulo/SP: ${enderecoSP ? 'Sim' : 'Não'}\n`;
        detalhe += `Endereço fora de São Paulo: ${enderecoForaSP ? 'Sim' : 'Não'}\n`;
        detalhe += `Pedido de audiência virtual: ${audienciaVirtual ? 'Sim' : 'Não'}\n`;
        
        let alertas = [];
        if (enderecoForaSP) {
            alertas.push('Endereço fora do município de São Paulo/SP');
        }
        if (audienciaVirtual) {
            alertas.push('Pedido de audiência virtual/telepresencial identificado');
        }
        
        let alerta = '';
        if (alertas.length > 0) {
            alerta = '🔔 ALERTA: ' + alertas.join('; ') + ' - verificar adequação para audiência virtual.';
        } else {
            alerta = '✅ Endereço adequado e sem pedidos especiais de audiência.';
        }
        
        return {alerta, trecho: alertas.join(', '), detalhe};
    }    // BLOCO 12: Definição e Validação do Rito Processual
    function analisarRitoProcessual(texto) {
        let valorCapa = (texto.match(/valor da causa[^\d]{0,20}([\d\.,]+)/i) || [])[1];
        let ritoDeclarado = '';        // Detecção do rito apenas na capa do processo (primeiros 500 caracteres)
        let secaoInicial = texto.substring(0, Math.min(500, texto.length));
        
        if (/RITO\s+SUMAR[ÍI]SSIMO|SUMAR[ÍI]SSIMO/i.test(secaoInicial)) {
            ritoDeclarado = 'Sumaríssimo';
        } else if (/RITO\s+ORDIN[ÁA]RIO|ORDIN[ÁA]RIO/i.test(secaoInicial)) {
            ritoDeclarado = 'Ordinário';
        } else if (/ALÇADA/i.test(secaoInicial)) {
            ritoDeclarado = 'Alçada';
        }
        
        // Verifica pessoa jurídica de direito público apenas no contexto das reclamadas
        let pessoaPublica = false;
        
        // Busca por reclamadas na capa
        let reclamadasTexto = '';
        let matchReclamadas = [...texto.matchAll(/RECLAMAD[AO]:\s*([^-\n]+(?:\s*-\s*CNPJ:\s*[\d\.\/-]+)?)/gi)];
        for (let match of matchReclamadas) {
            reclamadasTexto += match[1] + ' ';
        }
        
        // Também busca no corpo da petição por nomes das reclamadas seguidos dos termos
        let secaoReclamadas = texto.match(/reclamad[ao][\s\S]{0,500}/gi);
        if (secaoReclamadas) {
            reclamadasTexto += secaoReclamadas.join(' ');
        }
        
        // Verifica se há termos de pessoa jurídica de direito público apenas no contexto das reclamadas
        if (reclamadasTexto) {
            pessoaPublica = /MUNICÍPIO|ESTADO\s+DE\s+[A-Z]+|UNIÃO|AUTARQUIA|FUNDAÇÃO\s+PÚBLICA|PREFEITURA\s+MUNICIPAL|GOVERNO\s+DO\s+ESTADO/i.test(reclamadasTexto);
        }
        let salarioMinimo = 1518.00; // 2025
        
        let detalhe = `Valor da causa: ${valorCapa || 'Não informado'}\n`;
        detalhe += `Rito declarado: ${ritoDeclarado || 'Não identificado'}\n`;
        detalhe += `Pessoa jurídica de direito público: ${pessoaPublica ? 'Sim' : 'Não'}\n`;
        detalhe += `Salário mínimo considerado: R$ ${salarioMinimo.toFixed(2)}\n`;
        
        let ritoCorreto = '';
        let alerta = '';
        
        if (pessoaPublica) {
            ritoCorreto = 'Ordinário';
            alerta = ritoDeclarado === 'Ordinário' ? 
                '✅ Rito Ordinário corretamente aplicado (pessoa jurídica de direito público).' :
                '🔔 ALERTA: Rito deve ser Ordinário devido à presença de pessoa jurídica de direito público.';
        } else if (valorCapa) {
            let valor = parseFloat(valorCapa.replace(/\./g, '').replace(',', '.'));
            detalhe += `Valor convertido: R$ ${valor.toFixed(2)}\n`;
            
            if (valor <= 2 * salarioMinimo) {
                ritoCorreto = 'Alçada';
            } else if (valor <= 40 * salarioMinimo) {
                ritoCorreto = 'Sumaríssimo';
            } else {
                ritoCorreto = 'Ordinário';
            }
            
            detalhe += `Rito correto calculado: ${ritoCorreto}\n`;
            
            if (ritoDeclarado === ritoCorreto) {
                alerta = '✅ Rito processual corretamente definido.';
            } else {
                alerta = `🔔 ALERTA: Rito declarado (${ritoDeclarado}) incompatível. Rito correto: ${ritoCorreto}.`;
            }
        } else {
            alerta = '⚠️ ATENÇÃO: Valor da causa não informado - impossível validar rito processual.';
        }
        
        return {alerta, trecho: ritoDeclarado, detalhe};
    }

    // BLOCO 13: Verificação de Menção ao Art. 611-B da CLT
    function analisarArt611BCLT(texto) {
        let mencaoArt611B = /art\.?\s*611\-?B|artigo 611\-?B|611\-?B.*CLT/i.test(texto);
        
        let detalhe = `Menção ao art. 611-B da CLT: ${mencaoArt611B ? 'Encontrada' : 'Não encontrada'}\n`;
        
        let alerta = '';
        if (mencaoArt611B) {
            alerta = '🔔 ALERTA: Menção ao art. 611-B da CLT - colocar lembrete no processo.';
        } else {
            alerta = '✅ Sem menção ao art. 611-B da CLT.';
        }
        
        return {alerta, trecho: mencaoArt611B ? 'Art. 611-B mencionado' : '', detalhe};
    }

    // BLOCO 14: Validador de Consistência Jurídica Interna
    function validarConsistenciaInterna(todosResultados) {
        let consistencias = [];
          // Analisa cada resultado anterior
        let cepOK = todosResultados[0]?.result?.alerta?.includes('✅') || false;
        let ritoOK = todosResultados[11]?.result?.alerta?.includes('✅') || false;
        let tutelaPresente = todosResultados[4]?.result?.alerta?.includes('🔔') || false;
        let enderecoForaSP = todosResultados[10]?.result?.alerta?.includes('fora do município') || false;
        let audienciaVirtual = todosResultados[10]?.result?.alerta?.includes('virtual') || false;
        let outrosProcessos = todosResultados[8]?.result?.alerta?.includes('🔔') || false;
        let art611B = todosResultados[12]?.result?.alerta?.includes('🔔') || false;
        let responsabilidadeProblema = todosResultados[9]?.result?.alerta?.includes('🔔') || false;
        let procuracaoProblema = todosResultados[13]?.result?.alerta?.includes('🔔') || false;
        
        consistencias.push({
            item: 'CEP compatível com jurisdição territorial',
            situacao: cepOK ? 'Sim' : 'Não',
            resultado: cepOK ? '✅ OK' : '❌ Inconsistente'
        });
        
        consistencias.push({
            item: 'Rito compatível com valor da causa',
            situacao: ritoOK ? 'Sim' : 'Não',
            resultado: ritoOK ? '✅ OK' : '❌ Inconsistente'
        });
        
        consistencias.push({
            item: 'Presença de pedido de tutela provisória',
            situacao: tutelaPresente ? 'Sim' : 'Não',
            resultado: tutelaPresente ? '⚠️ Requer providência' : '✅ Ausente'
        });
        
        consistencias.push({
            item: 'Endereço do reclamante fora do município de SP',
            situacao: enderecoForaSP ? 'Sim' : 'Não',
            resultado: enderecoForaSP ? '⚠️ Verificar audiência virtual' : '✅ OK'
        });
        
        consistencias.push({
            item: 'Pedido de audiência virtual/telepresencial/híbrida',
            situacao: audienciaVirtual ? 'Sim' : 'Não',
            resultado: audienciaVirtual ? '⚠️ Avaliar viabilidade logística' : '✅ OK'
        });
        
        consistencias.push({
            item: 'Possível litispendência ou prevenção',
            situacao: outrosProcessos ? 'Sim' : 'Não',
            resultado: outrosProcessos ? '⚠️ Verificar necessidade de redistribuição' : '✅ OK'
        });
        
        consistencias.push({
            item: 'Menção ao art. 611-B da CLT',
            situacao: art611B ? 'Sim' : 'Não',
            resultado: art611B ? '⚠️ Colocar lembrete' : '✅ Não'
        });
          consistencias.push({
            item: 'Responsabilidade Subsidiária/Solidária sem fundamentação',
            situacao: responsabilidadeProblema ? 'Sim' : 'Não',
            resultado: responsabilidadeProblema ? '⚠️ Emenda necessária' : '✅ OK'
        });
        
        consistencias.push({
            item: 'Procuração adequada (presente, assinada digitalmente, outorgante correto)',
            situacao: procuracaoProblema ? 'Não' : 'Sim',
            resultado: procuracaoProblema ? '⚠️ Verificar procuração' : '✅ OK'
        });
        
        let tabelaMarkdown = '| Consistência Avaliada | Situação Encontrada | Resultado |\n';
        tabelaMarkdown += '|---|---|---|\n';
        
        for (let c of consistencias) {
            tabelaMarkdown += `| ${c.item} | ${c.situacao} | ${c.resultado} |\n`;
        }
        
        let problemasEncontrados = consistencias.filter(c => c.resultado.includes('❌') || c.resultado.includes('⚠️'));
        
        let alerta = '';
        if (problemasEncontrados.length === 0) {
            alerta = '✅ Consistência jurídica interna verificada - petição adequada para prosseguimento.';
        } else {
            alerta = `🔔 ALERTA: ${problemasEncontrados.length} inconsistência(s) identificada(s) - verificar necessidade de emenda ou providências.`;
        }
        
        return {
            alerta,
            trecho: `${problemasEncontrados.length} problema(s) encontrado(s)`,
            detalhe: `Tabela de Consistência:\n${tabelaMarkdown}\n\nProblemas: ${problemasEncontrados.map(p => p.item).join(', ')}`
        };
    }

    // Mapeamento de todas as análises (14 blocos)    // Função para salvar arquivo
    function salvarArquivo(conteudo, nomeArquivo, tipo) {
        const blob = new Blob([conteudo], {type: tipo});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nomeArquivo;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
    }

    // Gera relatório em texto
    function gerarRelatorioTexto(resultados) {
        let relatorio = '';
        relatorio += '='.repeat(80) + '\n';
        relatorio += 'RELATÓRIO COMPLETO DE TRIAGEM - PETIÇÃO INICIAL TRABALHISTA\n';
        relatorio += 'Fórum Trabalhista da Zona Sul de São Paulo/SP\n';
        relatorio += 'Data: ' + new Date().toLocaleString('pt-BR') + '\n';
        relatorio += '='.repeat(80) + '\n\n';
        
        // Resumo executivo
        let alertas = resultados.filter(r => r.status === 'ALERTA').length;
        let atencoes = resultados.filter(r => r.status === 'ATENÇÃO').length;
        let oks = resultados.filter(r => r.status === 'OK').length;
        
        relatorio += 'RESUMO EXECUTIVO:\n';
        relatorio += `-`.repeat(50) + '\n';
        relatorio += `Total de análises realizadas: ${resultados.length}\n`;
        relatorio += `🔔 Alertas críticos: ${alertas}\n`;
        relatorio += `⚠️ Atenções/Verificações: ${atencoes}\n`;
        relatorio += `✅ Itens conformes: ${oks}\n\n`;
        
        // Detalhes por bloco
        relatorio += 'ANÁLISE DETALHADA POR BLOCO:\n';
        relatorio += '='.repeat(50) + '\n\n';
        
        for (let resultado of resultados) {
            relatorio += `BLOCO ${resultado.bloco} - ${resultado.nome.toUpperCase()}\n`;
            relatorio += `Status: ${resultado.status}\n`;
            relatorio += `Resultado: ${resultado.result.alerta}\n`;
            if (resultado.result.trecho) {
                relatorio += `Trecho relevante: ${resultado.result.trecho}\n`;
            }
            if (resultado.result.detalhe) {
                relatorio += `Detalhes:\n${resultado.result.detalhe}\n`;
            }
            relatorio += '-'.repeat(50) + '\n\n';
        }
        
        // Adiciona validação de consistência interna
        let consistencia = validarConsistenciaInterna(resultados);
        relatorio += 'VALIDAÇÃO DE CONSISTÊNCIA JURÍDICA INTERNA:\n';
        relatorio += '='.repeat(50) + '\n';
        relatorio += `Resultado: ${consistencia.alerta}\n`;
        relatorio += `${consistencia.detalhe}\n\n`;
        
        relatorio += '='.repeat(80) + '\n';
        relatorio += 'FIM DO RELATÓRIO\n';
        relatorio += '='.repeat(80) + '\n';
          return relatorio;
    }

    // Cria tabela de relatório completo
    function mostrarRelatorioCompleto(resultados) {
        let html = `<div style="color:white;font-size:14px;">`;
        
        // Resumo
        let alertas = resultados.filter(r => r.status === 'ALERTA').length;
        let atencoes = resultados.filter(r => r.status === 'ATENÇÃO').length;
        let oks = resultados.filter(r => r.status === 'OK').length;
        
        html += `<div style="background:#1e40af;padding:8px;border-radius:4px;margin-bottom:10px;">`;
        html += `<strong>📊 RESUMO:</strong> ${resultados.length} análises | `;
        html += `🔔 ${alertas} alertas | ⚠️ ${atencoes} atenções | ✅ ${oks} OK`;
        html += `</div>`;
        
        // Tabela principal
        html += `<table style="width:100%;border-collapse:collapse;font-size:13px;background:#1e3a8a !important;">
            <tr style="background:#1e40af !important;color:white;">
                <th style="color:white;padding:6px;border:1px solid #3b82f6;">Bloco</th>
                <th style="color:white;padding:6px;border:1px solid #3b82f6;">Análise</th>
                <th style="color:white;padding:6px;border:1px solid #3b82f6;">Status</th>
                <th style="color:white;padding:6px;border:1px solid #3b82f6;">Resultado</th>
            </tr>`;
            
        for (let r of resultados) {
            let statusColor = '';
            if (r.status === 'ALERTA') statusColor = '#dc2626';
            else if (r.status === 'ATENÇÃO') statusColor = '#f59e0b';
            else if (r.status === 'OK') statusColor = '#059669';
            
            html += `<tr style="background:#1e3a8a !important;color:white;">
                <td style="color:white;padding:4px;border:1px solid #3b82f6;text-align:center;">${r.bloco}</td>
                <td style="color:white;padding:4px;border:1px solid #3b82f6;">${r.nome}</td>
                <td style="color:white;padding:4px;border:1px solid #3b82f6;background:${statusColor};text-align:center;">${r.status}</td>
                <td style="color:white;padding:4px;border:1px solid #3b82f6;font-size:12px;">${r.result.alerta}</td>
            </tr>`;
            
            if (r.result.trecho || r.result.detalhe) {
                html += `<tr style="background:#1e40af !important;color:white;">
                    <td colspan="4" style="color:#bfdbfe;padding:4px;font-size:11px;border:1px solid #3b82f6;">`;
                if (r.result.trecho) html += `<strong>Trecho:</strong> ${r.result.trecho}<br>`;
                if (r.result.detalhe) html += `<strong>Detalhes:</strong><br><pre style="white-space:pre-wrap;font-size:10px;margin:2px 0;">${r.result.detalhe}</pre>`;
                html += `</td></tr>`;
            }
        }
        
        html += `</table>`;
          // Adiciona consistência interna
        let consistencia = validarConsistenciaInterna(resultados);
        html += `<div style="margin-top:15px;padding:10px;background:#1e40af;border-radius:4px;">`;
        html += `<strong>🔍 CONSISTÊNCIA JURÍDICA INTERNA:</strong><br>`;
        html += `${consistencia.alerta}<br>`;
        html += `<small style="color:#bfdbfe;">${consistencia.trecho}</small>`;
        html += `</div>`;
        
        html += `</div>`;
        
        const tabelaEl = document.getElementById('trg-table-v3');
        if (tabelaEl) {
            tabelaEl.innerHTML = html;
        } else {
            console.error('Elemento trg-table-v3 não encontrado - interface pode ter sido removida');
        }
    }

    // Função para selecionar apenas Petição Inicial e Procuração
    function selecionarDocumentosEspecificos(janela) {
        try {
            console.log('Iniciando seleção de documentos específicos...');
            
            // 1. Primeiro desmarcar todos
            const checkboxTodos = janela.document.getElementById('tbdownloadDocumentos:downloadDocumentosModal_checkAll');
            if (checkboxTodos && checkboxTodos.checked) {
                console.log('Desmarcando todos os checkboxes...');
                checkboxTodos.click();
            }
            
            // 2. Aguarda um pouco e seleciona apenas os documentos desejados
            setTimeout(() => {
                const tabela = janela.document.getElementById('tbdownloadDocumentos');
                if (!tabela) {
                    console.error('Tabela de documentos não encontrada');
                    return;
                }
                
                // Busca por linhas que contenham "Petição Inicial" ou "Procuração"
                const linhas = tabela.querySelectorAll('tbody tr');
                let documentosSelecionados = 0;
                
                linhas.forEach((linha, index) => {
                    const textoDocumento = linha.querySelector('.texto-doc');
                    if (textoDocumento) {
                        const texto = textoDocumento.textContent.trim();
                        
                        // Verifica se é Petição Inicial ou Procuração
                        if (texto.toLowerCase().includes('petição inicial') || 
                            texto.toLowerCase().includes('procuração')) {
                            
                            const checkbox = linha.querySelector('input[type="checkbox"][name*="selecaoBox"]');
                            if (checkbox && !checkbox.checked) {
                                console.log(`Selecionando: ${texto}`);
                                checkbox.click();
                                documentosSelecionados++;
                            }
                        }
                    }
                });
                
                console.log(`${documentosSelecionados} documentos selecionados`);
                
                // 3. Clica no botão "Gerar PDF"
                setTimeout(() => {
                    const botaoGerar = janela.document.getElementById('j_id157:botaoDownloadDocumentos');
                    if (botaoGerar) {
                        console.log('Clicando em "Gerar PDF"...');
                        botaoGerar.click();
                        console.log('PDF sendo gerado...');
                    } else {
                        console.error('Botão "Gerar PDF" não encontrado');
                    }
                }, 1000); // Aguarda 1 segundo antes de gerar
                
            }, 500); // Aguarda 500ms após desmarcar todos
            
        } catch (error) {
            console.error('Erro ao selecionar documentos:', error);
        }
    }

    // Função para automação na página de download
    function executarAutomacaoDownload() {
        console.log('🤖 Executando automação na página de download...');
        
        // Verifica se há instrução para executar automação
        const shouldAutomate = localStorage.getItem('pje_automate_download');
        if (!shouldAutomate) {
            console.log('Nenhuma instrução de automação encontrada');
            return;
        }
        
        // Remove a instrução (executa uma vez)
        localStorage.removeItem('pje_automate_download');
        
        // Aguarda carregar e executa
        setTimeout(() => {
            // 1. Clica no ícone PDF
            const iconePdf = document.querySelector('img[src="/primeirograu/img/cp/pdf.png"]');
            if (iconePdf) {
                console.log('📄 Clicando no ícone PDF...');
                iconePdf.click();
                
                // 2. Aguarda modal carregar e executa seleção
                setTimeout(() => {
                    executarSelecaoDocumentos();
                }, 3000);
                
            } else {
                console.error('❌ Ícone PDF não encontrado');
            }
        }, 2000);
    }
    
    // Função para seleção automática de documentos
    function executarSelecaoDocumentos() {
        console.log('📋 Executando seleção de documentos...');
        
        try {
            // 1. Desmarcar todos
            const checkboxTodos = document.getElementById('tbdownloadDocumentos:downloadDocumentosModal_checkAll');
            if (checkboxTodos && checkboxTodos.checked) {
                console.log('☑️ Desmarcando todos...');
                checkboxTodos.click();
                
                // 2. Aguarda e seleciona específicos
                setTimeout(() => {
                    selecionarPeticaoEProcuracao();
                }, 1000);
            } else {
                // Se já está desmarcado, vai direto
                selecionarPeticaoEProcuracao();
            }
        } catch (error) {
            console.error('❌ Erro na seleção:', error);
        }
    }
    
    // Função para selecionar apenas Petição e Procuração
    function selecionarPeticaoEProcuracao() {
        const tabela = document.getElementById('tbdownloadDocumentos');
        if (!tabela) {
            console.error('❌ Tabela não encontrada');
            return;
        }
        
        const linhas = tabela.querySelectorAll('tbody tr');
        let selecionados = 0;
        
        linhas.forEach(linha => {
            const textoDoc = linha.querySelector('.texto-doc');
            if (textoDoc) {
                const texto = textoDoc.textContent.trim().toLowerCase();
                
                if (texto.includes('petição inicial') || texto.includes('procuração')) {
                    const checkbox = linha.querySelector('input[type="checkbox"][name*="selecaoBox"]');
                    if (checkbox && !checkbox.checked) {
                        console.log(`✅ Selecionando: ${textoDoc.textContent.trim()}`);
                        checkbox.click();
                        selecionados++;
                    }
                }
            }
        });
        
        console.log(`📊 ${selecionados} documentos selecionados`);
        
        // 3. Gerar PDF
        setTimeout(() => {
            const botaoGerar = document.getElementById('j_id157:botaoDownloadDocumentos');
            if (botaoGerar) {
                console.log('🔄 Gerando PDF...');
                botaoGerar.click();
                
                // Notifica sucesso
                setTimeout(() => {
                    localStorage.setItem('pje_pdf_status', 'generated');
                    console.log('✅ PDF gerado com sucesso!');
                }, 2000);
                
            } else {
                console.error('❌ Botão Gerar PDF não encontrado');
            }
        }, 1000);
    }
      // Função para inicializar página de detalhe
    function inicializarPaginaDetalhe() {
        console.log('🏠 Inicializando página de detalhe...');
        
        // Carrega PDF.js e depois cria interface
        loadPdfJs(() => {
            console.log('PDF.js carregado, criando interface...');
            
            // Tenta criar imediatamente
            if (!tryCreateInterface()) {
                console.log('Interface V3 não encontrada, observando mudanças no DOM...');
                
                let observer = new MutationObserver(() => {
                    if (tryCreateInterface()) {
                        console.log('Interface V3 criada após mudança no DOM');
                        observer.disconnect();
                    }
                });
                
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
                
                // Para de observar após 10 segundos
                setTimeout(() => {
                    observer.disconnect();
                    console.log('Parou de observar DOM V3, adicionando ativação manual');
                }, 10000);
            }
            
            // Ativação manual com Ctrl+Shift+R
            document.addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.shiftKey && e.key === 'R') {
                    console.log('Ativação manual V3 detectada');
                    createUI();
                }
            });
        });
    }    // BLOCO 15: Análise de Procuração
    function analisarProcuracao(texto) {
        let alertas = [];
        
        // 1. REGRA: Confirmar se há procuração
        let temProcuracao = /procura[çc][ãa]o/i.test(texto);
        
        // 2. REGRA: Ver se há assinatura digital do advogado outorgado
        let assinaturaDigital = /assinatura\s+digital|assinado\s+digitalmente|certificado\s+digital|ICP-Brasil|documento\s+eletr[ôo]nico|hash|timestamp/i.test(texto);
        
        // 3. REGRA: Verificar se outorgante é exatamente o reclamante da capa
        // Primeiro identifica o reclamante na capa
        let reclamanteCapa = '';
        let matchReclamante = texto.match(/RECLAMANTE:\s*([^-\n]+?)(?:\s*-\s*CPF:|$)/i);
        if (matchReclamante) {
            reclamanteCapa = matchReclamante[1].trim();
        }
        
        // Busca por outorgante na procuração
        let outorgante = '';
        let matchOutorgante = texto.match(/outorgante[:\s]*([^,\n]+?)(?:\s*,|\s*CPF|\s*RG|$)/i);
        if (matchOutorgante) {
            outorgante = matchOutorgante[1].trim();
        }
        
        // Verifica se outorgante corresponde ao reclamante
        let outorganteCorreto = false;
        if (reclamanteCapa && outorgante) {
            // Normaliza nomes para comparação (remove acentos, maiúsculas, espaços extras)
            let reclamanteNorm = reclamanteCapa.toLowerCase().replace(/[áàâãä]/g, 'a').replace(/[éèêë]/g, 'e').replace(/[íìîï]/g, 'i').replace(/[óòôõö]/g, 'o').replace(/[úùûü]/g, 'u').replace(/[ç]/g, 'c').replace(/\s+/g, ' ').trim();
            let outorganteNorm = outorgante.toLowerCase().replace(/[áàâãä]/g, 'a').replace(/[éèêë]/g, 'e').replace(/[íìîï]/g, 'i').replace(/[óòôõö]/g, 'o').replace(/[úùûü]/g, 'u').replace(/[ç]/g, 'c').replace(/\s+/g, ' ').trim();
            
            outorganteCorreto = reclamanteNorm.includes(outorganteNorm) || outorganteNorm.includes(reclamanteNorm);
        }
        
        // Monta detalhes da análise
        let detalhe = `1. Procuração presente: ${temProcuracao ? 'Sim' : 'Não'}\n`;
        detalhe += `2. Assinatura digital detectada: ${assinaturaDigital ? 'Sim' : 'Não'}\n`;
        detalhe += `3. Reclamante na capa: "${reclamanteCapa || 'Não identificado'}"\n`;
        detalhe += `   Outorgante na procuração: "${outorgante || 'Não identificado'}"\n`;
        detalhe += `   Correspondência: ${outorganteCorreto ? 'Sim' : 'Não'}\n`;
        
        // Análise e alertas das 3 regras específicas
        if (!temProcuracao) {
            alertas.push('Procuração não localizada');
        }
        
        if (temProcuracao && !assinaturaDigital) {
            alertas.push('Assinatura digital do advogado não detectada');
        }
        
        if (temProcuracao && !outorganteCorreto) {
            alertas.push('Outorgante na procuração não corresponde ao reclamante da capa');
        }
        
        // Monta resultado
        let alerta = '';
        let trecho = '';
        
        if (alertas.length > 0) {
            alerta = '🔔 ALERTA: ' + alertas.join('; ') + ' - verificar procuração.';
            trecho = alertas.join(', ');
        } else {
            alerta = '✅ Procuração adequada: presente, assinada digitalmente e outorgante correto.';
            trecho = `Outorgante: ${outorgante}`;
        }
        
        return {alerta, trecho, detalhe};
    }

})();
