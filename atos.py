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
    preencher_campos_prazo,)
from modulo import aplicar_filtro_100
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import logging
import time

logger = logging.getLogger(__name__)

# ====================================================
# BLOCO 1 - ATOS JUDICIAIS PADRÃO (Wrappers)
# ====================================================
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


def ato_judicial(driver, nome_ato, filtro_modelo, seletor_btn_ato=None, seletor_item_filtrado='.nodo-filtrado', seletor_btn_inserir='pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button', seletor_btn_enviar='.fa-angle-right', preencher_prazos=True, campos_personalizados=None, seletor_btn_gravar='.botao-salvar', ajuste_pos_inserir=None):
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
        # Espera robusta: só segue se a URL mudar para /minutar
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            print(f'[ATO][ERRO] URL inesperada após {nome_ato}: {driver.current_url}')
            return
        print(f'[ATO] URL correta após {nome_ato}: {driver.current_url}')
        # Espera robusta: aguarda sumir spinner/carregamento
        esperar_elemento(driver, '#inputFiltro', timeout=20)
        # 2. Filtro do modelo
        campo_filtro = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        campo_filtro.clear()
        campo_filtro.send_keys(filtro_modelo)
        campo_filtro.send_keys(Keys.ENTER)
        print(f'[ATO] "{filtro_modelo}" digitado e ENTER pressionado no filtro.')
        # Espera robusta: aguarda nodo filtrado aparecer
        nodo = esperar_nodo_filtrado(driver, seletor=seletor_item_filtrado)
        if not nodo:
            print('[ATO][ERRO] Nodo do modelo não encontrado!')
            return
        nodo.click()
        print('[ATO] Clique em nodo-filtrado realizado!')
        # Espera robusta: aguarda dialogo abrir
        dialogo = esperar_dialogo_mat(driver)
        if not dialogo:
            print('[ATO][ERRO] Dialogo do modelo não encontrado!')
            return
        try:
            log('Aguardando caixa carregar e clicando em inserir')
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            btn_inserir = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.div-botao-inserir > button'))
            )
            btn_inserir.click()
            time.sleep(1)
            print('[ATO] Clique no botão de inserir modelo realizado!')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível clicar no botão de inserir modelo: {e}')
            return
        # Espera robusta: aguarda dialogo sumir
        if not esperar_dialogo_mat_sumir(driver):
            print('[ATO][ERRO] O mat-dialog não sumiu após inserir modelo.')
            return
        print('[ATO] Caixa de diálogo fechada, prosseguindo.')
        time.sleep(0.5)
        # Espera botão enviar
        btn_enviar = esperar_elemento(driver, seletor_btn_enviar, timeout=10)
        if not btn_enviar:
            print('[ATO][ERRO] Botão de enviar não encontrado!')
            return
        btn_enviar.click()
        print('[ATO] Clique em enviar realizado!')
        # Espera robusta: aguarda sumir spinner após enviar
        time.sleep(1)
        # Preenchimento de prazos e campos personalizados
        if preencher_prazos:
            print('[ATO] Preenchendo campos de prazo com 0...')
            preencher_prazo_minuta_zero(driver)
        if campos_personalizados:
            campos_personalizados(driver)
        # Espera botão gravar habilitado
        try:
            btn_salvar = esperar_elemento(driver, seletor_btn_gravar, timeout=15)
            for _ in range(10):
                if btn_salvar and btn_salvar.is_displayed() and btn_salvar.is_enabled():
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
        # Campo de modelo
        log(f'Digitando modelo: {modelo_nome}')
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        campo_filtro = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '#inputFiltro'))
        )
        time.sleep(0.5)  # Delay extra para garantir renderização
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo_filtro)
        time.sleep(0.2)
        campo_filtro.clear()
        campo_filtro.send_keys(modelo_nome)
        campo_filtro.send_keys(Keys.ENTER)
        time.sleep(0.5)  # Pequena pausa para garantir atualização do DOM
        from selenium.webdriver.support.ui import WebDriverWait
        nodo = WebDriverWait(driver, 10).until(
            lambda d: next((el for el in d.find_elements(By.CSS_SELECTOR, '.nodo-filtrado') if el.is_displayed()), None)
        )
        nodo.click()
        time.sleep(1)
        log('Aguardando caixa carregar e clicando em inserir')
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
                log(f'[ERRO] Não foi possível clicar em .fa-pen-nib: {e}')
            # Após .fa-pen-nib, se estiver em /minutas, fecha a aba
            if '/minutas' in driver.current_url:
                try:
                    driver.close()
                except Exception as e:
                    log(f'[WARN] Erro ao fechar aba de minutas: {e}')
                if aba_origem in driver.window_handles:
                    try:
                        driver.switch_to.window(aba_origem)
                    except Exception as e:
                        log(f'[ERRO] Não foi possível voltar para aba original: {e}')
                else:
                    log('[ERRO] Aba original não está mais disponível após fechar minutas.')
            log('Comunicação processual finalizada.')
            return True
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em salvar: {e}')
            return False
        # Após inserir modelo, clicar em .fa-pen-nib para fechar a caixa de diálogo
        try:
            log('Clicando em .fa-pen-nib para finalizar comunicação')
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            btn_pen_nib = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.fa-pen-nib'))
            )
            btn_pen_nib.click()
            time.sleep(1)
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em .fa-pen-nib: {e}')
            return False
        # Agora estamos em /minutas: clicar em .pec-polo-passivo-partes-processo
        try:
            log('Clicando em .pec-polo-passivo-partes-processo')
            btn_polo_passivo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.pec-polo-passivo-partes-processo'))
            )
            btn_polo_passivo.click()
            time.sleep(1)
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em .pec-polo-passivo-partes-processo: {e}')
            return False
        # Clicar no botão Salvar (span com texto Salvar)
        try:
            log('Clicando no botão Salvar em /minutas')
            btn_salvar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and contains(text(), 'Salvar')]/parent::button"))
            )
            btn_salvar.click()
            time.sleep(1)
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar no botão Salvar em /minutas: {e}')
            return False
        # Fechar a aba de minutas e voltar para a original
        try:
            log('Fechando aba de minutas e voltando para a original')
            driver.close()
            if aba_origem in driver.window_handles:
                driver.switch_to.window(aba_origem)
            else:
                driver.switch_to.window(driver.window_handles[0])
            log('Comunicação processual finalizada.')
            return True
        except Exception as e:
            log(f'[ERRO] Não foi possível fechar a aba de minutas ou voltar para a original: {e}')
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
    Percorre a lista filtrada e loga o número do processo e o TERMO após 'xs pec' na coluna Observações.
    Exemplo: se Observações = 'xs pec decisao', registra 'decisao'.
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
        from Fix import extrair_xs_pec_atividades
        print('[DEBUG] Buscando termos xs pec nas atividades...')
        resultados = extrair_xs_pec_atividades(driver, log=True)
        if not resultados:
            print('[PROCESSO][ERRO] Nenhum termo "xs pec" encontrado nas atividades')
            criar_gigs(driver, 0, 'pz pec', tela='detalhe', log=True)
            print('[DEBUG] callback_processo finalizado (sem xs pec)', flush=True)
            return True
        texto = resultados[0].lower()
        import re
        m = re.search(r'xs pec[\s\+]+([\w-]+)', texto)
        if m:
            termo = m.group(1).strip()
            print(f'[PROCESSO][EXTRAIDO] Termo após "xs pec": {termo}')
        else:
            print(f'[PROCESSO][ERRO CRÍTICO] Não foi possível extrair o termo após "xs pec". Texto encontrado: {texto}')
            criar_gigs(driver, 0, 'pz pec', tela='detalhe', log=True)
            print('[DEBUG] callback_processo finalizado (erro extração termo)', flush=True)
            return True
        # Aguarda possíveis carregamentos antes de seguir
        time.sleep(0.5)
        pec_termo(driver, termo)
        print('[DEBUG] callback_processo finalizado com sucesso', flush=True)
        return True
    except Exception as e:
        print(f'[PROCESSO][ERRO] Erro no callback: {str(e)}')
        # Espera curta para evitar atropelamento em caso de erro
        time.sleep(0.5)
        return True

