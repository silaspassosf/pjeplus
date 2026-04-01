import logging
from typing import Dict, List
from .api_client import PECAPIClient, AtividadePEC
from .classificador import PECClassificador
from .executor_individual import PECExecutorIndividual

def carregar_progresso_pec():
    return {}

logger = logging.getLogger(__name__)

class PECOrquestrador:
    def __init__(self, driver):
        self.driver = driver
        self.api = PECAPIClient()
        self.classificador = PECClassificador()
        self.progresso = carregar_progresso_pec()

    def executar(self, dry_run: bool = False) -> Dict[str, int]:
        logger.info("=" * 60)
        logger.info("[ORQUESTRADOR] Iniciando pipeline PEC simplificado")
        logger.info("=" * 60)
        print("[PECOrquestrador] Chamando fetch_atividades_vencidas...")
        atividades = self.api.fetch_atividades_vencidas(self.driver)
        print(f"[PECOrquestrador] Atividades retornadas: {len(atividades)}")
        if not atividades:
            logger.info("[ORQUESTRADOR] Nenhuma atividade encontrada")
            print("[PECOrquestrador] Nenhuma atividade encontrada pelo fetch.")
            return {'total': 0, 'sucesso': 0, 'erro': 0}
        buckets = self.classificador.classificar(atividades)
        # Loga todos os buckets e suas quantidades antes de executar
        print("\n[PECOrquestrador] Buckets prontos para execução:")
        for nome in PECClassificador.BUCKETS_ORDEM:
            items = buckets.get(nome, [])
            print(f"  {nome}: {len(items)}")
        if dry_run:
            self._log_dry_run(buckets)
            return {'total': len(atividades), 'sucesso': 0, 'erro': 0}
        stats = {'total': len(atividades), 'sucesso': 0, 'erro': 0}
        executor = PECExecutorIndividual(self.driver, self.progresso)
        try:
            for bucket_nome in PECClassificador.BUCKETS_ORDEM:
                items = buckets.get(bucket_nome, [])
                if not items:
                    continue
                logger.info(f"\n[ORQUESTRADOR] >>> Processando bucket '{bucket_nome}' ({len(items)} itens)")
                for idx, atv in enumerate(items, 1):
                    logger.info(f"[{bucket_nome}] {idx}/{len(items)}: {atv.numero_processo}")
                    try:
                        if executor.processar_atividade(atv):
                            stats['sucesso'] += 1
                        else:
                            stats['erro'] += 1
                    except Exception as e:
                        if 'RESTART_PEC' in str(e):
                            logger.error(f"[RESTART] Detectado em {atv.numero_processo}, reiniciando fluxo...")
                            executor.cleanup()
                            raise
                        stats['erro'] += 1
        finally:
            executor.cleanup()
            executor.finalizar()
        logger.info("\n" + "=" * 60)
        logger.info(f"[RESUMO] Total: {stats['total']} | Sucesso: {stats['sucesso']} | Erro: {stats['erro']}")
        logger.info("=" * 60)
        return stats

    def _log_dry_run(self, buckets: Dict[str, List[AtividadePEC]]):
        logger.info("[DRY RUN] Distribuição prevista:")
        for nome, items in buckets.items():
            if items:
                logger.info(f"  {nome}: {len(items)}")
                for atv in items[:3]:
                    logger.info(f"    - {atv.numero_processo}: {atv.observacao[:50]}")

def executar_fluxo_novo_simplificado(driver) -> bool:
    try:
        orq = PECOrquestrador(driver)
        stats = orq.executar(dry_run=False)
        return stats['erro'] == 0
    except Exception as e:
        if 'RESTART_PEC' in str(e):
            raise
        logger.error(f"[FLUXO] Erro fatal: {e}")
        return False
