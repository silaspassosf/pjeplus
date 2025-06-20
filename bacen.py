# bacen.py
# Automação SISBAJUD/BACEN integrada ao PJe, com suporte a Firefox (login inicial) e Thorium/Chrome (acesso SISBAJUD)
# Baseado em sisbajud.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from Fix import extrair_dados_processo
from driver_config import criar_driver, login_func
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

# ===================== INJETAR BOTÃO ÚNICO NO PJe =====================
def injetar_botao_sisbajud_pje(driver):
    """Injeta apenas um botão no PJe para abrir o SISBAJUD"""
    driver.execute_script("""
        if (!document.getElementById('btn_abrir_sisbajud')) {
            let container = document.createElement('div');
            container.id = 'sisbajud_btn_container';
            container.style = 'position:fixed;top:60px;right:20px;z-index:9999;background:#1976d2;padding:12px;border-radius:12px;box-shadow:0 4px 12px rgba(25,118,210,0.3);';
            
            let btn = document.createElement('button');
            btn.id = 'btn_abrir_sisbajud';
            btn.innerHTML = '🏦 Abrir SISBAJUD';
            btn.style = 'padding:10px 20px;font-size:14px;font-weight:bold;cursor:pointer;background:#fff;color:#1976d2;border:none;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);transition:all 0.3s ease;';
            btn.onmouseenter = function() { this.style.transform = 'scale(1.05)'; this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)'; };
            btn.onmouseleave = function() { this.style.transform = 'scale(1)'; this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'; };
            btn.onclick = function() { window.dispatchEvent(new CustomEvent('abrir_sisbajud')); };
            
            container.appendChild(btn);
            document.body.appendChild(container);
        }
    """)

# ===================== PROMPT DE DADOS VIA JS =====================
def prompt_js(driver, mensagem, valor_padrao=''):
    return driver.execute_script(f"return prompt('{mensagem.replace("'", "\\'")}', '{valor_padrao}');")

