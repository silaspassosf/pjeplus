"""
tools/scan_live_modules.py
==========================
Varre transitivamente todos os imports a partir de x.py (único entry point),
incluindo imports lazy/condicionais dentro de funções, e produz
tools/live_modules.json com o conjunto de arquivos Python vivos.

Uso:
    py tools/scan_live_modules.py [--verbose]

Saída:
    tools/live_modules.json  — lista de caminhos relativos à raiz do projeto

Regras:
- Imports stdlib e third-party são ignorados.
- `import *` marca o módulo fonte como live e continua o BFS.
- Imports não resolvíveis (dinâmico, importlib) marcam o pacote inteiro como live.
- __init__.py de um pacote é sempre incluído se qualquer módulo do pacote for live.
"""

import ast
import json
import os
import sys
from pathlib import Path

# ===========================================================================
# Configuração
# ===========================================================================

ROOT = Path(__file__).parent.parent.resolve()  # d:\PjePlus
ENTRY_POINTS = [ROOT / "x.py", ROOT / "monitor.py"]

# Pastas de negócio que nos interessam (relativo a ROOT)
TARGET_ROOTS = [
    "atos", "Mandado", "Prazo", "PEC", "SISB", "Triagem", "Fix", "Peticao",
]

OUTPUT = ROOT / "tools" / "live_modules.json"
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

# Módulos stdlib conhecidos — usados para filtrar rapidamente
# (não precisa ser exaustivo; o fallback é checar se existe no projeto)
_STDLIB_TOPLEVEL = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else {
    "os", "sys", "re", "json", "time", "datetime", "logging", "pathlib",
    "collections", "itertools", "functools", "typing", "enum", "signal",
    "traceback", "threading", "subprocess", "shutil", "copy", "math",
    "hashlib", "base64", "io", "struct", "socket", "http", "urllib",
    "ast", "inspect", "importlib", "builtins", "contextlib", "abc",
    "dataclasses", "operator", "string", "textwrap", "warnings",
    "weakref", "gc", "platform", "stat", "glob", "fnmatch", "tempfile",
    "concurrent", "multiprocessing", "queue", "heapq", "bisect",
    "__future__",
}

# Third-party conhecidos do projeto
_THIRD_PARTY_TOPLEVEL = {
    "selenium", "requests", "bs4", "lxml", "PIL", "numpy", "pandas",
    "flask", "fastapi", "uvicorn", "pydantic", "sqlalchemy", "aiohttp",
    "httpx", "yaml", "toml", "dotenv", "psutil", "win32api", "win32con",
    "win32gui", "pyautogui", "keyboard", "mouse", "cv2", "pytesseract",
    "pkg_resources", "setuptools", "pip", "attr", "attrs",
}


# ===========================================================================
# Resolução de módulo → arquivo
# ===========================================================================

def _toplevel_package(dotted: str) -> str:
    return dotted.split(".")[0]


def _is_external(dotted: str) -> bool:
    top = _toplevel_package(dotted)
    return top in _STDLIB_TOPLEVEL or top in _THIRD_PARTY_TOPLEVEL


def resolve_module_to_path(dotted_name: str, current_file: Path) -> Path | None:
    """
    Converte 'Fix.core' → ROOT/Fix/core.py  (ou ROOT/Fix/core/__init__.py).
    Converte '.utils' (relativo) usando current_file como referência.
    Retorna None se não encontrado dentro de ROOT.
    """
    if not dotted_name:
        return None

    # Tentar como caminho absoluto a partir de ROOT
    parts = dotted_name.split(".")
    # Arquivo direto
    candidate = ROOT.joinpath(*parts).with_suffix(".py")
    if candidate.exists():
        return candidate
    # Pacote (__init__.py)
    candidate_pkg = ROOT.joinpath(*parts) / "__init__.py"
    if candidate_pkg.exists():
        return candidate_pkg

    return None


