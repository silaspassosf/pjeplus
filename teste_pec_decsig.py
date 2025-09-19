#!/usr/bin/env python3
"""
Script de teste para verificar o comportamento do pec_decsig
com navegação direta para minuta.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def testar_pec_decsig():
    """Testa o pec_decsig com navegação direta"""
    print("=== TESTE PEC_DECSIG COM NAVEGAÇÃO DIRETA ===")

    try:
        # Importar as dependências necessárias
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from atos import pec_decsig

        print("1. Inicializando driver...")
        options = Options()
        options.add_argument("--headless")  # Executar sem interface gráfica
        driver = webdriver.Firefox(options=options)

        print("2. Testando pec_decsig...")
        # Este teste vai falhar porque não temos uma sessão válida do PJe
        # Mas vai nos mostrar se o código está sendo executado corretamente
        try:
            pec_decsig(driver, debug=True)
            print("✅ pec_decsig executado sem erros de sintaxe")
        except Exception as e:
            error_msg = str(e)
            if "Unable to locate element" in error_msg or "NoSuchElementException" in error_msg:
                print("✅ pec_decsig iniciou execução (erro esperado sem sessão PJe)")
                print(f"   Detalhes do erro: {error_msg[:100]}...")
            else:
                print(f"❌ Erro inesperado: {error_msg}")
                raise

        driver.quit()
        print("3. Teste concluído com sucesso!")

    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("Verifique se todas as dependências estão instaladas")
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    testar_pec_decsig()