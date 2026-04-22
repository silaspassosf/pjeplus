import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_login - Módulo de autenticação e login para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import os
import time
from selenium.webdriver.common.by import By
from .utils_cookies import USAR_COOKIES_AUTOMATICO, SALVAR_COOKIES_AUTOMATICO
from .utils_paths import (
    obter_caminho_perfil_firefox,
    obter_caminho_firefox_executavel
)

# Seção: Navegação
# Configurações do navegador - agora obtidas via credenciais
PROFILE_PATH = obter_caminho_perfil_firefox()
FIREFOX_BINARY = obter_caminho_firefox_executavel()

def login_manual(driver, aguardar_url_painel=True):
    """Login manual: navega para login e aguarda usuário fazer login"""
    from .utils_cookies import verificar_e_aplicar_cookies, salvar_cookies_sessao, USAR_COOKIES_AUTOMATICO

    if verificar_e_aplicar_cookies(driver):
        if USAR_COOKIES_AUTOMATICO:
            salvar_cookies_sessao(driver, info_extra='cookies_reutilizados')
        return True

    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    driver.get(url_login)
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'

    if aguardar_url_painel:
        while True:
            try:
                if driver.current_url.startswith(painel_url):
                    if USAR_COOKIES_AUTOMATICO:
                        salvar_cookies_sessao(driver, info_extra='login_manual')
                    break
            except Exception as e:
                _ = e
            time.sleep(1)
    return True

def login_automatico(driver):
    """Login automático via AutoHotkey - OTIMIZADO: usa aguardar_e_clicar() e _obter_caminhos_ahk()"""
    from .utils_cookies import verificar_e_aplicar_cookies, salvar_cookies_sessao, USAR_COOKIES_AUTOMATICO
    from .extracao import aguardar_e_clicar
    from .utils_drivers import _obter_caminhos_ahk

    if verificar_e_aplicar_cookies(driver):
        if USAR_COOKIES_AUTOMATICO:
            salvar_cookies_sessao(driver, info_extra='cookies_reutilizados')
        return True

    import subprocess
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)

    try:
        # Usar aguardar_e_clicar (OTIMIZADO)
        if not aguardar_e_clicar(driver, '#btnSsoPdpj', timeout=10):
            logger.info("[LOGIN_AUTOMATICO][ERRO] Botão #btnSsoPdpj não encontrado")
            return False
        logger.info("[LOGIN_AUTOMATICO] Botão #btnSsoPdpj clicado com sucesso.")

        if not aguardar_e_clicar(driver, '.botao-certificado-titulo', timeout=10):
            logger.info("[LOGIN_AUTOMATICO][ERRO] Botão certificado não encontrado")
            return False
        logger.info("[LOGIN_AUTOMATICO] Botão .botao-certificado-titulo clicado com sucesso.")

        # Usar função auxiliar (OTIMIZADO - evita duplicação)
        ahk_exe, ahk_script = _obter_caminhos_ahk()

        if not ahk_exe or not os.path.exists(ahk_exe):
            logger.info(f"[LOGIN_AUTOMATICO][ERRO] Executável AutoHotkey não encontrado: {ahk_exe}")
            return False
        if not ahk_script or not os.path.exists(ahk_script):
            logger.info(f"[LOGIN_AUTOMATICO][ERRO] Script AutoHotkey não encontrado: {ahk_script}")
            return False

        subprocess.Popen([ahk_exe, ahk_script])
        logger.info("[LOGIN_AUTOMATICO] Script AutoHotkey chamado para digitar a senha.")

        for _ in range(60):
            if "login" not in driver.current_url.lower():
                logger.info("[LOGIN_AUTOMATICO] Login detectado, prosseguindo.")
                if USAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_automatico')
                return True
            time.sleep(1)

        logger.info("[ERRO] Timeout aguardando login.")
        return False
    except Exception as e:
        logger.info(f"[ERRO] Falha no processo de login: {e}")
        return False

