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
from Fix import extrair_dados_processo, criar_gigs
from driver_config import criar_driver, login_func, criar_driver_sisb

# ===================== CONFIGURAÇÕES DE RATE LIMITING =====================

# Configurações globais para evitar bloqueio por excesso de requisições
SISBAJUD_CONFIG = {
    'min_delay_between_actions': 1.5,  # Delay mínimo entre ações (segundos)
    'max_delay_between_actions': 3.0,  # Delay máximo entre ações (segundos)
    'min_delay_between_clicks': 0.8,   # Delay mínimo entre cliques (segundos)
    'max_delay_between_clicks': 1.5,   # Delay máximo entre cliques (segundos)
    'delay_after_navigation': 3.0,     # Delay após navegação de página
    'delay_after_form_fill': 2.0,      # Delay após preenchimento de formulário
    'retry_attempts': 3,               # Tentativas de retry
    'retry_backoff_base': 2.0,         # Base para backoff exponencial
    'human_simulation': True,          # Simular comportamento humano
    'random_movement': True,           # Movimentos aleatórios de mouse
}

# Contador global de requisições para monitoramento
SISBAJUD_STATS = {
    'total_requests': 0,
    'last_request_time': 0,
    'consecutive_errors': 0,
    'rate_limit_detected': False
}

# ===================== FUNÇÕES DE RATE LIMITING E SIMULAÇÃO HUMANA =====================

# ===================== FUNÇÕES DE RATE LIMITING E SIMULAÇÃO HUMANA =====================

def adjust_speed_for_rate_limit():
    """
    Ajusta automaticamente a velocidade quando rate limiting é detectado
    """
    global SISBAJUD_CONFIG
    
    if SISBAJUD_STATS['rate_limit_detected'] or SISBAJUD_STATS['consecutive_errors'] > 2:
        print('[SISBAJUD] 🐌 Rate limiting detectado - ajustando para modo LENTO')
        SISBAJUD_CONFIG['min_delay_between_actions'] = 3.0
        SISBAJUD_CONFIG['max_delay_between_actions'] = 5.0
        SISBAJUD_CONFIG['min_delay_between_clicks'] = 2.0
        SISBAJUD_CONFIG['max_delay_between_clicks'] = 3.0
        SISBAJUD_CONFIG['delay_after_navigation'] = 5.0
        SISBAJUD_CONFIG['delay_after_form_fill'] = 3.0
    else:
        # Valores normais
        SISBAJUD_CONFIG['min_delay_between_actions'] = 1.5
        SISBAJUD_CONFIG['max_delay_between_actions'] = 3.0
        SISBAJUD_CONFIG['min_delay_between_clicks'] = 0.8
        SISBAJUD_CONFIG['max_delay_between_clicks'] = 1.5
        SISBAJUD_CONFIG['delay_after_navigation'] = 3.0
        SISBAJUD_CONFIG['delay_after_form_fill'] = 2.0

def detect_rate_limit_error(error_message):
    """
    Detecta se uma mensagem de erro indica rate limiting
    """
    if not error_message:
        return False
    
    error_lower = str(error_message).lower()
    rate_limit_indicators = [
        'excesso de requisições',
        'excesso de requisicoes', 
        'too many requests',
        'rate limit',
        'limite de requisições',
        'acesso interrompido',
        'bloqueado temporariamente',
        'muitas tentativas'
    ]
    
    for indicator in rate_limit_indicators:
        if indicator in error_lower:
            print(f'[SISBAJUD] 🚨 Rate limiting detectado: {indicator}')
            SISBAJUD_STATS['rate_limit_detected'] = True
            adjust_speed_for_rate_limit()
            return True
    
    return False

def smart_delay(action_type='default', base_delay=None):
    """
    Implementa delay inteligente baseado no tipo de ação e estado atual
    """
    global SISBAJUD_STATS
    
    # Ajustar velocidade se necessário
    adjust_speed_for_rate_limit()
    
    # Determinar delay base por tipo de ação
    if base_delay is None:
        if action_type == 'navigation':
            base_delay = SISBAJUD_CONFIG['delay_after_navigation']
        elif action_type == 'form_fill':
            base_delay = SISBAJUD_CONFIG['delay_after_form_fill']
        elif action_type == 'click':
            min_delay = SISBAJUD_CONFIG['min_delay_between_clicks']
            max_delay = SISBAJUD_CONFIG['max_delay_between_clicks']
            base_delay = random.uniform(min_delay, max_delay)
        else:  # default
            min_delay = SISBAJUD_CONFIG['min_delay_between_actions']
            max_delay = SISBAJUD_CONFIG['max_delay_between_actions']
            base_delay = random.uniform(min_delay, max_delay)
    
    # Aumentar delay se houver erros consecutivos (backoff exponencial)
    if SISBAJUD_STATS['consecutive_errors'] > 0:
        backoff_multiplier = SISBAJUD_CONFIG['retry_backoff_base'] ** SISBAJUD_STATS['consecutive_errors']
        base_delay *= min(backoff_multiplier, 10)  # Máximo 10x o delay
        print(f'[SISBAJUD] Backoff ativo: {SISBAJUD_STATS["consecutive_errors"]} erros, delay = {base_delay:.2f}s')
    
    # Aumentar delay se rate limit foi detectado
    if SISBAJUD_STATS['rate_limit_detected']:
        base_delay *= 3
        print(f'[SISBAJUD] Rate limit detectado, delay aumentado para {base_delay:.2f}s')
    
    # Garantir tempo mínimo entre requisições
    current_time = time.time()
    time_since_last = current_time - SISBAJUD_STATS['last_request_time']
    if time_since_last < base_delay:
        additional_wait = base_delay - time_since_last
        time.sleep(additional_wait)
    
    # Atualizar estatísticas
    SISBAJUD_STATS['last_request_time'] = time.time()
    SISBAJUD_STATS['total_requests'] += 1
    
    print(f'[SISBAJUD] Delay {action_type}: {base_delay:.2f}s (requisição #{SISBAJUD_STATS["total_requests"]})')

def simulate_human_movement(driver, element=None):
    """
    Simula movimento humano de mouse para evitar detecção de bot
    """
    if not SISBAJUD_CONFIG['human_simulation']:
        return
    
    try:
        if element:
            # Fazer scroll suave para garantir que o elemento está visível
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            smart_delay('default', base_delay=0.2)
            
            # Movimento simples para o elemento (sem offset para evitar coordenadas inválidas)
            action_chains = ActionChains(driver)
            action_chains.move_to_element(element)
            action_chains.perform()
            
            # Pequena pausa para simular comportamento humano
            smart_delay('default', base_delay=0.1)
        
    except Exception as e:
        # Se der erro, apenas continuar sem movimento - não é crítico
        pass

def safe_click(driver, element, delay_type='click'):
    """
    Clique seguro com delay e simulação humana
    """
    try:
        smart_delay(delay_type)
        simulate_human_movement(driver, element)
        element.click()
        print('[SISBAJUD] ✅ Clique realizado com sucesso')
        # Reset contador de erros consecutivos em caso de sucesso
        SISBAJUD_STATS['consecutive_errors'] = 0
        SISBAJUD_STATS['rate_limit_detected'] = False
        return True
    except Exception as e:
        print(f'[SISBAJUD] ❌ Erro no clique: {e}')
        SISBAJUD_STATS['consecutive_errors'] += 1
        detect_rate_limit_error(str(e))
        return False

def safe_execute_script(driver, script, delay_type='default', *args):
    """
    Execução segura de JavaScript com delay e tratamento de erro
    """
    try:
        smart_delay(delay_type)
        if args:
            result = driver.execute_script(script, *args)
        else:
            result = driver.execute_script(script)
        print('[SISBAJUD] ✅ Script executado com sucesso')
        # Reset contador de erros consecutivos em caso de sucesso
        SISBAJUD_STATS['consecutive_errors'] = 0
        SISBAJUD_STATS['rate_limit_detected'] = False
        return result
    except Exception as e:
        print(f'[SISBAJUD] ❌ Erro na execução do script: {e}')
        SISBAJUD_STATS['consecutive_errors'] += 1
        detect_rate_limit_error(str(e))
        return None

def safe_navigate(driver, url, delay_type='navigation'):
    """
    Navegação segura com delay e tratamento de erro
    """
    try:
        smart_delay(delay_type)
        driver.get(url)
        print(f'[SISBAJUD] ✅ Navegação para {url} realizada com sucesso')
        # Reset contador de erros consecutivos em caso de sucesso
        SISBAJUD_STATS['consecutive_errors'] = 0
        SISBAJUD_STATS['rate_limit_detected'] = False
        return True
    except Exception as e:
        print(f'[SISBAJUD] ❌ Erro na navegação: {e}')
        SISBAJUD_STATS['consecutive_errors'] += 1
        detect_rate_limit_error(str(e))
        return False

def with_retry(func, *args, **kwargs):
    """
    Executa função com retry e backoff exponencial
    """
    max_attempts = SISBAJUD_CONFIG['retry_attempts']
    
    for attempt in range(max_attempts):
        try:
            result = func(*args, **kwargs)
            if result:  # Sucesso
                return result
        except Exception as e:
            print(f'[SISBAJUD] Tentativa {attempt + 1}/{max_attempts} falhou: {e}')
            detect_rate_limit_error(str(e))
            
            if attempt < max_attempts - 1:  # Não é a última tentativa
                backoff_time = SISBAJUD_CONFIG['retry_backoff_base'] ** attempt
                backoff_time += random.uniform(0, 1)  # Jitter
                print(f'[SISBAJUD] Aguardando {backoff_time:.2f}s antes da próxima tentativa...')
                time.sleep(backoff_time)
            else:
                print(f'[SISBAJUD] ❌ Todas as tentativas falharam para: {func.__name__}')
                
    return None

# ===================== UTILITÁRIOS =====================

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
        
        # Focar via JavaScript como no gigs.py (corrigido)
        driver.execute_script("arguments[0].focus();", elemento_cpf)
        
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
    """
    Aguarda elemento aparecer com delay inteligente (equivalente ao esperarElemento do gigs.js)
    """
    try:
        smart_delay('default')  # Delay antes de buscar elemento
        
        if texto:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{texto}')]"))
            )
        else:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
            )
        
        # Simular movimento humano para o elemento
        simulate_human_movement(driver, element)
        return element
        
    except Exception as e:
        print(f'[SISBAJUD] ⚠️ Elemento não encontrado ({seletor}): {e}')
        SISBAJUD_STATS['consecutive_errors'] += 1
        return None


def aguardar_e_clicar(driver, seletor, texto=None, timeout=10):
    """
    Aguarda e clica em elemento com segurança (equivalente ao clicarBotao do gigs.js)
    """
    elemento = aguardar_elemento(driver, seletor, texto, timeout)
    if elemento:
        return safe_click(driver, elemento, 'click')
    return False


def aguardar_opcoes_aparecerem(driver, seletor_opcoes, intervalo_ms=100, max_tentativas=50):
    """
    Polling com delay inteligente para aguardar opções de overlay aparecerem
    """
    tentativas = 0
    while tentativas < max_tentativas:
        try:
            # Usar delay menor mas com variação para parecer mais humano
            smart_delay('default', base_delay=intervalo_ms / 1000.0)
            
            opcoes = driver.find_elements(By.CSS_SELECTOR, seletor_opcoes)
            if opcoes:
                print(f'[SISBAJUD] ✅ Encontradas {len(opcoes)} opções após {tentativas + 1} tentativas')
                return opcoes
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao buscar opções (tentativa {tentativas + 1}): {e}')
            
        tentativas += 1
    
    print(f'[SISBAJUD] ❌ Timeout: opções não encontradas após {max_tentativas} tentativas')
    return []


def escolher_opcao_sisbajud(driver, seletor, valor):
    """
    Seleciona uma opção de autocomplete/select baseado em texto parcial - robusto para SISBAJUD
    com delays seguros para evitar rate limiting
    """
    try:
        # Buscar o campo com retry
        campo = None
        for tentativa in range(8):
            try:
                smart_delay('default', base_delay=0.5)  # Delay entre tentativas
                campo = driver.find_element(By.CSS_SELECTOR, seletor)
                break
            except Exception:
                print(f'[SISBAJUD] Tentativa {tentativa + 1}/8 para encontrar campo {seletor}')
        
        if not campo:
            print(f'[SISBAJUD] ❌ Campo não encontrado: {seletor}')
            return False

        # Clicar no campo com segurança
        if not safe_click(driver, campo, 'click'):
            # Tentar via JavaScript como fallback
            if not safe_execute_script(driver, 'arguments[0].click();', 'click', campo):
                print(f'[SISBAJUD] ❌ Não foi possível clicar no campo: {seletor}')
                return False

        # Aguardar opções aparecerem com delay inteligente
        print(f'[SISBAJUD] Aguardando opções para valor: {valor}')
        opcoes = aguardar_opcoes_aparecerem(driver, 'mat-option[role="option"], option, span.mat-option-text', 
                                          intervalo_ms=200, max_tentativas=20)
        
        if not opcoes:
            print(f'[SISBAJUD] ❌ Nenhuma opção encontrada para: {valor}')
            return False

        # Procurar correspondência com delay entre verificações
        print(f'[SISBAJUD] Procurando entre {len(opcoes)} opções...')
        for i, opc in enumerate(opcoes):
            try:
                smart_delay('default', base_delay=0.2)  # Delay entre verificações de opções
                texto_opcao = opc.text.strip()
                
                if valor.lower() in texto_opcao.lower():
                    print(f'[SISBAJUD] ✅ Opção encontrada: "{texto_opcao}" (posição {i + 1})')
                    
                    # Simular movimento para a opção
                    simulate_human_movement(driver, opc)
                    
                    # Tentar clicar na opção
                    if safe_click(driver, opc, 'click'):
                        print(f'[SISBAJUD] ✅ Opção selecionada com sucesso')
                        return True
                    else:
                        # Fallback via JavaScript
                        if safe_execute_script(driver, 'arguments[0].click();', 'click', opc):
                            print(f'[SISBAJUD] ✅ Opção selecionada via JavaScript')
                            return True
                        else:
                            print(f'[SISBAJUD] ❌ Falha ao clicar na opção: {texto_opcao}')
                            continue
                            
            except Exception as e:
                print(f'[SISBAJUD] ⚠️ Erro ao processar opção {i + 1}: {e}')
                continue

        print(f'[SISBAJUD] ❌ Nenhuma opção correspondente encontrada para: {valor}')
        return False
        
    except Exception as e:
        print(f'[SISBAJUD] ❌ Erro geral em escolher_opcao_sisbajud: {e}')
        SISBAJUD_STATS['consecutive_errors'] += 1
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

