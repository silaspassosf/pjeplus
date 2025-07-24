# sisb_modulos/kaizen_interface.py
# Interface Kaizen para SISBAJUD - Injeção de menus e gestão de eventos

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
                        console.log('[KAIZEN] Botão clicado:', config.id);
                        window.kaizen_evt = config.id;
                        
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
    """Verifica se algum evento do menu Kaizen foi ativado"""
    try:
        flag = driver.execute_script("return window.kaizen_evt;")
        if flag:
            driver.execute_script("window.kaizen_evt = '';")
        return flag
    except Exception:
        return None

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

def integrar_storage_processo(driver, processo_dados_extraidos):
    """
    Integra dados do processo com o storage local, similar ao JavaScript original
    """
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

    try:
        if processo_dados_extraidos:
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
