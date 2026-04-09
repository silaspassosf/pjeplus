import ast, json, os, re
from pathlib import Path

MAP_FILE  = "00act_map.json"
OUTPUT    = "00act.md"

def _extrair_via_ast(filepath: str, nome: str) -> str | None:
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree   = ast.parse(source)
        lines  = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == nome:
                return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    except Exception:
        pass
    return None

def _extrair_via_regex(filepath: str, nome: str) -> str | None:
    try:
        source  = Path(filepath).read_text(encoding="utf-8")
        pattern = (
            rf"((?:[ \t]*@\w[^\n]*\n)*"
            rf"[ \t]*(?:async\s+)?def {re.escape(nome)}\s*\(.*?)"
            rf"(?=\n[ \t]*(?:@|\s*(?:async\s+)?def )|\Z)"
        )
        m = re.search(pattern, source, re.DOTALL)
        if m:
            return m.group(0).rstrip()
    except Exception:
        pass
    return None

def extrair_funcao(arquivo: str, nome: str) -> str:
    resultado = _extrair_via_ast(arquivo, nome) or _extrair_via_regex(arquivo, nome)
    return resultado if resultado else f"# ERRO: '{nome}' nao encontrada em {arquivo}"

def bloco(arquivo: str, funcao: str, papel: str) -> str:
    codigo = extrair_funcao(arquivo, funcao)
    cab    = f"> **Papel:** {papel}\n\n" if papel else ""
    return f"### `{arquivo}` → `{funcao}`\n{cab}```python\n{codigo}\n```\n\n"

def main() -> None:
    if not os.path.exists(MAP_FILE):
        print(f"ERRO: {MAP_FILE} nao encontrado. Execute o agente primeiro.")
        return

    data      = json.load(open(MAP_FILE, encoding="utf-8"))
    contexto  = data.get("contexto",  "")
    causa     = data.get("causa",     "")
    objetivo  = data.get("objetivo",  "")
    abordagem = data.get("abordagem", "")
    funcoes   = data.get("funcoes",   [])

    secoes = [
        "# 00act — Contexto de Debug PJePlus\n",
        f"## Contexto\n{contexto}\n",
        f"## Causa Técnica\n{causa}\n",
        f"## Objetivo\n{objetivo}\n",
        f"## Abordagem Proposta\n{abordagem}\n",
        "## Funções Relevantes (Ordem de Execução)\n",
    ]

    for entry in funcoes:
        secoes.append(bloco(
            entry.get("arquivo", ""),
            entry.get("funcao",  ""),
            entry.get("papel",   ""),
        ))

    Path(OUTPUT).write_text("\n".join(secoes), encoding="utf-8")
    print(f"✅ {OUTPUT} gerado com {len(funcoes)} funcao(oes).")

if __name__ == "__main__":
    main()