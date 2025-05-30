"""
Script reorganizado de automação de Prazos para o PJePlus.
Estrutura inspirada nos padrões do pje.py e Mandado.py.
"""

# ========== IMPORTS ========== 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
import shutil
from Fix import criar_gigs, extrair_documento, login_automatico # Importação correta da função criar_gigs
import re
import math

# ========== FUNÇÕES DE SUPORTE ==========
def navegacao(driver):
    """Navega até o painel de prazos."""
    print('[NAV] Procurando ícone fa-laptop...')
    icone = driver.find_element(By.CSS_SELECTOR, 'i.fa-laptop')
    icone.click()
    print('[NAV] Ícone fa-laptop clicado.')
    time.sleep(2)
    driver.get('https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos')
    print('[NAV] Navegação direta para painel global de prazos.')
    time.sleep(2)

def limpar_temp_selenium():
    """
    Remove pastas webdriver-py-profilecopy e arquivos temporários antigos do Selenium no diretório TEMP.
    """
    import tempfile
    import os
    import shutil
    temp_dir = tempfile.gettempdir()
    for nome in os.listdir(temp_dir):
        if nome.startswith('tmp') or nome.startswith('webdriver-py-profilecopy'):
            caminho = os.path.join(temp_dir, nome)
            try:
                if os.path.isdir(caminho):
                    shutil.rmtree(caminho, ignore_errors=True)
                else:
                    os.remove(caminho)
                print(f'[LIMPEZA TEMP] Removido: {caminho}')
            except Exception as e:
                print(f'[LIMPEZA TEMP][ERRO] Falha ao remover {caminho}: {e}')

# ========== MAIN ========== 
def backup_rotativo(filepath):
    dirpath, filename = os.path.split(filepath)
    for i in range(5, 0, -1):
        bak_old = os.path.join(dirpath, f"{filename}.bak{i}")
        bak_new = os.path.join(dirpath, f"{filename}.bak{i+1}")
        if os.path.exists(bak_old):
            if i == 5 and os.path.exists(bak_old):
                os.remove(bak_old)
            else:
                os.rename(bak_old, bak_new)
    bak1 = os.path.join(dirpath, f"{filename}.bak1")
    if os.path.exists(filepath):
        shutil.copy2(filepath, bak1)
        print(f'[BACKUP] Backup rotativo criado: {bak1}')

def main():
    backup_rotativo(__file__)
    from selenium import webdriver
    driver = webdriver.Firefox()
    usuario = os.environ.get('PJE_USUARIO')
    senha = os.environ.get('PJE_SENHA')
    if not usuario:
        usuario = input('Usuário PJe: ')
        os.environ['PJE_USUARIO'] = usuario
        print('[INFO] Variável de ambiente PJE_USUARIO definida para esta sessão.')
    if not senha:
        senha = input('Senha PJe: ')
        os.environ['PJE_SENHA'] = senha
        print('[INFO] Variável de ambiente PJE_SENHA definida para esta sessão.')
    login_automatico(driver, usuario, senha)
    navegacao(driver)
    loop_movimentacao_processos(driver)
    # Após finalizar todos os loops, executa o filtro de prazos e atividade em lote
    from FILTROPRAZO import filtro_prazo
    filtro_prazo(driver)
    # Integração com Andamento: análise e extração de decisões
    from Andamento import lista_prazo, analisar_lista_processos
    lista_prazo(driver)
    analisar_lista_processos(driver)
    driver.quit()

