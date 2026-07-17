"""Migração de cache de seletores — separa frio/quente.

Estratégia automática:
  - Seletores baseados em atributos estruturais do PJe (`mat-dialog-container`,
    `mattooltip` com texto fixo) → `_frio_` (estáticos, nunca sobrescrever)
  - Chaves ciclo ou temporárias → mantidas em `aprendizado_seletores.json`

Uso:
  py scripts/migrate_selectores_frios.py

Saída:
  seletores_frios.json         — seletores estáticos, imutáveis pelo SmartFinder
  aprendizado_seletores.json   — seletores voláteis (aprendizado contínuo)
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE = PROJECT_ROOT / "aprendizado_seletores.json"
FRIO_PATH = PROJECT_ROOT / "seletores_frios.json"

# Heurísticas para classificar como frio (estrutural/estático do PJe)
_FRIO_PREFIXO_CHAVE = ("_frio_",)
_FRIO_PALAVRAS_CHAVE = (
    "mat-dialog-container",
    "mat-progress-bar",
    "Abre a tarefa",
)
_FRIO_PALAVRAS_VALOR = (
    "mat-dialog-container",
    "Abre a tarefa do processo",
)


def _classificar(chave: str, valor) -> bool:
    """Retorna True se o seletor deve ser tratado como frio."""
    if any(chave.startswith(p) for p in _FRIO_PREFIXO_CHAVE):
        return True
    if any(p in chave for p in _FRIO_PALAVRAS_CHAVE):
        return True
    valor_str = json.dumps(valor)
    if any(p in valor_str for p in _FRIO_PALAVRAS_VALOR):
        return True
    return False


def migrar(dry_run: bool = False):
    if not CACHE.exists():
        raise FileNotFoundError(f"Cache não encontrado: {CACHE}")

    todos: dict = json.loads(CACHE.read_text(encoding="utf-8"))

    # Carrega frios existentes (não sobrescreve o que já foi classificado)
    frios_existentes: dict = {}
    if FRIO_PATH.exists():
        frios_existentes = json.loads(FRIO_PATH.read_text(encoding="utf-8"))

    frio: dict = dict(frios_existentes)
    quente: dict = {}

    movidos = []
    for chave, valor in todos.items():
        if _classificar(chave, valor):
            # Normaliza chave para _frio_ se ainda não tem prefixo
            chave_frio = chave if chave.startswith("_frio_") else f"_frio__{chave}"
            frio[chave_frio] = valor
            movidos.append((chave, chave_frio))
        else:
            quente[chave] = valor

    if not dry_run:
        FRIO_PATH.write_text(json.dumps(frio, indent=2, ensure_ascii=False), encoding="utf-8")
        CACHE.write_text(json.dumps(quente, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'[DRY RUN] ' if dry_run else ''}Migracao concluida.")
    print(f"  Frio   : {len(frio)} chaves  → {FRIO_PATH.name}")
    print(f"  Quente : {len(quente)} chaves → {CACHE.name}")
    if movidos:
        print("  Movidos:")
        for orig, novo in movidos:
            print(f"    {orig!r}  →  {novo!r}")
    else:
        print("  Nenhuma chave nova movida.")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    migrar(dry_run=dry)
