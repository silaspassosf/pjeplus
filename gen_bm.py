# -*- coding: utf-8 -*-
import re, json, urllib.parse

# ---- Leitura do arquivo ----
with open(r"d:\PjePlus\html.txt", encoding="utf-8") as f:
    raw = f.read()

inner = re.sub(r"^<div[^>]+>", "", raw.strip())
inner = re.sub(r"</div>\s*$", "", inner.strip())

# ---- Limpeza global ----
inner = re.sub(r"<p><strong>TESTE</strong> - texto inserido\.</p>", "", inner)
inner = inner.replace(
    "{victor Instrru\u00e7\u00e3o com peritos)",
    "{victor Instrru\u00e7\u00e3o com peritos}"
)
inner = re.sub(r"<p[^>]*>\s*\[a partir daqui[^\]]*\]\s*</p>", "", inner, flags=re.IGNORECASE)
inner = re.sub(r"<p[^>]*>\s*\[para ambos\]\s*</p>", "", inner, flags=re.IGNORECASE)

# ---- Encontrar marcadores ----
marker_re = re.compile(r"\{([^{}]+)\}")
matches_braces = list(marker_re.finditer(inner))

hon_re2 = re.compile(r"\(honor\u00e1rios periciais - acordo p\u00f3s per\u00edcia\)[^\n<]*")
hon_match = hon_re2.search(inner)

# ---- Classificacao ----
def classify(key):
    k = key.lower().strip()
    if any(x in k for x in ["apenas victor", "s\u00f3 victor", "victor apenas"]):
        return "victor"
    if any(x in k for x in ["apenas otavio", "otavio apenas", "s\u00f3 otavio", "suspender otavio"]):
        return "otavio"
    if "victor" in k:
        return "victor"
    if "otavio" in k:
        return "otavio"
    return "ambos"

