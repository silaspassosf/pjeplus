"""
PEC.anexos.extracao - Módulo de extração de dados PEC/anexos.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém funções de extração de dados do PJe.
"""

import logging
logger = logging.getLogger(__name__)

import re
import time
import pyperclip
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


def extrair_numero_processo_da_pagina(driver: WebDriver, debug: bool = True) -> Optional[str]:
    """
    Tenta extrair o número do processo do cabeçalho da página PJe.
    Se não encontrar, tenta clicar no ícone de copiar e ler do clipboard do sistema (se pyperclip disponível).
    Retorna o número do processo como string ou None.
    """
    try:
        # 1. Tenta extrair do cabeçalho
        try:
            el = driver.find_element(By.CSS_SELECTOR, 'span.texto-numero-processo')
            numero = el.text.strip()
            if numero:
                return numero
        except Exception as e:
            if debug:
                logger.debug(f'[EXTRATOR] Erro ao extrair do cabeçalho: {e}')

        # 2. Tenta clicar no ícone de copiar e ler do clipboard
        try:
            icone = driver.find_element(By.CSS_SELECTOR, 'i.far.fa-copy.fa-lg')
            driver.execute_script('arguments[0].click();', icone)
            time.sleep(0.2)
            try:
                numero = pyperclip.paste().strip()
                if numero:
                    return numero
            except ImportError:
                if debug:
                    logger.warning('[EXTRATOR] pyperclip não disponível para leitura do clipboard')
        except Exception as e:
            if debug:
                logger.debug(f'[EXTRATOR] Erro ao usar clipboard: {e}')

    except Exception as e:
        if debug:
            logger.error(f'[EXTRATOR] Erro geral: {e}')
    return None


def extrair_numero_processo_da_url(driver: WebDriver) -> str:
    """
    Extrai o numero do processo da URL atual.

    Args:
        driver: Selenium WebDriver

    Returns:
        str: Numero do processo ou identificacao alternativa
    """
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