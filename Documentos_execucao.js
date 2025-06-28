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
    
    // Função para ler a timeline completa
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
        
        // Função para extrair UID do nome completo
        function extrairUidDocumento(link) {
            try {
                const nomeCompleto = link.textContent.trim();
                // Buscar padrão " - [códigoUID]" no final do nome
                const match = nomeCompleto.match(/\s-\s([a-zA-Z0-9]+)$/);
                if (match && match[1]) {
                    console.log(`[DOCS-EXEC] UID extraído: ${match[1]} do nome: ${nomeCompleto}`);
                    return match[1];
                }
                
                // Fallback: buscar qualquer código alfanumérico no final
                const fallbackMatch = nomeCompleto.match(/([a-zA-Z0-9]{6,})$/);
                if (fallbackMatch && fallbackMatch[1]) {
                    console.log(`[DOCS-EXEC] UID extraído (fallback): ${fallbackMatch[1]} do nome: ${nomeCompleto}`);
                    return fallbackMatch[1];
                }
                
                console.log(`[DOCS-EXEC] Nenhum UID encontrado no nome: ${nomeCompleto}`);
                return null;
            } catch (e) {
                console.error('[DOCS-EXEC] Erro ao extrair UID:', e);
                return null;
            }
        }
        
        itens.forEach((item, index) => {
            try {
                // Primeiro, verificar se há link de documento principal
                const link = item.querySelector('a.tl-documento:not([target="_blank"])');
                
                if (link) {
                    const textoDoc = link.textContent.trim().toLowerCase();
                    console.log(`[DOCS-EXEC] Item ${index}: "${link.textContent.trim()}"`);
                    
                    // Verificar se é um dos documentos alvo
                    const documentosAlvo = [
                        { nome: 'Alvará', termos: ['alvará', 'alvara'] },
                        { nome: 'Certidão de pesquisa patrimonial', termos: ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial'] },
                        { nome: 'Carta Ação', termos: ['carta ação', 'carta acao', 'carta de ação'] },
                        { nome: 'Serasa', termos: ['serasa'] },
                        { nome: 'CNIB', termos: ['cnib'] }
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
                                tipoItem: 'documento'
                            });
                            console.log(`[DOCS-EXEC] ✅ ${docTipo.nome}: ${link.textContent.trim()}`);
                            break;
                        }
                    }
                }
                
                // Verificar se há botão de anexos (seguindo a lógica do m1.py)
                const btnAnexos = item.querySelector('pje-timeline-anexos > div > div');
                if (btnAnexos) {
                    console.log(`[DOCS-EXEC] Item ${index}: encontrado botão de anexos`);
                    
                    // Se o documento principal contém "pesquisa patrimonial", anexos são relevantes
                    if (link && link.textContent.toLowerCase().includes('pesquisa patrimonial')) {
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
                            documentoPai: link.textContent.trim()
                        });
                        console.log(`[DOCS-EXEC] ✅ Anexos de Pesquisa Patrimonial: ${link.textContent.trim()}`);
                    }
                    // Verificar se os anexos contêm documentos relevantes (mesmo sem documento pai)
                    else {
                        // Para outros casos, podemos expandir a lógica aqui
                        console.log(`[DOCS-EXEC] Item ${index}: anexos disponíveis mas não relacionados à pesquisa patrimonial`);
                    }
                }
                
                // Se não tem documento principal nem anexos relevantes, informar
                if (!link && !btnAnexos) {
                    console.log(`[DOCS-EXEC] Item ${index}: sem documento ou anexos relevantes`);
                }
                
            } catch (e) {
                console.error(`[DOCS-EXEC] Erro ao processar item ${index}:`, e);
            }
        });
        
        return documentos;
    }
    
    // Função para gerar e exibir relatório
    function gerarRelatorio(documentos) {
        // Remover relatório anterior
        const relatorioExistente = document.getElementById('relatorioDocsExecucao');
        if (relatorioExistente) {
            relatorioExistente.remove();
        }
        
        const container = document.createElement('div');
        container.id = 'relatorioDocsExecucao';
        container.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 100000;
            background: white;
            border: 2px solid #007bff;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            max-width: 90%;
            max-height: 80%;
            overflow-y: auto;
            padding: 24px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        // Cabeçalho
        const cabecalho = document.createElement('div');
        cabecalho.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #007bff;
            padding-bottom: 15px;
        `;
        
        const titulo = document.createElement('h3');
        titulo.innerHTML = '📋 Documentos de Execução Encontrados';
        titulo.style.cssText = 'margin: 0; color: #007bff; font-size: 18px;';
        
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
        
        if (documentos.length === 0) {
            const mensagem = document.createElement('div');
            mensagem.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                    <h4 style="margin: 0 0 8px 0; color: #333;">Nenhum documento encontrado</h4>
                    <p style="margin: 0; font-style: italic;">Não foram encontrados documentos de execução na timeline.</p>
                </div>
            `;
            container.appendChild(mensagem);
        } else {
            // Contador
            const contador = document.createElement('div');
            contador.innerHTML = `<strong>${documentos.length}</strong> documento(s) encontrado(s)`;
            contador.style.cssText = `
                background: #e7f3ff;
                border: 1px solid #007bff;
                border-radius: 6px;
                padding: 8px 12px;
                margin-bottom: 16px;
                color: #0056b3;
                font-weight: 500;
            `;
            container.appendChild(contador);
            
            // Lista de documentos
            const lista = document.createElement('div');
            
            documentos.forEach((doc, index) => {
                const item = document.createElement('div');
                item.style.cssText = `
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    background: ${index % 2 === 0 ? '#f8f9fa' : 'white'};
                    transition: all 0.2s ease;
                    cursor: pointer;
                `;
                
                item.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#e7f3ff';
                    this.style.borderColor = '#007bff';
                });
                
                item.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = index % 2 === 0 ? '#f8f9fa' : 'white';
                    this.style.borderColor = '#dee2e6';
                });
                
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: #007bff; margin-bottom: 4px;">
                                ${doc.tipoItem === 'anexos' ? '�' : '�📄'} ${doc.tipo}
                            </div>
                            <div style="color: #333; margin-bottom: 8px;">
                                ${doc.texto}
                            </div>
                            <div style="font-size: 12px; color: #666; font-family: monospace;">
                                ID: ${doc.id} | Tipo: ${doc.tipoItem || 'documento'}
                            </div>
                            ${doc.documentoPai ? `<div style="font-size: 11px; color: #888; font-style: italic; margin-top: 4px;">Documento pai: ${doc.documentoPai}</div>` : ''}
                        </div>
                        <button class="btnSelecionar" data-index="${index}" style="
                            background: #28a745;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 8px 16px;
                            cursor: pointer;
                            font-size: 13px;
                            font-weight: 500;
                            transition: all 0.2s ease;
                            margin-left: 16px;
                        ">
                            ${doc.tipoItem === 'anexos' ? '📎 Expandir' : '🎯 Localizar'}
                        </button>
                    </div>
                `;
                
                lista.appendChild(item);
            });
            
            container.appendChild(lista);
            
            // Eventos dos botões
            container.addEventListener('click', function(e) {
                if (e.target.classList.contains('btnSelecionar')) {
                    const index = parseInt(e.target.getAttribute('data-index'));
                    const documento = documentos[index];
                    selecionarDocumentoTimeline(documento, e.target);
                }
            });
        }
        
        document.body.appendChild(container);
        console.log('[DOCS-EXEC] Relatório exibido');
    }
    
    // Função para selecionar documento na timeline
    function selecionarDocumentoTimeline(documento, botao) {
        try {
            console.log(`[DOCS-EXEC] Localizando: ${documento.texto}`);
            
            // Feedback no botão
            const textoOriginal = botao.innerHTML;
            botao.innerHTML = '⏳ Localizando...';
            botao.style.backgroundColor = '#ffc107';
            
            // Rolar até o elemento
            documento.elemento.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            
            // Destacar elemento
            setTimeout(() => {
                const estiloOriginal = documento.elemento.style.cssText;
                documento.elemento.style.cssText += `
                    background: linear-gradient(45deg, #fff3cd, #ffeaa7) !important;
                    border: 3px solid #007bff !important;
                    border-radius: 8px !important;
                    transform: scale(1.02) !important;
                    transition: all 0.3s ease !important;
                    box-shadow: 0 4px 15px rgba(0,123,255,0.3) !important;
                `;
                
                // Se for anexos, clicar no botão de anexos
                if (documento.tipoItem === 'anexos') {
                    console.log(`[DOCS-EXEC] Expandindo anexos para: ${documento.documentoPai}`);
                    setTimeout(() => {
                        documento.link.click();
                        console.log(`[DOCS-EXEC] ✅ Anexos expandidos`);
                    }, 1000);
                }
                
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
                
                // Remover destaque após 5 segundos
                setTimeout(() => {
                    documento.elemento.style.cssText = estiloOriginal;
                }, 5000);
                
                // Restaurar botão
                if (documento.tipoItem === 'anexos') {
                    botao.innerHTML = '✅ Anexos Expandidos';
                } else {
                    botao.innerHTML = '✅ Localizado';
                }
                botao.style.backgroundColor = '#28a745';
                
                setTimeout(() => {
                    botao.innerHTML = textoOriginal;
                    botao.style.backgroundColor = '#28a745';
                }, 3000);
                
            }, 1000);
            
        } catch (e) {
            console.error('[DOCS-EXEC] Erro ao localizar documento:', e);
            botao.innerHTML = '❌ Erro';
            botao.style.backgroundColor = '#dc3545';
            setTimeout(() => {
                botao.innerHTML = textoOriginal;
                botao.style.backgroundColor = '#28a745';
            }, 3000);
        }
    }
    
    // Função principal de análise
    function executarAnaliseTimeline() {
        try {
            console.log('[DOCS-EXEC] Executando análise...');
            
            // Feedback visual no botão
            const botao = document.getElementById('btnDocsExecucao');
            const textoOriginal = botao.textContent;
            botao.textContent = '⏳ Analisando...';
            botao.style.backgroundColor = '#ffc107';
            
            // Ler timeline e gerar relatório
            const documentos = lerTimelineCompleta();
            gerarRelatorio(documentos);
            
            // Restaurar botão
            setTimeout(() => {
                botao.textContent = textoOriginal;
                botao.style.backgroundColor = '#007bff';
            }, 1500);
            
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
    
})();
