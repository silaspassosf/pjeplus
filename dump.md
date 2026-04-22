# atos/comunicacao.py

```python
import time
from Fix.extracao import criar_gigs
from Fix.log import logger
from Fix.selenium_base.wait_operations import esperar_elemento
from selenium.webdriver.common.by import By
from .comunicacao_navigation import abrir_minutas
from .comunicacao_coleta import executar_coleta_conteudo
from .comunicacao_preenchimento import executar_preenchimento_minuta
from .comunicacao_destinatarios import selecionar_destinatarios
from .comunicacao_finalizacao import alterar_meio_expedicao, salvar_minuta_final, limpar_destinatarios_existentes
from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from typing import Optional, Any, Callable, Union, List, Dict, Tuple
from selenium.webdriver.remote.webdriver import WebDriver


def _extrair_observacao_gigs_vencida_xs_pec(driver: WebDriver, debug: bool = False) -> Optional[str]:
    """Extrai observação da linha GIGS vencida (ícone vermelho) com XS e PEC."""
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, '#tabela-atividades tbody tr')
        for linha in linhas:
            try:
                icone_vermelho = linha.find_elements(By.CSS_SELECTOR, 'i.fa-clock.danger, i.danger.fa-clock')
                if not icone_vermelho:
                    continue

                span_descricao = linha.find_element(By.CSS_SELECTOR, 'span.descricao')
                texto_descricao = (span_descricao.text or '').strip()
                if not texto_descricao:
                    continue

                texto_lower = texto_descricao.lower()
                if 'xs' not in texto_lower:
                    continue

                if texto_lower.startswith('prazo:'):
                    texto_descricao = texto_descricao[6:].strip()

                if debug:
                    logger.info(f"[COMUNICACAO][GIGS] Observação extraída para destinatário informado: {texto_descricao}")
                return texto_descricao
            except Exception:
                continue

        if debug:
            logger.info('[COMUNICACAO][GIGS] Nenhuma linha vencida com XS+PEC encontrada no painel')
        return None
    except Exception as e:
        if debug:
            logger.info(f"[COMUNICACAO][GIGS][ERRO] Falha ao extrair observação do painel: {e}")
        return None


def comunicacao_judicial(
    driver: WebDriver,
    tipo_expediente: str,
    prazo: int,
    nome_comunicacao: str,
    sigilo: str,
    modelo_nome: str,
    trocar_modelo: bool = False,
    **kwargs
) -> bool:
    """Função direta (não-wrapper) para manter compatibilidade com código existente."""
    wrapper_func = make_comunicacao_wrapper(
        tipo_expediente=tipo_expediente,
        prazo=prazo,
        nome_comunicacao=nome_comunicacao,
        sigilo=sigilo,
        modelo_nome=modelo_nome,
        subtipo=kwargs.get('subtipo'),
        descricao=kwargs.get('descricao'),
        tipo_prazo=kwargs.get('tipo_prazo', 'dias uteis'),
        gigs_extra=kwargs.get('gigs_extra'),
        coleta_conteudo=kwargs.get('coleta_conteudo'),
        inserir_conteudo=kwargs.get('inserir_conteudo'),
        cliques_polo_passivo=kwargs.get('cliques_polo_passivo', 1),
        destinatarios=kwargs.get('destinatarios', 'extraido'),
        mudar_expediente=kwargs.get('mudar_expediente'),
        checar_sp=kwargs.get('checar_sp'),
        endereco_tipo=kwargs.get('endereco_tipo'),
        trocar_modelo=trocar_modelo
    )
    debug_value = kwargs.pop('debug', False)
    terceiro_value = kwargs.pop('terceiro', False)
    return wrapper_func(driver, debug=debug_value, terceiro=terceiro_value, **kwargs)


def make_comunicacao_wrapper(
    tipo_expediente: str, 
    prazo: int, 
    nome_comunicacao: str, 
    sigilo: str, 
    modelo_nome: str, 
    subtipo: Optional[str] = None, 
    descricao: Optional[str] = None,
    tipo_prazo: str = 'dias uteis',
    gigs_extra: Optional[Union[bool, Tuple, List, Any]] = None,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    cliques_polo_passivo: int = 1,
    cliques_informado: int = 2,
    destinatarios: str = 'extraido',
    mudar_expediente: Optional[bool] = None,
    checar_sp: Optional[bool] = None,
    endereco_tipo: Optional[str] = None,
    trocar_modelo: bool = False,
    wrapper_name: Optional[str] = None,  # Nome específico para __name__
    terceiro_default: bool = False,
    assinar: bool = False
) -> Callable[[WebDriver, bool, Any], bool]:
    def wrapper(
        driver: WebDriver,
        numero_processo: Optional[str] = None,
        observacao: Optional[str] = None,
        destinatarios_override: Optional[List[Dict[str, Any]]] = None,
        debug: bool = False,
        **overrides: Any
    ) -> bool:
        """
        Wrapper que aceita overrides genéricos e repassa quaisquer parâmetros fornecidos
        diretamente para `comunicacao_judicial`, tratando `mudar_expediente` como um
        parâmetro comum (como `descricao`, `prazo`, etc.).
        """
        # Resolve destinatários override explicitamente se presente
        destinatarios_param = destinatarios_override if destinatarios_override is not None else (
            overrides.get('destinatarios') if 'destinatarios' in overrides else destinatarios
        )

        # Se o wrapper foi configurado com gigs_extra, executá-lo ANTES do início do fluxo
        if gigs_extra:
            try:
                if gigs_extra is True:
                    criar_gigs(driver, prazo, '', nome_comunicacao)
                elif isinstance(gigs_extra, (tuple, list)):
                    if len(gigs_extra) >= 3:
                        dias_uteis, responsavel, observacao_gigs = gigs_extra[:3]
                        criar_gigs(driver, dias_uteis, responsavel, observacao_gigs)
                    elif len(gigs_extra) == 2:
                        dias_uteis, observacao_gigs = gigs_extra
                        criar_gigs(driver, dias_uteis, '', observacao_gigs)
                    else:
                        criar_gigs(driver, gigs_extra)
                else:
                    criar_gigs(driver, gigs_extra)
            except Exception as e:
                try:
                    logger.info(f'[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs antes do fluxo: {e}')
                except Exception:
                    pass

        # Construir kwargs a serem repassados para comunicacao_judicial
        # Se o modo for 'informado' — primeiro garantir que os dados do processo
        # estejam disponíveis (populando dadosatuais.json), depois extrair a
        # observação dos GIGS. Isso permite que a comparação entre observação
        # e os dados do processo seja feita com os dados já carregados.
        dados_processo_wrapper = None
        if destinatarios_param == 'informado':
            try:
                from Fix.extracao_processo import extrair_dados_processo
                logger.info('[COMUNICACAO][ORQUESTRA] Extraindo dados do processo ANTES da leitura da observação (informado)')
                dados_processo_wrapper = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                logger.info(f"[COMUNICACAO][ORQUESTRA] extrair_dados_processo retornou tipo={type(dados_processo_wrapper)}; reu_count={len(dados_processo_wrapper.get('reu', [])) if isinstance(dados_processo_wrapper, dict) else 'N/A'}")
            except Exception as e:
                logger.info(f"[COMUNICACAO][ORQUESTRA][WARN] Falha ao extrair dados antes da observação: {e}")

            observacao_gigs = _extrair_observacao_gigs_vencida_xs_pec(driver, debug=debug)
            if observacao_gigs:
                observacao = observacao_gigs
            else:
                if not observacao or not (isinstance(observacao, str) and observacao.strip()):
                    logger.info('[COMUNICACAO][GIGS][WARN] Observação não localizada para informado - fallback polo passivo 2x')
                    destinatarios_param = 'polo_passivo_2x'
                else:
                    logger.info('[COMUNICACAO][GIGS] Observação fornecida será usada para seleção de destinatários')

        call_kwargs = {
            'driver': driver,
            'tipo_expediente': tipo_expediente,
            'prazo': prazo,
            'nome_comunicacao': nome_comunicacao,
            'sigilo': sigilo,
            'modelo_nome': modelo_nome,
            'subtipo': overrides.get('subtipo', subtipo),
            'descricao': overrides.get('descricao', descricao if descricao else nome_comunicacao),
            'tipo_prazo': overrides.get('tipo_prazo', tipo_prazo),
            # Evitar repassar gigs_extra para não duplicar criação
            'gigs_extra': None,
            'coleta_conteudo': overrides.get('coleta_conteudo', overrides.get('coleta_conteudo_', coleta_conteudo)),
            'inserir_conteudo': overrides.get('inserir_conteudo', overrides.get('inserir_conteudo_', inserir_conteudo)),
            'cliques_polo_passivo': overrides.get('cliques_polo_passivo', cliques_polo_passivo),
            'destinatarios': destinatarios_param,
            # Passa adiante quaisquer flags de controle (mudar_expediente, checar_sp) diretamente
            'mudar_expediente': mudar_expediente,
            'checar_sp': overrides.get('checar_sp', overrides.get('checar_sp_', checar_sp)),
            'endereco_tipo': endereco_tipo,
            'debug': debug,
            'terceiro': overrides.get('terceiro', terceiro_default),
            'trocar_modelo': overrides.get('trocar_modelo', trocar_modelo)
        }

        # Log function: usa print quando passado via log=print no override (ex: f.py)
        log_fn = overrides.get('log', logger.info)

        # Executar fluxo de comunicação orquestrado pelos módulos especializados
        try:
            # 0. Executar coleta de conteúdo PRIMEIRO (na aba /detalhe)
            if coleta_conteudo:
                log_fn(f"[COMUNICACAO][ORQUESTRA] Executando coleta de conteúdo na aba detalhes para {nome_comunicacao}")
                executar_coleta_conteudo(driver, coleta_conteudo, debug=debug)

            # 1. Abrir minutas (após coleta)
            log_fn(f"[COMUNICACAO][ORQUESTRA] Abrindo minutas para {nome_comunicacao}")
            sucesso_abertura = abrir_minutas(driver, debug=debug)
            if not sucesso_abertura:
                raise Exception("Falha ao abrir tela de minutas")

            # 1.5. REMOVIDO: Limpeza de destinatários (causava travamento)
            # limpar_destinatarios_existentes(driver, debug=debug)

            # 2. Executar preenchimento da minuta
            log_fn("[COMUNICACAO][ORQUESTRA] Executando preenchimento da minuta")
            executar_preenchimento_minuta(
                driver=driver,
                tipo_expediente=tipo_expediente,
                prazo=prazo,
                nome_comunicacao=nome_comunicacao,
                subtipo=subtipo,
                descricao=call_kwargs.get('descricao'),
                tipo_prazo=tipo_prazo,
                sigilo=sigilo,
                modelo_nome=modelo_nome,
                inserir_conteudo=inserir_conteudo,
                debug=debug,
                log=log_fn
            )

            # 3. Selecionar destinatários
            log_fn("[COMUNICACAO][ORQUESTRA] Selecionando destinatários")
            resultado_selecao = selecionar_destinatarios(
                driver=driver,
                destinatarios=destinatarios_param,
                cliques_polo_passivo=call_kwargs.get('cliques_polo_passivo', 1),
                cliques_informado=cliques_informado,
                debug=debug,
                log=log_fn,
                observacao=observacao,
                numero_processo=numero_processo,
                terceiro=call_kwargs.get('terceiro', False),
                dados_processo=dados_processo_wrapper
            )

            # 3.5. Validar seleção e aguardar renderização da tabela
            if destinatarios_param is not None and destinatarios_param != '':
                # aceitar formato de retorno antigo para compatibilidade
                status = None
                count = 0
                if isinstance(resultado_selecao, dict):
                    status = resultado_selecao.get('status')
                    count = int(resultado_selecao.get('count', 0) or 0)
                else:
                    if isinstance(resultado_selecao, int):
                        status = 'ok' if resultado_selecao > 0 else 'empty'
                        count = resultado_selecao
                    else:
                        status = 'geral'

                if status == 'ok' and count > 0:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Status: {count} destinatário(s) selecionado(s) pelo módulo.")
                elif status == 'empty':
                    log_fn("[COMUNICACAO][ORQUESTRA] Status: Nenhum destinatário validado. Fallback acionado internamente.")
                else:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Status: {status} selection route concluded.")

                # Aguarda a renderização dos cards na tabela — preferir observer nativo
                if status in ('ok', 'fallback', 'geral') or count > 0:
                    try:
                        try:
                            from Fix.core import aguardar_renderizacao_nativa as _observer_wait
                            ok_render = _observer_wait(driver, 'tbody.cdk-drop-list tr.cdk-drag', modo='aparecer', timeout=10)
                        except Exception:
                            ok_render = False

                        if ok_render:
                            log_fn("[COMUNICACAO][ORQUESTRA] Destinatários renderizados na DOM (observer).")
                        else:
                            if esperar_elemento(driver, 'tbody.cdk-drop-list tr.cdk-drag', timeout=10, by=By.CSS_SELECTOR):
                                log_fn("[COMUNICACAO][ORQUESTRA] Destinatários renderizados na DOM (esperar_elemento fallback).")
                            else:
                                log_fn("[COMUNICACAO][ORQUESTRA] Timeout: Tabela não renderizou os destinatários.")

                        try:
                            driver.execute_script("return window.requestAnimationFrame(function(){});")
                        except Exception:
                            pass
                    except Exception as e:
                        log_fn(f"[COMUNICACAO][ORQUESTRA] Erro ao aguardar renderização: {e}")

            # 4. Alterar meio de expedição se necessário
            if endereco_tipo == 'correios':
                log_fn("[COMUNICACAO][ORQUESTRA] Alterando meio de expedição para correios")
                alterar_meio_expedicao(
                    driver,
                    debug=debug,
                    log=log_fn,
                    trocar_modelo=call_kwargs.get('trocar_modelo', False)
                )

            # 5. Salvar minuta final
            log_fn("[COMUNICACAO][ORQUESTRA] Salvando minuta final")
            salvar_minuta_final(driver, sigilo, debug=debug, log=log_fn, executar_visibilidade=False, assinar=assinar)

            # 6. Fechar aba de minutas e voltar para aba de detalhe
            # (necessário para execução sequencial de múltiplas notificações no mesmo processo)
            try:
                handles = driver.window_handles
                if len(handles) > 1:
                    driver.close()
                    driver.switch_to.window(handles[0])
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Aba de minutas fechada; retornou à aba de detalhe para {nome_comunicacao}")
            except Exception as e_fechar:
                log_fn(f"[COMUNICACAO][ORQUESTRA] Falha ao fechar aba de minutas: {e_fechar}")

            if str(sigilo).lower() in ("sim", "true", "1"):
                try:
                    log_fn('[COMUNICACAO][ORQUESTRA] Executando visibilidade_sigilosos após fechamento da aba de minutas')
                    executar_visibilidade_sigilosos_se_necessario(driver, True, debug=debug)
                    log_fn('[COMUNICACAO][ORQUESTRA] Visibilidade extra aplicada por sigilo positivo.')
                except Exception as e_vis:
                    log_fn(f"[COMUNICACAO][ORQUESTRA] Falha ao aplicar visibilidade extra após fechar aba: {e_vis}")

            log_fn(f"[COMUNICACAO][ORQUESTRA] Fluxo concluído com sucesso para {nome_comunicacao}")
            return True

        except Exception as e:
            log_fn(f"[COMUNICACAO][ORQUESTRA][ERRO] Falha no fluxo: {e}")
    
    return wrapper
```

