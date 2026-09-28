'use strict';

// ── Portado de Script/core/extrair.js ───────────────────────────
// window.pjeExtrair()  — extrator via DOM (viewer/pdf.js embarcado)
// window.pjeExtrairApi() — extrator via API REST do PJe
//
// Adaptações para extensão Firefox MV3:
//   • workerSrc: browser.runtime.getURL('vendor/pdfjs/pdf.worker.min.js')
//   • Sem GM_*, sem @require externos — pdf.js já injetado pelo manifest

(function () {

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
  // EXTRAÇÃO VIA VIEWER (DOM)
  // ═══════════════════════════════════════════════════════════

  async function extrair(opts) {
    opts = opts || {};
    var rootDoc = (opts.containerDocument && opts.containerDocument.nodeType === 9) ? opts.containerDocument : document;

    // ── Editor HTML direto (documento não assinado) ──────────
    var _candidatos = [
      ...rootDoc.querySelectorAll('div#documento pje-historico-scroll-documento mat-card.container-html mat-card-content.conteudo-html')
    ];
    if (!_candidatos.length) {
      _candidatos = [...rootDoc.querySelectorAll('mat-card.container-html mat-card-content.conteudo-html')];
    }
    if (!_candidatos.length) {
      _candidatos = [...rootDoc.querySelectorAll('mat-card.container-html')];
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
      return { sucesso: true, tipo: 'html-editor', conteudo: conteudo, conteudo_bruto: fatiado, chars: conteudo.length };
    }

    var el = rootDoc.querySelector('object.conteudo-pdf, iframe.conteudo-pdf');
    if (!el) return { sucesso: false, erro: "elemento de visualização (object.conteudo-pdf) não encontrado" };

    var inner = el.contentDocument || (el.contentWindow && el.contentWindow.document);
    if (!inner) {
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

    // ── PDF ────────────────────────────────────────────────────
    if (typeof view.pdfjsLib !== 'undefined') {
      try {
        var pdfjsLib = view.pdfjsLib;
        var blobUrl = new view.URLSearchParams(view.location.search).get("file");
        if (!blobUrl) return { sucesso: false, tipo: "pdf", erro: "blob URL não encontrada" };

        // Adaptação extensão: worker local via browser.runtime.getURL
        pdfjsLib.GlobalWorkerOptions.workerSrc =
          typeof browser !== 'undefined'
            ? browser.runtime.getURL('vendor/pdfjs/pdf.worker.min.js')
            : "/pjekz/assets/pdf/build/pdf.worker.js";

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
    } else {
      // ── HTML viewer ─────────────────────────────────────────
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
    window._pjeResultado = res;
    window._pjePronto = !!res.sucesso;
    return res;
  };

  window.PjeExtrair = window.pjeExtrair;

  // ═══════════════════════════════════════════════════════════
  // EXTRAÇÃO VIA API REST — window.pjeExtrairApi(docId?, opts?)
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
    var titulos = document.querySelectorAll('mat-card-title, .mat-card-title');
    for (var i = 0; i < titulos.length; i++) {
      var t = (titulos[i].textContent || '').trim();
      var mt = t.match(/Id\s+([A-Za-z0-9]+)\s*[-–—]/i);
      if (mt) return mt[1].trim();
    }
    return null;
  }

  // Cache simples de timeline para acelerar extrações consecutivas
  var _apiTimelineCache = null;

  async function _apiObterDocsTimeline(idProcesso, forcarAtualizacao) {
    var agora = Date.now();
    if (!forcarAtualizacao && _apiTimelineCache && _apiTimelineCache.idProcesso === idProcesso && (agora - _apiTimelineCache.ts < 30000)) {
      return _apiTimelineCache.docs;
    }
    var url = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?' +
      new URLSearchParams({ somenteDocumentosAssinados: 'false', buscarMovimentos: 'false', buscarDocumentos: 'true' });
    var resp = await fetch(url, { method: 'GET', credentials: 'include', headers: _apiHeaders() });
    if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ao buscar timeline do processo ' + idProcesso);
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
    _apiTimelineCache = { idProcesso: idProcesso, ts: agora, docs: allDocs };
    return allDocs;
  }

  function _apiBuscarDocNaLista(docs, uid) {
    if (!Array.isArray(docs) || !uid) return null;
    var uidStr = String(uid).trim();
    var uidLower = uidStr.toLowerCase();

    // 1. Prioridade máxima: idUnicoDocumento exato (7 chars hexadecimais, ex: "0015c20" ou "3627494")
    var d = docs.find(function (item) {
      return item && item.idUnicoDocumento && String(item.idUnicoDocumento).trim().toLowerCase() === uidLower;
    });
    if (d) return d;

    // 2. numeroDocumento (ex: "24082506371234567890" ou número de protocolo)
    d = docs.find(function (item) {
      return item && item.numeroDocumento && (String(item.numeroDocumento).trim() === uidStr || String(item.numeroDocumento).includes(uidStr));
    });
    if (d) return d;

    // 3. ID de banco exato (quando o chamador já passa o id numérico interno)
    d = docs.find(function (item) {
      return item && (String(item.id) === uidStr || String(item.idDocumento) === uidStr);
    });
    if (d) return d;

    // 4. Substring de idUnicoDocumento
    d = docs.find(function (item) {
      return item && item.idUnicoDocumento && String(item.idUnicoDocumento).toLowerCase().includes(uidLower);
    });
    return d || null;
  }

  // Resolve id alfanumérico (idUnicoDocumento de 7 chars hex como 0015c20 ou 3627494),
  // numeroDocumento ou id interno → id numérico de banco aceito por /documentos/id/{id}.
  async function _apiResolverIdNumerico(idProcesso, uid) {
    if (!uid) throw new Error('UID do documento não fornecido');
    var uidStr = String(uid).trim();

    // 1. Tenta localizar na timeline (usa cache de 30s para agilizar extrações consecutivas)
    var allDocs = await _apiObterDocsTimeline(idProcesso, false);
    var docItem = _apiBuscarDocNaLista(allDocs, uidStr);

    // Se não encontrou no cache, força atualização da timeline uma vez
    if (!docItem) {
      allDocs = await _apiObterDocsTimeline(idProcesso, true);
      docItem = _apiBuscarDocNaLista(allDocs, uidStr);
    }

    if (docItem) {
      var idDoc = docItem.id || docItem.idDocumento;
      if (idDoc) return String(idDoc);
    }

    // Fallback: se não achou na timeline e o UID já possui 8+ dígitos numéricos,
    // pode ser um ID interno de banco passado diretamente.
    // UIDs de 7 caracteres não entram aqui porque são hashes hexadecimais (idUnicoDocumento).
    if (/^\d{8,}$/.test(uidStr)) {
      console.warn('[pjeExtrairApi] UID "' + uidStr + '" não localizado na timeline; tentando uso direto como id numérico.');
      return uidStr;
    }

    throw new Error('Documento "' + uidStr + '" não encontrado na timeline');
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
        if (!resp.ok) { console.warn('[pjeExtrairApi] Endpoint ignorado:', resp.status, url); continue; }
        const contentType = (resp.headers.get('content-type') || '').toLowerCase();
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
            if (conteudo !== null && conteudo !== undefined) return { tipo: 'json', conteudo: String(conteudo) };
            return { tipo: 'json-raw', conteudo: texto };
          }
        }
        if (/<(?:html|body|div|p|table)[\s>]/i.test(texto)) return { tipo: 'html', conteudo: texto };
        return { tipo: 'text', conteudo: texto };
      } catch (e) {
        console.warn('[pjeExtrairApi] Erro no endpoint:', url, e);
      }
    }
    throw new Error('Nenhum endpoint retornou conteúdo para docId=' + idDoc);
  }

  async function _apiExtrairTextoPdf(arrayBuffer) {
    var pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib) throw new Error('pdf.js não disponível (deve ser carregado pelo manifest)');

    // Adaptação extensão: worker local
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      typeof browser !== 'undefined'
        ? browser.runtime.getURL('vendor/pdfjs/pdf.worker.min.js')
        : 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

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
    return paginas.join('\n\n--- PÁGINA ---\n\n').trim();
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
        return { sucesso: true, tipo: 'meta-sem-conteudo', meta: meta, conteudo: '', conteudo_bruto: '', chars: 0, aviso: 'PDF obtido mas extração falhou: ' + e.message };
      }
      if (!bruto || bruto.length < 10)
        return { sucesso: true, tipo: 'meta-sem-conteudo', meta: meta, conteudo: '', conteudo_bruto: '', chars: 0, aviso: 'PDF sem texto extraível' };
      var cpdf = formatar(bruto, 'pdf');
      return { sucesso: true, tipo: 'api-pdf', meta: meta, conteudo: cpdf, conteudo_bruto: bruto, chars: cpdf.length };
    }
    var bruto2 = conteudoResult.tipo === 'html' ? _apiStripHtml(conteudoResult.conteudo) : conteudoResult.conteudo;
    if (!bruto2 || bruto2.length < 10) return { sucesso: false, erro: 'Conteúdo extraído está vazio' };
    var c2 = formatar(bruto2, 'html');
    return { sucesso: true, tipo: 'api-' + conteudoResult.tipo, meta: meta, conteudo: c2, conteudo_bruto: bruto2, chars: c2.length };
  }

  window.pjeExtrairApi = async function (docId, opts) {
    opts = opts || {};
    if (docId !== undefined && docId !== null) docId = String(docId).trim();
    try {
      const resultado = await _extrairApi(docId, opts);
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
    detectarDocId: _apiDetectarDocId,
    meta: async function (docId, opts) {
      var idProcesso = (opts && opts.idProcesso) || _apiIdProcesso();
      if (!idProcesso || !docId) { console.warn('[pjeApi] meta: idProcesso ou docId ausente'); return null; }
      return _apiFetchMetadados(idProcesso, docId, opts || {});
    },
  };

})();
