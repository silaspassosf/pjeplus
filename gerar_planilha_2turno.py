"""Planilha de acompanhamento Presidente Ubatuba-SP: 1o turno normalizado + 2o turno preenchivel, com comparativo."""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import FormulaRule, CellIsRule
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

DIR = r"D:\PjePlus\dados_tse_2026"
SAIDA = r"D:\PjePlus\Ubatuba_2026_Presidente_1T_2T_Lula_x_Flavio.xlsx"

p = pd.read_pickle(f"{DIR}\\ubatuba_presidente.pkl")

# ---- Base por seção (1o turno) ----
# O cadastro oficial do TSE lista 247 seções em Ubatuba (zona 144).
# Dessas, 238 sao "Principal" (recebem os votos) e 9 sao "Agregada" (incorporadas a uma principal).
meta = pd.read_pickle(f"{DIR}\\secao_meta.pkl")
meta["NR_SECAO"] = meta["NR_SECAO"].astype(int)
meta["NR_ZONA"] = meta["NR_ZONA"].astype(int)
meta = meta.drop_duplicates("NR_SECAO").set_index("NR_SECAO")

ag = p.groupby(["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO"])
por_secao = {}
for (zona, secao, cod, nm), df in ag:
    v = df.set_index("NR_VOTAVEL")["QT_VOTOS"]
    lula = int(v.get(13, 0))
    flavio = int(v.get(22, 0))
    bn = int(v.get(95, 0) + v.get(96, 0))          # brancos + nulos agrupados
    total = int(v.sum())
    outros = total - lula - flavio - bn             # demais candidatos
    por_secao[int(secao)] = dict(zona=int(zona), secao=int(secao), local=str(nm),
                                 lula=lula, flavio=flavio, bn=bn, outros=outros, total=total)

linhas = []
for sec in sorted(meta.index):
    m = meta.loc[sec]
    base = por_secao.get(sec)
    tipo = str(m["DS_TIPO_SECAO_AGREGADA"])
    principal = int(m["NR_SECAO_PRINCIPAL"])
    if base is None:
        # Secao agregada: nao vota separadamente; votos vao para a secao principal
        linhas.append(dict(zona=int(m["NR_ZONA"]), secao=int(sec),
                           local=str(m["NM_LOCAL_VOTACAO"]),
                           lula=0, flavio=0, bn=0, outros=0, total=0,
                           tipo=tipo, principal=principal,
                           eleitores=int(m["QT_ELEITOR_SECAO"])))
    else:
        base.update(tipo=tipo, principal=principal, eleitores=int(m["QT_ELEITOR_SECAO"]))
        linhas.append(base)
d = pd.DataFrame(linhas).sort_values("secao").reset_index(drop=True)

d["v1"] = d["lula"] + d["flavio"]                   # votos válidos = somente os 2
d["pl1"] = (d["lula"] / d["v1"]).fillna(0)
d["pf1"] = (d["flavio"] / d["v1"]).fillna(0)
d["pbn1"] = (d["bn"] / d["total"]).fillna(0)
d["vant1"] = d["flavio"] - d["lula"]

assert (d["lula"] + d["flavio"] + d["bn"] + d["outros"] == d["total"]).all()
pr = d[d["total"] > 0]
assert abs(pr["pl1"] + pr["pf1"] - 1).max() < 1e-9
assert len(d) == 247, len(d)
assert list(d["secao"]) == list(range(1, 248)), "numeracao incompleta"

print("secoes na base:", len(d), "| principais:", (d.tipo == "Principal").sum(),
      "| agregadas:", (d.tipo == "Agregada").sum())
print("eleitores:", int(d.eleitores.sum()))
print(d[["secao", "tipo", "local", "lula", "flavio", "bn", "v1"]].head(10).to_string())
print("TOTAIS 1T: lula", d.lula.sum(), "flavio", d.flavio.sum(), "BN", d.bn.sum(),
      "outros", d.outros.sum(), "validos", d.v1.sum(), "total", d.total.sum())
print("pct lula", round(d.lula.sum() / d.v1.sum() * 100, 2), "pct flavio", round(d.flavio.sum() / d.v1.sum() * 100, 2))

N = len(d)
PRIMEIRA = 6
ULTIMA = PRIMEIRA + N - 1          # 243
TOTAL_ROW = ULTIMA + 1             # 244

