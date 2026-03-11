"""
f.py - Script de Teste Rápido com estrutura fixa
===================================================

ESTRUTURA FIXA (NÃO MODIFICAR):
1. Escolha de Driver PJE (VT ou PC) - sempre visível
2. Login CPF
3. URL de navegação
4. Funções de teste (modificar apenas esta seção)

Uso:
    py f.py
    >> Escolha: [V] VT ou [P] PC
"""

import sys
import io
import os
import time
import logging

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from Fix.core import finalizar_driver
from Fix.utils import login_cpf

# Configurar logging para capturar logs de Fix.* durante execução do f.py
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Apenas INFO e acima globalmente
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

# Stream handler (stdout) - apenas INFO
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
sh.setLevel(logging.INFO)
logger.addHandler(sh)

# File handler - apenas INFO
try:
    fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), 'f_py_debug.log'), encoding='utf-8')
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)
except Exception:
    pass

# Silenciar logs extremamente verbose de selenium e urllib3
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
logging.getLogger('selenium.webdriver.remote').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)


# ============================================================================
# SEÇÃO 1: CONFIGURAÇÕES DE NAVEGAÇÃO (MODIFICAR AQUI)
# ============================================================================

# URL para navegar após login (caso de teste solicitado)
URL_NAVEGACAO = "https://pje.trt2.jus.br/pjekz/processo/3524536/detalhe"

# Dados adicionais (se necessário para testes)
NUMERO_PROCESSO = "3524536"


# ============================================================================
# CONFIGURAÇÕES GLOBAIS (NÃO MODIFICAR)
# ============================================================================

GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'Fix', 'geckodriver.exe')


# ============================================================================
# FUNÇÕES DE CRIAÇÃO DE DRIVER (BASEADAS EM X.PY - NÃO MODIFICAR)
# ============================================================================