def login_automatico_direto(driver):
    """Login automático DIRETO via AutoHotkey - OTIMIZADO: usa aguardar_e_clicar() e _obter_caminhos_ahk()"""
    from .utils_cookies import USAR_COOKIES_AUTOMATICO, salvar_cookies_sessao
    from .extracao import aguardar_e_clicar
    from .utils_drivers import _obter_caminhos_ahk

    import subprocess

    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)

    try:
        # Usar aguardar_e_clicar (OTIMIZADO)
        if not aguardar_e_clicar(driver, '#btnSsoPdpj', timeout=10):
            logger.error("[LOGIN_AUTOMATICO_DIRETO][ERRO] Botão #btnSsoPdpj não encontrado")
            return False

        if not aguardar_e_clicar(driver, '.botao-certificado-titulo', timeout=10):
            logger.error("[LOGIN_AUTOMATICO_DIRETO][ERRO] Botão certificado não encontrado")
            return False

        # Usar função auxiliar (OTIMIZADO - evita duplicação)
        ahk_exe, ahk_script = _obter_caminhos_ahk()

        if not ahk_exe or not os.path.exists(ahk_exe):
            logger.error(f"[LOGIN_AUTOMATICO_DIRETO][ERRO] Executável AutoHotkey não encontrado: {ahk_exe}")
            return False
        if not ahk_script or not os.path.exists(ahk_script):
            logger.error(f"[LOGIN_AUTOMATICO_DIRETO][ERRO] Script AutoHotkey não encontrado: {ahk_script}")
            return False

        subprocess.Popen([ahk_exe, ahk_script])

        for _ in range(60):
            if "login" not in driver.current_url.lower():
                if USAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_automatico_direto')
                return True
            time.sleep(1)

        return False

    except Exception as e:
        return False

def login_cpf(driver, url_login=None, cpf=None, senha=None, aguardar_url_final=True):
    """Login automático por CPF/senha - OTIMIZADO: usa preencher_multiplos_campos()"""
    import keyring
    cpf = cpf or keyring.get_password('pjeplus', 'PJE_USER')
    senha = senha or keyring.get_password('pjeplus', 'PJE_SENHA')
    from .utils_cookies import verificar_e_aplicar_cookies, salvar_cookies_sessao, USAR_COOKIES_AUTOMATICO

    try:
        # tentar aplicar cookies previamente salvos
        if verificar_e_aplicar_cookies(driver):
            if USAR_COOKIES_AUTOMATICO:
                try:
                    salvar_cookies_sessao(driver, info_extra='cookies_reutilizados_login_cpf')
                except Exception as e:
                    _ = e
            return True

        import time

        if not url_login:
            url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
        driver.get(url_login)
        time.sleep(1.2)

        # Se já estamos logados (URL não contém 'login'/'auth'), retorna True
        try:
            cur = driver.current_url.lower()
            if not any(k in cur for k in ['login', 'auth', 'realms']):
                return True
        except Exception as e:
            _ = e

        # Botão SSO PDPJ (fluxo antigo — opcional, pode não existir mais)
        try:
            btn_sso = driver.find_element(By.ID, 'btnSsoPdpj')
            btn_sso.click()
            time.sleep(1.0)
        except Exception:
            pass  # Página nova não tem mais esse botão — continuar normalmente

        # Digitar CPF no campo username
        try:
            username_field = driver.find_element(By.ID, 'username')
            username_field.clear()
            for ch in str(cpf):
                username_field.send_keys(ch)
                time.sleep(0.07)
        except Exception as e:
            logger.info(f"[LOGIN_CPF] Erro ao preencher CPF: {e}")
            return False

        # Digitar senha no campo password
        try:
            password_field = driver.find_element(By.ID, 'password')
            password_field.clear()
            for ch in str(senha):
                password_field.send_keys(ch)
                time.sleep(0.07)
        except Exception as e:
            logger.info(f"[LOGIN_CPF] Erro ao preencher senha: {e}")
            return False

        # Clicar no botão de confirmação do login (prioridade para #kc-login conforme requisitado)
        try:
            btn = driver.find_element(By.ID, 'kc-login')
            btn.click()
        except Exception:
            try:
                btn = driver.find_element(By.ID, 'btnEntrar')
                btn.click()
            except Exception as e:
                logger.info(f"[LOGIN_CPF] Botão de login não encontrado: {e}")
                return False

        # Aguardar redirecionamento/URL final
        if aguardar_url_final:
            timeout = 40
            inicio = time.time()
            while time.time() - inicio < timeout:
                try:
                    cur = driver.current_url.lower()
                    if 'pjekz' in cur or 'sisbajud' in cur or not any(k in cur for k in ['login', 'auth', 'realms']):
                        try:
                            if USAR_COOKIES_AUTOMATICO:
                                salvar_cookies_sessao(driver, info_extra='login_cpf')
                        except Exception as e:
                            _ = e
                        return True
                except Exception as e:
                    _ = e
                time.sleep(0.5)
            return False

        # Se não aguardamos, consideramos sucesso imediato
        return True

    except Exception as e:
        logger.info(f"[LOGIN_CPF] Erro durante login_cpf: {e}")
        return False

