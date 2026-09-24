import re
import time
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
        texto_norm = normalizar_string(texto_label)
        radios = espera.elementos(driver, 'mat-radio-button')
        for r in radios:
            lbl = normalizar_string(getattr(r, 'text', '') or '')
            if texto_norm in lbl:
                safe_click_no_scroll(driver, r)
                return True
        return False
    except Exception as e:
        raise NavegacaoError(f'clicar_radio_button_js({texto_label}): {e}')


def _aguardar_ck_com_conteudo(driver: Any, timeout: int = 8) -> bool:
    from Fix.selectors_pje import EDITOR_AREA_CONTEUDO
    expr = f"""(() => {{
        if (document.querySelector('pdf-viewer')) return true;
        var area = document.querySelector('{EDITOR_AREA_CONTEUDO}');
        if (!area) return false;
        var texto = (area.innerText || '').replace(/\\s/g, '');
        return texto.length > 1 || area.querySelector('figure') !== null;
    }})()"""
    return bool(espera.ate_js(driver, expr, teto=timeout))


def aguardar_ato_confeccionado(driver: Any, timeout_fechar: int = 15, timeout_icone: int = 10, log=None) -> bool:
    if log is None:
        def log(_msg): return None

    espera.ate_texto(driver, 'simple-snack-bar', 'Ato elaborado com sucesso', teto=5)

    ok_fechar = aguardar_renderizacao_nativa(driver, 'pje-pec-dialogo-ato', 'sumir', timeout_fechar)
    if not ok_fechar:
        log('[MINUTA][WARN] Timeout aguardando dialog fechar — prosseguindo mesmo assim')

    ok_icone = aguardar_renderizacao_nativa(driver, 'i.pec-icone-verde-ato-agrupado', 'aparecer', timeout_icone)
    if not ok_icone:
        log('[MINUTA][WARN] Icone verde nao detectado dentro do timeout')

    return ok_icone


def aguardar_estabilizacao_para_destinatarios(driver: Any, log=None, timeout: int = 15) -> bool:
    if log is None:
        def log(_msg):
            return None

    if not aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', 'sumir', timeout):
        log(f'[BARREIRA][WARN] Dialog de modelo ainda visível após {timeout}s — risco de overlay nos destinatários')

    if not aguardar_renderizacao_nativa(driver, 'pje-pec-dialogo-ato', 'sumir', timeout):
        log(f'[BARREIRA][WARN] Dialog do ato ainda visível após {timeout}s')

    if not (
        aguardar_renderizacao_nativa(driver, 'i.pec-icone-verde-ato-agrupado', 'aparecer', 5)
        or aguardar_renderizacao_nativa(driver, 'i.pec-icone-verde-ato-individual-tabela-destinatarios', 'aparecer', 5)
    ):
        log('[BARREIRA][WARN] Nenhum tick verde detectado em 5s — prosseguindo')

    if not aguardar_renderizacao_nativa(
        driver,
        'tbody.cdk-drop-list',
        'aparecer',
        10,
    ):
        log('[BARREIRA][WARN] Tabela de destinatários não detectada em 10s')
        return False
    return True


