"""
scan_orphan_imports.py — detecta 'from X import Y' onde Y nao existe no modulo X.
Uso: py tools/scan_orphan_imports.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCAN_DIRS = ["atos", "Fix", "Mandado", "Prazo", "PEC", "SISB", "Triagem", "Peticao", "core"]
EXCLUDE = {"_archive", "ref", "aider-env", "__pycache__"}

# Cache: module_path -> set of exported names
_exports_cache: dict[str, set[str]] = {}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def _get_exports(module_path: Path) -> set[str]:
    """Retorna todos os nomes definidos no topo de um modulo (def, class, import, assign)."""
    key = str(module_path)
    if key in _exports_cache:
        return _exports_cache[key]

    src = _read(module_path)
    names: set[str] = set()
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        names.add(alias.asname or alias.name)
    except SyntaxError:
        pass

    _exports_cache[key] = names
    return names


def _resolve_module(from_module: str | None, level: int, module_file: Path) -> Path | None:
    """Resolve modulo para caminho de arquivo .py."""
    # Relativo
    if level > 0:
        base = module_file.parent
        for _ in range(level - 1):
            base = base.parent
        if from_module:
            parts = from_module.split(".")
            candidate = base.joinpath(*parts)
            if (candidate / "__init__.py").exists():
                return candidate / "__init__.py"
            py = candidate.with_suffix(".py")
            if py.exists():
                return py
        else:
            init = base / "__init__.py"
            if init.exists():
                return init
        return None

    # Absoluto
    if not from_module:
        return None
    parts = from_module.split(".")
    candidate = ROOT.joinpath(*parts)
    if (candidate / "__init__.py").exists():
        return candidate / "__init__.py"
    py = candidate.with_suffix(".py")
    if py.exists():
        return py
    return None


def scan() -> list[tuple[str, int, str, str]]:
    """Retorna lista de (arquivo, linha, modulo, nome_orfao)."""
    orphans = []

    py_files: list[Path] = []
    for d in SCAN_DIRS:
        dp = ROOT / d
        if not dp.exists():
            continue
        for f in dp.rglob("*.py"):
            if any(p in EXCLUDE for p in f.parts):
                continue
            py_files.append(f)

    for fpath in py_files:
        src = _read(fpath)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            # Ignorar star imports e imports sem nomes especificos
            names = [a.name for a in node.names if a.name != "*"]
            if not names:
                continue

            module_path = _resolve_module(node.module, node.level, fpath)
            if module_path is None or not module_path.exists():
                continue

            exports = _get_exports(module_path)
            if not exports:
                continue  # nao conseguiu parsear — skip conservador

            for name in names:
                if name not in exports:
                    rel = str(fpath.relative_to(ROOT))
                    mod_str = ("." * node.level) + (node.module or "")
                    orphans.append((rel, node.lineno, mod_str, name))

    return orphans


if __name__ == "__main__":
    print("Scanning for orphan imports...")
    results = scan()
    if not results:
        print("✓ Nenhum import orfao encontrado.")
        sys.exit(0)

    print(f"\n{len(results)} import(s) orfao(s) encontrado(s):\n")
    for fpath, lineno, mod, name in sorted(results):
        print(f"  {fpath}:{lineno}: from {mod} import {name}")
    sys.exit(1)
