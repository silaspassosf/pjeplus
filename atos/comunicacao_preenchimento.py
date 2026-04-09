import time
import re
import unicodedata
from selenium.webdriver.common.by import By
from Fix.selenium_base.wait_operations import wait_for_clickable, esperar_elemento
from Fix.selenium_base.click_operations import aguardar_e_clicar, safe_click_no_scroll
from Fix.core import aguardar_renderizacao_nativa
from Fix.log import logger
from typing import Optional, Union, Callable, Any
from selenium.webdriver.remote.webdriver import WebDriver

def normalizar_string(valor):
    if not valor:
        return ''
    valor_norm = unicodedata.normalize('NFD', str(valor))
    valor_norm = ''.join(ch for ch in valor_norm if unicodedata.category(ch) != 'Mn')
    return valor_norm.lower()


def preencher_input_js(driver: WebDriver, seletor: str, valor: Union[str, int], max_tentativas: int = 3, debug: bool = False) -> bool:
    for tentativa in range(1, max_tentativas + 1):
        try:
            elemento = wait_for_clickable(driver, seletor, timeout=3, by=By.CSS_SELECTOR)
            if not elemento:
                raise Exception('Elemento não clicável')
            safe_click_no_scroll(driver, elemento, log=False)
            time.sleep(0.3)
            driver.execute_script("""
                var el = arguments[0];
                var val = arguments[1];
                window.focus();
                el.focus();
                Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('dateChange', {bubbles: true}));
                el.dispatchEvent(new Event('keyup', {bubbles: true}));
                var enterEvent = new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true });
                el.dispatchEvent(enterEvent);
                el.blur();
            """, elemento, str(valor))
            time.sleep(0.2)
            if debug:
                logger.info(f"[INPUT][OK] {seletor}='{valor}'")
            return True
        except Exception:
            if tentativa < max_tentativas:
                time.sleep(0.4)
            else:
                return False
    return False


def escolher_opcao_select_js(driver, seletor_select, valor_desejado, debug=False):
    """Seleciona opção em mat-select simulando digitação letra a letra.

    Padrão idêntico ao simularDigitacaoDeTexto do gigs-plugin.js:
    foca o mat-select e dispara keydown/keypress/keyup por letra.
    O Angular Material filtra e seleciona automaticamente — sem abrir
    dropdown de mat-option, portanto limpar_overlays_headless não interfere.
    Aguarda via aguardar_renderizacao_nativa (MutationObserver, sem WebDriverWait).
    """
    try:
        from Fix.core import aguardar_renderizacao_nativa
        select_el = wait_for_clickable(driver, seletor_select, timeout=10, by=By.CSS_SELECTOR)
        if not select_el:
            return False

        # Focar o mat-select e digitar letra a letra (mini-selenium.js:simularDigitacaoDeTexto)
        driver.execute_script("""
            var el = arguments[0];
            var texto = arguments[1];
            el.focus();
            for (var i = 0; i < texto.length; i++) {
                var letra = texto[i];
                el.dispatchEvent(new KeyboardEvent('keydown',  {key: letra, bubbles: true, cancelable: true}));
                el.dispatchEvent(new KeyboardEvent('keypress', {key: letra, bubbles: true, cancelable: true}));
                el.dispatchEvent(new KeyboardEvent('keyup',    {key: letra, bubbles: true, cancelable: true}));
            }
        """, select_el, valor_desejado)

        # Aguardar Angular processar (MutationObserver nativo — sem polling)
        aguardar_renderizacao_nativa(driver, 'mat-option[role="option"]', 'aparecer', 3)

        # Clicar na primeira opção que bater (dropdown pode ou não aparecer dependendo do Angular build)
        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
        valor_norm = normalizar_string(valor_desejado)
        for opcao in opcoes:
            texto_opcao = opcao.get_attribute('innerText') or opcao.text or ''
            if valor_norm == normalizar_string(texto_opcao) or valor_norm in normalizar_string(texto_opcao):
                driver.execute_script("arguments[0].click();", opcao)
                return True

        # Fallback: se não abriu dropdown, o Angular já selecionou via keydown — verificar valor atual
        valor_atual = select_el.get_attribute('value') or (
            select_el.find_element(By.CSS_SELECTOR, 'span.mat-select-value-text').text
            if select_el.find_elements(By.CSS_SELECTOR, 'span.mat-select-value-text') else ''
        )
        if valor_norm in normalizar_string(valor_atual):
            return True

        # Blur para fechar qualquer painel aberto
        driver.execute_script("arguments[0].blur();", select_el)
        return False
    except Exception:
        return False


