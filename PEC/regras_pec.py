"""
PEC/regras_pec.py — Tabela regras: padrão → bucket → ação(ões)

Substitui matcher.py + classificador.py + buckets.py.

Estrutura de cada regra:
    (re.Pattern, bucket: str, acao)

onde `acao` é:
    - callable(driver, atv)              → execução direta
    - tuple of callable(driver, atv)     → execução sequencial

Adaptor _w(fn) converte fn(driver) para a interface (driver, atv).
Helpers nomeados (_xs_ord, _def_sob, …) encapsulam ações com lógica própria.
"""
import re
import logging
from .helpers import normalizar_texto

logger = logging.getLogger(__name__)

BUCKET_ORDEM = ['carta', 'comunicacoes', 'sobrestamento', 'sob', 'outros', 'sisbajud']


# ─── adaptador: fn(driver) → fn(driver, atv) ─────────────────────────────────

def _w(fn):
    """Adapta callable (driver,) → (driver, atv) esperado pela tabela."""
    if fn is None:
        return None
    return lambda driver, atv: fn(driver)


# ─── helpers: ações com lógica interna ou assinatura especial ────────────────

def _xs_ord(driver, atv):
    """xs ord: pec_ord (trocar_modelo=True trata correios internamente) + mov_aud."""
    from atos.wrappers_pec import pec_ord
    from atos.wrappers_mov import mov_aud
    pec_ord(driver)
    mov_aud(driver)


def _xs_sum(driver, atv):
    """xs sum: pec_sum (trocar_modelo=True trata correios internamente) + mov_aud."""
    from atos.wrappers_pec import pec_sum
    from atos.wrappers_mov import mov_aud
    pec_sum(driver)
    mov_aud(driver)


def _def_sob(driver, atv):
    """Sobrestamento vencido — requer numero_processo e observacao do atv."""
    from PEC.sobrestamento import def_sob
    def_sob(driver, atv.numero_processo, atv.observacao)


def _pz_idpj(driver, atv):
    """pz idpj: cria gigs edital intimação + ato IDPJ."""
    from Fix.extracao import criar_gigs
    from atos.judicial import ato_idpj
    criar_gigs(driver, 1, 'Ingrid', 'edital intimacao correio')
    ato_idpj(driver)


def _xs_meios(driver, atv):
    """xs meios: inclusão BNDT + ato meios."""
    from Fix.extracao import bndt
    from atos.judicial import ato_meios
    ato_meios(driver)
    bndt(driver, inclusao=True)


def _xs_socio(driver, atv):
    """xs socio: inclusão BNDT + termo sócio."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoS
    ato_termoS(driver)
    bndt(driver, inclusao=True)


def _empresa_termo(driver, atv):
    """empresa termo: inclusão BNDT + termo empresa."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoE
    ato_termoE(driver)
    bndt(driver, inclusao=True)


def _sob_n(driver, atv):
    """sob/xs N: def_chip + mov_sob."""
    from atos.movimentos import def_chip, mov_sob
    def_chip(driver)
    mov_sob(driver)


def _audx_mov_int(driver, atv):
    """audx: movimenta diretamente para destino Audiência via API."""
    from atos.movimentos_fluxo import movimentar_inteligente
    movimentar_inteligente(driver, 'Audiência')


# ─── tabela plana ─────────────────────────────────────────────────────────────