# ---- Estilos ----
AZUL = "1F4E79"; VERM = "C00000"; CINZA_T = "1F3864"
f_titulo = Font(name="Calibri", size=16, bold=True, color=AZUL)
f_sub = Font(name="Calibri", size=10, italic=True, color="595959")
f_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
f_bold = Font(name="Calibri", size=11, bold=True)
b_thin = Side(style="thin", color="BFBFBF")
borda = Border(left=b_thin, right=b_thin, top=b_thin, bottom=b_thin)
fill_1t = PatternFill("solid", fgColor=CINZA_T)
fill_2t = PatternFill("solid", fgColor="C55A11")
fill_cmp = PatternFill("solid", fgColor="375623")
fill_lula = PatternFill("solid", fgColor=VERM)
fill_flavio = PatternFill("solid", fgColor=AZUL)
fill_total = PatternFill("solid", fgColor="DDEBF7")
fill_input = PatternFill("solid", fgColor="FFF2CC")
fill_agreg = PatternFill("solid", fgColor="FFF2CC")
centro = Alignment(horizontal="center", vertical="center")
esq = Alignment(horizontal="left", vertical="center")

wb = Workbook()
ws = wb.active
ws.title = "1T e 2T por Seção"

# Linhas de titulo
ws["A1"] = "Presidente da República — Ubatuba/SP — 1º Turno (04/10/2026) × 2º Turno (25/10/2026)"
ws["A1"].font = f_titulo
ws.merge_cells("A1:Y1")
ws["A2"] = ("Zona 144 • 247 seções cadastradas no TSE (238 principais + 9 agregadas) • "
            "Base normalizada: apenas Lula + Flávio; brancos e nulos agrupados. "
            "Os percentuais de candidato usam como denominador os votos válidos dos dois. "
            "1º turno: dados oficiais do TSE. 2º turno: preencher manualmente as células amarelas.")
ws["A2"].font = f_sub
ws.merge_cells("A2:Y2")
ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
ws.row_dimensions[1].height = 26
ws.row_dimensions[2].height = 30

# Mapa de colunas (A=1 ... T=20)
#  1 A No       2 B Local   3 C Lula1T   4 D Flavio1T  5 E %L1T   6 F %F1T
#  7 G Validos1T  8 H B+N 1T
#  9 I Lula2T  10 J Flavio2T  11 K %L2T  12 L %F2T  13 M Validos2T  14 N B+N 2T  15 O %B+N 2T
# 16 P Var validos  17 Q Var validos %  18 R Var Lula  19 S Cresc Lula%
# 20 T Var Flavio   (e mais 3 colunas): use letras explicitas abaixo
from openpyxl.utils import get_column_letter as _gcl

COL = {
    "no": 1, "local": 2, "sit": 3,
    "l1": 4, "f1": 5, "pl1": 6, "pf1": 7, "v1": 8, "bn1": 9,
    "l2": 10, "f2": 11, "pl2": 12, "pf2": 13, "v2": 14,
    "branco2": 15, "nulo2": 16, "bn2": 17, "pbn2": 18,
    "varv": 19, "varv_pct": 20, "varl": 21, "crl": 22, "varf": 23, "crf": 24, "quem": 25,
}
LAST_COL = 25

def L(nome):
    return _gcl(COL[nome])

# Linha 4: faixas de grupo
grupos = [
    ((COL["no"], COL["sit"]), "Seção / Local de votação", fill_1t),
    ((COL["l1"], COL["bn1"]), "1º TURNO (TSE)", fill_1t),
    ((COL["l2"], COL["pbn2"]), "2º TURNO (preencher)", fill_2t),
    ((COL["varv"], COL["quem"]), "COMPARATIVO 2T × 1T", fill_cmp),
]
for (c1, c2), txt, fill in grupos:
    ws.merge_cells(start_row=4, start_column=c1, end_row=4, end_column=c2)
    c = ws.cell(row=4, column=c1, value=txt)
    c.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    c.fill = fill
    c.alignment = centro
    for col in range(c1, c2 + 1):
        ws.cell(row=4, column=col).fill = fill
        ws.cell(row=4, column=col).border = borda
ws.row_dimensions[4].height = 22

# Linha 5: cabecalho das colunas
H = [
    ("Nº", fill_1t), ("Local de votação", fill_1t), ("Situação", fill_1t),
    ("Lula\nvotos", fill_lula), ("Flávio\nvotos", fill_flavio),
    ("Lula\n% vál.", fill_lula), ("Flávio\n% vál.", fill_flavio),
    ("Válidos\n(2)", fill_1t), ("Brancos+\nNulos", fill_1t),
    ("Lula\nvotos", fill_2t), ("Flávio\nvotos", fill_2t),
    ("Lula\n% vál.", fill_2t), ("Flávio\n% vál.", fill_2t),
    ("Válidos\n(2)", fill_2t), ("Brancos", fill_2t), ("Nulos", fill_2t),
    ("Brancos+\nNulos (soma)", fill_2t), ("Brancos+\nNulos %", fill_2t),
    ("Válidos\n(var.)", fill_cmp), ("Válidos\n(var. %)", fill_cmp),
    ("Lula\n(var. votos)", fill_cmp), ("Lula\n(cresc. %)", fill_cmp),
    ("Flávio\n(var. votos)", fill_cmp), ("Flávio\n(cresc. %)", fill_cmp),
    ("Quem\ncresceu", fill_cmp),
]
for i, (h, fill) in enumerate(H, start=1):
    c = ws.cell(row=5, column=i, value=h)
    c.font = f_hdr
    c.fill = fill
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = borda
ws.row_dimensions[5].height = 40

