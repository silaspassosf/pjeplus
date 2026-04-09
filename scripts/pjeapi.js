/**
 * pje_api_spy_iife.js
 *
 * Cola no console do PJe autenticado e fica ativo enquanto a aba permanecer aberta.
 *
 * PROBLEMA QUE RESOLVE
 * Dado um elemento da interface (table row, badge, card, span...),
 * descobrir qual endpoint de API forneceu aquele dado —
 * sem precisar abrir o DevTools Network e caçar manualmente.
 *
 * COMO USAR
 * ─────────────────────────────────────────────────────────────────────────────
 * 1. Cole este arquivo inteiro no console (ou carregue via snippet).
 *    O spy já está ativo — intercepta fetch + XHR silenciosamente.
 *
 * 2. Navegue normalmente: abra painéis, processos, abas...
 *    Cada chamada /api/ é capturada em window.__pje.log
 *
 * 3. Descoberta por elemento DOM:
 *    (a) Selecione o elemento no Inspector e volte para o console
 *        __pje.fromEl($0)              // $0 = último elemento inspecionado
 *    (b) Por seletor CSS:
 *        __pje.fromEl('pje-timeline')
 *    (c) Por texto visível na tela:
 *        __pje.search('1000632-12.2025')
 *
 * 4. Modo click-spy — próximo clique na página:
 *        __pje.watchNext()
 *    Clique qualquer elemento. O spy mostra todas as API calls feitas nos
 *    3s seguintes + mutações do DOM associadas.
 *
 * 5. Testar endpoint manualmente com XSRF automático:
 *        __pje.probe('/pje-comum-api/api/processos/id/12345')
 *        __pje.probe('/pje-comum-api/api/processos/id/12345/partes')
 *        __pje.probe('/pje-comum-api/api/escaninhos/peticoesjuntadas?pagina=1&tamanhoPagina=10')
 *
 * 6. Resumo de todos os endpoints vistos:
 *        __pje.summary()
 *
 * 7. Exportar log completo:
 *        __pje.export()   // copia JSON para clipboard
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * FLUXO RECOMENDADO PARA DESCOBERTA
 * ─────────────────────────────────────────────────────────────────────────────
 * Cenário: Vejo um badge "3 petições" e não sei de onde vem.
 *
 *   Passo 1 — Inspecionar elemento → $0 = badge no DOM
 *   Passo 2 — __pje.fromEl($0)
 *             → mostra endpoints cujas respostas contêm o texto "3" ou o texto
 *               visível do badge, ranqueados por score
 *   Passo 3 — Se nenhum resultado: __pje.watchNext() + navegar até o badge
 *             → o spy captura o XHR/fetch que carregou o dado
 *   Passo 4 — __pje.last(3)  → ver últimas 3 chamadas capturadas
 *   Passo 5 — __pje.probe('/endpoint/descoberto')  → confirmar estrutura
 */

