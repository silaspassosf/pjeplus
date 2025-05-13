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

# =========================
# 1. UTILITÁRIOS E LIMPEZA
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
    FIREFOX_BINARY = r"C:\ Program Files\Firefox Developer Edition\firefox.exe"
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service()
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    return driver

def driver_notebook(headless=False):
    # Retorna um driver Firefox padronizado para o ambiente TRT2, usando um perfil específico para notebooks.
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import os
    PROFILE_PATH = r"C:\\Users\\s164283\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\2bge54ld.Robot"
    FIREFOX_BINARY = r"C:\\Users\\s164283\\AppData\\Local\\Firefox Developer Edition\\firefox.exe"
    GECKODRIVER_PATH = r"C:\\Users\\s164283\\Desktop\\Pjeplus\\pjeplus\\geckodriver.exe"
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    return driver

# Função de login automático
def login_pc(driver):
    """
    Login automático no PJe TRT2 para PC, com tentativa de reutilização de cookies e lógica de cliques robusta.
    Usuário e senha são lidos das variáveis de ambiente PJE_USER e PJE_PASS.
    """
    import os
    import time
    usuario = os.environ.get('PJE_USER')
    senha = os.environ.get('PJE_PASS')
    if not usuario or not senha:
        print('[LOGIN][ERRO] Variáveis de ambiente PJE_USER e/ou PJE_PASS não definidas.')
        return False
    caminho_cookies = 'cookies_pjeplus_pc.json'
    # Tenta carregar cookies antes de login manual
    if carregar_cookies(driver, caminho_cookies):
        print('[LOGIN][PC] Cookies carregados, tentando acesso sem login manual...')
        time.sleep(2)
        if 'login' not in driver.current_url.lower():
            print('[LOGIN][PC] Login por cookies bem-sucedido.')
            return True
        else:
            print('[LOGIN][PC] Cookies inválidos ou expirados, prosseguindo com login manual.')
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    print('[LOGIN][PC] Página de login carregada.')
    # 1. Clicar no botão SSO PDPJ
    btn_sso = wait(driver, '#btnSsoPdpj', timeout=15)
    if not btn_sso:
        print('[LOGIN][ERRO] Botão SSO PDPJ não encontrado.')
        return False
    btn_sso.click()
    print('[LOGIN][PC] Botão SSO PDPJ clicado.')
    time.sleep(1)
    # 2. Preencher campo usuário
    campo_usuario = wait(driver, '#username', timeout=15)
    if not campo_usuario:
        print('[LOGIN][ERRO] Campo de usuário não encontrado.')
        return False
    campo_usuario.clear()
    campo_usuario.send_keys(usuario)
    print('[LOGIN][PC] Usuário preenchido.')
    time.sleep(1)
    # 3. Preencher campo senha
    campo_senha = wait(driver, '#password', timeout=15)
    if not campo_senha:
        print('[LOGIN][ERRO] Campo de senha não encontrado.')
        return False
    campo_senha.clear()
    campo_senha.send_keys(senha)
    print('[LOGIN][PC] Senha preenchida.')
    time.sleep(1)
    # 4. Clicar no botão de login
    btn_login = wait(driver, '#kc-login', timeout=15)
    if not btn_login:
        print('[LOGIN][ERRO] Botão de login não encontrado.')
        return False
    btn_login.click()
    print('[LOGIN][PC] Botão de login clicado.')
    time.sleep(3)
    # Após clicar no botão de login, checar acesso negado
    time.sleep(2)
    if checar_acesso_negado(driver):
        return False
    print('[LOGIN][PC] Login realizado com sucesso.')
    # Salva cookies após login bem-sucedido
    salvar_cookies(driver, caminho_cookies)
    # Navega diretamente para a página de atividades
    driver.get('https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades')
    print('[NAVEGAR] Página de atividades carregada.')
    time.sleep(3)
    # Aplica o filtro 100
    if aplicar_filtro_100(driver):
        print('[FILTRO] Filtro 100 aplicado com sucesso.')
    else:
        print('[FILTRO][ERRO] Falha ao aplicar o filtro 100.')
    return True

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
    # Aplica o filtro para exibir 100 itens por página no painel global.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    try:
        # Aguarda pelo menos uma linha da tabela de atividades estar visível antes de clicar no filtro
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
            )
            print('[FILTRO][DEBUG] Tabela de atividades carregada (tr.cdk-drag visível).')
        except Exception:
            print('[FILTRO][ERRO] Tabela de atividades não carregou a tempo.')
            return False

        # Encontra todos os spans de linhas por página
        spans = driver.find_elements(By.CSS_SELECTOR, "span.mat-select-min-line")
        seletor = None
        for s in reversed(spans):
            if s.is_displayed():
                # Sobe para o div.mat-select-value pai
                parent_div = s.find_element(By.XPATH, "./ancestor::div[contains(@class,'mat-select-value')]")
                if parent_div and parent_div.is_displayed():
                    seletor = parent_div
                    break
        if not seletor:
            print('[FILTRO][ERRO] Nenhum seletor de linhas por página visível encontrado.')
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", seletor)
        seletor.click()
        print('[FILTRO] Dropdown de linhas por página clicado (div.mat-select-value).')
        time.sleep(0.7)

        # Aguarda o overlay do dropdown aparecer
        try:
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )
            print('[FILTRO][DEBUG] Overlay do dropdown detectado.')
        except Exception:
            print('[FILTRO][ERRO] Overlay do dropdown não detectado.')
            return False

        # Busca apenas opções "100" dentro do overlay aberto
        opcoes = overlay.find_elements(By.XPATH, ".//span[contains(text(), '100')]")
        print(f'[FILTRO][DEBUG] Encontradas {len(opcoes)} opções "100" dentro do overlay.')
        clicou = False
        for idx, opcao in enumerate(opcoes):
            try:
                if opcao.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                    opcao.click()
                    print(f'[FILTRO] Selecionado 100 itens por página. Clique funcionou em opção #{idx+1} dentro do overlay.')
                    time.sleep(1)
                    clicou = True
                    break
                else:
                    print(f'[FILTRO][DEBUG] Opção #{idx+1} não está visível.')
            except Exception as e:
                print(f'[FILTRO][WARN] Falha ao clicar na opção #{idx+1} (100) dentro do overlay: {e}')
        if not clicou:
            print('[FILTRO][ERRO] Opção 100 não encontrada entre as opções visíveis no overlay.')
            return False
        return True
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha ao aplicar filtro 100: {e}')
        return False

