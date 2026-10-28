// ==UserScript==
// @name         PJe Probe
// @namespace    pjeplus.probe
// @version      1.2
// @description  Botao PROBE: grava seletores (ranking de estabilidade) e endpoints de API (fetch+XHR) da tela. Sobrevive a navegacao/login MESMO ATRAVESSANDO ORIGENS DIFERENTES (GM_setValue nao e por origem). Ao parar, copia relatorio para a area de transferencia.
// @match        *://*.jus.br/*
// @run-at       document-end
// @noframes
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// ==/UserScript==
/**
 * v1.2: alem de seletores e endpoints, grava os HOVERS da barra maisPJe.
 *
 *   Fica restrito a #maisPJe_bt_detalhes_base: so entra o hover cujo elemento
 *   esta dentro dessa barra. Hover em qualquer outra coisa da pagina e
 *   ignorado — o objetivo e mapear "icone -> botoes que o menu abre".
 *
 *   Depois de cada hover, espera 700ms (a extensao monta os botoes ~500ms
 *   depois, ver addBotaoTelaAnexar) e le o menu maisPjeContainerAA, gravando
 *   id, name, texto e visibilidade de cada botao. O relatorio sai no formato
 *   que o motor usa:  ICONE #maisPJe_bt_detalhes_anexarDocumentos
 *                     name="SISCON"  texto="SISCON"
 *
 * v1.1: troca sessionStorage (isolado por origem) por GM_setValue/GM_getValue
 * (compartilhado entre TODAS as origens que o script casa via @match) — resolve
 * o caso em que o fluxo de login/navegacao atravessa dominios diferentes dentro
 * de .jus.br e o estado da gravacao se perdia na troca de origem.
 *
 * Usa unsafeWindow.fetch / unsafeWindow.XMLHttpRequest para garantir que o
 * patch de rede afeta o fetch/XHR REAL da pagina, mesmo que o Tampermonkey
 * rode este script em sandbox (quando ha @grant alem de "none").
 *
 * Limitacao conhecida (nao tem como contornar via JS de pagina): um POST-back
 * classico de formulario HTML (navegacao nativa do browser, sem passar por
 * fetch/XHR) NAO aparece aqui. Para captura completa de TODA chamada de rede
 * em uma sessao inteira, incluindo essas, use DevTools -> Network -> "Preserve
 * Log" antes de navegar (exportavel como HAR).
 */
