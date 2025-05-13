import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random

# Configurações do Chrome para evitar detecção
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--window-size=1366,768')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')

# Função para digitação humana
def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.07, 0.25))

# Função para clique humano
def human_click(driver, element):
    actions = ActionChains(driver)
    actions.move_to_element(element).pause(random.uniform(0.2, 1.2)).click().perform()

# Função principal de login humanizado no PJe TRT2

def login_humano_pje(usuario, senha):
    driver = uc.Chrome(options=options)
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    time.sleep(random.uniform(1.2, 2.5))
    # Scroll leve para simular humano
    driver.execute_script('window.scrollBy(0, 100)')
    time.sleep(random.uniform(0.7, 1.7))
    try:
        # Clicar no botão SSO PDPJ
        btn_sso = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, 'btnSsoPdpj'))
        )
        human_click(driver, btn_sso)
        time.sleep(random.uniform(1, 2))
        # Preencher usuário
        campo_usuario = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'username'))
        )
        human_click(driver, campo_usuario)
        time.sleep(random.uniform(0.3, 0.7))
        human_type(campo_usuario, usuario)
        time.sleep(random.uniform(0.5, 1.2))
        campo_usuario.send_keys(Keys.TAB)
        time.sleep(random.uniform(0.3, 0.7))
        # Preencher senha
        campo_senha = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'password'))
        )
        human_click(driver, campo_senha)
        time.sleep(random.uniform(0.3, 0.7))
        human_type(campo_senha, senha)
        time.sleep(random.uniform(0.5, 1.2))
        # Submeter com Enter
        campo_senha.send_keys(Keys.ENTER)
        print('[LOGIN][HUMANO] Login submetido com Enter.')
        # Espera página carregar
        time.sleep(random.uniform(2, 4))
        # Verifica se há captcha
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

# Exemplo de uso:
# driver = login_humano_pje('SEU_USUARIO', 'SUA_SENHA')
# if driver:
#     # siga com sua automação normalmente
#     pass
