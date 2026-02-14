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
  - D: PEC Isolado
  - E: P2B Isolado

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

# Selenium imports
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

# Imports dos mdulos refatorados
from Fix.core import finalizar_driver as finalizar_driver_fix
from Fix.utils import login_cpf
from Mandado.core import navegacao as mandado_navegacao, iniciar_fluxo_robusto as mandado_fluxo
from Prazo.loop import loop_prazo
from Prazo.p2b_fluxo import fluxo_pz
from Prazo.p2b_prazo import fluxo_prazo
# PEC Isolado - importar com fallback para compatibilidade
try:
    from PEC.processamento import executar_fluxo_novo as pec_fluxo
except (ImportError, ModuleNotFoundError, AttributeError):
    try:
        # Fallback: se processamento não tem a função, tentar regras
        from PEC.regras import determinar_acoes_por_observacao
        def pec_fluxo(driver):
            print("[PEC] Aviso: usando placeholder para pec_fluxo")
            return {"sucesso": False, "erro": "Função não disponível em processamento"}
    except (ImportError, ModuleNotFoundError):
        def pec_fluxo(driver):
            print("[PEC] Aviso: módulo PEC não carregado")
            return {"sucesso": False, "erro": "Módulo PEC indisponível"}

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
        
        print(" Driver criado e logado com sucesso")
        return driver
        
    except Exception as e:
        print(f" Erro ao criar driver: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# VERIFICAÇÃO DE ACESSO NEGADO - CENTRALIZADA
# ============================================================================

def verificar_acesso_negado(driver, contexto: str = "operação") -> None:
    """
    Verifica se o driver está em página de acesso negado.
    Se detectado, lança exceção para forçar reinício do driver.
    
    Args:
        driver: Instância do WebDriver
        contexto: Nome da operação/módulo para logging
        
    Raises:
        Exception: Com prefixo RESTART_* para forçar reinício
    """
    try:
        url_atual = driver.current_url
        
        # Verificar se é acesso negado
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
            mensagem = f"ACESSO_NEGADO detectado em [{contexto}] - URL: {url_atual}"
            print(f"\n⚠️ {mensagem}")
            print(f"🔄 Lançando exceção para reiniciar driver...\n")
            
            # Lançar exceção para forçar reinício
            raise Exception(f"RESTART_DRIVER: {mensagem}")
            
    except Exception as e:
        # Se a exceção já é de RESTART, propagar
        if "RESTART_" in str(e):
            raise
        # Outros erros na verificação, ignorar
        pass


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
    """Reseta driver entre mdulos"""
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
        
        # Navegar para pgina inicial
        driver.get("https://pje.trt2.jus.br/pjekz/")
        time.sleep(2)
        
        print(" Driver resetado")
        return True
        
    except Exception as e:
        print(f" Erro ao resetar driver: {e}")
        return False


def executar_com_recuperacao(driver, nome_fluxo: str, funcao_execucao, max_tentativas: int = 2) -> Dict[str, Any]:
    """Executa um fluxo com recuperação global de ACESSO_NEGADO.

    Se detectar RESTART_DRIVER, reseta o driver e reexecuta apenas este fluxo.
    """
    tentativa = 0
    while tentativa < max_tentativas:
        try:
            return funcao_execucao(driver)
        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                tentativa += 1
                print(f"[{nome_fluxo}]  ACESSO_NEGADO - resetando driver (tentativa {tentativa}/{max_tentativas})")
                resetar_driver(driver)
                time.sleep(2)
                continue
            raise
    return {"sucesso": False, "erro": f"ACESSO_NEGADO persistente em {nome_fluxo}"}


def executar_bloco_completo(driver) -> Dict[str, Any]:
    """Bloco Completo: Mandado  Prazo  PEC"""
    resultados = {
        "mandado": None,
        "prazo": None,
        "pec": None,
        "sucesso_geral": False
    }
    
    try:
        print("=" * 80)
        print("BLOCO COMPLETO: MANDADO  PRAZO  PEC")
        print("=" * 80)
        
        # 1. MANDADO
        resultados["mandado"] = executar_com_recuperacao(driver, "MANDADO", executar_mandado)
        resetar_driver(driver)
        time.sleep(3)
        
        # 2. PRAZO
        resultados["prazo"] = executar_com_recuperacao(driver, "PRAZO", executar_prazo)
        resetar_driver(driver)
        time.sleep(3)
        
        # 3. PEC
        resultados["pec"] = executar_com_recuperacao(driver, "PEC", executar_pec)
        
        # Verificar sucesso geral
        todos_sucesso = all([
            resultados["mandado"].get("sucesso", False),
            resultados["prazo"].get("sucesso", False),
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
    """Mandado Isolado - Processamento de Documentos Internos"""
    print("\n" + "=" * 80)
    print(" MANDADO ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Navegao especfica do Mandado
        if not mandado_navegacao(driver):
            print("[MANDADO]  Falha na navegao")
            return {
                "sucesso": False, 
                "status": "ERRO_NAVEGACAO", 
                "erro": "Falha ao navegar para documentos internos"
            }
        
        # Executar fluxo principal
        resultado = mandado_fluxo(driver)
        
        # Verificar acesso negado após execução
        verificar_acesso_negado(driver, "MANDADO")
        
        resultado = normalizar_resultado(resultado)
        
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        
        if resultado.get("sucesso"):
            print(f"[MANDADO]  Concludo - {resultado.get('processos', 0)} processos")
        else:
            print(f"[MANDADO]  Falha: {resultado.get('erro', 'Desconhecido')}")
        
        return resultado
        
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[MANDADO]  Exceo: {e}")
        return {
            "sucesso": False, 
            "status": "ERRO_EXECUCAO", 
            "erro": str(e),
            "tempo": tempo
        }


def executar_prazo(driver) -> Dict[str, Any]:
    """Prazo Isolado (loop_prazo + fluxo_pz)"""
    print("\n" + "=" * 80)
    print(" PRAZO ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Executar loop_prazo
        print("[PRAZO] Executando loop_prazo...")
        resultado_loop = loop_prazo(driver)
        
        # Verificar acesso negado após loop_prazo
        verificar_acesso_negado(driver, "PRAZO_LOOP")
        
        resultado_loop = normalizar_resultado(resultado_loop)
        
        if not resultado_loop.get("sucesso"):
            print(f"[PRAZO]  Falha no loop_prazo: {resultado_loop.get('erro')}")
            return resultado_loop
        
        print("[PRAZO]  loop_prazo concludo")
        
        # Executar fluxo_pz (P2B)
        print("[PRAZO] Executando p2b_fluxo...")
        resetar_driver(driver)
        
        fluxo_pz(driver)  # fluxo_pz no retorna valor
        
        # Verificar acesso negado após p2b_fluxo
        verificar_acesso_negado(driver, "PRAZO_P2B")
        
        print("[PRAZO]  p2b_fluxo concludo")
        print("[PRAZO]  Mdulo Prazo completo")
        
        tempo = (datetime.now() - inicio).total_seconds()
        
        return {
            'sucesso': True,
            'status': 'SUCESSO',
            'tempo': tempo,
            'loop_prazo': resultado_loop
        }
        
    except Exception as e:
        print(f"[PRAZO]  Erro: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


def executar_pec(driver) -> Dict[str, Any]:
    """PEC Isolado - Processamento de Execuo"""
    print("\n" + "=" * 80)
    print(" PEC ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Executar fluxo PEC
        resultado = pec_fluxo(driver)
        
        # Verificar acesso negado após PEC
        verificar_acesso_negado(driver, "PEC")
        
        resultado = normalizar_resultado(resultado)
        
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        
        if resultado.get("sucesso"):
            print(f"[PEC]  Concludo - {resultado.get('processos', 0)} processos")
        else:
            print(f"[PEC]  Falha: {resultado.get('erro', 'Desconhecido')}")
        
        return resultado
        
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[PEC]  Exceo: {e}")
        return {
            "sucesso": False, 
            "status": "ERRO_EXECUCAO", 
            "erro": str(e),
            "tempo": tempo
        }


def executar_p2b(driver) -> Dict[str, Any]:
    """P2B Isolado (fluxo completo p2b_prazo)"""
    print("\n" + "=" * 80)
    print(" P2B ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Executar fluxo completo do P2B (lista de atividades + xs)
        print("[P2B] Executando fluxo_prazo...")
        fluxo_prazo(driver)  # fluxo_prazo no retorna valor

        # Verificar acesso negado após fluxo_prazo
        verificar_acesso_negado(driver, "P2B")

        print("[P2B]  fluxo_prazo concludo")

        tempo = (datetime.now() - inicio).total_seconds()

        return {
            'sucesso': True,
            'status': 'SUCESSO',
            'tempo': tempo,
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
    print("  MENU 2: SELECIONAR FLUXO DE EXECUO")
    print("=" * 80)
    print("\n  A - Bloco Completo (Mandado  Prazo  PEC)")
    print("  B - Mandado Isolado")
    print("  C - Prazo Isolado")
    print("  D - PEC Isolado")
    print("  E - P2B Isolado")
    print("  X - Cancelar")
    print("=" * 80)
    
    while True:
        opcao = input("\n Escolha um fluxo (A/B/C/D/E/X): ").strip().upper()
        
        if opcao == "X":
            return None
        elif opcao in ["A", "B", "C", "D", "E"]:
            return opcao
        else:
            print(" Opo invlida!")


# ============================================================================
# CONFIGURAO DE LOGGING
# ============================================================================

def configurar_logging(driver_type: DriverType):
    """Configura logging baseado no tipo de driver"""
    
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]
    
    # Suprimir logs de Selenium/urllib3 se headless
    if headless:
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
    
    # Arquivo de log
    env_name = "VT" if vt_mode else "PC"
    mode_name = "Headless" if headless else "Visible"
    log_file = os.path.join(LOG_DIR, f"x_{env_name}_{mode_name}_{TIMESTAMP}.log")
    
    # Configurar TeeOutput
    tee = TeeOutput(log_file)
    sys.stdout = tee
    
    return log_file, tee


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funo principal"""
    
    #  NOVO: Inicializar otimizaes
    try:
        from Fix.otimizacao_wrapper import inicializar_otimizacoes
        inicializar_otimizacoes()
    except:
        pass
    
    tee_output = None
    log_file = None
    driver = None
    
    try:
        while True:
            # Menu 1: Ambiente
            resultado_menu = menu_ambiente()
            if not resultado_menu:
                print(" Cancelado")
                break
            
            driver_type, debug_mode = resultado_menu
            
            # Debug mode desabilitado por enquanto
            debug_mode = False
            
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
            
            # Criar driver
            driver = criar_e_logar_driver(driver_type)
            if not driver:
                print(" Falha ao criar driver")
                if tee_output:
                    tee_output.close()
                continue
            
            # Executar fluxo
            max_tentativas = 3
            tentativa = 0
            
            while tentativa < max_tentativas:
                try:
                    inicio = datetime.now()
                    resultado = None
                    
                    if fluxo == "A":
                        resultado = executar_bloco_completo(driver)
                    elif fluxo == "B":
                        resultado = executar_com_recuperacao(driver, "MANDADO", executar_mandado)
                    elif fluxo == "C":
                        resultado = executar_com_recuperacao(driver, "PRAZO", executar_prazo)
                    elif fluxo == "D":
                        resultado = executar_com_recuperacao(driver, "PEC", executar_pec)
                    elif fluxo == "E":
                        resultado = executar_com_recuperacao(driver, "P2B", executar_p2b)
                    
                    tempo_total = (datetime.now() - inicio).total_seconds()
                    
                    # Relatório final
                    print("\n" + "=" * 80)
                    print(" RELATÓRIO FINAL")
                    print("=" * 80)
                    if resultado:
                        if 'sucesso_geral' in resultado:
                            print(f" Sucesso geral: {resultado['sucesso_geral']}")
                        elif 'sucesso' in resultado:
                            print(f" Sucesso: {resultado['sucesso']}")
                    print(f"  Tempo total: {tempo_total:.2f}s")
                    print("=" * 80)
                    
                    # Execução bem-sucedida, sair do loop de tentativas
                    break
                    
                except Exception as e:
                    # Verificar se é erro de ACESSO_NEGADO que requer restart
                    if "RESTART_" in str(e):
                        tentativa += 1
                        print(f"\n⚠️ ACESSO NEGADO DETECTADO - Tentativa {tentativa}/{max_tentativas}")
                        print(f"🔄 Reiniciando driver e reexecutando...\n")
                        
                        # Finalizar driver atual
                        if driver:
                            try:
                                finalizar_driver_fix(driver)
                            except:
                                pass
                        
                        # Recriar driver
                        if tentativa < max_tentativas:
                            print("🔧 Criando novo driver...")
                            driver = criar_e_logar_driver(driver_type)
                            if not driver:
                                print("❌ Falha ao recriar driver")
                                break
                            print("✅ Driver recriado com sucesso\n")
                            time.sleep(3)  # Aguardar estabilização
                        else:
                            print(f"❌ Máximo de {max_tentativas} tentativas atingido")
                            break
                    else:
                        # Outros erros, não tentar novamente
                        print(f"❌ Erro: {e}")
                        import traceback
                        traceback.print_exc()
                        break
            
            # Pós-execução: finalizar driver
            try:
                if driver:
                    print("\n Finalizando driver...")
                    finalizar_driver_fix(driver)
                    driver = None
            except Exception as e:
                print(f"⚠️ Erro ao finalizar driver: {e}")
            
            # Fechar log
            if tee_output:
                tee_output.close()
            
            # Finalizar após execução
            print("Encerrando")
            break
    
    except KeyboardInterrupt:
        print("\n Interrompido pelo usurio")
    except Exception as e:
        print(f" Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            try:
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
