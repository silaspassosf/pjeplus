# ====================================================================
# PJE PLUS - Fix.py
# Módulo principal de utilitários e funções para automação do PJe
# ====================================================================
###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.
# Evitar modificações em arquivos não explicitamente mencionados.
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.

# ===============================================
# CONFIGURAÇÃO GLOBAL DO GECKODRIVER (MIGRADO DE driver_config.py)
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
# PERFIS FIREFOX (MIGRADO DE driver_config.py)
# ===============================================
# Perfil padrão para SISBAJUD (PC). Caminho correto do perfil Sisb do Developer Edition
SISB_PROFILE_PC = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
# Perfil notebook para SISBAJUD — informe o caminho se diferente do padrão
SISB_PROFILE_NOTEBOOK = r'C:\Users\s164283\AppData\Local\Mozilla\Firefox\Profiles\2y17wq63.default'

# ===============================================
# CAMINHOS AUTOHOTKEY (MIGRADO DE driver_config.py)
# ===============================================
AHK_EXE_PC = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
AHK_SCRIPT_PC = r'D:\PjePlus\Login.ahk'

AHK_EXE_NOTEBOOK = r'C:\Users\s164283\Downloads\AHK\AutoHotkey64.exe'
AHK_SCRIPT_NOTEBOOK = r'C:\Users\s164283\Desktop\pjeplus\login.ahk'

AHK_EXE_ACTIVE = None
AHK_SCRIPT_ACTIVE = None

# ===============================================
# CONFIGURAÇÕES DE COOKIES (MIGRADO DE driver_config.py)
# ===============================================
SALVAR_COOKIES_AUTOMATICO = True    # ← Salvar cookies após login manual/automático

# ===============================================
# IMPORTAÇÕES PARA SISTEMA DE COOKIES
# ===============================================
import os
import json
from datetime import datetime, timedelta
import glob

# ===============================================
# FUNÇÕES DE CRIAÇÃO DE DRIVER (MIGRADO DE driver_config.py)
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
    from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    
    # Tentar usar perfil específico com fallback
    perfil_usado = None
    try:
        # Primeiro tentar o perfil antigo
        perfil_antigo = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
        if os.path.exists(perfil_antigo):
            profile = FirefoxProfile(perfil_antigo)
            options.profile = profile
            perfil_usado = perfil_antigo
            print(f"[DRIVER_SISB_NOTEBOOK] Usando perfil antigo: {perfil_antigo}")
        else:
            # Se não encontrou o perfil antigo, tentar o novo perfil
            if os.path.exists(SISB_PROFILE_NOTEBOOK):
                profile = FirefoxProfile(SISB_PROFILE_NOTEBOOK)
                options.profile = profile
                perfil_usado = SISB_PROFILE_NOTEBOOK
                print(f"[DRIVER_SISB_NOTEBOOK] Perfil antigo não encontrado, usando perfil novo: {SISB_PROFILE_NOTEBOOK}")
            else:
                print(f"[DRIVER_SISB_NOTEBOOK] Nenhum perfil encontrado, usando perfil temporário")
    except Exception as e:
        print(f"[DRIVER_SISB_NOTEBOOK] Erro ao carregar perfil: {e}, usando perfil temporário")
    
    service = Service(executable_path=GECKODRIVER_PATH)
    
    try:
        driver = webdriver.Firefox(options=options, service=service)
        driver.implicitly_wait(10)
        if perfil_usado:
            print(f"[DRIVER_SISB_NOTEBOOK] Driver SISBAJUD NOTEBOOK criado com sucesso (perfil: {perfil_usado})")
        else:
            print("[DRIVER_SISB_NOTEBOOK] Driver SISBAJUD NOTEBOOK criado com sucesso (perfil temporário)")
        return driver
    except Exception as e:
        print(f"[DRIVER_SISB_NOTEBOOK] Erro ao criar driver: {e}")
        return None

# ===============================================
# FUNÇÕES DE LOGIN (MIGRADO DE driver_config.py)
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
            cur = driver.current_url
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
# SISTEMA DE COOKIES (MIGRADO DE driver_config.py)
# ===============================================

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
    try:
        # Por padrão, permitir que o driver ativo utilize cookies salvos.
        # Isto faz com que o carregamento automático de cookies seja aplicado
        # também quando o driver ativo for o 'notebook'.
        USAR_COOKIES_AUTOMATICO = True
    except NameError:
        # Se a seleção do driver ainda não foi definida no momento da importação,
        # habilitar cookies por padrão.
        USAR_COOKIES_AUTOMATICO = True

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
# FUNÇÕES WRAPPER DE COMPATIBILIDADE (MIGRADO DE driver_config.py)
# ===============================================

# --- Seleção das funções ativas ---
# Configuração padrão: Notebook com login CPF
criar_driver = criar_driver_notebook    # ← ATIVO: Driver Notebook
login_func = login_cpf    # ← ATIVO: Login por CPF/senha (typing)

# ===============================================
# FUNÇÃO WRAPPER PRINCIPAL (MIGRADO DE driver_config.py)
# ===============================================

def criar_driver_principal(headless=False):
    """Cria o driver usando a fábrica ativa e aplica cookies salvos quando permitido.

    Retorna o WebDriver ou None em caso de falha.
    """
    try:
        driver = criar_driver(headless=headless)
    except Exception as e:
        print(f'[DRIVER_CONFIG] ❌ Erro ao criar driver via fábrica: {e}')
        return None

    # NÃO aplicar cookies aqui para evitar loop duplo
    # O login_cpf() já faz a aplicação de cookies via verificar_e_aplicar_cookies()
    print('[DRIVER_CONFIG] ✅ Driver criado (cookies serão aplicados no login)')

    return driver

# =========================
# 1. IMPORTAÇÕES E CONFIGURAÇÕES
# =========================
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.common.exceptions import WebDriverException, NoSuchWindowException, ElementNotInteractableException
import re
import time
import datetime
import pyperclip
import undetected_chromedriver as uc
import requests
import requests
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Fix.py
# Utilitário Selenium inspirado na lógica da extensão MaisPje para preenchimento robusto de campos em formulários do PJe TRT2
# Autor: Cascade AI

import os
import shutil
import tempfile
import time

import re
import json

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urlparse
import pyperclip
import logging

# Configuração de logs
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelvelname)s - %(message)s')  # Desativado DEBUG, agora só WARNING ou superior

# =========================
# 2. UTILITÁRIOS DE FORMATAÇÃO DE DADOS
# =========================

def formatar_moeda_brasileira(valor):
    """
    Formata valor numérico para moeda brasileira (R$ xxxxx,yy)
    """
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos, exceto vírgulas e pontos
            valor_limpo = re.sub(r'[^\d,.]', '', valor)

            # Converte para float
            if ',' in valor_limpo and '.' in valor_limpo:
                # Formato 1.234.567,89 ou 1,234,567.89
                if valor_limpo.rfind(',') > valor_limpo.rfind('.'):
                    # Último separador é vírgula (formato brasileiro)
                    valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                else:
                    # Último separador é ponto (formato internacional)
                    valor_limpo = valor_limpo.replace(',', '')
            elif ',' in valor_limpo:
                # Apenas vírgula como separador decimal
                valor_limpo = valor_limpo.replace(',', '.')

            valor = float(valor_limpo)

        if valor == 0:
            return "R$ 0,00"

        # Formata com separador de milhares e duas casas decimais
        valor_formatado = f"{valor:,.2f}"

        # Substitui separadores para formato brasileiro
        valor_formatado = valor_formatado.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')

        return f"R$ {valor_formatado}"

    except (ValueError, TypeError):
        return "R$ 0,00"

def normalizar_cpf_cnpj(documento):
    """
    Remove pontuação de CPF/CNPJ, mantendo apenas números
    """
    if not documento:
        return ""

    # Remove todos os caracteres não numéricos
    documento_limpo = re.sub(r'\D', '', str(documento))
    return documento_limpo

# =========================
# 3. GERENCIAMENTO DE DRIVER E LOGIN
# =========================

def driver_pc(headless=False):
    """
    Perfil: C:/Users/Silas/AppData/Roaming/Mozilla/Dev
    Executável: C:/Program Files/Firefox Developer Edition/firefox.exe
    """
    try:
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        import os

        options = Options()

        if headless:
            options.add_argument('--headless')

        # Configurações essenciais para PJe
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--ignore-ssl-errors-ignore-untrusted')

        # Perfil personalizado
        profile_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\pjeprofile"
        if os.path.exists(profile_path):
            options.add_argument(f"-profile")
            options.add_argument(profile_path)

        # Executável personalizado
        firefox_path = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
        if os.path.exists(firefox_path):
            options.binary_location = firefox_path

        service = Service()
        driver = webdriver.Firefox(service=service, options=options)

        # Configurações adicionais
        driver.maximize_window()
        driver.implicitly_wait(10)

        return driver

    except Exception as e:
        print(f"[ERRO] Falha ao criar driver padronizado: {e}")
        return None

def login_pc(driver):
    """Processo de login humanizado via AutoHotkey, aguardando login terminar antes de prosseguir."""
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
        import subprocess
        time.sleep(1)
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

# =========================
# 4. NAVEGAÇÃO E INTERAÇÃO BÁSICA
# =========================

def navegar_para_tela(driver, url=None, seletor=None, delay=2, timeout=30, log=True):
    # Navega para URL ou clica em seletor diretamente.
    # Args:
    # driver: WebDriver instance
    # url: URL para navegar
    # seletor: Seletor CSS/XPath para clicar
    # delay: Delay após clique (segundos)
    # timeout: Timeout máximo para espera (segundos)
    # log: Se deve exibir logs
    # Returns:
    # bool: True se sucesso, False se falha
    try:
        if log:
            print(f'[NAVEGAR] Iniciando navegação...')

        if url:
            driver.get(url)
            if log:
                print(f'[NAVEGAR] Navegando para {url}')

        if seletor:
            # Encontra e clica no elemento
            element = driver.find_element(By.CSS_SELECTOR, seletor)
            driver.execute_script('arguments[0].scrollIntoView(true);', element)
            element.click()

            # Espera após clique
            time.sleep(delay)
            if log:
                print(f'[NAVEGAR] Clicou em {seletor}')

        return True

    except Exception as e:
        if log:
            print(f'[NAVEGAR][ERRO] Falha na navegação: {str(e)}')
        return False

