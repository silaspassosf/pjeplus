"""Pré-processamento de texto: remoção de artefatos PJe e fingerprint de cabeçalho.

Este módulo é intencionalmente livre de regras de negócio; apenas limpeza
e identificação de fingerprint de cabeçalho.
"""
import re
from typing import List
from Triagem.utils import _norm

# Nível 1: artefatos PJe determinísticos (risco zero)
_RE_ARTEFATOS_PJE = re.compile(
    r'(?:^Documento assinado eletronicamente por[^\n]*\n?)'
    r'|(?:^https?://pje\.[^\n]+\n?)'
    r'|(?:^N[uú]mero do documento\s+\d+[^\n]*\n?)'
    r'|(?:^(?:Start|End) of OCR for page \d+[^\n]*\n?)'
    r'|(?:^\s*PJe\s*\n?)'
    r'|(?:^\s*LOGO\s+IMAGE[^\n]*\n?)',
    re.IGNORECASE | re.MULTILINE,
)

# Nível 2: início do conteúdo jurídico — ancora o fingerprint do cabeçalho
_RE_INICIO_JURIDICO = re.compile(
    r'\b(EXCELENT[ÍI]SSIM[OA]|RECLAMAÇÃO\s+TRABALHISTA|'
    r'RECLAMAÇÃO\s+TRABALHISTA|AO\s+EXCELENT|'
    r'INSTRUMENTO\s+PARTICULAR|AÇ[ÃA]O\s+DE\s+CONSIGNAÇ)',
    re.IGNORECASE,
)


def _remover_artefatos_pje(texto: str) -> str:
    """Nível 1: remove marcadores PJe/OCR determinísticos (risco zero)."""
    return _RE_ARTEFATOS_PJE.sub('', texto)


def _aprender_cabecalho(texto_sem_artefatos: str) -> List[str]:
    m = _RE_INICIO_JURIDICO.search(texto_sem_artefatos)
    if not m:
        return []

    bloco_pre = texto_sem_artefatos[:m.start()]
    linhas = [l.strip() for l in bloco_pre.splitlines() if l.strip()]
    if not linhas:
        return []

    fingerprint = []
    for linha in linhas:
        ln = linha.strip()
        if not ln:
            continue
        if len(ln) >= 90:
            continue
        ln_norm = _norm(ln)
        tem_contato = bool(re.search(
            r'\d{2}[\s\-]?\d{4}[\s\-]?\d{4}'
            r'|@\w|www\.'
            r'|\.com\.br|\.adv\.br',
            ln_norm,
        ))
        eh_nome_escritorio = bool(re.match(
            r'^[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\-\.]{4,}$', ln
        ))
        tem_endereco_escritorio = bool(
            re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cç]a|sala)\b', ln_norm)
            and re.search(r'\d', ln)
            and (
                'cep' in ln_norm
                or re.search(r'\d{5}\s*[-]?\s*\d{3}', ln_norm)
                or re.search(r'\b(av\.?|rua|travessa|rodovia|estrada|alameda|pra[cç]a)\b.*\d', ln_norm)
                and any(k in ln_norm for k in ('adv', 'escrit', 'oab', 'advogado', 'advogada'))
            )
        )

        if tem_contato or eh_nome_escritorio or tem_endereco_escritorio:
            fingerprint.append(ln)

    return fingerprint


def _remover_cabecalho_por_pagina(texto: str, fingerprint: List[str]) -> str:
    if not fingerprint:
        return texto
    fp_set = {l.strip() for l in fingerprint if l.strip()}
    linhas_out = []
    for linha in texto.splitlines():
        if linha.strip() in fp_set:
            continue
        linhas_out.append(linha)
    return '\n'.join(linhas_out)


def _strip_cabecalho_rodape(texto: str) -> str:
    """
    Ponto de entrada único: aplica nível 1 (artefatos PJe) e nível 2
    (cabeçalho do escritório) ao texto extraído da petição inicial.
    Seguro: nunca remove conteúdo do corpo jurídico.
    """
    if not texto:
        return texto
    texto = _remover_artefatos_pje(texto)
    fingerprint = _aprender_cabecalho(texto)
    if fingerprint:
        print(f'[TRIAGEM] cabecalho_fingerprint: {len(fingerprint)} linha(s) identificadas: '
              f'{fingerprint[:3]}')
        texto = _remover_cabecalho_por_pagina(texto, fingerprint)
    else:
        print('[TRIAGEM] cabecalho_fingerprint: nao identificado (texto inicia direto no conteudo juridico)')
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

__all__ = [
    '_RE_ARTEFATOS_PJE', '_RE_INICIO_JURIDICO',
    '_remover_artefatos_pje', '_aprender_cabecalho', '_remover_cabecalho_por_pagina', '_strip_cabecalho_rodape'
]
