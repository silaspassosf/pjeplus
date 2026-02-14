import logging
import time

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
            print(f"[SISBAJUD] Navegando para detalhes da serie {id_serie}")

        url_serie = f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes"
        driver.get(url_serie)
        time.sleep(3)

        if f"/{id_serie}/detalhes" not in driver.current_url:
            if log:
                print(f"[SISBAJUD] URL atual nao corresponde a serie: {driver.current_url}")
            return []

        if log:
            print(f"[SISBAJUD] Navegacao direta bem-sucedida para serie {id_serie}")

        time.sleep(2)

        from .ordens_dados import _extrair_ordens_da_serie
        ordens = _extrair_ordens_da_serie(driver, log)
        if log:
            print(f"[SISBAJUD] {len(ordens)} ordens extraidas da serie {id_serie}")

        return ordens

    except Exception as e:
        if log:
            print(f"[SISBAJUD] Erro na navegacao para serie {serie.get('id_serie', 'unknown')}: {str(e)}")
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
                    print(f"[SISBAJUD] Executado encontrado via expansion-panel: {header.text.strip()}")
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
                            print(f"[SISBAJUD] Executado encontrado via header: {nome}")
                        return nome
        except Exception:
            pass

        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "mat-card-title, .card-title, .reu-nome")
            for card in cards:
                text = card.text.strip()
                if text and len(text) > 3 and "Executado" not in text and "Ordem" not in text and "Serie" not in text:
                    if log:
                        print(f"[SISBAJUD] Executado encontrado via card: {text}")
                    return text
        except Exception:
            pass

        try:
            labels = driver.find_elements(By.XPATH, "//*[contains(text(), 'Reu') or contains(text(), 'Executado')]/following-sibling::*[1]")
            for label in labels:
                text = label.text.strip()
                if text and len(text) > 3:
                    if log:
                        print(f"[SISBAJUD] Executado encontrado via label: {text}")
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
                        print(f"[SISBAJUD] Executado encontrado via URL: {nome}")
                    return nome
        except Exception:
            pass

        if log:
            print("[SISBAJUD] Nome do executado nao identificado, usando placeholder")
        return "Executado"
    except Exception as e:
        if log:
            print(f"[SISBAJUD] Erro ao extrair nome do executado: {e}")
        return "Executado"