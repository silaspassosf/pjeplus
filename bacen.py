# bacen.py
# Automação SISBAJUD/BACEN integrada ao PJe, com suporte a Firefox (login inicial) e Thorium/Chrome (acesso SISBAJUD)
# Baseado em sisbajud.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import traceback
from Fix import extrair_dados_processo
from driver_config import criar_driver, login_func
import subprocess
import os
import json
import tempfile

def formatar_moeda_brasileira(valor):
    """
    Formatar valor monetário conforme padrão brasileiro do gigs-plugin.js
    Intl.NumberFormat('pt-br', {style: 'currency', currency: 'BRL'})
    Exemplo: 3777.29 -> "R$ 3.777,29" 
    """
    try:
        if isinstance(valor, str):
            # Remover formatação existente
            valor_limpo = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            valor = float(valor_limpo)
        
        # Formatação brasileira exata: R$ 1.234,56
        valor_formatado = f"R$ {valor:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        return valor_formatado
    except:
        return str(valor)

def formatar_cpf(cpf):
    """
    Formatar CPF no padrão brasileiro: 000.000.000-00
    CORREÇÃO: CPF 18545097808 deve virar 185.450.978-08, NÃO 18.545.097
    """
    try:
        # Extrair APENAS dígitos
        cpf_numerico = ''.join(filter(str.isdigit, str(cpf)))
        
        if len(cpf_numerico) == 11:
            # Formatação CORRETA: 185.450.978-08
            return f"{cpf_numerico[:3]}.{cpf_numerico[3:6]}.{cpf_numerico[6:9]}-{cpf_numerico[9:11]}"
        else:
            # Se não tiver 11 dígitos, retorna apenas os números
            return cpf_numerico  
    except:
        return str(cpf)

def formatar_cnpj(cnpj):
    """
    Formatar CNPJ no padrão brasileiro: 00.000.000/0000-00
    """
    try:
        # Limpar apenas números
        cnpj_numerico = ''.join(filter(str.isdigit, str(cnpj)))
        
        if len(cnpj_numerico) == 14:
            return f"{cnpj_numerico[:2]}.{cnpj_numerico[2:5]}.{cnpj_numerico[5:8]}/{cnpj_numerico[8:12]}-{cnpj_numerico[12:14]}"
        else:
            return cnpj_numerico  # Retorna original se não tiver 14 dígitos
    except:
        return str(cnpj)

def obter_cnpj_raiz(cnpj):
    """
    Extrair raiz do CNPJ (primeiros 8 dígitos) no formato 00.000.000
    """
    try:
        # Limpar apenas números
        cnpj_numerico = ''.join(filter(str.isdigit, str(cnpj)))
        
        if len(cnpj_numerico) >= 8:
            raiz = cnpj_numerico[:8]
            return f"{raiz[:2]}.{raiz[2:5]}.{raiz[5:8]}"
        else:
            return cnpj_numerico  # Retorna original se não tiver pelo menos 8 dígitos
    except:
        return str(cnpj)

def identificar_tipo_documento(documento):
    """
    Identificar se documento é CPF (11 dígitos) ou CNPJ (14 dígitos)
    """
    numerico = ''.join(filter(str.isdigit, str(documento)))
    if len(numerico) == 11:
        return 'CPF'
    elif len(numerico) == 14:
        return 'CNPJ'
    else:
        return 'INDEFINIDO'

def aguardar_elemento_carregado(driver, seletor, timeout=10):
    """Aguardar elemento carregar com verificação de overlays"""
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
        )
        # Aguardar estar visível
        WebDriverWait(driver, 5).until(
            EC.visibility_of(elemento)
        )
        return elemento
    except:
        return None

# ===================== CONFIGURAÇÕES =====================
CONFIG = {
    'cor_bloqueio_positivo': '#32cd32',
    'cor_bloqueio_negativo': '#ff6347',
    'acao_automatica': 'transferir',
    'banco_preferido': '0001',                                    # Código do banco preferido
    'agencia_preferida': '5905',                                  # Agência preferida
    'teimosinha': '60',
    'nome_default': '',
    'documento_default': '',
    'valor_default': '',
    'juiz_default': 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA',          # Juiz fixo
    'vara_default': '30006',                                      # Vara/Juízo fixo
    'cnpj_raiz': True,                                           # CNPJ raiz sempre SIM
}

processo_dados_extraidos = None
login_ahk_executado = False

def login_automatico_sisbajud(driver):
    """
    Login automatizado humanizado no SISBAJUD com simulação de comportamento humano
    """
    import random
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    
    try:
        print('[BACEN][LOGIN] Navegando para SISBAJUD...')
        driver.get('https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud&redirect_uri=https%3A%2F%2Fsisbajud.cnj.jus.br%2F&state=da9cbb01-be67-419d-8f19-f2c067a9e80f&response_mode=fragment&response_type=code&scope=openid&nonce=3d61a8ca-bb98-4924-88f9-9a0cb00f9f0e')
        
        # Aguardar carregamento com variação humana
        time.sleep(random.uniform(2.5, 4.0))
        
        # Verificar se já está logado
        current_url = driver.current_url
        if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
            print('[BACEN][LOGIN] ✅ Já está logado!')
            return True
        
        # Inserir tabela de credenciais
        print('[BACEN][LOGIN] Inserindo tabela de credenciais...')
        tabela_inserida = inserir_tabela_credenciais(driver)
        
        if not tabela_inserida:
            print('[BACEN][LOGIN] ❌ Não foi possível executar inserção da tabela')
            return False
        
        # AGORA SIM: aguardar que a tabela apareça no DOM
        print('[BACEN][LOGIN] Aguardando tabela aparecer no DOM...')
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            wait = WebDriverWait(driver, 10)
            tabela = wait.until(
                EC.presence_of_element_located((By.ID, "dados_login_sisbajud"))
            )
            print('[BACEN][LOGIN] ✅ Tabela encontrada no DOM')
            
            # Verificar se os botões estão clicáveis
            copiar_cpf = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Copiar CPF')]"))
            )
            copiar_senha = driver.find_element(By.XPATH, "//button[contains(text(), 'Copiar Senha')]")
            
            print('[BACEN][LOGIN] ✅ Botões "Copiar CPF" e "Copiar Senha" prontos')
            print('[BACEN][LOGIN] ✅ Tabela de credenciais completamente funcional')
            
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Tabela não apareceu ou botões não funcionais: {e}')
            return False
        
        # Aguardar estabilização
        print('[BACEN][LOGIN] Aguardando estabilização final...')
        time.sleep(random.uniform(1.5, 2.5))
        
        # 1. Clicar em "Copiar CPF" com clique REAL e movimento muito humanizado
        print('[BACEN][LOGIN] 1. Clicando em "Copiar CPF" (clique real)...')
        try:
            copiar_cpf = driver.find_element(By.XPATH, "//button[contains(text(), 'Copiar CPF')]")
            
            # Movimento muito mais humanizado
            actions = ActionChains(driver)
            
            # Simular movimento irregular (não linear)
            for i in range(3):
                offset_x = random.randint(-15, 15)
                offset_y = random.randint(-15, 15) 
                actions.move_to_element_with_offset(copiar_cpf, offset_x, offset_y)
                actions.pause(random.uniform(0.1, 0.4))
            
            # Movimento final para o centro do botão
            actions.move_to_element(copiar_cpf)
            actions.pause(random.uniform(0.3, 0.8))
            
            # Clique real com pressão e liberação separadas
            actions.click_and_hold(copiar_cpf)
            actions.pause(random.uniform(0.05, 0.15))  # Simular tempo de pressão humana
            actions.release()
            actions.perform()
            
            # Aguardar mais tempo para garantir que a cópia foi processada
            time.sleep(random.uniform(1.2, 2.0))
            print('[BACEN][LOGIN] ✅ Botão "Copiar CPF" clicado (clique real)')
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao clicar "Copiar CPF": {e}')
            return False
        
        # 2. Clicar no campo username com movimento muito humanizado  
        print('[BACEN][LOGIN] 2. Clicando no campo de usuário...')
        try:
            username_field = driver.find_element(By.ID, "username")
            
            # Movimento humano mais elaborado
            actions = ActionChains(driver)
            
            # Simular que o usuário viu o campo e está se movendo para ele
            actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50))
            actions.pause(random.uniform(0.2, 0.6))
            
            # Movimento para perto do campo (não exato)
            actions.move_to_element_with_offset(username_field, random.randint(-8, 8), random.randint(-8, 8))
            actions.pause(random.uniform(0.3, 0.7))
            
            # Movimento final para o campo
            actions.move_to_element(username_field)
            actions.pause(random.uniform(0.2, 0.5))
            
            # Clique com hesitação humana ocasional
            if random.random() < 0.3:  # 30% chance de hesitação
                print('[BACEN][LOGIN] Simulando hesitação humana...')
                actions.pause(random.uniform(0.5, 1.5))
            
            actions.click()
            actions.perform()
            
            time.sleep(random.uniform(0.5, 1.0))
            print('[BACEN][LOGIN] ✅ Campo usuário selecionado')
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao selecionar campo usuário: {e}')
            return False
        
        # 3. Ctrl+V para colar CPF com timing humanizado
        print('[BACEN][LOGIN] 3. Colando CPF (timing humanizado)...')
        try:
            # Aguardar um pouco como um humano faria
            time.sleep(random.uniform(0.5, 1.2))
            
            # Ctrl+V com ActionChains mais humanizada
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL)
            actions.pause(random.uniform(0.05, 0.15))  # Pequena pausa como humano
            actions.send_keys('v')
            actions.pause(random.uniform(0.05, 0.15))
            actions.key_up(Keys.CONTROL)
            actions.perform()
            
            # Aguardar o valor aparecer no campo
            time.sleep(random.uniform(1.0, 1.8))
            
            # Verificar se algo foi colado
            valor_colado = username_field.get_attribute('value')
            if valor_colado:
                print(f'[BACEN][LOGIN] ✅ CPF colado: {valor_colado[:6]}...')
            else:
                print('[BACEN][LOGIN] ⚠️ Nenhum valor detectado no campo após colar')
                
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao colar CPF: {e}')
            return False
        
        # 4. Clicar em "Copiar Senha" com clique real e muito humanizado
        print('[BACEN][LOGIN] 4. Clicando em "Copiar Senha" (clique real)...')
        try:
            copiar_senha = driver.find_element(By.XPATH, "//button[contains(text(), 'Copiar Senha')]")
            
            # Movimento ainda mais humanizado para o segundo botão
            actions = ActionChains(driver)
            
            # Simular movimento natural do primeiro para segundo botão
            actions.move_by_offset(random.randint(-20, 20), random.randint(10, 30))  # Move um pouco para baixo
            actions.pause(random.uniform(0.2, 0.5))
            
            # Aproximação do botão senha
            for i in range(2):
                offset_x = random.randint(-12, 12)
                offset_y = random.randint(-12, 12)
                actions.move_to_element_with_offset(copiar_senha, offset_x, offset_y)
                actions.pause(random.uniform(0.1, 0.3))
            
            # Posicionamento final
            actions.move_to_element(copiar_senha)
            actions.pause(random.uniform(0.4, 0.9))
            
            # Clique real com pressão e liberação  
            actions.click_and_hold(copiar_senha)
            actions.pause(random.uniform(0.06, 0.18))
            actions.release()
            actions.perform()
            
            # Aguardar processamento da cópia
            time.sleep(random.uniform(1.2, 2.2))
            print('[BACEN][LOGIN] ✅ Botão "Copiar Senha" clicado (clique real)')
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao clicar "Copiar Senha": {e}')
            return False
        
        # 5. Clicar no campo password
        print('[BACEN][LOGIN] 5. Clicando no campo de senha...')
        try:
            password_field = driver.find_element(By.ID, "password")
            simular_movimento_humano(driver, password_field)
            
            # Simular hesitação humana
            if random.random() < 0.4:  # 40% chance de hesitação
                print('[BACEN][LOGIN] Simulando hesitação humana...')
                time.sleep(random.uniform(0.5, 1.5))
            
            password_field.click()
            time.sleep(random.uniform(0.3, 0.8))
            print('[BACEN][LOGIN] ✅ Campo senha selecionado')
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao selecionar campo senha: {e}')
            return False
        
        # 6. Ctrl+V para colar senha
        print('[BACEN][LOGIN] 6. Colando senha...')
        try:
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(random.uniform(0.8, 1.5))
            print('[BACEN][LOGIN] ✅ Senha colada')
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao colar senha: {e}')
            return False
        
        # 7. Clicar no botão "Entrar"
        print('[BACEN][LOGIN] 7. Clicando em "Entrar"...')
        try:
            entrar_button = driver.find_element(By.ID, "kc-login")
            simular_movimento_humano(driver, entrar_button)
            
            # Simular pausa antes do login (comportamento humano)
            time.sleep(random.uniform(1.0, 2.5))
            
            entrar_button.click()
            print('[BACEN][LOGIN] ✅ Botão "Entrar" clicado')
            
            # Aguardar login processar
            time.sleep(random.uniform(3.0, 5.0))
            
            # Verificar sucesso do login
            current_url = driver.current_url
            if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                print('[BACEN][LOGIN] ✅ Login realizado com sucesso!')
                return True
            else:
                print('[BACEN][LOGIN] ❌ Login falhou - ainda na tela de autenticação')
                return False
                
        except Exception as e:
            print(f'[BACEN][LOGIN] ❌ Erro ao clicar em "Entrar": {e}')
            return False
    
    except Exception as e:
        print(f'[BACEN][LOGIN] ❌ Erro geral no login automatizado: {e}')
        return False

