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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def selecionar_opcao_select(driver, seletor, texto_opcao, timeout=10):
    """Seleciona uma opção em um mat-select de forma robusta, simulando o padrão do gigs-plugin.js."""
    select = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
    )
    select.send_keys(Keys.ENTER)
    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-option'))
    )
    opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
    for opcao in opcoes:
        if texto_opcao.lower() in opcao.text.lower():
            opcao.click()
            return True
    raise Exception(f'Opção "{texto_opcao}" não encontrada em {seletor}!')

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
    from selenium.webdriver.common.keys import Keys
    """
    Refatorado fluxo geral para CLS (movimentação de minuta):
    1. Clica no botão 'Abrir tarefa do processo' (seletor robusto mattooltip).
    2. Se estiver em 'Cumprimento de Providências', clica em 'Análise' primeiro.
    3. Clica em 'Conclusão ao Magistrado' (se não estiver já na tela de conclusão).
    4. Clica no botão do tipo de conclusão especificado.
    Retorna True em caso de sucesso, False em caso de falha.
    """
    try:
        # NOTA: A identificação da tarefa atual é feita de forma mais robusta
        # diretamente do botão "Abrir tarefa do processo" durante o clique.
        # A verificação prévia abaixo foi mantida para referência, mas pode ser removida
        # após validação em produção.
        
        """
        # 1. Verifica a tarefa atual usando seletores específicos (MÉTODO ANTIGO - PODE SER REMOVIDO)
        seletores_tarefa = [
            'pje-cabecalho-tarefa .texto-tarefa-processo',  # Novo padrão do cabeçalho
            '.descricao-tarefa button .texto-tarefa-processo',  # Estrutura completa
            'span.texto-tarefa-processo',  # Seletor simples
            'button[mattooltip="Abre a tarefa do processo"]',  # Via tooltip
            'button[aria-label*="tarefa"]'  # Via aria-label
        ]
        
        tarefa_atual = None
        seletor_funcionou = None
        print('[CLS] Testando seletores para identificar tarefa atual...')
        
        for seletor in seletores_tarefa:
            try:
                elemento = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                )
                if elemento:
                    if 'button' in seletor:
                        # Se o elemento é um botão, busca o span interno
                        spans = elemento.find_elements(By.CSS_SELECTOR, '.texto-tarefa-processo')
                        if spans:
                            tarefa_atual = spans[0].text.strip().lower()
                    else:
                        tarefa_atual = elemento.text.strip().lower()
                        
                    if tarefa_atual:
                        seletor_funcionou = seletor
                        print(f'[CLS] ✓ Tarefa identificada via seletor: {seletor}')
                        print(f'[CLS] ✓ Tarefa atual: "{tarefa_atual}"')
                        break
            except Exception as e:
                print(f'[CLS] ✗ Seletor falhou: {seletor}')
                continue
        
        if not tarefa_atual:
            print('[CLS] Tentando fallback: busca por elementos com texto de tarefa')
            elementos = driver.find_elements(By.XPATH, 
                "//*[contains(text(),'Cumprimento') or contains(text(),'Análise') or contains(text(),'Minuta')]")
            if elementos:
                tarefa_atual = elementos[0].text.strip().lower()
                seletor_funcionou = "fallback-xpath"
                print(f'[CLS] ✓ Tarefa identificada via fallback: "{tarefa_atual}"')
            
        # Se já está em Análise ou Minuta, pode prosseguir direto para conclusão
        if tarefa_atual and ('análise' in tarefa_atual or 'minuta' in tarefa_atual):
            print('[CLS] Já está em tarefa adequada para conclusão.')
        else:
            print('[CLS] Necessário navegar para tarefa adequada.')        """
        
        # 2. Clica no botão 'Abrir tarefa do processo' e captura informação da tarefa
        from Fix import esperar_elemento, safe_click
        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            logger.error('[CLS] Botão "Abrir tarefa do processo" não encontrado!')
            return False
        
        # Captura o texto da tarefa diretamente do botão antes do clique
        tarefa_do_botao = None
        try:
            # Busca span interno do botão que contém o nome da tarefa
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                print(f'[CLS] ✓ Tarefa identificada do botão: "{tarefa_do_botao}"')
        except Exception:
            # Fallback: usa o texto completo do botão
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                print(f'[CLS] ✓ Tarefa identificada (texto completo): "{tarefa_do_botao}"')
            except Exception:
                print('[CLS] ⚠ Não foi possível capturar nome da tarefa do botão')
        
        # Executa o clique e registra o resultado
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        if click_resultado and tarefa_do_botao:
            print(f'[CLS] ✓ TAREFA ABERTA: "{tarefa_do_botao}"')
            print(f'[CLS] ✓ Clique bem-sucedido no botão da tarefa')
        elif click_resultado:
            print('[CLS] ✓ Clique bem-sucedido, mas nome da tarefa não capturado')
        else:
            print('[CLS] ✗ Falha no clique do botão da tarefa')
            return False

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
            print('[CLS] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # NOVO: Limpa qualquer overlay/modal que possa estar interferindo
        def limpar_overlays():
            try:
                overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                if overlays:
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
                logger.error(f'[CLS] Erro na limpeza de overlays: {clean_err}')
        limpar_overlays()
        
        # 3. Verifica se já está na URL de conclusão antes de tentar clicar no botão
        current_url = driver.current_url
        if '/conclusao' in current_url:
            print(f'[CLS] Já está na página de conclusão, pulando clique em "Conclusão ao magistrado"')
        else:
            # Verifica a tarefa atual pelo nome já logado
            tarefa_nome = tarefa_do_botao.strip().lower() if tarefa_do_botao else None
            if tarefa_nome:
                if 'conclusão ao magistrado' in tarefa_nome:
                    print('[CLS][INFO] Já está na tarefa "Conclusão ao magistrado". Pulando clique.')
                elif 'cumprimento de providências' in tarefa_nome:
                    print('[CLS][INFO] Detectada tarefa "Cumprimento de Providências". Clicando em "Análise" antes de conclusão.')
                    try:
                        # Primeiro tenta pelo mesmo seletor usado para conclusão ao magistrado
                        btn_analise = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Análise']"))
                        )
                        btn_analise.click()
                        print('[CLS][INFO] Clique em "Análise" realizado com sucesso (aria-label exato).')
                    except Exception as e1:
                        # Fallback: busca por texto visível
                        try:
                            btns = driver.find_elements(By.XPATH, "//button[contains(normalize-space(text()), 'Análise') or .//span[contains(normalize-space(text()), 'Análise')]]")
                            btn_analise = next((b for b in btns if b.is_displayed() and b.is_enabled()), None)
                            if btn_analise:
                                btn_analise.click()
                                print('[CLS][INFO] Clique em "Análise" realizado com sucesso (texto visível).')
                            else:
                                raise Exception('Nenhum botão "Análise" disponível.')
                        except Exception as e2:
                            print(f'[CLS][WARN] Não foi possível encontrar/clicar no botão "Análise": {e1} | {e2}')
                            return False
                    time.sleep(1)
                    # Após clicar em Análise, tenta clicar em Conclusão ao magistrado
                    try:
                        btn_conclusao = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                        )
                        btn_conclusao.click()
                        print(f'[CLS][DEBUG] Clique no botão Conclusão ao magistrado realizado após Análise.')
                    except Exception as e:
                        print(f'[CLS][ERRO] Falha ao clicar no botão Conclusão ao magistrado após Análise: {e}')
                        return False
                else:
                    # Para qualquer outra tarefa, tenta clicar direto em Conclusão ao magistrado
                    try:
                        btn_conclusao = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Conclusão ao magistrado']"))
                        )
                        btn_conclusao.click()
                        print(f'[CLS][DEBUG] Clique no botão Conclusão ao magistrado realizado. Seletor usado: button[aria-label=\'Conclusão ao magistrado\']')
                    except Exception as e:
                        print(f'[CLS][ERRO] Falha ao clicar no botão Conclusão ao magistrado: {e}')
                        return False
            else:
                print('[CLS][WARN] Não foi possível identificar a tarefa atual pelo nome do botão.')
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

        # Foco e interação no campo de filtro de modelos (padrão GIGS)
        try:
            campo_filtro_modelo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
            )
            driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
            driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
            driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, "")  # Limpa campo
            driver.execute_script('var el=arguments[0]; el.dispatchEvent(new Event("input", {bubbles:true})); el.dispatchEvent(new Event("keyup", {bubbles:true}));', campo_filtro_modelo)
            print('[CLS][MODELO][OK] Foco e eventos JS realizados no campo de filtro de modelos (#inputFiltro).')
            time.sleep(0.3)
        except Exception as e:
            print(f'[CLS][MODELO][ERRO] Falha ao acessar/interagir com o campo de filtro de modelos: {e}')
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
    perito=False,     # NOVO: parâmetro para ativar peritos
    Assinar=False,    # NOVO: parâmetro para ativar assinatura
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
                    pass        # 3. Prazo
        print('[ATO][DEBUG] Etapa: Prazo')
        if prazo is not None:
            try:
                print('[ATO][PRAZO][DEBUG] Chamando preencher_prazos_destinatarios...')
                preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario, perito=perito)
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
        # 5. Assinar
        print('[ATO][DEBUG] Etapa: Assinar')
        if Assinar:
            try:
                btn_assinar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.mat-fab[aria-label="Enviar para assinatura"]'))
                )
                btn_assinar.click()
                print('[ATO][ASSINAR] Botão "Enviar para assinatura" clicado com sucesso.')
                time.sleep(1)
            except Exception as e:
                print(f'[ATO][ASSINAR][ERRO] Falha ao clicar no botão de assinatura: {e}')
                return False
        else:
            print('[ATO][ASSINAR] Assinatura não solicitada para este ato.')

        # 6. Fechar aba
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