# ---- Dados ----
for i, x in d.iterrows():
    r = PRIMEIRA + i
    C = {k: L(k) for k in COL}
    ws.cell(row=r, column=COL["no"], value=int(x["secao"])).alignment = centro
    ws.cell(row=r, column=COL["local"], value=str(x["local"]).title()).alignment = esq
    if x["tipo"] == "Agregada":
        sit = f"Agregada à {int(x['principal'])}"
        cs = ws.cell(row=r, column=COL["sit"], value=sit)
        cs.fill = fill_agreg
        cs.font = Font(name="Calibri", size=9, italic=True, color="7F6000")
    else:
        ws.cell(row=r, column=COL["sit"], value="Principal").font = Font(name="Calibri", size=9, color="595959")
    # Seção agregada não recebe voto próprio: as células do 1o turno ficam com "—"
    agreg = x["tipo"] == "Agregada"
    # 1o turno (valores e % dos validos)
    ws.cell(row=r, column=COL["l1"], value=None if agreg else int(x["lula"])).number_format = "#,##0"
    ws.cell(row=r, column=COL["f1"], value=None if agreg else int(x["flavio"])).number_format = "#,##0"
    ws.cell(row=r, column=COL["pl1"], value=f"=IF(${C['v1']}{r}=0,\"\",{C['l1']}{r}/${C['v1']}{r})").number_format = "0.00%"
    ws.cell(row=r, column=COL["pf1"], value=f"=IF(${C['v1']}{r}=0,\"\",{C['f1']}{r}/${C['v1']}{r})").number_format = "0.00%"
    ws.cell(row=r, column=COL["v1"], value=f"={C['l1']}{r}+{C['f1']}{r}").number_format = "#,##0"
    ws.cell(row=r, column=COL["bn1"], value=None if agreg else int(x["bn"])).number_format = "#,##0"
    # 2o turno (entrada manual amarela): Lula, Flavio, Brancos e Nulos (separados)
    for k in ("l2", "f2", "branco2", "nulo2"):
        c = ws.cell(row=r, column=COL[k], value=None)
        c.number_format = "#,##0"
        c.fill = fill_input
    # 2o turno: validos (so os dois), soma B+N e percentuais
    ws.cell(row=r, column=COL["v2"], value=f"=N({C['l2']}{r})+N({C['f2']}{r})").number_format = "#,##0"
    ws.cell(row=r, column=COL["bn2"], value=f"=N({C['branco2']}{r})+N({C['nulo2']}{r})").number_format = "#,##0"
    ws.cell(row=r, column=COL["pl2"], value=f"=IF(N(${C['v2']}{r})=0,\"\",N({C['l2']}{r})/N(${C['v2']}{r}))").number_format = "0.00%"
    ws.cell(row=r, column=COL["pf2"], value=f"=IF(N(${C['v2']}{r})=0,\"\",N({C['f2']}{r})/N(${C['v2']}{r}))").number_format = "0.00%"
    ws.cell(row=r, column=COL["pbn2"],
            value=f"=IF(N(${C['v2']}{r})=0,\"\",N({C['bn2']}{r})/(N(${C['v2']}{r})+N({C['bn2']}{r})))").number_format = "0.00%"
    # comparativo (v2 = validos 2T, v1 = validos 1T)
    ws.cell(row=r, column=COL["varv"], value=f"=IF(${C['v2']}{r}=0,\"\",{C['v2']}{r}-{C['v1']}{r})").number_format = "+#,##0;-#,##0;\"—\""
    ws.cell(row=r, column=COL["varv_pct"], value=f"=IF(OR(${C['v1']}{r}=0,${C['v2']}{r}=0),\"\",{C['v2']}{r}/${C['v1']}{r}-1)").number_format = "+0.00%;-0.00%;0.00%"
    ws.cell(row=r, column=COL["varl"], value=f"=IF(${C['v2']}{r}=0,\"\",N({C['l2']}{r})-{C['l1']}{r})").number_format = "+#,##0;-#,##0;\"—\""
    ws.cell(row=r, column=COL["crl"], value=f"=IF(OR(${C['l1']}{r}=0,N({C['l2']}{r})=0),\"\",N({C['l2']}{r})/{C['l1']}{r}-1)").number_format = "+0.00%;-0.00%;0.00%"
    ws.cell(row=r, column=COL["varf"], value=f"=IF(${C['v2']}{r}=0,\"\",N({C['f2']}{r})-{C['f1']}{r})").number_format = "+#,##0;-#,##0;\"—\""
    ws.cell(row=r, column=COL["crf"], value=f"=IF(OR(${C['f1']}{r}=0,N({C['f2']}{r})=0),\"\",N({C['f2']}{r})/{C['f1']}{r}-1)").number_format = "+0.00%;-0.00%;0.00%"
    ws.cell(row=r, column=COL["quem"],
            value=(f"=IF(${C['v2']}{r}=0,\"\",IF({C['crl']}{r}=\"\",IF({C['crf']}{r}=\"\",\"—\",\"Flávio\"),"
                   f"IF({C['crf']}{r}=\"\",\"Lula\",IF({C['crl']}{r}>{C['crf']}{r},\"Lula\","
                   f"IF({C['crf']}{r}>{C['crl']}{r},\"Flávio\",\"Igual\")))))"))
    for col in range(1, LAST_COL + 1):
        cu = ws.cell(row=r, column=col)
        cu.border = borda
        if col >= COL["l1"]:
            cu.alignment = centro

