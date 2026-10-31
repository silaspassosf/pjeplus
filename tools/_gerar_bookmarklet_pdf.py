# Gera o bookmarklet AUTOSSUFICIENTE "Juntar / Converter PDFs".
# Toda a UI e a logica vao embutidas; pdf-lib e pdf.js vem de CDN em runtime.
# Rodar: python tools/_gerar_bookmarklet_pdf.py
#
# Dois modos, escolhidos ao abrir:
#   - UNIR: junta os PDFs num unico arquivo (pdf-lib)
#   - MD:   converte para Markdown (pdf.js: extrai texto, infere titulos por
#           tamanho de fonte e listas por marcadores -- mesma abordagem da
#           ferramenta wutools.com/pt/pdf/pdf-para-markdown, que usa
#           pdf.js 3.11.174 + Tesseract.js para OCR)
import json, pathlib

AQUI = pathlib.Path(__file__).parent
SAIDA = AQUI / "bookmarklet_juntar_pdf.txt"

CSS = """
#pj-overlay{position:fixed;inset:0;background:rgba(8,10,14,.72);z-index:2147483646;display:flex;align-items:flex-start;justify-content:center;padding:28px 16px;overflow:auto;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
#pj-box{background:#fff;color:#1b1b1f;border-radius:14px;max-width:780px;width:100%;padding:22px;box-shadow:0 18px 60px rgba(0,0,0,.4);font-size:14px;line-height:1.5;position:relative}
#pj-box *{box-sizing:border-box}
#pj-box h2{margin:0 0 3px;font-size:19px;font-weight:700}
#pj-sub{opacity:.65;font-size:13px;margin-bottom:16px}
#pj-modos{display:flex;gap:10px;margin-bottom:16px}
#pj-modos button{flex:1;padding:14px 12px;border-radius:10px;border:2px solid #d9dee6;background:#fff;cursor:pointer;text-align:left;font-size:13px;line-height:1.35}
#pj-modos button:hover{border-color:#9db8f5}
#pj-modos button.on{border-color:#2f6fed;background:rgba(47,111,237,.07)}
#pj-modos button b{display:block;font-size:14px;margin-bottom:2px}
#pj-modos button span{opacity:.65;font-size:12px}
#pj-drop{border:2px dashed #c3cad6;border-radius:10px;padding:24px 16px;text-align:center;cursor:pointer;transition:.15s}
#pj-drop:hover,#pj-drop.hot{border-color:#2f6fed;background:rgba(47,111,237,.06)}
#pj-drop strong{display:block;font-size:15px;margin-bottom:3px}
#pj-drop span{opacity:.6;font-size:13px}
#pj-lista{list-style:none;margin:12px 0 0;padding:0;max-height:40vh;overflow:auto}
#pj-lista li{display:flex;align-items:center;gap:9px;padding:8px 10px;margin-bottom:5px;background:#fafbfc;border:1px solid #e6e9ef;border-radius:8px;font-size:13px}
#pj-lista .pj-num{flex:0 0 25px;height:25px;border-radius:50%;background:#2f6fed;color:#fff;display:grid;place-items:center;font-size:12px;font-weight:700}
#pj-lista .pj-nome{flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#pj-lista .pj-pags{flex:0 0 auto;opacity:.55;font-size:12px}
#pj-lista .pj-acoes{display:flex;gap:3px;flex:0 0 auto}
#pj-box button{font:inherit;font-size:12px;padding:4px 8px;border-radius:6px;border:1px solid #d2d8e2;background:#fff;color:#1b1b1f;cursor:pointer}
#pj-box button:hover{filter:brightness(.95)}
#pj-box button:disabled{opacity:.4;cursor:default}
#pj-box button.pj-rem{color:#c02626;border-color:#f0c9c9}
#pj-vazio{text-align:center;opacity:.5;font-size:13px;padding:12px 0}
#pj-barra{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:16px}
#pj-info{font-size:13px;opacity:.7}
#pj-opcoes{display:none;gap:16px;align-items:center;flex-wrap:wrap;margin-top:12px;font-size:13px}
#pj-opcoes.on{display:flex}
#pj-opcoes label{display:flex;gap:6px;align-items:center;cursor:pointer}
#pj-paginas{width:150px;font:inherit;font-size:13px;padding:5px 8px;border-radius:6px;border:1px solid #d2d8e2;background:#fff;color:#1b1b1f}
#pj-acao{background:#2f6fed;border-color:#2f6fed;color:#fff;font-size:14px;padding:10px 18px;border-radius:8px;font-weight:600}
#pj-fechar{position:absolute;top:12px;right:16px;background:none;border:none;font-size:24px;line-height:1;cursor:pointer;color:#888}
#pj-log{background:#0f1115;color:#c8cdd6;font-family:ui-monospace,Consolas,monospace;font-size:12px;padding:9px 11px;border-radius:8px;max-height:150px;overflow:auto;white-space:pre-wrap;margin-top:12px;display:none}
#pj-out{width:100%;min-height:240px;max-height:44vh;font-family:ui-monospace,Consolas,monospace;font-size:12px;padding:10px;border-radius:8px;border:1px solid #d2d8e2;margin-top:12px;display:none;resize:vertical;background:#fff;color:#1b1b1f}
@media (prefers-color-scheme:dark){
#pj-box{background:#1f232b;color:#e6e6e9}
#pj-drop{border-color:#3a4150}
#pj-modos button{background:#262b34;color:#e6e6e9;border-color:#3a4150}
#pj-modos button.on{border-color:#2f6fed;background:rgba(47,111,237,.16)}
#pj-lista li{background:#262b34;border-color:#333a45}
#pj-box button{background:#2b313c;color:#e6e6e9;border-color:#3a4150}
#pj-acao{background:#2f6fed;border-color:#2f6fed;color:#fff}
#pj-out{background:#12151a;color:#c8cdd6;border-color:#3a4150}
}
"""