def finalizar_minuta(driver: Any, log=None) -> bool:
    if log is None:
        def log(_msg):
            return None

    try:
        seletor_finalizar = 'button[aria-label="Finalizar minuta"]'
        btn = wait_for_clickable(driver, seletor_finalizar, timeout=5, by=By.CSS_SELECTOR)
        if not btn:
            raise NoSuchElementException(seletor_finalizar)
        safe_click_no_scroll(driver, btn)

        ato_ok = aguardar_ato_confeccionado(driver, log=log)
        if not ato_ok:
            raise Exception('Ato NÃO confeccionado — nenhum sinal de confirmação')
        return True

    except NoSuchElementException:
        return True

    except Exception as e:
        log(f'[SALVAR][ERRO] Falha ao salvar/finalizar: {e}')
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

    try:
        from Fix.utils import inserir_link_ato_validacao

        if not escolher_opcao_select_js(driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de expediente')
            raise Exception('Falha ao selecionar tipo de expediente')

        aguardar_renderizacao_nativa(driver, 'mat-radio-button', 'aparecer', 5)

        if prazo == "0" or prazo == 0:
            tipo_prazo = "sem prazo"

        if not clicar_radio_button_js(driver, tipo_prazo, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de prazo')
            raise Exception(f'Tipo de prazo "{tipo_prazo}" não encontrado')

        if prazo and tipo_prazo != "sem prazo":
            tipo_prazo_norm = normalizar_string(tipo_prazo)
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

            aguardar_renderizacao_nativa(driver, 'mat-form-field input[type="number"], input[aria-label="Prazo em dias úteis"], input[placeholder*="data"], input[type="date"], input[formcontrolname="prazo"]', 'aparecer', 10)

            for seletor in seletores_prazo:
                if preencher_input_js(driver, seletor, prazo, debug=debug):
                    prazo_preenchido = True
                    break

            if not prazo_preenchido:
                log('[AVISO] Não foi possível preencher prazo com nenhum seletor, tentando fallback...')
                try:
                    prazo_preenchido = preencher_campo(
                        driver, 'mat-form-field input[type="number"]', str(prazo), limpar=True
                    )
                    if not prazo_preenchido:
                        raise Exception('Elemento input_prazo não encontrado')
                except Exception as e:
                    log(f'[FALLBACK][ERRO] Falha no fallback: {e}')
                    prazo_preenchido = False

        if not aguardar_e_clicar(driver, 'button[aria-label="Confeccionar ato agrupado"]', timeout=10, by=By.CSS_SELECTOR, usar_js=False):
            raise Exception('Botão Confeccionar ato agrupado não disponível')

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

        desc_to_use = descricao if descricao else nome_comunicacao
        if not preencher_input_js(driver, 'input[aria-label="Descrição"]', desc_to_use, debug=debug):
            log('[ERRO] Falha ao preencher descrição')
            raise Exception('Falha ao preencher descrição')

        if sigilo:
            try:
                from Play.pjeplay.pje import mat_checkbox
                marcado = mat_checkbox(driver, 'input[name="sigiloso"], mat-checkbox[formcontrolname="sigiloso"]', marcar=True, timeout=5)
                if not marcado:
                    cb = espera.elemento(driver, 'input[name="sigiloso"]', teto=2, visivel=False)
                    if cb:
                        safe_click_no_scroll(driver, cb)
            except Exception as e:
                log(f'[WARN] Falha ao marcar sigilo: {e}')

        if modelo_nome:
            try:
                campo_filtro = wait_for_clickable(driver, 'input#inputFiltro', timeout=10, by=By.CSS_SELECTOR)
                if not campo_filtro:
                    raise Exception('Campo de filtro de modelo não encontrado')

                preencher_campo(driver, 'input#inputFiltro', modelo_nome, trigger_events=True, limpar=True)
                if hasattr(driver, 'page') and hasattr(driver.page, 'keyboard'):
                    try:
                        driver.page.keyboard.press('Enter')
                    except Exception:
                        pass

                aguardar_renderizacao_nativa(driver, '.nodo-filtrado', 'aparecer', 10)
                nodo = aguardar_e_clicar(driver, '.nodo-filtrado', timeout=15)
                if not nodo:
                    raise Exception(f'Nodo filtrado não encontrado para modelo "{modelo_nome}"')

                modal_aberto = aguardar_renderizacao_nativa(
                    driver, 'pje-dialogo-visualizar-modelo', 'aparecer', 5
                )
                if not modal_aberto:
                    log('[MODELO][WARN] Modal de visualização não abriu, tentando inserir mesmo assim...')

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

                try:
                    safe_click_no_scroll(driver, btn_inserir)
                except StaleElementReferenceException:
                    log('[MODELO][WARN] Elemento ficou stale, tentando novamente...')
                    btn_inserir = espera.elemento(driver, seletor_btn_inserir)
                    if btn_inserir:
                        safe_click_no_scroll(driver, btn_inserir)

                try:
                    snackbar_modelo_ok = espera.ate_texto(
                        driver, 'simple-snack-bar', 'Modelo de documento inserido com sucesso', teto=3.0
                    )
                    if not snackbar_modelo_ok:
                        log('[MODELO][WARN] Snackbar "Modelo inserido" não detectado após 3s, prosseguindo')
                except Exception as _e:
                    log(f'[MODELO][WARN] Exceção ao verificar snackbar: {_e}')

                aguardar_renderizacao_nativa(driver, 'pje-dialogo-visualizar-modelo', 'sumir', 10)

                if not _aguardar_ck_com_conteudo(driver, timeout=8):
                    log('[MODELO][WARN] Conteudo do modelo nao confirmado no editor apos 8s')

            except Exception as e:
                log(f'[ERRO] Falha ao inserir modelo: {e}')
                raise

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

        finalizar_minuta(driver, log=log)
        return True
    except Exception:
        raise
