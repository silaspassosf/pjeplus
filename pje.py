import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import re
import shutil
import tempfile
import os

# ========== CONFIGURAÇÕES ==========
PJE_LISTA_URL = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
PJE_DETALHE_REGEX = r"/detalhe/.*"

# ========== FLUXO PRINCIPAL: LOGIN AUTOMÁTICO ==========
# (1) Login automático com perfil dedicado do Firefox
# Funções: main, login_automatico, verificar_login_ativo

def main():
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from webdriver_manager.firefox import GeckoDriverManager
    import time

    limpar_temp_selenium()
    firefox_options = FirefoxOptions()
    firefox_options.add_argument('--start-maximized')
    # Atualiza para usar o novo perfil dedicado criado pelo usuário
    profile_path = r'C:\Users\Silas\AppData\Roaming\Mozilla\Dev'
    firefox_options.profile = profile_path
    firefox_options.binary_location = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=firefox_options)
    driver.implicitly_wait(10)

    try:
        driver.get('https://pje.trt2.jus.br/pjekz/')
        time.sleep(2)
        login_automatico(driver, '35305203813', 'SpF59866')
        print('[DEBUG] Login realizado com sucesso.')
        registrar_url(driver.current_url)

        # Loop de monitoramento contínuo
        aba_origem = None
        ultima_url = driver.current_url
        ultimas_abas = driver.window_handles
        while True:
            try:
                # Detecta troca de aba
                if driver.window_handles != ultimas_abas:
                    aba_origem = ultima_url  # Salva a URL de origem da troca de aba
                    ultimas_abas = driver.window_handles
                    driver.switch_to.window(ultimas_abas[-1])
                    print('[DEBUG] Troca de aba detectada')
                url_atual = driver.current_url
                # 1. Fluxo de prazos vencidos (painel global)
                if url_atual == 'https://pje.trt2.jus.br/pjekz/painel/global':
                    print('[DEBUG] URL painel global detectada, iniciando fluxo Vencimento da Lista...')
                    vencimento_da_lista(driver)
                # 2. Fluxo Mandados: troca de aba de documentos internos para peticao
                if aba_origem and '/documentos-internos' in aba_origem and '/peticao/' in url_atual:
                    print('[DEBUG] Nova aba de petição aberta a partir de documentos internos, iniciando fluxo Mandados...')
                    fluxo_automatico_mandados(driver)
                    aba_origem = None  # Limpa para evitar disparo duplo
                if url_atual != ultima_url:
                    registrar_url(url_atual)
                    ultima_url = url_atual
                time.sleep(0.5)
            except Exception as e:
                print(f'[MONITOR][ERRO] {e}')
                break
    except Exception as e:
        print(f'[MAIN][ERRO] {e}')

      
def login_automatico(driver, usuario, senha):
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    # 1. Clicar no botão do login PDPJ
    btn_pdpj = esperar_elemento(driver, 'button#btnSsoPdpj > img', timeout=10)
    if btn_pdpj:
        safe_click(driver, btn_pdpj)
        time.sleep(2)
    else:
        return False
    # 2. Preencher usuário
    campo_usuario = esperar_elemento(driver, 'input#username', timeout=10)
    if campo_usuario:
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
    else:
        return False
    # 3. Preencher senha
    campo_senha = esperar_elemento(driver, 'input#password', timeout=10)
    if campo_senha:
        campo_senha.clear()
        campo_senha.send_keys(senha)
    else:
        return False
    # 4. Clicar em Entrar
    btn_entrar = esperar_elemento(driver, 'input#kc-login', timeout=10)
    if btn_entrar:
        safe_click(driver, btn_entrar)
        time.sleep(3)
        return True
    else:
        return False

def verificar_login_ativo(driver):
    # Detecta se está na tela de login do PJe TRT2
    try:
        el = esperar_elemento(driver, 'input#username', timeout=5)
        if el:
            return False
        return True
    except Exception:
        return True

# ========== FLUXO AUTOMÁTICO DE MANDADOS (PETIÇÃO ABERTA DE DOCUMENTOS INTERNOS) ==========

def fluxo_automatico_mandados(driver):
    from selenium.webdriver.common.by import By

    try:
        cabecalho = driver.find_element(By.CSS_SELECTOR, 'div.cabecalho-conteudo')
        texto = cabecalho.text.strip().lower()
        print("[MANDADOS] verificando fluxo correto de mandado")
        if "certidão de devolução" in texto:
            print("[MANDADOS] identificado certidao de devolucao - fluxo 1")
            fluxo_mandados_hipotese1(driver)
        elif "certidão de oficial" in texto:
            print("[MANDADOS] identificado certidao de oficial - fluxo 2")
            fluxo_mandados_hipotese2(driver)
        else:
            print(f"[MANDADOS] documento ativo não elegível: '{texto}'")
    except Exception as e:
        print(f"[MANDADOS][ERRO] Falha ao identificar documento ativo pela classe cabecalho-conteudo: {e}")

# ========== CAMINHO 1: PRAZOS VENCIDOS ==========
# Seleciona prazos vencidos e inicia fluxo Vencimento
# Funções: acessar_prazos_vencidos, selecionar_processos_livres_e_aplicar_atividade

