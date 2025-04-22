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
import pyperclip
import re

# ========== CONFIGURAÇÕES ==========
PJE_LISTA_URL = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
PJE_DETALHE_REGEX = r"/processo/.+/detalhe"

# ========== UTILITÁRIOS ==========
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

def aguardar_carregamento_pje(driver, timeout=10):
    '''
    Monitora o spinner ou status do PJe, esperando desaparecer.
    '''
    spinner_sel = 'PJE-DIALOGO-STATUS-PROGRESSO, #maisPJe_mensagem_fundo'
    esperar_elemento(driver, spinner_sel, timeout=2)
    esperar_desaparecer(driver, spinner_sel, timeout=timeout)

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

# ========== ESTÁGIO 1: LISTA DE PROCESSOS ==========
def processar_lista(driver):
    driver.get(PJE_LISTA_URL)
    print("Aguardando página de lista carregar...")
    esperar_elemento(driver, 'body')

    # Tenta clicar no filtro MID1
    filtro_mid1 = None
    try:
        filtro_mid1 = driver.find_element(By.CSS_SELECTOR, '#maisPje_filtrofavorito_Mid1 > span:nth-child(1)')
        safe_click(driver, filtro_mid1)
        print('Filtro MID1 clicado diretamente.')
    except NoSuchElementException:
        print('Filtro MID1 não encontrado, executando fallback...')
        try:
            laptop_btn = driver.find_element(By.CSS_SELECTOR, '.fa-laptop')
            safe_click(driver, laptop_btn)
            time.sleep(1)
            painel_item = driver.find_element(By.CSS_SELECTOR, 'pje-painel-item.item-painel:nth-child(4) > div:nth-child(1) > mat-card:nth-child(2) > mat-card-title:nth-child(1) > span:nth-child(2)')
            safe_click(driver, painel_item)
            time.sleep(1)
            filtro_mid1_fallback = None
            try:
                filtro_mid1_fallback = driver.find_element(By.CSS_SELECTOR, '#maisPJe_filtrofavorito_Mid1')
            except NoSuchElementException:
                try:
                    filtro_mid1_fallback = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="MID1"]')
                except NoSuchElementException:
                    buttons = driver.find_elements(By.CSS_SELECTOR, 'button')
                    for b in buttons:
                        if 'MID1' in b.text:
                            filtro_mid1_fallback = b
                            break
            if filtro_mid1_fallback:
                safe_click(driver, filtro_mid1_fallback)
                print('Filtro MID1 clicado via fallback.')
            else:
                print('Filtro MID1 não encontrado mesmo após fallback.')
        except NoSuchElementException:
            print('Fallback para filtro MID1 falhou.')

    # Aguarda carregamento
    aguardar_carregamento_pje(driver, 5)
    time.sleep(2)

    # Seleciona processos válidos
    rows = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    selecionado = False
    for row in rows:
        try:
            time_cell = row.find_element(By.CSS_SELECTOR, 'td:nth-child(9) time')
            no_deadline = time_cell.text.strip() == ''
        except NoSuchElementException:
            no_deadline = True
        has_comment = len(row.find_elements(By.CSS_SELECTOR, 'i.fa-comment')) > 0
        try:
            input_field = row.find_element(By.CSS_SELECTOR, 'input[matinput]')
            has_input_value = input_field.get_attribute('value').strip() != ''
        except NoSuchElementException:
            has_input_value = False
        has_search_icon = len(row.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')) > 0
        if no_deadline and not has_comment and not has_input_value and not has_search_icon:
            try:
                checkbox = row.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type=checkbox]')
                if not checkbox.is_selected():
                    safe_click(driver, checkbox)
                driver.execute_script("arguments[0].style.backgroundColor = '#ffffaa';", row)
                time.sleep(0.5)
                btn_detalhes = None
                try:
                    btn_detalhes = row.find_element(By.CSS_SELECTOR, 'button[aria-label="Detalhes do Processo"], button[mattooltip="Detalhes do Processo"]')
                except NoSuchElementException:
                    try:
                        btn_detalhes = row.find_element(By.CSS_SELECTOR, 'button')
                    except NoSuchElementException:
                        pass
                if btn_detalhes:
                    safe_click(driver, btn_detalhes)
                    selecionado = True
                    break
            except Exception as e:
                print(f"Erro ao selecionar processo: {e}")
    if not selecionado:
        print('Nenhum processo válido encontrado para análise.')
        return False
    return True

# ========== ESTÁGIO 2: DETALHE DO PROCESSO ==========
def processar_detalhe(driver):
    print('Aguardando carregamento completo da página de detalhes...')
    esperar_elemento(driver, '#novo-comentario', 20)
    time.sleep(2)

    # Botão Prazo
    print('Executando processamento de prazo...')
    # Remove chips
    try:
        remove_chips_btn = driver.find_element(By.CSS_SELECTOR, '[id*="remover-chips"]')
        safe_click(driver, remove_chips_btn)
        time.sleep(2.5)
    except NoSuchElementException:
        pass

    # Clica no botão Analisar
    if not acionar_botao_pje(driver, 'gigs', 'Analisar'):
        print('Falha ao clicar no botão Analisar')
        return False

    aguardar_carregamento_pje(driver, 15)
    time.sleep(2)

    # Seleciona decisão e extrai conteúdo
    content = select_decision_and_extract(driver)
    if not content:
        print('Não foi possível extrair o conteúdo do documento')
        acionar_botao_pje(driver, 'gigs', 'Sconf')
        return False

    # Análise e avanço
    analyze_and_advance(driver, content)
    print('Prazo processado com sucesso.')
    # Fecha modal/minuta
    try:
        btn_fechar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Fechar"]')
        safe_click(driver, btn_fechar)
        time.sleep(1.5)
    except NoSuchElementException:
        pass
    return True

# ========== FUNÇÕES AUXILIARES ==========
def acionar_botao_pje(driver, grupo, botao_texto):
    print(f"Acionando botão '{botao_texto}' no grupo '{grupo}'...")
    try:
        icone = driver.find_element(By.CSS_SELECTOR, f"#maisPJe_bt_detalhes_{grupo}")
        webdriver.ActionChains(driver).move_to_element(icone).perform()
        time.sleep(1.5)
        botoes = driver.find_elements(By.CSS_SELECTOR, 'button')
        for btn in botoes:
            if btn.is_displayed() and btn.text.strip() == botao_texto:
                safe_click(driver, btn)
                aguardar_carregamento_pje(driver, 15)
                time.sleep(2)
                print(f"Botão '{botao_texto}' acionado com sucesso.")
                return True
        print(f"Botão '{botao_texto}' não encontrado no grupo '{grupo}'")
    except Exception as e:
        print(f"Erro ao acionar botão: {e}")
    return False

