import logging
logger = logging.getLogger(__name__)

import os
import time
from typing import Optional, Dict, List, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import StaleElementReferenceException

# Garantir pasta de logs para watchdog
LOG_DIR = 'logs_execucao'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

from utilitarios_processamento import executar_processamento_iterativo_com_corte_em_erro_critico

from .core import (
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
    verificar_acesso_negado_pec,
)
from .regras import determinar_acoes_por_observacao, executar_acao_pec

from Fix.extracao import abrir_detalhes_processo, trocar_para_nova_aba, reindexar_linha
from Fix.monitoramento_progresso_unificado import executar_com_monitoramento_unificado


def fluxo_pec_bucket(driver: WebDriver, bucket: Dict[str, Any]) -> bool:
    """Compatibilidade: executa a ação do bucket no processo já aberto."""
    try:
        observacao = (bucket or {}).get('observacao', '') if isinstance(bucket, dict) else ''
        acoes = determinar_acoes_por_observacao(observacao) if observacao else None
        acao = acoes[0] if isinstance(acoes, list) and acoes else acoes
        return executar_acao_pec(driver, acao, observacao=observacao, debug=False)
    except Exception as e:
        logger.error(f"[PEC_BUCKET] Erro ao executar fluxo_pec_bucket: {e}")
        return False


def _processar_buckets(driver: WebDriver, buckets: dict[str, list[dict[str, any]]], progresso: dict[str, any]) -> bool:
    """Helper: Processa todos os buckets na ordem correta."""
    total_results: dict[str, int] = {'sucesso': 0, 'erro': 0}

    # Processar buckets não-SISBAJUD
    for name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento']:
        bucket: List[Dict[str, Any]] = buckets.get(name, [])
        if not bucket:
            continue
        # Silenciar apenas os casos 'sobrestamento vencido' dentro do bucket 'sobrestamento'.
        if name == 'sobrestamento':
            original_len = len(bucket)
            def _is_sobrest_vencido(item):
                obs = (item.get('observacao') or '') if isinstance(item, dict) else ''
                obs_l = obs.lower()
                return 'sobrestamento vencido' in obs_l or obs_l.strip() == 'sobrestamento vencido'

            bucket = [it for it in bucket if not _is_sobrest_vencido(it)]
            skipped = original_len - len(bucket)
            if skipped > 0:
                logger.info(f"[PEC] Skipped {skipped} 'sobrestamento vencido' items in bucket '{name}'")
        res: Dict[str, int] = _processar_bucket_demais(driver, bucket, progresso, descricao=name.upper())
        total_results['sucesso'] += res.get('sucesso', 0)
        total_results['erro'] += res.get('erro', 0)

    # Processar SISBAJUD por último
    processos_sisbajud: List[Dict[str, Any]] = buckets.get('sisbajud', [])
    if processos_sisbajud:
        res: Dict[str, int] = _processar_bucket_sisbajud(driver, processos_sisbajud, progresso)
        total_results['sucesso'] += res.get('sucesso', 0)
        total_results['erro'] += res.get('erro', 0)

    # Relatório final
    _imprimir_relatorio_final(buckets, total_results)
    return True


from selenium.webdriver.remote.webdriver import WebDriver
from typing import Dict, List, Any