# ========== FLUXO PRINCIPAL DE PRAZOS ========== 
def filtrar_fase_processual(driver, fases_alvo=None):
    """
    Filtra as fases desejadas no painel global do PJe.
    Por padrão, seleciona 'Liquidação' e 'Execução'.
    Após selecionar, clica no botão de filtrar (ícone fa-filter).
    """
    if fases_alvo is None:
        fases_alvo = ['liquidação', 'execução']
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        # Localiza o seletor de fase processual usando XPath mais robusto
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            # Tenta método alternativo se o primeiro falhar
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                print('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        
        if not fase_element:
            print('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        
        # Clica no seletor de fase
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        
        # Aguarda o painel de opções aparecer
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        
        if not painel or not painel.is_displayed():
            print('[ERRO] Painel de opções não apareceu.')
            return False
        
        # Seleciona as fases desejadas - usando apenas o método mais robusto
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        print(f'[OK] Fase "{fase}" selecionada.')
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        
        if len(fases_clicadas) == 0:
            print(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        
        # Clique no botão de filtrar (ícone fa-filter) para finalizar
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[OK] Fases selecionadas e filtro aplicado (botão filtrar).')
            time.sleep(1)
        except Exception as e:
            print(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        
        return True
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    def movimentar_processos(driver):
    """
    Movimenta os processos selecionados para a tarefa 'Análise'.
    
    O fluxo é:
    1. Clica fora de painéis abertos para garantir interface limpa
    2. Marca todos os processos usando o ícone check
    3. Inicia movimentação pelo ícone mala (suitcase)
    4. Seleciona 'Análise' como tarefa destino
    5. Confirma movimentação dos processos
    """
    print('Movimentando processos...')
    try:
        # 1. Garantir interface limpa
        clicar_fora_painel(driver)
        
        # 2. Marcar todos os processos
        safe_click(driver, "//i[contains(@class, 'fa-check') and contains(@class, 'marcar-todas')]")
        time.sleep(0.7)
        clicar_fora_painel(driver)
        
        # 3. Iniciar movimentação
        safe_click(driver, "//i[contains(@class, 'fa-suitcase') and contains(@class, 'icone')]")
        print('[OK] Processos selecionados para movimentação.')
        time.sleep(2)
        
        # 4. Selecionar tarefa destino única
        print('[MOV] Selecionando tarefa destino única...')
        tarefa_select = driver.find_element(By.XPATH, "//span[contains(@class, 'mat-select-placeholder') and contains(@class, 'mat-select-min-line')]")
        driver.execute_script("arguments[0].click();", tarefa_select)
        time.sleep(1)
        
        # 5. Selecionar opção "Análise"
        opcoes = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-option-text')]")
        for opcao in opcoes:
            if 'análise' in opcao.text.strip().lower():
                driver.execute_script("arguments[0].click();", opcao)
                print('[MOV] Opção "Análise" selecionada.')
                time.sleep(1)
                break
        
        # 6. Confirmar movimentação
        btns = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and contains(text(), 'Movimentar processos')]")
        for btn in btns:
            try:
                driver.execute_script("arguments[0].click();", btn)
                print('[MOV] Movimentação de processos confirmada.')
                break
            except Exception as e:
                print(f'[MOV][ERRO] Falha ao clicar no botão "Movimentar processos": {e}')
        time.sleep(2)
        
    except Exception as e:
        print(f'[ERRO] Erro ao movimentar processos: {e}')

def clicar_fora_painel(driver):
    """
    Clica fora de qualquer painel aberto para garantir que elementos não estejam cobertos.
    """
    try:
        body = driver.find_element(By.TAG_NAME, 'body')
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).move_to_element_with_offset(body, 5, 5).click().perform()
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f'[ERRO] Não conseguiu clicar fora do painel: {e}')
        return False

def safe_click(driver, xpath, timeout=10):
    """
    Aguarda o elemento estar clicável via XPATH e realiza o clique via JavaScript.
    """
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        el = driver.find_element(By.XPATH, xpath)
        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception as e:
        print(f'[ERRO] Erro ao clicar (safe_click): {e}')
        return False

def selecionar_processos_livres(driver):
    """
    Seleciona processos "livres" na lista que atendem aos critérios:
    - Sem prazo (coluna 9 vazia)
    - Sem comentário
    - Sem valor em input[matinput]
    - Sem ícone de pesquisa na coluna 3
    
    Returns:
        int: Número de processos selecionados
        bool: True se executou com sucesso, False caso contrário
    """
    print('\n[SELECAO] Iniciando seleção de processos livres...')

    # 1. Configurar visualização para 100 linhas
    print('[SELECAO] Configurando visualização para 100 linhas por página...')
    try:
        btn_linhas = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-select-value-117'))
        )
        print('[SELECAO][DEBUG] Botão de linhas encontrado e clicável')
        
        driver.execute_script("arguments[0].click();", btn_linhas)
        print('[SELECAO][DEBUG] Dropdown de linhas clicado via JavaScript')
        time.sleep(0.5)
        
        opcao_100 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-option-266 > span'))
        )
        driver.execute_script("arguments[0].click();", opcao_100)
        print('[SELECAO][OK] Opção 100 linhas selecionada')
        time.sleep(1)
        
    except TimeoutException:
        print('[SELECAO][ERRO] Timeout ao aguardar elementos do filtro de linhas')
        driver.save_screenshot('debug_timeout_filtro_linhas.png')
        return 0, False
    except Exception as e:
        print(f'[SELECAO][ERRO] Falha ao configurar linhas por página: {str(e)}')
        driver.save_screenshot('debug_erro_filtro_linhas.png')
        return 0, False

    # 2. Localizar e analisar linhas da tabela
    print('\n[SELECAO] Iniciando análise das linhas da tabela...')
    try:
        linhas = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
        )
        print(f'[SELECAO][DEBUG] {len(linhas)} linhas encontradas na tabela')
        
        if not linhas:
            print('[SELECAO][AVISO] Nenhuma linha encontrada na tabela')
            driver.save_screenshot('debug_tabela_vazia.png')
            return 0, False
        
        # 3. Processar cada linha
        selecionados = 0
        erros = 0
        for idx, linha in enumerate(linhas, 1):
            print(f'\n[SELECAO] Analisando linha {idx}/{len(linhas)}...')
            try:
                # Verificar prazo
                prazo = linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(9) time')
                prazo_vazio = not prazo or not prazo[0].text.strip()
                print(f'[SELECAO][DEBUG] Linha {idx} - Prazo vazio: {prazo_vazio}')

                # Verificar comentário
                has_comment = len(linha.find_elements(By.CSS_SELECTOR, 'i.fa-comment')) > 0
                print(f'[SELECAO][DEBUG] Linha {idx} - Tem comentário: {has_comment}')

                # Verificar campo preenchido
                try:
                    input_field = linha.find_elements(By.CSS_SELECTOR, 'input[matinput]')
                    campo_preenchido = bool(input_field and input_field[0].get_attribute('value').strip())
                except Exception:
                    campo_preenchido = False
                print(f'[SELECAO][DEBUG] Linha {idx} - Campo preenchido: {campo_preenchido}')

                # Verificar lupa
                tem_lupa = len(linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')) > 0
                print(f'[SELECAO][DEBUG] Linha {idx} - Tem lupa: {tem_lupa}')

                # Processo é livre se atender todos os critérios
                if prazo_vazio and not has_comment and not campo_preenchido and not tem_lupa:
                    try:
                        checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type="checkbox"]')
                        if not checkbox.is_selected():
                            driver.execute_script('arguments[0].click()', checkbox)
                            driver.execute_script('arguments[0].style.backgroundColor = "#ffccd2";', linha)
                            selecionados += 1
                            print(f'[SELECAO][OK] Linha {idx} selecionada e destacada')
                    except Exception as e:
                        print(f'[SELECAO][ERRO] Falha ao marcar checkbox da linha {idx}: {str(e)}')
                        erros += 1
                        continue

            except Exception as e:
                print(f'[SELECAO][ERRO] Falha ao analisar linha {idx}: {str(e)}')
                erros += 1
                continue

        # 4. Relatório final
        print(f'\n[SELECAO] === Relatório Final ===')
        print(f'[SELECAO] Total de linhas processadas: {len(linhas)}')
        print(f'[SELECAO] Processos selecionados: {selecionados}')
        print(f'[SELECAO] Erros encontrados: {erros}')

        if selecionados == 0:
            print('[SELECAO][AVISO] Nenhum processo livre encontrado')
            driver.save_screenshot('debug_nenhum_processo_livre.png')
            return 0, True

        # 5. Registrar atividade para os processos selecionados
        print('\n[SELECAO] Registrando atividade para processos selecionados...')
        try:
            # Clicar no ícone verde de tag
            tag_verde = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-tag.icone.texto-verde'))
            )
            driver.execute_script("arguments[0].click();", tag_verde)
            print('[SELECAO][DEBUG] Tag verde clicada')
            time.sleep(0.8)
            
            # Clicar em "Atividade"
            span_atividade = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Atividade']"))
            )
            driver.execute_script("arguments[0].click();", span_atividade)
            print('[SELECAO][DEBUG] Menu Atividade clicado')
            time.sleep(0.8)
            
            # Preencher campos da atividade
            input_dias = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
            )
            driver.execute_script("arguments[0].value = '0';", input_dias)
            input_dias.send_keys('0')
            input_dias.send_keys(Keys.TAB)
            print('[SELECAO][DEBUG] Campo dias preenchido com 0')
            
            textarea_obs = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
            )
            driver.execute_script("arguments[0].value = 'pz checar';", textarea_obs)
            textarea_obs.send_keys('xs')
            textarea_obs.send_keys(Keys.TAB)
            print('[SELECAO][DEBUG] Campo observação preenchido com pz checar')
            
            # Salvar atividade
            btn_salvar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"].mat-primary'))
            )
            driver.execute_script("arguments[0].click();", btn_salvar)
            print('[SELECAO][OK] Atividade registrada com sucesso')
            time.sleep(1.2)

            return selecionados, True

        except Exception as e:
            print(f'[SELECAO][ERRO] Falha ao registrar atividade: {str(e)}')
            driver.save_screenshot('debug_erro_registro_atividade.png')
            return selecionados, False

    except Exception as e:
        print(f'[SELECAO][ERRO] Erro geral na seleção: {str(e)}')
        driver.save_screenshot('debug_erro_geral_selecao.png')
        return 0, False



