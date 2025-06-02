from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import os

# =====================
# BLOCO 1 - ATO JUDICIAL
# =====================

def fluxo_cls(driver):
    """
    Fluxo geral para CLS (movimentação de minuta):
    1. Clica no botão 'Abrir tarefa do processo' (seletor robusto mattooltip)
    2. Verifica se a URL contém '/transicao'.
    3. Clica no ícone .fa-clipboard-check (Conclusão ao Magistrado).
    4. Verifica se a URL contém '/conclusao'.
    5. Pausa para inspeção/manual.
    PRAZO: Não definido (manual)
    """
    print('[CLS] Iniciando fluxo de CLS...')
    # ... (restante do código igual ao fluxo_cls)


def fluxo_ato_judicial(driver, nome_ato, filtro_modelo, seletor_btn_ato=None, seletor_item_filtrado='.nodo-filtrado', seletor_btn_inserir='pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button', seletor_btn_enviar='.fa-angle-right', preencher_prazos=True, campos_personalizados=None, seletor_btn_gravar='.botao-salvar', ajuste_pos_inserir=None):
    """
    Fluxo generalizado para qualquer ato judicial que siga o padrão do sobrestamento.
    Permite customizar seletores e etapas principais do fluxo.
    """
    try:
        # 1. Clica no botão do ato (seletor customizável)
        if seletor_btn_ato:
            botoes = driver.find_elements(By.CSS_SELECTOR, seletor_btn_ato)
            btn_ato = next((b for b in botoes if b.is_displayed()), None)
        else:
            botoes = driver.find_elements(By.CSS_SELECTOR, 'button')
            btn_ato = next((b for b in botoes if b.is_displayed() and nome_ato in b.text), None)
        if not btn_ato:
            print(f'[ATO][ERRO] Botão "{nome_ato}" não encontrado!')
            return
        btn_ato.click()
        print(f'[ATO] Clique no botão {nome_ato} realizado!')
        time.sleep(1)
        if not esperar_url_conter(driver, '/minutar', timeout=15):
            print(f'[ATO][ERRO] URL inesperada após {nome_ato}: {driver.current_url}')
            return
        print(f'[ATO] URL correta após {nome_ato}: {driver.current_url}')
        if not esperar_carregamento_minutar(driver):
            print('[ATO][ERRO] Falha ao aguardar carregamento da página /minutar.')
            return
        campo_filtro = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro.clear()
        campo_filtro.send_keys(filtro_modelo)
        campo_filtro.send_keys(Keys.ENTER)
        print(f'[ATO] "{filtro_modelo}" digitado e ENTER pressionado no filtro.')
        nodo = esperar_nodo_filtrado(driver, seletor=seletor_item_filtrado)
        if not nodo:
            return
        nodo.click()
        print('[ATO] Clique em nodo-filtrado realizado!')
        dialogo = esperar_dialogo_mat(driver)
        if not dialogo:
            return
        try:
            botao_inserir = dialogo.find_element(By.CSS_SELECTOR, seletor_btn_inserir)
            botao_inserir.click()
            print('[ATO] Clique no botão de inserir modelo realizado!')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível clicar no botão de inserir modelo: {e}')
            return
        if not esperar_dialogo_mat_sumir(driver):
            print('[ATO][ERRO] O mat-dialog não sumiu após inserir modelo.')
            return
        print('[ATO] Caixa de diálogo fechada, prosseguindo.')
        time.sleep(0.5)
        btn_enviar = driver.find_element(By.CSS_SELECTOR, seletor_btn_enviar)
        btn_enviar.click()
        print('[ATO] Clique em enviar realizado!')
        time.sleep(1)
        if preencher_prazos:
            print('[ATO] Preenchendo campos de prazo com 0...')
            preencher_prazo_minuta_zero(driver)
        if campos_personalizados:
            campos_personalizados(driver)
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, seletor_btn_gravar)
            for _ in range(10):
                if btn_salvar.is_displayed() and btn_salvar.is_enabled():
                    break
                time.sleep(0.3)
            time.sleep(1.2)
            btn_salvar.click()
            print('[ATO] Clique no botão Gravar realizado!')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível clicar no botão Gravar: {e}')
        print(f'[ATO] Fluxo de {nome_ato} finalizado.')
    except Exception as e:
        print(f'[ATO][ERRO] Falha no fluxo de {nome_ato}: {e}')