# Função para processar lista de processos

def processar_lista_processos(driver, callback=None, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    # Percorre lista de processos, abre detalhes, executa callback, fecha aba, volta.
    # Agora NÃO faz mais indexação/listagem duplicada: espera que a lista já tenha sido extraída.
    # Só fecha a aba do processo se houver mais de uma aba aberta.
    from selectors_pje import buscar_seletor_robusto
    import time
    import re
    try:
        processados = 0
        processos_ids_processados = set()
        # Indexação/listagem removida! Assume que a lista já foi extraída e está na tela.
        if modo == 'tabela':
            processos = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        else:
            processos = driver.find_elements(By.CSS_SELECTOR, 'div.pje-content')
        lista_processos = []
        for idx, processo in enumerate(processos):
            try:
                proc_id = None
                links = processo.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    proc_id = links[0].text.strip()
                if not proc_id:
                    tds = processo.find_elements(By.TAG_NAME, 'td')
                    proc_id = tds[0].text.strip() if tds else None
                if not proc_id or proc_id in processos_ids_processados:
                    continue
                lista_processos.append((proc_id, idx))
            except Exception:
                continue
        if not lista_processos:
            if log:
                print('[PROCESSAR][ERRO] Nenhum processo encontrado para processar.')
            return False
        print(f'[PROCESSAR] Lista de processos extraída ({len(lista_processos)}):')
        for proc_id, _ in lista_processos:
            print(proc_id)
        time.sleep(2) # Added 2-second automatic delay
        aba_lista = driver.current_window_handle
        for idx, (proc_id, linha_idx) in enumerate(lista_processos):
            try:
                if max_processos and processados >= max_processos:
                    return True
                # Sempre volta para a aba da lista antes de abrir o próximo
                if aba_lista not in driver.window_handles:
                    print('[PROCESSAR][ERRO] Aba da lista foi perdida. Abortando processamento.')
                    return False
                try:
                    driver.switch_to.window(aba_lista)
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Não foi possível trocar para aba da lista: {e}')
                    return False
                # 1. Abrir o processo na lista
                linha = processos[linha_idx]
                try:
                    btn = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
                except Exception:
                    btn = None
                if btn is not None:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    driver.execute_script("arguments[0].click();", btn)
                else:
                    print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
                    continue
                time.sleep(1)
                # 2. Trocar para a nova aba
                time.sleep(1)
                abas = driver.window_handles
                nova_aba = None
                for h in abas:
                    if h != aba_lista:
                        nova_aba = h
                        break
                if not nova_aba:
                    print(f'[PROCESSAR][ERRO] Nova aba do processo {proc_id} não foi aberta.')
                    continue
                try:
                    driver.switch_to.window(nova_aba)
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Não foi possível trocar para nova aba do processo {proc_id}: {e}')
                    continue
                url_aba = driver.current_url
                if log:
                    print(f'[PROCESSAR] Aba do processo {proc_id} aberta em {url_aba}.')
                # 3. Executar callback (ou simular automação)
                try:
                    if callback:
                        callback(driver)
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}')
                # 4. Fechar a aba do processo, mas só se houver mais de uma aba aberta
                if len(driver.window_handles) > 1:
                    try:
                        driver.close()
                    except Exception as e:
                        print(f'[PROCESSAR][WARN] Erro ao fechar aba do processo {proc_id}: {e}')
                    # Volta para a aba da lista, se existir
                    if aba_lista in driver.window_handles:
                        try:
                            driver.switch_to.window(aba_lista)
                        except Exception as e:
                            print(f'[PROCESSAR][ERRO] Não foi possível voltar para aba da lista após fechar aba do processo {proc_id}: {e}')
                            return False
                    else:
                        print(f'[PROCESSAR][ERRO] Aba da lista não está mais disponível após fechar aba do processo {proc_id}.')
                        return False
                else:
                    print(f'[PROCESSAR][ERRO] Só existe uma aba aberta, não será fechada.')
                if log:
                    print(f'[PROCESSAR] Aba do processo {proc_id} fechada - voltando à lista.')
                time.sleep(1)
                processos_ids_processados.add(proc_id)
                processados += 1
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha ao processar processo {proc_id}: {e}')
                continue
        print('[PROCESSAR] Fim do processamento da lista.')
        return True
    except Exception as e:
        if log:
            print(f'[PROCESSAR][ERRO] Falha geral: {e}')
        return False

# Seção: Interação com Elementos

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
        if element is None and (
            'Detalhes do Processo' in selector_or_element or 'detalhes do processo' in selector_or_element.lower()
        ):
            try:
                # Try clicking the KZ icon directly
                element = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[aria-label*="Detalhes do Processo"]')
            except Exception:
                element = None
            if element is not None:
                driver.execute_script("arguments[0].click();", element)
                if log:
                    print('[CLICK] Clicked KZ details icon (img.mat-tooltip-trigger)')
                return True
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

# Seção: Extração de Dados
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
            return None, None

        # Extrai o texto abaixo de "Servidor Responsável"
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
            if log: print(f'[EXTRAI] Marcador "{marcador}" não encontrado. Usando texto completo.')
            texto_final = texto_completo.strip()

        # Aplica regras de análise se houver
        if regras_analise and callable(regras_analise):
            if log: print('[EXTRAI] Aplicando regras de análise.')
            try:
                resultado_analise = regras_analise(texto_final)
            except Exception as e_analise:
                if log: print(f'[EXTRAI][ERRO] Falha ao aplicar regras de análise: {e_analise}')
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

def extrair_texto_pdf_por_conteudo(driver, termo=None, pagina=2, timeout=10):
    # Extrai o texto da página desejada de um PDF embutido (object.conteudo-pdf) e retorna o texto encontrado.
    # Se termo for informado, retorna apenas o trecho que contém o termo.
    import time
    try:
        obj_pdf = driver.find_element(By.CSS_SELECTOR, 'object.conteudo-pdf')
        doc = obj_pdf.get_property('contentDocument') or obj_pdf.get_property('contentWindow').document
        if not doc:
            print('[PDF] Não foi possível obter o document do PDF.')
            return None
        paginas = doc.querySelectorAll('.page')
        if len(paginas) > pagina:
            driver.execute_script('arguments[0].scrollIntoView(true);', paginas[pagina])
            time.sleep(2)
            texto = driver.execute_script('return arguments[0].innerText;', paginas[pagina])
            if termo:
                idx = texto.lower().find(termo.lower())
                if idx >= 0:
                    return texto[idx:idx+100]  # retorna trecho ao redor do termo
            return texto
        else:
            print('[PDF] Página não encontrada.')
            return None
    except Exception as e:
        print(f'[PDF][ERRO] {e}')
        return None
