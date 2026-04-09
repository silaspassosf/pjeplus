
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

_recovery_config: Dict[str, Any] = {
    "enabled": False,
    "driver_creator": None,
    "login_function": None,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _primeiro_existente(candidatos):
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return str(candidato)
    return None


def _resolver_geckodriver() -> Optional[str]:
    candidatos = [
        os.environ.get("PJEPLUS_GECKODRIVER_PATH"),
        os.environ.get("GECKODRIVER_PATH"),
        _repo_root() / "geckodriver.exe",
        _repo_root() / "Fix" / "geckodriver.exe",
    ]
    return _primeiro_existente(candidatos)


def _resolver_firefox_binary() -> Optional[str]:
    candidatos = [
        os.environ.get("PJEPLUS_FIREFOX_BINARY"),
        os.environ.get("FIREFOX_BINARY"),
        r"C:\Program Files\Firefox Developer Edition\firefox.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Users\Silas\AppData\Local\Firefox Developer Edition\firefox.exe",
    ]
    return _primeiro_existente(candidatos)


def _resolver_perfil_firefox() -> Optional[str]:
    candidatos = [
        os.environ.get("PJEPLUS_FIREFOX_PROFILE"),
        os.environ.get("FIREFOX_PROFILE_PATH"),
        os.environ.get("VT_PROFILE_PJE"),
        os.environ.get("VT_PROFILE_PJE_ALT"),
        r"C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485",
        r"C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot",
    ]
    return _primeiro_existente(candidatos)


def configurar_recovery_driver(driver_creator, login_function):
    _recovery_config["enabled"] = True
    _recovery_config["driver_creator"] = driver_creator
    _recovery_config["login_function"] = login_function


def _erro_sugere_recuperacao(erro: Exception, driver: Optional[WebDriver]) -> bool:
    texto = str(erro).lower()
    sinais = (
        "acesso-negado",
        "login",
        "invalid session id",
        "no such window",
        "browsing context",
        "disconnected",
        "tried to run command without establishing a connection",
    )
    if any(sinal in texto for sinal in sinais):
        return True

    try:
        if driver is None:
            return False
        url = (driver.current_url or "").lower()
        return any(sinal in url for sinal in ("acesso-negado", "login", "auth", "realms"))
    except Exception:
        return False


def handle_exception_with_recovery(e: Exception, driver: WebDriver, tag: str) -> Optional[WebDriver]:
    logger.error(f"[{tag}] {e}")

    if not _recovery_config.get("enabled"):
        return None

    if not _erro_sugere_recuperacao(e, driver):
        return None

    driver_creator = _recovery_config.get("driver_creator")
    login_function = _recovery_config.get("login_function")
    if not driver_creator or not login_function:
        return None

    try:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass

        novo_driver = driver_creator()
        if not novo_driver:
            return None

        if not login_function(novo_driver):
            try:
                novo_driver.quit()
            except Exception:
                pass
            return None

        return novo_driver
    except Exception as recovery_error:
        logger.error(f"[{tag}] falha na recuperacao: {recovery_error}")
        return None


def driver_pc(headless: bool = False) -> Optional[WebDriver]:
    geckodriver = _resolver_geckodriver()
    firefox_binary = _resolver_firefox_binary()
    perfil_firefox = _resolver_perfil_firefox()

    try:
        options = Options()
        if headless:
            options.add_argument("--headless")
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")

        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("page.load.animation.disabled", True)
        options.set_preference("dom.min_background_timeout_value", 0)
        options.set_preference("dom.timeout.throttling_delay", 0)

        if firefox_binary:
            options.binary_location = firefox_binary

        if perfil_firefox:
            options.set_preference("profile", perfil_firefox)

        if geckodriver:
            service = Service(executable_path=geckodriver)
            driver = webdriver.Firefox(service=service, options=options)
        else:
            driver = webdriver.Firefox(options=options)

        driver.implicitly_wait(10)
        try:
            if not headless:
                driver.maximize_window()
            else:
                driver.set_window_size(1920, 1080)
        except Exception:
            pass

        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception:
            pass

        return driver
    except Exception as e:
        logger.error(f"[DRIVER_PC] erro ao criar driver: {e}")
        return None


def login_cpf(driver: WebDriver, url_login: Optional[str] = None, cpf: Optional[str] = None, senha: Optional[str] = None, aguardar_url_final: bool = True) -> bool:
    try:
        try:
            import keyring
        except Exception:
            keyring = None

        if cpf is None:
            cpf = os.environ.get("PJE_USER")
            if cpf is None and keyring is not None:
                cpf = keyring.get_password("pjeplus", "PJE_USER")

        if senha is None:
            senha = os.environ.get("PJE_SENHA")
            if senha is None and keyring is not None:
                senha = keyring.get_password("pjeplus", "PJE_SENHA")

        if not cpf or not senha:
            logger.error("[LOGIN_CPF] credenciais nao configuradas")
            return False

        if url_login is None:
            url_login = "https://pje.trt2.jus.br/primeirograu/login.seam"

        driver.get(url_login)
        time.sleep(1)

        try:
            current_url = (driver.current_url or "").lower()
            if not any(token in current_url for token in ("login", "auth", "realms")):
                return True
        except Exception:
            pass

        try:
            btn_sso = driver.find_element(By.ID, "btnSsoPdpj")
            btn_sso.click()
            time.sleep(1)
        except Exception:
            pass

        username_field = driver.find_element(By.ID, "username")
        username_field.clear()
        username_field.send_keys(str(cpf))

        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(str(senha))

        try:
            driver.find_element(By.ID, "kc-login").click()
        except Exception:
            driver.find_element(By.ID, "btnEntrar").click()

        if not aguardar_url_final:
            return True

        inicio = time.time()
        while time.time() - inicio < 40:
            try:
                current_url = (driver.current_url or "").lower()
                if "pjekz" in current_url or "sisbajud" in current_url or not any(token in current_url for token in ("login", "auth", "realms")):
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        return False
    except Exception as e:
        logger.error(f"[LOGIN_CPF] erro durante login: {e}")
        return False


def esperar_elemento(driver: WebDriver, seletor: str, texto: Optional[str] = None, timeout: int = 10, by: By = By.CSS_SELECTOR, log: bool = False):
    try:
        elemento = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, seletor)))
        if texto:
            WebDriverWait(driver, timeout).until(lambda d: texto in (elemento.text or ""))
        return elemento
    except Exception:
        if log:
            logger.error(f"[ESPERAR_ELEMENTO] falhou: {seletor}")
        return None


