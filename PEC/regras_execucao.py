"""PEC - Regras de Execucao

Consolidado de: regras_pec, sobrestamento.
"""

import logging
import math
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

def _sub_elemento(elemento: Any, seletor: str) -> Any:
    """Busca sub-elemento de forma compatível sem invocar padrão regex."""
    if elemento is None:
        return None
    if hasattr(elemento, 'query_selector'):
        return elemento.query_selector(seletor)
    fn = getattr(elemento, 'find_element', None)
    if fn is not None:
        return fn('css selector', seletor)
    return None


from atos.judicial import ato_fal, ato_prov, ato_termoS
from atos.movimentos import def_chip, mov_sob, mov_fimsob
from core.rule_registry import RuleRegistry, adapt_action as _w
from Fix.abas import aguardar_nova_aba
from Fix.extracao import extrair_direto, extrair_documento, extrair_pdf, criar_gigs, bndt
from Fix.core import (
    aguardar_renderizacao_nativa,
    esperar_elemento,
    safe_click,
    safe_click_no_scroll,
)
from Fix.facade_publica import carregar_js
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.utils import normalizar_texto
from Fix import espera

# Configuração global de logging (caso não tenha sido feita no script principal)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


# Sobrestamento vencido deve ser processado por ÚLTIMO, imediatamente antes de SISBAJUD
BUCKET_ORDEM = ['xs_sob', 'carta', 'comunicacoes', 'outros', 'sobrestamento', 'sisbajud_teimosinha', 'sisbajud_resultado']


# ─── helpers: acoes com logica interna ou assinatura especial ────────────────

def _normalizar_resultado_acao(resultado: Any) -> Any:
    """Converte sucesso implicito em retorno explicito sem esconder False."""
    if resultado is None:
        return True
    return resultado


def _executar_passos(*passos) -> Any:
    """Executa passos em sequencia, interrompendo em False explicito."""
    ultimo_resultado: Any = True
    for passo in passos:
        resultado = _normalizar_resultado_acao(passo())
        if resultado is False:
            return False
        if resultado is not True:
            ultimo_resultado = resultado
    return ultimo_resultado

def _xs_ord(driver, atv):
    """xs ord: domicilio eletronico determina qual sub-acao executar."""
    from atos.wrappers_pec import pec_ord, pec_arord
    from atos.wrappers_mov import mov_aud
    try:
        from Fix.variaveis import cliente_para
        from Fix.core import extrair_id_processo
        id_proc = extrair_id_processo(driver)
        if id_proc:
            client = cliente_para(driver)
            reclamadas = [p for p in (client.partes(id_proc) or [])
                          if p.get('poloProcessual', '').lower() in ['passivo', 'reclamada']]
            if reclamadas:
                com = sum(1 for p in reclamadas
                          if client.domicilio_eletronico(str(p.get('id') or p.get('idParte'))) is True)
                sem = len(reclamadas) - com
                logger.info(f'[xs_ord] {com} com domicilio, {sem} sem')
                if sem == 0:
                    return _executar_passos(
                        lambda: pec_ord(driver),
                        lambda: mov_aud(driver),
                    )
                if com == 0:
                    return _executar_passos(
                        lambda: pec_arord(driver),
                        lambda: mov_aud(driver),
                    )
                return _executar_passos(
                    lambda: pec_ord(driver),
                    lambda: pec_arord(driver),
                    lambda: mov_aud(driver),
                )
    except Exception as e:
        logger.warning(f'[xs_ord] fallback para pec_ord: {e}')
    return _executar_passos(
        lambda: pec_ord(driver),
        lambda: mov_aud(driver),
    )


def _xs_sum(driver, atv):
    """xs sum: domicilio eletronico determina qual sub-acao executar."""
    from atos.wrappers_pec import pec_sum, pec_arsum
    from atos.wrappers_mov import mov_aud
    try:
        from Fix.variaveis import cliente_para
        from Fix.core import extrair_id_processo
        id_proc = extrair_id_processo(driver)
        if id_proc:
            client = cliente_para(driver)
            reclamadas = [p for p in (client.partes(id_proc) or [])
                          if p.get('poloProcessual', '').lower() in ['passivo', 'reclamada']]
            if reclamadas:
                com = sum(1 for p in reclamadas
                          if client.domicilio_eletronico(str(p.get('id') or p.get('idParte'))) is True)
                sem = len(reclamadas) - com
                logger.info(f'[xs_sum] {com} com domicilio, {sem} sem')
                if sem == 0:
                    return _executar_passos(
                        lambda: pec_sum(driver),
                        lambda: mov_aud(driver),
                    )
                if com == 0:
                    return _executar_passos(
                        lambda: pec_arsum(driver),
                        lambda: mov_aud(driver),
                    )
                return _executar_passos(
                    lambda: pec_sum(driver),
                    lambda: pec_arsum(driver),
                    lambda: mov_aud(driver),
                )
    except Exception as e:
        logger.warning(f'[xs_sum] fallback para pec_sum: {e}')
    return _executar_passos(
        lambda: pec_sum(driver),
        lambda: mov_aud(driver),
    )


