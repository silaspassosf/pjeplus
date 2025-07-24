# sisb_modulos/utils.py
# Funções auxiliares e utilitárias para SISBAJUD

import time
import subprocess
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def dados_login(driver):
    """Injeta tabela de dados de login no SISBAJUD"""
    try:
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
            print('[BACEN] Tabela de dados de login injetada.')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao injetar dados de login: {e}')

def monitor_janela_sisbajud(driver):
    """
    Monitora a janela SISBAJUD para detectar mudanças e aplicar automações
    """
    try:
        from .kaizen_interface import monitor_janela_sisbajud
        monitor_janela_sisbajud(driver)
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao monitorar janela SISBAJUD: {e}')

def monitorar_driver_sisbajud(driver):
    """
    Monitora o driver SISBAJUD para detectar login e aplicar automações
    """
    print('[BACEN] Monitorando driver SISBAJUD...')
    try:
        timeout = 300  # 5 minutos
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_url = driver.current_url
                
                # Verificar se está logado (não está na tela de login)
                if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                    print('[BACEN] ✅ Login detectado no SISBAJUD!')
                    
                    # Aguardar estabilização
                    time.sleep(2)
                    
                    # Injetar automações
                    from .kaizen_interface import injetar_menu_kaizen_sisbajud
                    injetar_menu_kaizen_sisbajud(driver)
                    
                    # Iniciar monitoramento contínuo
                    monitor_janela_sisbajud(driver)
                    
                    return True
                    
            except Exception as e:
                print(f'[BACEN][DEBUG] Erro no monitoramento: {e}')
                
            time.sleep(2)
        
        print('[BACEN][TIMEOUT] Timeout aguardando login no SISBAJUD')
        return False
        
    except Exception as e:
        print(f'[BACEN][ERRO] Falha no monitoramento do driver: {e}')
        return False

def monitorar_drivers_completo(driver_pje, driver_sisbajud):
    """
    Monitora ambos os drivers (PJe e SISBAJUD) simultaneamente
    """
    print('[BACEN] Monitoramento completo de drivers iniciado')
    try:
        # Monitorar PJe
        if driver_pje:
            from .interface_pje import bind_eventos, checar_evento
            bind_eventos(driver_pje)
            
        # Monitorar SISBAJUD
        if driver_sisbajud:
            monitorar_driver_sisbajud(driver_sisbajud)
            
        # Loop principal de monitoramento
        while True:
            try:
                # Verificar eventos no PJe
                if driver_pje:
                    evento_pje = checar_evento(driver_pje)
                    if evento_pje == 'abrir_sisbajud':
                        print('[BACEN] Evento: Abrir SISBAJUD detectado!')
                        # Aqui você pode adicionar lógica para abrir/focar o SISBAJUD
                        
                # Verificar eventos no SISBAJUD
                if driver_sisbajud:
                    from .kaizen_interface import checar_kaizen_evento
                    evento_kaizen = checar_kaizen_evento(driver_sisbajud)
                    if evento_kaizen:
                        print(f'[BACEN] Evento Kaizen detectado: {evento_kaizen}')
                        # Processar evento Kaizen
                        _processar_evento_kaizen(driver_sisbajud, evento_kaizen)
                        
                time.sleep(1)
                
            except Exception as e:
                print(f'[BACEN][ERRO] Erro no loop de monitoramento: {e}')
                time.sleep(5)
                
    except Exception as e:
        print(f'[BACEN][ERRO] Falha no monitoramento completo: {e}')

