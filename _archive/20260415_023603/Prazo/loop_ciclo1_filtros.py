from .loop_base import *


def _ciclo1_aplicar_filtro_fases(driver: WebDriver) -> Union[bool, str]:
    """Aplica filtro de liquidação/execução no painel 14.

    Returns:
        True: filtro aplicado e processos encontrados
        "no_more_processes": filtro aplicado mas sem processos
        False: erro ao aplicar filtro
    """
    try:
        if not pausar_confirmacao('CICLO1/FILTRO_FASES', 'Aplicar filtro liquidação/execução'):
            return False
        t0 = time.perf_counter()
        result = filtrofases(driver, fases_alvo=['liquidação', 'execução'])
        t_filtro = time.perf_counter() - t0
        logger.info(f'[LATENCIA][DETALHE] CICLO1 filtrofases: {t_filtro:.3f}s')
        if not result:
            # filtrofases retorna False quando não encontra as opções para selecionar
            # Isso significa que não há processos nessas fases
            return "no_more_processes"

        # AGUARDAR LISTA CARREGAR - loop manual com break imediato ao encontrar células
        t1 = time.perf_counter()
        timeout_espera = 3.0  # máximo 3 segundos de espera

        seletor_celula_processo = 'td.td-class span.link.processo'
        xpath_vazio = "//span[contains(text(), 'Não há processos neste tema')]"

        # Loop manual: break assim que encontrar células ou mensagem vazio
        while time.perf_counter() - t1 < timeout_espera:
            try:
                celulas = driver.find_elements(By.CSS_SELECTOR, seletor_celula_processo)
                if len(celulas) > 0:
                    t_lista = time.perf_counter() - t1
                    logger.info(f'[CICLO1][FILTRO] Células encontradas em {t_lista:.3f}s')
                    logger.info(f'[LATENCIA][DETALHE] CICLO1 espera lista: {t_lista:.3f}s')
                    return True
            except Exception:
                pass

            # Verificar se há mensagem de vazio
            try:
                vazios = driver.find_elements(By.XPATH, xpath_vazio)
                if any(el.is_displayed() for el in vazios):
                    t_lista = time.perf_counter() - t1
                    logger.info(f'[CICLO1][FILTRO] Mensagem vazio encontrada em {t_lista:.3f}s')
                    logger.info(f'[LATENCIA][DETALHE] CICLO1 espera lista: {t_lista:.3f}s')
                    return "no_more_processes"
            except Exception:
                pass

            time.sleep(0.1)  # Sleep curto entre tentativas

        # Timeout da espera atingido - fazer avaliação final rápida
        t_lista = time.perf_counter() - t1
        logger.info(f'[CICLO1][FILTRO] Timeout de espera atingido ({timeout_espera}s), avaliando lista...')
        logger.info(f'[LATENCIA][DETALHE] CICLO1 espera lista: {t_lista:.3f}s')

        # Verificação rápida final se há células
        try:
            celulas = driver.find_elements(By.CSS_SELECTOR, seletor_celula_processo)
            if len(celulas) > 0:
                logger.info(f'[CICLO1][FILTRO] {len(celulas)} célula(s) de processo detectada(s) na avaliação final')
                return True
        except Exception:
            pass

        time.sleep(0.2)
        return True
    except Exception as e:
        logger.error(f'[CICLO1] Erro ao aplicar filtro de fases: {e}')
        return False


def _verificar_quantidade_processos_paginacao(driver: WebDriver) -> int:
    """
    Verifica quantidade de processos lendo o elemento de paginação.
    Retorna: quantidade de processos ou -1 se não conseguir detectar
    """
    try:
        # Buscar o elemento span.total-registros que contém "X - Y de Z"
        total_elem = driver.find_element(By.CSS_SELECTOR, 'span.total-registros')
        texto = total_elem.text.strip()

        # Extrair o total (último número após "de")
        # Formato: "1 - 1 de 1" ou "1 - 20 de 150" ou "0 de 0"
        import re
        match = re.search(r'de\s+(\d+)', texto)
        if match:
            total = int(match.group(1))
            return total

        # Fallback: tentar detectar "0 de 0" ou formato sem hífen
        if '0 de 0' in texto or '0 - 0 de 0' in texto:
            return 0

        return -1

    except Exception as e:
        logger.error(f'[CICLO1]  Erro ao ler paginação: {e}')
        return -1