def select_decision_and_extract(driver):
    try:
        items = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        doc_item = None
        for item in items:
            try:
                doc_link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = doc_link.text.lower()
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
                    doc_item = item
                    doc_link = doc_link
                    break
            except NoSuchElementException:
                continue
        if not doc_item or not doc_link:
            print('Documento não encontrado')
            return None
        doc_link.click()
        aguardar_carregamento_pje(driver, 15)
        time.sleep(2)
        try:
            content = driver.find_element(By.CSS_SELECTOR, '.conteudo-html').text
        except NoSuchElementException:
            print('Conteúdo HTML não encontrado, tentando visualizar código...')
            try:
                code_icon = driver.find_element(By.CSS_SELECTOR, '.fa-file-code')
                safe_click(driver, code_icon)
                preview = esperar_elemento(driver, '#previewModeloDocumento', 5)
                content = preview.text if preview else ''
                close_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Fechar"]')
                safe_click(driver, close_btn)
                time.sleep(1)
            except NoSuchElementException:
                content = ''
        if not content:
            print('Não foi possível extrair o conteúdo do documento')
            acionar_botao_pje(driver, 'gigs', 'Sconf')
            return None
        return content.lower()
    except Exception as e:
        print(f"Erro ao extrair conteúdo: {e}")
        return None

def analyze_and_advance(driver, content):
    regras = [
        (re.compile(r'concede-se 05 dias|visibilidade.*advogados|início da fluência|indicar meios|oito dias para apresentação'), 'gigs', 'ConfG'),
        (re.compile(r'revel|concorda com homologação'), 'gigs', 'Homol'),
        (re.compile(r'hasta|saldo devedor|prescrição'), 'gigs', 'Pec'),
        (re.compile(r'impugnações apresentadas'), 'gigs', 'Pesq'),
        (re.compile(r'cumprido o acordo homologado'), 'movimentar', 'Arq'),
        (re.compile(r'unicamente previdenciário'), 'concluso', 'suspinss')
    ]
    for regex, grupo, botao in regras:
        if regex.search(content):
            acionar_botao_pje(driver, grupo, botao)
            return
    acionar_botao_pje(driver, 'gigs', 'Sconf')

# ========== NOVO FLUXO ==========
def acessar_painel_global(driver):
    print('Acessando painel global (ícone laptop)...')
    # Aguarda e clica no ícone laptop
    laptop_btn = esperar_elemento(driver, '.fa-laptop', timeout=15)
    if laptop_btn:
        safe_click(driver, laptop_btn)
        time.sleep(2)
    else:
        print('Ícone laptop não encontrado!')
        return False
    return True

def acessar_prazos_vencidos(driver):
    print('Clicando em "Prazos Vencidos"...')
    # Usa o seletor CSS e XPath exatos fornecidos pelo usuário
    seletor_css = 'html > body > pje-root > mat-sidenav-container > mat-sidenav-content > div > div > pje-painel-global > div:nth-of-type(1) > pje-painel-item:nth-of-type(1) > div > mat-card > mat-card-title > span'
    xpath = '/html/body/PJE-ROOT[1]/MAT-SIDENAV-CONTAINER[1]/MAT-SIDENAV-CONTENT[1]/DIV[1]/DIV[1]/PJE-PAINEL-GLOBAL[1]/DIV[2]/PJE-PAINEL-ITEM[14]/DIV[1]/MAT-CARD[1]/MAT-CARD-TITLE[1]/SPAN[2]'
    try:
        # Tenta primeiro pelo CSS Selector
        prazos_btn = None
        try:
            prazos_btn = driver.find_element(By.CSS_SELECTOR, seletor_css)
            if prazos_btn and prazos_btn.is_displayed():
                safe_click(driver, prazos_btn)
                time.sleep(2)
                print('Clique em "Prazos Vencidos" realizado via CSS Selector!')
                return True
        except Exception:
            pass
        # Tenta pelo XPath
        try:
            prazos_btn = driver.find_element(By.XPATH, xpath)
            if prazos_btn and prazos_btn.is_displayed():
                safe_click(driver, prazos_btn)
                time.sleep(2)
                print('Clique em "Prazos Vencidos" realizado via XPath!')
                return True
        except Exception:
            pass
        print('Elemento "Prazos Vencidos" não encontrado pelo seletor fornecido!')
        return False
    except Exception as e:
        print(f'Erro ao clicar em "Prazos Vencidos": {e}')
        return False

def filtrar_fase_processual(driver):
    print('Filtrando fase processual: Liquidação e Execução...')
    # Procura filtro de fase processual (input ou select)
    # Tenta localizar por label ou placeholder
    filtro = None
    try:
        filtro = esperar_elemento(driver, 'mat-select[placeholder*="Fase Processual"], select[placeholder*="Fase Processual"], select', timeout=10)
        if not filtro:
            # Busca por label e input relacionados
            labels = driver.find_elements(By.TAG_NAME, 'label')
            for label in labels:
                if 'fase processual' in label.text.lower():
                    input_id = label.get_attribute('for')
                    if input_id:
                        filtro = driver.find_element(By.ID, input_id)
                        break
        if not filtro:
            print('Filtro de fase processual não encontrado!')
            return False
        safe_click(driver, filtro)
        time.sleep(1)
        # Seleciona opções "Liquidação" e "Execução"
        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option .mat-option-text')
        opcoes_selecionadas = 0
        for opcao in opcoes:
            texto = opcao.text.strip()
            if texto in ['Liquidação', 'Execução']:
                safe_click(driver, opcao)
                opcoes_selecionadas += 1
                time.sleep(1)
        if opcoes_selecionadas == 0:
            print('Nenhuma opção "Liquidação" ou "Execução" encontrada!')
        # Pequena pausa para garantir atualização do filtro
        time.sleep(1)
    except Exception as e:
        print(f'Erro ao filtrar fase processual: {e}')
        return False
    return True

