#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB.PY - Orquestrador Principal
Automação SISBAJUD/BACEN integrada ao PJe
Versão Modular - Refatoração do bacen.py

Este arquivo é o ponto de entrada principal que orquestra todos os módulos
de automação SISBAJUD/BACEN mantendo 100% da funcionalidade original.
"""

import sys
import os
import traceback

# Adicionar o diretório dos módulos ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sisb_modulos'))

# Importações dos módulos locais
from sisb_modulos import config
from sisb_modulos import drivers
from sisb_modulos import cookies
from sisb_modulos import interface_pje
from sisb_modulos import dados_processo
from sisb_modulos import sisbajud_core
from sisb_modulos import kaizen_interface
from sisb_modulos import preenchimento
from sisb_modulos import bloqueios
from sisb_modulos import minutas
from sisb_modulos import utils

# Importações externas (mantidas do original)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import tempfile
import subprocess

# Importações de dependências do projeto
from Fix import extrair_dados_processo
from driver_config import criar_driver, login_func

# ===================== VARIÁVEIS GLOBAIS =====================
# Estas variáveis são compartilhadas entre módulos
processo_dados_extraidos = None
login_ahk_executado = False

# ===================== FUNÇÃO PRINCIPAL =====================
def main():
    """
    Função principal que executa o fluxo completo da automação SISBAJUD/BACEN.
    Mantém a lógica original do bacen.py mas usando módulos organizados.
    """
    print('=' * 60)
    print('🏦 SISB - Automação SISBAJUD/BACEN Modular')
    print('   Versão refatorada do bacen.py')
    print('=' * 60)
    print()
    
    # Mostrar opções de execução
    print('Escolha o modo de execução:')
    print('1. 🔄 Modo Completo (PJe + SISBAJUD)')
    print('2. 🏦 Apenas SISBAJUD')
    print('3. 🧪 Modo Teste SISBAJUD')
    print('4. ⚙️  Configurações')
    print()
    
    try:
        escolha = input('Digite sua opção (1-4): ').strip()
        
        if escolha == '1':
            executar_modo_completo()
        elif escolha == '2':
            executar_modo_sisbajud()
        elif escolha == '3':
            executar_modo_teste()
        elif escolha == '4':
            mostrar_configuracoes()
        else:
            print('❌ Opção inválida. Executando modo completo por padrão.')
            executar_modo_completo()
            
    except KeyboardInterrupt:
        print('\n⏹️ Execução interrompida pelo usuário.')
    except Exception as e:
        print(f'\n❌ Erro durante a execução: {e}')
        traceback.print_exc()

def executar_modo_completo():
    """
    Executa o modo completo: PJe + SISBAJUD
    Equivalente ao main() original do bacen.py
    """
    print('🔄 Iniciando modo completo...')
    print()
    
    # Executar driver PJe
    print('1️⃣ Iniciando driver PJe...')
    driver_pje = executar_driver_pje()
    
    if driver_pje:
        print('✅ Driver PJe iniciado com sucesso!')
        
        # Executar driver SISBAJUD
        print('2️⃣ Iniciando driver SISBAJUD...')
        driver_sisbajud = executar_driver_sisbajud()
        
        if driver_sisbajud:
            print('✅ Driver SISBAJUD iniciado com sucesso!')
            print('🔄 Ambos os drivers estão ativos. Monitoramento iniciado...')
            
            # Monitorar ambos os drivers
            utils.monitorar_drivers_completo(driver_pje, driver_sisbajud)
        else:
            print('❌ Falha ao iniciar driver SISBAJUD.')
            driver_pje.quit()
    else:
        print('❌ Falha ao iniciar driver PJe.')

def executar_modo_sisbajud():
    """
    Executa apenas o SISBAJUD
    Equivalente ao main_sisbajud_apenas() original
    """
    print('🏦 Iniciando modo SISBAJUD apenas...')
    print()
    
    driver_sisbajud = executar_driver_sisbajud()
    
    if driver_sisbajud:
        print('✅ Driver SISBAJUD iniciado com sucesso!')
        print('🔄 Monitoramento ativo...')
        
        utils.monitorar_driver_sisbajud(driver_sisbajud)
    else:
        print('❌ Falha ao iniciar driver SISBAJUD.')

def executar_modo_teste():
    """
    Executa o modo de teste do SISBAJUD
    Equivalente ao main_teste_sisbajud() original
    """
    print('🧪 Iniciando modo teste SISBAJUD...')
    print()
    
    # Usar a função de teste dos módulos
    sisbajud_core.main_teste_sisbajud()

def mostrar_configuracoes():
    """
    Mostra as configurações atuais do sistema
    """
    print('⚙️  Configurações atuais:')
    print('=' * 40)
    
    for chave, valor in config.CONFIG.items():
        print(f'{chave}: {valor}')
    
    print('=' * 40)
    print()
    
    # Opção para editar configurações
    editar = input('Deseja editar alguma configuração? (s/n): ').lower().strip()
    if editar == 's':
        config.editar_configuracoes()

def executar_driver_pje():
    """
    Executa o driver PJe usando o módulo interface_pje
    Equivalente ao executar_driver_pje() original
    """
    try:
        # Criar driver PJe
        driver = criar_driver()
        
        if not driver:
            print('❌ Falha ao criar driver PJe.')
            return None
        
        # Fazer login
        if not login_func(driver):
            print('❌ Falha no login PJe.')
            driver.quit()
            return None
        
        # Extrair dados do processo
        global processo_dados_extraidos
        processo_dados_extraidos = extrair_dados_processo(driver)
        
        if processo_dados_extraidos:
            print('✅ Dados do processo extraídos com sucesso!')
            dados_processo.salvar_dados_processo_temp(processo_dados_extraidos)
        
        # Injetar interface no PJe
        interface_pje.injetar_botao_sisbajud_pje(driver)
        interface_pje.bind_eventos(driver)
        
        return driver
        
    except Exception as e:
        print(f'❌ Erro ao executar driver PJe: {e}')
        traceback.print_exc()
        return None

def executar_driver_sisbajud(modo_teste=False):
    """
    Executa o driver SISBAJUD usando o módulo sisbajud_core
    Equivalente ao executar_driver_sisbajud() original
    """
    try:
        return sisbajud_core.executar_driver_sisbajud(modo_teste=modo_teste)
        
    except Exception as e:
        print(f'❌ Erro ao executar driver SISBAJUD: {e}')
        traceback.print_exc()
        return None

# ===================== COMPATIBILIDADE =====================
# Funções exportadas para manter compatibilidade com scripts existentes

# Exportar funções principais dos módulos
injetar_botao_sisbajud_pje = interface_pje.injetar_botao_sisbajud_pje
prompt_js = interface_pje.prompt_js
bind_eventos = interface_pje.bind_eventos
checar_evento = interface_pje.checar_evento

salvar_cookies_sisbajud = cookies.salvar_cookies_sisbajud
carregar_cookies_sisbajud = cookies.carregar_cookies_sisbajud

minuta_bloqueio = minutas.minuta_bloqueio
minuta_endereco = minutas.minuta_endereco
processar_bloqueios = bloqueios.processar_bloqueios

kaizen_nova_minuta = minutas.kaizen_nova_minuta
kaizen_consultar_minuta = minutas.kaizen_consultar_minuta
kaizen_consultar_teimosinha = minutas.kaizen_consultar_teimosinha
kaizen_preencher_campos = preenchimento.kaizen_preencher_campos

dados_login = utils.dados_login
criar_driver_firefox_sisb = drivers.criar_driver_firefox_sisb

# Funções auxiliares para compatibilidade
main_sisbajud_apenas = executar_modo_sisbajud
main_teste_sisbajud = executar_modo_teste

# ===================== PONTO DE ENTRADA =====================
if __name__ == "__main__":
    """
    Ponto de entrada principal
    Mantém compatibilidade total com execução original do bacen.py
    """
    try:
        main()
    except KeyboardInterrupt:
        print('\n[SISB] ⏹️ Execução interrompida pelo usuário.')
    except Exception as e:
        print(f'\n[SISB] ❌ Erro crítico na execução: {e}')
        traceback.print_exc()
