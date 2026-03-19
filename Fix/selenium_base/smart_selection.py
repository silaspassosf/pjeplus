import logging
logger = logging.getLogger(__name__)

"""
Smart Selection - Seleção inteligente de elementos e opções
============================================================

Extração do Fix/core.py (2915 linhas) → selenium_base/smart_selection.py (~400 linhas)

FUNÇÕES EXTRAÍDAS (lines 609-971, 1220-1391 do core.py):
- selecionar_opcao: Abre dropdown e seleciona opção (múltiplas estratégias)
- escolher_opcao_inteligente: (DEPRECATED) Tenta múltiplos seletores
- encontrar_elemento_inteligente: Busca elemento com múltiplos seletores

RESPONSABILIDADE:
- Seleção inteligente de dropdowns (mat-select, select, etc.)
- Auto-detecção de dropdowns por nome conhecido
- Múltiplas estratégias de abertura (click, focus+enter, keyboard)
- Busca de elementos com fallback automático

DEPENDÊNCIAS:
- selenium.webdriver: WebDriver, By, Keys
- selenium.webdriver.support: WebDriverWait, expected_conditions
- selenium.common.exceptions: NoSuchElementException, TimeoutException, StaleElementReferenceException

USO TÍPICO:
    from Fix.selenium_base.smart_selection import selecionar_opcao
    
    # Auto-detecção
    selecionar_opcao(driver, None, 'Análise')
    
    # Seletor CSS direto
    selecionar_opcao(driver, 'mat-select[formcontrolname="destinos"]', 'Transferir valor')
    
    # Nome conhecido
    selecionar_opcao(driver, 'destino', 'Análise')
    selecionar_opcao(driver, 'fase', 'Execução')

AUTOR: Extração PJePlus Refactoring Phase 2
DATA: 2025-01-XX
"""

import time
from typing import Optional, List, Tuple, Union, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)