# atos/comunicacao_preenchimento.py

```python
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
                time.sleep(0.4)
        except Exception:
            if tentativa < max_tentativas:
                time.sleep(0.4)
    return False


def escolher_opcao_select_js(driver, seletor_select, valor_desejado, debug=False):
    """Abre o mat-select via JS click e clica na opção correspondente.

    Comportamento idêntico ao legado (_escolher_opcao_select_js):
    clica no mat-select para abrir o dropdown, aguarda as mat-options via
    aguardar_renderizacao_nativa (MutationObserver) e clica na opção correta.
    """
    try:
        select_el = wait_for_clickable(driver, seletor_select, timeout=10, by=By.CSS_SELECTOR)
        if not select_el:
            return False

        # Abrir dropdown via JS click (idêntico ao legado _escolher_opcao_select_js)
        driver.execute_script("arguments[0].click();", select_el)

        # Aguardar mat-options aparecerem (observer nativo — sem WebDriverWait polling)
        aguardar_renderizacao_nativa(driver, 'mat-option[role="option"]', 'aparecer', 10)

        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
        valor_norm = normalizar_string(valor_desejado)
        for opcao in opcoes:
            texto_opcao = opcao.get_attribute('innerText') or opcao.text or ''
            if valor_norm == normalizar_string(texto_opcao) or valor_norm in normalizar_string(texto_opcao):
                driver.execute_script("arguments[0].click();", opcao)
                return True

        # Fechar painel sem seleção
        driver.execute_script("arguments[0].blur();", select_el)
        return False
    except Exception:
        return False


def clicar_radio_button_js(driver, texto_label, debug=False):
    """Clica no input[type=radio] dentro do mat-radio-button correspondente.
    Identico ao gigs-plugin: clicarBotao(ancora.querySelector('input')).
    """
    try:
        texto_norm = normalizar_string(texto_label)
        ok = driver.execute_script("""
            var textoAlvo = arguments[0];
            function normLabel(s) {
                return s.normalize('NFD').replace(/[ - ]/g, '').toLowerCase();
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
    except Exception:
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
                    aguardar_renderizacao_nativa(driver, 'button[aria-label="Salvar"]', 'aparecer', 5)
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
            aguardar_renderizacao_nativa(driver, 'snack-bar-container', 'aparecer', 5)

            log(' Comunicação criada com sucesso!')

        except Exception as e:
            log(f'[SALVAR][ERRO] Falha ao salvar/finalizar: {e}')
            raise

        return True
    except Exception:
        raise
```

