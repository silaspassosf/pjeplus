# sisb_modulos/minutas.py
# Operações com minutas SISBAJUD

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def kaizen_nova_minuta(driver, processo_dados_extraidos=None, endereco=False):
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
                }
            """)
            time.sleep(1.5)
        
        # Verificar se chegamos na página de minuta
        current_url = driver.current_url
        print(f'[KAIZEN] URL após navegação: {current_url}')
        print('[KAIZEN] Passo 3: Procurando e clicando no botão Nova...')
        
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
            print('[BACEN][ERRO] Falha ao clicar no botão Nova')
            return
        
        print('[BACEN] ✅ Botão Nova clicado com sucesso!')
        
        # Passo 4: Se for minuta de endereço, selecionar "Requisição de informações"
        if endereco:
            print('[BACEN] Passo 4: Selecionando "Requisição de informações"...')
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
                print('[BACEN] ✅ "Requisição de informações" selecionada!')
            else:
                print('[BACEN][AVISO] "Requisição de informações" não encontrada, continuando...')
                
            time.sleep(0.8)
        
        # Aguardar a página carregar completamente
        print('[BACEN] Aguardando redirecionamento para página de cadastro...')
        
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
                print(f'[BACEN] ✅ Página de cadastro detectada! URL: {current_url}')
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
                print('[BACEN] ✅ Elementos de cadastro detectados na página!')
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
            });
        """)
        
        if elementos_encontrados:
            print('[KAIZEN] ✅ Elementos do formulário carregados!')
        else:
            print('[KAIZEN][AVISO] Elementos do formulário não detectados, tentando continuar...')
            
        time.sleep(1)
        
        print('[BACEN] ✅ Nova minuta criada com sucesso!')
        print('[BACEN] 💡 Para preencher os campos, clique em "Polo Ativo" ou "Polo Passivo" conforme necessário.')
        
    except Exception as e:
        print(f'[KAIZEN][ERRO] Falha ao criar nova minuta: {e}')

def kaizen_consultar_minuta(driver, processo_dados_extraidos=None):
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
    Consulta o sistema de teimosinha no SISBAJUD
    Função corrigida de JavaScript para Python
    """
    try:
        print('[KAIZEN] Iniciando consulta teimosinha...')
        
        try:
            # Tentar localizar o botão Consultar
            botoes = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'CONSULTAR', 'consultar'), 'consultar')]")
            botao_encontrado = False
            
            for botao in botoes:
                if not botao.is_enabled() or not botao.is_displayed():
                    continue
                    
                texto_botao = botao.text.lower()
                if 'consultar' in texto_botao:
                    botao.click()
                    print('[KAIZEN] Botão Consultar clicado!')
                    botao_encontrado = True
                    break
                    
            if not botao_encontrado:
                print('[KAIZEN][ERRO] Botão "Consultar" não encontrado ou não clicável')
                
            # Aguardar a tabela de resultados
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'table'))
                )
                
                # Aguardar mais um pouco para garantir que os dados foram carregados
                time.sleep(2)
                
                # Buscar linhas com padrão específico
                from .bloqueios import _buscar_linhas_jun_2025
                linhas_encontradas = _buscar_linhas_jun_2025(driver)
                
                return linhas_encontradas
                
            except Exception as e:
                print(f'[KAIZEN][ERRO] Falha ao aguardar tabela de resultados: {e}')
                return []
                
        except Exception as e:
            print(f'[KAIZEN][ERRO] Falha ao consultar teimosinha: {e}')
            return []

    except Exception as e:
        print(f'[KAIZEN][ERRO] Erro geral em teimosinha: {e}')
        import traceback
        traceback.print_exc()
        return []

def kaizen_consulta_rapida(driver):
    """Consulta rápida SISBAJUD/PJe"""
    print('[KAIZEN] Consulta rápida SISBAJUD/PJe')
    # Implementar aqui se desejar automação específica
    pass

def minuta_bloqueio(driver, sisbajud_driver_func):
    """Cria minuta de bloqueio"""
    try:
        sisbajud_driver = sisbajud_driver_func()
        if sisbajud_driver:
            from .kaizen_interface import injetar_menu_kaizen_sisbajud
            injetar_menu_kaizen_sisbajud(sisbajud_driver)
            print('[BACEN] Minuta de bloqueio: automação disponível na janela Firefox SISBAJUD.')
        else:
            print('[BACEN][ERRO] Falha ao criar driver SISBAJUD')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao criar minuta de bloqueio: {e}')

def minuta_endereco(driver, sisbajud_driver_func):
    """Cria minuta de endereço"""
    try:
        sisbajud_driver = sisbajud_driver_func()
        if sisbajud_driver:
            from .kaizen_interface import injetar_menu_kaizen_sisbajud
            injetar_menu_kaizen_sisbajud(sisbajud_driver)
            print('[BACEN] Minuta de endereço: automação disponível na janela Firefox SISBAJUD.')
        else:
            print('[BACEN][ERRO] Falha ao criar driver SISBAJUD')
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao criar minuta de endereço: {e}')