def _build() -> list:
    """Constrói REGRAS uma única vez na carga do módulo."""
    try:
        from atos import wrappers_pec as w
    except ImportError:
        w = None
    try:
        from atos.movimentos import def_chip
    except ImportError:
        def_chip = None
    try:
        from atos.judicial import mov_aud, ato_bloq
    except ImportError:
        mov_aud = ato_bloq = None
    try:
        from PEC.carta import carta
    except ImportError:
        carta = None
    try:
        from SISB.core import minuta_bloqueio, minuta_bloqueio_60, processar_ordem_sisbajud
    except ImportError:
        minuta_bloqueio = minuta_bloqueio_60 = processar_ordem_sisbajud = None
    try:
        from atos.movimentos_fluxo import movimentar_inteligente as _mov_int
    except ImportError:
        _mov_int = None

    def _a(mod, name):
        return getattr(mod, name, None) if mod else None

    def _a_pec(name):
        acao = _a(w, name)
        if acao is None:
            logger.warning(f'[PEC] Wrapper ausente em atos.wrappers_pec: {name} (placeholder ativo)')
        return acao

    def R(pat, bucket, acao):
        return (re.compile(pat, re.IGNORECASE), bucket, acao)

    return [
        # ── SISBAJUD ─────────────────────────────────────────────────────
        # teimosinha 60 ANTES de teimosinha (ordem importa)
        R(r'teimosinha\s+60|t2\s+60|\b60\s*d\b|60\s+dias',    'sisbajud', _w(minuta_bloqueio_60)),
        R(r'\bteimosinha\b|\bt2\b',                             'sisbajud', _w(minuta_bloqueio)),
        R(r'\bxs\s+resultado\b|\bresultado\b',                  'sisbajud', _w(processar_ordem_sisbajud)),
        # ── CARTA ────────────────────────────────────────────────────────
        R(r'\bxs\s+carta\b',                                    'carta',    _w(carta)),
        # ── SOB ──────────────────────────────────────────────────────────
        R(r'\bsob\s+chip\b',                                    'sob',      _w(def_chip)),
        R(r'\bsobrestamento\s+vencido\b',                       'sob',      _def_sob),
        R(r'\bsob\s+\d+|\bxs\s+\d+$',                          'sob',      _sob_n),
        # ── COMUNICACOES ─────────────────────────────────────────────────
        R(r'exclu[ei]r?.*(?:convenios?|serasa|cnib)|(?:convenios?|serasa|cnib).*exclu[ei]r?|mandado\s+de\s+exclus',
          'comunicacoes', _w(_a(w, 'pec_excluiargos'))),
        R(r'\bxs\s+ordc\b',                                     'comunicacoes', _w(_a(w, 'pec_ordc'))),
        R(r'\bxs\s+sumc\b',                                     'comunicacoes', _w(_a(w, 'pec_sumc'))),
        R(r'\bxs\s+ord\b',                                      'comunicacoes', _xs_ord),
        R(r'\bxs\s+sum\b',                                      'comunicacoes', _xs_sum),
        R(r'\bedital\s+aud\b|\bpec\s+aud\b',                    'comunicacoes', _w(_a(w, 'pec_editalaud'))),
        R(r'\bpz\s+idpj\b|\bidpjd\b',                          'comunicacoes', _pz_idpj),
        R(r'\bpec\s+cp\b|\bxs\s+pec\s+cp\b',                   'comunicacoes', _w(_a(w, 'pec_cpgeral'))),
        R(r'\bxs\s+mdd\s+pgto\b',                                 'comunicacoes', _w(_a_pec('pec_mddpgto'))),
        R(r'\bxs\s+edital\s+pgto\b',                              'comunicacoes', _w(_a_pec('pec_editalpagto'))),
        R(r'\bxs\s+edital\b|\bpec\s+edital\b|\bxs\s+pec\s+edital\b',
          'comunicacoes', _w(_a(w, 'pec_editaldec'))),
        R(r'\bpec\s+dec\b|\bxs\s+pec\s+dec\b',                 'comunicacoes', _w(_a(w, 'pec_decisao'))),
        R(r'\bpec\s+idpj\b|\bxs\s+pec\s+idpj\b',               'comunicacoes', _w(_a(w, 'pec_editalidpj'))),
        R(r'\bxs\s+bloq\b|\bpec\s+bloq\b',                     'comunicacoes', _w(_a(w, 'pec_bloqueio'))),
        R(r'\bxs\s+sigilo\b',                                   'comunicacoes', (_w(_a(w, 'pec_sigilo')), _w(lambda d: _mov_int(d, 'Aguardando prazo')))),
        # ── OUTROS ───────────────────────────────────────────────────────
        R(r'\bxs\s+audx\b|\baudx\b|\baud\s+x\b',               'outros',   _audx_mov_int),
        R(r'\bxs\s+parcial\b',                                  'outros',   _w(ato_bloq)),
        R(r'\bmeios\b',                                         'outros',   _xs_meios),
        R(r'\bxs\s+socio\b',                                    'outros',   _xs_socio),
        R(r'\bempresa\s*termo\b|\btermoempresa\b',              'outros',   _empresa_termo),
    ]


REGRAS = _build()


def determinar_regra(observacao: str):
    """Retorna (pattern, bucket, acao) para a observacao, ou None se sem match."""
    obs = normalizar_texto(observacao)
    for pattern, bucket, acao in REGRAS:
        if pattern.search(obs):
            return pattern, bucket, acao
    return None
