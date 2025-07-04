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
    driver.get(login_url)
    print(f"[INFO] Navegando para a URL de login: {login_url}")
    try:
        btn_sso = driver.find_element(By.CSS_SELECTOR, "#btnSsoPdpj")
        btn_sso.click()
        print("[INFO] Botão #btnSsoPdpj clicado com sucesso.")
        btn_certificado = driver.find_element(By.CSS_SELECTOR, ".botao-certificado-titulo")
        btn_certificado.click()
        print("[INFO] Botão .botao-certificado-titulo clicado com sucesso.")
        # Chama o AutoHotkey para digitar a senha
        subprocess.Popen([r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe", r"D:\\PjePlus\\Login.ahk"])
        print("[INFO] Script AutoHotkey chamado para digitar a senha.")
        # Aguarda sair da tela de login
        for _ in range(60):
            if "login" not in driver.current_url.lower():
                print("[INFO] Login detectado, prosseguindo.")
                return True
            time.sleep(1)
        print("[ERRO] Timeout aguardando login.")
        return False
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

def login_VT(driver, aguardar_url_painel=True):
    # Login manual: apenas navega para a tela de login e aguarda o usuário
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    print(f'[LOGIN_VT] Navegando para tela de login: {url_login}')
    driver.get(url_login)
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    print(f'[LOGIN_VT] Aguarde, faça o login manualmente e navegue até: {painel_url}')
    if aguardar_url_painel:
        while True:
            try:
                if driver.current_url.startswith(painel_url):
                    print('[LOGIN_VT] Painel detectado! Prosseguindo com automação...')
                    break
            except Exception:
                pass
            import time
            time.sleep(1)
    # Se não aguardar, retorna imediatamente após abrir a tela de login
    return True

# ======= SELECIONE O DRIVER E LOGIN ATIVOS =======
# criar_driver = criar_driver_PC
# login_func = login_PC
criar_driver = criar_driver_VT
login_func = login_VT
# Para trocar de máquina, basta comentar/descomentar as linhas acima/abaixo.
