def minuta_bloqueio(driver_pje=None, dados_processo=None):
    """
    Cria minuta de bloqueio no SISBAJUD
    
    Fluxo:
    1. Chama iniciar_sisbajud(driver_pje) que:
       - Extrai dados do processo PJe (se driver_pje fornecido)
       - Cria driver SISBAJUD e faz login
       - Retorna driver SISBAJUD já logado
    2. Usa o driver SISBAJUD para preencher a minuta
    
    Args:
        driver_pje: WebDriver do PJe para extração de dados (opcional)
        dados_processo: Dados do processo em formato de dicionário (opcional)
    
    Returns:
        dict: Dados da minuta criada ou None em caso de falha
    """
    try:
        print('\n[SISBAJUD] INICIANDO MINUTA DE BLOQUEIO')
        print('=' * 60)
        
        # 1. Inicializar SISBAJUD (extrai dados, cria driver e faz login)
        print('[SISBAJUD] 1. Inicializando SISBAJUD...')
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
            try:
                btn_nova = driver_sisbajud.find_element(By.CSS_SELECTOR, 'button.mat-fab.mat-primary')
                btn_nova.click()
                print('[SISBAJUD] ✅ Botão "Nova" clicado')
                # Maximizar janela
                try:
                    driver_sisbajud.maximize_window()
                    print('[SISBAJUD] 🖥️ Janela maximizada')
                except Exception as e:
                    print(f'[SISBAJUD] ⚠️ Falha ao maximizar janela: {e}')
            except Exception as e:
                print(f'[SISBAJUD] ❌ Falha ao clicar no botão "Nova": {e}')
                driver_sisbajud.quit()
                return None
        
        # 4. Preencher campos seguindo a lógica de 0c.py
        
        # 4.1. JUIZ SOLICITANTE
        print('[SISBAJUD] Preenchendo juiz solicitante...')
        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        # Preencher campo
        if not preencher_campo(driver_sisbajud, 'input[placeholder*="Juiz"]', juiz):
            print('[SISBAJUD] ❌ Falha ao preencher juiz solicitante')
            driver_sisbajud.quit()
            return None
        time.sleep(0.7)
        # Selecionar opção correta no dropdown
        try:
            opcoes_juiz = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'span.mat-option-text')
            for opcao in opcoes_juiz:
                if 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA' in opcao.text.upper():
                    try:
                        btn_adicionar = driver_sisbajud.find_element(By.CSS_SELECTOR, 'button.btn-adicionar')
                        btn_adicionar.click()
                        print(f'[SISBAJUD] ✅ Réu adicionado: {cpf_cnpj_reu}')
                        time.sleep(2)
                    except Exception as e:
                        print(f'[SISBAJUD] ⚠️ Falha ao clicar no botão de adicionar réu: {e}')
                    # --- Tratamento de overlay de CPF/CNPJ irregular ---
                    try:
                        overlay = None
                        for _ in range(10):
                            overlays = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'span.snack-messenger-text')
                            for ov in overlays:
                                if 'não está com situação cadastral regular/ativo' in ov.text:
                                    overlay = ov
                                    break
                            if overlay:
                                break
                            time.sleep(0.5)
                        if overlay:
                            print('[SISBAJUD] ⚠️ Overlay de CPF/CNPJ irregular detectado')
                            btn_ok = driver_sisbajud.find_element(By.XPATH, "//span[contains(@class,'mat-button-wrapper') and text()='OK']")
                            btn_ok.click()
                            time.sleep(1)
                            celulas = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'td.mat-cell.cdk-column-qtdeRelacionamentos')
                            alvo = None
                            for cel in celulas:
                                if '0' in cel.text:
                                    alvo = cel
                                    break
                            if alvo:
                                linha = alvo.find_element(By.XPATH, './ancestor::tr')
                                btn_ellipsis = linha.find_element(By.CSS_SELECTOR, 'mat-icon.fas.fa-ellipsis-h')
                                btn_ellipsis.click()
                                time.sleep(1)
                                btn_excluir = driver_sisbajud.find_element(By.XPATH, "//button[.//span[text()='Excluir']]")
                                btn_excluir.click()
                                time.sleep(1)
                                print('[SISBAJUD] ✅ Réu excluído após overlay de irregularidade')
                            else:
                                print('[SISBAJUD] ⚠️ Não encontrou célula de relacionamentos = 0 para exclusão')
                    except Exception as e_overlay:
                        print(f'[SISBAJUD] ⚠️ Erro ao tratar overlay/exclusão de réu: {e_overlay}')
        if not numero_processo:
            print('[SISBAJUD] ❌ Número do processo não encontrado nos dados')
            driver_sisbajud.quit()
            return None
        
        print(f'[SISBAJUD] Número do processo: {numero_processo}')
        
        # Mesmo seletor de 0c.py
        if not preencher_campo(driver_sisbajud, 'input[placeholder="Número do Processo"]', numero_processo):
            print('[SISBAJUD] ❌ Falha ao preencher número do processo')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 4.4. TIPO DE AÇÃO
        print('[SISBAJUD] Selecionando tipo de ação...')
        # Mesmo seletor de 0c.py
        if not clicar_elemento(driver_sisbajud, 'mat-select[name*="acao"]'):
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
        
        # 4.5. CPF/CNPJ DO AUTOR
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
        
        if not preencher_campo(driver_sisbajud, 'input[placeholder*="CPF"]', cpf_cnpj_limpo):
            print('[SISBAJUD] ❌ Falha ao preencher CPF/CNPJ do autor')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)

               
        # 4.6. NOME DO AUTOR
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
        
        # Mesmo seletor de 0c.py
        if not preencher_campo(driver_sisbajud, 'input[placeholder="Nome do autor/exequente da ação"]', nome_autor):
            print('[SISBAJUD] ❌ Falha ao preencher nome do autor')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # 4.7. REPETIÇÃO DA ORDEM (sempre SIM)
        print('[SISBAJUD] Selecionando repetição da ordem: SIM...')
        try:
            # Mesmo seletor de 0c.py
            radios = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
            for radio in radios:
                if 'Repetir a ordem' in radio.text:
                    radio.click()
                    print('[SISBAJUD] ✅ Repetição da ordem selecionada: SIM')
                    break
        except Exception as e:
            print(f'[SISBAJUD] ⚠️ Erro ao selecionar repetição da ordem: {e}')
        
        time.sleep(1)
        
        # 4.8. DATA LIMITE (30 dias + 2 = 32 dias como no gigs.js)
        print('[SISBAJUD] Preenchendo data limite (30 dias + 2 extras)...')
        from datetime import datetime, timedelta
        
        # Calcular data limite seguindo lógica do gigs.js: 30 + 2 dias
        numdias = 30  # Equivalente ao extrairNumeros(preferencias.sisbajud.teimosinha)
        data_limite = datetime.now() + timedelta(days=numdias + 2)  # +2 como no gigs.js
        
        ano_limite = data_limite.year
        mes_limite = data_limite.month  
        dia_limite = data_limite.day
        
        print(f'[SISBAJUD] Data calculada: {dia_limite}/{mes_limite}/{ano_limite}')
        
        # Mesmo seletor de 0c.py
        if not clicar_elemento(driver_sisbajud, 'button[aria-label="Open calendar"]'):
            print('[SISBAJUD] ❌ Falha ao abrir calendário')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # Mesmo seletor de 0c.py
        if not clicar_elemento(driver_sisbajud, 'mat-calendar button[aria-label="Choose month and year"]'):
            print('[SISBAJUD] ❌ Falha ao abrir seleção de mês/ano')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # Selecionar ano da data limite (não ano atual)
        if not clicar_elemento(driver_sisbajud, f'mat-calendar td[aria-label="{ano_limite}"]'):
            print('[SISBAJUD] ❌ Falha ao selecionar ano')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # Encontrar mês disponível (lógica do gigs.js)
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        
        mes_atual = mes_limite - 1  # Index do array (0-11)
        mes_encontrado = False
        
        while mes_atual >= 0:
            mes_str = f"{meses[mes_atual]} de {ano_limite}"
            print(f'[SISBAJUD] Tentando mês: {mes_str}')
            
            # Verificar se mês está disponível
            try:
                elemento_mes = driver_sisbajud.find_element(By.CSS_SELECTOR, f'mat-calendar td[aria-label="{mes_str}"]')
                if not elemento_mes.get_attribute('aria-disabled'):
                    elemento_mes.click()
                    mes_encontrado = True
                    break
                else:
                    print(f'[SISBAJUD] Mês {mes_str} desabilitado, tentando anterior...')
                    dia_limite = 31  # Se mês está desabilitado, usar último dia do mês anterior
            except:
                print(f'[SISBAJUD] Mês {mes_str} não encontrado, tentando anterior...')
                dia_limite = 31
            
            mes_atual -= 1
        
        if not mes_encontrado:
            print('[SISBAJUD] ❌ Nenhum mês disponível encontrado')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # Encontrar primeiro dia disponível (lógica do gigs.js)
        mes_final_str = f"{meses[mes_atual]} de {ano_limite}"
        dia_encontrado = False
        
        while dia_limite > 0:
            dia_str = f"{dia_limite} de {mes_final_str}"
            print(f'[SISBAJUD] Tentando dia: {dia_str}')
            
            try:
                elemento_dia = driver_sisbajud.find_element(By.CSS_SELECTOR, f'mat-calendar td[aria-label="{dia_str}"]')
                if not elemento_dia.get_attribute('aria-disabled'):
                    elemento_dia.click()
                    dia_encontrado = True
                    print(f'[SISBAJUD] ✅ Data selecionada: {dia_str}')
                    break
                else:
                    print(f'[SISBAJUD] Dia {dia_limite} desabilitado, tentando anterior...')
            except:
                print(f'[SISBAJUD] Dia {dia_limite} não encontrado, tentando anterior...')
            
            dia_limite -= 1
        
        if not dia_encontrado:
            print('[SISBAJUD] ❌ Nenhum dia disponível encontrado')
            driver_sisbajud.quit()
            return None
        
        time.sleep(1)
        
        # Definir string da data para retorno
        data_limite_final = datetime(ano_limite, mes_atual + 1, dia_limite)
        data_limite_str = data_limite_final.strftime('%d/%m/%Y')
        
        # 4.9. INSERÇÃO DOS RÉUS (todos, sem modal)
        print('[SISBAJUD] Inserindo todos os réus...')
        reus = dados_processo.get('reu', [])
        
        if not reus:
            print('[SISBAJUD] ❌ Nenhum réu encontrado nos dados')
            driver_sisbajud.quit()
            return None
        
        # Para cada réu, preencher os dados
        for i, reu in enumerate(reus):
            print(f'[SISBAJUD] Adicionando réu {i+1}/{len(reus)}: {reu.get("nome", "N/A")})')
            cpf_cnpj_reu = reu.get('cpfcnpj', '')
            if not cpf_cnpj_reu:
                print(f'[SISBAJUD] ⚠️ Réu sem CPF/CNPJ, pulando...')
                continue
            # Formatar CPF/CNPJ (CNPJ sempre raiz)
            tipo_doc_reu = identificar_tipo_documento(cpf_cnpj_reu)
            if tipo_doc_reu == 'CPF':
                cpf_cnpj_formatado_reu = formatar_cpf(cpf_cnpj_reu)
            elif tipo_doc_reu == 'CNPJ':
                # CNPJ raiz: 8 primeiros dígitos, sem formatação
                cpf_cnpj_formatado_reu = ''.join(filter(str.isdigit, cpf_cnpj_reu))[:8]
            else:
                cpf_cnpj_formatado_reu = cpf_cnpj_reu
            campo_documento_selector = 'input[placeholder="CPF/CNPJ do réu/executado"]'
            try:
                campo = driver_sisbajud.find_element(By.CSS_SELECTOR, campo_documento_selector)
                campo.click()
                time.sleep(0.3)
            except Exception as e:
                print(f'[SISBAJUD] ⚠️ Não foi possível focar campo do réu: {e}')
            sucesso = False
            for tentativa in range(5):
                # Para CNPJ, digitar dígito por dígito
                if tipo_doc_reu == 'CNPJ':
                    try:
                        campo = driver_sisbajud.find_element(By.CSS_SELECTOR, campo_documento_selector)
                        campo.clear()
                        time.sleep(0.2)
                        for digito in cpf_cnpj_formatado_reu:
                            campo.send_keys(digito)
                            time.sleep(0.08)
                    except Exception as e:
                        print(f'[SISBAJUD] ⚠️ Erro ao digitar CNPJ raiz: {e}')
                else:
                    preencher_campo(driver_sisbajud, campo_documento_selector, cpf_cnpj_formatado_reu)
                time.sleep(0.7)
                try:
                    campo = driver_sisbajud.find_element(By.CSS_SELECTOR, campo_documento_selector)
                    valor_inserido = campo.get_attribute('value')
                    def apenas_digitos(s):
                        return ''.join(filter(str.isdigit, str(s)))
                    digitos_inseridos = apenas_digitos(valor_inserido)
                    digitos_esperados = apenas_digitos(cpf_cnpj_formatado_reu)
                    # Para CNPJ raiz, comparar só os 8 primeiros dígitos
                    if tipo_doc_reu == 'CNPJ':
                        if digitos_inseridos[:8] == digitos_esperados[:8] and len(digitos_inseridos[:8]) == 8:
                            sucesso = True
                            break
                        else:
                            print(f'[SISBAJUD] ⚠️ Valor inserido incorreto (CNPJ raiz), reinserindo (tentativa {tentativa+2}/5)...')
                            campo.clear()
                            time.sleep(0.5)
                    else:
                        if digitos_inseridos == digitos_esperados:
                            sucesso = True
                            break
                        else:
                            print(f'[SISBAJUD] ⚠️ Valor inserido incorreto, reinserindo (tentativa {tentativa+2}/5)...')
                            campo.clear()
                            time.sleep(0.5)
                except Exception as e:
                    print(f'[SISBAJUD] ⚠️ Erro ao conferir campo do réu: {e}')
            if not sucesso:
                print(f'[SISBAJUD] ❌ Falha ao inserir documento do réu {i+1} após 5 tentativas')
                driver_sisbajud.quit()
                return None

            # Esperar overlay desaparecer antes de clicar em adicionar
            for espera in range(10):
                overlays = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'div.cdk-overlay-pane')
                if not overlays or not any(overlay.is_displayed() for overlay in overlays):
                    break
                time.sleep(0.5)

            # Clicar no botão de adicionar após conferência
            try:
                btn_adicionar = driver_sisbajud.find_element(By.CSS_SELECTOR, 'button.btn-adicionar')
                btn_adicionar.click()
                print(f'[SISBAJUD] ✅ Réu adicionado: {cpf_cnpj_reu}')
                    # --- Tratamento de overlay de CPF/CNPJ irregular ---
                    try:
                        overlay = None
                        for _ in range(10):
                            overlays = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'span.snack-messenger-text')
                            for ov in overlays:
                                if 'não está com situação cadastral regular/ativo' in ov.text:
                                    overlay = ov
                                    break
                            if overlay:
                                break
                            time.sleep(0.5)
                        if overlay:
                            print('[SISBAJUD] ⚠️ Overlay de CPF/CNPJ irregular detectado')
                            btn_ok = driver_sisbajud.find_element(By.XPATH, "//span[contains(@class,'mat-button-wrapper') and text()='OK']")
                            btn_ok.click()
                            time.sleep(1)
                            celulas = driver_sisbajud.find_elements(By.CSS_SELECTOR, 'td.mat-cell.cdk-column-qtdeRelacionamentos')
                            alvo = None
                            for cel in celulas:
                                if '0' in cel.text:
                                    alvo = cel
                                    break
                            if alvo:
                                linha = alvo.find_element(By.XPATH, './ancestor::tr')
                                btn_ellipsis = linha.find_element(By.CSS_SELECTOR, 'mat-icon.fas.fa-ellipsis-h')
                                btn_ellipsis.click()
                                time.sleep(1)
                                btn_excluir = driver_sisbajud.find_element(By.XPATH, "//button[.//span[text()='Excluir']]")
                                btn_excluir.click()
                                time.sleep(1)
                                print('[SISBAJUD] ✅ Réu excluído após overlay de irregularidade')
                            else:
                                print('[SISBAJUD] ⚠️ Não encontrou célula de relacionamentos = 0 para exclusão')
                    except Exception as e_overlay:
                        print(f'[SISBAJUD] ⚠️ Erro ao tratar overlay/exclusão de réu: {e_overlay}')
            except Exception as e:
                print(f'[SISBAJUD] ⚠️ Falha ao clicar no botão de adicionar réu: {e}')
            time.sleep(2)

        # 5. Preencher valor:
            print('[SISBAJUD] Preenchendo valor...')
            campo_valor_selector = 'input[placeholder="Valor aplicado a todos os réus/executados"]'
            valor_reu = str(dados_processo.get('valor', ''))
            valor_reu_digitos = ''.join(filter(str.isdigit, valor_reu))
            try:
                campo_valor = driver_sisbajud.find_element(By.CSS_SELECTOR, campo_valor_selector)
                campo_valor.click()
                time.sleep(0.3)
                campo_valor.clear()
                time.sleep(0.2)
                for digito in valor_reu_digitos:
                    campo_valor.send_keys(digito)
                    time.sleep(0.08)
            except Exception as e:
                print(f'[SISBAJUD] ❌ Falha ao preencher valor: {e}')
                driver_sisbajud.quit()
                return None
            try:
                btn_confirmar_valor = driver_sisbajud.find_element(By.CSS_SELECTOR, 'button.btn-adicionar')
                btn_confirmar_valor.click()
                print('[SISBAJUD] ✅ Valor confirmado com botão adicionar')
            except Exception as e:
                print(f'[SISBAJUD] ❌ Falha ao confirmar valor: {e}')
                driver_sisbajud.quit()
                return None

        # 6. Salvar minuta
        print('[SISBAJUD] Salvando minuta...')
        # Mesmo seletor de 0c.py
        if not clicar_elemento(driver_sisbajud, 'button.mat-fab.mat-primary mat-icon.fa-save'):
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
                    'tipo': 'bloqueio',
                    'repeticao': 'sim',
                    'data_limite': data_limite_str,
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
        print(f'[SISBAJUD][ERRO] Falha na minuta de bloqueio: {e}')
        traceback.print_exc()
        return None