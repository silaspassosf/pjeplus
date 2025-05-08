# atos.py
from Fix import (
    login_automatico,
    safe_click,
    esperar_elemento,
    processar_lista_processos,
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

        # NOVO: Clique/foco no campo de filtro de modelos ao entrar em /minutar (padrão MaisPje)
        try:
            campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
            if not campo_filtro_modelo.is_displayed() or not campo_filtro_modelo.is_enabled():
                print('[CLS][MODELO][ERRO] Campo de filtro de modelos não está visível/habilitado!')
                return False
            driver.execute_script("arguments[0].focus();", campo_filtro_modelo)
            time.sleep(0.3)
            print('[CLS][MODELO][OK] Clique/foco no campo de filtro de modelos realizado (padrão MaisPje).')
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
    **kwargs
):
    """
    Refatorado fluxo generalizado para qualquer ato judicial que siga o padrão do sobrestamento.
    Utiliza fluxo_cls para a etapa final de conclusão.
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
        import time
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

        # NOVO: Log robusto após clicar em Salvar
        print(f'[ATO][DEBUG] Após Salvar: URL atual = {driver.current_url}, Título = {driver.title}')
        time.sleep(1)

        # 6. Preenchimento de prazos e campos personalizados
        try:
            print('[ATO][PRAZO][DEBUG] Chamando preencher_prazos_destinatarios...')
            preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario)
        except Exception as e:
            print(f'[ATO][PRAZO][ERRO] Falha inesperada ao preencher prazos: {e}')
            return False

        campos_personalizados = kwargs.get('campos_personalizados', None)
        if campos_personalizados:
            try:
                campos_personalizados(driver)
            except Exception as cp_err:
                print(f'[ATO][ERRO] Falha ao executar campos_personalizados: {cp_err}')
                return False # Custom fields might be critical

        # 7. Clica em Gravar (Salvar) usando seletor direto
        try:
            btn_gravar = driver.find_element(By.CSS_SELECTOR, 'button.botao-salvar[type="submit"]')
            btn_gravar.click()
            print('[ATO] Clique no botão Gravar realizado!')
        except Exception as e:
            print(f'[ATO][ERRO] Botão Gravar não encontrado ou não clicável: {e}')
            return False

        # 8. Funções parametrizadas: PEC, Movimento, Sigilo
        # 8.1 PEC
        if marcar_pec is not None:
            try:
                pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label*="PEC"]')
                checked = pec_checkbox.get_attribute('aria-checked') == 'true' or pec_checkbox.is_selected()
                if marcar_pec and not checked:
                    driver.execute_script("arguments[0].click();", pec_checkbox)
                    if debug: print('[ATO] Caixa PEC marcada.')
                elif not marcar_pec and checked:
                    driver.execute_script("arguments[0].click();", pec_checkbox)
                    if debug: print('[ATO] Caixa PEC desmarcada.')
            except Exception as e:
                print(f'[ATO][ERRO] Não foi possível ajustar PEC: {e}')
        # 8.2 Movimento
        if movimento:
            try:
                # Clica na aba "Movimentos" antes de tentar preencher o campo
                abas = driver.find_elements(By.CSS_SELECTOR, '.mat-tab-labels .mat-tab-label')
                for aba in abas:
                    if 'Movimentos' in aba.text:
                        driver.execute_script("arguments[0].click();", aba)
                        print('[ATO][DEBUG] Aba "Movimentos" clicada.')
                        time.sleep(2)  # Pausa para garantir o carregamento da aba
                        break
                campo_mov = driver.find_element(By.CSS_SELECTOR, '#inputMovimento')
                campo_mov.clear()
                campo_mov.send_keys(movimento)
                campo_mov.send_keys(Keys.ENTER)
                if debug: print(f'[ATO] Movimento registrado: {movimento}')
            except Exception as e:
                print(f'[ATO][ERRO] Não foi possível registrar movimento: {e}')
                print('[ATO][DEBUG] Execução pausada após erro em Movimento.')
                import time; time.sleep(10)
        # 8.3 Sigilo (padrão: False)
        sigilo = kwargs.get('sigilo', False)
        try:
            # Busca o input do slide-toggle pelo atributo name ou id
            sigilo_input = driver.find_element(By.CSS_SELECTOR, 'input.mat-slide-toggle-input[name="sigiloso"]')
            checked = sigilo_input.get_attribute('aria-checked') == 'true' or sigilo_input.is_selected()
            if sigilo and not checked:
                driver.execute_script("arguments[0].click();", sigilo_input)
                if debug: print('[ATO] Sigilo ativado.')
            elif not sigilo and checked:
                driver.execute_script("arguments[0].click();", sigilo_input)
                if debug: print('[ATO] Sigilo desativado.')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível ajustar Sigilo: {e}')

        # 9. Cria GIGS (minuta) como última etapa, se definido
        if gigs:
            try:
                from Fix import gigs_minuta
                gigs_minuta(driver, **gigs)
                print('[ATO] GIGS (minuta) criado com sucesso na etapa final.')
            except Exception as e:
                print(f'[ATO][ERRO] Falha ao criar GIGS (minuta): {e}')

        # 10. Executa o fluxo de conclusão usando fluxo_cls
        print(f'[ATO] Iniciando fluxo de conclusão para tipo: {conclusao_tipo}')
        if not fluxo_cls(driver, conclusao_tipo):
            print(f'[ATO][ERRO] Falha no fluxo_cls para {conclusao_tipo}.')
            return False # Indicate failure if fluxo_cls fails

        print(f'[ATO] Fluxo de ato judicial ({conclusao_tipo}, {modelo_nome}) finalizado com sucesso.')
        return True # Indicate success

    except Exception as e:
        print(f'[ATO][ERRO] Falha no fluxo do ato judicial ({conclusao_tipo}, {modelo_nome}): {e}')
        # Attempt screenshot on error
        try:
            driver.save_screenshot(f'erro_ato_{conclusao_tipo}_{modelo_nome}.png')
        except Exception as screen_err:
            print(f'[ATO][WARN] Falha ao salvar screenshot do erro: {screen_err}')
        return False # Indicate failure

# Definição de wrappers para atos judiciais padrão
def ato_meios(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xsmeios',
        prazo=5,
        marcar_pec=False,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=True,
        debug=debug
    )

def ato_pesquisas(driver, conclusao_tipo=None, modelo_nome=None, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, debug=False):
    # Para pesquisas, a conclusão correta é sempre 'BNDT'
    return ato_judicial(
        driver,
        conclusao_tipo='BNDT',  # Força sempre BNDT
        modelo_nome=modelo_nome or 'xsbacen',
        prazo=prazo if prazo is not None else 30,
        marcar_pec=marcar_pec if marcar_pec is not None else True,
        movimento=movimento or 'bl',
        gigs=gigs if gigs is not None else {'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=marcar_primeiro_destinatario if marcar_primeiro_destinatario is not None else True,
        debug=debug
    )

def ato_crda(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='a reclda',
        prazo=15,
        marcar_pec=False,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=False,
        debug=debug
    )

def ato_crte(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xreit',
        prazo=15,
        marcar_pec=False,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=False,
        debug=debug
    )

def ato_bloq(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xsparcial',
        prazo=None,
        marcar_pec=True,
        movimento=None,
        gigs={'dias_uteis': 1, 'observacao': 'pec bloq'},
        marcar_primeiro_destinatario=False,
        debug=debug
    )

def ato_idpj(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='IDPJ',
        modelo_nome='pjsem',
        prazo=8,
        marcar_pec=True,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=False,
        debug=debug
    )

def ato_termoE(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xempre',
        prazo=5,
        marcar_pec=False,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=True,
        debug=debug
    )

def ato_termoS(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xsocio',
        prazo=5,
        marcar_pec=False,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=True,
        debug=debug
    )

def ato_edital(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xsedit',
        prazo=5,
        marcar_pec=False,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=True,
        debug=debug
    )

def ato_sobrestamento(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='sobrestamento',
        modelo_nome='suspf',
        prazo=0,
        marcar_pec=False,
        movimento='fr', # Assuming 'fr' is a string literal
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=False,
        debug=debug
    )

# ====================================================
# BLOCO 2 - COMUNICAÇÕES PROCESSUAIS (Wrappers + Regra Geral)
# ====================================================

# Definição da regra geral de comunicação processual
def comunicacao_judicial(driver, tipo_expediente, prazo, nome_comunicacao, sigilo, modelo_nome, gigs_extra=None, debug=False):
    """
    Novo fluxo: só executa se já estiver na URL do processo (termina com /detalhe).
    Abre nova aba para /comunicacoesprocessuais/minutas e executa o fluxo nela.
    Seletores adaptados para padrão MaisPje e máxima robustez.
    """
    def log(msg):
        print(f'[COMUNICACAO] {msg}')
        if debug:
            time.sleep(0.5)
    try:
        url_atual = driver.current_url
        if not url_atual.endswith('/detalhe'):
            log('[ERRO CRÍTICO] comunicacao_judicial só pode ser chamada na URL do processo que termina com /detalhe!')
            raise Exception('URL inválida para comunicacao_judicial')

        aba_origem = driver.current_window_handle # Define aba_origem HERE

        url_minutas = url_atual.replace('/detalhe', '/comunicacoesprocessuais/minutas')
        log(f'Abrindo nova aba para minutas: {url_minutas}')
        abas_antes = set(driver.window_handles)
        driver.execute_script(f"window.open('{url_minutas}', '_blank');")
        # Aguarda a nova aba aparecer (timeout de 10s)
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.5)
        if not nova_aba:
            log('[ERRO] Nova aba de minutas não foi aberta.')
            return False
        try:
            driver.switch_to.window(nova_aba)
        except Exception as e:
            log(f'[ERRO] Não foi possível trocar para nova aba de minutas: {e}')
            return False
        time.sleep(2)
        # Seleção padrão MaisPje: abre dropdown do tipo de expediente
        log('Abrindo dropdown do Tipo de Expediente (MaisPje)...')
        campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
        campo_tipo.click()
        time.sleep(0.5)
        # Seleciona a opção pelo texto visível
        log(f'Selecionando opção do tipo de expediente: {tipo_expediente}')
        xpath_opcao = f"//mat-option//span[contains(text(), '{tipo_expediente}')]"
        opcao_tipo = driver.find_element(By.XPATH, xpath_opcao)
        opcao_tipo.click()
        time.sleep(0.5)
        # Campo de dias úteis (radio ou botão)
        try:
            log('Selecionando Dias Úteis (forçando clique)')
            # Busca o span correto com texto "dias úteis" (ignora espaços e caixa)
            spans = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-radio-label-content') and contains(translate(normalize-space(.), 'DÍASÚTEIS', 'díasúteis'), 'dias úteis')]")
            clicou = False
            for span in spans:
                if span.is_displayed():
                    span.click()
                    log('Clique em Dias Úteis realizado.')
                    clicou = True
                    time.sleep(0.5)
                    break
            if not clicou:
                log('Nenhum span Dias Úteis visível para clicar.')
            # Após clicar, aguarda o campo de prazo aparecer
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            campo_prazo = None
            for selector in ['input[formcontrolname="prazo"]', 'input[type="number"]', 'input[type="text"]']:
                try:
                    campo_prazo = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if campo_prazo.is_displayed() and campo_prazo.is_enabled():
                        break
                except Exception:
                    pass
            # Se não apareceu, tenta clicar novamente
            if not campo_prazo:
                log('Campo de prazo não apareceu, tentando clicar novamente em Dias Úteis...')
                for span in spans:
                    if span.is_displayed():
                        span.click()
                        time.sleep(0.5)
                        break
                # Tenta esperar de novo
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
                # Busca qualquer input visível
                inputs = driver.find_elements(By.CSS_SELECTOR, 'input')
                for inp in inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        campo_prazo = inp
                        break
            if not campo_prazo:
                raise Exception('Nenhum campo de prazo localizado por nenhum seletor após tentar Dias Úteis')
            campo_prazo.clear()
            campo_prazo.send_keys(str(prazo))
            log(f'Campo de prazo preenchido com: {campo_prazo.get_attribute("value")})')
        except Exception as e:
            log(f'[ERRO] Não foi possível preencher o campo de prazo: {e}')
            return False
        time.sleep(0.5)
        # Clique no ícone .fa-edit para abrir a caixa de elaboração do ato
        try:
            log('Clicando em .fa-edit para abrir a caixa de elaboração do ato')
            driver.find_element(By.CSS_SELECTOR, '.fa-edit').click()
            time.sleep(1)
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em .fa-edit: {e}')
            return False
        # Preencher campo Tipo de Documento (input texto/autocomplete)
        try:
            log('Preenchendo campo Tipo de Documento (input texto/autocomplete)...')
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            campo_tipo_doc = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[aria-label*="Tipo de Documento"]'))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo_tipo_doc)
            time.sleep(0.2)
            campo_tipo_doc.clear()
            campo_tipo_doc.send_keys(tipo_expediente)
            time.sleep(0.2)
            from selenium.webdriver.common.keys import Keys
            campo_tipo_doc.send_keys(Keys.ENTER)
            log(f'Tipo de Documento preenchido: {tipo_expediente}')
        except Exception as e:
            log(f'[ERRO] Não foi possível preencher o campo Tipo de Documento: {e}')
        # Preencher campo de descrição (Título) com nome_comunicacao, aguardando o campo aparecer
        try:
            log(f'Preenchendo campo de descrição com: {nome_comunicacao}')
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            campo_descricao = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Descrição"]'))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo_descricao)
            time.sleep(0.2)
            campo_descricao.clear()
            campo_descricao.send_keys(nome_comunicacao)
            time.sleep(0.2)
        except Exception as e:
            log(f'[ERRO] Não foi possível preencher o campo de descrição: {e}')
            return False
        # 6. Seleciona o modelo na árvore por texto robusto
        campo_filtro = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#inputFiltro'))
        )
        campo_filtro.clear()
        campo_filtro.send_keys(modelo_nome)
        campo_filtro.send_keys(Keys.ENTER)
        xpath_modelo = f"//div[@role='treeitem' and contains(translate(normalize-space(), 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), translate('{modelo_nome}', 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'))]"
        nodo = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath_modelo))
        )
        nodo.click()
        time.sleep(1)
        # 7. Clica em Inserir na árvore de modelos
        btn_inserir = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.div-botao-inserir > button'))
        )
        btn_inserir.click()
        time.sleep(1)
        # Botão salvar
        try:
            log('Clicando em salvar (final)')
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            btn_salvar_final = WebDriverWait(driver, 20).until(
                lambda d: next(
                    (b for b in d.find_elements(By.CSS_SELECTOR, 'button.mat-focus-indicator[type="submit"]')
                     if b.is_displayed() and b.is_enabled() and 'mat-button-disabled' not in b.get_attribute('class')),
                    None
                )
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_salvar_final)
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-focus-indicator[type="submit"]')))
            try:
                btn_salvar_final.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn_salvar_final)
            time.sleep(1)
            # NOVO: clicar em .fa-pen-nib para finalizar
            try:
                log('Clicando em .fa-pen-nib para finalizar comunicação')
                btn_pen_nib = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '.fa-pen-nib'))
                )
                btn_pen_nib.click()
                time.sleep(1)
            except Exception as e:
                log(f'[ERRO] Não foi possível clicar em .fa-pen-nib após salvar: {e}')
                # Logged the error, continuing execution for now.

            # Após .fa-pen-nib, se estiver em /minutas, fecha a aba
            if '/minutas' in driver.current_url:
                try:
                    driver.close()
                except Exception as e:
                    log(f'[WARN] Erro ao fechar aba de minutas: {e}')
                if aba_origem in driver.window_handles: # Now aba_origem is defined
                    try:
                        driver.switch_to.window(aba_origem) # Now aba_origem is defined
                    except Exception as e:
                        log(f'[ERRO] Não foi possível voltar para aba original: {e}')
                else:
                    log('[ERRO] Aba original não está mais disponível após fechar minutas.')
            log('Comunicação processual finalizada.')
            return True
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em salvar: {e}')
            return False
    except Exception as e:
        log(f'[ERRO] Falha no fluxo de comunicação: {e}')
        # Consider adding tab closing logic here too if an error occurs earlier
        # Ensure aba_origem exists before trying to switch back in case of early failure
        if 'aba_origem' in locals() and aba_origem in driver.window_handles:
             try:
                 driver.switch_to.window(aba_origem)
             except Exception as switch_err:
                 log(f'[ERRO] Falha ao tentar voltar para aba original no erro principal: {switch_err}')
        return False

# Wrappers para comunicações processuais

def pec_bloqueio(driver, debug=False):
    """
    Wrapper para comunicação de ciência bloqueio (PEC bloqueio).
    - Tipo de expediente: Intimação
    - Prazo: 7 dias
    - Nome da comunicação: ciência bloqueio
    - Sigilo: Não
    - Modelo: zzintbloq
    - GIGS extra: 7/Guilherme - carta
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Intimação',
        prazo=7,
        nome_comunicacao='ciência bloqueio',
        sigilo=False,
        modelo_nome='zzintbloq',
        gigs_extra=(7, 'Guilherme - carta'),
        debug=debug
    )

