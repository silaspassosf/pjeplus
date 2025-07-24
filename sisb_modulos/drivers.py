#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/DRIVERS.PY
Gestão de drivers Selenium para SISBAJUD/BACEN
Extraído do bacen.py original
"""

import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from .config import FIREFOX_CONFIG, TIMEOUTS
from .cookies import carregar_cookies_sisbajud

def driver_firefox_sisbajud(headless=False):
    """
    Retorna um driver Firefox usando o perfil dedicado do SISBAJUD
    
    Args:
        headless: Se deve executar em modo headless
        
    Returns:
        webdriver.Firefox: Driver Firefox configurado
    """
    try:
        print('[DRIVERS] 🔄 Criando driver Firefox SISBAJUD (perfil dedicado)...')
        
        options = Options()
        if headless:
            options.add_argument('--headless')
            
        options.binary_location = FIREFOX_CONFIG['firefox_binary']
        options.set_preference('profile', FIREFOX_CONFIG['profile_path'])
        
        service = Service(executable_path=FIREFOX_CONFIG['geckodriver_path'])
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(FIREFOX_CONFIG['implicit_wait'])
        
        print('[DRIVERS] ✅ Driver Firefox SISBAJUD criado com sucesso!')
        return driver
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao criar driver Firefox SISBAJUD: {e}')
        return None

def criar_driver_firefox_sisb():
    """
    Cria driver Firefox para SISBAJUD automaticamente - versão otimizada com cookies
    
    Returns:
        webdriver.Firefox: Driver Firefox configurado ou None se erro
    """
    print('[DRIVERS] 🔄 Criando driver Firefox SISBAJUD (versão otimizada com cookies)...')
    
    # Tentar primeiro a abordagem simples que funciona
    try:
        print('[DRIVERS] 🔄 Iniciando Firefox Developer Edition (modo otimizado)...')
        
        options = Options()
        options.binary_location = FIREFOX_CONFIG['firefox_binary']
        options.add_argument("--new-instance")
        options.add_argument("--no-remote")
        
        driver = webdriver.Firefox(options=options)
        print('[DRIVERS] ✅ Firefox SISBAJUD iniciado com sucesso!')
        
        # Aguardar estabilização
        time.sleep(1)
        
        # Tentar carregar cookies salvos primeiro
        print('[DRIVERS] 🔄 Tentando carregar cookies salvos...')
        cookies_carregados = carregar_cookies_sisbajud(driver)
        
        if cookies_carregados:
            print('[DRIVERS] ✅ Cookies carregados! Verificando se login automático funcionou...')
            
            # Verificar se já está logado (não está na tela de login)
            current_url = driver.current_url
            if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                print('[DRIVERS] ✅ Login automático realizado com sucesso via cookies!')
                return driver
            else:
                print('[DRIVERS] ⚠️ Cookies carregados mas ainda na tela de login. Prosseguindo...')
        else:
            print('[DRIVERS] 🔄 Navegando automaticamente para SISBAJUD...')
            url_login = 'https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud&redirect_uri=https%3A%2F%2Fsisbajud.cnj.jus.br%2F&state=da9cbb01-be67-419d-8f19-f2c067a9e80f&response_mode=fragment&response_type=code&scope=openid&nonce=3d61a8ca-bb98-4924-88f9-9a0cb00f9f0e'
            driver.get(url_login)
        
        return driver
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Falha na abordagem otimizada: {e}')
        
        # Fallback: tentar com perfil específico apenas se a abordagem simples falhar
        try:
            print('[DRIVERS] 🔄 Tentando com perfil específico como fallback...')
            
            options_perfil = Options()
            options_perfil.binary_location = FIREFOX_CONFIG['firefox_binary']
            options_perfil.add_argument(f"--profile={FIREFOX_CONFIG['profile_path']}")
            options_perfil.add_argument("--new-instance")
            options_perfil.add_argument("--no-remote")
            
            driver = webdriver.Firefox(options=options_perfil)
            print('[DRIVERS] ✅ Firefox SISBAJUD iniciado com perfil específico!')
            
            time.sleep(1)
            url_login = 'https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud&redirect_uri=https%3A%2F%2Fsisbajud.cnj.jus.br%2F&state=da9cbb01-be67-419d-8f19-f2c067a9e80f&response_mode=fragment&response_type=code&scope=openid&nonce=3d61a8ca-bb98-4924-88f9-9a0cb00f9f0e'
            driver.get(url_login)
            
            return driver
            
        except Exception as e2:
            print(f'[DRIVERS] ❌ Falha no fallback com perfil: {e2}')
            print('[DRIVERS] ❌ Não foi possível criar o driver SISBAJUD')
            return None

def criar_driver_firefox_generico(headless=False, perfil_path=None):
    """
    Cria um driver Firefox genérico
    
    Args:
        headless: Se deve executar em modo headless
        perfil_path: Caminho do perfil personalizado (opcional)
        
    Returns:
        webdriver.Firefox: Driver Firefox configurado
    """
    try:
        print('[DRIVERS] 🔄 Criando driver Firefox genérico...')
        
        options = Options()
        if headless:
            options.add_argument('--headless')
            
        options.binary_location = FIREFOX_CONFIG['firefox_binary']
        
        if perfil_path:
            options.add_argument(f"--profile={perfil_path}")
            
        service = Service(executable_path=FIREFOX_CONFIG['geckodriver_path'])
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(FIREFOX_CONFIG['implicit_wait'])
        
        print('[DRIVERS] ✅ Driver Firefox genérico criado com sucesso!')
        return driver
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao criar driver Firefox genérico: {e}')
        return None

def configurar_timeouts(driver):
    """
    Configura timeouts para um driver
    
    Args:
        driver: WebDriver Selenium
    """
    try:
        driver.implicitly_wait(TIMEOUTS['implicit_wait'])
        driver.set_page_load_timeout(TIMEOUTS['page_load'])
        driver.set_script_timeout(TIMEOUTS['script_timeout'])
        
        print('[DRIVERS] ✅ Timeouts configurados')
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao configurar timeouts: {e}')

def verificar_driver_funcional(driver):
    """
    Verifica se o driver está funcional
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        bool: True se driver está funcional
    """
    try:
        # Tentar executar um comando simples
        driver.execute_script("return document.readyState;")
        return True
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Driver não funcional: {e}')
        return False

def fechar_driver_seguro(driver):
    """
    Fecha o driver de forma segura
    
    Args:
        driver: WebDriver Selenium
    """
    try:
        if driver:
            driver.quit()
            print('[DRIVERS] ✅ Driver fechado com sucesso')
        else:
            print('[DRIVERS] ⚠️ Driver já estava fechado')
            
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao fechar driver: {e}')

def obter_info_driver(driver):
    """
    Obtém informações do driver
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        dict: Informações do driver
    """
    try:
        info = {
            'url_atual': driver.current_url,
            'titulo': driver.title,
            'window_handles': len(driver.window_handles),
            'capabilities': driver.capabilities,
            'funcional': verificar_driver_funcional(driver)
        }
        
        return info
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao obter info do driver: {e}')
        return {'erro': str(e)}

def trocar_para_janela(driver, indice_janela=0):
    """
    Troca para uma janela específica
    
    Args:
        driver: WebDriver Selenium
        indice_janela: Índice da janela (0 = primeira)
        
    Returns:
        bool: True se conseguiu trocar
    """
    try:
        handles = driver.window_handles
        
        if indice_janela < len(handles):
            driver.switch_to.window(handles[indice_janela])
            print(f'[DRIVERS] ✅ Trocado para janela {indice_janela}')
            return True
        else:
            print(f'[DRIVERS] ❌ Janela {indice_janela} não existe')
            return False
            
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao trocar janela: {e}')
        return False

def maximizar_janela(driver):
    """
    Maximiza a janela do driver
    
    Args:
        driver: WebDriver Selenium
    """
    try:
        driver.maximize_window()
        print('[DRIVERS] ✅ Janela maximizada')
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao maximizar janela: {e}')

def limpar_cache_driver(driver):
    """
    Limpa cache e cookies do driver
    
    Args:
        driver: WebDriver Selenium
    """
    try:
        # Limpar cookies
        driver.delete_all_cookies()
        
        # Limpar localStorage e sessionStorage
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        
        print('[DRIVERS] ✅ Cache e cookies limpos')
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Erro ao limpar cache: {e}')

def aguardar_pagina_carregar(driver, timeout=None):
    """
    Aguarda a página carregar completamente
    
    Args:
        driver: WebDriver Selenium
        timeout: Timeout em segundos (usa padrão se None)
        
    Returns:
        bool: True se página carregou
    """
    try:
        if timeout is None:
            timeout = TIMEOUTS['page_load']
            
        # Aguardar document.readyState ser 'complete'
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(driver, timeout)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        print('[DRIVERS] ✅ Página carregada completamente')
        return True
        
    except Exception as e:
        print(f'[DRIVERS] ❌ Timeout ao aguardar página carregar: {e}')
        return False
