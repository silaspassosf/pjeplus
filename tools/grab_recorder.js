/**
 * grab_recorder.js
 *
 * Injeta no browser autenticado do PJe e captura TODA interacao humana:
 * cliques, digitacoes, selecoes de dropdown, mudancas de aba.
 *
 * Funciona em paralelo com pjeapi.js (que captura fetch/XHR).
 * O Python em tools/grab.py faz poll via window.__grab.flush() a cada 2s.
 *
 * SAIDA POR EVENTO (click):
 * {
 *   ts:                  timestamp em ms (Date.now())
 *   type:                "click" | "input" | "change" | "focus" | "nav"
 *   page_url:            URL completa da aba
 *   page_path:           pathname (sem query/hash)
 *   el_info: {
 *     tag, id, classes, ariaLabel, role, name, type, placeholder,
 *     text,             texto visivel (ate 80 chars)
 *     ngReflect,        atributos ng-reflect-*
 *     dataAttrs,        atributos data-*
 *     selector_candidates: [
 *       { selector: string, stability: "high|medium|low", type: string }
 *     ]
 *     best_selector:    melhor candidato (primeiro de maior estabilidade)
 *   }
 *   xpath:               XPath absoluto do elemento
 *   value:               (type input/change) valor digitado
 * }
 */