def make_ato_wrapper(conclusao_tipo, modelo_nome, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, descricao=None, sigilo=None, perito=False, Assinar=False):
    def wrapper(driver, debug=False, sigilo_=None, movimento_=None, descricao_=None, perito_=None, Assinar_=None, **kwargs):
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
            descricao=descricao_ if descricao_ is not None else descricao,
            perito=perito_ if perito_ is not None else perito,
            Assinar=Assinar_ if Assinar_ is not None else Assinar
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
    marcar_primeiro_destinatario=True,
    Assinar=True
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
    marcar_primeiro_destinatario=False,
    perito=True,
    descricao='Sobrestamento',
    Assinar=True
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

# NOVO WRAPPER: ato_meiosub
ato_meiosub = make_ato_wrapper(
    conclusao_tipo='Decisão Geral',
    modelo_nome='meiosub',
    prazo=None,
    marcar_pec=False,
    movimento='50071',
    gigs=None,
    marcar_primeiro_destinatario=False,
    sigilo=False
)

ato_pesquisas = make_ato_wrapper(
    conclusao_tipo='BACEN',
    modelo_nome='xsbacen',
    prazo=30,
    marcar_pec=True,
    movimento='bloqueio',
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Pesquisas para execução',
    sigilo=True
)

# ato_pesquisas permanece manual, pois tem lógica própria
def pesquisas(driver, conclusao_tipo=None, modelo_nome=None, prazo=None, marcar_pec=None, movimento=None, gigs=None, marcar_primeiro_destinatario=None, debug=False, sigilo=True, descricao=None, Assinar=True):
    try:
        # 1. Se existir botão 'Iniciar a execução', clicar antes de seguir
        try:
            btn_iniciar = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Iniciar a execução'], button[mattooltip*='Iniciar a execução']")
            if btn_iniciar and btn_iniciar.is_displayed() and btn_iniciar.is_enabled():
                safe_click(driver, btn_iniciar)
                print('[PESQUISAS] Clique em "Iniciar a execução" realizado.')
                import time
                time.sleep(1)
        except Exception:
            print('[PESQUISAS] Botão "Iniciar a execução" não encontrado ou não clicável, seguindo fluxo normal.')
        # 2. Segue fluxo padrão do ato judicial
        return ato_judicial(
            driver,
            conclusao_tipo='BACEN',
            modelo_nome='xsbacen',
            prazo=30,
            marcar_pec=True,
            movimento='bloqueio',
            gigs=gigs,
            marcar_primeiro_destinatario=True,
            debug=debug,
            sigilo=True,
            descricao='Pesquisas'
        )
    except Exception as e:
        print(f'[PESQUISAS][ERRO] Falha no fluxo do ato de pesquisas: {e}')
        try:
            driver.save_screenshot('erro_ato_pesquisas.png')
        except Exception:
            pass
        return False

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
    subtipo=None,
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None,
    debug=False
):
    """
    Fluxo generalizado para qualquer comunicação processual.
    """
    def log(msg):
        print(f'[COMUNICACAO] {msg}')
    modelo_nome,
    subtipo=None,
    descricao=None,
    tipo_prazo='dias uteis',
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
            
    try:  # FLUXO INICIAL ROBUSTO: abrir tarefa do processo e capturar informação da tarefa
        from Fix import esperar_elemento, safe_click
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selectors_pje import BTN_TAREFA_PROCESSO
        aba_origem = driver.current_url  # Armazena a URL atual
        abas_antes = set(driver.window_handles)
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_abrir_tarefa:
            log('[ERRO CRÍTICO] Botão "Abrir tarefa do processo" não encontrado!')
            raise Exception('Botão tarefa do processo não encontrado')
        
        # Captura o texto da tarefa diretamente do botão antes do clique
        tarefa_do_botao = None
        try:
            # Busca span interno do botão que contém o nome da tarefa
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                log(f'✓ Tarefa identificada do botão: "{tarefa_do_botao}"')
        except Exception:
            # Fallback: usa o texto completo do botão
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                log(f'✓ Tarefa identificada (texto completo): "{tarefa_do_botao}"')
            except Exception:
                log('⚠ Não foi possível capturar nome da tarefa do botão')
        
        # Executa o clique e registra o resultado
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        if click_resultado and tarefa_do_botao:
            log(f'✓ TAREFA ABERTA: "{tarefa_do_botao}"')
            log(f'✓ Clique bem-sucedido no botão da tarefa')
        elif click_resultado:
            log('✓ Clique bem-sucedido, mas nome da tarefa não capturado')
        else:
            log('✗ Falha no clique do botão da tarefa')
            raise Exception('Falha no clique do botão da tarefa')
        
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
            # Espera carregamento completo da nova aba (aguarda body presente e pelo menos um botão visível)
            try:
                WebDriverWait(driver, 20).until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.TAG_NAME, 'button')) > 0)
                log('Nova aba carregada completamente.')
            except Exception as e:
                log(f'[WARN] Timeout esperando carregamento completo da nova aba: {e}')
        else:
            log('[WARN] Nenhuma nova aba detectada após clique. Prosseguindo na aba atual.')
        # NOVO: Limpa qualquer overlay/modal que possa estar interferindo
        def limpar_overlays():
            try:
                overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-container')
                if overlays:
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
                logger.error(f'[CLS] Erro na limpeza de overlays: {clean_err}')
        limpar_overlays()
        
        # 2. Clicar no botão de Comunicações e expedientes - busca direta
        log('[DEBUG] Buscando botão de Comunicações e expedientes...')
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
        if not btn_comunic:
            # Tenta clicar em "Análise" e tenta de novo
            log('[INFO] Botão Comunicações e expedientes não encontrado. Tentando clicar em "Análise" e tentar novamente...')
            try:
                btn_analise = None
                # Busca botão Análise por texto
                btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ANÁLISE', 'análise'), 'análise')]")
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
                btns = driver.find_elements(By.XPATH, "//button[.//span[contains(translate(., 'ÁÀÂÃÉÈÊÍÏÔÕÖÚÇÑ', 'AAAAEEEIIOOOOUCN'), 'comunicacoes')]]")
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_comunic = btn
                        break
        if not btn_comunic:
            log('[ERRO] Botão de Comunicações e expedientes (fa-envelope) não encontrado mesmo após workaround!')
            raise Exception('Botão Comunicações e expedientes não encontrado')
        safe_click(driver, btn_comunic)
        log('Botão de Comunicações e expedientes clicado.')
          ###4.Criar comunicação####
        # Aguarda a tela de minutas carregar
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            WebDriverWait(driver, 20).until(lambda d: '/minutas' in d.current_url or 'Tipo de Expediente' in d.page_source)
            log('[DEBUG] Tela de minutas carregada.')

            # 1. Selecionar o tipo de expediente
            try:
                selecionar_opcao_select(driver, 'mat-select[placeholder="Tipo de Expediente"]', tipo_expediente)
                log(f'[DEBUG] Tipo de expediente selecionado: {tipo_expediente}')
            except Exception as e:
                log(f'[ERRO] Falha ao selecionar tipo de expediente: {e}')
            # 2. Selecionar o tipo de prazo
            try:
                selecionar_opcao_select(driver, 'mat-radio-button', tipo_prazo)
                log(f'[DEBUG] Tipo de prazo selecionado: {tipo_prazo}')
            except Exception as e:
                log(f'[WARN] Falha ao selecionar tipo de prazo: {e}')

            # 3. Preencher o prazo
            try:
                prazo = str(prazo) if prazo else ''
                if tipo_prazo == 'dias uteis':
                    input_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em dias úteis"]')
                    input_prazo.clear()
                    input_prazo.send_keys(prazo)
                elif tipo_prazo == 'data certa':
                    input_prazo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Prazo em data certa"]')
                    input_prazo.clear()
                    input_prazo.send_keys(prazo)
                log(f'[DEBUG] Prazo preenchido: {prazo}')
            except Exception as e:
                log(f'[WARN] Falha ao preencher prazo: {e}')

            # 4. Clicar no botão "Confeccionar ato agrupado"
            try:
                btn_agrupado = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
                safe_click(driver, btn_agrupado)
                log('[DEBUG] Botão "Confeccionar ato agrupado" clicado.')
                time.sleep(1)
            except Exception as e:
                log(f'[ERRO] Falha ao clicar em "Confeccionar ato agrupado": {e}')
            # 5. (Opcional) Escolher subtipo do expediente
            try:
                if subtipo is None:
                    if tipo_expediente.lower() == 'intimação':
                        subtipo = "Atos em Geral"
                    elif tipo_expediente.lower() == 'edital':
                        subtipo = "Edital"
                # Preenche o input de subtipo e seleciona a opção correta
                subtipo_input = driver.find_element(By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]')
                subtipo_input.clear()
                subtipo_input.send_keys(subtipo)
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                )
                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                for opcao in opcoes:
                    if subtipo.lower() in opcao.text.lower():
                        opcao.click()
                        log(f'[DEBUG] Subtipo de expediente selecionado: {opcao.text}')
                        break
                else:
                    log(f'[WARN] Subtipo "{subtipo}" não encontrado!')
            except Exception as e:
                log(f'[WARN] Falha ao selecionar subtipo de expediente: {e}')
            # 6. (Opcional) Preencher descrição
            try:
                # Usa o parâmetro descricao ou nome_comunicacao como fallback
                desc_to_use = descricao if descricao else nome_comunicacao
                input_descricao = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                input_descricao.clear()
                input_descricao.send_keys(desc_to_use)
                log(f'[DEBUG] Descrição preenchida: {desc_to_use}')
            except Exception as e:
                log(f'[WARN] Falha ao preencher descrição: {e}')
            
            # 7. (Opcional) Marcar sigilo
            try:
                if sigilo:
                    checkbox_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                    if not checkbox_sigilo.is_selected():
                        checkbox_sigilo.click()
                        log('[DEBUG] Marcado como sigiloso.')
                else:
                    log('[DEBUG] Documento não marcado como sigiloso.')
            except Exception as e:
                log(f'[WARN] Falha ao definir sigilo: {e}')            # 8. Selecionar o modelo seguindo o padrão gigs-plugin.js como em ato_judicial
            if modelo_nome:
                log(f'Selecionando modelo: {modelo_nome}')
                    
                    # 3. Disparar eventos como no gigs-plugin.js
                    for ev in ['input', 'change', 'keyup']:
                        driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)
                    
                    # 4. Simular pressionamento de Enter
                    campo_filtro_modelo.send_keys(Keys.ENTER)
                    log('[MODELO] Eventos disparados e ENTER pressionado')
                    
                    # 5. Selecionar o modelo filtrado destacado (fundo amarelo)
                    seletor_item_filtrado = '.nodo-filtrado'
                    nodo = esperar_elemento(driver, seletor_item_filtrado, timeout=15)
                    if not nodo:
                        log('[MODELO][ERRO] Nodo do modelo não encontrado!')
                        return False
                    
                    safe_click(driver, nodo)
                    log('[MODELO] Clique em nodo-filtrado realizado!')
                    
                    # 6. Aguardar a caixa de visualização do modelo carregar
                    seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
                    btn_inserir = esperar_elemento(driver, seletor_btn_inserir, timeout=15)
                    if not btn_inserir:
                        log('[MODELO][ERRO] Botão de inserir modelo não encontrado!')
                        return False
                    time.sleep(0.6)
                    
                    # 7. Pressionar ESPAÇO para inserir o modelo (padrão MaisPje)
                    btn_inserir.send_keys(Keys.SPACE)
                    log('[MODELO] Modelo inserido pressionando ESPAÇO no botão Inserir (padrão MaisPje)')
                    
                except Exception as e:
                    log(f'[ERRO] Falha ao selecionar modelo: {str(e)}')
                    raise# 9. Salvar e finalizar minuta com tratamento robusto
            try:
                # Primeiro salvar o documento
                log('[DEBUG] Procurando botão "Salvar"...')
                btn_salvar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salvar"]'))
                )
                
                # Usar JavaScript para garantir o clique
                log('[DEBUG] Clicando em "Salvar" via JS para maior confiabilidade')
                driver.execute_script("arguments[0].click();", btn_salvar)
                
                # Aguarda feedback visual do salvamento (snackbar ou outro indicador)
                try:
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, 'simple-snack-bar')) > 0
                    )
                    log('[DEBUG] Mensagem de salvamento detectada')
                    
                    # Fecha mensagens que possam estar interferindo
                    snack_bars = driver.find_elements(By.CSS_SELECTOR, 'simple-snack-bar')
                    for bar in snack_bars:
                        try:
                            fechar_btn = bar.find_element(By.TAG_NAME, 'button')
                            fechar_btn.click()
                            log('[DEBUG] Mensagem fechada')
                        except:
                            pass
                except:
                    # Continua mesmo se não encontrar confirmação visual
                    log('[DEBUG] Nenhuma mensagem de confirmação encontrada, mas prosseguindo')
                
                # Aguarda para estabilizar a UI
                time.sleep(1.5)
                
                # Agora finaliza a minuta
                log('[DEBUG] Procurando botão "Finalizar minuta"...')
                btn_finalizar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Finalizar minuta"]'))
                )
                
                # Usa clique JavaScript para maior confiabilidade
                log('[DEBUG] Clicando em "Finalizar minuta" via JS')
                driver.execute_script("arguments[0].click();", btn_finalizar)
                
                # Aguarda confirmação extra
                time.sleep(2)
                log('[DEBUG] Minuta finalizada com sucesso.')
            except Exception as e:
                log(f'[ERRO] Falha ao salvar/finalizar minuta: {e}')
            # 10. (Opcional) Clique em "fa-pen" para assinar
            # Exemplo: driver.find_element(By.CSS_SELECTOR, 'button .fa-pen').click()
        except Exception as e:
            log(f'[ERRO] Falha no fluxo de preenchimento de minuta: {e}')
              # 3. De volta à tela de minutas, clicar em .pec-polo-passivo-partes-processo
        try:
            btn_pec_polo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.fa.fa-user.pec-polo-passivo-partes-processo.pec-botao-intimar-polo-partes-processo'))
            )
            btn_pec_polo.click()
            log('[DEBUG] Clique em .fa.fa-user.pec-polo-passivo-partes-processo.pec-botao-intimar-polo-partes-processo realizado.')
            
            # Maximizar a tela
            driver.maximize_window()
            log('[DEBUG] Tela maximizada.')
            
            # Aplicar zoom de 60%
            driver.execute_script("document.body.style.zoom='0.6'")
            log('[DEBUG] Zoom aplicado para 60%.')
            
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar em .fa.fa-user.pec-polo-passivo-partes-processo.pec-botao-intimar-polo-partes-processo: {e}')
            return False
        
        # 4. Aguardar carregamento (pode ser necessário aguardar algum elemento específico, aqui aguarda 1s)
        time.sleep(3)
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
        
        # Chama Infojud para consulta IDPJ se for o caso
        if 'idpj' in nome_comunicacao.lower():
            try:
                from infojud import Infojud
                log('[COMUNICACAO] Chamando Infojud para consulta IDPJ...')
                Infojud(driver=driver, log=True)
                log('[COMUNICACAO] Infojud executado com sucesso.')
            except Exception as e:
                log(f"[COMUNICACAO][ERRO] Falha ao executar Infojud: {e}")
        
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

