// ==UserScript==
// @name         PJe - Obter dados bancários TRT2
// @namespace    https://pje.trt2.jus.br/
// @version      1.3.0
// @description  Consulta TRT2 com distinção entre advogado e pessoa física, CNPJ e estados sem cadastro.
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe#*
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe#*
// @grant        GM_xmlhttpRequest
// @grant        GM_setClipboard
// @connect      aplicacoes1.trt2.jus.br
// @run-at       document-start
// ==/UserScript==

(function() {
  'use strict';

  const BASE = 'https://aplicacoes1.trt2.jus.br/adv-dados-bancarios-consulta';

  const onlyDigits = v => (v || '').replace(/\D+/g, '');
  const formatCpf = d => d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
  const formatCnpj = d => d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');

  function normalizeDoc(v) {
    const d = onlyDigits(v);
    if (d.length === 11) return { kind: 'cpf', raw: d, display: formatCpf(d) };
    if (d.length === 14) return { kind: 'cnpj', raw: d, display: formatCnpj(d) };
    return { kind: 'invalid', raw: d, display: d };
  }

  function gmRequest(details) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        timeout: 30000,
        ...details,
        onload: resolve,
        onerror: reject,
        ontimeout: reject
      });
    });
  }

  async function fetchViewState(url) {
    const r = await gmRequest({ method: 'GET', url });
    const html = r.responseText || '';
    const m = html.match(/name="javax\.faces\.ViewState"\s+id="javax\.faces\.ViewState"\s+value="([^"]+)"/);
    if (!m) throw new Error('ViewState não encontrado.');
    return m[1];
  }

  function isEmptyCpf(html) {
    return /Nenhuma pessoa física encontrada\./i.test(html) || /Nenhum advogado encontrado\./i.test(html);
  }

  function isEmptyCnpj(html) {
    return /Nenhuma pessoa jurídica encontrada\./i.test(html);
  }

  async function searchCpfAsAdvogado(docDigits) {
    const url = `${BASE}/index`;
    const vs = await fetchViewState(url);

    const body = new URLSearchParams({
      formSearch: 'formSearch',
      'formSearch:tipoBusca_input': 'CPF',
      'formSearch:cpfOuOab': docDigits,
      'formSearch:j_idt39': 'formSearch:j_idt39',
      'javax.faces.partial.ajax': 'true',
      'javax.faces.source': 'formSearch:j_idt39',
      'javax.faces.partial.execute': 'formSearch:j_idt39 formSearch:tipoBusca formSearch:cpfOuOab',
      'javax.faces.partial.render': 'formSearch:resultado messages',
      'javax.faces.behavior.event': 'action',
      'javax.faces.partial.event': 'click',
      'javax.faces.ViewState': vs
    });

    const r = await gmRequest({
      method: 'POST',
      url,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Faces-Request': 'partial/ajax',
        'X-Requested-With': 'XMLHttpRequest'
      },
      data: body.toString()
    });

    const txt = r.responseText || '';
    if (isEmptyCpf(txt)) {
      return { status: 'empty' };
    }

    const m = txt.match(/\/adv-dados-bancarios-consulta\/advogado\?id=(\d+)/);
    if (!m) throw new Error('Resposta de advogado recebida, mas nenhum ID foi encontrado.');
    return { status: 'found', detailUrl: `${BASE}/advogado?id=${m[1]}`, kind: 'cpf-adv' };
  }

  async function searchCpfAsPessoaFisica(docDigits) {
    const url = `${BASE}/consulta-pf`;
    const vs = await fetchViewState(url);

    const body = new URLSearchParams({
      formSearch: 'formSearch',
      'formSearch:cpf': docDigits,
      'formSearch:j_idt38': 'formSearch:j_idt38',
      'javax.faces.partial.ajax': 'true',
      'javax.faces.source': 'formSearch:j_idt38',
      'javax.faces.partial.execute': 'formSearch:j_idt38 formSearch:cpf',
      'javax.faces.partial.render': 'formSearch:resultado messages',
      'javax.faces.behavior.event': 'action',
      'javax.faces.partial.event': 'click',
      'javax.faces.ViewState': vs
    });

    const r = await gmRequest({
      method: 'POST',
      url,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Faces-Request': 'partial/ajax',
        'X-Requested-With': 'XMLHttpRequest'
      },
      data: body.toString()
    });

    const txt = r.responseText || '';
    if (isEmptyCpf(txt)) {
      return { status: 'empty' };
    }

    const m = txt.match(/\/adv-dados-bancarios-consulta\/pessoa-fisica\?id=(\d+)/);
    if (!m) throw new Error('Resposta de pessoa física recebida, mas nenhum ID foi encontrado.');
    return { status: 'found', detailUrl: `${BASE}/pessoa-fisica?id=${m[1]}`, kind: 'cpf-pf' };
  }

  async function searchCnpj(docDigits) {
    const url = `${BASE}/consulta-pj`;
    const vs = await fetchViewState(url);

    const body = new URLSearchParams({
      formSearch: 'formSearch',
      'formSearch:cnpj': docDigits,
      'formSearch:j_idt37': 'formSearch:j_idt37',
      'javax.faces.partial.ajax': 'true',
      'javax.faces.source': 'formSearch:j_idt37',
      'javax.faces.partial.execute': 'formSearch:j_idt37 formSearch:cnpj',
      'javax.faces.partial.render': 'formSearch:resultado messages',
      'javax.faces.behavior.event': 'action',
      'javax.faces.partial.event': 'click',
      'javax.faces.ViewState': vs
    });

    const r = await gmRequest({
      method: 'POST',
      url,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Faces-Request': 'partial/ajax',
        'X-Requested-With': 'XMLHttpRequest'
      },
      data: body.toString()
    });

    const txt = r.responseText || '';
    if (isEmptyCnpj(txt)) {
      return { status: 'empty' };
    }

    const m = txt.match(/\/adv-dados-bancarios-consulta\/pessoa-juridica\?id=(\d+)/);
    if (!m) throw new Error('Resposta de CNPJ recebida, mas nenhum ID foi encontrado.');
    return { status: 'found', detailUrl: `${BASE}/pessoa-juridica?id=${m[1]}`, kind: 'cnpj' };
  }

  async function fetchDetail(detailUrl, kind) {
    const r = await gmRequest({ method: 'GET', url: detailUrl });
    const html = r.responseText || '';
    const doc = new DOMParser().parseFromString(html, 'text/html');

    const getByLabel = (text) => {
      const labels = [...doc.querySelectorAll('label')];
      const label = labels.find(el => (el.textContent || '').trim() === text);
      if (!label) return '';
      const span = label.parentElement ? label.parentElement.querySelector('span.readonly') : null;
      return (span ? span.textContent : '').trim();
    };

    if (kind === 'cpf-adv') {
      return {
        nome: getByLabel('Nome:'),
        documento: getByLabel('CPF:'),
        banco: getByLabel('Banco:'),
        tipo: getByLabel('Tipo:'),
        agencia: getByLabel('Agência:'),
        conta: getByLabel('Conta:')
      };
    }

    if (kind === 'cpf-pf') {
      return {
        nome: getByLabel('Nome:'),
        documento: getByLabel('CPF:'),
        banco: getByLabel('Banco:'),
        tipo: getByLabel('Tipo:'),
        agencia: getByLabel('Agência:'),
        conta: getByLabel('Conta:')
      };
    }

    return {
      nome: getByLabel('Razão Social'),
      documento: getByLabel('CNPJ:'),
      banco: getByLabel('Banco:'),
      tipo: getByLabel('Tipo:'),
      agencia: getByLabel('Agência:'),
      conta: getByLabel('Conta:')
    };
  }

  function buildSearchLink(kind, docDigits) {
    const q = encodeURIComponent(docDigits);
    if (kind === 'cpf-adv') return `${BASE}/index?doc=${q}&origem=advogado`;
    if (kind === 'cpf-pf') return `${BASE}/consulta-pf?doc=${q}&origem=pessoa-fisica`;
    return `${BASE}/consulta-pj?doc=${q}`;
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function setStatus(msg, cls = 'muted') {
    const el = document.getElementById('tm-trt2-status');
    if (el) {
      el.className = cls;
      el.textContent = msg;
    }
  }

  function renderResult(payload) {
    const el = document.getElementById('tm-trt2-result');
    if (!el) return;

    if (payload.status === 'empty') {
      el.innerHTML = `
        <div class="tm-card tm-empty">
          <div><strong>Sem dados cadastrados</strong></div>
          <div>Origem: ${escapeHtml(payload.origin || '')}</div>
          <div>Documento: ${escapeHtml(payload.query || '')}</div>
          <div class="tm-row"><a href="${escapeHtml(payload.searchLink || '#')}" target="_blank" rel="noopener">Abrir tela de busca pré-preenchida</a></div>
        </div>
      `;
      return;
    }

    if (payload.status === 'error') {
      el.innerHTML = `
        <div class="tm-card tm-error">
          <div><strong>Falha técnica</strong></div>
          <div>${escapeHtml(payload.message || 'Erro desconhecido')}</div>
        </div>
      `;
      return;
    }

    const d = payload.data || {};
    el.innerHTML = `
      <div class="tm-card tm-ok">
        <div><strong>Dados encontrados</strong></div>
        <div>Origem: ${escapeHtml(payload.origin || '')}</div>
        <div>Nome/Razão Social: ${escapeHtml(d.nome || '')}</div>
        <div>Documento: ${escapeHtml(d.documento || '')}</div>
        <div>Banco: ${escapeHtml(d.banco || '')}</div>
        <div>Tipo: ${escapeHtml(d.tipo || '')}</div>
        <div>Agência: ${escapeHtml(d.agencia || '')}</div>
        <div>Conta: ${escapeHtml(d.conta || '')}</div>
      </div>
    `;
  }

  async function runLookup() {
    const input = document.getElementById('tm-trt2-doc');
    const btn = document.getElementById('tm-trt2-btn');
    const mode = document.getElementById('tm-trt2-mode').value;
    const norm = normalizeDoc(input.value);

    if (norm.kind === 'invalid') {
      setStatus('Informe CPF com 11 dígitos ou CNPJ com 14 dígitos.', 'error');
      return;
    }

    btn.disabled = true;
    renderResult({ status: 'loading' });

    try {
      if (norm.kind === 'cnpj') {
        setStatus('Buscando CNPJ...', 'muted');
        const search = await searchCnpj(norm.raw);
        if (search.status === 'empty') {
          renderResult({
            status: 'empty',
            origin: 'CNPJ',
            query: norm.display,
            searchLink: buildSearchLink('cnpj', norm.raw)
          });
          setStatus('Consulta concluída sem cadastro.', 'ok');
          return;
        }

        const data = await fetchDetail(search.detailUrl, search.kind);
        renderResult({
          status: 'found',
          origin: 'CNPJ',
          data
        });
        setStatus('Consulta concluída com dados.', 'ok');
        return;
      }

      if (mode === 'advogado') {
        setStatus('Buscando CPF na lista de advogado...', 'muted');
        const adv = await searchCpfAsAdvogado(norm.raw);
        if (adv.status === 'found') {
          const data = await fetchDetail(adv.detailUrl, adv.kind);
          renderResult({
            status: 'found',
            origin: 'CPF - Advogado',
            data
          });
          setStatus('Consulta concluída com dados de advogado.', 'ok');
          return;
        }

        setStatus('Não encontrado como advogado. Buscando como pessoa física...', 'muted');
        const pf = await searchCpfAsPessoaFisica(norm.raw);
        if (pf.status === 'empty') {
          renderResult({
            status: 'empty',
            origin: 'CPF - Advogado e Pessoa Física',
            query: norm.display,
            searchLink: buildSearchLink('cpf-pf', norm.raw)
          });
          setStatus('Sem dados em ambas as consultas.', 'ok');
          return;
        }

        const data = await fetchDetail(pf.detailUrl, pf.kind);
        renderResult({
          status: 'found',
          origin: 'CPF - Pessoa Física',
          data
        });
        setStatus('Consulta concluída com dados de pessoa física.', 'ok');
        return;
      }

      setStatus('Buscando CPF diretamente como pessoa física...', 'muted');
      const pf = await searchCpfAsPessoaFisica(norm.raw);
      if (pf.status === 'empty') {
        renderResult({
          status: 'empty',
          origin: 'CPF - Pessoa Física',
          query: norm.display,
          searchLink: buildSearchLink('cpf-pf', norm.raw)
        });
        setStatus('Consulta concluída sem cadastro.', 'ok');
        return;
      }

      const data = await fetchDetail(pf.detailUrl, pf.kind);
      renderResult({
        status: 'found',
        origin: 'CPF - Pessoa Física',
        data
      });
      setStatus('Consulta concluída com dados de pessoa física.', 'ok');
    } catch (e) {
      const message = e && e.message ? e.message : String(e);
      renderResult({ status: 'error', message });
      setStatus('Falha técnica na consulta.', 'error');
    } finally {
      btn.disabled = false;
    }
  }

  function addStyle() {
    if (document.getElementById('tm-trt2-style')) return;
    const s = document.createElement('style');
    s.id = 'tm-trt2-style';
    s.textContent = `
      #tm-trt2-box{position:fixed;top:16px;right:16px;z-index:2147483647;background:#fff;border:1px solid #bbb;border-radius:8px;padding:12px;font:13px/1.4 Arial,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.2);width:380px}
      #tm-trt2-box input,#tm-trt2-box select{width:100%;box-sizing:border-box;margin:6px 0 8px 0;padding:8px;border:1px solid #bbb;border-radius:6px}
      #tm-trt2-box button{padding:8px 10px;border:0;border-radius:6px;background:#0b5ed7;color:#fff;cursor:pointer}
      #tm-trt2-box button:disabled{opacity:.6;cursor:not-allowed}
      #tm-trt2-status{margin-top:8px}
      #tm-trt2-status.muted{color:#666}
      #tm-trt2-status.error{color:#b00020}
      #tm-trt2-status.ok{color:#0a7a24}
      #tm-trt2-result{margin-top:8px;padding-top:8px;border-top:1px solid #e5e5e5}
      .tm-card{padding:8px 0}
      .tm-card > div{margin:2px 0}
      .tm-error{color:#b00020}
      .tm-empty{color:#444}
      .tm-ok{color:#111}
      .tm-row{margin-top:6px}
      .tm-small{font-size:12px;color:#666}
    `;
    document.documentElement.appendChild(s);
  }

  function mount() {
    if (document.getElementById('tm-trt2-box')) return;
    const box = document.createElement('div');
    box.id = 'tm-trt2-box';
    box.innerHTML = `
      <div><strong>TRT2 Dados Bancários</strong></div>
      <div>Documento</div>
      <input id="tm-trt2-doc" type="text" placeholder="CPF ou CNPJ" autocomplete="off" />
      <div>Modo CPF</div>
      <select id="tm-trt2-mode">
        <option value="advogado">Advogado primeiro, depois Pessoa Física</option>
        <option value="pf">Pessoa Física apenas</option>
      </select>
      <div class="tm-small">CNPJ sempre consulta PJ. CPF pode consultar advogado primeiro e, se não achar, cair para PF.</div>
      <button id="tm-trt2-btn">Obter dados</button>
      <div id="tm-trt2-status" class="muted"></div>
      <div id="tm-trt2-result"></div>
    `;
    document.documentElement.appendChild(box);
    document.getElementById('tm-trt2-btn').addEventListener('click', runLookup);
  }

  function boot() {
    addStyle();
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', mount, { once: true });
    } else {
      mount();
    }
  }

  boot();
})();