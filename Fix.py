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
import re
import time
import datetime
import pyperclip
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys

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
import pyperclip
import logging

# Configuração de logs
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelvelname)s - %(message)s')  # Desativado DEBUG, agora só WARNING ou superior

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
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        print(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None

# Função de clique seguro
def safe_click(driver, selector_or_element, timeout=10, by=None, log=True):
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
                if log:
                    print('[CLICK] Clicked KZ details icon (img.mat-tooltip-trigger)')
                return True
            except Exception:
                element = None
            # Try clicking the parent button if img not clickable
            try:
                img = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]')
                button = img.find_element(By.XPATH, './ancestor::button[1]')
                driver.execute_script("arguments[0].click();", button)
                if log:
                    print('[CLICK] Clicked parent button of KZ details icon')
                return True
            except Exception:
                pass
        if element and element.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            driver.execute_script("arguments[0].click();", element)
            if log:
                print(f'[CLICK] Clicked: {element.text if hasattr(element, "text") else selector_or_element}')
            return True
        return False
    except Exception as e:
        if log:
            print(f'[CLICK][ERROR] Failed to click: {e}')
        return False

def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5, log=True):
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
            if log:
                print(f'[ROBUSTO][FASE1] Buscando input com texto/atributo: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, 
                    f'input[placeholder*="{texto}"], '
                    f'input[aria-label*="{texto}"], '
                    f'input[name*="{texto}"]'
                )
                for el in elementos:
                    if el.is_displayed() and el.is_enabled():
                        if log:
                            print(f'[ROBUSTO][ENCONTRADO] Input direto: {el}')
                        return el
            except Exception as e:
                if log:
                    print(f'[ROBUSTO][ERRO] Fase1: {e}')
                continue
        # Fase 2: Busca hierárquica se não encontrar diretamente
        for texto in textos:
            if log:
                print(f'[ROBUSTO][FASE2] Buscando por texto visível: {texto}')
            try:
                elementos = driver.find_elements(By.XPATH, 
                    f'//*[contains(text(), "{texto}")]'
                )
                for el in elementos:
                    if log:
                        print(f'[ROBUSTO][FASE2] Elemento com texto encontrado: {el}')
                    input_assoc = buscar_input_associado(el)
                    if input_assoc:
                        if log:
                            print(f'[ROBUSTO][ENCONTRADO] Input associado: {input_assoc}')
                        return input_assoc
            except Exception as e:
                if log:
                    print(f'[ROBUSTO][ERRO] Fase2: {e}')
                continue
        # Fase 3: Busca por ícone/fa
        for texto in textos:
            if log:
                print(f'[ROBUSTO][FASE3] Buscando ícone/fa: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all')
                for el in elementos:
                    if el.is_displayed():
                        if log:
                            print(f'[ROBUSTO][ENCONTRADO] Ícone/fa: {el}')
                        return el
            except Exception as e:
                if log:
                    print(f'[ROBUSTO][ERRO] Fase3: {e}')
                continue
        if log:
            print('[ROBUSTO][FIM] Nenhum elemento encontrado com os critérios fornecidos.')
        return None
    except Exception as e:
        if log:
            print(f'[ROBUSTO][ERRO GERAL] {e}')
        return None
def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR, log=True):
    # Versão aprimorada - Espera até que um elemento esteja presente (e opcionalmente contenha texto), com logs detalhados.
    import time as _time
    try:
        if not isinstance(seletor, str):
            raise ValueError(f"Seletor deve ser string, recebido: {type(seletor)}")
        if texto and not isinstance(texto, str):
            raise ValueError(f"Text must be a string, got: {type(texto)}")
        if log:
            print(f"[ESPERAR] Aguardando elemento: '{seletor}' (by={by}, timeout={timeout}, texto={texto})")
        t0 = _time.time()
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )
        t1 = _time.time()
        if log:
            print(f"[ESPERAR][OK] Elemento encontrado: '{seletor}' em {t1-t0:.2f}s" + (f" (texto='{texto}')" if texto else ""))
        return el
    except Exception as e:
        if log:
            print(f"[ESPERAR][ERRO] Falha ao esperar elemento: '{seletor}' (by={by}, timeout={timeout}, texto={texto}) -> {e}")
        return None

