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
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente
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
# Flag simples para ativar logs detalhados quando necessário (sem novos arquivos)
DEBUG = os.getenv('PJEPLUS_DEBUG', '0') in ('1', 'true', 'TRUE', 'on', 'ON')

# Modo auditoria de seletores (gera arquivo NDJSON com eventos) - opcional
AUDIT = os.getenv('PJEPLUS_AUDIT', '0') in ('1', 'true', 'TRUE', 'on', 'ON')
AUDIT_FILE = os.getenv('PJEPLUS_AUDIT_FILE', 'selectors_audit.ndjson')

def _audit(event, selector, status, extra=None):
    """Registra evento de auditoria (wait/click) se AUDIT estiver ativo."""
    if not AUDIT:
        return
    try:
        rec = {
            'ts': datetime.datetime.now().isoformat(),
            'event': event,
            'selector': str(selector)[:500],
            'status': status,
        }
        if extra:
            rec.update(extra)
        with open(AUDIT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception:
        pass

# Helpers de log locais (sem arquivos novos)
def _log_info(msg):
    if DEBUG:
        print(msg)

def _log_error(msg):
    print(msg)

# =========================
# 2. FUNÇÕES DE SETUP E INICIALIZAÇÃO
# =========================
# Funções utilitárias gerais, limpeza de temp, helpers genéricos

# Função para limpar arquivos temporários
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
                    if datetime.datetime.now() - file_time > timedelta(days=1):
                        os.remove(filepath)
                        deleted += 1
                except Exception as e:
                    print(f'[AVISO] Não removeu {filepath}: {str(e)}')
        
        print(f'[SELENIUM] Limpeza concluída - {deleted} arquivos removidos')
        return True
    except Exception as e:
        print(f'[ERRO] Falha na limpeza: {str(e)}')
        return False

# Seção: Navegação
# Configurações do navegador
PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"

# Função para configurar e iniciar o navegador
def configurar_navegador():
    # Configura e retorna uma instância do Firefox com as configurações necessárias.
    try:
        options = webdriver.FirefoxOptions()
        options.binary_location = FIREFOX_BINARY
        options.set_preference('profile', PROFILE_PATH)
        service = webdriver.FirefoxService()
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as e:
        print(f'[CONFIG][ERRO] Falha ao configurar navegador: {e}')
        raise

def obter_driver_padronizado(headless=False):
    # Retorna um driver Firefox padronizado para o ambiente TRT2, usando perfil e binário já conhecidos.
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import os

    PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    GECKODRIVER_PATH = r"d:\PjePlus\geckodriver.exe"

    logging.debug(f"Usando o binário do Firefox em: {FIREFOX_BINARY}")
    logging.debug(f"Usando o geckodriver em: {GECKODRIVER_PATH}")
    logging.debug(f"Usando o perfil do Firefox em: {PROFILE_PATH}")

    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)

    service = Service(executable_path=GECKODRIVER_PATH)

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        logging.info("Driver Firefox iniciado com sucesso.")
        return driver
    except Exception as e:
        logging.error(f"Erro ao iniciar o driver Firefox: {e}")
        raise

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

def driver_pc(headless=False):
    """
    Perfil: C:/Users/Silas/AppData/Roaming/Mozilla/Dev
    Executável: C:/Program Files/Firefox Developer Edition/firefox.exe
    """
    return obter_driver_padronizado(headless=headless)

# Função de login automático
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
def salvar_cookies(driver, caminho_arquivo):
    """Salva os cookies do navegador em um arquivo JSON."""
    import json
    try:
        cookies = driver.get_cookies()
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f'[COOKIES] Cookies salvos em {caminho_arquivo}')
    except Exception as e:
        print(f'[COOKIES][ERRO] Falha ao salvar cookies: {e}')

def carregar_cookies(driver, caminho_arquivo, url_base='https://pje.trt2.jus.br'):
    """Carrega cookies de um arquivo JSON e injeta no navegador."""
    import os
    import json
    if not os.path.exists(caminho_arquivo):
        print(f'[COOKIES] Arquivo de cookies não encontrado: {caminho_arquivo}')
        return False
    try:
        driver.get(url_base)  # Necessário para definir domínio
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        for cookie in cookies:
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            driver.add_cookie(cookie)
        print(f'[COOKIES] Cookies carregados de {caminho_arquivo}')
        driver.refresh()
        return True
    except Exception as e:
        print(f'[COOKIES][ERRO] Falha ao carregar cookies: {e}')
        return False

def login_notebook(driver):
    # Realiza login automático no PJe TRT2 para notebooks, simulando digitação humana lenta e navegação por TAB/ENTER.
    try:
        from selenium.webdriver.common.keys import Keys
        import random
        caminho_cookies = 'cookies_pjeplus_notebook.json'
        # Tenta carregar cookies antes de login manual
        if carregar_cookies(driver, caminho_cookies):
            print('[LOGIN][NOTEBOOK] Cookies carregados, tentando acesso sem login manual...')
            time.sleep(2)
            if 'login' not in driver.current_url.lower():
                print('[LOGIN][NOTEBOOK] Login por cookies bem-sucedido.')
                return True
            else:
                print('[LOGIN][NOTEBOOK] Cookies inválidos ou expirados, prosseguindo com login manual.')
        driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
        print('[LOGIN][NOTEBOOK] Página de login carregada.')
        # 1. Clicar no botão SSO PDPJ
        btn_sso = wait(driver, '#btnSsoPdpj', timeout=15)
        if not btn_sso:
            print('[LOGIN][ERRO] Botão SSO PDPJ não encontrado.')
            return False
        btn_sso.click()
        print('[LOGIN][NOTEBOOK] Botão SSO PDPJ clicado.')
        time.sleep(1)
        # 2. Preencher campo usuário simulando digitação humana lenta e imperfeita
        usuario = '35305203813'
        campo_usuario = wait(driver, '#username', timeout=15)
        if not campo_usuario:
            print('[LOGIN][ERRO] Campo de usuário não encontrado.')
            return False
        campo_usuario.click()
        campo_usuario.clear()
        time.sleep(0.4)
        for c in usuario:
            campo_usuario.send_keys(c)
            time.sleep(0.22 + random.uniform(0, 0.09))
        print('[LOGIN][NOTEBOOK] Usuário preenchido (digitação simulada, lenta e imperfeita).')
        time.sleep(0.7 + random.uniform(0, 0.5))
        # 3. Navegar para o campo senha com TAB
        campo_usuario.send_keys(Keys.TAB)
        time.sleep(0.4)
        # 4. Preencher campo senha simulando digitação humana lenta e imperfeita
        senha = 'SpF59866'
        campo_senha = wait(driver, '#password', timeout=15)
        if not campo_senha:
            print('[LOGIN][ERRO] Campo de senha não encontrado.')
            return False
        campo_senha.click()
        campo_senha.clear()
        time.sleep(0.4)
        for c in senha:
            campo_senha.send_keys(c)
            time.sleep(0.22 + random.uniform(0, 0.09))
        print('[LOGIN][NOTEBOOK] Senha preenchida (digitação simulada, lenta e imperfeita).')
        time.sleep(0.7 + random.uniform(0, 0.5))
        # 5. Submeter com TAB+ENTER
        campo_senha.send_keys(Keys.TAB)
        time.sleep(0.2)
        campo_senha.send_keys(Keys.ENTER)
        print('[LOGIN][NOTEBOOK] TAB+Enter pressionados após senha.')
        # 6. Espera aleatória após submissão
        time.sleep(2 + random.uniform(0, 1.5))
        # 7. Fallback: se login falhar, tenta novamente mais devagar
        if checar_acesso_negado(driver):
            print('[LOGIN][NOTEBOOK] Login falhou, tentando novamente com digitação ainda mais lenta.')
            driver.refresh()
            time.sleep(2)
            campo_usuario = wait(driver, '#username', timeout=15)
            if not campo_usuario:
                print('[LOGIN][ERRO] Campo de usuário não encontrado (2ª tentativa).')
                return False
            campo_usuario.click()
            campo_usuario.clear()
            time.sleep(0.7)
            for c in usuario:
                campo_usuario.send_keys(c)
                time.sleep(0.32 + random.uniform(0, 0.13))
            time.sleep(1)
            campo_usuario.send_keys(Keys.TAB)
            time.sleep(0.5)
            campo_senha = wait(driver, '#password', timeout=15)
            if not campo_senha:
                print('[LOGIN][ERRO] Campo de senha não encontrado (2ª tentativa).')
                return False
            campo_senha.click()
            campo_senha.clear()
            time.sleep(0.7)
            for c in senha:
                campo_senha.send_keys(c)
                time.sleep(0.32 + random.uniform(0, 0.13))
            time.sleep(1)
            campo_senha.send_keys(Keys.TAB)
            time.sleep(0.3)
            campo_senha.send_keys(Keys.ENTER)
            print('[LOGIN][NOTEBOOK] TAB+Enter pressionados após senha (2ª tentativa).')
            time.sleep(3 + random.uniform(0, 1.5))
            if checar_acesso_negado(driver):
                print('[LOGIN][ERRO] Login falhou mesmo após 2ª tentativa.')
                return False
        print('[LOGIN][NOTEBOOK] Login realizado com sucesso.')
        return True
    except Exception as e:
        print(f'[LOGIN][ERRO] Falha no login: {e}')
        return False

