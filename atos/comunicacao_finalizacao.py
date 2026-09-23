import time
from typing import Any
from Fix.core import (
    aguardar_renderizacao_nativa,
    safe_click_no_scroll,
    safe_click,
    esperar_elemento,
    wait_for_clickable,
    preencher_campo,
)
from Fix.browser_suporte import click_headless_safe, scroll_to_element_safe
from Fix.errors import NavegacaoError
from Fix.log import log_start, log_fim
from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from Fix import espera


def _detectar_tipo_ato_para_modelo(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        elementos = espera.elementos(
            driver,
            "//span[contains(normalize-space(.),'ATOrd')] | //span[contains(normalize-space(.),'ATSum')]",
            teto=2
        )
        for elemento in elementos:
            texto = (getattr(elemento, 'text', '') or '').strip()
            if 'ATSum' in texto:
                return 'ATSUM'
            if 'ATOrd' in texto:
                return 'ATORD'

        elementos = espera.elementos(
            driver,
            "//*[contains(normalize-space(.),'ATOrd')] | //*[contains(normalize-space(.),'ATSum')]",
            teto=2
        )
        for elemento in elementos:
            texto = (getattr(elemento, 'text', '') or '').strip()
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
    """Retorna lista de elementos <tr> cujo meio de expedicao e Correios."""
    xpath = (
        '//tbody[contains(@class,"cdk-drop-list")]//tr[contains(@class,"cdk-drag")]'
        '[.//span[contains(@class,"mat-select-min-line") and '
        'contains(translate(.,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"correio")]]'
    )
    return espera.elementos(driver, xpath, teto=2)


def _botao_confeccionar_correios(driver, indice=0):
    """Retorna elemento do botao Confeccionar ato na linha Correios de indice N, re-consultando o DOM."""
    xpath = (
        f'(//tbody[contains(@class,"cdk-drop-list")]//tr[contains(@class,"cdk-drag")]'
        f'[.//span[contains(@class,"mat-select-min-line") and '
        f'contains(translate(.,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"correio")]]'
        f'//button[@aria-label="Confeccionar ato"])[{indice + 1}]'
    )
    return espera.elemento(driver, xpath, teto=2)


def _contar_linhas_correios(driver):
    return len(_linhas_correios(driver))


def _abrir_e_limpar_editor(driver, botao, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        scroll_to_element_safe(driver, botao)
        safe_click_no_scroll(driver, botao)
        log('[COMUNICACAO] Clique no botao Confeccionar ato realizado')

        aguardar_renderizacao_nativa(driver, '.ck-editor__editable[contenteditable="true"]', modo='aparecer', timeout=15)
        editor = wait_for_clickable(driver, '.ck-editor__editable[contenteditable="true"]', timeout=15)
        if not editor:
            log('[COMUNICACAO][WARN] Editor CKEditor nao apareceu apos clicar no botao de edicao')
            return False
        log('[COMUNICACAO] Editor CKEditor aberto')

        limpo = False
        if hasattr(editor, '_js'):
            limpo = bool(editor._js("""el => {
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
            }"""))
        elif hasattr(driver, 'page'):
            limpo = bool(driver.page.evaluate("""() => {
                var el = document.querySelector('.ck-editor__editable[contenteditable="true"]');
                if (!el) return false;
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
            }"""))

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
        campo_ok = False
        if hasattr(driver, 'page'):
            campo_ok = bool(driver.page.evaluate("""nomeModelo => {
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
            }""", modelo_nome))
        else:
            campo_ok = preencher_campo(driver, 'input#inputFiltro', modelo_nome)

        if not campo_ok:
            log('[COMUNICACAO][WARN] Campo de filtro de modelo nao encontrado')
            return False
        try:
            aguardar_renderizacao_nativa(driver, '.nodo-filtrado', modo='aparecer', timeout=5)
        except Exception:
            pass

        nodo = wait_for_clickable(driver, '.nodo-filtrado', timeout=10)
        if not nodo:
            log(f'[COMUNICACAO][WARN] Nodo filtrado não encontrado para modelo "{modelo_nome}"')
            return False

        safe_click_no_scroll(driver, nodo)
        try:
            aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', modo='aparecer', timeout=5)
        except Exception:
            pass

        btn_inserir = wait_for_clickable(driver, 'pje-dialogo-visualizar-modelo button', timeout=8)
        if not btn_inserir:
            log(f'[COMUNICACAO][WARN] Botão inserir modelo não encontrado para "{modelo_nome}"')
            return False

        safe_click_no_scroll(driver, btn_inserir)

        # Polling snackbar (idêntico ao fluxo geral de preenchimento)
        snack_ok = espera.ate_texto(driver, 'simple-snack-bar', 'Modelo de documento inserido com sucesso', teto=3)
        if not snack_ok and debug:
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

    if not esperar_elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', timeout=20):
        log('[TROCAR_MODELO] Tabela de destinatários não carregou')
        return False
        
    espera.assentar(driver, 2, motivo='Angular renderizar dropdowns de todas as linhas')

    tipo_ato = _detectar_tipo_ato_para_modelo(driver, debug=debug, log=log)
    if not tipo_ato:
        log('[TROCAR_MODELO] Não foi possível detectar tipo de ato')
        return False

    if modelo_troca:
        modelo_reaplicar = modelo_troca
    else:
        modelo_reaplicar = 'ar-sum' if tipo_ato == 'ATSUM' else 'ar-ord'
    log(f'[TROCAR_MODELO] Tipo={tipo_ato}, modelo={modelo_reaplicar}')

    total = _contar_linhas_correios(driver)
    total_linhas = len(espera.elementos(driver, 'tbody.cdk-drop-list tr.cdk-drag', teto=2))
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
                timeout=10
            )
            if not btn_finalizar:
                log(f'[TROCAR_MODELO] Botão Finalizar não encontrado na linha {i + 1}')
                continue

            safe_click_no_scroll(driver, btn_finalizar)

            # Aguardar confirmação de ato elaborado
            espera.ate_texto(driver, 'simple-snack-bar', 'Ato elaborado com sucesso', teto=5)
            log(f'[TROCAR_MODELO] Linha {i + 1}/{total} finalizada')
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
        try:
            aguardar_renderizacao_nativa(driver, 'tbody.cdk-drop-list tr.cdk-drag', modo='aparecer', timeout=1)
        except Exception:
            pass
        linhas_prontas = espera.elementos(driver, 'tbody.cdk-drop-list tr.cdk-drag', teto=1)
        if len(linhas_prontas) > 0:
            log('[COMUNICACAO] Tabela já contém destinatários - pulando esperas')
            linhas_tabela = linhas_prontas
            total_linhas = len(linhas_tabela)
        else:
            log('[COMUNICACAO] Verificando spinner/modal rapidamente (observer)...')
            t_spinner = time.perf_counter()
            try:
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

            log('[COMUNICACAO] Aguardando destinatários aparecerem (observer)...')
            t_dest = time.perf_counter()
            try:
                ok_rows = aguardar_renderizacao_nativa(driver, 'tbody.cdk-drop-list tr.cdk-drag', modo='aparecer', timeout=5)
            except Exception:
                ok_rows = False

            if not ok_rows:
                if espera.elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', teto=5, visivel=False):
                    linhas_tabela = espera.elementos(driver, 'tbody.cdk-drop-list tr.cdk-drag', teto=2)
                else:
                    log('[COMUNICACAO][WARN] Timeout aguardando destinatários, prosseguindo mesmo assim')
                    return False

                tempo_dest = time.perf_counter() - t_dest
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Destinatários apareceram em {tempo_dest:.3f}s (espera.elemento)')
            else:
                tempo_dest = time.perf_counter() - t_dest
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Destinatários apareceram em {tempo_dest:.3f}s (observer)')

            log('[COMUNICACAO] Verificação rápida de estabilização...')
            contagem_inicial = len(linhas_tabela)
            espera.ate_js(
                driver,
                "__pjeEls('tbody.cdk-drop-list tr.cdk-drag').length >= %d" % contagem_inicial,
                teto=2,
            )
            linhas_atual = espera.elementos(driver, 'tbody.cdk-drop-list tr.cdk-drag', teto=1)
            contagem_atual = len(linhas_atual)
            if contagem_atual != contagem_inicial:
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Contagem mudou {contagem_inicial} → {contagem_atual}')
            else:
                if debug:
                    log(f'[COMUNICACAO][DEBUG] Contagem estabilizada em {contagem_atual}')

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
                meio_atual = ''
                if hasattr(linha, '_js'):
                    meio_atual = linha._js("""el => {
                        const s = el.querySelector('.pec-item-coluna-meio-expedicao-tabela-destinatarios .mat-select-value-text .mat-select-min-line');
                        return s ? s.innerText.trim() : '';
                    }""") or ''
                else:
                    sel_span = f'(//tbody[contains(@class,"cdk-drop-list")]//tr[contains(@class,"cdk-drag")])[{idx}]//span[contains(@class,"mat-select-min-line")]'
                    sp = espera.elemento(driver, sel_span, teto=1)
                    meio_atual = (getattr(sp, 'text', '') or '').strip()

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

                sel_drop = f'(//tbody[contains(@class,"cdk-drop-list")]//tr[contains(@class,"cdk-drag")])[{idx}]//mat-select[@placeholder="Meios de Expedição"]'
                dropdown = espera.elemento(driver, sel_drop, teto=2)
                if not dropdown:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Dropdown não encontrado')
                    continue

                safe_click_no_scroll(driver, dropdown)

                try:
                    if not esperar_elemento(driver, 'mat-option', timeout=2):
                        raise Exception('Opções do dropdown não carregaram')
                except Exception:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Opções do dropdown não carregaram em 2s')
                    continue

                opcoes = espera.elementos(driver, 'mat-option', teto=2)
                correio_clicado = False
                for opcao in opcoes:
                    txt = getattr(opcao, 'text', '') or ''
                    if 'Correio' in txt:
                        safe_click_no_scroll(driver, opcao)
                        log(f'[COMUNICACAO]  Linha {idx}: Domicílio Eletrônico → Correio')
                        alterados += 1
                        correio_clicado = True
                        try:
                            aguardar_renderizacao_nativa(driver, 'div.cdk-overlay-pane', modo='sumir', timeout=2)
                        except Exception:
                            pass
                        break

                if not correio_clicado:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Opção "Correio" não encontrada nas opções')
                    try:
                        if hasattr(driver, 'page'):
                            driver.page.keyboard.press("Escape")
                        else:
                            safe_click_no_scroll(driver, 'body')
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
    _SEL_SALVAR = 'pje-pec-tabela-destinatarios button[aria-label="Salva os expedientes"]'
    btn_salvar = esperar_elemento(driver, _SEL_SALVAR, timeout=10)
    if not btn_salvar:
        if not click_headless_safe(driver, _SEL_SALVAR, timeout=8):
            log('[COMUNICACAO][ERRO] Botão Salvar não encontrado/habilitado!')
            log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'btn_salvar_nao_encontrado'})
            return False
    else:
        scroll_to_element_safe(driver, btn_salvar)
        if not safe_click_no_scroll(driver, btn_salvar):
            if not click_headless_safe(driver, _SEL_SALVAR, timeout=5):
                log('[COMUNICACAO][ERRO] Falha ao clicar no botão Salvar')
                return False
    log('[COMUNICACAO] Clique no botão Salvar realizado.')

    # 2. Checar snackbar de endereço inválido
    texto_snack = ''
    try:
        el_snack = espera.elemento(driver, 'snack-bar-container', teto=1)
        if el_snack:
            texto_snack = (getattr(el_snack, 'text', '') or '').strip()
    except Exception:
        texto_snack = ''
    if 'Selecione o endere' in texto_snack:
        log(f'[COMUNICACAO][ERRO] Snackbar endereço inválido: "{texto_snack[:80]}" — abortando.')
        log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'endereco_invalido'})
        return False

    # 3. Aguardar botão Assinar
    _SEL_ASSINAR = (
        'pje-pec-tabela-destinatarios button[aria-label="Assinar ato(s)"],'
        'pje-pec-tabela-destinatarios button[aria-label="Enviar para assinatura"]'
    )
    btn_finalizar = None
    if aguardar_renderizacao_nativa(driver, _SEL_ASSINAR, modo='habilitado', timeout=12):
        btn_finalizar = esperar_elemento(driver, _SEL_ASSINAR, timeout=5)
    if not btn_finalizar:
        btn_finalizar = esperar_elemento(driver, _SEL_ASSINAR, timeout=15)

    if not btn_finalizar:
        log('[COMUNICACAO][ERRO] Botão Assinar não habilitou em 27s.')
        log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'assinar_nao_habilitou_27s'})
        return False
    log('[COMUNICACAO] Botão Assinar disponível.')

    if gigs_extra:
        log('[GIGS_EXTRA][WARN] Criação de GIGS via minuta removida. Use criar_gigs na aba /detalhe antes do fluxo.')

    # 4. Assinar se solicitado
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
            btn_finalizar = esperar_elemento(driver, _SEL_ASSINAR, timeout=10)
        if not btn_finalizar:
            log('[COMUNICACAO][ERRO] Botão Assinar não encontrado — não é possível assinar.')
            log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'erro', 'motivo': 'btn_finalizar_none_antes_assinar'})
            raise NavegacaoError('assinar_atos: btn_finalizar é None')

        try:
            scroll_to_element_safe(driver, btn_finalizar)
            clicado = safe_click_no_scroll(driver, btn_finalizar)
            if not clicado:
                click_headless_safe(driver, _SEL_ASSINAR, timeout=5)
            log('[COMUNICACAO] Botão Assinar ato(s) clicado.')
        except Exception as e:
            log(f'[COMUNICACAO][ERRO] Falha ao clicar em Assinar ato(s): {e}')
            log('Comunicação processual finalizada.')
            raise NavegacaoError(f'assinar_atos: {e}')

        # 4a. Detectar dialog de validação por dispositivo móvel
        _TIMEOUT_VALIDACAO_MOVEL = 180
        _dialog_apareceu = aguardar_renderizacao_nativa(driver, 'input.codigo-otp', 'aparecer', 3)
        dialog_movel = espera.elemento(driver, 'input.codigo-otp', teto=1) if _dialog_apareceu else None

        if dialog_movel:
            log('[COMUNICACAO] Dialog "Validacao por dispositivo movel" detectado.')
            try:
                from Fix.assinatura_cookies import cache_tem_cookies
                _tem_cache = cache_tem_cookies()
            except Exception:
                _tem_cache = False

            if _tem_cache:
                log('[COMUNICACAO] Cache de assinatura com cookies — tentando reconfirmar via "Utilizar certificado digital nesta sessao"...')
                _dialog_fechou_auto = False
                try:
                    _radio = esperar_elemento(
                        driver,
                        'mat-dialog-container input[type="radio"][value="2"]',
                        timeout=4
                    )
                    if _radio:
                        scroll_to_element_safe(driver, _radio)
                        safe_click_no_scroll(driver, _radio)
                        log('[COMUNICACAO] Radio "Utilizar certificado digital nesta sessao" clicado (value=2).')
                    else:
                        _radio_fb = esperar_elemento(
                            driver,
                            'input[type="radio"][value="2"]',
                            timeout=3
                        )
                        if _radio_fb:
                            safe_click_no_scroll(driver, _radio_fb)
                            log('[COMUNICACAO] Radio clicado via fallback value=2.')
                        else:
                            log('[COMUNICACAO][WARN] Radio value=2 nao localizado — aguardando confirmacao manual.')

                    _btn_confirmar = esperar_elemento(
                        driver,
                        '//button[@aria-label="Confirmar" or .//span[normalize-space(text())="Confirmar"]]',
                        timeout=4
                    )
                    if _btn_confirmar:
                        scroll_to_element_safe(driver, _btn_confirmar)
                        safe_click_no_scroll(driver, _btn_confirmar)
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

            _lista_vazia = bool(espera.elementos(
                driver,
                "//span[contains(normalize-space(.),'Não há expedientes sendo confeccionados')]",
                teto=2
            ))
            if _lista_vazia:
                log('[COMUNICACAO] Assinatura confirmada — lista de expedientes vazia.')
            else:
                snack_final = esperar_elemento(driver, 'snack-bar-container', timeout=15)
                if snack_final:
                    txt = getattr(snack_final, 'text', '') or ''
                    if 'assinado' in txt.lower() and 'sucesso' in txt.lower():
                        log(f'[COMUNICACAO] Assinatura confirmada: "{txt.strip()}"')
                    else:
                        log(f'[COMUNICACAO][WARN] Snackbar com texto inesperado após dialog fechar: "{txt.strip()}"')
                else:
                    log('[COMUNICACAO][WARN] Snackbar de confirmação não detectado em 15s após dialog fechar.')
        else:
            log('[COMUNICACAO] Sem dialog de validação móvel — aguardando confirmação de assinatura...')
            aguardar_renderizacao_nativa(driver, 'snack-bar-container', modo='aparecer', timeout=15)
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
            snack_sucesso = esperar_elemento(driver, 'snack-bar-container', timeout=3)
            if snack_sucesso:
                txt = getattr(snack_sucesso, 'text', '') or ''
                if 'assinado' in txt.lower() and 'sucesso' in txt.lower():
                    log(f'[COMUNICACAO] Assinatura confirmada: "{txt.strip()}"')
                else:
                    log(f'[COMUNICACAO][WARN] Snackbar de assinatura: "{txt.strip()}"')
            else:
                _lista_vazia_nd = bool(espera.elementos(
                    driver,
                    "//span[contains(normalize-space(.),'Não há expedientes sendo confeccionados')]",
                    teto=2
                ))
                if _lista_vazia_nd:
                    log('[COMUNICACAO] Assinatura confirmada — lista de expedientes vazia.')
                else:
                    log('[COMUNICACAO][WARN] Confirmação de assinatura (snackbar/lista vazia) não detectada em 18s.')

    log_fim('COMUNICACAO_SALVAR_MINUTA', {'status': 'sucesso'})
    log('Comunicação processual finalizada.')
    return True



