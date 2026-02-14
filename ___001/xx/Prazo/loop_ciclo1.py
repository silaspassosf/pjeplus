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
        True: sucesso
        False: erro crítico
        "no_more_processes": sem processos em liquidação/execução
        "marcar_todas_not_found_but_continue": marcar-todas não encontrado
        "suitcase_not_found_but_continue": suitcase não encontrado
        "single_process": apenas 1 processo, batch não disponível
    """
    filtro_result = _ciclo1_aplicar_filtro_fases(driver)
    if filtro_result == "no_more_processes":
        print('[CICLO1] Nenhum processo em liquidação/execução.')
        return "no_more_processes"
    if not filtro_result:
        return False

    # ===== VERIFICAR QUANTIDADE DE PROCESSOS =====
    # Se houver apenas 1 processo, o PJE não mostra o botão batch (suitcase)
    try:
        time.sleep(1)
        processos = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        qtd_processos = len(processos)
        print(f'[CICLO1]  Detectados {qtd_processos} processo(s) na lista')

        if qtd_processos == 1:
            print('[CICLO1] ℹ Apenas 1 processo detectado - PJE não disponibiliza batch (suitcase)')
            print('[CICLO1]  Prosseguindo para processamento individual (Fase 2)')
            return "single_process"
        elif qtd_processos == 0:
            print('[CICLO1] Nenhum processo encontrado após filtro.')
            return "no_more_processes"
    except Exception as e:
        print(f'[CICLO1]  Erro ao contar processos: {e}')
        print('[CICLO1] Continuando com o fluxo normal...')

    marcar_result = _ciclo1_marcar_todas(driver)
    if marcar_result == "no_processes":
        print('[CICLO1] Nenhum processo encontrado para marcar.')
        return "no_more_processes"
    elif marcar_result in ["not_found", "error"]:
        print(f'[CICLO1] Falha em marcar-todas: {marcar_result}')
        return False

    if not _ciclo1_abrir_suitcase(driver):
        print('[CICLO1] Erro ao abrir suitcase.')
        return False

    if not _ciclo1_aguardar_movimentacao_lote(driver):
        print('[CICLO1] Erro ao aguardar movimentação em lote.')
        return False

    if not _ciclo1_movimentar_destino(driver, opcao_destino):
        print('[CICLO1] Erro ao movimentar destino.')
        return False

    _ciclo1_retornar_lista(driver)
    print('[CICLO1] Ciclo 1 concluído.')
    return True
