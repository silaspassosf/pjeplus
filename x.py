def _executar_mandado_bloco(driver):
    resultado = executar_mandado(driver)
    resetar_driver(driver)
    return resultado

def _executar_prazo_bloco(driver):
    resultado = executar_prazo(driver)
    resetar_driver(driver)
    return resultado

def _executar_p2b_bloco(driver):
    resultado = executar_p2b(driver)
    resetar_driver(driver)
    return resultado

def _executar_pec_bloco(driver):
    return executar_pec(driver)


"""
x.py - Orquestrador Unificado PJEPlus (100% STANDALONE)
=========================================================
Consolidao completa e independente de 1.py, 1b.py, 2.py, 2b.py.
NO depende de nenhum dos scripts originais.

Menu 1: Selecionar Ambiente/Driver
  - A: PC + Visvel (1.py)
  - B: PC + Headless (1b.py)
  - C: VT + Visvel (2.py)
  - D: VT + Headless (2b.py)

Menu 2: Selecionar Fluxo de Execuo
    - A: Bloco Completo (Mandado  Prazo  PEC)
    - B: Mandado Isolado
    - C: Prazo Isolado
    - D: P2B Isolado
    - E: PEC Isolado

Autor: Sistema PJEPlus
Data: 04/12/2025
"""

import sys
import time
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import signal

# Selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

# Imports dos mdulos refatorados
from Fix.core import finalizar_driver as finalizar_driver_fix, finalizar_driver_imediato as finalizar_driver_imediato_fix
from Fix.utils import login_cpf
from Fix.drivers import driver_session
from Prazo import loop_prazo
from PEC.orquestrador import executar_fluxo_novo_simplificado as pec_fluxo_api
from Fix.smart_finder import injetar_smart_finder_global
from Mandado.processamento_api import processar_mandados_devolvidos_api

# Otimização de imports (plano_imports_otimizacao.md)
import traceback
from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b

# Imports opcionais (carregados somente quando necessário)
# from Triagem.runner import run_triagem
# from Peticao.pet import run_pet

# ============================================================================
# CONFIGURAES GLOBAIS
# ============================================================================

# Caminho do geckodriver
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'Fix', 'geckodriver.exe')

# Diretrio de logs
LOG_DIR = "logs_execucao"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
# Flag para pular finalização lenta quando já usamos o finalizador imediato (Ctrl+C)
skip_finalizar = False


class DriverType(Enum):
    """Tipos de drivers suportados"""
    PC_VISIBLE = "pc_visible"
    PC_HEADLESS = "pc_headless"
    VT_VISIBLE = "vt_visible"
    VT_HEADLESS = "vt_headless"


# ============================================================================
# CAPTURA DE PRINTS (TEEOUTPUT)
# ============================================================================

class TeeOutput:
    """Captura stdout/stderr para arquivo e console"""
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log_file = open(file_path, 'a', encoding='utf-8')
        
    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
        
    def close(self):
        self.log_file.close()
        sys.stdout = self.terminal


# ============================================================================
# DRIVERS - PC
# ============================================================================

