import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from dotenv import load_dotenv
from Minuta import pec_cpgeral

PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"

def login_automatico_cp(driver, usuario, senha):
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    campo_usuario = driver.find_element(By.CSS_SELECTOR, 'input#username')
    campo_usuario.clear()
    campo_usuario.send_keys(usuario)
    time.sleep(1)
    campo_senha = driver.find_element(By.CSS_SELECTOR, 'input#password')
    campo_senha.clear()
    campo_senha.send_keys(senha)
    time.sleep(1)
    btn_entrar = driver.find_element(By.CSS_SELECTOR, 'button#btnEntrar')
    time.sleep(1)
    btn_entrar.click()
    time.sleep(3)
    print('[LOGIN][CP] Login realizado com sucesso.')
    return True

def main():
    load_dotenv()
    usuario = os.environ.get("PJE_USUARIO")
    senha = os.environ.get("PJE_SENHA")
    if not usuario:
        usuario = input("Usuário PJe: ")
    if not senha:
        senha = input("Senha PJe: ")
    options = Options()
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service()
    driver = webdriver.Firefox(service=service, options=options)
    try:
        if not login_automatico_cp(driver, usuario, senha):
            print('[LOGIN][ERRO] Falha no login automático. Encerrando script.')
            driver.quit()
            return
        driver.get("https://pje.trt2.jus.br/pjekz/processo/7161365/detalhe")
        time.sleep(3)
        pec_cpgeral(driver)
        print("[TESTE] Execução de pec_cpgeral concluída.")
        input("Pressione Enter para sair e fechar o navegador...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
