'use strict';

// ── Predicados ──────────────────────────────────────────────────
window.isCertDevolucao = d => d.tipo.toLowerCase().includes('certidão devolução');
window.isCertOficial = d => d.tipo.toLowerCase().includes('certidão de oficial');
window.isAlvara = d => d.tipo.toLowerCase() === 'alvarás';
window.isSobrest = d => d.tipo.toLowerCase().includes('sobrestamento');
window.isSerasaAntigo = d => d.tipo === 'SerasaAntigo';

window.byDataDesc = (a, b) => {
    const da = (a.data || '').split('/').reverse().join('').padEnd(8, '0');
    const db = (b.data || '').split('/').reverse().join('').padEnd(8, '0');
    return db.localeCompare(da);
};

window.filtrarDocs = function (docs) {
    return docs.filter(d => {
        const tipo = (d.tipo || '').toLowerCase();
        const texto = (d.texto || '').toLowerCase();
        if (tipo === 'edital') return false;
        if (/expedi[cç][aã]o/.test(tipo) && /ordem/.test(tipo)) return false;
        if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
        if ((tipo === 'alvarás') && /(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto))
            return false;
        return true;
    });
}

window.construirOrdem = function (docs) {
    const usados = new Set();
    const saida = [];
    const certsDev = docs.filter(d => isCertDevolucao(d) || isCertOficial(d)).sort(byDataDesc);

    for (const cert of certsDev) {
        const anexos = docs
            .filter(x => x.parentId === cert.id && (x.tipo === 'Serasa' || x.tipo === 'CNIB'))
            .sort(byDataDesc);
        if (isCertOficial(cert) && !anexos.length) continue;
        usados.add(cert.id);
        saida.push({ ...cert, _label: 'Pesquisa' });
        for (const ax of anexos) {
            usados.add(ax.id);
            saida.push({ ...ax, _label: ax.tipo });
        }
    }
    docs.filter(isSerasaAntigo).sort(byDataDesc).forEach(s => {
        if (usados.has(s.id)) return;
        usados.add(s.id);
        saida.push({ ...s, _label: 'SerasaAntigo' });
    });
    docs.filter(isAlvara).sort(byDataDesc).forEach(a => {
        if (usados.has(a.id)) return;
        usados.add(a.id);
        saida.push({ ...a, _label: 'Alvarás' });
    });
    docs.filter(isSobrest).sort(byDataDesc).forEach(s => {
        if (usados.has(s.id)) return;
        usados.add(s.id);
        saida.push({ ...s, _label: 'Sobrestamento' });
    });
    docs.filter(d => !usados.has(d.id)).sort(byDataDesc).forEach(o => {
        saida.push({ ...o, _label: o.tipo || 'Documento' });
    });
    return saida;
}

