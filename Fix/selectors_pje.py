# selectors_pje.py
# Seletores usados no projeto de automacao PJe TRT2

from Fix.log import logger

BTN_TAREFA_PROCESSO = 'button[mattooltip="Abre a tarefa do processo"]'

def buscar_seletor_robusto(driver, textos, timeout=10, log=True):
    """
    Busca robusta de elementos por texto, aria-label, mattooltip, alt, src, class, etc.
    Retorna o primeiro elemento encontrado que contenha o texto em qualquer desses atributos.
    """
    from selenium.webdriver.common.by import By
    import time
    # 1. Busca por aria-label, placeholder, name, title
    for texto in textos:
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR,
                f'*[aria-label*="{texto}"], *[placeholder*="{texto}"], *[name*="{texto}"], *[title*="{texto}"]')
            for el in elementos:
                if el.is_displayed():
                    if log:
                        logger.debug(f'[SELECTOR] Found by aria-label/placeholder/title: {texto}')
                    return el
        except Exception:
            continue
    # 2. Busca por texto visível
    for texto in textos:
        try:
            xpath = f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{texto.lower()}')]"
            elementos = driver.find_elements(By.XPATH, xpath)
            for el in elementos:
                if el.is_displayed():
                    if log:
                        logger.debug(f'[SELECTOR] Found by visible text: {texto}')
                    return el
        except Exception:
            continue
    # 3. Fallback: busca por ícones (img/button) com mattooltip, alt, src, class
    for texto in textos:
        try:
            img = driver.find_elements(By.CSS_SELECTOR, f'img[mattooltip*="{texto}"]')
            if img:
                if log:
                    logger.debug(f'[SELECTOR] Found by img[mattooltip]: {texto}')
                return img[0]
            img_alt = driver.find_elements(By.CSS_SELECTOR, f'img[alt*="{texto}"]')
            if img_alt:
                if log:
                    logger.debug(f'[SELECTOR] Found by img[alt]: {texto}')
                return img_alt[0]
            img_src = driver.find_elements(By.CSS_SELECTOR, f'img[src*="{texto}"]')
            if img_src:
                if log:
                    logger.debug(f'[SELECTOR] Found by img[src]: {texto}')
                return img_src[0]
            btn = driver.find_elements(By.CSS_SELECTOR, f'button[mattooltip*="{texto}"]')
            if btn:
                if log:
                    logger.debug(f'[SELECTOR] Found by button[mattooltip]: {texto}')
                return btn[0]
        except Exception:
            continue
    if log:
        logger.debug(f'[SELECTOR] No element found for: {textos}')
    return None