'use strict';

// ── PJeT — core/logger.js ─────────────────────────────────────────
// Sistema de logging estruturado, visual e diagnóstico do PJeT.
// Permite rastrear ciclo de vida, chamadas de API, DOM e erros
// com precisão de milissegundos e cores no DevTools Console.
// ─────────────────────────────────────────────────────────────────

(function () {
  // Polyfill universal de WebExtension API (Firefox / Chrome)
  if (typeof globalThis.browser === 'undefined' && typeof globalThis.chrome !== 'undefined') {
    globalThis.browser = globalThis.chrome;
  }

  const BADGE_STYLES = {
    BOOT:    'background:#6f42c1;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    LOADER:  'background:#4a148c;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    ROUTER:  'background:#0d47a1;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    STATE:   'background:#00695c;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    DOM:     'background:#00838f;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    API:     'background:#e65100;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    CHECK:   'background:#2e7d32;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    EDITAL:  'background:#1b5e20;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    PGTO:    'background:#880e4f;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    PAINEL:  'background:#37474f;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    WARN:    'background:#f57f17;color:#000;font-weight:bold;padding:2px 6px;border-radius:3px;',
    ERROR:   'background:#b71c1c;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    SUCCESS: 'background:#1b5e20;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    UNCAUGHT:'background:#d50000;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;',
    PROMISE: 'background:#ff1744;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;'
  };

  const TXT_STYLE = 'color:inherit;font-weight:normal;';
  const TIME_STYLE = 'color:#888;font-size:10px;margin-right:4px;';

  function getTime() {
    const d = new Date();
    return d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0');
  }

  function getProcessoId() {
    try {
      const m = window.location.pathname.match(/\/processo\/(\d+)/);
      return m ? m[1] : null;
    } catch (_) {
      return null;
    }
  }

  const PJeLogger = {
    enabled: true,

    _log(channel, level, message, ...args) {
      if (!this.enabled && level !== 'error') return;
      const tag = channel.toUpperCase();
      const style = BADGE_STYLES[tag] || BADGE_STYLES.LOADER;
      const proc = getProcessoId();
      const procLabel = proc ? `[Proc:${proc}] ` : '';
      const prefix = `%c${getTime()}%c[PJeT::${tag}]%c ${procLabel}${message}`;

      const fn = (console[level] || console.log).bind(console);
      if (args.length > 0) {
        fn(prefix, TIME_STYLE, style, TXT_STYLE, ...args);
      } else {
        fn(prefix, TIME_STYLE, style, TXT_STYLE);
      }
    },

    boot(msg, ...args)    { this._log('BOOT', 'info', msg, ...args); },
    loader(msg, ...args)  { this._log('LOADER', 'info', msg, ...args); },
    router(msg, ...args)  { this._log('ROUTER', 'info', msg, ...args); },
    state(msg, ...args)   { this._log('STATE', 'info', msg, ...args); },
    dom(msg, ...args)     { this._log('DOM', 'info', msg, ...args); },
    api(msg, ...args)     { this._log('API', 'info', msg, ...args); },
    check(msg, ...args)   { this._log('CHECK', 'info', msg, ...args); },
    edital(msg, ...args)  { this._log('EDITAL', 'info', msg, ...args); },
    pgto(msg, ...args)    { this._log('PGTO', 'info', msg, ...args); },
    painel(msg, ...args)  { this._log('PAINEL', 'info', msg, ...args); },
    warn(channel, msg, ...args) { this._log(channel, 'warn', msg, ...args); },
    success(channel, msg, ...args) { this._log(channel, 'info', `✅ ${msg}`, ...args); },

    error(channel, msg, err, extra = {}) {
      const tag = channel.toUpperCase();
      const style = BADGE_STYLES.ERROR;
      const proc = getProcessoId();
      console.group(`%c${getTime()}%c[PJeT::${tag} ❌ ERRO]%c ${msg}`, TIME_STYLE, style, 'color:#d32f2f;font-weight:bold;');
      console.error('Mensagem:', err?.message || err || 'Erro desconhecido');
      if (err?.stack) console.error('Stack trace:\n' + err.stack);
      console.info('Contexto diagnóstico:', {
        url: window.location.href,
        processoId: proc,
        pjeStateIniciado: !!window.PJeState?._iniciado,
        angularPronto: !!(document.querySelector('pje-cabecalho') || document.querySelector('li.tl-item-container')),
        cookiesPresentes: document.cookie ? document.cookie.split(';').map(c => c.split('=')[0].trim()) : [],
        ...extra
      });
      console.groupEnd();

      if (typeof window.showToast === 'function') {
        window.showToast(`[PJeT] Erro em ${tag}: ${err?.message || msg}`, '#c62828', 5000);
      }
    },

    group(label, collapsed = true) {
      if (collapsed) console.groupCollapsed(`%c[PJeT]%c ${label}`, 'background:#333;color:#fff;font-weight:bold;padding:1px 4px;border-radius:2px;', 'font-weight:bold;');
      else console.group(`%c[PJeT]%c ${label}`, 'background:#333;color:#fff;font-weight:bold;padding:1px 4px;border-radius:2px;', 'font-weight:bold;');
    },

    groupEnd() {
      console.groupEnd();
    }
  };

  // Status Diagnóstico global - digitável no console F12
  window.pjetStatus = function () {
    const proc = getProcessoId();
    const timelineDocs = window.PJeState?.lista?.docs;
    const info = {
      'Versão': '1.0.0 (MV3)',
      'URL Atual': window.location.href,
      'Processo ID': proc || '(não detectado)',
      'Rota Identificada': /\/processo\/\d+\/detalhe/.test(window.location.href) ? 'Detalhe do Processo'
        : window.location.href.includes('/comunicacoesprocessuais/minutas') ? 'Minutas (InfoJud)'
        : window.location.href.includes('/obrigacao-pagar/') ? 'Obrigação de Pagar (Débito)'
        : window.location.href.includes('/aud/') ? 'Audiência (PJeAud)'
        : 'Outra / Desconhecida',
      'PJeState Inicializado': !!window.PJeState?._iniciado,
      'Painel Flutuante no DOM': !!document.getElementById('pjetools-painel'),
      'Cache Timeline': timelineDocs ? `${timelineDocs.length} docs (lido há ${Math.round((Date.now() - (window.PJeState.lista.readAt || 0))/1000)}s)` : 'Vazio / Não carregado',
      'Angular / DOM Pronto': !!(document.querySelector('pje-cabecalho') || document.querySelector('li.tl-item-container')),
      'XSRF Token Presente': !!(document.cookie.match(/xsrf-token=/i)),
      'Global Error Handler': !!window.__pjetErrorHandlerAtivo
    };
    console.table(info);
    return info;
  };

  window.PJeDiagnostico = window.pjetStatus;
  window.PJeLogger = PJeLogger;

  // Interceptador global de erros não capturados para scripts da extensão
  if (!window.__pjetErrorHandlerAtivo) {
    window.__pjetErrorHandlerAtivo = true;
    window.addEventListener('error', function (e) {
      if (e.filename && (e.filename.includes('pjet') || e.filename.includes('moz-extension') || e.filename.includes('chrome-extension'))) {
        PJeLogger.error('UNCAUGHT', `Erro não tratado em ${e.filename}:${e.lineno}:${e.colno}`, e.error || e.message);
      }
    });
    window.addEventListener('unhandledrejection', function (e) {
      const reason = e.reason;
      if (reason && reason.stack && (reason.stack.includes('pjet') || reason.stack.includes('moz-extension') || reason.stack.includes('chrome-extension'))) {
        PJeLogger.error('PROMISE', 'Promise rejeitada sem tratamento na extensão', reason);
      }
    });
  }

  PJeLogger.boot('Módulo de logger inicializado. Digite pjetStatus() a qualquer momento para ver o status.');
})();
