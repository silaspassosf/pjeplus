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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import traceback
import random
import tempfile

# Importações de outros módulos
from Fix import extrair_dados_processo
from driver_config import criar_driver, login_func, criar_driver_sisb

# ===================== UTILITÁRIOS =====================

def formatar_moeda_brasileira(valor):
    """
    Formatar valor monetário conforme padrão brasileiro do gigs-plugin.js
    Intl.NumberFormat('pt-br', {style: 'currency', currency: 'BRL'})
    Exemplo: 3777.29 -> "R$ 3.777,29"
    """
    try:
        if isinstance(valor, str):
            # Remover formatação existente: 'R$', espaços, pontos de milhar e usar ponto decimal
            valor_limpo = valor.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            valor = float(valor_limpo)

        # Formatação brasileira exata: R$ 1.234,56
        valor_formatado = f"R$ {valor:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        return valor_formatado
    except Exception:
        return str(valor)
def aplicar_acao_por_fluxo(driver, tipo_fluxo, ordem_sequencial=None, log=True):
    """
    Wrapper reutilizável para selecionar a ação correta na página /desdobrar.
    Prioriza 'transferir' para POSITIVO e 'desbloquear' para DESBLOQUEIO.
    Retorna True se a ação foi selecionada e confirmada visualmente no mat-select.
    """
    try:
        if log:
            print(f"[SISBAJUD] ℹ️ Aplicando ação para fluxo {tipo_fluxo} (ordem {ordem_sequencial})")

        # tentar abrir dropdown(s) de ação e selecionar
        dropdown = None
        try:
            # tentar encontrar qualquer mat-select plausível
            selects = driver.find_elements(By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao'], sisbajud-inclusao-desdobramento mat-select, mat-select")
        except Exception:
            selects = []

        if not selects:
            if log:
                print('[SISBAJUD] ⚠️ Nenhum mat-select encontrado para ações')
            return False

        # iterar em cada select visível/habilitado e tentar selecionar opção desejada
        for idx in range(len(selects)):
            try:
                # re-obter elemento para evitar stale
                try:
                    sel = driver.find_elements(By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao'], sisbajud-inclusao-desdobramento mat-select, mat-select")[idx]
                except Exception:
                    continue

                # abrir
                opened = False
                try:
                    trigger = None
                    try:
                        trigger = sel.find_element(By.CSS_SELECTOR, '.mat-select-trigger')
                    except Exception:
                        trigger = None
                    if trigger:
                        try:
                            trigger.click()
                            opened = True
                        except Exception:
                            try:
                                driver.execute_script('arguments[0].click();', trigger)
                                opened = True
                            except Exception:
                                opened = False
                    if not opened:
                        try:
                            sel.click()
                            opened = True
                        except Exception:
                            try:
                                driver.execute_script('arguments[0].click();', sel)
                                opened = True
                            except Exception:
                                opened = False
                except StaleElementReferenceException:
                    time.sleep(0.2)
                    continue

                if not opened:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Falha ao abrir dropdown de ação #{idx+1}")
                    continue

                # usar a função local de seleção por overlay (re-query e confirma)
                ok = False
                try:
                    ok = _selecionar_opcao_acao(driver, sel, tipo_fluxo, log=log)
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Erro ao selecionar opção no dropdown #{idx+1}: {e}")

                if ok:
                    return True

                # se não ok, tentar fechar overlay e tentar próximo select
                try:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                except Exception:
                    pass
                try:
                    driver.find_element(By.TAG_NAME, 'body').click()
                except Exception:
                    pass
                time.sleep(0.2)

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro iterando selects de ação: {e}")
                continue

        # fallback: se POSITIVO, tentar DESBLOQUEIO
        if tipo_fluxo == 'POSITIVO':
            if log:
                print('[SISBAJUD] ℹ️ Fallback POSITIVO -> tentar DESBLOQUEIO')
            for tentativa in range(2):
                try:
                    # tentar abrir novamente o primeiro select
                    sel = None
                    try:
                        sel = driver.find_element(By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao'], mat-select")
                    except Exception:
                        sel = None

                    if not sel:
                        break

                    try:
                        sel.click()
                    except Exception:
                        try:
                            driver.execute_script('arguments[0].click();', sel)
                        except Exception:
                            pass

                    ok2 = _selecionar_opcao_acao(driver, sel, 'DESBLOQUEIO', log=log)
                    if ok2:
                        return True
                except Exception:
                    time.sleep(0.2)

        if log:
            print('[SISBAJUD] ❌ Não foi possível aplicar ação por fluxo')
        return False

    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro aplicar_acao_por_fluxo: {e}")
        return False

def cadastrar_reu_sisbajud(driver, reu, config_sisbajud):
    """
    Implementa a função cadastro() do código otimizado
    Com tratamento de CNPJ raiz e delays específicos
    """
    try:
        # Aguardar campo CPF/CNPJ
        try:
            elemento_cpf = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="CPF/CNPJ do réu/executado"], input[placeholder="CPF/CNPJ da pessoa pesquisada"]'))
            )
        except Exception as e:
            print(f'[SISBAJUD] ❌ Campo CPF/CNPJ não encontrado: {e}')
            return False
        
        try:
            botao_adicionar = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[class*="btn-adicionar"]'))
            )
        except:
            botao_adicionar = None
        
        if not elemento_cpf or not botao_adicionar:
            return False
        
        elemento_cpf.focus()
        
        # Lógica CNPJ raiz do código otimizado
        documento = reu.get('cpfcnpj', '').replace('.', '').replace('-', '').replace('/', '')
        
        # Se é CNPJ (>14 chars) e config permite CNPJ raiz
        if len(documento) > 14 and config_sisbajud.get('cnpjRaiz', '').lower() == 'sim':
            documento = documento[:10]  # Primeiros 10 dígitos
        
        print(f'[SISBAJUD]             Preenchendo: {documento}')
        
        elemento_cpf.clear()
        elemento_cpf.send_keys(documento)
        trigger_event(elemento_cpf, 'input')
        
        # Delay específico do código otimizado
        time.sleep(0.8)
        
        # Verificar se precisa corrigir (lógica complexa do código otimizado)
        valor_atual = elemento_cpf.get_attribute('value')
        if (len(documento) < 15 and len(valor_atual) == 10) or len(valor_atual) != len(documento):
            # Corrigir valor
            elemento_cpf.clear()
            elemento_cpf.send_keys(documento)
            trigger_event(elemento_cpf, 'input')
        
        # Aguardar estabilidade e clicar
        time.sleep(0.8)
        trigger_event(botao_adicionar, 'click')
        
        return True
        
    except Exception as e:
        print(f'[SISBAJUD] Erro ao cadastrar réu: {e}')
        return False

def configurar_monitoring_erros(driver):
    """
    Configura monitoring de erros similar ao MutationObserver do código otimizado
    """
    # Em Python/Selenium, podemos usar polling periódico ou aguardar elementos específicos
    # Esta função seria chamada para configurar tratamento de erros conhecido
    pass

def trigger_event(elemento, event_type):
    """Simula triggerEvent do gigs.js"""
    driver = elemento.parent
    driver.execute_script(f"arguments[0].dispatchEvent(new Event('{event_type}', {{bubbles: true}}));", elemento)


def aguardar_elemento(driver, seletor, texto=None, timeout=10):
    """Aguarda elemento aparecer (equivalente ao esperarElemento do gigs.js)"""
    try:
        if texto:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{texto}')]"))
            )
        else:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
            )
    except Exception:
        return None


def aguardar_e_clicar(driver, seletor, texto=None, timeout=10):
    """Aguarda e clica em elemento (equivalente ao clicarBotao do gigs.js)"""
    elemento = aguardar_elemento(driver, seletor, texto, timeout)
    if elemento:
        try:
            elemento.click()
            return True
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", elemento)
                return True
            except Exception:
                return False
    return False


def aguardar_opcoes_aparecerem(driver, seletor_opcoes, intervalo_ms=100, max_tentativas=50):
    """Polling simples para aguardar opções de overlay aparecerem e retornar a lista de elementos."""
    tentativas = 0
    while tentativas < max_tentativas:
        try:
            opcoes = driver.find_elements(By.CSS_SELECTOR, seletor_opcoes)
            if opcoes:
                return opcoes
        except Exception:
            pass
        tentativas += 1
        time.sleep(intervalo_ms / 1000.0)
    return []


def escolher_opcao_sisbajud(driver, seletor, valor):
    """Seleciona uma opção de autocomplete/select baseado em texto parcial - robusto para SISBAJUD."""
    try:
        # encontrar o campo e clicar
        for _ in range(8):
            try:
                campo = driver.find_element(By.CSS_SELECTOR, seletor)
                break
            except Exception:
                time.sleep(0.25)
        else:
            return False

        try:
            campo.click()
        except Exception:
            try:
                driver.execute_script('arguments[0].click();', campo)
            except Exception:
                pass

        time.sleep(0.4)

        # polling por opções
        opcoes = []
        for tentativa in range(40):
            try:
                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"], option, span.mat-option-text')
                if opcoes:
                    break
            except Exception:
                pass
            time.sleep(0.1)

        # procurar correspondência
        for opc in opcoes:
            try:
                if valor.lower() in opc.text.lower():
                    try:
                        opc.click()
                        return True
                    except Exception:
                        try:
                            driver.execute_script('arguments[0].click();', opc)
                            return True
                        except Exception:
                            continue
            except Exception:
                continue

        return False
    except Exception:
        return False