def login_automatico_sisbajud(driver):
    """
    Login automatizado humanizado no SISBAJUD com simulação de comportamento humano
    """
    try:
        print('[SISBAJUD][LOGIN] Navegando para SISBAJUD...')
        
        # Tentar navegação com retry em caso de erro de conexão
        max_tentativas = 3
        for tentativa in range(1, max_tentativas + 1):
            try:
                driver.get('https://sisbajud.cnj.jus.br/')
                break  # Sucesso, sair do loop
            except Exception as nav_error:
                print(f'[SISBAJUD][LOGIN] ⚠️ Tentativa {tentativa}/{max_tentativas} falhou: {nav_error}')
                if tentativa < max_tentativas:
                    print(f'[SISBAJUD][LOGIN] Aguardando 3s antes de tentar novamente...')
                    time.sleep(3)
                else:
                    print('[SISBAJUD][LOGIN] ❌ Todas as tentativas de navegação falharam')
                    return False
        
        # Aguardar carregamento otimizado
        time.sleep(random.uniform(1.0, 1.5))  # Reduzido de 2.5-4.0 para 1.0-1.5
        
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
            
        # Aguardar redirecionamento otimizado
        time.sleep(random.uniform(1.5, 2.0))  # Reduzido de 3.0-5.0 para 1.5-2.0
        
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

        # Após detectar a URL específica, aguardar 2 segundos e clicar em Nova Minuta
        print('[SISBAJUD] ✅ URL /minuta confirmada, aguardando 2 segundos...')
        time.sleep(2)
        
        # Maximizar janela rapidamente
        try:
            driver.maximize_window()
            print('[SISBAJUD] ✅ Janela maximizada')
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Não foi possível maximizar a janela: {e}')
        
        # Clicar automaticamente em "Nova Minuta"
        print('[SISBAJUD] Clicando automaticamente no botão "Nova Minuta"...')
        script = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary');
        }
        if (botaoNova) {
            // Se for ícone, clica no botão pai
            if (botaoNova.tagName === 'MAT-ICON') {
                botaoNova = botaoNova.closest('button');
            }
            botaoNova.click();
            return true;
        }
        return false;
        """
        
        sucesso = driver.execute_script(script)
        if sucesso:
            print('[SISBAJUD] ✅ Botão "Nova Minuta" clicado automaticamente')
            time.sleep(1)  # Aguardar navegação
        else:
            print('[SISBAJUD] ⚠️ Botão "Nova Minuta" não encontrado, será necessário navegar manualmente')

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

def safe_fill_field(driver, selector, value, field_name="campo", delay_base=1.0, log=True):
    """
    Preenchimento seguro de campo que evita StaleElementReferenceError
    """
    try:
        # Localizar elemento
        element = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        
        # Simular movimento humano
        simulate_human_movement(driver, element)
        
        # Clicar
        if not safe_click(driver, element, 'click'):
            safe_execute_script(driver, 'arguments[0].click();', 'click', element)
        
        # Delay antes de digitar
        smart_delay('form_fill', base_delay=delay_base)
        
        # Re-localizar elemento para digitação
        element_fresh = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        
        # Limpar e preencher
        element_fresh.clear()
        smart_delay('default', base_delay=0.3)
        
        # Digitar caractere por caractere
        for char in str(value):
            try:
                # Re-localizar antes de cada caractere para máxima segurança
                current_element = driver.find_element(By.CSS_SELECTOR, selector)
                current_element.send_keys(char)
                smart_delay('default', base_delay=0.1)
            except Exception:
                # Se falhar, tentar sem re-localização
                element_fresh.send_keys(char)
                smart_delay('default', base_delay=0.1)
        
        if log:
            print(f"[SISBAJUD] ✅ {field_name} preenchido: {value}")
        return True
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao preencher {field_name}: {e}")
        SISBAJUD_STATS['consecutive_errors'] += 1
        return False

def emergency_slow_mode():
    """
    Ativa modo de emergência ultra-lento quando rate limiting persiste
    """
    global SISBAJUD_CONFIG
    
    print('[SISBAJUD] 🚨 MODO DE EMERGÊNCIA ATIVADO - Velocidade ultra-lenta')
    
    SISBAJUD_CONFIG['min_delay_between_actions'] = 5.0
    SISBAJUD_CONFIG['max_delay_between_actions'] = 8.0
    SISBAJUD_CONFIG['min_delay_between_clicks'] = 3.0
    SISBAJUD_CONFIG['max_delay_between_clicks'] = 5.0
    SISBAJUD_CONFIG['delay_after_navigation'] = 8.0
    SISBAJUD_CONFIG['delay_after_form_fill'] = 5.0
    SISBAJUD_CONFIG['retry_attempts'] = 5
    
    print('[SISBAJUD] ⏱️ Delays configurados: ações 5-8s, cliques 3-5s, navegação 8s')

def reset_rate_limit_detection():
    """
    Reseta a detecção de rate limiting após período de sucesso
    """
    global SISBAJUD_STATS
    
    SISBAJUD_STATS['consecutive_errors'] = 0
    SISBAJUD_STATS['rate_limit_detected'] = False
    
    # Voltar para velocidade normal
    SISBAJUD_CONFIG['min_delay_between_actions'] = 1.5
    SISBAJUD_CONFIG['max_delay_between_actions'] = 3.0
    SISBAJUD_CONFIG['min_delay_between_clicks'] = 0.8
    SISBAJUD_CONFIG['max_delay_between_clicks'] = 1.5
    SISBAJUD_CONFIG['delay_after_navigation'] = 3.0
    SISBAJUD_CONFIG['delay_after_form_fill'] = 2.0
    SISBAJUD_CONFIG['retry_attempts'] = 3
    
    print('[SISBAJUD] ✅ Rate limiting resetado - voltando à velocidade normal')

def print_rate_limit_status():
    """
    Imprime status atual do controle de rate limiting
    """
    status = "🟢 NORMAL"
    if SISBAJUD_STATS['rate_limit_detected']:
        status = "🟡 RATE LIMIT DETECTADO"
    if SISBAJUD_STATS['consecutive_errors'] > 3:
        status = "🔴 MODO EMERGÊNCIA"
    
    print(f'''
[SISBAJUD] === STATUS RATE LIMITING ===
Status: {status}
Requisições totais: {SISBAJUD_STATS['total_requests']}
Erros consecutivos: {SISBAJUD_STATS['consecutive_errors']}
Rate limit detectado: {SISBAJUD_STATS['rate_limit_detected']}
Delays atuais: {SISBAJUD_CONFIG['min_delay_between_actions']:.1f}-{SISBAJUD_CONFIG['max_delay_between_actions']:.1f}s
==========================================
''')

# ===================== FUNÇÕES AUXILIARES OTIMIZADAS (baseadas em gigs.py) =====================

def trigger_event(driver, element, event_type):
    """Dispara evento customizado no elemento usando JavaScript otimizado"""
    if event_type == 'input':
        script = """
        if ('createEvent' in document) {        
            let e = document.createEvent('HTMLEvents');
            e.initEvent('input', false, true);
            arguments[0].dispatchEvent(e);
        }
        """
        driver.execute_script(script, element)
    elif event_type == 'click':
        element.click()

def aguardar_elemento_otimizado(driver, seletor, timeout=10, texto=None):
    """Aguarda elemento aparecer com otimizações do gigs.py"""
    try:
        if texto:
            element = WebDriverWait(driver, timeout).until(
                lambda d: next((el for el in d.find_elements(By.CSS_SELECTOR, seletor) 
                              if texto in el.text), None)
            )
        else:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
            )
        
        # Verificar se não está disabled (como em gigs.py)
        if element.get_attribute('disabled'):
            return None
        return element
    except:
        return None

def aguardar_opcoes_com_polling(driver, timeout_seconds=5):
    """Aguarda opções aparecerem usando polling como gigs.py"""
    end_time = time.time() + timeout_seconds
    while time.time() < end_time:
        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
        if opcoes:
            return opcoes
        time.sleep(0.1)  # Polling interval de 100ms como gigs.js
    return []

def escolher_opcao_sisbajud_otimizado(driver, seletor, valor):
    """Função otimizada baseada em escolherOpcaoSISBAJUD do gigs.py"""
    try:
        # 1. Aguardar e focar no elemento
        elemento = aguardar_elemento_otimizado(driver, seletor)
        if not elemento:
            print(f'[SISBAJUD][ERRO] Elemento não encontrado: {seletor}')
            return False
        
        # Focar via JavaScript como no gigs.py
        driver.execute_script("arguments[0].focus();", elemento)
        elemento.click()
        
        # 2. Múltiplas tentativas com seta para baixo (como gigs.py)
        for tentativa in range(3):
            # Simular seta para baixo para abrir dropdown
            ActionChains(driver).send_keys_to_element(elemento, Keys.ARROW_DOWN).perform()
            time.sleep(0.1)
            
            # Aguardar opções com polling
            opcoes = aguardar_opcoes_com_polling(driver, 1)
            if opcoes:
                break
        
        if not opcoes:
            print(f'[SISBAJUD][ERRO] Nenhuma opção encontrada para {seletor}')
            return False
        
        # 3. Procurar e clicar na opção correta
        for opcao in opcoes:
            if valor.lower().strip() in opcao.text.lower():
                opcao.click()
                print(f'[SISBAJUD] ✅ Opção selecionada: {opcao.text}')
                return True
        
        print(f'[SISBAJUD][ERRO] Opção "{valor}" não encontrada')
        return False
        
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao escolher opção {valor}: {e}')
        return False

def configurar_monitoring_erros_otimizado(driver):
    """Configura monitoramento de erros usando JavaScript como gigs.py"""
    script = """
    if (window.sisbajud_error_monitor) { return; }
    
    window.sisbajud_error_monitor = true;
    window.sisbajud_last_error = null;
    
    // MutationObserver para monitorar erros como gigs.py
    let target_erros = document.body;
    let observer_erros = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.target.tagName != "DIV") { return }
            if (mutation.target.className != "cdk-overlay-container") { return }
            if (!mutation.target.innerText) { return }
            
            let errorText = mutation.target.innerText;
            if (errorText.includes('CPF ou CNPJ inválidos.') || 
                errorText.includes('O Réu/Executado já foi incluído.') ||
                errorText.includes('Campo "CPF/CNPJ') ||
                errorText.includes('Falha ao obter retorno do sistema CCS.')) {
                
                window.sisbajud_last_error = errorText;
                
                // Fechar mensagem de erro
                let closeBtn = document.querySelector('button[class*="snack-messenger-close-button"]');
                if (closeBtn) { closeBtn.click(); }
            }
        });
    });
    
    let config_erros = { childList: true, characterData: true, subtree: true };
    observer_erros.observe(target_erros, config_erros);
    
    console.log('[SISBAJUD] Monitoring de erros configurado');
    """
    driver.execute_script(script)

def verificar_erro_sisbajud(driver):
    """Verifica se houve erro no SISBAJUD"""
    try:
        erro = driver.execute_script("return window.sisbajud_last_error;")
        if erro:
            # Limpar erro após leitura
            driver.execute_script("window.sisbajud_last_error = null;")
            return erro
        return None
    except:
        return None

def cadastrar_reu_sisbajud_otimizado(driver, reu, configuracoes_sisbajud):
    """Cadastra um réu no SISBAJUD com otimizações do gigs.py"""
    try:
        cpf_cnpj = reu.get('cpfcnpj', '')
        if not cpf_cnpj:
            print(f'[SISBAJUD] ⚠️ Réu sem CPF/CNPJ: {reu.get("nome", "N/A")}')
            return True  # Pular, mas não falhar
        
        # Campo de entrada
        campo_cpf = aguardar_elemento_otimizado(driver, 'input[placeholder*="CPF/CNPJ"]')
        if not campo_cpf:
            print('[SISBAJUD] ❌ Campo CPF/CNPJ não encontrado')
            return False
        
        # Limpar formatação
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
        
        # CNPJ raiz? (como gigs.py)
        valor_final = cpf_cnpj_limpo
        if len(cpf_cnpj_limpo) == 14:  # É CNPJ
            if configuracoes_sisbajud.get('cnpjRaiz', '').lower() == 'sim':
                valor_final = cpf_cnpj_limpo[:8]  # CNPJ raiz (8 dígitos)
        
        # Preencher campo usando JavaScript para focus (como gigs.py)
        driver.execute_script("arguments[0].focus();", campo_cpf)
        campo_cpf.clear()
        campo_cpf.send_keys(valor_final)
        trigger_event(driver, campo_cpf, 'input')
        
        # Delay como gigs.py para evitar bug
        time.sleep(0.8)
        
        # Verificar se houve correção automática do SISBAJUD
        valor_atual = campo_cpf.get_attribute('value')
        if len(valor_final) < 15 and len(valor_atual) == 10:
            # Corrigir bug do SISBAJUD mencionado em gigs.py
            campo_cpf.clear()
            campo_cpf.send_keys(valor_final)
            trigger_event(driver, campo_cpf, 'input')
            time.sleep(0.8)
        
        # Botão adicionar
        btn_adicionar = aguardar_elemento_otimizado(driver, 'button[aria-label="Adicionar"]')
        if btn_adicionar:
            btn_adicionar.click()
            time.sleep(0.5)
            
            # Verificar se houve erro
            erro = verificar_erro_sisbajud(driver)
            if erro:
                print(f'[SISBAJUD] ⚠️ Erro ao adicionar réu: {erro}')
                if 'inválidos' in erro and len(cpf_cnpj_limpo) == 14:
                    # Tentar com CNPJ completo
                    print('[SISBAJUD] Tentando com CNPJ completo...')
                    return cadastrar_reu_sisbajud_otimizado(driver, reu, {'cnpjRaiz': 'não'})
                return False
            
            return True
        else:
            print('[SISBAJUD] ❌ Botão adicionar não encontrado')
            return False
            
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao cadastrar réu: {e}')
        return False

def criar_span_valor_otimizado(driver, valor_formatado, data_divida):
    """Cria span clicável para valor como gigs.py"""
    script = f"""
    let ancora = document.querySelector('div[class="label-valor-extenso"]');
    if (ancora && !document.getElementById('maisPJe_valor_execucao')) {{
        let span = document.createElement('span');
        span.id = 'maisPJe_valor_execucao';
        span.innerText = "Última atualização do processo: {valor_formatado} em {data_divida}";
        span.style = "color: white; background-color: slategray; padding: 10px; border-radius: 10px; cursor: pointer;";
        span.onclick = function() {{
            let input = document.querySelector('input[placeholder*="Valor aplicado a todos"]');
            if (input) {{
                input.value = "{valor_formatado}";
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }};
        ancora.appendChild(document.createElement('br'));
        ancora.appendChild(document.createElement('br'));
        ancora.appendChild(span);
    }}
    """
    driver.execute_script(script)

def preencher_valor_automatico_otimizado(driver, valor_formatado):
    """Preenche valor automaticamente"""
    try:
        span_valor = driver.find_element(By.ID, 'maisPJe_valor_execucao')
        span_valor.click()
        time.sleep(0.5)
        
        # Marcar checkbox para aplicar valor
        checkbox = aguardar_elemento_otimizado(driver, 'div[id="maisPje_sisbajud_monitor"] mat-icon[class*="fa-check-square"]')
        if checkbox:
            checkbox.click()
    except Exception as e:
        print(f'[SISBAJUD] ⚠️ Erro ao preencher valor automaticamente: {e}')

def extrair_protocolo_otimizado(driver):
    """Extrai protocolo da página de sucesso"""
    try:
        # Aguardar página carregar
        time.sleep(2)
        
        # Buscar protocolo em vários seletores possíveis
        seletores_protocolo = [
            'span:contains("Protocolo")',
            '[class*="protocolo"]',
            'strong:contains("número")',
            'span[class*="numero"]'
        ]
        
        for seletor in seletores_protocolo:
            try:
                elemento = driver.find_element(By.CSS_SELECTOR, seletor)
                texto = elemento.text
                # Extrair número do protocolo usando regex
                import re
                match = re.search(r'(\d{10,})', texto)
                if match:
                    return match.group(1)
            except:
                continue
        
        # Buscar na URL
        url = driver.current_url
        match = re.search(r'/(\d{10,})/', url)
        if match:
            return match.group(1)
        
        return None
    except Exception as e:
        print(f'[SISBAJUD] ⚠️ Erro ao extrair protocolo: {e}')
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

def coletar_dados_minuta_sisbajud(driver, protocolo_primeira=None, data_protocolo=None):
    """
    Executa JavaScript para coletar dados da minuta SISBAJUD e retorna o texto formatado
    """
    try:
        print('[SISBAJUD] Executando script de coleta de dados...')
        
        # JavaScript fornecido pelo usuário (decodificado)
        script_coleta = """
        function getCleanText(selector) {
            const element = document.querySelector(selector);
            if (element) {
                return element.textContent.trim();
            }
            return null;
        }
        
        function getValueByLabel(labelText) {
            // Buscar no novo formato HTML do SISBAJUD
            const labels = Array.from(document.querySelectorAll('.sisbajud-label'));
            const targetLabel = labels.find(label => label.textContent.trim().includes(labelText));
            if (targetLabel) {
                // Buscar o valor na mesma div pai usando o novo formato
                const parentDiv = targetLabel.closest('.col-md-3') || targetLabel.parentElement;
                if (parentDiv) {
                    const valueElement = parentDiv.querySelector('.sisbajud-label-valor');
                    if (valueElement) {
                        return valueElement.textContent.trim();
                    }
                }
            }
            return null;
        }
        
        try {
            // Extrair dados usando o novo formato HTML
            const numeroProcesso = getValueByLabel('Número do processo:');
            const numeroProtocolo = getValueByLabel('Número do protocolo:');
            const repeticaoProgramada = getValueByLabel('Repetição programada?');
            const limiteRepeticao = getValueByLabel('Data limite da repetição:');
            const valorBloqueio = getCleanText('td[data-label="valorBloquear:"]');
            
            const executados = [];
            const rowsExecutados = document.querySelectorAll('tr.element-row');
            rowsExecutados.forEach(row => {
                const nomeElement = row.querySelector('.col-reu-dados-nome-pessoa');
                const documentoElement = row.querySelector('.col-reu-dados a');
                if (nomeElement && documentoElement) {
                    const nome = nomeElement.textContent.trim();
                    const documento = documentoElement.textContent.trim();
                    executados.push(`${nome} - [${documento}]`);
                }
            });
            
            const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';
            
            let resultado = `<p ${pStyle}><strong>Dados da Teimosinha protocolada:</strong></p>`;
            resultado += `<p ${pStyle}>Número do processo: <strong>${numeroProcesso || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Número do protocolo: <strong>${numeroProtocolo || 'Não encontrado'}</strong></p>`;
            
            // Adicionar data do protocolo se fornecida
            if (arguments[0] && arguments[0].dataProtocolo) {
                resultado += `<p ${pStyle}>Data do protocolo: <strong>${arguments[0].dataProtocolo}</strong></p>`;
            }
            
            resultado += `<p ${pStyle}>Repetição programada? <strong>${repeticaoProgramada || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Limite da repetição: <strong>${limiteRepeticao || 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}>Valor do bloqueio: <strong>${valorBloqueio ? valorBloqueio.split('\\n')[0] : 'Não encontrado'}</strong></p>`;
            resultado += `<p ${pStyle}><strong>Partes alvo do bloqueio:</strong></p>`;
            
            if (executados.length > 0) {
                executados.forEach(executado => {
                    resultado += `<p ${pStyle}><strong>${executado}</strong></p>`;
                });
            } else {
                resultado += `<p ${pStyle}><strong>Nenhum executado encontrado</strong></p>`;
            }
            
            // Adicionar linha sobre segunda ordem se protocolo fornecido
            if (arguments[0] && arguments[0].protocoloPrimeira) {
                resultado += `<p ${pStyle}><strong>Protocolo da segunda ordem agendada para o dia útil seguinte: ${arguments[0].protocoloPrimeira}</strong></p>`;
            }
            
            resultado += `<p ${pStyle}>Notas:</p>`;
            resultado += `<p ${pStyle}>-Por padrão é consultado CNPJ raiz.</p>`;
            resultado += `<p ${pStyle}>-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.</p>`;
            
            return resultado;
            
        } catch (error) {
            return 'ERRO: ' + error.message;
        }
        """
        
        # Executar o script e obter o resultado
        resultado = driver.execute_script(script_coleta, {'protocoloPrimeira': protocolo_primeira, 'dataProtocolo': data_protocolo})
        
        if resultado and not resultado.startswith('ERRO:'):
            print('[SISBAJUD] ✅ Dados coletados com sucesso')
            return resultado
        else:
            print(f'[SISBAJUD] ❌ Erro na coleta: {resultado}')
            return None
            
    except Exception as e:
        print(f'[SISBAJUD] ❌ Falha ao executar script de coleta: {e}')
        return None

def minuta_bloqueio(driver_pje=None, dados_processo=None, driver_sisbajud=None, prazo_dias=30):
    """
    Cria minuta de bloqueio no SISBAJUD reproduzindo exatamente a lógica do gigs.py
    
    Args:
        driver_pje: Driver do PJe
        dados_processo: Dados do processo
        driver_sisbajud: Driver do SISBAJUD (opcional)
        prazo_dias: Prazo em dias para repetição (30 ou 60, padrão 30)
    """
    try:
        print('\n[SISBAJUD] INICIANDO MINUTA DE BLOQUEIO')
        print('=' * 60)
        
        # Imprimir status do rate limiting
        print_rate_limit_status()
        
        # Ativar modo de emergência se muitos erros consecutivos
        if SISBAJUD_STATS['consecutive_errors'] > 3:
            emergency_slow_mode()
        
        # 1. Usar driver fornecido ou inicializar novo
        print('[SISBAJUD] 1. Verificando driver SISBAJUD...')
        if driver_sisbajud:
            print('[SISBAJUD] Usando driver SISBAJUD fornecido')
        else:
            driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        
        if not driver_sisbajud:
            print('[SISBAJUD] ❌ Falha ao obter driver SISBAJUD')
            return None
        
        print('[SISBAJUD] ✅ Driver SISBAJUD disponível')
        
        # 2. Carregar dados do processo
        if not dados_processo:
            print('[SISBAJUD] 2. Carregando dados do processo...')
            dados_processo = carregar_dados_processo()
        
        if not dados_processo:
            print('[SISBAJUD] ❌ Dados do processo não disponíveis')
            return None
        
        print('[SISBAJUD] ✅ Dados do processo carregados')
        
        # Extrair número do processo dos dados
        numero_processo = dados_processo.get('numero', 'desconhecido')
        print(f'[SISBAJUD] Número do processo: {numero_processo}')
        
        # 2.1. NOVO: Verificar se há réus restantes de processamento anterior
        print('[SISBAJUD] 2.1. Verificando réus restantes de processamento anterior...')
        reus_restantes_arquivo = os.path.join(os.path.dirname(__file__), f'reus_restantes_{numero_processo}.json')
        
        if os.path.exists(reus_restantes_arquivo):
            try:
                with open(reus_restantes_arquivo, 'r', encoding='utf-8') as f:
                    dados_restantes = json.load(f)
                
                reus_restantes_carregados = dados_restantes.get('reus_restantes', [])
                if reus_restantes_carregados:
                    print(f'[SISBAJUD] ✅ Encontrados {len(reus_restantes_carregados)} réus restantes de processamento anterior')
                    print(f'[SISBAJUD] Usando réus restantes em vez dos dados originais do processo')
                    
                    # Substituir os réus pelos restantes
                    reus = reus_restantes_carregados
                    
                    # Remover o arquivo após carregar
                    os.remove(reus_restantes_arquivo)
                    print(f'[SISBAJUD] ✅ Arquivo de réus restantes removido após carregamento')
                else:
                    print('[SISBAJUD] ⚠️ Arquivo de réus restantes encontrado mas vazio')
            except Exception as e:
                print(f'[SISBAJUD] ❌ Erro ao carregar réus restantes: {e}')
        else:
            print('[SISBAJUD] ✅ Nenhum réu restante encontrado - processando todos os réus')
        
        # 2.2. Verificar se há valor de execução nos dados do processo
        print('[SISBAJUD] 2.2. Verificando valor de execução...')
        valor_execucao = dados_processo.get('parametros_automacao', {}).get('valor_execucao') or dados_processo.get('divida', {}).get('valor')
        
        if not valor_execucao or str(valor_execucao).strip() == '' or str(valor_execucao).strip() == '0' or str(valor_execucao).strip() == '0.00':
            print('[SISBAJUD] ⚠️ Valor de execução não encontrado nos dados do processo')
            print('[SISBAJUD] Criando GIGS "Bruna atualizar cálculos" e abortando processamento SISBAJUD...')
            
            try:
                # Importar função criar_gigs se necessário
                from Fix import criar_gigs
                
                # Criar GIGS para Bruna atualizar cálculos
                resultado_gigs = criar_gigs(driver_pje, "01", "Bruna", "atualizar cálculos", log=True)
                
                if resultado_gigs:
                    print('[SISBAJUD] ✅ GIGS criado com sucesso: 01/Bruna/atualizar cálculos')
                    return {
                        'status': 'gigs_criado',
                        'motivo': 'valor_execucao_ausente',
                        'gigs': '30/Bruna/atualizar cálculos'
                    }
                else:
                    print('[SISBAJUD] ❌ Falha ao criar GIGS')
                    return {
                        'status': 'erro_gigs',
                        'motivo': 'falha_criacao_gigs'
                    }
                    
            except Exception as e:
                print(f'[SISBAJUD] ❌ Erro ao criar GIGS: {e}')
                return {
                    'status': 'erro_gigs',
                    'motivo': str(e)
                }
        else:
            print(f'[SISBAJUD] ✅ Valor de execução encontrado: {valor_execucao}')
        
        # 3. Verificar se já estamos na página de cadastro ou navegar para /minuta
        current_url = driver_sisbajud.current_url
        print(f'[SISBAJUD] 3. URL atual: {current_url}')
        
        if '/minuta/cadastrar' in current_url:
            print('[SISBAJUD] ✅ Já estamos na página de cadastro de minuta')
            # Aguardar estabilização da página
            smart_delay('navigation')
        else:
            print('[SISBAJUD] 3. Navegando para página /minuta...')
            if not safe_navigate(driver_sisbajud, 'https://sisbajud.cnj.jus.br/minuta', 'navigation'):
                print('[SISBAJUD] ❌ Falha na navegação para /minuta')
                return None
            
            # Aguardar URL /minuta com delay inteligente
            minuta_indicator = 'sisbajud.cnj.jus.br/minuta'
            url_timeout = 30
            inicio_url = time.time()
            url_ready = False
            while time.time() - inicio_url < url_timeout:
                smart_delay('default', base_delay=0.5)  # Delay entre verificações
                current_url = driver_sisbajud.current_url
                if minuta_indicator in current_url:
                    print(f'[SISBAJUD] ✅ URL /minuta confirmada: {current_url}')
                    url_ready = True
                    break
            
            if not url_ready:
                print('[SISBAJUD] ❌ Timeout aguardando URL /minuta')
                return None
            
            # Aguardar estabilização da página antes de clicar em Nova Minuta
            print('[SISBAJUD] Aguardando estabilização da página...')
            smart_delay('navigation')
            
            print('[SISBAJUD] Clicando em "Nova Minuta"...')
            script = """
            var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
            if (!botaoNova) {
                botaoNova = document.querySelector('button.mat-fab.mat-primary');
            }
            if (botaoNova) {
                if (botaoNova.tagName === 'MAT-ICON') {
                    botaoNova = botaoNova.closest('button');
                }
                botaoNova.click();
                return true;
            }
            return false;
            """
            
            # Usar função segura para executar script
            sucesso = safe_execute_script(driver_sisbajud, script, 'click')
            if sucesso:
                print('[SISBAJUD] ✅ Botão "Nova Minuta" clicado com sucesso')
                smart_delay('form_fill')  # Aguardar carregamento do formulário
            else:
                print('[SISBAJUD] ❌ Falha ao clicar em "Nova Minuta"')
                return None
        
        # Verificar se agora estamos na página de cadastro
        current_url = driver_sisbajud.current_url
        if '/minuta/cadastrar' not in current_url:
            print(f'[SISBAJUD] ❌ Não conseguimos chegar à página de cadastro. URL atual: {current_url}')
            return None
        
        print('[SISBAJUD] ✅ Estamos na página de cadastro de minuta')
        
        # === REPRODUÇÃO EXATA DO GIGS.PY PARA MINUTA DE BLOQUEIO ===
        
        # Valores hardcoded (equivalentes às preferências do gigs.py)
        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        vara = dados_processo.get('sisbajud', {}).get('vara', '30006')
        numero_lista = dados_processo.get('numero', [])
        numero_processo = numero_lista[0] if numero_lista else ''
        
        # CPF/CNPJ e nome do autor
        cpf_cnpj_autor = ''
        nome_autor = ''
        if dados_processo.get('autor') and len(dados_processo['autor']) > 0:
            cpf_cnpj_autor = dados_processo['autor'][0].get('cpfcnpj', '')
            nome_autor = dados_processo['autor'][0].get('nome', '')
        elif dados_processo.get('reu') and len(dados_processo['reu']) > 0:
            cpf_cnpj_autor = dados_processo['reu'][0].get('cpfcnpj', '')
            nome_autor = dados_processo['reu'][0].get('nome', '')
        
        cpf_cnpj_limpo = cpf_cnpj_autor.replace('.', '').replace('-', '').replace('/', '')
        
        # Réus
        reus = dados_processo.get('reu', [])
        
        print('[SISBAJUD] === REPRODUÇÃO EXATA DO GIGS.PY ===')
        
        # 1. JUIZ SOLICITANTE - usando JavaScript como gigs.py
        print('[SISBAJUD] 1. Preenchendo Juiz Solicitante...')
        script_juiz = f"""
        var juizInput = document.querySelector('input[placeholder*="Juiz"]');
        if (juizInput) {{
            juizInput.focus();
            juizInput.value = '';
            juizInput.value = '{juiz}';
            juizInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            // Aguardar opções aparecerem
            setTimeout(function() {{
                var opcoes = document.querySelectorAll('mat-option[role="option"]');
                for (var i = 0; i < opcoes.length; i++) {{
                    if (opcoes[i].textContent.toLowerCase().includes('{juiz.lower()}')) {{
                        opcoes[i].click();
                        break;
                    }}
                }}
            }}, 500);
            return true;
        }}
        return false;
        """
        sucesso = safe_execute_script(driver_sisbajud, script_juiz, 'form_fill')
        if sucesso:
            print(f'[SISBAJUD] ✅ Juiz preenchido: {juiz}')
            smart_delay('form_fill')
        else:
            print('[SISBAJUD] ❌ Falha ao preencher juiz')
        
        # 2. VARA/JUÍZO - usando JavaScript como gigs.py
        print('[SISBAJUD] 2. Preenchendo Vara/Juízo...')
        script_vara = f"""
        var varaSelect = document.querySelector('mat-select[name*="varaJuizoSelect"]');
        if (varaSelect) {{
            varaSelect.focus();
            varaSelect.click();
            
            setTimeout(function() {{
                var opcoes = document.querySelectorAll('mat-option[role="option"]');
                for (var i = 0; i < opcoes.length; i++) {{
                    if (opcoes[i].textContent.includes('{vara}')) {{
                        opcoes[i].click();
                        break;
                    }}
                }}
            }}, 500);
            return true;
        }}
        return false;
        """
        sucesso = safe_execute_script(driver_sisbajud, script_vara, 'form_fill')
        if sucesso:
            print(f'[SISBAJUD] ✅ Vara preenchida: {vara}')
            smart_delay('form_fill')
        else:
            print('[SISBAJUD] ❌ Falha ao preencher vara')
        
        # 3. NÚMERO DO PROCESSO - usando JavaScript como gigs.py
        print('[SISBAJUD] 3. Preenchendo Número do Processo...')
        script_numero = f"""
        var numeroInput = document.querySelector('input[placeholder="Número do Processo"]');
        if (numeroInput) {{
            numeroInput.focus();
            numeroInput.value = '';
            numeroInput.value = '{numero_processo}';
            numeroInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            numeroInput.blur();
            return true;
        }}
        return false;
        """
        sucesso = safe_execute_script(driver_sisbajud, script_numero, 'form_fill')
        if sucesso:
            print(f'[SISBAJUD] ✅ Número do processo preenchido: {numero_processo}')
            smart_delay('form_fill', base_delay=0.8)
        else:
            print('[SISBAJUD] ❌ Falha ao preencher número do processo')
        
        # 4. TIPO DE AÇÃO - usando JavaScript como gigs.py
        print('[SISBAJUD] 4. Preenchendo Tipo de Ação...')
        script_acao = """
        var acaoSelect = document.querySelector('mat-select[name*="acao"]');
        if (acaoSelect) {
            acaoSelect.focus();
            acaoSelect.click();
            
            setTimeout(function() {
                var opcoes = document.querySelectorAll('mat-option[role="option"]');
                for (var i = 0; i < opcoes.length; i++) {
                    if (opcoes[i].textContent.includes('Ação Trabalhista')) {
                        opcoes[i].click();
                        break;
                    }
                }
            }, 500);
            return true;
        }
        return false;
        """
        sucesso = safe_execute_script(driver_sisbajud, script_acao, 'form_fill')
        if sucesso:
            print('[SISBAJUD] ✅ Tipo de ação preenchido: Ação Trabalhista')
            smart_delay('form_fill')
        else:
            print('[SISBAJUD] ❌ Falha ao preencher tipo de ação')
        
        # 5. CPF/CNPJ DO AUTOR - usando JavaScript como gigs.py
        print('[SISBAJUD] 5. Preenchendo CPF/CNPJ do Autor...')
        script_cpf = f"""
        var cpfInput = document.querySelector('input[placeholder*="CPF"]');
        if (cpfInput) {{
            cpfInput.focus();
            setTimeout(function() {{
                cpfInput.value = '';
                cpfInput.value = '{cpf_cnpj_limpo}';
                cpfInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                cpfInput.blur();
            }}, 250);
            return true;
        }}
        return false;
        """
        sucesso = driver_sisbajud.execute_script(script_cpf)
        if sucesso:
            print(f'[SISBAJUD] ✅ CPF/CNPJ do autor preenchido: {cpf_cnpj_limpo}')
            time.sleep(0.5)
        else:
            print('[SISBAJUD] ❌ Falha ao preencher CPF/CNPJ do autor')
        
        # 6. NOME DO AUTOR - usando JavaScript como gigs.py
        print('[SISBAJUD] 6. Preenchendo Nome do Autor...')
        script_nome = f"""
        var nomeInput = document.querySelector('input[placeholder="Nome do autor/exequente da ação"]');
        if (nomeInput) {{
            nomeInput.focus();
            setTimeout(function() {{
                nomeInput.value = '';
                nomeInput.value = '{nome_autor}';
                nomeInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                nomeInput.blur();
            }}, 250);
            return true;
        }}
        return false;
        """
        sucesso = driver_sisbajud.execute_script(script_nome)
        if sucesso:
            print(f'[SISBAJUD] ✅ Nome do autor preenchido: {nome_autor}')
            time.sleep(0.5)
        else:
            print('[SISBAJUD] ❌ Falha ao preencher nome do autor')
        
        # 7. TEIMOSINHA - usando JavaScript como gigs.py
        print('[SISBAJUD] 7. Selecionando Teimosinha (Repetir a ordem)...')
        script_teimosinha = """
        var radios = document.querySelectorAll('mat-radio-button');
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].textContent.includes('Repetir a ordem')) {
                var label = radios[i].querySelector('label');
                if (label) {
                    label.click();
                    return true;
                }
            }
        }
        return false;
        """
        sucesso = driver_sisbajud.execute_script(script_teimosinha)
        if sucesso:
            print('[SISBAJUD] ✅ Teimosinha selecionada: Repetir a ordem')
        else:
            print('[SISBAJUD] ❌ Falha ao selecionar teimosinha')
        
        # 8. CALENDÁRIO - lógica exata do gigs.py
        print('[SISBAJUD] 8. Configurando Calendário...')
        
        # Validar prazo_dias (apenas 30 ou 60 dias permitidos)
        if prazo_dias not in [30, 60]:
            print(f'[SISBAJUD] ⚠️ Prazo inválido ({prazo_dias} dias). Usando padrão de 30 dias.')
            prazo_dias = 30
        
        # Calcular data: hoje + prazo_dias + 2 extras
        numdias = prazo_dias
        hoje = datetime.now()
        data_fim = hoje + timedelta(days=numdias + 2)
        
        print(f'[SISBAJUD] Prazo configurado: {prazo_dias} dias (+ 2 dias extras)')
        print(f'[SISBAJUD] Data calculada: {data_fim.strftime("%d/%m/%Y")}')
        
        ano = data_fim.year
        mes_d = data_fim.month - 1  # Month index (0-11 como no JS)
        dia_d = data_fim.day
        
        # Abrir calendário
        script_abrir_calendario = """
        var btnCalendario = document.querySelector('button[aria-label="Open calendar"]');
        if (btnCalendario) {
            btnCalendario.click();
            return true;
        }
        return false;
        """
        sucesso = driver_sisbajud.execute_script(script_abrir_calendario)
        if sucesso:
            print('[SISBAJUD] ✅ Calendário aberto')
            time.sleep(1)
        else:
            print('[SISBAJUD] ❌ Falha ao abrir calendário')
            return None
        
        # Abrir seleção mês/ano
        script_mes_ano = """
        var btnMesAno = document.querySelector('mat-calendar button[aria-label="Choose month and year"]');
        if (btnMesAno) {
            btnMesAno.click();
            return true;
        }
        return false;
        """
        sucesso = driver_sisbajud.execute_script(script_mes_ano)
        if sucesso:
            print('[SISBAJUD] ✅ Seleção mês/ano aberta')
            time.sleep(1)
        else:
            print('[SISBAJUD] ❌ Falha ao abrir seleção mês/ano')
            return None
        
        # Selecionar ano
        script_ano = f"""
        var anoCell = document.querySelector('mat-calendar td[aria-label="{ano}"]');
        if (anoCell) {{
            anoCell.click();
            return true;
        }}
        return false;
        """
        sucesso = driver_sisbajud.execute_script(script_ano)
        if sucesso:
            print(f'[SISBAJUD] ✅ Ano selecionado: {ano}')
            time.sleep(1)
        else:
            print(f'[SISBAJUD] ❌ Falha ao selecionar ano: {ano}')
            return None
        
        # Lógica de mês como gigs.py
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        
        mes_encontrado = False
        mes_atual = mes_d
        
        while mes_atual >= 0:
            mes_str = f"{meses[mes_atual]} de {ano}"
            print(f'[SISBAJUD] Tentando mês: {mes_str}')
            
            script_mes = f"""
            var mesCell = document.querySelector('mat-calendar td[aria-label="{mes_str}"]');
            if (mesCell && !mesCell.getAttribute('aria-disabled')) {{
                mesCell.click();
                return true;
            }}
            return false;
            """
            sucesso = driver_sisbajud.execute_script(script_mes)
            if sucesso:
                print(f'[SISBAJUD] ✅ Mês selecionado: {mes_str}')
                mes_encontrado = True
                break
            else:
                dia_d = 31
            
            mes_atual -= 1
        
        if not mes_encontrado:
            print('[SISBAJUD] ❌ Nenhum mês disponível')
            return None
        
        time.sleep(1)
        
        # Lógica de dia como gigs.py
        mes_final_str = f"{meses[mes_atual]} de {ano}"
        dia_encontrado = False
        
        while dia_d > 0:
            dia_str = f"{dia_d} de {mes_final_str}"
            print(f'[SISBAJUD] Tentando dia: {dia_d}')
            
            script_dia = f"""
            var diaCell = document.querySelector('mat-calendar td[aria-label="{dia_str}"]');
            if (diaCell && !diaCell.getAttribute('aria-disabled')) {{
                diaCell.click();
                return true;
            }}
            return false;
            """
            sucesso = driver_sisbajud.execute_script(script_dia)
            if sucesso:
                print(f'[SISBAJUD] ✅ Dia selecionado: {dia_d}')
                dia_encontrado = True
                break
            
            dia_d -= 1
        
        if not dia_encontrado:
            print('[SISBAJUD] ❌ Nenhum dia disponível')
            return None
        
        data_limite_str = datetime(ano, mes_atual + 1, dia_d).strftime('%d/%m/%Y')
        print(f'[SISBAJUD] ✅ Data final selecionada: {data_limite_str}')
        
        # 9. INSERÇÃO DOS RÉUS/EXECUTADOS - usando seletores corretos como gigs.py
        print('[SISBAJUD] 9. Inserindo Réus/Executados...')
        
        if not reus:
            print('[SISBAJUD] ❌ Nenhum réu encontrado')
            return None
        
        print(f'[SISBAJUD] Total de réus: {len(reus)}')
        
        # NOVO: Limitar a 10 executados ativos por minuta
        MAX_EXECUTADOS_POR_MINUTA = 10
        executados_ativos = 0
        executados_processados = 0
        reus_restantes = []
        
        for contador, reu in enumerate(reus):
            print(f'\n[SISBAJUD] === PROCESSANDO RÉU {contador + 1}/{len(reus)} ===')
            
            # Verificar se já atingimos o limite de 10 executados ativos
            if executados_ativos >= MAX_EXECUTADOS_POR_MINUTA:
                print(f'[SISBAJUD] ⚠️ Limite de {MAX_EXECUTADOS_POR_MINUTA} executados ativos atingido')
                print(f'[SISBAJUD] Restantes serão processados em nova ordem')
                reus_restantes = reus[contador:]
                break
            
            cpf_cnpj_reu = reu.get('cpfcnpj', '')
            if not cpf_cnpj_reu:
                print(f'[SISBAJUD] ⚠️ Réu {contador + 1} sem CPF/CNPJ, pulando...')
                continue
            
            nome_reu = reu.get('nome', '')
            cpf_cnpj_reu_limpo = ''.join(filter(str.isdigit, cpf_cnpj_reu))
            
            # Para minuta de bloqueio, sempre usar apenas raiz do CNPJ (antes de 000)
            valor_final = cpf_cnpj_reu_limpo
            if len(cpf_cnpj_reu_limpo) == 14:  # É CNPJ
                valor_final = cpf_cnpj_reu_limpo[:8]  # Sempre usar apenas a raiz para bloqueio
                print(f'[SISBAJUD] CNPJ detectado: {cpf_cnpj_reu_limpo} -> usando raiz: {valor_final}')
            else:
                print(f'[SISBAJUD] CPF detectado: {valor_final}')
            
            print(f'[SISBAJUD] Adicionando réu {contador + 1}: {nome_reu} ({valor_final})')
            
            # Delay maior entre adição de réus para evitar rate limiting
            if contador > 0:
                print(f'[SISBAJUD] Aguardando entre réus para evitar bloqueio...')
                smart_delay('form_fill', base_delay=2.0)
            
            # Script corrigido usando os seletores exatos fornecidos
            script_reu = f"""
            // Buscar campo de entrada com seletor específico
            var cpfInput = document.querySelector('input[placeholder="CPF/CNPJ do réu/executado"]');
            if (!cpfInput) {{
                // Fallback para seletor mais genérico
                cpfInput = document.querySelector('input.mat-input-element[cpfcnpjmask]');
            }}
            
            if (cpfInput) {{
                // Focar e limpar campo
                cpfInput.focus();
                cpfInput.value = '';
                
                // Aguardar um pouco e preencher (como gigs.py)
                setTimeout(function() {{
                    cpfInput.value = '{valor_final}';
                    cpfInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    cpfInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    // Aguardar e clicar no botão de adicionar
                    setTimeout(function() {{
                        // Buscar botão com seletor específico 
                        var btnAdicionar = document.querySelector('button.btn-adicionar.mat-mini-fab');
                        if (!btnAdicionar) {{
                            // Fallback para ícone específico
                            btnAdicionar = document.querySelector('button mat-icon.fa-plus-square');
                            if (btnAdicionar) {{
                                btnAdicionar = btnAdicionar.closest('button');
                            }}
                        }}
                        
                        if (btnAdicionar && !btnAdicionar.disabled) {{
                            btnAdicionar.click();
                            return true;
                        }}
                        return false;
                    }}, 800);  // Aumentado de 500 para 800ms
                }}, 400);      // Aumentado de 200 para 400ms
                return true;
            }}
            return false;
            """
            
            # Executar script com função segura
            sucesso = safe_execute_script(driver_sisbajud, script_reu, 'form_fill')
            if sucesso:
                print(f'[SISBAJUD] ✅ Script de adição do réu {contador + 1} executado')
                
                # Aguardar processamento com delay inteligente
                smart_delay('form_fill', base_delay=3.0)  # Aumentado para 3 segundos
                
                # NOVO: Verificar imediatamente se o réu tem 0 contas e remover se necessário
                script_verificar_contas = """
                // Verificar se o último réu adicionado tem 0 relacionamentos
                var tabelaLinhas = document.querySelectorAll('tr.mat-row');
                if (tabelaLinhas.length > 0) {
                    var ultimaLinha = tabelaLinhas[tabelaLinhas.length - 1];
                    var celulaRelacionamentos = ultimaLinha.querySelector('td.mat-column-qtdeRelacionamentos');
                    if (celulaRelacionamentos) {
                        var botaoRelacionamentos = celulaRelacionamentos.querySelector('button .mat-button-wrapper');
                        if (botaoRelacionamentos && botaoRelacionamentos.textContent.trim() === '0') {
                            // Encontrou 0 relacionamentos - remover imediatamente
                            var botaoMenu = ultimaLinha.querySelector('button.mat-menu-trigger');
                            if (botaoMenu) {
                                botaoMenu.click();
                                return 'REMOVER_AGORA';
                            }
                        } else {
                            // Tem relacionamentos - contar como ativo
                            return 'EXECUTADO_ATIVO';
                        }
                    }
                }
                return 'VERIFICACAO_INCONCLUSIVA';
                """
                
                resultado_verificacao = safe_execute_script(driver_sisbajud, script_verificar_contas, 'default')
                
                if resultado_verificacao == 'REMOVER_AGORA':
                    print(f'[SISBAJUD] ⚠️ Réu {contador + 1} tem 0 contas - removendo imediatamente...')
                    
                    # Aguardar menu abrir e clicar em excluir
                    time.sleep(0.5)
                    script_excluir_zero_contas = """
                    var botaoExcluir = document.querySelector('button.mat-menu-item mat-icon.fa-trash-alt');
                    if (botaoExcluir) {
                        botaoExcluir.closest('button').click();
                        return true;
                    }
                    return false;
                    """
                    
                    excluiu = driver_sisbajud.execute_script(script_excluir_zero_contas)
                    if excluiu:
                        print(f'[SISBAJUD] ✅ Réu {contador + 1} com 0 contas removido imediatamente')
                        time.sleep(1)  # Aguardar processamento
                        continue  # Pular para o próximo réu
                    else:
                        print(f'[SISBAJUD] ❌ Falha ao remover réu {contador + 1} com 0 contas')
                        
                elif resultado_verificacao == 'EXECUTADO_ATIVO':
                    executados_ativos += 1
                    print(f'[SISBAJUD] ✅ Réu {contador + 1} adicionado como executado ativo ({executados_ativos}/{MAX_EXECUTADOS_POR_MINUTA})')
                
                executados_processados += 1
                verificar_erro = """
                // Verificar se há mensagem de erro
                var errorMsg = document.querySelector('.mat-snack-bar-container');
                if (errorMsg && errorMsg.textContent) {
                    return errorMsg.textContent;
                }
                
                // Verificar se o campo foi limpo (indicando sucesso)
                var cpfInput = document.querySelector('input[placeholder="CPF/CNPJ do réu/executado"]');
                if (cpfInput && cpfInput.value === '') {
                    return 'SUCCESS';
                }
                
                return 'UNKNOWN';
                """
                
                resultado = safe_execute_script(driver_sisbajud, verificar_erro, 'default')
                
                if resultado == 'SUCCESS':
                    print(f'[SISBAJUD] ✅ Réu {contador + 1} adicionado com sucesso (campo limpo)')
                    # Reset contador de erros em caso de sucesso
                    SISBAJUD_STATS['consecutive_errors'] = 0
                elif resultado and ('erro' in str(resultado).lower() or 'inválido' in str(resultado).lower()):
                    print(f'[SISBAJUD] ❌ Erro ao adicionar réu {contador + 1}: {resultado}')
                    SISBAJUD_STATS['consecutive_errors'] += 1
                else:
                    print(f'[SISBAJUD] ⚠️ Status desconhecido para réu {contador + 1}: {resultado}')
                
            else:
                print(f'[SISBAJUD] ❌ Falha ao executar script para réu {contador + 1}')
                SISBAJUD_STATS['consecutive_errors'] += 1
        
        # Se há réus restantes, criar nova ordem
        if reus_restantes:
            print(f'\n[SISBAJUD] === CRIANDO NOVA ORDEM PARA {len(reus_restantes)} RÉUS RESTANTES ===')
            print(f'[SISBAJUD] Executados ativos nesta minuta: {executados_ativos}')
            print(f'[SISBAJUD] Réus restantes para próxima ordem: {len(reus_restantes)}')
            
            # Salvar dados dos réus restantes para próxima execução
            try:
                dados_restantes = {
                    'reus_restantes': reus_restantes,
                    'numero_processo': numero_processo,
                    'data_criacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'executados_ativos': executados_ativos,
                    'total_reus_original': len(reus)
                }
                
                restantes_path = os.path.join(os.path.dirname(__file__), f'reus_restantes_{numero_processo}.json')
                with open(restantes_path, 'w', encoding='utf-8') as f:
                    json.dump(dados_restantes, f, ensure_ascii=False, indent=2)
                
                print(f'[SISBAJUD] ✅ Dados dos réus restantes salvos em: {restantes_path}')
                print(f'[SISBAJUD] 💡 Para processar os restantes, chame minuta_bloqueio novamente')
                
            except Exception as e:
                print(f'[SISBAJUD] ❌ Erro ao salvar dados dos réus restantes: {e}')
        
        # Remover a lógica antiga de verificação/removal em lote (já foi integrada acima)
        print('[SISBAJUD] ✅ Processamento individual de réus concluído')
        
        # 10. VALOR (se houver)
        print('[SISBAJUD] 10. Configurando Valor...')
        if dados_processo.get('divida', {}).get('valor'):
            # Dados já vêm formatados do Fix.py
            valor_formatado = dados_processo['divida']['valor']
            data_divida_formatada = dados_processo.get('divida', {}).get('data', '')
            
            print(f'[SISBAJUD] Valor encontrado: {valor_formatado}')
            print(f'[SISBAJUD] Data da dívida: {data_divida_formatada}')
            
            # Criar span clicável como gigs.py com formatação correta
            script_valor = f"""
            var ancora = document.querySelector('div[class="label-valor-extenso"]');
            if (ancora && !document.getElementById('maisPJe_valor_execucao')) {{
                var span = document.createElement('span');
                span.id = 'maisPJe_valor_execucao';
                span.innerText = "Última atualização do processo: {valor_formatado} em {data_divida_formatada}";
                span.style = "color: white; background-color: slategray; padding: 10px; border-radius: 10px; cursor: pointer; font-weight: bold; margin: 5px 0;";
                span.onclick = function() {{
                    var input = document.querySelector('input[placeholder*="Valor aplicado a todos"]');
                    if (input) {{
                        input.value = "{valor_formatado}";
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }};
                ancora.appendChild(document.createElement('br'));
                ancora.appendChild(document.createElement('br'));
                ancora.appendChild(span);
            }}
            return true;
            """
            driver_sisbajud.execute_script(script_valor)
            print('[SISBAJUD] ✅ Span de valor criado com formatação correta')
            
            # Aguardar um pouco e clicar no overlay para inserir o valor
            time.sleep(1)
            print('[SISBAJUD] 10.1. Clicando no overlay para inserir valor...')
            
            script_clicar_overlay = """
            var overlay = document.getElementById('maisPJe_valor_execucao');
            if (overlay) {
                overlay.click();
                return true;
            }
            return false;
            """
            
            clicou_overlay = driver_sisbajud.execute_script(script_clicar_overlay)
            if clicou_overlay:
                print('[SISBAJUD] ✅ Overlay de valor clicado')
                time.sleep(1)
                
                # Clicar no botão de adicionar valor (seletor específico para valor)
                print('[SISBAJUD] 10.2. Clicando no botão de adicionar valor...')
                script_adicionar_valor = """
                var botaoAdicionar = document.querySelector('button.btn-adicionar.mat-mini-fab.mat-primary mat-icon.fa-check-square');
                if (botaoAdicionar) {
                    botaoAdicionar.closest('button').click();
                    return true;
                }
                
                // Fallback: buscar por qualquer botão com ícone de check-square
                var botaoFallback = document.querySelector('button.mat-mini-fab mat-icon.fa-check-square');
                if (botaoFallback) {
                    botaoFallback.closest('button').click();
                    return true;
                }
                
                return false;
                """
                
                adicionou_valor = driver_sisbajud.execute_script(script_adicionar_valor)
                if adicionou_valor:
                    print('[SISBAJUD] ✅ Valor adicionado com sucesso')
                else:
                    print('[SISBAJUD] ❌ Falha ao adicionar valor - botão não encontrado')
                    
            else:
                print('[SISBAJUD] ❌ Falha ao clicar no overlay de valor')
        else:
            # NOVA LÓGICA: Se valor da dívida não foi localizado, executar apenas criar_gigs
            print('[SISBAJUD] ⚠️ Valor da dívida não localizado - executando criar_gigs')
            try:
                # Sair do SISBAJUD e voltar para PJE para criar GIGS
                if driver_pje:
                    print('[SISBAJUD] Retornando para PJE para criar GIGS...')
                    driver_pje.switch_to.window(driver_pje.window_handles[0])  # Volta para PJE
                    criar_gigs(driver_pje, "1", "Bruna", "Atualizar")
                    print('[SISBAJUD] ✅ GIGS criado: 1/Bruna/Atualizar')
                    return "gigs_criado"  # Retorna status especial
                else:
                    print('[SISBAJUD] ❌ Driver PJE não disponível para criar GIGS')
                    return None
            except Exception as e:
                print(f'[SISBAJUD] ❌ Erro ao criar GIGS: {e}')
                return None
        
        # 11. CONTA-SALÁRIO (se configurado)
        print('[SISBAJUD] 11. Configurando Conta-Salário...')
        if dados_processo.get('sisbajud', {}).get('contasalario', '').lower() == 'sim':
            script_conta_salario = """
            var toggles = document.querySelectorAll('mat-slide-toggle label');
            for (var i = 0; i < toggles.length; i++) {
                toggles[i].click();
            }
            return true;
            """
            driver_sisbajud.execute_script(script_conta_salario)
            print('[SISBAJUD] ✅ Conta-salário ativada')
        
        # 12. SALVAR MINUTA (OBRIGATÓRIO)
        print('[SISBAJUD] 12. Salvando Minuta...')
        
        script_salvar = """
        // Buscar botão de salvar com seletor específico
        var btnSalvar = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save');
        if (btnSalvar) {
            btnSalvar.closest('button').click();
            return true;
        }
        
        // Fallback: buscar por qualquer botão com ícone de save
        var btnFallback = document.querySelector('button mat-icon.fa-save');
        if (btnFallback) {
            btnFallback.closest('button').click();
            return true;
        }
        
        // Fallback 2: buscar por texto "Salvar"
        var buttons = document.querySelectorAll('button');
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i].textContent.includes('Salvar')) {
                buttons[i].click();
                return true;
            }
        }
        
        return false;
        """
        
        salvou = driver_sisbajud.execute_script(script_salvar)
        if salvou:
            print('[SISBAJUD] ✅ Botão Salvar clicado')
            
            # Aguardar salvamento e verificar confirmação
            print('[SISBAJUD] 12.1. Aguardando confirmação do salvamento...')
            time.sleep(3)
            
            # Verificar se apareceu o botão "Alterar" (confirmação de que foi salvo)
            script_verificar_salvamento = """
            // Buscar botão "Alterar" como confirmação
            var btnAlterar = document.querySelector('button mat-icon.fa-edit');
            if (btnAlterar) {
                var btnTexto = btnAlterar.closest('button');
                if (btnTexto && btnTexto.textContent.includes('Alterar')) {
                    return 'SALVO_COM_SUCESSO';
                }
            }
            
            // Verificar se ainda está na página de edição (não salvou)
            var btnSalvar = document.querySelector('button mat-icon.fa-save');
            if (btnSalvar) {
                return 'AINDA_EDITANDO';
            }
            
            return 'STATUS_DESCONHECIDO';
            """
            
            status_salvamento = driver_sisbajud.execute_script(script_verificar_salvamento)
            
            if status_salvamento == 'SALVO_COM_SUCESSO':
                print('[SISBAJUD] ✅ Minuta salva com sucesso! Botão "Alterar" detectado.')
                
                # === NOVA FASE: PROTOCOLAR MINUTA ===
                print('[SISBAJUD] === NOVA FASE: PROTOCOLAR MINUTA ===')
                
                # 1. Clicar no botão "Protocolar Minuta"
                print('[SISBAJUD] 1. Clicando no botão "Protocolar Minuta"...')
                script_protocolar = """
                var btnProtocolar = document.querySelector('button.mat-fab[title="Protocolar Minuta"]');
                if (btnProtocolar) {
                    btnProtocolar.click();
                    return true;
                }
                return false;
                """
                sucesso_protocolar = safe_execute_script(driver_sisbajud, script_protocolar, 'click')
                if sucesso_protocolar:
                    print('[SISBAJUD] ✅ Botão "Protocolar Minuta" clicado')
                    smart_delay('navigation')
                else:
                    print('[SISBAJUD] ❌ Falha ao clicar no botão "Protocolar Minuta"')
                    return None
                
                # 2. Aguardar modal de protocolo aparecer
                print('[SISBAJUD] 2. Aguardando modal de protocolo...')
                modal_apareceu = False
                for tentativa in range(10):
                    try:
                        modal = driver_sisbajud.find_element(By.CSS_SELECTOR, 'mat-dialog-container')
                        if modal.is_displayed():
                            print('[SISBAJUD] ✅ Modal de protocolo detectado')
                            modal_apareceu = True
                            break
                    except:
                        pass
                    time.sleep(0.5)
                
                if not modal_apareceu:
                    print('[SISBAJUD] ❌ Modal de protocolo não apareceu')
                    return None
                
                # 3. Digitar senha de forma humana (simulando erros como no login SISBAJUD)
                print('[SISBAJUD] 3. Digitando senha de forma humana...')
                senha = "Fl\"quinho182"
                
                # Simular digitação humana com possíveis erros
                script_senha = f"""
                var inputSenha = document.querySelector('input[formcontrolname="senha"]');
                if (inputSenha) {{
                    inputSenha.focus();
                    
                    // Simular digitação humana com atrasos e possíveis erros
                    var senha = "{senha}";
                    var erros = ["F", "Fl", "Fl\"", "Fl\"q", "Fl\"qu", "Fl\"qui", "Fl\"quin", "Fl\"quinh"]; // Simular erros de digitação
                    
                    // Escolher se vai cometer erro (30% de chance)
                    var cometerErro = Math.random() < 0.3;
                    
                    if (cometerErro) {{
                        // Digitar com erro e corrigir
                        var erroEscolhido = erros[Math.floor(Math.random() * erros.length)];
                        for (var i = 0; i < erroEscolhido.length; i++) {{
                            inputSenha.value += erroEscolhido[i];
                            inputSenha.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            // Delay entre caracteres
                            var delay = 100 + Math.random() * 200;
                            setTimeout(function(){{}}, delay);
                        }}
                        // Apagar erro
                        setTimeout(function() {{
                            for (var i = 0; i < erroEscolhido.length; i++) {{
                                inputSenha.value = inputSenha.value.slice(0, -1);
                                inputSenha.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                var delay = 50 + Math.random() * 100;
                                setTimeout(function(){{}}, delay);
                            }}
                        }}, 500);
                        
                        // Aguardar correção e digitar correto
                        setTimeout(function() {{
                            for (var i = 0; i < senha.length; i++) {{
                                inputSenha.value += senha[i];
                                inputSenha.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                var delay = 100 + Math.random() * 200;
                                setTimeout(function(){{}}, delay);
                            }}
                        }}, 1000);
                    }} else {{
                        // Digitar diretamente
                        for (var i = 0; i < senha.length; i++) {{
                            inputSenha.value += senha[i];
                            inputSenha.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            var delay = 100 + Math.random() * 200;
                            setTimeout(function(){{}}, delay);
                        }}
                    }}
                    
                    return true;
                }}
                return false;
                """
                
                sucesso_senha = driver_sisbajud.execute_script(script_senha)
                if sucesso_senha:
                    print('[SISBAJUD] ✅ Senha digitada (com simulação humana)')
                    time.sleep(2)  # Aguardar digitação completar
                else:
                    print('[SISBAJUD] ❌ Falha ao digitar senha')
                    return None
                
                # 4. Clicar em "Confirmar"
                print('[SISBAJUD] 4. Clicando em "Confirmar"...')
                script_confirmar = """
                var btnConfirmar = document.querySelector('button.mat-raised-button.mat-primary[type="submit"]');
                if (btnConfirmar && !btnConfirmar.disabled) {
                    btnConfirmar.click();
                    return true;
                }
                return false;
                """
                sucesso_confirmar = safe_execute_script(driver_sisbajud, script_confirmar, 'click')
                if sucesso_confirmar:
                    print('[SISBAJUD] ✅ Botão "Confirmar" clicado')
                    smart_delay('navigation')
                else:
                    print('[SISBAJUD] ❌ Falha ao clicar em "Confirmar"')
                    return None
                
                # 5. Aguardar processamento e coletar dados atualizados com protocolo
                print('[SISBAJUD] 5. Aguardando processamento e coletando dados atualizados...')
                time.sleep(5)  # Aguardar processamento
                
                # Extrair protocolo e data do protocolo
                script_extrair_protocolo = """
                try {
                    var protocoloElement = document.querySelector('span.sisbajud-label-valor.maisPJe_destaque_elemento');
                    var protocolo = protocoloElement ? protocoloElement.textContent.trim() : null;
                    
                    var dataElement = document.querySelector('span.sisbajud-label-valor');
                    var dataProtocolo = null;
                    if (dataElement && dataElement.textContent.includes('SET')) {
                        // Padronizar data para dd/mm/yy
                        var dataTexto = dataElement.textContent.trim();
                        var match = dataTexto.match(/(\\d{1,2})\\s+(\\w{3})\\s+(\\d{4})/);
                        if (match) {
                            var dia = match[1].padStart(2, '0');
                            var mes = match[2].toUpperCase();
                            var ano = match[3].slice(-2);
                            var meses = {'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04', 'MAI': '05', 'JUN': '06',
                                       'JUL': '07', 'AGO': '08', 'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'};
                            dataProtocolo = dia + '/' + meses[mes] + '/' + ano;
                        }
                    }
                    
                    return {protocolo: protocolo, dataProtocolo: dataProtocolo};
                } catch (e) {
                    return {erro: e.message};
                }
                """
                
                dados_protocolo = driver_sisbajud.execute_script(script_extrair_protocolo)
                protocolo_primeira = dados_protocolo.get('protocolo') if dados_protocolo else None
                data_protocolo = dados_protocolo.get('dataProtocolo') if dados_protocolo else None
                
                print(f'[SISBAJUD] ✅ Protocolo primeira minuta: {protocolo_primeira}')
                print(f'[SISBAJUD] ✅ Data do protocolo: {data_protocolo}')
                
                # === NOVA FASE: COPIAR DADOS PARA NOVA ORDEM ===
                print('[SISBAJUD] === NOVA FASE: COPIAR DADOS PARA NOVA ORDEM ===')
                
                # 6. Clicar em "Copiar Dados para Nova Ordem"
                print('[SISBAJUD] 6. Clicando em "Copiar Dados para Nova Ordem"...')
                script_copiar = """
                var btnCopiar = document.querySelector('button.mat-fab[title="Copiar Dados para Nova Ordem"]');
                if (btnCopiar) {
                    btnCopiar.click();
                    return true;
                }
                return false;
                """
                sucesso_copiar = safe_execute_script(driver_sisbajud, script_copiar, 'click')
                if sucesso_copiar:
                    print('[SISBAJUD] ✅ Botão "Copiar Dados para Nova Ordem" clicado')
                    smart_delay('navigation')
                else:
                    print('[SISBAJUD] ❌ Falha ao clicar no botão "Copiar Dados para Nova Ordem"')
                    return None
                
                # 7. Aguardar modal de confirmação e clicar em "Confirmar"
                print('[SISBAJUD] 7. Aguardando modal de confirmação...')
                modal_confirmacao_apareceu = False
                for tentativa in range(10):
                    try:
                        modal_confirmacao = driver_sisbajud.find_element(By.CSS_SELECTOR, 'mat-dialog-container')
                        if modal_confirmacao.is_displayed():
                            print('[SISBAJUD] ✅ Modal de confirmação detectado')
                            modal_confirmacao_apareceu = True
                            break
                    except:
                        pass
                    time.sleep(0.5)
                
                if modal_confirmacao_apareceu:
                    script_confirmar_copia = """
                    var btnConfirmarCopia = document.querySelector('button.mat-raised-button.mat-primary');
                    if (btnConfirmarCopia && btnConfirmarCopia.textContent.includes('Confirmar')) {
                        btnConfirmarCopia.click();
                        return true;
                    }
                    return false;
                    """
                    sucesso_confirmar_copia = safe_execute_script(driver_sisbajud, script_confirmar_copia, 'click')
                    if sucesso_confirmar_copia:
                        print('[SISBAJUD] ✅ Confirmação de cópia clicada')
                        smart_delay('navigation')
                    else:
                        print('[SISBAJUD] ❌ Falha ao confirmar cópia')
                        return None
                else:
                    print('[SISBAJUD] ❌ Modal de confirmação não apareceu')
                    return None
                
                # 8. Aguardar URL /copiar-ordem
                print('[SISBAJUD] 8. Aguardando navegação para /copiar-ordem...')
                url_copiar_ready = False
                for tentativa in range(20):
                    current_url = driver_sisbajud.current_url
                    if '/copiar-ordem' in current_url:
                        print('[SISBAJUD] ✅ URL /copiar-ordem confirmada')
                        url_copiar_ready = True
                        break
                    time.sleep(0.5)
                
                if not url_copiar_ready:
                    print('[SISBAJUD] ❌ Timeout aguardando URL /copiar-ordem')
                    return None
                
                # 9. Preencher dados que faltam na segunda minuta
                print('[SISBAJUD] 9. Preenchendo dados da segunda minuta...')
                
                # 9.1. Juiz Solicitante (igual à primeira)
                print('[SISBAJUD] 9.1. Preenchendo Juiz Solicitante...')
                script_juiz_segunda = f"""
                var juizInput = document.querySelector('input[placeholder*="Juiz"]');
                if (juizInput) {{
                    juizInput.focus();
                    juizInput.value = '';
                    juizInput.value = '{juiz}';
                    juizInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    // Aguardar opções aparecerem
                    setTimeout(function() {{
                        var opcoes = document.querySelectorAll('mat-option[role="option"]');
                        for (var i = 0; i < opcoes.length; i++) {{
                            if (opcoes[i].textContent.toLowerCase().includes('{juiz.lower()}')) {{
                                opcoes[i].click();
                                break;
                            }}
                        }}
                    }}, 500);
                    return true;
                }}
                return false;
                """
                sucesso_juiz_segunda = safe_execute_script(driver_sisbajud, script_juiz_segunda, 'form_fill')
                if sucesso_juiz_segunda:
                    print(f'[SISBAJUD] ✅ Juiz preenchido na segunda minuta: {juiz}')
                    smart_delay('form_fill')
                
                # 9.2. Selecionar "Sim" no radio button de agendar protocolo da minuta
                print('[SISBAJUD] 9.2. Selecionando "Sim" para agendar protocolo da minuta...')
                script_radio_sim = """
                var radios = document.querySelectorAll('mat-radio-button');
                for (var i = 0; i < radios.length; i++) {
                    var label = radios[i].querySelector('label');
                    if (label && label.textContent.includes('Sim')) {
                        label.click();
                        return true;
                    }
                }
                return false;
                """
                sucesso_radio = safe_execute_script(driver_sisbajud, script_radio_sim, 'click')
                if sucesso_radio:
                    print('[SISBAJUD] ✅ "Sim" selecionado para agendar protocolo da minuta')
                    smart_delay('form_fill')
                
                # 9.3. Abrir calendário e escolher dia seguinte útil
                print('[SISBAJUD] 9.3. Configurando data limite da repetição...')
                
                # Calcular dia seguinte útil (evitando sábado e domingo)
                hoje = datetime.now()
                dia_seguinte = hoje + timedelta(days=1)
                
                # Se for sábado, pular para segunda
                if dia_seguinte.weekday() == 5:  # Sábado
                    dia_seguinte += timedelta(days=2)
                elif dia_seguinte.weekday() == 6:  # Domingo
                    dia_seguinte += timedelta(days=1)
                
                ano_segunda = dia_seguinte.year
                mes_segunda = dia_seguinte.month - 1  # 0-based
                dia_segunda = dia_seguinte.day
                
                print(f'[SISBAJUD] Data limite segunda minuta: {dia_seguinte.strftime("%d/%m/%Y")}')
                
                # Abrir calendário
                script_abrir_calendario_segunda = """
                var btnCalendario = document.querySelector('button[aria-label="Open calendar"]');
                if (btnCalendario) {
                    btnCalendario.click();
                    return true;
                }
                return false;
                """
                sucesso_abrir_calendario = safe_execute_script(driver_sisbajud, script_abrir_calendario_segunda, 'click')
                if sucesso_abrir_calendario:
                    print('[SISBAJUD] ✅ Calendário aberto para segunda minuta')
                    time.sleep(1)
                    
                    # Abrir seleção mês/ano
                    script_mes_ano_segunda = """
                    var btnMesAno = document.querySelector('mat-calendar button[aria-label="Choose month and year"]');
                    if (btnMesAno) {
                        btnMesAno.click();
                        return true;
                    }
                    return false;
                    """
                    sucesso_mes_ano = safe_execute_script(driver_sisbajud, script_mes_ano_segunda, 'click')
                    if sucesso_mes_ano:
                        print('[SISBAJUD] ✅ Seleção mês/ano aberta')
                        time.sleep(1)
                        
                        # Selecionar ano
                        script_ano_segunda = f"""
                        var anoCell = document.querySelector('mat-calendar td[aria-label="{ano_segunda}"]');
                        if (anoCell) {{
                            anoCell.click();
                            return true;
                        }}
                        return false;
                        """
                        sucesso_ano_segunda = safe_execute_script(driver_sisbajud, script_ano_segunda, 'click')
                        if sucesso_ano_segunda:
                            print(f'[SISBAJUD] ✅ Ano selecionado: {ano_segunda}')
                            time.sleep(1)
                            
                            # Selecionar mês
                            meses_segunda = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
                                           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
                            mes_str_segunda = f"{meses_segunda[mes_segunda]} de {ano_segunda}"
                            
                            script_mes_segunda = f"""
                            var mesCell = document.querySelector('mat-calendar td[aria-label="{mes_str_segunda}"]');
                            if (mesCell && !mesCell.getAttribute('aria-disabled')) {{
                                mesCell.click();
                                return true;
                            }}
                            return false;
                            """
                            sucesso_mes_segunda = safe_execute_script(driver_sisbajud, script_mes_segunda, 'click')
                            if sucesso_mes_segunda:
                                print(f'[SISBAJUD] ✅ Mês selecionado: {mes_str_segunda}')
                                time.sleep(1)
                                
                                # Selecionar dia
                                script_dia_segunda = f"""
                                var diaCell = document.querySelector('mat-calendar td[aria-label="{dia_segunda}"]');
                                if (diaCell && !diaCell.getAttribute('aria-disabled')) {{
                                    diaCell.click();
                                    return true;
                                }}
                                return false;
                                """
                                sucesso_dia_segunda = safe_execute_script(driver_sisbajud, script_dia_segunda, 'click')
                                if sucesso_dia_segunda:
                                    print(f'[SISBAJUD] ✅ Dia selecionado: {dia_segunda}')
                                    smart_delay('form_fill')
                                else:
                                    print(f'[SISBAJUD] ❌ Falha ao selecionar dia: {dia_segunda}')
                            else:
                                print(f'[SISBAJUD] ❌ Falha ao selecionar mês: {mes_str_segunda}')
                        else:
                            print(f'[SISBAJUD] ❌ Falha ao selecionar ano: {ano_segunda}')
                    else:
                        print('[SISBAJUD] ❌ Falha ao abrir seleção mês/ano')
                else:
                    print('[SISBAJUD] ❌ Falha ao abrir calendário')
                
                # 9.4. Preencher valor da execução (igual ao da primeira)
                print('[SISBAJUD] 9.4. Preenchendo valor da execução...')
                script_valor_segunda = f"""
                var valorInput = document.querySelector('input[placeholder*="Valor aplicado a todos"]');
                if (valorInput) {{
                    valorInput.focus();
                    valorInput.value = '';
                    valorInput.value = '{valor_execucao}';
                    valorInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    valorInput.blur();
                    return true;
                }}
                return false;
                """
                sucesso_valor_segunda = safe_execute_script(driver_sisbajud, script_valor_segunda, 'form_fill')
                if sucesso_valor_segunda:
                    print(f'[SISBAJUD] ✅ Valor preenchido na segunda minuta: {valor_execucao}')
                    smart_delay('form_fill')
                
                # 9.5. Salvar segunda minuta
                print('[SISBAJUD] 9.5. Salvando segunda minuta...')
                script_salvar_segunda = """
                // Buscar botão de salvar
                var btnSalvar = document.querySelector('button.mat-fab.mat-primary mat-icon.fa-save');
                if (btnSalvar) {
                    btnSalvar.closest('button').click();
                    return true;
                }
                
                // Fallback
                var btnFallback = document.querySelector('button mat-icon.fa-save');
                if (btnFallback) {
                    btnFallback.closest('button').click();
                    return true;
                }
                
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].textContent.includes('Salvar')) {
                        buttons[i].click();
                        return true;
                    }
                }
                
                return false;
                """
                
                salvou_segunda = safe_execute_script(driver_sisbajud, script_salvar_segunda, 'click')
                if salvou_segunda:
                    print('[SISBAJUD] ✅ Botão Salvar segunda minuta clicado')
                    smart_delay('navigation')
                    
                    # Aguardar confirmação
                    time.sleep(3)
                    print('[SISBAJUD] ✅ Segunda minuta salva com sucesso')
                    
                    # Extrair protocolo da segunda minuta
                    try:
                        script_extrair_protocolo_segunda = """
                        var protocoloElement = document.querySelector('span.sisbajud-label-valor.maisPJe_destaque_elemento');
                        return protocoloElement ? protocoloElement.textContent.trim() : null;
                        """
                        protocolo_segunda = driver_sisbajud.execute_script(script_extrair_protocolo_segunda)
                        print(f'[SISBAJUD] ✅ Protocolo segunda minuta: {protocolo_segunda}')
                    except Exception as e:
                        print(f'[SISBAJUD] ⚠️ Erro ao extrair protocolo segunda minuta: {e}')
                        protocolo_segunda = None
                else:
                    print('[SISBAJUD] ❌ Falha ao salvar segunda minuta')
                    return None
                
            elif status_salvamento == 'AINDA_EDITANDO':
                print('[SISBAJUD] ⚠️ Minuta ainda em modo de edição - pode não ter salvado')
            else:
                print('[SISBAJUD] ⚠️ Status de salvamento desconhecido')
                
        else:
            print('[SISBAJUD] ❌ Falha ao clicar no botão Salvar')
        
        print('[SISBAJUD] ✅ MINUTA DE BLOQUEIO CRIADA COM SUCESSO')
        
        # 13. COLETAR DADOS DA MINUTA PARA RELATÓRIO
        print('[SISBAJUD] 13. Coletando dados da minuta para relatório...')
        dados_relatorio = coletar_dados_minuta_sisbajud(driver_sisbajud, protocolo_primeira, data_protocolo)
        if dados_relatorio:
            # Salvar dados coletados em arquivo
            relatorio_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.html')
            try:
                # Criar HTML completo para visualização
                html_completo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório SISBAJUD</title>
</head>
<body>
{dados_relatorio}
</body>
</html>"""
                
                with open(relatorio_path, 'w', encoding='utf-8') as f:
                    f.write(html_completo)
                print(f'[SISBAJUD] ✅ Relatório salvo em: {relatorio_path}')
                
                # Também salvar apenas o conteúdo para uso direto no PJe
                relatorio_texto_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.txt')
                with open(relatorio_texto_path, 'w', encoding='utf-8') as f:
                    f.write(dados_relatorio)
                print(f'[SISBAJUD] ✅ Conteúdo para PJe salvo em: {relatorio_texto_path}')
                
                # Nota: Integração com PJe agora é feita pelo fluxo chamador (pec.py)
                print('[SISBAJUD] ✅ Relatório gerado para integração posterior com PJe')
                
            except Exception as e:
                print(f'[SISBAJUD] ⚠️ Erro ao salvar relatório: {e}')
        else:
            print('[SISBAJUD] ⚠️ Não foi possível coletar dados da minuta')
        
        # Extrair protocolo (se possível)
        protocolo = None
        try:
            url = driver_sisbajud.current_url
            match = re.search(r'/(\d{10,})/', url)
            if match:
                protocolo = match.group(1)
                print(f'[SISBAJUD] Protocolo extraído: {protocolo}')
        except:
            pass
        
        # NÃO fechar driver SISBAJUD aqui - deixar para a função coordenadora
        # O driver deve ser reutilizado para múltiplos processos SISBAJUD
        print('[SISBAJUD] ✅ Minuta de bloqueio concluída - mantendo driver SISBAJUD aberto para próximos processos')
        
        return {
            'status': 'sucesso',
            'dados_minuta': {
                'protocolo_primeira': protocolo_primeira,
                'protocolo_segunda': protocolo_segunda if 'protocolo_segunda' in locals() else None,
                'data_protocolo': data_protocolo,
                'tipo': 'bloqueio',
                'repeticao': 'sim',
                'data_limite': data_limite_str,
                'quantidade_reus': len(reus),
                'relatorio_html': 'relatorio_sisbajud.html',
                'relatorio_texto': 'relatorio_sisbajud.txt'
            }
        }
        
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha na minuta de bloqueio: {e}')
        traceback.print_exc()
        
        # Fechar driver SISBAJUD em caso de erro
        try:
            if 'driver_sisbajud' in locals() and driver_sisbajud:
                driver_sisbajud.quit()
                print('[SISBAJUD] ✅ Driver SISBAJUD fechado após erro')
        except Exception as cleanup_error:
            print(f'[SISBAJUD] ⚠️ Erro ao fechar driver SISBAJUD: {cleanup_error}')
        
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
            
            # Clique direto no botão "Nova" via JavaScript
            script = """
            var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
            if (!botaoNova) {
                botaoNova = document.querySelector('button.mat-fab.mat-primary');
            }
            if (botaoNova) {
                // Se for ícone, clica no botão pai
                if (botaoNova.tagName === 'MAT-ICON') {
                    botaoNova = botaoNova.closest('button');
                }
                botaoNova.click();
                return true;
            }
            return false;
            """
            
            sucesso = driver_sisbajud.execute_script(script)
            
            if sucesso:
                print('[SISBAJUD] ✅ Botão "Nova" clicado via JavaScript')
                time.sleep(2)
            else:
                print('[SISBAJUD] Navegação direta para /minuta/cadastrar...')
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
            # Focar via JavaScript como no gigs.py
            driver_sisbajud.execute_script("arguments[0].focus();", elemento_numero)
            elemento_numero.clear()
            elemento_numero.send_keys(numero_processo)
            trigger_event(elemento_numero, 'input')
            driver_sisbajud.execute_script("arguments[0].blur();", elemento_numero)
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
            # Focar via JavaScript como no gigs.py
            driver_sisbajud.execute_script("arguments[0].focus();", elemento_cpf)
            elemento_cpf.clear()
            elemento_cpf.send_keys(cpf_cnpj_limpo)
            trigger_event(elemento_cpf, 'input')
            driver_sisbajud.execute_script("arguments[0].blur();", elemento_cpf)
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
            # Focar via JavaScript como no gigs.py
            driver_sisbajud.execute_script("arguments[0].focus();", elemento_nome)
            elemento_nome.clear()
            elemento_nome.send_keys(nome_autor)
            trigger_event(elemento_nome, 'input')
            driver_sisbajud.execute_script("arguments[0].blur();", elemento_nome)
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
                # Focar via JavaScript como no gigs.py
                driver_sisbajud.execute_script("arguments[0].focus();", elemento_cpf_reu)
                elemento_cpf_reu.clear()
                elemento_cpf_reu.send_keys(cpf_cnpj_formatado_reu)
                trigger_event(elemento_cpf_reu, 'input')
                driver_sisbajud.execute_script("arguments[0].blur();", elemento_cpf_reu)
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

