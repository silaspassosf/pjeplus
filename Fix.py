# Fix.py
# Utilitário Selenium inspirado na lógica da extensão MaisPje para preenchimento robusto de campos em formulários do PJe TRT2
# Autor: Cascade AI

import os
import shutil
import tempfile
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# =========================
# 1. UTILITÁRIOS E LIMPEZA
# =========================
# Funções utilitárias gerais, limpeza de temp, helpers genéricos

# Função para limpar arquivos temporários
def limpar_temp_selenium():
    """
    Limpa os arquivos temporários do Selenium de forma segura
    Remove apenas arquivos .part e temp files antigos
    """
    import os, time, glob
    from datetime import datetime, timedelta
    
    try:
        # Define pastas temporárias comuns
        temp_dirs = [
            os.path.join(os.environ['TEMP'], 'selenium*'),
            os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp', 'selenium*')
        ]
        
        # Limpeza segura
        deleted = 0
        for pattern in temp_dirs:
            for filepath in glob.glob(pattern):
                try:
                    # Verifica se o arquivo é antigo (>1 dia)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if datetime.now() - file_time > timedelta(days=1):
                        os.remove(filepath)
                        deleted += 1
                except Exception as e:
                    print(f'[AVISO] Não removeu {filepath}: {str(e)}')
        
        print(f'[SELENIUM] Limpeza concluída - {deleted} arquivos removidos')
        return True
    except Exception as e:
        print(f'[ERRO] Falha na limpeza: {str(e)}')
        return False

# Seção: Navegação
# Configurações do navegador
PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"

# Função para configurar e iniciar o navegador
def configurar_navegador():
    """
    Configura e retorna uma instância do Firefox com as configurações necessárias.
    """
    try:
        options = webdriver.FirefoxOptions()
        options.binary_location = FIREFOX_BINARY
        options.set_preference('profile', PROFILE_PATH)
        service = webdriver.FirefoxService()
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as e:
        print(f'[CONFIG][ERRO] Falha ao configurar navegador: {e}')
        raise

def obter_driver_padronizado(headless=False):
    """
    Retorna um driver Firefox padronizado para o ambiente TRT2, usando perfil e binário já conhecidos.
    """
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import os
    PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service()
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    return driver

# Função de login automático
def login_automatico(driver, usuario, senha):
    """
    Realiza login automático no PJe TRT2.
    """
    try:
        driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
        
        # Campo de usuário
        campo_usuario = wait(driver, 'input#username')
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
        time.sleep(1)
        
        # Campo de senha
        campo_senha = wait(driver, 'input#password')
        campo_senha.clear()
        campo_senha.send_keys(senha)
        time.sleep(1)
        
        # Botão de entrar
        btn_entrar = wait(driver, 'button#btnEntrar')
        btn_entrar.click()
        time.sleep(3)
        
        print('[LOGIN] Login realizado com sucesso.')
        return True
        
    except Exception as e:
        print(f'[LOGIN][ERRO] Falha no login: {e}')
        return False

       
# Função para navegar e esperar carregamento
def navegar_para_tela(driver, url=None, seletor=None, delay=2, timeout=30, log=True):
    """
    Navega para URL ou clica em seletor diretamente.
    
    Args:
        driver: WebDriver instance
        url: URL para navegar
        seletor: Seletor CSS/XPath para clicar
        delay: Delay após clique (segundos)
        timeout: Timeout máximo para espera (segundos)
        log: Se deve exibir logs
    
    Returns:
        bool: True se sucesso, False se falha
    """
    try:
        if log:
            print(f'[NAVEGAR] Iniciando navegação...')
            
        if url:
            driver.get(url)
            if log:
                print(f'[NAVEGAR] Navegando para {url}')
                
        if seletor:
            # Encontra e clica no elemento
            element = driver.find_element(By.CSS_SELECTOR, seletor)
            driver.execute_script('arguments[0].scrollIntoView(true);', element)
            element.click()
            
            # Espera após clique
            time.sleep(delay)
            if log:
                print(f'[NAVEGAR] Clicou em {seletor}')
                
        return True
        
    except Exception as e:
        if log:
            print(f'[NAVEGAR][ERRO] Falha na navegação: {str(e)}')
        return False
        return False

    def aplicar_filtro_100(driver):
        """Aplica o filtro para exibir 100 itens por página."""
        try:
            # Clica no dropdown de itens por página
            dropdown_itens_por_pagina = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//mat-select[@aria-label='Itens por página:']"))
            )
            dropdown_itens_por_pagina.click()
            print("[DEBUG] Clicou no dropdown de itens por página.")

            # Espera a opção '100' ficar visível e clica nela
            opcao_100 = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//mat-option/span[contains(text(), '100')]"))
            )
            opcao_100.click()
            print("[DEBUG] Selecionou a opção '100'.")
            time.sleep(2) # Pequena pausa para garantir que a interface atualize

        except TimeoutException:
            print("[ERRO] Timeout ao tentar aplicar o filtro de 100 itens por página.")
        except Exception as e:
            print(f"[ERRO] Erro inesperado ao aplicar filtro de : {e}")
