import sys
import os
from datetime import datetime

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente


from Fix import login_pc, driver_notebook, aplicar_filtro_100, indexar_e_processar_lista, extrair_dados_processo, finalizar_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time
import re
import logging
import os
from Fix import esperar_elemento, safe_click, criar_gigs
from Fix import login_pc, aplicar_filtro_100
from Fix import extrair_documento, esperar_elemento, safe_click, indexar_e_processar_lista, login_notebook, aplicar_filtro_100
from atos import pesquisas, ato_sobrestamento, ato_180, mov_arquivar, mov_exec, ato_pesqliq, ato_calc2, ato_presc, ato_fal
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from Fix import driver_pc, login_pc
from driver_config import criar_driver, login_func

logger = logging.getLogger('AutomacaoPJe')

def checar_prox(driver, itens, doc_idx, regras, texto_normalizado):
    """
    Checa se há próximo documento relevante na timeline e retorna (doc_encontrado, doc_link, doc_idx) se houver.
    Executa apenas uma vez por chamada.
    """
    doc_encontrado = None
    doc_link = None
    next_idx = doc_idx + 1
    if next_idx < len(itens):
        for idx, item in enumerate(itens[next_idx:], next_idx):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    doc_idx = idx
                    break
            except Exception:
                continue
    return doc_encontrado, doc_link, doc_idx