def _def_sob(driver, atv):
    """Sobrestamento vencido — requer numero_processo e observacao do atv."""
    return def_sob(driver, atv.numero_processo, atv.observacao)


def _pz_idpj(driver, atv):
    """pz idpj: cria gigs xs mddid + ato IDPJ."""
    from Fix.extracao import criar_gigs
    from atos.judicial import ato_idpj
    def _run_idpj():
        r = ato_idpj(driver)
        return r[0] if isinstance(r, tuple) else r
        
    return _executar_passos(
        lambda: criar_gigs(driver, "1", "", "xs mddid"),
        _run_idpj
    )


def _mddid(driver, atv):
    """mdd id: pec_mddsent + pec_editalsent.

    Execução explícita (em vez de _executar_passos) para poder interpor
    a barreira aguardar_renderizacao_nativa entre os dois wrappers.
    Quando chamados isoladamente o PJe já está estável no início do
    próximo processo; aqui replicamos essa condição antes do 2º ato.
    """
    from atos.wrappers_pec import pec_mddsent, pec_editalsent
    ok = _normalizar_resultado_acao(pec_mddsent(driver))
    if ok is False:
        return False
    # Barreira: aguarda readyState completo na aba de detalhe após
    # fechar a aba de minutas do mandado — sem ela o Angular ainda
    # está processando o ato agrupado quando a aba do edital abre,
    # causando o spinner "Aguardando" por trás do modal de modelo.
    aguardar_renderizacao_nativa(driver, timeout=10)
    return _normalizar_resultado_acao(pec_editalsent(driver))


def _xs_meios(driver, atv):
    """xs meios: ato meios + inclusao BNDT."""
    from Fix.extracao import bndt
    from atos.judicial import ato_meios
    return _executar_passos(
        lambda: ato_meios(driver),
        lambda: bndt(driver, inclusao=True),
    )


def _xs_socio(driver, atv):
    """xs socio: termo socio + inclusao BNDT."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoS
    return _executar_passos(
        lambda: ato_termoS(driver),
        lambda: bndt(driver, inclusao=True),
    )


def _empresa_termo(driver, atv):
    """empresa termo: termo empresa + inclusao BNDT."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoE
    return _executar_passos(
        lambda: ato_termoE(driver),
        lambda: bndt(driver, inclusao=True),
    )


def _sob_n(driver, atv):
    """sob/xs N: def_chip + mov_sob com propagação de falha."""
    from atos.movimentos import def_chip, mov_sob
    import logging
    _log = logging.getLogger("PEC._sob_n")

    try:
        def_chip(driver)
    except Exception as e:
        _log.warning(f'[SOB] def_chip falhou (não crítico): {e}')

    try:
        ok = mov_sob(driver, atv.numero_processo, atv.observacao, debug=True)
        if not ok:
            _log.error(f'[SOB] mov_sob FALHOU para {atv.numero_processo} com obs="{atv.observacao}"')
        return ok
    except Exception as e:
        _log.error(f'[SOB] mov_sob EXCEÇÃO para {atv.numero_processo}: {e}')
        import traceback
        _log.error(traceback.format_exc())
        return False


_shared_driver_sisb = None

def _executar_sisbajud(driver, atv, fn_sisb):
    """Executa o fluxo completo PJE -> SISBAJUD para acoes SISBAJUD usando driver compartilhado."""
    global _shared_driver_sisb
    from Fix.extracao import extrair_dados_processo
    from SISB.core import iniciar_sisbajud

    dados_processo = extrair_dados_processo(driver)
    if not dados_processo:
        logger.error('[SISBAJUD] Falha ao extrair dados do processo')
        raise RuntimeError('Falha ao extrair dados do processo para SISBAJUD')

    # Garantir que o driver compartilhado exista e esteja ativo
    if _shared_driver_sisb is None:
        logger.info('[SISBAJUD] Inicializando novo driver compartilhado')
        _shared_driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
    else:
        try:
            # Teste rápido para ver se a janela não foi fechada pelo usuário ou quebrou
            _ = getattr(_shared_driver_sisb, 'window_handles', None)
        except Exception:
            logger.info('[SISBAJUD] Driver compartilhado morto. Reinicializando...')
            _shared_driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)

    if not _shared_driver_sisb:
        raise RuntimeError('Falha ao iniciar o driver SISBAJUD')

    # Executar a função (com fechar_driver=False para reaproveitar na próxima)
    try:
        resultado = fn_sisb(
            _shared_driver_sisb,
            dados_processo=dados_processo,
            driver_pje=driver,
            log=True,
            fechar_driver=False
        )
    except Exception as e:
        logger.error(f'[SISBAJUD] Exceção durante a execução de {fn_sisb.__name__}: {e}')
        raise

    if isinstance(resultado, dict) and resultado.get('status') == 'erro':
        raise RuntimeError(f'SISBAJUD falhou: {resultado.get("erros")}')

    return resultado


