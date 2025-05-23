# bacen.py
# Automação SISBAJUD/BACEN integrada ao PJe, com suporte a Firefox (login inicial) e Thorium/Chrome (acesso SISBAJUD)
# Baseado em sisbajud.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from Fix import driver_pc, login_pc, extrair_dados_processo
import subprocess
import os

# ===================== CONFIGURAÇÕES =====================
CONFIG = {
    'cor_bloqueio_positivo': '#32cd32',
    'cor_bloqueio_negativo': '#ff6347',
    'acao_automatica': 'transferir',
    'banco_preferido': 'Banco do Brasil',
    'agencia_preferida': '5905',
    'teimosinha': '60',
    'nome_default': '',
    'documento_default': '',
    'valor_default': '',
}

processo_dados_extraidos = None
login_ahk_executado = False

# ===================== INJETAR BOTÕES NO PJe =====================
def injetar_botoes_pje(driver):
    driver.execute_script("""
        if (!document.getElementById('btn_minuta_bloqueio')) {
            let container = document.createElement('div');
            container.id = 'sisbajud_btn_container';
            container.style = 'position:fixed;top:60px;right:20px;z-index:9999;background:#fff;padding:8px;border-radius:8px;box-shadow:0 2px 8px #0002;';
            let btn1 = document.createElement('button');
            btn1.id = 'btn_minuta_bloqueio';
            btn1.innerText = 'Minuta de Bloqueio';
            btn1.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn1.onclick = function() { window.dispatchEvent(new CustomEvent('minuta_bloqueio')); };
            container.appendChild(btn1);
            let btn2 = document.createElement('button');
            btn2.id = 'btn_minuta_endereco';
            btn2.innerText = 'Minuta de Endereço';
            btn2.style = 'margin:4px;padding:6px 14px;cursor:pointer;';
            btn2.onclick = function() { window.dispatchEvent(new CustomEvent('minuta_endereco')); };
            container.appendChild(btn2);
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
    return driver.execute_script(f"return prompt('{mensagem.replace("'", "\\'")}', '{valor_padrao}');")

# ===================== ACIONADORES DE EVENTOS =====================
def bind_eventos(driver):
    driver.execute_script("window.sisbajud_event_flag = '';")
    driver.execute_script("""
        window.addEventListener('minuta_bloqueio', function() { window.sisbajud_event_flag = 'minuta_bloqueio'; });
        window.addEventListener('minuta_endereco', function() { window.sisbajud_event_flag = 'minuta_endereco'; });
        window.addEventListener('processar_bloqueios', function() { window.sisbajud_event_flag = 'processar_bloqueios'; });
    """)

def checar_evento(driver):
    flag = driver.execute_script("return window.sisbajud_event_flag;")
    if flag:
        driver.execute_script("window.sisbajud_event_flag = '';")
    return flag

# ===================== FLUXOS DE AUTOMAÇÃO BACEN/SISBAJUD =====================
def salvar_cookies_sisbajud(driver, caminho='cookies_sisbajud.json'):
    import json
    cookies = driver.get_cookies()
    cookies_filtrados = [c for c in cookies if 'sisbajud.cloud.pje.jus.br' in c.get('domain', '')]
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(cookies_filtrados, f, ensure_ascii=False, indent=2)
    print(f'[BACEN] Cookies SISBAJUD salvos em {caminho}.')

def driver_firefox_sisbajud(headless=False):
    """
    Retorna um driver Firefox usando o perfil dedicado do SISBAJUD.
    """
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import os
    profile_path = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\arrn673i.Sisb'
    firefox_binary = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
    geckodriver_path = r'd:\PjePlus\geckodriver.exe'
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.binary_location = firefox_binary
    options.set_preference('profile', profile_path)
    service = Service(executable_path=geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)
    return driver

def abrir_sisbajud_em_firefox_sisbajud():
    driver = driver_firefox_sisbajud(headless=False)
    driver.get('https://sisbajud.cnj.jus.br/')
    print('[BACEN] SISBAJUD aberto em Firefox (perfil Sisb).')
    return driver

def minuta_bloqueio(driver):
    sisbajud_driver = abrir_sisbajud_em_firefox_sisbajud()
    injetar_menu_kaizen_sisbajud(sisbajud_driver)
    dados_login(sisbajud_driver)
    print('[BACEN] Minuta de bloqueio: automação disponível na janela Firefox SISBAJUD.')

def minuta_endereco(driver):
    sisbajud_driver = abrir_sisbajud_em_firefox_sisbajud()
    injetar_menu_kaizen_sisbajud(sisbajud_driver)
    dados_login(sisbajud_driver)
    print('[BACEN] Minuta de endereço: automação disponível na janela Firefox SISBAJUD.')

def processar_bloqueios(driver):
    sisbajud_driver = abrir_sisbajud_em_firefox_sisbajud()
    injetar_menu_kaizen_sisbajud(sisbajud_driver)
    dados_login(sisbajud_driver)
    print('[BACEN] Processamento de bloqueios: automação disponível na janela Firefox SISBAJUD.')

# ===================== INJETAR MENU KAIZEN NO SISBAJUD =====================
def injetar_menu_kaizen_sisbajud(driver):
    """
    Injeta um menu Kaizen flutuante, horizontal, pequeno, no canto inferior direito da tela do SISBAJUD.
    """
    driver.execute_script('''
        let old = document.getElementById('kaizen_menu_sisbajud');
        if (old) old.remove();
        let menu = document.createElement('div');
        menu.id = 'kaizen_menu_sisbajud';
        menu.style = `
            position: fixed;
            bottom: 18px;
            right: 18px;
            z-index: 2147483647;
            background: #111;
            border: 2px solid #1976d2;
            border-radius: 10px;
            box-shadow: 0 4px 16px #0008;
            padding: 7px 10px 7px 14px;
            min-width: unset;
            font-family: Arial, sans-serif;
            opacity: 0.97;
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 8px;
            transform: scale(0.65);
            transform-origin: bottom right;
        `;
        let title = document.createElement('div');
        title.innerText = 'KAIZEN SISBAJUD';
        title.style = 'font-weight:bold;font-size:13px;margin-right:10px;color:#fff;text-align:center;letter-spacing:1px;';
        menu.appendChild(title);
        const botoes = [
            ['Nova Minuta', 'kaizen_nova_minuta', '#1976d2'],
            ['Minuta Endereço', 'kaizen_nova_minuta_end', '#009688'],
            ['Teimosinha', 'kaizen_consultar_teimosinha', '#e65100'],
            ['Minuta', 'kaizen_consultar_minuta', '#6d4c41'],
            ['Rápida', 'kaizen_consulta_rapida', '#512da8'],
            ['Polo Ativo', 'kaizen_preencher_campos_invertido', '#388e3c'],
            ['Polo Passivo', 'kaizen_preencher_campos', '#c62828'],
        ];
        for (let [texto, evento, cor] of botoes) {
            let btn = document.createElement('button');
            btn.innerText = texto;
            btn.style = `
                display: inline-block;
                margin: 0 2px;
                padding: 8px 14px;
                background: ${cor};
                color: #fff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 1px 4px #0002;
                transition: background 0.2s;
            `;
            btn.addEventListener('mouseover', function() { btn.style.background = '#333'; });
            btn.addEventListener('mouseout', function() { btn.style.background = cor; });
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                window.dispatchEvent(new CustomEvent(evento));
            });
            menu.appendChild(btn);
        }
        document.body.appendChild(menu);
        // Listeners Kaizen
        if (!window.kaizen_event_flag) {
            window.kaizen_event_flag = '';
            const kaizen_events = [
                'kaizen_nova_minuta',
                'kaizen_nova_minuta_end',
                'kaizen_consultar_teimosinha',
                'kaizen_consultar_minuta',
                'kaizen_consulta_rapida',
                'kaizen_preencher_campos_invertido',
                'kaizen_preencher_campos',
            ];
            for (let evt of kaizen_events) {
                window.addEventListener(evt, function(){ window.kaizen_event_flag = evt; });
            }
        }
    ''')

def checar_kaizen_evento(driver):
    flag = driver.execute_script("return window.kaizen_event_flag;")
    if flag:
        driver.execute_script("window.kaizen_event_flag = '';")
    return flag

# ===================== AÇÕES DOS BOTÕES KAIZEN =====================
def kaizen_guardar_senha(driver):
    print('[KAIZEN] Guardar Senha: (ação não implementada, placeholder)')

def kaizen_preencher_campos(driver, invertido=False):
    global processo_dados_extraidos
    print(f'[KAIZEN] Preencher campos SISBAJUD (invertido={invertido})')
    if not processo_dados_extraidos:
        print('[KAIZEN][ERRO] Dados do processo não extraídos. Abortando preenchimento.')
        return
    campos_necessarios = {}
    if invertido:
        partes = processo_dados_extraidos.get('partes', {}).get('ativas', [])
    else:
        partes = processo_dados_extraidos.get('partes', {}).get('passivas', [])
    if partes and len(partes) > 0:
        campos_necessarios['nome'] = partes[0].get('nome', '')
        campos_necessarios['documento'] = partes[0].get('documento', '')
    else:
        campos_necessarios['nome'] = CONFIG.get('nome_default', '')
        campos_necessarios['documento'] = CONFIG.get('documento_default', '')
    campos_necessarios['valor'] = CONFIG.get('valor_default', '')
    try:
        nome = campos_necessarios['nome'].replace("'", "\\'").replace('"', '\\"')
        documento = campos_necessarios['documento'].replace("'", "\\'").replace('"', '\\"')
        valor = campos_necessarios['valor'].replace("'", "\\'").replace('"', '\\"')
        driver.execute_script("var inp=document.querySelector(\"input[placeholder='Nome']\"); if(inp) inp.value=arguments[0];", nome)
        driver.execute_script("var inp=document.querySelector(\"input[placeholder='Documento']\"); if(inp) inp.value=arguments[0];", documento)
        driver.execute_script("var inp=document.querySelector(\"input[placeholder='Valor']\"); if(inp) inp.value=arguments[0];", valor)
        print(f"[KAIZEN] Campos preenchidos: {campos_necessarios}")
        if not campos_necessarios['nome'] or not campos_necessarios['documento'] or not campos_necessarios['valor']:
            print('[KAIZEN][ATENÇÃO] Preencha os campos essenciais em CONFIG caso estejam vazios: nome_default, documento_default, valor_default.')
    except Exception as e:
        print(f"[KAIZEN][ERRO] Falha ao preencher campos no formulário SISBAJUD: {e}")

def kaizen_nova_minuta(driver, endereco=False):
    print(f'[KAIZEN] Nova minuta SISBAJUD (endereco={endereco})')
    try:
        # Aguarda a página de minuta carregar
        for _ in range(20):
            if 'minuta' in driver.current_url:
                break
            time.sleep(0.3)
        else:
            print('[KAIZEN][ERRO] Página de minuta não carregada.')
            return
        # Clicar diretamente no botão "Nova"
        for _ in range(15):
            btn_nova = driver.execute_script("return Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Nova');")
            if btn_nova:
                driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Nova').click();")
                time.sleep(1.2)
                break
            time.sleep(0.3)
        else:
            print('[KAIZEN][ERRO] Botão Nova não encontrado.')
            return
        # Se for minuta de endereço, clicar na opção correta
        if endereco:
            for _ in range(10):
                lbl = driver.execute_script("return Array.from(document.querySelectorAll('label')).find(e=>e.innerText && e.innerText.includes('Requisição de informações'));")
                if lbl:
                    driver.execute_script("Array.from(document.querySelectorAll('label')).find(e=>e.innerText && e.innerText.includes('Requisição de informações')).click();")
                    time.sleep(0.7)
                    break
                time.sleep(0.3)
        # Preencher campos principais
        kaizen_preencher_campos(driver, invertido=endereco)
        # Selecionar banco/agência
        escolher_opcao_sisbajud(driver, "mat-select[name*='banco']", CONFIG.get('banco_preferido', ''))
        escolher_opcao_sisbajud(driver, "mat-select[name*='agencia']", CONFIG.get('agencia_preferida', ''))
        # Tratar teimosinha
        if not endereco and CONFIG.get('teimosinha', '').lower() != 'nao':
            try:
                for _ in range(5):
                    radio = driver.execute_script("return Array.from(document.querySelectorAll('mat-radio-button')).find(e=>e.innerText && e.innerText.includes('Repetir a ordem'));")
                    if radio and radio.querySelector('label'):
                        driver.execute_script("arguments[0].querySelector('label').click();", radio)
                        time.sleep(0.5)
                        break
                    time.sleep(0.3)
            except Exception:
                pass
        # Salvar e protocolar
        for _ in range(10):
            btn_salvar = driver.execute_script("return Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Salvar');")
            if btn_salvar:
                driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Salvar').click();")
                time.sleep(1)
                break
            time.sleep(0.3)
        for _ in range(10):
            btn_protocolar = driver.execute_script("return Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Protocolar');")
            if btn_protocolar:
                driver.execute_script("Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Protocolar').click();")
                print('[KAIZEN] Nova minuta criada e protocolada com sucesso.')
                break
            time.sleep(0.3)
        else:
            print('[KAIZEN][ERRO] Botão Protocolar não encontrado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao criar nova minuta: {e}')

def kaizen_consultar_minuta(driver):
    print('[KAIZEN] Consultar Minuta SISBAJUD')
    try:
        driver.execute_script("var btn = document.querySelector(\"button[aria-label*='menu de navegação']\"); if(btn) btn.click();")
        time.sleep(0.7)
        driver.execute_script("var link = document.querySelector(\"a[aria-label*='Ir para Ordem judicial']\"); if(link) link.click();")
        time.sleep(1.2)
        driver.execute_script("var tab = Array.from(document.querySelectorAll(\"div[role='tab']\")).find(e=>e.innerText.includes('filtros')); if(tab) tab.click();")
        time.sleep(0.7)
        numero = processo_dados_extraidos.get('numero', '')
        if numero:
            numero = numero.replace("'", "\\'").replace('"', '\\"')
            driver.execute_script("var inp = document.querySelector(\"input[placeholder='Número do Processo']\"); if(inp) inp.value = arguments[0];", numero)
            time.sleep(0.3)
            driver.execute_script("var btn = Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Consultar'); if(btn) btn.click();")
            print('[KAIZEN] Consulta de minuta disparada.')
        else:
            print('[KAIZEN][ERRO] Número do processo não encontrado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao consultar minuta: {e}')

def kaizen_consultar_teimosinha(driver):
    print('[KAIZEN] Consultar Teimosinha SISBAJUD')
    try:
        driver.execute_script("let el=document.querySelector('mat-sidenav-container mat-sidenav');if(el){el.style.marginLeft='-1000px';}")
        driver.execute_script("var btn = document.querySelector(\"button[aria-label*='menu de navegação']\"); if(btn) btn.click();")
        time.sleep(0.7)
        driver.execute_script("var link = document.querySelector(\"a[aria-label*='Ir para Teimosinha']\"); if(link) link.click();")
        time.sleep(1.2)
        numero = processo_dados_extraidos.get('numero', '')
        if numero:
            numero = numero.replace("'", "\\'").replace('"', '\\"')
            driver.execute_script("var inp = document.querySelector(\"input[placeholder='Número do Processo']\"); if(inp) inp.value = arguments[0];", numero)
            time.sleep(0.3)
            driver.execute_script("var btn = Array.from(document.querySelectorAll('button')).find(e=>e.innerText=='Consultar'); if(btn) btn.click();")
            print('[KAIZEN] Consulta de teimosinha disparada.')
        else:
            print('[KAIZEN][ERRO] Número do processo não encontrado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao consultar teimosinha: {e}')

def escolher_opcao_sisbajud(driver, seletor, valor):
    try:
        # Espera até 5s pelo elemento
        for _ in range(10):
            try:
                el = driver.find_element(By.CSS_SELECTOR, seletor)
                break
            except Exception:
                time.sleep(0.5)
        else:
            print(f'[KAIZEN][ERRO] Opção "{valor}" não encontrada em {seletor} (elemento não existe)')
            return False
        el.click()
        time.sleep(0.5)
        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"], option')
        for opc in opcoes:
            if valor.lower() in opc.text.lower():
                opc.click()
                print(f'[KAIZEN] Opção "{valor}" selecionada em {seletor}')
                return True
        print(f'[KAIZEN][ERRO] Opção "{valor}" não encontrada em {seletor} (nenhuma opção corresponde)')
        return False
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao selecionar opção: {e}')
        return False

def monitor_janela_sisbajud(driver):
    try:
        driver.execute_script('''
        if (!window._kaizen_monitor_janela_sisbajud) {
            window._kaizen_monitor_janela_sisbajud = true;
            let observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (!mutation.addedNodes[0]) { return }
                    if (!mutation.addedNodes[0].tagName) { return }
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

def kaizen_consulta_rapida(driver):
    print('[KAIZEN] Consulta rápida SISBAJUD/PJe')
    # Implemente aqui se desejar automação específica

# ===================== EXIBIR DADOS DE LOGIN =====================
def dados_login(driver):
    url = driver.current_url
    if 'sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth' in url or 'sisbajud' in url and 'login' in url:
        driver.execute_script('''
            if (!document.getElementById('dados_login_sisbajud')) {
                let box = document.createElement('div');
                box.id = 'dados_login_sisbajud';
                box.style = 'position:fixed;bottom:30px;left:30px;z-index:99999;background:#fff;border:2px solid #1976d2;padding:10px 12px 8px 12px;border-radius:8px;box-shadow:0 2px 12px #0003;font-size:10px;min-width:192px;transform:scale(0.78);transform-origin:bottom left;';
                let title = document.createElement('div');
                title.innerText = 'Login SISBAJUD';
                title.style = 'font-weight:bold;font-size:12px;margin-bottom:6px;color:#1976d2;';
                box.appendChild(title);
                let labelCpf = document.createElement('label');
                labelCpf.innerText = 'CPF:';
                labelCpf.style = 'display:block;margin-bottom:2px;';
                box.appendChild(labelCpf);
                let inputCpf = document.createElement('input');
                inputCpf.type = 'text';
                inputCpf.value = '300.692.778-85';
                inputCpf.style = 'width:100%;margin-bottom:6px;padding:2px;font-size:10px;';
                box.appendChild(inputCpf);
                let btnCpf = document.createElement('button');
                btnCpf.innerText = 'Copiar CPF';
                btnCpf.style = 'margin-bottom:6px;padding:2px 8px;font-size:10px;cursor:pointer;background:#1976d2;color:#fff;border:none;border-radius:4px;';
                btnCpf.onclick = function() { navigator.clipboard.writeText(inputCpf.value); };
                box.appendChild(btnCpf);
                let labelSenha = document.createElement('label');
                labelSenha.innerText = 'Senha:';
                labelSenha.style = 'display:block;margin-bottom:2px;';
                box.appendChild(labelSenha);
                let inputSenha = document.createElement('input');
                inputSenha.type = 'text';
                inputSenha.value = 'Fl@quinho182';
                inputSenha.style = 'width:100%;margin-bottom:6px;padding:2px;font-size:10px;';
                box.appendChild(inputSenha);
                let btnSenha = document.createElement('button');
                btnSenha.innerText = 'Copiar Senha';
                btnSenha.style = 'margin-bottom:6px;padding:2px 8px;font-size:10px;cursor:pointer;background:#1976d2;color:#fff;border:none;border-radius:4px;';
                btnSenha.onclick = function() { navigator.clipboard.writeText(inputSenha.value); };
                box.appendChild(btnSenha);
                // Botão adicional: Copiar Ambos (CPF e Senha)
                let btnAmbos = document.createElement('button');
                btnAmbos.innerText = 'Copiar Ambos';
                btnAmbos.style = 'margin-bottom:6px;padding:2px 8px;font-size:10px;cursor:pointer;background:#388e3c;color:#fff;border:none;border-radius:4px;margin-left:6px;';
                btnAmbos.onclick = function() { navigator.clipboard.writeText(inputCpf.value + '\t' + inputSenha.value); };
                box.appendChild(btnAmbos);
                let info = document.createElement('div');
                info.innerText = 'Copie e cole os dados acima no formulário de login do SISBAJUD.';
                info.style = 'font-size:9px;color:#555;margin-top:2px;';
                box.appendChild(info);
                document.body.appendChild(box);
            }
        ''')

# ===================== LOOP PRINCIPAL =====================
def main():
    driver = driver_pc(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_pc(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        return
    print('[BACEN] Login realizado com sucesso (Firefox).')
    url_teste = 'https://pje.trt2.jus.br/pjekz/processo/2108106/detalhe'
    print(f'[BACEN] Navegando para a URL de teste: {url_teste}')
    driver.get(url_teste)
    time.sleep(3)
    global processo_dados_extraidos
    processo_dados_extraidos = extrair_dados_processo(driver, log=True)
    print('[BACEN] Dados do processo extraídos:', processo_dados_extraidos)
    injetar_botoes_pje(driver)
    bind_eventos(driver)
    print('[BACEN] Botões injetados na tela de detalhes do processo.')
    while True:
        evento = checar_evento(driver)
        if evento == 'minuta_bloqueio':
            driver = abrir_sisbajud_em_firefox_sisbajud()
            injetar_menu_kaizen_sisbajud(driver)
            dados_login(driver)
            print('[BACEN] Controle transferido para janela SISBAJUD (perfil Sisb).')
            break
        elif evento == 'minuta_endereco':
            driver = abrir_sisbajud_em_firefox_sisbajud()
            injetar_menu_kaizen_sisbajud(driver)
            dados_login(driver)
            print('[BACEN] Controle transferido para janela SISBAJUD (perfil Sisb).')
            break
        elif evento == 'processar_bloqueios':
            driver = abrir_sisbajud_em_firefox_sisbajud()
            injetar_menu_kaizen_sisbajud(driver)
            dados_login(driver)
            print('[BACEN] Controle transferido para janela SISBAJUD (perfil Sisb).')
            break
        time.sleep(1)
    # Novo loop: todas as ações Kaizen agora ocorrem no novo driver SISBAJUD
    while True:
        injetar_menu_kaizen_sisbajud(driver)
        dados_login(driver)
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
        time.sleep(1)

if __name__ == '__main__':
    main()
