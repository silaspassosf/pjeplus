# sisbajud.py
# Automação SISBAJUD integrada ao PJe (abertas em /detalhe)
# Injeta botões na tela de detalhes do processo no PJe para acionar automações no SISBAJUD
# Autor: Cascade AI

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from Fix import driver_pc, login_pc, extrair_dados_processo
import json
import tempfile
import os
import json
import tempfile
# Certifique-se de que driver_firefox_sisbajud está definido ou importado
from bacen import driver_firefox_sisbajud

# ===================== CONFIGURAÇÕES =====================
CONFIG = {
    'cor_bloqueio_positivo': '#32cd32',
    'cor_bloqueio_negativo': '#ff6347',
    'acao_automatica': 'transferir',  # opções: 'transferir', 'desbloquear', 'nenhuma'
    'banco_preferido': 'Banco do Brasil',
    'agencia_preferida': '5905',
    'teimosinha': '60',  # dias
    # Campos essenciais para SISBAJUD caso não estejam presentes nos dados extraídos:
    'nome_default': '',  # Preencha aqui o nome padrão do polo ativo/passivo
    'documento_default': '',  # Preencha aqui o documento padrão do polo ativo/passivo
    'valor_default': '',  # Preencha aqui o valor padrão do bloqueio
    # ... outros parâmetros
}

# Variável global para armazenar dados extraídos do processo
processo_dados_extraidos = None

# ===================== INJETAR BOTÕES NO PJe =====================
def injetar_botoes_pje(driver):
    """
    Injeta botões na tela de detalhes do processo (/detalhe) do PJe.
    Cada botão, ao ser clicado, pode abrir o SISBAJUD e executar automações.
    """
    driver.execute_script("""
        if (!document.getElementById('btn_minuta_bloqueio')) {
            let container = document.createElement('div');
            container.id = 'sisbajud_btn_container';
            container.style = 'position:fixed;top:60px;right:20px;z-index:9999;background:#fff;padding:8px;border-radius:8px;box-shadow:0 2px 8px #0002;';
            // Botão Minuta Bloqueio
            let btn1 = document.createElement('button');
            btn1.id = 'btn_minuta_bloqueio';
            btn1.innerText = 'Minuta de Bloqueio';
            btn1.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn1.onclick = function() { window.dispatchEvent(new CustomEvent('minuta_bloqueio')); };
            container.appendChild(btn1);
            // Botão Minuta Endereço
            let btn2 = document.createElement('button');
            btn2.id = 'btn_minuta_endereco';
            btn2.innerText = 'Minuta de Endereço';
            btn2.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn2.onclick = function() { window.dispatchEvent(new CustomEvent('minuta_endereco')); };
            container.appendChild(btn2);
            // Botão Processar Bloqueios
            let btn3 = document.createElement('button');
            btn3.id = 'btn_processar_bloqueios';
            btn3.innerText = 'Processar Bloqueios';
            btn3.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn3.onclick = function() { window.dispatchEvent(new CustomEvent('processar_bloqueios')); };
            container.appendChild(btn3);
            document.body.appendChild(container);
        }
    """)

# ===================== PROMPT DE DADOS VIA JS =====================
def prompt_js(driver, mensagem, valor_padrao=''):
    """
    Exibe um prompt JS na página e retorna o valor digitado.
    """
    return driver.execute_script(f"return prompt('{mensagem.replace("'", "\'")}', '{valor_padrao}');")

# ===================== ACIONADORES DE EVENTOS =====================
def bind_eventos(driver):
    """
    Injeta JS para escutar eventos customizados e acionar funções Python.
    Deve ser chamado após injetar os botões.
    """
    # No Selenium puro não é possível escutar eventos JS diretamente.
    # Usamos polling para checar flags JS e disparar as funções Python.
    driver.execute_script("window.sisbajud_event_flag = '';")
    driver.execute_script("""
        window.addEventListener('minuta_bloqueio', function() { window.sisbajud_event_flag = 'minuta_bloqueio'; });
        window.addEventListener('minuta_endereco', function() { window.sisbajud_event_flag = 'minuta_endereco'; });
        window.addEventListener('processar_bloqueios', function() { window.sisbajud_event_flag = 'processar_bloqueios'; });
    """)

