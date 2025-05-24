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
    1. Abre tarefa do processo (igual fluxo_cls)
    2. Clica no botão 'Arquivar o processo' (aria-label)
    3. Cria GIGS 0/pz checar na tela de minuta (força lógica de minuta: sempre clica no menu antes do .fa-tag)
    """
    print('[ARQ] Iniciando fluxo de arquivamento...')
    abas_antes = set(driver.window_handles)
    btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
    if not btn_abrir_tarefa:
        print('[ARQ][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
        return False
    safe_click(driver, btn_abrir_tarefa)
    print('[ARQ] Botão "Abrir tarefa do processo" clicado.')
    # Troca para nova aba, se aberta
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
    # 2. Clica no botão "Arquivar o processo" (aria-label)
    try:
        btn_arquivar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Arquivar o processo']"))
        )
        safe_click(driver, btn_arquivar)
        print('[ARQ] Botão "Arquivar o processo" clicado.')
        time.sleep(1)
    except Exception as e:
        print(f'[ARQ][ERRO] Botão "Arquivar o processo" não encontrado ou não clicável: {e}')
        return False
    # 3. (REMOVIDO) Não criar GIGS 0/pz checar na tela de minuta. Lógica removida conforme solicitado.
    print('[ARQ] Fluxo de arquivamento finalizado com sucesso.')
    return True
