# atos.py
from Fix import (
    login_pc,
    safe_click,
    esperar_elemento,
    criar_gigs,
    aplicar_filtro_100,
    limpar_temp_selenium,
    buscar_seletor_robusto,
    preencher_campos_prazo,
    # Funções adicionadas para corrigir erros
    esperar_url_conter,
    tratar_anexos_infojud_irpf_doi_sisbajud,
    selecionar_tipo_expediente,
    buscar_documentos_sequenciais
)
from modulo import aplicar_filtro_100
from selenium.webdriver.common.keys import Keys
import os
import logging
import time
from selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

# ====================================================
# BLOCO 1 - ATOS JUDICIAIS PADRÃO (Wrappers)
# ====================================================
def fluxo_cls(driver, conclusao_tipo, forcar_iniciar_execucao=False):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    """
    Refatorado fluxo geral para CLS (movimentação de minuta):
    1. Clica no botão 'Abrir tarefa do processo' (seletor robusto mattooltip).
    2. Verifica se a URL contém '/transicao'.
    3. Clica no ícone .fa-clipboard-check (Conclusão ao Magistrado).
    4. Verifica se a URL contém '/conclusao'.
    5. Clica no botão do tipo de conclusão especificado.
    Retorna True em caso de sucesso, False em caso de falha.
    """
    print(f'[CLS] Iniciando fluxo de CLS para tipo: {conclusao_tipo}...')
    try:
        # 1. Clica no botão 'Abrir tarefa do processo' usando seletor padronizado
        from Fix import esperar_elemento, safe_click
        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            print('[CLS][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
            return False
        safe_click(driver, btn_abrir_tarefa)
        print('[CLS] Botão "Abrir tarefa do processo" clicado.')
        # Troca para nova aba, se aberta, e espera carregamento completo
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        if nova_aba:
            driver.switch_to.window(nova_aba)
            print('[CLS] Foco trocado para nova aba da tarefa do processo.')
            # Espera carregamento completo da nova aba (aguarda body presente e pelo menos um botão visível)
            try:
                WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.TAG_NAME, 'button')) > 0)
                print('[CLS] Nova aba carregada completamente.')
            except Exception as e:
                print(f'[CLS][WARN] Timeout esperando carregamento completo da nova aba: {e}')
        else:
            print('[CLS][WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # 2. Não precisa aguardar URL /transicao, pois já estará nela

        # 0. (Ajuste para ato_pesquisas) Tenta clicar em "Iniciar execução" antes de seguir para conclusão ao magistrado
        if forcar_iniciar_execucao:
            try:
                xpath_iniciar = "//button[.//div[contains(@class, 'texto-botao-app') and contains(normalize-space(), 'Iniciar execução')]]"
                btn_iniciar = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_iniciar))
                )
                driver.execute_script("arguments[0].click();", btn_iniciar)
                print('[CLS][DEBUG] Clique em "Iniciar execução" realizado.')
                time.sleep(1)
            except Exception as e:
                print(f'[CLS][INFO] Botão "Iniciar execução" não encontrado ou não clicável: {e}')

        # 3. Clica no botão 'Conclusão ao Magistrado' de forma robusta
        btn_conclusao = None
        seletor_usado = None
        try:
            xpath_btn = "//button[.//div[contains(@class, 'texto-botao-app') and contains(normalize-space(), 'Conclusão ao magistrado')]]"
            btn_conclusao = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_btn))
            )
            driver.execute_script("arguments[0].click();", btn_conclusao)
            seletor_usado = xpath_btn
            print(f'[CLS][DEBUG] Clique JS no botão Conclusão ao magistrado realizado. Seletor usado: {xpath_btn}')
        except Exception as e1:
            print(f'[CLS][WARN] Falha ao clicar via JS no botão pelo texto: {e1}')
            try:
                btn_icon = esperar_elemento(driver, '.fa-clipboard-check', timeout=10)
                if btn_icon:
                    btn_pai = btn_icon.find_element(By.XPATH, './ancestor::button[1]')
                    driver.execute_script("arguments[0].click();", btn_pai)
                    seletor_usado = '.fa-clipboard-check > button'
                    print(f'[CLS][DEBUG] Clique JS no botão pai do ícone realizado. Seletor usado: .fa-clipboard-check > button')
                else:
                    print('[CLS][ERRO] Ícone .fa-clipboard-check não encontrado!')
                    return False
            except Exception as e2:
                print(f'[CLS][ERRO] Falha ao clicar no botão pai do ícone: {e2}')
                return False
        time.sleep(1)
        print(f'[CLS][DEBUG] Seletor de clique usado para conclusão: {seletor_usado}')

        # 4. Aguarda a URL mudar para /conclusao
        from Fix import esperar_url_conter
        if not esperar_url_conter(driver, '/conclusao', timeout=15):
            print(f'[CLS][ERRO] URL inesperada após clicar em conclusão: {driver.current_url}')
            return False

        # 5. Clica no botão do tipo de conclusão
        print(f'[CLS] Procurando botão de conclusão: {conclusao_tipo}')
        btn_tipo_conclusao = None
        try:
            # Busca dentro do componente pje-concluso-tarefa-botao pelo texto do tipo de conclusão
            xpath_conclusao = f"//pje-concluso-tarefa-botao//button[contains(translate(normalize-space(), 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), translate('{conclusao_tipo}', 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'))]"
            time.sleep(0.5)  # Aguarda meio segundo antes do clique, para garantir renderização
            btn_tipo_conclusao = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, xpath_conclusao))
            )
            safe_click(driver, btn_tipo_conclusao)
            print(f'[CLS] Botão de conclusão "{conclusao_tipo}" (pje-concluso-tarefa-botao) clicado.')
        except Exception as e:
            print(f'[CLS][WARN] Botão de conclusão robusto não encontrado: {e}')
            # Fallbacks
            btn_tipo_conclusao = buscar_seletor_robusto(driver, [conclusao_tipo], timeout=8)
            if not btn_tipo_conclusao:
                xpath_selector = f"//button[contains(., '{conclusao_tipo}')] | //button/span[contains(., '{conclusao_tipo}')]/.."
                try:
                    btn_tipo_conclusao = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_selector))
                    )
                except Exception:
                    print(f'[CLS][ERRO] Botão de conclusão "{conclusao_tipo}" não encontrado (nem via texto/XPath)!')
                    return False
            safe_click(driver, btn_tipo_conclusao)
            print(f'[CLS] Botão de conclusão "{conclusao_tipo}" (fallback) clicado.')
        time.sleep(1)

        # 6. Aguarda a URL mudar para /minutar
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            print(f'[CLS][ERRO] URL inesperada após clicar em conclusão tipo: {driver.current_url}')
            return False

        # Clique e foco no campo de filtro de modelos ao entrar em /minutar
        try:
            campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
            if not campo_filtro_modelo.is_displayed() or not campo_filtro_modelo.is_enabled():
                print('[CLS][MODELO][ERRO] Campo de filtro de modelos não está visível/habilitado!')
                return False
            driver.execute_script("arguments[0].focus();", campo_filtro_modelo)
            driver.execute_script("arguments[0].click();", campo_filtro_modelo)
            print('[CLS][MODELO][OK] Clique e foco no campo de filtro de modelos realizado (padrão MaisPje).')
            time.sleep(0.3)
        except Exception as e:
            print(f'[CLS][MODELO][ERRO] Falha ao clicar/focar no campo de filtro de modelos: {e}')
            return False

        print('[CLS] Fluxo de CLS finalizado com sucesso.')
        return True
    except Exception as e:
        print(f'[CLS][ERRO] Falha no fluxo de CLS: {e}')
        try:
            driver.save_screenshot(f'erro_fluxo_cls_{conclusao_tipo}.png')
        except Exception as screen_err:
            print(f'[CLS][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        return False # Indicate failure


def ato_judicial(
    driver,
    conclusao_tipo=None,
    modelo_nome=None,
    prazo=None,
    marcar_pec=None,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=None,
    debug=False,
    sigilo=None,
    descricao=None,  # NOVO: parâmetro para descrição
    **kwargs
):
    """
    Fluxo generalizado para qualquer ato judicial, seguindo a ordem:
    1. Descrição (NOVO)
    2. Sigilo
    3. PEC
    4. Prazo
    5. Movimento
    6. GIGS
    7. Fechar aba
    8. Função extra de sigilo (se necessário)
    """
    try:
        # 1. Executa fluxo_cls até o clique/foco no campo de modelo
        if debug: print(f'[ATO] Executando fluxo_cls para {conclusao_tipo}...')
        if not fluxo_cls(driver, conclusao_tipo):
            print(f'[ATO][ERRO] Falha no fluxo_cls para {conclusao_tipo}.')
            return False

        # 2. Digitação do modelo e prosseguimento (padrão MaisPje)
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro_modelo.clear()
        campo_filtro_modelo.send_keys(modelo_nome)
        campo_filtro_modelo.send_keys(Keys.ENTER)
        print(f'[ATO][MODELO][OK] Modelo "{modelo_nome}" digitado e ENTER pressionado no filtro.')
        # Seleciona o modelo filtrado destacado (fundo amarelo)
        seletor_item_filtrado = '.nodo-filtrado'
        nodo = esperar_elemento(driver, seletor_item_filtrado, timeout=15)
        if not nodo:
            print('[ATO][ERRO] Nodo do modelo não encontrado!')
            return False
        safe_click(driver, nodo)
        print('[ATO] Clique em nodo-filtrado realizado!')
        # Aguarda a caixa de visualização do modelo carregar
        seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
        btn_inserir = esperar_elemento(driver, seletor_btn_inserir, timeout=15)
        if not btn_inserir:
            print('[ATO][ERRO] Botão de inserir modelo não encontrado!')
            return False
        time.sleep(0.6)
        # Pressiona e solta ESPAÇO para inserir o modelo (padrão MaisPje)
        try:
            btn_inserir.send_keys(Keys.SPACE)
            print('[ATO] Modelo inserido pressionando ESPAÇO no botão Inserir (padrão MaisPje).')
        except Exception as e:
            print(f'[ATO][ERRO] Falha ao pressionar ESPAÇO para inserir modelo: {e}')
            return False

        # NOVO: Clica no botão Salvar (mat-raised-button mat-primary) e aguarda 1s para ativar aba de prazos
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            btn_salvar = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-raised-button') and contains(@class, 'mat-primary') and contains(., 'Salvar') and @aria-label='Salvar']"))
            )
            safe_click(driver, btn_salvar)
            print('[ATO] Clique no botão Salvar realizado!')
            time.sleep(1)
        except Exception as e:
            print(f'[ATO][ERRO] Botão Salvar não encontrado ou não clicável: {e}')
            return False

        # LOGS DETALHADOS DE FLUXO
        print(f'[ATO][DEBUG] Iniciando etapas pós-Salvar: Sigilo → PEC → Prazo → Movimento → GIGS → Fechar aba → Função extra de sigilo')
        # 1. Sigilo (apenas ativa se explicitamente solicitado)
        sigilo_ativado = False
        print('[ATO][DEBUG] Etapa: Sigilo')
        try:
            sigilo_input = driver.find_element(By.CSS_SELECTOR, 'input.mat-slide-toggle-input[name="sigiloso"]')
            checked = sigilo_input.get_attribute('aria-checked') == 'true' or sigilo_input.is_selected()
            if str(sigilo).lower() in ("sim", "true", "1") and not checked:
                driver.execute_script("arguments[0].click();", sigilo_input)
                sigilo_ativado = True
                print('[ATO][SIGILO][DEBUG] Sigilo ativado por solicitação explícita.')
            else:
                print(f'[ATO][SIGILO][DEBUG] Sigilo não solicitado ou já ativado. Nenhuma ação.')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível ajustar Sigilo: {e}')

        # 2. PEC
        print('[ATO][DEBUG] Etapa: PEC')
        if marcar_pec is not None:
            try:
                pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label*="PEC"]')
                checked = pec_checkbox.get_attribute('aria-checked') == 'true' or pec_checkbox.is_selected()
                print(f'[ATO][PEC][DEBUG] Estado atual da caixa PEC: {"marcada" if checked else "desmarcada"}. Parâmetro marcar_pec: {marcar_pec}')
                if marcar_pec and not checked:
                    driver.execute_script("arguments[0].click();", pec_checkbox)
                    print('[ATO][PEC][DEBUG] Caixa PEC estava desmarcada e foi marcada.')
                elif not marcar_pec and checked:
                    driver.execute_script("arguments[0].click();", pec_checkbox)
                    print('[ATO][PEC][DEBUG] Caixa PEC estava marcada e foi desmarcada.')
                else:
                    print('[ATO][PEC][DEBUG] Nenhuma ação necessária na caixa PEC.')
            except Exception as e:
                print(f'[ATO][ERRO] Não foi possível ajustar PEC: {e}')

        # 3. Prazo
        print('[ATO][DEBUG] Etapa: Prazo')
        try:
            print('[ATO][PRAZO][DEBUG] Chamando preencher_prazos_destinatarios...')
            preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario)
        except Exception as e:
            print(f'[ATO][PRAZO][ERRO] Falha inesperada ao preencher prazos: {e}')
            return False

        # 4. Movimento
        print('[ATO][DEBUG] Etapa: Movimento')
        if movimento:
            try:
                js_mov = f'''
                (function() {{
                    // Ativa a aba "Movimentos"
                    var tentativas = 0, abaMov = null;
                    while (tentativas < 3 && !abaMov) {{
                        var abas = Array.from(document.querySelectorAll('.mat-tab-label'));
                        abaMov = abas.find(a => a.textContent && a.textContent.normalize('NFD').replace(/[^\w\s]/g, '').toLowerCase().includes('movimentos'));
                        if (abaMov && abaMov.getAttribute('aria-selected') !== 'true') {{
                            abaMov.click();
                            break;
                        }}
                        tentativas++;
                    }}
                    setTimeout(function() {{
                        var textoMov = '{movimento}'.trim().toLowerCase().replace(/\s+/g, ' ');
                        var checkboxes = Array.from(document.querySelectorAll('mat-checkbox.mat-checkbox.movimento'));
                        var selecionado = false;
                        for (var cb of checkboxes) {{
                            try {{
                                var label = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                var labelNorm = label && label.textContent ? label.textContent.trim().toLowerCase().replace(/\s+/g, ' ') : '';
                                if (labelNorm.includes(textoMov)) {{
                                    var input = cb.querySelector('input[type="checkbox"]');
                                    if (input && !input.checked) input.click();
                                    selecionado = true;
                                    break;
                                }}
                            }} catch (e) {{}}
                        }}
                        if (!selecionado) {{
                            var allLabels = Array.from(document.querySelectorAll('.mat-checkbox-label'));
                            for (var labelEl of allLabels) {{
                                var labelText = labelEl.textContent.trim().toLowerCase().replace(/\s+/g, ' ');
                                if (labelText.includes(textoMov)) {{
                                    var cbInput = labelEl.parentElement && labelEl.parentElement.parentElement ? labelEl.parentElement.parentElement.querySelector('input[type="checkbox"]') : null;
                                    if (cbInput && !cbInput.checked) cbInput.click();
                                    break;
                                }}
                            }}
                        }}
                    }}, 700);
                }})();
                '''
                driver.execute_script(js_mov)
                print(f'[ATO][MOVIMENTO][OK] JS robusto executado para selecionar movimento: {movimento}')
                time.sleep(0.5)
                # Clica no botão Gravar dos movimentos
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                btn_gravar_mov = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Gravar os movimentos') and contains(@class, 'mat-raised-button') and contains(., 'Gravar')]"))
                )
                print('[ATO][MOVIMENTO][LOG] Botão Gravar dos movimentos localizado, clicando...')
                btn_gravar_mov.click()
                print('[ATO][MOVIMENTO][OK] Botão Gravar dos movimentos clicado.')
                time.sleep(1)
                # Aguarda o modal de confirmação e clica explicitamente no botão "Sim"
                try:
                    btn_sim = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//mat-dialog-container//button[.//span[normalize-space(text())='Sim'] and contains(@class, 'mat-primary') and contains(@class, 'mat-button') and contains(@class, 'mat-focus-indicator') ]"))
                    )
                    btn_sim.click()
                    print('[ATO][MOVIMENTO][OK] Botão "Sim" do modal de confirmação clicado.')
                    time.sleep(1)
                except Exception as e:
                    print(f'[ATO][MOVIMENTO][ERRO] Não foi possível clicar no botão "Sim" do modal: {e}')
                    return False
                # Clica no botão Salvar
                btn_salvar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Salvar') and contains(@class, 'mat-raised-button') and contains(., 'Salvar')]"))
                )
                print('[ATO][MOVIMENTO][LOG] Botão Salvar localizado, clicando...')
                btn_salvar.click()
                print('[ATO][MOVIMENTO][OK] Botão Salvar clicado.')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][MOVIMENTO][ERRO] Falha ao executar etapa de movimento: {e}')
                return False

        # 5. GIGS (minuta)
        print('[ATO][DEBUG] Etapa: GIGS')
        if gigs:
            try:
                # Garante que o parâmetro 'tela' seja 'minuta' se a URL contiver '/minutar'
                gigs_args = dict(gigs) if isinstance(gigs, dict) else {}
                if '/minutar' in driver.current_url:
                    gigs_args['tela'] = 'minuta'
                resultado_gigs = criar_gigs(driver, **gigs_args)
                if not resultado_gigs:
                    print('[ATO][ERRO] Falha ao criar GIGS (minuta): criar_gigs retornou False.')
                    return False
                print('[ATO] GIGS (minuta) criado com sucesso na etapa final.')
            except Exception as e:
                print(f'[ATO][ERRO] Falha ao criar GIGS (minuta): {e}')
                return False

        # 6. Fechar aba da minuta
        print('[ATO][DEBUG] Etapa: Fechar aba')
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                print('[ATO] Aba da minuta fechada e foco retornado para aba principal.')
        except Exception as e:
            print(f'[ATO][ERRO] Falha ao fechar aba da minuta: {e}')

        # 7. Função extra de sigilo (se ativado)
        print('[ATO][DEBUG] Etapa: Função extra de sigilo')
        if sigilo_ativado:
            try:
                from Fix import visibilidade_sigilosos
                visibilidade_sigilosos(driver, log=debug)
                print('[ATO] Fluxo extra de visibilidade sigilosa executado.')
            except Exception as e:
                print(f'[ATO][ERRO] Falha no fluxo extra de sigilo: {e}')

        print(f'[ATO] Fluxo de ato judicial ({conclusao_tipo}, {modelo_nome}) finalizado com sucesso.')
        return True

    except Exception as e:
        print(f'[ATO][ERRO] Falha no fluxo do ato judicial ({conclusao_tipo}, {modelo_nome}): {e}')
        try:
            driver.save_screenshot(f'erro_ato_{conclusao_tipo}_{modelo_nome}.png')
        except Exception as screen_err:
            print(f'[ATO][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        return False

def make_ato_wrapper(conclusao_tipo, modelo_nome, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None):
    def wrapper(driver, debug=False, sigilo=None, movimento_=None, descricao=None):
        return ato_judicial(
            driver,
            conclusao_tipo=conclusao_tipo,
            modelo_nome=modelo_nome,
            prazo=prazo,
            marcar_pec=marcar_pec,
            movimento=movimento_ if movimento_ is not None else movimento,
            gigs=gigs,
            marcar_primeiro_destinatario=marcar_primeiro_destinatario,
            debug=debug,
            sigilo=sigilo,
            descricao=descricao
        )
    return wrapper

# Wrappers gerados automaticamente
ato_meios = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='xsmeios',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=True
)

