#!/usr/bin/env python3
"""
Converters - Utilitários centralizados de conversão
Elimina duplicação de lógica entre módulos
"""

from typing import Optional
from datetime import datetime
import re


def converter_valor_monetario(texto: str) -> float:
    """
    Converte texto de valor monetário para float.

    Args:
        texto: Texto como "R$ 1.234,56" ou "1234.56"

    Returns:
        float: Valor convertido

    Exemplos:
        >>> converter_valor_monetario("R$ 1.234,56")
        1234.56
        >>> converter_valor_monetario("5000,00")
        5000.0
    """
    if not texto or not isinstance(texto, str):
        return 0.0

    # Remover caracteres especiais
    texto_limpo = texto.replace('R$', '').replace('\xa0', '').replace('&nbsp;', '').strip()

    # Se tem vírgula e ponto, assumir formato brasileiro
    if ',' in texto_limpo and '.' in texto_limpo:
        # "1.234,56" -> "1234.56"
        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
    elif ',' in texto_limpo:
        # "1234,56" -> "1234.56"
        texto_limpo = texto_limpo.replace(',', '.')

    try:
        return float(texto_limpo)
    except ValueError:
        return 0.0


def parsear_data_brasileira(texto_data: str) -> Optional[datetime]:
    """
    Converte data em formato brasileiro para datetime.

    Args:
        texto_data: Data como "31/12/2023" ou "31/12/2023 14:30"

    Returns:
        datetime: Data convertida ou None se inválida

    Exemplos:
        >>> parsear_data_brasileira("31/12/2023")
        datetime.datetime(2023, 12, 31, 0, 0)
        >>> parsear_data_brasileira("31/12/2023 14:30")
        datetime.datetime(2023, 12, 31, 14, 30)
    """
    if not texto_data or not isinstance(texto_data, str):
        return None

    texto_data = texto_data.strip()

    # Padrões comuns de data brasileira
    padroes = [
        r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{1,2})',  # 31/12/2023 14:30
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # 31/12/2023
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2023-12-31
    ]

    for padrao in padroes:
        match = re.match(padrao, texto_data)
        if match:
            grupos = match.groups()
            try:
                if len(grupos) == 5:  # Com hora
                    dia, mes, ano, hora, minuto = grupos
                    return datetime(int(ano), int(mes), int(dia), int(hora), int(minuto))
                elif len(grupos) == 3:
                    if '-' in texto_data:  # Formato ISO
                        ano, mes, dia = grupos
                    else:  # Formato brasileiro
                        dia, mes, ano = grupos
                    return datetime(int(ano), int(mes), int(dia))
            except ValueError:
                continue

    return None


def formatar_data_brasileira(data: datetime) -> str:
    """
    Formata datetime para string brasileira.

    Args:
        data: Data a formatar

    Returns:
        str: Data formatada como "31/12/2023"

    Exemplos:
        >>> formatar_data_brasileira(datetime(2023, 12, 31))
        '31/12/2023'
    """
    if not isinstance(data, datetime):
        return ""
    return data.strftime("%d/%m/%Y")


def formatar_data_hora_brasileira(data: datetime) -> str:
    """
    Formata datetime com hora para string brasileira.

    Args:
        data: Data a formatar

    Returns:
        str: Data formatada como "31/12/2023 14:30"

    Exemplos:
        >>> formatar_data_hora_brasileira(datetime(2023, 12, 31, 14, 30))
        '31/12/2023 14:30'
    """
    if not isinstance(data, datetime):
        return ""
    return data.strftime("%d/%m/%Y %H:%M")


def validar_cpf(cpf: str) -> bool:
    """
    Valida formato básico de CPF.

    Args:
        cpf: String do CPF

    Returns:
        bool: True se formato válido

    Nota: Esta é uma validação básica de formato, não algoritmo completo.
    """
    if not cpf or not isinstance(cpf, str):
        return False

    # Remover caracteres não numéricos
    cpf_numeros = re.sub(r'\D', '', cpf)

    # Deve ter exatamente 11 dígitos
    if len(cpf_numeros) != 11:
        return False

    # Não pode ter todos os dígitos iguais
    if cpf_numeros == cpf_numeros[0] * 11:
        return False

    return True


def limpar_texto(texto: str) -> str:
    """
    Limpa texto removendo espaços extras e caracteres especiais.

    Args:
        texto: Texto a limpar

    Returns:
        str: Texto limpo
    """
    if not texto or not isinstance(texto, str):
        return ""

    # Remover espaços múltiplos
    texto = re.sub(r'\s+', ' ', texto.strip())

    # Remover caracteres de controle
    texto = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', texto)

    return texto