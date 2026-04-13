from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

from typing import Dict, List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from Fix.extracao import extrair_dados_processo
from .progresso import (
    carregar_progresso_pet,
    marcar_processo_executado_pet,
    processo_ja_executado_pet,
)

from .api_client import PeticaoAPIClient, PeticaoItem

BUCKETS_ORDEM = ['diretos', 'pericias', 'recurso', 'analise']
ESCANINHO_URL = 'https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas'


# ---------------------------------------------------------------------------
# Classificador — usa as regras/verificações de pet_novo sem modificá-las
# ---------------------------------------------------------------------------

def _classificar(itens: List[PeticaoItem]) -> Dict[str, List[PeticaoItem]]:
    from .pet import classificar
    buckets: Dict[str, List[PeticaoItem]] = {nome: [] for nome in BUCKETS_ORDEM}
    for item in itens:
        bucket = classificar(item)
        buckets.setdefault(bucket, []).append(item)
    return buckets


# ---------------------------------------------------------------------------
# Execução individual
# ---------------------------------------------------------------------------

def _abrir_processo(driver: WebDriver, item: PeticaoItem) -> bool:
    id_proc = item.id_processo or item.numero_processo
    numero_limpo = ''.join(filter(str.isdigit, str(id_proc)))
    url = (f"https://pje.trt2.jus.br/pjekz/processo/{numero_limpo}/detalhe"
           if len(numero_limpo) == 20
           else f"https://pje.trt2.jus.br/pjekz/processo/{id_proc}/detalhe")
    driver.get(url)
    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script('return document.readyState') == 'complete'
    )
    if 'acesso-negado' in driver.current_url.lower():
        raise RuntimeError(f"RESTART_PET: acesso negado - {item.numero_processo}")
    return True


def _fechar_abas_extras(driver: WebDriver):
    try:
        handles = driver.window_handles
        if len(handles) > 1:
            principal = handles[0]
            for h in handles[1:]:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
            driver.switch_to.window(principal)
    except Exception:
        pass


def _executar_acao(driver: WebDriver, item: PeticaoItem, acao) -> bool:
    if isinstance(acao, tuple):
        for f in acao:
            if callable(f) and not f(driver, item):
                return False
        return True
    return acao(driver, item) if callable(acao) else False


def _executar_bucket_normal(driver: WebDriver, nome: str, itens: List[PeticaoItem],
                             progresso: dict) -> Dict[str, int]:
    """Buckets que requerem abertura individual do processo."""
    from .pet import resolver_acao
    stats = {'sucesso': 0, 'erro': 0}
    quesitos_consolidado = False  # Flag: consolidar apenas uma vez após quesitos

    for item in itens:
        if processo_ja_executado_pet(item.numero_processo, progresso):
            logger.info(f"[SKIP] {item.numero_processo}")
            stats['sucesso'] += 1
            continue

        acao = resolver_acao(item, driver)

        if not acao:
            logger.warning(f"[PET_EXEC] Sem ação para {item.numero_processo} em '{nome}'")
            continue

        logger.info(f"[PET_EXEC] {nome} | {item.numero_processo} | {item.tipo_peticao}")
        try:
            _abrir_processo(driver, item)
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
            ok = _executar_acao(driver, item, acao)
            if ok:
                marcar_processo_executado_pet(item.numero_processo, progresso)
                stats['sucesso'] += 1
            else:
                stats['erro'] += 1
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[PET_EXEC] {item.numero_processo}: {e}")
            stats['erro'] += 1
        finally:
            _fechar_abas_extras(driver)

        # Se processamos um item de quesitos e ainda não consolidamos, fazer agora
        if nome == 'diretos' and not quesitos_consolidado and ('quesitos' in (item.tipo_peticao or '') or 'quesitos' in (item.descricao or '')):
            logger.info('[PET_EXEC] ✓ Quesitos processado → consolidando delete.js')
            _consolidar_delete_bookmarklet()
            quesitos_consolidado = True

    return stats


def _executar_bucket_analise(driver: WebDriver, itens: List[PeticaoItem],
                              progresso: dict) -> Dict[str, int]:
    """Analise: sempre chama analise_pet, independente de hipótese."""
    from .pet import analise_pet
    stats = {'sucesso': 0, 'erro': 0}
    for item in itens:
        if processo_ja_executado_pet(item.numero_processo, progresso):
            logger.info(f"[SKIP] {item.numero_processo}")
            stats['sucesso'] += 1
            continue
        logger.info(f"[PET_EXEC] analise | {item.numero_processo} | {item.tipo_peticao}")
        try:
            _abrir_processo(driver, item)
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
            ok = analise_pet(driver, item)
            if ok:
                marcar_processo_executado_pet(item.numero_processo, progresso)
                stats['sucesso'] += 1
            else:
                stats['erro'] += 1
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[PET_EXEC] analise {item.numero_processo}: {e}")
            stats['erro'] += 1
        finally:
            _fechar_abas_extras(driver)
    return stats


