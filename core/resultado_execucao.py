from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from datetime import datetime

@dataclass
class ResultadoExecucao:
    sucesso: bool
    status: str = ""
    erro: Optional[str] = None
    tempo: Optional[float] = None
    detalhes: Optional[Dict[str, Any]] = field(default_factory=dict)
    processos: Optional[int] = None
    loop_prazo: Any = None
    p2b: Any = None
    # Campos extras podem ser adicionados conforme necessário

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        # Remove None para manter compatível com dicts antigos
        return {k: v for k, v in d.items() if v is not None}
