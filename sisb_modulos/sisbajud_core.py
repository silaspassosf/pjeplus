#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/SISBAJUD_CORE.PY
Núcleo da automação SISBAJUD - login, inicialização e gestão principal
Extraído do bacen.py original
"""

import time
import json
import os
from .config import processo_dados_extraidos
from .drivers import criar_driver_firefox_sisb
from .cookies import salvar_cookies_sisbajud
from .dados_processo import carregar_dados_processo_temp, integrar_storage_processo

def abrir_sisbajud_em_firefox_sisbajud():
    """
    Abre driver Firefox SISBAJUD e tenta login automático via cookies ou injeta tabela de login
    
    Returns:
        webdriver.Firefox: Driver SISBAJUD configurado ou None se erro
    """
    # Usar a função de driver Firefox específica para SISBAJUD
    driver = criar_driver_firefox_sisb()
    if not driver:
        print('[SISBAJUD_CORE] ❌ Falha ao criar driver Firefox SISBAJUD')
        return None
        
    print('[SISBAJUD_CORE] ✅ Driver SISBAJUD criado.')
    
    # Verificar se o login automático via cookies funcionou
    time.sleep(3)  # Aguardar estabilização
    current_url = driver.current_url
    
    # Verificar se já está logado (não está na tela de login)
    if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
        print('[SISBAJUD_CORE] ✅ Login automático realizado via cookies! Pulando login manual.')
        return driver
    
    print('[SISBAJUD_CORE] 📋 Cookies não funcionaram ou primeiro acesso. Injetando tabela de dados de login...')
    
    # Importar função de utils quando estiver disponível
    try:
        from .utils import dados_login
        dados_login(driver)
    except ImportError:
        print('[SISBAJUD_CORE] ⚠️ Função dados_login não disponível ainda')
    
    # Integração: carrega dados extraídos do processo do arquivo do projeto
    try:
        dados_carregados = carregar_dados_processo_temp()
        if dados_carregados:
            print('[SISBAJUD_CORE] ✅ Dados do processo carregados do arquivo:', dados_carregados)
        else:
            print('[SISBAJUD_CORE] ⚠️ Arquivo de dados do processo não encontrado.')
    except Exception as e:
        print(f'[SISBAJUD_CORE] ❌ Falha ao carregar dados do processo: {e}')
    
    print('[SISBAJUD_CORE] ✅ SISBAJUD aberto com tabela de login injetada.')
    print('[SISBAJUD_CORE] 👤 Faça login manualmente e aguarde a detecção automática.')
    return driver

def executar_driver_sisbajud(modo_teste=False):
    """
    DRIVER 2: SISBAJUD - Completamente autônomo
    Pode ser executado independentemente para testes
    
    Args:
        modo_teste (bool): Se True, tenta login automático via AHK se cookies falharem
        
    Returns:
        webdriver.Firefox: Driver SISBAJUD configurado ou None se erro
    """
    print('[SISBAJUD_CORE] === INICIANDO DRIVER SISBAJUD ===')
    
    try:
        print('[SISBAJUD_CORE] Passo 1: Criando driver SISBAJUD...')
        driver_sisbajud = criar_driver_firefox_sisb()
        
        if not driver_sisbajud:
            print('[SISBAJUD_CORE] ❌ Falha ao criar driver SISBAJUD.')
            return None
        
        print('[SISBAJUD_CORE] Passo 2: Driver SISBAJUD criado com sucesso!')
        
        # Verificar login automático via cookies
        current_url = driver_sisbajud.current_url
        ja_logado = not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms'])
        
        if ja_logado:
            print('[SISBAJUD_CORE] ✅ Login automático detectado via cookies!')
        else:
            print('[SISBAJUD_CORE] Passo 3: Preparando login manual...')
            
            # Injetar dados de login
            try:
                from .utils import dados_login
                dados_login(driver_sisbajud)
            except ImportError:
                print('[SISBAJUD_CORE] ⚠️ Função dados_login não disponível ainda')
            
            # TEMPORARIAMENTE DESABILITADO: Login AHK
            # if modo_teste:
            #     if tentar_login_automatico_ahk(driver_sisbajud):
            #         print('[SISBAJUD_CORE] ✅ Login automático via AHK realizado!')
            #     else:
            #         print('[SISBAJUD_CORE] ⚠️ Login AHK falhou. Aguardando login manual...')
            # else:
            
            print('[SISBAJUD_CORE] 👤 Aguardando login manual...')
            aguardar_login_manual_sisbajud(driver_sisbajud)
        
        print('[SISBAJUD_CORE] Passo 4: Inicializando componentes SISBAJUD...')
        
        # Carregar dados do processo (se disponíveis)
        carregar_dados_processo_temp()
        
        # Inicializar componentes
        try:
            from .utils import monitor_janela_sisbajud
            monitor_janela_sisbajud(driver_sisbajud)
        except ImportError:
            print('[SISBAJUD_CORE] ⚠️ Função monitor_janela_sisbajud não disponível ainda')
        
        integrar_storage_processo(driver_sisbajud)
        
        # Injetar barra de automações
        print('[SISBAJUD_CORE] Passo 5: Injetando barra de automações...')
        try:
            from .kaizen_interface import injetar_menu_kaizen_sisbajud
            injetar_menu_kaizen_sisbajud(driver_sisbajud)
        except ImportError:
            print('[SISBAJUD_CORE] ⚠️ Função injetar_menu_kaizen_sisbajud não disponível ainda')
        
        print('[SISBAJUD_CORE] ✅ SISBAJUD pronto! Barra de automações ativa.')
        return driver_sisbajud
        
    except Exception as e:
        print(f'[SISBAJUD_CORE] ❌ Erro crítico: {e}')
        import traceback
        traceback.print_exc()
        return None

def aguardar_login_manual_sisbajud(driver):
    """
    Aguarda o usuário fazer login manual no SISBAJUD
    Detecta quando o login foi realizado verificando mudanças na URL ou elementos da página
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        bool: True se login foi detectado
    """
    print('[SISBAJUD_CORE] 👤 Aguardando login manual no SISBAJUD...')
    print('[SISBAJUD_CORE] 💡 Faça o login manualmente na janela do SISBAJUD e aguarde.')
    
    login_detectado = False
    tentativas = 0
    max_tentativas = 300  # 5 minutos (300 * 1 segundo)
    
    while not login_detectado and tentativas < max_tentativas:
        try:
            current_url = driver.current_url
            
            # Verificar se saiu da tela de login (indicadores de login bem-sucedido)
            indicadores_login_sucesso = [
                'sisbajud.cnj.jus.br/web/',  # Após login vai para área principal
                'dashboard',  # Dashboard principal
                'home',  # Página inicial
                'minuta',  # Área de minutas
                'consulta'  # Área de consultas
            ]
            
            # Verificar se não está mais na tela de login
            if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                # Verificar se há elementos que indicam login bem-sucedido
                elementos_pos_login = driver.execute_script("""
                    // Verificar elementos que aparecem após login
                    let indicadores = [
                        'button[aria-label*="menu"]',  // Menu principal
                        'mat-toolbar',  // Barra de ferramentas
                        '.mat-toolbar',  // Barra superior
                        '[role="navigation"]',  // Navegação
                        'sisbajud-home',  // Componente home
                        'sisbajud-consulta',  // Componentes do SISBAJUD
                        'sisbajud-minuta'
                    ];
                    
                    for (let seletor of indicadores) {
                        if (document.querySelector(seletor)) {
                            return true;
                        }
                    }
                    return false;
                """)
                
                if elementos_pos_login:
                    login_detectado = True
                    print(f'[SISBAJUD_CORE] ✅ Login detectado! URL atual: {current_url}')
                    break
            
            # Verificar por URLs específicas de sucesso
            for indicador in indicadores_login_sucesso:
                if indicador in current_url.lower():
                    login_detectado = True
                    print(f'[SISBAJUD_CORE] ✅ Login detectado via URL! URL atual: {current_url}')
                    break
            
            if login_detectado:
                break
                
        except Exception as e:
            print(f'[SISBAJUD_CORE][DEBUG] Erro ao verificar login (tentativa {tentativas}): {e}')
        
        tentativas += 1
        if tentativas % 30 == 0:  # A cada 30 segundos
            print(f'[SISBAJUD_CORE] ⏳ Ainda aguardando login... ({tentativas//30} min)')
        
        time.sleep(1)  # Aguardar 1 segundo antes da próxima verificação
    
    if login_detectado:
        print('[SISBAJUD_CORE] ✅ Login manual detectado com sucesso!')
        
        # Salvar cookies após login bem-sucedido
        print('[SISBAJUD_CORE] 💾 Salvando cookies para login automático futuro...')
        try:
            salvar_cookies_sisbajud(driver)
        except Exception as e:
            print(f'[SISBAJUD_CORE] ❌ Falha ao salvar cookies: {e}')
        
        return True
    else:
        print('[SISBAJUD_CORE] ⚠️ Timeout aguardando login manual (5 minutos). Continuando mesmo assim...')
        return False

def verificar_login_sisbajud(driver):
    """
    Verifica se o usuário está logado no SISBAJUD
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        bool: True se está logado
    """
    try:
        current_url = driver.current_url
        
        # Verificar se não está na tela de login
        if any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
            return False
        
        # Verificar elementos que indicam login
        elementos_logado = driver.execute_script("""
            let indicadores = [
                'mat-toolbar',
                '.mat-toolbar',
                'button[aria-label*="menu"]',
                'sisbajud-home',
                'sisbajud-consulta',
                'sisbajud-minuta'
            ];
            
            for (let seletor of indicadores) {
                if (document.querySelector(seletor)) {
                    return true;
                }
            }
            return false;
        """)
        
        return bool(elementos_logado)
        
    except Exception as e:
        print(f'[SISBAJUD_CORE] ❌ Erro ao verificar login: {e}')
        return False

def tentar_login_automatico_ahk(driver):
    """
    Tenta fazer login automático usando AutoHotkey
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        bool: True se login foi bem-sucedido
    """
    print('[SISBAJUD_CORE] 🔧 Tentando login automático via AHK...')
    
    try:
        # Obter caminho do AutoHotkey
        ahk_path = obter_caminho_autohotkey()
        if not ahk_path:
            print('[SISBAJUD_CORE] ❌ AutoHotkey não encontrado')
            return False
        
        # Definir script AHK para login
        script_ahk = os.path.join(os.path.dirname(__file__), '..', 'loginsisb.ahk')
        
        if not os.path.exists(script_ahk):
            print(f'[SISBAJUD_CORE] ❌ Script AHK não encontrado: {script_ahk}')
            return False
        
        # Executar script AHK
        import subprocess
        result = subprocess.run([ahk_path, script_ahk], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print('[SISBAJUD_CORE] ✅ Script AHK executado com sucesso')
            
            # Aguardar um pouco e verificar se login funcionou
            time.sleep(5)
            
            if verificar_login_sisbajud(driver):
                print('[SISBAJUD_CORE] ✅ Login automático AHK realizado com sucesso!')
                return True
            else:
                print('[SISBAJUD_CORE] ❌ Login AHK executado mas não detectado')
                return False
        else:
            print(f'[SISBAJUD_CORE] ❌ Erro ao executar script AHK: {result.stderr}')
            return False
            
    except Exception as e:
        print(f'[SISBAJUD_CORE] ❌ Erro no login AHK: {e}')
        return False

def obter_caminho_autohotkey():
    """
    Obtém o caminho do executável AutoHotkey
    
    Returns:
        str: Caminho do AutoHotkey ou None se não encontrado
    """
    try:
        import shutil
        
        # Tentar encontrar AutoHotkey no PATH
        ahk_path = shutil.which('autohotkey.exe')
        if ahk_path:
            return ahk_path
        
        # Tentar caminhos padrão
        caminhos_padrao = [
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
            r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
            r"C:\AutoHotkey\AutoHotkey.exe"
        ]
        
        for caminho in caminhos_padrao:
            if os.path.exists(caminho):
                return caminho
        
        print('[SISBAJUD_CORE] ❌ AutoHotkey não encontrado no sistema')
        return None
        
    except Exception as e:
        print(f'[SISBAJUD_CORE] ❌ Erro ao buscar AutoHotkey: {e}')
        return None

def main_teste_sisbajud():
    """
    Função principal para teste do SISBAJUD
    """
    print('🧪 === TESTE DO SISBAJUD ===')
    print('=' * 60)
    print()
    
    print('Este modo irá:')
    print('1. ✅ Iniciar apenas o Driver SISBAJUD')
    print('2. 🤖 Tentar login automático via cookies')
    print('3. 🔧 Se falhar, tentar login automático via AHK')
    print('4. 👤 Se falhar, permitir login manual')
    print('5. 🚀 Inicializar todas as automações do SISBAJUD')
    print()
    
    confirmar = input('Deseja prosseguir com o teste? (s/n): ').lower().strip()
    
    if confirmar != 's':
        print('❌ Teste cancelado pelo usuário.')
        return
    
    print()
    print('🚀 Iniciando teste do SISBAJUD...')
    
    try:
        # Executar o Driver SISBAJUD em modo teste
        driver_sisbajud = executar_driver_sisbajud(modo_teste=True)
        
        if driver_sisbajud:
            print('')
            print('✅ Driver SISBAJUD iniciado com sucesso!')
            print('🔄 Monitoramento ativo. O driver continuará rodando...')
            print('💡 Pressione Ctrl+C para encerrar.')
            
            # Monitorar o driver
            try:
                from .utils import monitorar_driver_sisbajud
                monitorar_driver_sisbajud(driver_sisbajud)
            except ImportError:
                print('[SISBAJUD_CORE] ⚠️ Função monitorar_driver_sisbajud não disponível')
                
                # Monitoramento básico
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print('\n⏹️ Teste interrompido pelo usuário.')
                    from .drivers import fechar_driver_seguro
                    fechar_driver_seguro(driver_sisbajud)
            
        else:
            print('❌ Falha ao iniciar o Driver SISBAJUD.')
            
    except KeyboardInterrupt:
        print('\n⏹️ Teste interrompido pelo usuário.')
    except Exception as e:
        print(f'\n❌ Erro durante o teste: {e}')
        import traceback
        traceback.print_exc()
