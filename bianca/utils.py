# -*- coding: utf-8 -*-
"""
bianca/utils.py - Utilitarios base para o projeto bianca.

Contem implementacoes autocontidas de:
  - logger padrao do modulo
  - Tipagem ResultadoFluxo e funcoes resultado_ok / resultado_falha
  - RuleRegistry (registro de regras regex)
  - run_batch (processador generico em lote)

Nenhuma dependencia externa ao modulo bianca.
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("bianca")

# =============================================================================
# Tipos genericos
# =============================================================================

T = TypeVar("T")
ActionResult = Dict[str, Any]
BatchResult = Dict[str, Any]

# =============================================================================
# resultado_ok / resultado_falha
# =============================================================================


def resultado_ok(**dados: Any) -> ActionResult:
    """Retorna dict padronizado de resultado bem-sucedido.

    Returns:
        ``{"ok": True, "erro": None, "dados": dict|None}``
    """
    return {"ok": True, "erro": None, "dados": dados if dados else None}


def resultado_falha(erro: str, **dados: Any) -> ActionResult:
    """Retorna dict padronizado de resultado com falha.

    Args:
        erro: Mensagem de erro descritiva.
        **dados: Dados adicionais para contexto.

    Returns:
        ``{"ok": False, "erro": erro, "dados": dict|None}``
    """
    return {"ok": False, "erro": erro, "dados": dados if dados else None}


# =============================================================================
# RuleRegistry
# =============================================================================


class RuleRegistry:
    """Registry de regras regex para deteccao de alertas / triagem.

    Uso::

        registry = RuleRegistry()
        registry.add_rule(r"pattern", "bucket_a", "descricao da regra")
        match = registry.check("texto a ser analisado")
    """

    def __init__(self) -> None:
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, pattern: str, bucket: str, descricao: str) -> None:
        """Registra uma regra: pattern regex, bucket de classificacao e
        descricao textual.

        Args:
            pattern: Expressao regular (compilada com ``re.IGNORECASE``).
            bucket: Nome do bucket / categoria.
            descricao: Descricao textual da regra.
        """
        self._rules.append(
            {
                "pattern": re.compile(pattern, re.IGNORECASE),
                "bucket": bucket,
                "descricao": descricao,
            }
        )

    def all_rules(self) -> List[Dict[str, Any]]:
        """Retorna copia da lista de regras registradas."""
        return list(self._rules)

    def check(self, texto: str) -> Optional[Dict[str, Any]]:
        """Verifica *texto* contra todas as regras.

        Retorna a primeira correspondencia encontrada ou ``None``.

        Returns:
            ``{"bucket": str, "descricao": str}`` ou ``None`` se nenhuma
            regra corresponder.
        """
        if not texto:
            return None
        for rule in self._rules:
            if rule["pattern"].search(texto):
                return {"bucket": rule["bucket"], "descricao": rule["descricao"]}
        return None


# =============================================================================
# run_batch
# =============================================================================


def _safe_persist(
    persist_result: Callable[[T, ActionResult], None],
    item: T,
    result: ActionResult,
) -> None:
    """Executa ``persist_result`` de forma segura, ignorando excecoes."""
    try:
        persist_result(item, result)
    except Exception as e:
        logger.warning("[ENGINE] persist_result falhou: %s", e)


def run_batch(
    items: List[T],
    should_skip: Callable[[T], bool],
    open_item: Callable[[T], Any],
    execute_item: Callable[[T, Any], ActionResult],
    persist_result: Callable[[T, ActionResult], None],
    label: str = "processando",
    stop_on_critical: bool = False,
) -> BatchResult:
    """Executa pipeline de processamento sobre uma lista de itens.

    Pipeline para cada item::

        1. should_skip(item)        -> True: registra como pulado e continua.
        2. open_item(item)          -> Any: contexto do item aberto.
        3. execute_item(item, open_result)
                                    -> Dict{"ok": bool, ...}: acao principal.
        4. persist_result(item, result)
                                    -> None: persiste o resultado final.

    ``persist_result`` e chamado tanto em caso de sucesso quanto de falha
    (mas nao para itens pulados).

    Args:
        items: Lista de itens a processar.
        should_skip: Retorna ``True`` se o item deve ser pulado.
        open_item: Abre/navega para o processo. Retorna ``Any`` (contexto).
        execute_item: Executa a acao principal. Recebe o item e o retorno
            de ``open_item``. Deve retornar um dict com a chave ``"ok"``.
        persist_result: Persiste o resultado. Recebe o item e o
            ``ActionResult`` da etapa que falhou ou de ``execute_item`` em
            caso de sucesso.
        label: Nome do modulo para logging (ex: ``"TRIAGEM"``, ``"DOM"``).

    Returns:
        Dict padronizado::

            sucesso  (int) — itens com sucesso em todas as etapas.
            falha    (int) — itens com erro em ``open_item`` ou ``execute_item``.
            pulados  (int) — itens pulados via ``should_skip``.
            total    (int) — total de itens recebidos.
            itens    (list[dict]) — registros individuais:
                ``{"item": T, "status": "sucesso"|"falha"|"pulado",
                  "erro": str|None}``
    """
    stats: BatchResult = {
        "sucesso": 0,
        "falha": 0,
        "pulados": 0,
        "total": len(items),
        "itens": [],
        "critical_stop": False,
        "critical_reason": None,
    }

    for idx, item in enumerate(items, 1):
        # 1. Verificar skip
        try:
            if should_skip(item):
                stats["pulados"] += 1
                stats["itens"].append(
                    {"item": item, "status": "pulado", "erro": None}
                )
                continue
        except Exception as e:
            stats["falha"] += 1
            logger.error(
                "[%s] should_skip falhou item %d/%d: %s",
                label,
                idx,
                len(items),
                e,
            )
            stats["itens"].append(
                {"item": item, "status": "falha", "erro": f"should_skip: {e}"}
            )
            continue

        # 2. Abrir item
        try:
            open_result = open_item(item)
        except Exception as e:
            stats["falha"] += 1
            err = str(e)
            logger.error(
                "[%s] open_item falhou item %d/%d: %s",
                label,
                idx,
                len(items),
                err,
            )
            stats["itens"].append(
                {"item": item, "status": "falha", "erro": f"open_item: {err}"}
            )
            _safe_persist(persist_result, item, resultado_falha(err))
            continue

        # 3. Executar acao principal
        try:
            exec_result = execute_item(item, open_result)
            if not exec_result.get("ok"):
                stats["falha"] += 1
                err = exec_result.get("erro") or "execute_item falhou"
                stats["itens"].append(
                    {"item": item, "status": "falha", "erro": err}
                )
                _safe_persist(persist_result, item, exec_result)
                if stop_on_critical and exec_result.get("critical"):
                    stats["critical_stop"] = True
                    stats["critical_reason"] = err
                    logger.warning("[%s] Parada critica: %s", label, err)
                    break
                continue
        except Exception as e:
            stats["falha"] += 1
            err = str(e)
            logger.error(
                "[%s] execute_item falhou item %d/%d: %s",
                label,
                idx,
                len(items),
                err,
            )
            stats["itens"].append(
                {"item": item, "status": "falha", "erro": f"execute_item: {err}"}
            )
            _safe_persist(persist_result, item, resultado_falha(err))
            continue

        # 4. Sucesso — todas as etapas ok
        stats["sucesso"] += 1
        stats["itens"].append(
            {"item": item, "status": "sucesso", "erro": None}
        )
        _safe_persist(persist_result, item, exec_result)

    logger.info(
        "[%s] Batch concluido: %d sucesso, %d falha, %d pulados (total %d)",
        label,
        stats["sucesso"],
        stats["falha"],
        stats["pulados"],
        stats["total"],
    )

    return stats
