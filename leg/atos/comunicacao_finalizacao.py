import time
from selenium.webdriver.common.by import By
from Fix.selenium_base.wait_operations import wait_for_clickable, esperar_elemento
from Fix.selenium_base.click_operations import aguardar_e_clicar
from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.exceptions import ElementoNaoEncontradoError, NavegacaoError

from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario, preparar_campo_filtro_modelo


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
    """Retorna lista de WebElement <tr> cujo meio de expedicao e Correios."""
    resultado = []
    for linha in driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag'):
        try:
            meio = linha.find_element(By.CSS_SELECTOR, 'pje-pec-coluna-meio-expedicao .mat-select-min-line')
            if 'correio' in meio.text.strip().lower():
                resultado.append(linha)
        except Exception:
            continue
    return resultado


def _botao_confeccionar_correios(driver, indice=0):
    """Retorna WebElement do botao Confeccionar ato na linha Correios de indice N, re-consultando o DOM."""
    linhas = _linhas_correios(driver)
    if indice >= len(linhas):
        return None
    try:
        return linhas[indice].find_element(By.CSS_SELECTOR, 'pje-pec-coluna-confeccionar-ato button[aria-label="Confeccionar ato"]')
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
        if not preparar_campo_filtro_modelo(driver, log=debug):
            log('[COMUNICACAO][WARN] Falha ao preparar campo de filtro de modelo')
            return False

        campo_filtro = driver.find_element(By.CSS_SELECTOR, 'input#inputFiltro')
        driver.execute_script(
            "var el=arguments[0]; el.value = arguments[1]; el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); el.dispatchEvent(new Event('keyup', {bubbles:true}));",
            campo_filtro,
            modelo_nome
        )
        time.sleep(1.0)

        nodo = wait_for_clickable(driver, '.nodo-filtrado', timeout=10, by=By.CSS_SELECTOR)
        if not nodo:
            log(f'[COMUNICACAO][WARN] Nodo filtrado não encontrado para modelo "{modelo_nome}"')
            return False

        driver.execute_script('arguments[0].click();', nodo)
        time.sleep(0.5)

        btn_inserir = wait_for_clickable(driver, 'pje-dialogo-visualizar-modelo button', timeout=8, by=By.CSS_SELECTOR)
        if not btn_inserir:
            log(f'[COMUNICACAO][WARN] Botão inserir modelo não encontrado para "{modelo_nome}"')
            return False

        driver.execute_script('arguments[0].click();', btn_inserir)
        time.sleep(1.0)
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao inserir modelo "{modelo_nome}": {e}')
        raise NavegacaoError(f'inserir_modelo_por_nome({modelo_nome}): {e}')