def criar_span_valor(driver, valor_formatado, data_divida):
    """Cria span clicável para valor como no gigs.js"""
    # Implementação específica para criar elemento visual do valor
    pass

def preencher_valor_automatico(driver, valor):
    """Preenche valor automaticamente se configurado"""
    try:
        elemento_valor = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="Valor aplicado a todos"]')))
    except:
        elemento_valor = None
    if elemento_valor:
        elemento_valor.clear()
        elemento_valor.send_keys(valor)

def extrair_protocolo(driver):
    """Extrai protocolo da minuta salva"""
    try:
        protocolo_elemento = driver.find_element(By.CSS_SELECTOR, 
            '.protocolo-minuta, .protocolo, [id*="protocolo"]')
        return protocolo_elemento.text.strip()
    except:
        return None

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

def driver_sisbajud():
    """Cria o driver para SISBAJUD usando a fábrica definida em driver_config."""
    try:
        # A fábrica criar_driver_sisb devolve um WebDriver configurado para SISBAJUD
        driver = criar_driver_sisb()
        return driver
    except Exception as e:
        print(f"[PREAMBULO] ❌ Erro ao criar driver SISBAJUD via driver_config: {e}")
        return None

def aguardar_sisbajud_ready(driver, timeout=30):
    """
    Aguarda condição mínima de prontidão da aplicação SISBAJUD após login.
    Verifica document.readyState == 'complete' e procura por alguns seletores comuns.
    Retorna True se encontrou um dos seletores antes do timeout, caso contrário False.
    """
    import time
    end = time.time() + timeout
    candidate_selectors = [
        'span[id^="maisPje_menuKaizen_itemmenu"]',
        'nav',
        '.mat-toolbar',
        'sisbajud-cadastro-minuta',
        'body'
    ]
    while time.time() < end:
        try:
            ready = False
            try:
                ready = driver.execute_script('return document.readyState') == 'complete'
            except Exception:
                # driver may not be ready to execute script yet
                ready = False

            if ready:
                for sel in candidate_selectors:
                    try:
                        elems = driver.find_elements(By.CSS_SELECTOR, sel)
                        if elems:
                            print(f'[SISBAJUD] Página pronta (selector encontrado: {sel})')
                            return True
                    except Exception:
                        continue
            # se não pronto, aguarda um pouco
        except Exception:
            pass
        time.sleep(0.5)
    print('[SISBAJUD] ⚠️ Timeout aguardando página ficar pronta após login')
    return False

def login_automatico_sisbajud(driver):
    """
    Login automatizado humanizado no SISBAJUD com simulação de comportamento humano
    """
    try:
        print('[SISBAJUD][LOGIN] Navegando para SISBAJUD...')
        driver.get('https://sisbajud.cnj.jus.br/')
        
        # Aguardar carregamento com variação humana
        time.sleep(random.uniform(2.5, 4.0))
        
        # Verificar se já está logado
        current_url = driver.current_url
        if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms']):
            print('[SISBAJUD][LOGIN] ✅ Já está logado!')
            return True
        
        # 1. Clicar no campo de login e digitar CPF como humano
        print('[SISBAJUD][LOGIN] 1. Clicando no campo de login e digitando CPF como humano...')
        try:
            username_field = driver.find_element(By.ID, "username")
            simular_movimento_humano(driver, username_field)
            username_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            cpf = "30069277885"
            for i, char in enumerate(cpf):
                # Simular erro de digitação (5% chance)
                if random.random() < 0.05:
                    erro_char = str(random.randint(0,9))
                    username_field.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    username_field.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                username_field.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
            print('[SISBAJUD][LOGIN] ✅ CPF digitado como humano')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao digitar CPF: {e}')
            return False

        # 2. Clicar no campo de senha e digitar senha como humano
        print('[SISBAJUD][LOGIN] 2. Clicando no campo de senha e digitando senha como humano...')
        try:
            password_field = driver.find_element(By.ID, "password")
            simular_movimento_humano(driver, password_field)
            password_field.click()
            time.sleep(random.uniform(0.3, 0.7))
            senha = "Fl@quinho182"
            for i, char in enumerate(senha):
                # Simular erro de digitação (5% chance)
                if random.random() < 0.05:
                    erro_char = chr(random.randint(33,126))
                    password_field.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    password_field.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                password_field.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))
            print('[SISBAJUD][LOGIN] ✅ Senha digitada como humano')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao digitar senha: {e}')
            return False
            
        # 3. Clicar no botão de login "Entrar"
        print('[SISBAJUD][LOGIN] 3. Clicando no botão de login "Entrar"...')
        try:
            btn_entrar = driver.find_element(By.ID, "kc-login")
            simular_movimento_humano(driver, btn_entrar)
            btn_entrar.click()
            print('[SISBAJUD][LOGIN] ✅ Botão "Entrar" clicado')
        except Exception as e:
            print(f'[SISBAJUD][LOGIN] ❌ Erro ao clicar no botão de login: {e}')
            return False
            
        # Aguardar redirecionamento
        time.sleep(random.uniform(3.0, 5.0))
        
        # Verificar se login foi bem sucedido
        current_url = driver.current_url
        if 'sisbajud.cnj.jus.br' in current_url:
            print('[SISBAJUD][LOGIN] ✅ Login realizado com sucesso!')
            # Maximizar a janela imediatamente após o login para garantir visibilidade dos elementos
            try:
                driver.maximize_window()
                print('[SISBAJUD][LOGIN] ✅ Janela maximizada após login automático')
            except Exception:
                pass
            return True
        else:
            print('[SISBAJUD][LOGIN] ❌ Falha no login - URL não redirecionou corretamente')
            return False
            
    except Exception as e:
        print(f'[SISBAJUD][LOGIN] ❌ Erro durante login: {e}')
        traceback.print_exc()
        return False

def login_manual_sisbajud(driver, aguardar_url_final=True):
    """
    Login manual para SISBAJUD: navega até a página de login e aguarda o usuário completar o login.
    """
    try:
        print('[SISBAJUD][LOGIN_MANUAL] Navegando para SISBAJUD e aguardando login manual...')
        driver.get('https://sisbajud.cnj.jus.br/')
        # Aguarda o usuário completar o login
        target_indicator = 'sisbajud.cnj.jus.br'
        import time
        timeout = 300  # 5 minutos para login manual
        inicio = time.time()
        while True:
            try:
                if target_indicator in driver.current_url.lower():
                    print('[SISBAJUD][LOGIN_MANUAL] Login detectado manualmente (URL mudou).')
                    # Tentar salvar cookies via driver_config helper para persistência
                    try:
                        from driver_config import salvar_cookies_sessao, SALVAR_COOKIES_AUTOMATICO
                        if SALVAR_COOKIES_AUTOMATICO:
                            try:
                                salvar_cookies_sessao(driver, info_extra='login_manual_sisbajud')
                                print('[SISBAJUD][LOGIN_MANUAL] Cookies salvos após login manual SISBAJUD')
                            except Exception as e:
                                print(f"[SISBAJUD][LOGIN_MANUAL] Falha ao salvar cookies: {e}")
                    except Exception:
                        # driver_config pode não estar disponível neste contexto
                        pass
                    return True
            except Exception:
                pass
            if not aguardar_url_final:
                return False
            if time.time() - inicio > timeout:
                print('[SISBAJUD][LOGIN_MANUAL] Timeout aguardando login manual.')
                return False
            time.sleep(1)
    except Exception as e:
        print(f'[SISBAJUD][LOGIN_MANUAL] Erro durante login manual: {e}')
        return False

# Variável global para armazenar dados do processo
processo_dados_extraidos = None

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