def safe_click(driver, selector_or_element, timeout=10, by=None, log=True, retry_count=3):
    """
    Clicks safely on an element with multiple fallback mechanisms.
    Versão robusta baseando-se nas práticas do gigs-plugin.js
    """
    try:
        # Get the element if a selector was provided
        if isinstance(selector_or_element, str):
            if log:
                print(f"[SAFE_CLICK] Buscando elemento: {selector_or_element}")
            
            # Primeiro tenta usando wait_for_clickable que é mais restritivo
            element = wait_for_clickable(driver, selector_or_element, timeout, by)
            
            # Se não conseguir, usa o wait padrão que só verifica presença
            if element is None:
                element = wait(driver, selector_or_element, timeout, by)
        else:
            element = selector_or_element
            
        # Check if element was found
        if element is None:
            if log:
                print(f"[SAFE_CLICK] Elemento não encontrado")
            return False
        
        # Scroll elemento para a visualização antes de tentar clicar
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            sleep(300)  # Espera um pouco após o scroll
        except Exception as e:
            if log:
                print(f"[SAFE_CLICK] Não foi possível rolar para o elemento: {str(e)}")
            
        # Estratégia de tentativas de click com diferentes abordagens
        for attempt in range(retry_count):
            if attempt > 0 and log:
                print(f"[SAFE_CLICK] Tentativa {attempt+1}/{retry_count}")
            
            # Estratégia 1: Click padrão
            try:
                if log and attempt == 0:
                    print(f"[SAFE_CLICK] Tentando click padrão")
                element.click()
                if log:
                    print(f"[SAFE_CLICK] Click bem sucedido!")
                return True
            except (ElementClickInterceptedException, ElementNotInteractableException, WebDriverException) as e:
                if log:
                    print(f"[SAFE_CLICK] Click padrão falhou: {str(e)}")
                sleep(200)  # Pequena pausa entre tentativas
            
            # Estratégia 2: JavaScript click
            try:
                if log:
                    print(f"[SAFE_CLICK] Tentando click via JavaScript")
                driver.execute_script("arguments[0].click();", element)
                if log:
                    print(f"[SAFE_CLICK] Click via JavaScript bem sucedido!")
                return True
            except Exception as e:
                if log:
                    print(f"[SAFE_CLICK] Click via JavaScript falhou: {str(e)}")
                sleep(200)
            
            # Estratégia 3: ActionChains
            try:
                if log:
                    print(f"[SAFE_CLICK] Tentando click via ActionChains")
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()
                if log:
                    print(f"[SAFE_CLICK] Click via ActionChains bem sucedido!")
                return True
            except Exception as e:
                if log:
                    print(f"[SAFE_CLICK] Click via ActionChains falhou: {str(e)}")
                sleep(300)
                
            # Estratégia 4: Eventos de mouse simulados (inspirado no gigs-plugin.js)
            try:
                if log:
                    print(f"[SAFE_CLICK] Tentando click via eventos de mouse simulados")
                # Simula sequência completa de eventos de mouse
                driver.execute_script("""
                    var element = arguments[0];
                    var events = ['mousedown', 'mouseup', 'click'];
                    for (var i = 0; i < events.length; i++) {
                        var event = new MouseEvent(events[i], {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: element.getBoundingClientRect().left + element.offsetWidth / 2,
                            clientY: element.getBoundingClientRect().top + element.offsetHeight / 2
                        });
                        element.dispatchEvent(event);
                    }
                """, element)
                if log:
                    print(f"[SAFE_CLICK] Click via eventos de mouse simulados bem sucedido!")
                return True
            except Exception as e:
                if log:
                    print(f"[SAFE_CLICK] Click via eventos de mouse simulados falhou: {str(e)}")
                sleep(300)
                
        if log:
            print(f"[SAFE_CLICK] Todas as tentativas de click falharam após {retry_count} tentativas")
        return False
        
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Erro geral: {str(e)}")
        return False

def wait_for_clickable(driver, selector, timeout=10, by=None):
    """
    Wait for an element to be clickable in the DOM.
    
    Args:
        driver: Selenium WebDriver instance
        selector: CSS selector or XPath
        timeout: Maximum time to wait in seconds
        by: Selector type (By.CSS_SELECTOR by default)
    
    Returns:
        WebElement if clickable, None otherwise
    """
    if by is None:
        by = By.CSS_SELECTOR
        
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        if isinstance(selector, str):
            print(f"[WAIT_CLICKABLE] Elemento não clicável: {selector}")
        return None

def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR, log=False):
    # Versão aprimorada - Espera até que um elemento esteja presente (e opcionalmente contenha texto), com logs detalhados.
    import time as _time
    try:
        if not isinstance(seletor, str):
            raise ValueError(f"Seletor deve ser string, recebido: {type(seletor)}")
        if texto and not isinstance(texto, str):
            raise ValueError(f"Text must be a string, got: {type(texto)}")
        if DEBUG:
            _log_info(f"[ESPERAR] Aguardando elemento: '{seletor}' (by={by}, timeout={timeout}, texto={texto})")
        t0 = _time.time()
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )
        t1 = _time.time()
        if DEBUG:
            _log_info(f"[ESPERAR][OK] Elemento encontrado: '{seletor}' em {t1-t0:.2f}s" + (f" (texto='{texto}')" if texto else ""))
        return el
    except Exception as e:
        _log_error(f"[ESPERAR][ERRO] Falha ao esperar elemento: '{seletor}' (by={by}, timeout={timeout}, texto={texto}) -> {e}")
        return None

def wait_for_visible(driver, selector, timeout=10, by=None):
    """
    Wait for an element to be visible in the DOM.

    Args:
        driver: Selenium WebDriver instance
        selector: CSS selector or XPath
        timeout: Maximum time to wait in seconds
        by: Selector type (By.CSS_SELECTOR by default)

    Returns:
        WebElement if visible, None otherwise
    """
    if by is None:
        by = By.CSS_SELECTOR

    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        if isinstance(selector, str):
            print(f"[WAIT_VISIBLE] Elemento não visível: {selector}")
        return None

def sleep(ms):
    """
    Função que implementa pausa em milissegundos, similar ao sleep do JavaScript

    Args:
        ms: Tempo de pausa em milissegundos

    Returns:
        None
    """
    time.sleep(ms / 1000)

# =========================
# 5. FILTROS E INDEXAÇÃO
# =========================

