# sisbajud.py
# Módulo integrado para automação SISBAJUD/BACEN
# Integra funcionalidades de bacen.py, sisb.py e gigs.py

# ===================== IMPORTAÇÕES =====================
import time
import json
import os
import re
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
import traceback
import random
import tempfile

# Importações de outros módulos
from Fix import extrair_dados_processo
from driver_config import criar_driver, login_func

# ===================== UTILITÁRIOS =====================

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

def extrair_documentos_reus(dados_processo):
    """
    Extrair documentos (CPF/CNPJ) de todos os réus do processo
    Retorna lista de documentos e string concatenada com quebras de linha
    """
    documentos = []
    if 'reu' in dados_processo and len(dados_processo['reu']) > 0:
        for reu in dados_processo['reu']:
            cpfcnpj = reu.get('cpfcnpj', '')
            if cpfcnpj:
                documentos.append(cpfcnpj)
                print(f'[SISBAJUD] Réu encontrado: {reu.get("nome", "N/A")} ({cpfcnpj})')
    
    if not documentos:
        return None, None
    
    # Concatenar todos os documentos com quebra de linha (como no gigs.py)
    documentos_concatenados = '\n'.join(documentos)
    print(f'[SISBAJUD] Documentos para processamento:\n{documentos_concatenados}')
    
    return documentos, documentos_concatenados

def aguardar_elemento_carregado(driver, seletor, timeout=10):
    """Aguardar elemento carregar com verificação de overlays"""
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

def clicar_elemento(driver, seletores, timeout=10):
    """
    Clica em um elemento usando múltiplos seletores com tentativas
    Baseado na abordagem de gigs.py
    """
    if not isinstance(seletores, list):
        seletores = [seletores]
    
    for tentativa in range(3):
        for seletor in seletores:
            try:
                if seletor.startswith('//'):
                    elemento = WebDriverWait(driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, seletor))
                    )
                else:
                    elemento = WebDriverWait(driver, timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                elemento.click()
                return True
            except Exception as e:
                continue
        time.sleep(1)
    
    return False

def preencher_campo(driver, seletores, valor, timeout=10, limpar=True):
    """
    Preenche um campo usando múltiplos seletores com tentativas
    Baseado na abordagem de gigs.py
    """
    if not isinstance(seletores, list):
        seletores = [seletores]
    
    for tentativa in range(3):
        for seletor in seletores:
            try:
                if seletor.startswith('//'):
                    elemento = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, seletor))
                    )
                else:
                    elemento = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                    )
                
                if limpar:
                    elemento.clear()
                elemento.send_keys(valor)
                return True
            except Exception as e:
                continue
        time.sleep(1)
    
    return False

# ===================== COOKIES (de sisb.py) =====================

def salvar_cookies_sisbajud(driver):
    """
    Salvar cookies do SISBAJUD usando padrão do driver_config.py
    Salva na pasta cookies_sessoes com timestamp
    """
    try:
        cookies = driver.get_cookies()
        if not cookies:
            print('[SISBAJUD][COOKIES] Nenhum cookie encontrado para salvar.')
            return False
            
        pasta_cookies = os.path.join(os.getcwd(), 'cookies_sessoes')
        os.makedirs(pasta_cookies, exist_ok=True)
        
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
            
        print(f'[SISBAJUD][COOKIES] ✅ Cookies SISBAJUD salvos: {os.path.basename(caminho_arquivo)}')
        print(f'[SISBAJUD][COOKIES] Total de cookies: {len(cookies)}')
        
        return True
        
    except Exception as e:
        print(f'[SISBAJUD][COOKIES][ERRO] Falha ao salvar cookies: {e}')
        traceback.print_exc()
        return False

def carregar_cookies_sisbajud(driver, max_idade_horas=24):
    """
    Carregar cookies do SISBAJUD usando padrão do driver_config.py
    Busca o arquivo mais recente na pasta cookies_sessoes
    """
    try:
        pasta_cookies = os.path.join(os.getcwd(), 'cookies_sessoes')
        if not os.path.exists(pasta_cookies):
            print('[SISBAJUD][COOKIES] Pasta de cookies não encontrada.')
            return False
        
        # Buscar arquivos de cookies SISBAJUD
        arquivos_cookies = glob.glob(os.path.join(pasta_cookies, 'cookies_sisbajud_*.json'))
        if not arquivos_cookies:
            print('[SISBAJUD][COOKIES] Nenhum arquivo de cookies SISBAJUD encontrado.')
            return False
        
        # Arquivo mais recente
        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        print(f'[SISBAJUD][COOKIES] Carregando: {os.path.basename(arquivo_mais_recente)}')
        
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
            print(f'[SISBAJUD][COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h). Pulando.')
            return False
        
        # Navegar para domínio SISBAJUD antes de carregar cookies
        print('[SISBAJUD][COOKIES] Navegando para domínio SISBAJUD...')
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
                print(f'[SISBAJUD][COOKIES] Erro ao carregar cookie {cookie.get("name", "unknown")}: {e}')
        
        print(f'[SISBAJUD][COOKIES] {cookies_carregados} cookies SISBAJUD carregados')
        
        # Testar se cookies funcionam
        driver.get('https://sisbajud.cnj.jus.br/sisbajudweb/pages/consultas/bloqueio/bloqueio.jsf')
        time.sleep(3)
        
        # Verificar se redirecionou para login
        if 'login' in driver.current_url.lower() or 'auth' in driver.current_url.lower():
            print('[SISBAJUD][COOKIES] ❌ Redirecionamento para login detectado. Cookies inválidos.')
            driver.delete_all_cookies()
            return False
            
        print('[SISBAJUD][COOKIES] ✅ Cookies SISBAJUD funcionando!')
        return True
        
    except Exception as e:
        print(f'[SISBAJUD][COOKIES][ERRO] Falha ao carregar cookies: {e}')
        traceback.print_exc()
        return False

# ===================== FUNÇÕES DE LOGIN (de bacen.py) =====================

def simular_movimento_humano(driver, elemento):
    """
    Simula movimento de mouse humano antes de clicar em elemento
    """
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
        print(f'[SISBAJUD][LOGIN] Aviso: Não foi possível simular movimento humano: {e}')

def inserir_tabela_credenciais(driver):
    """
    Insere tabela de credenciais na página de login com dados reais e funcionalidade
    """
    try:
        print('[SISBAJUD][LOGIN] Executando inserção da tabela de credenciais...')
        
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
            copiarParaClipboard(cpfLogin + '\\\\t' + senhaLogin);
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
        print('[SISBAJUD][LOGIN] ✅ Tabela inserida com dados reais e funcionalidade de cópia')
        return True
        
    except Exception as e:
        print(f'[SISBAJUD][LOGIN] ❌ Erro ao executar inserção da tabela: {e}')
        return False

