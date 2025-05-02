# p1.py
# Fluxo automatizado do painel de prazos e análises PJe TRT2 usando Fix.py

from Fix import (
    esperar_elemento,
    safe_click,
    navegar_para_tela,
    criar_gigs,
    extrair_documento,
    processar_lista_processos,
    configurar_navegador,
    obter_driver_padronizado,
    login_pje_robusto,
    limpar_temp_selenium
)
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import re
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait

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

def processar_andamento(driver):
    """
    Processa o andamento dos processos livres com base no conteúdo do último ato judicial.
    """
    try:
        # Navega para a página de atividades
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        navegar_para_tela(driver, url=url_atividades)
        
        # Remover chip Vencidas
        chip_vencidas = esperar_elemento(driver, '.mat-chip-remove')
        safe_click(driver, chip_vencidas)
        time.sleep(0.5)
        
        # Clicar em atividades sem prazo
        btn_atividades_sem_prazo = esperar_elemento(driver, 'i.fa-pen:nth-child(1)')
        safe_click(driver, btn_atividades_sem_prazo)
        time.sleep(0.5)
        
        # Digitar xs no campo de descrição
        campo_descricao = esperar_elemento(driver, 'mat-form-field.ng-tns-c82-209 > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) input')
        campo_descricao.clear()
        campo_descricao.send_keys('xs')
        campo_descricao.send_keys(Keys.ENTER)
        time.sleep(1)
        
        # Aguardar lista filtrada
        linhas = esperar_colecao(driver, 'tr.cdk-drag')
        print(f'[ANDAMENTO] Total de processos filtrados: {len(linhas)}')
        
        for idx, linha in enumerate(linhas):
            try:
                # Abrir processo
                link_processo = linha.find_element(By.CSS_SELECTOR, 'a')
                safe_click(driver, link_processo)
                time.sleep(2)
                
                # Buscar último ato judicial
                from Fix import buscar_ultimo_ato_judicial
                autor, texto = buscar_ultimo_ato_judicial(driver)
                
                # Aplicar regras
                if autor in ['otavio', 'mariana']:
                    if re.search(r'concede-se 05 dias|visibilidade.*advogados|início da fluência|indicar meios|oito dias para apresentação', texto, re.IGNORECASE):
                        # Sobrestamento
                        criar_gigs(driver, 1, 'Guilerme', 'Sobrestamento')
                        ato_sobrestar(driver)
                    elif re.search(r'revel|concorda com homologação', texto, re.IGNORECASE):
                        # Homologação
                        criar_gigs(driver, 1, 'Silvia', 'Homologação')
                    elif re.search(r'hasta|saldo devedor|prescrição', texto, re.IGNORECASE):
                        # PEC
                        criar_gigs(driver, 1, 'xs', 'pec')
                    elif re.search(r'impugnações apresentadas', texto, re.IGNORECASE):
                        # Argos
                        criar_gigs(driver, 1, 'Silvia', 'Argos')
                        ato_pesquisas(driver)
                    elif re.search(r'cumprido o acordo homologado', texto, re.IGNORECASE):
                        # Arquivar
                        criar_gigs(driver, 0, 'pz', 'Arquivar')
                    else:
                        print(f'[ANDAMENTO] Nenhuma regra aplicável para o processo {idx}')
                else:
                    print(f'[ANDAMENTO] Autor não é Otávio ou Mariana: {autor}')
                
                # Fechar processo
                safe_click(driver, 'i.fas.fa-times')
                time.sleep(1)
                
            except Exception as e:
                logging.error(f'[ANDAMENTO][ERRO] Falha ao processar processo {idx}: {e}')
                driver.save_screenshot(f'screenshot_erro_processo_{idx}.png')
                continue
        
        logging.info('[ANDAMENTO] Todos os processos processados com sucesso.')
        
    except Exception as e:
        logging.error(f'[ANDAMENTO][ERRO] Falha no fluxo de andamento: {e}')
        driver.save_screenshot('screenshot_erro_andamento.png')
        raise

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
            raise Exception('[SELECAO][ERRO] Falha ao navegar para seção de Análises')
        
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
            logger.error(f'[SELECAO][ERRO] Falha no filtro de linhas: {e}')
            driver.save_screenshot('screenshot_erro_filtro_linhas.png')
            raise
        
        # Encontra todas as linhas da tabela
        logger.info('[SELECAO] Buscando linhas na tabela...')
        linhas = esperar_colecao(driver, 'tr.cdk-drag')
        logger.info(f'[SELECAO] Total de linhas encontradas: {len(linhas)}')
        selecionados = 0
        
        for idx, linha in enumerate(linhas):
            try:
                logger.info(f'[SELECAO] Processando linha {idx + 1}...')
                
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
                if prazo_vazio and not has_comment and not campo_preenchido and not tem_lupa:
                    try:
                        checkbox = linha.find_element(By.CSS_SELECTOR, 'mat-checkbox input[type="checkbox"]')
                        if not checkbox.is_selected():
                            driver.execute_script('arguments[0].click()', checkbox)
                            driver.execute_script('arguments[0].style.backgroundColor = "#ffccd2";', linha)
                            selecionados += 1
                            logger.info(f'[SELECAO] Linha {idx + 1} selecionada com sucesso.')
                    except Exception as e:
                        logger.error(f'[SELECAO][ERRO] Falha ao marcar checkbox na linha {idx + 1}: {e}')
                        driver.save_screenshot(f'screenshot_erro_checkbox_{idx + 1}.png')
                        continue
            except Exception as e:
                logger.error(f'[SELECAO][ERRO] Falha ao processar linha {idx + 1}: {e}')
                driver.save_screenshot(f'screenshot_erro_processamento_{idx + 1}.png')
                continue
        
        logger.info(f'[SELECAO] Total de processos livres selecionados: {selecionados}')
        if selecionados == 0:
            logger.warning('[SELECAO] Nenhum processo livre encontrado para seleção.')
            driver.save_screenshot('screenshot_nenhum_processo_livre.png')
            return 0
        
        # Registrar atividade em lote
        logger.info('[SELECAO] Registrando atividade em lote...')
        try:
            # Clicar no tag verde para aplicar atividade em lote
            tag_verde = esperar_elemento(driver, 'i.fa.fa-tag.icone.texto-verde')
            safe_click(driver, tag_verde)
            time.sleep(0.8)
            
            # Clicar em "Atividade" no menu
            span_atividade = esperar_elemento(driver, "//span[text()='Atividade']", by=By.XPATH)
            safe_click(driver, span_atividade)
            time.sleep(0.8)
            
            # Preencher e salvar atividade
            def preencher_atividade():
                try:
                    # Esperar e preencher dias
                    input_dias = esperar_elemento(driver, 'pje-gigs-cadastro-atividades input[formcontrolname="dias"]')
                    driver.execute_script("arguments[0].value = '0';", input_dias)
                    input_dias.send_keys('0')
                    input_dias.send_keys(Keys.TAB)
                    
                    # Esperar e preencher observação
                    textarea_obs = esperar_elemento(driver, 'pje-gigs-cadastro-atividades textarea[formcontrolname="observacao"]')
                    driver.execute_script("arguments[0].value = 'xs';", textarea_obs)
                    textarea_obs.send_keys('xs')
                    textarea_obs.send_keys(Keys.TAB)
                    
                    # Esperar e clicar em salvar
                    btn_salvar = esperar_elemento(driver, 'pje-gigs-cadastro-atividades button[type="submit"].mat-primary')
                    safe_click(driver, btn_salvar)
                    time.sleep(1.2)
                    
                    logger.info('[ATIVIDADE] Atividade registrada com sucesso para o lote.')
                    return True
                except Exception as e:
                    logger.error(f'[ATIVIDADE][ERRO] Falha ao preencher atividade: {e}')
                    return False
            
            if not preencher_atividade():
                raise Exception('[ATIVIDADE][ERRO] Falha ao preencher atividade')
            
        except Exception as e:
            logger.error(f'[SELECAO][ERRO] Falha ao registrar atividade em lote: {e}')
            driver.save_screenshot('screenshot_erro_atividade.png')
            raise
        
        logger.info('[SELECAO] Seleção de processos e atividade concluída com sucesso.')
        return selecionados
        
    except Exception as e:
        logger.error(f'[SELECAO][ERRO] Erro crítico na seleção de processos: {e}')
        driver.save_screenshot('screenshot_erro_selecao.png')
        raise
        
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

