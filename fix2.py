# ====================================================================
# PJE PLUS - Fix.py
# Módulo principal de utilitários e funções para automação do PJe
# ====================================================================

# =========================
# 1. IMPORTAÇÕES E CONFIGURAÇÕES
# =========================
import os
import json
import time
import re
import logging
import tempfile
import shutil
import requests
import undetected_chromedriver as uc
import pyperclip
from urllib.parse import urlparse
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
    WebDriverException, NoSuchWindowException, ElementNotInteractableException,
    StaleElementReferenceException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

# Configuração de logs (apenas erros)
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes de configuração
PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
GECKODRIVER_PATH = r"d:\PjePlus\geckodriver.exe"

# =========================
# 2. FUNÇÕES DE SETUP E INICIALIZAÇÃO
# =========================

def limpar_temp_selenium():
    """Limpa arquivos temporários do Selenium com segurança."""
    try:
        temp_dirs = [
            os.path.join(os.environ['TEMP'], 'selenium*'),
            os.path.join(os.environ['USERPROFILE'], 'AppData\Local\Temp', 'selenium*')
        ]
        
        deleted = 0
        for pattern in temp_dirs:
            for filepath in glob.glob(pattern):
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if datetime.now() - file_time > timedelta(days=1):
                        os.remove(filepath)
                        deleted += 1
                except Exception:
                    pass
        
        return deleted > 0
    except Exception as e:
        logger.error(f"Falha na limpeza: {e}")
        return False

def obter_driver_padronizado(headless=False):
    """Retorna driver Firefox padronizado para ambiente TRT2."""
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service(executable_path=GECKODRIVER_PATH)
    
    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.error(f"Erro ao iniciar driver: {e}")
        raise

def driver_pc(headless=False):
    """Driver para ambiente PC."""
    return obter_driver_padronizado(headless)

def driver_notebook(headless=False):
    """Driver para ambiente notebook."""
    return obter_driver_padronizado(headless)

def login_pc(driver):
    """Login automático via AutoHotkey."""
    try:
        driver.get("https://pje.trt2.jus.br/primeirograu/login.seam")
        
        btn_sso = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#btnSsoPdpj"))
        )
        btn_sso.click()
        
        btn_certificado = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".botao-certificado-titulo"))
        )
        btn_certificado.click()
        
        time.sleep(1)
        subprocess.Popen([r"C:\Program Files\AutoHotkey\AutoHotkey.exe", r"D:\PjePlus\Login.ahk"])
        
        for _ in range(60):
            if "login" not in driver.current_url.lower():
                return True
            time.sleep(1)
        
        return False
    except Exception as e:
        logger.error(f"Falha no login: {e}")
        return False

def login_notebook(driver):
    """Login humanizado para notebooks."""
    try:
        driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
        time.sleep(2)
        
        # Tenta carregar cookies primeiro
        if carregar_cookies(driver, 'cookies_pjeplus_notebook.json'):
            if 'login' not in driver.current_url.lower():
                return True
        
        # Login manual se cookies falharem
        usuario = '35305203813'
        senha = 'SpF59866'
        
        btn_sso = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, 'btnSsoPdpj'))
        )
        btn_sso.click()
        time.sleep(1)
        
        campo_usuario = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'username'))
        )
        campo_usuario.click()
        campo_usuario.clear()
        
        for c in usuario:
            campo_usuario.send_keys(c)
            time.sleep(0.2)
        
        campo_usuario.send_keys(Keys.TAB)
        time.sleep(0.4)
        
        campo_senha = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'password'))
        )
        campo_senha.click()
        campo_senha.clear()
        
        for c in senha:
            campo_senha.send_keys(c)
            time.sleep(0.2)
        
        campo_senha.send_keys(Keys.TAB)
        campo_senha.send_keys(Keys.ENTER)
        time.sleep(3)
        
        return 'login' not in driver.current_url.lower()
    except Exception as e:
        logger.error(f"Falha no login: {e}")
        return False

def checar_acesso_negado(driver):
    """Verifica se a página atual é de acesso negado."""
    return "negado" in driver.current_url.lower()

def salvar_cookies(driver, caminho_arquivo):
    """Salva cookies em arquivo JSON."""
    try:
        cookies = driver.get_cookies()
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Falha ao salvar cookies: {e}")
        return False

