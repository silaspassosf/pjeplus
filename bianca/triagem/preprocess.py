# -*- coding: utf-8 -*-
"""
bianca/triagem/preprocess.py -- Pre-processamento de textos extraidos.

Remove artefatos gerados pelo PJe (assinaturas digitais, rodapes de OCR,
URLs, etc.) e tenta identificar/remover cabecalhos de escritorios
de advocacia repetidos pagina a pagina.

Funcoes:
    _remover_artefatos_pje(texto)
    _aprender_cabecalho(texto_sem_artefatos)
    _remover_cabecalho_por_pagina(texto, fingerprint)
    _strip_cabecalho_rodape(texto)
"""

import logging
import re
from typing import List

from bianca.triagem.utils import _norm

logger = logging.getLogger("bianca.triagem.preprocess")

_RE_ARTEFATOS_PJE = re.compile(
    r'(?:^Documento assinado eletronicamente por[^\n]*\n?)'
    r'|(?:^https?://pje\.[^\n]+\n?)'
    r'|(?:^N[uú]mero do documento\s+\d+[^\n]*\n?)'
    r'|(?:^(?:Start|End) of OCR for page \d+[^\n]*\n?)'
    r'|(?:^\s*PJe\s*\n?)'
    r'|(?:^\s*LOGO\s+IMAGE[^\n]*\n?)',
    re.IGNORECASE | re.MULTILINE,
)

_RE_INICIO_JURIDICO = re.compile(
    r'\b(EXCELENT[IÍ]SSIM[OA]|RECLAMACAO\s+TRABALHISTA|'
    r'AO\s+EXCELENT|INSTRUMENTO\s+PARTICULAR|'
    r'ACAO\s+DE\s+CONSIGNACAO)',
    re.IGNORECASE,
)


def _remover_artefatos_pje(texto: str) -> str:
    """Remove artefatos padrao do PJe (assinaturas, rodapes OCR, URLs)."""
    return _RE_ARTEFATOS_PJE.sub('', texto)


def _aprender_cabecalho(texto_sem_artefatos: str) -> List[str]:
    """Tenta identificar linhas de cabecalho de escritorio antes do inicio juridico."""
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
        if not ln or len(ln) >= 90:
            continue
        ln_norm = _norm(ln)
        tem_contato = bool(re.search(
            r'\d{2}[\s\-]?\d{4}[\s\-]?\d{4}'
            r'|@\w|www\.'
            r'|\.com\.br|\.adv\.br',
            ln_norm,
        ))
        eh_nome_escritorio = bool(re.match(
            r'^[A-ZA-AE-EI-IO-O-U-UC-N\s\-\.]{4,}$', ln
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
    """Remove linhas exatas contidas no fingerprint."""
    if not fingerprint:
        return texto
    fp_set = {l.strip() for l in fingerprint if l.strip()}
    linhas_out = [linha for linha in texto.splitlines() if linha.strip() not in fp_set]
    return '\n'.join(linhas_out)


def _strip_cabecalho_rodape(texto: str) -> str:
    """Remove artefatos PJe e cabecalho de escritorio."""
    if not texto:
        return texto
    texto = _remover_artefatos_pje(texto)
    fingerprint = _aprender_cabecalho(texto)
    if fingerprint:
        logger.debug('cabecalho_fingerprint: %s linha(s)', len(fingerprint))
        texto = _remover_cabecalho_por_pagina(texto, fingerprint)
    else:
        logger.debug('cabecalho_fingerprint: nao identificado')
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()