## Função para extrair dados do processo
def extrair_dados_processo(driver, log=True):
    # Extrai dados estruturados do processo com foco nas partes (ativas/passivas/outras) e inclui valor do cálculo PJeCalc.
    # Retorna:
    # {
    # 'numero': str,               # Número completo do processo
    # 'partes': {
    # 'ativas': [],
    # 'passivas': [],
    # 'outras': []
    # },
    # 'metadados': dict,
    # 'calculo_pjecalc': { 'valor': ..., 'data': ... } ou None
    # }
    from selenium.webdriver.common.by import By
    import re
    
    dados = {
        'partes': {
            'ativas': [],
            'passivas': [],
            'outras': []
        },
        'metadados': {}
    }

    try:
        # Extração do diálogo de autuação
        dialogo = driver.find_element(By.CSS_SELECTOR, 'pje-autuacao-dialogo section#autuacao-dialogo')
        bloco = dialogo.find_element(By.CSS_SELECTOR, 'pje-autuacao section#processo')
        
        # Metadados básicos
        dts = bloco.find_elements(By.TAG_NAME, 'dt')
        dds = bloco.find_elements(By.TAG_NAME, 'dd')
        for dt, dd in zip(dts, dds):
            chave = dt.text.strip().replace(':', '')
            valor = dd.text.strip()
            if chave:
                dados['metadados'][chave] = valor
        
        # Extração robusta das partes
        for ul in bloco.find_elements(By.CSS_SELECTOR, 'ul.lista'):
            for li in ul.find_elements(By.CSS_SELECTOR, 'li.partes-corpo'):
                texto = li.text.strip()
                if not texto:
                    continue
                
                # Classificação por padrões
                texto_lower = texto.lower()
                if any(p in texto_lower for p in ['autor', 'requerente', 'exequente']):
                    categoria = 'ativas'
                elif any(p in texto_lower for p in ['réu', 'requerido', 'executado']):
                    categoria = 'passivas' 
                else:
                    categoria = 'outras'
                
                # Extração de documento se existir
                doc_match = re.search(
                    r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', 
                    texto
                )
                
                dados['partes'][categoria].append({
                    'nome': re.sub(r'\b(CPF|CNPJ).*', '', texto).strip(),
                    'documento': doc_match.group(0) if doc_match else None,
                    'texto_completo': texto
                })

        # INCLUIR INFORMAÇÃO DE CÁLCULO PJeCalc
        try:
            from calc import obter_valor_calculo_api, obter_id_processo_da_url
            id_processo = obter_id_processo_da_url(driver)
            if id_processo:
                resultado = obter_valor_calculo_api(driver, id_processo)
                if resultado:
                    dados['calculo_pjecalc'] = {
                        'valor': resultado['total'],
                        'data': resultado['dataLiquidacao']
                    }
                else:
                    dados['calculo_pjecalc'] = None
            else:
                dados['calculo_pjecalc'] = None
        except Exception as e:
            if log:
                print(f'[Fix.py] Erro ao extrair cálculo PJeCalc: {e}')
            dados['calculo_pjecalc'] = None

        if log:
            print('[Fix.py] Dados das partes extraídos com sucesso')
        return dados

    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao extrair dados do processo: {e}')
        return dados

def exibir_painel_copia_cola(driver, dados, log=True):
    # Exibe os dados extraídos do processo no painel Copia e Cola (formatação amigável).
    conteudo = ''
    for k, v in dados.items():
        if isinstance(v, list):
            conteudo += f'\n{k}:\n'
            for item in v:
                conteudo += f'  - {item}\n'
        else:
            conteudo += f'{v}\n'
    # Preenche o painel (se existir)
    driver.execute_script(f"document.getElementById('painel_copia_cola_conteudo').innerText = `{conteudo}`;")
    if log:
        print('[Fix.py] Painel Copia e Cola exibido.')
      
# Seção: Manipulaçao de intimações
# Função para preencher campos de prazo
def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    # Preenche todos os campos de prazo (input[type=text].mat-input-element) dentro do formulário de minuta/comunicação.
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

def preencher_primeiro_input(driver, valor, seletor='input[type="text"]', timeout=10, log=True):
    # Preenche o primeiro input de texto visível encontrado pelo seletor informado.
    try:
        campo = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor))
        )
        campo.clear()
        campo.send_keys(str(valor))
        driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
        driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
        if log:
            print(f'[Fix.py] Primeiro input preenchido com: {valor}')
        return True
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao preencher primeiro input: {e}')
        return False


def marcar_checkbox_por_label(driver, texto_label, timeout=10, log=True):
    # Marca/desmarca checkbox com base no texto do label associado (robusto para checkboxes customizados).
    try:
        labels = driver.find_elements(By.TAG_NAME, 'label')
        for label in labels:
            if texto_label.strip().lower() in label.text.strip().lower():
                checkbox = label.find_element(By.XPATH, './/preceding-sibling::input[@type="checkbox"] | .//input[@type="checkbox"]')
                driver.execute_script('arguments[0].scrollIntoView(true);', checkbox)
                checkbox.click()
                if log:
                    print(f'[Fix.py] Checkbox marcado/desmarcado: {texto_label}')
                return True
        if log:
            print(f'[Fix.py] Checkbox com label "{texto_label}" não encontrado.')
        return False
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao marcar checkbox: {e}')
        return False


def selecionar_opcao_select(driver, seletor_select, texto_opcao, timeout=10, log=True):
    # Seleciona uma opção em <select> tradicional pelo texto visível.
    try:
        select = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_select))
        )
        for option in select.find_elements(By.TAG_NAME, 'option'):
            if texto_opcao.strip().lower() in option.text.strip().lower():
                option.click()
                if log:
                    print(f'[Fix.py] Opção selecionada: {texto_opcao}')
                return True
        if log:
            print(f'[Fix.py] Opção "{texto_opcao}" não encontrada em {seletor_select}')
        return False
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao selecionar opção: {e}')
        return False