def _identificar_ordens_com_bloqueio(ordens, valor_total_bloqueado_serie=None):
    """
    Identifica ordens que geraram bloqueio usando a lógica do gigs.py.
    
    Args:
        ordens: Lista de ordens da série
        valor_total_bloqueado_serie: Valor total bloqueado da série
    
    Returns:
        list: Lista de ordens que têm bloqueio
    """
    bloqueios = []
    
    if not ordens:
        return bloqueios
    
    # 1. Detectar bloqueios pela diferença de valor entre ordens consecutivas
    for i in range(len(ordens) - 1):
        valor_atual = ordens[i]["valor_bloquear"]
        valor_posterior = ordens[i + 1]["valor_bloquear"]
        
        if valor_atual > valor_posterior:
            bloqueios.append(ordens[i])
            print(f"[SISBAJUD] ✅ Bloqueio detectado na ordem {ordens[i]['sequencial']}: {valor_atual} → {valor_posterior}")
    
    # 2. LÓGICA DO GIGS.PY: Verificar última ordem usando diferença de valores
    if len(ordens) > 0:
        ultima_ordem = ordens[-1]
        
        # Calcular valor total original que deveria ser bloqueado
        # (primeiro valor "a bloquear" da primeira ordem)
        valor_original_a_bloquear = ordens[0]["valor_bloquear"] if ordens else 0
        
        # Valor total efetivamente bloqueado (da série)
        valor_efetivamente_bloqueado = valor_total_bloqueado_serie or 0
        
        # Valor "a bloquear" da última ordem
        valor_ultima_ordem = ultima_ordem["valor_bloquear"]
        
        # Diferença esperada vs real
        diferenca_esperada = valor_original_a_bloquear - valor_efetivamente_bloqueado
        diferenca_real = valor_ultima_ordem
        
        # Se a diferença não bate, tem bloqueio na última ordem
        diferenca_absoluta = abs(diferenca_esperada - diferenca_real)
        
        if diferenca_absoluta > 0.01:  # Tolerância para arredondamento
            # Última ordem tem bloqueio
            if ultima_ordem not in bloqueios:
                bloqueios.append(ultima_ordem)
                print(f"[SISBAJUD] ✅ Bloqueio detectado na ÚLTIMA ordem {ultima_ordem['sequencial']}")
                print(f"[SISBAJUD]    Diferença esperada: R$ {diferenca_esperada:.2f}")
                print(f"[SISBAJUD]    Valor última ordem: R$ {diferenca_real:.2f}")
                print(f"[SISBAJUD]    Diferença absoluta: R$ {diferenca_absoluta:.2f}")
        else:
            print(f"[SISBAJUD] ⚪ Última ordem {ultima_ordem['sequencial']} não tem bloqueio")
    
    # 3. FALLBACK: Se a série tem valor bloqueado mas nenhum bloqueio foi detectado
    if valor_total_bloqueado_serie and valor_total_bloqueado_serie > 0 and len(bloqueios) == 0 and len(ordens) > 0:
        ultima_ordem = ordens[-1]
        bloqueios.append(ultima_ordem)
        print(f"[SISBAJUD] 🔄 FALLBACK: Série tem valor bloqueado mas nenhum bloqueio detectado")
        print(f"[SISBAJUD]    Forçando bloqueio na última ordem: {ultima_ordem['sequencial']}")
    
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
            
            # Seleção da ação com delays humanos
            try:
                if log:
                    print("[SISBAJUD] Selecionando ação para DESBLOQUEIO")

                # Delay antes de interagir com dropdown
                smart_delay('form_fill', base_delay=2.0)

                # Localizar dropdown de ações
                dropdown_acao = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao']"))
                )

                # Simular movimento humano para o dropdown
                simulate_human_movement(driver, dropdown_acao)
                
                # Clicar no dropdown com delay
                if not safe_click(driver, dropdown_acao, 'click'):
                    print("[SISBAJUD] ❌ Falha ao clicar no dropdown de ações")
                    return False

                # Delay após abrir dropdown
                smart_delay('form_fill', base_delay=1.5)

                # Procurar e clicar na opção "Desbloquear valor"
                opcao_desbloquear = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//mat-option[contains(text(), 'Desbloquear valor')]"))
                )
                
                # Simular movimento humano para a opção
                simulate_human_movement(driver, opcao_desbloquear)
                
                # Clicar na opção com delay
                if safe_click(driver, opcao_desbloquear, 'click'):
                    if log:
                        print("[SISBAJUD] ✅ Ação selecionada: Desbloquear valor")
                else:
                    print("[SISBAJUD] ❌ Falha ao selecionar opção Desbloquear valor")

                # Delay após seleção
                smart_delay('form_fill', base_delay=1.0)

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Erro ao selecionar ação: {e}")
                SISBAJUD_STATS['consecutive_errors'] += 1
            
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

            # Selecionar ação apropriada para POSITIVO (ex.: Transferir valor) - VERSÃO OTIMIZADA
            try:
                if log:
                    print("[SISBAJUD] Selecionando ação para POSITIVO")

                # Localizar dropdowns mais rapidamente
                selects = driver.find_elements(By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select")
                
                if not selects:
                    if log:
                        print('[SISBAJUD] ⚠️ Nenhum mat-select encontrado para ações')
                else:
                    if log:
                        print(f"[SISBAJUD] ℹ️ Encontrados {len(selects)} mat-select(s) para ação (POSITIVO)")

                    def selecionar_acao_otimizado(select_element, dropdown_index):
                        """Função otimizada com delays humanos para selecionar ações"""
                        start_time = time.time()
                        try:
                            # Delay antes de interagir com o elemento
                            smart_delay('form_fill', base_delay=1.5)
                            
                            # Simular movimento humano para o elemento
                            simulate_human_movement(driver, select_element)
                            
                            # Focar no elemento com delay (passando o elemento como argumento)
                            safe_execute_script(driver, "if (arguments[0]) { arguments[0].focus(); }", 'default', select_element)
                            
                            from selenium.webdriver.common.keys import Keys
                            from selenium.webdriver.common.action_chains import ActionChains
                            
                            # Delay antes de enviar tecla
                            smart_delay('click', base_delay=0.8)
                            
                            # Enviar seta para baixo para abrir dropdown
                            actions = ActionChains(driver)
                            actions.send_keys_to_element(select_element, Keys.ARROW_DOWN)
                            actions.perform()
                            
                            # Delay após abrir dropdown
                            smart_delay('form_fill', base_delay=1.2)
                            
                            # Aguardar opções com timeout mais generoso
                            opcoes = None
                            for tentativa in range(5):  # Aumentado de 3 para 5
                                try:
                                    opcoes = WebDriverWait(driver, 1.0).until(  # Aumentado de 0.3 para 1.0
                                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                                    )
                                    if opcoes:
                                        break
                                except Exception:
                                    if log:
                                        print(f"[SISBAJUD] Tentativa {tentativa + 1}/5 para abrir dropdown")
                                    # Tentar abrir novamente com delay
                                    smart_delay('click', base_delay=0.5)
                                    actions = ActionChains(driver)
                                    actions.send_keys_to_element(select_element, Keys.ARROW_DOWN)
                                    actions.perform()
                            
                            if not opcoes:
                                SISBAJUD_STATS['consecutive_errors'] += 1
                                return {'sucesso': False, 'tempo': time.time() - start_time, 'erro': 'Opções não encontradas'}
                            
                            # Buscar opções no dropdown com lógica igual a gigs.py
                            opcoes_encontradas = []
                            transferir_opcao = None
                            desbloquear_opcao = None
                            cancelar_opcao = None
                            
                            for i, opcao in enumerate(opcoes):
                                try:
                                    # Delay entre verificações de opções
                                    if i > 0:
                                        smart_delay('default', base_delay=0.3)
                                    
                                    texto = opcao.text.strip()
                                    texto_lower = texto.lower()
                                    
                                    # Guardar referências para as opções - BUSCAR EXATAMENTE "Transferir valor" (sem "e desbloquear")
                                    if texto == 'Transferir valor':
                                        transferir_opcao = opcao
                                    elif 'desbloquear valor' in texto_lower and 'transferir' not in texto_lower:
                                        desbloquear_opcao = opcao
                                    elif 'cancelar' in texto_lower:
                                        cancelar_opcao = opcao
                                    
                                    opcoes_encontradas.append(texto)
                                except Exception:
                                    continue
                            
                            if log:
                                print(f"[SISBAJUD] Opções encontradas no dropdown: {opcoes_encontradas}")
                            
                            # Lógica de seleção igual a gigs.py:
                            # 1. Priorizar "Transferir valor"
                            # 2. Se não tiver "Transferir", escolher "Cancelar"
                            # 3. Se não tiver nem "Cancelar", deixar em branco (primeira opção)
                            
                            opcao_selecionada = None
                            
                            if transferir_opcao:
                                opcao_selecionada = transferir_opcao
                                texto_acao = 'Transferir valor'
                            elif cancelar_opcao:
                                opcao_selecionada = cancelar_opcao
                                texto_acao = 'Cancelar'
                            else:
                                # Sem transferir nem cancelar - selecionar primeira opção (em branco)
                                if opcoes and len(opcoes) > 0:
                                    opcao_selecionada = opcoes[0]
                                    texto_acao = 'opção em branco (primeira opção)'
                            
                            if opcao_selecionada:
                                # Simular movimento para a opção
                                simulate_human_movement(driver, opcao_selecionada)
                                
                                # Clicar com função segura
                                if safe_click(driver, opcao_selecionada, 'click'):
                                    tempo_total = time.time() - start_time
                                    if log:
                                        print(f"[SISBAJUD] ✅ Ação selecionada no dropdown #{dropdown_index+1}: '{texto_acao}' -- tempo_total={tempo_total:.2f}s")
                                    return {'sucesso': True, 'texto': texto_acao, 'tempo': tempo_total}
                                else:
                                    print(f"[SISBAJUD] ❌ Falha ao clicar na opção: {texto_acao}")
                            else:
                                print(f"[SISBAJUD] ❌ Nenhuma opção válida encontrada no dropdown")
                            
                            SISBAJUD_STATS['consecutive_errors'] += 1
                            return {'sucesso': False, 'tempo': time.time() - start_time, 'erro': 'Nenhuma opção válida encontrada'}
                            
                        except Exception as e:
                            return {'sucesso': False, 'tempo': time.time() - start_time, 'erro': str(e)}

                    # Aplicar para todos os selects
                    selecionados = 0
                    for idx, select_el in enumerate(selects):
                        resultado = selecionar_acao_otimizado(select_el, idx)
                        
                        if resultado['sucesso']:
                            selecionados += 1
                        else:
                            if log:
                                print(f"[SISBAJUD] ❌ Falha no dropdown #{idx+1}: {resultado['erro']} -- tempo={resultado['tempo']:.2f}s")
                    
                    if log:
                        print(f"[SISBAJUD] ℹ️ Ações selecionadas: {selecionados}/{len(selects)} mat-select(s)")

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar ação (POSITIVO): {e}")

            # Clicar em Salvar com proteção contra stale element
            if log:
                print(f"[SISBAJUD] Aguardando antes de clicar em Salvar...")
            
            # Delay antes de tentar salvar
            smart_delay('form_fill', base_delay=2.0)
            
            if log:
                print(f"[SISBAJUD] Clicando em Salvar")
            
            salvar_clicado = False
            for tentativa in range(3):
                try:
                    # Re-localizar botão a cada tentativa
                    seletores_salvar = [
                        "button.mat-fab.mat-primary mat-icon.fa-save",
                        "//button[contains(@class,'mat-fab') and .//mat-icon[contains(@class,'fa-save')]]",
                        "//button[contains(@class,'mat-primary') and .//mat-icon[contains(@class,'fa-save')]]",
                        "//button[@title='Salvar']"
                    ]
                    
                    btn_salvar = None
                    for seletor in seletores_salvar:
                        try:
                            if seletor.startswith("//"):
                                btn_salvar = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, seletor))
                                )
                            else:
                                btn_salvar = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                                )
                            break
                        except:
                            continue
                    
                    if btn_salvar:
                        # Simular movimento humano
                        simulate_human_movement(driver, btn_salvar)
                        
                        # Tentar clicar
                        if safe_click(driver, btn_salvar, 'click'):
                            salvar_clicado = True
                            if log:
                                print(f"[SISBAJUD] ✅ Botão Salvar clicado com sucesso")
                            break
                        else:
                            # Fallback JavaScript
                            if safe_execute_script(driver, 'arguments[0].click();', 'click', btn_salvar):
                                salvar_clicado = True
                                if log:
                                    print(f"[SISBAJUD] ✅ Botão Salvar clicado via JavaScript")
                                break
                    
                    if not salvar_clicado and tentativa < 2:
                        if log:
                            print(f"[SISBAJUD] ⚠️ Tentativa {tentativa+1}/3: Botão Salvar não clicou, tentando novamente...")
                        smart_delay('default', base_delay=1.5)
                        
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Tentativa {tentativa+1}/3: Erro ao clicar em Salvar: {e}")
                    if tentativa < 2:
                        smart_delay('default', base_delay=1.5)
                        
            if not salvar_clicado:
                if log:
                    print(f"[SISBAJUD] ❌ Não foi possível clicar em Salvar após 3 tentativas")
                return False
        
            # Após salvar, preencher dados de transferência no fluxo POSITIVO
            if tipo_fluxo == "POSITIVO":
                if log:
                    print("[SISBAJUD] Preenchendo dados de transferência (depósito)")
                
                # Delay antes de iniciar preenchimento
                smart_delay('form_fill', base_delay=1.0)
                
                # ===== TIPO DE CRÉDITO: GERAL =====
                try:
                    # RE-LOCALIZAR elemento imediatamente antes de usar
                    tipo_credito_select = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-select[formcontrolname="tipoCredito"]'))
                    )
                    
                    # Clicar para abrir dropdown
                    driver.execute_script("arguments[0].click();", tipo_credito_select)
                    smart_delay('form_fill', base_delay=0.8)
                    
                    # RE-LOCALIZAR as opções após abrir o dropdown
                    opcoes_tipo = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.mat-option-text"))
                    )
                    
                    # Procurar e clicar em "Geral"
                    for opcao in opcoes_tipo:
                        try:
                            if "Geral" in (opcao.text or ''):
                                driver.execute_script("arguments[0].click();", opcao)
                                if log:
                                    print("[SISBAJUD] ✅ Tipo de crédito 'Geral' selecionado")
                                break
                        except:
                            continue
                    
                    smart_delay('form_fill', base_delay=0.5)
                    
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ❌ Erro ao selecionar tipo de crédito: {e}")
                    SISBAJUD_STATS['consecutive_errors'] += 1
                
                # ===== BANCO: 00001 BANCO DO BRASIL =====
                try:
                    # RE-LOCALIZAR o input do banco
                    banco_input = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="instituicaoFinanceiraPorCategoria"]'))
                    )
                    
                    # Clicar para abrir autocomplete
                    driver.execute_script("arguments[0].click();", banco_input)
                    smart_delay('form_fill', base_delay=0.8)
                    
                    # RE-LOCALIZAR as opções após abrir autocomplete
                    opcoes_banco = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.mat-option-text"))
                    )
                    
                    # Procurar e clicar em Banco do Brasil
                    banco_encontrado = False
                    for opcao in opcoes_banco:
                        try:
                            txt = (opcao.text or '').strip()
                            if '00001' in txt or 'BANCO DO BRASIL' in txt.upper() or 'BCO DO BRASIL' in txt.upper():
                                driver.execute_script("arguments[0].click();", opcao)
                                if log:
                                    print(f"[SISBAJUD] ✅ Banco selecionado: '{txt}'")
                                banco_encontrado = True
                                break
                        except:
                            continue
                    
                    if not banco_encontrado:
                        if log:
                            print("[SISBAJUD] ❌ Banco do Brasil não encontrado nas opções")
                        SISBAJUD_STATS['consecutive_errors'] += 1
                    
                    smart_delay('form_fill', base_delay=0.8)
                    
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ❌ Erro ao selecionar banco: {e}")
                    SISBAJUD_STATS['consecutive_errors'] += 1
                
                # ===== AGÊNCIA: 5905 =====
                agencia_preenchida = False
                for tentativa_agencia in range(5):
                    try:
                        if log and tentativa_agencia > 0:
                            print(f"[SISBAJUD] Tentativa {tentativa_agencia+1}/5 de preencher agência...")
                        
                        # RE-LOCALIZAR o campo agência a cada tentativa
                        agencia_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="agencia"]'))
                        )
                        
                        # Aguardar ser clicável
                        WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="agencia"]'))
                        )
                        
                        # Scroll e foco
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", agencia_input)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].focus();", agencia_input)
                        time.sleep(0.2)
                        
                        # Limpar e preencher
                        driver.execute_script("arguments[0].value = '';", agencia_input)
                        time.sleep(0.2)
                        agencia_input.send_keys("5905")
                        time.sleep(0.3)
                        
                        # Disparar eventos
                        driver.execute_script("""
                            var input = arguments[0];
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            input.dispatchEvent(new Event('blur', { bubbles: true }));
                        """, agencia_input)
                        
                        # Verificar se preencheu
                        time.sleep(0.3)
                        # RE-LOCALIZAR para verificar valor
                        agencia_input_verificar = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="agencia"]')
                        valor_atual = agencia_input_verificar.get_attribute('value')
                        
                        if valor_atual == '5905':
                            agencia_preenchida = True
                            if log:
                                print("[SISBAJUD] ✅ Agência '5905' preenchida e verificada")
                            break
                        else:
                            if log:
                                print(f"[SISBAJUD] ⚠️ Valor incorreto: '{valor_atual}' (esperado '5905')")
                        
                    except Exception as e:
                        if log:
                            print(f"[SISBAJUD] ⚠️ Tentativa {tentativa_agencia+1}/5 falhou: {e}")
                        if tentativa_agencia < 4:
                            time.sleep(1.0)
                
                if not agencia_preenchida:
                    if log:
                        print("[SISBAJUD] ❌ Não foi possível preencher a agência '5905'")
                    SISBAJUD_STATS['consecutive_errors'] += 1
                
                smart_delay('form_fill', base_delay=1.5)
                
                # ===== CONFIRMAR MODAL =====
                try:
                    # RE-LOCALIZAR botão confirmar
                    btn_confirm = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, "//button//span[contains(text(),'Confirmar')]/ancestor::button"))
                    )
                    
                    # Clicar com JavaScript (mais confiável)
                    driver.execute_script("arguments[0].click();", btn_confirm)
                    
                    if log:
                        print("[SISBAJUD] ✅ Confirmado modal de dados de depósito")
                    
                    smart_delay('form_fill', base_delay=2.0)
                    
                    # Aguardar fechamento do modal
                    try:
                        WebDriverWait(driver, 6).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, 'sisbajud-dialog-dados-deposito-judicial'))
                        )
                        if log:
                            print("[SISBAJUD] ✅ Modal de depósito fechado")
                    except:
                        if log:
                            print("[SISBAJUD] ⚠️ Modal não fechou visualmente, mas prosseguindo...")
                    
                    smart_delay('form_fill', base_delay=1.5)
                    
                    # Aguardar botão Protocolar
                    try:
                        WebDriverWait(driver, 6).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@title='Protocolar']"))
                        )
                        if log:
                            print("[SISBAJUD] ✅ Botão 'Protocolar' detectado - ordem processada")
                    except:
                        if log:
                            print("[SISBAJUD] ⚠️ Botão 'Protocolar' não encontrado")
                    
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ❌ Erro ao confirmar modal: {e}")
                    SISBAJUD_STATS['consecutive_errors'] += 1
        
        # Retornar True se chegou até aqui sem erros críticos
        if log:
            print(f"[SISBAJUD] ✅ Ordem {ordem['sequencial']} processada com sucesso")
        return True

    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao processar ordem {ordem['sequencial']}: {e}")
        return False