ato_crda = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='a reclda',
    prazo=15,
    marcar_pec=False,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=False
)

ato_crte = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='xreit',
    prazo=15,
    marcar_pec=False,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=False
)

ato_bloq = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='xsparcial',
    prazo=None,
    marcar_pec=True,
    movimento=None,
    gigs={'dias_uteis': 1, 'observacao': 'pec bloq'},
    marcar_primeiro_destinatario=False
)

ato_idpj = make_ato_wrapper(
    conclusao_tipo='IDPJ',
    modelo_nome='pjsem',
    prazo=8,
    marcar_pec=True,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=False
)

ato_termoE = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='xempre',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=True
)

ato_termoS = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='xsocio',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=True
)

ato_edital = make_ato_wrapper(
    conclusao_tipo='despacho',
    modelo_nome='xsedit',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=True
)

ato_sobrestamento = make_ato_wrapper(
    conclusao_tipo='/ Susp',
    modelo_nome='suspf',
    prazo=0,
    marcar_pec=False,
    movimento='frustrada',
    gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
    marcar_primeiro_destinatario=False
)

# ato_pesquisas permanece manual, pois tem lógica própria
def ato_pesquisas(driver, conclusao_tipo=None, modelo_nome=None, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, debug=False, sigilo=True, descricao=None):
    return ato_judicial(
        driver=driver,
        conclusao_tipo=conclusao_tipo or 'BNDT',
        modelo_nome=modelo_nome or 'xsbacen',
        prazo=prazo if prazo is not None else 30,
        marcar_pec=marcar_pec if marcar_pec is not None else True,
        movimento=movimento or 'bloqueio',
        gigs=gigs if gigs is not None else {'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=marcar_primeiro_destinatario if marcar_primeiro_destinatario is not None else True,
        debug=debug,
        sigilo=sigilo,
        descricao=descricao
    )

# ====================================================
# BLOCO 2 - COMUNICAÇÕES PROCESSUAIS (Wrappers + Regra Geral)
# ====================================================

# Definição da regra geral de comunicação processual
def comunicacao_judicial(
    driver,
    tipo_expediente,
    prazo,
    nome_comunicacao,
    sigilo,
    modelo_nome,
    gigs_extra=None,
    debug=False
):
    """
    Fluxo generalizado para qualquer comunicação processual.
    """
    def log(msg):
        print(f'[COMUNICACAO] {msg}')
        if debug:
            time.sleep(0.5)
    try:
        # FLUXO INICIAL ROBUSTO: abrir tarefa do processo igual ao fluxo_cls
        from Fix import esperar_elemento, safe_click
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selectors_pje import BTN_TAREFA_PROCESSO
        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            log('[ERRO CRÍTICO] Botão "Abrir tarefa do processo" não encontrado!')
            raise Exception('Botão tarefa do processo não encontrado')
        safe_click(driver, btn_abrir_tarefa)
        log('Botão "Abrir tarefa do processo" clicado.')
        # Troca para nova aba, se aberta, e espera carregamento completo
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        if nova_aba:
            driver.switch_to.window(nova_aba)
            log('Foco trocado para nova aba da tarefa do processo.')
            try:
                WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.TAG_NAME, 'button')) > 0)
                log('Nova aba carregada completamente.')
            except Exception as e:
                log(f'[WARN] Timeout esperando carregamento completo da nova aba: {e}')
        else:
            log('[WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # 2. Confirmar URL terminada em /transicao
        WebDriverWait(driver, 15).until(lambda d: d.current_url.endswith('/transicao'))
        log('URL de transição confirmada.')
        # 3. Clicar no botão de Comunicações e expedientes (fa-envelope)
        def buscar_btn_comunic():
            # Busca por texto, aria-label, mattooltip, ou ícone fa-envelope
            try:
                # 1. Por texto visível
                btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'comunicacoes e expedientes')]]")
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        return btn
                # 2. Por aria-label/mattooltip
                btns = driver.find_elements(By.CSS_SELECTOR, '*[aria-label*="Comunica"]')
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        return btn
                btns = driver.find_elements(By.CSS_SELECTOR, '*[mattooltip*="Comunica"]')
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        return btn
                # 3. Por ícone fa-envelope
                icons = driver.find_elements(By.CSS_SELECTOR, 'i.fa-envelope')
                for icon in icons:
                    try:
                        btn = icon.find_element(By.XPATH, './ancestor::button[1]')
                        if btn.is_displayed() and btn.is_enabled():
                            return btn
                    except Exception:
                        continue
            except Exception:
                pass
            return None

        btn_comunic = buscar_btn_comunic()
        if not btn_comunic:
            # Tenta clicar em "Análise" e tenta de novo
            log('[INFO] Botão Comunicações e expedientes não encontrado. Tentando clicar em "Análise" e tentar novamente...')
            try:
                btn_analise = None
                # Busca botão Análise por texto
                btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'analise')]]")
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_analise = btn
                        break
                if not btn_analise:
                    # Busca por aria-label/mattooltip
                    btns = driver.find_elements(By.CSS_SELECTOR, '*[aria-label*="Análise"]')
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_analise = btn
                            break
                    btns = driver.find_elements(By.CSS_SELECTOR, '*[mattooltip*="Análise"]')
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_analise = btn
                            break
                if btn_analise:
                    safe_click(driver, btn_analise)
                    log('Botão "Análise" clicado para habilitar botões.')
                    time.sleep(1.2)
                else:
                    log('[WARN] Botão "Análise" não encontrado para workaround.')
            except Exception as e:
                log(f'[WARN] Erro ao tentar clicar em "Análise": {e}')
            # Tenta novamente buscar o botão de comunicações
            btn_comunic = buscar_btn_comunic()
        if not btn_comunic:
            log('[ERRO] Botão de Comunicações e expedientes (fa-envelope) não encontrado mesmo após workaround!')
            raise Exception('Botão Comunicações e expedientes não encontrado')
        safe_click(driver, btn_comunic)
        log('Botão de Comunicações e expedientes clicado.')
        # 4. Aguardar carregamento da nova URL (aguarda mudança de URL ou modal)
        try:
            log('[DEBUG] Aguardando mudança de URL para minutas OU possível modal de lote...')
            for i in range(30):
                if '/comunicacoesprocessuais/minutas' in driver.current_url:
                    log('[DEBUG] URL de minutas detectada.')
                    break
                # Verifica se há modal de lote aberto
                modais = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container, .cdk-overlay-container .mat-dialog-container')
                if modais:
                    log('[DEBUG] Modal de lote detectado após clique em expediente. Aguardando interação manual ou automatize se necessário.')
                    # Opcional: pode tentar clicar em botão "OK" ou "Confirmar" do modal, se desejado
                    botoes_ok = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'ok') or contains(translate(., 'ÁÀÂÃÉÈÊÍÏÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'confirmar')]]")
                    for btn in botoes_ok:
                        if btn.is_displayed() and btn.is_enabled():
                            log('[DEBUG] Clicando em botão de confirmação do modal de lote.')
                            safe_click(driver, btn)
                            time.sleep(1)
                            break
                time.sleep(0.5)
            else:
                log('[ERRO] Timeout aguardando URL de minutas ou fechamento de modal de lote.')
                raise Exception('URL de minutas não carregada nem modal fechado')
        except Exception as e:
            log(f'[ERRO] Falha ao aguardar URL de minutas/modal: {e}')
            return False
        log(f'[DEBUG] Prosseguindo com URL: {driver.current_url}')
        # prossegue fluxo original a partir daqui
        url_atual = driver.current_url
        aba_origem = driver.current_window_handle

        # 1. Seleção do tipo de expediente
        log('[DEBUG] Selecionando tipo de expediente...')
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
            campo_tipo.click()
            time.sleep(0.5)
            xpath_opcao = f"//mat-option//span[contains(text(), '{tipo_expediente}')]"
            opcao_tipo = driver.find_element(By.XPATH, xpath_opcao)
            opcao_tipo.click()
            log(f'[DEBUG] Tipo de expediente selecionado: {tipo_expediente}')
            time.sleep(0.5)
        except Exception as e:
            log(f'[ERRO] Falha ao selecionar tipo de expediente: {e}')
            return False
        # Dias úteis e prazo
        try:
            log('[DEBUG] Selecionando opção "dias úteis" se disponível...')
            spans = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-radio-label-content') and contains(translate(normalize-space(.), 'DÍASÚTEIS', 'díasúteis'), 'dias úteis')]")
            for span in spans:
                if span.is_displayed():
                    span.click()
                    log('[DEBUG] Opção "dias úteis" selecionada.')
                    break
            campo_prazo = None
            log('[DEBUG] Buscando campo de prazo...')
            for selector in ['input[formcontrolname="prazo"]', 'input[type="number"]', 'input[type="text"]']:
                try:
                    campo_prazo = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if campo_prazo.is_displayed() and campo_prazo.is_enabled():
                        break
                except Exception:
                    pass
            if not campo_prazo:
                inputs = driver.find_elements(By.CSS_SELECTOR, 'input')
                for inp in inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        campo_prazo = inp
                        break
            if not campo_prazo:
                log('[ERRO] Nenhum campo de prazo localizado!')
                raise Exception('Nenhum campo de prazo localizado')
            log(f'[DEBUG] Preenchendo campo de prazo com: {prazo}')
            campo_prazo.clear()
            campo_prazo.send_keys(str(prazo))
            log(f"Campo de prazo preenchido com: {campo_prazo.get_attribute('value')}")
        except Exception as e:
            log(f"[ERRO] Não foi possível preencher o campo de prazo: {e}")
            return False
        time.sleep(0.5)
        # .fa-edit para abrir caixa de elaboração
        try:
            log('[DEBUG] Clicando no ícone .fa-edit para abrir caixa de elaboração...')
            driver.find_element(By.CSS_SELECTOR, '.fa-edit').click()
            time.sleep(1)
        except Exception as e:
            log(f"[ERRO] Não foi possível clicar em .fa-edit: {e}")
            return False
        # Aguarda o modal abrir e faz a seleção/inserção do modelo
        try:
            log('[DEBUG] Aguardando abertura do modal de minuta/modelo...')
            modal = None
            for i in range(20):
                modais = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container, .cdk-overlay-container .mat-dialog-container')
                if modais:
                    modal = modais[0]
                    break
                time.sleep(0.3)
            if not modal:
                log('[ERRO] Modal de minuta/modelo não apareceu após clique em .fa-edit!')
                return False
            log('[DEBUG] Modal de minuta/modelo detectado.')
            # Seleciona e insere o modelo corretamente antes do .fa-pen-nib
            campo_filtro = modal.find_element(By.CSS_SELECTOR, '#inputFiltro')
            campo_filtro.clear()
            campo_filtro.send_keys(modelo_nome)
            campo_filtro.send_keys(Keys.ENTER)
            # Aguarda e clica no item filtrado (ex: .nodo-filtrado)
            seletor_item_filtrado = '.nodo-filtrado'
            nodo = None
            for _ in range(20):
                nodos = modal.find_elements(By.CSS_SELECTOR, seletor_item_filtrado)
                if nodos:
                    nodo = nodos[0]
                    break
                time.sleep(0.2)
            if not nodo:
                log('[ERRO] Nodo do modelo não encontrado no modal!')
                return False
            nodo.click()
            # Aguarda e clica no botão de inserir modelo (corrigido para seletor robusto)
            btn_inserir = None
            for _ in range(20):
                botoes = modal.find_elements(By.XPATH, "//button[@aria-label='Inserir modelo de documento' and contains(@class, 'mat-raised-button') and .//span[normalize-space(text())='Inserir']]")
                for b in botoes:
                    if b.is_displayed() and b.is_enabled():
                        btn_inserir = b
                        break
                if btn_inserir:
                    break
                time.sleep(0.2)
            if not btn_inserir:
                log('[ERRO] Botão Inserir modelo de documento não encontrado!')
                return False
            btn_inserir.click()
            time.sleep(0.5)
            # Agora sim, clicar em .fa-pen-nib
            try:
                btn_pen_nib = modal.find_element(By.CSS_SELECTOR, '.fa-pen-nib')
                btn_pen_nib.click()
                log('[DEBUG] Clique em .fa-pen-nib realizado.')
            except Exception as e:
                log(f'[ERRO] Não foi possível clicar em .fa-pen-nib: {e}')
                return False
            # 2. Aguardar fechamento total do modal
            for i in range(20):
                modais = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container, .cdk-overlay-container .mat-dialog-container')
                if not modais:
                    log('[DEBUG] Modal fechado após clique em .fa-pen-nib.')
                    break
                time.sleep(0.3)
            else:
                log('[ERRO] Modal não fechou após clique em .fa-pen-nib!')
                return False
            # 3. De volta à tela de minutas, clicar em .pec-polo-passivo-partes-processo
            try:
                btn_pec_polo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '.pec-polo-passivo-partes-processo'))
                )
                btn_pec_polo.click()
                log('[DEBUG] Clique em .pec-polo-passivo-partes-processo realizado.')
            except Exception as e:
                log(f'[ERRO] Não foi possível clicar em .pec-polo-passivo-partes-processo: {e}')
                return False
            # 4. Aguardar carregamento (pode ser necessário aguardar algum elemento específico, aqui aguarda 1s)
            time.sleep(1)
            # 5. Clicar em <span class="mat-button-wrapper">Salvar</span>
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
                btn_salvar_final.click()
                log('[DEBUG] Clique no botão Salvar final realizado.')
            except Exception as e:
                log(f'[ERRO] Não foi possível clicar no botão Salvar final: {e}')
                return False
            time.sleep(1)
        except Exception as e:
            log(f"[ERRO] Falha ao interagir com o modal de minuta/modelo: {e}")
            return False

        # Fechar aba de minutas
        if '/minutas' in driver.current_url:
            try:
                driver.close()
            except Exception as e:
                log(f"[ERRO] Não foi possível fechar aba de minutas: {e}")
            if aba_origem in driver.window_handles:
                try:
                    driver.switch_to.window(aba_origem)
                except Exception as e:
                    log(f"[ERRO] Não foi possível voltar para aba original: {e}")
            else:
                log('[ERRO] Aba original não está mais disponível após fechar minutas.')
        # Visibilidade sigilosa
        if str(sigilo).lower() in ("sim", "true", "1"):
            try:
                from Fix import visibilidade_sigilosos
                visibilidade_sigilosos(driver, log=debug)
                log('[COMUNICACAO] Visibilidade extra aplicada por sigilo positivo.')
            except Exception as e:
                log(f"[COMUNICACAO][ERRO] Falha ao aplicar visibilidade extra: {e}")
        log('Comunicação processual finalizada.')
        return True
    except Exception as e:
        log(f"[ERRO] Falha no fluxo de comunicação: {e}")
        if 'aba_origem' in locals() and aba_origem in driver.window_handles:
            try:
                driver.switch_to.window(aba_origem)
            except Exception as e:
                log(f"[ERRO] Falha ao tentar voltar para aba original no erro principal: {e}")
        return False

