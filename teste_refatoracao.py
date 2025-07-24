"""
Teste para verificar se a refatoração do listaexec funcionou corretamente.
"""

def teste_imports():
    """Testa se todos os imports funcionam corretamente"""
    try:
        print("Testando import da função principal...")
        from listaexec import listaexec
        print("✓ Import de listaexec funcionou!")
        
        print("Testando imports dos módulos...")
        from listaexec_modules.buscar_medidas import buscar_medidas_executorias
        print("✓ Import de buscar_medidas funcionou!")
        
        from listaexec_modules.alvara_core import processar_alvara
        print("✓ Import de alvara_core funcionou!")
        
        from listaexec_modules.alvara_utils import converter_valor_para_float
        print("✓ Import de alvara_utils funcionou!")
        
        from listaexec_modules.file_utils import salvar_alvaras_processados_no_arquivo
        print("✓ Import de file_utils funcionou!")
        
        from listaexec_modules.gigs_utils import navegar_para_pagamentos
        print("✓ Import de gigs_utils funcionou!")
        
        print("\n🎉 Todos os imports funcionaram! A refatoração foi bem-sucedida!")
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    teste_imports()
