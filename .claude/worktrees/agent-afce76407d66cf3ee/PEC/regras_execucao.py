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

logger = logging.getLogger(__name__)


# ── Definicao de Buckets ──
BUCKET_ORDEM = ['carta', 'comunicacoes', 'sobrestamento', 'sob', 'outros', 'sisbajud']


# ─── helpers: acoes com logica interna ou assinatura especial ────────────────

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
    def_sob(driver, atv.numero_processo, atv.observacao)


def _pz_idpj(driver, atv):
    """pz idpj: cria gigs edital intimacao + ato IDPJ."""
    from Fix.extracao import criar_gigs
    from atos.judicial import ato_idpj
    criar_gigs(driver, 1, 'Ingrid', 'edital intimacao correio')
    ato_idpj(driver)


def _xs_meios(driver, atv):
    """xs meios: inclusao BNDT + ato meios."""
    from Fix.extracao import bndt
    from atos.judicial import ato_meios
    bndt(driver, inclusao=True)
    ato_meios(driver)


def _xs_socio(driver, atv):
    """xs socio: inclusao BNDT + termo socio."""
    from Fix.extracao import bndt
    from atos.wrappers_ato import ato_termoS
    bndt(driver, inclusao=True)
    ato_termoS(driver)


def _empresa_termo(driver, atv):
    """empresa termo: inclusao BNDT + termo empresa."""
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
    movimentar_inteligente(driver, 'Audiencia')


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
registry.register(r'\bxs\s+carta\b',                                    'carta',    _w(carta))
# ── SOB ───────────────────────────────────────────────────────────────────────
registry.register(r'\bsob\s+chip\b',                                    'sob',      _w(def_chip))
registry.register(r'\bsobrestamento\s+vencido\b',                       'sob',      _def_sob)
registry.register(r'\bsob\s+\d+|\bxs\s+\d+$',                          'sob',      _sob_n)
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
registry.register(r'\bxs\s+sigilo\b',                                   'comunicacoes', (_w(_a(w, 'pec_sigilo')), lambda driver, atv: __import__('atos.movimentos_fluxo', fromlist=['movimentar_inteligente']).movimentar_inteligente(driver, 'Aguardando Prazo')))
# ── OUTROS ────────────────────────────────────────────────────────────────────
registry.register(r'\bxs\s+audx\b|\baudx\b|\baud\s+x\b',               'outros',   _audx_mov_int)
registry.register(r'\bxs\s+parcial\b',                                  'outros',   _w(ato_bloq))
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
    bucket, action = registry.match(obs)
    if bucket is None:
        return None
    for pattern, rule_bucket, acao in REGRAS:
        if rule_bucket == bucket and acao is action and pattern.search(obs):
            return pattern, rule_bucket, acao
    return None


# ═══════════════════════════════════════════════════════════════
# SOBRESTAMENTO
# ═══════════════════════════════════════════════════════════════