(function pjeApiSpy() {
  'use strict';

  // ─── Constantes ──────────────────────────────────────────────────────────
  const TAG         = '[PJE_SPY]';
  const MAX_BODY    = 200_000;  // chars — limite p/ evitar OOM em respostas grandes
  const MAX_LOG     = 500;      // máximo de entradas no log
  const API_FILTER  = /\/(?:pje-[\w-]+-api|pje-comum-api|pje-gigs-api|sif-financeiro-api)\//;

  // ─── Estado global ────────────────────────────────────────────────────────
  if (!window.__pje) {
    window.__pje = {
      log:        [],   // entradas capturadas: {ts, method, url, reqBody, status, resBody, duration, urlTemplate}
      _mutations: [],   // mutações DOM recentes: {ts, addedText, target}
      _watching:  false,
    };
  }
  const L = window.__pje.log;

  // ─── Utilitários ─────────────────────────────────────────────────────────

  function now() { return performance.now() + performance.timeOrigin; }

  /** Normaliza URL para template (substitui IDs numéricos e hashes por {id}). */
  function urlTemplate(url) {
    return url
      .replace(location.origin, '')
      .replace(/[?#].*$/, '')
      .replace(/\/\d{5,}/g, '/{id}')
      .replace(/\/[a-f0-9]{8,}/gi, '/{hash}');
  }

  /** Extrai até MAX_BODY chars de um body para armazenar. */
  function truncate(str) {
    if (typeof str !== 'string') return str;
    return str.length > MAX_BODY ? str.slice(0, MAX_BODY) + '…[truncado]' : str;
  }

  /** Tenta parsear JSON; retorna a string original se falhar. */
  function tryJson(text) {
    if (!text || typeof text !== 'string') return null;
    try { return JSON.parse(text); } catch { return text; }
  }

  /** Registra uma chamada no log. */
  function registrar(entry) {
    L.push(entry);
    if (L.length > MAX_LOG) L.splice(0, L.length - MAX_LOG);
  }

  // ─── 1. Patch fetch ───────────────────────────────────────────────────────
  const _origFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url    = typeof input === 'string' ? input : (input.url || String(input));
    const method = (init?.method || 'GET').toUpperCase();

    if (!API_FILTER.test(url)) return _origFetch.apply(this, arguments);

    const t0      = now();
    const reqBody = init?.body ? tryJson(
      typeof init.body === 'string' ? init.body : null
    ) : null;

    let resp;
    try {
      resp = await _origFetch.apply(this, arguments);
    } catch (e) {
      registrar({ ts: t0, method, url, reqBody, status: 0, resBody: null, duration: now() - t0, erro: e.message, urlTemplate: urlTemplate(url) });
      throw e;
    }

    const clone = resp.clone();
    clone.text().then(text => {
      registrar({
        ts:          t0,
        method,
        url,
        reqBody,
        status:      resp.status,
        resBody:     tryJson(truncate(text)),
        duration:    Math.round(now() - t0),
        urlTemplate: urlTemplate(url),
      });
    }).catch(() => {});

    return resp;
  };

  // ─── 2. Patch XMLHttpRequest ──────────────────────────────────────────────
  const _origOpen        = XMLHttpRequest.prototype.open;
  const _origSend        = XMLHttpRequest.prototype.send;
  const _origSetHeader   = XMLHttpRequest.prototype.setRequestHeader;

  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._spy = API_FILTER.test(url) ? { method: method.toUpperCase(), url, headers: {}, t0: 0 } : null;
    return _origOpen.apply(this, [method, url, ...rest]);
  };

  XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
    if (this._spy) this._spy.headers[name.toLowerCase()] = value;
    return _origSetHeader.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function(body) {
    if (this._spy) {
      this._spy.t0       = now();
      this._spy.reqBody  = tryJson(typeof body === 'string' ? body : null);

      this.addEventListener('loadend', () => {
        if (!this._spy) return;
        registrar({
          ts:          this._spy.t0,
          method:      this._spy.method,
          url:         this._spy.url,
          reqBody:     this._spy.reqBody,
          status:      this.status,
          resBody:     tryJson(truncate(this.responseText)),
          duration:    Math.round(now() - this._spy.t0),
          urlTemplate: urlTemplate(this._spy.url),
        });
      });
    }
    return _origSend.apply(this, arguments);
  };

  // ─── 3. MutationObserver — correlação DOM ────────────────────────────────
  const M = window.__pje._mutations;
  const _obs = new MutationObserver(mutations => {
    const ts = now();
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        const text = node.textContent?.trim().slice(0, 200);
        if (text && text.length > 3) {
          M.push({ ts, addedText: text, target: node.parentElement?.tagName });
          if (M.length > 2000) M.splice(0, M.length - 2000);
        }
      }
    }
  });
  _obs.observe(document.body, { childList: true, subtree: true });

  // ─── 4. Extração de tokens de elementos DOM ───────────────────────────────

  /** Extrai tokens "interessantes" do texto: números, CNJ, datas, palavras longas. */
  function extrairTokens(texto) {
    const tokens = new Set();
    // Número de processo CNJ
    (texto.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g) || []).forEach(t => tokens.add(t));
    // CNPJ / CPF numérico
    (texto.match(/\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/g) || []).forEach(t => tokens.add(t));
    (texto.match(/\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g) || []).forEach(t => tokens.add(t));
    // Datas
    (texto.match(/\d{1,2}\/\d{2}\/\d{4}/g) || []).forEach(t => tokens.add(t));
    // IDs numéricos grandes (>= 5 dígitos)
    (texto.match(/\b\d{5,}\b/g) || []).forEach(t => tokens.add(t));
    // Palavras longas (>= 6 chars) que parecem nomes
    (texto.match(/[A-Za-záàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]{6,}/g) || [])
      .filter(w => w.length <= 30)
      .forEach(t => tokens.add(t));
    return [...tokens].filter(t => t.length >= 4);
  }

  /** Dado um token, retorna entradas do log que o contêm na resposta, com score. */
  function buscarToken(token) {
    const lower = token.toLowerCase();
    const hits  = [];
    for (const entry of L) {
      const haystack = typeof entry.resBody === 'string'
        ? entry.resBody.toLowerCase()
        : JSON.stringify(entry.resBody || '').toLowerCase();
      if (haystack.includes(lower)) {
        const existing = hits.find(h => h.urlTemplate === entry.urlTemplate);
        if (existing) { existing.score++; existing.exemplos.push(token); }
        else hits.push({ urlTemplate: entry.urlTemplate, method: entry.method, url: entry.url, status: entry.status, score: 1, exemplos: [token], entry });
      }
    }
    return hits;
  }

  // ─── 5. API pública __pje.* ───────────────────────────────────────────────

  /**
   * Busca texto em todos os log de respostas capturadas.
   * Retorna entradas únicas por urlTemplate, ranqueadas por frequência de match.
   */
  window.__pje.search = function(texto) {
    const tokens = typeof texto === 'string' && texto.includes(' ')
      ? texto.split(/\s+/).filter(t => t.length >= 3)
      : [texto];
    const scorePorTemplate = {};
    for (const token of tokens) {
      for (const hit of buscarToken(String(token))) {
        if (!scorePorTemplate[hit.urlTemplate]) scorePorTemplate[hit.urlTemplate] = { ...hit, score: 0, tokens: [] };
        scorePorTemplate[hit.urlTemplate].score += hit.score;
        scorePorTemplate[hit.urlTemplate].tokens.push(...hit.exemplos);
      }
    }
    const resultados = Object.values(scorePorTemplate).sort((a, b) => b.score - a.score);
    if (resultados.length === 0) {
      console.log(`${TAG} Nenhum resultado para "${texto}" em ${L.length} entradas capturadas.`);
    } else {
      console.group(`${TAG} search("${texto}") — ${resultados.length} endpoint(s)`);
      resultados.forEach((r, i) => {
        console.log(`  [${i + 1}] ${r.method} ${r.urlTemplate}  (score=${r.score}, HTTP ${r.status})`);
        console.log(`       URL real: ${r.url}`);
        console.log(`       Tokens:   ${[...new Set(r.tokens)].join(' | ')}`);
      });
      console.groupEnd();
    }
    return resultados;
  };

  /**
   * Dado um elemento DOM ou seletor CSS, extrai o texto visível e faz search().
   * Uso: __pje.fromEl($0)  ou  __pje.fromEl('pje-timeline')
   */
  window.__pje.fromEl = function(elOrSelector) {
    const el = typeof elOrSelector === 'string'
      ? document.querySelector(elOrSelector)
      : elOrSelector;
    if (!el) { console.warn(`${TAG} Elemento não encontrado: ${elOrSelector}`); return []; }
    const texto = el.innerText || el.textContent || '';
    const tokens = extrairTokens(texto);
    console.log(`${TAG} fromEl › ${el.tagName}${el.id ? '#' + el.id : ''} — ${tokens.length} token(s): ${tokens.slice(0, 8).join(' | ')}`);
    if (tokens.length === 0) { console.warn(`${TAG} Nenhum token extraído do elemento.`); return []; }

    const scorePorTemplate = {};
    for (const token of tokens) {
      for (const hit of buscarToken(token)) {
        if (!scorePorTemplate[hit.urlTemplate]) scorePorTemplate[hit.urlTemplate] = { ...hit, score: 0, tokens: [] };
        scorePorTemplate[hit.urlTemplate].score += hit.score;
        scorePorTemplate[hit.urlTemplate].tokens.push(token);
      }
    }
    const resultados = Object.values(scorePorTemplate).sort((a, b) => b.score - a.score);
    if (resultados.length === 0) {
      console.warn(`${TAG} Nenhum endpoint encontrado. Tente: __pje.watchNext() e navegar até o elemento.`);
    } else {
      console.group(`${TAG} fromEl — ${resultados.length} endpoint(s) candidato(s)`);
      resultados.slice(0, 8).forEach((r, i) => {
        const conf = Math.min(100, Math.round((r.score / tokens.length) * 100));
        console.log(`  [${i + 1}] confiança=${conf}%  ${r.method} ${r.urlTemplate}`);
        console.log(`       URL real:    ${r.url}`);
        console.log(`       Tokens match: ${[...new Set(r.tokens)].join(' | ')}`);
        if (r.entry?.reqBody) console.log(`       Request body:`, r.entry.reqBody);
      });
      console.groupEnd();
    }
    return resultados;
  };

  /**
   * Modo click-spy: aguarda o próximo clique do usuário e captura
   * todas as chamadas API nos 3s seguintes + mutações DOM correlacionadas.
   */
  window.__pje.watchNext = function(timeout_ms = 5000) {
    if (window.__pje._watching) { console.log(`${TAG} watchNext já ativo.`); return; }
    window.__pje._watching = true;
    const banner = document.createElement('div');
    Object.assign(banner.style, {
      position: 'fixed', top: '0', left: '0', width: '100%', padding: '8px', textAlign: 'center',
      background: '#1a73e8', color: '#fff', fontFamily: 'monospace', fontSize: '13px',
      zIndex: '999999', cursor: 'pointer',
    });
    banner.textContent = `[PJE_SPY] Click-spy ativo — clique em qualquer elemento para capturar API calls.`;
    document.body.appendChild(banner);

    function handleClick(evt) {
      document.removeEventListener('click', handleClick, true);
      banner.textContent = `[PJE_SPY] Capturando por ${timeout_ms / 1000}s…`;
      const el     = evt.target;
      const logSnapshot = L.length;
      const tsClick = now();

      setTimeout(() => {
        banner.remove();
        window.__pje._watching = false;
        const novas = L.slice(logSnapshot);
        const mutacoes = M.filter(m => m.ts >= tsClick && m.ts <= tsClick + timeout_ms);

        console.group(`${TAG} watchNext — ${novas.length} chamada(s) capturada(s)`);
        console.log(`  Elemento clicado: <${el.tagName.toLowerCase()}> "${el.textContent?.trim().slice(0, 60)}"`);
        novas.forEach((e, i) => {
          console.group(`  [${i + 1}] ${e.method} ${e.urlTemplate}  HTTP ${e.status}  (${e.duration}ms)`);
          console.log(`     URL completa: ${e.url}`);
          if (e.reqBody) console.log(`     Request body:`, e.reqBody);
          if (e.resBody) console.log(`     Response (resumo):`, _resumoResposta(e.resBody));
          console.groupEnd();
        });

        if (mutacoes.length > 0) {
          console.group(`  DOM mutations (${mutacoes.length}):`);
          mutacoes.slice(0, 10).forEach(m => console.log(`    <${m.target}> "${m.addedText.slice(0, 80)}"`));
          console.groupEnd();
        }

        // Correlação: qual API call corresponde a qual mutação DOM?
        if (novas.length > 0 && mutacoes.length > 0) {
          console.group('  Correlação API → DOM:');
          for (const call of novas) {
            const muts = mutacoes.filter(m => Math.abs(m.ts - (call.ts + call.duration)) < 800);
            if (muts.length > 0)
              console.log(`    ${call.method} ${call.urlTemplate} → ${muts.length} mutação(ões) em ~${Math.round(muts[0].ts - call.ts)}ms`);
          }
          console.groupEnd();
        }
        console.groupEnd();
        console.log(`${TAG} Dica: use __pje.fromEl($0) para buscar por elemento, ou __pje.search("texto") para busca manual.`);
      }, timeout_ms);
    }

    document.addEventListener('click', handleClick, true);
    console.log(`${TAG} watchNext ativo — aguardando clique...`);
  };

  /**
   * Clica em um elemento já conhecido e captura as API calls disparadas.
   * Mais prático que watchNext() quando você já tem o elemento em mãos.
   *
   * Uso:
   *   __pje.clickEl($0)                                               // elemento inspecionado
   *   __pje.clickEl('button[aria-label="Processos associados"]')      // por seletor
   *   __pje.clickEl($0, 8000)                                         // aguarda 8s
   */
  window.__pje.clickEl = async function(elOrSelector, timeout_ms = 5000) {
    const el = typeof elOrSelector === 'string'
      ? document.querySelector(elOrSelector)
      : elOrSelector;
    if (!el) { console.warn(`${TAG} clickEl: elemento não encontrado: ${elOrSelector}`); return []; }

    const logSnapshot = L.length;
    const tsClick     = now();
    const label       = (el.ariaLabel || el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 60);

    console.log(`${TAG} clickEl: clicando em <${el.tagName.toLowerCase()}>${label ? ' "' + label + '"' : ''} — aguardando ${timeout_ms}ms...`);
    el.click();

    await new Promise(r => setTimeout(r, timeout_ms));

    const novas    = L.filter(e => !e._fromPerf).slice(logSnapshot - L.filter(e => e._fromPerf).length);
    // simpler: entries appended after click
    const novasCap = L.slice(logSnapshot);
    const mutacoes = M.filter(m => m.ts >= tsClick && m.ts <= tsClick + timeout_ms);

    if (novasCap.length === 0) {
      console.warn(`${TAG} clickEl: nenhuma chamada API capturada em ${timeout_ms}ms.`);
      console.warn(`${TAG} Dica: os dados podem já estar em cache. Verifique __pje.live() ou recarregue a página antes de instalar o spy.`);
    } else {
      console.group(`${TAG} clickEl — ${novasCap.length} chamada(s) capturada(s)`);
      novasCap.forEach((e, i) => {
        console.group(`  [${i + 1}] ${e.method} ${e.urlTemplate}  HTTP ${e.status}  (${e.duration}ms)`);
        console.log(`     URL completa: ${e.url}`);
        if (e.reqBody) console.log(`     Request body:`, e.reqBody);
        if (e.resBody) console.log(`     Response:`, _resumoResposta(e.resBody));
        console.groupEnd();
      });
      if (mutacoes.length > 0)
        console.log(`  DOM mutations: ${mutacoes.length} nó(s) adicionado(s) ao DOM`);
      console.groupEnd();
    }
    return novasCap;
  };

  /**
   * Mostra apenas as chamadas capturadas em tempo real pelo spy
   * (ignora entradas importadas do Performance API via seed).
   * Uso: __pje.live()   ou   __pje.live(10)
   */
  window.__pje.live = function(n = 50) {
    const vivas = L.filter(e => !e._fromPerf).slice(-n);
    if (vivas.length === 0) {
      console.log(`${TAG} live: nenhuma chamada interceptada ainda (${L.length} entradas são todas do seed).`);
      return [];
    }
    console.group(`${TAG} live — ${vivas.length} chamada(s) interceptada(s) (seed excluído)`);
    vivas.forEach((e, i) => {
      console.group(`  [${i + 1}] ${e.method} ${e.urlTemplate}  HTTP ${e.status}  (${e.duration}ms)`);
      console.log(`     URL: ${e.url}`);
      if (e.reqBody) console.log(`     Req:`, e.reqBody);
      console.log(`     Res:`, _resumoResposta(e.resBody));
      console.groupEnd();
    });
    console.groupEnd();
    return vivas;
  };

  /** Mostra as últimas N entradas do log. */
  window.__pje.last = function(n = 5) {
    const recentes = L.slice(-n);
    console.group(`${TAG} Últimas ${recentes.length} chamadas:`);
    recentes.forEach((e, i) => {
      console.group(`  [${i + 1}] ${e.method} ${e.urlTemplate}  HTTP ${e.status}  (${e.duration}ms)`);
      console.log(`     URL: ${e.url}`);
      if (e.reqBody) console.log(`     Req:`, e.reqBody);
      console.log(`     Res:`, _resumoResposta(e.resBody));
      console.groupEnd();
    });
    console.groupEnd();
    return recentes;
  };

  /** Tabela de todos os endpoints únicos vistos, com contagem. */
  window.__pje.summary = function() {
    const contagem = {};
    for (const e of L) {
      const key = `${e.method} ${e.urlTemplate}`;
      if (!contagem[key]) contagem[key] = { method: e.method, urlTemplate: e.urlTemplate, count: 0, statuses: new Set(), ex: e.url };
      contagem[key].count++;
      contagem[key].statuses.add(e.status);
    }
    const seedCount = L.filter(e => e._fromPerf).length;
    const lista = Object.values(contagem).sort((a, b) => b.count - a.count);
    console.group(`${TAG} summary — ${lista.length} endpoint(s) únicos (${L.length} totais, ${seedCount} seed, ${L.length - seedCount} interceptados)`);
    for (const e of lista) {
      const seedEntries = L.filter(en => en._fromPerf && en.urlTemplate === e.urlTemplate);
      const tag = seedEntries.length === e.count ? ' [seed]' : seedEntries.length > 0 ? ` [${seedEntries.length} seed]` : '';
      console.log(`  ${e.count.toString().padStart(3)}x  ${e.method.padEnd(6)} ${e.urlTemplate}  [${[...e.statuses].join(',')}]${tag}`);
    }
    console.groupEnd();
    return lista;
  };

  /**
   * Testa um endpoint diretamente com XSRF automático.
   * __pje.probe('/pje-comum-api/api/processos/id/12345/partes')
   * __pje.probe('/pje-comum-api/api/processos/id/12345/partes', 'GET')
   * __pje.probe('/pje-comum-api/api/escaninhos/peticoesjuntadas', 'GET')
   */
  window.__pje.probe = async function(urlOrPath, method = 'GET', body) {
    const url  = urlOrPath.startsWith('http') ? urlOrPath : location.origin + urlOrPath;
    const xsrf = window.__pje.xsrf();
    const hdrs = {
      'Accept'           : 'application/json',
      'Content-Type'     : 'application/json',
      'X-Grau-Instancia' : '1',
    };
    if (xsrf) hdrs['X-XSRF-TOKEN'] = xsrf;

    method = method.toUpperCase();
    const opts = { method, credentials: 'include', headers: hdrs };
    if (body !== undefined) opts.body = JSON.stringify(body);

    console.log(`${TAG} probe ${method} ${url}${xsrf ? '' : '  (sem XSRF)'}`);
    try {
      const resp = await _origFetch(url, opts);
      const text = await resp.text();
      const data = tryJson(text);
      console.group(`${TAG} probe → HTTP ${resp.status}`);
      if (data && typeof data === 'object') {
        const arr   = Array.isArray(data) ? data : (data.resultado || data.content || data.conteudo || data.lista || []);
        const item0 = Array.isArray(arr) && arr.length > 0 ? arr[0] : (Array.isArray(data) ? null : data);
        console.log(`  Tipo: ${Array.isArray(data) ? 'Array' : 'Object'}  |  itens: ${Array.isArray(arr) ? arr.length : '—'}`);
        if (item0) {
          console.log(`  Campos do item[0]:`, Object.keys(item0));
          console.log(`  item[0]:`, item0);
        } else {
          console.log(`  Resposta:`, data);
        }
      } else {
        console.log(`  Resposta raw (${text.length} chars):`, text.slice(0, 500));
      }
      console.groupEnd();
      return { status: resp.status, data };
    } catch (e) {
      console.error(`${TAG} probe ERRO:`, e.message);
      return { status: 0, erro: e.message };
    }
  };

  /** Lê o XSRF-TOKEN do cookie. */
  window.__pje.xsrf = function() {
    const c = document.cookie.split(';').map(s => s.trim())
      .find(s => s.toLowerCase().startsWith('xsrf-token='));
    return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
  };

  /** Exporta todo o log para o clipboard. */
  window.__pje.export = function() {
    const json = JSON.stringify(L, null, 2);
    navigator.clipboard?.writeText(json).then(
      ()  => console.log(`${TAG} Log copiado (${L.length} entradas, ${(json.length / 1024).toFixed(1)} KB)`),
      ()  => { window.__pje._exportData = L; console.log(`${TAG} clipboard bloqueado — use window.__pje._exportData`); }
    );
    return json;
  };

  /**
   * Dado um elemento DOM ou seletor, lista apenas as mutações DOM
   * que aconteceram em paralelo com chamadas API — útil para ver
   * qual chamada "pintou" aquele elemento.
   */
  window.__pje.watchMutation = function(elOrSelector, duration_ms = 8000) {
    const el = typeof elOrSelector === 'string'
      ? document.querySelector(elOrSelector)
      : elOrSelector;
    if (!el) { console.warn(`${TAG} Elemento não encontrado`); return; }
    console.log(`${TAG} watchMutation: monitorando <${el.tagName}> por ${duration_ms}ms...`);
    const obs = new MutationObserver(muts => {
      const ts = now();
      for (const mut of muts) {
        const novas = L.filter(e => Math.abs((e.ts + e.duration) - ts) < 1000);
        if (novas.length > 0) {
          console.log(`${TAG} Mutação em <${el.tagName}> correlacionada com:`);
          novas.forEach(e => console.log(`  ${e.method} ${e.urlTemplate}  HTTP ${e.status}`));
        }
      }
    });
    obs.observe(el, { childList: true, subtree: true, characterData: true });
    setTimeout(() => { obs.disconnect(); console.log(`${TAG} watchMutation encerrado.`); }, duration_ms);
  };

  // ─── Helpers internos ────────────────────────────────────────────────────

  function _resumoResposta(resBody) {
    if (!resBody) return null;
    if (typeof resBody === 'string') return resBody.slice(0, 200);
    if (Array.isArray(resBody)) {
      const item = resBody[0];
      return item ? `Array[${resBody.length}] campos: ${Object.keys(item).join(', ')}` : `Array[0]`;
    }
    if (typeof resBody === 'object') {
      const arr = resBody.resultado || resBody.content || resBody.conteudo || resBody.lista;
      if (Array.isArray(arr) && arr.length > 0)
        return `{...resultado: Array[${arr.length}]} campos: ${Object.keys(arr[0]).join(', ')}`;
      return `{campos: ${Object.keys(resBody).join(', ')}}`;
    }
    return resBody;
  }

  // ─── Atalhos de teclado (opcional) ───────────────────────────────────────
  // Shift+Alt+W → watchNext()   Shift+Alt+S → summary()
  document.addEventListener('keydown', e => {
    if (!e.shiftKey || !e.altKey) return;
    if (e.key === 'W') window.__pje.watchNext();
    if (e.key === 'S') window.__pje.summary();
  });

  // ─── Varredura inicial: performance entries já existentes ─────────────────
  (function seed() {
    const entries = performance.getEntriesByType('resource')
      .filter(e => API_FILTER.test(e.name))
      .slice(-100);
    entries.forEach(e => {
      registrar({
        ts:          e.startTime + performance.timeOrigin,
        method:      'GET',   // performance API não expõe método; assume GET
        url:         e.name,
        reqBody:     null,
        status:      e.responseStatus || 0,
        resBody:     null,    // corpo não disponível retroativamente
        duration:    Math.round(e.duration),
        urlTemplate: urlTemplate(e.name),
        _fromPerf:   true,
      });
    });
    if (entries.length > 0)
      console.log(`${TAG} Seed: ${entries.length} chamada(s) de API pré-existentes importadas do Performance API.`);
  })();

  // ─── Ajuda rápida ─────────────────────────────────────────────────────────
  console.group(`${TAG} Ativo ✅  (fetch + XHR interceptados, MutationObserver ligado)`);
  console.log(`  __pje.clickEl($0)            // clica no elemento e mostra o que disparou  ← NOVO`);
  console.log(`  __pje.live()                 // mostra só chamadas interceptadas (exclui seed)  ← NOVO`);
  console.log(`  __pje.fromEl($0)             // descobre endpoint a partir de elemento DOM`);
  console.log(`  __pje.search("texto")        // busca texto em todas as respostas`);
  console.log(`  __pje.watchNext()            // espera próximo clique e captura chamadas (5s)`);
  console.log(`  __pje.watchMutation($0)      // correlaciona mutações do elemento com API`);
  console.log(`  __pje.probe("/api/caminho")  // testa endpoint manualmente`);
  console.log(`  __pje.last(5)                // últimas N chamadas (inclui seed)`);
  console.log(`  __pje.summary()              // todos os endpoints — [seed] marcado`);
  console.log(`  __pje.export()               // copia log JSON para clipboard`);
  console.log(`  __pje.xsrf()                 // token XSRF atual`);
  console.log(`  Atalhos: Shift+Alt+W = watchNext | Shift+Alt+S = summary`);
  console.groupEnd();

})();