# ---- Linha de total ----
r = TOTAL_ROW
C = {k: L(k) for k in COL}
ws.cell(row=r, column=COL["no"], value="")
ws.cell(row=r, column=COL["local"], value="TOTAL UBATUBA")


def soma2t(k):
    col = C[k]
    return f"=IF(COUNT({col}{PRIMEIRA}:{col}{ULTIMA})=0,\"\",SUM({col}{PRIMEIRA}:{col}{ULTIMA}))"


ws.cell(row=r, column=COL["l1"], value=f"=SUM({C['l1']}{PRIMEIRA}:{C['l1']}{ULTIMA})").number_format = "#,##0"
ws.cell(row=r, column=COL["f1"], value=f"=SUM({C['f1']}{PRIMEIRA}:{C['f1']}{ULTIMA})").number_format = "#,##0"
ws.cell(row=r, column=COL["pl1"], value=f"=IF(${C['v1']}{r}=0,\"\",{C['l1']}{r}/${C['v1']}{r})").number_format = "0.00%"
ws.cell(row=r, column=COL["pf1"], value=f"=IF(${C['v1']}{r}=0,\"\",{C['f1']}{r}/${C['v1']}{r})").number_format = "0.00%"
ws.cell(row=r, column=COL["v1"], value=f"={C['l1']}{r}+{C['f1']}{r}").number_format = "#,##0"
ws.cell(row=r, column=COL["bn1"], value=f"=SUM({C['bn1']}{PRIMEIRA}:{C['bn1']}{ULTIMA})").number_format = "#,##0"
ws.cell(row=r, column=COL["l2"], value=soma2t("l2")).number_format = "#,##0"
ws.cell(row=r, column=COL["f2"], value=soma2t("f2")).number_format = "#,##0"
ws.cell(row=r, column=COL["branco2"], value=soma2t("branco2")).number_format = "#,##0"
ws.cell(row=r, column=COL["nulo2"], value=soma2t("nulo2")).number_format = "#,##0"
ws.cell(row=r, column=COL["bn2"], value=f"=N({C['branco2']}{r})+N({C['nulo2']}{r})").number_format = "#,##0"
ws.cell(row=r, column=COL["v2"], value=f"=N({C['l2']}{r})+N({C['f2']}{r})").number_format = "#,##0"
ws.cell(row=r, column=COL["pl2"], value=f"=IF(N(${C['v2']}{r})=0,\"\",N({C['l2']}{r})/N(${C['v2']}{r}))").number_format = "0.00%"
ws.cell(row=r, column=COL["pf2"], value=f"=IF(N(${C['v2']}{r})=0,\"\",N({C['f2']}{r})/N(${C['v2']}{r}))").number_format = "0.00%"
ws.cell(row=r, column=COL["pbn2"],
        value=f"=IF(N(${C['v2']}{r})=0,\"\",N({C['bn2']}{r})/(N({C['v2']}{r})+N({C['bn2']}{r})))").number_format = "0.00%"
