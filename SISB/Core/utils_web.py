import logging
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Fix.core import safe_click as safe_click_fix, aguardar_e_clicar as aguardar_e_clicar_fix

from .utils_const import TIMEOUTS
from .utils_dados import log_sisbajud
from .utils_js import rate_limiting_manager

logger = logging.getLogger(__name__)

"""
SISB Core - Helpers Selenium
"""


def safe_click(driver, elemento, descricao="elemento", timeout=10):
    """Clique seguro com fallback para JavaScript."""
    _ = descricao
    return safe_click_fix(driver, elemento, timeout=timeout, log=False)


def simulate_human_movement(driver, elemento):
    """Simula movimento humano antes de interagir com elemento."""
    try:
        time.sleep(0.2)
        driver.execute_script("""
            arguments[0].scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'center'
            });
        """, elemento)
        time.sleep(0.3)
    except Exception as e:
        logger.error(f"[SISBAJUD] Erro no movimento humano: {e}")


def aguardar_elemento(driver, seletor, timeout=TIMEOUTS['elemento_padrao']):
    """Aguardar elemento com timeout padronizado."""
    from Fix.core import esperar_elemento
    return esperar_elemento(driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, log=False)


def aguardar_e_clicar(driver, seletor, timeout=TIMEOUTS['elemento_padrao']):
    """Aguardar elemento e clicar com tratamento de erros consolidado."""
    return aguardar_e_clicar_fix(driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, usar_js=True, log=False)


def escolher_opcao_sisbajud(driver, seletor_input, valor, timeout=TIMEOUTS['elemento_padrao']):
    """Escolher opcao em dropdown do SISBAJUD."""
    try:
        input_element = aguardar_elemento(driver, seletor_input, timeout)
        if not input_element:
            return False

        input_element.clear()
        input_element.send_keys(valor)
        time.sleep(1)

        opcao_seletor = f'span.mat-option-text:contains("{valor}")'
        return aguardar_e_clicar(driver, opcao_seletor, 5)

    except Exception as e:
        logger.error(f"[SISBAJUD] Erro ao escolher opcao {valor}: {e}")
        return False


def aplicar_rate_limiting(driver, acao):
    """Aplica rate limiting a uma acao do Selenium."""
    driver.execute_script(rate_limiting_manager())

    script = """
    return window.RateLimiter.executeWithRateLimit(async () => {
        return await arguments[0]();
    });
    """

    return driver.execute_script(script, acao)


def detectar_captcha(driver):
    """Detecta presenca de CAPTCHA na pagina."""
    try:
        indicadores_captcha = [
            'recaptcha',
            'captcha',
            'verify human',
            'robot',
            'automated'
        ]

        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()

        for indicador in indicadores_captcha:
            if indicador in page_text:
                return True

        captcha_selectors = [
            '.recaptcha',
            '#recaptcha',
            '[class*="captcha"]',
            '[id*="captcha"]'
        ]

        for selector in captcha_selectors:
            try:
                driver.find_element(By.CSS_SELECTOR, selector)
                return True
            except Exception:
                continue

        return False

    except Exception:
        return False


def anti_detection_measures(driver):
    """Aplica medidas anti-deteccao de automacao."""
    try:
        driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' }
            ],
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['pt-BR', 'pt', 'en-US', 'en'],
        });
        """)

        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    except Exception as e:
        log_sisbajud(f"Erro ao aplicar medidas anti-deteccao: {e}", "WARNING")


def smart_wait(driver, condition, timeout=TIMEOUTS['elemento_padrao'], interval=0.5):
    """Espera inteligente com deteccao de CAPTCHA e erros."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            if detectar_captcha(driver):
                log_sisbajud("CAPTCHA detectado! Aguardando intervencao manual...", "WARNING")
                time.sleep(30)
                continue

            result = condition()
            if result:
                return result

        except Exception as e:
            log_sisbajud(f"Erro durante smart_wait: {e}", "WARNING")

        time.sleep(interval)

    return None