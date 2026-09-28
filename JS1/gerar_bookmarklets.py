# -*- coding: utf-8 -*-
"""Gera bookmarklet-otavio.txt / bookmarklet-victor.txt (+ versões readable)
a partir de html.txt (HTML integral extraído do CKEditor 5)."""
import io, json, re, os
from urllib.parse import quote

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = io.open(os.path.join(RAIZ, 'html.txt'), encoding='utf-8').read()

# ---------------------------------------------------------------- marcadores
# '{victor Instrrução com peritos)' fecha com ')' (typo no documento-fonte)
# honorários: bloco especial sem chaves no fonte
MARCA_EXTRA = '{victor Instrrução com peritos)'
MARCA_HON = '(honorários periciais - acordo pós perícia)'
marcas = [(m.start(), m.group(1), len(m.group(0)))
          for m in re.finditer(r'\{([^{}]+)\}', HTML)]
marcas.append((HTML.index(MARCA_EXTRA), MARCA_EXTRA[1:-1], len(MARCA_EXTRA)))
marcas.append((HTML.index(MARCA_HON), MARCA_HON[1:-1], len(MARCA_HON)))
marcas.sort()
marcas.append((len(HTML), None, 0))

# ---------------------------------------------------------------- limpeza
RE_FILLER = re.compile(r'<p[^>]*>(?:\s|&nbsp;|<br[^>]*>)*</p>', re.I)
TESTE_P = '<p><strong>TESTE</strong> - texto inserido.</p>'
RE_TELE = re.compile(r'<p[^>]*>\s*\(tele10min novo\)\s*</p>', re.I)
RE_SUSP = re.compile(r'<p[^>]*>\s*#suspacordo novo\s*</p>', re.I)
RE_COLCH = re.compile(r'\[[^\]]*\]')            # [otavio apenas], [hora da ativação...], [para ambos]
RE_CRIAR = re.compile(r'\s*\(criar opçoes.*?documento enviado\s*\.?\s*', re.I)


def limpar(bruto):
    h = bruto
    i = h.find('</p>')                    # descarta resto do parágrafo do marcador
    h = h[i + 4:] if i >= 0 else h
    if h.rfind('</p>') >= 0:
        h = h[:h.rfind('</p>') + 4]       # descarta tag <p...> solta no fim
    h = h.replace(TESTE_P, '')
    h = RE_TELE.sub('', h)
    h = RE_SUSP.sub('', h)
    h = RE_CRIAR.sub('', h)
    h = RE_COLCH.sub('', h)
    h = h.strip()
    while True:                           # trim de parágrafos vazios/filler nas pontas
        h2 = RE_FILLER.sub('', h, count=1) if RE_FILLER.match(h) else h
        ms = list(RE_FILLER.finditer(h2))
        if ms and ms[-1].end() == len(h2.rstrip()):
            h2 = h2[:ms[-1].start()] + h2[ms[-1].end():]
        h2 = h2.strip()
        if h2 == h:
            break
        h = h2
    return h


# ---------------------------------------------------------------- blocos
blocos = []
for idx in range(len(marcas) - 1):
    pos, nome, tok = marcas[idx]
    bruto = HTML[pos + tok:marcas[idx + 1][0]]
    blocos.append({'nome': nome, 'h': limpar(bruto)})

# bloco especial honorários: sem chaves no fonte
hon = next(b for b in blocos if b['nome'].startswith('honorários periciais'))
HON_HTML = re.search(r'<p[^>]*>\s*A reclamada depositará.*?</p>', hon['h'], re.I).group(0)
hon['h'] = HON_HTML

TITULOS = {
    'notdev novo apenas victor': 'notdev',
    'Tele - Atraso da reclamada - apenas victor': 'Tele - Atraso da reclamada',
    'município revel apenas victor': 'município revel',
    'honorários periciais - acordo pós perícia': 'Honorários periciais - acordo pós perícia',
}
OTAVIO_SO = {'otavio - Insrução', 'pericia - allan', 'pericia - regiane',
             'Pericia - cirino', 'Pericia Vladia', 'suspender otavio'}
VICTOR_SO = {'instrução Dr. victor', 'victor Instrrução com peritos',
             'município revel apenas victor', 'notdev novo apenas victor',
             'Tele - Atraso da reclamada - apenas victor'}
SPECIAL = {'honorários periciais - acordo pós perícia',
           'INFOJUD Nome/CPF/Endereço', 'CEP para endereço'}