ws.cell(row=r, column=COL["varv"], value=f"=IF(${C['v2']}{r}=0,\"\",{C['v2']}{r}-{C['v1']}{r})").number_format = "+#,##0;-#,##0;\"—\""
ws.cell(row=r, column=COL["varv_pct"], value=f"=IF(OR(${C['v1']}{r}=0,${C['v2']}{r}=0),\"\",{C['v2']}{r}/${C['v1']}{r}-1)").number_format = "+0.00%;-0.00%;0.00%"
ws.cell(row=r, column=COL["varl"], value=f"=IF(${C['v2']}{r}=0,\"\",N({C['l2']}{r})-{C['l1']}{r})").number_format = "+#,##0;-#,##0;\"—\""
ws.cell(row=r, column=COL["crl"], value=f"=IF(OR(${C['l1']}{r}=0,N({C['l2']}{r})=0),\"\",N({C['l2']}{r})/{C['l1']}{r}-1)").number_format = "+0.00%;-0.00%;0.00%"
ws.cell(row=r, column=COL["varf"], value=f"=IF(${C['v2']}{r}=0,\"\",N({C['f2']}{r})-{C['f1']}{r})").number_format = "+#,##0;-#,##0;\"—\""
ws.cell(row=r, column=COL["crf"], value=f"=IF(OR(${C['f1']}{r}=0,N({C['f2']}{r})=0),\"\",N({C['f2']}{r})/{C['f1']}{r}-1)").number_format = "+0.00%;-0.00%;0.00%"
ws.cell(row=r, column=COL["quem"],
        value=(f"=IF(${C['v2']}{r}=0,\"\",IF({C['crl']}{r}=\"\",IF({C['crf']}{r}=\"\",\"—\",\"Flávio\"),"
               f"IF({C['crf']}{r}=\"\",\"Lula\",IF({C['crl']}{r}>{C['crf']}{r},\"Lula\","
               f"IF({C['crf']}{r}>{C['crl']}{r},\"Flávio\",\"Igual\")))))"))
for col in range(1, LAST_COL + 1):
    cu = ws.cell(row=r, column=col)
    cu.font = f_bold
    cu.fill = fill_total
    cu.border = borda
    if col >= COL["l1"]:
        cu.alignment = centro
ws.cell(row=r, column=COL["local"]).alignment = esq

# ---- Rodape ----
nr = r + 2
ws.cell(row=nr, column=1,
        value=("Como usar: preencha apenas as células amarelas de cada seção — Lula, Flávio, Brancos e Nulos do 2º turno "
               "(brancos e nulos em colunas separadas; a coluna “Brancos+Nulos (soma)” soma as duas sozinha). "
               "Todos os percentuais e comparações são calculados por fórmula e se atualizam sozinhos. "
               "Válidos = Lula + Flávio (brancos, nulos e os demais candidatos do 1º turno não entram nos válidos). "
               "“Brancos+Nulos %” do 2º turno = (Brancos + Nulos) ÷ (válidos + Brancos + Nulos). "
               "Crescimento % = votos do 2º turno ÷ votos do 1º turno − 1. "
               "As 9 seções marcadas “Agregada à N” não recebem votos próprios: foram incorporadas à seção principal N "
               "(é nela que os votos do TSE aparecem). Só preencha o 2º turno nas seções Principais. "
               "O 1º turno teve também outros candidatos (4.195 votos no município); eles não entram nesta base normalizada."))
ws.cell(row=nr, column=1).font = f_sub
ws.merge_cells(start_row=nr, start_column=1, end_row=nr + 1, end_column=LAST_COL)
ws.cell(row=nr, column=1).alignment = Alignment(wrap_text=True, vertical="top")

# Borda superior da área de digitacao (a partir do 2o turno)
for k in ("l2", "f2", "branco2", "nulo2"):
    ws.cell(row=PRIMEIRA, column=COL[k]).border = Border(
        left=b_thin, right=b_thin, top=Side(style="medium", color="C55A11"), bottom=b_thin)

# ---- Formatacao condicional ----
# 1) Seção onde Lula venceu no 1T (fundo rosado)
rng_sec = f"A{PRIMEIRA}:B{ULTIMA}"
ws.conditional_formatting.add(rng_sec, FormulaRule(formula=[f"${C['pl1']}{PRIMEIRA}>${C['pf1']}{PRIMEIRA}"],
                                                   fill=PatternFill("solid", fgColor="FCE4D6")))
# 2) Crescimento / variacao: verde se positivo, vermelho se negativo
for k in ("varv_pct", "crl", "crf"):
    col = C[k]
    ws.conditional_formatting.add(
        f"{col}{PRIMEIRA}:{col}{ULTIMA}",
        CellIsRule(operator="greaterThan", formula=["0"], font=Font(color="1E7D3C", bold=True)))
    ws.conditional_formatting.add(
        f"{col}{PRIMEIRA}:{col}{ULTIMA}",
        CellIsRule(operator="lessThan", formula=["0"], font=Font(color=VERM, bold=True)))
# 3) Seção que virou no 2T (passou do Flávio para Lula ou vice-versa)
ws.conditional_formatting.add(
    f"A{PRIMEIRA}:B{ULTIMA}",
    FormulaRule(formula=[f"AND(${C['v2']}{PRIMEIRA}>0,(${C['l2']}{PRIMEIRA}>${C['f2']}{PRIMEIRA})<>(${C['l1']}{PRIMEIRA}>${C['f1']}{PRIMEIRA}))"],
                fill=PatternFill("solid", fgColor="FFD966")))

# Validacao: apenas inteiros nao-negativos nas celulas de entrada
dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0",
                    allow_blank=True, showErrorMessage=True,
                    errorTitle="Valor inválido", error="Digite apenas o número de votos (inteiro, sem negativo).")
