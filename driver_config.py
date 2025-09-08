# driver_config.py
"""
Configuração modular de drivers e métodos de login para múltiplas máquinas.
ESTRUTURA:
1. BLOCO LOGIN: Manual ou Automático
2. BLOCO DRIVER: PC, VT ou Notebook
Selecione um de cada bloco no final do arquivo.
"""

# ===============================================
# CONFIGURAÇÃO GLOBAL DO GECKODRIVER
# ===============================================
import os
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')

# Verifica se o geckodriver existe
if not os.path.exists(GECKODRIVER_PATH):
    print(f'[DRIVER_CONFIG] ⚠️ AVISO: Geckodriver não encontrado em {GECKODRIVER_PATH}')
    print('[DRIVER_CONFIG] Baixe o geckodriver de: https://github.com/mozilla/geckodriver/releases')
else:
    print(f'[DRIVER_CONFIG] ✅ Geckodriver encontrado: {GECKODRIVER_PATH}')

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
        # Seleciona caminhos do AutoHotkey conforme a configuração ativa (PC x NOTEBOOK)
        try:
            # Prefer explicit active variables if defined
            ahk_exe = globals().get('AHK_EXE_ACTIVE')
            ahk_script = globals().get('AHK_SCRIPT_ACTIVE')
            if not ahk_exe or not ahk_script:
                # Fallback para seleção baseada no driver ativo
                if globals().get('criar_driver') == globals().get('criar_driver_notebook'):
                    ahk_exe = globals().get('AHK_EXE_NOTEBOOK')
                    ahk_script = globals().get('AHK_SCRIPT_NOTEBOOK')
                else:
                    ahk_exe = globals().get('AHK_EXE_PC')
                    ahk_script = globals().get('AHK_SCRIPT_PC')
        except Exception:
            ahk_exe = globals().get('AHK_EXE_PC')
            ahk_script = globals().get('AHK_SCRIPT_PC')

        # Valida existência dos caminhos antes de chamar
        import os
        if not ahk_exe or not os.path.exists(ahk_exe):
            print(f"[LOGIN_AUTOMATICO][ERRO] Executável AutoHotkey não encontrado: {ahk_exe}")
            return False
        if not ahk_script or not os.path.exists(ahk_script):
            print(f"[LOGIN_AUTOMATICO][ERRO] Script AutoHotkey não encontrado: {ahk_script}")
            return False

        # Chama o AutoHotkey para digitar a senha
        subprocess.Popen([ahk_exe, ahk_script])
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
        
        # Seleciona caminhos do AutoHotkey conforme a configuração ativa (PC x NOTEBOOK)
        try:
            ahk_exe = globals().get('AHK_EXE_ACTIVE')
            ahk_script = globals().get('AHK_SCRIPT_ACTIVE')
            if not ahk_exe or not ahk_script:
                if globals().get('criar_driver') == globals().get('criar_driver_notebook'):
                    ahk_exe = globals().get('AHK_EXE_NOTEBOOK')
                    ahk_script = globals().get('AHK_SCRIPT_NOTEBOOK')
                else:
                    ahk_exe = globals().get('AHK_EXE_PC')
                    ahk_script = globals().get('AHK_SCRIPT_PC')
        except Exception:
            ahk_exe = globals().get('AHK_EXE_PC')
            ahk_script = globals().get('AHK_SCRIPT_PC')

        import os
        if not ahk_exe or not os.path.exists(ahk_exe):
            print(f"[LOGIN_AUTOMATICO_DIRETO][ERRO] Executável AutoHotkey não encontrado: {ahk_exe}")
            return False
        if not ahk_script or not os.path.exists(ahk_script):
            print(f"[LOGIN_AUTOMATICO_DIRETO][ERRO] Script AutoHotkey não encontrado: {ahk_script}")
            return False

        # Chama o AutoHotkey para digitar a senha
        subprocess.Popen([ahk_exe, ahk_script])
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

