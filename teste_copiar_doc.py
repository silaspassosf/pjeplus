#!/usr/bin/env python3
"""
Teste da função copiarDOC para extrair texto de documentos PDF no PJe
"""

import time
from Fix import driver_pc, login_pc, copiarDOC

def testar_copiar_doc():
    """Testa a função copiarDOC no processo atual"""
    
    print("[TESTE] Iniciando teste da função copiarDOC...")
    
    # 1. Inicializar driver e fazer login
    driver = driver_pc()
    if not driver:
        print("[TESTE][ERRO] Falha ao inicializar driver.")
        return
    
    try:
        print("[TESTE] Fazendo login...")
        login_pc(driver)
        print("[TESTE] Login realizado com sucesso.")
        
        # 2. Navegar para o processo de teste
        url_teste = "https://pje.trt2.jus.br/pjekz/processo/2108106/detalhe"
        print(f"[TESTE] Navegando para: {url_teste}")
        driver.get(url_teste)
        time.sleep(3)
        
        # 3. Tentar extrair o ID do documento ativo (você mencionou 402213344)
        documento_id = "402213344"
        print(f"[TESTE] Tentando extrair texto do documento ID: {documento_id}")
        
        # 4. Chamar a função copiarDOC
        conteudo = copiarDOC(driver, documento_id)
        
        if conteudo:
            print(f"[TESTE] ✅ Extração bem-sucedida!")
            print(f"[TESTE] Tamanho do texto: {len(conteudo)} caracteres")
            print(f"[TESTE] Início do texto: {conteudo[:200]}...")
            
            # Verificar se contém a frase esperada
            if "bloqueio de valores realizado, ora" in conteudo.lower():
                print("[TESTE] ✅ Frase de referência encontrada!")
            else:
                print("[TESTE] ⚠️ Frase de referência NÃO encontrada")
                
        else:
            print("[TESTE] ❌ Falha na extração")
        
        print("[TESTE] Mantendo janela aberta para conferência manual...")
        input("Pressione Enter para finalizar...")
        
    except Exception as e:
        print(f"[TESTE][ERRO] Erro durante o teste: {e}")
    finally:
        # Não fechar o driver para permitir conferência manual
        pass

if __name__ == "__main__":
    testar_copiar_doc()
