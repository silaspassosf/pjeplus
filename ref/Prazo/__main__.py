"""
Script principal para execução do Módulo Prazo
Integra loop.py + p2b refatorado para processamento completo
"""

import sys
import os

# Adicionar pasta raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar função principal do módulo
from Prazo import executar_loop_principal

if __name__ == "__main__":
    print("=" * 70)
    print(" MÓDULO PRAZO - PROCESSAMENTO COMPLETO")
    print("=" * 70)
    print()
    print(" Fluxo de Execução:")
    print("  1️⃣  Processamento em lote (loop_prazo)")
    print("      ↳ Painel 14 (Análise)")
    print("      ↳ Painel 8 (Cumprimento de providências)")
    print()
    print("  2️⃣  Processamento individual (fluxo_prazo)")
    print("      ↳ Itera processos da lista")
    print("      ↳ Executa fluxo_pz para cada processo")
    print()
    print("=" * 70)
    print()
    
    # Executar função principal
    executar_loop_principal()
