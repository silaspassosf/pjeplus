import logging
logger = logging.getLogger(__name__)

"""Funções auxiliares para processamento de texto em regras."""

import re
import unicodedata


def remover_acentos(txt: str) -> str:
    """Remove acentos de texto."""
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')


def normalizar_texto(txt: str) -> str:
    """Normaliza texto: remove acentos e converte para minúscula."""
    return remover_acentos(txt.lower())


def gerar_regex_geral(termo: str):
    """Gera regex flexível para um termo, permitindo pontuação entre palavras."""
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    regex = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    return re.compile(rf"{regex}", re.IGNORECASE)
