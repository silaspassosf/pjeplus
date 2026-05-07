# ============================================================
# f.py -- Harness de teste isolado: buscar_documentos_sequenciais_via_api
# Uso: py f.py
# Processo alvo ARGOS: 7115867
# ============================================================

PROCESS_URL_ARGOS = 'https://pje.trt2.jus.br/pjekz/processo/7115867/detalhe/'

import json
import logging
import time
from contextlib import contextmanager

from x import criar_driver_pc
from Fix.utils import login_cpf, navegar_para_tela


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
    root.setLevel(logging.DEBUG)
    if not root.handlers:
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(_DestaquFormatter())
    for nome in ('Fix', 'PEC', 'SISB', 'atos', 'urllib3', 'requests'):
        logging.getLogger(nome).setLevel(logging.DEBUG)


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


def teste_buscar_sequenciais():
    """Teste isolado da funcao buscar_documentos_sequenciais_via_api."""
    from Mandado.apoio_fluxos import (
        buscar_documentos_sequenciais_via_api,
        retirar_sigilo_fluxo_argos,
    )
    configurar_logging_debug()

    for nome in (
        'selenium', 'selenium.webdriver', 'selenium.webdriver.remote',
        'selenium.webdriver.remote.remote_connection',
        'urllib3', 'urllib3.connectionpool', 'requests',
    ):
        logging.getLogger(nome).setLevel(logging.WARNING)

    LOGGER.info('=' * 60)
    LOGGER.info('[ARGOS_TEST] Teste isolado: buscar_documentos_sequenciais_via_api')
    LOGGER.info('[ARGOS_TEST] Processo: %s', PROCESS_URL_ARGOS)
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

        with etapa('navegar_processo'):
            LOGGER.info('[ARGOS_TEST] Navegando para %s', PROCESS_URL_ARGOS)
            t0 = time.perf_counter()
            navegar_para_tela(driver, url=PROCESS_URL_ARGOS)
            LOGGER.info('[ARGOS_TEST] navegacao concluida em %.2fs', time.perf_counter() - t0)

        # ── ETAPA 1: buscar documentos sequenciais via API ──
        with etapa('etapa1_docs_sequenciais_api'):
            t0 = time.perf_counter()
            docs, uids_sig = buscar_documentos_sequenciais_via_api(driver, log=True)
            LOGGER.info('[ARGOS_TEST] buscar_documentos_sequenciais_via_api -> docs=%d sigilosos=%d (%.2fs)',
                        len(docs), len(uids_sig or []), time.perf_counter() - t0)

        if not docs:
            LOGGER.error('[ARGOS_TEST] API docs=0 — ABORTANDO')
            return

        LOGGER.info('[ARGOS_TEST] Documentos encontrados:')
        for i, doc in enumerate(docs):
            LOGGER.info('[ARGOS_TEST]   [%d] %s', i, (doc.text or '').strip()[:120])

        # ── ETAPA 1.5: sigilo ──
        with etapa('etapa1_5_sigilo'):
            t0 = time.perf_counter()
            res = retirar_sigilo_fluxo_argos(driver, docs, log=True, uids_sigilosos_hint=uids_sig)
            LOGGER.info('[ARGOS_TEST] sigilo -> processados=%d (%.2fs)',
                        res.get('total_processados', 0), time.perf_counter() - t0)

        LOGGER.info('[ARGOS_TEST] concluido com sucesso')

    finally:
        LOGGER.info('[ARGOS_TEST] encerrando driver')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    teste_buscar_sequenciais()
