import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario


def alterar_meio_expedicao(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        log('[COMUNICACAO]  Alterando meio de expedição IMEDIATAMENTE (pós-seleção de destinatários, pré-salvamento)...')
        t0_expediente = time.perf_counter()

        # VERIFICAÇÃO ULTRA-RÁPIDA: tabela já está pronta?
        linhas_prontas = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
        if len(linhas_prontas) > 0:
            log('[COMUNICACAO] Tabela já contém destinatários - pulando esperas')
            linhas_tabela = linhas_prontas
            total_linhas = len(linhas_tabela)
        else:
            # Aguardar spinner/modal de carregamento desaparecer (observer nativo preferido)
            log('[COMUNICACAO] Verificando spinner/modal rapidamente (observer)...')
            t_spinner = time.perf_counter()
            try:
                from Fix.core import aguardar_renderizacao_nativa
                seletores_loading = '.loading-spinner, .mat-progress-spinner, .cdk-overlay-backdrop, .modal-backdrop, .loading-overlay'
                ok_spinner = aguardar_renderizacao_nativa(driver, seletores_loading, modo='sumir', timeout=3)
            except Exception:
                ok_spinner = False

            if not ok_spinner:
                log('[COMUNICACAO][WARN] Spinner ainda presente ou observer indisponível, prosseguindo mesmo assim')
            else:
                tempo_spinner = time.perf_counter() - t_spinner
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Spinner sumiu em {tempo_spinner:.3f}s')

            # Aguardar destinatários aparecerem (observer preferido)
            log('[COMUNICACAO] Aguardando destinatários aparecerem (observer)...')
            t_dest = time.perf_counter()
            try:
                from Fix.core import aguardar_renderizacao_nativa
                ok_rows = aguardar_renderizacao_nativa(driver, 'tbody.cdk-drop-list tr.cdk-drag', modo='aparecer', timeout=5)
            except Exception:
                ok_rows = False

            if not ok_rows:
                # Fallback: quick polling
                max_espera = 5
                tempo_espera = 0
                while tempo_espera < max_espera:
                    linhas_tabela = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
                    if len(linhas_tabela) > 0:
                        break
                    time.sleep(0.2)
                    tempo_espera += 0.2

                if tempo_espera >= max_espera:
                    log('[COMUNICACAO][WARN] Timeout aguardando destinatários, prosseguindo mesmo assim')
                    return False
                else:
                    tempo_dest = time.perf_counter() - t_dest
                    if debug:
                        log(f'[COMUNICACAO][DEBUG] Destinatários apareceram em {tempo_dest:.3f}s (polling fallback)')
            else:
                tempo_dest = time.perf_counter() - t_dest
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Destinatários apareceram em {tempo_dest:.3f}s (observer)')

            # Aguardar estabilização rápida (simplificada)
            log('[COMUNICACAO] Verificação rápida de estabilização...')
            contagem_inicial = len(linhas_tabela)
            
            # Verificação ultra-rápida: só 1 verificação adicional
            time.sleep(0.2)
            linhas_atual = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
            contagem_atual = len(linhas_atual)
            
            if contagem_atual != contagem_inicial:
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Contagem mudou {contagem_inicial} → {contagem_atual}')
            else:
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Contagem estabilizada em {contagem_atual}')

            # Usar a contagem mais recente
            linhas_tabela = linhas_atual
            total_linhas = len(linhas_tabela)

        if total_linhas == 0:
            log('[COMUNICACAO][WARN] Nenhuma linha de destinatário encontrada na tabela após espera!')
            return False

        log(f'[COMUNICACAO] Verificando {total_linhas} destinatário(s) para alterar meio de expedição')

        # OTIMIZAÇÃO: Pré-filtrar apenas linhas que precisam alteração
        linhas_para_alterar = []
        for idx, linha in enumerate(linhas_tabela, 1):
            try:
                span_meio = linha.find_element(By.CSS_SELECTOR, 'pje-pec-coluna-meio-expedicao .mat-select-value-text .mat-select-min-line')
                meio_atual = span_meio.text.strip()
                if meio_atual == 'Domicílio Eletrônico':
                    linhas_para_alterar.append((idx, linha))
                elif debug:
                    log(f'[COMUNICACAO] Linha {idx}: "{meio_atual}" - não precisa alteração')
            except Exception:
                if debug:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Erro ao ler meio de expedição')

        log(f'[COMUNICACAO] Encontradas {len(linhas_para_alterar)} linhas para alterar (de {total_linhas} total)')

        alterados = 0
        pulados = total_linhas - len(linhas_para_alterar)

        for idx, linha in linhas_para_alterar:
            t_linha = time.perf_counter()
            try:
                log(f'[COMUNICACAO] Linha {idx}: Domicílio Eletrônico encontrado - alterando para Correio...')

                try:
                    dropdown = linha.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Meios de Expedição"]')
                except Exception:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Dropdown não encontrado')
                    continue

                # Clicar dropdown (usar aguardar_e_clicar em vez de scrollIntoView + click)
                aguardar_e_clicar(driver, dropdown, log=False, timeout=3)
                time.sleep(0.2)

                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                    )
                except Exception:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Opções do dropdown não carregaram em 2s')
                    continue

                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                correio_clicado = False
                for opcao in opcoes:
                    if 'Correio' in opcao.text:
                        driver.execute_script("arguments[0].click();", opcao)
                        log(f'[COMUNICACAO]  Linha {idx}: Domicílio Eletrônico → Correio')
                        alterados += 1
                        correio_clicado = True
                        time.sleep(0.1)
                        break

                if not correio_clicado:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Opção "Correio" não encontrada nas opções')
                    try:
                        from selenium.webdriver.common.keys import Keys
                        dropdown.send_keys(Keys.ESCAPE)
                    except Exception:
                        pass

            except Exception as e_linha:
                log(f'[COMUNICACAO][WARN] Linha {idx}: Erro ao processar - {str(e_linha)[:60]}')
                continue

            tempo_linha = time.perf_counter() - t_linha
            if debug:
                log(f'[COMUNICACAO][DEBUG] Linha {idx} processada em {tempo_linha:.3f}s')

        tempo_total = time.perf_counter() - t0_expediente
        log(f'[COMUNICACAO]  Alterados: {alterados} | Não precisavam: {pulados} | Total: {total_linhas} (tempo: {tempo_total:.3f}s)')
        
        # Estimativa de performance
        if tempo_total > 5.0:
            log(f'[COMUNICACAO][PERF] Tempo alto detectado ({tempo_total:.1f}s). Possíveis otimizações:')
            if alterados > 0:
                tempo_medio_por_alteracao = (tempo_total - 1.0) / alterados  # subtraindo tempo de setup
                log(f'[COMUNICACAO][PERF] - Tempo médio por alteração: {tempo_medio_por_alteracao:.2f}s')
            if pulados > alterados:
                log(f'[COMUNICACAO][PERF] - Muitos pulados ({pulados}), considere pré-filtragem')
        
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao alterar meio de expedição para Correio: {e}')
        return False