def _voltar_para_lista_ordens_serie(driver, log=True):
    """
    Volta da ordem processada para a lista de ordens da série.
    Clica apenas uma vez no botão voltar, diferente de _voltar_para_lista_principal que clica duas vezes.
    
    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log das operações
    
    Returns:
        bool: True se conseguiu voltar com sucesso
    """
    try:
        if log:
            print("[SISBAJUD] Voltando para lista de ordens da série...")
        
        # Aguardar um pouco para garantir que a página está carregada
        time.sleep(1)
        
        # Seletores para o botão voltar (chevron-left)
        seletores_voltar = [
            "button[aria-label='Voltar'] i.fa-chevron-left",
            "button i.fa-chevron-left",
            ".fa-chevron-left",
            "i.fa-chevron-left",
            "button.btn-voltar",
            "[aria-label='Voltar']",
            "button[title='Voltar']"
        ]
        
        # Tentar encontrar e clicar no botão voltar
        botao_encontrado = False
        for seletor in seletores_voltar:
            try:
                # Buscar o elemento
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                
                for elemento in elementos:
                    if elemento.is_displayed() and elemento.is_enabled():
                        # Tentar clicar usando JavaScript para maior confiabilidade
                        driver.execute_script("arguments[0].click();", elemento)
                        if log:
                            print(f"[SISBAJUD] ✅ Clicou no botão voltar usando seletor: {seletor}")
                        botao_encontrado = True
                        break
                
                if botao_encontrado:
                    break
                    
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Seletor {seletor} falhou: {str(e)}")
                continue
        
        if not botao_encontrado:
            # Última tentativa: buscar por JavaScript
            try:
                js_script = """
                // Buscar botões com ícone chevron-left
                var botoes = document.querySelectorAll('button, a, .btn');
                for (var i = 0; i < botoes.length; i++) {
                    var botao = botoes[i];
                    var chevron = botao.querySelector('i.fa-chevron-left, .fa-chevron-left');
                    if (chevron && botao.offsetParent !== null) {
                        botao.click();
                        return 'Clicou via JavaScript';
                    }
                }
                return 'Botão não encontrado';
                """
                resultado_js = driver.execute_script(js_script)
                if log:
                    print(f"[SISBAJUD] JavaScript result: {resultado_js}")
                botao_encontrado = resultado_js == 'Clicou via JavaScript'
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] JavaScript fallback falhou: {str(e)}")
        
        if not botao_encontrado:
            if log:
                print("[SISBAJUD] ❌ Não foi possível encontrar o botão voltar")
            return False
        
        # Aguardar a navegação
        time.sleep(2)
        
        if log:
            print("[SISBAJUD] ✅ Voltou para lista de ordens da série")
        return True
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao voltar para lista de ordens da série: {str(e)}")
        return False


