"""
f.py - Script de Teste Rápido (xx)
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
import json
import io
import os
import time

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from Fix.drivers import finalizar_driver as finalizar_driver_fix
from Fix.utils import login_cpf


# ============================================================================
# SEÇÃO 1: CONFIGURAÇÕES DE NAVEGAÇÃO (MODIFICAR AQUI)
# ============================================================================

# URL para navegar após login (usar None para deixar a função de teste controlar)
URL_NAVEGACAO = "https://pje.trt2.jus.br/pjekz/processo/7183091/detalhe/peticao/443515232"


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
# SEÇÃO 2: FUNÇÕES DE TESTE (MODIFICAR AQUI CONFORME NECESSÁRIO)
# ============================================================================

# IMPORTAR APENAS FUNÇÕES PRONTAS DO xx
from Fix.core import buscar_documento_argos
from Mandado.regras import aplicar_regras_argos

# Configuracoes do teste (ajustar conforme necessario)
RESULTADO_SISBAJUD = "positivo"
SIGILO_ANEXOS = {}


def testar_decisao_argos(driver_pje):
    """Busca decisao e aplica regras Argos a partir dela."""
    print('[TESTE] Buscando documento com regra Argos...')
    resultado_documento = buscar_documento_argos(driver_pje, log=True)
    if not resultado_documento or not resultado_documento[0]:
        print('[TESTE] ❌ Nenhum documento Argos encontrado')
        return False

    documento_texto, documento_tipo = resultado_documento[0], resultado_documento[1]
    if not documento_texto or not documento_tipo:
        print('[TESTE] ❌ Documento invalido')
        return False

    print(f'[TESTE] Documento: tipo={documento_tipo}, chars={len(documento_texto)}')
    print('[TESTE] Aplicando regras...')
    return aplicar_regras_argos(
        driver_pje,
        RESULTADO_SISBAJUD,
        SIGILO_ANEXOS,
        documento_tipo,
        documento_texto,
        debug=True
    )


# Lista de funcoes e kwargs para teste
TESTE_FUNCOES = [
    {"nome": "testar_decisao_argos", "func": testar_decisao_argos, "kwargs": {}},
]


def executar_testes(driver_pje):
    """Executa as funcoes definidas em TESTE_FUNCOES."""
    print("\n" + "=" * 80)
    print("TESTES - EXECUCAO DIRETA")
    print("=" * 80)

    try:
        for item in TESTE_FUNCOES:
            nome = item.get("nome") or getattr(item.get("func"), "__name__", "func")
            func = item.get("func")
            kwargs = item.get("kwargs", {})

            if not func:
                print(f"[TESTE] ❌ Funcao invalida: {nome}")
                return False

            print(f"[TESTE] Executando {nome}...")
            resultado = func(driver_pje, **kwargs)
            if resultado is False:
                print(f"❌ {nome} retornou False")
                return False

        print("✅ Testes executados com sucesso")
        return True

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
        
        # 1. ESCOLHER DRIVER (PJE)
        print("\n[1/3] Escolha o tipo de driver PJE:")
        print("  [V] VT (máquina específica)")
        print("  [P] PC (padrão)")
        
        escolha = input("\nDigite V ou P: ").strip().upper()
        
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
        
        # 3. NAVEGAR PARA PROCESSO (opcional)
        if URL_NAVEGACAO:
            print(f"\n[3/3] Navegando para processo: {URL_NAVEGACAO}")
            driver_pje.get(URL_NAVEGACAO)
            time.sleep(2)
            print("✅ Processo aberto no PJE")
        else:
            print("\n[3/3] Navegação inicial pulada (controlada pelos testes).")
        
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
                finalizar_driver_fix(driver_pje)
                print("\n[CLEANUP] ✅ Driver PJE fechado")
            except:
                pass


if __name__ == "__main__":
    main()