def login_automatico_sisbajud(driver):
    """
    Login automatizado humanizado no SISBAJUD com simulação de comportamento humano
    """
    try:
        print('[SISBAJUD][LOGIN] Navegando para SISBAJUD...')
        driver.get('https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud&redirect_uri=https%3A%2F%2Fsisbajud.cnj.jus.br%2F&state=da9cbb01-be67-419d-8f19-f2c067a9e80f&response_mode=fragment&response_type=code&scope=openid&nonce=3d61a8ca-bb98-4924-88f9-9a0cb00f9f0e')
        
        # Aguardar carregamento com variação humana
        time.sleep(random.uniform(2.5, 4.0))
        
        # Verificar se já está logado
        current_url = driver.current_url
        if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
            print('[SISBAJUD][LOGIN] ✅ Já está logado!')
            return True
        
        # Inserir tabela de credenciais
        print('[SISBAJUD][LOGIN] Inserindo tabela de credenciais...')
        tabela_inserida = inserir_tabela_credenciais(driver)
        
        if not tabela_inserida:
            print('[SISBAJUD][LOGIN] ❌ Não foi possível executar inserção da tabela')
            return False
        
        # AGORA SIM: aguardar que a tabela apareça no DOM
        print('[SISBAJUD][LOGIN] Aguardando tabela aparecer no DOM...')
        
        try:
            wait = WebDriverWait(driver, 10)
            tabela = wait.until(
                EC.presence_of_element_located((By.ID, "dados_login_sisbajud"))
            )
            print('[SISBAJUD][LOGIN] ✅ Tabela encontrada no DOM')
            
            # Verificar se os botões estão clicáveis
            copiar_cpf = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Copiar CPF')]"))
            )
            copiar_senha = driver.find_element(By.XPATH, "//button[contains(text(), 'Copiar Senha')]")
            
            print('[SISBAJUD][LOGIN] ✅ Botões "Copiar CPF" e "Copiar Senha" prontos')
            print('[SISBAJUD][LOGIN] ✅ Tabela de credenciais completamente funcional')
            
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Tabela não apareceu ou botões não funcionais: {e}')
            return False
        
        # Aguardar estabilização
        print('[SISBAJUD][LOGIN] Aguardando estabilização final...')
        time.sleep(random.uniform(1.5, 2.5))
        
        # 1. Clicar em "Copiar CPF" com clique REAL e movimento muito humanizado
        print('[SISBAJUD][LOGIN] 1. Clicando em "Copiar CPF" (clique real)...')
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
            print('[SISBAJUD][LOGIN] ✅ Botão "Copiar CPF" clicado (clique real)')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao clicar "Copiar CPF": {e}')
            return False
        
        # 2. Clicar no campo username com movimento muito humanizado  
        print('[SISBAJUD][LOGIN] 2. Clicando no campo de usuário...')
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
                print('[SISBAJUD][LOGIN] Simulando hesitação humana...')
                actions.pause(random.uniform(0.5, 1.5))
            
            actions.click()
            actions.perform()
            
            time.sleep(random.uniform(0.5, 1.0))
            print('[SISBAJUD][LOGIN] ✅ Campo usuário selecionado')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao selecionar campo usuário: {e}')
            return False
        
        # 3. Ctrl+V para colar CPF com timing humanizado
        print('[SISBAJUD][LOGIN] 3. Colando CPF (timing humanizado)...')
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
                print(f'[SISBAJUD][LOGIN] ✅ CPF colado: {valor_colado[:6]}...')
            else:
                print('[SISBAJUD][LOGIN] ⚠️ Nenhum valor detectado no campo após colar')
                
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao colar CPF: {e}')
            return False
        
        # 4. Clicar em "Copiar Senha" com clique real e muito humanizado
        print('[SISBAJUD][LOGIN] 4. Clicando em "Copiar Senha" (clique real)...')
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
            print('[SISBAJUD][LOGIN] ✅ Botão "Copiar Senha" clicado (clique real)')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao clicar "Copiar Senha": {e}')
            return False
        
        # 5. Clicar no campo password
        print('[SISBAJUD][LOGIN] 5. Clicando no campo de senha...')
        try:
            password_field = driver.find_element(By.ID, "password")
            simular_movimento_humano(driver, password_field)
            
            # Simular hesitação humana
            if random.random() < 0.4:  # 40% chance de hesitação
                print('[SISBAJUD][LOGIN] Simulando hesitação humana...')
                time.sleep(random.uniform(0.5, 1.5))
            
            password_field.click()
            time.sleep(random.uniform(0.3, 0.8))
            print('[SISBAJUD][LOGIN] ✅ Campo senha selecionado')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao selecionar campo senha: {e}')
            return False
        
        # 6. Ctrl+V para colar senha
        print('[SISBAJUD][LOGIN] 6. Colando senha...')
        try:
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(random.uniform(0.8, 1.5))
            print('[SISBAJUD][LOGIN] ✅ Senha colada')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao colar senha: {e}')
            return False
        
        # 7. Clicar no botão "Entrar"
        print('[SISBAJUD][LOGIN] 7. Clicando em "Entrar"...')
        try:
            entrar_button = driver.find_element(By.ID, "kc-login")
            simular_movimento_humano(driver, entrar_button)
            
            # Simular pausa antes do login (comportamento humano)
            time.sleep(random.uniform(1.0, 2.5))
            
            entrar_button.click()
            print('[SISBAJUD][LOGIN] ✅ Botão "Entrar" clicado')
            
            # Aguardar login processar
            time.sleep(random.uniform(3.0, 5.0))
            
            # Verificar sucesso do login
            current_url = driver.current_url
            if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
                print('[SISBAJUD][LOGIN] ✅ Login realizado com sucesso!')
                return True
            else:
                print('[SISBAJUD][LOGIN] ❌ Login falhou - ainda na tela de autenticação')
                return False
                
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao clicar em "Entrar": {e}')
            return False
    
    except Exception as e:
        print(f'[SISBAJUD][LOGIN] ❌ Erro geral no login automatizado: {e}')
        return False

def driver_firefox_sisbajud(headless=False):
    """
    Retorna um driver Firefox usando o perfil dedicado do SISBAJUD.
    """
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    
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

# ===================== INICIALIZAÇÃO =====================

