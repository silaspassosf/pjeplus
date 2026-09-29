from typing import Any
import logging
from Fix.errors import PJePlusError
from .movimentos_fluxo import movimentar_inteligente

logger = logging.getLogger(__name__)


def mov_arquivar(driver: Any, debug: bool = False) -> bool:
    result = movimentar_inteligente(driver, 'Arquivar o processo', timeout=10)
    if result:
        try:
            from Fix.utils import aguardar_pagina_carregar
            aguardar_pagina_carregar(driver, timeout=10)
        except Exception as e:
            logger.warning('[MOV_ARQUIVAR] Erro ao aguardar carregamento: %s', e)
    else:
        logger.warning('[MOV_ARQUIVAR] movimentar_inteligente retornou False')
    return result


def mov_exec(driver: Any, debug: bool = False) -> bool:
    destinos = ['Iniciar execução']
    for destino in destinos:
        try:
            if movimentar_inteligente(driver, destino, timeout=8):
                return True
        except Exception:
            continue
    raise PJePlusError('Falha ao movimentar para Iniciar execução')


def mov_aud(driver: Any, debug: bool = False) -> bool:
    try:
        return movimentar_inteligente(driver, 'Aguardando audiência', timeout=8)
    except Exception:
        raise PJePlusError('Falha ao movimentar para Aguardando audiência')


def mov_prazo(driver: Any, debug: bool = False) -> bool:
    return True
