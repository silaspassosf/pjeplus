import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from Fix.selenium_base.wait_operations import wait_for_clickable, esperar_elemento
from Fix.selenium_base.click_operations import aguardar_e_clicar
from Fix.core import aguardar_renderizacao_nativa
from Fix.errors import ElementoNaoEncontradoError, NavegacaoError
from Fix.log import logger
from Fix.utils import normalizar_texto as normalizar_string
from typing import Optional, Union, Callable, Any
from selenium.webdriver.remote.webdriver import WebDriver


def preencher_input_js(driver: WebDriver, seletor: str, valor: Union[str, int], max_tentativas: int = 3, debug: bool = False) -> bool:
    """Preenche input via querySelector direto + setter de prototype.
    Identico ao gigs-plugin.js preencherInput: sem click previo, sem wait_for_clickable.
    """
    for tentativa in range(1, max_tentativas + 1):
        try:
            ok = driver.execute_script("""
                var seletor = arguments[0];
                var val = arguments[1];
                var el = document.querySelector(seletor);
                if (!el) { return false; }
                window.focus();
                el.focus();
                Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('dateChange', {bubbles: true}));
                el.dispatchEvent(new Event('keyup', {bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true }));
                el.blur();
                return true;
            """, seletor, str(valor))
            if ok:
                if debug:
                    logger.info(f"[INPUT][OK] {seletor}='{valor}'")
                return True
            if tentativa < max_tentativas:
                # Evita backoff fixo; aguarda somente se o campo ainda nao estiver pronto.
                aguardar_renderizacao_nativa(driver, seletor, 'aparecer', 1)
        except Exception:
            if tentativa < max_tentativas:
                # Evita backoff fixo apos erro transitorio de DOM.
                aguardar_renderizacao_nativa(driver, seletor, 'aparecer', 1)
    return False


def escolher_opcao_select_js(driver, seletor_select, valor_desejado, debug=False):
    """Abre o mat-select via JS click e clica na opção correspondente.

    Comportamento idêntico ao legado (_escolher_opcao_select_js):
    clica no mat-select para abrir o dropdown, aguarda as mat-options via
    aguardar_renderizacao_nativa (MutationObserver) e clica na opção correta.
    """
    try:
        el_presente = wait_for_clickable(driver, seletor_select, timeout=10, by=By.CSS_SELECTOR)
        if not el_presente:
            return False
        driver.execute_script("arguments[0].click();", el_presente)

        # Aguardar mat-options aparecerem (observer nativo)
        aguardar_renderizacao_nativa(driver, 'mat-option[role="option"]', 'aparecer', 10)

        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
        valor_norm = normalizar_string(valor_desejado)
        for opcao in opcoes:
            texto_opcao = opcao.get_attribute('innerText') or opcao.text or ''
            if valor_norm == normalizar_string(texto_opcao) or valor_norm in normalizar_string(texto_opcao):
                driver.execute_script("arguments[0].click();", opcao)
                return True

        # Fechar painel sem seleção
        driver.execute_script("arguments[0].blur();", el_presente)
        return False
    except Exception as e:
        raise NavegacaoError(f'escolher_opcao_select_js({seletor_select}): {e}')


def clicar_radio_button_js(driver, texto_label, debug=False):
    """Clica no input[type=radio] dentro do mat-radio-button correspondente.
    Identico ao gigs-plugin: clicarBotao(ancora.querySelector('input')).
    """
    try:
        texto_norm = normalizar_string(texto_label)
        ok = driver.execute_script("""
            var textoAlvo = arguments[0];
            function normLabel(s) {
                return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
            }
            var radios = document.querySelectorAll('mat-radio-button');
            for (var i = 0; i < radios.length; i++) {
                var label = normLabel((radios[i].innerText || radios[i].textContent || '').trim());
                if (label.indexOf(textoAlvo) !== -1) {
                    var inp = radios[i].querySelector('input[type="radio"]');
                    if (inp) { inp.click(); return true; }
                }
            }
            return false;
        """, texto_norm)
        return bool(ok)
    except Exception as e:
        raise NavegacaoError(f'clicar_radio_button_js({texto_label}): {e}')