def fluxo_ato_judicial_parametrizado(
    driver,
    nome_ato,
    modelo_filtro,
    seletor_btn_ato=None,
    seletor_btn_inserir_modelo='pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button',
    seletor_btn_salvar='button.mat-focus-indicator:nth-child(4)',
    prazo_func=None,  # função para preencher prazos
    intima_func=None, # função para lidar com intimação
    pec_func=None,    # função para PEC
    quem_func=None,   # função para selecionar destinatários
    movimento_func=None, # função para movimento (ex: escolher "fr")
    gigs_func=None,   # função para criar GIGS
    debug=False
):
    """
    Esqueleto generalizado para atos judiciais/minuta, parametrizável para diferentes fluxos.
    """
    try:
        if seletor_btn_ato:
            botoes = driver.find_elements(By.CSS_SELECTOR, seletor_btn_ato)
            btn_ato = next((b for b in botoes if b.is_displayed()), None)
        else:
            botoes = driver.find_elements(By.CSS_SELECTOR, 'button')
            btn_ato = next((b for b in botoes if b.is_displayed() and nome_ato in b.text), None)
        if not btn_ato:
            print(f'[ATO][ERRO] Botão "{nome_ato}" não encontrado!')
            return
        btn_ato.click()
        if debug:
            print(f'[PAR] Clique no botão {nome_ato} realizado!')
        time.sleep(1)
        if not esperar_url_conter(driver, '/minutar', timeout=15):
            print(f'[PAR][ERRO] URL inesperada após {nome_ato}: {driver.current_url}')
            return
        if debug:
            print(f'[PAR] URL correta após {nome_ato}: {driver.current_url}')
        if not esperar_carregamento_minutar(driver):
            print('[PAR][ERRO] Falha ao aguardar carregamento da página /minutar.')
            return
        campo_filtro = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro.clear()
        campo_filtro.send_keys(modelo_filtro)
        campo_filtro.send_keys(Keys.ENTER)
        if debug:
            print(f'[PAR] "{modelo_filtro}" digitado e ENTER pressionado no filtro.')
        nodo = esperar_nodo_filtrado(driver)
        if not nodo:
            return
        nodo.click()
        if debug:
            print('[PAR] Clique em nodo-filtrado realizado!')
        dialogo = esperar_dialogo_mat(driver)
        if not dialogo:
            return
        try:
            botao_inserir = dialogo.find_element(By.CSS_SELECTOR, seletor_btn_inserir_modelo)
            botao_inserir.click()
            if debug:
                print('[PAR] Clique no botão de inserir modelo realizado!')
        except Exception as e:
            print(f'[PAR][ERRO] Não foi possível clicar no botão de inserir modelo: {e}')
            return
        if not esperar_dialogo_mat_sumir(driver):
            print('[PAR][ERRO] O mat-dialog não sumiu após inserir modelo.')
            return
        if debug:
            print('[PAR] Caixa de diálogo fechada, prosseguindo.')
        time.sleep(0.5)
        if prazo_func:
            prazo_func(driver)
        if intima_func:
            intima_func(driver)
        if pec_func:
            pec_func(driver)
        if quem_func:
            quem_func(driver)
        if movimento_func:
            movimento_func(driver)
        if gigs_func:
            gigs_func(driver)
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, seletor_btn_salvar)
            for _ in range(10):
                if btn_salvar.is_displayed() and btn_salvar.is_enabled():
                    break
                time.sleep(0.3)
            time.sleep(1.2)
            btn_salvar.click()
            if debug:
                print('[PAR] Clique no botão Gravar realizado!')
        except Exception as e:
            print(f'[PAR][ERRO] Não foi possível clicar no botão Gravar: {e}')
        if debug:
            print(f'[PAR] Fluxo de {nome_ato} finalizado.')
    except Exception as e:
        print(f'[PAR][ERRO] Falha no fluxo de {nome_ato}: {e}')


