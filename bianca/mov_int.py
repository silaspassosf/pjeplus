"""
Módulo de movimentação interna (mov_int) para o fluxo Bianca.
"""

import logging
logger = logging.getLogger(__name__)

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.core import aguardar_e_clicar
from atos.movimentos_fluxo import movimentar_inteligente

def mov_int(driver: WebDriver, destino: str, debug: bool = True) -> bool:
    """
    Executa movimentação interna para o destino especificado.
    Delega para movimentar_inteligente (atos.movimentos_fluxo) que é a implementação
    funcional e completa para qualquer destino, incluindo 'Aguardando audiência'.
    """
    if debug:
        logger.info('[BIANCA][MOV_INT] destino=%r', destino)

    try:
        # movimentar_inteligente retorna True/False e não possui parâmetro debug
        return movimentar_inteligente(driver, destino, timeout=15)
    except Exception as e:
        if debug:
            logger.error('[BIANCA][MOV_INT] Erro: %s', e)
        return False
