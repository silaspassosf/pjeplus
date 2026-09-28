'use strict';
// lista.check.js v0.3.9

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
    const titulo = _norm(item.titulo || '');
    const desc = _norm((item.nomeDocumento || '') + ' ' + (item.descricao || ''));
    const low = titulo + ' ' + desc;
    if (low.includes('devolucao de ordem') || low.includes('ordem de pesquisa patrimonial')) return 'Certidão devolução pesquisa';
    if (low.includes('certidao de oficial') || low.includes('oficial de justica')) return 'Certidão de oficial de justiça';
    // Mandado de pagamento NÃO é o alvará em si (é a certidão que o expede):
    // não entra na lista, mas fica marcado para a conferência (a descrição
    // traz nome + valor que são batidos em executarPgto).
    if (titulo.includes('mandado de pagamento')) return 'MandadoPagamento';
    if (low.includes('alvara')) {
        // "Expedição"/"expedido" na descrição nunca é alvará a liberar
        if (/(expedicao|expedido)/.test(low)) return null;
        // Anti-falso-positivo pontual: "Manifestação (pedido de alvará)"
        if (titulo.startsWith('manifestacao')) return null;
        // Filtro de exclusão: tipo "Planilha" nunca é alvará a liberar.
        // Checa o `low` completo (título + nomeDocumento + descrição), pois
        // o título da API pode vir vazio e "Planilha de Cálculos" chega só
        // na descrição (ex: "Planilha de Cálculos, dedução alvará2").
        if (low.includes('planilha')) return null;
        // Qualquer outra menção a "alvará" no tipo+nome+descrição entra
        // (comportamento da v0.2.0, que detectava corretamente — a v0.3.3
        // exigia alvará na descrição E título exato e perdia alvarás reais).
        return 'Alvarás';
    }
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

        // Ícone da timeline: alvará só vale para documento interno (gavel).
        // Juntada por polo ativo/passivo/terceiro (fa-user POLO_*) não entra;
        // o label do ícone não importa.
        if (tipo === 'Alvarás' && elem) {
            const icone = elem.querySelector('.tl-icon i');
            if (!icone || !icone.classList.contains('fa-gavel')) continue;
        }

        const anexosApi = Array.isArray(item.anexos) ? item.anexos : [];

        // Certidão (Alvará) com anexo "Documento Diverso (Alvará)":
        // conta apenas o anexo — o documento principal não é listado.
        const ehCertidaoAlvara = tipo === 'Alvarás' && _norm(item.titulo || '').startsWith('certidao');
        const anexosAlvara = ehCertidaoAlvara
            ? anexosApi.filter(ax => _norm((ax.titulo || '') + ' ' + (ax.nomeDocumento || '')).includes('alvara'))
            : [];

        // Se é certidão de alvará COM anexo alvará, só o anexo entra na lista.
        // A certidão é apenas um container/índice, não o documento real.
        if (ehCertidaoAlvara && anexosAlvara.length) {
            // Skip a certidão — só os anexos são processados abaixo.
        } else {
            documentos.push({
                tipo, texto: item.titulo || '', id: uid, idDoc, tipoTexto: '',
                desc: (item.nomeDocumento || '') + ' ' + (item.descricao || ''),
                elementoId: elem ? (elem.id || null) : null,
                elementoSel: (elem && elem.id) ? `#${CSS.escape(elem.id)}` : null,
                linkId: iconLink ? (iconLink.id || null) : null,
                iconHref, data, isAnexo: false,
            });
        }

        for (const anexo of anexosApi) {
            const t = _norm((anexo.titulo || '') + ' ' + (anexo.nomeDocumento || ''));
            let tipoAnexo = null;
            if (anexosAlvara.includes(anexo)) tipoAnexo = 'Alvarás';
            else if (/serasa|serasajud/.test(t)) tipoAnexo = 'Serasa';
            else if (/cnib|indisp/.test(t)) tipoAnexo = 'CNIB';
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
        if (tipo === 'mandadopagamento') return false; // usado só pela conferência (executarPgto)
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

// ── Agrupamento de alvarás por beneficiário e valor ──
// Agrupa alvarás não registrados por beneficiário, somando valores
// e selecionando a data mais recente não registrada
window.agruparAlvarasPorBeneficiario = function (docs) {
    const alvaras = docs.filter(d => d.tipo === 'Alvarás' && !d.isAnexo);
    
    if (!alvaras.length) return [];
    
    // Agrupa por beneficiário (nome do autor/advogado/perito)
    const grupos = {};
    
    alvaras.forEach(alv => {
        // Tenta extrair beneficiário do texto/descrição
        const texto = (alv.texto || '') + ' ' + (alv.desc || '');
        const nomeBeneficiario = extrairNomeBeneficiario(texto);
        
        if (!nomeBeneficiario) return;
        
        if (!grupos[nomeBeneficiario]) {
            grupos[nomeBeneficiario] = {
                nome: nomeBeneficiario,
                valorTotal: 0,
                documentos: [],
                dataMaisRecente: null,
                flags: {}
            };
        }
        
        const grupo = grupos[nomeBeneficiario];
        
        // Extrai valor do alvará
        const valor = extrairValorDoAlvara(texto);
        grupo.valorTotal += valor;
        
        // Adiciona documento ao grupo
        grupo.documentos.push({
            ...alv,
            valorExtrato: valor
        });
        
        // Atualiza data mais recente
        if (!grupo.dataMaisRecente || alv.data > grupo.dataMaisRecente) {
            grupo.dataMaisRecente = alv.data;
        }
    });
    
    // Converte para array e ordena por valor total (maior primeiro)
    return Object.values(grupos).sort((a, b) => b.valorTotal - a.valorTotal);
};

// Extrai nome do beneficiário do texto do alvará
function extrairNomeBeneficiario(texto) {
    if (!texto) return null;
    
    const low = texto.toLowerCase();
    
    // Busca padrão SISCONDJ: "Beneficiário: NOME"
    const matchBeneficiario = texto.match(/beneficiario[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
    if (matchBeneficiario) return matchBeneficiario[1].trim();
    
    // Se não achou "Beneficiário", tenta autor
    const matchAutor = texto.match(/autor[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
    if (matchAutor) return matchAutor[1].trim();
    
    // Tenta procurador/advogado
    const matchProcurador = texto.match(/procurador[.:]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
    if (matchProcurador) return matchProcurador[1].trim();
    
    return null;
}

// Extrai valor monetário do texto do alvará
function extrairValorDoAlvara(texto) {
    if (!texto) return 0;
    
    // Busca padrão: "Valor Total: R$ X.XXX,XX" ou similar
    // Ou "Valor Principal: R$ X.XXX,XX"
    let valor = 0;
    
    // Tenta encontrar "Valor" seguido de número
    const matchValor = texto.match(/valor\s+(?:principal|total|de\s+pagamento)?[.:]?\s*(\d{1,3}\.\d{3}(?:,\d{3})*\.\d{2})/i);
    if (matchValor) {
        valor = parseMoney(matchValor[1]);
        if (valor > 0) return valor;
    }
    
    // Tenta encontrar "Calculado em" com valor anterior
    const matchCalculado = texto.match(/calculado\s+em[.:]?\s*(\d{1,3}\.\d{3}(?:,\d{3})*\.\d{2})/i);
    if (matchCalculado) {
        valor = parseMoney(matchCalculado[1]);
        if (valor > 0) return valor;
    }
    
    return 0;
}

// Parseia valor monetário (formato R$ X.XXX,XX ou X.XXX,XX)
function parseMoney(str) {
    if (!str) return 0;
    
    let text = String(str)
        .replace(/R\$\s*/gi, '')
        .replace(/\./g, '')
        .replace(',', '.')
        .trim();
    
    const number = parseFloat(text);
    return Number.isFinite(number) ? number : 0;
}

// Detecta flags baseados no conteúdo do alvará
function detectarFlags(texto, flags) {
    if (!texto) return;
    
    const low = texto.toLowerCase();
    
    // Autor → flag crédito
    if (/^autor/.test(texto)) {
        flags.credito = true;
    }
    
    // Advogado/Procurador → flag honorários advocatícios
    if (/^procurador/.test(texto) || /advogado/.test(low)) {
        flags.honorariosAdvocaticios = true;
    }
    
    // Perito → flag honorários periciais
    if (/^perito/.test(texto)) {
        flags.honorariosPericiais = true;
    }
    
    // CONTRIB.PREVIDENC. → flag INSS
    if (/contrib\.previdenc\./.test(low)) {
        flags.inss = true;
    }
    
    // Recolher GRU → flag custas
    if (/recolher gru/.test(low)) {
        flags.custas = true;
    }
}

// Mostra resumo dos alvarás agrupados
window.mostrarResumoAlvaras = function (grupos) {
    if (!grupos || !grupos.length) {
        showToast('Nenhum alvará encontrado', '#6c757d', 3000);
        return;
    }
    
    // Cria painel de resumo
    const panelId = 'pjeResumoAlvaras';
    document.getElementById(panelId)?.remove();
    
    const c = document.createElement('div');
    c.id = panelId;
    c.style.cssText = `position:fixed;top:50%;left:50%;transform:translate(-50%, -50%);z-index:999999999;background:#fff;border:2px solid #0078aa;border-radius:8px;padding:20px;min-width:400px;max-width:600px;box-shadow:0 8px 32px rgba(0,0,0,.3);font-family:sans-serif;`;
    
    // Header
    const hdr = document.createElement('div');
    hdr.style.cssText = `display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;`;
    hdr.innerHTML = `<h3 style="margin:0;color:#0078aa;font-size:16px">📋 Resumo de Alvarás (${grupos.length})</h3>` +
        `<button style="background:none;border:none;font-size:20px;cursor:pointer;color:#666">✕</button>`;
    const closeBtn = hdr.querySelector('button');
    closeBtn.onclick = () => c.remove();
    c.appendChild(hdr);
    
    // Lista de grupos
    const lista = document.createElement('div');
    lista.style.cssText = `max-height:300px;overflow:auto;margin-bottom:15px;`;
    
    grupos.forEach(grupo => {
        const div = document.createElement('div');
        div.style.cssText = `border:1px solid #eee;padding:10px;margin-bottom:10px;border-radius:4px;`;
        
        // Nome do beneficiário
        const nomeDiv = document.createElement('div');
        nomeDiv.style.cssText = `font-weight:bold;font-size:14px;margin-bottom:5px;`;
        nomeDiv.textContent = grupo.nome;
        div.appendChild(nomeDiv);
        
        // Flags
        const flagsDiv = document.createElement('div');
        flagsDiv.style.cssText = `font-size:12px;color:#666;margin-bottom:5px;`;
        const flagLabels = [];
        if (grupo.flags.credito) flagLabels.push('Crédito');
        if (grupo.flags.honorariosAdvocaticios) flagLabels.push('Honorários Advocatícios');
        if (grupo.flags.honorariosPericiais) flagLabels.push('Honorários Periciais');
        if (grupo.flags.inss) flagLabels.push('INSS');
        if (grupo.flags.custas) flagLabels.push('Custas');
        flagsDiv.textContent = flagLabels.length ? `Flags: ${flagLabels.join(', ')}` : '';
        div.appendChild(flagsDiv);
        
        // Valor total
        const valorDiv = document.createElement('div');
        valorDiv.style.cssText = `font-size:16px;font-weight:bold;color:#0078aa;margin-bottom:5px;`;
        valorDiv.textContent = `Total: R$ ${grupo.valorTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        div.appendChild(valorDiv);
        
        // Data mais recente
        const dataDiv = document.createElement('div');
        dataDiv.style.cssText = `font-size:12px;color:#666;`;
        dataDiv.textContent = `Data mais recente: ${grupo.dataMaisRecente || 'Desconhecida'}`;
        div.appendChild(dataDiv);
        
        lista.appendChild(div);
    });
    
    c.appendChild(lista);
    
    // Botões de ação
    const actions = document.createElement('div');
    actions.style.cssText = `display:flex;gap:10px;justify-content:flex-end;`;
    
    const btnConfirmar = document.createElement('button');
    btnConfirmar.textContent = '✅ Confirmar e Conferir';
    btnConfirmar.style.cssText = `padding:8px 16px;background:#0078aa;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;`;
    btnConfirmar.onclick = () => {
        c.remove();
        // Chama executarPgto para conferência
        if (typeof window.executarPgto === 'function') {
            setTimeout(() => window.executarPgto().catch(err =>
                console.error('Erro ao executar conferir alvarás:', err)
            ), 100);
        }
    };
    
    const btnCancelar = document.createElement('button');
    btnCancelar.textContent = '❌ Cancelar';
    btnCancelar.style.cssText = `padding:8px 16px;background:#dc3545;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;`;
    btnCancelar.onclick = () => c.remove();
    
    actions.appendChild(btnConfirmar);
    actions.appendChild(btnCancelar);
    c.appendChild(actions);
    
    document.body.appendChild(c);
};

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
window.autoSelecionarPesquisaCheck = async function () {
    // 1) Clicar no ícone de check-square nativo do PJe
    const icone = document.querySelector('i.icone-sozinho.fa-check-square, i.far.fa-check-square, .fa-check-square');
    if (!icone) {
        showToast('Ícone de check-square não encontrado', '#dc3545', 3000);
        return;
    }
    (icone.closest('button') || icone).click();
    await sleep(600);

    // 2) Usar a timeline já lida para saber exatamente quais pesquisas têm CNIB+Serasa
    const docs = await lerTimelineCompleta();
    const pares = [];
    const pais = docs.filter(d => !d.isAnexo && /pesquisa/i.test(d.tipo || d.texto || ''));
    for (const pai of pais) {
        const anexos = docs.filter(d => d.isAnexo && d.parentId === pai.id);
        const temCnib = anexos.some(a => a.tipo === 'CNIB');
        const temSerasa = anexos.some(a => a.tipo === 'Serasa');
        if (temCnib && temSerasa) {
            pares.push({ pai, anexos: anexos.filter(a => a.tipo === 'CNIB' || a.tipo === 'Serasa') });
        }
    }
    if (!pares.length) {
        showToast('Nenhuma pesquisa com par CNIB + Serasa encontrada', '#6c757d', 3000);
        return;
    }

    let marcados = 0;
    for (const { pai, anexos } of pares) {
        const paiEl = encontrarElementoPorUid(pai.id);
        if (!paiEl) {
            console.warn('[autoSelecionarPesquisaCheck] Pai não encontrado no DOM:', pai.id);
            continue;
        }
        await expandirAnexos(paiEl);
        await sleep(400);

        const anexoLinks = Array.from(paiEl.querySelectorAll('a.tl-documento[id^="anexo_"]'));
        for (const anexo of anexos) {
            const uidLower = String(anexo.id || '').toLowerCase();
            const link = anexoLinks.find(l =>
                (l.getAttribute('href') || '').toLowerCase().includes(uidLower) ||
                (l.textContent || '').toLowerCase().includes(uidLower)
            ) || anexoLinks.find(l => {
                const t = (l.textContent || '').toLowerCase();
                return anexo.tipo === 'CNIB' ? /cnib|indisp/.test(t) : /serasa/.test(t);
            });
            if (!link) {
                console.warn('[autoSelecionarPesquisaCheck] Link do anexo não encontrado:', anexo.id);
                continue;
            }
            const row = link.closest('li, tr, div, .tl-item-anexo') || link.parentElement;
            const cb = row.querySelector('input[type="checkbox"]');
            if (cb && !cb.checked) {
                cb.scrollIntoView({ block: 'nearest' });
                cb.click();
                marcados++;
            } else if (!cb) {
                console.warn('[autoSelecionarPesquisaCheck] Checkbox não encontrado para:', anexo.id);
            }
        }
    }

    showToast(`AutoCheck: ${marcados} documento(s) marcado(s)`, marcados ? '#28a745' : '#dc3545', 3000);
};

window.executarCheck = async function () {
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const saida = construirOrdem(filtrados);
    renderTabela('listaDocsExecucaoSimples', '📋 Relatório de Medidas', '#007bff',
        saida, onCheckRowClick);

    // Execução automática após gerar a tabela
    setTimeout(() => {
        window.autoSelecionarPesquisaCheck().catch(e => console.error('[CHECK] Erro autocheck', e));
    }, 500);

    // Adicionar botões no topo (header) da lista gerada pelo check
    const panel = document.getElementById('listaDocsExecucaoSimples');
    if (panel) {
        const hdr = panel.querySelector('div'); // header criado por renderTabela
        if (hdr) {
            const closeBtn = hdr.querySelector('button');

            // Botão Auto-check CNIB/Serasa
            const existingAuto = panel.querySelector('#maisPje_btn_autocheck');
            if (existingAuto) existingAuto.remove();
            const btnAuto = document.createElement('button');
            btnAuto.id = 'maisPje_btn_autocheck';
            btnAuto.textContent = '☑️ CNIB+Serasa';
            btnAuto.title = 'Selecionar automaticamente CNIB + Serasa de pesquisas';
            btnAuto.style.cssText = 'margin-left:8px;padding:6px 10px;background:#17a2b8;color:#fff;border:none;cursor:pointer;' +
                'border-radius:4px;font-size:12px;pointer-events:auto;z-index:999999999;';
            btnAuto.onclick = async (e) => {
                e.stopPropagation();
                e.preventDefault();
                try { await window.autoSelecionarPesquisaCheck(); }
                catch (err) { console.error('[CHECK] Erro no auto-check:', err); }
            };
            if (closeBtn) hdr.insertBefore(btnAuto, closeBtn);
            else hdr.appendChild(btnAuto);

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
                    // 1) Agrupa alvarás por beneficiário e valor
                    const docs = await lerTimelineCompleta();
                    const filtrados = filtrarDocs(docs);
                    const grupos = window.agruparAlvarasPorBeneficiario(filtrados);
                    
                    // 2) Mostra resumo antes de confirmar
                    if (grupos.length > 0) {
                        window.mostrarResumoAlvaras(grupos);
                    } else {
                        showToast('Nenhum alvará não registrado encontrado', '#6c757d', 3000);
                    }
                } catch (err) {
                    console.error('Erro ao preparar conferência de alvarás:', err);
                }
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

