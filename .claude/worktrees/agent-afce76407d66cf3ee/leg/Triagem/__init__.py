"""Fachada do pacote `triagem`.

Exporta `triagem_peticao` do serviço interno `triagem.service`.
Mantém contrato: `from triagem import triagem_peticao`.
"""
from .api import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial
from .acoes import acao_bucket_a, acao_bucket_b, acao_bucket_c, acao_bucket_d
from .citacao import def_citacao
from .driver import criar_driver_e_logar
from .runner import run_triagem
from .service import triagem_peticao

__all__ = [
    "triagem_peticao",
    "buscar_lista_triagem",
    "enriquecer_processo",
    "_is_triagem_inicial",
    "def_citacao",
    "acao_bucket_a",
    "acao_bucket_b",
    "acao_bucket_c",
    "acao_bucket_d",
    "criar_driver_e_logar",
    "run_triagem",
]
