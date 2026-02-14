"""
prov.py - Processamento Isolado com Progresso Permanente
==========================================================
Script executável isoladamente que:
1. Cria driver próprio com login
2. Navega para painel de processos
3. Aplica filtro 100
4. Seleciona processos via GIGS (AJ-JT/requisição) + livres
5. Aplica atividade XS a todos selecionados
6. Registra em arquivo permanente prov.json para evitar duplicação

Autor: Sistema PJEPlus
Data: 04/12/2025
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver

# Imports dos módulos refatorados (ajuste de path para Prazo/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Fix.core import finalizar_driver
from Fix.utils import login_cpf
from Fix.variaveis import PjeApiClient, buscar_atividade_gigs_por_observacao, session_from_driver
from Prazo.loop import (
    _ciclo2_aplicar_filtros,
    _extrair_numero_processo_da_linha,
    _selecionar_processos_por_gigs_aj_jt,
    _ciclo2_processar_livres,
    _ciclo2_criar_atividade_xs
)
from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado
)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

TIPO_EXECUCAO = 'prov'
URL_PAINEL = 'https://pje.trt2.jus.br/pjekz/painel/global/6/lista-processos'

# Caminhos do Geckodriver
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'Fix', 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    # Fallback: tenta na raiz
    GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'geckodriver.exe')

# Firefox Developer Edition
FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

# Perfis VT
VT_PROFILE_PJE = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
VT_PROFILE_PJE_ALT = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'

# Uso de perfil compartilhado deixa o startup mais lento; desligado por padrão
USAR_PERFIL_VT = False

# Suprimir logs internos
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

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
        print(f"[PROV] ❌ Tipo de driver inválido: {tipo}")
        return None


def _criar_driver_vt(headless=False):
    """
    Cria driver VT com perfil e todas as otimizações
    Tenta: FIREFOX_BINARY → FIREFOX_BINARY_ALT
    Tenta: VT_PROFILE_PJE → VT_PROFILE_PJE_ALT → sem perfil
    """
    if not os.path.exists(GECKODRIVER_PATH):
        print(f"[PROV_DRIVER_VT] ❌ Geckodriver não encontrado em {GECKODRIVER_PATH}")
        return None
    
    # Encontra o binário Firefox
    firefox_binaries = [FIREFOX_BINARY, FIREFOX_BINARY_ALT]
    firefox_bin_usado = None
    
    for bin_path in firefox_binaries:
        if os.path.exists(bin_path):
            firefox_bin_usado = bin_path
            break
    
    if not firefox_bin_usado:
        print(f"[PROV_DRIVER_VT] ❌ Nenhum binário Firefox encontrado")
        print(f"  Tentei: {firefox_binaries}")
        return None
    
    print(f"[PROV_DRIVER_VT] 📦 Usando binário: {firefox_bin_usado}")
    
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
                print(f"[PROV_DRIVER_VT] 🎯 Perfil primário: OK")
            elif os.path.exists(VT_PROFILE_PJE_ALT):
                options.profile = VT_PROFILE_PJE_ALT
                print(f"[PROV_DRIVER_VT] 🎯 Perfil alternativo: OK")
            else:
                print(f"[PROV_DRIVER_VT] ⚠️ Sem perfil, usando temporário")
        else:
            print(f"[PROV_DRIVER_VT] 🚀 USAR_PERFIL_VT desativado -> perfil limpo temporário")
        
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
        print("[PROV_DRIVER_VT] ⏳ Criando instância Firefox...")
        t0 = time.time()
        driver = webdriver.Firefox(options=options, service=service)
        print(f"[PROV_DRIVER_VT] ⏳ Configurando driver... (launch {time.time() - t0:.1f}s)")
        driver.implicitly_wait(10)
        
        if not headless:
            driver.maximize_window()
        else:
            driver.set_window_size(1920, 1080)
        
        # Ocultar webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[PROV_DRIVER_VT] ✅ Driver VT criado com sucesso")
        return driver
        
    except Exception as e:
        print(f"[PROV_DRIVER_VT] ⚠️ Erro com perfil: {e}")
        print("[PROV_DRIVER_VT] 🔄 Fallback: criando sem perfil...")
        
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
            print(f"[PROV_DRIVER_VT] ⏳ Configurando driver... (fallback launch {time.time() - t0:.1f}s)")
            driver.implicitly_wait(10)
            
            if not headless:
                driver.maximize_window()
            else:
                driver.set_window_size(1920, 1080)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("[PROV_DRIVER_VT] ✅ Driver VT criado (fallback sem perfil)")
            return driver
        
        except Exception as e2:
            print(f"[PROV_DRIVER_VT] ❌ Falha total: {e2}")
            return None


def _criar_driver_pc(headless=False):
    """
    COMENTADO - Alternativa para ambiente PC
    Descomente se precisar usar em ambiente local com diferentes configurações
    """
    pass
    # Implementar se necessário



def criar_e_logar_driver() -> Optional[WebDriver]:
    """Cria driver e faz login no PJE"""
    try:
        print("[PROV] 🚀 Criando driver...")
        driver = criar_driver(headless=False)
        
        if not driver:
            print("[PROV] ❌ Falha ao criar driver")
            return None
        
        print("[PROV] 🔐 Fazendo login no PJE...")
        if not login_cpf(driver):
            print("[PROV] ❌ Falha no login")
            finalizar_driver(driver)
            return None
        
        print("[PROV] ✅ Driver criado e logado com sucesso")
        return driver
        
    except Exception as e:
        print(f"[PROV] ❌ Erro ao criar driver: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# FLUXO REUTILIZÁVEL (SEM DRIVER/LOGIN) - PARA INTEGRAÇÃO EM loop.py
# ============================================================================

def fluxo_prov(driver: WebDriver) -> Dict[str, Any]:
    """
    Fluxo completo de processamento PROV (sem criar driver/login).
    Pode ser integrado diretamente em loop.py após loop_prazo.
    
    Executa:
    1. Carrega progresso permanente (prov.json)
    2. Navega + aplica filtros
    3. Seleciona GIGS + livres
    4. Aplica XS e registra progresso
    
    Args:
        driver: WebDriver já logado
        
    Returns:
        Dict com resultado completo:
        {
            'sucesso': bool,
            'selecao': {'gigs': int, 'livres': int, 'total': int, 'ja_processados': int},
            'processamento': {'processados': int, 'duplicados': int, 'erros': int},
            'tempo_total': float,
            'progresso_atual': int  # Total processado no histórico
        }
    """
    inicio = datetime.now()
    resultado = {
        'sucesso': False,
        'selecao': {'gigs': 0, 'livres': 0, 'total': 0, 'ja_processados': 0},
        'processamento': {'processados': 0, 'duplicados': 0, 'erros': 0},
        'tempo_total': 0,
        'progresso_atual': 0
    }
    
    try:
        print("\n[PROV_FLUXO] 🔄 Iniciando fluxo PROV (integrado)...")
        
        # Carregar progresso
        print("[PROV_FLUXO] 📂 Carregando progresso permanente...")
        progresso = carregar_progresso_unificado(TIPO_EXECUCAO)
        
        # Navegar + filtros
        print("[PROV_FLUXO] 🌐 Navegando + aplicando filtros...")
        if not navegacao_prov(driver):
            print("[PROV_FLUXO] ⚠️ Aviso na navegação, continuando...")
        
        # Seleção
        print("[PROV_FLUXO] 🎯 Selecionando processos...")
        resultado['selecao'] = selecionar_e_processar(driver, progresso)
        
        # Aplicar XS
        print("[PROV_FLUXO] ✨ Aplicando XS e registrando...")
        resultado['processamento'] = aplicar_xs_e_registrar(driver, progresso)
        
        # Atualizar progresso final
        resultado['progresso_atual'] = len(progresso.get('processos_executados', []))
        resultado['sucesso'] = True
        
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_total'] = tempo_total
        
        print(f"[PROV_FLUXO] ✅ Fluxo concluído em {tempo_total:.2f}s")
        return resultado
        
    except Exception as e:
        print(f"[PROV_FLUXO] ❌ Erro no fluxo: {e}")
        import traceback
        traceback.print_exc()
        resultado['sucesso'] = False
        return resultado


# ============================================================================
# FUNÇÕES DE ORQUESTRAÇÃO
# ============================================================================

def navegacao_prov(driver: WebDriver) -> bool:
    """
    Navega para o painel de processos e aplica APENAS filtro 100 (sem processos).
    NÃO aplica filtros de fases ou tarefas - isso é feito em loop.py.
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        True se navegação e filtro aplicados com sucesso
    """
    try:
        print("\n[PROV] 📍 Navegando para painel de processos...")
        driver.get(URL_PAINEL)
        time.sleep(3)
        
        print("[PROV] 🔍 Aplicando APENAS filtro 100 (sem processos)...")
        from Fix.core import aplicar_filtro_100
        
        try:
            aplicar_filtro_100(driver)
            print("[PROV] ✅ Filtro 100 aplicado com sucesso")
        except Exception as e:
            print(f"[PROV] ⚠️ Erro ao aplicar filtro 100: {e}")
            return False
        
        time.sleep(2)
        print("[PROV] ✅ Navegação e filtro concluídos")
        return True
        
    except Exception as e:
        print(f"[PROV] ❌ Erro na navegação: {e}")
        import traceback
        traceback.print_exc()
        return False


def selecionar_e_processar(driver: WebDriver, progresso: Dict[str, Any]) -> Dict[str, int]:
    """
    Seleciona processos via GIGS (AJ-JT/requisição) e livres.
    Verifica progresso para evitar duplicação.
    
    Args:
        driver: WebDriver Selenium
        progresso: Dict com histórico de processos já processados
        
    Returns:
        Dict com contadores: {'gigs': count, 'livres': count, 'total': count, 'ja_processados': count}
    """
    resultado = {
        'gigs': 0,
        'livres': 0,
        'total': 0,
        'ja_processados': 0
    }
    
    try:
        print("\n[PROV] 🔎 Iniciando seleção de processos...")
        
        # Criar cliente GIGS
        print("[PROV] 🔗 Inicializando cliente GIGS...")
        client = None
        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            print("[PROV] ✅ Cliente GIGS criado com sucesso")
        except Exception as e:
            print(f"[PROV] ⚠️ Erro ao criar cliente GIGS: {e}")
            import traceback
            traceback.print_exc()
            client = None
        
        # Selecionar GIGS (AJ-JT - Verificar Pagamento)
        if client:
            print("[PROV] 🔗 Selecionando processos com GIGS (AJ-JT - Verificar Pagamento)...")
            try:
                count_gigs = _selecionar_processos_por_gigs_aj_jt(driver, client)
                resultado['gigs'] = count_gigs
                print(f"[PROV] ✅ {count_gigs} processos selecionados via GIGS")
            except Exception as e:
                print(f"[PROV] ⚠️ Erro ao selecionar GIGS: {e}")
                resultado['gigs'] = 0
        else:
            print("[PROV] ⏭️  Pulando seleção GIGS (cliente não disponível)")
            resultado['gigs'] = 0
        
        time.sleep(2)
        
        # Selecionar livres
        print("[PROV] 🔓 Selecionando processos livres...")
        try:
            count_livres = _ciclo2_processar_livres(driver, client if client else None)
            resultado['livres'] = count_livres
            print(f"[PROV] ✅ {count_livres} processos livres selecionados")
        except Exception as e:
            print(f"[PROV] ⚠️ Erro ao selecionar livres: {e}")
            resultado['livres'] = 0
        
        resultado['total'] = resultado['gigs'] + resultado['livres']
        
        # Contar já processados
        ja_processados = len(progresso.get('processos_executados', []))
        resultado['ja_processados'] = ja_processados
        
        print(f"\n[PROV] 📊 Resumo de Seleção:")
        print(f"   GIGS (AJ-JT - Verificar Pagamento): {resultado['gigs']}")
        print(f"   Livres: {resultado['livres']}")
        print(f"   Total a processar: {resultado['total']}")
        print(f"   Já processados antes: {ja_processados}")
        
        return resultado
        
    except Exception as e:
        print(f"[PROV] ❌ Erro na seleção de processos: {e}")
        import traceback
        traceback.print_exc()
        return resultado


def aplicar_xs_e_registrar(driver: WebDriver, progresso: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica atividade XS aos processos selecionados e registra no progresso.
    
    Args:
        driver: WebDriver Selenium
        progresso: Dict com histórico (será atualizado)
        
    Returns:
        Dict com resultado: {'processados': count, 'erros': count, 'duplicados': count}
    """
    resultado = {
        'processados': 0,
        'erros': 0,
        'duplicados': 0
    }
    
    try:
        print("\n[PROV] 🔄 Registrando progresso dos processos XS...")
        
        # NOTA: A atividade XS já foi criada em _ciclo2_processar_livres()
        # Aqui apenas registramos no histórico permanente
        
        time.sleep(1)
        
        # Obter processos selecionados (via tabela)
        print("[PROV] 📋 Extraindo números dos processos selecionados...")
        try:
            linhas_selecionadas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag.selecionado')
            if not linhas_selecionadas:
                # Fallback: tentar encontrar checkboxes marcados
                linhas_selecionadas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
            
            processos_para_registrar = []
            for linha in linhas_selecionadas:
                try:
                    numero_processo = _extrair_numero_processo_da_linha(linha)
                    if numero_processo:
                        processos_para_registrar.append(numero_processo)
                except:
                    continue
            
            print(f"[PROV] ✅ Extraídos {len(processos_para_registrar)} números de processo")
            
        except Exception as e:
            print(f"[PROV] ⚠️ Erro ao extrair processos selecionados: {e}")
            processos_para_registrar = []
        
        # Registrar cada processo no progresso
        print("[PROV] 💾 Registrando processos em prov.json...")
        for numero_processo in processos_para_registrar:
            try:
                # Verificar se já foi processado
                if numero_processo in progresso.get('processos_executados', []):
                    print(f"[PROV] ⏭️  Processo {numero_processo} já estava registrado, pulando")
                    resultado['duplicados'] += 1
                    continue
                
                # Marcar como executado
                marcar_processo_executado_unificado(
                    tipo_execucao=TIPO_EXECUCAO,
                    numero_processo=numero_processo,
                    progresso=progresso,
                    sucesso=True
                )
                
                # Salvar imediatamente (segurança contra crash mid-execution)
                salvar_progresso_unificado(TIPO_EXECUCAO, progresso)
                resultado['processados'] += 1
                
            except Exception as e:
                print(f"[PROV] ❌ Erro ao registrar {numero_processo}: {e}")
                resultado['erros'] += 1
        
        print(f"\n[PROV] 📊 Resumo de Processamento:")
        print(f"   Processados: {resultado['processados']}")
        print(f"   Duplicados (já processados): {resultado['duplicados']}")
        print(f"   Erros: {resultado['erros']}")
        
        return resultado
        
    except Exception as e:
        print(f"[PROV] ❌ Erro ao aplicar XS: {e}")
        import traceback
        traceback.print_exc()
        return resultado


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal de orquestração"""
    
    driver = None
    
    try:
        print("=" * 80)
        print("🚀 PROCESSADOR ISOLADO COM PROGRESSO PERMANENTE (prov.py)")
        print("=" * 80)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📝 Tipo: {TIPO_EXECUCAO}")
        print("=" * 80)
        
        # ===== INICIALIZAÇÃO =====
        print("\n[PROV] 🔑 FASE 1: INICIALIZAÇÃO")
        print("-" * 80)
        
        # Carregar progresso
        print("[PROV] 📂 Carregando progresso permanente...")
        progresso = carregar_progresso_unificado(TIPO_EXECUCAO)
        print(f"[PROV] ✅ Progresso carregado: {len(progresso.get('processos_executados', []))} já processados")
        
        # Criar driver
        driver = criar_e_logar_driver()
        if not driver:
            print("[PROV] ❌ Falha ao criar driver. Encerrando.")
            return False
        
        # ===== NAVEGAÇÃO =====
        print("\n[PROV] 🌐 FASE 2: NAVEGAÇÃO E FILTROS")
        print("-" * 80)
        
        if not navegacao_prov(driver):
            print("[PROV] ⚠️ Erro na navegação, mas continuando...")
        
        # ===== SELEÇÃO =====
        print("\n[PROV] 🎯 FASE 3: SELEÇÃO DE PROCESSOS")
        print("-" * 80)
        
        resultado_selecao = selecionar_e_processar(driver, progresso)
        
        # ===== APLICAÇÃO XS =====
        print("\n[PROV] ✨ FASE 4: APLICAÇÃO DE ATIVIDADE XS")
        print("-" * 80)
        
        resultado_xs = aplicar_xs_e_registrar(driver, progresso)
        
        # ===== RELATÓRIO FINAL =====
        print("\n[PROV] 📋 RELATÓRIO FINAL")
        print("=" * 80)
        print(f"⏱️  Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"\n✅ SELEÇÃO:")
        print(f"   GIGS: {resultado_selecao['gigs']}")
        print(f"   Livres: {resultado_selecao['livres']}")
        print(f"   Total selecionado: {resultado_selecao['total']}")
        print(f"   Já processados: {resultado_selecao['ja_processados']}")
        print(f"\n✅ PROCESSAMENTO:")
        print(f"   Novos processados: {resultado_xs['processados']}")
        print(f"   Duplicados: {resultado_xs['duplicados']}")
        print(f"   Erros: {resultado_xs['erros']}")
        print(f"\n📊 PROGRESSO PERMANENTE:")
        print(f"   Total no histórico: {len(progresso.get('processos_executados', []))}")
        print("=" * 80)
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário (Ctrl+C)")
        return False
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if driver:
            print("\n[PROV] 🔚 Finalizando driver...")
            finalizar_driver(driver)
            print("[PROV] ✅ Driver finalizado")


def fluxo_prov_integrado(driver: WebDriver) -> bool:
    """
    Fluxo final de PROV para integração em loop.py.
    
    Executa:
    1. Navegação para painel de cumprimento de providências (painel global 6)
    2. Aplicar filtro 100 (sem processos)
    3. Selecionar processos livres
    4. Aplicar atividade XS uma única vez
    
    Args:
        driver: WebDriver já logado
        
    Returns:
        True se sucesso, False se falha crítica
    """
    try:
        print("\n[PROV_INTEGRADO] 🚀 Iniciando fluxo final PROV (integrado em loop)...")
        
        # 1. Navegação
        print("[PROV_INTEGRADO] 🌐 Navegando para painel global 6 (cumprimento de providências)...")
        from Prazo.prov import URL_PAINEL
        driver.get(URL_PAINEL)
        time.sleep(3)
        
        # 2. Aplicar filtro 100
        print("[PROV_INTEGRADO] 🔍 Aplicando filtro 100...")
        try:
            from Fix.core import aplicar_filtro_100
            aplicar_filtro_100(driver)
            print("[PROV_INTEGRADO] ✅ Filtro 100 aplicado")
        except Exception as e:
            print(f"[PROV_INTEGRADO] ⚠️ Erro ao aplicar filtro 100: {e}")
            return False
        
        time.sleep(2)
        
        # 3. Selecionar livres
        print("[PROV_INTEGRADO] 📋 Selecionando processos livres...")
        from Prazo.loop import SCRIPT_SELECAO_LIVRES
        livres_selecionados = driver.execute_script(SCRIPT_SELECAO_LIVRES)
        print(f"[PROV_INTEGRADO] ✅ {livres_selecionados} processos livres selecionados")
        
        # 4. Aplicar XS se houver processos
        if livres_selecionados > 0:
            print("[PROV_INTEGRADO] ✨ Aplicando atividade XS...")
            from Prazo.loop import _ciclo2_criar_atividade_xs
            _ciclo2_criar_atividade_xs(driver)
            print("[PROV_INTEGRADO] ✅ Atividade XS aplicada")
        else:
            print("[PROV_INTEGRADO] ℹ️ Nenhum processo livre encontrado")
        
        print("[PROV_INTEGRADO] ✅ Fluxo final concluído com sucesso")
        return True
        
    except Exception as e:
        print(f"[PROV_INTEGRADO] ❌ Erro no fluxo: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    try:
        sucesso = main()
        if sucesso:
            print("\n✅ Execução concluída com sucesso")
            sys.exit(0)
        else:
            print("\n⚠️ Execução concluída com avisos")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal não capturado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