def safe_click(driver: WebDriver, selector_or_element: Union[str, WebElement], timeout: int = 10, by: Optional[str] = None, log: bool = False) -> bool:
    try:
        if isinstance(selector_or_element, str):
            locator_by = by or By.CSS_SELECTOR
            element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((locator_by, selector_or_element)))
        else:
            element = selector_or_element

        try:
            driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));", element)
        except Exception:
            element.click()
        return True
    except Exception as e:
        if log:
            logger.error(f"[SAFE_CLICK] falhou: {e}")
        return False


def aguardar_e_clicar(driver: WebDriver, seletor: str, log: bool = False, timeout: int = 10, by: By = By.CSS_SELECTOR, usar_js: bool = True, retornar_elemento: bool = False, debug: Optional[bool] = None):
    if debug is not None:
        log = debug

    try:
        elemento = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, seletor)))
        if usar_js:
            driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));", elemento)
        else:
            elemento.click()
        return elemento if retornar_elemento else True
    except Exception as e:
        if log:
            logger.error(f"[AGUARDAR_E_CLICAR] falhou: {seletor} -> {e}")
        return None if retornar_elemento else False


def preencher_campo(driver: WebDriver, seletor: str, valor: str, trigger_events: bool = True, limpar: bool = True, log: bool = False) -> bool:
    try:
        elemento = driver.find_element(By.CSS_SELECTOR, seletor)
        if limpar:
            elemento.clear()
        elemento.send_keys(valor)
        if trigger_events:
            driver.execute_script(
                "var element = arguments[0]; element.dispatchEvent(new Event('input', { bubbles: true })); element.dispatchEvent(new Event('change', { bubbles: true })); element.dispatchEvent(new Event('blur', { bubbles: true }));",
                elemento,
            )
        return True
    except Exception as e:
        if log:
            logger.error(f"[PREENCHER_CAMPO] falhou: {seletor} -> {e}")
        return False


def preencher_multiplos_campos(driver: WebDriver, campos_dict: Dict[str, str], log: bool = False) -> bool:
    sucesso = True
    for seletor, valor in (campos_dict or {}).items():
        if not preencher_campo(driver, seletor, valor, log=log):
            sucesso = False
    return sucesso


def aguardar_renderizacao_nativa(driver: WebDriver, seletor: str, modo: str = "aparecer", timeout: int = 10) -> bool:
    try:
        if modo == "desaparecer":
            WebDriverWait(driver, timeout).until(lambda d: len(d.find_elements(By.CSS_SELECTOR, seletor)) == 0)
        else:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, seletor)))
        return True
    except TimeoutException:
        return False
    except Exception:
        return False


def abrir_detalhes_processo(driver: WebDriver, linha: WebElement) -> bool:
    try:
        try:
            botao = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
        except Exception:
            botao = linha.find_element(By.CSS_SELECTOR, 'button, a')
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
        driver.execute_script("arguments[0].click();", botao)
        return True
    except Exception as e:
        logger.error(f"[ABRIR_DETALHES] falhou: {e}")
        return False


def _extrair_numero_processo(driver: WebDriver) -> Optional[str]:
    try:
        url = driver.current_url or ""
        match = re.search(r"processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", url)
        if match:
            return match.group(1)
    except Exception:
        pass

    try:
        elemento = driver.find_element(By.XPATH, "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]")
        aria_label = elemento.get_attribute("aria-label") or ""
        match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
        if match:
            return match.group(1)
    except Exception:
        pass

    return None


