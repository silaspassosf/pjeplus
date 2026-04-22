"""Modelos de dados para o sistema de progresso."""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


class StatusModulo(Enum):
    """Estados possíveis de um módulo."""
    NAOINICIADO = "NAO_INICIADO"
    EmProgresso = "EM_PROGRESSO"
    Pausado = "PAUSADO"
    Completo = "COMPLETO"
    Falhado = "FALHADO"
    Recuperacao = "RECUPERACAO"


class NivelLog(Enum):
    """Níveis de log estruturado."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Checkpoint:
    """Ponto de recuperação para retomar execução."""
    ultimo_item: str
    timestamp: str
    proximo: Optional[str] = None
    contexto: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return asdict(self)


@dataclass
class StatusModuloData:
    """Status de um módulo individual."""
    status: StatusModulo
    processados: int = 0
    total: int = 0
    tempo_decorrido_segundos: int = 0
    erros: int = 0
    checkpoint: Optional[Checkpoint] = None
    detalhes: Dict[str, Any] = field(default_factory=dict)

    @property
    def percentual(self) -> float:
        """Percentual de progresso."""
        if self.total == 0:
            return 0.0
        return (self.processados / self.total) * 100

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        data = asdict(self)
        data['status'] = self.status.value
        data['percentual'] = self.percentual
        if self.checkpoint:
            data['checkpoint'] = self.checkpoint.to_dict()
        return data


@dataclass
class RegistroLog:
    """Registro de log estruturado."""
    timestamp: str
    modulo: str
    nivel: NivelLog
    mensagem: str
    detalhes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Converte nivel string para Enum se necessário."""
        if isinstance(self.nivel, str):
            self.nivel = NivelLog(self.nivel)

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        data = asdict(self)
        data['nivel'] = self.nivel.value
        return data
