def gigs_minuta(driver, dias_uteis, responsavel, observacao, timeout=10, log=True):
    t0 = time.time()
    try:
        if log:
            print(f"[GIGS_MINUTA] Iniciando criação de GIGS Minuta: {dias_uteis}/{responsavel}/{observacao}")
        # Garante sempre o padrão dias/responsavel/observacao
        if not responsavel or responsavel.strip() == '-':
            responsavel = ''
        obs = observacao
        # a- Confirma URL '/minutar'
        if '/minutar' not in driver.current_url:
            if log:
                print('[GIGS_MINUTA][ERRO] URL atual não é /minutar:', driver.current_url)
            return False
        # b- Clique no botão menu lateral
        try:
            btn_menu = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, 'botao-menu'))
            )
            btn_menu.click()
            if log:
                print('[GIGS_MINUTA] Botão menu clicado.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Botão menu não encontrado ou não clicável: {e}')
            return False
        # c- Clique no botão "Abrir o Gigs"
        try:
            btn_gigs = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.icone-descricao .fa-tag'))
            )
            btn_gigs = btn_gigs.find_element_by_xpath('ancestor::button')
            btn_gigs.click()
            if log:
                print('[GIGS_MINUTA] Botão Abrir o Gigs clicado.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Botão Abrir o Gigs não encontrado ou não clicável: {e}')
            return False
        # 2. Aguarda o modal GIGS abrir
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card[aria-label="Gigs"], #lista-atividades'))
            )
            if log:
                print('[GIGS_MINUTA] Modal de GIGS aberto (mat-card[aria-label="Gigs"] ou #lista-atividades detectado).')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Modal de GIGS não detectado: {e}')
            return False
        # 2a. Clique em Nova Atividade e aguarde modal
        try:
            btn_nova_atividade = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.ID, 'nova-atividade'))
            )
            btn_nova_atividade.click()
            if log:
                print('[GIGS_MINUTA] Botão Nova Atividade clicado.')
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'form'))
            )
            if log:
                print('[GIGS_MINUTA] Modal de Nova Atividade aberto.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][ERRO] Falha ao abrir modal de Nova Atividade: {e}')
            return False
        # 3. Preenche campos no modal de atividade
        if dias_uteis != 0:
            try:
                campo_dias = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
                )
                campo_dias.clear()
                for c in str(dias_uteis):
                    campo_dias.send_keys(c)
                    time.sleep(0.05)
                if log:
                    print(f'[GIGS_MINUTA] Dias úteis preenchido: {dias_uteis}')
            except Exception as e:
                if log:
                    print(f'[GIGS_MINUTA][AVISO] Campo dias não encontrado ou não preenchido: {e}')
        if responsavel:
            try:
                campo_resp = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]'))
                )
                campo_resp.clear()
                campo_resp.send_keys(responsavel)
                time.sleep(0.2)
                from selenium.webdriver.common.keys import Keys
                campo_resp.send_keys(Keys.ARROW_DOWN)
                campo_resp.send_keys(Keys.ENTER)
                if log:
                    print(f'[GIGS_MINUTA] Responsável preenchido: {responsavel}')
            except Exception as e:
                if log:
                    print(f'[GIGS_MINUTA][AVISO] Campo responsável não encontrado ou não preenchido: {e}')
        try:
            campo_obs = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
            )
            campo_obs.clear()
            for c in obs:
                campo_obs.send_keys(c)
                time.sleep(0.03)
            if log:
                print(f'[GIGS_MINUTA] Observação preenchida: {obs}')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][AVISO] Campo observação não encontrado ou não preenchido: {e}')
        # 4. Clica em Salvar
        btn_salvar = None
        botoes = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
        for btn in botoes:
            if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                btn_salvar = btn
                break
        if not btn_salvar:
            if log:
                print('[GIGS_MINUTA][ERRO] Botão Salvar não encontrado!')
            return False
        btn_salvar.click()
        if log:
            print('[GIGS_MINUTA] Botão Salvar clicado.')
        try:
            success_snackbar = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span'))
            )
            if 'salva com sucesso' in success_snackbar.text.lower():
                if log:
                    print('[GIGS_MINUTA] Mensagem de sucesso confirmada.')
                time.sleep(1)
                if log:
                    print('[GIGS_MINUTA] GIGS Minuta criado com sucesso!')
                return True
            else:
                if log:
                    print('[GIGS_MINUTA][AVISO] Snackbar encontrado mas sem mensagem de sucesso.')
        except Exception as e:
            if log:
                print(f'[GIGS_MINUTA][AVISO] Não foi possível confirmar mensagem de sucesso: {e}')
        return True
    except Exception as e:
        if log:
            print(f'[GIGS_MINUTA][ERRO] Falha ao criar GIGS Minuta: {e}')
        return False
                    # ...existing code...