def verificar_login_ativo(driver):
    # Detecta se está na tela de login do PJe TRT2
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    if url_login in driver.current_url or 'login' in driver.current_url:
        print('\n[Sessão expirada ou logout detectado!]')
        print('Faça o login manualmente na janela do Firefox e pressione ENTER para continuar...')
        while url_login in driver.current_url or 'login' in driver.current_url:
            input('Aguardando login... Pressione ENTER após logar.')
            driver.refresh()
        print('Login detectado! Prosseguindo...')
    else:
        # Opcional: pode adicionar checagem por elementos típicos da tela de login
        pass

def filtro_analise(driver):
    print('Iniciando filtro de análise...')
    acessar_painel_global(driver)
    time.sleep(2)  # tempo maior para garantir carregamento
    # Novo seletor para "Análises" baseado no DOM real capturado
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
            return False
    except Exception as e:
        print(f'Erro ao procurar mat-card "Análises": {e}')
        return False
    # 3. Verificar URL da tela de análises
    url_analises = 'https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos'
    for _ in range(15):
        if url_analises in driver.current_url:
            break
        time.sleep(1)
    if url_analises not in driver.current_url:
        print('URL de análises não detectada!')
        return False
    print('Na tela de análises.')
    # 4. Abrir filtro "Fase processual"
    seletor_fase = 'div#mat-select-value-35'
    fase_btn = esperar_elemento(driver, seletor_fase, timeout=15)
    if fase_btn:
        safe_click(driver, fase_btn)
        time.sleep(1.8)
        # Esperar o painel de opções abrir
        time.sleep(1)
        # Buscar todos os itens de opção pelo texto
        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option .mat-option-text')
        opcoes_selecionadas = 0
        for opcao in opcoes:
            texto = opcao.text.strip()
            if texto in ['Liquidação', 'Execução']:
                safe_click(driver, opcao)
                opcoes_selecionadas += 1
                time.sleep(1)
        if opcoes_selecionadas == 0:
            print('Nenhuma opção "Liquidação" ou "Execução" encontrada!')
        # Pequena pausa para garantir atualização do filtro
        time.sleep(1)
    else:
        print('Filtro "Fase processual" não encontrado!')
        return False
    # 5. Aplicar filtro
    btn_filtrar = driver.find_elements(By.CSS_SELECTOR, 'button.mat-focus-indicator.botao-filtrar')
    if btn_filtrar:
        btn_filtrar = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.botao-filtrar'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_filtrar)
        time.sleep(0.5)
        safe_click(driver, btn_filtrar)
        print('Filtro aplicado!')
        time.sleep(3.5)  # tempo maior para garantir atualização
    else:
        print('Botão de filtrar não encontrado!')
        return False
    # 6. Alterar quantidade de itens por página para 100
    seletor_qtd = 'div#mat-select-value-39'
    qtd_btn = esperar_elemento(driver, seletor_qtd, timeout=10)
    if qtd_btn:
        safe_click(driver, qtd_btn)
        time.sleep(1.8)
        seletor_100 = 'mat-option#mat-option-46 > span:nth-child(1)'
        btn_100 = esperar_elemento(driver, seletor_100, timeout=10)
        if btn_100:
            safe_click(driver, btn_100)
            print('Quantidade de itens por página definida para 100.')
            time.sleep(2.5)
        else:
            print('Opção 100 não encontrada!')
    else:
        print('Botão de quantidade de itens não encontrado!')
    print('Filtro de análise concluído.')
    return True

def login_automatico(driver, usuario, senha):
    print('Iniciando login automático...')
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    # 1. Clicar no botão do login PDPJ
    btn_pdpj = esperar_elemento(driver, 'button#btnSsoPdpj > img', timeout=10)
    if btn_pdpj:
        safe_click(driver, btn_pdpj)
        time.sleep(2)
    else:
        print('Botão PDPJ não encontrado!')
        return False
    # 2. Preencher usuário
    campo_usuario = esperar_elemento(driver, 'input#username', timeout=10)
    if campo_usuario:
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
    else:
        print('Campo usuário não encontrado!')
        return False
    # 3. Preencher senha
    campo_senha = esperar_elemento(driver, 'input#password', timeout=10)
    if campo_senha:
        campo_senha.clear()
        campo_senha.send_keys(senha)
    else:
        print('Campo senha não encontrado!')
        return False
    # 4. Clicar em Entrar
    btn_entrar = esperar_elemento(driver, 'input#kc-login', timeout=10)
    if btn_entrar:
        safe_click(driver, btn_entrar)
        print('Login submetido!')
        time.sleep(3)
        return True
    else:
        print('Botão Entrar não encontrado!')
        return False

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
                        linha.style = 'background-color: #ffccd2;'
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

# ========== FUNÇÃO DE ANÁLISE DE PRAZO NO DETALHE ==========
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
        # Aguarda ícone HTML aparecer
        for _ in range(25):
            try:
                btn_html = driver.find_element(By.CSS_SELECTOR, '.fa-file-code')
                if btn_html.is_displayed():
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            print('[DEBUG] Ícone HTML (.fa-file-code) não apareceu após abrir documento.')
            return
        print('[DEBUG] Clicando no ícone HTML...')
        try:
            btn_html = driver.find_element(By.CSS_SELECTOR, '.fa-file-code')
            btn_html.click()
        except Exception as e:
            print(f'[DEBUG] Não encontrou/clicou no ícone HTML (.fa-file-code): {e}')
            return
        time.sleep(1)  # Aguarda caixa de preview abrir
        texto = None
        for _ in range(25):
            try:
                preview = driver.find_element(By.CSS_SELECTOR, '#previewModeloDocumento')
                if preview.is_displayed() and preview.text.strip():
                    texto = preview.text.lower()
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not texto:
            print('[DEBUG] Não foi possível extrair o texto do preview HTML.')
            return
        print('[DEBUG] Texto extraído do preview HTML (completo):')
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
        print(f'[DEBUG] Erro na análise de prazo: {e}')

