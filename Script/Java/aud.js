/**
 * Script/Java/aud.js - Painel AUD Flutuante & Triagem de Audiências
 *
 * Instruções:
 *   Cole no Console ou execute via Bookmarklet em https://pje.trt2.jus.br/pjekz/painel/global
 *
 * Características:
 *   - Painel flutuante, arrastável (movável) pelo cabeçalho
 *   - Inicia RETRAÍDO por padrão (clique no título "Painel AUD" para expandir/minimizar)
 *   - Captura automática de XSRF-TOKEN e busca paginada de processos
 *   - Separação em Buckets A/B/C/D com visualização interativa no DOM
 */

(async function initAudPanel() {
  'use strict';

  const PANEL_ID = 'pje-aud-floating-panel';
  const STYLE_ID = 'pje-aud-panel-styles';

  // Se o painel já existe na página, apenas altera entre expandido/retraído
  const existingPanel = document.getElementById(PANEL_ID);
  if (existingPanel) {
    const headerTitle = existingPanel.querySelector('.aud-header-title');
    if (headerTitle) headerTitle.click();
    return;
  }

  // ─── 1. Estilização CSS ───────────────────────────────────────────────────
  if (!document.getElementById(STYLE_ID)) {
    const styleEl = document.createElement('style');
    styleEl.id = STYLE_ID;
    styleEl.textContent = `
      #${PANEL_ID} {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 999999;
        width: 360px;
        max-width: 90vw;
        background: #0f172a;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13px;
        overflow: hidden;
        transition: box-shadow 0.2s ease;
      }
      #${PANEL_ID} * {
        box-sizing: border-box;
      }
      .aud-header {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 10px 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: move;
        user-select: none;
        border-bottom: 1px solid #334155;
      }
      .aud-header-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 14px;
        color: #38bdf8;
        cursor: pointer;
        flex-grow: 1;
      }
      .aud-header-title:hover {
        color: #7dd3fc;
      }
      .aud-toggle-icon {
        font-size: 11px;
        transition: transform 0.2s ease;
        color: #94a3b8;
      }
      .aud-badge-retracted {
        font-size: 10px;
        background: #334155;
        color: #cbd5e1;
        padding: 2px 6px;
        border-radius: 10px;
        font-weight: 500;
      }
      .aud-header-controls {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .aud-btn-close {
        background: transparent;
        border: none;
        color: #94a3b8;
        font-size: 16px;
        line-height: 1;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 4px;
      }
      .aud-btn-close:hover {
        background: #ef4444;
        color: #ffffff;
      }
      .aud-body {
        padding: 12px;
        max-height: 75vh;
        overflow-y: auto;
        display: none; /* Inicia retraído por padrão */
        background: #0f172a;
      }
      .aud-body.expanded {
        display: block;
      }
      .aud-actions-bar {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
      }
      .aud-btn {
        flex: 1;
        padding: 7px 10px;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        transition: background 0.15s ease;
      }
      .aud-btn-primary {
        background: #0284c7;
        color: #ffffff;
      }
      .aud-btn-primary:hover {
        background: #0369a1;
      }
      .aud-btn-primary:disabled {
        background: #475569;
        cursor: not-allowed;
        opacity: 0.7;
      }
      .aud-btn-secondary {
        background: #334155;
        color: #e2e8f0;
      }
      .aud-btn-secondary:hover {
        background: #475569;
      }
      .aud-status {
        font-size: 11px;
        color: #94a3b8;
        margin-bottom: 10px;
        min-height: 16px;
      }
      .aud-buckets-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .aud-bucket-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        overflow: hidden;
      }
      .aud-bucket-header {
        padding: 8px 12px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        font-size: 12px;
      }
      .aud-bucket-header:hover {
        background: #334155;
      }
      .aud-bucket-count {
        background: #0f172a;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
      }
      .aud-bucket-list {
        padding: 8px 12px;
        border-top: 1px solid #334155;
        display: none;
        flex-direction: column;
        gap: 4px;
        max-height: 160px;
        overflow-y: auto;
      }
      .aud-bucket-list.open {
        display: flex;
      }
      .aud-process-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 6px;
        background: #0f172a;
        border-radius: 4px;
        font-family: monospace;
        font-size: 11px;
      }
      .aud-process-item:hover {
        background: #1e293b;
      }
      .aud-tag {
        font-size: 9px;
        padding: 1px 5px;
        border-radius: 3px;
        font-weight: 700;
        text-transform: uppercase;
      }
      .aud-tag-digital { background: #166534; color: #86efac; }
      .aud-tag-presencial { background: #9a3412; color: #ffedd5; }
      .aud-tag-hte { background: #1e40af; color: #bfdbfe; }
      
      /* Cores de borda por bucket */
      .aud-bucket-a { border-left: 4px solid #f59e0b; }
      .aud-bucket-b { border-left: 4px solid #22c55e; }
      .aud-bucket-c { border-left: 4px solid #f97316; }
      .aud-bucket-d { border-left: 4px solid #3b82f6; }
    `;
    document.head.appendChild(styleEl);
  }

  // ─── 2. Construção do DOM do Painel ───────────────────────────────────────
  const panel = document.createElement('div');
  panel.id = PANEL_ID;

  panel.innerHTML = `
    <div class="aud-header" id="aud-drag-header">
      <div class="aud-header-title" id="aud-toggle-btn" title="Clique para expandir ou recolher">
        <span>📌 Painel AUD</span>
        <span class="aud-toggle-icon" id="aud-toggle-icon">▼</span>
        <span class="aud-badge-retracted" id="aud-status-badge">Retraído</span>
      </div>
      <div class="aud-header-controls">
        <button class="aud-btn-close" id="aud-close-btn" title="Fechar painel">&times;</button>
      </div>
    </div>

    <div class="aud-body" id="aud-body">
      <div class="aud-actions-bar">
        <button class="aud-btn aud-btn-primary" id="aud-btn-run">▶ Executar Triagem</button>
        <button class="aud-btn aud-btn-secondary" id="aud-btn-copy">📋 Copiar JSON</button>
      </div>
      <div class="aud-status" id="aud-status-text">Clique em 'Executar Triagem' para iniciar.</div>

      <div class="aud-buckets-container">
        <div class="aud-bucket-card aud-bucket-a">
          <div class="aud-bucket-header" data-target="list-a">
            <span>Bucket A (Sem Audiência)</span>
            <span class="aud-bucket-count" id="count-a">0</span>
          </div>
          <div class="aud-bucket-list" id="list-a"></div>
        </div>

        <div class="aud-bucket-card aud-bucket-b">
          <div class="aud-bucket-header" data-target="list-b">
            <span>Bucket B (Aud + 100% Digital)</span>
            <span class="aud-bucket-count" id="count-b">0</span>
          </div>
          <div class="aud-bucket-list" id="list-b"></div>
        </div>

        <div class="aud-bucket-card aud-bucket-c">
          <div class="aud-bucket-header" data-target="list-c">
            <span>Bucket C (Aud sem 100% Digital)</span>
            <span class="aud-bucket-count" id="count-c">0</span>
          </div>
          <div class="aud-bucket-list" id="list-c"></div>
        </div>

        <div class="aud-bucket-card aud-bucket-d">
          <div class="aud-bucket-header" data-target="list-d">
            <span>Bucket D (HTE)</span>
            <span class="aud-bucket-count" id="count-d">0</span>
          </div>
          <div class="aud-bucket-list" id="list-d"></div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(panel);

  // ─── 3. Lógica de Drag & Minimize/Expand ──────────────────────────────────
  const dragHeader = document.getElementById('aud-drag-header');
  const toggleBtn  = document.getElementById('aud-toggle-btn');
  const bodyEl     = document.getElementById('aud-body');
  const toggleIcon = document.getElementById('aud-toggle-icon');
  const badgeEl    = document.getElementById('aud-status-badge');
  const closeBtn   = document.getElementById('aud-close-btn');

  let isCollapsed = true; // Inicia RETRAÍDO conforme solicitado
  let isDragging  = false;
  let startX = 0, startY = 0, initialLeft = 0, initialTop = 0;

  function toggleCollapse() {
    isCollapsed = !isCollapsed;
    if (isCollapsed) {
      bodyEl.classList.remove('expanded');
      toggleIcon.textContent = '▼';
      badgeEl.style.display = 'inline-block';
    } else {
      bodyEl.classList.add('expanded');
      toggleIcon.textContent = '▲';
      badgeEl.style.display = 'none';
    }
  }

  // Evento de fechar
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.remove();
  });

  // Toggle ao clicar no título
  toggleBtn.addEventListener('click', (e) => {
    if (!isDragging) {
      toggleCollapse();
    }
  });

  // Lógica para arrastar o painel (Drag)
  dragHeader.addEventListener('mousedown', (e) => {
    if (e.target.closest('#aud-close-btn')) return;

    isDragging = false;
    startX = e.clientX;
    startY = e.clientY;

    const rect = panel.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop  = rect.top;

    function onMouseMove(me) {
      const dx = me.clientX - startX;
      const dy = me.clientY - startY;

      if (Math.hypot(dx, dy) > 5) {
        isDragging = true;
      }

      if (isDragging) {
        panel.style.left = `${initialLeft + dx}px`;
        panel.style.top  = `${initialTop + dy}px`;
        panel.style.right = 'auto';
      }
    }

    function onMouseUp() {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      setTimeout(() => { isDragging = false; }, 50);
    }

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  // Toggle sanfona das listas de buckets
  panel.querySelectorAll('.aud-bucket-header').forEach(hdr => {
    hdr.addEventListener('click', () => {
      const targetId = hdr.getAttribute('data-target');
      const listEl = document.getElementById(targetId);
      if (listEl) listEl.classList.toggle('open');
    });
  });

  // ─── 4. Integração com Engine do PJe ──────────────────────────────────────
  const BASE      = location.origin;
  const URL_TODOS = BASE + '/pje-comum-api/api/agrupamentotarefas/processos/todos';
  const TIPOS     = new Set(['ATORD', 'ATSUM', 'ACUM', 'ACCUM', 'HTE']);
  const TAM       = 200;

  const btnRun    = document.getElementById('aud-btn-run');
  const btnCopy   = document.getElementById('aud-btn-copy');
  const statusTxt = document.getElementById('aud-status-text');

  async function capturarViaXHR() {
    return new Promise(resolve => {
      const origOpen      = XMLHttpRequest.prototype.open;
      const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
      const origSend      = XMLHttpRequest.prototype.send;

      let xsrf = '';
      let capturedBody = null;

      const restore = () => {
        XMLHttpRequest.prototype.open          = origOpen;
        XMLHttpRequest.prototype.setRequestHeader = origSetHeader;
        XMLHttpRequest.prototype.send          = origSend;
      };

      const timer = setTimeout(() => {
        restore();
        const m = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
        resolve({ xsrf: m ? decodeURIComponent(m[1]) : '', body: null });
      }, 6000);

      XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this._isAlvo = String(url).includes('agrupamentotarefas/processos/todos');
        return origOpen.apply(this, [method, url, ...rest]);
      };

      XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
        if (this._isAlvo && name.toLowerCase() === 'x-xsrf-token') {
          xsrf = value;
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
          const result = origSend.apply(this, arguments);
          resolve({ xsrf, body: capturedBody });
          return result;
        }
        return origSend.apply(this, arguments);
      };

      const card = [...document.querySelectorAll('mat-card.painel-item-padrao')]
        .find(c => c.textContent.includes('Novos Processos'));

      if (!card) {
        clearTimeout(timer);
        restore();
        const m = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
        resolve({ xsrf: m ? decodeURIComponent(m[1]) : '', body: null });
        return;
      }

      const alvo = card.querySelector('div[role="link"][aria-label*="processos"]') ||
                   card.querySelector('div[role="link"]') ||
                   card;
      alvo.click();
    });
  }

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
      statusTxt.textContent = `Buscando processos (Página ${pagina})...`;
      const body = { ...baseBody, pagina, tamanhoPagina: TAM };

      let resp;
      try {
        resp = await fetch(URL_TODOS, {
          method: 'POST', credentials: 'include', headers: H(),
          body: JSON.stringify(body)
        });
      } catch (e) { break; }

      if (!resp || !resp.ok) break;

      const dados = await resp.json();
      const lista = asArray(dados);
      acum.push(...lista);
      if (lista.length < TAM) break;
      pagina++;
    }
    return acum;
  }

  function filtrar(lista) {
    return lista.filter(p => {
      const tarefa = (p.nomeTarefa || p.descricaoTarefa || p.tarefa || '').toLowerCase();
      if (!tarefa.includes('triagem inicial')) return false;
      const tipo = ((p.classeJudicial?.sigla) || (p.classe?.sigla) || p.tipo || '').toUpperCase();
      return TIPOS.has(tipo);
    });
  }

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

  function renderList(listId, items) {
    const listEl = document.getElementById(listId);
    if (!listEl) return;
    listEl.innerHTML = '';
    items.forEach(p => {
      const itemEl = document.createElement('div');
      itemEl.className = 'aud-process-item';

      let tagClass = 'aud-tag-presencial';
      let tagText = p.tipo;

      if (p.tipo === 'HTE') tagClass = 'aud-tag-hte';
      else if (p.digital) tagClass = 'aud-tag-digital';

      itemEl.innerHTML = `
        <span>${p.numero}</span>
        <span class="aud-tag ${tagClass}">${tagText}</span>
      `;
      listEl.appendChild(itemEl);
    });
  }

  async function executarTriagem() {
    btnRun.disabled = true;
    statusTxt.textContent = 'Interceptando token XSRF...';

    const { xsrf, body: bodyCapturado } = await capturarViaXHR();
    const baseBody = bodyCapturado
      ? (({ pagina, tamanhoPagina, ...rest }) => rest)(bodyCapturado)
      : { idAgrupamento: 10 };

    statusTxt.textContent = 'Carregando lista de tarefas...';
    const todos     = await buscarTodos(baseBody, xsrf);
    const filtrados = filtrar(todos);

    statusTxt.textContent = `Analisando audiências (${filtrados.length} processos)...`;

    const A = [], B = [], C = [], D = [];
    let count = 0;

    for (const p of filtrados) {
      count++;
      statusTxt.textContent = `Verificando ${count}/${filtrados.length}...`;

      const id      = p.idProcesso || p.id;
      const numero  = p.numero || p.numeroProcesso || '';
      const tipo    = ((p.classeJudicial?.sigla) || (p.classe?.sigla) || p.tipo || '').toUpperCase();
      const digital = p.juizoDigital === true;
      const info    = { numero, id, tipo, digital };

      if (tipo === 'HTE') {
        D.push(info);
      } else {
        const aud = await temAud(id, xsrf);
        if (!aud) A.push(info);
        else if (digital) B.push(info);
        else C.push(info);
      }
    }

    const buckets = { A, B, C, D };
    window.__audBuckets = buckets;

    document.getElementById('count-a').textContent = A.length;
    document.getElementById('count-b').textContent = B.length;
    document.getElementById('count-c').textContent = C.length;
    document.getElementById('count-d').textContent = D.length;

    renderList('list-a', A);
    renderList('list-b', B);
    renderList('list-c', C);
    renderList('list-d', D);

    statusTxt.textContent = `Triagem concluída! Total: ${filtrados.length} processos.`;
    badgeEl.textContent = `A:${A.length} | B:${B.length} | C:${C.length} | D:${D.length}`;
    btnRun.disabled = false;
  }

  btnRun.addEventListener('click', executarTriagem);

  btnCopy.addEventListener('click', () => {
    if (window.__audBuckets) {
      navigator.clipboard.writeText(JSON.stringify(window.__audBuckets, null, 2));
      statusTxt.textContent = 'JSON copiado para a área de transferência!';
    } else {
      statusTxt.textContent = 'Execute a triagem primeiro para copiar.';
    }
  });

  console.log('[AUD_PANEL] Painel AUD inicializado (retraído por padrão).');
})();