def _executar_bucket_apagar(itens: List[PeticaoItem]) -> Dict[str, int]:
    """Apagar: sem abertura de processo — registra em delete.js apenas com id_doc."""
    from .helpers import apagar
    stats = {'sucesso': 0, 'erro': 0}
    for item in itens:
        try:
            apagar(item.numero_processo, item.id_item)
            logger.info(f'[PET_APAG] {item.numero_processo} | id_doc={item.id_item!r}')
            stats['sucesso'] += 1
        except Exception as e:
            logger.error(f'[PET_APAG] {item.numero_processo}: {e}')
            stats['erro'] += 1
    return stats


def _consolidar_delete_bookmarklet():
    """Consolida delete.js após habilitação e gera bookmarklet."""
    try:
        from .consolida_delete import consolidar_delete_com_bookmarklet
        consolidar_delete_com_bookmarklet()
        logger.info('[PET_ORQ] ✅ delete.js consolidado e bookmarklet gerado')
    except Exception as e:
        logger.warning(f'[PET_ORQ] ⚠️  Falha ao consolidar delete.js: {e}')


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

class PETOrquestrador:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.progresso: dict = carregar_progresso_pet()

    def executar(self, dry_run: bool = False) -> Dict[str, int]:
        logger.info('=' * 60)
        logger.info('[PET_ORQ] Iniciando pipeline petições')

        itens = PeticaoAPIClient().fetch(self.driver)
        if not itens:
            logger.info('[PET_ORQ] Nenhuma petição encontrada')
            return {'total': 0, 'sucesso': 0, 'erro': 0}

        logger.info(f'[PET_ORQ] {len(itens)} petições carregadas')
        buckets = _classificar(itens)

        print('\n[PET_ORQ] Distribuição por bucket:')
        for nome in ['apagar'] + BUCKETS_ORDEM:
            qtd = len(buckets.get(nome, []))
            if qtd:
                print(f'  {nome}: {qtd}')

        if dry_run:
            return {'total': len(itens), 'sucesso': 0, 'erro': 0}

        # Apagar: executa imediatamente, sem abrir processos
        apagar_itens = buckets.get('apagar', [])
        if apagar_itens:
            logger.info(f'[PET_ORQ] Apagar: {len(apagar_itens)} itens → delete.js')
            _executar_bucket_apagar(apagar_itens)

        # Executar sempre na ordem padrão dos buckets
        ordem = [n for n in BUCKETS_ORDEM if buckets.get(n)]
        stats = {'total': len(itens), 'sucesso': 0, 'erro': 0}

        for nome_bucket in ordem:
            itens_bucket = buckets.get(nome_bucket, [])
            if not itens_bucket:
                continue
            logger.info(f'\n[PET_ORQ] >>> Bucket "{nome_bucket}" ({len(itens_bucket)} itens)')
            try:
                if nome_bucket == 'analise':
                    r = _executar_bucket_analise(self.driver, itens_bucket, self.progresso)
                else:
                    r = _executar_bucket_normal(self.driver, nome_bucket, itens_bucket,
                                                self.progresso)
                stats['sucesso'] += r['sucesso']
                stats['erro'] += r['erro']
            except RuntimeError as e:
                if 'RESTART_PET' in str(e):
                    logger.error(f'[RESTART] {e}')
                    raise
                stats['erro'] += 1

        if apagar_itens:
            logger.info('[PET_ORQ] Consolidando delete.js e gerando bookmarklet')
            _consolidar_delete_bookmarklet()

        logger.info(f'\n[PET_ORQ] Total: {stats["total"]} | '
                    f'Sucesso: {stats["sucesso"]} | Erro: {stats["erro"]}')
        logger.info('=' * 60)
        return stats


def executar_fluxo_pet(driver: WebDriver) -> bool:
    """Entry point do pipeline de petições (compatível com x.py)."""
    try:
        orq = PETOrquestrador(driver)
        stats = orq.executar()
        return stats['erro'] == 0
    except RuntimeError as e:
        if 'RESTART_PET' in str(e):
            raise
        logger.error(f'[PET_FLUXO] Erro fatal: {e}')
        return False
