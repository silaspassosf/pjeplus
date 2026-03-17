from .loop_base import *
from .loop_helpers import _extrair_numero_processo_da_linha
from .loop_api import _verificar_processos_xs_paralelo


def _ciclo2_aplicar_filtros(driver: WebDriver) -> bool:
    """Aplica filtros necessários para ciclo 2."""
    try:
        # Aguardar lista carregar
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[role='combobox']"))
            )
            time.sleep(1.5)
        except Exception:
            time.sleep(2)
        
        if not aplicar_filtro_100(driver):
            return False
        time.sleep(1)

        if not filtrofases(
            driver, 
            fases_alvo=['liquidação', 'execução'],
            tarefas_alvo=['análise'],
            seletor_tarefa='Tarefa do processo'
        ):
            return False
        time.sleep(2)

        return True
    except Exception as e:
        logger.error(f'[CICLO2] Erro ao aplicar filtros: {e}')
        return False


def _ciclo2_processar_livres(driver: WebDriver, client: Optional['PjeApiClient'] = None) -> int:
    """Seleciona todos os processos livres (sem verificação de xs).

    Args:
        driver: WebDriver Selenium
        client: PjeApiClient (não utilizado, mantido para compatibilidade)

    Returns:
        Total de processos livres selecionados
    """
    try:
        selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES)
        
        if selecionados_livres > 0:
            logger.info(f'[CICLO2][LIVRES] ✅ {selecionados_livres} livre(s) selecionado(s)')
        else:
            logger.info('[CICLO2][LIVRES] Nenhum livre encontrado')
        
        time.sleep(1.5)
        return selecionados_livres

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em _ciclo2_processar_livres: {e}')
        return 0


def _ciclo2_selecionar_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não-livres via JavaScript."""
    try:
        driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
        time.sleep(0.6)

        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']

        logger.info(f'[CICLO2][NAO_LIVRES] {selecionados}/{total_nao_livres} selecionados')

        ha_mais = total_nao_livres > selecionados
        return selecionados, ha_mais
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao selecionar não-livres: {e}')
        return 0, False