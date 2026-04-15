"""
Funções de P2B Core utilizadas pelo módulo Peticao
"""

import re
import unicodedata
from typing import Any, Optional

from ..core.log import get_module_logger

logger = get_module_logger(__name__)


def remover_acentos(texto: str) -> str:
    """Remove acentos de um texto."""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def normalizar_texto(texto: str) -> str:
    """Normaliza texto: remove acentos e converte para minúsculo."""
    return remover_acentos(texto.lower())


def gerar_regex_geral(termo: str) -> re.Pattern:
    """
    Gera regex tolerante para busca de termos em texto.

    Args:
        termo: Termo a ser procurado

    Returns:
        Pattern regex compilado
    """
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()

    # Monta regex permitindo pontuação entre palavras
    partes = [re.escape(p) for p in palavras]
    regex = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()$]*'

    # Permite o trecho em qualquer lugar do texto
    return re.compile(rf"{regex}", re.IGNORECASE)