def _voltar_para_lista_principal(driver, log=True):
    """
    Volta para a lista principal de séries usando navegação direta ou botão voltar.
    
    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log das operações
    
    Returns:
        bool: True se conseguiu voltar com sucesso
    """
    try:
        if log:
            print("[SISBAJUD] Voltando para lista principal...")
        
        # Primeiro, tentar navegação direta usando a URL
        url_atual = driver.current_url
        
        # Se estamos em uma página de detalhes de série, voltar para teimosinha
        if "/detalhes" in url_atual:
            # Extrair o número do processo se possível
            numero_processo = None
            
            # Tentar extrair número do processo de diferentes formas
            if "numeroProcesso=" in url_atual:
                numero_processo = url_atual.split("numeroProcesso=")[1].split("&")[0]
            elif hasattr(driver, '_numero_processo_atual'):
                numero_processo = driver._numero_processo_atual
            
            # Construir URL de volta
            if numero_processo:
                url_volta = f"https://sisbajud.cnj.jus.br/teimosinha?numeroProcesso={numero_processo}"
            else:
                # Se não conseguir o número do processo, navegar para teimosinha e depois consultar novamente
                url_volta = "https://sisbajud.cnj.jus.br/teimosinha"
            
            if log:
                print(f"[SISBAJUD] Navegando diretamente para: {url_volta}")
            
            driver.get(url_volta)
            time.sleep(3)
            
            # Se não tinha número do processo, precisa fazer a consulta novamente
            if not numero_processo:
                # Implementar lógica para re-consultar o processo aqui se necessário
                pass
            
            if log:
                print("[SISBAJUD] ✅ Navegação direta concluída")
            return True
        
        # Se não está em página de detalhes, tentar usar botão voltar
        if log:
            print("[SISBAJUD] Tentando usar botão voltar...")
        
        # Seletor do botão de voltar com chevron-left
        botao_voltar_clicado = False
        seletores_voltar = [
            'button.mat-icon-button .fa-chevron-left',
            'button[mat-icon-button] .fas.fa-chevron-left',
            'button .mat-icon.fa-chevron-left',
            '.mat-icon-button .material-icons:contains("chevron_left")'
        ]
        
        for seletor in seletores_voltar:
            try:
                if 'contains' in seletor:
                    # Para seletores com :contains, usar JavaScript
                    botao = driver.execute_script(f"""
                        var elements = document.querySelectorAll('.mat-icon-button .material-icons');
                        for (var i = 0; i < elements.length; i++) {{
                            if (elements[i].textContent.includes('chevron_left')) {{
                                return elements[i].closest('button');
                            }}
                        }}
                        return null;
                    """)
                    if botao:
                        botao.click()
                        botao_voltar_clicado = True
                        break
                else:
                    botao_icon = driver.find_element(By.CSS_SELECTOR, seletor)
                    botao = botao_icon.find_element(By.XPATH, './ancestor::button[1]')
                    botao.click()
                    botao_voltar_clicado = True
                    break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Seletor {seletor} falhou: {e}")
                continue
        
        if botao_voltar_clicado:
            time.sleep(2)  # Aguardar carregamento
            if log:
                print("[SISBAJUD] ✅ Voltou para lista principal via botão")
            return True
        else:
            if log:
                print("[SISBAJUD] ❌ Falha ao voltar para lista principal")
            return False
            
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao voltar para lista principal: {e}")
        return False