def fluxo_sincrono_processo(driver):
    print('[FLUXO] Iniciando processamento síncrono do processo', flush=True)
    from Fix import extrair_xs_pec_atividades
    import re
    try:
        criar_gigs(driver, 0, 'pz pec', tela='detalhe', log=True)
        resultados = extrair_xs_pec_atividades(driver, log=True)
        if not resultados:
            print('[FLUXO] Nenhum termo "xs pec" encontrado. Fechando processo.')
            if len(driver.window_handles) > 1:
                try:
                    driver.close()
                    print('[FLUXO] Aba do processo fechada (nenhum xs pec).')
                except Exception as e:
                    print(f'[FLUXO][WARN] Erro ao fechar aba: {e}')
            else:
                print('[FLUXO] Só existe uma aba aberta, não será fechada.')
            time.sleep(1)
            return True
        texto = resultados[0].lower()
        m = re.search(r'xs pec[\s\+]+([\w-]+)', texto)
        if m:
            termo = m.group(1).strip()
            print(f'[FLUXO] Termo extraído: {termo}')
            func_name = f'pec_{termo.lower()}'
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
            print(f'[FLUXO] Não foi possível extrair termo após "xs pec". Nenhuma ação extra.')
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
        # Aplica filtro xs pec no campo correto
        campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Descrição"]')
        campo_desc.clear()
        campo_desc.send_keys('xs pec')
        campo_desc.send_keys(Keys.ENTER)
        print('[DEBUG] Filtro xs pec aplicado.')
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