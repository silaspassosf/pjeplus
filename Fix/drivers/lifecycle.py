# =============================
# CONTEXT MANAGER PARA DRIVER (reta3.md P7)
# =============================
from contextlib import contextmanager

from Fix.log import get_module_logger

logger = get_module_logger(__name__)

@contextmanager
def driver_session(driver_type: str, headless: bool = False):
    """
    Context manager que cria, entrega e finaliza o driver automaticamente.
    Uso:
        with driver_session("PC", headless=True) as driver:
            login(driver)
            executar_fluxo(driver)
        # driver.quit() acontece aqui, mesmo se houver exceção
    """
    _criadores = {
        "PC": lambda: criar_driver_PC(headless=headless),
        "VT": lambda: criar_driver_VT(headless=headless),
        "notebook": lambda: criar_driver_notebook(headless=headless),
        "SISB_PC": lambda: criar_driver_sisb_pc(headless=headless),
        "SISB_notebook": lambda: criar_driver_sisb_notebook(headless=headless),
    }
    if driver_type not in _criadores:
        raise ValueError(f"Tipo de driver desconhecido: {driver_type}")
    driver = None
    try:
        driver = _criadores[driver_type]()
        if driver is None:
            raise RuntimeError(f"Falha ao criar driver do tipo '{driver_type}'")
        yield driver
    finally:
        if driver is not None:
            try:
                finalizar_driver(driver)
            except Exception as e:
                logger.warning(f"DRIVER:WARN — Falha ao finalizar driver: {e}")


