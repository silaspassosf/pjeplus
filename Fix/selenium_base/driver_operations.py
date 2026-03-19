import logging
logger = logging.getLogger(__name__)

"""
Fix.selenium_base.driver_operations - Módulo de operações de drivers Selenium.

Parte da refatoração do Fix/core.py para melhor granularidade IA.
Nível 2 (Estratégias): Funções de criação e gerenciamento de drivers.
"""

import os
import time
import json
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

# Configurações globais
GECKODRIVER_PATH = r"C:\geckodriver\geckodriver.exe"
SISB_PROFILE_PC = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
SISB_PROFILE_NOTEBOOK = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'


def criar_driver_PC(headless: bool = False) -> WebDriver:
    """Driver PC - Firefox Developer Edition com configurações otimizadas"""
    options = Options()
    if headless:
        options.add_argument('-headless')

    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    options.set_preference("browser.cache.offline.enable", True)
    options.set_preference("network.http.use-cache", True)
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)  # Não reduzir velocidade de timers em background
    options.set_preference("dom.timeout.throttling_delay", 0)  # Não atrasar execução em abas inativas
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)  # Sem delay de budget
    options.set_preference("page.load.animation.disabled", True)  # Desabilitar animações de carregamento
    options.set_preference("dom.disable_window_move_resize", False)  # Permitir resize mesmo em background

    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    return driver


def criar_driver_VT(headless: bool = False) -> WebDriver:
    """Driver VT - Perfil padrão"""
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    logger.info("[DRIVER_VT] Driver VT criado com sucesso")
    return driver


def criar_driver_notebook(headless: bool = False) -> WebDriver:
    """Driver Notebook - Firefox Developer Edition"""
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

    USE_USER_PROFILE_NOTEBOOK = False
    if USE_USER_PROFILE_NOTEBOOK:
        options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    return driver


def criar_driver_sisb_pc(headless: bool = False) -> Optional[WebDriver]:
    """Driver SISBAJUD - PC (Firefox Developer Edition com configurações robustas)"""
    options = Options()
    if headless:
        options.add_argument('--headless')

    options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"

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

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    try:
        if os.path.exists(SISB_PROFILE_PC):
            profile = FirefoxProfile(SISB_PROFILE_PC)
            options.profile = profile
            logger.info(f"[DRIVER_SISB_PC] Usando perfil: {SISB_PROFILE_PC}")
        else:
            logger.info(f"[DRIVER_SISB_PC] Perfil não encontrado: {SISB_PROFILE_PC}, usando perfil temporário")
    except Exception as e:
        logger.info(f"[DRIVER_SISB_PC] Erro ao carregar perfil: {e}, usando perfil temporário")

    service = Service(executable_path=GECKODRIVER_PATH)

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        logger.info("[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition) criado com sucesso")
        return driver
    except Exception as e:
        logger.info(f"[DRIVER_SISB_PC] Erro ao criar driver: {e}")
        try:
            options_fallback = Options()
            if headless:
                options_fallback.add_argument('--headless')
            options_fallback.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
            driver = webdriver.Firefox(service=service, options=options_fallback)
            driver.implicitly_wait(10)
            logger.info("[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition - fallback) criado com sucesso")
            return driver
        except Exception as e2:
            logger.info(f"[DRIVER_SISB_PC] Falha total ao criar driver: {e2}")
            return None


def criar_driver_sisb_notebook(headless: bool = False) -> WebDriver:
    """Driver SISBAJUD - Notebook"""
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = SISB_PROFILE_NOTEBOOK

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    return driver


def finalizar_driver(driver: WebDriver, log: bool = True) -> bool:
    """Finaliza o driver de forma segura, aguardando operações pendentes"""
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
            logger.info('[DRIVER] Driver finalizado com sucesso')
        return True
    except Exception as e:
        if log:
            logger.info(f'[DRIVER][AVISO] Erro ao finalizar driver: {e}')
        return False


def salvar_cookies_sessao(driver: WebDriver, caminho_arquivo: Optional[str] = None, info_extra: Optional[str] = None) -> bool:
    """Salva todos os cookies da sessão Selenium em um arquivo JSON"""
    try:
        cookies = driver.get_cookies()
        if not cookies:
            return False

        if not caminho_arquivo:
            # Usar a raiz do repositório (duas pastas acima deste arquivo) para
            # garantir que os cookies sejam salvos no diretório do projeto PjePlus
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            pasta = os.path.join(repo_root, 'cookies_sessoes')
            os.makedirs(pasta, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            info = f'_{info_extra}' if info_extra else ''
            caminho_arquivo = os.path.join(pasta, f'cookies_sessao{info}_{timestamp}.json')

        dados_cookies = {
            'timestamp': datetime.datetime.now().isoformat(),
            'url_base': driver.current_url,
            'cookies': cookies
        }

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_cookies, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f'[COOKIES][ERRO] Falha ao salvar cookies: {e}')
        return False