def _navegar_e_extrair_ordens_serie(driver, serie, log=True):
    """
    Navega para uma série específica usando URL direta e extrai suas ordens.
    
    Args:
        driver: WebDriver do Selenium
        serie: Dicionário com dados da série (deve conter 'id_serie')
        log: Se deve fazer log das operações
    
    Returns:
        list: Lista de ordens da série ou lista vazia se houver erro
    """
    try:
        id_serie = serie['id_serie']
        if log:
            print(f"[SISBAJUD] Navegando para detalhes da série {id_serie}")
        
        # Navegar diretamente para a URL da série
        url_serie = f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes"
        if log:
            print(f"[SISBAJUD] Navegando para URL direta: {url_serie}")
        
        driver.get(url_serie)
        time.sleep(3)  # Aguardar carregamento da página
        
        # Verificar se chegou na página correta
        url_atual = driver.current_url
        if f"/{id_serie}/detalhes" not in url_atual:
            if log:
                print(f"[SISBAJUD] ❌ URL atual não corresponde à série: {url_atual}")
            return []
        
        if log:
            print(f"[SISBAJUD] ✅ Navegação direta bem-sucedida para série {id_serie}")
        
        # Aguardar a tabela de ordens carregar
        time.sleep(2)
        
        # Extrair ordens da série
        ordens = _extrair_ordens_da_serie(driver, log)
        if log:
            print(f"[SISBAJUD] ✅ {len(ordens)} ordens extraídas da série {id_serie}")
        
        return ordens
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro na navegação para série {serie.get('id_serie', 'unknown')}: {str(e)}")
        return []
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao navegar/extrair série {serie['id_serie']}: {e}")
        return None