def selecionar_opcao(
    driver: WebDriver,
    seletor_dropdown: Optional[str],
    texto_opcao: str,
    timeout: int = 10,
    exato: bool = False,
    log: bool = False
) -> bool:
    """
    Abre dropdown e seleciona opção por texto (1 script vs 5+ requisições).
    
    Padrão repetitivo consolidado: click dropdown + wait options + click option
    
    MELHORADO: Baseado no código original ORIGINAIS/loop.py + inspiração do a.py validado
    Usa múltiplas estratégias para localizar dropdown e opções, mantendo mínimo de requisições.
    
    Args:
        driver: WebDriver Selenium
        seletor_dropdown: Seletor CSS do dropdown OU nome conhecido do dropdown:
            - None: auto-detecção automática
            - CSS selector: seletor direto (ex: 'mat-select[formcontrolname="destinos"]')
            - Nome conhecido: 'destino', 'fase', 'tipo', 'tarefa', 'situacao', etc.
        texto_opcao: Texto da opção a selecionar
        timeout: Timeout em segundos (default: 10)
        exato: Se True, texto deve ser exato; se False, usa contains (default: False)
        log: Ativa logging (default: False)
    
    Returns:
        True se selecionou, False caso contrário
    
    Exemplos de Uso:
        # Auto-detecção (dropdown único na página)
        selecionar_opcao(driver, None, 'Análise')
        
        # Seletor CSS direto (mais específico)
        selecionar_opcao(driver, 'mat-select[formcontrolname="destinos"]', 'Transferir valor')
        
        # Nome conhecido (mais genérico, tenta múltiplos seletores)
        selecionar_opcao(driver, 'destino', 'Análise')
        selecionar_opcao(driver, 'fase', 'Execução')
        selecionar_opcao(driver, 'tipo', 'Geral')
        selecionar_opcao(driver, 'tarefa', 'Análise de processo')
    
    Nomes Conhecidos Suportados:
        - 'destino': Dropdowns de destino/transferência
        - 'fase': Fase processual
        - 'tipo': Tipo de crédito/documento
        - 'tarefa': Tarefa do processo
        - 'situacao': Situação do processo
        - 'prioridade': Prioridade
        - 'status': Status
    
    Estratégias de Abertura (em ordem):
        1. Click direto no dropdown
        2. Focus + Enter
        3. Focus + Arrow Down
    
    Estratégias de Seleção:
        1. Seletores CSS conhecidos
        2. Auto-detecção por aria-label/placeholder
        3. Painel mat-select (Material Design)
        4. JavaScript direto (fallback)
    """
    # MAPEAMENTO DE NOMES CONHECIDOS PARA SELETORES CSS
    # Permite usar nomes genéricos em vez de seletores específicos
    mapeamento_dropdowns = {
        'destino': [
            'mat-select[aria-placeholder*="destino"]',
            'mat-select[formcontrolname="destinos"]',
            'mat-select[aria-label*="destino"]'
        ],
        'fase': [
            'mat-select[formcontrolname="fpglobal_faseProcessual"]',
            'mat-select[placeholder*="Fase processual"]',
            'mat-select[aria-label*="Fase"]'
        ],
        'tipo': [
            'mat-select[formcontrolname="tipoCredito"]',
            'mat-select[formcontrolname="tipo"]',
            'mat-select[aria-label*="Tipo"]'
        ],
        'tarefa': [
            'mat-select[formcontrolname="tarefa"]',
            'mat-select[aria-label*="Tarefa"]',
            'mat-select[placeholder*="Tarefa"]'
        ],
        'situacao': [
            'mat-select[formcontrolname="situacao"]',
            'mat-select[aria-label*="Situação"]',
            'mat-select[placeholder*="Situação"]'
        ],
        'prioridade': [
            'mat-select[formcontrolname="prioridade"]',
            'mat-select[aria-label*="Prioridade"]'
        ],
        'status': [
            'mat-select[formcontrolname="status"]',
            'mat-select[aria-label*="Status"]'
        ]
    }

    # RESOLVE SELETOR: Converte nome conhecido em lista de seletores CSS
    seletores_possiveis: Optional[List[str]] = None
    if isinstance(seletor_dropdown, str) and seletor_dropdown in mapeamento_dropdowns:
        # Nome conhecido -> lista de seletores possíveis
        seletores_possiveis = mapeamento_dropdowns[seletor_dropdown]
    elif isinstance(seletor_dropdown, str):
        # Seletor CSS direto -> lista com um item
        seletores_possiveis = [seletor_dropdown]
    else:
        # None ou inválido -> manter como None para auto-detecção
        seletores_possiveis = None

    try:
        # ===================================================================
        # ESTRATÉGIA 1: AUTO-DETECÇÃO
        # ===================================================================
        if seletores_possiveis is None:
            estrategias_auto = [
                'mat-select[formcontrolname="destinos"]',  # Padrão do código original
                'mat-select[aria-label*="Tarefa destino"]',  # Aria-label comum
                'mat-select[aria-label*="destino"]',  # Aria-label genérico
                'mat-select[placeholder*="destino"]',  # Placeholder
                'mat-select[formcontrolname*="destino"]',  # Formcontrolname parcial
                'mat-select'  # Último recurso: qualquer mat-select
            ]

            for seletor_auto in estrategias_auto:
                if _tentar_selecionar_com_seletor(
                    driver, seletor_auto, texto_opcao, exato, log, timeout=5
                ):
                    if log:
                                            return True

            if log:
                            return False

        # ===================================================================
        # ESTRATÉGIA 2: SELETORES RESOLVIDOS (nome conhecido ou CSS direto)
        # ===================================================================
        for seletor_atual in seletores_possiveis:
            if _tentar_selecionar_com_seletor(
                driver, seletor_atual, texto_opcao, exato, log, timeout
            ):
                if log:
                                    return True

        # ===================================================================
        # FALLBACK: ESTRATÉGIA 3 (painel Material Design)
        # ===================================================================
        if _tentar_selecionar_via_painel(driver, texto_opcao, log):
            if log:
                            return True

        # ===================================================================
        # FALLBACK: ESTRATÉGIA 4 (JavaScript direto)
        # ===================================================================
        if _tentar_selecionar_via_javascript(
            driver, seletores_possiveis, texto_opcao, log
        ):
            if log:
                            return True

        if log:
                    return False

    except Exception as e:
        if log:
                    return False