def criar_driver_pc(headless=False):
    """
    Cria driver Firefox para PC (padro).
    Firefox Developer Edition com configuraes otimizadas.
    """
    try:
        options = Options()
        
        if headless:
            options.add_argument('-headless')
        
        # Configuraes de automao
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
        
        # Cache e performance
        options.set_preference("browser.cache.disk.enable", True)
        options.set_preference("browser.cache.memory.enable", True)
        options.set_preference("browser.cache.offline.enable", True)
        options.set_preference("network.http.use-cache", True)
        
        # Notificaes
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("media.volume_scale", "0.0")
        
        # Downloads headless-safe
        if headless:
            options.set_preference("browser.download.folderList", 2)
            options.set_preference("browser.download.manager.showWhenStarting", False)
            options.set_preference("browser.download.dir", os.path.join(os.path.dirname(__file__), "downloads"))
            options.set_preference("browser.helperApps.neverAsk.saveToDisk",
                "application/pdf,application/octet-stream,application/zip,"
                "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            options.set_preference("pdfjs.disabled", True)
        
        # Anti-throttling
        options.set_preference("dom.min_background_timeout_value", 0)
        options.set_preference("dom.timeout.throttling_delay", 0)
        options.set_preference("dom.timeout.budget_throttling_max_delay", 0)
        options.set_preference("page.load.animation.disabled", True)
        options.set_preference("dom.disable_window_move_resize", False)
        
        # Firefox binary
        options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
        
        service = Service(executable_path=GECKODRIVER_PATH)
        driver = webdriver.Firefox(options=options, service=service)
        driver.implicitly_wait(10)
        
        if not headless:
            driver.maximize_window()
        else:
            driver.set_window_size(1920, 1080)
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[DRIVER_PC]  Driver PC criado com sucesso")
        return driver
        
    except Exception as e:
        print(f"[DRIVER_PC]  Erro ao criar driver: {e}")
        return None


# ============================================================================
# DRIVERS - VT (Mquina Especfica)
# ============================================================================

def criar_driver_vt(headless=False):
    """
    Cria driver Firefox para VT (mquina especfica).
    Usa perfis e configuraes VT com otimizaes de startup.
    """
    # Configuraes VT
    FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
    FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    
    VT_PROFILE_PJE = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
    VT_PROFILE_PJE_ALT = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
    
    if not os.path.exists(GECKODRIVER_PATH):
        print(f"[DRIVER_VT]  Geckodriver no encontrado em {GECKODRIVER_PATH}")
        return None
    
    # Encontrar binrio
    firefox_bin = None
    for bin_path in [FIREFOX_BINARY, FIREFOX_BINARY_ALT]:
        if os.path.exists(bin_path):
            firefox_bin = bin_path
            break
    
    if not firefox_bin:
        print(f"[DRIVER_VT]  Nenhum binrio Firefox encontrado")
        return None
    
    print(f"[DRIVER_VT] Usando binrio: {firefox_bin}")
    
    try:
        options = Options()
        
        if headless:
            options.add_argument('-headless')
            #  OTIMIZAO HEADLESS: Viewport maior para evitar overlays
            options.add_argument('--width=1920')
            options.add_argument('--height=1200')
        
        # ===== DESABILITAR EXTENSES PARA ACELERAR STARTUP =====
        options.add_argument('-no-remote')
        options.add_argument('-new-instance')
        
        options.binary_location = firefox_bin
        
        # Tenta com perfil (opcional - pode deixar mais lento)
        # Se USAR_PERFIL_VT = False, cria driver sem perfil (mais rpido)
        USAR_PERFIL_VT = False
        
        if USAR_PERFIL_VT:
            if os.path.exists(VT_PROFILE_PJE):
                options.profile = VT_PROFILE_PJE
                print(f"[DRIVER_VT] Usando perfil: {VT_PROFILE_PJE}")
            elif os.path.exists(VT_PROFILE_PJE_ALT):
                options.profile = VT_PROFILE_PJE_ALT
                print(f"[DRIVER_VT] Usando perfil alternativo: {VT_PROFILE_PJE_ALT}")
        
        # Anti-automao
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        
        # ===== DESABILITAR EXTENSES =====
        options.set_preference("extensions.update.enabled", False)
        options.set_preference("extensions.update.autoUpdateDefault", False)
        options.set_preference("xpinstall.enabled", False)
        
        # ===== OTIMIZAES DE PERFORMANCE =====
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
        
        #  OTIMIZAO HEADLESS: Performance e cache
        if headless:
            # MANTER cache em headless para melhor performance
            options.set_preference("browser.cache.disk.enable", True)
            options.set_preference("browser.cache.memory.enable", True)
            # Desabilitar animaes que causam overlays
            options.set_preference("ui.prefersReducedMotion", 1)
            options.set_preference("browser.tabs.animate", False)
            options.set_preference("toolkit.cosmeticAnimations.enabled", False)
        else:
            # Performance normal para modo visvel
            options.set_preference("browser.cache.disk.enable", False)
            options.set_preference("browser.cache.memory.enable", False)
        
        # Performance geral
        options.set_preference("browser.sessionstore.max_tabs_undo", 0)
        options.set_preference("browser.sessionstore.max_windows_undo", 0)
        options.set_preference("browser.shell.checkDefaultBrowser", False)
        options.set_preference("browser.safebrowsing.malware.enabled", False)
        options.set_preference("browser.safebrowsing.phishing.enabled", False)
        options.set_preference("browser.safebrowsing.downloads.enabled", False)
        options.set_preference("browser.startup.homepage", "about:blank")
        options.set_preference("startup.homepage_welcome_url", "about:blank")
        options.set_preference("browser.startup.page", 0)
        options.set_preference("datareporting.healthreport.uploadEnabled", False)
        options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
        options.set_preference("toolkit.telemetry.enabled", False)
        
        service = Service(executable_path=GECKODRIVER_PATH)
        print("[DRIVER_VT]  Criando instncia Firefox...")
        t0 = time.time()
        driver = webdriver.Firefox(options=options, service=service)
        print(f"[DRIVER_VT]  Configurando driver... (launch {time.time() - t0:.1f}s)")
        driver.implicitly_wait(10)
        
        if not headless:
            driver.maximize_window()
        else:
            driver.set_window_size(1920, 1080)
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[DRIVER_VT]  Driver VT criado com sucesso")
        return driver
        
    except Exception as e:
        print(f"[DRIVER_VT]  Erro com configuraes otimizadas: {e}")
        print("[DRIVER_VT]  Fallback: criando driver com configuraes mnimas...")
        
        try:
            options = Options()
            
            if headless:
                options.add_argument('-headless')
            
            # ===== DESABILITAR EXTENSES PARA ACELERAR STARTUP =====
            options.add_argument('-no-remote')
            options.add_argument('-new-instance')
            
            options.binary_location = firefox_bin
            
            # Anti-automao
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference('useAutomationExtension', False)
            
            # ===== DESABILITAR EXTENSES =====
            options.set_preference("extensions.update.enabled", False)
            options.set_preference("extensions.update.autoUpdateDefault", False)
            options.set_preference("xpinstall.enabled", False)
            
            # ===== OTIMIZAES DE PERFORMANCE =====
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
            
            # Desabilitar notificaes
            options.set_preference("dom.disable_beforeunload", True)
            options.set_preference("browser.sessionstore.resuming_notification.delayed", False)
            
            service = Service(executable_path=GECKODRIVER_PATH)
            t0 = time.time()
            driver = webdriver.Firefox(options=options, service=service)
            print(f"[DRIVER_VT]  Configurando driver... (fallback launch {time.time() - t0:.1f}s)")
            driver.implicitly_wait(10)
            
            if not headless:
                driver.maximize_window()
            else:
                driver.set_window_size(1920, 1080)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("[DRIVER_VT]  Driver VT criado (fallback)")
            return driver
        
        except Exception as e2:
            print(f"[DRIVER_VT]  Falha total: {e2}")
            return None


# ============================================================================
# CRIAR E LOGAR DRIVER
# ============================================================================

def criar_e_logar_driver(driver_type: DriverType) -> Optional[Any]:
    """Cria driver apropriado e faz login"""
    
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]
    
    print(f"\n Criando driver: {driver_type.value}")
    
    try:
        # Criar driver
        if vt_mode:
            driver = criar_driver_vt(headless=headless)
        else:
            driver = criar_driver_pc(headless=headless)
        
        if not driver:
            print(" Falha ao criar driver")
            return None
        
        # Login
        print(" Fazendo login...")
        if not login_cpf(driver):
            print(" Falha no login")
            finalizar_driver_fix(driver)
            return None
        
        # Injecao do Smart Finder (Cache + Auto-Healing)
        try:
            injetar_smart_finder_global(driver)
        except Exception:
            # Não falhar se smart finder não puder ser ativado
            pass
        # Verificação rápida: testar se o cache do SmartFinder é gravável
        try:
            from Fix.smart_finder import carregar_cache, salvar_cache
            cache = carregar_cache() or {}
            test_key = '__SMARTFINDER_Writable_Test__'
            if test_key not in cache:
                try:
                    cache[test_key] = True
                    salvar_cache(cache)
                    # remover o marcador imediatamente
                    cache.pop(test_key, None)
                    salvar_cache(cache)
                except Exception:
                    # Não falhar a criação do arquivo de cache
                    pass
        except Exception:
            pass

        print(" Driver criado e logado com sucesso")
        return driver
        
    except Exception as e:
        print(f" Erro ao criar driver: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# FUNES DE EXECUO
# ============================================================================

def normalizar_resultado(resultado: Any) -> Dict[str, Any]:
    """Normaliza retorno para dict padro"""
    if isinstance(resultado, dict):
        return resultado
    if isinstance(resultado, bool):
        return {"sucesso": resultado, "status": "OK" if resultado else "ERRO"}
    if resultado is None:
        return {"sucesso": False, "status": "ERRO", "erro": "Mdulo retornou None"}
    return {"sucesso": False, "status": "ERRO", "erro": str(resultado)}


def resetar_driver(driver) -> bool:
    """Reseta driver entre módulos"""
    try:
        print(" Resetando driver...")

        # Fechar abas extras
        abas = driver.window_handles
        if len(abas) > 1:
            for aba in abas[1:]:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except:
                    pass
            driver.switch_to.window(abas[0])

        # Resetar zoom
        driver.execute_script("document.body.style.zoom='100%'")

        # Navegar para página inicial
        driver.get("https://pje.trt2.jus.br/pjekz/")
        time.sleep(2)

        print(" Driver resetado")
        return True

    except Exception as e:
        print(f" Erro ao resetar driver: {e}")
        return False


def executar_bloco_completo(driver) -> Dict[str, Any]:
    """Bloco Completo: Mandado  Prazo  PEC"""
    resultados = {
        "mandado": None,
        "prazo": None,
        "p2b": None,
        "pec": None,
        "sucesso_geral": False
    }
    try:
        print("=" * 80)
        print("BLOCO COMPLETO: MANDADO  PRAZO  PEC")
        print("=" * 80)

        resultados["mandado"] = _executar_mandado_bloco(driver)
        resultados["prazo"] = _executar_prazo_bloco(driver)
        resultados["p2b"] = _executar_p2b_bloco(driver)
        resultados["pec"] = _executar_pec_bloco(driver)

        todos_sucesso = all([
            resultados["mandado"].get("sucesso", False),
            resultados["prazo"].get("sucesso", False),
            resultados["p2b"].get("sucesso", False),
            resultados["pec"].get("sucesso", False)
        ])
        resultados["sucesso_geral"] = todos_sucesso

        print("=" * 80)
        print(" RESUMO DO BLOCO COMPLETO:")
        print(f"  Mandado: {'' if resultados['mandado'].get('sucesso', False) else ''}")
        print(f"  Prazo:   {'' if resultados['prazo'].get('sucesso', False) else ''}")
        print(f"  PEC:     {'' if resultados['pec'].get('sucesso', False) else ''}")
        print(f"  GERAL:   {' SUCESSO' if todos_sucesso else ' FALHAS PARCIAIS'}")
        print("=" * 80)

        return resultados
    except Exception as e:
        print(f" Erro no bloco completo: {e}")
        resultados["erro_geral"] = str(e)
        return resultados


def executar_mandado(driver) -> Dict[str, Any]:
    """Mandado Isolado — API (sem navegação DOM inicial)"""
    print("\n" + "=" * 80)
    print(" MANDADO ISOLADO")
    print("=" * 80)
    inicio = datetime.now()
    try:
        resultado = processar_mandados_devolvidos_api(driver)
        resultado = normalizar_resultado(resultado)
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        if resultado.get("sucesso"):
            print(f"[MANDADO]  Concluído")
        else:
            print(f"[MANDADO]  Falha: {resultado.get('erro', 'Desconhecido')}")
        return resultado
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[MANDADO]  Exceção: {e}")
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e), "tempo": tempo}