def _navegar_para_ordem_especifica(driver, ordem, log=True):
    """Navega especificamente para uma ordem para processamento"""
    try:
        if log:
            print(f"[SISBAJUD] Navegando para ordem {ordem['sequencial']} da série {ordem['id_serie']}")
        
        # Implementar navegação específica para a ordem
        # Por enquanto, retornar True assumindo que já estamos na página correta
        # Isso pode ser expandido conforme necessário
        
        return True
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao navegar para ordem {ordem['sequencial']}: {e}")
        return False

def _agrupar_dados_bloqueios(dados_agrupados, dados_nova_ordem, log=True):
    """Agrupa dados de bloqueios de uma nova ordem aos dados gerais"""
    try:
        if not dados_nova_ordem or not dados_nova_ordem.get('executados'):
            return
        
        # Agrupar executados
        for chave_exec, dados_exec in dados_nova_ordem['executados'].items():
            if chave_exec not in dados_agrupados['executados']:
                # Novo executado
                dados_agrupados['executados'][chave_exec] = {
                    'nome': dados_exec['nome'],
                    'documento': dados_exec['documento'],
                    'protocolos': [],
                    'total': 0.0
                }
            
            # Adicionar protocolos do executado
            dados_agrupados['executados'][chave_exec]['protocolos'].extend(dados_exec['protocolos'])
            dados_agrupados['executados'][chave_exec]['total'] += dados_exec['total']
        
        # Somar ao total geral
        dados_agrupados['total_geral'] += dados_nova_ordem.get('total_geral', 0.0)
        
        if log:
            print(f"[SISBAJUD] Dados agrupados: {len(dados_agrupados['executados'])} executados, Total: R$ {dados_agrupados['total_geral']:.2f}")
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao agrupar dados: {e}")

def extrair_dados_bloqueios_processados(driver, log=True):
    """
    Extrai dados dos bloqueios processados agrupados por executado
    Retorna estrutura organizada para o relatório
    """
    try:
        if log:
            print("[SISBAJUD] Extraindo dados dos bloqueios processados...")
        
        # Estrutura para armazenar dados agrupados por executado
        dados_bloqueios = {
            'executados': {},  # {nome_executado: {documento: str, protocolos: [{}], total: float}}
            'total_geral': 0.0
        }
        
        # 1. Extrair número do protocolo principal
        try:
            protocolo_element = driver.find_element(By.CSS_SELECTOR, 'div.col-md-3 .sisbajud-label-valor')
            numero_protocolo = protocolo_element.text.strip()
            if log:
                print(f"[SISBAJUD] Protocolo principal encontrado: {numero_protocolo}")
        except Exception as e:
            numero_protocolo = "Protocolo não encontrado"
            if log:
                print(f"[SISBAJUD] ⚠️ Erro ao extrair protocolo: {e}")
        
        # 2. Buscar todos os cabeçalhos de executados (mat-expansion-panel-header)
        try:
            headers_executados = driver.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header')
            if log:
                print(f"[SISBAJUD] Encontrados {len(headers_executados)} executados")
            
            for idx, header in enumerate(headers_executados, 1):
                try:
                    # Extrair nome do executado
                    nome_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados-nome-pessoa')
                    nome_executado = nome_element.text.strip()
                    
                    # Extrair documento do executado
                    documento_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados a')
                    documento_executado = documento_element.text.strip()
                    
                    # Extrair valor bloqueado do executado
                    valor_element = header.find_element(By.CSS_SELECTOR, '.div-description-reu span')
                    valor_text = valor_element.text.strip()
                    
                    # Processar valor (remover texto e converter para float)
                    # Exemplo: "Valor bloqueado (bloqueio original e reiterações): R$ 244,05"
                    import re
                    valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                    if valor_match:
                        valor_str = valor_match.group(1)
                        # Converter formato brasileiro para float
                        valor_float = float(valor_str.replace('.', '').replace(',', '.'))
                    else:
                        valor_float = 0.0
                    
                    if log:
                        print(f"[SISBAJUD] Executado {idx}: {nome_executado} ({documento_executado}) - R$ {valor_float:.2f}")
                    
                    # Criar chave única para o executado (nome + documento)
                    chave_executado = f"{nome_executado}|{documento_executado}"
                    
                    # Inicializar dados do executado se não existir
                    if chave_executado not in dados_bloqueios['executados']:
                        dados_bloqueios['executados'][chave_executado] = {
                            'nome': nome_executado,
                            'documento': documento_executado,
                            'protocolos': [],
                            'total': 0.0
                        }
                    
                    # Adicionar protocolo e valor
                    dados_bloqueios['executados'][chave_executado]['protocolos'].append({
                        'numero': numero_protocolo,
                        'valor': valor_float,
                        'valor_formatado': f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    })
                    
                    # Somar ao total do executado
                    dados_bloqueios['executados'][chave_executado]['total'] += valor_float
                    
                    # Somar ao total geral
                    dados_bloqueios['total_geral'] += valor_float
                    
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Erro ao processar executado {idx}: {e}")
                    continue
            
            if log:
                print(f"[SISBAJUD] ✅ Dados extraídos: {len(dados_bloqueios['executados'])} executados, Total: R$ {dados_bloqueios['total_geral']:.2f}")
            
            return dados_bloqueios
            
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ❌ Erro ao buscar executados: {e}")
            return None
            
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Falha geral na extração: {e}")
        return None

def gerar_relatorio_bloqueios_processados(dados_bloqueios, log=True):
    """
    Gera o relatório formatado dos bloqueios processados agrupados por executado
    """
    try:
        if log:
            print("[SISBAJUD] Gerando relatório dos bloqueios processados...")
        
        if not dados_bloqueios or not dados_bloqueios['executados']:
            return "Nenhum bloqueio processado encontrado."
        
        # Estrutura HTML do relatório
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''
        
        # Percorrer cada executado
        for chave_executado, dados_exec in dados_bloqueios['executados'].items():
            nome = dados_exec['nome']
            documento = dados_exec['documento']
            protocolos = dados_exec['protocolos']
            total_executado = dados_exec['total']
            
            # Cabeçalho do executado
            relatorio_html += f'<p {pStyle}><strong>Executado: {nome} - {documento}</strong></p>'
            
            # Listar protocolos do executado
            for protocolo in protocolos:
                numero_prot = protocolo['numero']
                valor_format = protocolo['valor_formatado']
                relatorio_html += f'<p {pStyle}>Protocolo {numero_prot} - Valor: {valor_format}</p>'
            
            # Total do executado
            total_format = f"R$ {total_executado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            relatorio_html += f'<p {pStyle}><strong>Total do executado: {total_format}</strong></p>'
        
        # Total geral do processo
        total_geral_format = f"R$ {dados_bloqueios['total_geral']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        relatorio_html += f'<p {pStyle}><strong>TOTAL BLOQUEADO NO PROCESSO: {total_geral_format}</strong></p>'
        
        if log:
            print(f"[SISBAJUD] ✅ Relatório de bloqueios gerado: {len(dados_bloqueios['executados'])} executados")
        
        return relatorio_html
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao gerar relatório de bloqueios: {e}")
        return "Erro ao gerar relatório dos bloqueios processados."

def gerar_relatorio_series_executadas(series_validas, log=True):
    """
    Gera relatório das séries executadas com formato específico:
    - (numero Serie X) - Data da finalização: (dd/mm/aaaa) - Total bloqueado: (total bloqueado)
    """
    try:
        if log:
            print("[SISBAJUD] Gerando relatório de séries executadas...")
        
        if not series_validas:
            if log:
                print("[SISBAJUD] ⚠️ Nenhuma série para o relatório")
            return False
        
        # Estrutura do relatório
        relatorio_linhas = ["Relatório de séries executadas:"]
        
        for i, serie in enumerate(series_validas, 1):
            # Extrair dados da série
            numero_serie = serie.get('id_serie', 'N/A')
            data_finalizacao = serie.get('data_programada')
            total_bloqueado = serie.get('valor_bloqueado', 0)
            total_bloqueado_text = serie.get('valor_bloqueado_text', 'R$ 0,00')
            
            # Formatar data de finalização
            if data_finalizacao and hasattr(data_finalizacao, 'strftime'):
                data_str = data_finalizacao.strftime('%d/%m/%Y')
            else:
                data_str = 'Data não disponível'
            
            # Usar o texto original do valor se disponível, senão formatar
            if total_bloqueado_text and total_bloqueado_text != 'R$ 0,00':
                valor_str = total_bloqueado_text
            else:
                valor_str = f"R$ {total_bloqueado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Adicionar linha da série
            linha_serie = f"- (Série {numero_serie}) - Data da finalização: ({data_str}) - Total bloqueado: ({valor_str})"
            relatorio_linhas.append(linha_serie)
            
            if log:
                print(f"[SISBAJUD] Série {i}: {numero_serie} - {data_str} - {valor_str}")
        
        # Juntar todas as linhas
        relatorio_texto = '\n'.join(relatorio_linhas)
        
        # Salvar em arquivo
        relatorio_series_path = os.path.join(os.path.dirname(__file__), 'relatorio_series_executadas.txt')
        
        try:
            with open(relatorio_series_path, 'w', encoding='utf-8') as f:
                f.write(relatorio_texto)
            
            if log:
                print(f'[SISBAJUD] ✅ Relatório de séries salvo em: {relatorio_series_path}')
                print(f'[SISBAJUD] Total de séries no relatório: {len(series_validas)}')
            
            return True
            
        except Exception as e:
            if log:
                print(f'[SISBAJUD] ⚠️ Erro ao salvar relatório de séries: {e}')
            return False
            
    except Exception as e:
        if log:
            print(f'[SISBAJUD] ❌ Falha ao gerar relatório de séries: {e}')
        return False