(function pjeGrabRecorder() {
  'use strict';

  if (window.__grab) {
    console.log('[PJE_GRAB] Recorder ja ativo.');
    return;
  }

  window.__grab = {
    events:    [],
    _flushPtr: 0,
  };

  const E = window.__grab.events;

  // ── Estabilidade de seletor ───────────────────────────────────────────────

  /**
   * Retorna candidatos de seletor CSS/XPath para um elemento,
   * ordenados do mais para o menos estavel.
   */
  function candidatos(el) {
    const tag  = el.tagName.toLowerCase();
    const list = [];

    // 1. ID nao-gerado (alta estabilidade)
    if (el.id && !el.id.match(/^(ng-|mat-|cdk-)/) && !el.id.match(/^\d/) && el.id.length < 50) {
      list.push({ selector: '#' + CSS.escape(el.id), stability: 'high', type: 'id' });
    }

    // 2. data-* atributo (alta estabilidade — adicionado intencionalmente pelo dev)
    for (const attr of el.attributes) {
      if (attr.name.startsWith('data-') && attr.value && attr.value.length < 80) {
        list.push({ selector: `[${attr.name}="${attr.value}"]`, stability: 'high', type: 'data-attr' });
        break;
      }
    }

    // 3. aria-label (media — pode mudar com i18n, mas estavel no PJe BR)
    const aria = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
    if (aria && aria.length < 80) {
      list.push({ selector: `${tag}[aria-label="${aria}"]`, stability: 'medium', type: 'aria' });
    }

    // 4. ng-reflect-name (angular binding — media estabilidade)
    const ngName = el.getAttribute('ng-reflect-name');
    if (ngName) {
      list.push({ selector: `[ng-reflect-name="${ngName}"]`, stability: 'medium', type: 'ng-reflect-name' });
    }

    // 5. name + type para inputs (media)
    const nameAttr = el.getAttribute('name');
    if (nameAttr) {
      const typeAttr = el.getAttribute('type');
      const base = typeAttr
        ? `${tag}[name="${nameAttr}"][type="${typeAttr}"]`
        : `${tag}[name="${nameAttr}"]`;
      list.push({ selector: base, stability: 'medium', type: 'name-attr' });
    }

    // 6. role + mat- class (media para Angular Material)
    const role = el.getAttribute('role');
    const matClasses = [...el.classList].filter(c => c.startsWith('mat-') && !c.match(/\d{4,}/));
    if (role && matClasses.length > 0) {
      list.push({
        selector: `${tag}[role="${role}"].${matClasses[0]}`,
        stability: 'medium',
        type: 'role-mat',
      });
    }

    // 7. Classes estaveis (sem hashes, sem ng-*, sem cdk-*)
    const stableClasses = [...el.classList].filter(
      c => !c.match(/^(ng-|_ng|cdk-|mat-ripple|mat-focus|ng-tns|ng-star)/) &&
           !c.match(/\d{5,}/) &&
           c.length > 2
    );
    if (stableClasses.length > 0) {
      list.push({
        selector: `${tag}.${stableClasses.slice(0, 3).join('.')}`,
        stability: 'low',
        type: 'tag-class',
      });
    }

    // 8. XPath por texto visivel (baixa estabilidade, ultima opcao)
    const txt = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    if (txt && txt.length >= 3 && txt.length <= 40 && !txt.match(/\d{5,}/)) {
      list.push({
        selector: `//${tag}[normalize-space(.)="${txt}"]`,
        stability: 'low',
        type: 'xpath-text',
      });
    }

    return list;
  }

  function xpathDe(el) {
    if (el.id && !el.id.match(/^(ng-|mat-|cdk-)/))
      return `//*[@id="${el.id}"]`;
    const partes = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
      let idx = 1;
      let sib = node.previousElementSibling;
      while (sib) {
        if (sib.tagName === node.tagName) idx++;
        sib = sib.previousElementSibling;
      }
      partes.unshift(`${node.tagName.toLowerCase()}[${idx}]`);
      node = node.parentElement;
    }
    return '/html/body/' + partes.join('/');
  }

  function elInfo(el) {
    const tag        = el.tagName.toLowerCase();
    const classes    = [...el.classList];
    const ngReflect  = {};
    const dataAttrs  = {};

    for (const attr of el.attributes) {
      if (attr.name.startsWith('ng-reflect-')) ngReflect[attr.name] = attr.value;
      if (attr.name.startsWith('data-'))       dataAttrs[attr.name] = attr.value;
    }

    const cands = candidatos(el);

    return {
      tag,
      id:           el.id || null,
      classes,
      ariaLabel:    el.getAttribute('aria-label') || null,
      role:         el.getAttribute('role') || null,
      name:         el.getAttribute('name') || null,
      type:         el.getAttribute('type') || null,
      placeholder:  el.getAttribute('placeholder') || null,
      text:         (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80),
      ngReflect,
      dataAttrs,
      selector_candidates: cands,
      best_selector: cands[0]?.selector || null,
      stability:     cands[0]?.stability || 'unknown',
    };
  }

  // ── Listeners ─────────────────────────────────────────────────────────────

  document.addEventListener('click', function(evt) {
    const el = evt.target;
    if (!el || el === document.body || el === document.documentElement) return;
    E.push({
      ts:         Date.now(),
      type:       'click',
      page_url:   location.href,
      page_path:  location.pathname,
      el_info:    elInfo(el),
      xpath:      xpathDe(el),
    });
    if (E.length % 10 === 0)
      console.log(`[PJE_GRAB] ${E.length} eventos capturados.`);
  }, true);

  document.addEventListener('input', function(evt) {
    const el = evt.target;
    if (!el || !['input', 'textarea'].includes(el.tagName.toLowerCase())) return;
    E.push({
      ts:        Date.now(),
      type:      'input',
      page_url:  location.href,
      page_path: location.pathname,
      el_info:   elInfo(el),
      xpath:     xpathDe(el),
      value:     (el.value || '').slice(0, 200),
    });
  }, true);

  document.addEventListener('change', function(evt) {
    const el = evt.target;
    if (!el) return;
    E.push({
      ts:        Date.now(),
      type:      'change',
      page_url:  location.href,
      page_path: location.pathname,
      el_info:   elInfo(el),
      xpath:     xpathDe(el),
      value:     (el.value || '').slice(0, 200),
    });
  }, true);

  document.addEventListener('focus', function(evt) {
    const el = evt.target;
    if (!el || !['input', 'textarea', 'select', 'mat-select'].includes(el.tagName.toLowerCase())) return;
    E.push({
      ts:        Date.now(),
      type:      'focus',
      page_url:  location.href,
      page_path: location.pathname,
      el_info:   elInfo(el),
      xpath:     xpathDe(el),
    });
  }, true);

  // ── API publica __grab.* ─────────────────────────────────────────────────

  /** Retorna novos eventos desde o ultimo flush (para polling Python). */
  window.__grab.flush = function() {
    const ptr  = window.__grab._flushPtr;
    const news = E.slice(ptr);
    window.__grab._flushPtr = E.length;
    return news;
  };

  /** Retorna todos os eventos capturados na sessao inteira. */
  window.__grab.export = function() {
    return E;
  };

  /** Estatisticas rapidas. */
  window.__grab.stats = function() {
    const byType = {};
    for (const ev of E) {
      byType[ev.type] = (byType[ev.type] || 0) + 1;
    }
    const byPage = {};
    for (const ev of E) {
      byPage[ev.page_path] = (byPage[ev.page_path] || 0) + 1;
    }
    console.group('[PJE_GRAB] Stats');
    console.log('Total eventos:', E.length);
    console.log('Por tipo:', byType);
    console.log('Por pagina:', byPage);
    const maisEstavel = E.filter(e => e.el_info?.stability === 'high').length;
    const media       = E.filter(e => e.el_info?.stability === 'medium').length;
    const baixa       = E.filter(e => e.el_info?.stability === 'low').length;
    console.log(`Seletores: high=${maisEstavel} medium=${media} low=${baixa}`);
    console.groupEnd();
    return { byType, byPage };
  };

  console.log('[PJE_GRAB] Recorder ativo -- capturando clicks, inputs, changes, focus.');
  console.log('[PJE_GRAB] Atalhos: __grab.stats() | __grab.export() | __grab.flush()');
})();
