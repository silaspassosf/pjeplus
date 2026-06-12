/**
 * IIFE de teste — Fluxo DOM: timeline (ata?) → expedientes → domicílio expirado/ciência automática → lembrete
 * Cole no console do browser em um processo PJe aberto.
 */
(async () => {
  // ── 1. ID do processo ─────────────────────────────────────────────────────
  const m = location.pathname.match(/\/processo\/(\d+)\//);
  if (!m) return console.error('[DOM-TEST] ID do processo não encontrado na URL:', location.pathname);
  const idProcesso = m[1];
  console.log('[DOM-TEST] Processo ID:', idProcesso);

  // ── 2. XSRF token ─────────────────────────────────────────────────────────
  const xsrf = decodeURIComponent(
    document.cookie.split(';').map(c => c.trim())
      .find(c => /^XSRF-TOKEN=/i.test(c))?.replace(/^XSRF-TOKEN=/i, '') || ''
  );
  const base = location.origin;
  const fetchJson = async (url) => {
    const res = await fetch(url, {
      credentials: 'include',
      headers: { 'Accept': 'application/json', ...(xsrf && { 'X-XSRF-TOKEN': xsrf }) },
    });
    if (!res.ok) { console.warn('[DOM-TEST] HTTP', res.status, url); return null; }
    return res.json();
  };

  // ── 3. Timeline — verificar Ata de Audiência ─────────────────────────────
  const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const tlUrl = `${base}/pje-comum-api/api/processos/id/${idProcesso}/timeline`
    + '?somenteDocumentosAssinados=false&buscarMovimentos=true&buscarDocumentos=true';
  const timeline = await fetchJson(tlUrl);
  if (Array.isArray(timeline)) {
    for (const item of timeline) {
      const texto = norm(item.tipo || '') + ' ' + norm(item.titulo || '');
      if (texto.includes('ata') && texto.includes('audienci')) {
        console.log('[DOM-TEST] Ata de audiência encontrada na timeline — nada a fazer.', item);
        return;
      }
    }
    console.log('[DOM-TEST] Timeline OK — sem ata de audiência, prosseguindo.');
  } else {
    console.warn('[DOM-TEST] Timeline não retornou array — continuando mesmo assim.', timeline);
  }

  // ── 5. Busca expedientes via API (paginado) ────────────────────────────────
  const expBase = `/pje-comum-api/api/processos/id/${idProcesso}/expedientes`;
  let todos = [];
  for (let pagina = 1; pagina <= 50; pagina++) {
    const json = await fetchJson(`${base}${expBase}?pagina=${pagina}&tamanhoPagina=100&instancia=1`);
    if (!json) break;
    const lista = json?.resultado || json || [];
    todos = todos.concat(lista);
    if (lista.length < 100) break;
  }
  console.log('[DOM-TEST] Total expedientes:', todos.length);

  // ── 6. Filtra: DOMICILIO_ELETRONICO + ciência automática ou prazo expirado ──
  const falhos = [];
  for (const exp of todos) {
    if ((exp.meioExpedienteEnum || '').toUpperCase() !== 'DOMICILIO_ELETRONICO') continue;
    const nome = (exp.nomePessoaParte || '').trim();
    if (!nome) continue;
    if (exp.cienciaViaSistema || exp.dataCiencia == null) {
      if (!falhos.includes(nome)) falhos.push(nome);
    }
  }
  console.log('[DOM-TEST] Empresas com falha DOM:', falhos);

  // ── 5. Verificar se lembrete já existe ────────────────────────────────────
  const titulosExistentes = [...document.querySelectorAll('mat-panel-title.post-it-titulo')]
    .map(el => el.textContent.trim());
  const jaTemLembrete = titulosExistentes.some(t =>
    ['Dom Eletronico', 'DomicEletr', 'DomElet'].some(kw => t.includes(kw))
  );
  if (jaTemLembrete) {
    console.log('[DOM-TEST] Lembrete DomicEletr já existe — nada a fazer.');
    return;
  }

  // ── 6. Monta conteúdo do lembrete ─────────────────────────────────────────
  const titulo = 'DomicEletr';
  let conteudo = 'Ciencia negativa Domicilio: Correio enviado:';
  if (falhos.length) conteudo += ` (${falhos.join(', ')})`;
  console.log('[DOM-TEST] Criando lembrete →', titulo, '/', conteudo);

  // ── 7. Abre menu hambúrguer ────────────────────────────────────────────────
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const clicar = async (selector, timeout = 8000) => {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      const el = document.querySelector(selector);
      if (el && !el.disabled) { el.click(); return true; }
      await sleep(200);
    }
    return false;
  };
  const esperar = async (selector, timeout = 5000) => {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      const el = document.querySelector(selector);
      if (el) return el;
      await sleep(200);
    }
    return null;
  };
  const preencher = async (el, valor) => {
    el.focus();
    el.value = '';
    el.dispatchEvent(new Event('input', { bubbles: true }));
    await sleep(100);
    // Angular reactive forms
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
      || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
    if (nativeInputValueSetter) nativeInputValueSetter.call(el, valor);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    await sleep(100);
  };

  if (!await clicar('#botao-menu')) {
    if (!await clicar('.fa-bars')) { console.error('[DOM-TEST] Menu hambúrguer não encontrado'); return; }
  }
  await sleep(800);

  // ── 8. Clica no botão de lembrete/post-it ────────────────────────────────
  const seletoresLembrete = [
    'pje-icone-post-it button',
    'button[aria-label*="Lembrete"]',
    'button[title*="Lembrete"]',
  ];
  let lembreteClicado = false;
  for (const sel of seletoresLembrete) {
    if (await clicar(sel, 3000)) { lembreteClicado = true; console.log('[DOM-TEST] Ícone lembrete:', sel); break; }
  }
  if (!lembreteClicado) { console.error('[DOM-TEST] Botão de lembrete não encontrado no menu'); return; }
  await sleep(800);

  // ── 9. Preenche campos do modal ───────────────────────────────────────────
  const elTitulo = await esperar('#tituloPostit', 5000);
  if (elTitulo) await preencher(elTitulo, titulo);

  const elConteudo = await esperar('#conteudoPostit', 5000);
  if (elConteudo) await preencher(elConteudo, conteudo);

  // ── 10. Salva ─────────────────────────────────────────────────────────────
  const seletoresSalvar = ['button[color="primary"]', '.mat-raised-button:not([disabled])', 'button[type="submit"]'];
  for (const sel of seletoresSalvar) {
    if (await clicar(sel, 3000)) { console.log('[DOM-TEST] Salvo via', sel); break; }
  }
  await sleep(800);

  // ── 11. Confirma presença do lembrete ─────────────────────────────────────
  const confirmado = [...document.querySelectorAll('mat-panel-title.post-it-titulo')]
    .some(el => el.textContent.includes('DomicEletr'));
  console.log('[DOM-TEST] Lembrete criado com sucesso?', confirmado);
})();
