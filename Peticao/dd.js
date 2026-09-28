// ==UserScript==
// @name         PJe PET Escaninho 100
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Força o escaninho de petições do PJe TRT2 a requisitar 100 linhas por página.
// @author       You
// @match        https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
  'use strict';

  if (window.top !== window.self) return;

  var TARGET_SIZE = 100;
  var MARKERS = [
    '/pje-comum-api/api/escaninhos/peticoesjuntadas',
    '/pjekz/escaninho/peticoes-juntadas',
    'peticoesjuntadas'
  ];

  function shouldRewrite(rawUrl) {
    if (!rawUrl) return false;

    try {
      var url = new URL(rawUrl, window.location.origin);
      if (url.origin !== window.location.origin) return false;

      var href = url.href.toLowerCase();
      return MARKERS.some(function (marker) {
        return href.indexOf(marker.toLowerCase()) !== -1;
      });
    } catch (error) {
      return false;
    }
  }

  function rewriteUrl(rawUrl) {
    if (!shouldRewrite(rawUrl)) return rawUrl;

    try {
      var url = new URL(rawUrl, window.location.origin);
      var params = url.searchParams;

      params.set('tamanhoPagina', String(TARGET_SIZE));
      if (!params.has('pagina')) params.set('pagina', '1');
      if (!params.has('ordenacaoCrescente')) params.set('ordenacaoCrescente', 'true');
      return url.toString();
    } catch (error) {
      return rawUrl;
    }

    return rawUrl;
  }

  function patchFetch() {
    if (typeof window.fetch !== 'function') return;

    var originalFetch = window.fetch.bind(window);

    window.fetch = function (input, init) {
      try {
        if (typeof input === 'string' || input instanceof URL) {
          input = rewriteUrl(String(input));
        } else if (input && typeof input.url === 'string') {
          var rewritten = rewriteUrl(input.url);
          if (rewritten !== input.url && typeof Request !== 'undefined') {
            input = new Request(rewritten, input);
          }
        }
      } catch (error) {
        // Ignora falhas de rewrite e preserva a requisição original.
      }

      return originalFetch(input, init);
    };
  }

  function patchXHR() {
    if (!window.XMLHttpRequest || !window.XMLHttpRequest.prototype) return;

    var originalOpen = window.XMLHttpRequest.prototype.open;
    if (typeof originalOpen !== 'function') return;

    window.XMLHttpRequest.prototype.open = function (method, url) {
      try {
        url = rewriteUrl(String(url));
      } catch (error) {
        // Mantém a URL original se o rewrite falhar.
      }

      return originalOpen.apply(this, [method, url].concat([].slice.call(arguments, 2)));
    };
  }

  function isPaginatorSelect(node) {
    if (!node) return false;

    var text = '';
    try {
      text = node.textContent || '';
    } catch (error) {
      text = '';
    }

    return /Linhas por página/i.test(text) || /mat-select-value/i.test(node.className || '') || /50/.test(text);
  }

  function forceVisiblePageSize() {
    var selectors = Array.prototype.slice.call(document.querySelectorAll('pje-paginador mat-select, mat-form-field.form-select mat-select, mat-select[role="combobox"]'));
    var paginator = selectors.find(function (node) {
      return isPaginatorSelect(node) && (node.textContent || '').indexOf('50') !== -1;
    });

    if (!paginator) return;

    var label = paginator.querySelector('.mat-select-value-text .mat-select-min-line') || paginator.querySelector('.mat-select-value-text') || paginator.querySelector('.mat-select-min-line');
    if (label && label.textContent.trim() !== String(TARGET_SIZE)) {
      label.textContent = String(TARGET_SIZE);
    }
  }

  patchFetch();
  patchXHR();

    // Botão "Mostrar 100" no canto superior direito
    function addMostrar100Button() {
      if (document.getElementById('btn-mostrar-100')) return;
      var btn = document.createElement('button');
      btn.id = 'btn-mostrar-100';
      btn.textContent = 'Mostrar 100';
      btn.style.position = 'fixed';
      btn.style.top = '10px';
      btn.style.right = '20px';
      btn.style.zIndex = 9999;
      btn.style.background = '#1976d2';
      btn.style.color = '#fff';
      btn.style.border = 'none';
      btn.style.padding = '8px 16px';
      btn.style.borderRadius = '4px';
      btn.style.cursor = 'pointer';
      btn.onclick = function() {
        try {
          forceVisiblePageSize();
          // Tenta disparar mudança de página para forçar reload
          var url = window.location.href;
          if (url.indexOf('tamanhoPagina=100') === -1) {
            var newUrl = rewriteUrl(url);
            if (newUrl !== url) window.location.href = newUrl;
          } else {
            window.location.reload();
          }
        } catch (e) {}
      };
      document.body.appendChild(btn);
    }

    // Adiciona botão após DOM pronto
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', addMostrar100Button, { once: true });
    } else {
      addMostrar100Button();
    }

  var tick = 0;
  var timer = window.setInterval(function () {
    forceVisiblePageSize();
    tick += 1;
    if (tick > 40) window.clearInterval(timer);
  }, 500);

  document.addEventListener('DOMContentLoaded', function () {
    forceVisiblePageSize();
  }, { once: true });
})();