# Seção: Ferramentas
def criar_gigs(driver, dias_uteis, observacao, tela='principal', timeout=10, log=True):
    # Cria GIGS em qualquer tela (principal ou minuta), parametrizável.
    # tela: 'principal' (default) ou 'minuta' para lógica adaptada.
    import datetime
    t0 = time.time()
    if log:
        print(f"[GIGS] Iniciando criação de GIGS: {dias_uteis}/{observacao} (tela={tela}) [{datetime.datetime.now().strftime('%H:%M:%S')}] (T0)")
    try:
        # Fecha modal de GIGS aberto, se houver
        modais = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container')
        for modal in modais:
            if modal.is_displayed():
                try:
                    btn_cancelar = modal.find_element(By.XPATH, ".//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cancelar')]")
                    if btn_cancelar.is_displayed():
                        btn_cancelar.click()
                        time.sleep(0.7)
                        if log:
                            print('[GIGS] Modal de GIGS anterior fechado (Cancelar).')
                        break
                except Exception:
                    pass
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.7)
                    if log:
                        print('[GIGS] Modal de GIGS anterior fechado (ESC).')
                        break
                except Exception:
                    pass
        # --- NOVO FLUXO MAISPJE ---
        if tela == 'minuta':
            if '/minutar' not in driver.current_url:
                if log:
                    print(f'[GIGS][ERRO] Não está na tela de minuta! URL atual: {driver.current_url}')
                return False
            if log:
                print('[GIGS][MINUTA] Confirmação: na tela de minuta.')
            # NOVO: dois cliques antes de abrir o formulário de atividade
            try:
                btn_bars = driver.find_element(By.CSS_SELECTOR, '.fa-bars')
                btn_bars.click()
                if log:
                    print('[GIGS][MINUTA] Clique em .fa-bars realizado.')
                time.sleep(0.7)
                btn_tag = driver.find_element(By.CSS_SELECTOR, '.icone-descricao > span:nth-child(1) > i.fa-tag')
                btn_tag.click()
                if log:
                    print('[GIGS][MINUTA] Clique em .fa-tag realizado.')
                time.sleep(0.7)
            except Exception as e:
                if log:
                    print(f'[GIGS][MINUTA][ERRO] Falha nos cliques iniciais (.fa-bars/.fa-tag): {e}')
                return False
        else:
            # 1. Garante que o GIGS está aberto
            try:
                btn_mostrar_gigs = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Mostrar o GIGS"]')
                if btn_mostrar_gigs.is_displayed():
                    btn_mostrar_gigs.click()
                    time.sleep(1.2)
                    if log:
                        print('[GIGS] GIGS aberto via botão "Mostrar o GIGS".')
            except Exception:
                pass  # Se não existe, já está aberto
            # 2. Clica no botão "Nova atividade" dentro de pje-gigs-lista-atividades
            nova_atividade_btn = None
            try:
                lista_atividades = driver.find_element(By.CSS_SELECTOR, 'pje-gigs-lista-atividades')
                botoes = lista_atividades.find_elements(By.TAG_NAME, 'button')
                for btn in botoes:
                    if btn.is_displayed() and 'nova atividade' in btn.text.strip().lower():
                        nova_atividade_btn = btn
                        break
            except Exception:
                pass
            if nova_atividade_btn:
                nova_atividade_btn.click()
                time.sleep(1.2)
            else:
                if log:
                    print(f'[GIGS][ERRO] Botão "Nova atividade" não encontrado dentro de pje-gigs-lista-atividades!')
                return False
        # Espera o formulário de GIGS abrir
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'form'))
        )
        # time.sleep(0.7)  # Removido: WebDriverWait já garante carregamento
        # Preenche Dias Úteis (MaisPje: input[formcontrolname="dias"])
        campo_dias = None
        tentativas = 0
        max_tentativas = int(timeout * 5)  # tenta por até 'timeout' segundos, a cada 0.2s
        while tentativas < max_tentativas and not campo_dias:
            try:
                campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
                if campo_dias.is_displayed() and campo_dias.is_enabled():
                    break
            except Exception:
                pass
            # Alternativa: busca por input[type="number"] visível
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="number"]')
                for inp in inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        campo_dias = inp
                        break
            except Exception:
                pass
            if not campo_dias:
                if log:
                    print(f'[GIGS][WAIT] Campo de dias úteis não disponível, tentativa {tentativas+1}/{max_tentativas}...')
                time.sleep(0.2)  # Mais responsivo
            tentativas += 1
        if not campo_dias:
            if log:
                print('[GIGS][ERRO] Campo de dias úteis (input[formcontrolname="dias"]) não encontrado após múltiplas tentativas!')
            return False
        campo_dias.clear()
        # time.sleep(0.3)  # Removido: não necessário após clear
        campo_dias.send_keys(str(dias_uteis))
        if log:
            print(f'[GIGS] Dias úteis preenchido: {dias_uteis}')
        # time.sleep(0.7)  # Removido: não necessário após preenchimento
        # Preenche Observação (MaisPje: textarea[formcontrolname="observacao"])
        campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
        campo_obs.clear()
        time.sleep(0.3)
        campo_obs.send_keys(observacao)
        if log:
            print(f'[GIGS] Observação preenchida: {observacao}')
        time.sleep(0.7)
        # Clica no botão Salvar
        botoes_salvar = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
        btn_salvar = None
        for btn in botoes_salvar:
            if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                btn_salvar = btn
                break
        if not btn_salvar:
            if log:
                print(f'[GIGS][ERRO] Botão Salvar não encontrado!')
            return False
        btn_salvar.click()
        if log:
            print(f'[GIGS] Botão Salvar clicado.')
        time.sleep(2.5)
        if log:
            print(f'[GIGS] GIGS criado com sucesso!')
        return True
    except Exception as e:
        if log:
            print(f'[GIGS][ERRO] Falha ao criar GIGS: {e}')
        return False

def Infojud(ni, log=True):
    # Gera link de consulta Infojud (CPF/CNPJ) e imprime/loga.
    ni = str(ni).strip()
    link = None
    if len(ni) == 11:
        link = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI={ni}"
    elif len(ni) == 14:
        link = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI={ni}"
    if log:
        print(f"[INFOJUD] Link para consulta: {link if link else 'NI inválido'}")
    return link

# Seção: Mandados Argos (Pesquisa Patrimonial)

def buscar_documentos_sequenciais(driver, log=True):
    # Placeholder para buscar_documentos_sequenciais (pode ser expandido conforme regras do fluxo).
    if log:
        print('[Fix.py] buscar_documentos_sequenciais chamado.')
    # Implementação futura conforme regras do fluxo
    pass

