import logging
logger = logging.getLogger(__name__)

"""
Navigation - Filtros e Navegação PJe
=====================================

Extração do Fix/core.py → navigation/ (~500 linhas)

FUNÇÕES EXTRAÍDAS (lines 1998-2270):
- aplicar_filtro_100: Aplica filtro 100 processos por página
- filtro_fase: Seleciona fases Execução e Liquidação
- filtrofases: Filtro complexo de fases e tarefas

RESPONSABILIDADE:
- Aplicar filtros no painel PJe
- Navegar entre fases processuais
- Selecionar tarefas específicas

DEPENDÊNCIAS:
- selenium.webdriver
- Fix.selenium_base: aguardar_e_clicar, com_retry, js_base
- Fix.log: logger

USO TÍPICO:
    from Fix.navigation import aplicar_filtro_100, filtro_fase, filtrofases
    
    # Filtrar 100 processos
    aplicar_filtro_100(driver)
    
    # Filtrar fases
    filtro_fase(driver)
    
    # Filtro complexo
    filtrofases(driver, fases_alvo=['liquidação', 'execução'])

AUTOR: Extração PJePlus Refactoring Phase 2
DATA: 2025-01-29
"""

import time
from typing import List, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Fix.selenium_base.retry_logic import com_retry
from Fix.selenium_base.wait_operations import aguardar_e_clicar, _aguardar_loader_painel
from Fix.selenium_base.js_helpers import js_base
from Fix.log import logger

def aplicar_filtro_100(driver: WebDriver) -> bool:
    """
    Aplica filtro para exibir 100 itens por página no painel global.
    
    OTIMIZADO: Usa selecionar_opcao() + com_retry() - 1 requisição vs 8-12 anteriores.
    
    Args:
        driver: WebDriver do Selenium
    
    Returns:
        True se aplicou com sucesso, False caso contrário
    
    Exemplo:
        driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        aplicar_filtro_100(driver)
    
    Notas:
        - Usa zoom 50% para facilitar cliques
        - Retry automático com 3 tentativas
        - Backoff exponencial base 1.5s
    """
    try:
        # Zoom out para facilitar cliques
        driver.execute_script("document.body.style.zoom='50%'")
        time.sleep(0.3)
        
        # Função interna para selecionar com múltiplos seletores
        def _selecionar():
            try:
                # Buscar dropdown por texto "20"
                span_20 = driver.find_element(
                    By.XPATH,
                    "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']"
                )
                mat_select = span_20.find_element(
                    By.XPATH,
                    "ancestor::mat-select[@role='combobox']"
                )
                mat_select.click()
                time.sleep(0.5)
                
                # Aguardar overlay aparecer
                overlay = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                
                # Clicar em opção "100"
                opcao_100 = overlay.find_element(
                    By.XPATH,
                    ".//mat-option[.//span[normalize-space(text())='100']]"
                )
                opcao_100.click()
                time.sleep(1)
                
                return True
                
            except Exception as e:
                logger.error(f'[FILTRO_LISTA_100][ERRO] Falha ao clicar em 100: {e}')
                return False

        # Aplica com retry automático
        resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log_enabled=True)

        if resultado:
            pass
        else:
            logger.error('Filtro lista 100 falhou após todas tentativas')

        return resultado
        
    except Exception as e:
        logger.error(f'[FILTRO_LISTA_100][ERRO] Falha geral: {e}')
        return False

def filtro_fase(driver: WebDriver) -> bool:
    """
    Seleciona fases 'Execução' e 'Liquidação' no filtro global.
    
    OTIMIZADO: Usa aguardar_e_clicar() + js_base() - 3 req vs 10-15 anteriores.
    
    Args:
        driver: WebDriver do Selenium
    
    Returns:
        True se aplicou com sucesso, False caso contrário
    
    Exemplo:
        driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        filtro_fase(driver)
    
    Notas:
        - Seleciona automaticamente "Execução" e "Liquidação"
        - Usa JavaScript para seleção rápida
        - Fecha dropdown com ESC após seleção
    """
    try:
        seletor = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'
        
        # Abre dropdown com aguardar_e_clicar (MutationObserver)
        if not aguardar_e_clicar(driver, seletor, timeout=5, usar_js=True):
            logger.error('[FILTRO_FASE][ERRO] Dropdown não encontrado.')
            return False
        
        time.sleep(0.3)
        
        # Seleciona ambas fases usando JavaScript (1 requisição)
        script = f"""
        {js_base()}
        
        const fases = ['Execução', 'Liquidação'];
        let sucesso = 0;
        
        for (const fase of fases) {{
            const opcao = Array.from(document.querySelectorAll('mat-option span.mat-option-text'))
                .find(el => el.textContent.trim() === fase);
            
            if (opcao && opcao.parentElement) {{
                opcao.parentElement.click();
                sucesso++;
            }}
        }}
        
        return sucesso;
        """
        
        selecionadas = driver.execute_script(script)
        
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        
        return True
        
    except Exception as e:
        logger.error(f'Falha no filtro de fase: {e}')
        return False

