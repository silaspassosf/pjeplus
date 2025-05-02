import os
import sys
import re
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_automacao.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PJeAutomation')

# Importa funções do Fix.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Fix import esperar_elemento, safe_click, navegar_para_tela

def fazer_login(driver):
    """Realiza o login no PJe."""
    try:
        logger.info('[LOGIN] Iniciando login no PJe')
        
        # Acessa a página de login
        driver.get('https://pje.trt2.jus.br/pjekz/')
        
        # Preenche credenciais
        usuario = esperar_elemento(driver, '#username')
        usuario.clear()
        usuario.send_keys(os.getenv('PJE_USUARIO'))
        
        senha = esperar_elemento(driver, '#password')
        senha.clear()
        senha.send_keys(os.getenv('PJE_SENHA')))
        
        # Clica no botão de login
        btn_login = esperar_elemento(driver, '#login-button')
        safe_click(driver, btn_login)
        
        logger.info('[LOGIN] Login realizado com sucesso')
        return True
    except Exception as e:
        logger.error(f'[LOGIN][ERRO] Falha no login: {str(e)}')
        driver.save_screenshot('screenshot_erro_login.png')
        return False

def processar_andamento(driver):
    """Processa o andamento dos processos."""
    try:
        logger.info('[ANDAMENTO] Iniciando processamento de andamentos')
        
        # Sua implementação do processar_andamento aqui
        # ...
        
        return True
    except Exception as e:
        logger.error(f'[ANDAMENTO][ERRO] Falha no fluxo de andamento: {str(e)}')
        driver.save_screenshot('screenshot_erro_andamento.png')
        return False

def selecionar_processos_livres(driver):
    """Seleciona processos livres para análise."""
    try:
        logger.info('[SELECAO] Iniciando seleção de processos livres')
        
        # Sua implementação do selecionar_processos_livres aqui
        # ...
        
        return True
    except Exception as e:
        logger.error(f'[SELECAO][ERRO] Falha na seleção de processos: {str(e)}')
        driver.save_screenshot('screenshot_erro_selecao.png')
        return False

def main():
    """Função principal."""
    try:
        logger.info('[SCRIPT] Iniciando automação PJe')
        
        # Configuração do driver
        from selenium import webdriver
        options = webdriver.FirefoxOptions()
        options.set_preference('permissions.default.image', 2)
        driver = webdriver.Firefox(options=options)
        
        try:
            # Login
            if not fazer_login(driver):
                raise Exception('Falha no login')
            
            # Navega para a lista de processos
            url_painel = 'https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos'
            if not navegar_para_tela(driver, url=url_painel):
                raise Exception(f'[NAVEGAR][ERRO] Falha ao navegar para {url_painel}')
            logger.info('[NAVEGAR] Navegação concluída.')
            
            # Verifica carregamento completo
            def sistema_pronto(driver):
                try:
                    loadings = driver.find_elements(By.CSS_SELECTOR, '.loading-spinner, .mat-progress-spinner')
                    if any(loading.is_displayed() for loading in loadings):
                        return False
                    tabela = driver.find_element(By.CSS_SELECTOR, 'mat-table.mat-table')
                    return tabela.is_displayed()
                except:
                    return False
            
            WebDriverWait(driver, 60).until(sistema_pronto)
            logger.info('[SCRIPT] Sistema carregado com sucesso')
            
            # Aqui você pode adicionar ações específicas para teste
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f'[SCRIPT][ERRO] Erro crítico: {str(e)}')
        driver.save_screenshot('screenshot_erro_critico.png')
        raise

if __name__ == '__main__':
    main()
