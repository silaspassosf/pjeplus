from .loop_base import *
from .loop_helpers import _extrair_numero_processo_da_linha
from .loop_api import _verificar_processos_xs_paralelo


def _ciclo2_aplicar_filtros(driver: WebDriver) -> bool:
    """Aplica filtros necessários para ciclo 2: 100 itens + fases liquidação/execução + tarefa análise."""
    try:
        # Aplicar filtro de 100 itens por página
        if not aplicar_filtro_100(driver):
            return False
        time.sleep(1)

        # Aplicar filtro de fases (liquidação/execução) + tarefa análise
        if not filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=['análise']):
            return False
        time.sleep(2)

        return True
    except Exception as e:
        logger.error(f'[CICLO2] Erro ao aplicar filtros: {e}')
        return False


def _ciclo2_processar_livres(driver: WebDriver, client: Optional['PjeApiClient'] = None) -> int:
    """Seleciona processos livres sem verificar atividades xs existentes.

    Args:
        driver: WebDriver Selenium
        client: PjeApiClient (não utilizado na versão simplificada)

    Returns:
        Total de processos livres selecionados
    """
    try:
        # Selecionar todos os processos livres diretamente
        print('[LOOP_PRAZO][LIVRES] 🔍 Selecionando todos os processos livres...')
        selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES)
        print(f'[LOOP_PRAZO][LIVRES] ✅ Processos livres selecionados: {selecionados_livres}')

        # ✅ AGUARDAR para garantir que a seleção de LIVRES foi completada ANTES de continuar
        time.sleep(1.5)

        return selecionados_livres

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em _ciclo2_processar_livres: {e}')
        return 0


def _ciclo2_selecionar_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não-livres via JavaScript."""
    try:
        # Desselecionar todos primeiro
        driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
        time.sleep(0.6)

        print(f'[LOOP_PRAZO][DEBUG] Executando script de seleção de não-livres (max={max_processos})...')
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']

        print(f'[LOOP_PRAZO][DEBUG] Resultado: {selecionados} selecionados de {total_nao_livres} não-livres totais')

        ha_mais = total_nao_livres > selecionados
        return selecionados, ha_mais
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao selecionar não-livres: {e}')
        return 0, False