#!/usr/bin/env python3
"""
Teste da função _formatar_nome_acao
"""

# Simular import da função
import sys
sys.path.append('PEC')

from processamento_buckets import _formatar_nome_acao

# Testes
print("Testando _formatar_nome_acao:")

# Teste 1: Lista com lambda + ato_idpj (como no caso do log)
acao_teste1 = [
    lambda driver: None,  # Simula a lambda de criar_gigs
    lambda driver: None   # Simula ato_idpj wrapper
]
resultado1 = _formatar_nome_acao(acao_teste1)
print(f"Lista [lambda, lambda]: {resultado1}")

# Teste 2: Ação única
acao_teste2 = lambda driver: None
resultado2 = _formatar_nome_acao(acao_teste2)
print(f"Lambda única: {resultado2}")

# Teste 3: String
acao_teste3 = "teste"
resultado3 = _formatar_nome_acao(acao_teste3)
print(f"String: {resultado3}")

print("Teste concluído!")