def executar_prazo(driver) -> Dict[str, Any]:
    """Prazo Isolado — loop ciclo1+2+3 + P2B (sempre executa p2b mesmo se loop falhar)."""
    print("\n" + "=" * 80)
    print(" PRAZO ISOLADO")
    print("=" * 80)

    inicio = datetime.now()

    resultado_loop = {"sucesso": False, "erro": "não executado"}
    resultado_p2b = {"sucesso": False, "erro": "não executado"}

    try:
        print("[PRAZO] Executando loop_prazo (ciclo1 + ciclo2 + ciclo3)...")
        resultado_loop = loop_prazo(driver)
        resultado_loop = normalizar_resultado(resultado_loop)
        if resultado_loop.get("sucesso"):
            print("[PRAZO] ✅ loop_prazo concluído")
        else:
            print(f"[PRAZO] ⚠ loop_prazo com falha: {resultado_loop.get('erro')} — continuando com P2B")
    except Exception as e:
        print(f"[PRAZO] ⚠ Exceção no loop_prazo: {e} — continuando com P2B")
        resultado_loop = {"sucesso": False, "erro": str(e)}

    try:
        print("[PRAZO] Executando P2B (atividades sem prazo XS)...")
        resultado_p2b = executar_p2b(driver)
        resultado_p2b = normalizar_resultado(resultado_p2b)
        if resultado_p2b.get("sucesso"):
            print("[PRAZO] ✅ P2B concluído")
        else:
            print(f"[PRAZO] ⚠ P2B com falha: {resultado_p2b.get('erro')}")
    except Exception as e:
        print(f"[PRAZO] ⚠ Exceção no P2B: {e}")
        resultado_p2b = {"sucesso": False, "erro": str(e)}

    tempo = (datetime.now() - inicio).total_seconds()
    sucesso_geral = resultado_loop.get("sucesso", False) and resultado_p2b.get("sucesso", False)

    return {
        "sucesso": sucesso_geral,
        "status": "SUCESSO" if sucesso_geral else "PARCIAL",
        "tempo": tempo,
        "loop_prazo": resultado_loop,
        "p2b": resultado_p2b,
    }


