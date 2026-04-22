"""
PEC.anexos.sisbajud - Módulo SISBAJUD PEC/anexos.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém funções específicas para processamento SISBAJUD.
"""

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, Any, List
from selenium.webdriver.remote.webdriver import WebDriver
from .anexos_juntador_base import wrapper_juntada_geral


def _obter_conteudo_relatorio_sisbajud(numero_processo: Optional[str] = None, debug: bool = True) -> Optional[str]:
    """Obtém conteúdo do relatório SISBAJUD do clipboard.txt centralizado."""
    try:
        from Fix.utils import obter_ultimo_conteudo_clipboard

        # Buscar do clipboard pelo número do processo
        conteudo = obter_ultimo_conteudo_clipboard(numero_processo, debug=debug)

        if conteudo:
            return conteudo
        else:
            return None

    except Exception as e:
        if debug: print(f'[SISB]  Erro: {e}')
        return None


def _wrapper_sisbajud_generico(
    driver: WebDriver,
    tipo: str,
    descricao: str,
    modelo: str,
    assinar: str,
    sigilo: str,
    prefixo_log: str,
    numero_processo: Optional[str] = None,
    debug: bool = True
) -> bool:
    """Wrapper genérico para SISBAJUD usando as funções já definidas."""
    def inserir_fn(driver: WebDriver, numero_processo: Optional[str] = numero_processo, debug: bool = True) -> bool:
        # Buscar conteúdo do clipboard pelo número do processo
        conteudo = _obter_conteudo_relatorio_sisbajud(numero_processo=numero_processo, debug=debug)
        if not conteudo:
            if debug:
                logger.info(f'[{prefixo_log}]  Conteúdo do relatório não disponível para processo: {numero_processo}')
            return False

        if debug:
            logger.info(f'[{prefixo_log}] Inserindo: {conteudo[:200]}...')

        # CORREÇÃO: Usar a mesma lógica robusta da PEC carta
        # Em vez de inserir_html_no_editor_apos_marcador com modo='replace'
        # Usar substituir_marcador_por_conteudo que é mais confiável
        from Fix.utils import substituir_marcador_por_conteudo
        return substituir_marcador_por_conteudo(
            driver=driver,
            conteudo_customizado=conteudo,
            debug=debug,
            marcador='--'
        )

    if debug:
        logger.info(f'[{prefixo_log}] Iniciando juntada com modelo: {modelo}')

    return wrapper_juntada_geral(
        driver=driver,
        tipo=tipo,
        descricao=descricao,
        modelo=modelo,
        assinar=assinar,
        sigilo=sigilo,
        inserir_conteudo=inserir_fn,
        coleta_conteudo=None,
        substituir_link=False,
        debug=debug
    )