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
    buscar_documentos_sequenciais,
    indexar_e_processar_lista  # <--- Importação adicionada
)
from selenium.webdriver.common.keys import Keys
import os
import logging
import time
from selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By
from driver_config import criar_driver, login_func

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
          # NOVO: Limpa qualquer overlay/modal que possa estar interferindo
        def limpar_overlays():
            try:
                overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                if overlays:
                    print('[CLS][DEBUG] Overlays detectados no início, limpando...')
                    from selenium.webdriver.common.keys import Keys
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
                    # Re-fetch elements to avoid stale reference
                    try:
                        fresh_overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                        for overlay in fresh_overlays:
                            try:
                                if overlay.is_displayed():
                                    driver.execute_script('arguments[0].click();', overlay)
                                    time.sleep(0.2)
                            except:
                                pass
                    except:
                        pass
            except Exception as clean_err:
                print(f'[CLS][DEBUG] Erro na limpeza de overlays: {clean_err}')
        
        limpar_overlays()
        
        # 2. Verifica se já está na URL de conclusão antes de tentar clicar no botão
        current_url = driver.current_url
        if '/conclusao' in current_url:
            print(f'[CLS][INFO] Já está na página de conclusão ({current_url}), pulando clique em "Conclusão ao magistrado"')
        else:
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
                    print(f'[CLS][INFO] Botão "Iniciar execução" não encontrado ou não clicável: {e}')            # 3. Clica no botão 'Conclusão ao Magistrado' usando aria-label
            try:
                btn_conclusao = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                )
                btn_conclusao.click()
                print(f'[CLS][DEBUG] Clique no botão Conclusão ao magistrado realizado. Seletor usado: button[aria-label=\'Conclusão ao magistrado\']')
            except Exception as e:
                print(f'[CLS][ERRO] Falha ao clicar no botão Conclusão ao magistrado por aria-label: {e}')
                print('[CLS][INFO] Tentando fluxo alternativo: Análise → Conclusão ao magistrado')
                
                # Fluxo alternativo para casos como "Cumprimento de Providências"
                try:
                    # Primeiro clica em "Análise"
                    btn_analise = None
                    # Busca por texto
                    btns_analise = driver.find_elements(By.XPATH, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]")
                    for btn in btns_analise:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_analise = btn
                            break
                    
                    if not btn_analise:
                        # Busca por aria-label
                        btns_analise = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Análise']")
                        for btn in btns_analise:
                            if btn.is_displayed() and btn.is_enabled():
                                btn_analise = btn
                                break
                    
                    if btn_analise:
                        btn_analise.click()
                        print('[CLS][DEBUG] Clique no botão "Análise" realizado.')
                        time.sleep(1)
                        
                        # Agora tenta novamente clicar em "Conclusão ao magistrado"
                        btn_conclusao = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                        )
                        btn_conclusao.click()
                        print('[CLS][DEBUG] Clique no botão "Conclusão ao magistrado" realizado após clique em Análise.')
                    else:
                        print('[CLS][ERRO] Botão "Análise" não encontrado no fluxo alternativo.')
                        return False
                        
                except Exception as e_alt:
                    print(f'[CLS][ERRO] Falha no fluxo alternativo (Análise → Conclusão ao magistrado): {e_alt}')
                    return False
        
        time.sleep(1)
        print(f'[CLS][DEBUG] Seletor de clique usado para conclusão: button[aria-label=\'Conclusão ao magistrado\']')

        # 4. Aguarda a URL mudar para /conclusao
        from Fix import esperar_url_conter
        if not esperar_url_conter(driver, '/conclusao', timeout=15):
            print(f'[CLS][ERRO] URL inesperada após clicar em conclusão: {driver.current_url}')
            return False        # 5. Clica no botão do tipo de conclusão priorizando aria-label (contém), com fallback para texto visível (contém)
        print(f'[CLS] Procurando botão de conclusão: {conclusao_tipo}')
        btn_tipo_conclusao = None
        # Primeiro tenta por aria-label que CONTÉM o tipo de conclusão
        btns = driver.find_elements(By.CSS_SELECTOR, f"button[aria-label]")
        for btn in btns:
            aria = btn.get_attribute('aria-label')
            if aria and conclusao_tipo.lower() in aria.lower():
                btn_tipo_conclusao = btn
                break
        if not btn_tipo_conclusao:
            # Fallback: tenta por texto visível (contém)
            xpath_conclusao = f"//button[contains(normalize-space(text()), '{conclusao_tipo}') or .//span[contains(normalize-space(text()), '{conclusao_tipo}')]]"
            btns = driver.find_elements(By.XPATH, xpath_conclusao)
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn_tipo_conclusao = btn
                    break
        if not btn_tipo_conclusao:
            print(f'[CLS][ERRO] Botão de conclusão "{conclusao_tipo}" não encontrado por aria-label nem texto visível.')
            return False
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_tipo_conclusao)
        time.sleep(0.3)
        driver.execute_script('arguments[0].click();', btn_tipo_conclusao)
        print(f'[CLS] Botão de conclusão "{conclusao_tipo}" clicado via JavaScript.')
        time.sleep(1)

        # 6. Aguarda a URL mudar para /minutar
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            print(f'[CLS][ERRO] URL inesperada após clicar em conclusão tipo: {driver.current_url}')
            return False

        # Clique e foco no campo de filtro de modelos ao entrar em /minutar
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            campo_filtro_modelo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '#inputFiltro'))
            )
            # Tenta clicar normalmente
            try:
                campo_filtro_modelo.click()
                print('[CLS][MODELO][OK] Clique direto no campo de filtro de modelos realizado (#inputFiltro).')
                time.sleep(0.3)
            except Exception as e_click:
                print(f'[CLS][MODELO][WARN] Falha ao clicar normalmente: {e_click}. Tentando workarounds JS...')
                # Tenta scrollIntoView e click via JS
                try:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', campo_filtro_modelo)
                    driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
                    driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                    driver.execute_script('arguments[0].click();', campo_filtro_modelo)
                    print('[CLS][MODELO][OK] Clique/foco via JS realizado no campo de filtro de modelos.')
                    time.sleep(0.3)
                except Exception as e_js:
                    print(f'[CLS][MODELO][ERRO] Falha ao clicar/focar via JS: {e_js}')
                    return False
        except Exception as e:
            print(f'[CLS][MODELO][ERRO] Falha ao acessar o campo de filtro de modelos: {e}')
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
        # 1. Preencher campo Descrição se fornecido
        if descricao:
            try:
                # Seletor do campo de descrição conforme gigs-plugin.js para despacho
                campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="descricao"], input[name="descricao"], input[aria-label="Descrição"], input[data-placeholder="Descrição"]')
                campo_desc.clear()
                campo_desc.send_keys(descricao)
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_desc, ev)
            except Exception as e:
                print(f'[ATO][DESCRICAO][WARN] Não foi possível preencher o campo Descrição: {e}')
        # 1. Executa fluxo_cls até o clique/foco no campo de modelo
        if debug: print(f'[ATO] Executando fluxo_cls para {conclusao_tipo}...')
        if not fluxo_cls(driver, conclusao_tipo):
            print(f'[ATO][ERRO] Falha no fluxo_cls para {conclusao_tipo}.')
            return False

        # 2. Digitação do modelo e prosseguimento (padrão MaisPje/gigs-plugin.js)
        from selenium.webdriver.common.by import By
        campo_filtro_modelo = driver.find_element(By.CSS_SELECTOR, '#inputFiltro')
        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
        driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo_nome)
        # Dispara eventos como no gigs-plugin.js
        for ev in ['input', 'change', 'keyup']:
            driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
        # Simula Enter
        from selenium.webdriver.common.keys import Keys
        campo_filtro_modelo.send_keys(Keys.ENTER)
        print(f'[ATO][MODELO][OK] Modelo "{modelo_nome}" preenchido via JS e ENTER pressionado no filtro.')
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
            ativar_sigilo = str(sigilo).lower() in ("sim", "true", "1")
            if ativar_sigilo:
                # Busca todos os mat-slide-toggle e procura o que tem texto 'Sigiloso' próximo
                toggles = driver.find_elements(By.CSS_SELECTOR, 'mat-slide-toggle')
                sigilo_toggle = None
                sigilo_input = None
                for toggle in toggles:
                    try:
                        # Verifica se o texto 'Sigiloso' está no label, no próprio toggle ou em elementos próximos
                        label_text = ''
                        try:
                            label = toggle.find_element(By.CSS_SELECTOR, 'label')
                            label_text = label.text.strip().lower()
                        except:
                            pass
                        # Também verifica texto do próprio toggle
                        toggle_text = toggle.text.strip().lower()
                        # Verifica irmãos próximos (ex: span, div)
                        sibling_text = ''
                        try:
                            parent = toggle.find_element(By.XPATH, '..')
                            siblings = parent.find_elements(By.XPATH, './*')
                            for sib in siblings:
                                if sib != toggle:
                                    sibling_text += sib.text.strip().lower() + ' '
                        except:
                            pass
                        if 'sigiloso' in label_text or 'sigiloso' in toggle_text or 'sigiloso' in sibling_text:
                            sigilo_toggle = toggle
                            try:
                                sigilo_input = toggle.find_element(By.CSS_SELECTOR, 'input[type="checkbox"], input.mat-slide-toggle-input')
                            except:
                                sigilo_input = None
                            break
                    except Exception as e:
                        print(f'[ATO][SIGILO][DEBUG] Erro ao inspecionar toggle: {e}')
                checked = False
                if sigilo_input:
                    checked = sigilo_input.get_attribute('aria-checked') == 'true' or sigilo_input.is_selected() or sigilo_input.get_attribute('checked') == 'true'
                # Se não está ativado, tenta clicar
                if not checked and sigilo_toggle:
                    try:
                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', sigilo_toggle)
                        driver.execute_script('arguments[0].click();', sigilo_toggle)
                        time.sleep(0.3)
                        # Rebusca input para checar estado
                        if sigilo_input:
                            checked = sigilo_input.get_attribute('aria-checked') == 'true' or sigilo_input.is_selected() or sigilo_input.get_attribute('checked') == 'true'
                        if checked:
                            sigilo_ativado = True
                            print('[ATO][SIGILO][DEBUG] Sigilo ativado por toggle associado ao texto Sigiloso.')
                        else:
                            print('[ATO][SIGILO][ERRO] Não foi possível ativar o sigilo (toggle não marcou).')
                    except Exception as e:
                        print(f'[ATO][SIGILO][ERRO] Falha ao clicar no toggle de sigilo: {e}')
                elif checked:
                    sigilo_ativado = True
                    print('[ATO][SIGILO][DEBUG] Sigilo já estava ativado.')
                else:
                    print('[ATO][SIGILO][ERRO] Não foi possível localizar toggle de sigilo associado ao texto Sigiloso.')
            else:
                print(f'[ATO][SIGILO][DEBUG] Sigilo não solicitado. Nenhuma ação.')
        except Exception as e:
            print(f'[ATO][ERRO] Não foi possível ajustar Sigilo: {e}')
        # 2. PEC
        print('[ATO][DEBUG] Etapa: PEC')
        if marcar_pec is not None:
            try:
                # Busca primeiro o mat-checkbox container usando múltiplos seletores
                pec_checkbox = None
                pec_input = None
                
                # Tenta encontrar o mat-checkbox pelo aria-label
                try:
                    pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]')
                    pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                except:
                    # Fallback: busca pela div container e depois o mat-checkbox
                    try:
                        pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'div.checkbox-pec mat-checkbox')
                        pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    except:
                        # Último fallback: busca diretamente pelo input
                        pec_input = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Enviar para PEC"]')
                        pec_checkbox = pec_input.find_element(By.XPATH, './ancestor::mat-checkbox[1]')
                
                if not pec_checkbox or not pec_input:
                    raise Exception("Não foi possível localizar o checkbox PEC")
                
                # Verifica estado atual do checkbox usando múltiplos métodos
                checked = False
                try:
                    # Método 1: aria-checked
                    aria_checked = pec_input.get_attribute('aria-checked')
                    if aria_checked == 'true':
                        checked = True
                    # Método 2: propriedade checked
                    elif pec_input.get_attribute('checked') == 'true':
                        checked = True
                    # Método 3: is_selected()
                    elif pec_input.is_selected():
                        checked = True
                    # Método 4: verificar classes CSS do mat-checkbox
                    elif 'mat-checkbox-checked' in pec_checkbox.get_attribute('class'):
                        checked = True
                except Exception as state_err:
                    print(f'[ATO][PEC][WARN] Erro ao verificar estado do checkbox: {state_err}')
                    # Em caso de erro, assume desmarcado
                    checked = False
                
                print(f'[ATO][PEC][DEBUG] Estado atual da caixa PEC: {"marcada" if checked else "desmarcada"}. Parâmetro marcar_pec: {marcar_pec}')
                
                # Executa ação baseada no estado e parâmetro
                if marcar_pec and not checked:
                    # Precisa marcar - clica no label ou mat-checkbox
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                    time.sleep(0.2)
                    # Tenta clicar no label primeiro (mais confiável)
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        driver.execute_script('arguments[0].click();', label)
                    except:
                        # Fallback: clica no mat-checkbox
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    print('[ATO][PEC][DEBUG] Caixa PEC estava desmarcada e foi marcada.')
                    time.sleep(0.3)
                elif not marcar_pec and checked:
                    # Precisa desmarcar - clica no label ou mat-checkbox
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                    time.sleep(0.2)
                    # Tenta clicar no label primeiro (mais confiável)
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        driver.execute_script('arguments[0].click();', label)
                    except:
                        # Fallback: clica no mat-checkbox
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    print('[ATO][PEC][DEBUG] Caixa PEC estava marcada e foi desmarcada.')
                    time.sleep(0.3)
                else:
                    print('[ATO][PEC][DEBUG] Nenhuma ação necessária na caixa PEC.')
                    
            except Exception as e:
                print(f'[ATO][ERRO] Não foi possível ajustar PEC: {e}')
                # Log adicional para debug
                try:
                    print(f'[ATO][PEC][DEBUG] URL atual: {driver.current_url}')
                    checkboxes = driver.find_elements(By.CSS_SELECTOR, 'mat-checkbox')
                    print(f'[ATO][PEC][DEBUG] Encontrados {len(checkboxes)} mat-checkbox na página')
                except:
                    pass

        # 3. Prazo
        print('[ATO][DEBUG] Etapa: Prazo')
        if prazo is not None:
            try:
                print('[ATO][PRAZO][DEBUG] Chamando preencher_prazos_destinatarios...')
                preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario)
                # NOVO: Clica no botão Gravar após preencher prazos (ajustado para o label visível)
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                btn_gravar_prazo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button') and not(contains(@aria-label, 'movimentos'))]"))
                )
                print('[ATO][PRAZO][LOG] Botão Gravar (prazo) localizado, clicando...')
                btn_gravar_prazo.click()
                print('[ATO][PRAZO][OK] Botão Gravar (prazo) clicado.')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][PRAZO][ERRO] Falha inesperada ao preencher prazos ou clicar em Gravar: {e}')
                return False
        else:
            print('[ATO][PRAZO][DEBUG] Nenhum prazo informado, etapa ignorada.')
               # 4. Movimento
        print('[ATO][DEBUG] Etapa: Movimento')
        if movimento:
            try:
                print(f'[ATO][MOVIMENTO][DEBUG] Parâmetro movimento recebido: {movimento!r}')
                # 1. JavaScript para ativar a aba Movimentos e selecionar o checkbox correto
                js_mov = f'''
                (function() {{
                    // Ativa a aba "Movimentos"
                    var tentativas = 0, abaMov = null;
                    while (tentativas < 3 && !abaMov) {{
                        var abas = Array.from(document.querySelectorAll('.mat-tab-label'));
                        abaMov = abas.find(a => a.textContent && a.textContent.normalize('NFD').replace(/[\\W_]/g, '').toLowerCase().includes('movimentos'));
                        if (abaMov && abaMov.getAttribute('aria-selected') !== 'true') {{
                            abaMov.click();
                            break;
                        }}
                        tentativas++;
                    }}
                    
                    setTimeout(function() {{
                        var textoMov = '{movimento}'.trim().toLowerCase().replace(/\\s+/g, ' ');
                        var checkboxes = Array.from(document.querySelectorAll('mat-checkbox.mat-checkbox.movimento'));
                        var selecionado = false;
                        
                        // Método mais flexível - não depende de mapeamento fixo
                        // Normaliza o texto para busca (remove acentos, etc.)
                        function normalizarTexto(texto) {{
                            return texto.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
                        }}
                        
                        var termoPesquisa = normalizarTexto(textoMov);
                        console.log('[ATO][MOVIMENTO][JS][DEBUG] Termo de pesquisa normalizado:', termoPesquisa);
                          
                        for (var cb of checkboxes) {{
                            try {{
                                var label = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                var labelText = label && label.textContent ? label.textContent : '';
                                var labelNorm = labelText.trim().toLowerCase().replace(/\\s+/g, ' ');
                                var labelSemAcento = normalizarTexto(labelText);
                                
                                // DEBUG: log do label de cada movimento
                                console.log('[ATO][MOVIMENTO][JS][DEBUG] labelNorm:', labelNorm);
                                console.log('[ATO][MOVIMENTO][JS][DEBUG] labelSemAcento:', labelSemAcento);
                                
                                // Busca flexível - verifica se o termo pesquisado está contido no texto do checkbox
                                // Tenta diferentes variações de normalização para aumentar chances de match
                                var encontrado = labelNorm.includes(textoMov) || 
                                                labelSemAcento.includes(termoPesquisa) ||
                                                // Busca específica para "frustrada"/"execução frustrada"
                                                (textoMov === 'frustrada' && (labelSemAcento.includes('execucao frustrada') || labelSemAcento.includes('276'))) ||
                                                // Busca por código numérico entre parênteses, se for um número
                                                (textoMov.match(/^\\d+$/) && labelText.includes('(' + textoMov + ')'));
                                
                                if (encontrado) {{
                                    console.log('[ATO][MOVIMENTO][JS][DEBUG] Encontrado movimento correspondente para:', textoMov);
                                    var input = cb.querySelector('input[type="checkbox"]');
                                    // DEBUG: log do input encontrado
                                    console.log('[ATO][MOVIMENTO][JS][DEBUG] input encontrado:', input);
                                    if (input && !input.checked) {{
                                        // Tenta clicar na inner-container (mais confiável)
                                        var inner = cb.querySelector('.mat-checkbox-inner-container');
                                        if(inner) {{
                                            inner.click();
                                            console.log('[ATO][MOVIMENTO][JS][DEBUG] inner-container clicado para:', labelNorm);
                                        }} else {{
                                            input.click();
                                            console.log('[ATO][MOVIMENTO][JS][DEBUG] input clicado para:', labelNorm);
                                        }}
                                    }} else if (input && input.checked) {{
                                        console.log('[ATO][MOVIMENTO][JS][DEBUG] Checkbox já estava marcado:', labelNorm);
                                    }}
                                    window.selecionadoMovimento = true;  // Sinaliza para o Python que o checkbox foi encontrado
                                    window.labelSelecionadoMovimento = labelText;  // Guarda o texto do label selecionado
                                    selecionado = true;
                                    break;
                                }}
                            }} catch (e) {{
                                console.warn('[ATO][MOVIMENTO][JS][CATCH] Erro ao processar checkbox:', e);
                            }}
                        }}
                        
                        if (!selecionado) {{
                            console.warn('[ATO][MOVIMENTO][JS] Movimento "' + textoMov + '" não encontrado na lista de checkboxes.');
                            window.selecionadoMovimento = false;
                            
                            // Diagnóstico detalhado com sugestões de possíveis matches parciais
                            console.warn('[ATO][MOVIMENTO][JS][DIAGNÓSTICO] Listando todos os movimentos disponíveis:');
                            var possivelMatch = [];
                            
                            for (var idx = 0; idx < checkboxes.length; idx++) {{
                                try {{
                                    var cb = checkboxes[idx];
                                    var lbl = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                    var labelText = lbl ? lbl.textContent : 'sem label';
                                    console.warn('[ATO][MOVIMENTO][JS][DIAGNÓSTICO] [' + idx + '] ' + labelText);
                                    
                                    // Tenta identificar possíveis matches parciais para sugerir
                                    var normLabel = normalizarTexto(labelText);
                                    var palavrasTermoPesquisa = termoPesquisa.split(/\\s+/);
                                    
                                    // Conta quantas palavras do termo de pesquisa estão na label
                                    var matchCount = 0;
                                    for (var p of palavrasTermoPesquisa) {{
                                        if (p.length > 2 && normLabel.includes(p)) {{ // Ignora palavras muito curtas
                                            matchCount++;
                                        }}
                                    }}
                                    
                                    if (matchCount > 0) {{
                                        possivelMatch.push({{
                                            index: idx,
                                            label: labelText,
                                            matchCount: matchCount,
                                            matchPercentage: (matchCount / palavrasTermoPesquisa.length) * 100
                                        }});
                                    }}
                                }} catch(e) {{
                                    console.warn('[ATO][MOVIMENTO][JS][DIAGNÓSTICO] [' + idx + '] Erro ao ler: ' + e);
                                }}
                            }}
                            
                            // Ordena por quantidade de matches e mostra as melhores sugestões
                            if (possivelMatch.length > 0) {{
                                possivelMatch.sort((a, b) => b.matchPercentage - a.matchPercentage);
                                console.warn('[ATO][MOVIMENTO][JS][SUGESTÕES] Possíveis matches parciais:');
                                for (var i = 0; i < Math.min(3, possivelMatch.length); i++) {{
                                    var match = possivelMatch[i];
                                    console.warn('[ATO][MOVIMENTO][JS][SUGESTÃO ' + (i+1) + '] [' + match.index + '] ' + 
                                        match.label + ' (Match: ' + match.matchPercentage.toFixed(1) + '%)');
                                }}
                            }}
                        }} else {{
                            console.log('[ATO][MOVIMENTO][JS] Movimento "' + textoMov + '" marcado com sucesso.');
                        }}
                    }}, 800);
                }})();
                '''
                print('[ATO][MOVIMENTO][DEBUG] Executando JS para marcar movimento...')
                driver.execute_script(js_mov)
                print('[ATO][MOVIMENTO][DEBUG] JS executado. Aguardando efeito...')
                time.sleep(1.5)  # Aguarda o script JS executar
                
                # 2. Verifica se o movimento foi selecionado 
                movimento_selecionado = driver.execute_script('return window.selecionadoMovimento === true;')
                if not movimento_selecionado:
                    print('[ATO][MOVIMENTO][ERRO] Movimento não foi selecionado pelo JavaScript.')
                    return False
                
                print('[ATO][MOVIMENTO][OK] Movimento selecionado com sucesso:', 
                      driver.execute_script('return window.labelSelecionadoMovimento || "desconhecido";'))
                
                # 3. Clica no botão Gravar (para movimentos)
                print('[ATO][MOVIMENTO][DEBUG] Clicando no botão Gravar movimentos...')
                btn_gravar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Gravar os movimentos a serem lançados']"))
                )
                btn_gravar.click()
                print('[ATO][MOVIMENTO][DEBUG] Botão Gravar movimentos clicado. Aguardando diálogo de confirmação...')
                time.sleep(1.5)
                
                # 4. Clica no botão "Sim" na caixa de diálogo de confirmação
                print('[ATO][MOVIMENTO][DEBUG] Clicando em "Sim" na caixa de diálogo de confirmação...')
                btn_sim = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-button') and contains(@class, 'mat-primary') and .//span[text()='Sim']]"))
                )
                btn_sim.click()
                print('[ATO][MOVIMENTO][DEBUG] Botão "Sim" clicado na caixa de diálogo. Aguardando...')
                time.sleep(1)
                
                # 5. Clica no botão Salvar final
                print('[ATO][MOVIMENTO][DEBUG] Clicando no botão Salvar final...')
                btn_salvar_mov = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar'][color='primary']"))
                )
                btn_salvar_mov.click()
                print('[ATO][MOVIMENTO][OK] Botão Salvar final clicado.')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][MOVIMENTO][ERRO] Falha ao executar etapa de movimento: {e}')
                import traceback
                traceback.print_exc()
                # Extra: dumpar checkboxes e abas para depuração
                try:
                    print('[ATO][MOVIMENTO][DEPURACAO] Listando checkboxes de movimento na página:')
                    checkboxes = driver.find_elements(By.CSS_SELECTOR, 'mat-checkbox.mat-checkbox.movimento')
                    for idx, cb in enumerate(checkboxes):
                        try:
                            label = cb.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout .mat-checkbox-label').text
                            print(f'  [MOVIMENTO][{idx}] Label: {label!r}')
                        except Exception as ecb:
                            print(f'  [MOVIMENTO][{idx}] Erro ao obter label: {ecb}')
                    print('[ATO][MOVIMENTO][DEPURACAO] Abas disponíveis:')
                    abas = driver.find_elements(By.CSS_SELECTOR, '.mat-tab-label')
                    for idx, aba in enumerate(abas):
                        print(f'  [ABA][{idx}] Texto: {aba.text!r} | aria-selected: {aba.get_attribute("aria-selected")}')
                except Exception as edebug:
                    print(f'[ATO][MOVIMENTO][DEPURACAO][ERRO] Falha ao depurar checkboxes/abas: {edebug}')
                return False

        # 5. GIGS (minuta)
        print('[ATO][DEBUG] Etapa: GIGS')
        if gigs:
            try:
                # Garante que o parâmetro 'tela' seja 'minuta' se a URL contiver '/minutar'
                gigs_args = dict(gigs) if isinstance(gigs, dict) else {}
                if '/minutar' in driver.current_url:
                    gigs_args['tela'] = 'minuta'
                # Remove argumentos inesperados do wrapper
                for k in list(kwargs.keys()):
                    if k not in gigs_args:
                        kwargs.pop(k)
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

