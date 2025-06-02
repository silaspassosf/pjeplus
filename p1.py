# p1.py
# Fluxo automatizado do painel de prazos e análises PJe TRT2 usando Fix.py

from Fix import (
    esperar_elemento,
    safe_click,
    criar_gigs,
    extrair_documento,
    processar_lista_processos,
    driver_notebook,
    login_notebook,
    limpar_temp_selenium,
    buscar_seletor_robusto  # Adicionado para uso de seletores robustos
)
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import re
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait
import traceback
from selenium.common.exceptions import TimeoutException

# URL base do sistema
URL_BASE = 'https://pje.trt2.jus.br/pjekz/'

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PJeAutomation')

def esperar_colecao(driver, seletor, timeout=10):
    """Espera e retorna uma coleção de elementos"""
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, seletor)
        )
    except TimeoutException:
        logging.error(f'[ESPERA][ERRO] Timeout esperando elementos: {seletor}')
        return []

def inicializar_driver():
    """Inicializa o driver do Selenium"""
    logger = logging.getLogger('PJeAutomation')
    try:
        logger.info("[DRIVER] Iniciando driver...")
        options = webdriver.FirefoxOptions()
        # ... configuração do driver ...
        driver = webdriver.Firefox(options=options)
        logger.info("[DRIVER] Driver iniciado com sucesso")
        return driver
    except Exception as e:
        logger.error(f"[DRIVER][ERRO] Falha ao inicializar driver: {str(e)}")
        return False



def filtrar_fase_processual(driver, fases_alvo=None):
    """
    Filtra as fases desejadas no painel global do PJe.
    Por padrão, seleciona 'Liquidação' e 'Execução'.
    Após selecionar, clica no botão de filtrar (ícone fa-filter).
    """
    from selenium.webdriver.common.by import By
    import time
    if fases_alvo is None:
        fases_alvo = ['liquidação', 'execução']
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        # 1. Clica no seletor de fase processual
        fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)

        # 2. Seleciona as fases desejadas
        for fase in fases_alvo:
            opcao = driver.find_element(By.XPATH, f"//span[contains(translate(text(), 'ÇÃLIUEO', 'çãliueo'), '{fase}')]")
            driver.execute_script("arguments[0].click();", opcao)
            time.sleep(0.5)

        # 3. NÃO clicar no botão de filtrar
        # 4. Navegação por teclado: pressionar TAB 6x e depois ESPAÇO
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(driver)
        for _ in range(6):
            actions.send_keys(Keys.TAB)
            time.sleep(0.2)
        actions.send_keys(Keys.SPACE)
        actions.perform()
        print('[OK] Fases selecionadas e filtro aplicado via navegação por teclado.')
        time.sleep(1)
        return True
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False

def movimentar_processos(driver):
    """
    Movimenta os processos selecionados para a tarefa 'Análise'.
    O fluxo é:
    1. Marca todos os processos usando o ícone check (agora apenas via navegação por teclado)
    2. Inicia movimentação pelo ícone mala (suitcase)
    3. Seleciona 'Análise' como tarefa destino
    4. Confirma movimentação dos processos
    """
    print('Movimentando processos...')
    try:
        total_elem = WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.CSS_SELECTOR, '.total-registros')
        )
        total_text = total_elem.text.strip()
        match = re.search(r'(\d+)$', total_text)
        total = int(match.group(1)) if match else 0
        blocos = (total + 19) // 20 if total > 0 else 0
        logger.info(f'[BLOCOS] Total de processos: {total} | Número de loops (blocos de 20): {blocos}')
    except Exception as e:
        logger.error(f'[BLOCOS][ERRO] Falha ao obter total de processos: {e}')
        total = 0
        blocos = 0
    try:
        # Não tentar clicar no botão de marcar todas, apenas navegação por teclado já foi feita no filtro
        time.sleep(0.7)
        # 2. Iniciar movimentação
        safe_click(driver, "//i[contains(@class, 'fa-suitcase') and contains(@class, 'icone')]", by=By.XPATH)
        print('[OK] Processos selecionados para movimentação.')
        time.sleep(2)
        # 3. Selecionar tarefa destino única
        print('[MOV] Selecionando tarefa destino única...')
        tarefa_select = driver.find_element(By.XPATH, "//span[contains(@class, 'mat-select-placeholder') and contains(@class, 'mat-select-min-line')]")
        driver.execute_script("arguments[0].click();", tarefa_select)
        time.sleep(1)
        # 4. Selecionar opção "Análise"
        opcoes = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-option-text')]")
        for opcao in opcoes:
            if 'análise' in opcao.text.strip().lower():
                driver.execute_script("arguments[0].click();", opcao)
                print('[MOV] Opção "Análise" selecionada.')
                time.sleep(1)
                break
        # 5. Confirmar movimentação
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

