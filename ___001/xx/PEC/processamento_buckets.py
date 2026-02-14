import logging
logger = logging.getLogger(__name__)

import time
from typing import Optional, Dict, List, Any
from selenium.common.exceptions import StaleElementReferenceException

from .core import (
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
    verificar_acesso_negado_pec,
)
from .regras import determinar_acoes_por_observacao, executar_acao_pec

from Fix.extracao import abrir_detalhes_processo, trocar_para_nova_aba, reindexar_linha


def _formatar_nome_acao(acao) -> str:
    """Formata o nome da ação para logging de forma legível."""
    if not acao:
        return "Nenhuma"
    
    if isinstance(acao, list):
        # Lista de ações - identificar cada uma
        nomes = []
        for item in acao:
            if callable(item):
                if hasattr(item, '__name__'):
                    nome = item.__name__
                    # Mapeamentos especiais para nomes mais legíveis
                    if nome == '<lambda>':
                        # Tentar identificar lambda por atributos ou contexto
                        func_str = str(item)
                        if 'criar_gigs' in func_str and 'Ingrid' in func_str:
                            nomes.append("gigs_ingrid")
                        elif 'criar_gigs' in func_str:
                            nomes.append("gigs")
                        else:
                            nomes.append("lambda")
                    elif nome.startswith('wrapper'):
                        nomes.append("ato_idpj")  # Para este contexto específico
                    elif nome == '_gigs_edital_intimacao':
                        nomes.append("gigs")
                    elif nome == 'ato_idpj':
                        nomes.append("ato_idpj")
                    elif nome == 'ato_bloq':
                        nomes.append("ato_bloq")
                    elif nome == 'ato_meios':
                        nomes.append("ato_meios")
                    else:
                        nomes.append(nome)
                else:
                    nomes.append(str(type(item).__name__))
            else:
                nomes.append(str(item))
        return " + ".join(nomes)
    
    if callable(acao):
        if hasattr(acao, '__name__'):
            nome = acao.__name__
            # Mapeamentos especiais
            if nome == '<lambda>':
                func_str = str(acao)
                if 'criar_gigs' in func_str and 'Ingrid' in func_str:
                    return "gigs_ingrid"
                elif 'criar_gigs' in func_str:
                    return "gigs"
                else:
                    return "lambda"
            elif nome.startswith('wrapper'):
                return "ato_judicial"
            elif nome == 'ato_idpj':
                return "ato_idpj"
            elif nome == 'ato_bloq':
                return "ato_bloq"
            elif nome == 'ato_meios':
                return "ato_meios"
            else:
                return nome
        else:
            return str(type(acao).__name__)
    
    return str(acao)


def _processar_buckets(driver: Any, buckets: Dict[str, List[Dict[str, Any]]], progresso: Dict[str, Any]) -> bool:
    """Helper: Processa todos os buckets na ordem correta."""
    total_results = {'sucesso': 0, 'erro': 0}

    # Processar buckets não-SISBAJUD na nova ordem
    for name in ['sobrestamento', 'carta', 'comunicacoes', 'outros']:
        bucket = buckets.get(name, [])
        if not bucket:
            continue
        res = _processar_bucket_demais(driver, bucket, progresso, descricao=name.upper())
        total_results['sucesso'] += res.get('sucesso', 0)
        total_results['erro'] += res.get('erro', 0)

    # Processar SISBAJUD por último
    processos_sisbajud = buckets.get('sisbajud', [])
    if processos_sisbajud:
        res = _processar_bucket_sisbajud(driver, processos_sisbajud, progresso)
        total_results['sucesso'] += res.get('sucesso', 0)
        total_results['erro'] += res.get('erro', 0)

    # Relatório final
    _imprimir_relatorio_final(buckets, total_results)
    return True


def _processar_bucket_generico(driver: Any, processos: List[Dict[str, Any]], progresso: Dict[str, Any], nome_bucket: str = "GENERICO") -> Dict[str, int]:
    """
    FUNÇÃO GENÉRICA ÚNICA: Processa QUALQUER bucket seguindo o fluxo padrão.

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
    resultados = {'sucesso': 0, 'erro': 0}
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

    for idx, processo_info in enumerate(processos):
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

        acao_principal = acoes[0] if acoes else None
        acao_nome = _formatar_nome_acao(acao_principal)

        print(f"[BUCKET:{nome_bucket}] {idx+1}/{len(processos)} -> {numero_processo} ({acao_nome})")

        resultado_processo = False
        try:
            # Verificar se já foi executado
            if processo_ja_executado_pec(numero_processo, progresso):
                print(f"[BUCKET:{nome_bucket}] ⏭️ {numero_processo} já executado, pulando")
                continue

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
                    resultados['erro'] += 1
                    continue

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
                    resultados['erro'] += 1
                    continue

            # Abrir detalhes do processo
            if not abrir_detalhes_processo(driver, linha_atual):
                print(f"[BUCKET:{nome_bucket}] ❌ Botão de detalhes não encontrado para {numero_processo}")
                resultados['erro'] += 1
                continue

            time.sleep(1)

            # Abrir nova aba para o processo
            nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
            if not nova_aba:
                print(f"[BUCKET:{nome_bucket}] ❌ Nova aba do processo {numero_processo} não foi aberta")
                resultados['erro'] += 1
                continue

            time.sleep(2)
            print(f"[BUCKET:{nome_bucket}] Executando ação: {acao_nome}")
            acao_exec = acoes if acoes else acao_principal
            resultado_processo = executar_acao_pec(driver, acao_exec, numero_processo=numero_processo, observacao=observacao, debug=True)

            # Resultado
            if resultado_processo:
                resultados['sucesso'] += 1
                print(f"[BUCKET:{nome_bucket}] ✅ {numero_processo} processado com sucesso")
            else:
                resultados['erro'] += 1
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
            resultados['erro'] += 1
            import traceback
            traceback.print_exc()

        finally:
            # Marcar progresso apenas se teve sucesso
            if resultado_processo:
                try:
                    marcar_processo_executado_pec(numero_processo, progresso)
                except Exception as prog_e:
                    print(f"[BUCKET:{nome_bucket}] ⚠️ Erro ao marcar progresso para {numero_processo}: {prog_e}")
            else:
                print(f"[BUCKET:{nome_bucket}] ⏭️ {numero_processo} NÃO marcado (não executado com sucesso)")

    return resultados


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
    total_pendentes = sum(len(buckets.get(name, [])) for name in ['sobrestamento', 'carta', 'comunicacoes', 'outros', 'sisbajud'])

    print(f"[INDEXAR] ========== RELATÓRIO FINAL ==========")
    print(f"[INDEXAR] Processos processados com sucesso: {processos_sucesso}")
    print(f"[INDEXAR] Processos com erro: {processos_erro}")
    print(f"[INDEXAR] Taxa de sucesso: {(processos_sucesso/total_pendentes*100):.1f}%" if total_pendentes else "N/A")
    print(f"[INDEXAR] =====================================")
