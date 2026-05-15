# -*- coding: utf-8 -*-
"""
bianca/driver.py - Gerenciamento do driver Selenium Firefox.
"""

import logging
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from bianca.config import FIREFOX_BINARY, GECKODRIVER_PATH

logger = logging.getLogger(__name__)


# =============================================================================
# Driver
# =============================================================================

def criar_driver() -> WebDriver:
    """Cria um driver Firefox Developer Edition configurado.

    Usa os caminhos definidos em bianca.config:
      - GECKODRIVER_PATH
      - FIREFOX_BINARY

    Retorna a instancia do WebDriver.
    Levanta excecao se o driver nao puder ser criado.
    """
    if not GECKODRIVER_PATH.exists():
        raise FileNotFoundError(
            f"Geckodriver nao encontrado em: {GECKODRIVER_PATH}"
        )

    options = Options()
    options.binary_location = str(FIREFOX_BINARY)

    # Anti-automacao
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)

    # Preferencias de desempenho
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    options.set_preference("browser.cache.offline.enable", True)
    options.set_preference("network.http.use-cache", True)
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")

    # Anti-throttling
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=str(GECKODRIVER_PATH))
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)

    logger.info("Driver Firefox criado com sucesso")
    return driver


# =============================================================================
# Login
# =============================================================================

def fazer_login_manual(driver: WebDriver) -> None:
    """Faz login no PJe com CPF e senha fornecidos pelo usuario.

    Etapas:
      1. Le CPF e senha via terminal (input())
      2. Navega para pagina de login do PJe
      3. Tenta preencher campos automaticamente (opcao A)
      4. Se falhar, permite login manual (opcao B)

    Nunca le credenciais de variaveis de ambiente ou arquivos.
    """
    cpf = input("Digite o CPF (somente numeros): ").strip()
    senha = input("Digite a senha: ").strip()

    if not cpf or not senha:
        logger.error("CPF ou senha nao informados. Abortando login.")
        return

    url_login = "https://pje.trt2.jus.br/primeirograu/login.seam"
    logger.info("Navegando para %s", url_login)
    driver.get(url_login)

    # Aguarda carregamento
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass

    # Se ja estiver logado, retorna
    try:
        cur = driver.current_url.lower()
        if not any(k in cur for k in ["login", "auth", "realms"]):
            logger.info("Ja autenticado.")
            return
    except Exception:
        pass

    # ---- Opcao A: preenchimento automatico ----
    try:
        # Clicar no botao SSO PDPJ
        btn_sso = driver.find_element(By.ID, "btnSsoPdpj")
        btn_sso.click()
        logger.info("Botao SSO PDPJ clicado")
        time.sleep(1.0)

        # Preencher CPF
        username_field = driver.find_element(By.ID, "username")
        username_field.clear()
        for ch in str(cpf):
            username_field.send_keys(ch)
            time.sleep(0.05)
        logger.info("CPF digitado no campo username")

        # Preencher senha
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        for ch in str(senha):
            password_field.send_keys(ch)
            time.sleep(0.05)
        logger.info("Senha digitada no campo password")

        # Clicar em Entrar
        try:
            btn_entrar = driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"
            )
            btn_entrar.click()
        except Exception:
            pass

        # Aguarda redirecionamento
        for _ in range(30):
            try:
                cur = driver.current_url.lower()
                if not any(k in cur for k in ["login", "auth", "realms"]):
                    logger.info("Login automatico bem-sucedido!")
                    return
            except Exception:
                pass
            time.sleep(1)

        logger.warning(
            "Preenchimento automatico concluido, mas nao foi possivel "
            "confirmar redirecionamento. Prosseguindo..."
        )

    except Exception as e:
        logger.warning(
            "Preenchimento automatico falhou (%s). "
            "Usando opcao B - login manual.",
            e,
        )
        _login_manual_fallback(driver)


def _login_manual_fallback(driver: WebDriver) -> None:
    """Opcao B: usuario faz login manualmente no navegador."""
    print("\n" + "=" * 60)
    print("LOGIN MANUAL")
    print("=" * 60)
    print("Preencha CPF e senha manualmente no navegador aberto.")
    print("Acesse: https://pje.trt2.jus.br/primeirograu/login.seam")
    print("Apos concluir o login, pressione Enter para continuar...")
    input()
    logger.info("Usuario confirmou login manual.")


# =============================================================================
# Verificacao e recuperacao de sessao
# =============================================================================


def verificar_sessao(driver: WebDriver) -> bool:
    """Verifica se a sessao atual ainda e valida.

    Checa se a URL atual nao contem indicadores de pagina de login,
    autenticacao ou acesso negado.

    Args:
        driver: WebDriver Selenium.

    Returns:
        bool: True se a sessao parece valida, False caso contrario.
    """
    try:
        url = driver.current_url.lower()
    except Exception:
        return False

    if any(k in url for k in ["login", "auth", "realms", "acesso-negado", "error"]):
        logger.warning("Sessao invalida — URL atual: %s", url[:120])
        return False

    return True


def resetar_driver(driver: WebDriver) -> bool:
    """Tenta recuperar sessao do driver: refresh + navegacao para pagina conhecida.

    Args:
        driver: WebDriver Selenium.

    Returns:
        bool: True se a sessao foi recuperada com sucesso.
    """
    try:
        logger.info("Resetando driver — tentando refresh...")
        driver.refresh()
        time.sleep(2)

        if verificar_sessao(driver):
            logger.info("Driver recuperado apos refresh.")
            return True

        # Tentar navegar para pagina base conhecida
        try:
            from bianca.config import URL_PJE_BASE

            logger.info("Refresh insuficiente — navegando para PJE_BASE...")
            driver.get(URL_PJE_BASE)
            time.sleep(3)
        except Exception:
            pass

        return verificar_sessao(driver)
    except Exception as e:
        logger.error("Erro ao resetar driver: %s", e)
        return False


# =============================================================================
# Combinado
# =============================================================================

def criar_driver_e_fazer_login() -> Optional[WebDriver]:
    """Cria o driver e faz login. Retorna o driver ou None se falhar."""
    try:
        driver = criar_driver()
    except Exception as e:
        logger.error("Falha ao criar driver: %s", e)
        return None

    try:
        fazer_login_manual(driver)
    except Exception as e:
        logger.error("Falha durante login: %s", e)
        try:
            driver.quit()
        except Exception:
            pass
        return None

    return driver