def tratar_anexos(certidao, driver, log=True):
    # Trata anexos da certidão: abre cada anexo, aplica sigilo/visibilidade se for INFOJUD, IRPF, DOI;
    # se for SISBAJUD (positivo/parcial/integral), apenas loga e registra bloqueio.
    # Retorna True se algum bloqueio SISBAJUD for registrado.
    bloqueio_registrado = False
    try:
        anexos = []
        linhas = certidao.text.splitlines()
        for l in linhas:
            if "Anexo(s):" in l:
                idx = linhas.index(l)
                anexos = linhas[idx+1:]
                break
        if not anexos:
            for l in linhas:
                if l.strip().startswith("- "):
                    anexos.append(l.strip())
        if log:
            print(f"[ANEXOS][DETALHE] {len(anexos)} anexos detectados na certidão de devolução.")
        for idx, texto in enumerate(anexos):
            if log:
                print(f"[ANEXOS][{idx+1}/{len(anexos)}] Conteúdo: '{texto}'")
            texto_lower = texto.lower()
            if any(p in texto_lower for p in ["infojud", "irpf", "doi", "sisbajud"]):
                strongs = certidao.find_elements(By.TAG_NAME, 'strong')
                alvo = None
                for s in strongs:
                    if s.text.strip() in texto:
                        alvo = s
                        break
                if alvo:
                    alvo.click()
                    time.sleep(0.7)
                    if any(p in texto_lower for p in ["infojud", "irpf", "doi"]):
                        try:
                            btn_sigilo = certidao.find_element(By.CSS_SELECTOR, "i.fa-wpexplorer")
                            btn_sigilo.click()
                            time.sleep(0.5)
                            btn_visibilidade = certidao.find_element(By.CSS_SELECTOR, "i.fa-plus")
                            if btn_visibilidade.is_displayed():
                                btn_visibilidade.click()
                                time.sleep(0.5)
                                modal_contexto = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-content")
                                btn_coluna = modal_contexto.find_element(By.CSS_SELECTOR, "i.botao-icone-titulo-coluna")
                                btn_coluna.click()
                                time.sleep(0.3)
                                btn_salvar = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-actions > button:nth-child(1) > span:nth-child(1)")
                                btn_salvar.click()
                                if log:
                                    print(f"[ANEXOS][{idx+1}] Sigilo e visibilidade aplicados com sucesso no anexo '{texto}'.")
                                modal_contexto.send_keys(Keys.ESCAPE)
                                if log:
                                    print("[MODAL] Fechado com ESC.")
                                time.sleep(1)
                            else:
                                if log:
                                    print(f"[ANEXOS][{idx+1}] Botão de visibilidade não visível para o anexo '{texto}'.")
                        except Exception as e:
                            if log:
                                print(f"[ERRO] Ao inserir sigilo/visibilidade em anexo '{texto}': {e}")
                    if "sisbajud" in texto_lower and any(p in texto_lower for p in ["positivo", "parcial", "integral"]):
                        if log:
                            print(f"[REGISTRO BLOQUEIO] SISBAJUD encontrado: {texto}. Bloqueio POSITIVO registrado.")
                        bloqueio_registrado = True
                else:
                    if log:
                        print(f"[ANEXOS][{idx+1}] Não foi possível localizar o elemento visual do anexo '{texto}'.")
    except Exception as e:
        if log:
            print(f"[ANEXOS][ERRO] Falha ao localizar ou processar anexos da certidão: {e}")
        return False
    return bloqueio_registrado

def fechar_prazo(driver, log=True):
    # Fecha prazo de intimação:
    # 1. Clica no envelope (intimação)
    # 2. Marca checkbox
    # 3. Clica em OK
    # 4. Confirma no modal
    try:
        if log:
            print("[PRAZO] Iniciando fechamento de prazo...")
            
        # 1. Clica no envelope (intimação)
        btn_envelope = esperar_elemento(
            driver,
            "i.fa-envelope.fa-lg.icone-cinza",
            timeout=5,
            log=log
        )
        if not btn_envelope:
            raise Exception("Botão de intimação não encontrado")
            
        safe_click(driver, btn_envelope)
        time.sleep(1)
        
        # 2. Marca checkbox
        modal = esperar_elemento(
            driver,
            ".flex-container-raiz, .mat-dialog-container",
            timeout=5,
            log=log
        )
        if not modal:
            raise Exception("Modal de intimação não encontrado")
            
        checkbox = modal.find_element(By.CSS_SELECTOR, ".mat-checkbox-inner-container-no-side-margin")
        safe_click(driver, checkbox)
        time.sleep(0.5)
        
        # 3. Clica em OK
        btn_ok = modal.find_element(By.CSS_SELECTOR, ".mat-raised-button > span")
        safe_click(driver, btn_ok)
        time.sleep(0.5)
        
        # 4. Confirma no modal
        modal_confirmacao = esperar_elemento(
            driver,
            ".mat-dialog-actions > button:nth-child(1) > span:nth-child(1)",
            timeout=5,
            log=log
        )
        if modal_confirmacao:
            safe_click(driver, modal_confirmacao)
            time.sleep(0.5)
        
        if log:
            print("[PRAZO] Prazo fechado com sucesso")
            
    except Exception as e:
        if log:
            print(f"[PRAZO][ERRO] Falha ao fechar prazo: {e}")
        raise
def analise_argos(driver):
    # Fluxo robusto para análise de mandados do tipo Argos (Pesquisa Patrimonial).
    # - Trata anexos SISBAJUD.
    # - Extrai trecho relevante do PDF se necessário.
    # - Executa lógica adicional de Argos (placeholder para regras futuras).
    print('[ARGOS] Iniciando análise Argos...')
    try:
        resultado_sisbajud = tratar_anexos_sisbajud(driver)
        if resultado_sisbajud == 'nao_encontrado':
            texto_pdf = extrair_texto_pdf_por_conteudo(driver, termo='sisbajud')
            print(f'[PDF][ARGOS] Trecho extraído: {texto_pdf}')
        # Placeholder para lógica Argos adicional
        print('[ARGOS] Análise Argos concluída.')
    except Exception as e:
        print(f'[ARGOS][ERRO] Falha na análise Argos: {e}')