# =========================
# 4. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

# Função para extrair documento
def extrair_documento(driver, regras_analise=None, timeout=15, log=True):
    # Extrai texto do documento aberto, aplica regras se houver.
    # Retorna: tupla (texto_final, resultado_analise) ou (None, None) em caso de erro.
    texto_completo = None
    texto_final = None
    resultado_analise = None
    try:
        # Espera o botão HTML
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            if log: print('[EXTRAI][ERRO] Botão HTML não encontrado.')
            return None, None

        # Clica no botão HTML
        safe_click(driver, btn_html)
        time.sleep(1)

        # Extrai o texto do preview
        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            if log: print('[EXTRAI][ERRO] Preview do documento não encontrado.')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return None, None

        texto_completo = preview.text

        # Fecha o modal ANTES de processar o texto
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            if log: print('[EXTRAI] Modal HTML fechado.')
            time.sleep(0.5)
            # Pressiona TAB para tentar restaurar cabeçalho da aba detalhes
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
            if log: print('[WORKAROUND] Pressionada tecla TAB após fechar modal de documento.')
        except Exception as e_esc:
            if log: print(f'[EXTRAI][WARN] Falha ao fechar modal com ESC: {e_esc}')

        if not texto_completo:
            if log: print('[EXTRAI][ERRO] Texto do preview vazio.')
            return None, None        # Extrai o texto abaixo de "Servidor Responsável" se encontrar, senão usa documento completo
        marcador = "Servidor Responsável"
        try:
            indice_marcador = texto_completo.rindex(marcador)
            indice_newline = texto_completo.find('\n', indice_marcador)
            if indice_newline != -1:
                texto_final = texto_completo[indice_newline:].strip()
            else:
                texto_final = texto_completo.strip()
            if log: print(f'[EXTRAI] Conteúdo extraído abaixo de "{marcador}".')
        except ValueError:
            # Se não encontrar o marcador, usa o documento INTEIRO para análise
            texto_final = texto_completo.strip()
            if log: print(f'[EXTRAI] Marcador "{marcador}" não encontrado. Usando texto completo do documento.')
            texto_final = texto_completo.strip()

        # Aplica regras de análise se houver
        if regras_analise and callable(regras_analise):
            if log: print('[EXTRAI] Aplicando regras de análise.')
            try:
                print('[DEBUG][REGRAS] Iniciando análise de regras...')
                resultado_analise = regras_analise(texto_final)
                print('[DEBUG][REGRAS] Análise de regras concluída.')
            except Exception as e_analise:
                print(f'[EXTRAI][ERRO] Falha ao analisar regras: {e_analise}')
                return texto_final, None

        if log: print('[EXTRAI] Extração concluída.')
        return texto_final, resultado_analise

    except Exception as e:
        if log: print(f'[EXTRAI][ERRO] Falha geral ao extrair documento: {e}')
        try:
            if driver.find_elements(By.CSS_SELECTOR, '#previewModeloDocumento'):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return None, None

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
def extrair_dados_processo(driver, max_tentativas=3, intervalo_tentativas=5):
    dados_processo = {"numero": "", "partes": [], "outros_dados": {}}
    json_path = "d:\\\\PjePlus\\\\dadosatuais.json"  # Corrigido para o caminho correto
    numero_processo_final = ""

    for tentativa in range(max_tentativas):
        try:
            logging.info(f"[EXTRAIR_DADOS] Tentativa {tentativa + 1} de extrair dados do processo.")

            # Estratégia Principal: Extrair do elemento clipboard do PJE + obter dados via API
            try:
                # Procura pelo elemento pje-icone-clipboard com aria-label contendo "Copia o número do processo"
                xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
                elemento_clipboard = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath_clipboard))
                )
                
                # Extrai o aria-label que contém o número do processo
                aria_label = elemento_clipboard.get_attribute("aria-label")
                if aria_label:
                    # Extrai o número do processo do aria-label usando regex
                    match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                    if match_clipboard:
                        numero_processo_final = match_clipboard.group(1)
                        logging.info(f"[EXTRAIR_DADOS] Número do processo encontrado no clipboard PJE: {numero_processo_final}")
                        
                        # TODO: Aqui você pode adicionar a lógica para obter dados via API usando o número do processo
                        # dados_api = obter_dados_via_api(numero_processo_final)
                        # if dados_api:
                        #     dados_processo.update(dados_api)
                        
                        break  # Sai do loop de tentativas
                        
            except TimeoutException:
                logging.warning("[EXTRAIR_DADOS] Elemento clipboard PJE não encontrado nesta tentativa")
            except Exception as e_clipboard:
                logging.warning(f"[EXTRAIR_DADOS] Erro na estratégia principal (clipboard PJE): {e_clipboard}")

            # Estratégia Fallback: Click no link de detalhes do processo
            if not numero_processo_final:
                try:
                    logging.info("[EXTRAIR_DADOS] Tentando estratégia fallback: clicar no link de detalhes do processo")
                    
                    # Procura por links que contenham o número do processo (formato padrão)
                    xpath_link_detalhes = "//a[contains(text(), '-') and contains(text(), '.') and string-length(normalize-space(text())) > 15]"
                    
                    link_detalhes = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_link_detalhes))
                    )
                    
                    # Extrai o número do processo do próprio link antes de clicar
                    texto_link = link_detalhes.text.strip()
                    match_link = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", texto_link)
                    
                    if match_link:
                        numero_processo_final = match_link.group(1)
                        logging.info(f"[EXTRAIR_DADOS] Número do processo encontrado no link: {numero_processo_final}")
                        
                        # Clica no link para abrir o modal com detalhes
                        driver.execute_script("arguments[0].click();", link_detalhes)
                        logging.info("[EXTRAIR_DADOS] Link de detalhes clicado com sucesso")
                        
                        # Aguarda o modal carregar
                        time.sleep(2)
                        
                        # Tenta extrair dados adicionais do modal de detalhes
                        try:
                            # Procura pela seção de dados do processo no modal
                            xpath_secao_dados = "//div[contains(@class, 'modal') or contains(@class, 'dialog')]//div[contains(@class, 'dados') or contains(@class, 'detalhes') or contains(@class, 'informacoes')]"
                            secao_dados = driver.find_element(By.XPATH, xpath_secao_dados)
                            
                            # Extrai texto da seção para logs
                            texto_secao = secao_dados.text
                            logging.info(f"[EXTRAIR_DADOS] Dados extraídos da seção de detalhes: {texto_secao[:500]}...")
                            
                            # Aqui você pode adicionar lógica específica para extrair outros dados como partes, etc.
                            # Por exemplo:
                            # partes_match = re.findall(r"Requerente|Requerido|Autor|Réu.*?([^\n]+)", texto_secao)
                            # dados_processo["partes"] = partes_match
                            
                        except Exception as e_modal:
                            logging.warning(f"[EXTRAIR_DADOS] Erro ao extrair dados do modal: {e_modal}")
                        
                        # Fecha o modal usando 3 ESC
                        for i in range(3):
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                        
                        logging.info("[EXTRAIR_DADOS] Modal fechado com 3 ESC")
                        break  # Sai do loop de tentativas
                        
                except TimeoutException:
                    logging.warning("[EXTRAIR_DADOS] Link de detalhes do processo não encontrado nesta tentativa")
                except Exception as e_fallback:
                    logging.warning(f"[EXTRAIR_DADOS] Erro na estratégia fallback: {e_fallback}")

            # Se nenhuma estratégia funcionou nesta tentativa
            if not numero_processo_final:
                logging.warning(f"[EXTRAIR_DADOS] Número do processo não encontrado na tentativa {tentativa + 1}.")
                if tentativa < max_tentativas - 1:
                    logging.info(f"Aguardando {intervalo_tentativas} segundos para a próxima tentativa.")
                    time.sleep(intervalo_tentativas)
                else:
                    logging.error(f"[EXTRAIR_DADOS] Todas as tentativas de extrair o número do processo falharam após {max_tentativas} tentativas.")
        
        except Exception as e_outer:  # Captura exceções inesperadas no loop de tentativa
            logging.error(f"[EXTRAIR_DADOS] Erro geral inesperado na tentativa {tentativa + 1}: {e_outer}")
            if tentativa < max_tentativas - 1:
                time.sleep(intervalo_tentativas)
            else:
                logging.error("[EXTRAIR_DADOS] Erro final e inesperado ao tentar extrair dados do processo.")
        
        # Verifica novamente se o número foi encontrado para sair do loop principal
        if numero_processo_final:
            break

    # Atualiza o dicionário com o número do processo encontrado (ou vazio se não encontrado)
    dados_processo["numero"] = numero_processo_final
    
    # Salva no JSON sempre ao final, após todas as tentativas
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dados_processo, f, ensure_ascii=False, indent=4)
        logging.info(f"[EXTRAIR_DADOS] Dados do processo salvos em {json_path}: {dados_processo}")
    except Exception as e_json:
        logging.error(f"[EXTRAIR_DADOS] Erro crítico ao salvar dados em JSON: {e_json}")
    
    return dados_processo

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
def criar_gigs(driver, dias_uteis, observacao, tela='principal', timeout=10, log=True):
    # Cria GIGS em qualquer tela (principal ou minuta), parametrizável.
    # tela: 'principal' (default) ou 'minuta' para lógica adaptada.
    import datetime
    t0 = time.time()
    try:
        if log:
            print(f"[GIGS] Iniciando criação de GIGS: {dias_uteis}/{observacao} (tela=principal)")
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
        campo_obs = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
        )
        campo_obs.clear()
        for c in observacao:
            campo_obs.send_keys(c)
            time.sleep(0.03)
        if log:
            print(f'[GIGS] Observação preenchida: {observacao}')
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
        # Aguarda o fechamento do modal
        try:
            WebDriverWait(driver, 8).until_not(
                lambda d: any(m.is_displayed() for m in d.find_elements(By.CSS_SELECTOR, '.mat-dialog-container'))
            )
        except Exception:
            pass
        if log:
            print('[GIGS] GIGS criado com sucesso!')
        return True
    except Exception as e:
        if log:
            print(f'[GIGS][ERRO] Falha ao criar GIGS: {e}')
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