def executar_pec(driver) -> Dict[str, Any]:
    """PEC Isolado — API modular (sem navegação DOM inicial)"""
    print("\n" + "=" * 80)
    print(" PEC ISOLADO")
    print("=" * 80)
    inicio = datetime.now()
    try:
        resultado = pec_fluxo_api(driver)
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        print(f"[PEC] Total: {resultado.get('total', 0)} | Sucesso: {resultado.get('sucesso_count', resultado.get('total', 0) - resultado.get('erro', 0))} | Erro: {resultado.get('erro', 0)}")
        return resultado
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[PEC] Excecao: {e}")
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e), "tempo": tempo}


def executar_triagem(driver) -> Dict[str, Any]:
    """Triagem Isolada — fluxo completo com análise pós-triagem e ações por alerta."""
    print("\n" + "=" * 80)
    print(" TRIAGEM ISOLADA")
    print("=" * 80)
    inicio = datetime.now()
    try:
        from Triagem.runner import run_triagem
        resultado = run_triagem(driver)
        tempo = (datetime.now() - inicio).total_seconds()
        if resultado is None:
            return {"sucesso": False, "status": "ERRO_EXECUCAO", "tempo": tempo,
                    "erro": "run_triagem retornou None"}
        resultado["tempo"] = tempo
        print(f"[TRIAGEM] Processados: {resultado.get('processados', 0)} / "
              f"{resultado.get('total', '?')} "
              f"| Sucesso: {resultado.get('sucesso_count', '?')}")
        return resultado
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[TRIAGEM] Exceção: {e}")
        traceback.print_exc()
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e), "tempo": tempo}