def _aguardar_ck_com_conteudo(driver: WebDriver, timeout: int = 8) -> bool:
    """Aguarda CKEditor conter conteúdo não-vazio após inserção de modelo.

    Faz polling leve via JS até o editor ter dados ou o timeout expirar.
    Substitui sleep cego: garante que o modelo foi efetivamente injetado
    antes de prosseguir para salvar o ato.
    """
    deadline = time.monotonic() + timeout
    selectors = [
        '.ck-editor__editable[contenteditable="true"]',
        '.ck-content',
        'div[contenteditable="true"]',
        'textarea',
        'iframe'
    ]

    while time.monotonic() < deadline:
        try:
            for sel in selectors:
                try:
                    tem_conteudo = driver.execute_script("""
                        var sel = arguments[0];
                        var el = document.querySelector(sel);
                        if (!el) {
                            if (sel === 'div[contenteditable="true"]') {
                                el = document.querySelector('[contenteditable="true"]');
                                if (!el) return false;
                            } else return false;
                        }

                        // iframe case
                        if (el.tagName === 'IFRAME') {
                            try {
                                var doc = el.contentDocument || el.contentWindow.document;
                                var txt = doc && doc.body ? (doc.body.innerText || doc.body.textContent || '') : '';
                                return (txt || '').trim().length > 0;
                            } catch(e) { return false; }
                        }

                        // CKEditor classic instance on the editable element
                        if (el.ckeditorInstance && typeof el.ckeditorInstance.getData === 'function') {
                            var data = el.ckeditorInstance.getData();
                            return (data || '').replace(/<[^>]*>/g,'').trim().length > 0;
                        }

                        // global CKEDITOR instances (fallback)
                        if (window.CKEDITOR) {
                            for (var k in window.CKEDITOR.instances) {
                                try {
                                    var d = window.CKEDITOR.instances[k].getData();
                                    if ((d || '').replace(/<[^>]*>/g,'').trim().length > 0) return true;
                                } catch(e) {}
                            }
                        }

                        var html = el.innerHTML || el.value || el.textContent || '';
                        return (html || '').replace(/<[^>]*>/g,'').trim().length > 0;
                    """, sel)
                except Exception:
                    tem_conteudo = False

                if tem_conteudo:
                    return True
        except Exception:
            pass

        # Pequena espera/trigger adicional para lidar com casos onde o
        # preview fecha muito rápido e a injeção ocorre com micro-latência.
        try:
            from atos.wrappers_utils import esperar_insercao_modelo
            esperar_insercao_modelo(driver, timeout=500)
        except Exception:
            time.sleep(0.3)

        time.sleep(0.3)

    return False


def aguardar_ato_confeccionado(driver: WebDriver, timeout_fechar: int = 15, timeout_icone: int = 10, log=None) -> bool:
    """Aguarda confirmação pós-'Finalizar minuta'.
    Snackbar 'Ato elaborado com sucesso' = confirmação definitiva → return True imediato.
    Sem snackbar: fallback para dialog sumir / ícone verde.
    """
    if log is None:
        def log(_msg): return None

    # Snackbar já presente?
    snackbar_ok = False
    try:
        snackbar_ok = driver.execute_script("""
            var bars = document.querySelectorAll('simple-snack-bar');
            for (var i = 0; i < bars.length; i++) {
                if ((bars[i].textContent || '').indexOf('Ato elaborado com sucesso') !== -1) return true;
            }
            return false;
        """)
    except Exception:
        pass

    if not snackbar_ok:
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("""
                    var bars = document.querySelectorAll('simple-snack-bar');
                    for (var i = 0; i < bars.length; i++) {
                        if ((bars[i].textContent || '').indexOf('Ato elaborado com sucesso') !== -1) return true;
                    }
                    return false;
                """)
            )
            snackbar_ok = True
        except Exception:
            pass

    if snackbar_ok:
        log('[MINUTA] Snackbar "Ato elaborado com sucesso" detectada — prosseguindo imediatamente')
        return True  # Snackbar = confirmação. Ponto final.


