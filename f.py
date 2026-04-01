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
from Mandado.core import navegacao as mandado_navegacao, iniciar_fluxo_robusto as mandado_fluxo
from Mandado.processamento_argos import processar_argos
from Mandado.processamento_outros import fluxo_mandados_outros

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
URL_NAVEGACAO = "https://pje.trt2.jus.br/pjekz/processo/6019203/detalhe/"

# Dados adicionais (se necessário para testes)
NUMERO_PROCESSO = "6019203"


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
    print("TESTE ISOLADO: pec_idpj")
    print("=" * 80)

    try:
        from atos.wrappers_pec import pec_idpj
        import time

        print("\n[1/1] Executando pec_idpj (wrapper) com timing detalhado...")
        print("-" * 80)

        inicio_total = time.time()
        try:
            print(f"[PEC_IDPJ] Iniciando processo {NUMERO_PROCESSO}...")
            resultado = pec_idpj(driver_pje, numero_processo=NUMERO_PROCESSO, debug=True)
            tempo_total = time.time() - inicio_total

            print("-" * 80)
            print(f"[PEC_IDPJ] Resultado: {resultado}")
            print(f"[PEC_IDPJ] Tempo total: {tempo_total:.2f}s")

            if resultado:
                print("✅ pec_idpj executado com sucesso")
                return True
            else:
                print("⚠️ pec_idpj retornou False")
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


def obter_mandados_devolvidos(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Retorna a lista de mandados devolvidos via endpoint interno"""
    url = ('https://pje.trt2.jus.br/pje-comum-api/api/escaninhos/documentosinternos'
           f'?mandadosDevolvidos=true&pagina={pagina}&tamanhoPagina={tamanho_pagina}'
           f'&ordenacaoCrescente={str(ordenacao_crescente).lower()}')

    script = f"""
        return (async function() {{
            const url = '{url}';
            const xsrfCookie = document.cookie.split(';').map(c => c.trim())
                .find(c => c.toLowerCase().startsWith('xsrf-token='));
            if (!xsrfCookie) {{ return {{ status: 0, error: 'XSRF_NOT_FOUND' }}; }}
            const xsrf = xsrfCookie.split('=')[1];

            const response = await fetch(url, {{
                method: 'GET',
                credentials: 'include',
                headers: {{
                    'Accept': 'application/json',
                    'X-XSRF-TOKEN': xsrf
                }}
            }});

            const text = await response.text();
            return {{ status: response.status, body: text }};
        }})();
    """

    resultado = driver.execute_script(script)
    status = resultado.get('status')

    if status != 200:
        raise RuntimeError(f"[MANDADOS] Erro HTTP: {status}, payload: {resultado.get('body')}")

    import json
    try:
        data = json.loads(resultado.get('body', '{}'))
    except Exception as e:
        raise RuntimeError(f"[MANDADOS] Falha parse JSON: {e}")

    if isinstance(data, dict):
        processos = data.get('resultado') or data.get('dados') or []
    elif isinstance(data, list):
        processos = data
    else:
        processos = []

    return processos


def test_mandados_devolvidos_api(driver):
    """Teste direto do endpoint /pje-comum-api/api/escaninhos/documentosinternos"""
    print("\n[TESTE-MANDADOS] Consultando API de mandados devolvidos...")

    try:
        processos = obter_mandados_devolvidos(driver)
    except Exception as e:
        print(f"[TESTE-MANDADOS] falha: {e}")
        return False

    print(f"[TESTE-MANDADOS] total de items retornados: {len(processos)}")
    if processos:
        print("[TESTE-MANDADOS] Exemplo de item cru:", processos[0])

    for idx, item in enumerate(processos[:30], start=1):
        processo_obj = item.get('processo') or {}
        processo_id = (processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id'))
        numero = (processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero'))
        tipo = (item.get('tipoAtividade') and (item['tipoAtividade'].get('descricao') or item['tipoAtividade'].get('nome')))
        if not tipo:
            tipo = (item.get('tipo') or item.get('tipoDeDocumento') or item.get('tipoDocumento'))
        status = item.get('statusAtividade') or item.get('status') or item.get('situacao')

        print(f"  {idx:02d} - id_processo: {processo_id} - processo: {numero} - tipo: {tipo} - status: {status}")

    return True


def obter_gigs_sem_prazo_xs(driver, tamanho_pagina=100):
    """Busca via API os registros de GIGS sem prazo (XS), usando logic of new fluxo mandado/filtro XS."""
    from Mandado.processamento_api import testar_api_gigs_sem_prazo

    try:
        resultado = testar_api_gigs_sem_prazo(driver, tamanho_pagina=tamanho_pagina)
    except Exception as e:
        print(f"[P2B] falha ao consultar GIGS sem prazo via API: {e}")
        return []

    print(f"[P2B] total de GIGS sem prazo (XS) retornados: {len(resultado)}")
    if resultado:
        print(f"[P2B] exemplo: {resultado[0]}")

    return resultado


def processar_gigs_sem_prazo_p2b(driver, tamanho_pagina=100):
    """Fluxo de teste p2b: obtém itens XS via endpoint e imprime resumo."""
    gigs = obter_gigs_sem_prazo_xs(driver, tamanho_pagina=tamanho_pagina)
    if not gigs:
        print("[P2B] Nenhum item para processar")
        return False

    for idx, item in enumerate(gigs, start=1):
        processo_obj = item.get('processo') or {}
        id_processo = (processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id'))
        numero = (processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero'))
        descricao = (item.get('tipoAtividade') or {}).get('descricao') or (item.get('tipoAtividade') or {}).get('nome') or item.get('descricao')

        print(f"  {idx:02d} - id: {id_processo} - numero: {numero} - descricao: {descricao}")

    print("[P2B] Fluxo de processamento p2b (apenas listagem) concluído.")
    return True


def processar_prazo_ciclo2(driver):
    """Executa apenas o ciclo2 do loop de Prazo (filtro + livres + não-livres + movimentação)."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from Prazo.loop_ciclo2_processamento import ciclo2

    # 1. Navegar para painel onde ciclo2 começa (depois do painel 14)
    painel_ciclo2 = 'https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos'
    print(f"[PRAZO_CICLO2] Navegando para painel do ciclo2: {painel_ciclo2}")
    driver.get(painel_ciclo2)

    # Esperar página carregar lista de processos
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Fase processual') or contains(text(), 'Fase processual')]"))
        )
    except Exception:
        print('[PRAZO_CICLO2] Aviso: tempo limite ao aguardar elemento de fase processual; prosseguindo mesmo assim')

    # 2-6. Executar ciclo 2 completo (filtros, seleção, XS, não-livres 20 em 20, movimentação, retorno)
    print('[PRAZO_CICLO2] Iniciando ciclo2 (filtro + livres + providências)')
    resultado = ciclo2(driver, opcao_destino='Cumprimento de providências')

    if resultado:
        print('[PRAZO_CICLO2] Ciclo2 finalizado com sucesso')
    else:
        print('[PRAZO_CICLO2] Ciclo2 finalizou com falhas')

    return resultado