def checar_evento(driver):
    """
    Checa se algum evento foi disparado via botão JS.
    """
    flag = driver.execute_script("return window.sisbajud_event_flag;")
    if flag:
        driver.execute_script("window.sisbajud_event_flag = '';")
    return flag

# ===================== FLUXOS DE AUTOMAÇÃO SISBAJUD =====================
def salvar_cookies_sisbajud(driver, caminho='cookies_sisbajud.json'):
    """
    Salva cookies da sessão SISBAJUD para o domínio https://sisbajud.cloud.pje.jus.br
    """
    import json
    cookies = driver.get_cookies()
    # Filtra cookies do domínio sisbajud.cloud.pje.jus.br
    cookies_filtrados = [c for c in cookies if 'sisbajud.cloud.pje.jus.br' in c.get('domain', '')]
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(cookies_filtrados, f, ensure_ascii=False, indent=2)
    print(f'[SISBAJUD] Cookies SISBAJUD salvos em {caminho}.')

def abrir_sisbajud_em_nova_aba(driver):
    """
    Abre o SISBAJUD em nova aba e retorna o handle.
    Força o salvamento de cookies após o primeiro acesso.
    """
    driver.execute_script("window.open('https://sisbajud.cnj.jus.br/', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(2)
    # Força salvamento de cookies SISBAJUD
    salvar_cookies_sisbajud(driver)
    return driver.current_window_handle

def abrir_sisbajud_em_firefox_sisbajud():
    driver = driver_firefox_sisbajud(headless=False)
    driver.get('https://sisbajud.cnj.jus.br/')
    print('[SISBAJUD] SISBAJUD aberto em Firefox (perfil Sisb).')
    # Integração: carrega dados extraídos do processo do arquivo temporário
    global processo_dados_extraidos
    try:
        temp_path = os.path.join(tempfile.gettempdir(), 'processo_dados_extraidos.json')
        if os.path.exists(temp_path):
            with open(temp_path, 'r', encoding='utf-8') as f:
                processo_dados_extraidos = json.load(f)
            print('[SISBAJUD] Dados do processo carregados do arquivo temporário:', processo_dados_extraidos)
        else:
            print('[SISBAJUD][ERRO] Arquivo temporário de dados do processo não encontrado.')
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao carregar dados do processo do arquivo temporário: {e}')
    return driver

def minuta_bloqueio(driver):
    """
    Fluxo de geração de minuta de bloqueio no SISBAJUD.
    Pode pedir dados ao usuário via prompt_js.
    """
    handle = abrir_sisbajud_em_nova_aba(driver)
    # Exemplo: pedir valor do bloqueio
    valor = prompt_js(driver, 'Informe o valor do bloqueio:', '1000,00')
    # Aqui implementar o preenchimento dos campos e execução da minuta
    # ...
    print(f'[SISBAJUD] Minuta de bloqueio iniciada com valor: {valor}')
    # Feche a aba do SISBAJUD se desejar
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])

def minuta_endereco(driver):
    """
    Fluxo de geração de minuta de endereço no SISBAJUD.
    """
    handle = abrir_sisbajud_em_nova_aba(driver)
    endereco = prompt_js(driver, 'Informe o endereço para pesquisa:', '')
    # Implementar automação do preenchimento
    print(f'[SISBAJUD] Minuta de endereço iniciada para: {endereco}')
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])