# Novo login humanizado usando undetected-chromedriver (Chrome)
def login_notebook_humano():
    """
    Login humanizado no PJe TRT2 usando undetected-chromedriver (Chrome),
    simulando digitação, clique, scroll e delays realistas.
    Usa as credenciais já presentes em login_notebook.
    """
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    import time
    import random

    usuario = '35305203813'
    senha = 'SpF59866'

    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1366,768')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')

    def human_type(element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.07, 0.25))

    def human_click(driver, element):
        actions = ActionChains(driver)
        actions.move_to_element(element).pause(random.uniform(0.2, 1.2)).click().perform()

    driver = uc.Chrome(options=options)
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    time.sleep(random.uniform(1.2, 2.5))
    driver.execute_script('window.scrollBy(0, 100)')
    time.sleep(random.uniform(0.7, 1.7))
    try:
        btn_sso = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, 'btnSsoPdpj'))
        )
        human_click(driver, btn_sso)
        time.sleep(random.uniform(1, 2))
        campo_usuario = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'username'))
        )
        human_click(driver, campo_usuario)
        time.sleep(random.uniform(0.3, 0.7))
        human_type(campo_usuario, usuario)
        time.sleep(random.uniform(0.5, 1.2))
        campo_usuario.send_keys(Keys.TAB)
        time.sleep(random.uniform(0.3, 0.7))
        campo_senha = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'password'))
        )
        human_click(driver, campo_senha)
        time.sleep(random.uniform(0.3, 0.7))
        human_type(campo_senha, senha)
        time.sleep(random.uniform(0.5, 1.2))
        campo_senha.send_keys(Keys.ENTER)
        print('[LOGIN][HUMANO] Login submetido com Enter.')
        time.sleep(random.uniform(2, 4))
        # Captcha
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, 'captcha-container'))
            )
            print('Captcha detectado! Resolva manualmente e pressione Enter...')
            input()
        except:
            pass
        # Verifica login
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'dashboard'))
        )
        print('Login realizado com sucesso!')
        return driver
    except Exception as e:
        print(f'[LOGIN][HUMANO][ERRO] {e}')
        driver.save_screenshot('erro_login_humano.png')
        driver.quit()
        return None

def checar_acesso_negado(driver):
    """Verifica se a página atual é de acesso negado e retorna True se for, senão False."""
    url = driver.current_url.lower()
    if 'negado' in url or 'acesso-negado' in url or 'acessonegado' in url:
        print('[LOGIN][ERRO] Página de acesso negado detectada! Reiniciando fluxo de login...')
        return True
    return False

# Função para navegar e esperar carregamento
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

# Aplica o filtro para exibir 100 itens por página no painel global.
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

def filtro_fase(driver):
    # Seleciona as fases 'Execução' e 'Liquidação' no filtro global do painel, igual ao filtro favorito 'Prazo1'.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    try:
        seletor_dropdown = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'
        dropdowns = driver.find_elements(By.CSS_SELECTOR, seletor_dropdown)
        dropdown = None
        for d in dropdowns:
            if d.is_displayed():
                dropdown = d
                break
        if not dropdown:
            print('[FILTRO_FASE][ERRO] Dropdown de fase processual não encontrado.')
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
        dropdown.click()
        time.sleep(0.5)
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        time.sleep(0.2)
        fases = ["Execução", "Liquidação"]
        for fase in fases:
            opcoes = overlay.find_elements(By.XPATH, f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{fase}']")
            for opcao in opcoes:
                if opcao.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                    opcao.click()
                    time.sleep(0.2)
                    break
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        return True
    except Exception as e:
        print(f'[FILTRO_FASE][ERRO] Falha ao aplicar filtro de fase: {e}')
        return False

# Função para processar lista de processos

# =========================
# 3. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

# Função de espera robusta
def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    # Espera até que um elemento esteja visível na página.
    try:
        _t0 = time.time()
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        _audit('wait', selector, 'ok', {'by': str(by), 'ms': int((time.time()-_t0)*1000)})
        return element
    except TimeoutException:
        _audit('wait', selector, 'fail', {'by': str(by)})
        _log_error(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None

# Função de clique seguro
def safe_click(driver, selector_or_element, timeout=10, by=None, log=False):
    # Clicks safely. Accepts selector (string) or element.
    try:
        from selenium.webdriver.common.by import By
        if isinstance(selector_or_element, str):
            element = wait(driver, selector_or_element, timeout, by)
        else:
            element = selector_or_element
        # Fallback for KZ details icon (robust selector)
        if element is None and isinstance(selector_or_element, str) and (
            'Detalhes do Processo' in selector_or_element or 'detalhes do processo' in selector_or_element.lower()
        ):
            try:
                # Try clicking the KZ icon directly
                element = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]')
                driver.execute_script("arguments[0].click();", element)
                if DEBUG:
                    _log_info('[CLICK] Clicked KZ details icon (img.mat-tooltip-trigger)')
                _audit('click', 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]', 'ok')
                return True
            except Exception:
                element = None
            # Try clicking the parent button if img not clickable
            try:
                img = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]')
                button = img.find_element(By.XPATH, './ancestor::button[1]')
                driver.execute_script("arguments[0].click();", button)
                if DEBUG:
                    _log_info('[CLICK] Clicked parent button of KZ details icon')
                _audit('click', 'button(parentOf: img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"])', 'ok')
                return True
            except Exception:
                pass
        if element and element.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            driver.execute_script("arguments[0].click();", element)
            if DEBUG:
                _log_info(f'[CLICK] Clicked: {element.text if hasattr(element, "text") else selector_or_element}')
            _audit('click', selector_or_element, 'ok')
            return True
        return False
    except Exception as e:
        _log_error(f'[CLICK][ERROR] Failed to click: {e}')
        _audit('click', selector_or_element, 'fail', {'error': str(e)[:300]})
        return False

def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5, log=False):
    # Versão 3.1 - Busca robusta com logs detalhados e timeout reduzido
    def buscar_input_associado(elemento):
        try:
            input_associado = elemento.find_element(By.XPATH, 
                './following-sibling::input|./preceding-sibling::input|'
                './ancestor::*[contains(@class,"form-group")]//input|'
                './ancestor::*[contains(@class,"mat-form-field")]//input'
            )
            return input_associado
        except Exception as e:
            if log:
                print(f'[ROBUSTO][DEBUG] Falha ao buscar input associado: {e}')
            return None
    try:
        # Fase 1: Busca direta por inputs editáveis
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE1] Buscando input com texto/atributo: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, 
                    f'input[placeholder*="{texto}"], '
                    f'input[aria-label*="{texto}"], '
                    f'input[name*="{texto}"]'
                )
                for el in elementos:
                    if el.is_displayed() and el.is_enabled():
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Input direto: {el}')
                        return el
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase1: {e}')
                continue
        # Fase 2: Busca hierárquica se não encontrar diretamente
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE2] Buscando por texto visível: {texto}')
            try:
                elementos = driver.find_elements(By.XPATH, 
                    f'//*[contains(text(), "{texto}")]'
                )
                for el in elementos:
                    if DEBUG:
                        _log_info(f'[ROBUSTO][FASE2] Elemento com texto encontrado: {el}')
                    input_assoc = buscar_input_associado(el)
                    if input_assoc:
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Input associado: {input_assoc}')
                        return input_assoc
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase2: {e}')
                continue
        # Fase 3: Busca por ícone/fa
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE3] Buscando ícone/fa: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all')
                for el in elementos:
                    if el.is_displayed():
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Ícone/fa: {el}')
                        return el
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase3: {e}')
                continue
        if DEBUG:
            _log_info('[ROBUSTO][FIM] Nenhum elemento encontrado com os critérios fornecidos.')
        return None
    except Exception as e:
        _log_error(f'[ROBUSTO][ERRO GERAL] {e}')
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

# =========================
# 4. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

