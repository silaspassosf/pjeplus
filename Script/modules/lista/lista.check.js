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
function _norm(t) {
    return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}
window.norm = _norm;
function _pjeTlClassApi(item) {
    const raw = (item.titulo || '') + ' ' + (item.nomeDocumento || '') + ' ' + (item.descricao || '');
    const low = _norm(raw);
    if (low.includes('devolucao de ordem') || low.includes('ordem de pesquisa patrimonial')) return 'Certidão devolução pesquisa';
    if (low.includes('certidao de oficial') || low.includes('oficial de justica')) return 'Certidão de oficial de justiça';
    if (low.includes('mandado de pagamento') && low.includes('alvara')) return 'Alvarás';
    if (low.includes('alvara') || low.includes('juntada de alvara')) return 'Alvarás';
    if (low.includes('sobrestamento')) return 'Decisao (Sobrestamento)';
    if (low.includes('serasa') || low.includes('apjur') || low.includes('carta acao')) return 'SerasaAntigo';
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
window.isCertDevolucao = d => _norm(d.tipo).includes('certidao devolucao');
window.isCertOficial = d => _norm(d.tipo).includes('certidao de oficial');
window.isAlvara = d => _norm(d.tipo) === 'alvaras';
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
    c.setAttribute('data-pjetools-panel', 'true');  // Marcador para MutationObserver
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
    const closeBtn = hdr.querySelector('button');
    closeBtn.onclick = (e) => { e.stopPropagation(); c.remove(); };
    c.appendChild(hdr);

    if (!saida.length) {
        const nd = document.createElement('div');
        nd.textContent = 'Nenhum item encontrado';
        nd.style.cssText = 'padding:20px;text-align:center;color:#666;font-style:italic;';
        c.appendChild(nd);
        (document.documentElement || document.body).appendChild(c);
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

    // ── Restaurar highlights persistentes de visitas anteriores ──
    saida.forEach((d, idx) => {
        if (window._checkVisited && window._checkVisited.has(d.id)) {
            const row = tbody.querySelector(`tr[data-idx="${idx}"]`);
            if (row) row.style.background = '#fff7d6';
        }
    });

    // DblClick tracker (300ms threshold)
    let clickTimer = null;

    // Event delegation – 1 listener para toda a tabela
    tbl.addEventListener('click', async ev => {
        const tr = ev.target.closest('tr[data-idx]');
        if (!tr) return;
        ev.stopPropagation();
        ev.preventDefault();

        const doc = saida[parseInt(tr.dataset.idx, 10)];
        if (!doc) return;

        // Detectar double-click (300ms)
        if (clickTimer) {
            clearTimeout(clickTimer);
            clickTimer = null;

            // ── DOUBLE CLICK: Abrir documento (clica no textLink Angular) ──
            if (!doc.isAnexo) {
                const elem = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
                if (elem) {
                    const textLink = elem.querySelector('a.tl-documento:not([target="_blank"])');
                    if (textLink) textLink.click();
                }
            } else if (doc.isAnexo && doc.parentId) {
                // Para anexos, abrir novamente em nova aba
                const parentItem = encontrarElementoPorUid(doc.parentId);
                if (parentItem) {
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
                    if (alvo) {
                        const anexoHref = alvo.getAttribute('href');
                        if (anexoHref) window.open(anexoHref, '_blank');
                    }
                }
            }
            return;
        }

        // ── SINGLE CLICK: Selecionar + destacar (persistente, sem navegação) ──
        clickTimer = setTimeout(async () => {
            clickTimer = null;

            // Destacar linha atual
            tbody.querySelectorAll('tr').forEach(r => {
                const d = saida[parseInt(r.dataset.idx, 10)];
                if (d && window._checkVisited && window._checkVisited.has(d.id)) {
                    r.style.background = '#fff7d6';
                } else {
                    r.style.background = '';
                }
            });
            tr.style.background = '#fff7d6';

            // Executar ação (scroll + highlight, SEM navegação)
            try {
                await onRowClick(doc);
            } catch (err) {
                console.error('[CHECK] Erro ao executar ação:', err);
            }
        }, 300);
    });

    tbl.addEventListener('mouseenter', ev => {
        const tr = ev.target.closest('tr[data-idx]');
        if (!tr) return;
        const doc = saida[parseInt(tr.dataset.idx, 10)];
        const isVisited = doc && window._checkVisited && window._checkVisited.has(doc.id);
        if (tr.style.background !== 'rgb(255, 247, 214)' && !isVisited)
            tr.style.background = '#f0f7ff';
    }, true);
    tbl.addEventListener('mouseleave', ev => {
        const tr = ev.target.closest('tr[data-idx]');
        if (!tr) return;
        const doc = saida[parseInt(tr.dataset.idx, 10)];
        const isVisited = doc && window._checkVisited && window._checkVisited.has(doc.id);
        if (tr.style.background !== 'rgb(255, 247, 214)') {
            tr.style.background = isVisited ? '#fff7d6' : '';
        }
    }, true);

    c.appendChild(tbl);
    
    // SEMPRE garantir que seja adicionado ao document.body
    document.body.appendChild(c);

    // Impedir que cliques/mousedown no painel disparem handlers do Angular
    c.addEventListener('mousedown', e => e.stopPropagation());
    c.addEventListener('click', e => e.stopPropagation());

    // ── Persistência reforçada: MutationObserver + polling ──
    c.dataset.userClosed = 'false';
    let watchdogTimer = null;

    const observer = new MutationObserver(() => {
        if (c.dataset.userClosed === 'true') return;
        if (!document.body.contains(c)) {
            console.warn('[CHECK] Painel removido pelo Angular, restaurando...');
            requestAnimationFrame(() => {
                if (!document.body.contains(c) && c.dataset.userClosed !== 'true') {
                    document.body.appendChild(c);
                }
            });
        }
    });

    // Observer com subtree:true e também observar documentElement como fallback
    observer.observe(document.body, { childList: true, subtree: true });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    // Polling de fallback a cada 600ms (caso o MutationObserver perca o evento)
    watchdogTimer = setInterval(() => {
        if (c.dataset.userClosed === 'true') {
            clearInterval(watchdogTimer);
            observer.disconnect();
            return;
        }
        if (!document.body.contains(c)) {
            console.warn('[CHECK] Watchdog: painel ausente, restaurando...');
            document.body.appendChild(c);
        }
    }, 600);

    // Armazenar observer/watchdog para poder cancelar após fechar
    const originalRemove = c.remove;
    c.remove = function () {
        c.dataset.userClosed = 'true';
        if (watchdogTimer) clearInterval(watchdogTimer);
        observer.disconnect();
        originalRemove.call(this);
    };
}

// ── Estado persistente de seleção ──
window._checkVisited = new Set();

async function onCheckRowClick(doc) {
    // ── CAMINHO 1: Documento principal — scroll + highlight persistente ──
    if (!doc.isAnexo) {
        const elem = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
        if (elem) {
            // NUNCA clicar no textLink (dispara navegação Angular → remove painel)
            // Apenas scroll suave + highlight persistente
            elem.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Destacar persistentemente (não some após timeout)
            elem.style.transition = 'all 0.3s ease';
            elem.style.border = '2px solid #fbbf24';
            elem.style.background = '#fffbeb';
            elem.dataset.pjeChecked = 'true';
            window._checkVisited.add(doc.id);

            // Expandir anexos após scroll
            setTimeout(() => expandirAnexos(elem), 600);

            // Destaque diminui mas permanece visível (não some totalmente)
            setTimeout(() => {
                elem.style.transition = 'all 0.8s ease';
                elem.style.border = '1px solid #fcd34d';
                elem.style.background = '#fffbeb';
                setTimeout(() => { elem.style.transition = ''; }, 800);
            }, 4000);
        }
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

        // Scroll até o anexo + highlight persistente
        alvo.scrollIntoView({ behavior: 'smooth', block: 'center' });
        parentItem.style.transition = 'all 0.3s ease';
        parentItem.style.boxShadow = '0 0 0 3px #fbbf24';
        parentItem.dataset.pjeChecked = 'true';
        window._checkVisited.add(doc.id);

        setTimeout(() => {
            parentItem.style.boxShadow = '0 0 0 1px #fcd34d';
            parentItem.style.transition = '';
        }, 4000);

        // Abrir anexo em nova aba (não afeta o painel)
        const anexoHref = alvo.getAttribute('href');
        if (anexoHref) {
            window.open(anexoHref, '_blank');
        }

        return;
    }

    // ── CAMINHO 3: Documento sem iconHref (fallback DOM) ──────────
    const elem = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
    if (!elem) {
        console.warn('[CHECK] Elemento nao encontrado para doc:', doc.id);
        return;
    }

    elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    elem.classList.add('pjetools-destaque');
    elem.dataset.pjeChecked = 'true';
    window._checkVisited.add(doc.id);

    setTimeout(() => expandirAnexos(elem), 800);
}

// Abre o painel nativo de seleção de documentos e marca CNIB + Serasa de pesquisas
window.autoSelecionarPesquisaCheck = async function (docs) {
    if (!docs || !docs.length) return;

    // 1) Identificar pares pelas APIs (não DOM)
    const pares = [];
    const pais = docs.filter(d => !d.isAnexo && /pesquisa|certid[aã]o|oficial de justi[cç]a/i.test(d.tipo || d.texto || ''));
    for (const pai of pais) {
        const anexos = docs.filter(d => d.isAnexo && d.parentId === pai.id);
        const temCnib = anexos.some(a => a.tipo === 'CNIB');
        const temSerasa = anexos.some(a => a.tipo === 'Serasa');
        if (temCnib && temSerasa) {
            pares.push({ pai, anexos: anexos.filter(a => a.tipo === 'CNIB' || a.tipo === 'Serasa') });
        }
    }
    
    if (!pares.length) return; // Se não tem par, não entra na seleção nativa

    // 2) Entrar no modo de seleção múltipla da SPA
    const icone = document.querySelector('i.icone-sozinho.fa-check-square, i.far.fa-check-square, .fa-check-square');
    if (!icone) return;
    const btnCheck = icone.closest('button') || icone;
    btnCheck.click();
    console.log('[AutoCheck] Entrou no modo seleção múltipla. Aguardando SPA...');
    
    // Aguardar checkboxes aparecerem (indicador de que o Angular recriou a lista)
    await sleep(2000); 

    // Helper text-match para encontrar itens na nova view
    const nTexto = t => window.norm(t);

    // 3) Expandir e marcar trabalhando no DOM re-renderizado
    let marcados = 0;
    for (const { pai, anexos } of pares) {
        // Encontrar container do Pai pelo uid ou titulo
        const elemUID = encontrarElementoPorUid(pai.id);
        const alvoBusca = pai.texto || '';
        
        let containerPai = elemUID;
        if (!containerPai) {
            // Tentar localizar pelo titulo
            const listItems = Array.from(document.querySelectorAll('li.tl-item-container, .documento-item'));
            containerPai = listItems.find(el => nTexto(el.textContent).includes(nTexto(alvoBusca).substring(0,25)));
        }

        if (!containerPai) {
            console.warn('[AutoCheck] Não achei a pesquisa no DOM pós-render:', pai.id);
            continue;
        }

        // Expandir anexos clicando no botão toggle no novo DOM
        const toggle = containerPai.querySelector('button.botao-anexos, mat-icon[svgicon*="expand"]');
        if (toggle && !containerPai.querySelector('.tl-item-anexo')) {
            toggle.click();
            await sleep(800);
        }

        // Selecionar os Checkboxes dos anexos
        const labelsAnexos = Array.from(containerPai.querySelectorAll('.tl-item-anexo, .anexo, a.tl-documento[id^="anexo_"]'));
        
        for (const anexo of anexos) {
            const ehCnib = anexo.tipo === 'CNIB';
            const matcher = ehCnib ? /cnib|indisp/ : /serasa/;
            
            // Encontrar elemento do anexo
            const anexoEl = labelsAnexos.find(el => {
                const t = nTexto(el.textContent);
                return matcher.test(t);
            });
            
            if (anexoEl) {
                const row = anexoEl.closest('li, tr, div') || anexoEl.parentElement;
                // No modo seleção do PJe, os inputs as vezes re-utilizam tag, garantir o da row corrente
                const cb = row.querySelector('input[type="checkbox"]');
                if (cb && !cb.checked) {
                    cb.scrollIntoView({ behavior: "smooth", block: "center" });
                    cb.click();
                    marcados++;
                }
            }
        }
    }
    
    if (marcados > 0) {
        showToast(`AutoCheck: ${marcados} documento(s) marcado(s)`, '#28a745', 3000);
    }
};

window.executarCheck = async function () {
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const saida = construirOrdem(filtrados);
    renderTabela('listaDocsExecucaoSimples', '📋 Relatório de Medidas', '#007bff',
        saida, onCheckRowClick);
    
    // Execução automática do Auto-check sem botão
    setTimeout(() => {
        window.autoSelecionarPesquisaCheck(docs).catch(e => console.error('[CHECK] Erro autocheck', e));
    }, 500);

    // Adicionar botões no topo (header) da lista gerada pelo check
    const panel = document.getElementById('listaDocsExecucaoSimples');
    if (panel) {
        const hdr = panel.querySelector('div'); // header criado por renderTabela
        if (hdr) {
            const closeBtn = hdr.querySelector('button');

            // Botão Conferir alvarás
            const existing = panel.querySelector('#maisPje_btn_conferir_alvaras');
            if (existing) existing.remove();
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

