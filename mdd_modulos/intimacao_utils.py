"""
Módulo responsável pelo fechamento de intimações.

Responsabilidades:
- Fechamento de intimações do processo
- Interação com modais de expedientes
- Tratamento de checkboxes e formulários
- Lógica otimizada para performance

Funções extraídas do m1.py:
- fechar_intimacao()
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from Fix import safe_click, wait_for_visible, wait, sleep

def fechar_intimacao(driver, log=True):
    """
    Fecha a intimação do processo, otimizado para performance e confiabilidade.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    
    Returns:
        bool: True se o processo foi executado (com ou sem sucesso)
    """
    try:
        if log:
            print('[INTIMACAO] Iniciando processo de fechar intimação...')
        
        # 1. Abre menu principal
        menu_selector = '#botao-menu'
        menu_clicked = safe_click(driver, menu_selector, timeout=10, log=log)
        if menu_clicked:
            if log:
                print('[INTIMACAO] Menu principal aberto')
        else:
            if log:
                print('[INTIMACAO] Falha ao abrir menu principal')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] Enviado ESC após falha de clique em Expedientes')
            except Exception:
                pass
            return True
        
        sleep(300)
        
        # 2. Clica no botão Expedientes
        btn_exp_selector = 'button[aria-label="Expedientes"]:not([disabled])'
        btn_exp_clicked = safe_click(driver, btn_exp_selector, timeout=5, log=log)
        if btn_exp_clicked:
            if log:
                print('[INTIMACAO] Botão Expedientes clicado')
        else:
            if log:
                print('[INTIMACAO] Falha ao clicar no botão Expedientes')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] Modal fechado com ESC após falha no botão Expedientes')
            except Exception:
                pass
            return True
        
        sleep(300)
        
        # 3. Espera o modal de expedientes aparecer
        try:
            modal_selector = 'mat-dialog-container pje-expedientes-dialogo'
            modal = wait_for_visible(driver, modal_selector, timeout=5)
            if not modal:
                if log:
                    print('[INTIMACAO] Modal de expedientes não encontrado, continuando mesmo assim')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                return True
        except Exception as e:
            if log:
                print(f'[INTIMACAO][ERRO] Falha ao verificar modal: {e}')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True
        
        # 4. Busca linha com prazo 30 - OTIMIZADO para verificação rápida
        try:
            rows_selector = 'tbody tr'
            first_row = wait(driver, rows_selector, timeout=5)
            if not first_row:
                if log:
                    print('[INTIMACAO] Falha ao encontrar linhas de expedientes')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                return True
            
            rows = driver.find_elements(By.CSS_SELECTOR, rows_selector)
            prazo_30_encontrado = False
            checkbox_selecionada = False
            
            if log:
                print(f'[INTIMACAO][OTIMIZADO] Encontradas {len(rows)} linhas de expedientes')
            
            # VERIFICAÇÃO RÁPIDA: Primeiro verifica se existe linha com prazo 30
            for i, row in enumerate(rows):
                try:
                    prazo_cell = row.find_element(By.CSS_SELECTOR, 'td:nth-child(9)')
                    prazo_texto = prazo_cell.text.strip()
                    if log and i < 3:
                        print(f'[INTIMACAO][DEBUG] Linha {i+1}: prazo = "{prazo_texto}"')
                    
                    if prazo_texto == '30':
                        prazo_30_encontrado = True
                        if log:
                            print(f'[INTIMACAO][OTIMIZADO] ✓ Linha com prazo 30 encontrada (linha {i+1})')
                        break  # Sai do loop assim que encontrar
                        
                except Exception as e_row:
                    if log:
                        print(f'[INTIMACAO][DEBUG] Erro ao verificar linha {i+1}: {e_row}')
                    continue
            
            # Se não encontrou linha com prazo 30, fecha imediatamente
            if not prazo_30_encontrado:
                if log:
                    print('[INTIMACAO][OTIMIZADO] ❌ Nenhuma linha com prazo 30 encontrada')
                    print('[INTIMACAO][OTIMIZADO] Fechando modal imediatamente e prosseguindo')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO][OTIMIZADO] ✅ Modal fechado com ESC - fluxo continua normalmente')
                except Exception:
                    pass
                return True
            
            # Se encontrou linha com prazo 30, processa a seleção
            checkbox_selecionada = _processar_checkbox_prazo_30(driver, rows, log)
            
            if not checkbox_selecionada:
                if log:
                    print('[INTIMACAO][OTIMIZADO] ❌ Falha em todas as estratégias para selecionar checkbox')
                    print('[INTIMACAO][OTIMIZADO] Fechando modal e prosseguindo')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO][OTIMIZADO] ✅ Modal fechado com ESC após falha na checkbox')
                except Exception:
                    pass
                return True
            
            # Se chegou aqui, significa que a checkbox foi selecionada com sucesso
            # Continua com o fluxo normal (botão Fechar Expedientes)
            _fechar_expedientes(driver, log)
            
        except Exception as e:
            if log:
                print(f'[INTIMACAO][ERRO] Falha ao processar expedientes: {e}')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] Modal fechado com ESC após erro')
            except Exception:
                pass
            return True
    
    except Exception as e:
        if log:
            print(f'[INTIMACAO][ERRO] Falha geral: {str(e)}')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            if log:
                print('[INTIMACAO] Modal fechado com ESC após erro')
        except Exception:
            pass
        return True

def _processar_checkbox_prazo_30(driver, rows, log):
    """
    Processa a seleção da checkbox da linha com prazo 30.
    
    Args:
        driver: Instância do WebDriver
        rows: Lista de elementos de linha
        log (bool): Se True, imprime logs de debug
    
    Returns:
        bool: True se checkbox foi selecionada com sucesso
    """
    checkbox_selecionada = False
    
    for i, row in enumerate(rows):
        try:
            prazo_cell = row.find_element(By.CSS_SELECTOR, 'td:nth-child(9)')
            prazo_texto = prazo_cell.text.strip()
            
            if prazo_texto == '30':
                if log:
                    print(f'[INTIMACAO][OTIMIZADO] Processando linha com prazo 30 (linha {i+1})')
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                sleep(200)
                
                # Verifica se existe checkbox clicável
                checkbox_exists = False
                try:
                    checkbox_element = row.find_element(By.CSS_SELECTOR, 'td:last-child mat-checkbox')
                    if checkbox_element.is_displayed() and checkbox_element.is_enabled():
                        checkbox_exists = True
                        if log:
                            print('[INTIMACAO][OTIMIZADO] ✓ Checkbox clicável encontrada')
                    else:
                        if log:
                            print('[INTIMACAO][OTIMIZADO] ❌ Checkbox existe mas não é clicável')
                except Exception:
                    if log:
                        print('[INTIMACAO][OTIMIZADO] ❌ Checkbox não encontrada')
                
                # Se não tem checkbox clicável, retorna False
                if not checkbox_exists:
                    if log:
                        print('[INTIMACAO][OTIMIZADO] ❌ Linha de 30 dias sem checkbox clicável')
                    return False
                
                # Tenta selecionar a checkbox usando múltiplas estratégias
                checkbox_selecionada = _tentar_selecionar_checkbox(driver, row, log)
                break
                
        except Exception as e_row:
            if log:
                print(f'[INTIMACAO][OTIMIZADO] Erro ao processar linha {i+1}: {e_row}')
            continue
    
    return checkbox_selecionada

def _tentar_selecionar_checkbox(driver, row, log):
    """
    Tenta selecionar checkbox usando múltiplas estratégias.
    
    Args:
        driver: Instância do WebDriver
        row: Elemento da linha
        log (bool): Se True, imprime logs de debug
    
    Returns:
        bool: True se checkbox foi selecionada
    """
    # Estratégia 1: Checkbox via safe_click
    try:
        checkbox_element = row.find_element(By.CSS_SELECTOR, 'td:last-child mat-checkbox')
        aria_checked = checkbox_element.get_attribute('aria-checked')
        if aria_checked == 'true':
            if log:
                print('[INTIMACAO][OTIMIZADO] ✓ Checkbox já estava selecionada')
            return True
        else:
            checkbox_selecionada = safe_click(driver, checkbox_element, timeout=3, log=log)
            if checkbox_selecionada:
                if log:
                    print('[INTIMACAO][OTIMIZADO] ✅ Checkbox selecionada com safe_click')
                return True
            else:
                driver.execute_script("arguments[0].click();", checkbox_element)
                sleep(200)
                aria_checked_after = checkbox_element.get_attribute('aria-checked')
                if aria_checked_after == 'true':
                    if log:
                        print('[INTIMACAO][OTIMIZADO] ✅ Checkbox selecionada via JavaScript')
                    return True
                else:
                    if log:
                        print('[INTIMACAO][OTIMIZADO] ❌ Checkbox não foi selecionada')
    except Exception as e_check1:
        if log:
            print(f'[INTIMACAO][OTIMIZADO] Estratégia 1 falhou: {e_check1}')
    
    # Estratégia 2: Inner container
    try:
        checkbox_container = row.find_element(By.CSS_SELECTOR, 'td:last-child mat-checkbox')
        inner_container = checkbox_container.find_element(By.CSS_SELECTOR, '.mat-checkbox-inner-container')
        driver.execute_script("arguments[0].click();", inner_container)
        sleep(200)
        aria_checked_after = checkbox_container.get_attribute('aria-checked')
        if aria_checked_after == 'true':
            if log:
                print('[INTIMACAO][OTIMIZADO] ✅ Checkbox selecionada via inner container')
            return True
        else:
            if log:
                print('[INTIMACAO][OTIMIZADO] ❌ Inner container não selecionou')
    except Exception as e_check2:
        if log:
            print(f'[INTIMACAO][OTIMIZADO] Estratégia 2 falhou: {e_check2}')
    
    # Estratégia 3: Input direto
    try:
        checkbox_input = row.find_element(By.CSS_SELECTOR, 'td:last-child input[type="checkbox"]')
        if not checkbox_input.is_selected():
            driver.execute_script("arguments[0].click();", checkbox_input)
            sleep(200)
            if checkbox_input.is_selected():
                if log:
                    print('[INTIMACAO][OTIMIZADO] ✅ Checkbox selecionada via input direto')
                return True
            else:
                if log:
                    print('[INTIMACAO][OTIMIZADO] ❌ Input direto não funcionou')
        else:
            if log:
                print('[INTIMACAO][OTIMIZADO] ✓ Input já estava selecionado')
            return True
    except Exception as e_check3:
        if log:
            print(f'[INTIMACAO][OTIMIZADO] Estratégia 3 falhou: {e_check3}')
    
    return False

def _fechar_expedientes(driver, log):
    """
    Clica no botão Fechar Expedientes e confirma.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    """
    try:
        modal_expedientes = driver.find_element(By.CSS_SELECTOR, 'mat-dialog-container pje-expedientes-dialogo')
        btn_fechar_clicked = False
        
        if log:
            print(f'[INTIMACAO][OTIMIZADO] Usando seletor vencedor: aria-label')
        
        botoes = modal_expedientes.find_elements(By.CSS_SELECTOR, 'button[aria-label="Fechar Expedientes"]')
        if log:
            print(f'[INTIMACAO][OTIMIZADO] Encontrados {len(botoes)} botões com aria-label="Fechar Expedientes"')
        
        for btn in botoes:
            if btn.is_displayed() and btn.is_enabled():
                btn_fechar_clicked = safe_click(driver, btn, timeout=5, log=log)
                if btn_fechar_clicked:
                    if log:
                        print(f'[INTIMACAO][OTIMIZADO] ✅ Botão Fechar Expedientes clicado com sucesso!')
                    break
    except Exception as e_modal:
        if log:
            print(f'[INTIMACAO][OTIMIZADO] ❌ ERRO ao buscar modal: {e_modal}')
        btn_fechar_clicked = False
    
    if not btn_fechar_clicked:
        if log:
            print('[INTIMACAO] Falha ao clicar no botão Fechar Expedientes')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            if log:
                print('[INTIMACAO] Modal fechado com ESC após falha no botão Fechar')
        except Exception:
            pass
        return
    
    if log:
        print('[INTIMACAO] Botão Fechar Expedientes clicado')
    
    sleep(500)
    
    # Modal de confirmação
    try:
        modal_confirm_selector = 'mat-dialog-container[role="dialog"]'
        modal_confirm = wait_for_visible(driver, modal_confirm_selector, timeout=5)
        if not modal_confirm:
            if log:
                print('[INTIMACAO] Modal de confirmação não encontrado, continuando mesmo assim')
            return
        
        try:
            # Aguardar modal aparecer e usar ESPAÇO ao invés de clicar no botão
            sleep(500)  # Aguarda modal aparecer
            if log:
                print('[INTIMACAO] Tentando confirmar com tecla ESPAÇO...')
            
            # Enviar ESPAÇO para confirmar
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            sleep(300)  # Aguarda processamento
            
            if log:
                print('[INTIMACAO] ✅ Confirmação via ESPAÇO enviada com sucesso')
                
        except Exception as e_space:
            if log:
                print(f'[INTIMACAO] ❌ Fallback ESC após falha do ESPAÇO: {e_space}')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] ✅ Modal fechado com ESC')
            except Exception as e_esc:
                if log:
                    print(f'[INTIMACAO] ❌ Erro ao enviar ESC: {e_esc}')
    
    except Exception as e:
        if log:
            print(f'[INTIMACAO][ERRO] Falha no modal de confirmação: {e}')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
