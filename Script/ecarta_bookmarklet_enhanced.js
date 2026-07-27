// === eCarta Bookmarklet Enhanced — com Auditoria de Falsos Positivos ===
// Base: bookmarklet original "Últimas" + "Antigas"
// Adição: audita rastreamentos ativos e corrige falsos positivos (devolução marcada como entrega)
// Uso: colar no console ou converter para bookmarklet com encodeURIComponent

(function(){
  'use strict';

  // ── Cleanup ──
  var oldBtn = document.getElementById('ecarta-copiar-btn');
  if (oldBtn) oldBtn.remove();
  var oldMenu = document.getElementById('doc-menu');
  if (oldMenu) oldMenu.remove();

  // ── Padrões de devolução (falso positivo) ──
  var RE_DEV = /objeto\s+(ser[áa]\s+devolvido|saiu\s+para\s+entrega\s+ao\s+remetente|entregue\s+ao\s+remetente)|devolvido\s+ao\s+remetente/i;
  var RE_ENTREGUE = /entregue\s+ao\s+destinat[áa]rio/i;
  var RE_DEVOLVIDO = /devolvid[oa]/i;
  var BASE_ECARTA = 'https://aplicacoes1.trt2.jus.br/eCarta-web/';

  // ── Overlay de alerta de falsos positivos ──
  function mostrarAlertaFP(count) {
    var ov = document.createElement('div');
    ov.style.cssText = 'position:fixed;top:60px;left:50%;transform:translateX(-50%);z-index:2147483647;'
      + 'background:#181825;color:#fab387;border:2px solid #f38ba8;border-radius:8px;'
      + 'padding:12px 20px;font:14px ui-monospace,Consolas,monospace;'
      + 'box-shadow:0 4px 24px rgba(0,0,0,.6);max-width:520px;text-align:center;';
    ov.innerHTML = '<b>\u26A0\uFE0F ' + count + ' FALSO(S) POSITIVO(S) DETECTADO(S)!</b><br>'
      + '<span style="font-size:11px;color:#cdd6f4;">O status "Entregue ao destinat\u00E1rio" na tabela escondia '
      + 'devolu\u00E7\u00E3o. Relat\u00F3rio j\u00E1 corrigido.</span>';
    document.body.appendChild(ov);
    setTimeout(function(){
      ov.style.opacity = '0'; ov.style.transition = 'opacity 0.5s';
      setTimeout(function(){ ov.remove(); }, 500);
    }, 5000);
  }

  // ── Auditoria de rastreio (GET + POST JSF → parse eventos → detecta devolução) ──
  async function auditarRastreio(link) {
    try {
      // Etapa 1: GET página do rastreio → extrai ViewState e índices
      var resp = await fetch(link, {credentials:'include'});
      var html = await resp.text();
      var vs = (html.match(/name="javax\.faces\.ViewState"[^>]+value="([^"]+)"/) || [])[1];
      if (!vs) return {falsoPositivo:false, statusReal:'SEM_VIEWSTATE', evidencias:[]};

      var indices = [];
      var reIdx = /id="main:tabDoc:(\d+):rastreamento"/g, mIdx;
      while ((mIdx = reIdx.exec(html)) !== null) indices.push(parseInt(mIdx[1], 10));
      if (!indices.length) return {falsoPositivo:false, statusReal:'SEM_INDICES', evidencias:[]};

      var evidencias = [];
      // Etapa 2: POST JSF para cada índice
      for (var i = 0; i < indices.length; i++) {
        var src = 'main:tabDoc:' + indices[i] + ':rastreamento';
        var body = 'javax.faces.partial.ajax=true'
          + '&javax.faces.source=' + encodeURIComponent(src)
          + '&javax.faces.partial.execute=' + encodeURIComponent(src)
          + '&javax.faces.partial.render=detalhesObjeto'
          + '&' + encodeURIComponent(src) + '=' + encodeURIComponent(src)
          + '&main=main'
          + '&javax.faces.ViewState=' + encodeURIComponent(vs);

        var postResp = await fetch(BASE_ECARTA + 'consultarObjeto.xhtml', {
          method:'POST', credentials:'include',
          headers:{
            'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8',
            'Faces-Request':'partial/ajax'
          },
          body:body
        });
        var xmlText = await postResp.text();

        // Parse partial-response XML
        var parser = new DOMParser();
        var xmlDoc = parser.parseFromString(xmlText, 'application/xml');
        if (xmlDoc.querySelector('parsererror')) continue;

        var updates = xmlDoc.querySelectorAll('update[id="detalhesObjeto"]');
        for (var u = 0; u < updates.length; u++) {
          var innerHtml = updates[u].textContent || '';
          if (!innerHtml) continue;
          var doc = parser.parseFromString(innerHtml, 'text/html');
          var tbody = doc.querySelector('#tabDetalhesObjeto_data')
            || doc.querySelector('tbody[id*="tabDetalhesObjeto"]');
          if (!tbody) continue;

          var rows = tbody.querySelectorAll('tr');
          for (var ri = 0; ri < rows.length; ri++) {
            var tds = rows[ri].querySelectorAll('td');
            if (tds.length < 2) continue;
            if ((tds[0].textContent||'').includes('Nenhum resultado')) continue;

            // Reconstrói descrição (text nodes + <br> → " | ")
            var descTd = tds[1];
            var desc = '';
            for (var cn = 0; cn < descTd.childNodes.length; cn++) {
              var node = descTd.childNodes[cn];
              if (node.nodeType === 3) desc += node.textContent.trim();
              else if (node.tagName === 'BR') desc += ' | ';
              else desc += node.textContent.trim();
            }
            desc = desc.replace(/\s+/g, ' ').trim();

            if (RE_DEV.test(desc)) {
              evidencias.push((tds[0].textContent||'').trim() + ' \u2014 ' + desc);
            }
          }
        }

        // Pequeno delay entre chamadas
        await new Promise(function(r){ setTimeout(r, 100); });
      }

      return {
        falsoPositivo: evidencias.length > 0,
        statusReal: evidencias.length > 0 ? 'DEVOLVIDO' : 'ENTREGUE',
        evidencias: evidencias
      };
    } catch(e) {
      return {falsoPositivo:false, statusReal:'ERRO_AUDITORIA', evidencias:[], erro:e.message};
    }
  }

  // ── Helpers de data ──
  function parseDate(d) {
    var parts = d.split('/');
    return new Date(parts[2] + '-' + parts[1] + '-' + parts[0]);
  }

  function criarUrlDocumento(documentoId) {
    var baseUrl = window.location.origin;
    var currentPath = window.location.pathname;
    var contexto = currentPath.includes('/pjekz/') ? '/pjekz'
      : currentPath.includes('/pje/') ? '/pje' : '/pjekz';
    if (contexto === '/pjekz') {
      return baseUrl + '/pjekz/processo/documento/' + documentoId + '/conteudo';
    }
    return baseUrl + '/pje/Processo/ConsultaDocumento/Documento.seam?doc=' + documentoId;
  }

  // ── Parse da tabela (comum) ──
  function parseTabela() {
    var rows = Array.from(document.querySelectorAll('#main\\:tabDoc_data tr'));
    if (!rows.length) return null;

    return rows.map(function(tr){
      var tds = tr.querySelectorAll('td');
      if (tds.length < 4) return null;

      var objetoTd = tds[4];
      var objeto = objetoTd ? objetoTd.innerText.trim() : '';
      var objetoLink = null;

      var idTd = tds[3];
      var idPje = idTd ? idTd.innerText.trim() : '';
      var idPjeLink = null;
      if (idPje && /^\d{10,}$/.test(idPje)) {
        idPjeLink = criarUrlDocumento(idPje);
      }

      var spanElement = objetoTd ? objetoTd.querySelector('span[id*=":rastreamento"]') : null;
      if (spanElement) {
        var codigoRastreamento = spanElement.innerText.trim();
        if (codigoRastreamento && codigoRastreamento.length > 5) {
          objeto = codigoRastreamento;
          var linkElement = spanElement.closest('a');
          if (linkElement && linkElement.href) {
            objetoLink = linkElement.href.startsWith('/')
              ? 'https://aplicacoes1.trt2.jus.br' + linkElement.href
              : linkElement.href;
          }
        }
      }

      return {
        dataEnvio: (tds[0] ? tds[0].innerText.trim() : ''),
        dataEntrega: (tds[1] ? tds[1].innerText.trim() : ''),
        idPje: idPje,
        idPjeLink: idPjeLink,
        objeto: objeto,
        objetoLink: objetoLink,
        status: (tds[5] ? tds[5].innerText.trim() : ''),
        destinatario: (tds[6] ? tds[6].innerText.trim() : ''),
        orgaoJulgador: (tds[7] ? tds[7].innerText.trim() : '')
      };
    }).filter(Boolean);
  }

  // ── Gera relatório a partir de lista de linhas ──
  function gerarRelatorio(linhas) {
    var conteudoHtml = '';
    var conteudoTexto = '';

    linhas.forEach(function(d, idx){
      var statusMostrar = d.statusCorrigido || d.status;

      conteudoHtml += 'ID: ' + (d.idPjeLink
        ? '<a href="' + d.idPjeLink + '" target="_blank">' + d.idPje + '</a>'
        : d.idPje)
        + '<br>DESTINAT\u00C1RIO: ' + d.destinatario
        + '<br>DATA DO ENVIO: ' + d.dataEnvio
        + '<br>DATA DE ENTREGA: ' + d.dataEntrega
        + '<br>RESULTADO: ' + statusMostrar
        + (d.falsoPositivo ? ' \u26A0\uFE0F FALSO POSITIVO CORRIGIDO (era "Entregue", mas houve devolu\u00E7\u00E3o)' : '')
        + '<br>OBJETO: ' + (d.objetoLink
          ? '<a href="' + d.objetoLink + '" target="_blank">' + d.objeto + '</a>'
          : d.objeto)
        + '<br>DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.'
        + (d.evidencias && d.evidencias.length
          ? '<br>\u2514 Evid\u00EAncia: ' + d.evidencias[0]
          : '');

      conteudoTexto += 'ID: ' + d.idPje
        + (d.idPjeLink ? '\n\uD83D\uDD17 Link do documento: ' + d.idPjeLink : '')
        + '\nDESTINAT\u00C1RIO: ' + d.destinatario
        + '\nDATA DO ENVIO: ' + d.dataEnvio
        + '\nDATA DE ENTREGA: ' + d.dataEntrega
        + '\nRESULTADO: ' + statusMostrar
        + (d.falsoPositivo ? ' \u26A0\uFE0F FALSO POSITIVO CORRIGIDO' : '')
        + '\nOBJETO: ' + d.objeto
        + (d.objetoLink ? '\n\uD83D\uDD17 Link: ' + d.objetoLink : '')
        + '\nDEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.'
        + (d.evidencias && d.evidencias.length
          ? '\n\u2514 Evid\u00EAncia: ' + d.evidencias[0]
          : '');

      if (idx < linhas.length - 1) {
        conteudoHtml += '<br><br>_____________________________________________________________<br><br>';
        conteudoTexto += '\n\n_____________________________________________________________\n\n';
      }
    });

    return {html: conteudoHtml, texto: conteudoTexto};
  }

  // ── Fluxo de auditoria + relatório ──
  async function auditarEGerar(linhas) {
    var falsosPositivos = 0;

    for (var i = 0; i < linhas.length; i++) {
      var d = linhas[i];
      if (!d.objetoLink) continue; // sem link de rastreio, pula

      try {
        var resultado = await auditarRastreio(d.objetoLink);
        if (resultado.falsoPositivo) {
          falsosPositivos++;
          d.falsoPositivo = true;
          d.statusCorrigido = 'DEVOLVIDO (corrigido de: ' + d.status + ')';
          d.evidencias = resultado.evidencias;
        }
      } catch(e) {
        // ignora erros de auditoria individual
      }
    }

    return {linhas: linhas, falsosPositivos: falsosPositivos};
  }

  // ── Copy helper ──
  async function copiarConteudo(htmlContent, textContent, btnEl, labelOriginal, corOriginal) {
    try {
      var htmlBlob = new Blob([htmlContent], {type:'text/html'});
      var textBlob = new Blob([textContent], {type:'text/plain'});
      await navigator.clipboard.write([new ClipboardItem({
        'text/html': htmlBlob,
        'text/plain': textBlob
      })]);
      btnEl.textContent = 'Copiado com links!';
    } catch(e1) {
      try {
        await navigator.clipboard.writeText(textContent);
        btnEl.textContent = 'Copiado (texto)!';
      } catch(e2) {
        var ta = document.createElement('textarea');
        ta.value = textContent;
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btnEl.textContent = 'Copiado!';
      }
    }
    btnEl.style.background = '#43a047';
    setTimeout(function(){
      btnEl.textContent = labelOriginal;
      btnEl.style.background = corOriginal;
    }, 2000);
  }

  // ── Botão 1: Últimas ──
  var btn = document.createElement('button');
  btn.id = 'ecarta-copiar-btn';
  btn.textContent = '\u00DAltimas';
  Object.assign(btn.style, {
    position:'fixed', bottom:'30px', right:'30px', zIndex:9999,
    padding:'12px 20px', background:'#1976d2', color:'#fff',
    border:'none', borderRadius:'8px', fontSize:'16px',
    boxShadow:'0 2px 8px rgba(0,0,0,0.2)', cursor:'pointer',
    transition:'background 0.2s'
  });
  btn.onmouseenter = function(){ btn.style.background = '#1565c0'; };
  btn.onmouseleave = function(){ btn.style.background = '#1976d2'; };
  document.body.appendChild(btn);

  // ── Botão 2: Antigas ──
  var btn2 = document.createElement('button');
  btn2.id = 'ecarta-copiar-btn-antigas';
  btn2.textContent = 'Antigas';
  Object.assign(btn2.style, {
    position:'fixed', bottom:'30px', right:'130px', zIndex:9999,
    padding:'12px 20px', background:'#f57c00', color:'#fff',
    border:'none', borderRadius:'8px', fontSize:'16px',
    boxShadow:'0 2px 8px rgba(0,0,0,0.2)', cursor:'pointer',
    transition:'background 0.2s'
  });
  btn2.onmouseenter = function(){ btn2.style.background = '#e65100'; };
  btn2.onmouseleave = function(){ btn2.style.background = '#f57c00'; };
  document.body.appendChild(btn2);

  // ── Handler: Últimas ──
  btn.onclick = async function(){
    try {
      btn.textContent = 'Auditando...';
      btn.style.background = '#7b1fa2';

      var todasLinhas = parseTabela();
      if (!todasLinhas) { alert('Tabela n\u00E3o encontrada!'); btn.textContent = '\u00DAltimas'; btn.style.background = '#1976d2'; return; }

      // Filtra data mais recente
      var maxData = todasLinhas.map(function(d){return d.dataEnvio;})
        .filter(function(d){return /\d{2}\/\d{2}\/\d{4}/.test(d);})
        .map(parseDate).sort(function(a,b){return b-a;})[0];
      var recentes = todasLinhas.filter(function(d){
        if (!/\d{2}\/\d{2}\/\d{4}/.test(d.dataEnvio)) return false;
        return parseDate(d.dataEnvio).getTime() === maxData.getTime();
      });

      if (!recentes.length) {
        alert('Nenhuma intima\u00E7\u00E3o encontrada na data mais recente!');
        btn.textContent = '\u00DAltimas'; btn.style.background = '#1976d2'; return;
      }

      // ═══ AUDITORIA DE FALSOS POSITIVOS ═══
      var auditado = await auditarEGerar(recentes);
      recentes = auditado.linhas;

      // Overlay se houve falso positivo
      if (auditado.falsosPositivos > 0) {
        mostrarAlertaFP(auditado.falsosPositivos);
      }

      // Gera relatório
      var conteudo = gerarRelatorio(recentes);
      if (!conteudo) return;

      await copiarConteudo(conteudo.html, conteudo.texto, btn, '\u00DAltimas', '#1976d2');

    } catch(error){
      console.error('Erro:', error);
      btn.textContent = 'Erro!';
      btn.style.background = '#d32f2f';
      setTimeout(function(){ btn.textContent = '\u00DAltimas'; btn.style.background = '#1976d2'; }, 2000);
    }
  };

  // ── Handler: Antigas ──
  btn2.onclick = async function(){
    try {
      btn2.textContent = 'Auditando...';
      btn2.style.background = '#7b1fa2';

      var todasLinhas = parseTabela();
      if (!todasLinhas) { alert('Tabela n\u00E3o encontrada!'); btn2.textContent = 'Antigas'; btn2.style.background = '#f57c00'; return; }

      // Filtra 2 datas mais recentes
      var datasUnicas = Array.from(new Set(
        todasLinhas.map(function(d){return d.dataEnvio;})
          .filter(function(d){return /\d{2}\/\d{2}\/\d{4}/.test(d);})
      )).map(parseDate).sort(function(a,b){return b-a;});

      if (datasUnicas.length < 2) {
        alert('N\u00E3o h\u00E1 2 datas diferentes!');
        btn2.textContent = 'Antigas'; btn2.style.background = '#f57c00'; return;
      }

      var maxData = datasUnicas[0];
      var segundaData = datasUnicas[1];
      var recentes = todasLinhas.filter(function(d){
        if (!/\d{2}\/\d{2}\/\d{4}/.test(d.dataEnvio)) return false;
        var dAtual = parseDate(d.dataEnvio);
        return dAtual.getTime() === maxData.getTime() || dAtual.getTime() === segundaData.getTime();
      });

      if (!recentes.length) {
        alert('Nenhuma intima\u00E7\u00E3o encontrada!');
        btn2.textContent = 'Antigas'; btn2.style.background = '#f57c00'; return;
      }

      // ═══ AUDITORIA DE FALSOS POSITIVOS ═══
      var auditado = await auditarEGerar(recentes);
      recentes = auditado.linhas;

      // Overlay se houve falso positivo
      if (auditado.falsosPositivos > 0) {
        mostrarAlertaFP(auditado.falsosPositivos);
      }

      // Gera relatório
      var conteudo = gerarRelatorio(recentes);
      if (!conteudo) return;

      await copiarConteudo(conteudo.html, conteudo.texto, btn2, 'Antigas', '#f57c00');

    } catch(error){
      console.error('Erro:', error);
      btn2.textContent = 'Erro!';
      btn2.style.background = '#d32f2f';
      setTimeout(function(){ btn2.textContent = 'Antigas'; btn2.style.background = '#f57c00'; }, 2000);
    }
  };

})();
