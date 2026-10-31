"""Gera a planilha consolidada Lula x Flávio por seção eleitoral - Ubatuba-SP, 1º turno 2026."""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

DIR = r"D:\PjePlus\dados_tse_2026"
SAIDA = r"D:\PjePlus\Ubatuba_2026_1turno_Presidente_Lula_x_Flavio.xlsx"

p = pd.read_pickle(f"{DIR}\\ubatuba_presidente.pkl")

# ---- Base por seção ----
g = p.groupby(["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO",
               "DS_LOCAL_VOTACAO_ENDERECO"])

def soma_secao(df, votavel):
    return df[df["NR_VOTAVEL"] == votavel]["QT_VOTOS"].sum()

linhas = []
for chave, df in g:
    zona, secao, cod_loc, nm_loc, end_loc = chave
    v13 = soma_secao(df, 13)
    v22 = soma_secao(df, 22)
    brancos = soma_secao(df, 95)
    nulos = soma_secao(df, 96)
    outros = df[~df["NR_VOTAVEL"].isin([13, 22, 95, 96])]["QT_VOTOS"].sum()
    total = df["QT_VOTOS"].sum()
    linhas.append({
        "zona": int(zona), "secao": int(secao), "cod_local": int(cod_loc),
        "local": nm_loc, "endereco": end_loc,
        "lula": int(v13), "flavio": int(v22),
        "brancos": int(brancos), "nulos": int(nulos), "outros": int(outros),
        "total": int(total),
    })

d = pd.DataFrame(linhas).sort_values("secao").reset_index(drop=True)
assert (d["lula"] + d["flavio"] + d["brancos"] + d["nulos"] + d["outros"] == d["total"]).all()

d["validos"] = d["lula"] + d["flavio"]
d["pct_lula"] = (d["lula"] / d["validos"]).fillna(0)
d["pct_flavio"] = (d["flavio"] / d["validos"]).fillna(0)
d["pct_lula_total"] = d["lula"] / d["total"]
d["pct_flavio_total"] = d["flavio"] / d["total"]
d["vantagem"] = d["flavio"] - d["lula"]
d["vencedor"] = ["Flávio" if f > l else ("Lula" if l > f else "Empate")
                 for l, f in zip(d["lula"], d["flavio"])]

print(d[["secao", "lula", "flavio", "validos", "pct_lula", "pct_flavio"]].head(10).to_string())
print("\nTOTAIS: lula", d["lula"].sum(), "flavio", d["flavio"].sum(),
      "validos", d["validos"].sum(), "brancos", d["brancos"].sum(),
      "nulos", d["nulos"].sum(), "outros", d["outros"].sum(), "total", d["total"].sum())

# ---- Estilos ----
AZUL = "1F4E79"; VERDE = "1E7D3C"; VERM = "B3261E"; CINZA = "F2F2F2"
f_titulo = Font(name="Calibri", size=16, bold=True, color=AZUL)
f_sub = Font(name="Calibri", size=10, italic=True, color="595959")
f_hdr = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
f_hdr_l = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
f_bold = Font(name="Calibri", size=11, bold=True)
f_borda_med = Side(style="thin", color="BFBFBF")
borda = Border(left=f_borda_med, right=f_borda_med, top=f_borda_med, bottom=f_borda_med)
fill_hdr = PatternFill("solid", fgColor=AZUL)
fill_lula = PatternFill("solid", fgColor="C00000")
fill_flavio = PatternFill("solid", fgColor="1F4E79")
fill_total = PatternFill("solid", fgColor="DDEBF7")
fill_titulo = PatternFill("solid", fgColor="D9E1F2")
centro = Alignment(horizontal="center", vertical="center")
esq = Alignment(horizontal="left", vertical="center")

wb = Workbook()

# ================= ABA 1: Consolidado por seção =================
ws = wb.active
ws.title = "Consolidado por Seção"

ws["A1"] = "Eleições 2026 — 1º Turno — Presidente da República"
ws["A1"].font = f_titulo
ws.merge_cells("A1:J1")
ws["A2"] = ("Município: Ubatuba/SP (IBGE 72095) • Zona Eleitoral 144 • 238 seções • "
            "Data da eleição: 04/10/2026 • Fonte: TSE — Dados Abertos (votacao_secao_2026_BR)")
ws["A2"].font = f_sub
ws.merge_cells("A2:J2")
ws.row_dimensions[1].height = 24

