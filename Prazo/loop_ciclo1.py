from .loop_base import *
from .loop_ciclo1_filtros import _ciclo1_aplicar_filtro_fases, _verificar_quantidade_processos_paginacao
from .loop_ciclo1_movimentacao import (
    _ciclo1_marcar_todas,
    _ciclo1_abrir_suitcase,
    _ciclo1_aguardar_movimentacao_lote,
    _ciclo1_movimentar_destino_providencias,
    _ciclo1_movimentar_destino,
    _ciclo1_retornar_lista,
)


def ciclo1(driver: WebDriver, opcao_destino: str = 'Análise') -> Union[bool, str]:
    """
    Orquestra ciclo 1: filtro, marcação, suitcase, movimentação para painel 14.

    Returns:
        True: sucesso (pode ter mais processos, repetir loop)
        "complete_single_batch": sucesso, todos processos movidos em lote único (<20), não repetir
        False: erro crítico
        "no_more_processes": sem processos em liquidação/execução
        "marcar_todas_not_found_but_continue": marcar-todas não encontrado
        "go_to_ciclo2": batch indisponível no ciclo1, seguir para ciclo2
        "single_process": apenas 1 processo, batch não disponível
    """
    # ===== VERIFICAÇÃO PRÉVIA: Lista já vazia antes do filtro =====
    try:
        mensagem_vazia = driver.find_elements(By.XPATH, "//span[contains(text(), 'Não há processos neste tema')]")
        if mensagem_vazia and any(el.is_displayed() for el in mensagem_vazia):
            logger.info('[CICLO1] ⚡ Lista já vazia antes do filtro - nada a processar')
            return "no_more_processes"
    except Exception:
        pass  # Se erro ao verificar, segue normalmente
    
    with medir_latencia('CICLO1_APLICAR_FILTRO_FASES'):
        filtro_result = _ciclo1_aplicar_filtro_fases(driver)
    if filtro_result == "no_more_processes":
        logger.info('[CICLO1] Nenhum processo em liquidação/execução.')
        return "no_more_processes"
    if not filtro_result:
        return False

    # ===== VERIFICAR QUANTIDADE DE PROCESSOS =====
    # Se houver apenas 1 processo, o PJE não mostra o botão batch (suitcase)
    qtd_processos = 0
    try:
        time.sleep(1)
        processos = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        qtd_processos = len(processos)
        logger.info(f'[CICLO1]  Detectados {qtd_processos} processo(s) na lista')

        if qtd_processos == 1:
            logger.info('[CICLO1] ℹ Apenas 1 processo detectado - PJE não disponibiliza batch (suitcase)')
            logger.info('[CICLO1]  Prosseguindo para processamento individual (Fase 2)')
            return "single_process"
        elif qtd_processos == 0:
            logger.info('[CICLO1] Nenhum processo encontrado após filtro.')
            return "no_more_processes"
        
        # Otimização: se menos de 20, sabemos que processaremos tudo em um único lote
        if qtd_processos < 20:
            logger.info(f'[CICLO1] ⚡ Lote único detectado ({qtd_processos} < 20) - não repetir após conclusão')
    except Exception as e:
        logger.info(f'[CICLO1]  Erro ao contar processos: {e}')
        logger.info('[CICLO1] Continuando com o fluxo normal...')

    with medir_latencia('CICLO1_MARCAR_TODAS'):
        marcar_result = _ciclo1_marcar_todas(driver)
    if marcar_result == "marcar_todas_not_found_but_continue":
        logger.info('[CICLO1] Marcar-todas indisponível; prosseguindo para Fase 2.')
        return "marcar_todas_not_found_but_continue"
    elif marcar_result == "error":
        logger.info(f'[CICLO1] Falha em marcar-todas: {marcar_result}')
        return False
    elif marcar_result != "success":
        logger.info(f'[CICLO1] Retorno inesperado em marcar-todas: {marcar_result}')
        return False

    with medir_latencia('CICLO1_ABRIR_SUITCASE'):
        abriu_suitcase = _ciclo1_abrir_suitcase(driver)
    if not abriu_suitcase:
        logger.info('[CICLO1] Suitcase indisponível no ciclo1; redirecionando para ciclo2.')
        return "go_to_ciclo2"

    with medir_latencia('CICLO1_AGUARDAR_MOVIMENTACAO_LOTE'):
        aguardou_mov_lote = _ciclo1_aguardar_movimentacao_lote(driver)
    if not aguardou_mov_lote:
        logger.info('[CICLO1] Erro ao aguardar movimentação em lote.')
        return False

    with medir_latencia(f'CICLO1_MOVIMENTAR_DESTINO_{opcao_destino}'):
        moveu_destino = _ciclo1_movimentar_destino(driver, opcao_destino)
    if not moveu_destino:
        logger.info('[CICLO1] Erro ao movimentar destino.')
        return False

    with medir_latencia('CICLO1_RETORNAR_LISTA'):
        _ciclo1_retornar_lista(driver)
    
    # Retornar status baseado na quantidade inicial de processos
    if qtd_processos < 20:
        logger.info(f'[CICLO1] ✓ Ciclo 1 concluído - lote único ({qtd_processos} processos), não repetir')
        return "complete_single_batch"
    else:
        logger.info('[CICLO1] Ciclo 1 concluído - pode haver mais processos, verificar novamente')
        return True
