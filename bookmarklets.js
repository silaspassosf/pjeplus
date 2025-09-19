// ============================================
// BOOKMARKLETS PJEPLUS - VERSÃO CONSOLIDADA
// ============================================
// Arquivo consolidado com todas as funcionalidades bookmarklet
// Atualizado em: 11/09/2025
// ============================================

// ============================================
// 1. MINUTAPJE - Automação de Minutas PJE
// ============================================

function bookmarklet_minutapje() {
    javascript: (function () { 'use strict'; if (window.MinutaPJE_bookmarklet_ativo) { console.log('[MinutaPJE] Bookmarklet já está ativo'); return; } window.MinutaPJE_bookmarklet_ativo = true; window.MinutaPJE_executando = false; let clickCounter = {}; function debounceClick(seletor, callback, delay = 1000) { const agora = Date.now(); const ultimo = clickCounter[seletor] || 0; if (agora - ultimo > delay) { clickCounter[seletor] = agora; return callback(); } else { console.log(`[MinutaPJE] Clique em ${seletor} ignorado por debounce (${agora - ultimo}ms)`); return Promise.resolve(false); } } function detectarMaisPJe() { if (window.preferencias && window.preferencias.extensaoAtiva) { console.log('[MinutaPJE] ⚠️ Extensão maisPJe detectada e ativa'); return true; } const elementosMaisPJe = document.querySelectorAll('[id*="maisPje"], [class*="maisPje"]'); if (elementosMaisPJe.length > 0) { console.log('[MinutaPJE] ⚠️ Elementos maisPJe detectados no DOM'); return true; } return false; } async function clicarBotaoSeguro(seletor, timeout = 5000) { return debounceClick(seletor, async () => { window.MinutaPJE_executando = true; try { const elemento = await waitForElement(seletor, timeout); if (!elemento) { console.warn(`[MinutaPJE] Elemento não encontrado: ${seletor}`); return false; } if (elemento.dataset.maisPjeProcessando) { console.log(`[MinutaPJE] Elemento ${seletor} sendo processado por maisPJe, aguardando...`); await sleep(2000); } elemento.dataset.minutaPjeProcessando = 'true'; console.log(`[MinutaPJE] Clicando seguro em: ${seletor}`); elemento.click(); await sleep(500); delete elemento.dataset.minutaPjeProcessando; return true; } catch (error) { console.error(`[MinutaPJE] Erro ao clicar em ${seletor}:`, error); return false; } finally { setTimeout(() => { window.MinutaPJE_executando = false; }, 3000); } }); } const REGRAS_FUNDAMENTACAO = [{ trigger: "promover a execução", descricao: "Regra para execução - promover execução", params: { pec: false, sigilo: false, prazo: 5, primeiroDestinatario: true, movimento: null, assinar: true } }]; function analisarFundamentacao() { try { let fundamentacao = null; fundamentacao = document.querySelector('div[aria-label*="Fundamentação"] .ck-content'); if (!fundamentacao) { fundamentacao = document.querySelector('div[aria-label="Fundamentação. Alt+F10 para acessar a barra de tarefas"]'); } if (!fundamentacao) { fundamentacao = document.querySelector('.area-conteudo.ck.ck-content.ck-editor__editable'); } if (!fundamentacao) { fundamentacao = document.querySelector('div.ck-content[contenteditable="true"]'); } if (!fundamentacao) { console.warn('[MinutaPJE] Elemento de fundamentação não encontrado com nenhum seletor'); const editaveis = document.querySelectorAll('[contenteditable="true"]'); if (editaveis.length > 0) { fundamentacao = editaveis[0]; } } if (!fundamentacao) { return null; } const textoFundamentacao = fundamentacao.textContent.toLowerCase(); for (const regra of REGRAS_FUNDAMENTACAO) { if (textoFundamentacao.includes(regra.trigger.toLowerCase())) { console.log(`[MinutaPJE] Regra encontrada: ${regra.descricao}`); return regra.params; } } console.warn('[MinutaPJE] Nenhuma regra correspondente encontrada na fundamentação'); return null; } catch (error) { console.error('[MinutaPJE] Erro ao analisar fundamentação:', error); return null; } } async function executarMinuta() { try { console.log('[MinutaPJE] Iniciando execução da minuta...'); if (detectarMaisPJe()) { criarLogExecucao('⚠️ maisPJe detectado - usando modo compatibilidade', 'warning'); } let params = analisarFundamentacao(); if (!params) { params = { pec: false, sigilo: false, prazo: 11, primeiroDestinatario: true, movimento: 'bloqueio', assinar: false }; } criarLogExecucao('Iniciando execução da minuta...'); criarLogExecucao('Etapa 1: Configurando sigilo...'); await configurarSigilo(params.sigilo); criarLogExecucao('Etapa 2: Configurando PEC...'); await configurarPEC(params.pec); if (params.prazo) { criarLogExecucao('Etapa 3: Configurando prazo...'); await configurarPrazo(params.prazo, params.primeiroDestinatario); } if (params.movimento) { criarLogExecucao('Etapa 4: Configurando movimento...'); await configurarMovimento(params.movimento); } if (params.assinar) { criarLogExecucao('Etapa 5: Enviando para assinatura...'); await enviarParaAssinatura(); } criarLogExecucao('✅ Minuta executada com sucesso!', 'success'); } catch (error) { console.error('[MinutaPJE] Erro:', error); criarLogExecucao(`❌ Erro: ${error.message}`, 'error'); } } async function configurarSigilo(ativar) { try { const toggles = document.querySelectorAll('mat-slide-toggle'); let sigiloToggle = null; for (const toggle of toggles) { if (toggle.textContent.toLowerCase().includes('sigilo')) { sigiloToggle = toggle; break; } } if (!sigiloToggle) { console.warn('[MinutaPJE] Toggle de sigilo não encontrado'); return false; } const sigiloInput = sigiloToggle.querySelector('input[type="checkbox"], input.mat-slide-toggle-input'); const checked = sigiloInput?.getAttribute('aria-checked') === 'true'; if ((ativar && !checked) || (!ativar && checked)) { const label = sigiloToggle.querySelector('label.mat-slide-toggle-label'); if (label) { label.click(); await sleep(500); } } return true; } catch (error) { console.error('[MinutaPJE] Erro ao configurar sigilo:', error); return false; } } async function configurarPEC(marcar) { try { let pecCheckbox = null; let pecInput = null; try { pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"]'); pecInput = pecCheckbox?.querySelector('input[type="checkbox"]'); } catch (e) { try { pecCheckbox = document.querySelector('div.checkbox-pec mat-checkbox'); pecInput = pecCheckbox?.querySelector('input[type="checkbox"]'); } catch (e2) { pecInput = document.querySelector('input[type="checkbox"][aria-label="Enviar para PEC"]'); pecCheckbox = pecInput?.closest('mat-checkbox'); } } if (!pecCheckbox || !pecInput) { console.warn('[MinutaPJE] Checkbox PEC não encontrado'); return false; } const checked = pecInput.getAttribute('aria-checked') === 'true' || pecInput.checked || pecCheckbox.classList.contains('mat-checkbox-checked'); if ((marcar && !checked) || (!marcar && checked)) { const label = pecCheckbox.querySelector('label.mat-checkbox-layout'); if (label) { label.click(); } else { pecCheckbox.click(); } await sleep(300); } return true; } catch (error) { console.error('[MinutaPJE] Erro ao configurar PEC:', error); return false; } } async function configurarPrazo(prazo, apenasUm) { try { const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted'); if (linhas.length === 0) { console.warn('[MinutaPJE] Nenhuma linha de destinatário encontrada!'); return false; } let ativos = []; for (const tr of linhas) { try { const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]'); const nomeElem = tr.querySelector('.destinario'); if (checkbox && nomeElem) { const nome = nomeElem.textContent.trim().toUpperCase(); if (checkbox.getAttribute('aria-checked') === 'true' || checkbox.checked) { ativos.push({ tr, checkbox, nome }); } } } catch (e) { console.warn('[MinutaPJE] Erro ao processar linha de destinatário:', e); } } if (ativos.length === 0) { return false; } if (apenasUm && ativos.length > 1) { for (let i = 1; i < ativos.length; i++) { try { const { checkbox } = ativos[i]; checkbox.click(); await sleep(200); } catch (e) { console.warn(`[MinutaPJE] Erro ao desmarcar checkbox ${i + 1}:`, e); } } ativos = [ativos[0]]; } for (const { tr } of ativos) { try { const inputPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element'); if (inputPrazo) { inputPrazo.focus(); inputPrazo.select(); inputPrazo.value = ''; inputPrazo.value = prazo.toString();['input', 'change', 'blur'].forEach(eventType => { const event = new Event(eventType, { bubbles: true }); inputPrazo.dispatchEvent(event); }); await sleep(200); } } catch (e) { console.warn(`[MinutaPJE] Erro ao preencher prazo:`, e); } } await sleep(500); const btnGravar = await waitForElement("button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button')]", 5000, true); if (btnGravar) { await clicarBotaoSeguro('button[aria-label="Salvar"]', 5000); await sleep(1000); } return true; } catch (error) { console.error('[MinutaPJE] Erro ao configurar prazo:', error); return false; } } async function configurarMovimento(movimento) { try { const abas = document.querySelectorAll('.mat-tab-label'); let abaMovimentos = null; for (const aba of abas) { if (aba.textContent.toLowerCase().includes('movimento')) { abaMovimentos = aba; break; } } if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') { abaMovimentos.click(); await sleep(800); } const checkboxes = document.querySelectorAll('mat-checkbox.movimento'); let movimentoEncontrado = false; const movimentoNorm = movimento.toLowerCase().trim(); for (const checkbox of checkboxes) { const label = checkbox.querySelector('label .mat-checkbox-label'); if (label) { const labelText = label.textContent.toLowerCase().trim(); if (labelText.includes(movimentoNorm) || (movimentoNorm === 'frustrada' && labelText.includes('execução frustrada'))) { const input = checkbox.querySelector('input[type="checkbox"]'); if (input && !input.checked) { const innerContainer = checkbox.querySelector('.mat-checkbox-inner-container'); if (innerContainer) { innerContainer.click(); } else { input.click(); } movimentoEncontrado = true; break; } } } } if (!movimentoEncontrado) { return false; } await sleep(500); const btnGravarMov = await waitForElement("button[aria-label='Gravar os movimentos a serem lançados']", 5000); if (btnGravarMov) { await clicarBotaoSeguro("button[aria-label='Gravar os movimentos a serem lançados']", 5000); await sleep(1000); const btnSim = await waitForElement("button[contains(@class, 'mat-button') and contains(@class, 'mat-primary') and .//span[text()='Sim']]", 5000, true); if (btnSim) { btnSim.click(); await sleep(1000); await clicarBotaoSeguro("button[aria-label='Salvar'][color='primary']", 5000); await sleep(1000); } } return true; } catch (error) { console.error('[MinutaPJE] Erro ao configurar movimento:', error); return false; } } async function enviarParaAssinatura() { try { await sleep(3000); const sucesso = await clicarBotaoSeguro('button.mat-fab[aria-label="Enviar para assinatura"]', 10000); return sucesso; } catch (error) { console.error('[MinutaPJE] Erro ao enviar para assinatura:', error); return false; } } function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); } function waitForElement(selector, timeout = 5000, isXPath = false) { return new Promise((resolve) => { const startTime = Date.now(); const checkElement = () => { let element; if (isXPath) { const result = document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null); element = result.singleNodeValue; } else { element = document.querySelector(selector); } if (element) { resolve(element); } else if (Date.now() - startTime < timeout) { setTimeout(checkElement, 100); } else { resolve(null); } }; checkElement(); }); } function criarLogExecucao(mensagem, tipo = 'info') { const timestamp = new Date().toLocaleTimeString(); let cor = '#2196F3'; switch (tipo) { case 'success': cor = '#4CAF50'; break; case 'error': cor = '#f44336'; break; case 'warning': cor = '#FF9800'; break; }console.log(`[MinutaPJE] ${timestamp} - ${mensagem}`); const toast = document.createElement('div'); toast.style.cssText = `position: fixed;top: 20px;right: 20px;background: ${cor};color: white;padding: 12px 20px;border-radius: 6px;box-shadow: 0 4px 12px rgba(0,0,0,0.15);z-index: 11000;font-family: Arial, sans-serif;font-size: 14px;max-width: 400px;word-wrap: break-word;transition: opacity 0.3s;`; toast.textContent = `${timestamp} - ${mensagem}`; document.body.appendChild(toast); setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => { if (toast.parentNode) { toast.parentNode.removeChild(toast); } }, 300); }, 4000); } function criarInterface() { const botaoExistente = document.getElementById('minutapje-btn-bookmarklet'); if (botaoExistente) { console.log('[MinutaPJE] Botão já existe - não criando novamente'); return; } const btnMinuta = document.createElement('button'); btnMinuta.id = 'minutapje-btn-bookmarklet'; btnMinuta.textContent = 'Minuta (BM)'; btnMinuta.style.cssText = `position: fixed;top: 50%;right: 20px;transform: translateY(-50%);z-index: 99999;padding: 15px 25px;background: #FF5722;color: white;border: none;border-radius: 8px;font-size: 16px;font-weight: bold;cursor: pointer;box-shadow: 0 4px 20px rgba(0,0,0,0.15);transition: background 0.3s;font-family: Arial, sans-serif;`; btnMinuta.onmouseover = () => btnMinuta.style.background = '#D84315'; btnMinuta.onmouseout = () => btnMinuta.style.background = '#FF5722'; btnMinuta.onclick = () => { console.log('[MinutaPJE] Botão bookmarklet clicado!'); executarMinuta(); }; document.body.appendChild(btnMinuta); console.log('[MinutaPJE] Botão bookmarklet adicionado ao DOM'); criarLogExecucao('🚀 MinutaPJE Bookmarklet carregado!', 'info'); } if (!window.location.href.includes('minutar')) { criarLogExecucao('❌ Não é página de minutar', 'error'); window.MinutaPJE_bookmarklet_ativo = false; return; } if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', criarInterface); } else { setTimeout(criarInterface, 1000); } })();
}

