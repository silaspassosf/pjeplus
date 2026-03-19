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
            logger.info(f"[SISBAJUD] Navegando para detalhes da serie {id_serie}")

        url_serie = f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes"
        # evitar reload completo se ja estamos na pagina correta
        if f"/{id_serie}/detalhes" not in driver.current_url:
            driver.get(url_serie)
            try:
                wait_for_page_load(driver, timeout=10)
            except Exception:
                # fallback de curto sleep para compatibilidade
                time.sleep(3)
        else:
            if log:
                logger.info(f"[SISBAJUD] Ja estamos na pagina da serie {id_serie}, evitando driver.get")

        if log:
            logger.info(f"[SISBAJUD] Navegacao direta bem-sucedida para serie {id_serie}")

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