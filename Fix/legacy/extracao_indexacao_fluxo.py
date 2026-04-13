import time
import re

from Fix.log import logger
from Fix.monitoramento_progresso_unificado import carregar_progresso_unificado
from .abas import validar_conexao_driver, forcar_fechamento_abas_extras
from .extracao_indexacao import (
    _indexar_tentar_reindexar,
    _indexar_tentar_trocar_aba,
    abrir_detalhes_processo,
    indexar_processos,
)

try:
    from PEC.core import reiniciar_driver_e_logar_pje
except Exception:
    reiniciar_driver_e_logar_pje = None


def _indexar_processar_item(driver, proc_id, linha, aba_lista_original, callback):
    """Processa um item individual da lista: abre, executa callback, limpa abas."""
    logger.info(f'[PROCESSAR] Processando {proc_id}...')
    
    # Validar conexão
    conexao_status = validar_conexao_driver(driver, "PROCESSAR")
    if conexao_status == "FATAL":
        logger.error(f'[PROCESSAR][FATAL] Contexto descartado - interrompendo')
        return "FATAL"
    elif not conexao_status:
        logger.error(f'[PROCESSAR][ERRO] Conexão perdida para {proc_id}')
        return "ERRO"
    
    # Verificar URL e recuperar se necessário
    try:
        atual_url = driver.current_url
        if 'acesso-negado' in atual_url.lower() or 'login.jsp' in atual_url.lower():
            logger.warning(f'[PROCESSAR][ALERTA] Acesso negado detectado. Reiniciando driver...')
            novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            if not novo_driver:
                logger.error('[PROCESSAR][ERRO] Falha ao reiniciar driver')
                return "ERRO"
            driver = novo_driver
            aba_lista_original = driver.window_handles[0] if driver.window_handles else None
        
        # Guard clause: URL inválida
        if "escaninho" not in atual_url and "documentos" not in atual_url:
            if not aba_lista_original or aba_lista_original not in driver.window_handles:
                return "ERRO"
            driver.switch_to.window(aba_lista_original)
            logger.info('[PROCESSAR] Voltado para aba da lista')
    except Exception as e:
        logger.error(f'[PROCESSAR][ERRO] Falha ao verificar URL: {e}')
        return "ERRO"
    
    # Reindexar com tentativas (extraído em função)
    linha_atual = _indexar_tentar_reindexar(driver, proc_id)
    if not linha_atual:
        logger.error(f'[PROCESSAR][ERRO] Não reindexado após 3 tentativas')
        return "ERRO"
    
    # Abrir detalhes
    try:
        if not abrir_detalhes_processo(driver, linha_atual):
            logger.error(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado')
            return "ERRO"
    except Exception as e:
        logger.error(f'[PROCESSAR][ERRO] Falha ao abrir detalhes: {e}')
        return "ERRO"
    
    time.sleep(1)
    
    # Trocar para nova aba com tentativas (extraído em função)
    nova_aba = _indexar_tentar_trocar_aba(driver, aba_lista_original)
    if not nova_aba:
        logger.error(f'[PROCESSAR][ERRO] Nova aba não aberta após 3 tentativas')
        return "ERRO"
    
    # Executar callback COM O NÚMERO DA LISTA
    try:
        time.sleep(1)
        # CRIAR UM WRAPPER QUE PASSA O NÚMERO DA LISTA PARA O CALLBACK
        def callback_wrapper(driver_inner):
            # Adicionar o número da lista como atributo temporário do driver
            driver_inner._numero_processo_lista = proc_id
            return callback(driver_inner)
        
        logger.debug(f'[PROCESSAR] Chamando callback para {proc_id}')
        try:
            callback_result = callback_wrapper(driver)
            logger.debug(f'[PROCESSAR] callback_result for {proc_id}: {callback_result}')
            if callback_result:
                logger.info(f'[PROCESSAR] Callback OK para {proc_id}')
                conexao_pos = validar_conexao_driver(driver, "POS-CALLBACK")
                if conexao_pos == "FATAL":
                    logger.error(f'[PROCESSAR][FATAL] Contexto perdido durante callback')
                    return "FATAL"
            else:
                logger.error(f'[PROCESSAR][ERRO] Callback retornou False')
                return "ERRO"
        except Exception as e:
            logger.error(f'[PROCESSAR][ERRO] Falha inesperada em callback: {e}')
            return "ERRO"
    except Exception as e:
        logger.error(f'[PROCESSAR][ERRO] Falha inesperada em callback: {e}')
        return "ERRO"
    finally:
        # Limpar atributo temporário
        if hasattr(driver, '_numero_processo_lista'):
            delattr(driver, '_numero_processo_lista')
    
    # ===== CALLBACK JÁ GERENCIOU SUAS ABAS NO FINALLY =====
    # Agora callback retornou e deve ter limpado suas próprias abas.
    # Um breve sleep para garantir que Selenium esteja sincronizado.
    logger.info('[PROCESSAR] Callback completado. Sincronizando driver...')
    time.sleep(0.3)  # Minimal sync sleep
    
    # Limpeza de segurança (fallback, em caso callback n tenha conseguido)
    limpeza = forcar_fechamento_abas_extras(driver, aba_lista_original)
    if limpeza == "FATAL":
        logger.error(f'[PROCESSAR][FATAL] Contexto perdido durante limpeza')
        return "FATAL"
    elif not limpeza:
        logger.error(f'[PROCESSAR][ALERTA] Limpeza de abas falhou (não é fatal)')
    
    return "SUCESSO"


def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True, tipo_execucao: str = None):
    """
    Processa lista de processos com tratamento robusto de conexão e abas.
    Estratégia: reindexa a lista completa antes de cada processamento para lidar com listas dinâmicas.
    """
    
    logger.info('[FLUXO] Iniciando indexação da lista de processos...')

    from .extracao_indexacao import _indexar_preparar_contexto

    aba_original, processos_iniciais = _indexar_preparar_contexto(driver, max_processos)
    if not aba_original or not processos_iniciais:
        return False

    # Indexar uma vez no início (não a cada iteração)
    try:
        processos_iniciais = indexar_processos(driver)
        if not processos_iniciais:
            logger.info('[FLUXO] Nenhum processo encontrado para processar')
            return False

        # Se informado, usar o monitor de progresso para eliminar processos já executados
        if tipo_execucao:
            try:
                progresso = carregar_progresso_unificado(tipo_execucao, suppress_load_log=True)
                executados = progresso.get('processos_executados', []) or []
                executados_set = set(executados)
                executados_digits = set([re.sub(r'\D', '', e) for e in executados_set if e])

                def _is_executado(pid: str) -> bool:
                    if not pid:
                        return False
                    if pid in executados_set:
                        return True
                    pid_digits = re.sub(r'\D', '', pid)
                    return pid_digits in executados_digits

                processos_filtrados = [(pid, linha) for (pid, linha) in processos_iniciais if not _is_executado(pid)]
                skipped = len(processos_iniciais) - len(processos_filtrados)
                if skipped:
                    logger.info(f'[FLUXO] {skipped} processos pulados (já executados) via progresso {tipo_execucao}')
                processos_iniciais = processos_filtrados
            except Exception as e:
                logger.info(f'[FLUXO][AVISO] Falha ao filtrar processos via progresso: {e}')

        logger.info(f'[FLUXO] {len(processos_iniciais)} processos encontrados para processamento')
    except Exception as e:
        logger.info(f'[FLUXO][ERRO] Falha ao indexar lista inicial: {e}')
        return False

    processados = 0
    erros = 0
    fatal = False
    
    # Processar lista indexada (sem reindexar a cada item)
    for idx, (proc_id, linha_original) in enumerate(processos_iniciais):
        if max_processos and processados >= max_processos:
            logger.info(f'[FLUXO] Limite de {max_processos} processos atingido')
            break

        logger.info(f'[FLUXO] Processando item {idx+1}/{len(processos_iniciais)}: {proc_id}')


        resultado = _indexar_processar_item(driver, proc_id, linha_original, aba_original, callback)

        if resultado == "SUCESSO":
            processados += 1
        elif resultado == "FATAL":
            fatal = True
            logger.info(f'[FLUXO][FATAL] Interrompendo processamento')
            break
        else:
            erros += 1
            # Em caso de erro, tentar o próximo da lista atual
            idx += 1

    # Relatório final
    logger.info(f'[FLUXO]  Processamento concluído: {processados} sucesso, {erros} erros')

    # Se detectamos um fatal (ex.: driver fechado), abortar imediatamente para liberar terminal
    if fatal:
        logger.error('[FLUXO][FATAL] Detected fatal driver state — aborting process to free terminal')
        raise SystemExit('Driver context fatal - aborting')

    return processados > 0