def remover_destinatarios_invalidos(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        log('[COMUNICACAO] Verificando destinatários com ícone vermelho (endereço inválido)')
        try:
            red_icons = driver.find_elements(By.CSS_SELECTOR, '.pec-icone-vermelho-endereco-tabela-destinatarios')
            removidos = 0
            for ic in red_icons:
                try:
                    try:
                        row = ic.find_element(By.XPATH, './ancestor::tr[1]')
                    except Exception:
                        elem = ic
                        row = None
                        for _ in range(6):
                            try:
                                elem = elem.find_element(By.XPATH, './..')
                                if elem.tag_name.lower() == 'tr':
                                    row = elem
                                    break
                            except Exception:
                                break
                        if row is None:
                            continue

                    try:
                        btn_excluir = row.find_element(By.XPATH, ".//button[.//i[contains(@class,'fa-trash-alt')]]")
                        driver.execute_script('arguments[0].scrollIntoView(true);', btn_excluir)
                        time.sleep(0.2)
                        driver.execute_script('arguments[0].click();', btn_excluir)
                        removidos += 1
                        log(f'[COMUNICACAO]  Destinatário com ícone vermelho removido (linha). Total removidos: {removidos}')
                        time.sleep(0.6)
                    except Exception as ebtn:
                        log(f'[COMUNICACAO][WARN] Não encontrou botão de excluir na linha do ícone vermelho: {ebtn}')
                        continue
                except Exception as einner:
                    log(f'[COMUNICACAO][WARN] Erro ao processar ícone vermelho: {einner}')
                    continue
            if removidos == 0:
                log('[COMUNICACAO] Nenhum destinatário com ícone vermelho encontrado')
        except Exception as echeck:
            log(f'[COMUNICACAO][WARN] Falha ao varrer ícones vermelhos: {echeck}')
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Erro inesperado na verificação de ícones vermelhos: {e}')
        return False


def salvar_minuta_final(driver, sigilo, gigs_extra=None, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        btn_salvar_final = None
        spans = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and normalize-space(text())='Salvar']")
        for span in spans:
            btn = span.find_element(By.XPATH, './ancestor::button[1]')
            if btn.is_displayed() and btn.is_enabled():
                btn_salvar_final = btn
                break
        if not btn_salvar_final:
            log('[ERRO] Botão Salvar final não encontrado!')
            return False

        try:
            from Fix.core import safe_click
            clicked = safe_click(driver, btn_salvar_final, log=debug)
        except Exception:
            clicked = False

        if not clicked:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_salvar_final)
                driver.execute_script('arguments[0].click();', btn_salvar_final)
                clicked = True
            except Exception as e_click_final:
                log(f'[ERRO] Não foi possível clicar no botão Salvar final (tentativa direta): {e_click_final}')
                return False

        if clicked:
            log('[DEBUG] Clique no botão Salvar final realizado.')
    except Exception as e:
        log(f'[ERRO] Não foi possível clicar no botão Salvar final: {e}')
        return False

    time.sleep(1)
    
    # =========================================================
    # VERIFICAÇÃO DE ERRO DE ENDEREÇO (SNACKBAR) E RE-TENTATIVA
    # =========================================================
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Tenta captar o snackbar de erro especifico de endereço em até 2 segundos
        snackbar_erro = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//simple-snack-bar[contains(., 'endereço válido') or contains(., 'expedição!')]"))
        )
        if snackbar_erro:
            log('[COMUNICACAO][WARN] Detectado erro ao salvar (endereço inválido). Apagando destinatário e re-tentando...')
            
            # 1. Fechar o snackbar para não atrapalhar cliques
            try:
                btn_fechar_snack = snackbar_erro.find_element(By.XPATH, ".//button")
                driver.execute_script("arguments[0].click();", btn_fechar_snack)
            except Exception:
                pass
            
            # 2. Remover o destinatário com ícone vermelho usando a função local existente
            remover_destinatarios_invalidos(driver, debug=debug, log=log)
            time.sleep(1)
            
            # 3. Buscar botão salvar novamente e clicar
            btn_salvar_retry = None
            spans_retry = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and normalize-space(text())='Salvar']")
            for span in spans_retry:
                btn = span.find_element(By.XPATH, './ancestor::button[1]')
                if btn.is_displayed() and btn.is_enabled():
                    btn_salvar_retry = btn
                    break
            
            if btn_salvar_retry:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_salvar_retry)
                time.sleep(0.5)
                driver.execute_script('arguments[0].click();', btn_salvar_retry)
                log('[COMUNICACAO] Segundo clique em Salvar realizado após limpeza.')
                time.sleep(1)
            else:
                log('[COMUNICACAO][ERRO] Botão Salvar não encontrado para a segunda tentativa.')
                
    except Exception:
        # Se der timeout no WebDriverWait, significa que o erro não apareceu, segue a vida normal
        pass

    time.sleep(0.3)
    log('[DEBUG] Aguardando processamento do salvamento...')

    if gigs_extra:
        log('[GIGS_EXTRA][WARN] Criação de GIGS via minuta removida. Use criar_gigs na aba /detalhe antes do fluxo.')

    if str(sigilo).lower() in ("sim", "true", "1"):
        try:
            log('[COMUNICACAO] Executando visibilidade_sigilosos após salvamento...')
            executar_visibilidade_sigilosos_se_necessario(driver, True, debug=debug)
            log('[COMUNICACAO] Visibilidade extra aplicada por sigilo positivo.')
        except Exception as e:
            log(f"[COMUNICACAO][ERRO] Falha ao aplicar visibilidade extra: {e}")

    # Verificar confirmação explícita de salvamento (snackbar ou mudança de botão)
    try:
        # Prefer observer waiting for snackbar
        try:
            from Fix.core import aguardar_renderizacao_nativa
            ok_snack = aguardar_renderizacao_nativa(driver, 'simple-snack-bar', modo='aparecer', timeout=3)
        except Exception:
            ok_snack = False

        if ok_snack:
            log('[COMUNICACAO] Confirmação via snackbar detectada (observer).')
        else:
            # Fallback: existing predicate-based wait for snackbar or Alterar button
            from selenium.webdriver.support.ui import WebDriverWait
            def _salvo_ok(drv):
                try:
                    snacks = drv.find_elements(By.XPATH, "//simple-snack-bar")
                    for s in snacks:
                        txt = (s.text or '').lower()
                        if 'minuta' in txt and 'salva' in txt:
                            return True
                    spans = drv.find_elements(By.XPATH, "//span[contains(normalize-space(.), 'Alterar')]")
                    for sp in spans:
                        try:
                            btn = sp.find_element(By.XPATH, './ancestor::button[1]')
                            if btn.is_displayed() and btn.is_enabled():
                                return True
                        except Exception:
                            continue
                except Exception:
                    return False
                return False

            try:
                WebDriverWait(driver, 3).until(_salvo_ok)
                log('[COMUNICACAO] Confirmação visual de salvamento detectada (fallback).')
            except Exception:
                log('[COMUNICACAO][WARN] Não foi possível confirmar visualmente o salvamento da minuta. Tentando retry imediato...')
                try:
                    # localizar botão Salvar novamente e tentar um clique de retry
                    btn_salvar_retry = None
                    spans_retry = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and normalize-space(text())='Salvar']")
                    for span in spans_retry:
                        try:
                            btn = span.find_element(By.XPATH, './ancestor::button[1]')
                            if btn.is_displayed() and btn.is_enabled():
                                btn_salvar_retry = btn
                                break
                        except Exception:
                            continue

                    if btn_salvar_retry:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_salvar_retry)
                            driver.execute_script('arguments[0].click();', btn_salvar_retry)
                        except Exception:
                            pass

                    # nova espera por confirmação (observer preferred)
                    try:
                        ok_snack = aguardar_renderizacao_nativa(driver, 'simple-snack-bar', modo='aparecer', timeout=6)
                    except Exception:
                        ok_snack = False

                    if ok_snack:
                        log('[COMUNICACAO] Confirmação visual de salvamento detectada após retry (observer).')
                    else:
                        try:
                            WebDriverWait(driver, 3).until(_salvo_ok)
                            log('[COMUNICACAO] Confirmação visual de salvamento detectada após retry (fallback).')
                        except Exception:
                            log('[COMUNICACAO][ERRO] Retry de salvamento não confirmou o sucesso.')
                except Exception as e_retry:
                    log(f'[COMUNICACAO][ERRO] Falha no retry de salvamento: {e_retry}')
    except Exception as final_e:
        log(f'[COMUNICACAO][ERRO] Erro ao verificar confirmação de salvamento: {final_e}')

    log('Comunicação processual finalizada.')
    return True