def aplicar_filtro_100(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    try:
        driver.execute_script("document.body.style.zoom='50%'")

        # Método simplificado que funciona
        for tentativa in range(2):  # Reduzido para 2 tentativas
            try:
                print(f'[FILTRO_LISTA_100] Tentativa {tentativa + 1}...')

                # Busca pelo span '20' e encontra o mat-select pai
                span_20 = driver.find_element(By.XPATH, "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
                mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")

                # Scroll para centralizar o elemento
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mat_select)
                time.sleep(0.3)

                # Clique com fallback para JavaScript
                try:
                    mat_select.click()
                except:
                    driver.execute_script("arguments[0].click();", mat_select)

                # Aguarda overlay e seleciona opção 100
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                opcao_100 = overlay.find_element(By.XPATH, ".//mat-option[.//span[normalize-space(text())='100']]")
                opcao_100.click()
                time.sleep(1)

                print('[FILTRO_LISTA_100] Filtro aplicado com sucesso!')
                return True

            except Exception as e:
                print(f'[FILTRO_LISTA_100] Tentativa {tentativa + 1} falhou: {e}')
                if tentativa < 1:
                    time.sleep(1)

        # Se chegou aqui, todas as tentativas falharam
        print('[FILTRO_LISTA_100][ERRO] Falha após todas as tentativas')
        return False

    except Exception as e:
        print(f'[FILTRO_LISTA_100][ERRO] Falha geral: {e}')
        return False

def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    """
    Função principal para processar uma lista de processos, com tratamento robusto
    para questões de conexão, abas e manipulação do driver.
    """
    import time  # Adicionando import explícito do time

    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
      # Verificar conexão inicial
    try:
        # Teste básico: tentar obter URL atual
        current_url = driver.current_url
        if not current_url:
            print(f'[FLUXO][VALIDAÇÃO] URL vazia detectada')
            conexao_inicial = False
        else:
            # Teste de handles de janela
            try:
                handles = driver.window_handles
                if not handles:
                    print(f'[FLUXO][VALIDAÇÃO] Nenhum handle de janela disponível')
                    conexao_inicial = False
                else:
                    # Teste de execução de script
                    try:
                        driver.execute_script("return 'test';")
                        conexao_inicial = True
                    except Exception as e:
                        print(f'[FLUXO][VALIDAÇÃO] Erro na execução de script: {e}')
                        conexao_inicial = "FATAL"
            except Exception as e:
                print(f'[FLUXO][VALIDAÇÃO] Erro ao obter handles: {e}')
                conexao_inicial = "FATAL"
    except Exception as e:
        print(f'[FLUXO][VALIDAÇÃO] Erro geral na validação: {e}')
        conexao_inicial = "FATAL"
    if conexao_inicial == "FATAL":
        print('[FLUXO][FATAL] Driver inutilizável no início do processamento!')
        return False
    elif not conexao_inicial:
        print('[FLUXO][ERRO] Driver não está conectado no início do processamento!')
        return False

    # Capturar aba original
    try:
        aba_lista_original = driver.current_window_handle
        print(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao capturar aba da lista: {e}')
        return False

    # Indexar processos com tratamento de erro
    try:
        processos = indexar_processos(driver)
        if not processos:
            print('[FLUXO][ALERTA] Nenhum processo encontrado para indexação')
            return False
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao indexar processos: {e}')
        return False

    processos_processados = 0
    processos_com_erro = 0
    interrompido_por_fatal = False

    # Limitar número de processos se necessário
    if max_processos and max_processos > 0 and max_processos < len(processos):
        processos = processos[:max_processos]
        print(f'[FLUXO] Limitando processamento a {max_processos} processos')

    for idx, (proc_id, linha) in enumerate(processos):
        print(f'[PROCESSAR] Iniciando processo {idx+1}/{len(processos)}: {proc_id}', flush=True)

        # Verificar conexão antes de cada processo
        try:
            # Teste básico: tentar obter URL atual
            current_url = driver.current_url
            if not current_url:
                print(f'[PROCESSAR][VALIDAÇÃO] URL vazia detectada')
                conexao_status = False
            else:
                # Teste de handles de janela
                try:
                    handles = driver.window_handles
                    if not handles:
                        print(f'[PROCESSAR][VALIDAÇÃO] Nenhum handle de janela disponível')
                        conexao_status = False
                    else:
                        # Teste de execução de script
                        try:
                            driver.execute_script("return 'test';")
                            conexao_status = True
                        except Exception as e:
                            print(f'[PROCESSAR][VALIDAÇÃO] Erro na execução de script: {e}')
                            conexao_status = "FATAL"
                except Exception as e:
                    print(f'[PROCESSAR][VALIDAÇÃO] Erro ao obter handles: {e}')
                    conexao_status = "FATAL"
        except Exception as e:
            print(f'[PROCESSAR][VALIDAÇÃO] Erro geral na validação: {e}')
            conexao_status = "FATAL"
        if conexao_status == "FATAL":
            print(f'[PROCESSAR][FATAL] Contexto do navegador foi descartado. Interrompendo processamento.')
            print(f'[PROCESSAR][FATAL] Processos restantes não serão processados: {len(processos) - idx}')
            interrompido_por_fatal = True
            break  # Para o loop imediatamente
        elif not conexao_status:
            print(f'[PROCESSAR][ERRO] Conexão perdida antes de processar {proc_id}')
            processos_com_erro += 1
            continue

        # SKIP: Não limpar abas extras antes do callback - permite que carta() abra aba programaticamente
        # A limpeza será feita após o callback se necessário

        # Verificar se ainda estamos na aba da lista
        try:
            atual_url = driver.current_url
            # Se estamos em acesso-negado, reiniciar driver e tentar retomar
            if 'acesso-negado' in atual_url.lower() or 'login.jsp' in atual_url.lower():
                print(f'[PROCESSAR][ALERTA] Acesso negado detectado (URL: {atual_url[:80]}). Tentando reiniciar driver e refazer login...')
                # Reinicia o driver do PJe usando as fábricas em `driver_config` e executa o login
                try:
                    print('[RECOVERY][RESTART] Tentando reiniciar driver e efetuar novo login...')
                    try:
                        try:
                            driver.quit()
                        except Exception:
                            pass

                        from driver_config import criar_driver, login_func

                        novo_driver = criar_driver()
                        if not novo_driver:
                            print('[RECOVERY][RESTART] Falha ao criar novo driver')
                            processos_com_erro += 1
                            continue

                        ok = False
                        try:
                            ok = login_func(novo_driver)
                        except Exception as e:
                            print(f'[RECOVERY][RESTART] Erro ao executar login_func: {e}')
                            ok = False

                        if not ok:
                            print('[RECOVERY][RESTART] Login falhou no novo driver')
                            try:
                                novo_driver.quit()
                            except Exception:
                                pass
                            processos_com_erro += 1
                            continue

                        try:
                            url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
                            novo_driver.get(url_atividades)
                            time.sleep(4)
                        except Exception:
                            pass

                        print('[RECOVERY][RESTART] Novo driver criado e logado com sucesso')
                        driver = novo_driver

                    except Exception as e:
                        print(f'[RECOVERY][RESTART] Falha durante reinício do driver: {e}')
                        processos_com_erro += 1
                        continue
                except Exception as e:
                    print(f'[RECOVERY][RESTART][ERRO] Exceção inesperada: {e}')
                    processos_com_erro += 1
                    continue

                    # Verificar se precisamos reaplicar filtros específicos (P2B)
                    # Detecta contexto P2B verificando se callback é de p2b
                    try:
                        callback_str = str(callback)
                        if 'p2b.py' in callback_str or 'fluxo_pz' in callback_str:
                            print('[PROCESSAR] Contexto P2B detectado, reaplicando filtros específicos...')
                            try:
                                # Importar e executar função de reaplicar filtros P2B
                                import sys
                                import os
                                current_dir = os.path.dirname(os.path.abspath(__file__))
                                if current_dir not in sys.path:
                                    sys.path.append(current_dir)
                                from p2b import reaplicar_filtros_p2b
                                if reaplicar_filtros_p2b(driver):
                                    print('[PROCESSAR] ✅ Filtros P2B reaplicados com sucesso')
                                else:
                                    print('[PROCESSAR] ❌ Falha ao reaplicar filtros P2B')
                            except Exception as filter_error:
                                print(f'[PROCESSAR][ERRO] Falha ao reaplicar filtros P2B: {filter_error}')
                    except Exception:
                        pass

                    # atualizar aba_lista_original se necessário
                    try:
                        aba_lista_original = driver.window_handles[0]
                    except Exception:
                        pass
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha ao verificar acesso negado: {e}')
            processos_com_erro += 1
            continue

        # Reindexar linha com maior tolerância
        tentativas = 3
        linha_atual = None
        for tentativa in range(tentativas):
            try:
                linha_atual = reindexar_linha(driver, proc_id)
                if linha_atual:
                    break
                print(f'[PROCESSAR] Tentativa {tentativa+1}/{tentativas} - Aguardando para reindexar linha')
                time.sleep(1)
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha na tentativa {tentativa+1} de reindexar: {e}')
                time.sleep(1)

        if not linha_atual:
            print(f'[PROCESSAR][ERRO] Não foi possível reindexar a linha para {proc_id} após {tentativas} tentativas')
            processos_com_erro += 1
            continue

        # Abre detalhes do processo
        try:
            if not abrir_detalhes_processo(driver, linha_atual):
                print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
                processos_com_erro += 1
                continue
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha ao abrir detalhes do processo {proc_id}: {e}')
            processos_com_erro += 1
            continue

        # Pausa para carregamento da nova aba
        time.sleep(1)

        # Troca para nova aba com várias tentativas
        nova_aba = None
        for tentativa in range(3):
            try:
                nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
                if nova_aba:
                    print(f'[PROCESSAR] Trocado para nova aba: {nova_aba}')
                    time.sleep(0.5)  # Pequena pausa para estabilização da nova aba
                    break
                print(f'[PROCESSAR] Tentativa {tentativa+1}/3 - Aguardando abertura de nova aba')
                time.sleep(1)
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha na tentativa {tentativa+1} de trocar para nova aba: {e}')
                time.sleep(1)

        if not nova_aba:
            print(f'[PROCESSAR][ERRO] Não foi possível trocar para nova aba para {proc_id}')
            processos_com_erro += 1
            continue

        # Executar callback para o processo
        try:
            callback(driver)
            processos_processados += 1
            print(f'[PROCESSAR] ✅ Processo {proc_id} processado com sucesso')
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha no callback para {proc_id}: {e}')
            processos_com_erro += 1
            continue

        # Limpeza de abas após processamento
        try:
            # Verificar se ainda estamos na aba da lista
            current_handle = driver.current_window_handle
            if current_handle != aba_lista_original:
                # Fechar aba atual e voltar para lista
                driver.close()
                driver.switch_to.window(aba_lista_original)
                print(f'[LIMPEZA] Aba fechada, retornando à lista')
            else:
                print('[LIMPEZA] Já na aba da lista')
        except Exception as e:
            print(f'[LIMPEZA][ERRO] Falha na limpeza de abas: {e}')

        print(f'[PROCESSAR] Finalizado processamento de {proc_id}')

    # Relatório final
    relatorio_final(processos, processos_processados, processos_com_erro, interrompido_por_fatal)
    return True

def indexar_processos(driver):
    """
    Indexa todos os processos visíveis na lista atual
    """
    processos = []
    try:
        # Aguardar carregamento da tabela
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
        )

        # Encontrar todas as linhas da tabela
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')

        for linha in linhas:
            try:
                # Extrair número do processo
                links = linha.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    proc_id = links[0].text.strip()
                    if proc_id:
                        processos.append((proc_id, linha))
            except Exception as e:
                print(f'[INDEXAR][AVISO] Erro ao processar linha: {e}')
                continue

        print(f'[INDEXAR] {len(processos)} processos indexados')
        return processos

    except Exception as e:
        print(f'[INDEXAR][ERRO] Falha ao indexar processos: {e}')
        return []

def relatorio_final(processos, processados, erros, interrompido_por_fatal=False):
    """
    Gera relatório final do processamento
    """
    total = len(processos)
    print('\n' + '='*50)
    print('RELATÓRIO FINAL DE PROCESSAMENTO')
    print('='*50)
    print(f'Total de processos encontrados: {total}')
    print(f'Processos processados com sucesso: {processados}')
    print(f'Processos com erro: {erros}')

    if interrompido_por_fatal:
        print('⚠️  PROCESSAMENTO INTERROMPIDO POR FATAL ERROR')
    else:
        print('✅ PROCESSAMENTO CONCLUÍDO')

    print('='*50 + '\n')

def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """
    Wait for an element to be present in the DOM.
    Similar ao esperarElemento do gigs-plugin.js

    Args:
        driver: Selenium WebDriver instance
        selector: CSS selector or XPath
        timeout: Maximum time to wait in seconds
        by: Selector type (By.CSS_SELECTOR by default)

    Returns:
        WebElement if present, None otherwise
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        return None

# Variáveis globais necessárias
DEBUG = False

def _log_info(msg):
    """Log de informação"""
    if DEBUG:
        print(f"[INFO] {msg}")

def _log_error(msg):
    """Log de erro"""
    print(f"[ERROR] {msg}")

def _audit(event, selector, status, extra=None):
    """Função de auditoria (placeholder)"""
    pass

# =========================
# 6. EXTRAÇÃO DE DOCUMENTOS E DADOS
# =========================

def extrair_documento(driver, regras_analise=None, timeout=15, log=False):
    # Extrai texto do documento aberto, aplica regras se houver.
    # Retorna texto_final (str) ou None em caso de erro.
    texto_completo = None
    texto_final = None
    try:
        # Espera o botão HTML
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            _log_error('[EXTRAI][ERRO] Botão HTML não encontrado.')
            return None

        # Clica no botão HTML
        safe_click(driver, btn_html)
        time.sleep(1)

        # Extrai o texto do preview
        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            _log_error('[EXTRAI][ERRO] Preview do documento não encontrado.')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return None

        texto_completo = preview.text

        # Fecha o modal ANTES de processar o texto
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            if DEBUG:
                _log_info('[EXTRAI] Modal HTML fechado.')
            time.sleep(0.5)
            # Pressiona TAB para tentar restaurar cabeçalho da aba detalhes
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
            if DEBUG:
                _log_info('[WORKAROUND] Pressionada tecla TAB após fechar modal de documento.')
        except Exception as e_esc:
            if DEBUG:
                _log_info(f'[EXTRAI][WARN] Falha ao fechar modal com ESC: {e_esc}')

        if not texto_completo:
            _log_error('[EXTRAI][ERRO] Texto do preview vazio.')
            return None
        marcador = "Servidor Responsável"
        try:
            indice_marcador = texto_completo.rindex(marcador)
            indice_newline = texto_completo.find('\n', indice_marcador)
            if indice_newline != -1:
                texto_final = texto_completo[indice_newline:].strip()
            else:
                texto_final = texto_completo.strip()
            if DEBUG:
                _log_info(f'[EXTRAI] Conteúdo extraído abaixo de "{marcador}".')
        except ValueError:
            texto_final = texto_completo.strip()
            if DEBUG:
                _log_info(f'[EXTRAI] Marcador "{marcador}" não encontrado. Usando texto completo do documento.')

        # Aplica regras de análise se houver
        if regras_analise and callable(regras_analise):
            if DEBUG:
                _log_info('[EXTRAI] Aplicando regras de análise.')
            try:
                print('[DEBUG][REGRAS] Iniciando análise de regras...')
                _ = regras_analise(texto_final)
                print('[DEBUG][REGRAS] Análise de regras concluída.')
            except Exception as e_analise:
                print(f'[EXTRAI][ERRO] Falha ao analisar regras: {e_analise}')

        if log: print('[EXTRAI] Extração concluída.')
        return texto_final

    except Exception as e:
        if log: print(f'[EXTRAI][ERRO] Falha geral ao extrair documento: {e}')
        try:
            if driver.find_elements(By.CSS_SELECTOR, '#previewModeloDocumento'):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return None

def extrair_pdf(driver, log=True):
    import time
    from selenium.webdriver.common.keys import Keys
    import pyperclip
    try:
        # 1. Clicar no botão de exportar texto
        btn_export = driver.find_element(By.CSS_SELECTOR, '.fa-file-export')
        btn_export.click()
        if log:
            print('[EXPORT] Botão .fa-file-export clicado.')
        # 2. Aguardar modal com título "Texto Extraído"
        for _ in range(20):
            modais = driver.find_elements(By.CSS_SELECTOR, 'pje-conteudo-documento-dialog')
            for modal in modais:
                try:
                    titulo = modal.find_element(By.CSS_SELECTOR, '.mat-dialog-title')
                    if 'Texto Extraído' in titulo.text:
                        # 2.1 Clicar no ícone de copiar texto
                        try:
                            btn_copiar = modal.find_element(By.CSS_SELECTOR, 'i.far.fa-copy')
                            btn_copiar.click()
                            time.sleep(0.3)
                            texto = pyperclip.paste()
                            if log:
                                print('[EXPORT] Texto extraído do modal via copiar.')
                        except Exception as e:
                            if log:
                                print(f'[EXPORT][ERRO] Falha ao copiar texto do modal: {e}')
                            # fallback: tentar pegar do <pre>
                            pre = modal.find_element(By.CSS_SELECTOR, 'pre')
                            texto = pre.text
                        # Fechar modal
                        try:
                            btn_fechar = modal.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close]')
                            btn_fechar.click()
                        except Exception:
                            modal.send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                        return texto
                except Exception:
                    continue
            time.sleep(0.5)
        if log:
            print('[EXPORT][ERRO] Modal de texto extraído não apareceu.')
        return None
    except Exception as e:
        if log:
            print(f'[EXPORT][ERRO] {e}')
        return None

def extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False):
    """
    Extrai dados essenciais do processo via API do PJe (TRT2).
    Baseado na função do gigs.py e Fix_backup.py.
    
    Retorna dicionário organizado com:
    - numero: Número do processo
    - id: ID do processo
    - partes: {autor: [], reu: [], terceiro: []}
    - data_ajuizamento: Data de ajuizamento formatada (dd/mm/aaaa)
    - valor_execucao: Valor atualizado da execução formatado (R$ x.xxx,xx)
    - data_calculo: Data do cálculo mais recente
    - tem_calculos: Boolean indicando se há cálculos
    """
    from datetime import datetime
    
    # Funções auxiliares internas
    def get_cookies_dict(driver):
        cookies = driver.get_cookies()
        return {c['name']: c['value'] for c in cookies}

    def extrair_numero_processo_url(driver):
        """Extrai número do processo da URL ou do elemento clipboard"""
        url = driver.current_url
        # Primeiro tenta extrair da URL
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)

        # Se não encontrar na URL, tenta extrair do elemento clipboard do PJE
        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
            elemento_clipboard = driver.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except:
            pass

        return None

    def extrair_trt_host(driver):
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo, sess, trt_host):
        """Replica a função obterIdProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('idProcesso')
        except Exception as e:
            if debug:
                print(f'[EXTRAIR] Erro ao obter ID via API: {e}')
        return None
    
    def formatar_moeda(valor):
        """Formata valor numérico como moeda brasileira"""
        try:
            return f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
        except:
            return "R$ 0,00"
    
    def formatar_data(data_iso):
        """Formata data ISO para formato brasileiro dd/mm/aaaa"""
        try:
            if not data_iso:
                return ""
            dt = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y')
        except:
            return ""

    cookies = get_cookies_dict(driver)
    numero_processo = extrair_numero_processo_url(driver)
    trt_host = extrair_trt_host(driver)

    if not numero_processo:
        if debug:
            print('[EXTRAIR] Número do processo não encontrado')
        return None

    if debug:
        print(f'[EXTRAIR] Extraindo dados do processo: {numero_processo}')

    # Criar sessão com cookies
    sess = requests.Session()
    sess.cookies.update(cookies)
    sess.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Grau-Instancia": "1"
    })

    # 1. Obter ID do processo
    id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
    if not id_processo:
        if debug:
            print('[EXTRAIR] ID do processo não encontrado via API')
        return None

    if debug:
        print(f'[EXTRAIR] ID do processo obtido: {id_processo}')

    # Estrutura de dados organizada
    dados_organizados = {
        'numero': numero_processo,
        'id': id_processo,
        'partes': {
            'autor': [],
            'reu': [],
            'terceiro': []
        },
        'data_ajuizamento': '',
        'valor_execucao': 'R$ 0,00',
        'data_calculo': '',
        'tem_calculos': False
    }

    # 2. Obter dados básicos do processo (para data de ajuizamento)
    try:
        url_dados = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        resp = sess.get(url_dados, timeout=10)
        if resp.ok:
            dados_proc = resp.json()
            # Data de ajuizamento
            data_ajuiz = dados_proc.get('autuadoEm')
            if data_ajuiz:
                dados_organizados['data_ajuizamento'] = formatar_data(data_ajuiz)
            if debug:
                print(f'[EXTRAIR] Data ajuizamento: {dados_organizados["data_ajuizamento"]}')
    except Exception as e:
        if debug:
            print(f'[EXTRAIR] Erro ao obter dados básicos: {e}')

    # 3. Obter partes do processo
    try:
        url_partes = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes'
        resp = sess.get(url_partes, timeout=10)
        if resp.ok:
            partes_data = resp.json()
            
            # Polo Ativo (Autor)
            for parte in partes_data.get('ATIVO', []):
                dados_organizados['partes']['autor'].append({
                    'nome': parte.get('nome', '').strip(),
                    'documento': parte.get('documento', '')
                })
            
            # Polo Passivo (Réu)
            for parte in partes_data.get('PASSIVO', []):
                dados_organizados['partes']['reu'].append({
                    'nome': parte.get('nome', '').strip(),
                    'documento': parte.get('documento', '')
                })
            
            # Terceiros
            for parte in partes_data.get('TERCEIROS', []):
                dados_organizados['partes']['terceiro'].append({
                    'nome': parte.get('nome', '').strip(),
                    'documento': parte.get('documento', '')
                })
            
            if debug:
                print(f'[EXTRAIR] Partes: {len(dados_organizados["partes"]["autor"])} autor(es), {len(dados_organizados["partes"]["reu"])} réu(s)')
    except Exception as e:
        if debug:
            print(f'[EXTRAIR] Erro ao obter partes: {e}')

    # 4. Obter valor da execução (cálculo mais recente)
    try:
        url_calculos = f'https://{trt_host}/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=false&idProcesso={id_processo}'
        resp = sess.get(url_calculos, timeout=10)
        if resp.ok:
            calculos_data = resp.json()
            if calculos_data and calculos_data.get('resultado'):
                dados_organizados['tem_calculos'] = True
                
                # Pegar o cálculo mais recente (primeiro da lista já ordenado)
                calculo_recente = calculos_data['resultado'][0]
                
                valor_total = calculo_recente.get('total', 0)
                data_calculo = calculo_recente.get('dataLiquidacao', '')
                
                dados_organizados['valor_execucao'] = formatar_moeda(valor_total)
                dados_organizados['data_calculo'] = formatar_data(data_calculo)
                
                if debug:
                    print(f'[EXTRAIR] Valor execução: {dados_organizados["valor_execucao"]} em {dados_organizados["data_calculo"]}')
            else:
                if debug:
                    print('[EXTRAIR] Sem cálculos cadastrados')
    except Exception as e:
        if debug:
            print(f'[EXTRAIR] Erro ao obter cálculos: {e}')

    # Salvar dados em JSON se caminho fornecido
    if caminho_json:
        try:
            with open(caminho_json, 'w', encoding='utf-8') as f:
                json.dump(dados_organizados, f, ensure_ascii=False, indent=2)
            if debug:
                print(f'[EXTRAIR] Dados salvos em {caminho_json}')
        except Exception as e:
            if debug:
                print(f'[EXTRAIR] Erro ao salvar dados: {e}')

    return dados_organizados

