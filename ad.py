#!/usr/bin/env python3
"""
ad.py - Consolida o conteúdo de:
- Script/pjetools.user.js
- Script/modules/Aud/Aud.core.js
- Script/modules/Aud/Aud.data.js
em aud.md na raiz do projeto.
"""
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    files = [
        ("pjetools.user.js", root / "Script" / "pjetools.user.js", "javascript"),
        ("Aud.core.js", root / "Script" / "modules" / "Aud" / "Aud.core.js", "javascript"),
        ("Aud.data.js", root / "Script" / "modules" / "Aud" / "Aud.data.js", "javascript"),
    ]

    out_lines = ["# AUD - Arquivos Consolidados\n"]
    for name, file_path, lang in files:
        if not file_path.exists():
            print(f"[Aviso] Arquivo não encontrado: {file_path}")
            continue
        content = file_path.read_text(encoding="utf-8")
        out_lines.append(f"## {name}\n")
        out_lines.append(f"```{lang}\n{content}\n```\n")

    out_file = root / "aud.md"
    out_file.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"[OK] aud.md gerado com sucesso em: {out_file} ({out_file.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