"""
FUNÇÕES EXTRAÍDAS (lines 1485-1693 do core.py):
- criar_driver_PC: Driver PC - Firefox Developer Edition
- criar_driver_VT: Driver VT - Perfil padrão
- criar_driver_notebook: Driver Notebook
- criar_driver_sisb_pc: Driver SISBAJUD PC
- criar_driver_sisb_notebook: Driver SISBAJUD Notebook
- finalizar_driver: Finaliza driver com segurança

RESPONSABILIDADE:
- Criação de WebDrivers Firefox configurados
- Configurações específicas por ambiente (PC, VT, notebook)
- Configurações anti-throttling para background
- Gestão de perfis Firefox
- Finalização segura de drivers

DEPENDÊNCIAS:
- selenium.webdriver: WebDriver Firefox
- selenium.webdriver.firefox.options: Options
- selenium.webdriver.firefox.service: Service
- selenium.webdriver.firefox.firefox_profile: FirefoxProfile
- Fix.variaveis: GECKODRIVER_PATH

USO TÍPICO:
    from Fix.drivers import criar_driver_PC, finalizar_driver
    
    # Criar driver
    driver = criar_driver_PC(headless=False)
    
    # ... uso do driver ...
    
    # Finalizar
    finalizar_driver(driver)

AUTOR: Extração PJePlus Refactoring Phase 2
DATA: 2025-01-29
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from Fix.variaveis import GECKODRIVER_PATH
from ..utils_paths import (
    obter_caminho_firefox_executavel,
    obter_caminho_firefox_alt,
    obter_caminho_geckodriver
)

# =============================
# CONSTANTES
# =============================

# Obter caminhos via credenciais do Windows
def _obter_caminho_sisb_profile():
    # Tentar obter via credenciais, com fallback para valor padrão
    import keyring
    try:
        profile_path = keyring.get_password('pjeplus_paths', 'SISB_PROFILE_PATH')
        if profile_path and os.path.exists(profile_path):
            return profile_path
    except:
        pass
    return r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'

SISB_PROFILE_PC = _obter_caminho_sisb_profile()
SISB_PROFILE_NOTEBOOK = _obter_caminho_sisb_profile()

# Perfil fixo legado — mantido apenas como referência; criar_driver_PC/VT agora usam temp
FIREFOX_PROFILE_PC  = r'C:\SeleniumProfilePC'
FIREFOX_PROFILE_VT  = r'C:\SeleniumProfileVT'

def _criar_perfil_temp() -> str:
    """Cria e retorna um diretório temporário limpo para o perfil Firefox.

    Usar perfil temp garante inicialização sem cache corrompido e sem
    depender de caminhos fixos que variam por máquina.
    """
    return tempfile.mkdtemp(prefix="pjeplus_profile_")

# Padrões de arquivos temporários deixados pelo geckodriver/Firefox
_TEMP_PADROES = (
    r'^rust_mozprofile',
    r'^webdriver-py-',
    r'^geckodriver',
    r'^tmp[a-zA-Z0-9]{6,}$',
)

# =============================
# UTILIDADES INTERNAS
# =============================

def _matar_zumbis_geckodriver(limpar_temp: bool = True) -> None:
    """
    Mata processos geckodriver zumbis e limpa pastas rust_mozprofile na TEMP.
    Chamado antes de criar um novo driver e após finalizar.

    Args:
        limpar_temp: Se True, também remove arquivos temp órfãos do selenium/firefox.
    """
    # 1. Encerrar processos geckodriver presos
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'geckodriver.exe'],
            capture_output=True, text=True
        )
        if 'SUCCESS' in result.stdout or 'SUCESSO' in result.stdout:
            logger.debug('[DRIVER] Processos geckodriver zumbis encerrados')
    except Exception:
        pass


def _aplicar_prefs_download_headless(options: Options) -> None:
    """
    Aplica preferências para permitir downloads em modo headless.

    Ajusta prefs essenciais para que arquivos como PDF/ZIP/CSV sejam
    baixados automaticamente sem abrir visualizadores embutidos.
    """
    MIME_TYPES = ",".join([
        "application/pdf",
        "application/octet-stream",
        "text/csv",
        "application/zip",
    ])

    # Preferências para download automático em headless
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", MIME_TYPES)
    options.set_preference("pdfjs.disabled", True)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    # Garantir que o diretório de download é usado (2 = use especificado)
    try:
        options.set_preference("browser.download.folderList", 2)
    except Exception:
        pass


def _resolver_profile_path(base_path: str) -> str:
    """
    Retorna `base_path` se o diretório pai existir, caso contrário cria
    e retorna um diretório temporário via `tempfile.mkdtemp`.

    Logs uma warning quando o fallback é acionado.
    """
    parent = os.path.dirname(base_path)
    if parent and os.path.exists(parent):
        return base_path

    # Fallback: criar temp dir para perfil
    temp_profile = tempfile.mkdtemp(prefix="pjeplus_profile_")
    logger.warning("[DRIVER/WARN] Profile path indisponivel — usando temp: %s", temp_profile)
    return temp_profile

    # 2. Remover pastas temp órfãs do Selenium/Firefox
    if limpar_temp:
        try:
            temp_dir = tempfile.gettempdir()
            removidos = 0
            for entrada in os.listdir(temp_dir):
                if any(re.match(p, entrada, re.IGNORECASE) for p in _TEMP_PADROES):
                    caminho = os.path.join(temp_dir, entrada)
                    try:
                        if os.path.isdir(caminho):
                            shutil.rmtree(caminho, ignore_errors=True)
                        else:
                            os.remove(caminho)
                        removidos += 1
                    except Exception:
                        pass
            if removidos:
                logger.debug(f'[DRIVER] {removidos} arq. temp Selenium removidos da TEMP')
        except Exception:
            pass

# =============================
# DRIVERS FIREFOX
# =============================

def criar_driver_PC(headless: bool = False) -> webdriver.Firefox:
    """
    Cria driver Firefox Developer Edition para PC com configurações otimizadas.

    Otimizações:
    - Perfil fixo (FIREFOX_PROFILE_PC) → evita acúmulo de rust_mozprofile na TEMP
    - Mata geckodriver zumbis antes de criar
    - Anti-webdriver detection
    - Cache otimizado
    - Anti-throttling
    - Notificações e áudio desabilitados

    Args:
        headless: Se True, executa em modo headless (sem interface gráfica)

    Returns:
        WebDriver Firefox configurado
    """
    # Limpar zumbis antes de criar novo driver
    _matar_zumbis_geckodriver(limpar_temp=True)

    options = Options()
    if headless:
        options.add_argument('-headless')
        _aplicar_prefs_download_headless(options)

    # Perfil temporário limpo — sem dependência de caminho fixo por máquina
    temp_profile = _criar_perfil_temp()
    options.profile = FirefoxProfile(temp_profile)

    # Anti-detection
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
    )

    # Cache
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    options.set_preference("browser.cache.offline.enable", True)
    options.set_preference("network.http.use-cache", True)

    # Notificações e mídia
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("media.volume_scale", "0.0")

    # Anti-throttling
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    options.set_preference("page.load.animation.disabled", True)
    options.set_preference("dom.disable_window_move_resize", False)

    options.binary_location = obter_caminho_firefox_executavel()

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)

    return driver

def criar_driver_VT(headless: bool = False) -> webdriver.Firefox:
    """
    Cria driver Firefox para VT com perfil padrão.

    Otimizações:
    - Perfil fixo (FIREFOX_PROFILE_VT) — evita acúmulo de rust_mozprofile na TEMP
    - Mata geckodriver zumbis antes de criar
    - Configurações anti-throttling ativadas

    Args:
        headless: Se True, executa em modo headless

    Returns:
        WebDriver Firefox configurado
    """
    # Limpar zumbis antes de criar novo driver
    _matar_zumbis_geckodriver(limpar_temp=True)

    options = Options()
    if headless:
        options.add_argument('-headless')
        _aplicar_prefs_download_headless(options)

    options.binary_location = (
        obter_caminho_firefox_alt()
    )

    # Perfil temporário limpo — sem dependência de caminho fixo por máquina
    temp_profile = _criar_perfil_temp()
    options.profile = FirefoxProfile(temp_profile)

    # Anti-throttling
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)

    return driver

def criar_driver_notebook(headless: bool = False) -> webdriver.Firefox:
    """
    Cria driver Firefox Developer Edition para notebook.
    
    Args:
        headless: Se True, executa em modo headless
    
    Returns:
        WebDriver Firefox configurado
    
    Notas:
        - Pode usar perfil customizado 'Robot' (atualmente desativado)
        - Configurações anti-throttling ativadas
    """
    options = Options()
    if headless:
        options.add_argument('-headless')
        _aplicar_prefs_download_headless(options)
    
    options.binary_location = (
        obter_caminho_firefox_alt()
    )
    
    # Perfil customizado (atualmente desativado)
    USE_USER_PROFILE_NOTEBOOK = False
    if USE_USER_PROFILE_NOTEBOOK:
        resolved_profile = _resolver_profile_path(
            r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
        )
        os.makedirs(resolved_profile, exist_ok=True)
        options.profile = FirefoxProfile(resolved_profile)
    
    # Anti-throttling
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    
    return driver

# =============================
# DRIVERS SISBAJUD
# =============================

def criar_driver_sisb_pc(headless: bool = False) -> Optional[webdriver.Firefox]:
    """
    Cria driver Firefox Developer Edition para SISBAJUD (PC).
    
    Configurações robustas específicas para SISBAJUD:
    - Cache desabilitado
    - SafeBrowsing desabilitado
    - Telemetria desabilitada
    - Perfil SISB customizado
    
    Args:
        headless: Se True, executa em modo headless
    
    Returns:
        WebDriver Firefox configurado, ou None se falhar
    
    Exemplo:
        driver = criar_driver_sisb_pc()
        if driver:
            # ... processar SISBAJUD ...
            finalizar_driver(driver)
    
    Notas:
        - Usa perfil SISB em: arrn673i.Sisb
        - Fallback automático se perfil não existir
        - Implicit wait: 10 segundos
    """
    options = Options()
    if headless:
        options.add_argument('--headless')
    
    options.binary_location = obter_caminho_firefox_executavel()
    
    # Configurações específicas SISBAJUD
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("startup.homepage_welcome_url", "about:blank")
    options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
    options.set_preference("browser.startup.page", 0)
    
    # Cache desabilitado (segurança SISB)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    
    # SafeBrowsing desabilitado
    options.set_preference("browser.safebrowsing.enabled", False)
    options.set_preference("browser.safebrowsing.malware.enabled", False)
    
    # Telemetria desabilitada
    options.set_preference("datareporting.healthreport.uploadEnabled", False)
    options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
    options.set_preference("toolkit.telemetry.enabled", False)
    
    # Anti-throttling
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    # Tentar carregar perfil SISB
    try:
        if os.path.exists(SISB_PROFILE_PC):
            profile = FirefoxProfile(SISB_PROFILE_PC)
            options.profile = profile
        else:
            print(
                f"[DRIVER_SISB_PC] Perfil não encontrado: {SISB_PROFILE_PC}, "
                f"usando perfil temporário"
            )
    except Exception as e:
        print(
            f"[DRIVER_SISB_PC] Erro ao carregar perfil: {e}, "
            f"usando perfil temporário"
        )
    
    service = Service(executable_path=GECKODRIVER_PATH)
    
    # Tentativa 1: Com configurações completas
    try:
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"[DRIVER_SISB_PC] Erro ao criar driver: {e}")
        
        # Tentativa 2: Fallback com configurações mínimas
        try:
            options_fallback = Options()
            if headless:
                options_fallback.add_argument('--headless')
            options_fallback.binary_location = (
                obter_caminho_firefox_executavel()
            )
            
            driver = webdriver.Firefox(service=service, options=options_fallback)
            print(
                "[DRIVER_SISB_PC] Driver SISBAJUD PC (Developer Edition - fallback) "
                "criado com sucesso"
            )
            return driver
        except Exception as e2:
            return None

def criar_driver_sisb_notebook(headless: bool = False) -> webdriver.Firefox:
    """
    Cria driver Firefox Developer Edition para SISBAJUD (Notebook).
    
    Args:
        headless: Se True, executa em modo headless
    
    Returns:
        WebDriver Firefox configurado
    
    Notas:
        - Usa perfil SISB: arrn673i.Sisb
        - Configurações anti-throttling ativadas
    """
    options = Options()
    if headless:
        options.add_argument('-headless')
    
    options.binary_location = (
        obter_caminho_firefox_alt()
    )
    options.profile = SISB_PROFILE_NOTEBOOK
    
    # Anti-throttling
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    
    return driver

# =============================
# LIFECYCLE
# =============================

def finalizar_driver(driver: webdriver.Firefox, log: bool = True) -> bool:
    """
    Finaliza o driver de forma segura, aguardando operações pendentes.
    
    Processo:
    1. Fecha todas as janelas exceto a principal
    2. Aguarda 0.5s para operações pendentes
    3. Encerra o driver com quit()
    
    Args:
        driver: WebDriver a ser finalizado
        log: Se True, imprime mensagens de log
    
    Returns:
        True se finalizou com sucesso, False se houve erro
    
    Exemplo:
        driver = criar_driver_PC()
        # ... uso do driver ...
        finalizar_driver(driver)
    
    Notas:
        - Fecha janelas extras automaticamente
        - Aguarda operações pendentes antes de finalizar
        - Não levanta exceções (retorna False em caso de erro)
    """
    try:
        # Fecha todas as janelas exceto a principal
        if len(driver.window_handles) > 1:
            janela_principal = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(janela_principal)
        
        # Pequeno delay para operações pendentes
        time.sleep(0.5)
        
        # Fecha o driver
        driver.quit()

        # Pós-quit: limpar geckodriver zumbis e temp órfãos
        _matar_zumbis_geckodriver(limpar_temp=True)

        return True

    except Exception as e:
        if log:
            logger.error(f'[DRIVER][AVISO] Erro ao finalizar driver: {e}')
        # Tentar limpar mesmo em erro
        try:
            _matar_zumbis_geckodriver(limpar_temp=False)
        except Exception:
            pass
        return False