def pec_Decisao(driver, debug=False):
    """
    Wrapper para comunicação de intimação de decisão (PEC Decisao).
    - Tipo de expediente: Intimação
    - Prazo: 10 dias
    - Nome da comunicação: intimação de decisão
    - Sigilo: Não
    - Modelo: xs dec reg
    - GIGS extra: 7/Guilherme - carta
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Intimação',
        prazo=10,
        nome_comunicacao='intimação de decisão',
        sigilo=False,
        modelo_nome='xs dec reg',
        gigs_extra=(7, 'Guilherme - carta'),
        debug=debug
    )

def pec_idpj(driver, debug=False):
    """
    Wrapper para comunicação de defesa IDPJ (PEC idpj).
    - Tipo de expediente: Intimação
    - Prazo: 17 dias
    - Nome da comunicação: defesa IDPJ
    - Sigilo: Não
    - Modelo: xidpj c
    - GIGS extra: 7/Guilherme - carta
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Intimação',
        prazo=17,
        nome_comunicacao='defesa IDPJ',
        sigilo=False,
        modelo_nome='xidpj c',
        gigs_extra=(7, 'Guilherme - carta'),
        debug=debug
    )

def pec_editalidpj(driver, debug=False):
    """
    Wrapper para comunicação de edital defesa IDPJ (PEC editalidpj).
    - Tipo de expediente: Edital
    - Prazo: 15 dias
    - Nome da comunicação: Defesa IDPJ
    - Sigilo: Não
    - Modelo: IDPJ (edital)
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Edital',
        prazo=15,
        nome_comunicacao='Defesa IDPJ',
        sigilo=False,
        modelo_nome='IDPJ (edital)',
        gigs_extra=None,
        debug=debug
    )

def pec_editaldec(driver, debug=False):
    """
    Wrapper para comunicação de edital decisão/sentença (PEC editaldec).
    - Tipo de expediente: Edital
    - Prazo: 8 dias
    - Nome da comunicação: Decisão/Sentença
    - Sigilo: Não
    - Modelo: 3dec
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Edital',
        prazo=8,
        nome_comunicacao='Decisão/Sentença',
        sigilo=False,
        modelo_nome='3dec',
        gigs_extra=None,
        debug=debug
    )