# atos/comunicacao_finalizacao.py

```python
import time
from selenium.webdriver.common.by import By
from Fix.selenium_base.wait_operations import wait_for_clickable, esperar_elemento
from Fix.selenium_base.click_operations import aguardar_e_clicar
from Fix.utils_observer import aguardar_renderizacao_nativa

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
        return False


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
        return False


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
        return False

    # --- 2. Verificar snackbar de endereço inválido (antes de aguardar confirmação) ---
    try:
        aguardar_renderizacao_nativa(driver, 'snack-bar-container', modo='aparecer', timeout=1)
        snackbar_erro = esperar_elemento(driver, "snack-bar-container", timeout=1, by=By.CSS_SELECTOR)
        if snackbar_erro and 'Selecione o endere' in (snackbar_erro.text or ''):
            log('[COMUNICACAO][WARN] Erro de endereço inválido detectado. Removendo destinatário e re-tentando...')
            try:
                btn_fechar_snack = snackbar_erro.find_element(By.CSS_SELECTOR, "button")
                driver.execute_script("arguments[0].click();", btn_fechar_snack)
            except Exception:
                pass
            remover_destinatarios_invalidos(driver, debug=debug, log=log)
            time.sleep(0.8)
            # Retry salvar
            try:
                spans_retry = driver.find_elements(By.XPATH, "//span[contains(@class,'mat-button-wrapper') and normalize-space(text())='Salvar']")
                for span in spans_retry:
                    btn_retry = span.find_element(By.XPATH, './ancestor::button[1]')
                    if btn_retry.is_displayed() and btn_retry.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_retry)
                        driver.execute_script('arguments[0].click();', btn_retry)
                        log('[COMUNICACAO] Segundo clique em Salvar realizado após limpeza.')
                        break
            except Exception:
                pass
    except Exception:
        # Sem snackbar de erro = OK prosseguir
        pass

    # --- 3. Confirmar salvamento: btnFinalizarExpedientes aparece APENAS após save aceito ---
    # (igual ao atalhos.js: clicar Salvar → aguardar Assinar)
    aguardar_renderizacao_nativa(driver, 'button[name="btnFinalizarExpedientes"]', modo='aparecer', timeout=15)
    btn_finalizar = None
    try:
        btn_finalizar = driver.find_element(By.CSS_SELECTOR, 'button[name="btnFinalizarExpedientes"]')
    except Exception:
        pass
    if not btn_finalizar:
        # Fallback: texto 'Assinar ato'
        try:
            elementos = driver.find_elements(By.XPATH, "//button[.//span[contains(normalize-space(text()),'Assinar ato')]]")
            btn_finalizar = next((b for b in elementos if b.is_displayed() and b.is_enabled()), None)
        except Exception:
            pass

    if btn_finalizar:
        log('[COMUNICACAO] Salvamento confirmado — botão Assinar ato(s) detectado.')
    else:
        log('[COMUNICACAO][ERRO] Salvamento NÃO confirmado — botão Assinar ato(s) não apareceu após 15s.')
        return False

    if gigs_extra:
        log('[GIGS_EXTRA][WARN] Criação de GIGS via minuta removida. Use criar_gigs na aba /detalhe antes do fluxo.')

    # --- 4. Assinar se solicitado ---
    if assinar:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_finalizar)
            driver.execute_script("arguments[0].click();", btn_finalizar)
            log('[COMUNICACAO] Botão Assinar ato(s) clicado.')
        except Exception as e:
            log(f'[COMUNICACAO][ERRO] Falha ao clicar em Assinar ato(s): {e}')
            log('Comunicação processual finalizada.')
            return False

        # --- 4a. Detectar dialog de validação por dispositivo móvel ---
        _TIMEOUT_VALIDACAO_MOVEL = 180  # 3 minutos para o usuário autenticar
        try:
            dialog_movel = esperar_elemento(
                driver,
                '//h3[normalize-space(text())="Validação por dispositivo móvel"]',
                timeout=5,
                by=By.XPATH
            )
        except Exception:
            dialog_movel = None

        if dialog_movel:
            log('[COMUNICACAO] Dialog "Validação por dispositivo móvel" detectado — aguardando autenticação do usuário...')
            # Aguardar dialog fechar via MutationObserver (sem polling nem time.sleep)
            dialog_sumiu = aguardar_renderizacao_nativa(
                driver, 'mat-dialog-container', modo='sumir', timeout=_TIMEOUT_VALIDACAO_MOVEL
            )
            if not dialog_sumiu:
                log('[COMUNICACAO][ERRO] Timeout de 3 min aguardando autenticação por dispositivo móvel — assinatura não confirmada.')
                log('Comunicação processual finalizada.')
                return False
            log('[COMUNICACAO] Dialog de validação móvel fechado — verificando confirmação...')
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
        return False
```