def gerar_relatorio_processamento_ordem(tipo_fluxo, series_processadas, ordens_processadas, detalhes, driver=None, dados_bloqueios_agrupados=None, log=True):
    """
    Gera relatório do processamento de ordens SISBAJUD baseado no tipo de fluxo
    SEMPRE inclui primeiro o relatório das séries executadas
    Para fluxo POSITIVO, usa dados agrupados ou extrai dados de bloqueios processados
    
    Args:
        driver: WebDriver para extração de dados de bloqueios (usado se dados_bloqueios_agrupados não fornecido)
        dados_bloqueios_agrupados: Dados já agrupados de todas as ordens processadas
    """
    try:
        if log:
            print("[SISBAJUD] Gerando relatório de processamento...")
        
        # Estrutura HTML do relatório
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        
        resultado_html = ''
        
        # ETAPA 1: SEMPRE incluir o relatório das séries primeiro
        if log:
            print("[SISBAJUD] Incluindo relatório das séries executadas...")
        
        # Ler o relatório de séries gerado anteriormente
        relatorio_series_path = os.path.join(os.path.dirname(__file__), 'relatorio_series_executadas.txt')
        try:
            with open(relatorio_series_path, 'r', encoding='utf-8') as f:
                conteudo_series = f.read().strip()
            
            if conteudo_series:
                # Converter para HTML mantendo quebras de linha
                linhas_series = conteudo_series.split('\n')
                for linha in linhas_series:
                    if linha.strip():
                        if linha.startswith('Relatório de séries executadas:'):
                            resultado_html += f'<p {pStyle}><strong>{linha}</strong></p>'
                        else:
                            resultado_html += f'<p {pStyle}>{linha}</p>'
            else:
                resultado_html += f'<p {pStyle}><strong>Relatório de séries executadas:</strong></p>'
                resultado_html += f'<p {pStyle}>Nenhuma série executada encontrada.</p>'
                
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ⚠️ Erro ao ler relatório de séries: {e}")
            resultado_html += f'<p {pStyle}><strong>Relatório de séries executadas:</strong></p>'
            resultado_html += f'<p {pStyle}>Erro ao carregar dados das séries.</p>'
        
        # ETAPA 2: Processar baseado no tipo de fluxo
        if tipo_fluxo == 'NEGATIVO':
            # Fluxo NEGATIVO: bloqueios = 0
            if log:
                print("[SISBAJUD] Fluxo NEGATIVO: Não houve bloqueios realizados")
            resultado_html += f'<p {pStyle}>Não houve bloqueios realizados.</p>'
            
        elif tipo_fluxo == 'POSITIVO':
            # Fluxo POSITIVO/BLOQUEIO: usar dados agrupados ou extrair dados dos bloqueios processados
            if log:
                print("[SISBAJUD] Fluxo POSITIVO: Gerando relatório dos bloqueios realizados")
            
            # Priorizar dados agrupados (nova lógica)
            if dados_bloqueios_agrupados and dados_bloqueios_agrupados.get('executados'):
                if log:
                    print("[SISBAJUD] Usando dados agrupados de bloqueios")
                relatorio_bloqueios = gerar_relatorio_bloqueios_processados(dados_bloqueios_agrupados, log)
                resultado_html += relatorio_bloqueios
                
            # Fallback: tentar extrair dados do driver
            elif driver:
                dados_bloqueios = extrair_dados_bloqueios_processados(driver, log)
                if dados_bloqueios:
                    # Gerar relatório dos bloqueios processados
                    relatorio_bloqueios = gerar_relatorio_bloqueios_processados(dados_bloqueios, log)
                    resultado_html += relatorio_bloqueios
                else:
                    # Fallback se não conseguir extrair dados
                    resultado_html += f'<p {pStyle}><strong>Relatório dos bloqueios processados:</strong></p>'
                    resultado_html += f'<p {pStyle}>Erro ao extrair dados dos bloqueios processados.</p>'
            else:
                # Nem dados agrupados nem driver disponível
                resultado_html += f'<p {pStyle}><strong>[RELATÓRIO DOS BLOQUEIOS PROCESSADOS - DADOS NÃO DISPONÍVEIS]</strong></p>'
            
            # Mensagem final sobre transferência
            resultado_html += f'<p {pStyle}>Considerando os bloqueios realizados, as quantias localizadas foram TRANSFERIDAS à conta judicial do processo, ação que será efetivada em até 48h úteis.</p>'
            
        elif tipo_fluxo == 'DESBLOQUEIO':
            # Fluxo DESBLOQUEIO: usar mensagem específica sobre bloqueios irrisórios
            if log:
                print("[SISBAJUD] Fluxo DESBLOQUEIO: Desbloqueio realizado")
            resultado_html += f'<p {pStyle}>Considerando as regras sobre bloqueios irrisórios, as quantias localizadas foram desbloqueadas, ação que será efetivada em até 48h úteis.</p>'
        
        # Salvar relatório em arquivos
        relatorio_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.html')
        relatorio_texto_path = os.path.join(os.path.dirname(__file__), 'relatorio_sisbajud.txt')
        
        try:
            # Determinar título para o HTML
            if tipo_fluxo == 'NEGATIVO':
                titulo_html = "RELATÓRIO SISBAJUD - SEM BLOQUEIOS"
            elif tipo_fluxo == 'POSITIVO':
                titulo_html = "RELATÓRIO SISBAJUD - TRANSFERÊNCIA DE VALORES"
            elif tipo_fluxo == 'DESBLOQUEIO':
                titulo_html = "RELATÓRIO SISBAJUD - DESBLOQUEIO DE VALORES"
            else:
                titulo_html = "RELATÓRIO SISBAJUD - PROCESSAMENTO"
            
            # Criar HTML completo para visualização
            html_completo = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo_html}</title>
</head>
<body>
{resultado_html}
</body>
</html>"""
            
            with open(relatorio_path, 'w', encoding='utf-8') as f:
                f.write(html_completo)
            
            # Também salvar apenas o conteúdo para uso direto no PJe
            with open(relatorio_texto_path, 'w', encoding='utf-8') as f:
                f.write(resultado_html)
            
            if log:
                print(f'[SISBAJUD] ✅ Relatório salvo em: {relatorio_path}')
                print(f'[SISBAJUD] ✅ Conteúdo para PJe salvo em: {relatorio_texto_path}')
            
            return True
            
        except Exception as e:
            if log:
                print(f'[SISBAJUD] ⚠️ Erro ao salvar relatório: {e}')
            return False
            
    except Exception as e:
        if log:
            print(f'[SISBAJUD] ❌ Falha ao gerar relatório: {e}')
        return False

def processar_ordem_sisbajud(driver, dados_processo, driver_pje=None, log=True):
    """
    Processamento completo de ordens EXISTENTES no SISBAJUD:
    1. Navegação para teimosinha (área de ordens existentes)
    2. Filtro de ordens recentes
    3. Extração de dados
    4. Processamento individual de cada ordem
    5. Fechamento do driver
    
    DIFERENTE de minuta_bloqueio que cria novas minutas!
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
        # Armazenar número do processo no driver para navegação futura
        numero_processo = dados_processo.get('numero_processo') or dados_processo.get('numero')
        if numero_processo:
            driver._numero_processo_atual = numero_processo
        
        # ETAPA 1: NAVEGAÇÃO PARA TEIMOSINHA (sempre, independente do estado atual)
        if log:
            print("\n[SISBAJUD] ETAPA 1: NAVEGAÇÃO PARA TEIMOSINHA")
        
        # Navegar sempre para /teimosinha, independente do estado atual do driver
        if log:
            print("[SISBAJUD] Navegando para /teimosinha...")
        driver.get('https://sisbajud.cnj.jus.br/teimosinha')
        time.sleep(2)
        
        # ETAPA 2: JÁ ESTAMOS EM TEIMOSINHA - INICIAR PROCESSAMENTO
        if log:
            print("\n[SISBAJUD] ETAPA 2: INICIANDO PROCESSAMENTO DE ORDENS EXISTENTES")
            print("[SISBAJUD] ✅ Já estamos na página de teimosinha")
        
        # Aguardar carregamento da página
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
        
        # GERAÇÃO DE RELATÓRIO DAS SÉRIES EXECUTADAS
        if log:
            print("\n[SISBAJUD] ETAPA 3.1: GERAÇÃO DE RELATÓRIO DAS SÉRIES")
        
        relatorio_series_gerado = gerar_relatorio_series_executadas(series_validas, log)
        if relatorio_series_gerado:
            if log:
                print("[SISBAJUD] ✅ Relatório de séries executadas gerado com sucesso")
        else:
            if log:
                print("[SISBAJUD] ⚠️ Falha na geração do relatório de séries")
        
        # ETAPA 4: DEFINIÇÃO DE FLUXO
        if log:
            print("\n[SISBAJUD] ETAPA 4: DEFINIÇÃO DE FLUXO")
        
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
        
        # ETAPA 5: PROCESSAMENTO DE ORDENS (LÓGICA CORRIGIDA)
        if log:
            print("\n[SISBAJUD] ETAPA 4: PROCESSAMENTO DE ORDENS - LÓGICA CORRIGIDA")
            print(f"[SISBAJUD] Tipo de fluxo: {tipo_fluxo}")
        
        if tipo_fluxo == 'NEGATIVO':
            if log:
                print("[SISBAJUD] Fluxo NEGATIVO, nenhuma série será processada.")
            resultado['status'] = 'concluido'
            return resultado
        
        # Processar cada série individualmente e suas ordens
        dados_bloqueios_agrupados = {'executados': {}, 'total_geral': 0.0}
        
        for idx, serie in enumerate(series_validas, 1):
            if log:
                print(f"\n[SISBAJUD] >>> Processando série {idx}/{len(series_validas)} ID={serie['id_serie']}")

            try:
                # 1. Navegar para detalhes da série
                ordens_serie = _navegar_e_extrair_ordens_serie(driver, serie, log)
                if not ordens_serie:
                    if log:
                        print(f"[SISBAJUD] ❌ Não foi possível extrair ordens da série {serie['id_serie']}")
                    continue
                
                # 2. Identificar ordens com bloqueio da série
                valor_bloqueado_serie = float(serie.get('valor_bloqueado', 0)) if serie.get('valor_bloqueado') else 0
                ordens_bloqueio_serie = _identificar_ordens_com_bloqueio(ordens_serie, valor_bloqueado_serie)
                if log:
                    print(f"[SISBAJUD] Série {serie['id_serie']}: {len(ordens_bloqueio_serie)} ordens com bloqueio")
                
                if len(ordens_bloqueio_serie) == 0:
                    if log:
                        print(f"[SISBAJUD] Série {serie['id_serie']} não tem ordens com bloqueio, voltando para lista de séries")
                    # Voltar para lista de séries
                    _voltar_para_lista_principal(driver, log)
                    continue
                
                # 3. Processar cada ordem com bloqueio da série atual
                for idx_ordem, ordem in enumerate(ordens_bloqueio_serie, 1):
                    if log:
                        print(f"\n[SISBAJUD] >>> Processando ordem {idx_ordem}/{len(ordens_bloqueio_serie)} da série {serie['id_serie']}")
                        print(f"[SISBAJUD] Ordem: {ordem['sequencial']}, Protocolo: {ordem['protocolo']}")
                    
                    try:
                        # Processar a ordem
                        sucesso_processamento = _processar_ordem(driver, ordem, tipo_fluxo, log)
                        if not sucesso_processamento:
                            erro = f"Falha ao processar ordem {ordem['sequencial']} da série {serie['id_serie']}"
                            if log:
                                print(f"[SISBAJUD] ❌ {erro}")
                            resultado['erros'].append(erro)
                            # Continuar mesmo com erro - tentar voltar
                        else:
                            if log:
                                print(f"[SISBAJUD] ✅ Ordem {ordem['sequencial']} processada com sucesso")
                        
                        # CRUCIAL: Extrair dados IMEDIATAMENTE após processamento, ANTES de voltar
                        dados_ordem = extrair_dados_bloqueios_processados(driver, log)
                        if dados_ordem:
                            # Agrupar dados nos dados gerais
                            _agrupar_dados_bloqueios(dados_bloqueios_agrupados, dados_ordem, log)
                            resultado['ordens_processadas'] += 1
                            if log:
                                print(f"[SISBAJUD] ✅ Dados extraídos da ordem {ordem['sequencial']}")
                        else:
                            if log:
                                print(f"[SISBAJUD] ⚠️ Dados de bloqueios não extraídos da ordem {ordem['sequencial']}")
                        
                        # Agora sim, voltar para navegação
                        if idx_ordem < len(ordens_bloqueio_serie):
                            # Ainda há mais ordens para processar nesta série
                            _voltar_para_lista_ordens_serie(driver, log)
                        else:
                            # Última ordem da série, voltar para lista de séries
                            if log:
                                print(f"[SISBAJUD] Última ordem da série {serie['id_serie']}, voltando para lista de séries")
                            _voltar_para_lista_principal(driver, log)
                        
                    except Exception as e:
                        erro = f"Erro ao processar ordem {ordem['sequencial']} da série {serie['id_serie']}: {str(e)}"
                        if log:
                            print(f"[SISBAJUD] ❌ {erro}")
                        resultado['erros'].append(erro)
                        
                        # Tentar voltar para lista de ordens ou séries
                        try:
                            if idx_ordem < len(ordens_bloqueio_serie):
                                _voltar_para_lista_ordens_serie(driver, log)
                            else:
                                _voltar_para_lista_principal(driver, log)
                        except:
                            pass
                
                resultado['series_processadas'] += 1
                
            except Exception as e:
                erro = f"Erro geral ao processar série {serie['id_serie']}: {str(e)}"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['erros'].append(erro)
                
                # Tentar voltar para lista de séries
                try:
                    _voltar_para_lista_principal(driver, log)
                except:
                    pass
        
        if log:
            print(f"[SISBAJUD] ✅ Processamento concluído: {resultado['series_processadas']} séries, {resultado['ordens_processadas']} ordens")
        
        # ETAPA 6: GERAÇÃO DE RELATÓRIO
        if log:
            print("\n[SISBAJUD] ETAPA 5: GERAÇÃO DE RELATÓRIO")
        
        # Gerar relatório baseado no tipo de fluxo e resultados agrupados
        relatorio_gerado = gerar_relatorio_processamento_ordem(
            tipo_fluxo=resultado['tipo_fluxo'],
            series_processadas=resultado['series_processadas'],
            ordens_processadas=resultado['ordens_processadas'],
            detalhes=resultado['detalhes'],
            driver=None,  # Não usar driver, usar dados agrupados
            dados_bloqueios_agrupados=dados_bloqueios_agrupados,  # Passar dados agrupados
            log=log
        )
        
        if relatorio_gerado:
            resultado['relatorio_gerado'] = True
            if log:
                print("[SISBAJUD] ✅ Relatório gerado com sucesso")
        else:
            resultado['relatorio_gerado'] = False
            if log:
                print("[SISBAJUD] ⚠️ Falha na geração do relatório")
        
        # ETAPA 7: FINALIZAÇÃO
        if log:
            print("\n[SISBAJUD] ETAPA 6: FINALIZAÇÃO")
        
        # NÃO fechar driver SISBAJUD aqui - deixar para a função coordenadora em pec.py
        # O driver será reutilizado para próximos processos da lista SISBAJUD
        if log:
            print('[SISBAJUD] ✅ Ordem processada - mantendo driver SISBAJUD aberto para próximos processos')
        
        # ETAPA 7: JUNTADAS NO PJE (baseado no tipo de fluxo)
        if driver_pje and numero_processo:
            if log:
                print("\n[SISBAJUD] ETAPA 7: JUNTADAS NO PJE")
            
            tipo_fluxo = resultado.get('tipo_fluxo')
            
            try:
                # Importar funções necessárias
                from anexos import wrapper_parcial, wrapper_bloqneg
                from atos import ato_bloq, ato_meiosocio
                
                if tipo_fluxo == 'DESBLOQUEIO':
                    # DESBLOQUEIO: juntada + ato_meiosocio (sem juntada na minuta)
                    if log:
                        print("[SISBAJUD] Fluxo DESBLOQUEIO: juntada + ato_meiosocio")
                    
                    # 1. Juntada
                    resultado_juntada = wrapper_bloqneg(driver=driver_pje, numero_processo=numero_processo, debug=True)
                    if resultado_juntada:
                        print("[SISBAJUD] ✅ Juntada DESBLOQUEIO concluída")
                        
                        # Fechar aba e confirmar /detalhe
                        todas_abas = driver_pje.window_handles
                        if len(todas_abas) > 1:
                            driver_pje.close()
                            driver_pje.switch_to.window(todas_abas[0])
                        
                        import time
                        time.sleep(1)
                        if '/detalhe' not in driver_pje.current_url:
                            driver_pje.get(f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe")
                            time.sleep(2)
                        
                        # 2. ato_meiosocio (sem juntada)
                        resultado_ato = ato_meiosocio(driver_pje, debug=True)
                        if resultado_ato:
                            print("[SISBAJUD] ✅ ato_meiosocio executado")
                        else:
                            print("[SISBAJUD] ⚠️ Falha no ato_meiosocio")
                    else:
                        print("[SISBAJUD] ⚠️ Falha na juntada DESBLOQUEIO")
                
                elif tipo_fluxo == 'POSITIVO':
                    # POSITIVO: juntada parcial + ato_bloq (com juntada do relatório na minuta)
                    if log:
                        print("[SISBAJUD] Fluxo POSITIVO: juntada parcial + ato_bloq")
                    
                    # 1. Juntada parcial (certidão)
                    resultado_juntada = wrapper_parcial(driver=driver_pje, numero_processo=numero_processo, debug=True)
                    if resultado_juntada:
                        print("[SISBAJUD] ✅ Juntada POSITIVO (certidão) concluída")
                        
                        # Fechar aba e confirmar /detalhe
                        todas_abas = driver_pje.window_handles
                        if len(todas_abas) > 1:
                            driver_pje.close()
                            driver_pje.switch_to.window(todas_abas[0])
                        
                        import time
                        time.sleep(1)
                        if '/detalhe' not in driver_pje.current_url:
                            driver_pje.get(f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe")
                            time.sleep(2)
                        
                        # 2. ato_bloq (junta relatório no despacho)
                        resultado_ato = ato_bloq(driver_pje, debug=True)
                        if resultado_ato:
                            print("[SISBAJUD] ✅ ato_bloq executado (relatório juntado no despacho)")
                        else:
                            print("[SISBAJUD] ⚠️ Falha no ato_bloq")
                    else:
                        print("[SISBAJUD] ⚠️ Falha na juntada POSITIVO")
                
                elif tipo_fluxo == 'NEGATIVO':
                    # NEGATIVO: juntada + ato_meiosocio
                    if log:
                        print("[SISBAJUD] Fluxo NEGATIVO: juntada + ato_meiosocio")
                    
                    # 1. Juntada
                    resultado_juntada = wrapper_bloqneg(driver=driver_pje, numero_processo=numero_processo, debug=True)
                    if resultado_juntada:
                        print("[SISBAJUD] ✅ Juntada NEGATIVO concluída")
                        
                        # Fechar aba e confirmar /detalhe
                        todas_abas = driver_pje.window_handles
                        if len(todas_abas) > 1:
                            driver_pje.close()
                            driver_pje.switch_to.window(todas_abas[0])
                        
                        import time
                        time.sleep(1)
                        if '/detalhe' not in driver_pje.current_url:
                            driver_pje.get(f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe")
                            time.sleep(2)
                        
                        # 2. ato_meiosocio
                        resultado_ato = ato_meiosocio(driver_pje, debug=True)
                        if resultado_ato:
                            print("[SISBAJUD] ✅ ato_meiosocio executado")
                        else:
                            print("[SISBAJUD] ⚠️ Falha no ato_meiosocio")
                    else:
                        print("[SISBAJUD] ⚠️ Falha na juntada NEGATIVO")
                
                else:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Tipo de fluxo desconhecido: {tipo_fluxo}")
                
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Erro nas juntadas PJE: {e}")
                import traceback
                traceback.print_exc()
        
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
        resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo, driver_pje=driver_pje)
        
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