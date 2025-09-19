from Fix import extrair_dados_processo
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from driver_config import criar_driver, login_func
import time
import json
import os

# Configuração específica do Infojud
INFOJUD_PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\u6fs26dn.Info"
INFOJUD_COOKIES_FILE = r"d:\PjePlus\cookies_infojud.json"

def Infojud(ni=None, driver=None, log=True, abrir_navegador=True, usar_perfil_real=True):
    """Gera link de consulta Infojud (CPF/CNPJ) e imprime/loga. LOGIN SEMPRE MANUAL - aguarda confirmação do usuário.
    Se ni não for informado, extrai o primeiro documento de parte passiva (reclamada).
    Se driver for passado, abre a consulta em nova aba.
    Se usar_perfil_real=True, abre nova janela Firefox com perfil real."""

    if log:
        print("=" * 60)
        print("[INFOJUD] 🔐 LOGIN MANUAL OBRIGATÓRIO")
        print("[INFOJUD] ⚠️  O sistema irá aguardar sua confirmação antes de prosseguir")
        print("=" * 60)

    if ni is None and driver is not None:
        dados = extrair_dados_processo(driver, log=log)
        ni = None
        # Busca o primeiro documento de parte passiva (reclamada)
        if 'partes' in dados and 'passivas' in dados['partes']:
            for parte in dados['partes']['passivas']:
                doc = parte.get('documento', '').strip()
                doc_num = ''.join(filter(str.isdigit, doc))
                if doc_num and (len(doc_num) == 11 or len(doc_num) == 14):
                    ni = doc_num
                    break
        if log:
            print(f"[INFOJUD] NI extraído do processo: {ni if ni else 'Não encontrado'}")

    ni = str(ni).strip() if ni else ''
    link = None
    if len(ni) == 11:
        link = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI={ni}"
    elif len(ni) == 14:
        link = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI={ni}"

    if log:
        print(f"[INFOJUD] Link para consulta: {link if link else 'NI inválido'}")

    if link and abrir_navegador:
        if usar_perfil_real:
            # LOGIN MANUAL OBRIGATÓRIO - sempre abre nova janela
            if log:
                print("[INFOJUD] 🚀 Abrindo Infojud em nova janela Firefox...")
                print("[INFOJUD] 📋 INSTRUÇÕES:")
                print("[INFOJUD]   1. Faça o login manualmente no site da Receita")
                print("[INFOJUD]   2. Confirme quando estiver logado")
                print("[INFOJUD]   3. O sistema irá aguardar sua confirmação")

            # Usa perfil específico do Infojud
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options

            firefox_path = r"C:\\Program Files\\Mozilla Firefox\\firefox.exe"
            options = Options()
            options.binary_location = firefox_path
            options.profile = INFOJUD_PROFILE_PATH
            options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0")

            driver_infojud = webdriver.Firefox(options=options)
            driver_infojud.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            import random
            time.sleep(random.uniform(1.5, 3.5))

            # Navega para o link
            driver_infojud.get(link)
            time.sleep(random.uniform(2, 4))
            driver_infojud.execute_script("window.scrollBy(0, 200);")
            time.sleep(random.uniform(1, 2))

            # LOGIN MANUAL - sempre aguarda confirmação
            if log:
                print("=" * 60)
                print("[INFOJUD] ⏳ AGUARDANDO LOGIN MANUAL")
                print("[INFOJUD] 📝 Faça o login no navegador que foi aberto")
                print("[INFOJUD] ✅ Quando estiver logado, pressione ENTER no terminal")
                print("=" * 60)

            # Aguarda confirmação do usuário
            try:
                input("[INFOJUD] Pressione ENTER quando estiver logado... ")
                if log:
                    print("[INFOJUD] ✅ Confirmação recebida - prosseguindo...")
            except KeyboardInterrupt:
                if log:
                    print("[INFOJUD] ❌ Operação cancelada pelo usuário")
                driver_infojud.quit()
                return link

            # Salva cookies após login manual
            try:
                salvar_cookies_infojud(driver_infojud)
                if log:
                    print("[INFOJUD] 💾 Cookies salvos para próximas sessões")
            except Exception as e:
                if log:
                    print(f"[INFOJUD] ⚠️  Erro ao salvar cookies: {e}")

            if log:
                print("[INFOJUD] ✅ Consulta Infojud pronta com login manual realizado")

            return link
        
        # Se driver for passado (PJE), abre em nova aba com LOGIN MANUAL
        if log:
            print("[INFOJUD] 🔄 Abrindo Infojud em nova aba do PJE...")
            print("[INFOJUD] 📋 INSTRUÇÕES PARA NOVA ABA:")
            print("[INFOJUD]   1. Uma nova aba será aberta")
            print("[INFOJUD]   2. Faça o login manualmente se necessário")
            print("[INFOJUD]   3. Confirme quando estiver pronto")

        try:
            # Valida contexto antes de abrir nova aba
            current_handles = driver.window_handles
            current_handle = driver.current_window_handle
            if not current_handles or current_handle not in current_handles:
                if log:
                    print('[INFOJUD][ERRO] Contexto do browser inválido - não abrindo nova aba')
                return link

            # Abre nova aba
            driver.execute_script(
                f"window.open('{link}', '_blank', 'noopener,noreferrer,width=1024,height=768,left=100,top=100');")
            time.sleep(2 + 1.5 * (0.5 + __import__('random').random()))

            # Valida que nova aba foi criada
            new_handles = driver.window_handles
            if len(new_handles) <= len(current_handles):
                if log:
                    print('[INFOJUD][ERRO] Nova aba não foi criada - contexto pode estar perdido')
                return link

            # Troca para nova aba com validação
            try:
                driver.switch_to.window(new_handles[-1])
                # Valida que conseguiu trocar
                if driver.current_window_handle != new_handles[-1]:
                    if log:
                        print('[INFOJUD][ERRO] Falha ao trocar para nova aba - contexto perdido')
                    return link

                time.sleep(1.5 + 1.5 * __import__('random').random())

                # LOGIN MANUAL - sempre aguarda confirmação
                if log:
                    print("=" * 60)
                    print("[INFOJUD] ⏳ AGUARDANDO LOGIN MANUAL NA NOVA ABA")
                    print("[INFOJUD] 📝 Faça o login na nova aba que foi aberta")
                    print("[INFOJUD] ✅ Quando estiver logado, pressione ENTER no terminal")
                    print("=" * 60)

                # Aguarda confirmação do usuário
                try:
                    input("[INFOJUD] Pressione ENTER quando estiver logado na nova aba... ")
                    if log:
                        print("[INFOJUD] ✅ Confirmação recebida - prosseguindo...")
                except KeyboardInterrupt:
                    if log:
                        print("[INFOJUD] ❌ Operação cancelada pelo usuário")
                    # Volta para aba original
                    try:
                        driver.switch_to.window(current_handle)
                    except:
                        pass
                    return link

            except Exception as switch_error:
                if log:
                    print(f'[INFOJUD][ERRO] Erro ao trocar para nova aba: {switch_error}')
                return link

        except Exception as tab_error:
            if log:
                print(f'[INFOJUD][ERRO] Erro no gerenciamento de abas: {tab_error}')
            return link

        if log:
            print(f"[INFOJUD] ✅ Consulta Infojud aberta em nova aba do PJE com login manual")
            print(f"[INFOJUD] 🌐 URL: {driver.current_url}")
    
    return link