def make_comunicacao_wrapper(tipo_expediente, prazo, nome_comunicacao, sigilo, modelo_nome, gigs_extra=None):
    def wrapper(driver, debug=False):
        return comunicacao_judicial(
            driver=driver,
            tipo_expediente=tipo_expediente,
            prazo=prazo,
            nome_comunicacao=nome_comunicacao,
            sigilo=sigilo,
            modelo_nome=modelo_nome,
            gigs_extra=gigs_extra,
            debug=debug
        )
    return wrapper

pec_bloqueio = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=7,
    nome_comunicacao='ciência bloqueio',
    sigilo=False,
    modelo_nome='zzintbloq',
    gigs_extra=(7, 'Guilherme - carta')
)
pec_decisao = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=10,
    nome_comunicacao='intimação de decisão',
    sigilo=False,
    modelo_nome='xs dec reg',
    gigs_extra=(7, 'Guilherme - carta')
)
pec_idpj = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=17,
    nome_comunicacao='defesa IDPJ',
    sigilo=False,
    modelo_nome='xidpj c',
    gigs_extra=(7, 'Guilherme - carta')
)
pec_editalidpj = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=15,
    nome_comunicacao='Defesa IDPJ',
    sigilo=False,
    modelo_nome='IDPJ (edital)',
    gigs_extra=None
)
pec_editaldec = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=8,
    nome_comunicacao='Decisão/Sentença',
    sigilo=False,
    modelo_nome='3dec',
    gigs_extra=None
)
pec_cpgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado CP',
    sigilo=False,
    modelo_nome='mdd cp geral',
    gigs_extra=None
)
pec_excluiargos = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Exclusão de convênios',
    sigilo=False,
    modelo_nome='asa/cnib',
    gigs_extra=None
)
pec_mddgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=8,
    nome_comunicacao='Mandado',
    sigilo=False,
    modelo_nome='02 - gené',
    gigs_extra=None
)
pec_mddaud = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado citação',
    sigilo=False,
    modelo_nome='xmdd aud',
    gigs_extra=None
)
pec_editalaud = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=1,
    nome_comunicacao='Citação',
    sigilo=False,
    modelo_nome='1cit',
    gigs_extra=None
)

