"""Fix/telemetria_seletores.py — Registro empírico de seletores na execução real.

Problema que resolve
--------------------
O `CatalogoSeletores` já sabe qual seletor venceu, mas essa informação morria na
memória do processo: nenhum log de execução (mandado, p2b, pec) registrava o
vencedor. Sem esse dado, consolidar o catálogo vira adivinhação.

O que faz
---------
Grava, para cada resolução de seletor, uma linha JSON em
`logs_execucao/seletores_AAAAMMDD_HHMMSS.jsonl`:

    {"ts": "...", "fluxo": "mandado", "acao": "abrir_timeline",
     "seletor": "pje-timeline", "origem": "catalogo", "ok": true,
     "tentativas": 2, "ms": 43, "contexto": "mandado", "processo": "..."}

`origem` distingue:
    catalogo — veio do `executar_busca` do catálogo (seletor vencedor real)
    candidatos — chamada ad-hoc (seletor cru no código), via `resolver`

Uso
---
    from Fix.telemetria_seletores import registrar_resolucao, resolver

    # ad-hoc: testa candidatos em ordem e devolve o primeiro que existir
    el = resolver(driver, "mandado", "abrir_timeline",
                  ["pje-timeline", "//pje-timeline"], contexto="mandado")

Desligar: PJEPLUS_TELEMETRIA_SELETORES=0 (ligada por padrão).

Custo: uma escrita de linha por resolução, com buffer. Nunca levanta exceção —
telemetria não pode derrubar fluxo.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from Fix.log import logger

_ENABLED = os.getenv("PJEPLUS_TELEMETRIA_SELETORES", "1").lower() not in ("0", "false", "off", "no")
_DIR = os.getenv("PJEPLUS_LOG_DIR", "logs_execucao")
_LOCK = threading.Lock()
_ARQUIVO: Optional[str] = None
_ESTATISTICA: Dict[str, int] = {}


def _caminho() -> str:
    """Caminho do JSONL do processo atual (criado na primeira escrita)."""
    global _ARQUIVO
    if _ARQUIVO:
        return _ARQUIVO
    nome = "seletores_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".jsonl"
    _ARQUIVO = os.path.join(_DIR, nome)
    return _ARQUIVO


def registrar_resolucao(
    acao: str,
    seletor: Optional[str],
    *,
    fluxo: str = "",
    origem: str = "candidatos",
    ok: bool = True,
    tentativas: int = 1,
    ms: float = 0.0,
    contexto: str = "geral",
    processo: str = "",
    candidatos: Optional[List[str]] = None,
    erro: str = "",
) -> None:
    """Grava uma linha de telemetria. Nunca levanta (falha de escrita é ignorada)."""
    if not _ENABLED:
        return
    registro = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "fluxo": fluxo or contexto,
        "acao": acao,
        "seletor": seletor or "",
        "origem": origem,
        "ok": bool(ok),
        # nas buscas de DOM cada volta do polling conta; o que importa é se
        # achou e quanto tempo levou, então a contagem fica limitada
        "tentativas": min(int(tentativas), 99),
        "ms": round(ms, 1),
        "contexto": contexto,
        "processo": processo,
    }
    if candidatos:
        registro["candidatos"] = list(candidatos)
    if erro:
        registro["erro"] = erro[:300]

    with _LOCK:
        _ESTATISTICA["total"] = _ESTATISTICA.get("total", 0) + 1
        if ok:
            _ESTATISTICA["ok"] = _ESTATISTICA.get("ok", 0) + 1
        else:
            _ESTATISTICA["falha"] = _ESTATISTICA.get("falha", 0) + 1
        try:
            os.makedirs(_DIR, exist_ok=True)
            with open(_caminho(), "a", encoding="utf-8") as fp:
                fp.write(json.dumps(registro, ensure_ascii=False) + "\n")
        except Exception as e:  # telemetria nunca derruba o fluxo
            logger.debug("[telemetria] falha ao gravar: %s", e)


def resolver(
    driver: Any,
    fluxo: str,
    acao: str,
    candidatos: List[str],
    *,
    contexto: str = "geral",
    processo: str = "",
    condicao: str = "presente",
    teto_por_candidato: float = 2.0,
    testar: Optional[Callable[[str], Any]] = None,
) -> Optional[Any]:
    """Resolve um elemento testando `candidatos` em ordem, registrando o vencedor.

    É o substituto instrumentado do seletor cru: em vez de
    `esperar_elemento(driver, 'pje-timeline')`, chame

        resolver(driver, fluxo, 'abrir_timeline', ['pje-timeline', '//pje-timeline'])

    e a telemetria passa a saber qual candidato de fato existe no DOM real.

    `testar` permite injetar o teste (útil para fluxos com condição própria).
    """
    from Fix import espera

    def _padrao(sel: str) -> Any:
        if condicao == "visivel":
            return espera.elemento(driver, sel, teto=teto_por_candidato, visivel=True)
        return espera.elemento(driver, sel, teto=teto_por_candidato, visivel=False)

    fn = testar or _padrao
    inicio = time.perf_counter()
    tentativas = 0
    ultimo_erro = ""
    for sel in candidatos:
        tentativas += 1
        try:
            try:
                el = fn(sel)
            except TypeError as e_aridade:
                # aceita testadores no formato (driver, seletor, ...)
                if "positional argument" not in str(e_aridade):
                    raise
                el = fn(driver, sel)
        except Exception as e:
            ultimo_erro = str(e)
            el = None
        if el:
            registrar_resolucao(
                acao, sel, fluxo=fluxo, origem="candidatos", ok=True,
                tentativas=tentativas, ms=(time.perf_counter() - inicio) * 1000,
                contexto=contexto, processo=processo, candidatos=candidatos,
            )
            return el

    registrar_resolucao(
        acao, None, fluxo=fluxo, origem="candidatos", ok=False,
        tentativas=tentativas, ms=(time.perf_counter() - inicio) * 1000,
        contexto=contexto, processo=processo, candidatos=candidatos,
        erro=ultimo_erro or "nenhum candidato encontrado",
    )
    return None


def estatisticas() -> Dict[str, int]:
    """Contadores do processo atual (útil para resumo ao fim do fluxo)."""
    with _LOCK:
        return dict(_ESTATISTICA)


def resumo_vencedores() -> Dict[str, str]:
    """Mapa acao -> seletor vencedor observado nesta execução.

    Agrega o JSONL do processo; devolve {} se nada foi gravado.
    """
    vencedores: Dict[str, str] = {}
    if not _ARQUIVO or not os.path.exists(_ARQUIVO):
        return vencedores
    try:
        with open(_ARQUIVO, "r", encoding="utf-8") as fp:
            for linha in fp:
                try:
                    r = json.loads(linha)
                except Exception:
                    continue
                if r.get("ok") and r.get("seletor"):
                    vencedores[str(r.get("acao"))] = str(r.get("seletor"))
    except Exception:
        pass
    return vencedores