def limpar_destinatarios_existentes(driver, debug=False):
    """Fluxo rápido: aguarda 1.5s, seleciona todos e clica em excluir sem verificações extras."""
    if debug:
        def log(msg):
            print(f"[DEBUG] {msg}")
    else:
        def log(_msg):
            return None

    try:
        # esperar tempo curto para a tela estabilizar (otimizado para velocidade)
        log('[COMUNICACAO] Fluxo rápido de limpeza: aguardando 0.6s para povoar destinatários (otimizado)')
        import time as _time
        _time.sleep(0.6)

        # Clicar no checkbox 'selecionar todos' (input interno) via JS - método rápido
        try:
            input_el = driver.find_element(By.ID, 'todosSelecionados-input')
            driver.execute_script("arguments[0].click();", input_el)
            log('[COMUNICACAO] Checkbox "Selecionar todos" clicado (input id)')
        except Exception as e:
            log(f'[COMUNICACAO][WARN] Não conseguiu clicar checkbox selecionar todos (input id): {e}')

        # Clicar no botão de excluir usando JS click (rápido) e prosseguir sem esperas longas
        try:
            btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Excluir expedientes selecionados"]')
            try:
                driver.execute_script("arguments[0].click();", btn)
                log('[COMUNICACAO][DEBUG] JS click no botão excluir realizado (rápido)')
            except Exception as e_js:
                log(f'[COMUNICACAO][DEBUG] JS click falhou: {e_js} - tentando Selenium click')
                try:
                    btn.click()
                    log('[COMUNICACAO][DEBUG] Selenium click no botão excluir realizado')
                except Exception as e_click:
                    log(f'[COMUNICACAO][WARN] Falha ao clicar botão excluir: {e_click}')

        except Exception as e:
            log(f'[COMUNICACAO][WARN] Botão excluir não encontrado pelo selector aria-label: {e}')

        # Não realizar verificações adicionais para manter fluxo rápido
        log('[COMUNICACAO] Fluxo rápido completado (prosseguindo sem checagem)')
        return True

    except Exception as e:
        log(f'[COMUNICACAO][ERRO] Falha geral no fluxo rápido de limpeza: {e}')
        return False