def make_ato_wrapper(conclusao_tipo, modelo_nome, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, descricao=None, sigilo=None):
    def wrapper(driver, debug=False, sigilo_=None, movimento_=None, descricao_=None, **kwargs):
        call_args = dict(
            driver=driver,
            conclusao_tipo=conclusao_tipo,
            modelo_nome=modelo_nome,
            prazo=prazo,
            marcar_pec=marcar_pec,
            movimento=movimento_ if movimento_ is not None else movimento,
            gigs=gigs,
            marcar_primeiro_destinatario=marcar_primeiro_destinatario,
            debug=debug,
            sigilo=sigilo_ if sigilo_ is not None else sigilo,
            descricao=descricao_ if descricao_ is not None else descricao
        )
        return ato_judicial(**call_args)
    return wrapper

# Wrappers gerados automaticamente
ato_meios = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsmeios',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_crda = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='a reclda',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_crte = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xreit',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_bloq = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsparcial',
    prazo=None,
    marcar_pec=True,
    movimento=None,
    gigs="1/SILAS/pec bloq",
    marcar_primeiro_destinatario=False
)

ato_idpj = make_ato_wrapper(
    conclusao_tipo='IDPJ',
    modelo_nome='pjsem',
    prazo=8,
    marcar_pec=True,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_termoE = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xempre',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_termoS = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsocio',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_edital = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xsedit',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True
)

