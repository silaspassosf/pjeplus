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
    """xs ord: domicílio eletrônico determina qual sub-ação executar."""
    from atos.wrappers_pec import pec_ord, pec_arord
    from atos.wrappers_mov import mov_aud
    try:
        from Fix.variaveis import session_from_driver, PjeApiClient
        from Fix.core import extrair_id_processo
        id_proc = extrair_id_processo(driver)
        if id_proc:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            reclamadas = [p for p in (client.partes(id_proc) or [])
                          if p.get('poloProcessual', '').lower() in ['passivo', 'reclamada']]
            if reclamadas:
                com = sum(1 for p in reclamadas
                          if client.domicilio_eletronico(str(p.get('id') or p.get('idParte'))) is True)
                sem = len(reclamadas) - com
                logger.info(f'[xs_ord] {com} com domicilio, {sem} sem')
                if sem == 0:
                    pec_ord(driver)
                elif com == 0:
                    pec_arord(driver)
                else:
                    pec_ord(driver)
                    pec_arord(driver)
                mov_aud(driver)
                return
    except Exception as e:
        logger.warning(f'[xs_ord] fallback para pec_ord: {e}')
    pec_ord(driver)
    mov_aud(driver)


def _xs_sum(driver, atv):
    """xs sum: domicílio eletrônico determina qual sub-ação executar."""
    from atos.wrappers_pec import pec_sum, pec_arsum
    from atos.wrappers_mov import mov_aud
    try:
        from Fix.variaveis import session_from_driver, PjeApiClient
        from Fix.core import extrair_id_processo
        id_proc = extrair_id_processo(driver)
        if id_proc:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            reclamadas = [p for p in (client.partes(id_proc) or [])
                          if p.get('poloProcessual', '').lower() in ['passivo', 'reclamada']]
            if reclamadas:
                com = sum(1 for p in reclamadas
                          if client.domicilio_eletronico(str(p.get('id') or p.get('idParte'))) is True)
                sem = len(reclamadas) - com
                logger.info(f'[xs_sum] {com} com domicilio, {sem} sem')
                if sem == 0:
                    pec_sum(driver)
                elif com == 0:
                    pec_arsum(driver)
                else:
                    pec_sum(driver)
                    pec_arsum(driver)
                mov_aud(driver)
                return
    except Exception as e:
        logger.warning(f'[xs_sum] fallback para pec_sum: {e}')
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
    bndt(driver, inclusao=True)
    ato_meios(driver)


def _xs_socio(driver, atv):
    """xs socio: inclusão BNDT + termo sócio."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoS
    bndt(driver, inclusao=True)
    ato_termoS(driver)


def _empresa_termo(driver, atv):
    """empresa termo: inclusão BNDT + termo empresa."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoE
    bndt(driver, inclusao=True)
    ato_termoE(driver)


def _sob_n(driver, atv):
    """sob/xs N: def_chip + mov_sob."""
    from atos.movimentos import def_chip, mov_sob
    def_chip(driver)
    mov_sob(driver, atv.numero_processo, atv.observacao)


def _executar_sisbajud(driver, atv, fn_sisb):
    """Executa o fluxo completo PJE -> SISBAJUD para ações SISBAJUD."""
    from Fix.extracao import extrair_dados_processo
    from SISB.core import iniciar_sisbajud

    dados_processo = extrair_dados_processo(driver)
    if not dados_processo:
        raise RuntimeError('Falha ao extrair dados do processo para SISBAJUD')

    driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
    if not driver_sisb:
        raise RuntimeError('Falha ao iniciar o driver SISBAJUD')

    resultado = fn_sisb(
        driver_sisb,
        dados_processo=dados_processo,
        driver_pje=driver,
        log=True,
        fechar_driver=True
    )

    if isinstance(resultado, dict) and resultado.get('status') == 'erro':
        raise RuntimeError(f'SISBAJUD falhou: {resultado.get("erros")}')

    return resultado