# ========== AJUSTA INJEÇÃO DO BOTÃO PRAZO PARA CHAMAR A FUNÇÃO ==========
def injetar_botoes_interface(driver):
    if '/painel/global/8/lista-processos' in driver.current_url:
        botao_script = '''
        if (!document.getElementById('btnAnaliseProcesso')) {
            var btn = document.createElement('button');
            btn.id = 'btnAnaliseProcesso';
            btn.textContent = 'Analisar 1º Processo';
            btn.style.position = 'fixed';
            btn.style.bottom = '20px';
            btn.style.right = '20px';
            btn.style.zIndex = '9999';
            btn.style.padding = '10px 15px';
            btn.style.backgroundColor = '#007bff';
            btn.style.color = 'white';
            btn.style.border = 'none';
            btn.style.borderRadius = '5px';
            btn.style.cursor = 'pointer';
            btn.style.fontWeight = 'bold';
            document.body.appendChild(btn);
        }
        '''
        driver.execute_script(botao_script)
        acao_script = '''
        document.getElementById('btnAnaliseProcesso').onclick = function() {
            var linhas = document.querySelectorAll('tr.cdk-drag');
            for (var i = 0; i < linhas.length; i++) {
                var row = linhas[i];
                var checkbox = row.querySelector('mat-checkbox input[type=checkbox]');
                if (checkbox && !checkbox.disabled) {
                    row.style.backgroundColor = '#ffffaa';
                    var btnDetalhes = row.querySelector('button[aria-label="Detalhes do Processo"], button[mattooltip="Detalhes do Processo"]') || row.querySelector('button');
                    if (btnDetalhes) {
                        btnDetalhes.click();
                        break;
                    }
                }
            }
        };
        '''
        driver.execute_script(acao_script)
    elif '/processo/' in driver.current_url and '/detalhe' in driver.current_url:
        try:
            for _ in range(50):
                if driver.execute_script("return document.readyState") == 'complete':
                    break
                time.sleep(0.2)
            for tent in range(50):
                if driver.execute_script("return document.querySelector('#btnPrazoAnalise') === null"):
                    botao_script = '''
                    if (!document.getElementById('btnPrazoAnalise')) {
                        var btn = document.createElement('button');
                        btn.id = 'btnPrazoAnalise';
                        btn.textContent = 'Prazo';
                        btn.style.position = 'fixed';
                        btn.style.bottom = '20px';
                        btn.style.left = '20px';
                        btn.style.zIndex = '9999';
                        btn.style.padding = '12px 18px';
                        btn.style.backgroundColor = '#4CAF50';
                        btn.style.color = 'white';
                        btn.style.border = 'none';
                        btn.style.borderRadius = '7px';
                        btn.style.cursor = 'pointer';
                        btn.style.fontWeight = 'bold';
                        btn.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
                        btn.onclick = function() { window.dispatchEvent(new CustomEvent('botaoPrazoClicadoSelenium')); };
                        document.body.appendChild(btn);
                    }
                    '''
                    driver.execute_script(botao_script)
                if driver.execute_script("return document.querySelector('#btnPrazoAnalise') !== null"):
                    break
                time.sleep(0.2)
            driver.execute_script('''
                window._seleniumPrazoListenerAdded = window._seleniumPrazoListenerAdded || false;
                if (!window._seleniumPrazoListenerAdded) {
                    window.addEventListener('botaoPrazoClicadoSelenium', () => {
                        document.title = '[PRAZO_CLICADO]';
                    });
                    window._seleniumPrazoListenerAdded = true;
                }
            ''')
        except Exception as e:
            print(f'[DEBUG] Falha ao injetar botão Prazo: {e}')

# Exemplo de uso: chame após carregar a página desejada
# injetar_botoes_interface(driver)

# ========== FLUXO PRINCIPAL ==========
def main():
    firefox_options = FirefoxOptions()
    firefox_options.add_argument("--start-maximized")
    firefox_options.set_preference("profile", r"C:\\Users\\s164283\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\2bge54ld.Robot")
    driver = webdriver.Firefox(options=firefox_options)
    driver.implicitly_wait(10)

    driver.get('https://pje.trt2.jus.br/pjekz/')
    time.sleep(2)
    login_automatico(driver, '35305203813', 'SpF59866')
    verificar_login_ativo(driver)
    print('[DEBUG] Login realizado com sucesso.')

    print('[DEBUG] Aguardando contexto de página para injetar botões...')
    url_aba_anterior = None
    botao_analise_injetado = False
    botao_argos_injetado = False
    ultima_url = None
    handles_anteriores = driver.window_handles
    aba_doc_internos_handle = None
    aba_doc_internos_registrada = False
    while True:
        current_url = driver.current_url
        if current_url != ultima_url:
            print(f'[DEBUG] URL atual: {current_url}')
            if url_aba_anterior:
                print(f'[DEBUG] URL anterior: {url_aba_anterior}')
            ultima_url = current_url
        # Detecta se está em documentos internos e guarda o handle apenas uma vez
        if (current_url.startswith('https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos') and not aba_doc_internos_registrada):
            aba_doc_internos_handle = driver.current_window_handle
            aba_doc_internos_registrada = True
            print(f'[DEBUG] Handle da aba documentos internos: {aba_doc_internos_handle}')
        # Se saiu da aba de documentos internos, limpa o registro para permitir novo ciclo
        if (aba_doc_internos_registrada and not current_url.startswith('https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')):
            aba_doc_internos_handle = None
            aba_doc_internos_registrada = False
        # Injeta botão "Analisar 1º Processo" apenas na lista de processos, e só uma vez por navegação
        if current_url.startswith('https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos'):
            try:
                if not driver.execute_script("return document.getElementById('btnAnaliseProcesso') !== null;"):
                    injetar_botoes_interface(driver)
                    print('[DEBUG] Botão "Analisar 1º Processo" injetado na lista.')
                    botao_analise_injetado = True
            except Exception as e:
                print(f'[DEBUG] Falha ao injetar botão de análise: {e}')
            url_aba_anterior = current_url
            botao_argos_injetado = False  # reset ao voltar para lista
        # Detecta abertura de nova aba após documentos internos
        handles_atuais = driver.window_handles
        if aba_doc_internos_handle and len(handles_atuais) > len(handles_anteriores):
            novas_abas = list(set(handles_atuais) - set(handles_anteriores))
            for nova_aba in novas_abas:
                driver.switch_to.window(nova_aba)
                url_nova_aba = driver.current_url
                print(f'[DEBUG] Nova aba detectada: {nova_aba} | URL: {url_nova_aba}')
                if url_nova_aba.startswith('https://pje.trt2.jus.br/pjekz/processo/') and '/detalhe/peticao/' in url_nova_aba:
                    print('[DEBUG] Critério para botão Argos atendido (nova aba após documentos internos).')
                    try:
                        if not driver.execute_script("return document.getElementById('btn-argos-cascade') !== null;"):
                            injetar_botao_argos(driver)
                            print('[DEBUG] Botão Argos injetado na aba de detalhes/petição.')
                            botao_argos_injetado = True
                        # Permanece na nova aba de petição após injetar o botão
                        print(f'[DEBUG] Permanecendo na aba de petição: {nova_aba}')
                        url_aba_anterior = url_nova_aba
                        handles_anteriores = handles_atuais
                        break  # Sai do loop após encontrar a aba correta
                    except Exception as e:
                        print(f'[DEBUG] Falha ao injetar botão Argos: {e}')
                else:
                    # Se não for a aba de petição, volta para documentos internos
                    driver.switch_to.window(aba_doc_internos_handle)
            else:
                handles_anteriores = handles_atuais
        # Monitora clique manual no botão Prazo
        if '[PRAZO_CLICADO]' in driver.title:
            print('[DEBUG] Botão Prazo foi clicado! Iniciando análise...')
            analisar_prazo_detalhe(driver)
            break
        # Monitora clique manual no botão Argos
        if '[ARGOS_CLICADO]' in driver.title:
            print('[DEBUG] Botão Argos foi clicado! Iniciando fluxo Mandados Argos...')
            fluxo_mandados_argos(driver)
            break
        time.sleep(0.2)
    driver.quit()

