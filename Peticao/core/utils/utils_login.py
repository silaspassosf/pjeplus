import logging
logger = logging.getLogger(__name__)

"""
Utils login module for Peticao - contains login functions
"""

import os
import time
from selenium.webdriver.common.by import By

def login_cpf(driver, url_login=None, cpf=None, senha=None, aguardar_url_final=True):
    """Login automático por CPF/senha - OTIMIZADO: usa preencher_multiplos_campos()"""
    import keyring
    cpf = cpf or keyring.get_password('pjeplus', 'PJE_USER')
    senha = senha or keyring.get_password('pjeplus', 'PJE_SENHA')

    # Import local cookie utils (would need to be created separately)
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
            if any(k in cur for k in ['acesso-negado', 'access-denied', 'login.jsp']):
                return False
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
                    if any(k in cur for k in ['acesso-negado', 'access-denied', 'login.jsp']):
                        return False
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