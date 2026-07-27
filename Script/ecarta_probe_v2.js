// eCarta API Probe v2 — com suporte a POST JSF para detalhes de rastreamento
// Uso: compilar com bookmarklet minifier ou testar no console da página consultarObjeto.xhtml

(function pjeEcartaProbeV2() {
  'use strict';

  if (window.__ecartaProbeV2) {
    window.__ecartaProbeV2.toggle();
    return;
  }

  const BASE = 'https://aplicacoes1.trt2.jus.br/eCarta-web/';

  // ─── temas ───
  const C = {
    BG: '#181825', SURFACE: '#11111b', TEXT: '#cdd6f4', BORDER: '#313244',
    ACCENT: '#89b4fa', OK: '#a6e3a1', ERR: '#f38ba8', MUTED: '#6c7086',
    WARN: '#fab387'
  };

  // ─── helpers ───
  function extrairDaUrl() {
    const m = location.search.match(/codigo=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  const atual = extrairDaUrl();
  const processoDefault = /^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$/.test(atual) ? atual : '';
  const rastreioDefault = /^[A-Za-z]{2}\d{9}BR$/.test(atual) ? atual : '';

  function copyText(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed'; ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch (e) { /* noop */ }
    document.body.removeChild(ta);
  }

  function textoComSeparadorBr(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('br').forEach(br => br.replaceWith(' | '));
    return clone.textContent.trim().replace(/\s+/g, ' ');
  }

  // ─── extratores de tabela ───
  function extrairTabelaProcesso(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const seletores = [
      '#main\\:tabDoc_data tr', '#main\\:tabDoc tbody tr',
      'table[id*="tabDoc"] tr', '.ui-datatable tbody tr', 'tbody tr'
    ];
    let rows = null;
    for (const sel of seletores) {
      const tmp = doc.querySelectorAll(sel);
      if (tmp.length) { rows = tmp; break; }
    }
    if (!rows || !rows.length) return null;
    const out = [];
    rows.forEach(tr => {
      const tds = tr.querySelectorAll('td');
      if (tds.length < 4) return;
      const get = i => tds[i] ? tds[i].textContent.trim() : '';
      out.push({
        dataEnvio: get(0), dataEntrega: get(1), processo: get(2),
        idPje: get(3), objeto: get(4), status: get(5),
        destinatario: get(6), orgaoJulgador: get(7)
      });
    });
    return out;
  }

  function extrairDetalhesObjeto(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const seletores = [
      '#tabDetalhesObjeto_data tr', 'div[id*="tabDetalhesObjeto"] tbody tr'
    ];
    let rows = null;
    for (const sel of seletores) {
      const tmp = doc.querySelectorAll(sel);
      if (tmp.length) { rows = tmp; break; }
    }
    if (!rows || !rows.length) return null;
    const out = [];
    rows.forEach(tr => {
      const tds = tr.querySelectorAll('td');
      if (tds.length < 2) return;
      // ignora a linha "Nenhum resultado encontrado"
      if (tds[0].textContent.includes('Nenhum resultado')) return;
      out.push({
        dataEvento: tds[0] ? tds[0].textContent.trim() : '',
        descricao: tds[1] ? textoComSeparadorBr(tds[1]) : '',
        cidadeUf: tds[2] ? tds[2].textContent.trim() : ''
      });
    });
    return out.length ? out : null;
  }

  // ─── extrai ViewState e índice dos links de rastreamento ───
  function extrairViewStateEIndices(html) {
    const vsMatch = html.match(/name="javax\.faces\.ViewState"[^>]+value="([^"]+)"/);
    const viewState = vsMatch ? vsMatch[1] : '';

    // encontra todos os links de rastreamento: main:tabDoc:N:rastreamento
    const indices = [];
    const linkRe = /id="main:tabDoc:(\d+):rastreamento"/g;
    let m;
    while ((m = linkRe.exec(html)) !== null) {
      indices.push(parseInt(m[1], 10));
    }
    return { viewState, indices };
  }

  // ─── POST JSF para obter detalhes de um objeto ───
  function postJsfDetalhes(viewState, rowIndex) {
    const source = `main:tabDoc:${rowIndex}:rastreamento`;
    const body = new URLSearchParams();
    body.append('javax.faces.partial.ajax', 'true');
    body.append('javax.faces.source', source);
    body.append('javax.faces.partial.execute', source);
    body.append('javax.faces.partial.render', 'detalhesObjeto');
    body.append(source, source);
    body.append('main', 'main');
    body.append('javax.faces.ViewState', viewState);

    return fetch(BASE + 'consultarObjeto.xhtml', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Faces-Request': 'partial/ajax'
      },
      body: body.toString()
    }).then(r => r.text());
  }

  function extrairDetalhesDoPartialResponse(xmlText) {
    // parse do <partial-response> e extrai #tabDetalhesObjeto_data
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'application/xml');
    // verifica parse error
    const parseError = xmlDoc.querySelector('parsererror');
    if (parseError) return null;

    const updates = xmlDoc.querySelectorAll('update');
    for (const upd of updates) {
      if (upd.getAttribute('id') === 'detalhesObjeto') {
        const html = upd.textContent || upd.innerHTML || '';
        return extrairDetalhesObjeto(html);
      }
    }
    return null;
  }

  // ─── UI ───
  const panel = document.createElement('div');
  panel.setAttribute('data-pje-probe-ui', '1');
  panel.style.cssText =
    'position:fixed;top:16px;right:16px;z-index:2147483647;width:520px;max-height:88vh;' +
    'background:' + C.BG + ';color:' + C.TEXT + ';border:1px solid ' + C.BORDER + ';border-radius:10px;' +
    'padding:14px;font:12px ui-monospace,Consolas,monospace;box-shadow:0 8px 30px rgba(0,0,0,.5);' +
    'display:flex;flex-direction:column;gap:8px;overflow:hidden;';

  panel.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;">' +
      '<b style="color:' + C.ACCENT + ';">📮 eCarta API Probe v2</b>' +
      '<button id="__ecCloseV2" style="background:' + C.ERR + ';color:' + C.SURFACE + ';border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-weight:700;">✕</button>' +
    '</div>' +
    '<div style="color:' + C.MUTED + ';font-size:11px;">base: ' + BASE + '</div>' +

    // ─── consultarProcesso ───
    '<label style="font-size:11px;color:' + C.MUTED + ';">consultarProcesso.xhtml?codigo=</label>' +
    '<div style="display:flex;gap:6px;">' +
      '<input id="__ecProcessoV2" value="' + processoDefault + '" placeholder="0000000-00.0000.0.00.0000" style="flex:1;padding:6px;background:' + C.SURFACE + ';color:' + C.TEXT + ';border:1px solid ' + C.BORDER + ';border-radius:4px;">' +
      '<button id="__ecCallProcessoV2" style="padding:6px 10px;background:' + C.ACCENT + ';color:' + C.SURFACE + ';border:none;border-radius:4px;font-weight:700;cursor:pointer;">GET</button>' +
    '</div>' +

    // ─── consultarObjeto GET ───
    '<label style="font-size:11px;color:' + C.MUTED + ';">consultarObjeto.xhtml?codigo= (GET — tabela principal)</label>' +
    '<div style="display:flex;gap:6px;">' +
      '<input id="__ecObjetoV2" value="' + rastreioDefault + '" placeholder="AA000000000BR" style="flex:1;padding:6px;background:' + C.SURFACE + ';color:' + C.TEXT + ';border:1px solid ' + C.BORDER + ';border-radius:4px;">' +
      '<button id="__ecCallObjetoV2" style="padding:6px 10px;background:' + C.ACCENT + ';color:' + C.SURFACE + ';border:none;border-radius:4px;font-weight:700;cursor:pointer;">GET</button>' +
    '</div>' +

    // ─── POST JSF para detalhes ───
    '<label style="font-size:11px;color:' + C.WARN + ';">POST JSF — detalhes de rastreamento (histórico completo)</label>' +
    '<div style="display:flex;gap:6px;">' +
      '<input id="__ecObjetoPostV2" value="' + rastreioDefault + '" placeholder="código de rastreio" style="flex:1;padding:6px;background:' + C.SURFACE + ';color:' + C.TEXT + ';border:1px solid ' + C.BORDER + ';border-radius:4px;">' +
      '<button id="__ecCallDetalhesV2" style="padding:6px 10px;background:' + C.WARN + ';color:' + C.SURFACE + ';border:none;border-radius:4px;font-weight:700;cursor:pointer;">POST detalhes</button>' +
    '</div>' +
    '<div style="font-size:10px;color:' + C.MUTED + ';">Faz GET da página → extrai ViewState + índices → POST JSF p/ cada linha → extrai histórico</div>' +

    // ─── status ───
    '<div id="__ecStatusV2" style="color:' + C.MUTED + ';"></div>' +

    // ─── botões de cópia ───
    '<div style="display:flex;gap:6px;">' +
      '<button id="__ecCopyRawV2" style="flex:1;padding:6px;background:' + C.BORDER + ';color:' + C.TEXT + ';border:none;border-radius:4px;cursor:pointer;">copiar raw</button>' +
      '<button id="__ecCopyJsonV2" style="flex:1;padding:6px;background:' + C.BORDER + ';color:' + C.TEXT + ';border:none;border-radius:4px;cursor:pointer;">copiar JSON</button>' +
    '</div>' +

    // ─── resultado ───
    '<pre id="__ecResultV2" style="margin:0;background:' + C.SURFACE + ';border:1px solid ' + C.BORDER + ';border-radius:6px;padding:8px;overflow:auto;max-height:52vh;white-space:pre-wrap;word-break:break-all;"></pre>';

  document.body.appendChild(panel);

  let rawHtml = '';
  let tableJson = '';

  // ─── fetch helpers ───
  function chamarGet(url, label) {
    const statusEl = panel.querySelector('#__ecStatusV2');
    const resultEl = panel.querySelector('#__ecResultV2');
    statusEl.textContent = 'GET ' + label + ' ...';
    statusEl.style.color = C.MUTED;
    resultEl.textContent = '';
    rawHtml = '';
    tableJson = '';

    const t0 = Date.now();
    fetch(url, { credentials: 'include' })
      .then(resp => resp.text().then(text => {
        const dur = Date.now() - t0;
        rawHtml = text;

        const tabelaProcesso = extrairTabelaProcesso(text);
        const detalhesObjeto = extrairDetalhesObjeto(text);
        const pareceLogin = /login-box|input_user/i.test(text);

        let resumo = resp.status + ' — ' + dur + 'ms — ' + text.length + ' chars';
        if (pareceLogin) resumo += ' — ⚠️ LOGIN (sessão expirada?)';

        const achados = [];
        if (tabelaProcesso) achados.push('tabela processo: ' + tabelaProcesso.length + ' linha(s)');
        if (detalhesObjeto) achados.push('histórico inline: ' + detalhesObjeto.length + ' evento(s)');

        if (achados.length) {
          resumo += ' — ' + achados.join(' | ');
          const payload = {};
          if (tabelaProcesso) payload.tabelaProcesso = tabelaProcesso;
          if (detalhesObjeto) payload.historicoRastreio = detalhesObjeto;
          tableJson = JSON.stringify(payload, null, 2);
          resultEl.textContent = tableJson;
        } else {
          resumo += ' — nenhuma tabela reconhecida (use "POST detalhes" para histórico)';
          resultEl.textContent = text.slice(0, 20000);
        }
        statusEl.textContent = resumo;
        statusEl.style.color = resp.ok ? (achados.length ? C.OK : C.MUTED) : C.ERR;
      }))
      .catch(e => {
        statusEl.textContent = 'erro de rede: ' + e.message;
        statusEl.style.color = C.ERR;
      });
  }

  // ─── POST JSF para TODOS os detalhes ───
  async function chamarPostDetalhes(codigoRastreio) {
    const statusEl = panel.querySelector('#__ecStatusV2');
    const resultEl = panel.querySelector('#__ecResultV2');
    statusEl.textContent = 'Etapa 1/2: GET página para extrair ViewState...';
    statusEl.style.color = C.MUTED;
    resultEl.textContent = '';
    rawHtml = '';
    tableJson = '';

    try {
      // Etapa 1: GET da página principal
      const t0 = Date.now();
      const pageResp = await fetch(BASE + 'consultarObjeto.xhtml?codigo=' + encodeURIComponent(codigoRastreio), { credentials: 'include' });
      const pageHtml = await pageResp.text();
      rawHtml = pageHtml;

      const { viewState, indices } = extrairViewStateEIndices(pageHtml);
      if (!viewState) {
        statusEl.textContent = 'Erro: não encontrei javax.faces.ViewState no HTML';
        statusEl.style.color = C.ERR;
        return;
      }
      if (!indices.length) {
        statusEl.textContent = 'Nenhum link de rastreamento (main:tabDoc:N:rastreamento) encontrado na página';
        statusEl.style.color = C.WARN;
        return;
      }

      statusEl.textContent = 'Etapa 2/2: POST JSF para ' + indices.length + ' objeto(s)... ViewState=' + viewState.slice(0, 20) + '...';
      statusEl.style.color = C.MUTED;

      // Etapa 2: POST para cada linha
      const todosResultados = [];
      for (const idx of indices) {
        statusEl.textContent = 'POST JSF linha ' + idx + ' de ' + (indices.length) + '...';
        const xmlText = await postJsfDetalhes(viewState, idx);
        const detalhes = extrairDetalhesDoPartialResponse(xmlText);
        if (detalhes) {
          todosResultados.push({ indice: idx, eventos: detalhes });
        }
        // pequeno delay entre requests
        await new Promise(r => setTimeout(r, 200));
      }

      const dur = Date.now() - t0;
      const tabelaProcesso = extrairTabelaProcesso(pageHtml);

      const payload = {
        codigo: codigoRastreio,
        duracaoMs: dur,
        viewState: viewState,
      };
      if (tabelaProcesso) payload.tabelaProcesso = tabelaProcesso;
      if (todosResultados.length) payload.detalhesRastreamento = todosResultados;

      tableJson = JSON.stringify(payload, null, 2);
      resultEl.textContent = tableJson;

      let resumo = pageResp.status + ' — ' + dur + 'ms — ' + indices.length + ' POST(s) JSF';
      if (tabelaProcesso) resumo += ' — tabela: ' + tabelaProcesso.length + ' linhas';
      if (todosResultados.length) {
        const totalEventos = todosResultados.reduce((s, r) => s + r.eventos.length, 0);
        resumo += ' — histórico: ' + totalEventos + ' eventos em ' + todosResultados.length + ' objeto(s)';
      }
      statusEl.textContent = resumo;
      statusEl.style.color = todosResultados.length ? C.OK : C.WARN;

    } catch (e) {
      statusEl.textContent = 'erro: ' + e.message;
      statusEl.style.color = C.ERR;
    }
  }

  // ─── event listeners ───
  panel.querySelector('#__ecCallProcessoV2').addEventListener('click', () => {
    const codigo = panel.querySelector('#__ecProcessoV2').value.trim();
    if (!codigo) return;
    chamarGet(BASE + 'consultarProcesso.xhtml?codigo=' + encodeURIComponent(codigo), 'processo');
  });

  panel.querySelector('#__ecCallObjetoV2').addEventListener('click', () => {
    const codigo = panel.querySelector('#__ecObjetoV2').value.trim();
    if (!codigo) return;
    chamarGet(BASE + 'consultarObjeto.xhtml?codigo=' + encodeURIComponent(codigo), 'objeto');
  });

  panel.querySelector('#__ecCallDetalhesV2').addEventListener('click', () => {
    const codigo = panel.querySelector('#__ecObjetoPostV2').value.trim();
    if (!codigo) return;
    chamarPostDetalhes(codigo);
  });

  panel.querySelector('#__ecCopyRawV2').addEventListener('click', () => {
    copyText(rawHtml || '(nada ainda)');
  });

  panel.querySelector('#__ecCopyJsonV2').addEventListener('click', () => {
    copyText(tableJson || '(nenhum dado extraído ainda)');
  });

  panel.querySelector('#__ecCloseV2').addEventListener('click', () => {
    panel.remove();
    window.__ecartaProbeV2 = null;
  });

  window.__ecartaProbeV2 = {
    toggle() { panel.style.display = panel.style.display === 'none' ? 'flex' : 'none'; }
  };

  // ─── auto-disparo se já estamos numa página com código ───
  if (rastreioDefault) {
    setTimeout(() => {
      const statusEl = panel.querySelector('#__ecStatusV2');
      if (statusEl) {
        statusEl.textContent = 'Pronto. Clique "POST detalhes" para buscar histórico ou "GET" para tabela.';
        statusEl.style.color = C.MUTED;
      }
    }, 300);
  }

})();