# ===================== ACIONADORES DE EVENTOS =====================
def bind_eventos(driver):
    """Configura apenas o evento de abrir SISBAJUD"""
    driver.execute_script("window.sisbajud_event_flag = '';")
    driver.execute_script("""
        window.addEventListener('abrir_sisbajud', function() { window.sisbajud_event_flag = 'abrir_sisbajud'; });
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
    cookies_filtrados = [c for c in cookies if 'sisbajud.cloud.pje.jus.br' in c.get('domain', '') or 'sso.cloud.pje.jus.br' in c.get('domain', '') or 'cnj.jus.br' in c.get('domain', '')]
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(cookies_filtrados, f, ensure_ascii=False, indent=2)
    print(f'[BACEN] Cookies SISBAJUD salvos em {caminho}.')

def carregar_cookies_sisbajud(driver, caminho='cookies_sisbajud.json'):
    """Carrega cookies salvos para o driver SISBAJUD"""
    import json
    import os
    
    if not os.path.exists(caminho):
        print(f'[BACEN] Arquivo de cookies não encontrado: {caminho}')
        return False
    
    try:
        # Primeiro navegar para uma página válida do domínio
        print('[BACEN] Navegando para domínio SISBAJUD para carregar cookies...')
        driver.get('https://sso.cloud.pje.jus.br')
        time.sleep(2)
        
        with open(caminho, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        print(f'[BACEN] Carregando {len(cookies)} cookies...')
        cookies_carregados = 0
        
        for cookie in cookies:
            try:
                # Remover campos que podem causar problemas
                cookie_limpo = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
                
            except Exception as e:
                print(f'[BACEN][DEBUG] Erro ao carregar cookie {cookie.get("name", "desconhecido")}: {e}')
                continue
        
        print(f'[BACEN] ✅ {cookies_carregados} cookies carregados com sucesso!')
        
        # Navegar para a URL final do SISBAJUD
        print('[BACEN] Redirecionando para SISBAJUD com cookies carregados...')
        driver.get('https://sisbajud.cnj.jus.br/')
        time.sleep(3)
        
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao carregar cookies: {e}')
        return False

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
    """Abre driver Firefox SISBAJUD e tenta login automático via cookies ou injeta tabela de login"""
    # Usar a função de driver Firefox específica para SISBAJUD
    driver = criar_driver_firefox_sisb()
    if not driver:
        print('[BACEN][ERRO] Falha ao criar driver Firefox SISBAJUD')
        return None
        
    print('[BACEN] ✅ Driver SISBAJUD criado.')
    
    # Verificar se o login automático via cookies funcionou
    time.sleep(3)  # Aguardar estabilização
    current_url = driver.current_url
    
    # Verificar se já está logado (não está na tela de login)
    if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
        print('[BACEN] ✅ Login automático realizado via cookies! Pulando login manual.')
        return driver
    
    print('[BACEN] 📋 Cookies não funcionaram ou primeiro acesso. Injetando tabela de dados de login...')
    dados_login(driver)
    
    # Integração: carrega dados extraídos do processo do arquivo do projeto
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
            print('[BACEN][AVISO] Arquivo de dados do processo não encontrado.')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao carregar dados do processo: {e}')
    
    print('[BACEN] ✅ SISBAJUD aberto com tabela de login injetada.')
    print('[BACEN] 👤 Faça login manualmente e aguarde a detecção automática.')
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
    Injeta uma barra de automações moderna e organizada no SISBAJUD
    """
    print('[KAIZEN] Injetando barra de automações no SISBAJUD...')
    
    # Aguardar página estar pronta
    try:
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)
    except Exception as e:
        print(f'[KAIZEN] Timeout aguardando página: {e}, continuando...')
    
    try:
        driver.execute_script('''
            function injetarBarraAutomacoes() {
                console.log('[KAIZEN] Iniciando injeção da barra de automações...');
                
                // Remover barra existente se houver
                let old = document.getElementById('kaizen_barra_automacoes');
                if (old) {
                    old.remove();
                    console.log('[KAIZEN] Barra antiga removida');
                }
                
                // Criar container principal
                let barra = document.createElement('div');
                barra.id = 'kaizen_barra_automacoes';
                barra.style = `
                    position: fixed !important;
                    bottom: 20px !important;
                    left: 50% !important;
                    transform: translateX(-50%) !important;
                    z-index: 2147483647 !important;
                    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%) !important;
                    border-radius: 16px !important;
                    box-shadow: 0 8px 32px rgba(25, 118, 210, 0.4) !important;
                    padding: 12px 20px !important;
                    font-family: 'Segoe UI', Arial, sans-serif !important;
                    display: flex !important;
                    align-items: center !important;
                    gap: 12px !important;
                    backdrop-filter: blur(10px) !important;
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                `;
                
                // Título da barra
                let titulo = document.createElement('span');
                titulo.textContent = '🤖 AUTOMAÇÕES SISBAJUD';
                titulo.style = `
                    color: white !important;
                    font-weight: bold !important;
                    font-size: 12px !important;
                    margin-right: 8px !important;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
                `;
                barra.appendChild(titulo);
                
                // Separador
                let separador = document.createElement('div');
                separador.style = `
                    width: 1px !important;
                    height: 24px !important;
                    background: rgba(255, 255, 255, 0.3) !important;
                    margin: 0 4px !important;
                `;
                barra.appendChild(separador);
                
                // Botões de automação
                const botoes = [
                    { id: 'nova_minuta_bloqueio', texto: '🔒 Nova Minuta', titulo: 'Criar nova minuta de bloqueio' },
                    { id: 'nova_minuta_endereco', texto: '🏠 Minuta Endereço', titulo: 'Criar minuta de endereço' },
                    { id: 'preencher_campos', texto: '📝 Preencher', titulo: 'Preencher dados do processo' },
                    { id: 'preencher_invertido', texto: '🔄 Polo Passivo', titulo: 'Preencher com polo passivo' },
                    { id: 'consultar_teimosinha', texto: '🔍 Consultar', titulo: 'Consultar teimosinha' },
                    { id: 'consultar_minuta', texto: '📋 Minutas', titulo: 'Consultar minutas existentes' }
                ];
                
                botoes.forEach(config => {
                    let btn = document.createElement('button');
                    btn.id = config.id;
                    btn.textContent = config.texto;
                    btn.title = config.titulo;
                    btn.style = `
                        background: rgba(255, 255, 255, 0.95) !important;
                        color: #1976d2 !important;
                        border: none !important;
                        border-radius: 10px !important;
                        padding: 8px 12px !important;
                        font-size: 11px !important;
                        font-weight: 600 !important;
                        cursor: pointer !important;
                        transition: all 0.3s ease !important;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
                        text-shadow: none !important;
                        font-family: inherit !important;
                    `;
                    
                    // Efeitos hover
                    btn.onmouseenter = function() {
                        this.style.transform = 'translateY(-2px) scale(1.05)';
                        this.style.boxShadow = '0 4px 16px rgba(0,0,0,0.2)';
                        this.style.background = 'white';
                    };
                    
                    btn.onmouseleave = function() {
                        this.style.transform = 'translateY(0) scale(1)';
                        this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                        this.style.background = 'rgba(255, 255, 255, 0.95)';
                    };
                    
                    // Evento de clique
                    btn.onclick = function() {
                        console.log('[KAIZEN] Botão clicado:', config.id);                        window.kaizen_evt = config.id;
                        
                        // Efeito visual de clique
                        this.style.transform = 'scale(0.95)';
                        setTimeout(() => {
                            this.style.transform = 'scale(1)';
                        }, 150);
                    };
                    
                    barra.appendChild(btn);
                });
                
                // Adicionar ao DOM
                document.body.appendChild(barra);
                
                console.log('[KAIZEN] ✅ Barra de automações injetada com sucesso!');
                return true;
            }
            
            // Executar a injeção
            return injetarBarraAutomacoes();
        ''')
        
        print('[KAIZEN] ✅ Barra de automações SISBAJUD injetada com sucesso!')
        
    except Exception as e:
        print(f'[KAIZEN] ❌ Erro ao injetar barra: {e}')
        import traceback
        traceback.print_exc()
        
    return True

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
    try:        return driver.execute_script("""
            let radio = document.querySelector('mat-radio-button[class*="mat-radio-checked"]');
            return radio && radio.innerText.includes('Requisição de informações');
        """)
    except Exception as e:
        print(f'[KAIZEN] Erro ao verificar requisição de endereço: {e}')
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
    Navega para a tela de consulta de teimosinha do SISBAJUD, preenche o número do processo
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
    
    # Se numero_processo é uma lista, pegar o primeiro elemento
    if isinstance(numero_processo, list):
        numero_processo = numero_processo[0] if numero_processo else ""
    
    if not numero_processo:
        print('[KAIZEN][ERRO] Número do processo vazio.')
        return
    
    print(f'[KAIZEN] Consultando Teimosinha para o processo: {numero_processo}')

    try:
        current_url = driver.current_url
        print(f'[KAIZEN] URL inicial: {current_url}')
        
        # Verificar se já estamos na página de teimosinha
        if '/teimosinha' in current_url:
            print('[KAIZEN] ✅ Já estamos na página de teimosinha, pulando navegação inicial.')
        else:
            print('[KAIZEN] Navegando para página de teimosinha...')
            
            # Passo 1: Clicar no menu de navegação
            print('[KAIZEN] Passo 1: Abrindo menu de navegação...')
            menu_clicado = driver.execute_script("""
                let btn = document.querySelector('button[aria-label*="menu de navegação"], button[aria-label*="Abri menu de navegação"]');
                if (btn) {
                    console.log('[KAIZEN] Menu de navegação encontrado, clicando...');
                    btn.click();
                    return true;
                } else {
                    console.log('[KAIZEN][ERRO] Menu de navegação não encontrado');
                    return false;
                }
            """)
            
            if not menu_clicado:
                print('[KAIZEN][ERRO] Falha ao clicar no menu de navegação')
                return
                
            time.sleep(0.8)
            
            # Passo 2: Ir para Teimosinha
            print('[KAIZEN] Passo 2: Navegando para Teimosinha...')
            teimosinha_clicado = driver.execute_script("""
                let link = document.querySelector('a[aria-label*="Ir para Teimosinha"]');
                if (link) {
                    console.log('[KAIZEN] Link Teimosinha encontrado, clicando...');
                    link.click();
                    return true;
                } else {
                    console.log('[KAIZEN][ERRO] Link Teimosinha não encontrado');
                    return false;
                }
            """)
            
            if not teimosinha_clicado:
                print('[KAIZEN][ERRO] Falha ao clicar no link Teimosinha')
                return
                
            time.sleep(1.5)
        
        # Passo 3: Verificar se chegamos na página de teimosinha
        print('[KAIZEN] Passo 3: Verificando URL de teimosinha...')
        for tentativa in range(10):
            current_url = driver.current_url
            print(f'[KAIZEN] Tentativa {tentativa + 1}/10 - URL atual: {current_url}')
            
            if '/teimosinha' in current_url:
                print('[KAIZEN] ✅ Página de teimosinha detectada!')
                break
                
            time.sleep(1)
        else:
            print(f'[KAIZEN][AVISO] Página de teimosinha não detectada após 10 tentativas. URL final: {current_url}')
            print('[KAIZEN] Tentando continuar mesmo assim...')        
        # Passo 4: Preencher campo do número do processo usando Python puro (mais robusto)
        print('[KAIZEN] Passo 4: Preenchendo número do processo com Python/Selenium...')
        
        try:
            # Lista de seletores para tentar encontrar o campo do número do processo
            seletores_processo = [
                'input[formcontrolname="numeroProcesso"]',
                'input[data-placeholder="Número do processo"]',
                'input[placeholder="Número do Processo"]',
                'input[placeholder*="Processo"]',
                'input[placeholder="Nº do processo"]',
                'input[aria-label="Número do processo"]',
                'input[id*="numeroProcesso"]',
                'input[name*="numeroProcesso"]',
                'input[id^="mat-input-"]'
            ]
            
            campo_encontrado = False
            for seletor in seletores_processo:
                try:
                    # Aguardar até o campo aparecer (máximo 5 segundos)
                    campo = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                    
                    # Limpar e preencher o campo
                    campo.clear()
                    campo.send_keys(numero_processo)
                    
                    # Disparar eventos para Angular/Material
                    driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        arguments[0].blur();
                    """, campo)
                    
                    print(f'[KAIZEN] ✅ Campo "Número do Processo" preenchido com: {numero_processo}')
                    print(f'[KAIZEN] Seletor usado: {seletor}')
                    campo_encontrado = True
                    break
                    
                except Exception:
                    continue
            
            if not campo_encontrado:
                print('[KAIZEN][ERRO] Campo "Número do Processo" não encontrado em nenhum seletor')
                return
            
            # Aguardar um pouco para o preenchimento ser processado
            time.sleep(1)
            
            # Passo 5: Encontrar e clicar no botão "Consultar" usando Python puro
            print('[KAIZEN] Passo 5: Procurando e clicando no botão "Consultar"...')
            
            botao_encontrado = False
            
            # Primeiro, tentar encontrar por texto usando XPath (mais confiável)
            try:
                botao = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Consultar') or contains(.//span/text(), 'Consultar')]"))
                )
                botao.click()
                print('[KAIZEN] ✅ Botão "Consultar" clicado com sucesso (XPath)')
                botao_encontrado = True
                
            except Exception as e:
                print(f'[KAIZEN] XPath para botão Consultar falhou: {e}')
                
                # Fallback: buscar todos os botões e verificar texto
                try:
                    botoes = driver.find_elements(By.TAG_NAME, 'button')
                    for botao in botoes:
                        if not botao.is_enabled() or not botao.is_displayed():
                            continue
                            
                        texto_botao = botao.get_attribute('innerText') or botao.text or ''
                        if 'consultar' in texto_botao.lower():
                            botao.click()
                            print(f'[KAIZEN] ✅ Botão "Consultar" clicado com sucesso: {texto_botao}')
                            botao_encontrado = True
                            break
                            
                except Exception as e2:
                    print(f'[KAIZEN][ERRO] Fallback para botão Consultar também falhou: {e2}')
            
            if not botao_encontrado:
                print('[KAIZEN][ERRO] Botão "Consultar" não encontrado ou não clicável')
                return
            
            # Aguardar a tabela de resultados carregar
            print('[KAIZEN] Aguardando carregamento da tabela de resultados...')
            
            try:
                # Aguardar tabela aparecer (máximo 15 segundos)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table, tbody, tr'))
                )
                print('[KAIZEN] ✅ Tabela de resultados carregada!')
                
                # Aguardar mais um pouco para garantir que os dados foram preenchidos
                time.sleep(2)
                
                # Buscar linhas com "JUN DE 2025"
                _buscar_linhas_jun_2025(driver)
                
            except Exception as e:
                print(f'[KAIZEN][AVISO] Tabela não detectada no tempo esperado: {e}')
                print('[KAIZEN] Tentando buscar linhas mesmo assim...')
                _buscar_linhas_jun_2025(driver)
                
        except Exception as e:
            print(f'[KAIZEN][ERRO] Falha no preenchimento/consulta Python: {e}')

    except Exception as e:
        print(f'[KAIZEN][ERRO] Exceção ao executar consulta teimosinha: {e}')

def _buscar_linhas_jun_2025(driver):
    """
    Busca na tabela de resultados as linhas que contêm "JUN DE 2025"
    e exibe o ID da série correspondente usando Python puro (mais robusto que JavaScript).
    """
    try:
        print('[KAIZEN] Buscando linhas com "JUN DE 2025" na tabela...')
        
        # Buscar todas as tabelas na página
        tabelas = driver.find_elements(By.TAG_NAME, 'table')
        
        if not tabelas:
            print('[KAIZEN][AVISO] Nenhuma tabela encontrada na página')
            return
        
        print(f'[KAIZEN] Encontradas {len(tabelas)} tabela(s) na página')
        
        linhas_encontradas = []
        
        for indice_tabela, tabela in enumerate(tabelas):
            # Buscar todas as linhas da tabela
            linhas = tabela.find_elements(By.TAG_NAME, 'tr')
            
            for indice_linha, linha in enumerate(linhas):
                try:
                    texto_linha = linha.text or linha.get_attribute('innerText') or ''
                    
                    # Verificar se a linha contém "JUN DE 2025" (case-insensitive)
                    if 'JUN DE 2025' in texto_linha.upper():
                        print(f'[KAIZEN] ✅ Linha com "JUN DE 2025" encontrada!')
                        
                        # Buscar células da linha para encontrar o ID da série
                        celulas = linha.find_elements(By.TAG_NAME, 'td') + linha.find_elements(By.TAG_NAME, 'th')
                        
                        id_serie = 'ID não encontrado'
                        
                        # Verificar cada célula
                        for indice_celula, celula in enumerate(celulas):
                            try:
                                texto_celula = celula.text or celula.get_attribute('innerText') or ''
                                
                                # Procurar por padrões de ID (números com 4+ dígitos)
                                import re
                                matches = re.findall(r'\b\d{4,}\b', texto_celula)
                                if matches:
                                    id_serie = matches[0]  # Pegar o primeiro match
                                    break
                                
                                # Verificar atributos HTML que possam conter ID
                                if celula.get_attribute('id'):
                                    id_serie = celula.get_attribute('id')
                                    break
                                if celula.get_attribute('data-id'):
                                    id_serie = celula.get_attribute('data-id')
                                    break
                                if celula.get_attribute('data-serie'):
                                    id_serie = celula.get_attribute('data-serie')
                                    break
                                    
                            except Exception as e:
                                continue
                        
                        # Baseado no HTML fornecido, o ID da série está na primeira coluna
                        # Vamos tentar pegar especificamente a primeira célula
                        if id_serie == 'ID não encontrado' and celulas:
                            try:
                                primeira_celula = celulas[0]
                                texto_primeira = primeira_celula.text or primeira_celula.get_attribute('innerText') or ''
                                # Remove espaços e pega apenas números
                                id_candidato = ''.join(filter(str.isdigit, texto_primeira))
                                if id_candidato and len(id_candidato) >= 4:
                                    id_serie = id_candidato
                            except Exception:
                                pass
                        
                        resultado = {
                            'tabela': indice_tabela,
                            'linha': indice_linha,
                            'id_serie': id_serie,
                            'texto_completo': texto_linha.strip()
                        }
                        
                        linhas_encontradas.append(resultado)
                        
                except Exception as e:
                    continue
        
        # Exibir resultados
        if linhas_encontradas:
            total = len(linhas_encontradas)
            print(f'[KAIZEN] ✅ Encontradas {total} linha(s) com "JUN DE 2025":')
            
            for i, linha in enumerate(linhas_encontradas, 1):
                id_serie = linha.get('id_serie', 'N/A')
                texto = linha.get('texto_completo', '')[:150]  # Primeiros 150 caracteres
                
                print(f'[KAIZEN] Linha {i}:')
                print(f'  - ID da Série: {id_serie}')
                print(f'  - Texto: {texto}...')
                print('  ---')
                
        else:
            print('[KAIZEN] ❌ Nenhuma linha com "JUN DE 2025" foi encontrada na tabela.')
            
    except Exception as e:
        print(f'[KAIZEN][ERRO] Exceção ao buscar linhas JUN DE 2025: {e}')
        import traceback
        traceback.print_exc()

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
            # Extrair dados de forma segura, tratando listas e valores nulos
            def safe_extract(data, key, default=""):
                """Extrai dados de forma segura, convertendo listas para string se necessário"""
                value = data.get(key, default)
                if isinstance(value, list):
                    if value:  # Se a lista não está vazia
                        return str(value[0]) if value[0] else default
                    return default
                return str(value) if value else default
            
            def safe_escape(text):
                """Escapa texto para JavaScript de forma segura"""
                if not text:
                    return ""
                return str(text).replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            
            # Extrair número do processo
            numero = safe_escape(safe_extract(processo_dados_extraidos, "numero"))
            
            # Extrair dados do autor
            autor_list = processo_dados_extraidos.get("autor", [])
            if autor_list and len(autor_list) > 0:
                autor_data = autor_list[0]
                nome_ativo = safe_escape(autor_data.get("nome", ""))
                doc_ativo = safe_escape(autor_data.get("cpfcnpj", ""))
            else:
                nome_ativo = ""
                doc_ativo = ""
            
            # Extrair dados do réu
            reu_list = processo_dados_extraidos.get("reu", [])
            if reu_list and len(reu_list) > 0:
                reu_data = reu_list[0]
                nome_passivo = safe_escape(reu_data.get("nome", ""))
                doc_passivo = safe_escape(reu_data.get("cpfcnpj", ""))
            else:
                nome_passivo = ""
                doc_passivo = ""
            
            print(f'[KAIZEN] Integrando dados: numero={numero}, autor={nome_ativo}, reu={nome_passivo}')
            
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
            print('[KAIZEN] ✅ Dados do processo integrados ao storage local.')
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao integrar dados do processo: {e}')
        import traceback
        traceback.print_exc()

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

# ===================== CONFIGURAÇÃO DO DRIVER FIREFOX =====================
def criar_driver_firefox_sisb():
    """Cria driver Firefox para SISBAJUD automaticamente - versão otimizada com cookies"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    import subprocess
    
    print('[BACEN][DRIVER] Criando driver Firefox SISBAJUD (versão otimizada com cookies)...')
    
    # Tentar primeiro a abordagem simples que funciona
    try:
        print('[BACEN][DRIVER] Iniciando Firefox Developer Edition (modo otimizado)...')
        options = Options()
        options.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
        options.add_argument("--new-instance")
        options.add_argument("--no-remote")
        
        driver = webdriver.Firefox(options=options)
        print('[BACEN][DRIVER] ✅ Firefox SISBAJUD iniciado com sucesso!')
        
        # Aguardar estabilização
        time.sleep(1)
        
        # Tentar carregar cookies salvos primeiro
        print('[BACEN][DRIVER] Tentando carregar cookies salvos...')
        cookies_carregados = carregar_cookies_sisbajud(driver)
        
        if cookies_carregados:
            print('[BACEN][DRIVER] ✅ Cookies carregados! Verificando se login automático funcionou...')
            
            # Verificar se já está logado (não está na tela de login)
            current_url = driver.current_url
            if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                print('[BACEN][DRIVER] ✅ Login automático realizado com sucesso via cookies!')
                return driver
            else:
                print('[BACEN][DRIVER] ⚠️ Cookies carregados mas ainda na tela de login. Prosseguindo...')
        else:
            print('[BACEN][DRIVER] Navegando automaticamente para SISBAJUD...')
            driver.get('https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud&redirect_uri=https%3A%2F%2Fsisbajud.cnj.jus.br%2F&state=da9cbb01-be67-419d-8f19-f2c067a9e80f&response_mode=fragment&response_type=code&scope=openid&nonce=3d61a8ca-bb98-4924-88f9-9a0cb00f9f0e')
        
        return driver
        
    except Exception as e:
        print(f'[BACEN][DRIVER][ERRO] Falha na abordagem otimizada: {e}')
        
        # Fallback: tentar com perfil específico apenas se a abordagem simples falhar
        try:
            print('[BACEN][DRIVER] Tentando com perfil específico como fallback...')
            perfil_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\arrn673i.Sisb"
            
            options_perfil = Options()
            options_perfil.binary_location = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
            options_perfil.add_argument(f"--profile={perfil_path}")
            options_perfil.add_argument("--new-instance")
            options_perfil.add_argument("--no-remote")
            
            driver = webdriver.Firefox(options=options_perfil)
            print('[BACEN][DRIVER] ✅ Firefox SISBAJUD iniciado com perfil específico!')
            
            time.sleep(1)
            driver.get('https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud&redirect_uri=https%3A%2F%2Fsisbajud.cnj.jus.br%2F&state=da9cbb01-be67-419d-8f19-f2c067a9e80f&response_mode=fragment&response_type=code&scope=openid&nonce=3d61a8ca-bb98-4924-88f9-9a0cb00f9f0e')
            
            return driver
            
        except Exception as e2:
            print(f'[BACEN][DRIVER][ERRO] Falha no fallback com perfil: {e2}')
            print('[BACEN][DRIVER][ERRO] Não foi possível criar o driver SISBAJUD')
            return None

