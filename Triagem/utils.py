"""Utilitários puros usados na triagem (normalização, pequenas formatações).
"""
import unicodedata

def _norm(t: str) -> str:
    if t is None:
        return ''
    return unicodedata.normalize('NFD', t).encode('ascii', 'ignore').decode().lower()

__all__ = ['_norm']


def _formatar_endereco_parte(endereco: dict) -> str:
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

__all__ = ['_norm', '_formatar_endereco_parte']