# atos/comunicacao_destinatarios.py

```python
from Fix.selenium_base.click_operations import safe_click_no_scroll
from Fix.selenium_base.wait_operations import esperar_elemento, wait_for_clickable
from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.headless_helpers import click_headless_safe
import re
import json
import unicodedata
from selenium.webdriver.common.by import By
from Fix.log import log_seletor_multiplo, logger


def normalizar_string(valor):
    if not valor:
        return ''
    valor_norm = unicodedata.normalize('NFD', str(valor))
    valor_norm = ''.join(ch for ch in valor_norm if unicodedata.category(ch) != 'Mn')
    return valor_norm.lower()


def _normalizar_nome_para_match(nome):
    nome_norm = normalizar_string(nome)
    return re.sub(r'\s+', ' ', nome_norm).strip()


def _partial_name_match(nome_norm, texto_norm, min_tokens=2):
    try:
        tokens = [t for t in re.findall(r'[a-z0-9]+', nome_norm) if len(t) >= 3]
        if len(tokens) < min_tokens:
            return False
        found = sum(1 for t in tokens if t in texto_norm)
        return found >= min_tokens
    except Exception:
        return False


def _carregar_dadosatuais_local(caminho='dadosatuais.json'):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _montar_destinatarios_por_observacao(observacao, dados_processo, debug=False):
    if not observacao or not isinstance(dados_processo, dict):
        return []

    texto_obs = _normalizar_nome_para_match(observacao)
    if not texto_obs:
        return []

    texto_limpo = re.sub(r'^\s*prazo\s*:\s*', '', texto_obs, flags=re.I).strip()
    texto_limpo = re.sub(r'^\s*xs\s+pec\b', '', texto_limpo, flags=re.I).strip()

    stopwords = {
        'xs', 'pec', 'prazo', 'para', 'sobre', 'com', 'sem', 'de', 'da', 'do',
        'dos', 'das', 'e', 'ou', 'manifestacao', 'manifestação', 'idpj'
    }
    tokens_alvo = [
        t for t in re.findall(r'[a-z0-9]+', texto_limpo)
        if len(t) >= 3 and t not in stopwords
    ]

    if debug:
        try:
            logger.info(f"[DESTINATARIOS][DEBUG] Tokens alvo extraídos da observação: {tokens_alvo}")
        except Exception:
            pass

    if not tokens_alvo:
        return []

    destinatarios = []
    vistos = set()
    for parte in dados_processo.get('reu', []) or []:
        nome = (parte.get('nome') or '').strip()
        doc = (parte.get('cpfcnpj') or parte.get('cpfCnpj') or '').strip()
        if not nome:
            continue

        nome_norm = _normalizar_nome_para_match(nome)
        if not nome_norm:
            continue

        tokens_nome = set(re.findall(r'[a-z0-9]+', nome_norm))
        match_found = any(token in tokens_nome for token in tokens_alvo)
        if debug:
            try:
                logger.info(f"[DESTINATARIOS][DEBUG] Comparando parte='{nome}' tokens_nome={list(tokens_nome)} match={match_found}")
            except Exception:
                pass

        if match_found:
            chave = (nome_norm, re.sub(r'\D', '', doc or ''))
            if chave in vistos:
                continue
            vistos.add(chave)
            destinatarios.append({
                'nome_oficial': nome,
                'nome_identificado': nome,
                'documento': doc,
                'documento_normalizado': re.sub(r'\D', '', doc or ''),
                'polo': 'reu'
            })
    return destinatarios


def _clicar_polo_passivo(driver, log):
    try:
        header = esperar_elemento(driver, '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]', timeout=10, by=By.XPATH)
        if not header:
            log('[DESTINATARIOS][ERRO] Header Polo Passivo não encontrado')
            return

        aria_expanded = (header.get_attribute('aria-expanded') or '').strip().lower()
        if aria_expanded == 'true':
            return

        click_headless_safe(driver, '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]', by=By.XPATH)

        # aguardar conteúdo do painel (preferir observer nativo)
        try:
            aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=5)
        except Exception:
            esperar_elemento(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', timeout=5, by=By.CSS_SELECTOR)
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao expandir Polo Passivo: {e}')


def _clicar_botao_polo_passivo(driver, log, qtd_cliques=1):
    try:
        for _ in range(qtd_cliques):
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                log('[DESTINATARIOS][ERRO] Botão polo passivo não clicável')
                return
            safe_click_no_scroll(driver, btn_polo_passivo, log=False)
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar no botão polo passivo (fallback): {e}')


def selecionar_destinatario_por_documento(driver, destinatario_info, debug=False, timeout=10, qtd_cliques=1):
    qtd_cliques = 2 if str(qtd_cliques).strip().lower() in ('2', '2x') else 1
    try:
        documento_alvo = None
        nome_alvo = None
        doc_normalizado = None
        if isinstance(destinatario_info, dict):
            documento_alvo = destinatario_info.get('documento') or destinatario_info.get('cpfcnpj') or destinatario_info.get('cpfCnpj')
            doc_normalizado = destinatario_info.get('documento_normalizado') or re.sub(r'\D', '', str(documento_alvo or ''))
            nome_alvo = (
                destinatario_info.get('nome_oficial')
                or destinatario_info.get('nome_identificado')
                or destinatario_info.get('nome')
            )

        doc_digits = re.sub(r'\D', '', doc_normalizado or documento_alvo or '')

        try:
            # Prefer observer to wait rows (fast)
            try:
                ok = aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=timeout)
            except Exception:
                ok = False
            if ok:
                linhas = driver.find_elements(By.CSS_SELECTOR, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row')
            if not linhas:
                esperar_elemento(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', timeout=timeout, by=By.CSS_SELECTOR)
                linhas = driver.find_elements(By.CSS_SELECTOR, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row')
        except Exception:
            linhas = driver.find_elements(By.CSS_SELECTOR, 'mat-row, .pec-partes-polo li, ul.sem-padding li')

        candidatos = []
        for linha in linhas:
            try:
                texto_linha = linha.text or ''
                texto_normalizado = re.sub(r'\D', '', texto_linha)
                if doc_digits and doc_digits in texto_normalizado:
                    candidatos.append((linha, texto_linha))
            except Exception:
                continue

        # tentativa por documento primeiro
        if candidatos:
            nome_alvo_norm = normalizar_string(nome_alvo) if nome_alvo else ''
            best = None
            best_score = -1
            for linha, texto_linha in candidatos:
                try:
                    score = 20
                    nome_span = None
                    try:
                        nome_span = linha.find_element(By.CSS_SELECTOR, '.nome-parte, .nome-tipo-parte, .pec-formatacao-padrao-dados-parte.nome-parte')
                    except Exception:
                        nome_span = None

                    if nome_span:
                        nome_linha = normalizar_string(nome_span.text or '')
                        if nome_alvo_norm and nome_linha == nome_alvo_norm:
                            score += 40
                        elif nome_alvo_norm and nome_alvo_norm in nome_linha:
                            score += 15
                    else:
                        if nome_alvo_norm and nome_alvo_norm in normalizar_string(texto_linha):
                            score += 10

                    try:
                        texto_norm = normalizar_string(texto_linha)
                        doc_pos = texto_norm.find(re.sub(r'\D', '', doc_digits)) if doc_digits else -1
                    except Exception:
                        doc_pos = -1
                    try:
                        nome_pos = texto_norm.find(nome_alvo_norm) if nome_alvo_norm else -1
                    except Exception:
                        nome_pos = -1
                    if doc_pos >= 0 and nome_pos >= 0 and abs(doc_pos - nome_pos) < 80:
                        score += 5

                    if 'advogado' in texto_linha.lower() and nome_alvo_norm and len(nome_alvo_norm.split()) >= 2:
                        score -= 2

                    if score > best_score:
                        best_score = score
                        best = linha
                except Exception:
                    continue

            if best is not None:
                # buscar botão de acrescentar dentro do row
                seletores_seta = [
                    'button[mattooltip*="acrescentar"]',
                    'button[aria-label*="acrescentar"]',
                    'button .fa-arrow-circle-down',
                    'button[mat-icon-button]',
                ]
                btn_seta = None
                for seletor in seletores_seta:
                    log_seletor_multiplo('[DESTINATARIOS]', seletor, 'TENTATIVA')
                    try:
                        btn_seta = best.find_element(By.CSS_SELECTOR, seletor)
                        log_seletor_multiplo('[DESTINATARIOS]', seletor, 'SUCESSO')
                        break
                    except Exception as e:
                        log_seletor_multiplo('[DESTINATARIOS]', seletor, 'FALHA', str(e))
                        continue
                if btn_seta:
                    try:
                        clickable = driver.execute_script("return (arguments[0].closest && arguments[0].closest('button')) || arguments[0];", btn_seta)
                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', clickable)
                        for _ in range(qtd_cliques):
                            safe_click_no_scroll(driver, clickable, log=False)
                    except Exception:
                        try:
                            for _ in range(qtd_cliques):
                                btn_seta.click()
                        except Exception:
                            pass
                    if debug:
                        logger.info(f"[DESTINATARIOS]  Parte selecionada via documento (melhor candidato): {documento_alvo}")
                    return {'status': 'ok', 'count': 1}

        # tentativa por nome
        if nome_alvo:
            nome_alvo_norm = normalizar_string(nome_alvo)
            for linha in linhas:
                try:
                    texto_linha = linha.text or ''
                    texto_norm = normalizar_string(texto_linha)
                    if nome_alvo_norm and (nome_alvo_norm in texto_norm or _partial_name_match(nome_alvo_norm, texto_norm)):
                        seletores_seta = [
                            'button[mattooltip*="acrescentar"]',
                            'button[aria-label*="acrescentar"]',
                            'button .fa-arrow-circle-down',
                            'button[mat-icon-button]'
                        ]
                        btn_seta = None
                        for seletor in seletores_seta:
                            log_seletor_multiplo('[DESTINATARIOS]', seletor, 'TENTATIVA')
                            try:
                                btn_seta = linha.find_element(By.CSS_SELECTOR, seletor)
                                log_seletor_multiplo('[DESTINATARIOS]', seletor, 'SUCESSO')
                                break
                            except Exception as e:
                                log_seletor_multiplo('[DESTINATARIOS]', seletor, 'FALHA', str(e))
                                continue
                        if btn_seta:
                            try:
                                clickable = driver.execute_script(
                                    "return (arguments[0].closest && arguments[0].closest('button')) || arguments[0];",
                                    btn_seta
                                )
                                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', clickable)
                                for _ in range(qtd_cliques):
                                    safe_click_no_scroll(driver, clickable, log=False)
                            except Exception:
                                try:
                                    for _ in range(qtd_cliques):
                                        btn_seta.click()
                                except Exception:
                                    pass
                            if debug:
                                try:
                                    logger.info(f"[DESTINATARIOS]  Parte selecionada via nome: {nome_alvo}")
                                except Exception:
                                    pass
                            return {'status': 'ok', 'count': 1}
                except Exception:
                    continue

        if debug:
            logger.info(f"[DESTINATARIOS][WARN] Não foi possível incluir parte: {nome_alvo or documento_alvo}")
        return {'status': 'empty', 'count': 0}
    except Exception as e:
        if debug:
            logger.info(f"[DESTINATARIOS][ERRO] {e}")
        return {'status': 'error', 'count': 0, 'details': str(e)}


def _selecionar_por_lista(driver, lista_destinatarios, origem_log, log, fallback_polo_passivo=False, qtd_seta_override=None, debug=False, qtd_cliques_fallback=1):
    selecionados = 0

    # 1. GARANTE ABERTURA DO PAINEL E AGUARDA O RENDER DO PJE (CRÍTICO)
    try:
        _clicar_polo_passivo(driver, log)
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao expandir Polo Passivo: {e}')

    qtd_cliques = qtd_seta_override if qtd_seta_override is not None else 1

    if not lista_destinatarios:
        log(f'[DESTINATARIOS][WARN] Lista de destinatários vazia ({origem_log})')
        if fallback_polo_passivo:
            _clicar_botao_polo_passivo(driver, log, qtd_cliques_fallback)
            log(f'[DESTINATARIOS] Fallback polo passivo aplicado ({qtd_cliques_fallback}x)')
            return {'status': 'fallback', 'count': 0}
        return {'status': 'empty', 'count': 0}

    for dest in lista_destinatarios:
        info_padrao = dest
        if isinstance(dest, dict):
            nome = dest.get('nome') or dest.get('nome_oficial') or dest.get('nome_identificado')
            doc = dest.get('cpfcnpj') or dest.get('cpfCnpj') or dest.get('documento')
            info_padrao = {
                'nome_alvo': nome,
                'nome_oficial': nome,
                'documento': doc,
                'documento_normalizado': re.sub(r'\D', '', str(doc)) if doc else ''
            }

        try:
            res = selecionar_destinatario_por_documento(driver, info_padrao, debug=debug, qtd_cliques=qtd_cliques)
            if isinstance(res, dict) and res.get('status') == 'ok':
                selecionados += int(res.get('count', 1) or 1)
            elif res is True:
                selecionados += 1
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Exceção ao tentar selecionar {info_padrao.get("nome_alvo")} : {e}')

    if selecionados == 0:
        log(f'[DESTINATARIOS][WARN] Nenhum destinatário selecionado ({origem_log})')
        if fallback_polo_passivo:
            _clicar_botao_polo_passivo(driver, log, qtd_cliques_fallback)
            log(f'[DESTINATARIOS] Fallback polo passivo aplicado ({qtd_cliques_fallback}x) (botão geral)')
            return {'status': 'fallback', 'count': 0}
        return {'status': 'empty', 'count': 0}
    else:
        log(f'[DESTINATARIOS] {selecionados} destinatário(s) selecionado(s) via {origem_log}')
        return {'status': 'ok', 'count': selecionados}


def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)
            return _selecionar_por_lista(driver, candidatos, 'observação', log, fallback_polo_passivo=True, qtd_seta_override=qtd_informado, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            click_headless_safe(
                driver,
                'i.fa.fa-user.pec-polo-ativo-partes-processo.pec-botao-intimar-polo-partes-processo',
                by=By.CSS_SELECTOR
            )
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                safe_click_no_scroll(driver, btn_polo_passivo, log=False)
                if i < cliques - 1:
                    esperar_elemento(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=3, by=By.CSS_SELECTOR)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            try:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
            except Exception:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo'))
                )
            driver.execute_script("arguments[0].click();", btn_terceiro)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: primeiro do Polo Passivo')
        try:
            click_headless_safe(driver, '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]', by=By.XPATH)
            aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=5)
            click_headless_safe(driver, '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]//button[@aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações.'][1]', by=By.XPATH)
            log('[DESTINATARIOS] Primeira seta clicada')
            return ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo primeiro: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        safe_click_no_scroll(driver, btn_polo_passivo, log=False)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})
```