# --- CONFIGURAÇÕES ATIVAS ---

# Configuração AutoHotkey
AHK_EXE_PC = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
AHK_SCRIPT_PC = r'D:\PjePlus\Login.ahk'
AHK_EXE_NOTEBOOK = r'C:\Users\s164283\Downloads\AHK\AutoHotkey64.exe'
AHK_SCRIPT_NOTEBOOK = r'C:\Users\s164283\Desktop\pjeplus\login.ahk'
AHK_EXE_ACTIVE = None
AHK_SCRIPT_ACTIVE = None

# SELEÇÃO ATIVA (descomente apenas uma de cada)
from .drivers.lifecycle import criar_driver_PC, criar_driver_VT, criar_driver_notebook, criar_driver_sisb_pc, criar_driver_sisb_notebook
login_func = login_cpf            # ← ATIVO: Login por CPF/senha
criar_driver = criar_driver_PC    # ← ATIVO: Driver PC (Firefox)
criar_driver_sisb = criar_driver_sisb_pc  # ← ATIVO: Driver SISBAJUD PC

def exibir_configuracao_ativa():
    """Exibe qual configuração está ativa"""
    login_nome = "Manual" if login_func == login_manual else "CPF" if login_func == login_cpf else "Automático"

    if criar_driver == criar_driver_PC:
        driver_nome = "PC"
    elif criar_driver == criar_driver_VT:
        driver_nome = "VT"
    else:
        driver_nome = "Notebook"

    logger.info(f"[CONFIG] Login: {login_nome}")
    logger.info(f"[CONFIG] Driver: {driver_nome}")
    return login_nome, driver_nome

def login_pc(driver):
    """Processo de login humanizado via AutoHotkey, aguardando login terminar antes de prosseguir."""
    import subprocess
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    try:
        btn_sso = driver.find_element(By.CSS_SELECTOR, "#btnSsoPdpj")
        btn_sso.click()
        btn_certificado = driver.find_element(By.CSS_SELECTOR, ".botao-certificado-titulo")
        btn_certificado.click()
        time.sleep(1)
        # Obter caminho do AutoHotkey via credenciais, com fallback para valor padrão
        import keyring
        try:
            ahk_exe = keyring.get_password('pjeplus_paths', 'AUTOHOTKEY_EXE')
            if not ahk_exe or not os.path.exists(ahk_exe):
                ahk_exe = r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe"
        except:
            ahk_exe = r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe"

        subprocess.Popen([ahk_exe, r"D:\\PjePlus\\Login.ahk"])
        for _ in range(60):
            if "login" not in driver.current_url.lower():
                return True
            time.sleep(1)
        return False
    except Exception as e:
        logger.error(f"Erro no login_pc: {e}")
        return False