# ---- Limpar conteudo de bloco ----
def clean_block(html):
    html = re.sub(r"<p[^>]*>\s*#suspacordo\s*(?:novo)?\s*</p>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>\s*\(tele10min\s*(?:novo)?\)\s*</p>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"\[[^\[\]]*\]", "", html)
    html = re.sub(r"\(criar op[cç][oõ]es[^)]*\)", "", html, flags=re.IGNORECASE)
    for pat in [
        r"\botavio apenas\b", r"\bOtavio apenas\b",
        r"\bapenas victor\b", r"\bapenas Victor\b",
        r"\bpara ambos\b", r"\bambos\b",
        r"#suspacordo\s*(?:novo)?", r"#alv\b", r"\btele10min\b",
        r"\s*-\s*municipiorevel\b", r"\s*-\s*#alv\b", r"\s*-\s*ambos\b",
        r"\s*-\s*quando a segunda reclamada n\u00e3o concorda com o acordo",
    ]:
        html = re.sub(pat, "", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>\s*(?:<br data-cke-filler=\"true\">|&nbsp;|\s)*\s*</p>", "", html)
    return html.strip()

# ---- Limpar titulo ----
def clean_title(raw_title):
    t = raw_title.strip()
    specials = {
        "notdev novo apenas victor": "Citar por mandado e Edital",
        "tele - atraso da reclamada - apenas victor": "Tele - Atraso da reclamada",
        "munic\u00edpio revel apenas victor": "Munic\u00edpio revel",
        "victor instrru\u00e7\u00e3o com peritos": "Victor - Instru\u00e7\u00e3o com peritos",
        "instru\u00e7\u00e3o dr. victor": "Instru\u00e7\u00e3o Dr. Victor",
        "suspender otavio": "Suspender subsidi\u00e1ria",
        "alvar\u00e1": "Alvar\u00e1",
    }
    if t.lower() in specials:
        return specials[t.lower()]
    for suf in [
        r"\s*-?\s*apenas victor$", r"\s*-?\s*apenas otavio$",
        r"\s*-?\s*otavio apenas$", r"\s*-?\s*victor apenas$",
        r"\s*-?\s*ambos$", r"\s*-?\s*#alv$", r"\s*-?\s*#suspacordo$",
        r"\s*-?\s*novo$",
    ]:
        t = re.sub(suf, "", t, flags=re.IGNORECASE).strip()
    return t.strip(" -\u2013").strip()

def find_p_end(html, pos):
    idx = html.find("</p>", pos)
    return (idx + 4) if idx != -1 else pos

def find_p_start(html, pos):
    idx = html.rfind("<p", 0, pos)
    return idx if idx != -1 else 0

# ---- Construir lista de marcadores ----
all_markers = []
for m in matches_braces:
    all_markers.append({"type":"brace","start":m.start(),"end":m.end(),"raw_title":m.group(1)})
if hon_match:
    all_markers.append({"type":"paren","start":hon_match.start(),"end":hon_match.end(),"raw_title":"honor\u00e1rios periciais - acordo p\u00f3s per\u00edcia"})
all_markers.sort(key=lambda x: x["start"])

# ---- Extrair blocos ----
blocks = []
for i, mk_ in enumerate(all_markers):
    rt = mk_["raw_title"]
    title = clean_title(rt)
    cls = classify(rt)
    cs = find_p_end(inner, mk_["end"])
    ce = find_p_start(inner, all_markers[i+1]["start"]) if i+1 < len(all_markers) else len(inner)
    raw_c = inner[cs:ce]
    clean_c = clean_block(raw_c)
    blocks.append({"title":title,"raw_title":rt,"classification":cls,"html":clean_c,"special":mk_["type"]=="paren"})

# ---- Dados dos peritos ----
peritos = {
    "ROGERIO APARECIDO ROSA": {"banco":"001 \u2014 Banco do Brasil","agencia":"1832","conta":"160235-7"},
    "REGIANE SOUZA ROCHA SILVA": {"banco":"001 \u2014 Banco do Brasil","agencia":"0717","conta":"127844-4"},
    "CARLOS IRAYBA CREMONINI": {"banco":"341 \u2014 It\u00e1u Unibanco","agencia":"8215","conta":"13827-5"},
    "ALEXANDRE MARCOS INACO CIRINO": {"banco":"237 \u2014 Banco Bradesco","agencia":"2677","conta":"0049115-2"},
    "ALLAN STRUCK PINHEIRO": {"banco":"001 \u2014 Banco do Brasil","agencia":"1563","conta":"30305-4"},
    "MARIANA ACCARDO DE MORAES FONTES": {"banco":"341 \u2014 It\u00e1u Unibanco","agencia":"3768","conta":"39697-4"},
    "VLADIA JUOZEPAVICIUS GON\u00c7ALVES": {"banco":"","agencia":"","conta":""},
}

HON_BASE_HTML = (
    '<p style="margin-left:0cm;text-align:justify;text-indent:3cm;">'
    'A reclamada depositar\u00e1 os honor\u00e1rios periciais no valor de R$*, no prazo de 30 dias, '
    'ap\u00f3s o pagamento do acordo, na conta do perito * cujos dados banc\u00e1rios seguem: '
    'Banco *, ag\u00eancia *, conta corrente *.'
    '</p>'
)

# ---- Filtrar blocos por pessoa ----
def get_blocks_for(person, blks):
    return [b for b in blks if b["classification"] in ("ambos", person)]

blocks_otavio = get_blocks_for("otavio", blocks)
blocks_victor = get_blocks_for("victor", blocks)

# ---- Categorizar blocos em secoes ----
def categorize(blks):
    s1,s2,s3,s4,s5 = [],[],[],[],[]
    for b in blks:
        if b["special"] or b["title"] in ("CEP para endere\u00e7o","INFOJUD Nome/CPF/Endere\u00e7o"):
            continue
        t = b["title"].lower()
        rt = b["raw_title"].lower()
        if "instru" in t or "insru" in t:
            s1.append(b)
        elif t == "revelia":
            s1.append(b)  # revelia por ultimo
        elif "pericia" in rt or "per\u00edcia" in rt:
            s2.append(b)
        elif t in ("provimento","testemunha - independente","citar por mandado e edital"):
            s3.append(b)
        elif any(x in t for x in ("alvar","suspender","acordo","suspens\u00e3o")):
            s4.append(b)
        else:
            s5.append(b)
    # Ordenar s1: instrução primeiro, revelia por último
    s1.sort(key=lambda b: 1 if b["title"].lower() == "revelia" else 0)
    def ord4(b):
        t = b["title"].lower()
        if "alvar" in t: return 0
        if "suspender" in t: return 1
        if "retorno" in t or "+retorno" in t: return 2
        return 3
    s4.sort(key=ord4)
    return s1,s2,s3,s4,s5

# ---- Construir JS com layout em secoes ----
def build_js(blks, panel_title, person):
    s1,s2,s3,s4,s5 = categorize(blks)

    def jd(lst):
        return json.dumps([{"t":b["title"],"h":b["html"]} for b in lst], ensure_ascii=False)

    s1j = jd(s1); s2j = jd(s2); s3j = jd(s3); s4j = jd(s4); s5j = jd(s5)
    pj  = json.dumps(peritos, ensure_ascii=False)
    hj  = json.dumps(HON_BASE_HTML, ensure_ascii=False)
    tj  = json.dumps(panel_title, ensure_ascii=False)
    pid = panel_title.lower()

    p = []

    # Editor + selecao + insercao
    p.append("(function(){")
    p.append("var T=" + tj + ";")
    p.append("var ed=[...document.querySelectorAll('.ck-editor__editable[contenteditable=\"true\"],.ck-editor__editable_inline[contenteditable=\"true\"],[contenteditable=\"true\"]')].find(function(x){return x.ckeditorInstance;});")
    p.append("if(!ed){alert('Editor CKEditor 5 n\u00e3o encontrado.');return;}")
    p.append("var ck=ed.ckeditorInstance;var SR=null;")
    p.append("function sv(){try{var s=ck.model.document.selection;var r=[...s.getRanges()];SR=r.length>0?r[0]:null;}catch(e){SR=null;}}")
    p.append("function ins(h){if(!SR){alert('Posicione o cursor no editor antes de usar o bot\u00e3o.');return;}try{var v=ck.data.processor.toView(h);var m=ck.data.toModel(v);ck.model.change(function(){ck.model.insertContent(m,SR);});ed.focus();}catch(e){alert('Erro: '+e.message);}}")

    # Dados
    p.append("var S1=" + s1j + ";")
    p.append("var S2=" + s2j + ";")
    p.append("var S3=" + s3j + ";")
    p.append("var S4=" + s4j + ";")
    p.append("var S5=" + s5j + ";")
    p.append("var PR=" + pj + ";")
    p.append("var HH=" + hj + ";")

    # Toggle painel
    p.append("var ex=document.getElementById('bm-" + pid + "');")
    p.append("if(ex){ex.remove();return;}")
    p.append("sv();")

    # Criar painel
    p.append("var P=document.createElement('div');")
    p.append("P.id='bm-" + pid + "';")
    p.append("P.style.cssText='position:fixed;top:50%;transform:translateY(-50%);right:8px;width:295px;max-height:90vh;overflow-y:auto;background:#fff;border:1px solid #c8d0ea;border-radius:10px;padding:12px;z-index:2147483647;box-shadow:0 6px 24px rgba(30,50,130,.2);font-family:Arial,sans-serif;font-size:13px;';")

    # Helpers
    p.append("function E(t,c,x){var e=document.createElement(t);if(c)e.style.cssText=c;if(x!=null)e.textContent=x;return e;}")
    # ST(title) - titulo de secao, retorna o div container
    p.append("function ST(t){var d=E('div','margin-top:10px;border-top:1px solid #eef;padding-top:6px;');d.appendChild(E('div','font-weight:bold;font-size:10px;color:#8899cc;text-transform:uppercase;letter-spacing:.7px;margin-bottom:5px;',t));P.appendChild(d);return d;}")
    # BF(b) - botao flex (lado a lado, secao 1)
    p.append("function BF(b){var btn=E('button','flex:1 1 auto;min-width:70px;padding:7px 4px;background:#e8f0fe;border:1px solid #b0c4f8;border-radius:6px;cursor:pointer;font-size:11px;text-align:center;line-height:1.3;');btn.textContent=b.t;btn.onclick=function(){sv();ins(b.h);};btn.onmouseover=function(){this.style.background='#c5d8ff';};btn.onmouseout=function(){this.style.background='#e8f0fe';};return btn;}")
    # BC(b,bg) - card botao (secoes 3/4/5)
    p.append("function BC(b,bg){var btn=E('button','display:block;width:100%;padding:7px 8px;margin:3px 0;background:'+(bg||'#f5f8ff')+';border:1px solid #c8d4f0;border-radius:6px;cursor:pointer;font-size:12px;text-align:left;');btn.textContent=b.t;btn.onclick=function(){sv();ins(b.h);};btn.onmouseover=function(){this.style.background='#d8e4ff';};btn.onmouseout=function(){this.style.background=(bg||'#f5f8ff');};return btn;}")
    # BP(b) - card pequeno para grid de pericias
    p.append("function BP(b){var btn=E('button','padding:6px 4px;background:#f5f8ff;border:1px solid #c8d4f0;border-radius:5px;cursor:pointer;font-size:11px;text-align:center;width:100%;');btn.textContent=b.t;btn.onclick=function(){sv();ins(b.h);};btn.onmouseover=function(){this.style.background='#d8e4ff';};btn.onmouseout=function(){this.style.background='#f5f8ff';};return btn;}")

    # Cabecalho
    p.append("var hdr=E('div','display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:8px;border-bottom:2px solid #e8edff;');")
    p.append("hdr.appendChild(E('strong','font-size:15px;color:#223;',T));")
    p.append("var fc=E('button','border:none;background:none;cursor:pointer;font-size:18px;color:#aab;padding:0 2px;','\u2715');fc.onclick=function(){P.remove();};hdr.appendChild(fc);P.appendChild(hdr);")

    # SECAO 1: Instrucao + Revelia (flex, lado a lado)
    p.append("var r1=E('div','display:flex;flex-wrap:wrap;gap:4px;');")
    p.append("S1.forEach(function(b){r1.appendChild(BF(b));});")
    p.append("P.appendChild(r1);")

    # INFOJUD + CEP (abaixo da secao 1)
    p.append("var ricep=E('div','display:flex;gap:4px;margin-top:6px;');")
    p.append("var bInfo=E('button','flex:1;padding:5px 3px;background:#e8f5e9;border:1px solid #80c080;border-radius:5px;cursor:pointer;font-size:11px;text-align:center;','INFOJUD CPF');")
    p.append("var bCep2=E('button','flex:1;padding:5px 3px;background:#e3f2fd;border:1px solid #90caf9;border-radius:5px;cursor:pointer;font-size:11px;text-align:center;','CEP endere\u00e7o');")
    p.append("ricep.appendChild(bInfo);ricep.appendChild(bCep2);P.appendChild(ricep);")
    # Painel expansivel compartilhado
    p.append("var xp=E('div','display:none;margin-top:4px;padding:6px;background:#f8f8ff;border:1px solid #dde;border-radius:5px;');P.appendChild(xp);")
    # Form INFOJUD
    p.append("var fInfo=E('div','');")
    p.append("var cpfIn=E('input',null);cpfIn.type='text';cpfIn.placeholder='Digite o CPF';cpfIn.style.cssText='width:100%;box-sizing:border-box;margin-bottom:4px;padding:4px;font-size:12px;border:1px solid #ccc;border-radius:3px;';fInfo.appendChild(cpfIn);")
    p.append("var bPcpf=E('button','display:block;width:100%;padding:5px;background:#2196f3;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;','Pesquisar e colar');")
    p.append("bPcpf.onclick=function(){var c=cpfIn.value.replace(/\\D/g,'');if(c.length!==11){alert('Digite um CPF v\u00e1lido com 11 n\u00fameros.');return;}alert('Consulta INFOJUD ser\u00e1 implementada na pr\u00f3xima etapa.');};fInfo.appendChild(bPcpf);")
    # Form CEP
    p.append("var fCep=E('div','');")
    p.append("var cepIn=E('input',null);cepIn.type='text';cepIn.placeholder='Digite o CEP';cepIn.style.cssText='width:100%;box-sizing:border-box;margin-bottom:4px;padding:4px;font-size:12px;border:1px solid #ccc;border-radius:3px;';fCep.appendChild(cepIn);")
    p.append("var bPcep=E('button','display:block;width:100%;padding:5px;background:#2196f3;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;','Pesquisar e colar');")
    p.append("bPcep.onclick=function(){var c=cepIn.value.replace(/\\D/g,'');if(c.length!==8){alert('Digite um CEP v\u00e1lido com 8 n\u00fameros.');return;}alert('Consulta de CEP ser\u00e1 implementada na pr\u00f3xima etapa.');};fCep.appendChild(bPcep);")
    # Toggle INFOJUD
    p.append("bInfo.onclick=function(){var open=xp.style.display!=='none'&&xp.dataset.active==='info';xp.style.display=open?'none':'block';xp.dataset.active='info';while(xp.firstChild)xp.removeChild(xp.firstChild);if(!open)xp.appendChild(fInfo);};")
    # Toggle CEP
    p.append("bCep2.onclick=function(){var open=xp.style.display!=='none'&&xp.dataset.active==='cep';xp.style.display=open?'none':'block';xp.dataset.active='cep';while(xp.firstChild)xp.removeChild(xp.firstChild);if(!open)xp.appendChild(fCep);};")

    # SECAO 2: Pericias (grid 2 colunas)
    p.append("if(S2.length>0){var d2=ST('Per\u00edcias');var g2=E('div','display:grid;grid-template-columns:1fr 1fr;gap:4px;');S2.forEach(function(b){g2.appendChild(BP(b));});d2.appendChild(g2);}")

    # SECAO 3: Adiamento - Testemunhas
    p.append("if(S3.length>0){var d3=ST('Adiamento - Testemunhas');S3.forEach(function(b){d3.appendChild(BC(b));});}")

    # SECAO 4: Acordo
    p.append("var d4=ST('Acordo');")
    p.append("S4.forEach(function(b){d4.appendChild(BC(b));});")
    # Honorarios dentro de Acordo
    p.append("var honBtn=E('button','display:block;width:100%;padding:7px 8px;margin:3px 0;background:#fff8e1;border:1px solid #f0c060;border-radius:6px;cursor:pointer;font-size:12px;text-align:left;','Honor\u00e1rios periciais - acordo p\u00f3s per\u00edcia');")
    p.append("var honEx=E('div','display:none;margin-top:4px;padding:6px;background:#fffdf0;border:1px solid #f0d080;border-radius:5px;');")
    p.append("var selP=E('select','width:100%;margin-bottom:4px;padding:4px;font-size:12px;border:1px solid #ccc;border-radius:3px;');")
    p.append("var op0=E('option',null,'Selecione o perito aqui');op0.value='';selP.appendChild(op0);")
    p.append("Object.keys(PR).forEach(function(n){var o=E('option',null,n);o.value=n;selP.appendChild(o);});honEx.appendChild(selP);")
    p.append("var bColar=E('button','display:block;width:100%;padding:5px;background:#4caf50;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;','Colar dados');")
    p.append("bColar.onclick=function(){var n=selP.value;if(!n){selP.style.borderColor='red';return;}selP.style.borderColor='#ccc';var pp=PR[n];var hf=HH.replace('perito *',n).replace('Banco *',pp.banco||'(banco n\u00e3o informado)').replace('ag\u00eancia *',pp.agencia||'(ag\u00eancia n\u00e3o informada)').replace('conta corrente *',pp.conta||'(conta n\u00e3o informada)');sv();ins(hf);};honEx.appendChild(bColar);")
    p.append("honBtn.onclick=function(){honEx.style.display=honEx.style.display==='none'?'block':'none';};")
    p.append("d4.appendChild(honBtn);d4.appendChild(honEx);")

    # SECAO 5: Extras (apenas Victor ou blocos nao classificados)
    p.append("if(S5.length>0){var d5=ST('Extras');S5.forEach(function(b){d5.appendChild(BC(b,'#fdf5ff'));});}")

    p.append("document.body.appendChild(P);")
    p.append("})();")

    return "".join(p)

# ---- Gerar JS ----
js_otavio = build_js(blocks_otavio, "Otavio", "otavio")
js_victor = build_js(blocks_victor, "Victor", "victor")

bm_otavio = "javascript:" + urllib.parse.quote(js_otavio, safe="")
bm_victor = "javascript:" + urllib.parse.quote(js_victor, safe="")

assert "\n" not in bm_otavio
assert "\n" not in bm_victor

with open(r"d:\PjePlus\bookmarklet-otavio.txt", "w", encoding="utf-8", newline="") as f:
    f.write(bm_otavio)
with open(r"d:\PjePlus\bookmarklet-victor.txt", "w", encoding="utf-8", newline="") as f:
    f.write(bm_victor)
with open(r"d:\PjePlus\bookmarklet-otavio-readable.js", "w", encoding="utf-8") as f:
    f.write(js_otavio)
with open(r"d:\PjePlus\bookmarklet-victor-readable.js", "w", encoding="utf-8") as f:
    f.write(js_victor)

print(f"bookmarklet-otavio.txt: {len(bm_otavio):,} chars")
print(f"bookmarklet-victor.txt: {len(bm_victor):,} chars")

# ---- Imprimir secoes para conferencia ----
def print_sections(blks, name):
    s1,s2,s3,s4,s5 = categorize(blks)
    print(f"\n[{name}]")
    print(f"  S1 Instrucao+Revelia:  {[b['title'] for b in s1]}")
    print(f"  S2 Pericias:           {[b['title'] for b in s2]}")
    print(f"  S3 Adiamento:          {[b['title'] for b in s3]}")
    print(f"  S4 Acordo:             {[b['title'] for b in s4]}")
    print(f"  S5 Extras:             {[b['title'] for b in s5]}")

print_sections(blocks_otavio, "OTAVIO")
print_sections(blocks_victor, "VICTOR")

# ---- Validacoes ----
def validate(name, bm, js):
    errs = []
    if "\n" in bm: errs.append("contem newline")
    if not bm.startswith("javascript:"): errs.append("nao comeca com javascript:")
    bm_dec = urllib.parse.unquote(bm)
    if re.search(r'\bTESTE\b', bm_dec): errs.append("contem TESTE")
    if re.search(r"\{otavio", bm_dec, re.IGNORECASE): errs.append("contem {otavio")
    if re.search(r"\{victor", bm_dec, re.IGNORECASE): errs.append("contem {victor")
    if "hora da ativa" in bm_dec.lower(): errs.append("contem [hora da ativacao]")
    if "insertContent" not in js: errs.append("nao usa insertContent")
    if "selP" not in js: errs.append("nao tem selecao de peritos")
    if "CEP endere" not in js and "CEP para endere" not in js: errs.append("nao tem botao CEP")
    if "INFOJUD" not in js: errs.append("nao tem botao INFOJUD")
    if errs:
        print(f"[{name}] PROBLEMAS: {errs}")
    else:
        print(f"[{name}] OK!")

validate("Otavio", bm_otavio, js_otavio)
validate("Victor", bm_victor, js_victor)
print("\nConcluido.")
