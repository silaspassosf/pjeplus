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
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    print(f'[LOGIN_MANUAL] Navegando para tela de login: {url_login}')
    driver.get(url_login)
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    print(f'[LOGIN_MANUAL] Aguarde, faça o login manualmente e navegue até: {painel_url}')
    if aguardar_url_painel:
        while True:
            try:
                if driver.current_url.startswith(painel_url):
                    print('[LOGIN_MANUAL] Painel detectado! Prosseguindo com automação...')
                    break
            except Exception:
                pass
            import time
            time.sleep(1)
    return True

def login_automatico(driver):
    """Login automático via AutoHotkey (certificado digital)"""
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
                return True
            time.sleep(1)
        print("[ERRO] Timeout aguardando login.")
        return False
    except Exception as e:
        print(f"[ERRO] Falha no processo de login: {e}")
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
login_func = login_manual        # ← ATIVO: Login manual
# login_func = login_automatico    # ← Login automático via AutoHotkey

# BLOCO 2: ESCOLHA DO DRIVER (descomente apenas uma linha)
# criar_driver = criar_driver_PC       # ← Driver PC
# criar_driver = criar_driver_VT       # ← Driver VT
criar_driver = criar_driver_notebook # ← ATIVO: Driver Notebook

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