def aguardar_login_manual_sisbajud(driver):
    """
    Aguarda o usuário fazer login manual no SISBAJUD
    Detecta quando o login foi realizado verificando mudanças na URL ou elementos da página
    """
    print('[BACEN] 👤 Aguardando login manual no SISBAJUD...')
    print('[BACEN] 💡 Faça o login manualmente na janela do SISBAJUD e aguarde.')
    
    login_detectado = False
    tentativas = 0
    max_tentativas = 300  # 5 minutos (300 * 1 segundo)
    
    while not login_detectado and tentativas < max_tentativas:
        try:
            current_url = driver.current_url
            
            # Verificar se saiu da tela de login (indicadores de login bem-sucedido)
            indicadores_login_sucesso = [
                'sisbajud.cnj.jus.br/web/',  # Após login vai para área principal
                'dashboard',  # Dashboard principal
                'home',  # Página inicial
                'minuta',  # Área de minutas
                'consulta'  # Área de consultas
            ]
            
            # Verificar se não está mais na tela de login
            if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                # Verificar se há elementos que indicam login bem-sucedido
                elementos_pos_login = driver.execute_script("""
                    // Verificar elementos que aparecem após login
                    let indicadores = [
                        'button[aria-label*="menu"]',  // Menu principal
                        'mat-toolbar',  // Barra de ferramentas
                        '.mat-toolbar',  // Barra superior
                        '[role="navigation"]',  // Navegação
                        'sisbajud-home',  // Componente home
                        'sisbajud-consulta',  // Componentes do SISBAJUD
                        'sisbajud-minuta'
                    ];
                    
                    for (let seletor of indicadores) {
                        if (document.querySelector(seletor)) {
                            return true;
                        }
                    }
                    return false;
                """)
                
                if elementos_pos_login:
                    login_detectado = True
                    print(f'[BACEN] ✅ Login detectado! URL atual: {current_url}')
                    break
              # Verificar por URLs específicas de sucesso
            for indicador in indicadores_login_sucesso:
                if indicador in current_url.lower():
                    login_detectado = True
                    print(f'[BACEN] ✅ Login detectado via URL! URL atual: {current_url}')
                    break
            
            if login_detectado:
                break
                
        except Exception as e:
            print(f'[BACEN][DEBUG] Erro ao verificar login (tentativa {tentativas}): {e}')
        
        tentativas += 1
        if tentativas % 30 == 0:  # A cada 30 segundos
            print(f'[BACEN] ⏳ Ainda aguardando login... ({tentativas//30} min)')
        
        time.sleep(1)  # Aguardar 1 segundo antes da próxima verificação
    
    if login_detectado:
        print('[BACEN] ✅ Login manual detectado com sucesso!')
        
        # Salvar cookies após login bem-sucedido
        print('[BACEN] 💾 Salvando cookies para login automático futuro...')
        try:
            salvar_cookies_sisbajud(driver)
        except Exception as e:
            print(f'[BACEN][ERRO] Falha ao salvar cookies: {e}')
        
        return True
    else:
        print('[BACEN] ⚠️ Timeout aguardando login manual (5 minutos). Continuando mesmo assim...')
        return False