window.renderTabela = function (id, titulo, corBorda, saida, onRowClick) {
    document.getElementById(id)?.remove();
    const c = document.createElement('div');
    c.id = id;
    c.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:100000;background:#fff;` +
        `border:2px solid ${corBorda};border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.18);` +
        `min-width:360px;max-height:60vh;overflow:auto;font-family:sans-serif;`;

    // Header com título e botão fechar
    const hdr = document.createElement('div');
    hdr.style.cssText = `position:sticky;top:0;background:#fff;border-bottom:1px solid #eee;` +
        `display:flex;align-items:center;justify-content:space-between;padding:8px 12px;`;
    hdr.innerHTML = `<span style="font-weight:bold;color:${corBorda};font-size:13px">${titulo}</span>` +
        `<button style="background:#dc3545;color:#fff;border:none;border-radius:50%;` +
        `width:24px;height:24px;cursor:pointer;font-size:14px;line-height:1">✕</button>`;
    hdr.querySelector('button').onclick = () => c.remove();
    c.appendChild(hdr);

    if (!saida.length) {
        const nd = document.createElement('div');
        nd.textContent = 'Nenhum item encontrado';
        nd.style.cssText = 'padding:20px;text-align:center;color:#666;font-style:italic;';
        c.appendChild(nd);
        document.body.appendChild(c);
        return;
    }

    // Tabela com event delegation (evita N listeners)
    const tbl = document.createElement('table');
    tbl.id = `${id}_tbl`;
    tbl.style.width = '100%';
    tbl.innerHTML = `<thead><tr>${['Documento', 'Data', 'ID'].map((h, i) =>
        `<th style="padding:6px;font-size:12px;text-align:${i === 0 ? 'left' : i === 1 ? 'center' : 'right'};` +
        `background:#f4f8ff;position:sticky;top:41px">${h}</th>`
    ).join('')
        }</tr></thead><tbody></tbody>`;

    const tbody = tbl.querySelector('tbody');
    saida.forEach((d, idx) => {
        const tr = document.createElement('tr');
        tr.style.cssText = 'cursor:pointer;border-bottom:1px solid #eee;';
        tr.dataset.idx = idx;
        tr.dataset.docId = d.id;
        [
            d._label || d.tipo || 'Documento',
            d.data || '',
            d.id || '',
        ].forEach((val, i) => {
            const td = document.createElement('td');
            td.textContent = val;
            td.style.cssText = `padding:5px 6px;font-size:12px;` +
                `text-align:${i === 0 ? 'left' : i === 1 ? 'center' : 'right'}`;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    // Event delegation – 1 listener para toda a tabela
    tbl.addEventListener('click', async ev => {
        const tr = ev.target.closest('tr[data-idx]');
        if (!tr) return;
        ev.stopPropagation();
        tbody.querySelectorAll('tr').forEach(r =>
            r.style.background = '');
        tr.style.background = '#fff7d6';
        const doc = saida[parseInt(tr.dataset.idx, 10)];
        if (doc) await onRowClick(doc);
    });

    tbl.addEventListener('mouseenter', ev => {
        const tr = ev.target.closest('tr[data-idx]');
        if (tr && tr.style.background !== 'rgb(255, 247, 214)')
            tr.style.background = '#f0f7ff';
    }, true);
    tbl.addEventListener('mouseleave', ev => {
        const tr = ev.target.closest('tr[data-idx]');
        if (tr && tr.style.background !== 'rgb(255, 247, 214)')
            tr.style.background = '';
    }, true);

    c.appendChild(tbl);
    document.body.appendChild(c);
}

async function onCheckRowClick(doc) {
    const elem = resolverElemento(doc);
    const link = resolverLink(doc);

    if (doc.isAnexo && (doc.tipo === 'Serasa' || doc.tipo === 'CNIB') && link) {
        // Fechar modais abertos
        document.querySelectorAll('button.ui-dialog-titlebar-close, .ui-dialog-titlebar-close')
            .forEach(b => { try { b.click(); } catch (e) { } });
        await sleep(500);

        // Re-resolver link (pode ter mudado após sleep)
        const freshLink = resolverLink(doc) || link;
        freshLink.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await sleep(1500);

        // Tentar abrir certificado
        const certSels = [
            'i.fa.fa-certificate.fa-lg', '.fa-certificate',
            'button[title*="certificado"]', 'button[title*="Certificado"]',
        ];
        for (const sel of certSels) {
            const certIcon = document.querySelector(sel);
            if (certIcon) {
                const btn = certIcon.closest('button') || certIcon;
                btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                break;
            }
        }
    } else if (elem) {
        elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        elem.classList.add('pjetools-destaque');
        setTimeout(() => elem?.classList.remove('pjetools-destaque'), 3000);
    }
}

window.executarCheck = async function () {
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const saida = construirOrdem(filtrados);
    renderTabela('listaDocsExecucaoSimples', '📋 Relatório de Medidas', '#007bff',
        saida, onCheckRowClick);

    // Botão baixar Serasa/CNIB dentro do painel
    const tbl = document.getElementById('listaDocsExecucaoSimples_tbl');
    if (tbl) {
        const bar = document.createElement('div');
        bar.style.cssText = 'padding:8px;border-top:1px solid #ddd;';
        const btn = document.createElement('button');
        btn.textContent = '⬇ Baixar Serasa/CNIB';
        btn.style.cssText = 'width:100%;padding:8px;background:#dc3545;color:#fff;' +
            'border:none;cursor:pointer;font-weight:bold;border-radius:4px;';
        btn.onclick = () => executarBaixarAutomatico(saida);
        bar.appendChild(btn);
        document.getElementById('listaDocsExecucaoSimples').appendChild(bar);
    }
}

window.executarBaixarAutomatico = async function (saida) {
    const serasaCnib = (saida || []).filter(d =>
        (d.tipo === 'Serasa' || d.tipo === 'CNIB') && d.isAnexo
    );
    if (!serasaCnib.length) { alert('Nenhum Serasa/CNIB para baixar'); return; }

    for (let i = 0; i < serasaCnib.length; i++) {
        const item = serasaCnib[i];
        try {
            document.querySelectorAll(
                'button.ui-dialog-titlebar-close, .ui-dialog-titlebar-close')
                .forEach(b => { try { b.click(); } catch (e) { } });
            await sleep(300);

            const link = resolverLink(item);
            if (link) {
                link.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                await sleep(1500);
            }
            const certSels = ['i.fa.fa-certificate.fa-lg', '.fa-certificate',
                'button[title*="certificado"]', 'button[title*="Certificado"]'];
            for (const sel of certSels) {
                const ic = document.querySelector(sel);
                if (ic) {
                    (ic.closest('button') || ic).dispatchEvent(
                        new MouseEvent('click', { bubbles: true }));
                    await sleep(800);
                    break;
                }
            }
            // Marcar linha como baixada
            const tbl = document.getElementById('listaDocsExecucaoSimples_tbl');
            if (tbl) {
                tbl.querySelector(`tr[data-doc-id="${item.id}"]`)?.style &&
                    (tbl.querySelector(`tr[data-doc-id="${item.id}"]`).style.background = '#ff4444');
            }
            await sleep(500);
        } catch (e) { console.error('[CHECK] Erro baixar:', e); }
    }
}

