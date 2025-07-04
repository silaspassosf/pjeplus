// ==UserScript==
// @name         Documentos Execução - OTIMIZADO
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Identifica e lista documentos específicos da timeline de execução do PJe - VERSÃO OTIMIZADA
// @author       PjePlus
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('[DOCS-EXEC] Script OTIMIZADO iniciado');
    
    // Função para verificar se a página contém a timeline
    function verificarPagina() {
        const url = window.location.href;
        const timeline = document.querySelector('pje-timeline, .tl-data');
        return url.includes('/detalhe') && !!timeline;
    }
    
    // Criar botão de ativação
    function criarBotaoCheck() {
        console.log('[DOCS-EXEC] Criando botão...');
        
        // Verificar se o botão já existe
        const botaoExistente = document.getElementById('btnDocsExecucao');
        if (botaoExistente) {
            botaoExistente.remove();
        }
        
        try {
            const botao = document.createElement('button');
            botao.id = 'btnDocsExecucao';
            botao.textContent = '📋 Check';
            
            botao.style.cssText = `
                position: fixed !important;
                bottom: 80px !important;
                right: 20px !important;
                z-index: 99999 !important;
                background-color: #007bff !important;
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
                this.style.backgroundColor = '#0056b3 !important';
                this.style.transform = 'scale(1.05) translateY(-2px)';
                this.style.boxShadow = '0 6px 20px rgba(0,0,0,0.4) !important';
            });
            
            botao.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '#007bff !important';
                this.style.transform = 'scale(1) translateY(0)';
                this.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3) !important';
            });
            
            // Evento de clique
            botao.addEventListener('click', function() {
                console.log('[DOCS-EXEC] Botão clicado');
                executarAnaliseTimeline();
            });
            
            document.body.appendChild(botao);
            console.log('[DOCS-EXEC] ✅ Botão criado com sucesso');
            return true;
            
        } catch (error) {
            console.error('[DOCS-EXEC] Erro ao criar botão:', error);
            return false;
        }
    }
    
    // Função para ler a timeline completa (com data e Decisão Sobrestamento)
    function lerTimelineCompleta() {
        console.log('[DOCS-EXEC] Lendo timeline...');
        const seletoresTimeline = [
            'li.tl-item-container',
            '.tl-data .tl-item-container',
            '.timeline-item'
        ];
        let itens = [];
        for (const seletor of seletoresTimeline) {
            itens = document.querySelectorAll(seletor);
            if (itens.length > 0) {
                console.log(`[DOCS-EXEC] Encontrados ${itens.length} itens com: ${seletor}`);
                break;
            }
        }
        if (itens.length === 0) {
            console.log('[DOCS-EXEC] Nenhum item encontrado na timeline');
            return [];
        }
        const documentos = [];
        function extrairUidDocumento(link) {
            try {
                const nomeCompleto = link.textContent.trim();
                const match = nomeCompleto.match(/\s-\s([a-zA-Z0-9]+)$/);
                if (match && match[1]) return match[1];
                const fallbackMatch = nomeCompleto.match(/([a-zA-Z0-9]{6,})$/);
                if (fallbackMatch && fallbackMatch[1]) return fallbackMatch[1];
                return null;
            } catch (e) { return null; }
        }
        // Função para extrair data do item da timeline (padrão Lista_Exec)
        function extrairDataItem(item) {
            try {
                // Estratégia 1: Buscar o elemento .tl-data que está ACIMA do documento atual
                let dataElement = null;
                dataElement = item.querySelector('.tl-data[name="dataItemTimeline"]');
                if (!dataElement) {
                    dataElement = item.querySelector('.tl-data');
                }
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
                if (dataElement) {
                    const dataTexto = dataElement.textContent.trim();
                    const dataConvertida = converterDataTextoParaNumerico(dataTexto);
                    if (dataConvertida) return dataConvertida;
                    const matchData = dataTexto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
                    if (matchData) return matchData[1];
                }
                const textoCompleto = item.textContent;
                const matchDataFallback = textoCompleto.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
                if (matchDataFallback) return matchDataFallback[1];
                return '';
            } catch (e) {
                return '';
            }
        }
        // Função auxiliar para converter texto de data (ex: "01 mar. 2019") para formato numérico (ex: "01/03/2019")
        function converterDataTextoParaNumerico(dataTexto) {
            try {
                const meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                };
                const match = dataTexto.match(/(\d{1,2})\s+(\w{3})\.?\s+(\d{4})/);
                if (match) {
                    const dia = match[1].padStart(2, '0');
                    const mesTexto = match[2].toLowerCase();
                    const ano = match[3];
                    const mesNumero = meses[mesTexto];
                    if (mesNumero) {
                        return `${dia}/${mesNumero}/${ano}`;
                    }
                }
                return null;
            } catch (e) {
                return null;
            }
        }
        itens.forEach((item, index) => {
            try {
                const link = item.querySelector('a.tl-documento:not([target="_blank"])');
                let data = extrairDataItem(item); // <-- aqui
                if (link) {
                    const textoDoc = link.textContent.trim().toLowerCase();
                    const documentosAlvo = [
                        { nome: 'Alvará', termos: ['alvará', 'alvara'] },
                        { nome: 'Certidão de pesquisa patrimonial', termos: ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial'] },
                        { nome: 'Carta Ação', termos: ['carta ação', 'carta acao', 'carta de ação'] },
                        { nome: 'Serasa', termos: ['serasa'] },
                        { nome: 'CNIB', termos: ['cnib'] },
                        { nome: 'Decisão (Sobrestamento)', termos: ['decisão de sobrestamento', 'decisao de sobrestamento', 'decisão (sobrestamento)', 'decisao (sobrestamento)'] }
                    ];
                    for (const docTipo of documentosAlvo) {
                        const encontrado = docTipo.termos.some(termo => textoDoc.includes(termo));
                        if (encontrado) {
                            const uid = extrairUidDocumento(link);
                            const documentoId = uid || `doc-${index}`;
                            documentos.push({
                                tipo: docTipo.nome,
                                texto: link.textContent.trim(),
                                id: documentoId,
                                elemento: item,
                                link: link,
                                index: index,
                                tipoItem: 'documento',
                                data: data
                            });
                            break;
                        }
                    }
                }
                const btnAnexos = item.querySelector('pje-timeline-anexos > div > div');
                if (btnAnexos && link && link.textContent.toLowerCase().includes('pesquisa patrimonial')) {
                    const uid = extrairUidDocumento(link);
                    const anexoId = uid ? `anexos-${uid}` : `anexos-${index}`;
                    documentos.push({
                        tipo: 'Anexos da Pesquisa Patrimonial',
                        texto: `Anexos: ${link.textContent.trim()}`,
                        id: anexoId,
                        elemento: item,
                        link: btnAnexos,
                        index: index,
                        tipoItem: 'anexos',
                        documentoPai: link.textContent.trim(),
                        data: data
                    });
                }
            } catch (e) {}
        });
        return documentos;
    }

    // Função para gerar e exibir lista simples (Alvarás no topo, demais por data)
    function gerarListaSimples(documentos) {
        const listaExistente = document.getElementById('listaDocsExecucaoSimples');
        if (listaExistente) listaExistente.remove();
        // Ordenação: alvarás no topo, depois por data decrescente (mais recente primeiro)
        const alvaras = documentos.filter(d => d.tipo === 'Alvará');
        const outros = documentos.filter(d => d.tipo !== 'Alvará');
        function parseData(dt) {
            if (!dt) return 0;
            const p = dt.split('/');
            if (p.length < 3) return 0;
            let y = p[2].length === 2 ? '20'+p[2] : p[2];
            return parseInt(y+p[1].padStart(2,'0')+p[0].padStart(2,'0'));
        }
        outros.sort((a,b) => parseData(b.data)-parseData(a.data));
        const docsOrdenados = [...alvaras, ...outros];
        const container = document.createElement('div');
        container.id = 'listaDocsExecucaoSimples';
        container.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 100000;
            background: #fff;
            border: 2px solid #007bff;
            border-radius: 10px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.18);
            min-width: 340px;
            max-width: 90vw;
            max-height: 70vh;
            overflow-y: auto;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        const btnFechar = document.createElement('button');
        btnFechar.innerHTML = '✕';
        btnFechar.style.cssText = `position: absolute; top: 8px; right: 12px; background: #dc3545; color: #fff; border: none; border-radius: 50%; width: 28px; height: 28px; font-size: 15px; font-weight: bold; cursor: pointer; z-index: 2;`;
        btnFechar.onclick = () => container.remove();
        container.appendChild(btnFechar);
        const tabela = document.createElement('table');
        tabela.style.cssText = 'width: 100%; border-collapse: collapse; margin-top: 0;';
        const tbody = document.createElement('tbody');
        docsOrdenados.forEach((doc, idx) => {
            const tr = document.createElement('tr');
            tr.style.cssText = `cursor:pointer; border-bottom:1px solid #e0e0e0; transition:background 0.2s;`;
            tr.addEventListener('mouseenter', () => tr.style.background = '#e7f3ff');
            tr.addEventListener('mouseleave', () => tr.style.background = '');
            tr.onclick = () => selecionarDocumentoTimeline(doc, tr);
            // Descrição
            const tdDesc = document.createElement('td');
            tdDesc.textContent = doc.texto;
            tdDesc.style.cssText = 'padding: 10px 8px; color: #222; font-size: 15px;';
            tr.appendChild(tdDesc);
            // Data
            const tdData = document.createElement('td');
            tdData.textContent = doc.data || '';
            tdData.style.cssText = 'padding: 10px 8px; color: #555; font-size: 13px; text-align:center; min-width:80px;';
            tr.appendChild(tdData);
            // ID
            const tdId = document.createElement('td');
            tdId.textContent = doc.id;
            tdId.style.cssText = 'padding: 10px 8px; color: #888; font-size: 13px; text-align:right; min-width:90px;';
            tr.appendChild(tdId);
            tbody.appendChild(tr);
        });
        tabela.appendChild(tbody);
        container.appendChild(tabela);
        document.body.appendChild(container);
        tornarListaMovelEPequena(container);
    }

    // Função para localizar documento na timeline (padrão Lista_Exec)
    function selecionarDocumentoTimeline(documento, tr) {
        try {
            // Remove destaque anterior
            document.querySelectorAll('.doc-exec-destaque').forEach(el => el.classList.remove('doc-exec-destaque'));
            documento.elemento.classList.add('doc-exec-destaque');
            documento.elemento.scrollIntoView({behavior:'smooth', block:'center'});
            // Piscar destaque
            let piscar = 0;
            const intervalo = setInterval(() => {
                documento.elemento.style.opacity = piscar % 2 === 0 ? '0.7' : '1';
                piscar++;
                if (piscar > 6) {
                    clearInterval(intervalo);
                    documento.elemento.style.opacity = '1';
                }
            }, 300);
            setTimeout(() => {
                documento.elemento.classList.remove('doc-exec-destaque');
            }, 4000);
        } catch (e) {
            console.error('[DOCS-EXEC] Erro ao localizar documento:', e);
        }
    }
    // Adiciona estilo para destaque
    const style = document.createElement('style');
    style.innerHTML = `.doc-exec-destaque { outline: 3px solid #007bff !important; background: #e7f3ff !important; transition: outline 0.2s, background 0.2s; }`;
    document.head.appendChild(style);
    
    // Função principal de análise
    function executarAnaliseTimeline() {
        try {
            console.log('[DOCS-EXEC] Executando análise...');
            const botao = document.getElementById('btnDocsExecucao');
            const textoOriginal = botao.textContent;
            botao.textContent = '⏳ Analisando...';
            botao.style.backgroundColor = '#ffc107';
            // Ler timeline e gerar lista simples
            const documentos = lerTimelineCompleta();
            gerarListaSimples(documentos);
            setTimeout(() => {
                botao.textContent = textoOriginal;
                botao.style.backgroundColor = '#007bff';
            }, 1200);
        } catch (e) {
            console.error('[DOCS-EXEC] Erro na análise:', e);
            alert('Erro durante a análise: ' + e.message);
            const botao = document.getElementById('btnDocsExecucao');
            if (botao) {
                botao.textContent = '❌ Erro';
                botao.style.backgroundColor = '#dc3545';
                setTimeout(() => {
                    botao.textContent = '📋 Check';
                    botao.style.backgroundColor = '#007bff';
                }, 3000);
            }
        }
    }
    
    // INICIALIZAÇÃO SIMPLIFICADA E DIRETA
    function inicializar() {
        console.log('[DOCS-EXEC] Inicializando...');
        
        // Verificar apenas a URL primeiro
        if (window.location.href.includes('/detalhe')) {
            console.log('[DOCS-EXEC] ✅ URL válida (/detalhe), criando botão...');
            criarBotaoCheck();
        } else {
            console.log('[DOCS-EXEC] ❌ URL não contém /detalhe');
        }
    }
    
    // Executar IMEDIATAMENTE se a página já carregou
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log('[DOCS-EXEC] Página já carregada, executando imediatamente');
        inicializar();
    } else {
        // Se ainda está carregando, aguardar
        console.log('[DOCS-EXEC] Aguardando carregamento da página');
        document.addEventListener('DOMContentLoaded', inicializar);
    }
    
    // Torna a lista móvel e reduzida
    function tornarListaMovelEPequena(container) {
        // Reduz tamanho
        container.style.transform = 'scale(0.6)';
        container.style.transformOrigin = 'bottom right';
        container.style.maxWidth = '600px';
        container.style.fontSize = '12px';
        // Drag and drop melhorado
        let isDragging = false, startX, startY, startLeft, startTop;
        container.style.cursor = 'grab';
        let mouseMoveHandler, mouseUpHandler;
        container.addEventListener('mousedown', function(e) {
            if (e.target.tagName === 'BUTTON') return; // não arrasta ao clicar botão fechar
            isDragging = true;
            container.style.cursor = 'grabbing';
            startX = e.clientX;
            startY = e.clientY;
            const rect = container.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            document.body.style.userSelect = 'none';
            // Adiciona listeners apenas durante o drag
            mouseMoveHandler = function(e) {
                if (!isDragging) return;
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                container.style.left = (startLeft + dx) + 'px';
                container.style.top = (startTop + dy) + 'px';
                container.style.right = 'auto';
                container.style.bottom = 'auto';
            };
            mouseUpHandler = function() {
                isDragging = false;
                container.style.cursor = 'grab';
                document.body.style.userSelect = '';
                document.removeEventListener('mousemove', mouseMoveHandler);
                document.removeEventListener('mouseup', mouseUpHandler);
            };
            document.addEventListener('mousemove', mouseMoveHandler);
            document.addEventListener('mouseup', mouseUpHandler);
        });
    }
})();
