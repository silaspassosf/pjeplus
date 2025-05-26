"""
Teste da nova função extrair_documento_silencioso() baseada na técnica MaisPje
"""

from Fix import extrair_documento_silencioso, extrair_documento_modal_free
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def teste_extracao_silenciosa():
    """Testa se a nova extração silenciosa funciona sem abrir modal visível"""
    
    print("=== TESTE EXTRAÇÃO SILENCIOSA ===")
    
    # Configurar Chrome
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("1. Navegando para PJe...")
        driver.get("https://pje.trt2.jus.br/pjekz/login.seam")
        
        print("2. Aguardando login manual...")
        print("   Por favor, faça login e navegue até um processo com documentos")
        print("   Pressione ENTER quando estiver pronto para testar")
        input()
        
        print("3. Testando extração silenciosa...")
        texto_silencioso = extrair_documento_silencioso(driver, timeout=10)
        
        if texto_silencioso:
            print(f"✅ SUCESSO! Extraído silenciosamente: {len(texto_silencioso)} caracteres")
            print(f"   Primeiros 200 chars: {texto_silencioso[:200]}...")
        else:
            print("❌ FALHA na extração silenciosa")
        
        print("\n4. Testando função combinada...")
        texto_combinado, analise = extrair_documento_modal_free(driver, timeout=10)
        
        if texto_combinado:
            print(f"✅ SUCESSO! Função combinada: {len(texto_combinado)} caracteres")
        else:
            print("❌ FALHA na função combinada")
            
        print("\n5. Teste concluído. Pressione ENTER para fechar")
        input()
        
    except Exception as e:
        print(f"ERRO durante teste: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    teste_extracao_silenciosa()