def navegar_para_sobrestamento(driver):
    """
    Navega para a tela de sobrestamento:
    1. Clica no ícone de notebook (fa-laptop)
    2. Clica no botão 'Exibir todos'
    3. Aplica filtro de chips para 'Sobrestamento vencido'
    """
    try:
        # 1. Clicar no ícone de notebook
        print('[SOB] Clicando no ícone de notebook (fa-laptop)...')
        btn_laptop = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa-laptop.icone-menu'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_laptop)
        btn_laptop.click()
        time.sleep(1.2)
        # 2. Clicar no botão 'Exibir todos'
        print('[SOB] Clicando no botão Exibir todos...')
        btn_exibir_todos = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(),'Exibir todos')]]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_exibir_todos)
        driver.execute_script("arguments[0].click();", btn_exibir_todos)  # Usando execute_script para garantir que o clique ocorra
        print('[SOB] Aguardando carregamento da página após clicar em Exibir todos...')
        
        # Aguarda o carregamento da página com espera mais robusta
        # Primeiro aguarda um tempo mínimo para iniciar o carregamento
        time.sleep(3)
        
        # Verifica se elementos críticos estão presentes com múltiplas tentativas
        elementos_carregados = False
        max_tentativas = 3
        
        for tentativa in range(max_tentativas):
            try:
                # Aguarda primeiro o desaparecimento do indicador de carregamento (se existir)
                try:
                    loading = driver.find_element(By.CSS_SELECTOR, '.loading-shade')
                    if loading.is_displayed():
                        print('[SOB] Aguardando desaparecer indicador de carregamento...')
                        WebDriverWait(driver, 20).until_not(
                            EC.visibility_of(loading)
                        )
                except Exception:
                    pass  # O elemento de loading pode não existir, o que é ok
                
                # Verifica se elementos críticos estão presentes
                print(f'[SOB] Tentativa {tentativa+1}/{max_tentativas} - Verificando se a página carregou completamente...')
                WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR, 'i.fas.fa-filter, i.fas.fa-check-square, span.mat-select-placeholder'
                    ))
                )
                
                # Verificação adicional - verifica se a tabela/lista de processos está visível
                try:
                    table = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'table, mat-table, .list-container'))
                    )
                    elementos_carregados = True
                    print(f'[SOB] Página carregada com sucesso na tentativa {tentativa+1}')
                    break
                except Exception:
                    # Se não encontrar a tabela, pode ser que a interface esteja diferente
                    # Tenta verificar se pelo menos os controles estão visíveis
                    controls = driver.find_elements(By.CSS_SELECTOR, 'i.fas.fa-filter, i.fas.fa-check-square')
                    if len(controls) >= 2:
                        elementos_carregados = True
                        print(f'[SOB] Controles carregados com sucesso na tentativa {tentativa+1}')
                        break
            except Exception as e:
                print(f'[SOB][WARN] Tentativa {tentativa+1} - Tempo de espera excedido: {e}')
                # Se não for a última tentativa, tenta novamente após uma pausa
                if tentativa < max_tentativas - 1:
                    time.sleep(3)
                    try:
                        # Tenta clicar novamente no botão se necessário
                        btn_exibir_todos = driver.find_element(By.XPATH, "//button[.//span[contains(text(),'Exibir todos')]]")
                        if btn_exibir_todos.is_displayed():
                            driver.execute_script("arguments[0].click();", btn_exibir_todos)
                            print('[SOB] Clicando novamente no botão Exibir todos...')
                    except Exception:
                        pass
        
        if not elementos_carregados:
            print('[SOB][WARN] Não foi possível confirmar carregamento da página, continuando assim mesmo...')
        # 3. Aplicar filtro de chips para 'Sobrestamento vencido'
        print('[SOB] Aplicando filtro de chips para Sobrestamento vencido...')
        filtro_chip_sobrestamento(driver)
        print('[SOB] Filtro de sobrestamento aplicado.')
        
        # 4. GIGS será criado individualmente para cada processo durante o processamento
        print('[SOB] Filtro aplicado. Iniciando processamento da lista de processos...')
        
        # # 4. Criação manual de GIGS para todos os processos - COMENTADO
        # print('[SOB] Criando GIGS para todos os processos...')
        # gigs_sucesso = False
        # 
        # try:
        #     # Aguardar carregamento completo da página após filtro
        #     print('[SOB] Aguardando carregamento completo após filtro...')
        #     time.sleep(3)
        #     
        #     # Verificar se existem processos na lista
        #     try:
        #         processos = driver.find_elements(By.CSS_SELECTOR, 'tr.mat-row, .processo-item, .list-item')
        #         if len(processos) == 0:
        #             print('[SOB][ERRO] Nenhum processo encontrado na lista após aplicar filtro.')
        #             print('[SOB][ERRO] GIGS não pode ser criado - não há processos para selecionar.')
        #             return False
        #         else:
        #             print(f'[SOB] {len(processos)} processos encontrados na lista.')
        #     except Exception as e:
        #         print(f'[SOB][WARN] Não foi possível contar processos: {e}')
        #     
        #     # 1. SELECIONAR TODOS - com verificação robusta
        #     print('[SOB] Procurando botão "Selecionar todos"...')
        #     btn_selecionar_todos = None
        #     
        #     # Múltiplas tentativas para encontrar o botão selecionar todos
        #     seletores_selecionar = [
        #         'i.fas.fa-check-square',
        #         'i.fa-check-square',
        #         'button[title*="Selecionar"]',
        #         'button[aria-label*="Selecionar"]',
        #         '.selecionar-todos',
        #         'input[type="checkbox"][title*="Selecionar"]'
        #     ]
        #     
        #     for seletor in seletores_selecionar:
        #         try:
        #             btn_selecionar_todos = WebDriverWait(driver, 5).until(
        #                 EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
        #             )
        #             print(f'[SOB] Botão "Selecionar todos" encontrado com seletor: {seletor}')
        #             break
        #         except Exception:
        #             continue
        #     
        #     if not btn_selecionar_todos:
        #         print('[SOB][ERRO] Botão "Selecionar todos" não encontrado com nenhum seletor.')
        #         return False
        #     
        #     driver.execute_script("arguments[0].scrollIntoView(true);", btn_selecionar_todos)
        #     time.sleep(0.5)
        #     driver.execute_script("arguments[0].click();", btn_selecionar_todos)
        #     print('[SOB] Clique no botão "Selecionar todos" realizado.')
        #     time.sleep(2)
        #     
        #     # Verificar se algum processo foi selecionado
        #     try:
        #         processos_selecionados = driver.find_elements(By.CSS_SELECTOR, 'tr.mat-row.selected, .processo-item.selected, input[type="checkbox"]:checked')
        #         if len(processos_selecionados) == 0:
        #             # Tentar outro método de seleção
        #             print('[SOB][WARN] Nenhum processo parece ter sido selecionado. Tentando método alternativo...')
        #             checkboxes = driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
        #             for checkbox in checkboxes:
        #                 if not checkbox.is_selected():
        #                     driver.execute_script("arguments[0].click();", checkbox)
        #             time.sleep(1)
        #         else:
        #             print(f'[SOB] {len(processos_selecionados)} processos selecionados.')
        #     except Exception as e:
        #         print(f'[SOB][WARN] Não foi possível verificar seleção: {e}')
        #     
        #     # 2. Procurar e clicar no ícone fa-tag (texto-verde)
        #     print('[SOB] Procurando ícone de tag (GIGS)...')
        #     btn_tag = None
        #     
        #     seletores_tag = [
        #         'i.fa.fa-tag.icone.texto-verde',
        #         'i.fa-tag.texto-verde',
        #         'i.fas.fa-tag',
        #         'i.fa.fa-tag',
        #         'button[title*="tag"], button[title*="Tag"]',
        #         'button[aria-label*="tag"], button[aria-label*="Tag"]',
        #         '.btn-tag, .botao-tag'
        #     ]
        #     
        #     for seletor in seletores_tag:
        #         try:
        #             btn_tag = WebDriverWait(driver, 5).until(
        #                 EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
        #             )
        #             print(f'[SOB] Ícone de tag encontrado com seletor: {seletor}')
        #             break
        #         except Exception:
        #             continue
        #     
        #     if not btn_tag:
        #         print('[SOB][ERRO] Ícone de tag não encontrado com nenhum seletor.')
        #         return False
        #     
        #     driver.execute_script("arguments[0].scrollIntoView(true);", btn_tag)
        #     time.sleep(0.5)
        #     driver.execute_script("arguments[0].click();", btn_tag)
        #     print('[SOB] Clique no ícone de tag realizado.')
        #     time.sleep(2)
        #     
        #     # 3. Procurar e clicar no botão Atividade
        #     print('[SOB] Procurando botão "Atividade"...')
        #     btn_atividade = None
        #     
        #     seletores_atividade = [
        #         "//button[.//span[normalize-space(text())='Atividade'] and contains(@class,'mat-menu-item')]",
        #         "//button[contains(text(),'Atividade')]",
        #         "//mat-menu-item[contains(text(),'Atividade')]",
        #         "//button[@title='Atividade']",
        #         "//a[contains(text(),'Atividade')]"
        #     ]
        #     
        #     for seletor in seletores_atividade:
        #         try:
        #             btn_atividade = WebDriverWait(driver, 5).until(
        #                 EC.element_to_be_clickable((By.XPATH, seletor))
        #             )
        #             print(f'[SOB] Botão "Atividade" encontrado.')
        #             break
        #         except Exception:
        #             continue
        #     
        #     if not btn_atividade:
        #         print('[SOB][ERRO] Botão "Atividade" não encontrado.')
        #         # Tentar listar todos os botões disponíveis para diagnóstico
        #         try:
        #             botoes = driver.find_elements(By.CSS_SELECTOR, 'button, mat-menu-item')
        #             print('[SOB] Botões disponíveis para diagnóstico:')
        #             for i, botao in enumerate(botoes[:10]):  # Listar apenas os primeiros 10
        #                 try:
        #                     texto = botao.text.strip()
        #                     if texto:
        #                         print(f'[SOB] Botão {i+1}: "{texto}"')
        #                 except:
        #                     pass
        #         except:
        #             pass
        #         return False
        #     
        #     driver.execute_script("arguments[0].scrollIntoView(true);", btn_atividade)
        #     time.sleep(0.5)
        #     driver.execute_script("arguments[0].click();", btn_atividade)
        #     print('[SOB] Clique no botão "Atividade" realizado.')
        #     time.sleep(3)
        #     
        #     # 4. Procurar campo de observação e preencher
        #     print('[SOB] Procurando campo de observação...')
        #     campo_obs = None
        #     
        #     seletores_observacao = [
        #         "textarea[formcontrolname='observacao']",
        #         "textarea[name='observacao']",
        #         "textarea[placeholder*='observa']",
        #         "textarea[placeholder*='Observa']",
        #         "input[formcontrolname='observacao']",
        #         "input[name='observacao']",
        #         ".campo-observacao textarea",
        #         ".observacao textarea"
        #     ]
        #     
        #     for seletor in seletores_observacao:
        #         try:
        #             campo_obs = WebDriverWait(driver, 5).until(
        #                 EC.visibility_of_element_located((By.CSS_SELECTOR, seletor))
        #             )
        #             print(f'[SOB] Campo de observação encontrado com seletor: {seletor}')
        #             break
        #         except Exception:
        #             continue
        #     
        #     if not campo_obs:
        #         print('[SOB][ERRO] Campo de observação não encontrado.')
        #         return False
        #     
        #     campo_obs.click()
        #     time.sleep(0.5)
        #     campo_obs.clear()
        #     campo_obs.send_keys('sob')
        #     print('[SOB] Observação preenchida com "sob".')
        #     time.sleep(1)
        #     
        #     # 5. Procurar e clicar no botão Salvar
        #     print('[SOB] Procurando botão "Salvar"...')
        #     btn_salvar = None
        #     
        #     seletores_salvar = [
        #         "//button[.//span[normalize-space(text())='Salvar'] and contains(@class,'mat-raised-button') and contains(@class,'mat-primary')]",
        #         "//button[contains(text(),'Salvar')]",
        #         "//button[@title='Salvar']",
        #         "//input[@value='Salvar']",
        #         ".btn-salvar, .botao-salvar",
        #         "button[type='submit']"
        #     ]
        #     
        #     for seletor in seletores_salvar:
        #         try:
        #             if seletor.startswith('//'):
        #                 btn_salvar = WebDriverWait(driver, 5).until(
        #                     EC.element_to_be_clickable((By.XPATH, seletor))
        #                 )
        #             else:
        #                 btn_salvar = WebDriverWait(driver, 5).until(
        #                     EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
        #                 )
        #             print(f'[SOB] Botão "Salvar" encontrado.')
        #             break
        #         except Exception:
        #             continue
        #     
        #     if not btn_salvar:
        #         print('[SOB][ERRO] Botão "Salvar" não encontrado.')
        #         return False
        #     
        #     driver.execute_script("arguments[0].scrollIntoView(true);", btn_salvar)
        #     time.sleep(0.5)
        #     driver.execute_script("arguments[0].click();", btn_salvar)
        #     print('[SOB] Clique no botão "Salvar" realizado.')
        #     time.sleep(3)
        #     
        #     # Verificar se houve sucesso (procurar por mensagem de confirmação ou mudança na interface)
        #     try:
        #         # Procurar por mensagens de sucesso
        #         mensagens_sucesso = driver.find_elements(By.CSS_SELECTOR, '.alert-success, .toast-success, .notification-success, .snack-bar-success')
        #         if mensagens_sucesso:
        #             print('[SOB] Mensagem de sucesso detectada.')
        #             gigs_sucesso = True
        #         else:
        #             # Se não encontrou mensagem, assumir sucesso se não há erros visíveis
        #             mensagens_erro = driver.find_elements(By.CSS_SELECTOR, '.alert-error, .toast-error, .notification-error, .snack-bar-error')
        #             if not mensagens_erro:
        #                 print('[SOB] Nenhuma mensagem de erro detectada - assumindo sucesso.')
        #                 gigs_sucesso = True
        #             else:
        #                 print('[SOB][ERRO] Mensagem de erro detectada ao salvar GIGS.')
        #                 for msg in mensagens_erro:
        #                     try:
        #                         print(f'[SOB][ERRO] Mensagem de erro: {msg.text}')
        #                     except:
        #                         pass
        #     except Exception as e:
        #         print(f'[SOB][WARN] Não foi possível verificar resultado do salvamento: {e}')
        #         # Assumir sucesso se chegou até aqui sem exceções
        #         gigs_sucesso = True
        #     
        #     if gigs_sucesso:
        #         print('[SOB] GIGS criado com sucesso!')
        #     
        # except Exception as gigs_error:
        #     print(f'[SOB][ERRO] Falha ao criar GIGS manual: {gigs_error}')
        #     import traceback
        #     print(f'[SOB][ERRO] Detalhes do erro: {traceback.format_exc()}')
        #     gigs_sucesso = False
        # 
        # # CRÍTICO: Se GIGS não foi criado com sucesso, abortar execução
        # if not gigs_sucesso:
        #     print('[SOB][ERRO CRÍTICO] GIGS não foi criado com sucesso.')
        #     print('[SOB][ERRO CRÍTICO] ABORTANDO EXECUÇÃO conforme solicitado.')
        #     return False
        
        return True
    except Exception as e:
        print(f'[SOB][ERRO] Falha na navegação sobrestamento: {e}')
        return False