def executar_pet(driver) -> Dict[str, Any]:
    """Petição Isolada — fluxo completo de petições (escaninho)."""
    print("\n" + "=" * 80)
    print(" PETIÇÃO ISOLADA")
    print("=" * 80)
    inicio = datetime.now()
    try:
        from Peticao.pet import run_pet
        resultado = run_pet(driver)
        tempo = (datetime.now() - inicio).total_seconds()
        if resultado is None:
            return {"sucesso": False, "status": "ERRO_EXECUCAO", "tempo": tempo,
                    "erro": "run_pet retornou None"}
        resultado["tempo"] = tempo
        return resultado
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[PET] Exceção: {e}")
        traceback.print_exc()
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e), "tempo": tempo}


def executar_p2b(driver) -> Dict[str, Any]:
    """P2B Isolado (API GIGS sem prazo XS + processamento por processo)"""
    print("\n" + "=" * 80)
    print(" P2B ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Executar API + fluxo de cada processo (substitui lista antiga)
        print("[P2B] Executando fluxo_prazo via API GIGS sem prazo XS...")
        from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b, testar_gigs_sem_prazo
        atividades = testar_gigs_sem_prazo(driver, tamanho_pagina=100)
        print(f"[P2B] Processos encontrados: {len(atividades)}")
        if atividades:
            numeros_processos = [item.get('processo', {}).get('numero') or item.get('numeroProcesso') or item.get('numero') for item in atividades]
            print(f"[P2B] Números dos processos: {numeros_processos}")

        resultado = processar_gigs_sem_prazo_p2b(driver, tamanho_pagina=100, max_processos=0)

        print("[P2B]  Processamento individual concluído")
        
        tempo = (datetime.now() - inicio).total_seconds()

        sucesso = resultado.get('sucesso', False)
        return {
            'sucesso': sucesso,
            'status': 'SUCESSO' if sucesso else 'FALHA',
            'tempo': tempo,
            'detalhes': resultado,
        }
        
    except Exception as e:
        print(f"[P2B]  Erro: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


# ============================================================================
# MENUS
# ============================================================================

def menu_ambiente() -> Optional[DriverType]:
    """Menu 1: Selecionar Ambiente"""
    print("\n" + "=" * 80)
    print(" MENU 1: SELECIONAR AMBIENTE")
    print("=" * 80)
    print("\n  A - PC + Visvel (1.py)")
    print("  B - PC + Headless (1b.py)")
    print("  C - VT + Visvel (2.py)")
    print("  D - VT + Headless (2b.py)")
    print("\n  [DEBUG] Adicione 'D' no final para modo debug interativo")
    print("           Ex: 'DD' = VT Headless + Debug ativo")
    print("  X - Cancelar")
    print("=" * 80)
    
    while True:
        opcao = input("\n Escolha um ambiente (A/B/C/D/X ou AD/BD/CD/DD para debug): ").strip().upper()
        
        #  NOVO: Detectar modo debug
        debug_mode = opcao.endswith('D') and len(opcao) > 1
        if debug_mode:
            opcao = opcao[0]  # Remove 'D' do final
        
        if opcao == "X":
            return None, False
        elif opcao == "A":
            return DriverType.PC_VISIBLE, debug_mode
        elif opcao == "B":
            return DriverType.PC_HEADLESS, debug_mode
        elif opcao == "C":
            return DriverType.VT_VISIBLE, debug_mode
        elif opcao == "D":
            return DriverType.VT_HEADLESS, debug_mode
        else:
            print(" Opo invlida!")


def menu_execucao() -> Optional[str]:
    """Menu 2: Selecionar Fluxo"""
    print("\n" + "=" * 80)
    print("  MENU 2: SELECIONAR FLUXO DE EXECUÇÃO")
    print("=" * 80)
    print("\n  A - Bloco Completo (Mandado → Prazo → PEC)")
    print("  B - Mandado Isolado")
    print("  C - Prazo Isolado (ciclo1+2+3 + P2B)")
    print("  D - P2B Isolado")
    print("  E - PEC Isolado")
    print("  F - Triagem Isolada (análise pós-triagem com alertas)")
    print("  G - Petição Isolada (escaninho)")
    print("  X - Cancelar")
    print("=" * 80)

    while True:
        opcao = input("\n Escolha um fluxo (A/B/C/D/E/F/G/X): ").strip().upper()

        if opcao == "X":
            return None
        elif opcao in ["A", "B", "C", "D", "E", "F", "G"]:
            return opcao
        else:
            print(" Opção inválida!")


# ============================================================================
# CONFIGURAO DE LOGGING
# ============================================================================

def configurar_logging(driver_type: DriverType):
    """Configura logging baseado no tipo de driver"""
    
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]
    
    # Suprimir logs ruidosos do urllib3.connectionpool sempre (evita flood no terminal)
    # e reduzir logs do Selenium quando em headless
    logging.getLogger('urllib3.connectionpool').disabled = True
    if headless:
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
    
    # Arquivo de log
    env_name = "VT" if vt_mode else "PC"
    mode_name = "Headless" if headless else "Visible"
    log_file = os.path.join(LOG_DIR, f"x_{env_name}_{mode_name}_{TIMESTAMP}.log")
    
    # Configurar TeeOutput para capturar print()
    tee = TeeOutput(log_file)
    sys.stdout = tee
    
    # Configurar logging (para logger.info(), logger.error(), etc.)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remover handlers antigos se existirem
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Adicionar FileHandler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', 
                                 datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Adicionar StreamHandler para console (vai passar por TeeOutput)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(name)s] %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    return log_file, tee