def buscar_documento_argos(driver, log=True):
    # Busca e extrai documento específico para Argos:
    # 1. Procura primeiro despacho ou decisão
    # 2. Se for decisão, extrai e retorna
    # 3. Se for despacho, verifica conteúdo e:
    # - Se contém "EM QUE PESE A AUSÊNCIA", extrai e retorna
    # - Senão, busca próxima decisão após o despacho
    # Retorna: tupla (texto, tipo) onde tipo é 'decisao' ou 'despacho'
    import re
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
                    return (texto, 'decisao')
                    
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
        return (None, None)


def buscar_ultimo_despacho_juiz(driver, log=True):
    # Busca o último despacho de Mariana ou Otávio na timeline do processo.
    # Retorna o texto do despacho e a data.
    try:
        # Espera e encontra todos os itens da timeline
        itens_timeline = esperar_colecao(driver, "li.tl-item-container", qtde_minima=1, timeout=10, log=log)
        
        # Procura o último despacho de Mariana ou Otávio
        for item in reversed(itens_timeline):
            texto = item.text.lower()
            if any(j in texto for j in ['mariana', 'otávio', 'otavio']):
                # Encontra a data
                data_element = item.find_elements(By.CSS_SELECTOR, "time")
                data = data_element[0].text if data_element else "Data não encontrada"
                
                # Extrai o conteúdo do despacho
                conteudo = item.text
                
                if log:
                    print(f'[DESPACHO] Encontrado despacho de juiz: {data}')
                
                return {
                    'data': data,
                    'conteudo': conteudo
                }
        
        if log:
            print('[DESPACHO] Não encontrado despacho de juiz na timeline.')
        return None
        
    except Exception as e:
        if log:
            print(f'[DESPACHO][ERRO] Falha ao buscar despacho: {e}')
        return None

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

def indexar_lista_processos(driver, seletor_linha='tr.cdk-drag', logar_termo_observacao=False, termo_chave='xs'):
    # Indexa os processos visíveis na lista, extraindo número e link.
    # Retorna uma lista de dicionários: [{'numero': '...', 'link_element': element, 'termo_obs': '...'}]
    # Se logar_termo_observacao=True, também loga o termo após 'xs' na coluna Observações.
    """
    Indexa os processos visíveis na lista, extraindo número e link.
    Retorna uma lista de dicionários: [{'numero': '...', 'link_element': element, 'termo_obs': '...'}]
    Se logar_termo_observacao=True, também loga o termo após 'xs' na coluna Observações.
    """
    import re
    linhas = driver.find_elements(By.CSS_SELECTOR, seletor_linha)
    print(f'[INDEXAR] Total de processos encontrados: {len(linhas)}')
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
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
            if logar_termo_observacao:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                termo = ''
                if len(tds) >= 10:
                    obs = tds[9].text.strip()
                    if obs.lower().startswith(termo_chave):
                        termo = obs[len(termo_chave):].strip()
                print(f'[INDEXAR] {idx+1:02d}: {num_proc} | TERMO: {termo}')
            else:
                print(f'[INDEXAR] {idx+1:02d}: {num_proc}')
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e}')

def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    # Indexa (conta/loga) os processos e já executa o processamento sequencial, com logs claros.
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
    indexar_lista_processos(driver, logar_termo_observacao=False)
    print('[FLUXO] Indexação concluída. Iniciando processamento da lista de processos...', flush=True)
    # Após abrir a aba de detalhes, pressiona TAB para tentar restaurar o cabeçalho
    from selenium.webdriver.common.keys import Keys
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
        print('[WORKAROUND] Pressionada tecla TAB para tentar restaurar cabeçalho da aba detalhes.')
    except Exception as e:
        print(f'[WORKAROUND][ERRO] Falha ao pressionar TAB: {e}')
    # Chama criar_botoes_detalhes antes de processar a lista
    criar_botoes_detalhes()
    processar_lista_processos(driver, callback, seletor_btn=seletor_btn, modo=modo, max_processos=max_processos, log=log)
    print('[FLUXO] Fim do processamento da lista de processos.', flush=True)

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

# Função auxiliar para tratar anexos do SISBAJUD
def tratar_anexos_sisbajud(driver, log=True):
    # Trata especificamente anexos do SISBAJUD.
    # Retorna: 'encontrado' se encontrou e tratou, 'nao_encontrado' se não achou
    try:
        anexos = driver.find_elements(By.CSS_SELECTOR, '.anexo')
        for anexo in anexos:
            if 'sisbajud' in anexo.text.lower():
                if log:
                    print('[SISBAJUD] Anexo encontrado')
                return 'encontrado'
        return 'nao_encontrado'
    except Exception as e:
        if log:
            print(f'[SISBAJUD][ERRO] {e}')
        return 'nao_encontrado'

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
# 2. FUNÇÕES DE INTERAÇÃO PJe (Movidas/Adaptadas)
# =========================

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Seleciona '100' no filtro de itens por página do painel global.
def aplicar_filtro_100(driver):
   
    # Aplica o filtro para exibir 100 itens por página no painel global.
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    try:
        # Aguarda pelo menos uma linha da tabela de atividades estar visível antes de clicar no filtro
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
            )
            print('[FILTRO][DEBUG] Tabela de atividades carregada (tr.cdk-drag visível).')
        except Exception:
            print('[FILTRO][ERRO] Tabela de atividades não carregou a tempo.')
            return False

        # Encontra todos os spans de linhas por página
        spans = driver.find_elements(By.CSS_SELECTOR, "span.mat-select-min-line")
        seletor = None
        for s in reversed(spans):
            if s.is_displayed():
                # Sobe para o div.mat-select-value pai
                parent_div = s.find_element(By.XPATH, "./ancestor::div[contains(@class,'mat-select-value')]")
                if parent_div and parent_div.is_displayed():
                    seletor = parent_div
                    break
        if not seletor:
            print('[FILTRO][ERRO] Nenhum seletor de linhas por página visível encontrado.')
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", seletor)
        seletor.click()
        print('[FILTRO] Dropdown de linhas por página clicado (div.mat-select-value).')
        time.sleep(0.7)

        # Aguarda o overlay do dropdown aparecer
        try:
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )
            print('[FILTRO][DEBUG] Overlay do dropdown detectado.')
        except Exception:
            print('[FILTRO][ERRO] Overlay do dropdown não detectado.')
            return False

        # Busca apenas opções "100" dentro do overlay aberto
        opcoes = overlay.find_elements(By.XPATH, ".//span[contains(text(), '100')]")
        print(f'[FILTRO][DEBUG] Encontradas {len(opcoes)} opções "100" dentro do overlay.')
        clicou = False
        for idx, opcao in enumerate(opcoes):
            try:
                if opcao.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                    opcao.click()
                    print(f'[FILTRO] Selecionado 100 itens por página. Clique funcionou em opção #{idx+1} dentro do overlay.')
                    time.sleep(1)
                    clicou = True
                    break
                else:
                    print(f'[FILTRO][DEBUG] Opção #{idx+1} não está visível.')
            except Exception as e:
                print(f'[FILTRO][WARN] Falha ao clicar na opção #{idx+1} (100) dentro do overlay: {e}')
        if not clicou:
            print('[FILTRO][ERRO] Opção 100 não encontrada entre as opções visíveis no overlay.')
            return False
        return True
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha ao aplicar filtro 100: {e}')
        return False

