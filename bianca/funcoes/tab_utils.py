
import logging
import time
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


def validar_conexao_driver(driver: WebDriver) -> bool:
    try:
        return bool(getattr(driver, "session_id", None)) and bool(driver.window_handles)
    except Exception:
        return False


def _abrir_nova_aba(driver: WebDriver, url: str, aba_origem: str, url_fragmento: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                for handle in driver.window_handles:
                    if handle == aba_origem:
                        continue
                    driver.switch_to.window(handle)
                    if not url_fragmento or url_fragmento in (driver.current_url or ""):
                        return handle
            except Exception:
                pass
            time.sleep(0.2)
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        logger.error(f"[TAB] erro ao abrir nova aba: {e}")
        return None


def trocar_para_nova_aba(driver: WebDriver, aba_origem: str, timeout: int = 10) -> Optional[str]:
    try:
        if not validar_conexao_driver(driver):
            return None

        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                for handle in driver.window_handles:
                    if handle == aba_origem:
                        continue
                    driver.switch_to.window(handle)
                    if driver.current_window_handle == handle:
                        return handle
            except Exception:
                pass
            time.sleep(0.2)

        return None
    except Exception as e:
        logger.error(f"[TAB] erro ao trocar de aba: {e}")
        return None


def _gerenciar_abas_apos_processo_dom(driver: WebDriver, aba_lista_original: str):
    try:
        handles = list(driver.window_handles)
        if aba_lista_original not in handles:
            raise Exception("RESTART_DRIVER: aba_lista_original_missing")

        for handle in handles:
            if handle == aba_lista_original:
                continue
            try:
                driver.switch_to.window(handle)
                time.sleep(0.25)
                driver.close()
            except Exception as e:
                if "disconnected" in str(e).lower() or "tried to run command" in str(e).lower():
                    raise Exception(f"RESTART_DRIVER: {e}")
                continue

        driver.switch_to.window(aba_lista_original)
        time.sleep(2.0)
    except Exception:
        raise


__all__ = [
    "validar_conexao_driver",
    "trocar_para_nova_aba",
    "_abrir_nova_aba",
    "_gerenciar_abas_apos_processo_dom",
]
