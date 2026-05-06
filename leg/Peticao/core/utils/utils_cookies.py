import logging
logger = logging.getLogger(__name__)

"""
Utils cookies module for Peticao - contains cookie management functions
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Configurações de cookies
USAR_COOKIES_AUTOMATICO = True
SALVAR_COOKIES_AUTOMATICO = True
COOKIES_DIR = Path.home() / '.pjeplus_cookies'

def verificar_e_aplicar_cookies(driver):
    """Verifica e aplica cookies salvos anteriormente"""
    try:
        if not USAR_COOKIES_AUTOMATICO:
            return False

        # Aqui seria implementada a lógica para carregar e aplicar cookies
        # Esta é uma implementação simplificada
        cookies_file = COOKIES_DIR / 'pje_cookies.json'

        if not cookies_file.exists():
            return False

        try:
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    continue  # Ignora cookies inválidos

            driver.refresh()
            return True
        except Exception:
            return False
    except Exception:
        return False

def salvar_cookies_sessao(driver, info_extra=''):
    """Salva cookies da sessão atual"""
    try:
        if not SALVAR_COOKIES_AUTOMATICO:
            return

        COOKIES_DIR.mkdir(exist_ok=True)
        cookies_file = COOKIES_DIR / 'pje_cookies.json'

        cookies = driver.get_cookies()

        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        logger.info(f"Cookies salvos: {len(cookies)} itens - {info_extra}")
    except Exception as e:
        logger.error(f"Erro ao salvar cookies: {e}")