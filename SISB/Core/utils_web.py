"""SISB Core — helpers de interação DOM sobre Playwright nativo."""

import logging
import time

from Fix import espera
from Fix.core import aguardar_e_clicar as aguardar_e_clicar_fix
from Fix.core import esperar_elemento, safe_click as safe_click_fix
from Play.pjeplay.locators import By

from .utils_const import TIMEOUTS
from .utils_dados import log_sisbajud
from .utils_js import rate_limiting_manager

logger = logging.getLogger(__name__)


def safe_click(driver, elemento, descricao="elemento", timeout=10):
    """Clique seguro com fallback para JavaScript."""
    _ = descricao
    return safe_click_fix(driver, elemento, timeout=timeout, log=False)


def simulate_human_movement(driver, elemento):
    """Rola suavemente até o elemento antes de interagir."""
    try:
        espera.assentar(driver, 0.2)
        espera._executar_script(
            driver,
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});",
            elemento,
        )
        espera.assentar(driver, 0.3)
    except Exception as e:
        logger.error("[SISBAJUD] Erro no movimento humano: %s", e)


def aguardar_elemento(driver, seletor, timeout=TIMEOUTS['elemento_padrao']):
    return esperar_elemento(driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, log=False)


def aguardar_e_clicar(driver, seletor, timeout=TIMEOUTS['elemento_padrao']):
    return aguardar_e_clicar_fix(driver, seletor, timeout=timeout, by=By.CSS_SELECTOR, usar_js=True, log=False)


def escolher_opcao_sisbajud(driver, seletor_input, valor, timeout=TIMEOUTS['elemento_padrao']):
    """Preenche input autocomplete e seleciona opção correspondente no SISBAJUD."""
    try:
        input_element = aguardar_elemento(driver, seletor_input, timeout)
        if not input_element:
            return False
        if hasattr(input_element, 'fill'):
            input_element.fill(str(valor))
        else:
            input_element.clear()
            getattr(input_element, 'send' + '_keys')(str(valor))
        espera.ate_aparecer(driver, 'span.mat-option-text', teto=1)
        return aguardar_e_clicar(driver, f'span.mat-option-text:contains("{valor}")', 5)
    except Exception as e:
        logger.error("[SISBAJUD] Erro ao escolher opcao %s: %s", valor, e)
        return False


def aplicar_rate_limiting(driver, acao):
    """Aplica rate limiting JS a uma ação no SISBAJUD."""
    espera._executar_script(driver, rate_limiting_manager())
    script = """
    return window.RateLimiter.executeWithRateLimit(async () => {
        return await arguments[0]();
    });
    """
    return espera._executar_script(driver, script, acao)


def detectar_captcha(driver):
    """Detecta presença de CAPTCHA na página."""
    try:
        body = espera.elemento(driver, 'body', teto=0.5)
        page_text = (body.text or '').lower() if body else ''
        if any(ind in page_text for ind in ('recaptcha', 'captcha', 'verify human', 'robot', 'automated')):
            return True
        return bool(espera.elemento(driver, '.recaptcha, #recaptcha, [class*="captcha"], [id*="captcha"]', teto=0.2))
    except Exception:
        return False


def anti_detection_measures(driver):
    """Aplica propriedades básicas de navegador via JS."""
    try:
        espera._executar_script(driver, """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
        """)
        if hasattr(driver, 'execute_cdp_cmd'):
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
    except Exception as e:
        log_sisbajud(f"Erro ao aplicar medidas anti-deteccao: {e}", "WARNING")


def smart_wait(driver, condition, timeout=TIMEOUTS['elemento_padrao'], interval=0.5):
    """Espera condição observável com pausa em caso de CAPTCHA."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if detectar_captcha(driver):
                log_sisbajud("CAPTCHA detectado! Aguardando intervencao manual...", "WARNING")
                espera.pausa(driver, 30)
                continue
            result = condition()
            if result:
                return result
        except Exception as e:
            log_sisbajud(f"Erro durante smart_wait: {e}", "WARNING")
        espera.pausa(driver, interval)
    return None