# =========================
# 7. PROCESSAMENTO DE PROCESSOS
# =========================

def abrir_detalhes_processo(driver, linha):
    try:
        btn = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
    except Exception:
        try:
            btn = linha.find_element(By.CSS_SELECTOR, 'button, a')
        except Exception:
            return False
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    return True

def trocar_para_nova_aba(driver, aba_lista_original):
    """
    Troca para uma nova aba diferente da aba original da lista.
    Inclui tratamento robusto de erros e verificações adicionais.

    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista

    Returns:
        str: O handle da nova aba se foi bem-sucedido, None caso contrário
    """
    try:
        # Verificar se o driver está conectado
        try:
            # Teste básico: tentar obter URL atual
            current_url = driver.current_url
            if not current_url:
                print(f'[ABAS][VALIDAÇÃO] URL vazia detectada')
                driver_conectado = False
            else:
                # Teste de handles de janela
                try:
                    handles = driver.window_handles
                    if not handles:
                        print(f'[ABAS][VALIDAÇÃO] Nenhum handle de janela disponível')
                        driver_conectado = False
                    else:
                        # Teste de execução de script
                        try:
                            driver.execute_script("return 'test';")
                            driver_conectado = True
                        except Exception as e:
                            print(f'[ABAS][VALIDAÇÃO] Erro na execução de script: {e}')
                            driver_conectado = False
                except Exception as e:
                    print(f'[ABAS][VALIDAÇÃO] Erro ao obter handles: {e}')
                    driver_conectado = False
        except Exception as e:
            print(f'[ABAS][VALIDAÇÃO] Erro geral na validação: {e}')
            driver_conectado = False

        if not driver_conectado:
            print('[ABAS][ERRO] Driver não está conectado ao tentar trocar de aba')
            return None

        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                print('[ABAS][ERRO] Nenhuma aba disponível')
                return None

            if len(abas) == 1 and abas[0] == aba_lista_original:
                print('[ABAS][ERRO] Apenas a aba original está disponível, nenhuma nova aba foi aberta')
                return None

            print(f'[ABAS] Detectadas {len(abas)} abas: {abas}')
        except Exception as e:
            print(f'[ABAS][ERRO] Falha ao obter lista de abas: {e}')
            return None

        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    # Verificar se realmente trocamos de aba
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        print(f'[ABAS] Troca bem-sucedida para aba: {h}')
                        return h
                    else:
                        print(f'[ABAS][ALERTA] Troca para aba {h} falhou, handle atual é: {atual_handle}')
                except Exception as e:
                    print(f'[ABAS][ERRO] Erro ao trocar para aba {h}: {e}')
                    continue

        # Se chegou aqui, não conseguiu trocar para nenhuma nova aba
        print('[ABAS][ERRO] Não foi possível trocar para nenhuma nova aba')
        return None
    except Exception as e:
        print(f'[ABAS][ERRO] Erro geral ao tentar trocar de aba: {e}')
        return None

def reindexar_linha(driver, proc_id):
    linhas_atuais = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    for linha_temp in linhas_atuais:
        try:
            links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
            texto_linha = links[0].text.strip() if links else (linha_temp.find_elements(By.TAG_NAME, 'td')[0].text.strip() if linha_temp.find_elements(By.TAG_NAME, 'td') else '')
            if proc_id in texto_linha:
                return linha_temp
        except Exception:
            continue
    return None

# =========================
# 8. FUNCIONALIDADES DE GIGS
# =========================