# Função para processar lista de processos
def processar_lista_processos(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    """
    Percorre lista de processos, abre detalhes, executa callback, fecha aba, volta.
    Agora NÃO faz mais indexação/listagem duplicada: espera que a lista já tenha sido extraída.
    Só fecha a aba do processo se houver mais de uma aba aberta.
    """
    from selectors_pje import buscar_seletor_robusto
    import time
    import re
    try:
        processados = 0
        processos_ids_processados = set()
        # Indexação/listagem removida! Assume que a lista já foi extraída e está na tela.
        if modo == 'tabela':
            processos = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        else:
            processos = driver.find_elements(By.CSS_SELECTOR, 'div.pje-content')
        lista_processos = []
        for idx, processo in enumerate(processos):
            try:
                proc_id = None
                links = processo.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    proc_id = links[0].text.strip()
                if not proc_id:
                    tds = processo.find_elements(By.TAG_NAME, 'td')
                    proc_id = tds[0].text.strip() if tds else None
                if not proc_id or proc_id in processos_ids_processados:
                    continue
                lista_processos.append((proc_id, idx))
            except Exception:
                continue
        if not lista_processos:
            if log:
                print('[PROCESSAR][ERRO] Nenhum processo encontrado para processar.')
            return False
        print(f'[PROCESSAR] Lista de processos extraída ({len(lista_processos)}):')
        for proc_id, _ in lista_processos:
            print(proc_id)
        input('Pressione Enter para iniciar o processamento sequencial...')
        aba_lista = driver.current_window_handle
        for idx, (proc_id, linha_idx) in enumerate(lista_processos):
            try:
                if max_processos and processados >= max_processos:
                    return True
                # Sempre volta para a aba da lista antes de abrir o próximo
                if aba_lista not in driver.window_handles:
                    print('[PROCESSAR][ERRO] Aba da lista foi perdida. Abortando processamento.')
                    return False
                try:
                    driver.switch_to.window(aba_lista)
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Não foi possível trocar para aba da lista: {e}')
                    return False
                # Fecha abas extras se necessário (mantém só a da lista)
                while len(driver.window_handles) > 1:
                    for h in driver.window_handles:
                        if h != aba_lista:
                            try:
                                driver.switch_to.window(h)
                                driver.close()
                            except Exception as e:
                                print(f'[PROCESSAR][WARN] Erro ao fechar aba extra: {e}')
                # 1. Abrir o processo na lista
                linha = processos[linha_idx]
                try:
                    btn = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
                except Exception:
                    btn = None
                if btn is not None:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    driver.execute_script("arguments[0].click();", btn)
                else:
                    print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
                    continue
                time.sleep(1)
                # 2. Trocar para a nova aba
                time.sleep(1)
                abas = driver.window_handles
                nova_aba = None
                for h in abas:
                    if h != aba_lista:
                        nova_aba = h
                        break
                if not nova_aba:
                    print(f'[PROCESSAR][ERRO] Nova aba do processo {proc_id} não foi aberta.')
                    continue
                try:
                    driver.switch_to.window(nova_aba)
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Não foi possível trocar para nova aba do processo {proc_id}: {e}')
                    continue
                url_aba = driver.current_url
                if log:
                    print(f'[PROCESSAR] Aba do processo {proc_id} aberta em {url_aba}.')
                # 3. Executar callback (ou simular automação)
                try:
                    callback(driver)
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}')
                # 4. Fechar a aba do processo, mas só se houver mais de uma aba aberta
                if len(driver.window_handles) > 1:
                    try:
                        driver.close()
                    except Exception as e:
                        print(f'[PROCESSAR][WARN] Erro ao fechar aba do processo {proc_id}: {e}')
                    # Volta para a aba da lista, se existir
                    if aba_lista in driver.window_handles:
                        try:
                            driver.switch_to.window(aba_lista)
                        except Exception as e:
                            print(f'[PROCESSAR][ERRO] Não foi possível voltar para aba da lista após fechar aba do processo {proc_id}: {e}')
                            return False
                    else:
                        print(f'[PROCESSAR][ERRO] Aba da lista não está mais disponível após fechar aba do processo {proc_id}.')
                        return False
                else:
                    print(f'[PROCESSAR][ERRO] Só existe uma aba aberta, não será fechada.')
                if log:
                    print(f'[PROCESSAR] Aba do processo {proc_id} fechada - voltando à lista.')
                time.sleep(1)
                processos_ids_processados.add(proc_id)
                processados += 1
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha ao processar processo {proc_id}: {e}')
                continue
        print('[PROCESSAR] Fim do processamento da lista.')
        input('Pressione Enter para finalizar...')
        return True
    except Exception as e:
        if log:
            print(f'[PROCESSAR][ERRO] Falha geral: {e}')
        return False

# Seção: Interação com Elementos

