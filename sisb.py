#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB.PY - Orquestrador Principal
Automação SISBAJUD/BACEN integrada ao PJe - Versão Modular
"""

import sys
import os
import traceback
import time
import json
import tempfile
import subprocess

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

# Importações de dependências do projeto
from Fix import extrair_dados_processo
from driver_config import criar_driver, login_func

# Variáveis globais para compatibilidade
CONFIG = config.CONFIG
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
    print('4. 🤖 Ferramentas Kaizen')
    print('5. 📋 Minutas e Bloqueios')
    print('6. ⚙️  Configurações')
    print()
    
    try:
        escolha = input('Digite sua opção (1-6): ').strip()
        
        if escolha == '1':
            executar_modo_completo()
        elif escolha == '2':
            main_sisbajud_apenas()
        elif escolha == '3':
            main_teste_sisbajud()
        elif escolha == '4':
            menu_ferramentas_kaizen()
        elif escolha == '5':
            menu_minutas_bloqueios()
        elif escolha == '6':
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
            monitorar_drivers_completo(driver_pje, driver_sisbajud)
        else:
            print('❌ Falha ao iniciar driver SISBAJUD.')
            driver_pje.quit()
    else:
        print('❌ Falha ao iniciar driver PJe.')

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
    Executa o driver SISBAJUD usando os módulos organizados
    Equivalente ao executar_driver_sisbajud() original
    """
    try:
        # Usar função dos módulos para criar driver
        driver = drivers.criar_driver_firefox_sisb()
        
        if not driver:
            print('❌ Falha ao criar driver SISBAJUD.')
            return None
        
        # Carregar dados do processo se disponíveis
        dados_processo.carregar_dados_processo_temp()
        
        # Integrar dados do processo ao storage
        dados_processo.integrar_storage_processo(driver)
        
        # Executar login automático se não for modo teste
        if not modo_teste:
            try:
                # Tentar login automático via cookies
                cookies.carregar_cookies_sisbajud(driver)
                
                # Se não conseguir login via cookies, tentar AHK
                if not sisbajud_core.aguardar_login_manual_sisbajud(driver):
                    print('🔐 Tentando login automático via AHK...')
                    sisbajud_core.tentar_login_automatico_ahk()
                    
            except Exception as e:
                print(f'⚠️ Erro no login automático: {e}')
                print('🔐 Será necessário login manual.')
        
        # Injetar menu Kaizen no SISBAJUD
        kaizen_interface.injetar_menu_kaizen_sisbajud(driver)
        
        # Aguardar tela de minuta e injetar menu
        kaizen_interface.aguardar_tela_minuta_e_injetar_menu(driver)
        
        return driver
        
    except Exception as e:
        print(f'❌ Erro ao executar driver SISBAJUD: {e}')
        traceback.print_exc()
        return None

def monitorar_drivers_completo(driver_pje, driver_sisbajud):
    """
    Monitora ambos os drivers em funcionamento
    
    Args:
        driver_pje: Driver do PJe
        driver_sisbajud: Driver do SISBAJUD
    """
    print('🔄 Monitoramento ativo dos drivers...')
    print('💡 Pressione Ctrl+C para encerrar.')
    
    try:
        while True:
            # Verificar eventos no PJe
            if driver_pje:
                try:
                    evento = interface_pje.checar_evento(driver_pje)
                    if evento == 'abrir_sisbajud':
                        print('📢 Evento detectado: Abrir SISBAJUD')
                        # Aqui poderiam ser executadas ações específicas
                except:
                    pass
            
            # Verificar eventos no SISBAJUD (Kaizen)
            if driver_sisbajud:
                try:
                    evento_kaizen = kaizen_interface.checar_kaizen_evento(driver_sisbajud)
                    if evento_kaizen:
                        print(f'🤖 Evento Kaizen detectado: {evento_kaizen}')
                        # Processar evento conforme necessário
                except:
                    pass
            
            # Verificar se drivers ainda estão funcionais
            if not drivers.verificar_driver_funcional(driver_pje):
                print('⚠️ Driver PJe não está mais funcional')
                break
            
            if not drivers.verificar_driver_funcional(driver_sisbajud):
                print('⚠️ Driver SISBAJUD não está mais funcional')
                break
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('\n⏹️ Monitoramento interrompido pelo usuário.')
    finally:
        # Salvar cookies do SISBAJUD antes de fechar
        try:
            cookies.salvar_cookies_sisbajud(driver_sisbajud)
        except:
            pass
        
        # Fechar drivers
        drivers.fechar_driver_seguro(driver_pje)
        drivers.fechar_driver_seguro(driver_sisbajud)

def main_sisbajud_apenas():
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
        
        monitorar_driver_sisbajud(driver_sisbajud)
    else:
        print('❌ Falha ao iniciar driver SISBAJUD.')