ws.add_data_validation(dv)
dv.add(f"{C['l2']}{PRIMEIRA}:{C['nulo2']}{ULTIMA}")

ws.freeze_panes = "D6"
ws.auto_filter.ref = f"A5:{_gcl(LAST_COL)}{ULTIMA}"
ws.column_dimensions["A"].width = 7
ws.column_dimensions["B"].width = 36
ws.column_dimensions["C"].width = 16
for i in range(COL["l1"], LAST_COL + 1):
    letra = _gcl(i)
    ws.column_dimensions[letra].width = 9.5
# cabecalhos mais longos
ws.column_dimensions[_gcl(COL["bn2"])].width = 12
ws.column_dimensions[_gcl(COL["quem"])].width = 11
ws.column_dimensions[_gcl(COL["varl"])].width = 11
ws.column_dimensions[_gcl(COL["varf"])].width = 11
ws.column_dimensions[_gcl(COL["varv"])].width = 10
ws.column_dimensions[_gcl(COL["varv_pct"])].width = 10
ws.sheet_view.showGridLines = False
ws.sheet_view.zoomScale = 80

# ================= ABA Resumo =================
ws2 = wb.create_sheet("Resumo")
ws2.sheet_view.showGridLines = False
ws2["A1"] = "Resumo geral — Presidente em Ubatuba/SP"
ws2["A1"].font = f_titulo
ws2.merge_cells("A1:E1")
ws2["A2"] = "Base normalizada: só Lula e Flávio. % dos candidatos = sobre os votos válidos dos dois."
ws2["A2"].font = f_sub
ws2.merge_cells("A2:E2")

lin = PRIMEIRA
resumo = [
    (L("v1"), "1º TURNO", None),
    (L("l1"), "Lula — votos", "#,##0"),
    (L("f1"), "Flávio — votos", "#,##0"),
    (L("v1"), "Votos válidos (Lula + Flávio)", "#,##0"),
    (L("pl1"), "Lula — % dos válidos", "0.00%"),
    (L("pf1"), "Flávio — % dos válidos", "0.00%"),
    (L("bn1"), "Brancos + Nulos (não entram nos válidos)", "#,##0"),
    (L("l2"), "2º TURNO", None),
    (L("l2"), "Lula — votos", "#,##0"),
    (L("f2"), "Flávio — votos", "#,##0"),
    (L("v2"), "Votos válidos (Lula + Flávio)", "#,##0"),
    (L("pl2"), "Lula — % dos válidos", "0.00%"),
    (L("pf2"), "Flávio — % dos válidos", "0.00%"),
    (L("branco2"), "Brancos — votos", "#,##0"),
    (L("nulo2"), "Nulos — votos", "#,##0"),
    (L("bn2"), "Brancos + Nulos (soma)", "#,##0"),
    (L("pbn2"), "Brancos + Nulos — % dos votos dados", "0.00%"),
    (L("varl"), "Lula — variação de votos vs 1º turno", "+#,##0;-#,##0;\"—\""),
    (L("varf"), "Flávio — variação de votos vs 1º turno", "+#,##0;-#,##0;\"—\""),
    (L("crl"), "Lula — crescimento % vs 1º turno", "+0.00%;-0.00%;0.00%"),
    (L("crf"), "Flávio — crescimento % vs 1º turno", "+0.00%;-0.00%;0.00%"),
    ("VAR", "Variação dos votos válidos (em votos)", "+#,##0;-#,##0;\"—\""),
    (L("varv_pct"), "Variação dos votos válidos (%)", "+0.00%;-0.00%;0.00%"),
]
SECOES_2T = (f"COUNT('1T e 2T por Seção'!{L('l2')}{PRIMEIRA}:{L('l2')}{ULTIMA})"
             f"+COUNT('1T e 2T por Seção'!{L('f2')}{PRIMEIRA}:{L('f2')}{ULTIMA})")
COLS_2T = {L("l2"), L("f2"), L("pl2"), L("pf2"), L("v2"), L("branco2"), L("nulo2"),
           L("bn2"), L("pbn2"), L("varl"), L("varf"), L("crl"), L("crf"),
           L("varv"), L("varv_pct")}
r2 = 4
a = ws2.cell(row=r2, column=1, value="Seções cadastradas")
a.alignment = esq
a.border = borda
b = ws2.cell(row=r2, column=2,
             value=f"=COUNTA('1T e 2T por Seção'!A{PRIMEIRA}:A{ULTIMA})")
b.number_format = "0"
b.alignment = centro
b.font = f_bold
b.border = borda
a2 = ws2.cell(row=5, column=1, value="  — Principais (recebem votos)")
a2.alignment = esq
a2.border = borda
b2 = ws2.cell(row=5, column=2,
              value=f"=COUNTIF('1T e 2T por Seção'!{L('sit')}{PRIMEIRA}:{L('sit')}{ULTIMA},\"Principal\")")