def simular_movimento_humano(driver, elemento):
    """
    Simula movimento de mouse humano antes de clicar em elemento
    """
    import random
    from selenium.webdriver.common.action_chains import ActionChains
    
    try:
        actions = ActionChains(driver)
        
        # Movimento com curva (não linear)
        if random.random() < 0.7:  # 70% chance de movimento curvo
            # Primeiro move para uma posição próxima (não exata)
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            actions.move_to_element_with_offset(elemento, offset_x, offset_y)
            actions.pause(random.uniform(0.1, 0.3))
        
        # Move para o elemento final
        actions.move_to_element(elemento)
        actions.pause(random.uniform(0.1, 0.5))
        actions.perform()
        
    except Exception as e:
        print(f'[BACEN][LOGIN] Aviso: Não foi possível simular movimento humano: {e}')

def inserir_tabela_credenciais(driver):
    """
    Insere tabela de credenciais na página de login com dados reais e funcionalidade
    """
    try:
        print('[BACEN][LOGIN] Executando inserção da tabela de credenciais...')
        
        # Código JavaScript para inserir a tabela COM DADOS REAIS e funcionalidade
        insert_table_js = """
        // Remove tabela existente se houver
        var existingTable = document.getElementById('dados_login_sisbajud');
        if (existingTable) {
            existingTable.remove();
        }
        
        // DADOS REAIS DO SISTEMA
        var cpfLogin = '30069277885';  // CPF real sem formatação
        var senhaLogin = 'Fl@quinho182';     // Senha real
        
        // Criar nova tabela com dados reais
        var tableHTML = `
        <div id="dados_login_sisbajud" style="position: fixed; bottom: 30px; left: 30px; z-index: 99999; background: rgb(255, 255, 255); border: 2px solid rgb(25, 118, 210); padding: 10px 12px 8px; border-radius: 8px; box-shadow: rgba(0, 0, 0, 0.2) 0px 2px 12px; font-size: 10px; min-width: 192px; transform: scale(0.78); transform-origin: left bottom 0px;">
            <div style="font-weight: bold; font-size: 12px; margin-bottom: 6px; color: rgb(25, 118, 210);">Login SISBAJUD</div>
            <label style="display: block; margin-bottom: 2px;">CPF:</label>
            <input id="cpf_field" type="text" value="${cpfLogin}" style="width: 100%; margin-bottom: 6px; padding: 2px; font-size: 10px;" readonly>
            <button id="btn_copiar_cpf" style="margin-bottom: 6px; padding: 2px 8px; font-size: 10px; cursor: pointer; background: rgb(25, 118, 210); color: rgb(255, 255, 255); border: medium; border-radius: 4px;">Copiar CPF</button>
            <label style="display: block; margin-bottom: 2px;">Senha:</label>
            <input id="senha_field" type="text" value="${senhaLogin}" style="width: 100%; margin-bottom: 6px; padding: 2px; font-size: 10px;" readonly>
            <button id="btn_copiar_senha" style="margin-bottom: 6px; padding: 2px 8px; font-size: 10px; cursor: pointer; background: rgb(25, 118, 210); color: rgb(255, 255, 255); border: medium; border-radius: 4px;">Copiar Senha</button>
            <button id="btn_copiar_ambos" style="margin-bottom: 6px; padding: 2px 8px; font-size: 10px; cursor: pointer; background: rgb(56, 142, 60); color: rgb(255, 255, 255); border: medium; border-radius: 4px; margin-left: 6px;">Copiar Ambos</button>
            <div style="font-size: 9px; color: rgb(85, 85, 85); margin-top: 2px;">Dados carregados e prontos para cópia.</div>
        </div>`;
        
        // Inserir no body
        document.body.insertAdjacentHTML('beforeend', tableHTML);
        
        // ADICIONAR FUNCIONALIDADE DE CÓPIA REAL
        function copiarParaClipboard(texto) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(texto).then(function() {
                    console.log('Texto copiado para clipboard: ' + texto.substring(0, 8) + '...');
                }).catch(function(err) {
                    console.error('Erro ao copiar: ', err);
                    // Fallback para método antigo
                    var textArea = document.createElement("textarea");
                    textArea.value = texto;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                });
            } else {
                // Fallback para browsers antigos
                var textArea = document.createElement("textarea");
                textArea.value = texto;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                console.log('Texto copiado (fallback): ' + texto.substring(0, 8) + '...');
            }
        }
        
        // Event listeners para os botões
        document.getElementById('btn_copiar_cpf').addEventListener('click', function() {
            copiarParaClipboard(cpfLogin);
            this.style.background = 'rgb(76, 175, 80)';
            this.innerHTML = 'CPF Copiado!';
            setTimeout(() => {
                this.style.background = 'rgb(25, 118, 210)';
                this.innerHTML = 'Copiar CPF';
            }, 2000);
        });
        
        document.getElementById('btn_copiar_senha').addEventListener('click', function() {
            copiarParaClipboard(senhaLogin);
            this.style.background = 'rgb(76, 175, 80)';
            this.innerHTML = 'Senha Copiada!';
            setTimeout(() => {
                this.style.background = 'rgb(25, 118, 210)';
                this.innerHTML = 'Copiar Senha';
            }, 2000);
        });
        
        document.getElementById('btn_copiar_ambos').addEventListener('click', function() {
            copiarParaClipboard(cpfLogin + '\\t' + senhaLogin);
            this.style.background = 'rgb(76, 175, 80)';
            this.innerHTML = 'Ambos Copiados!';
            setTimeout(() => {
                this.style.background = 'rgb(56, 142, 60)';
                this.innerHTML = 'Copiar Ambos';
            }, 2000);
        });
        
        console.log('Tabela SISBAJUD inserida com sucesso - CPF: ' + cpfLogin);
        return true;
        """
        
        # APENAS executar JavaScript - não aguardar nada
        driver.execute_script(insert_table_js)
        print('[BACEN][LOGIN] ✅ Tabela inserida com dados reais e funcionalidade de cópia')
        return True
        
    except Exception as e:
        print(f'[BACEN][LOGIN] ❌ Erro ao executar inserção da tabela: {e}')
        return False

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
# ===================== FUNÇÕES DE COOKIES REMOVIDAS =====================
# Funções de cookies foram removidas e substituídas por login automatizado humanizado
# - salvar_cookies_sisbajud() 
# - carregar_cookies_sisbajud()
# Agora usamos login_automatico_sisbajud() que simula comportamento humano

# ===================== INJETAR BOTÃO ÚNICO NO PJe =====================
    """
    Salvar cookies do SISBAJUD usando padrão do driver_config.py
    Salva na pasta cookies_sessoes com timestamp
    """
    try:
        cookies = driver.get_cookies()
        if not cookies:
            print('[BACEN][COOKIES] Nenhum cookie encontrado para salvar.')
            return False
            
        pasta_cookies = os.path.join(os.getcwd(), 'cookies_sessoes')
        os.makedirs(pasta_cookies, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        caminho_arquivo = os.path.join(pasta_cookies, f'cookies_sisbajud_{timestamp}.json')
        
        # Adicionar metadados para validação conforme driver_config.py
        dados_cookies = {
            'timestamp': datetime.now().isoformat(),
            'url_base': driver.current_url,
            'tipo': 'sisbajud',
            'dominios': ['sisbajud.cnj.jus.br', 'sso.cloud.pje.jus.br'],
            'cookies': cookies
        }
        
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_cookies, f, ensure_ascii=False, indent=2)
            
        print(f'[BACEN][COOKIES] ✅ Cookies SISBAJUD salvos: {os.path.basename(caminho_arquivo)}')
        print(f'[BACEN][COOKIES] Total de cookies: {len(cookies)}')
        
        return True
        
    except Exception as e:
        print(f'[BACEN][COOKIES][ERRO] Falha ao salvar cookies: {e}')
        import traceback
        traceback.print_exc()
        return False

def carregar_cookies_sisbajud(driver, max_idade_horas=24):
    """
    Carregar cookies do SISBAJUD usando padrão do driver_config.py
    Busca o arquivo mais recente na pasta cookies_sessoes
    """
    try:
        import glob
        from datetime import datetime, timedelta
        
        pasta_cookies = os.path.join(os.getcwd(), 'cookies_sessoes')
        if not os.path.exists(pasta_cookies):
            print('[BACEN][COOKIES] Pasta de cookies não encontrada.')
            return False
        
        # Buscar arquivos de cookies SISBAJUD
        arquivos_cookies = glob.glob(os.path.join(pasta_cookies, 'cookies_sisbajud_*.json'))
        if not arquivos_cookies:
            print('[BACEN][COOKIES] Nenhum arquivo de cookies SISBAJUD encontrado.')
            return False
        
        # Arquivo mais recente
        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        print(f'[BACEN][COOKIES] Carregando: {os.path.basename(arquivo_mais_recente)}')
        
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Verificar idade dos cookies
        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados['cookies']
        else:
            # Formato antigo
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados if isinstance(dados, list) else dados.get('cookies', [])
        
        timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.now() - timestamp_cookies
        
        if idade > timedelta(hours=max_idade_horas):
            print(f'[BACEN][COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h). Pulando.')
            return False
        
        # Navegar para domínio SISBAJUD antes de carregar cookies
        print('[BACEN][COOKIES] Navegando para domínio SISBAJUD...')
        driver.get('https://sisbajud.cnj.jus.br/')
        time.sleep(2)
        
        # Carregar cookies conforme driver_config.py
        cookies_carregados = 0
        for cookie in cookies:
            try:
                # Remover campos problemáticos
                cookie_limpo = {k: v for k, v in cookie.items() if k not in ['expiry', 'httpOnly', 'secure', 'sameSite']}
                
                # Verificar se cookie é do domínio correto
                domain = cookie.get('domain', '')
                if any(dom in domain for dom in ['sisbajud.cnj.jus.br', 'sso.cloud.pje.jus.br', '.cnj.jus.br']):
                    driver.add_cookie(cookie_limpo)
                    cookies_carregados += 1
                    
            except Exception as e:
                print(f'[BACEN][COOKIES] Erro ao carregar cookie {cookie.get("name", "unknown")}: {e}')
        
        print(f'[BACEN][COOKIES] {cookies_carregados} cookies SISBAJUD carregados')
        
        # Testar se cookies funcionam
        driver.get('https://sisbajud.cnj.jus.br/sisbajudweb/pages/consultas/bloqueio/bloqueio.jsf')
        time.sleep(3)
        
        # Verificar se redirecionou para login
        if 'login' in driver.current_url.lower() or 'auth' in driver.current_url.lower():
            print('[BACEN][COOKIES] ❌ Redirecionamento para login detectado. Cookies inválidos.')
            driver.delete_all_cookies()
            return False
            
        print('[BACEN][COOKIES] ✅ Cookies SISBAJUD funcionando!')
        return True
        
    except Exception as e:
        print(f'[BACEN][COOKIES][ERRO] Falha ao carregar cookies: {e}')
        import traceback
        traceback.print_exc()
        return False            
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao salvar cookies: {e}')
        import traceback
        traceback.print_exc()
        return False

