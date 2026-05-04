# ============================================================
# f.py -- Harness de teste isolado: fluxo RESULTADO em PEC
# Uso: py f.py
# Processo alvo: 1738069
# ============================================================

PROCESS_URL = 'https://pje.trt2.jus.br/pjekz/processo/1738069/detalhe'

import json
import logging
import sys
import types
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import requests

from x import criar_driver_pc
from Fix.utils import login_cpf, navegar_para_tela


def configurar_logging_debug():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
    )
    for nome in ('Fix', 'PEC', 'SISB', 'atos', 'urllib3', 'requests'):
        logging.getLogger(nome).setLevel(logging.DEBUG)


LOGGER = logging.getLogger('f')


def instalar_shim_fix_scripts():
    modulo = sys.modules.get('Fix.scripts')
    if modulo and hasattr(modulo, 'carregar_js'):
        return

    scripts_dir = Path('SISB') / 'scripts'

    def carregar_js(nome_arquivo: str, pasta: Path | str | None = None):
        base_dir = Path(pasta) if pasta else scripts_dir
        caminho = base_dir / nome_arquivo
        try:
            return caminho.read_text(encoding='utf-8')
        except Exception:
            LOGGER.debug('[shim Fix.scripts] arquivo nao encontrado: %s', caminho)
            return ''

    modulo = types.ModuleType('Fix.scripts')
    modulo.carregar_js = carregar_js
    sys.modules['Fix.scripts'] = modulo


def instalar_shim_sisb_package():
    modulo = sys.modules.get('SISB')
    if modulo is None:
        modulo = types.ModuleType('SISB')
        sys.modules['SISB'] = modulo

    modulo.__path__ = [str((Path('SISB')).resolve())]


class MedidorChamadas:
    def __init__(self):
        self.total = 0
        self.contagens = Counter()
        self.inicio = time.perf_counter()

    def registrar(self, nome: str):
        self.total += 1
        self.contagens[nome] += 1

    def resumo(self):
        return {
            'total': self.total,
            'duracao_segundos': round(time.perf_counter() - self.inicio, 2),
            'detalhes': dict(self.contagens),
        }


class DriverInstrumentado:
    def __init__(self, driver, medidor: MedidorChamadas, nome: str):
        self._driver = driver
        self._medidor = medidor
        self._nome = nome

    def __getattr__(self, item):
        attr = getattr(self._driver, item)
        if item == 'switch_to':
            return SwitchToInstrumentado(attr, self._medidor, self._nome)
        if callable(attr):
            def wrapper(*args, **kwargs):
                self._medidor.registrar(f'{self._nome}.{item}')
                LOGGER.debug('[%s] %s args=%d kwargs=%d', self._nome, item, len(args), len(kwargs))
                return attr(*args, **kwargs)

            return wrapper
        return attr


class SwitchToInstrumentado:
    def __init__(self, switch_to, medidor: MedidorChamadas, nome: str):
        self._switch_to = switch_to
        self._medidor = medidor
        self._nome = nome

    def __getattr__(self, item):
        attr = getattr(self._switch_to, item)
        if callable(attr):
            def wrapper(*args, **kwargs):
                self._medidor.registrar(f'{self._nome}.switch_to.{item}')
                LOGGER.debug('[%s.switch_to] %s args=%d kwargs=%d', self._nome, item, len(args), len(kwargs))
                return attr(*args, **kwargs)

            return wrapper
        return attr


@contextmanager
def rastrear_requests(medidor: MedidorChamadas):
    original_session = requests.Session

    class CountingSession(original_session):
        def request(self, method, url, *args, **kwargs):
            medidor.registrar(f'requests.{method.upper()}')
            LOGGER.debug('[requests] %s %s', method.upper(), url)
            return super().request(method, url, *args, **kwargs)

    requests.Session = CountingSession
    try:
        yield
    finally:
        requests.Session = original_session