def filtrofases(
    driver: WebDriver,
    fases_alvo: List[str] = ['liquidação', 'execução'],
    tarefas_alvo: Optional[List[str]] = None,
    seletor_tarefa: str = 'Tarefa do processo'
) -> bool:
    """
    Filtro complexo de fases e tarefas com suporte a múltiplas opções.
    
    Args:
        driver: WebDriver do Selenium
        fases_alvo: Lista de fases a selecionar (default: ['liquidação', 'execução'])
        tarefas_alvo: Lista de tarefas a selecionar (opcional)
        seletor_tarefa: Texto do seletor de tarefa (default: 'Tarefa do processo')
    
    Returns:
        True se aplicou com sucesso, False caso contrário
    
    Exemplo Básico:
        filtrofases(driver)  # Fases liquidação e execução
    
    Exemplo com Tarefas:
        filtrofases(
            driver,
            fases_alvo=['liquidação', 'execução'],
            tarefas_alvo=['Análise de processo', 'Cálculo']
        )
    
    Exemplo Customizado:
        filtrofases(
            driver,
            fases_alvo=['execução'],
            tarefas_alvo=['Análise'],
            seletor_tarefa='Tarefa específica'
        )
    
    Notas:
        - Usa JavaScript para cliques robustos
        - Suporta múltiplas fases e tarefas
        - Aguarda carregamento entre filtros
        - Fecha dropdowns com ESC
    """
    
    try:
        # ========================================
        # ETAPA 1: FILTRAR FASES
        # ========================================
        fase_element = None
        
        # Tentar múltiplos seletores para fase
        try:
            fase_element = driver.find_element(
                By.XPATH,
                "//span[contains(text(), 'Fase processual')]"
            )
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                logger.error('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        
        if not fase_element:
            logger.error('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        
        # Clicar para abrir dropdown
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        
        # Aguardar painel aparecer
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
            logger.error('[ERRO] Painel de opções não apareceu.')
            return False
        
        # Aguardar opções reais aparecerem no painel
        opcoes = []
        for _ in range(20):
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            textos = [o.text.strip().lower() for o in opcoes if o.text.strip()]
            if any(fase in texto for fase in fases_alvo for texto in textos):
                break
            if textos and not any(t in ['nenhuma opção', 'carregando itens...'] for t in textos):
                break
            time.sleep(0.3)

        # Selecionar fases
        fases_clicadas = set()
        
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        
        if len(fases_clicadas) == 0:
            logger.error(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        
        # Aplicar filtro de fase
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            time.sleep(1)
            _aguardar_loader_painel(driver)
        except Exception as e:
            logger.error(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        
        # ========================================
        # ETAPA 2: FILTRAR TAREFAS (OPCIONAL)
        # ========================================
        if tarefas_alvo:
            
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(
                    By.XPATH,
                    f"//span[contains(text(), '{seletor_tarefa}')]"
                )
            except Exception:
                try:
                    seletor = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                        if seletor_tarefa in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    logger.error(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                    return False
            
            if not tarefa_element:
                logger.error(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                return False
            
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            
            # Aguardar painel de tarefas
            painel = None
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            
            if not painel or not painel.is_displayed():
                logger.error('[ERRO] Painel de opções de tarefa não apareceu.')
                return False

            # Aguardar opções reais de tarefa aparecerem
            opcoes = []
            for _ in range(20):
                opcoes = painel.find_elements(By.XPATH, ".//mat-option")
                textos = [o.text.strip().lower() for o in opcoes if o.text.strip()]
                if any(tarefa.lower() in texto for tarefa in tarefas_alvo for texto in textos):
                    break
                if textos and not any(t in ['nenhuma opção', 'carregando itens...'] for t in textos):
                    break
                time.sleep(0.3)

            # Selecionar tarefas
            tarefas_clicadas = set()
            
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        tarefa_lower = tarefa.lower()
                        
                        # Matching flexível
                        encontrado = (
                            tarefa_lower in texto or
                            any(word in texto for word in tarefa_lower.split()) or
                            texto == tarefa_lower
                        )
                        
                        if encontrado and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            
            if len(tarefas_clicadas) == 0:
                logger.error(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            
            # Aplicar filtro de tarefas
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                time.sleep(1)
                _aguardar_loader_painel(driver)
            except Exception as e:
                logger.error(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
        
        return True
        
    except Exception as e:
        logger.error(f'[ERRO] Erro no filtro de fase: {e}')
        return False