def criar_gigs(driver, dias_uteis, responsavel, observacao, timeout=10, log=True):
    # Cria GIGS sempre usando o padrão dias/responsavel/observacao.
    import datetime
    t0 = time.time()

    try:
        if log:
            print(f"[GIGS] Iniciando criação de GIGS: {dias_uteis}/{responsavel}/{observacao}")

        # Garante sempre o padrão dias/responsavel/observacao
        if not responsavel or responsavel.strip() == '-':
            responsavel = ''
        obs = observacao

        # 1. Clica no botão 'Nova Atividade'
        btn_nova_atividade = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, 'nova-atividade'))
        )
        btn_nova_atividade.click()
        if log:
            print('[GIGS] Botão Nova Atividade clicado.')

        # 2. Aguarda o modal abrir (<form>)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'form'))
        )
        if log:
            print('[GIGS] Modal de GIGS aberto.')

        # 3. Preenche campos
        if dias_uteis != 0:
            campo_dias = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
            )
            campo_dias.clear()
            for c in str(dias_uteis):
                campo_dias.send_keys(c)
                time.sleep(0.05)
            if log:
                print(f'[GIGS] Dias úteis preenchido: {dias_uteis}')

        # --- Preenchimento do responsável ---
        if responsavel:
            try:
                # Seletor compatível com gigs-plugin para campo responsável
                campo_resp = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]'))
                )
                campo_resp.clear()
                campo_resp.send_keys(responsavel)
                time.sleep(0.2)
                campo_resp.send_keys(Keys.ARROW_DOWN)
                campo_resp.send_keys(Keys.ENTER)
                if log:
                    print(f'[GIGS] Responsável preenchido: {responsavel}')
            except Exception as e:
                if log:
                    print(f'[GIGS][AVISO] Campo responsável não encontrado ou não preenchido: {e}')

        # --- Preenchimento da observação ---
        try:
            campo_obs = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
            )
            campo_obs.clear()
            for c in obs:
                campo_obs.send_keys(c)
                time.sleep(0.03)
            if log:
                print(f'[GIGS] Observação preenchida: {obs}')
        except Exception as e:
            if log:
                print(f'[GIGS][AVISO] Campo observação não encontrado ou não preenchido: {e}')

        # 4. Clica em Salvar
        btn_salvar = None
        botoes = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
        for btn in botoes:
            if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                btn_salvar = btn
                break

        if not btn_salvar:
            if log:
                print('[GIGS][ERRO] Botão Salvar não encontrado!')
            return False

        btn_salvar.click()
        if log:
            print('[GIGS] Botão Salvar clicado.')

        # 5. Aguarda confirmação de sucesso
        try:
            success_snackbar = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span'))
            )
            if 'salva com sucesso' in success_snackbar.text.lower():
                if log:
                    print('[GIGS] Mensagem de sucesso confirmada.')
                time.sleep(1)
                if log:
                    print('[GIGS] GIGS criado com sucesso!')
                return True
            else:
                if log:
                    print('[GIGS][AVISO] Snackbar encontrado mas sem mensagem de sucesso.')
        except Exception as e:
            if log:
                print(f'[GIGS][AVISO] Não foi possível confirmar mensagem de sucesso: {e}')

        return True

    except Exception as e:
        if log:
            print(f'[GIGS][ERRO] Falha ao criar GIGS: {e}')
        return False

# =========================
# 9. INTERFACE E INTERAÇÕES
# =========================

def visibilidade_sigilosos(driver, polo='ativo', log=True):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente, conforme lógica do gigs-plugin.js.
    polo: 'ambos', 'ativo', 'passivo' ou 'nenhum'
    """
    try:
        # 1. Seleciona o último documento sigiloso na timeline
        sigiloso_link = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline a.tl-documento.is-sigiloso:last-child')
        if not sigiloso_link:
            if log:
                print('[VISIBILIDADE][ERRO] Documento sigiloso não encontrado na timeline.')
            return False
        # Extrai id do documento
        aria_label = sigiloso_link.get_attribute('aria-label')
        import re
        m = re.search(r'Id[:\.\s]+([A-Za-z0-9]{6,8})', aria_label or '')
        if not m:
            if log:
                print('[VISIBILIDADE][ERRO] Não foi possível extrair o ID do documento.')
            return False
        id_documento = m.group(1)
        if log:
            print(f'[VISIBILIDADE] Documento sigiloso encontrado: {id_documento}')
        # 2. Ativa múltipla seleção
        btn_multi = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]')
        btn_multi.click()
        time.sleep(0.5)
        # 3. Marca o checkbox do documento
        mat_checkbox = driver.find_element(By.CSS_SELECTOR, f'mat-card[id*="{id_documento}"] mat-checkbox label')
        mat_checkbox.click()
        time.sleep(0.5)
        # 4. Clica no botão de visibilidade
        btn_visibilidade = driver.find_element(By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
        btn_visibilidade.click()
        time.sleep(1)
        # 5. No modal, seleciona o polo desejado
        if polo == 'ativo':
            icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo')
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'passivo':
            icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo')
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'ambos':
            # Marca todos
            btn_todos = driver.find_element(By.CSS_SELECTOR, 'th button')
            btn_todos.click()
        # 6. Confirma no botão Salvar
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
        )
        btn_salvar.click()
        time.sleep(1)
        # 7. Oculta múltipla seleção
        try:
            btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
            btn_ocultar.click()
        except:
            pass
        if log:
            print('[VISIBILIDADE] Visibilidade aplicada com sucesso.')
        return True
    except Exception as e:
        if log:
            print(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}')
        return False

# =========================
# FUNÇÕES NÃO UTILIZADAS (PARA ANÁLISE POSTERIOR)
# =========================

# [Lista de funções não importadas que podem ser removidas ou integradas futuramente]
# formatar_data_brasileira, extrair_raiz_cnpj, identificar_tipo_documento, _audit, _log_info, _log_error
# limpar_temp_selenium, configurar_navegador, obter_driver_padronizado (já incluído), driver_notebook
# salvar_cookies, carregar_cookies, login_notebook, login_notebook_humano, checar_acesso_negado
# filtro_fase, buscar_seletor_robusto, preencher_campos_prazo, gigs_minuta, criar_comentario
# analise_argos, buscar_documento_argos, tratar_anexos_argos, analise_outros, is_browsing_context_discarded_error
# indexar_processos, reiniciar_driver_e_logar_pje, executar_callback, forcar_fechamento_abas_extras
# relatorio_final, extrair_xs_atividades, esperar_colecao, wait_for_clickable, criar_template_juntada
# clicar_em_elemento_com_texto, selecionar_destinatario_por_nome, verificar_documento_decisao_sentenca
# criar_botoes_detalhes, buscar_ultimo_mandado, buscar_mandado_autor, colar_conteudo
# extrair_documento_silencioso, buscar_documentos_sequenciais, esperar_url_conter, BNDT_apagar
# filtrofases, finalizar_driver, extrair_direto

def obter_driver_padronizado(headless=False):
    """
    Cria e configura um driver Firefox padronizado para o PJe
    """
    try:
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        import os

        options = Options()

        if headless:
            options.add_argument('--headless')

        # Configurações essenciais para PJe
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--ignore-ssl-errors-ignore-untrusted')

        # Perfil personalizado
        profile_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\pjeprofile"
        if os.path.exists(profile_path):
            options.add_argument(f"-profile")
            options.add_argument(profile_path)

        # Executável personalizado
        firefox_path = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
        if os.path.exists(firefox_path):
            options.binary_location = firefox_path

        service = Service()
        driver = webdriver.Firefox(service=service, options=options)

        # Configurações adicionais
        driver.maximize_window()
        driver.implicitly_wait(10)

        return driver

    except Exception as e:
        print(f"[ERRO] Falha ao criar driver padronizado: {e}")
        return None

def reiniciar_driver_e_logar_pje(driver, log=True):
    """
    Reinicia o driver do PJe usando as fábricas em `driver_config` e executa o login
    Retorna o novo driver se bem-sucedido, ou None em caso de falha.
    """
    try:
        if log:
            print('[RECOVERY][RESTART] Tentando reiniciar driver e efetuar novo login...')
        try:
            try:
                driver.quit()
            except Exception:
                pass

            from driver_config import criar_driver, login_func

            novo_driver = criar_driver()
            if not novo_driver:
                if log:
                    print('[RECOVERY][RESTART] Falha ao criar novo driver')
                return None

            ok = False
            try:
                ok = login_func(novo_driver)
            except Exception as e:
                if log:
                    print(f'[RECOVERY][RESTART] Erro ao executar login_func: {e}')
                ok = False

            if not ok:
                if log:
                    print('[RECOVERY][RESTART] Login falhou no novo driver')
                try:
                    novo_driver.quit()
                except Exception:
                    pass
                return None

            try:
                url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
                novo_driver.get(url_atividades)
                time.sleep(4)
            except Exception:
                pass

            if log:
                print('[RECOVERY][RESTART] Novo driver criado e logado com sucesso')
            return novo_driver

        except Exception as e:
            if log:
                print(f'[RECOVERY][RESTART] Falha durante reinício do driver: {e}')
            return None
    except Exception as e:
        print(f'[RECOVERY][RESTART][ERRO] Exceção inesperada: {e}')
        return None

# ===============================================
# FUNÇÕES UTILITÁRIAS ADICIONADAS/RECUPERADAS
# ===============================================

def limpar_temp_selenium():
    # Limpa os arquivos temporários do Selenium de forma segura.
    # Remove apenas arquivos .part e temp files antigos.
    import os, time, glob
    from datetime import datetime, timedelta
    
    try:
        # Define pastas temporárias comuns
        temp_dirs = [
            os.path.join(os.environ['TEMP'], 'selenium*'),
            os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp', 'selenium*')
        ]
        
        # Limpeza segura
        deleted = 0
        for pattern in temp_dirs:
            for filepath in glob.glob(pattern):
                try:
                    # Verifica se o arquivo é antigo (>1 dia)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if datetime.now() - file_time > timedelta(days=1):
                        os.remove(filepath)
                        deleted += 1
                except Exception as e:
                    print(f'[AVISO] Não removeu {filepath}: {str(e)}')
        
        print(f'[SELENIUM] Limpeza concluída - {deleted} arquivos removidos')
        return True
    except Exception as e:
        print(f'[ERRO] Falha na limpeza: {str(e)}')
        return False

def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5, log=True):
    """
    Busca seletor robusto para elementos baseado em textos.
    Retorna o primeiro elemento encontrado que contenha algum dos textos.
    """
    try:
        if contexto:
            base_element = esperar_elemento(driver, contexto, timeout=timeout)
            if not base_element:
                if log:
                    print(f'[SELETOR ROBUSTO] Contexto não encontrado: {contexto}')
                return None
        else:
            base_element = driver

        # Estratégias de busca
        estrategias = [
            # 1. Busca por texto exato em links
            lambda: base_element.find_element(By.XPATH, f"//a[normalize-space(text())='{textos[0]}']"),
            # 2. Busca por texto parcial em links
            lambda: base_element.find_element(By.XPATH, f"//a[contains(text(), '{textos[0]}')]"),
            # 3. Busca por texto em botões
            lambda: base_element.find_element(By.XPATH, f"//button[normalize-space(text())='{textos[0]}']"),
            # 4. Busca por texto parcial em botões
            lambda: base_element.find_element(By.XPATH, f"//button[contains(text(), '{textos[0]}')]"),
            # 5. Busca por atributo title
            lambda: base_element.find_element(By.CSS_SELECTOR, f'[title*="{textos[0]}"]'),
            # 6. Busca por atributo placeholder
            lambda: base_element.find_element(By.CSS_SELECTOR, f'[placeholder*="{textos[0]}"]'),
        ]

        for estrategia in estrategias:
            try:
                elemento = estrategia()
                if elemento and elemento.is_displayed():
                    if log:
                        print(f'[SELETOR ROBUSTO] Elemento encontrado com estratégia: {estrategia.__name__}')
                    return elemento
            except:
                continue

        if log:
            print(f'[SELETOR ROBUSTO] Nenhum elemento encontrado para textos: {textos}')
        return None

    except Exception as e:
        if log:
            print(f'[SELETOR ROBUSTO] Erro geral: {e}')
        return None

def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    """Preenche todos os campos de prazo (input[type=text].mat-input-element) dentro do formulário de minuta/comunicação."""
    try:
        # Busca o formulário principal
        form = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form'))
        )
        if not form:
            if log:
                print('[Fix.py] Formulário de minuta/comunicação não encontrado.')
            return False
        
        # Busca todos os campos de texto de prazo
        inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="text"].mat-input-element')
        if not inputs:
            if log:
                print('[Fix.py] Nenhum campo de prazo encontrado.')
            return False
        
        for campo in inputs:
            driver.execute_script("arguments[0].focus();", campo)
            campo.clear()
            campo.send_keys(str(valor))
            
            # Dispara eventos JS para simular digitação real
            driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
            driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
            
            if log:
                print(f'[Fix.py] Campo de prazo preenchido com {valor}')
        
        return True
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao preencher campos de prazo: {e}')
        return False

def esperar_url_conter(driver, substring, timeout=10):
    """
    Espera até que a URL atual contenha a substring especificada.
    Args:
        driver: WebDriver instance
        substring: String a ser encontrada na URL
        timeout: Tempo máximo de espera em segundos
    Returns:
        bool: True se encontrou, False se timeout
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: substring in d.current_url
        )
        return True
    except Exception as e:
        print(f'[URL][ERRO] Erro ao esperar URL conter "{substring}": {e}')
        return False