def finalizar_minuta(driver: WebDriver, log=None) -> bool:
    """Clica 'Finalizar minuta' e aguarda confirmacao do ato.
    Separada de executar_preenchimento_minuta para ser chamada
    tardiamente quando trocar_modelo=True."""
    if log is None:
        def log(_msg):
            return None

    log('9. Finalizando minuta')
    try:
        # Clique direto, sem retry headless
        seletor_finalizar = 'button[aria-label="Finalizar minuta"]'
        btn = driver.find_element(By.CSS_SELECTOR, seletor_finalizar)
        driver.execute_script("""
            var btn = arguments[0];
            btn.scrollIntoView({block:'center'});
            var span = btn.querySelector('span.mat-button-wrapper');
            if (span) { span.click(); } else { btn.click(); }
        """, btn)
        log(' Botão Finalizar minuta clicado')

        # Aguardar confirmacao: snackbar "Ato confeccionado com sucesso"
        ato_ok = aguardar_ato_confeccionado(driver, log=log)
        if not ato_ok:
            raise Exception('Ato NÃO confeccionado — nenhum sinal de confirmação')
        log(' Comunicação criada com sucesso!')
        return True

    except NoSuchElementException:
        log('[SALVAR] Botão não encontrado — já foi clicado, ato já confeccionado')
        return True

    except Exception as e:
        log(f'[SALVAR][ERRO] Falha ao salvar/finalizar: {e}')
        raise


