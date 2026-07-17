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
    // FIX: Tolerância a quebras de linha e espaços entre "atualizado" e a data
    dataCalculo: /atualizad[\s\S]{0,60}?(\d{2}\/\d{2}\/\d{4})/i,
    
    // FIX: Plano B - Procura uma data até 100 caracteres antes ou depois da palavra INSS
    dataCalculoFallback: /inss[\s\S]{0,100}?(\d{2}\/\d{2}\/\d{4})|(\d{2}\/\d{2}\/\d{4})[\s\S]{0,100}?inss/i,

    credito:     /crédito\s+do\s+(?:autor|reclamante|demandante)[\s\S]{0,30}?R\$\s*([\d.,]+)/i,
    fgts:        /R\$\s*([\d.,]+)[\s\S]{0,30}?FGTS|FGTS[\s\S]{0,60}?R\$\s*([\d.,]+)/i,
    inssReclamante: /\(cota\s+do\s+reclamante\)[\s\S]{0,100}?R\$\s*([\d.,]+)/i,
    inssReclamada:  /cota[\s-]*parte\s+no\s+INSS[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honAdvReclamada:  /honorários\s+advocatícios\s+(?:sucumbenciais\s+)?pela\s+reclamada[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honAdvReclamante: /honorários\s+sucumbenciais\s+pelo\s+(?:autor|reclamante)[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    custas: /custas\s+de\s*(?:\|\s*)?R\$\s*([\d.,]+)(?:\s*\|)?/i,
    honTecnicos:    /honorários\s+(?:periciais\s+)?técnicos[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honMedicos:     /honorários\s+médicos[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honContabeis:   /honorários\s+(?:periciais\s+)?contábeis[\s\S]{0,80}?R\$\s*([\d.,]+)/i,
    honConhecimento:/honorários\s+periciais\s+da\s+fase\s+de\s+conhecimento[\s\S]{0,200}?R\$\s*([\d.,]+)/i,
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

    // Honorários advocatícios devem ser extraídos de TODOS os blocos
    var honAdvRcd = m(RE.honAdvReclamada);
    var honAdvRec = m(RE.honAdvReclamante);
    var honAdvTotal = (honAdvRcd || honAdvRec)
      ? _utils.formatMoney(_utils.parseMoney(honAdvRcd) + _utils.parseMoney(honAdvRec))
      : null;

    var periciaisList = [];
    if (isPrimeiro) {
      var perRegexes = [RE.honTecnicos, RE.honMedicos, RE.honContabeis, RE.honConhecimento];
      perRegexes.forEach(function (r) {
        var match = txt.match(r);
        if (!match) return;
        // obter primeiro grupo com valor
        var val = null; for (var i = 1; i < match.length; i++) { if (match[i]) { val = match[i].trim(); break; } }
        if (!val) return;
        var idx = txt.search(r);
        var ctx = txt.substr(Math.max(0, idx - 20), 140).toLowerCase();
        // Ignorar se o contexto indicar que foi pago pelo TRT ou pelo reclamante
        if (/pago[s]? pelo trt|pelo trt|pago[s]? pelo reclamante|pelo reclamante|somente o reclamante/i.test(ctx)) return;
        periciaisList.push(val);
      });
    }
    var somaPericiais = periciaisList.length
      ? periciaisList.map(function (v) { return _utils.parseMoney(v); }).reduce(function (a, b) { return a + b; }, 0)
      : 0;

    // Tenta achar a data pela palavra 'atualizado', se não achar, usa o fallback do 'INSS'
    var dataCalc = m(RE.dataCalculo) || m(RE.dataCalculoFallback);

    return {
      dataCalculo:    dataCalc,
      credito:        m(RE.credito),
      fgts:           m(RE.fgts),
      inss:           inssTotal,
      inssDetalhes:   { reclamante: inssRec, reclamada: inssRcd },
      honAdv:         honAdvTotal,
      honAdvDetalhes: { autor: honAdvRcd, reu: honAdvRec },
      custas:         isPrimeiro ? m(RE.custas) : null,
      honPericiais:   somaPericiais > 0 ? _utils.formatMoney(somaPericiais) : null,
      honPericiaisDetalhes: periciaisList.length ? periciaisList : null,
    };
  }

  // Extrai blocos separados por ocorrências de HOMOLOGO — primeiro bloco é considerado 'primeiro'
  function extrairBlocos(textoRaw) {
    var txt = textoRaw.replace(/ \| /g, ' ').replace(/[ \t]{2,}/g, ' ');

    var partes = txt.split(/(?=HOMOLOGO)/i).filter(function (p) { return /HOMOLOGO/i.test(p); });
    if (partes.length === 0) return [extrairDadosDoPart(txt, true)];

    var blocos = partes.map(function (parte, idx) { return extrairDadosDoPart(parte, idx === 0); });

    // --- Extrai custas e honorários periciais do texto completo ---
    var primeiroBloco = blocos[0];

    var custasMatch = txt.match(RE.custas);
    if (custasMatch && custasMatch[1]) {
      primeiroBloco.custas = custasMatch[1];
    }

    var periciaisTotal = 0;
    var periciaisDetalhes = [];

    var contabeisMatch = txt.match(RE.honContabeis);
    if (contabeisMatch && contabeisMatch[1]) {
      periciaisTotal += _utils.parseMoney(contabeisMatch[1]);
      periciaisDetalhes.push(contabeisMatch[1]);
    }

    var conhecimentoMatch = txt.match(RE.honConhecimento);
    if (conhecimentoMatch && conhecimentoMatch[1]) {
      periciaisTotal += _utils.parseMoney(conhecimentoMatch[1]);
      periciaisDetalhes.push(conhecimentoMatch[1]);
    }

    if (periciaisTotal > 0) {
      primeiroBloco.honPericiais = _utils.formatMoney(periciaisTotal);
      primeiroBloco.honPericiaisDetalhes = periciaisDetalhes;
    }

    return blocos;
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
// FIX 3 — Estratégia C (KeyboardEvent char a char) — única que habilita Salvar
async function preencherMonetario(input, valorBR) {
  if (!input || !valorBR) return;

  // Remove R$, pontos de milhar e vírgula decimal — envia só dígitos
  // A currency mask do PJe formata automaticamente enquanto digita
  var apenasDigitos = valorBR.replace(/R\$\s*/g, '').replace(/\./g, '').replace(',', '').trim();

  var set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;

  input.focus();
  await _utils.sleep(80);

  // Limpa campo
  set.call(input, '');
  input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
  await _utils.sleep(40);

  // Digita dígito por dígito simulando teclado real
  for (var i = 0; i < apenasDigitos.length; i++) {
    var ch = apenasDigitos[i];
    input.dispatchEvent(new KeyboardEvent('keydown',  { key: ch, bubbles: true, cancelable: true }));
    input.dispatchEvent(new KeyboardEvent('keypress', { key: ch, bubbles: true, cancelable: true, charCode: ch.charCodeAt(0) }));
    // REMOVIDO: set.call(input, input.value + ch)
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: ch }));
    input.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true }));
    await _utils.sleep(30);
  }

  input.dispatchEvent(new Event('change', { bubbles: true }));
  input.dispatchEvent(new Event('blur',   { bubbles: true }));
  await _utils.sleep(60);
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

    // Trava de segurança atualizada: procura o PDF ou a nova classe da Minuta
    var objPdf = document.querySelector('object.conteudo-pdf');
    var objMinuta = document.querySelector('mat-card.container-html, .visualizador-html');

    if (!objPdf && !objMinuta) {
      alert('⚠️ Abra um documento (PDF ou Minuta) no visualizador antes de clicar em Débito.\n\nClique no documento de homologação na timeline e tente novamente.');
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

    var blocos = estado.blocos;
    // Guardamos os blocos globalmente para os botões poderem acessar depois
    window._pjeDebitoBlocos = blocos; 

    try {
      await aguardar('input[data-placeholder="Crédito do demandante"]', 8000);
      await _utils.sleep(400);

      // Preenche APENAS o primeiro bloco automaticamente ao carregar a página
      await _preencherCampos(blocos[0]);

      // Mostra a interface unificada com o aviso e todos os blocos
      _mostrarPainelResumo(blocos);

      // Limpa o storage, pois os dados já estão salvos na tela e na variável global
      limpar();
      console.log('[PjeRegistrarDebito] ✅ Painel carregado.');

    } catch (e) { console.error('[PjeRegistrarDebito] Erro em onInclusao:', e); }
  }

  // Lógica de preenchimento isolada para ser reusada pelos botões
  async function _preencherCampos(dados) {
    console.log('[PjeRegistrarDebito] Iniciando preenchimento dos campos', dados);

    if (!dados || typeof dados !== 'object') {
      console.error('[PjeRegistrarDebito] dados inválidos em _preencherCampos:', dados);
      throw new Error('dados inválidos para _preencherCampos');
    }

    if (dados.dataCalculo) {
      var inputData = inputPorPlaceholder('Data do Cálculo');
      if (inputData) {
        console.log('[PjeRegistrarDebito] Preenchendo data:', dados.dataCalculo);
        preencherInput(inputData, dados.dataCalculo);
        await _utils.sleep(150);
      } else {
        console.warn('[PjeRegistrarDebito] Campo "Data do Cálculo" não encontrado');
      }
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
      var ph  = mapa[i][0];
      var val = mapa[i][1];
      if (!val) continue;
      var inp = inputPorPlaceholder(ph);
      if (inp) {
        console.log('[PjeRegistrarDebito] Preenchendo ' + ph + ': ' + val);
        await preencherMonetario(inp, val);
        await _utils.sleep(80);
      } else {
        console.warn('[PjeRegistrarDebito] Campo não encontrado: "' + ph + '"');
      }
    }

    console.log('[PjeRegistrarDebito] Preenchimento finalizado');
  }

  // ── Painel Unificado de Resumo ────────────────────────────────────────────────
  function _mostrarPainelResumo(blocos) {
    var id = 'pje-debito-painel-resumo';
    var el = document.getElementById(id);
    if (el) el.remove();

    var temVarios = blocos.length > 1;

    // Container principal fixo no canto superior direito (para não cobrir os inputs centrais)
    var html = '<div id="' + id + '" style="position:fixed;top:20px;right:30px;width:340px;'
             + 'background:#1e1e2e;color:#cdd6f4;border-radius:8px;box-shadow:0 6px 28px rgba(0,0,0,.6);'
             + 'z-index:99999;font-family:sans-serif;border:1px solid #313244;display:flex;flex-direction:column;max-height:90vh;">';

    // CABEÇALHO / AVISO (Colado no topo)
    html += '<div style="background:' + (temVarios ? '#fab387' : '#cba6f7') + ';color:#11111b;padding:12px 16px;border-radius:7px 7px 0 0;display:flex;justify-content:space-between;align-items:center;">'
          +   '<span style="font-weight:bold;font-size:14px;">'
          +     (temVarios ? '⚠️ ' + blocos.length + ' Cálculos Detectados' : '📋 Débito Extraído')
          +   '</span>'
          +   '<button onclick="document.getElementById(\'' + id + '\').remove()" style="background:none;border:none;color:#11111b;cursor:pointer;font-size:16px;font-weight:bold;">✕</button>'
          + '</div>';

    // CONTEÚDO SCROLLÁVEL COM OS CARDS
    html += '<div style="padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;">';

    blocos.forEach(function(dados, i) {
      var inssD = dados.inssDetalhes ? ('Aut: ' + (dados.inssDetalhes.reclamante || '—') + ' | Réu: ' + (dados.inssDetalhes.reclamada || '—')) : '';
      var honD = dados.honAdvDetalhes ? ('Aut: ' + (dados.honAdvDetalhes.autor || '—') + ' | Réu: ' + (dados.honAdvDetalhes.reu || '—')) : '';

      function makeRow(label, valor, detalhe) {
        if (!valor) return '';
        return '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;border-bottom:1px solid #313244;padding-bottom:2px;">'
             + '<span style="color:#a6adc8;">' + label + '</span>'
             + '<span style="font-weight:bold;">R$ ' + valor + '</span>'
             + '</div>'
             + (detalhe ? '<div style="font-size:10px;color:#6c7086;text-align:right;margin-top:-2px;margin-bottom:6px;">' + detalhe + '</div>' : '');
      }

      // CARD DO BLOCO
      html += '<div style="background:#181825;padding:12px;border-radius:6px;border:1px solid #45475a;">';
      html += '<div style="font-weight:bold;font-size:13px;color:#89b4fa;margin-bottom:10px;">Bloco ' + (i + 1) + (i === 0 ? ' (Preenchido)' : '') + '</div>';

      if (dados.dataCalculo) html += makeRow('Data', dados.dataCalculo);
      html += makeRow('Principal', dados.credito);
      html += makeRow('FGTS', dados.fgts);
      html += makeRow('INSS', dados.inss, inssD);
      html += makeRow('Honorários', dados.honAdv, honD);
      html += makeRow('Custas', dados.custas);
      var pDetalhes = dados.honPericiaisDetalhes ? ' [' + dados.honPericiaisDetalhes.join(' + ') + ']' : '';
      html += makeRow('Periciais', dados.honPericiais, pDetalhes);

      // BOTÃO DE INSERIR APENAS PARA OS PRÓXIMOS BLOCOS
      if (i > 0) {
         html += '<button data-debito-bloco="' + i + '" '
               + 'style="margin-top:10px;width:100%;padding:8px;background:#a6e3a1;color:#11111b;border:none;border-radius:4px;font-weight:bold;cursor:pointer;font-size:12px;transition:0.2s;">'
               + '⬇️ Inserir Valores na Tela'
               + '</button>';
      }

      html += '</div>';
    });

    html += '</div></div>';
    document.body.insertAdjacentHTML('beforeend', html);

    // FIX: event delegation no sandbox — sem dependência de unsafeWindow
    document.querySelectorAll('[data-debito-bloco]').forEach(function(btn) {
        btn.addEventListener('click', async function() {
            var idx = parseInt(btn.getAttribute('data-debito-bloco'));
            await window.PjeRegistrarDebito.acionarPreenchimento(btn, idx);
        });
    });
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
    extrairDados: extrairBlocos,

    acionarPreenchimento: async function(btn, idx) {
      console.log(`[PjeRegistrarDebito] Botão clicado para bloco ${idx}`);
      if (!window._pjeDebitoBlocos) {
        console.error('[PjeRegistrarDebito] _pjeDebitoBlocos não definido');
        alert('Erro: blocos não disponíveis. Recarregue a página.');
        return;
      }

      const dadosBloco = window._pjeDebitoBlocos[idx];
      if (!dadosBloco) {
        console.error(`[PjeRegistrarDebito] Dados do bloco ${idx} não encontrados`);
        btn.innerText = '❌ Bloco não encontrado';
        return;
      }

      console.log('[PjeRegistrarDebito] Dados a preencher:', dadosBloco);
      btn.innerText = '⏳ Preenchendo...';
      btn.style.opacity = '0.7';
      btn.disabled = true;

      try {
        await _preencherCampos(dadosBloco);
        btn.innerText = '✅ Valores Inseridos';
        btn.style.background = '#89b4fa';
        console.log(`[PjeRegistrarDebito] Preenchimento concluído para bloco ${idx}`);
      } catch (err) {
        console.error(`[PjeRegistrarDebito] Erro no preenchimento:`, err);
        btn.innerText = '❌ Erro';
        btn.style.background = '#f38ba8';
        setTimeout(function () {
          btn.innerText = '⬇️ Tentar Novamente';
          btn.style.background = '#a6e3a1';
          btn.disabled = false;
        }, 2000);
      }
    }
  };

  console.log('[PjeRegistrarDebito] ✅ Módulo carregado.');

})();