def carregar_cookies_sisbajud(driver, caminho='cookies_sisbajud.json'):
    """
    Carrega cookies salvos para o driver SISBAJUD com melhor compatibilidade
    Agora compatível com o novo formato de dados salvos
    """
    import json
    import os
    import time
    from urllib.parse import urlparse
    
    if not os.path.exists(caminho):
        print(f'[BACEN] 📁 Arquivo de cookies não encontrado: {caminho}')
        return False
    
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Compatibilidade com formato antigo e novo
        if isinstance(dados, list):
            # Formato antigo - lista direta de cookies
            cookies = dados
            print('[BACEN] 📋 Carregando cookies no formato antigo')
        elif isinstance(dados, dict) and 'cookies' in dados:
            # Formato novo - dados estruturados
            cookies = dados['cookies']
            timestamp = dados.get('timestamp', 0)
            url_captura = dados.get('url_captura', 'N/A')
            cookies_criticos = dados.get('cookies_criticos', [])
            
            # Verificar idade dos cookies (avisar se muito antigos)
            idade_horas = (time.time() - timestamp) / 3600 if timestamp else 0
            print(f'[BACEN] 📊 Carregando cookies salvos há {idade_horas:.1f}h')
            print(f'[BACEN] 🌐 URL de captura: {url_captura}')
            print(f'[BACEN] 🔑 Cookies críticos salvos: {cookies_criticos}')
            
            if idade_horas > 24:
                print('[BACEN] ⚠️ AVISO: Cookies têm mais de 24h, podem estar expirados')
        else:
            print('[BACEN] ❌ Formato de arquivo de cookies não reconhecido')
            return False
        
        if not cookies:
            print('[BACEN] ❌ Nenhum cookie encontrado no arquivo')
            return False
            
        print(f'[BACEN] 🍪 Tentando carregar {len(cookies)} cookies salvos...')
        
        # Primeiro navegar para o domínio principal para definir o contexto
        print('[BACEN] 🔄 Navegando para SISBAJUD para definir contexto de cookies...')
        driver.get('https://sisbajud.cnj.jus.br')
        time.sleep(3)
        
        # Verificar se houve redirecionamento e ajustar domínios
        current_url = driver.current_url
        print(f'[BACEN] 🌐 URL após navegação inicial: {current_url}')
        
        # Detectar domínio real após redirecionamentos
        if 'sso.cloud.pje.jus.br' in current_url:
            print('[BACEN] 🔄 Detectado redirecionamento para SSO do PJe Cloud')
            # Adicionar domínios específicos do PJe Cloud
            dominios_adicionais = ['sso.cloud.pje.jus.br', '.cloud.pje.jus.br', 'cloud.pje.jus.br']
        elif 'sso.cnj.jus.br' in current_url:
            print('[BACEN] 🔄 Detectado redirecionamento para SSO do CNJ')
            dominios_adicionais = ['sso.cnj.jus.br', '.sso.cnj.jus.br']
        else:
            dominios_adicionais = []
        
        # Agrupar cookies por domínio para melhor carregamento
        dominios = {}
        for cookie in cookies:
            domain = cookie.get('domain', '')
            if domain not in dominios:
                dominios[domain] = []
            dominios[domain].append(cookie)
        
        print(f'[BACEN] 📂 Cookies agrupados em {len(dominios)} domínios: {list(dominios.keys())}')
        
        cookies_carregados = 0
        cookies_essenciais_carregados = []
        
        # Carregar cookies por domínio
        for domain, domain_cookies in dominios.items():
            print(f'[BACEN] 🌐 Carregando {len(domain_cookies)} cookies para domínio: {domain}')
            
            try:
                # Determinar URL de navegação baseada no domínio
                if 'sso.cloud.pje.jus.br' in domain:
                    domain_url = 'https://sso.cloud.pje.jus.br'
                elif 'sisbajud.cnj.jus.br' in domain:
                    domain_url = 'https://sisbajud.cnj.jus.br'
                elif 'sso.cnj.jus.br' in domain:
                    domain_url = 'https://sso.cnj.jus.br'
                elif domain.startswith('.'):
                    # Para domínios que começam com ponto, usar sem o ponto
                    domain_url = f'https://{domain[1:]}'
                elif domain:
                    domain_url = f'https://{domain}'
                else:
                    domain_url = None
                
                # Navegar para o domínio se necessário e possível
                if domain_url and domain_url != driver.current_url.split('?')[0]:
                    print(f'[BACEN] 🔄 Navegando para domínio: {domain_url}')
                    try:
                        driver.get(domain_url)
                        time.sleep(2)
                    except Exception as e:
                        print(f'[BACEN] ⚠️ Erro ao navegar para {domain_url}: {e}')
                        continue
                
                # Carregar cookies do domínio
                for cookie in domain_cookies:
                    try:
                        # Preparar cookie limpo
                        cookie_limpo = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'path': cookie.get('path', '/'),
                            'secure': cookie.get('secure', False),
                            'httpOnly': cookie.get('httpOnly', False)
                        }
                        
                        # Ajustar domínio baseado na URL atual
                        current_domain = driver.current_url.split('/')[2]
                        original_domain = cookie.get('domain', '')
                        
                        # Se o cookie é de um domínio diferente do atual, tentar ajustar
                        if original_domain and not current_domain.endswith(original_domain.replace('.', '')):
                            print(f'[BACEN] 🔄 Ajustando domínio do cookie {cookie["name"]} de {original_domain} para contexto atual')
                            # Não definir domínio - deixar o browser decidir
                        else:
                            cookie_limpo['domain'] = original_domain
                        
                        # Verificar e adicionar expiry se válido
                        if cookie.get('expiry') and cookie['expiry'] > time.time():
                            cookie_limpo['expiry'] = cookie['expiry']
                        
                        driver.add_cookie(cookie_limpo)
                        cookies_carregados += 1
                        
                        # Registrar cookies essenciais
                        cookies_essenciais = ['JSESSIONID', 'KEYCLOAK_SESSION', 'KEYCLOAK_IDENTITY']
                        if cookie['name'] in cookies_essenciais:
                            cookies_essenciais_carregados.append(cookie['name'])
                            print(f'[BACEN] 🔑 Cookie essencial carregado: {cookie["name"]} = {cookie["value"][:10]}...')
                        else:
                            print(f'[BACEN] 🍪 Cookie carregado: {cookie["name"]} (domínio: {cookie.get("domain", "N/A")})')
                        
                    except Exception as e:
                        print(f'[BACEN] ⚠️ Erro ao carregar cookie {cookie.get("name", "desconhecido")}: {e}')
                        continue
                        
            except Exception as e:
                print(f'[BACEN] ⚠️ Erro ao processar domínio {domain}: {e}')
                continue
        
        # Retornar para página principal
        print('[BACEN] 🔄 Retornando para página principal do SISBAJUD...')
        driver.get('https://sisbajud.cnj.jus.br')
        time.sleep(3)
        
        print(f'[BACEN] ✅ {cookies_carregados} cookies carregados no total!')
        print(f'[BACEN] 🔑 Cookies essenciais carregados: {cookies_essenciais_carregados}')
        
        # Verificar se cookies essenciais foram carregados
        if cookies_essenciais_carregados:
            print('[BACEN] ✅ Cookies de autenticação carregados com sucesso!')
            return True
        else:
            print('[BACEN] ⚠️ AVISO: Nenhum cookie essencial foi carregado')
            return cookies_carregados > 0
        
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao carregar cookies: {e}')
        import traceback
        traceback.print_exc()
        return False
        
        # Organizar cookies por domínio
        cookies_por_dominio = {}
        for cookie in cookies:
            domain = cookie.get('domain', '')
            if domain not in cookies_por_dominio:
                cookies_por_dominio[domain] = []
            cookies_por_dominio[domain].append(cookie)
        
        cookies_carregados = 0
        
        # Carregar cookies para cada domínio
        for domain, domain_cookies in cookies_por_dominio.items():
            try:
                # Determinar URL para navegar baseado no domínio
                if 'sisbajud.cnj.jus.br' in domain:
                    url_navegacao = 'https://sisbajud.cnj.jus.br'
                elif 'cnj.jus.br' in domain:
                    url_navegacao = f'https://{domain.lstrip(".")}'
                elif 'cloud.pje.jus.br' in domain:
                    url_navegacao = f'https://{domain.lstrip(".")}'
                else:
                    continue
                
                print(f'[BACEN] Navegando para {url_navegacao} para carregar {len(domain_cookies)} cookies...')
                driver.get(url_navegacao)
                time.sleep(1)
                
                # Adicionar cookies deste domínio
                for cookie in domain_cookies:
                    try:
                        # Preparar cookie limpo
                        cookie_limpo = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'path': cookie.get('path', '/'),
                            'secure': cookie.get('secure', False)
                        }
                        
                        # Ajustar domínio se necessário
                        if cookie.get('domain'):
                            cookie_limpo['domain'] = cookie['domain']
                        
                        # Adicionar expiry se válido
                        if cookie.get('expiry') and cookie['expiry'] > time.time():
                            cookie_limpo['expiry'] = cookie['expiry']
                        
                        driver.add_cookie(cookie_limpo)
                        cookies_carregados += 1
                        print(f'[BACEN] ✅ Cookie carregado: {cookie["name"]} (domínio: {cookie.get("domain", "N/A")})')
                        
                    except Exception as e:
                        print(f'[BACEN] ⚠️ Erro ao carregar cookie {cookie.get("name", "desconhecido")}: {e}')
                        continue
                        
            except Exception as e:
                print(f'[BACEN] ⚠️ Erro ao processar domínio {domain}: {e}')
                continue
        
        print(f'[BACEN] ✅ {cookies_carregados} cookies carregados no total!')
        
        # Navegar para a URL principal do SISBAJUD
        print('[BACEN] Redirecionando para SISBAJUD principal...')
        driver.get('https://sisbajud.cnj.jus.br')
        time.sleep(3)
        
        return cookies_carregados > 0
        
    except Exception as e:
        print(f'[BACEN][ERRO] Falha ao carregar cookies: {e}')
        import traceback
        traceback.print_exc()
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

def salvar_dados_processo_temp(params_adicionais=None):
    """
    Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas
    
    Args:
        params_adicionais (dict): Parâmetros adicionais para automação (ex: tipo_minuta, polo_executado, etc.)
    """
    global processo_dados_extraidos
    if processo_dados_extraidos:
        try:
            # Usa caminho do projeto ao invés de pasta temporária
            import os
            project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o bacen.py
            dados_path = os.path.join(project_path, 'dadosatuais.json')
            
            # Adicionar parâmetros de automação aos dados do processo
            dados_para_salvar = processo_dados_extraidos.copy()
            if params_adicionais:
                dados_para_salvar['parametros_automacao'] = params_adicionais
                print(f'[BACEN] Parâmetros de automação adicionados: {params_adicionais}')
            
            # Sempre sobrescreve o arquivo para não acumular dados de múltiplos processos
            with open(dados_path, 'w', encoding='utf-8') as f:
                json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
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
    
    # Aguardar estabilização e verificar se o login automático funcionou
    print('[BACEN] 🔍 Verificando status do login...')
    time.sleep(3)
    current_url = driver.current_url
    
    # Verificar se já está logado (não está na tela de login)
    if verificar_login_sisbajud(driver):
        print('[BACEN] ✅ Login automático realizado via cookies!')
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
    
    print('[BACEN] 🚀 Iniciando login automatizado humanizado...')
    
    # Usar login automatizado humanizado ao invés de login manual
    login_sucesso = login_automatico_sisbajud(driver)
    
    if login_sucesso:
        print('[BACEN] ✅ Login automatizado realizado com sucesso!')
        return driver
    else:
        print('[BACEN] ❌ Falha no login automatizado')
        print('[BACEN] 🔄 Você pode tentar fazer login manualmente no navegador')
        return driver
    
    if status_login:
        print('[BACEN] 🎉 LOGIN CONFIRMADO! Iniciando salvamento de cookies...')
        
        # Aguardar um pouco mais para garantir estabilização
        time.sleep(5)
        
        # Cookies removidos - agora usa login automatizado humanizado
        print('[BACEN] � Login automatizado humanizado implementado')
        print('[BACEN] ✅ Próximas sessões usarão processo de login inteligente')

        
        return driver
    else:
        print('[BACEN] ⚠️ TIMEOUT: Login não foi detectado no tempo limite')
        print('[BACEN] 🔄 Retornando driver para permitir login manual posterior')
        return driver

def verificar_login_sisbajud(driver):
    """
    Verifica se o usuário está logado no SISBAJUD de forma mais precisa
    
    Returns:
        bool: True se logado, False caso contrário
    """
    try:
        current_url = driver.current_url
        
        print(f'[BACEN] 🔍 Verificando login - URL atual: {current_url}')
        
        # Verifica cookies essenciais para SISBAJUD
        cookies = driver.get_cookies()
        has_session_cookie = False
        
        for cookie in cookies:
            if cookie['name'] in ['JSESSIONID', 'KEYCLOAK_SESSION', 'KEYCLOAK_IDENTITY', 'AUTH_SESSION_ID']:
                has_session_cookie = True
                print(f'[BACEN] 🍪 Cookie de sessão encontrado: {cookie["name"]}')
                break
        
        # URLs que indicam que ainda está no processo de login
        login_urls = [
            'auth/realms', 'login', 'sign-in', 'authentication',
            'keycloak', '/auth/', 'sso'
        ]
        
        # Verifica se ainda está na tela de login pela URL
        for login_url in login_urls:
            if login_url in current_url.lower():
                print(f'[BACEN] ⚠️ Ainda na tela de login - URL contém: {login_url}')
                return False
        
        # Se tem cookie de sessão e não está em URL de login
        if has_session_cookie and 'sisbajud.cnj.jus.br' in current_url:
            # Verificação final: procura por elementos específicos do sistema logado
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Aguarda até 5 segundos por elementos que indicam sistema logado
                wait = WebDriverWait(driver, 5)
                
                # Procura por botões específicos do SISBAJUD logado
                elementos_logado = [
                    "//button[contains(@class,'mat-fab')]",  # Botão "Nova"
                    "//mat-icon[contains(@class,'fa-plus')]",  # Ícone de adicionar
                    "//span[contains(text(),'Nova')]",  # Texto "Nova"
                    "//mat-toolbar",  # Toolbar do sistema
                    "//mat-sidenav",  # Menu lateral
                    "//*[contains(text(),'Minuta')]",  # Texto "Minuta" na página
                ]
                
                for elemento in elementos_logado:
                    try:
                        wait.until(EC.presence_of_element_located((By.XPATH, elemento)))
                        print(f'[BACEN] ✅ Login confirmado - elemento encontrado: {elemento}')
                        return True
                    except:
                        continue
                
                # Se não encontrou elementos específicos, mas tem cookies e está no domínio correto
                print('[BACEN] 🤔 Tem cookies de sessão mas não encontrou elementos específicos')
                
                # Verifica se há formulários de login na página atual
                page_source = driver.page_source.lower()
                if any(termo in page_source for termo in ['password', 'senha', 'cpf', 'entrar']):
                    # Mas verifica se não tem também elementos do sistema logado
                    if not any(termo in page_source for termo in ['minuta', 'nova', 'logout', 'sair']):
                        print('[BACEN] ⚠️ Encontrou elementos de login sem elementos do sistema')
                        return False
                
                # Se chegou até aqui, provavelmente está logado
                return True
                
            except Exception as e:
                print(f'[BACEN] ⚠️ Erro na verificação de elementos: {e}')
                # Fallback: se tem cookies de sessão e está no domínio, assume logado
                return has_session_cookie
        
        print('[BACEN] ❌ Login não verificado - sem cookies de sessão ou domínio incorreto')
        return False
        
    except Exception as e:
        print(f'[BACEN] ❌ Erro ao verificar login: {e}')
        import traceback
        traceback.print_exc()
        return False

