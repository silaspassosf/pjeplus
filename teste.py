#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de extração de dados de processo
URL: https://pje.trt2.jus.br/pjekz/processo/2661854/detalhe
"""

from driver_config import criar_driver, login_func
from Fix import extrair_dados_processo
import time
import sys
import os

def teste_extracao_dados():
    """Testa a extração de dados de um processo específico."""
    driver = None
    try:
        print("[TESTE] Iniciando teste de extração de dados...")
        
        # 1. Criar driver e fazer login
        print("[TESTE] Criando driver...")
        driver = criar_driver()
        
        print("[TESTE] Fazendo login...")
        login_success = login_func(driver)
        if not login_success:
            print("[TESTE][ERRO] Falha no login!")
            return False
        
        # 2. Navegar para o processo específico
        url_processo = "https://pje.trt2.jus.br/pjekz/processo/2661854/detalhe"
        print(f"[TESTE] Navegando para o processo: {url_processo}")
        driver.get(url_processo)
        
        # Aguarda carregamento da página
        time.sleep(5)
        print(f"[TESTE] URL atual: {driver.current_url}")
        
        # 3. Executar extração de dados
        print("[TESTE] Executando extração de dados do processo...")
        dados_extraidos = extrair_dados_processo(driver)
        
        if dados_extraidos:
            print("[TESTE] ✓ Extração de dados executada com sucesso!")
            print("[TESTE] Dados extraídos:")
            print("-" * 50)
            
            # Exibir dados de forma organizada
            if 'numero' in dados_extraidos:
                print(f"Número: {dados_extraidos['numero']}")
            if 'id' in dados_extraidos:
                print(f"ID: {dados_extraidos['id']}")
            if 'partes' in dados_extraidos:
                partes = dados_extraidos['partes']
                if 'ativas' in partes and partes['ativas']:
                    print(f"Autor: {partes['ativas'][0].get('nome', 'N/A')}")
                if 'passivas' in partes and partes['passivas']:
                    print(f"Réu: {partes['passivas'][0].get('nome', 'N/A')}")
            if 'valor' in dados_extraidos:
                print(f"Valor: R$ {dados_extraidos['valor']}")
            if 'magistrado' in dados_extraidos:
                print(f"Magistrado: {dados_extraidos['magistrado']}")
            if 'juizo' in dados_extraidos:
                print(f"Juízo: {dados_extraidos['juizo']}")
                
            print("-" * 50)
            print(f"[TESTE] Total de campos extraídos: {len(dados_extraidos)}")
        else:
            print("[TESTE] ✗ Falha na extração de dados")
            return False
        
        # 4. Aguardar para verificar resultado
        print("[TESTE] Teste concluído. Pressione Enter para fechar o navegador...")
        input()
        
        return True
        
    except Exception as e:
        print(f"[TESTE][ERRO] Exceção durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            try:
                print("[TESTE] Fechando navegador...")
                driver.quit()
            except Exception as e:
                print(f"[TESTE][WARN] Erro ao fechar driver: {e}")

if __name__ == "__main__":
    sucesso = teste_extracao_dados()
    if sucesso:
        print("[TESTE] Teste finalizado com sucesso!")
    else:
        print("[TESTE] Teste finalizado com erro!")
