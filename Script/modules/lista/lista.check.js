'use strict';
// lista.check.js v0.2.0

// ── Cache / API helpers (incorporados de lista.timeline.js) ─────
const CACHE_TTL = 5 * 60 * 1000;

function _pjeTlXsrf() {
    const c = document.cookie.split(';').map(s => s.trim())
        .find(s => s.toLowerCase().startsWith('xsrf-token='));
    return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
}
function _pjeTlHeaders() {
    const h = { 'Accept': 'application/json', 'Content-Type': 'application/json', 'X-Grau-Instancia': '1' };
    const x = _pjeTlXsrf(); if (x) h['X-XSRF-TOKEN'] = x;
    return h;
}
function _pjeTlIdProcesso() {
    const m = window.location.pathname.match(/\/processo\/(\d+)/);
    return m ? m[1] : null;
}
function _pjeTlNormData(s) {
    if (!s) return '';
    const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1].slice(2)}` : s;
}
function _pjeTlClassApi(item) {
    const low = ((item.titulo || '') + ' ' + (item.nomeDocumento || '') + ' ' + (item.descricao || '')).toLowerCase();
    if (low.includes('devolução de ordem')) return 'Certidão devolução pesquisa';
    if (low.includes('certidão de oficial') || low.includes('oficial de justiça')) return 'Certidão de oficial de justiça';
    if (low.includes('mandado de pagamento') && low.includes('alvará')) return 'Alvarás';
    if (low.includes('alvará') || low.includes('juntada de alvará')) return 'Alvarás';
    if (low.includes('sobrestamento')) return 'Decisão (Sobrestamento)';
    if (low.includes('serasa') || low.includes('apjur') || low.includes('carta ação') || low.includes('carta acao')) return 'SerasaAntigo';
    if (low.includes('edital')) return 'Edital';
    return null;
}

window.encontrarElementoPorUid = function (uid) {
    if (!uid) return null;
    const itens = document.querySelectorAll('li.tl-item-container');
    for (const item of itens) {
        // Busca no link de texto (documento principal): "Nome - UID"
        const textLink = item.querySelector('a.tl-documento:not([target="_blank"])');
        if (textLink) {
            const m = textLink.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
            if (m && m[1] === uid) return item;
        }
        // Busca no link de ícone (target="_blank"): href contém uid
        const iconLink = item.querySelector('a.tl-documento[target="_blank"]');
        if (iconLink) {
            const href = (iconLink.getAttribute('href') || '').toLowerCase();
            if (href.includes(uid.toLowerCase())) return item;
        }
    }
    return null;
}

// Dispatch seguro — fallback chain: MouseEvent → .click() → initMouseEvent
function safeDispatch(el, type, opts) {
    try { el.dispatchEvent(new MouseEvent(type, opts || {})); return true; }
    catch (e) {
        try { const safeOpts = Object.assign({}, opts || {}); if ('view' in safeOpts) delete safeOpts.view; el.dispatchEvent(new MouseEvent(type, safeOpts)); return true; }
        catch (e2) { try { el.click(); return true; } catch (e3) {} try { const ev = document.createEvent('MouseEvents'); ev.initMouseEvent(type, !!(opts && opts.bubbles), !!(opts && opts.cancelable), window, 0,0,0,0,0,false,false,false,false,0,null); el.dispatchEvent(ev); return true; } catch (e4) {} }
    }
    return false;
}

// Expande a seção de anexos de um container da timeline
async function expandirAnexos(container) {
    try {
        if (container.querySelector('.tl-item-anexo')) return true;
        const toggle = container.querySelector('button.botao-anexos');
        if (!toggle) return false;
        toggle.click();
        await sleep(400);
        return true;
    } catch (e) {
        return false;
    }
}

window.lerTimelineCompleta = async function () {
    const state = PJeState.lista;
    const agora = Date.now();
    if (state.docs && (agora - state.readAt) < CACHE_TTL) return state.docs;

    const idProcesso = _pjeTlIdProcesso();
    if (!idProcesso) return [];

    let itensApi = [];
    try {
        const params = new URLSearchParams({
            buscarMovimentos: 'false', buscarDocumentos: 'true', somenteDocumentosAssinados: 'false',
        });
        const url = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?' + params;
        const resp = await fetch(url, { method: 'GET', credentials: 'include', headers: _pjeTlHeaders() });
        if (resp.ok) itensApi = JSON.parse(await resp.text());
    } catch (e) {
        console.warn('[lerTimeline] API indisponível:', e.message);
    }

    if (!itensApi.length) return [];

    const documentos = [];

    for (const item of itensApi) {
        if (!item.idUnicoDocumento) continue;
        const tipo = _pjeTlClassApi(item);
        if (!tipo) continue;

        const uid = item.idUnicoDocumento;
        const idDoc = item.id ? String(item.id) : null;
        const data = _pjeTlNormData(item.data || item.atualizadoEm || '');
        const elem = encontrarElementoPorUid(uid);
        const iconLink = elem ? elem.querySelector('a.tl-documento[target="_blank"]') : null;
        // Captura href direto do ícone para bypass de UI — abre documento via API
        const iconHref = iconLink ? iconLink.getAttribute('href') : null;

        documentos.push({
            tipo, texto: item.titulo || '', id: uid, idDoc, tipoTexto: '',
            elementoId: elem ? (elem.id || null) : null,
            elementoSel: (elem && elem.id) ? `#${CSS.escape(elem.id)}` : null,
            linkId: iconLink ? (iconLink.id || null) : null,
            iconHref, data, isAnexo: false,
        });

        const anexosApi = Array.isArray(item.anexos) ? item.anexos : [];
        for (const anexo of anexosApi) {
            const t = ((anexo.titulo || '') + ' ' + (anexo.nomeDocumento || '')).toLowerCase();
            const tipoAnexo = /serasa|serasajud/.test(t) ? 'Serasa' : /cnib|indisp/.test(t) ? 'CNIB' : null;
            if (!tipoAnexo) continue;
            const uidAnexo = anexo.idUnicoDocumento || `anexo_${uid}_${tipoAnexo}`;
            const elemAnexo = encontrarElementoPorUid(uidAnexo);
            documentos.push({
                tipo: tipoAnexo, texto: anexo.titulo || '', id: uidAnexo,
                idDoc: anexo.id ? String(anexo.id) : null, tipoTexto: '',
                elementoId: elemAnexo ? (elemAnexo.id || null) : null,
                elementoSel: (elemAnexo && elemAnexo.id) ? `#${CSS.escape(elemAnexo.id)}` : null,
                linkId: null,
                data: _pjeTlNormData(anexo.data || anexo.atualizadoEm || '') || data,
                isAnexo: true, parentId: uid,
            });
        }
    }

    state.docs = documentos;
    state.readAt = agora;
    return documentos;
}

