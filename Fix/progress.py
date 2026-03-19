#!/usr/bin/env python3
"""
Sistema de Progresso Unificado - API Principal
Gerenciamento centralizado de progresso com persistência em progresso.json
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .progress_models import (
    StatusModulo, NivelLog, Checkpoint, StatusModuloData, RegistroLog
)
import logging

logger = logging.getLogger(__name__)


class ProgressoUnificado:
    """Gerenciador centralizado de progresso."""

    def __init__(self, arquivo_progresso: Path = Path('status_execucao.json')) -> None:
        """
        Inicializa gerenciador.

        Args:
            arquivo_progresso: Caminho do arquivo progresso.json
        """
        self.arquivo = arquivo_progresso
        self.modulos: Dict[str, StatusModuloData] = {}
        self.logs: List[RegistroLog] = []
        self.session_id: str = self._gerar_session_id()
        self.inicio: datetime = datetime.now()
        self._carrega_existente()

    def _gerar_session_id(self) -> str:
        """Gera ID único da sessão."""
        return f"sess_{uuid.uuid4().hex[:16]}"

    def _carrega_existente(self):
        """Carrega progresso existente se arquivo existe."""
        if self.arquivo.exists():
            try:
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.session_id = data.get('metadata', {}).get('session_id', self.session_id)
                    self.logs = [RegistroLog(**log) for log in data.get('logs', [])]
                    # Não recarrega modulos - deve ser feito explicitamente
            except Exception as e:
                logger.warning(f"Não foi possível carregar progresso existente: {e}")

    def registrar_modulo(self, nome_modulo: str, total_items: int) -> None:
        """
        Registra um módulo com total de items.

        Args:
            nome_modulo: Nome do módulo (PRAZO, MANDADO, PEC, SISB)
            total_items: Total de items a processar
        """
        self.modulos[nome_modulo] = StatusModuloData(
            status=StatusModulo.EmProgresso,
            total=total_items
        )
        self._registrar_log(
            modulo=nome_modulo,
            nivel=NivelLog.INFO,
            mensagem=f"Módulo {nome_modulo} iniciado com {total_items} items"
        )
        logger.info(f"Módulo {nome_modulo} registrado com {total_items} items")

    def atualizar(
        self,
        nome_modulo: str,
        processados: Optional[int] = None,
        item_atual: Optional[str] = None,
        proximo_item: Optional[str] = None,
        erro: bool = False
    ) -> None:
        """
        Atualiza progresso de um módulo.

        Args:
            nome_modulo: Nome do módulo
            processados: Items processados (incrementa se None)
            item_atual: Item sendo processado
            proximo_item: Próximo item
            erro: Se ocorreu erro
        """
        if nome_modulo not in self.modulos:
            raise ValueError(f"Módulo {nome_modulo} não registrado")

        status = self.modulos[nome_modulo]

        if processados is not None:
            status.processados = processados
        else:
            status.processados += 1

        if erro:
            status.erros += 1

        # Atualizar checkpoint
        if item_atual:
            status.checkpoint = Checkpoint(
                ultimo_item=item_atual,
                timestamp=datetime.now().isoformat(),
                proximo=proximo_item
            )

        # Calcular tempo
        status.tempo_decorrido_segundos = int((datetime.now() - self.inicio).total_seconds())

        # Atualizar arquivo
        self.salvar()

    def completar(self, nome_modulo: str, sucesso: bool = True) -> None:
        """Marca módulo como completo."""
        if nome_modulo not in self.modulos:
            raise ValueError(f"Módulo {nome_modulo} não registrado")

        status = self.modulos[nome_modulo]
        status.status = StatusModulo.Completo if sucesso else StatusModulo.Falhado
        status.tempo_decorrido_segundos = int((datetime.now() - self.inicio).total_seconds())

        self._registrar_log(
            modulo=nome_modulo,
            nivel=NivelLog.INFO,
            mensagem=f"Módulo {nome_modulo} finalizado: {status.processados}/{status.total}"
        )
        logger.info(f"Módulo {nome_modulo} completado: {status.processados}/{status.total}")
        self.salvar()

    def pausar_modulo(self, nome_modulo: str) -> None:
        """Pausa execução de módulo."""
        if nome_modulo in self.modulos:
            self.modulos[nome_modulo].status = StatusModulo.Pausado
            self.salvar()

    def retomar_modulo(self, nome_modulo: str) -> None:
        """Retoma execução de módulo."""
        if nome_modulo in self.modulos:
            self.modulos[nome_modulo].status = StatusModulo.EmProgresso
            self.salvar()

    def _registrar_log(
        self,
        modulo: str,
        nivel: NivelLog,
        mensagem: str,
        detalhes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra log estruturado."""
        log = RegistroLog(
            timestamp=datetime.now().isoformat(),
            modulo=modulo,
            nivel=nivel,
            mensagem=mensagem,
            detalhes=detalhes or {}
        )
        self.logs.append(log)

        # Manter últimos 1000 logs
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]

    def salvar(self) -> None:
        """Salva progresso em arquivo."""
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)

        # Calcular resumo
        total_modulos = len(self.modulos)
        completos = sum(1 for m in self.modulos.values() if m.status == StatusModulo.Completo)
        em_progresso = sum(1 for m in self.modulos.values() if m.status == StatusModulo.EmProgresso)

        total_items = sum(m.total for m in self.modulos.values())
        processados = sum(m.processados for m in self.modulos.values())
        percentual_global = (processados / total_items * 100) if total_items > 0 else 0

        data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'versao': '2.0',
                'session_id': self.session_id
            },
            'execution': {
                'status': 'EM_PROGRESSO',
                'inicio': self.inicio.isoformat(),
                'duracao_segundos': int((datetime.now() - self.inicio).total_seconds()),
                'modulo_ativo': next((k for k, v in self.modulos.items() if v.status == StatusModulo.EmProgresso), None),
                'pode_retomar': True
            },
            'modulos': {k: v.to_dict() for k, v in self.modulos.items()},
            'resumo_global': {
                'total_modulos': total_modulos,
                'completos': completos,
                'em_progresso': em_progresso,
                'pausados': sum(1 for m in self.modulos.values() if m.status == StatusModulo.Pausado),
                'falhados': sum(1 for m in self.modulos.values() if m.status == StatusModulo.Falhado),
                'percentual_global': percentual_global,
                'tempo_total_segundos': int((datetime.now() - self.inicio).total_seconds()),
                'tempo_restante_estimado_segundos': 0  # TODO: implementar estimativa
            },
            'logs': [log.to_dict() for log in self.logs[-100:]]  # últimos 100 logs
        }

        with open(self.arquivo, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# Instância global para uso direto
_progresso_global = None

def _get_progresso_global():
    """Obtém instância global do progresso."""
    global _progresso_global
    if _progresso_global is None:
        _progresso_global = ProgressoUnificado()
    return _progresso_global

def registrar_modulo(nome_modulo: str, total_items: int):
    """
    Registra um módulo no sistema de progresso unificado.

    Args:
        nome_modulo: Nome do módulo (ex: 'SISB_SERIES_FILTER')
        total_items: Total de items a processar
    """
    _get_progresso_global().registrar_modulo(nome_modulo, total_items)

def atualizar(
    nome_modulo: str,
    processados: int = None,
    item_atual: str = None,
    proximo_item: str = None,
    erro: bool = False
):
    """
    Atualiza progresso de um módulo.

    Args:
        nome_modulo: Nome do módulo
        processados: Items processados
        item_atual: Item atual sendo processado
        proximo_item: Próximo item
        erro: Se ocorreu erro
    """
    _get_progresso_global().atualizar(
        nome_modulo, processados, item_atual, proximo_item, erro
    )

def completar(nome_modulo: str, sucesso: bool = True):
    """
    Marca módulo como completo.

    Args:
        nome_modulo: Nome do módulo
        sucesso: Se foi bem-sucedido
    """
    _get_progresso_global().completar(nome_modulo, sucesso)