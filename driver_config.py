# driver_config.py
"""
Configuração modular de drivers e métodos de login para múltiplas máquinas.
ESTRUTURA:
1. BLOCO LOGIN: Manual ou Automático
2. BLOCO DRIVER: PC, VT ou Notebook
Selecione um de cada bloco no final do arquivo.
"""

# ===============================================
# BLOCO 1: CONFIGURAÇÕES DE LOGIN
# ===============================================

def login_manual(driver, aguardar_url_painel=True):
    """Login manual: navega para login e aguarda usuário fazer login"""
    # Primeiro tenta carregar cookies salvos
    if verificar_e_aplicar_cookies(driver):
        # Salva cookies atualizados após sucesso
        if SALVAR_COOKIES_AUTOMATICO:
            salvar_cookies_sessao(driver, info_extra='cookies_reutilizados')
        return True
    
    # Se cookies não funcionaram, faz login manual
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    print(f'[LOGIN_MANUAL] Navegando para tela de login: {url_login}')
    driver.get(url_login)
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    print(f'[LOGIN_MANUAL] Aguarde, faça o login manualmente e navegue até: {painel_url}')
    
    if aguardar_url_painel:
        while True:
            try:
                if driver.current_url.startswith(painel_url):
                    print('[LOGIN_MANUAL] Painel detectado! Login realizado com sucesso.')
                    # Salva cookies após login manual bem-sucedido
                    if SALVAR_COOKIES_AUTOMATICO:
                        salvar_cookies_sessao(driver, info_extra='login_manual')
                    break
            except Exception:
                pass
            import time
            time.sleep(1)
    return True