def processar_evento_kaizen(driver_sisbajud, evento):
    """
    Processa eventos de automação Kaizen no SISBAJUD
    """
    try:
        print(f'[BACEN][KAIZEN] Processando evento: {evento}')
        
        if evento == 'nova_minuta_bloqueio':
            print('[BACEN][KAIZEN] Executando: Nova minuta de bloqueio')
            kaizen_nova_minuta(driver_sisbajud, endereco=False)
            
        elif evento == 'nova_minuta_endereco':
            print('[BACEN][KAIZEN] Executando: Nova minuta de endereço')
            kaizen_nova_minuta(driver_sisbajud, endereco=True)
            
        elif evento == 'preencher_campos':
            print('[BACEN][KAIZEN] Executando: Preencher campos (polo ativo)')
            kaizen_preencher_campos(driver_sisbajud, invertido=False)
            
        elif evento == 'preencher_invertido':
            print('[BACEN][KAIZEN] Executando: Preencher campos (polo passivo)')
            kaizen_preencher_campos(driver_sisbajud, invertido=True)
            
        elif evento == 'consultar_teimosinha':
            print('[BACEN][KAIZEN] Executando: Consultar teimosinha')
            kaizen_consultar_teimosinha(driver_sisbajud)
            
        elif evento == 'consultar_minuta':
            print('[BACEN][KAIZEN] Executando: Consultar minutas')
            kaizen_consultar_minuta(driver_sisbajud)
            
        else:
            print(f'[BACEN][KAIZEN] Evento desconhecido: {evento}')
            
    except Exception as e:
        print(f'[BACEN][KAIZEN][ERRO] Erro ao processar evento {evento}: {e}')
        import traceback
        traceback.print_exc()

