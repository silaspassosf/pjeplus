from typing import Optional, Tuple, Dict, List, Union, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from Fix import (
    login_pc,
    safe_click,
    esperar_elemento,
    criar_gigs,
    aplicar_filtro_100,
    limpar_temp_selenium,
    buscar_seletor_robusto,
    preencher_campos_prazo,
    esperar_url_conter,
    buscar_documentos_sequenciais,
    indexar_e_processar_lista,
    extrair_dados_processo,
    carregar_destinatarios_cache,
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    com_retry
)
import os
import logging
import time
from Fix.selectors_pje import BTN_TAREFA_PROCESSO

logger = logging.getLogger(__name__)


def selecionar_opcao_select(
    driver: WebDriver,
    seletor: str,
    texto_opcao: str,
    timeout: int = 10
) -> bool:
    """
    Seleciona uma opção em um mat-select de forma robusta.
    
    Args:
        driver: WebDriver do Selenium
        seletor: Seletor CSS do elemento mat-select
        texto_opcao: Texto da opção a selecionar
        timeout: Timeout em segundos (padrão: 10)
    
    Returns:
        bool: True se selecionado com sucesso, False caso contrário
    """
    try:
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
    except Exception as e:
        logger.error(f'Erro em selecionar_opcao_select: {e}')
        return False


def verificar_carregamento_pagina(
    driver: WebDriver,
    timeout_spinner: float = 1.0,
    max_tentativas: int = 5,
    log: bool = False
) -> bool:
    """
    Verifica se a página está em estado de carregamento (spinner visível).
    Continua tentando até o spinner desaparecer - NÃO desiste facilmente.
    
    Args:
        driver: WebDriver do Selenium
        timeout_spinner: Tempo em segundos para aguardar entre tentativas (padrão: 1.0)
        max_tentativas: Número máximo de tentativas de reload (padrão: 5)
        log: Ativa logs detalhados
    
    Returns:
        bool: True se a página carregou corretamente, False se falhou após todas tentativas
    """
    # Script JavaScript otimizado e rápido
    JS_CHECK_LOADING = """
    if (document.readyState !== 'complete') return 'loading';
    const spinner = document.querySelector('mat-progress-spinner, mat-spinner, .mat-progress-spinner');
    if (spinner && window.getComputedStyle(spinner).display !== 'none') return 'spinner';
    return 'complete';
    """
    
    for tentativa in range(1, max_tentativas + 1):
        time.sleep(timeout_spinner)
        
        try:
            # Verificação rápida via JavaScript com timeout implícito do driver
            status = driver.execute_script(JS_CHECK_LOADING)
            
            if status == 'complete':
                return True
            
            if status == 'loading':
                # Aguarda mais um pouco e verifica de novo
                time.sleep(0.3)
                if driver.execute_script("return document.readyState") == "complete":
                    return True
            
            # Spinner ou loading persistente - refresh
            if log:
                logger.warning(f"[CARREGAMENTO] Status={status}, F5...")
            
            driver.refresh()
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass
            
            # Aguardar mais após refresh para dar tempo do spinner sumir
            time.sleep(1.5)
            
        except Exception as e:
            if log:
                logger.warning(f"[CARREGAMENTO] Erro: {e}")
            return True  # Em caso de erro, prossegue
    
    if log:
        logger.error(f"[CARREGAMENTO]  Falha após {max_tentativas} tentativas")
    return False


def aguardar_e_verificar_aba(
    driver: WebDriver,
    url_esperada: str = None,
    timeout_aba: int = 10,
    timeout_spinner: float = 2.0,
    max_tentativas_reload: int = 3,
    log: bool = False
) -> bool:
    """
    Aguarda uma nova aba carregar e verifica se não está travada no spinner.
    Útil para quando se abre uma nova aba (tarefa ou minuta) e precisa garantir que carregou.
    
    Args:
        driver: WebDriver do Selenium
        url_esperada: Parte da URL esperada na nova aba (ex: '/tarefa', '/minutar'). None para não verificar.
        timeout_aba: Timeout em segundos para aguardar a URL esperada
        timeout_spinner: Tempo em segundos para aguardar antes de verificar o spinner
        max_tentativas_reload: Número máximo de tentativas de reload se detectar spinner
        log: Ativa logs detalhados
    
    Returns:
        bool: True se a aba carregou corretamente, False caso contrário
    """
    try:
        # Se URL esperada foi especificada, aguarda ela aparecer
        if url_esperada:
            try:
                WebDriverWait(driver, timeout_aba).until(
                    lambda d: url_esperada in d.current_url
                )
            except TimeoutException:
                if log:
                    logger.warning(f"[ABA]  Timeout aguardando URL com '{url_esperada}'. URL atual: {driver.current_url}")
                # Continua mesmo assim para verificar o carregamento
        
        # Verifica se a página carregou (não está travada no spinner)
        return verificar_carregamento_pagina(
            driver,
            timeout_spinner=timeout_spinner,
            max_tentativas=max_tentativas_reload,
            log=log
        )
        
    except Exception as e:
        logger.error(f"[ABA] Erro ao verificar aba: {e}")
        return False


