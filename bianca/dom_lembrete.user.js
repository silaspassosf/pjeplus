// ==UserScript==
// @name         DOM Eletrônico — Bianca
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Botão DOM no detalhe do processo: timeline → expedientes → lembrete DomicEletr
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje1g.trt2.jus.br/pjekz/processo/*/detalhe*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ── Constantes ────────────────────────────────────────────────────────────
  const PAINEL_ID = 'bianca-dom-painel';
  const LOG = (...a) => console.log('[DOM-Bianca]', ...a);

  // ── Helpers de DOM ────────────────────────────────────────────────────────
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
    // Padrão Fix/core.py: setter do prototype + eventos padrão
    if (!el) return;
    
    try { el.focus(); } catch (e) { /* ignorar */ }

    // Estratégia padrão do projeto: getter HTMLInputElement.prototype.value
    try {
      const isTA = el instanceof HTMLTextAreaElement;
      const proto = isTA ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) {
        setter.call(el, valor);
      } else {
        el.value = valor;
      }
    } catch (e) {
      // Fallback: atribuição simples
      el.value = valor;
    }

    // Disparar eventos padrão do Fix (input, change, blur)
    try {
      el.dispatchEvent(new Event('input',  { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.dispatchEvent(new Event('blur',   { bubbles: true }));
    } catch (e) {
      LOG('preencher: erro ao disparar eventos:', e.message);
    }

    await sleep(100);
  };

  // ── API helper ────────────────────────────────────────────────────────────
  const xsrf = () => decodeURIComponent(
    document.cookie.split(';').map(c => c.trim())
      .find(c => /^XSRF-TOKEN=/i.test(c))?.replace(/^XSRF-TOKEN=/i, '') || ''
  );

  const fetchJson = async (url) => {
    const tok = xsrf();
    const res = await fetch(url, {
      credentials: 'include',
      headers: { 'Accept': 'application/json', ...(tok && { 'X-XSRF-TOKEN': tok }) },
    });
    if (!res.ok) { LOG('HTTP', res.status, url); return null; }
    return res.json();
  };

  // ── Normaliza texto (remove acentos, lowercase) ───────────────────────────
  const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  // ── Função: verificar Ata de Audiência na timeline ────────────────────────
  async function temAtaAudiencia(idProcesso) {
    const url = `${location.origin}/pje-comum-api/api/processos/id/${idProcesso}/timeline`
      + '?somenteDocumentosAssinados=false&buscarMovimentos=true&buscarDocumentos=true';
    const tl = await fetchJson(url);
    if (!Array.isArray(tl)) { LOG('Timeline inválida:', tl); return false; }
    for (const item of tl) {
      const txt = norm(item.tipo || '') + ' ' + norm(item.titulo || '');
      if (txt.includes('ata') && txt.includes('audienci')) {
        LOG('Ata de audiência encontrada na timeline:', item.titulo || item.tipo);
        return true;
      }
    }
    return false;
  }

  // ── Função: buscar empresas com falha DOM via expedientes ─────────────────
  async function checarEmpresasDom(idProcesso) {
    const base = `${location.origin}/pje-comum-api/api/processos/id/${idProcesso}/expedientes`;
    let todos = [];
    for (let pagina = 1; pagina <= 50; pagina++) {
      const json = await fetchJson(`${base}?pagina=${pagina}&tamanhoPagina=100&instancia=1`);
      if (!json) break;
      const lista = json?.resultado || (Array.isArray(json) ? json : []);
      todos = todos.concat(lista);
      if (lista.length < 100) break;
    }
    LOG('Total expedientes:', todos.length);
    const falhos = [];
    for (const exp of todos) {
      if ((exp.meioExpedienteEnum || '').toUpperCase() !== 'DOMICILIO_ELETRONICO') continue;
      const nome = (exp.nomePessoaParte || '').trim();
      if (!nome) continue;
      if (exp.cienciaViaSistema || exp.dataCiencia == null) {
        if (!falhos.includes(nome)) falhos.push(nome);
      }
    }
    return falhos;
  }

  // ── Função: criar lembrete DomicEletr ────────────────────────────────────
  async function criarLembrete(titulo, conteudo) {
    if (!await clicar('#botao-menu')) {
      if (!await clicar('.fa-bars', 4000)) { LOG('Menu hambúrguer não encontrado'); return false; }
    }
    await sleep(800);

    const seletoresLembrete = [
      'pje-icone-post-it button',
      'button[aria-label*="Lembrete"]',
      'button[title*="Lembrete"]',
    ];
    let clicado = false;
    for (const sel of seletoresLembrete) {
      if (await clicar(sel, 3000)) { clicado = true; LOG('Ícone lembrete via:', sel); break; }
    }
    if (!clicado) { LOG('Botão de lembrete não encontrado no menu'); return false; }
    await sleep(800);

    const elTitulo   = await esperar('#tituloPostit', 5000);
    const elConteudo = await esperar('#conteudoPostit', 5000);
    if (elTitulo)   await preencher(elTitulo, titulo);
    if (elConteudo) await preencher(elConteudo, conteudo);
    await sleep(300);

    // Salvar: buscar botão "Salvar" dentro do modal (mat-dialog-content)
    // Usar seletor mais específico: button dentro de mat-dialog com mat-raised-button + color="primary"
    const seletoresSalvar = [
      'mat-dialog-container button[mat-raised-button][color="primary"]',
      '.mat-dialog-container button[mat-raised-button][color="primary"]',
      'button[mat-raised-button][color="primary"]:not([disabled])',
      'button[color="primary"]:not([disabled])',
    ];
    
    let salvou = false;
    for (const sel of seletoresSalvar) {
      if (await clicar(sel, 3000)) { 
        LOG('Salvo via:', sel); 
        salvou = true;
        break; 
      }
    }
    
    if (!salvou) {
      LOG('Botão Salvar não encontrado no modal');
      return false;
    }
    
    await sleep(800);
    return true;
  }

  // ── Função: remover chips DOM Eletrônico ─────────────────────────────────
  async function removerChipsDom(setStatus) {
    let total = 0;
    // Requery a cada iteração pois o Angular remove o nó após exclusão
    while (true) {
      const chips = [...document.querySelectorAll('mat-chip')];
      let btnRemover = null;
      for (const chip of chips) {
        // Rótulo: spans que não estão dentro de button
        const spans = [...chip.querySelectorAll('span')].filter(s => !s.closest('button'));
        const texto = norm(spans.map(s => s.textContent).join(' '));
        if (texto.includes('domicil') && texto.includes('eletr')) {
          btnRemover = chip.querySelector('button.etq-botao-excluir, button[mattooltip*="Remover Chip"]');
          if (btnRemover) break;
        }
      }
      if (!btnRemover) break;

      setStatus(`⏳ Removendo chip DOM… (${total + 1})`, '#888');
      btnRemover.click();
      await sleep(800);

      const simBtn = [...document.querySelectorAll('button.mat-primary, button[color="primary"]')]
        .find(b => b.textContent.trim() === 'Sim');
      if (simBtn) { simBtn.click(); total++; }
      else { LOG('Botão Sim não encontrado — abortando remoção de chips'); break; }
      await sleep(1000);
    }
    LOG('removerChipsDom:', total, 'chip(s) removido(s)');
    return total;
  }

  // ── Função: excluir comentários Bianca ─────────────────────────────────
  async function deletarComentariosBianca(setStatus) {
    let total = 0;
    // Requery a cada iteração pois o Angular remove o nó após exclusão
    while (true) {
      const rows = [...document.querySelectorAll('tbody tr')];
      let btnExcluir = null;
      for (const row of rows) {
        const desc = row.querySelector('.descricao');
        if (desc && desc.textContent.toLowerCase().includes('bianca')) {
          btnExcluir = row.querySelector('button[aria-label="Excluir Comentário"]');
          if (btnExcluir) break;
        }
      }
      if (!btnExcluir) break;

      setStatus(`⏳ Excluindo… (${total + 1})`, '#888');
      btnExcluir.click();
      await sleep(800);

      // Confirmar no dialog — botão mat-primary com texto "Sim"
      const simBtn = [...document.querySelectorAll('button.mat-primary, button[color="primary"]')]
        .find(b => b.textContent.trim() === 'Sim');
      if (simBtn) { simBtn.click(); total++; }
      else { LOG('Botão Sim não encontrado — abortando'); break; }
      await sleep(1000);
    }
    setStatus(
      total ? `✅ ${total} comentário(s) excluído(s)` : '⚠️ Nenhum comentário Bianca encontrado',
      total ? '#28a745' : '#e67e22'
    );
    LOG('deletarComentariosBianca:', total, 'excluído(s)');
  }

  // ── Fluxo principal ───────────────────────────────────────────────────────
  async function executarFluxoDom(setStatus) {
    const m = location.pathname.match(/\/processo\/(\d+)\//);
    if (!m) { setStatus('❌ ID não encontrado na URL', 'red'); return; }
    const idProcesso = m[1];
    LOG('Processo ID:', idProcesso);

    // 0. Remover chips DOM Eletrônico
    setStatus('⏳ Removendo chips DOM…', '#888');
    await removerChipsDom(setStatus);
    await sleep(300);

    // 1. Limpar comentários Bianca antes de qualquer verificação
    setStatus('⏳ Limpando comentários Bianca…', '#888');
    await deletarComentariosBianca(setStatus);

    // 2. Timeline — ata de audiência?
    setStatus('⏳ Verificando timeline…', '#888');
    if (await temAtaAudiencia(idProcesso)) {
      setStatus('✅ Tem ata — nada a fazer', '#28a745');
      LOG('Ata de audiência detectada — encerrando.');
      return;
    }
    LOG('Sem ata de audiência, prosseguindo.');

    // 3. Expedientes DOM com falha
    setStatus('⏳ Buscando expedientes…', '#888');
    const falhos = await checarEmpresasDom(idProcesso);

    LOG('Empresas com falha DOM:', falhos);

    // 4. Verificar lembrete existente
    const jaTemLembrete = [...document.querySelectorAll('mat-panel-title.post-it-titulo')]
      .some(el => ['Dom Eletronico', 'DomicEletr', 'DomElet'].some(kw => el.textContent.includes(kw)));
    if (jaTemLembrete) {
      setStatus('✅ Lembrete já existe', '#28a745');
      LOG('Lembrete DomicEletr já existe.');
      return;
    }

    // 5. Criar lembrete
    let conteudo = 'Negativo - repetido via correio:';
    if (falhos.length) conteudo += ` (${falhos.join(', ')})`;
    setStatus('⏳ Criando lembrete…', '#888');
    LOG('Criando lembrete →', 'DomicEletr', '/', conteudo);
    const ok = await criarLembrete('DomicEletr', conteudo);

    // 6. Confirmar
    if (ok) {
      const confirmado = [...document.querySelectorAll('mat-panel-title.post-it-titulo')]
        .some(el => el.textContent.includes('DomicEletr'));
      setStatus(confirmado ? '✅ Lembrete criado!' : '⚠️ Salvo (não confirmado)', confirmado ? '#28a745' : '#e67e22');
    } else {
      setStatus('❌ Falha ao criar lembrete', 'red');
    }
  }

  // ── UI: painel flutuante ──────────────────────────────────────────────────
  function criarPainel() {
    document.getElementById(PAINEL_ID)?.remove();

    const painel = document.createElement('div');
    painel.id = PAINEL_ID;
    painel.style.cssText = [
      'position:fixed', 'bottom:170px', 'right:230px', 'z-index:99999',
      'background:#fff', 'border:2px solid #333', 'border-radius:8px',
      'box-shadow:0 8px 32px rgba(0,0,0,.25)', 'padding:10px 12px',
      'font-family:sans-serif', 'min-width:180px', 'user-select:none',
    ].join(';');

    // Título
    const titulo = document.createElement('div');
    titulo.textContent = 'DOM Eletrônico';
    titulo.style.cssText = 'font-weight:bold;margin-bottom:8px;color:#333;font-size:12px;' +
      'text-align:center;border-bottom:1px solid #ddd;padding-bottom:6px;cursor:move;';
    painel.appendChild(titulo);

    // Container para botões
    const containerBotoes = document.createElement('div');
    containerBotoes.style.cssText = 'display:flex;gap:6px;flex-direction:column;';
    painel.appendChild(containerBotoes);

    // Botão "Executar"
    const btn = document.createElement('button');
    btn.textContent = '▶ Executar';
    btn.style.cssText = 'width:100%;padding:7px 6px;background:#6f42c1;color:#fff;border:none;' +
      'border-radius:4px;cursor:pointer;font-weight:bold;font-size:11px;transition:opacity .15s;';
    btn.onmouseenter = () => { btn.style.opacity = '.85'; };
    btn.onmouseleave = () => { btn.style.opacity = '1'; };
    containerBotoes.appendChild(btn);

    // Botão "Limpar"
    const btnLimpar = document.createElement('button');
    btnLimpar.textContent = '🧹 Limpar';
    btnLimpar.style.cssText = 'width:100%;padding:7px 6px;background:#e67e22;color:#fff;border:none;' +
      'border-radius:4px;cursor:pointer;font-weight:bold;font-size:11px;transition:opacity .15s;';
    btnLimpar.onmouseenter = () => { btnLimpar.style.opacity = '.85'; };
    btnLimpar.onmouseleave = () => { btnLimpar.style.opacity = '1'; };
    containerBotoes.appendChild(btnLimpar);

    // Status
    const status = document.createElement('div');
    status.style.cssText = 'margin-top:7px;font-size:10px;text-align:center;color:#888;min-height:14px;';
    painel.appendChild(status);

    const setStatus = (msg, cor = '#888') => { status.textContent = msg; status.style.color = cor; };

    // Click handler: Executar
    btn.onclick = async () => {
      btn.disabled = true; btn.style.opacity = '.5'; btn.textContent = '⏳ Rodando…';
      btnLimpar.disabled = true;
      setStatus('', '#888');
      try {
        await executarFluxoDom(setStatus);
      } catch (e) {
        setStatus('❌ Erro: ' + e.message, 'red');
        LOG('Erro no fluxo:', e);
      } finally {
        btn.disabled = false; btn.style.opacity = '1'; btn.textContent = '▶ Executar';
        btnLimpar.disabled = false;
      }
    };

    // Click handler: Limpar
    btnLimpar.onclick = async () => {
      btnLimpar.disabled = true; btnLimpar.style.opacity = '.5'; btnLimpar.textContent = '⏳ Limpando…';
      btn.disabled = true;
      setStatus('', '#888');
      try {
        setStatus('⏳ Excluindo comentários Bianca…', '#888');
        await deletarComentariosBianca(setStatus);

        setStatus('⏳ Removendo chips DOM…', '#888');
        await removerChipsDom(setStatus);

        setStatus('✅ Limpeza concluída!', '#28a745');
      } catch (e) {
        setStatus('❌ Erro: ' + e.message, 'red');
        LOG('Erro ao limpar:', e);
      } finally {
        btnLimpar.disabled = false; btnLimpar.style.opacity = '1'; btnLimpar.textContent = '🧹 Limpar';
        btn.disabled = false;
      }
    };

    // Arrastar pelo título
    let ox = 0, oy = 0, drag = false;
    titulo.addEventListener('mousedown', e => {
      drag = true; ox = e.clientX - painel.offsetLeft; oy = e.clientY - painel.offsetTop;
      e.preventDefault();
    });
    document.addEventListener('mousemove', e => {
      if (!drag) return;
      painel.style.left   = (e.clientX - ox) + 'px';
      painel.style.top    = (e.clientY - oy) + 'px';
      painel.style.right  = 'auto';
      painel.style.bottom = 'auto';
    });
    document.addEventListener('mouseup', () => { drag = false; });

    document.body.appendChild(painel);
  }

  // ── Inicialização + monitor SPA ───────────────────────────────────────────
  function init() {
    if (!/\/processo\/\d+\/detalhe/.test(location.pathname)) return;
    if (document.getElementById(PAINEL_ID)) return;
    criarPainel();
    LOG('Painel DOM criado.');
  }

  // MutationObserver para navegação SPA Angular
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      document.getElementById(PAINEL_ID)?.remove();
      setTimeout(init, 600);
    }
  }).observe(document.body, { childList: true, subtree: true });

  // Boot inicial
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(init, 800));
  } else {
    setTimeout(init, 800);
  }
})();