def vencimento_da_lista(driver):
    """
    Fluxo automatizado para tarefa 'Prazos Vencidos' na lista do painel global.
    1. Aguarda e clica no botão 'Prazos Vencidos' (span).
    2. Aguarda URL correta de carregamento.
    3. Aplica filtro de linhas (100 por página) e filtro de fase (Liquidação e Execução).
    4. Marca todos os processos.
    5. Clica no ícone de mala (fa-suitcase).
    6. Aguarda carregamento da tela de movimentação em lote.
    7. Loga cada etapa.
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    print('[VENCIMENTO][INICIO] Iniciando fluxo Vencimento da Lista')
    # 1. Clicar no botão 'Prazos Vencidos'
    try:
        btn_prazos = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'html > body > pje-root > mat-sidenav-container > mat-sidenav-content > div > div > pje-painel-global > div:nth-of-type(1) > pje-painel-item:nth-of-type(1) > div > mat-card > mat-card-title > span'))
        )
        btn_prazos.click()
        print('[VENCIMENTO][CLICK] Botão "Prazos Vencidos" clicado.')
    except Exception as e:
        print(f'[VENCIMENTO][ERRO] Falha ao clicar em "Prazos Vencidos": {e}')
        return
    # 2. Aguarda URL correta
    url_esperada = 'https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos'
    for _ in range(20):
        if driver.current_url == url_esperada:
            print(f'[VENCIMENTO][URL] Página correta carregada: {driver.current_url}')
            break
        time.sleep(0.5)
    else:
        print(f'[VENCIMENTO][ERRO] URL não carregou: {driver.current_url}')
        return
    # 3 e 4. Filtro de linhas e fase
    aplicar_filtros_fase(driver)
    # 5. Marcar todos (fa-check)
    try:
        btn_check = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.fa-check'))
        )
        btn_check.click()
        print('[VENCIMENTO][CHECK] Todos marcados.')
        time.sleep(0.7)
    except Exception as e:
        print(f'[VENCIMENTO][ERRO] Falha ao marcar todos: {e}')
        return
    # 6. Clicar mala (fa-suitcase)
    try:
        btn_mala = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.fa-suitcase'))
        )
        btn_mala.click()
        print('[VENCIMENTO][MALA] Ícone de mala clicado.')
    except Exception as e:
        print(f'[VENCIMENTO][ERRO] Falha ao clicar mala: {e}')
        return
    # 7. Aguarda movimentação em lote
    url_mov = 'https://pje.trt2.jus.br/pjekz/painel/movimentacao-lote'
    for _ in range(20):
        if driver.current_url == url_mov:
            print(f'[VENCIMENTO][MOV] Tela de movimentação em lote carregada: {driver.current_url}')
            break
        time.sleep(0.5)
    else:
        print(f'[VENCIMENTO][ERRO] Movimentação em lote não carregou: {driver.current_url}')
        return
    print('[VENCIMENTO][FIM] Fluxo concluído.')

def aplicar_filtros_fase(driver):
    """
    Aplica filtro de linhas (100 por página) e filtro de fase (Liquidação e Execução) na lista de prazos vencidos.
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    # 1. Filtro de linhas (100 por página)
    try:
        btn_linhas = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-select-value-117'))
        )
        btn_linhas.click()
        print('[FILTRO][LINHAS] Dropdown de linhas clicado.')
        time.sleep(0.5)
        opcao_100 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-option-266 > span'))
        )
        opcao_100.click()
        print('[FILTRO][LINHAS] Selecionado 100 por página.')
        time.sleep(1)
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha no filtro de linhas: {e}')
    # 2. Filtro de fase processual
    try:
        btn_fase = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.ng-tns-c179-306'))
        )
        btn_fase.click()
        print('[FILTRO][FASE] Dropdown de fases clicado.')
        time.sleep(0.5)
        opcao_liquidacao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-option-274 > span'))
        )
        if 'liquidação' in opcao_liquidacao.text.lower():
            opcao_liquidacao.click()
            print('[FILTRO][FASE] Selecionada fase Liquidação.')
            time.sleep(0.5)
        opcao_execucao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-option-275 > span'))
        )
        if 'execução' in opcao_execucao.text.lower():
            opcao_execucao.click()
            print('[FILTRO][FASE] Selecionada fase Execução.')
            time.sleep(0.5)
        btn_filtrar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.botao-filtrar > span > i.fa-filter'))
        )
        btn_filtrar.click()
        print('[FILTRO][FASE] Botão filtrar clicado.')
        time.sleep(1)
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha no filtro de fase: {e}')

def selecionar_processos_livres_e_aplicar_atividade(driver):
    print('Selecionando processos Livres e aplicando atividade...')
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        print(f'[DEBUG] Total de linhas encontradas na tabela: {len(linhas)}')
        selecionados = 0
        for idx, linha in enumerate(linhas):
            try:
                prazo = linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(9) time')
                prazo_vazio = not prazo or not prazo[0].text.strip()
            except NoSuchElementException:
                prazo_vazio = True
            has_comment = len(linha.find_elements(By.CSS_SELECTOR, 'i.fa-comment')) > 0
            try:
                input_field = linha.find_elements(By.CSS_SELECTOR, 'input[matinput]')
                campo_preenchido = input_field and input_field[0].get_attribute('value').strip()
            except NoSuchElementException:
                campo_preenchido = False
            tem_lupa = len(linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')) > 0
            print(f'[DEBUG] Linha {idx}: prazo_vazio={prazo_vazio}, comentario={bool(has_comment)}, campo_preenchido={bool(campo_preenchido)}, lupa={bool(tem_lupa)}')
            if prazo_vazio and not has_comment and not campo_preenchido and not tem_lupa:
                try:
                    checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type="checkbox"]')
                    if not checkbox.is_selected():
                        driver.execute_script('arguments[0].click()', checkbox)
                        driver.execute_script('arguments[0].style.backgroundColor = "#ffccd2";', linha)
                        selecionados += 1
                except Exception as e:
                    print(f'[DEBUG] Falha ao marcar checkbox na linha {idx}: {e}')
                    continue
        print(f'[DEBUG] Total de processos livres selecionados: {selecionados}')
        if selecionados == 0:
            driver.save_screenshot('screenshot_nenhum_processo_livre.png')
            print('Nenhum processo livre encontrado para seleção. Screenshot salvo.')
            return False
    except Exception as e:
        print(f'Erro ao selecionar processos livres: {e}')
        driver.save_screenshot('screenshot_atividade_silas_fail.png')
        print('[DEBUG] Screenshot salvo: screenshot_atividade_silas_fail.png')
        return False
    # 2. Adicionar atividade .Silas em lote
    try:
        gigs_lote_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-tag.icone'))
        )
        safe_click(driver, gigs_lote_btn)
        time.sleep(1)
        atividade_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Atribuir Atividade em Lote"]'))
        )
        safe_click(driver, atividade_btn)
        time.sleep(1)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mat-dialog-4'))
        )
        opcoes = driver.find_elements(By.CSS_SELECTOR, '#mat-dialog-4 mat-option span.mat-option-text')
        silas_opcao = None
        for opcao in opcoes:
            if '.silas' in opcao.text.strip().lower():
                silas_opcao = opcao
                break
        if silas_opcao:
            safe_click(driver, silas_opcao)
            time.sleep(0.5)
        else:
            print('[DEBUG] Opção de atividade ".Silas" não encontrada!')
            driver.save_screenshot('screenshot_atividade_silas_opcao_nao_encontrada.png')
            return False
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-dialog-container#mat-dialog-4 > pje-gigs-cadastro-atividades.ng-star-inserted > div > form.ng-valid.ng-touched.ng-dirty > mat-card-actions.mat-card-actions.botoes-cadastro-crud.ng-star-inserted > button.mat-focus-indicator.mat-tooltip-trigger.mat-raised-button.mat-button-base.mat-primary.cdk-focused.cdk-mouse-focused:nth-of-type(2) > span.mat-button-wrapper:nth-of-type(1)'))
        )
        safe_click(driver, btn_salvar)
        print('Atividade .Silas aplicada com sucesso!')
        time.sleep(2)
        return True
    except Exception as e:
        print(f'Erro ao adicionar atividade .Silas: {e}')
        driver.save_screenshot('screenshot_atividade_silas_fail.png')
        print('[DEBUG] Screenshot salvo: screenshot_atividade_silas_fail.png')
        return False
        