# Cabeçalho de grupos
ws["A4"] = "Seção"
ws.merge_cells("A4:B4")
ws["C4"] = "LULA (13) — PT"
ws.merge_cells("C4:E4")
ws["F4"] = "FLÁVIO BOLSONARO (22) — PL"
ws.merge_cells("F4:H4")
ws["I4"] = "Total de votos na seção (Lula + Flávio)"
ws.merge_cells("I4:K4")
for col, fill in [("A", fill_hdr), ("C", fill_lula), ("F", fill_flavio), ("I", fill_hdr)]:
    for c in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
        pass
for rng, fill in [("A4:B4", fill_hdr), ("C4:E4", fill_lula), ("F4:H4", fill_flavio), ("I4:K4", fill_hdr)]:
    for row in ws[rng]:
        for c in row:
            c.fill = fill
            c.font = f_hdr
            c.alignment = centro

hdr = ["Nº", "Local de votação", "Votos", "% dos 2", "% do total",
       "Votos", "% dos 2", "% do total", "Votos válidos (2)", "Brancos + Nulos", "Vantagem de Flávio"]
ws.append([])  # linha 5 vazia -> vamos escrever na 5
for i, h in enumerate(hdr, start=1):
    c = ws.cell(row=5, column=i, value=h)
    c.font = f_hdr
    c.fill = fill_lula if 3 <= i <= 5 else (fill_flavio if 6 <= i <= 8 else fill_hdr)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = borda
ws.row_dimensions[5].height = 32

r = 6
for _, x in d.iterrows():
    ws.cell(row=r, column=1, value=int(x["secao"])).alignment = centro
    c = ws.cell(row=r, column=2, value=str(x["local"]).title())
    c.alignment = esq
    ws.cell(row=r, column=3, value=int(x["lula"])).number_format = "#,##0"
    ws.cell(row=r, column=4, value=float(x["pct_lula"])).number_format = "0.00%"
    ws.cell(row=r, column=5, value=float(x["pct_lula_total"])).number_format = "0.00%"
    ws.cell(row=r, column=6, value=int(x["flavio"])).number_format = "#,##0"
    ws.cell(row=r, column=7, value=float(x["pct_flavio"])).number_format = "0.00%"
    ws.cell(row=r, column=8, value=float(x["pct_flavio_total"])).number_format = "0.00%"
    ws.cell(row=r, column=9, value=int(x["validos"])).number_format = "#,##0"
    ws.cell(row=r, column=10, value=int(x["brancos"] + x["nulos"])).number_format = "#,##0"
    c = ws.cell(row=r, column=11, value=int(x["vantagem"]))
    c.number_format = "+#,##0;-#,##0;0"
    c.font = Font(color=VERDE if x["vantagem"] > 0 else VERM, bold=True)
    for col in range(1, 12):
        cc = ws.cell(row=r, column=col)
        cc.border = borda
        if col >= 3:
            cc.alignment = centro
    r += 1

ultima = r - 1
# Linha de total
ws.cell(row=r, column=1, value="")
ws.cell(row=r, column=2, value="TOTAL UBATUBA")
tot = d[["lula", "flavio", "validos", "brancos", "nulos", "vantagem"]].sum()
pct_l = tot["lula"] / tot["validos"]; pct_f = tot["flavio"] / tot["validos"]
tt = d["total"].sum()
ws.cell(row=r, column=3, value=int(tot["lula"]))
ws.cell(row=r, column=4, value=float(pct_l)).number_format = "0.00%"
ws.cell(row=r, column=5, value=float(tot["lula"] / tt)).number_format = "0.00%"
ws.cell(row=r, column=6, value=int(tot["flavio"]))
ws.cell(row=r, column=7, value=float(pct_f)).number_format = "0.00%"
ws.cell(row=r, column=8, value=float(tot["flavio"] / tt)).number_format = "0.00%"
ws.cell(row=r, column=9, value=int(tot["validos"]))
ws.cell(row=r, column=10, value=int(tot["brancos"] + tot["nulos"]))
ws.cell(row=r, column=11, value=int(tot["vantagem"]))
for col in range(1, 12):
    c = ws.cell(row=r, column=col)
    c.font = f_bold
    c.fill = fill_total
    c.border = borda
    if col >= 3:
        c.number_format = c.number_format or "#,##0"
        c.alignment = centro
