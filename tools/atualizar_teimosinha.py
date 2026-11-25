# -*- coding: utf-8 -*-
r"""Pre-atualizador de calculos para atividades PEC vencidas do bucket 'sisbajud_teimosinha'.

1) Lista atividades vencidas do PEC via API e filtra pelo bucket 'sisbajud_teimosinha'
   (mesma regra de PEC/regras_execucao.py).
2) Consulta a divida mais recente de cada processo via API (/calculos/processo) e aplica
   a mesma regra de SISB/core.py (calculo_antigo: data de liquidacao > 45 dias).
3) Executa a atualizacao rapida no PJe-Calc (selecionar_mais_recente=True) para cada
   processo desatualizado e confirma o novo valor na API.

Uso:
  py tools/atualizar_teimosinha.py --dry-run      # somente lista todas as vencidas e mostra >45d
  py tools/atualizar_teimosinha.py                # atualiza todas as >45d sem limite de data (headless)
  py tools/atualizar_teimosinha.py --d1           # aplica filtro D-1 do PEC
  py tools/atualizar_teimosinha.py --limite 5     # limita quantidade de atualizacoes
  py tools/atualizar_teimosinha.py --visivel      # roda com janela visivel
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

RAIZ = Path(__file__).resolve().parent.parent
PLAY = RAIZ / "play"
for p in (str(RAIZ), str(PLAY)):
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger("atualizar_teimosinha")


def listar_teimosinhas_vencidas(
    driver: Any,
    *,
    filtro_d1: bool = False,
    data_minima: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Retorna processos unicos do bucket 'sisbajud_teimosinha' na fila vencida do PEC."""
    from PEC.regras_execucao import determinar_regra
    from PEC.runtime_pec import PECAPIClient, _dia_util_anterior

    atividades = PECAPIClient().fetch_atividades_vencidas(driver)
    if atividades is None:
        raise RuntimeError("Falha ao buscar atividades vencidas do PEC via API.")

    if data_minima:
        atividades = [a for a in atividades if (a.data_prazo or "")[:10] >= data_minima]
    elif filtro_d1:
        data_d1 = _dia_util_anterior(date.today()).isoformat()
        atividades = [a for a in atividades if (a.data_prazo or "")[:10] >= data_d1]

    unicos: dict[str, dict[str, Any]] = {}
    for atv in atividades:
        match = determinar_regra(atv.observacao or "")
        if not match or match[1] != "sisbajud_teimosinha":
            continue
        chave = str(atv.id_processo or atv.numero_processo or "")
        if not chave or chave in unicos:
            continue
        unicos[chave] = {
            "id_processo": atv.id_processo,
            "numero_processo": (atv.numero_processo or "").strip(),
            "observacao": (atv.observacao or "").strip(),
            "data_prazo": (atv.data_prazo or "")[:10],
        }
    return list(unicos.values())