def make_comunicacao_wrapper(
    tipo_expediente, 
    prazo, 
    nome_comunicacao, 
    sigilo, 
    modelo_nome, 
    subtipo=None, 
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None
):
    def wrapper(driver, debug=False):
        return comunicacao_judicial(
            driver=driver,
            tipo_expediente=tipo_expediente,
            prazo=prazo,
            nome_comunicacao=nome_comunicacao,
            sigilo=sigilo,
            modelo_nome=modelo_nome,
            subtipo=subtipo,
            descricao=descricao if descricao else nome_comunicacao,
            tipo_prazo=tipo_prazo,
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
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    gigs_extra=(7, 'Guilherme - carta')
)
pec_decisao = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=10,
    nome_comunicacao='intimação de decisão',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    gigs_extra=(7, 'Guilherme - carta')
)
pec_idpj = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=17,
    nome_comunicacao='defesa IDPJ',
    sigilo=False,
    modelo_nome='xidpj c',
    subtipo="Intimação",  # Adicionando subtipo explícito
    descricao="Intimação para manifestação sobre IDPJ",  # Descrição mais detalhada
    tipo_prazo='dias uteis',
    gigs_extra=(7, 'Guilherme - carta')
)
pec_editalidpj = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=15,
    nome_comunicacao='Defesa IDPJ',
    sigilo=False,
    modelo_nome='IDPJ (edital)',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_editaldec = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=8,
    nome_comunicacao='Decisão/Sentença',
    sigilo=False,
    modelo_nome='3dec',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_cpgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado CP',
    sigilo=False,
    modelo_nome='mdd cp geral',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_excluiargos = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Exclusão de convênios',
    sigilo=False,
    modelo_nome='asa/cnib',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_mddgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=8,
    nome_comunicacao='Mandado',
    sigilo=False,
    modelo_nome='02 - gené',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_mddaud = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado citação',
    sigilo=False,
    modelo_nome='xmdd aud',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)
