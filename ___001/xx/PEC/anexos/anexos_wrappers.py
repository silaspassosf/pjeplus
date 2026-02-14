"""
PEC.anexos.wrappers - Módulo de wrappers específicos PEC/anexos.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém wrappers específicos para diferentes tipos de juntada.
"""

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Callable
from .anexos_sisbajud import _wrapper_sisbajud_generico, _obter_conteudo_relatorio_sisbajud
from .anexos_juntador import wrapper_juntada_geral


def carta_wrapper(
    driver,
    numero_processo: Optional[str] = None,
    debug: bool = True,
    ecarta_html: Optional[str] = None
) -> bool:
    """
    Wrapper específico para juntada de e-carta.
    Busca o conteúdo do clipboard.txt para o processo e insere no editor via editor_insert.
    Parâmetros fixos conforme padrão do fluxo:
      tipo: Certidão
      descricao: Rastreamentos e-Carta
      modelo: xs carta
      assinar: nao
      sigilo: nao
      substituir_link: True
    """
    from Fix.utils import obter_ultimo_conteudo_clipboard

    conteudo = obter_ultimo_conteudo_clipboard(numero_processo, debug=debug)

    # Se ecarta_html for fornecido, usar ele diretamente (já é HTML formatado)
    if ecarta_html is not None:
        conteudo = ecarta_html

    def inserir_fn(driver, numero_processo=None, debug=True):
        # Usar substituir_marcador_por_conteudo que é mais robusto para CKEditor
        from Fix.utils import substituir_marcador_por_conteudo
        return substituir_marcador_por_conteudo(
            driver=driver,
            conteudo_customizado=conteudo or '',
            debug=True,
            marcador='--'
        )

    return wrapper_juntada_geral(
        driver=driver,
        tipo='Certidão',
        descricao='Rastreamentos e-Carta',
        modelo='xs carta',
        assinar='nao',
        sigilo='nao',
        inserir_conteudo=inserir_fn,
        coleta_conteudo=None,
        substituir_link=False,
        debug=debug
    )


def consulta_wrapper(
    driver,
    numero_processo: Optional[str] = None,
    debug: bool = True,
    tipo: str = 'Certidão',
    descricao: str = 'Consulta SISBAJUD',
    modelo: str = 'xteim',
    assinar: str = 'nao',
    sigilo: str = 'sim'
) -> bool:
    """Wrapper SISBAJUD positivo (renomeado para consulta)."""
    return _wrapper_sisbajud_generico(driver, tipo, descricao, modelo,
                                    assinar, sigilo, 'SISB', numero_processo, debug)


def wrapper_bloqneg(
    driver,
    numero_processo: Optional[str] = None,
    debug: bool = True,
    tipo: str = 'Certidão',
    descricao: str = 'Consulta sisbajud NEGATIVA',
    modelo: str = 'xjsisbneg',
    assinar: str = 'nao',
    sigilo: str = 'nao'
) -> bool:
    """Wrapper SISBAJUD negativo."""
    return _wrapper_sisbajud_generico(driver, tipo, descricao, modelo,
                                    assinar, sigilo, 'BLOQNEG', numero_processo, debug)


def wrapper_parcial(
    driver,
    numero_processo: Optional[str] = None,
    debug: bool = True,
    tipo: str = 'Certidão',
    descricao: str = 'Consulta sisbajud POSITIVA',
    modelo: str = 'XSISBPARCIAL',
    assinar: str = 'nao',
    sigilo: str = 'nao'
) -> bool:
    """Wrapper SISBAJUD parcial."""
    return _wrapper_sisbajud_generico(driver, tipo, descricao, modelo,
                                    assinar, sigilo, 'PARCIAL', numero_processo, debug)