def salvar_dados_processo_temp(params_adicionais=None):
    """
    Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas
    """
    try:
        # Usa caminho do projeto ao invés de pasta temporária
        project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o sisbajud.py
        dados_path = os.path.join(project_path, 'dadosatuais.json')
        
        # Adicionar parâmetros de automação aos dados do processo
        dados_para_salvar = processo_dados_extraidos.copy()
        if params_adicionais:
            dados_para_salvar['parametros_automacao'] = params_adicionais
            print(f'[SISBAJUD] Parâmetros de automação adicionados: {params_adicionais}')
        
        # Sempre sobrescreve o arquivo para não acumular dados de múltiplos processos
        with open(dados_path, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
        print(f'[SISBAJUD] Dados do processo salvos em: {dados_path}')
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao salvar dados do processo: {e}')

# Variável global para armazenar dados do processo
processo_dados_extraidos = None

def iniciar_sisbajud(driver_pje=None):
    """
    Função unificada de inicialização do SISBAJUD:
    1. Extrai dados do processo PJe
    2. Cria driver Firefox SISBAJUD
    3. Verifica se já existe sessão ativa (via cookies)
    4. Se não houver sessão, insere tabela de credenciais e realiza login
    5. Salva cookies para sessões futuras
    """
    global processo_dados_extraidos
    
    try:
        print('[SISBAJUD] Iniciando sessão SISBAJUD...')
        
        # 1. Extrair dados do processo PJe (se driver fornecido)
        if driver_pje:
            print('[SISBAJUD] Extraindo dados do processo PJe...')
            from Fix import extrair_dados_processo
            processo_dados_extraidos = extrair_dados_processo(driver_pje)
            if processo_dados_extraidos:
                print(f'[SISBAJUD] ✅ Dados extraídos: {processo_dados_extraidos.get("numero_processo", "N/A")}')
                salvar_dados_processo_temp()
            else:
                print('[SISBAJUD] ⚠️ Não foi possível extrair dados do processo')
        else:
            print('[SISBAJUD] ⚠️ Driver PJE não fornecido, pulando extração de dados')
        
        # 2. Criar driver Firefox SISBAJUD
        print('[SISBAJUD] Criando driver Firefox SISBAJUD...')
        driver = driver_firefox_sisbajud()
        
        # 3. Verificar se já existe sessão ativa (via cookies)
        print('[SISBAJUD] Verificando sessão ativa via cookies...')
        if carregar_cookies_sisbajud(driver):
            print('[SISBAJUD] ✅ Sessão ativa encontrada via cookies')
            return driver
        
        # 4. Se não houver sessão, realizar login
        print('[SISBAJUD] Nenhuma sessão ativa encontrada. Realizando login...')
        
        # Inserir tabela de credenciais
        if not inserir_tabela_credenciais(driver):
            print('[SISBAJUD] ❌ Falha ao inserir tabela de credenciais')
            driver.quit()
            return None
        
        # Realizar login automatizado
        if not login_automatico_sisbajud(driver):
            print('[SISBAJUD] ❌ Falha no login automatizado')
            driver.quit()
            return None
        
        # 5. Salvar cookies para sessões futuras
        print('[SISBAJUD] Salvando cookies para sessões futuras...')
        salvar_cookies_sisbajud(driver)
        
        print('[SISBAJUD] ✅ Sessão SISBAJUD iniciada com sucesso!')
        return driver
        
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao iniciar sessão SISBAJUD: {e}')
        traceback.print_exc()
        return None

# ===================== FUNÇÕES PRINCIPAIS =====================

def minuta_bloqueio(driver_pje=None, dados_processo=None):
    """
    Cria minuta de bloqueio no SISBAJUD
    """
    try:
        print('\n[SISBAJUD] INICIANDO MINUTA DE BLOQUEIO')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao inicializar SISBAJUD')
            return None
        
        # 2. Clicar no botão "Nova" para criar nova minuta
        print('[SISBAJUD] Clicando no botão Nova...')
        seletores_nova = [
            'button[color="primary"][mat-fab] mat-icon.fa-plus',
            'button.mat-fab.mat-primary',
            '//button[contains(@class,"mat-fab") and contains(@class,"mat-primary")]//mat-icon[contains(@class,"fa-plus")]',
            '//button[contains(@class,"mat-fab")]//span[contains(text(),"Nova")]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_nova):
            print('[SISBAJUD] ❌ Falha ao clicar no botão Nova')
            driver_sisbajud.quit()
            return None
        
        time.sleep(2)
        
        # Aguardar carregamento da página de minuta (bloqueio já selecionado por padrão)
        print('[SISBAJUD] Aguardando carregamento da página de bloqueio...')
        time.sleep(3)
        
        # 3. Preencher dados do processo completo (seguindo lógica do gigs.py)
        print('[SISBAJUD] Preenchendo dados do processo...')
        
        # Obter dados do processo
        if not dados_processo:
            dados_processo = processo_dados_extraidos
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            driver_sisbajud.quit()
            return None
        
        # 3.1. Preencher número do processo
        numero_processo = dados_processo.get('numero', [''])[0] if isinstance(dados_processo.get('numero'), list) else dados_processo.get('numero', '')
        if numero_processo:
            print(f'[SISBAJUD] Preenchendo número do processo: {numero_processo}')
            seletores_numero_processo = [
                'input[name="numeroProcesso"]',
                'input[formcontrolname="numeroProcesso"]',
                'input[id*="numeroProcesso"]'
            ]
            preencher_campo(driver_sisbajud, seletores_numero_processo, numero_processo)
        
        # 3.2. Preencher motivo da consulta
        motivo_consulta = "Execução trabalhista"
        print(f'[SISBAJUD] Preenchendo motivo da consulta: {motivo_consulta}')
        seletores_motivo = [
            'textarea[name="motivoConsulta"]',
            'textarea[formcontrolname="motivoConsulta"]',
            'input[name="motivoConsulta"]'
        ]
        preencher_campo(driver_sisbajud, seletores_motivo, motivo_consulta)
        
        # 3.3. Preencher data de início (1 ano atrás)
        from datetime import datetime, timedelta
        data_atual = datetime.now()
        data_inicio = datetime(data_atual.year - 1, data_atual.month, 1).strftime('%d/%m/%Y')
        print(f'[SISBAJUD] Preenchendo data de início: {data_inicio}')
        seletores_data_inicio = [
            'input[name="dataInicio"]',
            'input[formcontrolname="dataInicio"]',
            'input[id*="dataInicio"]'
        ]
        preencher_campo(driver_sisbajud, seletores_data_inicio, data_inicio)
        
        # 3.4. Preencher data de fim (hoje)
        data_fim = data_atual.strftime('%d/%m/%Y')
        print(f'[SISBAJUD] Preenchendo data de fim: {data_fim}')
        seletores_data_fim = [
            'input[name="dataFim"]',
            'input[formcontrolname="dataFim"]',
            'input[id*="dataFim"]'
        ]
        preencher_campo(driver_sisbajud, seletores_data_fim, data_fim)
        
        # 3.5. Extrair e preencher documentos de todos os réus (usando função auxiliar)
        documentos_lista, documentos_concatenados = extrair_documentos_reus(dados_processo)
        
        if not documentos_concatenados:
            print('[SISBAJUD] ❌ Nenhum documento de réu encontrado nos dados do processo')
            print(f'[SISBAJUD] Dados disponíveis: {list(dados_processo.keys()) if dados_processo else "Nenhum"}')
            driver_sisbajud.quit()
            return None
        
        # Preencher campo de documentos (textarea para múltiplos CPFs/CNPJs)
        print('[SISBAJUD] Preenchendo documentos dos réus...')
        seletores_documento = [
            'textarea[name="cpfCnpj"]',
            'textarea[formcontrolname="cpfCnpj"]',
            'textarea[id*="cpfCnpj"]',
            'input[formcontrolname="documento"]',
            'input[id*="documento"]',
            'input[name*="documento"]'
        ]
        
        if not preencher_campo(driver_sisbajud, seletores_documento, documentos_concatenados):
            print('[SISBAJUD] ❌ Falha ao preencher campo de documentos')
            driver_sisbajud.quit()
            return None
        
        print('[SISBAJUD] ✅ Todos os campos preenchidos com sucesso')
        
        # 3.6. Clicar no botão Continuar (se existir)
        print('[SISBAJUD] Procurando botão Continuar...')
        seletores_continuar = [
            'input[value="Continuar"]',
            'button:contains("Continuar")',
            '//button[contains(text(),"Continuar")]',
            '//input[@value="Continuar"]'
        ]
        
        continuar_clicado = clicar_elemento(driver_sisbajud, seletores_continuar)
        if continuar_clicado:
            print('[SISBAJUD] ✅ Botão Continuar clicado')
            time.sleep(3)
        else:
            print('[SISBAJUD] ⚠️ Botão Continuar não encontrado - prosseguindo...')
        
        
        # 4. Selecionar juiz padrão
        print('[SISBAJUD] Selecionando juiz padrão...')
        
        # Clicar no campo de juiz
        seletores_juiz = [
            'input[formcontrolname="juiz"]',
            'input[id*="juiz"]',
            'input[name*="juiz"]',
            'input[placeholder*="Juiz"]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_juiz):
            print('[SISBAJUD] ❌ Falha ao clicar no campo de juiz')
            driver_sisbajud.quit()
            return None
        
        # Digitar nome do juiz
        juiz_nome = "OTAVIO AUGUSTO MACHADO DE OLIVEIRA"
        if not preencher_campo(driver_sisbajud, seletores_juiz, juiz_nome):
            print('[SISBAJUD] ❌ Falha ao preencher nome do juiz')
            driver_sisbajud.quit()
            return None
        
        time.sleep(2)
        
        # Selecionar opção correta do dropdown
        try:
            opcoes_juiz = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'span.mat-option-text')
            juiz_selecionado = False
            
            for opcao in opcoes_juiz:
                if juiz_nome in opcao.text:
                    opcao.click()
                    juiz_selecionado = True
                    print(f'[SISBAJUD] ✅ Juiz selecionado: {opcao.text}')
                    break
            
            if not juiz_selecionado:
                print('[SISBAJUD] ⚠️ Opção de juiz não encontrada no dropdown')
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}')
        
        # 5. Salvar minuta
        print('[SISBAJUD] Salvando minuta...')
        
        # Clicar no botão Salvar
        seletores_salvar = [
            'button.mat-fab.mat-primary mat-icon.fa-save',
            '//button[contains(@class,"mat-fab") and .//mat-icon[contains(@class,"fa-save")]]',
            '//button[contains(@class,"mat-primary") and .//mat-icon[contains(@class,"fa-save")]]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_salvar):
            print('[SISBAJUD] ❌ Falha ao clicar no botão Salvar')
            driver_sisbajud.quit()
            return None
        
        time.sleep(3)
        
        # Verificar se a minuta foi salva com sucesso
        if 'protocolo' in driver_sisbajud.current_url.lower() or 'minuta' in driver_sisbajud.current_url.lower():
            print('[SISBAJUD] ✅ Minuta salva com sucesso!')
            
            # Extrair protocolo se disponível
            try:
                protocolo_elemento = driver_sisbajud.find_element(By.CSS_SELECTOR, '.protocolo-minuta, .protocolo, [id*="protocolo"]')
                protocolo = protocolo_elemento.text.strip()
                print(f'[SISBAJUD] Protocolo gerado: {protocolo}')
            except:
                protocolo = None
            
            # Fechar driver
            driver_sisbajud.quit()
            
            # Retornar dados para o PJe
            return {
                'status': 'sucesso',
                'dados_minuta': {
                    'protocolo': protocolo,
                    'documento': documento_formatado,
                    'tipo_documento': tipo_doc
                },
                'acao_posterior': {
                    'tipo': 'atualizar_pje',
                    'parametros': {
                        'protocolo_sisbajud': protocolo,
                        'id_processo': dados_processo.get('id_processo')
                    }
                }
            }
        else:
            print('[SISBAJUD] ❌ Falha ao salvar minuta')
            driver_sisbajud.quit()
            return None
            
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha na minuta de bloqueio: {e}')
        traceback.print_exc()
        return None

def minuta_endereco(driver_pje=None, dados_processo=None):
    """
    Cria minuta de endereço no SISBAJUD
    """
    try:
        print('\n[SISBAJUD] INICIANDO MINUTA DE ENDEREÇO')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao inicializar SISBAJUD')
            return None
        
        # 2. Clicar no botão "Nova" para criar nova minuta
        print('[SISBAJUD] Clicando no botão Nova...')
        seletores_nova = [
            'button[color="primary"][mat-fab] mat-icon.fa-plus',
            'button.mat-fab.mat-primary',
            '//button[contains(@class,"mat-fab") and contains(@class,"mat-primary")]//mat-icon[contains(@class,"fa-plus")]',
            '//button[contains(@class,"mat-fab")]//span[contains(text(),"Nova")]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_nova):
            print('[SISBAJUD] ❌ Falha ao clicar no botão Nova')
            driver_sisbajud.quit()
            return None
        
        time.sleep(2)
        
        # Selecionar tipo de minuta: ENDEREÇO
        print('[SISBAJUD] Selecionando tipo de minuta: Endereço...')
        
        # 1. Clicar no radio button "Requisição de informações"
        print('[SISBAJUD] Selecionando "Requisição de informações"...')
        seletores_requisicao = [
            'label[for*="mat-radio"][for*="input"] div.mat-radio-label-content:contains("Requisição de informações")',
            '//label[contains(@class,"mat-radio-label")]//div[contains(@class,"mat-radio-label-content") and contains(text(),"Requisição de informações")]',
            '//input[@type="radio" and @value="2"]',
            'input[type="radio"][value="2"]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_requisicao):
            print('[SISBAJUD] ❌ Falha ao selecionar "Requisição de informações"')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 2. Marcar checkbox "Endereços"
        print('[SISBAJUD] Marcando checkbox "Endereços"...')
        seletores_checkbox_endereco = [
            'label.mat-checkbox-layout span.mat-checkbox-label:contains("Endereços")',
            '//label[contains(@class,"mat-checkbox-layout")]//span[contains(@class,"mat-checkbox-label") and contains(text(),"Endereços")]',
            '//input[@type="checkbox" and following-sibling::*//span[contains(text(),"Endereços")]]',
            'input[type="checkbox"][id*="mat-checkbox"]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_checkbox_endereco):
            print('[SISBAJUD] ❌ Falha ao marcar checkbox "Endereços"')
            driver_sisbajud.quit()
            return None
        
        # Aguardar carregamento da página de minuta de endereço
        print('[SISBAJUD] Aguardando carregamento da página de endereço...')
        time.sleep(3)
        
        # 3. Preencher dados do processo
        print('[SISBAJUD] Preenchendo dados do processo...')
        
        # Obter dados do processo
        if not dados_processo:
            dados_processo = processo_dados_extraidos
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            driver_sisbajud.quit()
            return None
        
        # Extrair documento (CPF/CNPJ) do primeiro réu
        documento = ''
        if 'reu' in dados_processo and len(dados_processo['reu']) > 0:
            documento = dados_processo['reu'][0].get('cpfcnpj', '')
        
        if not documento:
            print('[SISBAJUD] ❌ Documento do réu não encontrado nos dados do processo')
            print(f'[SISBAJUD] Dados disponíveis: {list(dados_processo.keys()) if dados_processo else "Nenhum"}')
            driver_sisbajud.quit()
            return None
        
        # Formatar documento
        tipo_doc = identificar_tipo_documento(documento)
        if tipo_doc == 'CPF':
            documento_formatado = formatar_cpf(documento)
        elif tipo_doc == 'CNPJ':
            documento_formatado = formatar_cnpj(documento)
        else:
            documento_formatado = documento
        
        print(f'[SISBAJUD] Documento formatado: {documento_formatado}')
        
        # Preencher campo de documento
        seletores_documento = [
            'input[formcontrolname="documento"]',
            'input[id*="documento"]',
            'input[name*="documento"]',
            'input[placeholder*="CPF"]',
            'input[placeholder*="CNPJ"]'
        ]
        
        if not preencher_campo(driver_sisbajud, seletores_documento, documento_formatado):
            print('[SISBAJUD] ❌ Falha ao preencher campo de documento')
            driver_sisbajud.quit()
            return None
        
        print('[SISBAJUD] ✅ Campo de documento preenchido')
        
        # 4. Selecionar juiz padrão
        print('[SISBAJUD] Selecionando juiz padrão...')
        
        # Clicar no campo de juiz
        seletores_juiz = [
            'input[formcontrolname="juiz"]',
            'input[id*="juiz"]',
            'input[name*="juiz"]',
            'input[placeholder*="Juiz"]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_juiz):
            print('[SISBAJUD] ❌ Falha ao clicar no campo de juiz')
            driver_sisbajud.quit()
            return None
        
        # Digitar nome do juiz
        juiz_nome = "OTAVIO AUGUSTO MACHADO DE OLIVEIRA"
        if not preencher_campo(driver_sisbajud, seletores_juiz, juiz_nome):
            print('[SISBAJUD] ❌ Falha ao preencher nome do juiz')
            driver_sisbajud.quit()
            return None
        
        time.sleep(2)
        
        # Selecionar opção correta do dropdown
        try:
            opcoes_juiz = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'span.mat-option-text')
            juiz_selecionado = False
            
            for opcao in opcoes_juiz:
                if juiz_nome in opcao.text:
                    opcao.click()
                    juiz_selecionado = True
                    print(f'[SISBAJUD] ✅ Juiz selecionado: {opcao.text}')
                    break
            
            if not juiz_selecionado:
                print('[SISBAJUD] ⚠️ Opção de juiz não encontrada no dropdown')
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}')
        
        # 5. Salvar minuta
        print('[SISBAJUD] Salvando minuta...')
        
        # Clicar no botão Salvar
        seletores_salvar = [
            'button.mat-fab.mat-primary mat-icon.fa-save',
            '//button[contains(@class,"mat-fab") and .//mat-icon[contains(@class,"fa-save")]]',
            '//button[contains(@class,"mat-primary") and .//mat-icon[contains(@class,"fa-save")]]'
        ]
        
        if not clicar_elemento(driver_sisbajud, seletores_salvar):
            print('[SISBAJUD] ❌ Falha ao clicar no botão Salvar')
            driver_sisbajud.quit()
            return None
        
        time.sleep(3)
        
        # Verificar se a minuta foi salva com sucesso
        if 'protocolo' in driver_sisbajud.current_url.lower() or 'minuta' in driver_sisbajud.current_url.lower():
            print('[SISBAJUD] ✅ Minuta salva com sucesso!')
            
            # Extrair protocolo se disponível
            try:
                protocolo_elemento = driver_sisbajud.find_element(By.CSS_SELECTOR, '.protocolo-minuta, .protocolo, [id*="protocolo"]')
                protocolo = protocolo_elemento.text.strip()
                print(f'[SISBAJUD] Protocolo gerado: {protocolo}')
            except:
                protocolo = None
            
            # Fechar driver
            driver_sisbajud.quit()
            
            # Retornar dados para o PJe
            return {
                'status': 'sucesso',
                'dados_minuta': {
                    'protocolo': protocolo,
                    'documento': documento_formatado,
                    'tipo_documento': tipo_doc
                },
                'acao_posterior': {
                    'tipo': 'atualizar_pje',
                    'parametros': {
                        'protocolo_sisbajud': protocolo,
                        'id_processo': dados_processo.get('id_processo')
                    }
                }
            }
        else:
            print('[SISBAJUD] ❌ Falha ao salvar minuta')
            driver_sisbajud.quit()
            return None
            
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha na minuta de endereço: {e}')
        traceback.print_exc()
        return None

# ===================== FUNÇÕES AUXILIARES PARA PROCESSAR BLOQUEIOS =====================

def _extrair_ordens_da_serie(driver, log=True):
    """Extrai ordens da página de detalhes da série"""
    ordens = []
    try:
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
        )
        
        linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
        meses = {
            "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
            "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
        }
        
        for linha in linhas:
            try:
                cols = linha.find_elements(By.CSS_SELECTOR, "td")
                sequencial = int(cols[0].text.strip())
                data_txt = cols[2].text.strip()
                protocolo = cols[5].text.strip()
                valor_txt = cols[4].text.strip()

                # Converter data
                data_ordem = None
                # Suporte ao formato 'dd/mm/yyyy, HH:MM'
                if "/" in data_txt:
                    partes = data_txt.split(",")
                    data_parte = partes[0].strip() if len(partes) > 0 else data_txt.strip()
                    hora_parte = partes[1].strip() if len(partes) > 1 else None
                    data_split = data_parte.split("/")
                    if len(data_split) == 3:
                        try:
                            dia, mes, ano = map(int, data_split)
                            if hora_parte:
                                hora_min = hora_parte.split(":")
                                if len(hora_min) == 2:
                                    hora, minuto = map(int, hora_min)
                                    data_ordem = datetime(ano, mes, dia, hora, minuto)
                                else:
                                    data_ordem = datetime(ano, mes, dia)
                            else:
                                data_ordem = datetime(ano, mes, dia)
                        except Exception as e:
                            if log:
                                print(f"[SISBAJUD] Ignorando ordem: data/hora inválida '{data_txt}' - {e}")
                            continue
                    else:
                        if log:
                            print(f"[SISBAJUD] Ignorando ordem: data com formato inesperado '{data_txt}'")
                        continue
                else:
                    partes = data_txt.split()
                    if len(partes) == 3:
                        try:
                            dia = int(partes[0])
                            mes_abr = partes[1].upper()
                            ano = int(partes[2])
                            mes = meses.get(mes_abr)
                            if not mes:
                                if log:
                                    print(f"[SISBAJUD] Ignorando ordem: mês inválido '{mes_abr}' em '{data_txt}'")
                                continue
                            data_ordem = datetime(ano, mes, dia)
                        except Exception as e:
                            if log:
                                print(f"[SISBAJUD] Ignorando ordem: data inválida '{data_txt}' - {e}")
                            continue
                    else:
                        if log:
                            print(f"[SISBAJUD] Ignorando ordem: data com formato inesperado '{data_txt}'")
                            continue

                if not data_ordem:
                    continue

                # Converter valor
                try:
                    valor = float(valor_txt.replace("R$", "")
                                   .replace("\u00a0", "")
                                   .replace(".", "")
                                   .replace(",", ".")
                                   .strip())
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] Ignorando ordem: valor inválido '{valor_txt}' - {e}")
                    continue

                ordens.append({
                    "sequencial": sequencial,
                    "data": data_ordem,
                    "valor_bloquear": valor,
                    "protocolo": protocolo,
                    "linha_el": linha
                })

                if log:
                    print(f"[SISBAJUD] Ordem {sequencial}: Data={data_ordem.strftime('%d/%m/%Y')}, Valor=R$ {valor:.2f}")

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Ignorando linha: erro inesperado - {e}")
                continue
        
        # Ordenar por data
        ordens.sort(key=lambda x: x["data"])
        return ordens
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] Erro ao extrair ordens: {e}")
        return []

def _identificar_ordens_com_bloqueio(ordens):
    """Identifica ordens que geraram bloqueio"""
    bloqueios = []
    for i in range(len(ordens) - 1):
        if ordens[i]["valor_bloquear"] > ordens[i + 1]["valor_bloquear"]:
            bloqueios.append(ordens[i])
    return bloqueios

def _processar_ordem(driver, ordem, tipo_fluxo, log=True):
    """Processa uma ordem individual"""
    try:
        # Abrir menu da ordem
        if log:
            print(f"[SISBAJUD] Abrindo menu da ordem {ordem['sequencial']}")
        
        menu_clicado = False
        for tentativa in range(3):
            try:
                botao_menu = ordem["linha_el"].find_element(By.CSS_SELECTOR, "mat-icon.fas.fa-ellipsis-h")
                botao_menu.click()
                
                # Aguardar menu aparecer
                WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-menu-panel"))
                )
                menu_clicado = True
                break
            except StaleElementReferenceException:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Elemento obsoleto, tentando novamente...")
                time.sleep(1)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar no menu: {e}")
                time.sleep(1)
        
        if not menu_clicado:
            if log:
                print(f"[SISBAJUD] ❌ Não foi possível abrir o menu da ordem {ordem['sequencial']}")
            return False
        
        # Clicar em Desdobrar
        if log:
            print(f"[SISBAJUD] Clicando em Desdobrar")

        desdobrar_clicado = False
        for tentativa in range(3):
            try:
                # Buscar botão pelo ícone fa-search-plus e texto Detalhar
                botoes_menu = driver.find_elements(By.CSS_SELECTOR, "button[role='menuitem']")
                for btn in botoes_menu:
                    try:
                        icone = btn.find_element(By.CSS_SELECTOR, "mat-icon.fas.fa-search-plus")
                        texto = btn.text.strip().lower()
                        if icone and "detalhar" in texto:
                            btn.click()
                            desdobrar_clicado = True
                            break
                    except Exception:
                        continue
                if desdobrar_clicado:
                    break
                time.sleep(1)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar em Detalhar: {e}")
                time.sleep(1)

        if not desdobrar_clicado:
            if log:
                print(f"[SISBAJUD] ❌ Não foi possível clicar em Detalhar")
            return False
        
        # Confirmar navegação para /desdobrar
        desdobrar_carregado = False
        for _ in range(10):
            if "/desdobrar" in driver.current_url:
                desdobrar_carregado = True
                break
            time.sleep(1)
        
        if not desdobrar_carregado:
            if log:
                print(f"[SISBAJUD] ❌ Página de desdobramento não carregou")
            return False
        
        if log:
            print(f"[SISBAJUD] ✅ Página de desdobramento carregada")

        # Reduzir zoom para 40% após abrir cada ordem
        try:
            driver.execute_script("document.body.style.zoom='0.4'")
            if log:
                print("[SISBAJUD] ✅ Zoom da página ajustado para 40%")
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ⚠️ Não foi possível ajustar o zoom: {e}")
        
        # Preencher campos conforme tipo de fluxo
        if tipo_fluxo == "DESBLOQUEIO":
            if log:
                print(f"[SISBAJUD] Preenchendo campos para DESBLOQUEIO")
            
            # Selecionar Juiz
            try:
                juiz_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
                )
                juiz_input.clear()
                juiz_input.send_keys("OTAVIO AUGUSTO")
                time.sleep(1)
                # Clicar na opção correta do dropdown
                opcoes_juiz = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                juiz_clicado = False
                for opcao in opcoes_juiz:
                    if "OTAVIO AUGUSTO MACHADO DE OLIVEIRA" in opcao.text:
                        opcao.click()
                        juiz_clicado = True
                        if log:
                            print(f"[SISBAJUD] ✅ Juiz 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA' selecionado")
                        break
                if not juiz_clicado:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Opção de juiz não encontrada no dropdown")
                # Clicar fora para fechar o dropdown do juiz
                try:
                    driver.find_element(By.TAG_NAME, "body").click()
                    time.sleep(0.5)
                except Exception:
                    pass
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}")
            
            # IMPLEMENTAÇÃO 1: Preenchimento de CPF/CNPJ na criação de minuta
            try:
                if log:
                    print("[SISBAJUD] Preenchendo CPF/CNPJ na criação de minuta")
                
                # Localizar campo CPF/CNPJ
                campo_cpf_cnpj = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[formcontrolname='documento']"))
                )
                
                # Limpar campo
                campo_cpf_cnpj.clear()
                
                # Preencher com valor completo (14 dígitos para CNPJ, 11 para CPF)
                # Exemplo: "12345678901234" (CNPJ) ou "12345678901" (CPF)
                documento_completo = "12345678901234"  # Substituir pelo valor real obtido
                campo_cpf_cnpj.send_keys(documento_completo)
                
                if log:
                    print(f"[SISBAJUD] ✅ CPF/CNPJ preenchido com {len(documento_completo)} dígitos")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao preencher CPF/CNPJ: {e}")
            
            # IMPLEMENTAÇÃO 2: Seleção da caixa de ações na ordem de bloqueio
            try:
                if log:
                    print("[SISBAJUD] Selecionando ação na ordem de bloqueio")
                
                # Localizar dropdown de ações
                dropdown_acao = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='acao']"))
                )
                
                # Clicar para abrir dropdown
                dropdown_acao.click()
                time.sleep(0.5)
                
                # Aguardar opções aparecerem
                opcoes_acao = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option"))
                )
                
                # Selecionar opção desejada conforme o fluxo
                opcao_desejada = "Desbloquear valor" if tipo_fluxo == "DESBLOQUEIO" else "Transferir valor"
                
                opcao_encontrada = False
                for opcao in opcoes_acao:
                    if opcao_desejada in opcao.text:
                        # Rolar até a opção para garantir visibilidade
                        driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                        time.sleep(0.3)
                        
                        # Clicar na opção
                        opcao.click()
                        opcao_encontrada = True
                        
                        if log:
                            print(f"[SISBAJUD] ✅ Ação '{opcao_desejada}' selecionada")
                        break
                
                if not opcao_encontrada:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Opção '{opcao_desejada}' não encontrada")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar ação: {e}")
            
        else:  # POSITIVO
            if log:
                print(f"[SISBAJUD] Preenchendo campos para POSITIVO")
            
            # Implementação para fluxo positivo
            try:
                juiz_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
                )
                juiz_input.clear()
                juiz_input.send_keys("OTAVIO AUGUSTO\n")
                if log:
                    print(f"[SISBAJUD] ✅ Juiz selecionado")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}")
            
            # IMPLEMENTAÇÃO 1: Preenchimento de CPF/CNPJ na criação de minuta
            try:
                if log:
                    print("[SISBAJUD] Preenchendo CPF/CNPJ na criação de minuta")
                
                # Localizar campo CPF/CNPJ
                campo_cpf_cnpj = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[formcontrolname='documento']"))
                )
                
                # Limpar campo
                campo_cpf_cnpj.clear()
                
                # Preencher com valor completo (14 dígitos para CNPJ, 11 para CPF)
                # Exemplo: "12345678901234" (CNPJ) ou "12345678901" (CPF)
                documento_completo = "12345678901234"  # Substituir pelo valor real obtido
                campo_cpf_cnpj.send_keys(documento_completo)
                
                if log:
                    print(f"[SISBAJUD] ✅ CPF/CNPJ preenchido com {len(documento_completo)} dígitos")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao preencher CPF/CNPJ: {e}")
            
            # IMPLEMENTAÇÃO 2: Seleção da caixa de ações na ordem de bloqueio
            try:
                if log:
                    print("[SISBAJUD] Selecionando ação na ordem de bloqueio")
                
                # Localizar dropdown de ações
                dropdown_acao = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='acao']"))
                )
                
                # Clicar para abrir dropdown
                dropdown_acao.click()
                time.sleep(0.5)
                
                # Aguardar opções aparecerem
                opcoes_acao = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option"))
                )
                
                # Selecionar opção desejada conforme o fluxo
                opcao_desejada = "Desbloquear valor" if tipo_fluxo == "DESBLOQUEIO" else "Transferir valor"
                
                opcao_encontrada = False
                for opcao in opcoes_acao:
                    if opcao_desejada in opcao.text:
                        # Rolar até a opção para garantir visibilidade
                        driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                        time.sleep(0.3)
                        
                        # Clicar na opção
                        opcao.click()
                        opcao_encontrada = True
                        
                        if log:
                            print(f"[SISBAJUD] ✅ Ação '{opcao_desejada}' selecionada")
                        break
                
                if not opcao_encontrada:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Opção '{opcao_desejada}' não encontrada")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar ação: {e}")
        
        # Clicar em Salvar
        if log:
            print(f"[SISBAJUD] Clicando em Salvar")
        salvar_clicado = False
        for tentativa in range(3):
            try:
                seletores_salvar = [
                    "button.mat-fab.mat-primary mat-icon.fa-save",
                    "//button[contains(@class,'mat-fab') and .//mat-icon[contains(@class,'fa-save')]]",
                    "//button[contains(@class,'mat-primary') and .//mat-icon[contains(@class,'fa-save')]]"
                ]
                for seletor in seletores_salvar:
                    try:
                        if seletor.startswith("//"):
                            btn_salvar = driver.find_element(By.XPATH, seletor)
                        else:
                            btn_salvar = driver.find_element(By.CSS_SELECTOR, seletor)
                        btn_salvar.click()
                        salvar_clicado = True
                        break
                    except:
                        continue
                if salvar_clicado:
                    break
                time.sleep(1)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar em Salvar: {e}")
                time.sleep(1)
        if not salvar_clicado:
            if log:
                print(f"[SISBAJUD] ❌ Não foi possível clicar em Salvar")
            return False

        # Após salvar, preencher dados de transferência no fluxo POSITIVO
        if tipo_fluxo == "POSITIVO":
            try:
                if log:
                    print("[SISBAJUD] Preenchendo dados de transferência (depósito)")
                
                # IMPLEMENTAÇÃO 3: Preenchimento completo do modal de dados de depósito
                # Tipo de crédito: Geral
                tipo_credito_select = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-select[formcontrolname="tipoCredito"]'))
                )
                tipo_credito_select.click()
                time.sleep(1)
                opcoes_tipo = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                for opcao in opcoes_tipo:
                    if "Geral" in opcao.text:
                        opcao.click()
                        if log:
                            print("[SISBAJUD] ✅ Tipo de crédito 'Geral' selecionado")
                        break
                
                # Banco: 0001 Banco do Brasil
                banco_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="instituicaoFinanceiraPorCategoria"]'))
                )
                banco_input.click()
                time.sleep(1)
                opcoes_banco = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                for opcao in opcoes_banco:
                    if "0001 Banco do Brasil" in opcao.text:
                        opcao.click()
                        if log:
                            print("[SISBAJUD] ✅ Banco '0001 Banco do Brasil' selecionado")
                        break
                
                # Agência: 5905
                agencia_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="agencia"]'))
                )
                agencia_input.clear()
                agencia_input.send_keys("5905")
                if log:
                    print("[SISBAJUD] ✅ Agência '5905' preenchida")
                
                # Clicar em Salvar após preencher dados de depósito
                if log:
                    print("[SISBAJUD] Clicando em Salvar após preencher dados de depósito")
                
                btn_salvar_deposito = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mat-fab.mat-primary mat-icon.fa-save"))
                )
                btn_salvar_deposito.click()
                
                if log:
                    print("[SISBAJUD] ✅ Dados de depósito salvos com sucesso")
                    
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao preencher dados de transferência: {e}")
        
        # Aguardar botão Protocolar aparecer
        protocolar_apareceu = False
        for _ in range(10):
            try:
                driver.find_element(By.XPATH, "//button[contains(@class,'mat-fab') and @title='Protocolar']")
                protocolar_apareceu = True
                break
            except:
                time.sleep(1)
        
        if not protocolar_apareceu:
            if log:
                print(f"[SISBAJUD] ❌ Botão Protocolar não apareceu após salvar")
            return False
        
        if log:
            print(f"[SISBAJUD] ✅ Ordem {ordem['sequencial']} processada com sucesso")
        
        return True
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao processar ordem {ordem['sequencial']}: {e}")
        return False

