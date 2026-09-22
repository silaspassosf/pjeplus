"""
Xcode Dump Tool — Extrai funcoes Python e popula bug.md com dumps formatados.

Uso:
    py tools/xcode_dump.py --config dump_config.json --output bug.md

Formato do dump_config.json:
{
    "targets": [
        {
            "file": "SISB/helpers.py",
            "function": "_parse_linha_bloqueio",
            "line": 415,
            "relevance": "Contem a falha — regex nao captura notacao brasileira",
            "callers": ["SISB/helpers.py:extrair_dados_bloqueios_processados()"],
            "callees": []
        },
        ...
    ]
}

A saida e appendada ao bug.md existente, substituindo o placeholder:
    ## 5. Dump de Funcoes
    *(a preencher na Fase B)*
"""

import argparse
import json
import re
import sys
from pathlib import Path


def find_function_boundaries(file_path: str, func_name: str, hint_line: int) -> tuple[int, int] | None:
    """Encontra as linhas exatas de inicio e fim de uma funcao Python.

    Retorna (linha_inicio, linha_fim) 1-indexed ou None se nao encontrar.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"  [!] Arquivo nao encontrado: {file_path}", file=sys.stderr)
        return None

    lines = path.read_text(encoding="utf-8").splitlines()

    # 1. Encontrar a linha do def
    pattern = re.compile(rf"^\s*def\s+{re.escape(func_name)}\s*\(")
    def_line = None
    start_search = max(0, hint_line - 10)

    for i in range(start_search, len(lines)):
        if pattern.match(lines[i]):
            def_line = i + 1  # 1-indexed
            break

    if def_line is None:
        # fallback: search whole file
        for i, line in enumerate(lines):
            if pattern.match(line):
                def_line = i + 1
                break

    if def_line is None:
        print(f"  [!] Funcao '{func_name}' nao encontrada em {file_path}", file=sys.stderr)
        return None

    # 2. Determinar indentacao da funcao
    def_indent = len(lines[def_line - 1]) - len(lines[def_line - 1].lstrip())

    # 3. Encontrar fim: proxima linha com indentacao <= def_indent que nao seja
    #    comentario, decorator, ou blank
    end_line = len(lines)
    for i in range(def_line, len(lines)):
        stripped = lines[i].rstrip()
        if stripped == "":
            continue
        line_indent = len(lines[i]) - len(lines[i].lstrip())
        if line_indent <= def_indent and not stripped.startswith("#") and not stripped.startswith("@"):
            end_line = i  # linha ANTERIOR a esta (i eh 0-indexed, end_line 1-indexed)
            break

    return (def_line, end_line)


def extract_function_code(file_path: str, start: int, end: int) -> str:
    """Extrai o codigo da funcao entre start e end (1-indexed, inclusivo)."""
    path = Path(file_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start - 1 : end])


def format_dump_block(
    index: int,
    file_path: str,
    func_name: str,
    start: int,
    end: int,
    relevance: str,
    callers: list[str],
    callees: list[str],
    code: str,
) -> str:
    """Formata um bloco de dump de funcao no padrao bug.md."""
    total = end - start + 1
    caller_str = ", ".join(f"`{c}`" for c in callers) if callers else "(nenhum)"
    callee_str = ", ".join(f"`{c}`" for c in callees) if callees else "(nenhuma externa relevante)"

    # Extrai parametros da assinatura
    sig_match = re.search(rf"def\s+{re.escape(func_name)}\s*\(([^)]*)\)", code.split("\n")[0])
    params = ""
    if sig_match:
        raw = sig_match.group(1)
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) <= 3:
            params = ", ".join(parts)
        else:
            params = ", ".join(parts[:3]) + ", ..."

    block = f"""
### {index}. `{file_path}` — `{func_name}({params})`

**Range:** L{start}-L{end} ({total} linhas)
**Callers:** {caller_str}
**Callees:** {callee_str}
**Relevancia:** {relevance}

```python
# {file_path} L{start}-L{end}
{code}
```
"""
    return block


def main():
    parser = argparse.ArgumentParser(description="Xcode Dump Tool — Extrai e formata funcoes para bug.md")
    parser.add_argument("--config", required=True, help="JSON com lista de funcoes a extrair")
    parser.add_argument("--output", default="bug.md", help="Arquivo de saida (default: bug.md)")
    args = parser.parse_args()

    # Carregar config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Erro: arquivo de config nao encontrado: {args.config}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    targets = config.get("targets", [])
    if not targets:
        print("Erro: config sem 'targets'", file=sys.stderr)
        sys.exit(1)

    # Gerar blocos de dump
    dump_blocks: list[str] = []
    errors: list[str] = []

    for i, t in enumerate(targets, start=1):
        file_path = t["file"]
        func_name = t["function"]
        hint_line = t.get("line", 1)
        relevance = t.get("relevance", "(nao especificada)")
        callers = t.get("callers", [])
        callees = t.get("callees", [])

        boundaries = find_function_boundaries(file_path, func_name, hint_line)
        if boundaries is None:
            errors.append(f"  - {file_path}:{func_name}() — nao encontrada")
            continue

        start, end = boundaries
        code = extract_function_code(file_path, start, end)

        block = format_dump_block(i, file_path, func_name, start, end, relevance, callers, callees, code)
        dump_blocks.append(block)
        print(f"  [OK] {file_path}:{func_name}() L{start}-L{end} ({end - start + 1} linhas)")

    if errors:
        print("\n  [!] Erros:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)

    if not dump_blocks:
        print("Erro: nenhum dump gerado", file=sys.stderr)
        sys.exit(1)

    # Juntar todos os blocos
    dump_section = "\n".join(dump_blocks)

    # Inserir no bug.md (substitui placeholder ou append)
    output_path = Path(args.output)
    placeholder = "## 5. Dump de Funcoes\n\n*(a preencher na Fase B)*"
    alt_placeholder = "## 5. Dump de Funcoes\n*(a preencher na Fase B)*"

    if output_path.exists():
        content = output_path.read_text(encoding="utf-8")

        if placeholder in content:
            new_content = content.replace(placeholder, f"## 5. Dump de Funcoes\n{dump_section}")
        elif alt_placeholder in content:
            new_content = content.replace(alt_placeholder, f"## 5. Dump de Funcoes\n{dump_section}")
        else:
            # Se nao encontrar placeholder, append no final
            new_content = content.rstrip() + f"\n\n## 5. Dump de Funcoes\n{dump_section}\n"

        output_path.write_text(new_content, encoding="utf-8")
    else:
        # bug.md nao existe ainda — criar minimo
        header = "# Bug Analysis\n\n## 5. Dump de Funcoes\n"
        output_path.write_text(header + dump_section + "\n", encoding="utf-8")

    print(f"\n  [DONE] {len(dump_blocks)} dumps gravados em {args.output}")


if __name__ == "__main__":
    main()
