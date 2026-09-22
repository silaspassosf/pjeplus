// ==UserScript==
// @name         eCarta API Hunter — Relatório com Auditoria de Falsos Positivos
// @namespace    pjeplus
// @version      1.0
// @description  GET consultarProcesso → POST JSF detalhes → detecta "entregue" que é devolução
// @author       PJePlus
// @match        https://aplicacoes1.trt2.jus.br/eCarta-web/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function () {
  'use strict';

  if (window.__ecartaHunter) { window.__ecartaHunter.toggle(); return; }

  const BASE = 'https://aplicacoes1.trt2.jus.br/eCarta-web/';

  const C = {
    BG: '#181825', SURFACE: '#11111b', TEXT: '#cdd6f4', BORDER: '#313244',
    ACCENT: '#89b4fa', OK: '#a6e3a1', ERR: '#f38ba8', MUTED: '#6c7086',
    WARN: '#fab387', YELLOW: '#f9e2af',
  };

  // ─── Padrões de devolução (falso positivo) ───
  const RE_DEVOLUCAO = /objeto\s+(ser[áa]\s+devolvido|saiu\s+para\s+entrega\s+ao\s+remetente|entregue\s+ao\s+remetente)|devolvido\s+ao\s+remetente/i;
  const RE_STATUS_ENTREGUE = /entregue\s+ao\s+destinat[áa]rio/i;
  const RE_STATUS_DEVOLVIDO = /devolvid[oa]/i;

  // ─── Helpers ───
  const $ = (sel, ctx) => (ctx || document).querySelector(sel);
  const $$ = (sel, ctx) => [...(ctx || document).querySelectorAll(sel)];

  function copyText(text) {
    const ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
    document.body.appendChild(ta); ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch (e) { /* noop */ }
    document.body.removeChild(ta);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ─── Parsers ───
  function parseTabelaProcesso(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const tbody = doc.querySelector('#main\\:tabDoc_data') ||
      [...doc.querySelectorAll('tbody')].find(t => t.id && t.id.includes('tabDoc') && t.id.includes('data'));
    if (!tbody) return [];

    return $$('tr', tbody).map(tr => {
      const tds = $$('td', tr);
      if (tds.length < 4) return null;
      const get = i => tds[i] ? tds[i].textContent.trim() : '';

      let rastreio = '', rastreioLink = '';
      const objetoTd = tds[4];
      if (objetoTd) {
        const span = objetoTd.querySelector('span[id$=":rastreamento"]');
        if (span) {
          rastreio = span.textContent.trim();
          const a = span.closest('a');
          if (a && a.href) rastreioLink = a.href.startsWith('/') ? 'https://aplicacoes1.trt2.jus.br' + a.href : a.href;
        } else {
          const a = objetoTd.querySelector('a[href*="consultarObjeto"]');
          if (a) {
            const m = a.href.match(/codigo=([^&]+)/);
            if (m) { rastreio = decodeURIComponent(m[1]); rastreioLink = a.href; }
          }
        }
        if (!rastreio) {
          const m = get(4).match(/^([A-Z]{2}\d{9}BR)/);
          if (m) { rastreio = m[1]; rastreioLink = BASE + 'consultarObjeto.xhtml?codigo=' + rastreio; }
        }
      }

      return {
        dataEnvio: get(0), dataEntrega: get(1), processo: get(2),
        idPje: get(3), objeto: rastreio || get(4), objetoLink: rastreioLink,
        status: get(5), destinatario: get(6), orgaoJulgador: get(7),
      };
    }).filter(Boolean);
  }

  function parseDetalhesDoPartialResponse(xmlText) {
    // Extrai <update id="detalhesObjeto"> do <partial-response>
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'application/xml');
    if (xmlDoc.querySelector('parsererror')) return null;

    for (const upd of xmlDoc.querySelectorAll('update')) {
      if (upd.getAttribute('id') !== 'detalhesObjeto') continue;
      const innerHtml = upd.textContent || '';
      if (!innerHtml) continue;

      const doc = new DOMParser().parseFromString(innerHtml, 'text/html');
      const tbody = doc.querySelector('#tabDetalhesObjeto_data') ||
        [...doc.querySelectorAll('tbody')].find(t => t.id && t.id.includes('tabDetalhesObjeto'));

      if (!tbody) return null;

      return $$('tr', tbody).map(tr => {
        const tds = $$('td', tr);
        if (tds.length < 2) return null;
        if (tds[0].textContent.includes('Nenhum resultado')) return null;

        // descrição: junta texto com <br> → " | "
        let descricao = '';
        const descTd = tds[1];
        for (const node of descTd.childNodes) {
          if (node.nodeType === 3) descricao += node.textContent.trim();
          else if (node.tagName === 'BR') descricao += ' | ';
          else descricao += node.textContent.trim();
        }
        descricao = descricao.replace(/\s+/g, ' ').trim();

        return {
          dataEvento: tds[0].textContent.trim(),
          descricao: descricao || tds[1].textContent.trim(),
          cidadeUf: tds[2] ? tds[2].textContent.trim() : '',
        };
      }).filter(Boolean);
    }
    return null;
  }

  function extrairViewState(html) {
    const m = html.match(/name="javax\.faces\.ViewState"[^>]+value="([^"]+)"/);
    return m ? m[1] : '';
  }

  function extrairIndicesRastreamento(html) {
    const indices = [];
    const re = /id="main:tabDoc:(\d+):rastreamento"/g;
    let m;
    while ((m = re.exec(html)) !== null) indices.push(parseInt(m[1], 10));
    return indices;
  }

  // ─── Chamadas API ───
  async function fetchProcesso(codigo) {
    const url = BASE + 'consultarProcesso.xhtml?codigo=' + encodeURIComponent(codigo);
    const resp = await fetch(url, { credentials: 'include' });
    const html = await resp.text();

    if (/input_user|login-box/i.test(html)) throw new Error('Sessão expirada — faça login no eCarta primeiro');

    return { html, rows: parseTabelaProcesso(html) };
  }

  async function fetchDetalhesRastreio(codigoRastreio) {
    // Etapa 1: GET da página
    const url = BASE + 'consultarObjeto.xhtml?codigo=' + encodeURIComponent(codigoRastreio);
    const resp = await fetch(url, { credentials: 'include' });
    const html = await resp.text();

    const viewState = extrairViewState(html);
    if (!viewState) return [];

    const indices = extrairIndicesRastreamento(html);
    if (!indices.length) return [];

    // Etapa 2: POST JSF para cada índice
    const todosEventos = [];
    for (const idx of indices) {
      const source = `main:tabDoc:${idx}:rastreamento`;
      const body = new URLSearchParams();
      body.append('javax.faces.partial.ajax', 'true');
      body.append('javax.faces.source', source);
      body.append('javax.faces.partial.execute', source);
      body.append('javax.faces.partial.render', 'detalhesObjeto');
      body.append(source, source);
      body.append('main', 'main');
      body.append('javax.faces.ViewState', viewState);

      const postResp = await fetch(BASE + 'consultarObjeto.xhtml', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'Faces-Request': 'partial/ajax',
        },
        body: body.toString(),
      });
      const xmlText = await postResp.text();
      const eventos = parseDetalhesDoPartialResponse(xmlText);
      if (eventos) todosEventos.push(...eventos);

      await new Promise(r => setTimeout(r, 150));
    }

    return todosEventos;
  }

  // ─── Classificação ───
  function classificarStatus(row, eventos) {
    const status = row.status || '';

    if (RE_STATUS_DEVOLVIDO.test(status)) return 'DEVOLVIDO';

    if (!eventos.length) {
      return RE_STATUS_ENTREGUE.test(status) ? 'ENTREGUE_SEM_AUDITORIA' : (status || 'SEM_EVENTOS');
    }

    // Verifica histórico de devolução
    for (const ev of eventos) {
      if (RE_DEVOLUCAO.test(ev.descricao)) return 'DEVOLVIDO';
    }

    if (RE_STATUS_ENTREGUE.test(status)) return 'ENTREGUE';
    return status || 'INDETERMINADO';
  }

  // ─── UI ───
  function buildPanel() {
    const panel = document.createElement('div');
    panel.id = '__ecHunterPanel';
    panel.style.cssText =
      'position:fixed;top:12px;right:12px;z-index:2147483647;width:580px;max-height:92vh;' +
      'background:' + C.BG + ';color:' + C.TEXT + ';border:1px solid ' + C.BORDER + ';border-radius:10px;' +
      'padding:14px;font:12px ui-monospace,Consolas,monospace;box-shadow:0 8px 30px rgba(0,0,0,.5);' +
      'display:flex;flex-direction:column;gap:8px;overflow:hidden;';

    const processoDefault = (() => {
      const m = location.search.match(/codigo=([^&]+)/);
      if (m) {
        const v = decodeURIComponent(m[1]);
        if (/^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$/.test(v)) return v;
      }
      return '';
    })();

    panel.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;">' +
        '<b style="color:' + C.ACCENT + ';">📮 eCarta Hunter — Relatório com Auditoria</b>' +
        '<button id="__ecHunterClose" style="background:' + C.ERR + ';color:' + C.SURFACE + ';border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-weight:700;">✕</button>' +
      '</div>' +

      '<div style="font-size:10px;color:' + C.MUTED + ';">' +
        'Fluxo: GET consultarProcesso → parse tabela → GET consultarObjeto → POST JSF → auditar histórico → corrigir falsos positivos' +
      '</div>' +

      // Input processo
      '<label style="font-size:11px;color:' + C.MUTED + ';">Número do processo (CNJ)</label>' +
      '<div style="display:flex;gap:6px;">' +
        '<input id="__ecHunterProcesso" value="' + processoDefault + '" placeholder="0000000-00.0000.0.00.0000" style="flex:1;padding:6px;background:' + C.SURFACE + ';color:' + C.TEXT + ';border:1px solid ' + C.BORDER + ';border-radius:4px;">' +
        '<button id="__ecHunterRun" style="padding:6px 14px;background:' + C.ACCENT + ';color:' + C.SURFACE + ';border:none;border-radius:4px;font-weight:700;cursor:pointer;">▶ Executar</button>' +
      '</div>' +

      // Status / progresso
      '<div id="__ecHunterStatus" style="font-size:11px;color:' + C.MUTED + ';">Pronto. Insira o número do processo e clique Executar.</div>' +

      // Progress bar
      '<div id="__ecHunterProgressBar" style="display:none;height:4px;background:' + C.SURFACE + ';border-radius:2px;overflow:hidden;">' +
        '<div id="__ecHunterProgressFill" style="height:100%;width:0%;background:' + C.ACCENT + ';transition:width 0.3s;"></div>' +
      '</div>' +

      // Botões
      '<div style="display:flex;gap:6px;">' +
        '<button id="__ecHunterCopyTxt" style="flex:1;padding:5px;background:' + C.BORDER + ';color:' + C.TEXT + ';border:none;border-radius:4px;cursor:pointer;">📋 copiar relatório</button>' +
        '<button id="__ecHunterCopyJson" style="flex:1;padding:5px;background:' + C.BORDER + ';color:' + C.TEXT + ';border:none;border-radius:4px;cursor:pointer;">📋 copiar JSON</button>' +
      '</div>' +

      // Resultado
      '<div id="__ecHunterResult" style="background:' + C.SURFACE + ';border:1px solid ' + C.BORDER + ';border-radius:6px;padding:10px;overflow:auto;max-height:56vh;white-space:pre-wrap;word-break:break-all;font-size:11px;line-height:1.5;">' +
        '<span style="color:' + C.MUTED + ';">(resultado aparecerá aqui)</span>' +
      '</div>';

    document.body.appendChild(panel);

    // Eventos
    $('#__ecHunterClose', panel).addEventListener('click', () => {
      panel.remove();
      window.__ecartaHunter = null;
    });

    $('#__ecHunterCopyTxt', panel).addEventListener('click', () => {
      copyText(window._rawReport || '(nada ainda)');
    });

    $('#__ecHunterCopyJson', panel).addEventListener('click', () => {
      copyText(window._rawJson || '(nada ainda)');
    });

    $('#__ecHunterRun', panel).addEventListener('click', async () => {
      const processo = $('#__ecHunterProcesso', panel).value.trim();
      if (!processo) return;
      await executarFluxo(processo);
    });

    // Auto-run se já tem processo na URL
    if (processoDefault && location.search.includes('codigo=')) {
      setTimeout(() => executarFluxo(processoDefault), 400);
    }

    return panel;
  }

  async function executarFluxo(numeroProcesso) {
    const panel = $('#__ecHunterPanel');
    const statusEl = $('#__ecHunterStatus', panel);
    const resultEl = $('#__ecHunterResult', panel);
    const progressBar = $('#__ecHunterProgressBar', panel);
    const progressFill = $('#__ecHunterProgressFill', panel);
    const runBtn = $('#__ecHunterRun', panel);

    runBtn.disabled = true;
    progressBar.style.display = 'block';
    progressFill.style.width = '0%';
    resultEl.innerHTML = '';
    window._rawReport = '';
    window._rawJson = '';

    const log = (msg, color) => {
      statusEl.textContent = msg;
      statusEl.style.color = color || C.MUTED;
    };

    try {
      // ── Etapa 1: GET tabela do processo ──
      log('Etapa 1/3: Buscando tabela do processo...');
      progressFill.style.width = '10%';

      const { html: pageHtml, rows } = await fetchProcesso(numeroProcesso);
      window._pageHtml = pageHtml;

      if (!rows.length) {
        log('Nenhuma linha encontrada na tabela eCarta.', C.WARN);
        resultEl.innerHTML = '<span style="color:' + C.WARN + ';">Nenhum dado encontrado para este processo.</span>';
        runBtn.disabled = false;
        progressBar.style.display = 'none';
        return;
      }

      log(`Etapa 1/3: ${rows.length} linhas na tabela. Filtrando rastreios...`);
      progressFill.style.width = '25%';

      // Filtra linhas com rastreio válido
      const comRastreio = rows.filter(r => /^[A-Z]{2}\d{9}BR$/.test(r.objeto));
      const semRastreio = rows.filter(r => !/^[A-Z]{2}\d{9}BR$/.test(r.objeto));

      log(`Etapa 2/3: ${comRastreio.length} rastreios para auditar...`);

      // ── Etapa 2: Para cada rastreio, buscar detalhes ──
      const resultados = [];

      for (let i = 0; i < comRastreio.length; i++) {
        const row = comRastreio[i];
        const pct = 25 + Math.round((i / Math.max(comRastreio.length, 1)) * 50);
        progressFill.style.width = pct + '%';
        log(`Etapa 2/3: auditando ${i + 1}/${comRastreio.length}: ${row.objeto}...`);

        let eventos = [];
        try {
          eventos = await fetchDetalhesRastreio(row.objeto);
        } catch (e) {
          eventos = [];
        }

        const statusReal = classificarStatus(row, eventos);
        const falsoPositivo = RE_STATUS_ENTREGUE.test(row.status) && statusReal === 'DEVOLVIDO';

        resultados.push({ ...row, eventos, statusReal, falsoPositivo });
      }

      // ── Etapa 3: Adiciona linhas sem rastreio ──
      for (const row of semRastreio) {
        resultados.push({ ...row, eventos: [], statusReal: row.status, falsoPositivo: false });
      }

      progressFill.style.width = '85%';
      log('Etapa 3/3: Gerando relatório...');

      // ── Gera relatório ──
      const falsosPositivos = resultados.filter(r => r.falsoPositivo);

      // Estatísticas
      const stats = {
        processo: numeroProcesso,
        total: resultados.length,
        comRastreio: comRastreio.length,
        auditadas: resultados.filter(r => r.eventos.length > 0).length,
        falsosPositivos: falsosPositivos.length,
        entregues: resultados.filter(r => r.statusReal === 'ENTREGUE').length,
        devolvidos: resultados.filter(r => r.statusReal === 'DEVOLVIDO').length,
      };

      // Relatório formatado
      const linhasRelatorio = [];
      linhasRelatorio.push('═'.repeat(55));
      linhasRelatorio.push('  ECARTA — RELATÓRIO DE INTIMAÇÕES COM AUDITORIA');
      linhasRelatorio.push('═'.repeat(55));
      linhasRelatorio.push(`  Processo: ${numeroProcesso}`);
      linhasRelatorio.push(`  Total: ${stats.total} | Com rastreio: ${stats.comRastreio} | Auditadas: ${stats.auditadas}`);
      linhasRelatorio.push(`  Entregues: ${stats.entregues} | Devolvidos: ${stats.devolvidos}`);
      if (stats.falsosPositivos > 0) {
        linhasRelatorio.push(`  ⚠️ FALSOS POSITIVOS CORRIGIDOS: ${stats.falsosPositivos}`);
      }
      linhasRelatorio.push('─'.repeat(55));

      for (let i = 0; i < resultados.length; i++) {
        const r = resultados[i];
        linhasRelatorio.push('');
        linhasRelatorio.push(`  [${i + 1}] ${r.destinatario || '(sem destinatário)'}`);

        let statusLinha = `  Status: ${r.statusReal}`;
        if (r.falsoPositivo) {
          statusLinha += ` ⚠️ TABELA DIZIA "ENTREGUE AO DESTINATÁRIO" → CORRIGIDO PARA DEVOLVIDO`;
          linhasRelatorio.push(`  ${statusLinha}`);
          // Mostra evidência
          for (const ev of r.eventos) {
            if (RE_DEVOLUCAO.test(ev.descricao)) {
              linhasRelatorio.push(`    └ evidência: ${ev.dataEvento} — ${ev.descricao}`);
            }
          }
        } else {
          linhasRelatorio.push(`  ${statusLinha}`);
        }

        linhasRelatorio.push(`  Id PJe: ${r.idPje}`);
        linhasRelatorio.push(`  Rastreio: ${r.objeto || 'Indisponível'}`);
        linhasRelatorio.push(`  Envio: ${r.dataEnvio || '—'} | Entrega: ${r.dataEntrega || '—'}`);
        linhasRelatorio.push(`  Destinatário: ${r.destinatario || '—'}`);

        // Eventos resumidos (últimos 3)
        if (r.eventos.length > 0) {
          const ultimos = r.eventos.slice(0, 3);
          linhasRelatorio.push(`  Últimos eventos:`);
          for (const ev of ultimos) {
            linhasRelatorio.push(`    ${ev.dataEvento} — ${ev.descricao} (${ev.cidadeUf})`);
          }
          if (r.eventos.length > 3) linhasRelatorio.push(`    ... +${r.eventos.length - 3} eventos`);
        }

        if (i < resultados.length - 1) linhasRelatorio.push('  ' + '─'.repeat(50));
      }

      linhasRelatorio.push('');
      linhasRelatorio.push('═'.repeat(55));
      if (stats.falsosPositivos > 0) {
        linhasRelatorio.push(`  ⚠️ ATENÇÃO: ${stats.falsosPositivos} caso(s) de falso positivo detectado(s)!`);
        linhasRelatorio.push('  O status "Objeto entregue ao destinatário" na tabela escondia uma devolução.');
        linhasRelatorio.push('  Verifique os eventos com "Objeto será devolvido ao remetente".');
      } else {
        linhasRelatorio.push('  ✓ Nenhum falso positivo detectado.');
      }
      linhasRelatorio.push('═'.repeat(55));

      const relatorioTxt = linhasRelatorio.join('\n');

      // JSON
      const jsonData = { stats, resultados };
      window._rawReport = relatorioTxt;
      window._rawJson = JSON.stringify(jsonData, null, 2);

      // Render
      let htmlResult = '';
      for (const line of linhasRelatorio) {
        let color = C.TEXT;
        if (line.includes('⚠️')) color = C.WARN;
        else if (line.includes('CORRIGIDO')) color = C.ERR;
        else if (line.includes('✓')) color = C.OK;
        else if (line.startsWith('═') || line.startsWith('─')) color = C.BORDER;

        htmlResult += `<span style="color:${color};">${escapeHtml(line)}</span>\n`;
      }

      resultEl.innerHTML = htmlResult;
      progressFill.style.width = '100%';

      const msgFinal = stats.falsosPositivos > 0
        ? `✅ CONCLUÍDO — ${stats.total} linhas, ${stats.falsosPositivos} FALSO(S) POSITIVO(S) CORRIGIDO(S)!`
        : `✅ CONCLUÍDO — ${stats.total} linhas, nenhum falso positivo.`;
      log(msgFinal, stats.falsosPositivos > 0 ? C.WARN : C.OK);

    } catch (e) {
      log('ERRO: ' + e.message, C.ERR);
      resultEl.innerHTML = `<span style="color:${C.ERR};">${escapeHtml(e.message)}</span>`;
    } finally {
      runBtn.disabled = false;
      setTimeout(() => { progressBar.style.display = 'none'; }, 800);
    }
  }

  // ─── Init ───
  const panel = buildPanel();
  window.__ecartaHunter = {
    toggle() { panel.style.display = panel.style.display === 'none' ? 'flex' : 'none'; },
    panel,
    getReport() { return window._rawReport || ''; },
    getJson() { return window._rawJson || ''; },
  };

})();