# ===================== GERENCIADOR DE DRIVERS SEPARADOS =====================

def executar_driver_pje():
    """
    DRIVER 1: PJe - Completamente autônomo
    Executa login, extração de dados e interface com botão único
    """
    print('[DRIVER 1][PJe] === INICIANDO DRIVER PJe ===')
    
    try:
        print('[DRIVER 1] Passo 1: Criando driver PJe...')
        driver_pje = criar_driver(headless=False)
        
        if not driver_pje:
            print('[DRIVER 1][ERRO] Falha ao iniciar o driver PJe.')
            return None
        
        print('[DRIVER 1] Passo 2: Driver PJe criado com sucesso!')
        
        # Login no PJe
        print('[DRIVER 1] Passo 3: Realizando login no PJe...')
        if not login_func(driver_pje):
            print('[DRIVER 1][ERRO] Falha no login PJe.')
            driver_pje.quit()
            return None
        
        print('[DRIVER 1] Passo 4: Login PJe realizado com sucesso!')
        
        # Navegar para URL de teste
        url_teste = 'https://pje.trt2.jus.br/pjekz/processo/2661854/detalhe'
        print(f'[DRIVER 1] Passo 5: Navegando para URL: {url_teste}')
        driver_pje.get(url_teste)
        time.sleep(3)
        
        # Extrair dados do processo
        print('[DRIVER 1] Passo 6: Extraindo dados do processo...')
        global processo_dados_extraidos
        processo_dados_extraidos = extrair_dados_processo(driver_pje)
        print('[DRIVER 1] Dados extraídos:', processo_dados_extraidos)
        
        # Salvar dados para o Driver 2
        salvar_dados_processo_temp()
        
        # Injetar interface
        print('[DRIVER 1] Passo 7: Injetando interface PJe...')
        injetar_botao_sisbajud_pje(driver_pje)
        bind_eventos(driver_pje)
        
        print('[DRIVER 1] ✅ PJe pronto! Botão SISBAJUD disponível.')
        return driver_pje
        
    except Exception as e:
        print(f'[DRIVER 1][ERRO] Erro crítico: {e}')
        return None

