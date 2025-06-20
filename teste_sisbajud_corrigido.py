#!/usr/bin/env python3
# teste_sisbajud_corrigido.py
"""
Script de teste para validar o fluxo SISBAJUD independente
com login automático via AHK usando loginsisb_avancado.ahk
"""

import sys
import os

# Adicionar o diretório atual ao path para importar as funções
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("🧪 TESTE SISBAJUD INDEPENDENTE - VERSÃO CORRIGIDA")
    print("=" * 60)
    print()
    
    try:
        # Importar as funções do bacen.py
        from bacen import main_teste_sisbajud, obter_caminho_autohotkey
        
        # Testar se a função de obter caminho do AHK funciona
        print("🔍 Testando extração do caminho do AutoHotkey...")
        caminho_ahk = obter_caminho_autohotkey()
        if caminho_ahk:
            print(f"✅ Caminho do AutoHotkey encontrado: {caminho_ahk}")
        else:
            print("⚠️ Caminho do AutoHotkey não encontrado, será usado fallback")
        print()
        
        # Verificar se o script AHK avançado existe
        script_ahk = os.path.join(os.path.dirname(__file__), 'loginsisb_avancado.ahk')
        if os.path.exists(script_ahk):
            print(f"✅ Script AHK avançado encontrado: {script_ahk}")
        else:
            print(f"❌ Script AHK avançado não encontrado: {script_ahk}")
            # Verificar script simples como fallback
            script_simples = os.path.join(os.path.dirname(__file__), 'loginsisb.ahk')
            if os.path.exists(script_simples):
                print(f"⚠️ Script AHK simples encontrado como fallback: {script_simples}")
            else:
                print("❌ Nenhum script AHK encontrado!")
        print()
        
        # Executar o teste principal
        print("🚀 Iniciando teste do SISBAJUD...")
        print("📋 Ordem de tentativas de login:")
        print("   1. Cookies salvos")
        print("   2. AutoHotkey (loginsisb_avancado.ahk)")
        print("   3. Login manual")
        print()
        
        # Executar o main de teste
        main_teste_sisbajud()
        
    except ImportError as e:
        print(f"❌ Erro ao importar funções: {e}")
        print("💡 Verifique se o arquivo bacen.py está no mesmo diretório")
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