def _extrair_trt_host(driver: WebDriver) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(driver.current_url or "").netloc
    except Exception:
        return "pje.trt2.jus.br"


def extrair_dados_processo(driver: WebDriver, caminho_json: str = "dadosatuais.json", debug: bool = False) -> Dict[str, Any]:
    try:
        import requests
    except Exception as e:
        if debug:
            logger.error(f"[EXTRAIR_DADOS] requests indisponivel: {e}")
        return {}

    numero_processo = _extrair_numero_processo(driver)
    if not numero_processo:
        return {}

    try:
        cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
    except Exception:
        cookies = {}

    session = requests.Session()
    for nome, valor in cookies.items():
        session.cookies.set(nome, valor)
    session.headers.update({"Accept": "application/json, text/plain, */*", "Content-Type": "application/json"})

    trt_host = _extrair_trt_host(driver)

    try:
        resposta = session.get(
            f"https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}",
            timeout=10,
        )
        resposta.raise_for_status()
        dados_busca = resposta.json() or []
        id_processo = dados_busca[0].get("idProcesso") if dados_busca else None
        if not id_processo:
            return {}

        dados = {"numero": [numero_processo], "id": id_processo}
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return dados
    except Exception as e:
        if debug:
            logger.error(f"[EXTRAIR_DADOS] falhou: {e}")
        return {}


def _parse_gigs_string(valor: str):
    if "/" not in valor:
        return {"dias_uteis": None, "responsavel": None, "observacao": valor.strip()}

    partes = valor.split("/")
    if len(partes) == 2:
        dias_str, observacao = partes
        try:
            dias_uteis = int(dias_str.strip())
        except ValueError:
            dias_uteis = None
        return {"dias_uteis": dias_uteis, "responsavel": None, "observacao": observacao.strip()}

    if len(partes) >= 3:
        dias_str, responsavel, observacao = partes[0], partes[1], "/".join(partes[2:])
        try:
            dias_uteis = int(dias_str.strip())
        except ValueError:
            dias_uteis = None
        return {"dias_uteis": dias_uteis, "responsavel": responsavel.strip(), "observacao": observacao.strip()}

    return {"dias_uteis": None, "responsavel": None, "observacao": valor.strip()}


def criar_gigs(driver: WebDriver, dias_uteis: Optional[Union[int, str]] = None, responsavel: Optional[str] = None, observacao: Optional[str] = None, timeout: int = 10, log: bool = True) -> bool:
    if isinstance(dias_uteis, str) and responsavel is None and observacao is None:
        parsed = _parse_gigs_string(dias_uteis)
        dias_uteis = parsed["dias_uteis"]
        responsavel = parsed["responsavel"]
        observacao = parsed["observacao"]

    if observacao is None and responsavel is not None:
        observacao = responsavel
        responsavel = None

    try:
        botao_nova = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[.//span[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')] or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')]",
                )
            )
        )
        botao_nova.click()
        time.sleep(1)

        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')))

        if dias_uteis:
            campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))

        if responsavel and responsavel.strip() and responsavel.strip() != "-":
            campo_responsavel = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]')
            campo_responsavel.clear()
            campo_responsavel.send_keys(responsavel)
            time.sleep(0.2)
            campo_responsavel.send_keys(Keys.ARROW_DOWN)
            campo_responsavel.send_keys(Keys.ENTER)

        if observacao:
            campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
            campo_obs.clear()
            campo_obs.send_keys(observacao)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", campo_obs)

        botao_salvar = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Salvar')]")))
        botao_salvar.click()
        time.sleep(0.5)
        return True
    except Exception as e:
        if log:
            logger.error(f"[GIGS] falhou: {e}")
        return False


def criar_e_logar_driver(driver_type) -> Optional[WebDriver]:
    logger.info("Criando e logando driver...")
    return None


def resetar_driver(driver: WebDriver) -> Optional[WebDriver]:
    try:
        driver.quit()
    except Exception:
        pass
    return None


def verificar_acesso_negado(driver: WebDriver, contexto: str):
    try:
        url = (driver.current_url or "").lower()
        return any(token in url for token in ("acesso-negado", "login", "auth", "realms"))
    except Exception:
        return False


__all__ = [
    "configurar_recovery_driver",
    "handle_exception_with_recovery",
    "driver_pc",
    "login_cpf",
    "aguardar_e_clicar",
    "aguardar_renderizacao_nativa",
    "esperar_elemento",
    "safe_click",
    "preencher_campo",
    "preencher_multiplos_campos",
    "abrir_detalhes_processo",
    "extrair_dados_processo",
    "criar_gigs",
    "criar_e_logar_driver",
    "resetar_driver",
    "verificar_acesso_negado",
]
