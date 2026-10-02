import re
from typing import Optional, Union, Callable, Any
from Play.pjeplay.locators import By, Keys
from Play.pjeplay.errors import NoSuchElementException, StaleElementReferenceException, TimeoutException
from Fix.core import (
    aguardar_renderizacao_nativa,
    safe_click_no_scroll,
    wait_for_clickable,
    esperar_elemento,
    aguardar_e_clicar,
    preencher_campo,
)
from Fix.browser_suporte import limpar_overlays_headless
from Fix.errors import ElementoNaoEncontradoError, NavegacaoError
from Fix.log import logger
from Fix.utils import normalizar_texto as normalizar_string
from Fix import espera


def _executar_js(driver: Any, script: str, *args):
    """Executa JavaScript de forma compativel entre Selenium e Playwright."""
    fn = getattr(driver, "execute_" + "script", None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


def preencher_input_js(driver: Any, seletor: str, valor: Union[str, int], max_tentativas: int = 3, debug: bool = False) -> bool:
    for tentativa in range(1, max_tentativas + 1):
        try:
            if preencher_campo(driver, seletor, str(valor)):
                return True
            if tentativa < max_tentativas:
                aguardar_renderizacao_nativa(driver, seletor, 'aparecer', 1)
        except Exception:
            if tentativa < max_tentativas:
                aguardar_renderizacao_nativa(driver, seletor, 'aparecer', 1)
    return False


def escolher_opcao_select_js(driver, seletor_select, valor_desejado, debug=False):
    try:
        el_presente = wait_for_clickable(driver, seletor_select, timeout=10, by=By.CSS_SELECTOR)
        if not el_presente:
            return False
        safe_click_no_scroll(driver, el_presente)

        espera.ate_aparecer(driver, 'div.cdk-overlay-pane', teto=0.3)
        aguardar_renderizacao_nativa(driver, 'mat-option[role="option"]', 'aparecer', 10)

        opcoes = espera.elementos(driver, 'mat-option[role="option"]')
        valor_norm = normalizar_string(valor_desejado)
        for opcao in opcoes:
            texto_opcao = getattr(opcao, 'text', '') or ''
            if not texto_opcao and hasattr(opcao, 'get_attribute'):
                try:
                    texto_opcao = opcao.get_attribute('innerText') or ''
                except Exception:
                    texto_opcao = ''
            if valor_norm == normalizar_string(texto_opcao) or valor_norm in normalizar_string(texto_opcao):
                safe_click_no_scroll(driver, opcao)
                return True

        limpar_overlays_headless(driver)
        return False
    except Exception as e:
        raise NavegacaoError(f'escolher_opcao_select_js({seletor_select}): {e}')


def clicar_radio_button_js(driver, texto_label, debug=False):
    try:
        ok = _executar_js(
            driver,
            """
            var alvo = String(arguments[0]).normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
            var radios = document.querySelectorAll('mat-radio-button');
            for (var i = 0; i < radios.length; i++) {
                var rotulo = (radios[i].innerText || radios[i].textContent || '')
                    .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
                if (rotulo.indexOf(alvo) === -1) continue;
                var input = radios[i].querySelector('input[type="radio"]');
                if (!input) continue;
                input.click();
                if (input.checked) return true;
            }
            return false;
            """,
            texto_label,
        )
        return bool(ok)
    except Exception as e:
        raise NavegacaoError(f'clicar_radio_button_js({texto_label}): {e}')


def inserir_modelo_comunicacao(driver: Any, modelo_nome: str, log=None) -> bool:
    """Insere modelo na elaboração do ato de comunicação conforme LEGADO.md (L1940-1990 e L19230-19265).
    1. Preenche input#inputFiltro com eventos e ENTER
    2. Clica no .nodo-filtrado
    3. Aguarda botão Inserir e pressiona ESPAÇO (padrão MaisPje / legado)
    4. Aguarda confirmação REAL de texto no editor (> 50 chars) — NÃO depende de snackbar
    5. Aguarda diálogo de visualização sumir
    """
    if log is None:
        def log(_msg): return None

    log(f'[MODELO_PEC] Selecionando modelo: {modelo_nome}')
    # 1. Campo de filtro
    campo_filtro = wait_for_clickable(driver, 'input#inputFiltro', timeout=10, by=By.CSS_SELECTOR)
    if not campo_filtro:
        log('[MODELO_PEC][ERRO] Campo input#inputFiltro não encontrado')
        return False

    # Dispara eventos de input e preenchimento conforme legado L1958-1970
    _executar_js(driver, """
        var el = arguments[0];
        var val = arguments[1];
        el.focus();
        el.value = '';
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('keyup', {bubbles: true}));
        el.value = val;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('keyup', {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 13, which: 13, bubbles: true}));
    """, campo_filtro, modelo_nome)

    if hasattr(driver, 'page') and driver.page:
        try:
            driver.page.keyboard.press('Enter')
        except Exception:
            pass

    espera.assentar(driver, 1.0, motivo='aguardando filtro de modelo ser aplicado na árvore')

    # 2. Nodo filtrado
    nodo = wait_for_clickable(driver, '.nodo-filtrado', timeout=12, by=By.CSS_SELECTOR)
    if not nodo:
        log(f'[MODELO_PEC][ERRO] .nodo-filtrado não encontrado para "{modelo_nome}"')
        return False

    try:
        _executar_js(driver, "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", nodo)
    except Exception:
        safe_click_no_scroll(driver, nodo)
    log('[MODELO_PEC] Clique em .nodo-filtrado realizado')

    # 3. Botão Inserir no preview
    seletor_btn_inserir = (
        'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button,'
        'pje-dialogo-visualizar-modelo button,'
        'button[aria-label="Inserir modelo de documento"]'
    )
    btn_inserir = wait_for_clickable(driver, seletor_btn_inserir, timeout=10, by=By.CSS_SELECTOR)
    if not btn_inserir:
        log('[MODELO_PEC][ERRO] Botão Inserir não encontrado no preview do modelo')
        return False

    espera.assentar(driver, 0.6, motivo='pausa antes de inserir (padrão legado L19257)')

    # 4. Inserir com tecla ESPAÇO (padrão MaisPje / legado L19260) + clique fallback
    _inserido = False
    try:
        if hasattr(btn_inserir, '_handle') and btn_inserir._handle:
            btn_inserir._handle.focus()
            if hasattr(driver, 'page') and driver.page:
                driver.page.keyboard.press('Space')
                _inserido = True
    except Exception:
        pass

    if not _inserido:
        try:
            _executar_js(driver, """
                var btn = arguments[0];
                btn.focus();
                btn.dispatchEvent(new KeyboardEvent('keydown', {code: 'Space', keyCode: 32, which: 32, bubbles: true}));
                btn.dispatchEvent(new KeyboardEvent('keyup', {code: 'Space', keyCode: 32, which: 32, bubbles: true}));
                btn.click();
            """, btn_inserir)
        except Exception:
            safe_click_no_scroll(driver, btn_inserir)

    log('[MODELO_PEC] Comando de inserção enviado ao botão')

    # 5. VERIFICAÇÃO REAL DE CONTEÚDO NO EDITOR (conforme legado L19520-19525)
    # Não confia em snackbar: verifica diretamente innerText/textContent do editor!
    _JS_TEXTO_EDITOR = """() => {
        var sels = [
            'pje-pec-dialogo-ato div[contenteditable="true"]',
            'div.area-conteudo[contenteditable="true"]',
            '.ck-editor__editable[contenteditable="true"]',
            '.ck-content[contenteditable="true"]',
            'div[contenteditable="true"]'
        ];
        for (var s of sels) {
            var el = document.querySelector(s);
            if (el) {
                var clone = el.cloneNode(true);
                clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
                var txt = (clone.innerText || clone.textContent || '').trim();
                if (txt.length > 50 || clone.querySelector('p.corpo') || clone.querySelector('figure') || clone.querySelector('table')) {
                    return true;
                }
            }
        }
        return false;
    }"""

    tem_conteudo = espera.ate_js(driver, f"({_JS_TEXTO_EDITOR})()", teto=12)
    if not tem_conteudo:
        log('[MODELO_PEC][WARN] Editor ainda sem texto — tentando acionar clique direto de fallback...')
        try:
            if hasattr(btn_inserir, '_handle') and btn_inserir._handle:
                btn_inserir._handle.click()
        except Exception:
            safe_click_no_scroll(driver, btn_inserir)
        tem_conteudo = espera.ate_js(driver, f"({_JS_TEXTO_EDITOR})()", teto=8)

    if not tem_conteudo:
        log(f'[MODELO_PEC][ERRO] Editor permaneceu vazio após inserção do modelo "{modelo_nome}"')
        return False

    log(f'[MODELO_PEC] ✓ Conteúdo do modelo "{modelo_nome}" CONFIRMADO dentro do editor.')

    # 6. Aguardar diálogo de modelo sumir
    aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', modo='sumir', timeout=10)
    espera.ate_js(driver, "document.querySelector('pje-dialogo-visualizar-modelo') === null", teto=5)
    espera.pausa(driver, 1.0, motivo='estabilizacao apos inserir modelo (fechar modal)')
    return True


# Diálogo "Elaboração do ato de comunicação" (pje-pec-dialogo-ato).
# Enquanto estiver visível, a dialog está aberta — e os elementos de
# destinatários (ícone verde de check, tabela) existem POR TRÁS dela.
_JS_ELAB_VISIVEL = """(function(){
    var dlg = document.querySelector('pje-pec-dialogo-ato');
    if (dlg) {
        var c = dlg.closest('mat-dialog-container, .cdk-overlay-pane') || dlg;
        if (c.offsetWidth > 0 || c.offsetHeight > 0 || c.getClientRects().length > 0) return true;
    }
    var sp = document.querySelector('mat-progress-spinner, mat-spinner, .loading-spinner, pje-dialogo-status-progresso');
    if (sp && (sp.offsetWidth > 0 || sp.offsetHeight > 0 || sp.getClientRects().length > 0)) return true;
    return false;
})()"""


def aguardar_fechamento_dialogo_elaboracao(driver: Any, log=None, timeout: int = 20) -> bool:
    """Hard-gate de finalização do ato de comunicação.

    Só retorna True quando a dialog "Elaboração do ato de comunicação" NÃO está
    mais visível. Motivo: o ícone verde de check e a tabela de destinatários
    existem por trás da dialog — checá-los como sinal de "pronto" fazia o fluxo
    seguir com a dialog ainda aberta e destinatários atropelando a finalização.
    """
    if not espera.ate_js(driver, f"!({_JS_ELAB_VISIVEL})", teto=timeout):
        if log:
            log('[MINUTA][ERRO] Dialog "Elaboração do ato de comunicação" ainda aberta '
                '— finalização não confirmada')
        return False
    return True


def aguardar_ato_confeccionado(driver: Any, timeout_fechar: int = 20, timeout_icone: int = 10, log=None) -> bool:
    if log is None:
        def log(_msg): return None

    # PROVA de finalização = dialog "Elaboração do ato de comunicação" FECHADA.
    # Ícone verde de check e a tabela de destinatários ficam POR TRÁS da dialog:
    # checá-los como sinal de pronto fazia o fluxo seguir com a dialog aberta.
    if not aguardar_fechamento_dialogo_elaboracao(driver, log=log, timeout=timeout_fechar):
        return False

    # Snackbar "Ato elaborado com sucesso." — apenas fecha para não bloquear
    # os cliques de destinatários (não é critério de sucesso).
    try:
        if espera.elementos(driver, 'simple-snack-bar', teto=1):
            _btn_snack = espera.elemento(driver, 'simple-snack-bar button', teto=2)
            if _btn_snack:
                safe_click_no_scroll(driver, _btn_snack)
                log('[MINUTA] Snackbar de ato elaborado fechado.')
    except Exception as _e:
        log(f'[MINUTA][WARN] Não foi possível fechar o snackbar: {_e}')

    return True


def aguardar_estabilizacao_para_destinatarios(driver: Any, log=None, timeout: int = 20) -> bool:
    if log is None:
        def log(_msg):
            return None

    # HARD-GATE 1: dialog de modelo DEVE ter sumido do DOM
    dlg_modelo_sumiu = espera.ate_js(
        driver,
        "document.querySelector('pje-dialogo-visualizar-modelo') === null",
        teto=timeout
    )
    if not dlg_modelo_sumiu:
        log('[BARREIRA][ERRO] Dialog de modelo ainda presente — seleção de destinatários abortada')
        return False

    # HARD-GATE 2: dialog de elaboração do ato DEVE ter sumido do DOM
    dlg_ato_sumiu = espera.ate_js(
        driver,
        "document.querySelector('pje-pec-dialogo-ato') === null",
        teto=timeout
    )
    if not dlg_ato_sumiu:
        log('[BARREIRA][ERRO] Dialog de elaboração do ato ainda aberta — seleção de destinatários abortada')
        return False

    # HARD-GATE 3: tabela de destinatários disponível na tela principal
    if not aguardar_renderizacao_nativa(
        driver,
        'pje-pec-tabela-destinatarios, tbody.cdk-drop-list',
        'aparecer',
        10,
    ):
        log('[BARREIRA][WARN] Tabela de destinatários não detectada em 10s')
        return False
    return True


def _aguardar_overlay_livre(driver: Any, timeout: int = 15) -> bool:
    """Aguarda overlay de loading do PJe sumir antes de clicar."""
    seletores_loading = (
        'mat-progress-spinner, mat-spinner, mat-progress-bar, '
        '.loading-spinner, pje-dialogo-status-progresso'
    )
    try:
        return bool(aguardar_renderizacao_nativa(driver, seletores_loading, modo='sumir', timeout=timeout))
    except Exception:
        return True


def finalizar_minuta(driver: Any, log=None) -> bool:
    """Finaliza a minuta clicando em 'Finalizar minuta'.
    3. Aguarda snackbar 'Ato elaborado com sucesso.' e fecha
    4. Confirma que a dialog de elaboração fechou
    """
    if log is None:
        def log(_msg):
            return None

    try:
        # 1. Finalizar minuta
        seletor_finalizar = (
            'pje-pec-dialogo-ato button[aria-label="Finalizar minuta"],'
            'button[aria-label="Finalizar minuta"]'
        )
        btn = None
        for _tentativa in range(3):
            btn = wait_for_clickable(driver, seletor_finalizar, timeout=10, by=By.CSS_SELECTOR)
            if btn:
                break
            log(f'[MINUTA][WARN] "Finalizar minuta" não clicável — tentativa {_tentativa + 1}/3')
        if not btn:
            log('[MINUTA][ERRO] Botão "Finalizar minuta" não encontrado — ato NÃO finalizado')
            return False

        # Dispara eventos de clique no botão Finalizar minuta
        _clicado = False
        try:
            if hasattr(btn, '_handle') and btn._handle:
                btn._handle.evaluate("""el => {
                    el.focus();
                    el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
                    el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
                    el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                }""")
                _clicado = True
        except Exception:
            pass

        espera.pausa(driver, 1.0, motivo='estabilizacao antes de finalizar a minuta')
        if not _clicado:
            try:
                if hasattr(btn, 'click'):
                    btn.click()
                else:
                    safe_click_no_scroll(driver, btn)
            except Exception:
                safe_click_no_scroll(driver, btn)
        log('[MINUTA] "Finalizar minuta" clicado — aguardando fechar a dialog de elaboração.')
        
        # O backend processa o modelo e uma snackbar e spinner vao aparecer
        espera.pausa(driver, 1.0, motivo='estabilizacao apos clicar em finalizar minuta')

        # 3. Aguardar snackbar "Ato elaborado com sucesso." (padrão gigs-plugin L10935)
        snack_ok = espera.ate_texto(driver, 'simple-snack-bar', 'Ato elaborado com sucesso', teto=10)
        if snack_ok:
            log('[MINUTA] Snackbar "Ato elaborado com sucesso" confirmada.')
            try:
                btn_snack = espera.elemento(driver, 'simple-snack-bar button', teto=2)
                if btn_snack:
                    safe_click_no_scroll(driver, btn_snack)
            except Exception:
                pass

        # 4. Aguardar diálogo de elaboração sumir
        aguardar_renderizacao_nativa(driver, 'pje-pec-dialogo-ato', modo='sumir', timeout=15)
        log('[MINUTA] Dialog de elaboração do ato fechada com sucesso.')
        return True

    except Exception as e:
        log(f'[MINUTA][ERRO] Falha ao finalizar minuta: {e}')
        raise


def executar_preenchimento_minuta(
    driver: Any,
    tipo_expediente: str,
    prazo: Union[str, int],
    nome_comunicacao: str,
    sigilo: bool,
    modelo_nome: str,
    subtipo: Optional[str] = None,
    descricao: Optional[str] = None,
    tipo_prazo: str = 'dias uteis',
    inserir_conteudo: Optional[Callable] = None,
    finalizar: bool = True,
    debug: bool = False,
    log: Optional[Callable] = None,
) -> bool:
    if log is None:
        def log(_msg):
            return None

    _passo = 'inicio'
    try:
        from Fix.utils import inserir_link_ato_validacao

        _passo = 'tipo_expediente'
        if not escolher_opcao_select_js(driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de expediente')
            raise Exception('Falha ao selecionar tipo de expediente')

        aguardar_renderizacao_nativa(driver, 'mat-radio-button', 'aparecer', 5)

        if prazo == "0" or prazo == 0:
            tipo_prazo = "sem prazo"

        _passo = 'tipo_prazo'
        if not clicar_radio_button_js(driver, tipo_prazo, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de prazo')
            raise Exception(f'Tipo de prazo "{tipo_prazo}" não encontrado')

        if not espera.ate_js(driver, "__pjeEls('mat-radio-button input[type=\"radio\"]').some(el => el.checked)", teto=5):
            raise Exception(f'tipo de prazo "{tipo_prazo}" nao foi marcado')

        _passo = 'prazo'
        if prazo and tipo_prazo != "sem prazo":
            tipo_prazo_norm = normalizar_string(tipo_prazo)
            acao_map = {
                'dias uteis': 'campo_prazo_dias_uteis',
                'data certa': 'campo_prazo_data_certa',
                'dias corridos': 'campo_prazo_dias_corridos',
            }
            acao_prazo = acao_map.get(tipo_prazo_norm, 'campo_prazo_destinatario')
            from Fix.seletores_catalogo import buscar_elemento_por_acao
            el_prazo = buscar_elemento_por_acao(driver, acao_prazo, contexto="pec", timeout=10)
            prazo_preenchido = False
            if el_prazo:
                prazo_preenchido = preencher_campo(driver, el_prazo, str(prazo), limpar=True, trigger_events=True)
            if not prazo_preenchido:
                try:
                    prazo_preenchido = preencher_campo(
                        driver, 'mat-form-field input[type="number"]', str(prazo), limpar=True
                    )
                    if not prazo_preenchido:
                        raise Exception('Elemento input_prazo não encontrado')
                except Exception as e:
                    log(f'[FALLBACK][ERRO] Falha no fallback: {e}')
                    prazo_preenchido = False

        _passo = 'confeccionar'
        if not aguardar_e_clicar(driver, 'button[aria-label="Confeccionar ato agrupado"]', timeout=10, by=By.CSS_SELECTOR, usar_js=False):
            raise Exception('Botão Confeccionar ato agrupado não disponível')

        _passo = 'subtipo'
        if subtipo:
            tentativas_subtipo = 0
            sucesso_subtipo = False

            while tentativas_subtipo < 3 and not sucesso_subtipo:
                try:
                    tentativas_subtipo += 1

                    input_subtipo = esperar_elemento(driver, 'input[data-placeholder="Tipo de Documento"]', timeout=10, by=By.CSS_SELECTOR)
                    if not input_subtipo:
                        raise Exception('Campo subtipo não encontrado')

                    safe_click_no_scroll(driver, input_subtipo)
                    aguardar_renderizacao_nativa(driver, 'mat-option', 'aparecer', 3)

                    opcoes = espera.elementos(driver, 'mat-option')
                    for opcao in opcoes:
                        txt = getattr(opcao, 'text', '') or ''
                        if subtipo.lower() in txt.lower():
                            safe_click_no_scroll(driver, opcao)
                            sucesso_subtipo = True
                            break

                    if not sucesso_subtipo and tentativas_subtipo < 3:
                        try:
                            btn_fechar = espera.elemento(driver, 'pje-pec-dialogo-ato a[mattooltip="Fechar"]')
                            if btn_fechar:
                                safe_click_no_scroll(driver, btn_fechar)
                            aguardar_renderizacao_nativa(driver, 'button[aria-label="Confeccionar ato agrupado"]', 'aparecer', 5)
                            btn_confeccionar = espera.elemento(driver, 'button[aria-label="Confeccionar ato agrupado"]')
                            if btn_confeccionar:
                                safe_click_no_scroll(driver, btn_confeccionar)
                        except Exception:
                            pass

                except Exception as e:
                    log(f'[SUBTIPO][WARN] Erro na tentativa {tentativas_subtipo}: {e}')
                    if tentativas_subtipo >= 3:
                        log('[SUBTIPO][ERRO] Falha ao selecionar subtipo após 3 tentativas')

        _passo = 'descricao'
        desc_to_use = descricao if descricao else nome_comunicacao
        if not preencher_input_js(driver, 'input[aria-label="Descrição"]', desc_to_use, debug=debug):
            log('[ERRO] Falha ao preencher descrição')
            raise Exception('Falha ao preencher descrição')

        _passo = 'sigilo'
        if sigilo:
            # O input é um mat-slide-toggle (role="switch", cdk-visually-hidden):
            # o thumb intercepta o clique do driver e o mat_checkbox estoura
            # timeout de 5s. Marcar via JS PRIMEIRO (caminho que funciona);
            # helpers de driver ficam só como fallback.
            try:
                _sigilo_ok = _executar_js(
                    driver,
                    """
                    var el = document.querySelector('input[name="sigiloso"]');
                    if (el && !el.checked) { el.click(); }
                    return !!(el && el.checked);
                    """,
                )
            except Exception as _e:
                _sigilo_ok = False
                log(f'[SIGILO][WARN] Fallback JS do sigilo falhou: {_e}')
            if not _sigilo_ok:
                try:
                    marcado = mat_checkbox(driver, 'input[name="sigiloso"], mat-checkbox[formcontrolname="sigiloso"]', marcar=True, timeout=5)
                    if not marcado:
                        cb = espera.elemento(driver, 'input[name="sigiloso"]', teto=2, visivel=False)
                        if cb:
                            safe_click_no_scroll(driver, cb)
                except Exception as e:
                    log(f'[WARN] Falha ao marcar sigilo: {e}')
                if not _sigilo_ok:
                    log('[SIGILO][ERRO] Toggle de sigilo permaneceu desmarcado após fallbacks')

        _passo = 'modelo'
        if modelo_nome:
            # FLUXO DEDICADO para dialog de comunicação PEC (pje-pec-dialogo-ato).
            # NÃO delega para judicial_modelos.inserir_modelo_no_editor porque a
            # hierarquia de dialogs é diferente: o editor-alvo fica dentro de
            # pje-pec-dialogo-ato e o _resolver_editor_alvo não o enxerga corretamente.
            # Fonte: LEGADO.md L1940-1990, L19230-19265 e gigs-plugin.js aaAnexar L10106.
            if not inserir_modelo_comunicacao(driver, modelo_nome, log=log):
                raise Exception(f'Modelo "{modelo_nome}" não confirmado no editor-alvo')

            try:
                if inserir_conteudo:
                    inserir_fn = inserir_conteudo
                    if isinstance(inserir_conteudo, str):
                        try:
                            if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                                inserir_fn = inserir_link_ato_validacao
                            elif inserir_conteudo.lower() in ('conteudo_formatado', 'transcricao'):
                                from Fix.utils import inserir_conteudo_formatado
                                inserir_fn = inserir_conteudo_formatado
                        except Exception as _e:
                            log(f'[INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}')

                    try:
                        from PEC.anexos import extrair_numero_processo_da_url
                        numero_processo_atual = extrair_numero_processo_da_url(driver)
                    except Exception:
                        numero_processo_atual = None

                    ok = False
                    try:
                        ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, debug=debug)
                    except TypeError:
                        try:
                            ok = inserir_fn(driver, numero_processo_atual)
                        except Exception:
                            ok = inserir_fn(driver)
            except Exception as e:
                log(f'[INSERIR][WARN] Erro ao executar inserção: {e}')

        _passo = 'finalizar'
        if not finalizar_minuta(driver, log=log):
            raise Exception('finalizar_minuta falhou — ato não finalizado (documento vazio)')
        return True
    except Exception as e:
        raise Exception(f'[passo={_passo}] {e}') from e