def login_cpf(driver, url_login=None, cpf='35305203813', senha='SpF59866', aguardar_url_final=True):
    """Login automático por CPF/senha (typing) — reproduz ações similares ao login_automatico_sisbajud.

    Parâmetros:
        driver: WebDriver
        url_login: URL inicial para navegar ao formulário de login (se None, usa PJe padrão)
        cpf: CPF a ser digitado no campo 'username'
        senha: senha a ser digitada no campo 'password'
        aguardar_url_final: se True espera até detectar redirecionamento pós-login

    Retorna True se o login for detectado com sucesso, False caso contrário.
    """
    try:
        # tentar aplicar cookies previamente salvos
        if verificar_e_aplicar_cookies(driver):
            if SALVAR_COOKIES_AUTOMATICO:
                try:
                    salvar_cookies_sessao(driver, info_extra='cookies_reutilizados_login_cpf')
                except Exception:
                    pass
            return True

        from selenium.webdriver.common.by import By
        import time

        if not url_login:
            # URL padrão (PJe primeiro grau) — pode ser sobrescrita ao chamar
            url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'

        print(f"[LOGIN_CPF] Navegando para: {url_login}")
        driver.get(url_login)
        time.sleep(1.2)

        # Se já estamos logados (URL não contém 'login'/'auth'), retorna True
        try:
            cur = driver.current_url.lower()
            if not any(k in cur for k in ['login', 'auth', 'realms']):
                print('[LOGIN_CPF] ✅ Já autenticado (URL indica sessão ativa)')
                return True
        except Exception:
            pass

        # Clicar no botão SSO PDPJ antes de preencher credenciais
        try:
            btn_sso = driver.find_element(By.ID, 'btnSsoPdpj')
            btn_sso.click()
            print('[LOGIN_CPF] ✅ Botão SSO PDPJ clicado')
            time.sleep(1.0)  # Aguardar carregamento do formulário
        except Exception as e:
            print(f"[LOGIN_CPF] ❌ Falha ao clicar no botão SSO PDPJ: {e}")
            return False

        # Digitar CPF no campo username
        try:
            username_field = driver.find_element(By.ID, 'username')
            username_field.clear()
            for ch in str(cpf):
                username_field.send_keys(ch)
                time.sleep(0.07)
            print('[LOGIN_CPF] ✅ CPF digitado')
        except Exception as e:
            print(f"[LOGIN_CPF] ❌ Não foi possível preencher CPF: {e}")
            return False

        # Digitar senha no campo password
        try:
            password_field = driver.find_element(By.ID, 'password')
            password_field.clear()
            for ch in str(senha):
                password_field.send_keys(ch)
                time.sleep(0.07)
            print('[LOGIN_CPF] ✅ Senha digitada')
        except Exception as e:
            print(f"[LOGIN_CPF] ❌ Não foi possível preencher senha: {e}")
            return False

        # Clicar no botão de login (id comum do Keycloak)
        try:
            btn = driver.find_element(By.ID, 'kc-login')
            btn.click()
            print('[LOGIN_CPF] ✅ Botão de login clicado')
        except Exception as e:
            print(f"[LOGIN_CPF] ❌ Falha ao clicar no botão de login: {e}")
            return False

        # Aguardar redirecionamento/URL final
        if aguardar_url_final:
            timeout = 40
            inicio = time.time()
            while time.time() - inicio < timeout:
                try:
                    cur = driver.current_url.lower()
                    if 'pjekz' in cur or 'sisbajud' in cur or not any(k in cur for k in ['login', 'auth', 'realms']):
                        print('[LOGIN_CPF] ✅ Login detectado por mudança de URL')
                        # salvar cookies quando configurado
                        try:
                            if SALVAR_COOKIES_AUTOMATICO:
                                salvar_cookies_sessao(driver, info_extra='login_cpf')
                        except Exception:
                            pass
                        return True
                except Exception:
                    pass
                time.sleep(0.5)
            print('[LOGIN_CPF] ⚠️ Timeout aguardando redirecionamento pós-login')
            return False

        # Se não aguardamos, consideramos sucesso imediato
        return True

    except Exception as e:
        print(f"[LOGIN_CPF] Erro durante login_cpf: {e}")
        return False

