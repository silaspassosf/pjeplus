// ==UserScript==
// @name         PJe - Extrator Universal (standalone)
// @namespace    http://tampermonkey.net/
// @version      1.0.2
// @description  Versão standalone para testes: expõe window.pjeExtrair() e permite testes isolados
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  console.log('[PjeExtrairStandalone] carregado');

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
      var emTabela  = false;
      var linhas    = pag.trim().split("\n").reduce(function (acc, linha) {
        var celulas     = linha.split(" | ");
        var ehTabelar   = celulas.length >= 3;

        if (ehTabelar) {
          celulas.forEach(function (c, i) {
            colWidths[i] = Math.max(colWidths[i] || 0, c.trim().length);
          });
          if (!emTabela) { acc.push("\n=== TABELA ==="); emTabela = true; }
          var pad    = celulas.map(function (c, i) { return c.trim().padEnd(colWidths[i] || 0); }).join(" | ");
          var total  = /total|subtotal|líquido|bruto|devido/i.test(linha);
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

  async function extrair(opts = {}) {
    var rootDoc = (opts.containerDocument && opts.containerDocument.nodeType === 9) ? opts.containerDocument : document;

    var el = opts.element || (opts.selector && rootDoc.querySelector(opts.selector)) || rootDoc.querySelector("object.conteudo-pdf");
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

    if (typeof view.pdfjsLib !== 'undefined') {
      try {
        var pdfjsLib = view.pdfjsLib;
        var blobUrl  = new view.URLSearchParams(view.location.search).get("file");
        if (!blobUrl) return { sucesso: false, tipo: "pdf", erro: "blob URL não encontrada" };

        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pjekz/assets/pdf/build/pdf.worker.js";
        var pdf = await pdfjsLib.getDocument(blobUrl).promise;

        var paginas = [];
        for (var i = 1; i <= pdf.numPages; i++) {
          var content = await (await pdf.getPage(i)).getTextContent();
          var linhas  = {};
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

        var bruto      = paginas.join("\n\n--- PÁGINA ---\n\n");
        var conteudo   = formatar(bruto, "pdf");
        return { sucesso: true, tipo: "pdf", conteudo: conteudo, conteudo_bruto: bruto, chars: conteudo.length };

      } catch (e) {
        return { sucesso: false, tipo: "pdf", erro: e.message };
      }

    } else {
      var viewer = inner.querySelector("#viewer");
      if (!viewer) return { sucesso: false, tipo: "html", erro: "#viewer não encontrado" };
      var bruto    = (viewer.innerText || viewer.textContent || "").trim();
      if (bruto.length < 50) return { sucesso: false, tipo: "html", erro: "conteúdo vazio" };
      var conteudo = formatar(bruto, "html");
      return { sucesso: true, tipo: "html", conteudo: conteudo, conteudo_bruto: bruto, chars: conteudo.length };
    }
  }

  window.pjeExtrair = async function (opts) {
    var res = await extrair(opts);
    window._pjeResultado = res;
    window._pjePronto    = !!res.sucesso;
    return res;
  };

  window.PjeExtrair = window.pjeExtrair;

// Injeta um botão de teste na página de detalhe para acionar a extração manualmente
(function injectButton(){
  try {
    if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) return;
    if (document.getElementById('pjeextrair-standalone-btn')) return;
    // Aguarda curto período para garantir que o DOM principal esteja pronto
    setTimeout(() => {
      try {
        const btn = document.createElement('button');
        btn.id = 'pjeextrair-standalone-btn';
        btn.textContent = '🔎 Extrair Documento';
        btn.style.cssText = 'position:fixed;bottom:120px;right:20px;z-index:9999999;' +
          'background:#17a2b8;color:#fff;border:none;padding:8px 10px;border-radius:6px;cursor:pointer;box-shadow:0 6px 18px rgba(0,0,0,.18);font-weight:600;';
        btn.onclick = async function () {
          btn.disabled = true; btn.textContent = 'Extraindo...';
          try {
            const res = await window.PjeExtrair();
            console.log('[PjeExtrairStandalone] resultado:', res);
            alert('Extração: ' + (res.sucesso ? 'OK' : 'ERRO') + (res.erro ? '\n' + res.erro : ''));
          } catch (e) {
            console.error('[PjeExtrairStandalone] erro:', e);
            alert('Erro na extração: ' + (e && e.message ? e.message : String(e)));
          }
          btn.disabled = false; btn.textContent = '🔎 Extrair Documento';
        };
        document.body.appendChild(btn);
      } catch (e) { console.error('[PjeExtrairStandalone] inject append error', e); }
    }, 800);
  } catch (e) { console.error('[PjeExtrairStandalone] inject error', e); }
})();

})();
