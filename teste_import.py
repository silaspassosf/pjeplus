import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from Fix.utils_paths import exibir_configuracao_atual
    print("Importação bem-sucedida!")
    exibir_configuracao_atual()
except Exception as e:
    print(f"Erro na importação: {e}")
    import traceback
    traceback.print_exc()