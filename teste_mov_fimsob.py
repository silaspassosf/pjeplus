# ====================================================================
# TESTE DIRETO MOV_FIMSOB
# Executa apenas o mov_fimsob para investigar o problema das abas
# ====================================================================

import sys
import os
import time

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def testar_mov_fimsob():
    """
    Testa o mov_fimsob diretamente para investigar o problema
    """
    print("="*80)
    print("🔍 TESTE DIRETO: MOV_FIMSOB")
    print("="*80)

    try:
        # Importar mov_fimsob
        from atos import mov_fimsob
        print("✅ mov_fimsob importado com sucesso")

        # Simular um driver (não podemos criar um real aqui)
        # Mas podemos testar a lógica de importação e estrutura
        print("📋 mov_fimsob está disponível para teste com driver real")
        print("🎯 Para testar completamente, use o executor_pec_monitor.py --monitor")

    except Exception as e:
        print(f"❌ Erro ao importar mov_fimsob: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    testar_mov_fimsob()