def carregar_cookies_sessao(driver: WebDriver, max_idade_horas: int = 24) -> bool:
    """Carrega cookies de sessão mais recentes e válidos automaticamente"""
    try:
        # Localizar a pasta de cookies na raiz do repositório (garante consistência
        # independentemente do CWD atual ao executar scripts de outros projetos)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        pasta = os.path.join(repo_root, 'cookies_sessoes')
        if not os.path.exists(pasta):
            logger.info('[COOKIES] Pasta de cookies não encontrada.')
            return False

        import glob
        arquivos_cookies = glob.glob(os.path.join(pasta, 'cookies_sessao*.json'))
        if not arquivos_cookies:
            logger.info('[COOKIES] Nenhum arquivo de cookies encontrado.')
            return False

        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)

        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados['cookies']
        else:
            timestamp_str = datetime.datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados

        timestamp_cookies = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.datetime.now() - timestamp_cookies

        if idade > datetime.timedelta(hours=max_idade_horas):
            logger.info(f'[COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h). Pulando.')
            return False

        driver.get('https://pje.trt2.jus.br/primeirograu/')

        cookies_carregados = 0
        for cookie in cookies:
            try:
                cookie_limpo = {k: v for k, v in cookie.items() if k not in ['expiry', 'httpOnly', 'secure', 'sameSite']}
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
            except Exception as e:
                logger.info(f'[COOKIES] Erro ao carregar cookie {cookie.get("name", "unknown")}: {e}')

        logger.info(f'[COOKIES] {cookies_carregados} cookies carregados de {os.path.basename(arquivo_mais_recente)}')

        driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        time.sleep(3)

        # Verificar se login foi bem-sucedido
        try:
            driver.find_element(By.CSS_SELECTOR, '.navbar-brand')  # Elemento que aparece quando logado
            logger.info('[COOKIES] Login via cookies bem-sucedido')
            return True
        except Exception:
            logger.info('[COOKIES] Cookies carregados, mas login pode ter expirado')
            return False

    except Exception as e:
        logger.info(f'[COOKIES] Erro ao carregar cookies: {e}')
        return False


def credencial(tipo_driver: str = 'PC', tipo_login: str = 'CPF', headless: bool = False, cpf: Optional[str] = None, senha: Optional[str] = None, url_login: Optional[str] = None, max_idade_cookies: int = 24) -> Optional[WebDriver]:
    """
    Função unificada para criação de driver + login + gerenciamento de cookies.

    Args:
        tipo_driver (str): 'PC', 'VT', 'notebook', 'sisb_pc', 'sisb_notebook'
        tipo_login (str): 'PC' (certificado) ou 'CPF' (cpf/senha)
        headless (bool): Executar em modo headless
        cpf (str): CPF para login (se tipo_login='CPF')
        senha (str): Senha para login (se tipo_login='CPF')
        url_login (str): URL de login customizada
        max_idade_cookies (int): Idade máxima dos cookies em horas

    Returns:
        driver: Driver configurado e logado, ou None se falhar
    """
    try:
        # 1. CRIAR DRIVER baseado no tipo
        if tipo_driver.upper() == 'PC':
            driver = criar_driver_PC(headless=headless)
        elif tipo_driver.upper() == 'VT':
            driver = criar_driver_VT(headless=headless)
        elif tipo_driver.lower() == 'notebook':
            driver = criar_driver_notebook(headless=headless)
        elif tipo_driver.lower() == 'sisb_pc':
            driver = criar_driver_sisb_pc(headless=headless)
        elif tipo_driver.lower() == 'sisb_notebook':
            driver = criar_driver_sisb_notebook(headless=headless)
        else:
            return None

        if not driver:
            return None

        # 2. CARREGAR COOKIES (sempre ativo)
        cookies_carregados = carregar_cookies_sessao(driver, max_idade_horas=max_idade_cookies)

        if cookies_carregados:
            return driver

        # 3. FAZER LOGIN baseado no tipo
        if tipo_login.upper() == 'PC':
            # Login por certificado
            from Fix.utils import login_pc
            sucesso_login = login_pc(driver)

        elif tipo_login.upper() == 'CPF':
            # Login por CPF/senha
            from Fix.utils import login_cpf

            # Usar valores padrão se não fornecidos
            if not cpf:
                cpf = os.environ.get('PJE_SILAS')
            if not senha:
                senha = os.environ.get('PJE_SENHA')

            sucesso_login = login_cpf(
                driver,
                url_login=url_login,
                cpf=cpf,
                senha=senha,
                aguardar_url_final=True
            )
        else:
            driver.quit()
            return None

        if not sucesso_login:
            driver.quit()
            return None

        # 4. SALVAR COOKIES (sempre ativo)
        try:
            info_extra = f"credencial_{tipo_driver}_{tipo_login}"
            salvar_cookies_sessao(driver, info_extra=info_extra)
        except Exception:
            pass
        return driver

    except Exception:
        if 'driver' in locals():
            try:
                driver.quit()
            except Exception:
                pass
        return None


__all__ = [
    'criar_driver_PC',
    'criar_driver_VT',
    'criar_driver_notebook',
    'criar_driver_sisb_pc',
    'criar_driver_sisb_notebook',
    'finalizar_driver',
    'salvar_cookies_sessao',
    'carregar_cookies_sessao',
    'credencial'
]