def analisar_prazo_detalhe(driver):
    import re
    import time
    print('[DEBUG] Iniciando análise de prazo na aba de detalhes...')
    try:
        # 1. Seleciona documento relevante (decisão, despacho ou sentença do Otavio ou Mariana)
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        doc_encontrado = None
        doc_link = None
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = False
                for mag in mag_icons:
                    aria = mag.get_attribute('aria-label').lower()
                    if 'otavio' in aria or 'mariana' in aria:
                        mag_ok = True
                        break
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    break
            except Exception:
                continue
        if not doc_encontrado or not doc_link:
            print('[DEBUG] Nenhum documento relevante encontrado.')
            return
        print('[DEBUG] Documento relevante encontrado, clicando para abrir painel...')
        doc_link.click()
        time.sleep(1)  # Aguarda painel abrir
        # Tenta extrair o texto do documento
        texto = None
        try:
            texto = driver.find_element(By.CSS_SELECTOR, '.conteudo-html').text.lower()
        except Exception:
            print('[DEBUG] Conteúdo HTML não encontrado, tentando visualizar código...')
            try:
                btn_html = driver.find_element(By.CSS_SELECTOR, '.fa-file-code')
                safe_click(driver, btn_html)
                preview = esperar_elemento(driver, '#previewModeloDocumento', 5)
                texto = preview.text.lower() if preview and preview.text else None
                close_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Fechar"]')
                safe_click(driver, close_btn)
                time.sleep(1)
            except Exception:
                texto = None
        if not texto:
            print('[DEBUG] Não foi possível extrair o texto do documento.')
            acionar_botao_pje(driver, 'gigs', 'Sconf')
            return
        print('[DEBUG] Texto extraído do documento (completo):')
        print(texto)
        # 4. Analisa o texto conforme regras do Tampermonkey
        regras = [
            (re.compile(r'concede-se 05 dias|visibilidade.*advogados|in[ií]cio da flu[êe]ncia|indicar meios|oito dias para apresenta[cç][aã]o'), 'gigs', 'ConfG'),
            (re.compile(r'revel|concorda com homologação'), 'gigs', 'Homol'),
            (re.compile(r'hasta|saldo devedor|prescrição'), 'gigs', 'Pec'),
            (re.compile(r'impugnações apresentadas'), 'gigs', 'Pesq'),
            (re.compile(r'cumprido o acordo homologado'), 'movimentar', 'Arq'),
            (re.compile(r'unicamente previdenciário'), 'concluso', 'suspinss')
        ]
        trecho_encontrado = None
        for regex, grupo, botao in regras:
            m = regex.search(texto)
            if m:
                trecho_encontrado = m.group(0)
                print(f'[DEBUG] Trecho encontrado para regra: {trecho_encontrado}')
                break
        if not trecho_encontrado:
            print('[DEBUG] Nenhum trecho de regra encontrado no texto.')
        # [NOVO] Fechar janela HTML pressionando ESC
        from selenium.webdriver.common.keys import Keys
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        print('[DEBUG] Janela HTML fechada com ESC.')
        time.sleep(1)
        # [NOVO] Executar autogigs: criar GIGS tipo prazo (observação "silas", 1 dia útil)
        print('[DEBUG] Executando análise e criação de GIGS conforme regra do texto...')
        analisar_e_criar_gigs(driver, texto)
    except Exception as e:
        print(f'[ERRO] Erro na análise de prazo em detalhes: {e}')

# ========== CAMINHO 2: ANÁLISE DE PRAZO ==========
# Navega até análises (lista-processos/8), aplica filtros, abre nova aba /detalhe e injeta botão prazo
# Inclui análise, criação de GIGS, e ao final: minuta_apos_gigs(driver)
# Funções: processar_lista, analisar_e_criar_gigs, analisar_prazo_detalhe (antiga)

def processar_lista(driver):
    driver.get(PJE_LISTA_URL)
    registrar_url(driver.current_url)
    print("Aguardando página de lista carregar...")
    esperar_elemento(driver, 'body')

    # --- Filtro de Análise incorporado ---
    print('Iniciando filtro de análise...')
    acessar_painel_global(driver)
    time.sleep(2)  # tempo maior para garantir carregamento
    try:
        analises_cards = driver.find_elements(By.CSS_SELECTOR, 'mat-card.mat-card.painel-item-padrao')
        analise_encontrado = False
        for card in analises_cards:
            try:
                span = card.find_element(By.XPATH, './/span[contains(text(), "Análises")]')
                if span:
                    safe_click(driver, card)
                    print('Clique em "Análises" realizado (via mat-card)!')
                    analise_encontrado = True
                    time.sleep(2.5)  # aguarda tela carregar
                    break
            except Exception:
                continue
        if not analise_encontrado:
            print('mat-card com texto "Análises" não encontrado!')
    except Exception as e:
        print(f'Erro ao aplicar filtro de análise: {e}')

# Restante da função processar_lista...

# ========== FUNÇÕES AUXILIARES ==========
# Utilitários para espera, clique seguro, busca por texto, etc.

def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR):
    '''
    Espera ativo até o elemento aparecer. Se texto for fornecido, busca por texto visível.
    '''
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            if texto:
                elementos = driver.find_elements(by, seletor)
                for el in elementos:
                    if texto.strip().lower() in el.text.strip().lower():
                        return el
            else:
                el = driver.find_element(by, seletor)
                if el.is_displayed():
                    return el
        except Exception:
            pass
        time.sleep(0.2)
    print(f"Timeout esperando elemento: {seletor} ({texto if texto else ''})")
    return None

def esperar_colecao(driver, seletor, qtde_minima=1, timeout=10, by=By.CSS_SELECTOR):
    '''
    Espera até que exista uma coleção de elementos >= qtde_minima.
    '''
    end_time = time.time() + timeout
    while time.time() < end_time:
        elementos = driver.find_elements(by, seletor)
        if len(elementos) >= qtde_minima:
            return elementos
        time.sleep(0.2)
    print(f"Timeout esperando coleção: {seletor}")
    return []

def esperar_desaparecer(driver, seletor, timeout=10, by=By.CSS_SELECTOR):
    '''
    Espera até que o elemento desapareça do DOM ou fique invisível.
    '''
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            el = driver.find_element(by, seletor)
            if not el.is_displayed():
                return True
        except NoSuchElementException:
            return True
        time.sleep(0.2)
    print(f"Timeout esperando desaparecer: {seletor}")
    return False


