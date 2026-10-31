# f.py -- Harness de teste isolado: Multi-testes
# Uso: py f.py [teste] [id_processo]
#   testes disponiveis:
#     argos, sisb, pec, pesquisa, ordem, pecord, pecidpj, mddid, anex, triagem,
#     probe, tdbg, dom, bndt, p2b, excluiargos, sisbdir, carta_completa, aud, todos
#   Exemplos:
#     py f.py argos            → teste Argos no processo padrão (7508281)
#     py f.py argos 7449746    → teste Argos no processo 7449746
#     py f.py probe 7449746 465383360  → probe documento 465383360 do processo 7449746
#     py f.py pecidpj          → pec_idpj (Intimação defesa IDPJ)
#     py f.py mddid            → ação real de 'xs mddid' (pec_mddsent + pec_editalsent)
#     py f.py aud 1002072      → diagnostico isolado de _marcar_aud (artefatos em
#                                logs_execucao/aud_diag/)
#     py f.py aud 1002072-78.2026.5.02.0703 ATVARI 08:35  → CNJ/rito/hora fixos
# ============================================================
#
# ARQUITETURA: este harness usa exactamente os mesmos entrypoints que pw.py → x.py.
#   Bootstrap: pjeplay.iniciar(nativo=True) — MESMO motor de produção (Playwright)
#   Driver:    Fix.core.criar_driver_vt / criar_driver_pc
#   Finalizar: Fix.core.finalizar_driver
#   Login:     _logar_como_pw_visivel() — mesmo fluxo de x.py no modo visivel:
#              login_cpf -> login manual na mesma janela -> confirma OAuth
#   Navegação: driver.get(url) + espera.ate_js(driver, "document.readyState==='complete'", teto=15)
#   Espera:    Fix.espera — nunca time.sleep()
#   Log:       console + logs_execucao/f_<timestamp>.log (DEBUG nos módulos de negócio)
# ============================================================

import json
import logging
import os
import sys
from contextlib import contextmanager
import time

# ── Bootstrap Playwright (idêntico a pw.py) ──────────────────────────────────
# DEVE vir ANTES de qualquer import de Fix/*: pjeplay.iniciar() instala o
# backend Playwright e aplica os helpers nativos (auto-wait). Sem isto o
# harness não roda no mesmo motor de produção.
AQUI = os.path.dirname(os.path.abspath(__file__))
PLAY = os.path.join(AQUI, "play")
for _caminho in (AQUI, PLAY):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

import pjeplay  # noqa: E402

pjeplay.iniciar(raiz_projeto=AQUI, nativo=True)
os.chdir(AQUI)

# Entrypoints reais (mesmo que x.py usa)
from Fix.core import criar_driver_vt, criar_driver_pc, finalizar_driver  # noqa: E402
from Fix.utils import login_manual, login_cpf, navegar_para_tela  # noqa: E402
from Fix import espera  # noqa: E402
from Fix.diagnostico_runtime import handler_console_sem_pjeplus  # noqa: E402

# ============================================================
# URLs de processos para testes (valores padrão)
# ============================================================
_URL_BASE = 'https://pje.trt2.jus.br/pjekz/processo'


def _resolver(id_padrao, id_override=None):
    """Retorna (url, id_str) resolvendo id_override sobre id_padrao."""
    pid = str(id_override or id_padrao)
    return f'{_URL_BASE}/{pid}/detalhe', pid


PROCESS_ID_ARGOS    = '7508281'
PROCESS_ID_SISB     = '4863758'
PROCESS_ID_PEC      = '6095583'
PROCESS_ID_PEC_ORD  = '5455795'
PROCESS_ID_ANEX_CARTA = '7258019'
PROCESS_ID_TRIAGEM  = '8685584'
PROCESS_ID_BNDT     = '8685584'
PROBE_ID_PROCESSO   = '8685584'
PROBE_ID_DOC        = '461896095'