ws.cell(row=r, column=2).alignment = esq
ws.cell(row=r, column=3).number_format = "#,##0"
ws.cell(row=r, column=6).number_format = "#,##0"
ws.cell(row=r, column=9).number_format = "#,##0"
ws.cell(row=r, column=10).number_format = "#,##0"
ws.cell(row=r, column=11).number_format = "+#,##0;-#,##0;0"

# Nota de rodapé
nota_r = r + 2
ws.cell(row=nota_r, column=1,
        value=("Notas: “% dos 2” = percentual sobre os votos válidos apenas de Lula e Flávio. "
               "“% do total” = percentual sobre todos os votos da seção (inclui os demais candidatos, brancos e nulos). "
               "Seções sem voto em um candidato aparecem com 0. Abstenções e comparecimento não estão incluídos."))
ws.cell(row=nota_r, column=1).font = f_sub
ws.merge_cells(start_row=nota_r, start_column=1, end_row=nota_r, end_column=11)

ws.freeze_panes = "C6"
ws.auto_filter.ref = f"A5:K{ultima}"
ws.column_dimensions["A"].width = 7
ws.column_dimensions["B"].width = 42
for col in ["C", "D", "E", "F", "G", "H", "I", "J"]:
    ws.column_dimensions[col].width = 11
ws.column_dimensions["K"].width = 15
ws.sheet_view.showGridLines = False

# Formatação condicional: destaca seção em que Lula venceu
from openpyxl.formatting.rule import FormulaRule
verde_claro = PatternFill("solid", fgColor="FFF2CC")
ws.conditional_formatting.add(
    f"A6:B{ultima}",
    FormulaRule(formula=[f"$C6>$F6"], fill=PatternFill("solid", fgColor="FCE4D6"))
)

# ================= ABA 2: Resumo =================
ws2 = wb.create_sheet("Resumo")
ws2.sheet_view.showGridLines = False
ws2["A1"] = "Resumo — Ubatuba/SP — Presidente — 1º Turno 2026"
ws2["A1"].font = f_titulo
ws2.merge_cells("A1:D1")

resumo = [
    ("Total de seções eleitorais", d.shape[0], "0"),
    ("Locais de votação", d["cod_local"].nunique(), "0"),
    ("", None, ""),
    ("Votos válidos (Lula + Flávio)", int(tot["validos"]), "#,##0"),
    ("Demais candidatos", int(d["outros"].sum()), "#,##0"),
    ("Brancos", int(d["brancos"].sum()), "#,##0"),
    ("Nulos", int(d["nulos"].sum()), "#,##0"),
    ("TOTAL de votos apurados", int(tt), "#,##0"),
    ("", None, ""),
    ("LULA — votos", int(tot["lula"]), "#,##0"),
    ("LULA — % válidos (2 candidatos)", float(pct_l), "0.00%"),
    ("LULA — seções em que venceu", int((d["lula"] > d["flavio"]).sum()), "0"),
    ("", None, ""),
    ("FLÁVIO BOLSONARO — votos", int(tot["flavio"]), "#,##0"),
    ("FLÁVIO BOLSONARO — % válidos (2 candidatos)", float(pct_f), "0.00%"),
    ("FLÁVIO BOLSONARO — seções em que venceu", int((d["flavio"] > d["lula"]).sum()), "0"),
    ("", None, ""),
    ("Vantagem de Flávio (votos)", int(tot["vantagem"]), "+#,##0;-#,##0;0"),
    ("Maior votação de Flávio numa seção", int(d["flavio"].max()), "#,##0"),
    ("Maior votação de Lula numa seção", int(d["lula"].max()), "#,##0"),
]
r2 = 3
for rot, val, fmt in resumo:
    if rot == "":
        r2 += 1
        continue
    a = ws2.cell(row=r2, column=1, value=rot)
    a.font = f_bold if val is not None else Font()
    a.alignment = esq
    b = ws2.cell(row=r2, column=2, value=val)
    b.number_format = fmt
    b.alignment = centro
    b.font = f_bold
    for c in (a, b):
        c.border = borda
    r2 += 1

ws2["A24"] = ("Fonte: Tribunal Superior Eleitoral — Portal de Dados Abertos. "
              "Arquivo: votacao_secao_2026_BR.zip (presidente, 1º turno). Consulta em 24/10/2026.")