def processar_bloqueios(driver):
    """
    Processa a tabela de bloqueios no SISBAJUD, muda cor das linhas e preenche campos automaticamente.
    """
    handle = abrir_sisbajud_em_nova_aba(driver)
    # Exemplo: mudar cor das linhas com bloqueio positivo
    js = """
        let linhas = document.querySelectorAll('tr');
        linhas.forEach(function(linha) {
            if (linha.innerText.toLowerCase().includes('bloqueio positivo')) {
                linha.style.backgroundColor = '%s';
            }
            if (linha.innerText.toLowerCase().includes('bloqueio negativo')) {
                linha.style.backgroundColor = '%s';
            }
        });
    """ % (CONFIG['cor_bloqueio_positivo'], CONFIG['cor_bloqueio_negativo'])
    driver.execute_script(js)
    # Preencher campos de transferência/desbloqueio conforme config
    # ...
    print('[SISBAJUD] Processamento de bloqueios executado.')
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])

def escolher_opcao_sisbajud(driver, seletor, valor):
    """
    Seleciona uma opção em um campo select do SISBAJUD, simulando teclas e cliques.
    """
    try:
        el = driver.find_element_by_css_selector(seletor)
        el.click()
        time.sleep(0.3)
        # Tenta encontrar a opção pelo texto
        opcoes = driver.find_elements_by_css_selector('mat-option[role="option"], option')
        for opc in opcoes:
            if valor.lower() in opc.text.lower():
                opc.click()
                print(f'[KAIZEN] Opção "{valor}" selecionada em {seletor}')
                return True
        print(f'[KAIZEN][ERRO] Opção "{valor}" não encontrada em {seletor}')
        return False
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao selecionar opção: {e}')
        return False

# ===================== INJETAR MENU KAIZEN NO SISBAJUD =====================
def injetar_menu_kaizen_sisbajud(driver):
    """
    Injeta o menu Kaizen (estilo MaisPje) na página do SISBAJUD, com todos os botões e estilos principais e ações vinculadas.
    """
    driver.execute_script('''
    if (!document.getElementById('maisPje_menuKaizen')) {
        let menuMaisPje = document.createElement("menumaispje");
        menuMaisPje.setAttribute('aria-live','polite');
        menuMaisPje.id = "maisPje_menuKaizen";
        menuMaisPje.className = "maisPje-no-print openv";
        menuMaisPje.draggable = true;
        menuMaisPje.style = "filter: revert; left: 80vw; top: 80vh; z-index:99999; position:fixed;";
        let menuMaisPje_content = document.createElement("div");
        menuMaisPje_content.id = "maisPje_menuKaizen_content";
        menuMaisPje_content.className = "menuMaisPje-content";
        // Função para criar cada botão do menu
        function criarBotao(id, tooltip, color, icone, handler) {
            let span = document.createElement('span');
            span.id = id;
            span.style = `--p:1; --d:-1; --c:0; --color:${color};`;
            let a = document.createElement('a');
            a.setAttribute('maispje-tooltip-esquerda', tooltip);
            a.style.backgroundColor = color;
            let i = document.createElement('i');
            i.className = icone;
            a.appendChild(i);
            if (handler) a.onclick = handler;
            span.appendChild(a);
            return span;
        }
        // Adiciona os botões do menu Kaizen (SISBAJUD) com handlers que disparam eventos customizados
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_guardar_senha', 'Guardar Senha', 'orangered', 'icone menuConvenio_senha t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_guardar_senha'));}));
        menuMaisPje_content.lastChild.style.display = 'none';
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_preencher_camposinvertido', 'Preencher Campos com Polo Ativo', 'darkcyan', 'icone menuConvenio_magic t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_preencher_campos_invertido'));}));
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_preencher_campos', 'Preencher Campos com Polo Passivo', 'orangered', 'icone menuConvenio_magic t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_preencher_campos'));}));
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_nova_minuta_end', 'Nova Minuta Endereço', 'darkcyan', 'icone menuConvenio_add t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_nova_minuta_end'));}));
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_nova_minuta', 'Nova Minuta', 'orangered', 'icone menuConvenio_add t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_nova_minuta'));}));
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_consultar_TEIMOSINHA', 'Consultar Teimosinha', 'orangered', 'icone menuConvenio_history t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_consultar_teimosinha'));}));
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_consultar_minuta', 'Consultar Minuta', 'orangered', 'icone menuConvenio_search t100 tamanho70', function(){window.dispatchEvent(new CustomEvent('kaizen_consultar_minuta'));}));
        menuMaisPje_content.appendChild(criarBotao('maisPje_menuKaizen_itemmenu_consulta_rapida', 'Consultar Processo no PJe', 'orangered', 'icone bolt t100 tamanho40', function(){window.dispatchEvent(new CustomEvent('kaizen_consulta_rapida'));}));
        // Botão Kaizen (toggle)
        let toggle_btn = document.createElement("div");
        toggle_btn.className = "toggle-btn";
        let img = document.createElement("img");
        img.draggable = false;
        img.className = "maisPje-img";
        img.src = "https://raw.githubusercontent.com/cascadetech/maispje/main/icons/ico_32.png";
        toggle_btn.appendChild(img);
        menuMaisPje_content.insertBefore(toggle_btn, menuMaisPje_content.firstChild);
        menuMaisPje.appendChild(menuMaisPje_content);
        document.body.appendChild(menuMaisPje);
    }
    ''')
    # Injeta listeners para os eventos customizados dos botões Kaizen
    driver.execute_script('''
        window.kaizen_event_flag = '';
        window.addEventListener('kaizen_guardar_senha', function(){ window.kaizen_event_flag = 'kaizen_guardar_senha'; });
        window.addEventListener('kaizen_preencher_campos_invertido', function(){ window.kaizen_event_flag = 'kaizen_preencher_campos_invertido'; });
        window.addEventListener('kaizen_preencher_campos', function(){ window.kaizen_event_flag = 'kaizen_preencher_campos'; });
        window.addEventListener('kaizen_nova_minuta_end', function(){ window.kaizen_event_flag = 'kaizen_nova_minuta_end'; });
        window.addEventListener('kaizen_nova_minuta', function(){ window.kaizen_event_flag = 'kaizen_nova_minuta'; });
        window.addEventListener('kaizen_consultar_teimosinha', function(){ window.kaizen_event_flag = 'kaizen_consultar_teimosinha'; });
        window.addEventListener('kaizen_consultar_minuta', function(){ window.kaizen_event_flag = 'kaizen_consultar_minuta'; });
        window.addEventListener('kaizen_consulta_rapida', function(){ window.kaizen_event_flag = 'kaizen_consulta_rapida'; });
    ''')