# ====================================================
# BLOCO 3 - FLUXOS DE EXECUÇÃO E AUXILIARES
# ====================================================

# Definição do fluxo principal
def fluxo_principal(driver):
    # Navegação por clique no ícone .fa-tags
    print("[NAVEGAR] Procurando ícone .fa-tags...")
    tag_icon = esperar_elemento(driver, ".fa-tags", timeout=20)
    if not tag_icon:
        print("[ERRO] Ícone .fa-tags não encontrado!")
        return
    safe_click(driver, tag_icon)
    print("[NAVEGAR] Ícone .fa-tags clicado.")
    # Aguarda o carregamento da tela de atividades (ajuste o seletor se necessário)
    esperar_elemento(driver, ".classe-unica-da-tela-atividades", timeout=20)
    print("[OK] Na tela de atividades do GIGS. Continue o fluxo normalmente...")

def callback_ato(driver):
    # Fluxo completo de ato judicial/minuta
    preencher_campos_prazo(driver, valor=0)
    tratar_anexos_infojud_irpf_doi_sisbajud(driver, driver)
    selecionar_tipo_expediente(driver, texto='Intimação')
    criar_gigs(driver, dias_uteis=5, observacao='Ato Judicial', tela='minuta')
    buscar_documentos_sequenciais(driver)
    print('[ATOS] Fluxo de ato judicial executado.')