def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    # Indexa e já processa cada processo sequencialmente, sem delay e sem logs intermediários desnecessários.
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
      # Armazena a referência da aba da lista ANTES de qualquer operação
    aba_lista_original = driver.current_window_handle
    print(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')
    
    # Indexa e obtém as linhas/processos
    linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    print(f'[INDEXAR] Total de processos encontrados: {len(linhas)}')
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []
    for idx, linha in enumerate(linhas):
        try:
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                texto = tds[0].text.strip() if tds else ''
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            processos.append((num_proc, linha))
            print(f'[INDEXAR] {idx+1:02d}: {num_proc}')
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e}')
    
    print(f'[FLUXO] Indexação concluída. Iniciando processamento da lista de processos...', flush=True)
    
    def validar_conexao_driver(driver, contexto="GERAL"):
        """Valida se a conexão com o driver está ativa e funcional"""
        try:
            # Verifica se o driver possui session_id válido
            if not hasattr(driver, 'session_id') or driver.session_id is None:
                print(f'[{contexto}][CONEXÃO][ERRO] Driver não possui session_id válido')
                return False
                
            # Testa a conexão com comando simples
            try:
                current_url = driver.current_url
                window_handles = driver.window_handles
                print(f'[{contexto}][CONEXÃO][OK] Driver conectado - URL: {current_url[:50]}... | Abas: {len(window_handles)}')
                return True
            except Exception as connection_test_err:
                print(f'[{contexto}][CONEXÃO][ERRO] Falha no teste de conexão: {connection_test_err}')
                return False
                
        except Exception as validation_err:
            print(f'[{contexto}][CONEXÃO][ERRO] Falha na validação de conexão: {validation_err}')
            return False
    
    def forcar_fechamento_abas_extras():
        """Força o fechamento de abas extras, mantendo apenas a aba da lista com validação de conexão"""
        try:
            # Valida conexão antes de tentar operações
            if not validar_conexao_driver(driver, "LIMPEZA"):
                print('[LIMPEZA][ERRO] Conexão perdida - não é possível limpar abas')
                return False
                
            abas_atuais = driver.window_handles
            print(f'[LIMPEZA] Abas detectadas: {len(abas_atuais)}')
            
            for aba in abas_atuais:
                if aba != aba_lista_original:
                    try:
                        # Valida conexão antes de cada operação
                        if not validar_conexao_driver(driver, "LIMPEZA_ABA"):
                            print(f'[LIMPEZA][ERRO] Conexão perdida durante limpeza da aba {aba}')
                            return False
                            
                        driver.switch_to.window(aba)
                        driver.close()
                        print(f'[LIMPEZA] Aba fechada: {aba}')
                    except Exception as e:
                        print(f'[LIMPEZA][WARN] Erro ao fechar aba {aba}: {e}')
            
            # Volta para a aba da lista
            if aba_lista_original in driver.window_handles:
                if not validar_conexao_driver(driver, "LIMPEZA_RETORNO"):
                    print('[LIMPEZA][ERRO] Conexão perdida antes de retornar à aba da lista')
                    return False
                    
                driver.switch_to.window(aba_lista_original)
                print('[LIMPEZA] Retornou para aba da lista')
                return True
            else:
                print('[LIMPEZA][ERRO] Aba da lista original não está mais disponível!')
                return False
        except Exception as e:
            print(f'[LIMPEZA][ERRO] Falha na limpeza de abas: {e}')
            return False
    # Processa cada processo da lista indexada
    processos_processados = 0
    processos_com_erro = 0
    
    for idx, (proc_id, linha) in enumerate(processos):
        try:
            print(f'[PROCESSAR] Iniciando processo {idx+1}/{len(processos)}: {proc_id}', flush=True)
            
            # PASSO 1: Força limpeza de abas extras ANTES de abrir novo processo
            print(f'[PROCESSAR][PRE] Verificando estado de abas antes de processar {proc_id}...')
            abas_iniciais = driver.window_handles
            print(f'[PROCESSAR][PRE] Abas detectadas inicialmente: {len(abas_iniciais)}')
            
            if len(abas_iniciais) > 1:
                print(f'[PROCESSAR][PRE] Múltiplas abas detectadas! Forçando limpeza antes de {proc_id}...')
                if not forcar_fechamento_abas_extras():
                    print(f'[PROCESSAR][ERRO] Não foi possível limpar abas antes do processo {proc_id}. Abortando processamento.')
                    return False
            
            # Verifica se ainda estamos na aba da lista
            if driver.current_window_handle != aba_lista_original:
                print(f'[PROCESSAR][WARN] Não estamos na aba da lista antes de {proc_id}. Tentando retornar...')
                try:
                    driver.switch_to.window(aba_lista_original)
                    print(f'[PROCESSAR][PRE] Retornado à aba da lista para {proc_id}')
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Não foi possível retornar à aba da lista antes de {proc_id}: {e}')
                    return False            # PASSO 2: Reindexar e abrir o processo na lista
            # A referência DOM da linha pode ter ficado obsoleta após limpeza de abas
            # Vamos buscar novamente a linha pelo número do processo
            linha_atual = None
            try:
                # Busca todas as linhas novamente
                linhas_atuais = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
                for linha_temp in linhas_atuais:
                    try:
                        # Extrai o texto da linha para encontrar o processo correto
                        links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                        texto_linha = ''
                        if links:
                            texto_linha = links[0].text.strip()
                        else:
                            tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                            texto_linha = tds[0].text.strip() if tds else ''
                        
                        # Verifica se é a linha do processo que queremos
                        if proc_id in texto_linha:
                            linha_atual = linha_temp
                            print(f'[PROCESSAR][REINDEX] Linha reindexada para {proc_id}')
                            break
                    except Exception as e:
                        continue
                        
                if not linha_atual:
                    print(f'[PROCESSAR][ERRO] Não foi possível reindexar a linha para {proc_id}')
                    processos_com_erro += 1
                    continue
                    
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha na reindexação para {proc_id}: {e}')
                processos_com_erro += 1
                continue
            
            # Agora busca o botão na linha reindexada
            btn = None
            try:
                btn = linha_atual.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
            except Exception:
                try:
                    btn = linha_atual.find_element(By.CSS_SELECTOR, 'button, a')
                except Exception:
                    pass
            if btn is not None:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                driver.execute_script("arguments[0].click();", btn)
                print(f'[PROCESSAR][CLICK] Botão de detalhes clicado para {proc_id}')
            else:
                print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
                processos_com_erro += 1
                continue
            time.sleep(1)
            
            # PASSO 3: Trocar para a nova aba
            time.sleep(1)
            abas = driver.window_handles
            nova_aba = None
            for h in abas:
                if h != aba_lista_original:
                    nova_aba = h
                    break
            if not nova_aba:
                print(f'[PROCESSAR][ERRO] Nova aba do processo {proc_id} não foi aberta.')
                processos_com_erro += 1
                continue
            try:
                driver.switch_to.window(nova_aba)
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Não foi possível trocar para nova aba do processo {proc_id}: {e}')
                processos_com_erro += 1
                continue
            url_aba = driver.current_url
            if log:
                print(f'[PROCESSAR] Aba do processo {proc_id} aberta em {url_aba}.')
            
            # Aplica workaround TAB após abrir a aba
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
                print('[WORKAROUND] Pressionada tecla TAB para tentar restaurar cabeçalho da aba detalhes.')
            except Exception as e:
                print(f'[WORKAROUND][ERRO] Falha ao pressionar TAB: {e}')
              # PASSO 4: Executar callback (ou simular automação) com tratamento defensivo de abas
            callback_sucesso = False
            try:
                if callback:
                    print(f'[PROCESSAR][DEBUG] Iniciando callback para processo {proc_id}...', flush=True)
                    
                    # Captura estado das abas ANTES do callback
                    abas_antes_callback = set(driver.window_handles)
                    
                    # Executa callback
                    callback(driver)
                    
                    # Verifica estado das abas APÓS callback
                    abas_depois_callback = set(driver.window_handles)
                    novas_abas_callback = abas_depois_callback - abas_antes_callback
                    
                    if novas_abas_callback:
                        print(f'[PROCESSAR][WARN] Callback criou {len(novas_abas_callback)} nova(s) aba(s): {novas_abas_callback}')
                    
                    print(f'[PROCESSAR][DEBUG] Callback concluído para processo {proc_id}.', flush=True)
                    callback_sucesso = True
                    processos_processados += 1
                else:
                    print(f'[PROCESSAR][DEBUG] Nenhum callback definido para processo {proc_id}.', flush=True)
                    callback_sucesso = True
                    processos_processados += 1
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}', flush=True)
                import traceback
                print(f'[PROCESSAR][ERRO] Traceback completo: {traceback.format_exc()}', flush=True)
                processos_com_erro += 1
                callback_sucesso = False
            
            # PASSO 5: FORÇA limpeza de abas após processamento (SEMPRE, independente do callback)
            print(f'[PROCESSAR] Processo {proc_id} finalizado (sucesso={callback_sucesso}) - FORÇANDO limpeza completa de abas...')
            
            # Limpeza defensiva SEMPRE, mesmo que callback falhe
            try:
                abas_antes_limpeza = driver.window_handles
                print(f'[PROCESSAR][LIMPEZA] Abas antes da limpeza: {len(abas_antes_limpeza)}')
                
                if not forcar_fechamento_abas_extras():
                    print(f'[PROCESSAR][ERRO] Falha na limpeza automática para {proc_id}. Tentando limpeza manual...')
                    
                    # Limpeza manual forçada em caso de falha
                    for aba in driver.window_handles:
                        if aba != aba_lista_original:
                            try:
                                driver.switch_to.window(aba)
                                driver.close()
                                print(f'[PROCESSAR][LIMPEZA] Aba manual fechada: {aba}')
                            except Exception as cleanup_err:
                                print(f'[PROCESSAR][LIMPEZA][WARN] Erro na limpeza manual da aba {aba}: {cleanup_err}')
                    
                    # Volta para a lista após limpeza manual
                    try:
                        driver.switch_to.window(aba_lista_original)
                        print('[PROCESSAR][LIMPEZA] Retornou à aba da lista após limpeza manual')
                    except Exception as switch_err:
                        print(f'[PROCESSAR][ERRO] Não foi possível retornar à aba da lista: {switch_err}')
                        return False
                
                abas_depois_limpeza = driver.window_handles
                print(f'[PROCESSAR][LIMPEZA] Abas após limpeza: {len(abas_depois_limpeza)}')
                
                if len(abas_depois_limpeza) > 1:
                    print(f'[PROCESSAR][WARN] Ainda há {len(abas_depois_limpeza)} abas abertas após limpeza!')
                
            except Exception as cleanup_error:
                print(f'[PROCESSAR][ERRO] Falha crítica na limpeza de abas para {proc_id}: {cleanup_error}')
                # Mesmo com erro na limpeza, tenta continuar
                try:
                    driver.switch_to.window(aba_lista_original)
                except:
                    print(f'[PROCESSAR][ERRO] Não foi possível retornar à aba da lista após erro de limpeza')
                    return False
            
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha geral ao processar processo {proc_id}: {e}')
            processos_com_erro += 1
            # Mesmo com erro, força limpeza de abas para tentar prosseguir
            try:
                forcar_fechamento_abas_extras()
            except:
                pass
            continue
    
    # Relatório final
    print(f'[FLUXO] Processamento concluído!')
    print(f'[FLUXO] Processos processados com sucesso: {processos_processados}')
    print(f'[FLUXO] Processos com erro: {processos_com_erro}')
    print(f'[FLUXO] Total de processos: {len(processos)}')
    
    return processos_processados > 0  # Retorna True se pelo menos um processo foi processado

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

