"""Utilitários para sanitização de logs e exceções do PJePlus.

Esses helpers são projetados para reduzir consumo de tokens ao compartilhar
contexto de erro em sessões de IA.
"""

from __future__ import annotations

import re
import traceback
from pathlib import Path


def resumir_excecao(exc: BaseException, contexto: str = "", max_frames: int = 3) -> str:
    """Retorna string compacta de exceção para uso em debug/IA."""
    if exc is None:
        return "[Nenhuma exceção fornecida]"

    tb = exc.__traceback__
    frames = traceback.extract_tb(tb) if tb is not None else []
    ultimos = frames[-max_frames:]

    linhas = [f"[{type(exc).__name__}] {exc}"]
    if contexto:
        linhas.append(f"  contexto: {contexto}")

    for frame in ultimos:
        linhas.append(f"  {Path(frame.filename).name}:{frame.lineno} in {frame.name}")
        if frame.line:
            linhas.append(f"    → {frame.line.strip()}")

    return "\n".join(linhas)


def filtrar_log_arquivo(caminho: str | Path, nivel: str = "ERROR", max_linhas: int = 50) -> list[str]:
    """Retorna as primeiras linhas do nível desejado de um arquivo de log."""
    caminho = Path(caminho)
    nivel = nivel.upper()

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de log não encontrado: {caminho}")

    resultado: list[str] = []
    with caminho.open("r", encoding="utf-8", errors="replace") as f:
        for linha in f:
            if nivel in linha.upper():
                resultado.append(linha.rstrip())
                if len(resultado) >= max_linhas:
                    break

    return resultado


def extrair_seletor_dom(html_bruto: str) -> str:
    """Converte um HTML bruto em selector reduzido para compartilhar em IA."""
    if not html_bruto or not isinstance(html_bruto, str):
        return ""

    tag = re.search(r"<(\w+)", html_bruto)
    classes = re.search(r'class=["\']([^"\']+)["\']', html_bruto)
    id_val = re.search(r'id=["\']([^"\']+)["\']', html_bruto)
    texto = re.search(r">([^<]{1,40})<", html_bruto)

    partes = [tag.group(1) if tag else "*" ]
    if classes:
        classes_clean = classes.group(1).strip().replace(" ", ".")
        if classes_clean:
            partes[0] += f".{classes_clean}"
    if id_val:
        partes[0] += f"#{id_val.group(1).strip()}"

    if texto and texto.group(1).strip():
        partes.append(f"texto: '{texto.group(1).strip()}'")

    return " ".join(partes)


if __name__ == "__main__":
    import sys as _sys

    # Uso 1: py Fix/log_cleaner.py caminho/arquivo.log [NIVEL] [max_linhas]
    # Uso 2: py x.py 2>&1 | py Fix/log_cleaner.py --stdin [NIVEL]
    # Uso 3: py Fix/log_cleaner.py --stdin --nivel ERROR

    import argparse as _ap

    parser = _ap.ArgumentParser(
        description="Filtra e resume logs PJePlus para uso em sessão de IA.",
        formatter_class=_ap.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  py Fix/log_cleaner.py logs_execucao/run.log\n"
            "  py Fix/log_cleaner.py logs_execucao/run.log ERROR 30\n"
            "  py x.py 2>&1 | py Fix/log_cleaner.py --stdin\n"
            "  py x.py 2>&1 | py Fix/log_cleaner.py --stdin --nivel WARNING\n"
        ),
    )
    parser.add_argument("arquivo", nargs="?", help="Caminho do arquivo de log (opcional se --stdin)")
    parser.add_argument("--stdin", action="store_true", help="Ler da entrada padrão (pipe)")
    parser.add_argument("--nivel", default="ERROR", help="Nível a filtrar: ERROR, WARNING, INFO (padrão: ERROR)")
    parser.add_argument("--max", type=int, default=50, dest="max_linhas", help="Máximo de linhas (padrão: 50)")
    args = parser.parse_args()

    nivel = args.nivel.upper()

    if args.stdin or (not args.arquivo and not _sys.stdin.isatty()):
        # Modo pipe: py x.py 2>&1 | py Fix/log_cleaner.py --stdin
        linhas = []
        for linha in _sys.stdin:
            if nivel in linha.upper():
                linhas.append(linha.rstrip())
                if len(linhas) >= args.max_linhas:
                    break
        for l in linhas:
            print(l)
    elif args.arquivo:
        linhas = filtrar_log_arquivo(args.arquivo, nivel=nivel, max_linhas=args.max_linhas)
        for l in linhas:
            print(l)
    else:
        parser.print_help()
