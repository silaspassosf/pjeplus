# -*- coding: utf-8 -*-
"""Troca `time.sleep(N)` por `espera.assentar(driver, N)` no escopo da migração.

Segurança por construção: `assentar` é limitada pelo mesmo N. Em Selenium o
comportamento é idêntico ao de hoje (dorme N); em Playwright retorna quando a
interface estabiliza. Nenhum caminho fica mais lento ou menos confiável.

Recusa-se a tocar quando não tem certeza:
  - sleeps de throttle/anti-detecção (SISB) — são deliberados;
  - sítios sem um driver no escopo léxico;
  - sleeps dentro de `except` de retry/backoff — ali a espera é a política.

    py play/migrar_sleeps.py            # dry-run, só relata
    py play/migrar_sleeps.py --aplicar  # grava
"""
import ast
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESCOPO = ["PEC", "Mandado", "atos", "Fix",
          "Prazo/p2b_documentos.py", "Prazo/p2b_gateway.py",
          "Prazo/p2b_regras_execucao.py", "SISB"]

SLEEP = re.compile(r"^(\s*)time\.sleep\(\s*([0-9]*\.?[0-9]+)\s*\)\s*$")

# Deliberados: throttle e evasão de detecção. Nunca tocar.
# Inclui simulação de comportamento humano — `simulate_human_movement` no SISB
# existe *para* gastar tempo; sem os sleeps ela não faz nada.
THROTTLE = re.compile(
    r"throttl|rate.?limit|anti.?detec|deteccao|detecção|backoff|captcha|"
    r"aguardar_entre|intervalo_seguro|pausa_seguranca|"
    r"human|humano|simulate|simular|digitacao|jitter|aleatori", re.I)

# Nome da função já denuncia espera deliberada.
FUNCAO_DELIBERADA = re.compile(
    r"human|humano|simulate|simular|throttl|rate_limit|anti_detec|"
    r"smart_wait|digitar|typing|delay", re.I)

NOME_RETRY = re.compile(r"tentativa|retry|attempt", re.I)

# SISB/Core/ é o motor de baixo nível do SISBAJUD, onde mora a evasão de
# detecção. Fora do alcance do reescritor mecânico por inteiro.
PULAR = ("Fix/espera.py", "Fix/core.py", "SISB/Core/")


def _faixas_retry(arvore):
    """Linhas onde a espera é política de retry, não espera de UI.

    Detectado na árvore, não por regex de contexto: `except` cobre quase todo
    o código deste projeto, então buscar a palavra perto do sleep recusaria
    praticamente tudo. Aqui só conta estar *dentro* do handler ou de um laço
    de tentativa.
    """
    faixas = []
    for no in ast.walk(arvore):
        dentro = isinstance(no, ast.ExceptHandler)
        if isinstance(no, ast.For):
            alvo = getattr(no.target, "id", "")
            dentro = bool(NOME_RETRY.search(alvo))
        if dentro:
            faixas.append((no.lineno, no.end_lineno or no.lineno))
    return faixas


def _funcao_de(arvore, linha):
    """Função mais interna que contém `linha`, ou None."""
    melhor = None
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not (no.lineno <= linha <= (no.end_lineno or no.lineno)):
            continue
        if melhor is None or no.lineno > melhor.lineno:
            melhor = no
    return melhor


def _driver_no_escopo(melhor):
    """Nome de driver disponível na função, ou None."""
    if melhor is None:
        return None

    args = [a.arg for a in melhor.args.args]
    for nome in ("driver", "page", "d"):
        if nome in args:
            return nome
    if args and args[0] == "self":
        return "self.driver"
    return None


def arquivos():
    for alvo in ESCOPO:
        caminho = os.path.join(RAIZ, alvo)
        if alvo.endswith(".py"):
            if os.path.exists(caminho):
                yield caminho
            continue
        for dp, _, fs in os.walk(caminho):
            if "__pycache__" in dp:
                continue
            for f in fs:
                if f.endswith(".py"):
                    yield os.path.join(dp, f)