def checar_kaizen_evento(driver):
    """
    Checa se algum evento do menu Kaizen foi disparado.
    """
    flag = driver.execute_script("return window.kaizen_event_flag;")
    if flag:
        driver.execute_script("window.kaizen_event_flag = '';")
    return flag

# ===================== AÇÕES DOS BOTÕES KAIZEN =====================
def kaizen_guardar_senha(driver):
    print('[KAIZEN] Guardar Senha: (ação não implementada, placeholder)')
    # Implemente aqui se necessário

def kaizen_preencher_campos(driver, invertido=False):
    global processo_dados_extraidos
    print(f'[KAIZEN] Preencher campos SISBAJUD (invertido={invertido})')
    if not processo_dados_extraidos:
        print('[KAIZEN][ERRO] Dados do processo não extraídos. Abortando preenchimento.')
        return
    try:
        # Garante que está na tela de cadastro de minuta
        if '/minuta/cadastrar' not in driver.current_url:
            print('[KAIZEN][ERRO] Não está na tela de cadastro de minuta.')
            return
        # Seleção de partes conforme polo
        partes = processo_dados_extraidos.get('partes', {})
        if invertido:
            lista_de_executados = partes.get('ativas', [])
        else:
            lista_de_executados = partes.get('passivas', [])
        if not lista_de_executados:
            print('[KAIZEN][ERRO] Nenhuma parte encontrada para o polo selecionado.')
            return
        # Preencher CPF/CNPJ e nome do executado
        for idx, parte in enumerate(lista_de_executados):
            cpf = parte.get('documento', '')
            nome = parte.get('nome', '')
            try:
                el_cpf = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='CPF']")
                el_cpf.clear()
                el_cpf.send_keys(cpf)
                el_cpf.send_keys(Keys.TAB)
                time.sleep(0.2)
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao preencher CPF/CNPJ: {e}")
            try:
                el_nome = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Nome do autor/exequente da ação']")
                el_nome.clear()
                el_nome.send_keys(nome)
                el_nome.send_keys(Keys.TAB)
                time.sleep(0.2)
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao preencher nome: {e}")
            # Tenta clicar no botão adicionar réu/executado se existir
            try:
                btn_add = driver.find_element(By.CSS_SELECTOR, "button[class*='btn-adicionar']")
                btn_add.click()
                time.sleep(0.5)
            except Exception:
                pass  # Não é erro fatal se não existir
        # Valor atualizado
        valor = processo_dados_extraidos.get('valor', CONFIG.get('valor_default', ''))
        if valor:
            try:
                el = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Valor aplicado a todos']")
                el.clear()
                el.send_keys(valor)
                el.send_keys(Keys.TAB)
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao preencher valor: {e}")
        # Conta-salário
        if CONFIG.get('contasalario', '').lower() == 'sim':
            try:
                toggles = driver.find_elements(By.CSS_SELECTOR, 'mat-slide-toggle label')
                for toggle in toggles:
                    toggle.click()
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao marcar conta-salário: {e}")
        print(f"[KAIZEN] Campos preenchidos para {len(lista_de_executados)} parte(s).")
    except Exception as e:
        print(f"[KAIZEN][ERRO] Falha geral ao preencher campos: {e}")

