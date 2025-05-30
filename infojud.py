from Fix import extrair_dados_processo
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

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
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options
            profile_path = r"C:\\Users\\Silas\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\x4fkuw2q.silas-1723037723659"
            firefox_path = r"C:\\Program Files\\Mozilla Firefox\\firefox.exe"
            options = Options()
            options.binary_location = firefox_path
            options.profile = profile_path
            options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0")
            driver_real = webdriver.Firefox(options=options)
            driver_real.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            import random
            import time
            time.sleep(random.uniform(1.5, 3.5))
            driver_real.get(link)
            time.sleep(random.uniform(2, 4))
            driver_real.execute_script("window.scrollBy(0, 200);")
            time.sleep(random.uniform(1, 2))
            if log:
                print('[INFOJUD] Consulta Infojud aberta em nova janela com perfil real.')
            return link
        # Abre em nova janela (não apenas nova aba)
        # window.open com features abre nova janela real (não só aba)
        driver.execute_script(
            f"window.open('{link}', '_blank', 'noopener,noreferrer,width=1024,height=768,left=100,top=100');")
        time.sleep(2 + 1.5 * (0.5 + __import__('random').random()))
        janelas = driver.window_handles
        driver.switch_to.window(janelas[-1])
        time.sleep(1.5 + 1.5 * __import__('random').random())
        atual = driver.current_url
        if log:
            print(f"[INFOJUD] URL atual na nova janela: {atual}")
        # Se for tela de login GovBR, faz os cliques automáticos humanizados
        if 'autenticacao/login' in atual:
            import random
            import sys
            try:
                # 1. Clique humanizado no botão GovBR (imagem)
                btn_govbr = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='image'][alt*='Acesso Gov BR']"))
                )
                # Simula movimento de mouse, foco e scroll antes do clique
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(driver)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_govbr)
                    time.sleep(random.uniform(0.3, 0.7))
                    actions.move_to_element(btn_govbr).pause(random.uniform(0.2, 0.7)).perform()
                    time.sleep(random.uniform(0.1, 0.3))
                    btn_govbr.location_once_scrolled_into_view
                    btn_govbr.click()
                except Exception:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn_govbr)
                    time.sleep(random.uniform(0.2, 0.7))
                    btn_govbr.click()
                if log:
                    print('[INFOJUD] Clique humanizado no botão GovBR realizado.')
                time.sleep(1.2 + random.uniform(0.5, 1.5))
                # 2. Espera e clica no botão certificado digital (humanizado)
                btn_cert = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#login-certificate"))
                )
                try:
                    actions = ActionChains(driver)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_cert)
                    time.sleep(random.uniform(0.3, 0.7))
                    actions.move_to_element(btn_cert).pause(random.uniform(0.2, 0.7)).perform()
                    time.sleep(random.uniform(0.1, 0.3))
                    btn_cert.location_once_scrolled_into_view
                    btn_cert.click()
                except Exception:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn_cert)
                    time.sleep(random.uniform(0.2, 0.7))
                    btn_cert.click()
                if log:
                    print('[INFOJUD] Clique humanizado no botão Certificado Digital realizado.')
                # 3. Executa Login.ahk para digitar o PIN do certificado digital (igual login_pc)
                import subprocess
                time.sleep(1 + random.uniform(0.2, 0.7))
                try:
                    subprocess.Popen([r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe", r"D:\\PjePlus\\Login.ahk"])
                    if log:
                        print('[INFOJUD] Script Login.ahk executado para PIN do certificado digital.')
                except Exception as e:
                    if log:
                        print(f'[INFOJUD][ERRO] Falha ao executar Login.ahk: {e}')
                # Aguarda sair da tela de login GovBR/certificado
                for _ in range(60):
                    # Pequeno scroll e foco para simular atividade humana
                    driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(-30, 30))
                    time.sleep(0.1 + random.uniform(0, 0.2))
                    if 'autenticacao/login' not in driver.current_url.lower():
                        if log:
                            print('[INFOJUD] Login detectado, prosseguindo.')
                        break
                    time.sleep(1 + random.uniform(0, 0.5))
                else:
                    if log:
                        print('[INFOJUD][ERRO] Timeout aguardando login Infojud.')
                # Se após login cair na página /ecac/, fecha a aba e reabre o link original
                if driver.current_url.startswith('https://cav.receita.fazenda.gov.br/ecac/'):
                    if log:
                        print('[INFOJUD] Página /ecac/ detectada após login. Fechando aba e reabrindo link Infojud...')
                    driver.close()
                    driver.switch_to.window(janelas[0])
                    # Reabre a consulta Infojud em nova janela
                    driver.execute_script(
                        f"window.open('{link}', '_blank', 'noopener,noreferrer,width=1024,height=768,left=100,top=100');")
                    time.sleep(2 + 1.5 * random.random())
                    janelas = driver.window_handles
                    driver.switch_to.window(janelas[-1])
            except Exception as e:
                if log:
                    print(f'[INFOJUD][ERRO] Falha ao automatizar login GovBR/certificado: {e}')
    return link
