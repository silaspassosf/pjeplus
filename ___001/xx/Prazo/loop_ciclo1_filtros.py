from .loop_base import *


def _ciclo1_aplicar_filtro_fases(driver: WebDriver) -> Union[bool, str]:
    """Aplica filtro de liquidação/execução no painel 14.

    Returns:
        True: filtro aplicado e processos encontrados
        "no_more_processes": filtro aplicado mas sem processos
        False: erro ao aplicar filtro
    """
    try:
        result = filtrofases(driver, fases_alvo=['liquidação', 'execução'])
        if not result:
            # filtrofases retorna False quando não encontra as opções para selecionar
            # Isso significa que não há processos nessas fases
            return "no_more_processes"

        # AGUARDAR LISTA CARREGAR - verificar se há processos ou mensagem de vazio
        max_tentativas = 20  # ~6 segundos
        lista_carregada = False

        for _ in range(max_tentativas):
            # Verificar se apareceu mensagem de lista vazia
            try:
                msg_vazia = driver.find_element(By.XPATH, "//span[contains(text(), 'Não há processos neste tema')]")
                if msg_vazia.is_displayed():
                    return "no_more_processes"
            except Exception:
                pass

            # Verificar se há processos na tabela
            try:
                linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class, tr.cdk-drag')
                if len(linhas) > 0:
                    lista_carregada = True
                    break
            except Exception:
                pass

            time.sleep(0.3)

        time.sleep(1.5)
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