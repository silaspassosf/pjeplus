#!/usr/bin/env python3
"""
Teste simples da barra de automações SISBAJUD
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bacen import *

def teste_simples_sisbajud():
    """Teste apenas da barra de automações SISBAJUD"""
    print('[TESTE] Iniciando teste da barra SISBAJUD...')
    
    try:        # Configurar driver
        driver_sisbajud = driver_firefox_sisbajud(headless=False)
        print('[TESTE] Driver SISBAJUD configurado')
        
        # Abrir SISBAJUD
        driver_sisbajud.get('https://www.sisbajud.cnj.jus.br/')
        print('[TESTE] SISBAJUD aberto')
        
        # Aguardar página carregar
        time.sleep(3)
        
        # Testar injeção da barra
        print('[TESTE] Testando injeção da barra...')
        resultado = injetar_menu_kaizen_sisbajud(driver_sisbajud)
        
        if resultado:
            print('[TESTE] ✅ Barra injetada com sucesso!')
        else:
            print('[TESTE] ❌ Falha na injeção da barra')
        
        # Aguardar para visualizar
        input('[TESTE] Pressione Enter para fechar...')
        
    except Exception as e:
        print(f'[TESTE] ❌ Erro no teste: {e}')
        import traceback
        traceback.print_exc()
    finally:
        try:
            driver_sisbajud.quit()
        except:
            pass

if __name__ == '__main__':
    teste_simples_sisbajud()
