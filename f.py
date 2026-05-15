# ============================================================
# f.py -- Harness de teste isolado: Multi-testes
# Uso: py f.py [teste]
#   teste disponiveis: argos, sisb, pec, pesquisa, ordem, pecord, anex, todos
# ============================================================

import json
import logging
import time
import sys
from contextlib import contextmanager

from x import criar_driver_pc
from Fix.utils import login_cpf, navegar_para_tela

# ============================================================
# URLs de processos para testes
# ============================================================
PROCESS_URL_ARGOS = 'https://pje.trt2.jus.br/pjekz/processo/6191451/detalhe/peticao/461152313'
PROCESS_ID_ARGOS = '6191451'
PROCESS_URL_SISB  = 'https://pje.trt2.jus.br/pjekz/processo/4863758/detalhe'
PROCESS_URL_PEC      = 'https://pje.trt2.jus.br/pjekz/processo/6095583/detalhe'
PROCESS_URL_PEC_ORD  = 'https://pje.trt2.jus.br/pjekz/processo/5455795/detalhe/peticao/460955334'
PROCESS_URL_ANEX_CARTA = 'https://pje.trt2.jus.br/pjekz/processo/7258019/detalhe'

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

def teste_buscar_sequenciais():
    """Teste do fluxo completo Argos usando o entrypoint real de Mandado."""
    from Mandado.entrada_api import processar_mandado_detalhe

    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[ARGOS_TEST] Teste real: fluxo completo Argos')
    LOGGER.info('[ARGOS_TEST] Processo: %s (id=%s)', PROCESS_URL_ARGOS, PROCESS_ID_ARGOS)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[ARGOS_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[ARGOS_TEST] Falha no login')
                return

        with etapa('fluxo_argos_completo'):
            t0 = time.perf_counter()
            resultado = processar_mandado_detalhe(driver, id_processo=PROCESS_ID_ARGOS)
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

def teste_sisbajud_minuta():
    """Teste isolado da minuta de bloqueio SISBAJUD."""
    import re
    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[SISB_TEST] Teste isolado: minuta_bloqueio SISBAJUD')
    LOGGER.info('[SISB_TEST] Processo: %s', PROCESS_URL_SISB)
    LOGGER.info('=' * 60)

    driver = None
    driver_sisb = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[SISB_TEST] Falha ao criar driver PJE')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[SISB_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[SISB_TEST] Navegando para %s', PROCESS_URL_SISB)
            navegar_para_tela(driver, url=PROCESS_URL_SISB)

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

def teste_pec_sigilo():
    """
    Teste isolado do fluxo PEC para observacao 'xs sigilo':
        1. pec_sigilo(driver) — cria comunicacao sigilosa (modelo xdecsig)
        2. movimentar_inteligente(driver, 'Aguardando Prazo') — move o processo

    Equivalente ao _xs_sigilo em PEC/regras_execucao.py.
    """
    from atos.wrappers_pec import pec_sigilo
    from atos.movimentos_fluxo import movimentar_inteligente
    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[PEC_TEST] Teste isolado: fluxo xs sigilo (pec_sigilo + mov_int)')
    LOGGER.info('[PEC_TEST] Processo: %s', PROCESS_URL_PEC)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[PEC_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PEC_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_TEST] Navegando para %s', PROCESS_URL_PEC)
            navegar_para_tela(driver, url=PROCESS_URL_PEC)

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

def teste_ato_pesquisas():
    """
    Teste isolado do ato_pesquisas — fluxo judicial BACEN:
        - Verifica e clica 'Iniciar a execucao' se disponivel
        - Executa ato_judicial com modelo 'xsbacen', prazo=30, sigilo=True
        - Retorna (sucesso, sigilo_ativado)

    Equivalente ao chamado em Prazo/p2b_gateway.py e atos/judicial.py.
    """
    from atos.judicial import ato_pesquisas
    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[PESQUISA_TEST] Teste isolado: ato_pesquisas (BACEN)')
    LOGGER.info('[PESQUISA_TEST] Processo: %s', PROCESS_URL_PEC)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[PESQUISA_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PESQUISA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PESQUISA_TEST] Navegando para %s', PROCESS_URL_PEC)
            navegar_para_tela(driver, url=PROCESS_URL_PEC)

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