ws2["A24"].font = f_sub
ws2.merge_cells("A24:D25")
ws2["A24"].alignment = Alignment(wrap_text=True, vertical="top")
ws2.column_dimensions["A"].width = 46
ws2.column_dimensions["B"].width = 18

# ================= ABA 3: Por local de votação =================
ws3 = wb.create_sheet("Por Local de Votação")
ws3.sheet_view.showGridLines = False
ws3["A1"] = "Consolidado por local de votação — Ubatuba/SP — Presidente — 1º Turno 2026"
ws3["A1"].font = f_titulo
ws3.merge_cells("A1:G1")

loc = (d.groupby(["cod_local", "local", "endereco"])
        .agg(secoes=("secao", "count"), lula=("lula", "sum"), flavio=("flavio", "sum"),
             validos=("validos", "sum"), brancos_nulos=("brancos", "sum"))
        .reset_index())
loc["brancos_nulos"] = d.groupby("cod_local")["brancos"].sum().values + d.groupby("cod_local")["nulos"].sum().values
loc["pct_lula"] = loc["lula"] / loc["validos"]
loc["pct_flavio"] = loc["flavio"] / loc["validos"]
loc = loc.sort_values("flavio", ascending=False)

h2 = ["Local de votação", "Endereço", "Seções", "Lula (13)", "% Lula", "Flávio (22)", "% Flávio", "Válidos"]
for i, h in enumerate(h2, start=1):
    c = ws3.cell(row=3, column=i, value=h)
    c.font = f_hdr
    c.fill = fill_hdr
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = borda
ws3.row_dimensions[3].height = 28

r3 = 4
for _, x in loc.iterrows():
    ws3.cell(row=r3, column=1, value=str(x["local"]).title()).alignment = esq
    ws3.cell(row=r3, column=2, value=str(x["endereco"]).title()).alignment = esq
    ws3.cell(row=r3, column=3, value=int(x["secoes"])).alignment = centro
    ws3.cell(row=r3, column=4, value=int(x["lula"])).number_format = "#,##0"
    ws3.cell(row=r3, column=5, value=float(x["pct_lula"])).number_format = "0.00%"
    ws3.cell(row=r3, column=6, value=int(x["flavio"])).number_format = "#,##0"
    ws3.cell(row=r3, column=7, value=float(x["pct_flavio"])).number_format = "0.00%"
    ws3.cell(row=r3, column=8, value=int(x["validos"])).number_format = "#,##0"
    for col in range(1, 9):
        cc = ws3.cell(row=r3, column=col)
        cc.border = borda
        if col >= 3:
            cc.alignment = centro
    r3 += 1

ws3.cell(row=r3, column=1, value="TOTAL").font = f_bold
ws3.cell(row=r3, column=3, value=int(loc["secoes"].sum()))
ws3.cell(row=r3, column=4, value=int(loc["lula"].sum())).number_format = "#,##0"
ws3.cell(row=r3, column=5, value=float(tot["lula"] / tot["validos"])).number_format = "0.00%"
ws3.cell(row=r3, column=6, value=int(loc["flavio"].sum())).number_format = "#,##0"
ws3.cell(row=r3, column=7, value=float(tot["flavio"] / tot["validos"])).number_format = "0.00%"
ws3.cell(row=r3, column=8, value=int(loc["validos"].sum())).number_format = "#,##0"
for col in range(1, 9):
    c = ws3.cell(row=r3, column=col)
    c.font = f_bold
    c.fill = fill_total
    c.border = borda
    if col >= 3:
        c.alignment = centro

ws3.freeze_panes = "A4"
ws3.auto_filter.ref = f"A3:H{r3-1}"
ws3.column_dimensions["A"].width = 40
ws3.column_dimensions["B"].width = 44
for col in ["C", "D", "E", "F", "G", "H"]:
    ws3.column_dimensions[col].width = 11

wb.save(SAIDA)
print("\nSalvo:", SAIDA)

# ---- Verificação ----
from openpyxl import load_workbook
wb2 = load_workbook(SAIDA)
print("abas:", wb2.sheetnames)
w = wb2["Consolidado por Seção"]
print("dimensoes:", w.dimensions)
print("primeira secao:", w.cell(row=6, column=1).value, "| ultima:", w.cell(row=5 + d.shape[0], column=1).value)
print("total linha:", w.cell(row=6 + d.shape[0], column=2).value,
      w.cell(row=6 + d.shape[0], column=3).value, w.cell(row=6 + d.shape[0], column=6).value)
