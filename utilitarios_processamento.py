#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTILITÁRIOS DE PROCESSAMENTO

Funções utilitárias para processamento iterativo com tratamento padronizado de erros.
Este arquivo foi separado para evitar dependências circulares entre módulos.
"""

import logging
from typing import Dict, Any, Callable, List, Optional, TypeVar
import threading
import queue

logger = logging.getLogger(__name__)


def executar_processamento_iterativo_com_corte_em_erro_critico(
    driver,
    nome_modulo: str,
    lista_itens,
    funcao_processamento_item,
    max_tentativas_recuperacao: int = 2,
    stop_on_critical: bool = True
) -> Dict[str, Any]:
    """
    Executa processamento iterativo com interrupção automática em erros críticos.

    Esta função padroniza o tratamento de erros em todos os módulos que fazem
    processamento em lote, evitando poluição do log com mensagens repetidas.

    Args:
        driver: WebDriver instance
        nome_modulo: Nome do módulo para logging (ex: "DOM", "P2B", "MANDADO")
        lista_itens: Lista de itens a processar (pode ser dict ou list)
        funcao_processamento_item: Função que processa um item individual
        max_tentativas_recuperacao: Máximo de tentativas para recuperação de acesso negado

    Returns:
        Dict com resultados: {"processados": int, "erros": int, "interrompido_por_erro_critico": bool}

    Exemplo de uso:
        def processar_um_processo(driver, proc_id, linha):
            # lógica específica do módulo
            return True

        resultados = executar_processamento_iterativo_com_corte_em_erro_critico(
            driver=driver,
            nome_modulo="DOM",
            lista_itens=processos_dict,
            funcao_processamento_item=lambda driver, item: processar_um_processo(driver, item['id'], item['linha'])
        )
    """
    processados = 0
    erros = 0
    interrompido_por_erro_critico = False

    logger.info(f'[{nome_modulo}] Iniciando processamento de {len(lista_itens)} itens')

    for idx, item in enumerate(lista_itens):
        # Determinar ID do item para logging
        if isinstance(item, dict) and 'id' in item:
            item_id = item['id']
        elif isinstance(item, tuple) and len(item) >= 1:
            item_id = str(item[0])  # Assume que primeiro elemento é ID
        else:
            item_id = f"item_{idx+1}"

        logger.info(f'[{nome_modulo}] Processando {idx+1}/{len(lista_itens)}: {item_id}')

        try:
            # Executar função de processamento do item com timeout para evitar bloqueio
            result_queue = queue.Queue()

            def _run_item():
                try:
                    res = funcao_processamento_item(driver, item)
                    result_queue.put(('ok', res))
                except Exception as ex:
                    result_queue.put(('exc', ex))

            t = threading.Thread(target=_run_item, daemon=True)
            t.start()

            # timeout por item (segundos) - evita que um item trave toda a sequência
            ITEM_TIMEOUT = 60
            try:
                kind, payload = result_queue.get(timeout=ITEM_TIMEOUT)
            except queue.Empty:
                erros += 1
                logger.error(f'[{nome_modulo}] Timeout ({ITEM_TIMEOUT}s) ao processar {item_id} - interrompendo para evitar bloqueio')
                if stop_on_critical:
                    interrompido_por_erro_critico = True
                    break
                else:
                    # registrar e continuar com próximo item
                    logger.warning(f'[{nome_modulo}] Continuando após timeout em {item_id} (stop_on_critical=False)')
                    continue

            if kind == 'exc':
                erros += 1
                error_msg = str(payload)
                logger.error(f'[{nome_modulo}] Erro geral no processamento de {item_id}: {error_msg}')
                # DETECÇÃO DE ERROS CRÍTICOS será avaliada abaixo
                error_msg = error_msg
            else:
                resultado = payload
                if resultado:
                    processados += 1
                    logger.info(f'[{nome_modulo}] Item {item_id} processado com sucesso')
                else:
                    erros += 1
                    logger.error(f'[{nome_modulo}] Falha no processamento de {item_id}')

        except Exception as e:
            erros += 1
            error_msg = str(e)
            logger.error(f'[{nome_modulo}] Erro geral no processamento de {item_id}: {error_msg}')

            # DETECÇÃO DE ERROS CRÍTICOS - Interromper processamento para evitar poluição do log
            erros_criticos = [
                "takes 0 positional arguments but 1 was given",  # Erro de assinatura de função
                "RESTART_DRIVER",  # Driver restart forçado
                "Unable to locate element",  # Elemento não encontrado (estrutura mudou)
                "SessionNotCreatedException",  # Sessão do driver inválida
                "WebDriverException.*invalid session",  # Sessão expirada
                "Browsing context has been discarded",  # Contexto de navegação perdido (aba fechada)
                "chrome not reachable",  # Chrome não acessível
                "disconnected",  # Conexão perdida
                "connection refused",  # Conexão recusada
                "timeout",  # Timeout geral
                "RESTART_PEC",  # Reinício específico do PEC
                "RESTART_PRAZO",  # Reinício específico do Prazo
                "RESTART_MANDADO",  # Reinício específico do Mandado
            ]

            if any(critico in error_msg for critico in erros_criticos):
                logger.error(f'[{nome_modulo}] ERRO CRÍTICO detectado: {error_msg}')
                logger.error(f'[{nome_modulo}] Último erro crítico: {error_msg}')
                if stop_on_critical:
                    logger.error(f'[{nome_modulo}] Interrompendo processamento por erro crítico')
                    interrompido_por_erro_critico = True
                    break
                else:
                    logger.warning(f'[{nome_modulo}] Continuando após erro crítico em {item_id} (stop_on_critical=False)')
                    continue

            continue

    logger.info(f'[{nome_modulo}] Processamento concluído: {processados} sucesso, {erros} erros')
    if interrompido_por_erro_critico:
        logger.warning(f'[{nome_modulo}] Processamento interrompido por erro crítico - verifique e corrija antes de continuar')

    return {
        "processados": processados,
        "erros": erros,
        "interrompido_por_erro_critico": interrompido_por_erro_critico,
        "total_itens": len(lista_itens),
        "sucessos": processados,  # Alias para compatibilidade
        "erros": erros,  # Alias para compatibilidade
    }


# ======================================================================
# Engine genérico de processamento por processo (Phase 3 / Task 7)
# ======================================================================

T = TypeVar("T")

ActionResult = Dict[str, Any]
BatchResult = Dict[str, Any]


def resultado_ok(**dados: Any) -> ActionResult:
    """Retorna dict padronizado de resultado bem-sucedido.

    Returns:
        {"ok": True, "erro": None, "dados": dict|None}
    """
    return {"ok": True, "erro": None, "dados": dados if dados else None}


def resultado_falha(erro: str, **dados: Any) -> ActionResult:
    """Retorna dict padronizado de resultado com falha.

    Args:
        erro: Mensagem de erro descritiva.
        **dados: Dados adicionais para contexto.

    Returns:
        {"ok": False, "erro": str, "dados": dict|None}
    """
    return {"ok": False, "erro": erro, "dados": dados if dados else None}


def _extrair_numero(item: Any) -> Optional[str]:
    """Extrai número de processo de um item (dict ou string)."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return (
            item.get("numero")
            or item.get("numeroProcesso")
            or str(item.get("id", ""))
        )
    return None