pec_editalaud = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=1,
    nome_comunicacao='Citação',
    sigilo=False,
    modelo_nome='1cit',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None
)

# ====================================================
# BLOCO 3 - MOVIMENTOS (importado de mov.py)
# ====================================================

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
    from selenium.webdriver.common.by import By
    try:
        print(f'[MOV][DEBUG] Iniciando fluxo de movimento para seletor: {seletor_alvo}')
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if not btn_abrir_tarefa:
            print('[MOV][ERRO] Botão "Abrir tarefa do processo" não encontrado!')

            return False
        
        # Captura o texto da tarefa diretamente do botão antes do clique
        tarefa_do_botao = None
        try:
            # Busca span interno do botão que contém o nome da tarefa
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                print(f'[MOV] ✓ Tarefa identificada do botão: "{tarefa_do_botao}"')
        except Exception:
            # Fallback: usa o texto completo do botão
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                print(f'[MOV] ✓ Tarefa identificada (texto completo): "{tarefa_do_botao}"')
            except Exception:
                print('[MOV] ⚠ Não foi possível capturar nome da tarefa do botão')
        
        abas_antes = set(driver.window_handles)
        # Executa o clique e registra o resultado
        click_resultado = safe_click(driver, btn_abrir_tarefa)
        if click_resultado and tarefa_do_botao:
            print(f'[MOV] ✓ TAREFA ABERTA: "{tarefa_do_botao}"')
            print(f'[MOV] ✓ Clique bem-sucedido no botão da tarefa')
        elif click_resultado:
            print('[MOV] ✓ Clique bem-sucedido, mas nome da tarefa não capturado')
        else:
            print('[MOV] ✗ Falha no clique do botão da tarefa')
            return False
        
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
                return False        # Confirmação/log final
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
    