def buscar_documentos_sequenciais(driver):
    """
    Busca documentos sequenciais na árvore e os seleciona.
    """
    try:
        import re
        arvore = esperar_elemento(driver, 'pje-arvore-documento', timeout=15)
        if not arvore:
            print('[DOC SEQ] Árvore de documentos não encontrada.')
            return False

        nos_texto = arvore.find_elements(By.CSS_SELECTOR, '.node-content-wrapper span')
        documentos_encontrados = []
        padrao = re.compile(r"^(\d+)\s*-\s*(.+)")

        for no in nos_texto:
            texto_no = no.text.strip()
            match = padrao.match(texto_no)
            if match:
                numero = int(match.group(1))
                descricao = match.group(2)
                documentos_encontrados.append({'numero': numero, 'descricao': descricao, 'elemento': no})

        if not documentos_encontrados:
            print('[DOC SEQ] Nenhum documento com padrão número-descrição encontrado.')
            return False

        documentos_encontrados.sort(key=lambda x: x['numero'])
        selecionou_algum = False

        for i in range(len(documentos_encontrados) - 1):
            doc_atual = documentos_encontrados[i]
            doc_proximo = documentos_encontrados[i+1]

            # Verifica se são sequenciais
            if doc_atual['numero'] + 1 == doc_proximo['numero']:
                print(f'[DOC SEQ] Sequência encontrada: {doc_atual["numero"]} -> {doc_proximo["numero"]}')
                # Tenta encontrar o checkbox associado
                try:
                    checkbox_atual = doc_atual['elemento'].find_element(By.XPATH, './ancestor::mat-tree-node//mat-checkbox')
                    checkbox_proximo = doc_proximo['elemento'].find_element(By.XPATH, './ancestor::mat-tree-node//mat-checkbox')

                    # Clica se não estiver selecionado
                    if not checkbox_atual.find_element(By.TAG_NAME, 'input').is_selected():
                        safe_click(driver, checkbox_atual)
                        print(f'[DOC SEQ] Checkbox para doc {doc_atual["numero"]} marcado.')
                        selecionou_algum = True
                    if not checkbox_proximo.find_element(By.TAG_NAME, 'input').is_selected():
                        safe_click(driver, checkbox_proximo)
                        print(f'[DOC SEQ] Checkbox para doc {doc_proximo["numero"]} marcado.')
                        selecionou_algum = True
                except Exception as e:
                    print(f'[DOC SEQ] Erro ao marcar checkboxes: {e}')

        if selecionou_algum:
            print('[DOC SEQ] Documentos sequenciais selecionados com sucesso.')
            return True
        else:
            print('[DOC SEQ] Nenhum documento sequencial foi selecionado.')
            return False

    except Exception as e:
        print(f'[DOC SEQ] Erro geral: {e}')
        return False

def driver_notebook(headless=False):
    # Retorna um driver Firefox padronizado para o ambiente TRT2, usando um perfil específico para notebooks.
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import os
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

def finalizar_driver(driver, log=True):
    """Finaliza o driver de forma segura, aguardando operações pendentes"""
    import time
    try:
        # Fecha todas as janelas exceto a principal
        if len(driver.window_handles) > 1:
            janela_principal = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(janela_principal)
        
        # Pequeno delay para operações pendentes
        time.sleep(0.5)
        
        # Fecha o driver
        driver.quit()
        
        if log:
            print('[DRIVER] Driver finalizado com sucesso')
        return True
    except Exception as e:
        if log:
            print(f'[DRIVER][AVISO] Erro ao finalizar driver: {e}')
        return False

def extrair_direto(driver, timeout=10, debug=False, formatar=True):
    """
    Extrai o conteúdo do documento PDF ativo na tela do processo PJe DIRETAMENTE.
    SEM CLIQUES, SEM INTERAÇÃO, apenas leitura direta.
    Função única e completa com todas as funcionalidades integradas.
    
    Args:
        driver: WebDriver do Selenium
        timeout: Timeout para operações
        debug: Se True, exibe logs detalhados
        formatar: Se True, aplica formatação organizacional ao texto
    
    Returns:
        dict: {
            'conteudo': str,           # Texto formatado (se formatar=True)
            'conteudo_bruto': str,     # Texto original
            'info': dict,              # Metadados do documento
            'sucesso': bool,           # Se extração foi bem-sucedida
            'metodo': str              # Método que funcionou
        }
    """
    
    def log_debug(msg):
        """Função auxiliar para logs de debug"""
        if debug:
            print(f'[EXTRAIR_DIRETO] {msg}')
    
    def formatar_texto(texto_bruto):
        """Função auxiliar para organizar e formatar o texto extraído"""
        if not texto_bruto or not texto_bruto.strip():
            return ""
        
        try:
            log_debug("Aplicando formatação ao texto...")
            
            # 1. Limpeza inicial
            texto = texto_bruto.strip()
            
            # 2. Normalizar quebras de linha
            import re
            texto = re.sub(r'\r\n|\r', '\n', texto)
            
            # 3. Remover espaços excessivos
            texto = re.sub(r'[ \t]+', ' ', texto)
            
            # 4. Normalizar múltiplas quebras de linha
            texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
            
            return texto.strip()
            
        except Exception as e:
            log_debug(f"Erro na formatação: {e}")
            return texto_bruto
    
    # ===== INÍCIO DA FUNÇÃO PRINCIPAL =====
    resultado = {
        'conteudo': None,
        'conteudo_bruto': None,
        'info': {},
        'sucesso': False,
        'metodo': None
    }
    
    try:
        log_debug("Iniciando extração DIRETA do documento ativo...")
        
        # 1. Aguardar e verificar documento ativo
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            documento_wrapper = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "documento"))
            )
            log_debug("Elemento #documento encontrado")
            
        except Exception as timeout_error:
            log_debug(f"Timeout aguardando #documento: {timeout_error}")
            try:
                documento_wrapper = driver.find_element(By.ID, "documento")
                log_debug("Elemento #documento encontrado (busca direta)")
            except:
                log_debug("Elemento #documento não encontrado")
                return resultado
        
        # 2. Buscar object PDF ativo
        try:
            pdf_object = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "object.conteudo-pdf"))
            )
            
            WebDriverWait(driver, timeout).until(
                lambda d: pdf_object.get_attribute("data") is not None
            )
            
            pdf_url = pdf_object.get_attribute("data")
            log_debug(f"PDF Object encontrado com URL: {pdf_url}")
            
        except Exception as pdf_error:
            log_debug(f"Erro ao encontrar PDF object: {pdf_error}")
            return resultado
        
        # 3. MÉTODO 1: PDF.js viewer (prioritário)
        try:
            log_debug("Tentando extrair do PDF.js viewer...")
            
            js_script = """
            try {
                var pdfFrame = document.querySelector('object[data*="viewer.html"], iframe[src*="viewer.html"]');
                if (pdfFrame) {
                    try {
                        var frameDoc = pdfFrame.contentDocument || pdfFrame.contentWindow.document;
                        
                        // Aguardar textLayers carregarem
                        var maxAttempts = 10;
                        var attempt = 0;
                        
                        while (attempt < maxAttempts) {
                            var textLayers = frameDoc.querySelectorAll('.textLayer, .page .textLayer');
                            
                            if (textLayers.length > 0) {
                                var fullText = '';
                                var hasValidText = false;
                                
                                for (var i = 0; i < textLayers.length; i++) {
                                    var pageText = textLayers[i].textContent || textLayers[i].innerText;
                                    if (pageText && pageText.trim().length > 10) {
                                        fullText += pageText + '\\n';
                                        hasValidText = true;
                                    }
                                }
                                
                                if (hasValidText) {
                                    return fullText.trim();
                                }
                            }
                            
                            var start = Date.now();
                            while (Date.now() - start < 100) {}
                            attempt++;
                        }
                        
                        var viewer = frameDoc.querySelector('#viewer');
                        if (viewer) {
                            var pages = viewer.querySelectorAll('.page');
                            var fullText = '';
                            for (var i = 0; i < pages.length; i++) {
                                var pageText = pages[i].textContent || pages[i].innerText;
                                if (pageText && pageText.trim().length > 10) {
                                    fullText += pageText + '\\n';
                                }
                            }
                            if (fullText.trim()) {
                                return fullText.trim();
                            }
                        }
                    } catch (e) {
                        console.log('Cross-origin restriction:', e);
                    }
                }
                
                // Buscar na janela principal
                var mainViewer = document.querySelector('#viewer');
                if (mainViewer) {
                    var pages = mainViewer.querySelectorAll('.page');
                    var fullText = '';
                    for (var i = 0; i < pages.length; i++) {
                        var pageText = pages[i].textContent || pages[i].innerText;
                        if (pageText && pageText.trim().length > 10) {
                            fullText += pageText + '\\n';
                        }
                    }
                    if (fullText.trim()) {
                        return fullText.trim();
                    }
                }
                
                var textLayers = document.querySelectorAll('.textLayer, .page .textLayer');
                if (textLayers.length > 0) {
                    var fullText = '';
                    for (var i = 0; i < textLayers.length; i++) {
                        var pageText = textLayers[i].textContent || textLayers[i].innerText;
                        if (pageText && pageText.trim().length > 10) {
                            fullText += pageText + '\\n';
                        }
                    }
                    if (fullText.trim()) {
                        return fullText.trim();
                    }
                }
                
                return null;
            } catch (e) {
                console.log('Erro geral:', e);
                return null;
            }
            """
            
            texto_extraido = driver.execute_script(js_script)
            
            if texto_extraido and len(texto_extraido.strip()) > 20:
                log_debug(f"Texto extraído com sucesso via PDF.js: {len(texto_extraido)} caracteres")
                resultado['conteudo_bruto'] = texto_extraido
                resultado['conteudo'] = formatar_texto(texto_extraido) if formatar else texto_extraido
                resultado['sucesso'] = True
                resultado['metodo'] = 'PDF.js viewer'
                return resultado
            else:
                log_debug("PDF.js não retornou texto válido")
                
        except Exception as js_error:
            log_debug(f"Erro no método PDF.js: {js_error}")
        
        # 4. MÉTODO 2: Fallback - extrair via textContent do object
        try:
            log_debug("Tentando método fallback...")
            
            texto_fallback = driver.execute_script("""
                var pdfObj = document.querySelector('object.conteudo-pdf');
                if (pdfObj) {
                    return pdfObj.textContent || pdfObj.innerText || '';
                }
                return '';
            """)
            
            if texto_fallback and len(texto_fallback.strip()) > 10:
                log_debug(f"Fallback funcionou: {len(texto_fallback)} caracteres")
                resultado['conteudo_bruto'] = texto_fallback
                resultado['conteudo'] = formatar_texto(texto_fallback) if formatar else texto_fallback
                resultado['sucesso'] = True
                resultado['metodo'] = 'textContent fallback'
                return resultado
            
        except Exception as fallback_error:
            log_debug(f"Erro no fallback: {fallback_error}")
        
        log_debug("Nenhum método de extração funcionou")
        return resultado
        
    except Exception as e:
        log_debug(f"Erro geral na extração: {e}")
        return resultado

