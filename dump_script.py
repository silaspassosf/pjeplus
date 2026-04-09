#!/usr/bin/env python3
"""
Extrai todo o conteúdo do diretório `Script/` do projeto
e grava em `00dump_Script.md`. Baseado em dump.py, porém
limitado apenas à pasta Script.
"""
import os
import json
import hashlib

DIRECTORY = "Script"
HASH_FILE = ".export_hashes_script.json"
OUTPUT = "00dump_Script.md"

EXTENSIONS = None  # aceitar todas as extensões dentro de Script/

def hash_file(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def coletar_arquivos():
    resultado = {}
    base = os.path.join(".", DIRECTORY)
    if not os.path.exists(base):
        return resultado
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith("__") and d != ".git"]
        for file in sorted(files):
            filepath = os.path.join(root, file).replace("\\", "/").lstrip("./")
            resultado[filepath] = hash_file(os.path.join(root, file))
    return resultado

def bloco(filepath):
    ext = os.path.splitext(filepath)[1].lstrip(".")
    try:
        conteudo = open(filepath, encoding="utf-8").read()
    except Exception as e:
        return f"## {filepath}\n```{ext}\n⚠️ Erro ao ler: {e}\n```\n\n"
    return f"## {filepath}\n```{ext}\n{conteudo}\n```\n\n"

def main():
    hashes_antigos = json.load(open(HASH_FILE)) if os.path.exists(HASH_FILE) else {}
    hashes_novos = coletar_arquivos()

    alterados = [f for f, h in hashes_novos.items() if hashes_antigos.get(f) != h]
    removidos = [f for f in hashes_antigos if f not in hashes_novos]

    if not hashes_novos:
        print(f"⚠️  Diretório '{DIRECTORY}' não encontrado ou vazio.")
        return

    if not alterados and not removidos and os.path.exists(OUTPUT):
        print("✅ Sem alterações.")
    else:
        with open(OUTPUT, "w", encoding="utf-8") as out:
            for filepath in sorted(hashes_novos):
                try:
                    out.write(bloco(filepath))
                except Exception as e:
                    print(f"⚠️  Erro ao processar {filepath}: {e}")
        motivo = "Criado" if not hashes_antigos else f"Atualizado ({len(alterados)} alterado(s), {len(removidos)} removido(s))"
        print(f"✅ {motivo}: {OUTPUT} ({len(hashes_novos)} arquivos)")

    json.dump(hashes_novos, open(HASH_FILE, "w"), indent=2)

if __name__ == '__main__':
    main()