def iniciar_fluxo_pec(driver):
    try:
        print("[INICIAR] Iniciando fluxo PEC...")
        # Clicar no botão "Processo Eletrônico Colaborativo (PEC)"
        safe_click(driver, '#cke_16', timeout=10)
        #safe_click(driver, 'span.cke_button_label.cke_button__pec_label', timeout=10)
        
        # Verificar e clicar no botão "Incluir PEC" se ele não estiver visível
        # incluir_pec_button = buscar_seletor_robusto(driver, 'Incluir PEC')
        # if incluir_pec_button and incluir_pec_button.is_displayed():
        #     safe_click(driver, incluir_pec_button)
        
        # safe_click(driver, 'a[title="Incluir PEC"]', timeout=10)
        safe_click(driver, 'a[title="Incluir processo eletrônico colaborativo"]', timeout=10)

        # Preencher os campos do PEC
        # ... (código para preencher os campos do PEC)
        
        # Clicar no botão "OK" para confirmar a inclusão do PEC
        safe_click(driver, '#btnOk', timeout=10)
        
        # Lógica para lidar com a lista de processos (se aplicável)
        # ...
        
        print("[INFO] Preparando lista de processos...")
        # tratar_pec = callback_ato(driver)
        
        def tratar_pec(driver):
            # Implemente a lógica específica para tratar cada PEC aqui
            # Por exemplo, preencher campos, anexar documentos, etc.
            print("[INFO] Tratando PEC...")
            
            # Exemplo: Preencher o campo de observação
            # driver.find_element(By.CSS_SELECTOR, "textarea[id*='observacoes']").send_keys("PEC processado automaticamente")
            # time.sleep(1)
            # safe_click(driver, '#cke_61', timeout=10)
            # time.sleep(1)
            return True

        if not indexar_e_processar_lista(driver, tratar_pec, seletor_btn='button[aria-label="Abrir processo"]'):
            print('[ERRO] Falha ao processar lista de PECs')

    except Exception as e:
        logger.error(f'Erro no fluxo principal: {str(e)}')
        driver.save_screenshot('screenshot_erro_fluxo.png')
        raise

