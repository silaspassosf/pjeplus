// ==UserScript==
// @name         PJeTools — Orquestrador
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Infojud + Lista Geral + Atalhos integrados com boas práticas
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt2.jus.br/pjekz/processo/*/comunicacoesprocessuais/minutas*
// @match        https://pje.trt2.jus.br/pjekz/pagamento/*/cadastro*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @run-at       document-idle
// ==/UserScript==

(function () {
'use strict';

// ────────────────────────────────────────────────────────────
// core/state.js
// ────────────────────────────────────────────────────────────
// ── CleanupRegistry ──────────────────────────────────────────────
// Rastreia TODOS os recursos criados (event listeners, intervals,
// timeouts, observers, channels) e os libera em dispose().
class CleanupRegistry {
    #items = [];

    add(fn) {
        this.#items.push(fn);
        // Retorna função de cancelamento individual
        return () => {
            const i = this.#items.indexOf(fn);
            if (i !== -1) this.#items.splice(i, 1);
        };
    }

    // Listeners com remoção automática
    on(target, type, fn, opts) {
        target.addEventListener(type, fn, opts);
        return this.add(() => target.removeEventListener(type, fn, opts));
    }

    // setInterval com limpeza
    interval(fn, ms) {
        const id = setInterval(fn, ms);
        return this.add(() => clearInterval(id));
    }

    // setTimeout com limpeza (se ainda não disparou)
    timeout(fn, ms) {
        const id = setTimeout(fn, ms);
        return this.add(() => clearTimeout(id));
    }

    // MutationObserver
    observer(obs) {
        return this.add(() => obs.disconnect());
    }

    // BroadcastChannel
    channel(ch) {
        return this.add(() => { try { ch.close(); } catch(e) {} });
    }

    dispose() {
        // Inverte a ordem para desfazer na ordem oposta à criação
        [...this.#items].reverse().forEach(fn => { try { fn(); } catch(e) {} });
        this.#items = [];
    }
}

// ── AsyncRunner ───────────────────────────────────────────────────
// Garante que apenas uma operação assíncrona rode por vez.
// Cancela a anterior ao iniciar nova (via AbortSignal).
class AsyncRunner {
    #ctrl = null;

    get running() { return !!this.#ctrl; }

    async run(fn) {
        this.abort();
        this.#ctrl = new AbortController();
        const signal = this.#ctrl.signal;
        try {
            await fn(signal);
        } catch (e) {
            if (e?.name !== 'AbortError') throw e;
        } finally {
            this.#ctrl = null;
        }
    }

    abort() {
        this.#ctrl?.abort(new DOMException('Cancelled', 'AbortError'));
        this.#ctrl = null;
    }
}

// ── Estado global ─────────────────────────────────────────────────
// Singleton reutilizado entre navegações SPA.
// dispose() é chamado pelo orchestrator a cada pushState.

if (!window._pjeTools) {
    window._pjeTools = {
        // Módulo lista
        lista: {
            docs: null,          // cache da timeline
            readAt: 0,           // timestamp da última leitura
            runner: new AsyncRunner(),
        },
        // Módulo atalhos
        atalhos: {
            channel: null,
            registry: new CleanupRegistry(),
        },
        // Módulo infojud
        infojud: {
            fila: [],
            atual: 0,
            modo: '',
            dados: [],
            runner: new AsyncRunner(),
        },
        // Registro global (listeners do painel, etc.)
        registry: new CleanupRegistry(),
        _iniciado: false,

        dispose() {
            this.lista.docs = null;
            this.lista.readAt = 0;
            this.lista.runner.abort();

            this.infojud.runner.abort();
            this.infojud.fila = [];
            this.infojud.atual = 0;
            this.infojud.dados = [];

            this.atalhos.registry.dispose();

            this.registry.dispose();
            this._iniciado = false;

            // Remove painéis injetados
            ['pjetools-painel', 'listaDocsExecucaoSimples',
             'listaDocsEditalSimples', 'god-relatorio-panel',
             'pjetools-toast'].forEach(id => document.getElementById(id)?.remove());

            // Remove atributo de boot (permite reinjeção após navigate)
            document.documentElement.removeAttribute('data-pjetools-boot');
        },
    };
}

const PJeState = window._pjeTools;

// ────────────────────────────────────────────────────────────
// core/utils.js
// ────────────────────────────────────────────────────────────
// ── Primitivas ──────────────────────────────────────────────────
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function waitElement(selector, timeout = 5000) {
    return new Promise(resolve => {
        const el = document.querySelector(selector);
        if (el && el.offsetParent !== null) return resolve(el);
        const start = Date.now();
        const id = setInterval(() => {
            const found = document.querySelector(selector);
            if (found && found.offsetParent !== null) { clearInterval(id); resolve(found); return; }
            if (Date.now() - start > timeout) { clearInterval(id); resolve(null); }
        }, 100);
    });
}

function waitElementVisible(selector, timeout = 8000) {
    return new Promise(resolve => {
        const start = Date.now();
        const id = setInterval(() => {
            const el = document.querySelector(selector);
            if (el) { clearInterval(id); resolve(el); return; }
            if (Date.now() - start > timeout) { clearInterval(id); resolve(null); }
        }, 100);
    });
}

// ── Formatação ──────────────────────────────────────────────────
function formatMoney(value) {
    const n = typeof value === 'string' ? parseMoney(value) : value;
    return Number.isFinite(n)
        ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : '0,00';
}

function parseMoney(str) {
    if (!str) return 0;
    const n = parseFloat(
        String(str).replace(/R\$\s*/g, '').replace(/\./g, '').replace(',', '.').trim()
    );
    return Number.isFinite(n) ? n : 0;
}

function normalizeText(str) {
    return String(str)
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase()
        .trim();
}

// ── UI ───────────────────────────────────────────────────────────
function showToast(text, color = '#333', duration = 4000) {
    document.getElementById('pjetools-toast')?.remove();
    const t = document.createElement('div');
    t.id = 'pjetools-toast';
    t.textContent = text;
    t.style.cssText = `position:fixed;top:15px;right:15px;background:${color};color:#fff;` +
        `padding:10px 16px;z-index:9999999;border-radius:4px;font-weight:bold;` +
        `box-shadow:0 3px 6px rgba(0,0,0,.4);font-family:sans-serif;max-width:380px;` +
        `white-space:pre-wrap;font-size:13px;`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), duration);
}

function playBeep(freq = 880, ms = 100) {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = 'sine'; osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        osc.start(ctx.currentTime); osc.stop(ctx.currentTime + ms / 1000);
        setTimeout(() => ctx.close(), ms + 200);
    } catch (e) {}
}

// ── DOM helpers ──────────────────────────────────────────────────
function addStyles(css, id) {
    if (id && document.getElementById(id)) return;
    const s = document.createElement('style');
    if (id) s.id = id;
    s.textContent = css;
    document.head.appendChild(s);
}

function hoverAndDispatch(el) {
    const opts = { bubbles: true, cancelable: true, view: window };
    ['mouseover', 'mouseenter', 'mousemove'].forEach(type =>
        el.dispatchEvent(new MouseEvent(type, opts))
    );
}

// ── SPA monitor ──────────────────────────────────────────────────
function monitorarSPA(onNavigate) {
    const orig = history.pushState.bind(history);
    history.pushState = function (...args) {
        orig(...args);
        setTimeout(onNavigate, 50);
    };
    window.addEventListener('popstate', () => setTimeout(onNavigate, 50));
}

// ── Anti-duplicação ──────────────────────────────────────────────
function antiDuplicacao(attr) {
    if (document.documentElement.hasAttribute(attr)) return false;
    document.documentElement.setAttribute(attr, '1');
    return true;
}

// ────────────────────────────────────────────────────────────
// modules/lista/lista.timeline.js
// ────────────────────────────────────────────────────────────
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

// Meses PT para número
const MESES_PT = {
    jan:'01',fev:'02',mar:'03',abr:'04',mai:'05',jun:'06',
    jul:'07',ago:'08',set:'09',out:'10',nov:'11',dez:'12',
};

function extrairData(item) {
    let el = null;
    let prev = item.previousElementSibling;
    while (prev) {
        el = prev.querySelector('.tl-data[name="dataItemTimeline"]') ||
             prev.querySelector('.tl-data');
        if (el) break;
        prev = prev.previousElementSibling;
    }
    if (!el) el = item.querySelector('.tl-data[name="dataItemTimeline"]') ||
                  item.querySelector('.tl-data');
    const txt = el?.textContent.trim() || '';

    // dd/mm/yyyy
    const m1 = txt.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
    if (m1) return m1[1];

    // "20 out. 2025"
    const m2 = txt.match(/(\d{1,2})\s+(\w{3})\.\s+(\d{4})/);
    if (m2) {
        const mes = MESES_PT[m2[2].toLowerCase()];
        if (mes) return `${m2[1].padStart(2,'0')}/${mes}/${m2[3].slice(-2)}`;
    }
    return '';
}

function extrairUid(link) {
    const m = link.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
    return m ? m[1] : null;
}

function classificarItem(low, tipoTexto, titulo) {
    if (low.includes('devolução de ordem')) return 'Certidão devolução pesquisa';
    if (low.includes('certidão de oficial') || low.includes('oficial de justiça'))
        return 'Certidão de oficial de justiça';
    if ((low.includes('mandado de pagamento') && (low.includes('alvará'))))
        return 'Alvarás';
    if ((tipoTexto === 'certidão' || tipoTexto === 'documento diverso') &&
        (titulo.includes('alvará'))) return 'Alvarás';
    if (tipoTexto === 'alvará' || tipoTexto === 'alvara') return 'Alvarás';
    if (low.includes('juntada de alvará')) return 'Alvarás';
    if (low.includes('sobrestamento')) return 'Decisão (Sobrestamento)';
    if (low.includes('serasa') || low.includes('apjur') ||
        low.includes('carta ação') || low.includes('carta acao')) return 'SerasaAntigo';
    if (low.includes('edital')) return 'Edital';
    return null;
}

async function lerTimelineCompleta() {
    const state = PJeState.lista;
    const agora = Date.now();
    if (state.docs && (agora - state.readAt) < CACHE_TTL) return state.docs;

    const seletores = [
        'li.tl-item-container',
        '.tl-data .tl-item-container',
        '.timeline-item',
    ];
    let itens = [];
    for (const s of seletores) {
        itens = document.querySelectorAll(s);
        if (itens.length) break;
    }

    const documentos = [];

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
        const texto  = textLink.textContent.trim();
        const low    = texto.toLowerCase();
        const tipo   = classificarItem(low, tipoTexto, titulo);
        if (!tipo) continue;

        // ID: usar UID do texto ou fallback index
        const id = extrairUid(textLink) || `doc${i}`;

        // IMPORTANTE: guardar apenas o ID do elemento, não a referência DOM
        // A referência será re-resolvida no momento do uso (evita memory leak)
        documentos.push({
            tipo, texto, id, tipoTexto,
            elementoId: item.id || null,
            elementoSel: item.id ? `#${CSS.escape(item.id)}` : null,
            linkId: iconLink.id || null,
            data: extrairData(item),
            isAnexo: false,
        });

        // Buscar anexos Serasa/CNIB apenas para certidões
        const isCertAlvo = (tipo === 'Certidão devolução pesquisa' ||
                            tipo === 'Certidão de oficial de justiça');
        if (isCertAlvo) {
            const anexosRoot = item.querySelector('pje-timeline-anexos');
            let anexoLinks = anexosRoot
                ? anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]') : [];

            // Expandir se necessário
            if (!anexoLinks.length) {
                const toggle = item.querySelector(
                    'pje-timeline-anexos div[name="mostrarOuOcultarAnexos"]');
                if (toggle) {
                    try { toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
                    catch(e) {}
                    await sleep(350);
                    anexoLinks = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                }
            }

            Array.from(anexoLinks).forEach(anexo => {
                const t = (anexo.textContent || '').toLowerCase();
                const tipoAnexo = /serasa|serasajud/.test(t) ? 'Serasa'
                                : /cnib|indisp/.test(t)       ? 'CNIB'
                                : null;
                if (!tipoAnexo) return;
                documentos.push({
                    tipo: tipoAnexo, texto: anexo.textContent.trim(),
                    id: anexo.id || `anexo_${id}_${tipoAnexo}`,
                    elementoId: anexo.id || null,
                    elementoSel: anexo.id ? `a[id="${anexo.id}"]` : null,
                    linkId: anexo.id || null,
                    data: extrairData(item),
                    isAnexo: true, parentId: id,
                });
            });
        }
    }

    state.docs = documentos;
    state.readAt = agora;
    return documentos;
}