ato_sobrestamento = make_ato_wrapper(
    conclusao_tipo='Suspensão',
    modelo_nome='suspf',
    prazo=0,
    marcar_pec=False,
    movimento='frustrada',
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_180 = make_ato_wrapper(
    conclusao_tipo='Sobrestamento',
    modelo_nome='x180',
    prazo=0,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

ato_pesqliq = make_ato_wrapper(
    conclusao_tipo='Homologação de Cálculos',
    modelo_nome='xsbacen',
    prazo=30,
    marcar_pec=True,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='pesquisas para execucao',
    sigilo=True
)

# NOVO WRAPPER: ato_calc2
ato_calc2 = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xscalc2',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False
)

# ato_pesquisas permanece manual, pois tem lógica própria
# ato_pesquisas permanece manual, pois tem lógica própria
def ato_pesquisas(driver, conclusao_tipo=None, modelo_nome=None, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, debug=False, sigilo=True, descricao=None):
    # Wrapper de pesquisa: prazo 30 apenas para o primeiro destinatário
    resultado = ato_judicial(
        driver=driver,
        conclusao_tipo=conclusao_tipo or 'BNDT',
        modelo_nome=modelo_nome or 'xsbacen',
        prazo=30,  # sempre 30 para o primeiro destinatário
        marcar_pec=marcar_pec if marcar_pec is not None else True,
        movimento=movimento or 'bloqueio',
        gigs=gigs if gigs is not None else None,
        marcar_primeiro_destinatario=True,  # só o primeiro
        debug=debug,
        sigilo=True,
        descricao=descricao
    )
    from Fix import visibilidade_sigilosos
    visibilidade_sigilosos(driver, polo='ativo', log=debug)
    return resultado

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
        # 3. Clicar no botão de Comunicações e expedientes (fa-envelope) - abordagem robusta igual fluxo_cls
        log('[DEBUG] Buscando botão de Comunicações e expedientes (robusto)...')
        btn_comunic = None
        # 1. Por aria-label que contenha "Comunica"
        btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
        for btn in btns:
            aria = btn.get_attribute('aria-label')
            if aria and 'comunica' in aria.lower():
                if btn.is_displayed() and btn.is_enabled():
                    btn_comunic = btn
                    break
        # 2. Por texto visível (span ou button)
        if not btn_comunic:
            btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'analise')]]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn_comunic = btn
                    break
        # 3. Por mattooltip
        if not btn_comunic:
            btns = driver.find_elements(By.CSS_SELECTOR, "button[mattooltip]")
            for btn in btns:
                tip = btn.get_attribute('mattooltip')
                if tip and 'comunica' in tip.lower():
                    if btn.is_displayed() and btn.is_enabled():
                        btn_comunic = btn
                        break        
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
            except Exception as e:                log(f'[WARN] Erro ao tentar clicar em "Análise": {e}')
            # Tenta novamente buscar o botão de comunicações de forma similar à busca anterior
            # (redefinimos a lógica de busca em vez de chamar uma função inexistente)
            btn_comunic = None
            # 1. Por aria-label que contenha "Comunica"
            btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
            for btn in btns:
                aria = btn.get_attribute('aria-label')
                if aria and 'comunica' in aria.lower():
                    if btn.is_displayed() and btn.is_enabled():
                        btn_comunic = btn
                        break
            # 2. Por texto visível (span ou button)
            if not btn_comunic:
                btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'comunicacoes')]]")
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_comunic = btn
                        break
            # 3. Por mattooltip
            if not btn_comunic:
                btns = driver.find_elements(By.CSS_SELECTOR, "button[mattooltip]")
                for btn in btns:
                    tip = btn.get_attribute('mattooltip')
                    if tip and 'comunica' in tip.lower():
                        if btn.is_displayed() and btn.is_enabled():
                            btn_comunic = btn
                            break
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
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Magistrado"]')
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
                if span.isDisplayed():
                    time.sleep(0.3)
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
# BLOCO 3 - MOVIMENTOS (importado de mov.py)
# ====================================================
import logging
import time
from Fix import esperar_elemento, safe_click
from selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def mov(driver, seletor_alvo, texto_confirmacao=None, debug=False, timeout=15):
    """
    Fluxo geral para movimentos:
    1. Clica no botão "Abrir tarefa do processo" (BTN_TAREFA_PROCESSO)
    2. Troca para nova aba, se aberta
    3. Procura o botão alvo (seletor_alvo)
       - Se não encontrar, clica em "Análise" e tenta novamente
    4. Clica no botão alvo
    5. (Opcional) Confirma ação se texto_confirmacao for fornecido
    """
    try:
        print(f'[MOV][DEBUG] Iniciando fluxo de movimento para seletor: {seletor_alvo}')
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if not btn_abrir_tarefa:
            print('[MOV][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
            return False
        abas_antes = set(driver.window_handles)
        safe_click(driver, btn_abrir_tarefa)
        print('[MOV] Botão "Abrir tarefa do processo" clicado.')
        # Troca para nova aba, se aberta
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
            print('[MOV] Foco trocado para nova aba da tarefa do processo.')
        else:
            print('[MOV][WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # Procura botão alvo
        try:
            btn_alvo = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
            )
            safe_click(driver, btn_alvo)
            print(f'[MOV] Botão alvo ({seletor_alvo}) clicado.')
        except Exception:
            # Tenta clicar em "Análise" e tenta novamente
            print('[MOV][INFO] Botão alvo não encontrado. Tentando clicar em "Análise" e tentar novamente...')
            btn_analise = None
            # Busca por texto
            btns_analise = driver.find_elements(By.XPATH, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]")
            for btn in btns_analise:
                if btn.is_displayed() and btn.is_enabled():
                    btn_analise = btn
                    break
            if not btn_analise:
                btns_analise = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Análise']")
                for btn in btns_analise:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_analise = btn
                        break
            if btn_analise:
                btn_analise.click()
                print('[MOV][DEBUG] Clique no botão "Análise" realizado.')
                time.sleep(1)
                btn_alvo = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
                )
                safe_click(driver, btn_alvo)
                print(f'[MOV] Botão alvo ({seletor_alvo}) clicado após "Análise".')
            else:
                print('[MOV][ERRO] Botão "Análise" não encontrado no fluxo alternativo.')
                return False
        # Confirmação extra se necessário
        if texto_confirmacao:
            try:
                btn_confirma = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"))
                )
                btn_confirma.click()
                print(f'[MOV] Botão de confirmação "{texto_confirmacao}" clicado.')
            except Exception as e:
                print(f'[MOV][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                return False
        print('[MOV] Fluxo de movimento finalizado com sucesso.')
        return True
    except Exception as e:
        print(f'[MOV][ERRO] Falha no fluxo de movimento: {e}')
        return False

# Wrappers para movimentos específicos

def mov_arquivar(driver, debug=False):
    """Movimento: Arquivar o processo"""
    return mov(driver, "button[aria-label='Arquivar o processo']", debug=debug)

def mov_exec(driver, debug=False):
    """Movimento: Iniciar execução"""
    return mov(driver, "button[aria-label='Iniciar execução']", debug=debug)

# ====================================================
# BLOCO 4 - FLUXOS DE EXECUÇÃO E AUXILIARES
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
        if not login_func(driver, usuario, senha):
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
            # CORRIGIDO: Selenium Python usa get_attribute, não getAttribute
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
            input_prazo.clear()
            input_prazo.send_keys(str(prazo))
            print(f'[ATO][PRAZO][OK] Preenchido prazo {prazo} para destinatário.')
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao preencher prazo: {e}')
    return True