# ===============================================
# BLOCO 2: CONFIGURAÇÕES DE DRIVER
# ===============================================

def criar_driver_PC(headless=False):
    """Driver PC - Firefox Developer Edition com configurações otimizadas para PC"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    
    # Configurações otimizadas para Firefox PC
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
    
    # Configurações de performance
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    options.set_preference("browser.cache.offline.enable", True)
    options.set_preference("network.http.use-cache", True)
    
    # Desabilitar notificações e popups
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")
    
    # Firefox Developer Edition (como solicitado)
    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    
    # Usar geckodriver da pasta do projeto
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_PC] Driver PC (Firefox Developer Edition) criado com sucesso")
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
    options.profile = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_VT] Driver VT criado com sucesso")
    return driver



def criar_driver_notebook(headless=False):
    """Cria um WebDriver Firefox configurado para a máquina "notebook".
    Garante que o geckodriver usado é o da pasta do projeto (GECKODRIVER_PATH).
    """
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    # Use a clean temporary profile for the notebook driver to avoid loading user
    # extensions which can cause erratic behaviour and slow startup.
    # If you need to use the real user profile, set USE_USER_PROFILE_NOTEBOOK = True
    USE_USER_PROFILE_NOTEBOOK = False
    if USE_USER_PROFILE_NOTEBOOK:
        options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_NOTEBOOK] Driver NOTEBOOK criado com sucesso")
    return driver
    # ...existing code...


# ===============================================
# BLOCO 2b: CONFIGURAÇÕES DE DRIVER - SISBAJUD
# Opcional: duas opções (PC, Notebook). Reaproveitam os mesmos caminhos de geckodriver
# usados nos drivers comuns; apenas o perfil pode diferir.
# Ajuste SISB_PROFILE_NOTEBOOK se necessário.
# ===============================================

# Perfil padrão para SISBAJUD (PC). Caminho correto do perfil Sisb do Developer Edition
SISB_PROFILE_PC = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
# Perfil notebook para SISBAJUD — informe o caminho se diferente do padrão
SISB_PROFILE_NOTEBOOK = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'

def criar_driver_sisb_pc(headless=False):
    """Driver SISBAJUD - PC (Firefox Developer Edition com configurações robustas)"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
    
    options = Options()
    if headless:
        options.add_argument('--headless')
    
    # Firefox Developer Edition
    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    
    # Configurações mais robustas para evitar crash
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("startup.homepage_welcome_url", "about:blank")
    options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
    options.set_preference("browser.startup.page", 0)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    options.set_preference("browser.safebrowsing.enabled", False)
    options.set_preference("browser.safebrowsing.malware.enabled", False)
    options.set_preference("datareporting.healthreport.uploadEnabled", False)
    options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
    options.set_preference("toolkit.telemetry.enabled", False)
    
    # Tentar usar perfil específico com tratamento de erro
    try:
        if os.path.exists(SISB_PROFILE_PC):
            profile = FirefoxProfile(SISB_PROFILE_PC)
            options.profile = profile
            print(f"[DRIVER_SISB_PC] Usando perfil: {SISB_PROFILE_PC}")
        else:
            print(f"[DRIVER_SISB_PC] Perfil não encontrado: {SISB_PROFILE_PC}, usando perfil temporário")
    except Exception as e:
        print(f"[DRIVER_SISB_PC] Erro ao carregar perfil: {e}, usando perfil temporário")
    
    service = Service(executable_path=GECKODRIVER_PATH)
    
    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        print("[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition) criado com sucesso")
        return driver
    except Exception as e:
        print(f"[DRIVER_SISB_PC] Erro ao criar driver: {e}")
        # Fallback: tentar sem perfil específico
        try:
            options_fallback = Options()
            if headless:
                options_fallback.add_argument('--headless')
            options_fallback.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
            driver = webdriver.Firefox(service=service, options=options_fallback)
            driver.implicitly_wait(10)
            print("[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition - fallback) criado com sucesso")
            return driver
        except Exception as e2:
            print(f"[DRIVER_SISB_PC] Falha total ao criar driver: {e2}")
            return None