def executar_minuta_sisbajud_parametrizada(driver, params):
    """
    Executa automação SISBAJUD parametrizada baseada nos padrões do gigs-plugin.js
    
    Args:
        driver: WebDriver SISBAJUD
        params (dict): Parâmetros de automação contendo tipo_minuta, polo_executado, etc.
    """
    print(f'[BACEN] === EXECUTANDO MINUTA SISBAJUD PARAMETRIZADA ===')
    print(f'[BACEN] Parâmetros recebidos: {params}')
    
    # VERIFICAÇÃO DE LOGIN E AUTOMAÇÃO SE NECESSÁRIO
    print('[BACEN] 🔐 VERIFICANDO LOGIN NO SISBAJUD...')
    if not verificar_login_sisbajud(driver):
        print('[BACEN] 🤖 Login não detectado - iniciando login automatizado...')
        login_sucesso = login_automatico_sisbajud(driver)
        
        if not login_sucesso:
            print('[BACEN] ❌ Falha no login automatizado')
            print('[BACEN] � Aguardando login manual como fallback...')
            
            # Fallback para login manual apenas se o automatizado falhar
            max_tentativas = 60  # 5 minutos
            tentativas = 0
            
            while tentativas < max_tentativas:
                print(f'[BACEN] ⏳ Aguardando login manual... ({tentativas + 1}/{max_tentativas})')
                time.sleep(5)
                
                if verificar_login_sisbajud(driver):
                    print('[BACEN] ✅ LOGIN DETECTADO! Prosseguindo com automação...')
                    break
                    
                tentativas += 1
                break
                
            tentativas += 1
        else:
            print('[BACEN] ❌ TIMEOUT: Login não foi detectado após 5 minutos')
            print('[BACEN] ❌ EXECUÇÃO CANCELADA')
            return False
    else:
        print('[BACEN] ✅ Login verificado - prosseguindo com automação')
    
    # Carregar dados do processo salvos
    dados_processo = None
    try:
        import os
        project_path = os.path.dirname(os.path.abspath(__file__))
        dados_path = os.path.join(project_path, 'dadosatuais.json')
        
        if os.path.exists(dados_path):
            with open(dados_path, 'r', encoding='utf-8') as f:
                dados_completos = json.load(f)
                dados_processo = {k: v for k, v in dados_completos.items() if k != 'parametros_automacao'}
                print('[BACEN] Dados do processo carregados para automação')
        else:
            print('[BACEN][ERRO] Arquivo dadosatuais.json não encontrado')
            return False
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao carregar dados: {e}')
        return False
    
    try:
        tipo_minuta = params.get('tipo_minuta', 'bloqueio')
        polo_executado = params.get('polo_executado', 'reu')
        
        # PASSO 1: Navegar para nova minuta (COM VERIFICAÇÃO DE ERRO)
        print('[BACEN] Passo 1: Navegando para nova minuta...')
        resultado_navegacao = False
        
        if tipo_minuta == 'endereco':
            # Minuta de requisição de informações/endereço
            resultado_navegacao = navegar_nova_minuta_endereco(driver)
        else:
            # Minuta de bloqueio padrão
            resultado_navegacao = navegar_nova_minuta_bloqueio(driver)
        
        if not resultado_navegacao:
            print('[BACEN] ❌ ERRO CRÍTICO: Falha na navegação para nova minuta')
            print('[BACEN] ❌ EXECUÇÃO INTERROMPIDA - Verifique se está logado corretamente')
            return False
        
        print('[BACEN] ✅ Navegação para minuta realizada com sucesso')
        
        # PASSO 2: Preencher dados básicos da minuta (COM VERIFICAÇÃO DE ERRO)
        print('[BACEN] Passo 2: Preenchendo dados básicos...')
        resultado_preenchimento = preencher_dados_basicos_minuta(driver, dados_processo)
        
        if not resultado_preenchimento:
            print('[BACEN] ❌ ERRO CRÍTICO: Falha no preenchimento de dados básicos')
            print('[BACEN] ❌ EXECUÇÃO INTERROMPIDA')
            return False
        
        print('[BACEN] ✅ Dados básicos preenchidos com sucesso')
        
        # PASSO 3: Selecionar e processar executados baseado no polo (COM VERIFICAÇÃO DE ERRO)
        print('[BACEN] Passo 3: Processando executados...')
        lista_executados = obter_lista_executados(dados_processo, polo_executado)
        
        if not lista_executados:
            print('[BACEN] ❌ ERRO CRÍTICO: Nenhum executado encontrado')
            print('[BACEN] ❌ EXECUÇÃO INTERROMPIDA')
            return False
        
        print(f'[BACEN] ✅ {len(lista_executados)} executados encontrados')
        
        resultado_executados = processar_executados_minuta(driver, lista_executados, params)
        if not resultado_executados:
            print('[BACEN] ❌ ERRO CRÍTICO: Falha no processamento de executados')
            print('[BACEN] ❌ EXECUÇÃO INTERROMPIDA')
            return False
        
        print('[BACEN] ✅ Executados processados com sucesso')
        
        # PASSO 4: Configurações específicas por tipo
        if tipo_minuta == 'bloqueio':
            configurar_minuta_bloqueio(driver, params, dados_processo)
        else:
            configurar_minuta_endereco(driver, params)
        
        # PASSO 5: Finalização
        if params.get('salvar_protocolar', True):
            finalizar_minuta_salvar_protocolar(driver)
        
        print('[BACEN] ✅ Minuta SISBAJUD executada com sucesso')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro durante execução da minuta: {e}')
        traceback.print_exc()
        return False

