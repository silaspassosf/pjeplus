"""Constantes e limites usados pela triagem.

Este arquivo contém apenas valores imutáveis e listas de referência.
"""
SALARIO_MINIMO = 1622.00                          # 2026
ALCADA = SALARIO_MINIMO * 2                        # R$ 3.244,00
RITO_SUMARISSIMO_MAX = SALARIO_MINIMO * 40         # R$ 64.880,00

INTERVALOS_CEP_ZONA_SUL = [
    (4307000, 4314999), (4316000, 4477999), (4603000, 4620999),
    (4624000, 4703999), (4708000, 4967999), (5640000, 5642999),
    (5657000, 5665999), (5692000, 5692999), (5703000, 5743999),
    (5745000, 5750999), (5752000, 5895999),
]

__all__ = [
    'SALARIO_MINIMO', 'ALCADA', 'RITO_SUMARISSIMO_MAX', 'INTERVALOS_CEP_ZONA_SUL'
]
