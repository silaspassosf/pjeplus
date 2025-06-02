# bacen.py
# Automação SISBAJUD/BACEN integrada ao PJe, com suporte a Firefox (login inicial) e Thorium/Chrome (acesso SISBAJUD)
# Baseado em sisbajud.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from Fix import driver_pc, login_pc, extrair_dados_processo
import subprocess
import os
import json
import tempfile

# ===================== CONFIGURAÇÕES =====================
CONFIG = {
    'cor_bloqueio_positivo': '#32cd32',
    'cor_bloqueio_negativo': '#ff6347',
    'acao_automatica': 'transferir',
    'banco_preferido': 'Banco do Brasil',
    'agencia_preferida': '5905',
    'teimosinha': '60',
    'nome_default': '',
    'documento_default': '',    'valor_default': '',
    'juiz_default': 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA',
    'vara_default': '3006',
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

def salvar_dados_processo_temp():
    """
    Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas
    """
    global processo_dados_extraidos
    if processo_dados_extraidos:
        try:
            # Usa caminho do projeto ao invés de pasta temporária
            import os
            project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o bacen.py
            dados_path = os.path.join(project_path, 'dadosatuais.json')
            
            # Sempre sobrescreve o arquivo para não acumular dados de múltiplos processos
            with open(dados_path, 'w', encoding='utf-8') as f:
                json.dump(processo_dados_extraidos, f, ensure_ascii=False, indent=2)
            print(f'[BACEN] Dados do processo salvos em: {dados_path}')
        except Exception as e:
            print(f'[BACEN][ERRO] Falha ao salvar dados do processo: {e}')

def abrir_sisbajud_em_firefox_sisbajud():
    driver = driver_firefox_sisbajud(headless=False)
    driver.get('https://sisbajud.cnj.jus.br/')
    print('[BACEN] SISBAJUD aberto em Firefox (perfil Sisb).')    # Integração: carrega dados extraídos do processo do arquivo do projeto
    global processo_dados_extraidos
    try:
        # Usa caminho do projeto ao invés de pasta temporária
        import os
        project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o bacen.py
        dados_path = os.path.join(project_path, 'dadosatuais.json')
        
        if os.path.exists(dados_path):
            with open(dados_path, 'r', encoding='utf-8') as f:
                processo_dados_extraidos = json.load(f)
            print('[BACEN] Dados do processo carregados do arquivo:', processo_dados_extraidos)
        else:
            print('[BACEN][ERRO] Arquivo de dados do processo não encontrado.')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao carregar dados do processo do arquivo temporário: {e}')
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
    Versão robusta que funciona mesmo após login/navegação.
    """
    print('[KAIZEN] Injetando menu SISBAJUD...')
    
    # Aguardar página estar pronta
    try:
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)  # Tempo extra para elementos dinâmicos
    except:
        print('[KAIZEN] Timeout aguardando página, continuando...')
    
    driver.execute_script('''
        function injetarMenuKaizen() {
            console.log('[KAIZEN] Iniciando injeção do menu...');
            
            // Remover menu existente se houver
            let old = document.getElementById('kaizen_menu_sisbajud');
            if (old) {
                old.remove();
                console.log('[KAIZEN] Menu antigo removido');
            }
            
            let menu = document.createElement('div');
            menu.id = 'kaizen_menu_sisbajud';
            menu.style = `
                position: fixed !important;
                bottom: 18px !important;
                right: 18px !important;
                z-index: 2147483647 !important;
                background: #111 !important;
                border: 2px solid #1976d2 !important;
                border-radius: 10px !important;
                box-shadow: 0 4px 16px #0008 !important;
                padding: 7px 10px 7px 14px !important;
                min-width: unset !important;
                font-family: Arial, sans-serif !important;
                opacity: 0.97 !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                gap: 8px !important;
                transform: scale(0.65) !important;
                transform-origin: bottom right !important;
            `;
            
            let title = document.createElement('div');
            title.innerText = 'KAIZEN SISBAJUD';
            title.style = 'font-weight:bold;font-size:13px;margin-right:10px;color:#fff;text-align:center;letter-spacing:1px;';
            menu.appendChild(title);
            
            const botoes = [
                ['Passivo (Bloqueio)', 'kaizen_minuta_bloqueio_passivo', '#c62828'],
                ['Passivo (Endereço)', 'kaizen_minuta_endereco_passivo', '#009688'],
                ['Autor (Bloqueio)', 'kaizen_minuta_bloqueio_ativo', '#388e3c'],
                ['Consultar Teimosinha', 'kaizen_consultar_teimosinha', '#e65100']
            ];
            
            for (let [texto, evento, cor] of botoes) {
                let btn = document.createElement('button');
                btn.innerText = texto;
                btn.style = `
                    display: inline-block !important;
                    margin: 0 2px !important;
                    padding: 8px 14px !important;
                    background: ${cor} !important;
                    color: #fff !important;
                    border: none !important;
                    border-radius: 6px !important;
                    font-size: 13px !important;
                    font-weight: bold !important;
                    cursor: pointer !important;
                    box-shadow: 0 1px 4px #0002 !important;
                `;
                
                // Apenas clique - sem ações de hover para simplicidade
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    console.log('[KAIZEN] Clique em botão:', evento);
                    window.dispatchEvent(new CustomEvent(evento));
                });
                menu.appendChild(btn);
            }
            
            // Adicionar ao body
            document.body.appendChild(menu);
            console.log('[KAIZEN] Menu SISBAJUD injetado com sucesso');
            
            return true;
        }
        
        // Aguardar DOM estar pronto e então injetar
        if (document.readyState !== 'complete') {
            console.log('[KAIZEN] Aguardando DOM ficar pronto...');
            window.addEventListener('load', function() {
                setTimeout(function() {
                    injetarMenuKaizen();
                }, 1000);
            });
            
            // Fallback se load não disparar
            if (document.readyState === 'interactive') {
                setTimeout(function() {
                    if (!document.getElementById('kaizen_menu_sisbajud')) {
                        injetarMenuKaizen();
                    }
                }, 2000);
            }
        } else {
            injetarMenuKaizen();
        }
        
        // Inicializar listeners Kaizen se ainda não existem
        if (!window.kaizen_event_flag) {
            window.kaizen_event_flag = '';
            const kaizen_events = [
                'kaizen_minuta_bloqueio_passivo',
                'kaizen_minuta_endereco_passivo',
                'kaizen_minuta_bloqueio_ativo',
                'kaizen_consultar_teimosinha'
            ];
            for (let evt of kaizen_events) {
                window.addEventListener(evt, function(){ 
                    console.log('[KAIZEN] Evento capturado:', evt);
                    window.kaizen_event_flag = evt; 
                });
            }
            console.log('[KAIZEN] Event listeners registrados');
        }
    ''')
      # Verificar se o menu foi injetado
    time.sleep(1)
    menu_presente = driver.execute_script("return !!document.getElementById('kaizen_menu_sisbajud');")
    if menu_presente:
        print('[KAIZEN] ✅ Menu SISBAJUD injetado com sucesso!')
    else:
        print('[KAIZEN] ❌ Falha na injeção do menu SISBAJUD')
    
    return menu_presente

def checar_kaizen_evento(driver):
    flag = driver.execute_script("return window.kaizen_event_flag;")
    if flag:
        driver.execute_script("window.kaizen_event_flag = '';")
    return flag

def aguardar_tela_minuta_e_injetar_menu(driver):
    """
    Aguarda a tela de minuta aparecer após login e injeta o menu Kaizen.
    Estratégia focada: injeção robusta inicial ao invés de re-injeção constante.
    """
    print('[KAIZEN] Aguardando tela de minuta para injetar menu...')
    
    try:
        # Aguardar até estar na tela de minuta (após login)
        timeout = 30  # 30 segundos de timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_url = driver.current_url
            
            # Verificar se está numa tela de minuta do SISBAJUD
            if any(path in current_url for path in ['/minuta', '/cadastrar', '/nova-minuta']):
                print(f'[KAIZEN] Tela de minuta detectada: {current_url}')
                
                # Aguardar página estar completamente carregada
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Aguardar elementos específicos do SISBAJUD aparecerem
                for tentativa in range(10):
                    try:
                        # Verificar se elementos típicos da tela de minuta estão presentes
                        elementos_presentes = driver.execute_script("""
                            return !!(
                                document.querySelector('input[placeholder*="Juiz"]') ||
                                document.querySelector('mat-select[name*="varaJuizoSelect"]') ||
                                document.querySelector('input[placeholder="Número do Processo"]') ||
                                document.querySelector('sisbajud-nova-minuta') ||
                                document.querySelector('.nova-minuta')
                            );
                        """)
                        
                        if elementos_presentes:
                            print(f'[KAIZEN] Elementos da tela de minuta carregados (tentativa {tentativa + 1})')
                            time.sleep(2)  # Aguardar estabilização
                            
                            # Injetar menu com retry
                            for tentativa_injecao in range(3):
                                if injetar_menu_kaizen_sisbajud(driver):
                                    print(f'[KAIZEN] ✅ Menu injetado com sucesso na tela de minuta')
                                    return True
                                time.sleep(1)
                            
                            print('[KAIZEN] ❌ Falha ao injetar menu após múltiplas tentativas')
                            return False
                        
                    except Exception as e:
                        print(f'[KAIZEN] Erro verificando elementos da tela (tentativa {tentativa + 1}): {e}')
                    
                    time.sleep(1)
                
                print('[KAIZEN] ❌ Timeout aguardando elementos da tela de minuta')
                return False
            
            time.sleep(1)
        
        print('[KAIZEN] ❌ Timeout aguardando tela de minuta')
        return False
        
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao aguardar tela de minuta: {e}')
        return False

# ===================== AÇÕES DOS BOTÕES KAIZEN =====================
def kaizen_guardar_senha(driver):
    print('[KAIZEN] Guardar Senha: (ação não implementada, placeholder)')

def kaizen_preencher_campos(driver, invertido=False):
    """
    Implementação fiel à função preenchercamposSisbajud do gigs-plugin.js
    Reproduz a sequência exata de ações: Juiz -> Vara -> Processo -> Tipo Ação -> CPF Autor -> Nome Autor -> Teimosinha
    """
    global processo_dados_extraidos
    print(f'[KAIZEN] Preencher campos SISBAJUD (invertido={invertido}) - Sequência completa')
    
    if not processo_dados_extraidos:
        print('[KAIZEN][ERRO] Dados do processo não extraídos. Abortando preenchimento.')
        return
    
    try:
        # Verificar se estamos na página correta (cadastrar minuta)
        # Ajuste para URLs mais genéricas de nova minuta
        current_url = driver.current_url
        if not ('/minuta/cadastrar' in current_url or '/minuta/nova' in current_url or '/minuta/criar' in current_url):
            print(f'[KAIZEN][AVISO] Não parece estar na página de cadastro de minuta (URL: {current_url}). Tentando prosseguir...')
            # Não retorna mais, tenta preencher mesmo assim. A verificação de elementos abaixo será mais crucial.

        # Ação 1: JUIZ SOLICITANTE (revertendo para a função que usa CONFIG)
        _preencher_juiz_solicitante(driver)
        time.sleep(0.5)
        
        # Ação 2: VARA/JUÍZO (revertendo para a função que usa CONFIG e lida com CONFIG)
        _preencher_vara_juizo(driver)
        time.sleep(0.5)
        
        # Ação 3: NÚMERO DO PROCESSO
        _preencher_numero_processo(driver)
        time.sleep(0.5)
        
        # Ação 4: TIPO DE AÇÃO
        _preencher_tipo_acao(driver)
        time.sleep(0.5)
        
        # Ação 5: CPF/CNPJ AUTOR
        _preencher_cpf_autor(driver, invertido)
        time.sleep(0.5)
        
        # Ação 6: NOME AUTOR
        _preencher_nome_autor(driver, invertido)
        time.sleep(0.5)
        
        # Ação 7: TEIMOSINHA (apenas se não for requisição de endereço)
        req_endereco = _verificar_requisicao_endereco(driver)
        if not req_endereco:
            _preencher_teimosinha(driver)
        else:
            _preencher_endereco_opcoes(driver)
            
        print('[KAIZEN] Preenchimento de campos SISBAJUD concluído com sucesso.')
        
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha no preenchimento de campos SISBAJUD: {e}')

def _preencher_juiz_solicitante(driver):
    """Ação 1: Preencher Juiz Solicitante baseado no padrão gigs-plugin.js"""
    print('[KAIZEN] Ação 1: JUIZ SOLICITANTE')
    global processo_dados_extraidos
    try:
        # Usar magistrado dos dados extraídos ou CONFIG como fallback
        magistrado = ''
        if processo_dados_extraidos:
            magistrado = processo_dados_extraidos.get('magistrado', '')
        
        if not magistrado:
            magistrado = CONFIG.get('juiz_default', 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA')
            
        script = f"""
const selectors = [
    'input[placeholder*="Juiz"]',
    'input[placeholder*="Magistrado"]', 
    'input[formcontrolname="juizSolicitante"]',
    'input[name*="juiz"]',
    'input[aria-label*="Juiz"]',
    'input[id*="juiz"]'
];
let el = null;
let successfulSelector = '';

for (let selector of selectors) {{
    try {{
        el = document.querySelector(selector);
        if (el && el.offsetParent !== null && !el.disabled && !el.readOnly) {{
            successfulSelector = selector;
            break;
        }}
        el = null;
    }} catch (e) {{
        console.warn('[KAIZEN] Error with selector: ' + selector, e);
        el = null;
    }}
}}

if (el) {{
    el.focus();
    el.value = '{magistrado}';
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    el.blur();
    console.log('[KAIZEN] Magistrado preenchido com: {magistrado} usando seletor: ' + successfulSelector);
}} else {{
    console.error('[KAIZEN] Campo "Juiz Solicitante" não encontrado ou não interativo.');
}}
"""
        driver.execute_script(script)
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao preencher juiz solicitante: {e}')

def _preencher_vara_juizo(driver):
    """Ação 2: Preencher Vara/Juízo baseado no padrão gigs-plugin.js"""
    print('[KAIZEN] Ação 2: VARA/JUÍZO')
    global processo_dados_extraidos
    try:
        # Usar juízo dos dados extraídos ou CONFIG como fallback
        juizo = ''
        if processo_dados_extraidos:
            juizo = processo_dados_extraidos.get('juizo', '')
        
        if not juizo:
            juizo = CONFIG.get('vara_default', '3006')
            
        script = f"""
const selectors = [
    'mat-select[name*="varaJuizoSelect"]',
    'mat-select[formcontrolname="vara"]',
    'mat-select[formcontrolname="juizo"]',
    'select[name*="vara"]',
    'select[name*="juizo"]',
    'input[placeholder*="Vara"]',
    'input[placeholder*="Juízo"]'
];
let el = null;
let successfulSelector = '';

for (let selector of selectors) {{
    try {{
        el = document.querySelector(selector);
        if (el && el.offsetParent !== null && !el.disabled && !el.readOnly) {{
            successfulSelector = selector;
            break;
        }}
        el = null;
    }} catch (e) {{
        console.warn('[KAIZEN] Error with selector: ' + selector, e);
        el = null;
    }}
}}

if (el) {{
    if (el.tagName.toLowerCase() === 'mat-select' || el.tagName.toLowerCase() === 'select') {{
        // Para selects, tentar abrir e buscar opção
        el.focus();
        el.click();
        
        setTimeout(() => {{
            let options = document.querySelectorAll('mat-option[role="option"], option');
            for (let opt of options) {{
                if (opt.innerText.includes('{juizo}') || opt.value === '{juizo}') {{
                    opt.click();
                    console.log('[KAIZEN] Vara/Juízo selecionado: {juizo} usando seletor: ' + successfulSelector);
                    return;
                }}
            }}
            console.warn('[KAIZEN] Opção {juizo} não encontrada no select');
        }}, 500);
    }} else {{
        // Para inputs de texto
        el.focus();
        el.value = '{juizo}';
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        el.blur();
        console.log('[KAIZEN] Vara/Juízo preenchido: {juizo} usando seletor: ' + successfulSelector);
    }}
}} else {{
    console.error('[KAIZEN] Campo "Vara/Juízo" não encontrado ou não interativo.');
}}
"""
        driver.execute_script(script)
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao preencher vara/juízo: {e}')

def _preencher_numero_processo(driver):
    """Ação 3: Preencher Número do Processo baseado no padrão gigs-plugin.js"""
    print('[KAIZEN] Ação 3: NÚMERO DO PROCESSO')
    global processo_dados_extraidos
    try:
        numero = processo_dados_extraidos.get('numero', '') if processo_dados_extraidos else ''
        if numero:
            # Limpar formatação mantendo apenas dígitos
            numero_limpo = ''.join(filter(str.isdigit, numero))
            script = f"""
const selectors = [
    'input[formcontrolname="numeroProcesso"]', 
    'input[placeholder="Número do Processo"]',
    'input[placeholder*="Número"]',
    'input[placeholder*="Processo"]',
    'input[name*="numeroProcesso"]',
    'input[id*="numeroProcesso"]',
    'input[aria-label*="Número do processo"]',
    'input[id^="mat-input-"][placeholder*="Processo"]'
];
let el = null;
let successfulSelector = '';

for (let selector of selectors) {{
    try {{
        el = document.querySelector(selector);
        if (el && el.offsetParent !== null && !el.disabled && !el.readOnly) {{
            successfulSelector = selector;
            break;
        }}
        el = null;
    }} catch (e) {{
        console.warn('[KAIZEN] Error with selector: ' + selector, e);
        el = null;
    }}
}}

if (el) {{
    el.focus();
    el.value = '';
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.value = '{numero_limpo}';
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    el.blur();
    console.log('[KAIZEN] Número do processo preenchido com: {numero_limpo} usando seletor: ' + successfulSelector);
}} else {{
    console.error('[KAIZEN] Campo "Número do Processo" não encontrado ou não interativo.');
}}
"""
            driver.execute_script(script)
        else:
            print('[KAIZEN][INFO] Número do processo não disponível em processo_dados_extraidos.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao preencher número do processo: {e}')

def _preencher_tipo_acao(driver):
    """Ação 4: Preencher Tipo de Ação"""
    print('[KAIZEN] Ação 4: TIPO DE AÇÃO')
    try:
        driver.execute_script("""
            let el = document.querySelector('mat-select[name*="acao"]');
            if (el) {
                el.focus();
                el.click();
            }
        """)
        time.sleep(1)
        driver.execute_script("""
            let options = document.querySelectorAll('mat-option[role="option"]');
            for (let opt of options) {
                if (opt.innerText === 'Ação Trabalhista') {
                    opt.click();
                    break;
                }
            }
        """)
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao preencher tipo de ação: {e}')

def _preencher_cpf_autor(driver, invertido):
    """Ação 5: Preencher CPF/CNPJ do Autor"""
    print('[KAIZEN] Ação 5: CPF/CNPJ AUTOR')
    try:
        partes = processo_dados_extraidos.get('partes', {})
        
        if invertido:
            # Para polo invertido, usar parte passiva como autor
            cpf_cnpj = partes.get('passivas', [{}])[0].get('documento', '')
        else:
            # Usar parte ativa como autor
            cpf_cnpj = partes.get('ativas', [{}])[0].get('documento', '')
            
        if cpf_cnpj:
            # Limpar formatação do CPF/CNPJ
            cpf_cnpj_limpo = cpf_cnpj.replace('.', '').replace('-', '').replace('/', '')
            driver.execute_script(f"""
                let el = document.querySelector('input[placeholder*="CPF"]');
                if (el) {{
                    el.focus();
                    setTimeout(function() {{
                        el.value = '{cpf_cnpj_limpo}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.blur();
                    }}, 250);
                }}
            """)
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao preencher CPF do autor: {e}')

def _preencher_nome_autor(driver, invertido):
    """Ação 6: Preencher Nome do Autor"""
    print('[KAIZEN] Ação 6: NOME AUTOR')
    try:
        partes = processo_dados_extraidos.get('partes', {})
        
        if invertido:
            # Para polo invertido, usar parte passiva como autor
            nome = partes.get('passivas', [{}])[0].get('nome', '')
        else:
            # Usar parte ativa como autor
            nome = partes.get('ativas', [{}])[0].get('nome', '')
            
        if nome:
            # Preencher o campo nome do autor (similar ao CPF, mas com nome)
            # Adaptar o seletor se necessário
            escolher_opcao_sisbajud_avancado(driver, 'input[placeholder*="Nome do Autor"]', nome) # Exemplo de seletor
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao preencher nome do autor: {e}')

def _verificar_requisicao_endereco(driver):
    """Verifica se é requisição de endereço/informações"""
    try:
        return driver.execute_script("""
            let radio = document.querySelector('mat-radio-button[class*="mat-radio-checked"]');
            return radio && radio.innerText.includes('Requisição de informações');
        """)
    except:
        return False

def _preencher_teimosinha(driver):
    """Ação 7: Configurar Teimosinha"""
    print('[KAIZEN] Ação 7: TEIMOSINHA')
    try:
        teimosinha = CONFIG.get('teimosinha', '60').lower()
        if teimosinha != 'nao':
            driver.execute_script("""
                let radios = document.querySelectorAll('mat-radio-button');
                for (let radio of radios) {
                    if (radio.innerText.includes('Repetir a ordem')) {
                        radio.querySelector('label').click();
                        break;
                    }
                }
            """)
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao configurar teimosinha: {e}')

def _preencher_endereco_opcoes(driver):
    """Ação 7.1 e 7.2: Configurar opções de endereço"""
    print('[KAIZEN] Ação 7.1-7.2: CONFIGURAR ENDEREÇO')
    try:
        # Marcar opção "Endereços"
        driver.execute_script("""
            let checkboxes = document.querySelectorAll('span[class*="mat-checkbox-label"]');
            for (let checkbox of checkboxes) {
                if (checkbox.innerText === 'Endereços') {
                    checkbox.parentElement.firstElementChild.firstElementChild.click();
                    break;
                }
            }
        """)
        time.sleep(0.5)
        
        # Desmarcar "Incluir dados sobre contas"
        driver.execute_script("""
            let radios = document.querySelectorAll('mat-radio-button');
            for (let radio of radios) {
                if (radio.innerText.includes('Não')) {
                    radio.querySelector('label').click();
                    break;
                }
            }
        """)
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao configurar opções de endereço: {e}')

def escolher_opcao_sisbajud_avancado(driver, seletor, valor):
    """
    Implementação avançada baseada na função escolherOpcaoSISBAJUD do gigs-plugin.js
    """
    try:
        driver.execute_script(f"""
            async function escolherOpcaoSISBAJUD(seletor, valor) {{
                await new Promise(resolve => setTimeout(resolve, 200));
                let element = document.querySelector(seletor);
                if (!element) return false;
                
                element.focus();
                element.dispatchEvent(new KeyboardEvent('keydown', {{ keyCode: 40, which: 40 }}));
                
                // Aguardar opções aparecerem
                let tentativas = 0;
                while (tentativas < 5) {{
                    await new Promise(resolve => setTimeout(resolve, 300));
                    let opcoes = document.querySelectorAll('mat-option[role="option"], option');
                    if (opcoes.length > 0) {{
                        for (let opcao of opcoes) {{
                            if (opcao.innerText.toLowerCase().includes(valor.toLowerCase())) {{
                                opcao.click();
                                return true;
                            }}
                        }}
                        break;
                    }}
                    tentativas++;
                    element.focus();
                    element.dispatchEvent(new KeyboardEvent('keydown', {{ keyCode: 40, which: 40 }}));
                }}
                return false;
            }}
            escolherOpcaoSISBAJUD('{seletor}', '{valor}');
        """)
        return True
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha na seleção avançada: {e}')
        return False

def kaizen_nova_minuta(driver, endereco=False):
    """
    Implementação fiel à função novaMinutaSisbajud do gigs-plugin.js
    Reproduz a navegação exata: Menu -> Minuta -> Nova -> [Requisição de informações se endereco=True]
    ADAPTADO: Se a URL já estiver em /minuta, pula direto para o botão "Nova"
    """
    print(f'[KAIZEN] ========== NOVA MINUTA SISBAJUD ==========')
    print(f'[KAIZEN] Parâmetros: endereco={endereco}')
    
    try:
        current_url = driver.current_url
        print(f'[KAIZEN] URL inicial: {current_url}')
        
        # Verificar se já estamos na página de minuta
        if '/minuta' in current_url:
            print('[KAIZEN] ✅ Já estamos na página de minuta, pulando navegação inicial.')
        else:
            print('[KAIZEN] Navegando para página de minuta...')
            # Implementação fiel ao JavaScript original
            # Passo 1: Clicar no menu de navegação
            print('[KAIZEN] Passo 1: Abrindo menu de navegação...')
            driver.execute_script("""
                let btn = document.querySelector('button[aria-label*="menu de navegação"]');
                if (btn) {
                    console.log('[KAIZEN] Menu de navegação encontrado, clicando...');
                    btn.click();
                    return true;
                } else {
                    console.log('[KAIZEN][ERRO] Menu de navegação não encontrado');
                    return false;
                }
            """)
            time.sleep(0.8)
            
            # Passo 2: Ir para Minuta
            print('[KAIZEN] Passo 2: Navegando para Minuta...')
            driver.execute_script("""
                let link = document.querySelector('a[aria-label*="Ir para Minuta"]');
                if (link) {
                    console.log('[KAIZEN] Link Minuta encontrado, clicando...');
                    link.click();
                    return true;
                } else {
                    console.log('[KAIZEN][ERRO] Link Minuta não encontrado');
                    return false;
                }            """)
            time.sleep(1.5)
        
        # Verificar se chegamos na página de minuta
        current_url = driver.current_url
        print(f'[KAIZEN] URL após navegação: {current_url}')
        print('[KAIZEN] Passo 3: Procurando e clicando no botão Nova...')
        
        # Executar debug dos botões (opcional - descomente para debug detalhado)
        # debug_botao_nova(driver)
        
        # Implementação fiel à função querySelectorByText do JavaScript original com estratégias múltiplas
        sucesso_click = driver.execute_script("""
            // Função removeAcento (reprodução fiel do mini-selenium.js)
            function removeAcento(text) {
                let stringComAcentos = "ÄÅÁÂÀÃäáâàãÉÊËÈéêëèÍÎÏÌíîïìÖÓÔÒÕöóôòõÜÚÛüúûùÇç";
                let stringSemAcentos = "AAAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUuuuuCc";
                
                for (let i = 0; i < stringComAcentos.length; i++) {
                    while(true) {
                        if (text.search(stringComAcentos[i].toString()) > -1) {
                            text = text.replace(stringComAcentos[i].toString(), stringSemAcentos[i].toString());
                        } else {
                            break;
                        }
                    }
                }
                return text;
            }
            
            // Função querySelectorByText (reprodução fiel do mini-selenium.js)
            function querySelectorByText(tagname, texto) {
                return Array.from(document.querySelectorAll(tagname)).find(el => 
                    removeAcento(el.textContent.trim().toLowerCase()).includes(removeAcento(texto.toLowerCase()))
                );
            }
            
            // Buscar botão Nova usando a mesma lógica do JavaScript original
            console.log('[KAIZEN] Procurando botão com texto "Nova"...');
            let botaoNova = querySelectorByText('button', 'Nova');
            
            if (botaoNova) {
                console.log('[KAIZEN] Botão Nova encontrado:', botaoNova);
                console.log('[KAIZEN] Texto do botão:', botaoNova.textContent.trim());
                console.log('[KAIZEN] Clicando no botão Nova...');
                
                // Verificar se o botão não está desabilitado
                if (!botaoNova.hasAttribute('disabled') && !botaoNova.disabled) {
                    botaoNova.click();
                    return true;
                } else {
                    console.log('[KAIZEN][ERRO] Botão Nova está desabilitado');
                    return false;
                }
            } else {
                console.log('[KAIZEN][ERRO] Botão Nova não encontrado');
                return false;
            }
        """)
        time.sleep(2)  # Aguardar resultado do clique
        
        # Verificar se o clique foi bem-sucedido
        if not sucesso_click:
            print('[KAIZEN][ERRO] Falha ao clicar no botão Nova')
            return
            
        print('[KAIZEN] ✅ Botão Nova clicado com sucesso!')
          # Passo 4: Se for minuta de endereço, selecionar "Requisição de informações"
        if endereco:
            print('[KAIZEN] Passo 4: Selecionando "Requisição de informações"...')
            requisicao_selecionada = driver.execute_script("""
                // Buscar por labels que contenham "Requisição de informações"
                let labels = document.querySelectorAll('label');
                for (let label of labels) {
                    if (label.innerText && label.innerText.includes('Requisição de informações')) {
                        console.log('[KAIZEN] Label "Requisição de informações" encontrada, clicando...');
                        label.click();
                        return true;
                    }
                }
                
                // Buscar por radio buttons ou checkboxes relacionados
                let radioButtons = document.querySelectorAll('input[type="radio"], mat-radio-button');
                for (let radio of radioButtons) {
                    let parent = radio.closest('mat-radio-button, label');
                    if (parent && parent.innerText.includes('Requisição de informações')) {
                        console.log('[KAIZEN] Radio "Requisição de informações" encontrado, clicando...');
                        radio.click();
                        return true;
                    }
                }
                
                console.log('[KAIZEN][ERRO] "Requisição de informações" não encontrado');
                return false;
            """)
            
            if requisicao_selecionada:
                print('[KAIZEN] ✅ "Requisição de informações" selecionada!')
            else:
                print('[KAIZEN][AVISO] "Requisição de informações" não encontrada, continuando...')
                
            time.sleep(0.8)# Aguardar a página carregar completamente
        print('[KAIZEN] Aguardando redirecionamento para página de cadastro...')
        
        for tentativa in range(20):  # Aumentado de 15 para 20 tentativas
            current_url = driver.current_url
            print(f'[KAIZEN] Tentativa {tentativa + 1}/20 - URL atual: {current_url}')
            
            # Verificar múltiplas variações de URL de cadastro
            urls_validas = [
                'minuta/cadastrar',
                'minuta/nova', 
                'cadastrar',
                'minuta/add',
                'minuta/create',
                'sisbajud-cadastro-minuta'
            ]
            
            if any(url_pattern in current_url for url_pattern in urls_validas):
                print(f'[KAIZEN] ✅ Página de cadastro detectada! URL: {current_url}')
                break
                
            # Verificar se elementos de cadastro já estão disponíveis mesmo que a URL não tenha mudado
            elementos_presentes = driver.execute_script("""
                let elementos = [
                    'input[placeholder*="Juiz"]',
                    'sisbajud-cadastro-minuta',
                    'input[placeholder*="Solicitante"]',
                    'mat-form-field'
                ];
                
                for (let seletor of elementos) {
                    if (document.querySelector(seletor)) {
                        console.log('[KAIZEN] Elemento de cadastro encontrado:', seletor);
                        return true;
                    }
                }
                return false;
            """)
            
            if elementos_presentes:
                print('[KAIZEN] ✅ Elementos de cadastro detectados na página!')
                break
                
            time.sleep(1.5)  # Aumentado tempo entre tentativas
        else:
            print(f'[KAIZEN][AVISO] Página de cadastro não detectada após 20 tentativas.')
            print(f'[KAIZEN] URL final: {driver.current_url}')
            print('[KAIZEN] Tentando continuar mesmo assim...')
            
        # Aguardar elementos de formulário estarem totalmente carregados
        print('[KAIZEN] Aguardando elementos do formulário...')
        elementos_encontrados = driver.execute_script("""
            return new Promise(resolve => {
                let tentativas = 0;
                let maxTentativas = 15;
                
                function verificarElementos() {
                    tentativas++;
                    console.log('[KAIZEN] Verificando elementos... tentativa', tentativas);
                    
                    let elementos = [
                        'input[placeholder*="Juiz"]',
                        'input[placeholder*="Solicitante"]',
                        'sisbajud-cadastro-minuta input',
                        'mat-form-field input'
                    ];
                    
                    for (let seletor of elementos) {
                        let elemento = document.querySelector(seletor);
                        if (elemento) {
                            console.log('[KAIZEN] ✅ Elemento encontrado:', seletor);
                            resolve(true);
                            return;
                        }
                    }
                    
                    if (tentativas >= maxTentativas) {
                        console.log('[KAIZEN][ERRO] Elementos não encontrados após', maxTentativas, 'tentativas');
                        resolve(false);
                    } else {
                        setTimeout(verificarElementos, 500);
                    }
                }
                
                verificarElementos();
            });        """)
        
        if elementos_encontrados:
            print('[KAIZEN] ✅ Elementos do formulário carregados!')
        else:
            print('[KAIZEN][AVISO] Elementos do formulário não detectados, tentando continuar...')
            
        time.sleep(1)
        
        print('[KAIZEN] ✅ Nova minuta criada com sucesso!')
        print('[KAIZEN] 💡 Para preencher os campos, clique em "Polo Ativo" ou "Polo Passivo" conforme necessário.')
        
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao criar nova minuta: {e}')

def kaizen_consultar_minuta(driver):
    """
    Implementação fiel à função consultarMinutaSisbajud do gigs-plugin.js
    Reproduz a navegação: Menu -> Ordem judicial -> Busca por filtros -> Consultar
    """
    print('[KAIZEN] Consultar Minuta SISBAJUD')
    try:
        # Passo 1: Clicar no menu de navegação
        driver.execute_script("""
            let btn = document.querySelector('button[aria-label*="menu de navegação"]');
            if (btn) btn.click();
        """)
        time.sleep(0.8)
        
        # Passo 2: Ir para Ordem judicial
        driver.execute_script("""
            let link = document.querySelector('a[aria-label*="Ir para Ordem judicial"]');
            if (link) link.click();
        """)
        time.sleep(1.5)
        
        # Passo 3: Clicar na aba "Busca por filtros de pesquisa"
        driver.execute_script("""
            let tabs = document.querySelectorAll('div[role="tab"]');
            for (let tab of tabs) {
                if (tab.innerText && tab.innerText.includes('Busca por filtros de pesquisa')) {
                    tab.click();
                    break;
                }
            }
        """)
        time.sleep(1)
        
        # Passo 4: Preencher número do processo e consultar
        numero = processo_dados_extraidos.get('numero', '') if processo_dados_extraidos else ''
        if numero:
            numero_escape = numero.replace("'", "\\'").replace('"', '\\"')
            driver.execute_script(f"""
                let input = document.querySelector('input[placeholder="Número do Processo"]');
                if (input) {{
                    input.value = '{numero_escape}';
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            """)
            time.sleep(0.5)
            
            driver.execute_script("""
                let buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    if (btn.innerText === 'Consultar') {
                        btn.click();
                        break;
                    }
                }
            """)
            print('[KAIZEN] Consulta de minuta disparada.')
        else:
            print('[KAIZEN][ERRO] Número do processo não encontrado.')
            
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao consultar minuta: {e}')

def kaizen_consultar_teimosinha(driver):
    """
    Preenche o número do processo na tela de consulta de teimosinha do SISBAJUD
    e clica em "Consultar", carregando os dados de 'dadosatuais.json'.
    """
    print('[KAIZEN] Iniciando Consulta de Teimosinha...')
    
    project_path = os.path.dirname(os.path.abspath(__file__))
    dados_path = os.path.join(project_path, 'dadosatuais.json')
    
    processo_local_data = None
    if os.path.exists(dados_path):
        try:
            with open(dados_path, 'r', encoding='utf-8') as f:
                processo_local_data = json.load(f)
            print(f'[KAIZEN] Dados carregados de {dados_path}: {processo_local_data}')
        except json.JSONDecodeError as e:
            print(f'[KAIZEN][ERRO] Falha ao decodificar JSON de {dados_path}: {e}')
            return
        except Exception as e:
            print(f'[KAIZEN][ERRO] Falha ao ler {dados_path}: {e}')
            return
    else:
        print(f'[KAIZEN][ERRO] Arquivo {dados_path} não encontrado.')
        return

    if not processo_local_data or not isinstance(processo_local_data, dict):
        print('[KAIZEN][ERRO] Conteúdo de dadosatuais.json inválido ou não é um dicionário.')
        return

    numero_processo = processo_local_data.get("numero")
    if not numero_processo:
        print('[KAIZEN][ERRO] "numero" do processo não encontrado em dadosatuais.json.')
        return
    
    print(f'[KAIZEN] Consultando Teimosinha para o processo: {numero_processo}')

    # Escape single quotes in numero_processo for JavaScript
    numero_processo_js = numero_processo.replace("'", "\\\\'")

    js_script = f"""
        const numeroProcesso = '{numero_processo_js}';
        let campoProcessoEncontrado = false;
        let botaoConsultarEncontrado = false;
        let mensagemRetorno = '';

        console.log('[KAIZEN JS] Iniciando script para consulta teimosinha. Processo:', numeroProcesso);

        // Tentar preencher o campo do número do processo
        const selectorsProcesso = [
            'input[formcontrolname="numeroProcesso"]', // Angular
            'input[data-placeholder="Número do processo"]', // Material com data-placeholder
            'input[placeholder="Número do Processo"]', // Placeholder genérico
            'input[placeholder="Nº do processo"]', // Variação placeholder
            'input[aria-label="Número do processo"]',
            'input[id*="numeroProcesso"]', 
            'input[name*="numeroProcesso"]',
            'input[id^="mat-input-"][placeholder*="Processo"]' // Angular Material common pattern
        ];

        for (const selector of selectorsProcesso) {{
            const field = document.querySelector(selector);
            if (field && field.offsetParent !== null && !field.disabled && !field.readOnly) {{
                try {{
                    field.value = ''; // Limpar campo primeiro
                    field.dispatchEvent(new Event('input', {{ bubbles: true }})); 
                    field.value = numeroProcesso;
                    field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    field.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    console.log('[KAIZEN JS] Campo "Número do Processo" preenchido com:', numeroProcesso, 'usando seletor:', selector);
                    campoProcessoEncontrado = true;
                    break;
                }} catch (e) {{
                    console.error('[KAIZEN JS] Erro ao tentar preencher campo com seletor', selector, e);
                }}
            }}
        }}

        if (!campoProcessoEncontrado) {{
            mensagemRetorno = 'Campo "Número do Processo" não encontrado ou não interagível.';
            console.error('[KAIZEN JS]', mensagemRetorno);
            return {{success: false, message: mensagemRetorno}};
        }}

        // Aguardar um instante para que o preenchimento seja processado
        // e o botão Consultar possa ser habilitado/estado da UI atualizado.
        // Usar uma Promise para garantir que o Selenium espere.
        await new Promise(resolve => setTimeout(resolve, 500));

        // Tentar clicar no botão "Consultar"
        const allButtons = Array.from(document.querySelectorAll('button'));
        let consultarButton = null;

        for (const btn of allButtons) {{
            if (btn.disabled || btn.offsetParent === null) continue; 

            const buttonText = (btn.innerText || btn.textContent || '').trim().toLowerCase();
            const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
            let spanText = '';
            const spanElement = btn.querySelector('span.mat-button-wrapper') || btn.querySelector('span');
            if (spanElement) {{
                spanText = (spanElement.innerText || spanElement.textContent || '').trim().toLowerCase();
            }}
            
            if (buttonText === 'consultar' || 
                ariaLabel.includes('consultar') || 
                spanText === 'consultar' ||
                (btn.matches('button[type="submit"]') && (buttonText.includes('consultar') || spanText.includes('consultar'))) ||
                (btn.querySelector('mat-icon') && (btn.querySelector('mat-icon').textContent || '').trim() === 'search')
               ) {{
                consultarButton = btn;
                console.log('[KAIZEN JS] Botão "Consultar" encontrado:', btn, 'Texto:', buttonText, 'Span:', spanText, 'Aria:', ariaLabel);
                break;
            }}
        }}
        
        if (consultarButton) {{
            try {{
                consultarButton.click();
                botaoConsultarEncontrado = true;
                mensagemRetorno = 'Botão "Consultar" clicado com sucesso.';
                console.log('[KAIZEN JS]', mensagemRetorno);
                return {{success: true, message: mensagemRetorno}};
            }} catch (e) {{
                mensagemRetorno = 'Erro ao clicar no botão "Consultar": ' + e.message;
                console.error('[KAIZEN JS]', mensagemRetorno, e);
                return {{success: false, message: mensagemRetorno, raw_error: e.toString()}};
            }}
        }} else {{
            mensagemRetorno = 'Botão "Consultar" não encontrado, não visível ou não clicável.';
            console.error('[KAIZEN JS]', mensagemRetorno);
            const visibleButtons = Array.from(document.querySelectorAll('button:not([disabled])'))
                                     .filter(b => b.offsetParent !== null)
                                     .map(b => `Text: '${{(b.innerText || b.textContent || '').trim()}}', ID: ${{b.id}}, Classes: ${{b.className}}`);
            console.log('[KAIZEN JS] Botões visíveis e habilitados para depuração:', visibleButtons.join('; '));
            return {{success: false, message: mensagemRetorno}};
        }}
    """
    
    try:
        resultado_js = driver.execute_script(js_script) # execute_script handles promises returned by the JS
        
        if resultado_js and isinstance(resultado_js, dict) and resultado_js.get('success'):
            print(f'[KAIZEN] Consulta Teimosinha: {resultado_js.get("message")}')
        else:
            error_message = resultado_js.get("message") if isinstance(resultado_js, dict) else "Resultado inesperado ou falha na execução do script JS."
            print(f'[KAIZEN][ERRO] Consulta Teimosinha falhou: {error_message}')
            if isinstance(resultado_js, dict) and 'raw_error' in resultado_js:
                 print(f'[KAIZEN][ERRO JS Bruto] {resultado_js["raw_error"]}')

    except Exception as e:
        print(f'[KAIZEN][ERRO] Exceção ao executar script de consulta teimosinha: {e}')

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
    """
    Implementação fiel à função monitor_janela_sisbajud do gigs-plugin.js
    Monitora mudanças no DOM e aplica estilos/eventos conforme o JavaScript original
    """
    try:
        driver.execute_script('''
        if (!window._kaizen_monitor_janela_sisbajud) {
            window._kaizen_monitor_janela_sisbajud = true;
            console.log("Extensão maisPJE: monitor_janela_sisbajud iniciado");
            
            let targetDocumento = document.body;
            let observerDocumento = new MutationObserver(function(mutationsDocumento) {
                mutationsDocumento.forEach(function(mutation) {
                    if (!mutation.addedNodes[0]) { return }
                    if (!mutation.addedNodes[0].tagName) { return }
                    
                    // Aplicar estilos nas linhas de tabelas (reprodução fiel do JS original)
                    if (document.querySelector('SISBAJUD-PESQUISA-TEIMOSINHA') && 
                        mutation.addedNodes[0].tagName == "TR" && 
                        mutation.target.tagName == "TBODY") {
                        
                        mutation.addedNodes[0].onmouseenter = function () {
                            this.style.cursor = 'pointer';
                            this.style.outline = '2px solid #3e3f3f';
                            this.style.filter = 'drop-shadow(0 0 0.03rem #e9581c)';
                        };
                        
                        mutation.addedNodes[0].onmouseleave = function () {
                            this.style.cursor = 'revert';
                            this.style.outline = 'unset';
                            this.style.filter = 'revert';
                        };
                        
                        mutation.addedNodes[0].onclick = function () {
                            // Simular função clicar_detalhes do JS original
                            console.log("Clique em linha da tabela de teimosinha detectado");
                            if (typeof clicar_detalhes === 'function') {
                                clicar_detalhes(this);
                            }
                        };
                    }
                    
                    // Outros monitoramentos específicos do SISBAJUD podem ser adicionados aqui
                    // conforme necessário
                });
            });
            
            // Configuração idêntica ao JavaScript original
            let config = { childList: true, characterData: true, subtree: true };
            observerDocumento.observe(targetDocumento, config);
            
            console.log("Monitor de janelas SISBAJUD configurado com sucesso");
        }
        ''')
        print('[KAIZEN] Monitoramento de janelas SISBAJUD ativado.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao monitorar janelas: {e}')

def integrar_storage_processo(driver):
    """
    Integra dados do processo com o storage local, similar ao JavaScript original
    """
    try:
        if processo_dados_extraidos:
            # Escapar dados para JavaScript
            numero = processo_dados_extraidos.get("numero", "").replace("'", "\\'").replace('"', '\\"')
            nome_ativo = processo_dados_extraidos.get("partes", {}).get("ativas", [{}])[0].get("nome", "").replace("'", "\\'").replace('"', '\\"')
            doc_ativo = processo_dados_extraidos.get("partes", {}).get("ativas", [{}])[0].get("documento", "").replace("'", "\\'").replace('"', '\\"')
            nome_passivo = processo_dados_extraidos.get("partes", {}).get("passivas", [{}])[0].get("nome", "").replace("'", "\\'").replace('"', '\\"')
            doc_passivo = processo_dados_extraidos.get("partes", {}).get("passivas", [{}])[0].get("documento", "").replace("'", "\\'").replace('"', '\\"')
            
            driver.execute_script(f"""
                // Simular storage.local.set do JavaScript original
                if (!window.processo_memoria) {{
                    window.processo_memoria = {{}};
                }}
                
                window.processo_memoria = {{
                    numero: '{numero}',
                    autor: [{{"nome": "{nome_ativo}", "cpfcnpj": "{doc_ativo}"}}],
                    reu: [{{"nome": "{nome_passivo}", "cpfcnpj": "{doc_passivo}"}}]
                }};
                
                console.log("Dados do processo integrados ao storage:", window.processo_memoria);
            """)
            print('[KAIZEN] Dados do processo integrados ao storage local.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao integrar dados do processo: {e}')

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
    
    # Salvar dados em arquivo temporário para acesso do SISBAJUD
    salvar_dados_processo_temp()
    
    injetar_botoes_pje(driver)
    bind_eventos(driver)
    print('[BACEN] Botões injetados na tela de detalhes do processo.')
    
    while True:
        evento = checar_evento(driver)
        if evento == 'minuta_bloqueio':
            driver = abrir_sisbajud_em_firefox_sisbajud()
            break
        elif evento == 'minuta_endereco':
            driver = abrir_sisbajud_em_firefox_sisbajud()
            break
        elif evento == 'processar_bloqueios':
            driver = abrir_sisbajud_em_firefox_sisbajud()
            break
        time.sleep(1)    # Inicializar componentes SISBAJUD uma única vez
    dados_login(driver) 
    monitor_janela_sisbajud(driver)
    integrar_storage_processo(driver)
    
    # Aguardar tela de minuta e injetar menu de forma robusta
    print('[BACEN] Aguardando tela de minuta para injeção inicial do menu...')
    menu_injetado = aguardar_tela_minuta_e_injetar_menu(driver)
    if not menu_injetado:
        print('[BACEN] ⚠️ Falha na injeção inicial do menu. Tentando injeção básica...')
        injetar_menu_kaizen_sisbajud(driver)
    
    print('[BACEN] Componentes SISBAJUD inicializados. Controle transferido para janela SISBAJUD (perfil Sisb).')
    
    # Loop principal para eventos Kaizen no SISBAJUD
    while True:
        try:
            
            kaizen_evt = checar_kaizen_evento(driver)
            
            if kaizen_evt == 'kaizen_guardar_senha':
                kaizen_guardar_senha(driver)
            elif kaizen_evt == 'kaizen_minuta_bloqueio_passivo':
                print("[KAIZEN_EVT] Evento: kaizen_minuta_bloqueio_passivo")
                kaizen_nova_minuta(driver, endereco=False)
                # Adicionar uma pequena pausa e verificação de URL antes de preencher
                time.sleep(1) # Pausa para a navegação da nova minuta acontecer
                if '/minuta/cadastrar' in driver.current_url or '/minuta/nova' in driver.current_url: # Checar se está na tela correta
                    kaizen_preencher_campos(driver, invertido=False)
                else:
                    print(f"[KAIZEN_EVT][ERRO] Após kaizen_nova_minuta, não está na URL esperada para preenchimento. URL atual: {driver.current_url}")
            elif kaizen_evt == 'kaizen_minuta_endereco_passivo':
                print("[KAIZEN_EVT] Evento: kaizen_minuta_endereco_passivo")
                kaizen_nova_minuta(driver, endereco=True)
                time.sleep(1)
                if '/minuta/cadastrar' in driver.current_url or '/minuta/nova' in driver.current_url:
                    kaizen_preencher_campos(driver, invertido=False)
                else:
                    print(f"[KAIZEN_EVT][ERRO] Após kaizen_nova_minuta (endereço), não está na URL esperada. URL atual: {driver.current_url}")
            elif kaizen_evt == 'kaizen_minuta_bloqueio_ativo':
                print("[KAIZEN_EVT] Evento: kaizen_minuta_bloqueio_ativo")
                kaizen_nova_minuta(driver, endereco=False)
                time.sleep(1)
                if '/minuta/cadastrar' in driver.current_url or '/minuta/nova' in driver.current_url:
                    kaizen_preencher_campos(driver, invertido=True)
                else:
                    print(f"[KAIZEN_EVT][ERRO] Após kaizen_nova_minuta, não está na URL esperada para preenchimento (ativo). URL atual: {driver.current_url}")
            elif kaizen_evt == 'kaizen_consultar_teimosinha':
                print("[KAIZEN_EVT] Evento: kaizen_consultar_teimosinha")
                kaizen_consultar_teimosinha(driver)
            # Remover os handlers antigos:
            # elif kaizen_evt == 'kaizen_preencher_campos_invertido':
            #     kaizen_preencher_campos(driver, invertido=True)
            # elif kaizen_evt == 'kaizen_preencher_campos':
            #     kaizen_preencher_campos(driver, invertido=False)
            # elif kaizen_evt == 'kaizen_nova_minuta_end':
            #     kaizen_nova_minuta(driver, endereco=True)
            # elif kaizen_evt == 'kaizen_nova_minuta':
            #     kaizen_nova_minuta(driver, endereco=False)
            # elif kaizen_evt == 'kaizen_consultar_minuta':
            #     kaizen_consultar_minuta(driver)
            # elif kaizen_evt == 'kaizen_consulta_rapida':
            #     kaizen_consulta_rapida(driver)
                
        except Exception as e:
            print(f'[BACEN][ERRO] Erro no loop principal: {e}')
            
        time.sleep(3)  # Ciclo de 3 segundos

if __name__ == '__main__':
    main()

def debug_botao_nova(driver):
    """
    Função de debug para analisar o botão Nova na página
    """
    print('[KAIZEN][DEBUG] Analisando botões na página...')
    
    # Buscar todos os botões e analisar
    resultado = driver.execute_script("""
        let botoes = Array.from(document.querySelectorAll('button'));
        let analise = {
            total_botoes: botoes.length,
            botoes_com_nova: [],
            botoes_mat_fab: [],
            url_atual: window.location.href,
            page_ready: document.readyState
        };
        
        // Analisar cada botão
        botoes.forEach((btn, index) => {
            let texto = btn.textContent.trim().toLowerCase();
            
            // Botões que contenham "nova"
            if (texto.includes('nova')) {
                analise.botoes_com_nova.push({
                    index: index,
                    texto: btn.textContent.trim(),
                    id: btn.id || 'sem-id',
                    class: btn.className || 'sem-class',
                    disabled: btn.disabled,
                    hasDisabledAttr: btn.hasAttribute('disabled'),
                    ariaLabel: btn.getAttribute('aria-label') || 'sem-aria-label'
                });
            }
            
            // Botões mat-fab
            if (btn.hasAttribute('mat-fab') || btn.classList.contains('mat-fab')) {
                analise.botoes_mat_fab.push({
                    index: index,
                    texto: btn.textContent.trim(),
                    id: btn.id || 'sem-id',
                    class: btn.className || 'sem-class'
                });
            }
        });
        
        return analise;
    """)
    
    print(f'[KAIZEN][DEBUG] URL atual: {resultado["url_atual"]}')
    print(f'[KAIZEN][DEBUG] Estado da página: {resultado["page_ready"]}')
    print(f'[KAIZEN][DEBUG] Total de botões: {resultado["total_botoes"]}')
    print(f'[KAIZEN][DEBUG] Botões mat-fab: {len(resultado["botoes_mat_fab"])}')
    print(f'[KAIZEN][DEBUG] Botões com "nova": {len(resultado["botoes_com_nova"])}')
    
   
    
    if resultado["botoes_com_nova"]:
        print('[KAIZEN][DEBUG] Detalhes dos botões com "nova":')
        for botao in resultado["botoes_com_nova"]:
            print(f'[KAIZEN][DEBUG]   - Texto: "{botao["texto"]}"')
            print(f'[KAIZEN][DEBUG]     ID: {botao["id"]}')
            print(f'[KAIZEN][DEBUG]     Classe: {botao["class"]}')
            print(f'[KAIZEN][DEBUG]     Desabilitado: {botao["disabled"]}')
            print(f'[KAIZEN][DEBUG]     Aria-label: {botao["ariaLabel"]}')
    else:
        print('[KAIZEN][DEBUG] ❌ Nenhum botão com "nova" encontrado!')
    
    return resultado