def processar_apos_selecao(driver, num_selecionados):
    """
    Processa os próximos passos após a seleção de processos livres.
    Retorna True se conseguiu processar com sucesso.
    """
    print(f'\n[POS-SELECAO] Iniciando processamento de {num_selecionados} processos...')
    
    try:
        # 1. Verificar se há processos para processar
        if num_selecionados == 0:
            print('[POS-SELECAO][AVISO] Nenhum processo para processar')
            return True
            
        # 2. Iniciar movimentação
        print('[POS-SELECAO] Iniciando movimentação dos processos...')
        
        try:
            movimentar_processos(driver)
            print('[POS-SELECAO][OK] Movimentação concluída com sucesso')
            
            # 3. Verificar se processos sumiram da lista (movimentação efetiva)
            time.sleep(2)
            linhas_apos = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
            total_apos = len(linhas_apos)
            
            if total_apos >= num_selecionados:
                print('[POS-SELECAO][ALERTA] Possível falha na movimentação - quantidade de processos não diminuiu')
                driver.save_screenshot('debug_movimentacao_suspeita.png')
            else:
                print(f'[POS-SELECAO][OK] {num_selecionados - total_apos} processos movimentados com sucesso')
            
            return True
            
        except Exception as e:
            print(f'[POS-SELECAO][ERRO] Falha ao movimentar processos: {str(e)}')
            driver.save_screenshot('debug_erro_pos_selecao.png')
            return False
            
    except Exception as e:
        print(f'[POS-SELECAO][ERRO] Erro geral no processamento pós-seleção: {str(e)}')
        driver.save_screenshot('debug_erro_geral_pos_selecao.png')
        return False

