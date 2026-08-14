"""PEC - Regras de Execucao

Consolidado de: regras_pec, sobrestamento.
"""

import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from atos.judicial import ato_fal, ato_prov, ato_termoS
from atos.movimentos import def_chip, mov_sob, mov_fimsob
from core.rule_registry import RuleRegistry, adapt_action as _w
from Fix.extracao import extrair_direto, extrair_documento, extrair_pdf, criar_gigs, bndt
from Fix.core import safe_click_no_scroll, aguardar_renderizacao_nativa
from Fix.facade_publica import carregar_js
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.selenium_base import esperar_elemento, safe_click
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
    return _executar_passos(
        lambda: criar_gigs(driver, "1", "", "xs mddid"),
        lambda: ato_idpj(driver),
    )


def _mddid(driver, atv):
    """mdd id: pec_mddsent + pec_editalsent."""
    return _executar_passos(
        lambda: _a(w, 'pec_mddsent')(driver),
        lambda: _a(w, 'pec_editalsent')(driver),
    )


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
            _ = _shared_driver_sisb.window_handles
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


def _extrair_decisao_sobrestamento_api(driver: WebDriver, timeout: int = 10) -> Optional[str]:
    """
    Extrai conteúdo da decisão de sobrestamento via API REST + pdfplumber.
    ANTES de clicar no documento (enquanto URL ainda é /processo).
    
    Reusa lógica de Prazo/p2b_gateway.py que funciona de verdade.
    """
    try:
        from api.variaveis_client import session_from_driver
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
    Analisa decisão de sobrestamento via API+PDF (padrão P2B).
    Extrai conteúdo ANTES de clicar, garantindo extração completa.
    """
    logger.debug(f"[DEF_SOB] Iniciando para {numero_processo}")
    if not driver or not numero_processo:
        logger.error("[DEF_SOB] Driver ou numero_processo inválidos")
        return False

    # ── Step 1: Tentar extração via API (ANTES de clicar) ──
    texto = None
    try:
        texto = _extrair_decisao_sobrestamento_api(driver, timeout=timeout)
        if texto and len(texto.strip()) > 50:
            logger.info(f'[DEF_SOB] Extração via API bem-sucedida ({len(texto)} chars)')
    except Exception as e:
        logger.warning(f'[DEF_SOB] Extração via API falhou: {e}')
    
    # ── Fallback: tentar via DOM (clicar no documento) ──
    if not texto or len((texto or '').strip()) < 50:
        logger.debug('[DEF_SOB] Tentando fallback DOM...')
        try:
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
            logger.debug(f"[DEF_SOB] Encontrados {len(itens)} itens na timeline")
            
            doc_link = None
            for item in itens:
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    if re.search(r'^decis[ãa]o', link.text.lower()):
                        doc_link = link
                        logger.debug(f"[DEF_SOB] Documento localizado: '{link.text}'")
                        break
                except Exception:
                    continue
            
            if doc_link:
                try:
                    if safe_click_no_scroll(driver, doc_link, log=True):
                        aguardar_renderizacao_nativa(driver, "div.conteudo-principal", timeout=timeout//2)
                        resultado = extrair_direto(driver, timeout=timeout//2, debug=False, formatar=True)
                        if resultado and resultado.get('sucesso'):
                            texto = resultado.get('conteudo')
                            if texto:
                                logger.debug(f"[DEF_SOB] Extração DOM bem-sucedida ({len(texto)} chars)")
                except Exception as e:
                    logger.warning(f'[DEF_SOB] Extração DOM falhou: {e}')
        except Exception as e:
            logger.error(f'[DEF_SOB] Erro em fallback DOM: {e}')

    if not texto or len(texto.strip()) < 10:
        logger.warning(f"[DEF_SOB] Texto muito curto (len={len(texto) if texto else 0})")
        return True

    # ── Step 2: Normalizar e testar padrões ──
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
            logger.info(f"[DEF_SOB][PRESCRICAO] Iniciando def_presc para {numero_processo}")
            from PEC.prescricao import def_presc
            resultado = def_presc(driver, numero_processo, texto, debug=debug)
            logger.info(f"[DEF_SOB][PRESCRICAO] def_presc retornou: {resultado}")
            return resultado
        except Exception as e:
            logger.error(f"[DEF_SOB][PRESCRICAO] Exceção em def_presc: {e}")
            import traceback
            logger.error(f"[DEF_SOB][PRESCRICAO] Traceback:\n{traceback.format_exc()}")
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
            try:
                resultado_acao = acao()
                if resultado_acao:
                    logger.info(f"[DEF_SOB] Execução OK para '{descricao}'")
                    return True
                else:
                    logger.error(f"[DEF_SOB] Execução falhou para '{descricao}' (retornou False)")
                    return False
            except Exception as e:
                logger.error(f"[DEF_SOB] Exceção ao executar '{descricao}': {e}")
                import traceback
                logger.error(f"[DEF_SOB] Traceback:\n{traceback.format_exc()}")
                return False

    logger.warning(f"[DEF_SOB] Nenhum padrão correspondeu ao texto")
    return True


# ───────────────────────────────────────────────────────
# SEÇÃO ANTIGA (REMOVIDA) - deixa aqui para referência
# ───────────────────────────────────────────────────────
# Antes: tinha fallback em extrair_documento + extrair_pdf
# Antes: tinha lógica complexa com regras_def_sob list
# Refatorado: padrão P2B simples (regex pattern → action)
