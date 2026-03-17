import time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

from Fix import aguardar_e_clicar, safe_click
from Fix.log import logger


def _selecionar_checkbox_intimacao(driver: WebDriver, linha: WebElement, log: bool = True) -> bool:
    """Marca o checkbox da linha alvo usando poucas tentativas eficientes."""
    try:
        checkbox_element = linha.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox')
        input_checkbox = checkbox_element.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
    except Exception:
        return False

    tentativas = (
        lambda: safe_click(driver, checkbox_element, timeout=3, log=False),
        lambda: safe_click(driver, input_checkbox, timeout=3, log=False),
        lambda: driver.execute_script("arguments[0].click();", checkbox_element),
        lambda: driver.execute_script("arguments[0].click();", input_checkbox),
    )

    def marcado() -> bool:
        try:
            return input_checkbox.is_selected()
        except StaleElementReferenceException:
            try:
                novo_input = linha.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox input[type="checkbox"]')
                return novo_input.is_selected()
            except Exception:
                return False

    for tentativa in tentativas:
        try:
            tentativa()
            time.sleep(0.3)
            if marcado():
                return True
        except Exception:
            continue

    return False

def fechar_intimacao(driver: WebDriver, log: bool = True) -> bool:
    """Fecha a intimação do processo."""
    logger.info('[INTIMACAO] === INÍCIO ===')
    try:
        # 1. Abrir menu
        logger.info('[INTIMACAO] [1] Tentando abrir menu #botao-menu...')
        if not aguardar_e_clicar(driver, '#botao-menu', timeout=10):
            logger.info('[INTIMACAO] [1]  FALHOU: Não conseguiu abrir menu')
            return False
        logger.info('[INTIMACAO] [1]  Menu aberto')
        time.sleep(0.5)
        
        # 2. Clicar Expedientes
        logger.info('[INTIMACAO] [2] Tentando clicar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Expedientes"]', timeout=5):
            logger.info('[INTIMACAO] [2]  FALHOU: Não conseguiu clicar Expedientes')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return False
        logger.info('[INTIMACAO] [2]  Botão Expedientes clicado')
        
        # 3. Aguardar modal
        logger.info('[INTIMACAO] [3] Aguardando modal abrir...')
        time.sleep(2)
        
        # 4. Buscar linha prazo 30
        logger.info('[INTIMACAO] [4] Buscando linhas com prazo 30...')
        rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
        logger.info(f'[INTIMACAO] [4] Total de linhas encontradas: {len(rows)}')
        
        linha_prazo_30 = None
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 11:
                    prazo = cells[8].text.strip()
                    fechado = cells[10].text.strip().lower()
                    
                    if prazo == '30' and fechado != "sim":
                        linha_prazo_30 = row
                        logger.info(f'[INTIMACAO] [4]  Linha {i+1} selecionada (prazo 30, não fechado)')
                        break
            except Exception as e:
                logger.info(f'[INTIMACAO] [4] Erro na linha {i+1}: {str(e)[:40]}')
                continue
        
        if not linha_prazo_30:
            logger.info('[INTIMACAO] [4]  Nenhuma linha prazo 30 não fechada encontrada')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return True
        
        # 5. Clicar checkbox
        logger.info('[INTIMACAO] [5] Tentando marcar checkbox...')
        if not _selecionar_checkbox_intimacao(driver, linha_prazo_30, log=log):
            logger.info('[INTIMACAO] [5]  FALHOU: Não conseguiu marcar checkbox')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return False
        logger.info('[INTIMACAO] [5]  Checkbox marcado')
        
        # 6. Clicar Fechar Expedientes
        logger.info('[INTIMACAO] [6] Tentando clicar Fechar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Fechar Expedientes"]', timeout=5):
            logger.info('[INTIMACAO] [6]  FALHOU: Não conseguiu clicar Fechar Expedientes')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return False
        logger.info('[INTIMACAO] [6]  Botão Fechar Expedientes clicado')
        time.sleep(1)
        
        # 7. Confirmar
        logger.info('[INTIMACAO] [7] Confirmando fechamento...')
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
        time.sleep(1)
        
        # AGUARDAR LATÊNCIA APÓS FECHAR INTIMAÇÃO
        logger.info('[INTIMACAO] [8] Aguardando latência pós-fechamento...')
        time.sleep(3)  # Espera adicional para estabilização da página
        
        logger.info('[INTIMACAO] === SUCESSO ===')
        
        return True
        
    except Exception as e:
        logger.info(f'[INTIMACAO] === ERRO GERAL: {str(e)[:150]} ===')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            pass
        return False