def fluxo_ato_judicial_esqueleto(
    driver,
    nome_ato,
    func_conclusao,
    modelo_nome,
    func_modelo=None,
    func_prazo=None,
    func_intimacao=None,
    func_pec=None,
    func_quem=None,
    func_movimento=None,
    func_gigs=None,
    debug=False
):
    """
    Esqueleto para fluxo de ato judicial parametrizável, baseado no detalhamento do sobrestamento.
    """
    try:
        func_conclusao(driver)
        if debug:
            print(f'[ESQ] Conclusão realizada.')
        campo_filtro = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro.clear()
        campo_filtro.send_keys(modelo_nome)
        campo_filtro.send_keys(Keys.ENTER)
        if debug:
            print(f'[ESQ] "{modelo_nome}" digitado e ENTER pressionado no filtro.')
        if func_modelo:
            func_modelo(driver)
        nodo = esperar_nodo_filtrado(driver)
        if not nodo:
            return
        nodo.click()
        if debug:
            print('[ESQ] Clique em nodo-filtrado realizado!')
        dialogo = esperar_dialogo_mat(driver)
        if not dialogo:
            return
        try:
            botao_inserir = dialogo.find_element(By.CSS_SELECTOR, 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button')
            botao_inserir.click()
            if debug:
                print('[ESQ] Clique no botão de inserir modelo realizado!')
        except Exception as e:
            print(f'[ESQ][ERRO] Não foi possível clicar no botão de inserir modelo: {e}')
            return
        if not esperar_dialogo_mat_sumir(driver):
            print('[ESQ][ERRO] O mat-dialog não sumiu após inserir modelo.')
            return
        if debug:
            print('[ESQ] Caixa de diálogo fechada, prosseguindo.')
        time.sleep(0.5)
        if func_prazo:
            func_prazo(driver)
        if func_intimacao:
            func_intimacao(driver)
        if func_pec:
            func_pec(driver)
        if func_quem:
            func_quem(driver)
        if func_movimento:
            func_movimento(driver)
        if func_gigs:
            func_gigs(driver)
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, '.botao-salvar')
            for _ in range(10):
                if btn_salvar.is_displayed() and btn_salvar.is_enabled():
                    break
                time.sleep(0.3)
            time.sleep(1.2)
            btn_salvar.click()
            if debug:
                print('[ESQ] Clique no botão Gravar realizado!')
        except Exception as e:
            print(f'[ESQ][ERRO] Não foi possível clicar no botão Gravar: {e}')
        if debug:
            print(f'[ESQ] Fluxo de {nome_ato} finalizado.')
    except Exception as e:
        print(f'[ESQ][ERRO] Falha no fluxo de {nome_ato}: {e}')