def lista(quem):
    out = []
    for b in blocos:
        n = b['nome']
        if n in SPECIAL:
            continue
        if n in OTAVIO_SO and quem != 'otavio':
            continue
        if n in VICTOR_SO and quem != 'victor':
            continue
        out.append({'t': TITULOS.get(n, n), 'h': b['h']})
    return out


# ---------------------------------------------------------------- template JS
JS = r"""(function(){
var titulo=%TITULO%;
var editable=[].slice.call(document.querySelectorAll('.ck-editor__editable[contenteditable="true"],.ck-editor__editable_inline[contenteditable="true"],[contenteditable="true"]')).filter(function(e){return e.ckeditorInstance;})[0];
if(!editable){alert('CKEditor 5 nao encontrado nesta pagina.');return;}
var editor=editable.ckeditorInstance;
var B=%BLOCOS%;
var peritos=%PERITOS%;
var saved=null;
function salvarSelecao(){try{saved=editor.model.document.selection.getFirstRange();}catch(e){saved=null;}}
function restaurarSelecao(){
  var sel=editor.model.document.selection;
  if(saved){editor.model.change(function(){sel.setTo(saved);});return;}
  var r=sel.getFirstRange();
  if(!r||r.root!==editor.model.document.getRoot()){alert('Posicione o cursor no editor antes de usar o botao.');return;}
}
function inserirHTML(html){
  restaurarSelecao();
  var viewFragment=editor.data.processor.toView(html);
  var modelFragment=editor.data.toModel(viewFragment);
  editor.model.change(function(){editor.model.insertContent(modelFragment,editor.model.document.selection);});
  editable.focus();
}
var painel=document.createElement('div');
painel.style.cssText='position:fixed;top:20px;right:20px;width:340px;max-height:90vh;overflow:auto;background:#fff;border:1px solid #888;border-radius:8px;padding:10px;z-index:2147483647;box-shadow:0 4px 18px rgba(0,0,0,.3);font-family:sans-serif;font-size:13px;';
var cab=document.createElement('div');
cab.style.cssText='font-weight:bold;font-size:15px;margin-bottom:8px;';
cab.textContent='Textos - '+titulo;
var fechar=document.createElement('button');
fechar.textContent='X';
fechar.style.cssText='float:right;';
fechar.onclick=function(){document.body.removeChild(painel);};
cab.appendChild(fechar);
painel.appendChild(cab);
function botao(txt,fn){
  var b=document.createElement('button');
  b.textContent=txt;
  b.style.cssText='display:block;width:100%;margin:4px 0;padding:6px;text-align:left;cursor:pointer;';
  b.onclick=fn;
  painel.appendChild(b);
  return b;
}
B.forEach(function(bl){botao(bl.t,function(){salvarSelecao();inserirHTML(bl.h);});});
function rotulo(txt){
  var d=document.createElement('div');
  d.style.cssText='font-weight:bold;margin:10px 0 4px 0;';
  d.textContent=txt;
  painel.appendChild(d);
}
function statusBox(){
  var s=document.createElement('div');
  s.style.cssText='color:#b00;font-size:12px;margin-top:4px;min-height:14px;';
  painel.appendChild(s);
  return s;
}
rotulo('Honorários periciais - acordo pós perícia');
var selP=document.createElement('select');
selP.style.cssText='display:block;width:100%;margin:4px 0;padding:4px;';
var opt0=document.createElement('option');
opt0.value='';opt0.textContent='Selecione o perito';
selP.appendChild(opt0);
Object.keys(peritos).forEach(function(n){var o=document.createElement('option');o.value=n;o.textContent=n;selP.appendChild(o);});
painel.appendChild(selP);
var stH=statusBox();
botao('Colar dados',function(){
  var n=selP.value;
  if(!n){stH.textContent='Selecione o perito aqui';return;}
  stH.textContent='';
  var p=peritos[n];
  var html='<p style="margin-left:0cm;text-align:justify;text-indent:3cm;">A reclamada depositará os honorários periciais no valor de R$*, no prazo de 30 dias, após o pagamento do acordo, na conta do perito '+n+' cujos dados bancários seguem: Banco '+p.banco+', agência '+p.agencia+', conta corrente '+p.conta+'.</p>';
  salvarSelecao();inserirHTML(html);
});
rotulo('CEP para endereço');
var inC=document.createElement('input');
inC.placeholder='Digite o CEP';
inC.style.cssText='display:block;width:100%;margin:4px 0;padding:4px;box-sizing:border-box;';
painel.appendChild(inC);
botao('Pesquisar e colar',function(){
  var cep=inC.value.replace(/\D/g,'');
  if(cep.length!==8){alert('Digite um CEP válido com 8 números.');return;}
  alert('Consulta de CEP será implementada na próxima etapa.');
});
rotulo('INFOJUD Nome/CPF/Endereço');
var inI=document.createElement('input');
inI.placeholder='Digite o CPF';
inI.style.cssText='display:block;width:100%;margin:4px 0;padding:4px;box-sizing:border-box;';
painel.appendChild(inI);
botao('Pesquisar e colar',function(){
  var cpf=inI.value.replace(/\D/g,'');
  if(cpf.length!==11){alert('Digite um CPF válido com 11 números.');return;}
  alert('Consulta INFOJUD será implementada na próxima etapa.');
});
document.body.appendChild(painel);
salvarSelecao();
})();"""