def criar_driver_pc_visivel():
    """
    Cria driver Firefox para PC - VISÍVEL
    Firefox Developer Edition com configurações otimizadas.
    """
    print("[DRIVER] 🔧 Criando driver PC (visível)...")
    
    try:
        options = Options()
        
        # Configurações de automação
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference("general.useragent.override", 
                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
        
        # Cache e performance
        options.set_preference("browser.cache.disk.enable", True)
        options.set_preference("browser.cache.memory.enable", True)
        options.set_preference("browser.cache.offline.enable", True)
        options.set_preference("network.http.use-cache", True)
        
        # Notificações
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
        driver.maximize_window()
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[DRIVER] ✅ Driver PC criado com sucesso")
        return driver
        
    except Exception as e:
        print(f"[DRIVER] ❌ Erro ao criar driver PC: {e}")
        raise


def criar_driver_vt_visivel():
    """
    Cria driver Firefox para VT - VISÍVEL
    Configurações VT com otimizações de startup.
    """
    print("[DRIVER] 🔧 Criando driver VT (visível)...")
    
    # Configurações VT
    FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
    FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    
    # Encontrar binário Firefox
    firefox_bin = None
    for bin_path in [FIREFOX_BINARY, FIREFOX_BINARY_ALT]:
        if os.path.exists(bin_path):
            firefox_bin = bin_path
            break
    
    if not firefox_bin:
        print(f"[DRIVER] ❌ Nenhum binário Firefox encontrado")
        raise Exception("Firefox Developer Edition não encontrado")
    
    print(f"[DRIVER] Usando binário: {firefox_bin}")
    
    try:
        options = Options()
        
        # Desabilitar extensões para acelerar startup
        options.add_argument('-no-remote')
        options.add_argument('-new-instance')
        
        options.binary_location = firefox_bin
        
        # Anti-automação
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        
        # Desabilitar extensões
        options.set_preference("extensions.update.enabled", False)
        options.set_preference("extensions.update.autoUpdateDefault", False)
        options.set_preference("xpinstall.enabled", False)
        
        # Otimizações de performance
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
        
        # Performance geral
        options.set_preference("browser.startup.homepage", "about:blank")
        options.set_preference("startup.homepage_welcome_url", "about:blank")
        options.set_preference("browser.startup.page", 0)
        options.set_preference("datareporting.healthreport.uploadEnabled", False)
        options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
        options.set_preference("toolkit.telemetry.enabled", False)
        
        service = Service(executable_path=GECKODRIVER_PATH)
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(30)
        driver.implicitly_wait(10)
        driver.maximize_window()
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[DRIVER] ✅ Driver VT criado com sucesso")
        return driver
    except Exception as e:
        print(f"[DRIVER] ❌ Erro ao criar driver VT: {e}")
        raise


# ============================================================================
# SEÇÃO 3: FUNÇÕES DE TESTE (MODIFICAR AQUI CONFORME NECESSÁRIO)
# ============================================================================

def executar_testes(driver_pje):
    """
    TESTE ISOLADO: Execução de `pec_decisao` (wrapper) no processo já aberto
    """
    print("\n" + "=" * 80)
    print("TESTE ISOLADO: pec_decisao")
    print("=" * 80)

    try:
        from atos.wrappers_pec import pec_excluiargos
        import time

        print("\n[1/1] Executando pec_excluiargos (wrapper) com timing detalhado...")
        print("-" * 80)

        inicio_total = time.time()
        try:
            print(f"[PEC_EXCLUIARGOS] Iniciando processo {NUMERO_PROCESSO}...")
            resultado = pec_excluiargos(driver_pje, numero_processo=NUMERO_PROCESSO, debug=True)
            tempo_total = time.time() - inicio_total

            print("-" * 80)
            print(f"[PEC_EXCLUIARGOS] Resultado: {resultado}")
            print(f"[PEC_EXCLUIARGOS] Tempo total: {tempo_total:.2f}s")

            if resultado:
                print("✅ pec_excluiargos executado com sucesso")
                return True
            else:
                print("⚠️ pec_excluiargos retornou False")
                return False

        except Exception as e:
            tempo_total = time.time() - inicio_total
            print("-" * 80)
            print(f"❌ pec_excluiargos FALHOU: {e}")
            print(f"[PEC_EXCLUIARGOS] Tempo até erro: {tempo_total:.2f}s")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# EXECUÇÃO PRINCIPAL (NÃO MODIFICAR)
# ============================================================================

def main():
    """Execução principal com escolha de driver"""
    driver_pje = None
    
    try:
        print("=" * 80)
        print("F.PY - SCRIPT DE TESTE RÁPIDO")
        print("=" * 80)
        
        # 1. ESCOLHER DRIVER (PJE) - DEFAULT PARA PC
        print("\n[1/3] Escolha o tipo de driver PJE: (default P)")
        # opção VT comentada por padrão
        # print("  [V] VT (máquina específica)")
        print("  [P] PC (padrão)")

        # allow non-interactive choice via env var or CLI arg for automated runs
        escolha = None
        if len(sys.argv) > 1:
            escolha = sys.argv[1].strip().upper()
        if not escolha:
            escolha = os.environ.get('F_CHOICE', '').strip().upper()
        # se nada fornecido, usar PC por padrão (P)
        if not escolha:
            escolha = 'P'
        
        if escolha == 'V':
            driver_pje = criar_driver_vt_visivel()
        elif escolha == 'P':
            driver_pje = criar_driver_pc_visivel()
        else:
            print(f"❌ Opção inválida: {escolha}")
            return False
        
        # 2. LOGIN PJE
        print("\n[2/3] Fazendo login no PJE...")
        sucesso_login = login_cpf(driver_pje)
        if not sucesso_login:
            print("❌ Falha no login")
            return False
        print("✅ Login PJE concluído")
        
        # 3. NAVEGAR PARA PROCESSO
        print(f"\n[3/3] Navegando para processo: {URL_NAVEGACAO}")
        driver_pje.get(URL_NAVEGACAO)
        time.sleep(2)
        print("✅ Processo aberto no PJE")
        
        # 4. EXECUTAR TESTES
        resultado = executar_testes(driver_pje)
        
        # 5. AGUARDAR ANTES DE FECHAR
        print("\n" + "=" * 80)
        print("TESTES CONCLUÍDOS - Pressione Enter para fechar o browser...")
        input()
        
        return resultado is not None
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Execução interrompida pelo usuário (Ctrl+C)")
        return False
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Fechar driver PJE
        if driver_pje:
            try:
                finalizar_driver(driver_pje)
                print("\n[CLEANUP] ✅ Driver PJE fechado")
            except:
                pass


if __name__ == "__main__":
    main()
