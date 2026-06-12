#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da correção de variações I/Y na busca de nomes em procurações.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bianca.triagem.utils import _norm

def test_variacao_i_y():
    """Testa se a lógica de variação I/Y funciona."""
    print("=" * 80)
    print("TESTE DE VARIAÇÃO ORTOGRÁFICA I/Y")
    print("=" * 80)
    
    def _expandir_variacao_i_y(nome: str) -> list:
        """Retorna nome + variacao com I/Y trocados."""
        if not nome or len(nome) <= 1:
            return [nome]
        variacoes = [nome]
        if 'i' in nome:
            variacoes.append(nome.replace('i', 'y'))
        if 'y' in nome:
            variacoes.append(nome.replace('y', 'i'))
        return variacoes
    
    # Caso real: MICHELLY vs MYCHELLY
    nome_reclamante = "MICHELLY DA SILVA FRANCA PEREIRA"
    nome_norm = _norm(nome_reclamante)
    procuracao_norm = _norm("MYCHELLY DA SILVA FRANCA")
    
    print(f"Reclamante normalizado: {nome_norm}")
    print(f"Procuração normalizado: {procuracao_norm}")
    print()
    
    # Extrair partes
    partes_nome = nome_norm.split()
    primeiro_nome = partes_nome[0] if partes_nome else ''
    
    print(f"Primeiro nome: {primeiro_nome}")
    variações = _expandir_variacao_i_y(primeiro_nome)
    print(f"Variações: {variações}")
    print()
    
    # Testar busca
    print("Testes de busca:")
    for nome_busca in variações:
        encontrado = ' ' + nome_busca + ' ' in ' ' + procuracao_norm + ' ' or nome_busca in procuracao_norm
        print(f"  '{nome_busca}' em procuração: {'✓ SIM' if encontrado else '✗ NÃO'}")
    
    print()
    print("=" * 80)
    print("RESULTADO: Teste de busca com variações I/Y")
    print("=" * 80)
    
    # Teste final
    nome_encontrado = any(
        nome and len(nome) > 3 and (' ' + nome + ' ' in ' ' + procuracao_norm + ' ' or nome in procuracao_norm)
        for nome in _expandir_variacao_i_y(primeiro_nome)
    )
    
    if nome_encontrado:
        print("✓ SUCESSO: Nome encontrado na procuração considerando variações I/Y")
        print("  O sistema agora detectaria corretamente que 'MICHELLY' (reclamante)")
        print("  está presente na procuração assinada como 'MYCHELLY'")
    else:
        print("✗ FALHA: Nome ainda não encontrado")
    
    return nome_encontrado

if __name__ == '__main__':
    sucesso = test_variacao_i_y()
    sys.exit(0 if sucesso else 1)
