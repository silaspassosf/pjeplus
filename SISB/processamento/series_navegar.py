import logging
import time
from Fix.core import wait_for_page_load

from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

"""
SISB Series - Navegacao e extracao de ordens/nome
"""


def _navegar_e_extrair_ordens_serie(driver, serie, log=True):
    """
    Navega para uma serie especifica e extrai suas ordens.
    """
    try:
        id_serie = serie.get('id_serie')
        if not id_serie:
            return []

        if log:
            logger.info(f"[SISBAJUD] Navegando para detalhes da serie {id_serie} via clique")

        try:
            # Identificar e clicar na linha correspondente na SPA
            linha_index = serie.get('linha_index')
            if linha_index is not None:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                tabela = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table"))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, "tbody tr.mat-row, tbody tr[mat-row]")
                
                if linha_index < len(linhas):
                    linha_el = linhas[linha_index]
                    
                    # Scroll para o elemento
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", linha_el)
                    time.sleep(0.5)
                    
                    # Tentar clicar no botao "detalhes" (lupa) ou na linha inteira
                    try:
                        btn_detalhes = linha_el.find_element(By.CSS_SELECTOR, "button.mat-icon-button, button mat-icon")
                        driver.execute_script("arguments[0].click();", btn_detalhes)
                    except:
                        # Fallback: clicar na celula
                        driver.execute_script("arguments[0].click();", linha_el.find_element(By.CSS_SELECTOR, "td"))
                        
                    if log:
                        logger.info(f"[SISBAJUD] Clique bem-sucedido na serie {id_serie}")
                else:
                    raise Exception(f"Indice da linha {linha_index} fora de escopo ({len(linhas)} linhas)")
            else:
                raise Exception("Atributo linha_index nao fornecido na serie")
                
        except Exception as e:
            if log:
                logger.info(f"[SISBAJUD] Falha ao clicar na serie, erro: {e}")
            return []

        # Espera reativa: aguardar carregamento mínimo antes de extrair ordens
        try:
            wait_for_page_load(driver, timeout=6)
        except Exception:
            time.sleep(1)

        from .ordens_dados import _extrair_ordens_da_serie
        ordens = _extrair_ordens_da_serie(driver, log)
        if log:
            logger.info(f"[SISBAJUD] {len(ordens)} ordens extraidas da serie {id_serie}")

        return ordens

    except Exception as e:
        if log:
            logger.info(f"[SISBAJUD] Erro na navegacao para serie {serie.get('id_serie', 'unknown')}: {str(e)}")
        return []


def _extrair_nome_executado_serie(driver, log=True):
    """
    Tenta extrair o nome do executado na pagina de detalhes da serie.
    """
    try:
        try:
            header = driver.find_element(By.CSS_SELECTOR, "mat-expansion-panel-header .col-reu-dados-nome-pessoa")
            if header and header.text.strip():
                if log:
                    logger.info(f"[SISBAJUD] Executado encontrado via expansion-panel: {header.text.strip()}")
                return header.text.strip()
        except Exception:
            pass

        try:
            header = driver.find_element(By.CSS_SELECTOR, "div.header-title, .mat-card-title, h1, h2")
            if header:
                text = header.text
                if "-" in text:
                    nome = text.split("-")[-1].strip()
                    if nome and len(nome) > 3:
                        if log:
                            logger.info(f"[SISBAJUD] Executado encontrado via header: {nome}")
                        return nome
        except Exception:
            pass

        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "mat-card-title, .card-title, .reu-nome")
            for card in cards:
                text = card.text.strip()
                if text and len(text) > 3 and "Executado" not in text and "Ordem" not in text and "Serie" not in text:
                    if log:
                        logger.info(f"[SISBAJUD] Executado encontrado via card: {text}")
                    return text
        except Exception:
            pass

        try:
            labels = driver.find_elements(By.XPATH, "//*[contains(text(), 'Reu') or contains(text(), 'Executado')]/following-sibling::*[1]")
            for label in labels:
                text = label.text.strip()
                if text and len(text) > 3:
                    if log:
                        logger.info(f"[SISBAJUD] Executado encontrado via label: {text}")
                    return text
        except Exception:
            pass

        try:
            url = driver.current_url
            if "nome=" in url.lower():
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'nome' in params:
                    nome = params['nome'][0]
                    if log:
                        logger.info(f"[SISBAJUD] Executado encontrado via URL: {nome}")
                    return nome
        except Exception:
            pass

        if log:
            logger.info("[SISBAJUD] Nome do executado nao identificado, usando placeholder")
        return "Executado"
    except Exception as e:
        if log:
            logger.info(f"[SISBAJUD] Erro ao extrair nome do executado: {e}")
        return "Executado"