import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_extracao - Módulo de extração de dados SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
"""

def _extrair_cpf_autor(dados_processo):
    """Extrai CPF/CNPJ do autor."""
    if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
        return dados_processo['autor'][0].get('cpfcnpj', '')
    elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
        return dados_processo['reu'][0].get('cpfcnpj', '')
    return ''

def _extrair_nome_autor(dados_processo):
    """Extrai nome do autor."""
    if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
        return dados_processo['autor'][0].get('nome', '')
    elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
        return dados_processo['reu'][0].get('nome', '')
    return ''