def fechar_driver_sisbajud_compartilhado():
    """Fecha o driver compartilhado do SISBAJUD de forma segura ao final do fluxo."""
    global _shared_driver_sisb
    if _shared_driver_sisb:
        logger.info('[SISBAJUD] Encerrando driver compartilhado do SISBAJUD.')
        try:
            _shared_driver_sisb.quit()
        except Exception as e:
            logger.debug(f'[SISBAJUD] Erro ignorado ao fechar driver: {e}')
        finally:
            _shared_driver_sisb = None


def _sisbajud_minuta(driver, atv):
    from SISB.core import minuta_bloqueio_amanha
    # Usa a nova funcionalidade de 2 minutas independentes (com prazo padrão 30)
    return _executar_sisbajud(driver, atv, lambda d, dados_processo, driver_pje, log, fechar_driver: 
                              minuta_bloqueio_amanha(d, dados_processo, driver_pje, log, fechar_driver, prazo_dias=30))


def _sisbajud_minuta_60(driver, atv):
    from SISB.core import minuta_bloqueio_amanha
    # Usa a nova funcionalidade de 2 minutas independentes (com prazo padrão 60)
    return _executar_sisbajud(driver, atv, lambda d, dados_processo, driver_pje, log, fechar_driver: 
                              minuta_bloqueio_amanha(d, dados_processo, driver_pje, log, fechar_driver, prazo_dias=60))


def _sisbajud_processar_ordem(driver, atv):
    from SISB.core import processar_ordem_sisbajud
    return _executar_sisbajud(driver, atv, processar_ordem_sisbajud)


def _audx_mov_int(driver, atv):
    """audx: movimenta diretamente para destino Audiencia via API."""
    from atos.movimentos_fluxo import movimentar_inteligente
    return _normalizar_resultado_acao(movimentar_inteligente(driver, 'Audiencia'))


def _carta_exec(driver, atv):
    """xs carta: carrega a implementação real sob demanda."""
    from PEC.carta_execucao import carta
    return carta(driver)


def _xs_parcial(driver, atv):
    """xs parcial: carrega ato_bloq via export público atual."""
    from atos import ato_bloq
    return _normalizar_resultado_acao(ato_bloq(driver))


def _xs_sigilo(driver, atv):
    """xs sigilo: aplica comunicação de sigilo e move para Aguardando Prazo."""
    from atos.wrappers_pec import pec_sigilo
    from atos.movimentos_fluxo import movimentar_inteligente

    return _executar_passos(
        lambda: pec_sigilo(driver),
        lambda: movimentar_inteligente(driver, 'Aguardando Prazo'),
    )


def _mov_exec(driver, atv):
    """mov exec: mov_int iniciar execução, mov_int aguardando prazo."""
    from atos.movimentos_fluxo import movimentar_inteligente
    return _executar_passos(
        lambda: movimentar_inteligente(driver, 'Iniciar Execução'),
        lambda: movimentar_inteligente(driver, 'Aguardando Prazo'),
    )


def _xs_pesq(driver, atv):
    """xs pesq: cria GIGS Argos + sigilo, tenta iniciar execução e roteia ato —
    reutiliza a função completa que já existe no fluxo p2b (Prazo/p2b_gateway)."""
    from Prazo.p2b_gateway import inicar_exec
    return inicar_exec(driver)



# ─── Lazy imports ────────────────────────────────────────────────────────────

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
    from PEC.carta_execucao import carta
except ImportError:
    carta = None
try:
    from SISB.core import minuta_bloqueio, minuta_bloqueio_60, processar_ordem_sisbajud
except ImportError:
    minuta_bloqueio = minuta_bloqueio_60 = processar_ordem_sisbajud = None


def _a(mod, name):
    return getattr(mod, name, None) if mod else None


# ─── registry ─────────────────────────────────────────────────────────────────

registry = RuleRegistry("pec", BUCKET_ORDEM)

# ── SISBAJUD ──────────────────────────────────────────────────────────────────
registry.register(r'teimosinha\s+60|t2\s+60|\b60\s*d\b|60\s+dias',    'sisbajud_teimosinha', _sisbajud_minuta_60)
registry.register(r'\bteimosinha\b|\bt2\b',                             'sisbajud_teimosinha', _sisbajud_minuta)
registry.register(r'\b(?:xs\s+)?resultado\b|\bsisbajud\s+resultado\b|\bresultado\s+teimosinha\b', 'sisbajud_resultado', _sisbajud_processar_ordem)
# ── CARTA ─────────────────────────────────────────────────────────────────────
registry.register(r'\bxs\s+carta\b',                                    'carta',    _carta_exec)
# ── SOB ───────────────────────────────────────────────────────────────────────
registry.register(r'\bsob\s+chip\b',                                    'xs_sob',   _w(def_chip))
registry.register(r'\bsobrestamento\s+vencido\b',                       'sobrestamento', _def_sob)
registry.register(r'\b(?:xs\s+)?sob\s+\d+|\bxs\s+\d+$',                  'xs_sob',   _sob_n)
# ── COMUNICACOES ──────────────────────────────────────────────────────────────
registry.register(r'exclu[ei]r?.*(?:convenios?|serasa|cnib)|(?:convenios?|serasa|cnib).*exclu[ei]r?|mandado\s+de\s+exclus',
                  'comunicacoes', _w(_a(w, 'pec_excluiargos')))