def executar_driver_sisbajud(modo_teste=False):
    """
    DRIVER 2: SISBAJUD - Completamente autônomo
    Pode ser executado independentemente para testes
    
    Args:
        modo_teste (bool): Se True, tenta login automático via AHK se cookies falharem
    """
    print('[DRIVER 2][SISBAJUD] === INICIANDO DRIVER SISBAJUD ===')
    
    try:
        print('[DRIVER 2] Passo 1: Criando driver SISBAJUD...')
        driver_sisbajud = criar_driver_firefox_sisb()
        
        if not driver_sisbajud:
            print('[DRIVER 2][ERRO] Falha ao criar driver SISBAJUD.')
            return None
        
        print('[DRIVER 2] Passo 2: Driver SISBAJUD criado com sucesso!')
        
        # Verificar login automático via cookies
        current_url = driver_sisbajud.current_url
        ja_logado = not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms'])
        
        if ja_logado:
            print('[DRIVER 2] ✅ Login automático detectado via cookies!')
        else:
            print('[DRIVER 2] Passo 3: Preparando login manual...')
            
            # Injetar dados de login
            dados_login(driver_sisbajud)
            
            # TEMPORARIAMENTE DESABILITADO: Login AHK
            # if modo_teste:
            #     if tentar_login_automatico_ahk(driver_sisbajud):
            #         print('[DRIVER 2] ✅ Login automático via AHK realizado!')
            #     else:
            #         print('[DRIVER 2] ⚠️ Login AHK falhou. Aguardando login manual...')
            #         aguardar_login_manual_sisbajud(driver_sisbajud)
            # else:
            
            print('[DRIVER 2] 👤 Aguardando login manual...')
            aguardar_login_manual_sisbajud(driver_sisbajud)
        
        print('[DRIVER 2] Passo 4: Inicializando componentes SISBAJUD...')
        
        # Carregar dados do processo (se disponíveis)
        carregar_dados_processo_temp()
        
        # Inicializar componentes
        monitor_janela_sisbajud(driver_sisbajud)
        integrar_storage_processo(driver_sisbajud)
        
        # Injetar barra de automações
        print('[DRIVER 2] Passo 5: Injetando barra de automações...')
        injetar_menu_kaizen_sisbajud(driver_sisbajud)
        
        print('[DRIVER 2] ✅ SISBAJUD pronto! Barra de automações ativa.')
        return driver_sisbajud
        
    except Exception as e:
        print(f'[DRIVER 2][ERRO] Erro crítico: {e}')
        import traceback
        traceback.print_exc()
        return None

def carregar_dados_processo_temp():
    """Carrega dados do processo salvos pelo Driver 1"""
    global processo_dados_extraidos
    try:
        import os
        project_path = os.path.dirname(os.path.abspath(__file__))
        dados_path = os.path.join(project_path, 'dadosatuais.json')
        
        if os.path.exists(dados_path):
            with open(dados_path, 'r', encoding='utf-8') as f:
                processo_dados_extraidos = json.load(f)
            print('[DRIVER 2] Dados do processo carregados:', processo_dados_extraidos)
        else:
            print('[DRIVER 2][AVISO] Nenhum dado de processo encontrado.')
    except Exception as e:
        print(f'[DRIVER 2][ERRO] Falha ao carregar dados: {e}')