def gerar(quem, caminho_txt, caminho_js):
    code = (JS
            .replace('%TITULO%', json.dumps(quem.capitalize(), ensure_ascii=False))
            .replace('%BLOCOS%', json.dumps(lista(quem), ensure_ascii=False))
            .replace('%PERITOS%', json.dumps(PERITOS, ensure_ascii=False)))
    io.open(caminho_js, 'w', encoding='utf-8', newline='\n').write(code)
    uma_linha = ''.join(l for l in code.split('\n'))
    bookmarklet = 'javascript:' + quote(uma_linha, safe='')
    io.open(caminho_txt, 'w', encoding='utf-8', newline='\n').write(bookmarklet)

    # ---- validação automática
    assert bookmarklet.startswith('javascript:')
    assert '\n' not in bookmarklet and bookmarklet.count('\r') == 0
    for proibido in ['{otavio', '{victor', '[hora da ativação', 'texto inserido', 'tele10min',
                     '#suspacordo', 'setData', 'execCommand', 'apenas victor',
                     'Otavio apenas', 'otavio apenas', 'innerH']:
        assert proibido not in uma_linha, proibido
    for exigido in ['model.insertContent', 'toModel', 'ckeditorInstance',
                    'Selecione o perito aqui', 'Colar dados', 'Digite o CEP',
                    'Digite o CPF', 'Pesquisar e colar', 'ROGERIO APARECIDO ROSA',
                    'VLADIA JUOZEPAVICIUS GONÇALVES', 'Posicione o cursor']:
        assert exigido in uma_linha, exigido
    # nenhum marcador ou colchete restante nos textos dos blocos
    for bl in lista(quem):
        assert '{' not in bl['t'] and '{' not in bl['h'], bl['t']
        assert '[' not in bl['t'] and '[' not in bl['h'], bl['t']
    print('%s: %d blocos, txt=%d chars, js=%d chars' %
          (quem, len(lista(quem)), len(bookmarklet), len(code)))


PERITOS = {
    'ROGERIO APARECIDO ROSA': {'banco': '001 — Banco do Brasil', 'agencia': '1832', 'conta': '160235-7'},
    'REGIANE SOUZA ROCHA SILVA': {'banco': '001 — Banco do Brasil', 'agencia': '0717', 'conta': '127844-4'},
    'CARLOS IRAYBA CREMONINI': {'banco': '341 — Itaú Unibanco', 'agencia': '8215', 'conta': '13827-5'},
    'ALEXANDRE MARCOS INACO CIRINO': {'banco': '237 — Banco Bradesco', 'agencia': '2677', 'conta': '0049115-2'},
    'ALLAN STRUCK PINHEIRO': {'banco': '001 — Banco do Brasil', 'agencia': '1563', 'conta': '30305-4'},
    'MARIANA ACCARDO DE MORAES FONTES': {'banco': '341 — Itaú Unibanco', 'agencia': '3768', 'conta': '39697-4'},
    'VLADIA JUOZEPAVICIUS GONÇALVES': {'banco': '', 'agencia': '', 'conta': ''},
}

gerar('otavio', os.path.join(RAIZ, 'bookmarklet-otavio.txt'),
      os.path.join(RAIZ, 'bookmarklet-otavio-readable.js'))
gerar('victor', os.path.join(RAIZ, 'bookmarklet-victor.txt'),
      os.path.join(RAIZ, 'bookmarklet-victor-readable.js'))
print('ok')
