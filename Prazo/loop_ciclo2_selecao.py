from .loop_base import *
from .loop_helpers import _extrair_numero_processo_da_linha
from .loop_api import _verificar_processos_xs_paralelo, _obter_processos_com_gigs_api
from Fix.smart_finder import buscar
from Fix.core import aguardar_renderizacao_nativa


def _ciclo2_aplicar_filtros(driver: WebDriver) -> bool:
    """Aplica filtros necessários para ciclo 2."""
    try:
        # Aguardar lista carregar
        try:
            # Usar buscar() para detectar o mat-select mais rapidamente
            el = buscar(driver, 'ciclo2_mat_select_combobox', ["mat-select[role='combobox']", "//mat-select"])
            if not el:
                # Prefer waiting for the stable total-registros indicator (shows "X - Y de Z")
                try:
                    aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=10)
                except Exception:
                    # Fallback: esperar mat-select quando total-registros não estiver presente
                    aguardar_renderizacao_nativa(driver, "mat-select[role='combobox']", timeout=10)
        except Exception:
            # fallback leve
            WebDriverWait(driver, 5)
        
        if not aplicar_filtro_100(driver):
            return False
        # aguardar aplicação do filtro — checar presença de linhas
        try:
            aguardar_renderizacao_nativa(driver, 'tr.cdk-drag', timeout=6)
        except Exception:
            pass

        if not filtrofases(
            driver, 
            fases_alvo=['liquidação', 'execução'],
            tarefas_alvo=['análise'],
            seletor_tarefa='Tarefa do processo'
        ):
            return False
        try:
            aguardar_renderizacao_nativa(driver, 'tr.cdk-drag', timeout=6)
        except Exception:
            pass

        return True
    except Exception as e:
        logger.error(f'[CICLO2] Erro ao aplicar filtros: {e}')
        return False


def _ciclo2_processar_livres(driver: WebDriver, client: Optional['PjeApiClient'] = None) -> int:
    """Seleciona todos os processos livres (sem gigs DOM nem gigs via API).

    Args:
        driver: WebDriver Selenium
        client: PjeApiClient — quando fornecido, faz checagem extra via API para
                detectar gigs sem prazo que não aparecem no DOM.

    Returns:
        Total de processos livres selecionados
    """
    try:
        import time as _time

        processos_com_gigs_api: List[str] = []
        if client is not None:
            # Extrai números de todos os processos visíveis na tabela
            linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
            numeros = [n for linha in linhas
                       if (n := _extrair_numero_processo_da_linha(linha))]
            if numeros:
                logger.info(f'[CICLO2][LIVRES] Verificando {len(numeros)} processos via API GIGS...')
                processos_com_gigs_api = _obter_processos_com_gigs_api(
                    client, numeros, max_workers=GIGS_API_MAX_WORKERS
                )
                logger.info(f'[CICLO2][LIVRES] {len(processos_com_gigs_api)} processo(s) com gigs via API')

        _t0 = _time.perf_counter()
        if processos_com_gigs_api:
            selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES_API, processos_com_gigs_api)
            _label = 'SCRIPT_SELECAO_LIVRES_API'
        else:
            selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES)
            _label = 'SCRIPT_SELECAO_LIVRES'
        _t1 = _time.perf_counter()
        try:
            logger.info(f'[LATENCIA][DETALHE] {_label}: {(_t1-_t0)*1000:.1f}ms')
        except Exception:
            pass

        if selecionados_livres > 0:
            logger.info(f'[CICLO2][LIVRES] ✅ {selecionados_livres} livre(s) selecionado(s)')
        else:
            logger.info('[CICLO2][LIVRES] Nenhum livre encontrado')

        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=4)
        except Exception:
            pass
        return selecionados_livres

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em _ciclo2_processar_livres: {e}')
        return 0


def _ciclo2_selecionar_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não-livres via JavaScript."""
    try:
        driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
        try:
            WebDriverWait(driver, 4).until(lambda d: len(d.execute_script("return document.querySelectorAll('mat-checkbox input[type=\\\"checkbox\\\"]:checked').length")) == 0)
        except Exception:
            pass

        import time as _time
        _t0 = _time.perf_counter()
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)
        _t1 = _time.perf_counter()
        try:
            logger.info(f'[LATENCIA][DETALHE] SCRIPT_SELECAO_NAO_LIVRES: {(_t1-_t0)*1000:.1f}ms')
        except Exception:
            pass
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']

        logger.info(f'[CICLO2][NAO_LIVRES] {selecionados}/{total_nao_livres} selecionados')

        ha_mais = total_nao_livres > selecionados
        return selecionados, ha_mais
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao selecionar não-livres: {e}')
        return 0, False