def processar_lote(driver, num_lote):
    """Processa todos os itens do lote atual"""
    # 1. Processar andamentos
    if not processar_andamento(driver):
        raise Exception('Falha ao processar andamentos')
    
    # 2. Movimentar processos
    if not movimentar_processos(driver):
        raise Exception('Falha ao movimentar processos')
    
    # 3. Verificar conclusão
    if not verificar_conclusao(driver):
        raise Exception('Processos não concluídos corretamente')

def fazer_login():
    """
    Wrapper simplificado para login
    """
    driver = obter_driver_padronizado()
    return login_pje_robusto(driver)

def obter_driver():
    from selenium.webdriver import Firefox
    from selenium.webdriver.firefox.options import Options
    
    opts = Options()
    opts.profile = '/caminho/do/seu/perfil/firefox-dev'  # Ajuste conforme seu ambiente
    return Firefox(options=opts)

def main():
    """
    Fluxo principal de automação do PJe TRT2.
    1. Configura navegador e faz login
    2. Navega para painel de prazos
    3. Processa lotes de processos
    """
    try:
        # Limpeza inicial
        logger.info('[SCRIPT] Iniciando script...')
        limpar_temp_selenium()
        logger.info('[SCRIPT] Limpeza inicial concluída.')
        
        # Configuração do navegador
        logger.info('[CONFIG] Configurando navegador...')
        driver = fazer_login()
        if not driver:
            raise Exception('[CONFIG][ERRO] Falha ao configurar navegador')
        logger.info('[CONFIG] Navegador configurado com sucesso.')
        
        # Navegação para o painel de prazos
        logger.info('[NAVEGAR] Navegando para painel de prazos...')
        url_painel = 'https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos'
        navegar_result = navegar_para_tela(driver, url=url_painel)
        if not navegar_result:
            driver.save_screenshot('screenshot_erro_navegacao.png')
            raise Exception(f'[NAVEGAR][ERRO] Falha ao navegar para {url_painel}')
        logger.info('[NAVEGAR] Navegação concluída.')
        
        # Espera até que o sistema esteja totalmente carregado
        def sistema_pronto(driver):
            try:
                # Verifica spinner/loading
                loadings = driver.find_elements(By.CSS_SELECTOR, '.loading-spinner, .mat-progress-spinner')
                if any(loading.is_displayed() for loading in loadings):
                    return False
                
                # Verifica se a tabela principal está visível
                tabela = driver.find_element(By.CSS_SELECTOR, 'mat-table.mat-table')
                return tabela.is_displayed()
            except:
                return False
        
        # Aguarda até 60 segundos pelo carregamento
        WebDriverWait(driver, 60).until(sistema_pronto)
        
        # Extração definitiva do total
        try:
            # Método 1: Via elemento de total
            total_elem = driver.find_element(By.CSS_SELECTOR, 'span.total-registros')
            texto = total_elem.text.strip()
            if 'de' in texto:
                total = int(texto.split('de')[-1].strip().split()[0])
                logger.info(f'[LOOP] Total oficial: {total} processos')
            else:
                raise ValueError('Formato não reconhecido')
        except Exception as e:
            # Método 2: Contagem direta como fallback
            processos = driver.find_elements(By.CSS_SELECTOR, 'mat-row.mat-row')
            total = len(processos)
            logger.warning(f'[LOOP] Total estimado: {total} processos (fallback)')
        
        if total == 0:
            driver.save_screenshot('screenshot_sem_processos.png')
            logger.error('[LOOP][ERRO CRÍTICO] Nenhum processo encontrado após carregamento completo')
            raise Exception('Nenhum processo encontrado - verifique manualmente')
        
        # Cálculo de lotes
        ITENS_POR_PAGINA = 20
        lotes = max(1, (total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
        logger.info(f'[LOOP] Total confirmado: {total} processos ({lotes} lotes)')
        
        # Processa cada lote
        for lote_atual in range(lotes):
            try:
                # Processa o lote atual
                logger.info(f'[LOOP] Processando andamento do lote {lote_atual}...')
                
                # Verifica se há processos antes de continuar
                processos = esperar_elemento(driver, 'mat-row.mat-row', timeout=10)
                if not processos:
                    driver.save_screenshot('screenshot_sem_processos_lote.png')
                    logger.warning('[LOOP] Nenhum processo encontrado no lote - pulando')
                    continue
                        
                # Executa o processamento
                resultado = processar_andamento(driver)
                
                if not resultado:
                    driver.save_screenshot('screenshot_erro_processamento.png')
                    logger.error('[LOOP] Falha no processamento - continuando para próximo lote')
                    continue
                        
            except Exception as e:
                driver.save_screenshot('screenshot_erro_critico.png')
                logger.error(f'[LOOP][ERRO] Falha crítica: {str(e)}')
                raise

        # Após processar todos os lotes, vai para processos livres
        logger.info('[SELECAO] Iniciando seleção de processos livres...')
        selecionar_processos_livres(driver)
            
        logger.info('[LOOP] Todos os lotes processados com sucesso.')
                
        logger.info(f'[LOOP] Lote {lote_atual} processado com sucesso.')
            
    except Exception as e:
        logger.error(f'[SCRIPT][ERRO] Erro crítico: {str(e)}')
        driver.save_screenshot('screenshot_erro_critico.png')
        raise
            
if __name__ == '__main__':
    main()