@contextmanager
def etapa(nome: str):
    inicio = time.perf_counter()
    LOGGER.info('[TESTE][%s] iniciando', nome)
    try:
        yield
        LOGGER.info('[TESTE][%s] concluído em %.2fs', nome, time.perf_counter() - inicio)
    except Exception:
        LOGGER.exception('[TESTE][%s] falhou após %.2fs', nome, time.perf_counter() - inicio)
        raise


def main():
    configurar_logging_debug()
    medidor = MedidorChamadas()
    driver = None
    driver_sisb = None

    try:
        with etapa('criar_driver_pje'):
            driver = criar_driver_pc(headless=False)
        if not driver:
            print('[TESTE][ERRO] Falha ao criar driver PJE')
            return

        driver = DriverInstrumentado(driver, medidor, 'pje')

        with etapa('login_pje'):
            if not login_cpf(driver):
                print('[TESTE][ERRO] Falha no login via login_cpf()')
                return

        with rastrear_requests(medidor):
            with etapa('abrir_processo_pje'):
                print(f'[TESTE] Navegando para processo de teste: {PROCESS_URL}')
                if not navegar_para_tela(driver, url=PROCESS_URL):
                    print('[TESTE][ERRO] Falha ao navegar para o processo alvo')
                    return

            with etapa('extrair_dados_processo'):
                print('[TESTE] Extraindo dados do processo para SISBAJUD...')
                try:
                    from Fix.extracao import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, debug=True)
                except Exception as e:
                    print('[TESTE][ERRO] Falha ao extrair dados do processo:', e)
                    dados_processo = None

                try:
                    with open('dadosatuais.json', 'w', encoding='utf-8') as fh:
                        json.dump(dados_processo or {}, fh, ensure_ascii=False, indent=2)
                    print('[TESTE] dadosatuais.json salvo')
                except Exception as e:
                    print('[TESTE] Falha ao salvar dadosatuais.json:', e)

            if not dados_processo:
                print('[TESTE][ERRO] Sem dados extraídos; abortando antes do SISBAJUD')
                return

            with etapa('iniciar_sisbajud'):
                try:
                    instalar_shim_fix_scripts()
                    instalar_shim_sisb_package()
                    from SISB.core import iniciar_sisbajud, processar_ordem_sisbajud
                except Exception as e:
                    print('[TESTE][ERRO] Erro ao importar SISB.core:', e)
                    raise

                print('[TESTE] Iniciando driver SISBAJUD...')
                try:
                    driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
                except Exception as e:
                    print('[TESTE][ERRO] Erro ao iniciar SISBAJUD:', e)
                    driver_sisb = None

                if not driver_sisb:
                    print('[TESTE][ERRO] Não foi possível iniciar o driver SISBAJUD')
                    return

                driver_sisb = DriverInstrumentado(driver_sisb, medidor, 'sisb')

            with etapa('processar_resultado'):
                LOGGER.info('[TESTE] Executando fluxo RESULTADO (sem assinar/protocolar)')
                try:
                    from PEC.regras_pec import determinar_regra
                    regra = determinar_regra('resultado')
                    LOGGER.info('[TESTE] Regra de observação simulada: %s', regra[1] if regra else 'sem_regra')
                except Exception:
                    LOGGER.debug('[TESTE] Não foi possível resolver a regra de observação de teste')

                resultado_sisb = processar_ordem_sisbajud(
                    driver=driver_sisb,
                    dados_processo=dados_processo,
                    driver_pje=driver,
                    log=True,
                    fechar_driver=True,
                )
                print('[TESTE] Resultado SISB:', resultado_sisb)

        resumo = medidor.resumo()
        print('[TESTE][RESUMO]', json.dumps(resumo, ensure_ascii=False, indent=2))
        LOGGER.info('[TESTE] Resumo final: %s', json.dumps(resumo, ensure_ascii=False))

    finally:
        print('[TESTE] Encerrando driver PJE...')
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()

