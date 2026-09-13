"""
judicial_modelos.py - Funções de modelos de documentos
=====================================================

Funções para inserção e monitoramento de modelos no editor de atos judiciais.
As funções de transição de rota (escolher_tipo_conclusao, aguardar_transicao_minutar, etc.)
residem canonicamente em atos.judicial_navegacao e são reexportadas aqui para retrocompatibilidade.
"""

from Fix.log import logger
from Fix import espera
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver

# Reexportação canônica de navegação / conclusão a partir de judicial_navegacao
from .judicial_navegacao import (
    verificar_estado_atual,
    escolher_tipo_conclusao,
    aguardar_transicao_minutar,
    focar_campo_minutar_se_necessario,
    navegar_para_minutar,
)


def esperar_insercao_modelo(driver: WebDriver, timeout: int = 8000) -> bool:
    """
    Aguarda a inserção do modelo com timeout simples.

    Args:
        driver: WebDriver instance
        timeout: Timeout em ms para aguardar inserção (padrão: 8000ms)

    Returns:
        bool: True (sempre retorna True após aguardar)
    """
    try:
        timeout_segundos = timeout / 1000.0
        logger.info(f'[MODELO] Aguardando {timeout_segundos}s para inserção do modelo...')
        espera.assentar(driver, timeout_segundos, motivo='inserção de modelo')
        logger.info('[MODELO] Timeout de espera concluído')
        return True
    except Exception as e:
        logger.warning(f'[MODELO] Erro na espera: {e}')
        return True