def atualizar_teimosinhas_vencidas(
    driver: Any,
    *,
    dry_run: bool = False,
    filtro_d1: bool = False,
    data_minima: Optional[str] = None,
    limite: int = 0,
) -> dict[str, Any]:
    """Avalia cada TEIMOSINHA vencida e executa atualizacao rapida nos calculos > 45 dias."""
    from Fix import espera
    from Fix.atualizacao_rapida import (
        AtualizacaoRapidaErro,
        _divida_mais_recente_api,
        calculo_antigo,
        executar_atualizacao_rapida_detalhada,
    )

    teimosinhas = listar_teimosinhas_vencidas(
        driver, filtro_d1=filtro_d1, data_minima=data_minima
    )
    resumo: dict[str, Any] = {
        "total_teimosinha": len(teimosinhas),
        "em_dia": 0,
        "sem_calculo": 0,
        "pendentes_atualizacao": 0,
        "atualizados": 0,
        "erros": 0,
        "itens": [],
    }

    print(f"[TEIMOSINHA] {len(teimosinhas)} processo(s) TEIMOSINHA vencido(s) encontrado(s).")
    if not teimosinhas:
        return resumo

    executados = 0
    for idx, proc in enumerate(teimosinhas, 1):
        pid = proc["id_processo"]
        cnj = proc["numero_processo"]
        obs = proc["observacao"]

        divida = _divida_mais_recente_api(driver, pid) if pid else None
        if not divida or not divida.get("data"):
            resumo["sem_calculo"] += 1
            print(f"  [{idx}/{len(teimosinhas)}] {cnj} (id={pid}) | SEM_CALCULO (SISB usara R$ 33,33 + GIGS CALC) | obs={obs!r}")
            resumo["itens"].append({**proc, "status": "SEM_CALCULO"})
            continue

        data_div = divida["data"]
        valor_div = divida["valor"]
        precisa = calculo_antigo(data_div)
        if not precisa:
            resumo["em_dia"] += 1
            print(f"  [{idx}/{len(teimosinhas)}] {cnj} | EM_DIA ({valor_div} em {data_div}) | obs={obs!r}")
            resumo["itens"].append({**proc, "status": "EM_DIA", "antes": divida})
            continue

        resumo["pendentes_atualizacao"] += 1
        if dry_run:
            print(f"  [{idx}/{len(teimosinhas)}] {cnj} (id={pid}) | ATUALIZAR (>45d: {valor_div} em {data_div}) | obs={obs!r}")
            resumo["itens"].append({**proc, "status": "PRECISA_ATUALIZAR", "antes": divida})
            continue

        if limite > 0 and executados >= limite:
            print(f"  [{idx}/{len(teimosinhas)}] {cnj} | PULADO (limite={limite} atingido)")
            resumo["itens"].append({**proc, "status": "LIMITE", "antes": divida})
            continue

        executados += 1
        print(f"  [{idx}/{len(teimosinhas)}] {cnj} (id={pid}) | ATUALIZANDO (>45d: {valor_div} em {data_div})...")
        try:
            res_ar = executar_atualizacao_rapida_detalhada(
                driver, cnj, selecionar_mais_recente=True
            )
            nova = espera.ate(
                driver,
                lambda _d: (
                    c if (c := _divida_mais_recente_api(driver, pid))
                    and c.get("valor")
                    and not calculo_antigo(c.get("data", ""))
                    else None
                ),
                teto=25,
                intervalo=4,
            )
            resumo["atualizados"] += 1
            depois_txt = f"{nova['valor']} em {nova['data']}" if nova else f"calc {res_ar.numero_calculo} (aguardando propagacao API)"
            print(f"      -> OK: {valor_div} ({data_div}) => {depois_txt}")
            resumo["itens"].append({
                **proc,
                "status": "ATUALIZADO",
                "calculo": res_ar.numero_calculo,
                "antes": divida,
                "depois": nova,
            })
        except AtualizacaoRapidaErro as e:
            resumo["erros"] += 1
            print(f"      -> ERRO (fase={e.fase}, pos_envio={e.pos_envio}): {e}")
            resumo["itens"].append({
                **proc,
                "status": "ERRO",
                "antes": divida,
                "erro": str(e),
                "pos_envio": e.pos_envio,
            })
        except Exception as e:
            resumo["erros"] += 1
            print(f"      -> ERRO inesperado: {type(e).__name__}: {e}")
            resumo["itens"].append({**proc, "status": "ERRO", "antes": divida, "erro": str(e)})

    print(
        f"[RESUMO] total={resumo['total_teimosinha']} | em_dia={resumo['em_dia']} | "
        f"sem_calculo={resumo['sem_calculo']} | >45d={resumo['pendentes_atualizacao']} | "
        f"atualizados={resumo['atualizados']} | erros={resumo['erros']}"
    )
    return resumo


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-atualiza calculos (>45 dias) de atividades PEC vencidas do tipo TEIMOSINHA."
    )
    parser.add_argument("--dry-run", action="store_true", help="Apenas lista e verifica >45 dias sem atualizar")
    parser.add_argument("--d1", action="store_true", help="Restringe ao filtro D-1 do PEC (padrao: sem limite de data)")
    parser.add_argument("--data-minima", default=None, help="Data minima YYYY-MM-DD para prazo da atividade")
    parser.add_argument("--limite", type=int, default=0, help="Maximo de processos a atualizar (0 = todos)")
    parser.add_argument("--visivel", action="store_true", help="Abre Firefox visivel em vez de headless")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    import pjeplay
    pjeplay.iniciar(raiz_projeto=str(RAIZ), nativo=True, silencioso=True)

    from Fix.core import criar_driver_PC, finalizar_driver
    from Fix.sessao import login_cpf

    driver = criar_driver_PC(headless=not args.visivel)
    if not driver:
        print("ERRO: nao foi possivel criar driver Playwright Firefox.")
        return 1
    try:
        if not login_cpf(driver):
            print("ERRO: falha no login PJe.")
            return 1
        res = atualizar_teimosinhas_vencidas(
            driver,
            dry_run=args.dry_run,
            filtro_d1=args.d1,
            data_minima=args.data_minima,
            limite=args.limite,
        )
        return 0 if res["erros"] == 0 else 2
    finally:
        finalizar_driver(driver)


if __name__ == "__main__":
    raise SystemExit(main())