def loop_movimentacao_processos(driver):
    """
    Loop principal: repete o fluxo de filtro, seleção e movimentação até não restarem processos.
    O fluxo completo é:
    1. Acessar lista de prazos
    2. Aplicar filtro de fase processual
    3. Calcular total de processos e lotes
    4. Para cada lote:
       4.1 Selecionar processos livres
       4.2 Registrar atividade para selecionados
       4.3 Movimentar processos
       4.4 Verificar resultado da movimentação
    """
    url_lista = 'https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos'
    print('\n[LOOP] Acessando lista de prazos para contagem inicial...')
    driver.get(url_lista)
    time.sleep(2)

    if not filtrar_fase_processual(driver):
        print('[LOOP][ERRO] Filtro de fase não aplicável. Encerrando loop.')
        return

    try:
        # Aguardar e obter total de registros
        total_elem = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.total-registros'))
        )
        total_text = total_elem.text.strip()
        print(f'[LOOP][DEBUG] Texto do total-registros: "{total_text}"')
        
        # Extrair número do texto
        match = re.search(r'(\d+)', total_text)
        total = int(match.group(1)) if match else 0
        print(f'[LOOP] Total de processos encontrados: {total}')
        
        if total == 0:
            print('[LOOP][AVISO] Nenhum processo encontrado após filtro.')
            driver.save_screenshot('debug_sem_processos_apos_filtro.png')
            return

        # Loop principal de processamento
        while True:
            print('\n[LOOP] === Iniciando novo ciclo de processamento ===')
            
            # 1. Selecionar processos livres
            num_selecionados, sucesso = selecionar_processos_livres(driver)
            
            if not sucesso:
                print('[LOOP][ERRO] Falha crítica na seleção de processos. Encerrando loop.')
                driver.save_screenshot('debug_erro_critico_selecao.png')
                return
                
            if num_selecionados == 0:
                print('[LOOP] Não há mais processos livres para processar. Encerrando loop.')
                return
                
            # 2. Processar os selecionados
            if not processar_apos_selecao(driver, num_selecionados):
                print('[LOOP][ERRO] Falha no processamento pós-seleção. Tentando próximo ciclo...')
                driver.save_screenshot('debug_erro_processamento.png')
                continue
                
            print('[LOOP] Ciclo completado com sucesso. Aguardando 2 segundos...')
            time.sleep(2)
            
    except Exception as e:
        print(f'[LOOP][ERRO] Erro geral no loop principal: {str(e)}')
        driver.save_screenshot('debug_erro_geral_loop.png')

if __name__ == "__main__":
    main()