def wait_for_visible(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
    except TimeoutException:
        print(f"Timeout esperando aparecer: {selector}")
        return None

def wait_for_disappear(driver, selector, timeout=15, by=By.CSS_SELECTOR):
    try:
        WebDriverWait(driver, timeout).until_not(
            EC.visibility_of_element_located((by, selector))
        )
        return True
    except TimeoutException:
        print(f"Timeout esperando desaparecer: {selector}")
        return False

def safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        element.click()
        return True
    except (ElementClickInterceptedException, Exception) as e:
        print(f"Erro ao clicar: {e}")
        return False

def click_element_by_visible_text(driver, texto, tag_preferida=None, timeout=10):
    """
    Clica no primeiro elemento visível que contenha o texto especificado.
    Se tag_preferida for fornecida, prioriza elementos dessa tag.
    """
    from selenium.webdriver.common.by import By
    import time
    for _ in range(timeout * 2):  # tenta por até timeout segundos
        elementos = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), '{texto}')]")
        visiveis = [el for el in elementos if el.is_displayed() and texto in el.text]
        if tag_preferida:
            visiveis = sorted(visiveis, key=lambda el: el.tag_name != tag_preferida)
        if visiveis:
            btn = visiveis[0]
            # Se não for botão, sobe até 5 níveis para achar um button
            if btn.tag_name.lower() != 'button':
                parent = btn
                for _ in range(5):
                    parent = parent.find_element(By.XPATH, '..')
                    if parent.tag_name.lower() == 'button':
                        btn = parent
                        break
            btn.click()
            print(f"[DEBUG] Clique realizado no elemento com texto visível: '{texto}'")
            return True
        time.sleep(0.5)
    raise Exception(f"Elemento com texto visível '{texto}' não encontrado ou não clicável.")

def click_button_by_text_or_aria(driver, texto, timeout=10):
    """
    Clica no primeiro <button> visível que contenha o texto ou tenha aria-label igual ao texto.
    Se não encontrar, faz log detalhado e busca profunda por estrutura, texto e atributos.
    """
    from selenium.webdriver.common.by import By
    import time
    for tent in range(timeout * 2):
        # 1. Buscar <button> por aria-label
        botoes_aria = driver.find_elements(By.CSS_SELECTOR, f'button[aria-label="{texto}"]')
        botoes_aria = [b for b in botoes_aria if b.is_displayed()]
        if botoes_aria:
            print(f"[DEBUG] Clique em <button aria-label='{texto}'> na tentativa {tent+1}")
            botoes_aria[0].click()
            time.sleep(1)
            return True
        # 2. Buscar <button> por texto visível (normalizado)
        botoes_texto = driver.find_elements(By.XPATH, f"//button[contains(normalize-space(text()), '{texto}')]")
        botoes_texto = [b for b in botoes_texto if b.is_displayed() and texto in b.text]
        if botoes_texto:
            print(f"[DEBUG] Clique em <button> com texto visível '{texto}' na tentativa {tent+1}")
            botoes_texto[0].click()
            time.sleep(1)
            return True
        time.sleep(0.5)
    # Busca profunda e log detalhado
    print(f"[ERRO] Não foi possível clicar em <button> com texto ou aria-label='{texto}'. Candidatos encontrados:")
    botoes = driver.find_elements(By.XPATH, '//button')
    for idx, b in enumerate(botoes):
        print(f"[DEBUG] <button> idx={idx}, aria-label='{b.get_attribute('aria-label')}', texto='{b.text}', visível={b.is_displayed()}, classes='{b.get_attribute('class')}'")
    # Busca outros elementos com texto semelhante
    outros = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), '{texto}')]")
    for idx, el in enumerate(outros):
        print(f"[DEBUG] [OUTRO] tag={el.tag_name}, texto='{el.text}', visível={el.is_displayed()}, classes='{el.get_attribute('class')}', id='{el.get_attribute('id')}'")
    print("[ERRO] Busca profunda finalizada. Nenhum botão clicável encontrado.")
    raise Exception(f"Nenhum <button> visível com texto ou aria-label='{texto}' encontrado.")

# ========== PLACEHOLDER: MINUTA APÓS GIGS ==========
# Função já criada: minuta_apos_gigs(driver)
# Implementar lógica conforme requisitos futuros.

def minuta_apos_gigs(driver):
    """
    Placeholder: Função para gerar minuta após GIGS.
    Implementar lógica conforme requisitos futuros.
    """
    pass

# ========== LIMPEZA TEMPORÁRIA ==========
# Função: limpar_temp_selenium

def limpar_temp_selenium():
    """
    Remove pastas webdriver-py-profilecopy e arquivos temporários antigos do Selenium no diretório TEMP.
    """
    temp_dir = tempfile.gettempdir()
    for nome in os.listdir(temp_dir):
        if nome.startswith('tmp') or nome.startswith('webdriver-py-profilecopy'):
            caminho = os.path.join(temp_dir, nome)
            try:
                if os.path.isdir(caminho):
                    shutil.rmtree(caminho, ignore_errors=True)
                else:
                    os.remove(caminho)
                print(f'[LIMPEZA TEMP] Removido: {caminho}')
            except Exception as e:
                print(f'[LIMPEZA TEMP][ERRO] Falha ao remover {caminho}: {e}')

def registrar_url(url):
    print(f'[URL_ACESSADA] {url}')

# Funções auxiliares para fluxo Mandados - Hipótese 1
def buscar_documentos_sequenciais(driver):
    """
    Busca documentos relevantes na timeline do PJe na ordem especificada.
    Loga o nome de cada documento encontrado na ordem correta.
    Retorna lista de elementos Selenium dos documentos encontrados.
    """
    from selenium.webdriver.common.by import By
    import re
    import time

    documentos_alvo = [
        "Certidão de devolução",
        "Certidão de expedição",
        "Planilha",
        "Intimação",
        "Decisão"
    ]
    resultados = []
    elementos = driver.find_elements(By.CSS_SELECTOR, ".tl-data, li.tl-item-container")
    indice_doc_atual = 0
    for elemento in elementos:
        if indice_doc_atual >= len(documentos_alvo):
            break
        texto_item = elemento.text.strip().lower()
        documento_atual = documentos_alvo[indice_doc_atual]
        if documento_atual.lower() in texto_item:
            print(f"[ENCONTRADO] {documento_atual}")
            resultados.append(elemento)
            indice_doc_atual += 1
    return resultados

