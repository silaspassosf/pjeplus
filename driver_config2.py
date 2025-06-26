# driver_config.py
"""
Centralização de drivers e métodos de login para múltiplas máquinas.
Selecione o par ativo descomentando a linha correspondente ao final do arquivo.
"""

def criar_driver_PC(headless=False):
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import time
    PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    GECKODRIVER_PATH = r"d:\PjePlus\geckodriver.exe"
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    return driver

def login_PC(driver):
    """Processo de login humanizado via AutoHotkey, aguardando login terminar antes de prosseguir."""
    from selenium.webdriver.common.by import By
    import time
    import subprocess
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    print("[DEBUG] Iniciando login_PC")
    driver.get(login_url)
    print(f"[DEBUG] Navegando para a URL de login: {login_url}")
    try:
        print("[DEBUG] Procurando botão #btnSsoPdpj...")
        btn_sso = driver.find_element(By.CSS_SELECTOR, "#btnSsoPdpj")
        print("[DEBUG] Botão #btnSsoPdpj encontrado, clicando...")
        btn_sso.click()
        print("[DEBUG] Procurando botão .botao-certificado-titulo...")
        btn_certificado = driver.find_element(By.CSS_SELECTOR, ".botao-certificado-titulo")
        print("[DEBUG] Botão .botao-certificado-titulo encontrado, aguardando 3s antes de clicar...")
        time.sleep(3)  # Espera 3 segundos antes do clique para evitar erro de timing
        print("[DEBUG] Clicando no botão de certificado via JavaScript (método original)...")
        driver.execute_script("arguments[0].click();", btn_certificado)
        print("[DEBUG] Chamando AutoHotkey para digitar a senha...")
        subprocess.Popen([r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe", r"D:\\PjePlus\\Login.ahk"])
        print("[DEBUG] Script AutoHotkey chamado. Continuando execução.")
        
        # O login acontece rapidamente. A verificação de URL será feita pelo código chamador quando necessário.
        # A URL para verificar login bem-sucedido é: https://pje.trt2.jus.br/pjekz/gigs/meu-painel
        return True
    except Exception as e:
        print(f"[ERRO] Falha no processo de login: {e}")
        return False

# --- Perfil VT (p2t) ---
def criar_driver_VT(headless=False):
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2y17wq63.default'
    service = Service(executable_path=r'C:\Users\s164283\Desktop\pjeplus\geckodriver.exe')
    driver = webdriver.Firefox(
        options=options,
        service=service
    )
    return driver

def login_VT(driver):
    # Login manual: apenas navega para a tela de login e aguarda o usuário
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    print(f'[LOGIN_VT] Navegando para tela de login: {url_login}')
    driver.get(url_login)
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    print(f'[LOGIN_VT] Aguarde, faça o login manualmente e navegue até: {painel_url}')
    while True:
        try:
            if driver.current_url.startswith(painel_url):
                print('[LOGIN_VT] Painel detectado! Prosseguindo com automação...')
                break
        except Exception:
            pass
        import time
        time.sleep(1)

def criar_driver_manual(headless=False):
    # Usa o mesmo driver padrão (PC), mas pode ser customizado se necessário
    return criar_driver_PC(headless=headless)

def login_manual(driver):
    """
    Login manual: apenas navega para a tela de login e aguarda o usuário realizar o login manualmente.
    Prossegue automaticamente quando o usuário acessa a URL do painel.
    """
    import time
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    print(f'[LOGIN_MANUAL] Navegando para tela de login: {url_login}')
    driver.get(url_login)
    print(f'[LOGIN_MANUAL] Aguarde, faça o login manualmente e navegue até: {painel_url}')
    
    # Espera até detectar a URL do painel
    print('[LOGIN_MANUAL] Monitorando URL para detecção automática do login bem-sucedido...')
    while True:
        try:
            if driver.current_url.startswith(painel_url):
                print(f'[LOGIN_MANUAL] Painel detectado! URL: {driver.current_url}')
                print('[LOGIN_MANUAL] Login manual concluído. Prosseguindo com automação.')
                return True  # Retorna True para indicar que o login foi bem-sucedido
        except Exception as e:
            print(f'[LOGIN_MANUAL][ERRO] Erro ao verificar URL: {e}')
        time.sleep(1)

# ======= SELECIONE O DRIVER E LOGIN ATIVOS =======
criar_driver = criar_driver_PC
# login_func = login_PC    # Login automático com certificado e AutoHotkey
login_func = login_manual  # Login manual monitorando URL do painel (recomendado se o login automático estiver falhando)
# Para ativar o perfil VT, descomente as linhas abaixo e comente as demais:
# criar_driver = criar_driver_VT
# login_func = login_VT
# ATENÇÃO: Todas as funções de login (PC, manual, VT) retornam True quando bem-sucedidas
# para garantir que o fluxo de automação continue normalmente após o login.
