# f.py -- Harness de teste isolado: Multi-testes
# Uso: py f.py [teste] [id_processo]
#   teste disponiveis: argos, sisb, pec, pesquisa, ordem, pecord, anex, juntada, triagem, probe, tdbg, todos
#   Exemplos:
#     py f.py argos            → teste Argos no processo padrão (7508281)
#     py f.py argos 7449746    → teste Argos no processo 7449746
#     py f.py sisb 1234567     → teste SISBAJUD no processo 1234567
#     py f.py probe 7449746 465383360  → probe documento 465383360 do processo 7449746
# ============================================================

import json
import logging
import time
import sys
from contextlib import contextmanager

from x import criar_driver_vt
from Fix.utils import login_cpf, navegar_para_tela

# ============================================================
# URLs de processos para testes (valores padrão)
# ============================================================
_URL_BASE = 'https://pje.trt2.jus.br/pjekz/processo'

def _resolver(id_padrao, id_override=None):
    """Retorna (url, id_str) resolvendo id_override sobre id_padrao.
    Uso: url, pid = _resolver(PADRAO, id_override)
    """
    pid = str(id_override or id_padrao)
    return f'{_URL_BASE}/{pid}/detalhe', pid

PROCESS_ID_ARGOS = '7508281'
PROCESS_ID_SISB  = '4863758'
PROCESS_ID_PEC      = '6095583'
PROCESS_ID_PEC_ORD  = '5455795'
PROCESS_ID_ANEX_CARTA = '7258019'
PROCESS_ID_TRIAGEM = '8685584'
PROBE_ID_PROCESSO = '8685584'
PROBE_ID_DOC      = '461896095'  # documento que retornou vazio no log

# Resolvidos com defaults
PROCESS_URL_ARGOS, _ = _resolver(PROCESS_ID_ARGOS)
PROCESS_URL_SISB, _  = _resolver(PROCESS_ID_SISB)
PROCESS_URL_PEC, _      = _resolver(PROCESS_ID_PEC)
PROCESS_URL_PEC_ORD, _  = _resolver(PROCESS_ID_PEC_ORD)
PROCESS_URL_ANEX_CARTA, _ = _resolver(PROCESS_ID_ANEX_CARTA)
PROCESS_URL_TRIAGEM, _ = _resolver(PROCESS_ID_TRIAGEM)

# ============================================================
# Logging
# ============================================================


class _DestaquFormatter(logging.Formatter):
    _FMT_NORMAL = '%(asctime)s %(levelname)-8s [%(name)s] %(message)s'
    _FMT_ERRO   = '\n--- %(levelname)s ---\n%(asctime)s [%(name)s] %(message)s\n' + '-' * 40

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            self._style._fmt = self._FMT_ERRO
        else:
            self._style._fmt = self._FMT_NORMAL
        return super().format(record)