def safe_immediate_shutdown(driver, tee_output=None, reason=None):
    """Força shutdown imediato: suprime logs ruidosos, finaliza driver e sai do processo.

    Usa `finalizar_driver_imediato_fix` (que mata processos) e `os._exit(0)` para liberar o terminal
    imediatamente — isso evita flood de mensagens de `urllib3.connectionpool` durante teardown.
    """
    try:
        import logging as _logging
        try:
            _logging.getLogger('urllib3.connectionpool').disabled = True
            _logging.getLogger('urllib3').setLevel(_logging.CRITICAL)
        except Exception:
            pass
        try:
            # tentar finalizar de forma imediata (mata geckodriver/firefox)
            finalizar_driver_imediato_fix(driver)
        except Exception:
            pass
        try:
            if tee_output:
                tee_output.close()
        except Exception:
            pass
    finally:
        # Saída imediata sem executar handlers adicionais
        os._exit(0)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funo principal"""
    global skip_finalizar
    
    #  NOVO: Inicializar otimizaes
    try:
        from Fix.otimizacao_wrapper import inicializar_otimizacoes
        inicializar_otimizacoes()
    except:
        pass
    
    tee_output = None
    log_file = None
    try:
        while True:
            # Menu 1: Ambiente
            resultado_menu = menu_ambiente()
            if not resultado_menu:
                print(" Cancelado")
                break

            driver_type, debug_mode = resultado_menu
            debug_mode = False  # Debug mode desabilitado por enquanto

            # Menu 2: Fluxo
            fluxo = menu_execucao()
            if not fluxo:
                print("Cancelado")
                continue

            # Configurar logging
            log_file, tee_output = configurar_logging(driver_type)

            print("\n" + "=" * 80)
            print("ORQUESTRADOR UNIFICADO PJEPlus")
            print("=" * 80)
            print(f" Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(f" Ambiente: {driver_type.value}")
            print(f"  Fluxo: {fluxo}")
            print(f" Log: {log_file}")
            print("=" * 80)

            # Usar context manager para ciclo de vida do driver
            driver_type_str = "VT" if driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS] else "PC"
            headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
            with driver_session(driver_type_str, headless=headless) as driver:
                # Login
                if not login_cpf(driver):
                    print(" Falha no login")
                    continue
                try:
                    inicio = datetime.now()
                    resultado = None
                    if fluxo == "A":
                        resultado = executar_bloco_completo(driver)
                    elif fluxo == "B":
                        resultado = executar_mandado(driver)
                    elif fluxo == "C":
                        resultado = executar_prazo(driver)
                    elif fluxo == "D":
                        resultado = executar_p2b(driver)
                    elif fluxo == "E":
                        resultado = executar_pec(driver)
                    elif fluxo == "F":
                        resultado = executar_triagem(driver)
                    elif fluxo == "G":
                        resultado = executar_pet(driver)
                    tempo_total = (datetime.now() - inicio).total_seconds()
                    # Relatório final
                    print("\n" + "=" * 80)
                    print(" RELATRIO FINAL")
                    print("=" * 80)
                    if resultado:
                        if 'sucesso_geral' in resultado:
                            print(f" Sucesso geral: {resultado['sucesso_geral']}")
                        elif 'sucesso' in resultado:
                            print(f" Sucesso: {resultado['sucesso']}")
                    print(f"  Tempo total: {tempo_total:.2f}s")
                    print("=" * 80)
                except KeyboardInterrupt:
                    print("\n Interrompido (Ctrl+C) — finalizando imediatamente")
                    try:
                        safe_immediate_shutdown(driver, tee_output, reason='KeyboardInterrupt')
                    except Exception:
                        try:
                            finalizar_driver_imediato_fix(driver)
                        except Exception:
                            pass
                        os._exit(0)
                except Exception as e:
                    print(f" Erro: {e}")
                    import traceback
                    traceback.print_exc()
            # Fechar log
            if tee_output:
                tee_output.close()
            print("Encerrando")
            break
    
    except KeyboardInterrupt:
        print("\n Interrompido pelo usurio — finalizando imediatamente")
        try:
            safe_immediate_shutdown(driver, tee_output, reason='OuterKeyboardInterrupt')
        except Exception:
            try:
                finalizar_driver_imediato_fix(driver)
            except Exception:
                pass
            os._exit(0)
    except Exception as e:
        print(f" Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            try:
                if not skip_finalizar:
                    finalizar_driver_fix(driver)
            except:
                pass
        if tee_output:
            tee_output.close()
        
        #  NOVO: Finalizar otimizaes
        try:
            from Fix.otimizacao_wrapper import finalizar_otimizacoes
            finalizar_otimizacoes()
        except:
            pass


if __name__ == "__main__":
    print("=" * 80)
    print("ORQUESTRADOR UNIFICADO PJEPlus (x.py)")
    print("=" * 80)
    print(f"Executando como: {os.path.basename(__file__)}")
    print("100% STANDALONE - Nao depende de 1.py, 1b.py, 2.py, 2b.py")
    print("=" * 80 + "\n")
    
    try:
        main()
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)
    finally:
        print("\n" + "=" * 80)
        print("Orquestrador finalizado")
        print("=" * 80)
    
    sys.exit(0)
