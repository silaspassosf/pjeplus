"""tools/check_imports.py — Valida importabilidade de todos os módulos Fix.

Uso:
    py tools/check_imports.py

O script:
1. Varre todos os .py dentro de Fix/
2. Tenta importar cada módulo via importlib
3. Reporta sucessos e falhas
4. Retorna exit code 0 se tudo OK, 1 caso contrário
"""

import importlib
import os
import sys
import warnings
from pathlib import Path

# Add project root to path so `Fix` can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Suppress DeprecationWarning during import check (stubs intentionally use them)
warnings.filterwarnings("ignore", category=DeprecationWarning)

FIX_DIR = PROJECT_ROOT / "Fix"

if not FIX_DIR.is_dir():
    print(f"ERRO: Diretório Fix não encontrado em {FIX_DIR}")
    sys.exit(1)


def find_py_files(directory: Path) -> list:
    """Encontra todos os arquivos .py recursivamente, ignorando __pycache__."""
    py_files = []
    for root, dirs, files in os.walk(directory):
        # Ignorar __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                full_path = Path(root) / f
                rel_path = full_path.relative_to(directory.parent)  # e.g., Fix/selenium_base/__init__.py
                # Converter para módulo: Fix.selenium_base.__init__
                parts = list(rel_path.parts)
                parts[-1] = parts[-1].replace(".py", "")
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                module_name = ".".join(parts)
                py_files.append((module_name, full_path))
    return py_files


def check_syntax(filepath: Path) -> bool:
    """Verifica se o arquivo tem sintaxe válida."""
    import py_compile
    try:
        py_compile.compile(str(filepath), doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  SYNTAX ERROR: {e}")
        return False


def check_import(module_name: str) -> bool:
    """Tenta importar um módulo."""
    try:
        importlib.import_module(module_name)
        return True
    except Exception as e:
        print(f"  IMPORT ERROR: {e}")
        return False


def main():
    print(f"=== Verificando módulos em {FIX_DIR} ===\n")

    py_files = find_py_files(FIX_DIR)
    print(f"Encontrados {len(py_files)} módulos Python.\n")

    ok_count = 0
    fail_count = 0
    skip_count = 0
    failures = []

    for module_name, full_path in sorted(py_files):
        # Pular módulos que sabemos serem problemáticos ou muito específicos
        # (ex.: native_host.py depende de ambiente específico)
        skip_modules = {"Fix.native_host"}
        if module_name in skip_modules:
            skip_count += 1
            continue

        print(f"[{ok_count + fail_count + 1}] {module_name}...", end=" ")

        # 1. Check syntax
        if not check_syntax(full_path):
            fail_count += 1
            failures.append(module_name)
            print("FAIL (syntax)")
            continue

        # 2. Try import
        if not check_import(module_name):
            fail_count += 1
            failures.append(module_name)
            print("FAIL (import)")
            continue

        ok_count += 1
        print("OK")

    print(f"\n{'='*50}")
    print(f"Resultados: {ok_count} OK, {fail_count} FAIL, {skip_count} SKIP")

    if failures:
        print(f"\nMódulos com falha:")
        for f in failures:
            print(f"  - {f}")
        print(f"\n{'='*50}")
        print("VALIDAÇÃO FALHOU")
        return 1
    else:
        print(f"\n{'='*50}")
        print("VALIDAÇÃO PASSOU — todos os módulos importam corretamente")
        return 0


if __name__ == "__main__":
    sys.exit(main())
