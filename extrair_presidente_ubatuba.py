"""Extrai e analisa a votação de presidente (1º turno 2026) em Ubatuba-SP, por seção eleitoral."""
import zipfile
import pandas as pd

DIR = r"D:\PjePlus\dados_tse_2026"
COD_UBATUBA = "72095"

cols = ["SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "CD_CARGO",
        "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS", "NR_LOCAL_VOTACAO",
        "NM_LOCAL_VOTACAO", "DS_LOCAL_VOTACAO_ENDERECO"]

partes = []
with zipfile.ZipFile(f"{DIR}\\votacao_secao_2026_BR.zip") as z:
    nome = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    with z.open(nome) as f:
        for chunk in pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, usecols=cols,
                                 chunksize=1_000_000):
            sub = chunk[chunk["CD_MUNICIPIO"] == COD_UBATUBA]
            if len(sub):
                partes.append(sub)

p = pd.concat(partes, ignore_index=True)
p["NR_VOTAVEL"] = p["NR_VOTAVEL"].astype(int)
p["QT_VOTOS"] = p["QT_VOTOS"].astype(int)
p["NR_ZONA"] = p["NR_ZONA"].astype(int)
p["NR_SECAO"] = p["NR_SECAO"].astype(int)
p["NR_LOCAL_VOTACAO"] = p["NR_LOCAL_VOTACAO"].astype(int)
print("linhas Ubatuba:", len(p))
print("UF:", p["SG_UF"].unique(), "municipio:", p["NM_MUNICIPIO"].unique())
print("cargos:", p["CD_CARGO"].unique(), "turnos ok")

print("\n== Totais por votavel ==")
t = p.groupby(["NR_VOTAVEL", "NM_VOTAVEL"])["QT_VOTOS"].sum().reset_index().sort_values("NR_VOTAVEL")
t["%"] = (t["QT_VOTOS"] / t["QT_VOTOS"].sum() * 100).round(2)
print(t.to_string(index=False))
print("TOTAL votos (todos):", t["QT_VOTOS"].sum())
print("TOTAL Lula+Flavio:", t[t["NR_VOTAVEL"].isin([13, 22])]["QT_VOTOS"].sum())

print("\nsecoes:", p["NR_SECAO"].nunique(), "| locais:", p["NR_LOCAL_VOTACAO"].nunique(),
      "| zonas:", p["NR_ZONA"].unique())
# secoes com area (secao 1000+ = exterior? nao para municipio) - checar local unico por secao
loc_por_secao = p.groupby("NR_SECAO")["NR_LOCAL_VOTACAO"].nunique()
print("secoes com >1 local:", (loc_por_secao > 1).sum())
print("secoes com >1 nome/local:", p.groupby("NR_SECAO")["NM_LOCAL_VOTACAO"].nunique().max())

p.to_pickle(f"{DIR}\\ubatuba_presidente.pkl")