def criar_driver_sisb_notebook(headless=False):
    """Driver SISBAJUD - Notebook (usa caminhos notebook; perfil a ser informado)"""
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = SISB_PROFILE_NOTEBOOK
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    print("[DRIVER_SISB_NOTEBOOK] Driver SISBAJUD NOTEBOOK criado com sucesso")
    return driver

# Qual opção de SISBAJUD está ativa (ajuste para Notebook se preferir)
criar_driver_sisb = criar_driver_sisb_pc

# ===============================================
# CONFIGURAÇÃO ATIVA
# ===============================================

# BLOCO 1: ESCOLHA DO LOGIN (descomente apenas uma linha)
# login_func = login_manual        # ← Login manual
login_func = login_cpf    # ← ATIVO: Login por CPF/senha (typing)
# login_func = login_automatico    # ← Opcional: Login automático (AutoHotkey)

# BLOCO 2: ESCOLHA DO DRIVER (descomente apenas uma linha)
# criar_driver = criar_driver_notebook    # ← Driver Notebook
criar_driver = criar_driver_PC          # ← ATIVO: Driver PC (Firefox)
# criar_driver = criar_driver_VT          # ← Driver VT

# Sincroniza automaticamente a fábrica SISBAJUD com a opção ativa de driver
# Se o driver ativo for o notebook, usa o driver SISBAJUD notebook; caso contrário usa o PC
try:
    if criar_driver == criar_driver_notebook:
        criar_driver_sisb = criar_driver_sisb_notebook
    else:
        criar_driver_sisb = criar_driver_sisb_pc
except NameError:
    # Em caso de import/ordem diferente, mantém a configuração explícita definida anteriormente
    pass

# =========================
# CONFIGURAÇÃO AUTOHOTKEY
# Caminhos separados para PC e NOTEBOOK (preencha com seus caminhos locais)
# AHK_EXE_PC / AHK_SCRIPT_PC : usados quando o driver ativo NÃO for notebook
# AHK_EXE_NOTEBOOK / AHK_SCRIPT_NOTEBOOK : usados quando o driver ativo for notebook
# AHK_EXE_ACTIVE / AHK_SCRIPT_ACTIVE : se definidos, forçam uso explícito independentemente do criar_driver
# =========================
AHK_EXE_PC = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
AHK_SCRIPT_PC = r'D:\PjePlus\Login.ahk'

# Ajuste estes valores para o notebook quando necessário. Deixe como string vazia se não tiver.
AHK_EXE_NOTEBOOK = r'C:\Users\s164283\Downloads\AHK\AutoHotkey64.exe'
AHK_SCRIPT_NOTEBOOK = r'C:\Users\s164283\Desktop\pjeplus\login.ahk'

