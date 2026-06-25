import time
from selenium.webdriver.common.by import By
from Fix.selenium_base.wait_operations import wait_for_clickable, esperar_elemento
from Fix.selenium_base.click_operations import aguardar_e_clicar
from Fix.core import aguardar_renderizacao_nativa
from Fix.errors import ElementoNaoEncontradoError, NavegacaoError
from Fix.log import log_start, log_fim
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario


def _detectar_tipo_ato_para_modelo(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        elementos = driver.find_elements(
            By.XPATH,
            "//span[contains(normalize-space(.),'ATOrd')] | //span[contains(normalize-space(.),'ATSum')]"
        )
        for elemento in elementos:
            texto = (elemento.text or '').strip()
            if 'ATSum' in texto:
                return 'ATSUM'
            if 'ATOrd' in texto:
                return 'ATORD'

        elementos = driver.find_elements(
            By.XPATH,
            "//*[contains(normalize-space(.),'ATOrd')] | //*[contains(normalize-space(.),'ATSum')]"
        )
        for elemento in elementos:
            texto = (elemento.text or '').strip()
            if 'ATSum' in texto:
                return 'ATSUM'
            if 'ATOrd' in texto:
                return 'ATORD'

        if debug:
            log('[COMUNICACAO] Tipo de ato não detectado na página para trocar modelo')
        return None
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao detectar tipo de ato: {e}')
        return None


def _linhas_correios(driver):
    """Retorna lista de WebElement <tr> cujo meio de expedicao e Correios.
    Usa XPath com translate para case-insensitive — ignora hierarquia Angular."""
    return driver.find_elements(By.XPATH,
        '//tbody[contains(@class,"cdk-drop-list")]//tr[contains(@class,"cdk-drag")]'
        '[.//span[contains(@class,"mat-select-min-line") and '
        'contains(translate(.,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"correio")]]'
    )


def _botao_confeccionar_correios(driver, indice=0):
    """Retorna WebElement do botao Confeccionar ato na linha Correios de indice N, re-consultando o DOM."""
    linhas = _linhas_correios(driver)
    if indice >= len(linhas):
        return None
    try:
        return linhas[indice].find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato"]')
    except Exception:
        return None


def _contar_linhas_correios(driver):
    return len(_linhas_correios(driver))


def _abrir_e_limpar_editor(driver, botao, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        driver.execute_script('arguments[0].scrollIntoView({block: "center", inline: "center"});', botao)
        try:
            botao.click()
        except Exception:
            driver.execute_script('arguments[0].click();', botao)
        log('[COMUNICACAO] Clique no botao Confeccionar ato realizado')

        aguardar_renderizacao_nativa(driver, '.ck-editor__editable[contenteditable="true"]', modo='aparecer', timeout=15)
        editor = wait_for_clickable(driver, '.ck-editor__editable[contenteditable="true"]', timeout=15, by=By.CSS_SELECTOR)
        if not editor:
            log('[COMUNICACAO][WARN] Editor CKEditor nao apareceu apos clicar no botao de edicao')
            return False
        log('[COMUNICACAO] Editor CKEditor aberto')

        limpo = driver.execute_script("""
            var el = arguments[0];
            var ck = el.ckeditorInstance || (el.closest('.ck-editor') ? el.closest('.ck-editor').ckeditorInstance : null);
            if (ck) {
                ck.setData('');
                return ck.getData().trim() === '';
            }
            el.focus();
            el.innerHTML = '';
            el.dispatchEvent(new InputEvent('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            return el.innerText.trim().length === 0;
        """, editor)

        if not limpo:
            log('[COMUNICACAO][WARN] Editor nao ficou vazio apos limpeza via ckInstance.setData - abortando linha')
            return False

        if debug:
            log('[COMUNICACAO][DEBUG] Editor limpo com sucesso via ckInstance')
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao abrir/limpar editor: {e}')
        raise NavegacaoError(f'abrir_limpar_editor: {e}')


def _inserir_modelo_por_nome(driver, modelo_nome, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        campo_ok = driver.execute_script("""
            var nomeModelo = arguments[0];
            var filtro = document.querySelector('input#inputFiltro');
            if (!filtro) return false;
            filtro.removeAttribute('disabled');
            filtro.removeAttribute('readonly');
            filtro.focus();
            filtro.value = nomeModelo;
            filtro.dispatchEvent(new Event('input', {bubbles: true}));
            filtro.dispatchEvent(new Event('change', {bubbles: true}));
            filtro.dispatchEvent(new Event('keyup', {bubbles: true}));
            return true;
        """, modelo_nome)

        if not campo_ok:
            log('[COMUNICACAO][WARN] Campo de filtro de modelo nao encontrado')
            return False
        try:
            aguardar_renderizacao_nativa(driver, '.nodo-filtrado', modo='aparecer', timeout=5)
        except Exception:
            pass

        nodo = wait_for_clickable(driver, '.nodo-filtrado', timeout=10, by=By.CSS_SELECTOR)
        if not nodo:
            log(f'[COMUNICACAO][WARN] Nodo filtrado não encontrado para modelo "{modelo_nome}"')
            return False

        driver.execute_script('arguments[0].click();', nodo)
        try:
            aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', modo='aparecer', timeout=5)
        except Exception:
            pass

        btn_inserir = wait_for_clickable(driver, 'pje-dialogo-visualizar-modelo button', timeout=8, by=By.CSS_SELECTOR)
        if not btn_inserir:
            log(f'[COMUNICACAO][WARN] Botão inserir modelo não encontrado para "{modelo_nome}"')
            return False

        driver.execute_script('arguments[0].click();', btn_inserir)

        # Polling snackbar (idêntico ao fluxo geral de preenchimento)
        for _poll in range(15):  # até 3s
            if driver.execute_script("""
                var bars = document.querySelectorAll('simple-snack-bar');
                for (var i = 0; i < bars.length; i++) {
                    var t = bars[i].textContent || '';
                    if (t.indexOf('Modelo de documento inserido com sucesso') !== -1) return true;
                }
                return false;
            """):
                return True
            time.sleep(0.2)

        if debug:
            log(f'[COMUNICACAO] Snackbar modelo não detectado para "{modelo_nome}", prosseguindo')
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao inserir modelo "{modelo_nome}": {e}')
        raise NavegacaoError(f'inserir_modelo_por_nome({modelo_nome}): {e}')


def trocar_modelo_minuta(driver, modelo_troca=None, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    log(f'[TROCAR_MODELO] Iniciando troca de modelo (modelo_troca={modelo_troca})')

    if not esperar_elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', timeout=20, by=By.CSS_SELECTOR):
        log('[TROCAR_MODELO] Tabela de destinatários não carregou')
        return False
        
    time.sleep(2) # Aguarda Angular renderizar dropdowns de todas as linhas

    tipo_ato = _detectar_tipo_ato_para_modelo(driver, debug=debug, log=log)
    if not tipo_ato:
        log('[TROCAR_MODELO] Não foi possível detectar tipo de ato')
        return False

    if modelo_troca:
        modelo_reaplicar = modelo_troca
    else:
        modelo_reaplicar = 'zsumc' if tipo_ato == 'ATSUM' else 'zordc'
    log(f'[TROCAR_MODELO] Tipo={tipo_ato}, modelo={modelo_reaplicar}')

    total = _contar_linhas_correios(driver)
    total_linhas = len(driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag'))
    log(f'[TROCAR_MODELO] Encontradas {total_linhas} linhas na tabela de destinatários, sendo {total} de Correios')
    if total == 0:
        log('[TROCAR_MODELO] Nenhuma linha com Correios encontrada')
        return False
    log(f'[TROCAR_MODELO] {total} linha(s) Correios para processar')

    for i in range(total):
        log(f'[TROCAR_MODELO] Linha {i + 1}/{total}: abrindo editor...')
        botao = _botao_confeccionar_correios(driver, indice=i)
        if not botao:
            log(f'[TROCAR_MODELO] Botão Confeccionar ato não encontrado na linha {i + 1}')
            continue

        if not _abrir_e_limpar_editor(driver, botao, debug=debug, log=log):
            log(f'[TROCAR_MODELO] Falha ao abrir/limpar editor na linha {i + 1}')
            continue

        if not _inserir_modelo_por_nome(driver, modelo_reaplicar, debug=debug, log=log):
            log(f'[TROCAR_MODELO] Falha ao inserir modelo na linha {i + 1}')
            continue

        # Finalizar ato individual (igual dump: inserir → snackbar → finalizar)
        try:
            btn_finalizar = wait_for_clickable(
                driver,
                'pje-pec-dialogo-ato button[aria-label="Finalizar minuta"]',
                timeout=10,
                by=By.CSS_SELECTOR
            )
            if not btn_finalizar:
                log(f'[TROCAR_MODELO] Botão Finalizar não encontrado na linha {i + 1}')
                continue

            driver.execute_script('arguments[0].click();', btn_finalizar)

            # Polling snackbar "Ato elaborado" (idêntico ao fluxo geral)
            for _poll in range(25):  # até 5s
                if driver.execute_script("""
                    var bars = document.querySelectorAll('simple-snack-bar');
                    for (var i = 0; i < bars.length; i++) {
                        var t = bars[i].textContent || '';
                        if (t.indexOf('Ato elaborado com sucesso') !== -1) return true;
                    }
                    return false;
                """):
                    log(f'[TROCAR_MODELO] Linha {i + 1}/{total} finalizada')
                    break
                time.sleep(0.2)
        except Exception as e:
            log(f'[TROCAR_MODELO] Erro ao finalizar linha {i + 1}: {e}')
            continue

    log(f'[TROCAR_MODELO] Concluído — {total} linha(s) processadas')
    return True


def alterar_meio_expedicao(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    log_start('COMUNICACAO_MEIO_EXPEDICAO')
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
                # Fallback: WebDriverWait
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag'))
                    )
                    linhas_tabela = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
                except Exception:
                    log('[COMUNICACAO][WARN] Timeout aguardando destinatários, prosseguindo mesmo assim')
                    return False

                tempo_dest = time.perf_counter() - t_dest
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Destinatários apareceram em {tempo_dest:.3f}s (WebDriverWait)')
            else:
                tempo_dest = time.perf_counter() - t_dest
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Destinatários apareceram em {tempo_dest:.3f}s (observer)')

            # Aguardar estabilização via WebDriverWait
            log('[COMUNICACAO] Verificação rápida de estabilização...')
            contagem_inicial = len(linhas_tabela)
            try:
                WebDriverWait(driver, 2).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')) >= contagem_inicial
                )
            except Exception:
                pass
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
                span_meio = linha.find_element(By.CSS_SELECTOR, '.pec-item-coluna-meio-expedicao-tabela-destinatarios .mat-select-value-text .mat-select-min-line')
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

                try:
                    if not esperar_elemento(driver, 'mat-option', timeout=2, by=By.CSS_SELECTOR):
                        raise Exception('Opções do dropdown não carregaram')
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
                        # UI-transition: aguardar dropdown fechar apos selecao
                        try:
                            aguardar_renderizacao_nativa(driver, 'div.cdk-overlay-pane', modo='sumir', timeout=2)
                        except Exception:
                            pass
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

        log_fim('COMUNICACAO_MEIO_EXPEDICAO', {'status': 'sucesso', 'alterados': alterados, 'total': total_linhas})
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao alterar meio de expedição para Correio: {e}')
        log_fim('COMUNICACAO_MEIO_EXPEDICAO', {'status': 'erro', 'motivo': str(e)[:80]})
        raise NavegacaoError(f'alterar_meio_expedicao_para_correio: {e}')


def salvar_minuta_final(driver, sigilo, gigs_extra=None, debug=False, log=None, executar_visibilidade=False, assinar=False):
    if log is None:
        def log(_msg):
            return None

    log_start('COMUNICACAO_SALVAR_MINUTA')
    # --- 1. Salvar — seletor canônico do gigs-plugin.js ---
    # JS: await esperarElemento('pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]')
    btn_salvar = esperar_elemento(driver, 'pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]', timeout=15, by=By.CSS_SELECTOR)
    if not btn_salvar:
        log('[COMUNICACAO][ERRO] Botão Salvar não encontrado!')
        log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'btn_salvar_nao_encontrado'})
        return False

    try:
        driver.execute_script("arguments[0].click();", btn_salvar)
        log('[COMUNICACAO] Clique no botão Salvar realizado.')
    except Exception as e:
        log(f'[COMUNICACAO][ERRO] Não foi possível clicar no botão Salvar: {e}')
        raise NavegacaoError(f'clicar_botao_salvar: {e}')

    # --- 2. Checar snackbar de endereço inválido (único erro relevante pós-salvar) ---
    try:
        texto_snack = driver.find_element(By.CSS_SELECTOR, 'snack-bar-container').get_attribute('innerText') or ''
    except Exception:
        texto_snack = ''
    if 'Selecione o endere' in texto_snack:
        log(f'[COMUNICACAO][ERRO] Snackbar endereço inválido: "{texto_snack[:80]}" — abortando.')
        log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'endereco_invalido'})
        return False

    # --- 3. Aguardar botão Assinar — seletor canônico do gigs-plugin.js ---
    # JS: await esperarElemento('pje-pec-tabela-destinatarios button[aria-label="Assinar ato(s)"],
    #                           pje-pec-tabela-destinatarios button[aria-label="Enviar para assinatura"]')
    _SEL_ASSINAR = (
        'pje-pec-tabela-destinatarios button[aria-label="Assinar ato(s)"],'
        'pje-pec-tabela-destinatarios button[aria-label="Enviar para assinatura"]'
    )
    btn_finalizar = esperar_elemento(driver, _SEL_ASSINAR, timeout=30, by=By.CSS_SELECTOR)
    if not btn_finalizar:
        log('[COMUNICACAO][ERRO] Botão Assinar não habilitou em 30s.')
        log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'assinar_nao_habilitou_30s'})
        return False
    log('[COMUNICACAO] Botão Assinar disponível.')

    if gigs_extra:
        log('[GIGS_EXTRA][WARN] Criação de GIGS via minuta removida. Use criar_gigs na aba /detalhe antes do fluxo.')

    # --- 4. Assinar se solicitado ---
    if assinar:
        try:
            from Fix.debug_assinatura import ativo as _dbg_ativo, capturar_estado_browser, diff_estado, salvar_delta
            _debug_assin = _dbg_ativo()
        except Exception:
            _debug_assin = False

        _estado_antes = None
        if _debug_assin:
            try:
                _estado_antes = capturar_estado_browser(driver)
            except Exception:
                log('[COMUNICACAO][DEBUG] capturar_estado_browser falhou (não crítico)')

        try:
            from Fix.assinatura_cookies import reinjetar_antes_assinatura
            reinjetar_antes_assinatura(driver)
        except Exception:
            log('[COMUNICACAO][DEBUG] reinjetar_antes_assinatura não disponível (1a assinatura)')

        if not btn_finalizar:
            log('[COMUNICACAO][ERRO] Botão Assinar não encontrado — não é possível assinar.')
            log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'btn_finalizar_none_antes_assinar'})
            raise NavegacaoError('assinar_atos: btn_finalizar é None')
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_finalizar)
            driver.execute_script("arguments[0].click();", btn_finalizar)
            log('[COMUNICACAO] Botão Assinar ato(s) clicado.')
        except Exception as e:
            log(f'[COMUNICACAO][ERRO] Falha ao clicar em Assinar ato(s): {e}')
            log('Comunicação processual finalizada.')
            raise NavegacaoError(f'assinar_atos: {e}')

        # --- 4a. Detectar dialog de validação por dispositivo móvel ---
        # Usar observer+CSS silencioso: não gera [ERRO] quando o dialog não aparece
        # (caminho esperado quando cookies de sessão já estão válidos).
        _TIMEOUT_VALIDACAO_MOVEL = 180  # 3 minutos para o usuário autenticar
        _dialog_apareceu = aguardar_renderizacao_nativa(driver, 'input.codigo-otp', 'aparecer', 3)
        try:
            dialog_movel = driver.find_element(By.CSS_SELECTOR, 'input.codigo-otp') if _dialog_apareceu else None
        except Exception:
            dialog_movel = None

        if dialog_movel:
            log('[COMUNICACAO] Dialog "Validacao por dispositivo movel" detectado.')
            # --- 4b. Se já temos cookies de sessão registrados, tentar reconfirmar via radio "sessão" ---
            try:
                from Fix.assinatura_cookies import cache_tem_cookies
                _tem_cache = cache_tem_cookies()
            except Exception:
                _tem_cache = False

            if _tem_cache:
                log('[COMUNICACAO] Cache de assinatura com cookies — tentando reconfirmar via "Utilizar certificado digital nesta sessao"...')
                _dialog_fechou_auto = False
                try:
                    # Clicar no radio "Utilizar certificado digital nesta sessão" (value="2" é fixo no componente Angular)
                    _radio = esperar_elemento(
                        driver,
                        'mat-dialog-container input[type="radio"][value="2"]',
                        timeout=4,
                        by=By.CSS_SELECTOR
                    )
                    if _radio:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center', behavior:'instant'}); arguments[0].click();",
                            _radio
                        )
                        log('[COMUNICACAO] Radio "Utilizar certificado digital nesta sessao" clicado (value=2).')
                    else:
                        # fallback por value direto sem container
                        _radio_fb = esperar_elemento(
                            driver,
                            'input[type="radio"][value="2"]',
                            timeout=3,
                            by=By.CSS_SELECTOR
                        )
                        if _radio_fb:
                            driver.execute_script("arguments[0].click();", _radio_fb)
                            log('[COMUNICACAO] Radio clicado via fallback value=2.')
                        else:
                            log('[COMUNICACAO][WARN] Radio value=2 nao localizado — aguardando confirmacao manual.')
                    # Clicar em Confirmar
                    _btn_confirmar = esperar_elemento(
                        driver,
                        '//button[@aria-label="Confirmar" or .//span[normalize-space(text())="Confirmar"]]',
                        timeout=4,
                        by=By.XPATH
                    )
                    if _btn_confirmar:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center', behavior:'instant'}); arguments[0].click();",
                            _btn_confirmar
                        )
                        log('[COMUNICACAO] Botao Confirmar clicado — aguardando dialog fechar...')
                        _dialog_fechou_auto = aguardar_renderizacao_nativa(
                            driver, 'mat-dialog-container', modo='sumir', timeout=15
                        )
                        if _dialog_fechou_auto:
                            log('[COMUNICACAO] Dialog fechou automaticamente apos reconfirmacao por sessao.')
                        else:
                            log('[COMUNICACAO][WARN] Dialog nao fechou em 15s apos Confirmar — pode precisar de acao manual.')
                    else:
                        log('[COMUNICACAO][WARN] Botao Confirmar nao localizado no dialog.')
                except Exception as _e_auto:
                    log(f'[COMUNICACAO][WARN] Erro na tentativa automatica de reconfirmacao: {_e_auto}')
                    _dialog_fechou_auto = False

                if not _dialog_fechou_auto:
                    log('[COMUNICACAO] Aguardando confirmacao manual do usuario (timeout 3 min)...')
                    dialog_sumiu = aguardar_renderizacao_nativa(
                        driver, 'mat-dialog-container', modo='sumir', timeout=_TIMEOUT_VALIDACAO_MOVEL
                    )
                    if not dialog_sumiu:
                        log('[COMUNICACAO][ERRO] Timeout de 3 min aguardando autenticacao por dispositivo movel — assinatura nao confirmada.')
                        log('Comunicacao processual finalizada.')
                        return False
            else:
                log('[COMUNICACAO] Sem cache de cookies (1a assinatura) — aguardando autenticacao do usuario...')
                # Aguardar dialog fechar via MutationObserver (sem polling nem time.sleep)
                dialog_sumiu = aguardar_renderizacao_nativa(
                    driver, 'mat-dialog-container', modo='sumir', timeout=_TIMEOUT_VALIDACAO_MOVEL
                )
                if not dialog_sumiu:
                    log('[COMUNICACAO][ERRO] Timeout de 3 min aguardando autenticacao por dispositivo movel — assinatura nao confirmada.')
                    log('Comunicacao processual finalizada.')
                    return False

            log('[COMUNICACAO] Dialog de validacao movel fechado — verificando confirmacao...')
            try:
                from Fix.assinatura_cookies import capturar_apos_assinatura
                capturar_apos_assinatura(driver)
            except Exception:
                log('[COMUNICACAO][DEBUG] capturar_apos_assinatura não disponível')
            if _debug_assin and _estado_antes:
                try:
                    salvar_delta(diff_estado(_estado_antes, capturar_estado_browser(driver)))
                except Exception:
                    log('[COMUNICACAO][DEBUG] salvar_delta falhou (não crítico)')
            _lista_vazia = bool(driver.find_elements(
                By.XPATH,
                "//span[contains(normalize-space(.),'Não há expedientes sendo confeccionados')]"
            ))
            if _lista_vazia:
                log('[COMUNICACAO] Assinatura confirmada — lista de expedientes vazia.')
            else:
                snack_final = esperar_elemento(driver, 'snack-bar-container', timeout=15, by=By.CSS_SELECTOR)
                if snack_final:
                    txt = snack_final.text or ''
                    if 'assinado' in txt.lower() and 'sucesso' in txt.lower():
                        log(f'[COMUNICACAO] Assinatura confirmada: "{txt.strip()}"')
                    else:
                        log(f'[COMUNICACAO][WARN] Snackbar com texto inesperado após dialog fechar: "{txt.strip()}"')
                else:
                    log('[COMUNICACAO][WARN] Snackbar de confirmação não detectado em 15s após dialog fechar.')
        else:
            # Sem dialog → assinatura direta; confirmar via snackbar
            log('[COMUNICACAO] Sem dialog de validação móvel — aguardando confirmação de assinatura...')
            _lista_vazia_nd = bool(driver.find_elements(
                By.XPATH,
                "//span[contains(normalize-space(.),'Não há expedientes sendo confeccionados')]"
            ))
            if _lista_vazia_nd:
                log('[COMUNICACAO] Assinatura confirmada — lista de expedientes vazia.')
            else:
                aguardar_renderizacao_nativa(driver, 'snack-bar-container', modo='aparecer', timeout=20)
                try:
                    from Fix.assinatura_cookies import capturar_apos_assinatura
                    capturar_apos_assinatura(driver)
                except Exception:
                    log('[COMUNICACAO][DEBUG] capturar_apos_assinatura não disponível')
                if _debug_assin and _estado_antes:
                    try:
                        salvar_delta(diff_estado(_estado_antes, capturar_estado_browser(driver)))
                    except Exception:
                        log('[COMUNICACAO][DEBUG] salvar_delta falhou (não crítico)')
                snack_sucesso = esperar_elemento(driver, 'snack-bar-container', timeout=5, by=By.CSS_SELECTOR)
                if snack_sucesso:
                    txt = snack_sucesso.text or ''
                    if 'assinado' in txt.lower() and 'sucesso' in txt.lower():
                        log(f'[COMUNICACAO] Assinatura confirmada: "{txt.strip()}"')
                    else:
                        log(f'[COMUNICACAO][WARN] Snackbar apareceu mas texto inesperado: "{txt.strip()}"')
                else:
                    log('[COMUNICACAO][WARN] Snackbar de confirmação de assinatura não detectado em 30s.')

    log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'sucesso'})
    log('Comunicação processual finalizada.')
    return True


