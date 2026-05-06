import random
import time
import traceback

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

"""
SISB Core - Login e simulacao humana
"""


def simular_movimento_humano(driver, elemento):
    """Simula movimento de mouse humano antes de clicar em elemento."""
    try:
        actions = ActionChains(driver)

        if random.random() < 0.7:
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            actions.move_to_element_with_offset(elemento, offset_x, offset_y)
            actions.pause(random.uniform(0.1, 0.3))

        actions.move_to_element(elemento)
        actions.pause(random.uniform(0.1, 0.5))
        actions.perform()

    except Exception:
        pass


def login_automatico_sisbajud(driver):
    """Login automatizado humanizado no SISBAJUD."""
    try:
        logger.info('[SISBAJUD][LOGIN] Navegando para SISBAJUD...')
        driver.get('https://sisbajud.cnj.jus.br/')

        time.sleep(random.uniform(1.0, 1.5))

        current_url = driver.current_url
        if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
            logger.info('[SISBAJUD][LOGIN] Ja esta logado')
            return True

        logger.info('[SISBAJUD][LOGIN] Clicando no campo de login e digitando CPF...')
        try:
            username_field = driver.find_element(By.ID, "username")
            simular_movimento_humano(driver, username_field)
            username_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            cpf = "30069277885"
            for char in cpf:
                if random.random() < 0.05:
                    erro_char = str(random.randint(0, 9))
                    username_field.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    username_field.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                username_field.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
        except Exception as e:
            logger.info(f'[SISBAJUD][LOGIN] Erro ao digitar CPF: {e}')
            return False

        logger.info('[SISBAJUD][LOGIN] Clicando no campo de senha e digitando senha...')
        try:
            password_field = driver.find_element(By.ID, "password")
            simular_movimento_humano(driver, password_field)
            password_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            senha = "Fl@quinho182"
            for char in senha:
                if random.random() < 0.05:
                    erro_char = chr(random.randint(33, 126))
                    password_field.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    password_field.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                password_field.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
        except Exception as e:
            logger.info(f'[SISBAJUD][LOGIN] Erro ao digitar senha: {e}')
            return False

        logger.info('[SISBAJUD][LOGIN] Clicando no botao de login "Entrar"...')
        try:
            btn_entrar = driver.find_element(By.ID, "kc-login")
            simular_movimento_humano(driver, btn_entrar)
            btn_entrar.click()
        except Exception as e:
            logger.info(f'[SISBAJUD][LOGIN] Erro ao clicar no botao de login: {e}')
            return False

        logger.info('[SISBAJUD][LOGIN] Aguardando redirecionamento...')
        max_tentativas = 20
        for _ in range(max_tentativas):
            time.sleep(0.5)
            try:
                current_url = driver.current_url.lower()
                if 'sisbajud.cnj.jus.br' in current_url and not any(ind in current_url for ind in ['login', 'auth', 'realms']):
                    logger.info('[SISBAJUD][LOGIN] Login realizado com sucesso')
                    try:
                        driver.maximize_window()
                    except Exception:
                        pass
                    return True

                if any(ind in current_url for ind in ['auth', 'realms']) and 'kc-login' not in driver.page_source:
                    logger.info('[SISBAJUD][LOGIN] Login automatico nao concluido - pode necessitar verificacao manual')
                    logger.info('[SISBAJUD][LOGIN] URL atual:', driver.current_url)
                    return 'manual_needed'

            except Exception:
                pass

        current_url = driver.current_url.lower()
        if 'sisbajud.cnj.jus.br' in current_url and not any(ind in current_url for ind in ['login', 'auth', 'realms']):
            logger.info('[SISBAJUD][LOGIN] Login realizado com sucesso (apos timeout)')
            return True
        logger.info('[SISBAJUD][LOGIN] Login nao concluido automaticamente - pode precisar de verificacao')
        logger.info('[SISBAJUD][LOGIN] URL final:', driver.current_url)
        return 'manual_needed'

    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN] Erro durante login: {e}')
        logger.exception("Erro detectado")
        return False


def login_manual_sisbajud(driver, aguardar_url_final=True):
    """Login manual para SISBAJUD."""
    try:
        logger.info('[SISBAJUD][LOGIN_MANUAL] Navegando para SISBAJUD e aguardando login manual...')

        current_url = driver.current_url
        if not any(ind in current_url.lower() for ind in ['sisbajud', 'login', 'auth', 'realms']):
            driver.get('https://sisbajud.cnj.jus.br/')
        else:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Ja esta na pagina de autenticacao, aguardando conclusao...')

        target_indicator = 'sisbajud.cnj.jus.br'
        timeout = 300
        inicio = time.time()
        while True:
            try:
                current = driver.current_url.lower()
                if target_indicator in current and not any(ind in current for ind in ['login', 'auth', 'realms']):
                    logger.info('[SISBAJUD][LOGIN_MANUAL] Login detectado manualmente (URL mudou).')
                    try:
                        from driver_config import salvar_cookies_sessao, salvar_cookies_sisbajud, SALVAR_COOKIES_AUTOMATICO
                        if SALVAR_COOKIES_AUTOMATICO:
                            try:
                                salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                            except Exception as e:
                                logger.info(f"[SISBAJUD][LOGIN_MANUAL] Falha ao salvar cookies: {e}")
                    except Exception:
                        pass
                    return True
            except Exception:
                pass
            if not aguardar_url_final:
                return False
            if time.time() - inicio > timeout:
                logger.info('[SISBAJUD][LOGIN_MANUAL] Timeout aguardando login manual.')
                return False
            time.sleep(0.5)
    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN_MANUAL] Erro durante login manual: {e}')
        return False