registry.register(r'\b(?:xs\s+ordc|c\.ord\.ar)\b',                    'comunicacoes', _w(_a(w, 'pec_arord')))
registry.register(r'\b(?:xs\s+sumc|c\.sum\.ar)\b',                    'comunicacoes', _w(_a(w, 'pec_arsum')))
registry.register(r'\b(?:xs\s+ord|c\.ord)\b',                          'comunicacoes', _xs_ord)
registry.register(r'\b(?:xs\s+sum|c\.sum)\b',                          'comunicacoes', _xs_sum)
registry.register(r'\bedital\s+aud\b|\bpec\s+aud\b',                    'comunicacoes', _w(_a(w, 'pec_editalaud')))
registry.register(r'\bpz\s+idpj\b|\bidpjd\b|\bpzi\b',                 'comunicacoes', _pz_idpj)
registry.register(r'\bpec\s+cp\b|\bxs\s+pec\s+cp\b',                   'comunicacoes', _w(_a(w, 'pec_cpgeral')))
registry.register(r'\bmdd\s+pgto\b',                                  'comunicacoes', _w(_a(w, 'pec_mddpg')))
registry.register(r'\bmdd\s*2\b',                                    'comunicacoes', _w(_a(w, 'pec_mddgeral')))
registry.register(r'\bmdd\s+id\b|\bmddid\b',                         'comunicacoes', _mddid)
registry.register(r'\bedital\s+(?:de\s+)?pgto\b|\bpec\s+edital\s+(?:de\s+)?pgto\b', 'comunicacoes', _w(_a(w, 'pec_editalpg')))
registry.register(r'\bxs\s+edital\b|\bpec\s+edital\b|\bxs\s+pec\s+edital\b|\bedital\b',
                  'comunicacoes', _w(_a(w, 'pec_editaldec')))
registry.register(r'\bpec\s+dec\b|\bxs\s+pec\s+dec\b',                 'comunicacoes', _w(_a(w, 'pec_decisao')))
registry.register(r'\bpec\s+idpj\b|\bxs\s+pec\s+idpj\b',               'comunicacoes', _w(_a(w, 'pec_editalidpj')))
registry.register(r'\bxs\s+bloq\b|\bpec\s+bloq\b',                     'comunicacoes', _w(_a(w, 'pec_bloqueio')))
registry.register(r'\bxs\s+sigilo\b',                                   'comunicacoes', _xs_sigilo)
# ── OUTROS ────────────────────────────────────────────────────────────────────
registry.register(r'\bxs\s+audx\b|\baudx\b|\baud\s+x\b',               'outros',   _audx_mov_int)
registry.register(r'\bxs\s+parcial\b',                                  'outros',   _xs_parcial)
registry.register(r'\bmeios\b',                                         'outros',   _xs_meios)
registry.register(r'\bxs\s+socio\b',                                    'outros',   _xs_socio)
registry.register(r'\bsociot\b',                                       'outros',   _xs_socio)
registry.register(r'\bempresa\s*termo\b|\btermoempresa\b',              'outros',   _empresa_termo)
registry.register(r'\bmov\s+exec\b',                                    'outros',   _mov_exec)
registry.register(r'\bxs\s+pesq\b',                                    'outros',   _xs_pesq)

REGRAS = registry.all_rules()


# ── Determinacao de Regra ──
def determinar_regra(observacao: str):
    """Retorna (pattern, bucket, acao) para a observacao, ou None se sem match.

    Uses registry.match() internally for bucket-order-respecting search.
    Maintains backward-compatible 3-tuple return by looking up the pattern
    from the full rules list.
    """
    # Lazy import to break circular dependency with runtime_pec
    from .runtime_pec import normalizar_texto

    obs = normalizar_texto(observacao)
    if not obs:
        return None
    pattern, bucket, action = registry.match_rule(obs)
    if bucket is None:
        return None
    return pattern, bucket, action


# ═══════════════════════════════════════════════════════════════
# SOBRESTAMENTO
# ═══════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────
# DEF_SOB — SOBRESTAMENTO (Refatorado com padrão P2B)
# ───────────────────────────────────────────────────────

# Padrões regex para regras de sobrestamento (padrão P2B).
# Testados sobre `texto_norm` (normalizar_texto = sem acentos e minúsculo).
DEF_SOB_PATTERNS = {
    'retorno_feito_principal': re.compile(r'retorno do feito principal|retorno\s+do\s+feito|volta dos autos', re.IGNORECASE),
    'penhora_rosto': re.compile(r'penhora no rosto|penhora\s+no\s+rosto|sobre\s+os\s+bens', re.IGNORECASE),
    'precatorio': re.compile(r'precatorio|RPV|pequeno valor|saldo\s+devedor|até\s+.*\s+UFRGS|beneficiario do FGTS', re.IGNORECASE),
    'juizo_universal': re.compile(r'juizo\s+universal', re.IGNORECASE),
    'prescricao': re.compile(r'prazo prescricional|prescricao|prescricional', re.IGNORECASE),
    'autos_principais': re.compile(r'autos principais|processo principal|retorno\s+ao\s+processo', re.IGNORECASE),
}