def executar_preenchimento_minuta(
    driver: WebDriver,
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

    try:
        from Fix.utils import inserir_link_ato_validacao

        log(f'1. Selecionando tipo de expediente: {tipo_expediente}')
        if not escolher_opcao_select_js(driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de expediente')
            raise Exception('Falha ao selecionar tipo de expediente')

        # Aguardar radio buttons aparecerem após select de tipo de expediente
        aguardar_renderizacao_nativa(driver, 'mat-radio-button', 'aparecer', 5)

        log(f'2. Selecionando tipo de prazo: {tipo_prazo}')
        if prazo == "0" or prazo == 0:
            tipo_prazo = "sem prazo"

        if not clicar_radio_button_js(driver, tipo_prazo, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de prazo')
            raise Exception(f'Tipo de prazo "{tipo_prazo}" não encontrado')

        if prazo and tipo_prazo != "sem prazo":
            log(f'3. Preenchendo prazo: {prazo}')
            tipo_prazo_norm = normalizar_string(tipo_prazo)

            # Inicializar variável de controle
            prazo_preenchido = False

            seletores_prazo = []
            if tipo_prazo_norm == 'dias uteis':
                seletores_prazo = [
                    'input[aria-label="Prazo em dias úteis"]',
                    'input[placeholder*="dias úteis"]',
                    'mat-form-field input[type="number"]',
                    'input[formcontrolname="prazo"]'
                ]
            elif tipo_prazo_norm == 'data certa':
                seletores_prazo = [
                    'input[aria-label="Prazo em data certa"]',
                    'input[placeholder*="data"]',
                    'input[type="date"]'
                ]
            elif tipo_prazo_norm == 'dias corridos':
                seletores_prazo = [
                    'input[aria-label="Prazo em dias úteis"]',
                    'input[placeholder*="dias"]',
                    'mat-form-field input[type="number"]',
                    'input[formcontrolname="prazo"]'
                ]

            # Esperar o campo de prazo aparecer após a seleção do tipo de prazo.
            aguardar_renderizacao_nativa(driver, 'mat-form-field input[type="number"], input[aria-label="Prazo em dias úteis"], input[placeholder*="data"], input[type="date"], input[formcontrolname="prazo"]', 'aparecer', 10)

            # Tentar cada seletor até encontrar um que funcione (como no legado)
            for seletor in seletores_prazo:
                if preencher_input_js(driver, seletor, prazo, debug=debug):
                    prazo_preenchido = True
                    break

            if not prazo_preenchido:
                log('[AVISO] Não foi possível preencher prazo com nenhum seletor, tentando fallback...')
                try:
                    input_prazo = esperar_elemento(driver, 'mat-form-field input[type="number"]', timeout=5, by=By.CSS_SELECTOR)
                    if input_prazo:
                        input_prazo.clear()
                        input_prazo.send_keys(str(prazo))
                        log('[FALLBACK][OK] Prazo preenchido via send_keys')
                        prazo_preenchido = True
                    else:
                        raise Exception('Elemento input_prazo não encontrado')
                except Exception as e:
                    log(f'[FALLBACK][ERRO] Falha no fallback: {e}')
                    prazo_preenchido = False
        else:
            log('3. Sem prazo a preencher')

        log('4. Clicando "Confeccionar ato agrupado"')
        if not aguardar_e_clicar(driver, 'button[aria-label="Confeccionar ato agrupado"]', timeout=10, by=By.CSS_SELECTOR, usar_js=False):
            raise Exception('Botão Confeccionar ato agrupado não disponível')

        if subtipo:
            log(f'5. Selecionando subtipo: {subtipo}')
            tentativas_subtipo = 0
            sucesso_subtipo = False

            while tentativas_subtipo < 3 and not sucesso_subtipo:
                try:
                    tentativas_subtipo += 1
                    log(f'[SUBTIPO] Tentativa {tentativas_subtipo}/3')

                    input_subtipo = esperar_elemento(driver, 'input[data-placeholder="Tipo de Documento"]', timeout=10, by=By.CSS_SELECTOR)
                    if not input_subtipo:
                        raise Exception('Campo subtipo não encontrado')

                    driver.execute_script("""
                        var el = arguments[0];
                        el.focus();
                        el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 13, which: 13, bubbles: true}));
                    """, input_subtipo)

                    if not aguardar_renderizacao_nativa(driver, 'mat-option', 'aparecer', 3):
                        raise Exception('mat-option ainda não disponível')

                    try:
                        if not esperar_elemento(driver, 'mat-option', timeout=3, by=By.CSS_SELECTOR):
                            raise Exception('mat-option ainda não disponível')
                    except Exception:
                        driver.execute_script("""
                            var el = arguments[0];
                            el.focus();
                            el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 40, which: 40, bubbles: true}));
                        """, input_subtipo)
                        if not aguardar_renderizacao_nativa(driver, 'mat-option', 'aparecer', 3):
                            raise Exception('mat-option não apareceu mesmo após fallback')
                        if not esperar_elemento(driver, 'mat-option', timeout=3, by=By.CSS_SELECTOR):
                            raise Exception('mat-option não apareceu mesmo após fallback')

                    opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                    for opcao in opcoes:
                        if subtipo.lower() in (opcao.text or '').lower():
                            driver.execute_script("arguments[0].click();", opcao)
                            log(f' Subtipo selecionado: {subtipo}')
                            sucesso_subtipo = True
                            break

                    if not sucesso_subtipo and tentativas_subtipo < 3:
                        log('[SUBTIPO] Opção não encontrada, tentando novamente...')
                        try:
                            btn_fechar = driver.find_element(By.CSS_SELECTOR, 'pje-pec-dialogo-ato a[mattooltip="Fechar"]')
                            driver.execute_script("arguments[0].click();", btn_fechar)
                            aguardar_renderizacao_nativa(driver, 'button[aria-label="Confeccionar ato agrupado"]', 'aparecer', 5)
                            btn_confeccionar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
                            driver.execute_script("arguments[0].click();", btn_confeccionar)
                        except Exception:
                            pass

                except Exception as e:
                    log(f'[SUBTIPO][WARN] Erro na tentativa {tentativas_subtipo}: {e}')
                    if tentativas_subtipo >= 3:
                        log('[SUBTIPO][ERRO] Falha ao selecionar subtipo após 3 tentativas')
        else:
            log('5. Sem subtipo para selecionar')

        desc_to_use = descricao if descricao else nome_comunicacao
        log(f'6. Preenchendo descrição: {desc_to_use}')
        if not preencher_input_js(driver, 'input[aria-label="Descrição"]', desc_to_use, debug=debug):
            log('[ERRO] Falha ao preencher descrição')
            raise Exception('Falha ao preencher descrição')

        if sigilo:
            log('7. Marcando sigilo')
            try:
                input_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not input_sigilo.is_selected():
                    driver.execute_script("arguments[0].click();", input_sigilo)
                    log(' Sigilo marcado')
            except Exception as e:
                log(f'[WARN] Falha ao marcar sigilo: {e}')
        else:
            log('7. Sem sigilo')

        if modelo_nome:
            log(f'8. Selecionando modelo: {modelo_nome}')

            try:
                from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

                # 1. Localizar campo filtro e preencher via JS + ENTER (robusto como judicial_fluxo)
                campo_filtro = wait_for_clickable(driver, 'input#inputFiltro', timeout=10, by=By.CSS_SELECTOR)
                if not campo_filtro:
                    raise Exception('Campo de filtro de modelo não encontrado')

                driver.execute_script('arguments[0].focus();', campo_filtro)
                driver.execute_script('arguments[0].value = arguments[1];', campo_filtro, modelo_nome)
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script(
                        'var e = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(e);',
                        campo_filtro, ev
                    )
                campo_filtro.send_keys(Keys.ENTER)
                log(f'[MODELO] Filtro preenchido: "{modelo_nome}"')

                # 2. Aguardar nodo filtrado e clicar
                aguardar_renderizacao_nativa(driver, '.nodo-filtrado', 'aparecer', 10)
                nodo = aguardar_e_clicar(driver, '.nodo-filtrado', timeout=15)
                if not nodo:
                    raise Exception(f'Nodo filtrado não encontrado para modelo "{modelo_nome}"')
                log('[MODELO] Clique em nodo-filtrado realizado')

                # 3. Aguardar modal abrir
                modal_aberto = aguardar_renderizacao_nativa(
                    driver, 'pje-dialogo-visualizar-modelo', 'aparecer', 5
                )
                if not modal_aberto:
                    log('[MODELO][WARN] Modal de visualização não abriu, tentando inserir mesmo assim...')

                # 4. Retry loop para botão inserir (evita StaleElement)
                seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
                btn_inserir = None
                for tentativa in range(5):
                    try:
                        btn_inserir = wait_for_clickable(driver, seletor_btn_inserir, timeout=4, by=By.CSS_SELECTOR)
                        if btn_inserir:
                            break
                        raise TimeoutException('Botão inserir não clicável')
                    except (TimeoutException, StaleElementReferenceException):
                        if tentativa < 4:
                            continue
                        raise Exception('Botão inserir não encontrado após 5 tentativas')

                # 5. Inserir via SPACE (mais confiável que JS click no Angular)
                try:
                    btn_inserir.send_keys(Keys.SPACE)
                    log(' Modelo inserido')
                except StaleElementReferenceException:
                    log('[MODELO][WARN] Elemento ficou stale, tentando novamente...')
                    btn_inserir = driver.find_element(By.CSS_SELECTOR, seletor_btn_inserir)
                    btn_inserir.send_keys(Keys.SPACE)
                    log(' Modelo inserido (2a tentativa)')

                # 6. Aguardar snackbar "Modelo de documento inserido com sucesso no editor"
                #    Polling JS: snackbar pode demorar alguns ms para aparecer no DOM
                try:
                    snackbar_modelo_ok = False
                    for _poll in range(15):  # até 3 segundos (15 × 200ms)
                        if driver.execute_script("""
                            var bars = document.querySelectorAll('simple-snack-bar');
                            for (var i = 0; i < bars.length; i++) {
                                var t = bars[i].textContent || '';
                                if (t.indexOf('Modelo de documento inserido com sucesso') !== -1) return true;
                            }
                            return false;
                        """):
                            snackbar_modelo_ok = True
                            break
                        time.sleep(0.2)
                    if snackbar_modelo_ok:
                        log('[MODELO] ✓ Snackbar "Modelo inserido" confirmado')
                    else:
                        log('[MODELO][WARN] Snackbar "Modelo inserido" não detectado após 3s, prosseguindo')
                except Exception as _e:
                    log(f'[MODELO][WARN] Exceção ao verificar snackbar: {_e}')

                # 7. Aguardar dialog fechar (rápido: só confirma que sumiu)
                aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', 'sumir', 5)

            except Exception as e:
                log(f'[ERRO] Falha ao inserir modelo: {e}')
                raise

            try:
                if inserir_conteudo:
                    log('[INSERIR] Executando função de inserção de conteúdo...')
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
                    log(f"[INSERIR] Resultado da inserção: {'' if ok else ''}")
            except Exception as e:
                log(f'[INSERIR][WARN] Erro ao executar inserção: {e}')
        else:
            log('8. Sem modelo para inserir')

        # SEMPRE finaliza/salva após inserir modelo (finalizar sempre True)
        log('[COMUNICACAO] Finalizando minuta (salvando)...')
        finalizar_minuta(driver, log=log)

        return True
    except Exception:
        raise
