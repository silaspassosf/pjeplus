// ==UserScript==
// @name         Documentos Edital - v1.0
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Relatório de Editais: Filtra apenas editais da timeline com seleção e destaque; marcação de linha clicada.
// @author       PjePlus
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @grant        none
// ==/UserScript==
(function () {
    'use strict';
    console.log('[DOCS-EDITAL] v1.0 iniciado');

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    // ------------------------------------------------------------
    // Leitura da timeline + filtragem apenas de Editais
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

            // Filtrar apenas editais
            if (low.includes('edital')) {
                tipoEncontrado = 'Edital';
            }

            if (!tipoEncontrado) continue;

            // Registrar documento da timeline
            documentos.push({
                tipo: tipoEncontrado,
                texto,
                id,
                elemento: item,
                link,
                data: extrairData(item),
                isAnexo: false
            });
        }
        return documentos;
    }

    function gerarListaSimples(docs) {
        document.getElementById('listaDocsEditalSimples')?.remove();

        // Índice para lookup por id
        const docIndex = new Map();
        docs.forEach(d => docIndex.set(d.id, d));

        // Ordenação data desc
        const byDataDesc = (a, b) => {
            const da = (a.data || '').split('/').reverse().join('').padEnd(8, '0');
            const db = (b.data || '').split('/').reverse().join('').padEnd(8, '0');
            return db.localeCompare(da);
        };

        // Ordenar editais por data decrescente
        const editais = docs.filter(d => d.tipo === 'Edital').sort(byDataDesc);
        const saida = [];

        // Adicionar todos os editais encontrados
        for (const edital of editais) {
            saida.push({ ...edital, _displayLabel: 'Edital' });
        }

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

            // Clique: abrir/selecionar e marcar linha
            saida.forEach(d => {
                const tr = document.createElement('tr');
                tr.style.cssText = 'cursor:pointer;border-bottom:1px solid #eee;';
                tr.onclick = async (ev) => {
                    ev.stopPropagation();
                    // marcação persistente da linha clicada
                    tr.classList.add('doc-edital-row-clicked');

                    try {
                        // Rolar e destacar o edital na timeline
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
        .doc-edital-destaque { outline:3px solid #28a745; background:#e8f5e8 !important; }
        #listaDocsEditalSimples tr.doc-edital-row-clicked { background:#fff7d6 !important; }
    `;
    document.head.appendChild(style);

    // Fluxo principal e botão 📋 Edital
    async function executar() {
        const docs = await lerTimelineCompleta();
        gerarListaSimples(docs);
    }

    const btn = document.createElement('button');
    btn.id = 'btnDocsEdital';
    btn.textContent = '📋 Edital';
    btn.style.cssText = 'position:fixed;bottom:190px;right:20px;background:#28a745;color:#fff;padding:10px;border:none;border-radius:5px;cursor:pointer;z-index:99999';
    btn.onclick = executar;
    document.body.appendChild(btn);
})();