# Termos do legado (LEGADO.md 31440-31447): casados com gerar_regex_geral, que
# tolera pontuação/espaços extras entre as palavras do termo.
DEF_SOB_TERMOS = {
    'retorno_feito_principal': ['retorno do feito principal'],
    'penhora_rosto': ['penhora no rosto'],
    'precatorio': ['precatório', 'RPV', 'pequeno valor'],
    'juizo_universal': ['juízo universal'],
    'prescricao': ['prazo prescricional'],
    'autos_principais': ['autos principais', 'processo principal'],
}

_MESES_ABREV = {
    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
    'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
}

_RELEVANTE_DOC_RE = re.compile(r'despacho|decis[ãa]o|senten[çc]a|conclus[ãa]o', re.IGNORECASE)


def _data_para_numerico(data_texto: Optional[str]) -> Optional[str]:
    """Converte 'DD/MM/AAAA', 'DD-MM-AAAA' ou 'DD mar. AAAA' em 'DD/MM/AAAA'."""
    if not data_texto:
        return None
    match = re.search(r'(\d{1,2})\s+([A-Za-zÀ-ÿ]{3})\.?\s+(\d{4})', data_texto)
    if match:
        mes = _MESES_ABREV.get(match.group(2).lower()[:3])
        if mes:
            return f'{match.group(1).zfill(2)}/{mes}/{match.group(3)}'
    match = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', data_texto)
    if match:
        return f'{match.group(1).zfill(2)}/{match.group(2).zfill(2)}/{match.group(3)}'
    return None


def _data_decisao_do_item(item) -> Optional[str]:
    """Data da decisão no item da timeline (title do .tl-item-hora, LEGADO.md 30830-30845)."""
    try:
        hora = _sub_elemento(item, '.tl-item-hora')
        if not hora:
            return None
        titulo = (getattr(hora, 'get_attribute', lambda a: '')('title') or
                  (getattr(hora, 'text_content', None) and hora.text_content()) or
                  getattr(hora, 'text', '') or '')
    except Exception:
        return None
    return _data_para_numerico(titulo)


def _selecionar_decisao_timeline(driver):
    """Seleciona a decisão relevante da timeline e devolve (link, data_decisao_str).

    Critério do legado (LEGADO.md 30748-30805):
    1) documento relevante (despacho/decisão/sentença/conclusão) assinado por
       magistrado (div.tl-icon[aria-label*='Magistrado']);
    2) primeiro documento relevante, se nenhum tiver o ícone.
    """
    try:
        itens = espera.elementos(driver, 'li.tl-item-container', teto=2)
    except Exception:
        itens = []
    if not itens:
        logger.warning('[DEF_SOB] Nenhum item encontrado na timeline')
        return None, None

    fallback = None
    for item in itens:
        link = _sub_elemento(item, 'a.tl-documento:not([target="_blank"])')
        if not link:
            continue
        link_texto = (getattr(link, 'text_content', None) and link.text_content()) or getattr(link, 'text', '') or ''
        if not _RELEVANTE_DOC_RE.search(link_texto):
            continue
        if fallback is None:
            fallback = (link, _data_decisao_do_item(item))
        magistrado_icon = _sub_elemento(item, 'div.tl-icon[aria-label*="Magistrado"]')
        if not magistrado_icon:
            continue
        logger.debug(f"[DEF_SOB] Decisão assinada por magistrado: '{link_texto}'")
        return link, _data_decisao_do_item(item)

    if fallback is not None:
        fallback_texto = (getattr(fallback[0], 'text_content', None) and fallback[0].text_content()) or getattr(fallback[0], 'text', '') or ''
        logger.debug(f"[DEF_SOB] Documento relevante (sem ícone de magistrado): '{fallback_texto}'")
    return fallback if fallback is not None else (None, None)


def _data_sobrestamento_na_tarefa(driver) -> Optional[datetime]:
    """Data do sobrestamento na tabela da tarefa (LEGADO.md 31088-31137)."""
    seletores = (
        'td.centralizado.td-class.ng-star-inserted',
        'td[class*="data"]',
        'td[class*="prazo"]',
        '.data-sobrestamento',
    )
    for seletor in seletores:
        try:
            celulas = espera.elementos(driver, seletor, teto=1)
        except Exception:
            continue
        for celula in celulas:
            celula_texto = (getattr(celula, 'text_content', None) and celula.text_content()) or getattr(celula, 'text', '') or ''
            data_str = _data_para_numerico(celula_texto)
            if not data_str:
                continue
            try:
                return datetime.strptime(data_str, '%d/%m/%Y')
            except ValueError:
                continue
    return None


def _match_def_sob(texto_norm: str, chave: str) -> bool:
    """Casa a regra pelo padrão compilado ou pelos termos do legado."""
    if DEF_SOB_PATTERNS[chave].search(texto_norm):
        return True
    from .runtime_pec import gerar_regex_geral
    return any(gerar_regex_geral(termo).search(texto_norm) for termo in DEF_SOB_TERMOS[chave])