def copiarDOC(driver, id):
    # Função para copiar o conteúdo do documento ativo no PJe via PDF.js.
    # Args:
    # driver: WebDriver instance.
    # id: Identificador do documento a ser copiado.
    # Returns:
    # String com o conteúdo ou None se falhar
    try:
        print(f"[COPIAR_DOC] Tentando extrair texto do documento ID: {id}")
        
        # Opção 1: Tentar extrair diretamente do viewer PDF.js principal
        try:
            viewer_element = driver.find_element(By.CSS_SELECTOR, 'div#viewer.pdfViewer')
            if viewer_element:
                conteudo = viewer_element.text
                if conteudo and conteudo.strip():
                    print(f"[COPIAR_DOC] Texto extraído via div#viewer.pdfViewer: {len(conteudo)} caracteres")
                    return conteudo.strip()
        except Exception as e:
            print(f"[COPIAR_DOC] Falha na extração via div#viewer.pdfViewer: {e}")
        
        # Opção 2: Tentar acessar elemento de acessibilidade oculto
        try:
            elemento_acess = driver.find_element(By.CSS_SELECTOR, f'#acess{id}')
            if elemento_acess:
                # Tornar visível temporariamente para extração
                driver.execute_script("arguments[0].style.display = 'block';", elemento_acess)
                conteudo = elemento_acess.text
                driver.execute_script("arguments[0].style.display = 'none';", elemento_acess)
                
                if conteudo and conteudo.strip():
                    print(f"[COPIAR_DOC] Texto extraído via elemento acessibilidade: {len(conteudo)} caracteres")
                    return conteudo.strip()
        except Exception as e:
            print(f"[COPIAR_DOC] Falha na extração via elemento acessibilidade: {e}")
        
        # Opção 2: Tentar acessar PDF.js diretamente
        try:
            objeto_pdf = driver.find_element(By.CSS_SELECTOR, f'#obj{id}')
            if objeto_pdf:
                # Executar JavaScript para acessar conteúdo do PDF.js
                script = """
                try {
                    var obj = arguments[0];
                    var pdfWindow = obj.contentWindow;
                    if (pdfWindow && pdfWindow.PDFViewerApplication) {
                        var pdfApp = pdfWindow.PDFViewerApplication;
                        if (pdfApp.pdfDocument) {
                            // Tentar extrair texto de todas as páginas
                            var extractText = async function() {
                                var textContent = '';
                                var numPages = pdfApp.pdfDocument.numPages;
                                for (var i = 1; i <= numPages; i++) {
                                    var page = await pdfApp.pdfDocument.getPage(i);
                                    var content = await page.getTextContent();
                                    var strings = content.items.map(item => item.str);
                                    textContent += strings.join(' ') + '\\n';
                                }
                                return textContent;
                            };
                            return extractText();
                        }
                    }
                    return null;
                } catch (e) {
                    return 'ERRO: ' + e.message;
                }
                """
                resultado = driver.execute_script(script, objeto_pdf)
                
                if resultado and isinstance(resultado, str) and not resultado.startswith('ERRO'):
                    print(f"[COPIAR_DOC] Texto extraído via PDF.js: {len(resultado)} caracteres")
                    return resultado.strip()
                else:
                    print(f"[COPIAR_DOC] Falha na extração via PDF.js: {resultado}")
        except Exception as e:
            print(f"[COPIAR_DOC] Falha na extração via PDF.js: {e}")
          # Opção 3: Usar extrair_documento_silencioso como fallback preferencial
        try:
            print("[COPIAR_DOC] Tentando usar extrair_documento_silencioso...")
            resultado = extrair_documento_silencioso(driver, log=False)
            if resultado:
                print(f"[COPIAR_DOC] Texto extraído via extrair_documento_silencioso: {len(resultado)} caracteres")
                return resultado
        except Exception as e:
            print(f"[COPIAR_DOC] Falha ao usar extrair_documento_silencioso: {e}")
        
        # Opção 4: Usar extrair_documento original como último recurso
        try:
            print("[COPIAR_DOC] Tentando usar extrair_documento original como último recurso...")
            resultado = extrair_documento(driver, log=False)
            if resultado and resultado[0]:
                print(f"[COPIAR_DOC] Texto extraído via extrair_documento: {len(resultado[0])} caracteres")
                return resultado[0]
        except Exception as e:
            print(f"[COPIAR_DOC] Falha no fallback extrair_documento: {e}")
        
        print("[COPIAR_DOC] Nenhum método de extração funcionou.")
        return None
        
    except Exception as e:
        print(f"[COPIAR_DOC] Erro geral: {str(e)}")
        return None


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

