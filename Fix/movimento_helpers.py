import logging
logger = logging.getLogger(__name__)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import unicodedata
import time

def _normalize_text(s: str) -> str:
    if not s:
        return ''
    s = s.strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if ord(ch) < 128)
    s = re.sub(r'\s+', ' ', s)
    return s

def selecionar_movimento_dois_estagios(driver, movimento: str, timeout_select: int = 2) -> bool:
    """Seleciona movimentos em múltiplos estágios (comboboxes / complementos).

    Uso: chamar esta função dentro de `ato_judicial` quando o parâmetro `movimento`
    contém separadores (`/` ou `-`). A função tenta, em ordem:
      1) localizar `mat-select` dentro de `pje-complemento` e escolher `mat-option` que contenha o termo;
      2) preencher `input` ou `textarea` dentro do complemento correspondente;
      3) fallback: abrir qualquer `mat-select` visível e buscar a opção.

    Retorna True se todas as etapas (segmentos) do movimento foram satisfeitas, False caso contrário.
    """
    termos = [t.strip() for t in re.split(r'[/\\-]', movimento) if t.strip()]
    if not termos:
        return False

    complementos = driver.find_elements(By.CSS_SELECTOR, 'pje-complemento')
    usados = set()

    for termo in termos:
        termo_norm = _normalize_text(termo)
        encontrado = False

        # 1) tenta mat-select dentro dos complementos
        for idx, comp in enumerate(complementos):
            if idx in usados:
                continue
            try:
                sel = comp.find_element(By.CSS_SELECTOR, 'mat-select')
                try:
                    driver.execute_script('arguments[0].parentElement.parentElement.click();', sel)
                except Exception:
                    driver.execute_script('arguments[0].click();', sel)

                opts = WebDriverWait(driver, timeout_select).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                )
                for op in opts:
                    try:
                        if termo_norm in _normalize_text(op.text or ''):
                            driver.execute_script('arguments[0].click();', op)
                            usados.add(idx)
                            encontrado = True
                            break
                    except Exception:
                        continue
                if encontrado:
                    break
            except Exception:
                continue

        # 2) tentar input/textarea no complemento
        if not encontrado:
            for idx, comp in enumerate(complementos):
                if idx in usados:
                    continue
                try:
                    inp = comp.find_element(By.CSS_SELECTOR, 'input')
                    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", inp, termo)
                    usados.add(idx)
                    encontrado = True
                    break
                except Exception:
                    try:
                        ta = comp.find_element(By.CSS_SELECTOR, 'textarea')
                        driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true}));", ta, termo)
                        usados.add(idx)
                        encontrado = True
                        break
                    except Exception:
                        continue

        # 3) fallback: tentar qualquer mat-select visível na página
        if not encontrado:
            all_selects = driver.find_elements(By.CSS_SELECTOR, 'mat-select')
            for sel in all_selects:
                try:
                    try:
                        driver.execute_script('arguments[0].parentElement.parentElement.click();', sel)
                    except Exception:
                        driver.execute_script('arguments[0].click();', sel)
                    opts = WebDriverWait(driver, 1).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                    )
                    for op in opts:
                        if termo_norm in _normalize_text(op.text or ''):
                            driver.execute_script('arguments[0].click();', op)
                            encontrado = True
                            break
                    if encontrado:
                        break
                except Exception:
                    continue

        if not encontrado:
            return False

        time.sleep(0.2)

    return True

def selecionar_movimento_auto(driver, movimento: str) -> bool:
    """Chamada auxiliar: decide a estratégia e executa seleção.

    - se `movimento` contém `/` ou `-` → usa `selecionar_movimento_dois_estagios`
    - caso contrário retorna False para indicar que o chamador deve usar a lógica por checkbox

    Retorna True se a seleção foi feita aqui, False se o chamador deve usar fluxo por checkbox.
    """
    if not movimento:
        return False
    if '/' in movimento or '-' in movimento:
        return selecionar_movimento_dois_estagios(driver, movimento)
    return False