def create_skip_checker(tipo: str) -> Callable[[Any], bool]:
    """Cria função should_skip baseada no arquivo de progresso unificado.

    A função carrega o progresso do tipo especificado via
    Fix.monitoramento_progresso_unificado e retorna True para itens
    cujo número de processo já consta como executado com sucesso.

    Args:
        tipo: Chave de seção no progresso.json ('mandado', 'pec',
              'triagem', 'p2b', 'm1', etc.).

    Returns:
        Callable que recebe um item e retorna bool: True se deve pular.
    """
    from Fix.monitoramento_progresso_unificado import (
        carregar_progresso_unificado,
        processo_ja_executado_unificado,
    )

    progresso = carregar_progresso_unificado(tipo)

    def should_skip(item: Any) -> bool:
        numero = _extrair_numero(item)
        if not numero:
            return False
        return processo_ja_executado_unificado(numero, progresso)

    return should_skip


def run_batch(
    items: List[T],
    should_skip: Callable[[T], bool],
    open_item: Callable[[T], ActionResult],
    execute_item: Callable[[T], ActionResult],
    persist_result: Callable[[T, ActionResult], None],
    progress_callback: Optional[Callable[[int, int, T, ActionResult], None]] = None,
    stop_on_critical: bool = False,
) -> BatchResult:
    """Executa pipeline de processamento sobre uma lista de itens.

    Pipeline para cada item:
      1. should_skip(item) — se True, registra como pulado e continua.
      2. open_item(item) — navega/abre o processo. Se falhar (ok=False),
         a execução do item é interrompida e persist_result recebe o erro.
      3. execute_item(item) — executa a ação principal. Só chamado se
         open_item retornou ok=True.
      4. persist_result(item, result) — persiste o resultado final
         (chamado tanto em caso de sucesso quanto de falha).

    Args:
        items: Lista de itens a processar.
        should_skip: Retorna True se o item deve ser pulado.
        open_item: Abre/navega para o processo. Retorna ActionResult.
        execute_item: Executa a ação principal sobre o processo aberto.
            Retorna ActionResult.
        persist_result: Persiste o resultado no mecanismo de progresso.
            Recebe o item e o ActionResult da etapa que falhou ou de
            execute_item em caso de sucesso.
        progress_callback: Opcional, chamado após cada item processado.
            Assinatura: (idx, total, item, result_acao)

    Returns:
        Dict padronizado:
            sucesso  (int) — itens com sucesso em todas as etapas.
            falha    (int) — itens com erro em open_item ou execute_item.
            pulados  (int) — itens pulados via should_skip.
            total    (int) — total de itens recebidos.
            itens    (list[dict]) — registros individuais:
                {"item": T, "status": "sucesso"|"falha"|"pulado",
                 "erro": str|None}
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
                if progress_callback:
                    progress_callback(idx, len(items), item, resultado_ok(skipped=True))
                continue
        except Exception as e:
            stats["falha"] += 1
            stats["itens"].append(
                {"item": item, "status": "falha", "erro": f"should_skip: {e}"}
            )
            if progress_callback:
                progress_callback(idx, len(items), item, resultado_falha(str(e)))
            continue

        # 2. Abrir item
        try:
            open_result = open_item(item)
            if not open_result.get("ok"):
                stats["falha"] += 1
                err = open_result.get("erro") or "open_item falhou"
                stats["itens"].append(
                    {"item": item, "status": "falha", "erro": err}
                )
                _safe_persist(persist_result, item, open_result)
                if progress_callback:
                    progress_callback(idx, len(items), item, open_result)
                if stop_on_critical and (open_result.get("dados") or {}).get("critical"):
                    logger.warning("[ENGINE] parada antecipada por erro critico em open_item: %s", err)
                    stats["critical_stop"] = True
                    stats["critical_reason"] = err
                    break
                continue
        except Exception as e:
            stats["falha"] += 1
            err = str(e)
            stats["itens"].append(
                {"item": item, "status": "falha", "erro": f"open_item: {err}"}
            )
            _safe_persist(persist_result, item, resultado_falha(err))
            if progress_callback:
                progress_callback(idx, len(items), item, resultado_falha(err))
            continue

        # 3. Executar ação principal
        try:
            exec_result = execute_item(item)
            if not exec_result.get("ok"):
                stats["falha"] += 1
                err = exec_result.get("erro") or "execute_item falhou"
                stats["itens"].append(
                    {"item": item, "status": "falha", "erro": err}
                )
                _safe_persist(persist_result, item, exec_result)
                if progress_callback:
                    progress_callback(idx, len(items), item, exec_result)
                if stop_on_critical and (exec_result.get("dados") or {}).get("critical"):
                    logger.warning("[ENGINE] parada antecipada por erro critico em execute_item: %s", err)
                    stats["critical_stop"] = True
                    stats["critical_reason"] = err
                    break
                continue
        except Exception as e:
            stats["falha"] += 1
            err = str(e)
            stats["itens"].append(
                {"item": item, "status": "falha", "erro": f"execute_item: {err}"}
            )
            _safe_persist(persist_result, item, resultado_falha(err))
            if progress_callback:
                progress_callback(idx, len(items), item, resultado_falha(err))
            continue

        # 4. Sucesso — todas as etapas ok
        stats["sucesso"] += 1
        stats["itens"].append(
            {"item": item, "status": "sucesso", "erro": None}
        )
        _safe_persist(persist_result, item, exec_result)

        if progress_callback:
            progress_callback(idx, len(items), item, exec_result)

    return stats


def _safe_persist(
    persist_result: Callable[[T, ActionResult], None],
    item: T,
    result: ActionResult,
) -> None:
    """Executa persist_result de forma segura, ignorando exceções."""
    try:
        persist_result(item, result)
    except Exception as e:
        logger.warning(f"[ENGINE] persist_result falhou: {e}")