def salvar_cookies_infojud(driver):
    """Salva cookies do Infojud para reutilização em próximas sessões."""
    try:
        cookies = driver.get_cookies()
        with open(INFOJUD_COOKIES_FILE, 'w') as f:
            json.dump(cookies, f)
        print(f"[INFOJUD] Cookies salvos: {len(cookies)} cookies")
        return True
    except Exception as e:
        print(f"[INFOJUD][ERRO] Falha ao salvar cookies: {e}")
        return False

def carregar_cookies_infojud(driver):
    """Carrega cookies salvos do Infojud para manter sessão."""
    try:
        if not os.path.exists(INFOJUD_COOKIES_FILE):
            print("[INFOJUD] Nenhum cookie salvo encontrado")
            return False
        
        with open(INFOJUD_COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        
        # Primeiro navega para o domínio para poder adicionar cookies
        driver.get("https://cav.receita.fazenda.gov.br")
        time.sleep(1)
        
        cookies_carregados = 0
        for cookie in cookies:
            try:
                # Remove campos que podem causar erro
                cookie.pop('sameSite', None)
                cookie.pop('expiry', None)
                driver.add_cookie(cookie)
                cookies_carregados += 1
            except Exception as e:
                print(f"[INFOJUD][WARN] Erro ao carregar cookie: {e}")
                continue
        
        print(f"[INFOJUD] Cookies carregados: {cookies_carregados}/{len(cookies)}")
        return cookies_carregados > 0
    except Exception as e:
        print(f"[INFOJUD][ERRO] Falha ao carregar cookies: {e}")
        return False
