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
import os
import datetime
from typing import List, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Fix.selenium_base.retry_logic import com_retry
from Fix.selenium_base.wait_operations import aguardar_e_clicar, _aguardar_loader_painel
from Fix.selenium_base.js_helpers import js_base
from Fix.selenium_base.element_interaction import safe_click
from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.log import logger


def _dump_debug_snapshot(content: str, label: str) -> None:
    """Grava um snapshot de depuração em logs_execucao para análise posterior."""
    try:
        # gravar em logs_execucao na raiz do projeto (duas pastas acima: Fix/navigation -> Fix -> projeto)
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        logs_dir = os.path.join(base, 'logs_execucao')
        os.makedirs(logs_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        fname = f'filter100_{label}_{ts}.log'
        path = os.path.join(logs_dir, fname)
        with open(path, 'w', encoding='utf-8') as fh:
            if isinstance(content, bytes):
                try:
                    fh.write(content.decode('utf-8', errors='replace'))
                except Exception:
                    fh.write(str(content))
            else:
                fh.write(str(content))
        logger.info(f'[FILTRO_LISTA_100] Debug snapshot gravado: {path}')
    except Exception:
        logger.exception('[FILTRO_LISTA_100] Falha ao gravar snapshot de depuração')

def aplicar_filtro_100(driver: WebDriver) -> bool:
    """
    Aplica filtro para exibir 100 itens por página no painel global.
    Esta versão foi alinhada com a implementação do LEGADO para evitar regressões.
    """
    try:
        # marcar entrada para depuração
        try:
            _dump_debug_snapshot('ENTER aplicar_filtro_100', 'entry')
        except Exception:
            pass

        # zoom para facilitar cliques em interfaces com alta densidade
        try:
            driver.execute_script("document.body.style.zoom='50%'")
        except Exception:
            pass
        time.sleep(0.3)

        # Verificar estado atual do filtro antes de tentar alteração
        for selector in [
            "mat-select[formcontrolname] .mat-select-value-text span",
            "mat-select[role='combobox'] .mat-select-value-text span",
        ]:
            try:
                value = driver.execute_script(
                    f"const el = document.querySelector('{selector}'); return el ? el.textContent.trim() : null;"
                )
                if value == '100':
                    logger.info('[FILTRO_LISTA_100] Já está em 100; pular.')
                    return True
            except Exception:
                continue

        def _selecionar():
            try:
                # Tentativa principal: localizar o seletor 20 (legado)
                mat_select = None
                try:
                    span_20 = driver.find_element(
                        By.XPATH,
                        "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='20']"
                    )
                    mat_select = span_20.find_element(By.XPATH, "ancestor::mat-select[@role='combobox']")
                except Exception:
                    pass

                # fallback: localizar mat-select genérico ou paginador
                if not mat_select:
                    for css in [
                        "mat-select[aria-labelledby*='mat-paginator-page']",
                        "mat-paginator mat-select[id*='mat-select-']",
                        "mat-select[role='combobox']",
                        "mat-select[formcontrolname]",
                        "mat-select",
                    ]:
                        try:
                            mat_select = driver.find_element(By.CSS_SELECTOR, css)
                            break
                        except Exception:
                            mat_select = None

                if not mat_select:
                    logger.error('[FILTRO_LISTA_100] Não encontrou mat-select para aplicar filtro.')
                    _dump_debug_snapshot(driver.page_source, 'mat_select_not_found')
                    return False

                try:
                    driver.execute_script('arguments[0].scrollIntoView({block:"center",behavior:"instant"})', mat_select)
                except Exception:
                    pass

                # abrir dropdown com múltiplas estratégias
                opened = False
                try:
                    mat_select.click()
                    opened = True
                except Exception:
                    pass

                if not opened:
                    try:
                        driver.execute_script('arguments[0].click();', mat_select)
                        opened = True
                    except Exception:
                        pass

                if not opened:
                    try:
                        clicked = safe_click(driver, mat_select, log=True)
                        opened = bool(clicked)
                    except Exception:
                        opened = False

                if not opened:
                    logger.error('[FILTRO_LISTA_100] Não conseguiu abrir o mat-select.')
                    return False

                # Aguardar mat-options renderizarem no overlay (Angular precisa de tempo)
                # .cdk-overlay-pane existe sempre no DOM; aguardar a presença de mat-option
                try:
                    aguardar_renderizacao_nativa(driver, '.cdk-overlay-pane mat-option', timeout=4)
                except Exception:
                    pass

                # Aguardar overlay de opções
                try:
                    overlay = WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".mat-select-panel, .cdk-overlay-pane")
                        )
                    )
                except Exception:
                    try:
                        overlay = driver.find_element(By.CSS_SELECTOR, '.cdk-overlay-pane')
                    except Exception:
                        overlay = None

                if not overlay:
                    logger.error('[FILTRO_LISTA_100] Overlay do mat-select não apareceu')
                    return False

                # localizar opção 100
                opcao_100 = None
                try:
                    opcao_100 = overlay.find_element(By.XPATH, ".//mat-option[.//span[normalize-space(text())='100']]")
                except Exception:
                    try:
                        opcao_100 = overlay.find_element(By.XPATH, ".//span[normalize-space(text())='100']/ancestor::mat-option")
                    except Exception:
                        opcao_100 = None

                if not opcao_100:
                    # Fallback: busca por qualquer mat-option contendo 100 no texto
                    for item in overlay.find_elements(By.XPATH, ".//mat-option"):
                        try:
                            if '100' in item.text.strip().split('\n')[0].strip():
                                opcao_100 = item
                                break
                        except Exception:
                            continue

                if not opcao_100:
                    logger.error('[FILTRO_LISTA_100] Não encontrou opção 100 no overlay')
                    logger.debug(f'[FILTRO_LISTA_100] Overlay HTML: {overlay.get_attribute("outerHTML")[:2000]}')
                    return False

                # clicar na opção 100
                try:
                    driver.execute_script('arguments[0].click();', opcao_100)
                except Exception:
                    try:
                        opcao_100.click()
                    except Exception as e:
                        logger.error(f'[FILTRO_LISTA_100] Falha ao clicar em opção 100: {e}')
                        return False

                time.sleep(0.8)
                return True

            except Exception as e:
                logger.exception(f'[FILTRO_LISTA_100][_selecionar] Erro inesperado: {e}')
                return False

        resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log_enabled=True)

        if resultado:
            logger.info('Filtro lista 100 aplicado')
            try:
                _dump_debug_snapshot('RESULTADO: OK', 'result_ok')
            except Exception:
                pass
        else:
            logger.error('Filtro lista 100 falhou após todas tentativas')
            try:
                _dump_debug_snapshot('RESULTADO: FALHA', 'result_fail')
            except Exception:
                pass

        return resultado

    except Exception as e:
        logger.exception(f'[FILTRO_LISTA_100][ERRO] Falha geral: {e}')
        return False


def filtro_fase(driver: WebDriver, fases_alvo: List[str] = ['liquidação', 'execução'], tarefas_alvo: Optional[List[str]] = None, seletor_tarefa: str = 'Tarefa do processo') -> bool:
    """Backward-compatible alias para filtrofases."""
    return filtrofases(driver, fases_alvo=fases_alvo, tarefas_alvo=tarefas_alvo, seletor_tarefa=seletor_tarefa)


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