def monitorar_driver_sisbajud(driver_sisbajud):
    """
    Loop de monitoramento exclusivo do Driver 2
    Processa todos os eventos de automação
    """
    print('[DRIVER 2] 🔄 Iniciando monitoramento de eventos...')
    
    try:
        while True:
            # Verificar eventos de automação
            evento_kaizen = driver_sisbajud.execute_script("""
                return window.kaizen_evt || null;
            """)
            
            if evento_kaizen:
                print(f'[DRIVER 2] 🔧 Evento detectado: {evento_kaizen}')
                processar_evento_kaizen(driver_sisbajud, evento_kaizen)
                # Limpar evento
                driver_sisbajud.execute_script("window.kaizen_evt = null;")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('[DRIVER 2] ⚠️ Monitoramento interrompido pelo usuário.')
    except Exception as e:
        print(f'[DRIVER 2][ERRO] Erro no monitoramento: {e}')

# ===================== FUNÇÃO PRINCIPAL REORGANIZADA =====================

def main():
    """
    Função principal com drivers separados
    Permite execução independente ou conjunta
    """
    print('[BACEN] === INICIANDO SISTEMA BACEN.PY ===')
    print('[BACEN] Escolha o modo de execução:')
    print('[BACEN] 1. Ambos os drivers (modo completo)')
    print('[BACEN] 2. Apenas Driver SISBAJUD (modo teste)')
    
    # Para desenvolvimento/teste: forçar modo SISBAJUD apenas
    modo = input('[BACEN] Digite 1 ou 2 (Enter = modo completo): ').strip()
    
    if modo == '2':
        # MODO TESTE: Apenas Driver SISBAJUD
        print('[BACEN] 🧪 MODO TESTE: Executando apenas Driver SISBAJUD')
        driver_sisbajud = executar_driver_sisbajud()
        
        if driver_sisbajud:
            print('[BACEN] 💡 Use os botões da barra inferior para testar automações.')
            monitorar_driver_sisbajud(driver_sisbajud)
        
    else:
        # MODO COMPLETO: Ambos os drivers
        print('[BACEN] 🔄 MODO COMPLETO: Executando ambos os drivers')
        
        # Executar Driver 1 (PJe)
        driver_pje = executar_driver_pje()
        if not driver_pje:
            print('[BACEN][ERRO] Falha no Driver PJe. Encerrando.')
            return
        
        driver_sisbajud = None
        
        # Loop de aguardar evento do Driver 1
        print('[BACEN] Aguardando clique no botão SISBAJUD...')
        while True:
            evento = checar_evento(driver_pje)
            
            if evento == 'abrir_sisbajud':
                print('[BACEN] 🏦 Acionando Driver SISBAJUD...')
                driver_sisbajud = executar_driver_sisbajud()
                
                if driver_sisbajud:
                    print('[BACEN] ✅ Ambos os drivers ativos!')
                    # Monitorar apenas o Driver 2 daqui em diante
                    monitorar_driver_sisbajud(driver_sisbajud)
                    break
            
            time.sleep(1)
    
    print('[BACEN] Sistema finalizado.')

def main_sisbajud_apenas():
    """
    Função para testar apenas o SISBAJUD (desenvolvimento)
    """
    print('[BACEN] 🧪 MODO DESENVOLVIMENTO: Apenas SISBAJUD')
    
    driver_sisbajud = executar_driver_sisbajud()
    if driver_sisbajud:
        print('[BACEN] 💡 Testando automações no SISBAJUD...')
        monitorar_driver_sisbajud(driver_sisbajud)

def obter_caminho_autohotkey():
    """
    Extrai o caminho do executável do AutoHotkey do driver_config.py
    
    Returns:
        str: Caminho do executável do AutoHotkey ou None se não encontrado
    """
    import re
    import os
    
    try:
        # Ler o arquivo driver_config.py
        config_path = os.path.join(os.path.dirname(__file__), 'driver_config.py')
        if not os.path.exists(config_path):
            print(f'[CONFIG] ❌ Arquivo driver_config.py não encontrado: {config_path}')
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Procurar pelo caminho do AutoHotkey usando regex
        # Procura por padrões como: "C:\\Program Files\\AutoHotkey\\AutoHotkey.exe"
        padrao = r'["\']([C-Z]:\\[^"\']*AutoHotkey[^"\']*\.exe)["\']'
        matches = re.findall(padrao, conteudo, re.IGNORECASE)
        
        if matches:
            # Pegar o primeiro match encontrado
            caminho_ahk = matches[0]
            print(f'[CONFIG] ✅ Caminho do AutoHotkey encontrado: {caminho_ahk}')
            return caminho_ahk
        else:
            print('[CONFIG] ❌ Caminho do AutoHotkey não encontrado no driver_config.py')
            return None
            
    except Exception as e:
        print(f'[CONFIG] ❌ Erro ao ler driver_config.py: {e}')
        return None