def retirar_sigilo(elemento):
    try:
        btn_sigilo = elemento.find_element(By.CSS_SELECTOR, "pje-doc-sigiloso span button i.fa-wpexplorer")
        
        # Verifica se o ícone está vermelho (com sigilo ativo) através da classe tl-sigiloso
        if "tl-sigiloso" in btn_sigilo.get_attribute("class"):
            btn_sigilo.click()
            time.sleep(1)
            print("[SIGILO] Clique para retirar sigilo realizado (ícone estava vermelho).")
        else:
            print("[SIGILO] Ícone está azul (sem sigilo ativo). Não é necessário clicar.")
    except Exception as e:
        print("[SIGILO] Erro ao retirar sigilo (pode já estar sem sigilo):", e)

def tratar_anexos_certidao(certidao, driver):
    """
    Para cada anexo da certidão de devolução:
    - Se for INFOJUD, IRPF ou DOI no texto, executa a sequência:
      1. Clica no anexo para abrir.
      2. Clica no botão de sigilo (fa-wpexplorer).
      3. Clica no botão de visibilidade (fa-plus).
      4. No modal (.mat-dialog-content), clica em i.botao-icone-titulo-coluna.
      5. Clica em Salvar (.mat-dialog-actions > button:nth-child(1) > span:nth-child(1)).
      6. Fecha o diálogo com ESC.
    - Se for SISBAJUD com POSITIVO/PARCIAL/INTEGRAL, registra bloqueio.
    - Outros: ignorado.
    Retorna True se algum bloqueio SISBAJUD for encontrado.
    """
    from selenium.webdriver.common.keys import Keys
    bloqueio_registrado = False
    try:
        # Busca apenas anexos da certidão de devolução (não timeline geral)
        # Normalmente estão em <div> ou <li> dentro do próprio elemento certidao, com texto 'Anexo(s):'
        texto_certidao = certidao.text
        anexos = []
        if 'Anexo(s):' in texto_certidao:
            linhas = texto_certidao.split('\n')
            try:
                idx = linhas.index(next(l for l in linhas if 'Anexo(s):' in l))
                # Os anexos costumam estar nas próximas linhas até acabar ou vir linha vazia
                for l in linhas[idx+1:]:
                    if not l.strip():
                        break
                    anexos.append(l.strip())
            except Exception as e:
                print(f"[ANEXOS][ERRO] Falha ao identificar linhas de anexos: {e}")
        print(f"[ANEXOS][DETALHE] {len(anexos)} anexos detectados na certidão de devolução.")
        for idx, texto in enumerate(anexos):
            print(f"[ANEXOS][{idx+1}/{len(anexos)}] Conteúdo: '{texto}'")
            texto_lower = texto.lower()
            if any(p in texto_lower for p in ["infojud", "irpf", "doi"]):
                print(f"[ANEXOS][{idx+1}] Tipo reconhecido (INFOJUD/IRPF/DOI). Inserindo sigilo e visibilidade...")
                try:
                    # Tenta clicar no strong correspondente ao texto do anexo
                    strongs = certidao.find_elements(By.TAG_NAME, 'strong')
                    alvo = None
                    for s in strongs:
                        if s.text.strip() in texto:
                            alvo = s
                            break
                    if alvo:
                        alvo.click()
                        time.sleep(0.7)
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
                            print(f"[ANEXOS][{idx+1}] Sigilo e visibilidade aplicados com sucesso no anexo '{texto}'.")
                            modal_contexto.send_keys(Keys.ESCAPE)
                            print("[MODAL] Fechado com ESC.")
                            time.sleep(1)
                        else:
                            print(f"[ANEXOS][{idx+1}] Botão de visibilidade não visível para o anexo '{texto}'.")
                    else:
                        print(f"[ANEXOS][{idx+1}] Não foi possível localizar o elemento visual do anexo '{texto}'.")
                except Exception as e:
                    print(f"[ERRO] Ao inserir sigilo/visibilidade em anexo '{texto}': {e}")
            elif "sisbajud" in texto_lower and any(p in texto_lower for p in ["positivo", "parcial", "integral"]):
                print(f"[REGISTRO BLOQUEIO] SISBAJUD encontrado: {texto}. Bloqueio POSITIVO registrado.")
                bloqueio_registrado = True
            else:
                print(f"[ANEXOS][{idx+1}] Tipo não tratado/ignorado: '{texto}'. Nenhuma ação realizada.")
    except Exception as e:
        print(f"[ANEXOS][ERRO] Falha ao localizar ou processar anexos da certidão: {e}")
        return False
    return bloqueio_registrado

def tratar_sigilo_documentos_relevantes(documentos):
    nomes = ["Certidão de expedição", "Planilha", "Intimação", "Decisão"]
    for doc, nome in zip(documentos[1:], nomes):
        print(f"[TRATAR] {nome}")
        retirar_sigilo(doc)
        time.sleep(0.5)

def tratar_prazo_intimacao(driver, elemento_intimacao):
    try:
        print("[DEBUG][INTIMACAO] Buscando envelope...")
        btn_envelope = elemento_intimacao.find_element(By.CSS_SELECTOR, "i.fa-envelope.fa-lg.icone-cinza")
        btn_envelope.click()
        print("[DEBUG][INTIMACAO] Envelope clicado. Aguardando modal...")
        time.sleep(1)
        modal = driver.find_element(By.CSS_SELECTOR, ".flex-container-raiz, .mat-dialog-container")
        print("[DEBUG][INTIMACAO] Modal encontrado. Procurando checkbox...")
        try:
            checkbox = modal.find_element(By.CSS_SELECTOR, ".mat-checkbox-inner-container-no-side-margin")
            checkbox.click()
            print("[DEBUG][INTIMACAO] Checkbox marcada. Procurando botão OK...")
            time.sleep(1)
            btn_confirmar = modal.find_element(By.CSS_SELECTOR, ".mat-raised-button > span:nth-child(1)")
            btn_confirmar.click()
            print("[DEBUG][INTIMACAO] Botão OK clicado. Procurando botão SIM...")
            time.sleep(1)
            # Novo: procurar botão SIM em novo dialog
            modal_confirm = driver.find_element(By.CSS_SELECTOR, ".mat-dialog-container")
            btn_sim = None
            for btn in modal_confirm.find_elements(By.TAG_NAME, "button"):
                if "sim" in btn.text.strip().lower():
                    btn_sim = btn
                    break
            if btn_sim:
                btn_sim.click()
                print("[DEBUG][INTIMACAO] Botão SIM clicado. Intimação tratada com sucesso.")
            else:
                print("[DEBUG][INTIMACAO] Botão SIM não encontrado após OK.")
        except Exception as e:
            print(f"[DEBUG][INTIMACAO] Checkbox não encontrada ou erro: {e}. Fechando modal com ESC.")
            from selenium.webdriver.common.keys import Keys
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            time.sleep(1)
    except Exception as e:
        print(f"[DEBUG][INTIMACAO] Erro ao tratar prazo de intimação: {e}")

