"""PEC - Regras de Execucao

Consolidado de: regras_pec, sobrestamento.
"""

import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from atos.judicial import ato_fal, ato_prov, ato_termoS
from atos.movimentos import def_chip, mov_sob, mov_fimsob
from core.rule_registry import RuleRegistry, adapt_action as _w
from Fix.extracao import extrair_direto, extrair_documento, extrair_pdf, criar_gigs, bndt
from Fix.facade_publica import carregar_js
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.selenium_base import esperar_elemento, safe_click
from Fix.utils import normalizar_texto

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


# ── Definicao de Buckets ──
# Sobrestamento vencido deve ser processado por ÚLTIMO, imediatamente antes de SISBAJUD
BUCKET_ORDEM = ['xs_sob', 'carta', 'comunicacoes', 'outros', 'sobrestamento', 'sisbajud']


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
    """pz idpj: cria gigs edital intimacao + ato IDPJ."""
    from Fix.extracao import criar_gigs
    from atos.judicial import ato_idpj
    return _executar_passos(
        lambda: criar_gigs(driver, 1, 'Ingrid', 'edital intimacao correio'),
        lambda: ato_idpj(driver),
    )


def _xs_meios(driver, atv):
    """xs meios: inclusao BNDT + ato meios."""
    from Fix.extracao import bndt
    from atos.judicial import ato_meios
    return _executar_passos(
        lambda: bndt(driver, inclusao=True),
        lambda: ato_meios(driver),
    )