def pec_cpgeral(driver, debug=False):
    """
    Wrapper para comunicação de mandado CP Geral (PEC cpgeral).
    - Tipo de expediente: Mandado
    - Prazo: 1 dia
    - Nome da comunicação: Mandado
    - Sigilo: Não
    - Modelo: mdd cp geral
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Mandado',
        prazo=1,
        nome_comunicacao='Mandado CP',
        sigilo=False,
        modelo_nome='mdd cp geral',
        gigs_extra=None,
        debug=debug
    )

def pec_excluiargos(driver, debug=False):
    """
    Wrapper para comunicação de exclusão de convênios (PEC excluiargos).
    - Tipo de expediente: Mandado
    - Prazo: 1 dia
    - Nome da comunicação: Exclusão de convênios
    - Sigilo: Não
    - Modelo: asa/cnib
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Mandado',
        prazo=1,
        nome_comunicacao='Exclusão de convênios',
        sigilo=False,
        modelo_nome='asa/cnib',
        gigs_extra=None,
        debug=debug
    )

def pec_mddgeral(driver, debug=False):
    """
    Wrapper para comunicação de mandado geral (PEC mddgeral).
    - Tipo de expediente: Mandado
    - Prazo: 8 dias
    - Nome da comunicação: Mandado
    - Sigilo: Não
    - Modelo: 02 - gené
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Mandado',
        prazo=8,
        nome_comunicacao='Mandado',
        sigilo=False,
        modelo_nome='02 - gené',
        gigs_extra=None,
        debug=debug
    )

def pec_mddaud(driver, debug=False):
    """
    Wrapper para comunicação de mandado citação (PEC mddaud).
    - Tipo de expediente: Mandado
    - Prazo: 1 dia
    - Nome da comunicação: Mandado citação
    - Sigilo: Não
    - Modelo: xmdd aud
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Mandado',
        prazo=1,
        nome_comunicacao='Mandado citação',
        sigilo=False,
        modelo_nome='xmdd aud',
        gigs_extra=None,
        debug=debug
    )