def clicar_radio_button_js(driver, texto_label, debug=False):
    """
    Clica em radio button baseado no texto do label.
    Baseado na implementação simples do a.py: sempre clica no radio correto.
    """
    try:
        if debug:
            print(f'[RADIO] Selecionando: "{texto_label}"')

        # Normalizar o texto como no a.py
        texto_norm = texto_label.lower().replace('ú', 'u')

        radios = driver.find_elements(By.CSS_SELECTOR, 'mat-radio-button')

        for radio in radios:
            label = radio.get_attribute('innerText') or radio.text or ''
            label_norm = label.lower().replace('ú', 'u')

            if texto_norm in label_norm:
                if debug:
                    print(f'[RADIO][ENCONTRADO] Radio encontrado: "{label}"')
                # Clicar no mat-radio-button em si, não no input (como no a.py)
                try:
                    if debug:
                        print(f'[RADIO][TENTATIVA] Clicando no mat-radio-button')
                    radio.click()
                    if debug:
                        print(f'[RADIO] Selecionado: "{label}"')
                    return True
                except Exception as e1:
                    if debug:
                        print(f'[RADIO][FALHA] mat-radio-button falhou: {str(e1)[:50]}...')
                    # Fallback: tentar clicar no input
                    try:
                        if debug:
                            print(f'[RADIO][FALLBACK] Tentando clicar no input')
                        input_elem = radio.find_element(By.CSS_SELECTOR, 'input[type="radio"]')
                        input_elem.click()
                        if debug:
                            print(f'[RADIO] Selecionado (fallback): "{label}"')
                        return True
                    except Exception as e2:
                        if debug:
                            print(f'[RADIO][FALHA] Input também falhou: {str(e2)[:50]}...')
                        continue

        if debug:
            print(f'[RADIO] ERRO: Radio "{texto_label}" não encontrado')
        return False

    except Exception as e:
        if debug:
            print(f'[RADIO] ERRO: {e}')
        return False


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
    debug: bool = False,
    log: Optional[Callable] = None,
) -> bool:
    if log is None:
        def log(_msg):
            return None

    try:
        from .wrappers_utils import esperar_insercao_modelo, preparar_campo_filtro_modelo
        from Fix.utils import inserir_link_ato_validacao

        log(f'1. Selecionando tipo de expediente: {tipo_expediente}')
        if not escolher_opcao_select_js(driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de expediente')
            raise Exception('Falha ao selecionar tipo de expediente')

        log(f'2. Selecionando tipo de prazo: {tipo_prazo}')
        if prazo == "0" or prazo == 0:
            tipo_prazo = "sem prazo"

        if not clicar_radio_button_js(driver, tipo_prazo, debug=debug):
            log('[ERRO] Falha ao selecionar tipo de prazo')
            raise Exception(f'Tipo de prazo "{tipo_prazo}" não encontrado')
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

            # Pular verificação de aparecimento do campo - se o radio foi clicado,
            # o campo deve estar disponível. Ir direto para preenchimento.
            time.sleep(0.6)

            # Tentar cada seletor até encontrar um que funcione (como no legado)
            for seletor in seletores_prazo:
                if preencher_input_js(driver, seletor, prazo, debug=debug):
                    prazo_preenchido = True
                    break
                time.sleep(0.3)

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
        time.sleep(0.8)

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

                    time.sleep(0.5)

                    try:
                        if not esperar_elemento(driver, 'mat-option', timeout=3, by=By.CSS_SELECTOR):
                            raise Exception('mat-option ainda não disponível')
                    except Exception:
                        driver.execute_script("""
                            var el = arguments[0];
                            el.focus();
                            el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 40, which: 40, bubbles: true}));
                        """, input_subtipo)
                        time.sleep(0.5)
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
                            time.sleep(0.5)
                            btn_confeccionar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
                            driver.execute_script("arguments[0].click();", btn_confeccionar)
                            time.sleep(0.8)
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
                # Espera campo de filtro aparecer usando aguardar_renderizacao_nativa
                if not aguardar_renderizacao_nativa(driver, 'input#inputFiltro', 'aparecer', 10):
                    raise Exception('Campo de filtro de modelo não apareceu')
                campo_filtro = driver.find_element(By.CSS_SELECTOR, 'input#inputFiltro')

                if not preparar_campo_filtro_modelo(driver, log=debug):
                    raise Exception('Falha ao preparar campo de filtro de modelos')

                driver.execute_script("""
                    var el = arguments[0];
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('keyup', {bubbles: true}));
                """, campo_filtro)

                time.sleep(0.3)

                driver.execute_script("""
                    var el = arguments[0];
                    var val = arguments[1];
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

                time.sleep(1.5)

                try:
                    nodo = wait_for_clickable(driver, '.nodo-filtrado', timeout=10, by=By.CSS_SELECTOR)
                    if not nodo:
                        raise Exception('Nodo filtrado não clicável')
                    driver.execute_script("arguments[0].click();", nodo)
                    time.sleep(0.5)

                    btn_inserir = wait_for_clickable(driver, 'pje-dialogo-visualizar-modelo button', timeout=8, by=By.CSS_SELECTOR)
                    if not btn_inserir:
                        raise Exception('Botão inserir não clicável')
                    driver.execute_script("arguments[0].click();", btn_inserir)
                    log(' Modelo inserido')
                    time.sleep(1.0)  # Tempo para inserção completar
                except Exception as e_nodo:
                    log(f'[MODELO][ERRO] Modelo "{modelo_nome}" não encontrado ou não foi possível inserir: {e_nodo}')
                    raise Exception(f'Modelo não encontrado: {modelo_nome}')

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

        log('9. Salvando e finalizando minuta')
        try:
            if not aguardar_e_clicar(driver, 'button[aria-label="Salvar"]', timeout=10, by=By.CSS_SELECTOR, usar_js=False):
                raise Exception('Botão Salvar não disponível')
            log(' Botão Salvar clicado')
            time.sleep(1.0)

            if not aguardar_e_clicar(driver, 'button[aria-label="Finalizar minuta"]', timeout=10, by=By.CSS_SELECTOR, usar_js=False):
                raise Exception('Botão Finalizar minuta não disponível')
            log(' Botão Finalizar minuta clicado')
            time.sleep(2.0)

            log(' Comunicação criada com sucesso!')

        except Exception as e:
            log(f'[SALVAR][ERRO] Falha ao salvar/finalizar: {e}')
            raise

        return True
    except Exception:
        raise