def iniciar_sisbajud(driver_pje=None):
    """
    Função unificada de inicialização do SISBAJUD:
    1. Extrai dados do processo PJe
    2. Cria driver Firefox SISBAJUD
    3. Realiza login automatizado
    4. Retorna o driver SISBAJUD logado
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
                # Corrigir para usar o campo correto do dadosatuais.json
                numero_lista = processo_dados_extraidos.get("numero", [])
                numero_display = numero_lista[0] if numero_lista else "N/A"
                print(f'[SISBAJUD] ✅ Dados extraídos: {numero_display}')
                salvar_dados_processo_temp()
            else:
                print('[SISBAJUD] ⚠️ Não foi possível extrair dados do processo')
        else:
            print('[SISBAJUD] ⚠️ Driver PJE não fornecido, pulando extração de dados')
        
        # 2. Criar driver Firefox SISBAJUD
        print('[SISBAJUD] Criando driver Firefox SISBAJUD...')
        driver = driver_sisbajud()
        # Tentativa: recarregar cookies específicos do SISBAJUD (implementado em bacen.py)
        cookie_restored = False
        try:
            from bacen import carregar_cookies_sisbajud
            try:
                if carregar_cookies_sisbajud(driver):
                    print('[SISBAJUD] ✅ Cookies SISBAJUD carregados com sucesso; pulando etapa de login.')
                    cookie_restored = True
            except Exception:
                # falha ao carregar cookies SISBAJUD - continuar para o fluxo de login
                cookie_restored = False
        except Exception:
            # módulo bacen pode não existir em todos os contextos; ignorar
            cookie_restored = False
        
        if not driver:
            print('[SISBAJUD] ❌ Falha ao criar driver')
            return None
        
        # Realizar login: priorizar cookies SISBAJUD, depois tentar login automático SISBAJUD
        try:
            from driver_config import criar_driver_sisb, criar_driver_sisb_notebook, salvar_cookies_sessao, SALVAR_COOKIES_AUTOMATICO
        except Exception:
            criar_driver_sisb = None
            criar_driver_sisb_notebook = None
            salvar_cookies_sessao = None
            SALVAR_COOKIES_AUTOMATICO = False

        try:
            from bacen import carregar_cookies_sisbajud
        except Exception:
            carregar_cookies_sisbajud = None

        # Se os cookies SISBAJUD foram restaurados anteriormente, já temos sessão válida
        login_ok = False
        if cookie_restored:
            login_ok = True

        # Tentar carregar cookies específicos do SISBAJUD (formato do módulo bacen)
        if not login_ok and carregar_cookies_sisbajud:
            try:
                if carregar_cookies_sisbajud(driver):
                    print('[SISBAJUD] ✅ Cookies SISBAJUD (bacen) carregados com sucesso; pulando etapa de login.')
                    login_ok = True
            except Exception:
                pass

        # Se ainda não temos sessão, tentar login automático SISBAJUD (função local)
        if not login_ok:
            try:
                print('[SISBAJUD] Tentando login automático SISBAJUD (função interna)...')
                if login_automatico_sisbajud(driver):
                    login_ok = True
                    # Salvar cookies gerados pelo login automático, se configurado
                    try:
                        if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sessao:
                            salvar_cookies_sessao(driver, info_extra='login_automatico_sisbajud')
                    except Exception:
                        pass
                else:
                    print('[SISBAJUD] Login automático SISBAJUD falhou, seguindo para login manual...')
            except Exception as e:
                print(f'[SISBAJUD] Erro no login automático SISBAJUD: {e}')

        # Se ainda não logado, fallback para login manual SISBAJUD
        if not login_ok:
            try:
                print('[SISBAJUD] Aguardando login MANUAL SISBAJUD...')
                if login_manual_sisbajud(driver):
                    login_ok = True
                    # Salvar cookies após login manual SISBAJUD (se permitido)
                    try:
                        if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sessao:
                            salvar_cookies_sessao(driver, info_extra='login_manual_sisbajud')
                            print('[SISBAJUD] ✅ Cookies SISBAJUD salvos após login manual')
                    except Exception as e:
                        print(f'[SISBAJUD] ⚠️ Falha ao salvar cookies SISBAJUD: {e}')
                else:
                    print('[SISBAJUD] ❌ Login manual SISBAJUD falhou ou expirou')
            except Exception as e:
                print(f'[SISBAJUD] Erro durante login manual SISBAJUD: {e}')

        if not login_ok:
            print('[SISBAJUD] ❌ Não foi possível autenticar no SISBAJUD')
            try:
                driver.quit()
            except Exception:
                pass
            return None

        # Se chegou aqui, o login foi bem-sucedido — agora AGUARDAR explicitamente pela URL /minuta
        minuta_indicator = 'sisbajud.cnj.jus.br/minuta'
        url_timeout = 120
        inicio_url = time.time()
        url_ready = False
        while time.time() - inicio_url < url_timeout:
            try:
                current = driver.current_url.lower()
                if minuta_indicator in current:
                    print('[SISBAJUD] ✅ URL /minuta detectada')
                    url_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not url_ready:
            print('[SISBAJUD] ⚠️ Timeout aguardando a URL https://sisbajud.cnj.jus.br/minuta após login')
            return None

        # Após detectar a URL específica, maximizar a janela e olhar rapidamente se a página está pronta
        try:
            try:
                driver.maximize_window()
                print('[SISBAJUD] ✅ Janela maximizadda após detectar /minuta')
            except Exception as e:
                print(f'[SISBAJUD] ⚠️ Não foi possível maximizar a janela: {e}')

            ready = aguardar_sisbajud_ready(driver, timeout=10)
        except Exception as e:
            print(f"[SISBAJUD] Erro ao aguardar prontidão da página: {e}")
            ready = False

        if not ready:
            print('[SISBAJUD] ⚠️ Página /minuta detectada, mas não ficou totalmente pronta no tempo curto; ainda assim permitindo continuar (manter driver aberto).')
            # Ainda assim retornamos o driver para que as funções possam iniciar quando desejado
            return driver

        print('[SISBAJUD] ✅ Sessão SISBAJUD inicializada com sucesso e página /minuta pronta')
        return driver
# exceção externa para toda inicialização
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao iniciar sessão SISBAJUD: {e}')
        try:
            traceback.print_exc()
        except Exception:
            pass
        return None

# ===================== FUNÇÕES PRINCIPAIS =====================

def carregar_dados_processo():
    """
    Carrega os dados do processo do arquivo dadosatuais.json no projeto
    """
    try:
        project_path = os.path.dirname(os.path.abspath(__file__))
        dados_path = os.path.join(project_path, 'dadosatuais.json')
        
        if not os.path.exists(dados_path):
            print(f'[SISBAJUD] Arquivo de dados não encontrado: {dados_path}')
            return None
        
        with open(dados_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        print('[SISBAJUD] Dados do processo carregados com sucesso')
        return dados
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao carregar dados do processo: {e}')
        return None

def minuta_bloqueio(driver_pje=None, dados_processo=None, driver_sisbajud=None):
    """
    Cria minuta de bloqueio no SISBAJUD
    
    Fluxo:
    1. Se driver_sisbajud não fornecido, chama iniciar_sisbajud(driver_pje) que:
       - Extrai dados do processo PJe (se driver_pje fornecido)
       - Cria driver SISBAJUD e faz login
       - Retorna driver SISBAJUD já logado
    2. Se driver_sisbajud fornecido, usa diretamente
    3. Usa o driver SISBAJUD para preencher a minuta
    
    Args:
        driver_pje: WebDriver do PJe para extração de dados (opcional)
        dados_processo: Dados do processo em formato de dicionário (opcional)
        driver_sisbajud: WebDriver do SISBAJUD já logado (opcional)
    
    Returns:
        dict: Dados da minuta criada ou None em caso de falha
    """
    try:
        print('\n[SISBAJUD] INICIANDO MINUTA DE BLOQUEIO')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD (extrai dados, cria driver e faz login) ou usar driver fornecido
        print('[SISBAJUD] 1. Inicializando SISBAJUD...')
        if driver_sisbajud:
            print('[SISBAJUD] Usando driver SISBAJUD fornecido')
        else:
            driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao inicializar SISBAJUD')
            return None
        
        print('[SISBAJUD] ✅ SISBAJUD inicializado e logado com sucesso')
        
        # 2. Carregar dados do processo (se não fornecidos)
        if not dados_processo:
            print('[SISBAJUD] 2. Carregando dados do processo...')
            dados_processo = carregar_dados_processo()
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            driver_sisbajud.quit()
            return None
        
        print('[SISBAJUD] ✅ Dados do processo carregados')
        
        # 3. Navegar para página de cadastro de minuta
        print('[SISBAJUD] 3. Navegando para página de cadastro de minuta...')
        if not driver_sisbajud.current_url.endswith("/minuta/cadastrar"):
            print('[SISBAJUD] Clicando no menu Nova Minuta (sem espera longa)...')
            # tentar encontrar e clicar imediatamente, sem aguardar
            element = None
            try:
                element = driver_sisbajud.find_element(By.CSS_SELECTOR, 'span[id="maisPje_menuKaizen_itemmenu_nova_minuta"] a')
            except Exception:
                element = None

            if element:
                try:
                    element.click()
                    print('[SISBAJUD] ✅ Clique realizado no menu Nova Minuta')
                except Exception:
                    try:
                        driver_sisbajud.execute_script("arguments[0].click();", element)
                        print('[SISBAJUD] ✅ JS click realizado no menu Nova Minuta')
                    except Exception:
                        element = None

            # fallback: tentar disparar clique via querySelector (JS)
            if not element:
                try:
                    driver_sisbajud.execute_script("var el=document.querySelector('span[id=\"maisPje_menuKaizen_itemmenu_nova_minuta\"] a'); if(el){el.click();}")
                    print('[SISBAJUD] ✅ Tentativa de JS click via querySelector executada')
                except Exception:
                    pass

            # se ainda não estivermos na página de cadastro, navegar diretamente (sem esperar)
            time.sleep(0.5)
            if not driver_sisbajud.current_url.endswith("/minuta/cadastrar"):
                try:
                    driver_sisbajud.get("https://sisbajud.cnj.jus.br/sisbajudweb/pages/minuta/cadastrar")
                    print('[SISBAJUD] Navegando diretamente para /minuta/cadastrar')
                except Exception as e:
                    print(f'[SISBAJUD] ❌ Falha ao navegar diretamente para /minuta/cadastrar: {e}')
                    driver_sisbajud.quit()
                    return None

            # dar um pequeno delay para estabilizar elementos, sem esperar longos timeouts
            time.sleep(0.8)
        
        # === SEQUÊNCIA DE AÇÕES IDÊNTICA AO CÓDIGO OTIMIZADO ===
        
        # AÇÃO 1: JUIZ SOLICITANTE
        print('[SISBAJUD] === AÇÃO 1: JUIZ SOLICITANTE ===')
        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        print(f'[SISBAJUD]       |___JUIZ SOLICITANTE: {juiz}')
        
        if juiz:
            # Usar função específica do código otimizado: escolher_opcao_sisbajud
            try:
                seletor = 'input[placeholder*="Juiz"]'
                valor = juiz
                for _ in range(10):
                    try:
                        el = driver_sisbajud.find_element(By.CSS_SELECTOR, seletor)
                        break
                    except Exception:
                        time.sleep(0.5)
                else:
                    print(f'[SISBAJUD][ERRO] Opção "{valor}" não encontrada em {seletor} (elemento não existe)')
                    success = False
                el.click()
                time.sleep(0.5)
                opcoes = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"], option')
                for opc in opcoes:
                    if valor.lower() in opc.text.lower():
                        opc.click()
                        print(f'[SISBAJUD] Opção "{valor}" selecionada em {seletor}')
                        success = True
                        break
                else:
                    print(f'[SISBAJUD][ERRO] Opção "{valor}" não encontrada em {seletor} (nenhuma opção corresponde)')
                    success = False
            except Exception as e:
                print(f'[SISBAJUD][ERRO] Falha ao selecionar opção: {e}')
                success = False
            if not success:
                print('[SISBAJUD] ❌ Falha ao preencher juiz solicitante')
                driver_sisbajud.quit()
                return None
        
        # AÇÃO 2: VARA/JUÍZO - LÓGICA EXATA DO CÓDIGO OTIMIZADO
        print('[SISBAJUD] === AÇÃO 2: VARA/JUÍZO ===')
        vara = dados_processo.get('sisbajud', {}).get('vara', '30006')
        print(f'[SISBAJUD]       |___VARA/JUÍZO: {vara}')
        
        if vara:
            # 1. Focus + click no seletor exato
            try:
                elemento_vara = WebDriverWait(driver_sisbajud, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-select[name*="varaJuizoSelect"]')))
            except:
                elemento_vara = None
            if not elemento_vara:
                print('[SISBAJUD] ❌ Elemento vara não encontrado')
                driver_sisbajud.quit()
                return None
            
            elemento_vara.focus()
            elemento_vara.click()
            
            # 2. Aguardar opções aparecerem com polling como código otimizado
            opcoes = []
            for tentativa in range(50):
                opcoes = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
                if opcoes:
                    break
                time.sleep(0.1)
            
            if opcoes:
                # 3. Buscar e clicar na opção correta
                for opcao in opcoes:
                    if vara in opcao.text:
                        opcao.click()
                        print(f'[SISBAJUD] ✅ Vara selecionada: {opcao.text}')
                        break
        
        # AÇÃO 3: NÚMERO DO PROCESSO
        print('[SISBAJUD] === AÇÃO 3: NÚMERO DO PROCESSO ===')
        numero_lista = dados_processo.get('numero', [])
        numero_processo = numero_lista[0] if numero_lista else ''
        print(f'[SISBAJUD]       |___NUMERO PROCESSO: {numero_processo}')
        
        if numero_processo:
            try:
                elemento_numero = WebDriverWait(driver_sisbajud, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Número do Processo"]')))
            except:
                elemento_numero = None
            if elemento_numero:
                elemento_numero.focus()
                elemento_numero.clear()
                elemento_numero.send_keys(numero_processo)
                trigger_event(elemento_numero, 'input')  # Simular triggerEvent do código otimizado
                elemento_numero.blur()
        
        # AÇÃO 4: TIPO DE AÇÃO
        print('[SISBAJUD] === AÇÃO 4: TIPO AÇÃO ===')
        print('[SISBAJUD]       |___TIPO AÇÃO: Ação Trabalhista')
        
        try:
            elemento_acao = WebDriverWait(driver_sisbajud, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-select[name*="acao"]')))
        except:
            elemento_acao = None
        if elemento_acao:
            elemento_acao.focus()
            elemento_acao.click()
            
            # Aguardar e selecionar "Ação Trabalhista"
            opcoes = []
            for tentativa in range(50):
                opcoes = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
                if opcoes:
                    break
                time.sleep(0.1)
            for opcao in opcoes:
                if 'Ação Trabalhista' in opcao.text:
                    opcao.click()
                    break
        
        # AÇÃO 5: CPF/CNPJ DO AUTOR
        print('[SISBAJUD] === AÇÃO 5: CPF/CNPJ AUTOR ===')
        
        # Lógica do código otimizado para determinar autor
        cpf_cnpj_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            cpf_cnpj_autor = dados_processo['autor'][0].get('cpfcnpj', '')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            cpf_cnpj_autor = dados_processo['reu'][0].get('cpfcnpj', '')
        
        # Limpar formatação como no código otimizado
        cpf_cnpj_limpo = cpf_cnpj_autor.replace('.', '').replace('-', '').replace('/', '')
        print(f'[SISBAJUD]       |___CPF/CNPJ AUTOR: {cpf_cnpj_limpo}')
        
        elemento_cpf = aguardar_elemento(driver_sisbajud, 'input[placeholder*="CPF"]')
        try:
            elemento_cpf = WebDriverWait(driver_sisbajud, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="CPF"]')))
        except:
            elemento_cpf = None
        if elemento_cpf:
            elemento_cpf.focus()
            
            # Delay específico do código otimizado antes do preenchimento
            time.sleep(0.25)
            
            elemento_cpf.clear()
            elemento_cpf.send_keys(cpf_cnpj_limpo)
            trigger_event(elemento_cpf, 'input')
            elemento_cpf.blur()
        
        # AÇÃO 6: NOME DO AUTOR
        print('[SISBAJUD] === AÇÃO 6: NOME DO AUTOR ===')
        
        # Mesma lógica do CPF para o nome
        nome_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            nome_autor = dados_processo['autor'][0].get('nome', '')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            nome_autor = dados_processo['reu'][0].get('nome', '')
        
        print(f'[SISBAJUD]       |___NOME AUTOR: {nome_autor}')
        
        try:
            elemento_nome = WebDriverWait(driver_sisbajud, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Nome do autor/exequente da ação"]')))
        except:
            elemento_nome = None
        if elemento_nome:
            elemento_nome.focus()
            
            # Delay específico do código otimizado
            time.sleep(0.25)
            
            elemento_nome.clear()
            elemento_nome.send_keys(nome_autor)
            trigger_event(elemento_nome, 'input')
            elemento_nome.blur()
        
        # AÇÃO 7: TEIMOSINHA (REPETIÇÃO DA ORDEM)
        print('[SISBAJUD] === AÇÃO 7: TEIMOSINHA ===')
        print('[SISBAJUD]       |___TEIMOSINHA: Repetir a ordem')
        
        # Buscar radio buttons exato como código otimizado
        radios = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
        for radio in radios:
            if 'Repetir a ordem' in radio.text:
                label = radio.find_element(By.CSS_SELECTOR, 'label')
                label.click()
                print('[SISBAJUD] ✅ Repetir a ordem selecionado')
                break
        
        # AÇÃO 8: CALENDÁRIO - LÓGICA COMPLEXA DO CÓDIGO OTIMIZADO
        print('[SISBAJUD] === AÇÃO 8: CALENDÁRIO ===')
        
        # Calcular data como no código otimizado: hoje + 30 dias + 2 extras
        numdias = 30  # Equivalente ao extrairNumeros(preferencias.sisbajud.teimosinha)
        hoje = datetime.now()
        data_fim = hoje + timedelta(days=numdias + 2)
        
        ano = data_fim.year
        mes_d = data_fim.month - 1  # Month index (0-11 como no JS)
        dia_d = data_fim.day
        
        print(f'[SISBAJUD]       |___ABRE CALENDARIO: {numdias} dias -> {data_fim.strftime("%d/%m/%Y")}')
        
        # 1. Abrir calendário
        if not aguardar_e_clicar(driver_sisbajud, 'button[aria-label="Open calendar"]'):
            print('[SISBAJUD] ❌ Falha ao abrir calendário')
            driver_sisbajud.quit()
            return None
            
        # 2. Abrir seleção mês/ano
        if not aguardar_e_clicar(driver_sisbajud, 'mat-calendar button[aria-label="Choose month and year"]'):
            print('[SISBAJUD] ❌ Falha ao abrir seleção mês/ano')
            driver_sisbajud.quit()
            return None
            
        # 3. Selecionar ano
        if not aguardar_e_clicar(driver_sisbajud, f'mat-calendar td[aria-label="{ano}"]'):
            print('[SISBAJUD] ❌ Falha ao selecionar ano')
            driver_sisbajud.quit()
            return None
        
        # 4. Lógica de encontrar mês disponível (como código otimizado)
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        
        mes_encontrado = False
        mes_atual = mes_d
        
        while mes_atual >= 0:
            mes_str = f"{meses[mes_atual]} de {ano}"
            print(f'[SISBAJUD] ***Tentando mês: {mes_str}')
            
            try:
                elemento_mes = aguardar_elemento(driver_sisbajud, f'mat-calendar td[aria-label="{mes_str}"]', timeout=1)
                if elemento_mes and not elemento_mes.get_attribute('aria-disabled'):
                    elemento_mes.click()
                    mes_encontrado = True
                    break
                else:
                    print(f'[SISBAJUD] ***Mês {mes_str} desabilitado, alterando dia para 31')
                    dia_d = 31
            except:
                print(f'[SISBAJUD] ***Mês {mes_str} não encontrado')
                dia_d = 31
            
            mes_atual -= 1
        
        if not mes_encontrado:
            print('[SISBAJUD] ❌ Nenhum mês disponível')
            driver_sisbajud.quit()
            return None
        
        # 5. Encontrar primeiro dia disponível (lógica código otimizado)
        mes_final_str = f"{meses[mes_atual]} de {ano}"
        dia_encontrado = False
        
        while dia_d > 0:
            dia_str = f"{dia_d} de {mes_final_str}"
            print(f'[SISBAJUD] ***Tentando teimosinha do dia {dia_d}')
            
            try:
                elemento_dia = aguardar_elemento(driver_sisbajud, f'mat-calendar td[aria-label="{dia_str}"]', timeout=1)
                if elemento_dia and not elemento_dia.get_attribute('aria-disabled'):
                    elemento_dia.click()
                    dia_encontrado = True
                    break
            except:
                pass
            
            dia_d -= 1
        
        if not dia_encontrado:
            print('[SISBAJUD] ❌ Nenhum dia disponível')
            driver_sisbajud.quit()
            return None
        
        data_limite_str = datetime(ano, mes_atual + 1, dia_d).strftime('%d/%m/%Y')
        print(f'[SISBAJUD] ✅ Data selecionada: {data_limite_str}')
        
        # AÇÃO 10: INSERÇÃO DOS RÉUS (pula acao9 que é só setup)
        print('[SISBAJUD] === AÇÃO 10: INSERÇÃO DOS RÉUS ===')
        
        reus = dados_processo.get('reu', [])
        if not reus:
            print('[SISBAJUD] ❌ Nenhum réu encontrado')
            driver_sisbajud.quit()
            return None
        
        print(f'[SISBAJUD]       |___INSERÇÃO DOS RÉUS: {len(reus)} réus')
        
        # Iniciar processo de cadastro com monitoring como código otimizado
        configurar_monitoring_erros(driver_sisbajud)
        
        for contador, reu in enumerate(reus):
            print(f'[SISBAJUD]       |___{contador + 1}: {reu.get("nome", "")}'
                  f' ({reu.get("cpfcnpj", "")})')
            
            # Função cadastro equivalente
            sucesso = cadastrar_reu_sisbajud(driver_sisbajud, reu, dados_processo.get('sisbajud', {}))
            if not sucesso:
                print('[SISBAJUD] ❌ Falha ao cadastrar réu')
                driver_sisbajud.quit()
                return None
        
        # AÇÃO 11: VALOR
        print('[SISBAJUD] === AÇÃO 11: VALOR ===')
        
        if dados_processo.get('divida', {}).get('valor'):
            valor_formatado = formatar_moeda_brasileira(dados_processo['divida']['valor'])
            print(f'[SISBAJUD]       |___VALOR: {valor_formatado}')
            
            # Criar span clicável como no código otimizado
            criar_span_valor(driver_sisbajud, valor_formatado, dados_processo.get('divida', {}).get('data'))
            
            # Auto-preencher se configurado
            if dados_processo.get('sisbajud', {}).get('preencherValor', '').lower() == 'sim':
                preencher_valor_automatico(driver_sisbajud, valor_formatado)
        
        # AÇÃO 12: CONTA-SALÁRIO
        print('[SISBAJUD] === AÇÃO 12: CONTA-SALÁRIO ===')
        
        if dados_processo.get('sisbajud', {}).get('contasalario', '').lower() == 'sim':
            print('[SISBAJUD]       |___CONTA-SALÁRIO: Ativando toggles')
            
            toggles = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-slide-toggle label')
            for toggle in toggles:
                toggle.click()
        
        # AÇÃO 13: SALVAR E PROTOCOLAR
        print('[SISBAJUD] === AÇÃO 13: SALVAR E PROTOCOLAR ===')
        
        if dados_processo.get('sisbajud', {}).get('salvarEprotocolar', '').lower() == 'sim':
            print('[SISBAJUD]       |___SALVAR E PROTOCOLAR')
            
            # 1. Salvar
            btn_salvar = aguardar_elemento(driver_sisbajud, 'sisbajud-cadastro-minuta button', texto='Salvar')
            if btn_salvar:
                btn_salvar.click()
                
                # 2. Aguardar mensagem
                mensagem = aguardar_elemento(driver_sisbajud, 'SISBAJUD-SNACK-MESSENGER')
                if mensagem and 'incluída com sucesso' in mensagem.text:
                    # 3. Protocolar
                    btn_protocolar = aguardar_elemento(driver_sisbajud, 'sisbajud-detalhamento-minuta button', texto='Protocolar')
                    if btn_protocolar:
                        time.sleep(1.0)  # Sleep do código otimizado
                        btn_protocolar.click()
        
        print('[SISBAJUD] ✅ MINUTA CRIADA COM SUCESSO')
        
        # Extrair dados finais
        protocolo = extrair_protocolo(driver_sisbajud)
        
        driver_sisbajud.quit()
        
        return {
            'status': 'sucesso',
            'dados_minuta': {
                'protocolo': protocolo,
                'tipo': 'bloqueio',
                'repeticao': 'sim',
                'data_limite': data_limite_str,
                'quantidade_reus': len(reus)
            }
        }
        
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha na minuta de bloqueio: {e}')
        traceback.print_exc()
        if 'driver_sisbajud' in locals():
            driver_sisbajud.quit()
        return None

def minuta_endereco(driver_pje=None, dados_processo=None):
    """
    Cria minuta de endereço no SISBAJUD baseado na função preenchercamposSisbajud de 0c.py
    Sem modal de executados, sempre preenchendo todos, CNPJ raiz
    """
    try:
        print('\n[SISBAJUD] INICIANDO MINUTA DE ENDEREÇO')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao inicializar SISBAJUD')
            return None
        
        # 2. Carregar dados do processo do arquivo
        if not dados_processo:
            dados_processo = carregar_dados_processo()
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            driver_sisbajud.quit()
            return None
        
        # 3. Navegar para a página de cadastro de minuta se não estiver lá
        if not driver_sisbajud.current_url.endswith("/minuta/cadastrar"):
            print('[SISBAJUD] Navegando para página de cadastro de minuta...')
            driver_sisbajud.get("https://sisbajud.cnj.jus.br/sisbajudweb/pages/minuta/cadastrar")
            time.sleep(3)
        
        # 4. Selecionar tipo de minuta: ENDEREÇO
        print('[SISBAJUD] Selecionando tipo de minuta: Endereço...')
        
        # 4.1. Clicar no radio button "Requisição de informações"
        print('[SISBAJUD] Selecionando "Requisição de informações"...')
        # Usando função auxiliar otimizada
        if not aguardar_e_clicar(driver_sisbajud, '//input[@type="radio" and @value="2"]'):
            print('[SISBAJUD] ❌ Falha ao selecionar "Requisição de informações"')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 4.2. Marcar checkbox "Endereços"
        print('[SISBAJUD] Marcando checkbox "Endereços"...')
        # Usando função auxiliar otimizada
        if not aguardar_e_clicar(driver_sisbajud, '//input[@type="checkbox" and following-sibling::*//span[contains(text(),"Endereços")]]'):
            print('[SISBAJUD] ❌ Falha ao marcar checkbox "Endereços"')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 4.3. Desmarcar opção "Incluir dados sobre contas" (se existir)
        print('[SISBAJUD] Desmarcando "Incluir dados sobre contas"...')
        try:
            # Mesmo seletor de 0c.py
            radios = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
            for radio in radios:
                if 'Não' in radio.text:
                    radio.click()
                    print('[SISBAJUD] ✅ "Incluir dados sobre contas" desmarcado')
                    break
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao desmarcar "Incluir dados sobre contas": {e}')
        
        time.sleep(1)
        
        # 5. Preencher campos seguindo a lógica de 0c.py
        
        # 5.1. JUIZ SOLICITANTE
        print('[SISBAJUD] Preenchendo juiz solicitante...')
        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        
        # Usando função auxiliar otimizada
        if not escolher_opcao_sisbajud(driver_sisbajud, 'input[placeholder*="Juiz"]', juiz):
            print('[SISBAJUD] ❌ Falha ao preencher juiz solicitante')
            driver_sisbajud.quit()
            return None
        
        time.sleep(0.7)
        # Selecionar opção correta no dropdown
        try:
            opcoes_juiz = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'span.mat-option-text')
            for opcao in opcoes_juiz:
                if 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA' in opcao.text.upper():
                    opcao.click()
                    print('[SISBAJUD] ✅ Juiz selecionado: OTAVIO AUGUSTO MACHADO DE OLIVEIRA')
                    break
            else:
                print('[SISBAJUD] ⚠️ Opção de juiz não encontrada, prosseguindo...')
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}')
        time.sleep(1)
        
        # 5.2. VARA/JUÍZO
        print('[SISBAJUD] Preenchendo vara/juízo...')
        vara = dados_processo.get('sisbajud', {}).get('vara', '30006')
        
        if vara:
            # Usando função auxiliar otimizada
            if not aguardar_e_clicar(driver_sisbajud, 'mat-select[name*="varaJuizoSelect"]'):
                print('[SISBAJUD] ❌ Falha ao clicar no campo de vara')
                driver_sisbajud.quit()
                return None
            
            time.sleep(1)
            
            # Selecionar a opção correta
            try:
                opcoes_vara = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
                for opcao in opcoes_vara:
                    if vara in opcao.text:
                        opcao.click()
                        print(f'[SISBAJUD] ✅ Vara selecionada: {opcao.text}')
                        break
            except Exception as e:
                print(f'[SISBAJUD] ⚠️ Erro ao selecionar vara: {e}')
        
        time.sleep(1)
        
        # 5.3. NÚMERO DO PROCESSO
        print('[SISBAJUD] Preenchendo número do processo...')
        # Número está em array no dadosatuais.json
        numero_lista = dados_processo.get('numero', [])
        numero_processo = numero_lista[0] if numero_lista else ''
        
        if not numero_processo:
            print('[SISBAJUD] ❌ Número do processo não encontrado nos dados')
            driver_sisbajud.quit()
            return None
        
        print(f'[SISBAJUD] Número do processo: {numero_processo}')
        
        # Usando função auxiliar otimizada
        elemento_numero = aguardar_elemento(driver_sisbajud, 'input[placeholder="Número do Processo"]')
        if elemento_numero:
            elemento_numero.focus()
            elemento_numero.clear()
            elemento_numero.send_keys(numero_processo)
            trigger_event(elemento_numero, 'input')
            elemento_numero.blur()
        else:
            print('[SISBAJUD] ❌ Falha ao preencher número do processo')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 5.4. TIPO DE AÇÃO
        print('[SISBAJUD] Selecionando tipo de ação...')
        # Usando função auxiliar otimizada
        if not aguardar_e_clicar(driver_sisbajud, 'mat-select[name*="acao"]'):
            print('[SISBAJUD] ❌ Falha ao clicar no campo de tipo de ação')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # Selecionar "Ação Trabalhista"
        try:
            opcoes_acao = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
            for opcao in opcoes_acao:
                if 'Ação Trabalhista' in opcao.text:
                    opcao.click()
                    print('[SISBAJUD] ✅ Tipo de ação selecionado: Ação Trabalhista')
                    break
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao selecionar tipo de ação: {e}')
        
        time.sleep(1)
        
        # 5.5. CPF/CNPJ DO AUTOR
        print('[SISBAJUD] Preenchendo CPF/CNPJ do autor...')
        
        # Lógica simplificada: primeiro autor por padrão, se não há autores usa primeiro réu
        cpf_cnpj_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            cpf_cnpj_autor = dados_processo['autor'][0].get('cpfcnpj', '')
            print(f'[SISBAJUD] Usando CPF/CNPJ do primeiro autor: {cpf_cnpj_autor}')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            cpf_cnpj_autor = dados_processo['reu'][0].get('cpfcnpj', '')
            print(f'[SISBAJUD] Usando CPF/CNPJ do primeiro réu: {cpf_cnpj_autor}')
        
        if not cpf_cnpj_autor:
            print('[SISBAJUD] ❌ CPF/CNPJ não encontrado nem em autor nem em réu')
            driver_sisbajud.quit()
            return None
        
        # Remove pontuação do CPF/CNPJ
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj_autor))
        
        # Usando função auxiliar otimizada
        elemento_cpf = aguardar_elemento(driver_sisbajud, 'input[placeholder*="CPF"]')
        if elemento_cpf:
            elemento_cpf.focus()
            elemento_cpf.clear()
            elemento_cpf.send_keys(cpf_cnpj_limpo)
            trigger_event(elemento_cpf, 'input')
            elemento_cpf.blur()
        else:
            print('[SISBAJUD] ❌ Falha ao preencher CPF/CNPJ do autor')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 5.6. NOME DO AUTOR
        print('[SISBAJUD] Preenchendo nome do autor...')
        
        # Usar o mesmo padrão: primeiro autor, senão primeiro réu
        nome_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            nome_autor = dados_processo['autor'][0].get('nome', '')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            nome_autor = dados_processo['reu'][0].get('nome', '')
        
        if not nome_autor:
            print('[SISBAJUD] ❌ Nome do autor não encontrado nos dados')
            driver_sisbajud.quit()
            return None
        
        # Usando função auxiliar otimizada
        elemento_nome = aguardar_elemento(driver_sisbajud, 'input[placeholder="Nome do autor/exequente da ação"]')
        if elemento_nome:
            elemento_nome.focus()
            elemento_nome.clear()
            elemento_nome.send_keys(nome_autor)
            trigger_event(elemento_nome, 'input')
            elemento_nome.blur()
        else:
            print('[SISBAJUD] ❌ Falha ao preencher nome do autor')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 5.7. INSERÇÃO DOS RÉUS (todos, sem modal)
        print('[SISBAJUD] Inserindo todos os réus...')
        reus = dados_processo.get('reu', [])
        
        if not reus:
            print('[SISBAJUD] ❌ Nenhum réu encontrado nos dados')
            driver_sisbajud.quit()
            return None
        
        # Para cada réu, preencher os dados
        for i, reu in enumerate(reus):
            print(f'[SISBAJUD] Adicionando réu {i+1}/{len(reus)}: {reu.get("nome", "N/A")}')
            
            cpf_cnpj_reu = reu.get('cpfcnpj', '')
            if not cpf_cnpj_reu:
                print(f'[SISBAJUD] ⚠️ Réu sem CPF/CNPJ, pulando...')
                continue
            
            # Formatar CPF/CNPJ (CNPJ raiz)
            numerico = ''.join(filter(str.isdigit, str(cpf_cnpj_reu)))
            if len(numerico) == 11:
                tipo_doc_reu = 'CPF'
            elif len(numerico) == 14:
                tipo_doc_reu = 'CNPJ'
            else:
                tipo_doc_reu = 'INDEFINIDO'
            if tipo_doc_reu == 'CPF':
                cpf_numerico = ''.join(filter(str.isdigit, str(cpf_cnpj_reu)))
                if len(cpf_numerico) == 11:
                    cpf_cnpj_formatado_reu = f"{cpf_numerico[:3]}.{cpf_numerico[3:6]}.{cpf_numerico[6:9]}-{cpf_numerico[9:11]}"
                else:
                    cpf_cnpj_formatado_reu = cpf_numerico
            elif tipo_doc_reu == 'CNPJ':
                # CNPJ raiz (8 primeiros dígitos)
                cnpj_numerico = ''.join(filter(str.isdigit, str(cpf_cnpj_reu)))
                if len(cnpj_numerico) == 14:
                    cpf_cnpj_formatado_reu = f"{cnpj_numerico[:2]}.{cnpj_numerico[2:5]}.{cnpj_numerico[5:8]}/{cnpj_numerico[8:12]}-{cnpj_numerico[12:14]}"[:8]
                else:
                    cpf_cnpj_formatado_reu = cnpj_numerico[:8]
            else:
                cpf_cnpj_formatado_reu = cpf_cnpj_reu
            
            # Clicar no botão Adicionar (se não for o primeiro réu)
            if i > 0:
                # Usando função auxiliar otimizada
                try:
                    element = WebDriverWait(driver_sisbajud, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Adicionar"]')))
                    element.click()
                    success = True
                except:
                    success = False
                if not success:
                    print('[SISBAJUD] ❌ Falha ao clicar no botão Adicionar')
                    driver_sisbajud.quit()
                    return None
                
                time.sleep(1)
            
            # Preencher CPF/CNPJ do réu usando função auxiliar otimizada
            try:
                elemento_cpf_reu = WebDriverWait(driver_sisbajud, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="CPF/CNPJ"]')))
            except:
                elemento_cpf_reu = None
            if elemento_cpf_reu:
                elemento_cpf_reu.focus()
                elemento_cpf_reu.clear()
                elemento_cpf_reu.send_keys(cpf_cnpj_formatado_reu)
                trigger_event(elemento_cpf_reu, 'input')
                elemento_cpf_reu.blur()
            else:
                print('[SISBAJUD] ❌ Campo CPF/CNPJ do réu não encontrado')
                driver_sisbajud.quit()
                return None
            
            time.sleep(0.5)
        
        # 7. Salvar minuta
        print('[SISBAJUD] Salvando minuta...')
        # Usando função auxiliar otimizada
        try:
            element = WebDriverWait(driver_sisbajud, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-fab.mat-primary mat-icon.fa-save')))
            element.click()
            success = True
        except:
            success = False
        if not success:
            print('[SISBAJUD] ❌ Falha ao clicar no botão Salvar')
            driver_sisbajud.quit()
            return None
        
        time.sleep(3)
        
        # Verificar se a minuta foi salva com sucesso
        if 'protocolo' in driver_sisbajud.current_url.lower() or 'minuta' in driver_sisbajud.current_url.lower():
            print('[SISBAJUD] ✅ Minuta salva com sucesso!')
            
            # Extrair protocolo se disponível
            try:
                protocolo = extrair_protocolo(driver_sisbajud)
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
                    'tipo': 'endereco',
                    'quantidade_reus': len(reus)
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
                # Ignorar ordens que já foram respondidas com minuta
                try:
                    all_text = ' '.join([c.text for c in cols]).strip()
                    if 'Respondida com minuta' in all_text:
                        if log:
                            print(f"[SISBAJUD] Ignorando ordem {sequencial}: Respondida com minuta")
                        continue
                except Exception:
                    pass
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
        # helper: localizar a linha da ordem na tabela pelo sequencial
        def _recuperar_linha_ordem(sequencial, timeout=5):
            try:
                tabela = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody tr.mat-row')
                for linha in linhas:
                    try:
                        txt = linha.find_element(By.CSS_SELECTOR, 'td[data-label="sequencial"]').text.strip()
                        if str(sequencial) == txt or str(sequencial) in txt:
                            return linha
                    except Exception:
                        continue
            except Exception:
                return None
            return None

        # Abrir menu da ordem
        if log:
            print(f"[SISBAJUD] Abrindo menu da ordem {ordem['sequencial']}")
        
        # Garantir que temos um WebElement válido para a linha; tentar recuperar se estiver ausente
        if not ordem.get('linha_el'):
            ordem['linha_el'] = _recuperar_linha_ordem(ordem.get('sequencial'))

        menu_clicado = False
        for tentativa in range(3):
            try:
                # se elemento estiver None ou obsoleto, tentar recuperar antes de cada tentativa
                if not ordem.get('linha_el'):
                    ordem['linha_el'] = _recuperar_linha_ordem(ordem.get('sequencial'))

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

        # Zoom intentionally disabled: do NOT change page zoom (can break selectors).
        if log:
            print('[SISBAJUD] ℹ️ Zoom adjustment skipped (disabled by configuration)')
        
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
                # Clicar na opção correta do dropdown usando span.mat-option-text
                opcao_juiz = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA')]"))
                )
                opcao_juiz.click()

                if log:
                    print(f"[SISBAJUD] ✅ Juiz selecionado: OTAVIO AUGUSTO MACHADO DE OLIVEIRA")

                # Clicar fora para fechar dropdown
                try:
                    driver.find_element(By.TAG_NAME, "body").click()
                except Exception:
                    pass
                time.sleep(0.5)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}")
            
            # Seleção da ação
            try:
                if log:
                    print("[SISBAJUD] Selecionando ação para DESBLOQUEIO")

                # Localizar dropdown de ações
                dropdown_acao = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao']"))
                )

                # Clicar no dropdown
                dropdown_acao.click()
                time.sleep(0.5)

                # Procurar e clicar na opção "Desbloquear valor"
                opcao_desbloquear = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//mat-option[contains(text(), 'Desbloquear valor')]"))
                )
                opcao_desbloquear.click()

                if log:
                    print("[SISBAJUD] ✅ Ação selecionada: Desbloquear valor")

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
        
        else:  # POSITIVO
            if log:
                print(f"[SISBAJUD] Preenchendo campos para POSITIVO")

            # Selecionar Juiz (robusto: clicar no span.mat-option-text correspondente)
            try:
                juiz_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
                )
                juiz_input.clear()
                juiz_input.send_keys("OTAVIO AUGUSTO")
                time.sleep(0.8)

                # Buscar opções do dropdown e clicar no span correto
                juiz_clicado = False
                try:
                    opcoes_juiz = driver.find_elements(By.CSS_SELECTOR, 'span.mat-option-text')
                except Exception:
                    opcoes_juiz = []

                alvo_completo = 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA'
                alvo_parcial = 'OTAVIO AUGUSTO'
                for opcao in opcoes_juiz:
                    try:
                        texto = (opcao.text or '').strip().upper()
                        if alvo_completo in texto or alvo_parcial in texto:
                            try:
                                opcao.click()
                            except Exception:
                                try:
                                    driver.execute_script('arguments[0].click();', opcao)
                                except Exception:
                                    pass
                            juiz_clicado = True
                            if log:
                                print(f"[SISBAJUD] ✅ Juiz selecionado: '{opcao.text.strip()}' (POSITIVO)")
                            break
                    except StaleElementReferenceException:
                        # elemento obsoleto, tentar próxima opção
                        continue
                    except Exception:
                        continue

                if not juiz_clicado:
                    # tentar reabrir o filtro e buscar novamente rapidamente
                    try:
                        juiz_input.clear()
                        juiz_input.send_keys('OTAVIO AUGUSTO')
                        time.sleep(0.6)
                        opcoes_juiz = driver.find_elements(By.CSS_SELECTOR, 'span.mat-option-text')
                        for opcao in opcoes_juiz:
                            try:
                                texto = (opcao.text or '').strip().upper()
                                if 'OTAVIO' in texto:
                                    try:
                                        opcao.click()
                                    except Exception:
                                        try:
                                            driver.execute_script('arguments[0].click();', opcao)
                                        except Exception:
                                            pass
                                    juiz_clicado = True
                                    if log:
                                        print(f"[SISBAJUD] ⚠️ Fallback: juiz selecionado por 'OTAVIO' -> '{opcao.text.strip()}'")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # Fechar dropdown do juiz (ESC + body click) como garantia
                try:
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                except Exception:
                    pass
                try:
                    driver.find_element(By.TAG_NAME, 'body').click()
                except Exception:
                    pass
                time.sleep(0.4)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz (POSITIVO): {e}")

            # Selecionar ação apropriada para POSITIVO (ex.: Transferir valor)
            try:
                if log:
                    print("[SISBAJUD] Selecionando ação para POSITIVO")

                # tentar localizar mat-selects de ação rapidamente
                try:
                    selects = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-select[formcontrolname='acao']"))
                    )
                except Exception:
                    # fallback para qualquer mat-select visível (sem esperar muito)
                    try:
                        selects = driver.find_elements(By.CSS_SELECTOR, "mat-select")
                    except Exception:
                        selects = []

                if not selects:
                    if log:
                        print('[SISBAJUD] ⚠️ Nenhum mat-select encontrado para ações (POSITIVO)')
                else:
                    total_selects = len(selects)
                    if log:
                        print(f"[SISBAJUD] ℹ️ Encontrados {total_selects} mat-select(s) para ação (POSITIVO)")

                    # prioridade de seleção: tentar transferir antes de desbloquear
                    prioridade = ["transferir valor", "transferir", "transferência", "transferir saldo", "desbloquear valor", "desbloquear"]

                    selecionados = 0
                    # iterar todos os selects e tentar selecionar ação em cada um
                    for idx in range(total_selects):
                        start_time = time.time()
                        try:
                            # re-obter elemento para evitar stale
                            try:
                                sel = driver.find_elements(By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao'], sisbajud-inclusao-desdobramento mat-select, mat-select")[idx]
                            except Exception:
                                sel = selects[idx]

                            sel_outer = ''
                            try:
                                sel_outer = (sel.get_attribute('outerHTML') or '')[:160]
                            except Exception:
                                sel_outer = f'<mat-select idx={idx}>'

                            # abrir dropdown com fallbacks rápidos e contar tentativas (mais agressivo)
                            opened = False
                            open_attempts = 0
                            open_method = None
                            t_open_start = time.time()
                            # reduzir tentativas para 2 e diminuir sleeps para acelerar
                            while not opened and open_attempts < 2:
                                open_attempts += 1
                                try:
                                    trigger = sel.find_element(By.CSS_SELECTOR, '.mat-select-trigger')
                                    try:
                                        trigger.click()
                                        opened = True
                                        open_method = 'trigger.click'
                                    except Exception:
                                        try:
                                            driver.execute_script('arguments[0].click();', trigger)
                                            opened = True
                                            open_method = 'trigger.jsclick'
                                        except Exception:
                                            opened = False
                                except Exception:
                                    try:
                                        sel.click()
                                        opened = True
                                        open_method = 'sel.click'
                                    except Exception:
                                        try:
                                            driver.execute_script('arguments[0].click();', sel)
                                            opened = True
                                            open_method = 'sel.jsclick'
                                        except Exception:
                                            opened = False
                                if not opened:
                                    time.sleep(0.06)
                            t_open_end = time.time()
                            open_time = t_open_end - t_open_start

                            if not opened:
                                if log:
                                    print(f"[SISBAJUD] ⚠️ Falha ao abrir dropdown de ação #{idx+1} (tentativas={open_attempts}) - snippet: {sel_outer}")
                                continue

                            # aguardar painel e coletar opções (re-query) com timing para debug
                            t_panel_start = time.time()
                            try:
                                # reduzir timeout para detectar rapidamente que painel não abriu
                                WebDriverWait(driver, 0.8).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.mat-select-panel')))
                                panel_wait = time.time() - t_panel_start
                                panel_visible = True
                            except Exception:
                                panel_wait = time.time() - t_panel_start
                                panel_visible = False

                            t_find_start = time.time()
                            try:
                                # tentar coletar opções mesmo se painel não reportou visibilidade
                                opcoes_acao = driver.find_elements(By.CSS_SELECTOR, 'div.mat-select-panel mat-option, mat-option[role="option"], mat-option')
                                find_time = time.time() - t_find_start
                            except Exception:
                                opcoes_acao = []
                                find_time = time.time() - t_find_start

                            if log:
                                print(f"[SISBAJUD] ℹ️ open_time={open_time:.2f}s panel_visible={panel_visible} panel_wait={panel_wait:.2f}s options_found={len(opcoes_acao)} find_time={find_time:.2f}s (dropdown #{idx+1})")

                            escolhido = None
                            escolhido_text = ''
                            try:
                                textos = [((o.text or '').strip(), o) for o in opcoes_acao]
                                lower_texts = [(t[0].lower(), t[1]) for t in textos]
                                for chave in prioridade:
                                    for txt, el in lower_texts:
                                        if chave in txt:
                                            escolhido = el
                                            escolhido_text = txt
                                            break
                                    if escolhido:
                                        break
                            except Exception:
                                escolhido = None

                            if not escolhido and opcoes_acao:
                                escolhido = opcoes_acao[0]
                                escolhido_text = (escolhido.text or '').strip()

                            if escolhido:
                                try:
                                    driver.execute_script('arguments[0].scrollIntoView(true);', escolhido)
                                except Exception:
                                    pass
                                time.sleep(0.06)

                                click_attempts = 0
                                clicked = False
                                click_method = None
                                while not clicked and click_attempts < 3:
                                    click_attempts += 1
                                    try:
                                        escolhido.click()
                                        clicked = True
                                        click_method = 'escolhido.click'
                                    except Exception:
                                        try:
                                            filho = escolhido.find_element(By.CSS_SELECTOR, 'span.mat-option-text')
                                            filho.click()
                                            clicked = True
                                            click_method = 'filho.click'
                                        except Exception:
                                            try:
                                                driver.execute_script('arguments[0].click();', escolhido)
                                                clicked = True
                                                click_method = 'escolhido.jsclick'
                                            except Exception:
                                                clicked = False
                                    if not clicked:
                                        time.sleep(0.08)

                                # medir tempos detalhados: após o clique, tempo até o painel sumir e breve espera adicional
                                t_after_click = time.time()
                                try:
                                    WebDriverWait(driver, 2).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '.mat-select-panel')))
                                    invis_wait = time.time() - t_after_click
                                except Exception:
                                    # se a espera falhar, medir o tempo gasto e prosseguir
                                    time.sleep(0.12)
                                    invis_wait = time.time() - t_after_click

                                # curto delay para a UI reagir
                                t_after_sleep = time.time()
                                time.sleep(0.06)
                                post_sleep = time.time() - t_after_sleep

                                # inspecionar se um modal de depósito ou snackbar apareceu logo após a seleção
                                dialog_present = False
                                dialog_snippet = ''
                                try:
                                    dialogs = driver.find_elements(By.CSS_SELECTOR, 'sisbajud-dialog-dados-deposito-judicial, div[role="dialog"], div.cdk-overlay-pane')
                                    if dialogs:
                                        dialog_present = True
                                        try:
                                            dialog_snippet = (dialogs[0].get_attribute('outerHTML') or '')[:240]
                                        except Exception:
                                            dialog_snippet = str(type(dialogs[0]))
                                except Exception:
                                    dialog_present = False

                                elapsed = time.time() - start_time
                                if log:
                                    try:
                                        snippet = escolhido.get_attribute('outerHTML')[:180]
                                    except Exception:
                                        snippet = escolhido_text
                                    print(f"[SISBAJUD] ✅ Ação selecionada no dropdown #{idx+1}: '{(escolhido_text or (escolhido.text or '').strip())}' -- click_attempts={click_attempts} click_method={click_method} open_attempts={open_attempts} open_method={open_method} total_elapsed={elapsed:.2f}s open_time={open_time:.2f}s panel_wait={panel_wait:.2f}s find_time={find_time:.2f}s invis_wait={invis_wait:.2f}s post_sleep={post_sleep:.2f}s dialog_present={dialog_present} url={driver.current_url} snippet: {snippet}")

                                selecionados += 1
                            else:
                                if log:
                                    print(f"[SISBAJUD] ⚠️ Nenhuma opção encontrada no dropdown #{idx+1} - painel_options={len(opcoes_acao)} snippet: {sel_outer}")

                            # pequeno atraso entre selects
                            time.sleep(0.08)
                        except Exception as e:
                            if log:
                                elapsed = time.time() - start_time
                                print(f"[SISBAJUD] ⚠️ Erro ao processar dropdown #{idx+1} after {elapsed:.2f}s: {e}")
                            continue

                    if log:
                        print(f"[SISBAJUD] ℹ️ Ações selecionadas: {selecionados}/{total_selects} mat-select(s)")

                    # fim for selects
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar ação (POSITIVO): {e}")

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
                    # Tipo de crédito: Geral (mat-select)
                    tipo_credito_select = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-select[formcontrolname="tipoCredito"]'))
                    )
                    try:
                        tipo_credito_select.click()
                    except Exception:
                        driver.execute_script('arguments[0].click();', tipo_credito_select)
                    time.sleep(0.8)
                    opcoes_tipo = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                    for opcao in opcoes_tipo:
                        try:
                            if "Geral" in (opcao.text or ''):
                                opcao.click()
                                if log:
                                    print("[SISBAJUD] ✅ Tipo de crédito 'Geral' selecionado")
                                break
                        except Exception:
                            continue

                    # Banco: 0001 Banco do Brasil (input com autocomplete)
                    banco_input = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="instituicaoFinanceiraPorCategoria"]'))
                    )
                    try:
                        banco_input.click()
                    except Exception:
                        driver.execute_script('arguments[0].click();', banco_input)
                    time.sleep(0.8)
                    opcoes_banco = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                    escolhido_banco = None
                    for opcao in opcoes_banco:
                        try:
                            txt = (opcao.text or '').strip()
                            # tentar casar formatos comuns: '00001 - BCO DO BRASIL' ou contendo 'Banco do Brasil'
                            if '00001' in txt or 'BANCO DO BRASIL' in txt.upper() or 'BCO DO BRASIL' in txt.upper():
                                escolhido_banco = opcao
                                break
                        except Exception:
                            continue

                    if escolhido_banco:
                        try:
                            # clicar diretamente no span de opção
                            escolhido_banco.click()
                            if log:
                                print(f"[SISBAJUD] ✅ Banco selecionado: '{(escolhido_banco.text or '').strip()}'")
                        except Exception:
                            try:
                                driver.execute_script('arguments[0].click();', escolhido_banco)
                                if log:
                                    print(f"[SISBAJUD] ✅ Banco (JS click) selecionado: '{(escolhido_banco.text or '').strip()}'")
                            except Exception:
                                if log:
                                    print("[SISBAJUD] ⚠️ Falha ao clicar na opção de banco selecionada")
                    else:
                        if log:
                            print("[SISBAJUD] ⚠️ Opção de banco desejada não encontrada nas opções exibidas")

                    # Agência: 5905
                    agencia_input = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="agencia"]'))
                    )
                    agencia_input.clear()
                    agencia_input.send_keys("5905")
                    if log:
                        print("[SISBAJUD] ✅ Agência '5905' preenchida")

                    # Confirmar/Enviar o modal de dados de depósito (botão 'Confirmar')
                    try:
                        btn_confirm = WebDriverWait(driver, 6).until(
                            EC.element_to_be_clickable((By.XPATH, "//sisbajud-dialog-dados-deposito-judicial//button//span[normalize-space(text())='Confirmar']/ancestor::button"))
                        )
                        try:
                            btn_confirm.click()
                        except Exception:
                            driver.execute_script('arguments[0].click();', btn_confirm)
                        if log:
                            print("[SISBAJUD] ✅ Confirmado modal de dados de depósito (Confirmar clicado)")

                        # aguardar fechamento do modal
                        try:
                            WebDriverWait(driver, 6).until(
                                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'sisbajud-dialog-dados-deposito-judicial'))
                            )
                            if log:
                                print("[SISBAJUD] ✅ Modal de depósito fechado")
                        except Exception:
                            if log:
                                print("[SISBAJUD] ⚠️ Modal de depósito não fechou imediatamente; prosseguindo")
                        # Após fechar modal: primeiro clicar no snackbar 'OK' se aparecer (confirma operação).
                        try:
                            ok_btn = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'snack-messenger-close-button') and .//span[normalize-space(text())='OK']]"))
                            )
                            try:
                                ok_btn.click()
                            except Exception:
                                try:
                                    driver.execute_script('arguments[0].click();', ok_btn)
                                except Exception:
                                    pass
                            if log:
                                print("[SISBAJUD] ✅ Snackbar 'OK' clicado após confirmação de depósito")
                            # pequeno delay para let the UI settle
                            time.sleep(0.4)
                        except Exception:
                            # snackbar not present - continue
                            pass

                        # após (possível) snackbar OK, aguardar botão 'Protocolar' e então clicar no chevron 'voltar' para sair de /desdobrar
                        try:
                            # Aguarda aparecimento do botão Protocolar como sinal de que a ordem foi processada
                            WebDriverWait(driver, 6).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'mat-fab') and @title='Protocolar']"))
                            )
                            if log:
                                print("[SISBAJUD] ✅ Botão 'Protocolar' detectado - ordem provavelmente processada")

                            # Clicar no botão chevron-left (voltar) para retornar a /detalhes
                            try:
                                chevron = WebDriverWait(driver, 4).until(
                                    EC.element_to_be_clickable((By.XPATH, "//button[.//mat-icon[contains(@class,'fa-chevron-left')]]"))
                                )
                                try:
                                    chevron.click()
                                except Exception:
                                    driver.execute_script('arguments[0].click();', chevron)
                                if log:
                                    print("[SISBAJUD] ✅ Clique no chevron 'voltar' executado")
                                # aguardar retorno para /detalhes
                                for _ in range(6):
                                    if "/detalhes" in driver.current_url:
                                        break
                                    time.sleep(0.5)
                            except Exception:
                                if log:
                                    print("[SISBAJUD] ⚠️ Não foi possível clicar no chevron 'voltar' automaticamente")
                        except Exception:
                            if log:
                                print("[SISBAJUD] ⚠️ Botão 'Protocolar' não encontrado após confirmar depósito; prosseguindo")
                    except Exception as e:
                        if log:
                            print(f"[SISBAJUD] ⚠️ Não foi possível confirmar modal de depósito: {e}")

                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Erro ao preencher dados de transferência: {e}")

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
        
        # Tentar extrair o número do processo a partir de várias fontes:
        # 1) dados_processo passado (pode conter 'numero_processo' ou 'numero' como lista)
        # 2) variável global processo_dados_extraidos (preenchida por iniciar_sisbajud)
        # 3) arquivo 'dadosatuais.json' via carregar_dados_processo()
        numero_processo = None
        def _normalizar_numero(valor):
            if isinstance(valor, list) and len(valor) > 0:
                return valor[0]
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
            return None

        if dados_processo and isinstance(dados_processo, dict):
            numero_processo = _normalizar_numero(dados_processo.get('numero_processo') or dados_processo.get('numero'))

        # Se não encontrado, tentar a variável global preenchida por iniciar_sisbajud
        if not numero_processo:
            try:
                if processo_dados_extraidos and isinstance(processo_dados_extraidos, dict):
                    numero_processo = _normalizar_numero(processo_dados_extraidos.get('numero') or processo_dados_extraidos.get('numero_processo'))
            except Exception:
                pass

        # Se ainda não encontrado, tentar carregar do arquivo dadosatuais.json
        if not numero_processo:
            try:
                dados_arquivo = carregar_dados_processo()
                if dados_arquivo and isinstance(dados_arquivo, dict):
                    numero_processo = _normalizar_numero(dados_arquivo.get('numero') or dados_arquivo.get('numero_processo'))
            except Exception:
                pass

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