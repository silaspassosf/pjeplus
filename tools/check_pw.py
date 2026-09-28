#!/usr/bin/env python3
"""
tools/check_pw.py — Ferramenta de trava (ratchet) para migração Playwright nativo.

Objetivo:
- Garantir que nenhum arquivo piore em relação ao baseline registrado em tools/pw_baseline.json;
- Arquivos que zerarem entram em 'migrados' e não podem regredir nunca mais;
- Fornece relatórios detalhados por módulo/arquivo.

Uso:
  py tools/check_pw.py                 # Verificação rápida (exit 0 se ok, exit 1 se regressão)
  py tools/check_pw.py --relatorio     # Relatório consolidado por pasta/domínio
  py tools/check_pw.py --arquivo <arq> # Detalha ocorrências de um arquivo específico
  py tools/check_pw.py --atualizar-baseline  # Grava novo baseline (apenas em fechamento de fase)
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = WORKSPACE_ROOT / "tools" / "pw_baseline.json"

EXCLUDE_DIRS = {
    ".venv", "venv", "worktrees", "outros projetos", "ORIGINAIS",
    ".git", "__pycache__", ".idea", ".vscode"
}

EXCLUDE_FILES = {
    "tools/check_pw.py",
}

PATTERNS = {
    "import_selenium": (re.compile(r"\bimport\s+selenium\b"), "import selenium"),
    "from_selenium": (re.compile(r"\bfrom\s+selenium\b"), "from selenium"),
    "find_element": (re.compile(r"\.find_element\b"), "driver.find_element"),
    "find_elements": (re.compile(r"\.find_elements\b"), "driver.find_elements"),
    "execute_script": (re.compile(r"\.execute_script\b"), "driver.execute_script"),
    "send_keys": (re.compile(r"\.send_keys\b"), "driver.send_keys"),
    "window_handles": (re.compile(r"\.window_handles\b"), "driver.window_handles"),
    "webdriver_wait": (re.compile(r"\bWebDriverWait\b"), "WebDriverWait"),
    "expected_conditions": (re.compile(r"(\bexpected_conditions\b|\bEC\.)"), "expected_conditions"),
    "time_sleep": (re.compile(r"\btime\.sleep\s*\("), "time.sleep"),
    "webdriver_type": (re.compile(r"(:\s*WebDriver\b|->\s*WebDriver\b)"), "tipagem WebDriver"),
}


def scan_file(filepath: Path) -> Tuple[int, Dict[str, int], List[Tuple[int, str, str]]]:
    """
    Escaneia um arquivo Python e retorna:
    (total_ocorrencias, contagem_por_padrao, lista_de_ocorrencias_detalhadas)
    """
    total = 0
    counts = {k: 0 for k in PATTERNS}
    details: List[Tuple[int, str, str]] = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
            for idx, line in enumerate(fp, start=1):
                # Ignora a parte comentada da linha para evitar falso-positivo em narração/docs
                code_part = line.split("#")[0]
                if not code_part.strip():
                    continue

                for pat_key, (regex, label) in PATTERNS.items():
                    matches = regex.findall(code_part)
                    if matches:
                        cnt = len(matches)
                        counts[pat_key] += cnt
                        total += cnt
                        details.append((idx, label, line.strip()))
    except Exception as e:
        print(f"[ERRO] Falha ao ler {filepath}: {e}", file=sys.stderr)

    return total, counts, details


def scan_workspace() -> Dict[str, Dict[str, Any]]:
    """
    Escaneia todos os arquivos .py do workspace e retorna um dict:
    { rel_path: {"total": int, "breakdown": dict, "details": list} }
    """
    results: Dict[str, Dict[str, Any]] = {}

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Filtra diretórios excluídos
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue

            full_path = Path(root) / fname
            rel_path = full_path.relative_to(WORKSPACE_ROOT).as_posix()

            if rel_path in EXCLUDE_FILES:
                continue

            total, counts, details = scan_file(full_path)
            results[rel_path] = {
                "total": total,
                "breakdown": counts,
                "details": details,
            }

    return results


def carregar_baseline() -> Dict[str, Any]:
    if not BASELINE_PATH.is_file():
        return {"files": {}, "migrados": []}
    try:
        with open(BASELINE_PATH, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar {BASELINE_PATH}: {e}", file=sys.stderr)
        return {"files": {}, "migrados": []}


def salvar_baseline(scan_data: Dict[str, Dict[str, Any]], migrados: List[str] = None) -> None:
    if migrados is None:
        # Preserva migrados anteriores ou inicializa vazio
        atual_base = carregar_baseline()
        migrados = atual_base.get("migrados", [])

    # Todos os arquivos que possuem 0 e já estavam em migrados continuam em migrados
    # Arquivos que tinham padrões e agora estão com 0 entram em migrados
    migrados_set = set(migrados)

    files_dict: Dict[str, Any] = {}
    for rel_path, data in sorted(scan_data.items()):
        total = data["total"]
        if total > 0:
            active_breakdown = {k: v for k, v in data["breakdown"].items() if v > 0}
            files_dict[rel_path] = {
                "total": total,
                "breakdown": active_breakdown,
            }
        else:
            # Se zerou e estava no baseline antigo ou ja em migrados, promove para migrados
            base_files_antigo = atual_base.get("files", {})
            if rel_path in base_files_antigo or rel_path in migrados_set:
                migrados_set.add(rel_path)

    payload = {
        "version": "1.0",
        "description": "Baseline de migracao Playwright nativo (ratchet)",
        "total_files": len(scan_data),
        "files_with_patterns": len(files_dict),
        "total_patterns": sum(d["total"] for d in files_dict.values()),
        "migrados": sorted(migrados_set),
        "files": files_dict,
    }

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, ensure_ascii=False)
    print(f"[OK] Baseline atualizado em {BASELINE_PATH} com {len(files_dict)} arquivos com ocorrencias e {len(migrados_set)} migrados.")


def executar_verificacao(scan_data: Dict[str, Dict[str, Any]], baseline: Dict[str, Any]) -> int:
    """
    Compara o scan atual com o baseline.
    Retorna 0 se OK (sem regressões), 1 se houver regressão.
    """
    base_files = baseline.get("files", {})
    migrados = set(baseline.get("migrados", []))

    regressoes = []
    melhorias = []
    zerados_novos = []
    novos_nao_registrados = []

    for rel_path, data in sorted(scan_data.items()):
        total_hoje = data["total"]

        # 1. Arquivo estava em 'migrados'? Não pode ter nada > 0!
        if rel_path in migrados:
            if total_hoje > 0:
                regressoes.append((rel_path, total_hoje, 0, "ARQUIVO MIGRADO REGREDIU!"))
            continue

        # 2. Arquivo está registrado no baseline?
        if rel_path in base_files:
            base_entry = base_files[rel_path]
            base_total = base_entry if isinstance(base_entry, int) else base_entry.get("total", 0)

            if total_hoje > base_total:
                regressoes.append((rel_path, total_hoje, base_total, "Piorou"))
            elif total_hoje < base_total:
                if total_hoje == 0:
                    zerados_novos.append((rel_path, total_hoje, base_total, "ZEROU! (pronto para migrados)"))
                else:
                    melhorias.append((rel_path, total_hoje, base_total, "Melhorou"))
        else:
            # Arquivo não estava no baseline
            if total_hoje > 0:
                novos_nao_registrados.append((rel_path, total_hoje, 0, "Novo arquivo com padrões proibidos"))

    # Relatório de Execução
    print("=" * 70)
    print("VERIFICAÇÃO DE PADRÕES PLAYWRIGHT NATIVO (RATCHET)")
    print("=" * 70)

    if regressoes:
        print(f"\n[REGRESSAO] REGRESSOES ENCONTRADAS ({len(regressoes)}):")
        for rel_path, hoje, base, status in regressoes:
            print(f"  {rel_path} — hoje {hoje} (baseline {base}) — [FALHA: {status}]")

    if novos_nao_registrados:
        print(f"\n[NOVO-PROIBIDO] NOVOS ARQUIVOS COM PADROES PROIBIDOS ({len(novos_nao_registrados)}):")
        for rel_path, hoje, base, status in novos_nao_registrados:
            print(f"  {rel_path} — hoje {hoje} (baseline {base}) — [FALHA: {status}]")

    if zerados_novos:
        print(f"\n[MIGRADO] ARQUIVOS QUE ZERARAM ({len(zerados_novos)}):")
        for rel_path, hoje, base, status in zerados_novos:
            print(f"  {rel_path} — hoje 0 (baseline {base}) — [MIGRADO!]")

    if melhorias:
        print(f"\n[MELHORIA] ARQUIVOS QUE MELHORARAM ({len(melhorias)}):")
        for rel_path, hoje, base, status in melhorias:
            print(f"  {rel_path} — hoje {hoje} (baseline {base}) — [MELHORIA]")

    total_base = baseline.get("total_patterns", 0)
    total_hoje = sum(d["total"] for d in scan_data.values())

    print("\n" + "-" * 70)
    print(f"Total de padroes: hoje {total_hoje} | baseline {total_base} (diferenca: {total_hoje - total_base:+d})")
    print(f"Arquivos migrados garantidos: {len(migrados)}")
    print("-" * 70)

    if regressoes or novos_nao_registrados:
        print("\n[FALHA] VEREDITO: FALHA — Regressao detectada contra o baseline!")
        return 1

    print("\n[OK] VEREDITO: APROVADO — Nenhuma regressao detectada.")
    return 0


def imprimir_relatorio(scan_data: Dict[str, Dict[str, Any]], baseline: Dict[str, Any]) -> None:
    """Imprime relatório agrupado por diretório."""
    pastas: Dict[str, List[Tuple[str, int, int]]] = {}
    base_files = baseline.get("files", {})

    for rel_path, data in sorted(scan_data.items()):
        total_hoje = data["total"]
        base_entry = base_files.get(rel_path, {})
        base_total = base_entry if isinstance(base_entry, int) else base_entry.get("total", 0)

        top_dir = rel_path.split("/")[0] if "/" in rel_path else "(raiz)"
        pastas.setdefault(top_dir, []).append((rel_path, total_hoje, base_total))

    print("=" * 80)
    print(f"{'PASTA / MÓDULO':<25} {'ARQUIVOS':<10} {'HOJE':<10} {'BASELINE':<10} {'STATUS'}")
    print("=" * 80)

    total_geral_hoje = 0
    total_geral_base = 0

    for pasta, itens in sorted(pastas.items()):
        soma_hoje = sum(i[1] for i in itens)
        soma_base = sum(i[2] for i in itens)
        com_padroes = sum(1 for i in itens if i[1] > 0)
        total_geral_hoje += soma_hoje
        total_geral_base += soma_base

        diff = soma_hoje - soma_base
        status_str = "OK" if diff <= 0 else f"+{diff} REGRESSÃO!"
        if soma_hoje == 0:
            status_str = "LIMPO"

        print(f"{pasta:<25} {len(itens):<10} {soma_hoje:<10} {soma_base:<10} {status_str}")

    print("=" * 80)
    print(f"{'TOTAL GERAL':<25} {len(scan_data):<10} {total_geral_hoje:<10} {total_geral_base:<10}")
    print("=" * 80)


def detalhar_arquivo(scan_data: Dict[str, Dict[str, Any]], caminho_alvo: str) -> None:
    norm_alvo = Path(caminho_alvo).as_posix().replace("\\", "/")
    # Permite match parcial ou relativo
    encontrado = None
    for k in scan_data:
        if k == norm_alvo or k.endswith(norm_alvo):
            encontrado = k
            break

    if not encontrado:
        print(f"[ERRO] Arquivo não encontrado no scan: {caminho_alvo}")
        sys.exit(1)

    data = scan_data[encontrado]
    print("=" * 70)
    print(f"DETALHAMENTO: {encontrado}")
    print(f"Total de padrões: {data['total']}")
    print("=" * 70)
    print("Breakdown:")
    for pat_key, cnt in data["breakdown"].items():
        if cnt > 0:
            print(f"  - {PATTERNS[pat_key][1]}: {cnt}")

    if data["details"]:
        print("\nOcorrências (linha: padrão | snippet):")
        for lineno, label, snippet in data["details"]:
            print(f"  L{lineno:4d} [{label}]: {snippet[:80]}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Verificador de padrões Selenium (Ratchet Playwright)")
    parser.add_argument("--relatorio", action="store_true", help="Exibe relatório consolidado por pasta")
    parser.add_argument("--atualizar-baseline", action="store_true", help="Atualiza tools/pw_baseline.json com os dados atuais")
    parser.add_argument("--arquivo", type=str, help="Detalha ocorrências de um arquivo específico")

    args = parser.parse_args()

    scan_data = scan_workspace()

    if args.atualizar_baseline:
        salvar_baseline(scan_data)
        sys.exit(0)

    baseline = carregar_baseline()
    if not baseline.get("files") and not BASELINE_PATH.is_file():
        print("[AVISO] tools/pw_baseline.json não encontrado. Criando baseline inicial...")
        salvar_baseline(scan_data)
        baseline = carregar_baseline()

    if args.arquivo:
        detalhar_arquivo(scan_data, args.arquivo)
        sys.exit(0)

    if args.relatorio:
        imprimir_relatorio(scan_data, baseline)

    ret = executar_verificacao(scan_data, baseline)
    sys.exit(ret)


if __name__ == "__main__":
    main()
