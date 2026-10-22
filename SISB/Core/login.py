import os
import random
import time
import traceback

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

"""
SISB Core - Login e simulacao humana
"""


def simular_movimento_humano(driver, elemento):
    """Simula movimento de mouse humano antes de clicar em elemento."""
    try:
        actions = ActionChains(driver)

        if random.random() < 0.7:
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            actions.move_to_element_with_offset(elemento, offset_x, offset_y)
            actions.pause(random.uniform(0.1, 0.3))

        actions.move_to_element(elemento)
        actions.pause(random.uniform(0.1, 0.5))
        actions.perform()

    except Exception:
        pass


def login_automatico_sisbajud(driver):
    """Login automatizado no SISBAJUD delegando para SISB.core."""
    from SISB.core import login_automatico_sisbajud as _impl
    return _impl(driver)



def login_manual_sisbajud(driver, aguardar_url_final=True):
    """Login manual para SISBAJUD."""
    try:
        logger.info('[SISBAJUD][LOGIN_MANUAL] Navegando para SISBAJUD e aguardando login manual...')

        current_url = driver.current_url
        if not any(ind in current_url.lower() for ind in ['sisbajud', 'login', 'auth', 'realms']):
            driver.get('https://sisbajud.cnj.jus.br/')
        else:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Ja esta na pagina de autenticacao, aguardando conclusao...')

        timeout = 300
        if not aguardar_url_final:
            return False
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: any(h in (d.current_url or '').lower() for h in ['sisbajud.cnj.jus.br', 'sisbajud.pdpj.jus.br', 'sisbajud'])
                and not any(ind in (d.current_url or '').lower() for ind in ['login', 'auth', 'realms', 'sso.cloud'])
            )
            logger.info('[SISBAJUD][LOGIN_MANUAL] Login detectado manualmente (URL mudou: %s).', driver.current_url)
            try:
                from driver_config import salvar_cookies_sessao, salvar_cookies_sisbajud, SALVAR_COOKIES_AUTOMATICO
                if SALVAR_COOKIES_AUTOMATICO:
                    try:
                        salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                    except Exception as e:
                        logger.info(f"[SISBAJUD][LOGIN_MANUAL] Falha ao salvar cookies: {e}")
            except Exception:
                pass
            return True
        except Exception:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Timeout aguardando login manual.')
            return False
    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN_MANUAL] Erro durante login manual: {e}')
        return False