def fluxo_sincrono_processo(driver):
    """
    Fluxo robusto para processamento de cada processo na lista, fiel ao gigs-plugin.js:
    - Verifica tarefa atual
    - Clica no suitcase
    - Seleciona destino
    - Logs detalhados
    - Interrompe em caso de erro crítico
    """
    try:
        print('[SINCRONO] Iniciando fluxo do processo atual...')
        # 1. Verifica se está na tela de tarefas/processos
        tarefa = None
        try:
            tarefa_elem = driver.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            tarefa = tarefa_elem.text.strip().lower()
            print(f'[SINCRONO] Tarefa identificada: {tarefa}')
        except Exception as e:
            print(f'[SINCRONO][ERRO] Não foi possível identificar a tarefa atual: {e}')
            raise

        # 2. Clica no suitcase (ícone de movimentação)
        try:
            suitcase_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Movimentar"], button[mattooltip*="Movimentar"], .fa-suitcase')
            safe_click(driver, suitcase_btn)
            print('[SINCRONO] Clique no suitcase realizado.')
        except Exception as e:
            print(f'[SINCRONO][ERRO] Falha ao clicar no suitcase: {e}')
            raise

        # 3. Seleciona destino (exemplo: "Conclusão ao magistrado")
        try:
            destino_btn = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Conclusão ao magistrado"]')
            safe_click(driver, destino_btn)
            print('[SINCRONO] Clique em "Conclusão ao magistrado" realizado.')
        except Exception as e:
            print(f'[SINCRONO][ERRO] Falha ao clicar no destino "Conclusão ao magistrado": {e}')
            raise

        # 4. Confirmação/log final
        print('[SINCRONO] Processo movimentado com sucesso.')
        return True
    except Exception as e:
        print(f'[SINCRONO][FATAL] Erro crítico no fluxo do processo: {e}')
        driver.save_screenshot('erro_fluxo_sincrono.png')
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