def processar_bloqueio(driver):
    print("[PROCESSAR BLOQUEIO] Função placeholder chamada.")

def fallback_bloqueio_pdf(driver):
    try:
        obj_pdf = driver.find_element(By.CSS_SELECTOR, "object.conteudo-pdf")
        driver.execute_script("arguments[0].scrollIntoView(true);", obj_pdf)
        print("[FALLBACK] Leitura de PDF para SISBAJUD não implementada.")
    except Exception as e:
        print("Erro ao executar fallback bloqueio-pdf:", e)

def fluxo_mandados_hipotese1(driver):
    """
    Fluxo completo de automação de mandados, executando etapas na ordem correta:
    1. Confirmar certidão de devolução
    2. Buscar documentos na ordem correta na timeline (buscar_documentos_sequenciais)
    3. Retirar sigilo da Certidão de Devolução
    4. Clicar e tratar anexos
      4a. Registrar se houver bloqueio (função SISBAJUD anexo)
    5. Retirar sigilo dos documentos seguintes
    6. Tratar intimação
    7. Processar bloqueio se positivo (4a)
      7b. Fallback leitura de PDF e processar sigilo
    8. Processar bloqueio conforme resultado
    """
    # 1. Confirmar certidão de devolução (AQUI deve estar a lógica de confirmação, se aplicável)
    # Exemplo: confirmar_certidao_de_devolucao(driver)  # <-- Se houver função específica
    print("[MANDADOS][CONFIRMAÇÃO] Certidão de devolução confirmada (ajuste aqui se necessário).")

    # 2. Buscar documentos relevantes na timeline (apenas após confirmação)
    print("[MANDADOS][BUSCA] Buscando documentos sequenciais APÓS confirmação da certidão de devolução...")
    documentos = buscar_documentos_sequenciais(driver)
    if not documentos or len(documentos) == 0:
        return
    doc_principal = documentos[0]
    texto_principal = doc_principal.text.strip().lower()
    if "certidão de devolução" not in texto_principal:
        print(f"[MANDADOS] Documento principal ('{texto_principal}') não é Certidão de Devolução!")
        return
    print("[MANDADOS] Extraindo conteúdo da Certidão de Devolução...")
    conteudo = extrair_conteudo_documento(driver, doc_principal)
    if not conteudo:
        print("[MANDADOS][ERRO] Falha ao extrair o conteúdo da certidão.")
        return
    print("[MANDADOS] Analisando conteúdo para cumprimento positivo...")
    if analisar_andamento_mandado_positivo(conteudo):
        print("[MANDADOS] Mandado POSITIVO identificado. Criando atividade .silas...")
        criar_gig_atividade(driver, prazo=0, observacao='Silas teste')
    else:
        print("[MANDADOS] Mandado POSITIVO NÃO identificado. Nenhuma atividade criada.")