def verificar_carregamento_detalhe(
    driver: WebDriver,
    timeout_inicial: float = 2.0,
    max_tentativas: int = 3,
    log: bool = False
) -> bool:
    """
    Verifica se a página /detalhe carregou corretamente.
    A página /detalhe não tem spinner, então verificamos a presença do botão de filtro.
    
    Indicador de página carregada:
    <button mat-mini-fab color="branco" aria-label="Filtrar" class="mat-mini-fab... botao-menu">
        <i class="fa fa-filter botao-menu-texto"></i>
    </button>
    
    Args:
        driver: WebDriver do Selenium
        timeout_inicial: Tempo em segundos para aguardar antes de verificar (padrão: 2.0)
        max_tentativas: Número máximo de tentativas de reload (padrão: 3)
        log: Ativa logs detalhados
    
    Returns:
        bool: True se a página carregou corretamente, False se falhou após todas tentativas
    """
    # Seletores para o botão de filtro que indica página carregada
    FILTRO_SELECTORS = [
        'button[aria-label="Filtrar"] i.fa-filter',
        'button.botao-menu i.fa-filter',
        'button[name="Mostrar ou Esconder Filtros"]',
        'button[accesskey="o"] i.fa-filter',
        '.botao-menu i.fa-filter.botao-menu-texto',
        'button.mat-mini-fab[aria-label="Filtrar"]'
    ]
    
    for tentativa in range(1, max_tentativas + 1):
        time.sleep(timeout_inicial)
        
        # Verifica se a URL contém /detalhe
        try:
            current_url = driver.current_url or ''
            if '/detalhe' not in current_url.lower():
                if log:
                    logger.warning(f"[DETALHE] URL não contém /detalhe: {current_url}")
                # Não é página de detalhe, retorna True para não bloquear
                return True
        except Exception:
            pass
        
        # Verifica presença do botão de filtro
        filtro_encontrado = False
        for selector in FILTRO_SELECTORS:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                for elemento in elementos:
                    if elemento.is_displayed():
                        filtro_encontrado = True
                        break
                if filtro_encontrado:
                    break
            except Exception:
                continue
        
        if filtro_encontrado:
            # Verifica também se o readyState está completo
            try:
                ready_state = driver.execute_script("return document.readyState")
                if ready_state == "complete":
                    return True
                else:
                    time.sleep(1)
                    ready_state = driver.execute_script("return document.readyState")
                    if ready_state == "complete":
                        return True
            except Exception:
                pass
            
            # Botão encontrado, considera carregado
            return True
        
        # Botão não encontrado - página não carregou
        if log:
            logger.warning(f"[DETALHE]  Botão de filtro não encontrado na tentativa {tentativa}. Recarregando página (F5)...")
        
        try:
            driver.refresh()
            time.sleep(1)
            # Aguarda readyState ficar completo
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception as e:
            if log:
                logger.error(f"[DETALHE] Erro ao recarregar página: {e}")
    
    # Esgotou tentativas
    logger.error(f"[DETALHE]  Falha após {max_tentativas} tentativas. Página /detalhe não carregou.")
    return False


def aguardar_e_verificar_detalhe(
    driver: WebDriver,
    timeout_aba: int = 10,
    timeout_carregamento: float = 2.0,
    max_tentativas_reload: int = 3,
    log: bool = False
) -> bool:
    """
    Aguarda uma nova aba /detalhe carregar e verifica se não está travada.
    Útil para quando se abre um processo da lista e precisa garantir que a aba /detalhe carregou.
    
    Args:
        driver: WebDriver do Selenium
        timeout_aba: Timeout em segundos para aguardar a URL /detalhe aparecer
        timeout_carregamento: Tempo em segundos para aguardar antes de verificar o botão de filtro
        max_tentativas_reload: Número máximo de tentativas de reload se não encontrar o botão
        log: Ativa logs detalhados
    
    Returns:
        bool: True se a aba carregou corretamente, False caso contrário
    """
    try:
        # Aguarda URL conter /detalhe
        try:
            WebDriverWait(driver, timeout_aba).until(
                lambda d: '/detalhe' in (d.current_url or '').lower()
            )
        except TimeoutException:
            current_url = driver.current_url or ''
            if log:
                logger.warning(f"[DETALHE_ABA]  Timeout aguardando /detalhe. URL atual: {current_url}")
            # Se não for página de detalhe, não bloqueia
            if '/detalhe' not in current_url.lower():
                return True
        
        # Verifica se a página carregou (botão de filtro presente)
        return verificar_carregamento_detalhe(
            driver,
            timeout_inicial=timeout_carregamento,
            max_tentativas=max_tentativas_reload,
            log=log
        )
        
    except Exception as e:
        logger.error(f"[DETALHE_ABA] Erro ao verificar aba: {e}")
        return False