def visibilidade_sigilosos(driver, log=True):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente.
    """
    try:
        # Localiza o último documento juntado
        ultimo_documento = driver.find_element(By.CSS_SELECTOR, "div.timeline-item:last-child")
        if not ultimo_documento:
            if log:
                print("[VISIBILIDADE][ERRO] Último documento não encontrado.")
            return False

        # Verifica se o documento é sigiloso
        btn_sigilo = ultimo_documento.find_element(By.CSS_SELECTOR, "i.fa-wpexplorer")
        if btn_sigilo:
            btn_sigilo.click()
            time.sleep(0.5)

        # Aplica visibilidade
        btn_visibilidade = ultimo_documento.find_element(By.CSS_SELECTOR, "i.fa-plus")
        if btn_visibilidade.is_displayed():
            btn_visibilidade.click()
            time.sleep(0.5)

            # Confirma a visibilidade no modal
            modal_contexto = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-content")
            btn_coluna = modal_contexto.find_element(By.CSS_SELECTOR, "i.botao-icone-titulo-coluna")
            btn_coluna.click()
            time.sleep(0.3)

            btn_salvar = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-actions > button:nth-child(1) > span:nth-child(1)")
            btn_salvar.click()
            if log:
                print("[VISIBILIDADE] Visibilidade aplicada com sucesso.")

            # Fecha o modal
            modal_contexto.send_keys(Keys.ESCAPE)
            time.sleep(1)
        else:
            if log:
                print("[VISIBILIDADE][ERRO] Botão de visibilidade não visível.")
            return False

        return True

    except Exception as e:
        if log:
            print(f"[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}")
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