def _xs_socio(driver, atv):
    """xs socio: inclusao BNDT + termo socio."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoS
    return _executar_passos(
        lambda: bndt(driver, inclusao=True),
        lambda: ato_termoS(driver),
    )


def _empresa_termo(driver, atv):
    """empresa termo: inclusao BNDT + termo empresa."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoE
    return _executar_passos(
        lambda: bndt(driver, inclusao=True),
        lambda: ato_termoE(driver),
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


def _executar_sisbajud(driver, atv, fn_sisb):
    """Executa o fluxo completo PJE -> SISBAJUD para acoes SISBAJUD."""
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
registry.register(r'teimosinha\s+60|t2\s+60|\b60\s*d\b|60\s+dias',    'sisbajud', _sisbajud_minuta_60)
registry.register(r'\bteimosinha\b|\bt2\b',                             'sisbajud', _sisbajud_minuta)
registry.register(r'\bxs\s+resultado\b|\bresultado\b',                  'sisbajud', _sisbajud_processar_ordem)
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
registry.register(r'\bxs\s+edital\b|\bpec\s+edital\b|\bxs\s+pec\s+edital\b',
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
registry.register(r'\bempresa\s*termo\b|\btermoempresa\b',              'outros',   _empresa_termo)

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

# Padrões regex para regras de sobrestamento (padrão P2B)
DEF_SOB_PATTERNS = {
    'retorno_feito_principal': re.compile(r'retorno do feito principal|retorno\s+do\s+feito|volta dos autos', re.IGNORECASE),
    'penhora_rosto': re.compile(r'penhora no rosto|penhora\s+no\s+rosto|sobre\s+os\s+bens', re.IGNORECASE),
    'precatorio': re.compile(r'precatorio|RPV|pequeno valor|saldo\s+devedor|até\s+.*\s+UFRGS|beneficiario do FGTS', re.IGNORECASE),
    'prescricao': re.compile(r'prazo prescricional|prescricao|prescricional', re.IGNORECASE),
    'autos_principais': re.compile(r'autos principais|processo principal|retorno\s+ao\s+processo', re.IGNORECASE),
}


def def_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 10) -> bool:
    """
    Analisa decisão na aba /detalhe e executa ação (Padrão P2B).
    Versão instrumentada com logs detalhados.
    """
    logger.debug(f"[DEF_SOB] Iniciando para {numero_processo}")
    if not driver or not numero_processo:
        logger.error("[DEF_SOB] Driver ou numero_processo inválidos")
        return False

    try:
        # ── Step 1: Localizar última decisão ──
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        logger.debug(f"[DEF_SOB] Encontrados {len(itens)} itens na timeline")
        if not itens:
            logger.warning(f"[DEF_SOB] Nenhum item na timeline para {numero_processo}")
            return True

        doc_item, doc_link = None, None
        # Prioridade: documento COM ícone de magistrado
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                # ✅ Apenas decisões (NUNCA despacho, sentença, conclusão)
                if not re.search(r'^decis[ãa]o', link.text.lower()):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                if mag_icons:
                    doc_item, doc_link = item, link
                    logger.debug(f"[DEF_SOB] Documento com ícone magistrado: '{link.text}'")
                    break
            except Exception as e:
                logger.warning(f"[DEF_SOB] Erro ao processar item (magistrado): {e}")
        # Fallback: primeiro documento relevante
        if not doc_link:
            for item in itens:
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    if re.search(r'^decis[ãa]o', link.text.lower()):
                        doc_item, doc_link = item, link
                        logger.debug(f"[DEF_SOB] Fallback: '{link.text}'")
                        break
                except Exception:
                    continue

        if not doc_link:
            logger.warning(f"[DEF_SOB] Nenhuma decisão/despacho encontrada")
            return True

        # ── Step 2: Clicar e aguardar ──
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", doc_link)
            doc_link.click()
            # Aguardar aparecimento do conteúdo (não apenas readyState)
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return !!document.querySelector('.documento-visualizacao, #documento, pje-arvore-documento')")
            )
            time.sleep(0.5)
            logger.debug("[DEF_SOB] Documento clicado e aguardado")
        except Exception as e:
            logger.error(f"[DEF_SOB] Falha ao clicar/aguardar: {e}")
            return False

        # ── Step 3: Extrair conteúdo (com debug=True) ──
        texto = None
        try:
            resultado = extrair_direto(driver, timeout=timeout, debug=True, formatar=True)
            if resultado and resultado.get('sucesso'):
                texto = resultado.get('conteudo')
                if texto:
                    logger.debug(f"[DEF_SOB] Texto extraído ({len(texto)} chars): {texto[:200]}")
                else:
                    logger.warning("[DEF_SOB] extrair_direto retornou conteúdo vazio")
            else:
                logger.warning(f"[DEF_SOB] extrair_direto falhou: resultado={resultado}")
        except Exception as e:
            logger.error(f"[DEF_SOB] Erro em extrair_direto: {e}")

        if not texto or len(texto.strip()) < 10:
            logger.warning(f"[DEF_SOB] Texto muito curto (len={len(texto) if texto else 0})")
            return True

        # ── Step 4: Normalizar e testar padrões ──
        texto_norm = normalizar_texto(texto)
        logger.debug(f"[DEF_SOB] Texto normalizado (200): {texto_norm[:200]}")

        # Ações associadas
        def executar_retorno_feito():
            try:
                return mov_sob(driver, numero_processo, "sob 4", debug=debug, timeout=timeout)
            except Exception:
                return False

        def executar_penhora_rosto():
            try:
                chips_padrao = ["Prazo vencido", "Prazo vencido pos sentenca", "SISBAJUD"]
                def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
            except Exception:
                pass
            try:
                ok_gigs = criar_gigs(driver, 1, '', 'xs rosto', detalhe=True)
            except Exception:
                ok_gigs = False
            try:
                if mov_sob(driver, numero_processo, "sob 1", debug=debug):
                    return True
                return ok_gigs
            except Exception:
                return ok_gigs

        def executar_precatorio():
            try:
                chips_padrao = ["Prazo vencido", "Prazo vencido pos sentenca", "SISBAJUD"]
                def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
            except Exception:
                pass
            try:
                if criar_gigs(driver, '-1', 'silas', 'precatorio'):
                    return True
            except Exception:
                pass
            try:
                return mov_sob(driver, numero_processo, "sob 1", debug=debug, timeout=timeout)
            except Exception:
                return False

        def executar_prescricao():
            try:
                from PEC.prescricao import def_presc
                return def_presc(driver, numero_processo, texto, debug=debug)
            except Exception:
                return False

        def executar_autos_principais():
            try:
                if mov_fimsob(driver, debug=debug):
                    return ato_prov(driver, debug=debug)
            except Exception:
                return False

        # ── Step 5: Testar e executar regras ──
        regras = [
            (DEF_SOB_PATTERNS['retorno_feito_principal'], executar_retorno_feito, 'Retorno do feito principal'),
            (DEF_SOB_PATTERNS['penhora_rosto'], executar_penhora_rosto, 'Penhora no rosto'),
            (DEF_SOB_PATTERNS['precatorio'], executar_precatorio, 'Precatorio/RPV/Pequeno valor'),
            (DEF_SOB_PATTERNS['prescricao'], executar_prescricao, 'Prazo prescricional'),
            (DEF_SOB_PATTERNS['autos_principais'], executar_autos_principais, 'Autos principais'),
        ]

        for pattern, acao, descricao in regras:
            match = pattern.search(texto_norm)
            logger.debug(f"[DEF_SOB] Padrão '{descricao}': match={'SIM' if match else 'NÃO'}")
            if match:
                logger.info(f"[DEF_SOB] Regra '{descricao}' ativada")
                resultado_acao = acao()
                if resultado_acao:
                    logger.info(f"[DEF_SOB] Execução OK")
                    return True
                else:
                    logger.error(f"[DEF_SOB] Execução falhou")
                    return False

        logger.warning(f"[DEF_SOB] Nenhum padrão correspondeu ao texto")
        return True

    except Exception as e:
        logger.error(f"[DEF_SOB] Exceção geral: {e}")
        logger.exception("Traceback completo:")
        return False


# ───────────────────────────────────────────────────────
# SEÇÃO ANTIGA (REMOVIDA) - deixa aqui para referência
# ───────────────────────────────────────────────────────
# Antes: tinha fallback em extrair_documento + extrair_pdf
# Antes: tinha lógica complexa com regras_def_sob list
# Refatorado: padrão P2B simples (regex pattern → action)
