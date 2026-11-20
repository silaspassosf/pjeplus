# -*- coding: utf-8 -*-
"""bianca/triagem/__init__.py -- Facade do modulo de triagem."""

from bianca.triagem.runner import run_triagem
from bianca.triagem.service import triagem_peticao
from bianca.triagem.api import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial
from bianca.triagem.acoes import acao_bucket_a, acao_bucket_b, acao_bucket_c, acao_bucket_d
from bianca.triagem.citacao import def_citacao

__all__ = [
    "run_triagem", "triagem_peticao",
    "buscar_lista_triagem", "enriquecer_processo", "_is_triagem_inicial",
    "def_citacao",
    "acao_bucket_a", "acao_bucket_b", "acao_bucket_c", "acao_bucket_d",
]