function invalidarCacheTimeline() {
    PJeState.lista.docs = null;
    PJeState.lista.readAt = 0;
}

// Helper para re-resolver elemento pelo ID/seletor salvo
function resolverElemento(doc) {
    if (doc.elementoSel) return document.querySelector(doc.elementoSel);
    if (doc.elementoId) return document.getElementById(doc.elementoId);
    return null;
}

function resolverLink(doc) {
    if (doc.linkId) return document.getElementById(doc.linkId) ||
                           document.querySelector(`a[id="${doc.linkId}"]`);
    return null;
}

// ────────────────────────────────────────────────────────────
// modules/lista/lista.check.js
// ────────────────────────────────────────────────────────────
// ── Predicados ──────────────────────────────────────────────────
const isCertDevolucao = d => d.tipo.toLowerCase().includes('certidão devolução');
const isCertOficial   = d => d.tipo.toLowerCase().includes('certidão de oficial');
const isAlvara        = d => d.tipo.toLowerCase() === 'alvarás';
const isSobrest       = d => d.tipo.toLowerCase().includes('sobrestamento');
const isSerasaAntigo  = d => d.tipo === 'SerasaAntigo';

const byDataDesc = (a, b) => {
    const da = (a.data||'').split('/').reverse().join('').padEnd(8,'0');
    const db = (b.data||'').split('/').reverse().join('').padEnd(8,'0');
    return db.localeCompare(da);
};

