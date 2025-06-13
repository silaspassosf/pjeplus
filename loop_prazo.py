# loop_prazo.py
# Função para automação em lote do painel global do PJe TRT2
# Segue estritamente o roteiro solicitado pelo usuário
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def loop_prazo(driver):
    # 0. Maximizar janela e ajustar zoom para 75%
    driver.maximize_window()
    driver.execute_script("document.body.style.zoom='75%'")
    time.sleep(0.5)
    # Maximizar a janela antes de iniciar o fluxo
    try:
        driver.maximize_window()
        print('[LOOP_PRAZO][DEBUG] Janela maximizada.')
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Não foi possível maximizar a janela: {e}')

    # 1. Navegar para a lista de processos e esperar 2.5s
    url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    driver.get(url_lista)
    time.sleep(2.5)

    # 2. Aplicar filtro de fase processual: Liquidação e Execução
    fases_alvo = ['liquidação', 'execução']
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                print('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            print('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            print('[ERRO] Painel de opções não apareceu.')
            return False
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        print(f'[OK] Fase "{fase}" selecionada.')
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            print(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[OK] Fases selecionadas e filtro aplicado (botão filtrar).')
            time.sleep(1)
        except Exception as e:
            print(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False

    # Aguarda a lista de processos ser atualizada após o filtro
    time.sleep(5)
    # 3. Clicar no ícone "marcar-todas" e garantir seleção antes de prosseguir
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            btn_marcar_todas = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-check.icone.marcar-todas'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_marcar_todas)
            btn_marcar_todas.click()
            time.sleep(1)
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Falha ao clicar em marcar-todas (tentativa {tentativa+1}): {e}")
            if tentativa == max_tentativas - 1:
                return False
        # 4. Tentar localizar o ícone "fa-suitcase icone" após marcar todas
        try:
            btn_suitcase = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_suitcase)
            btn_suitcase.click()
            break  # Sucesso, segue fluxo
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Falha ao localizar/clicar em fa-suitcase (tentativa {tentativa+1}): {e}")
            if tentativa == max_tentativas - 1:
                return False
            time.sleep(1.5)  # Espera antes de tentar novamente

    # 5. Aguardar mudança de URL para movimentacao-lote e garantir que está na tela correta
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains('/painel/movimentacao-lote')
        )
        # Confirma se está realmente na tela correta
        if '/painel/movimentacao-lote' not in driver.current_url:
            print(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
            return False
        print(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")
        time.sleep(1.2)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False

    # 6. Clicar na seta do dropdown "Tarefa destino única" (robustez: aguarda elemento existir e estar visível)
    try:
        seta_dropdown = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
        # [FIX] Restaurar zoom para 100% antes do clique na seta
        print("[LOOP_PRAZO][DEBUG] Restaurando zoom para 100% antes do clique na seta do dropdown.")
        driver.execute_script("document.body.style.zoom='100%'")
        time.sleep(0.3)
        seta_dropdown.click()
        print("[LOOP_PRAZO][OK] Clique na seta do dropdown 'Tarefa destino única' realizado com sucesso (div.mat-select-arrow-wrapper)")
        time.sleep(0.5)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao abrir dropdown Tarefa destino única pela seta: {e}")
        print(f"[LOOP_PRAZO][DEBUG] URL atual: {driver.current_url}")
        return False

    # 7. Selecionar "Análise"
    try:
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        opcao_analise = overlay.find_element(By.XPATH, ".//span[contains(@class,'mat-option-text') and normalize-space(text())='Análise']")
        opcao_analise.click()
        time.sleep(0.5)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao selecionar 'Análise': {e}")
        return False

    # 8. Clicar em "Movimentar processos"
    try:
        btn_movimentar = driver.find_element(By.XPATH, "//button[.//span[contains(text(),'Movimentar processos')]]")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_movimentar)
        btn_movimentar.click()
        print('[LOOP_PRAZO] Movimentação em lote concluída.')
        time.sleep(1.2)
        # 9. Voltar para a lista de processos (reinicia o fluxo)
        url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
        driver.get(url_lista)
        print('[LOOP_PRAZO] Retornou para a lista de processos.')
        # Ajustar zoom e aguardar carregamento
        driver.execute_script("document.body.style.zoom='75%'")
        time.sleep(2.5)
        # Chamar filtrofases do fix.py
        from fix import filtrofases
        filtrofases(driver)
        print('[LOOP_PRAZO] Filtro de fases aplicado.')
        time.sleep(2)
        # .inserir logica de repeticao de cilclo
        # 10. Navegar para painel global 8
        url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
        driver.get(url_painel8)
        print('[LOOP_PRAZO] Navegou para painel global 8.')
        time.sleep(3)
        # 11. Aplicar filtros
        from Fix import filtrofases, aplicar_filtro_100
        filtrofases(driver)
        print('[LOOP_PRAZO] Filtro de fases aplicado no painel 8.')
        time.sleep(4)
        aplicar_filtro_100(driver)
        print('[LOOP_PRAZO] Filtro 100 aplicado no painel 8.')
        time.sleep(3)
        # 12. Seleção de processos NÃO livres
        driver.execute_script('''try{let linhas=document.querySelectorAll('tr.cdk-drag');let selecionados=0;for(let i=0;i<linhas.length&&selecionados<20;i++){let linha=linhas[i];let prazo=linha.querySelector('td:nth-child(9) time');let prazoPreenchido=prazo&&prazo.textContent.trim();let hasComment=linha.querySelector('i.fa-comment')!==null;let inputField=linha.querySelector('input[matinput]');let campoPreenchido=inputField&&inputField.value.trim();let temLupa=linha.querySelector('td:nth-child(3) i.fa-search')!==null;if(prazoPreenchido||hasComment||campoPreenchido||temLupa){let checkbox=linha.querySelector('mat-checkbox input[type="checkbox"]');if(checkbox&&!checkbox.checked){checkbox.click();linha.style.backgroundColor="#d2ffcc";selecionados++;}}}console.log("[Bookmarklet] Total de processos NÃO livres selecionados (máx 20): "+selecionados);}catch(e){console.error('[Bookmarklet][ERRO] '+e);}''')
        print('[LOOP_PRAZO] Seleção de processos NÃO livres (máx 20) via JS concluída.')
        time.sleep(3)
        # 13. Marcar todas e suitcase
        try:
            btn_marcar_todas = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-check.icone.marcar-todas'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_marcar_todas)
            btn_marcar_todas.click()
            time.sleep(1)
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Falha ao clicar em marcar-todas: {e}")
            return False
        try:
            btn_suitcase = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_suitcase)
            btn_suitcase.click()
            print('[LOOP_PRAZO] Clique em suitcase realizado.')
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Falha ao clicar em suitcase: {e}")
            return False
        # 14. Aguardar URL movimentacao-lote
        try:
            WebDriverWait(driver, 15).until(
                EC.url_contains('/painel/movimentacao-lote')
            )
            if '/painel/movimentacao-lote' not in driver.current_url:
                print(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
                return False
            print(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")
            time.sleep(1.2)
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
            return False
        # 15. Dropdown e seleção
        driver.execute_script("document.body.style.zoom='100%'")
        print('[LOOP_PRAZO][DEBUG] Zoom restaurado para 100% antes do clique na seta do dropdown.')
        seta_dropdown = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
        seta_dropdown.click()
        print("[LOOP_PRAZO][OK] Clique na seta do dropdown 'Tarefa destino única' realizado com sucesso (div.mat-select-arrow-wrapper)")
        time.sleep(0.5)
        # 16. Selecionar destino
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        opcao_cumprimento = overlay.find_element(By.XPATH, ".//span[contains(@class,'mat-option-text') and normalize-space(text())='Cumprimento de providências']")
        opcao_cumprimento.click()
        time.sleep(0.5)
        # 17. Clicar em Movimentar processos com zoom ajustado
        driver.execute_script("document.body.style.zoom='55%'")
        print('[LOOP_PRAZO][DEBUG] Zoom reduzido para 55% antes de clicar em Movimentar processos.')
        btn_movimentar = driver.find_element(By.XPATH, "//button[.//span[contains(text(),'Movimentar processos')]]")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_movimentar)
        btn_movimentar.click()
        print('[LOOP_PRAZO] Movimentação em lote concluída (Cumprimento de providências).')
        time.sleep(1.2)
        # Removido o return True para permitir execução do ciclo dos livres
        # 18. Preparar próximo ciclo para painel 8 (livres)
        url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
        driver.get(url_painel8)
        print('[LOOP_PRAZO] Navegou novamente para painel global 8 (livres).')
        time.sleep(3)
        from Fix import filtrofases, aplicar_filtro_100
        filtrofases(driver)
        print('[LOOP_PRAZO] Filtro de fases aplicado no painel 8 (livres).')
        time.sleep(4)
        aplicar_filtro_100(driver)
        print('[LOOP_PRAZO] Filtro 100 aplicado no painel 8 (livres).')
        time.sleep(3)
        # Executar JS para selecionar processos LIVRES
        driver.execute_script('''try { let linhas = document.querySelectorAll('tr.cdk-drag'); let selecionados = 0; linhas.forEach(function(linha){ let prazo = linha.querySelector('td:nth-child(9) time'); let prazoVazio = !prazo || !prazo.textContent.trim(); let hasComment = linha.querySelector('i.fa-comment') !== null; let inputField = linha.querySelector('input[matinput]'); let campoPreenchido = inputField && inputField.value.trim(); let temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null; if (prazoVazio && !hasComment && !campoPreenchido && !temLupa) { let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]'); if (checkbox && !checkbox.checked) { checkbox.click(); linha.style.backgroundColor = "#ffccd2"; selecionados++; } } }); console.log("[Bookmarklet] Total de processos livres selecionados: " + selecionados); } catch(e) { console.error('[Bookmarklet][ERRO] ' + e); }''')
        print('[LOOP_PRAZO] Seleção de processos LIVRES via JS concluída.')
        time.sleep(2)
        # Clicar no ícone fa-tag (texto-verde)
        btn_tag = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-tag.icone.texto-verde'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_tag)
        btn_tag.click()
        print('[LOOP_PRAZO] Clique no ícone fa-tag realizado.')
        time.sleep(1)
        # Clicar em botão Atividade
        btn_atividade = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Atividade'] and contains(@class,'mat-menu-item')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_atividade)
        btn_atividade.click()
        print('[LOOP_PRAZO] Clique no botão Atividade realizado.')
        time.sleep(2)
        # Focar no campo Observação e digitar 'xs'
        campo_obs = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[formcontrolname='observacao']"))
        )
        campo_obs.click()
        campo_obs.clear()
        campo_obs.send_keys('xs')
        print('[LOOP_PRAZO] Observação preenchida com "xs".')
        time.sleep(1)
        # Clicar em Salvar
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Salvar'] and contains(@class,'mat-raised-button') and contains(@class,'mat-primary')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_salvar)
        btn_salvar.click()
        print('[LOOP_PRAZO] Atividade salva com sucesso.')
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao clicar em Movimentar processos: {e}")
        return False
