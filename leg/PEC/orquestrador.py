"""
PEC/orquestrador.py — Orquestrador PEC simplificado

Fluxo: API → regras_pec (match + bucket) → execução sequencial por bucket.
"""
import logging
from datetime import date, timedelta
from typing import Dict

from .api_client import PECAPIClient
from .regras_pec import BUCKET_ORDEM, determinar_regra
from .helpers import _montar_url_processo, _fechar_abas_extras
from .core_progresso import (
    carregar_progresso_pec,
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
)

logger = logging.getLogger(__name__)


def _aguardar_carregamento(driver) -> None:
    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, timeout=10)
    except Exception:
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )


class PECOrquestrador:
    def __init__(self, driver):
        self.driver = driver
        self.api = PECAPIClient()

    def executar(self, dry_run: bool = False, filtro_d1: bool = False) -> Dict[str, int]:
        atividades = self.api.fetch_atividades_vencidas(self.driver)

        if filtro_d1:
            data_d1 = (date.today() - timedelta(days=1)).isoformat()
            antes = len(atividades)
            # Filtrar apenas atividades com prazo D-1 (somente por data)
            atividades = [a for a in atividades if (a.data_prazo or '')[:10] == data_d1]
            logger.info(f'[PEC] D-1 ({data_d1}): {antes} -> {len(atividades)} (filtrado por data)')
        else:
            logger.info(f'[PEC] Filtro D-1 OFF — processando todas: {len(atividades)}')

        if not atividades:
            return {'total': 0, 'sucesso': 0, 'erro': 0}

        # Agrupar por bucket via REGRAS
        buckets: Dict[str, list] = {b: [] for b in BUCKET_ORDEM}
        for atv in atividades:
            match = determinar_regra(atv.observacao or '')
            if match:
                _, bucket, acao = match
                buckets[bucket].append((atv, acao))
            else:
                logger.warning(f'[PEC] Sem regra: {atv.observacao!r} — {atv.numero_processo}')

        if buckets.get('comunicacoes'):
            buckets['comunicacoes'].sort(
                key=lambda item: 0 if 'xs sigilo' in (getattr(item[0], 'observacao', '') or '').lower() else 1
            )

        if dry_run:
            self._log_dry_run(buckets)
            return {'total': len(atividades), 'sucesso': 0, 'erro': 0}

        progresso = carregar_progresso_pec()
        stats = {'total': len(atividades), 'sucesso': 0, 'erro': 0}

        for bucket in BUCKET_ORDEM:
            for atv, acao in buckets[bucket]:
                if processo_ja_executado_pec(atv.numero_processo, progresso):
                    logger.info(f'[PEC] Skip já executado: {atv.numero_processo}')
                    continue

                try:
                    if atv.id_processo:
                        url = f'https://pje.trt2.jus.br/pjekz/processo/{atv.id_processo}/detalhe/'
                    else:
                        url = _montar_url_processo(atv.numero_processo or '')
                    self.driver.get(url)
                    _aguardar_carregamento(self.driver)
                    if acao is None:
                        logger.warning(f'[PEC] Acao None: {atv.numero_processo} ({atv.observacao!r})')
                        stats['erro'] += 1
                        marcar_processo_executado_pec(atv.numero_processo, progresso, status='ERRO')
                        continue
                    if isinstance(acao, tuple):
                        for f in acao:
                            f(self.driver, atv)
                    else:
                        acao(self.driver, atv)
                    stats['sucesso'] += 1
                    logger.info(f'[OK] {atv.numero_processo}')
                    marcar_processo_executado_pec(atv.numero_processo, progresso)
                except Exception as e:
                    if 'RESTART_PEC' in str(e) or 'acesso negado' in str(e).lower():
                        raise
                    stats['erro'] += 1
                    logger.error(f'[FAIL] {atv.numero_processo}: {e}')
                    try:
                        marcar_processo_executado_pec(atv.numero_processo, progresso, status='ERRO')
                    except Exception:
                        pass
                finally:
                    _fechar_abas_extras(self.driver)

        logger.info(f'[RESUMO] Total: {stats["total"]} | Sucesso: {stats["sucesso"]} | Erro: {stats["erro"]}')
        return stats

    def _log_dry_run(self, buckets: Dict[str, list]):
        logger.info("[DRY RUN] Distribuicao prevista:")
        for nome, items in buckets.items():
            if items:
                logger.info(f"  {nome}: {len(items)}")
                for atv, acao in items[:3]:
                    acao_nome = getattr(acao, '__name__', repr(acao))
                    logger.info(f"    - {atv.numero_processo}: {atv.observacao[:50]} -> {acao_nome}")

def executar_fluxo_novo_simplificado(driver, filtro_d1: bool = True) -> dict:
    try:
        orq = PECOrquestrador(driver)
        stats = orq.executar(dry_run=False, filtro_d1=filtro_d1)
        stats['sucesso'] = stats['erro'] == 0
        return stats
    except Exception as e:
        if 'RESTART_PEC' in str(e):
            raise
        logger.error(f'[FLUXO] Erro fatal: {e}')
        return {'total': 0, 'sucesso': False, 'erro': 1}