// ============================================
// 2. SISBAJUD ORDENS - Extrator de Ordens
// ============================================

function bookmarklet_sisbajud_ordens() {
    javascript: (function () {
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
                return `R$ ${(Number(n) || 0).toFixed(2).toFixed(2).replace('.', ',')}`;
            }
        }

        // Função para mostrar notificações
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
            `;

            document.body.appendChild(notificacao);

            setTimeout(() => {
                if (notificacao.parentNode) {
                    notificacao.parentNode.removeChild(notificacao);
                }
            }, 4000);
        }

        // Função para extrair dados da página atual
        function extrairDadosPagina() {
            try {
                console.log('[SISBAJUD] Iniciando extração de dados...');

                // Extrair dados do executado
                const nomeExecutado = document.querySelector('span[data-testid="nome-executado"]')?.textContent?.trim() ||
                    document.querySelector('.nome-executado')?.textContent?.trim() ||
                    document.querySelector('h3, h4, h5')?.textContent?.trim() ||
                    'Nome não encontrado';

                // Extrair valor da ordem
                let valorOrdem = 0;
                const elementosValor = document.querySelectorAll('*');
                for (const elemento of elementosValor) {
                    const texto = elemento.textContent || elemento.innerText || '';
                    const match = texto.match(/R\$\s*[\d.,]+/);
                    if (match) {
                        valorOrdem = brlToFloat(match[0]);
                        if (valorOrdem > 0) break;
                    }
                }

                // Extrair número da ordem
                let numeroOrdem = '';
                const elementosNumero = document.querySelectorAll('h1, h2, h3, .titulo, .numero-ordem');
                for (const elemento of elementosNumero) {
                    const texto = elemento.textContent || elemento.innerText || '';
                    const match = texto.match(/Ordem\s*Judicial\s*[Nº]?\s*(\d+)/i) ||
                        texto.match(/(\d{4,})/);
                    if (match) {
                        numeroOrdem = match[1] || match[0];
                        break;
                    }
                }

                // Extrair data da ordem
                let dataOrdem = '';
                const elementosData = document.querySelectorAll('*');
                for (const elemento of elementosData) {
                    const texto = elemento.textContent || elemento.innerText || '';
                    const match = texto.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
                    if (match) {
                        dataOrdem = `${match[1].padStart(2, '0')}/${match[2].padStart(2, '0')}/${match[3]}`;
                        break;
                    }
                }

                if (!nomeExecutado || nomeExecutado === 'Nome não encontrado') {
                    mostrarNotificacao('❌ Nome do executado não encontrado', 'error');
                    return null;
                }

                const dadosExtraidos = {
                    nomeExecutado: nomeExecutado,
                    valorOrdem: valorOrdem,
                    numeroOrdem: numeroOrdem,
                    dataOrdem: dataOrdem,
                    url: window.location.href,
                    timestamp: new Date().toISOString()
                };

                console.log('[SISBAJUD] Dados extraídos:', dadosExtraidos);
                return dadosExtraidos;

            } catch (error) {
                console.error('[SISBAJUD] Erro ao extrair dados:', error);
                mostrarNotificacao('❌ Erro ao extrair dados da página', 'error');
                return null;
            }
        }

        // Função para acumular dados
        function acumularDados(dados) {
            if (!dados) return;

            const nomeExecutado = dados.nomeExecutado;

            if (!ordensAcumuladas.executados[nomeExecutado]) {
                ordensAcumuladas.executados[nomeExecutado] = {
                    ordens: [],
                    totalValor: 0.0
                };
            }

            // Verificar se já existe uma ordem com mesmo número
            const ordemExistente = ordensAcumuladas.executados[nomeExecutado].ordens.find(
                ordem => ordem.numeroOrdem === dados.numeroOrdem
            );

            if (!ordemExistente) {
                ordensAcumuladas.executados[nomeExecutado].ordens.push({
                    numeroOrdem: dados.numeroOrdem,
                    dataOrdem: dados.dataOrdem,
                    valorOrdem: dados.valorOrdem,
                    url: dados.url,
                    timestamp: dados.timestamp
                });

                ordensAcumuladas.executados[nomeExecutado].totalValor += dados.valorOrdem;
                ordensAcumuladas.totalGeral += dados.valorOrdem;
                ordensAcumuladas.ultimaExtracao = new Date().toLocaleString('pt-BR');

                console.log(`[SISBAJUD] Ordem adicionada para ${nomeExecutado}`);
            } else {
                console.log(`[SISBAJUD] Ordem ${dados.numeroOrdem} já existe para ${nomeExecutado}`);
            }
        }

        // Função para gerar relatório
        function gerarRelatorio() {
            try {
                console.log('[SISBAJUD] Gerando relatório...');

                let relatorio = 'RELATÓRIO DE ORDENS JUDICIAIS - SISBAJUD\n';
                relatorio += '='.repeat(50) + '\n\n';

                if (Object.keys(ordensAcumuladas.executados).length === 0) {
                    relatorio += 'Nenhuma ordem foi extraída ainda.\n';
                } else {
                    relatorio += `Última extração: ${ordensAcumuladas.ultimaExtracao}\n`;
                    relatorio += `Total geral: ${toBRL(ordensAcumuladas.totalGeral)}\n\n`;

                    for (const [nomeExecutado, dados] of Object.entries(ordensAcumuladas.executados)) {
                        relatorio += `EXECUTADO: ${nomeExecutado}\n`;
                        relatorio += `Total para este executado: ${toBRL(dados.totalValor)}\n`;
                        relatorio += `Quantidade de ordens: ${dados.ordens.length}\n\n`;

                        dados.ordens.forEach((ordem, index) => {
                            relatorio += `  Ordem ${index + 1}:\n`;
                            relatorio += `    Número: ${ordem.numeroOrdem || 'N/A'}\n`;
                            relatorio += `    Data: ${ordem.dataOrdem || 'N/A'}\n`;
                            relatorio += `    Valor: ${toBRL(ordem.valorOrdem)}\n`;
                            relatorio += `    URL: ${ordem.url}\n\n`;
                        });

                        relatorio += '-'.repeat(30) + '\n';
                    }
                }

                // Copiar para clipboard
                navigator.clipboard.writeText(relatorio).then(() => {
                    mostrarNotificacao('✅ Relatório copiado para clipboard!', 'success');
                }).catch(() => {
                    // Fallback para browsers antigos
                    const textArea = document.createElement('textarea');
                    textArea.value = relatorio;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    mostrarNotificacao('✅ Relatório copiado!', 'success');
                });

                console.log('[SISBAJUD] Relatório gerado com sucesso');

            } catch (error) {
                console.error('[SISBAJUD] Erro ao gerar relatório:', error);
                mostrarNotificacao('❌ Erro ao gerar relatório', 'error');
            }
        }

        // Função principal
        function executarExtracao() {
            const dados = extrairDadosPagina();
            if (dados) {
                acumularDados(dados);
                mostrarNotificacao(`✅ Ordem extraída: ${dados.nomeExecutado}`, 'success');
            }
        }

        // Criar interface
        function criarInterface() {
            // Botão de extração
            const btnExtrair = document.createElement('button');
            btnExtrair.textContent = 'Extrair Ordem';
            btnExtrair.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 99999;
                padding: 12px 20px;
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                font-family: Arial, sans-serif;
            `;

            btnExtrair.onmouseover = () => btnExtrair.style.background = '#1976D2';
            btnExtrair.onmouseout = () => btnExtrair.style.background = '#2196F3';
            btnExtrair.onclick = executarExtracao;

            // Botão de relatório
            const btnRelatorio = document.createElement('button');
            btnRelatorio.textContent = 'Gerar Relatório';
            btnRelatorio.style.cssText = `
                position: fixed;
                top: 70px;
                right: 20px;
                z-index: 99999;
                padding: 12px 20px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                font-family: Arial, sans-serif;
            `;

            btnRelatorio.onmouseover = () => btnRelatorio.style.background = '#388E3C';
            btnRelatorio.onmouseout = () => btnRelatorio.style.background = '#4CAF50';
            btnRelatorio.onclick = gerarRelatorio;

            document.body.appendChild(btnExtrair);
            document.body.appendChild(btnRelatorio);

            mostrarNotificacao('🚀 SISBAJUD Extrator carregado!', 'info');
        }

        // Inicializar
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', criarInterface);
        } else {
            criarInterface();
        }

    })();
}

