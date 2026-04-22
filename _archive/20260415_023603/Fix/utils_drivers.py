import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_drivers - Módulo de gerenciamento de drivers para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import os
import platform
import subprocess
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Optional, Tuple, Any

from .utils_paths import (
    obter_caminho_perfil_firefox,
    obter_caminho_firefox_executavel
)

# Configurações do navegador - agora obtidas via credenciais
PROFILE_PATH = obter_caminho_perfil_firefox()
FIREFOX_BINARY = obter_caminho_firefox_executavel()

# Configuração AutoHotkey
AHK_EXE_PC = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
AHK_SCRIPT_PC = r'D:\PjePlus\Login.ahk'
AHK_EXE_NOTEBOOK = r'C:\Users\s164283\Downloads\AHK\AutoHotkey64.exe'
AHK_SCRIPT_NOTEBOOK = r'C:\Users\s164283\Desktop\pjeplus\login.ahk'

def _obter_caminhos_ahk() -> Tuple[Optional[str], Optional[str]]:
    """Retorna os caminhos corretos do AutoHotkey baseado no ambiente"""
    sistema = platform.system().lower()

    if 'windows' in sistema:
        # Detectar se é PC ou notebook baseado na existência dos arquivos
        if os.path.exists(AHK_EXE_PC) and os.path.exists(AHK_SCRIPT_PC):
            return AHK_EXE_PC, AHK_SCRIPT_PC
        elif os.path.exists(AHK_EXE_NOTEBOOK) and os.path.exists(AHK_SCRIPT_NOTEBOOK):
            return AHK_EXE_NOTEBOOK, AHK_SCRIPT_NOTEBOOK
        else:
            # Fallback: tentar encontrar AutoHotkey no PATH
            try:
                result = subprocess.run(['where', 'AutoHotkey.exe'], capture_output=True, text=True)
                if result.returncode == 0:
                    ahk_exe = result.stdout.strip().split('\n')[0]
                    # Para o script, assumir caminho relativo
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    ahk_script = os.path.join(script_dir, '..', '..', 'Login.ahk')
                    if os.path.exists(ahk_script):
                        return ahk_exe, ahk_script
            except Exception:
                pass

    return None, None

def criar_driver_firefox(profile_path: Optional[str] = None, binary_path: Optional[str] = None, headless: bool = False) -> Optional[WebDriver]:
    """Cria driver Firefox com configurações otimizadas"""
    options = FirefoxOptions()

    if profile_path and os.path.exists(profile_path):
        options.profile = profile_path

    if binary_path and os.path.exists(binary_path):
        options.binary_location = binary_path

    if headless:
        options.add_argument('--headless')

    # Configurações adicionais para melhor performance
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.set_preference('dom.webdriver.enabled', False)
    options.set_preference('useAutomationExtension', False)

    try:
        driver = webdriver.Firefox(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logger.error(f"Erro ao criar driver Firefox: {e}")
        return None

def criar_driver_PC(headless: bool = False) -> Optional[WebDriver]:
    """Cria driver para PC com configurações específicas"""
    return criar_driver_firefox(
        profile_path=PROFILE_PATH,
        binary_path=FIREFOX_BINARY,
        headless=headless
    )

def criar_driver_VT(headless: bool = False) -> Optional[WebDriver]:
    """Cria driver para VT (Virtual Terminal)"""
    # Configurações específicas para VT
    return criar_driver_firefox(headless=headless)

def criar_driver_notebook(headless: bool = False) -> Optional[WebDriver]:
    """Cria driver para notebook"""
    # Configurações específicas para notebook
    return criar_driver_firefox(headless=headless)

def criar_driver_sisb_pc(headless: bool = False) -> Optional[WebDriver]:
    """Cria driver para SISBAJUD no PC"""
    return criar_driver_firefox(
        profile_path=PROFILE_PATH,
        binary_path=FIREFOX_BINARY,
        headless=headless
    )

def criar_driver_sisb_notebook(headless: bool = False) -> Optional[WebDriver]:
    """Cria driver para SISBAJUD no notebook"""
    return criar_driver_firefox(headless=headless)

def configurar_driver_avancado(driver: WebDriver, timeout_implicito: int = 10) -> bool:
    """Configurações avançadas do driver após criação"""
    try:
        driver.implicitly_wait(timeout_implicito)
        driver.maximize_window()
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar driver avançado: {e}")
        return False

def verificar_driver_ativo(driver: WebDriver) -> bool:
    """Verifica se o driver ainda está ativo"""
    try:
        driver.current_url
        return True
    except Exception:
        return False

def fechar_driver_safely(driver: WebDriver) -> bool:
    """Fecha o driver de forma segura"""
    try:
        # Evita flood de logs durante o teardown (ex.: urllib3.connectionpool)
        try:
            logging.getLogger('urllib3.connectionpool').disabled = True
        except Exception:
            pass
        if driver:
            driver.quit()
        return True
    except Exception as e:
        logger.error(f"Erro ao fechar driver: {e}")
        return False


def fechar_driver_imediato(driver: WebDriver, kill_processes: bool = True) -> bool:
    """Fecha o driver de forma imediata, forçando encerramento de processos.

    Tenta `driver.quit()` e, se necessário, mata processos do geckodriver/firefox
    para evitar retries HTTP (urllib3) demorados durante teardown.
    """
    try:
        # Suprimir logs ruidosos que aparecem quando o geckodriver/firefox é morto
        try:
            logging.getLogger('urllib3.connectionpool').disabled = True
            logging.getLogger('urllib3').setLevel(logging.WARNING)
        except Exception:
            pass
        if not driver:
            # Ainda assim, tentar limpar temporários
            limpar_temp_selenium()
            return True

        # Primeiro tentar fechamento gracioso
        try:
            driver.quit()
        except Exception:
            pass

        # Tentar matar o processo associado ao serviço (se existir)
        try:
            service = getattr(driver, 'service', None)
            proc = getattr(service, 'process', None)
            pid = None
            if proc is not None:
                pid = getattr(proc, 'pid', None)
            if pid:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(['kill', '-9', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Matar por nome (fallback)
            if kill_processes:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/IM', 'geckodriver.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['taskkill', '/F', '/IM', 'firefox.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(['pkill', '-f', 'geckodriver'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['pkill', '-f', 'firefox'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # Não falhar caso não seja possível matar processos
            pass

        # Limpeza final de temporários
        try:
            limpar_temp_selenium()
        except Exception:
            pass

        return True
    except Exception as e:
        logger.error(f"fechar_driver_imediato falhou: {e}")
        return False

def limpar_temp_selenium() -> int:
    """Limpa os arquivos temporários do Selenium de forma segura"""
    import os
    import glob
    from datetime import datetime, timedelta

    try:
        # Define pastas temporárias comuns
        temp_dirs = [
            os.path.join(os.environ.get('TEMP', ''), 'selenium*'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp', 'selenium*')
        ]

        # Limpeza segura
        deleted = 0
        for pattern in temp_dirs:
            for filepath in glob.glob(pattern):
                try:
                    # Verifica se o arquivo é antigo (>1 dia)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if datetime.now() - file_time > timedelta(days=1):
                        os.remove(filepath)
                        deleted += 1
                except Exception:
                    pass  # Ignora erros individuais

        logger.info(f"Limpeza concluída: {deleted} arquivos temporários removidos")
        return deleted

    except Exception as e:
        logger.error(f"Erro na limpeza de temporários: {e}")
        return 0