def copiarDOC(driver, id):
    # Função para copiar o conteúdo do documento ativo no PJe.
    # Args:
    # driver: WebDriver instance.
    # id: Identificador do documento a ser copiado.
    # Returns:
    # None
    try:
        # Localiza o elemento do documento ativo
        documento = driver.find_element(By.CSS_SELECTOR, f'div[class*="cabecalho-direita"] [id="{id}"]')
        if documento:
            conteudo = documento.text
            pyperclip.copy(conteudo)
            print("Conteúdo copiado para a área de transferência.")
        else:
            print("Documento não encontrado.")
    except Exception as e:
        print(f"Erro ao copiar o documento: {str(e)}")

# Função para criar e acionar prazos em lote em telas de minuta.
def pz_minuta(driver):
    import time

    def executar(prazo_em_lote):
        # Executa a aplicação do prazo em lote.
        # Args:
        # prazo_em_lote (str): Prazo em dias úteis.
        elementos = driver.find_elements(By.CSS_SELECTOR, 'mat-form-field[class*="prazo"]')
        if not elementos:
            print("Nenhum campo de prazo encontrado.")
            return

        for elemento in elementos:
            input_field = elemento.find_element(By.TAG_NAME, "input")
            input_field.clear()
            input_field.send_keys(prazo_em_lote)

        # Simula o clique no botão "Gravar"
        gravar_button = driver.find_element(By.XPATH, '//button[contains(text(), "Gravar")]')
        gravar_button.click()
        print(f"Prazo de {prazo_em_lote} dias aplicado com sucesso.")

    # Exemplo de uso
    prazos = ["0", "2", "5", "8", "10", "15"]
    for prazo in prazos:
        executar(prazo)

    # Para prazos personalizados
    prazo_personalizado = input("Digite o prazo em dias úteis:")
    executar(prazo_personalizado)

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
        destinatarios = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-list-option'))) # Usar tupla para By

        for dest in destinatarios:
            nome_dest = dest.text.lower()
            if nome_parcial.lower() in nome_dest:
                # Verifica se já está selecionado
                if dest.get_attribute('aria-selected') != 'true':
                    safe_click(driver, dest)
                    print(f'[DEST] Destinatário "{nome_dest}" selecionado.')
                else:
                    print(f'[DEST] Destinatário "{nome_dest}" já estava selecionado.')
                return True
        print(f'[DEST][ERRO] Nenhum destinatário encontrado contendo "{nome_parcial}".')
        return False
    except Exception as e:
        print(f'[DEST][ERRO] Falha ao selecionar destinatário: {e}')
        return False

def tratar_anexos_infojud_irpf_doi_sisbajud(driver, wait):
    # Marca checkboxes de anexos específicos se presentes.
    termos = ['infojud', 'irpf', 'doi', 'sisbajud']
    try:
        # Espera os checkboxes carregarem (ajuste o seletor se necessário)
        checkboxes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-checkbox label'))) # Usar tupla para By

        for checkbox_label in checkboxes:
            texto_label = checkbox_label.text.lower()
            # Verifica se algum dos termos está no texto do label
            if any(termo in texto_label for termo in termos):
                # Encontra o input checkbox associado
                checkbox_input = checkbox_label.find_element(By.XPATH, './preceding-sibling::div/input[@type="checkbox"]')
                # Marca se não estiver marcado
                if not checkbox_input.is_selected():
                    safe_click(driver, checkbox_label) # Clica no label para marcar
                    print(f'[ANEXO] Checkbox "{checkbox_label.text}" marcado.')
    except TimeoutException:
        print('[ANEXO] Checkboxes não encontrados ou não carregaram a tempo.')
    except Exception as e:
        print(f'[ANEXO][ERRO] Falha ao tratar anexos: {e}')

def selecionar_tipo_expediente(driver, texto):
    # Seleciona o tipo de expediente pelo texto.
    try:
        # Clica no dropdown de tipo de expediente
        dropdown = esperar_elemento(driver, 'mat-select[formcontrolname="tipoExpediente"]', timeout=10)
        if not dropdown:
            print('[TIPO EXP] Dropdown não encontrado.')
            return False
        safe_click(driver, dropdown)

        # Espera as opções aparecerem e clica na opção desejada
        xpath_opcao = f"//mat-option[contains(., '{texto}')]"
        opcao = esperar_elemento(driver, (By.XPATH, xpath_opcao), timeout=10) # Usar tupla para By
        if not opcao:
            print(f'[TIPO EXP] Opção "{texto}" não encontrada.')
            # Tenta fechar o dropdown se a opção não foi encontrada
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except: pass
            return False

        safe_click(driver, opcao)
        print(f'[TIPO EXP] Tipo de expediente "{texto}" selecionado.')
        return True
    except Exception as e:
        print(f'[TIPO EXP][ERRO] Falha ao selecionar tipo de expediente: {e}')
        return False

