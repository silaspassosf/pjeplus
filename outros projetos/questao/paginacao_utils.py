import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def ir_para_proxima_pagina(driver):
    """
    Tenta clicar no botão de próxima página na paginação do QConcursos.
    Retorna True se conseguiu avançar, False se não encontrou o botão.
    """
    try:
        # Primeiro tenta pelo seletor fornecido pelo usuário
        btns = driver.find_elements(By.CSS_SELECTOR, 'body > div.q-root > main > div.container > nav > div > a.q-next.btn.btn-default')
        if not btns:
            # Alternativa: busca pelo ícone
            btns = driver.find_elements(By.CSS_SELECTOR, 'a > i.q-icon.q-icon-caret-right-solid')
            if btns:
                btns = [btn.find_element(By.XPATH, './..') for btn in btns]  # Pega o <a> pai do <i>
        for btn in btns:
            if btn.is_enabled() and btn.is_displayed():
                btn.click()
                print('[INFO] Cliquei no botão de próxima página (seletor customizado)')
                time.sleep(2.5)
                return True
        print('[INFO] Nenhum botão de próxima página encontrado pelo seletor customizado.')
    except Exception as e:
        print(f'[ERRO] ao tentar avançar página (seletor customizado): {e}')
    return False

def ir_para_pagina(driver, numero):
    """
    Tenta ir para uma página específica na paginação.
    """
    try:
        paginadores = driver.find_elements(By.CSS_SELECTOR, 'ul.pagination li a')
        for pag in paginadores:
            if pag.text.strip() == str(numero):
                pag.click()
                time.sleep(2.5)
                return True
    except Exception as e:
        print(f'[ERRO] ao tentar ir para a página {numero}: {e}')
    return False
