"""
Andrei.driver - Gerenciamento do driver Firefox para PJe.
Perfil temporario criado via tempfile.mkdtemp(), removido ao fechar.
"""

import tempfile
import shutil
import time
import logging

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from Andrei.config import (
    GECKODRIVER_PATH,
    FIREFOX_BINARY,
    ESCANINHO_URL,
    LOGIN_TIMEOUT,
    DEFAULT_TIMEOUT,
)

logger = logging.getLogger(__name__)


def criar_driver(headless: bool = False) -> webdriver.Firefox:
    """Cria um driver Firefox com perfil temporario.

    O perfil e criado via tempfile.mkdtemp() e armazenado em
    driver._profile_dir para limpeza posterior em fechar_driver().

    Args:
        headless: Se True, executa o Firefox em modo headless.

    Returns:
        Instancia configurada de webdriver.Firefox.

    Raises:
        Exception: Se o driver nao puder ser criado.
    """
    profile_dir = tempfile.mkdtemp(prefix="pjeplus_andrei_")
    logger.info("Perfil Firefox temporario criado em: %s", profile_dir)

    profile = FirefoxProfile(profile_dir)

    options = Options()
    if headless:
        options.add_argument("--headless")
    options.binary_location = str(FIREFOX_BINARY)
    options.profile = profile

    service = Service(executable_path=str(GECKODRIVER_PATH))

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(DEFAULT_TIMEOUT)
        # Armazena o diretorio do perfil para limpeza posterior
        driver._profile_dir = profile_dir
        logger.info("Driver Firefox inicializado com sucesso")
        return driver
    except Exception:
        logger.exception("Falha ao criar driver Firefox")
        # Limpa o diretorio temporario se a criacao falhar
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise


def aguardar_login_manual(
    driver: webdriver.Firefox, timeout: int = LOGIN_TIMEOUT
) -> bool:
    """Navega para o escaninho e aguarda o login manual do usuario.

    A funcao abre a pagina de peticoes juntadas e monitora a URL
    ate que o usuario complete o login manualmente. Nao tenta
    automatizar credenciais — o login e exclusivamente manual.

    Args:
        driver: WebDriver Firefox ativo.
        timeout: Tempo maximo de espera em segundos (padrao: 300).

    Returns:
        True se o usuario fez login dentro do tempo limite,
        False se expirou sem login detectado.
    """
    logger.info("Navegando para: %s", ESCANINHO_URL)
    try:
        driver.get(ESCANINHO_URL)
    except Exception:
        logger.exception("Falha ao navegar para o escaninho")
        return False

    logger.info(
        "=== LOGIN MANUAL REQUERIDO ==="
    )
    logger.info(
        "A pagina de login foi aberta. Faca o login manualmente "
        "no navegador usando seu certificado digital ou CPF/senha."
    )
    logger.info(
        "Aguardando login por ate %d segundos...", timeout
    )

    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            url_atual = driver.current_url.lower()
            logger.debug("URL atual: %s", url_atual)

            # Verifica se o login foi concluido:
            # - URL contem "escaninho" (indicando area logada)
            # - URL NAO contem "login" (indicando pagina de autenticacao)
            if "escaninho" in url_atual and "login" not in url_atual:
                logger.info("Login manual detectado com sucesso!")
                return True
        except Exception:
            logger.debug("Falha ao ler URL (navegacao ainda em progresso)", exc_info=True)

        time.sleep(2)

    logger.warning("Tempo limite de %d segundos excedido aguardando login manual", timeout)
    return False


def fechar_driver(driver: webdriver.Firefox) -> None:
    """Encerra o driver Firefox e remove o perfil temporario.

    Args:
        driver: WebDriver Firefox a ser encerrado.
    """
    profile_dir = getattr(driver, "_profile_dir", None)

    # Encerra o navegador
    try:
        driver.quit()
        logger.info("Driver Firefox encerrado")
    except Exception:
        logger.exception("Erro ao encerrar driver Firefox")

    # Remove o diretorio de perfil temporario
    if profile_dir:
        try:
            shutil.rmtree(profile_dir, ignore_errors=True)
            logger.info("Perfil temporario removido: %s", profile_dir)
        except Exception:
            logger.exception("Erro ao remover perfil temporario: %s", profile_dir)


def criar_driver_e_logar(headless: bool = False) -> webdriver.Firefox | None:
    """Combina: criar driver, navegar para escaninho, aguardar login manual.

    Args:
        headless: Se True, executa o Firefox em modo headless.

    Returns:
        driver: WebDriver Firefox logado, ou None se falhou.
    """
    driver = None
    try:
        driver = criar_driver(headless=headless)
        if not aguardar_login_manual(driver):
            logger.error("Falha no login manual")
            fechar_driver(driver)
            return None
        logger.info("Driver criado e logado com sucesso")
        return driver
    except Exception:
        logger.exception("Falha ao criar driver e realizar login")
        if driver is not None:
            fechar_driver(driver)
        return None
