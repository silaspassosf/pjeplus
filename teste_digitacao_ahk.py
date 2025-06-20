#!/usr/bin/env python3
# teste_digitacao_ahk.py
"""
Teste específico para verificar se o AHK está digitando corretamente
"""

import os
import subprocess
import time

def main():
    print("🔍 TESTE DE DIGITAÇÃO - loginsisb.ahk")
    print("=" * 50)
    print()
    
    # Verificar arquivos
    script_ahk = "loginsisb.ahk"
    ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
    
    if not os.path.exists(script_ahk):
        print(f"❌ {script_ahk} não encontrado!")
        return
    
    if not os.path.exists(ahk_exe):
        print(f"❌ AutoHotkey não encontrado!")
        return
    
    print("✅ Arquivos encontrados")
    print()
    
    # Instruções de teste
    print("📋 TESTE MANUAL DE DIGITAÇÃO:")
    print("1. Abra o Bloco de Notas (notepad)")
    print("2. Clique no campo de texto do Bloco de Notas")
    print("3. Pressione Enter aqui para testar a digitação")
    print()
    
    input("⏳ Pressione Enter quando o Bloco de Notas estiver aberto e focado...")
    
    print()
    print("🧪 TESTANDO HOTKEYS INDIVIDUAIS:")
    print()
    
    # Teste 1: F6 (teste de digitação)
    print("--- TESTE 1: F6 (Digitar 'TESTE123') ---")
    input("Pressione Enter para executar F6...")
    
    # Criar script temporário para F6
    script_temp = """
#NoEnv
#SingleInstance Force
SendMode Input

; Aguardar 2 segundos
Sleep, 2000

; Digitar teste
SendRaw, TESTE123

; Sair
Sleep, 1000
ExitApp
"""
    
    with open("teste_f6.ahk", "w") as f:
        f.write(script_temp)
    
    try:
        subprocess.run([ahk_exe, "teste_f6.ahk"], timeout=10)
        print("✅ F6 executado")
    except:
        print("❌ Erro no F6")
    
    os.remove("teste_f6.ahk")
    
    resultado_f6 = input("Digitou 'TESTE123' no Bloco de Notas? (s/n): ").lower()
    
    if resultado_f6 != 's':
        print("❌ PROBLEMA: AutoHotkey não está digitando!")
        print("💡 Possíveis causas:")
        print("   - AutoHotkey bloqueado por antivírus")
        print("   - Permissões insuficientes")
        print("   - Bloco de Notas não estava em foco")
        return
    
    print("✅ AutoHotkey está digitando corretamente!")
    print()
    
    # Teste 2: CPF
    print("--- TESTE 2: F2 (Digitar CPF) ---")
    print("Limpe o Bloco de Notas e pressione Enter...")
    input()
    
    script_cpf = """
#NoEnv
#SingleInstance Force
SendMode Input

CPF := "300.692.778-85"

; Aguardar 2 segundos
Sleep, 2000

; Limpar e digitar CPF
Send, ^a
Sleep, 100
Send, {Delete}
Sleep, 100

Loop, Parse, CPF
{
    SendRaw, %A_LoopField%
    Sleep, 50
}

; Sair
Sleep, 1000
ExitApp
"""
    
    with open("teste_cpf.ahk", "w") as f:
        f.write(script_cpf)
    
    try:
        subprocess.run([ahk_exe, "teste_cpf.ahk"], timeout=15)
        print("✅ Teste CPF executado")
    except:
        print("❌ Erro no teste CPF")
    
    os.remove("teste_cpf.ahk")
    
    resultado_cpf = input("Digitou o CPF '300.692.778-85'? (s/n): ").lower()
    
    if resultado_cpf != 's':
        print("❌ PROBLEMA: CPF não foi digitado corretamente!")
        return
    
    print("✅ CPF digitado corretamente!")
    print()
    
    # Teste 3: Script completo
    print("--- TESTE 3: Script completo ---")
    print("Agora vamos testar o login completo no SISBAJUD")
    print("1. Abra o SISBAJUD")
    print("2. Clique no campo CPF")
    print("3. Pressione Enter aqui")
    print()
    
    input("⏳ Pressione Enter quando estiver pronto no SISBAJUD...")
    
    try:
        resultado = subprocess.run([ahk_exe, script_ahk], timeout=60)
        print(f"✅ Script completo executado (código: {resultado.returncode})")
    except subprocess.TimeoutExpired:
        print("⏰ Timeout no script completo")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    resultado_login = input("O login foi preenchido no SISBAJUD? (s/n): ").lower()
    
    if resultado_login == 's':
        print()
        print("🎉 SUCESSO TOTAL!")
        print("✅ O script loginsisb.ahk está funcionando perfeitamente!")
    else:
        print()
        print("❌ O script não funcionou no SISBAJUD")
        print("💡 Mas a digitação básica funciona, então:")
        print("   - Verifique se o cursor estava no campo CPF")
        print("   - Teste os hotkeys manuais (F2, F3, F4, F5)")
    
    print()
    print("=" * 50)

if __name__ == "__main__":
    main()