def monitorar_driver_sisbajud(driver_sisbajud):
    """
    Monitora apenas o driver SISBAJUD
    
    Args:
        driver_sisbajud: Driver do SISBAJUD
    """
    print('🔄 Monitoramento ativo do SISBAJUD...')
    print('💡 Pressione Ctrl+C para encerrar.')
    
    try:
        while True:
            # Verificar eventos Kaizen
            try:
                evento_kaizen = kaizen_interface.checar_kaizen_evento(driver_sisbajud)
                if evento_kaizen:
                    print(f'🤖 Evento Kaizen detectado: {evento_kaizen}')
                    # Processar evento conforme necessário
            except:
                pass
            
            # Verificar se driver ainda está funcional
            if not drivers.verificar_driver_funcional(driver_sisbajud):
                print('⚠️ Driver SISBAJUD não está mais funcional')
                break
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('\n⏹️ Monitoramento interrompido pelo usuário.')
    finally:
        # Salvar cookies antes de fechar
        try:
            cookies.salvar_cookies_sisbajud(driver_sisbajud)
        except:
            pass
        
        # Fechar driver
        drivers.fechar_driver_seguro(driver_sisbajud)

def main_teste_sisbajud():
    """
    Executa o modo de teste do SISBAJUD usando o módulo sisbajud_core
    Equivalente ao main_teste_sisbajud() original
    """
    print('🧪 Iniciando modo teste SISBAJUD...')
    print('=' * 60)
    print()
    
    print('Este modo irá:')
    print('1. ✅ Iniciar apenas o Driver SISBAJUD')
    print('2. 🤖 Tentar login automático via cookies')
    print('3. 🔧 Se falhar, permitir login manual')
    print('4. 🚀 Inicializar todas as automações do SISBAJUD')
    print()
    
    confirmar = input('Deseja prosseguir com o teste? (s/n): ').lower().strip()
    
    if confirmar != 's':
        print('❌ Teste cancelado pelo usuário.')
        return
    
    print()
    print('🚀 Iniciando teste do SISBAJUD...')
    
    try:
        # Usar o módulo sisbajud_core para o teste
        resultado = sisbajud_core.main_teste_sisbajud()
        
        if resultado:
            print('✅ Teste do SISBAJUD concluído com sucesso!')
        else:
            print('❌ Teste do SISBAJUD falhou.')
            
    except KeyboardInterrupt:
        print('\n⏹️ Teste interrompido pelo usuário.')
    except Exception as e:
        print(f'\n❌ Erro durante o teste: {e}')
        traceback.print_exc()

def menu_ferramentas_kaizen():
    """Menu para acessar ferramentas específicas do Kaizen"""
    print('🤖 Ferramentas Kaizen')
    print('=' * 40)
    print('1. 🔓 Guardar Senha  2. 📝 Preencher Campos  3. 🔍 Consulta Rápida')
    print('4. 📋 Nova Minuta   5. 🔎 Consultar Minuta   6. 🔄 Voltar')
    print()
    
    escolha = input('Digite sua opção (1-6): ').strip()
    
    if escolha == '6':
        main()
    else:
        print('💡 Esta função será executada automaticamente quando necessário.')

def menu_minutas_bloqueios():
    """Menu para acessar funcionalidades de minutas e bloqueios"""
    print('📋 Minutas e Bloqueios')
    print('=' * 40)
    print('1. 🔒 Processar Bloqueios  2. 📝 Minuta de Bloqueio')
    print('3. 🏠 Minuta de Endereço   4. 🔍 Consultar Teimosinha  5. 🔄 Voltar')
    print()
    
    escolha = input('Digite sua opção (1-5): ').strip()
    
    if escolha == '5':
        main()
    else:
        print('💡 Esta função será executada automaticamente quando necessário.')

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
    
    # Validar configurações
    if config.validar_configuracoes():
        print('✅ Configurações válidas!')
    else:
        print('❌ Há problemas nas configurações.')

# ===================== COMPATIBILIDADE =====================
# Funções exportadas para manter compatibilidade com scripts existentes

# Módulo interface_pje
injetar_botao_sisbajud_pje = interface_pje.injetar_botao_sisbajud_pje
prompt_js = interface_pje.prompt_js
bind_eventos = interface_pje.bind_eventos
checar_evento = interface_pje.checar_evento

# Módulo cookies
salvar_cookies_sisbajud = cookies.salvar_cookies_sisbajud
carregar_cookies_sisbajud = cookies.carregar_cookies_sisbajud

# Módulo drivers
driver_firefox_sisbajud = drivers.driver_firefox_sisbajud
criar_driver_firefox_sisb = drivers.criar_driver_firefox_sisb
verificar_driver_funcional = drivers.verificar_driver_funcional
fechar_driver_seguro = drivers.fechar_driver_seguro

# Módulo dados_processo
salvar_dados_processo_temp = dados_processo.salvar_dados_processo_temp
carregar_dados_processo_temp = dados_processo.carregar_dados_processo_temp
integrar_storage_processo = dados_processo.integrar_storage_processo

# Módulo sisbajud_core
abrir_sisbajud_em_firefox_sisbajud = sisbajud_core.abrir_sisbajud_em_firefox_sisbajud
aguardar_login_manual_sisbajud = sisbajud_core.aguardar_login_manual_sisbajud
tentar_login_automatico_ahk = sisbajud_core.tentar_login_automatico_ahk
obter_caminho_autohotkey = sisbajud_core.obter_caminho_autohotkey

# Módulo kaizen_interface
injetar_menu_kaizen_sisbajud = kaizen_interface.injetar_menu_kaizen_sisbajud
checar_kaizen_evento = kaizen_interface.checar_kaizen_evento
aguardar_tela_minuta_e_injetar_menu = kaizen_interface.aguardar_tela_minuta_e_injetar_menu
monitor_janela_sisbajud = kaizen_interface.monitor_janela_sisbajud

# Módulo config
CONFIG = config.CONFIG

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
