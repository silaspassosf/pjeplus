import logging
logger = logging.getLogger(__name__)

"""
SISBAJUD Validacao - Funcoes de validacao
"""


def _validar_dados(dados_processo):
    """
    Helper para validar dados do processo necessarios para minuta de bloqueio.

    Args:
        dados_processo: Dados do processo (se None, carrega do arquivo dadosatuais.json)

    Returns:
        tuple: (dados_validos, numero_processo) onde dados_validos e bool e numero_processo e str
    """
    try:
        # Se dados_processo nao foi fornecido, carregar do arquivo
        if not dados_processo:
            try:
                from ..utils import carregar_dados_processo
                dados_processo = carregar_dados_processo()
                if not dados_processo:
                    return False, None
            except Exception as e:
                logger.error(f'[SISBAJUD]  Erro ao carregar dados do arquivo: {e}')
                return False, None

        # Verificar campos obrigatorios
        numero_lista = dados_processo.get('numero', [])
        if not numero_lista:
            return False, None

        numero_processo = numero_lista[0] if numero_lista else None
        if not numero_processo:
            return False, None

        reus = dados_processo.get('reu', [])
        if not reus:
            return False, None

        return True, numero_processo

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao validar dados: {e}')
        return False, None