def filtro_chip_sobrestamento(driver):
    """
    Seleciona o chip 'Chips' e a opção 'Sobrestamento vencido' no dropdown, similar ao filtrofases.
    """
    try:
        # 1. Clicar no seletor Chips com método mais robusto (similar ao filtrofases)
        print('[SOB] Localizando e clicando no seletor Chips...')
        chips_element = None
        
        # Primeira tentativa - XPATH
        try:
            chips_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chips')]"))
            )
        except Exception:
            # Segunda tentativa - CSS com iteração sobre elementos potenciais
            try:
                print('[SOB] Primeira tentativa falhou, tentando método alternativo...')
                seletor_chips = 'span.ng-tns-c82-22.ng-star-inserted, span.mat-select-placeholder'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_chips):
                    if 'Chips' in elem.text:
                        chips_element = elem
                        break
            except Exception as e:
                print(f'[SOB][ERRO] Não encontrou o seletor de Chips: {e}')
                return False
        
        if not chips_element:
            print('[SOB][ERRO] Não encontrou o seletor de Chips.')
            return False
            
        # Rolar para o elemento e clicar com script (modificando para abordagem direta como no filtrofases)
        print('[SOB] Seletor Chips encontrado, tentando clicar...')
        driver.execute_script("arguments[0].scrollIntoView(true);", chips_element)
        
        # Clique direto no elemento (como é feito em filtrofases)
        driver.execute_script("arguments[0].click();", chips_element)
        print('[SOB] Clique executado no seletor Chips.')
        
        # Pausa significativa para garantir que o dropdown tenha tempo de abrir e carregar
        time.sleep(3)  # Aumentado de 1.5 para 3 segundos
        
        # 2. Esperar painel de opções com abordagem de filtrofases
        print('[SOB] Aguardando abertura do painel de opções...')
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        
        # Usando método mais robusto para esperar o painel
        max_tentativas = 20  # Aumentado para 20 tentativas
        for i in range(max_tentativas):
            try:
                painel_elements = driver.find_elements(By.CSS_SELECTOR, painel_selector)
                for panel_element in painel_elements:
                    if panel_element.is_displayed():
                        painel = panel_element
                        print(f'[SOB] Painel de opções encontrado na tentativa {i+1}.')
                        # Adiciona uma pausa após encontrar o painel para garantir que carregue completamente
                        time.sleep(2)
                        break
                if painel:
                    break
            except Exception:
                pass
                
            print(f'[SOB] Aguardando painel... tentativa {i+1}/{max_tentativas}')
            time.sleep(0.7)  # Aumentado tempo entre tentativas
        
        if not painel:
            print('[SOB][ERRO] Painel de opções de chips não apareceu após várias tentativas.')
            # Tentar clique alternativo - primeiro fecha qualquer painel aberto
            try:
                print('[SOB] Tentando método alternativo para abrir o painel...')
                # Clique fora para fechar qualquer painel aberto
                driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(1)
                
                # Tenta clicar de novo no seletor usando outro método
                if chips_element and chips_element.is_displayed():
                    # Tenta clique direto sem JavaScript
                    print('[SOB] Tentando clique direto no seletor Chips...')
                    actions = webdriver.ActionChains(driver)
                    actions.move_to_element(chips_element).click().perform()
                    time.sleep(3)
                    
                    # Tenta encontrar o painel novamente
                    try:
                        painel = WebDriverWait(driver, 8).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, painel_selector))
                        )
                        print('[SOB] Painel encontrado após clique alternativo!')
                        time.sleep(2)  # Espera para garantir carregamento
                    except Exception as e:
                        print(f'[SOB][ERRO] Falha no segundo método: {e}')
                        return False
            except Exception as e:
                print(f'[SOB][ERRO] Segunda tentativa de abrir o painel também falhou: {e}')
                return False
            
        # 3. Selecionar opção 'Sobrestamento vencido' (usando método de filtrofases)
        print('[SOB] Buscando opção "Sobrestamento vencido" no painel...')
        opcao_encontrada = False
        try:
            # Espera adicional para garantir que o painel carregou completamente
            time.sleep(1)
            
            # Método direto para encontrar todas as opções mat-option dentro do painel
            print('[SOB] Tentando localizar opções no painel...')
            try:
                opcoes = painel.find_elements(By.CSS_SELECTOR, "mat-option")
            except Exception:
                # Se falhar, tenta com XPATH
                opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            
            print(f'[SOB] {len(opcoes)} opções encontradas no painel.')
            
            # Se não encontrou opções, tenta outro método mais abrangente
            if not opcoes or len(opcoes) == 0:
                print('[SOB] Tentando método alternativo para encontrar opções...')
                try:
                    # Tenta encontrar opções em qualquer lugar na página
                    opcoes = driver.find_elements(By.CSS_SELECTOR, ".mat-select-panel-wrap mat-option")
                    print(f'[SOB] {len(opcoes)} opções encontradas pelo método alternativo.')
                except Exception as e:
                    print(f'[SOB][ERRO] Método alternativo falhou: {e}')
            
            # Debug: vamos imprimir o texto de cada opção para diagnóstico
            print('[SOB] Listando todas as opções disponíveis:')
            for i, op in enumerate(opcoes):
                try:
                    texto = op.text.strip()
                    print(f'[SOB] Opção {i+1}: "{texto}" (visível: {op.is_displayed()})')
                except:
                    print(f'[SOB] Opção {i+1}: <erro ao ler texto>')
            
            # Primeiro tenta encontrar "sobrestamento vencido"
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if 'sobrestamento vencido' in texto and opcao.is_displayed():
                        print(f'[SOB] Encontrada opção exata: "{texto}"')
                        # Garantir que está visível antes de clicar
                        driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", opcao)
                        print('[SOB] Opção "Sobrestamento vencido" selecionada.')
                        time.sleep(1.5)  # Espera após o clique
                        opcao_encontrada = True
                        break
                except Exception as e:
                    print(f'[SOB][WARN] Erro ao processar uma opção: {e}')
                    continue
                    
            # Se não encontrou a opção exata, tenta com qualquer opção que contenha "sobrestamento"
            if not opcao_encontrada:
                print('[SOB] Tentando com busca parcial por "sobrestamento"...')
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if 'sobrestamento' in texto and opcao.is_displayed():
                            print(f'[SOB] Encontrada opção parcial: "{texto}"')
                            driver.execute_script("arguments[0].scrollIntoView(true);", opcao)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", opcao)
                            print(f'[SOB] Opção com "sobrestamento" selecionada: "{texto}"')
                            time.sleep(1.5)
                            opcao_encontrada = True
                            break
                    except Exception as e:
                        print(f'[SOB][WARN] Erro na busca parcial: {e}')
                        continue
                
            # Se ainda não encontrou, tenta clicar na primeira opção disponível
            if not opcao_encontrada and opcoes and len(opcoes) > 0:
                try:
                    print('[SOB] Tentando clicar na primeira opção disponível...')
                    primeira_opcao = opcoes[0]
                    driver.execute_script("arguments[0].scrollIntoView(true);", primeira_opcao)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", primeira_opcao)
                    print(f'[SOB] Primeira opção selecionada: "{primeira_opcao.text}"')
                    time.sleep(1.5)
                    opcao_encontrada = True
                except Exception as e:
                    print(f'[SOB][ERRO] Falha ao clicar na primeira opção: {e}')
        
        except Exception as e:
            print(f'[SOB][ERRO] Erro ao buscar opções no painel: {e}')
        
        # 4. Clicar no botão filtrar
        try:
            print('[SOB] Tentando clicar no botão filtrar...')
            botao_filtrar = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-filter'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", botao_filtrar)
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[SOB] Filtro aplicado (botão filtrar).')
            time.sleep(2)  # Aumentado para garantir que o filtro seja aplicado
            
            # Maximizar a janela e aplicar zoom de 60% para melhor visualização
            print('[SOB] Maximizando janela do navegador...')
            driver.maximize_window()
            print('[SOB] Janela maximizada com sucesso.')
            time.sleep(0.5)
            
            print('[SOB] Aplicando zoom de 60% na página...')
            driver.execute_script("document.body.style.zoom='60%'")
            print('[SOB] Zoom aplicado com sucesso.')
            time.sleep(1)  # Pequena pausa após aplicar o zoom
        except Exception as e:
            print(f'[SOB][ERRO] Não conseguiu clicar no botão de filtrar: {e}')
            # Tentar método alternativo
            try:
                filtros = driver.find_elements(By.CSS_SELECTOR, 'i.fas')
                for filtro in filtros:
                    if 'filter' in filtro.get_attribute('class'):
                        driver.execute_script('arguments[0].click();', filtro)
                        print('[SOB] Filtro aplicado pelo método alternativo.')
                        time.sleep(2)
                        
                        # Maximizar a janela e aplicar zoom de 60% mesmo usando o método alternativo
                        print('[SOB] Maximizando janela do navegador (método alternativo)...')
                        driver.maximize_window()
                        print('[SOB] Janela maximizada com sucesso.')
                        time.sleep(0.5)
                        
                        print('[SOB] Aplicando zoom de 60% na página (método alternativo)...')
                        driver.execute_script("document.body.style.zoom='60%'")
                        print('[SOB] Zoom aplicado com sucesso.')
                        time.sleep(1)
                        break
            except Exception:
                pass
        
        return opcao_encontrada
    except Exception as e:
        print(f'[SOB][ERRO] Erro ao aplicar filtro de chips: {e}')
        return False