# Função para extrair documento
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
## Função para extrair dados do processo
def extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False):
    """
    Extrai dados do processo via API do PJe (TRT2), seguindo a mesma lógica da extensão MaisPje.
    Função completa auto-contida.
    """
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
                print(f'[extrair.py] Erro ao obter ID via API: {e}')
        return None

    def obter_dados_processo_via_api(id_processo, sess, trt_host):
        """Replica a função obterDadosProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                return resp.json()
        except Exception as e:
            if debug:
                print(f'[extrair.py] Erro ao obter dados via API: {e}')
        return None
    
    cookies = get_cookies_dict(driver)
    numero_processo = extrair_numero_processo_url(driver)
    trt_host = extrair_trt_host(driver)
    
    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)
    sess.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Grau-Instancia": "1"  # Adiciona header usado pela extensão
    })
    
    if not numero_processo:
        if debug:
            print('[extrair.py] Não foi possível extrair o número do processo.')
        return {}

    # 1. Obter ID do processo usando o número (como na extensão MaisPje)
    id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
    if not id_processo:
        if debug:
            print('[extrair.py] Não foi possível obter o ID do processo via API.')
        return {}

    # 2. Obter dados completos do processo usando o ID
    dados_processo = obter_dados_processo_via_api(id_processo, sess, trt_host)
    if not dados_processo:
        if debug:
            print('[extrair.py] Não foi possível obter dados do processo via API.')
        return {}
    
    processo_memoria = {
        "numero": [dados_processo.get("numero", numero_processo)], 
        "id": id_processo, 
        "autor": [], 
        "reu": [], 
        "terceiro": [],
        "divida": {}, 
        "justicaGratuita": [], 
        "transito": "", 
        "custas": "", 
        "dtAutuacao": "",
        "classeJudicial": dados_processo.get("classeJudicial", {}),
        "labelFaseProcessual": dados_processo.get("labelFaseProcessual", ""),
        "orgaoJuizo": dados_processo.get("orgaoJuizo", {}),
        "dataUltimo": dados_processo.get("dataUltimo", "")
    }

    # Extrai data de autuação dos dados principais
    dt = dados_processo.get("autuadoEm")
    if dt:
        from datetime import datetime
        try:
            dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except:
            processo_memoria["dtAutuacao"] = dt
    
    # 2. Partes (formato limpo)
    def criar_pessoa_limpa(parte):
        nome = parte.get("nome", "").strip()
        doc = re.sub(r'[^\d]', '', parte.get("documento", ""))
        
        pessoa = {"nome": nome, "cpfcnpj": doc}
        
        reps = parte.get("representantes", [])
        if reps:
            adv = reps[0]
            pessoa["advogado"] = {
                "nome": adv.get("nome", "").strip(),
                "cpf": re.sub(r'[^\d]', '', adv.get("documento", "")),
                "oab": adv.get("numeroOab", "")
            }
        return pessoa
          # 2. Partes usando API separada (como na extensão)
    try:
        url_partes = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes"
        resp = sess.get(url_partes, timeout=10)
        if resp.ok:
            j = resp.json()
            for parte in j.get("ATIVO", []):
                processo_memoria["autor"].append(criar_pessoa_limpa(parte))
            for parte in j.get("PASSIVO", []):
                processo_memoria["reu"].append(criar_pessoa_limpa(parte))
            for parte in j.get("TERCEIROS", []):
                processo_memoria["terceiro"].append({"nome": parte.get("nome", "").strip()})
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar partes:', e)
    
    # 3. Divida
    try:
        url_divida = f"https://{trt_host}/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=false&idProcesso={id_processo}"
        resp = sess.get(url_divida, timeout=10)
        if resp.ok:
            j = resp.json()
            if j and j.get("resultado"):
                # Pega o PRIMEIRO elemento (mais recente)
                mais_recente = j["resultado"][0]
                processo_memoria["divida"] = {
                    "valor": mais_recente.get("total", 0),
                    "data": mais_recente.get("dataLiquidacao", "")
                }
    except Exception as e:
        if debug:
            print('[extrair.py] Erro ao buscar divida:', e)


      # Salva JSON
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)
    return processo_memoria

# =========================
# 5. FUNÇÕES DE MANIPULAÇÃO DE DOCUMENTOS
# =========================

# Seção: Manipulaçao de intimações
# Função para preencher campos de prazo
def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    """Preenche todos os campos de prazo (input[type=text].mat-input-element) dentro do formulário de minuta/comunicação."""
    try:
        # Busca o formulário principal
        form = wait(driver, '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form', timeout)
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

# =========================
# 6. FUNÇÕES DE MANIPULAÇÃO DE PRAZOS E GIGS
# =========================

# Seção: Ferramentas
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def gigs_minuta(driver, dias_uteis, responsavel, observacao, timeout=10, log=True):
    t0 = time.time()
    try:
        if log:
            print(f"[GIGS_MINUTA] Iniciando criação de GIGS Minuta: {dias_uteis}/{responsavel}/{observacao}")

        # Garante sempre o padrão dias/responsavel/observacao
        if not responsavel or responsavel.strip() == '-':
            responsavel = ''
        obs = observacao

        # a - Confirma URL '/minutar'
        if '/minutar' not in driver.current_url:
            if log:
                print('[GIGS_MINUTA][ERRO] URL atual não é /minutar:', driver.current_url)
            return False

        # b - Clique no botão menu lateral
        try:
            btn_menu = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, 'botao-menu'))
            )
            btn_menu.click()
            if log:
                print('[GIGS_MINUTA] Botão menu clicado.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Botão menu não encontrado ou não clicável: {e}')
            return False

        # c - Clique no botão "Abrir o Gigs"
        try:
            btn_gigs_icon = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.icone-descricao .fa-tag'))
            )
            btn_gigs = btn_gigs_icon.find_element(By.XPATH, 'ancestor::button')
            btn_gigs.click()
            if log:
                print('[GIGS_MINUTA] Botão Abrir o Gigs clicado.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Botão Abrir o Gigs não encontrado ou não clicável: {e}')
            return False

        # 2 - Aguarda o modal GIGS abrir
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card[aria-label="Gigs"], #lista-atividades'))
            )
            if log:
                print('[GIGS_MINUTA] Modal de GIGS aberto.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Modal de GIGS não detectado: {e}')
            return False

        # 2a - Clique em Nova Atividade
        try:
            btn_nova_atividade = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, 'nova-atividade'))
            )
            btn_nova_atividade.click()
            if log:
                print('[GIGS_MINUTA] Botão Nova Atividade clicado.')

            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'form'))
            )
            if log:
                print('[GIGS_MINUTA] Modal de Nova Atividade aberto.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Falha ao abrir modal de Nova Atividade: {e}')
            return False

        # 3 - Preenche campos no modal de atividade
        if dias_uteis != 0:
            try:
                campo_dias = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
                )
                campo_dias.clear()
                for c in str(dias_uteis):
                    campo_dias.send_keys(c)
                    time.sleep(0.05)
                if log:
                    print(f'[GIGS_MINUTA] Dias úteis preenchido: {dias_uteis}')
            except Exception as e:
                if log:
                    print(f'[GIGS_MINUTA][AVISO] Campo dias não encontrado ou não preenchido: {e}')

        if responsavel:
            try:
                campo_resp = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]'))
                )
                campo_resp.clear()
                campo_resp.send_keys(responsavel)
                time.sleep(0.2)
                campo_resp.send_keys(Keys.ARROW_DOWN)
                campo_resp.send_keys(Keys.ENTER)
                if log:
                    print(f'[GIGS_MINUTA] Responsável preenchido: {responsavel}')
            except Exception as e:
                if log:
                    print(f'[GIGS_MINUTA][AVISO] Campo responsável não encontrado ou não preenchido: {e}')

        try:
            campo_obs = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
            )
            campo_obs.clear()
            for c in obs:
                campo_obs.send_keys(c)
                time.sleep(0.03)
            if log:
                print(f'[GIGS_MINUTA] Observação preenchida: {obs}')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][AVISO] Campo observação não encontrado ou não preenchido: {e}')

        # 4 - Clica em Salvar
        btn_salvar = None
        botoes = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
        for btn in botoes:
            if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                btn_salvar = btn
                break

        if not btn_salvar:
            if log:
                print('[GIGS_MINUTA][ERRO] Botão Salvar não encontrado!')
            return False

        btn_salvar.click()
        if log:
            print('[GIGS_MINUTA] Botão Salvar clicado.')

        try:
            success_snackbar = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span'))
            )
            if 'salva com sucesso' in success_snackbar.text.lower():
                if log:
                    print('[GIGS_MINUTA] Mensagem de sucesso confirmada.')
                time.sleep(1)
                if log:
                    print('[GIGS_MINUTA] GIGS Minuta criado com sucesso!')
                return True
            else:
                if log:
                    print('[GIGS_MINUTA][AVISO] Snackbar encontrado mas sem mensagem de sucesso.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][AVISO] Não foi possível confirmar mensagem de sucesso: {e}')

        return True

    except Exception as e:
        if log:
            print(f'[GIGS_MINUTA][ERRO] Falha ao criar GIGS Minuta: {e}')
        return False

def criar_comentario(driver, observacao, timeout=10, log=True):
    """
    Cria um novo comentário no processo atual clicando no botão "Novo Comentário".
    
    Args:
        driver: WebDriver do Selenium
        observacao: Texto do comentário a ser criado
        timeout: Timeout para aguardar elementos
        log: Se deve exibir logs detalhados
        
    Returns:
        bool: True se o comentário foi criado com sucesso, False caso contrário
    """
    try:
        if log:
            print(f'[COMENTARIO] Criando novo comentário: "{observacao}"')
        
        # 1. Clicar no botão "Novo Comentário"
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            # Usar o ID do botão como seletor principal
            btn_novo_comentario = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, "novo-comentario"))
            )
            
            if log:
                print('[COMENTARIO] Botão "Novo Comentário" encontrado')
                
            # Clicar no botão
            btn_novo_comentario.click()
            
            if log:
                print('[COMENTARIO] Botão "Novo Comentário" clicado')
                
        except Exception as e:
            if log:
                print(f'[COMENTARIO][ERRO] Botão "Novo Comentário" não encontrado: {e}')
            return False
        
        # 2. Aguardar o modal de comentário abrir
        try:
            # Aguardar o campo de comentário ficar disponível no modal
            campo_comentario = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="comentario"], textarea.mat-input-element'))
            )
            
            if log:
                print('[COMENTARIO] Modal de comentário aberto')
                
        except:
            try:
                # Tentativa alternativa - qualquer textarea no modal
                campo_comentario = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.mat-dialog-content textarea'))
                )
                
                if log:
                    print('[COMENTARIO] Campo de comentário encontrado com seletor alternativo')
                    
            except Exception as e:
                if log:
                    print(f'[COMENTARIO][ERRO] Campo de comentário não encontrado no modal: {e}')
                return False
        
        # 3. Preencher o comentário
        if log:
            print('[COMENTARIO] Preenchendo campo de comentário...')
        
        # Limpar e preencher o campo
        campo_comentario.clear()
        campo_comentario.send_keys(observacao)
        
        if log:
            print(f'[COMENTARIO] Comentário preenchido: "{observacao}"')
        
        # 4. Clicar no botão de enviar comentário no modal
        try:
            # Procurar botão de enviar no modal
            btn_enviar = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.mat-dialog-actions button[type="submit"], .mat-dialog-actions button.mat-raised-button'))
            )
            
            if log:
                print('[COMENTARIO] Botão de envio encontrado')
                
            # Clicar no botão
            btn_enviar.click()
            
            if log:
                print('[COMENTARIO] Botão de envio clicado')
                
        except Exception as e:
            if log:
                print(f'[COMENTARIO][ERRO] Botão de envio não encontrado: {e}')
            return False
        
        # 5. Aguardar confirmação de envio e fechamento do modal
        try:
            # Aguardar o modal fechar (indicando envio concluído)
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, '.mat-dialog-content'))
            )
            
            if log:
                print('[COMENTARIO] ✅ Comentário enviado com sucesso! Modal fechado.')
            return True
            
        except:
            # Verificar se apareceu mensagem de sucesso
            try:
                msg_sucesso = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.success-message, .mat-snack-bar-success'))
                )
                
                if msg_sucesso and log:
                    print('[COMENTARIO] ✅ Comentário enviado com sucesso!')
                return True
                
            except:
                # Se não houver confirmação explícita, considerar sucesso se não houve erro
                if log:
                    print('[COMENTARIO] ✅ Comentário enviado (sem confirmação explícita)')
                return True
        
    except Exception as e:
        if log:
            print(f'[COMENTARIO][ERRO] Falha ao criar comentário: {e}')
        return False
# =========================
# 7. FUNÇÕES DE TRATAMENTO DE DOCUMENTOS ESPECÍFICOS
# =========================

# Seção: Mandados Argos (Pesquisa Patrimonial)
def analise_argos(driver):
    # Fluxo robusto para análise de mandados do tipo Argos (Pesquisa Patrimonial).
    print('[ARGOS] Iniciando análise Argos...')
    try:
        # Placeholder para lógica Argos adicional
        print('[ARGOS] Análise Argos concluída.')
    except Exception as e:
        print(f'[ARGOS][ERRO] Falha na análise Argos: {e}')

def buscar_documento_argos(driver, log=True):
    """Versão robusta do buscador de documentos Argos com melhor tratamento de erros."""
    try:
        # Encontra todos os itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        # Procura primeiro despacho ou decisão
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                # Verifica se é despacho ou decisão
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                # Verifica se é de juiz
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = False
                for mag in mag_icons:
                    aria = mag.get_attribute('aria-label')
                    if 'otavio' in aria or 'mariana' in aria:
                        mag_ok = True
                        break
                if not mag_ok:
                    continue
                # Clica no documento
                link.click()
                time.sleep(1)
                # Extrai o texto
                texto = extrair_documento(driver)
                if not texto:
                    continue
                # Se é decisão, retorna imediatamente
                if 'decisão' in doc_text or 'sentença' in doc_text:
                    safe_click(driver, link)
                    time.sleep(1)
                    texto = extrair_documento(driver)
                    if texto:
                        return (texto, 'decisao')
                    else:
                        if log:
                            print('[ARGOS][ERRO] Não foi possível extrair texto da decisão.')
                        return (None, None)
                # Se é despacho, verifica conteúdo
                if 'EM QUE PESE A AUSÊNCIA' in texto.upper():
                    return (texto, 'despacho')
            except Exception:
                continue
        # Se chegou aqui, não encontrou documento válido
        if log:
            print('[ARGOS] Nenhum documento válido encontrado.')
        return (None, None)
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha ao buscar documento: {e}')
            print('[ARGOS][INFO] Tentando fallback...')
        return (None, None)

def tratar_anexos_argos(driver, log=True):
    # Função placeholder, lógica removida conforme solicitado.
    if log:
        print('[ARGOS][ANEXOS] Tratando anexos...')
    if log:
        print('[ARGOS][ANEXOS] Anexos tratados com sucesso.')

# =========================
# 8. FUNÇÕES DE UI E INTERFACE
# =========================

# Seção: Mandados Outros

def analise_outros(driver):
    # Fluxo robusto para análise de mandados do tipo Outros (Oficial de Justiça).
    # - Extrai certidão do documento.
    # - Cria GIGS sempre como tipo 'prazo', 0 dias, nome 'Pz mdd'.
    print('[OUTROS] Iniciando análise Outros...')
    texto = extrair_documento(driver, regras_analise=lambda texto: criar_gigs(driver, 0, 'Pz mdd', tela='principal'))
    if not texto:
        print("[OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
    print('[OUTROS] Análise Outros concluída.')

def is_browsing_context_discarded_error(error_message):
    """
    Verifica se o erro é do tipo 'Browsing context has been discarded' ou similar.
    Estes erros são fatais e indicam que o driver não pode mais se comunicar com o navegador.
    """
    if not error_message:
        return False
    error_str = str(error_message).lower()
    return ('browsing context has been discarded' in error_str or 
            'no such window' in error_str or 
            'nosuchwindowerror' in error_str or
            'session not created' in error_str or
            'invalid session id' in error_str)

def indexar_processos(driver):
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    processos = []
    for idx, linha in enumerate(linhas):
        try:
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = links[0].text.strip() if links else (linha.find_elements(By.TAG_NAME, 'td')[0].text.strip() if linha.find_elements(By.TAG_NAME, 'td') else '')
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            processos.append((num_proc, linha))
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e}')
    return processos

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
        if not validar_conexao_driver(driver, "ABAS"):
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

def executar_callback(driver, callback, proc_id):
    """
    Executa o callback com tratamento de exceções e verificação de conexão.
    
    Args:
        driver: O driver Selenium
        callback: A função callback a ser executada
        proc_id: O identificador do processo
        
    Returns:
        bool: True se o callback foi bem sucedido, False caso contrário
    """
    if not callback:
        print(f'[PROCESSAR] Nenhum callback definido para {proc_id}, considerando como sucesso')
        return True
          # Verificar se o driver está conectado antes do callback
    try:
        conexao_status = validar_conexao_driver(driver, "CALLBACK")
        if conexao_status == "FATAL":
            print(f'[PROCESSAR][FATAL] Driver inutilizável antes do callback para {proc_id}')
            return False
        elif not conexao_status:
            print(f'[PROCESSAR][ERRO] Driver não está conectado antes do callback para {proc_id}')
            return False
    except Exception:
        print(f'[PROCESSAR][ERRO] Falha ao verificar conexão antes do callback para {proc_id}')
        return False
        
    # Executar o callback com tratamento de exceções
    try:
        # Executar o callback e capturar o retorno se houver
        resultado = callback(driver)
        # Se o callback retornar explicitamente False, respeitamos isso
        if resultado is False:
            print(f'[PROCESSAR][ALERTA] Callback para {proc_id} retornou False explicitamente')
            return False
        # Qualquer outro retorno é considerado sucesso
        return True
    except Exception as e:
        print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}')
        import traceback
        print(f'[PROCESSAR][ERRO] Traceback completo: {traceback.format_exc()}')
        return False

def validar_conexao_driver(driver, contexto="GERAL", proc_id=None):
    import traceback
    try:
        if not hasattr(driver, 'session_id') or driver.session_id is None:
            print(f'[{contexto}][CONEXÃO][ERRO] Driver não possui session_id válido')
            return False
        try:
            # Teste 1: Verificar se podemos acessar current_url
            try:
                current_url = driver.current_url
            except Exception as url_err:
                if is_browsing_context_discarded_error(url_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                    print(f'[{contexto}][CONEXÃO][FATAL] Erro: {url_err}')
                    print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                    if proc_id:
                        print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                    # Log em arquivo
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{url_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                    return "FATAL"  # Retorna "FATAL" para indicar erro irrecuperável
                else:
                    print(f'[{contexto}][CONEXÃO][ERRO] Falha ao acessar URL atual: {url_err}')
                    return False
            # Teste 2: Verificar se podemos acessar window_handles
            try:
                window_handles = driver.window_handles
            except Exception as handles_err:
                if is_browsing_context_discarded_error(handles_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                    print(f'[{contexto}][CONEXÃO][FATAL] Erro: {handles_err}')
                    print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                    if proc_id:
                        print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{handles_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                    return "FATAL"  # Retorna "FATAL" para indicar erro irrecuperável
                else:
                    print(f'[{contexto}][CONEXÃO][ERRO] Falha ao acessar handles: {handles_err}')
                    return False
            # Se ambos os testes passaram, o driver está OK
            print(f'[{contexto}][CONEXÃO][OK] Driver conectado - URL: {current_url[:50]}... | Abas: {len(window_handles)}')
            return True
        except Exception as connection_test_err:
            if is_browsing_context_discarded_error(connection_test_err):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                print(f'[{contexto}][CONEXÃO][FATAL] Erro: {connection_test_err}')
                print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                if proc_id:
                    print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                try:
                    with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{connection_test_err}\n{traceback.format_exc()}\n\n")
                except Exception as logerr:
                    print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                return "FATAL"
            else:
                print(f'[{contexto}][CONEXÃO][ERRO] Falha no teste de conexão: {connection_test_err}')
                return False
    except Exception as validation_err:
        if is_browsing_context_discarded_error(validation_err):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
            print(f'[{contexto}][CONEXÃO][FATAL] Erro: {validation_err}')
            print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
            if proc_id:
                print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
            try:
                with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{validation_err}\n{traceback.format_exc()}\n\n")
            except Exception as logerr:
                print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
            return "FATAL"
        else:
            print(f'[{contexto}][CONEXÃO][ERRO] Falha na validação de conexão: {validation_err}')
            return False

def forcar_fechamento_abas_extras(driver, aba_lista_original):
    """
    Fecha todas as abas extras, com tratamento robusto de erros e reconexão.
    Retorna True se a limpeza foi bem-sucedida, False para erro recuperável, "FATAL" para erro irrecuperável.
    """
    try:
        # Verifica se o driver ainda está conectado
        conexao_status = validar_conexao_driver(driver, "LIMPEZA")
        if conexao_status == "FATAL":
            print('[LIMPEZA][FATAL] Contexto do navegador foi descartado - não é possível limpar abas')
            return "FATAL"
        elif not conexao_status:
            print('[LIMPEZA][ERRO] Conexão perdida - não é possível limpar abas')
            return False
            
        # Etapa 1: Obter lista de abas de forma segura
        try:
            abas_atuais = driver.window_handles
            print(f'[LIMPEZA] Abas detectadas: {len(abas_atuais)}')
        except Exception as e:
            print(f'[LIMPEZA][ERRO] Falha ao obter lista de abas: {e}')
            return False
            
        # Verifica se a aba original ainda existe
        if aba_lista_original not in abas_atuais:
            print('[LIMPEZA][ERRO] Aba original não encontrada entre as abas disponíveis!')
            # Se tiver pelo menos uma aba, continua com ela
            if len(abas_atuais) > 0:
                print('[LIMPEZA][RECUPERAÇÃO] Usando primeira aba disponível como nova aba principal')
                driver.switch_to.window(abas_atuais[0])
                return True
            else:
                return False
            
        # Etapa 2: Fechar abas extras com tratamento de exceções
        for aba in list(abas_atuais):  # Cria uma cópia da lista para evitar modificação durante iteração
            if aba != aba_lista_original:
                for tentativa in range(3):  # Tenta até 3 vezes para cada aba
                    try:
                        driver.switch_to.window(aba)
                        driver.close()
                        print(f'[LIMPEZA] Aba fechada: {aba}')
                        break  # Sai do loop de tentativas se conseguiu fechar
                    except Exception as e:
                        print(f'[LIMPEZA][WARN] Tentativa {tentativa+1}/3 - Erro ao fechar aba {aba}: {e}')
                        if tentativa == 2:  # Na última tentativa
                            print(f'[LIMPEZA][WARN] Não foi possível fechar a aba {aba} após 3 tentativas')
        
        # Etapa 3: Verificar novamente as abas e voltar para a original
        try:
            abas_atuais = driver.window_handles
        except Exception:
            print('[LIMPEZA][ERRO] Falha ao verificar abas após limpeza')
            return False
            
        if aba_lista_original in abas_atuais:
            try:
                driver.switch_to.window(aba_lista_original)
                print('[LIMPEZA] Retornou para aba da lista')
                return True
            except Exception as e:
                print(f'[LIMPEZA][ERRO] Não foi possível voltar para aba original: {e}')
                return False
        else:
            print('[LIMPEZA][ERRO] Aba da lista original não está mais disponível!')
            # Se tiver pelo menos uma aba, continua com ela
            if len(abas_atuais) > 0:
                print('[LIMPEZA][RECUPERAÇÃO] Usando primeira aba disponível como nova aba principal')
                driver.switch_to.window(abas_atuais[0])
                return True
            else:
                return False
    except Exception as e:
        print(f'[LIMPEZA][ERRO] Falha na limpeza de abas: {e}')
        return False

def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    """
    Função principal para processar uma lista de processos, com tratamento robusto 
    para questões de conexão, abas e manipulação do driver.
    """
    import time  # Adicionando import explícito do time
    
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
      # Verificar conexão inicial
    conexao_inicial = validar_conexao_driver(driver, "FLUXO")
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
        conexao_status = validar_conexao_driver(driver, "PROCESSAR")
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
                novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
                if novo_driver:
                    driver = novo_driver
                    # atualizar aba_lista_original se necessário
                    try:
                        aba_lista_original = driver.window_handles[0]
                    except Exception:
                        pass
                    print('[PROCESSAR] ✅ Driver reiniciado e logado. Re-tentando o processo atual.')
                else:
                    print('[PROCESSAR][ERRO] Falha ao reiniciar driver após acesso negado')
                    processos_com_erro += 1
                    continue

            if "escaninho" not in atual_url and "documentos" not in atual_url:
                print(f'[PROCESSAR][ALERTA] Não estamos na página da lista! URL: {atual_url[:50]}...')
                # Tentar navegar de volta se possível
                try:
                    if aba_lista_original in driver.window_handles:
                        driver.switch_to.window(aba_lista_original)
                        print('[PROCESSAR] Voltamos para a aba da lista')
                    else:
                        print('[PROCESSAR][ERRO] Aba da lista não está mais disponível')
                        processos_com_erro += 1
                        continue
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Falha ao tentar voltar para a aba da lista: {e}')
                    processos_com_erro += 1
                    continue
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha ao verificar URL atual: {e}')
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
            
        # Abre detalhes
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
            print(f'[PROCESSAR][ERRO] Nova aba do processo {proc_id} não foi aberta após 3 tentativas.')
            processos_com_erro += 1
            continue
            
        # Verificar se a página carregou corretamente
        try:
            # Aguardar carregamento mínimo da página
            time.sleep(1)
            page_title = driver.title
            current_url = driver.current_url
            print(f'[PROCESSAR] Nova aba carregada: {page_title} | URL: {current_url[:50]}...')
        except Exception as e:
            print(f'[PROCESSAR][ALERTA] Não foi possível verificar carregamento da nova aba: {e}')
            # Continua mesmo assim, o callback pode lidar com isso
              # Executa callback com tratamento adicional
        try:
            if executar_callback(driver, callback, proc_id):
                processos_processados += 1
                print(f'[PROCESSAR] Callback executado com sucesso para {proc_id}')
                  # Verificar conexão imediatamente após o callback para detectar se o crash aconteceu durante o processamento
                conexao_pos_callback = validar_conexao_driver(driver, "POS-CALLBACK")
                if conexao_pos_callback == "FATAL":
                    print(f'[PROCESSAR][FATAL] Contexto do navegador foi descartado durante processamento de {proc_id}')
                    print(f'[PROCESSAR][FATAL] Interrompendo processamento. Processos restantes: {len(processos) - idx - 1}')
                    interrompido_por_fatal = True
                    break  # Para o loop imediatamente
                elif not conexao_pos_callback:
                    print(f'[PROCESSAR][ALERTA] Conexão instável após processamento de {proc_id}')
                    # Continua, mas registra o alerta
            else:
                print(f'[PROCESSAR][ERRO] Callback retornou False para {proc_id}')
                processos_com_erro += 1
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha inesperada ao executar callback: {e}')
            processos_com_erro += 1
            
        # Limpar abas extras APÓS o callback para permitir que funções como carta() abram abas programaticamente
        limpeza_status = forcar_fechamento_abas_extras(driver, aba_lista_original)
        if limpeza_status == "FATAL":
            print(f'[PROCESSAR][FATAL] Contexto do navegador foi descartado durante limpeza pós-callback.')
            print(f'[PROCESSAR][FATAL] Interrompendo processamento.')
            interrompido_por_fatal = True
            break
        elif not limpeza_status:
            print(f'[PROCESSAR][ALERTA] Não foi possível limpar abas após processar {proc_id}')
            # Continua mesmo assim - não é erro fatal
              # Relatório final
    relatorio_final(processos, processos_processados, processos_com_erro, interrompido_por_fatal)
    return processos_processados > 0

def relatorio_final(processos, processados, erros, interrompido_por_fatal=False):
    print(f'[FLUXO] Processamento concluído!')
    if interrompido_por_fatal:
        print(f'[FLUXO][FATAL] ⚠️  Processamento INTERROMPIDO devido a erro fatal do driver!')
        print(f'[FLUXO][FATAL] ⚠️  O contexto do navegador foi descartado (driver inutilizável)')
    print(f'[FLUXO] Processos processados com sucesso: {processados}')
    print(f'[FLUXO] Processos com erro: {erros}')
    print(f'[FLUXO] Total de processos: {len(processos)}')
    if interrompido_por_fatal:
        processos_nao_processados = len(processos) - processados - erros
        if processos_nao_processados > 0:
            print(f'[FLUXO][FATAL] Processos não processados devido ao erro fatal: {processos_nao_processados}')
def extrair_xs_atividades(driver, log=False):
    # Extrai todas as descrições de atividades que contenham 'xs' diretamente da tabela de atividades do GIGS.
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr')
        resultados = []
        for linha in linhas:
            try:
                # Assume que a descrição está na segunda coluna (índice 1)
                coluna_descricao = linha.find_elements(By.CSS_SELECTOR, 'td')[1]
                texto = coluna_descricao.text
                if 'xs' in texto.lower():
                    if log: print(f'[XSACT] "xs" encontrado: {texto}')
                    resultados.append(texto)
            except IndexError:
                if log: print('[XSACT] Linha sem colunas suficientes.')
            except Exception as inner_e:
                if log: print(f'[XSACT][ERRO INTERNO] {inner_e}')
        if not resultados:
            if log: print('[XSACT] Nenhum "xs" encontrado nas descrições.')
            return None
        return resultados
    except Exception as e:
        if log: print(f'[XSACT][ERRO] Falha ao extrair xs: {e}')
        return None


def esperar_colecao(driver, seletor, qtde_minima=1, timeout=10, log=True):
    # Espera até que uma coleção de elementos esteja presente e tenha pelo menos qtde_minima itens.
    try:
        def check_collection(d):
            elementos = d.find_elements(By.CSS_SELECTOR, seletor)
            return elementos if len(elementos) >= qtde_minima else False

        elementos = WebDriverWait(driver, timeout).until(check_collection)
        if log:
            print(f'[COLECAO] Encontrados {len(elementos)} elementos para {seletor}')
        return elementos
    except Exception as e:
        if log:
            print(f'[COLECAO][ERRO] Timeout esperando {seletor}: {e}')
        return []

# =========================
# 9. CLASSES UTILITÁRIAS
# =========================

# =========================
# 10. FUNÇÕES AUXILIARES E UTILITÁRIOS
# =========================
################# O ASSISTENTE COPILOYT NAO DEVE LER OU ANALISAR NADA ABAIXO DESTA LINHA, A NAO SER QUE SEJA EXPLICITAMENTE PEDIDO. MUITO MENOS, SUGERIR DELEÇÕES ABAIXO DWESSSA LINHA QUE NAO FAZEM PARTE DO ESCOPO DO PROMPT EXPLICITAMENTE.###################
# =========================
# 2. FUNÇÕES DE INTERAÇÃO PJe (Movidas/Adaptadas)
# =========================

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Seleciona '100' no filtro de itens por página do painel global.
def filtro_fase(driver):
    # Seleciona as fases 'Execução' e 'Liquidação' no filtro global do painel, igual ao filtro favorito 'Prazo1'.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    try:
        seletor_dropdown = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'
        dropdowns = driver.find_elements(By.CSS_SELECTOR, seletor_dropdown)
        dropdown = None
        for d in dropdowns:
            if d.is_displayed():
                dropdown = d
                break
        if not dropdown:
            print('[FILTRO_FASE][ERRO] Dropdown de fase processual não encontrado.')
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
        dropdown.click()
        time.sleep(0.5)
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        time.sleep(0.2)
        fases = ["Execução", "Liquidação"]
        for fase in fases:
            opcoes = overlay.find_elements(By.XPATH, f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{fase}']")
            for opcao in opcoes:
                if opcao.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                    opcao.click()
                    time.sleep(0.2)
                    break
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        return True
    except Exception as e:
        print(f'[FILTRO_FASE][ERRO] Falha ao aplicar filtro de fase: {e}')
        return False

# Função para processar lista de processos

# =========================
# 3. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

# Função de espera robusta
def sleep(ms):
    """
    Função que implementa pausa em milissegundos, similar ao sleep do JavaScript
    
    Args:
        ms: Tempo de pausa em milissegundos
    
    Returns:
        None
    """
    time.sleep(ms / 1000)

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
        WebElement if found, None otherwise
    """
    if by is None:
        by = By.CSS_SELECTOR
        
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        
        # Verifica se o elemento está habilitado, similar ao gigs-plugin.js
        disabled = getattr(element, 'disabled', False)
        if disabled:
            print(f"[WAIT] Elemento encontrado, mas está desabilitado: {selector}")
            return None
            
        return element
    except (TimeoutException, NoSuchElementException):
        if isinstance(selector, str):
            print(f"[WAIT] Elemento não encontrado: {selector}")
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