ato_pesquisas_wrapper = lambda driver, debug=False: pesquisas(
    driver,
    conclusao_tipo='BACEN',
    modelo_nome='xsbacen',
    descricao='Pesquisas',
    marcar_pec=True,
    sigilo=True,
    prazo=30,
    marcar_primeiro_destinatario=True,
    debug=debug
)
def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False, perito=False, perito_nomes=None):
    from selenium.webdriver.common.by import By
    # Lista fixa de nomes de peritos
    nomes_peritos_padrao = [
        'ROGERIO APARECIDO ROSA',
        # Adicione outros nomes fixos aqui se necessário
    ]
    if perito_nomes is None:
        perito_nomes = nomes_peritos_padrao
    linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
    if not linhas:
        print('[ATO][PRAZO][ERRO] Nenhuma linha de destinatário encontrada!')
        return False
    ativos = []
    for tr in linhas:
        try:
            checkbox = tr.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Intimar parte"]')
            nome_elem = tr.find_element(By.CSS_SELECTOR, '.destinario')
            nome = nome_elem.text.strip().upper()
            # Se já está marcado
            if checkbox.get_attribute('aria-checked') == 'true':
                ativos.append((tr, checkbox, nome))
            # Se está desmarcado e é perito e perito=True e nome na lista
            elif perito and nome in [n.upper() for n in perito_nomes]:
                driver.execute_script("arguments[0].click();", checkbox)
                print(f'[ATO][PRAZO][PERITO] Checkbox do perito {nome} ativado.')
                ativos.append((tr, checkbox, nome))
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao localizar checkbox/nome: {e}')
    if not ativos:
        print('[ATO][PRAZO][ERRO] Nenhum destinatário ativo!')
        return False
    if apenas_primeiro:
        # Desmarca todos exceto o primeiro
        for i, (tr, checkbox, nome) in enumerate(ativos):
            if i == 0:
                continue
            try:
                driver.execute_script("arguments[0].click();", checkbox)
                print(f'[ATO][PRAZO][INFO] Checkbox do destinatário {i+1} desmarcado.')
            except Exception as e:
                print(f'[ATO][PRAZO][WARN] Erro ao desmarcar checkbox: {e}')
        ativos = [ativos[0]]
    # Preenche prazos
    for tr, checkbox, nome in ativos:
        try:
            input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
            input_prazo.clear()
            input_prazo.send_keys(str(prazo))
            input_prazo.clear()
            input_prazo.send_keys(str(prazo))
            print(f'[ATO][PRAZO][OK] Preenchido prazo {prazo} para destinatário {nome}.')
        except Exception as e:
            print(f'[ATO][PRAZO][WARN] Erro ao preencher prazo: {e}')
    return True

def selecionar_subtipo(driver, subtipo, timeout=10):
    """Seleciona um subtipo de documento de forma robusta, simulando o padrão do gigs-plugin.js."""
    input_subtipo = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]'))
    )
    input_subtipo.clear()
    input_subtipo.send_keys(subtipo)
    
    # Espera pelo dropdown de opções e seleciona a opção exata
    opcoes = WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'mat-option'))
    )
    for opcao in opcoes:
        if opcao.text.strip().lower() == subtipo.lower():
            opcao.click()
            return True
    raise Exception(f'Subtipo "{subtipo}" não encontrado!')