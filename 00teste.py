1- trecho com problema para clicar na caixa de tipo de ação (debloquar, cancelar, transferir) junto com su acao anterior:
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
                # Preferir a string completa do mat-option quando disponível
                alvo_completo = "OTAVIO AUGUSTO MACHADO DE OLIVEIRA"
                alvo_parcial = "OTAVIO AUGUSTO"
                for opcao in opcoes_juiz:
                    texto = (opcao.text or "").strip()
                    texto_norm = texto.upper()
                    try:
                        if alvo_completo in texto_norm or alvo_parcial in texto_norm:
                            try:
                                opcao.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", opcao)
                            juiz_clicado = True
                            if log:
                                print(f"[SISBAJUD] ✅ Juiz selecionado: '{texto}' (etapa: selecionar juiz)")
                            break
                    except Exception:
                        continue
                # Fallback: se nada encontrado, selecionar a primeira opção que contenha 'OTAVIO'
                if not juiz_clicado:
                    for opcao in opcoes_juiz:
                        texto = (opcao.text or "").strip().upper()
                        if 'OTAVIO' in texto:
                            try:
                                opcao.click()
                            except Exception:
                                try:
                                    driver.execute_script("arguments[0].click();", opcao)
                                except Exception:
                                    pass
                            juiz_clicado = True
                            if log:
                                print(f"[SISBAJUD] ⚠️ Fallback: juiz selecionado por 'OTAVIO' -> '{opcao.text.strip()}'")
                            break

                if not juiz_clicado:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Opção de juiz não encontrada no dropdown (etapa: selecionar juiz)")

                # Garantir que o dropdown do juiz foi fechado: enviar ESC e clicar no body como fallback
                try:
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                except Exception:
                    pass
                try:
                    driver.find_element(By.TAG_NAME, "body").click()
                except Exception:
                    pass
                time.sleep(0.6)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}")
            
            # IMPLEMENTAÇÃO 1: Preenchimento de CPF/CNPJ na criação de minuta
            # Nota: Para ordens de DESBLOQUEIO NÃO é necessário buscar/colocar CPF/CNPJ.
            # Manteremos o passo SKIPado para evitar erros e acelerar o fluxo.
            if log:
                print('[SISBAJUD] ℹ️ Pulando preenchimento de CPF/CNPJ (não necessário para DESBLOQUEIO)')
            
                # IMPLEMENTAÇÃO 2: Seleção da caixa de ações na ordem de bloqueio
            try:
                if log:
                    print("[SISBAJUD] ℹ️ Etapa: selecionar ação apropriada para o fluxo (abrindo dropdown de ação)")
                
                # Localizar dropdown de ações com espera maior e vários seletores de fallback
                try:
                    dropdown_acao = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='acao'], mat-select[name*='acao']"))
                    )
                except Exception:
                    if log:
                        print('[SISBAJUD] ⚠️ Dropdown de ação não encontrado (mat-select[formcontrolname=acao])')
                    dropdown_acao = None

                if dropdown_acao:
                    # Clicar no gatilho interno do mat-select ('.mat-select-trigger') — muitos app material precisam disso
                    try:
                        trigger = dropdown_acao.find_element(By.CSS_SELECTOR, '.mat-select-trigger')
                    except Exception:
                        trigger = None

                    clicked = False
                    if trigger:
                        try:
                            trigger.click()
                            clicked = True
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", trigger)
                                clicked = True
                            except Exception:
                                clicked = False

                    if not clicked:
                        # fallback para clicar no próprio mat-select
                        try:
                            dropdown_acao.click()
                            clicked = True
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", dropdown_acao)
                                clicked = True
                            except Exception:
                                if log:
                                    print('[SISBAJUD] ⚠️ Falha ao clicar no dropdown de ação (gatilho e mat-select)')

                    # Aguardar o painel de opções aparecer (overlay .mat-select-panel) antes de coletar opções
                    opcoes_acao = []
                    try:
                        WebDriverWait(driver, 8).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, ".mat-select-panel"))
                        )
                    except Exception:
                        # não crítico, continuar tentando coletar opções mesmo que o painel não tenha sido detectado
                        pass

                    try:
                        opcoes_acao = WebDriverWait(driver, 6).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.mat-select-panel mat-option, mat-option[role='option'], mat-option"))
                        )
                    except Exception:
                        # tentar coletar opções de forma manual como último recurso
                        opcoes_acao = driver.find_elements(By.CSS_SELECTOR, "div.mat-select-panel mat-option, mat-option[role='option'], mat-option")

                    # Preparar candidatos de texto para seleção
                    if tipo_fluxo == "DESBLOQUEIO":
                        candidatos = ["desbloquear valor", "desbloquear", "liberar", "liberação"]
                        alvo_nome = 'Desbloquear'
                    else:
                        candidatos = ["transferir valor", "transferir", "transferência", "transferir saldo"]
                        alvo_nome = 'Transferir'

                    opcao_encontrada = False
                    for opcao in opcoes_acao:
                        texto_opcao = (opcao.text or "").strip().lower()
                        try:
                            if any(c in texto_opcao for c in candidatos):
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                                except Exception:
                                    pass
                                time.sleep(0.2)
                                # Tentar clicar a opção
                                try:
                                    opcao.click()
                                except Exception:
                                    try:
                                        filho = opcao.find_element(By.CSS_SELECTOR, 'span.mat-option-text')
                                        filho.click()
                                    except Exception:
                                        try:
                                            driver.execute_script("arguments[0].click();", opcao)
                                        except Exception:
                                            pass

                                # Verificar se a seleção foi aplicada no mat-select (pegar texto visível)
                                selecionado = ''
                                try:
                                    # esperar o painel de opções desaparecer (aplicação angular fecha o overlay)
                                    WebDriverWait(driver, 4).until(
                                        EC.invisibility_of_element_located((By.CSS_SELECTOR, '.mat-select-panel'))
                                    )
                                except Exception:
                                    # painel pode já ter sumido ou não ter sido detectado; continuar
                                    pass

                                # Re-localizar o mat-select pai (às vezes o elemento é substituído pelo framework)
                                try:
                                    # se o elemento original tem id, usar para re-localizar
                                    mat_id = None
                                    try:
                                        mat_id = dropdown_acao.get_attribute('id')
                                    except Exception:
                                        mat_id = None

                                    if mat_id:
                                        novo_select = driver.find_element(By.ID, mat_id)
                                    else:
                                        novo_select = dropdown_acao
                                except Exception:
                                    novo_select = dropdown_acao

                                # Tentar vários caminhos para obter o texto selecionado
                                try:
                                    selecionado = novo_select.find_element(By.CSS_SELECTOR, '.mat-select-value-text').text.strip()
                                except Exception:
                                    try:
                                        # algumas versões usam .mat-select-value .mat-select-placeholder
                                        selecionado = novo_select.find_element(By.CSS_SELECTOR, '.mat-select-value').text.strip()
                                    except Exception:
                                        try:
                                            selecionado = novo_select.text.strip()
                                        except Exception:
                                            selecionado = ''

                                if selecionado and any(k.lower() in selecionado.lower() for k in candidatos):
                                    opcao_encontrada = True
                                    if log:
                                        print(f"[SISBAJUD] ✅ Ação selecionada: '{opcao.text.strip()}' -> confirmado no mat-select: '{selecionado.strip()}'")
                                    break
                                else:
                                    # deu clique mas não confirmou; tentar pequeno retry: reabrir e verificar texto no overlay
                                    try:
                                        # reabrir para inspecionar (caso o mat-select não tenha atualizado visualmente)
                                        try:
                                            trigger = novo_select.find_element(By.CSS_SELECTOR, '.mat-select-trigger')
                                            driver.execute_script('arguments[0].click();', trigger)
                                        except Exception:
                                            driver.execute_script('arguments[0].click();', novo_select)

                                        # aguardar as opções ficarem visíveis e procurar a opção selecionada no overlay
                                        WebDriverWait(driver, 4).until(
                                            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.mat-select-panel'))
                                        )
                                        # procurar opção que contém o texto clicado
                                        try:
                                            painel_opts = driver.find_elements(By.CSS_SELECTOR, 'div.mat-select-panel mat-option, mat-option')
                                            for opt in painel_opts:
                                                if opt.text and opt.text.strip().lower() == opcao.text.strip().lower():
                                                    selecionado = opt.text.strip()
                                                    break
                                        except Exception:
                                            pass
                                        # fechar overlay
                                        try:
                                            driver.find_element(By.TAG_NAME, 'body').click()
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass

                                    if selecionado and any(k.lower() in selecionado.lower() for k in candidatos):
                                        opcao_encontrada = True
                                        if log:
                                            print(f"[SISBAJUD] ✅ Ação selecionada após retry: '{opcao.text.strip()}' -> '{selecionado.strip()}'")
                                        break
                        except Exception:
                            continue

                    if not opcao_encontrada:
                        if log:
                            print(f"[SISBAJUD] ⚠️ Opção aproximada para '{alvo_nome}' não encontrada (etapa: selecionar ação)")
                        try:
                            driver.find_element(By.TAG_NAME, 'body').click()
                        except Exception:
                            pass
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
        
        2- trecho do codigo que executa essas acoes corretamente, ja testado.
        //preenche o campo JUIZ SOLICITANTE
	async function juiz() {
		console.log("      |___Juiz");
		return new Promise(async resolve => {
			if (preferencias.sisbajud.juiz) {
				let magistrado = preferencias.sisbajud.juiz;
				if (magistrado.toLowerCase().includes('modulo8')) {
					let processoNumero = document.querySelector('sisbajud-inclusao-desdobramento mat-card-content').innerText.match(new RegExp('\\d{7}-\\d{2}\\.\\d{4}\\.\\d{1,2}\\.\\d{1,2}\\.\\d{4}','g')).join();
					magistrado = await filtroMagistrado(processoNumero);
				}
				
				await escolherOpcao('input[placeholder*="Juiz"]',magistrado,0,false);
			}
			resolve(true);
		});
	}
	
	//preenche o campo VARA/JUÍZO
	async function vara_juizo() {
		console.log("      |___vara_juizo");
		return new Promise(async resolve => {
			if (preferencias.sisbajud.vara) {
				await escolherOpcao('input[placeholder*="Vara"]',preferencias.sisbajud.vara,0,false);
			}
			resolve(true);
		});
	}
	
	//preenche não-respostas e desbloqueio de valores mínimos
	async function escolher_Opcao(el) {
		return new Promise(resolve => {
			if (preferencias.sisbajud.naorespostas && preferencias.sisbajud.valor_desbloqueio) {						
				console.log("      |___NÃO-RESPOSTAS (" + preferencias.sisbajud.naorespostas + ") e DESBLOQUEIO DE VALORES MÍNIMOS (" + preferencias.sisbajud.valor_desbloqueio + ")");
				el.click();
				let check = setInterval(async function() {
					if (document.querySelectorAll('mat-option[role="option"]')) {
						clearInterval(check)
						let el2 = document.querySelectorAll('mat-option[role="option"]');
						if (!el2) {
							resolve(true);
						}
						let desbloquear = null;
						for (const [pos, item] of el2.entries()) {
							// console.log("pos: " + pos + " - item: " + item.innerText)
							
							if (item.innerText.includes('Desbloquear valor')) {
								desbloquear = item;
							}
							
							if (item.innerText === 'Transferir valor') {
								item.click();
								let ancora_valor = el.parentElement.parentElement.parentElement.parentElement.parentElement;
								let valor = ancora_valor.querySelector('input').value;
								valor = valor.replace(new RegExp('[^0-9\,]', 'g'), ""); //tira o R$
								valor = valor.replace(',', '.'); //substitui a virgula por ponto
								if (parseFloat(valor) < parseFloat(preferencias.sisbajud.valor_desbloqueio)) { //manda desbloquear
									desbloquear.click();
								}
								resolve(true);
								return;
							}
							
							if (item.innerText.includes(preferencias.sisbajud.naorespostas)) {
								item.click();
								resolve(true);
								return;
							}
						}
						
						//Se chegou até aqui é porquê são casos de tratamento na requisição de endereço. Lá não tem a opção "CANCELAR", apenas "REITERAR". Nesses casos, se o usuário escolheu cancelar a opção será deixada em branco.
						document.querySelector('mat-option').click(); //a primeira opção é sempre "em branco"
						resolve(true);
					}
				}, 250); //dar tempo de popular o checklist
			} else {
				resolve(true);
			}
		});
		
	}