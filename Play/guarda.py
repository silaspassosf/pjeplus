# -*- coding: utf-8 -*-
"""Guarda de fronteira: impede o fork de voltar a crescer.

O `play/` anterior era uma cópia integral do projeto e apodreceu em ~1 mês.
Nenhuma das divergências tinha a ver com Playwright: eram regras de negócio e
API evoluindo na raiz enquanto a cópia ficava parada.

A regra é verificável, não é disciplina:

    se um módulo não importa selenium/playwright nem toca no driver,
    ele não é copiado — é importado da raiz.

    py play/guarda.py        # sai != 0 se a fronteira foi violada
"""
import ast
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# Nunca copiar, mesmo que passem a importar selenium por acidente.
NEGADOS = (
    "regras", "variaveis", "monitoramento_", "progresso", "tipos.py",
    "utilitarios_processamento.py", "rule_registry.py", "resultado_execucao.py",
)

# Não fazem parte da superfície de fork.
IGNORADOS = ("pjeplay", "docs", "__pycache__", ".git", "downloads")

MARCAS_BROWSER = ("selenium", "playwright", "pjeplay", "driver", "page", "locator")


def _toca_browser(caminho):
    """True se o módulo importa selenium/playwright ou recebe driver/page."""
    try:
        arvore = ast.parse(open(caminho, encoding="utf-8").read())
    except Exception:
        return True  # ilegível: não acusar
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and no.module:
            if any(m in no.module for m in ("selenium", "playwright", "pjeplay")):
                return True
        elif isinstance(no, ast.Import):
            if any(m in a.name for a in no.names for m in ("selenium", "playwright")):
                return True
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(a.arg in ("driver", "page") for a in no.args.args):
                return True
    return False


def verificar():
    duplicados, violacoes = [], []

    for dp, dirs, arquivos in os.walk(AQUI):
        dirs[:] = [d for d in dirs if d not in IGNORADOS]
        for arquivo in arquivos:
            if not arquivo.endswith(".py"):
                continue
            caminho = os.path.join(dp, arquivo)
            rel = os.path.relpath(caminho, AQUI).replace("\\", "/")
            if not os.path.exists(os.path.join(RAIZ, rel)):
                continue  # arquivo só do play/: legítimo

            if any(n in rel for n in NEGADOS):
                violacoes.append((rel, "na lista de nunca-copiar"))
            elif not _toca_browser(caminho):
                violacoes.append((rel, "não toca no browser — importe da raiz"))
            else:
                duplicados.append(rel)

    return duplicados, violacoes


def main():
    duplicados, violacoes = verificar()

    if duplicados:
        print(f"superfície de fork ({len(duplicados)} arquivos de browser):")
        for rel in sorted(duplicados):
            print(f"   ~ {rel}")

    if violacoes:
        print(f"\nFRONTEIRA VIOLADA ({len(violacoes)}):")
        for rel, motivo in sorted(violacoes):
            print(f"   X {rel}  — {motivo}")
        print("\nEsses arquivos devem ser importados da raiz, não copiados.")
        return 1

    print(f"fronteira ok — {len(duplicados)} arquivos duplicados, todos de browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