def def_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 10) -> bool:
    """
    Analisa ultima decisao e executa acao baseada no conteudo.

    Estrategias suportadas:
    - Retorno do feito principal
    - Penhora no rosto
    - Precatorio/RPV/Pequeno valor
    - Juizo universal
    - Prazo prescricional
    - Autos principais

    Args:
        driver: WebDriver do Selenium
        numero_processo: Numero do processo
        observacao: Observacao do processo
        debug: Se True, exibe logs detalhados
        timeout: Timeout para operacoes (segundos)

    Returns:
        bool: True se executado com sucesso
    """
    # ── ETAPA 0: Verificacao de condicoes ──
    if not driver:
        logger.error("[DEF_SOB] driver nao fornecido")
        return False

    if not numero_processo or not isinstance(numero_processo, str):
        logger.error(f"[DEF_SOB] numero_processo invalido: {numero_processo}")
        return False

    if not observacao or not isinstance(observacao, str):
        logger.error(f"[DEF_SOB] observacao invalida: {observacao}")
        return False

    if timeout <= 0:
        logger.error(f"[DEF_SOB] timeout deve ser positivo: {timeout}")
        return False

    def log_msg(msg):
        if debug:
            logger.info(f"[DEF_SOB] {msg}")

    logger.info(f"[DEF_SOB] Iniciando analise sobrestamento: {numero_processo}")
    log_msg(f"Observacao: {observacao}")

    try:
        # ── ETAPA 1: Consulta de sobrestamento ──
        log_msg("0. Abrindo tarefa do processo...")
        btn_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_tarefa:
            logger.error("[DEF_SOB] Botao tarefa do processo nao encontrado")
            return False
        if not safe_click(driver, btn_tarefa):
            logger.error("[DEF_SOB] Falha ao clicar no botao tarefa do processo")
            return False

        log_msg("1. Selecionando decisoes na timeline...")
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg(" Nenhum item encontrado na timeline")
            return False

        docs_decisao = []
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'decisão|decisao', doc_text):
                    continue
                if re.search(r'sentença|sentenca', doc_text):
                    continue
                docs_decisao.append((item, link))
            except Exception:
                continue

        if not docs_decisao:
            logger.error("[DEF_SOB] Nenhuma decisao encontrada na timeline")
            return False

        iteracoes = 0
        for doc_item, doc_link in docs_decisao:
            if iteracoes >= 3:
                log_msg(" Limite de 3 decisoes analisadas atingido.")
                logger.warning(f"[DEF_SOB] Limite de iteracoes atingido sem encontrar regra no processo {numero_processo}. Encaminhando para verificacao manual.")
                return True

            iteracoes += 1
            log_msg(f" Documento em analise [{iteracoes}/3]: {doc_link.text}")

            # ===== Extrair data da decisao =====
            data_decisao_str = None
            try:
                hora_element = doc_item.find_element(By.CSS_SELECTOR, '.tl-item-hora')
                if hora_element:
                    title_attr = hora_element.get_attribute('title')
                    if title_attr:
                        data_decisao_str = title_attr.split(' ')[0]
                        log_msg(f" Data da decisao extraida: {data_decisao_str}")
            except Exception as e:
                log_msg(f" Erro ao extrair data da decisao: {e}")

            # Clica no documento
            try:
                SCRIPTS_DIR = Path(__file__).parent / "scripts"
                script_scroll = carregar_js("scroll_into_view_instant.js", SCRIPTS_DIR)
                driver.execute_script(script_scroll, doc_link)
                try:
                    WebDriverWait(driver, 1).until(lambda d: doc_link.is_displayed())
                except Exception:
                    pass
                doc_link.click()
                try:
                    WebDriverWait(driver, 5).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                except Exception:
                    pass
            except Exception as e:
                log_msg(f" Erro ao clicar no documento: {e}")
                continue

            # Sub-etapa: extrair conteudo do documento
            log_msg("2. Extraindo conteudo do documento...")
            texto = None
            try:
                resultado_extracao = extrair_direto(driver, timeout=timeout, debug=debug, formatar=True)
                if resultado_extracao['sucesso']:
                    texto = resultado_extracao['conteudo']
            except Exception:
                pass

            if not texto or len(texto.strip()) < 10:
                try:
                    texto = extrair_documento(driver, regras_analise=None, timeout=timeout, log=debug)
                    if texto:
                        texto = texto.lower()
                except Exception:
                    pass

            if not texto or len(texto.strip()) < 10:
                try:
                    texto_pdf = extrair_pdf(driver, log=debug)
                    if texto_pdf:
                        texto = texto_pdf.lower()
                except Exception:
                    pass

            if not texto or len(texto.strip()) < 10:
                log_msg(" Texto extraido muito curto ou vazio para este doc. Pulando para o proximo.")
                continue

            log_texto = texto[:200] + '...' if len(texto) > 200 else texto
            log_msg(f"Texto extraido: {log_texto}")

            # ── ETAPA 2: Aplicacao do sobrestamento ──
            log_msg("3. Analisando conteudo e aplicando regras...")

            def remover_acentos(txt):
                return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

            def normalizar_texto(txt):
                return remover_acentos(txt.lower())

            def gerar_regex_geral(termo):
                termo_norm = normalizar_texto(termo)
                palavras = termo_norm.split()
                partes = [re.escape(p) for p in palavras]
                regex = r''
                for i, parte in enumerate(partes):
                    regex += parte
                    if i < len(partes) - 1:
                        regex += r'[\s\.,;:!\-–—]*'
                return re.compile(rf"{regex}", re.IGNORECASE)

            texto_normalizado = normalizar_texto(texto)

            # FUNCOES DE ACAO
            def executar_mov_sob_retorno_feito():
                try:
                    return mov_sob(driver, numero_processo, "sob 4", debug=True, timeout=timeout)
                except Exception:
                    return False

            def executar_penhora_rosto():
                try:
                    chips_padrao = ["Prazo vencido", "Prazo vencido pos sentenca", "SISBAJUD"]
                    try:
                        def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
                    except Exception:
                        pass
                    ok_gigs = False
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
                except Exception:
                    return False

            def executar_mov_sob_precatorio():
                try:
                    chips_padrao = ["Prazo vencido", "Prazo vencido pos sentenca", "SISBAJUD"]
                    try:
                        def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
                    except Exception:
                        pass

                    meses_necessarios = 1
                    try:
                        from datetime import datetime
                        if data_decisao_str:
                            dt = datetime.strptime(data_decisao_str, "%d/%m/%Y")
                            target = datetime(2026, 7, 1)
                            meses_necessarios = (target.year - dt.year) * 12 + (target.month - dt.month)
                            if meses_necessarios < 1:
                                meses_necessarios = 1
                    except Exception:
                        meses_necessarios = 1

                    try:
                        from datetime import datetime
                        hoje = datetime.now()
                        if hoje.year == 2026 and hoje.month == 7:
                            if criar_gigs(driver, '-1', 'silas', 'precatorio'):
                                return True
                            return False
                    except Exception:
                        pass

                    return mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=True, timeout=timeout)
                except Exception:
                    return False

            def executar_juizo_universal():
                return False

            def executar_def_presc():
                try:
                    from PEC.prescricao import def_presc as def_presc_func
                    return def_presc_func(driver, numero_processo, texto, data_decisao_str, debug=debug)
                except Exception:
                    return False

            def executar_ato_prov():
                try:
                    res_fimsob = mov_fimsob(driver, debug=debug)
                    if not res_fimsob:
                        return False
                    res_prov = ato_prov(driver, debug=debug)
                    return True if res_prov else False
                except Exception:
                    return False

            regras_def_sob = [
                (['retorno do feito principal'], executar_mov_sob_retorno_feito, 'Retorno do feito principal'),
                (['penhora no rosto'], executar_penhora_rosto, 'Penhora no rosto'),
                (['precatorio', 'RPV', 'pequeno valor'], executar_mov_sob_precatorio, 'Precatorio/RPV/Pequeno valor'),
                (['juizo universal'], executar_juizo_universal, 'Juizo universal'),
                (['prazo prescricional'], executar_def_presc, 'Prazo prescricional'),
                (['autos principais', 'processo principal'], executar_ato_prov, 'Autos principais'),
            ]

            regra_com_sucesso = False
            for termos, acao_func, descricao in regras_def_sob:
                for termo in termos:
                    regex = gerar_regex_geral(termo)
                    if regex.search(texto_normalizado):
                        logger.info(f"[DEF_SOB] Regra encontrada: {descricao} (termo: '{termo}') no doc {doc_link.text}")
                        resultado = acao_func()
                        if resultado:
                            logger.info(f"[DEF_SOB] Regra '{descricao}' executada com sucesso")
                            return True
                        else:
                            logger.error(f"[DEF_SOB] Falha na regra '{descricao}'")
                            regra_com_sucesso = True
                        break
                if regra_com_sucesso:
                    break

            if regra_com_sucesso:
                logger.warning(f"[DEF_SOB] Regra encontrada no doc '{doc_link.text}' mas falhou na execucao.")
                return False

            log_msg(" Nenhuma regra aplicada neste documento, tentando a proxima decisao na timeline...")

        # ── ETAPA 3: Finalizacao ──
        logger.warning(f"[DEF_SOB] Nenhuma decisao na timeline validou as regras de sobrestamento para {numero_processo}. Encaminhando para verificacao manual.")
        return True

    except Exception as e:
        logger.error(f"[DEF_SOB] Erro geral em def_sob ({numero_processo}): {e}")
        import traceback
        logger.exception("Erro detectado em def_sob")
        return False