def selecionar_processos_livres(driver):
    """
    Seleciona processos livres na seção de Análises e registra atividade em lote.
    """
    try:
        logger.info('[SELECAO] Iniciando seleção de processos livres...')
        
        # Navega para a seção de Análises
        url_analises = 'https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos'
        logger.info(f'[SELECAO] Navegando para {url_analises}...')
        if not navegar_para_tela(driver, url=url_analises):
            logger.error('[SELECAO][ERRO] Falha ao navegar para seção de Análises')
            return False
        
        # Configura 100 linhas por página
        logger.info('[SELECAO] Configurando 100 linhas por página...')
        try:
            btn_linhas = esperar_elemento(driver, '#mat-select-value-117')
            safe_click(driver, btn_linhas)
            opcao_100 = esperar_elemento(driver, '#mat-option-266 > span')
            safe_click(driver, opcao_100)
            time.sleep(1)
            logger.info('[SELECAO] Configuração de 100 linhas concluída.')
        except Exception as e:
            logger.error(f'[SELECAO][ERRO] Falha no filtro de linhas: {str(e)}')
            return False
        
        # Encontra todas as linhas da tabela
        logger.info('[SELECAO] Buscando linhas na tabela...')
        linhas = esperar_colecao(driver, 'tr.cdk-drag')
        logger.info(f'[SELECAO] Total de linhas encontradas: {len(linhas)}')
        selecionados = 0
        
        for idx, linha in enumerate(linhas):
            try:
                logger.debug(f'[SELECAO] Processando linha {idx + 1}...')
                
                # Verifica se não tem prazo (coluna 9 vazia)
                prazo = linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(9) time')
                prazo_vazio = not prazo or not prazo[0].text.strip()
                logger.debug(f'[SELECAO] Linha {idx + 1} - Prazo vazio: {prazo_vazio}')
                
                # Verifica se não tem comentário
                has_comment = len(linha.find_elements(By.CSS_SELECTOR, 'i.fa-comment')) > 0
                logger.debug(f'[SELECAO] Linha {idx + 1} - Tem comentário: {has_comment}')
                
                # Verifica se não tem valor em input[matinput]
                try:
                    input_field = linha.find_elements(By.CSS_SELECTOR, 'input[matinput]')
                    campo_preenchido = input_field and input_field[0].get_attribute('value').strip()
                except Exception:
                    campo_preenchido = False
                logger.debug(f'[SELECAO] Linha {idx + 1} - Campo preenchido: {campo_preenchido}')
                
                # Verifica se não tem ícone de pesquisa na coluna 3
                tem_lupa = len(linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')) > 0
                logger.debug(f'[SELECAO] Linha {idx + 1} - Tem ícone de pesquisa: {tem_lupa}')
                
                # Se atende todos os critérios
                
                # Verifica se não tem ícone de pesquisa na coluna 3
                tem_lupa = len(linha.find_elements(By.CSS_SELECTOR, 'td:nth-child(3) i.fa-search')) > 0
                logger.debug(f'[SELECAO] Linha {idx + 1} - Tem ícone de pesquisa: {tem_lupa}')
                
                # Se atende todos os critérios
                if prazo_vazio and not has_comment and not campo_preenchido and not tem_lupa:
                    try:
                        checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type="checkbox"]')
                        if not checkbox.is_selected():
                            driver.execute_script('arguments[0].click()', checkbox)
                            driver.execute_script('arguments[0].style.backgroundColor = "#ffccd2";', linha)
                            selecionados += 1
                            logger.info(f'[SELECAO] Linha {idx + 1} selecionada com sucesso.')
                    except Exception as e:
                        logger.error(f'[SELECAO][ERRO] Falha ao marcar checkbox na linha {idx + 1}: {str(e)}')
                        continue
            except Exception as e:
                logger.error(f'[SELECAO][ERRO] Falha ao processar linha {idx + 1}: {str(e)}')
                continue
        
        logger.info(f'[SELECAO] Total de processos livres selecionados: {selecionados}')
        if selecionados == 0:
            logger.warning('[SELECAO] Nenhum processo livre encontrado para seleção.')
            return 0
        
        # Registrar atividade em lote
        logger.info('[SELECAO] Registrando atividade em lote...')
        try:
            # Clicar no tag verde para aplicar atividade em lote
            tag_verde = esperar_elemento(driver, 'i.fa.fa-tag.icone.texto-verde')
            safe_click(driver, tag_verde)
            time.sleep(0.8)
            
            def preencher_atividade():
                try:
                    # Esperar e preencher dias
                    input_dias = esperar_elemento(driver, 'pje-gigs-cadastro-atividades input[formcontrolname="dias"]')
                    driver.execute_script("arguments[0].value = '0';", input_dias)
                    input_dias.send_keys('0')
                    input_dias.send_keys(Keys.TAB)

                    # Esperar e preencher observação
                    textarea_obs = esperar_elemento(driver, 'pje-gigs-cadastro-atividades textarea[formcontrolname="observacao"]')
                    driver.execute_script("arguments[0].value = 'pz checar';", textarea_obs)
                    textarea_obs.send_keys('pz checar')
                    textarea_obs.send_keys(Keys.TAB)

                    # Esperar e clicar em salvar
                    btn_salvar = esperar_elemento(driver, 'pje-gigs-cadastro-atividades button[type="submit"].mat-primary')
                    safe_click(driver, btn_salvar)
                    time.sleep(1.2)

                    logger.info('[ATIVIDADE] Atividade registrada com sucesso para o lote.')
                    return True
                except Exception as e:
                    logger.error(f'[ATIVIDADE][ERRO] Falha ao preencher atividade: {str(e)}')
                    return False

            if not preencher_atividade():
                logger.error('[ATIVIDADE][ERRO] Falha ao preencher atividade')
                return False
            
        except Exception as e:
            logger.error(f'[SELECAO][ERRO] Falha ao registrar atividade em lote: {str(e)}')
            return False
        
        logger.info('[SELECAO] Seleção de processos e atividade concluída com sucesso.')
        return selecionados
    except Exception as e:
        logger.error(f'[SELECAO][ERRO] Erro crítico na seleção de processos: {str(e)}')
        return False