def processar_mandado_detalhe(driver, numero_processo, id_processo=None):
    """Abre /processo/{numero}/detalhe/ em nova aba, processa fluxo Mandado e fecha aba."""
    from Fix.core import wait_for_page_load, esperar_elemento

    if id_processo:
        detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/"
    else:
        detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe/"
    initial_handle = driver.current_window_handle

    driver.execute_script("window.open(arguments[0], '_blank');", detalhe_url)
    time.sleep(0.5)
    new_handle = [h for h in driver.window_handles if h != initial_handle]
    if not new_handle:
        print(f"[MANDADOS][ERRO] Não foi possível abrir aba para {numero_processo}")
        return False
    new_handle = new_handle[0]

    driver.switch_to.window(new_handle)

    try:
        wait_for_page_load(driver, timeout=15)
        cabecalho = esperar_elemento(driver, '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title', timeout=15)
        if not cabecalho:
            print(f"[MANDADOS][ERRO] Cabeçalho não encontrado para {numero_processo}")
            return False

        texto_doc = cabecalho.text or ''
        texto_lower = texto_doc.lower()

        if any(term in texto_lower for term in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao', 'certidão de devolução']):
            print(f"[MANDADOS] ({numero_processo}) identificou fluxo Argos")
            return processar_argos(driver, log=True)

        if any(term in texto_lower for term in ['oficial de justica', 'certidao de oficial', 'certidão de oficial', 'oficial de justiça']):
            print(f"[MANDADOS] ({numero_processo}) identificou fluxo Outros")
            fluxo_mandados_outros(driver, log=False)
            return True

        print(f"[MANDADOS] ({numero_processo}) tipo não identificado no cabeçalho: {texto_doc[:40]}")
        return False

    except Exception as e:
        print(f"[MANDADOS][ERRO] Falha ao processar {numero_processo}: {e}")
        return False

    finally:
        try:
            driver.close()
        except Exception:
            pass
        driver.switch_to.window(initial_handle)


def processar_mandados_devolvidos(driver, pagina=1, tamanho_pagina=50, ordenacao_crescente=True):
    """Processa mandados devolvidos via API, abrindo um processo por vez no /detalhe/."""
    mandados = obter_mandados_devolvidos(driver, pagina=pagina, tamanho_pagina=tamanho_pagina, ordenacao_crescente=ordenacao_crescente)

    if not mandados:
        print('[MANDADOS] Nenhum mandado devolvido encontrado para processar')
        return False

    print(f"[MANDADOS] Encontrados {len(mandados)} mandados devolvidos (API)")

    sucesso_total = True
    for idx, item in enumerate(mandados, start=1):
        processo_obj = item.get('processo') or {}
        id_processo = (processo_obj.get('id') or processo_obj.get('idProcesso') or item.get('idProcesso') or item.get('id'))
        numero = (processo_obj.get('numero') or processo_obj.get('numeroProcesso') or item.get('numeroProcesso') or item.get('numero'))

        if not id_processo:
            print(f"[MANDADOS] Aviso: idProcesso não encontrado para item {idx}, pulando")
            continue

        print(f"  {idx:02d} - idProcesso={id_processo} numeroProcesso={numero}")
        sucesso = processar_mandado_detalhe(driver, numero, id_processo=id_processo)
        if not sucesso:
            print(f"[MANDADOS] Falha ao processar {numero}")
            sucesso_total = False

    return sucesso_total


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
        
        # 1. ESCOLHER DRIVER (PJE) - DEFAULT PARA VT
        print("\n[1/3] Escolha o tipo de driver PJE: (default V)")
        print("  [V] VT (padrão)")
        # print("  [P] PC (opcional)")

        # allow non-interactive choice via env var or CLI arg for automated runs
        escolha = None
        if len(sys.argv) > 1:
            escolha = sys.argv[1].strip().upper()
        if not escolha:
            escolha = os.environ.get('F_CHOICE', '').strip().upper()
        # se nada fornecido, usar VT por padrão (V)
        if not escolha:
            escolha = 'V'
        
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
            print("[LOGIN] Primeira tentativa falhou (cookies ou sessão expirada). Limpando cookies e resetando navegação...")
            try:
                driver_pje.delete_all_cookies()
            except Exception:
                pass
            try:
                driver_pje.get("https://pje.trt2.jus.br/primeirograu/")
                time.sleep(1.5)
            except Exception:
                pass
            print("[LOGIN] Tentando login manual novamente...")
            sucesso_login = login_cpf(driver_pje)
            if not sucesso_login:
                print("❌ Falha no login (mesmo após retry)")
                return False
        print("✅ Login PJE concluído")

        # === TESTE PRAZO CICLO2 (P2) ===
        try:
            print("[PRAZO_CICLO2] Iniciando ciclo2 isolado em Prazo")
            sucesso_prazo_c2 = processar_prazo_ciclo2(driver_pje)
            print(f"[PRAZO_CICLO2] Resultado do fluxo: {'sucesso' if sucesso_prazo_c2 else 'falha'}")

            # Caso queira manter o fluxo de GIGS sem prazo XS via API (alternativa):
            # print("[P2B] Iniciando fluxo de teste GIGS sem prazo XS via API")
            # sucesso_p2b = processar_gigs_sem_prazo_p2b(driver_pje)
            # print(f"[P2B] Resultado do fluxo: {'sucesso' if sucesso_p2b else 'falha'}")

        except Exception as e:
            print(f"[TESTE] Erro ao testar API mandados devolvidos ou processar fluxo: {e}")
        print("\n" + "=" * 80)
        print("TESTE CONCLUÍDO - Pressione Enter para fechar o browser...")
        input()
        return True
        
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
