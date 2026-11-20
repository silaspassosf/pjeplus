"""atos.anexos.anexos_sisbajud - Conteúdo/relatório SISBAJUD e dispatch da juntada."""

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, Any, List
from .anexos_juntador_base import wrapper_juntada_com_navegacao


def _obter_conteudo_relatorio_sisbajud(numero_processo: Optional[str] = None, debug: bool = True) -> Optional[str]:
    """Obtém conteúdo do relatório SISBAJUD do clipboard.txt centralizado."""
    try:
        from Fix.utils import obter_ultimo_conteudo_clipboard

        conteudo = obter_ultimo_conteudo_clipboard(numero_processo, debug=debug)

        if conteudo:
            return conteudo
        else:
            return None

    except Exception as e:
        if debug: logger.info(f'[SISB]  Erro: {e}')
        return None


def _wrapper_sisbajud_generico(
    driver: Any,
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
    def inserir_fn(driver: Any, numero_processo: Optional[str] = numero_processo, debug: bool = True) -> bool:
        conteudo = _obter_conteudo_relatorio_sisbajud(numero_processo=numero_processo, debug=debug)
        if not conteudo:
            if debug:
                logger.info(f'[{prefixo_log}]  Conteúdo do relatório não disponível para processo: {numero_processo}')
            return False

        if debug:
            logger.info(f'[{prefixo_log}] Inserindo: {conteudo[:200]}...')

        from Fix.utils import substituir_marcador_por_conteudo
        return substituir_marcador_por_conteudo(
            driver=driver,
            conteudo_customizado=conteudo,
            debug=debug,
            marcador='--'
        )

    if debug:
        logger.info(f'[{prefixo_log}] Iniciando juntada com modelo: {modelo}')

    return wrapper_juntada_com_navegacao(
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


def executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log=True):
    """Dispatch canonico para juntada SISBAJUD baseado no tipo de fluxo."""
    try:
        from .anexos_wrappers import anex_bloqneg, anex_parcial

        if tipo_fluxo in ['NEGATIVO', 'DESBLOQUEIO']:
            resultado = anex_bloqneg(
                driver=driver_pje,
                numero_processo=numero_processo,
                debug=log
            )
        elif tipo_fluxo == 'POSITIVO':
            resultado = anex_parcial(
                driver=driver_pje,
                numero_processo=numero_processo,
                debug=log
            )
        else:
            return False

        return bool(resultado)

    except Exception as e:
        if log:
            logger.error('[SISBAJUD] Erro na juntada: %s', e)
        return False