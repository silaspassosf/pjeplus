# m1t.py - Versão customizada de m1.py para ambiente e caminhos específicos
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Fix import (
    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    safe_click,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    login_notebook,
    indexar_e_processar_lista,
    extrair_dados_processo,
    buscar_documento_argos,
    buscar_mandado_autor,
    buscar_ultimo_mandado,
)
from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj
)

# --- Configurações customizadas ---
FIREFOX_PROFILE_PATH = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2y17wq63.default'
FIREFOX_EXECUTABLE_PATH = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
GECKODRIVER_PATH = r'C:\Users\s164283\Desktop\pjeplus\geckodriver.exe'
LOGIN_AHK_PATH = r'C:\Users\s164283\Desktop\pjeplus\Login.ahk'
DADOS_ATUAIS_PATH = r'C:\Users\s164283\Desktop\pjeplus\dadosatuais.json'
AHK_ROOT = r'C:\Users\s164283\Desktop\pjeplus\AHK\UX'

def setup_driver():
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    options.binary_location = FIREFOX_EXECUTABLE_PATH
    options.profile = FIREFOX_PROFILE_PATH
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(
        options=options,
        service=service
    )
    return driver

def login_pc(driver):
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
        time.sleep(1)
        subprocess.Popen([os.path.join(AHK_ROOT, 'AutoHotkey.exe'), LOGIN_AHK_PATH])
        print("[INFO] Script AutoHotkey chamado para digitar a senha.")
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

def main():
    driver = setup_driver()
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_pc(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        return
    print('[M1T] Login realizado com sucesso.')
    # Chame aqui a função principal do fluxo, por exemplo:
    # fluxo_mandados(driver)  # Substitua pelo nome correto da função principal do seu m1.py

if __name__ == "__main__":
    main()
