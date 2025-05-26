import logging
import time
from Fix import esperar_elemento, safe_click
from selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

def def_arq(driver):
    """
    Fluxo de arquivamento do processo:
    1. Verifica o texto do botão "Abrir tarefa do processo" para detectar se já está na tarefa de arquivamento
    2. Se detectar "Escolher tipo de arquivamento", processo já está correto - retorna sucesso
    3. Abre tarefa do processo (igual fluxo_cls)
    4. Verifica se URL da segunda aba contém '/arquivamento' (processo já arquivado)
    5. Clica no botão 'Arquivar o processo' (aria-label)
    """
    print('[ARQ] Iniciando fluxo de arquivamento...')
    
    # PASSO 1: Verificar o texto do botão antes de clicar
    btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
    if not btn_abrir_tarefa:
        print('[ARQ][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
        return False
    
    # Captura o texto do botão para verificar se já está na tarefa correta
    texto_botao = ""
    try:
        # O safe_click já mostra o texto no log, mas vamos capturar explicitamente
        texto_botao = btn_abrir_tarefa.text.strip() if btn_abrir_tarefa.text else ""
        mattooltip = btn_abrir_tarefa.get_attribute('mattooltip') or ""
        aria_label = btn_abrir_tarefa.get_attribute('aria-label') or ""
        
        print(f'[ARQ][DEBUG] Texto do botão: "{texto_botao}"')
        print(f'[ARQ][DEBUG] Mattooltip: "{mattooltip}"')  
        print(f'[ARQ][DEBUG] Aria-label: "{aria_label}"')
        
        # Verifica se o processo já está na tarefa de arquivamento
        if 'Escolher tipo de arquivamento' in texto_botao or \
           'Escolher tipo de arquivamento' in mattooltip or \
           'Escolher tipo de arquivamento' in aria_label:
            print('[ARQ][INFO] Botão indica "Escolher tipo de arquivamento" - processo já está na tarefa correta!')
            print('[ARQ][INFO] Nenhuma ação necessária. Retornando sucesso.')
            return True
            
    except Exception as e:
        print(f'[ARQ][WARN] Erro ao capturar texto do botão: {e}')
    
    print('[ARQ][DEBUG] Botão não indica tarefa de arquivamento. Prosseguindo com abertura da tarefa...')
    
    # PASSO 2: Abrir a tarefa do processo
    abas_antes = set(driver.window_handles)
    safe_click(driver, btn_abrir_tarefa)
    print('[ARQ] Botão "Abrir tarefa do processo" clicado.')
    
    # PASSO 3: Troca para nova aba, se aberta
    nova_aba = None
    for _ in range(20):
        abas_depois = set(driver.window_handles)
        novas_abas = abas_depois - abas_antes
        if novas_abas:
            nova_aba = novas_abas.pop()
            break
        time.sleep(0.3)
    
    if nova_aba:
        driver.switch_to.window(nova_aba)
        print('[ARQ] Foco trocado para nova aba da tarefa do processo.')
        try:
            WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
            WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.TAG_NAME, 'button')) > 0)
            print('[ARQ] Nova aba carregada completamente.')
        except Exception as e:
            print(f'[ARQ][WARN] Timeout esperando carregamento completo da nova aba: {e}')
    else:
        print('[ARQ][WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
    
    # PASSO 4: Verificação da URL para '/arquivamento' NA SEGUNDA ABA
    url_atual = driver.current_url
    if '/arquivamento' in url_atual:
        print('[ARQ][INFO] URL já contém "/arquivamento" - processo já está arquivado. Nenhuma ação necessária.')
        print(f'[ARQ][INFO] URL atual: {url_atual}')
        return True
    
    print(f'[ARQ][DEBUG] URL atual não contém "/arquivamento". Prosseguindo com fluxo: {url_atual}')
    try:
        btn_arquivar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Arquivar o processo']"))
        )
        safe_click(driver, btn_arquivar)
        print('[ARQ] Botão "Arquivar o processo" clicado.')
        time.sleep(1)
    except Exception as e:
        print(f'[ARQ][ERRO] Falha ao clicar no botão "Arquivar o processo" por aria-label: {e}')
        print('[ARQ][INFO] Tentando fluxo alternativo: Análise → Arquivar o processo')
        
        # Fluxo alternativo para casos como "Cumprimento de Providências"
        try:
            # Primeiro clica em "Análise"
            btn_analise = None
            # Busca por texto
            btns_analise = driver.find_elements(By.XPATH, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]")
            for btn in btns_analise:
                if btn.is_displayed() and btn.is_enabled():
                    btn_analise = btn
                    break
            
            if not btn_analise:
                # Busca por aria-label
                btns_analise = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Análise']")
                for btn in btns_analise:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_analise = btn
                        break
            
            if btn_analise:
                btn_analise.click()
                print('[ARQ][DEBUG] Clique no botão "Análise" realizado.')
                time.sleep(1)
                
                # Agora tenta novamente clicar em "Arquivar o processo"
                btn_arquivar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Arquivar o processo']"))
                )
                btn_arquivar.click()
                print('[ARQ][DEBUG] Clique no botão "Arquivar o processo" realizado após clique em Análise.')
            else:
                print('[ARQ][ERRO] Botão "Análise" não encontrado no fluxo alternativo.')
                return False
                
        except Exception as e_alt:
            print(f'[ARQ][ERRO] Falha no fluxo alternativo (Análise → Arquivar o processo): {e_alt}')
            return False
    # 3. (REMOVIDO) Não criar GIGS 0/pz checar na tela de minuta. Lógica removida conforme solicitado.
    print('[ARQ] Fluxo de arquivamento finalizado com sucesso.')
    return True