def _tentar_selecionar_com_seletor(
    driver: WebDriver,
    seletor: str,
    texto_opcao: str,
    exato: bool,
    log: bool,
    timeout: int = 10
) -> bool:
    """
    Tenta selecionar opção usando um seletor específico.
    
    Helper interno para reduzir duplicação de código.
    """
    try:
        dropdown = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
        )

        # MELHORIA: Múltiplas tentativas de abrir dropdown
        dropdown_aberto = False

        # Tentativa 1: Click direto
        try:
            dropdown.click()
            time.sleep(0.5)
            dropdown_aberto = True
        except:
            pass

        # Tentativa 2: Focus + Enter
        if not dropdown_aberto:
            try:
                driver.execute_script("arguments[0].focus();", dropdown)
                dropdown.send_keys(Keys.ENTER)
                time.sleep(0.5)
                dropdown_aberto = True
            except:
                pass

        # Tentativa 3: Focus + Arrow Down
        if not dropdown_aberto:
            try:
                driver.execute_script("arguments[0].focus();", dropdown)
                dropdown.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.5)
                dropdown_aberto = True
            except:
                pass

        if not dropdown_aberto:
            return False

        # MELHORIA: Aguardar opções aparecerem
        try:
            WebDriverWait(driver, 3).until(
                lambda d: len(d.find_elements(
                    By.CSS_SELECTOR, 
                    'mat-option[role="option"], option'
                )) >= 1
            )
        except:
            return False

        # Procurar opção dentro do overlay ou painel
        opcao_seletor = 'mat-option[role="option"] span.mat-option-text, option'
        opcoes = driver.find_elements(By.CSS_SELECTOR, opcao_seletor)

        for opcao in opcoes:
            try:
                texto = opcao.text.strip().lower()
                if exato:
                    encontrado = texto == texto_opcao.lower()
                else:
                    encontrado = texto_opcao.lower() in texto

                if encontrado:
                    opcao.click()
                    time.sleep(0.3)
                    return True
            except StaleElementReferenceException:
                continue

        return False

    except Exception as e:
        return False

def _tentar_selecionar_via_painel(
    driver: WebDriver,
    texto_opcao: str,
    log: bool
) -> bool:
    """
    Tenta selecionar opção via painel Material Design.
    
    Fallback para quando seletores diretos falham.
    """
    try:
        select = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                'mat-select[formcontrolname="destinos"]'
            ))
        )
        select.click()
        time.sleep(1)

        # Aguardar painel aparecer
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, painel_selector))
        )

        # Procurar opção no painel
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for opcao in opcoes:
            try:
                texto = opcao.text.strip().lower()
                if texto_opcao.lower() in texto:
                    driver.execute_script("arguments[0].click();", opcao)
                    return True
            except Exception:
                continue

        return False

    except Exception as e:
        return False

def _tentar_selecionar_via_javascript(
    driver: WebDriver,
    seletores_possiveis: Optional[List[str]],
    texto_opcao: str,
    log: bool
) -> bool:
    """
    Tenta selecionar opção via JavaScript direto.
    
    Último recurso quando todas outras estratégias falharam.
    """
    try:
        seletor_primario = (
            seletores_possiveis[0] if seletores_possiveis else "mat-select"
        )

        script = f"""
        try {{
            // Procurar dropdown por múltiplos seletores
            let dropdown = document.querySelector('{seletor_primario}') ||
                          document.querySelector('mat-select[formcontrolname="destinos"]') ||
                          document.querySelector('mat-select[aria-label*="Tarefa destino"]') ||
                          document.querySelector('mat-select');

            if (dropdown) {{
                dropdown.click();

                // Aguardar opções aparecerem
                setTimeout(() => {{
                    let opcoes = document.querySelectorAll('mat-option span.mat-option-text, .mat-option-text');
                    for (let opcao of opcoes) {{
                        let texto = opcao.textContent.trim().toLowerCase();
                        if (texto.includes('{texto_opcao.lower()}')) {{
                            opcao.click();
                            return true;
                        }}
                    }}

                    // Fallback: primeira opção
                    if (opcoes.length > 0) {{
                        opcoes[0].click();
                        return true;
                    }}
                }}, 500);

                return true;
            }}
            return false;
        }} catch(e) {{
            return false;
        }}
        """

        resultado = driver.execute_script(script)
        return resultado if resultado else False

    except Exception as e:
        return False

def escolher_opcao_inteligente(
    driver: WebDriver,
    valor: str,
    estrategias_custom: Optional[List[Tuple[By, str]]] = None,
    debug: bool = False
) -> bool:
    """
    DEPRECATED: Use selecionar_opcao() ou aguardar_e_clicar() para melhor performance.
    
    Mantido apenas para compatibilidade com código legado.
    
    Tenta múltiplos seletores com early return na primeira que funcionar.
    Reduz código repetitivo de tentativas múltiplas.
    
    Args:
        driver: WebDriver Selenium
        valor: Valor a procurar (texto, id, etc)
        estrategias_custom: Lista de tuplas (By, seletor) customizadas
        debug: Ativa logging detalhado
    
    Returns:
        True se encontrou e clicou, False caso contrário
    
    Exemplo:
        # Procurar e clicar em elemento por múltiplos seletores
        escolher_opcao_inteligente(driver, 'botao_enviar', debug=True)
        
        # Com estratégias customizadas
        estrategias = [
            (By.ID, 'submit'),
            (By.NAME, 'enviar'),
            (By.XPATH, "//button[text()='Enviar']")
        ]
        escolher_opcao_inteligente(driver, 'enviar', estrategias_custom=estrategias)
    """
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
        (By.XPATH, f"//*[contains(text(), '{valor}')]"),
    ]
    
    for by, seletor in estrategias:
        try:
            elem = driver.find_element(by, seletor)
            elem.click()
            if debug:
                            return True
        except (NoSuchElementException, TimeoutException):
            if debug:
                            continue
        except Exception as e:
            if debug:
                            continue
    
    if debug:
            return False