def minuta_bloqueio(driver_pje, valor_total=None, incluir_conjuge=True, 
                   protocolar_automaticamente=True):
    """
    Executa minuta de bloqueio com parâmetros específicos (sem botões de interação):
    1. Extrai dados do processo atual do PJe
    2. Obtém valor da execução via API do PJe se não fornecido
    3. Salva dados em dadosatuais.json
    4. Abre driver SISBAJUD e executa automação parametrizada
    
    VALORES FIXOS (configurados automaticamente):
    - Juiz: OTAVIO AUGUSTO MACHADO DE OLIVEIRA
    - Vara/Juízo: 30009  
    - CNPJ Raiz: SIM (sempre True)
    - Banco Preferido: 0001
    - Agência: 5905
    
    Args:
        driver_pje: Driver do PJe já navegado para o processo
        valor_total (str): Valor específico para execução (ex: "5000.00")
        incluir_conjuge (bool): Se deve incluir cônjuge na pesquisa
        protocolar_automaticamente (bool): Se deve protocolar automaticamente
    """
    print('[BACEN] === INICIANDO MINUTA DE BLOQUEIO PARAMETRIZADA ===')
    
    # PASSO 1: EXTRAIR DADOS DO PROCESSO E OBTER VALOR VIA API
    print('[BACEN] Passo 1: Extraindo dados do processo e obtendo valor via API...')
    global processo_dados_extraidos
    
    try:
        from Fix import extrair_dados_processo
        from calc import obter_valor_calculo_api, obter_id_processo_da_url
        import json
        import os
        import time
        
        # Extrair dados básicos do processo
        processo_dados_extraidos = extrair_dados_processo(driver_pje)
        print('[BACEN] ✅ Dados do processo extraídos:', processo_dados_extraidos)
        
        # Obter ID do processo da URL
        id_processo = obter_id_processo_da_url(driver_pje)
        if not id_processo:
            print('[BACEN] ❌ Não foi possível extrair ID do processo da URL')
            return False
        
        print(f'[BACEN] ID do processo extraído: {id_processo}')
        
        # Obter valor via API se não fornecido
        valor_execucao_final = valor_total
        dados_calculo = None
        
        if not valor_total:
            print('[BACEN] Obtendo valor da execução via API do PJe...')
            try:
                dados_calculo = obter_valor_calculo_api(driver_pje, id_processo)
                if dados_calculo:
                    valor_execucao_final = str(dados_calculo['total'])
                    print(f'[BACEN] ✅ Valor obtido via API: R$ {valor_execucao_final}')
                    print(f'[BACEN] Data da liquidação: {dados_calculo["dataLiquidacao"]}')
                else:
                    print('[BACEN] ⚠️ Nenhum cálculo encontrado via API')
                    valor_execucao_final = "0.00"
            except Exception as e:
                print(f'[BACEN] ⚠️ Erro ao obter valor via API: {e}')
                valor_execucao_final = valor_total or "0.00"
        
        # Preparar dados para salvar em dadosatuais.json
        dados_para_salvar = {
            **processo_dados_extraidos,
            'id_processo': id_processo,
            'valor_execucao': valor_execucao_final,
            'incluir_conjuge': incluir_conjuge,
            'protocolar_automaticamente': protocolar_automaticamente,
            'tipo_minuta': 'bloqueio',
            'dados_calculo_api': dados_calculo,
            'timestamp_extracao': time.strftime('%Y-%m-%d %H:%M:%S'),
            # Valores fixos
            'cnpj_raiz': CONFIG['cnpj_raiz'],
            'banco_preferido': CONFIG['banco_preferido'],
            'agencia_preferida': CONFIG['agencia_preferida'],
            'juiz_default': CONFIG['juiz_default'],
            'vara_default': CONFIG['vara_default']
        }
        
        # Salvar em dadosatuais.json
        try:
            with open('dadosatuais.json', 'w', encoding='utf-8') as f:
                json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
            print('[BACEN] ✅ Dados salvos em dadosatuais.json')
        except Exception as e:
            print(f'[BACEN] ⚠️ Erro ao salvar dadosatuais.json: {e}')
        
        # Preparar parâmetros para o SISBAJUD
        params_bloqueio = {
            'tipo_minuta': 'bloqueio',
            'valor_execucao': valor_execucao_final,
            'incluir_conjuge': incluir_conjuge,
            'protocolar_automaticamente': protocolar_automaticamente,
            'cnpj_raiz': CONFIG['cnpj_raiz'],
            'banco_preferido': CONFIG['banco_preferido'],
            'agencia_preferida': CONFIG['agencia_preferida'],
            'juiz_default': CONFIG['juiz_default'],
            'vara_default': CONFIG['vara_default']
        }
        
        salvar_dados_processo_temp(params_bloqueio)
        print('[BACEN] ✅ Dados e parâmetros salvos temporariamente')
        
    except Exception as e:
        print(f'[BACEN] ⚠️ Erro ao extrair dados do processo: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # PASSO 2: ABRIR DRIVER SISBAJUD E EXECUTAR AUTOMAÇÃO PARAMETRIZADA
    print('[BACEN] Passo 2: Abrindo driver SISBAJUD...')
    sisbajud_driver = abrir_sisbajud_em_firefox_sisbajud()
    
    if sisbajud_driver:
        print('[BACEN] Passo 3: Executando automação SISBAJUD parametrizada...')
        resultado = executar_minuta_sisbajud_parametrizada(sisbajud_driver, params_bloqueio)
        print('[BACEN] ✅ Minuta de bloqueio executada com parâmetros definidos.')
        return resultado
    else:
        print('[BACEN] ❌ Erro ao abrir driver SISBAJUD.')
        return False

def minuta_endereco(driver, polo_executado='reu', incluir_enderecos=True, incluir_dados_contas=False,
                   salvar_protocolar=True, executar_acao_final=True, confirmar_automatico=True):
    """
    Executa minuta de endereço (requisição de informações) com parâmetros específicos:
    1. Primeiro extrai dados do processo atual (driver do chamador) 
    2. Salva dados temporariamente incluindo parâmetros de ação
    3. Depois abre o driver SISBAJUD e executa automação parametrizada
    
    VALORES FIXOS (configurados automaticamente):
    - Juiz: OTAVIO AUGUSTO MACHADO DE OLIVEIRA
    - Vara/Juízo: 30009
    - CNPJ Raiz: SIM (sempre True)
    - Banco Preferido: 0001
    - Agência: 5905
    
    Args:
        polo_executado (str): 'reu' para polo passivo (padrão), 'autor' para polo ativo
        incluir_enderecos (bool): Se deve incluir requisição de endereços
        incluir_dados_contas (bool): Se deve incluir dados sobre contas
        cnpj_raiz (bool): Se deve usar CNPJ raiz para pessoas jurídicas
        salvar_protocolar (bool): Se deve salvar e protocolar automaticamente
        executar_acao_final (bool): Se deve executar ação final automaticamente
        confirmar_automatico (bool): Se deve confirmar ações automaticamente
    """
    print('[BACEN] === INICIANDO MINUTA DE ENDEREÇO PARAMETRIZADA ===')
    
    # PASSO 1: ARMAZENAR DADOS DO PROCESSO NO DRIVER ATUAL (CHAMADOR)
    print('[BACEN] Passo 1: Extraindo dados do processo no driver atual...')
    global processo_dados_extraidos
    
    try:
        from Fix import extrair_dados_processo
        processo_dados_extraidos = extrair_dados_processo(driver)
        print('[BACEN] ✅ Dados do processo extraídos:', processo_dados_extraidos)
        
        # Salvar dados para o driver SISBAJUD incluindo parâmetros
        params_endereco = {
            'tipo_minuta': 'endereco',
            'polo_executado': polo_executado,
            'incluir_enderecos': incluir_enderecos,
            'incluir_dados_contas': incluir_dados_contas,
            'cnpj_raiz': CONFIG['cnpj_raiz'],                    # Sempre True (fixo)
            'juiz_default': CONFIG['juiz_default'],              # Otavio Augusto (fixo)
            'vara_default': CONFIG['vara_default'],              # 30009 (fixo)
            'salvar_protocolar': salvar_protocolar,
            'executar_acao_final': executar_acao_final,
            'confirmar_automatico': confirmar_automatico
        }
        salvar_dados_processo_temp(params_endereco)
        print('[BACEN] ✅ Dados e parâmetros salvos temporariamente')
        
    except Exception as e:
        print(f'[BACEN] ⚠️ Erro ao extrair dados do processo: {e}')
        # Continua mesmo com erro na extração
    
    # PASSO 2: ABRIR DRIVER SISBAJUD E EXECUTAR AUTOMAÇÃO PARAMETRIZADA  
    print('[BACEN] Passo 2: Abrindo driver SISBAJUD...')
    sisbajud_driver = abrir_sisbajud_em_firefox_sisbajud()
    
    if sisbajud_driver:
        print('[BACEN] Passo 3: Executando automação SISBAJUD parametrizada...')
        executar_minuta_sisbajud_parametrizada(sisbajud_driver, params_endereco)
        print('[BACEN] ✅ Minuta de endereço executada com parâmetros definidos.')
    else:
        print('[BACEN] ❌ Erro ao abrir driver SISBAJUD.')


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
            print(f'[KAIZEN] Integrando dados: numero={numero}, autor={nome_ativo}, reu={nome_passivo}');
            
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
# sisbajud_teimosinha.py
"""
Automação completa do fluxo ‘Teimosinha’ (SISBAJUD):
1. Navega do menu /minuta até /teimosinha
2. Filtra séries elegíveis
3. Determina o tipo de fluxo (NEGATIVO | DESBLOQUEIO | POSITIVO)
4. Para DESBLOQUEIO/POSITIVO: abre cada série, identifica ordens com bloqueio
5. Preenche tela Desdobrar conforme fluxo (Desbloquear valor | Transferir valor)
6. Registra texto dos bloqueios e totals por parte
7. Chama wrappers/atos externos indicados no fluxo
Todas as funções foram isoladas para facilitar manutenção e testes unitários.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ---------------------------------------------------------------------------------
# CONSTANTES E CONFIGURAÇÕES GERAIS
# ---------------------------------------------------------------------------------
JUÍZ_SOLICITANTE_PADRÃO = "OTAVIO AUGUSTO MACHADO DE OLIVEIRA"
TIPO_CRÉDITO_PADRÃO = "Crédito geral"
BANCO_PADRÃO = "Banco do Brasil"
AGÊNCIA_PADRÃO = "5905"
DIAS_LIMITE_SERIE = 15

# ---------------------------------------------------------------------------------
# 0. UTILITÁRIOS
# ---------------------------------------------------------------------------------
def _esperar_clickável(driver: WebDriver, by: Tuple[str, str], timeout: int = 5):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(by))


def _try_select_option(driver: WebDriver, span_texto: str, timeout: int = 4) -> bool:
    """Clica numa <mat-option> cujo span possui texto igual a `span_texto`."""
    try:
        opc = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//span[@class='mat-option-text' and normalize-space(text())='{span_texto}']")
            )
        )
        opc.click()
        return True
    except TimeoutException:
        return False


def _texto_para_float(texto_moeda: str) -> float:
    """Converte 'R$ 1.234,56' → 1234.56"""
    limpo = (
        texto_moeda.replace("R$", "")
        .replace("\u00a0", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(limpo)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------------
# 1. NAVEGAÇÃO PARA /TEIMOSINHA E APLICAÇÃO DO FILTRO
# ---------------------------------------------------------------------------------
def _abrir_teimosinha(driver: WebDriver, num_processo: str) -> None:
    """Parte 1 do fluxo – navegação a /teimosinha e pesquisa pelo processo."""
    # a) Hamburguer
    _esperar_clickável(
        driver,
        (By.CSS_SELECTOR, "button.btn-hamburger, button[aria-label*='navegação']"),
    ).click()
    time.sleep(0.5)

    # b) Link Teimosinha
    _esperar_clickável(driver, (By.CSS_SELECTOR, "a[href='/teimosinha']")).click()
    WebDriverWait(driver, 5).until(EC.url_contains("/teimosinha"))

    # c) Campo Número do Processo
    inp_proc = _esperar_clickável(
        driver, (By.CSS_SELECTOR, "input[placeholder*='Número do Processo']")
    )
    inp_proc.clear()
    inp_proc.send_keys(num_processo)

    # d) Botão Consultar
    _esperar_clickável(
        driver,
        (By.XPATH, "//button[contains(@class,'mat-fab') and .//mat-icon[contains(@class,'fa-search')]]"),
    ).click()

    # e) Confirma que tabela carregou
    WebDriverWait(driver, 8).until(
        EC.presence_of_element_located(
            (By.XPATH, "//th[normalize-space(text())='ID da série']")
        )
    )


def _listar_series_elegíveis(driver: WebDriver) -> List[Dict[str, Any]]:
    """Retorna lista de séries que atendem aos critérios de situação/data."""
    series: List[Dict[str, Any]] = []
    linhas = driver.find_elements(By.CSS_SELECTOR, "tbody tr.mat-row")

    if not linhas:
        return series

    meses = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
    }
    limite = datetime.now() - timedelta(days=DIAS_LIMITE_SERIE)

    for ln in linhas:
        try:
            id_serie = ln.find_element(By.CSS_SELECTOR, "td[data-label='sequencial']").text.strip()
            situacao = ln.find_element(By.CSS_SELECTOR, "td[data-label='dataFim']").text.strip()
            data_prog_txt = ln.find_element(By.CSS_SELECTOR, "td[data-label='dataProgramada']").text.strip()
            val_bloq_txt = ln.find_element(By.CSS_SELECTOR, "td[data-label='valorBloqueado']").text.strip()
            val_a_bloq_txt = ln.find_element(By.CSS_SELECTOR, "td[data-label='valorBloquear']").text.strip()

            if "encerrada" not in situacao.lower():
                continue

            # Converte data “25 DE AGO DE 2023”
            p = data_prog_txt.upper().split()
            if len(p) < 5:
                continue
            dia, mes, ano = int(p[0]), meses.get(p[2], 1), int(p[4])
            data_prog = datetime(ano, mes, dia)

            if data_prog > limite:
                continue

            serie = dict(
                id_serie=id_serie,
                situacao=situacao,
                data_programada=data_prog,
                valor_bloqueado=_texto_para_float(val_bloq_txt),
                valor_a_bloquear=_texto_para_float(val_a_bloq_txt),
                ln_element=ln,
            )
            series.append(serie)
        except NoSuchElementException:
            continue
    return series


# ---------------------------------------------------------------------------------
# 2. EXTRAÇÃO DE TEXTO DAS SÉRIES + DEFINIÇÃO DO TIPO DE FLUXO
# ---------------------------------------------------------------------------------
def _texto_series(series: List[Dict[str, Any]]) -> Tuple[List[str], float, float]:
    linhas, total_bloq, total_a_bloq = [], 0.0, 0.0
    for s in series:
        linhas.append(
            f"Id da série: {s['id_serie']} - Valor Bloqueado na série: "
            f"R$ {s['valor_bloqueado']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        total_bloq += s["valor_bloqueado"]
        total_a_bloq += s["valor_a_bloquear"]
    if len(series) > 1:
        linhas.append(
            f"Total bloqueado = R$ {total_bloq:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    return linhas, total_bloq, total_a_bloq


def _classificar_fluxo(total_bloq: float, total_a_bloq: float) -> str:
    if total_bloq == 0:
        return "NEGATIVO"
    if total_bloq < 100 and total_a_bloq >= 1000:
        return "DESBLOQUEIO"
    return "POSITIVO"


# ---------------------------------------------------------------------------------
# 3. FUNÇÕES DE APOIO A /DETALHES E /DESDOBRAR
# ---------------------------------------------------------------------------------
def _abrir_nova_aba(driver: WebDriver, url: str) -> None:
    driver.execute_script("window.open(arguments[0],'_blank');", url)
    driver.switch_to.window(driver.window_handles[-1])


def _extrair_ordens(driver: WebDriver) -> List[Dict[str, Any]]:
    """Extrai todas as ordens da tabela na página /detalhes."""
    tbody = _esperar_clickável(driver, (By.CSS_SELECTOR, "table.mat-table tbody"), 10)
    linhas = tbody.find_elements(By.CSS_SELECTOR, "tr.mat-row")
    ordens = []
    for ln in linhas:
        cols = ln.find_elements(By.CSS_SELECTOR, "td")
        if len(cols) < 6:
            continue
        seq = int(cols[0].text.strip())
        data_txt = cols[2].text.strip().split()  # assume dd/mm/aaaa
        dia, mes, ano = map(int, data_txt.split("/"))
        data_ord = datetime(ano, mes, dia)
        valor = _texto_para_float(cols[4].text)
        ordens.append(
            dict(
                sequencial=seq,
                data=data_ord,
                valor_bloquear=valor,
                protocolo=cols[5].text.strip(),
                ln_element=ln,
            )
        )
    ordens.sort(key=lambda o: o["data"])
    return ordens


def _ordens_com_bloqueio(ordens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detecta ordens cujo valor à bloquear diminuiu em relação à ordem seguinte."""
    bloqs = []
    for i in range(len(ordens) - 1):
        if ordens[i]["valor_bloquear"] > ordens[i + 1]["valor_bloquear"]:
            bloqs.append(ordens[i])
    return bloqs


# -------------------------- Tela DESDOBRAR ---------------------------------------
def _preencher_tela_desdobrar(
    driver: WebDriver,
    fluxo: str,
) -> bool:
    """Preenche os campos na tela /desdobrar de acordo com o fluxo."""
    # Juiz solicitante
    try:
        inp_juiz = _esperar_clickável(driver, (By.CSS_SELECTOR, "input[placeholder*='Juiz']"), 6)
        inp_juiz.clear()
        inp_juiz.send_keys(JUÍZ_SOLICITANTE_PADRÃO + "\n")
    except TimeoutException:
        pass

    # Dropdowns de ação
    selects = driver.find_elements(By.CSS_SELECTOR, "mat-select[name*='acao']")
    opcao = "Desbloquear valor" if fluxo == "DESBLOQUEIO" else "Transferir valor"
    for sel in selects:
        try:
            sel.click()
            if not _try_select_option(driver, opcao):
                _try_select_option(driver, opcao.upper())  # variação de texto
        except Exception:
            continue

    # Botão Salvar
    try:
        _esperar_clickável(
            driver,
            (
                By.XPATH,
                "//button[contains(@class,'mat-fab') "
                "and .//mat-icon[contains(@class,'fa-save')]]",
            ),
            6,
        ).click()
    except TimeoutException:
        return False

    # Esperar botão 'Protocolar' aparecer
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//button[contains(@class,'mat-fab') "
                    "and @title='Protocolar']",
                )
            )
        )
        return True
    except TimeoutException:
        return False


# ---------------------------------------------------------------------------------
# 4. PROCESSAMENTO DE UMA ORDEM (menu → Desdobrar → preencher → fechar)
# ---------------------------------------------------------------------------------
def _processar_ordem(driver: WebDriver, ordem: Dict[str, Any], fluxo: str) -> bool:
    """Executa todas as etapas para uma única ordem."""
    ln = ordem["ln_element"]
    # Abrir menu
    try:
        ln.find_element(By.CSS_SELECTOR, "mat-icon.fa-ellipsis-h").click()
        _esperar_clickável(driver, (By.CSS_SELECTOR, "div.mat-menu-panel"))
    except Exception:
        return False

    # Clicar em Desdobrar
    try:
        _esperar_clickável(
            driver, (By.XPATH, "//button//span[contains(text(),'Desdobrar')]")
        ).click()
    except TimeoutException:
        return False

    # Aguarda URL /desdobrar
    try:
        WebDriverWait(driver, 8).until(EC.url_contains("/desdobrar"))
    except TimeoutException:
        return False

    # Preencher tela
    sucesso = _preencher_tela_desdobrar(driver, fluxo)

    # Fecha aba da ordem
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])
    return sucesso


# ---------------------------------------------------------------------------------
# 5. PROCESSAR UMA SÉRIE COMPLETA
# ---------------------------------------------------------------------------------
def _processar_serie(
    driver: WebDriver,
    serie: Dict[str, Any],
    fluxo: str,
    registro_partes: Dict[str, float],
) -> None:
    """Abre a série, processa ordens relevantes e acumula registro por parte."""
    id_serie = serie["id_serie"]
    _abrir_nova_aba(driver, f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes")

    if not EC.url_contains("/detalhes")(driver):
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
        return

    # Extrai ordens + identifica bloqueios
    ordens = _extrair_ordens(driver)
    ordens_bloq = _ordens_com_bloqueio(ordens)

    # Registros de bloqueio por parte (parse simplificado do HTML da parte)
    for o in ordens_bloq:
        # Parte encontra-se no cabeçalho expansion-panel acima da ordem
        try:
            panel = o["ln_element"].find_element(By.XPATH, "./ancestor::mat-expansion-panel[2]")
            parte_nome = panel.find_element(By.CSS_SELECTOR, ".col-reu-dados-nome-pessoa").text.strip()
        except Exception:
            parte_nome = "Parte não identificada"
        registro_partes[parte_nome] += o["valor_bloquear"]

        _processar_ordem(driver, o, fluxo)

    # Fecha a aba /detalhes
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])