def resolve_relative_import(level: int, module: str | None, current_file: Path) -> str | None:
    """
    Converte import relativo (from . import X, from ..utils import Y) em nome absoluto.
    """
    # package do arquivo atual
    pkg_parts = list(current_file.parent.relative_to(ROOT).parts)
    if level > len(pkg_parts):
        return None
    base_parts = pkg_parts[: len(pkg_parts) - (level - 1)]
    if module:
        base_parts += module.split(".")
    return ".".join(base_parts) if base_parts else None


# ===========================================================================
# Extração de imports de um arquivo (incluindo imports lazy dentro de funções)
# ===========================================================================

def extract_imports(filepath: Path) -> list[tuple[str | None, list[str] | None, bool]]:
    """
    Retorna lista de (module_dotted, names, is_star) para cada import no arquivo.
    Percorre TODO o AST (funcoes, classes, blocos try) -- captura imports lazy.
    Fallback: regex quando o arquivo tem SyntaxError.
    """
    try:
        source = filepath.read_text(encoding="utf-8-sig", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        print(f"  [WARN-SYNTAX] {filepath.name}: {e} -- usando fallback regex")
        return _extract_imports_regex(filepath)

    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name, None, False))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None and node.level == 0:
                continue
            names = [a.name for a in node.names]
            is_star = names == ["*"]
            if node.level > 0:
                # Import relativo -- sera resolvido depois
                results.append((f"__relative__{node.level}__{node.module or ''}", names, is_star))
            else:
                results.append((node.module, names, is_star))

    return results


def _extract_imports_regex(filepath: Path) -> list[tuple[str | None, list[str] | None, bool]]:
    """Extrai imports via regex quando o AST falha (arquivo com SyntaxError)."""
    import re
    results = []
    try:
        source = filepath.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return []

    # from X import Y, Z
    for m in re.finditer(
        r"^\s*from\s+([\w.]+)\s+import\s+(.+)$", source, re.MULTILINE
    ):
        module = m.group(1).strip()
        names_raw = m.group(2).strip()
        if names_raw == "*":
            results.append((module, ["*"], True))
        else:
            # Remover parenteses e comentarios inline
            names_raw = re.sub(r"#.*", "", names_raw).replace("(", "").replace(")", "")
            names = [n.strip().split(" as ")[0].strip() for n in names_raw.split(",") if n.strip()]
            if names:
                results.append((module, names, False))

    # import X
    for m in re.finditer(r"^\s*import\s+([\w.]+)", source, re.MULTILINE):
        results.append((m.group(1).strip(), None, False))

    return results


# ===========================================================================
# BFS principal
# ===========================================================================

def _log(msg: str):
    if VERBOSE:
        print(msg)


