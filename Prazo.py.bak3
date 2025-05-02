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
from acoes import criar_gigs, extrair_documento, login_automatico # Importação correta da função criar_gigs
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

def selecionar_processos_livres(driver):
    """
    Seleciona processos "livres" na lista, conforme o seletor JS fornecido.
    Marca checkboxes dos processos que:
    - Não possuem prazo (coluna 9 vazia)
    - Não possuem comentário
    - Não possuem valor preenchido em input[matinput]
    - Não possuem ícone de pesquisa na coluna 3
    Retorna o número de processos selecionados.
    """
    # 1. Filtro de linhas (100 por página)
    try:
        btn_linhas = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-select-value-117'))
        )
        btn_linhas.click()
        print('[FILTRO][LINHAS] Dropdown de linhas clicado.')
        time.sleep(0.5)
        opcao_100 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mat-option-266 > span'))
        )
        opcao_100.click()
        print('[FILTRO][LINHAS] Selecionado 100 por página.')
        time.sleep(1)
    except Exception as e:
        print(f'[FILTRO][ERRO] Falha no filtro de linhas: {e}')
    print('Selecionando processos Livres e aplicando atividade...')
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        print(f'[DEBUG] Total de linhas encontradas na tabela: {len(linhas)}')
        selecionados = 0
        for idx, linha in enumerate(linhas):
            try:
                prazo = linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(9) time')
                prazo_vazio = not prazo or not prazo[0].text.strip()
            except Exception:
                prazo_vazio = True
            has_comment = len(linha.find_elements(By.CSS_SELECTOR, 'i.fa-comment')) > 0
            try:
                input_field = linha.find_elements(By.CSS_SELECTOR, 'input[matinput]')
                campo_preenchido = input_field and input_field[0].get_attribute('value').strip()
            except Exception:
                campo_preenchido = False
            tem_lupa = len(linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')) > 0
            print(f'[DEBUG] Linha {idx}: prazo_vazio={prazo_vazio}, comentario={bool(has_comment)}, campo_preenchido={bool(campo_preenchido)}, lupa={bool(tem_lupa)}')
            if prazo_vazio and not has_comment and not campo_preenchido and not tem_lupa:
                try:
                    checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type="checkbox"]')
                    if not checkbox.is_selected():
                        driver.execute_script('arguments[0].click()', checkbox)
                        driver.execute_script('arguments[0].style.backgroundColor = "#ffccd2";', linha)
                        selecionados += 1
                except Exception as e:
                    print(f'[DEBUG] Falha ao marcar checkbox na linha {idx}: {e}')
                    continue
        print(f'[DEBUG] Total de processos livres selecionados: {selecionados}')
        if selecionados == 0:
            driver.save_screenshot('screenshot_nenhum_processo_livre.png')
            print('Nenhum processo livre encontrado para seleção. Screenshot salvo.')
            return 0
        return selecionados
    except Exception as e:
        print(f'Erro ao selecionar processos livres: {e}')
        driver.save_screenshot('screenshot_atividade_silas_fail.png')
        print('[DEBUG] Screenshot salvo: screenshot_atividade_silas_fail.png')
        return 0

def movimentar_processos(driver):
    print('Movimentando processos...')
    try:
        clicar_fora_painel(driver)
        # Marcar todos os processos com ícone fa-check
        safe_click(driver, "//i[contains(@class, 'fa-check') and contains(@class, 'marcar-todas')]")
        time.sleep(0.7)
        clicar_fora_painel(driver)
        # Clicar no ícone de mala (fa-suitcase)
        safe_click(driver, "//i[contains(@class, 'fa-suitcase') and contains(@class, 'icone')]")
        print('[OK] Processos movimentados.')
        time.sleep(2)
        # Após clicar na mala, selecionar "Tarefa destino única"
        print('[MOV] Selecionando tarefa destino única...')
        # 1. Abrir select
        tarefa_select = driver.find_element(By.XPATH, "//span[contains(@class, 'mat-select-placeholder') and contains(@class, 'mat-select-min-line')]")
        driver.execute_script("arguments[0].click();", tarefa_select)
        time.sleep(1)
        # 2. Selecionar opção "Análise"
        opcoes = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-option-text')]")
        for opcao in opcoes:
            if 'análise' in opcao.text.strip().lower():
                driver.execute_script("arguments[0].click();", opcao)
                print('[MOV] Opção "Análise" selecionada.')
                time.sleep(1)
                break
        # 3. Clicar no botão "Movimentar processos"
        btns = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and contains(text(), 'Movimentar processos')]")
        for btn in btns:
            try:
                driver.execute_script("arguments[0].click();", btn)
                print('[MOV] Botão "Movimentar processos" clicado.')
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

def loop_movimentacao_processos(driver):
    """
    Loop principal: repete o fluxo de filtro, seleção e movimentação até não restarem processos.
    Antes da primeira execução, calcula o total de lotes (20 por vez) com base em .total-registros.
    """
    url_lista = 'https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos'
    print('\n[LOOP] Acessando lista de prazos para contagem inicial...')
    driver.get(url_lista)
    time.sleep(2)
    if not filtrar_fase_processual(driver):
        print('[LOOP] Filtro de fase não aplicável ou não há mais processos.')
        return
    try:
        total_elem = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.total-registros'))
        )
        total_text = total_elem.text.strip()
        print(f'[LOOP] Texto do total-registros: "{total_text}"')
        match = re.search(r'(\d+)', total_text)
        total = int(match.group(1)) if match else 0
        print(f'[LOOP] Total de processos encontrados: {total}')
        lotes = math.ceil(total / 20) if total > 0 else 0
        print(f'[LOOP] Serão necessários {lotes} loop(s) para processar todos os lotes (20 por vez).')
        if total == 0:
            print('[LOOP] Nenhum processo encontrado após filtro. Encerrando loop.')
            return
    except Exception as e:
        print(f'[LOOP][ERRO] Não foi possível ler o total de registros: {e}')
        return
    for i in range(lotes):
        print(f'\n[LOOP] Execução do lote {i+1}/{lotes}')
        try:
            filtrar_fase_processual(driver)
            movimentar_processos(driver)
            # Voltar para a lista usando ALT + seta esquerda
            print('[LOOP] Retornando à lista com ALT + seta esquerda.')
            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ALT, Keys.ARROW_LEFT)
            time.sleep(2)
        except Exception as e:
            print(f'[LOOP][ERRO] Erro durante a execução do lote {i+1}: {e}')
    print('[LOOP] Não há mais processos para movimentar.')

if __name__ == "__main__":
    main()