def buscar_documentos_sequenciais(driver):
    # Busca documentos sequenciais na árvore e os seleciona.

    try:
        arvore = esperar_elemento(driver, 'pje-arvore-documento', timeout=15)
        if not arvore:
            print('[DOC SEQ] Árvore de documentos não encontrada.')
            return False

        # Encontra todos os nós da árvore
        # Usar um seletor mais específico se possível, ex: '.node-name', '.mat-tree-node span'
        nos_texto = arvore.find_elements(By.CSS_SELECTOR, '.node-content-wrapper span') # Exemplo de seletor

        documentos_encontrados = []
        padrao = re.compile(r"^(\d+)\s*-\s*(.+)") # Padrão: número - texto

        for no in nos_texto:
            texto_no = no.text.strip()
            match = padrao.match(texto_no)
            if match:
                numero = int(match.group(1))
                descricao = match.group(2)
                documentos_encontrados.append({'numero': numero, 'descricao': descricao, 'elemento': no})
                print(f'[DOC SEQ] Documento potencial encontrado: {texto_no}')

        if not documentos_encontrados:
            print('[DOC SEQ] Nenhum documento com padrão número-descrição encontrado.')
            return False

        # Ordena por número
        documentos_encontrados.sort(key=lambda x: x['numero'])

        # Verifica sequencialidade e seleciona
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
                    print(f'[DOC SEQ][WARN] Não foi possível encontrar/clicar no checkbox para os docs {doc_atual["numero"]}/{doc_proximo["numero"]}: {e}')

        if not selecionou_algum:
            print('[DOC SEQ] Nenhuma sequência válida encontrada ou checkboxes já marcados/não encontrados.')

        return selecionou_algum

    except TimeoutException:
        print('[DOC SEQ] Árvore de documentos não carregou a tempo.')
        return False
    except Exception as e:
        print(f'[DOC SEQ][ERRO] Falha ao buscar documentos sequenciais: {e}')
        return False

def esperar_url_conter(driver, fragmento_url, timeout=10):
    # Espera até que a URL atual contenha o fragmento especificado.
    try:
        WebDriverWait(driver, timeout).until(
            EC.url_contains(fragmento_url)
        )
        print(f'[URL WAIT] URL agora contém: "{fragmento_url}"')
        return True
    except TimeoutException:
        print(f'[URL WAIT][ERRO] Timeout esperando URL conter: "{fragmento_url}". URL atual: {driver.current_url}')
        return False
    except Exception as e:
        print(f'[URL WAIT][ERRO] Erro inesperado: {e}')
        return False

class EditorTextoPJe:
    # ... (código existente da classe) ...

    def preencher_campo(self, seletor, valor):
        """Preenche um campo de input/textarea."""
        try:
            campo = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor))) # Usar tupla para By
            campo.clear()
            campo.send_keys(valor)
            print(f'[EDITOR] Campo "{seletor}" preenchido.')
        except Exception as e:
            print(f'[EDITOR][ERRO] Falha ao preencher campo "{seletor}": {e}')

    def selecionar_opcao_dropdown(self, seletor_dropdown, texto_opcao):
         """Seleciona uma opção em um dropdown mat-select."""
         try:
             dropdown = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_dropdown))) # Usar tupla para By
             dropdown.click()
             xpath_opcao = f"//mat-option[contains(., '{texto_opcao}')]"
             opcao = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath_opcao))) # Usar tupla para By
             opcao.click()
             print(f'[EDITOR] Opção "{texto_opcao}" selecionada em "{seletor_dropdown}".')
         except Exception as e:
             print(f'[EDITOR][ERRO] Falha ao selecionar dropdown "{seletor_dropdown}": {e}')

    def configurar_documento(self, tipo_documento, nome_documento, modelo_nome): # Adicionado parâmetro tipo_documento
        """Configura tipo, nome e modelo do documento."""
        print('[EDITOR] Configurando documento...')
        # self.preencher_campo('input[aria-label="Tipo de Documento"]', tipo) # Linha original com erro
        self.preencher_campo('input[aria-label*="Tipo de Documento"]', tipo_documento) # Corrigido: usa parâmetro e seletor mais robusto
        self.preencher_campo('input[aria-label="Descrição"]', nome_documento)
        self.selecionar_modelo(modelo_nome)

    # ... (restante da classe) ...

def verificar_destinatario_juizo(driver):
    """Verifica se 'Juízo' está entre os destinatários e o seleciona se não estiver."""
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

def verificar_prioridade_processual(driver):
    """Verifica se existe um chip 'Prioridade processual' e se 'Otavio' ou 'Mariana' estão no tooltip."""
    try:
        chips_prioridade = driver.find_elements(By.CSS_SELECTOR, 'mat-chip-list mat-chip')
        for chip in chips_prioridade:
            if 'prioridade processual' in chip.text.lower():
                tooltip = chip.get_attribute('mattooltip')
                if tooltip:
                    aria = tooltip.lower()
                    if 'otavio' in aria or 'mariana' in aria:
                        print('[PRIORIDADE] Prioridade processual encontrada (Otavio/Mariana).')
                        return True
                else:
                    chip_text_lower = chip.text.lower()
                    if 'otavio' in chip_text_lower or 'mariana' in chip_text_lower:
                        print('[PRIORIDADE] Prioridade processual encontrada no texto do chip (Otavio/Mariana).')
                        return True

        print('[PRIORIDADE] Nenhuma prioridade processual relevante (Otavio/Mariana) encontrada.')
        return False
    except Exception as e:
        print(f'[PRIORIDADE][ERRO] Falha ao verificar prioridade: {e}')
        return False

def verificar_documento_decisao_sentenca(driver):
    """Verifica se existe um documento com 'decisão' ou 'sentença' no nome."""
    try:
        seletor_nomes_docs = 'pje-arvore-documento .node-content-wrapper span'
        nomes_docs = driver.find_elements(By.CSS_SELECTOR, seletor_nomes_docs)

        for nome_element in nomes_docs:
            doc_text = nome_element.text.lower()
            if 'decisão' in doc_text or 'sentença' in doc_text:
                print(f'[DOC CHECK] Documento encontrado: "{nome_element.text}"')
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

def criar_botoes_detalhes():
    """
    Creates buttons with specific icons and actions, replicating the functionality from MaisPje.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # Use the standardized driver instance
    driver = obter_driver_padronizado()

    try:
        base_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pjextension_bt_detalhes_base"))
        )
    except:
        base_element = driver.find_element(By.TAG_NAME, "body")

    # Create the container div if it doesn't exist
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

    # Define button configurations
    buttons = [
        {"title": "Abrir o Gigs", "icon": "fa fa-tag", "action": "abrir_gigs"},
        {"title": "Expedientes", "icon": "fa fa-envelope", "action": "acao_botao_detalhes('Expedientes')"},
        {"title": "Lembretes", "icon": "fas fa-thumbtack", "action": "acao_botao_detalhes('Lembretes')"},
    ]

    # Add buttons to the container
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
    # NOVO: Força a atualização da posição dos botões
    driver.execute_script(
        "setTimeout(function() {"
        "  var div = document.getElementById('pjextension_bt_detalhes_base');"
        "  if (div) { div.style.display='none'; div.offsetHeight; div.style.display=''; }"
        "}, 100);"
    )