def encontrar_elemento_inteligente(
    driver: WebDriver,
    valor: str,
    estrategias_custom: Optional[List[Tuple[By, str]]] = None,
    debug: bool = False
) -> Optional[WebElement]:
    """
    Similar a escolher_opcao_inteligente mas retorna o elemento ao invés de clicar.
    
    Args:
        driver: WebDriver Selenium
        valor: Valor a procurar (texto, id, etc)
        estrategias_custom: Lista de tuplas (By, seletor) customizadas
        debug: Ativa logging detalhado
    
    Returns:
        WebElement se encontrou, None caso contrário
    
    Exemplo:
        # Buscar elemento sem clicar
        elemento = encontrar_elemento_inteligente(driver, 'campo_nome', debug=True)
        if elemento:
            elemento.send_keys('João Silva')
    """
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
    ]
    
    for by, seletor in estrategias:
        try:
            elem = driver.find_element(by, seletor)
            if debug:
                            return elem
        except (NoSuchElementException, TimeoutException):
            continue
    
    if debug:
            return None

def buscar_seletor_robusto(driver: WebDriver, textos: List[str], contexto=None, timeout: int = 5, log: bool = False) -> Optional[WebElement]:
    """
    Busca robusta de elementos por texto/contexto
    Versão 3.1 - Busca robusta com logs detalhados e timeout reduzido
    
    Args:
        driver: WebDriver Selenium
        textos: Lista de textos para buscar
        contexto: Contexto adicional (opcional)
        timeout: Timeout em segundos
        log: Ativar logging detalhado
        
    Returns:
        WebElement encontrado ou None
    """
    def buscar_input_associado(elemento: WebElement) -> Optional[WebElement]:
        try:
            input_associado = elemento.find_element(By.XPATH, 
                './following-sibling::input|./preceding-sibling::input|'
                './ancestor::*[contains(@class,"form-group")]//input|'
                './ancestor::*[contains(@class,"mat-form-field")]//input'
            )
            return input_associado
        except Exception as e:
            if log:
                logger.info(f'[ROBUSTO][DEBUG] Falha ao buscar input associado: {e}')
            return None
    
    try:
        # Fase 1: Busca direta por inputs editáveis
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE1] Buscando input com texto/atributo: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, 
                    f'input[placeholder*="{texto}"], '
                    f'input[aria-label*="{texto}"], '
                    f'input[name*="{texto}"]'
                )
                for el in elementos:
                    if el.is_displayed() and el.is_enabled():
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Input direto: {el}')
                        return el
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase1: {e}')
                continue
        
        # Fase 2: Busca hierárquica se não encontrar diretamente
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE2] Buscando por texto visível: {texto}')
            try:
                elementos = driver.find_elements(By.XPATH, 
                    f'//*[contains(text(), "{texto}")]'
                )
                for el in elementos:
                    if DEBUG:
                        _log_info(f'[ROBUSTO][FASE2] Elemento com texto encontrado: {el}')
                    input_assoc = buscar_input_associado(el)
                    if input_assoc:
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Input associado: {input_assoc}')
                        return input_assoc
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase2: {e}')
                continue
        
        # Fase 3: Busca por ícone/fa
        for texto in textos:
            if DEBUG:
                _log_info(f'[ROBUSTO][FASE3] Buscando ícone/fa: {texto}')
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all')
                for el in elementos:
                    if el.is_displayed():
                        if DEBUG:
                            _log_info(f'[ROBUSTO][ENCONTRADO] Ícone/fa: {el}')
                        return el
            except Exception as e:
                if DEBUG:
                    _log_info(f'[ROBUSTO][ERRO] Fase3: {e}')
                continue
        
        if DEBUG:
            _log_info('[ROBUSTO][FIM] Nenhum elemento encontrado com os critérios fornecidos.')
        return None
    except Exception as e:
        logger.error(f'[ROBUSTO][ERRO GERAL] {e}')
        return None