def processar_ordem_sisbajud(driver, dados_processo, log=True):
    """
    Processamento completo de ordens no SISBAJUD:
    1. Navegação para teimosinha
    2. Filtro de ordens recentes
    3. Extração de dados
    4. Processamento individual de cada ordem
    5. Fechamento do driver
    """
    resultado = {
        'status': 'pendente',
        'tipo_fluxo': None,
        'series_processadas': 0,
        'ordens_processadas': 0,
        'erros': [],
        'detalhes': {}
    }
    
    try:
        # ETAPA 1: NAVEGAÇÃO INICIAL
        if log:
            print("\n" + "="*80)
            print("[SISBAJUD] INICIANDO PROCESSAMENTO COMPLETO")
            print("="*80)
        
        # Verificar URL inicial
        current_url = driver.current_url
        if 'sisbajud.cnj.jus.br' not in current_url:
            erro = f"URL inválida: {current_url}"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        # Navegar para /minuta se necessário
        if '/minuta' not in current_url:
            if log:
                print("[SISBAJUD] Navegando para /minuta...")
            driver.get('https://sisbajud.cnj.jus.br/minuta')
            time.sleep(2)
        
        # ETAPA 2: ACESSAR TEIMOSINHA
        if log:
            print("\n[SISBAJUD] ETAPA 1: NAVEGAÇÃO PARA TEIMOSINHA")
        
        # Clicar no menu hamburguer
        if log:
            print("[SISBAJUD] 1. Clicando no menu hamburguer...")
        hamburger_clicado = False
        seletores_hamburger = [
            'button.btn-hamburger.hamburger--slider.mat-flat-button',
            'button[aria-label="Abri menu de navegação"]',
            'button.btn-hamburger',
            'button[mattooltip="Abri menu de navegação"]'
        ]
        
        for i, seletor in enumerate(seletores_hamburger, 1):
            try:
                hamburguer_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                )
                hamburguer_btn.click()
                if log:
                    print(f"[SISBAJUD] ✅ Menu hamburguer clicado com seletor {i}: {seletor}")
                hamburger_clicado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not hamburger_clicado:
            erro = "Não foi possível clicar no menu hamburguer"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(1)
        
        # Clicar no link Teimosinha
        if log:
            print("[SISBAJUD] 2. Clicando no link Teimosinha...")
        teimosinha_clicado = False
        seletores_teimosinha = [
            'a[href="/teimosinha"]',
            'a[aria-label="Ir para Teimosinha"]',
            'a:contains("Teimosinha")',
            'a.mat-button[href="/teimosinha"]'
        ]
        
        for i, seletor in enumerate(seletores_teimosinha, 1):
            try:
                if ':contains(' in seletor:
                    teimosinha_link = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Teimosinha')]"))
                    )
                else:
                    teimosinha_link = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                teimosinha_link.click()
                if log:
                    print(f"[SISBAJUD] ✅ Link Teimosinha clicado com seletor {i}: {seletor}")
                teimosinha_clicado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not teimosinha_clicado:
            erro = "Não foi possível clicar no link Teimosinha"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(2)
        
        # Confirmar URL /teimosinha
        current_url = driver.current_url
        if '/teimosinha' not in current_url:
            erro = f"Falha na navegação para teimosinha. URL atual: {current_url}"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print(f"[SISBAJUD] ✅ Navegação confirmada: {current_url}")
        
        # Preencher campo do processo
        if log:
            print("[SISBAJUD] 3. Preenchendo número do processo...")
        
        numero_processo = None
        if dados_processo and isinstance(dados_processo, dict):
            numero_processo = dados_processo.get('numero_processo')
        
        if not numero_processo:
            erro = "Número do processo não encontrado nos dados extraídos"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print(f"[SISBAJUD] Processo a consultar: {numero_processo}")
        
        input_preenchido = False
        seletores_input_processo = [
            'input[placeholder="Número do Processo"]',
            'input[mask="0000000-00.0000.0.00.0000"]',
            'input.mat-input-element[maxlength="25"]',
            'input[id*="mat-input"]'
        ]
        
        for i, seletor in enumerate(seletores_input_processo, 1):
            try:
                input_processo = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                )
                input_processo.clear()
                input_processo.send_keys(numero_processo)
                if log:
                    print(f"[SISBAJUD] ✅ Campo processo preenchido com seletor {i}: {seletor}")
                input_preenchido = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not input_preenchido:
            erro = "Não foi possível preencher o campo do processo"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(1)
        
        # Clicar no botão Consultar
        if log:
            print("[SISBAJUD] 4. Clicando no botão Consultar...")
        consultar_clicado = False
        seletores_btn_consultar = [
            'button.mat-fab.mat-primary:has(mat-icon.fa-search)',
            'button[color="primary"][mat-fab]:has(mat-icon)',
            'button.mat-fab:contains("Consultar")',
            'button.mat-fab.mat-primary'
        ]
        
        for i, seletor in enumerate(seletores_btn_consultar, 1):
            try:
                if ':has(' in seletor or ':contains(' in seletor:
                    btn_consultar = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-fab') and contains(@class, 'mat-primary')]//mat-icon[contains(@class, 'fa-search')]//ancestor::button"))
                    )
                else:
                    btn_consultar = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                btn_consultar.click()
                if log:
                    print(f"[SISBAJUD] ✅ Botão Consultar clicado com seletor {i}: {seletor}")
                consultar_clicado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not consultar_clicado:
            erro = "Não foi possível clicar no botão Consultar"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(3)
        
        # Confirmar página de resultados
        if log:
            print("[SISBAJUD] 5. Confirmando página de resultados...")
        header_encontrado = False
        seletores_header_serie = [
            'th.mat-header-cell:contains("ID da série")',
            'th[class*="sequencial"]:contains("ID")',
            'th.cdk-column-sequencial'
        ]
        
        for i, seletor in enumerate(seletores_header_serie, 1):
            try:
                if ':contains(' in seletor:
                    header = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//th[contains(text(), 'ID da série')]"))
                    )
                else:
                    header = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                    )
                if log:
                    print(f"[SISBAJUD] ✅ Cabeçalho encontrado com seletor {i}: {seletor}")
                header_encontrado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not header_encontrado:
            erro = "Página de resultados não confirmada - cabeçalho 'ID da série' não encontrado"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print("[SISBAJUD] ✅ Navegação inicial concluída com sucesso!")
        
        # ETAPA 3: FILTRO E EXTRAÇÃO DE SÉRIES
        if log:
            print("\n[SISBAJUD] ETAPA 2: FILTRO E EXTRAÇÃO DE SÉRIES")
        
        # Calcular data limite (15 dias antes da data atual)
        data_atual = datetime.now()
        data_limite = data_atual - timedelta(days=15)
        if log:
            print(f"[SISBAJUD] Data limite para filtro: {data_limite.strftime('%d/%m/%Y')}")
        
        # Extrair dados das séries
        series_validas = []
        try:
            tabela = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
            )
            
            linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody tr.mat-row')
            if log:
                print(f"[SISBAJUD] Encontradas {len(linhas)} linhas na tabela")
            
            if len(linhas) == 0:
                erro = "Nenhuma série encontrada na tabela"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['status'] = 'erro'
                resultado['erros'].append(erro)
                return resultado
            
            for idx, linha in enumerate(linhas, 1):
                try:
                    # Extrair dados da linha
                    id_serie = linha.find_element(By.CSS_SELECTOR, 'td[data-label="sequencial"]').text.strip()
                    situacao = linha.find_element(By.CSS_SELECTOR, 'td[data-label="dataFim"]').text.strip()
                    data_programada_text = linha.find_element(By.CSS_SELECTOR, 'td[data-label="dataProgramada"]').text.strip()
                    valor_bloqueado_text = linha.find_element(By.CSS_SELECTOR, 'td[data-label="valorBloqueado"]').text.strip()
                    valor_bloquear_text = linha.find_element(By.CSS_SELECTOR, 'td[data-label="valorBloquear"]').text.strip()

                    if log:
                        print(f"[SISBAJUD] Série {idx}: ID={id_serie}, Situação={situacao}, Data={data_programada_text}")

                    # Verificar se situação é "Encerrada"
                    if 'encerrada' not in situacao.lower():
                        if log:
                            print(f"[SISBAJUD] Série {id_serie} rejeitada: situação não é 'Encerrada' ({situacao})")
                        continue

                    # Verificar data programada
                    try:
                        meses = {
                            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
                            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
                        }

                        partes = data_programada_text.upper().split()
                        if len(partes) >= 5:
                            dia = int(partes[0])
                            mes = meses.get(partes[2], 1)
                            ano = int(partes[4])
                            data_programada = datetime(ano, mes, dia)

                            # CORREÇÃO: considerar apenas séries finalizadas nos últimos 15 dias
                            if data_programada < data_limite:
                                if log:
                                    print(f"[SISBAJUD] Série {id_serie} rejeitada: data muito antiga ({data_programada.strftime('%d/%m/%Y')} < {data_limite.strftime('%d/%m/%Y')})")
                                continue
                        else:
                            if log:
                                print(f"[SISBAJUD] Série {id_serie}: formato de data inválido - {data_programada_text}")
                            continue
                            
                    except Exception as e:
                        if log:
                            print(f"[SISBAJUD] Erro ao processar data da série {id_serie}: {e}")
                        continue
                    
                    # Converter valores monetários
                    def extrair_valor_monetario(texto):
                        texto_limpo = texto.replace('R$', '').replace('\\xa0', '').replace('&nbsp;', '').strip()
                        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
                        try:
                            return float(texto_limpo)
                        except:
                            return 0.0
                    
                    valor_bloqueado = extrair_valor_monetario(valor_bloqueado_text)
                    valor_bloquear = extrair_valor_monetario(valor_bloquear_text)
                    
                    # Adicionar série válida
                    serie_data = {
                        'id_serie': id_serie,
                        'situacao': situacao,
                        'data_programada': data_programada,
                        'valor_bloqueado': valor_bloqueado,
                        'valor_bloquear': valor_bloquear,
                        'valor_bloqueado_text': valor_bloqueado_text,
                        'valor_bloquear_text': valor_bloquear_text
                    }
                    
                    series_validas.append(serie_data)
                    if log:
                        print(f"[SISBAJUD] ✅ Série {id_serie} válida: R$ {valor_bloqueado:.2f} bloqueado")
                    
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] Erro ao processar linha {idx}: {e}")
                    continue
            
        except Exception as e:
            erro = f"Erro ao extrair dados da tabela: {str(e)}"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        # Verificar se há séries válidas
        if len(series_validas) == 0:
            erro = "Não há teimosinha para processar"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'concluido'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print(f"[SISBAJUD] ✅ Encontradas {len(series_validas)} séries válidas para processamento")
        
        # ETAPA 4: DEFINIÇÃO DE FLUXO
        if log:
            print("\n[SISBAJUD] ETAPA 3: DEFINIÇÃO DE FLUXO")
        
        total_bloqueado = sum(s['valor_bloqueado'] for s in series_validas)
        total_bloquear = sum(s['valor_bloquear'] for s in series_validas)
        
        if log:
            print(f"[SISBAJUD] Total bloqueado: R$ {total_bloqueado:.2f}")
            print(f"[SISBAJUD] Total a bloquear: R$ {total_bloquear:.2f}")
        
        # Determinar tipo de fluxo
        if total_bloqueado == 0.0:
            tipo_fluxo = 'NEGATIVO'
            if log:
                print("[SISBAJUD] 🔴 FLUXO NEGATIVO: Total bloqueado = 0")
        elif total_bloqueado < 100.0 and total_bloquear >= 1000.0:
            tipo_fluxo = 'DESBLOQUEIO'
            if log:
                print(f"[SISBAJUD] 🟡 FLUXO DESBLOQUEIO: Total bloqueado < R$ 100,00 e valor a bloquear >= R$ 1.000,00")
        elif total_bloqueado < 100.0 and total_bloquear < 1000.0:
            tipo_fluxo = 'POSITIVO'
            if log:
                print(f"[SISBAJUD] 🟢 FLUXO POSITIVO: Total bloqueado < R$ 100,00 mas valor a bloquear < R$ 1.000,00")
        else:
            tipo_fluxo = 'POSITIVO'
            if log:
                print(f"[SISBAJUD] 🟢 FLUXO POSITIVO: Total bloqueado >= R$ 100,00")
        
        resultado['tipo_fluxo'] = tipo_fluxo
        
        # ETAPA 5: PROCESSAMENTO DE ORDENS
        if log:
            print("\n[SISBAJUD] ETAPA 4: PROCESSAMENTO DE ORDENS")
            print(f"[SISBAJUD] Tipo de fluxo: {tipo_fluxo}")
        
        if tipo_fluxo == 'NEGATIVO':
            if log:
                print("[SISBAJUD] Fluxo NEGATIVO, nenhuma série será processada.")
            resultado['status'] = 'concluido'
            return resultado
        
        # Processar cada série
        for idx, serie in enumerate(series_validas, 1):
            if log:
                print(f"\n[SISBAJUD] >>> Processando série {idx}/{len(series_validas)} ID={serie['id_serie']}")

            # Navegar para detalhes da série via clique
            try:
                # 1. Clicar no menu da linha da série
                if log:
                    print(f"[SISBAJUD] Clicando no menu da série {serie['id_serie']}")
                linha_serie = None
                # Buscar a linha correspondente na tabela
                tabela = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody tr.mat-row')
                for linha in linhas:
                    try:
                        id_serie_linha = linha.find_element(By.CSS_SELECTOR, 'td[data-label="sequencial"]').text.strip()
                        if id_serie_linha == serie['id_serie']:
                            linha_serie = linha
                            break
                    except:
                        continue
                if not linha_serie:
                    erro = f"Linha da série {serie['id_serie']} não encontrada para clique no menu"
                    if log:
                        print(f"[SISBAJUD] ❌ {erro}")
                    resultado['erros'].append(erro)
                    continue

                botao_menu = linha_serie.find_element(By.CSS_SELECTOR, 'button.mat-menu-trigger.mat-icon-button')
                botao_menu.click()
                time.sleep(1)

                # 2. Clicar em 'Detalhar' no menu
                if log:
                    print(f"[SISBAJUD] Clicando em 'Detalhar' para série {serie['id_serie']}")
                detalhar_clicado = False
                for tentativa in range(3):
                    try:
                        botoes_menu = driver.find_elements(By.CSS_SELECTOR, 'button[role="menuitem"]')
                        for btn in botoes_menu:
                            try:
                                texto_btn = btn.text.strip().lower()
                                if 'detalhar' in texto_btn:
                                    btn.click()
                                    detalhar_clicado = True
                                    break
                            except:
                                continue
                        if detalhar_clicado:
                            break
                        time.sleep(1)
                    except Exception as e:
                        if log:
                            print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar em 'Detalhar': {e}")
                        time.sleep(1)
                if not detalhar_clicado:
                    erro = f"Não foi possível clicar em 'Detalhar' para série {serie['id_serie']}"
                    if log:
                        print(f"[SISBAJUD] ❌ {erro}")
                    resultado['erros'].append(erro)
                    continue

                # 3. Confirmar navegação
                detalhes_carregado = False
                for _ in range(10):
                    if "/detalhes" in driver.current_url and serie["id_serie"] in driver.current_url:
                        detalhes_carregado = True
                        break
                    time.sleep(1)
                if not detalhes_carregado:
                    erro = f"Falha ao abrir detalhes da série {serie['id_serie']}"
                    if log:
                        print(f"[SISBAJUD] ❌ {erro}")
                    resultado['erros'].append(erro)
                    continue
                if log:
                    print(f"[SISBAJUD] ✅ Detalhes da série {serie['id_serie']} carregados")
            except Exception as e:
                erro = f"Erro na navegação para detalhes da série {serie['id_serie']}: {e}"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['erros'].append(erro)
                continue
            
            # Extrair ordens da série
            try:
                ordens = _extrair_ordens_da_serie(driver, log)
                if log:
                    print(f"[SISBAJUD] Encontradas {len(ordens)} ordens na série")
                
                # Identificar ordens com bloqueio
                ordens_bloqueio = _identificar_ordens_com_bloqueio(ordens)
                if log:
                    print(f"[SISBAJUD] Encontradas {len(ordens_bloqueio)} ordens com bloqueio")
                
                # Processar cada ordem com bloqueio
                for ordem in ordens_bloqueio:
                    if log:
                        print(f"[SISBAJUD] Processando ordem {ordem['sequencial']} - Protocolo: {ordem['protocolo']}")
                    
                    sucesso = _processar_ordem(driver, ordem, tipo_fluxo, log)
                    if sucesso:
                        resultado['ordens_processadas'] += 1
                        if log:
                            print(f"[SISBAJUD] ✅ Ordem {ordem['sequencial']} processada com sucesso")
                    else:
                        erro = f"Falha ao processar ordem {ordem['sequencial']}"
                        if log:
                            print(f"[SISBAJUD] ❌ {erro}")
                        resultado['erros'].append(erro)
                
                resultado['series_processadas'] += 1
                
            except Exception as e:
                erro = f"Erro ao processar série {serie['id_serie']}: {str(e)}"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['erros'].append(erro)
            
            # Fechar aba de detalhes
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
        
        # ETAPA 6: FINALIZAÇÃO
        if log:
            print("\n[SISBAJUD] ETAPA 5: FINALIZAÇÃO")
        
        # Fechar driver SISBAJUD
        driver.quit()
        if log:
            print("[SISBAJUD] ✅ Driver SISBAJUD fechado")
        
        resultado['status'] = 'concluido'
        return resultado
        
    except Exception as e:
        erro = f"Erro geral no processamento: {str(e)}"
        if log:
            print(f"[SISBAJUD] ❌ {erro}")
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)
        
        try:
            driver.quit()
        except:
            pass
        
        return resultado