# Função de criação de GIG/atividade .silas
def criar_gig_atividade(driver, prazo, observacao):
    """
    Cria uma atividade GIGS (.silas) no PJe:
    1. Clica no botão de adicionar atividade.
    2. Seleciona tipo .silas.
    3. Preenche prazo e observação.
    4. Salva a atividade.
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        # 1. Clicar no botão de adicionar atividade
        try:
            btn_add = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Adicionar atividade"]')
        except NoSuchElementException:
            try:
                btn_add = driver.find_element(By.CSS_SELECTOR, '#nova-atividade > span:nth-child(1) > span:nth-child(2)')
            except NoSuchElementException:
                print('[GIGS][ERRO] Botão de adicionar atividade não encontrado com nenhum seletor!')
                driver.save_screenshot('screenshot_gigs_btn_add_fail.png')
                return False
        btn_add.click()
        print("[GIGS] Botão 'Adicionar atividade' clicado.")
        time.sleep(1)

        # 2. Selecionar tipo de atividade .silas
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[formcontrolname="tipoAtividade"]')
        except NoSuchElementException:
            print('[GIGS][ERRO] Campo tipo de atividade não encontrado!')
            driver.save_screenshot('screenshot_gigs_tipo_atividade_fail.png')
            return False
        campo_tipo.click()
        time.sleep(0.5)
        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
        silas_opcao = None
        for opcao in opcoes:
            if ".silas" in opcao.text.lower():
                silas_opcao = opcao
                break
        if silas_opcao:
            silas_opcao.click()
            print("[GIGS] Tipo de atividade .silas selecionado.")
        else:
            print('[GIGS][ERRO] Opção .silas não encontrada!')
            driver.save_screenshot('screenshot_gigs_opcao_silas_fail.png')
            return False
        time.sleep(0.5)

        # 3. Preencher prazo
        try:
            campo_prazo = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="prazo"]')
        except NoSuchElementException:
            print('[GIGS][ERRO] Campo prazo não encontrado!')
            driver.save_screenshot('screenshot_gigs_prazo_fail.png')
            return False
        campo_prazo.clear()
        campo_prazo.send_keys(str(prazo))
        print(f"[GIGS] Prazo preenchido: {prazo}")
        time.sleep(0.5)

        # 4. Preencher observação
        try:
            campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
        except NoSuchElementException:
            print('[GIGS][ERRO] Campo observação não encontrado!')
            driver.save_screenshot('screenshot_gigs_obs_fail.png')
            return False
        campo_obs.clear()
        campo_obs.send_keys(observacao)
        print(f"[GIGS] Observação preenchida: {observacao}")
        time.sleep(0.5)

        # 5. Salvar atividade
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"] span')
        except NoSuchElementException:
            print('[GIGS][ERRO] Botão salvar não encontrado!')
            driver.save_screenshot('screenshot_gigs_salvar_fail.png')
            return False
        btn_salvar.click()
        print("[GIGS] Atividade .silas criada e salva com sucesso!")
        time.sleep(1)
        return True
    except Exception as e:
        print(f"[GIGS][ERRO] Falha ao criar atividade .silas: {e}")
        driver.save_screenshot('screenshot_gigs_falha_geral.png')
        return False

def criar_gig_atividade_geral(driver, tipo_gig, dias_uteis, observacao):
    """
    Cria uma atividade GIGS (tipo_gig: '.silas', 'Prazo', etc) no PJe TRT2.
    - Abre o diálogo de nova atividade
    - Seleciona o tipo, se necessário
    - Preenche dias úteis e observação
    - Salva
    """
    from selenium.common.exceptions import NoSuchElementException
    import time
    try:
        # 1. Abrir diálogo Nova Atividade
        btn_nova = None
        try:
            btn_nova = driver.find_element(By.ID, 'nova-atividade')
        except NoSuchElementException:
            # Busca alternativa por texto
            spans = driver.find_elements(By.XPATH, "//span[text()='Nova atividade']")
            for sp in spans:
                if sp.is_displayed():
                    btn_nova = sp.find_element(By.XPATH, '../../..') # Sobe até o botão
                    break
        if not btn_nova:
            print('[GIGS][ERRO] Botão Nova atividade não encontrado!')
            return False
        safe_click(driver, btn_nova)
        print('[GIGS] Botão Nova atividade clicado.')
        time.sleep(1.2)

        # 2. Selecionar tipo (se necessário)
        if tipo_gig:
            try:
                campo_tipo = driver.find_element(By.ID, 'mat-input-11')
                safe_click(driver, campo_tipo)
                time.sleep(0.5)
                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option > span')
                selecionado = False
                for opcao in opcoes:
                    if tipo_gig.lower() in opcao.text.lower():
                        safe_click(driver, opcao)
                        print(f'[GIGS] Tipo de atividade selecionado: {opcao.text}')
                        selecionado = True
                        break
                if not selecionado:
                    print(f'[GIGS][ERRO] Tipo de atividade "{tipo_gig}" não encontrado!')
                    return False
                time.sleep(0.5)
            except Exception as e:
                print(f'[GIGS][ERRO] Falha ao selecionar tipo: {e}')
                return False

        # 3. Preencher Dias Úteis
        try:
            campo_dias = driver.find_element(By.ID, 'mat-input-15')
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))
            print(f'[GIGS] Dias úteis preenchido: {dias_uteis}')
        except Exception as e:
            print(f'[GIGS][ERRO] Falha ao preencher dias úteis: {e}')
            return False
        time.sleep(0.4)

        # 4. Preencher Observação
        try:
            campo_obs = driver.find_element(By.ID, 'mat-input-13')
            campo_obs.clear()
            campo_obs.send_keys(observacao)
            print(f'[GIGS] Observação preenchida: {observacao}')
        except Exception as e:
            print(f'[GIGS][ERRO] Falha ao preencher observação: {e}')
            return False
        time.sleep(0.4)

        # 5. Clicar em Salvar
        try:
            btns_salvar = driver.find_elements(By.XPATH, "//button[.//span[contains(text(),'Salvar')]]")
            btn_salvar = None
            for btn in btns_salvar:
                if btn.is_displayed():
                    btn_salvar = btn
                    break
            if not btn_salvar:
                print('[GIGS][ERRO] Botão Salvar não encontrado!')
                return False
            safe_click(driver, btn_salvar)
            print('[GIGS] Atividade salva com sucesso!')
        except Exception as e:
            print(f'[GIGS][ERRO] Falha ao clicar em Salvar: {e}')
            return False
        time.sleep(1)
        return True
    except Exception as e:
        print(f'[GIGS][ERRO] Falha geral: {e}')
        return False

def injetar_botao_teste_gigs(driver):
    """
    Injeta um botão flutuante 'TESTE GIGS' em qualquer página /detalhe do PJe.
    Ao clicar, executa criar_gig_atividade(driver, prazo=0, observacao='Silas teste').
    """
    import re
    import time
    if re.search(r"/detalhe/.*", driver.current_url):
        try:
            # Evita múltiplos botões
            if driver.execute_script("return document.getElementById('btnTesteGigs') !== null"):
                return
            script = '''
            (function() {
                var btn = document.createElement('button');
                btn.id = 'btnTesteGigs';
                btn.textContent = 'TESTE GIGS';
                btn.style.backgroundColor = '#1976d2';
                btn.style.color = 'white';
                btn.style.border = 'none';
                btn.style.borderRadius = '7px';
                btn.style.cursor = 'pointer';
                btn.style.fontWeight = 'bold';
                btn.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
                btn.style.padding = '10px 18px';
                btn.style.position = 'fixed';
                btn.style.bottom = '30px';
                btn.style.right = '30px';
                btn.style.zIndex = '9999';
                btn.onclick = function() { window.dispatchEvent(new CustomEvent('botaoTesteGigsClicadoSelenium')); };
                document.body.appendChild(btn);
            })();
            '''
            driver.execute_script(script)
            driver.execute_script('''
                window._seleniumTesteGigsListenerAdded = window._seleniumTesteGigsListenerAdded || false;
                if (!window._seleniumTesteGigsListenerAdded) {
                    window.addEventListener('botaoTesteGigsClicadoSelenium', () => {
                        document.title = '[GIGS_TESTE_CLICADO]';
                    });
                    window._seleniumTesteGigsListenerAdded = true;
                }
            ''')
            print('[INJETOR] Botão TESTE GIGS injetado na página.')
        except Exception as e:
            print(f'[INJETOR][ERRO] Falha ao injetar botão TESTE GIGS: {e}')

def extrair_documento(driver, regras_analise=None, timeout=15):
    """
    Aguarda o carregamento do documento, clica no ícone HTML (.fa-file-code),
    extrai o texto do preview (#previewModeloDocumento),
    analisa o texto conforme callback (regras_analise, se fornecida)
    e fecha a janela HTML pressionando ESC.
    Retorna o texto extraído e o resultado da análise (se houver).
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    texto = ''
    resultado_analise = None
    try:
        # 1. Aguarda ícone HTML aparecer
        for _ in range(timeout * 2):
            try:
                btn_html = driver.find_element(By.CSS_SELECTOR, '.fa-file-code')
                if btn_html.is_displayed():
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            print('[extrair_documento] Ícone HTML (.fa-file-code) não apareceu após abrir documento.')
            return '', None
        print('[extrair_documento] Clicando no ícone HTML...')
        btn_html.click()
        # 2. Aguarda preview carregar e extrai texto
        for _ in range(timeout * 2):
            try:
                preview = driver.find_element(By.CSS_SELECTOR, '#previewModeloDocumento')
                if preview.is_displayed() and preview.text.strip():
                    texto = preview.text.strip()
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not texto:
            print('[extrair_documento] Não foi possível extrair o texto do preview HTML.')
            return '', None
        print('[extrair_documento] Texto extraído do preview HTML.')
        # 3. Analisa o texto conforme regras (callback)
        if regras_analise:
            resultado_analise = regras_analise(texto)
        # 4. Fecha janela HTML pressionando ESC
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        print('[extrair_documento] Janela HTML fechada com ESC.')
        time.sleep(1)
        return texto, resultado_analise
    except Exception as e:
        print(f'[extrair_documento][ERRO] {e}')
        return '', None

def fluxo_mandados_hipotese2(driver):
    """
    Fluxo Mandado 2 - Outros
    Sempre executa a extração da certidão via extrair_documento e, em seguida, analisa conforme a tarefa.
    """
    print("[MANDADOS][OUTROS] Iniciando fluxo Mandado 2 - Outros")
    from selenium.webdriver.common.keys import Keys
    # Exemplo de callback de análise (pode ser substituído por lógica específica da tarefa)
    def analise_padrao(texto):
        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
        texto_lower = texto.lower()
        padrao_oficial = "certidão de oficial" in texto_lower
        padrao_positivo = any(p in texto_lower for p in ["citei", "intimei", "recebeu o mandado", "de tudo ficou ciente"])
        padrao_negativo = any(p in texto_lower for p in [
            "não localizado", "negativo", "não encontrado",
            "deixei de citar", "deixei de efetuar", "não logrei êxito", "desconhecido no local"
        ])
        if padrao_oficial:
            print("[MANDADOS][OUTROS][LOG] Padrão 'certidão de oficial' ENCONTRADO no texto.")
            if padrao_positivo:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd positivo')
            elif padrao_negativo:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd negativo')
            else:
                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Nenhum padrão positivo/negativo detectado. Criando GIGS fallback.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd sem padrão')
        else:
            print("[MANDADOS][OUTROS][LOG] Documento NÃO é certidão de oficial. Nenhum padrão reconhecido. Criando GIGS fallback.")
            criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd sem padrão')
        return None  # ou algum resultado útil

    texto, resultado = extrair_documento(driver, regras_analise=analise_padrao)
    if not texto:
        print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
    # Fechar aba após análise e ação
    try:
        driver.close()
        print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
    except Exception as e:
        print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
    print("[MANDADOS][OUTROS] Fluxo Mandado 2 concluído.")

def fluxo_mandados_hipotese2_caso1_encaminhado(driver):
    """
    Caso 1 - Encaminhado: Verifica Certidão de Oficial e presença do ícone de atividade para gerar Gigs.
    """
    print("[MANDADOS][OUTROS][CASO 1] Iniciando análise de Certidão de Oficial - Encaminhado")
    def analise_encaminhado(texto):
        from selenium.webdriver.common.by import By
        # Confirma se o texto extraído é de Certidão de Oficial
        if "certidão de oficial" not in texto.lower():
            print("[MANDADOS][OUTROS][CASO 1] Documento não é Certidão de Oficial.")
            return False
        print("[MANDADOS][OUTROS][CASO 1] Certidão de Oficial confirmada.")
        # Verifica presença do ícone de tipo de atividade
        try:
            icone = driver.find_element(By.CSS_SELECTOR, '.icone-tipo-atividade')
            if icone.is_displayed():
                print("[MANDADOS][OUTROS][CASO 1] Ícone de tipo de atividade encontrado.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Encaminhado')
                print("[MANDADOS][OUTROS][CASO 1] Gigs gerado: Atividade .Silas Verificar prazo 0 (Encaminhado)")
                return True
            else:
                print("[MANDADOS][OUTROS][CASO 1] Ícone de tipo de atividade não visível.")
                return False
        except Exception:
            print("[MANDADOS][OUTROS][CASO 1] Ícone de tipo de atividade não encontrado.")
            return False
    texto, _ = extrair_documento(driver, regras_analise=analise_encaminhado)
    if not texto:
        print("[MANDADOS][OUTROS][CASO 1][ERRO] Não foi possível extrair o texto da certidão.")

def fluxo_mandados_hipotese2_caso2_positivo(driver):
    """
    Caso 2 - Positivo: Verifica Certidão de Oficial positiva e gera Gigs se encontrar palavras-chave.
    """
    print("[MANDADOS][OUTROS][CASO 2] Iniciando análise de Certidão de Oficial - Positivo")
    def analise_positivo(texto):
        # Confirma se o texto extraído é de Certidão de Oficial
        if "certidão de oficial" not in texto.lower():
            print("[MANDADOS][OUTROS][CASO 2] Documento não é Certidão de Oficial.")
            return False
        print("[MANDADOS][OUTROS][CASO 2] Certidão de Oficial confirmada.")
        # Palavras-chave de mandado positivo
        palavras_chave = [
            'citei',
            'intimei',
            'dei ciência',
            'recebeu o mandado',
            'de tudo ficou ciente'
        ]
        if any(p in texto.lower() for p in palavras_chave):
            criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd positivo')
            print("[MANDADOS][OUTROS][CASO 2] Gigs gerado: Tipo .Silas, Prazo 0, Observação - Mdd positivo")
            return True
        else:
            print("[MANDADOS][OUTROS][CASO 2] Mandado não é positivo.")
            return False
    texto, _ = extrair_documento(driver, regras_analise=analise_positivo)
    if not texto:
        print("[MANDADOS][OUTROS][CASO 2][ERRO] Não foi possível extrair o texto da certidão.")

def expandir_e_listar_anexos(driver):
    from selenium.webdriver.common.by import By
    import time

    print("[DEBUG] Procurando container de anexos via .header-documento...")
    try:
        container = driver.find_element(By.CSS_SELECTOR, ".header-documento[role='button'][name='mostrarOuOcultarAnexos']")
        print("[DEBUG] Container de anexos encontrado. Tentando clicar para expandir...")
        container.click()
        time.sleep(1)
    except Exception as e:
        print(f"[ERRO] Não encontrou/clicou container de anexos: {e}")
        return False

    anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
    print(f"[DEBUG] Total de anexos encontrados após expandir: {len(anexos)}")
    for idx, anexo in enumerate(anexos):
        print(f"[DEBUG][ANEXO {idx+1}] Texto: {anexo.text.strip()}")
    return anexos

def clicar_botao_confirmar_intimacao(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    try:
        print('[DEBUG] Aguardando caixa de confirmação de intimação aparecer (#mat-dialog-6)...')
        dialog = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#mat-dialog-6'))
        )
        print('[DEBUG] Caixa de confirmação visível. Buscando botão de confirmação...')
        btn_sim = dialog.find_element(By.CSS_SELECTOR, '.mat-dialog-actions > button:nth-child(1)')
        btn_sim_text = btn_sim.text.strip()
        print(f'[DEBUG] Botão encontrado. Texto: {btn_sim_text}. Tentando clicar...')
        btn_sim.click()
        print('[DEBUG] Clique no botão de confirmação realizado.')
        time.sleep(1)
        return True
    except Exception as e:
        print(f'[ERRO] Falha ao clicar no botão de confirmação da intimação: {e}')
        return False

if __name__ == "__main__":
    main()
