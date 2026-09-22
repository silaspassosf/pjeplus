"""
atos.anexos.extracao - Extração de dados do PJe.
"""

import logging
logger = logging.getLogger(__name__)

import re
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


def extrair_numero_processo_da_url(driver: WebDriver) -> str:
    """Extrai o número do processo da URL atual."""
    try:
        url_atual = driver.current_url
        padroes = [
            r'processo/(\d+)',
            r'processoTrfId=(\d+)',
            r'numeroProcesso=(\d+)',
            r'idProcesso=(\d+)',
        ]
        for padrao in padroes:
            match = re.search(padrao, url_atual)
            if match:
                return match.group(1)
        if 'pje' in url_atual.lower():
            partes = url_atual.split('/')
            for parte in partes:
                if parte.isdigit() and len(parte) > 6:
                    return parte
        return f"URL_{hash(url_atual) % 10000}"
    except Exception as e:
        return f"ERRO_{str(e)[:20]}"