# Funções auxiliares
def fechar_preparacao_expediente(driver):
    """Fecha a tela de preparação de expediente"""
    try:
        btn_fechar = buscar_seletor_robusto(driver, ['fechar-expediente'])
        if btn_fechar:
            safe_click(driver, btn_fechar)
    except Exception as e:
        logger.warning(f'Não foi possível fechar expediente: {str(e)}')

# Corrige import para evitar conflito com módulo padrão selectors
import selectors_pje

def logar_termo_observacoes(driver):
    """
    Percorre a lista filtrada e loga o número do processo e o TERMO após 'xs' na coluna Observações. # Modificado docstring
    Exemplo: se Observações = 'xs decisao', registra 'decisao'. # Modificado exemplo
    """
    print('[DEBUG] Iniciando logar_termo_observacoes', flush=True)
    try:
        pass
    except Exception as outer_e:
        print(f'[DEBUG][FALHA] Erro inesperado em logar_termo_observacoes: {outer_e}', flush=True)

def pec_termo(driver, termo, debug=False):
    print(f'[PACTO] pec_termo chamado com: {termo}')
    func_name = f'pec_{termo.lower()}'
    func = globals().get(func_name)
    if callable(func):
        return func(driver, debug=debug)
    else:
        print(f'[PACTO] Nenhum wrapper encontrado para termo "{termo}". Aplicando fallback GIGS (0/pz pec).')
        # Ajuste: tela correta é 'detalhe', não 'minuta'
        criar_gigs(driver, 0, 'pz pec', tela='detalhe', log=debug)
        return True

