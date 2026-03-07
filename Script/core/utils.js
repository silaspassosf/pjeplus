(function () {
    'use strict';

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
        } catch (e) { }
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

    // Exports
    window.sleep = sleep;
    window.waitElement = waitElement;
    window.waitElementVisible = waitElementVisible;
    window.formatMoney = formatMoney;
    window.parseMoney = parseMoney;
    window.normalizeText = normalizeText;
    window.showToast = showToast;
    window.playBeep = playBeep;
    window.addStyles = addStyles;
    window.hoverAndDispatch = hoverAndDispatch;
    window.monitorarSPA = monitorarSPA;
    window.antiDuplicacao = antiDuplicacao;
})();