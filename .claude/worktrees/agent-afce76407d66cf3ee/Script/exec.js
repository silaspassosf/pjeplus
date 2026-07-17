// ==UserScript==
// @name         PJe Lista Check (via API)
// @namespace    http://tampermonkey.net/
// @version      0.1.0
// @description  Mesmo que exec.js (Argos, Sisbajud, etc.), mas obtém a timeline via endpoint de API em vez de varrer o DOM
// @author       Silas
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==
(function () {
    'use strict';

    const CACHE_TTL = 5 * 60 * 1000;
    const ONE_YEAR_MS = 365 * 24 * 60 * 60 * 1000;
    const COLORS = {
        border: '#1565c0',
        recent: '#e3f2fd',
        selected: '#fff7d6',
        hover: '#f0f7ff'
    };

    const cache = { docs: null, ts: 0 };

    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

    // ─── UTILITÁRIOS DE API ───────────────────────────────────────────────

    function extrairIdProcessoUrl() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }

    function obterXsrf() {
        const c = document.cookie.split(';')
            .map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function headersApi() {
        const xsrf = obterXsrf();
        const h = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1',
        };
        if (xsrf) h['X-XSRF-TOKEN'] = xsrf;
        return h;
    }

    // ─── NORMALIZAÇÃO ─────────────────────────────────────────────────────

    /** Converte data ISO ("2025-01-15T00:00:00") para "15/01/25". */
    function normalizarDataApi(dataStr) {
        if (!dataStr) return '';
        const m = dataStr.match(/(\d{4})-(\d{2})-(\d{2})/);
        if (m) return `${m[3]}/${m[2]}/${m[1].slice(2)}`;
        return dataStr;
    }

    function parseDate(dateStr) {
        if (!dateStr) return null;
        const parts = dateStr.split('/').map(x => parseInt(x, 10));
        if (parts.length !== 3) return null;
        const [d, m, y] = parts;
        return new Date(y < 100 ? 2000 + y : y, m - 1, d);
    }

    function dataMaisRecente(a, b) {
        const da = parseDate(a.data);
        const db = parseDate(b.data);
        if (!da && !db) return 0;
        if (!da) return 1;
        if (!db) return -1;
        return db - da;
    }

    function isLessThanOneYear(dateStr) {
        const dt = parseDate(dateStr);
        if (!dt) return false;
        return (Date.now() - dt.getTime()) < ONE_YEAR_MS;
    }

    // ─── CLASSIFICAÇÃO ────────────────────────────────────────────────────

    /**
     * Classifica item da API pelo campo titulo (e descricao, se houver).
     * Mesma lógica de classificarItem em exec.js.
     */
    function classificarItemApi(item) {
        const low = ((item.titulo || '') + ' ' + (item.descricao || '')).toLowerCase();
        if (low.includes('pesquisa patrimonial')) return 'Argos';
        if (low.includes('sisbajud') || low.includes('teimosinha')) return 'Sisbajud';
        if (low.includes('censec') || low.includes('campo')) return 'Censec';
        if (low.includes('ccs')) return 'CCS';
        if (low.includes('cnseg')) return 'CNSEG';
        if (low.includes('sniper')) return 'Sniper';
        if (low.includes('prevjud')) return 'Prevjud';
        if (low.includes('simba')) return 'Simba';
        if (low.includes('mandado')) return 'Penhora';
        return null;
    }

    // ─── FETCH TIMELINE VIA API ───────────────────────────────────────────

    async function fetchTimelineApi(idProcesso) {
        const params = new URLSearchParams({
            buscarMovimentos: 'false',
            buscarDocumentos: 'true',
            somenteDocumentosAssinados: 'false',
        });
        const url = location.origin
            + '/pje-comum-api/api/processos/id/' + idProcesso
            + '/timeline?' + params.toString();
        const resp = await fetch(url, { method: 'GET', credentials: 'include', headers: headersApi() });
        if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ao buscar timeline');
        const txt = await resp.text();
        try { return JSON.parse(txt); }
        catch (_) { throw new Error('Timeline API: resposta não é JSON — ' + txt.slice(0, 100)); }
    }

    async function lerTimelineViaApi() {
        const agora = Date.now();
        if (cache.docs && (agora - cache.ts) < CACHE_TTL) return cache.docs;

        const idProcesso = extrairIdProcessoUrl();
        if (!idProcesso) return [];

        let itens;
        try {
            itens = await fetchTimelineApi(idProcesso);
        } catch (e) {
            console.error('[ExecApi] Falha ao buscar timeline:', e.message);
            return [];
        }

        // Filtrar somente documentos (têm idUnicoDocumento)
        const documentos = [];
        let argosLogados = 0;

        for (const item of itens) {
            if (!item.idUnicoDocumento) continue;

            const tipo = classificarItemApi(item);
            if (!tipo) continue;

            const id = item.idUnicoDocumento;
            const idDoc = item.id ? String(item.id) : null;
            const data = normalizarDataApi(item.data || item.atualizadoEm || '');
            const texto = item.titulo || '';

            if (tipo === 'Argos' && argosLogados < 2) {
                argosLogados++;
                console.log(`[ExecApi] Argos #${argosLogados} | UID: ${id} | idDoc: ${idDoc || '?'} | data: ${data}`);
            }

            documentos.push({ tipo, texto, id, idDoc, data });
        }

        cache.docs = documentos;
        cache.ts = agora;
        return documentos;
    }

    // ─── DOM: ENCONTRAR ELEMENTO PELO UID ────────────────────────────────

    /**
     * Localiza o li.tl-item-container cujo link de texto termina com " - {uid}".
     * Usado pelo onRowClick para interagir com o DOM após detecção via API.
     */
    function encontrarElementoPorUid(uid) {
        if (!uid) return null;
        const itens = document.querySelectorAll('li.tl-item-container');
        for (const item of itens) {
            const textLink = item.querySelector('a.tl-documento:not([target="_blank"])');
            if (!textLink) continue;
            const m = textLink.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
            if (m && m[1] === uid) return item;
        }
        return null;
    }

    // ─── RENDER TABELA ────────────────────────────────────────────────────

    function renderTabela(id, titulo, corBorda, saida, onRowClick) {
        document.getElementById(id)?.remove();
        const panel = document.createElement('div');
        panel.id = id;
        panel.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:100000;background:#fff;` +
            `border:2px solid ${corBorda};border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,.18);` +
            `min-width:360px;max-height:60vh;overflow:auto;font-family:sans-serif;`;

        const hdr = document.createElement('div');
        hdr.style.cssText = `position:sticky;top:0;background:#fff;border-bottom:1px solid #eee;` +
            `display:flex;align-items:center;justify-content:space-between;padding:8px 12px;`;
        hdr.innerHTML = `<span style="font-weight:bold;color:${corBorda};font-size:13px">${titulo}</span>` +
            `<button style="background:#dc3545;color:#fff;border:none;border-radius:50%;` +
            `width:24px;height:24px;cursor:pointer;font-size:14px;line-height:1">✕</button>`;
        hdr.querySelector('button').onclick = () => panel.remove();
        panel.appendChild(hdr);

        if (!saida.length) {
            const nd = document.createElement('div');
            nd.textContent = 'Nenhum item encontrado';
            nd.style.cssText = 'padding:20px;text-align:center;color:#666;font-style:italic;';
            panel.appendChild(nd);
            document.body.appendChild(panel);
            return;
        }

        const tbl = document.createElement('table');
        tbl.id = `${id}_tbl`;
        tbl.style.width = '100%';
        tbl.innerHTML = `<thead><tr>${['Documento', 'Data', 'UID'].map((h, i) =>
            `<th style="padding:6px;font-size:12px;text-align:${i === 0 ? 'left' : i === 1 ? 'center' : 'right'};` +
            `background:#f4f8ff;position:sticky;top:41px">${h}</th>`
        ).join('')}</tr></thead><tbody></tbody>`;

        const tbody = tbl.querySelector('tbody');
        saida.forEach((d, idx) => {
            const tr = document.createElement('tr');
            const isRecent = isLessThanOneYear(d.data);
            tr.style.cssText = 'cursor:pointer;border-bottom:1px solid #eee;';
            tr.dataset.idx = idx;
            tr.dataset.docId = d.id;
            tr.dataset.recent = isRecent ? '1' : '0';
            if (isRecent) tr.style.background = COLORS.recent;

            [d._label || d.tipo || 'Documento', d.data || '', d.id || ''].forEach((val, i) => {
                const td = document.createElement('td');
                td.textContent = val;
                td.style.cssText = `padding:5px 6px;font-size:12px;` +
                    `text-align:${i === 0 ? 'left' : i === 1 ? 'center' : 'right'}`;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        tbl.addEventListener('click', async ev => {
            const tr = ev.target.closest('tr[data-idx]');
            if (!tr) return;
            ev.stopPropagation();
            tbody.querySelectorAll('tr').forEach(r => {
                if (r.dataset.recent === '1') r.style.background = COLORS.recent;
                else r.style.background = '';
            });
            tr.style.background = COLORS.selected;
            const doc = saida[parseInt(tr.dataset.idx, 10)];
            if (doc) await onRowClick(doc);
        });

        tbl.addEventListener('mouseenter', ev => {
            const tr = ev.target.closest('tr[data-idx]');
            if (tr && tr.style.background !== COLORS.selected) tr.style.background = COLORS.hover;
        }, true);
        tbl.addEventListener('mouseleave', ev => {
            const tr = ev.target.closest('tr[data-idx]');
            if (tr && tr.style.background !== COLORS.selected) {
                tr.style.background = tr.dataset.recent === '1' ? COLORS.recent : '';
            }
        }, true);

        panel.appendChild(tbl);
        document.body.appendChild(panel);
    }

    // ─── ON ROW CLICK ─────────────────────────────────────────────────────

    async function onRowClick(doc) {
        // Tenta encontrar o elemento no DOM pelo UID detectado via API
        const elem = encontrarElementoPorUid(doc.id);
        if (elem) {
            const textLink = elem.querySelector('a.tl-documento:not([target="_blank"])');
            if (textLink) {
                textLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                elem.classList.add('pjetools-destaque');
                setTimeout(() => elem.classList.remove('pjetools-destaque'), 3000);
                return;
            }
            const iconLink = elem.querySelector('a.tl-documento[target="_blank"]');
            if (iconLink) {
                iconLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                return;
            }
        }
        console.warn(`[ExecApi] Elemento DOM não encontrado para UID=${doc.id}. Documento pode não estar visível na timeline.`);
    }

    // ─── EXECUÇÃO PRINCIPAL ───────────────────────────────────────────────

    async function executarListaCheckApi() {
        const btn = document.getElementById('listaCheckApiBtn');
        if (btn) { btn.textContent = 'Carregando...'; btn.disabled = true; }
        try {
            cache.docs = null; // forçar refresh
            const docs = await lerTimelineViaApi();
            const saida = docs.sort(dataMaisRecente).map(d => ({ ...d, _label: d.tipo }));
            renderTabela('listaCheckApiPanel', '📋 Lista Check (API)', COLORS.border, saida, onRowClick);
            console.log(`[ExecApi] ${saida.length} documentos encontrados via API`);
        } finally {
            if (btn) { btn.textContent = 'Lista (API)'; btn.disabled = false; }
        }
    }

    function criarBotao() {
        if (document.getElementById('listaCheckApiBtn')) return;
        const btn = document.createElement('button');
        btn.id = 'listaCheckApiBtn';
        btn.textContent = 'Lista (API)';
        btn.title = 'Listar documentos via API (Argos, Sisbajud, etc.)';
        btn.style.cssText = `position:fixed;bottom:20px;left:120px;z-index:100000;` +
            `padding:10px 14px;background:#1565c0;color:#fff;border:none;border-radius:8px;` +
            `box-shadow:0 8px 24px rgba(0,0,0,.18);cursor:pointer;font-size:13px;font-weight:600;`;
        btn.onclick = executarListaCheckApi;
        document.body.appendChild(btn);
    }

    async function waitElement(selector, timeout = 10000) {
        const found = document.querySelector(selector);
        if (found) return found;
        return new Promise(resolve => {
            const observer = new MutationObserver(() => {
                const el = document.querySelector(selector);
                if (el) { observer.disconnect(); resolve(el); }
            });
            observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
            setTimeout(() => { observer.disconnect(); resolve(null); }, timeout);
        });
    }

    async function init() {
        if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) return;
        await waitElement('li.tl-item-container, .timeline-item');
        criarBotao();
    }

    init();
})();