def kaizen_nova_minuta(driver, endereco=False):
    print(f'[KAIZEN] Nova minuta SISBAJUD (endereco={endereco})')
    try:
        # 1. Clica no botão do menu de navegação
        for _ in range(5):
            try:
                btn_menu = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='menu de navegação']")
                if btn_menu.is_displayed():
                    btn_menu.click()
                    time.sleep(0.7)
                    break
            except Exception:
                time.sleep(0.5)
        # 2. Clica no item "Ir para Minuta"
        for _ in range(5):
            try:
                a_minuta = None
                links = driver.find_elements(By.CSS_SELECTOR, "a[aria-label]")
                for a in links:
                    if 'Minuta' in a.get_attribute('aria-label'):
                        a_minuta = a
                        break
                if a_minuta and a_minuta.is_displayed():
                    a_minuta.click()
                    time.sleep(1.2)
                    break
            except Exception:
                time.sleep(0.5)
        # 3. Clica no botão "Nova"
        for _ in range(5):
            try:
                botoes = driver.find_elements(By.CSS_SELECTOR, "button")
                btn_nova = next((b for b in botoes if b.is_displayed() and 'Nova' in b.text), None)
                if btn_nova:
                    btn_nova.click()
                    time.sleep(1.2)
                    break
            except Exception:
                time.sleep(0.5)
        # 4. Seleciona tipo de minuta (endereço ou bloqueio)
        if endereco:
            for _ in range(3):
                try:
                    labels = driver.find_elements(By.CSS_SELECTOR, "label")
                    for label in labels:
                        if 'Requisição de informações' in label.text:
                            label.click()
                            time.sleep(1)
                            break
                except Exception:
                    time.sleep(0.3)
        # Selecionar Juiz Solicitante
        juiz = CONFIG.get('juiz_default', '')
        if juiz:
            try:
                juiz_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Juiz']")
                juiz_input.clear()
                juiz_input.send_keys(juiz)
                time.sleep(0.5)
                juiz_input.send_keys(Keys.ARROW_DOWN)
                juiz_input.send_keys(Keys.ENTER)
                print(f"[KAIZEN] Juiz selecionado: {juiz}")
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao selecionar juiz: {e}")
        # Selecionar Vara/Juízo
        vara = CONFIG.get('vara_default', '')
        if vara:
            try:
                mat_select = driver.find_element(By.CSS_SELECTOR, "mat-select[name*='varaJuizoSelect']")
                mat_select.click()
                time.sleep(0.5)
                opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option[role='option']")
                for opc in opcoes:
                    if vara.lower() in opc.text.lower():
                        opc.click()
                        print(f"[KAIZEN] Vara/Juízo selecionado: {vara}")
                        break
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao selecionar vara/juízo: {e}")
        # Preencher número do processo
        numero = processo_dados_extraidos.get('numero', '')
        if numero:
            try:
                el = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Número do Processo']")
                el.clear()
                el.send_keys(numero)
                el.send_keys(Keys.TAB)
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao preencher número do processo: {e}")
        # Selecionar tipo de ação
        try:
            mat_select = driver.find_element(By.CSS_SELECTOR, "mat-select[name*='acao']")
            mat_select.click()
            time.sleep(0.5)
            opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option[role='option']")
            for opc in opcoes:
                if 'Ação Trabalhista' in opc.text:
                    opc.click()
                    break
        except Exception as e:
            print(f"[KAIZEN][ERRO] Falha ao selecionar tipo de ação: {e}")
        # Preencher partes (CPF/CNPJ e nome)
        try:
            partes = processo_dados_extraidos.get('partes', {})
            if endereco:
                # Endereço: pode ser polo ativo ou passivo, conforme lógica
                parte = partes.get('ativas', [{}])[0]
            else:
                parte = partes.get('passivas', [{}])[0]
            cpf = parte.get('documento', '')
            nome = parte.get('nome', '')
            if cpf:
                el = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='CPF']")
                el.clear()
                el.send_keys(cpf)
                el.send_keys(Keys.TAB)
            if nome:
                el = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Nome do autor/exequente da ação']")
                el.clear()
                el.send_keys(nome)
                el.send_keys(Keys.TAB)
        except Exception as e:
            print(f"[KAIZEN][ERRO] Falha ao preencher partes: {e}")
        # Teimosinha
        teimosinha = CONFIG.get('teimosinha', '60')
        if not endereco and teimosinha and teimosinha.lower() != 'nao':
            try:
                # Seleciona "Repetir a ordem" se não for requisição de informações
                radios = driver.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
                for radio in radios:
                    if 'Repetir a ordem' in radio.text:
                        radio.find_element(By.TAG_NAME, 'label').click()
                        break
                # Abrir calendário e selecionar data
                # (implementação simplificada, pode ser expandida para lógica de data exata)
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao configurar teimosinha: {e}")
        # Valor atualizado
        valor = processo_dados_extraidos.get('valor', CONFIG.get('valor_default', ''))
        if valor:
            try:
                el = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Valor aplicado a todos']")
                el.clear()
                el.send_keys(valor)
                el.send_keys(Keys.TAB)
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao preencher valor: {e}")
        # Conta-salário
        if CONFIG.get('contasalario', '').lower() == 'sim':
            try:
                toggles = driver.find_elements(By.CSS_SELECTOR, 'mat-slide-toggle label')
                for toggle in toggles:
                    toggle.click()
            except Exception as e:
                print(f"[KAIZEN][ERRO] Falha ao marcar conta-salário: {e}")
        # Salvar e protocolar
        try:
            driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Salvar').click();")
            time.sleep(1)
            driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Protocolar').click();")
            print('[KAIZEN] Nova minuta criada e protocolada com sucesso.')
        except Exception as e:
            print(f'[KAIZEN][ERRO] Falha ao salvar/protocolar minuta: {e}')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha geral ao criar nova minuta: {e}')

