import os, json, hashlib, re

EXTENSIONS   = {".py", ".js", ".json", ".md"}
INCLUIR      = {"x.py", "f.py", ".vscode", "PEC", "atos", "Mandado", "Fix", "Prazo", "Sisb", "maispje", "Ref"}
INCLUIR_NORM = {i.lower() for i in INCLUIR}
HASH_FILE    = ".export_hashes.json"
OUTPUT       = "00dump.md"

# Pastebin integration removed — uploads disabled

def hash_file(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()

def deve_incluir(path):
    partes = path.replace("\\", "/").lstrip("./").split("/")
    return partes[0].lower() in INCLUIR_NORM

def coletar_arquivos():
    resultado = {}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith("__") and d != ".git"]
        for file in sorted(files):
            if not any(file.endswith(ext) for ext in EXTENSIONS):
                continue
            filepath = os.path.join(root, file).replace("\\", "/").lstrip("./")
            if deve_incluir(filepath):
                resultado[filepath] = hash_file(os.path.join(root, file))
    return resultado

def bloco(filepath):
    ext = os.path.splitext(filepath)[1].lstrip(".")
    conteudo = open(filepath, encoding="utf-8").read()
    return f"## {filepath}\n```{ext}\n{conteudo}\n```\n\n"

# push_pastebin removed — external upload disabled

# _get_user_key removed

# ── execução ──────────────────────────────────────────────────────────────────

hashes_antigos = json.load(open(HASH_FILE)) if os.path.exists(HASH_FILE) else {}
hashes_novos   = coletar_arquivos()

alterados = [f for f, h in hashes_novos.items() if hashes_antigos.get(f) != h]
removidos = [f for f in hashes_antigos if f not in hashes_novos]

if not alterados and not removidos and os.path.exists(OUTPUT):
    print("✅ Sem alterações.")
else:
    with open(OUTPUT, "w", encoding="utf-8") as out:
        for filepath in hashes_novos:
            try:
                out.write(bloco(filepath))
            except Exception as e:
                print(f"⚠️  Erro ao ler {filepath}: {e}")
    motivo = "Criado" if not hashes_antigos else f"Atualizado ({len(alterados)} alterado(s), {len(removidos)} removido(s))"
    print(f"✅ {motivo}: {OUTPUT} ({len(hashes_novos)} arquivos)")

json.dump(hashes_novos, open(HASH_FILE, "w"), indent=2)