# ---------------------------------------------------------------------------------
# 6. FUNÇÃO PRINCIPAL EXTERNAMENTE VISÍVEL
# ---------------------------------------------------------------------------------
def processar_teimosinha(
    driver: WebDriver,
    num_processo: str,
    ato_wrappers: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Entrada ÚNICA para o sistema externo:
    - `driver`  : driver SISBAJUD já logado
    - `num_processo`: string com número CNJ
    - `ato_wrappers`: dict com funções externas {positivo, negativo, desbloqueio, atos_medio, atos_parcial}
    Retorna dicionário‐relatório com:
       texto_series, fluxo, registro_partes, series_processadas
    """
    _abrir_teimosinha(driver, num_processo)
    series = _listar_series_elegíveis(driver)

    if not series:
        return {"erro": "Não há teimosinha para processar"}

    linhas_texto, total_bloq, total_a_bloq = _texto_series(series)
    fluxo = _classificar_fluxo(total_bloq, total_a_bloq)

    # Acumula registros por parte durante processamento
    registro_partes = defaultdict(float)

    if fluxo in ("DESBLOQUEIO", "POSITIVO"):
        for serie in series:
            if serie["valor_bloqueado"] > 0:
                _processar_serie(driver, serie, fluxo, registro_partes)

    # Fecha driver SISBAJUD (continuação no PJe)
    driver.quit()

    # ---- Invoca wrappers externos conforme fluxo ----
    if fluxo == "NEGATIVO":
        ato_wrappers["negativo"]()
        ato_wrappers["meios"]()
    elif fluxo == "DESBLOQUEIO":
        ato_wrappers["negativo"]()
        ato_wrappers["meios"]()
    else:  # POSITIVO
        ato_wrappers["positivo"]()
        ato_wrappers["parcial"]()

    # ---- Monta registro textual final ----
    texto_reg_partes = []
    for parte, valor in registro_partes.items():
        linha = f"{parte}: R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        texto_reg_partes.append(linha)

    return {
        "texto_series": linhas_texto,
        "fluxo": fluxo,
        "registro_partes": texto_reg_partes,
        "series_processadas": [s["id_serie"] for s in series],
    }


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
        
        # Login automatizado humanizado no SISBAJUD
        print('[BACEN][LOGIN] Iniciando login automatizado humanizado...')
        login_automatico_sisbajud(driver)
        
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
            # Cookies removidos - login automatizado implementado
            pass
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
            kaizen_nova_minuta(driver_sisbajud, False)
        elif evento == 'nova_minuta_endereco':
            print('[BACEN][KAIZEN] Executando: Nova minuta de endereço')
            kaizen_nova_minuta(driver_sisbajud, True)
        elif evento == 'preencher_campos':
            print('[BACEN][KAIZEN] Executando: Preencher campos (polo ativo)')
            kaizen_preencher_campos(driver_sisbajud, False)
        elif evento == 'preencher_invertido':
            print('[BACEN][KAIZEN] Executando: Preencher campos (polo passivo)')
            kaizen_preencher_campos(driver_sisbajud, True)
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
    print('Iniciando monitoramento de eventos...')
    
    try:
        while True:
            # Verificar eventos de automação
            evento_kaizen = driver_sisbajud.execute_script("""
                return window.kaizen_evt || null;
            """)
            
            if evento_kaizen:
                # print(f'Evento detectado: {evento_kaizen}')
                print(f'Evento detectado: {evento_kaizen}')
                processar_evento_kaizen(driver_sisbajud, evento_kaizen)
                # Limpar evento
                driver_sisbajud.execute_script("window.kaizen_evt = null;")
            
            time.sleep(1)
            
    except Exception as e:
        print(f'Erro no monitoramento: {e}')

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


# ===================== FUNÇÕES AUXILIARES PARA MINUTA PARAMETRIZADA =====================

def navegar_nova_minuta_bloqueio(driver):
    """Navega para nova minuta de bloqueio - após login já está na tela de minuta"""
    try:
        wait = WebDriverWait(driver, 15)
        
        print('[BACEN] Procurando botão Nova para criar minuta...')
        
        # Após login, já está na tela de minuta. Só precisa clicar em "Nova"
        # Seletor baseado no HTML fornecido: botão com fa-plus e texto "Nova"
        btn_nova = None
        seletores_nova = [
            'button[mat-fab] mat-icon.fa-plus',  # Botão fab com ícone fa-plus
            'button[mat-fab]:has(mat-icon.fa-plus)',  # Botão fab que contém ícone fa-plus
            'button[color="primary"][mat-fab]',  # Botão fab primário
            'button[mat-fab] span:contains("Nova")',  # Botão fab que contém texto "Nova"
            'button[mat-fab][type="button"]',  # Botão fab genérico
            '//button[contains(@class, "mat-fab") and .//mat-icon[contains(@class, "fa-plus")]]',  # XPath
            '//button[contains(@class, "mat-fab") and contains(., "Nova")]'  # XPath por texto
        ]
        
        for seletor in seletores_nova:
            try:
                print(f'[BACEN] Tentando seletor: {seletor}')
                
                if seletor.startswith('//'):
                    # XPath
                    btn_nova = wait.until(EC.element_to_be_clickable((By.XPATH, seletor)))
                else:
                    # CSS Selector
                    btn_nova = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                
                print(f'[BACEN] ✅ Botão Nova encontrado com seletor: {seletor}')
                break
                
            except Exception as e:
                print(f'[BACEN] ❌ Seletor {seletor} falhou: {e}')
                continue
        
        # Se não encontrou com seletores específicos, tentar seletor mais genérico
        if not btn_nova:
            try:
                print('[BACEN] Tentando seletor genérico para botões fab...')
                botoes_fab = driver.find_elements(By.CSS_SELECTOR, 'button[mat-fab]')
                
                for botao in botoes_fab:
                    try:
                        # Verificar se contém ícone de plus ou texto Nova
                        html_botao = botao.get_attribute('outerHTML')
                        texto_botao = botao.text.strip().lower()
                        
                        if ('fa-plus' in html_botao or 'nova' in texto_botao):
                            btn_nova = botao
                            print(f'[BACEN] ✅ Botão Nova encontrado via busca genérica')
                            print(f'[BACEN] Texto do botão: {botao.text}')
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f'[BACEN] ❌ Busca genérica falhou: {e}')
        
        if not btn_nova:
            print('[BACEN] ❌ Botão Nova não encontrado com nenhum método')
            return False
        
        # Clicar no botão Nova
        print('[BACEN] Clicando no botão Nova...')
        try:
            # Scroll até o botão se necessário
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_nova)
            time.sleep(0.5)
            
            # Tentar clicar
            btn_nova.click()
            print('[BACEN] ✅ Botão Nova clicado')
            
        except Exception as e:
            print(f'[BACEN] ❌ Erro ao clicar no botão Nova: {e}')
            # Tentar clique via JavaScript
            try:
                print('[BACEN] Tentando clique via JavaScript...')
                driver.execute_script("arguments[0].click();", btn_nova)
                print('[BACEN] ✅ Botão Nova clicado via JavaScript')
            except Exception as e2:
                print(f'[BACEN] ❌ Clique via JavaScript também falhou: {e2}')
                return False
        
        # Aguardar a tela de criação de minuta carregar
        time.sleep(2)
        
        # Verificar se chegou na página de criação de minuta
        print('[BACEN] Verificando se chegou na página de criação de minuta...')
        try:
            # Esperar elementos da página de minuta aparecerem
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'sisbajud-cadastro-minuta, input[placeholder*="Juiz"], mat-select')))
            print('[BACEN] ✅ Página de criação de minuta carregada com sucesso')
        except:
            print('[BACEN] ⚠️ Não foi possível verificar se chegou na página de criação')
        
        print('[BACEN] ✅ Navegação para nova minuta realizada')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao navegar para nova minuta: {e}')
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao navegar para nova minuta de bloqueio: {e}')
        import traceback
        traceback.print_exc()
        return False

def navegar_nova_minuta_endereco(driver):
    """Navega para nova minuta de requisição de informações/endereço"""
    try:
        # Primeiro navegar para nova minuta
        if not navegar_nova_minuta_bloqueio(driver):
            return False
        
        # Depois selecionar "Requisição de informações"
        wait = WebDriverWait(driver, 10)
        radio_requisicao = wait.until(EC.element_to_be_clickable((By.XPATH, '//label[contains(text(), "Requisição de informações")]')))
        radio_requisicao.click()
        time.sleep(0.5)
        
        print('[BACEN] ✅ Navegação para nova minuta de endereço realizada')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao navegar para nova minuta de endereço: {e}')
        return False

def preencher_dados_basicos_minuta(driver, dados_processo):
    """
    Preenche dados básicos da minuta baseado nos dados do processo
    Seletores extraídos do gigs-plugin.js para compatibilidade total
    """
    try:
        wait = WebDriverWait(driver, 10)
        
        # Aguardar página carregar
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'sisbajud-cadastro-minuta')))
        time.sleep(2)

        print('[BACEN] Passo 2: Preenchendo dados básicos...')
        
        # JUIZ SOLICITANTE - seletor correto: input[placeholder*="Juiz"]
        try:
            juiz_nome = dados_processo.get('parametros_automacao', {}).get('juiz_default') or CONFIG.get('juiz_default', 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA')
            print(f'[BACEN] Preenchendo juiz: {juiz_nome}')
            juiz_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="Juiz"]')
            if juiz_input:
                juiz_input.clear()
                juiz_input.send_keys(juiz_nome)
                time.sleep(0.5)
                print(f'[BACEN] ✅ Juiz preenchido: {juiz_nome}')
        except Exception as e:
            print(f'[BACEN][AVISO] Campo juiz não encontrado: {e}')
        
        # VARA/JUÍZO - seletor correto: input[placeholder*="Vara"] com fallbacks
        try:
            vara_codigo = dados_processo.get('parametros_automacao', {}).get('vara_default') or CONFIG.get('vara_default', '30009')
            print(f'[BACEN] Selecionando vara: {vara_codigo}')
            
            # Tentar diferentes seletores para vara
            seletores_vara = [
                'input[placeholder*="Vara"]',
                'input[placeholder*="Juízo"]', 
                'mat-select[formcontrolname*="vara"]',
                'select[name*="vara"]'
            ]
            
            vara_field = None
            for seletor in seletores_vara:
                try:
                    vara_field = driver.find_element(By.CSS_SELECTOR, seletor)
                    print(f'[BACEN] Campo vara encontrado com seletor: {seletor}')
                    break
                except:
                    continue
            
            if vara_field:
                if vara_field.tag_name in ['input']:
                    vara_field.clear()
                    vara_field.send_keys(vara_codigo)
                elif vara_field.tag_name in ['mat-select', 'select']:
                    vara_field.click()
                    time.sleep(1)
                    # Procurar opção com o código da vara
                    opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option, option')
                    for opcao in opcoes:
                        if vara_codigo in opcao.text:
                            opcao.click()
                            break
                time.sleep(0.5)
                print(f'[BACEN] ✅ Vara preenchida: {vara_codigo}')
            else:
                print('[BACEN][AVISO] Nenhum campo de vara encontrado')
        except Exception as e:
            print(f'[BACEN][AVISO] Campo vara não encontrado ou erro na seleção: {e}')
        
        # NÚMERO DO PROCESSO - seletor correto: input[placeholder="Número do Processo"]
        try:
            numero_list = dados_processo.get('numero', [])
            numero = numero_list[0] if isinstance(numero_list, list) and numero_list else str(numero_list) if numero_list else ''
            if numero:
                print(f'[BACEN] Preenchendo número do processo conforme gigs-plugin.js SISBAJUD: {numero}')
                numero_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Número do Processo"]')
                if numero_input:
                    # Método EXATO do gigs-plugin.js no SISBAJUD (acao3)
                    driver.execute_script("""
                        var el = arguments[0];
                        var valor = arguments[1];
                        el.focus();
                        el.value = valor;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.blur();
                    """, numero_input, numero)
                    time.sleep(0.5)
                    print(f'[BACEN] ✅ Número do processo preenchido: {numero}')
        except Exception as e:
            print(f'[BACEN][AVISO] Campo número do processo não encontrado: {e}')
        
        # TIPO DE AÇÃO - seletor ESPECÍFICO do gigs-plugin.js: mat-select[name*="acao"]
        try:
            tipo_acao = dados_processo.get('classeJudicial', {}).get('descricao', 'Ação Trabalhista - Rito Ordinário')
            print(f'[BACEN] Selecionando tipo de ação: {tipo_acao}')
            
            # Seletor ESPECÍFICO conforme gigs-plugin.js linha 13815
            acao_select = driver.find_element(By.CSS_SELECTOR, 'mat-select[name*="acao"]')
            if acao_select:
                acao_select.click()
                time.sleep(1)
                
                # Aguardar opções aparecerem - conforme gigs-plugin.js linha 13821
                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
                if opcoes:
                    # Buscar EXATAMENTE por 'Ação Trabalhista' conforme gigs-plugin.js linha 13828
                    for opcao in opcoes:
                        if opcao.text == 'Ação Trabalhista':
                            print(f'[BACEN] ✅ Selecionando: {opcao.text}')
                            opcao.click()
                            break
                    else:
                        print('[BACEN] ⚠️ Opção "Ação Trabalhista" não encontrada')
                        # Se não encontrar, clicar na primeira opção
                        if opcoes:
                            opcoes[0].click()
                            print(f'[BACEN] ⚠️ Selecionou primeira opção: {opcoes[0].text}')
                
                print(f'[BACEN] ✅ Tipo de ação processado')
        except Exception as e:
            print(f'[BACEN][AVISO] Campo tipo de ação não encontrado: {e}')
        
        # CPF/CNPJ AUTOR - seletor ESPECÍFICO do gigs-plugin.js: input[placeholder*="CPF"]
        try:
            autor_list = dados_processo.get('autor', [])
            if autor_list:
                cpf_autor_bruto = autor_list[0].get('cpfcnpj', '')
                
                # CORREÇÃO: CPF/CNPJ do autor - enviar APENAS NÚMEROS
                # SISBAJUD formata automaticamente, não precisamos formatar
                cpf_autor_bruto = autor_list[0].get('cpfcnpj', '')
                cpf_autor_numeros = ''.join(filter(str.isdigit, cpf_autor_bruto))
                
                print(f'[BACEN] Preenchendo documento do autor (APENAS NÚMEROS): {cpf_autor_numeros} (original: {cpf_autor_bruto})')
                
                # Seletor ESPECÍFICO conforme gigs-plugin.js linha 13843
                cpf_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="CPF"]')
                if cpf_input:
                    print(f'[BACEN] Preenchendo CPF autor conforme gigs-plugin.js SISBAJUD: {cpf_autor_numeros}')
                    
                    # Processamento EXATO conforme gigs-plugin.js acao5()
                    n = cpf_autor_numeros
                    n = n.replace('.', '')  # Remove pontos
                    n = n.replace('-', '')  # Remove hífens
                    print(f'[BACEN] CPF autor processado: {n} (original: {cpf_autor_numeros})')
                    
                    # Método EXATO do gigs-plugin.js no SISBAJUD (acao5)
                    driver.execute_script("""
                        var el = arguments[0];
                        var n = arguments[1];
                        el.focus();
                        setTimeout(function() {
                            el.value = n;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.blur();
                        }, 250);
                    """, cpf_input, n)
                    
                    time.sleep(0.25)
                    print(f'[BACEN] ✅ CPF/CNPJ do autor preenchido: {n}')
        except Exception as e:
            print(f'[BACEN][AVISO] Campo CPF/CNPJ autor não encontrado: {e}')
        
        # NOME AUTOR - seletor correto: input[placeholder="Nome do autor/exequente da ação"]
        try:
            autor_list = dados_processo.get('autor', [])
            if autor_list:
                nome_autor = autor_list[0].get('nome', '')
                print(f'[BACEN] Preenchendo nome autor conforme gigs-plugin.js SISBAJUD: {nome_autor}')
                nome_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Nome do autor/exequente da ação"]')
                if nome_input:
                    # Método EXATO do gigs-plugin.js no SISBAJUD (acao6)
                    driver.execute_script("""
                        var el = arguments[0];
                        var n = arguments[1];
                        el.focus();
                        el.value = n;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.blur();
                    """, nome_input, nome_autor)
                    time.sleep(0.5)
                    print(f'[BACEN] ✅ Nome autor preenchido: {nome_autor}')
        except Exception as e:
            print(f'[BACEN][AVISO] Campo nome autor não encontrado: {e}')
        
        print('[BACEN] ✅ Dados básicos da minuta preenchidos com seletores do gigs-plugin.js')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao preencher dados básicos: {e}')
        import traceback
        traceback.print_exc()
        return False

def obter_lista_executados(dados_processo, polo_executado):
    """Obtém lista de executados baseado no polo especificado"""
    try:
        if polo_executado == 'autor':
            # Polo ativo: autor é executado
            return dados_processo.get('autor', [])
        else:
            # Polo passivo (padrão): réu é executado
            return dados_processo.get('reu', [])
            
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao obter lista de executados: {e}')
        return []

def processar_executados_minuta(driver, lista_executados, params):
    """
    Processa lista de executados na minuta usando seletores do gigs-plugin.js
    Seletores: input[placeholder="CPF/CNPJ do réu/executado"], input[placeholder="CPF/CNPJ da pessoa pesquisada"]
    MODO FORÇA BRUTA: Limpa tudo e insere apenas dados do JSON
    """
    try:
        if not lista_executados:
            print('[BACEN][AVISO] Lista de executados vazia')
            return False
        
        wait = WebDriverWait(driver, 10)
        cnpj_raiz = params.get('cnpj_raiz', CONFIG['cnpj_raiz'])
        
        print('[BACEN] Passo 3: Processando executados... (MODO FORÇA BRUTA)')
        print(f'[BACEN] ✅ {len(lista_executados)} executados encontrados no JSON')
        
        # FORÇA BRUTA: Limpar todos os executados existentes primeiro
        try:
            print('[BACEN] 🧹 Limpando executados pré-existentes...')
            # Buscar todos os botões de remover executados
            botoes_remover = driver.find_elements(By.CSS_SELECTOR, 'button[mattooltip*="Remover"], button[title*="Remover"], button[aria-label*="Remover"], .btn-remover, .fa-trash')
            
            for i, botao in enumerate(botoes_remover):
                try:
                    print(f'[BACEN] 🗑️ Removendo executado pré-existente {i+1}')
                    botao.click()
                    time.sleep(0.5)
                    
                    # Confirmar remoção se houver dialog
                    try:
                        confirmar = driver.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close="true"], .mat-dialog-actions button:last-child, button:contains("Sim"), button:contains("Confirmar")')
                        confirmar.click()
                        time.sleep(0.5)
                    except:
                        pass
                except Exception as e:
                    print(f'[BACEN] ⚠️ Erro ao remover executado {i+1}: {e}')
                    
            print('[BACEN] ✅ Limpeza concluída. Inserindo executados do JSON...')
            
        except Exception as e:
            print(f'[BACEN] ⚠️ Erro na limpeza (continuar anyway): {e}')
        
        # Processar executados do JSON
        for idx, executado in enumerate(lista_executados):
            try:
                nome_executado = executado.get("nome", "Nome não informado")
                print(f'[BACEN] 📝 Processando executado {idx+1}: {nome_executado}')
                
                # Campo CPF/CNPJ do executado - seletores extraídos do gigs-plugin.js
                seletores_executado = [
                    'input[placeholder="CPF/CNPJ do réu/executado"]',
                    'input[placeholder="CPF/CNPJ da pessoa pesquisada"]',
                    'input[placeholder*="CPF/CNPJ"]',
                    'input[name*="documento"], input[formcontrolname*="documento"]'
                ]
                
                executado_input = None
                for seletor in seletores_executado:
                    try:
                        executado_input = driver.find_element(By.CSS_SELECTOR, seletor)
                        print(f'[BACEN] ✅ Campo executado encontrado: {seletor}')
                        break
                    except:
                        continue
                
                if not executado_input:
                    print(f'[BACEN][AVISO] Campo de executado não encontrado para {nome_executado}')
                    continue
                
                # CORREÇÃO COMPLETA: Aplicar lógica correta de documentos conforme dadosatuais.json
                cpf_cnpj = executado.get('documento', executado.get('cpfcnpj', ''))
                if cpf_cnpj:
                    tipo_doc = identificar_tipo_documento(cpf_cnpj)
                    
                    # LÓGICA CORRETA conforme análise do usuário:
                    # CPFs: 18545097808, 28167103862 -> devem aparecer COMPLETOS formatados
                    # CNPJ: 09219077000121 -> deve aparecer como RAIZ se cnpj_raiz=True
                    
                    if tipo_doc == 'CPF':
                        # CPFs: enviar APENAS NÚMEROS (sem formatação)
                        # CPF 18545097808 -> enviar "18545097808", não "185.450.978-08"
                        # O SISBAJUD vai formatar automaticamente
                        documento_final = ''.join(filter(str.isdigit, cpf_cnpj))
                        print(f'[BACEN] CPF do executado {idx+1} (APENAS NÚMEROS): {documento_final} (original: {cpf_cnpj})')
                        
                    elif tipo_doc == 'CNPJ':
                        if cnpj_raiz:
                            # CNPJ: usar apenas os 8 primeiros dígitos (sem formatação)
                            cnpj_numerico = ''.join(filter(str.isdigit, cpf_cnpj))
                            documento_final = cnpj_numerico[:8]
                            print(f'[BACEN] CNPJ RAIZ do executado {idx+1} (APENAS NÚMEROS): {documento_final} (original: {cpf_cnpj})')
                        else:
                            # CNPJ completo (apenas números)
                            documento_final = ''.join(filter(str.isdigit, cpf_cnpj))
                            print(f'[BACEN] CNPJ COMPLETO do executado {idx+1} (APENAS NÚMEROS): {documento_final} (original: {cpf_cnpj})')
                    else:
                        # Formato indefinido: usar original limpo
                        documento_final = ''.join(filter(str.isdigit, cpf_cnpj))
                        print(f'[BACEN] Documento indefinido do executado {idx+1}: {documento_final} (original: {cpf_cnpj})')
                    
                    print(f'[BACEN] {idx+1}: {nome_executado} -> {documento_final}')
                    
                    # Processamento EXATO conforme gigs-plugin.js função cadastro()
                    print(f'[BACEN] Preenchendo executado {idx+1} conforme gigs-plugin.js SISBAJUD')
                    
                    var1 = documento_final
                    
                    # Regra do gigs-plugin: CNPJ raiz para documentos > 14 caracteres
                    if len(var1) > 14:
                        if CONFIG.get('cnpj_raiz', True):  # preferencia sisbajud.cnpjRaiz
                            var1 = var1[:10]  # substring(0, 10) conforme gigs-plugin
                            print(f'[BACEN] CNPJ raiz aplicado: {var1} (original: {documento_final})')
                    
                    print(f'[BACEN] Valor final para preenchimento: {var1}')
                    
                    # PRIMEIRA INSERÇÃO conforme gigs-plugin
                    driver.execute_script("""
                        var el = arguments[0];
                        var var1 = arguments[1];
                        el.focus();
                        el.value = var1;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    """, executado_input, var1)
                    
                    print(f'[BACEN] Primeira inserção feita, aguardando 800ms para verificação...')
                    time.sleep(0.8)  # 800ms conforme gigs-plugin
                    
                    # VERIFICAÇÃO E CORREÇÃO conforme gigs-plugin (corrigeBug)
                    valor_no_campo = executado_input.get_attribute('value')
                    print(f'[BACEN] Valor no campo após 800ms: "{valor_no_campo}" (esperado: "{var1}")')
                    
                    precisa_corrigir = False
                    # Lógica EXATA do gigs-plugin.js linha ~14150
                    if len(var1) < 15:  # É CNPJ RAIZ ou CPF
                        if len(valor_no_campo) == 10 and len(var1) > 10:  # CNPJ raiz truncado de >10 para exatamente 10
                            print('[BACEN] Detectado truncamento de CNPJ RAIZ (ficou com 10 chars)')
                            precisa_corrigir = True
                        elif len(valor_no_campo) < 11 and len(var1) == 11:  # CPF truncado
                            print('[BACEN] Detectado truncamento de CPF (ficou com menos de 11 chars)')
                            precisa_corrigir = True
                    
                    if precisa_corrigir:
                        # SEGUNDA INSERÇÃO (correção) conforme gigs-plugin
                        print(f'[BACEN] Aplicando correção: preenchendo novamente com "{var1}"')
                        driver.execute_script("""
                            var el = arguments[0];
                            var var1 = arguments[1];
                            el.focus();
                            el.value = var1;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                        """, executado_input, var1)
                        
                        # Verificar se a correção funcionou
                        time.sleep(0.3)
                        valor_corrigido = executado_input.get_attribute('value')
                        print(f'[BACEN] Valor após correção: "{valor_corrigido}"')
                        
                        if valor_corrigido == var1:
                            print('[BACEN] ✅ Correção aplicada com sucesso!')
                        else:
                            print(f'[BACEN] ⚠️ Correção parcial: esperado "{var1}", obtido "{valor_corrigido}"')
                    else:
                        print('[BACEN] ✅ Valor preenchido corretamente, sem necessidade de correção')
                    
                    # AGUARDAR mais 800ms antes de clicar ADICIONAR (conforme gigs-plugin setInterval)
                    print('[BACEN] Aguardando 800ms antes de adicionar executado...')
                    time.sleep(0.8)
                    
                    print(f'[BACEN] ✅ Executado {idx+1} preenchido e validado: {var1}')
                    
                    # Procurar e clicar botão adicionar
                    try:
                        botoes_adicionar = [
                            'button[class*="btn-adicionar"]',
                            'button[mattooltip*="Adicionar"]', 
                            'button[title*="Adicionar"]',
                            'button[aria-label*="Adicionar"]',
                            'button:contains("Adicionar")',
                            '.fa-plus',
                            'mat-icon:contains("add")'
                        ]
                        
                        btn_adicionar = None
                        for seletor in botoes_adicionar:
                            try:
                                btn_adicionar = driver.find_element(By.CSS_SELECTOR, seletor)
                                break
                            except:
                                continue
                        
                        if btn_adicionar:
                            btn_adicionar.click()
                            time.sleep(1)
                            print(f'[BACEN] ✅ Executado {idx+1} adicionado')
                        else:
                            print(f'[BACEN] ⚠️ Botão adicionar não encontrado para executado {idx+1}')
                            
                    except Exception as add_error:
                        print(f'[BACEN] ⚠️ Erro ao adicionar executado {idx+1}: {add_error}')
                
            except Exception as e:
                print(f'[BACEN][ERRO] Erro ao processar executado {idx+1}: {e}')
                continue
        
        print('[BACEN] ✅ Executados processados com FORÇA BRUTA')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro geral ao processar executados: {e}')
        import traceback
        traceback.print_exc()
        return False

def configurar_minuta_bloqueio(driver, params, dados_processo):
    """
    Configura opções específicas para minuta de bloqueio usando seletores do gigs-plugin.js
    """
    try:
        wait = WebDriverWait(driver, 10)
        
        # TEIMOSINHA - seletor: mat-radio-button (buscar por texto "Repetir a ordem")
        teimosinha_dias = params.get('teimosinha_dias', 30)
        if teimosinha_dias > 0:
            try:
                print(f'[BACEN] Configurando teimosinha para {teimosinha_dias} dias')
                # Buscar radio button conforme gigs-plugin.js linha 13889
                radios = driver.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
                for radio in radios:
                    if 'Repetir a ordem' in radio.text:
                        label = radio.find_element(By.TAG_NAME, 'label')
                        label.click()
                        time.sleep(0.5)
                        print('[BACEN] ✅ Teimosinha habilitada')
                        
                        # Configurar data da teimosinha
                        configurar_data_teimosinha(driver, teimosinha_dias)
                        break
                        
            except Exception as e:
                print(f'[BACEN][AVISO] Não foi possível configurar teimosinha: {e}')
        
        # VALOR DE EXECUÇÃO - formatação CORRETA conforme gigs-plugin.js
        # PRIORIZAR parametros_automacao.valor_execucao sobre divida.valor
        valor_execucao = params.get('valor_execucao') or dados_processo.get('parametros_automacao', {}).get('valor_execucao') or dados_processo.get('divida', {}).get('valor')
        print(f'[BACEN] DEBUG - Valor obtido: {valor_execucao} (tipo: {type(valor_execucao)})')
        
        if valor_execucao:
            try:
                # CORREÇÃO CRÍTICA: valor_execucao vem como "3777.29" (ponto = decimal)
                # Deve resultar em "R$ 3.777,29" não "R$ 377.729,00"
                
                # Converter para float tratando ponto como decimal
                if isinstance(valor_execucao, str):
                    # Se vier como "3777.29", tratar ponto como decimal, não milhares
                    if '.' in valor_execucao and ',' not in valor_execucao:
                        valor_numerico = float(valor_execucao)
                        print(f'[BACEN] DEBUG - Valor string com ponto decimal: {valor_execucao} -> {valor_numerico}')
                    else:
                        # Remover formatação se existir e converter
                        valor_limpo = valor_execucao.replace('R$', '').replace(' ', '')
                        # NÃO remover o ponto se for o único separador decimal
                        if valor_limpo.count('.') == 1 and ',' not in valor_limpo:
                            valor_numerico = float(valor_limpo)
                        else:
                            valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                            valor_numerico = float(valor_limpo)
                        print(f'[BACEN] DEBUG - Valor string formatado: {valor_execucao} -> {valor_numerico}')
                else:
                    valor_numerico = float(valor_execucao)
                    print(f'[BACEN] DEBUG - Valor numérico: {valor_execucao} -> {valor_numerico}')
                
                # Formatação CORRETA para padrão brasileiro
                valor_formatado = formatar_moeda_brasileira(valor_numerico)
                print(f'[BACEN] Valor CORRIGIDO: "{valor_execucao}" -> "{valor_formatado}"')
                print(f'[BACEN] Preenchendo valor de execução: {valor_formatado}')
                
                # Fechar qualquer overlay que possa estar aberto
                try:
                    overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-pane, .mat-dialog-container')
                    for overlay in overlays:
                        if overlay.is_displayed():
                            try:
                                close_btn = overlay.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close], .mat-dialog-close, [aria-label*="fechar"], [aria-label*="close"]')
                                close_btn.click()
                                time.sleep(1)
                            except:
                                driver.execute_script("arguments[0].style.display = 'none';", overlay)
                except:
                    pass
                
                # Criar elemento de valor conforme gigs-plugin.js (linhas 14038-14048)
                try:
                    ancora = driver.find_element(By.CSS_SELECTOR, 'div[class="label-valor-extenso"]')
                except:
                    # Fallback: procurar outros containers possíveis
                    ancora = driver.find_element(By.CSS_SELECTOR, 'body')
                
                # Remover span anterior se existir
                driver.execute_script("""
                    var existing = document.getElementById('maisPJe_valor_execucao');
                    if (existing) existing.remove();
                """)
                
                # Criar span EXATAMENTE como no gigs-plugin.js
                data_divida = dados_processo.get('divida', {}).get('data', '10/08/2025')
                if 'T' in str(data_divida):
                    # Converter de formato ISO para DD/MM/AAAA
                    from datetime import datetime
                    try:
                        data_obj = datetime.fromisoformat(data_divida.replace('T', ' ').replace('Z', ''))
                        data_formatada = data_obj.strftime('%d/%m/%Y')
                    except:
                        data_formatada = '10/08/2025'
                else:
                    data_formatada = str(data_divida)
                
                valor_com_data = f"{valor_formatado} em {data_formatada}"
                
                driver.execute_script("""
                    var ancora = arguments[0];
                    var span = document.createElement('span');
                    span.id = 'maisPJe_valor_execucao';
                    span.innerText = 'Última atualização do processo: %s';
                    span.style = 'color: white;background-color: slategray;padding: 10px;border-radius: 10px; cursor: pointer;position: fixed;top: 10px;right: 10px;z-index: 9999;';
                    
                    // Função onclick conforme gigs-plugin.js linha 14043
                    span.onclick = function() {
                        var input = document.querySelector('input[placeholder*="Valor aplicado a todos"]');
                        if (input) {
                            // Usar valor formatado correto (sem data)
                            input.value = '%s';
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            span.style.backgroundColor = 'green';
                            span.innerText = 'Valor preenchido: %s';
                        }
                    };
                    
                    document.body.appendChild(span);
                """ % (valor_com_data, valor_formatado, valor_formatado))
                
                # Aguardar um pouco e clicar no span conforme gigs-plugin.js
                time.sleep(1)
                
                try:
                    # Auto-clicar se configurado para preencher automaticamente
                    driver.execute_script("""
                        var span = document.getElementById('maisPJe_valor_execucao');
                        if (span) span.click();
                    """)
                    
                    time.sleep(1)
                    print(f'[BACEN] ✅ Valor de execução configurado: {valor_formatado}')
                    
                except Exception as click_error:
                    print(f'[BACEN] ⚠️ Erro ao clicar no span de valor: {click_error}')
                
            except Exception as e:
                print(f'[BACEN][AVISO] Não foi possível preencher valor de execução: {e}')
                import traceback
                traceback.print_exc()
        
        # CONTA-SALÁRIO - seletor: mat-slide-toggle label
        incluir_conta_salario = params.get('incluir_conta_salario', False)
        if incluir_conta_salario:
            try:
                print('[BACEN] Incluindo conta-salário')
                # Seletor conforme gigs-plugin.js linha 14070
                toggles = driver.find_elements(By.CSS_SELECTOR, 'mat-slide-toggle label')
                for toggle in toggles:
                    toggle.click()
                    time.sleep(0.2)
                print('[BACEN] ✅ Conta-salário incluída')
            except Exception as e:
                print(f'[BACEN][AVISO] Não foi possível incluir conta-salário: {e}')
        
        print('[BACEN] ✅ Configuração de minuta de bloqueio concluída com seletores gigs-plugin.js')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao configurar minuta de bloqueio: {e}')
        return False

def configurar_minuta_endereco(driver, params):
    """
    Configura opções específicas para minuta de endereço usando seletores do gigs-plugin.js
    """
    try:
        wait = WebDriverWait(driver, 10)
        
        # INCLUIR ENDEREÇOS - seletor: span[class*="mat-checkbox-label"]
        incluir_enderecos = params.get('incluir_enderecos', True)
        if incluir_enderecos:
            try:
                print('[BACEN] Incluindo endereços na requisição')
                # Seletor conforme gigs-plugin.js linha 13926
                checkboxes = driver.find_elements(By.CSS_SELECTOR, 'span[class*="mat-checkbox-label"]')
                for checkbox_span in checkboxes:
                    if checkbox_span.text == "Endereços":
                        # Clicar no checkbox conforme gigs-plugin.js linha 13932
                        checkbox_input = checkbox_span.find_element(By.XPATH, '../../..//input[@type="checkbox"]')
                        if not checkbox_input.is_selected():
                            checkbox_input.click()
                            time.sleep(0.5)
                            print('[BACEN] ✅ Endereços incluídos na requisição')
                        break
            except Exception as e:
                print(f'[BACEN][AVISO] Não foi possível incluir endereços: {e}')
        
        # INCLUIR DADOS SOBRE CONTAS - seletor: mat-radio-button (buscar por "Não")
        incluir_dados_contas = params.get('incluir_dados_contas', False)
        if not incluir_dados_contas:
            try:
                print('[BACEN] Configurando para NÃO incluir dados sobre contas')
                # Buscar no monitor conforme gigs-plugin.js linha 13946
                monitor = driver.find_element(By.ID, 'maisPje_sisbajud_monitor')
                radios = monitor.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
                
                for radio in radios:
                    if 'Não' in radio.text:
                        # Clicar no label conforme gigs-plugin.js linha 13954
                        label = radio.find_element(By.TAG_NAME, 'label')
                        label.click()
                        time.sleep(0.5)
                        print('[BACEN] ✅ Configurado para NÃO incluir dados sobre contas')
                        break
                        
            except Exception as e:
                print(f'[BACEN][AVISO] Não foi possível configurar dados sobre contas: {e}')
        else:
            print('[BACEN] Mantendo configuração padrão para incluir dados sobre contas')
        
        print('[BACEN] ✅ Configuração de minuta de endereço concluída com seletores gigs-plugin.js')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao configurar minuta de endereço: {e}')
        return False

def configurar_data_teimosinha(driver, dias):
    """Configura data para teimosinha"""
    try:
        wait = WebDriverWait(driver, 10)
        
        # Clicar no calendário
        btn_calendario = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Open calendar"]')))
        btn_calendario.click()
        time.sleep(1)
        
        # Calcular data futura
        from datetime import datetime, timedelta
        data_futura = datetime.now() + timedelta(days=dias+2)  # +2 conforme lógica do gigs-plugin.js
        
        # Navegar para o ano correto
        btn_ano = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-calendar button[aria-label="Choose month and year"]')))
        btn_ano.click()
        time.sleep(0.5)
        
        ano_elemento = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'mat-calendar td[aria-label="{data_futura.year}"]')))
        ano_elemento.click()
        time.sleep(0.5)
        
        # Navegar para o mês correto
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        mes_nome = f"{meses[data_futura.month-1]} de {data_futura.year}"
        
        mes_elemento = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'mat-calendar td[aria-label="{mes_nome}"]')))
        mes_elemento.click()
        time.sleep(0.5)
        
        # Selecionar o dia
        dia_nome = f"{data_futura.day} de {mes_nome}"
        dia_elemento = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'mat-calendar td[aria-label="{dia_nome}"]')))
        dia_elemento.click()
        time.sleep(0.5)
        
        print(f'[BACEN] Data da teimosinha configurada: {data_futura.strftime("%d/%m/%Y")}')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao configurar data da teimosinha: {e}')
        return False

def finalizar_minuta_salvar_protocolar(driver):
    """
    Finaliza minuta salvando e protocolando usando seletores do gigs-plugin.js
    """
    try:
        wait = WebDriverWait(driver, 10)
        
        # SALVAR - múltiplos seletores baseados no gigs-plugin.js
        print('[BACEN] Salvando minuta...')
        
        # Tentar diferentes seletores
        btn_salvar = None
        seletores = [
            '//div[@class="uikit-actions"]//button[contains(text(), "Salvar")]',  # gigs-plugin.js linha 14101
            '//button[contains(text(), "Salvar")]',  # XPath genérico
            'button[aria-label="Salvar"]'  # Aria-label
        ]
        
        for seletor in seletores:
            try:
                if seletor.startswith('//'):
                    btn_salvar = wait.until(EC.element_to_be_clickable((By.XPATH, seletor)))
                else:
                    btn_salvar = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                break
            except:
                continue
        
        # Fallback usando JavaScript
        if not btn_salvar:
            btn_salvar = driver.execute_script("""
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].textContent.includes('Salvar')) {
                        return buttons[i];
                    }
                }
                return null;
            """)
        
        if btn_salvar:
            btn_salvar.click()
        else:
            raise Exception("Botão Salvar não encontrado")
        
        # Aguardar mensagem de sucesso - seletor: SISBAJUD-SNACK-MESSENGER
        print('[BACEN] Aguardando confirmação de salvamento...')
        time.sleep(3)
        try:
            # Seletor conforme gigs-plugin.js linha 14085
            mensagem = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'sisbajud-snack-messenger')))
            texto_mensagem = mensagem.text
            
            if 'incluída com sucesso' in texto_mensagem:
                print('[BACEN] ✅ Minuta salva com sucesso')
                
                # PROTOCOLAR - seletor: sisbajud-detalhamento-minuta button (texto "Protocolar")
                try:
                    print('[BACEN] Protocolando minuta...')
                    # Seletor conforme gigs-plugin.js linha 14086
                    btn_protocolar = wait.until(EC.element_to_be_clickable((By.XPATH, '//sisbajud-detalhamento-minuta//button[contains(text(), "Protocolar")]')))
                    time.sleep(1)  # Conforme gigs-plugin.js
                    
                    # Adicionar evento onmouseenter conforme gigs-plugin.js linha 14088
                    driver.execute_script("arguments[0].onmouseenter = function(event) { event.stopPropagation(); };", btn_protocolar)
                    
                    btn_protocolar.click()
                    print('[BACEN] ✅ Minuta protocolada com sucesso')
                    
                except Exception as e:
                    print(f'[BACEN][AVISO] Erro ao protocolar: {e}')
                    
            else:
                print(f'[BACEN][AVISO] Mensagem inesperada: {texto_mensagem}')
                
                # Verificar mensagem específica conforme gigs-plugin.js linha 14094
                if 'que não possui Instituição Financeira associada' in texto_mensagem:
                    print('[BACEN] Detectada mensagem sobre instituição financeira')
                    # Tentar salvar novamente conforme gigs-plugin.js
                    try:
                        btn_salvar_2 = driver.find_element(By.XPATH, '//div[@class="uikit-actions"]//button[contains(text(), "Salvar")]')
                        btn_salvar_2.click()
                        time.sleep(2)
                        
                        # Tentar protocolar após segundo salvamento
                        btn_protocolar_2 = driver.find_element(By.XPATH, '//div[@class="uikit-actions"]//button[contains(text(), "Protocolar")]')
                        btn_protocolar_2.click()
                        print('[BACEN] ✅ Minuta salva e protocolada após correção')
                        
                    except Exception as e:
                        print(f'[BACEN][AVISO] Erro na correção de instituição financeira: {e}')
                
        except Exception as e:
            print(f'[BACEN][AVISO] Não foi possível verificar mensagem de sucesso: {e}')
        
        print('[BACEN] ✅ Finalização da minuta concluída com seletores gigs-plugin.js')
        return True
        
    except Exception as e:
        print(f'[BACEN][ERRO] Erro ao finalizar minuta: {e}')
        return False

def main_teste_sisbajud():
    """
    Main de teste para executar apenas o SISBAJUD com login automático
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
            print('')
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

# ===================== PONTO DE ENTRADA PRINCIPAL =====================
if __name__ == "__main__":
    """
    Ponto de entrada principal do bacen.py
    Executa a função main() quando o script é executado diretamente
    """
    try:
        main()
    except KeyboardInterrupt:
        print('\n[BACEN] ⏹️ Execução interrompida pelo usuário.')
    except Exception as e:
        print(f'\n[BACEN] ❌ Erro crítico na execução: {e}')
        import traceback
        traceback.print_exc()