def _extrair_decisao_sobrestamento_api(driver: Any, timeout: int = 10) -> Optional[str]:
    """
    Extrai conteúdo da decisão de sobrestamento via API REST + pdfplumber.
    ANTES de clicar no documento (enquanto URL ainda é /processo).
    
    Reusa lógica de Prazo/p2b_gateway.py que funciona de verdade.
    """
    try:
        from Fix.variaveis import session_from_driver
        import io
        import pdfplumber
        
        # 1) Obter id_processo da URL
        m = re.search(r'/processo/(\d+)', driver.current_url)
        if not m:
            logger.warning('[DEF_SOB_API] id_processo não detectado na URL')
            return None
        id_processo = m.group(1)
        
        sess, host = session_from_driver(driver)
        base = f'https://{host}'
        
        # 2) Timeline via API
        url_timeline = (
            f'{base}/pje-comum-api/api/processos/id/{id_processo}/timeline'
            '?buscarDocumentos=true&buscarMovimentos=false'
        )
        try:
            r = sess.get(url_timeline, timeout=timeout)
            if r.status_code == 401:
                logger.warning('[DEF_SOB_API] Sessão expirada (401)')
                return None
            r.raise_for_status()
            timeline = r.json()
        except Exception as e:
            logger.warning(f'[DEF_SOB_API] timeline HTTP error: {e}')
            return None
        
        # 3) Buscar decisão de sobrestamento
        doc = None
        for item in timeline:
            tipo = (item.get('tipo') or '').lower().strip()
            if 'decis' in tipo and 'sobrest' in tipo:
                doc = item
                logger.debug(f'[DEF_SOB_API] Encontrado: {item.get("titulo", "?")}')
                break
        
        # Fallback: qualquer decisão
        if not doc:
            for item in timeline:
                tipo = (item.get('tipo') or '').lower().strip()
                if 'decis' in tipo:
                    doc = item
                    logger.debug(f'[DEF_SOB_API] Fallback decisão: {item.get("titulo", "?")}')
                    break
        
        if not doc:
            logger.warning('[DEF_SOB_API] Nenhuma decisão encontrada na timeline')
            return None
        
        id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
        
        # 4) Baixar PDF
        url_conteudo = f'{base}/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
        try:
            r = sess.get(url_conteudo, timeout=timeout, stream=True)
            r.raise_for_status()
            pdf_bytes = r.content
        except Exception as e:
            logger.warning(f'[DEF_SOB_API] /conteudo download error: {e}')
            return None
        
        if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
            logger.warning(f'[DEF_SOB_API] Não é PDF válido')
            return None
        
        # 5) Extrair com pdfplumber
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                paginas = [p.extract_text() or '' for p in pdf.pages]
            texto = '\n\n'.join(paginas).strip()
            if texto:
                logger.debug(f'[DEF_SOB_API] Texto extraído: {len(texto)} chars')
                return texto
        except Exception as e:
            logger.warning(f'[DEF_SOB_API] pdfplumber error: {e}')
        
        return None
    except Exception as e:
        logger.error(f'[DEF_SOB_API] Erro geral: {e}')
        return None