def callback_processo(driver):
    print('[DEBUG] Iniciando callback_processo', flush=True)
    try:
        from Fix import extrair_xs_atividades # Atualizado import
        print('[DEBUG] Buscando termos xs nas atividades...') # Log atualizado
        resultados = extrair_xs_atividades(driver, log=True) # Atualizada chamada de função
        if not resultados:
            print('[PROCESSO][ERRO] Nenhum termo "xs" encontrado nas atividades') # Log atualizado
            criar_gigs(driver, 0, 'pz xs', tela='detalhe', log=True) # GIGS atualizado para 'pz xs'
            print('[DEBUG] callback_processo finalizado (sem xs)', flush=True) # Log atualizado
            return True
        texto = resultados[0].lower()
        import re
        m = re.search(r'xs[\s\+]+([\w-]+)', texto) # Regex atualizado para 'xs'
        if m:
            termo = m.group(1).strip()
            print(f'[PROCESSO][EXTRAIDO] Termo após "xs": {termo}') # Log atualizado
        else:
            print(f'[PROCESSO][ERRO CRÍTICO] Não foi possível extrair o termo após "xs". Texto encontrado: {texto}') # Log atualizado
            criar_gigs(driver, 0, 'pz xs', tela='detalhe', log=True) # GIGS atualizado para 'pz xs'
            print('[DEBUG] callback_processo finalizado (erro extração termo)', flush=True)
            return True
        # Aguarda possíveis carregamentos antes de seguir
        time.sleep(0.5)
        # A função pec_termo provavelmente precisa ser renomeada ou ajustada para lidar com 'xs'
        # Assumindo que a lógica de pec_termo ainda é relevante para termos após 'xs'
        pec_termo(driver, termo) # Chamada mantida, mas pode precisar de revisão
        print('[DEBUG] callback_processo finalizado com sucesso', flush=True)
        return True
    except Exception as e:
        print(f'[PROCESSO][ERRO] Erro no callback: {str(e)}')
        # Espera curta para evitar atropelamento em caso de erro
        time.sleep(0.5)
        return True