def login_notebook(driver):
    """Login automático para notebook - versão simplificada baseada em login_pc"""
    try:
        # Usa a mesma lógica do login_pc mas com perfil de notebook
        return login_automatico(driver)
    except Exception as e:
        print(f'[LOGIN][NOTEBOOK] Erro: {e}')
        return False

def buscar_documento_argos(driver, log=True):
    """Busca documentos relevantes na timeline do Argos, priorizando decisões/despachos anteriores à Planilha de Atualização de Cálculos."""
    try:
        print('[ARGOS][DOC] Iniciando busca de documento relevante...')
        
        # Aguarda a timeline carregar (aguarda pelo menos um item na timeline)
        timeline_selector = 'li.tl-item-container'
        print('[ARGOS][DOC] Aguardando carregamento da timeline...')
        
        # Usando as novas funções do Fix.py
        timeline_item = wait(driver, timeline_selector, timeout=15)
        
        if not timeline_item:
            print('[ARGOS][DOC][ERRO] Timeline não carregou após 15 segundos de espera')
            return None, None
            
        print('[ARGOS][DOC] Timeline carregada com sucesso')
        
        # Garantimos um tempo extra para carregar completamente a timeline
        sleep(1000)
        
        # Buscamos todos os itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, timeline_selector)
        print(f'[ARGOS][DOC] Encontrados {len(itens)} itens na timeline')
        
        # NOVA REGRA: Busca por decisões/despachos anteriores à Planilha de Atualização de Cálculos
        planilha_index = None
        documentos_antes_planilha = []
        
        # Primeiro, encontra a primeira "Planilha de Atualização de Cálculos" na timeline
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                doc_text = link.text.lower()
                if 'planilha de atualização' in doc_text or 'planilha de atuali' in doc_text:
                    planilha_index = idx
                    if log:
                        print(f'[ARGOS][DEBUG] Planilha de Atualização encontrada no item {idx}: {doc_text}')
                    break
            except Exception:
                continue
        
        # Se encontrou uma planilha, procura por decisões/despachos anteriores a ela
        if planilha_index is not None:
            if log:
                print(f'[ARGOS][DEBUG] Procurando decisões/despachos antes da planilha (itens 0 a {planilha_index-1})...')
            
            for idx in range(planilha_index):
                try:
                    item = itens[idx]
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    doc_text = link.text.lower()
                    
                    # Verifica se é despacho ou decisão
                    if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                        documentos_antes_planilha.append((idx, item, link, doc_text))
                        if log:
                            print(f'[ARGOS][DEBUG] Item {idx}: documento relevante encontrado antes da planilha: {doc_text}')
                except Exception:
                    continue
            
            # Se encontrou documentos antes da planilha, processa o primeiro
            if documentos_antes_planilha:
                idx, item, link, doc_text = documentos_antes_planilha[0]
                if log:
                    print(f'[ARGOS][DEBUG] Processando primeiro documento antes da planilha: item {idx}')
                  # Clica para ativar o documento usando safe_click
                print(f'[ARGOS][DOC] Tentando abrir documento: {doc_text}')
                # Primeiro rolamos para o elemento para garantir visibilidade
                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', link)
                sleep(500)  # Breve pausa após scroll
                
                # Tentamos o clique seguro
                click_resultado = safe_click(driver, link, log=True)
                
                if not click_resultado:
                    print(f'[ARGOS][DOC][ERRO] Falha ao clicar no documento usando safe_click. Tentando método alternativo.')
                    try:
                        driver.execute_script('arguments[0].click();', link)
                        print(f'[ARGOS][DOC] Clique via JavaScript executado com sucesso')
                    except Exception as e:
                        print(f'[ARGOS][DOC][ERRO] Falha no clique alternativo: {e}')
                
                sleep(1500)  # Esperamos mais tempo para carregar o documento
                print(f'[ARGOS][DOC] Extraindo texto do documento...')
                
                # Tentar extrair_direto primeiro, com fallback para extrair_pdf
                texto = None
                try:
                    resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=False)
                    if resultado_direto and resultado_direto.get('sucesso') and resultado_direto.get('conteudo_bruto'):
                        texto = resultado_direto['conteudo_bruto']
                        print(f'[ARGOS][DOC] ✅ Extração DIRETA bem-sucedida via {resultado_direto.get("metodo", "método desconhecido")}')
                    else:
                        print('[ARGOS][DOC] ⚠️ extrair_direto não conseguiu extrair texto válido, tentando extrair_pdf...')
                        texto = extrair_pdf(driver, log=False)
                        if texto:
                            print('[ARGOS][DOC] ✅ Extração via extrair_pdf bem-sucedida')
                        else:
                            print('[ARGOS][DOC] ❌ Ambos os métodos de extração falharam')
                except Exception as e:
                    print(f'[ARGOS][DOC] ❌ Erro na extração DIRETA: {e}, tentando extrair_pdf...')
                    try:
                        texto = extrair_pdf(driver, log=False)
                        if texto:
                            print('[ARGOS][DOC] ✅ Extração via extrair_pdf bem-sucedida (fallback)')
                        else:
                            print('[ARGOS][DOC] ❌ Método de fallback também falhou')
                    except Exception as e2:
                        print(f'[ARGOS][DOC] ❌ Erro no método de fallback: {e2}')
                
                if log:
                    print(f'[ARGOS][DEBUG] TEXTO EXTRAÍDO DO DOCUMENTO (antes da planilha):\n---\n{texto}\n---')
                
                # Determina o tipo do documento
                if 'decisão' in doc_text or 'sentença' in doc_text:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: documento é decisão/sentença anterior à planilha.')
                    return texto, 'decisao'
                else:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: documento é despacho anterior à planilha.')
                    return texto, 'despacho'
        
        # FALLBACK: Se não encontrou planilha ou documentos antes dela, usa a lógica original
        # LIMITADO A 4 DESPACHOS/DECISÕES MÁXIMO (não conta outros tipos de documento)
        if log:
            print('[ARGOS][DEBUG] Usando lógica fallback: procurando primeiro despacho/decisão na timeline...')
        
        despachos_decisoes_processados = 0
        max_despachos_decisoes = 4
        
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: texto do link = {doc_text}')
                
                # Verifica se é despacho ou decisão PRIMEIRO
                if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    despachos_decisoes_processados += 1
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: é despacho/decisão ({despachos_decisoes_processados}/{max_despachos_decisoes}), clicando para ativar.')
                    
                    # Clica para ativar o documento usando safe_click (fallback)
                    print(f'[ARGOS][DOC][FALLBACK] Tentando abrir documento: {doc_text}')
                    # Primeiro rolamos para o elemento
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', link)
                    sleep(500)
                    
                    # Tentamos o clique seguro
                    click_resultado = safe_click(driver, link, log=True)
                    
                    if not click_resultado:
                        print(f'[ARGOS][DOC][FALLBACK][ERRO] Falha ao clicar no documento. Tentando método alternativo.')
                        try:
                            driver.execute_script('arguments[0].click();', link)
                            print(f'[ARGOS][DOC][FALLBACK] Clique via JavaScript executado com sucesso')
                        except Exception as e:
                            print(f'[ARGOS][DOC][FALLBACK][ERRO] Falha no clique alternativo: {e}')
                            # Não incrementa o contador se falhou no clique
                            despachos_decisoes_processados -= 1
                            continue  # Tenta próximo documento se falha no clique
                    
                    sleep(1500)  # Esperamos mais tempo para carregar o documento
                    print(f'[ARGOS][DOC][FALLBACK] Extraindo texto do documento...')
                    
                    # Verificar se o cabeçalho está presente antes da extração
                    def verificar_cabecalho_presente():
                        """Verifica se o cabeçalho do processo está visível na página"""
                        try:
                            # Tentar múltiplos seletores do cabeçalho
                            cabecalho_selectors = [
                                'mat-toolbar[color="primary"]',
                                'pje-cabecalho-processo',
                                '.texto-numero-processo',
                                '.texto-tarefa-processo'
                            ]
                            
                            for selector in cabecalho_selectors:
                                try:
                                    elemento = driver.find_element(By.CSS_SELECTOR, selector)
                                    if elemento.is_displayed():
                                        print(f'[ARGOS][DOC][SELETOR] ✅ Cabeçalho encontrado com seletor: {selector}')
                                        return True
                                except:
                                    continue
                            return False
                        except Exception:
                            return False
                    
                    # Se o cabeçalho não estiver presente, tentar restaurá-lo com TAB
                    if not verificar_cabecalho_presente():
                        print('[ARGOS][DOC][FALLBACK] Cabeçalho não detectado, tentando restaurar com TAB...')
                        try:
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
                            print('[ARGOS][DOC][FALLBACK] Tecla TAB pressionada para restaurar cabeçalho')
                            sleep(1000)  # Aguardar restauração
                            
                            # Verificar novamente se funcionou
                            if verificar_cabecalho_presente():
                                print('[ARGOS][DOC][FALLBACK] ✅ Cabeçalho restaurado com sucesso')
                            else:
                                print('[ARGOS][DOC][FALLBACK] ⚠️ Cabeçalho ainda não detectado após TAB')
                        except Exception as e:
                            print(f'[ARGOS][DOC][FALLBACK][ERRO] Falha ao tentar restaurar cabeçalho: {e}')
                    else:
                        print('[ARGOS][DOC][FALLBACK] ✅ Cabeçalho já está presente')
                    
                    try:
                        # Tentar extrair_direto primeiro, com fallback para extrair_pdf
                        texto = None
                        try:
                            resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=False)
                            if resultado_direto and resultado_direto.get('sucesso') and resultado_direto.get('conteudo_bruto'):
                                texto = resultado_direto['conteudo_bruto']
                                print(f'[ARGOS][DOC][FALLBACK] ✅ Extração DIRETA bem-sucedida via {resultado_direto.get("metodo", "método desconhecido")}')
                            else:
                                print('[ARGOS][DOC][FALLBACK] ⚠️ extrair_direto não conseguiu extrair texto válido, tentando extrair_pdf...')
                                texto = extrair_pdf(driver, log=False)
                                if texto:
                                    print('[ARGOS][DOC][FALLBACK] ✅ Extração via extrair_pdf bem-sucedida')
                                else:
                                    print('[ARGOS][DOC][FALLBACK] ❌ Ambos os métodos de extração falharam')
                        except Exception as e:
                            print(f'[ARGOS][DOC][FALLBACK] ❌ Erro na extração DIRETA: {e}, tentando extrair_pdf...')
                            try:
                                texto = extrair_pdf(driver, log=False)
                                if texto:
                                    print('[ARGOS][DOC][FALLBACK] ✅ Extração via extrair_pdf bem-sucedida (fallback)')
                                else:
                                    print('[ARGOS][DOC][FALLBACK] ❌ Método de fallback também falhou')
                            except Exception as e2:
                                print(f'[ARGOS][DOC][FALLBACK] ❌ Erro no método de fallback: {e2}')
                        
                        if log:
                            print(f'[ARGOS][DEBUG] TEXTO EXTRAÍDO DO DOCUMENTO (fallback):\n---\n{texto}\n---')
                        
                        if 'decisão' in doc_text or 'sentença' in doc_text:
                            if log:
                                print(f'[ARGOS][DEBUG] Item {idx}: documento é decisão/sentença (fallback).')
                            return texto, 'decisao'
                        else:
                            if log:
                                print(f'[ARGOS][DEBUG] Item {idx}: documento é despacho (fallback).')
                            return texto, 'despacho'
                    except Exception as e:
                        if log:
                            print(f'[ARGOS][DEBUG] Item {idx}: erro ao extrair texto do documento: {e}')
                        # Não incrementa o contador se falhou na extração
                        despachos_decisoes_processados -= 1
                        continue  # Tenta próximo documento se falha na extração
                        
                    # Limite de 4 despachos/decisões APÓS encontrar um válido
                    if despachos_decisoes_processados >= max_despachos_decisoes:
                        if log:
                            print(f'[ARGOS][DEBUG] Limite de {max_despachos_decisoes} despachos/decisões atingido no fallback, encerrando busca.')
                        break
                else:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: não é despacho/decisão/sentença/conclusão.')
            except Exception as e:
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: erro ao processar item: {e}')
                continue
        
        if log:
            print(f'[ARGOS] Nenhum documento relevante encontrado após varrer {despachos_decisoes_processados} despachos/decisões (máximo {max_despachos_decisoes}).')
        return None, None
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha ao buscar documento: {e}')
            print('[ARGOS][INFO] Tentando fallback...')
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
            for elem in elementos:
                if elem.is_displayed() and not elem.get_attribute('target'):
                    if log:
                        print('[ARGOS][DEBUG] Fallback: clicando em documento visível.')
                    safe_click(driver, elem)
                    time.sleep(1)
                    texto = extrair_documento(driver)
                    if texto:
                        return texto, 'fallback'
        except Exception as e_fb:
            if log:
                print(f'[ARGOS][ERRO] Fallback também falhou: {e_fb}')
        return None, None