def processar(caminho, aplicar):
    rel = os.path.relpath(caminho, RAIZ).replace("\\", "/")
    if any(p in rel for p in PULAR):
        return [], []

    fonte = open(caminho, encoding="utf-8").read()
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        return [], [(rel, 0, "arquivo nao parseia")]

    linhas = fonte.splitlines()
    trocados, recusados = [], []
    faixas_retry = _faixas_retry(arvore)

    for i, ln in enumerate(linhas):
        m = SLEEP.match(ln)
        if not m:
            continue
        indent, valor = m.group(1), float(m.group(2))
        ctx = "\n".join(linhas[max(0, i - 5):i + 3])

        if THROTTLE.search(ctx):
            recusados.append((rel, i + 1, "throttle/anti-deteccao deliberado"))
            continue
        if any(ini <= i + 1 <= fim for ini, fim in faixas_retry):
            recusados.append((rel, i + 1, "espera de retry/backoff"))
            continue

        funcao = _funcao_de(arvore, i + 1)
        if funcao is not None and FUNCAO_DELIBERADA.search(funcao.name):
            recusados.append((rel, i + 1, f"espera deliberada em {funcao.name}()"))
            continue

        nome = _driver_no_escopo(funcao)
        if nome is None:
            recusados.append((rel, i + 1, "sem driver no escopo"))
            continue

        num = int(valor) if valor == int(valor) else valor
        linhas[i] = f"{indent}espera.assentar({nome}, {num})"
        trocados.append((rel, i + 1, valor))

    if trocados and aplicar:
        novo = "\n".join(linhas) + ("\n" if fonte.endswith("\n") else "")
        novo = _garantir_import(novo)
        open(caminho, "w", encoding="utf-8").write(novo)

    return trocados, recusados


def _garantir_import(fonte):
    """Insere `from Fix import espera` após o último import de topo (P8).

    Localizado pela árvore, não por regex: `import` dentro de função ou de
    string levaria a inserção para o lugar errado.
    """
    arvore = ast.parse(fonte)
    ultimo = None
    for no in arvore.body:  # só o topo do módulo
        if isinstance(no, (ast.Import, ast.ImportFrom)):
            if isinstance(no, ast.ImportFrom) and no.module == "Fix":
                if any(a.name == "espera" for a in no.names):
                    return fonte
            ultimo = no

    linhas = fonte.splitlines()
    pos = (ultimo.end_lineno if ultimo else 0)
    linhas.insert(pos, "from Fix import espera")
    return "\n".join(linhas) + "\n"


def main():
    aplicar = "--aplicar" in sys.argv
    todos_trocados, todos_recusados = [], []

    for caminho in sorted(arquivos()):
        t, r = processar(caminho, aplicar)
        todos_trocados += t
        todos_recusados += r

    out = io.StringIO()
    ganho = sum(v for _, _, v in todos_trocados)
    out.write(f"{'APLICADO' if aplicar else 'DRY-RUN'}\n\n")
    out.write(f"trocados : {len(todos_trocados):3d} sleeps  ({ganho:.1f}s de teto)\n")
    out.write(f"recusados: {len(todos_recusados):3d}\n\n")

    motivos = {}
    for _, _, motivo in todos_recusados:
        motivos[motivo] = motivos.get(motivo, 0) + 1
    for motivo, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
        out.write(f"  {n:3d}  {motivo}\n")

    por_arquivo = {}
    for rel, _, v in todos_trocados:
        a, b = por_arquivo.get(rel, (0, 0.0))
        por_arquivo[rel] = (a + 1, b + v)
    out.write("\npor arquivo:\n")
    for rel, (n, s) in sorted(por_arquivo.items(), key=lambda kv: -kv[1][1])[:18]:
        out.write(f"  {n:3d}  {s:6.1f}s  {rel}\n")

    sys.stdout.buffer.write(out.getvalue().encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
