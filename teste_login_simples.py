#!/usr/bin/env python3
# teste_login_simples.py
"""
Teste SIMPLES para testar APENAS o loginsisb.ahk
Foco total em um único arquivo funcional
"""

import os
import subprocess
import time

def main():
    print("=" * 60)
    print("🎯 TESTE SIMPLES - APENAS loginsisb.ahk")
    print("=" * 60)
    print()
    
    # Verificar se loginsisb.ahk existe
    script_ahk = "loginsisb.ahk"
    
    if not os.path.exists(script_ahk):
        print(f"❌ Arquivo {script_ahk} não encontrado!")
        return
    
    print(f"✅ Arquivo {script_ahk} encontrado")
    
    # Verificar AutoHotkey
    ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
    
    if not os.path.exists(ahk_exe):
        print(f"❌ AutoHotkey não encontrado em: {ahk_exe}")
        return
    
    print(f"✅ AutoHotkey encontrado: {ahk_exe}")
    print()
    
    # Instruções para o usuário
    print("📋 INSTRUÇÕES:")
    print("1. Abra o SISBAJUD no navegador")
    print("2. Navegue até a tela de login")
    print("3. Clique no campo CPF para posicionar o cursor")
    print("4. Pressione Enter quando estiver pronto")
    print()
    
    input("⏳ Pressione Enter quando estiver pronto...")
    
    # Executar o script
    print()
    print(f"🚀 Executando: {ahk_exe} {script_ahk}")
    print()
    print("⏳ O script irá:")
    print("   • Aguardar 2 segundos")
    print("   • Digitar CPF onde estiver o cursor")
    print("   • Pressionar Tab para campo senha")
    print("   • Digitar senha")
    print("   • Pressionar Enter para enviar")
    print()
    
    try:
        # Executar script
        resultado = subprocess.run(
            [ahk_exe, script_ahk],
            timeout=70,  # 70 segundos para comportamento humanizado
            capture_output=True,
            text=True
        )
        
        print("📊 RESULTADO:")
        print(f"   Código de retorno: {resultado.returncode}")
        
        if resultado.stdout:
            print(f"   Saída: {resultado.stdout}")
        
        if resultado.stderr:
            print(f"   Erro: {resultado.stderr}")
        
        if resultado.returncode == 0:
            print("   ✅ Script executado sem erros!")
        else:
            print("   ⚠️ Script terminou com aviso/erro")
        
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT: Script demorou mais que 70 segundos")
    except Exception as e:
        print(f"❌ ERRO: {e}")
    
    print()
    # Feedback do usuário
    print("🤔 RESULTADO DO LOGIN:")
    resultado_usuario = input("O login funcionou? (s/n): ").lower().strip()
    
    if resultado_usuario == 's':
        print()
        print("🎉 SUCESSO!")
        print("✅ O arquivo loginsisb.ahk está funcionando corretamente!")
        print("💡 Agora pode ser usado no sistema automático.")
    else:
        print()
        print("❌ LOGIN NÃO FUNCIONOU")
        print()
        print("🔧 DICAS PARA DEBUG:")
        print("• Verifique se o cursor estava realmente no campo CPF")
        print("• Teste manualmente os hotkeys:")
        print("  - F1: Login completo")
        print("  - F2: Apenas CPF")
        print("  - F3: Apenas senha")
        print("  - F4: Tab")
        print("  - F5: Enter")
        print("• Execute o script novamente após posicionar melhor o cursor")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