def _sisbajud_minuta(driver, atv):
    from SISB.core import minuta_bloqueio
    return _executar_sisbajud(driver, atv, minuta_bloqueio)


def _sisbajud_minuta_60(driver, atv):
    from SISB.core import minuta_bloqueio_60
    return _executar_sisbajud(driver, atv, minuta_bloqueio_60)


def _sisbajud_processar_ordem(driver, atv):
    from SISB.core import processar_ordem_sisbajud
    return _executar_sisbajud(driver, atv, processar_ordem_sisbajud)


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

    def _a(mod, name):
        return getattr(mod, name, None) if mod else None

    def R(pat, bucket, acao):
        return (re.compile(pat, re.IGNORECASE), bucket, acao)

    return [
        # ── SISBAJUD ─────────────────────────────────────────────────────
        # teimosinha 60 ANTES de teimosinha (ordem importa)
        R(r'teimosinha\s+60|t2\s+60|\b60\s*d\b|60\s+dias',    'sisbajud', _sisbajud_minuta_60),
        R(r'\bteimosinha\b|\bt2\b',                             'sisbajud', _sisbajud_minuta),
        R(r'\bxs\s+resultado\b|\bresultado\b',                  'sisbajud', _sisbajud_processar_ordem),
        # ── CARTA ────────────────────────────────────────────────────────
        R(r'\bxs\s+carta\b',                                    'carta',    _w(carta)),
        # ── SOB ──────────────────────────────────────────────────────────
        R(r'\bsob\s+chip\b',                                    'sob',      _w(def_chip)),
        R(r'\bsobrestamento\s+vencido\b',                       'sob',      _def_sob),
        R(r'\bsob\s+\d+|\bxs\s+\d+$',                          'sob',      _sob_n),
        # ── COMUNICACOES ─────────────────────────────────────────────────
        R(r'exclu[ei]r?.*(?:convenios?|serasa|cnib)|(?:convenios?|serasa|cnib).*exclu[ei]r?|mandado\s+de\s+exclus',
          'comunicacoes', _w(_a(w, 'pec_excluiargos'))),
        R(r'\b(?:xs\s+ordc|c\.ord\.ar)\b',                    'comunicacoes', _w(_a(w, 'pec_arord'))),
        R(r'\b(?:xs\s+sumc|c\.sum\.ar)\b',                    'comunicacoes', _w(_a(w, 'pec_arsum'))),
        R(r'\b(?:xs\s+ord|c\.ord)\b',                          'comunicacoes', _xs_ord),
        R(r'\b(?:xs\s+sum|c\.sum)\b',                          'comunicacoes', _xs_sum),
        R(r'\bedital\s+aud\b|\bpec\s+aud\b',                    'comunicacoes', _w(_a(w, 'pec_editalaud'))),
        R(r'\bpz\s+idpj\b|\bidpjd\b|\bpzi\b',                 'comunicacoes', _pz_idpj),
        R(r'\bpec\s+cp\b|\bxs\s+pec\s+cp\b',                   'comunicacoes', _w(_a(w, 'pec_cpgeral'))),
        R(r'\bxs\s+edital\b|\bpec\s+edital\b|\bxs\s+pec\s+edital\b',
          'comunicacoes', _w(_a(w, 'pec_editaldec'))),
        R(r'\bpec\s+dec\b|\bxs\s+pec\s+dec\b',                 'comunicacoes', _w(_a(w, 'pec_decisao'))),
        R(r'\bpec\s+idpj\b|\bxs\s+pec\s+idpj\b',               'comunicacoes', _w(_a(w, 'pec_editalidpj'))),
        R(r'\bxs\s+bloq\b|\bpec\s+bloq\b',                     'comunicacoes', _w(_a(w, 'pec_bloqueio'))),
        R(r'\bxs\s+sigilo\b',                                   'comunicacoes', (_w(_a(w, 'pec_sigilo')), lambda driver, atv: __import__('atos.movimentos_fluxo', fromlist=['movimentar_inteligente']).movimentar_inteligente(driver, 'Aguardando Prazo'))),
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