def processar_bloqueios(driver_pje=None, dados_processo=None):
    """
    Processa bloqueios no SISBAJUD usando a função processar_ordem_sisbajud
    """
    try:
        print('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE BLOQUEIOS')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao inicializar SISBAJUD')
            return None
        
        # 2. Obter dados do processo
        if not dados_processo:
            dados_processo = processo_dados_extraidos
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            driver_sisbajud.quit()
            return None
        
        # 3. Processar ordens SISBAJUD
        resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo)
        
        # 4. Retornar resultado para o PJe
        if resultado['status'] == 'concluido':
            print('[SISBAJUD] ✅ Processamento de bloqueios concluído com sucesso!')
            
            return {
                'status': 'sucesso',
                'dados_processamento': resultado,
                'acao_posterior': {
                    'tipo': 'atualizar_pje_bloqueios',
                    'parametros': {
                        'id_processo': dados_processo.get('id_processo'),
                        'tipo_fluxo': resultado.get('tipo_fluxo'),
                        'series_processadas': resultado.get('series_processadas', 0),
                        'ordens_processadas': resultado.get('ordens_processadas', 0)
                    }
                }
            }
        else:
            print('[SISBAJUD] ❌ Falha no processamento de bloqueios')
            return {
                'status': 'erro',
                'erros': resultado.get('erros', []),
                'acao_posterior': None
            }
            
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha no processamento de bloqueios: {e}')
        traceback.print_exc()
        return None

def processar_endereco(driver_pje=None, dados_processo=None):
    """
    Processa endereços no SISBAJUD (placeholder)
    """
    try:
        print('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE ENDEREÇO')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao inicializar SISBAJUD')
            return None
        
        # 2. Obter dados do processo
        if not dados_processo:
            dados_processo = processo_dados_extraidos
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            driver_sisbajud.quit()
            return None
        
        # Placeholder para implementação futura
        print('[SISBAJUD] ⚠️ Função processar_endereco ainda não implementada')
        
        # Fechar driver
        driver_sisbajud.quit()
        
        return {
            'status': 'pendente',
            'mensagem': 'Função processar_endereco ainda não implementada',
            'acao_posterior': None
        }
        
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha no processamento de endereço: {e}')
        traceback.print_exc()
        return None