def criar_gigs_prazo(driver, observacao_nome="silas", dias_uteis=1):
    """
    Automatiza a criação de um GIGS tipo prazo, preenchendo:
    - Observação: 'silas'
    - Dias úteis: 1
    """
    from selenium.webdriver.common.by import By
    import time
    print(f"[DEBUG] Iniciando criação do GIGS prazo: observacao={observacao_nome}, dias_uteis={dias_uteis}")
    try:
        # 1. Abrir painel de GIGS/Atividades clicando em "Nova atividade"
        print("[DEBUG] Procurando botão 'Nova atividade'...")
        try:
            btn_nova_atividade = driver.find_element(By.CSS_SELECTOR, "button#nova-atividade > span.mat-button-wrapper > span")
            safe_click(driver, btn_nova_atividade)
            print("[DEBUG] Botão 'Nova atividade' clicado.")
        except Exception as e:
            print(f"[ERRO] Não foi possível clicar em 'Nova atividade': {e}")
            return False
        time.sleep(1.2)

        # 2. Tipo de atividade (input#mat-input-6) - NÃO mexer, assume que vem preenchido corretamente
        # [DEBUG] Não altera o campo tipo de atividade. Assume valor padrão 'Prazo'.
        time.sleep(0.6)

        # 3. Dias úteis (input#mat-input-10)
        try:
            input_dias = driver.find_element(By.CSS_SELECTOR, "input#mat-input-10")
            input_dias.clear()
            input_dias.send_keys(str(dias_uteis))
            print(f"[DEBUG] Preencheu dias úteis: {dias_uteis}")
        except Exception as e:
            print(f"[ERRO] Não foi possível preencher dias úteis: {e}")
            return False
        time.sleep(0.6)

        # 4. Observação (textarea#mat-input-8)
        try:
            input_obs = driver.find_element(By.CSS_SELECTOR, "textarea#mat-input-8")
            input_obs.clear()
            input_obs.send_keys(observacao_nome)
            print(f"[DEBUG] Preencheu observação: {observacao_nome}")
        except Exception as e:
            print(f"[ERRO] Não foi possível preencher a observação: {e}")
            return False
        time.sleep(0.6)

        # 5. Clicar em Salvar usando seletor robusto fornecido
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-focus-indicator.mat-tooltip-trigger.mat-raised-button.mat-button-base.mat-primary > span.mat-button-wrapper")
            # O botão é o <span>, mas precisamos clicar no <button> pai
            btn_salvar_button = btn_salvar.find_element(By.XPATH, "..")
            safe_click(driver, btn_salvar_button)
            print("[DEBUG] GIGS prazo criado com sucesso! (clicou em Salvar)")
            return True
        except Exception as e:
            print(f"[ERRO] Botão Salvar não encontrado pelo seletor robusto: {e}")
            return False
    except Exception as e:
        print(f"[ERRO] Exceção ao criar GIGS prazo: {e}")
        return False

# Exemplo de uso: chame após carregar a página desejada
# criar_gigs_prazo(driver, observacao_nome="silas", dias_uteis=1)

def criar_gigs_prazo_generico(driver, dias_uteis, observacao):
    """
    Cria um GIGS do tipo Prazo usando seletores robustos e parâmetros informados.
    Não altera o campo Tipo de Atividade (assume 'Prazo' já está preenchido).
    Preenche Dias Úteis e Observação, e clica em Salvar.
    """
    from selenium.webdriver.common.by import By
    import time
    print(f"[DEBUG] Iniciando criação GIGS (dias_uteis={dias_uteis}, observacao={observacao})")
    try:
        # 1. Clicar em Nova Atividade
        print("[DEBUG] Procurando botão 'Nova atividade'...")
        btn_nova_atividade = driver.find_element(By.CSS_SELECTOR, "button#nova-atividade > span.mat-button-wrapper > span")
        safe_click(driver, btn_nova_atividade)
        print("[DEBUG] Botão 'Nova atividade' clicado.")
        time.sleep(1.2)

        # 2. NÃO mexe no campo Tipo de Atividade
        time.sleep(0.6)

        # 3. Dias úteis
        input_dias = driver.find_element(By.CSS_SELECTOR, "input#mat-input-10")
        input_dias.clear()
        input_dias.send_keys(str(dias_uteis))
        print(f"[DEBUG] Preencheu dias úteis: {dias_uteis}")
        time.sleep(0.6)

        # 4. Observação
        input_obs = driver.find_element(By.CSS_SELECTOR, "textarea#mat-input-8")
        input_obs.clear()
        input_obs.send_keys(observacao)
        print(f"[DEBUG] Preencheu observação: {observacao}")
        time.sleep(0.6)

        # 5. Clicar em Salvar
        btn_salvar = driver.find_element(By.CSS_SELECTOR, "button.mat-focus-indicator.mat-tooltip-trigger.mat-raised-button.mat-button-base.mat-primary > span.mat-button-wrapper")
        btn_salvar_button = btn_salvar.find_element(By.XPATH, "..")
        safe_click(driver, btn_salvar_button)
        print("[DEBUG] GIGS criado com sucesso! (clicou em Salvar)")
        return True
    except Exception as e:
        print(f"[ERRO] na criação do GIGS: {e}")
        return False

