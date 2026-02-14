import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_formatting - Módulo de formatação de dados para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import re

def formatar_moeda_brasileira(valor):
    """
    Formata valor numérico para moeda brasileira (R$ xxxxx,yy)
    """
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos, exceto vírgulas e pontos
            valor_limpo = re.sub(r'[^\d,.]', '', valor)

            # Converte para float
            if ',' in valor_limpo and '.' in valor_limpo:
                # Formato 1.234.567,89 ou 1,234,567.89
                if valor_limpo.rfind(',') > valor_limpo.rfind('.'):
                    # Último separador é vírgula (formato brasileiro)
                    valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                else:
                    # Último separador é ponto (formato internacional)
                    valor_limpo = valor_limpo.replace(',', '')
            elif ',' in valor_limpo:
                # Apenas vírgula como separador decimal
                valor_limpo = valor_limpo.replace(',', '.')

            valor = float(valor_limpo)

        if valor == 0:
            return "R$ 0,00"

        # Formata com separador de milhares e duas casas decimais
        valor_formatado = f"{valor:,.2f}"

        # Substitui separadores para formato brasileiro
        valor_formatado = valor_formatado.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')

        return f"R$ {valor_formatado}"

    except (ValueError, TypeError):
        return "R$ 0,00"

def formatar_data_brasileira(data_str):
    """
    Formata data para padrão brasileiro (dd/mm/yyyy)
    """
    try:
        if not data_str:
            return ""

        # Se já está no formato brasileiro, retorna como está
        if re.match(r'\d{2}/\d{2}/\d{4}', data_str):
            return data_str

        # Remove horário se presente
        data_limpa = data_str.split('T')[0].split(' ')[0]

        # Tenta diferentes formatos de entrada
        formatos = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%Y.%m.%d',
            '%d.%m.%Y'
        ]

        for formato in formatos:
            try:
                from datetime import datetime
                data_obj = datetime.strptime(data_limpa, formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue

        # Se não conseguiu formatar, retorna string original
        return data_str

    except Exception:
        return data_str

def normalizar_cpf_cnpj(documento):
    """
    Remove pontuação de CPF/CNPJ, mantendo apenas números
    """
    if not documento:
        return ""

    # Remove todos os caracteres não numéricos
    documento_limpo = re.sub(r'\D', '', str(documento))
    return documento_limpo

def extrair_raiz_cnpj(cnpj):
    """
    Extrai apenas a raiz do CNPJ (antes de 000)
    Para CNPJ no formato 38448964000170, retorna 38448964
    """
    if not cnpj:
        return ""

    # Normaliza primeiro (remove pontuação)
    cnpj_limpo = normalizar_cpf_cnpj(cnpj)

    # Se tem 14 dígitos (CNPJ completo), pega os primeiros 8 dígitos (raiz)
    if len(cnpj_limpo) == 14:
        return cnpj_limpo[:8]

    # Se não é CNPJ de 14 dígitos, retorna como está
    return cnpj_limpo

def identificar_tipo_documento(documento):
    """
    Identifica se é CPF (11 dígitos) ou CNPJ (14 dígitos)
    """
    if not documento:
        return "UNKNOWN"

    documento_limpo = normalizar_cpf_cnpj(documento)

    if len(documento_limpo) == 11:
        return "CPF"
    elif len(documento_limpo) == 14:
        return "CNPJ"
    else:
        return "UNKNOWN"