def safe_click(driver, selector_or_element, timeout=10, by=None, log=True, retry_count=3):
    """
    Clicks safely on an element with multiple fallback mechanisms.
    Versão robusta baseando-se nas práticas do gigs-plugin.js
    
    Args:
        driver: Selenium WebDriver instance
        selector_or_element: CSS selector (string) or WebElement
        timeout: Maximum time to wait in seconds
        by: Selector type (By.CSS_SELECTOR by default)
        log: Whether to log actions
        retry_count: Number of attempts before giving up
    
    Returns:
        True if successful, False otherwise
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
                
            # Estratégia 4: JavaScript mais avançado
            try:
                if log:
                    print(f"[SAFE_CLICK] Tentando click via JavaScript avançado")
                script = """
                    var element = arguments[0];
                    var e = document.createEvent('MouseEvents');
                    e.initEvent('mousedown', true, true);
                    element.dispatchEvent(e);
                    e.initEvent('mouseup', true, true);
                    element.dispatchEvent(e);
                    e.initEvent('click', true, true);
                    element.dispatchEvent(e);
                    return true;
                """
                driver.execute_script(script, element)
                if log:
                    print(f"[SAFE_CLICK] Click via JavaScript avançado bem sucedido!")
                return True
            except Exception as e:
                if log:
                    print(f"[SAFE_CLICK] Click via JavaScript avançado falhou: {str(e)}")
                
            # Espera um pouco mais entre tentativas
            sleep(500)
        
        if log:
            print(f"[SAFE_CLICK] Todas as tentativas de click falharam após {retry_count} tentativas")
        return False
        
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Erro geral: {str(e)}")
        return False


# Classe responsável por gerenciar a juntada automática de anexos.
class JuntadaAutomatica:
    def __init__(self, driver):
        self.driver = driver

    def executar_juntada(self, configuracao):
        # Get 'tipo' from configuracao dictionary
        tipo = configuracao.get('tipo', '') # Add default value if needed
        if not tipo:
             print("[JUNTADA][ERRO] 'tipo' não encontrado na configuração.")
             return # Or handle the error appropriately

        self.preencher_campo('input[aria-label*="Tipo de Documento"]', tipo) # Use the retrieved tipo

        # Preenche a descrição
        descricao = configuracao.get('descricao', '')
        if descricao:
            self.preencher_campo('input[aria-label="Descrição"]', descricao)

        # Configura sigilo
        sigilo = configuracao.get('sigilo', 'nao').lower()
        if 'sim' in sigilo:
            self.clicar_elemento('input[name="sigiloso"]')
            print("[JUNTADA] Sigilo aplicado.")

        # Escolhe o modelo
        modelo = configuracao.get('modelo', '')
        if modelo:
            self.selecionar_modelo(modelo)

        # Realiza a juntada
        self.clicar_elemento('button[aria-label="Salvar"]')
        print("[JUNTADA] Documento salvo com sucesso.")

        # Assina o documento, se necessário
        if configuracao.get('assinar', 'nao').lower() == 'sim':
            self.clicar_elemento('button[aria-label="Assinar documento e juntar ao processo"]')
            print("[JUNTADA] Documento assinado com sucesso.")

    def preencher_campo(self, seletor, valor):
        # Preenche um campo de entrada com o valor fornecido.
        # Args:
        # seletor (str): Seletor CSS do campo.
        # valor (str): Valor a ser preenchido.
        campo = self.driver.find_element(By.CSS_SELECTOR, seletor)
        campo.clear()
        campo.send_keys(valor)

    def clicar_elemento(self, seletor):
        # Clica em um elemento identificado pelo seletor CSS.
        # Args:
        # seletor (str): Seletor CSS do elemento.
        elemento = self.driver.find_element(By.CSS_SELECTOR, seletor)
        elemento.click()

    def selecionar_modelo(self, modelo):
        # Seleciona um modelo de documento.
        # Args:
        # modelo (str): Nome do modelo a ser selecionado.
        print(f"[JUNTADA] Selecionando modelo: {modelo}")
        # Implementar lógica para selecionar o modelo

# Exemplo de template para configuração de juntada automática
# Cria um template de configuração para juntada automática de anexos.
def criar_template_juntada():
    return {
        "nm_botao": "Nome do Botão",
        "tipo": "Certidão",
        "descricao": "Descrição do Documento",
        "sigilo": "nao",
        "modelo": "",
        "assinar": "nao",
        "vinculo": "Nenhum",
        "visibilidade": "sim"
    }

def clicar_em_elemento_com_texto(driver, texto, tag='*'):
    # Clica em um elemento visível que contém o texto especificado.
    xpath = f"//{tag}[contains(normalize-space(.), '{texto}') and not(ancestor::*[contains(@style, 'display: none')]) and not(ancestor::*[contains(@hidden, 'true')]) ]"
    try:
        elemento = esperar_elemento(driver, (By.XPATH, xpath), timeout=5) # Usar tupla para By
        if elemento:
            safe_click(driver, elemento)
            return True
        else:
            print(f'[ERRO] Elemento com texto "{texto}" não encontrado ou não clicável.')
            return False
    except Exception as e:
        print(f'[ERRO] Ao clicar em elemento com texto "{texto}": {e}')
        return False

def selecionar_destinatario_por_nome(driver, nome_parcial):
    # Seleciona o primeiro destinatário cujo nome contenha nome_parcial.
    try:
        # Espera a lista de destinatários carregar
        wait = WebDriverWait(driver, 10)
        destinatarios_options = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-list-option'))) # Usar tupla para By

        juizo_option = None
        juizo_selecionado = False

        for option in destinatarios_options:
            if 'juízo' in option.text.lower():
                juizo_option = option
                if option.get_attribute('aria-selected') == 'true':
                    juizo_selecionado = True
                break # Encontrou 'Juízo', pode parar

        if juizo_option:
            if not juizo_selecionado:
                print('[DEST JUÍZO] Destinatário "Juízo" encontrado, mas não selecionado. Selecionando...')
                safe_click(driver, juizo_option)
                # Confirma se foi selecionado
                time.sleep(0.5) # Pequena pausa para garantir atualização do DOM
                if juizo_option.get_attribute('aria-selected') == 'true':
                    print('[DEST JUÍZO] Destinatário "Juízo" selecionado com sucesso.')
                    return True
                else:
                    print('[DEST JUÍZO][ERRO] Falha ao selecionar "Juízo" após clique.')
                    return False
            else:
                print('[DEST JUÍZO] Destinatário "Juízo" já está selecionado.')
                return True
        else:
            print('[DEST JUÍZO][AVISO] Destinatário "Juízo" não encontrado na lista.')
            return False # Ou True dependendo se a ausência é um erro ou não

    except TimeoutException:
        print('[DEST JUÍZO][ERRO] Lista de destinatários não encontrada ou não carregou a tempo.')
        return False
    except Exception as e:
        print(f'[DEST JUÍZO][ERRO] Falha ao verificar/selecionar destinatário Juízo: {e}')
        return False

def verificar_documento_decisao_sentenca(driver):
    """Verifica se existe um documento com 'decisão' ou 'sentença' no nome."""
    try:
        seletor_nomes_docs = 'pje-arvore-documento .node-content-wrapper span'
        nomes_docs = driver.find_elements(By.CSS_SELECTOR, seletor_nomes_docs)

        for nome_element in nomes_docs:
            doc_text = nome_element.text.lower()
            if 'decisão' in doc_text or 'sentença' in doc_text:
                print(f'[DOC CHECK] Documento encontrado: "{doc_text}"')
                return True

        print('[DOC CHECK] Nenhum documento de decisão/sentença encontrado.')
        return False
    except Exception as e:
        print(f'[DOC CHECK][ERRO] Falha ao verificar documentos: {e}')
        return False

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

def criar_botoes_detalhes(driver):
    """
    Cria botões com ícones e ações específicas, replicando a funcionalidade do MaisPje, usando o driver já autenticado.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        base_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pjextension_bt_detalhes_base"))
        )
    except:
        base_element = driver.find_element(By.TAG_NAME, "body")

    # Cria o container se não existir
    if not driver.find_elements(By.ID, "pjextension_bt_detalhes_base"):
        container = driver.execute_script(
            "var div = document.createElement('div');"
            "div.id = 'pjextension_bt_detalhes_base';"
            "div.style = 'float: left';"
            "div.setAttribute('role', 'toolbar');"
            "document.body.appendChild(div);"
            "return div;"
        )
    else:
        container = driver.find_element(By.ID, "pjextension_bt_detalhes_base")

    # Configuração dos botões
    buttons = [
        {"title": "Abrir o Gigs", "icon": "fa fa-tag", "action": "abrir_gigs"},
        {"title": "Expedientes", "icon": "fa fa-envelope", "action": "acao_botao_detalhes('Expedientes')"},
        {"title": "Lembretes", "icon": "fas fa-thumbtack", "action": "acao_botao_detalhes('Lembretes')"},
    ]

    for button in buttons:
        driver.execute_script(
            f"var a = document.createElement('a');"
            f"a.title = '{button['title']}';"
            f"a.style = 'cursor: pointer; position: relative; vertical-align: middle; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;';"
            f"a.onmouseover = function() {{ a.style.opacity = 0.5; }};"
            f"a.onmouseleave = function() {{ a.style.opacity = 1; }};"
            f"var i = document.createElement('i');"
            f"i.className = '{button['icon']}';"
            f"a.appendChild(i);"
            f"a.onclick = function() {{ {button['action']} }};"
            f"document.getElementById('pjextension_bt_detalhes_base').appendChild(a);"
        )
    driver.execute_script(
        "setTimeout(function() {"
        "  var div = document.getElementById('pjextension_bt_detalhes_base');"
        "  if (div) { div.style.display='none'; div.offsetHeight; div.style.display=''; }"
        "}, 100);"
    )