def tipo_gigs_por_texto(texto):
    """
    Retorna o tipo de GIGS a ser criado com base no texto analisado, seguindo as regras do Tampermonkey.
    """
    import re
    regras = [
        (re.compile(r'concede-se 05 dias|visibilidade.*advogados|início da fluência|indicar meios|oito dias para apresentação', re.I), 'ConfG'),
        (re.compile(r'revel|concorda com homologação', re.I), 'Homol'),
        (re.compile(r'hasta|saldo devedor|prescrição', re.I), 'Pec'),
        (re.compile(r'impugnações apresentadas', re.I), 'Pesq')
    ]
    for regex, tipo in regras:
        if regex.search(texto):
            return tipo
    return 'Sconf'  # fallback

def analisar_e_criar_gigs(driver, texto):
    tipo = tipo_gigs_por_texto(texto)
    descricoes = {
        'Pec': 'xs pec',
        'Homol': 'Silvia - Homologação',
        'ConfG': 'Guilherme - Conferir Sobrestamento.',
        'Sconf': 'Silas - Prazo Manual',
        'Pesq': 'Silvia - Argos'
    }
    dias_uteis = 0 if tipo == 'Sconf' else 1
    observacao = descricoes.get(tipo, f"GIGS automático: {tipo}")
    print(f"[DEBUG] Tipo de GIGS identificado: {tipo}. Criando GIGS com {dias_uteis} dias úteis e observação '{observacao}'...")
    criar_gigs_prazo_generico(driver, dias_uteis, observacao)
    # Pós-criação: ações automáticas específicas
    pos_criacao_gigs(driver, tipo)
    if tipo == "Pesq":
        fluxo_minuta_silvia_argos(driver)

def fluxo_minuta_silvia_argos(driver):
    """
    Fluxo automatizado para minutar processo após criação do GIGS Silvia - Argos.
    1. Abrir tarefa do processo (clicar no botão com span.texto-tarefa-processo)
    2. Selecionar 'Conclusão ao magistrado'
    3. Selecionar tipo de minuta: BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens
    4. Validar URL final
    """
    from selenium.webdriver.common.by import By
    import time
    # 1. Abrir tarefa do processo e trocar para nova aba
    try:
        print('[DEBUG] Procurando botão de tarefa do processo...')
        abas_antes = driver.window_handles
        btn_tarefa = driver.find_element(By.CSS_SELECTOR, 'span.texto-tarefa-processo')
        btn_tarefa_button = btn_tarefa.find_element(By.XPATH, '../../..')
        safe_click(driver, btn_tarefa_button)
        print('[DEBUG] Botão de tarefa do processo clicado.')
        # Aguarde até a URL conter '/transicao' ou timeout
        for i in range(20):
            if '/transicao' in driver.current_url:
                break
            time.sleep(0.5)
        abas_depois = driver.window_handles
        nova_aba = [aba for aba in abas_depois if aba not in abas_antes]
        if nova_aba:
            driver.switch_to.window(nova_aba[0])
            print(f'[DEBUG] Switched para nova aba: {nova_aba[0]} | URL: {driver.current_url}')
        else:
            print('[ALERTA] Nenhuma nova aba detectada após clicar na tarefa!')
        if '/transicao' not in driver.current_url:
            print(f'[ALERTA] URL inesperada após clicar na tarefa: {driver.current_url}')
    except Exception as e:
        print(f'[ERRO] Não foi possível clicar na tarefa do processo: {e}')
        return False
    # 2. Seleciona 'Conclusão ao magistrado'
    try:
        print('[DEBUG] Procurando botão "Conclusão ao magistrado"...')
        click_button_conclusao_ao_magistrado(driver, timeout=10)
        print('[DEBUG] Botão "Conclusão ao magistrado" clicado.')
        # Aguarde até a URL conter '/conclusao' ou timeout
        for i in range(20):
            if '/conclusao' in driver.current_url:
                break
            time.sleep(0.5)
        if '/conclusao' not in driver.current_url:
            print(f'[ALERTA] URL inesperada após clicar em "Conclusão ao magistrado": {driver.current_url}')
    except Exception as e:
        print(f'[ERRO] Não foi possível clicar em "Conclusão ao magistrado": {e}')
        return False
    # 3. Seleciona tipo de minuta
    try:
        print('[DEBUG] Procurando botão "BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens"...')
        click_element_by_visible_text(driver, 'BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens', tag_preferida='button')
        print('[DEBUG] Botão de minuta "BACEN / BNDT / Sigilo Fiscal / Indisponibilidade de Bens" clicado.')
        # Aguarde até a URL conter '/minutar' ou timeout
        for i in range(20):
            if '/minutar' in driver.current_url:
                break
            time.sleep(0.5)
        if '/minutar' not in driver.current_url:
            print(f'[ALERTA] URL inesperada após clicar na minuta: {driver.current_url}')
    except Exception as e:
        print(f'[ERRO] Não foi possível clicar no botão de minuta: {e}')
        return False
    # 4. Validar página de minuta
    try:
        print('[DEBUG] Checando URL da página de minutar...')
        if '/minutar' in driver.current_url:
            print('[DEBUG] Página de minutar carregada com sucesso.')
            return True
        else:
            print(f'[ALERTA] Não está na página esperada de minutar: {driver.current_url}')
            return False
    except Exception as e:
        print(f'[ERRO] Erro ao validar página de minutar: {e}')
        return False

