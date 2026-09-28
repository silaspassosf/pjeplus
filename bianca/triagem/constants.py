# -*- coding: utf-8 -*-
"""
bianca/triagem/constants.py -- Constantes de dominio para o modulo de triagem.

Importa e re-exporta de ``bianca.config`` as constantes necessarias
para as checagens de triagem:

- Zonas de CEP (Zona Sul, Zona Leste, Rui Barbosa)
- Valores financeiros (salario minimo, alcada, rito sumarissimo)
- URLs do PJe (lista de triagem, base)
"""

from bianca.config import (
    ZONA_SUL_CEPS,
    ZONA_LESTE_CEPS,
    RUI_BARBOSA_CEPS,
    SALARIO_MINIMO,
    ALCADA,
    RITO_SUMARISSIMO_MAX,
    URL_LISTA_TRIAGEM,
    URL_PJE_BASE,
)
