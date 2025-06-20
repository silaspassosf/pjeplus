#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador da Integração Python + AutoHotkey
==========================================

Este script testa se a integração entre Python e AutoHotkey
está funcionando corretamente para o login do SISBAJUD.
"""

import subprocess
import os
import sys

def verificar_autohotkey():
    """Verifica se o AutoHotkey está instalado"""
    try:
        resultado = subprocess.run(['autohotkey', '--version'], 
                                 capture_output=True, text=True, timeout=5)
        if resultado.returncode == 0:
            print('✅ AutoHotkey encontrado no sistema')
            print(f'   Versão: {resultado.stdout.strip()}')
            return True
        else:
            print('❌ AutoHotkey não responde corretamente')
            return False
    except FileNotFoundError:
        print('❌ AutoHotkey não encontrado no PATH')
        print('   Instale o AutoHotkey: https://autohotkey.com/')
        return False
    except Exception as e:
        print(f'❌ Erro ao verificar AutoHotkey: {e}')
        return False

def verificar_script_ahk():
    """Verifica se o script AHK existe"""
    script_path = os.path.join(os.path.dirname(__file__), 'loginsisb.ahk')
    if os.path.exists(script_path):
        print(f'✅ Script AHK encontrado: {script_path}')
        return True
    else:
        print(f'❌ Script AHK não encontrado: {script_path}')
        return False

def testar_execucao_ahk():
    """Testa a execução do script AHK (sem login real)"""
    script_path = os.path.join(os.path.dirname(__file__), 'loginsisb_simples.ahk')
    
    if not os.path.exists(script_path):
        print('⚠️ Script de teste não encontrado, criando...')
        # Criar um script AHK simples para teste
        with open(script_path, 'w') as f:
            f.write('; Script de teste AutoHotkey\n')
            f.write('MsgBox, Teste de integração Python + AHK OK!\n')
            f.write('ExitApp\n')
    
    try:
        print('🧪 Testando execução do script AHK...')
        resultado = subprocess.run(['autohotkey', script_path], 
                                 timeout=10, capture_output=True, text=True)
        
        if resultado.returncode == 0:
            print('✅ Script AHK executado com sucesso!')
            return True
        else:
            print(f'❌ Script AHK falhou (código: {resultado.returncode})')
            if resultado.stderr:
                print(f'   Erro: {resultado.stderr}')
            return False
            
    except subprocess.TimeoutExpired:
        print('⏰ Timeout na execução do script AHK')
        return False
    except Exception as e:
        print(f'❌ Erro ao executar script AHK: {e}')
        return False

def main():
    print('=' * 50)
    print('🔍 VALIDADOR DA INTEGRAÇÃO PYTHON + AUTOHOTKEY')
    print('=' * 50)
    print()
    
    testes_passou = 0
    total_testes = 3
    
    # Teste 1: AutoHotkey instalado
    print('Teste 1: Verificando instalação do AutoHotkey...')
    if verificar_autohotkey():
        testes_passou += 1
    print()
    
    # Teste 2: Script AHK existe
    print('Teste 2: Verificando script AHK...')
    if verificar_script_ahk():
        testes_passou += 1
    print()
    
    # Teste 3: Execução funcional
    print('Teste 3: Testando execução AHK...')
    if testar_execucao_ahk():
        testes_passou += 1
    print()
    
    # Resultado final
    print('=' * 50)
    print(f'RESULTADO: {testes_passou}/{total_testes} testes passaram')
    
    if testes_passou == total_testes:
        print('🎉 Todos os testes passaram! Integração funcionando.')
        print('✅ O login automático via AHK deve funcionar corretamente.')
    else:
        print('⚠️ Alguns testes falharam. Verifique os problemas acima.')
        print('❌ O login automático pode não funcionar adequadamente.')
    
    print('=' * 50)

if __name__ == "__main__":
    main()
