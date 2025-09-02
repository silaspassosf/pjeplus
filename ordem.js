// ==UserScript==
// @name         Documentos Execução - OTIMIZADO v3.7
// @namespace    http://tampermonkey.net/
// @version      3.7
// @description  Relatório unificado: Certidões(+Serasa/CNIB anexos) → SerasaAntigo (timeline) → Alvarás → Sobrestamentos; rótulos curtos; filtro Alvará; evitar cliques indevidos; abrir Serasa/CNIB com clique automático no certificado; seleção e destaque de anexos; marcação de linha clicada.
// @author       PjePlus
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @grant        none
// ==/UserScript==
(function() {
    'use strict';
    console.log('[DOCS-EXEC] v3.7 iniciado');

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

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
            const dEl = item.querySelector('.tl-data[name="dataItemTimeline"]') || item.querySelector('.tl-data');
            const txt = dEl?.textContent.trim() || '';
            const m = txt.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
            return m ? m[1] : '';
        }

        for (let i = 0; i < itens.length; i++) {
            const item = itens[i];
            const link = item.querySelector('a.tl-documento:not([target])');
            if (!link) continue;

            const texto = link.textContent.trim();
            const low = texto.toLowerCase();
            const id = extrairUid(link) || `doc${i}`;
            let tipoEncontrado = null;

            if (low.includes('devolução de ordem')) {
                tipoEncontrado = 'Certidão devolução pesquisa';
            } else if (low.includes('certidão de oficial') || low.includes('oficial de justiça')) {
                tipoEncontrado = 'Certidão de oficial de justiça';
            } else if (low.includes('alvará') || low.includes('alvara')) {
                tipoEncontrado = 'Alvará';
            } else if (low.includes('sobrestamento')) {
                tipoEncontrado = 'Decisão (Sobrestamento)';
            } else if (low.includes('serasa') || low.includes('apjur') || low.includes('carta ação') || low.includes('carta acao')) {
                tipoEncontrado = 'SerasaAntigo';
            }
            if (!tipoEncontrado) continue;

            // Registrar documento da timeline (pai)
            documentos.push({
                tipo: tipoEncontrado,
                texto,
                id,
                elemento: item,
                link,
                data: extrairData(item),
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
                    try { toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); } catch(e) {}
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

    function gerarListaSimples(docs) {
        document.getElementById('listaDocsExecucaoSimples')?.remove();

        // Filtros
        docs = docs.filter(d => {
            try {
                const tipo = (d.tipo||'').toString().toLowerCase();
                const texto = (d.texto||'').toString().toLowerCase();
                if (/expedi[cç][aã]o/.test(tipo) && /ordem/.test(tipo)) return false;
                if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
                if (tipo === 'alvará' || texto.includes('alvar')) {
                    if (/(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto)) return false;
                }
            } catch (e) {}
            return true;
        });

        // Índice para lookup por id (pai/anexo)
        const docIndex = new Map();
        docs.forEach(d => docIndex.set(d.id, d));

        // Ordenação data desc
        const byDataDesc = (a, b) => {
            const da = (a.data||'').split('/').reverse().join('').padEnd(8, '0');
            const db = (b.data||'').split('/').reverse().join('').padEnd(8, '0');
            return db.localeCompare(da);
        };

        // Predicados
        const isCertDevolucao = (d) => (d.tipo||'').toLowerCase().includes('certidão devolução');
        const isCertOficial  = (d) => (d.tipo||'').toLowerCase().includes('certidão de oficial');
        const isAlvara       = (d) => (d.tipo||'').toLowerCase() === 'alvará';
        const isSobrest      = (d) => (d.tipo||'').toLowerCase().includes('sobrestamento');
        const isSerasaAntigo = (d) => (d.tipo||'') === 'SerasaAntigo';

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
            saida.push({...cert, _displayLabel: 'Pesquisa'});
            for (const ax of anexos) {
                usados.add(ax.id);
                saida.push({...ax, _displayLabel: ax.tipo}); // Serasa/CNIB
            }
        }

        // SerasaAntigo (timeline)
        for (const s of serasaAntigos) {
            if (usados.has(s.id)) continue;
            usados.add(s.id);
            saida.push({...s, _displayLabel: 'SerasaAntigo'});
        }

        // Bloco 2: Alvarás
        for (const alv of alvaras) {
            if (usados.has(alv.id)) continue;
            usados.add(alv.id);
            saida.push({...alv, _displayLabel: 'Alvará'});
        }

        // Bloco 3: Sobrestamentos
        for (const sb of sobrests) {
            if (usados.has(sb.id)) continue;
            usados.add(sb.id);
            saida.push({...sb, _displayLabel: 'Sobrestamento'});
        }

        // Restante por data desc
        const outros = docs.filter(d => !usados.has(d.id)).sort(byDataDesc);
        for (const o of outros) {
            saida.push({...o, _displayLabel: o.tipo || 'Documento'});
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

        const thead = document.createElement('thead');
        const hr = document.createElement('tr');
        ['Documento', 'Data', 'ID'].forEach((h, idx) => {
            const th = document.createElement('th');
            th.textContent = h;
            th.style.cssText = `padding:6px;font-size:13px;text-align:${idx===0?'left':idx===1?'center':'right'};background:#f4f8ff;position:sticky;top:0;`;
            hr.appendChild(th);
        });
        thead.appendChild(hr);
        tbl.appendChild(thead);

        const tbody = document.createElement('tbody');

        // Clique: abrir/selecionar e marcar linha
        saida.forEach(d => {
            const tr = document.createElement('tr');
            tr.style.cssText = 'cursor:pointer;border-bottom:1px solid #eee;';
            tr.onclick = async (ev) => {
                ev.stopPropagation();
                // marcação persistente da linha clicada
                tr.classList.add('doc-exec-row-clicked');

                try {
                    if (d.isAnexo && (d.tipo === 'Serasa' || d.tipo === 'CNIB') && d.link) {
                        // Abrir anexo
                        d.link.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                        // Destacar o anexo na timeline
                        d.elemento?.scrollIntoView({ behavior:'smooth', block:'center' });
                        d.elemento?.classList.add('doc-exec-destaque');
                        setTimeout(() => d.elemento?.classList.remove('doc-exec-destaque'), 3000);

                        await sleep(1000);
                        // Tentar acionar ícone de certificado (quando existir)
                        const certIcon = document.querySelector('i.fa.fa-certificate.fa-lg');
                        const clickable = certIcon?.closest('button') || certIcon;
                        if (clickable) clickable.dispatchEvent(new MouseEvent('click', { bubbles: true }));

                        // Selecionar também o item pai (certidão) na timeline
                        if (d.parentId) {
                            const pai = docIndex.get(d.parentId);
                            if (pai?.elemento) {
                                pai.elemento.scrollIntoView({ behavior:'smooth', block:'center' });
                                pai.elemento.classList.add('doc-exec-destaque');
                                setTimeout(() => pai.elemento.classList.remove('doc-exec-destaque'), 3000);
                            }
                        }
                    } else {
                        // Itens normais: rolar e destacar
                        d.elemento?.scrollIntoView({ behavior:'smooth', block:'center' });
                        d.elemento?.classList.add('doc-exec-destaque');
                        setTimeout(() => d.elemento?.classList.remove('doc-exec-destaque'), 3000);
                    }
                } catch(e) {
                    d.elemento?.scrollIntoView({ behavior:'smooth', block:'center' });
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
                td.style.textAlign = idx===0?'left':idx===1?'center':'right';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        tbl.appendChild(tbody);
        c.appendChild(tbl);
        document.body.appendChild(c);
    }

    // Destaques CSS (elemento na timeline + linha clicada)
    const style = document.createElement('style');
    style.textContent = `
        .doc-exec-destaque { outline:3px solid #007bff; background:#e7f3ff !important; }
        #listaDocsExecucaoSimples tr.doc-exec-row-clicked { background:#fff7d6 !important; }
    `;
    document.head.appendChild(style);

    // Fluxo principal e botão 📋 Check
    async function executar() {
        const docs = await lerTimelineCompleta();
        gerarListaSimples(docs);
    }
    const btn = document.createElement('button');
    btn.id = 'btnDocsExecucao';
    btn.textContent = '📋 Check';
    btn.style.cssText = 'position:fixed;bottom:80px;right:20px;background:#007bff;color:#fff;padding:10px;border:none;border-radius:5px;cursor:pointer;z-index:99999';
    btn.onclick = executar;
    document.body.appendChild(btn);
})();