"""Fachada do pacote `triagem`.

Exporta `triagem_peticao` do serviço interno `triagem.service`.
Mantém contrato: `from triagem import triagem_peticao`.
"""
from .service import triagem_peticao

__all__ = ["triagem_peticao"]