// ============================================
// 3. SÉRIES TEIMOSINHA - Extrator de Séries
// ============================================

function bookmarklet_series_teimosinha() {
    javascript: (function () { function extrairSeriesTeimosinha() { try { console.log('[TEIMOSINHA] Iniciando extração de séries elegíveis...'); const linhasTabela = document.querySelectorAll('tbody tr, .mat-row, tr[data-serie-id], tr.serie-row'); if (linhasTabela.length === 0) { const alternativas = ['table tr:not(:first-child)', '.series-container .serie-item', '[class*="serie"]', '.tabela-series tr']; for (const seletor of alternativas) { const elementos = document.querySelectorAll(seletor); if (elementos.length > 0) { console.log(`[TEIMOSINHA] Encontrado ${elementos.length} elementos com seletor: ${seletor}`); break; } } } const series = []; let contador = 0; linhasTabela.forEach((linha, index) => { try { const textoLinha = linha.textContent || linha.innerText || ''; const colunas = linha.querySelectorAll('td, .mat-cell'); if (colunas.length >= 3) { let numeroProtocolo = ''; let dataConclusao = ''; let valorBloqueado = ''; let idSerie = ''; const atributoId = linha.getAttribute('data-serie-id') || linha.getAttribute('id') || linha.querySelector('[data-serie-id]')?.getAttribute('data-serie-id'); if (atributoId) { idSerie = atributoId; } else { const matchId = textoLinha.match(/série\s+(\d+)/i); if (matchId) { idSerie = matchId[1]; } } const matchProtocolo = textoLinha.match(/(\d{7,}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,})/); if (matchProtocolo) { numeroProtocolo = matchProtocolo[1]; } const matchData = textoLinha.match(/(\d{1,2})[\/](\d{1,2})[\/](\d{4})/); if (matchData) { dataConclusao = `${matchData[1].padStart(2, '0')}/${matchData[2].padStart(2, '0')}/${matchData[3]}`; } const matchValor = textoLinha.match(/R\$\s*([\d.,]+)/); if (matchValor) { valorBloqueado = `R$ ${matchValor[1]}`; } if (idSerie || numeroProtocolo) { series.push({ indice: contador + 1, idSerie: idSerie || `ID-${contador + 1}`, numeroProtocolo: numeroProtocolo || 'Protocolo não identificado', dataConclusao: dataConclusao || 'Data não identificada', valorBloqueado: valorBloqueado || 'Valor não identificado', textoCompleto: textoLinha.trim() }); contador++; } } } catch (erro) { console.warn(`[TEIMOSINHA] Erro ao processar linha ${index}:`, erro); } }); if (series.length === 0) { console.log('[TEIMOSINHA] Tentando extração baseada em texto...'); const textoCompleto = document.body.textContent || document.body.innerText || ''; const linhasTexto = textoCompleto.split('\n').filter(linha => linha.trim().length > 10); linhasTexto.forEach((linha, index) => { const textoLimpo = linha.trim(); if (/série|protocolo|\d{7,}-\d{2}\.\d{4}/i.test(textoLimpo)) { let numeroProtocolo = ''; let dataConclusao = ''; let valorBloqueado = ''; const matchProtocolo = textoLimpo.match(/(\d{7,}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,})/); if (matchProtocolo) { numeroProtocolo = matchProtocolo[1]; } const matchData = textoLimpo.match(/(\d{1,2})[\/](\d{1,2})[\/](\d{4})/); if (matchData) { dataConclusao = `${matchData[1].padStart(2, '0')}/${matchData[2].padStart(2, '0')}/${matchData[3]}`; } const matchValor = textoLimpo.match(/R\$\s*([\d.,]+)/); if (matchValor) { valorBloqueado = `R$ ${matchValor[1]}`; } if (numeroProtocolo || /série/i.test(textoLimpo)) { series.push({ indice: series.length + 1, idSerie: `Série-${series.length + 1}`, numeroProtocolo: numeroProtocolo || 'Protocolo não identificado', dataConclusao: dataConclusao || 'Data não identificada', valorBloqueado: valorBloqueado || 'Valor não identificado', textoCompleto: textoLimpo }); } } }); } if (series.length > 0) { const dataAtual = new Date().toLocaleDateString('pt-BR'); let relatorioHTML = ''; relatorioHTML += '<p style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:center;text-indent:4.5cm;" class="corpo"><strong>JUNTADA</strong></p>'; relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;">Nessa data, procedo à juntada de informação sobre séries de teimosinha elegíveis processadas no sistema SISBAJUD, conforme dados abaixo transcritos:</p>'; relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Data da conferência: ${dataAtual}</p>`; relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Total de séries encontradas: <strong>${series.length}</strong></p>`; relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Discriminação das séries elegíveis:</p>'; series.forEach((serie, index) => { relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:1cm;text-align:justify !important;text-indent:4.5cm;">• <u>Série ${serie.idSerie}</u> - Protocolo: ${serie.numeroProtocolo} - Data da conclusão: ${serie.dataConclusao} - Valor bloqueado: <strong>${serie.valorBloqueado}</strong>`; if (index < series.length - 1) { relatorioHTML += '<br>'; } relatorioHTML += '</p>'; }); relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"><br data-cke-filler="true"></p>'; navigator.clipboard.writeText(relatorioHTML).then(() => { mostrarNotificacao(`✅ ${series.length} séries copiadas (formato HTML)!`, 'success'); }).catch(() => { const textarea = document.createElement('textarea'); textarea.value = relatorioHTML; document.body.appendChild(textarea); textarea.select(); document.execCommand('copy'); document.body.removeChild(textarea); mostrarNotificacao(`✅ ${series.length} séries copiadas!`, 'success'); }); console.log('[TEIMOSINHA] Relatório HTML gerado:', relatorioHTML); } else { mostrarNotificacao('❌ Nenhuma série elegível encontrada', 'error'); console.log('[TEIMOSINHA] Nenhuma série encontrada na página'); } } catch (erro) { console.error('[TEIMOSINHA] Erro geral:', erro); mostrarNotificacao('❌ Erro ao extrair séries', 'error'); } } function mostrarNotificacao(mensagem, tipo = 'info') { const cores = { success: '#4CAF50', error: '#f44336', info: '#2196F3', warning: '#FF9800' }; const notificacao = document.createElement('div'); notificacao.textContent = mensagem; notificacao.style.cssText = `position:fixed;top:20px;right:20px;background:${cores[tipo]};color:white;padding:15px 25px;border-radius:8px;font-size:16px;font-weight:bold;z-index:99999;box-shadow:0 4px 15px rgba(0,0,0,0.3);font-family:Arial,sans-serif;`; document.body.appendChild(notificacao); setTimeout(() => { if (notificacao.parentNode) { notificacao.parentNode.removeChild(notificacao); } }, 4000); } extrairSeriesTeimosinha(); })();
}

// ============================================
// FUNÇÕES DE INTERFACE E UTILITÁRIOS
// ============================================

// Função para criar menu principal
function criarMenuPrincipal() {
    const menuContainer = document.createElement('div');
    menuContainer.id = 'pjeplus-bookmarklets-menu';
    menuContainer.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 100000;
        background: white;
        border: 2px solid #2196F3;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        font-family: Arial, sans-serif;
        min-width: 250px;
    `;

    menuContainer.innerHTML = `
        <div style="margin-bottom: 15px; font-weight: bold; color: #2196F3; text-align: center;">
            🚀 PJEPLUS BOOKMARKLETS
        </div>
        <button onclick="bookmarklet_minutapje()" style="width: 100%; margin: 5px 0; padding: 10px; background: #FF5722; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
            📝 MinutaPJE
        </button>
        <button onclick="bookmarklet_sisbajud_ordens()" style="width: 100%; margin: 5px 0; padding: 10px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
            📋 SISBAJUD Ordens
        </button>
        <button onclick="bookmarklet_series_teimosinha()" style="width: 100%; margin: 5px 0; padding: 10px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
            📊 Séries Teimosinha
        </button>
        <button onclick="fecharMenu()" style="width: 100%; margin: 10px 0 0 0; padding: 8px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;">
            ❌ Fechar
        </button>
    `;

    document.body.appendChild(menuContainer);
}

// Função para fechar menu
function fecharMenu() {
    const menu = document.getElementById('pjeplus-bookmarklets-menu');
    if (menu) {
        menu.remove();
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
    `;

    document.body.appendChild(notificacao);

    setTimeout(() => {
        if (notificacao.parentNode) {
            notificacao.parentNode.removeChild(notificacao);
        }
    }, 4000);
}

// ============================================
// INICIALIZAÇÃO
// ============================================

// Criar botão flutuante para abrir menu
function criarBotaoMenu() {
    const botaoMenu = document.createElement('button');
    botaoMenu.id = 'pjeplus-menu-btn';
    botaoMenu.textContent = '🚀 PJE+';
    botaoMenu.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 100000;
        padding: 15px 20px;
        background: linear-gradient(45deg, #2196F3, #21CBF3);
        color: white;
        border: none;
        border-radius: 50px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        font-family: Arial, sans-serif;
        transition: all 0.3s;
    `;

    botaoMenu.onmouseover = () => {
        botaoMenu.style.transform = 'scale(1.05)';
        botaoMenu.style.boxShadow = '0 6px 25px rgba(0,0,0,0.3)';
    };

    botaoMenu.onmouseout = () => {
        botaoMenu.style.transform = 'scale(1)';
        botaoMenu.style.boxShadow = '0 4px 20px rgba(0,0,0,0.2)';
    };

    botaoMenu.onclick = () => {
        if (document.getElementById('pjeplus-bookmarklets-menu')) {
            fecharMenu();
        } else {
            criarMenuPrincipal();
        }
    };

    document.body.appendChild(botaoMenu);
    mostrarNotificacao('🚀 PJEPLUS Bookmarklets carregado!', 'success');
}

// Inicializar quando DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', criarBotaoMenu);
} else {
    criarBotaoMenu();
}

console.log('📦 PJEPLUS Bookmarklets v1.0 - Carregado com sucesso!');