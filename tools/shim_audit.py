#!/usr/bin/env python3
"""
tools/shim_audit.py
Audita arquivos shim do projeto PJePlus.

Uso:
  py tools/shim_audit.py                            # lista todos os shims + callers
  py tools/shim_audit.py --shim Prazo/loop_api.py   # auditoria de shim especifico
  py tools/shim_audit.py --zero                     # lista apenas shims sem callers (safe to delete)
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDES = {
    '_archive', '.claude', '.git', 'ref', '.venv', 'ClaudeFree',
    '__pycache__', 'node_modules', 'aider-env',
}

SHIM_MARKERS = [
    'Shim', 'shim', 'Re-export', 're-export', 'LEGADO — thin shim',
    'Reexporta de', 'Espelha a API', 'Compat wrapper', 'compatibilidade',
    'LEGADO: thin shim', 'thin shim', 'LEGADO — thin',
]


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDES for part in path.parts)


def is_shim(path: Path) -> bool:
    try:
        src = path.read_text(encoding='utf-8', errors='ignore')
        head = src[:500]
        return any(marker in head for marker in SHIM_MARKERS)
    except Exception:
        return False


def path_to_module(p: Path) -> str:
    """Converte caminho de arquivo para nome de modulo Python."""
    rel = p.relative_to(ROOT)
    return str(rel).replace('\\', '.').replace('/', '.').removesuffix('.py')


def find_callers(shim_module: str, shim_path: Path) -> list:
    """
    Encontra todos os arquivos que importam shim_module.
    Retorna lista de (arquivo_relativo, numero_linha, conteudo_linha).
    """
    results = []
    parts = shim_module.split('.')
    # Variantes para busca: modulo completo, nome curto, path com / e \
    variants = {
        shim_module,
        '/'.join(parts),
        '\\'.join(parts),
    }
    for py in ROOT.rglob('*.py'):
        if is_excluded(py):
            continue
        if py.resolve() == shim_path.resolve():
            continue  # nao reportar o proprio shim como caller
        try:
            src = py.read_text(encoding='utf-8', errors='ignore')
            for i, line in enumerate(src.splitlines(), 1):
                stripped = line.strip()
                if not ('import' in stripped or 'from' in stripped):
                    continue
                for v in variants:
                    if v in stripped:
                        results.append((str(py.relative_to(ROOT)), i, stripped))
                        break
        except Exception:
            continue
    return results


def collect_shims() -> list:
    shims = []
    for py in sorted(ROOT.rglob('*.py')):
        if is_excluded(py):
            continue
        if is_shim(py):
            shims.append(py)
    return shims


def main():
    args = sys.argv[1:]
    zero_only = '--zero' in args
    target = None
    if '--shim' in args:
        idx = args.index('--shim')
        target = args[idx + 1] if idx + 1 < len(args) else None

    shims = collect_shims()
    if target:
        norm_target = target.replace('\\', '/')
        shims = [s for s in shims if norm_target in str(s).replace('\\', '/')]

    total = 0
    safe_delete = []
    for s in shims:
        mod = path_to_module(s)
        callers = find_callers(mod, s)
        try:
            lines = len(s.read_text(encoding='utf-8', errors='ignore').splitlines())
        except Exception:
            lines = 0

        if zero_only and callers:
            continue

        total += 1
        rel = str(s.relative_to(ROOT))
        print(f"\n{'='*60}")
        print(f"SHIM  : {rel} ({lines}L)")
        print(f"MODULE: {mod}")
        if callers:
            print(f"CALLERS ({len(callers)}):")
            for f, ln, line in callers:
                print(f"  {f}:{ln}  {line}")
        else:
            print("CALLERS: nenhum -- SAFE TO DELETE")
            safe_delete.append(rel)

    print(f"\n{'='*60}")
    print(f"Total shims analisados: {total}")
    print(f"Safe to delete agora  : {len(safe_delete)}")
    if safe_delete:
        print("Arquivos sem callers:")
        for f in safe_delete:
            print(f"  {f}")


if __name__ == '__main__':
    main()
