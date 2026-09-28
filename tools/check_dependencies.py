#!/usr/bin/env python3
"""
check_dependencies.py — PJePlus
Detecta dependências instaladas, compara com requirements.txt e gera install_missing.sh
"""

import importlib
import subprocess
import sys
from pathlib import Path

REQUIREMENTS_FILE = Path("requirements.txt")
OUTPUT_SCRIPT = Path("install_missing.sh")

# Mapeamento nome-pacote PyPI → nome-módulo importável (quando diferem)
IMPORT_ALIASES = {
    "selenium": "selenium",
    "webdriver-manager": "webdriver_manager",
    "python-dotenv": "dotenv",
    "Pillow": "PIL",
    "beautifulsoup4": "bs4",
    "pyautogui": "pyautogui",
    "pynput": "pynput",
    "requests": "requests",
    "lxml": "lxml",
    "pyperclip": "pyperclip",
    "pywin32": "win32api",
}


def get_installed_packages() -> dict[str, str]:
    """Retorna {nome_normalizado: versão} de tudo instalado no ambiente atual."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True, text=True
    )
    packages = {}
    for line in result.stdout.splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            packages[name.lower().replace("-", "_")] = version
    return packages


def parse_requirements() -> list[str]:
    if not REQUIREMENTS_FILE.exists():
        print(f"[AVISO] {REQUIREMENTS_FILE} não encontrado — usando lista interna.")
        return list(IMPORT_ALIASES.keys())
    reqs = []
    for line in REQUIREMENTS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            reqs.append(line.split("==")[0].split(">=")[0].split("<=")[0].strip())
    return reqs


def check(reqs: list[str], installed: dict[str, str]) -> tuple[list, list]:
    ok, missing = [], []
    for pkg in reqs:
        key = pkg.lower().replace("-", "_")
        if key in installed:
            ok.append((pkg, installed[key]))
        else:
            # Tenta importar diretamente como fallback
            mod = IMPORT_ALIASES.get(pkg, key)
            try:
                importlib.import_module(mod)
                ok.append((pkg, "importável"))
            except ImportError:
                missing.append(pkg)
    return ok, missing


def generate_install_script(missing: list[str]):
    lines = ["#!/bin/bash", "# Gerado por check_dependencies.py — PJePlus", ""]
    lines.append(f'PYTHON="{sys.executable}"')
    lines.append("")
    for pkg in missing:
        lines.append(f'$PYTHON -m pip install "{pkg}"')
    lines.append("")
    lines.append('echo "Instalação concluída."')
    OUTPUT_SCRIPT.write_text("\n".join(lines))
    try:
        OUTPUT_SCRIPT.chmod(0o755)
    except Exception:
        pass
    print(f"\n[OK] Script gerado: {OUTPUT_SCRIPT}")


def main():
    print("=== PJePlus — Check de Dependências ===\n")
    installed = get_installed_packages()
    reqs = parse_requirements()
    ok, missing = check(reqs, installed)

    print(f"✅ Instaladas ({len(ok)}):")
    for name, ver in ok:
        print(f"   {name} == {ver}")

    if missing:
        print(f"\n❌ Faltando ({len(missing)}):")
        for pkg in missing:
            print(f"   {pkg}")
        generate_install_script(missing)
    else:
        print("\n✅ Todas as dependências estão satisfeitas.")


if __name__ == "__main__":
    main()