window.invalidarCacheTimeline = function () {
    PJeState.lista.docs = null;
    PJeState.lista.readAt = 0;
}

window.resolverElemento = function (doc) {
    if (doc.elementoSel) return document.querySelector(doc.elementoSel);
    if (doc.elementoId) return document.getElementById(doc.elementoId);
    return null;
}

window.resolverLink = function (doc) {
    if (doc.linkId) return document.getElementById(doc.linkId) ||
        document.querySelector(`a[id="${doc.linkId}"]`);
    return null;
}

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
    c.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:999999999;background:#fff;` +
        `border:2px solid ${corBorda};border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.18);` +
        `min-width:360px;max-height:60vh;overflow:auto;font-family:sans-serif;` +
        `pointer-events:auto;contain:layout style paint;will-change:transform;`;

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
        if (doc) {
            // Preservar painel durante click para evitar re-render Angular remover
            const panelRef = c; // manter referência ao container
            await onRowClick(doc);
            // Garantir que painel ainda existe após operação
            if (!document.body.contains(panelRef)) document.body.appendChild(panelRef);
        }
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
    // ── CAMINHO 1: Documento principal — rolar e destacar na timeline ──
    if (!doc.isAnexo) {
        const elem = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
        if (elem) {
            elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const origBorder = elem.style.border;
            const origBg = elem.style.background;
            elem.style.transition = 'all 0.3s ease';
            elem.style.border = '2px solid #fbbf24';
            elem.style.background = '#fffbeb';
            setTimeout(() => expandirAnexos(elem), 500);
            setTimeout(() => {
                elem.style.transition = 'all 0.5s ease';
                elem.style.border = origBorder;
                elem.style.background = origBg;
                setTimeout(() => { elem.style.transition = ''; }, 500);
            }, 3000);
        }
        invalidarCacheTimeline();
        return;
    }

    // ── CAMINHO 2: Anexo (Serasa / CNIB) ──────────────────────────
    if (doc.isAnexo && (doc.tipo === 'Serasa' || doc.tipo === 'CNIB') && doc.parentId) {
        const parentItem = encontrarElementoPorUid(doc.parentId);
        if (!parentItem) {
            console.warn('[CHECK] Parent certidao nao encontrado para anexo:', doc.id);
            return;
        }

        await expandirAnexos(parentItem);
        await sleep(500);

        // Localizar o link do anexo e capturar href direto
        const anexoLinks = parentItem.querySelectorAll('a.tl-documento[id^="anexo_"]');
        let alvo = null;
        if (doc.id) {
            const uidLower = doc.id.toLowerCase();
            alvo = Array.from(anexoLinks).find(l =>
                (l.getAttribute('href') || '').toLowerCase().includes(uidLower) ||
                (l.textContent || '').toLowerCase().includes(uidLower)
            );
        }
        alvo = alvo || anexoLinks[0];
        if (!alvo) {
            console.warn('[CHECK] Link do anexo nao encontrado:', doc.id);
            return;
        }

        // Abrir diretamente via href do link (bypass dispatchEvent)
        const anexoHref = alvo.getAttribute('href');
        if (anexoHref) {
            window.open(anexoHref, '_blank');
        } else {
            safeDispatch(alvo, 'click', { bubbles: true, cancelable: true });
        }

        // Destacar visualmente
        parentItem.style.transition = 'all 0.3s ease';
        parentItem.style.boxShadow = '0 0 0 3px #fbbf24';
        setTimeout(() => {
            parentItem.style.boxShadow = '';
            parentItem.style.transition = '';
        }, 3000);

        invalidarCacheTimeline();
        return;
    }

    // ── CAMINHO 3: Documento sem iconHref (fallback DOM) ──────────
    const elem = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
    if (!elem) {
        console.warn('[CHECK] Elemento nao encontrado para doc:', doc.id);
        return;
    }

    // Usar apenas highlight visual, SEM dispatchEvent para evitar quebra de cabeçalho
    // (o dispatchEvent causa re-render agressivo do Angular)
    elem.classList.add('pjetools-destaque');
    setTimeout(() => elem?.classList.remove('pjetools-destaque'), 3000);
    setTimeout(() => expandirAnexos(elem), 800);

    invalidarCacheTimeline();
}