def tentar_login_automatico_ahk(driver_sisbajud):
    """
    Tenta login automático no SISBAJUD usando APENAS loginsisb.ahk
    Versão simplificada focada em um único arquivo funcional
    
    Args:
        driver_sisbajud: Driver do Firefox para SISBAJUD
        
    Returns:
        bool: True se login foi bem-sucedido, False caso contrário
    """
    import subprocess
    import time
    import os
    
    try:
        # Usar APENAS o arquivo loginsisb.ahk
        script_ahk = os.path.join(os.path.dirname(__file__), 'loginsisb.ahk')
        
        if not os.path.exists(script_ahk):
            print(f'[AHK] ❌ Script loginsisb.ahk não encontrado: {script_ahk}')
            return False
        
        print('[AHK] ✅ Usando loginsisb.ahk (versão humanizada)')
        print('[AHK] 🤖 Executando script de login automático...')
        
        # Garantir que a janela do Firefox esteja em foco
        driver_sisbajud.switch_to.window(driver_sisbajud.current_window_handle)
        
        # Tentar focar no campo CPF (cursor deve estar lá)
        try:
            print('[AHK] 🎯 Preparando campo para digitação...')
            driver_sisbajud.execute_script("""
                // Tentar focar no primeiro campo de input visível
                let campos = document.querySelectorAll('input[type="text"], input[type="email"], input[name*="cpf"], input[placeholder*="CPF"]');
                for (let campo of campos) {
                    if (campo.offsetParent !== null && !campo.disabled) {
                        campo.focus();
                        campo.click();
                        console.log('Campo focado:', campo);
                        break;
                    }
                }
            """)
            time.sleep(0.5)
        except Exception as e:
            print(f'[AHK] ⚠️ Não foi possível focar campo via JS: {e}')
        
        # Obter caminho do AutoHotkey
        ahk_exe = obter_caminho_autohotkey()
        
        if not ahk_exe:
            # Fallback para o caminho padrão
            ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
            print(f'[AHK] ⚠️ Usando caminho padrão: {ahk_exe}')
        
        # Verificar se o executável existe
        if not os.path.exists(ahk_exe):
            print(f'[AHK] ❌ AutoHotkey não encontrado: {ahk_exe}')
            print('[AHK] 💡 Instale o AutoHotkey de: https://autohotkey.com/')
            return False
        
        # Executar o script AHK
        try:
            print(f'[AHK] 🚀 Executando: {ahk_exe} {script_ahk}')
            print('[AHK] ⏳ O script irá:')
            print('[AHK]    1. Aguardar 2 segundos')
            print('[AHK]    2. Digitar CPF onde estiver o cursor')
            print('[AHK]    3. Pressionar Tab para ir ao campo senha')
            print('[AHK]    4. Digitar a senha')
            print('[AHK]    5. Pressionar Enter para enviar')
            
            resultado = subprocess.run(
                [ahk_exe, script_ahk],
                timeout=60,  # 60 segundos para comportamento humanizado
                capture_output=True,
                text=True
            )
            
            if resultado.returncode == 0:
                print('[AHK] ✅ Script AHK executado com sucesso!')
            else:
                print(f'[AHK] ⚠️ Script terminou com código: {resultado.returncode}')
                if resultado.stderr:
                    print(f'[AHK] Stderr: {resultado.stderr}')
                if resultado.stdout:
                    print(f'[AHK] Stdout: {resultado.stdout}')
                    
        except subprocess.TimeoutExpired:
            print('[AHK] ⏰ Timeout: Script AHK demorou mais que 60 segundos')
            return False
        except FileNotFoundError:
            print(f'[AHK] ❌ Não foi possível executar: {ahk_exe}')
            return False
        except Exception as e:
            print(f'[AHK] ❌ Erro ao executar script: {e}')
            return False
        
        # Aguardar processamento do login (tempo para página responder)
        print('[AHK] ⏳ Aguardando resposta do login...')
        time.sleep(8)  # Tempo maior para comportamento humanizado
        
        # Verificar se o login foi bem-sucedido
        try:
            current_url = driver_sisbajud.current_url
            print(f'[AHK] 🔍 URL atual: {current_url}')
            
            # Verificar se saiu da página de login
            login_indicators = ['login', 'auth', 'realms', 'signin']
            ainda_na_tela_login = any(indicador in current_url.lower() for indicador in login_indicators)
            
            if not ainda_na_tela_login:
                print('[AHK] ✅ Login automático realizado com sucesso!')
                
                # Salvar cookies para próximas sessões
                try:
                    salvar_cookies_sisbajud(driver_sisbajud)
                    print('[AHK] 💾 Cookies salvos para login futuro')
                except Exception as e:
                    print(f'[AHK] ⚠️ Falha ao salvar cookies: {e}')
                
                return True
            else:
                print('[AHK] ❌ Ainda na tela de login. Verificando possíveis erros...')
                
                # Verificar mensagens de erro
                try:
                    erros = driver_sisbajud.execute_script("""
                        let erros = [];
                        let seletores = ['.error', '.alert-danger', '.invalid-feedback', '[class*="error"]', '.text-danger'];
                        seletores.forEach(seletor => {
                            document.querySelectorAll(seletor).forEach(el => {
                                if (el.textContent.trim()) {
                                    erros.push(el.textContent.trim());
                                }
                            });
                        });
                        return erros.join('; ');
                    """)
                    
                    if erros:
                        print(f'[AHK] ❌ Erro detectado na página: {erros}')
                    else:
                        print('[AHK] ❌ Login falhou mas sem mensagem de erro específica')
                        
                except Exception as e:
                    print(f'[AHK] ⚠️ Não foi possível verificar erros: {e}')
                
                return False
                
        except Exception as e:
            print(f'[AHK] ❌ Erro ao verificar status do login: {e}')
            return False
            
    except Exception as e:
        print(f'[AHK] ❌ Erro geral: {e}')
        return False


def main_teste_sisbajud():
    """
    Main de teste para executar apenas o SISBAJUD com login automático
    
    Este main permite testar o Driver 2 (SISBAJUD) de forma completamente
    autônoma, incluindo tentativa de login automático via AHK.
    """
    print('=' * 60)
    print('🧪 MODO TESTE: SISBAJUD AUTÔNOMO COM LOGIN AUTOMÁTICO')
    print('=' * 60)
    print()
    
    print('Este modo irá:')
    print('1. ✅ Iniciar apenas o Driver 2 (SISBAJUD)')
    print('2. 🤖 Tentar login automático via cookies')
    print('3. 🔧 Se falhar, tentar login automático via AHK')
    print('4. 👤 Se falhar, permitir login manual')
    print('5. 🚀 Inicializar todas as automações do SISBAJUD')
    print()
    
    confirmar = input('Deseja prosseguir com o teste? (s/n): ').lower().strip()
    
    if confirmar != 's':
        print('❌ Teste cancelado pelo usuário.')
        return
    
    print()
    print('🚀 Iniciando teste do SISBAJUD...')
    
    try:
        # Executar o Driver 2 em modo teste (com login AHK)
        driver_sisbajud = executar_driver_sisbajud(modo_teste=True)
        
        if driver_sisbajud:
            print()
            print('✅ Driver SISBAJUD iniciado com sucesso!')
            print('🔄 Monitoramento ativo. O driver continuará rodando...')
            print('💡 Pressione Ctrl+C para encerrar.')
            
            # Monitorar o driver
            monitorar_driver_sisbajud(driver_sisbajud)
            
        else:
            print('❌ Falha ao iniciar o Driver SISBAJUD.')
            
    except KeyboardInterrupt:
        print('\n⏹️ Teste interrompido pelo usuário.')
    except Exception as e:
        print(f'\n❌ Erro durante o teste: {e}')
        import traceback
        traceback.print_exc()


# Execução principal
if __name__ == "__main__":
    # Verificar se deve executar o teste do SISBAJUD
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['teste', 'test', 'sisbajud']:
        main_teste_sisbajud()
    else:
        main()