def _processar_item_pec(driver: WebDriver, processo_info: dict[str, any], contexto: dict[str, any]) -> bool:
    """
    Wrapper para processar um item individual do PEC usando a função utilitária genérica.

    Args:
        driver: WebDriver do Selenium
        processo_info: Dicionário com informações do processo
        contexto: Contexto adicional (nome_bucket, progresso, etc.)

    Returns:
        bool: True se processado com sucesso
    """
    nome_bucket = contexto.get('nome_bucket', 'GENERICO')
    progresso = contexto.get('progresso', {})

    numero_processo = processo_info.get('numero')
    observacao = processo_info.get('observacao')
    linha = processo_info.get('linha')
    linha_index = processo_info.get('linha_index')
    acoes = processo_info.get('acoes', [])

    # Garantir que temos a lista de ações
    if not acoes and observacao:
        # FALLBACK: Se ações não chegaram (não deveria acontecer em fluxo correto)
        # Chama determinar_acoes_por_observacao() como último recurso
        temp_result = determinar_acoes_por_observacao(observacao)
        if temp_result:
            acoes = temp_result
            print(f"[BUCKET:{nome_bucket}] ⚠️ Ações determinadas no fallback (não deveriam estar vazias)")
        else:
            print(f"[BUCKET:{nome_bucket}] ❌ Nenhuma ação encontrada mesmo no fallback")
            return False

    acao_principal = acoes[0] if acoes else None
    acao_nome = acao_principal.__name__ if callable(acao_principal) else (str(acao_principal) if acao_principal else None)

    resultado_processo = False
    aba_lista_original = driver.current_window_handle

    consecutive_reindex_fails = 0
    MAX_CONSECUTIVE_FAILS = 2

    # Contador específico para erros do tipo StaleElementReference/UnboundLocalError
    consecutive_stale_errors = 0
    MAX_STALE_ERRORS = 3

    def _solicitar_reinicio_por_stale(numero_processo: Optional[str], detalhes: str) -> None:
        """Helper: injeta exceção de reinício com checagem da URL."""
        try:
            url_atual = driver.current_url
        except Exception:
            url_atual = ""

        acesso_negado_flag = False
        try:
            acesso_negado_flag = verificar_acesso_negado_pec(driver)
        except Exception:
            lower_url = url_atual.lower() if url_atual else ""
            acesso_negado_flag = any(token in lower_url for token in ['acesso-negado', 'access-denied', 'login.jsp'])

        msg = (
            f"RESTART_PEC: stale_errors={consecutive_stale_errors} acesso_negado={acesso_negado_flag} "
            f"for {numero_processo or '<desconhecido>'} -> {detalhes}"
        )
        if url_atual:
            msg = f"{msg} | url={url_atual}"
        raise Exception(msg)

    try:
        # Verificar se já foi executado
        if processo_ja_executado_pec(numero_processo, progresso):
            print(f"[BUCKET:{nome_bucket}] ⏭️ {numero_processo} já executado, pulando")
            return True

        # Reindexar linha se necessário
        linha_atual = linha
        try:
            linha_atual.is_displayed()
        except Exception:
            linha_atual = reindexar_linha(driver, numero_processo)
            if not linha_atual:
                consecutive_reindex_fails += 1
                acesso_negado = False
                try:
                    acesso_negado = verificar_acesso_negado_pec(driver)
                except Exception:
                    acesso_negado = False

                # Se acesso negado, REINICIAR DRIVER (não marcar como executado!)
                if acesso_negado:
                    msg = f"RESTART_PEC: ACESSO_NEGADO detectado para {numero_processo}"
                    print(f"[BUCKET:{nome_bucket}] ⚠️ {msg}")
                    print(f"[BUCKET:{nome_bucket}] 🔄 Reiniciando driver devido a acesso negado...")
                    raise Exception(msg)

                # Se muitos erros consecutivos, reiniciar
                if consecutive_reindex_fails >= MAX_CONSECUTIVE_FAILS:
                    msg = f"RESTART_PEC: reindex failures={consecutive_reindex_fails} for {numero_processo}"
                    print(f"[BUCKET:{nome_bucket}] ⚠️ {msg}")
                    raise Exception(msg)

                print(f"[BUCKET:{nome_bucket}] ❌ Não foi possível reindexar linha para {numero_processo} (fails={consecutive_reindex_fails})")
                return False

        # TODOS os processos são processados individualmente abrindo sua própria aba
        # Independente do tipo de ação - buckets são apenas organizadores

        # Verificar se linha ainda é válida (similar ao executar_lista_sisbajud_por_abas)
        try:
            linha_atual.is_displayed()
        except:
            print(f"[BUCKET:{nome_bucket}] ⚠️ Linha ficou stale, tentando reindexar {numero_processo}...")
            linha_atual = reindexar_linha(driver, numero_processo)
            if not linha_atual:
                print(f"[BUCKET:{nome_bucket}] ❌ Não foi possível reindexar linha para {numero_processo}")
                return False

        # Abrir detalhes do processo
        if not abrir_detalhes_processo(driver, linha_atual):
            print(f"[BUCKET:{nome_bucket}] ❌ Botão de detalhes não encontrado para {numero_processo}")
            return False

        time.sleep(1)

        # Abrir nova aba para o processo
        nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
        if not nova_aba:
            print(f"[BUCKET:{nome_bucket}] ❌ Nova aba do processo {numero_processo} não foi aberta")
            return False

        time.sleep(2)
        def _format_item(item):
            # item can be callable, (func, dict), or nested list
            try:
                if callable(item):
                    return getattr(item, '_wrapper_id', getattr(item, '__name__', str(item)))
                if isinstance(item, (list, tuple)) and len(item) == 2 and callable(item[0]) and isinstance(item[1], dict):
                    func = item[0]
                    return getattr(func, '_wrapper_id', getattr(func, '__name__', str(func)))
                if isinstance(item, (list, tuple)):
                    parts = [_format_item(x) for x in item]
                    return '[' + ', '.join(parts) + ']'
                return str(item)
            except Exception:
                return str(item)

        readable_acao = _format_item(acoes if acoes else acao_principal)
        print(f"[BUCKET:{nome_bucket}] Executando ação: {readable_acao} | observacao: {observacao}")
        acao_exec = acoes if acoes else acao_principal

        # Watchdog: detecta stalls longos na execução da ação e registra stacktrace para diagnóstico
        import threading, sys, traceback
        watchdog_active = {'running': True}

        def _watchdog():
            timeout = 25.0
            time.sleep(timeout)
            if watchdog_active.get('running'):
                try:
                    print(f"[WATCHDOG] Ação demorando mais de {timeout}s para {numero_processo} - gerando stacktrace de threads")
                    frames = sys._current_frames()
                    out_path = os.path.join(LOG_DIR, f'watchdog_{numero_processo.replace("/", "_")}.log')
                    with open(out_path, 'w', encoding='utf-8') as fh:
                        for tid, frame in frames.items():
                            fh.write(f"\n# ThreadID: {tid}\n")
                            traceback.print_stack(frame, file=fh)
                    print(f"[WATCHDOG] Stacktrace salvo em {out_path}")
                except Exception as e:
                    print(f"[WATCHDOG] Falha ao gerar stacktrace: {e}")

        try:
            t_watch = threading.Thread(target=_watchdog, daemon=True)
            t_watch.start()
        except Exception:
            t_watch = None

        try:
            resultado_processo = executar_acao_pec(driver, acao_exec, numero_processo=numero_processo, observacao=observacao, debug=True)
        finally:
            watchdog_active['running'] = False

        # Resultado
        if resultado_processo:
            print(f"[BUCKET:{nome_bucket}] ✅ {numero_processo} processado com sucesso")
        else:
            print(f"[BUCKET:{nome_bucket}] ❌ Falha ao processar {numero_processo}")

        # FECHAR ABAS E VOLTAR PARA LISTA
        try:
            if aba_lista_original in driver.window_handles:
                driver.switch_to.window(aba_lista_original)
                for handle in driver.window_handles:
                    if handle != aba_lista_original:
                        try:
                            driver.switch_to.window(handle)
                            driver.close()
                        except:
                            pass
                driver.switch_to.window(aba_lista_original)
        except Exception as eback:
            print(f"[BUCKET:{nome_bucket}] ⚠️ Erro ao voltar para lista: {eback}")

        time.sleep(1)

    except KeyboardInterrupt:
        if resultado_processo:
            try:
                marcar_processo_executado_pec(numero_processo, progresso)
            except:
                pass
        raise

    except Exception as e:
        # Detectar padrões recorrentes de erro relacionados a elementos stale / reindex
        msg_exc = str(e)

        # RESTART_PEC deve ser propagado para o nível superior para reinício do driver
        if 'RESTART_PEC' in msg_exc:
            print(f"[BUCKET:{nome_bucket}] 🔄 Propagando RESTART_PEC para reinício do fluxo")
            raise

        is_stale_like = False

        # Exceções do Selenium indicando elemento stale
        if isinstance(e, StaleElementReferenceException):
            is_stale_like = True

        # Situações onde reindexar_linha falha gerando UnboundLocalError
        if isinstance(e, UnboundLocalError) or "cannot access local variable 'reindexar_linha'" in msg_exc:
            is_stale_like = True

        if is_stale_like:
            consecutive_stale_errors += 1
            print(f"[BUCKET:{nome_bucket}] ⚠️ Erro stale/reindex detectado ({consecutive_stale_errors}/{MAX_STALE_ERRORS}): {e}")

            precisa_reiniciar = (
                isinstance(e, UnboundLocalError)
                or 'reindexar_linha' in msg_exc
                or consecutive_stale_errors >= MAX_STALE_ERRORS
            )

            if precisa_reiniciar:
                _solicitar_reinicio_por_stale(numero_processo, msg_exc)
        else:
            # reset counter on other exceptions
            consecutive_stale_errors = 0

        print(f"[BUCKET:{nome_bucket}] ❌ Exceção ao processar {numero_processo}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # GARANTIR QUE NÃO MARCA COMO EXECUTADO SE DRIVER QUEBROU (acesso negado)
        try:
            from .core_progresso import verificar_acesso_negado_pec
            if verificar_acesso_negado_pec(driver):
                print(f"[BUCKET:{nome_bucket}] ⚠️ Driver quebrado (acesso negado) - forçando status ERRO para {numero_processo}")
                resultado_processo = False
        except Exception as veri_ex:
            print(f"[BUCKET:{nome_bucket}] ⚠️ Falha ao verificar acesso negado: {veri_ex}")
        
        # Marcar progresso se teve sucesso; marcar erro se falhou —
        # registra `processos_com_erro` para permitir reprocessamento futuro.
        try:
            if resultado_processo:
                marcar_processo_executado_pec(numero_processo, progresso)
            else:
                # Registrar como erro (não será confundido com 'executado')
                try:
                    marcar_processo_executado_pec(numero_processo, progresso, status="ERRO")
                except Exception:
                    # Fallback: garantir que falha não interrompa o loop
                    print(f"[BUCKET:{nome_bucket}] ⚠️ Não foi possível marcar erro para {numero_processo}")
        except Exception as prog_e:
            print(f"[BUCKET:{nome_bucket}] ⚠️ Erro ao atualizar progresso para {numero_processo}: {prog_e}")

        # Pequena pausa anti-rate entre itens
        try:
            time.sleep(0.7)
        except Exception:
            pass

    return resultado_processo


def _processar_bucket_generico(driver: Any, processos: List[Dict[str, Any]], progresso: Dict[str, Any], nome_bucket: str = "GENERICO") -> Dict[str, int]:
    """
    FUNÇÃO GENÉRICA ÚNICA: Processa QUALQUER bucket seguindo o fluxo padrão.

    Refatorada para usar função utilitária genérica com interrupção automática em erros críticos.

    Fluxo universal para TODOS os buckets:
    1. Abrir processo no PJE
    2. Executar ações definidas nas regras
    3. Fechar processo e voltar para lista

    Args:
        driver: WebDriver do Selenium
        processos: Lista de processos do bucket
        progresso: Dicionário de progresso
        nome_bucket: Nome do bucket para logs

    Returns:
        dict: {'sucesso': int, 'erro': int}
    """
    def processar_item_pec(driver_param, processo_info):
        """Wrapper para processar um item individual do PEC.

        Agora utiliza o monitoramento unificado (`executar_com_monitoramento_unificado`) —
        isso garante:
        - reprocessamento de itens previamente com erro (não são pulados),
        - marcação consistente de sucesso/erro no `progresso.json`,
        - tratamento de ACCESS_NEGADO/RESTART via mecanismo unificado,
        - supressão de logs de carregamento repetidos.
        """
        contexto = {'nome_bucket': nome_bucket, 'progresso': progresso}

        numero = processo_info.get('numero')

        # Usar o monitoramento unificado — suprimir log de carregamento dentro de loops
        sucesso, _ = executar_com_monitoramento_unificado(
            'pec',
            driver_param,
            numero,
            lambda drv: _processar_item_pec(drv, processo_info, contexto),
            suppress_load_log=True
        )

        # Final pequena pausa anti-rate entre items
        try:
            time.sleep(0.6)
        except Exception:
            pass

        return sucesso

    # Usar função utilitária genérica com interrupção automática
    resultados = executar_processamento_iterativo_com_corte_em_erro_critico(
        driver=driver,
        nome_modulo=f"PEC_{nome_bucket}",
        lista_itens=processos,
        funcao_processamento_item=processar_item_pec,
        max_tentativas_recuperacao=2,
        stop_on_critical=False
    )

    # Converter formato de retorno da função utilitária para o formato esperado
    return {
        'sucesso': resultados.get('sucessos', 0),
        'erro': resultados.get('erros', 0)
    }


def _processar_bucket_demais(driver: Any, bucket: List[Dict[str, Any]], progresso: Dict[str, Any], descricao: str = "") -> Dict[str, int]:
    """[DEPRECATED] Mantida para compatibilidade - usa _processar_bucket_generico."""
    return _processar_bucket_generico(driver, bucket, progresso, descricao.upper())


def _processar_bucket_sisbajud(driver: Any, processos_sisbajud: List[Dict[str, Any]], progresso: Dict[str, Any]) -> Dict[str, int]:
    """
    Processa bucket SISBAJUD com driver compartilhado.
    
    OTIMIZAÇÃO: Usa um único driver SISBAJUD para todos os processos,
    evitando abrir/fechar o driver para cada processo.
    
    Delega para SISB/batch.py que implementa a lógica de lote.
    
    Args:
        driver: WebDriver PJE
        processos_sisbajud: Lista de processos do bucket
        progresso: Dicionário de progresso
        
    Returns:
        dict: {'sucesso': int, 'erro': int}
    """
    if not processos_sisbajud:
        return {'sucesso': 0, 'erro': 0}
    
    try:
        from SISB.batch import processar_lote_sisbajud
        
        resultados = processar_lote_sisbajud(
            driver_pje=driver,
            processos=processos_sisbajud,
            progresso=progresso,
            fn_reindexar_linha=reindexar_linha,
            fn_abrir_detalhes=abrir_detalhes_processo,
            fn_trocar_aba=trocar_para_nova_aba,
            fn_ja_executado=processo_ja_executado_pec,
            fn_marcar_executado=marcar_processo_executado_pec,
            log=True
        )
        
        logger.error(f"[SISBAJUD_BUCKET]  Resultado: {resultados['sucesso']} sucesso, {resultados['erro']} erros")
        return resultados
        
    except Exception as e:
        logger.error(f"[SISBAJUD_BUCKET]  Erro ao importar SISB.batch: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: usar método antigo
        return _processar_bucket_generico(driver, processos_sisbajud, progresso, "SISBAJUD")


def _imprimir_relatorio_final(buckets: Dict[str, List[Dict[str, Any]]], total_results: Dict[str, int]) -> None:
    """Helper: Imprime relatório final do processamento."""
    processos_sucesso = total_results['sucesso']
    processos_erro = total_results['erro']

    # Calcular total de processos pendentes (soma de todos os buckets)
    total_pendentes = sum(len(buckets.get(name, [])) for name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento', 'sisbajud'])

    print(f"[INDEXAR] ========== RELATÓRIO FINAL ==========")
    print(f"[INDEXAR] Processos processados com sucesso: {processos_sucesso}")
    print(f"[INDEXAR] Processos com erro: {processos_erro}")
    print(f"[INDEXAR] Taxa de sucesso: {(processos_sucesso/total_pendentes*100):.1f}%" if total_pendentes else "N/A")
    print(f"[INDEXAR] =====================================")