# URLs pré-computadas com defaults
PROCESS_URL_ARGOS,   _ = _resolver(PROCESS_ID_ARGOS)
PROCESS_URL_SISB,    _ = _resolver(PROCESS_ID_SISB)
PROCESS_URL_PEC,     _ = _resolver(PROCESS_ID_PEC)
PROCESS_URL_PEC_ORD, _ = _resolver(PROCESS_ID_PEC_ORD)
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
    """Logging profundo: console + arquivo, DEBUG nos módulos de negócio.

    Espelha o sink de arquivo de x.py (logs_execucao/) para que a falha possa
    ser rastreada linha a linha depois da execução.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_DestaquFormatter())
    # F8: nao reimprimir linhas da familia 'pjeplus' (handler proprio no Fix.diagnostico_runtime)
    handler_console_sem_pjeplus(handler)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not root.handlers:
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(_DestaquFormatter())

    # Sink de arquivo (um por execução do harness) — idempotente
    global _LOG_FILE_CONFIGURADO
    if not _LOG_FILE_CONFIGURADO:
        try:
            log_dir = os.path.join(AQUI, 'logs_execucao')
            os.makedirs(log_dir, exist_ok=True)
            marca = time.strftime('%Y%m%d_%H%M%S')
            arq = os.path.join(log_dir, f'f_{marca}.log')
            fh = logging.FileHandler(arq, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(
                '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
            root.addHandler(fh)
            _LOG_FILE_CONFIGURADO = True
            LOGGER.info('[LOG] arquivo de log: %s', arq)
        except Exception as e:
            LOGGER.warning('[LOG] nao foi possivel criar arquivo de log: %s', e)

    # Debug nos módulos do projeto
    for nome in ('Fix', 'PEC', 'SISB', 'atos', 'Mandado', 'Prazo', 'bianca', 'core'):
        logging.getLogger(nome).setLevel(logging.DEBUG)

    # Silenciar módulos ruidosos (Playwright, urllib3, pdfminer)
    for nome in (
        'urllib3', 'urllib3.connectionpool', 'requests',
        'playwright', 'asyncio', 'pdfminer', 'pypdf', 'fitz',
    ):
        logging.getLogger(nome).setLevel(logging.WARNING)
        
    # Ativar o profiler global para testes
    _ativar_profiler_tempo_global()


LOGGER = logging.getLogger('f')
_LOG_FILE_CONFIGURADO = False

_PROFILER_ATIVO = False
_PROFILE_CALLS = {}

def _profiler_tracer(frame, event, arg):
    """Tracer global via sys.setprofile para cronometrar todas as funções dos módulos do PJePlus."""
    if event == 'call':
        module = frame.f_globals.get('__name__') or ''
        # Monitora apenas módulos do próprio projeto, ignorando internas e terceiros
        if module and (module.startswith(('atos.', 'Fix.', 'PEC.', 'Mandado.', 'Prazo.', 'bianca.')) or module == 'core'):
            _PROFILE_CALLS[frame] = time.perf_counter()
    elif event == 'return' or event == 'exception':
        if frame in _PROFILE_CALLS:
            t0 = _PROFILE_CALLS.pop(frame)
            tf = time.perf_counter() - t0
            # Evitar poluição: só loga funções que demoram mais de 100ms
            if tf >= 0.1:
                module = frame.f_globals.get('__name__', '')
                func = frame.f_code.co_name
                if not func.startswith('<'):
                    LOGGER.debug(f"[PROFILER GLOBAL] {module}.{func} levou {tf:.3f}s")
    return _profiler_tracer

def _ativar_profiler_tempo_global():
    """Ativa o rastreador global do Python para cronometrar a execução de todas as funções."""
    global _PROFILER_ATIVO
    if _PROFILER_ATIVO: return
    _PROFILER_ATIVO = True
    sys.setprofile(_profiler_tracer)
    LOGGER.info("[PROFILER GLOBAL] sys.setprofile ativado! Monitorando lentidão em todas as chamadas.")


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


def _logar_como_pw_visivel(driver) -> bool:
    """Login identico ao de x.py (o que pw.py usa), com reuso de cookies.

    Ordem:
      1. verificar_e_aplicar_cookies(driver) — restaura a sessao salva da
         execucao anterior. Se valida, nao ha login nenhum a fazer.
      2. login_cpf(driver)                   — CPF salvo
      3. se falhar, login manual na MESMA janela (browser fica aberto)
      4. aguarda o handshake OAuth gravar o access_token

    O passo 1 precisa vir PRIMEIRO e por fora do login_cpf: o driver aqui
    acabou de ser criado, esta numa pagina em branco, entao
    sessao_oauth_completa() e False e o login_cpf apagaria os cookies e iria
    para o formulario. E o mesmo motivo pelo qual x.py chama
    verificar_e_aplicar_cookies antes do login_cpf no modo headless.

    Retorna True se a sessao ficou ativa. O driver nao e recriado em nenhum
    passo — e o mesmo do inicio ao fim.
    """
    from Fix.utils import (
        sessao_oauth_completa,
        verificar_e_aplicar_cookies,
        salvar_cookies_sessao,
        SALVAR_COOKIES_AUTOMATICO,
    )

    def aguardar_login_manual(timeout=900):
        LOGGER.warning('[LOGIN] Login automatico falhou. Browser mantido ABERTO — '
                       'conclua o login manualmente na janela do navegador.')
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                driver.current_url
            except Exception:
                LOGGER.error('[LOGIN] Browser indisponivel durante espera do login manual.')
                return False
            if sessao_oauth_completa(driver):
                LOGGER.info('[LOGIN] Login manual detectado (%.0fs).', time.time() - inicio)
                _salvar_sessao(driver, 'login_manual_pos_falha')
                return True
            espera.pausa(driver, 2)
        LOGGER.error('[LOGIN] Timeout (%ds) aguardando login manual.', timeout)
        return False

    def aguardar_sessao_ativa(timeout=60):
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                if sessao_oauth_completa(driver):
                    LOGGER.info('[LOGIN] Sessao OAuth completa confirmada (%.0fs).',
                                time.time() - inicio)
                    return True
            except Exception:
                LOGGER.error('[LOGIN] Browser indisponivel ao confirmar sessao.')
                return False
            espera.pausa(driver, 2)
        LOGGER.error('[LOGIN] access_token nao apareceu em %ds.', timeout)
        return False

    def _salvar_sessao(driver, motivo):
        if not SALVAR_COOKIES_AUTOMATICO:
            return
        try:
            salvar_cookies_sessao(driver, info_extra=motivo)
        except Exception as e:
            LOGGER.debug('[LOGIN] Nao foi possivel salvar cookies: %s', e)

    # 1) Sessao salva da execucao anterior
    t0 = time.perf_counter()
    if verificar_e_aplicar_cookies(driver):
        LOGGER.info('[LOGIN] Sessao restaurada via cookies em %.2fs — sem login.',
                    time.perf_counter() - t0)
        return True
    LOGGER.info('[LOGIN] Cookies ausentes/expirados (%.2fs) — indo para login_cpf.',
                time.perf_counter() - t0)

    # 2) Login automatico por CPF
    try:
        if login_cpf(driver):
            if aguardar_sessao_ativa():
                _salvar_sessao(driver, 'login_cpf')
                return True
            LOGGER.error('[LOGIN] Sessao OAuth nao completou apos login_cpf')
            return aguardar_login_manual()
        LOGGER.error('[LOGIN] login_cpf nao concluiu')
        return aguardar_login_manual()
    except Exception as e:
        LOGGER.error('[LOGIN] %s: %s', type(e).__name__, e)
        return False


def _navegar(driver, url: str):
    """Navega para URL e aguarda DOM pronto — equivale ao driver.get + espera de x.py."""
    driver.get(url)
    try:
        espera.ate_js(driver, "document.readyState === 'complete'", teto=15)
    except Exception:
        pass


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
            if not _logar_como_pw_visivel(driver):
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
        if driver is not None:
            try:
                finalizar_driver(driver)
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[SISB_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[SISB_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('extrair_dados'):
            from Fix.extracao import extrair_dados_processo
            dados_processo = extrair_dados_processo(driver)
            LOGGER.info('[SISB_TEST] Dados extraidos: %s', bool(dados_processo))

        try:
            with open('dadosatuais.json', 'w', encoding='utf-8') as fh:
                json.dump(dados_processo or {}, fh, ensure_ascii=False, indent=2)
            LOGGER.info('[SISB_TEST] dadosatuais.json salvo')
        except Exception as e:
            LOGGER.warning('[SISB_TEST] Falha ao salvar dadosatuais.json: %s', e)

        with etapa('iniciar_sisbajud'):
            from SISB.core import iniciar_sisbajud, minuta_bloqueio, minuta_bloqueio_60
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
            if not driver_sisb:
                LOGGER.error('[SISB_TEST] Falha ao iniciar SISBAJUD')
                return

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
        for d in (driver_sisb, driver):
            if d is not None:
                try:
                    finalizar_driver(d)
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[PEC_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('pec_sigilo'):
            LOGGER.info('[PEC_TEST] Executando pec_sigilo (modelo xdecsig, sigilo=True, prazo=30)...')
            ok = pec_sigilo(driver, debug=True)
            LOGGER.info('[PEC_TEST] pec_sigilo -> %s', 'OK' if ok else 'FALHA')

        with etapa('mov_int_aguardando_prazo'):
            LOGGER.info('[PEC_TEST] Movendo para Aguardando Prazo...')
            ok = movimentar_inteligente(driver, 'Aguardando Prazo')
            LOGGER.info('[PEC_TEST] movimentar_inteligente -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[PEC_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PEC_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[PEC_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 4: ato_pesquisas — fluxo BACEN (pesquisas para execucao)
# ============================================================

def teste_ato_pesquisas(id_processo=None):
    """
    Teste isolado do ato_pesquisas — fluxo judicial BACEN:
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[PESQUISA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PESQUISA_TEST] Navegando para %s', url)
            _navegar(driver, url)

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
            LOGGER.info('[PESQUISA_TEST] ato_pesquisas -> sucesso=%s sigilo_ativado=%s',
                        sucesso, sigilo_ativado)

        LOGGER.info('[PESQUISA_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PESQUISA_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[PESQUISA_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[ORDEM_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[ORDEM_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('extrair_dados'):
            from Fix.extracao import extrair_dados_processo
            dados_processo = extrair_dados_processo(driver)
            LOGGER.info('[ORDEM_TEST] Dados extraidos: %s', bool(dados_processo))

        try:
            with open('dadosatuais.json', 'w', encoding='utf-8') as fh:
                json.dump(dados_processo or {}, fh, ensure_ascii=False, indent=2)
            LOGGER.info('[ORDEM_TEST] dadosatuais.json salvo')
        except Exception as e:
            LOGGER.warning('[ORDEM_TEST] Falha ao salvar dadosatuais.json: %s', e)

        with etapa('iniciar_sisbajud'):
            from SISB.core import iniciar_sisbajud, processar_ordem_sisbajud
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
            if not driver_sisb:
                LOGGER.error('[ORDEM_TEST] Falha ao iniciar SISBAJUD')
                return

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
        for d in (driver_sisb, driver):
            if d is not None:
                try:
                    finalizar_driver(d)
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

    url, pid = _resolver(PROCESS_ID_PEC_ORD, id_processo)

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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[PEC_ORD_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_ORD_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('pec_ord'):
            LOGGER.info('[PEC_ORD_TEST] Executando pec_ord (modelo zordd, prazo=5, sigilo=False)...')
            ok = pec_ord(driver, debug=True)
            LOGGER.info('[PEC_ORD_TEST] pec_ord -> %s', 'OK' if ok else 'FALHA')

        with etapa('mov_int_aguardando_prazo'):
            LOGGER.info('[PEC_ORD_TEST] Movendo para Aguardando Prazo...')
            ok = movimentar_inteligente(driver, 'Aguardando Prazo')
            LOGGER.info('[PEC_ORD_TEST] movimentar_inteligente -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[PEC_ORD_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PEC_ORD_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[PEC_ORD_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 6b: PEC — pec_idpj (Intimação defesa IDPJ, xidpj c, prazo=17)
# ============================================================

def teste_pec_idpj(id_processo=None):
    """
    Teste isolado do wrapper pec_idpj — Intimação para manifestação sobre IDPJ:
        - pec_idpj(driver) — modelo xidpj c, prazo=17, destinatarios=informado decisao
        - movimentar_inteligente(driver, 'Aguardando Prazo') — move o processo

    Chama a função real de atos.wrappers_pec (sem lógica própria).
    """
    from atos.wrappers_pec import pec_idpj
    from atos.movimentos_fluxo import movimentar_inteligente
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_PEC, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[PEC_IDPJ_TEST] Teste isolado: pec_idpj (xidpj c, prazo=17)')
    LOGGER.info('[PEC_IDPJ_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[PEC_IDPJ_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[PEC_IDPJ_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_IDPJ_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('pec_idpj'):
            LOGGER.info('[PEC_IDPJ_TEST] Executando pec_idpj (modelo xidpj c, prazo=17)...')
            ok = pec_idpj(driver, debug=True)
            LOGGER.info('[PEC_IDPJ_TEST] pec_idpj -> %s', 'OK' if ok else 'FALHA')

        with etapa('mov_int_aguardando_prazo'):
            LOGGER.info('[PEC_IDPJ_TEST] Movendo para Aguardando Prazo...')
            ok = movimentar_inteligente(driver, 'Aguardando Prazo')
            LOGGER.info('[PEC_IDPJ_TEST] movimentar_inteligente -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[PEC_IDPJ_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PEC_IDPJ_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[PEC_IDPJ_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 6c: PEC — xs mddid (pec_mddsent + pec_editalsent)
# ============================================================

class _AtvMinima:
    """Atividade mínima compatível com a assinatura (driver, atv) do registry PEC."""
    def __init__(self, numero_processo='', observacao='xs mddid'):
        self.numero_processo = numero_processo
        self.observacao = observacao
        self.status = ''
        self.data_prazo = ''
        self.tipo_gigs = ''
        self.id_processo = None


def teste_mddid(id_processo=None):
    """
    Teste isolado da ação real da observação 'xs mddid':
        PEC.regras_execucao._mddid(driver, atv)
        → pec_mddsent(driver) + barreira aguardar_renderizacao_nativa + pec_editalsent(driver)

    Chama a MESMA função registrada no RuleRegistry (sem lógica própria).
    """
    from PEC.regras_execucao import _mddid
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_PEC, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[MDDID_TEST] Teste isolado: xs mddid (pec_mddsent + pec_editalsent)')
    LOGGER.info('[MDDID_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[MDDID_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[MDDID_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[MDDID_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('mddid'):
            atv = _AtvMinima(numero_processo=pid, observacao='xs mddid')
            LOGGER.info('[MDDID_TEST] Executando _mddid (pec_mddsent + pec_editalsent)...')
            ok = _mddid(driver, atv)
            LOGGER.info('[MDDID_TEST] _mddid -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[MDDID_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[MDDID_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[MDDID_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[ANEX_CARTA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[ANEX_CARTA_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('anex_carta'):
            LOGGER.info('[ANEX_CARTA_TEST] Executando anex_carta (modelo xs carta)...')
            ok = anex_carta(driver, debug=True)
            LOGGER.info('[ANEX_CARTA_TEST] anex_carta -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[ANEX_CARTA_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[ANEX_CARTA_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[ANEX_CARTA_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
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
    from Fix.extracao import criar_comentario

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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[TRIAGEM_TEST] Falha no login')
                return

        with etapa('navegar'):
            _navegar(driver, url)
            try:
                espera.ate_aparecer(driver, 'pje-cabecalho-processo,pje-timeline', teto=15)
            except Exception:
                pass

        with etapa('triagem_peticao'):
            from bianca.triagem.coleta import _coletar_textos_processo
            _coleta_debug = _coletar_textos_processo(driver)

            cnj_coletado = _coleta_debug.get('capa_dados', {}).get('numero_processo')
            if cnj_coletado:
                proc['numero'] = cnj_coletado
                LOGGER.info('[TRIAGEM_TEST] CNJ atualizado via coleta: %s', proc['numero'])

            juizo_digital = _coleta_debug.get('capa_dados', {}).get('juizo_digital')
            if juizo_digital is not None:
                proc['digital'] = juizo_digital
                proc['tem_100'] = juizo_digital
                LOGGER.info('[TRIAGEM_TEST] juizo_digital atualizado via coleta: %s', juizo_digital)

            rito_declarado = _coleta_debug.get('capa_dados', {}).get('rito_declarado', '')
            if rito_declarado:
                if 'SUMARÍSSIMO' in rito_declarado.upper() or 'SUMARISSIMO' in rito_declarado.upper():
                    proc['tipo'] = 'ATSUM'
                else:
                    proc['tipo'] = 'ATORD'
                LOGGER.info('[TRIAGEM_TEST] tipo atualizado via coleta: %s (%s)',
                            proc['tipo'], rito_declarado)

            _texto_debug = _coleta_debug.get('texto_inicial', '')
            with open('triagem_debug_texto.txt', 'w', encoding='utf-8') as _f:
                _f.write(_texto_debug or '(vazio)')
            LOGGER.info('[TRIAGEM_TEST] texto_inicial: %d chars -> salvo em triagem_debug_texto.txt',
                        len(_texto_debug or ''))
            triagem_txt = triagem_peticao(driver)
            proc['triagem'] = triagem_txt
            LOGGER.info('[TRIAGEM_TEST] triagem_txt:\n%s', triagem_txt)

        if triagem_txt:
            if "Juízo 100% digital: com pedido" in triagem_txt or "Juizo 100% digital: com pedido" in triagem_txt:
                proc['digital'] = True

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
                    from bianca.triagem.acoes import _tem_audiencia_marcada
                    tem_aud = _tem_audiencia_marcada(driver, proc)
                    tem_100 = bool(proc.get('digital', proc.get('tem_100', False)))

                    if tem_aud:
                        proc["bucket"] = "C"
                        status_str = "Direto - aud marcada / citado?"
                    else:
                        proc["bucket"] = "A"
                        status_str = ("100% digital - marcado e despachado?"
                                      if tem_100 else "Sem aud - marcado e despachado?")

                observacao = 'BIANCA - TRIAGEM\nESTADO DE FLUXO: %s\n\n%s' % (status_str, triagem_txt)
                with etapa('criar_comentario'):
                    criar_comentario(driver, observacao)
            except Exception:
                LOGGER.exception('[TRIAGEM_TEST] Falha ao criar comentario')

        with etapa('aguardar_gigs'):
            try:
                espera.ate_aparecer(driver, 'pje-gigs-lista-atividades button', teto=8)
            except Exception:
                pass

        with etapa('acao_pos_triagem'):
            ok, status = _aplicar_acao_pos_triagem(driver, proc.get('numero'), proc, triagem_txt)
            LOGGER.info('[TRIAGEM_TEST] acao_pos_triagem -> ok=%s status=%r', ok, status)

        LOGGER.info('[TRIAGEM_TEST] concluido')

    except Exception:
        LOGGER.exception('[TRIAGEM_TEST] Erro nao tratado')
    finally:
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 9: PROBE DOCUMENTO — diagnóstico raw de endpoint API
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
        base + '/pje-comum-api/api/processos/id/' + idProcesso + '/documentos/' + idDoc + '/conteudo',
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
    return resultados;
})();
"""


def teste_probe_documento(id_processo=None, id_documento=None):
    """
    Probe direto: usa evaluate (JS com cookies do browser) para bater em todos
    os endpoints possiveis do documento e mostrar status, campos JSON e preview.
    Util para diagnosticar mudancas na API.
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[PROBE_DOC] Falha no login')
                return

        with etapa('navegar_processo'):
            url_probe, _ = _resolver(pid_probe)
            _navegar(driver, url_probe)

        with etapa('probe_endpoints'):
            # Injeta as variaveis JS no escopo antes de avaliar o script
            js_com_vars = (
                f'var idProcesso = {json.dumps(pid_probe)};\n'
                f'var idDoc = {json.dumps(doc_probe)};\n'
                + _JS_PROBE_DOCUMENTO
            )
            # Playwright: page.evaluate() para scripts async que retornam Promise
            page = getattr(driver, 'page', None)
            if page is not None:
                resultados = page.evaluate(js_com_vars)
            else:
                # fallback: driver com interface evaluate direto
                resultados = driver.evaluate(js_com_vars)

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

        with open('probe_documento.json', 'w', encoding='utf-8') as fh:
            json.dump(resultados, fh, ensure_ascii=False, indent=2)
        LOGGER.info('[PROBE_DOC] Resultado completo salvo em probe_documento.json')

    except Exception:
        LOGGER.exception('[PROBE_DOC] Erro nao tratado')
    finally:
        if driver is not None:
            try:
                finalizar_driver(driver)
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
    from api.variaveis_client import PjeApiClient, session_from_driver
    from bianca.triagem.coleta import _extrair_id_processo_da_url, _norm
    configurar_logging_debug()

    if url_processo and url_processo.isdigit():
        url_alvo, _ = _resolver(url_processo)
    else:
        url_alvo = url_processo or PROCESS_URL_TRIAGEM

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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[TDBG] Falha no login')
                return

        with etapa('navegar_processo'):
            _navegar(driver, url_alvo)

        with etapa('montar_cliente'):
            sessao, trt_host = session_from_driver(driver, grau=1)
            client = PjeApiClient(sessao, trt_host, grau=1)
            LOGGER.info('[TDBG] cliente montado -> host=%s', trt_host)

        id_processo = _extrair_id_processo_da_url(driver.current_url)
        LOGGER.info('[TDBG] id_processo=%s', id_processo)

        with etapa('timeline'):
            timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
            LOGGER.info('[TDBG] timeline: %s items', len(timeline) if timeline else 0)

        peticao = None
        for doc in (timeline or []):
            if not isinstance(doc, dict):
                continue
            tipo   = _norm(doc.get('tipo') or '')
            titulo = _norm(doc.get('titulo') or '')
            if 'peticao inicial' in tipo or 'peticao inicial' in titulo:
                peticao = doc
                break

        if not peticao:
            LOGGER.error('[TDBG] peticao inicial nao localizada na timeline')
            return

        id_doc = str(peticao.get('id') or peticao.get('idUnicoDocumento') or '')
        LOGGER.info('[TDBG] peticao inicial encontrada: id=%s titulo=%r',
                    id_doc, peticao.get('titulo'))
        LOGGER.info('[TDBG] chaves do doc: %s', list(peticao.keys()))

        with etapa('check_pdfplumber'):
            try:
                import pdfplumber
                LOGGER.info('[TDBG] pdfplumber OK: %s',
                            pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else 'instalado')
            except ImportError as e:
                LOGGER.error('[TDBG] pdfplumber NAO INSTALADO: %s', e)
                LOGGER.error('[TDBG] Instalar: py -m pip install pdfplumber')
                return

        with etapa('baixar_pdf'):
            url_pdf = client._url(
                f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo')
            LOGGER.info('[TDBG] GET %s', url_pdf)
            resp = client.sess.get(url_pdf, timeout=60)
            ctype  = resp.headers.get('Content-Type', '')
            magic  = resp.content[:8] if resp.content else b''
            is_pdf = b'%PDF' in magic
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
            LOGGER.info('[TDBG] texto nativo total: %s chars  media=%.0f chars/pag',
                        len(texto_total), media)

            if texto_total:
                with open('triagem_debug_texto.txt', 'w', encoding='utf-8') as fh:
                    fh.write(texto_total)
                LOGGER.info('[TDBG] texto salvo em triagem_debug_texto.txt')
            else:
                LOGGER.warning('[TDBG] pdfplumber extraiu 0 chars (PDF pode ser escaneado/imagem)')

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
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 11: DOM — lembrete (callback_bucket2 isolado)
# ============================================================

def _teste_dom_eletronico_1_proc(id_processo=None):
    """
    Teste SEM mocks do fluxo DOM por 1 processo especifico:
    - cria driver, login, navega para /processo/{id}/detalhe
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
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[DOM_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[DOM_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('extrair_tipo'):
            tipo_processo = "ATOrd"
            try:
                # Playwright: page.evaluate() para JS síncrono
                _js_tipo = """
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
                tipo_js = espera.ate_js(driver, _js_tipo, teto=5)
                if tipo_js:
                    tipo_processo = str(tipo_js).strip()
            except Exception as e:
                LOGGER.warning('[DOM_TEST] Falha ao extrair tipo, usando ATOrd: %s', e)

            LOGGER.info('[DOM_TEST] tipo_processo=%s', tipo_processo)

        driver._numero_processo_lista = pid  # type: ignore[attr-defined]

        with etapa('callback_bucket2'):
            ok = _dom_engine.callback_bucket2(driver, tipo_processo=tipo_processo)
            LOGGER.info('[DOM_TEST] callback_bucket2 -> %s', ok)

        LOGGER.info('[DOM_TEST] concluido')

    except Exception:
        LOGGER.exception('[DOM_TEST] Erro nao tratado')
    finally:
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 11b: DOM API + COMENTARIO + LEMBRETE (sem GIGS)
# ============================================================
def _teste_dom_api_comentario_lembrete(id_processo=None):
    """Testa SO O COMECO do fluxo DOM + publicacao em comentario + lembrete.

    Executa apenas a parte de API do callback_bucket2 (sub-caso 2b), sem PEC,
    sem chips, sem GIGS:

        1. _checar_empresas_e_ids_api  -> filtro DOM + PJDP (via procuradoria)
                                          + idUnicoDocumento de cada notificacao
        2. criar_comentario            -> observacao DOM
        3. criar_lembrete_posit        -> titulo "DomElet" + empresas/ids

    Serve para validar a refatoracao do lembrete sem rodar o fluxo inteiro.

    Uso: py f.py dom_api [id_processo]
    """
    from bianca import dom_engine as _dom_engine
    from Fix.extracao import criar_comentario, criar_lembrete_posit

    configurar_logging_debug()

    url, pid = _resolver(id_processo or '8296007', id_processo)
    LOGGER.info('=' * 60)
    LOGGER.info('[DOM_API] Teste API + comentario + lembrete (sem GIGS, sem PEC)')
    LOGGER.info('[DOM_API] Processo URL: %s', url)
    LOGGER.info('[DOM_API] id=%s', pid)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[DOM_API] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[DOM_API] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[DOM_API] Navegando para %s', url)
            _navegar(driver, url)

        driver._numero_processo_lista = pid  # type: ignore[attr-defined]

        # --- 1. SO AS CHAMADAS DE API ------------------------------------
        with etapa('api_filtro_dom'):
            LOGGER.info('[DOM_API] Chamando _checar_empresas_e_ids_api (DOM + PJDP)...')
            destinatarios = _dom_engine._checar_empresas_e_ids_api(pid, driver)
            # A PJDP ja foi descartada dentro do filtro; os nomes ficam na
            # propria lista para marcar o comentario.
            pjdp = list(getattr(destinatarios, 'pjdp_detectado', []) or [])
            LOGGER.info('[DOM_API] %d empresa(s) no filtro: %s',
                        len(destinatarios),
                        ', '.join(
                            f"{d.get('empresa')} ({d.get('id_unico_documento')})"
                            for d in destinatarios
                        ) or '-')
            for d in destinatarios:
                LOGGER.info('[DOM_API]   empresa=%s | id_notif=%s | id_documento=%s',
                            d.get('empresa'),
                            d.get('id_unico_documento'),
                            d.get('id_documento'))
            LOGGER.info('[DOM_API] PJDP detectado (eliminado do fluxo): %s',
                        ', '.join(sorted(pjdp)) or '-')

        # --- 2. COMENTARIO -------------------------------------------------
        with etapa('criar_comentario'):
            # Comentario e' apenas a marca "DOM". Quando ha PJDP no polo
            # passivo, marca "DOM com PJDP detectado" — independente de
            # haver lembrete para outras partes ou nao.
            observacao_dom = 'DOM com PJDP detectado' if pjdp else 'DOM'
            LOGGER.info('[DOM_API] Comentario: %s', observacao_dom)
            ok_coment = criar_comentario(driver, observacao_dom, log=True)
            LOGGER.info('[DOM_API] criar_comentario -> %s', ok_coment)

        if not destinatarios:
            LOGGER.warning('[DOM_API] Nenhuma empresa no filtro - sem lembrete')
            LOGGER.info('=' * 60)
            LOGGER.info('[DOM_API] RESUMO: comentario=%s lembrete=(nao criado)', ok_coment)
            LOGGER.info('=' * 60)
            return

        # --- 3. LEMBRETE ---------------------------------------------------
        with etapa('criar_lembrete'):
            # O campo de conteudo do lembrete nao comporta paragrafacao (nem
            # quebra de linha), entao tudo vai numa linha so, separado por " - ".
            titulo_dom = 'DomElet'
            conteudo_dom = _dom_engine._montar_conteudo_lembrete_dom(destinatarios) if hasattr(_dom_engine, '_montar_conteudo_lembrete_dom') else ('Renovado por correio para ' + ', '.join(
                f"({d.get('empresa')} - {d.get('id_unico_documento')})"
                for d in destinatarios
            ))
            LOGGER.info('[DOM_API] Lembrete titulo=%r', titulo_dom)
            LOGGER.info('[DOM_API] Lembrete conteudo=%r', conteudo_dom)
            ok_lembrete = criar_lembrete_posit(
                driver, titulo_dom, conteudo_dom, debug=True
            )
            LOGGER.info('[DOM_API] criar_lembrete_posit -> %s', ok_lembrete)

        LOGGER.info('=' * 60)
        LOGGER.info('[DOM_API] RESUMO: comentario=%s lembrete=%s',
                    ok_coment, ok_lembrete)
        LOGGER.info('=' * 60)

    except Exception:
        LOGGER.exception('[DOM_API] Erro nao tratado')
    finally:
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 12: BNDT — exclusão (bndt com inclusao=False)
# ============================================================

def teste_bndt_exclusao(id_processo=None):
    """
    Teste isolado da funcao bndt (exclusao) de Fix/extracao.
    Navega para o /detalhe do processo e executa bndt(driver, inclusao=False).
    Uso: py f.py bndt [id_processo]
    """
    from Fix.extracao import bndt

    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_BNDT, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[BNDT_TEST] Teste isolado: bndt exclusao')
    LOGGER.info('[BNDT_TEST] Processo: %s (id=%s)', url, pid)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[BNDT_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[BNDT_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[BNDT_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('bndt_exclusao'):
            LOGGER.info('[BNDT_TEST] Executando bndt(driver, inclusao=False)...')
            t0 = time.perf_counter()
            resultado = bndt(driver, inclusao=False)
            LOGGER.info('[BNDT_TEST] bndt -> %r (%.2fs)', resultado, time.perf_counter() - t0)

        if resultado:
            LOGGER.info('[BNDT_TEST] concluido com sucesso')
        else:
            LOGGER.error('[BNDT_TEST] bndt retornou falha')

    except Exception:
        LOGGER.exception('[BNDT_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[BNDT_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 13: P2B - Leitura de Decisao e Indicacao de Regra
# ============================================================

def teste_p2b(id_processo=None):
    """
    Teste do fluxo P2B isolado:
    Le o documento e indica qual regra seria aplicada (sem executar a acao).
    Tambem testa a logica de verificar data < 5 dias.
    Uso: py f.py p2b [id_processo]
    """
    from Prazo.p2b_gateway import extrair_documento_relevante
    from Prazo.p2b_documentos import _definir_regras_processamento
    from Prazo.p2b_core import normalizar_texto, gerar_regex_geral

    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_PEC, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[P2B_TEST] Teste isolado: P2B extracao e match de regra (sem execucao)')
    LOGGER.info('[P2B_TEST] Processo: %s (id=%s)', url, pid)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[P2B_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[P2B_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[P2B_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('p2b_teste'):
            LOGGER.info('[P2B_TEST] Extraindo documento relevante (com logica de data < 5 dias)...')
            resultado = extrair_documento_relevante(driver)

            if not resultado or not resultado.get('sucesso'):
                if (resultado or {}).get('decisao_recente'):
                    LOGGER.info('[P2B_TEST] ⚠️ A decisao encontrada tem 5 dias ou menos e seria PULADA. '
                                '(Data: %s, Idade: %s dias uteis)',
                                (resultado or {}).get('data_extraida', 'N/A'),
                                (resultado or {}).get('idade_dias', 'N/A'))
                    LOGGER.info('[P2B_TEST] >>> REGRA MATCH: Decisão Recente (<= 5 dias uteis) <<<')
                    LOGGER.info("[P2B_TEST] Acoes que seriam chamadas: ['movimentar_inteligente(\"Aguardando Prazo\")']")
                    return
                LOGGER.error('[P2B_TEST] Nenhuma decisao encontrada ou erro: %s',
                             (resultado or {}).get('erro'))
                return

            texto = resultado.get('conteudo', '')
            if not texto:
                LOGGER.error('[P2B_TEST] Documento foi extraido mas o texto esta vazio.')
                return

            LOGGER.info('[P2B_TEST] Documento encontrado! Tipo: %s, Data: %s, Idade: %s dias uteis.',
                        resultado.get('tipo', ''), resultado.get('data_extraida', 'N/A'),
                        resultado.get('idade_dias', 'N/A'))
            LOGGER.info('[P2B_TEST] Trecho (primeiros 200 chars): %s',
                        texto[:200].replace('\n', ' '))

            try:
                from Fix.extracao import _extrair_formatar_texto
                texto_formatado = _extrair_formatar_texto(texto)
            except Exception:
                texto_formatado = texto

            texto_normalizado = normalizar_texto(texto_formatado)

            regras = _definir_regras_processamento()
            for idx, (trechos, tipo_acao) in enumerate(regras):
                match = None
                for trecho in trechos:
                    padrao = trecho if hasattr(trecho, 'search') else gerar_regex_geral(trecho)
                    encontrado = padrao.search(texto_normalizado)
                    if encontrado:
                        match = encontrado
                        break
                if not match:
                    continue

                LOGGER.info(f'[P2B_TEST] >>> REGRA MATCH (indice {idx}) <<<')
                LOGGER.info(f'[P2B_TEST] Expressao casada: {match.re.pattern}')

                acoes_raw = list(tipo_acao) if isinstance(tipo_acao, (list, tuple)) else [tipo_acao]
                acoes = [act.__name__ if callable(act) else str(act) for act in acoes_raw]
                LOGGER.info(f'[P2B_TEST] Acoes que seriam chamadas: {acoes}')
                return

            LOGGER.info('[P2B_TEST] Nenhuma regra do P2B casou com o texto do documento.')

    except Exception:
        LOGGER.exception('[P2B_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[P2B_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 14: PEC — excluiargos
# ============================================================

def teste_pec_excluiargos(id_processo=None):
    """Teste isolado do wrapper pec_excluiargos."""
    from atos.wrappers_pec import pec_excluiargos
    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_PEC, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[PEC_EXCLUIARGOS_TEST] Teste isolado: pec_excluiargos')
    LOGGER.info('[PEC_EXCLUIARGOS_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[PEC_EXCLUIARGOS_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[PEC_EXCLUIARGOS_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[PEC_EXCLUIARGOS_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('pec_excluiargos'):
            LOGGER.info('[PEC_EXCLUIARGOS_TEST] Executando pec_excluiargos...')
            ok = pec_excluiargos(driver, debug=True)
            LOGGER.info('[PEC_EXCLUIARGOS_TEST] pec_excluiargos -> %s', 'OK' if ok else 'FALHA')

        LOGGER.info('[PEC_EXCLUIARGOS_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[PEC_EXCLUIARGOS_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[PEC_EXCLUIARGOS_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 15: SISBAJUD — direto (teimosinha)
# ============================================================

def teste_sisbajud_direto(numero_processo=None):
    """
    Teste isolado para comecar direto no driver sisbajud com navegacao para a
    tela de teimosinha (processar ordens) com um numero de processo fixo.
    """
    configurar_logging_debug()
    numero_processo = numero_processo or "1002077-60.2024.5.02.0060"

    LOGGER.info('=' * 60)
    LOGGER.info('[SISBAJUD_DIRETO_TEST] Teste isolado: processar_ordem_sisbajud (teimosinha direto)')
    LOGGER.info('[SISBAJUD_DIRETO_TEST] Processo CNJ: %s', numero_processo)
    LOGGER.info('=' * 60)

    driver_pje = None
    driver_sisb = None
    try:
        with etapa('criar_driver'):
            driver_pje = criar_driver_vt(headless=False)
        if not driver_pje:
            LOGGER.error('[SISBAJUD_DIRETO_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver_pje):
                LOGGER.error('[SISBAJUD_DIRETO_TEST] Falha no login')
                return

        with etapa('iniciar_sisbajud'):
            from SISB.core import iniciar_sisbajud, processar_ordem_sisbajud
            driver_sisb = iniciar_sisbajud(driver_pje=driver_pje, extrair_dados=False)
            if not driver_sisb:
                LOGGER.error('[SISBAJUD_DIRETO_TEST] Falha ao iniciar SISBAJUD')
                return

        with etapa('processar_ordens'):
            LOGGER.info('[SISBAJUD_DIRETO_TEST] Executando processar_ordem_sisbajud...')
            dados = {
                'numero_processo': numero_processo,
                'divida': {'valor': 'R$ 28.500,00', 'data': '10/05/2024'}
            }
            resultado = processar_ordem_sisbajud(driver_sisb, dados,
                                                  driver_pje=driver_pje, fechar_driver=False)
            LOGGER.info('[SISBAJUD_DIRETO_TEST] processar_ordem_sisbajud -> %s', resultado)

        LOGGER.info('[SISBAJUD_DIRETO_TEST] concluido com sucesso')

    except Exception:
        LOGGER.exception('[SISBAJUD_DIRETO_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[SISBAJUD_DIRETO_TEST] encerrando drivers')
        for d in (driver_sisb, driver_pje):
            if d is not None:
                try:
                    finalizar_driver(d)
                except Exception:
                    pass


# ============================================================
# TESTE 15b: SISBAJUD — minuta dupla (teimosinha) direto, SEM PJe
# ============================================================

def teste_sisbajud_minuta_direto(prazo_dias=None):
    """
    Teste isolado da minuta dupla de teimosinha direto no driver SISBAJUD.

    - NAO abre PJe: usa os dados ja gravados em dadosatuais.json.
    - Chama apenas funcoes reais: iniciar_sisbajud + minuta_bloqueio_amanha.
    - driver_pje=None => nao ha juntada; o relatorio gerado e impresso no log
      (resultado['relatorio_minuta_1'] e resultado['relatorio_consolidado']).
    Uso: py f.py minutadir [30|60]
    """
    configurar_logging_debug()
    prazo = int(prazo_dias) if prazo_dias else 30

    LOGGER.info('=' * 60)
    LOGGER.info('[MINUTA_DIR_TEST] minuta_bloqueio_amanha direto (sem PJe), prazo=%s', prazo)
    LOGGER.info('=' * 60)

    caminho = os.path.join(AQUI, 'dadosatuais.json')
    try:
        with open(caminho, 'r', encoding='utf-8') as fh:
            dados_processo = json.load(fh)
    except Exception:
        LOGGER.exception('[MINUTA_DIR_TEST] Nao foi possivel ler %s', caminho)
        return
    LOGGER.info('[MINUTA_DIR_TEST] Processo em memoria: %s | reus=%d | divida=%s',
                dados_processo.get('numero'), len(dados_processo.get('reu') or []),
                dados_processo.get('divida'))

    driver_sisb = None
    try:
        with etapa('iniciar_sisbajud'):
            from SISB.core import iniciar_sisbajud, minuta_bloqueio_amanha
            driver_sisb = iniciar_sisbajud(driver_pje=None, extrair_dados=False)
            if not driver_sisb:
                LOGGER.error('[MINUTA_DIR_TEST] Falha ao iniciar SISBAJUD')
                return

        with etapa('minuta_bloqueio_amanha'):
            resultado = minuta_bloqueio_amanha(
                driver_sisb, dados_processo=dados_processo, driver_pje=None,
                log=True, fechar_driver=False, prazo_dias=prazo)

        resultado = resultado or {}
        LOGGER.info('[MINUTA_DIR_TEST] status=%s erros=%s', resultado.get('status'), resultado.get('erros'))
        LOGGER.info('[MINUTA_DIR_TEST] minuta_1=%s', resultado.get('minuta_1'))
        LOGGER.info('[MINUTA_DIR_TEST] minuta_2=%s', resultado.get('minuta_2'))
        LOGGER.info('[MINUTA_DIR_TEST] RELATORIO MINUTA 1:\n%s', resultado.get('relatorio_minuta_1'))
        LOGGER.info('[MINUTA_DIR_TEST] RELATORIO MINUTA 2:\n%s', resultado.get('relatorio_minuta_2'))
        LOGGER.info('[MINUTA_DIR_TEST] RELATORIO CONSOLIDADO (sairia na juntada):\n%s',
                    resultado.get('relatorio_consolidado'))
        LOGGER.info('[MINUTA_DIR_TEST] concluido')

    except Exception:
        LOGGER.exception('[MINUTA_DIR_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[MINUTA_DIR_TEST] navegador SISBAJUD mantido aberto para inspecao.')
        try:
            input('[MINUTA_DIR_TEST] ENTER para fechar o navegador SISBAJUD... ')
        except Exception:
            pass
        if driver_sisb is not None:
            try:
                finalizar_driver(driver_sisb)
            except Exception:
                pass


# ============================================================
# TESTE 16: CARTA — fluxo completo (intimacoes + eCarta + juntada)
# ============================================================

def teste_carta_completa(id_processo=None):
    """
    Teste isolado do orquestrador carta() -- PEC/carta_execucao.py:
        coletar_intimacoes -> coletar_tabela_ecarta -> formatar_dados_ecarta
        -> salvar_conteudo_clipboard -> anex_carta (juntada)

    Diferente de teste_anex_carta (que so testa a juntada isolada, assumindo
    conteudo ja pronto no clipboard), este roda o fluxo completo do zero.
    """
    from PEC.carta_execucao import carta

    configurar_logging_debug()
    url, pid = _resolver(PROCESS_ID_ANEX_CARTA, id_processo)

    LOGGER.info('=' * 60)
    LOGGER.info('[CARTA_TEST] Teste isolado: carta() (fluxo completo)')
    LOGGER.info('[CARTA_TEST] Processo: %s', url)
    LOGGER.info('=' * 60)

    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[CARTA_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[CARTA_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[CARTA_TEST] Navegando para %s', url)
            _navegar(driver, url)

        with etapa('carta'):
            LOGGER.info('[CARTA_TEST] Executando carta()...')
            resultado = carta(driver, log=True)
            LOGGER.info('[CARTA_TEST] carta() -> %s', resultado)

        LOGGER.info('[CARTA_TEST] concluido')

    except Exception:
        LOGGER.exception('[CARTA_TEST] Erro nao tratado')
    finally:
        LOGGER.info('[CARTA_TEST] encerrando driver')
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


# ============================================================
# TESTE 17: MARCAR AUD — diagnostico isolado da designacao de audiencia
# ============================================================
#
# Uso: py f.py aud <id_processo> [numero_cnj] [rito] [hora]
#   py f.py aud 1002072                        -> id direto, numero/rito/hora auto
#   py f.py aud 1002072 1002072-78.2026.5.02.0703 ATVARI 08:35
#
# Instrumenta cada etapa de _marcar_aud: URL da pauta, DOM do modal antes/depois
# do Confirmar, estado dos campos, toast, screenshots e TODAS as requisicoes de
# rede -- para descobrir por que o PJe responde "Consulte o processo para
# designar audiencia".
# ============================================================

_DIR_AUD_DIAG = os.path.join(AQUI, 'logs_execucao', 'aud_diag')


def _aud_salvar(nome: str, conteudo) -> str:
    """Grava um artefato de diagnostico e devolve o caminho."""
    os.makedirs(_DIR_AUD_DIAG, exist_ok=True)
    caminho = os.path.join(_DIR_AUD_DIAG, nome)
    try:
        with open(caminho, 'w', encoding='utf-8') as fh:
            fh.write(conteudo if isinstance(conteudo, str) else json.dumps(
                conteudo, ensure_ascii=False, indent=2))
    except Exception as e:
        LOGGER.warning('[AUD_TEST] falha ao salvar %s: %s', nome, e)
    return caminho


def _aud_html(driver, seletor: str, limite: int = 6000) -> str:
    """HTML externo de um elemento (ou '' se ausente).

    Antes devolvia `espera.ate_js(...)`, que retorna bool (True/False) e nao o
    HTML -- os dumps saiam como "True". Agora le o valor de verdade.
    """
    js = (
        "(function(){var e=document.querySelector(%s);"
        "return e ? e.outerHTML : '';})()" % json.dumps(seletor)
    )
    page = getattr(driver, 'page', None)
    if page is not None:
        try:
            return str(page.evaluate(js) or '')[:limite * 20]
        except Exception as e:
            LOGGER.warning('[AUD_TEST] html via page falhou: %s', e)
    try:
        fn = getattr(driver, 'execute_script', None)
        if fn is not None:
            return str(fn('return ' + js) or '')[:limite * 20]
    except Exception as e:
        LOGGER.warning('[AUD_TEST] html via driver falhou: %s', e)
    return ''


def _aud_screenshot(driver, nome: str) -> None:
    """Screenshot da aba atual (Playwright e Selenium)."""
    try:
        os.makedirs(_DIR_AUD_DIAG, exist_ok=True)
        caminho = os.path.join(_DIR_AUD_DIAG, nome)
        page = getattr(driver, 'page', None)
        if page is not None and hasattr(page, 'screenshot'):
            page.screenshot(path=caminho, full_page=True)
            LOGGER.info('[AUD_TEST] screenshot -> %s', caminho)
            return
        fn = getattr(driver, 'save_screenshot', None)
        if callable(fn):
            fn(caminho)
            LOGGER.info('[AUD_TEST] screenshot -> %s', caminho)
    except Exception as e:
        LOGGER.warning('[AUD_TEST] screenshot falhou: %s', e)


def _aud_estado_modal(driver) -> dict:
    """Estado detalhado do modal de audiencia: campos, selects, botoes, texto."""
    js = """
    (function(){
      var d = document.querySelector('mat-dialog-container');
      if (!d) return {aberto:false};
      function txt(e){ return e ? (e.textContent||'').replace(/\\s+/g,' ').trim() : ''; }
      var campos = [];
      d.querySelectorAll('input,textarea').forEach(function(el,i){
        campos.push({i:i, id:el.id||'', nome:el.getAttribute('formcontrolname')||el.name||'',
                     valor:(el.value||''), vazio:!(el.value||'').trim(),
                     disabled:!!el.disabled,
                     ariaInvalid:el.getAttribute('aria-invalid')||'',
                     classe:(el.className||'').slice(0,120)});
      });
      var selects = [];
      d.querySelectorAll('mat-select').forEach(function(s,i){
        selects.push({i:i, controle:s.getAttribute('formcontrolname')||'',
                      valor:txt(s.querySelector('.mat-select-value'))});
      });
      var botoes = [];
      d.querySelectorAll('button').forEach(function(b,i){
        botoes.push({i:i, texto:txt(b), disabled:!!b.disabled,
                     classe:(b.className||'').slice(0,120)});
      });
      var erros = [];
      d.querySelectorAll('mat-error, .mat-form-field-invalid, .mat-error, [class*="erro"], [class*="error"]')
       .forEach(function(e){ var t=txt(e); if(t) erros.push(t.slice(0,200)); });
      return {
        aberto:true,
        texto:txt(d).slice(0,1200),
        campos:campos, selects:selects, botoes:botoes,
        erros:erros.slice(0,20),
        tem_container_conteudo: !!d.querySelector('div.container-conteudo'),
        classes_ativas: [].slice.call(d.querySelectorAll('[class*="ativo"],[class*="conteudo"]'))
                          .map(function(e){return (e.className||'').slice(0,100);}).slice(0,10)
      };
    })()
    """
    page = getattr(driver, 'page', None)
    try:
        if page is not None:
            return page.evaluate(js) or {'aberto': False}
    except Exception as e:
        LOGGER.warning('[AUD_TEST] estado do modal falhou (page): %s', e)
    try:
        fn = getattr(driver, 'execute_script', None)
        if fn is not None:
            return fn(js) or {'aberto': False}
    except Exception as e:
        LOGGER.warning('[AUD_TEST] estado do modal falhou (driver): %s', e)
    return {'aberto': False, 'erro': 'sem evaluate'}


def _aud_instalar_monitor_rede(driver):
    """Captura requisicoes/respostas da pagina para correlacionar com o erro."""
    eventos = []
    page = getattr(driver, 'page', None)
    if page is None:
        return eventos, None

    def _on_response(resp):
        try:
            url = resp.url
            if not any(k in url for k in ('pauta', 'audiencia', 'designa', 'gravar', 'salvar', 'api/')):
                return
            corpo = ''
            try:
                ctype = (resp.headers or {}).get('content-type', '')
                if 'json' in ctype or 'text' in ctype:
                    corpo = resp.text()[:500]
            except Exception:
                corpo = '(corpo indisponivel)'
            eventos.append({'status': resp.status, 'metodo': resp.request.method,
                            'url': url[:300], 'corpo': corpo})
        except Exception:
            pass

    try:
        page.on('response', _on_response)
        return eventos, page
    except Exception as e:
        LOGGER.warning('[AUD_TEST] nao foi possivel instalar monitor de rede: %s', e)
        return eventos, None


def teste_marcar_aud(id_processo=None, numero_cnj=None, rito=None, hora=None):
    """
    Teste ISOLADO de _marcar_aud com diagnostico completo.

    Aceita tanto o ID do processo (como os outros testes) quanto o numero CNJ.
    Se o argumento tiver o formato CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO), ele e usado
    direto como numero e o ID e extraido do processo aberto no PJe.

    Uso: py f.py aud 1002072
         py f.py aud 1002072-78.2026.5.02.0703 ATVARI 08:35
    """
    import re as _re
    from bianca.triagem import acoes as _acoes

    configurar_logging_debug()
    logging.getLogger('bianca').setLevel(logging.DEBUG)

    # Parametros posicionais: aceitam id ou CNJ em qualquer ordem util
    args_pos = [a for a in (id_processo, numero_cnj, rito, hora) if a]
    cnj = next((a for a in args_pos if _re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', a)), None)
    id_num = next((a for a in args_pos if str(a).isdigit()), None)
    rito_arg = next((a for a in args_pos if str(a).upper() in ('ATVARI', 'ATSUM', 'ATORD')), None)
    hora_arg = next((a for a in args_pos if _re.match(r'^\d{1,2}:\d{2}$', a)), None)

    id_processo = id_num or '8685584'

    LOGGER.info('=' * 70)
    LOGGER.info('[AUD_TEST] Diagnostico isolado de _marcar_aud')
    LOGGER.info('[AUD_TEST] id_processo=%s  cnj=%s  rito=%s  hora=%s',
                id_processo, cnj, rito_arg, hora_arg)
    LOGGER.info('[AUD_TEST] artefatos em: %s', _DIR_AUD_DIAG)
    LOGGER.info('=' * 70)

    url, pid = _resolver(id_processo)
    driver = None
    try:
        with etapa('criar_driver'):
            driver = criar_driver_vt(headless=False)
        if not driver:
            LOGGER.error('[AUD_TEST] Falha ao criar driver')
            return

        with etapa('login'):
            if not _logar_como_pw_visivel(driver):
                LOGGER.error('[AUD_TEST] Falha no login')
                return

        with etapa('navegar_processo'):
            LOGGER.info('[AUD_TEST] Navegando para %s', url)
            _navegar(driver, url)

        # --- numero CNJ e rito reais, direto do cabecalho ---
        with etapa('detectar_processo'):
            info = _aud_js_info_processo(driver)
            LOGGER.info('[AUD_TEST] info do cabecalho: %s', json.dumps(info, ensure_ascii=False))
            numero = cnj or info.get('cnj') or ''
            tipo = info.get('tipo') or ''
            LOGGER.info('[AUD_TEST] numero detectado: %r | tipo detectado: %r', numero, tipo)
            if not numero:
                LOGGER.error('[AUD_TEST] Numero CNJ nao detectado no cabecalho -- informe como argumento')
                return

        # rito de pauta: respeita o argumento explicitamente informado
        if rito_arg:
            rito_pauta = rito_arg
            LOGGER.info('[AUD_TEST] rito FORCADO pelo argumento: %s', rito_pauta)
        else:
            rito_pauta = 'ATSUM' if tipo.upper().startswith('ATSUM') else 'ATVARI'
            LOGGER.info('[AUD_TEST] rito derivado do tipo %r -> %s', tipo, rito_pauta)

        # --- monitor de rede ---
        eventos, page = _aud_instalar_monitor_rede(driver)
        LOGGER.info('[AUD_TEST] monitor de rede: %s', 'ativo' if page is not None else 'indisponivel')

        # --- desmarcar 100% (igual ao fluxo de producao) ---
        with etapa('desmarcar_100'):
            aba_retificar = _acoes.desmarcar_100(driver, pid)
            LOGGER.info('[AUD_TEST] aba retificar: %s', aba_retificar)

        # --- preview da URL antes de tentar ---
        url_previa = (f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true"
                      f"&numero={numero}&rito={rito_pauta}&fase=Conhecimento")
        LOGGER.info('[AUD_TEST] URL de pauta: %s', url_previa)

        if not aba_retificar:
            LOGGER.warning('[AUD_TEST] Sem aba retificar -- seguindo de qualquer forma')

        # --- gancho de diagnostico: captura o modal ANTES de _marcar_aud fechar ---
        capturas = []

        def _hook(etapa_hook, info_hook):
            LOGGER.info('[AUD_TEST] >>> hook: %s  info=%s', etapa_hook, info_hook)
            if etapa_hook == 'tabela_carregada':
                _aud_screenshot(driver, '1_pauta_carregada.png')
                return
            estado = _aud_estado_modal(driver)
            _aud_salvar(f'modal_{etapa_hook}.json', estado)
            html = _aud_html(driver, 'mat-dialog-container')
            if not isinstance(html, str):
                html = '' if html is None else str(html)
            if html:
                _aud_salvar(f'modal_{etapa_hook}.html', html)
            # O painel do autocomplete mora no overlay do CDK, fora do modal
            overlay = _aud_html(driver, '.cdk-overlay-container')
            if overlay:
                _aud_salvar(f'overlay_{etapa_hook}.html', overlay)
            _aud_screenshot(driver, f'2_{etapa_hook}.png')
            capturas.append(etapa_hook)
            LOGGER.info('[AUD_TEST] estado do modal em %r: %s',
                        etapa_hook, json.dumps(estado, ensure_ascii=False)[:2500])
            if html:
                LOGGER.info('[AUD_TEST] HTML do modal (%d chars) -> modal_%s.html',
                            len(html), etapa_hook)

        _acoes._HOOK_DIAG = _hook
        LOGGER.info('[AUD_TEST] hook de diagnostico instalado')

        # --- chamada real ---
        # Os print('[MARCAR_AUD] ...') de acoes.py so iam para o console e nao
        # ficavam em nenhum log; aqui sao redirecionados para o LOGGER.
        class _StdoutParaLog:
            def __init__(self, destino):
                self._destino = destino
                self._buf = ''

            def write(self, texto):
                self._buf += texto
                while '\n' in self._buf:
                    linha, self._buf = self._buf.split('\n', 1)
                    if linha.strip():
                        LOGGER.info('[PRINT] %s', linha.rstrip())
                try:
                    self._destino.write(texto)
                except Exception:
                    pass
                return len(texto)

            def flush(self):
                try:
                    self._destino.flush()
                except Exception:
                    pass

        with etapa('marcar_aud'):
            t0 = time.perf_counter()
            _stdout_original = sys.stdout
            sys.stdout = _StdoutParaLog(_stdout_original)
            try:
                res_aud = _acoes._marcar_aud(driver, numero, rito_pauta, aba_retificar or '')
            finally:
                sys.stdout = _stdout_original
            ok = res_aud[0] if isinstance(res_aud, tuple) else bool(res_aud)
            dt_aud = res_aud[1] if isinstance(res_aud, tuple) else None
            LOGGER.info('[AUD_TEST] _marcar_aud -> %s (data: %s) (%.2fs)', ok, dt_aud, time.perf_counter() - t0)

        if ok and aba_retificar and aba_retificar in getattr(driver, 'window_handles', []):
            with etapa('remarcar_100'):
                driver.switch_to.window(aba_retificar)
                remarcou = _acoes.remarcar_100_pos_aud(driver)
                LOGGER.info('[AUD_TEST] remarcar_100_pos_aud -> %s', remarcou)

        _acoes._HOOK_DIAG = None
        LOGGER.info('[AUD_TEST] capturas do modal: %s', capturas or 'nenhuma')

        # --- artefatos finais ---
        try:
            LOGGER.info('[AUD_TEST] URL final da aba ativa: %s', driver.current_url)
        except Exception:
            pass
        _aud_screenshot(driver, 'final.png')

        # Painel de diagnostico no console
        LOGGER.info('=' * 70)
        LOGGER.info('[AUD_TEST] RESULTADO: %s', 'DESIGNADO' if ok else 'FALHOU')
        LOGGER.info('[AUD_TEST] Requisicoes de rede capturadas: %d', len(eventos))
        for ev in eventos[-15:]:
            LOGGER.info('[AUD_TEST]   HTTP %s %s %s\n           %s',
                        ev['status'], ev['metodo'], ev['url'], (ev['corpo'] or '')[:300])
        _aud_salvar('rede.json', eventos)
        LOGGER.info('[AUD_TEST] artefatos salvos em %s', _DIR_AUD_DIAG)
        LOGGER.info('=' * 70)

        if not ok:
            LOGGER.error('[AUD_TEST] Designacao FALHOU -- ver modal_*.json, modal_*.html e rede.json')
            LOGGER.error('[AUD_TEST] Dica: se o toast citar "Consulte o processo", compare a URL '
                         'logada com a que funciona no navegador (rito/numero/fase).')

    except Exception:
        LOGGER.exception('[AUD_TEST] Erro nao tratado')
    finally:
        # Pausa de inspecao: por padrao o navegador FICA ABERTO para conferir
        # o estado do modal. Use --fechar (ou PJE_AUD_FECHAR=1) para fechar.
        fechar = ('--fechar' in sys.argv) or os.environ.get('PJE_AUD_FECHAR') == '1'
        if driver is not None and not fechar:
            try:
                LOGGER.info('=' * 70)
                LOGGER.info('[AUD_TEST] NAVEGADOR ABERTO para inspecao.')
                LOGGER.info('[AUD_TEST] Confira a janela do PJe; pressione ENTER aqui para fechar.')
                try:
                    input()
                except EOFError:
                    LOGGER.info('[AUD_TEST] sem terminal interativo; aguardando 60s...')
                    import time as _time
                    _time.sleep(60)
            except Exception:
                pass
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception:
                pass


def _aud_js_info_processo(driver) -> dict:
    """Le numero CNJ e tipo (ATOrd/ATSum/...) do cabecalho do processo."""
    js = """
    (function(){
      var out = {cnj:'', tipo:'', titulo:''};
      var cab = document.querySelector('pje-cabecalho-processo');
      var escopo = cab || document;
      // numero CNJ: aria-label de "Detalhes do Processo" ou regex no texto
      var a = escopo.querySelector('a[aria-label*="Detalhes do Processo"]');
      if (a) {
        var m = (a.getAttribute('aria-label')||'').match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/);
        if (m) out.cnj = m[0];
      }
      if (!out.cnj) {
        var m2 = (document.body.innerText||'').match(/\\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/);
        if (m2) out.cnj = m2[0];
      }
      // tipo: span com ATOrd/ATSum/ACum
      var spans = escopo.querySelectorAll('span');
      for (var i=0;i<spans.length;i++){
        var t = (spans[i].innerText||spans[i].textContent||'').trim();
        if (/^(ATOrd|ATSum|ACum|ATVARI|ATSUM)\\b/i.test(t) || /\\b(ATOrd|ATSum|ACum)\\b/.test(t)) {
          out.tipo = t.slice(0,120); break;
        }
      }
      out.titulo = (document.title||'').slice(0,120);
      return out;
    })()
    """
    page = getattr(driver, 'page', None)
    try:
        if page is not None:
            return page.evaluate(js) or {}
    except Exception as e:
        LOGGER.warning('[AUD_TEST] info via page falhou: %s', e)
    try:
        fn = getattr(driver, 'execute_script', None)
        if fn is not None:
            return fn(js) or {}
    except Exception as e:
        LOGGER.warning('[AUD_TEST] info via driver falhou: %s', e)
    return {}


# ============================================================
# MAIN — seleciona qual teste executar
# ============================================================

if __name__ == '__main__':
    teste = sys.argv[1].lower() if len(sys.argv) > 1 else 'argos'
    id_p  = sys.argv[2] if len(sys.argv) > 2 else None

    if teste in ('argos', '1'):
        teste_buscar_sequenciais(id_p)
    elif teste in ('sisb', 'sisbajud', 'minuta', '2'):
        teste_sisbajud_minuta(id_p)
    elif teste in ('pec', 'sigilo', '3'):
        teste_pec_sigilo(id_p)
    elif teste in ('pesquisa', 'ato_pesquisas', '4'):
        teste_ato_pesquisas(id_p)
    elif teste in ('ordem', 'resultado', '5'):
        teste_sisbajud_ordem(id_p)
    elif teste in ('pecord', '6'):
        teste_pec_ord(id_p)
    elif teste in ('pecidpj', 'idpj', '6b'):
        teste_pec_idpj(id_p)
    elif teste in ('mddid', 'xs_mddid', '6c'):
        teste_mddid(id_p)
    elif teste in ('anex', 'anex_carta', 'juntada', '7'):
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
        _teste_dom_eletronico_1_proc(id_p)
    elif teste in ('bndt', 'exclusao', '12'):
        teste_bndt_exclusao(id_p)
    elif teste in ('p2b', '13'):
        teste_p2b(id_p)
    elif teste in ('excluiargos', 'exclui', '14'):
        teste_pec_excluiargos(id_p)
    elif teste in ('sisbdir', '15'):
        teste_sisbajud_direto(id_p)
    elif teste in ('minutadir', 'minuta_direta', '15b'):
        teste_sisbajud_minuta_direto(id_p)
    elif teste in ('carta', 'carta_completa', 'carta_full', 'fluxo_carta', '16'):
        teste_carta_completa(id_p)
    elif teste in ('aud', 'marcar_aud', 'marcaraud', '17'):
        arg3 = sys.argv[3] if len(sys.argv) > 3 else None
        arg4 = sys.argv[4] if len(sys.argv) > 4 else None
        teste_marcar_aud(id_p, arg3, arg4)
    elif teste in ('dom_api', 'domapi', '11b'):
        _teste_dom_api_comentario_lembrete(id_p)
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
        print('\n--- TESTE 6b: PEC IDPJ ---')
        teste_pec_idpj(id_p)
        print('\n--- TESTE 6c: XS MDDID ---')
        teste_mddid(id_p)
        print('\n--- TESTE 7: ANEX CARTA ---')
        teste_anex_carta(id_p)
        print('\n--- TESTE 8: TRIAGEM ---')
        teste_triagem_peticao(id_p)
        print('\n--- TESTE 11: DOM ELETRONICO ---')
        _teste_dom_eletronico_1_proc(id_p)
        print('\n--- TESTE 13: P2B (match regras) ---')
        teste_p2b(id_p)
        print('\n--- TESTE 14: PEC EXCLUIARGOS ---')
        teste_pec_excluiargos(id_p)
    else:
        print(f'Teste desconhecido: {teste}')
        print('Disponiveis: argos, sisb, pec, pesquisa, ordem, pecord, pecidpj, mddid,')
        print('             anex, triagem, probe, tdbg, dom, bndt, p2b, excluiargos,')
        print('             sisbdir, carta, todos')
        print('Uso: py f.py <teste> [id_processo]')