def parse_gigs_param(param):
    """
    Recebe uma string no formato 'dias/responsavel/observacao' e retorna (dias, responsavel, observacao).
    Se não houver responsável, deve ser 'dias/-/observacao'.
    """
    if isinstance(param, str) and param.count('/') >= 2:
        partes = param.split('/', 2)
        try:
            dias = int(partes[0]) if partes[0].isdigit() else 0
        except Exception:
            dias = 0
        responsavel = partes[1].strip()
        observacao = partes[2].strip()
        return dias, responsavel, observacao
    # fallback: dias=0, responsavel='', observacao=param
    return 0, '', param

def fluxo_sob(driver):
    """
    Processa sobrestamento em processos abertos.
    Seleciona apenas documentos do tipo decisão.
    """
    # Verificar se estamos na URL de detalhe do processo e criar GIGS
    try:
        current_url = driver.current_url
        if '/detalhe' in current_url:
            print('[SOB] Processo aberto em URL de detalhe. Criando GIGS...')
            from Fix import criar_gigs
            criar_gigs(driver, 0, '', 'sob')
            print('[SOB] GIGS criado: 0 dias, sem responsável, observação sob')
            time.sleep(1)
            
            # Chamar função listaexec após criar GIGS
            try:
                print('[SOB] Iniciando análise de medidas executórias...')
                from listaexec import listaexec
                medidas = listaexec(driver, log=True)
                print(f'[SOB] Análise de medidas executórias concluída. Total encontradas: {len(medidas)}')
            except Exception as e_listaexec:
                print(f'[SOB][ERRO] Falha na análise de medidas executórias: {e_listaexec}')
            
        else:
            print(f'[SOB] URL atual não contém /detalhe: {current_url}')
    except Exception as e:
        print(f'[SOB][ERRO] Falha ao criar GIGS: {e}')
    
    acao_secundaria = None
    texto = None
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    doc_encontrado = None
    doc_link = None
    doc_idx = 0
    while True:
        for idx, item in enumerate(itens[doc_idx:], doc_idx):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                # Seleciona apenas decisão
                if 'decisão' not in doc_text and 'decisao' not in doc_text:
                    continue
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                mag_ok = any('otavio' in mag.get_attribute('aria-label').lower() or 'mariana' in mag.get_attribute('aria-label').lower() for mag in mag_icons)
                if mag_ok:
                    doc_encontrado = item
                    doc_link = link
                    doc_idx = idx
                    break
            except Exception:
                continue
        if not doc_encontrado or not doc_link:
            print('[SOB] Nenhuma decisão relevante encontrada.')
            return
        doc_link.click()
        time.sleep(2)
        # 2. Extrair texto usando a função de Fix.py
        import datetime
        texto_tuple = None # Initialize tuple variable
        try:
            texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True) # timeout reduzido
            if texto_tuple and texto_tuple[0]:
                texto = texto_tuple[0].lower()
            else:
                logger.error('[FLUXO_PZ] extrair_documento retornou None ou texto vazio.')
                texto = None
        except Exception as e_extrair:
            logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')
            texto = None
        
        if not texto:
            logger.error('[FLUXO_PZ] Não foi possível extrair o texto do documento via extrair_documento.')
            return
        
        # Log do texto extraído (início apenas)
        log_texto = texto[:200] + '...' if len(texto) > 200 else texto
        print(f'[FLUXO_PZ] Texto extraído: {log_texto}')

        # 4. Define as regras com parâmetros e ações sequenciais
        def remover_acentos(txt):
            import unicodedata
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

        def normalizar_texto(txt):
            return remover_acentos(txt.lower())

        texto_normalizado = normalizar_texto(texto)

        def gerar_regex_geral(termo):
            # Remove acentos e deixa minúsculo para o termo
            termo_norm = normalizar_texto(termo)
            # Divide termo em palavras
            palavras = termo_norm.split()
            # Monta regex permitindo pontuação, vírgula, etc. entre as palavras
            partes = [re.escape(p) for p in palavras]
            # Entre cada palavra, aceita qualquer quantidade de espaços, pontuação, vírgula, etc.
            regex = r''
            for i, parte in enumerate(partes):
                regex += parte
                if i < len(partes) - 1:                regex += r'[\s\.,;:!\-–—]*'
            # Permite o trecho em qualquer lugar do texto (texto antes/depois)
            return re.compile(rf"{regex}", re.IGNORECASE)

        regras = [
            # Regra combinada para prescrição que executa todas as ações necessárias
            # Agora busca dois termos: "2023" E "prazo prescricional" em qualquer ordem/lugar
            ([re.compile(r'(?=.*2023)(?=.*prazo[\s\.,;:!\-–—]*prescricional)', re.IGNORECASE | re.DOTALL)],
             'multi', ['1/xs/pec', '8/xs/conf prescrição'], ato_presc),
            ([gerar_regex_geral('recebeu')],
             None, None, ato_fal),
        ]

        # 5. Iterate through rules and keywords to find the first match
        acao_definida = None
        parametros_acao = None
        termo_encontrado = None
        acao_secundaria = None  # Reset before checking rules
        for keywords, tipo_acao, params, acao_sec in regras:
            for regex in keywords:
                match = regex.search(texto_normalizado)
                if match:
                    # Log da regra encontrada
                    print(f'[FLUXO_PZ] Regra aplicada: {tipo_acao} - {params if params else acao_sec.__name__ if acao_sec else "Nenhuma"}')
                    acao_definida = tipo_acao
                    parametros_acao = params
                    acao_secundaria = acao_sec
                    termo_encontrado = regex.pattern
                    # NOVA REGRA: se acao_definida == 'checar_prox', chamar checar_prox imediatamente
                    if acao_definida == 'checar_prox':
                        prox_doc_encontrado, prox_doc_link, prox_doc_idx = checar_prox(driver, itens, doc_idx, regras, texto_normalizado)
                        if prox_doc_encontrado and prox_doc_link:
                            print(f'[FLUXO_PZ] Regra de cancelamento/baixa: buscando próximo documento relevante')
                            doc_encontrado = prox_doc_encontrado
                            doc_link = prox_doc_link
                            doc_idx = prox_doc_idx
                            break
                    break
            if acao_definida:
                break        # 6. Perform action(s) based on the matched rule (or default)
        import datetime
        gigs_aplicado = False
        
        # Nova lógica para ações múltiplas (tipo_acao 'multi')
        if acao_definida == 'multi':
            try:
                # parametros_acao é uma lista de strings no formato 'dias/responsavel/observacao'
                print(f'[FLUXO_PZ] Executando ações múltiplas para regra encontrada')
                
                # Criar todos os GIGS da lista
                for gigs_param in parametros_acao:
                    try:
                        dias, responsavel, observacao = parse_gigs_param(gigs_param)
                        criar_gigs(driver, dias, responsavel, observacao)
                        print(f'[FLUXO_PZ] GIGS criado: {observacao}')
                        time.sleep(0.5)  # Pequena pausa entre operações de GIGS
                    except Exception as gigs_error:
                        logger.error(f'[FLUXO_PZ] Falha ao criar GIGS {gigs_param}: {gigs_error}')
                
                # Executar função secundária se existir
                if acao_secundaria:
                    print(f'[FLUXO_PZ] Executando ação secundária: {acao_secundaria.__name__}')
                    try:
                        acao_secundaria(driver)
                    except TypeError:
                        acao_secundaria(driver)
                    time.sleep(1)
                
                gigs_aplicado = True
            except Exception as multi_error:
                logger.error(f'[FLUXO_PZ] Falha ao processar ações múltiplas: {multi_error}')
                
        elif acao_definida == 'gigs':
            # parametros_acao já está no formato 'dias/responsavel/observacao'
            try:
                dias, responsavel, observacao = parse_gigs_param(parametros_acao)
                criar_gigs(driver, dias, responsavel, observacao)
                gigs_aplicado = True
                print(f'[FLUXO_PZ] GIGS criado: {observacao}')
                if acao_secundaria:
                    print(f'[FLUXO_PZ] Executando ação secundária: {acao_secundaria.__name__}')
                    try:
                        acao_secundaria(driver)
                    except TypeError:
                        acao_secundaria(driver)
                    time.sleep(1)
            except Exception as gigs_error:
                logger.error(f'[FLUXO_PZ] Falha ao criar GIGS ou na ação secundária: {gigs_error}') 

    # Fim do while True    # Fechar a aba após o processamento do fluxo_pz (sem usar try/finally)
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        # Troca para uma aba válida após fechar
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
            else:
                print("[LIMPEZA][ERRO] Nenhuma aba restante para alternar.")
        except Exception as e:
            print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida após fechar: {e}")
        # Testa se a aba está realmente acessível
        from selenium.common.exceptions import NoSuchWindowException
        try:
            _ = driver.current_url
        except NoSuchWindowException:
            print("[LIMPEZA][ERRO] Tentou acessar uma aba já fechada.")
    
    print('[FLUXO_PZ] Processo concluído, retornando à lista')

