// ==UserScript==
// @name         PJe - Extrator Universal (HTML + PDF)
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Expõe window.pjeExtrair() — chame de qualquer script para extrair o documento ativo
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════════
  // FORMATAÇÃO
  // ═══════════════════════════════════════════════════════════

  function formatarHtml(texto) {
    var saida = [];
    texto.split("\n").map(function (l) { return l.trim(); }).forEach(function (l) {
      if (!l) { if (saida[saida.length - 1] !== "") saida.push(""); return; }
      var up = l.toUpperCase();
      if (l.length < 80 && (l === up || /DECISÃO|DESPACHO|SENTENÇA|CONCLUSÃO|VISTOS|ACÓRDÃO/.test(up)))
        return saida.push("\n=== " + l + " ===");
      if (/^(DEFIRO|INDEFIRO|DETERMINO|HOMOLOGO|CONDENO|JULGO)/.test(up))
        return saida.push("\n>>> " + l);
      if (/Juiz|Magistrado|Servidor Responsável/.test(l))
        return saida.push("\n--- " + l + " ---");
      saida.push(l);
    });
    return saida.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function formatarPdf(texto) {
    return texto.split("--- PÁGINA ---").map(function (pag, numPag) {
      var colWidths = [];
      var emTabela = false;
      var linhas = pag.trim().split("\n").reduce(function (acc, linha) {
        var celulas = linha.split(" | ");
        var ehTabelar = celulas.length >= 3;

        if (ehTabelar) {
          celulas.forEach(function (c, i) {
            colWidths[i] = Math.max(colWidths[i] || 0, c.trim().length);
          });
          if (!emTabela) { acc.push("\n=== TABELA ==="); emTabela = true; }
          var pad = celulas.map(function (c, i) { return c.trim().padEnd(colWidths[i] || 0); }).join(" | ");
          var total = /total|subtotal|líquido|bruto|devido/i.test(linha);
          acc.push(total ? "** " + pad + " **" : pad);
        } else {
          if (emTabela) { acc.push(""); emTabela = false; }
          if (!linha.trim()) { if (acc[acc.length - 1] !== "") acc.push(""); return acc; }
          var up = linha.toUpperCase();
          if (linha.length < 100 && /PLANILHA|DEMONSTRATIVO|RESUMO|CRÉDITO|DÉBITO/.test(up)) {
            acc.push("\n=== " + linha.trim() + " ===");
            return acc;
          }
          acc.push(linha.trim());
        }
        return acc;
      }, []);
      return "══ Página " + (numPag + 1) + " ══\n" + linhas.join("\n");
    }).join("\n\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function formatar(texto, tipo) {
    if (!texto) return texto;
    var t = texto.replace(/\r\n|\r/g, "\n").replace(/[ \t]+/g, " ");
    return tipo === "pdf" ? formatarPdf(t) : formatarHtml(t);
  }

  // ═══════════════════════════════════════════════════════════
  // EXTRAÇÃO
  // ═══════════════════════════════════════════════════════════

  // internal extractor: accepts an options object to allow callers to specify
  // the container element or selector. Returns same result shape as before.
  async function extrair(opts = {}) {
    var rootDoc = (opts.containerDocument && opts.containerDocument.nodeType === 9) ? opts.containerDocument : document;

    // ── NOVO: Editor HTML direto (documento não assinado) ───────────────
    // Ativo quando não há <object class="conteudo-pdf"> no DOM
    // e o conteúdo está em mat-card.container-html no próprio documento
    var _candidatos = [
      ...rootDoc.querySelectorAll('div#documento pje-historico-scroll-documento mat-card.container-html mat-card-content.conteudo-html')
    ];

    if (!_candidatos.length) {
      _candidatos = [
        ...rootDoc.querySelectorAll('mat-card.container-html mat-card-content.conteudo-html')
      ];
    }

    if (!_candidatos.length) {
      _candidatos = [
        ...rootDoc.querySelectorAll('mat-card.container-html')
      ];
    }

    var editorHtml = _candidatos.reduce(function (best, el) {
      if (!el) return best;
      if (!best) return el;
      return (el.innerText || el.textContent || '').length > (best.innerText || best.textContent || '').length ? el : best;
    }, null);

    if (editorHtml && !opts.forcePdf) {
      var bruto = (editorHtml.innerText || editorHtml.textContent || '').trim();
      var idx = bruto.search(/CONCLUS[AÃ]O/i);
      var fatiado = idx !== -1 ? bruto.slice(idx) : bruto;

      if (fatiado.length < 50)
        return { sucesso: false, tipo: 'html-editor', erro: 'conteúdo vazio ou muito curto' };

      var conteudo = formatar(fatiado, 'html');
      return {
        sucesso: true,
        tipo: 'html-editor',
        conteudo: conteudo,
        conteudo_bruto: fatiado,
        chars: conteudo.length
      };
    }
    // ── fim bloco editor html direto ────────────────────────────────────

    // ✅ Define o elemento de visualização do PDF/HTML
    var el = rootDoc.querySelector('object.conteudo-pdf, iframe.conteudo-pdf');

    if (!el) return { sucesso: false, erro: "elemento de visualização (object.conteudo-pdf) não encontrado" };

    var inner = el.contentDocument || (el.contentWindow && el.contentWindow.document);
    if (!inner) {
      // try waiting a short period for iframe/object to initialize
      var waited = 0;
      while (waited < (opts.timeout || 1500)) {
        await new Promise(r => setTimeout(r, 100));
        waited += 100;
        inner = el.contentDocument || (el.contentWindow && el.contentWindow.document);
        if (inner) break;
      }
    }
    if (!inner) return { sucesso: false, erro: "contentDocument inacessível ou não inicializado" };

    var view = inner.defaultView;

    // ── PDF ────────────────────────────────────────────────
    if (typeof view.pdfjsLib !== 'undefined') {
      try {
        var pdfjsLib = view.pdfjsLib;
        var blobUrl = new view.URLSearchParams(view.location.search).get("file");
        if (!blobUrl) return { sucesso: false, tipo: "pdf", erro: "blob URL não encontrada" };

        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pjekz/assets/pdf/build/pdf.worker.js";
        var pdf = await pdfjsLib.getDocument(blobUrl).promise;

        var paginas = [];
        for (var i = 1; i <= pdf.numPages; i++) {
          var content = await (await pdf.getPage(i)).getTextContent();
          var linhas = {};
          content.items
            .filter(function (it) { return it.str.trim(); })
            .forEach(function (it) {
              var y = Math.round(it.transform[5]);
              var k = Object.keys(linhas).find(function (k) { return Math.abs(parseInt(k) - y) <= 4; }) || String(y);
              if (!linhas[k]) linhas[k] = [];
              linhas[k].push({ str: it.str, x: Math.round(it.transform[4]) });
            });
          paginas.push(
            Object.keys(linhas).map(Number).sort(function (a, b) { return b - a; })
              .map(function (y) {
                return linhas[y]
                  .sort(function (a, b) { return a.x - b.x; })
                  .map(function (it) { return it.str.trim(); })
                  .filter(Boolean).join(" | ");
              }).join("\n")
          );
        }

        var bruto = paginas.join("\n\n--- PÁGINA ---\n\n");
        var conteudo = formatar(bruto, "pdf");
        return { sucesso: true, tipo: "pdf", conteudo: conteudo, conteudo_bruto: bruto, chars: conteudo.length };

      } catch (e) {
        return { sucesso: false, tipo: "pdf", erro: e.message };
      }

      // ── HTML ───────────────────────────────────────────────
    } else {
      var viewer = inner.querySelector("#viewer");
      if (!viewer) return { sucesso: false, tipo: "html", erro: "#viewer não encontrado" };
      var bruto = (viewer.innerText || viewer.textContent || "").trim();
      if (bruto.length < 50) return { sucesso: false, tipo: "html", erro: "conteúdo vazio" };
      var conteudo = formatar(bruto, "html");
      return { sucesso: true, tipo: "html", conteudo: conteudo, conteudo_bruto: bruto, chars: conteudo.length };
    }
  }

  // ═══════════════════════════════════════════════════════════
  // API PÚBLICA — window.pjeExtrair()
  // ═══════════════════════════════════════════════════════════

  window.pjeExtrair = async function (opts) {
    var res = await extrair(opts);
    // Persiste no window para Selenium ler via execute_script
    window._pjeResultado = res;
    window._pjePronto = !!res.sucesso;
    return res;
  };

  // Alias com nome Pascal para consistência com outros módulos
  window.PjeExtrair = window.pjeExtrair;

  // ═══════════════════════════════════════════════════════════
  // EXTRAÇÃO VIA API — window.pjeExtrairApi(docId?, opts?)
  // Portado de extrairapi.user.js; reutiliza formatar() deste módulo.
  // ═══════════════════════════════════════════════════════════

  function _apiXsrf() {
    var c = document.cookie.split(';').map(function (s) { return s.trim(); })
      .find(function (s) { return s.toLowerCase().startsWith('xsrf-token='); });
    return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
  }

  function _apiHeaders() {
    var h = { 'Accept': 'application/json', 'Content-Type': 'application/json', 'X-Grau-Instancia': '1' };
    var x = _apiXsrf(); if (x) h['X-XSRF-TOKEN'] = x;
    return h;
  }

  function _apiIdProcesso() {
    var m = window.location.pathname.match(/\/processo\/(\d+)/);
    return m ? m[1] : null;
  }

  function _apiDetectarDocId() {
    var highlighted = document.querySelector('li.tl-item-container[style*="rgb(255, 247, 214)"]')
      || document.querySelector('li.tl-item-container.pjetools-destaque');
    if (highlighted) {
      var link = highlighted.querySelector('a.tl-documento:not([target="_blank"])');
      if (link) { var m = link.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/); if (m) return m[1]; }
    }
    var params = new URLSearchParams(window.location.search);
    var porUrl = params.get('documentoId') || params.get('docId');
    if (porUrl) return porUrl;
    // Documento ativo: <mat-card-title>Id 0015c20 - calculo ...</mat-card-title>
    // (padrão para qualquer documento aberto; Id curto vem antes do traço)
    var titulos = document.querySelectorAll('mat-card-title, .mat-card-title');
    for (var i = 0; i < titulos.length; i++) {
      var t = (titulos[i].textContent || '').trim();
      var mt = t.match(/Id\s+([A-Za-z0-9]+)\s*[-–—]/i);
      if (mt) return mt[1].trim();
    }
    return null;
  }

  // Resolve id alfanumérico (idUnicoDocumento, ex.: 0015c20) → id numérico,
  // do mesmo jeito que hcalc-overlay.carregarPlanilhaPorUidBotao: busca a
  // timeline do processo e localiza o documento pelo uid.
  async function _apiResolverIdNumerico(idProcesso, uid) {
    if (/^\d+$/.test(String(uid))) return String(uid); // já é numérico
    var url = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?' +
      new URLSearchParams({ somenteDocumentosAssinados: 'false', buscarMovimentos: 'false', buscarDocumentos: 'true' });
    var resp = await fetch(url, { method: 'GET', credentials: 'include', headers: _apiHeaders() });
    if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ao buscar timeline para uid=' + uid);
    var data = await resp.json();
    var allDocs = [];
    if (Array.isArray(data)) {
      data.forEach(function (item) {
        if (item) {
          allDocs.push(item);
          if (Array.isArray(item.anexos)) allDocs.push.apply(allDocs, item.anexos);
        }
      });
    }
    var docItem = allDocs.find(function (d) {
      return d && ((d.idUnicoDocumento && String(d.idUnicoDocumento).includes(uid)) ||
        (d.numeroDocumento && String(d.numeroDocumento).includes(uid)) ||
        (d.id && String(d.id) === String(uid)) ||
        (d.idDocumento && String(d.idDocumento) === String(uid)));
    });
    var idDoc = docItem ? (docItem.id || docItem.idDocumento) : null;
    if (!idDoc) throw new Error('Documento "' + uid + '" não encontrado na timeline');
    return String(idDoc);
  }

  async function _apiFetchMetadados(idProcesso, idDoc, opts) {
    opts = opts || {};
    var params = new URLSearchParams();
    if (opts.incluirAnexos) params.append('incluirAnexos', 'true');
    if (opts.incluirAssinatura) params.append('incluirAssinatura', 'true');
    var qs = params.toString() ? '?' + params.toString() : '';
    var url = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + qs;
    var resp = await fetch(url, { method: 'GET', credentials: 'include', headers: _apiHeaders() });
    if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ao buscar metadados de ' + idDoc);
    var txt = await resp.text();
    try { return JSON.parse(txt); } catch (_) { throw new Error('Metadados: não é JSON — ' + txt.slice(0, 100)); }
  }

  async function _apiFetchConteudo(idProcesso, idDoc) {
    const endpoints = [
      '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + '/conteudo',
      '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + '/html'
    ];
    for (const endpoint of endpoints) {
      const url = location.origin + endpoint;
      try {
        const resp = await fetch(url, { method: 'GET', credentials: 'include', headers: _apiHeaders() });
        if (!resp.ok) {
          console.warn('[pjeExtrairApi] Endpoint ignorado:', resp.status, url);
          continue;
        }
        const contentType = (resp.headers.get('content-type') || '').toLowerCase();
        // Lê uma vez como ArrayBuffer para não consumir o body duas vezes
        const buffer = await resp.arrayBuffer();
        const primeirosBytes = new Uint8Array(buffer.slice(0, 5));
        const assinaturaPdf = primeirosBytes[0] === 0x25 && primeirosBytes[1] === 0x50 && primeirosBytes[2] === 0x44 && primeirosBytes[3] === 0x46;
        if (contentType.includes('application/pdf') || assinaturaPdf) {
          return { tipo: 'pdf-buffer', conteudo: buffer };
        }
        const texto = new TextDecoder('utf-8').decode(buffer);
        if (!texto || texto.trim().length < 10) { continue; }
        if (contentType.includes('application/json')) {
          let dados = null;
          try { dados = JSON.parse(texto); } catch (_) { dados = null; }
          if (dados) {
            const conteudo = dados.conteudo ?? dados.conteudoHtml ?? dados.html ?? dados.texto ?? dados.conteudoTexto ?? dados.documento ?? null;
            if (conteudo !== null && conteudo !== undefined) {
              return { tipo: 'json', conteudo: String(conteudo) };
            }
            // Mantém o JSON inteiro para o parser posterior
            return { tipo: 'json-raw', conteudo: texto };
          }
        }
        // Alguns retornos vêm como HTML mesmo com content-type genérico
        if (/<(?:html|body|div|p|table)[\s>]/i.test(texto)) {
          return { tipo: 'html', conteudo: texto };
        }
        // Caso o endpoint retorne texto puro
        return { tipo: 'text', conteudo: texto };
      } catch (e) {
        console.warn('[pjeExtrairApi] Erro no endpoint:', url, e);
      }
    }
    throw new Error('Nenhum endpoint retornou conteúdo para docId=' + idDoc);
  }

  async function _apiExtrairTextoPdf(arrayBuffer) {
    var pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib) {
      // Carregar pdf.js dinamicamente se não disponível
      await new Promise(function (resolve, reject) {
        var s = document.createElement('script');
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js';
        s.onload = resolve; s.onerror = reject;
        document.head.appendChild(s);
      });
      pdfjsLib = window.pdfjsLib;
    }
    if (!pdfjsLib) throw new Error('pdf.js não disponível');
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
    var pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    var paginas = [];
    for (var p = 1; p <= pdf.numPages; p++) {
      var content = await (await pdf.getPage(p)).getTextContent();
      var linhas = {};
      content.items.filter(function (it) { return it.str && it.str.trim(); })
        .forEach(function (it) {
          var y = Math.round(it.transform[5]);
          var k = Object.keys(linhas).find(function (k) { return Math.abs(parseInt(k) - y) <= 4; }) || String(y);
          if (!linhas[k]) linhas[k] = [];
          linhas[k].push({ str: it.str, x: Math.round(it.transform[4]) });
        });
      paginas.push(
        Object.keys(linhas).map(Number).sort(function (a, b) { return b - a; })
          .map(function (y) {
            return linhas[y].sort(function (a, b) { return a.x - b.x; })
              .map(function (it) { return it.str.trim(); }).filter(Boolean).join(' ');
          }).join('\n')
      );
    }
    var texto = paginas.join('\n\n--- PÁGINA ---\n\n').trim();
    // Fallback OCR: PDFs escaneados (só o carimbo de assinatura tem texto).
    // Mesma técnica do hcalc-pdf.js: renderiza páginas e roda Tesseract 'por'.
    var charsPorPagina = texto.length / pdf.numPages;
    if (texto.length < 300 || charsPorPagina < 200) {
      console.log('[pjeExtrairApi] Pouco texto (' + texto.length + ' chars em ' + pdf.numPages + ' pág.) — iniciando OCR...');
      try {
        var ocrTexto = await _apiOcrPdf(pdf);
        if (ocrTexto && ocrTexto.length > texto.length) {
          console.log('[pjeExtrairApi] OCR produziu', ocrTexto.length, 'chars — substituindo texto extraído.');
          texto = ocrTexto;
        }
      } catch (e) {
        console.warn('[pjeExtrairApi] OCR falhou:', e.message);
      }
    }
    return texto;
  }

  async function _apiOcrPdf(pdf) {
    if (!window.Tesseract) {
      await new Promise(function (resolve, reject) {
        var s = document.createElement('script');
        s.src = 'https://unpkg.com/tesseract.js@5.1.1/dist/tesseract.min.js';
        s.onload = resolve; s.onerror = reject;
        document.head.appendChild(s);
      });
    }
    if (!window.Tesseract || !window.Tesseract.createWorker) throw new Error('tesseract.js não disponível');
    var worker = await window.Tesseract.createWorker('por', 1, { logger: function () {} });
    try {
      var out = [];
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');
      var maxPag = Math.min(pdf.numPages, 8);
      for (var p = 1; p <= maxPag; p++) {
        try {
          var page = await pdf.getPage(p);
          var vp1 = page.getViewport({ scale: 1 });
          var scale = Math.min(2.5, 2200 / vp1.width);
          var viewport = page.getViewport({ scale: scale });
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          await page.render({ canvasContext: ctx, viewport: viewport }).promise;
          var dataUrl = canvas.toDataURL('image/png');
          var txt = '';
          try {
            var res = await Promise.race([
              worker.recognize(dataUrl),
              new Promise(function (_, rej) { setTimeout(function () { rej(new Error('OCR timeout (90s)')); }, 90000); })
            ]);
            txt = (res && res.data && res.data.text) || '';
          } catch (e2) {
            console.warn('[pjeExtrairApi] OCR página ' + p + ' falhou/timeout:', e2.message);
            continue;
          }
          if (txt && txt.trim()) out.push(txt.trim());
          console.log('[pjeExtrairApi] OCR pág', p, 'concluído:', (txt || '').length, 'chars');
        } catch (e3) {
          console.warn('[pjeExtrairApi] Render página ' + p + ' falhou:', e3.message);
        }
      }
      return out.join('\n\n--- PÁGINA ---\n\n').trim();
    } finally {
      try { await worker.terminate(); } catch (e) { /* ignore */ }
    }
  }

  function _apiStripHtml(html) {
    var tmp = document.createElement('div');
    tmp.innerHTML = html;
    return (tmp.innerText || tmp.textContent || '').trim();
  }

  async function _extrairApi(docId, opts) {
    opts = opts || {};
    var idProcesso = opts.idProcesso || _apiIdProcesso();
    if (!idProcesso) return { sucesso: false, erro: 'ID do processo não encontrado' };
    var idDoc = docId || _apiDetectarDocId();
    if (!idDoc) return { sucesso: false, erro: 'doc_id não fornecido e não detectado na tela' };

    // Endpoints /documentos/id/{id} só aceitam id numérico: se veio o hash
    // alfanumérico (mat-card-title "Id xxxxx - ..."), resolve antes.
    try { idDoc = await _apiResolverIdNumerico(idProcesso, idDoc); }
    catch (e) { return { sucesso: false, erro: e.message }; }

    var meta;
    try { meta = await _apiFetchMetadados(idProcesso, idDoc, opts); }
    catch (e) { return { sucesso: false, erro: 'Erro ao buscar metadados: ' + e.message }; }

    if (opts.somenteMetadados)
      return { sucesso: true, tipo: 'meta-only', meta: meta, conteudo: '', conteudo_bruto: '', chars: 0 };

    var conteudoResult;
    try { conteudoResult = await _apiFetchConteudo(idProcesso, idDoc); }
    catch (e) { return { sucesso: false, erro: 'Erro ao buscar conteúdo: ' + e.message }; }

    if (conteudoResult.tipo === 'pdf-buffer') {
      var bruto;
      try { bruto = await _apiExtrairTextoPdf(conteudoResult.conteudo); } catch (e) {
        return {
          sucesso: true, tipo: 'meta-sem-conteudo', meta: meta, conteudo: '', conteudo_bruto: '', chars: 0,
          aviso: 'PDF obtido mas extração falhou: ' + e.message
        };
      }
      if (!bruto || bruto.length < 10)
        return {
          sucesso: true, tipo: 'meta-sem-conteudo', meta: meta, conteudo: '', conteudo_bruto: '', chars: 0,
          aviso: 'PDF sem texto extraível (possivelmente escaneado/imagem)'
        };
      var cpdf = formatar(bruto, 'pdf');
      return { sucesso: true, tipo: 'api-pdf', meta: meta, conteudo: cpdf, conteudo_bruto: bruto, chars: cpdf.length };
    }

    var bruto2 = conteudoResult.tipo === 'html' ? _apiStripHtml(conteudoResult.conteudo) : conteudoResult.conteudo;
    if (!bruto2 || bruto2.length < 10) return { sucesso: false, erro: 'Conteúdo extraído está vazio' };
    var c2 = formatar(bruto2, 'html');
    return { sucesso: true, tipo: 'api-' + conteudoResult.tipo, meta: meta, conteudo: c2, conteudo_bruto: bruto2, chars: c2.length };
  }

  /**
   * window.pjeExtrairApi(docId?, opts?) — extrai documento via API (sem abrir no viewer).
   * docId: idUnicoDocumento alfanumérico (auto-detectado da tela se omitido).
   * opts: { idProcesso, incluirAnexos, incluirAssinatura, somenteMetadados }
   */
  window.pjeExtrairApi = async function (docId, opts) {
    opts = opts || {};
    // Mantém exatamente o identificador fornecido pelo chamador.
    // Sem docId (vazio/null), cai na auto-detecção de _extrairApi → _apiDetectarDocId
    // (item destacado na timeline → URL → mat-card-title "Id xxxxx - ...").
    if (docId !== undefined && docId !== null) {
      docId = String(docId).trim();
    }
    try {
      const resultado = await _extrairApi(docId, opts);
      // Preserva o mesmo formato usado pelo standalone
      window._pjeResultado = resultado;
      window._pjePronto = !!resultado?.sucesso;
      return resultado;
    } catch (e) {
      const resultado = { sucesso: false, erro: e?.message || String(e) };
      window._pjeResultado = resultado;
      window._pjePronto = false;
      return resultado;
    }
  };

  window.PjeExtrairApi = window.pjeExtrairApi;

  window.__pjeApi = {
    extrair: window.pjeExtrairApi,
    xsrf: _apiXsrf,
    idProcesso: _apiIdProcesso,
    meta: async function (docId, opts) {
      var idProcesso = (opts && opts.idProcesso) || _apiIdProcesso();
      if (!idProcesso || !docId) { console.warn('[pjeApi] meta: idProcesso ou docId ausente'); return null; }
      return _apiFetchMetadados(idProcesso, docId, opts || {});
    },
  };

})();