# Função de espera robusta
def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """
    Espera até que um elemento esteja visível na página.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        print(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None

# Função de clique seguro
def safe_click(driver, selector_or_element, timeout=10, by=None, log=True):
    """
    Clicks safely. Accepts selector (string) or element.
    """
    try:
        from selenium.webdriver.common.by import By
        if isinstance(selector_or_element, str):
            element = wait(driver, selector_or_element, timeout, by)
        else:
            element = selector_or_element
        # Fallback for KZ details icon (robust selector)
        if element is None and (
            'Detalhes do Processo' in selector_or_element or 'detalhes do processo' in selector_or_element.lower()
        ):
            try:
                # Try clicking the KZ icon directly
                element = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[mattooltip*="Detalhes do Processo"]')
            except Exception:
                element = None
            if element is not None:
                driver.execute_script("arguments[0].click();", element)
                if log:
                    print('[CLICK] Clicked KZ details icon (img.mat-tooltip-trigger)')
                return True
            # Try clicking the parent button if img not clickable
            try:
                img = driver.find_element(By.CSS_SELECTOR, 'img.mat-tooltip-trigger[mattooltip*="Detalhes do Processo"]')
                button = img.find_element(By.XPATH, './ancestor::button[1]')
                driver.execute_script("arguments[0].click();", button)
                if log:
                    print('[CLICK] Clicked parent button of KZ details icon')
                return True
            except Exception:
                pass
        if element and element.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            driver.execute_script("arguments[0].click();", element)
            if log:
                print(f'[CLICK] Clicked: {element.text if hasattr(element, "text") else selector_or_element}')
            return True
        return False
    except Exception as e:
        if log:
            print(f'[CLICK][ERROR] Failed to click: {e}')
        return False

def buscar_seletor_robusto(driver, textos, contexto=None, timeout=10, log=True):
    """
    Versão 3.0 - Busca verdadeiramente robusta e não intrusiva
    
    Parâmetros:
    - contexto: elemento pai para limitar a busca (opcional)
    - textos: lista de textos ou atributos para buscar
    - timeout: tempo máximo de espera implícita
    """
    def buscar_input_associado(elemento):
        """Busca inputs próximos ao elemento encontrado"""
        try:
            # 1. Tenta encontrar input dentro do mesmo container
            input_associado = elemento.find_element(By.XPATH, 
                './following-sibling::input|./preceding-sibling::input|'
                './ancestor::*[contains(@class,"form-group")]//input|'
                './ancestor::*[contains(@class,"mat-form-field")]//input'
            )
            return input_associado
        except:
            return None

    try:
        # Fase 1: Busca direta por inputs editáveis
        for texto in textos:
            try:
                # Busca por atributos relevantes
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

        # Fase 2: Busca hierárquica se não encontrar diretamente
        for texto in textos:
            try:
                # Busca por texto visível
                elementos = driver.find_elements(By.XPATH, 
                    f'//*[contains(text(), "{texto}")]'
                )
                for el in elementos:
                    input_assoc = buscar_input_associado(el)
                    if input_assoc:
                        return input_assoc
            except:
                continue

        return None

    except Exception as e:
        if log:
            print(f'[Fix.py][DEBUG] Erro na busca robusta: {str(e)}')
        return None
def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR, log=True):
    """
    Versão corrigida - Espera até que um elemento esteja presente (e opcionalmente contenha texto).
    Agora verifica tipos de entrada e tem tratamento de erros melhorado.
    """
    try:
        if not isinstance(seletor, str):
            raise ValueError(f"Seletor deve ser string, recebido: {type(seletor)}")
            
        # Corrigido: 'if texto e not ...' para 'if texto and not ...'
        if texto and not isinstance(texto, str):
            raise ValueError(f"Text must be a string, got: {type(texto)}")

        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        
        if texto:
            WebDriverWait(driver, timeout).until(
                lambda d: texto in el.text
            )
            
        if log:
            print(f'[Fix.py] Elemento encontrado: {seletor}')
        return el
    except Exception as e:
        if log:
            print(f'[Fix.py][ERRO] esperar_elemento: {str(e)}')
        return None

# Seção: Extração de Dados
# Função para extrair documento
def extrair_documento(driver, regras_analise=None, timeout=15, log=True):
    """
    Extrai texto do documento aberto, aplica regras se houver.
    """
    try:
        # Espera o botão HTML
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            return None
        
        # Clica no botão HTML
        safe_click(driver, btn_html)
        time.sleep(1)
        
        # Extrai o texto do preview
        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            return None
        
        texto = preview.text
        
        # Aplica regras de análise se houver
        if regras_analise and callable(regras_analise):
            texto = regras_analise(texto)
        
        # Fecha o modal
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        
        return texto
    except Exception as e:
        if log:
            print(f'[EXTRAI][ERRO] Falha ao extrair documento: {e}')
        return None

def extrair_texto_pdf_por_conteudo(driver, termo=None, pagina=2, timeout=10):
    """
    Extrai o texto da página desejada de um PDF embutido (object.conteudo-pdf) e retorna o texto encontrado.
    Se termo for informado, retorna apenas o trecho que contém o termo.
    """
    import time
    try:
        obj_pdf = driver.find_element(By.CSS_SELECTOR, 'object.conteudo-pdf')
        doc = obj_pdf.get_property('contentDocument') or obj_pdf.get_property('contentWindow').document
        if not doc:
            print('[PDF] Não foi possível obter o document do PDF.')
            return None
        paginas = doc.querySelectorAll('.page')
        if len(paginas) > pagina:
            driver.execute_script('arguments[0].scrollIntoView(true);', paginas[pagina])
            time.sleep(2)
            texto = driver.execute_script('return arguments[0].innerText;', paginas[pagina])
            if termo:
                idx = texto.lower().find(termo.lower())
                if idx >= 0:
                    return texto[idx:idx+100]  # retorna trecho ao redor do termo
            return texto
        else:
            print('[PDF] Página não encontrada.')
            return None
    except Exception as e:
        print(f'[PDF][ERRO] {e}')
        return None
## Função para extrair dados do processo
def extrair_dados_processo(driver, log=True):
    """
    Extrai dados estruturados do processo com foco nas partes (ativas/passivas/outras) e inclui valor do cálculo PJeCalc.
    Retorna:
    {
        'numero': str,               # Número completo do processo
        'partes': {
            'ativas': [],
            'passivas': [],
            'outras': []
        },
        'metadados': dict,
        'calculo_pjecalc': { 'valor': ..., 'data': ... } ou None
    }
    """
    from selenium.webdriver.common.by import By
    import re
    
    dados = {
        'partes': {
            'ativas': [],
            'passivas': [],
            'outras': []
        },
        'metadados': {}
    }

    try:
        # Extração do diálogo de autuação
        dialogo = driver.find_element(By.CSS_SELECTOR, 'pje-autuacao-dialogo section#autuacao-dialogo')
        bloco = dialogo.find_element(By.CSS_SELECTOR, 'pje-autuacao section#processo')
        
        # Metadados básicos
        dts = bloco.find_elements(By.TAG_NAME, 'dt')
        dds = bloco.find_elements(By.TAG_NAME, 'dd')
        for dt, dd in zip(dts, dds):
            chave = dt.text.strip().replace(':', '')
            valor = dd.text.strip()
            if chave:
                dados['metadados'][chave] = valor
        
        # Extração robusta das partes
        for ul in bloco.find_elements(By.CSS_SELECTOR, 'ul.lista'):
            for li in ul.find_elements(By.CSS_SELECTOR, 'li.partes-corpo'):
                texto = li.text.strip()
                if not texto:
                    continue
                
                # Classificação por padrões
                texto_lower = texto.lower()
                if any(p in texto_lower for p in ['autor', 'requerente', 'exequente']):
                    categoria = 'ativas'
                elif any(p in texto_lower for p in ['réu', 'requerido', 'executado']):
                    categoria = 'passivas' 
                else:
                    categoria = 'outras'
                
                # Extração de documento se existir
                doc_match = re.search(
                    r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', 
                    texto
                )
                
                dados['partes'][categoria].append({
                    'nome': re.sub(r'\b(CPF|CNPJ).*', '', texto).strip(),
                    'documento': doc_match.group(0) if doc_match else None,
                    'texto_completo': texto
                })

        # INCLUIR INFORMAÇÃO DE CÁLCULO PJeCalc
        try:
            from calc import obter_valor_calculo_api, obter_id_processo_da_url
            id_processo = obter_id_processo_da_url(driver)
            if id_processo:
                resultado = obter_valor_calculo_api(driver, id_processo)
                if resultado:
                    dados['calculo_pjecalc'] = {
                        'valor': resultado['total'],
                        'data': resultado['dataLiquidacao']
                    }
                else:
                    dados['calculo_pjecalc'] = None
            else:
                dados['calculo_pjecalc'] = None
        except Exception as e:
            if log:
                print(f'[Fix.py] Erro ao extrair cálculo PJeCalc: {e}')
            dados['calculo_pjecalc'] = None

        if log:
            print('[Fix.py] Dados das partes extraídos com sucesso')
        return dados

    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao extrair dados do processo: {e}')
        return dados

def exibir_painel_copia_cola(driver, dados, log=True):
    """
    Exibe os dados extraídos do processo no painel Copia e Cola (formatação amigável).
    """
    conteudo = ''
    for k, v in dados.items():
        if isinstance(v, list):
            conteudo += f'\n{k}:\n'
            for item in v:
                conteudo += f'  - {item}\n'
        else:
            conteudo += f'{v}\n'
    # Preenche o painel (se existir)
    driver.execute_script(f"document.getElementById('painel_copia_cola_conteudo').innerText = `{conteudo}`;")
    if log:
        print('[Fix.py] Painel Copia e Cola exibido.')
      
# Seção: Manipulaçao de intimações
# Função para preencher campos de prazo
def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    """
    Preenche todos os campos de prazo (input[type=text].mat-input-element) dentro do formulário de minuta/comunicação.
    """
    try:
        # Busca o formulário principal
        form = wait(driver, '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form', timeout)
        if not form:
            if log:
                print('[Fix.py] Formulário de minuta/comunicação não encontrado.')
            return False
        
        # Busca todos os campos de texto de prazo
        inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="text"].mat-input-element')
        if not inputs:
            if log:
                print('[Fix.py] Nenhum campo de prazo encontrado.')
            return False
        
        for campo in inputs:
            driver.execute_script("arguments[0].focus();", campo)
            campo.clear()
            campo.send_keys(str(valor))
            
            # Dispara eventos JS para simular digitação real
            driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
            driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
            
            if log:
                print(f'[Fix.py] Campo de prazo preenchido com {valor}')
        
        return True
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao preencher campos de prazo: {e}')
        return False

def preencher_primeiro_input(driver, valor, seletor='input[type="text"]', timeout=10, log=True):
    """
    Preenche o primeiro input de texto visível encontrado pelo seletor informado.
    """
    try:
        campo = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, seletor))
        )
        campo.clear()
        campo.send_keys(str(valor))
        driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
        driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
        if log:
            print(f'[Fix.py] Primeiro input preenchido com: {valor}')
        return True
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao preencher primeiro input: {e}')
        return False


def marcar_checkbox_por_label(driver, texto_label, timeout=10, log=True):
    """
    Marca/desmarca checkbox com base no texto do label associado (robusto para checkboxes customizados).
    """
    try:
        labels = driver.find_elements(By.TAG_NAME, 'label')
        for label in labels:
            if texto_label.strip().lower() in label.text.strip().lower():
                checkbox = label.find_element(By.XPATH, './/preceding-sibling::input[@type="checkbox"] | .//input[@type="checkbox"]')
                driver.execute_script('arguments[0].scrollIntoView(true);', checkbox)
                checkbox.click()
                if log:
                    print(f'[Fix.py] Checkbox marcado/desmarcado: {texto_label}')
                return True
        if log:
            print(f'[Fix.py] Checkbox com label "{texto_label}" não encontrado.')
        return False
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao marcar checkbox: {e}')
        return False


def selecionar_opcao_select(driver, seletor_select, texto_opcao, timeout=10, log=True):
    """
    Seleciona uma opção em <select> tradicional pelo texto visível.
    """
    try:
        select = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_select))
        )
        for option in select.find_elements(By.TAG_NAME, 'option'):
            if texto_opcao.strip().lower() in option.text.strip().lower():
                option.click()
                if log:
                    print(f'[Fix.py] Opção selecionada: {texto_opcao}')
                return True
        if log:
            print(f'[Fix.py] Opção "{texto_opcao}" não encontrada em {seletor_select}')
        return False
    except Exception as e:
        if log:
            print(f'[Fix.py] Erro ao selecionar opção: {e}')
        return False

# Seção: Ferramentas
def criar_gigs(driver, dias_uteis, observacao, tela='principal', timeout=10, log=True):
    """
    Cria GIGS em qualquer tela (principal ou minuta), parametrizável.
    tela: 'principal' (default) ou 'minuta' para lógica adaptada.
    """
    import datetime
    t0 = time.time()
    if log:
        print(f"[GIGS] Iniciando criação de GIGS: {dias_uteis}/{observacao} (tela={tela}) [{datetime.datetime.now().strftime('%H:%M:%S')}] (T0)")
    try:
        # Fecha modal de GIGS aberto, se houver
        modais = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container')
        for modal in modais:
            if modal.is_displayed():
                try:
                    btn_cancelar = modal.find_element(By.XPATH, ".//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cancelar')]")
                    if btn_cancelar.is_displayed():
                        btn_cancelar.click()
                        time.sleep(0.7)
                        if log:
                            print('[GIGS] Modal de GIGS anterior fechado (Cancelar).')
                        break
                except Exception:
                    pass
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.7)
                    if log:
                        print('[GIGS] Modal de GIGS anterior fechado (ESC).')
                    break
                except Exception:
                    pass
        # --- NOVO FLUXO MAISPJE ---
        if tela == 'minuta':
            if '/minutar' not in driver.current_url:
                if log:
                    print(f'[GIGS][ERRO] Não está na tela de minuta! URL atual: {driver.current_url}')
                return False
            btn_bars = driver.find_element(By.CSS_SELECTOR, '.fa-bars')
            btn_bars.click()
            time.sleep(0.7)
            btn_tag = driver.find_element(By.CSS_SELECTOR, '.fa-tag')
            btn_tag.click()
            time.sleep(1.2)
        else:
            # 1. Garante que o GIGS está aberto
            try:
                btn_mostrar_gigs = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Mostrar o GIGS"]')
                if btn_mostrar_gigs.is_displayed():
                    btn_mostrar_gigs.click()
                    time.sleep(1.2)
                    if log:
                        print('[GIGS] GIGS aberto via botão "Mostrar o GIGS".')
            except Exception:
                pass  # Se não existe, já está aberto
            # 2. Clica no botão "Nova atividade" dentro de pje-gigs-lista-atividades
            nova_atividade_btn = None
            try:
                lista_atividades = driver.find_element(By.CSS_SELECTOR, 'pje-gigs-lista-atividades')
                botoes = lista_atividades.find_elements(By.TAG_NAME, 'button')
                for btn in botoes:
                    if btn.is_displayed() and 'nova atividade' in btn.text.strip().lower():
                        nova_atividade_btn = btn
                        break
            except Exception:
                pass
            if nova_atividade_btn:
                nova_atividade_btn.click()
                time.sleep(1.2)
            else:
                if log:
                    print(f'[GIGS][ERRO] Botão "Nova atividade" não encontrado dentro de pje-gigs-lista-atividades!')
                return False
        # Espera o formulário de GIGS abrir
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'form'))
        )
        time.sleep(0.7)
        # Preenche Dias Úteis (MaisPje: input[formcontrolname="dias"])
        campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
        campo_dias.clear()
        time.sleep(0.3)
        campo_dias.send_keys(str(dias_uteis))
        if log:
            print(f'[GIGS] Dias úteis preenchido: {dias_uteis}')
        time.sleep(0.7)
        # Preenche Observação (MaisPje: textarea[formcontrolname="observacao"])
        campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
        campo_obs.clear()
        time.sleep(0.3)
        campo_obs.send_keys(observacao)
        if log:
            print(f'[GIGS] Observação preenchida: {observacao}')
        time.sleep(0.7)
        # Clica no botão Salvar
        botoes_salvar = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
        btn_salvar = None
        for btn in botoes_salvar:
            if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                btn_salvar = btn
                break
        if not btn_salvar:
            if log:
                print(f'[GIGS][ERRO] Botão Salvar não encontrado!')
            return False
        btn_salvar.click()
        if log:
            print(f'[GIGS] Botão Salvar clicado.')
        time.sleep(2.5)
        if log:
            print(f'[GIGS] GIGS criado com sucesso!')
        return True
    except Exception as e:
        if log:
            print(f'[GIGS][ERRO] Falha ao criar GIGS: {e}')
        return False

def Infojud(ni, log=True):
    """
    Gera link de consulta Infojud (CPF/CNPJ) e imprime/loga.
    """
    ni = str(ni).strip()
    link = None
    if len(ni) == 11:
        link = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI={ni}"
    elif len(ni) == 14:
        link = f"https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI={ni}"
    if log:
        print(f"[INFOJUD] Link para consulta: {link if link else 'NI inválido'}")
    return link

# Seção: Mandados Argos (Pesquisa Patrimonial)

def buscar_documentos_sequenciais(driver, log=True):
    """
    Placeholder para buscar_documentos_sequenciais (pode ser expandido conforme regras do fluxo).
    """
    if log:
        print('[Fix.py] buscar_documentos_sequenciais chamado.')
    # Implementação futura conforme regras do fluxo
    pass

def tratar_anexos(certidao, driver, log=True):
    """
    Trata anexos da certidão: abre cada anexo, aplica sigilo/visibilidade se for INFOJUD, IRPF, DOI;
    se for SISBAJUD (positivo/parcial/integral), apenas loga e registra bloqueio.
    Retorna True se algum bloqueio SISBAJUD for registrado.
    """
    bloqueio_registrado = False
    try:
        anexos = []
        linhas = certidao.text.splitlines()
        for l in linhas:
            if "Anexo(s):" in l:
                idx = linhas.index(l)
                anexos = linhas[idx+1:]
                break
        if not anexos:
            for l in linhas:
                if l.strip().startswith("- "):
                    anexos.append(l.strip())
        if log:
            print(f"[ANEXOS][DETALHE] {len(anexos)} anexos detectados na certidão de devolução.")
        for idx, texto in anexos:
            if log:
                print(f"[ANEXOS][{idx+1}/{len(anexos)}] Conteúdo: '{texto}'")
            texto_lower = texto.lower()
            if any(p in texto_lower for p in ["infojud", "irpf", "doi", "sisbajud"]):
                strongs = certidao.find_elements(By.TAG_NAME, 'strong')
                alvo = None
                for s in strongs:
                    if s.text.strip() in texto:
                        alvo = s
                        break
                if alvo:
                    alvo.click()
                    time.sleep(0.7)
                    if any(p in texto_lower for p in ["infojud", "irpf", "doi"]):
                        try:
                            btn_sigilo = certidao.find_element(By.CSS_SELECTOR, "i.fa-wpexplorer")
                            btn_sigilo.click()
                            time.sleep(0.5)
                            btn_visibilidade = certidao.find_element(By.CSS_SELECTOR, "i.fa-plus")
                            if btn_visibilidade.is_displayed():
                                btn_visibilidade.click()
                                time.sleep(0.5)
                                modal_contexto = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-content")
                                btn_coluna = modal_contexto.find_element(By.CSS_SELECTOR, "i.botao-icone-titulo-coluna")
                                btn_coluna.click()
                                time.sleep(0.3)
                                btn_salvar = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-actions > button:nth-child(1) > span:nth-child(1)")
                                btn_salvar.click()
                                if log:
                                    print(f"[ANEXOS][{idx+1}] Sigilo e visibilidade aplicados com sucesso no anexo '{texto}'.")
                                modal_contexto.send_keys(Keys.ESCAPE)
                                if log:
                                    print("[MODAL] Fechado com ESC.")
                                time.sleep(1)
                            else:
                                if log:
                                    print(f"[ANEXOS][{idx+1}] Botão de visibilidade não visível para o anexo '{texto}'.")
                        except Exception as e:
                            if log:
                                print(f"[ERRO] Ao inserir sigilo/visibilidade em anexo '{texto}': {e}")
                    if "sisbajud" in texto_lower and any(p in texto_lower for p in ["positivo", "parcial", "integral"]):
                        if log:
                            print(f"[REGISTRO BLOQUEIO] SISBAJUD encontrado: {texto}. Bloqueio POSITIVO registrado.")
                        bloqueio_registrado = True
                else:
                    if log:
                        print(f"[ANEXOS][{idx+1}] Não foi possível localizar o elemento visual do anexo '{texto}'.")
    except Exception as e:
        if log:
            print(f"[ANEXOS][ERRO] Falha ao localizar ou processar anexos da certidão: {e}")
        return False
    return bloqueio_registrado

def fechar_prazo(driver, log=True):
    """
    Fecha prazo de intimação:
    1. Clica no envelope (intimação)
    2. Marca checkbox
    3. Clica em OK
    4. Confirma no modal
    """
    try:
        if log:
            print("[PRAZO] Iniciando fechamento de prazo...")
            
        # 1. Clica no envelope (intimação)
        btn_envelope = esperar_elemento(
            driver,
            "i.fa-envelope.fa-lg.icone-cinza",
            timeout=5,
            log=log
        )
        if not btn_envelope:
            raise Exception("Botão de intimação não encontrado")
            
        safe_click(driver, btn_envelope)
        time.sleep(1)
        
        # 2. Marca checkbox
        modal = esperar_elemento(
            driver,
            ".flex-container-raiz, .mat-dialog-container",
            timeout=5,
            log=log
        )
        if not modal:
            raise Exception("Modal de intimação não encontrado")
            
        checkbox = modal.find_element(By.CSS_SELECTOR, ".mat-checkbox-inner-container-no-side-margin")
        safe_click(driver, checkbox)
        time.sleep(0.5)
        
        # 3. Clica em OK
        btn_ok = modal.find_element(By.CSS_SELECTOR, ".mat-raised-button > span")
        safe_click(driver, btn_ok)
        time.sleep(0.5)
        
        # 4. Confirma no modal
        modal_confirmacao = esperar_elemento(
            driver,
            ".mat-dialog-actions > button:nth-child(1) > span:nth-child(1)",
            timeout=5,
            log=log
        )
        if modal_confirmacao:
            safe_click(driver, modal_confirmacao)
            time.sleep(0.5)
        
        if log:
            print("[PRAZO] Prazo fechado com sucesso")
            
    except Exception as e:
        if log:
            print(f"[PRAZO][ERRO] Falha ao fechar prazo: {e}")
        raise
def analise_argos(driver):
    """
    Fluxo robusto para análise de mandados do tipo Argos (Pesquisa Patrimonial).
    - Trata anexos SISBAJUD.
    - Extrai trecho relevante do PDF se necessário.
    - Executa lógica adicional de Argos (placeholder para regras futuras).
    """
    print('[ARGOS] Iniciando análise Argos...')
    try:
        resultado_sisbajud = tratar_anexos_sisbajud(driver)
        if resultado_sisbajud == 'nao_encontrado':
            texto_pdf = extrair_texto_pdf_por_conteudo(driver, termo='sisbajud')
            print(f'[PDF][ARGOS] Trecho extraído: {texto_pdf}')
        # Placeholder para lógica Argos adicional
        print('[ARGOS] Análise Argos concluída.')
    except Exception as e:
        print(f'[ARGOS][ERRO] Falha na análise Argos: {e}')

def buscar_documento_argos(driver, log=True):
    """
    Busca e extrai documento específico para Argos:
    1. Procura primeiro despacho ou decisão
    2. Se for decisão, extrai e retorna
    3. Se for despacho, verifica conteúdo e:
       - Se contém "EM QUE PESE A AUSÊNCIA", extrai e retorna
       - Senão, busca próxima decisão após o despacho
    Retorna: tupla (texto, tipo) onde tipo é 'decisao' ou 'despacho'
    """
    import re
    try:
        # Encontra todos os itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        
        # Procura primeiro despacho ou decisão
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                
                # Verifica se é despacho ou decisão
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                    
                # Verifica se é de juiz
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = False
                for mag in mag_icons:
                    if 'otavio' in aria or 'mariana' in aria:
                        mag_ok = True
                        break
                if not mag_ok:
                    continue
                    
                # Clica no documento
                link.click()
                time.sleep(1)
                
                # Extrai o texto
                texto = extrair_documento(driver)
                if not texto:
                    continue
                    
                # Se é decisão, retorna imediatamente
                if 'decisão' in doc_text or 'sentença' in doc_text:
                    return (texto, 'decisao')
                    
                # Se é despacho, verifica conteúdo
                if 'EM QUE PESE A AUSÊNCIA' in texto.upper():
                    return (texto, 'despacho')
                    
            except Exception:
                continue
                
        # Se chegou aqui, não encontrou documento válido
        if log:
            print('[ARGOS] Nenhum documento válido encontrado.')
        return (None, None)
        
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha ao buscar documento: {e}')
        return (None, None)


def buscar_ultimo_despacho_juiz(driver, log=True):
    """
    Busca o último despacho de Mariana ou Otávio na timeline do processo.
    Retorna o texto do despacho e a data.
    """
    try:
        # Espera e encontra todos os itens da timeline
        itens_timeline = esperar_colecao(driver, "li.tl-item-container", qtde_minima=1, timeout=10, log=log)
        
        # Procura o último despacho de Mariana ou Otávio
        for item in reversed(itens_timeline):
            texto = item.text.lower()
            if any(j in texto for j in ['mariana', 'otávio', 'otavio']):
                # Encontra a data
                data_element = item.find_elements(By.CSS_SELECTOR, "time")
                data = data_element[0].text if data_element else "Data não encontrada"
                
                # Extrai o conteúdo do despacho
                conteudo = item.text
                
                if log:
                    print(f'[DESPACHO] Encontrado despacho de juiz: {data}')
                
                return {
                    'data': data,
                    'conteudo': conteudo
                }
        
        if log:
            print('[DESPACHO] Não encontrado despacho de juiz na timeline.')
        return None
        
    except Exception as e:
        if log:
            print(f'[DESPACHO][ERRO] Falha ao buscar despacho: {e}')
        return None

# Seção: Mandados Outros

def analise_outros(driver):
    """
    Fluxo robusto para análise de mandados do tipo Outros (Oficial de Justiça).
    - Extrai certidão do documento.
    - Cria GIGS sempre como tipo 'prazo', 0 dias, nome 'Pz mdd'.
    """
    print('[OUTROS] Iniciando análise Outros...')
    texto = extrair_documento(driver, regras_analise=lambda texto: criar_gigs(driver, 0, 'Pz mdd', tela='principal'))
    if not texto:
        print("[OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
    print('[OUTROS] Análise Outros concluída.')

def indexar_lista_processos(driver, seletor_linha='tr.cdk-drag', logar_termo_observacao=False, termo_chave='xs pec'):
    """
    Identifica e loga os números dos processos presentes na lista da tela atual.
    Se logar_termo_observacao=True, também loga o termo após 'xs pec' na coluna Observações.
    """
    import re
    linhas = driver.find_elements(By.CSS_SELECTOR, seletor_linha)
    print(f'[INDEXAR] Total de processos encontrados: {len(linhas)}')
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    for idx, linha in enumerate(linhas):
        try:
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                texto = tds[0].text.strip() if tds else ''
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            if logar_termo_observacao:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                termo = ''
                if len(tds) >= 10:
                    obs = tds[9].text.strip()
                    if obs.lower().startswith(termo_chave):
                        termo = obs[len(termo_chave):].strip()
                print(f'[INDEXAR] {idx+1:02d}: {num_proc} | TERMO: {termo}')
            else:
                print(f'[INDEXAR] {idx+1:02d}: {num_proc}')
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e}')

def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    """
    Indexa (conta/loga) os processos e já executa o processamento sequencial, com logs claros.
    """
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
    indexar_lista_processos(driver, logar_termo_observacao=False)
    print('[FLUXO] Indexação concluída. Iniciando processamento da lista de processos...', flush=True)
    processar_lista_processos(driver, callback, seletor_btn=seletor_btn, modo=modo, max_processos=max_processos, log=log)
    print('[FLUXO] Fim do processamento da lista de processos.', flush=True)

def extrair_xs_pec_atividades(driver, log=True):
    """
    Extrai todas as descrições de atividades que contenham 'xs pec' diretamente da tabela de atividades do GIGS.
    Retorna uma lista de textos encontrados.
    """
    resultados = []
    try:
        # Aguarda o componente de atividades estar presente
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-gigs-atividades table'))
        )
        if log:
            print('[XSPEC] Tabela de atividades localizada.')
        # Busca todos os spans de descrição
        descricoes = driver.find_elements(By.CSS_SELECTOR, 'pje-gigs-atividades span.descricao')
        if log:
            print(f'[XSPEC] {len(descricoes)} descrições encontradas.')
        for desc in descricoes:
            texto = desc.text.strip()
            if 'xs pec' in texto.lower():
                resultados.append(texto)
                if log:
                    print(f'[XSPEC] Encontrado: {texto}')
        if not resultados and log:
            print('[XSPEC] Nenhum "xs pec" encontrado nas descrições.')
        return resultados
    except Exception as e:
        if log:
            print(f'[XSPEC][ERRO] Falha ao extrair xs pec: {e}')
        return resultados

# Função auxiliar para tratar anexos do SISBAJUD
def tratar_anexos_sisbajud(driver, log=True):
    """
    Trata especificamente anexos do SISBAJUD.
    Retorna: 'encontrado' se encontrou e tratou, 'nao_encontrado' se não achou
    """
    try:
        anexos = driver.find_elements(By.CSS_SELECTOR, '.anexo')
        for anexo in anexos:
            if 'sisbajud' in anexo.text.lower():
                if log:
                    print('[SISBAJUD] Anexo encontrado')
                return 'encontrado'
        return 'nao_encontrado'
    except Exception as e:
        if log:
            print(f'[SISBAJUD][ERRO] {e}')
        return 'nao_encontrado'

def esperar_colecao(driver, seletor, qtde_minima=1, timeout=10, log=True):
    """
    Espera até que uma coleção de elementos esteja presente e tenha pelo menos qtde_minima itens.
    """
    try:
        def check_collection(d):
            elementos = d.find_elements(By.CSS_SELECTOR, seletor)
            return elementos if len(elementos) >= qtde_minima else False

        elementos = WebDriverWait(driver, timeout).until(check_collection)
        if log:
            print(f'[COLECAO] Encontrados {len(elementos)} elementos para {seletor}')
        return elementos
    except Exception as e:
        if log:
            print(f'[COLECAO][ERRO] Timeout esperando {seletor}: {e}')
        return []

# =========================
# 2. FUNÇÕES DE INTERAÇÃO PJe (Movidas/Adaptadas)
# =========================

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

def aplicar_filtro_100(driver):
    """
    Seleciona '100' no filtro de itens por página do painel global.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    try:
        # Pode haver mais de um seletor, escolha o último visível
        seletores = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-select-min-line')]")
        seletor = None
        for s in reversed(seletores):
            if s.is_displayed():
                seletor = s
                break
        if not seletor:
            print('[FILTRO][ERRO] Nenhum seletor de linhas por página visível encontrado.')
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", seletor)
        seletor.click()
        print('[FILTRO] Dropdown de linhas por página clicado.')
        time.sleep(1.2)  # Aguarda o dropdown abrir
        opcoes = driver.find_elements(By.XPATH, "//mat-option//span[contains(text(), '100')]")
        for opcao in opcoes:
            if opcao.is_displayed():
                opcao.click()
                print('[FILTRO] Selecionado 100 itens por página.')
                time.sleep(1)
                return True
        print('[FILTRO][ERRO] Opção 100 não encontrada entre as opções visíveis.')
        return False
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha ao aplicar filtro 100: {e}')
        return False