# atos/comunicacao_coleta.py

```python
import time
import re
from typing import Any


def executar_coleta_conteudo(driver, config_coleta, debug=False) -> bool:
    """Executa a coleta de conteúdo parametrizável usada pela comunicação orquestrada.
    Retorna True se a coleta teve sucesso (ou link obtido), False caso contrário.
    """
    try:
        # Normaliza config para dict
        if isinstance(config_coleta, str):
            config = {'tipo': config_coleta}
        else:
            config = config_coleta or {}

        tipo_coleta = config.get('tipo', '')
        parametros = config.get('parametros', None)

        # Extrair número do processo via PEC.anexos se disponível
        numero_processo = None
        try:
            from PEC.anexos import extrair_numero_processo_da_url
            numero_processo = extrair_numero_processo_da_url(driver)
            if not numero_processo:
                numero_processo = "PROCESSO_DESCONHECIDO"
        except Exception:
            numero_processo = "PROCESSO_DESCONHECIDO"

        sucesso_coleta = False
        if tipo_coleta and tipo_coleta.lower() in ('link_ato', 'link_ato_validacao', 'link_ato_timeline'):
            # Tenta API via Fix.variaveis
            try:
                from Fix.variaveis import session_from_driver, PjeApiClient, obter_chave_ultimo_despacho_decisao_sentenca
                sess_tmp, trt_tmp = session_from_driver(driver)
                client_tmp = PjeApiClient(sess_tmp, trt_tmp)
                link_validacao = obter_chave_ultimo_despacho_decisao_sentenca(client_tmp, str(numero_processo), driver=driver)
            except Exception:
                link_validacao = None

            if link_validacao:
                try:
                    if not str(link_validacao).lower().startswith('http'):
                        base = trt_tmp
                        if not base.startswith('http'):
                            base = 'https://' + base
                        link_validacao = f"{base}/pjekz/validacao/{link_validacao}?instancia=1"
                    from PEC.anexos import salvar_conteudo_clipboard
                    sucesso_coleta = salvar_conteudo_clipboard(conteudo=link_validacao, numero_processo=str(numero_processo), tipo_conteudo=f"link_ato_validacao", debug=debug)
                    if sucesso_coleta:
                        return True
                    else:
                        return True
                except Exception:
                    sucesso_coleta = True

            # Fallback DOM/timeline
            try:
                from Prazo.p2b_fluxo_helpers import _encontrar_documento_relevante
                doc_encontrado, doc_link, doc_idx = _encontrar_documento_relevante(driver)
                if doc_link:
                    try:
                        driver.execute_script('arguments[0].scrollIntoView(true);', doc_link)
                        time.sleep(0.5)
                        driver.execute_script('arguments[0].click();', doc_link)
                        time.sleep(1)
                    except Exception:
                        pass
                    try:
                        link_validacao_dom = driver.execute_script("""
                            var spans = document.querySelectorAll('div[style="display: block;"] span');
                            for (var i = 0; i < spans.length; i++) {
                                var text = spans[i].textContent.trim();
                                if (text.includes('Número do documento:')) {
                                    var numero = text.split('Número do documento:')[1].trim();
                                    if (numero) {
                                        return 'https://pje.trt2.jus.br/pjekz/validacao/' + numero + '?instancia=1';
                                    }
                                }
                            }
                            var links = document.querySelectorAll('a[href*="validacao"]');
                            for (var i = 0; i < links.length; i++) {
                                var href = links[i].getAttribute('href');
                                if (href && href.includes('/validacao/')) {
                                    return href;
                                }
                            }
                            return null;
                        """)
                    except Exception:
                        link_validacao_dom = None

                    if link_validacao_dom:
                        try:
                            from PEC.anexos import salvar_conteudo_clipboard
                            sucesso_coleta = salvar_conteudo_clipboard(conteudo=link_validacao_dom, numero_processo=str(numero_processo), tipo_conteudo=f"link_ato_validacao", debug=debug)
                            if sucesso_coleta:
                                return True
                        except Exception:
                            return True
                    else:
                        sucesso_coleta = False
                else:
                    sucesso_coleta = False
            except Exception:
                sucesso_coleta = False

        if not sucesso_coleta:
            try:
                from Fix.utils import executar_coleta_parametrizavel
                sucesso_coleta = executar_coleta_parametrizavel(driver, numero_processo, tipo_coleta, parametros, debug)
            except Exception:
                sucesso_coleta = False

        return bool(sucesso_coleta)
    except Exception:
        return False
```