# Se quiser forçar um par ativo, defina AHK_EXE_ACTIVE e AHK_SCRIPT_ACTIVE como caminhos completos.
# Caso contrário, a seleção automática usará criar_driver para decidir entre PC/NOTEBOOK.
AHK_EXE_ACTIVE = None
AHK_SCRIPT_ACTIVE = None

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
            print('[COOKIES] URL de acesso negado detectada. Apagando cookies carregados; não dispararemos login automático aqui.')
            # Apaga todos os cookies do navegador
            try:
                driver.delete_all_cookies()
                print('[COOKIES] Cookies apagados do navegador.')
            except Exception as e:
                print(f'[COOKIES] Erro ao apagar cookies: {e}')
            # Não iniciar login automático aqui; retornar False para que o chamador decida o fallback
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
        # Verificar se após aplicar cookies não caiu em acesso negado
        try:
            current_url = driver.current_url
            if 'acesso-negado' in current_url:
                print('[COOKIES] ⚠️ Acesso negado detectado após aplicar cookies - forçando login CPF...')
                # Forçar login CPF quando detectar acesso negado
                from selenium.webdriver.common.by import By
                import time
                
                url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
                print(f"[COOKIES][LOGIN_FORCE] Navegando para: {url_login}")
                driver.get(url_login)
                time.sleep(1.2)
                
                # Login CPF direto
                try:
                    username_field = driver.find_element(By.NAME, 'username')
                    password_field = driver.find_element(By.NAME, 'password')
                    submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
                    
                    username_field.clear()
                    username_field.send_keys('35305203813')
                    time.sleep(0.3)
                    
                    password_field.clear()
                    password_field.send_keys('SpF59866')
                    time.sleep(0.3)
                    
                    submit_button.click()
                    time.sleep(3)
                    
                    # Salvar novos cookies após login bem-sucedido
                    if SALVAR_COOKIES_AUTOMATICO:
                        salvar_cookies_sessao(driver, info_extra='login_forcado_apos_acesso_negado')
                    
                    print('[COOKIES] ✅ Login forçado realizado após acesso negado!')
                    return True
                    
                except Exception as e:
                    print(f'[COOKIES][ERRO] Falha no login forçado: {e}')
                    return False
            else:
                print('[COOKIES] ✅ Login realizado via cookies! Pularemos a tela de login.')
        except Exception as e:
            print(f'[COOKIES][WARN] Erro ao verificar URL atual: {e}')
    else:
        print('[COOKIES] ❌ Cookies inválidos ou inexistentes. Login manual necessário.')
    
    return sucesso

# ===============================================
# CONFIGURAÇÕES DE COOKIES
# ===============================================
# Por padrão, habilitamos uso e salvamento de cookies para drivers "normais"
# (PC e VT). Para o driver "notebook" preferimos comportamento manual e não
# recarregar cookies automaticamente, para evitar sessões conflitantes.
try:
    # Por padrão, permitir que o driver ativo utilize cookies salvos.
    # Isto faz com que o carregamento automático de cookies seja aplicado
    # também quando o driver ativo for o 'notebook'.
    USAR_COOKIES_AUTOMATICO = True
except NameError:
    # Se a seleção do driver ainda não foi definida no momento da importação,
    # habilitar cookies por padrão.
    USAR_COOKIES_AUTOMATICO = True

# Sempre permitimos salvar cookies após o usuário fazer login manualmente,
# para que sessões possam ser reutilizadas por drivers normais.
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


# --- Wrapper: criar_driver ativo que aplica carregamento automático de cookies ---
# Substitui a referência direta à fábrica por uma função que cria o driver
# e tenta aplicar cookies salvos (se configurado). Isso garante que callers
# que usam `criar_driver()` já obtenham um driver com sessão reaproveitável.
try:
    # Preserve original factory (pode ser uma função atribuída acima)
    criar_driver_factory = criar_driver
except NameError:
    criar_driver_factory = None

def criar_driver(headless=False):
    """Cria o driver usando a fábrica ativa e aplica cookies salvos quando permitido.

    Retorna o WebDriver ou None em caso de falha.
    """
    if criar_driver_factory is None:
        print('[DRIVER_CONFIG] ❌ Fábrica de driver não definida')
        return None

    try:
        driver = criar_driver_factory(headless=headless)
    except Exception as e:
        print(f'[DRIVER_CONFIG] ❌ Erro ao criar driver via fábrica: {e}')
        return None

    # NÃO aplicar cookies aqui para evitar loop duplo
    # O login_cpf() já faz a aplicação de cookies via verificar_e_aplicar_cookies()
    print('[DRIVER_CONFIG] ✅ Driver criado (cookies serão aplicados no login)')

    return driver