b2.number_format = "0"
b2.alignment = centro
b2.font = f_bold
b2.border = borda
a3 = ws2.cell(row=6, column=1, value="  — Agregadas (sem voto próprio)")
a3.alignment = esq
a3.border = borda
b3 = ws2.cell(row=6, column=2,
              value=f"=COUNTIF('1T e 2T por Seção'!{L('sit')}{PRIMEIRA}:{L('sit')}{ULTIMA},\"Agregada*\")")
b3.number_format = "0"
b3.alignment = centro
b3.font = f_bold
b3.border = borda
r2 = 8
for col, rot, fmt in resumo:
    a = ws2.cell(row=r2, column=1, value=rot)
    if fmt is None:
        f_marca = PatternFill("solid", fgColor=CINZA_T if col == L("v1") else "C55A11")
        a.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        a.fill = f_marca
        a.alignment = esq
        ws2.merge_cells(start_row=r2, start_column=1, end_row=r2, end_column=2)
        ws2.cell(row=r2, column=2).fill = f_marca
        r2 += 1
        continue
    a.alignment = esq
    # Linhas do 2o turno ficam vazias enquanto nao houver nenhum voto digitado
    if col == "VAR":
        formula = ("=IF(%s=0,\"\",IF('1T e 2T por Seção'!%s%d=0,\"\","
                   "'1T e 2T por Seção'!%s%d-'1T e 2T por Seção'!%s%d))"
                   % (SECOES_2T, L("v2"), TOTAL_ROW, L("v2"), TOTAL_ROW, L("v1"), TOTAL_ROW))
    else:
        ref = f"'1T e 2T por Seção'!{col}{TOTAL_ROW}"
        if col in COLS_2T:
            formula = f"=IF({SECOES_2T}=0,\"\",IF({ref}=\"\",\"\",{ref}))"
        else:
            formula = ref
    b = ws2.cell(row=r2, column=2, value=formula)
    b.number_format = fmt
    b.alignment = centro
    b.font = f_bold
    for c in (a, b):
        c.border = borda
    r2 += 1

r2 += 1
ws2.cell(row=r2, column=1, value=("Este resumo usa fórmulas ligadas à aba “1T e 2T por Seção”: basta digitar os votos do 2º turno "
                                  "lá e os totais se atualizam aqui."))
ws2.cell(row=r2, column=1).font = f_sub
ws2.merge_cells(start_row=r2, start_column=1, end_row=r2 + 1, end_column=3)
ws2.cell(row=r2, column=1).alignment = Alignment(wrap_text=True, vertical="top")
ws2.column_dimensions["A"].width = 44
ws2.column_dimensions["B"].width = 16

# ================= ABA Comparativo por local =================
ws3 = wb.create_sheet("Comparativo por Local")
ws3.sheet_view.showGridLines = False
ws3["A1"] = "Comparativo 2º turno × 1º turno por local de votação — Ubatuba/SP"
ws3["A1"].font = f_titulo
ws3.merge_cells("A1:O1")

# A Local | B Secoes | C Lula1T | D Flavio1T | E B+N 1T | F Validos1T
# G Lula2T | H Flavio2T | I Brancos2T | J Nulos2T | K B+N 2T (soma) | L Validos2T
# M Var validos % | N Cresc Lula % | O Cresc Flavio %
hdr3 = ["Local de votação", "Seções", "1T Lula", "1T Flávio", "1T B+N", "1T válidos",
        "2T Lula", "2T Flávio", "2T Brancos", "2T Nulos", "2T B+N (soma)", "2T válidos",
        "Var. válidos %", "Cresc. Lula %", "Cresc. Flávio %"]
for i, h in enumerate(hdr3, start=1):
    c = ws3.cell(row=3, column=i, value=h)
    c.font = f_hdr
    c.fill = fill_cmp if i > 6 else fill_1t
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = borda
ws3.row_dimensions[3].height = 30

chave = f"$B${PRIMEIRA}:$B${ULTIMA}"
SHEET1 = "'1T e 2T por Seção'"


def sif(letra, nome):
    """SUMIF por local; as colunas do 2o turno ficam vazias se nada foi digitado no local."""
    rng = f"{SHEET1}!${letra}${PRIMEIRA}:${letra}${ULTIMA}"
    if letra in (L("l2"), L("f2"), L("branco2"), L("nulo2")):
        cond = f"COUNTIFS({SHEET1}!{chave},\"{nome.upper()}\",{rng},\">=0\")=0"
        return f"=IF({cond},\"\",SUMIF({SHEET1}!{chave},\"{nome.upper()}\",{rng}))"
    return f"=SUMIF({SHEET1}!{chave},\"{nome.upper()}\",{rng})"


