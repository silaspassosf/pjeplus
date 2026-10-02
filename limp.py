# -*- coding: utf-8 -*-
"""Limpeza de artefatos temporários, cache e logs antigos do PJePlus.

    py limp.py                 # limpeza padrão (logs > 3 dias; progresso total)
    py limp.py --dias 7        # mantém logs dos últimos 7 dias
    py limp.py --dry-run       # apenas mostra o que seria removido
    py limp.py --sem-progresso # não mexe nas listas de progresso

Remove:
  - cache Python: __pycache__/, .pytest_cache/, *.pyc, *.pyo
  - temporários conhecidos na raiz (html.txt, p2b_log.txt,
    erro_fatal_selenium.log, login_timeout_*.png, *.tmp, *.bak)
  - logs de execução em logs_execucao/ com mais de N dias (padrão: 3)
  - TODAS as listas de progresso em progresso.json, independente da idade
    (via Fix.monitoramento_progresso_unificado.limpar_progresso_antigos)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# Diretórios que nunca devem ser varridos/limpos.
IGNORAR_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules",
    "outros projetos", "ref", "leg", "_archive", "ORIGINAIS",
}

# Artefatos temporários conhecidos na raiz (padrões glob).
TEMP_RAIZ = (
    "html.txt",
    "p2b_log.txt",
    "erro_fatal_selenium.log",
    "login_timeout_*.png",
    "*.tmp",
    "*.bak",
    "*~",
)

LOG_DIR = RAIZ / "logs_execucao"


def _tamanho(caminho: Path) -> int:
    """Soma o tamanho em bytes de um arquivo ou árvore de diretórios."""
    if caminho.is_file():
        try:
            return caminho.stat().st_size
        except OSError:
            return 0
    total = 0
    for base, _, arquivos in os.walk(caminho):
        for nome in arquivos:
            try:
                total += (Path(base) / nome).stat().st_size
            except OSError:
                pass
    return total


def _remover(caminho: Path, dry_run: bool, resumo: dict) -> None:
    """Remove arquivo/diretório (ou apenas reporta, em dry-run)."""
    try:
        tamanho = _tamanho(caminho)
        if not dry_run:
            if caminho.is_dir():
                shutil.rmtree(caminho, ignore_errors=True)
            else:
                caminho.unlink(missing_ok=True)
        resumo["itens"] += 1
        resumo["bytes"] += tamanho
        try:
            relativo = caminho.relative_to(RAIZ)
        except ValueError:
            relativo = caminho
        print(f"  {'[dry] ' if dry_run else ''}- {relativo}")
    except OSError as e:
        print(f"  ! falha ao remover {caminho}: {e}")


def limpar_cache(dry_run: bool, resumo: dict) -> None:
    """Remove __pycache__/, .pytest_cache/ e arquivos *.pyc/*.pyo."""
    print("[limp] cache Python (__pycache__, .pytest_cache, *.pyc/*.pyo)")
    for base, dirs, arquivos in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
        for d in list(dirs):
            if d == "__pycache__":
                _remover(Path(base) / d, dry_run, resumo)
                dirs.remove(d)
        for nome in arquivos:
            if nome.endswith((".pyc", ".pyo")):
                _remover(Path(base) / nome, dry_run, resumo)

    pytest_cache = RAIZ / ".pytest_cache"
    if pytest_cache.exists():
        _remover(pytest_cache, dry_run, resumo)


def limpar_temp_raiz(dry_run: bool, resumo: dict) -> None:
    """Remove artefatos temporários conhecidos na raiz do projeto."""
    print("[limp] temporários na raiz")
    for padrao in TEMP_RAIZ:
        for caminho in sorted(RAIZ.glob(padrao)):
            if caminho.is_file():
                _remover(caminho, dry_run, resumo)


def limpar_logs(dias: int, dry_run: bool, resumo: dict) -> None:
    """Remove logs de execução com mais de `dias` dias."""
    print(f"[limp] logs de execução com mais de {dias} dia(s) em logs_execucao/")
    if not LOG_DIR.is_dir():
        print("  (diretório ausente)")
        return
    limite = datetime.now() - timedelta(days=dias)
    for caminho in sorted(LOG_DIR.iterdir()):
        if not caminho.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(caminho.stat().st_mtime)
        except OSError:
            continue
        if mtime < limite:
            _remover(caminho, dry_run, resumo)


def _carregar_purga_progresso():
    """Importa a purga de progresso respeitando a ordem do backend Playwright."""
    play = RAIZ / "Play"
    for caminho in (str(RAIZ), str(play)):
        if caminho not in sys.path:
            sys.path.insert(0, caminho)
    try:
        import pjeplay
        pjeplay.iniciar(raiz_projeto=str(RAIZ), nativo=True, silencioso=True)
    except Exception as e:  # noqa: BLE001 - backend opcional para limpeza
        print(f"  ! backend Playwright indisponível ({e})")
    from Fix.monitoramento_progresso_unificado import limpar_progresso_antigos
    return limpar_progresso_antigos


def limpar_progresso(dry_run: bool, resumo: dict) -> None:
    """Purga TODAS as entradas das listas de progresso (progresso.json).

    Independente da idade: `dias=0` faz `limpar_progresso_antigos` remover
    qualquer entrada com data de hoje ou anterior (ou seja, todas).
    """
    print("[limp] listas de progresso (progresso.json) — limpeza total")
    if dry_run:
        print("  (dry-run: purga não aplicada)")
        return
    try:
        purgar = _carregar_purga_progresso()
        resultado = purgar(dias=0)
    except Exception as e:  # noqa: BLE001 - limpeza não deve quebrar o script
        print(f"  ! purga de progresso falhou: {e}")
        return
    if resultado:
        total = sum(resultado.values())
        detalhe = ", ".join(f"{k}={v}" for k, v in sorted(resultado.items()))
        print(f"  - {total} entrada(s) removida(s): {detalhe}")
        resumo["itens"] += total
    else:
        print("  (nada a remover)")


def _formatar_bytes(total: int) -> str:
    valor = float(total)
    for unidade in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            return f"{valor:.1f} {unidade}"
        valor /= 1024
    return f"{valor:.1f} GB"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Limpeza de temporários, cache, logs e progresso do PJePlus.")
    parser.add_argument("--dias", type=int, default=3,
                        help="idade mínima (dias) para remover logs de execução (padrão: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="apenas mostra o que seria removido")
    parser.add_argument("--sem-progresso", action="store_true",
                        help="não mexe nas listas de progresso")
    args = parser.parse_args(argv)

    if args.dias < 0:
        parser.error("--dias deve ser >= 0")

    resumo = {"itens": 0, "bytes": 0}
    print(f"[limp] raiz: {RAIZ}")
    print(f"[limp] modo: {'dry-run' if args.dry_run else 'aplicar'}\n")

    limpar_cache(args.dry_run, resumo)
    limpar_temp_raiz(args.dry_run, resumo)
    limpar_logs(args.dias, args.dry_run, resumo)
    if not args.sem_progresso:
        limpar_progresso(args.dry_run, resumo)

    print(f"\n[limp] {resumo['itens']} item(ns) "
          f"{'a remover' if args.dry_run else 'removido(s)'} "
          f"({_formatar_bytes(resumo['bytes'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
