import logging
from typing import List, Dict, Any
from .api_client import AtividadePEC

logger = logging.getLogger(__name__)

class PECClassificador:
    BUCKETS_ORDEM = ['carta', 'comunicacoes', 'sobrestamento', 'sob', 'outros', 'sisbajud']

    @classmethod
    def classificar(cls, atividades: List[AtividadePEC]) -> Dict[str, List[AtividadePEC]]:
        buckets = {nome: [] for nome in cls.BUCKETS_ORDEM}
        for atv in atividades:
            acoes = atv.acoes
            if not acoes:
                continue
            acao_nome = cls._get_acao_nome(acoes[0])
            bucket = cls._mapear_acao_para_bucket(acao_nome)
            buckets[bucket].append(atv)
            logger.debug(f"[CLASS] {atv.numero_processo} -> {bucket} ({acao_nome})")
        return buckets

    @staticmethod
    def _get_acao_nome(acao) -> str:
        if callable(acao):
            return getattr(acao, '__name__', str(acao))
        elif isinstance(acao, (list, tuple)) and acao:
            return PECClassificador._get_acao_nome(acao[0])
        return str(acao)

    @staticmethod
    def _mapear_acao_para_bucket(acao_nome: str) -> str:
        nome = acao_nome.lower()
        if any(x in nome for x in ['minuta_bloqueio', 'processar_ordem_sisbajud', 'sisb']):
            return 'sisbajud'
        elif any(x in nome for x in ['carta', 'analisar_documentos_pos_carta']):
            return 'carta'
        elif any(x in nome for x in ['def_sob', 'sobrestamento']):
            return 'sobrestamento'
        elif any(x in nome for x in ['mov_sob', 'def_chip', 'mov_aud']):
            return 'sob'
        elif any(x in nome for x in ['pec_', 'ato_citacao', 'ato_intimacao', 'wrapper']):
            return 'comunicacoes'
        else:
            return 'outros'
