import logging
logger = logging.getLogger(__name__)

"""
Fix.navigation.sigilo - Módulo de controle de sigilo e visibilidade de documentos.

Parte da refatoração do Fix/core.py para melhor granularidade IA.
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException


def visibilidade_sigilosos(driver, polo='ativo', log=True):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente, conforme lógica do gigs-plugin.js.
    polo: 'ambos', 'ativo', 'passivo' ou 'nenhum'
    """
    try:
        # ✨ OTIMIZADO: Limpar overlays antes de buscar documento
        try:
            from Fix.headless_helpers import limpar_overlays_headless
            limpar_overlays_headless(driver)
        except ImportError:
            pass

        # 1. Seleciona o último documento sigiloso na timeline
        sigiloso_link = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline a.tl-documento.is-sigiloso:last-child')
        if not sigiloso_link:
            if log:
                logger.error('[VISIBILIDADE][ERRO] Documento sigiloso não encontrado na timeline.')
            return False

        # Extrai id do documento
        aria_label = sigiloso_link.get_attribute('aria-label')
        m = re.search(r'Id[:\.\s]+([A-Za-z0-9]{6,8})', aria_label or '')
        if not m:
            if log:
                logger.error('[VISIBILIDADE][ERRO] Não foi possível extrair o ID do documento.')
            return False

        id_documento = m.group(1)
        if log:
            pass

        # 2. Ativa múltipla seleção
        btn_multi = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]')
        # ✨ OTIMIZADO: Click headless-safe
        try:
            btn_multi.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", btn_multi)
        time.sleep(0.5)

        # 3. Marca o checkbox do documento
        mat_checkbox = driver.find_element(By.CSS_SELECTOR, f'mat-card[id*="{id_documento}"] mat-checkbox label')
        # ✨ OTIMIZADO: Click headless-safe
        try:
            mat_checkbox.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", mat_checkbox)
        time.sleep(0.5)

        # 4. Clica no botão de visibilidade
        btn_visibilidade = driver.find_element(By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
        # ✨ OTIMIZADO: Click headless-safe
        try:
            btn_visibilidade.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", btn_visibilidade)
        time.sleep(1)

        # 5. No modal, seleciona o polo desejado
        if polo == 'ativo':
            icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nameTabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo')
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'passivo':
            icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nameTabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo')
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'ambos':
            # Marca todos
            btn_todos = driver.find_element(By.CSS_SELECTOR, 'th button')
            btn_todos.click()

        # 6. Confirma no botão Salvar
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
        )
        btn_salvar.click()
        time.sleep(1)

        # 7. Oculta múltipla seleção
        try:
            btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
            btn_ocultar.click()
        except:
            pass

        if log:
            pass
        return True

    except Exception as e:
        if log:
            logger.error(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}')
        return False