import os

EXTENSIONS = {".py", ".js", ".json", ".md"}
API_DIR = "api"
OUTPUT = "0api.md"

def bloco(filepath):
    ext = os.path.splitext(filepath)[1].lstrip(".")
    with open(filepath, encoding="utf-8") as f:
        conteudo = f.read()
    return f"## {filepath}\n```{ext}\n{conteudo}\n```\n\n"

def main():
    arquivos = []
    for file in sorted(os.listdir(API_DIR)):
        if any(file.endswith(ext) for ext in EXTENSIONS):
            arquivos.append(os.path.join(API_DIR, file))
    with open(OUTPUT, "w", encoding="utf-8") as out:
        for filepath in arquivos:
            try:
                out.write(bloco(filepath))
            except Exception as e:
                print(f"⚠️  Erro ao ler {filepath}: {e}")
    print(f"✅ Exportado: {OUTPUT} ({len(arquivos)} arquivos)")

if __name__ == "__main__":
    main()