def pec_editalaud(driver, debug=False):
    """
    Wrapper para comunicação de edital citação (PEC editalaud).
    - Tipo de expediente: Edital
    - Prazo: 1 dia
    - Nome da comunicação: Citação
    - Sigilo: Não
    - Modelo: 1cit
    - Sem GIGS extra
    """
    return comunicacao_judicial(
        driver,
        tipo_expediente='Edital',
        prazo=1,
        nome_comunicacao='Citação',
        sigilo=False,
        modelo_nome='1cit',
        gigs_extra=None,
        debug=debug
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

        if not processar_lista_processos(driver, tratar_pec, seletor_btn='button[aria-label="Abrir processo"]'):
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
            return True
        texto = resultados[0].lower()
        m = re.search(r'xs[\s\+]+([\w-]+)', texto) # Regex atualizado para 'xs'
        if m:
            termo = m.group(1).strip()
            print(f'[FLUXO] Termo extraído: {termo}')
            # A lógica de chamar 'pec_{termo}' pode não fazer mais sentido com 'xs'
            # Precisa revisar se os wrappers 'pec_*' são aplicáveis ou se uma nova lógica é necessária
            func_name = f'pec_{termo.lower()}' # Mantido por enquanto, mas revisar!
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
            print(f'[FLUXO] Não foi possível extrair termo após "xs". Nenhuma ação extra.') # Log atualizado
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
        if not login_automatico(driver, usuario, senha):
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