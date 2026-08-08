import logging
import time
from Fix.core import wait_for_page_load, safe_click_no_scroll

from selenium.webdriver.common.by import By
from Fix import espera

logger = logging.getLogger(__name__)


def dispensar_dialog_ordem_pendente(driver, log=True):
    """Fecha o dialog 'Ordens de bloqueio sem desdobramento apos 5 dias' clicando em 'Nao'."""
    try:
        dialog = driver.find_element(By.CSS_SELECTOR, 'sisbajud-dialog-aviso-ordem-pendente')
        if dialog.is_displayed():
            btn_nao = dialog.find_element(By.XPATH, './/button[.//span[contains(text(),"Não")]]')
            driver.execute_script("arguments[0].click();", btn_nao)
            if log:
                logger.info('[SISBAJUD] Dialog de ordens pendentes dispensado (clicou "Não")')
            espera.assentar(driver, 0.5)
            return True
    except Exception:
        pass
    return False

"""
SISB Series - Navegacao e extracao de ordens/nome
"""


def _navegar_e_extrair_ordens_serie(driver, serie, log=True):
    """
    Navega para uma serie especifica e extrai suas ordens.
    Usa o padrao menu-trigger + "Detalhar" (probe-confirmed).
    """
    try:
        id_serie = serie.get('id_serie')
        if not id_serie:
            return []

        if log:
            logger.info(f"[SISBAJUD] Navegando para detalhes da serie {id_serie} via menu")

        try:
            linha_index = serie.get('linha_index')
            if linha_index is not None:
                tabela = espera.elemento(driver, "table.mat-table", teto=10)
                linhas = tabela.find_elements(By.CSS_SELECTOR, "tbody tr.mat-row, tbody tr[mat-row]")

                if linha_index < len(linhas):
                    linha_el = linhas[linha_index]

                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", linha_el)
                    espera.assentar(driver, 0.5)

                    aberto = False

                    # Estrategia 1: menu-trigger (botao com tres pontinhos) + "Detalhar"
                    try:
                        btn_menu = linha_el.find_element(By.CSS_SELECTOR, "button.mat-menu-trigger.mat-icon-button")
                        driver.execute_script("arguments[0].click();", btn_menu)
                        espera.assentar(driver, 0.8)
                        itens_menu = driver.find_elements(By.CSS_SELECTOR, "button[role='menuitem'].mat-menu-item")
                        for item in itens_menu:
                            texto = (item.text or '').strip().lower()
                            if 'detalhar' in texto or 'detalhe' in texto:
                                driver.execute_script("arguments[0].click();", item)
                                aberto = True
                                break
                        if not aberto and itens_menu:
                            driver.execute_script("arguments[0].click();", itens_menu[0])
                            aberto = True
                    except Exception:
                        pass

                    # Estrategia 2: botao icon-button direto (fallback)
                    if not aberto:
                        try:
                            btn_detalhes = linha_el.find_element(By.CSS_SELECTOR, "button.mat-icon-button")
                            safe_click_no_scroll(driver, btn_detalhes)
                            aberto = True
                        except Exception:
                            pass

                    # Estrategia 3: clique na celula
                    if not aberto:
                        try:
                            driver.execute_script("arguments[0].click();", linha_el.find_element(By.CSS_SELECTOR, "td"))
                            aberto = True
                        except Exception:
                            pass

                    if not aberto:
                        raise Exception(f"Nao foi possivel abrir a serie {id_serie} (nenhuma estrategia funcionou)")

                    if log:
                        logger.info(f"[SISBAJUD] Serie {id_serie} aberta com sucesso")
                else:
                    raise Exception(f"Indice da linha {linha_index} fora de escopo ({len(linhas)} linhas)")
            else:
                raise Exception("Atributo linha_index nao fornecido na serie")

        except Exception as e:
            if log:
                logger.info(f"[SISBAJUD] Falha ao abrir serie, erro: {e}")
            return []

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