def _processar_evento_kaizen(driver, evento):
    """Processa eventos do menu Kaizen"""
    try:
        if evento == 'nova_minuta_bloqueio':
            from .minutas import kaizen_nova_minuta
            kaizen_nova_minuta(driver, endereco=False)
            
        elif evento == 'nova_minuta_endereco':
            from .minutas import kaizen_nova_minuta
            kaizen_nova_minuta(driver, endereco=True)
            
        elif evento == 'preencher_campos':
            from .preenchimento import kaizen_preencher_campos
            # Você precisaria ter acesso aos dados do processo aqui
            # kaizen_preencher_campos(driver, processo_dados_extraidos, config, invertido=False)
            print('[BACEN] Preenchimento de campos solicitado')
            
        elif evento == 'preencher_invertido':
            from .preenchimento import kaizen_preencher_campos
            # kaizen_preencher_campos(driver, processo_dados_extraidos, config, invertido=True)
            print('[BACEN] Preenchimento invertido solicitado')
            
        elif evento == 'consultar_teimosinha':
            from .minutas import kaizen_consultar_teimosinha
            linhas = kaizen_consultar_teimosinha(driver)
            if linhas:
                from .bloqueios import processar_bloqueios
                # processar_bloqueios(driver, config, linhas)
                print('[BACEN] Consulta teimosinha concluída')
                
        elif evento == 'consultar_minuta':
            from .minutas import kaizen_consultar_minuta
            kaizen_consultar_minuta(driver)
            
        else:
            print(f'[BACEN][AVISO] Evento não reconhecido: {evento}')
            
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao processar evento Kaizen: {e}')

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
                        'nav',  // Navegação
                        '[class*="toolbar"]',  // Elementos da toolbar
                        'sisbajud-header',  // Header específico do SISBAJUD
                        'mat-sidenav'  // Menu lateral
                    ];
                    
                    for (let seletor of indicadores) {
                        if (document.querySelector(seletor)) {
                            return true;
                        }
                    }
                    return false;
                """)
                
                if elementos_pos_login:
                    print('[BACEN] ✅ Login manual detectado com sucesso!')
                    print(f'[BACEN] URL pós-login: {current_url}')
                    login_detectado = True
                    
                    # Aguardar estabilização
                    time.sleep(2)
                    
                    # Salvar cookies após login bem-sucedido
                    from .cookies import salvar_cookies_sisbajud
                    salvar_cookies_sisbajud(driver)
                    
                    # Injetar automações
                    from .kaizen_interface import injetar_menu_kaizen_sisbajud
                    injetar_menu_kaizen_sisbajud(driver)
                    
                    return True
            
            tentativas += 1
            time.sleep(1)
            
        except Exception as e:
            print(f'[BACEN][ERRO] Erro durante detecção de login: {e}')
            tentativas += 1
            time.sleep(1)
    
    if not login_detectado:
        print('[BACEN] ❌ Timeout aguardando login manual (5 minutos)')
        return False
    
    return login_detectado

def tentar_login_automatico_ahk():
    """
    Tenta executar login automático usando AutoHotkey
    """
    try:
        print('[BACEN] Tentando login automático via AutoHotkey...')
        
        # Obter caminho do AutoHotkey
        ahk_path = obter_caminho_autohotkey()
        if not ahk_path:
            print('[BACEN][ERRO] AutoHotkey não encontrado')
            return False
        
        # Caminho do script de login
        script_path = os.path.join(os.path.dirname(__file__), '..', 'loginsisb.ahk')
        
        if not os.path.exists(script_path):
            print(f'[BACEN][ERRO] Script AHK não encontrado: {script_path}')
            return False
        
        # Executar script
        result = subprocess.run([ahk_path, script_path], 
                              capture_output=True, 
                              text=True, 
                              timeout=30)
        
        if result.returncode == 0:
            print('[BACEN] ✅ Script AutoHotkey executado com sucesso')
            return True
        else:
            print(f'[BACEN][ERRO] Falha na execução do script AHK: {result.stderr}')
            return False
            
    except subprocess.TimeoutExpired:
        print('[BACEN][ERRO] Timeout executando script AutoHotkey')
        return False
    except Exception as e:
        print(f'[BACEN][ERRO] Erro executando AutoHotkey: {e}')
        return False

def obter_caminho_autohotkey():
    """
    Obtém o caminho do executável AutoHotkey
    """
    try:
        # Locais comuns do AutoHotkey
        caminhos_possiveis = [
            r'C:\Program Files\AutoHotkey\AutoHotkey.exe',
            r'C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe',
            r'C:\AutoHotkey\AutoHotkey.exe',
            r'AutoHotkey.exe'  # Se estiver no PATH
        ]
        
        for caminho in caminhos_possiveis:
            if os.path.exists(caminho):
                return caminho
        
        # Tentar encontrar via PATH
        result = subprocess.run(['where', 'AutoHotkey.exe'], 
                              capture_output=True, 
                              text=True, 
                              shell=True)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
        
        return None
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao obter caminho AutoHotkey: {e}')
        return None

def main_teste_sisbajud():
    """
    Função principal para teste do módulo SISBAJUD
    """
    print('[BACEN] === TESTE SISBAJUD ===')
    
    try:
        # Criar driver
        from .drivers import criar_driver_firefox_sisb
        driver = criar_driver_firefox_sisb()
        
        if not driver:
            print('[BACEN][ERRO] Falha ao criar driver SISBAJUD')
            return False
        
        # Aguardar login
        if aguardar_login_manual_sisbajud(driver):
            print('[BACEN] ✅ Teste concluído com sucesso!')
            return True
        else:
            print('[BACEN] ❌ Falha no teste')
            return False
            
    except Exception as e:
        print(f'[BACEN][ERRO] Erro no teste: {e}')
        return False
    finally:
        # Não fechar o driver para permitir uso contínuo
        pass
