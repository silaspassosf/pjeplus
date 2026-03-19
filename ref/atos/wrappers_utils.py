"""
Utilitários e funções auxiliares para automação de processos.
Contém funções de visibilidade de sigilosos e controle de sigilo.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def visibilidade_sigilosos(driver, polo='ativo', log=False):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente.
    NOVO: Automaticamente troca para aba /detalhe e atualiza a página com driver.refresh().
    Sequência: Tab switch → refresh → Múltipla seleção → Primeira checkbox → Visibilidade → Salvar
    
    :param driver: A instância do WebDriver.
    :param polo: 'ativo', 'passivo', 'ambos'. Define qual polo será selecionado.
    :param log: Ativa logs detalhados.
    :return: True se executou com sucesso, False caso contrário.
    """
    if log:
        print(f"[VISIBILIDADE] Iniciando atribuição de visibilidade para polo: '{polo}'")

    try:
        # Preferir a aba cuja URL contenha '/detalhe'. Se não existir, tentar a segunda aba
        current_url = driver.current_url
        if len(driver.window_handles) > 1:
            if log:
                print("[VISIBILIDADE] Múltiplas abas detectadas. Procurando aba com '/detalhe'...")

            detalhe_handle = None
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    url = driver.current_url
                    if log:
                        print(f"[VISIBILIDADE] Verificando aba {handle}: {url}")
                    if '/detalhe' in url:
                        detalhe_handle = handle
                        if log:
                            print(f"[VISIBILIDADE] ✓ Encontrada aba /detalhe: {handle}")
                        break
                except Exception:
                    continue

            if detalhe_handle:
                driver.switch_to.window(detalhe_handle)
                current_url = driver.current_url
            else:
                # Se não encontrou, tentar a segunda aba (índice 1) e aguardar até que sua URL contenha /detalhe
                try:
                    segundo = driver.window_handles[1]
                    driver.switch_to.window(segundo)
                    if log:
                        print(f"[VISIBILIDADE] Nenhuma aba com '/detalhe' encontrada. Mudando para segunda aba: {segundo}")
                    # Esperar até o URL conter '/detalhe' (timeout 10s)
                    waited = 0
                    while '/detalhe' not in driver.current_url and waited < 10:
                        if log:
                            print(f"[VISIBILIDADE] Aguardando /detalhe na URL atual: {driver.current_url}")
                        time.sleep(1)
                        waited += 1
                    current_url = driver.current_url
                except Exception as e:
                    if log:
                        print(f"[VISIBILIDADE] Falha ao alternar para segunda aba: {e}")
        else:
            if log:
                print(f"[VISIBILIDADE] Apenas uma aba. URL atual: {current_url}")
        
        # NOVO: Atualiza a página com F5 - APENAS driver.refresh()
        if log:
            print("[VISIBILIDADE] Atualizando página com driver.refresh()...")
        
        try:
            driver.refresh()
            time.sleep(3)  # Aguarda a página recarregar
            if log:
                print("[VISIBILIDADE][F5] ✓ Página atualizada com driver.refresh()")
        except Exception as refresh_err:
            if log:
                print(f"[VISIBILIDADE][F5][ERRO] Falha no refresh: {refresh_err}")
            return False
        
        # Aguarda a página estar completamente carregada
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            if log:
                print("[VISIBILIDADE][F5] ✓ Página completamente carregada")
        except:
            if log:
                print("[VISIBILIDADE][F5] ⚠ Timeout aguardando carregamento completo")
        
        if log:
            print("[VISIBILIDADE] Iniciando sequência de visibilidade...")

        # 1. Ativa múltipla seleção PRIMEIRO
        if log:
            print("[VISIBILIDADE] 1. Ativando múltipla seleção...")
        try:
            btn_multi = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]')
            btn_multi.click()
            time.sleep(0.5)
            if log:
                print("[VISIBILIDADE] ✓ Múltipla seleção ativada")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao ativar múltipla seleção: {e}')
            return False
            
        # 2. Clica na primeira checkbox encontrada na timeline
        if log:
            print("[VISIBILIDADE] 2. Procurando primeira checkbox na timeline...")
        try:
            primeira_checkbox = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline mat-card mat-checkbox label')
            primeira_checkbox.click()
            time.sleep(0.5)
            if log:
                print("[VISIBILIDADE] ✓ Primeira checkbox marcada")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao marcar primeira checkbox: {e}')
            return False
            
        # 3. Clica no botão de visibilidade
        if log:
            print("[VISIBILIDADE] 3. Clicando no botão de visibilidade...")
        try:
            btn_visibilidade = driver.find_element(By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
            btn_visibilidade.click()
            time.sleep(1)
            if log:
                print("[VISIBILIDADE] ✓ Modal de visibilidade aberto")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao clicar no botão de visibilidade: {e}')
            return False
            
        # 4. No modal, seleciona o polo desejado
        if log:
            print(f"[VISIBILIDADE] 4. Selecionando polo: {polo}")
        try:
            if polo == 'ativo':
                icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo')
                for icone in icones:
                    linha = icone.find_element(By.XPATH, './../../..')
                    label = linha.find_element(By.CSS_SELECTOR, 'label')
                    label.click()
            elif polo == 'passivo':
                icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo')
                for icone in icones:
                    linha = icone.find_element(By.XPATH, './../../..')
                    label = linha.find_element(By.CSS_SELECTOR, 'label')
                    label.click()
            elif polo == 'ambos':
                # Marca todos
                btn_todos = driver.find_element(By.CSS_SELECTOR, 'th button')
                btn_todos.click()
            if log:
                print(f"[VISIBILIDADE] ✓ Polo '{polo}' selecionado")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao selecionar polo: {e}')
            return False
            
        # 5. Confirma no botão Salvar
        if log:
            print("[VISIBILIDADE] 5. Salvando configuração de visibilidade...")
        try:
            btn_salvar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
            )
            btn_salvar.click()
            time.sleep(1)
            if log:
                print("[VISIBILIDADE] ✓ Configuração salva")
        except Exception as e:
            if log:
                print(f'[VISIBILIDADE][ERRO] Falha ao salvar configuração: {e}')
            return False
            
        # 6. Oculta múltipla seleção
        if log:
            print("[VISIBILIDADE] 6. Ocultando múltipla seleção...")
        try:
            btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
            btn_ocultar.click()
            if log:
                print("[VISIBILIDADE] ✓ Múltipla seleção ocultada")
        except:
            if log:
                print("[VISIBILIDADE] ⚠ Não foi possível ocultar múltipla seleção")
            pass
            
        if log:
            print('[VISIBILIDADE] ✓ Visibilidade aplicada com sucesso!')
        return True
        
    except Exception as e:
        if log:
            print(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}')
        return False


def executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=False):
    """
    Executa a função visibilidade_sigilosos se sigilo foi ativado.
    NOVO: Atualiza a página com F5 antes de executar as ações de visibilidade.
    Deve ser chamada na aba /detalhe.
    
    :param driver: WebDriver
    :param sigilo_ativado: Boolean indicando se sigilo foi ativado
    :param debug: Boolean para logs detalhados
    :return: True se executou com sucesso ou não era necessário, False se falhou
    """
    if not sigilo_ativado:
        print('[VISIBILIDADE][INFO] Sigilo não foi ativado. Função visibilidade_sigilosos não necessária.')
        return True
    
    try:
        # Verifica se está na URL correta (/detalhe)
        current_url = driver.current_url
        if '/detalhe' not in current_url:
            print(f'[VISIBILIDADE][WARN] URL atual não contém /detalhe: {current_url}')
            print('[VISIBILIDADE][WARN] A função visibilidade_sigilosos deve ser executada na URL /detalhe')
        
        # NOVO: Atualiza a página com F5 como primeira ação
        print('[VISIBILIDADE][INFO] Atualizando página com F5...')
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.F5)
        
        # Aguarda a página recarregar
        time.sleep(3)
        print('[VISIBILIDADE][INFO] Página atualizada. Executando visibilidade_sigilosos...')
        
        # Usa a função local que já tem tab switching e F5
        resultado = visibilidade_sigilosos(driver, log=debug)
        
        if resultado:
            print('[VISIBILIDADE][OK] ✓ Função visibilidade_sigilosos executada com sucesso.')
            return True
        else:
            print('[VISIBILIDADE][ERRO] ✗ Função visibilidade_sigilosos falhou.')
            return False
            
    except Exception as e:
        print(f'[VISIBILIDADE][ERRO] ✗ Exceção ao executar visibilidade_sigilosos: {e}')
        import traceback
        traceback.print_exc()
        return False
