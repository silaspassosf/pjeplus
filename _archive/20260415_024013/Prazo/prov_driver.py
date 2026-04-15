import logging
import os
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

from Fix.drivers import finalizar_driver
from Fix.utils import login_cpf

from .prov_config import (
    GECKODRIVER_PATH,
    FIREFOX_BINARY,
    FIREFOX_BINARY_ALT,
    VT_PROFILE_PJE,
    VT_PROFILE_PJE_ALT,
    USAR_PERFIL_VT,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DRIVER CREATION
# ============================================================================

def criar_driver(headless=False, tipo='vt'):
    """
    Cria driver Firefox para PROV
    
    Args:
        headless: Se True, executa sem interface gráfica
        tipo: 'vt' (ativo) ou 'pc' (alternativa)
    
    Returns:
        WebDriver ou None se falhar
    """
    
    # ==================== DRIVER VT (ATIVO) ====================
    if tipo == 'vt':
        return _criar_driver_vt(headless)
    
    # ==================== DRIVER PC (COMENTADO) ====================
    # elif tipo == 'pc':
    #     return _criar_driver_pc(headless)
    
    else:
        return None


def _criar_driver_vt(headless=False):
    """
    Cria driver VT com perfil e todas as otimizações
    Tenta: FIREFOX_BINARY → FIREFOX_BINARY_ALT
    Tenta: VT_PROFILE_PJE → VT_PROFILE_PJE_ALT → sem perfil
    """
    if not os.path.exists(GECKODRIVER_PATH):
        return None
    
    # Encontra o binário Firefox
    firefox_binaries = [FIREFOX_BINARY, FIREFOX_BINARY_ALT]
    firefox_bin_usado = None
    
    for bin_path in firefox_binaries:
        if os.path.exists(bin_path):
            firefox_bin_usado = bin_path
            break
    
    if not firefox_bin_usado:
        return None
    
    
    # Tenta criar com perfil
    try:
        options = Options()
        
        if headless:
            options.add_argument('-headless')
        
        # ===== DESABILITAR EXTENSÕES PARA ACELERAR STARTUP =====
        options.add_argument('-no-remote')
        options.add_argument('-new-instance')
        
        options.binary_location = firefox_bin_usado
        
        # Tenta com perfil primário (opcional)
        if USAR_PERFIL_VT:
            if os.path.exists(VT_PROFILE_PJE):
                options.profile = VT_PROFILE_PJE
            elif os.path.exists(VT_PROFILE_PJE_ALT):
                options.profile = VT_PROFILE_PJE_ALT
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        
        # ===== DESABILITAR EXTENSÕES =====
        options.set_preference("extensions.update.enabled", False)
        options.set_preference("extensions.update.autoUpdateDefault", False)
        options.set_preference("xpinstall.enabled", False)
        
        # ===== OTIMIZAÇÕES DE PERFORMANCE =====
        options.set_preference("browser.sessionstore.max_tabs_undo", 0)
        options.set_preference("browser.sessionstore.max_windows_undo", 0)
        options.set_preference("browser.cache.disk.enable", False)
        options.set_preference("browser.cache.memory.enable", False)
        options.set_preference("browser.shell.checkDefaultBrowser", False)
        options.set_preference("browser.safebrowsing.malware.enabled", False)
        options.set_preference("browser.safebrowsing.phishing.enabled", False)
        options.set_preference("browser.safebrowsing.downloads.enabled", False)
        
        # Anti-throttling
        options.set_preference("dom.min_background_timeout_value", 0)
        options.set_preference("dom.timeout.throttling_delay", 0)
        options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
        
        # Performance - Inicialização rápida
        options.set_preference("browser.startup.homepage", "about:blank")
        options.set_preference("startup.homepage_welcome_url", "about:blank")
        options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
        options.set_preference("browser.startup.firstrunSkipsHomepage", True)
        options.set_preference("browser.startup.page", 0)
        options.set_preference("browser.tabs.drawInTitlebar", True)
        options.set_preference("browser.privatebrowsing.autostart", False)
        options.set_preference("toolkit.cosmeticAnimations.enabled", False)
        options.set_preference("alerts.useSystemBackend", False)
        
        # Telemetria
        options.set_preference("datareporting.healthreport.uploadEnabled", False)
        options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
        options.set_preference("toolkit.telemetry.enabled", False)
        options.set_preference("toolkit.startup.max_pinned_tabs", 0)
        
        # Desabilitar notificações e popups
        options.set_preference("dom.disable_beforeunload", True)
        options.set_preference("browser.sessionstore.resuming_notification.delayed", False)
        
        service = Service(executable_path=GECKODRIVER_PATH)
        t0 = time.time()
        driver = webdriver.Firefox(options=options, service=service)
        driver.implicitly_wait(10)
        
        if not headless:
            driver.maximize_window()
        else:
            driver.set_window_size(1920, 1080)
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        logger.error(f"[PROV_DRIVER_VT]  Erro com perfil: {e}")
        
        # Fallback sem perfil
        try:
            options = Options()
            
            if headless:
                options.add_argument('-headless')
            
            # ===== DESABILITAR EXTENSÕES PARA ACELERAR STARTUP =====
            options.add_argument('-no-remote')
            options.add_argument('-new-instance')
            
            options.binary_location = firefox_bin_usado
            
            # Anti-automação
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference('useAutomationExtension', False)
            
            # ===== DESABILITAR EXTENSÕES =====
            options.set_preference("extensions.update.enabled", False)
            options.set_preference("extensions.update.autoUpdateDefault", False)
            options.set_preference("xpinstall.enabled", False)
            
            # ===== OTIMIZAÇÕES DE PERFORMANCE =====
            options.set_preference("browser.sessionstore.max_tabs_undo", 0)
            options.set_preference("browser.sessionstore.max_windows_undo", 0)
            options.set_preference("browser.cache.disk.enable", False)
            options.set_preference("browser.cache.memory.enable", False)
            options.set_preference("browser.shell.checkDefaultBrowser", False)
            options.set_preference("browser.safebrowsing.malware.enabled", False)
            options.set_preference("browser.safebrowsing.phishing.enabled", False)
            options.set_preference("browser.safebrowsing.downloads.enabled", False)
            
            # Anti-throttling
            options.set_preference("dom.min_background_timeout_value", 0)
            options.set_preference("dom.timeout.throttling_delay", 0)
            options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
            
            # Performance
            options.set_preference("browser.startup.homepage", "about:blank")
            options.set_preference("startup.homepage_welcome_url", "about:blank")
            options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
            options.set_preference("browser.startup.firstrunSkipsHomepage", True)
            options.set_preference("browser.startup.page", 0)
            options.set_preference("browser.tabs.drawInTitlebar", True)
            options.set_preference("browser.privatebrowsing.autostart", False)
            options.set_preference("toolkit.cosmeticAnimations.enabled", False)
            options.set_preference("alerts.useSystemBackend", False)
            
            # Telemetria
            options.set_preference("datareporting.healthreport.uploadEnabled", False)
            options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
            options.set_preference("toolkit.telemetry.enabled", False)
            options.set_preference("toolkit.startup.max_pinned_tabs", 0)
            
            # Desabilitar notificações
            options.set_preference("dom.disable_beforeunload", True)
            options.set_preference("browser.sessionstore.resuming_notification.delayed", False)
            
            service = Service(executable_path=GECKODRIVER_PATH)
            t0 = time.time()
            driver = webdriver.Firefox(options=options, service=service)
            driver.implicitly_wait(10)
            
            if not headless:
                driver.maximize_window()
            else:
                driver.set_window_size(1920, 1080)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        
        except Exception as e2:
            return None


def _criar_driver_pc(headless=False):
    """
    COMENTADO - Alternativa para ambiente PC
    Descomente se precisar usar em ambiente local com diferentes configurações
    """
    # Implementar se necessário


def criar_e_logar_driver() -> Optional[WebDriver]:
    """Cria driver e faz login no PJE"""
    try:
        logger.info("[PROV]  Criando driver...")
        driver = criar_driver(headless=False)
        
        if not driver:
            logger.info("[PROV]  Falha ao criar driver")
            return None
        
        logger.info("[PROV]  Fazendo login no PJE...")
        if not login_cpf(driver):
            logger.info("[PROV]  Falha no login")
            finalizar_driver(driver)
            return None
        
        logger.info("[PROV]  Driver criado e logado com sucesso")
        return driver
        
    except Exception as e:
        logger.info(f"[PROV]  Erro ao criar driver: {e}")
        import traceback
        logger.exception("Erro detectado")
        return None