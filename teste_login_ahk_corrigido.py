#!/usr/bin/env python3
# teste_login_ahk_corrigido.py
"""
Script de teste específico para validar as correções do login AHK
Testa os diferentes scripts AHK em ordem de prioridade
"""

import sys
import os
import subprocess

def main():
    print("=" * 70)
    print("🔧 TESTE DE LOGIN AHK CORRIGIDO - SISBAJUD")
    print("=" * 70)
    print()
    
    # Verificar scripts AHK disponíveis
    scripts_ahk = [
        'loginsisb_avancado.ahk',  # Versão corrigida
        'loginsisb_simples.ahk',   # Versão ultra simples
        'loginsisb.ahk'            # Fallback original
    ]
    
    scripts_encontrados = []
    
    print("🔍 Verificando scripts AHK disponíveis:")
    for script in scripts_ahk:
        if os.path.exists(script):
            print(f"   ✅ {script} - ENCONTRADO")
            scripts_encontrados.append(script)
        else:
            print(f"   ❌ {script} - NÃO ENCONTRADO")
    
    if not scripts_encontrados:
        print("\n❌ Nenhum script AHK encontrado!")
        return
    
    print(f"\n📋 Scripts disponíveis: {len(scripts_encontrados)}")
    
    # Verificar AutoHotkey
    print("\n🔍 Verificando AutoHotkey:")
    ahk_paths = [
        r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
        r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
    ]
    
    ahk_exe = None
    for path in ahk_paths:
        if os.path.exists(path):
            print(f"   ✅ AutoHotkey encontrado: {path}")
            ahk_exe = path
            break
        else:
            print(f"   ❌ Não encontrado: {path}")
    
    if not ahk_exe:
        print("\n❌ AutoHotkey não encontrado! Instale de: https://autohotkey.com/")
        return
    
    # Testar cada script
    print("\n" + "=" * 70)
    print("🧪 INICIANDO TESTES DOS SCRIPTS AHK")
    print("=" * 70)
    
    for i, script in enumerate(scripts_encontrados, 1):
        print(f"\n--- TESTE {i}: {script} ---")
        
        escolha = input(f"Deseja testar {script}? (s/n/q=quit): ").lower().strip()
        
        if escolha == 'q':
            print("❌ Testes cancelados pelo usuário.")
            break
        elif escolha != 's':
            print(f"⏭️ Pulando {script}")
            continue
        
        print(f"🚀 Executando {script}...")
        print("💡 INSTRUÇÕES:")
        print("   1. Abra manualmente o SISBAJUD no navegador")
        print("   2. Posicione o cursor no campo CPF")
        print("   3. Pressione Enter quando estiver pronto")
        
        input("   Pressione Enter quando estiver pronto...")
        
        try:
            print(f"🤖 Executando: {ahk_exe} {script}")
            
            resultado = subprocess.run(
                [ahk_exe, script],
                timeout=60,
                capture_output=True,
                text=True
            )
            
            print(f"📊 Resultado:")
            print(f"   Código de retorno: {resultado.returncode}")
            
            if resultado.stdout:
                print(f"   Saída: {resultado.stdout}")
            
            if resultado.stderr:
                print(f"   Erro: {resultado.stderr}")
            
            if resultado.returncode == 0:
                print("   ✅ Script executado com sucesso!")
            else:
                print("   ⚠️ Script terminou com erro/aviso")
            
            # Verificar resultado manualmente
            feedback = input("\n🤔 O login funcionou? (s/n): ").lower().strip()
            
            if feedback == 's':
                print(f"🎉 SUCESSO! {script} está funcionando corretamente!")
                print(f"💡 Este script será usado como preferência no sistema.")
                break
            else:
                print(f"❌ {script} não funcionou adequadamente.")
                print("Continuando para próximo script...")
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout: Script demorou mais que 60 segundos")
        except FileNotFoundError:
            print(f"❌ Erro: Não foi possível executar {ahk_exe}")
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
    
    print("\n" + "=" * 70)
    print("📋 RESUMO DOS TESTES")
    print("=" * 70)
    print("Scripts testados e resultados:")
    print("- Se algum script funcionou, ele será usado automaticamente")
    print("- Scripts são testados em ordem de prioridade")
    print("- Verifique se os campos foram preenchidos corretamente")
    print("=" * 70)

if __name__ == "__main__":
    main()