def teste_sisbajud_ordem():
    """
    Teste isolado do processamento de ordens SISBAJUD (fluxo 'xs resultado').

    Diferente de minuta_bloqueio (que cria minuta nova), processar_ordem_sisbajud
    navega para a teimosinha existente, filtra series nos ultimos 30 dias e
    processa ordens de bloqueio/desbloqueio conforme o tipo de fluxo detectado.

    Equivalente ao _sisbajud_processar_ordem em PEC/regras_execucao.py,
    acionado por observacao contendo 'xs resultado' ou 'resultado'.
    """
    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[ORDEM_TEST] Teste isolado: processar_ordem_sisbajud (xs resultado)')
    LOGGER.info('[ORDEM_TEST] Processo: %s', PROCESS_URL_SISB)
    LOGGER.info('=' * 60)

    driver = None
    driver_sisb = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[ORDEM_TEST] Falha ao criar driver PJE')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[ORDEM_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[ORDEM_TEST] Navegando para %s', PROCESS_URL_SISB)
            navegar_para_tela(driver, url=PROCESS_URL_SISB)

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

def teste_pec_ord():
    """
    Teste isolado do wrapper pec_ord — Notificação Inicial:
        - pec_ord(driver) — cria comunicação com modelo zordd, prazo=5, sigilo=False
        - movimentar_inteligente(driver, 'Aguardando Prazo') — move o processo

    Equivalente ao _xs_ord em PEC/regras_execucao.py.
    """
    from atos.wrappers_pec import pec_ord
    from atos.movimentos_fluxo import movimentar_inteligente
    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[PEC_ORD_TEST] Teste isolado: pec_ord (Notificacao Inicial, zordd, prazo=5)')
    LOGGER.info('[PEC_ORD_TEST] Processo: %s', PROCESS_URL_PEC_ORD)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[PEC_ORD_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[PEC_ORD_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_ORD_TEST] Navegando para %s', PROCESS_URL_PEC_ORD)
            navegar_para_tela(driver, url=PROCESS_URL_PEC_ORD)

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

def teste_anex_carta():
    """
    Teste isolado do wrapper anex_carta — juntada de e-carta:
        - Usa conteudo do clipboard.txt para substituicao no editor
        - Modelo: xs carta | Tipo: Certidao | Desc: Rastreamentos e-Carta

    Fluxo completo: abre interface de anexacao → preenche campos →
    seleciona modelo → insere conteudo clipboard → salva
    """
    from PEC.anexos.anexos_wrappers import anex_carta
    configurar_logging_debug()

    LOGGER.info('=' * 60)
    LOGGER.info('[ANEX_CARTA_TEST] Teste isolado: anex_carta (juntada completa)')
    LOGGER.info('[ANEX_CARTA_TEST] Processo: %s', PROCESS_URL_ANEX_CARTA)
    LOGGER.info('=' * 60)

    driver = None

    try:
        with etapa('criar_driver'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            LOGGER.error('[ANEX_CARTA_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not login_cpf(driver):
                LOGGER.error('[ANEX_CARTA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[ANEX_CARTA_TEST] Navegando para %s', PROCESS_URL_ANEX_CARTA)
            navegar_para_tela(driver, url=PROCESS_URL_ANEX_CARTA)

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
# MAIN — seleciona qual teste executar
# ============================================================

if __name__ == '__main__':
    teste = sys.argv[1].lower() if len(sys.argv) > 1 else 'argos'

    if teste in ('argos', '1'):
        teste_buscar_sequenciais()
    elif teste in ('sisb', 'sisbajud', 'minuta', '2'):
        teste_sisbajud_minuta()
    elif teste in ('pec', 'sigilo', '3'):
        teste_pec_sigilo()
    elif teste in ('pesquisa', 'ato_pesquisas', '4'):
        teste_ato_pesquisas()
    elif teste in ('ordem', 'resultado', '5'):
        teste_sisbajud_ordem()
    elif teste in ('pecord', '6'):
        teste_pec_ord()
    elif teste in ('anex', 'anex_carta', 'carta', '7'):
        teste_anex_carta()
    elif teste in ('todos', 'all'):
        print('=== Executando todos os testes ===')
        print('\n--- TESTE 1: ARGOS ---')
        teste_buscar_sequenciais()
        print('\n--- TESTE 2: SISBAJUD MINUTA ---')
        teste_sisbajud_minuta()
        print('\n--- TESTE 3: PEC SIGILO ---')
        teste_pec_sigilo()
        print('\n--- TESTE 4: ATO PESQUISAS ---')
        teste_ato_pesquisas()
        print('\n--- TESTE 5: SISBAJUD ORDEM ---')
        teste_sisbajud_ordem()
        print('\n--- TESTE 6: PEC ORD ---')
        teste_pec_ord()
        print('\n--- TESTE 7: ANEX CARTA ---')
        teste_anex_carta()
    else:
        print(f'Teste desconhecido: {teste}')
        print('Disponiveis: argos, sisb, pec, pesquisa, ordem, pecord, anex, todos')