def carregar_cookies(driver, caminho_arquivo, url_base='https://pje.trt2.jus.br'):
    """Carrega cookies de arquivo JSON."""
    if not os.path.exists(caminho_arquivo):
        return False
    
    try:
        driver.get(url_base)
        
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        for cookie in cookies:
            cookie.pop('sameSite', None)
            cookie.pop('expiry', None)
            driver.add_cookie(cookie)
        
        driver.refresh()
        return True
    except Exception as e:
        logger.error(f"Falha ao carregar cookies: {e}")
        return False

# =========================
# 3. FUNÇÕES DE NAVEGAÇÃO
# =========================

def navegar_para_tela(driver, url=None, seletor=None, delay=2, timeout=30):
    """Navega para URL ou clica em seletor."""
    try:
        if url:
            driver.get(url)
        
        if seletor:
            element = driver.find_element(By.CSS_SELECTOR, seletor)
            driver.execute_script('arguments[0].scrollIntoView(true);', element)
            element.click()
            time.sleep(delay)
        
        return True
    except Exception as e:
        logger.error(f"Falha na navegação: {e}")
        return False

def aplicar_filtro_100(driver):
    """Aplica filtro para exibir 100 itens por página."""
    try:
        driver.execute_script("document.body.style.zoom='50%'")
        
        for tentativa in range(2):
            try:
                span_20 = driver.find_element(By.XPATH, "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']")
                mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mat_select)
                time.sleep(0.3)
                
                mat_select.click()
                time.sleep(0.5)
                
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                opcao_100 = overlay.find_element(By.XPATH, ".//mat-option[.//span[normalize-space(text())='100']]")
                opcao_100.click()
                time.sleep(1)
                
                return True
            except Exception:
                if tentativa < 1:
                    time.sleep(1)
        
        return False
    except Exception as e:
        logger.error(f"Falha ao aplicar filtro: {e}")
        return False