def aplicar_filtro_100(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    try:
        driver.execute_script("document.body.style.zoom='50%'")
        
        # Método simplificado que funciona
        for tentativa in range(2):  # Reduzido para 2 tentativas
            try:
                print(f'[FILTRO_LISTA_100] Tentativa {tentativa + 1}...')
                
                # Busca pelo span '20' e encontra o mat-select pai
                span_20 = driver.find_element(By.XPATH, "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
                mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
                
                # Scroll para centralizar o elemento
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mat_select)
                time.sleep(0.3)
                
                # Clique com fallback para JavaScript
                try:
                    mat_select.click()
                except:
                    driver.execute_script("arguments[0].click();", mat_select)
                
                # Aguarda overlay e seleciona opção 100
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                opcao_100 = overlay.find_element(By.XPATH, ".//mat-option[.//span[normalize-space(text())='100']]")
                opcao_100.click()
                time.sleep(1)
                
                print('[FILTRO_LISTA_100] Filtro aplicado com sucesso!')
                return True
                
            except Exception as e:
                print(f'[FILTRO_LISTA_100] Tentativa {tentativa + 1} falhou: {e}')
                if tentativa < 1:
                    time.sleep(1)
        
        # Se chegou aqui, todas as tentativas falharam
        print('[FILTRO_LISTA_100][ERRO] Falha após todas as tentativas')
        return False
        
    except Exception as e:
        print(f'[FILTRO_LISTA_100][ERRO] Falha geral: {e}')
        return False

def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                print('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            print('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            print('[ERRO] Painel de opções não apareceu.')
            return False
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        print(f'[OK] Fase "{fase}" selecionada.')
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            print(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[OK] Fases selecionadas e filtro aplicado (botão filtrar).')
            time.sleep(1)
        except Exception as e:
            print(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        # Generalização da seleção de tarefa
        if tarefas_alvo:
            print(f'Filtrando tarefa: {", ".join(tarefas_alvo).title()}...')
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(By.XPATH, f"//span[contains(text(), '{seletor_tarefa}')]")
            except Exception:
                try:
                    seletor = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                        if seletor_tarefa in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    print(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                    return False
            if not tarefa_element:
                print(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                return False
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            painel = None
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            if not painel or not painel.is_displayed():
                print('[ERRO] Painel de opções de tarefa não apareceu.')
                return False
            tarefas_clicadas = set()
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if tarefa.lower() in texto and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            print(f'[OK] Tarefa "{tarefa}" selecionada.')
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            if len(tarefas_clicadas) == 0:
                print(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                print('[OK] Tarefas selecionadas e filtro aplicado (botão filtrar).')
                time.sleep(1)
            except Exception as e:
                print(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    return True


def copiacont(driver, doc_id=None, log=False):
    """
    Copia o conteúdo de um documento do PJe para a área de transferência.
    Baseado na função copiarDocumentoProcesso do gigs.py.
    
    Args:
        driver: Instância do WebDriver
        doc_id: ID do documento (opcional, se None usa documento atual)
        log: Ativa logs detalhados
    
    Returns:
        str: Conteúdo copiado ou None em caso de erro
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    import re
    
    if log:
        print('[COPIACONT] Iniciando cópia de documento...')
    
    try:
        conteudo = ""
        tipo_documento = None
        id_documento = None
        
        if not doc_id:
            # Sistema antigo - minutar despacho, intimação, anexar documentos
            if log:
                print('[COPIACONT] Modo: documento atual (sistema antigo)')
            
            titulo_elemento = driver.find_element(By.CSS_SELECTOR, '.mat-card-title')
            titulo_documento = titulo_elemento.text
            
            # Extrair tipo e ID do título
            if ' - ' in titulo_documento and 'Id ' in titulo_documento:
                tipo_documento = titulo_documento.split(' - ')[1].replace('.pdf', '')
                id_documento = re.search(r'Id ([A-Za-z0-9]+)', titulo_documento).group(1)
            
            if log:
                print(f'[COPIACONT] Tipo: {tipo_documento}, ID: {id_documento}')
            
            conteudo += f'Transcrição do(a) {tipo_documento} (ID {id_documento}): \n"'
            
            # Verifica se é HTML antigo ou novo
            try:
                container_html = driver.find_element(By.CSS_SELECTOR, '.container-html')
                if log:
                    print('[COPIACONT] Formato: HTML antigo')
                conteudo += container_html.find_element(By.XPATH, './/*').text.replace('\r\n', '').replace('\n', '').replace('\r', '')
                conteudo += '"'
            except:
                if log:
                    print('[COPIACONT] Formato: HTML novo, abrindo visualizador...')
                
                # Clicar em "Visualizar HTML original"
                btn_html = driver.find_element(By.CSS_SELECTOR, 'pje-documento-visualizador button[mattooltip="Visualizar HTML original"]')
                btn_html.click()
                time.sleep(2)
                
                # Aguardar modal
                try:
                    ancora = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-documento-original'))
                    )
                    
                    ancora_texto = ancora.find_element(By.CSS_SELECTOR, 'div#previewModeloDocumento div')
                    conteudo += ancora_texto.text
                    conteudo += '"'
                    
                    # Fechar modal
                    btn_fechar = ancora.find_element(By.CSS_SELECTOR, 'button[aria-label="Fechar"]')
                    btn_fechar.click()
                    time.sleep(0.5)
                    
                    if log:
                        print('[COPIACONT] ✅ Transcrição concluída com sucesso')
                except:
                    if log:
                        print('[COPIACONT] ❌ Não foi possível concluir a transcrição')
                    return None
        else:
            # Sistema novo - janela de detalhes do processo
            if log:
                print(f'[COPIACONT] Modo: documento ID {doc_id} (sistema novo)')
            
            ancora = driver.find_element(By.CSS_SELECTOR, 'pje-historico-scroll-titulo')
            titulo_elemento = ancora.find_element(By.CSS_SELECTOR, '.mat-card-title')
            titulo_documento = titulo_elemento.text
            
            # Extrair tipo e ID do título
            if ' - ' in titulo_documento and 'Id ' in titulo_documento:
                tipo_documento = titulo_documento.split(' - ')[1].replace('.pdf', '')
                id_documento = re.search(r'Id ([A-Za-z0-9]+)', titulo_documento).group(1)
            
            if log:
                print(f'[COPIACONT] Tipo: {tipo_documento}, ID: {id_documento}')
            
            conteudo += f'Transcrição do(a) {tipo_documento} (ID {id_documento}): \n"'
            
            # Verifica se é HTML antigo ou novo
            try:
                container_html = driver.find_element(By.CSS_SELECTOR, '.container-html')
                if log:
                    print('[COPIACONT] Formato: HTML antigo')
                conteudo += container_html.find_element(By.XPATH, './/*').text.replace('\r\n', '').replace('\n', '').replace('\r', '')
                conteudo += '"'
            except:
                if log:
                    print('[COPIACONT] Formato: HTML novo, abrindo visualizador...')
                
                # Clicar em "Visualizar HTML original"
                btn_html = driver.find_element(By.CSS_SELECTOR, 'pje-historico-scroll-titulo button[mattooltip="Visualizar HTML original"]')
                btn_html.click()
                time.sleep(2)
                
                # Aguardar modal
                try:
                    ancora = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-documento-original'))
                    )
                    
                    ancora_texto = ancora.find_element(By.CSS_SELECTOR, '#previewModeloDocumento')
                    conteudo += ancora_texto.text
                    conteudo += '"'
                    
                    # Fechar modal
                    btn_fechar = ancora.find_element(By.CSS_SELECTOR, 'button[aria-label="Fechar"]')
                    btn_fechar.click()
                    time.sleep(0.5)
                    
                    if log:
                        print('[COPIACONT] ✅ Transcrição concluída com sucesso')
                except:
                    if log:
                        print('[COPIACONT] ❌ Não foi possível concluir a transcrição')
                    return None
        
        # Limpar espaços duplicados
        texto_copiado = re.sub(r'\s{2,}', ' ', conteudo)
        
        # Copiar para clipboard usando pyperclip (mais confiável que clipboard direto)
        try:
            import pyperclip
            pyperclip.copy(texto_copiado)
            if log:
                print('[COPIACONT] ✅ Texto copiado para área de transferência')
        except ImportError:
            # Fallback: usar JavaScript
            driver.execute_script(f"navigator.clipboard.writeText(`{texto_copiado}`);")
            if log:
                print('[COPIACONT] ✅ Texto copiado para área de transferência (via JS)')
        
        return texto_copiado
        
    except Exception as e:
        if log:
            print(f'[COPIACONT] ❌ Erro ao copiar documento: {e}')
        return None


