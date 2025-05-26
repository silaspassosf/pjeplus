# teste_bacen.py
# Script de teste para verificar as automações BACEN/SISBAJUD

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bacen import *
import time

def teste_configuracao():
    """Testa se as configurações estão corretas"""
    print("=== TESTE DE CONFIGURAÇÃO ===")
    print(f"Juiz Default: {CONFIG.get('juiz_default', 'NÃO CONFIGURADO')}")
    print(f"Vara Default: {CONFIG.get('vara_default', 'NÃO CONFIGURADO')}")
    print(f"Banco Preferido: {CONFIG.get('banco_preferido', 'NÃO CONFIGURADO')}")
    print(f"Agência Preferida: {CONFIG.get('agencia_preferida', 'NÃO CONFIGURADO')}")
    print(f"Teimosinha: {CONFIG.get('teimosinha', 'NÃO CONFIGURADO')}")
    print()

def teste_dados_processo():
    """Simula dados de processo para teste"""
    global processo_dados_extraidos
    processo_dados_extraidos = {
        'numero': '0000000-00.2024.5.02.0000',
        'partes': {
            'ativas': [
                {
                    'nome': 'JOÃO DA SILVA TESTE',
                    'documento': '123.456.789-00'
                }
            ],
            'passivas': [
                {
                    'nome': 'EMPRESA TESTE LTDA',
                    'documento': '12.345.678/0001-90'
                }
            ]
        }
    }
    print("=== DADOS DE TESTE CONFIGURADOS ===")
    print(f"Processo: {processo_dados_extraidos['numero']}")
    print(f"Parte Ativa: {processo_dados_extraidos['partes']['ativas'][0]['nome']}")
    print(f"Parte Passiva: {processo_dados_extraidos['partes']['passivas'][0]['nome']}")
    print()

def teste_firefox_sisbajud():
    """Testa a abertura do Firefox SISBAJUD"""
    print("=== TESTE DE ABERTURA FIREFOX SISBAJUD ===")
    try:
        driver = driver_firefox_sisbajud(headless=False)
        print("✓ Driver Firefox SISBAJUD criado com sucesso")
        
        driver.get('https://sisbajud.cnj.jus.br/')
        print("✓ SISBAJUD carregado")
        
        time.sleep(3)
        
        # Testar injeção do menu Kaizen
        injetar_menu_kaizen_sisbajud(driver)
        print("✓ Menu Kaizen injetado")
        
        # Testar dados de login
        dados_login(driver)
        print("✓ Dados de login exibidos")
        
        # Testar monitoramento
        monitor_janela_sisbajud(driver)
        print("✓ Monitoramento de janelas ativado")
        
        # Testar integração de storage
        integrar_storage_processo(driver)
        print("✓ Storage do processo integrado")
        
        print("\n✓ TODOS OS TESTES PASSARAM!")
        print("Pressione Enter para fechar...")
        input()
        
        driver.quit()
        
    except Exception as e:
        print(f"✗ ERRO NO TESTE: {e}")
        return False
    
    return True

def main():
    print("INICIANDO TESTES DAS AUTOMAÇÕES BACEN/SISBAJUD")
    print("=" * 50)
    
    teste_configuracao()
    teste_dados_processo()
    
    resposta = input("Deseja testar a abertura do Firefox SISBAJUD? (s/n): ")
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        teste_firefox_sisbajud()
    else:
        print("Teste de Firefox ignorado.")
    
    print("\nTestes concluídos!")

if __name__ == '__main__':
    main()
