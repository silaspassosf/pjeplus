import time
import re
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

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
                magistrate_icon = item.find_element(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                doc_text = doc_link.text.lower()
                mag_text = magistrate_icon.get_attribute('aria-label').lower()
                if re.search(r'despacho|decisão|sentença|conclusão', doc_text) and re.search(r'otavio|mariana', mag_text):
                    doc_item = item
                    break
            except NoSuchElementException:
                continue
        if not doc_item:
            print('Documento não encontrado')
            return None
        doc_link = doc_item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
        safe_click(driver, doc_link)
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
        (re.compile(r'unicamente previdenciário'), 'concluso', 'suspinss'),
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
        safe_click(driver, btn_filtrar[0])
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

def selecionar_processos_livres_e_aplicar_chip(driver, chip_nome="Analisado"):
    print(f'Selecionando processos Livres e aplicando chip: {chip_nome}')
    # 1. Selecionar processos livres na tabela
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        selecionados = 0
        for linha in linhas:
            try:
                # 9a coluna: time (prazo), se não existir ou vazio = livre
                prazo = linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(9) time')
                prazo_vazio = not prazo or not prazo[0].text.strip()
                # Comentário
                tem_comentario = linha.find_elements(By.CSS_SELECTOR, 'i.fa-comment')
                # Campo preenchido
                campo = linha.find_elements(By.CSS_SELECTOR, 'input[matinput]')
                campo_preenchido = campo and campo[0].get_attribute('value').strip()
                # Ícone lupa (consulta)
                tem_lupa = linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')
                if prazo_vazio and not tem_comentario and not campo_preenchido and not tem_lupa:
                    checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type="checkbox"]')
                    if not checkbox.is_selected():
                        driver.execute_script('arguments[0].click()', checkbox)
                        linha.style = 'background-color: #ffccd2;'
                        selecionados += 1
            except Exception:
                continue
        print(f'{selecionados} processos livres selecionados.')
        if selecionados == 0:
            print('Nenhum processo livre encontrado para seleção.')
            return False
    except Exception as e:
        print(f'Erro ao selecionar processos livres: {e}')
        return False
    # 2. Aplicar chip em lote
    try:
        # Clicar no botão de chips em lote
        botao_chip = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'pje-botoes-etiquetas-lote button i.far.fa-circle.texto-verde'))
        )
        safe_click(driver, botao_chip)
        time.sleep(2)
        # Campo de busca do chip
        campo_chip = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-dialog-container input[matinput]'))
        )
        campo_chip.click()
        campo_chip.clear()
        for letra in chip_nome:
            campo_chip.send_keys(letra)
            time.sleep(0.3)
        time.sleep(2)
        # Selecionar chip pelo nome
        linhas_chip = driver.find_elements(By.CSS_SELECTOR, 'mat-dialog-container pje-data-table tbody tr')
        chip_encontrado = False
        for linha in linhas_chip:
            if chip_nome in linha.text:
                checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox .mat-checkbox-inner-container')
                driver.execute_script('arguments[0].click()', checkbox)
                chip_encontrado = True
                print(f'Chip "{chip_nome}" selecionado!')
                break
        if not chip_encontrado:
            # Seleciona o primeiro da lista
            primeira_linha = driver.find_element(By.CSS_SELECTOR, 'mat-dialog-container pje-data-table tbody tr:first-child mat-checkbox')
            driver.execute_script('arguments[0].click()', primeira_linha)
            print('Chip padrão selecionado (primeiro da lista).')
        time.sleep(1)
        # Confirmar
        btn_confirmar = driver.find_element(By.CSS_SELECTOR, 'mat-dialog-container button.mat-primary span')
        driver.execute_script('arguments[0].click()', btn_confirmar)
        print('Chip aplicado com sucesso!')
        time.sleep(2)
        return True
    except Exception as e:
        print(f'Erro ao aplicar chip: {e}')
        return False

# ========== FLUXO PRINCIPAL ==========
def main():
    firefox_options = FirefoxOptions()
    # firefox_options.add_argument('--headless')  # Descomente para rodar sem interface gráfica
    # Caminho do novo perfil Firefox do usuário
    firefox_profile_path = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\msjsuwps.Robot'
    firefox_options.add_argument('-profile')
    firefox_options.add_argument(firefox_profile_path)
    driver = webdriver.Firefox(options=firefox_options)
    driver.maximize_window()
    try:
        # Login automático
        login_automatico(driver, '35305203813', 'SpF59866')
        verificar_login_ativo(driver)
        # Placeholder para estágio 1: VENCIMENTO
        print('--- [PRAZOS] Estágio 1: VENCIMENTO (placeholder) ---')
        # Estágio 2: FILTRO DE ANÁLISE
        filtro_analise(driver)
        # Estágio 2b: Selecionar Livres e aplicar chip "Analisado"
        selecionar_processos_livres_e_aplicar_chip(driver, chip_nome="Analisado")
        # Estágio 3: ABERTURA DE PROCESSOS E PROCESSAMENTO (já iniciado no script)
        print('--- Parando aqui conforme solicitado. O restante do fluxo será implementado depois. ---')
        input('Pressione ENTER para fechar o navegador...')
    finally:
        print('Finalizando...')
        driver.quit()

if __name__ == "__main__":
    main()