def def_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 10) -> bool:
    """
    Analisa a decisão de sobrestamento e executa a ação da regra casada.

    Fluxo (LEGADO.md 30692-31476):
    1. Seleciona a última decisão relevante da timeline (despacho/decisão/
       sentença/conclusão), preferindo a assinada por magistrado, e captura a
       data dessa decisão (title do .tl-item-hora) — insumo das regras.
    2. Extrai o texto: API/PDF antes do clique (padrão P2B) e, se falhar, via
       DOM (clicando na decisão selecionada).
    3. Testa os padrões na ordem do legado e executa a ação correspondente.
    """
    logger.debug(f"[DEF_SOB] Iniciando para {numero_processo}")
    if not driver or not numero_processo:
        logger.error("[DEF_SOB] Driver ou numero_processo inválidos")
        return False
    if not observacao or not isinstance(observacao, str):
        logger.error("[DEF_SOB] observacao inválida ou não fornecida")
        return False
    if timeout <= 0:
        logger.error("[DEF_SOB] timeout deve ser positivo")
        return False

    # ── Step 1: seleção da decisão + data (antes de clicar) ──
    doc_link, data_decisao_str = _selecionar_decisao_timeline(driver)
    if data_decisao_str:
        logger.debug(f'[DEF_SOB] Data da decisão: {data_decisao_str}')

    # ── Step 2: extração via API/PDF (ANTES de clicar) ──
    texto = None
    try:
        texto = _extrair_decisao_sobrestamento_api(driver, timeout=timeout)
        if texto and len(texto.strip()) > 50:
            logger.info(f'[DEF_SOB] Extração via API bem-sucedida ({len(texto)} chars)')
    except Exception as e:
        logger.warning(f'[DEF_SOB] Extração via API falhou: {e}')

    # ── Fallback DOM: clica na decisão selecionada e extrai o conteúdo ──
    if not texto or len((texto or '').strip()) < 50:
        if doc_link is None:
            logger.error('[DEF_SOB] Nenhum documento relevante encontrado na timeline')
            return False
        logger.debug('[DEF_SOB] Tentando fallback DOM...')
        meio_timeout = max(1, timeout // 2)
        try:
            if safe_click_no_scroll(driver, doc_link, log=debug):
                aguardar_renderizacao_nativa(driver, 'div.conteudo-principal', timeout=meio_timeout)
                resultado = extrair_direto(driver, timeout=meio_timeout, debug=False, formatar=True)
                if resultado and resultado.get('sucesso'):
                    texto = resultado.get('conteudo')
                    if texto:
                        logger.debug(f'[DEF_SOB] Extração DOM bem-sucedida ({len(texto)} chars)')
        except Exception as e:
            logger.warning(f'[DEF_SOB] Extração DOM falhou: {e}')

    if not texto or len(texto.strip()) < 10:
        logger.warning(f"[DEF_SOB] Texto muito curto (len={len(texto) if texto else 0})")
        return False

    # ── Step 3: normalizar e testar padrões ──
    texto_norm = normalizar_texto(texto)
    logger.debug(f"[DEF_SOB] Texto normalizado (200): {texto_norm[:200]}")

    # Ações associadas
    def _remover_chips():
        """def_chip é não-crítico: falha não deve abortar a regra."""
        try:
            chips_padrao = ["Prazo vencido", "Prazo vencido pos sentenca", "SISBAJUD"]
            def_chip(driver, numero_processo=numero_processo, observacao=observacao,
                     chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
        except Exception as e:
            logger.debug(f'[DEF_SOB] def_chip falhou (não crítico): {e}')

    def executar_retorno_feito():
        try:
            return mov_sob(driver, numero_processo, "sob 4", debug=debug, timeout=timeout)
        except Exception as e:
            logger.error(f'[DEF_SOB] mov_sob (retorno do feito) falhou: {e}')
            return False

    def executar_penhora_rosto():
        """def_chip + GIGS '-1/xs rosto' + mov_sob 1 (LEGADO.md 31370-31427).

        A GIGS é best-effort: se mov_sob falhar mas a GIGS saiu, a regra é
        considerada cumprida (mesmo retorno do legado).
        """
        _remover_chips()
        ok_gigs = False
        try:
            ok_gigs = bool(criar_gigs(driver, '-1', '', 'xs rosto'))
        except Exception as e:
            logger.warning(f'[DEF_SOB] criar_gigs xs rosto falhou: {e}')
        try:
            if mov_sob(driver, numero_processo, "sob 1", debug=debug, timeout=timeout):
                return True
            logger.error('[DEF_SOB] mov_sob (penhora no rosto) retornou False')
        except Exception as e:
            logger.error(f'[DEF_SOB] mov_sob (penhora no rosto) falhou: {e}')
        return ok_gigs

    def executar_precatorio():
        """Precatório/RPV/pequeno valor (LEGADO.md 30938-31013).

        Meses necessários para o sobrestamento vencer em JULHO/2026, contados da
        data da decisão. Em JULHO/2026, cria a GIGS '-1/silas/precatorio' em vez
        de mover o sobrestamento.
        """
        _remover_chips()
        hoje = datetime.now()
        if hoje.year == 2026 and hoje.month == 7:
            logger.info('[DEF_SOB] JULHO/2026 — criando GIGS -1/silas/precatorio')
            try:
                return bool(criar_gigs(driver, '-1', 'silas', 'precatorio'))
            except Exception as e:
                logger.error(f'[DEF_SOB] criar_gigs precatorio falhou: {e}')
                return False

        meses_necessarios = 1
        if data_decisao_str:
            try:
                data_decisao_dt = datetime.strptime(data_decisao_str, '%d/%m/%Y')
                alvo = datetime(2026, 7, 1)
                meses_necessarios = max(1, (alvo.year - data_decisao_dt.year) * 12 + (alvo.month - data_decisao_dt.month))
                logger.debug(f'[DEF_SOB] decisão {data_decisao_str} → {meses_necessarios} meses até 07/2026')
            except Exception as e:
                logger.warning(f'[DEF_SOB] Falha ao calcular meses até 07/2026 ({data_decisao_str}): {e}')
        else:
            logger.warning('[DEF_SOB] Data da decisão indisponível — usando 1 mês')
        try:
            return mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=debug, timeout=timeout)
        except Exception as e:
            logger.error(f'[DEF_SOB] mov_sob {meses_necessarios} meses falhou: {e}')
            return False

    def executar_juizo_universal():
        """Juízo universal (LEGADO.md 31015-31265).

        Abre a tarefa do processo, lê o prazo atual do sobrestamento e:
        - menos de 8 meses desde a decisão → ajusta o sobrestamento para
          completar 9 meses (mov_sob com os meses faltantes);
        - 8+ meses (ou prazo não lido) → encerra o sobrestamento
          (mov_fimsob + ato_fal).
        """
        if not data_decisao_str:
            logger.error('[DEF_SOB][JUIZO] Data da decisão indisponível — abortando regra')
            return False
        try:
            data_decisao_dt = datetime.strptime(data_decisao_str, '%d/%m/%Y')
        except Exception as e:
            logger.error(f'[DEF_SOB][JUIZO] Data da decisão inválida ({data_decisao_str}): {e}')
            return False

        # 1) Abrir a tarefa do processo (Fix.core + Fix.abas — não reinventar abas)
        btn_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_tarefa:
            logger.error('[DEF_SOB][JUIZO] Botão "Abrir tarefa do processo" não encontrado')
            return False
        aba_processo = driver.current_window_handle
        if not safe_click(driver, btn_tarefa):
            logger.error('[DEF_SOB][JUIZO] Falha no clique da tarefa do processo')
            return False
        try:
            driver.switch_to.window(aguardar_nova_aba(driver, aba_processo, timeout=timeout))
        except Exception:
            logger.warning('[DEF_SOB][JUIZO] Nenhuma nova aba detectada — seguindo na aba atual')
        aguardar_renderizacao_nativa(driver)

        # 2) Prazo decorrido desde a decisão e data atual do sobrestamento
        meses_decorridos = (datetime.now() - data_decisao_dt).days / 30.44
        data_sobrestamento = _data_sobrestamento_na_tarefa(driver)
        logger.info(
            f'[DEF_SOB][JUIZO] decisão={data_decisao_dt:%d/%m/%Y} | decorrido={meses_decorridos:.1f} meses | '
            f'sobrestamento={data_sobrestamento.strftime("%d/%m/%Y") if data_sobrestamento else "não lido"}'
        )

        if data_sobrestamento and meses_decorridos < 8:
            meses_necessarios = max(1, math.ceil(9 - meses_decorridos))
            logger.info(f'[DEF_SOB][JUIZO] Ajustando sobrestamento para {meses_necessarios} meses')
            try:
                if mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=debug, timeout=timeout):
                    return True
                logger.warning('[DEF_SOB][JUIZO] Ajuste falhou — executando fluxo completo')
            except Exception as e:
                logger.warning(f'[DEF_SOB][JUIZO] Erro no ajuste ({e}) — executando fluxo completo')

        # 3) Fluxo completo: encerrar sobrestamento + ato_fal
        if not mov_fimsob(driver, debug=debug):
            logger.error('[DEF_SOB][JUIZO] mov_fimsob falhou')
            return False
        if aba_processo in getattr(driver, 'window_handles', []):
            driver.switch_to.window(aba_processo)
        return bool(ato_fal(driver, debug=debug))

    def executar_prescricao():
        try:
            logger.info(f"[DEF_SOB][PRESCRICAO] Iniciando def_presc para {numero_processo}")
            from PEC.prescricao import def_presc
            resultado = def_presc(driver, numero_processo, texto, data_decisao_str, debug=debug)
            logger.info(f"[DEF_SOB][PRESCRICAO] def_presc retornou: {resultado}")
            return resultado
        except Exception as e:
            logger.error(f"[DEF_SOB][PRESCRICAO] Exceção em def_presc: {e}")
            import traceback
            logger.error(f"[DEF_SOB][PRESCRICAO] Traceback:\n{traceback.format_exc()}")
            return False

    def executar_autos_principais():
        """mov_fimsob + ato_prov, voltando à aba do processo para o ato (LEGADO.md 31310-31365)."""
        aba_processo = driver.current_window_handle
        try:
            if not mov_fimsob(driver, debug=debug):
                return False
            if aba_processo in getattr(driver, 'window_handles', []):
                driver.switch_to.window(aba_processo)
            return bool(ato_prov(driver, debug=debug))
        except Exception as e:
            logger.error(f'[DEF_SOB] autos principais falhou: {e}')
            return False

    # ── Step 5: Testar e executar regras (ordem do legado) ──
    regras = [
        ('retorno_feito_principal', executar_retorno_feito, 'Retorno do feito principal'),
        ('penhora_rosto', executar_penhora_rosto, 'Penhora no rosto'),
        ('precatorio', executar_precatorio, 'Precatorio/RPV/Pequeno valor'),
        ('juizo_universal', executar_juizo_universal, 'Juízo universal'),
        ('prescricao', executar_prescricao, 'Prazo prescricional'),
        ('autos_principais', executar_autos_principais, 'Autos principais'),
    ]

    for chave, acao, descricao in regras:
        if not _match_def_sob(texto_norm, chave):
            logger.debug(f"[DEF_SOB] Padrão '{descricao}': não")
            continue
        logger.info(f"[DEF_SOB] Regra '{descricao}' ativada")
        try:
            if acao():
                logger.info(f"[DEF_SOB] Execução OK para '{descricao}'")
                return True
            logger.error(f"[DEF_SOB] Execução falhou para '{descricao}' (retornou False)")
            return False
        except Exception as e:
            logger.error(f"[DEF_SOB] Exceção ao executar '{descricao}': {e}")
            import traceback
            logger.error(f"[DEF_SOB] Traceback:\n{traceback.format_exc()}")
            return False

    logger.warning("[DEF_SOB] Nenhum padrão correspondeu ao texto")
    return False


# ───────────────────────────────────────────────────────
# SEÇÃO ANTIGA (REMOVIDA) - deixa aqui para referência
# ───────────────────────────────────────────────────────
# Antes: tinha fallback em extrair_documento + extrair_pdf
# Antes: tinha lógica complexa com regras_def_sob list
# Refatorado: padrão P2B simples (regex pattern → action)