def configurar_logging_debug():
    handler = logging.StreamHandler()
    handler.setFormatter(_DestaquFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(_DestaquFormatter())
            
    # Enable debug only for our modules
    for nome in ('Fix', 'PEC', 'SISB', 'atos'):
        logging.getLogger(nome).setLevel(logging.DEBUG)
        
    # Silence noisy modules
    for nome in (
        'selenium', 'selenium.webdriver', 'selenium.webdriver.remote',
        'selenium.webdriver.remote.remote_connection', 'selenium.webdriver.common.driver_finder',
        'urllib3', 'urllib3.connectionpool', 'requests',
    ):
        logging.getLogger(nome).setLevel(logging.WARNING)


LOGGER = logging.getLogger('f')


@contextmanager
def etapa(nome: str):
    inicio = time.perf_counter()
    LOGGER.info('[TESTE][%s] iniciando', nome)
    try:
        yield
        LOGGER.info('[TESTE][%s] concluido em %.2fs', nome, time.perf_counter() - inicio)
    except Exception:
        LOGGER.exception('[TESTE][%s] falhou apos %.2fs', nome, time.perf_counter() - inicio)
        raise


# ============================================================
# TESTE 1: Argos — fluxo completo real
# ============================================================

def teste_buscar_sequenciais(id_processo=None):
    """Teste do fluxo completo Argos usando o entrypoint real de Mandado."""
    from Mandado.entrada_api import processar_mandado_detalhe

    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_ARGOS, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[ARGOS_TEST] Teste real: fluxo completo Argos')
    LOGGER.info('[ARGOS_TEST] Processo: %s (id=%s)', url, pid)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[ARGOS_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[ARGOS_TEST] Falha no login')
                return

        with etapa('fluxo_argos_completo'):
            t0 = time.perf_counter()
            resultado = processar_mandado_detalhe(driver, id_processo=pid)
            LOGGER.info('[ARGOS_TEST] processar_mandado_detalhe -> %r (%.2fs)',
                        resultado, time.perf_counter() - t0)

        if resultado == 'PULAR':
            LOGGER.error('[ARGOS_TEST] Processo nao entrou no ramo Argos do fluxo real')
            return

        if not resultado:
            LOGGER.error('[ARGOS_TEST] Fluxo Argos real retornou falha')
            return

        LOGGER.info('[ARGOS_TEST] fluxo completo concluido com sucesso')

    finally:
        LOGGER.info('[ARGOS_TEST] encerrando driver')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 2: SISBAJUD — minuta_bloqueio (30/60 dias)
# ============================================================

def teste_sisbajud_minuta(id_processo=None):
    """Teste isolado da minuta de bloqueio SISBAJUD."""
    import re
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_SISB, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[SISB_TEST] Teste isolado: minuta_bloqueio SISBAJUD')
    LOGGER.info('[SISB_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None
    driver_sisb = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[SISB_TEST] Falha ao criar driver PJE')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[SISB_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[SISB_TEST] Navegando para %s', url)
            navegar_para_tela(driver, url=url)

        # Extrair dados do processo
        with etapa('extrair_dados'):
            from Fix.extracao import extrair_dados_processo
            dados_processo = extrair_dados_processo(driver)
            LOGGER.info('[SISB_TEST] Dados extraidos: %s', bool(dados_processo))

        # Salvar snapshot
        try:
            with open('dadosatuais.json', 'w', encoding='utf-8') as fh:
                json.dump(dados_processo or {}, fh, ensure_ascii=False, indent=2)
            LOGGER.info('[SISB_TEST] dadosatuais.json salvo')
        except Exception as e:
            LOGGER.warning('[SISB_TEST] Falha ao salvar dadosatuais.json: %s', e)

        # Iniciar driver SISBAJUD
        with etapa('iniciar_sisbajud'):
            from SISB.core import iniciar_sisbajud, minuta_bloqueio, minuta_bloqueio_60
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
            if not driver_sisb:
                LOGGER.error('[SISB_TEST] Falha ao iniciar SISBAJUD')
                return

        # Executar minuta (30 dias padrao, 60 se observacao contiver "60")
        with etapa('minuta_bloqueio'):
            observacao = 'teimosinha'
            if re.search(r'\b60\b|60d|60\s+dias|t2\s*60', observacao, re.IGNORECASE):
                LOGGER.info('[SISB_TEST] Chamando minuta_bloqueio_60')
                resultado = minuta_bloqueio_60(driver_sisb, dados_processo=dados_processo,
                                               driver_pje=driver, log=True, fechar_driver=False)
            else:
                LOGGER.info('[SISB_TEST] Chamando minuta_bloqueio (30 dias padrao)')
                resultado = minuta_bloqueio(driver_sisb, dados_processo=dados_processo,
                                            driver_pje=driver, log=True, fechar_driver=False)
            LOGGER.info('[SISB_TEST] Resultado: %s', resultado)

        LOGGER.info('[SISB_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[SISB_TEST] Erro nao tratado')

    finally:
        LOGGER.info('[SISB_TEST] encerrando drivers')
        try:
            if driver_sisb is not None:
                driver_sisb.quit()
        except Exception:
            pass
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 3: PEC — fluxo xs sigilo (pec_sigilo + mov_int)
# ============================================================

def teste_pec_sigilo(id_processo=None):
    """
    Teste isolado do fluxo PEC para observacao 'xs sigilo':
        1. pec_sigilo(driver) — cria comunicacao sigilosa (modelo xdecsig)
        2. movimentar_inteligente(driver, 'Aguardando Prazo') — move o processo

    Equivalente ao _xs_sigilo em PEC/regras_execucao.py.
    """
    from atos.wrappers_pec import pec_sigilo
    from atos.movimentos_fluxo import movimentar_inteligente
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_PEC, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[PEC_TEST] Teste isolado: fluxo xs sigilo (pec_sigilo + mov_int)')
    LOGGER.info('[PEC_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[PEC_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PEC_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_TEST] Navegando para %s', url)
            navegar_para_tela(driver, url=url)

        # ── ETAPA 1: pec_sigilo — comunicacao sigilosa ──
        with etapa('pec_sigilo'):
            LOGGER.info('[PEC_TEST] Executando pec_sigilo (modelo xdecsig, sigilo=True, prazo=30)...')
            ok = pec_sigilo(driver, debug=True)
            LOGGER.info('[PEC_TEST] pec_sigilo -> %s', 'OK' if ok else 'FALHA')

        # ── ETAPA 2: mov_int — mover para Aguardando Prazo ──
        with etapa('mov_int_aguardando_prazo'):
            LOGGER.info('[PEC_TEST] Movendo para Aguardando Prazo...')
            ok = movimentar_inteligente(driver, 'Aguardando Prazo')
            LOGGER.info('[PEC_TEST] movimentar_inteligente -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[PEC_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PEC_TEST] Erro nao tratado')

    finally:
        LOGGER.info('[PEC_TEST] encerrando driver')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 4: ato_pesquisas — fluxo BACEN (pesquisas para execucao)
# ============================================================

def teste_ato_pesquisas(id_processo=None):
    """
    Teste isolado do ato_pesquisas — fluxo judicial BACEN:
        - Verifica e clica 'Iniciar a execucao' se disponivel
        - Executa ato_judicial com modelo 'xsbacen', prazo=30, sigilo=True
        - Retorna (sucesso, sigilo_ativado)

    Equivalente ao chamado em Prazo/p2b_gateway.py e atos/judicial.py.
    """
    from atos.judicial import ato_pesquisas
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_PEC, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[PESQUISA_TEST] Teste isolado: ato_pesquisas (BACEN)')
    LOGGER.info('[PESQUISA_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[PESQUISA_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PESQUISA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PESQUISA_TEST] Navegando para %s', url)
            navegar_para_tela(driver, url=url)

        # ── ETAPA: ato_pesquisas ──
        with etapa('ato_pesquisas'):
            LOGGER.info('[PESQUISA_TEST] Executando ato_pesquisas (modelo xsbacen, sigilo=True) com profiling...')
            
            import cProfile
            import pstats
            import io
            
            pr = cProfile.Profile()
            pr.enable()
            
            sucesso, sigilo_ativado = ato_pesquisas(driver, debug=True)
            
            pr.disable()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumtime')
            ps.print_stats(35)
            
            LOGGER.info('[PESQUISA_TEST] PROFILING DE LATÊNCIAS:\n%s', s.getvalue())
            LOGGER.info('[PESQUISA_TEST] ato_pesquisas -> sucesso=%s sigilo_ativado=%s', sucesso, sigilo_ativado)

        LOGGER.info('[PESQUISA_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PESQUISA_TEST] Erro nao tratado')

    finally:
        LOGGER.info('[PESQUISA_TEST] encerrando driver')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 5: SISBAJUD — processar_ordem (xs resultado)
# ============================================================

def teste_sisbajud_ordem(id_processo=None):
    """
    Teste isolado do processamento de ordens SISBAJUD (fluxo 'xs resultado').

    Diferente de minuta_bloqueio (que cria minuta nova), processar_ordem_sisbajud
    navega para a teimosinha existente, filtra series nos ultimos 30 dias e
    processa ordens de bloqueio/desbloqueio conforme o tipo de fluxo detectado.

    Equivalente ao _sisbajud_processar_ordem em PEC/regras_execucao.py,
    acionado por observacao contendo 'xs resultado' ou 'resultado'.
    """
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_SISB, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[ORDEM_TEST] Teste isolado: processar_ordem_sisbajud (xs resultado)')
    LOGGER.info('[ORDEM_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None
    driver_sisb = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[ORDEM_TEST] Falha ao criar driver PJE')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[ORDEM_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[ORDEM_TEST] Navegando para %s', url)
            navegar_para_tela(driver, url=url)

        # Extrair dados do processo
        with etapa('extrair_dados'):
            from Fix.extracao import extrair_dados_processo
            dados_processo = extrair_dados_processo(driver)
            LOGGER.info('[ORDEM_TEST] Dados extraidos: %s', bool(dados_processo))

        # Salvar snapshot
        try:
            with open('dadosatuais.json', 'w', encoding='utf-8') as fh:
                json.dump(dados_processo or {}, fh, ensure_ascii=False, indent=2)
            LOGGER.info('[ORDEM_TEST] dadosatuais.json salvo')
        except Exception as e:
            LOGGER.warning('[ORDEM_TEST] Falha ao salvar dadosatuais.json: %s', e)

        # Iniciar driver SISBAJUD
        with etapa('iniciar_sisbajud'):
            from SISB.core import iniciar_sisbajud, processar_ordem_sisbajud
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
            if not driver_sisb:
                LOGGER.error('[ORDEM_TEST] Falha ao iniciar SISBAJUD')
                return

        # Executar processamento de ordens (equiv. _executar_sisbajud com processar_ordem_sisbajud)
        with etapa('processar_ordem'):
            LOGGER.info('[ORDEM_TEST] Chamando processar_ordem_sisbajud...')
            resultado = processar_ordem_sisbajud(driver_sisb, dados_processo=dados_processo,
                                                  driver_pje=driver, log=True, fechar_driver=False)
            LOGGER.info('[ORDEM_TEST] Resultado: %s', resultado)

        LOGGER.info('[ORDEM_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[ORDEM_TEST] Erro nao tratado')

    finally:
        LOGGER.info('[ORDEM_TEST] encerrando drivers')
        try:
            if driver_sisb is not None:
                driver_sisb.quit()
        except Exception:
            pass
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 6: PEC — fluxo pec_ord (Notificação Inicial, zordd, prazo=5)
# ============================================================

def teste_pec_ord(id_processo=None):
    """
    Teste isolado do wrapper pec_ord — Notificação Inicial:
        - pec_ord(driver) — cria comunicação com modelo zordd, prazo=5, sigilo=False
        - movimentar_inteligente(driver, 'Aguardando Prazo') — move o processo

    Equivalente ao _xs_ord em PEC/regras_execucao.py.
    """
    from atos.wrappers_pec import pec_ord
    from atos.movimentos_fluxo import movimentar_inteligente
    configurar_logging_debug()
    # PEC_ORD usa /peticao/... com default; com override usa /detalhe simples
    if id_processo:
        url, pid = _resolver(PROCESS_ID_PEC_ORD, id_processo)
    else:
        url = PROCESS_URL_PEC_ORD
        pid = PROCESS_ID_PEC_ORD

    LOGGER.info('=' * 60)
    LOGGER.info('[PEC_ORD_TEST] Teste isolado: pec_ord (Notificacao Inicial, zordd, prazo=5)')
    LOGGER.info('[PEC_ORD_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[PEC_ORD_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PEC_ORD_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_ORD_TEST] Navegando para %s', url)
            navegar_para_tela(driver, url=url)

        # ETAPA 1: pec_ord — Notificacao Inicial (zordd)
        with etapa('pec_ord'):
            LOGGER.info('[PEC_ORD_TEST] Executando pec_ord (modelo zordd, prazo=5, sigilo=False)...')
            ok = pec_ord(driver, debug=True)
            LOGGER.info('[PEC_ORD_TEST] pec_ord -> %s', 'OK' if ok else 'FALHA')

        # ETAPA 2: mov_int — mover para Aguardando Prazo
        with etapa('mov_int_aguardando_prazo'):
            LOGGER.info('[PEC_ORD_TEST] Movendo para Aguardando Prazo...')
            ok = movimentar_inteligente(driver, 'Aguardando Prazo')
            LOGGER.info('[PEC_ORD_TEST] movimentar_inteligente -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[PEC_ORD_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PEC_ORD_TEST] Erro nao tratado')

    finally:
        LOGGER.info('[PEC_ORD_TEST] encerrando driver')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 7: Anex Carta — juntada completa com clipboard
# ============================================================

def teste_anex_carta(id_processo=None):
    """
    Teste isolado do wrapper anex_carta — juntada de e-carta:
        - Usa conteudo do clipboard.txt para substituicao no editor
        - Modelo: xs carta | Tipo: Certidao | Desc: Rastreamentos e-Carta

    Fluxo completo: abre interface de anexacao → preenche campos →
    seleciona modelo → insere conteudo clipboard → salva
    """
    from PEC.anexos.anexos_wrappers import anex_carta
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_ANEX_CARTA, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[ANEX_CARTA_TEST] Teste isolado: anex_carta (juntada completa)')
    LOGGER.info('[ANEX_CARTA_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[ANEX_CARTA_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[ANEX_CARTA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[ANEX_CARTA_TEST] Navegando para %s', url)
            navegar_para_tela(driver, url=url)

        # Executar juntada completa
        with etapa('anex_carta'):
            LOGGER.info('[ANEX_CARTA_TEST] Executando anex_carta (modelo xs carta)...')
            ok = anex_carta(driver, debug=True)
            LOGGER.info('[ANEX_CARTA_TEST] anex_carta -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[ANEX_CARTA_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[ANEX_CARTA_TEST] Erro nao tratado')

    finally:
        LOGGER.info('[ANEX_CARTA_TEST] encerrando driver')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# TESTE 8: TRIAGEM — fluxo real via run_triagem (igual ao producao)
# ============================================================

def teste_triagem_peticao(id_processo=None):
    """
    Executa o fluxo de triagem direto no processo.
    Nao usa a fila da API -- navega direto para o processo e roda o pipeline.
    Uso: py f.py triagem [id_processo]
    """
    from bianca.triagem.service import triagem_peticao
    from bianca.triagem.acoes import (
        _aplicar_acao_pos_triagem,
        _determinar_acao_pos_triagem,
        _RE_BUCKET_B2,
        _RE_BUCKET_C,
        _RE_BUCKET_D,
    )
    from bianca.extracao import criar_comentario
    from bianca.selenium_utils import aguardar_renderizacao_nativa, esperar_elemento
    from selenium.webdriver.common.by import By

    configurar_logging_debug()
    logging.getLogger('bianca').setLevel(logging.DEBUG)

    url, pid = _resolver(PROBE_ID_PROCESSO, id_processo)
    id_processo = pid

    LOGGER.info('=' * 60)
    LOGGER.info('[TRIAGEM_TEST] Teste direto: id=%s', id_processo)
    LOGGER.info('[TRIAGEM_TEST] URL: %s', url)
    LOGGER.info('=' * 60)

    proc = {
        'numero': id_processo,
        'id_processo': id_processo,
        'tipo': 'ATORD',
        'digital': False,
        'tem_audiencia': True,
        'bucket': 'C',
    }

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[TRIAGEM_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[TRIAGEM_TEST] Falha no login')
                return

        with etapa('navegar'):
            driver.get(url)
            esperar_elemento(driver, 'pje-cabecalho-processo,pje-timeline',
                             by=By.CSS_SELECTOR, timeout=15)
            aguardar_renderizacao_nativa(driver, timeout=5)

        with etapa('triagem_peticao'):
            # DEBUG: interceptar texto_inicial antes da triagem
            from bianca.triagem.coleta import _coletar_textos_processo
            _coleta_debug = _coletar_textos_processo(driver)
            _texto_debug = _coleta_debug.get('texto_inicial', '')
            with open('triagem_debug_texto.txt', 'w', encoding='utf-8') as _f:
                _f.write(_texto_debug or '(vazio)')
            LOGGER.info('[TRIAGEM_TEST] texto_inicial: %d chars -> salvo em triagem_debug_texto.txt', len(_texto_debug or ''))
            triagem_txt = triagem_peticao(driver)
            proc['triagem'] = triagem_txt
            LOGGER.info('[TRIAGEM_TEST] triagem_txt:\n%s', triagem_txt)

        if triagem_txt:
            try:
                bucket, _ = _determinar_acao_pos_triagem(triagem_txt)
                if bucket == 'pre_bucket':
                    if _RE_BUCKET_B2.search(triagem_txt):
                        bucket = 'b2_incompetencia'
                    elif _RE_BUCKET_C.search(triagem_txt):
                        bucket = 'c_pedidos'
                    elif _RE_BUCKET_D.search(triagem_txt):
                        bucket = 'd_docs'
                    else:
                        bucket = 'b1_normal'
                if bucket == 'b2_incompetencia':
                    status_str = 'Incompetencia territorial'
                elif bucket == 'c_pedidos':
                    status_str = 'Pedidos nao liquidados'
                elif bucket == 'd_docs':
                    status_str = 'Falta de documentos'
                else:
                    status_str = 'Direto'
                observacao = 'BIANCA - TRIAGEM\nESTADO DE FLUXO: %s\n\n%s' % (status_str, triagem_txt)
                with etapa('criar_comentario'):
                    criar_comentario(driver, observacao)
            except Exception:
                LOGGER.exception('[TRIAGEM_TEST] Falha ao criar comentario')

        with etapa('aguardar_gigs'):
            aguardar_renderizacao_nativa(driver, 'pje-gigs-lista-atividades button', 'aparecer', 8)

        with etapa('acao_pos_triagem'):
            ok, status = _aplicar_acao_pos_triagem(driver, proc.get('numero'), proc, triagem_txt)
            LOGGER.info('[TRIAGEM_TEST] acao_pos_triagem -> ok=%s status=%r', ok, status)

        LOGGER.info('[TRIAGEM_TEST] concluido')

    except Exception:
        LOGGER.exception('[TRIAGEM_TEST] Erro nao tratado')

    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass



# ============================================================
# TESTE 10: TRIAGEM DEBUG — passo a passo manual da coleta
# ============================================================

def teste_triagem_debug(url_processo: str = None):
    """
    Debug passo a passo da coleta de texto da peticao inicial.
    url_processo: URL do processo (default: usa PROCESS_ID_TRIAGEM)
    Uso: py f.py tdbg [url_ou_id_processo]
    """
    import io as _io
    from bianca.api_client import PjeApiClient, session_from_driver
    from bianca.triagem.coleta import _extrair_id_processo_da_url, _norm
    configurar_logging_debug()

    if url_processo and url_processo.isdigit():
        url_alvo, _ = _resolver(url_processo)
    else:
        url_alvo = url_processo or PROCESS_URL_TRIAGEM

    # habilitar DEBUG em bianca para ver todos os logs
    logging.getLogger('bianca').setLevel(logging.DEBUG)

    LOGGER.info('=' * 60)
    LOGGER.info('[TDBG] DEBUG COLETA TRIAGEM - passo a passo')
    LOGGER.info('[TDBG] Processo: %s', url_alvo)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[TDBG] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[TDBG] Falha no login')
                return

        with etapa('navegar_processo'):
            navegar_para_tela(driver, url=url_alvo)

        # ── PASSO 1: montar cliente ──────────────────────────────
        with etapa('montar_cliente'):
            sessao, trt_host = session_from_driver(driver, grau=1)
            client = PjeApiClient(sessao, trt_host, grau=1)
            LOGGER.info('[TDBG] cliente montado -> host=%s', trt_host)

        id_processo = _extrair_id_processo_da_url(driver.current_url)
        LOGGER.info('[TDBG] id_processo=%s', id_processo)

        # ── PASSO 2: timeline ────────────────────────────────────
        with etapa('timeline'):
            timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
            LOGGER.info('[TDBG] timeline: %s items', len(timeline) if timeline else 0)

        # ── PASSO 3: localizar peticao inicial ───────────────────
        peticao = None
        for doc in (timeline or []):
            if not isinstance(doc, dict):
                continue
            tipo  = _norm(doc.get('tipo') or '')
            titulo = _norm(doc.get('titulo') or '')
            if 'peticao inicial' in tipo or 'peticao inicial' in titulo:
                peticao = doc
                break

        if not peticao:
            LOGGER.error('[TDBG] peticao inicial nao localizada na timeline')
            return

        id_doc = str(peticao.get('id') or peticao.get('idUnicoDocumento') or '')
        LOGGER.info('[TDBG] peticao inicial encontrada: id=%s titulo=%r', id_doc, peticao.get('titulo'))
        LOGGER.info('[TDBG] chaves do doc: %s', list(peticao.keys()))

        # ── PASSO 4: checar pdfplumber ───────────────────────────
        with etapa('check_pdfplumber'):
            try:
                import pdfplumber
                LOGGER.info('[TDBG] pdfplumber OK: %s', pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else 'instalado')
            except ImportError as e:
                LOGGER.error('[TDBG] pdfplumber NAO INSTALADO: %s', e)
                LOGGER.error('[TDBG] Instalar: py -m pip install pdfplumber')
                return

        # ── PASSO 5: baixar PDF do endpoint /conteudo ────────────
        with etapa('baixar_pdf'):
            url_pdf = client._url(
                f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo')
            LOGGER.info('[TDBG] GET %s', url_pdf)
            resp = client.sess.get(url_pdf, timeout=60)
            ctype   = resp.headers.get('Content-Type', '')
            magic   = resp.content[:8] if resp.content else b''
            is_pdf  = b'%PDF' in magic
            LOGGER.info('[TDBG] status=%s  ctype=%r  body=%s bytes  magic=%r  is_pdf=%s',
                        resp.status_code, ctype, len(resp.content), magic, is_pdf)

            if resp.status_code != 200:
                LOGGER.error('[TDBG] HTTP %s - abortando', resp.status_code)
                return
            if not is_pdf:
                LOGGER.error('[TDBG] Resposta nao e PDF (magic=%r) - primeiros 400 chars:\n%s',
                             magic, resp.text[:400])
                return

            pdf_bytes = resp.content

        # ── PASSO 6: extrair texto com pdfplumber ────────────────
        with etapa('pdfplumber_extract'):
            textos = []
            with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
                n_pag = len(pdf.pages)
                LOGGER.info('[TDBG] PDF aberto: %s paginas', n_pag)
                for i, pag in enumerate(pdf.pages):
                    t = pag.extract_text() or ''
                    LOGGER.info('[TDBG]   pag %s/%s: %s chars', i + 1, n_pag, len(t))
                    if t:
                        textos.append(t)

            texto_total = '\n'.join(textos).strip()
            media = len(texto_total) / n_pag if n_pag else 0
            LOGGER.info('[TDBG] texto nativo total: %s chars  media=%.0f chars/pag', len(texto_total), media)

            if texto_total:
                # salvar amostra
                with open('triagem_debug_texto.txt', 'w', encoding='utf-8') as fh:
                    fh.write(texto_total)
                LOGGER.info('[TDBG] texto salvo em triagem_debug_texto.txt')
            else:
                LOGGER.warning('[TDBG] pdfplumber extraiu 0 chars (PDF pode ser escaneado/imagem)')

        # ── PASSO 7: OCR fallback se necessario ──────────────────
        if not texto_total:
            with etapa('ocr_fallback'):
                try:
                    import fitz
                    LOGGER.info('[TDBG] PyMuPDF (fitz) disponivel: %s', fitz.version)
                except ImportError:
                    LOGGER.warning('[TDBG] PyMuPDF nao instalado - OCR impossivel')
                try:
                    import pytesseract
                    LOGGER.info('[TDBG] pytesseract disponivel')
                except ImportError:
                    LOGGER.warning('[TDBG] pytesseract nao instalado - OCR impossivel')

        LOGGER.info('[TDBG] DEBUG concluido.')

    except Exception:
        LOGGER.exception('[TDBG] Erro nao tratado')
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# MAIN — seleciona qual teste executar
# ============================================================

_JS_PROBE_DOCUMENTO = """

(async function() {
    var base = location.origin;
    var hdrs = { 'Accept': 'application/json', 'X-Grau-Instancia': '1' };
    var resultados = [];

    var endpoints = [
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + '?incluirAssinatura=true&incluirAnexos=true',
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + '?incluirAssinatura=false&incluirAnexos=false',
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + '/conteudo',
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/id/' + idDoc + '/conteudoHtml',
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documento/' + idDoc + '/conteudo',
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/' + idDoc + '/conteudo',
        base + '/pje-comum-api/api/processos/' + idProcesso + '/documentos/' + idDoc,
    ];

    for (var i = 0; i < endpoints.length; i++) {
        var url = endpoints[i];
        try {
            var r = await fetch(url, { credentials: 'include', headers: hdrs });
            var ctype = r.headers.get('Content-Type') || '';
            var txt = await r.text();
            var parsed = null;
            var keys = [];
            var campos_texto = {};
            try {
                parsed = JSON.parse(txt);
                keys = Object.keys(parsed);
                for (var k of ['conteudo', 'conteudoHtml', 'conteudoTexto', 'texto', 'html', 'previewModeloDocumento']) {
                    if (parsed[k]) campos_texto[k] = String(parsed[k]).length;
                }
            } catch(e) {}
            resultados.push({
                url: url, status: r.status, ctype: ctype,
                body_len: txt.length, keys: keys,
                campos_texto: campos_texto,
                preview: txt.slice(0, 400),
                is_pdf: txt.slice(0, 5) === '%PDF-'
            });
        } catch(e) {
            resultados.push({ url: url, erro: e.message });
        }
    }
    callback(resultados);
})();
"""


# ============================================================
# TESTE 9: PROBE DOCUMENTO — diagnóstico raw de endpoint API
# ============================================================

def teste_probe_documento(id_processo=None, id_documento=None):
    """
    Probe direto: usa execute_async_script (JS com cookies do browser) para
    bater em TODOS os endpoints possíveis do documento e mostrar status,
    campos JSON e preview do corpo. Util para diagnosticar mudancas na API.
    Uso: py f.py probe [id_processo] [id_documento]
    """
    configurar_logging_debug()
    pid_probe = str(id_processo or PROBE_ID_PROCESSO)
    doc_probe = str(id_documento or PROBE_ID_DOC)

    LOGGER.info('=' * 60)
    LOGGER.info('[PROBE_DOC] processo=%s  documento=%s', pid_probe, doc_probe)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[PROBE_DOC] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PROBE_DOC] Falha no login')
                return

        with etapa('navegar_processo'):
            url_probe, _ = _resolver(pid_probe)
            navegar_para_tela(driver, url=url_probe)

        with etapa('probe_endpoints'):
            driver.set_script_timeout(45)
            resultados = driver.execute_async_script(
                _JS_PROBE_DOCUMENTO, pid_probe, doc_probe)

        LOGGER.info('[PROBE_DOC] --- Resultados por endpoint ---')
        for r in (resultados or []):
            if r.get('erro'):
                LOGGER.warning('[PROBE_DOC] ERRO  %s  ->  %s', r['url'], r['erro'])
                continue
            status = r.get('status')
            keys   = r.get('keys') or []
            ctxt   = r.get('campos_texto') or {}
            marker = '✓' if status == 200 else '✗'
            LOGGER.info(
                '[PROBE_DOC] %s HTTP %s  body=%s bytes  ctype=%s  is_pdf=%s  keys=%s  campos_texto=%s\n'
                '           URL: %s\n'
                '           preview: %s',
                marker, status, r.get('body_len', 0),
                r.get('ctype', ''), r.get('is_pdf', False),
                keys[:10], ctxt,
                r['url'],
                r.get('preview', '')[:300],
            )

        # Salvar resultado completo
        with open('probe_documento.json', 'w', encoding='utf-8') as fh:
            json.dump(resultados, fh, ensure_ascii=False, indent=2)
        LOGGER.info('[PROBE_DOC] Resultado completo salvo em probe_documento.json')

    except Exception:
        LOGGER.exception('[PROBE_DOC] Erro nao tratado')
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


# ============================================================
# MAIN — seleciona qual teste executar
# ============================================================

if __name__ == '__main__':
    teste = sys.argv[1].lower() if len(sys.argv) > 1 else 'argos'
    # id_processo opcional como 2º argumento (ex: py f.py argos 7449746)
    id_p = sys.argv[2] if len(sys.argv) > 2 else None

    if teste in ('argos', '1'):
        teste_buscar_sequenciais(id_p)
    elif teste in ('sisb', 'sisbajud', 'minuta', '2'):
        teste_sisbajud_minuta(id_p)
    elif teste in ('pec', 'sigilo', '3'):
        teste_pec_ord(id_p)
    elif teste in ('pesquisa', 'ato_pesquisas', '4'):
        teste_ato_pesquisas(id_p)
    elif teste in ('ordem', 'resultado', '5'):
        teste_sisbajud_ordem(id_p)
    elif teste in ('pecord', '6'):
        teste_pec_ord(id_p)
    elif teste in ('anex', 'anex_carta', 'carta', 'juntada', '7'):
        teste_anex_carta(id_p)
    elif teste in ('triagem', 'bianca', '8'):
        teste_triagem_peticao(id_p)
    elif teste in ('probe', 'probe_doc', '9'):
        id_doc = sys.argv[3] if len(sys.argv) > 3 else None
        teste_probe_documento(id_p, id_doc)
    elif teste in ('tdbg', 'triagem_debug', '10'):
        url_arg = sys.argv[2] if len(sys.argv) > 2 else None
        teste_triagem_debug(url_arg)
    elif teste in ('dom', 'dom_lembrete', '11'):
        def _teste_dom_eletronico_1_proc(id_processo=None):
            """
            Teste SEM mocks do fluxo DOM por 1 processo específico:
            - cria driver
            - login
            - navega para /processo/{id}/detalhe
            - extrai tipo do processo via JS (ATOrd/ATSum/ACum)
            - chama diretamente bianca.dom_engine.callback_bucket2
            """
            from bianca import dom_engine as _dom_engine

            configurar_logging_debug()

            url, pid = _resolver(id_processo or '8296007', id_processo)
            LOGGER.info('=' * 60)
            LOGGER.info('[DOM_TEST] Teste real DOM ELETRONICO (1 processo)')
            LOGGER.info('[DOM_TEST] Processo URL: %s', url)
            LOGGER.info('[DOM_TEST] id=%s', pid)
            LOGGER.info('=' * 60)

            driver = None
            try:
                with etapa('criar_driver'):
                    driver = criar_driver_vt(headless=False)
                if not driver:
                    LOGGER.error('[DOM_TEST] Falha ao criar driver')
                    return

                with etapa('login'):
                    if not login_cpf(driver):
                        LOGGER.error('[DOM_TEST] Falha no login')
                        return

                with etapa('navegar_processo'):
                    LOGGER.info('[DOM_TEST] Navegando para %s', url)
                    navegar_para_tela(driver, url=url)

                # Extrair tipo do processo da aba de detalhes (equivalente ao run_dom_api)
                with etapa('extrair_tipo'):
                    tipo_processo = "ATOrd"
                    try:
                        tipo_js = driver.execute_script(
                            """
                            var cabecalho = document.querySelector('pje-cabecalho-processo');
                            if (cabecalho) {
                                var spansTipo = cabecalho.querySelectorAll(
                                    'pje-descricao-processo span.align-end.ng-star-inserted'
                                );
                                for (var i = 0; i < spansTipo.length; i++) {
                                    var texto = (spansTipo[i].innerText
                                        || spansTipo[i].textContent || '').trim();
                                    if (texto && (texto.includes('ATOrd')
                                        || texto.includes('ATSum')
                                        || texto.includes('ACum'))) {
                                        return texto;
                                    }
                                }
                            }
                            return '';
                            """
                        )
                        if tipo_js:
                            tipo_processo = tipo_js.strip()
                    except Exception as e:
                        LOGGER.warning('[DOM_TEST] Falha ao extrair tipo, usando ATOrd: %s', e)

                    LOGGER.info('[DOM_TEST] tipo_processo=%s', tipo_processo)

                # setar numero_processo_lista para logs do callback_bucket2
                driver._numero_processo_lista = pid  # type: ignore[attr-defined]

                with etapa('callback_bucket2'):
                    ok = _dom_engine.callback_bucket2(driver, tipo_processo=tipo_processo)
                    LOGGER.info('[DOM_TEST] callback_bucket2 -> %s', ok)

                LOGGER.info('[DOM_TEST] concluido')

            except Exception:
                LOGGER.exception('[DOM_TEST] Erro nao tratado')
            finally:
                try:
                    if driver is not None:
                        driver.quit()
                except Exception:
                    pass

        _teste_dom_eletronico_1_proc(id_p)
    elif teste in ('todos', 'all'):
        print('=== Executando todos os testes ===')
        print('\n--- TESTE 1: ARGOS ---')
        teste_buscar_sequenciais(id_p)
        print('\n--- TESTE 2: SISBAJUD MINUTA ---')
        teste_sisbajud_minuta(id_p)
        print('\n--- TESTE 3: PEC SIGILO ---')
        teste_pec_sigilo(id_p)
        print('\n--- TESTE 4: ATO PESQUISAS ---')
        teste_ato_pesquisas(id_p)
        print('\n--- TESTE 5: SISBAJUD ORDEM ---')
        teste_sisbajud_ordem(id_p)
        print('\n--- TESTE 6: PEC ORD ---')
        teste_pec_ord(id_p)
        print('\n--- TESTE 7: ANEX CARTA ---')
        teste_anex_carta(id_p)
        print('\n--- TESTE 8: TRIAGEM ---')
        teste_triagem_peticao(id_p)
        print('\n--- TESTE 11: DOM ELETRONICO lembrete (isola decisao) ---')
        teste_dom_lembrete_detection(id_p)
    else:
        print(f'Teste desconhecido: {teste}')
        print('Disponiveis: argos, sisb, pec, pesquisa, ordem, pecord, anex, juntada, triagem, probe, tdbg, dom, todos')
        print('Uso: py f.py <teste> [id_processo]')
