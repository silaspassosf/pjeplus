"""
tools/archive_dead.py
=====================
Le tools/live_modules.json e move para _archive/YYYYMMDD_HHMMSS/ todos os
arquivos .py nas pastas alvo que NAO estao no live set.

Uso:
    py tools/archive_dead.py [--dry-run]

Flags:
    --dry-run   Imprime o que seria movido sem mover nada.

Saida:
    _archive/YYYYMMDD_HHMMSS/_manifest.json
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ===========================================================================
# Configuracao
# ===========================================================================

ROOT = Path(__file__).parent.parent.resolve()
LIVE_JSON = ROOT / "tools" / "live_modules.json"
ARCHIVE_BASE = ROOT / "_archive"

TARGET_ROOTS = [
    "atos", "Mandado", "Prazo", "PEC", "SISB", "Triagem", "Fix", "Peticao",
]

DRY_RUN = "--dry-run" in sys.argv or "-n" in sys.argv


# ===========================================================================
# Helpers
# ===========================================================================

def load_live_set() -> set[str]:
    """Carrega live_modules.json e retorna conjunto de caminhos relativos (forward slash)."""
    if not LIVE_JSON.exists():
        print(f"[ERRO] {LIVE_JSON} nao encontrado. Rode scan_live_modules.py primeiro.")
        sys.exit(1)
    data = json.loads(LIVE_JSON.read_text(encoding="utf-8"))
    # Normalizar para forward slash
    return set(p.replace("\\", "/") for p in data)


def collect_all_target_files() -> list[Path]:
    """Retorna todos os .py nas pastas alvo (sem __pycache__)."""
    result = []
    for troot in TARGET_ROOTS:
        d = ROOT / troot
        if not d.is_dir():
            continue
        for p in d.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            result.append(p)
    return result


def rel(p: Path) -> str:
    """Caminho relativo a ROOT com forward slash."""
    return str(p.relative_to(ROOT)).replace("\\", "/")


def should_archive(p: Path, live: set[str], dead_set: set[str]) -> bool:
    """
    Decide se o arquivo deve ser arquivado.
    Regra especial __init__.py: so arquiva se todos os .py do mesmo diretorio
    tambem estiverem mortos.
    """
    r = rel(p)
    if r in live:
        return False

    if p.name == "__init__.py":
        siblings = [
            f for f in p.parent.glob("*.py")
            if "__pycache__" not in f.parts and f != p
        ]
        # So arquiva o __init__ se todos os irmaos tambem sao dead
        if any(rel(s) in live for s in siblings):
            return False

    return True


# ===========================================================================
# Main
# ===========================================================================

def main():
    live = load_live_set()
    all_files = collect_all_target_files()

    print(f"[archive_dead] Arquivos .py nas pastas alvo: {len(all_files)}")
    print(f"[archive_dead] Arquivos no live set: {len(live)}")

    # Primeiro passo: identificar dead sem considerar regra __init__
    raw_dead = {p for p in all_files if rel(p) not in live}
    raw_dead_rels = {rel(p) for p in raw_dead}

    # Segundo passo: aplicar regra __init__
    to_archive = []
    protected_inits = []
    for p in sorted(raw_dead):
        if should_archive(p, live, raw_dead_rels):
            to_archive.append(p)
        else:
            protected_inits.append(p)

    print(f"[archive_dead] Candidatos a arquivar: {len(to_archive)}")
    if protected_inits:
        print(f"[archive_dead] __init__.py protegidos (pacote parcialmente vivo): {len(protected_inits)}")
        for p in protected_inits:
            print(f"  PROTEGIDO  {rel(p)}")

    if DRY_RUN:
        print("\n[DRY-RUN] Os seguintes arquivos SERIAM movidos para _archive/:\n")
        for p in to_archive:
            print(f"  {rel(p)}")
        print(f"\n[DRY-RUN] Total: {len(to_archive)} arquivos. Nenhuma acao executada.")
        return

    if not to_archive:
        print("[archive_dead] Nenhum arquivo dead encontrado. Repositorio limpo!")
        return

    # Criar diretorio datado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_root = ARCHIVE_BASE / timestamp
    dest_root.mkdir(parents=True, exist_ok=True)

    manifest = []
    moved = 0
    errors = []

    for p in to_archive:
        r = rel(p)
        dest = dest_root / r
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(p), str(dest))
            manifest.append({
                "original": r,
                "archived_to": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "motivo": "not_reachable_from_x_py",
                "timestamp": timestamp,
            })
            moved += 1
            print(f"  MOVIDO  {r}")
        except Exception as e:
            errors.append({"arquivo": r, "erro": str(e)})
            print(f"  ERRO    {r} -- {e}")

    # Salvar manifesto
    manifest_path = dest_root / "_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n[RESULTADO] {moved} arquivos movidos para _archive/{timestamp}/")
    print(f"[RESULTADO] Manifesto: {manifest_path.relative_to(ROOT)}")
    if errors:
        print(f"[ALERTA] {len(errors)} erros durante o arquivamento:")
        for e in errors:
            print(f"  {e['arquivo']}: {e['erro']}")


if __name__ == "__main__":
    main()