window.executarCheck = async function () {
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const saida = construirOrdem(filtrados);
    renderTabela('listaDocsExecucaoSimples', '📋 Relatório de Medidas', '#007bff',
        saida, onCheckRowClick);
    // Adicionar botão "Conferir alvarás" no topo (header) da lista gerada pelo check
    const panel = document.getElementById('listaDocsExecucaoSimples');
    if (panel) {
        // evitar duplicatas
        const existing = panel.querySelector('#maisPje_btn_conferir_alvaras');
        if (existing) existing.remove();

        const hdr = panel.querySelector('div'); // header criado por renderTabela
        if (hdr) {
            const btn = document.createElement('button');
            btn.id = 'maisPje_btn_conferir_alvaras';
            btn.textContent = 'Conferir alvarás';
            btn.title = 'Conferir alvarás';
            btn.style.cssText = 'margin-left:8px;padding:6px 10px;background:#0078aa;color:#fff;border:none;cursor:pointer;' +
                'border-radius:4px;font-size:12px;pointer-events:auto;z-index:999999999;';
            btn.onclick = async (e) => {
                e.stopPropagation();
                e.preventDefault();
                try {
                    if (typeof window.executarPgto === 'function') {
                        // Delay para garantir que painel não é removido antes do executarPgto
                        setTimeout(() => window.executarPgto().catch(err => 
                            console.error('Erro ao executar conferir alvarás:', err)
                        ), 100);
                    } else {
                        console.warn('executarPgto não encontrado');
                    }
                } catch (e) { console.error('Erro ao executar conferir alvarás:', e); }
            };

            // Inserir antes do botão fechar (último botão no header)
            const closeBtn = hdr.querySelector('button');
            if (closeBtn) hdr.insertBefore(btn, closeBtn);
            else hdr.appendChild(btn);
        }
    }
}

window.executarBaixarAutomatico = async function (saida) {
    const serasaCnib = (saida || []).filter(d =>
        (d.tipo === 'Serasa' || d.tipo === 'CNIB') && d.isAnexo
    );
    if (!serasaCnib.length) { alert('Nenhum Serasa/CNIB para baixar'); return; }

    const idProcesso = _pjeTlIdProcesso();
    const origin = location.origin;

    for (let i = 0; i < serasaCnib.length; i++) {
        const item = serasaCnib[i];
        try {
            const parentItem = encontrarElementoPorUid(item.parentId);
            if (parentItem) {
                await expandirAnexos(parentItem);
                await sleep(400);

                const anexoLinks = parentItem.querySelectorAll('a.tl-documento[id^="anexo_"]');
                let alvo = null;
                if (item.id) {
                    const uidLower = item.id.toLowerCase();
                    alvo = Array.from(anexoLinks).find(l =>
                        (l.getAttribute('href') || '').toLowerCase().includes(uidLower) ||
                        (l.textContent || '').toLowerCase().includes(uidLower)
                    );
                }
                alvo = alvo || anexoLinks[0];
                if (alvo) {
                    // Abrir diretamente via href (bypass dispatchEvent / UI)
                    const anexoHref = alvo.getAttribute('href');
                    if (anexoHref) {
                        window.open(anexoHref, '_blank');
                    }
                }
                await sleep(600);
            }

            // Abrir certificado (via href do ícone se disponivel)
            const certSels = ['i.fa.fa-certificate.fa-lg', '.fa-certificate',
                'button[title*="certificado"]', 'button[title*="Certificado"]'];
            for (const sel of certSels) {
                const ic = document.querySelector(sel);
                if (ic) {
                    const btn = ic.closest('button') || ic;
                    safeDispatch(btn, 'click', { bubbles: true });
                    await sleep(600);
                    break;
                }
            }

            // Marcar linha como baixada
            const tbl = document.getElementById('listaDocsExecucaoSimples_tbl');
            if (tbl) {
                const row = tbl.querySelector(`tr[data-doc-id="${CSS.escape(item.id)}"]`);
                if (row) row.style.background = '#ff4444';
            }
            await sleep(400);
        } catch (e) { console.error('[CHECK] Erro baixar:', e); }
    }

    invalidarCacheTimeline();
}

