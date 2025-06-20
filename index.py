def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    # Indexa e já processa cada processo sequencialmente, sem delay e sem logs intermediários desnecessários.
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
      # Armazena a referência da aba da lista ANTES de qualquer operação
    aba_lista_original = driver.current_window_handle
    print(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')
    
    # Indexa e obtém as linhas/processos
    linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    print(f'[INDEXAR] Total de processos encontrados: {len(linhas)}')
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []
    for idx, linha in enumerate(linhas):
        try:
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                texto = tds[0].text.strip() if tds else ''
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            processos.append((num_proc, linha))
            print(f'[INDEXAR] {idx+1:02d}: {num_proc}')
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e}')
    
    print(f'[FLUXO] Indexação concluída. Iniciando processamento da lista de processos...', flush=True)
    
    def validar_conexao_driver(driver, contexto="GERAL"):
        """Valida se a conexão com o driver está ativa e funcional"""
        try:
            # Verifica se o driver possui session_id válido
            if not hasattr(driver, 'session_id') or driver.session_id is None:
                print(f'[{contexto}][CONEXÃO][ERRO] Driver não possui session_id válido')
                return False
                
            # Testa a conexão com comando simples
            try:
                current_url = driver.current_url
                window_handles = driver.window_handles
                print(f'[{contexto}][CONEXÃO][OK] Driver conectado - URL: {current_url[:50]}... | Abas: {len(window_handles)}')
                return True
            except Exception as connection_test_err:
                print(f'[{contexto}][CONEXÃO][ERRO] Falha no teste de conexão: {connection_test_err}')
                return False
                
        except Exception as validation_err:
            print(f'[{contexto}][CONEXÃO][ERRO] Falha na validação de conexão: {validation_err}')
            return False
    
    def forcar_fechamento_abas_extras():
        """Força o fechamento de abas extras, mantendo apenas a aba da lista com validação de conexão"""
        try:
            # Valida conexão antes de tentar operações
            if not validar_conexao_driver(driver, "LIMPEZA"):
                print('[LIMPEZA][ERRO] Conexão perdida - não é possível limpar abas')
                return False
                
            abas_atuais = driver.window_handles
            print(f'[LIMPEZA] Abas detectadas: {len(abas_atuais)}')
            
            for aba in abas_atuais:
                if aba != aba_lista_original:
                    try:
                        # Valida conexão antes de cada operação
                        if not validar_conexao_driver(driver, "LIMPEZA_ABA"):
                            print(f'[LIMPEZA][ERRO] Conexão perdida durante limpeza da aba {aba}')
                            return False
                            
                        driver.switch_to.window(aba)
                        driver.close()
                        print(f'[LIMPEZA] Aba fechada: {aba}')
                    except Exception as e:
                        print(f'[LIMPEZA][WARN] Erro ao fechar aba {aba}: {e}')
            
            # Volta para a aba da lista
            if aba_lista_original in driver.window_handles:
                if not validar_conexao_driver(driver, "LIMPEZA_RETORNO"):
                    print('[LIMPEZA][ERRO] Conexão perdida antes de retornar à aba da lista')
                    return False
                    
                driver.switch_to.window(aba_lista_original)
                print('[LIMPEZA] Retornou para aba da lista')
                return True
            else:
                print('[LIMPEZA][ERRO] Aba da lista original não está mais disponível!')
                return False
        except Exception as e:
            print(f'[LIMPEZA][ERRO] Falha na limpeza de abas: {e}')
            return False
    # Processa cada processo da lista indexada
    processos_processados = 0
    processos_com_erro = 0
    
    for idx, (proc_id, linha) in enumerate(processos):
        try:
            print(f'[PROCESSAR] Iniciando processo {idx+1}/{len(processos)}: {proc_id}', flush=True)
            
            # PASSO 1: Força limpeza de abas extras ANTES de abrir novo processo
            print(f'[PROCESSAR][PRE] Verificando estado de abas antes de processar {proc_id}...')
            abas_iniciais = driver.window_handles
            print(f'[PROCESSAR][PRE] Abas detectadas inicialmente: {len(abas_iniciais)}')
            
            if len(abas_iniciais) > 1:
                print(f'[PROCESSAR][PRE] Múltiplas abas detectadas! Forçando limpeza antes de {proc_id}...')
                if not forcar_fechamento_abas_extras():
                    print(f'[PROCESSAR][ERRO] Não foi possível limpar abas antes do processo {proc_id}. Abortando processamento.')
                    return False
            
            # Verifica se ainda estamos na aba da lista
            if driver.current_window_handle != aba_lista_original:
                print(f'[PROCESSAR][WARN] Não estamos na aba da lista antes de {proc_id}. Tentando retornar...')
                try:
                    driver.switch_to.window(aba_lista_original)
                    print(f'[PROCESSAR][PRE] Retornado à aba da lista para {proc_id}')
                except Exception as e:
                    print(f'[PROCESSAR][ERRO] Não foi possível retornar à aba da lista antes de {proc_id}: {e}')
                    return False            # PASSO 2: Reindexar e abrir o processo na lista
            # A referência DOM da linha pode ter ficado obsoleta após limpeza de abas
            # Vamos buscar novamente a linha pelo número do processo
            linha_atual = None
            try:
                # Busca todas as linhas novamente
                linhas_atuais = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
                for linha_temp in linhas_atuais:
                    try:
                        # Extrai o texto da linha para encontrar o processo correto
                        links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                        texto_linha = ''
                        if links:
                            texto_linha = links[0].text.strip()
                        else:
                            tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                            texto_linha = tds[0].text.strip() if tds else ''
                        
                        # Verifica se é a linha do processo que queremos
                        if proc_id in texto_linha:
                            linha_atual = linha_temp
                            print(f'[PROCESSAR][REINDEX] Linha reindexada para {proc_id}')
                            break
                    except Exception as e:
                        continue
                        
                if not linha_atual:
                    print(f'[PROCESSAR][ERRO] Não foi possível reindexar a linha para {proc_id}')
                    processos_com_erro += 1
                    continue
                    
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Falha na reindexação para {proc_id}: {e}')
                processos_com_erro += 1
                continue
            
            # Agora busca o botão na linha reindexada
            btn = None
            try:
                btn = linha_atual.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
            except Exception:
                try:
                    btn = linha_atual.find_element(By.CSS_SELECTOR, 'button, a')
                except Exception:
                    pass
            if btn is not None:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                driver.execute_script("arguments[0].click();", btn)
                print(f'[PROCESSAR][CLICK] Botão de detalhes clicado para {proc_id}')
            else:
                print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
                processos_com_erro += 1
                continue
            time.sleep(1)
            
            # PASSO 3: Trocar para a nova aba
            time.sleep(1)
            abas = driver.window_handles
            nova_aba = None
            for h in abas:
                if h != aba_lista_original:
                    nova_aba = h
                    break
            if not nova_aba:
                print(f'[PROCESSAR][ERRO] Nova aba do processo {proc_id} não foi aberta.')
                processos_com_erro += 1
                continue
            try:
                driver.switch_to.window(nova_aba)
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Não foi possível trocar para nova aba do processo {proc_id}: {e}')
                processos_com_erro += 1
                continue
            url_aba = driver.current_url
            if log:
                print(f'[PROCESSAR] Aba do processo {proc_id} aberta em {url_aba}.')
            
            # Aplica workaround TAB após abrir a aba
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
                print('[WORKAROUND] Pressionada tecla TAB para tentar restaurar cabeçalho da aba detalhes.')
            except Exception as e:
                print(f'[WORKAROUND][ERRO] Falha ao pressionar TAB: {e}')
              # PASSO 4: Executar callback (ou simular automação) com tratamento defensivo de abas
            callback_sucesso = False
            try:
                if callback:
                    print(f'[PROCESSAR][DEBUG] Iniciando callback para processo {proc_id}...', flush=True)
                    
                    # Captura estado das abas ANTES do callback
                    abas_antes_callback = set(driver.window_handles)
                    
                    # Executa callback
                    callback(driver)
                    
                    # Verifica estado das abas APÓS callback
                    abas_depois_callback = set(driver.window_handles)
                    novas_abas_callback = abas_depois_callback - abas_antes_callback
                    
                    if novas_abas_callback:
                        print(f'[PROCESSAR][WARN] Callback criou {len(novas_abas_callback)} nova(s) aba(s): {novas_abas_callback}')
                    
                    print(f'[PROCESSAR][DEBUG] Callback concluído para processo {proc_id}.', flush=True)
                    callback_sucesso = True
                    processos_processados += 1
                else:
                    print(f'[PROCESSAR][DEBUG] Nenhum callback definido para processo {proc_id}.', flush=True)
                    callback_sucesso = True
                    processos_processados += 1
            except Exception as e:
                print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}', flush=True)
                import traceback
                print(f'[PROCESSAR][ERRO] Traceback completo: {traceback.format_exc()}', flush=True)
                processos_com_erro += 1
                callback_sucesso = False
            
            # PASSO 5: FORÇA limpeza de abas após processamento (SEMPRE, independente do callback)
            print(f'[PROCESSAR] Processo {proc_id} finalizado (sucesso={callback_sucesso}) - FORÇANDO limpeza completa de abas...')
            
            # Limpeza defensiva SEMPRE, mesmo que callback falhe
            try:
                abas_antes_limpeza = driver.window_handles
                print(f'[PROCESSAR][LIMPEZA] Abas antes da limpeza: {len(abas_antes_limpeza)}')
                
                if not forcar_fechamento_abas_extras():
                    print(f'[PROCESSAR][ERRO] Falha na limpeza automática para {proc_id}. Tentando limpeza manual...')
                    
                    # Limpeza manual forçada em caso de falha
                    for aba in driver.window_handles:
                        if aba != aba_lista_original:
                            try:
                                driver.switch_to.window(aba)
                                driver.close()
                                print(f'[PROCESSAR][LIMPEZA] Aba manual fechada: {aba}')
                            except Exception as cleanup_err:
                                print(f'[PROCESSAR][LIMPEZA][WARN] Erro na limpeza manual da aba {aba}: {cleanup_err}')
                    
                    # Volta para a lista após limpeza manual
                    try:
                        driver.switch_to.window(aba_lista_original)
                        print('[PROCESSAR][LIMPEZA] Retornou à aba da lista após limpeza manual')
                    except Exception as switch_err:
                        print(f'[PROCESSAR][ERRO] Não foi possível retornar à aba da lista: {switch_err}')
                        return False
                
                abas_depois_limpeza = driver.window_handles
                print(f'[PROCESSAR][LIMPEZA] Abas após limpeza: {len(abas_depois_limpeza)}')
                
                if len(abas_depois_limpeza) > 1:
                    print(f'[PROCESSAR][WARN] Ainda há {len(abas_depois_limpeza)} abas abertas após limpeza!')
                
            except Exception as cleanup_error:
                print(f'[PROCESSAR][ERRO] Falha crítica na limpeza de abas para {proc_id}: {cleanup_error}')
                # Mesmo com erro na limpeza, tenta continuar
                try:
                    driver.switch_to.window(aba_lista_original)
                except:
                    print(f'[PROCESSAR][ERRO] Não foi possível retornar à aba da lista após erro de limpeza')
                    return False
            
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha geral ao processar processo {proc_id}: {e}')
            processos_com_erro += 1
            # Mesmo com erro, força limpeza de abas para tentar prosseguir
            try:
                forcar_fechamento_abas_extras()
            except:
                pass
            continue
    
    # Relatório final
    print(f'[FLUXO] Processamento concluído!')
    print(f'[FLUXO] Processos processados com sucesso: {processos_processados}')
    print(f'[FLUXO] Processos com erro: {processos_com_erro}')
    print(f'[FLUXO] Total de processos: {len(processos)}')
    
    return processos_processados > 0  # Retorna True se pelo menos um processo foi processado