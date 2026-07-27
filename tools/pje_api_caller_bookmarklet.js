/**
 * pje_api_caller_bookmarklet.js
 *
 * Bookmarklet generico: abre um painel flutuante que dispara uma
 * chamada fetch() na aba atual (usando os cookies/sessao ja logados
 * dessa aba) contra QUALQUER endpoint relativo ou absoluto, e mostra
 * a resposta bruta (JSON formatado se der pra parsear, senao texto cru).
 *
 * Nao e especifico de nenhum sistema (PJe, eCarta, etc.) — serve pra
 * testar "esse endpoint responde algo direto, sem eu precisar clicar
 * pela tela?" em qualquer lugar onde voce ja esta autenticado.
 *
 * Limitacao conhecida: paginas JSF classicas (eCarta, etc.) frequentemente
 * exigem javax.faces.ViewState e outros campos ocultos do formulario para
 * um POST funcionar — um POST "cru" sem esses campos pode retornar erro/
 * pagina de login/estado invalido. Funciona bem, sem ressalvas, contra
 * endpoints REST/JSON stateless (o padrao da maioria das APIs do PJe em
 * Fix/variaveis.py, ex: /pje-comum-api/api/...).
 *
 * Versao minificada (para colar como URL de favorito) em
 * tools/pje_api_caller_bookmarklet.min.txt.
 */
(function pjeApiCaller() {
  'use strict';

  if (window.__pjeApiCaller) {
    window.__pjeApiCaller.toggle();
    return;
  }

  var BG = '#181825', SURFACE = '#11111b', TEXT = '#cdd6f4', BORDER = '#313244';
  var ACCENT = '#89b4fa', OK = '#a6e3a1', ERR = '#f38ba8', MUTED = '#6c7086';

  var panel = document.createElement('div');
  panel.setAttribute('data-pje-probe-ui', '1');
  panel.style.cssText = 'position:fixed;top:16px;right:16px;z-index:2147483647;width:420px;max-height:82vh;' +
    'background:' + BG + ';color:' + TEXT + ';border:1px solid ' + BORDER + ';border-radius:10px;' +
    'padding:14px;font:12px ui-monospace,Consolas,monospace;box-shadow:0 8px 30px rgba(0,0,0,.5);' +
    'display:flex;flex-direction:column;gap:8px;';

  panel.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;">' +
      '<b style="color:' + ACCENT + ';">🔧 API Caller — sessão atual</b>' +
      '<button id="__apiClose" style="background:' + ERR + ';color:' + SURFACE + ';border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-weight:700;">✕</button>' +
    '</div>' +
    '<div style="display:flex;gap:6px;">' +
      '<select id="__apiMethod" style="padding:6px;background:' + SURFACE + ';color:' + TEXT + ';border:1px solid ' + BORDER + ';border-radius:4px;">' +
        '<option>GET</option><option>POST</option>' +
      '</select>' +
      '<input id="__apiUrl" style="flex:1;padding:6px;background:' + SURFACE + ';color:' + TEXT + ';border:1px solid ' + BORDER + ';border-radius:4px;">' +
    '</div>' +
    '<textarea id="__apiBody" placeholder="corpo — opcional, so p/ POST (JSON ou form-urlencoded)" style="padding:6px;background:' + SURFACE + ';color:' + TEXT + ';border:1px solid ' + BORDER + ';border-radius:4px;min-height:44px;font-family:inherit;"></textarea>' +
    '<div style="display:flex;gap:6px;">' +
      '<button id="__apiSend" style="flex:1;padding:7px;background:' + ACCENT + ';color:' + SURFACE + ';border:none;border-radius:4px;font-weight:700;cursor:pointer;">Enviar</button>' +
      '<button id="__apiCopy" style="padding:7px 10px;background:' + BORDER + ';color:' + TEXT + ';border:none;border-radius:4px;cursor:pointer;">copiar resposta</button>' +
    '</div>' +
    '<div id="__apiStatus" style="color:' + MUTED + ';"></div>' +
    '<pre id="__apiResult" style="margin:0;background:' + SURFACE + ';border:1px solid ' + BORDER + ';border-radius:6px;padding:8px;overflow:auto;max-height:50vh;white-space:pre-wrap;word-break:break-all;"></pre>';

  document.body.appendChild(panel);

  var urlInput = panel.querySelector('#__apiUrl');
  urlInput.value = location.pathname + location.search;

  var lastResult = '';

  function copyText(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  panel.querySelector('#__apiSend').addEventListener('click', function () {
    var method = panel.querySelector('#__apiMethod').value;
    var url = urlInput.value;
    var body = panel.querySelector('#__apiBody').value;
    var statusEl = panel.querySelector('#__apiStatus');
    var resultEl = panel.querySelector('#__apiResult');

    statusEl.textContent = 'enviando...';
    statusEl.style.color = MUTED;
    resultEl.textContent = '';

    var opts = { method: method, credentials: 'include', headers: {} };
    if (method === 'POST' && body) {
      opts.body = body;
      try {
        JSON.parse(body);
        opts.headers['Content-Type'] = 'application/json';
      } catch (e) {
        opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
      }
    }

    var t0 = Date.now();
    fetch(url, opts).then(function (resp) {
      return resp.text().then(function (text) {
        var dur = Date.now() - t0;
        statusEl.textContent = resp.status + ' ' + resp.statusText + ' — ' + dur + 'ms — ' + text.length + ' chars — content-type: ' + (resp.headers.get('content-type') || '?');
        statusEl.style.color = resp.ok ? OK : ERR;
        try {
          lastResult = JSON.stringify(JSON.parse(text), null, 2);
        } catch (e) {
          lastResult = text;
        }
        resultEl.textContent = lastResult.slice(0, 20000);
      });
    }).catch(function (e) {
      statusEl.textContent = 'erro de rede: ' + e.message;
      statusEl.style.color = ERR;
    });
  });

  panel.querySelector('#__apiCopy').addEventListener('click', function () {
    copyText(lastResult);
    var btn = panel.querySelector('#__apiCopy');
    var orig = btn.textContent;
    btn.textContent = 'copiado ✓';
    setTimeout(function () { btn.textContent = orig; }, 1200);
  });

  panel.querySelector('#__apiClose').addEventListener('click', function () {
    panel.remove();
    window.__pjeApiCaller = null;
  });

  window.__pjeApiCaller = {
    toggle: function () {
      panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    },
  };
})();