def click_button_conclusao_ao_magistrado(driver, timeout=10):
    """
    Clica no botão de conclusão ao magistrado usando, em ordem:
    1. O ícone .fa-clipboard-check
    2. <button> com aria-label='Conclusão ao magistrado'
    """
    from selenium.webdriver.common.by import By
    import time
    for tent in range(timeout * 2):
        # 1. Buscar pelo ícone .fa-clipboard-check
        icones = driver.find_elements(By.CSS_SELECTOR, '.fa-clipboard-check')
        for icone in icones:
            if icone.is_displayed():
                # Subir até 5 níveis para achar um <button>
                parent = icone
                for _ in range(5):
                    parent = parent.find_element(By.XPATH, '..')
                    if parent.tag_name.lower() == 'button' and parent.is_displayed():
                        print(f"[DEBUG] Clique em <button> via .fa-clipboard-check na tentativa {tent+1}")
                        parent.click()
                        return True
        # 2. Buscar <button> por aria-label
        botoes_aria = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Conclusão ao magistrado"]')
        botoes_aria = [b for b in botoes_aria if b.is_displayed()]
        if botoes_aria:
            print(f"[DEBUG] Clique em <button aria-label='Conclusão ao magistrado'> na tentativa {tent+1}")
            botoes_aria[0].click()
            return True
        time.sleep(0.5)
    # Log detalhado
    print(f"[ERRO] Não foi possível clicar em conclusão ao magistrado. Candidatos:")
    icones = driver.find_elements(By.CSS_SELECTOR, '.fa-clipboard-check')
    for idx, ic in enumerate(icones):
        print(f"[DEBUG] .fa-clipboard-check idx={idx}, visível={ic.is_displayed()}, tag={ic.tag_name}")
    botoes_aria = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label]')
    for idx, b in enumerate(botoes_aria):
        print(f"[DEBUG] <button> idx={idx}, aria-label='{b.get_attribute('aria-label')}', texto='{b.text}', visível={b.is_displayed()}, classes='{b.get_attribute('class')}'")
    print("[ERRO] Busca finalizada. Nenhum botão de conclusão ao magistrado clicável encontrado.")
    raise Exception("Nenhum botão de conclusão ao magistrado encontrado.")

def pos_criacao_gigs(driver, tipo_gigs):
    """
    Executa ação automática após criar o GIGS, podendo mudar de aba e realizar movimentação ou outra ação.
    """
    print(f"[DEBUG] Iniciando ação pós-GIGS para tipo: {tipo_gigs}")
    if tipo_gigs == "Pesq":  # Silvia - Argos
        fluxo_minuta_silvia_argos(driver)
    # Outras regras futuras podem ser adicionadas aqui
    print("[DEBUG] Fase 3 concluída para tipo:", tipo_gigs)
    if tipo_gigs == "Pesq":  # Silvia - Argos
        sucesso_ajuste = ajuste_minuta_silvia_argos(driver)
        if not sucesso_ajuste:
            print('[ERRO] Ajuste de minuta Silvia - Argos falhou.')
        else:
            print('[DEBUG] Ajuste de minuta Silvia - Argos concluído.')

def ajuste_minuta_silvia_argos(driver):
    """
    Fluxo final de ajuste de minuta para o caso Silvia - Argos:
    1. Seleciona o campo #inputFiltro[aria-label], clica, limpa e digita 'xsbacen'.
    2. Seleciona o modelo destacado com .nodo-filtrado > span:nth-child(1) e clica.
    3. Na janela, localiza e clica no botão Inserir (button.mat-primary > span, texto ou aria inserir).
    """
    from selenium.webdriver.common.by import By
    import time
    print('[DEBUG] Iniciando ajuste de minuta Silvia - Argos...')
    try:
        # 1. Selecionar campo de busca de modelo
        campo_busca = driver.find_element(By.CSS_SELECTOR, '#inputFiltro[aria-label]')
        campo_busca.click()
        time.sleep(0.5)
        campo_busca.clear()
        campo_busca.send_keys('xsbacen')
        print('[DEBUG] Digitado "xsbacen" no campo de busca do modelo.')
        time.sleep(1)
        # 2. Selecionar modelo destacado
        modelo_destacado = driver.find_element(By.CSS_SELECTOR, '.nodo-filtrado > span:nth-child(1)')
        modelo_destacado.click()
        print('[DEBUG] Modelo destacado selecionado.')
        time.sleep(1)
        # 3. Clicar em inserir na janela
        botoes_inserir = driver.find_elements(By.CSS_SELECTOR, 'button.mat-primary > span')
        btn_inserir = None
        for btn in botoes_inserir:
            if 'inserir' in btn.text.lower():
                btn_inserir = btn.find_element(By.XPATH, '..')
                break
        if btn_inserir:
            btn_inserir.click()
            print('[DEBUG] Botão Inserir clicado.')
        else:
            print('[ALERTA] Botão Inserir não encontrado!')
        time.sleep(1)
    except Exception as e:
        print(f'[ERRO] Erro no ajuste de minuta Silvia - Argos: {e}')
        return False
    return True

# === MÓDULO MANDADOS: Hipótese 1 - Pesquisas (Argos) ===
def fluxo_mandados_argos(driver):
    """
    Fluxo Mandados Argos - Hipótese 1 (Pesquisas)
    1. Abrir sigilo da Certidão de devolução e tratar anexos INFOJUD/DOI/IRPF
    2. Tratar documentos seguintes: abrir sigilo de Planilha, Decisão e Certidão de expedição
    3. Tratar Intimação (envelope, checkbox, confirmar) - apenas se Decisão e Intimação estiverem na mesma data, e Planilha logo após Intimação
    4. Ao final, garantir seleção da Certidão de devolução
    """
    from selenium.webdriver.common.by import By
    import time
    print('[DEBUG] Iniciando fluxo Mandados Argos...')
    abas = driver.window_handles
    if len(abas) < 2:
        print('[ERRO] Não há aba anterior para validar escaninho!')
        return False
    print('[DEBUG] Escaninho de documentos internos validado.')
    if not fechar_overlays(driver, timeout=10):
        print('[ERRO] Não foi possível fechar overlay/modal. Corrija manualmente e tente novamente.')
        return False
    try:
        # 1. Certidão de devolução
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        certidao = next((el for el in itens if 'Certidão de devolução' in el.text), None)
        if not certidao:
            print('[ERRO] Certidão de devolução não encontrada.')
            return False
        certidao.click()
        print('[DEBUG] Certidão de devolução clicada.')
        time.sleep(1)
        # 2. Coletar todos os documentos relevantes (com data)
        docs_info = []
        for el in itens:
            try:
                nome = el.text.split('\n')[0].strip()
                data = el.find_element(By.CSS_SELECTOR, '.tl-data').text.strip()
                docs_info.append({'el': el, 'nome': nome, 'data': data})
            except Exception:
                continue
        # 3. Identificar Decisão, Intimação e Planilha agrupados
        decisao = next((d for d in docs_info if 'Decisão' in d['nome']), None)
        intimacao = next((d for d in docs_info if 'Intimação' in d['nome']), None)
        planilha = next((d for d in docs_info if 'Planilha' in d['nome']), None)
        # Critério: Decisão e Intimação na mesma data, Planilha logo após Intimação
        if not (decisao and intimacao and planilha):
            print('[ERRO] Não localizados Decisão, Intimação e Planilha para o critério.')
            return False
        idx_dec = docs_info.index(decisao)
        idx_int = docs_info.index(intimacao)
        idx_pla = docs_info.index(planilha)
        if decisao['data'] != intimacao['data']:
            print('[ERRO] Decisão e Intimação não estão na mesma data.')
            return False
        if not (idx_pla == idx_int + 1):
            print('[ERRO] Planilha de cálculos não está logo após a Intimação.')
            return False
        # 4. Tratar Decisão, Intimação e Planilha
        for doc in [decisao, intimacao, planilha]:
            el = doc['el']
            try:
                el.click()
                print(f'[DEBUG] Documento tratado: {doc["nome"]} ({doc["data"]})')
                time.sleep(1)
            except Exception as e:
                print(f'[ERRO] Falha ao clicar em {doc["nome"]}: {e}')
                return False
        # 5. Tratar Certidão de expedição se existir
        cert_exp = next((d for d in docs_info if 'Certidão de expedição' in d['nome']), None)
        if cert_exp:
            try:
                cert_exp['el'].click()
                print(f'[DEBUG] Certidão de expedição tratada: {cert_exp["data"]}')
                time.sleep(1)
            except Exception as e:
                print(f'[ERRO] Falha ao clicar em Certidão de expedição: {e}')
        # 6. Garantir seleção da Certidão de devolução
        certidao.click()
        print('[DEBUG] Certidão de devolução selecionada ao final.')
        return True
    except Exception as e:
        print(f'[ERRO] Falha no fluxo Mandados Argos: {e}')
        return False