# atos/comunicacao_navigation.py

```python
import time
import re
from selenium.webdriver.common.by import By
from Fix.log import getmodulelogger
logger = getmodulelogger(__name__)

from Fix.core import aguardar_renderizacao_nativa, esperar_url_conter
from .core import aguardar_e_verificar_aba, aguardar_e_clicar


def abrir_minutas(driver, debug=False):
    """Tenta navegação direta para a página de minutas; faz fallback para navegação por cliques.
    Retorna True se a tela de minutas estiver pronta, levanta Exception em erro crítico.
    """
    try:
        current_url = driver.current_url
        if debug:
            logger.info(f'[URL] URL atual: {current_url}')

        if '/comunicacoesprocessuais/minutas' in current_url:
            if debug:
                logger.info('[URL] Já está na página de minutas; pulando redirecionamento.')
            return True

        match = re.search(r'/processo/(\d+)/detalhe', current_url)
        if not match:
            raise Exception('ID do processo não encontrado na URL /detalhe')

        processo_id = match.group(1)
        url_minutas = f'https://pje.trt2.jus.br/pjekz/processo/{processo_id}/comunicacoesprocessuais/minutas'
        if debug:
            logger.info(f'[URL] Abrindo URL de minutas: {url_minutas}')

        abas_antes = driver.window_handles
        driver.execute_script(f"window.open('{url_minutas}', '_blank');")

        nova_aba = None
        for tentativa in range(15):
            abas_apos_abertura = driver.window_handles
            if len(abas_apos_abertura) > len(abas_antes):
                nova_aba = abas_apos_abertura[-1]
                break
            else:
                # Usar aguardar_renderizacao_nativa ao invés de time.sleep hardcoded
                try:
                    aguardar_renderizacao_nativa(driver, timeout=0.5)
                except Exception:
                    pass

        if not nova_aba:
            raise Exception('Nova aba de minutas não abriu')

        driver.switch_to.window(nova_aba)
        driver.execute_script("window.focus();")

        if not aguardar_e_verificar_aba(driver, timeout_spinner=0.5, max_tentativas_reload=2, log=debug):
            raise Exception('Página travou no carregamento (spinner)')

        if not esperar_url_conter(driver, '/minutas', timeout=20):
            raise Exception('URL de minutas não carregou')

        # Quick check: if 'Tipo de Expediente' (ou botões suficientes) não aparecer em 3s, refresh na aba e tentar novamente
        if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 3):
            logger.info('[MINUTAS] Elemento esperado não encontrado rápido; recarregando aba e tentando novamente')
            try:
                driver.refresh()
            except Exception as e_ref:
                logger.info(f'[MINUTAS] Falha ao refresh da aba: {e_ref}')
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('Página de minutas não exibiu conteúdo esperado após refresh')
        return True

    except Exception as url_error:
        if debug:
            logger.info(f'[URL][ERRO] Falha na navegação direta por URL: {url_error}')
            logger.info('[URL] Fazendo fallback para navegação tradicional por cliques...')

        # FALLBACK: Navegação tradicional por cliques
        from Fix.selectors_pje import BTN_TAREFA_PROCESSO

        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            raise Exception('Botão tarefa do processo não encontrado')

        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            else:
                # Usar aguardar_renderizacao_nativa ao invés de time.sleep hardcoded
                try:
                    aguardar_renderizacao_nativa(driver, timeout=0.5)
                except Exception:
                    pass

        if nova_aba:
            driver.switch_to.window(nova_aba)
            if not aguardar_e_verificar_aba(driver, timeout_spinner=0.5, max_tentativas_reload=2, log=debug):
                raise Exception('Página travou no carregamento (spinner)')

        if not esperar_url_conter(driver, '/minutas', timeout=20):
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('URL e conteúdo de minutas não carregaram')
        # Quick refresh attempt if UI parts not present shortly after load
        if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 3):
            logger.info('[MINUTAS][FALLBACK] Elemento esperado não encontrado rápido; recarregando aba e tentando novamente')
            try:
                driver.refresh()
            except Exception as e_ref2:
                logger.info(f'[MINUTAS][FALLBACK] Falha ao refresh da aba: {e_ref2}')
            if not aguardar_renderizacao_nativa(driver, 'pje-tipo-expediente, [aria-label*="Tipo de Expediente"], button', 'aparecer', 20):
                raise Exception('Página de minutas não exibiu conteúdo esperado após refresh')
        if debug:
            logger.info('[MINUTAS] Tela de minutas carregada com sucesso')
        return True
```