HTML_UI = (
    '<button id="pj-fechar" title="Fechar">&times;</button>'
    '<h2>PDFs</h2>'
    '<div id="pj-sub">Escolha o modo, selecione os arquivos e confira a ordem.</div>'
    '<div id="pj-modos">'
    '<button id="pj-modo-unir" class="on"><b>Unir em PDF</b>'
    '<span>Junta os arquivos num PDF s\u00f3</span></button>'
    '<button id="pj-modo-md"><b>Converter p/ Markdown</b>'
    '<span>Extrai o texto de cada PDF em .md</span></button>'
    '</div>'
    '<div id="pj-drop"><strong>Clique para escolher os PDFs</strong>'
    '<span>ou arraste os arquivos aqui</span></div>'
    '<input type="file" id="pj-input" accept="application/pdf,.pdf" multiple hidden>'
    '<ul id="pj-lista"></ul>'
    '<div id="pj-vazio">Nenhum arquivo selecionado ainda.</div>'
    '<div id="pj-opcoes">'
    '<label>Páginas <input id="pj-paginas" type="text" spellcheck="false"'
    ' placeholder="todas (ex.: 1, 3-5)"></label>'
    '<label><input id="pj-front" type="checkbox"> front matter YAML</label>'
    '<label title="Desligar pula o OCR e entrega o texto cru do PDF (rapido, mas ilegivel em PDF com fonte quebrada)">'
    '<input id="pj-ocr" type="checkbox" checked> OCR</label>'
    '<label title="OCR com portugues + ingles custa ~2,5s por pagina a mais">'
    '<input id="pj-ingles" type="checkbox"> + inglês</label>'
    '</div>'
    '<div id="pj-barra">'
    '<button id="pj-acao" disabled>Unir e baixar</button>'
    '<button id="pj-inverter" disabled>Inverter ordem</button>'
    '<button id="pj-limpar" disabled>Limpar</button>'
    '<span id="pj-info"></span></div>'
    '<textarea id="pj-out" spellcheck="false"></textarea>'
    '<div id="pj-log"></div>'
)

