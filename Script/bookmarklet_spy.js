/**
 * Bookmarklet — API Spy com Overlay (PJePlus)
 *
 * Cola como bookmarklet ou no console do PJe autenticado.
 *
 * Comportamento:
 *   1. Abre um overlay flutuante no canto superior direito
 *   2. Intercepta fetch() + XMLHttpRequest e captura TODAS as chamadas a /api/
 *   3. Mostra contador ao vivo de chamadas capturadas
 *   4. Botao "Parar Spy" → compila relatorio agrupado por endpoint,
 *      exibe no overlay e copia automaticamente pro clipboard
 *   5. Botao "Fechar" → remove overlay e restaura listeners
 *
 * Baseado no mecanismo de spy de Script/Java/pjeapi.js
 */

(function apiSpyOverlay() {
  'use strict';

  if (window.__pjeSpyOverlay) {
    window.__pjeSpyOverlay.close();
    return;
  }

  var API_FILTER = /\/(?:pje-[\w-]+-api|pje-comum-api|pje-gigs-api|sif-financeiro-api)\//;
  var MAX_BODY = 50000;
  var log = [];
  var startTime = Date.now();
  var stopped = false;

  // ── Utilitarios ──────────────────────────────────────────────────────────

  function urlTemplate(url) {
    return url.replace(location.origin, '').replace(/[?#].*$/, '')
      .replace(/\/\d{5,}/g, '/{id}')
      .replace(/\/[a-f0-9]{8,}/gi, '/{hash}');
  }

  function tryJson(text) {
    if (!text || typeof text !== 'string') return null;
    try { return JSON.parse(text); } catch(e) { return text; }
  }

  function truncate(str) {
    if (typeof str !== 'string') return str;
    return str.length > MAX_BODY ? str.slice(0, MAX_BODY) : str;
  }

  function now() { return performance.now() + performance.timeOrigin; }

  function registrar(entry) {
    if (stopped) return;
    log.push(entry);
    updateCounter();
  }

  // ── Interceptacao fetch ──────────────────────────────────────────────────

  var _origFetch = window.fetch;
  window.fetch = function(input, init) {
    var url = typeof input === 'string' ? input : (input.url || String(input));
    if (!API_FILTER.test(url)) return _origFetch.apply(this, arguments);

    var method = (init && init.method || 'GET').toUpperCase();
    var t0 = now();
    var reqBody = init && init.body ? tryJson(typeof init.body === 'string' ? init.body : null) : null;

    var respPromise = _origFetch.apply(this, arguments);

    respPromise.then(function(resp) {
      var clone = resp.clone();
      clone.text().then(function(text) {
        registrar({
          ts: t0, method: method, url: url,
          reqBody: reqBody, status: resp.status,
          resBody: tryJson(truncate(text)),
          duration: Math.round(now() - t0),
          urlTemplate: urlTemplate(url)
        });
      }).catch(function(){});
    }).catch(function(e) {
      registrar({
        ts: t0, method: method, url: url,
        reqBody: reqBody, status: 0, resBody: null,
        duration: Math.round(now() - t0),
        urlTemplate: urlTemplate(url), erro: e.message
      });
    });

    return respPromise;
  };

  // ── Interceptacao XMLHttpRequest ──────────────────────────────────────────

  var _origOpen  = XMLHttpRequest.prototype.open;
  var _origSend  = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url) {
    var args = arguments;
    this.__spy = API_FILTER.test(String(url)) ? { method: method.toUpperCase(), url: String(url), t0: 0 } : null;
    return _origOpen.apply(this, args);
  };

  XMLHttpRequest.prototype.send = function(body) {
    if (!this.__spy) return _origSend.apply(this, arguments);
    var spy = this.__spy;
    spy.t0 = now();
    spy.reqBody = tryJson(typeof body === 'string' ? body : null);

    var self = this;
    this.addEventListener('loadend', function() {
      registrar({
        ts: spy.t0, method: spy.method, url: spy.url,
        reqBody: spy.reqBody, status: self.status,
        resBody: tryJson(truncate(self.responseText)),
        duration: Math.round(now() - spy.t0),
        urlTemplate: urlTemplate(spy.url)
      });
    });
    return _origSend.apply(this, arguments);
  };

  // ── Overlay UI ───────────────────────────────────────────────────────────

  var overlay = document.createElement('div');
  overlay.id = '__pjeSpyOverlay';
  Object.assign(overlay.style, {
    position: 'fixed', top: '10px', right: '10px', zIndex: '2147483647',
    width: '380px', maxHeight: '90vh', background: '#0f1923',
    color: '#cdd6f4', fontFamily: 'monospace', fontSize: '12px',
    borderRadius: '8px', padding: '12px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
    overflow: 'hidden', display: 'flex', flexDirection: 'column',
    border: '1px solid #313244'
  });

  overlay.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
      '<b style="color:#89b4fa;font-size:14px">🔍 PJe API Spy</b>' +
      '<span id="__spyCounter" style="color:#a6e3a1;font-weight:bold">0 chamadas</span>' +
    '</div>' +
    '<div id="__spyTime" style="color:#6c7086;margin-bottom:8px;font-size:10px">escutando...</div>' +
    '<div id="__spyBody" style="flex:1;overflow-y:auto;max-height:60vh;margin-bottom:8px;font-size:11px">' +
      '<div style="color:#6c7086">Interceptando chamadas API...</div>' +
      '<div style="color:#6c7086;margin-top:4px">Navegue pelo PJe — cada chamada /api/ sera capturada</div>' +
    '</div>' +
    '<div style="display:flex;gap:6px">' +
      '<button id="__spyStop" style="flex:1;padding:6px;background:#a6e3a1;color:#1e1e2e;border:0;border-radius:4px;cursor:pointer;font-weight:bold;font-family:monospace">Parar Spy</button>' +
      '<button id="__spyClose" style="padding:6px 12px;background:#f38ba8;color:#1e1e2e;border:0;border-radius:4px;cursor:pointer;font-family:monospace">✕</button>' +
    '</div>';

  document.body.appendChild(overlay);

  function updateCounter() {
    var el = document.getElementById('__spyCounter');
    var timeEl = document.getElementById('__spyTime');
    if (el) el.textContent = log.length + ' chamadas';
    if (timeEl) timeEl.textContent = 'escutando... ' + Math.round((Date.now() - startTime) / 1000) + 's';
  }

  // Live time update
  var timeInterval = setInterval(function() {
    if (stopped) { clearInterval(timeInterval); return; }
    updateCounter();
  }, 1000);

  // ── Compilar relatorio ───────────────────────────────────────────────────

  function compileReport() {
    var byEndpoint = {};
    for (var i = 0; i < log.length; i++) {
      var e = log[i];
      var key = e.method + ' ' + e.urlTemplate;
      if (!byEndpoint[key]) {
        byEndpoint[key] = {
          method: e.method, urlTemplate: e.urlTemplate,
          count: 0, statuses: {}, lastUrl: e.url,
          exampleReq: e.reqBody, exampleRes: null
        };
      }
      byEndpoint[key].count++;
      byEndpoint[key].statuses[e.status] = (byEndpoint[key].statuses[e.status] || 0) + 1;
      byEndpoint[key].lastUrl = e.url;
      if (e.resBody && !byEndpoint[key].exampleRes) byEndpoint[key].exampleRes = e.resBody;
    }

    var list = [];
    for (var k in byEndpoint) { list.push(byEndpoint[k]); }
    list.sort(function(a, b) { return b.count - a.count; });

    // Texto para clipboard
    var lines = ['PJe API Spy — Relatorio', '========================', '',
      'Capturado em: ' + new Date().toISOString(),
      'Total chamadas: ' + log.length,
      'Endpoints unicos: ' + list.length,
      'Duracao: ' + Math.round((Date.now() - startTime) / 1000) + 's', ''
    ];

    for (var i2 = 0; i2 < list.length; i2++) {
      var item = list[i2];
      var statusStr = [];
      for (var s in item.statuses) { statusStr.push(s + 'x' + item.statuses[s]); }
      lines.push(item.count + 'x  ' + item.method + ' ' + item.urlTemplate + '  [' + statusStr.join(', ') + ']');
      lines.push('    URL: ' + item.lastUrl);
      if (item.exampleReq) {
        var reqStr = JSON.stringify(item.exampleReq);
        lines.push('    Req: ' + reqStr.slice(0, 200));
      }
      if (item.exampleRes) {
        var resObj = item.exampleRes;
        if (typeof resObj === 'object') {
          if (Array.isArray(resObj)) {
            lines.push('    Res: Array[' + resObj.length + '] campos: ' + (resObj[0] ? Object.keys(resObj[0]).join(', ') : ''));
          } else {
            var arr = resObj.resultado || resObj.content || resObj.lista;
            if (Array.isArray(arr)) {
              lines.push('    Res: {resultado:[' + arr.length + ']} campos: ' + (arr[0] ? Object.keys(arr[0]).join(', ') : ''));
            } else {
              lines.push('    Res: {' + Object.keys(resObj).join(', ') + '}');
            }
          }
        }
      }
      lines.push('');
    }

    return { list: list, lines: lines, text: lines.join('\n') };
  }

  // ── Clipboard robusto (textarea + execCommand, nao depende de user gesture async) ──

  function copyText(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch(e) {}
    document.body.removeChild(ta);
  }

  // ── Stop Spy ─────────────────────────────────────────────────────────────

  function stopSpy() {
    if (stopped) return;
    stopped = true;
    clearInterval(timeInterval);

    var report = compileReport();

    // Copiar para clipboard ANTES de atualizar DOM (preserva user gesture)
    copyText(report.text);

    // Atualizar overlay com o relatorio
    var body = document.getElementById('__spyBody');
    if (body) {
      var html = '<div style="color:#a6e3a1;font-weight:bold;margin-bottom:8px">✅ Spy concluido — ' + log.length + ' chamadas em ' + report.list.length + ' endpoints</div>';
      html += '<div style="color:#f9e2af;margin-bottom:4px">📋 Copiado para clipboard!</div>';
      for (var i = 0; i < report.list.length; i++) {
        var item = report.list[i];
        var bg = i % 2 === 0 ? '#181825' : '#1e1e2e';
        html += '<div style="background:' + bg + ';padding:4px 6px;margin:2px 0;border-radius:3px">';
        html += '<b style="color:#89b4fa">' + item.count + 'x</b> ';
        html += '<span style="color:#cba6f7">' + item.method + '</span> ';
        html += '<span style="color:#a6e3a1">' + item.urlTemplate + '</span>';
        html += '</div>';
      }
      body.innerHTML = html;
    }

    // Atualizar botoes
    var stopBtn = document.getElementById('__spyStop');
    if (stopBtn) {
      stopBtn.textContent = 'Copiar novamente';
      stopBtn.style.background = '#89b4fa';
      stopBtn.onclick = function() {
        copyText(report.text);
        stopBtn.textContent = 'Copiado! ✓';
        setTimeout(function() { stopBtn.textContent = 'Copiar novamente'; }, 1500);
      };
    }

    // Atualizar contador
    var counter = document.getElementById('__spyCounter');
    if (counter) counter.textContent = log.length + ' chamadas';

    var timeEl = document.getElementById('__spyTime');
    if (timeEl) timeEl.textContent = 'capturado em ' + Math.round((Date.now() - startTime) / 1000) + 's';
    });

    // Restaurar fetch/XHR originais
    window.fetch = _origFetch;
    XMLHttpRequest.prototype.open = _origOpen;
    XMLHttpRequest.prototype.send = _origSend;

    console.log('[SPY] Relatorio com ' + log.length + ' chamadas em ' + report.list.length + ' endpoints copiado para clipboard');
    console.table(report.list.map(function(i) { return { count: i.count, method: i.method, endpoint: i.urlTemplate }; }));
  }

  // ── Eventos dos botoes ──────────────────────────────────────────────────

  document.getElementById('__spyStop').addEventListener('click', stopSpy);

  // ── Cleanup ──────────────────────────────────────────────────────────────

  function closeOverlay() {
    clearInterval(timeInterval);
    if (!stopped) {
      window.fetch = _origFetch;
      XMLHttpRequest.prototype.open = _origOpen;
      XMLHttpRequest.prototype.send = _origSend;
    }
    if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    window.__pjeSpyOverlay = null;
  }

  document.getElementById('__spyClose').addEventListener('click', closeOverlay);

  window.__pjeSpyOverlay = {
    close: closeOverlay,
    stop: stopSpy,
    log: log
  };

  console.log('[SPY] API Spy ativo. Overlay no canto superior direito. ' + log.length + ' chamadas capturadas.');
})();
