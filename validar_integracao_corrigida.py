#!/usr/bin/env python3
# validar_integracao_corrigida.py  
"""
Valida a integração corrigida Python + AutoHotkey para SISBAJUD
Testa se todos os componentes estão funcionando corretamente
"""

import sys
import os
import subprocess

def main():
    print("=" * 70)
    print("🔧 VALIDAÇÃO DE INTEGRAÇÃO CORRIGIDA - PYTHON + AUTOHOTKEY")
    print("=" * 70)
    print()
    
    # Contadores
    testes_aprovados = 0
    total_testes = 6
    
    # Teste 1: Verificar se o bacen.py existe
    print("1. 📄 Verificando arquivo bacen.py...")
    if os.path.exists("bacen.py"):
        print("   ✅ bacen.py encontrado")
        testes_aprovados += 1
    else:
        print("   ❌ bacen.py não encontrado")
    print()
    
    # Teste 2: Verificar se as funções podem ser importadas
    print("2. 🔗 Testando importação de funções...")
    try:
        from bacen import main_teste_sisbajud, obter_caminho_autohotkey, tentar_login_automatico_ahk
        print("   ✅ Funções importadas com sucesso")
        testes_aprovados += 1
    except ImportError as e:
        print(f"   ❌ Erro ao importar funções: {e}")
    print()
    
    # Teste 3: Verificar extração do caminho do AutoHotkey
    print("3. 🛠️ Testando extração do caminho do AutoHotkey...")
    try:
        from bacen import obter_caminho_autohotkey
        caminho_ahk = obter_caminho_autohotkey()
        if caminho_ahk:
            print(f"   ✅ Caminho extraído: {caminho_ahk}")
            if os.path.exists(caminho_ahk):
                print("   ✅ Executável do AutoHotkey existe")
                testes_aprovados += 1
            else:
                print("   ❌ Executável do AutoHotkey não existe no caminho especificado")
        else:
            print("   ❌ Não foi possível extrair o caminho do AutoHotkey")
    except Exception as e:
        print(f"   ❌ Erro ao testar extração: {e}")
    print()
    
    # Teste 4: Verificar script AHK avançado
    print("4. 📜 Verificando script AutoHotkey avançado...")
    script_ahk = "loginsisb_avancado.ahk"
    if os.path.exists(script_ahk):
        print(f"   ✅ Script AHK avançado encontrado: {script_ahk}")
        testes_aprovados += 1
    else:
        print(f"   ❌ Script AHK avançado não encontrado: {script_ahk}")
        # Verificar fallback
        script_simples = "loginsisb.ahk"
        if os.path.exists(script_simples):
            print(f"   ⚠️ Script AHK simples disponível como fallback: {script_simples}")
    print()
    
    # Teste 5: Verificar driver_config.py
    print("5. ⚙️ Verificando driver_config.py...")
    if os.path.exists("driver_config.py"):
        print("   ✅ driver_config.py encontrado")
        # Verificar se contém referência ao AutoHotkey
        try:
            with open("driver_config.py", "r", encoding="utf-8") as f:
                conteudo = f.read()
            if "AutoHotkey" in conteudo:
                print("   ✅ Referência ao AutoHotkey encontrada no driver_config.py")
                testes_aprovados += 1
            else:
                print("   ❌ Referência ao AutoHotkey não encontrada no driver_config.py")
        except Exception as e:
            print(f"   ❌ Erro ao verificar conteúdo: {e}")
    else:
        print("   ❌ driver_config.py não encontrado")
    print()
    
    # Teste 6: Teste básico de sintaxe do script de teste
    print("6. 🧪 Verificando script de teste...")
    if os.path.exists("teste_sisbajud_corrigido.py"):
        print("   ✅ Script de teste corrigido encontrado")
        try:
            # Tentar compilar o script para verificar sintaxe
            with open("teste_sisbajud_corrigido.py", "r", encoding="utf-8") as f:
                code = f.read()
            compile(code, "teste_sisbajud_corrigido.py", "exec")
            print("   ✅ Sintaxe do script de teste está correta")
            testes_aprovados += 1
        except SyntaxError as e:
            print(f"   ❌ Erro de sintaxe no script de teste: {e}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar script de teste: {e}")
    else:
        print("   ❌ Script de teste não encontrado")
    print()
    
    # Resultado final
    print("=" * 70)
    print(f"📊 RESULTADO FINAL: {testes_aprovados}/{total_testes} testes aprovados")
    
    if testes_aprovados == total_testes:
        print("🎉 INTEGRAÇÃO VALIDADA COM SUCESSO!")
        print("💡 Você pode executar o teste com: python teste_sisbajud_corrigido.py")
    elif testes_aprovados >= total_testes - 1:
        print("⚠️ INTEGRAÇÃO QUASE COMPLETA - Verificar itens pendentes")
        print("💡 Você pode tentar executar o teste mesmo assim")
    else:
        print("❌ INTEGRAÇÃO INCOMPLETA - Vários problemas encontrados")
        print("💡 Corrija os problemas antes de executar o teste")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