function filtrarDocs(docs) {
    return docs.filter(d => {
        const tipo  = (d.tipo  || '').toLowerCase();
        const texto = (d.texto || '').toLowerCase();
        if (tipo === 'edital') return false;
        if (/expedi[cç][aã]o/.test(tipo)  && /ordem/.test(tipo))  return false;
        if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
        if ((tipo === 'alvarás') && /(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto))
            return false;
        return true;
    });
}

function construirOrdem(docs) {
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

function renderTabela(id, titulo, corBorda, saida, onRowClick) {
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
    tbl.innerHTML = `<thead><tr>${
        ['Documento','Data','ID'].map((h, i) =>
            `<th style="padding:6px;font-size:12px;text-align:${i===0?'left':i===1?'center':'right'};` +
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
                `text-align:${i===0?'left':i===1?'center':'right'}`;
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
            .forEach(b => { try { b.click(); } catch(e) {} });
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

async function executarCheck() {
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

async function executarBaixarAutomatico(saida) {
    const serasaCnib = (saida || []).filter(d =>
        (d.tipo === 'Serasa' || d.tipo === 'CNIB') && d.isAnexo
    );
    if (!serasaCnib.length) { alert('Nenhum Serasa/CNIB para baixar'); return; }

    for (let i = 0; i < serasaCnib.length; i++) {
        const item = serasaCnib[i];
        try {
            document.querySelectorAll(
                'button.ui-dialog-titlebar-close, .ui-dialog-titlebar-close')
                .forEach(b => { try { b.click(); } catch(e) {} });
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
        } catch(e) { console.error('[CHECK] Erro baixar:', e); }
    }
}

// ────────────────────────────────────────────────────────────
// modules/lista/lista.edital.js
// ────────────────────────────────────────────────────────────
async function executarEdital() {
    const docs = await lerTimelineCompleta();
    const editais = docs.filter(d => d.tipo === 'Edital').sort(byDataDesc);
    const saida = editais.map(e => ({ ...e, _label: 'Edital' }));

    renderTabela('listaDocsEditalSimples', '📣 Relatório de Editais', '#28a745',
        saida, async (doc) => {
            const elem = resolverElemento(doc);
            if (elem) {
                elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                elem.classList.add('pjetools-destaque-edital');
                setTimeout(() => elem?.classList.remove('pjetools-destaque-edital'), 3000);
            }
        });
}

// ────────────────────────────────────────────────────────────
// modules/lista/lista.sigilo.js
// ────────────────────────────────────────────────────────────
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

                    // 3. Clicar "Marcar Todas"
                    try {
                        let marcarTodasBtn = null;
                        const iconeMarcarTodas = modal.querySelector('i.fa-check.marcar-todas');
                        if (iconeMarcarTodas) {
                            marcarTodasBtn = iconeMarcarTodas.closest('button, div[role="button"]') || iconeMarcarTodas;
                        }
                        if (!marcarTodasBtn) {
                            marcarTodasBtn = modal.querySelector('.marcar-todas');
                        }
                        if (!marcarTodasBtn) {
                            const botaoIcone = modal.querySelector('i.fa-check.botao-icone-titulo-coluna');
                            if (botaoIcone) {
                                marcarTodasBtn = botaoIcone.closest('button, div[role="button"]') || botaoIcone;
                            }
                        }
                        if (marcarTodasBtn) {
                            console.log('[V] Clicando "Marcar Todas"...');
                            if (marcarTodasBtn.tagName === 'BUTTON' || marcarTodasBtn.getAttribute('role') === 'button') {
                                marcarTodasBtn.click();
                            } else {
                                const parentBtn = marcarTodasBtn.closest('button');
                                if (parentBtn) {
                                    parentBtn.click();
                                } else {
                                    marcarTodasBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                }
                            }
                            await sleep(400);
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

        if (totalProcessados > 0) {
            console.log(`[V] ✅ Concluído! ${totalProcessados} anexo(s) processado(s) com visibilidade`);
        } else {
            console.log('[V] ⚠️ Nenhum anexo encontrado para processar');
        }

    } catch (e) {
        console.error('[V] Erro:', e);
    }
}

async function aplicarVisibilidadeSigilosamente() {
    showToast('🔐 Iniciando visibilidade...', '#d9534f');
    try {
        const itens = Array.from(document.querySelectorAll('li.tl-item-container'));
        if (!itens.length) { alert('⚠ Nenhum item na timeline'); return; }

        let total = 0;
        let achouPrimeiro = false;

        for (const item of itens) {
            if (achouPrimeiro) break;
            const anexosComp = item.querySelector('pje-timeline-anexos');
            if (!anexosComp) continue;

            const toggle = anexosComp.querySelector('div[name="mostrarOuOcultarAnexos"]');
            if (!toggle) continue;

            const jaExpandido = toggle.getAttribute('aria-pressed') === 'true';
            if (!jaExpandido) {
                toggle.click();
                await sleep(600);
            }
            await sleep(200);
            const links = anexosComp.querySelectorAll('a.tl-documento[id^="anexo_"]');
            if (!links.length) continue;
            achouPrimeiro = true;

            for (const anexo of links) {
                try {
                    const icone = anexo.querySelector('i.fa-plus, [class*="plus"]') ||
                                  anexo.parentElement?.querySelector('i.fa-plus, [class*="plus"]');
                    if (!icone) continue;
                    (icone.closest('button') || icone).click();
                    await sleep(1500);

                    // Aguardar modal de visibilidade
                    let modal = null;
                    for (let t = 0; t < 30; t++) {
                        for (const m of document.querySelectorAll(
                            '.cdk-overlay-container .mat-dialog-container')) {
                            if (m.innerHTML.includes('Visibilidade') &&
                                (m.innerHTML.includes('partes') || m.innerHTML.includes('Atribuir'))) {
                                modal = m; break;
                            }
                        }
                        if (modal) break;
                        await sleep(200);
                    }
                    if (!modal) {
                        document.body.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
                        await sleep(800); continue;
                    }

                    // Marcar Todas
                    const marcarSels = [
                        'i.fa-check.marcar-todas', '.marcar-todas',
                        'i.fa-check.botao-icone-titulo-coluna',
                    ];
                    let btnMarcar = null;
                    for (const s of marcarSels) {
                        const ic = modal.querySelector(s);
                        if (ic) { btnMarcar = ic.closest('button, div[role="button"]') || ic; break; }
                    }
                    if (btnMarcar) { btnMarcar.click(); await sleep(400); }

                    // Salvar
                    const btnSalvar = Array.from(modal.querySelectorAll('button'))
                        .find(b => (b.textContent||'').trim().toLowerCase().includes('salvar'));
                    if (btnSalvar) { btnSalvar.click(); await sleep(1500); total++; }
                    else {
                        document.body.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
                        await sleep(800);
                    }
                } catch(e) {
                    document.body.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
                    await sleep(800);
                }
            }
        }
        showToast(`✅ Visibilidade: ${total} anexo(s) processado(s)`, '#28a745', 5000);
    } catch(e) {
        showToast(`❌ Erro: ${e.message}`, '#dc3545');
    }
}

// ────────────────────────────────────────────────────────────
// modules/lista/lista.sibajud.js
// ────────────────────────────────────────────────────────────
// ── Acumulador SISBAJUD ─────────────────────────────────────────
// Usa CleanupRegistry para limpar o timer de reset automaticamente
let _sisbAccum = { executados: {}, protocolos: [] };
let _sisbTimerId = null;
const SISB_TIMEOUT = 15000;

function _resetSisbAccum() {
    _sisbAccum = { executados: {}, protocolos: [] };
    _sisbTimerId = null;
}

function _acumularDados(executados, protocolo) {
    Object.assign(_sisbAccum.executados, executados);
    if (!_sisbAccum.protocolos.includes(protocolo))
        _sisbAccum.protocolos.push(protocolo);
    // Limpar timer anterior ANTES de criar novo (evita acúmulo)
    if (_sisbTimerId) clearTimeout(_sisbTimerId);
    _sisbTimerId = setTimeout(_resetSisbAccum, SISB_TIMEOUT);
}

// Registra o timer no CleanupRegistry para limpeza em dispose()
PJeState.registry.add(() => {
    if (_sisbTimerId) clearTimeout(_sisbTimerId);
    _resetSisbAccum();
});

async function extrairRelatorioSISB() {
    for (let t = 0; t < 25; t++) {
        const modal = document.querySelector(
            '.cdk-overlay-container .mat-dialog-container');
        if (!modal) { await sleep(600); continue; }
        const txt = modal.innerText || modal.textContent || '';
        if (!txt.includes('protocolo') && !txt.includes('Protocolo')) {
            await sleep(600); continue;
        }
        const matchProto = modal.innerHTML.match(/Número do protocolo:\s*(\d+)/i);
        const protocolo = matchProto ? matchProto[1] : 'N/A';

        const executados = {};
        const padrao = /(\d+):\s*(.+?)\s+R\$\s*([\d.,]+)/g;
        let m;
        while ((m = padrao.exec(modal.innerHTML)) !== null) {
            executados[m[2].trim()] = m[3].trim();
        }
        _acumularDados(executados, protocolo);
        return { protocolo, executados };
    }
    return null;
}

function _formatValorSISB(v) {
    const n = parseFloat(v.replace(/[^\d,]/g,'').replace(',','.'));
    return Number.isFinite(n)
        ? n.toLocaleString('pt-BR', { style:'currency', currency:'BRL' })
        : v;
}

function _gerarRelatorioHTML() {
    const pS = 'style="margin:0;padding:0;text-indent:4.5cm;line-height:1.5;"';
    let html = `<p ${pS}><strong>BLOQUEIOS TRANSFERIDOS - SISBAJUD</strong></p>`;
    Object.entries(_sisbAccum.executados).forEach(([nome, valor]) => {
        const lbl = _sisbAccum.protocolos.length > 1 ? 'Protocolos' : 'Protocolo';
        html += `<p ${pS}>- ${nome}: Ordens com bloqueios transferidos` +
            ` [${lbl}: ${_sisbAccum.protocolos.join(', ')}]` +
            ` - Total: ${_formatValorSISB(valor)}</p>`;
    });
    return html;
}

function _copiarHTMLFormatado() {
    const html = _gerarRelatorioHTML();
    const div = document.createElement('div');
    div.innerHTML = html;
    document.body.appendChild(div);
    try {
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(div);
        sel.removeAllRanges(); sel.addRange(range);
        document.execCommand('copy');
        sel.removeAllRanges();
    } finally {
        document.body.removeChild(div);
    }
}

async function executarSISBAJUD() {
    try {
        showToast('🏦 Extraindo SISBAJUD...', '#6f42c1');
        const resultado = await extrairRelatorioSISB();
        if (resultado) {
            await sleep(300);
            _copiarHTMLFormatado();
            alert(`✅ Relatório copiado!\n\nProtocolo: ${resultado.protocolo}\n` +
                `Executados: ${Object.keys(_sisbAccum.executados).length}`);
        } else {
            alert('⚠ Nenhum modal SISBAJUD encontrado');
        }
    } catch(e) {
        alert(`❌ Erro: ${e.message}`);
        console.error('[SISB]', e);
    }
}

// ── Pgto ─────────────────────────────────────────────────────────
async function executarPgto() {
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const alvaras = filtrados
        .filter(d => d.tipo.toLowerCase() === 'alvarás' && d.data)
        .map(a => ({ data: a.data, link: resolverLink(a)?.getAttribute('href') || '#' }));
    localStorage.setItem('pjeplus_alvaras', JSON.stringify(alvaras));

    const match = window.location.href.match(/\/processo\/(\d+)\//);
    if (match) {
        window.open(
            `https://pje.trt2.jus.br/pjekz/pagamento/${match[1]}/cadastro`, '_blank');
    } else {
        alert('⚠ Não foi possível identificar o número do processo na URL');
    }
}

// ────────────────────────────────────────────────────────────
// modules/atalhos/atalhos.js
// ────────────────────────────────────────────────────────────
const CHANNEL_NAME = 'maispje_expediente_worker';

function initAtalhos() {
    const reg = PJeState.atalhos.registry;

    // Garante channel único (fechar anterior se existir)
    if (PJeState.atalhos.channel) {
        try { PJeState.atalhos.channel.close(); } catch(e) {}
    }
    const channel = new BroadcastChannel(CHANNEL_NAME);
    PJeState.atalhos.channel = channel;
    reg.channel(channel);

    // Escutar resposta do worker
    reg.on(channel, 'message', async event => {
        if (event.data?.type === 'WORKER_DONE') {
            showToast('F7: Expediente concluído. Limpando...', '#ff9800');
            await runCleanup();
            await sleep(500);
            await hoverAndClickTarget('pje-gigs', 'Inativar atividades');
        }
        if (event.data?.type === 'WORKER_ERROR') {
            showToast(`Worker erro: ${event.data.message}`, '#f44336');
        }
    });

    // Teclas F6 / F7
    reg.on(document, 'keydown', async e => {
        if (e.key === 'F6') {
            e.preventDefault();
            showToast('F6: Iniciando limpeza GIGS...', '#ff9800');
            await runCleanup();
        } else if (e.key === 'F7') {
            e.preventDefault();
            showToast('F7: Abrindo aba de expediente...', '#673ab7');
            await runExpedienteFlow(channel);
        }
    });
}

// ── GIGS cleanup ─────────────────────────────────────────────────
async function runCleanup() {
    const runner = new AsyncRunner();  // runner local, não persiste
    await runner.run(async (signal) => {
        let removed = 0;
        let hasMore = true;
        while (hasMore && !signal.aborted) {
            hasMore = false;
            for (const row of document.querySelectorAll(
                'pje-gigs-atividades table tbody tr')) {
                if (signal.aborted) break;
                if (row.style.display === 'none') continue;
                const desc = row.querySelector('td .descricao')?.textContent.trim();
                if (!desc) continue;
                const prazo = row.querySelector('pje-gigs-alerta-prazo .prazo');
                if (!prazo) continue;
                if (prazo.querySelector('i.fa-clock.far.success')) continue;
                const isVencida  = prazo.querySelector('i.danger.fa-clock.far');
                const isSemPrazo = prazo.querySelector('i.fa.fa-pen.atividade-sem-prazo');
                const descL = desc.toLowerCase();
                const hasXsSilas = descL.includes('xs') || descL.includes('silas');
                const hasDomE    = desc.includes('Dom.E');
                if (!((isVencida && hasXsSilas) ||
                      (isSemPrazo && (hasXsSilas || hasDomE)))) continue;
                const btnEx = row.querySelector('button[mattooltip="Excluir Atividade"]');
                if (!btnEx) continue;
                btnEx.click(); await sleep(800);
                let btnSim = null;
                for (const b of document.querySelectorAll('button[color="primary"]')) {
                    if (b.querySelector('span.mat-button-wrapper')?.textContent.trim() === 'Sim') {
                        btnSim = b; break;
                    }
                }
                if (btnSim) { btnSim.click(); await sleep(600); removed++; hasMore = true; break; }
            }
        }
        showToast(`✅ GIGS: ${removed} atividade(s) removida(s)`, '#4caf50', 5000);
    });
}

// ── Expediente flow ──────────────────────────────────────────────
async function runExpedienteFlow(channel) {
    const url = window.location.href
        .replace(/\/detalhe.*/, '/comunicacoesprocessuais/minutas?maispje_worker=1');
    window.open(url, '_blank');
}

async function hoverAndClickTarget(menuSelector, buttonLabel) {
    const triggerEl = document.querySelector(menuSelector);
    if (!triggerEl) {
        showToast(`Menu não encontrado! (${menuSelector})`, '#f44336');
        return;
    }
    hoverAndDispatch(triggerEl);
    const container = await waitElement('maispjecontaineraa', 3000);
    if (!container) { showToast('Timeout: Menu MaisPJe não abriu!', '#f44336'); return; }
    await sleep(250);
    const labelL = buttonLabel.toLowerCase();
    const alvo = Array.from(container.querySelectorAll('button, div, span, a'))
        .find(el => {
            const txt = (el.textContent || '').toLowerCase().trim();
            return txt === labelL || txt.includes(labelL);
        });
    if (alvo) {
        alvo.style.border = '2px solid red';
        await sleep(150);
        (alvo.querySelector('.mat-button-wrapper') || alvo).click();
        showToast(`Ação disparada: ${buttonLabel}`, '#4caf50');
    } else {
        showToast(`Botão não encontrado: ${buttonLabel}`, '#f44336');
    }
}

// ────────────────────────────────────────────────────────────
// modules/atalhos/atalhos.worker.js
// ────────────────────────────────────────────────────────────
// Executado APENAS na aba worker (?maispje_worker=1)
// Responsabilidade única: salvar + finalizar expediente e avisar a aba principal.

async function runWorker() {
    const channel = new BroadcastChannel('maispje_expediente_worker');

    // Registra fechamento para quando a função terminar
    const cleanup = () => { try { channel.close(); } catch(e) {} };

    try {
        showToast('Worker: Aguardando página...', '#4caf50');

        // Salvar expedientes
        const btnSalvar = await waitElementVisible(
            'button[name="btnSalvarExpedientes"]', 15000) ||
            Array.from(document.querySelectorAll('button'))
                .find(b => b.querySelector('.mat-button-wrapper')
                    ?.textContent.trim() === 'salvar');

        if (btnSalvar) {
            if (!btnSalvar.disabled) btnSalvar.click();
            await sleep(2000);
        }

        // Finalizar / Assinar
        const btnFinalizar = await waitElementVisible(
            'button[name="btnFinalizarExpedientes"]', 10000) ||
            Array.from(document.querySelectorAll('button'))
                .find(b => (b.querySelector('.mat-button-wrapper')
                    ?.textContent || '').toLowerCase().includes('assinar'));

        if (btnFinalizar && !btnFinalizar.disabled) {
            btnFinalizar.click();
            await sleep(1500);
        }

        showToast('Worker: Concluído! Fechando...', '#4caf50');
        channel.postMessage({ type: 'WORKER_DONE' });
    } catch(e) {
        console.error('[WORKER]', e);
        channel.postMessage({ type: 'WORKER_ERROR', message: e.message || 'Erro desconhecido' });
        showToast(`Worker erro: ${e.message}`, '#f44336');
    } finally {
        await sleep(400);
        cleanup();
        setTimeout(() => window.close(), 500);
    }
}

// ────────────────────────────────────────────────────────────
// modules/infojud/infojud.js
// ────────────────────────────────────────────────────────────
const URL_BASE_CPF  = 'https://pje.trt2.jus.br/infojud-frontend/pages/consulta-cpf/';
const URL_BASE_CNPJ = 'https://pje.trt2.jus.br/infojud-frontend/pages/consulta-cnpj/';
const GOD_KEY_STATUS = 'GOD_STATUS';
const GOD_KEY_TIPO   = 'GOD_TIPO_ORIGEM';

function iniciarFluxoInfojud(modo) {
    const state = PJeState.infojud;

    if (state.runner.running) {
        alert('Infojud já está rodando. Aguarde ou recarregue a página.');
        return;
    }

    // Coletar CPF/CNPJ da tela
    const spans = Array.from(
        document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
    const vistos = new Set();
    state.fila = [];
    state.dados = [];
    state.atual = 0;
    state.modo = modo;

    spans.forEach(s => {
        const txt = s.textContent.trim();
        if (/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/.test(txt)) {
            const num = txt.replace(/\D/g,'');
            if (!vistos.has(num)) { vistos.add(num); state.fila.push(num); }
        }
    });

    if (!state.fila.length) { alert('Nenhum CPF/CNPJ encontrado na tela!'); return; }

    // Remover relatório anterior
    document.getElementById('god-relatorio-panel')?.remove();

    GM_setValue(GOD_KEY_STATUS, 'STANDBY');
    showToast(`Infojud ${modo}: ${state.fila.length} doc(s)`, '#0288d1');
    criarBotoesInfojud();
    monitorarSinaisInfojud();
    processarProximoInfojud();
}

function processarProximoInfojud() {
    const state = PJeState.infojud;
    if (state.atual >= state.fila.length) {
        console.log('[GOD] Ciclo finalizado');
        exibirRelatorioFinalInfojud();
        return;
    }

    const doc = state.fila[state.atual];
    highlightLinha(doc);

    if (doc.length === 11) {
        GM_setValue(GOD_KEY_TIPO, 'CPF_DIRETO');
        GM_openInTab(URL_BASE_CPF + doc, { active: true, insert: true });
    } else {
        GM_setValue(GOD_KEY_TIPO, 'CNPJ_DIRETO');
        GM_openInTab(URL_BASE_CNPJ + doc, { active: true, insert: true });
    }
}

function highlightLinha(doc) {
    document.querySelectorAll('span.pec-formatacao-padrao-dados-parte').forEach(s => {
        if (s.textContent.replace(/\D/g,'') === doc) {
            const tr = s.closest('tr');
            if (tr) tr.style.backgroundColor = '#fff9c4';
        }
    });
}

let _godPollId = null;
function monitorarSinaisInfojud() {
    if (_godPollId) clearInterval(_godPollId);
    _godPollId = setInterval(() => {
        const status = GM_getValue(GOD_KEY_STATUS);
        if (status === 'STANDBY') return;
        const state = PJeState.infojud;
        if (status === 'DONE' || status === 'ERROR') {
            clearInterval(_godPollId);
            _godPollId = null;
            const linha = state.fila[state.atual];
            const tr = document.querySelector(`span.pec-formatacao-padrao-dados-parte`)
                ?.closest('tr');
            if (tr) tr.style.backgroundColor = status === 'DONE' ? '#c8e6c9' : '#ef9a9a';
            state.atual++;
            GM_setValue(GOD_KEY_STATUS, 'STANDBY');
            setTimeout(() => {
                monitorarSinaisInfojud();
                processarProximoInfojud();
            }, 800);
        }
    }, 1000);
    // Registrar limpeza no registry
    PJeState.registry.add(() => {
        if (_godPollId) { clearInterval(_godPollId); _godPollId = null; }
    });
}

function exibirRelatorioFinalInfojud() {
    playBeep();
    const painel = document.createElement('div');
    painel.id = 'god-relatorio-panel';
    painel.style.cssText = `position:fixed;bottom:80px;left:20px;background:white;` +
        `border:2px solid #004d40;padding:10px;z-index:10000;width:600px;` +
        `max-height:400px;overflow-y:auto;box-shadow:0 5px 20px rgba(0,0,0,.4);` +
        `border-radius:6px;font-family:'Segoe UI',sans-serif;font-size:12px;`;
    const cab = document.createElement('div');
    cab.innerHTML = `<strong>RELATÓRIO INFOJUD</strong>` +
        `<span style="float:right;cursor:pointer;font-weight:bold" ` +
        `onclick="this.closest('#god-relatorio-panel').remove()">[X]</span>`;
    cab.style.borderBottom = '1px solid #ccc';
    cab.style.marginBottom = '10px';
    painel.appendChild(cab);

    const content = document.createElement('div');
    content.textContent = `${PJeState.infojud.fila.length} documento(s) processado(s).`;
    painel.appendChild(content);
    document.body.appendChild(painel);
    showToast(`✅ Infojud concluído: ${PJeState.infojud.fila.length} doc(s)`, '#4caf50', 6000);
}

function criarBotoesInfojud() {
    document.getElementById('god-btns')?.remove();
    const container = document.createElement('div');
    container.id = 'god-btns';
    container.style.cssText = `position:fixed;top:100px;right:20px;z-index:9999;` +
        `display:flex;flex-direction:column;gap:5px;`;
    const styleBtn = 'padding:10px 20px;color:white;font-weight:bold;cursor:pointer;' +
        'border-radius:4px;box-shadow:0 3px 6px rgba(0,0,0,.3);font-size:14px;border:none;';
    const btnD = document.createElement('button');
    btnD.textContent = 'Infojud Direto';
    btnD.style.cssText = styleBtn + 'background:#0288d1;';
    btnD.onclick = () => iniciarFluxoInfojud('DIRETO');
    const btnC = document.createElement('button');
    btnC.textContent = 'Infojud Correção';
    btnC.style.cssText = styleBtn + 'background:#004d40;';
    btnC.onclick = () => iniciarFluxoInfojud('COMPLETO');
    container.appendChild(btnD);
    container.appendChild(btnC);
    document.body.appendChild(container);
    PJeState.registry.add(() => container.remove());
}

// ────────────────────────────────────────────────────────────
// ui/painel.js
// ────────────────────────────────────────────────────────────
const CSS_PAINEL = `
.pjetools-destaque        { outline:3px solid #007bff!important; background:#e7f3ff!important; transition:.3s; }
.pjetools-destaque-edital { outline:3px solid #28a745!important; background:#e8f5e8!important; transition:.3s; }
#pjetools-painel button:hover { opacity:.85; }
`;

function criarPainel(botoes) {
    document.getElementById('pjetools-painel')?.remove();
    addStyles(CSS_PAINEL, 'pjetools-styles');

    const painel = document.createElement('div');
    painel.id = 'pjetools-painel';
    painel.style.cssText = `position:fixed;bottom:170px;right:20px;z-index:99999;` +
        `background:#fff;border:2px solid #333;border-radius:8px;` +
        `box-shadow:0 8px 32px rgba(0,0,0,.25);padding:10px 12px;font-family:sans-serif;` +
        `min-width:190px;user-select:none;`;

    const titulo = document.createElement('div');
    titulo.textContent = 'PJeTools v1.0';
    titulo.style.cssText = `font-weight:bold;margin-bottom:8px;color:#333;font-size:12px;` +
        `text-align:center;border-bottom:1px solid #ddd;padding-bottom:6px;`;
    painel.appendChild(titulo);

    const grid = document.createElement('div');
    grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:6px;';

    botoes.forEach(btn => {
        const b = document.createElement('button');
        b.id = btn.id;
        b.textContent = btn.texto;
        b.title = btn.titulo || '';
        b.style.cssText = `padding:7px 6px;background:${btn.bg};color:#fff;border:none;` +
            `border-radius:4px;cursor:pointer;font-weight:bold;font-size:11px;` +
            `transition:opacity .15s;`;
        b.onclick = btn.fn;
        if (btn.full) b.style.gridColumn = '1 / -1';
        grid.appendChild(b);
    });

    painel.appendChild(grid);

    // Botão limpar cache
    const limparBtn = document.createElement('button');
    limparBtn.textContent = '🔄 Limpar Cache';
    limparBtn.style.cssText = `margin-top:8px;width:100%;padding:5px;background:#6c757d;` +
        `color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:10px;`;
    limparBtn.onclick = () => {
        invalidarCacheTimeline();
        showToast('Cache da timeline limpo', '#6c757d', 2000);
    };
    painel.appendChild(limparBtn);

    // Arrastar
    _tornaPainelArrastavel(painel);

    document.body.appendChild(painel);
    PJeState.registry.add(() => painel.remove());
}

function _tornaPainelArrastavel(el) {
    let ox = 0, oy = 0, drag = false;
    const onDown = e => {
        if (e.target.tagName === 'BUTTON') return;
        drag = true; ox = e.clientX - el.offsetLeft; oy = e.clientY - el.offsetTop;
        e.preventDefault();
    };
    const onMove = e => {
        if (!drag) return;
        el.style.left = (e.clientX - ox) + 'px';
        el.style.top  = (e.clientY - oy) + 'px';
        el.style.right = 'auto'; el.style.bottom = 'auto';
    };
    const onUp = () => { drag = false; };
    el.addEventListener('mousedown', onDown);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    // Limpeza quando painel for removido
    PJeState.registry.add(() => {
        el.removeEventListener('mousedown', onDown);
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    });
}

function inicializarPainel() {
    criarPainel([
        { id:'btnCheck',   texto:'🔎 Check',    bg:'#007bff', fn: executarCheck,     titulo:'Relatório de Medidas' },
        { id:'btnEdital',  texto:'📣 Edital',   bg:'#28a745', fn: executarEdital,    titulo:'Relatório de Editais' },
        { id:'btnSigilo',  texto:'🔐 Sigilo',   bg:'#d9534f', fn: aplicarVisibilidadeSigilosamente, titulo:'Marcar visibilidade' },
        { id:'btnPgto',    texto:'💳 Pgto',     bg:'#ff6600', fn: executarPgto,      titulo:'Abrir página de pagamento' },
        { id:'btnSISBAJUD',texto:'🏦 SISBAJUD', bg:'#6f42c1', fn: executarSISBAJUD,  titulo:'Extrair relatório SISBAJUD' },
        { id:'btnInfojud', texto:'🔍 Infojud',  bg:'#0288d1', fn: ()=> criarBotoesInfojud(), titulo:'Busca de endereços', full: true },
    ]);
}

// ────────────────────────────────────────────────────────────
// orchestrator.js
// ────────────────────────────────────────────────────────────
(function () {
    'use strict';

    if (window.self !== window.top) return;

    const url = window.location.href;

    const isMinutas    = /\/comunicacoesprocessuais\/minutas/.test(url);
    const isPagamento  = /\/pagamento\/\d+\/cadastro/.test(url);
    const isWorkerTab  = isMinutas &&
        new URLSearchParams(location.search).get('maispje_worker') === '1';

    if (isPagamento) {
        waitElement('mat-card').then(() => {
            console.log('[PJeTools] Página de pagamento detectada');
        });
        return;
    }

    if (isWorkerTab) {
        if (document.documentElement.hasAttribute('data-pjetools-worker')) return;
        document.documentElement.setAttribute('data-pjetools-worker', '1');
        window.addEventListener('load', () => setTimeout(runWorker, 2000));
        return;
    }

    if (!antiDuplicacao('data-pjetools-boot')) return;

    monitorarSPA(() => {
        PJeState.dispose();
        setTimeout(boot, 300);
    });

    boot();

    function boot() {
        if (!antiDuplicacao('data-pjetools-boot')) return;

        const currentUrl = window.location.href;
        const onDetalhe = /\/processo\/\d+\/detalhe/.test(currentUrl);

        if (onDetalhe && !PJeState._iniciado) {
            PJeState._iniciado = true;
            inicializarPainel();
            initAtalhos();
        }
    }

})();

})();