LOGICA = r"""
(function(){
  'use strict';
  if (window.__pjJuntadorAberto) {
    var velho = document.getElementById('pj-overlay');
    if (velho) { velho.remove(); window.__pjJuntadorAberto = false; }
  }

  var CSS_ = __CSS__;
  var UI_ = __UI__;
  var URL_PDFLIB = __PDFLIB__;
  var URL_PDFJS = __PDFJS__;
  var URL_PDFJS_WORKER = __PDFJS_WORKER__;

  var st = document.createElement('style');
  st.textContent = CSS_;
  document.head.appendChild(st);

  var ov = document.createElement('div');
  ov.id = 'pj-overlay';
  ov.innerHTML = '<div id="pj-box">' + UI_ + '</div>';
  document.body.appendChild(ov);
  window.__pjJuntadorAberto = true;

  function $(id){ return document.getElementById(id); }
  var input=$('pj-input'), drop=$('pj-drop'), lista=$('pj-lista'), vazio=$('pj-vazio');
  var btnAcao=$('pj-acao'), btnInverter=$('pj-inverter'), btnLimpar=$('pj-limpar');
  var info=$('pj-info'), logEl=$('pj-log'), outEl=$('pj-out');
  var opcoes=$('pj-opcoes'), campoPaginas=$('pj-paginas'), chkFront=$('pj-front');
  var chkOcr=$('pj-ocr');
  var chkIngles=$('pj-ingles');
  var bUnir=$('pj-modo-unir'), bMd=$('pj-modo-md');

  var modo = 'unir';
  var arquivos = [];

  function log(m){
    logEl.style.display='block';
    logEl.textContent += m + '\n';
    logEl.scrollTop = logEl.scrollHeight;
  }

  var colator = new Intl.Collator('pt-BR', {numeric:true, sensitivity:'base'});
  function ordenar(a,b){ return colator.compare(a.file.name, b.file.name); }

  function carregarScript(urls, teste, nome){
    if (teste()) return Promise.resolve();
    return urls.reduce(function(p, url){
      return p.catch(function(){
        return new Promise(function(ok, falha){
          var s=document.createElement('script');
          s.src=url;
          s.onload=function(){ teste() ? ok() : falha(new Error(nome+' nao inicializou')); };
          s.onerror=function(){ falha(new Error('falha ao baixar '+nome)); };
          document.head.appendChild(s);
        });
      });
    }, Promise.reject());
  }

  function carregarPdfLib(){
    return carregarScript(URL_PDFLIB, function(){ return !!window.PDFLib; }, 'pdf-lib')
      .then(function(){ return window.PDFLib; });
  }

  function carregarPdfJs(){
    var pronto = function(){ return !!(window.pdfjsLib && window.pdfjsLib.getDocument); };
    return carregarScript(URL_PDFJS, pronto, 'pdf.js').then(function(){
      if (URL_PDFJS_WORKER && window.pdfjsLib.GlobalWorkerOptions
          && !window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = URL_PDFJS_WORKER;
      }
      return window.pdfjsLib;
    });
  }

  // /Encrypt no trailer indica PDF criptografado.
  function criptografado(bytes){
    var ini = Math.max(0, bytes.length - 4096), c = '';
    for (var i=ini; i<bytes.length; i++) c += String.fromCharCode(bytes[i]);
    return /\/Encrypt[\s<(\[]/.test(c);
  }

  // Contagem de paginas barata: o pdf.js ja vai abrir o arquivo no modo MD,
  // e o pdf-lib (513 KB) so faz falta mesmo no modo unir. Assim o modo MD
  // nao baixa o pdf-lib so para mostrar "N pags".
  function contarPaginasPdfJs(file){
    return carregarPdfJs()
      .then(function(){
        return file.arrayBuffer();
      })
      .then(function(buf){
        return window.pdfjsLib.getDocument({data:new Uint8Array(buf)}).promise;
      })
      .then(function(doc){
        var n = doc.numPages;
        try { doc.destroy(); } catch(e){}
        return n;
      })
      .catch(function(){ return null; });
  }

  function contarPaginasPdfLib(file){
    return carregarPdfLib()
      .then(function(){ return file.arrayBuffer(); })
      .then(function(buf){
        return window.PDFLib.PDFDocument.load(new Uint8Array(buf),
          {ignoreEncryption:true, updateMetadata:false});
      })
      .then(function(doc){ return doc.getPageCount(); })
      .catch(function(){ return null; });
  }

  function contarPaginas(file){
    // unir precisa do pdf-lib de qualquer forma; md usa o pdf.js
    return modo === 'unir' ? contarPaginasPdfLib(file) : contarPaginasPdfJs(file);
  }

  // ------------------------------------------------------------------ RENDER
  function render(){
    lista.innerHTML='';
    var total = arquivos.length;
    vazio.style.display = total ? 'none' : 'block';

    arquivos.forEach(function(item, i){
      var li=document.createElement('li');
      var num=document.createElement('div');
      num.className='pj-num'; num.textContent=String(i+1);

      var nome=document.createElement('div');
      nome.className='pj-nome'; nome.textContent=item.file.name; nome.title=item.file.name;

      var pags=document.createElement('div');
      pags.className='pj-pags';
      if (item.cript) {
        pags.textContent='senha - ignorado';
        pags.style.color='#c02626'; pags.style.opacity='1';
      } else {
        pags.textContent = item.pags==null ? '' : item.pags + (item.pags===1?' pag':' pags');
      }

      var acoes=document.createElement('div');
      acoes.className='pj-acoes';

      var sub=document.createElement('button');
      sub.textContent='\u2191'; sub.title='Mover para cima'; sub.disabled = i===0;
      sub.onclick=function(){ trocar(i,i-1); };

      var des=document.createElement('button');
      des.textContent='\u2193'; des.title='Mover para baixo'; des.disabled = i===total-1;
      des.onclick=function(){ trocar(i,i+1); };

      var rem=document.createElement('button');
      rem.className='pj-rem'; rem.textContent='\u00d7'; rem.title='Remover';
      rem.onclick=function(){ arquivos.splice(i,1); render(); };

      acoes.appendChild(sub); acoes.appendChild(des); acoes.appendChild(rem);
      li.appendChild(num); li.appendChild(nome); li.appendChild(pags); li.appendChild(acoes);
      lista.appendChild(li);
    });

    var validos = arquivos.filter(function(a){ return !a.cript; });
    var somaPags = validos.reduce(function(s,a){ return s + (a.pags||0); }, 0);
    var somaMb = arquivos.reduce(function(s,a){ return s + a.file.size; }, 0) / 1048576;
    if (total) {
      var bloq = total - validos.length;
      info.textContent = validos.length + ' de ' + total + ' arquivo(s) \u00b7 ' +
        somaPags + ' pag \u00b7 ' + somaMb.toFixed(1) + ' MB' +
        (bloq ? ' \u00b7 ' + bloq + ' ignorado(s)' : '');
    } else {
      info.textContent='';
    }

    btnAcao.disabled = validos.length === 0;
    btnInverter.disabled = total < 2;
    btnLimpar.disabled = total === 0;
    btnAcao.textContent = modo === 'unir' ? 'Unir e baixar' : 'Converter e baixar .md';
  }

  function trocar(i,j){
    if (j<0 || j>=arquivos.length) return;
    var t=arquivos[i]; arquivos[i]=arquivos[j]; arquivos[j]=t;
    render();
  }

  function setModo(m){
    modo = m;
    bUnir.className = m==='unir' ? 'on' : '';
    bMd.className   = m==='md'   ? 'on' : '';
    opcoes.className = m==='md' ? 'on' : '';
    outEl.style.display='none';
    render();
  }

  function adicionar(fileList){
    var novos = Array.prototype.slice.call(fileList).filter(function(f){
      return /\.pdf$/i.test(f.name) || f.type==='application/pdf';
    });
    if (!novos.length) { log('Nenhum PDF na selecao.'); return; }

    function chave(f){ return f.name+'|'+f.size+'|'+f.lastModified; }
    var existentes = {};
    arquivos.forEach(function(a){ existentes[chave(a.file)] = 1; });

    var entrando = novos.filter(function(f){ return !existentes[chave(f)]; })
      .map(function(file){ return {file:file, pags:null, cript:false}; });

    arquivos = arquivos.concat(entrando).sort(ordenar);
    render();
    log('+ ' + entrando.length + ' arquivo(s). Total: ' + arquivos.length + '.');

    (function passo(i){
      if (i >= entrando.length) return;
      var item = entrando[i];
      item.file.arrayBuffer().then(function(buf){
        var bytes = new Uint8Array(buf);
        if (criptografado(bytes)) {
          item.cript = true;
          log('\u26a0 "' + item.file.name + '" esta protegido por senha - nao sera processado.');
          if (arquivos.indexOf(item) >= 0) render();
          passo(i+1);
          return;
        }
        contarPaginas(item.file).then(function(n){
          item.pags = n;
          if (n == null) log('\u26a0 Nao consegui ler "' + item.file.name + '".');
          if (arquivos.indexOf(item) >= 0) render();
          passo(i+1);
        });
      }).catch(function(e){
        log('\u26a0 Falha ao ler "' + item.file.name + '": ' + (e.message||e));
        passo(i+1);
      });
    })(0);
  }

  function baixar(blob, nome){
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function(){ URL.revokeObjectURL(url); }, 60000);
  }

  function carimbo(){
    return new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  }

  // ------------------------------------------------------------------- OCR
  // So carrega o Tesseract quando alguma pagina nao tem texto (PDF escaneado).
  // O WASM e o traineddata de portugues sao grandes (~10 MB na primeira vez),
  // por isso o carregamento e preguicoso e o worker e reaproveitado.
  var _ocrWorker = null;
  var _ocrFalhou = false;
  var paginasOcr = 0;

  function carregarTesseract(){
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    return new Promise(function(ok, falha){
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js';
      s.onload = function(){ window.Tesseract ? ok(window.Tesseract) : falha(new Error('Tesseract nao inicializou')); };
      s.onerror = function(){ falha(new Error('falha ao baixar Tesseract')); };
      document.head.appendChild(s);
    });
  }

  function obterWorkerOcr(){
    if (_ocrWorker) return Promise.resolve(_ocrWorker);
    if (_ocrFalhou) return Promise.reject(new Error('OCR indisponivel'));
    log('   ocr: baixando Tesseract + portugues (~7 MB, so na primeira vez)...');
    return carregarTesseract().then(function(T){
      // 'por' sozinho: medido 4,6s contra 7,2s com ['por','eng'] no mesmo
      // documento, e reconheceu MAIS texto. O modelo portugues ja cobre ASCII
      // e nomes de sistema; o ingles fica no seletor para quem precisar.
      var idiomas = chkIngles && chkIngles.checked ? ['por','eng'] : ['por'];
      return T.createWorker(idiomas, 1, {
        logger: function(m){
          if (m.status === 'loading tesseract core' || m.status === 'loading language traineddata') {
            if (typeof m.progress === 'number' && m.progress > 0) {
              log('   ocr: ' + m.status + ' ' + Math.round(m.progress*100) + '%');
            }
          }
        }
      });
    }).then(function(w){
      _ocrWorker = w;
      return w;
    }).catch(function(e){
      _ocrFalhou = true;
      throw e;
    });
  }

  // renderiza a pagina pdf.js num canvas e manda para o Tesseract.
  // largura: 700 em pagina vetorial com fonte quebrada (o desenho e' nitido,
  // nao precisa de pixel) e 1100 em scan de verdade. Medido: 700 = 7,3s/3 pag
  // contra 9,3s em 1300, perdendo ~14% do texto so no scan.
  function ocrPagina(page, largura){
    return obterWorkerOcr().then(function(){
      var LARGURA_ALVO = largura || 1100;
      var vp1 = page.getViewport({scale:1});
      var escala = Math.min(1.9, Math.max(1.0, LARGURA_ALVO / vp1.width));
      var viewport = page.getViewport({scale:escala});
      var larg = Math.ceil(viewport.width), alt = Math.ceil(viewport.height);
      var canvas = document.createElement('canvas');
      canvas.width = larg; canvas.height = alt;
      var ctx2d = canvas.getContext('2d');
      // fundo branco: PDFs escaneados costumam ter transparencia, e o OCR
      // erra quando o fundo e preto
      ctx2d.fillStyle = '#fff';
      ctx2d.fillRect(0,0,larg,alt);
      return page.render({canvasContext: ctx2d, viewport: viewport}).promise
        .then(function(){
          // binariza: cinza escuro vira preto puro e cinza claro vira branco.
          // Escaneados de processo trazem fundo acinzentado e ruido de
          // digitalizacao; sem isso o Tesseract gasta tempo tentando separar
          // cinzas e erra mais.
          try {
            var img = ctx2d.getImageData(0,0,larg,alt);
            var px = img.data;
            for (var i2=0; i2<px.length; i2+=4){
              var lum = (px[i2]*0.299 + px[i2+1]*0.587 + px[i2+2]*0.114);
              var v = lum < 160 ? 0 : 255;
              px[i2]=v; px[i2+1]=v; px[i2+2]=v;
            }
            ctx2d.putImageData(img, 0, 0);
          } catch(e){ /* canvas opaco (tainted) nao acontece aqui; segue sem binarizar */ }
          return canvas.toDataURL('image/png');
        });
    }).then(function(dataUrl){
      return obterWorkerOcr().then(function(worker){
        return worker.recognize(dataUrl);
      });
    }).then(function(res){
      var txt = (res && res.data && res.data.text) ? res.data.text : '';
      return limparTextoOcr(txt);
    });
  }

  // O OCR devolve o texto com quebras de linha do reconhecimento: remonta
  // paragrafos, junta a palavra cortada por hifen no fim da linha e remove
  // linhas que sao apenas ruido.
  function limparTextoOcr(txt){
    var linhas = String(txt || '').split(/\r?\n/);
    var saida = [];
    var atual = '';
    function fechar(){
      var t = atual.replace(/[ \t]+/g,' ').trim();
      atual = '';
      if (!t) return;
      // linha com 1-2 caracteres sem palavra = ruido do OCR
      if (t.length <= 2 && !/[0-9]{1,2}[.)]/.test(t)) return;
      saida.push(t);
    }
    for (var i=0; i<linhas.length; i++){
      var l = linhas[i].replace(/\s+$/,'');
      if (!l.trim()) { fechar(); saida.push(''); continue; }
      // hifen no fim = palavra continuava na linha de baixo
      if (/[A-Za-zÀ-ÿ]-$/.test(l.trim())) {
        atual += l.trim().replace(/-$/,'');
        continue;
      }
      if (atual) {
        // junta com a linha anterior quando ela nao terminou em pontuacao
        atual = atual + ' ' + l.trim();
      } else {
        atual = l.trim();
      }
      // fecha o paragrafo quando a linha termina em ponto/dois-pontos
      if (/[.:;!?]$/.test(atual)) fechar();
    }
    fechar();
    var out = saida.join('\n').replace(/\n{3,}/g,'\n\n').trim();
    return corrigirOcr(out);
  }

  // Correcoes conservadoras de OCR. So mexe onde o erro e' previsivel e a
  // troca e' segura; nada que possa alterar numero, nome ou citacao.
  function corrigirOcr(t){
    // 1) 'i'/'l' isolado trocado por 'I' dentro de palavra em CAIXA ALTA:
    //    "EXCELENTiISSIMO" -> "EXCELENTISSIMO". Exige 3+ maiusculas em volta
    //    para nao tocar em palavra minuscula legitima.
    t = t.replace(/\b([A-ZÀ-Ý]{3,})i([A-ZÀ-Ý]{2,})\b/g, '$1I$2');
    t = t.replace(/\b([A-ZÀ-Ý]{2,})l([A-ZÀ-Ý]{3,})\b/g, '$1I$2');
    // 2) barra vertical/hifen perdido entre numero de pagina: "FIs. 1]" -> "Fls.: 1"
    t = t.replace(/\bF[Iil1]s?\.?\s*([0-9]{1,3})\]/g, 'Fls.: $1');
    // 2b) numero romano no inicio de titulo que o OCR leu como digito/barra:
    //     "11 = DOS ELEMENTOS" -> "II - DOS ELEMENTOS". So atua quando a linha
    //     inteira parece titulo (maiusculas), para nao mexer em tabela.
    t = t.replace(/^([0-9Il|]{1,4})\s*[=—–-]+\s*(.+)$/gm, function(m, rom, resto){
      var letras = resto.replace(/[^A-ZÀ-Ý]/g,'');
      var todas = resto.replace(/[^A-Za-zÀ-Ý]/g,'');
      if (todas.length < 6 || letras.length / todas.length < 0.9) return m;
      var conv = rom.replace(/0/g,'O').replace(/1/g,'I').replace(/\|/g,'I').replace(/l/g,'I');
      if (!/^[IVX]+$/.test(conv)) return m;
      return conv + ' - ' + resto;
    });
    // 3) '—' virou travessao onde o original era hifen de intervalo
    //    ("Personalidade Jurídica — IDPJ"): mantem, e' estilistico.
    // 4) espaco antes de pontuacao
    t = t.replace(/\s+([,;:.!?])/g, '$1');
    // 5) pontuacao duplicada
    t = t.replace(/([,;:])\1+/g, '$1');
    return t;
  }

  function juntar(){
    return carregarPdfLib().then(function(){
      var final, paginas=0, ignorados=[];
      return window.PDFLib.PDFDocument.create().then(function(doc){
        final = doc;
        return (function loop(i){
          if (i >= arquivos.length) return Promise.resolve();
          var item = arquivos[i];
          if (item.cript) {
            ignorados.push(item.file.name + ' (senha)');
            log('[' + (i+1) + '/' + arquivos.length + '] ' + item.file.name + ' - ignorado');
            return loop(i+1);
          }
          log('[' + (i+1) + '/' + arquivos.length + '] ' + item.file.name);
          return item.file.arrayBuffer()
            .then(function(buf){
              return window.PDFLib.PDFDocument.load(new Uint8Array(buf),
                {ignoreEncryption:true});
            })
            .then(function(src){ return final.copyPages(src, src.getPageIndices()); })
            .then(function(cop){
              cop.forEach(function(p){ final.addPage(p); });
              paginas += cop.length;
            })
            .catch(function(e){
              ignorados.push(item.file.name);
              log('   ! ignorado: ' + (e.message||e));
            })
            .then(function(){ return loop(i+1); });
        })(0);
      }).then(function(){
        if (!paginas) throw new Error('Nenhuma pagina pudo ser importada.');
        return final.save();
      }).then(function(bytes){
        var blob = new Blob([bytes], {type:'application/pdf'});
        baixar(blob, 'juntado_' + carimbo() + '.pdf');
        log('\u2705 PDF gerado: ' + paginas + ' pagina(s), ' +
            (blob.size/1048576).toFixed(2) + ' MB.');
        if (ignorados.length) log('\u26a0 Ignorado(s): ' + ignorados.join(', '));
      });
    });
  }

  // --------------------------------------------------------------- MARKDOWN
  // Abordagem da ferramenta de referencia (pdf.js + heuristica de layout):
  //  1. getTextContent() devolve itens com transform [a,b,c,d,e,f] e `height`
  //     (tamanho efetivo da fonte), mais a coordenada Y de cada trecho.
  //  2. Trechos sao agrupados em LINHAS por Y (tolerancia de ~40% da altura).
  //  3. Linhas sao agrupadas em BLOCOS quando a distancia vertical e pequena
  //     (paragrafo continua) ou quebradas quando ha salto (novo paragrafo).
  //  4. Tamanho de fonte acima da mediana do documento => titulo; a escala
  //     relativa define o nivel (#, ##, ###).
  //  5. Marcadores no inicio da linha ("-", "*", "1.", "a)") => lista.
  //  6. Cabecalho/rodape sao reconhecidos por repetirem em varias paginas.
  function textoDoItem(it){
    var s = it.str || '';
    return s;
  }

  function mdPagina(conteudo, opts){
    var itens = conteudo.items || [];
    var linhas = [];
    // Indice por faixa de Y: antes, cada item varria TODAS as linhas ja
    // criadas (O(n^2)) e uma pagina densa tinha centenas de itens. Agora a
    // busca olha so as faixas vizinhas, com o mesmo criterio de tolerancia.
    var faixas = {};

    itens.forEach(function(it){
      if (!it.str) return;
      var tr = it.transform || [1,0,0,1,0,0];
      var x = tr[4], y = tr[5];
      var alt = Math.abs(it.height || tr[3] || tr[0] || 10);
      if (!isFinite(alt) || alt <= 0) alt = 10;
      // Os itens que sao apenas espaco vem com height 0 (o pdf.js nao da altura
      // a eles). Antes eu os descartava e tentava reconstruir o espaco por gap,
      // mas a estimativa de largura era grosseira e colava palavras
      // ("observadososarts"). Agora o espaco e preservado como texto.
      var soEspaco = !it.str.trim();
      if (soEspaco && !it.str) return;
      // width e a largura REAL do trecho no PDF; sem ela a estimativa por
      // numero de caracteres erra e o gap entre palavras deixa de ser visto.
      var larg = Math.abs(it.width || 0);

      // faixa do item: altura de referencia de ~1 pt por balde
      var chave = Math.round(y);
      var achou = null;
      // olha a faixa e as vizinhas (a tolerancia e alguns pontos)
      for (var d=-3; d<=3 && !achou; d++){
        var balde = faixas[chave + d];
        if (!balde) continue;
        for (var k=0; k<balde.length; k++){
          var cand = balde[k];
          if (Math.abs(cand.y - y) <= Math.max(alt, cand.alt) * 0.42) { achou = cand; break; }
        }
      }
      if (!achou) {
        achou = {y:y, alt:alt, partes:[]};
        linhas.push(achou);
        var b = faixas[chave];
        if (!b) { b = []; faixas[chave] = b; }
        b.push(achou);
      }
      achou.partes.push({x:x, s:it.str, alt:alt, larg:larg, espaco:soEspaco});
      if (alt > achou.alt) achou.alt = alt;
    });

    // maior Y = topo da pagina
    linhas.sort(function(a,b){ return b.y - a.y; });
    linhas.forEach(function(l){
      l.partes.sort(function(a,b){ return a.x - b.x; });
      var txt = '';
      var ultimoFim = null, ultimaAlt = l.alt;
      l.partes.forEach(function(p){
        // 1) item que ja e espaco: entra como espaco simples
        if (p.espaco) {
          if (txt && !/\s$/.test(txt)) txt += ' ';
          if (p.larg > 0) ultimoFim = p.x + p.larg;
          return;
        }
        // 2) item de texto: usa a largura real quando existir, senao estima
        var fim = p.larg > 0 ? (p.x + p.larg) : (p.x + p.s.length * p.alt * 0.5);
        if (ultimoFim !== null && txt && !/\s$/.test(txt)) {
          var gap = p.x - ultimoFim;
          // gap positivo relevante = havia um espaco no PDF que nao veio como
          // item proprio. O limiar acompanha o tamanho da fonte.
          var limiarGap = Math.max(1.2, Math.min(p.alt, ultimaAlt) * 0.16);
          if (gap > limiarGap) txt += ' ';
          // sobreposicao (gap muito negativo) = mesma palavra em spans
          // diferentes, como em texto com kerning; nao insere nada
        }
        txt += p.s;
        ultimoFim = fim;
        ultimaAlt = p.alt;
      });
      l.texto = txt.replace(/[ \t]+/g,' ').trim();
    });

    linhas = linhas.filter(function(l){ return l.texto; });

    // fontes: mediana das linhas para achar a escala de titulos
    var tamanhos = linhas.map(function(l){ return Math.round(l.alt * 10) / 10; })
      .sort(function(a,b){ return a-b; });
    var mediana = tamanhos.length ? tamanhos[Math.floor(tamanhos.length/2)] : 10;
    var maior = tamanhos.length ? tamanhos[tamanhos.length-1] : 10;

    // lista de marcadores
    var RE_MARCADOR = /^([\u2022\u2023\u25e6\u25aa\u25ab\u2043\u00b7\-*\u2013\u2014]|\(?[0-9]{1,2}[.)]|\(?[a-zA-Z][.)])\s+/;

    var saida = [];
    var buffer = [];
    var bufferAlt = mediana;
    var ultimoY = null;

    function descarregar(){
      if (!buffer.length) return;
      var txt = buffer.join(' ').replace(/\s+/g,' ').trim();
      buffer = [];
      if (!txt) return;

      var nivel = 0;
      if (opts.titulos && maior > 0 && bufferAlt >= mediana * 1.18) {
        var razao = bufferAlt / mediana;
        nivel = razao >= 1.75 ? 1 : (razao >= 1.42 ? 2 : 3);
      }
      if (nivel) {
        saida.push('\n' + new Array(nivel+1).join('#') + ' ' + txt + '\n');
        return;
      }
      if (opts.listas && RE_MARCADOR.test(txt)) {
        var m = txt.match(RE_MARCADOR);
        var corpo = txt.slice(m[0].length).trim();
        var marc = m[1];
        if (/[0-9]/.test(marc)) {
          // "1." / "2)" -> lista numerada do Markdown
          saida.push((marc.match(/[0-9]+/)||['1'])[0] + '. ' + corpo);
        } else if (/^[a-zA-Z][.)]$/.test(marc)) {
          // "a)" / "b." -> preserva a letra: virar "-" perde a referencia que
          // o texto usa depois ("conforme a alínea c")
          saida.push('- ' + marc.replace(/[)]$/,'') + ') ' + corpo);
        } else {
          saida.push('- ' + corpo);
        }
        return;
      }
      saida.push(txt + '\n');
    }

    linhas.forEach(function(l, i){
      if (i > 0 && ultimoY !== null) {
        var salto = ultimoY - l.y;
        var mesmaAltura = Math.abs(l.alt - bufferAlt) <= mediana * 0.12;
        var atualMarcador = RE_MARCADOR.test(l.texto);
        var bufferMarcador = buffer.length && RE_MARCADOR.test(buffer[0]);
        // A linha anterior terminou fechando uma ideia? Se nao terminou em
        // pontuacao, a linha de baixo e' continuacao do mesmo paragrafo ou do
        // mesmo item de lista, e nao pode virar bloco novo. Antes isso partia
        // frases no meio: "a) ... das empresas vinculadas" / "aos suscitados;"
        // Obs.: a classe evita aspas de proposito. O limpador de comentarios
        // do gerador trata aspas como inicio de string e desalinhava o resto
        // do codigo quando encontrava uma dentro de regex.
        var ULTIMO = buffer.length ? buffer[buffer.length-1] : '';
        var ultimoChar = ULTIMO ? ULTIMO.charAt(ULTIMO.length - 1) : '';
        var anteriorFechou = buffer.length > 0 &&
          ('.:;!?…)'.indexOf(ultimoChar) >= 0 ||
           ultimoChar === ']' || ultimoChar === '\u201d');
        // entrada de lista sempre abre bloco; saida de lista so quando o item
        // anterior tinha terminado (senao e' a continuacao do item)
        var quebraLista = atualMarcador || (bufferMarcador && anteriorFechou);
        // salto grande so quebra se a linha anterior fechou a ideia
        var quebraSalto = salto > Math.max(l.alt, bufferAlt) * 1.7 && anteriorFechou;
        if (quebraSalto || !mesmaAltura || quebraLista) {
          descarregar();
          bufferAlt = l.alt;
        }
      } else {
        bufferAlt = l.alt;
      }
      buffer.push(l.texto);
      ultimoY = l.y;
    });
    descarregar();

    return saida.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  // Fecha listas: garante linha em branco entre o ultimo item e um paragrafo
  // que o segue, senao o Markdown engole o paragrafo para dentro da lista.
  function separarListas(md){
    var linhas = md.split('\n');
    var out = [];
    for (var i=0; i<linhas.length; i++){
      var atual = linhas[i] || '';
      var prox = linhas[i+1] || '';
      out.push(atual);
      var atualItem = /^\s*([-*]|[0-9]+\.)\s/.test(atual);
      var proxItem = /^\s*([-*]|[0-9]+\.)\s/.test(prox);
      var proxTitulo = /^#{1,6}\s/.test(prox);
      if (atualItem && prox && !proxItem && !proxTitulo) out.push('');
    }
    return out.join('\n').replace(/\n{3,}/g,'\n\n');
  }

  // "1, 3-5" -> [0,2,3,4] (0-based). Vazio ou invalido = todas as paginas.
  function paginasEscolhidas(total){
    var todas = [];
    for (var i=0; i<total; i++) todas.push(i);
    var bruto = (campoPaginas.value || '').trim();
    if (!bruto) return todas;
    var vistos = {}, saida = [];
    bruto.split(/[,;]/).forEach(function(pedaco){
      var m = pedaco.trim().match(/^(\d+)\s*(?:-\s*(\d+))?$/);
      if (!m) return;
      var de = parseInt(m[1], 10), ate = m[2] ? parseInt(m[2], 10) : de;
      if (de > ate) { var t = de; de = ate; ate = t; }
      for (var n=de; n<=ate; n++){
        if (n >= 1 && n <= total && !vistos[n]) { vistos[n] = 1; saida.push(n-1); }
      }
    });
    if (!saida.length) return todas;
    saida.sort(function(a,b){ return a-b; });
    return saida;
  }

  // PDF com fonte Type3/sem ToUnicode entrega codigos de controle no lugar de
  // letras. Detecta e manda a pagina para o OCR em vez de gravar lixo.
  // ponytail: limiar fixo medido em PDFs do PJe (40%+ de controle); ajustar se
  // aparecer falso positivo em documento com muito simbolo.
  function pareceLixo(txt){
    if (!txt || txt.length < 80) return false;
    var ctrl = 0, letras = 0;
    for (var i=0; i<txt.length; i++){
      var c = txt.charCodeAt(i);
      if (c === 10 || c === 13 || c === 9) continue;
      if (c < 32) ctrl++;
      else if (c > 127 || (c >= 65 && c <= 90) || (c >= 97 && c <= 122)) letras++;
    }
    return ctrl / txt.length > 0.12 && letras / txt.length < 0.55;
  }

  function frontMatter(nome, paginas){
    var titulo = nome.replace(/\.pdf$/i, '').replace(/"/g, "'");
    return '---\ntitle: "' + titulo + '"\npages: ' + paginas +
      '\nsource: "' + nome.replace(/"/g, "'") +
      '"\ndate: ' + new Date().toISOString().slice(0,10) + '\n---\n\n';
  }

  // Pool simples com limite de concorrencia, preservando a ordem pelo indice.
  function pool(total, limite, tarefa){
    return new Promise(function(ok){
      var proximo = 0, ativos = 0, terminou = false;
      function bomba(){
        if (terminou) return;
        if (proximo >= total && ativos === 0) { terminou = true; return ok(); }
        while (ativos < limite && proximo < total){
          (function(n){
            ativos++;
            tarefa(n).catch(function(){}).then(function(){
              ativos--; bomba();
            });
          })(proximo++);
        }
      }
      bomba();
    });
  }

  function mdDocumento(){
    return carregarPdfJs().then(function(){
      var pdfjs = window.pdfjsLib;
      var partes = [], ignorados = [];
      var paginas = 0;
      // Extrai texto nativo primeiro (rapido e paralelo). So depois roda o OCR
      // nas paginas que ficaram sem texto, para o texto ja bom nao esperar por
      // ele. Antes tudo era serial: uma pagina escaneada travava as seguintes.
      var CONCORRENCIA = 6;

      return (function loop(i){
        if (i >= arquivos.length) return Promise.resolve();
        var item = arquivos[i];
        if (item.cript) {
          ignorados.push(item.file.name + ' (senha)');
          log('[' + (i+1) + '/' + arquivos.length + '] ' + item.file.name + ' - ignorado');
          return loop(i+1);
        }
        log('[' + (i+1) + '/' + arquivos.length + '] ' + item.file.name);
        var doc = null;
        return item.file.arrayBuffer()
          .then(function(buf){ return pdfjs.getDocument({data:new Uint8Array(buf)}).promise; })
          .then(function(d){
            doc = d;
            var alvo = paginasEscolhidas(d.numPages);
            if (alvo.length < d.numPages) {
              log('   paginas: ' + alvo.length + ' de ' + d.numPages + ' selecionada(s)');
            }
            var textoPaginas = new Array(alvo.length);
            var precisaOcr = [];
            // paginasComTexto conta separado das que vao para OCR; o total
            // exibido e' doc.numPages, para nao depender de qual ramo rodou
            var paginasComTexto = 0;
            return pool(alvo.length, CONCORRENCIA, function(idx){
              var n = alvo[idx] + 1;
              return d.getPage(n).then(function(page){
                return page.getTextContent().then(function(cont){
                  var md = mdPagina(cont, {titulos:true, listas:true});
                  var limpo = (md || '').replace(/\s/g,'');
                  var cru = cont.items.map(function(it){ return it.str || ''; }).join('');
                  var lixo = pareceLixo(cru);
                  if (limpo.length >= 30 && (!lixo || !chkOcr.checked)) {
                    textoPaginas[idx] = md;
                    paginasComTexto++;
                  } else {
                    // lixo = fonte quebrada em pagina vetorial: desenho nitido,
                    // OCR a 700 px basta. Vazio = scan: precisa de 1100.
                    precisaOcr.push([idx, lixo ? 700 : 1100]);
                    textoPaginas[idx] = lixo ? '' : (md || '');
                  }
                  try { page.cleanup(); } catch(e){}
                });
              }).catch(function(){
                textoPaginas[idx] = '';
              });
            }).then(function(){
              if (!precisaOcr.length) return null;
              precisaOcr.sort(function(a,b){ return a[0]-b[0]; });
              log('   ocr: ' + precisaOcr.length + ' pagina(s) sem texto - pode levar ~25s cada');
              // OCR tambem em paralelo, com menos concorrencia: cada worker do
              // Tesseract ja usa CPU pesado, e mais que isso satura a maquina.
              var concOcr = Math.min(3, precisaOcr.length,
                Math.max(1, Math.floor((navigator.hardwareConcurrency||2)/2)));
              var feitos = 0;
              return pool(precisaOcr.length, concOcr, function(idx){
                var pos = precisaOcr[idx][0];
                var larg = precisaOcr[idx][1];
                var n = alvo[pos] + 1;
                return doc.getPage(n).then(function(page){
                  return ocrPagina(page, larg).then(function(txt){
                    textoPaginas[pos] = txt;
                    paginasOcr++;
                    feitos++;
                    log('   ocr: pagina ' + n + ' concluida (' + feitos + '/' + precisaOcr.length + ')');
                  }).then(function(){
                    try { page.cleanup(); } catch(e){}
                  });
                }).catch(function(e){
                  log('   ! ocr falhou na pagina ' + n + ': ' + (e.message||e));
                });
              });
            }).then(function(){ return textoPaginas; });
          })
          .then(function(textoPaginas){
            // conta as paginas que realmente entraram (com texto ou por OCR),
            // e nao o numero de paginas do documento
            paginas += textoPaginas.filter(function(t){ return t && t.trim(); }).length;
            var corpo = textoPaginas.filter(function(t){ return t; }).join('\n\n');
            if (arquivos.length > 1) {
              partes.push('## ' + item.file.name.replace(/\.pdf$/i,'') + '\n\n' + corpo);
            } else {
              partes.push(corpo);
            }
            if (!corpo.trim()) {
              log('   ! nenhum texto, nem por OCR - arquivo provavelmente vazio ou corrompido');
            }
          })
          .catch(function(e){
            ignorados.push(item.file.name);
            log('   ! ignorado: ' + (e.message||e));
          })
          .then(function(){
            if (doc) { try { doc.destroy(); } catch(e){} }
            return loop(i+1);
          });
      })(0).then(function(){
        if (!paginas) throw new Error('Nenhuma pagina pudo ser lida.');
        var md = partes.join('\n\n---\n\n').trim() + '\n';
        md = separarListas(md);
        if (chkFront.checked && arquivos.length) {
          md = frontMatter(arquivos[0].file.name, paginas) + md;
        }
        var blob = new Blob([md], {type:'text/markdown;charset=utf-8'});
        baixar(blob, 'convertido_' + carimbo() + '.md');
        // Preview limitado: jogar varios MB no textarea trava a interface, e o
        // arquivo ja foi baixado de qualquer forma.
        var LIMITE_PREVIEW = 200000;
        outEl.style.display='block';
        outEl.value = md.length > LIMITE_PREVIEW
          ? md.slice(0, LIMITE_PREVIEW) + '\n\n[... preview cortado em ' +
            LIMITE_PREVIEW.toLocaleString('pt-BR') + ' de ' +
            md.length.toLocaleString('pt-BR') + ' caracteres; o arquivo baixado tem tudo ...]'
          : md;
        log('\u2705 Markdown gerado: ' + paginas + ' pagina(s), ' +
            md.length + ' caracteres.' +
            (paginasOcr ? ' (' + paginasOcr + ' por OCR)' : ''));
        if (ignorados.length) log('\u26a0 Ignorado(s): ' + ignorados.join(', '));
        if (_ocrWorker) { try { _ocrWorker.terminate(); } catch(e){} _ocrWorker = null; }
        return md;
      });
    });
  }

  // ------------------------------------------------------------------ ACAO
  function executar(){
    if (!arquivos.length) return;
    btnAcao.disabled = true;
    var rotulo = btnAcao.textContent;
    btnAcao.textContent = modo === 'unir' ? 'Unindo...' : 'Convertendo...';

    var tarefa = (modo === 'unir' ? juntar() : mdDocumento());
    tarefa.catch(function(e){
      log('\u274c Erro: ' + (e.message||e));
      if (/nao inicializou|falha ao baixar/.test(String(e.message||e))) {
        log('Verifique a conexao: as bibliotecas vem de CDN na primeira vez.');
      }
    }).then(function(){
      btnAcao.disabled = false;
      btnAcao.textContent = rotulo;
    });
  }

  // ---------------------------------------------------------------- EVENTOS
  bUnir.onclick = function(){ setModo('unir'); carregarPdfLib().catch(function(){}); };
  bMd.onclick = function(){ setModo('md'); };

  drop.onclick = function(){ input.click(); };
  input.onchange = function(){ adicionar(input.files); input.value=''; };

  ['dragenter','dragover'].forEach(function(ev){
    drop.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.add('hot'); });
  });
  ['dragleave','drop'].forEach(function(ev){
    drop.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.remove('hot'); });
  });
  drop.addEventListener('drop', function(e){
    if (e.dataTransfer && e.dataTransfer.files.length) adicionar(e.dataTransfer.files);
  });

  btnAcao.onclick = executar;
  btnInverter.onclick = function(){ arquivos.reverse(); render(); };
  btnLimpar.onclick = function(){
    arquivos=[]; render(); logEl.textContent=''; logEl.style.display='none';
    outEl.style.display='none'; outEl.value='';
  };
  $('pj-fechar').onclick = function(){ ov.remove(); window.__pjJuntadorAberto=false; };
  ov.addEventListener('click', function(e){
    if (e.target === ov) { ov.remove(); window.__pjJuntadorAberto=false; }
  });
  document.addEventListener('keydown', function esc(e){
    if (e.key === 'Escape') {
      ov.remove(); window.__pjJuntadorAberto=false;
      document.removeEventListener('keydown', esc);
    }
  });

  setModo('unir');

  // Pre-carrega as bibliotecas enquanto o usuario escolhe arquivos: o clique
  // em "Converter" entao nao espera download. O pdf.js serve os dois modos
  // (conta paginas mesmo em "unir"), e o pdf-lib so faz falta ao unir.
  carregarPdfJs().then(function(){
    if (modo === 'unir') { carregarPdfLib().catch(function(){}); }
  }).catch(function(){ /* sem rede o erro aparece na hora de executar */ });
})();
"""