def navegar_para_pagina(driver, numero_pagina):
    """Navega para página específica usando padrão Fix.py"""
    try:
        seletor = f'a.page-link[data-page="{numero_pagina}"]'
        btn_pagina = esperar_elemento(driver, seletor, timeout=10)
        if btn_pagina:
            safe_click(driver, btn_pagina)
            time.sleep(1)  # Espera carregamento
            return True
        return False
    except Exception as e:
        logger.error(f'[NAVEGACAO][ERRO] Página {numero_pagina}: {str(e)}')
        return False


def fazer_login():
    """
    Wrapper simplificado para login
    """
    driver = driver_notebook()
    return login_notebook(driver)

def obter_driver():
    from selenium.webdriver import Firefox
    from selenium.webdriver.firefox.options import Options
    
    opts = Options()
    opts.profile = '/caminho/do/seu/perfil/firefox-dev'  # Ajuste conforme seu ambiente
    return Firefox(options=opts)

def loop_principal(driver):
    # 1. Aplicar filtro de fases apenas uma vez
    if not filtrar_fase_processual(driver):
        logger.info('[LOOP] Filtro de fase processual não aplicável ou sem processos. Encerrando loop.')
        return
    # 2. Contabilizar blocos/lotes
    try:
        total_elem = WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.CSS_SELECTOR, '.total-registros')
        )
        total_text = total_elem.text.strip()
        match = re.search(r'(\d+)$', total_text)
        total = int(match.group(1)) if match else 0
        blocos = (total + 19) // 20 if total > 0 else 0
        logger.info(f'[BLOCOS] Total de processos: {total} | Número de loops (blocos de 20): {blocos}')
    except Exception as e:
        logger.error(f'[BLOCOS][ERRO] Falha ao obter total de processos: {e}')
    # 3. Prosseguir com a movimentação
    while True:
        movimentar_processos(driver)
        # Sair da tela com ALT + seta para a esquerda
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).key_down(u'\ue00c').send_keys(u'\ue012').key_up(u'\ue00c').perform()  # ALT + seta esquerda
        time.sleep(1)
        # Checar se ainda há processos para movimentar
        try:
            total_elem = WebDriverWait(driver, 5).until(
                lambda d: d.find_element(By.CSS_SELECTOR, '.total-registros')
            )
            total_text = total_elem.text.strip()
            match = re.search(r'(\d+)$', total_text)
            total = int(match.group(1)) if match else 0
            if total == 0:
                logger.info('[LOOP] Não há mais processos para movimentar. Encerrando loop.')
                break
        except Exception:
            logger.info('[LOOP] Não foi possível obter o total de processos. Encerrando loop.')
            break

def main():
    logger.info("[SCRIPT] Iniciando automação...")
    driver = driver_notebook()
    if not driver:
        logger.error("[SCRIPT][ERRO] Falha ao inicializar driver")
        return
    if not login_notebook(driver):
        logger.error("[SCRIPT][ERRO] Falha no login. Encerrando script.")
        driver.quit()
        return
    logger.info("[SCRIPT] Login realizado com sucesso.")
    # Maximizar a janela do navegador após login
    try:
        driver.maximize_window()
        logger.info("[SCRIPT] Janela do navegador maximizada.")
    except Exception as e:
        logger.warning(f"[SCRIPT][WARN] Não foi possível maximizar a janela: {e}")
    url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    logger.info(f"[SCRIPT] Navegando diretamente para {url_lista} ...")
    driver.get(url_lista)
    time.sleep(2)
    loop_principal(driver)
    driver.quit()
    logger.info("[SCRIPT] Driver encerrado")

if __name__ == "__main__":
    main()
