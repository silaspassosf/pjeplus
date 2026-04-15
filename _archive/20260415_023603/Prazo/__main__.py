import logging
logger = logging.getLogger(__name__)

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
    
    # Executar função principal
    executar_loop_principal()