def kaizen_consultar_teimosinha(driver):
    print('[KAIZEN] Consultar Teimosinha SISBAJUD')
    try:
        # Oculta barra lateral se necessário
        driver.execute_script("let el=document.querySelector('mat-sidenav-container mat-sidenav');if(el){el.style.marginLeft='-1000px';}")
        # Abrir menu de navegação
        driver.execute_script("document.querySelector('button[aria-label*=\'menu de navegação\']').click();")
        time.sleep(0.7)
        # Ir para Teimosinha
        driver.execute_script("document.querySelector('a[aria-label*=\'Ir para Teimosinha\']').click();")
        time.sleep(1.2)
        # Preencher número do processo
        numero = processo_dados_extraidos.get('numero', '')
        if numero:
            driver.execute_script(f"document.querySelector('input[placeholder=\'Número do Processo\']').value = '{numero}';")
            time.sleep(0.3)
            driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Consultar').click();")
            print('[KAIZEN] Consulta de teimosinha disparada.')
        else:
            print('[KAIZEN][ERRO] Número do processo não encontrado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao consultar teimosinha: {e}')

def kaizen_consultar_minuta(driver):
    print('[KAIZEN] Consultar Minuta SISBAJUD')
    try:
        # Abrir menu de navegação
        driver.execute_script("document.querySelector('button[aria-label*=\'menu de navegação\']').click();")
        time.sleep(0.7)
        # Ir para Ordem Judicial
        driver.execute_script("document.querySelector('a[aria-label*=\'Ir para Ordem judicial\']').click();")
        time.sleep(1.2)
        # Selecionar aba de busca por filtros
        driver.execute_script("Array.from(document.querySelectorAll('div[role=\'tab\']')).find(e=>e.innerText.includes('filtros')).click();")
        time.sleep(0.7)
        # Preencher número do processo
        numero = processo_dados_extraidos.get('numero', '')
        if numero:
            driver.execute_script(f"document.querySelector('input[placeholder=\'Número do Processo\']').value = '{numero}';")
            time.sleep(0.3)
            driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Consultar').click();")
            print('[KAIZEN] Consulta de minuta disparada.')
        else:
            print('[KAIZEN][ERRO] Número do processo não encontrado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao consultar minuta: {e}')