def fluxo_lista(driver):
    """
    Executa o fluxo de prazo: Itera processos, chama fluxo_pz para cada um.
    """
    from Fix import indexar_e_processar_lista # Keep this import

    print('[FLUXO_PRAZO] Iniciando processamento da lista de processos')

    def callback_processo(driver_processo):
        """
        Callback para executar fluxo_sob no processo aberto.
        fluxo_sob handles analysis, actions (primary & secondary), and tab closing.
        """
        try:
            fluxo_sob(driver_processo) # Call the main function for the process tab
        except Exception as callback_error:
            logger.error(f'[FLUXO_PRAZO] ERRO no fluxo_sob: {callback_error}')
            raise  # Re-raise para que o indexar_e_processar_lista saiba que houve erro
        
        time.sleep(1)  # Pausa para evitar race condition/travamento entre processamentos

    # Chama indexar_e_processar_lista com o callback definido
    indexar_e_processar_lista(driver, callback_processo) # Use the correct processing function

    print('[FLUXO_PRAZO] Processamento da lista concluído')


def executar_fluxo(driver):
    """
    Executa o fluxo completo para sobrestamento:
    1. Navegação e filtro de sobrestamento
    2. Processamento da lista de processos, chamando fluxo_sob para cada processo
    """
    # 1. Navegação e filtro de sobrestamento
    if not navegar_para_sobrestamento(driver):
        print('[SOB][ERRO] Falha na navegação/filtro de sobrestamento. Abortando.')
        return False
    # 2. Processar lista de processos
    fluxo_lista(driver)
    return True


def processar_sob(driver_existente=None):
    """
    Função principal que executa o fluxo sob.py.
    1. Cria driver e faz login (usando driver_config.py)
    2. Executa o fluxo principal de sobrestamento
    """
    driver = driver_existente
    should_quit = False
    try:
        if not driver:
            driver = criar_driver()
            login_func(driver)
            should_quit = True  # Só fecha o driver se foi criado aqui
        executar_fluxo(driver)
        return True
    except Exception as e:
        logger.error(f'[PROCESSAR_SOB] Erro: {e}')
        return False
    finally:
        if should_quit and driver:
            finalizar_driver(driver)

if __name__ == "__main__":
    processar_sob()  # Quando executado diretamente, cria seu próprio driver