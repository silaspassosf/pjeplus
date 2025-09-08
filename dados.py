#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dados.py - Script para navegar para processo específico no PJe e executar função carta

Funcionalidades:
1. Driver e login ativos de driver_config
2. Navegar para processo específico no PJe (3734856)
3. Executar função carta() do carta.py para teste de extração
4. Deixar processo carregado para verificação manual dos resultados
"""

import json
import os
import sys
import traceback
import time

# Importações do projeto
from driver_config import criar_driver, login_func
from carta import carta

def main():
    """Função principal do script dados.py"""
    try:
        print('[DADOS] ========== INICIANDO SCRIPT DADOS.PY ==========')
        print('[DADOS] Teste da função carta() do carta.py')
        
        # 1. DRIVER E LOGIN ATIVOS DE DRIVER_CONFIG
        print('[DADOS] 1. Criando driver e fazendo login via driver_config...')
        
        # Criar driver usando driver_config
        driver = criar_driver()
        if not driver:
            print('[DADOS] ❌ Falha ao criar driver')
            return False
        
        print('[DADOS] ✅ Driver criado com sucesso')
        
        # Fazer login usando driver_config
        login_sucesso = login_func(driver)
        if not login_sucesso:
            print('[DADOS] ❌ Falha no login')
            driver.quit()
            return False
        
        print('[DADOS] ✅ Login realizado com sucesso')
        
        # 2. NAVEGAR PARA PROCESSO ESPECÍFICO NO PJE
        print('[DADOS] 2. Navegando para processo específico...')
        
        url_processo = 'https://pje.trt2.jus.br/pjekz/processo/3734856/detalhe'
        print(f'[DADOS] URL do processo: {url_processo}')
        
        driver.get(url_processo)
        
        # Aguardar página carregar
        time.sleep(5)
        
        # Verificar se chegou na página correta
        current_url = driver.current_url
        if '3734856' in current_url:
            print('[DADOS] ✅ Navegação para processo bem-sucedida')
        else:
            print(f'[DADOS] ⚠️ URL atual: {current_url}')
            print('[DADOS] ⚠️ Pode não ter chegado na página esperada, mas prosseguindo...')
        
        # 3. EXECUTAR FUNÇÃO CARTA DO CARTA.PY
        print('[DADOS] 3. Executando função carta() do carta.py...')
        
        # Aguardar mais tempo para garantir que a página carregue completamente
        time.sleep(3)
        
        try:
            print('[DADOS] ⚙️ Chamando carta(driver, log=True)...')
            
            # Executar função carta com log habilitado
            resultado = carta(driver, log=True, limite_intimacoes=None)
            
            if resultado:
                print(f'[DADOS] ✅ Função carta() executada com sucesso!')
                print(f'[DADOS] 📄 Resultado: {resultado}')
            else:
                print('[DADOS] ⚠️ Função carta() retornou None ou resultado vazio')
                print('[DADOS] � Isso pode ser normal se não houver intimações de correio')
            
        except Exception as e:
            print(f'[DADOS][ERRO] Falha ao executar função carta(): {e}')
            traceback.print_exc()
        
        # 4. MANTER DRIVER ABERTO PARA VERIFICAÇÃO MANUAL
        print('\n' + '='*80)
        print('[DADOS] 🔄 Driver permanece aberto para verificação manual...')
        print('[DADOS] ⚠️ ATENÇÃO: Feche manualmente quando terminar!')
        print('[DADOS] 💡 Você pode verificar se a função carta() funcionou corretamente')
        print('[DADOS] 🔍 Verifique o console acima para detalhes da execução')
        print('='*80)
        
        # Não fechar o driver automaticamente - deixar para uso manual
        return True
        
    except Exception as e:
        print(f'[DADOS][ERRO] Falha no script dados.py: {e}')
        traceback.print_exc()
        
        # Fechar driver se ainda estiver aberto  
        try:
            if 'driver' in locals():
                driver.quit()
                print('[DADOS] Driver fechado após erro')
        except:
            pass
        
        return False

if __name__ == '__main__':
    """Executar script quando chamado diretamente"""
    print('[DADOS] Executando dados.py...')
    sucesso = main()
    
    if sucesso:
        print('[DADOS] ✅ Script executado com sucesso!')
        sys.exit(0)
    else:
        print('[DADOS] ❌ Script falhou!')
        sys.exit(1)