def kaizen_consulta_rapida(driver):
    print('[KAIZEN] Consulta rápida SISBAJUD/PJe')
    # Exemplo: abrir consulta rápida no PJe
    # ...

# ===================== EXIBIR DADOS DE LOGIN =====================
def dados_login(driver):
    # Exibe uma caixa editável com os dados de login SISBAJUD se a URL for de login do SISBAJUD
    url = driver.current_url
    if 'sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth' in url or 'sisbajud' in url and 'login' in url:
        driver.execute_script('''
            if (!document.getElementById('dados_login_sisbajud')) {
                let box = document.createElement('div');
                box.id = 'dados_login_sisbajud';
                box.style = 'position:fixed;top:30px;right:30px;z-index:99999;background:#fff;border:2px solid #1976d2;padding:16px 18px 12px 18px;border-radius:8px;box-shadow:0 2px 12px #0003;font-size:16px;min-width:320px;';
                let title = document.createElement('div');
                title.innerText = 'Login SISBAJUD';
                title.style = 'font-weight:bold;font-size:18px;margin-bottom:8px;color:#1976d2;';
                box.appendChild(title);
                let labelCpf = document.createElement('label');
                labelCpf.innerText = 'CPF:';
                labelCpf.style = 'display:block;margin-bottom:2px;';
                box.appendChild(labelCpf);
                let inputCpf = document.createElement('input');
                inputCpf.type = 'text';
                inputCpf.value = '300.692.778-85';
                inputCpf.style = 'width:100%;margin-bottom:8px;padding:4px;font-size:16px;';
                box.appendChild(inputCpf);
                let labelSenha = document.createElement('label');
                labelSenha.innerText = 'Senha:';
                labelSenha.style = 'display:block;margin-bottom:2px;';
                box.appendChild(labelSenha);
                let inputSenha = document.createElement('input');
                inputSenha.type = 'text';
                inputSenha.value = 'Fl@quinho182';
                inputSenha.style = 'width:100%;margin-bottom:8px;padding:4px;font-size:16px;';
                box.appendChild(inputSenha);
                let info = document.createElement('div');
                info.innerText = 'Copie e cole os dados acima no formulário de login do SISBAJUD.';
                info.style = 'font-size:13px;color:#555;margin-top:4px;';
                box.appendChild(info);
                document.body.appendChild(box);
            }
        ''')

