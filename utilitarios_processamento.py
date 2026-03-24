#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTILITÁRIOS DE PROCESSAMENTO

Funções utilitárias para processamento iterativo com tratamento padronizado de erros.
Este arquivo foi separado para evitar dependências circulares entre módulos.
"""

import logging
from typing import Dict, Any, Callable, List
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