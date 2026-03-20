// registrar_debito.js
// Módulo PJeTools — Registrar Débito (Obrigação a Pagar)
// Integração com painel/orquestrador: chamar PjeRegistrarDebito.executar()
// Auto-init em /obrigacao-pagar/*/cadastro e /obrigacao-pagar/*/inclusao

(function () {
  'use strict';

  const STORAGE_KEY = 'pje_registrar_debito';

  // ── Utilitários: reutiliza PjeLibParser se carregado, senão define localmente ──
  const _utils = (window.PjeLibParser && window.PjeLibParser.utils) || {
    parseMoney: function (v) {
      if (!v) return 0;
      return parseFloat(v.replace(/[^\d,]/g, '').replace(',', '.')) || 0;
    },
    formatMoney: function (n) {
      if (isNaN(n)) return '0,00';
      return n.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    },
    sleep: function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  };

  // ── Padrões de extração ────────────────────────────────────────────────────────
  const RE = {
    dataCalculo:      /atualizados?\s+para\s+(\d{2}\/\d{2}\/\d{4})/i,
    credito:          /crédito\s+do\s+(?:autor|reclamante|demandante)\s+em\s+R\$\s*([\d.,]+)/i,
    fgts:             /R\$\s*([\d.,]+)\s*(?:relativo\s+ao\s+)?FGTS/i,
    inssReclamante:   /cota\s+do\s+reclamante\)?[^R\n]*R\$\s*([\d.,]+)/i,
    inssReclamada:    /cota-parte\s+no\s+INSS[^R\n]*R\$\s*([\d.,]+)/i,
    honAdvReclamada:  /honorários\s+advocatícios\s+sucumbenciais\s+pela\s+reclamada[^R\n]*R\$\s*([\d.,]+)/i,
    honAdvReclamante: /honorários\s+sucumbenciais\s+pelo\s+(?:autor|reclamante)[^R\n]*R\$\s*([\d.,]+)/i,
    custas:           /custas\s+(?:processuais)?[^R\n]*fixadas?\s+em\s+R\$\s*([\d.,]+)/i,
    honTecnicos:      /honorários\s+técnicos[^R\n]*(?:em|de)\s+R\$\s*([\d.,]+)/i,
    honMedicos:       /honorários\s+médicos[^R\n]*R\$\s*([\d.,]+)/i,
    honContabeis:     /honorários\s+contábeis[^R\n]*R\$\s*([\d.,]+)/i,
    honConhecimento:  /honorários\s+(?:da\s+fase\s+de\s+)?conhecimento[^R\n]*R\$\s*([\d.,]+)/i,
  };

  // ── Extração de dados da decisão ───────────────────────────────────────────────
  function extrairDados(texto) {
    function m(re) {
      var match = texto.match(re);
      return match ? match[1].trim() : null;
    }

    var inssRec  = m(RE.inssReclamante);
    var inssRcd  = m(RE.inssReclamada);
    var inssTotal = (inssRec || inssRcd)
      ? _utils.formatMoney(_utils.parseMoney(inssRec) + _utils.parseMoney(inssRcd))
      : null;

    var honAdvRcd  = m(RE.honAdvReclamada);   // pago pela reclamada → crédito do autor
    var honAdvRec  = m(RE.honAdvReclamante);  // pago pelo reclamante → crédito do réu
    var honAdvTotal = (honAdvRcd || honAdvRec)
      ? _utils.formatMoney(_utils.parseMoney(honAdvRcd) + _utils.parseMoney(honAdvRec))
      : null;

    var somaPericiais = [
      _utils.parseMoney(m(RE.honTecnicos)),
      _utils.parseMoney(m(RE.honMedicos)),
      _utils.parseMoney(m(RE.honContabeis)),
      _utils.parseMoney(m(RE.honConhecimento)),
    ].reduce(function (a, b) { return a + b; }, 0);

    return {
      dataCalculo:   m(RE.dataCalculo),
      credito:       m(RE.credito),
      fgts:          m(RE.fgts),
      inss:          inssTotal,
      inssDetalhes:  { reclamante: inssRec, reclamada: inssRcd },
      honAdv:        honAdvTotal,
      honAdvDetalhes:{ autor: honAdvRcd, reu: honAdvRec },
      custas:        m(RE.custas),
      honPericiais:  somaPericiais > 0 ? _utils.formatMoney(somaPericiais) : null,
    };
  }

  // ── Persistência entre navegações SPA ────────────────────────────────────────
  function salvar(dados)   { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(dados)); }
  function carregar()      { try { return JSON.parse(sessionStorage.getItem(STORAGE_KEY)); } catch (e) { return null; } }
  function limpar()        { sessionStorage.removeItem(STORAGE_KEY); }

  // ── Helpers DOM ───────────────────────────────────────────────────────────────
  function aguardar(seletor, timeout) {
    timeout = timeout || 8000;
    return new Promise(function (resolve, reject) {
      var el = document.querySelector(seletor);
      if (el) return resolve(el);
      var obs = new MutationObserver(function () {
        var found = document.querySelector(seletor);
        if (found) { obs.disconnect(); resolve(found); }
      });
      obs.observe(document.body, { childList: true, subtree: true });
      setTimeout(function () { obs.disconnect(); reject(new Error('Timeout aguardar: ' + seletor)); }, timeout);
    });
  }

  function aguardarUrl(pattern, timeout) {
    timeout = timeout || 10000;
    return new Promise(function (resolve, reject) {
      if (pattern.test(window.location.href)) return resolve();
      var iv = setInterval(function () {
        if (pattern.test(window.location.href)) { clearInterval(iv); resolve(); }
      }, 200);
      setTimeout(function () { clearInterval(iv); reject(new Error('Timeout URL')); }, timeout);
    });
  }

  // ── Preenchimento de input (Angular-safe) ─────────────────────────────────────
  function preencherInput(input, valor) {
    if (!input || valor === null || valor === undefined) return;
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, valor);
    ['input', 'change', 'keyup'].forEach(function (evt) {
      input.dispatchEvent(new Event(evt, { bubbles: true }));
    });
  }

  // currencymask espera float numérico: "1.624.491,78" → "1624491.78"
  function preencherMonetario(input, valorBR) {
    if (!input || !valorBR) return;
    var numerico = valorBR.replace(/\./g, '').replace(',', '.');
    preencherInput(input, numerico);
  }

  function inputPorPlaceholder(ph) {
    return document.querySelector('input[data-placeholder="' + ph + '"]');
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // PASSO 1 — Extrair decisão + navegar para /cadastro
  // Chamado pelo painel quando em /processo/[id]/detalhe
  // ─────────────────────────────────────────────────────────────────────────────
  async function executar() {
    var url     = window.location.href;
    var idMatch = url.match(/\/processo\/(\d+)\/detalhe/);
    if (!idMatch) {
      console.error('[PjeRegistrarDebito] Execute em /processo/[id]/detalhe.');
      return;
    }
    var processoId = idMatch[1];

    if (typeof window.pjeExtrair !== 'function') {
      console.error('[PjeRegistrarDebito] window.pjeExtrair não disponível — verifique se extrair.js está carregado.');
      return;
    }

    console.log('[PjeRegistrarDebito] ⏳ Extraindo documento ativo...');
    var extractor = (typeof window.PjeExtrair === 'function') ? window.PjeExtrair : ((typeof window.pjeExtrair === 'function') ? window.pjeExtrair : null);
    if (!extractor) {
      console.error('[PjeRegistrarDebito] ❌ Extrator não disponível — verifique se core/extrair.js foi carregado.');
      return;
    }
    // solicitar explicitamente o object viewer quando possível
    var res = await extractor({ selector: 'object.conteudo-pdf', timeout: 2000 }).catch(function (e) { return { sucesso: false, erro: e && e.message ? e.message : String(e) }; });

    if (!res.sucesso) {
      console.error('[PjeRegistrarDebito] ❌ Falha na extração:', res.erro);
      return;
    }

    var dados = extrairDados(res.conteudo_bruto || res.conteudo);
    dados._processoId = processoId;

    console.log('[PjeRegistrarDebito] ✅ Dados extraídos:', dados);
    salvar(dados);

    window.location.href = 'https://pje.trt2.jus.br/pjekz/obrigacao-pagar/' + processoId + '/cadastro';
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // PASSO 2 — Selecionar partes + clicar Próximo
  // URL: /obrigacao-pagar/[id]/cadastro
  // ─────────────────────────────────────────────────────────────────────────────
  async function onCadastro() {
    var dados = carregar();
    if (!dados) { console.warn('[PjeRegistrarDebito] Sem estado em sessão — abortando.'); return; }

    try {
      await aguardar('table.t-class', 8000);
      await _utils.sleep(600);

      var linhas = Array.from(document.querySelectorAll('tbody tr.tr-class'));

      function posicaoLinha(tr) {
        var span = tr.querySelector('.mat-select-min-line');
        return span ? span.textContent.trim() : '';
      }

      var credorRow  = linhas.find(function (tr) { return posicaoLinha(tr) === 'Credor'; });
      var devedorRow = linhas.find(function (tr) { return posicaoLinha(tr) === 'Devedor'; });

      [credorRow, devedorRow].forEach(function (tr) {
        if (!tr) return;
        var cb = tr.querySelector('input[type="checkbox"]');
        if (cb && !cb.checked) cb.click();
      });

      await _utils.sleep(300);

      var btnProximo = document.querySelector('button[name="proximo"]');
      if (!btnProximo) { console.error('[PjeRegistrarDebito] Botão Próximo não encontrado.'); return; }
      btnProximo.click();

      await aguardarUrl(/\/obrigacao-pagar\/\d+\/inclusao/, 10000);
      await _utils.sleep(600);
      await onInclusao();

    } catch (e) {
      console.error('[PjeRegistrarDebito] Erro em onCadastro:', e);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // PASSO 3 — Preencher campos + exibir card de resumo
  // URL: /obrigacao-pagar/[id]/inclusao
  // ─────────────────────────────────────────────────────────────────────────────
  async function onInclusao() {
    var dados = carregar();
    if (!dados) { console.warn('[PjeRegistrarDebito] Sem estado em sessão — abortando.'); return; }

    try {
      await aguardar('input[data-placeholder="Crédito do demandante"]', 8000);
      await _utils.sleep(400);

      // Data do Cálculo
      if (dados.dataCalculo) {
        var inputData = inputPorPlaceholder('Data do Cálculo');
        if (inputData) preencherInput(inputData, dados.dataCalculo);
      }

      // Campos monetários → mapeamento placeholder : valor extraído
      var mapa = [
        ['Crédito do demandante',      dados.credito],
        ['Contribuição Previdenciária', dados.inss],
        ['Custas',                      dados.custas],
        ['Honorários Advocatícios',     dados.honAdv],
        ['Honorários Periciais',        dados.honPericiais],
      ];

      for (var i = 0; i < mapa.length; i++) {
        var placeholder = mapa[i][0];
        var valor       = mapa[i][1];
        if (!valor) continue;
        var input = inputPorPlaceholder(placeholder);
        if (input) {
          preencherMonetario(input, valor);
          await _utils.sleep(120);
        } else {
          console.warn('[PjeRegistrarDebito] Campo "' + placeholder + '" não encontrado na página.');
        }
      }

      _mostrarCard(dados);
      limpar();
      console.log('[PjeRegistrarDebito] ✅ Preenchimento concluído.');

    } catch (e) {
      console.error('[PjeRegistrarDebito] Erro em onInclusao:', e);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Card de resumo — centro-inferior da página
  // ─────────────────────────────────────────────────────────────────────────────
  function _mostrarCard(dados) {
    var id = 'pje-debito-resumo-card';
    var existing = document.getElementById(id);
    if (existing) existing.remove();

    function row(label, valor, detalhe) {
      if (!valor) return '';
      return '<tr>'
        + '<td style="color:#a6adc8;padding:4px 14px 4px 0;font-size:12px;white-space:nowrap">' + label + '</td>'
        + '<td style="font-weight:700;font-size:13px;padding:4px 0;color:#cdd6f4">R$ ' + valor + '</td>'
        + '<td style="color:#6c7086;font-size:11px;padding:4px 0 4px 10px">' + (detalhe || '') + '</td>'
        + '</tr>';
    }

    var inssDetalhe = dados.inssDetalhes
      ? ('Rec: ' + (dados.inssDetalhes.reclamante || '—') + ' · Rcd: ' + (dados.inssDetalhes.reclamada || '—'))
      : '';
    var honAdvDetalhe = dados.honAdvDetalhes
      ? ('Autor: ' + (dados.honAdvDetalhes.autor || '—') + ' · Réu: ' + (dados.honAdvDetalhes.reu || '—'))
      : '';

    var html = '<div id="' + id + '" style="'
      + 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);'
      + 'background:#1e1e2e;color:#cdd6f4;border-radius:10px;'
      + 'box-shadow:0 6px 28px rgba(0,0,0,.55);padding:16px 22px;'
      + 'z-index:99999;min-width:400px;font-family:sans-serif;'
      + 'border:1px solid #313244;">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
      +   '<span style="font-weight:700;font-size:14px;color:#cba6f7">📋 Débito Registrado</span>'
      +   '<span style="color:#6c7086;font-size:11px">' + (dados.dataCalculo || '') + '</span>'
      +   '<button onclick="document.getElementById(\'' + id + '\').remove()" '
      +     'style="background:none;border:none;color:#6c7086;cursor:pointer;font-size:17px;line-height:1;padding:0 2px;margin-left:12px">✕</button>'
      + '</div>'
      + '<table style="width:100%;border-collapse:collapse">'
      +   row('Crédito Principal', dados.credito)
      +   row('FGTS',              dados.fgts)
      +   row('INSS',              dados.inss,        inssDetalhe)
      +   row('Hon. Advocatícios', dados.honAdv,      honAdvDetalhe)
      +   row('Custas',            dados.custas)
      +   row('Hon. Periciais',    dados.honPericiais)
      + '</table>'
      + '</div>';

    document.body.insertAdjacentHTML('beforeend', html);
  }

  // autoInit removed: orquestrador centraliza chamadas para onCadastro/onInclusao

  // ─────────────────────────────────────────────────────────────────────────────
  // API Pública
  // ─────────────────────────────────────────────────────────────────────────────
  window.PjeRegistrarDebito = {
    executar:     executar,    // chamar do painel em /detalhe
    onCadastro:   onCadastro,  // chamada explícita pelo orquestrador se necessário
    onInclusao:   onInclusao,  // chamada explícita pelo orquestrador se necessário
    extrairDados: extrairDados // utilitário de teste/debug
  };

  console.log('[PjeRegistrarDebito] ✅ Módulo carregado.');

})();
