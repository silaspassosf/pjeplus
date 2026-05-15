# -*- coding: utf-8 -*-
"""
bianca/triagem/utils.py -- Utilitarios gerais para o modulo de triagem.

Funcoes:
    _norm(s)                       Normalizacao NFD + lower + remove acentos.
    _formatar_endereco_parte(endereco)  Formata endereco dict como string.
    _normalizar_continuacao(texto)      Substitui \\n por \\n\\ \\ (recuo).
"""

import logging
import unicodedata

logger = logging.getLogger("bianca.triagem")


def _norm(s: str) -> str:
    """Normaliza texto: lower, remove acentos via NFD."""
    if not s:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    ).strip()


def _formatar_endereco_parte(endereco: dict) -> str:
    """Formata endereco dict em string legivel de ate 120 chars."""
    if not endereco or not isinstance(endereco, dict):
        return ''
    partes = []
    for chave in ('logradouro', 'numero', 'bairro', 'municipio', 'uf', 'complemento'):
        valor = endereco.get(chave)
        if valor:
            valor = str(valor).strip()
            if valor:
                partes.append(valor)
    return ', '.join(partes)[:120]


def _normalizar_continuacao(texto: str) -> str:
    """Normaliza quebras de linha inserindo recuo."""
    if not texto:
        return ''
    return texto.replace('\n', '\n  ').strip()