def filtro_fase(driver, fases=['Execução', 'Liquidação']):
    """Seleciona fases processuais no filtro."""
    try:
        seletor_dropdown = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'
        dropdowns = driver.find_elements(By.CSS_SELECTOR, seletor_dropdown)
        dropdown = next((d for d in dropdowns if d.is_displayed()), None)
        
        if not dropdown:
            return False
        
        driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
        dropdown.click()
        time.sleep(0.5)
        
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        
        for fase in fases:
            opcoes = overlay.find_elements(By.XPATH, f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{fase}']")
            for opcao in opcoes:
                if opcao.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                    opcao.click()
                    time.sleep(0.2)
        
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        return True
    except Exception as e:
        logger.error(f"Falha no filtro de fase: {e}")
        return False

def esperar_url_conter(driver, trecho_url, timeout=60):
    """Espera URL conter trecho específico."""
    start = time.time()
    while time.time() - start < timeout:
        if trecho_url in driver.current_url:
            return True
        time.sleep(0.5)
    return False

# =========================
# 4. FUNÇÕES DE INTERAÇÃO COM ELEMENTOS
# =========================

def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """Espera elemento ficar visível."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        logger.error(f"Elemento não encontrado: {selector}")
        return None

def safe_click(driver, selector_or_element, timeout=10, by=None):
    """Clique seguro em elemento."""
    try:
        if isinstance(selector_or_element, str):
            element = wait(driver, selector_or_element, timeout, by)
        else:
            element = selector_or_element
        
        if element and element.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            driver.execute_script("arguments[0].click();", element)
            return True
        return False
    except Exception as e:
        logger.error(f"Falha ao clicar: {e}")
        return False

def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR):
    """Espera elemento estar presente e opcionalmente conter texto."""
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        
        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )
        
        return el
    except Exception as e:
        logger.error(f"Falha ao esperar elemento: {e}")
        return None

def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5):
    """Busca robusta por múltiplas estratégias."""
    def buscar_input_associado(elemento):
        try:
            return elemento.find_element(By.XPATH, 
                './following-sibling::input|./preceding-sibling::input|'
                './ancestor::*[contains(@class,"form-group")]//input|'
                './ancestor::*[contains(@class,"mat-form-field")]//input'
            )
        except:
            return None
    
    try:
        # Estratégia 1: Inputs diretos
        for texto in textos:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, 
                    f'input[placeholder*="{texto}"], '
                    f'input[aria-label*="{texto}"], '
                    f'input[name*="{texto}"]'
                )
                for el in elementos:
                    if el.is_displayed() and el.is_enabled():
                        return el
            except:
                continue
        
        # Estratégia 2: Busca hierárquica
        for texto in textos:
            try:
                elementos = driver.find_elements(By.XPATH, f'//*[contains(text(), "{texto}")]')
                for el in elementos:
                    input_assoc = buscar_input_associado(el)
                    if input_assoc:
                        return input_assoc
            except:
                continue
        
        # Estratégia 3: Ícones
        for texto in textos:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, 
                    f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all'
                )
                for el in elementos:
                    if el.is_displayed():
                        return el
            except:
                continue
        
        return None
    except Exception as e:
        logger.error(f"Erro na busca robusta: {e}")
        return None

# =========================
# 5. FUNÇÕES DE EXTRAÇÃO DE DADOS
# =========================

def extrair_documento(driver, regras_analise=None, timeout=15):
    """Extrai texto do documento aberto."""
    try:
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            return None
        
        safe_click(driver, btn_html)
        time.sleep(1)
        
        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return None
        
        texto_completo = preview.text
        
        # Fecha modal
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.5)
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
        
        # Aplica regras se existirem
        if regras_analise and callable(regras_analise):
            try:
                regras_analise(texto_completo)
            except:
                pass
        
        return texto_completo
    except Exception as e:
        logger.error(f"Falha ao extrair documento: {e}")
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except:
            pass
        return None

def extrair_pdf(driver):
    """Extrai texto de PDF via exportação."""
    try:
        btn_export = driver.find_element(By.CSS_SELECTOR, '.fa-file-export')
        btn_export.click()
        
        for _ in range(20):
            modais = driver.find_elements(By.CSS_SELECTOR, 'pje-conteudo-documento-dialog')
            for modal in modais:
                try:
                    titulo = modal.find_element(By.CSS_SELECTOR, '.mat-dialog-title')
                    if 'Texto Extraído' in titulo.text:
                        try:
                            btn_copiar = modal.find_element(By.CSS_SELECTOR, 'i.far.fa-copy')
                            btn_copiar.click()
                            time.sleep(0.3)
                            return pyperclip.paste()
                        except:
                            pre = modal.find_element(By.CSS_SELECTOR, 'pre')
                            return pre.text
                except:
                    continue
            time.sleep(0.5)
        
        return None
    except Exception as e:
        logger.error(f"Falha ao extrair PDF: {e}")
        return None

def extrair_dados_processo(driver, caminho_json='dadosatuais.json'):
    """Extrai dados do processo via API do PJe."""
    def get_cookies_dict(driver):
        return {c['name']: c['value'] for c in driver.get_cookies()}
    
    def extrair_numero_processo_url(driver):
        url = driver.current_url
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)
        
        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
            elemento_clipboard = driver.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except:
            pass
        
        return None
    
    def extrair_trt_host(driver):
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc
    
    def obter_id_processo_via_api(numero_processo, sess, trt_host):
        url = f'https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('idProcesso')
        except:
            pass
        return None
    
    def obter_dados_processo_via_api(id_processo, sess, trt_host):
        url = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                return resp.json()
        except:
            pass
        return None
    
    def criar_pessoa_limpa(parte):
        nome = parte.get("nome", "").strip()
        doc = re.sub(r'[^\d]', '', parte.get("documento", ""))
        
        pessoa = {"nome": nome, "cpfcnpj": doc}
        
        reps = parte.get("representantes", [])
        if reps:
            adv = reps[0]
            pessoa["advogado"] = {
                "nome": adv.get("nome", "").strip(),
                "cpf": re.sub(r'[^\d]', '', adv.get("documento", "")),
                "oab": adv.get("numeroOab", "")
            }
        return pessoa
    
    try:
        cookies = get_cookies_dict(driver)
        numero_processo = extrair_numero_processo_url(driver)
        trt_host = extrair_trt_host(driver)
        
        sess = requests.Session()
        for k, v in cookies.items():
            sess.cookies.set(k, v)
        sess.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "X-Grau-Instancia": "1"
        })
        
        if not numero_processo:
            return {}
        
        id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
        if not id_processo:
            return {}
        
        dados_processo = obter_dados_processo_via_api(id_processo, sess, trt_host)
        if not dados_processo:
            return {}
        
        processo_memoria = {
            "numero": [dados_processo.get("numero", numero_processo)], 
            "id": id_processo, 
            "autor": [], 
            "reu": [], 
            "terceiro": [],
            "divida": {}, 
            "justicaGratuita": [], 
            "transito": "", 
            "custas": "", 
            "dtAutuacao": "",
            "classeJudicial": dados_processo.get("classeJudicial", {}),
            "labelFaseProcessual": dados_processo.get("labelFaseProcessual", ""),
            "orgaoJuizo": dados_processo.get("orgaoJuizo", {}),
            "dataUltimo": dados_processo.get("dataUltimo", "")
        }
        
        dt = dados_processo.get("autuadoEm")
        if dt:
            try:
                dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
            except:
                processo_memoria["dtAutuacao"] = dt
        
        try:
            url_partes = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes"
            resp = sess.get(url_partes, timeout=10)
            if resp.ok:
                j = resp.json()
                for parte in j.get("ATIVO", []):
                    processo_memoria["autor"].append(criar_pessoa_limpa(parte))
                for parte in j.get("PASSIVO", []):
                    processo_memoria["reu"].append(criar_pessoa_limpa(parte))
                for parte in j.get("TERCEIROS", []):
                    processo_memoria["terceiro"].append({"nome": parte.get("nome", "").strip()})
        except:
            pass
        
        try:
            url_divida = f"https://{trt_host}/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=true&idProcesso={id_processo}&mostrarCalculosHomologados=true&incluirCalculosHomologados=true"
            resp = sess.get(url_divida, timeout=10)
            if resp.ok:
                j = resp.json()
                if j and j.get("resultado"):
                    ultimo = j["resultado"][-1]
                    processo_memoria["divida"] = {
                        "valor": ultimo.get("total", 0),
                        "data": ultimo.get("dataLiquidacao", "")
                    }
        except:
            pass
        
        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(processo_memoria, f, ensure_ascii=False, indent=2)
        
        return processo_memoria
    except Exception as e:
        logger.error(f"Falha ao extrair dados: {e}")
        return {}

# =========================
# 6. FUNÇÕES DE MANIPULAÇÃO DE PRAZOS E GIGS
# =========================

def preencher_campos_prazo(driver, valor=0, timeout=10):
    """Preenche campos de prazo no formulário."""
    try:
        form = wait(driver, '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form', timeout)
        if not form:
            return False
        
        inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="text"].mat-input-element')
        if not inputs:
            return False
        
        for campo in inputs:
            driver.execute_script("arguments[0].focus();", campo)
            campo.clear()
            campo.send_keys(str(valor))
            driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
            driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
        
        return True
    except Exception as e:
        logger.error(f"Falha ao preencher prazos: {e}")
        return False

def criar_gigs(driver, dias_uteis, responsavel, observacao, timeout=10):
    """Cria GIGS com padrão dias/responsavel/observacao."""
    try:
        # Garante padrão correto
        if not responsavel or responsavel.strip() == '-':
            responsavel = ''
        
        # Navega para tela de atividades
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        driver.get(url_atividades)
        
        # Clica em novo
        btn_novo = wait(driver, 'button[aria-label="Novo"]', timeout)
        if not btn_novo:
            return False
        
        safe_click(driver, btn_novo)
        time.sleep(1)
        
        # Preenche formulário
        campo_dias = wait(driver, 'input[formcontrolname="diasUteis"]', timeout)
        if campo_dias:
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))
        
        if responsavel:
            campo_responsavel = wait(driver, 'input[formcontrolname="responsavel"]', timeout)
            if campo_responsavel:
                campo_responsavel.clear()
                campo_responsavel.send_keys(responsavel)
        
        campo_observacao = wait(driver, 'textarea[formcontrolname="observacao"]', timeout)
        if campo_observacao:
            campo_observacao.clear()
            campo_observacao.send_keys(observacao)
        
        # Salva
        btn_salvar = wait(driver, 'button[aria-label="Salvar"]', timeout)
        if btn_salvar:
            safe_click(driver, btn_salvar)
            time.sleep(1)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Falha ao criar GIGS: {e}")
        return False

# =========================
# 7. FUNÇÕES DE LISTA E PROCESSAMENTO
# =========================

def indexar_e_processar_lista(driver, callback_processo):
    """Processa itens de uma lista com callback."""
    try:
        # Aguarda lista carregar
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
        )
        
        # Obtém todos os itens
        itens = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        
        for i, item in enumerate(itens):
            try:
                # Abre item em nova aba
                link = item.find_element(By.CSS_SELECTOR, 'a[href*="processo"]')
                url = link.get_attribute('href')
                
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                driver.get(url)
                
                # Processa com callback
                callback_processo(driver)
                
                # Fecha aba e volta para lista
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro ao processar item {i}: {e}")
                continue
        
        return True
    except Exception as e:
        logger.error(f"Falha no processamento da lista: {e}")
        return False

def finalizar_driver(driver):
    """Finaliza driver com segurança."""
    try:
        if driver:
            driver.quit()
    except Exception as e:
        logger.error(f"Erro ao finalizar driver: {e}")