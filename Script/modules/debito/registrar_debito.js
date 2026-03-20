// registrar_debito.js
// Módulo PJeTools — Registrar Débito (Obrigação a Pagar)

(function () {
  'use strict';

  const STORAGE_KEY = 'pje_registrar_debito';

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

  // ── Padrões de extração ────────────────────────────────────────────────────
  const RE = {
    dataCalculo: /atualizados?\s+para\s+(\d{2}\/\d{2}\/\d{4})/i,
    credito:     /crédito\s+do\s+(?:autor|reclamante|demandante)[\s\S]{0,30}?R\$\s*([\d.,]+)/i,
    fgts:        /R\$\s*([\d.,]+)[\s\S]{0,30}?FGTS|FGTS[\s\S]{0,60}?R\$\s*([\d.,]+)/i,

    // FIX 1: captura tanto "(cota do reclamante)" quanto "descontos previdenciários (cota do reclamante)"
    inssReclamante: /\(cota\s+do\s+reclamante\)[\s\S]{0,100}?R\$\s*([\d.,]+)/i,
    inssReclamada:  /cota-parte\s+no\s+INSS[\s\S]{0,80}?R\$\s*([\d.,]+)/i,

    honAdvReclamada:  /honorários\s+advocatícios\s+sucumbenciais\s+pela\s+reclamada[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honAdvReclamante: /honorários\s+sucumbenciais\s+pelo\s+(?:autor|reclamante)[\s\S]{0,80}?R\$\s*([\d.,]+)/i,

    // FIX 2: captura "Custas de R$X" E "Custas fixadas em R$X"
    custas: /custas\s+de\s+R\$\s*([\d.,]+)|custas[\s\S]{0,60}?fixadas?\s+em\s+R\$\s*([\d.,]+)/i,

    honTecnicos:    /honorários\s+técnicos[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honMedicos:     /honorários\s+médicos[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honContabeis:   /honorários\s+contábeis[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honConhecimento:/honorários[\s\S]{0,30}?fase\s+de\s+conhecimento[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
  };

  // Renomeado: extrairDadosDoPart(txt, isPrimeiro)
  // isPrimeiro=false -> não extrai custas/honorários (usado para blocos secundários)
  function extrairDadosDoPart(txt, isPrimeiro) {
    txt = txt.replace(/ \| /g, ' ').replace(/[ \t]{2,}/g, ' ');

    function m(re) {
      var match = txt.match(re);
      if (!match) return null;
      for (var i = 1; i < match.length; i++) {
        if (match[i]) return match[i].trim();
      }
      return null;
    }

    var inssRec = m(RE.inssReclamante);
    var inssRcd = m(RE.inssReclamada);
    var inssTotal = (inssRec || inssRcd)
      ? _utils.formatMoney(_utils.parseMoney(inssRec) + _utils.parseMoney(inssRcd))
      : null;

    var honAdvRcd = isPrimeiro ? m(RE.honAdvReclamada)  : null;
    var honAdvRec = isPrimeiro ? m(RE.honAdvReclamante) : null;
    var honAdvTotal = (honAdvRcd || honAdvRec)
      ? _utils.formatMoney(_utils.parseMoney(honAdvRcd) + _utils.parseMoney(honAdvRec))
      : null;

    var somaPericiais = isPrimeiro
      ? [m(RE.honTecnicos), m(RE.honMedicos), m(RE.honContabeis), m(RE.honConhecimento)]
          .reduce(function (a, v) { return a + _utils.parseMoney(v); }, 0)
      : 0;

    return {
      dataCalculo:    m(RE.dataCalculo),
      credito:        m(RE.credito),
      fgts:           m(RE.fgts),
      inss:           inssTotal,
      inssDetalhes:   { reclamante: inssRec, reclamada: inssRcd },
      honAdv:         honAdvTotal,
      honAdvDetalhes: { autor: honAdvRcd, reu: honAdvRec },
      custas:         isPrimeiro ? m(RE.custas) : null,
      honPericiais:   somaPericiais > 0 ? _utils.formatMoney(somaPericiais) : null,
    };
  }

  // Extrai blocos separados por ocorrências de HOMOLOGO — primeiro bloco é considerado 'primeiro'
  function extrairBlocos(textoRaw) {
    var txt = textoRaw.replace(/ \| /g, ' ').replace(/[ \t]{2,}/g, ' ');

    var partes = txt.split(/(?=HOMOLOGO)/i).filter(function (p) { return /HOMOLOGO/i.test(p); });
    if (partes.length === 0) return [extrairDadosDoPart(txt, true)];

    return partes.map(function (parte, idx) { return extrairDadosDoPart(parte, idx === 0); });
  }

  // ── Persistência ─────────────────────────────────────────────────────────────
  function salvar(dados)  { localStorage.setItem(STORAGE_KEY, JSON.stringify(dados)); }
  function carregar()     { try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch(e) { return null; } }
  function limpar()       { localStorage.removeItem(STORAGE_KEY); }

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
      setTimeout(function () { obs.disconnect(); reject(new Error('Timeout: ' + seletor)); }, timeout);
    });
  }

  function preencherInput(input, valor) {
    if (!input || valor === null || valor === undefined) return;
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, valor);
    ['input', 'change', 'keyup'].forEach(function (evt) {
      input.dispatchEvent(new Event(evt, { bubbles: true }));
    });
  }

  // FIX 3: cola o valor exatamente como extraído (ex: "1.624.491,78"), sem converter para float.
  // Remove apenas o prefixo "R$" se presente.
  function preencherMonetario(input, valorBR) {
    if (!input || !valorBR) return;
    var valor = valorBR.replace(/R\$\s*/g, '').trim();
    preencherInput(input, valor);
  }

  function inputPorPlaceholder(ph) {
    return document.querySelector('input[data-placeholder="' + ph + '"]');
  }

  // ── PASSO 1 — Extrair + abrir /cadastro em nova aba ──────────────────────────
  async function executar() {
    var url = window.location.href;
    var idMatch = url.match(/\/processo\/(\d+)\/detalhe/);
    if (!idMatch) { console.error('[PjeRegistrarDebito] Execute em /processo/[id]/detalhe.'); return; }
    var processoId = idMatch[1];

    var obj = document.querySelector('object.conteudo-pdf');
    if (!obj) {
      alert('⚠️ Abra um documento no visualizador antes de clicar em Débito.\n\nClique no documento de homologação na timeline e tente novamente.');
      return;
    }

    var extractor = window.pjeExtrair || window.PjeExtrair;
    if (typeof extractor !== 'function') {
      console.error('[PjeRegistrarDebito] pjeExtrair não disponível.');
      return;
    }

    console.log('[PjeRegistrarDebito] ⏳ Extraindo...');
    var res = await extractor().catch(function (e) {
      return { sucesso: false, erro: e && e.message ? e.message : String(e) };
    });

    if (!res.sucesso) {
      console.error('[PjeRegistrarDebito] ❌ Falha na extração:', res.erro);
      alert('❌ Falha na extração:\n' + res.erro);
      return;
    }

    var textoRaw = res.conteudo_bruto || res.conteudo || '';
    console.log('[PjeRegistrarDebito] 📄 Texto (' + textoRaw.length + ' chars):', textoRaw.substring(0, 800));

    var blocos = extrairBlocos(textoRaw);
    console.log('[PjeRegistrarDebito] ✅ Blocos extraídos (' + blocos.length + '):', blocos);

    var algumValor = blocos[0].credito || blocos[0].fgts || blocos[0].inss;
    if (!algumValor) {
      var continuar = confirm('⚠️ Nenhum valor extraído.\n\nVeja o console (F12).\n\nProsseguir mesmo assim?');
      if (!continuar) return;
    }

    salvar({ blocos: blocos, blocoAtual: 0, processoId: processoId });
    window.open('https://pje.trt2.jus.br/pjekz/obrigacao-pagar/' + processoId + '/cadastro', '_blank');
  }

  // ── PASSO 2 — /cadastro: marcar partes + avançar ──────────────────────────────
  async function onCadastro() {
    var dados = carregar();
    if (!dados) { console.warn('[PjeRegistrarDebito] Sem dados em localStorage.'); return; }

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

      var started = Date.now();
      await new Promise(function (resolve, reject) {
        var iv = setInterval(function () {
          if (/\/obrigacao-pagar\/\d+\/inclusao/.test(window.location.href)) { clearInterval(iv); resolve(); }
          else if (Date.now() - started > 10000) { clearInterval(iv); reject(new Error('Timeout /inclusao')); }
        }, 200);
      });

      await _utils.sleep(600);
      await onInclusao();

    } catch (e) { console.error('[PjeRegistrarDebito] Erro em onCadastro:', e); }
  }

  // ── PASSO 3 — /inclusao: preencher campos ────────────────────────────────────
  async function onInclusao() {
    var estado = carregar();
    if (!estado || !estado.blocos) { console.warn('[PjeRegistrarDebito] Sem dados.'); return; }

    var idx    = estado.blocoAtual || 0;
    var blocos = estado.blocos;
    var dados  = blocos[idx];
    var total  = blocos.length;

    try {
      await aguardar('input[data-placeholder="Crédito do demandante"]', 8000);
      await _utils.sleep(400);

      if (dados.dataCalculo) {
        var inputData = inputPorPlaceholder('Data do Cálculo');
        if (inputData) { preencherInput(inputData, dados.dataCalculo); await _utils.sleep(150); }
      }

      var mapa = [
        ['Crédito do demandante',         dados.credito],
        ['Outras Obrigações Pecuniárias',  dados.fgts],
        ['Contribuição Previdenciária',    dados.inss],
        ['Custas',                         dados.custas],
        ['Honorários Advocatícios',        dados.honAdv],
        ['Honorários Periciais',           dados.honPericiais],
      ];

      for (var i = 0; i < mapa.length; i++) {
        var ph  = mapa[i][0], val = mapa[i][1];
        if (!val) continue;
        var inp = inputPorPlaceholder(ph);
        if (inp) { preencherMonetario(inp, val); await _utils.sleep(200); }
        else console.warn('[PjeRegistrarDebito] Campo não encontrado: "' + ph + '"');
      }

      // Trigger Angular no campo crédito
      var inputCredito = inputPorPlaceholder('Crédito do demandante');
      if (inputCredito && inputCredito.value) {
        inputCredito.focus();
        await _utils.sleep(150);
        var v = inputCredito.value;
        preencherInput(inputCredito, v.slice(0, -1));
        await _utils.sleep(150);
        preencherInput(inputCredito, v);
        inputCredito.dispatchEvent(new Event('blur', { bubbles: true }));
        await _utils.sleep(150);
      }

      // Há mais blocos?
      if (idx + 1 < total) {
        // Atualiza índice e avisa o usuário
        estado.blocoAtual = idx + 1;
        salvar(estado);

        _mostrarCardAviso(idx + 1, total);

        // Aguarda botão Salvar ficar desabilitado (novo painel aberto pelo usuário)
        await _aguardarSalvarDesabilitado();
        await _utils.sleep(500);

        // Preenche próximo bloco recursivamente
        await onInclusao();

      } else {
        // Último bloco
        _mostrarCard(dados, idx + 1, total);
        limpar();
        console.log('[PjeRegistrarDebito] ✅ Todos os ' + total + ' blocos preenchidos.');
      }

    } catch (e) { console.error('[PjeRegistrarDebito] Erro em onInclusao:', e); }
  }

  // ── Card de resumo ─────────────────────────────────────────────────────────────
  // Card de aviso multi-bloco
  function _mostrarCardAviso(proximoIdx, total) {
    var id = 'pje-debito-aviso-card';
    var el = document.getElementById(id);
    if (el) el.remove();

    var registrados = proximoIdx; // já preencheu até aqui
    var restam      = total - proximoIdx;
    var msg = registrados + ' cálculo(s) registrado(s). '
      + (restam > 0
          ? 'Clique em <b>Incluir Obrigação</b> para adicionar o próximo responsável.'
          : 'Todos os cálculos registrados — finalizado.');

    document.body.insertAdjacentHTML('beforeend',
      '<div id="' + id + '" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);'
      + 'background:#1e1e2e;color:#cdd6f4;border-radius:10px;box-shadow:0 6px 28px rgba(0,0,0,.55);'
      + 'padding:16px 22px;z-index:99999;min-width:400px;font-family:sans-serif;border:1px solid #fab387;">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;gap:16px">'
      +   '<span style="font-size:13px;color:#fab387">⚠️ Cálculos diversos detectados</span>'
      +   '<button onclick="document.getElementById(\'' + id + '\').remove()" '
      +     'style="background:none;border:none;color:#6c7086;cursor:pointer;font-size:17px">✕</button>'
      + '</div>'
      + '<p style="margin:10px 0 0;font-size:13px;line-height:1.5">' + msg + '</p>'
      + '</div>'
    );
  }

  // Aguarda botão Salvar ficar disabled (indica novo painel aberto)
  function _aguardarSalvarDesabilitado(timeout) {
    timeout = timeout || 30000;
    return new Promise(function (resolve, reject) {
      var started = Date.now();
      var iv = setInterval(function () {
        var btn = document.querySelector('button[name="salvar"]');
        if (btn && btn.disabled) { clearInterval(iv); resolve(); }
        if (Date.now() - started > timeout) { clearInterval(iv); reject(new Error('Timeout salvar disabled')); }
      }, 300);
    });
  }
  function _mostrarCard(dados, numAtual, total) {
    var id = 'pje-debito-resumo-card';
    var el = document.getElementById(id);
    if (el) el.remove();

    function row(label, valor, detalhe) {
      if (!valor) return '';
      return '<tr>'
        + '<td style="color:#a6adc8;padding:4px 14px 4px 0;font-size:12px;white-space:nowrap">' + label + '</td>'
        + '<td style="font-weight:700;font-size:13px;color:#cdd6f4">R$ ' + valor + '</td>'
        + '<td style="color:#6c7086;font-size:11px;padding-left:10px">' + (detalhe || '') + '</td>'
        + '</tr>';
    }

    var inssD = dados.inssDetalhes
      ? 'Autor: ' + (dados.inssDetalhes.reclamante || '—') + ' · Rcd: ' + (dados.inssDetalhes.reclamada || '—')
      : '';
    var honD = dados.honAdvDetalhes
      ? 'Autor: ' + (dados.honAdvDetalhes.autor || '—') + ' · Réu: ' + (dados.honAdvDetalhes.reu || '—')
      : '';

    var titulo = total > 1
      ? '📋 Débito Registrado (' + (numAtual || 1) + '/' + total + ')'
      : '📋 Débito Registrado';

    document.body.insertAdjacentHTML('beforeend',
      '<div id="' + id + '" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);'
      + 'background:#1e1e2e;color:#cdd6f4;border-radius:10px;box-shadow:0 6px 28px rgba(0,0,0,.55);'
      + 'padding:16px 22px;z-index:99999;min-width:420px;font-family:sans-serif;border:1px solid #313244;">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
      +   '<span style="font-weight:700;font-size:14px;color:#cba6f7">' + titulo + '</span>'
      +   '<span style="color:#6c7086;font-size:11px">' + (dados.dataCalculo || '') + '</span>'
      +   '<button onclick="document.getElementById(\'' + id + '\').remove()" '
      +     'style="background:none;border:none;color:#6c7086;cursor:pointer;font-size:17px;margin-left:12px">✕</button>'
      + '</div>'
      + '<table style="width:100%;border-collapse:collapse">'
      +   row('Crédito Principal', dados.credito)
      +   row('FGTS',              dados.fgts)
      +   row('INSS (total)',       dados.inss, inssD)
      +   row('Hon. Advocatícios', dados.honAdv, honD)
      +   row('Custas',            dados.custas)
      +   row('Hon. Periciais',    dados.honPericiais)
      + '</table>'
      + '</div>'
    );
  }

  // ── Auto-init ─────────────────────────────────────────────────────────────────
  (function autoInit() {
    var url = window.location.href;
    if (/\/obrigacao-pagar\/\d+\/cadastro/.test(url))      setTimeout(onCadastro, 1500);
    else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(url)) setTimeout(onInclusao, 1500);
  })();

  // ── API Pública ───────────────────────────────────────────────────────────────
  window.PjeRegistrarDebito = {
    executar:     executar,
    onCadastro:   onCadastro,
    onInclusao:   onInclusao,
    extrairBlocos: extrairBlocos,
    extrairDadosDoPart: extrairDadosDoPart,
    // compat: manter `extrairDados` como alias retornando blocos
    extrairDados: extrairBlocos
  };

  console.log('[PjeRegistrarDebito] ✅ Módulo carregado.');

})();