def login_automatico(driver):
    """Login automático via AutoHotkey (certificado digital)"""
    # Primeiro tenta carregar cookies salvos
    if verificar_e_aplicar_cookies(driver):
        # Salva cookies atualizados após sucesso
        if SALVAR_COOKIES_AUTOMATICO:
            salvar_cookies_sessao(driver, info_extra='cookies_reutilizados')
        return True
    
    # Se cookies não funcionaram, faz login automático
    from selenium.webdriver.common.by import By
    import time
    import subprocess
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    print(f"[LOGIN_AUTOMATICO] Navegando para a URL de login: {login_url}")
    try:
        btn_sso = driver.find_element(By.CSS_SELECTOR, "#btnSsoPdpj")
        btn_sso.click()
        print("[LOGIN_AUTOMATICO] Botão #btnSsoPdpj clicado com sucesso.")
        btn_certificado = driver.find_element(By.CSS_SELECTOR, ".botao-certificado-titulo")
        btn_certificado.click()
        print("[LOGIN_AUTOMATICO] Botão .botao-certificado-titulo clicado com sucesso.")
        # Chama o AutoHotkey para digitar a senha
        subprocess.Popen([r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe", r"D:\\PjePlus\\Login.ahk"])
        print("[LOGIN_AUTOMATICO] Script AutoHotkey chamado para digitar a senha.")
        # Aguarda sair da tela de login
        for _ in range(60):
            if "login" not in driver.current_url.lower():
                print("[LOGIN_AUTOMATICO] Login detectado, prosseguindo.")
                # Salva cookies após login automático bem-sucedido
                if SALVAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_automatico')
                return True
            time.sleep(1)
        print("[ERRO] Timeout aguardando login.")
        return False
    except Exception as e:
        print(f"[ERRO] Falha no processo de login: {e}")
        return False

def login_automatico_direto(driver):
    """Login automático DIRETO via AutoHotkey (certificado digital) - SEM tentar cookies"""
    from selenium.webdriver.common.by import By
    import time
    import subprocess
    
    print('[LOGIN_AUTOMATICO_DIRETO] Iniciando login direto sem cookies...')
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    print(f"[LOGIN_AUTOMATICO_DIRETO] Navegando para a URL de login: {login_url}")
    
    try:
        btn_sso = driver.find_element(By.CSS_SELECTOR, "#btnSsoPdpj")
        btn_sso.click()
        print("[LOGIN_AUTOMATICO_DIRETO] Botão #btnSsoPdpj clicado com sucesso.")
        
        btn_certificado = driver.find_element(By.CSS_SELECTOR, ".botao-certificado-titulo")
        btn_certificado.click()
        print("[LOGIN_AUTOMATICO_DIRETO] Botão .botao-certificado-titulo clicado com sucesso.")
        
        # Chama o AutoHotkey para digitar a senha
        subprocess.Popen([r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe", r"D:\\PjePlus\\Login.ahk"])
        print("[LOGIN_AUTOMATICO_DIRETO] Script AutoHotkey chamado para digitar a senha.")
        
        # Aguarda sair da tela de login
        for _ in range(60):
            if "login" not in driver.current_url.lower():
                print("[LOGIN_AUTOMATICO_DIRETO] Login detectado, prosseguindo.")
                # Salva cookies após login automático bem-sucedido
                if SALVAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_automatico_direto')
                return True
            time.sleep(1)
        
        print("[LOGIN_AUTOMATICO_DIRETO] Timeout aguardando login.")
        return False
        
    except Exception as e:
        print(f"[LOGIN_AUTOMATICO_DIRETO] Falha no processo de login: {e}")
        return False

# ===============================================
# BLOCO 2: CONFIGURAÇÕES DE DRIVER
# ===============================================

def criar_driver_PC(headless=False):
    """Driver PC - Perfil personalizado Selenium"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    options.set_preference('profile', r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium")
    service = Service(executable_path=r"d:\PjePlus\geckodriver.exe")
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    print("[DRIVER_PC] Driver PC criado com sucesso")
    return driver

def criar_driver_VT(headless=False):
    """Driver VT - Perfil padrão"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2y17wq63.default'
    service = Service(executable_path=r'C:\Users\s164283\Desktop\pjeplus\geckodriver.exe')
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_VT] Driver VT criado com sucesso")
    return driver

def criar_driver_notebook(headless=False):
    """Driver Notebook - Perfil Robot"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
    service = Service(executable_path=r'C:\Users\s164283\Desktop\pjeplus\geckodriver.exe')
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_NOTEBOOK] Driver Notebook criado com sucesso")
    return driver

# ===============================================
# CONFIGURAÇÃO ATIVA
# ===============================================

# BLOCO 1: ESCOLHA DO LOGIN (descomente apenas uma linha)
# login_func = login_manual        # ← Login manual
login_func = login_automatico    # ← ATIVO: Login automático via AutoHotkey

# BLOCO 2: ESCOLHA DO DRIVER (descomente apenas uma linha)
criar_driver = criar_driver_PC       # ← ATIVO: Driver PC
# criar_driver = criar_driver_VT       # ← Driver VT
# criar_driver = criar_driver_notebook # ← Driver Notebook

# ===============================================
# SISTEMA INTELIGENTE DE COOKIES DE SESSÃO
# ===============================================

import os
import json
from datetime import datetime, timedelta
import glob

def salvar_cookies_sessao(driver, caminho_arquivo=None, info_extra=None):
    """
    Salva todos os cookies da sessão Selenium em um arquivo JSON.
    O nome do arquivo inclui data/hora e info_extra se fornecido.
    """
    try:
        cookies = driver.get_cookies()
        if not cookies:
            print('[COOKIES] Nenhum cookie encontrado para salvar.')
            return False
        if not caminho_arquivo:
            pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
            os.makedirs(pasta, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            info = f'_{info_extra}' if info_extra else ''
            caminho_arquivo = os.path.join(pasta, f'cookies_sessao{info}_{timestamp}.json')
        
        # Adiciona metadados para validação
        dados_cookies = {
            'timestamp': datetime.now().isoformat(),
            'url_base': driver.current_url,
            'cookies': cookies
        }
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_cookies, f, ensure_ascii=False, indent=2)
        print(f'[COOKIES] Cookies salvos em: {caminho_arquivo}')
        return True
    except Exception as e:
        print(f'[COOKIES][ERRO] Falha ao salvar cookies: {e}')
        return False

def carregar_cookies_sessao(driver, max_idade_horas=24):
    """
    Carrega cookies de sessão mais recentes e válidos automaticamente.
    Retorna True se cookies foram carregados com sucesso, False caso contrário.
    """
    try:
        pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
        if not os.path.exists(pasta):
            print('[COOKIES] Pasta de cookies não encontrada.')
            return False
        
        # Busca todos os arquivos de cookies
        arquivos_cookies = glob.glob(os.path.join(pasta, 'cookies_sessao*.json'))
        if not arquivos_cookies:
            print('[COOKIES] Nenhum arquivo de cookies encontrado.')
            return False
        
        # Encontra o arquivo mais recente
        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Verifica se é formato antigo ou novo
        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados['cookies']
        else:
            # Formato antigo - usa timestamp do arquivo
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados
        
        # Verifica idade dos cookies
        timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.now() - timestamp_cookies
        
        if idade > timedelta(hours=max_idade_horas):
            print(f'[COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h). Pulando.')
            return False
        
        # Navega para o domínio antes de carregar cookies
        driver.get('https://pje.trt2.jus.br/primeirograu/')
        
        # Carrega cookies
        cookies_carregados = 0
        for cookie in cookies:
            try:
                # Remove campos que podem causar problemas
                cookie_limpo = {k: v for k, v in cookie.items() if k not in ['expiry', 'httpOnly', 'secure', 'sameSite']}
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
            except Exception as e:
                print(f'[COOKIES] Erro ao carregar cookie {cookie.get("name", "unknown")}: {e}')
        
        print(f'[COOKIES] {cookies_carregados} cookies carregados de {os.path.basename(arquivo_mais_recente)}')
        
        # Testa se os cookies funcionam navegando para uma página protegida
        driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        
        # Aguarda um pouco para a página carregar
        import time
        time.sleep(3)
        
        # Verifica se recebeu a URL de acesso negado
        if 'acesso-negado' in driver.current_url.lower():
            print('[COOKIES] URL de acesso negado detectada. Apagando cookies e iniciando login automático direto...')
            # Apaga todos os cookies do navegador
            try:
                driver.delete_all_cookies()
                print('[COOKIES] Cookies apagados do navegador.')
            except Exception as e:
                print(f'[COOKIES] Erro ao apagar cookies: {e}')
            
            # Chama login automático DIRETO (sem tentar cookies novamente)
            try:
                return login_automatico_direto(driver)
            except Exception as e:
                print(f'[COOKIES][ERRO] Falha no login automático direto após acesso negado: {e}')
                return False
        
        # Verifica se está logado (não é redirecionado para login)
        if 'login' in driver.current_url.lower():
            print('[COOKIES] Cookies inválidos - ainda redirecionando para login.')
            return False
        else:
            print('[COOKIES] ✅ Cookies válidos! Login automático realizado.')
            return True
            
    except Exception as e:
        print(f'[COOKIES][ERRO] Falha ao carregar cookies: {e}')
        return False

def verificar_e_aplicar_cookies(driver):
    """
    Função integrada que verifica e aplica cookies automaticamente.
    Retorna True se login via cookies foi bem-sucedido.
    """
    if not USAR_COOKIES_AUTOMATICO:
        return False
    
    print('[COOKIES] Tentando login automático via cookies salvos...')
    sucesso = carregar_cookies_sessao(driver)
    
    if sucesso:
        print('[COOKIES] ✅ Login realizado via cookies! Pularemos a tela de login.')
    else:
        print('[COOKIES] ❌ Cookies inválidos ou inexistentes. Login manual necessário.')
    
    return sucesso

# ===============================================
# CONFIGURAÇÕES DE COOKIES
# ===============================================
USAR_COOKIES_AUTOMATICO = True      # ← Carregar cookies automaticamente ao iniciar driver
SALVAR_COOKIES_AUTOMATICO = True    # ← Salvar cookies após login manual/automático

# ===============================================
# INFORMAÇÕES DE CONFIGURAÇÃO
# ===============================================

def exibir_configuracao_ativa():
    """Exibe qual configuração está ativa"""
    login_nome = "Manual" if login_func == login_manual else "Automático"
    
    if criar_driver == criar_driver_PC:
        driver_nome = "PC"
    elif criar_driver == criar_driver_VT:
        driver_nome = "VT"
    else:
        driver_nome = "Notebook"
    
    print(f"[CONFIG] Login: {login_nome}")
    print(f"[CONFIG] Driver: {driver_nome}")
    return login_nome, driver_nome