def fluxo_sincrono_processo(driver):
    print('[FLUXO] Iniciando processamento síncrono do processo', flush=True)
    from Fix import extrair_xs_atividades # Atualizado import
    import re
    try:
        # Criar GIGS padrão para 'xs' caso algo falhe
        criar_gigs(driver, 0, 'pz xs', tela='detalhe', log=True) # GIGS atualizado para 'pz xs'
        resultados = extrair_xs_atividades(driver, log=True) # Atualizada chamada de função
        if not resultados:
            print('[FLUXO] Nenhum termo "xs" encontrado. Fechando processo.') # Log atualizado
            if len(driver.window_handles) > 1:
                try:
                    driver.close()
                    print('[FLUXO] Aba do processo fechada (nenhum xs).') # Log atualizado
                except Exception as e:
                    print(f'[FLUXO][WARN] Erro ao fechar aba: {e}')
            else:
                print('[FLUXO] Só existe uma aba aberta, não será fechada.')
            time.sleep(1)
            return False
        texto = resultados[0].lower()
        import re
        m = re.search(r'xs[\s\+]+([\w-]+)', texto)  # Regex atualizado para 'xs'
        if m:
            termo = m.group(1).strip()
            print(f'[FLUXO] Termo extraído: {termo}')
            # A lógica de chamar 'pec_{termo}' pode não fazer mais sentido com 'xs'
            # Precisa revisar se os wrappers 'pec_*' são aplicáveis ou se uma nova lógica é necessária
            func_name = f'pec_{termo.lower()}'  # Mantido por enquanto, mas revisar!
            func = globals().get(func_name)
            if callable(func):
                print(f'[FLUXO] Executando wrapper: {func_name}')
                resultado = func(driver, debug=False)
                if resultado is not True:
                    print(f'[FLUXO][ERRO] Execução do wrapper {func_name} falhou. Mantendo aba aberta para inspeção.')
                    return False  # Não fecha a aba, não segue
            else:
                print(f'[FLUXO] Wrapper {func_name} não encontrado. Nenhuma ação extra.')
        else:
            print(f'[FLUXO] Não foi possível extrair termo após "xs". Nenhuma ação extra.')  # Log atualizado
        # Após o wrapper, garantir que está na aba da lista ou fechar a aba do processo se ainda existir
        current_handle = driver.current_window_handle
        handles = driver.window_handles
        # Se ainda estiver na aba do processo (não foi fechada pelo wrapper), fecha
        if len(handles) > 1 and current_handle != handles[0]:
            try:
                driver.close()
                print('[FLUXO] Aba do processo fechada após wrapper.')
            except Exception as e:
                print(f'[FLUXO][WARN] Erro ao fechar aba após wrapper: {e}')
            # Volta para a aba da lista
            try:
                driver.switch_to.window(handles[0])
                print('[FLUXO] Foco retornado para aba da lista.')
            except Exception as e:
                print(f'[FLUXO][WARN] Erro ao retornar foco para aba da lista: {e}')
        else:
            print('[FLUXO] Nenhuma aba extra para fechar ou já está na aba da lista.')
        time.sleep(1)
        print('[FLUXO] Processamento do processo finalizado.', flush=True)
        return True
    except Exception as e:
        print(f'[FLUXO][ERRO] {e}')
        print('[FLUXO][ERRO] Mantendo aba aberta para inspeção. Não seguirá para o próximo processo.')
        return False

def main():
    limpar_temp_selenium()
    PROFILE_PATH = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
    FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
    from selenium.webdriver.firefox.service import Service
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    import time
    options = Options()
    options.binary_location = FIREFOX_BINARY
    options.set_preference('profile', PROFILE_PATH)
    service = Service()
    driver = webdriver.Firefox(service=service, options=options)
    try:
        usuario = os.environ.get('PJE_USUARIO') or input('Usuário PJe: ')
        senha = os.environ.get('PJE_SENHA') or input('Senha PJe: ')
        if not login_pc(driver, usuario, senha):
            raise Exception('Falha no login')
        print('Clicando no ícone de tags...')
        icone_tags = esperar_elemento(driver, '.fa-tags', timeout=15)
        if icone_tags:
            safe_click(driver, icone_tags)
            esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=20)
            time.sleep(1)
        else:
            raise Exception('Ícone de tags não encontrado')
        from Fix import aplicar_filtro_100
        print('[DEBUG] Chamando aplicar_filtro_100(driver)...')
        aplicar_filtro_100(driver)
        # Aplica filtro xs no campo correto
        campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Descrição"]')
        campo_desc.clear()
        campo_desc.send_keys('xs') # Modificado de 'xs pec' para 'xs'
        campo_desc.send_keys(Keys.ENTER)
        print('[DEBUG] Filtro xs aplicado.') # Log atualizado
        time.sleep(2)  # Aguarda atualização da lista
        # Indexa e processa a lista de processos (indexação ocorre apenas uma vez)
        from Fix import indexar_e_processar_lista
        print('[DEBUG] Iniciando processamento da lista...')
        indexar_e_processar_lista(driver, fluxo_sincrono_processo, seletor_btn='button[aria-label="Abrir processo"]', log=True)
        print('[MAIN] Fim do processamento da lista de processos.', flush=True)
    except Exception as e:
        logger.error(f'Erro no fluxo principal: {str(e)}')
        driver.save_screenshot('screenshot_erro_fluxo.png')
        raise
if __name__ == "__main__":
    main()
    # Executa o script principal
    # main()

def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False):
    from selenium.webdriver.common.by import By
    linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
    if not linhas:
        print('[ATO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!')
        return False
    ativos = []
    for tr in linhas:
        try:
            checkbox = tr.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Intimar parte"]')
            if checkbox.get_attribute('aria-checked') == 'true':
                ativos.append((tr, checkbox))
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao localizar checkbox: {e}')
    if not ativos:
        print('[ATO][PRAZO][ERRO] Nenhum destinatário ativo!')
        return False
    if apenas_primeiro:
        # Desmarca todos exceto o primeiro
        for i, (tr, checkbox) in enumerate(ativos):
            if i == 0:
                continue
            try:
                driver.execute_script("arguments[0].click();", checkbox)
                print(f'[ATO][PRAZO][INFO] Checkbox do destinatário {i+1} desmarcado.')
            except Exception as e:
                print(f'[ATO][PRAZO][WARN] Erro ao desmarcar checkbox: {e}')
        ativos = [ativos[0]]
    # Preenche prazos
    for tr, checkbox in ativos:
        try:
            input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
            input_prazo.clear()
            input_prazo.send_keys(str(prazo))
            print(f'[ATO][PRAZO][OK] Preenchido prazo {prazo} para destinatário.')
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao preencher prazo: {e}')
    return True

        # ---
        # SEGUNDA TENTATIVA (REFERÊNCIA JS/ASYNC PARA MOVIMENTO)
        # if (comandos?.movimento) {
        #     // Ativa a guia Movimentos se desativada
        #     let guia = await esperarElemento('pje-editor-lateral div[aria-posinset="2"]');
        #     if (guia.getAttribute('aria-selected') == "false") {
        #         await clicarBotao(guia);
        #         await sleep(500);
        #     }
        #     let movimentos = comandos.movimento.split(',');
        #     for (const [i,mo] of movimentos.entries()) {
        #         if (i == 0) { // Checkbox de movimento
        #             let chk = await esperarElemento('pje-movimento mat-checkbox', mo);
        #             if (!chk.className.includes('checked')) {
        #                 await clicarBotao('pje-movimento mat-checkbox label',mo);
        #                 await sleep(500);
        #             }
        #         } else { // Complementos do tipo
        #             await sleep(500);
        #             let complementosDoTipo = await esperarColecao('pje-complemento');
        #             await sleep(500);
        #             let comboBox = complementosDoTipo[i-1].querySelector('mat-select');
        #             await escolherOpcaoTeste2(comboBox,mo)
        #             await sleep(500);
        #         }
        #     }
        #     await clicarBotao('pje-lancador-de-movimentos button[aria-label*="Gravar"]');
        #     await clicarBotao('mat-dialog-container button', 'Sim', true);
        # }
        # ---