(function pjeProbe() {
  'use strict';

  if (unsafeWindow.__pjeProbe) return;

  var STORAGE_KEY = '__pjeProbeState__';

  var state = {
    recording: false,
    startTime: 0,
    selectors: [],
    selectorIndex: {},
    endpoints: {},
    hovers: {},
    origFetch: null,
    origOpen: null,
    origSend: null,
  };
  unsafeWindow.__pjeProbe = state;

  // ── Persistencia entre paginas E entre origens (GM_setValue) ───────────

  function salvarEstado() {
    try {
      GM_setValue(STORAGE_KEY, JSON.stringify({
        recording: state.recording,
        startTime: state.startTime,
        selectors: state.selectors,
        selectorIndex: state.selectorIndex,
        endpoints: state.endpoints,
        hovers: state.hovers,
      }));
    } catch (e) {}
  }

  function carregarEstadoSalvo() {
    try {
      var raw = GM_getValue(STORAGE_KEY, null);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function limparEstadoSalvo() {
    try { GM_deleteValue(STORAGE_KEY); } catch (e) {}
  }

  // ── Seletores (mesmo criterio de tools/grab_recorder.js) ──────────────

  function closestBounded(el, selector, maxLevels) {
    var node = el, level = 0;
    while (node && node.nodeType === 1 && level <= maxLevels) {
      if (node.matches && node.matches(selector)) return node;
      node = node.parentElement;
      level++;
    }
    return null;
  }

  // Checkbox de documento na timeline: o id real do input (mat-checkbox-N-input)
  // e um contador sequencial global do Angular Material (filtrado pelo regex
  // ^(ng-|mat-|cdk-) no bloco "id" abaixo, ja que muda a cada reload), mas o
  // item pai tem id estavel com prefixo "doc_" e um
  // mat-label.sr-only com a descricao do documento — usa essa combinacao como
  // candidato de alta prioridade antes do fallback generico de classes.
  function candidatoTimelinePje(el) {
    var matCheckbox = closestBounded(el, 'mat-checkbox', 4);
    var itemContainer = el.closest('[id^="doc_"], .tl-item-container, .tl-item-desc');
    if (!matCheckbox && !itemContainer) return null;

    var scope = matCheckbox || itemContainer;
    var idEl = closestBounded(scope, '[id^="doc_"]', 12) || itemContainer;
    if (!idEl || !idEl.id) return null;

    var labelEl = idEl.querySelector('mat-label.sr-only, .sr-only');
    var texto = labelEl ? (labelEl.innerText || labelEl.textContent || '') : '';
    if (!texto.trim()) {
      var linkEl = idEl.querySelector('a.tl-documento, .tl-documento');
      if (linkEl) texto = linkEl.innerText || linkEl.textContent || '';
    }
    texto = texto.trim().replace(/\s+/g, ' ').slice(0, 80);

    return {
      selector: '#' + CSS.escape(idEl.id) + (matCheckbox ? ' (mat-checkbox)' : ''),
      stability: 'high', type: 'pje-timeline-doc', text: texto,
    };
  }

  function candidatos(el) {
    var tag = el.tagName.toLowerCase();
    var list = [];

    if (el.id && !/^(ng-|mat-|cdk-)/.test(el.id) && !/^\d/.test(el.id) && el.id.length < 50) {
      list.push({ selector: '#' + CSS.escape(el.id), stability: 'high', type: 'id' });
    }

    for (var i = 0; i < el.attributes.length; i++) {
      var attr = el.attributes[i];
      if (attr.name.indexOf('data-') === 0 && attr.value && attr.value.length < 80) {
        list.push({ selector: '[' + attr.name + '="' + attr.value + '"]', stability: 'high', type: 'data-attr' });
        break;
      }
    }

    var pjeTimeline = candidatoTimelinePje(el);
    if (pjeTimeline) list.push(pjeTimeline);

    var aria = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
    if (aria && aria.length < 80) {
      list.push({ selector: tag + '[aria-label="' + aria + '"]', stability: 'medium', type: 'aria' });
    }

    var ngName = el.getAttribute('ng-reflect-name');
    if (ngName) {
      list.push({ selector: '[ng-reflect-name="' + ngName + '"]', stability: 'medium', type: 'ng-reflect-name' });
    }

    var nameAttr = el.getAttribute('name');
    if (nameAttr) {
      var typeAttr = el.getAttribute('type');
      var base = typeAttr ? tag + '[name="' + nameAttr + '"][type="' + typeAttr + '"]' : tag + '[name="' + nameAttr + '"]';
      list.push({ selector: base, stability: 'medium', type: 'name-attr' });
    }

    var role = el.getAttribute('role');
    var matClasses = Array.prototype.filter.call(el.classList, function (c) { return c.indexOf('mat-') === 0 && !/\d{4,}/.test(c); });
    if (role && matClasses.length > 0) {
      list.push({ selector: tag + '[role="' + role + '"].' + matClasses[0], stability: 'medium', type: 'role-mat' });
    }

    var stableClasses = Array.prototype.filter.call(el.classList, function (c) {
      return !/^(ng-|_ng|cdk-|mat-ripple|mat-focus|ng-tns|ng-star)/.test(c) && !/\d{5,}/.test(c) && c.length > 2;
    });
    if (stableClasses.length > 0) {
      list.push({ selector: tag + '.' + stableClasses.slice(0, 3).join('.'), stability: 'low', type: 'tag-class' });
    }

    var txt = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    if (txt && txt.length >= 3 && txt.length <= 40 && !/\d{5,}/.test(txt)) {
      list.push({ selector: '//' + tag + '[normalize-space(.)="' + txt + '"]', stability: 'low', type: 'xpath-text' });
    }

    if (!list.length) list.push({ selector: tag, stability: 'low', type: 'tag' });
    return list;
  }

  function labelFor(el) {
    return (el.innerText || el.value || el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  }

  function registrarSeletor(el) {
    var best = candidatos(el)[0];
    var key = best.selector;
    if (state.selectorIndex.hasOwnProperty(key)) {
      state.selectors[state.selectorIndex[key]].count++;
    } else {
      state.selectorIndex[key] = state.selectors.length;
      state.selectors.push({
        selector: best.selector, stability: best.stability, type: best.type,
        tag: el.tagName.toLowerCase(), text: best.text || labelFor(el), count: 1,
      });
    }
    salvarEstado();
  }

  function onInteraction(ev) {
    try {
      if (ev.target.closest && ev.target.closest('[data-pje-probe-ui]')) return;
      var el = (ev.target.closest && ev.target.closest('button, a, input, select, textarea, mat-select, mat-option, [role="button"], [tabindex]')) || ev.target;
      if (el && el.nodeType === 1) registrarSeletor(el);
    } catch (e) {
      // nunca deixar o probe quebrar a pagina do usuario
    }
  }

  // ── Hovers da maisPJe ──────────────────────────────────────────────────
  //
  // Grava SO os hovers cujo elemento esta dentro de #maisPJe_bt_detalhes_base
  // (a barra de icones da extensao). Cada hover e registrado junto com os
  // botoes que apareceram no menu depois dele — o mapa "icone -> botoes" e
  // exatamente o que falta para automatizar o clique por nome.
  //
  // Fica separado de state.selectors de proposito: sao coisas diferentes.
  // Um seletor e "como achar este elemento"; um hover e "que menu este
  // icone abre".

  var MAISPJE_BASE = '#maisPJe_bt_detalhes_base';
  var MAISPJE_MENU = 'maisPjeContainerAA';

  function iconeDoHover(ev) {
    var alvo = ev.target;
    if (!alvo || !alvo.closest) return null;
    return alvo.closest(MAISPJE_BASE + ' button[aria-label], ' + MAISPJE_BASE + ' a[aria-label]');
  }

  // Le os botoes que a extensao montou no menu (nome + texto + visibilidade).
  function lerMenuMaisPje() {
    var menu = document.querySelector(MAISPJE_MENU);
    if (!menu) return null;

    var botoes = [];
    var todos = menu.querySelectorAll('button');
    for (var i = 0; i < todos.length; i++) {
      var b = todos[i];
      var texto = (b.textContent || '').trim();
      if (!texto && !b.name && !b.id) continue;
      // visivel de verdade: sem display:none e com caixa
      var visivel = b.offsetParent !== null && b.style.display !== 'none';
      botoes.push({
        id: b.id || '',
        name: b.name || '',
        texto: texto,
        ariaLabel: b.getAttribute('aria-label') || '',
        visivel: visivel
      });
    }
    return { id: menu.id || '', total: botoes.length, botoes: botoes };
  }

  function registrarHoverMaisPje(iconeEl) {
    if (!state.recording) return;

    var rotulo = iconeEl.getAttribute('aria-label') || '';
    var chave = iconeEl.id || rotulo;
    var agora = Date.now();

    // Agrupa hovers repetidos do mesmo icone (o mouse sai e volta o tempo
    // todo). Guarda so o ultimo menu lido, mas conta as ocorrencias.
    var h = state.hovers[chave];
    if (!h) {
      h = state.hovers[chave] = {
        id: iconeEl.id || '',
        rotulo: rotulo,
        vezes: 0,
        menuId: '',
        botoes: [],
        atualizadoEm: null
      };
    }
    h.vezes++;
    h.atualizadoEm = agora;

    // A extensao monta os botoes ~500ms depois do hover (addBotaoTelaAnexar
    // usa sleep(500)). Ler cedo demais pegaria o menu vazio ou o anterior.
    setTimeout(function () {
      try {
        var menu = lerMenuMaisPje();
        if (!menu) return;
        h.menuId = menu.id;
        h.botoes = menu.botoes;
        salvarEstado();
      } catch (e) {}
    }, 700);

    salvarEstado();
  }

  function onHoverMaisPje(ev) {
    try {
      if (!state.recording) return;
      var icone = iconeDoHover(ev);
      if (icone) registrarHoverMaisPje(icone);
    } catch (e) {
      // nunca deixar o probe quebrar a pagina do usuario
    }
  }

  // ── Endpoints (mesmo mecanismo de Script/bookmarklet_spy.js) ───────────

  function urlTemplate(url) {
    return String(url).replace(location.origin, '').replace(/[?#].*$/, '')
      .replace(/\/\d{5,}/g, '/{id}')
      .replace(/\/[a-f0-9]{8,}/gi, '/{hash}');
  }

  function tryJson(text) {
    if (!text || typeof text !== 'string') return null;
    try { return JSON.parse(text); } catch (e) { return null; }
  }

  function resumoResposta(body) {
    if (!body || typeof body !== 'object') return '';
    if (Array.isArray(body)) return 'Array[' + body.length + ']' + (body[0] ? ' campos: ' + Object.keys(body[0]).join(', ') : '');
    var arr = body.resultado || body.conteudo || body.content || body.dados || body.lista;
    if (Array.isArray(arr)) return '{resultado:[' + arr.length + ']} campos: ' + (arr[0] ? Object.keys(arr[0]).join(', ') : '');
    return '{' + Object.keys(body).join(', ') + '}';
  }

  function registrarEndpoint(method, url, status, resBody) {
    var tpl = urlTemplate(url);
    var key = (method || 'GET').toUpperCase() + ' ' + tpl;
    var e = state.endpoints[key];
    if (!e) {
      e = state.endpoints[key] = { method: (method || 'GET').toUpperCase(), urlTemplate: tpl, count: 0, statuses: {}, exampleUrl: url, exampleRes: null };
    }
    e.count++;
    if (status !== null && status !== undefined) e.statuses[status] = (e.statuses[status] || 0) + 1;
    if (resBody && !e.exampleRes) e.exampleRes = resumoResposta(resBody);
    salvarEstado();
  }

  function patchNetwork() {
    state.origFetch = unsafeWindow.fetch;
    unsafeWindow.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : (input && input.url) || String(input);
      var method = (init && init.method) || (input && input.method) || 'GET';
      var promise = state.origFetch.apply(this, arguments);
      promise.then(function (resp) {
        resp.clone().text().then(function (text) {
          registrarEndpoint(method, url, resp.status, tryJson(text));
        }).catch(function () {});
      }).catch(function () { registrarEndpoint(method, url, 0, null); });
      return promise;
    };

    state.origOpen = unsafeWindow.XMLHttpRequest.prototype.open;
    state.origSend = unsafeWindow.XMLHttpRequest.prototype.send;
    unsafeWindow.XMLHttpRequest.prototype.open = function (method, url) {
      this.__probe = { method: method, url: url };
      return state.origOpen.apply(this, arguments);
    };
    unsafeWindow.XMLHttpRequest.prototype.send = function () {
      var xhr = this;
      var info = this.__probe;
      if (info) {
        this.addEventListener('loadend', function () {
          registrarEndpoint(info.method, info.url, xhr.status, tryJson(xhr.responseText));
        });
      }
      return state.origSend.apply(this, arguments);
    };
  }

  function unpatchNetwork() {
    if (state.origFetch) unsafeWindow.fetch = state.origFetch;
    if (state.origOpen) unsafeWindow.XMLHttpRequest.prototype.open = state.origOpen;
    if (state.origSend) unsafeWindow.XMLHttpRequest.prototype.send = state.origSend;
  }

  // ── Relatorio ────────────────────────────────────────────────────────

  function buildReport() {
    var dur = Math.round((Date.now() - state.startTime) / 1000);
    var lines = [
      'PJe Probe — ' + document.title,
      location.href,
      'gravado: ' + dur + 's | seletores: ' + state.selectors.length + ' | endpoints: ' + Object.keys(state.endpoints).length,
      '',
      '== SELETORES ==',
    ];
    state.selectors.forEach(function (s) {
      lines.push('[' + s.stability + '] ' + s.selector + (s.count > 1 ? '  (' + s.count + 'x)' : '') + (s.text ? '   // ' + s.text : ''));
    });

    lines.push('', '== ENDPOINTS ==');
    var eps = [];
    for (var k in state.endpoints) eps.push(state.endpoints[k]);
    eps.sort(function (a, b) { return b.count - a.count; });
    eps.forEach(function (e) {
      var statusStr = Object.keys(e.statuses).map(function (s) { return s + 'x' + e.statuses[s]; }).join(', ');
      lines.push(e.count + 'x  ' + e.method + ' ' + e.urlTemplate + (statusStr ? '  [' + statusStr + ']' : ''));
      lines.push('    ex: ' + e.exampleUrl);
      if (e.exampleRes) lines.push('    res: ' + e.exampleRes);
    });

    lines.push('', '== HOVERS maisPJe ==');
    var hovs = [];
    for (var hk in state.hovers) hovs.push(state.hovers[hk]);
    if (!hovs.length) {
      lines.push('(nenhum hover registrado na barra maisPJe)');
    } else {
      hovs.sort(function (a, b) { return b.vezes - a.vezes; });
      hovs.forEach(function (h) {
        lines.push('');
        // Linha pronta para usar no motor: hover(<id>) -> clicar(<name>)
        lines.push('ICONE ' + (h.id || '(sem id)') + '   "' + h.rotulo + '"   (' + h.vezes + 'x)');
        if (h.id) lines.push('  selector: #' + h.id);
        if (!h.botoes.length) {
          lines.push('  botoes: (menu nao lido — hover sem menu aberto?)');
        } else {
          lines.push('  botoes (' + h.botoes.length + '):');
          h.botoes.forEach(function (b) {
            var marca = b.visivel ? '' : '  [OCULTO]';
            lines.push('    name="' + b.name + '"  texto="' + b.texto + '"' +
              (b.id ? '  id=' + b.id : '') + marca);
          });
        }
      });
    }

    return lines.join('\n');
  }

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

  // ── Botao (paleta Catppuccin Mocha, igual Script/bookmarklet_spy.js) ──

  var COLOR_IDLE = '#313244';
  var COLOR_REC = '#f38ba8';
  var COLOR_DONE = '#a6e3a1';
  var COLOR_TEXT = '#cdd6f4';

  var btn = document.createElement('button');
  btn.setAttribute('data-pje-probe-ui', '1');
  btn.textContent = '● PROBE';
  btn.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:2147483647;' +
    'padding:10px 18px;border:none;border-radius:20px;font:600 13px monospace;' +
    'background:' + COLOR_IDLE + ';color:' + COLOR_TEXT + ';box-shadow:0 4px 16px rgba(0,0,0,.4);cursor:pointer;';
  document.body.appendChild(btn);

  var liveTimer = null;

  function iniciarGravacao(retomarDe) {
    state.recording = true;
    state.startTime = retomarDe ? retomarDe.startTime : Date.now();
    state.selectors = retomarDe ? retomarDe.selectors : [];
    state.selectorIndex = retomarDe ? retomarDe.selectorIndex : {};
    state.endpoints = retomarDe ? retomarDe.endpoints : {};
    state.hovers = (retomarDe && retomarDe.hovers) ? retomarDe.hovers : {};
    document.addEventListener('click', onInteraction, true);
    document.addEventListener('focusin', onInteraction, true);
    // Hovers da barra maisPJe: mouseover e o unico evento que a extensao
    // garante receber (ela usa onmouseenter no botao, que dispara junto).
    document.addEventListener('mouseover', onHoverMaisPje, true);
    patchNetwork();
    btn.style.background = COLOR_REC;
    salvarEstado();
    liveTimer = setInterval(function () {
      btn.textContent = '● GRAVANDO ' + state.selectors.length + '/' +
        Object.keys(state.endpoints).length + ' ep/' +
        Object.keys(state.hovers).length + ' hov (clique p/ parar)';
    }, 500);
  }

  function pararGravacao() {
    state.recording = false;
    clearInterval(liveTimer);
    document.removeEventListener('click', onInteraction, true);
    document.removeEventListener('focusin', onInteraction, true);
    document.removeEventListener('mouseover', onHoverMaisPje, true);
    unpatchNetwork();
    var report = buildReport();
    copyText(report);
    limparEstadoSalvo();
    console.log('[PJE_PROBE] relatorio copiado:\n' + report);
    btn.textContent = '✓ copiado (' + state.selectors.length + ' sel / ' +
      Object.keys(state.endpoints).length + ' ep / ' +
      Object.keys(state.hovers).length + ' hov)';
    btn.style.background = COLOR_DONE;
    setTimeout(function () {
      btn.textContent = '● PROBE';
      btn.style.background = COLOR_IDLE;
    }, 2500);
  }

  btn.addEventListener('click', function () {
    if (!state.recording) iniciarGravacao(null);
    else pararGravacao();
  });

  // ── Auto-retomada: sobrevive a navegacao E a troca de origem ──────────

  var salvo = carregarEstadoSalvo();
  if (salvo && salvo.recording) {
    iniciarGravacao(salvo);
    console.log('[PJE_PROBE] gravacao retomada apos navegacao/troca de origem (' + salvo.selectors.length + ' sel / ' + Object.keys(salvo.endpoints).length + ' ep ate agora).');
  }

  console.log('[PJE_PROBE] pronto — clique no botao PROBE (canto inferior direito) para gravar. Dica: clique PROBE ANTES de recarregar a pagina que voce quer mapear por completo, senao as chamadas automaticas de carregamento daquela pagina especifica ficam de fora (o probe so ve o que acontece depois de ligado).');
})();
