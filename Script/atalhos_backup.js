// ==UserScript==
// @name         PJePlus - Documentos + Edital + Sigilo + SISBAJUD v4.0
// @namespace    http://tampermonkey.net/
// @version      4.0
// @description  Suite integrada: Relatórios de Execução (Check) + Editais + Pagamentos + Visibilidade Sigilosos + Extrator SISBAJUD em painel único centralizado
// @author       PjePlus
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt2.jus.br/pjekz/pagamento/*/cadastro
// @grant        none
// ==/UserScript==
(function () {
    'use strict';

    const sleep = ms => new Promise(r => setTimeout(r, ms));

    async function aplicarVisibilidadeSigilosos() {
        try {
            console.log('[V] Iniciando visibilidade (TODOS os anexos do primeiro documento)...');

            const itens = Array.from(document.querySelectorAll('li.tl-item-container'));
            if (!itens.length) {
                alert('⚠️ Nenhum item na timeline');
                return;
            }

            let totalProcessados = 0;
            let encontrouPrimeiro = false;

            // Processar apenas o PRIMEIRO documento com anexos
            for (const item of itens) {
                if (encontrouPrimeiro) break;

                const anexosComp = item.querySelector('pje-timeline-anexos');
                if (!anexosComp) continue;

                const toggle = anexosComp.querySelector('div[name="mostrarOuOcultarAnexos"]');
                if (!toggle) continue;

                const jaExpandido = toggle.getAttribute('aria-pressed') === 'true';

                if (!jaExpandido) {
                    console.log('[V] Expandindo anexos...');
                    toggle.click();
                    await sleep(600);
                }

                await sleep(200);
                const anexoLinks = anexosComp.querySelectorAll('a.tl-documento[id^="anexo_"]');

                if (!anexoLinks.length) continue;

                console.log(`[V] Encontrados ${anexoLinks.length} anexos - processando TODOS...`);
                encontrouPrimeiro = true;

                // Processar TODOS os anexos do primeiro documento
                for (const anexo of anexoLinks) {
                    try {
                        const textoAnexo = (anexo.textContent || anexo.innerText || '').trim();
                        console.log(`[V] Processando anexo ${totalProcessados + 1}: ${textoAnexo}`);

                        // 1. Procurar ícone + do anexo
                        const iconePlus = anexo.querySelector('i.fa-plus, [class*="plus"], button[title*="Visibilidade"]') ||
                                         anexo.parentElement?.querySelector('i.fa-plus, [class*="plus"]');

                        if (!iconePlus) {
                            console.log(`[V] ⚠️ Ícone + não encontrado para: ${textoAnexo}`);
                            continue;
                        }

                        const elemClicavel = iconePlus.closest('button') || iconePlus;
                        elemClicavel.click();
                        await sleep(1500);

                        // 2. Aguardar modal de visibilidade
                        let modal = null;
                        for (let t = 0; t < 30; t++) {
                            const mods = document.querySelectorAll('.cdk-overlay-container .mat-dialog-container');
                            for (const m of mods) {
                                const html = m.innerHTML || '';
                                if (html.includes('Visibilidade') && (html.includes('partes') || html.includes('Atribuir'))) {
                                    modal = m;
                                    break;
                                }
                            }
                            if (modal) break;
                            await sleep(200);
                        }

                        if (!modal) {
                            console.log(`[V] ⚠️ Modal não encontrado para: ${textoAnexo}`);
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                            await sleep(800);
                            continue;
                        }

                        console.log('[V] Modal encontrado - processando...');
                        await sleep(600);

                        // 3. Clicar "Marcar Todas" (buscar por classe ou ícone)
                        try {
                            let marcarTodasBtn = null;

                            // Opção 1: Procurar pelo ícone fa-check com classe marcar-todas
                            const iconeMarcarTodas = modal.querySelector('i.fa-check.marcar-todas');
                            if (iconeMarcarTodas) {
                                marcarTodasBtn = iconeMarcarTodas.closest('button, div[role="button"]') || iconeMarcarTodas;
                            }

                            // Opção 2: Procurar por elemento com classe marcar-todas
                            if (!marcarTodasBtn) {
                                marcarTodasBtn = modal.querySelector('.marcar-todas');
                            }

                            // Opção 3: Buscar por classe botao-icone-titulo-coluna com fa-check
                            if (!marcarTodasBtn) {
                                const botaoIcone = modal.querySelector('i.fa-check.botao-icone-titulo-coluna');
                                if (botaoIcone) {
                                    marcarTodasBtn = botaoIcone.closest('button, div[role="button"]') || botaoIcone;
                                }
                            }

                            if (marcarTodasBtn) {
                                console.log('[V] Clicando "Marcar Todas"...');
                                // Usar script em vez de .click() para garantir execução
                                if (marcarTodasBtn.tagName === 'BUTTON' || marcarTodasBtn.getAttribute('role') === 'button') {
                                    marcarTodasBtn.click();
                                } else {
                                    // Se for apenas um ícone, buscar o button pai
                                    const parentBtn = marcarTodasBtn.closest('button');
                                    if (parentBtn) {
                                        parentBtn.click();
                                    } else {
                                        marcarTodasBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                    }
                                }
                                await sleep(400);
                            } else {
                                console.log('[V] ⚠️ Botão "Marcar Todas" não encontrado - procurando alternativas');
                            }
                        } catch (e) {
                            console.log('[V] Erro ao buscar "Marcar Todas":', e.message);
                        }

                        // 4. Clicar botão Salvar
                        await sleep(300);
                        const btnSalvar = Array.from(modal.querySelectorAll('button'))
                            .find(b => (b.textContent || '').trim().toLowerCase().includes('salvar'));

                        if (!btnSalvar) {
                            console.log('[V] ⚠️ Botão Salvar não encontrado');
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                            await sleep(800);
                            continue;
                        }

                        console.log('[V] Clicando Salvar...');
                        btnSalvar.click();
                        await sleep(1500);

                        console.log('[V] ✅ Anexo processado');
                        totalProcessados++;

                        // Fechar com ESC como fallback
                        document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                        await sleep(500);

                    } catch (e) {
                        console.error('[V] Erro ao processar anexo:', e.message);
                        try {
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                        } catch (e2) {}
                        await sleep(800);
                    }
                }
            }

            // Log final sem alert
            if (totalProcessados > 0) {
                console.log(`[V] ✅ Concluído! ${totalProcessados} anexo(s) processado(s) com visibilidade`);
            } else {
                console.log('[V] ⚠️ Nenhum anexo encontrado para processar');
            }

        } catch (e) {
            console.error('[V] Erro:', e);
        }
    }

    // ============================================================
    // SISBAJUD PDF EXTRACTOR
    // ============================================================
    let acumuladorSISB = { executados: {}, protocolos: [] };
    const timeoutSISB = 15000; // 15 segundos para acumular dados
    let timerSISB = null;

    async function extrairRelatorioSISB() {
        console.log('[SISB] Iniciando extração...');

        for (let tentativa = 0; tentativa < 25; tentativa++) {
            const modal = document.querySelector('.cdk-overlay-container .mat-dialog-container');
            if (!modal) {
                await sleep(600);
                continue;
            }

            const texto = modal.innerText || modal.textContent || '';
            if (!texto.includes('protocolo') && !texto.includes('Protocolo')) {
                await sleep(600);
                continue;
            }

            console.log('[SISB] ✓ Modal encontrado com dados');

            // Extrair protocolo
            const matchProto = modal.innerHTML.match(/Número do protocolo:\s*(\d+)/i);
            const protocolo = matchProto ? matchProto[1] : 'N/A';

            // Extrair executados
            const executados = {};
            const seçãoReúsRegex = /Relação dos Réus\/Executados[\s\S]*?Réu\/Executado[\s\S]*?\n([\s\S]*?)(?=\n\n|Respostas|$)/i;
            const match = modal.innerHTML.match(seçãoReúsRegex);

            if (match) {
                const secaoText = match[1];
                const linhas = secaoText.split('\n').filter(l => l.trim());
                const padrão = /(\d+):\s*(.+?)\s+R\$\s*([\d.,]+)/g;
                let m;
                while ((m = padrão.exec(secaoText)) !== null) {
                    const [, num, nome, valor] = m;
                    executados[nome.trim()] = valor.trim();
                }
            }

            acumularDados(executados, protocolo);
            return { protocolo, executados };
        }

        console.log('[SISB] ⚠️ Modal não encontrado após 25 tentativas');
        return null;
    }

    function acumularDados(executados, protocolo) {
        Object.assign(acumuladorSISB.executados, executados);
        if (!acumuladorSISB.protocolos.includes(protocolo)) {
            acumuladorSISB.protocolos.push(protocolo);
        }

        clearTimeout(timerSISB);
        timerSISB = setTimeout(() => {
            console.log('[SISB] Timeout de 15s atingido, resetando...');
            acumuladorSISB = { executados: {}, protocolos: [] };
        }, timeoutSISB);
    }

    function gerarRelatorioConciso() {
        const pStyle = 'style="margin:0;padding:0;text-indent:4.5cm;line-height:1.5;"';
        let html = `<p ${pStyle}><strong>BLOQUEIOS TRANSFERIDOS - SISBAJUD</strong></p>`;

        Object.entries(acumuladorSISB.executados).forEach(([nome, valor]) => {
            html += `<p ${pStyle}>- ${nome} (Documento: ${nome.split('(')[1]?.split(')')[0] || '?'}):</p>`;
            const label = acumuladorSISB.protocolos.length > 1 ? 'Protocolos' : 'Protocolo';
            html += `<p ${pStyle}>Ordens com bloqueios transferidos: [${label}: ${acumuladorSISB.protocolos.join(', ')}] - Total: ${formatarValorSISB(valor)}</p>`;
        });

        return html;
    }

    function formatarValorSISB(valor) {
        const num = parseFloat(valor.replace(/[^\d,]/g, '').replace(',', '.'));
        if (isNaN(num)) return valor;
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(num);
    }

    function copiarHTMLFormatado() {
        const html = gerarRelatorioConciso();
        const container = document.createElement('div');
        container.innerHTML = html;
        document.body.appendChild(container);

        try {
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(container);
            selection.removeAllRanges();
            selection.addRange(range);
            document.execCommand('copy');
            selection.removeAllRanges();
            console.log('[SISB] ✓ HTML copiado para clipboard');
        } catch (e) {
            console.error('[SISB] Erro ao copiar:', e);
        } finally {
            document.body.removeChild(container);
        }
    }

    async function executarSISBAJUD() {
        try {
            console.log('[SISB] Botão clicado');
            const resultado = await extrairRelatorioSISB();

            if (resultado) {
                console.log('[SISB] ✓ Dados extraídos');
                await sleep(300);
                copiarHTMLFormatado();
                alert(`✅ Relatório copiado!\n\nProtocolo: ${resultado.protocolo}\nExecutados: ${Object.keys(acumuladorSISB.executados).length}`);
            } else {
                alert('⚠️ Nenhum modal de SISBAJUD encontrado');
            }
        } catch (e) {
            alert(`❌ Erro: ${e.message}`);
            console.error('[SISB] Erro:', e);
        }
    }

    if (window.location.href.includes('/pagamento/')) {
        // Lógica para página de pagamento
        function gerarRelatorioPagamentos() {
            // Aguardar carregamento dos dados dinâmicos (mat-cards)
            setTimeout(() => {
                const stored = localStorage.getItem('pjeplus_alvaras');
                if (!stored) return;

                const alvaras = JSON.parse(stored);
                const pagamentos = [];

                const cards = document.querySelectorAll('mat-card');
                cards.forEach(card => {
                    const dataDt = card.querySelector('dl.dl-rubrica dt');
                    if (dataDt && dataDt.textContent.trim() === 'Data do Pagamento') {
                        const dataDd = dataDt.nextElementSibling;
                        if (dataDd) {
                            const dataStr = dataDd.textContent.trim();
                            const [dia, mes, anoPart] = dataStr.split('/').map(Number);
                            let ano = anoPart;
                            if (ano < 100) ano += 2000;
                            const data = new Date(ano, mes - 1, dia);

                            // Procurar por valor != 0,00 na mesma card
                            let valor = '';
                            let rubrica = '';
                            const dls = card.querySelectorAll('dl.dl-rubrica');
                            dls.forEach(dl => {
                                const dt = dl.querySelector('dt');
                                const dd = dl.querySelector('dd');
                                if (dt && dd) {
                                    const rub = dt.textContent.trim();
                                    const val = dd.textContent.trim();
                                    if (val.includes('R$') && val !== 'R$ 0,00' && val !== 'R$&nbsp;0,00') {
                                        if (!valor) { // Pegar o primeiro valor != 0,00
                                            valor = val;
                                            rubrica = rub;
                                        }
                                    }
                                }
                            });

                            pagamentos.push({ data, valor, rubrica });
                        }
                    }
                });

                function formatDate(d) {
                    const dia = d.getDate().toString().padStart(2, '0');
                    const mes = (d.getMonth() + 1).toString().padStart(2, '0');
                    const ano = d.getFullYear();
                    return `${dia}/${mes}/${ano}`;
                }

                const resultados = alvaras.map(alv => {
                    const [dia, mes, anoPart] = alv.data.split('/').map(Number);
                    let ano = anoPart;
                    if (ano < 100) ano += 2000;
                    const alvData = new Date(ano, mes - 1, dia);
                    const match = pagamentos.find(pg => Math.abs((alvData - pg.data) / (1000 * 60 * 60 * 24)) <= 6);
                    return {
                        data: alv.data,
                        link: alv.link,
                        status: match ? 'Registrado' : 'SEM REGISTRO',
                        pgData: match ? formatDate(match.data) : '',
                        pgValor: match ? match.valor : '',
                        pgRubrica: match ? match.rubrica : ''
                    };
                }).sort((a, b) => {
                    if (a.status === 'SEM REGISTRO' && b.status !== 'SEM REGISTRO') return -1;
                    if (b.status === 'SEM REGISTRO' && a.status !== 'SEM REGISTRO') return 1;
                    return 0;
                });

                // Render relatório
                const c = document.createElement('div');
                c.id = 'relatorioPagamentos';
                c.style.cssText = 'position:fixed;top:20px;left:20px;z-index:100000;background:#fff;border:2px solid #ff6600;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.18);min-width:300px;max-height:60vh;overflow:auto;font-family:sans-serif;';
                const closeBtn = document.createElement('button');
                closeBtn.textContent = '✕';
                closeBtn.style.cssText = 'position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:50%;width:24px;height:24px;cursor:pointer;';
                closeBtn.onclick = () => c.remove();
                c.appendChild(closeBtn);

                const header = document.createElement('div');
                header.textContent = 'Relatório de Alvarás vs Pagamentos';
                header.style.cssText = 'font-weight:bold;padding:8px 12px;color:#ff6600;';
                c.appendChild(header);

                const tbl = document.createElement('table');
                tbl.style.width = '100%';

                const thead = document.createElement('thead');
                const hr = document.createElement('tr');
                ['Data do Alvará', 'Data do Pagamento', 'Valor', 'Status'].forEach((h, idx) => {
                    const th = document.createElement('th');
                    th.textContent = h;
                    th.style.cssText = `padding:6px;font-size:13px;text-align:left;background:#f4f8ff;position:sticky;top:0;`;
                    hr.appendChild(th);
                });
                thead.appendChild(hr);
                tbl.appendChild(thead);

                const tbody = document.createElement('tbody');
                resultados.forEach(r => {
                    const tr = document.createElement('tr');
                    tr.style.cssText = 'border-bottom:1px solid #eee;';
                    // Data column with link
                    const tdData = document.createElement('td');
                    tdData.style.padding = '6px';
                    tdData.style.fontSize = '13px';
                    const link = document.createElement('a');
                    link.href = r.link;
                    link.target = '_blank';
                    link.textContent = r.data;
                    link.style.color = '#007bff';
                    link.style.textDecoration = 'none';
                    link.onmouseover = () => link.style.textDecoration = 'underline';
                    link.onmouseout = () => link.style.textDecoration = 'none';
                    tdData.appendChild(link);
                    tr.appendChild(tdData);
                    // Pg Data column
                    const tdPgData = document.createElement('td');
                    tdPgData.textContent = r.pgData;
                    tdPgData.style.padding = '6px';
                    tdPgData.style.fontSize = '13px';
                    tr.appendChild(tdPgData);
                    // Valor column
                    const tdValor = document.createElement('td');
                    tdValor.textContent = r.pgValor ? `${r.pgValor} (${r.pgRubrica})` : '';
                    tdValor.style.padding = '6px';
                    tdValor.style.fontSize = '13px';
                    tr.appendChild(tdValor);
                    // Status column
                    const tdStatus = document.createElement('td');
                    tdStatus.textContent = r.status;
                    tdStatus.style.padding = '6px';
                    tdStatus.style.fontSize = '13px';
                    tr.appendChild(tdStatus);
                    tbody.appendChild(tr);
                });
                tbl.appendChild(tbody);
                c.appendChild(tbl);
                document.body.appendChild(c);
            }, 2000); // Aguardar 2 segundos para carregamento dos dados
        }

        // Aguardar carregamento
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', gerarRelatorioPagamentos);
        } else {
            gerarRelatorioPagamentos();
        }
        return;
    }

    // Código original para página de detalhe
    console.log('[DOCS-EXEC+EDITAL] v3.8 iniciado');

    // ------------------------------------------------------------
    // Leitura da timeline + anexos relevantes (Serasa/CNIB) sem extração
    // ------------------------------------------------------------
    async function lerTimelineCompleta() {
        const seletores = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item'];
        let itens = [];
        for (const sel of seletores) {
            itens = document.querySelectorAll(sel);
            if (itens.length) break;
        }
        const documentos = [];

        // CORREÇÃO: usar grupo [1] do regex (não [12])
        function extrairUid(link) {
            const m = link.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
            return m ? m[1] : null;
        }
        function extrairData(item) {
            // A data correta é sempre a primeira ACIMA de cada ocorrência na timeline
            let dataElement = null;

            // Buscar o elemento .tl-data que está ACIMA do documento atual
            // Primeiro, tenta buscar .tl-data no elemento anterior (irmão anterior)
            let elementoAnterior = item.previousElementSibling;
            while (elementoAnterior) {
                dataElement = elementoAnterior.querySelector('.tl-data[name="dataItemTimeline"]');
                if (!dataElement) {
                    dataElement = elementoAnterior.querySelector('.tl-data');
                }
                if (dataElement) break;
                elementoAnterior = elementoAnterior.previousElementSibling;
            }

            // Se não encontrou no anterior, tenta dentro do próprio item (fallback)
            if (!dataElement) {
                dataElement = item.querySelector('.tl-data[name="dataItemTimeline"]') || item.querySelector('.tl-data');
            }

            const txt = dataElement?.textContent.trim() || '';

            // Primeiro tenta formato dd/mm/yyyy
            const m = txt.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
            if (m) return m[1];

            // Converte formato "20 out. 2025" para "20/10/25"
            const meses = {
                'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
                'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
            };

            const matchData = txt.match(/(\d{1,2})\s+(\w{3})\.\s+(\d{4})/);
            if (matchData) {
                const dia = matchData[1].padStart(2, '0');
                const mes = meses[matchData[2].toLowerCase()];
                let ano = matchData[3].slice(-2); // Últimos 2 dígitos
                ano = parseInt(ano) + 2000; // Converter para ano completo
                if (mes) {
                    return `${dia}/${mes}/${ano.toString().slice(-2)}`; // Manter formato yy
                }
            }

            return '';
        }

        for (let i = 0; i < itens.length; i++) {
            const item = itens[i];
            const textLink = item.querySelector('a.tl-documento:not([target])');
            if (!textLink) continue;
            const iconLink = item.querySelector('a.tl-documento[target="_blank"]');
            if (!iconLink) continue;

            const spans = textLink.querySelectorAll('span');
            if (spans.length < 4) continue;

            const tipoTexto = spans[2].textContent.trim().toLowerCase();
            const titulo = spans[3].textContent.trim().toLowerCase();
            const texto = textLink.textContent.trim();
            const low = texto.toLowerCase();
            const id = extrairUid(textLink) || `doc${i}`;
            let tipoEncontrado = null;

            if (low.includes('devolução de ordem')) {
                tipoEncontrado = 'Certidão devolução pesquisa';
            } else if (low.includes('certidão de oficial') || low.includes('oficial de justiça')) {
                tipoEncontrado = 'Certidão de oficial de justiça';
            } else if (low.includes('mandado de pagamento') && (low.includes('alvará') || low.includes('alvara'))) {
                tipoEncontrado = 'Alvará';
            } else if ((tipoTexto === 'certidão' || tipoTexto === 'documento diverso') && (titulo.includes('alvará') || titulo.includes('alvara'))) {
                tipoEncontrado = 'Alvará';
            } else if (tipoTexto === 'alvará' || tipoTexto === 'alvara') {
                tipoEncontrado = 'Alvará';
            } else if (low.includes('certidão') && low.includes('juntada de alvará')) {
                tipoEncontrado = 'Alvará';
            } else if (low.includes('sobrestamento')) {
                tipoEncontrado = 'Decisão (Sobrestamento)';
            } else if (low.includes('serasa') || low.includes('apjur') || low.includes('carta ação') || low.includes('carta acao')) {
                tipoEncontrado = 'SerasaAntigo';
            } else if (low.includes('edital')) {
                tipoEncontrado = 'Edital';
            }
            if (!tipoEncontrado) continue;

            // Registrar documento da timeline (pai)
            documentos.push({
                tipo: tipoEncontrado,
                texto,
                id,
                elemento: item,
                link: iconLink,
                data: extrairData(item),
                tipoTexto: tipoTexto,
                isAnexo: false
            });

            // Para certidões: buscar anexos Serasa/CNIB
            const isCertAlvo = (
                tipoEncontrado === 'Certidão devolução pesquisa' ||
                tipoEncontrado === 'Certidão de oficial de justiça'
            );
            if (isCertAlvo) {
                const anexosRoot = item.querySelector('pje-timeline-anexos');
                const toggle = item.querySelector('pje-timeline-anexos div[name="mostrarOuOcultarAnexos"]');
                let anexoLinks = anexosRoot ? anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]') : [];
                if ((!anexoLinks || anexoLinks.length === 0) && toggle) {
                    try { toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); } catch (e) { }
                    await sleep(350);
                    anexoLinks = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                }
                if (anexoLinks && anexoLinks.length) {
                    Array.from(anexoLinks).forEach(anexo => {
                        const t = (anexo.textContent || '').toLowerCase();
                        const parentData = extrairData(item);
                        if (/serasa|serasajud/.test(t)) {
                            documentos.push({
                                tipo: 'Serasa',
                                texto: anexo.textContent.trim(),
                                id: anexo.id || `serasa_${id}`,
                                elemento: anexo,
                                link: anexo,
                                data: parentData,
                                isAnexo: true,
                                parentId: id
                            });
                        } else if (/cnib|indisp/.test(t)) {
                            documentos.push({
                                tipo: 'CNIB',
                                texto: anexo.textContent.trim(),
                                id: anexo.id || `cnib_${id}`,
                                elemento: anexo,
                                link: anexo,
                                data: parentData,
                                isAnexo: true,
                                parentId: id
                            });
                        }
                    });
                }
            }
        }
        return documentos;
    }

    // ------------------------------------------------------------
    // Relatório de Execução (Check)
    // ------------------------------------------------------------
    function gerarListaSimples(docs) {
        document.getElementById('listaDocsExecucaoSimples')?.remove();

        // Filtros - exclui editais do relatório de execução
        docs = docs.filter(d => {
            try {
                const tipo = (d.tipo || '').toString().toLowerCase();
                const texto = (d.texto || '').toString().toLowerCase();
                if (tipo === 'edital') return false; // Excluir editais
                if (/expedi[cç][aã]o/.test(tipo) && /ordem/.test(tipo)) return false;
                if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
                if (tipo === 'alvará' || texto.includes('alvar')) {
                    if (/(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto)) return false;
                }
            } catch (e) { }
            return true;
        });

        // Índice para lookup por id (pai/anexo)
        const docIndex = new Map();
        docs.forEach(d => docIndex.set(d.id, d));

        // Ordenação data desc
        const byDataDesc = (a, b) => {
            const da = (a.data || '').split('/').reverse().join('').padEnd(8, '0');
            const db = (b.data || '').split('/').reverse().join('').padEnd(8, '0');
            return db.localeCompare(da);
        };

        // Predicados
        const isCertDevolucao = (d) => (d.tipo || '').toLowerCase().includes('certidão devolução');
        const isCertOficial = (d) => (d.tipo || '').toLowerCase().includes('certidão de oficial');
        const isAlvara = (d) => (d.tipo || '').toLowerCase() === 'alvará';
        const isSobrest = (d) => (d.tipo || '').toLowerCase().includes('sobrestamento');
        const isSerasaAntigo = (d) => (d.tipo || '') === 'SerasaAntigo';

        // Construção dos blocos
        const certs = docs.filter(d => isCertDevolucao(d) || isCertOficial(d)).sort(byDataDesc);
        const serasaAntigos = docs.filter(isSerasaAntigo).sort(byDataDesc);
        const alvaras = docs.filter(isAlvara).sort(byDataDesc);
        const sobrests = docs.filter(isSobrest).sort(byDataDesc);
        const usados = new Set();
        const saida = [];

        // Bloco 1: Certidões + anexos; ignorar "oficial" sem Serasa/CNIB
        for (const cert of certs) {
            const anexos = docs
                .filter(x => x.parentId === cert.id && (x.tipo === 'Serasa' || x.tipo === 'CNIB'))
                .sort(byDataDesc);
            const ehOficial = isCertOficial(cert);
            const temAx = anexos.length > 0;
            if (ehOficial && !temAx) continue;

            usados.add(cert.id);
            saida.push({ ...cert, _displayLabel: 'Pesquisa' });
            for (const ax of anexos) {
                usados.add(ax.id);
                saida.push({ ...ax, _displayLabel: ax.tipo }); // Serasa/CNIB
            }
        }

        // SerasaAntigo (timeline)
        for (const s of serasaAntigos) {
            if (usados.has(s.id)) continue;
            usados.add(s.id);
            saida.push({ ...s, _displayLabel: 'SerasaAntigo' });
        }

        // Bloco 2: Alvarás
        for (const alv of alvaras) {
            if (usados.has(alv.id)) continue;
            usados.add(alv.id);
            const displayLabel = (alv.tipoTexto === 'alvará' || alv.tipoTexto === 'alvara') ? 'Alvará (Alvará)' : 'Alvará';
            saida.push({ ...alv, _displayLabel: displayLabel });
        }

        // Bloco 3: Sobrestamentos
        for (const sb of sobrests) {
            if (usados.has(sb.id)) continue;
            usados.add(sb.id);
            saida.push({ ...sb, _displayLabel: 'Sobrestamento' });
        }

        // Restante por data desc
        const outros = docs.filter(d => !usados.has(d.id)).sort(byDataDesc);
        for (const o of outros) {
            saida.push({ ...o, _displayLabel: o.tipo || 'Documento' });
        }

        // Render
        const c = document.createElement('div');
        c.id = 'listaDocsExecucaoSimples';
        c.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:100000;background:#fff;border:2px solid #007bff;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.18);min-width:360px;max-height:60vh;overflow:auto;font-family:sans-serif;';
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:50%;width:24px;height:24px;cursor:pointer;';
        closeBtn.onclick = () => c.remove();
        c.appendChild(closeBtn);

        const header = document.createElement('div');
        header.textContent = 'Relatório de Medidas';
        header.style.cssText = 'font-weight:bold;padding:8px 12px;color:#007bff;';
        c.appendChild(header);

        const tbl = document.createElement('table');
        tbl.style.width = '100%';
        tbl.id = 'tblExecucaoLista'; // MELHORIA: ID único para referência

        const thead = document.createElement('thead');
        const hr = document.createElement('tr');
        ['Documento', 'Data', 'ID'].forEach((h, idx) => {
            const th = document.createElement('th');
            th.textContent = h;
            th.style.cssText = `padding:6px;font-size:13px;text-align:${idx === 0 ? 'left' : idx === 1 ? 'center' : 'right'};background:#f4f8ff;position:sticky;top:0;`;
            hr.appendChild(th);
        });
        thead.appendChild(hr);
        tbl.appendChild(thead);

        const tbody = document.createElement('tbody');

        // MELHORIA 2: Usar event delegation com data-attributes para robustez
        saida.forEach((d, idx) => {
            const tr = document.createElement('tr');
            tr.style.cssText = 'cursor:pointer;border-bottom:1px solid #eee;';
            tr.dataset.docIndex = idx; // Índice para busca posterior
            tr.dataset.docId = d.id;   // ID do documento

            const cols = [
                d._displayLabel || d.tipo || 'Documento',
                d.data || '',
                d.id || ''
            ];
            cols.forEach((val, idx) => {
                const td = document.createElement('td');
                td.textContent = val;
                td.style.padding = '6px';
                td.style.fontSize = '13px';
                td.style.textAlign = idx === 0 ? 'left' : idx === 1 ? 'center' : 'right';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        tbl.appendChild(tbody);
        c.appendChild(tbl);

        // Botão Baixar (aparece após Check ser clicado)
        const btnBaixarContainer = document.createElement('div');
        btnBaixarContainer.style.cssText = 'padding:8px;border-top:1px solid #ddd;';
        const btnBaixar = document.createElement('button');
        btnBaixar.id = 'btnBaixarAuto';
        btnBaixar.textContent = '🔴 Baixar Serasa/CNIB';
        btnBaixar.style.cssText = 'width:100%;padding:8px;background:#dc3545;color:#fff;border:none;cursor:pointer;font-weight:bold;border-radius:4px;';
        btnBaixar.onclick = executarBaixarAutomatico;
        btnBaixarContainer.appendChild(btnBaixar);
        c.appendChild(btnBaixarContainer);

        document.body.appendChild(c);

        // MELHORIA 2: Event delegation na tabela (não em cada tr)
        tbl.addEventListener('click', async (ev) => {
            const tr = ev.target.closest('tr');
            if (!tr || !tr.dataset.docIndex) return;

            ev.stopPropagation();
            const docIndex = parseInt(tr.dataset.docIndex, 10);
            const d = saida[docIndex];

            if (!d) return;

            // Remover destaque anterior
            tbody.querySelectorAll('tr').forEach(r => r.classList.remove('doc-exec-row-clicked'));

            // Marcar linha clicada
            tr.classList.add('doc-exec-row-clicked');

            try {
                if (d.isAnexo && (d.tipo === 'Serasa' || d.tipo === 'CNIB') && d.link) {
                    // Fechar modais anteriores
                    const closeButtons = document.querySelectorAll('button.ui-dialog-titlebar-close, .ui-dialog-titlebar-close');
                    closeButtons.forEach(btn => {
                        try { btn.click(); } catch(e) {}
                    });
                    await sleep(500);

                    // Abrir anexo - MELHORIA: Refrescar referência do elemento
                    const linkElementoFresh = document.querySelector(`a[id="${d.link.id}"]`) || d.link;
                    linkElementoFresh.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                    await sleep(1500);

                    // Destacar anexo
                    const elementoFresh = document.querySelector(`[id="${d.elemento.id}"]`) || d.elemento;
                    elementoFresh?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    elementoFresh?.classList.add('doc-exec-destaque');
                    setTimeout(() => elementoFresh?.classList.remove('doc-exec-destaque'), 3000);

                    // Procurar certificado
                    let certIcon = null;
                    const selectors = [
                        'i.fa.fa-certificate.fa-lg',
                        '.fa-certificate',
                        'button[title*="certificado"]',
                        'button[title*="Certificado"]',
                        '[data-tooltip*="certificado"]',
                        '[data-tooltip*="Certificado"]'
                    ];

                    for (const selector of selectors) {
                        certIcon = document.querySelector(selector);
                        if (certIcon) break;
                    }

                    if (certIcon) {
                        const clickable = certIcon.closest('button') || certIcon;
                        if (clickable) {
                            clickable.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                        }
                    }

                    // Selecionar pai
                    if (d.parentId) {
                        const pai = docIndex.get(d.parentId);
                        if (pai?.elemento) {
                            const paiElementoFresh = document.querySelector(`[id="${pai.elemento.id}"]`) || pai.elemento;
                            paiElementoFresh.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paiElementoFresh.classList.add('doc-exec-destaque');
                            setTimeout(() => paiElementoFresh.classList.remove('doc-exec-destaque'), 3000);
                        }
                    }
                } else {
                    // Itens normais
                    const elementoFresh = document.querySelector(`[id="${d.elemento.id}"]`) || d.elemento;
                    elementoFresh?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    elementoFresh?.classList.add('doc-exec-destaque');
                    setTimeout(() => elementoFresh?.classList.remove('doc-exec-destaque'), 3000);
                }
            } catch (e) {
                console.error('[LISTA] Erro ao clicar linha:', e);
                d.elemento?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    // ------------------------------------------------------------
    // Relatório de Editais
    // ------------------------------------------------------------
    function gerarListaEditais(docs) {
        document.getElementById('listaDocsEditalSimples')?.remove();

        // Filtrar apenas editais
        const editais = docs.filter(d => d.tipo === 'Edital');

        // Ordenação data desc
        const byDataDesc = (a, b) => {
            const da = (a.data || '').split('/').reverse().join('').padEnd(8, '0');
            const db = (b.data || '').split('/').reverse().join('').padEnd(8, '0');
            return db.localeCompare(da);
        };

        const saida = editais.sort(byDataDesc).map(edital => ({ ...edital, _displayLabel: 'Edital' }));

        // Render
        const c = document.createElement('div');
        c.id = 'listaDocsEditalSimples';
        c.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:100000;background:#fff;border:2px solid #28a745;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.18);min-width:360px;max-height:60vh;overflow:auto;font-family:sans-serif;';
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:50%;width:24px;height:24px;cursor:pointer;';
        closeBtn.onclick = () => c.remove();
        c.appendChild(closeBtn);

        const header = document.createElement('div');
        header.textContent = 'Relatório de Editais';
        header.style.cssText = 'font-weight:bold;padding:8px 12px;color:#28a745;';
        c.appendChild(header);

        if (saida.length === 0) {
            const noData = document.createElement('div');
            noData.textContent = 'Nenhum edital encontrado na timeline';
            noData.style.cssText = 'padding:20px;text-align:center;color:#666;font-style:italic;';
            c.appendChild(noData);
        } else {
            const tbl = document.createElement('table');
            tbl.style.width = '100%';

            const thead = document.createElement('thead');
            const hr = document.createElement('tr');
            ['Documento', 'Data', 'ID'].forEach((h, idx) => {
                const th = document.createElement('th');
                th.textContent = h;
                th.style.cssText = `padding:6px;font-size:13px;text-align:${idx === 0 ? 'left' : idx === 1 ? 'center' : 'right'};background:#f4f8ff;position:sticky;top:0;`;
                hr.appendChild(th);
            });
            thead.appendChild(hr);
            tbl.appendChild(thead);

            const tbody = document.createElement('tbody');

            saida.forEach(d => {
                const tr = document.createElement('tr');
                tr.style.cssText = 'cursor:pointer;border-bottom:1px solid #eee;';
                tr.onclick = async (ev) => {
                    ev.stopPropagation();
                    tr.classList.add('doc-edital-row-clicked');

                    try {
                        d.elemento?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        d.elemento?.classList.add('doc-edital-destaque');
                        setTimeout(() => d.elemento?.classList.remove('doc-edital-destaque'), 3000);
                    } catch (e) {
                        d.elemento?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                };

                const cols = [
                    d._displayLabel || d.tipo || 'Documento',
                    d.data || '',
                    d.id || ''
                ];
                cols.forEach((val, idx) => {
                    const td = document.createElement('td');
                    td.textContent = val;
                    td.style.padding = '6px';
                    td.style.fontSize = '13px';
                    td.style.textAlign = idx === 0 ? 'left' : idx === 1 ? 'center' : 'right';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });

            tbl.appendChild(tbody);
            c.appendChild(tbl);
        }

        document.body.appendChild(c);
    }

    // Destaques CSS (elemento na timeline + linha clicada)
    const style = document.createElement('style');
    style.textContent = `
        .doc-exec-destaque { outline:3px solid #007bff; background:#e7f3ff !important; }
        #listaDocsExecucaoSimples tr.doc-exec-row-clicked { background:#fff7d6 !important; }
        .doc-edital-destaque { outline:3px solid #28a745; background:#e8f5e8 !important; }
        #listaDocsEditalSimples tr.doc-edital-row-clicked { background:#fff7d6 !important; }
    `;
    document.head.appendChild(style);

    // Fluxo principal e botões
    async function executarCheck() {
        const docs = await lerTimelineCompleta();
        gerarListaSimples(docs);
    }

    async function executarEdital() {
        const docs = await lerTimelineCompleta();
        gerarListaEditais(docs);
    }

    // ============================================================
    // Fluxo de Baixar Serasa/CNIB com Destaque Vermelho
    // Usa a mesma lista do Check, marca itens baixados em vermelho
    // ============================================================
    async function executarBaixarAutomatico() {
        const docs = await lerTimelineCompleta();

        // Filtrar apenas Serasa e CNIB (anexos)
        const serasaCnib = docs.filter(d =>
            (d.tipo === 'Serasa' || d.tipo === 'CNIB') && d.isAnexo
        );

        if (serasaCnib.length === 0) {
            console.log('[BAIXAR] Nenhum Serasa/CNIB encontrado');
            alert('Nenhum Serasa/CNIB para baixar');
            return;
        }

        console.log(`[BAIXAR] Iniciando download automático de ${serasaCnib.length} itens`);

        // Processar cada item sequencialmente
        for (let i = 0; i < serasaCnib.length; i++) {
            const item = serasaCnib[i];
            console.log(`[BAIXAR] ${i + 1}/${serasaCnib.length}: ${item.tipo} - ${item.id}`);

            try {
                // 1. Fechar qualquer modal aberto
                const closeButtons = document.querySelectorAll('button.ui-dialog-titlebar-close, .ui-dialog-titlebar-close');
                closeButtons.forEach(btn => {
                    try { btn.click(); } catch(e) {}
                });
                await sleep(300);

                // 2. Clicar no anexo para abrir documento
                if (item.link) {
                    item.link.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                    await sleep(1500);
                }

                // 3. Procurar e clicar no ícone de certificado (fa-certificate)
                let certIcon = null;
                const selectors = [
                    'i.fa.fa-certificate.fa-lg',
                    '.fa-certificate',
                    'button[title*="certificado"]',
                    'button[title*="Certificado"]'
                ];

                for (const selector of selectors) {
                    certIcon = document.querySelector(selector);
                    if (certIcon) break;
                }

                if (certIcon) {
                    const clickable = certIcon.closest('button') || certIcon;
                    if (clickable) {
                        clickable.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                        console.log(`[BAIXAR] ✓ Certificado clicado para ${item.tipo}`);
                        await sleep(800);
                    }
                }

                // 4. Marcar como baixado na lista do Check (fundo vermelho)
                const tabelaCheck = document.getElementById('tblExecucaoLista');
                if (tabelaCheck) {
                    const linhas = tabelaCheck.querySelectorAll('tbody tr');
                    linhas.forEach(tr => {
                        // Comparar ID da linha com ID do item
                        if (tr.dataset.docId === item.id) {
                            tr.style.backgroundColor = '#ff4444';
                            tr.style.color = '#fff';
                            tr.style.fontWeight = 'bold';
                        }
                    });
                }

                // 5. Aguardar um pouco antes do próximo item
                await sleep(500);

            } catch (e) {
                console.error(`[BAIXAR] Erro ao processar ${item.id}:`, e);
            }
        }

        console.log(`[BAIXAR] ✓ Download completo! ${serasaCnib.length} itens processados`);
    }

    // ============================================================
    // PAINEL DE CONTROLE CENTRALIZADO (Check, Edital, Pgto, Sigilo)
    // ============================================================
    const painel = document.createElement('div');
    painel.id = 'pjeplus-painel-controle';
    painel.style.cssText = 'position:fixed;bottom:170px;right:20px;z-index:99999;background:#fff;border:2px solid #333;border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.25);padding:12px;font-family:sans-serif;';

    const titulo = document.createElement('div');
    titulo.textContent = 'PJePlus v4.0';
    titulo.style.cssText = 'font-weight:bold;margin-bottom:10px;color:#333;font-size:13px;text-align:center;border-bottom:1px solid #ddd;padding-bottom:8px;';
    painel.appendChild(titulo);

    const gridBotoes = document.createElement('div');
    gridBotoes.style.cssText = 'display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;';

    const botoes = [
        { id: 'btnCheck', texto: '📋 Check', bg: '#007bff', fn: executarCheck },
        { id: 'btnEdital', texto: '📋 Edital', bg: '#28a745', fn: executarEdital },
        { id: 'btnSigilo', texto: '🔐 Sigilo', bg: '#d9534f', fn: aplicarVisibilidadeSigilosos },
        { id: 'btnPgto', texto: '💰 Pgto', bg: '#ff6600', fn: () => {
            (async () => {
                const docs = await lerTimelineCompleta();
                let filteredDocs = docs.filter(d => {
                    try {
                        const tipo = (d.tipo || '').toString().toLowerCase();
                        const texto = (d.texto || '').toString().toLowerCase();
                        if (tipo === 'edital') return false;
                        if (/expedi[cç][aã]o/.test(tipo) && /ordem/.test(tipo)) return false;
                        if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
                        if (tipo === 'alvará' || texto.includes('alvar')) {
                            if (/(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto)) return false;
                        }
                    } catch (e) { }
                    return true;
                });
                const alvaras = filteredDocs.filter(d => (d.tipo || '').toLowerCase() === 'alvará' && d.data);
                const alvarasData = alvaras.map(a => ({ data: a.data, link: a.link.getAttribute('href') }));
                localStorage.setItem('pjeplus_alvaras', JSON.stringify(alvarasData));
                const url = window.location.href;
                const match = url.match(/\/processo\/(\d+)\//);
                if (match) {
                    const id = match[1];
                    const pgtoUrl = `https://pje.trt2.jus.br/pjekz/pagamento/${id}/cadastro`;
                    window.open(pgtoUrl, '_blank');
                }
            })();
        }},
        { id: 'btnSISB', texto: '📊 SISBAJUD', bg: '#6f42c1', fn: executarSISBAJUD }
    ];

    botoes.forEach(btn => {
        const botao = document.createElement('button');
        botao.id = btn.id;
        botao.textContent = btn.texto;
        botao.style.cssText = `padding:8px;background:${btn.bg};color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:bold;font-size:12px;`;
        botao.onmouseover = () => botao.style.opacity = '0.9';
        botao.onmouseout = () => botao.style.opacity = '1';
        botao.onclick = btn.fn;
        gridBotoes.appendChild(botao);
    });

    painel.appendChild(gridBotoes);
    document.body.appendChild(painel);

})();