PDFLIB = [
    "https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js",
    "https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/dist/pdf-lib.min.js",
]
# mesma versao usada pela ferramenta de referencia
PDFJS = [
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js",
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js",
]
PDFJS_WORKER = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"


def _sem_comentarios(js: str) -> str:
    """Remove comentarios /* */ e // de um JS, preservando strings e regex.

    Necessario porque o bookmarklet vira UMA linha: um // sobrevivente
    comentaria todo o codigo seguinte. O scanner respeita strings para nao
    quebrar 'https://' nem a regex de /Encrypt.
    """
    saida = []
    i, n = 0, len(js)
    estado = None
    while i < n:
        c = js[i]
        prox = js[i + 1] if i + 1 < n else ''
        if estado is None:
            if c == '/' and prox == '*':
                fim = js.find('*/', i + 2)
                i = n if fim < 0 else fim + 2
                continue
            if c == '/' and prox == '/':
                fim = js.find('\n', i)
                i = n if fim < 0 else fim
                continue
            if c in ('"', "'", '`'):
                estado = c
            saida.append(c)
            i += 1
            continue
        if c == '\\':
            saida.append(js[i:i + 2])
            i += 2
            continue
        if c == estado:
            estado = None
        saida.append(c)
        i += 1
    return ''.join(saida)


codigo = (LOGICA
          .replace("__CSS__", json.dumps(CSS))
          .replace("__UI__", json.dumps(HTML_UI))
          .replace("__PDFLIB__", json.dumps(PDFLIB))
          .replace("__PDFJS_WORKER__", json.dumps(PDFJS_WORKER))
          .replace("__PDFJS__", json.dumps(PDFJS)))

codigo = _sem_comentarios(codigo)
bookmarklet = "javascript:(function(){" + codigo + "})()"

bookmarklet = bookmarklet.replace("\n", " ").replace("\r", " ").replace("\t", " ")
while "  " in bookmarklet:
    bookmarklet = bookmarklet.replace("  ", " ")

SAIDA.write_text(bookmarklet, encoding="utf-8")
print("gerado:", SAIDA)
print("tamanho:", round(len(bookmarklet) / 1024, 1), "KB")
