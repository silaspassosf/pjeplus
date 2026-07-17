/**
 * aud_triagem_buckets_iife.js
 *
 * Cole no console em https://pje.trt2.jus.br/pjekz/painel/global
 * (onde o mat-card "Novos Processos" está visível).
 *
 * Estratégia:
 *   1. Patch XMLHttpRequest (Angular usa XHR, não fetch)
 *      -> captura X-XSRF-TOKEN e body real que o Angular envia
 *   2. Usa token + body para busca paginada paginada via fetch
 *   3. Filtra por tarefa "Triagem Inicial" + tipos ATOrd/ATSum/ACum/HTE
 *   4. Para cada processo: GET audiências pendentes
 *   5. Monta buckets A/B/C/D -> window.__audBuckets
 *
 * Exportar: copy(JSON.stringify(window.__audBuckets, null, 2))
 */

(async function audTriagemBuckets() {
  const BASE      = location.origin;
  const URL_TODOS = BASE + '/pje-comum-api/api/agrupamentotarefas/processos/todos';
  const TIPOS     = new Set(['ATORD', 'ATSUM', 'ACUM', 'ACCUM', 'HTE']);
  const TAM       = 200;

  // ─── 1. Capturar XSRF + body via XHR intercept + click ──────────────────
  async function capturarViaXHR() {
    return new Promise(resolve => {
      const origOpen        = XMLHttpRequest.prototype.open;
      const origSetHeader   = XMLHttpRequest.prototype.setRequestHeader;
      const origSend        = XMLHttpRequest.prototype.send;

      let xsrf = '';
      let capturedBody = null;

      const restore = () => {
        XMLHttpRequest.prototype.open          = origOpen;
        XMLHttpRequest.prototype.setRequestHeader = origSetHeader;
        XMLHttpRequest.prototype.send          = origSend;
      };

      const timer = setTimeout(() => {
        restore();
        console.warn('[AUD_IIFE] Timeout XHR — usando XSRF de cookie (pode falhar)');
        // tentar ler do cookie como último recurso
        const m = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
        resolve({ xsrf: m ? decodeURIComponent(m[1]) : '', body: null });
      }, 8000);

      // Marcar quais XHRs são para o endpoint alvo
      XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this._isAlvo = String(url).includes('agrupamentotarefas/processos/todos');
        return origOpen.apply(this, [method, url, ...rest]);
      };

      XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
        if (this._isAlvo && name.toLowerCase() === 'x-xsrf-token') {
          xsrf = value;
          console.log('[AUD_IIFE] XSRF capturado via XHR intercept:', xsrf ? xsrf.substring(0, 12) + '…' : '(vazio)');
        }
        return origSetHeader.apply(this, arguments);
      };

      XMLHttpRequest.prototype.send = function(data) {
        if (this._isAlvo) {
          if (data) {
            try { capturedBody = JSON.parse(data); } catch { capturedBody = data; }
          }
          clearTimeout(timer);
          restore();
          console.log('[AUD_IIFE] Body POST capturado:', JSON.stringify(capturedBody));
          // Deixar a requisição original do Angular continuar normalmente
          const result = origSend.apply(this, arguments);
          resolve({ xsrf, body: capturedBody });
          return result;
        }
        return origSend.apply(this, arguments);
      };

      // Localizar e clicar no card "Novos Processos"
      const card = [...document.querySelectorAll('mat-card.painel-item-padrao')]
        .find(c => c.textContent.includes('Novos Processos'));

      if (!card) {
        clearTimeout(timer);
        restore();
        console.warn('[AUD_IIFE] Card não encontrado');
        resolve({ xsrf: '', body: null });
        return;
      }

      const alvo = card.querySelector('div[role="link"][aria-label*="processos"]') ||
                   card.querySelector('div[role="link"]') ||
                   card;
      console.log('[AUD_IIFE] Clicando:', alvo.getAttribute('aria-label') || alvo.tagName);
      alvo.click();
    });
  }

  // ─── 2. Busca paginada (fetch com XSRF real) ─────────────────────────────
  function asArray(d) {
    if (!d) return [];
    if (Array.isArray(d)) return d;
    return d.lista || d.content || d.processos || d.resultado || d.conteudo || d.dados || [];
  }

  async function buscarTodos(baseBody, xsrf) {
    const H = () => ({
      'Content-Type': 'application/json',
      'X-Grau-Instancia': '1',
      'X-XSRF-TOKEN': xsrf
    });
    const acum = [];
    let pagina = 1;

    while (true) {
      const body = { ...baseBody, pagina, tamanhoPagina: TAM };
      console.log(`[AUD_IIFE] POST p${pagina}`, body);

      let resp;
      try {
        resp = await fetch(URL_TODOS, {
          method: 'POST', credentials: 'include', headers: H(),
          body: JSON.stringify(body)
        });
      } catch (e) { console.error('[AUD_IIFE] Rede:', e.message); break; }

      if (!resp.ok) {
        const txt = await resp.text().catch(() => '');
        console.warn(`[AUD_IIFE] HTTP ${resp.status}`, txt);
        break;
      }

      const dados = await resp.json();
      const lista = asArray(dados);
      console.log(`[AUD_IIFE] p${pagina}: ${lista.length}`,
        lista[0] ? '| campos: ' + Object.keys(lista[0]).join(', ') : '');
      acum.push(...lista);
      if (lista.length < TAM) break;
      pagina++;
    }
    return acum;
  }

  // ─── 3. Filtros ───────────────────────────────────────────────────────────
  function filtrar(lista) {
    return lista.filter(p => {
      const tarefa = (p.nomeTarefa || p.descricaoTarefa || p.tarefa || '').toLowerCase();
      if (!tarefa.includes('triagem inicial')) return false;
      const tipo = ((p.classeJudicial?.sigla) || (p.classe?.sigla) || p.tipo || '').toUpperCase();
      return TIPOS.has(tipo);
    });
  }

  // ─── 4. Audiências + buckets ──────────────────────────────────────────────
  async function temAud(id, xsrf) {
    try {
      const r = await fetch(
        `${BASE}/pje-comum-api/api/processos/id/${id}/audiencias?status=M`,
        { credentials: 'include', headers: { 'X-Grau-Instancia': '1', 'X-XSRF-TOKEN': xsrf } }
      );
      if (!r.ok) return false;
      const d = await r.json();
      return Array.isArray(d) && d.length > 0;
    } catch { return false; }
  }

  async function montar(processos, xsrf) {
    const A = [], B = [], C = [], D = [];
    for (const p of processos) {
      const id      = p.idProcesso || p.id;
      const numero  = p.numero || p.numeroProcesso || '';
      const tipo    = ((p.classeJudicial?.sigla) || (p.classe?.sigla) || p.tipo || '').toUpperCase();
      const digital = p.juizoDigital === true;
      const info    = { numero, id, tipo, digital };

      if (tipo === 'HTE') { D.push(info); console.log('[AUD_IIFE] D:', numero); continue; }

      const aud = await temAud(id, xsrf);
      const bucket = !aud ? 'A' : digital ? 'B' : 'C';
      ({ A, B, C }[bucket]).push(info);
      console.log(`[AUD_IIFE] ${bucket}: ${numero} | ${tipo} | digital:${digital} | aud:${aud}`);
    }
    return { A, B, C, D };
  }

  // ─── Execução ─────────────────────────────────────────────────────────────
  console.log('[AUD_IIFE] Iniciando — patch XHR + click...');
  const { xsrf, body: bodyCapturado } = await capturarViaXHR();

  const baseBody = bodyCapturado
    ? (({ pagina, tamanhoPagina, ...rest }) => rest)(bodyCapturado)
    : { idAgrupamento: 10 };

  console.log('[AUD_IIFE] XSRF:', xsrf ? xsrf.substring(0, 12) + '…' : '(vazio — pode falhar)');
  console.log('[AUD_IIFE] Base body:', baseBody);

  const todos     = await buscarTodos(baseBody, xsrf);
  const filtrados = filtrar(todos);
  console.log(`[AUD_IIFE] Total: ${todos.length} | filtrados: ${filtrados.length}`);

  const buckets = await montar(filtrados, xsrf);

  console.log('\n[AUD_IIFE] === BUCKETS ===');
  console.log('A (sem aud):    ', buckets.A.length, buckets.A.map(p => p.numero));
  console.log('B (aud + 100%): ', buckets.B.length, buckets.B.map(p => p.numero));
  console.log('C (aud s/100%): ', buckets.C.length, buckets.C.map(p => p.numero));
  console.log('D (HTE):        ', buckets.D.length, buckets.D.map(p => p.numero));

  window.__audBuckets = buckets;
  console.log('[AUD_IIFE] window.__audBuckets disponível.');
  return buckets;
})();