locais = (d.groupby("local").agg(secoes=("secao", "count")).reset_index().sort_values("local"))
r3 = 4
for _, Lx in locais.iterrows():
    nome = str(Lx["local"])
    ws3.cell(row=r3, column=1, value=nome.title()).alignment = esq
    ws3.cell(row=r3, column=2, value=f"=COUNTIF({SHEET1}!{chave},\"{nome.upper()}\")").number_format = "0"
    ws3.cell(row=r3, column=3, value=sif(L("l1"), nome)).number_format = "#,##0"   # 1T Lula
    ws3.cell(row=r3, column=4, value=sif(L("f1"), nome)).number_format = "#,##0"   # 1T Flavio
    ws3.cell(row=r3, column=5, value=sif(L("bn1"), nome)).number_format = "#,##0"   # 1T B+N
    ws3.cell(row=r3, column=6, value=f"=C{r3}+D{r3}").number_format = "#,##0"
    ws3.cell(row=r3, column=7, value=sif(L("l2"), nome)).number_format = "#,##0"    # 2T Lula
    ws3.cell(row=r3, column=8, value=sif(L("f2"), nome)).number_format = "#,##0"    # 2T Flavio
    ws3.cell(row=r3, column=9, value=sif(L("branco2"), nome)).number_format = "#,##0"    # 2T Brancos
    ws3.cell(row=r3, column=10, value=sif(L("nulo2"), nome)).number_format = "#,##0"   # 2T Nulos
    ws3.cell(row=r3, column=11, value=f"=N(I{r3})+N(J{r3})").number_format = "#,##0"
    ws3.cell(row=r3, column=12, value=f"=N(G{r3})+N(H{r3})").number_format = "#,##0"
    ws3.cell(row=r3, column=13, value=f"=IF(OR(F{r3}=0,N(L{r3})=0),\"\",N(L{r3})/F{r3}-1)").number_format = "+0.00%;-0.00%;0.00%"
    ws3.cell(row=r3, column=14, value=f"=IF(OR(C{r3}=0,N(G{r3})=0),\"\",N(G{r3})/C{r3}-1)").number_format = "+0.00%;-0.00%;0.00%"
    ws3.cell(row=r3, column=15, value=f"=IF(OR(D{r3}=0,N(H{r3})=0),\"\",N(H{r3})/D{r3}-1)").number_format = "+0.00%;-0.00%;0.00%"
    for col in range(1, 16):
        cu = ws3.cell(row=r3, column=col)
        cu.border = borda
        if col >= 2:
            cu.alignment = centro
    r3 += 1

ws3.cell(row=r3, column=1, value="TOTAL").font = f_bold
for col in range(2, 13):
    letter = get_column_letter(col)
    if col in (7, 8, 9, 10, 11):   # colunas 2T: vazias se nada digitado
        cell = ws3.cell(row=r3, column=col,
                        value=f"=IF(COUNT({letter}4:{letter}{r3-1})=0,\"\",SUM({letter}4:{letter}{r3-1}))")
    else:
        cell = ws3.cell(row=r3, column=col, value=f"=SUM({letter}4:{letter}{r3-1})")
    cell.number_format = "#,##0"
ws3.cell(row=r3, column=13, value=f"=IF(OR(F{r3}=0,N(L{r3})=0),\"\",N(L{r3})/F{r3}-1)").number_format = "+0.00%;-0.00%;0.00%"
ws3.cell(row=r3, column=14, value=f"=IF(OR(C{r3}=0,N(G{r3})=0),\"\",N(G{r3})/C{r3}-1)").number_format = "+0.00%;-0.00%;0.00%"
ws3.cell(row=r3, column=15, value=f"=IF(OR(D{r3}=0,N(H{r3})=0),\"\",N(H{r3})/D{r3}-1)").number_format = "+0.00%;-0.00%;0.00%"
for col in range(1, 16):
    cu = ws3.cell(row=r3, column=col)
    cu.font = f_bold
    cu.fill = fill_total
    cu.border = borda
    if col >= 2:
        cu.alignment = centro

for col in ("M", "N", "O"):
    ws3.conditional_formatting.add(f"{col}4:{col}{r3-1}",
        CellIsRule(operator="greaterThan", formula=["0"], font=Font(color="1E7D3C", bold=True)))
    ws3.conditional_formatting.add(f"{col}4:{col}{r3-1}",
        CellIsRule(operator="lessThan", formula=["0"], font=Font(color=VERM, bold=True)))
ws3.auto_filter.ref = f"A3:O{r3-1}"
ws3.column_dimensions["A"].width = 40
for col in "BCDEFGHIJKLMNO":
    ws3.column_dimensions[col].width = 11
ws3.column_dimensions["K"].width = 13

wb.save(SAIDA)
print("\nSalvo:", SAIDA)