def trocar_modelo_minuta(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    log('[COMUNICACAO] Iniciando troca de modelo na minuta')

    if not esperar_elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', timeout=20, by=By.CSS_SELECTOR):
        log('[COMUNICACAO][WARN] Tabela de destinatarios nao carregou na pagina de minutas')
        return False

    tipo_ato = _detectar_tipo_ato_para_modelo(driver, debug=debug, log=log)
    if not tipo_ato:
        log('[COMUNICACAO][WARN] Não foi possível detectar tipo de ato para troca de modelo')
        return False

    modelo_reaplicar = 'zsumc' if tipo_ato == 'ATSUM' else 'zordc'
    log(f'[COMUNICACAO] Tipo de ato detectado: {tipo_ato}; modelo a inserir: {modelo_reaplicar}')

    total = _contar_linhas_correios(driver)
    if total == 0:
        log('[COMUNICACAO][WARN] Nenhuma linha com Correios encontrada na tabela')
        return False
    log(f'[COMUNICACAO] {total} linha(s) com Correios encontrada(s)')

    for i in range(total):
        log(f'[COMUNICACAO] Processando linha Correios {i + 1}/{total}')
        botao = _botao_confeccionar_correios(driver, indice=i)
        if not botao:
            log(f'[COMUNICACAO][WARN] Botao Confeccionar ato nao encontrado para linha Correios {i + 1}')
            continue

        if not _abrir_e_limpar_editor(driver, botao, debug=debug, log=log):
            log(f'[COMUNICACAO][WARN] Falha ao abrir/limpar editor na linha {i + 1}, pulando')
            continue

        if not _inserir_modelo_por_nome(driver, modelo_reaplicar, debug=debug, log=log):
            log(f'[COMUNICACAO][WARN] Falha ao inserir modelo na linha {i + 1}, pulando')
            continue

        log(f'[COMUNICACAO] Modelo "{modelo_reaplicar}" inserido na linha {i + 1}/{total}')

    log(f'[COMUNICACAO] Troca de modelo concluida ({total} linha(s))')
    return True


def alterar_meio_expedicao(driver, debug=False, log=None, trocar_modelo=False):
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

        if trocar_modelo and alterados > 0:
            trocar_modelo_minuta(driver, debug=debug, log=log)

        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao alterar meio de expedição para Correio: {e}')
        raise NavegacaoError(f'alterar_meio_expedicao_para_correio: {e}')


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
        raise NavegacaoError(f'verificar_icones_vermelhos: {e}')


def _aguardar_confirmar_save_js(driver, timeout=15, log=None):
    """Race JS entre btnFinalizarExpedientes habilitado e snackbar de erro.

    Monitora em paralelo via MutationObserver nativo:
    - button[name="btnFinalizarExpedientes"] visivel E !disabled  -> {'tipo': 'assinar'}
    - snack-bar-container visivel                                  -> {'tipo': 'snackbar', 'texto': '...'}
    - timeout esgotado                                             -> {'tipo': 'timeout'}

    Vantagem critica sobre observer+esperar_elemento em serie:
    - Happy path: retorna assim que o botao fica habilitado (zero wait fixo)
    - Error path: retorna assim que o snackbar aparece (sem esperar timeout)
    - Verifica !disabled, nao apenas visibilidade (display !== none)
    """
    if log is None:
        def log(_msg): return None
    try:
        driver.set_script_timeout(timeout + 2)
    except Exception:
        pass
    resultado = driver.execute_async_script("""
        var timeoutMs = arguments[0] * 1000;
        var callback = arguments[arguments.length - 1];

        function checar() {
            var btn = document.querySelector('button[name="btnFinalizarExpedientes"]');
            if (btn && !btn.disabled && !btn.hasAttribute('disabled') && btn.offsetParent !== null) {
                return {tipo: 'assinar', texto: ''};
            }
            var snack = document.querySelector('snack-bar-container');
            if (snack && snack.offsetParent !== null) {
                return {tipo: 'snackbar', texto: snack.innerText || ''};
            }
            return null;
        }

        var r = checar();
        if (r) { callback(r); return; }

        var observer = new MutationObserver(function(mutations, me) {
            var r2 = checar();
            if (r2) { me.disconnect(); clearTimeout(tid); callback(r2); }
        });
        observer.observe(document.body, {
            childList: true, subtree: true,
            attributes: true, attributeFilter: ['disabled', 'aria-disabled', 'class', 'style']
        });
        var tid = setTimeout(function() {
            observer.disconnect();
            callback({tipo: 'timeout', texto: ''});
        }, timeoutMs);
    """, timeout)

    if resultado is None:
        resultado = {'tipo': 'timeout', 'texto': ''}
    log(f'[SAVE_JS] tipo={resultado.get("tipo")} texto="{str(resultado.get("texto", ""))[:80]}')
    return resultado


def salvar_minuta_final(driver, sigilo, gigs_extra=None, debug=False, log=None, executar_visibilidade=False, assinar=False):
    if log is None:
        def log(_msg):
            return None

    # --- 1. Localizar botão Salvar (igual ao atalhos.js: name="btnSalvarExpedientes") ---
    btn_salvar = wait_for_clickable(driver, 'button[name="btnSalvarExpedientes"]', timeout=10, by=By.CSS_SELECTOR)
    if not btn_salvar:
        # Fallback: span text 'Salvar' (compatibilidade)
        try:
            spans = driver.find_elements(By.XPATH, "//span[contains(@class,'mat-button-wrapper') and normalize-space(text())='Salvar']")
            for span in spans:
                candidate = span.find_element(By.XPATH, './ancestor::button[1]')
                if candidate.is_displayed() and candidate.is_enabled():
                    btn_salvar = candidate
                    break
        except Exception:
            pass

    if not btn_salvar:
        log('[COMUNICACAO][ERRO] Botão Salvar não encontrado!')
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_salvar)
        driver.execute_script("arguments[0].click();", btn_salvar)
        log('[DEBUG] Clique no botão Salvar realizado.')
    except Exception as e:
        log(f'[COMUNICACAO][ERRO] Não foi possível clicar no botão Salvar: {e}')
        raise NavegacaoError(f'clicar_botao_salvar: {e}')

    # --- 2+3. Aguardar btnFinalizarExpedientes habilitado OU snackbar de erro ---
    # Modo 'habilitado' verifica visivel E !disabled em uma unica chamada.
    # Timeout reduzido: o fallback por texto é instantâneo e sempre funciona quando o botão está presente.
    if aguardar_renderizacao_nativa(driver, 'button[name="btnFinalizarExpedientes"]', 'habilitado', 3):
        # Happy path: botao habilitado, verificar se ha snackbar de erro ANTES de prosseguir
        try:
            snack = driver.find_element(By.CSS_SELECTOR, 'snack-bar-container')
            texto_snack = snack.get_attribute('innerText') or ''
        except Exception:
            texto_snack = ''

        if 'Selecione o endere' in texto_snack:
            log(f'[COMUNICACAO][WARN] Snackbar de endereco invalido: "{texto_snack[:80]}"')
            aguardar_renderizacao_nativa(driver, 'snack-bar-container', 'sumir', 3)
        else:
            if texto_snack:
                log(f'[COMUNICACAO][WARN] Snackbar inesperado: "{texto_snack[:80]}"')

        btn_finalizar = None
        try:
            btn_finalizar = driver.find_element(By.CSS_SELECTOR, 'button[name="btnFinalizarExpedientes"]')
            log('[COMUNICACAO] Salvamento confirmado — botao Assinar habilitado.')
        except Exception:
            pass
    else:
        btn_finalizar = None
        # Fallback por texto
        try:
            elementos = driver.find_elements(By.XPATH, "//button[.//span[contains(normalize-space(text()),'Assinar ato')]]")
            btn_finalizar = next((b for b in elementos if b.is_displayed() and b.is_enabled()), None)
        except Exception:
            pass
        if btn_finalizar:
            log('[COMUNICACAO][WARN] Timeout observer mas botao Assinar encontrado por fallback texto.')
        else:
            log('[COMUNICACAO][ERRO] Botao Assinar nao habilitou em 15s.')
            return False

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
                pass

        try:
            from Fix.assinatura_cookies import reinjetar_antes_assinatura
            reinjetar_antes_assinatura(driver)
        except Exception:
            pass

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
                pass
            if _debug_assin and _estado_antes:
                try:
                    salvar_delta(diff_estado(_estado_antes, capturar_estado_browser(driver)))
                except Exception:
                    pass
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
            aguardar_renderizacao_nativa(driver, 'snack-bar-container', modo='aparecer', timeout=20)
            try:
                from Fix.assinatura_cookies import capturar_apos_assinatura
                capturar_apos_assinatura(driver)
            except Exception:
                pass
            if _debug_assin and _estado_antes:
                try:
                    salvar_delta(diff_estado(_estado_antes, capturar_estado_browser(driver)))
                except Exception:
                    pass
            snack_sucesso = esperar_elemento(driver, 'snack-bar-container', timeout=5, by=By.CSS_SELECTOR)
            if snack_sucesso:
                txt = snack_sucesso.text or ''
                if 'assinado' in txt.lower() and 'sucesso' in txt.lower():
                    log(f'[COMUNICACAO] Assinatura confirmada: "{txt.strip()}"')
                else:
                    log(f'[COMUNICACAO][WARN] Snackbar apareceu mas texto inesperado: "{txt.strip()}"')
            else:
                log('[COMUNICACAO][WARN] Snackbar de confirmação de assinatura não detectado em 30s.')

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
        raise NavegacaoError(f'limpar_destinatarios_existentes: {e}')