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


def gerar_regex_geral(termo: str) -> re.Pattern:
    """Gera regex flexível para um termo, permitindo pontuação entre palavras."""
    termo_norm: str = normalizar_texto(termo)
    palavras: List[str] = termo_norm.split()
    partes: List[str] = [re.escape(p) for p in palavras]
    regex: str = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    return re.compile(rf"{regex}", re.IGNORECASE)
