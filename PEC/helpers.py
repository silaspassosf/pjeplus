import logging
logger = logging.getLogger(__name__)

"""Funções auxiliares para processamento de texto em regras."""

import re
import unicodedata
from typing import List
from re import Pattern


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


def _montar_url_processo(numero_cnj: str, base_url: str = "https://pje.trt2.jus.br") -> str:
    """Monta URL de detalhe do processo para navegação direta no PJe."""
    numero_texto = str(numero_cnj or "")
    numero_limpo = ''.join(filter(str.isdigit, numero_texto))
    identificador = numero_limpo if len(numero_limpo) == 20 else numero_texto
    return f"{base_url}/pjekz/processo/{identificador}/detalhe"


def _fechar_abas_extras(driver) -> None:
    """Mantém apenas a aba principal aberta, fechando as demais."""
    try:
        abas = driver.window_handles
        if len(abas) <= 1:
            return
        aba_principal = abas[0]
        for aba in abas[1:]:
            try:
                driver.switch_to.window(aba)
                driver.close()
            except Exception:
                pass
        driver.switch_to.window(aba_principal)
    except Exception:
        pass