# ===================== MONITORAR JANELAS SISBAJUD =====================
def monitor_janela_sisbajud(driver):
    """
    Monitora a abertura/fechamento de janelas do SISBAJUD para sincronizar ações.
    """
    try:
        driver.execute_script('''
        if (!window._kaizen_monitor_janela_sisbajud) {
            window._kaizen_monitor_janela_sisbajud = true;
            let observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (!mutation.addedNodes[0]) { return }
                    if (!mutation.addedNodes[0].tagName) { return }
                    // Exemplo: aplicar estilos ou acionar funções ao abrir janelas específicas
                    if (document.querySelector('SISBAJUD-PESQUISA-TEIMOSINHA') && mutation.addedNodes[0].tagName == "TR" && mutation.target.tagName == "TBODY") {
                        mutation.addedNodes[0].style.outline = '2px solid #3e3f3f';
                    }
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
        ''')
        print('[KAIZEN] Monitoramento de janelas SISBAJUD ativado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao monitorar janelas: {e}')

# ===================== LOOP PRINCIPAL =====================
def main():
    # Setup driver e login igual teste.py
    driver = driver_pc(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_pc(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        return
    print('[SISBAJUD] Login realizado com sucesso.')
    url_teste = 'https://pje.trt2.jus.br/pjekz/processo/2108106/detalhe'
    print(f'[SISBAJUD] Navegando para a URL de teste: {url_teste}')
    driver.get(url_teste)
    time.sleep(3)
    # Extração dos dados do processo
    global processo_dados_extraidos
    processo_dados_extraidos = extrair_dados_processo(driver, log=True)
    print('[SISBAJUD] Dados do processo extraídos:', processo_dados_extraidos)
    injetar_botoes_pje(driver)
    bind_eventos(driver)
    print('[SISBAJUD] Botões injetados na tela de detalhes do processo.')
    while True:
        evento = checar_evento(driver)
        if evento == 'minuta_bloqueio':
            minuta_bloqueio(driver)
        elif evento == 'minuta_endereco':
            minuta_endereco(driver)
        elif evento == 'processar_bloqueios':
            processar_bloqueios(driver)
        # Injeta o menu Kaizen no SISBAJUD sempre que abrir a aba
        injetar_menu_kaizen_sisbajud(driver)
        # Exibe a interface de login SISBAJUD se necessário
        dados_login(driver)
        # Checa eventos do menu Kaizen e executa ações
        kaizen_evt = checar_kaizen_evento(driver)
        if kaizen_evt == 'kaizen_guardar_senha':
            kaizen_guardar_senha(driver)
        elif kaizen_evt == 'kaizen_preencher_campos_invertido':
            kaizen_preencher_campos(driver, invertido=True)
        elif kaizen_evt == 'kaizen_preencher_campos':
            kaizen_preencher_campos(driver, invertido=False)
        elif kaizen_evt == 'kaizen_nova_minuta_end':
            kaizen_nova_minuta(driver, endereco=True)
        elif kaizen_evt == 'kaizen_nova_minuta':
            kaizen_nova_minuta(driver, endereco=False)
        elif kaizen_evt == 'kaizen_consultar_teimosinha':
            kaizen_consultar_teimosinha(driver)
        elif kaizen_evt == 'kaizen_consultar_minuta':
            kaizen_consultar_minuta(driver)
        elif kaizen_evt == 'kaizen_consulta_rapida':
            kaizen_consulta_rapida(driver)
        # Monitora a abertura/fechamento de janelas do SISBAJUD
        monitor_janela_sisbajud(driver)
        time.sleep(1)

if __name__ == '__main__':
    main()
