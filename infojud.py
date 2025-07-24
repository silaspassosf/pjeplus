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
    """Gera link de consulta Infojud (CPF/CNPJ) e imprime/loga. Se ni não for informado, extrai o primeiro documento de parte passiva (reclamada). Se driver for passado, pode abrir a consulta em nova janela e automatizar login GovBR/certificado.
    Se usar_perfil_real=True, abre nova janela Firefox com perfil real, user-agent real e oculta navigator.webdriver."""
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
            # Usa perfil específico do Infojud com gerenciamento de cookies
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
            
            # Carrega cookies salvos primeiro
            cookies_carregados = carregar_cookies_infojud(driver_infojud)
            
            # Navega para o link
            driver_infojud.get(link)
            time.sleep(random.uniform(2, 4))
            driver_infojud.execute_script("window.scrollBy(0, 200);")
            time.sleep(random.uniform(1, 2))
            
            # Verifica se precisa fazer login
            if "autenticacao/login" in driver_infojud.current_url.lower():
                if log:
                    print('[INFOJUD] Tela de login detectada - LOGIN MANUAL necessário.')
                    print('[INFOJUD] Após fazer login, os cookies serão salvos automaticamente.')
                
                # Aguarda sair da tela de login para salvar cookies
                for _ in range(300):  # 5 minutos de timeout
                    time.sleep(1)
                    if "autenticacao/login" not in driver_infojud.current_url.lower():
                        if log:
                            print('[INFOJUD] Login detectado! Salvando cookies...')
                        salvar_cookies_infojud(driver_infojud)
                        break
            else:
                if log:
                    print('[INFOJUD] Sessão mantida com cookies - login não necessário!')
            
            if log:
                print('[INFOJUD] Consulta Infojud aberta em nova janela com perfil específico.')
                if not cookies_carregados:
                    print('[INFOJUD] LOGIN MANUAL: Faça o login manualmente se necessário.')
            return link
        
        # Se driver for passado (PJE), abre em nova aba com validação de contexto
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
                
            except Exception as switch_error:
                if log:
                    print(f'[INFOJUD][ERRO] Erro ao trocar para nova aba: {switch_error}')
                return link
            
        except Exception as tab_error:
            if log:
                print(f'[INFOJUD][ERRO] Erro no gerenciamento de abas: {tab_error}')
            return link
        
        if log:
            print(f"[INFOJUD] Consulta Infojud aberta em nova aba do PJE.")
            print(f"[INFOJUD] URL: {driver.current_url}")
            print("[INFOJUD] LOGIN MANUAL: Faça o login manualmente se necessário.")
    
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