def injetar_botao_argos(driver):
    """
    Injeta o botão 'Argos' na interface da aba de detalhes, se a aba anterior for escaninho de documentos internos.
    O botão, quando clicado manualmente, executa o fluxo_mandados_argos(driver).
    """
    import time
    try:
        # Verifica se o botão já existe para não duplicar
        if driver.execute_script("return document.getElementById('btn-argos-cascade') !== null"):
            print('[DEBUG] Botão Argos já está presente.')
            return
        # Localiza o botão de referência para posicionar o Argos à direita
        ref_btn = None
        try:
            ref_btn = driver.find_element(By.CSS_SELECTOR, '.actions-container > button:nth-child(1)')
        except Exception:
            ref_btn = None
        if ref_btn:
            driver.execute_script('''
                var ref = arguments[0];
                var btn = document.createElement('button');
                btn.id = 'btn-argos-cascade';
                btn.innerText = 'Argos';
                btn.style.marginLeft = '16px';
                btn.style.backgroundColor = '#1976d2';
                btn.style.color = 'white';
                btn.style.border = 'none';
                btn.style.borderRadius = '5px';
                btn.style.cursor = 'pointer';
                btn.style.fontWeight = 'bold';
                btn.style.padding = '10px 15px';
                btn.style.fontSize = '16px';
                btn.style.zIndex = '9999';
                ref.parentNode.insertBefore(btn, ref.nextSibling);
            ''', ref_btn)
        else:
            driver.execute_script('''
                var btn = document.createElement('button');
                btn.id = 'btn-argos-cascade';
                btn.innerText = 'Argos';
                btn.style.position = 'fixed';
                btn.style.top = '90px';
                btn.style.right = '30px';
                btn.style.zIndex = '9999';
                btn.style.padding = '10px 15px';
                btn.style.backgroundColor = '#1976d2';
                btn.style.color = 'white';
                btn.style.border = 'none';
                btn.style.borderRadius = '5px';
                btn.style.cursor = 'pointer';
                btn.style.fontWeight = 'bold';
                btn.style.fontSize = '16px';
                document.body.appendChild(btn);
            ''')
        print('[DEBUG] Botão Argos injetado na interface.')
        # Injeta o listener para disparar o fluxo de mandados ao clicar
        driver.execute_script('''
            if (!window._argosListenerAdded) {
                document.getElementById('btn-argos-cascade').addEventListener('click', function() {
                    document.title = '[ARGOS_CLICADO]';
                });
                window._argosListenerAdded = true;
            }
        ''')
    except Exception as e:
        print(f'[DEBUG] Falha ao injetar botão Argos: {e}')

def aguardar_clique_botao_argos(driver, timeout=600):
    """
    Aguarda o clique manual do botão Argos (até timeout em segundos).
    Só chama fluxo_mandados_argos(driver) se o botão for clicado (data-argos-cascade=1).
    """
    import time
    print('[INFO] Aguarde o clique manual no botão Argos para iniciar o fluxo Mandados...')
    for _ in range(timeout*2):
        try:
            flag = driver.execute_script("return document.body.getAttribute('data-argos-cascade')")
            if flag == '1':
                print('[DEBUG] Botão Argos clicado! Iniciando fluxo Mandados Argos.')
                # Limpa o flag para permitir reuso
                driver.execute_script("document.body.removeAttribute('data-argos-cascade')")
                fluxo_mandados_argos(driver)
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        print('[INFO] Timeout aguardando clique no botão Argos.')

def fechar_overlays(driver, timeout=10):
    """
    Aguarda o fechamento de overlays/backdrops (ex: .cdk-overlay-backdrop) antes de prosseguir.
    Se houver overlay, tenta clicar ou pressionar ESC para fechá-lo.
    Se não conseguir fechar, retorna False.
    """
    import time
    from selenium.webdriver.common.keys import Keys
    end_time = time.time() + timeout
    while time.time() < end_time:
        overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop')
        overlays_visiveis = [o for o in overlays if o.is_displayed()]
        if not overlays_visiveis:
            return True
        print('[DEBUG] Overlay detectado, tentando fechar...')
        try:
            # Tenta clicar no overlay
            for overlay in overlays_visiveis:
                overlay.click()
                time.sleep(0.5)
            # Tenta pressionar ESC
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except Exception as e:
            print(f'[DEBUG] Falha ao tentar fechar overlay: {e}')
        time.sleep(0.5)
    print('[ERRO] Overlay não foi fechado após timeout.')
    return False

if __name__ == "__main__":
    main()