# =========================
# 11. FUNÇÕES DE BUSCA E PESQUISA
# =========================

def buscar_ultimo_mandado(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Retorna o texto do documento e seu tipo, ou None se não encontrado.
    """
    try:
        # Espera a timeline carregar
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                print('[MANDADO] Nenhum item encontrado na timeline.')
            return None, None

        # Procura pelo último documento do tipo 'mandado'
        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()

                # Verifica se é do tipo 'mandado'
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)

                    # Extrai o texto do documento
                    texto = item.text
                    if log:
                        print(f'[MANDADO] Documento encontrado: {doc_text}')
                    return texto, 'mandado'

            except Exception as e:
                if log:
                    print(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue

        if log:
            print('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None, None

    except Exception as e:
        if log:
            print(f'[MANDADO][ERRO] Falha geral: {e}')
        return None, None

def buscar_mandado_autor(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Após localizar, busca o ícone de martelo (gavel) e registra o autor: 'SILAS PASSOS' ou outro.
    Retorna um dicionário com texto, tipo e autor, ou None se não encontrado.
    """
    try:
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                print('[MANDADO] Nenhum item encontrado na timeline.')
            return None

        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)
                    texto = item.text
                    autor = 'DESCONHECIDO'
                    # Busca o ícone de martelo (gavel) e extrai o nome do autor
                    try:
                        gavel_icon = item.find_element(By.CSS_SELECTOR, 'i.fa-gavel, i.fas.fa-gavel')
                        # O nome do autor pode estar em um elemento próximo ao ícone
                        parent = gavel_icon.find_element(By.XPATH, './ancestor::*[1]')
                        autor_text = parent.text.strip().upper()
                        if 'SILAS PASSOS' in autor_text:
                            autor = 'SILAS PASSOS'
                        else:
                            autor = autor_text
                        if log:
                            print(f'[MANDADO] Autor identificado: {autor}')
                    except Exception:
                        if log:
                            print('[MANDADO] Ícone gavel ou autor não localizado.')
                    if log:
                        print(f'[MANDADO] Documento encontrado: {doc_text}')
                    return {'texto': texto, 'tipo': 'mandado', 'autor': autor}
            except Exception as e:
                if log:
                    print(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue
        if log:
            print('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None
    except Exception as e:
        if log:
            print(f'[MANDADO][ERRO] Falha geral: {e}')
        return None

# =========================
# 12. FUNÇÕES DE PROCESSAMENTO DE MINUTAS
# =========================

# =========================
# 13. FUNÇÕES DE GESTÃO DE COOKIES E SESSÃO
# =========================

# =========================
# 14. FUNÇÕES DE TRATAMENTO DE ERROS
# =========================

# =========================
# 15. FUNÇÕES DE VALIDAÇÃO E VERIFICAÇÃO
# =========================

# =========================
# 16. FUNÇÕES DE AUTOMAÇÃO DE INTERFACE
# =========================

# =========================
# 17. FUNÇÕES DE TRATAMENTO DE MODELOS
# =========================

# =========================
# 18. FUNÇÕES DE PROCESSAMENTO DE DOCUMENTOS
# =========================

# =========================
# 19. FUNÇÕES DE LOGGING E DEPURAÇÃO
# =========================

# =========================
# 20. FUNÇÕES DE INTEGRAÇÃO COM APIS
# =========================

def colar_conteudo(driver, termo, valor, seletor_paragrafo='p.corpo', seletor_editor='div.area-conteudo.ck-editor__editable'):
    js = f'''
    var alterou = false, msg = '';
    var editorDiv = document.querySelector('{seletor_editor}');
    var editor = null;
    if (editorDiv && editorDiv.ckeditorInstance) {{
        editor = editorDiv.ckeditorInstance;
    }} else if (window.editor) {{
        editor = window.editor;
    }} else if (window.CKEDITOR && window.CKEDITOR.instances) {{
        var keys = Object.keys(window.CKEDITOR.instances);
        if (keys.length > 0) editor = window.CKEDITOR.instances[keys[0]];
    }}
    if (editor && editor.getData && editor.setData) {{
        var log_antes = editor.getData();
        var reMark = new RegExp('<mark[^>]*>\\\\s*' + {repr(termo)} + '\\\\s*<\\\\/mark>', 'i');
        var novo = log_antes;
        if (reMark.test(novo)) {{
            novo = novo.replace(reMark, {repr(valor)});
            editor.setData(novo);
            alterou = (log_antes !== editor.getData());
            msg = alterou ? '[FIX][OK] Substituição realizada.' : '[FIX][ERRO] Substituição não ocorreu.';        }} else {{
            msg = '[FIX][ERRO] <mark>' + {repr(termo)} + '</mark> não encontrado.';
        }}
    }} else {{
        msg = '[FIX][ERRO] Instância do CKEditor não encontrada.';
    }}
    return {{alterou: alterou, msg: msg}};
    '''
    resultado = driver.execute_script(js)
    if resultado and resultado.get('msg'):
        print(resultado['msg'])
    if not resultado or not resultado.get('alterou'):
        raise Exception('[FIX][ERRO] Substituição não realizada no editor.')
    try:
        area = driver.find_element(By.CSS_SELECTOR, seletor_editor)
        area.click()
        area.send_keys(Keys.TAB)
    except Exception:
        pass

def extrair_documento_silencioso(driver, timeout=15, log=True):
    """
    Extrai texto do documento de forma silenciosa, sem logs excessivos.
    Retorna o texto extraído ou None se falhar.
    """
    try:
        # Espera o botão HTML
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            if log: print('[EXTRAI_SIL][ERRO] Botão HTML não encontrado.')
            return None

        # Clica no botão HTML
        safe_click(driver, btn_html)
        time.sleep(1)

        # Extrai o texto do preview
        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            if log: print('[EXTRAI_SIL][ERRO] Preview do documento não encontrado.')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return None

        texto_completo = preview.text

        # Fecha o modal
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except Exception:
            pass

        if not texto_completo:
            if log: print('[EXTRAI_SIL][ERRO] Texto do preview vazio.')
            return None

        return texto_completo.strip()

    except Exception as e:
        if log: print(f'[EXTRAI_SIL][ERRO] Falha ao extrair documento: {e}')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return None

def buscar_documentos_sequenciais(driver):
    """
    Busca documentos sequenciais na árvore e os seleciona.
    """
    try:
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
                # Tenta encontrar o checkbox associado ao nó de texto e clicar
                # A estrutura exata para encontrar o checkbox a partir do span pode variar
                try:
                    # Exemplo: Tenta encontrar um mat-checkbox como irmão ou pai próximo
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
                    print(f'[DOC SEQ][WARN] Erro ao selecionar checkboxes: {e}')

        return selecionou_algum

    except Exception as e:
        print(f'[DOC SEQ][ERRO] Falha ao buscar documentos sequenciais: {e}')
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
    except TimeoutException:
        print(f'[URL][ERRO] Timeout esperando URL conter: "{substring}". URL atual: {driver.current_url}')
        return False
    except Exception as e:
        print(f'[URL][ERRO] Erro ao esperar URL: {e}')
        return False
def BNDT_apagar(driver):
    """
    Executa a rotina de exclusão BNDT conforme instruções:
    - Sempre parte da tela /detalhes
    - Navega para BNDT em nova aba
    - Seleciona Exclusão, Selecionar todos, Gravar
    - Confirma exclusão se dialog de decisão não encontrada aparecer
    """
    # 1. Garante que está em /detalhes
    if '/detalhes' not in driver.current_url:
        raise Exception('BNDT_apagar deve ser executado a partir de /detalhes')

    # 2. Clica no menu fa-bars
    btn_menu = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa-bars.icone-botao-menu'))
    )
    btn_menu.click()
    time.sleep(0.5)

    # 3. Clica no ícone BNDT (fa-money-check-alt)
    btn_bndt = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-money-check-alt.icone-padrao'))
    )
    btn_bndt.click()
    time.sleep(1)

    # 4. Troca para nova aba BNDT
    main_window = driver.current_window_handle
    all_windows = driver.window_handles
    nova_aba = [w for w in all_windows if w != main_window][-1]
    driver.switch_to.window(nova_aba)
    WebDriverWait(driver, 10).until(lambda d: '/BNDT' in d.current_url)
    time.sleep(1)

    # 5. Seleciona opção Exclusão
    radio_exclusao = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(@class,'mat-radio-label-content')][.//text()[contains(.,'Exclusão')]]"))
    )
    radio_exclusao.click()
    time.sleep(0.5)

    # 6. Clica em Selecionar todos
    chk_todos = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(@class,'mat-checkbox-label')][.//text()[contains(.,'Selecionar todos')]]"))
    )
    chk_todos.click()
    time.sleep(0.5)

    # 7. Clica em Gravar
    btn_gravar = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"))
    )
    btn_gravar.click()
    time.sleep(1)

    # 8. Se aparecer dialog de decisão não encontrada, confirma exclusão
    try:
        dialog = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.XPATH, "//mat-dialog-container[contains(@class,'mat-dialog-container')]//h2[contains(text(),'Decisão não encontrada')]/../../.."))
        )
        btn_sim = dialog.find_element(By.XPATH, ".//button[.//span[contains(text(),'Sim')]]")
        btn_sim.click()
        time.sleep(1)
    except Exception:
        pass  # Dialog pode não aparecer, segue normal

    # 9. Sempre tenta clicar no botão 'Sim' (confirmação final)
    try:
        btn_sim_final = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(),'Sim') and contains(@class,'mat-button-wrapper')]]"))
        )
        btn_sim_final.click()
        time.sleep(1)
    except Exception:
        pass  # Botão pode não aparecer, segue normal

    # Foco permanece na aba BNDT
    return True
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