def ato_judicial(
    driver,
    conclusao_tipo,      # ex: 'despacho', 'IDPJ', etc
    modelo_nome,         # ex: 'xsmeios', 'pjsem', etc
    prazo=None,          # int (dias) ou None para não alterar
    marcar_pec=None,     # True, False ou None (para não mexer)
    movimento=None,      # string do movimento ou None
    gigs=None,           # dict com params para criar_gigs ou None
    marcar_primeiro_destinatario=False,
    debug=False
):
    """
    Função base para todos os atos judiciais padronizados do TRT2.
    Executa CLS, conclusão, modelo, destinatário, prazo, PEC, movimento e GIGS conforme parâmetros.
    """
    try:
        # 1. CLS
        if debug: print('[ATO] Executando CLS...')
        fluxo_cls(driver)
        # 2. Conclusão
        if debug: print(f'[ATO] Executando conclusão: {conclusao_tipo}')
        botoes = driver.find_elements(By.CSS_SELECTOR, 'button')
        btn_conclusao = next((b for b in botoes if b.is_displayed() and conclusao_tipo.lower() in b.text.lower()), None)
        if not btn_conclusao:
            print(f'[ATO][ERRO] Botão de conclusão "{conclusao_tipo}" não encontrado!')
            return False
        btn_conclusao.click()
        time.sleep(1)
        if not esperar_url_conter(driver, '/minutar', timeout=15):
            print(f'[ATO][ERRO] URL inesperada após conclusão: {driver.current_url}')
            return False
        if not esperar_carregamento_minutar(driver):
            print('[ATO][ERRO] Falha ao aguardar carregamento da página /minutar.')
            return False
        # 3. Seleciona modelo
        campo_filtro = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro.clear()
        campo_filtro.send_keys(modelo_nome)
        campo_filtro.send_keys(Keys.ENTER)
        nodo = esperar_nodo_filtrado(driver)
        if not nodo:
            print('[ATO][ERRO] Nodo do modelo não encontrado!')
            return False
        nodo.click()
        dialogo = esperar_dialogo_mat(driver)
        if not dialogo:
            print('[ATO][ERRO] Dialogo do modelo não encontrado!')
            return False
        try:
            botao_inserir = dialogo.find_element(By.CSS_SELECTOR, 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button')
            botao_inserir.click()
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível clicar no botão de inserir modelo: {e}')
            return False
        if not esperar_dialogo_mat_sumir(driver):
            print('[ATO][ERRO] O mat-dialog não sumiu após inserir modelo.')
            return False
        time.sleep(0.5)
        # 4. Destinatário e Prazo
        definir_prazo_e_destinatario(driver, prazo=prazo, marcar_primeiro_destinatario=marcar_primeiro_destinatario)
        # 5. PEC
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
        # 6. Movimento
        if movimento:
            try:
                campo_mov = driver.find_element(By.CSS_SELECTOR, '#inputMovimento')
                campo_mov.clear()
                campo_mov.send_keys(movimento)
                campo_mov.send_keys(Keys.ENTER)
                if debug: print(f'[ATO] Movimento registrado: {movimento}')
            except Exception as e:
                print(f'[ATO][ERRO] Não foi possível registrar movimento: {e}')
        # 7. GIGS - removido, usando apenas criar_gigs do Fix.py
        # 8. Gravar
        try:
            btn_salvar = driver.find_element(By.CSS_SELECTOR, '.botao-salvar')
            for _ in range(10):
                if btn_salvar.is_displayed() and btn_salvar.is_enabled():
                    break
                time.sleep(0.3)
            time.sleep(1.2)
            btn_salvar.click()
            if debug: print('[ATO] Clique no botão Gravar realizado!')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível clicar no botão Gravar: {e}')
        if debug: print('[ATO] Fluxo finalizado.')
        return True
    except Exception as e:
        print(f'[ATO][ERRO] Falha no fluxo do ato judicial: {e}')
        return False


def selecionar_primeira_caixa_destinatario(driver):
    """
    Seleciona apenas a primeira caixa de seleção de destinatário (checkbox) marcada, desmarcando as demais.
    """
    print('[UTIL] Selecionando apenas a primeira caixa de destinatário marcada...')
    try:
        tabela = driver.find_element(By.CSS_SELECTOR, 'table.t-class')
        linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody > tr.ng-star-inserted')
        checkboxes = [
            linha.find_element(By.CSS_SELECTOR, 'input[type="checkbox"].mat-checkbox-input:not([disabled])')
            for linha in linhas
            if 'desabilitado' not in linha.get_attribute('class')
            and linha.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"].mat-checkbox-input:not([disabled])')
        ]
        if not checkboxes:
            print('[UTIL][AVISO] Nenhuma caixa de destinatário habilitada encontrada.')
            return
        for idx, cb in enumerate(checkboxes):
            aria_checked = cb.get_attribute('aria-checked')
            if idx == 0 and aria_checked != 'true':
                cb.click()
            elif idx != 0 and aria_checked == 'true':
                cb.click()
        print('[UTIL] Apenas a primeira caixa de destinatário está marcada.')
    except Exception as e:
        print(f'[UTIL][ERRO] Falha ao selecionar caixas de destinatário: {e}')


def definir_prazo_e_destinatario(driver, prazo=None, marcar_primeiro_destinatario=False):
    """
    Função utilitária para:
    - Selecionar apenas a primeira caixa de destinatário, se marcar_primeiro_destinatario=True
    - Definir o prazo (em dias) no primeiro campo de texto, limpando os demais
    """
    if marcar_primeiro_destinatario:
        selecionar_primeira_caixa_destinatario(driver)
    if prazo is not None:
        campos = driver.find_elements(By.CSS_SELECTOR, 'input.mat-input-element[type="text"]')
        if campos:
            campos[0].clear()
            campos[0].send_keys(str(prazo).zfill(2))
            for campo in campos[1:]:
                campo.clear()
        print(f'[UTIL] Prazo ajustado: {prazo} dias (apenas primeiro campo)')


# =====================
# BLOCO 1 - ATOS JUDICIAIS
# =====================

# ---- A) REGRA GERAL E MÓDULOS PADRÃO ----
# (Funções utilitárias e ato_judicial já presentes)

# ---- B) ATOS DEFINIDOS (WRAPPERS) ----

# 1. Meios: apenas o primeiro destinatário, 5 dias
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

# 2. Pesquisas: apenas o primeiro destinatário, 30 dias
def ato_pesquisas(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='Bacen/BNDT',
        modelo_nome='xsbacen',
        prazo=30,
        marcar_pec=True,
        movimento='bl',
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=True,
        debug=debug
    )

# 3. Bloq: padrão do sistema (todos marcados, prazo padrão)
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

# 4. Sobrestamento: conclusão sobrestamento com modelo suspf
def ato_sobrestar(driver, debug=False):
    return ato_judicial(
        driver,
        conclusao_tipo='sobrestamento',
        modelo_nome='suspf',
        prazo=0,
        marcar_pec=False,
        movimento='fr',
        gigs={'dias_uteis': 0, 'observacao': 'pz verificar'},
        marcar_primeiro_destinatario=False,
        debug=debug
    )

# 4. Crte: todos destinatários marcados, 15 dias

# 5. Edital: despacho, modelo xsedit, prazo padrão, PEC sim
def ato_edital(driver, debug=False):
    """
    Cria ato judicial com modelo xsedit (edital).
    - Tipo de ato: despacho
    - Modelo: xsedit
    - Prazo: padrão do sistema
    - PEC: sim
    """
    return ato_judicial(
        driver,
        conclusao_tipo='despacho',
        modelo_nome='xsedit',
        prazo=None,
        marcar_pec=True,
        movimento=None,
        gigs={'dias_uteis': 0, 'observacao': 'pz mdd'},
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

# 5. Crda: todos destinatários marcados, 15 dias
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

# 6. TermoE: apenas o primeiro destinatário, 5 dias
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

# 7. TermoS: apenas o primeiro destinatário, 5 dias
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

# 8. IDPJ: todos destinatários marcados, 8 dias
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

# =====================
# BLOCO 2 - COMUNICAÇÃO
# =====================

def comunicacao_judicial(
    driver,
    tipo_expediente,
    prazo,
    nome_comunicacao,
    sigilo,
    modelo_nome,
    gigs_extra=None,  # NOVO: tupla (dias_uteis, observacao) ou None
    debug=False
):
    """
    Fluxo geral para comunicações processuais (intimação, citação, etc).
    Parâmetros variáveis:
        tipo_expediente: string (nome/valor do tipo de expediente)
        prazo: int (dias)
        nome_comunicacao: string (nome a ser digitado)
        sigilo: bool (True para marcar sigilo, False para não marcar)
        modelo_nome: string (nome do modelo para buscar)
        gigs_extra: tupla (dias_uteis, observacao) para segunda chamada de criar_gigs, ou None
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from Fix import selecionar_tipo_expediente, buscar_seletor_robusto
    def log(msg):
        print(f'[COMUNICACAO] {msg}')
        if debug:
            time.sleep(1)

    log('Iniciando fluxo de comunicação...')
    try:
        log('Clicando na tarefa do processo (primeiro clique do CLS)')
        btn_abrir_tarefa = driver.find_element(By.CSS_SELECTOR, 'button.botao-detalhe')
        btn_abrir_tarefa.click()
        time.sleep(1)
        # 1. Foca na nova aba, se houver
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            log('Foco alterado para a nova aba.')
        else:
            log('Apenas uma aba detectada, foco mantido.')
        # 2. Checa a URL: se já estiver em /comunicacoesprocessuais, pula o clique em .fa-envelope
        if '/comunicacoesprocessuais' in driver.current_url:
            log('URL já está em /comunicacoesprocessuais: pulando clique em .fa-envelope e indo direto para tipo de expediente.')
            try:
                seletor_tipo_expediente = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
            except Exception:
                # fallback: busca por id conhecido
                seletor_tipo_expediente = driver.find_element(By.CSS_SELECTOR, 'mat-select#mat-select-0')
            seletor_tipo_expediente.click()
            time.sleep(1)
        else:
            log('Fluxo padrão: clicando em .fa-envelope')
            driver.find_element(By.CSS_SELECTOR, '.fa-envelope').click()
            time.sleep(1)
            try:
                seletor_tipo_expediente = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Tipo de Expediente"]')
            except Exception:
                # fallback: busca por id conhecido
                seletor_tipo_expediente = driver.find_element(By.CSS_SELECTOR, 'mat-select#mat-select-0')
            seletor_tipo_expediente.click()
            time.sleep(1)
        # Seleção robusta do Tipo de Expediente usando utilitário Fix.py
        if not selecionar_tipo_expediente(driver, tipo_expediente, timeout=5, log=True):
            # Se falhar, tenta clicar diretamente na opção usando texto visível
            opcao = buscar_seletor_robusto(driver, [tipo_expediente], timeout=5, log=True)
            if opcao:
                opcao.click()
                log(f'Tipo de Expediente selecionado manualmente: {tipo_expediente}')
            else:
                log(f'[ERRO] Não foi possível selecionar o Tipo de Expediente: {tipo_expediente}')
                return False
        time.sleep(1)
        log('Clicando em Dias Úteis')
        driver.find_element(By.CSS_SELECTOR, '#tipoPrazoAtoAgrupadoD > label:nth-child(1) > span:nth-child(1) > span:nth-child(1)').click()
        time.sleep(1)
        log(f'Preenchendo prazo: {prazo}')
        # Aguarda até o campo de prazo estar visível antes de interagir
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            campo_prazo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-form-field input[type="text"]'))
            )
            campo_prazo.clear()
            campo_prazo.send_keys(str(prazo))
            log(f'Campo de prazo preenchido com: {campo_prazo.get_attribute("value")}')
        except Exception as e:
            log(f'[ERRO] Não foi possível preencher o campo de prazo: {e}')
            return False
        time.sleep(1)
        log('Clicando em .fa-edit')
        driver.find_element(By.CSS_SELECTOR, '.fa-edit').click()
        time.sleep(1)
        log('Focando em Elaboração do ato de comunicação')
        div_ato = driver.find_element(By.CSS_SELECTOR, 'div.pec-item-dialogo-ato:nth-child(2)')
        div_ato.click()
        time.sleep(1)
        log('Criando GIGS inicial (0/Pz - Pec Verificar)')
        from Fix import criar_gigs
        criar_gigs(driver, dias_uteis=0, observacao='Pz - Pec Verificar', tela='principal', log=True)
        time.sleep(1)
        if gigs_extra:
            log(f'Criando GIGS extra: {gigs_extra}')
            criar_gigs(driver, dias_uteis=gigs_extra[0], observacao=gigs_extra[1], tela='principal', log=True)
            time.sleep(1)
        log('TAB real - 0.5s - seta para baixo - 0.5s - ENTER real - TAB real')
        campo = driver.switch_to.active_element
        campo.send_keys(Keys.TAB)
        time.sleep(0.5)
        campo.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        campo.send_keys(Keys.ENTER)
        campo.send_keys(Keys.TAB)
        time.sleep(1)
        log(f'Digitando nome da comunicação: {nome_comunicacao}')
        campo_nome = driver.switch_to.active_element
        campo_nome.send_keys(nome_comunicacao)
        time.sleep(1)
        log(f'Sigilo: {"Sim" if sigilo else "Não"}')
        if sigilo:
            driver.find_element(By.CSS_SELECTOR, '.mat-slide-toggle-thumb').click()
            time.sleep(1)
        log('Clicando em #inputFiltro')
        driver.find_element(By.CSS_SELECTOR, '#inputFiltro').click()
        time.sleep(1)
        log(f'Digitando modelo: {modelo_nome}')
        campo_filtro = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro.clear()
        campo_filtro.send_keys(modelo_nome)
        time.sleep(1)
        log('Clicando no nodo filtrado')
        driver.find_element(By.CSS_SELECTOR, '.nodo-filtrado > span:nth-child(1)').click()
        time.sleep(1)
        log('Aguardando caixa carregar e clicando em inserir')
        dialogo = driver.find_element(By.CSS_SELECTOR, '#mat-dialog')
        btn_inserir = dialogo.find_element(By.CSS_SELECTOR, '.div-botao-inserir > button:nth-child(1)')
        btn_inserir.click()
        time.sleep(1)
        log('Clicando em salvar e depois em .fa-pen-nib')
        btn_salvar = driver.find_element(By.CSS_SELECTOR, '.button.mat-focus-indicator:nth-child(4)')
        btn_salvar.click()
        time.sleep(1)
        driver.find_element(By.CSS_SELECTOR, '.fa-pen-nib').click()
        time.sleep(1)
        log('De volta à tela de minutas')
        log('Clicando no boneco laranja (polo passivo)')
        btn_boneco = driver.find_element(By.CSS_SELECTOR, 'mat-panel-title.ng-tns-c157-42 > div:nth-child(1) > div:nth-child(1) > button:nth-child(1)')
        btn_boneco.click()
        time.sleep(1)
        log('Clicando em salvar (final)')
        btn_salvar_final = driver.find_element(By.CSS_SELECTOR, 'div.pec-item-botoes-acoes-expedientes:nth-child(2) > button:nth-child(1)')
        btn_salvar_final.click()
        time.sleep(1)
        log('Fluxo de comunicação finalizado.')
        return True
    except Exception as e:
        print(f'[COMUNICACAO][ERRO] {e}')
        return False

# Aqui você poderá criar wrappers para cada tipo de comunicação, ex:
# def comunicacao_intimacao(driver, debug=False):
#     return comunicacao_judicial(driver, tipo_expediente='Intimação', prazo=5, nome_comunicacao='Intimação', sigilo=False, modelo_nome='modelo_intimacao', gigs_extra=None, debug=debug)

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
        nome_comunicacao='Mandado',
        sigilo=False,
        modelo_nome='mdd cp geral',
        gigs_extra=None,
        debug=debug
    )