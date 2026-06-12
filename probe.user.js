// ==UserScript==
// @name         PJe Probe
// @namespace    https://github.com/silaspassosf/pjeplus
// @version      1.0.0
// @description  Probe compacto para mapear cliques, seletores e endpoints reais do PJe a partir da URL atual.
// @author       Perplexity
// @match        https://*/pjekz/*
// @match        https://*/pje/*
// @run-at       document-idle
// @grant        GM_setClipboard
// ==/UserScript==

(function () {
  'use strict';

  if (window.__PJE_PROBE__) return;
  window.__PJE_PROBE__ = true;

  const Probe = {
    on: false,
    t0: 0,
    runId: '',
    pageUrlAtStart: '',
    clicks: [],
    signals: [],
    mutations: [],
    network: [],
    timeline: [],
    observer: null,
    xhrHooked: false,
    fetchHooked: false,
    navTimer: null,
    ui: {},
    attrThrottle: Object.create(null),
    lastUrl: location.href,
    pushedPatched: false,
    allowedNet: [
      /\/api\/agrupamentotarefas\//i,
      /\/api\/processos\//i,
      /\/api\/etiquetas\//i,
      /\/api\/tiposatividades/i,
      /\/api\/fasesprocessuais/i,
      /\/api\/tarefas/i,
      /\/api\/chips/i,
      /\/timeline/i,
      /\/sobrestamentos/i
    ],
    relevantNodeTags: new Set([
      'mat-option',
      'mat-select',
      'mat-chip',
      'mat-chip-list',
      'mat-dialog-container',
      'snack-bar-container',
      'simple-snack-bar',
      'button'
    ]),
    relevantNodeClasses: [
      'mat-option',
      'mat-select',
      'mat-chip',
      'cdk-overlay-pane',
      'cdk-overlay-backdrop',
      'loading-spinner',
      'mat-progress-spinner',
      'mat-mdc-chip'
    ],
    signalSelectors: {
      'button[aria-label="Filtrar"]': 'BtnFiltrar',
      'i.fas.fa-filter': 'IconeFiltrar',
      'mat-option[role="option"]': 'MatOptions',
      '.mat-select-value-text': 'SelectValueText',
      '.mat-chip-list,.mat-mdc-chip-set,.mat-chip': 'Chips',
      '[aria-label*="Tarefa do processo"]': 'FiltroTarefa',
      '[aria-label*="Fase processual"]': 'FiltroFase',
      '[aria-label*="Etiqueta"]': 'FiltroEtiqueta'
    }
  };

  function nowTs() {
    return ((Date.now() - Probe.t0) / 1000).toFixed(3) + 's';
  }

  function makeId() {
    return Math.random().toString(36).slice(2, 10);
  }

  function safeText(v, n = 140) {
    return String(v || '').replace(/\s+/g, ' ').trim().slice(0, n);
  }

  function safeUrl(url) {
    try {
      return new URL(url, location.href).href;
    } catch {
      return String(url || '');
    }
  }

  function compactUrl(url) {
    const full = safeUrl(url);
    try {
      const u = new URL(full);
      return `${u.origin}${u.pathname}${u.search}`;
    } catch {
      return full;
    }
  }

  function shortBody(body, n = 500) {
    if (body == null) return '';
    if (typeof body === 'string') return safeText(body, n);
    if (body instanceof URLSearchParams) return safeText(body.toString(), n);
    if (window.FormData && body instanceof FormData) {
      const pairs = [];
      for (const [k, v] of body.entries()) pairs.push(`${k}=${typeof v === 'string' ? v : '[blob]'}`);
      return safeText(pairs.join('&'), n);
    }
    try {
      return safeText(JSON.stringify(body), n);
    } catch {
      return '[body-unserializable]';
    }
  }

  function cssPath(el) {
    if (!el || !el.tagName) return '';
    const tag = el.tagName.toLowerCase();
    const aria = el.getAttribute && el.getAttribute('aria-label');
    const name = el.getAttribute && el.getAttribute('name');
    const role = el.getAttribute && el.getAttribute('role');
    const id = el.id;
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 3).join('.').slice(0, 80) : '';
    if (aria) return `${tag}[aria-label="${aria}"]`;
    if (name) return `${tag}[name="${name}"]`;
    if (id) return `#${id}`;
    if (role) return `${tag}[role="${role}"]`;
    if (cls) return `${tag}.${cls}`;
    return tag;
  }

  function ancestry(el, depth = 3) {
    const out = [];
    let p = el && el.parentElement;
    while (p && out.length < depth) {
      out.push(cssPath(p));
      p = p.parentElement;
    }
    return out;
  }

  function selectedState(el) {
    if (!el || !el.getAttribute) return false;
    return el.classList.contains('mat-selected') || el.getAttribute('aria-selected') === 'true' || el.getAttribute('aria-checked') === 'true';
  }

  function describeNode(el) {
    return {
      tag: (el.tagName || '').toLowerCase(),
      sel: cssPath(el),
      txt: safeText(el.innerText || el.textContent || '', 100),
      selected: selectedState(el)
    };
  }

  function isRelevantNode(node) {
    if (!node || node.nodeType !== 1) return false;
    const tag = (node.tagName || '').toLowerCase();
    if (Probe.relevantNodeTags.has(tag)) return true;
    const cls = typeof node.className === 'string' ? node.className : '';
    return Probe.relevantNodeClasses.some(c => cls.includes(c));
  }

  function isAllowedRequest(url) {
    const full = safeUrl(url);
    return Probe.allowedNet.some(re => re.test(full));
  }

  function currentFilterSnapshot() {
    const snap = {};
    const selectedOptions = Array.from(document.querySelectorAll('mat-option.mat-selected,[role="option"].mat-selected,[role="option"][aria-selected="true"]'))
      .map(el => safeText(el.innerText || el.textContent || '', 80))
      .filter(Boolean);
    const chips = Array.from(document.querySelectorAll('.mat-chip,.mat-mdc-chip,.mat-chip-selected,.mat-mdc-chip-selected'))
      .map(el => safeText(el.innerText || el.textContent || '', 80))
      .filter(Boolean);
    const placeholders = Array.from(document.querySelectorAll('.mat-select-value-text,.mat-mdc-select-value-text,.mat-select-placeholder'))
      .map(el => safeText(el.innerText || el.textContent || '', 80))
      .filter(Boolean);
    if (selectedOptions.length) snap.selectedOptions = selectedOptions;
    if (chips.length) snap.chips = chips;
    if (placeholders.length) snap.visibleSelectText = placeholders;
    return snap;
  }

  function pushEvent(kind, payload) {
    const event = Object.assign({ type: kind, time: nowTs() }, payload || {});
    Probe.timeline.push(event);
    if (kind === 'clk') Probe.clicks.push(event);
    else if (kind === 'sig') Probe.signals.push(event);
    else if (kind === 'mut') Probe.mutations.push(event);
    else if (kind.startsWith('net:')) Probe.network.push(event);
    updateCounter();
    liveLine(event);
    return event;
  }

  function scanSignals(why) {
    const active = {};
    for (const selector in Probe.signalSelectors) {
      try {
        const els = document.querySelectorAll(selector);
        if (els.length) active[Probe.signalSelectors[selector]] = { n: els.length, selector };
      } catch {}
    }
    pushEvent('sig', { why, active, filters: currentFilterSnapshot() });
  }

  function liveLine(e) {
    const box = Probe.ui.log;
    if (!box) return;
    let line = `${e.time} `;
    if (e.type === 'clk') line += `🖱 ${e.sel} :: ${safeText(e.txt, 40)}`;
    else if (e.type === 'sig') line += `📍 ${e.why}`;
    else if (e.type === 'mut') line += `🧩 ${e.act} ${e.node.sel}${e.node.selected ? ' [selected]' : ''}`;
    else if (e.type === 'net:req') line += `🌐 ${e.method} ${e.url}`;
    else if (e.type === 'net:res') line += `↳ ${e.status} ${e.ms}ms`;
    else if (e.type === 'nav') line += `🔗 ${e.to}`;
    box.textContent += line + '\n';
    const rows = box.textContent.split('\n');
    if (rows.length > 60) box.textContent = rows.slice(-60).join('\n');
    box.scrollTop = box.scrollHeight;
  }

  function updateCounter() {
    if (!Probe.ui.counter) return;
    Probe.ui.counter.textContent = `C:${Probe.clicks.length} M:${Probe.mutations.length} S:${Probe.signals.length} N:${Probe.network.filter(x => x.type === 'net:req').length}`;
  }

  function startObserver() {
    if (Probe.observer) Probe.observer.disconnect();
    Probe.observer = new MutationObserver(mutations => {
      if (!Probe.on) return;
      for (const m of mutations) {
        if (m.type === 'attributes') {
          if (!isRelevantNode(m.target)) continue;
          if (!['class', 'aria-selected', 'aria-checked', 'value'].includes(m.attributeName)) continue;
          const key = `${cssPath(m.target)}::${m.attributeName}`;
          const t = Date.now();
          if (Probe.attrThrottle[key] && t - Probe.attrThrottle[key] < 400) continue;
          Probe.attrThrottle[key] = t;
          const node = describeNode(m.target);
          if (!node.selected && !/mat-selected|aria-selected|aria-checked/.test(m.attributeName)) continue;
          pushEvent('mut', {
            act: 'ATR',
            attr: m.attributeName,
            val: safeText(m.target.getAttribute(m.attributeName), 80),
            node
          });
        }
        if (m.addedNodes) {
          for (const node of m.addedNodes) {
            if (!isRelevantNode(node)) continue;
            const d = describeNode(node);
            if (!d.txt && !/mat-option|mat-chip|overlay|button/.test(d.sel)) continue;
            pushEvent('mut', { act: 'ADD', node: d });
          }
        }
      }
    });
    Probe.observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'aria-selected', 'aria-checked', 'value']
    });
  }

  function hookClicks() {
    document.addEventListener('click', function (ev) {
      if (!Probe.on) return;
      const el = ev.target && ev.target.closest ? ev.target.closest('button,[role="button"],mat-option,.mat-option,.mat-chip,.mat-mdc-chip,.mat-select,.mat-mdc-select,[aria-label]') || ev.target : ev.target;
      if (!el) return;
      pushEvent('clk', {
        sel: cssPath(el),
        tag: (el.tagName || '').toLowerCase(),
        txt: safeText(el.innerText || el.textContent || '', 80),
        ctx: ancestry(el),
        filtersBefore: currentFilterSnapshot()
      });
      clearTimeout(Probe._scanDebounce);
      Probe._scanDebounce = setTimeout(() => scanSignals('post-click'), 250);
    }, true);
  }

  function hookNavigation() {
    if (Probe.navTimer) clearInterval(Probe.navTimer);
    Probe.navTimer = setInterval(() => {
      if (!Probe.on) return;
      if (location.href !== Probe.lastUrl) {
        pushEvent('nav', { from: Probe.lastUrl, to: location.href });
        Probe.lastUrl = location.href;
        setTimeout(() => scanSignals('nav'), 400);
      }
    }, 250);
  }

  function hookFetch() {
    if (Probe.fetchHooked || !window.fetch) return;
    Probe.fetchHooked = true;
    const originalFetch = window.fetch;
    window.fetch = async function (input, init) {
      const url = safeUrl(typeof input === 'string' ? input : (input && input.url) || '');
      const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
      if (!isAllowedRequest(url)) return originalFetch.apply(this, arguments);
      const id = makeId();
      const started = performance.now();
      pushEvent('net:req', {
        id,
        api: 'fetch',
        method,
        url: compactUrl(url),
        body: shortBody(init && init.body),
        page: Probe.pageUrlAtStart,
        filtersAtRequest: currentFilterSnapshot()
      });
      try {
        const response = await originalFetch.apply(this, arguments);
        pushEvent('net:res', {
          id,
          api: 'fetch',
          method,
          url: compactUrl(url),
          status: response.status,
          ms: Math.round(performance.now() - started)
        });
        return response;
      } catch (err) {
        pushEvent('net:res', {
          id,
          api: 'fetch',
          method,
          url: compactUrl(url),
          status: 'ERR',
          ms: Math.round(performance.now() - started),
          err: safeText(err && err.message, 120)
        });
        throw err;
      }
    };
  }

  function hookXHR() {
    if (Probe.xhrHooked || !window.XMLHttpRequest) return;
    Probe.xhrHooked = true;
    const open = XMLHttpRequest.prototype.open;
    const send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url) {
      this.__probe = { method: String(method || 'GET').toUpperCase(), url: safeUrl(url) };
      return open.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function (body) {
      const meta = this.__probe || { method: 'GET', url: '' };
      if (!isAllowedRequest(meta.url)) return send.apply(this, arguments);
      const id = makeId();
      const started = performance.now();
      pushEvent('net:req', {
        id,
        api: 'xhr',
        method: meta.method,
        url: compactUrl(meta.url),
        body: shortBody(body),
        page: Probe.pageUrlAtStart,
        filtersAtRequest: currentFilterSnapshot()
      });
      this.addEventListener('loadend', () => {
        pushEvent('net:res', {
          id,
          api: 'xhr',
          method: meta.method,
          url: compactUrl(meta.url),
          status: this.status,
          ms: Math.round(performance.now() - started)
        });
      });
      return send.apply(this, arguments);
    };
  }

  function copyText(text) {
    if (typeof GM_setClipboard === 'function') {
      GM_setClipboard(text, 'text');
      return Promise.resolve();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        ta.remove();
        resolve();
      } catch (e) {
        ta.remove();
        reject(e);
      }
    });
  }

  function downloadJson(text, filename) {
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function buildResult() {
    return {
      meta: {
        probe: 'PJe Probe',
        version: '1.0.0',
        startedFrom: Probe.pageUrlAtStart,
        endedAt: location.href,
        duration: nowTs(),
        clicks: Probe.clicks.length,
        signals: Probe.signals.length,
        mutations: Probe.mutations.length,
        netReqs: Probe.network.filter(e => e.type === 'net:req').length,
        netRes: Probe.network.filter(e => e.type === 'net:res').length,
        ts: new Date().toISOString()
      },
      clicks: Probe.clicks,
      signals: Probe.signals,
      mutations: Probe.mutations,
      network: Probe.network,
      timeline: Probe.timeline
    };
  }

  function summarizeEndpoints() {
    const reqs = Probe.network.filter(e => e.type === 'net:req');
    const grouped = new Map();
    for (const req of reqs) {
      const key = `${req.method} ${req.url}`;
      if (!grouped.has(key)) grouped.set(key, { count: 0, filters: [], bodies: [] });
      const row = grouped.get(key);
      row.count += 1;
      if (req.filtersAtRequest) row.filters.push(req.filtersAtRequest);
      if (req.body) row.bodies.push(req.body);
    }
    return Array.from(grouped.entries()).map(([k, v]) => ({ endpoint: k, count: v.count, sampleFilters: v.filters[0] || {}, sampleBody: v.bodies[0] || '' }));
  }

  function startProbe() {
    Probe.on = true;
    Probe.t0 = Date.now();
    Probe.runId = makeId();
    Probe.pageUrlAtStart = location.href;
    Probe.lastUrl = location.href;
    Probe.clicks = [];
    Probe.signals = [];
    Probe.mutations = [];
    Probe.network = [];
    Probe.timeline = [];
    Probe.attrThrottle = Object.create(null);
    Probe.ui.log.textContent = '';
    Probe.ui.status.textContent = 'Gravando';
    Probe.ui.status.style.color = '#ff7a7a';
    Probe.ui.button.textContent = 'STOP Probe';
    Probe.ui.button.style.background = '#a12626';
    startObserver();
    hookFetch();
    hookXHR();
    scanSignals('initial');
  }

  function stopProbe() {
    Probe.on = false;
    if (Probe.observer) {
      Probe.observer.disconnect();
      Probe.observer = null;
    }
    scanSignals('final');
    const result = buildResult();
    const json = JSON.stringify(result, null, 2);
    const summary = summarizeEndpoints();
    console.group('PJe Probe');
    console.log('Resumo de endpoints', summary);
    console.log(result);
    console.groupEnd();
    copyText(json).then(() => {
      Probe.ui.status.textContent = `Copiado (${json.length}b)`;
      Probe.ui.status.style.color = '#92f2b3';
    }).catch(() => {
      downloadJson(json, `probe_${Date.now()}.json`);
      Probe.ui.status.textContent = 'Baixado';
      Probe.ui.status.style.color = '#f5d26a';
    });
    Probe.ui.button.textContent = 'Probe';
    Probe.ui.button.style.background = '#1565c0';
  }

  function mountUi() {
    const root = document.createElement('div');
    root.id = 'pje-probe-root';
    root.innerHTML = `
      <div id="pje-probe-box">
        <div id="pje-probe-head">
          <button id="pje-probe-btn" type="button">Probe</button>
          <span id="pje-probe-status">Parado</span>
          <span id="pje-probe-counter">C:0 M:0 S:0 N:0</span>
        </div>
        <pre id="pje-probe-log"></pre>
      </div>
    `;
    const style = document.createElement('style');
    style.textContent = `
      #pje-probe-root{position:fixed;right:16px;bottom:16px;z-index:2147483647;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
      #pje-probe-box{width:360px;max-width:calc(100vw - 24px);background:rgba(16,18,22,.96);color:#eef2f7;border:1px solid rgba(255,255,255,.1);border-radius:14px;box-shadow:0 18px 45px rgba(0,0,0,.45);backdrop-filter:blur(12px);padding:10px}
      #pje-probe-head{display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap}
      #pje-probe-btn{border:0;border-radius:10px;background:#1565c0;color:#fff;font-weight:700;padding:8px 14px;cursor:pointer}
      #pje-probe-status{font-size:12px;color:#aab4c3}
      #pje-probe-counter{margin-left:auto;font-size:11px;color:#91a0b5}
      #pje-probe-log{margin:0;max-height:220px;overflow:auto;white-space:pre-wrap;word-break:break-word;font-size:11px;line-height:1.45;color:#dbe3ee;background:rgba(255,255,255,.03);border-radius:10px;padding:10px}
    `;
    document.documentElement.appendChild(style);
    document.documentElement.appendChild(root);
    Probe.ui = {
      root,
      button: root.querySelector('#pje-probe-btn'),
      status: root.querySelector('#pje-probe-status'),
      counter: root.querySelector('#pje-probe-counter'),
      log: root.querySelector('#pje-probe-log')
    };
    Probe.ui.button.addEventListener('click', () => {
      if (Probe.on) stopProbe();
      else startProbe();
    });
  }

  mountUi();
  hookClicks();
  hookNavigation();
})();