def build_live_set() -> set[Path]:
    """
    Faz BFS a partir dos entry points e retorna conjunto de arquivos .py vivos.
    """
    visited: set[Path] = set()
    queue: list[Path] = []
    unresolved_log: list[str] = []

    def enqueue(p: Path):
        p = p.resolve()
        if p not in visited:
            visited.add(p)
            queue.append(p)

    for ep in ENTRY_POINTS:
        if ep.exists():
            enqueue(ep)

    while queue:
        current = queue.pop(0)
        _log(f"[BFS] {current.relative_to(ROOT)}")

        for raw_module, names, is_star in extract_imports(current):
            # Import relativo
            if raw_module and raw_module.startswith("__relative__"):
                parts = raw_module.split("__", 3)
                # formato: __relative__<level>__<module>
                try:
                    level = int(parts[2])
                    mod_suffix = parts[3] if len(parts) > 3 else ""
                except (IndexError, ValueError):
                    continue
                abs_name = resolve_relative_import(level, mod_suffix or None, current)
                if abs_name:
                    raw_module = abs_name
                else:
                    _log(f"  [SKIP-REL] não resolvido em {current.relative_to(ROOT)}")
                    continue

            if not raw_module:
                continue
            if _is_external(raw_module):
                _log(f"  [EXT] {raw_module}")
                continue

            resolved = resolve_module_to_path(raw_module, current)
            if resolved:
                _log(f"  [LIVE] {raw_module} -> {resolved.relative_to(ROOT)}")
                enqueue(resolved)
                # Se e 'from pkg.sub import func' e pkg.sub e um pacote,
                # garantir que __init__.py do pacote tambem e live
                pkg_init = resolved.parent / "__init__.py"
                if pkg_init.exists():
                    enqueue(pkg_init)
                # Se importamos 'from pkg import name', tentar tambem pkg/name.py
                # (submodule vs atributo — ex: from Prazo import loop_prazo)
                if names and not is_star:
                    for name in names:
                        sub_candidate = resolved.parent / f"{name}.py"
                        if sub_candidate.exists():
                            _log(f"  [SUBMOD] {raw_module}.{name} -> {sub_candidate.relative_to(ROOT)}")
                            enqueue(sub_candidate)
                        sub_pkg = resolved.parent / name / "__init__.py"
                        if sub_pkg.exists():
                            _log(f"  [SUBPKG] {raw_module}.{name} -> {sub_pkg.relative_to(ROOT)}")
                            enqueue(sub_pkg)
            else:
                # Não encontrado no projeto — pode ser dinâmico ou third-party não listado
                top = _toplevel_package(raw_module)
                # Tentar marcar o pacote inteiro como live (conservador)
                pkg_dir = ROOT / top
                if pkg_dir.is_dir():
                    init = pkg_dir / "__init__.py"
                    if init.exists():
                        _log(f"  [CONSERVATIVE] {raw_module} nao resolvido -> marcando {top}/__init__.py")
                        enqueue(init)
                    else:
                        _log(f"  [WARN] {raw_module} não resolvido e sem __init__.py em {top}/")
                    unresolved_log.append(f"{current.relative_to(ROOT)} :: {raw_module}")
                else:
                    _log(f"  [EXT?] {raw_module} — ignorado (não é diretório no projeto)")

    if unresolved_log:
        print(f"\n[WARN] {len(unresolved_log)} imports nao resolvidos completamente:")
        for u in unresolved_log[:20]:
            print(f"  {u}")
        if len(unresolved_log) > 20:
            print(f"  ... e mais {len(unresolved_log) - 20}")

    return visited


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("[scan_live_modules] Iniciando BFS a partir de x.py + monitor.py...")
    live = build_live_set()

    # Filtrar: apenas arquivos dentro das pastas alvo OU raiz (x.py, monitor.py)
    target_dirs = [ROOT / t for t in TARGET_ROOTS]
    filtered = set()
    for p in live:
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            continue
        # Incluir se está numa das pastas alvo OU é um entry point da raiz
        parts = rel.parts
        if parts[0] in TARGET_ROOTS or p in ENTRY_POINTS:
            filtered.add(p)

    # Converter para caminhos relativos e ordenar
    relative_paths = sorted(
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in filtered
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(relative_paths, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n[RESULTADO] {len(relative_paths)} arquivos vivos encontrados")
    print(f"[SAIDA] {OUTPUT.relative_to(ROOT)}")

    # Verificacoes obrigatorias do plano
    must_have = [
        "Fix/core.py",
        "Mandado/processamento_api.py",
        "Prazo/__init__.py",     # loop_prazo esta definido no __init__.py do pacote
        "Triagem/runner.py",
        "Peticao/pet.py",
    ]
    print("\n[CHECK] Arquivos criticos no live set:")
    all_ok = True
    for m in must_have:
        found = m in relative_paths
        status = "OK" if found else "FAIL - NAO ENCONTRADO"
        print(f"  {status}  {m}")
        if not found:
            all_ok = False

    if not all_ok:
        print("\n[ALERTA] Alguns arquivos criticos nao foram detectados.")
        print("         Verificar imports lazy e caminhos de modulo.")
        sys.exit(1)
    else:
        print("\n[OK] Todos os arquivos criticos detectados.")


if __name__ == "__main__":
    main()
