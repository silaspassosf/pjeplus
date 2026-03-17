"""
judicial_modelos.py - Funções de modelos e conclusões
=====================================================

Funções para inserção e monitoramento de modelos, além de seleção
de tipos de conclusão no editor de atos judiciais.
"""

import time
from Fix.core import aguardar_e_clicar, safe_click, logger, esperar_url_conter
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException
from Fix.core import safe_click_no_scroll

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


def esperar_insercao_modelo(driver: WebDriver, timeout: int = 8000) -> bool:
    """
    Aguarda a inserção do modelo com timeout simples.
    NOTA: Monitoramento complexo removido - usa apenas sleep.

    Args:
        driver: WebDriver instance
        timeout: Timeout em ms para aguardar inserção (padrão: 8000ms)

    Returns:
        bool: True (sempre retorna True após aguardar)
    """
    try:
        # Converte timeout de ms para segundos
        timeout_segundos = timeout / 1000.0
        logger.info(f'[MODELO] Aguardando {timeout_segundos}s para inserção do modelo...')
        time.sleep(timeout_segundos)
        logger.info('[MODELO] Timeout de espera concluído')
        return True
    except Exception as e:
        logger.warning(f'[MODELO] Erro na espera: {e}')
        return True  # Retorna True mesmo em caso de erro para não interromper fluxo



def escolher_tipo_conclusao(driver: WebDriver, conclusao_tipo: str) -> bool:
    """
    Escolhe o tipo de conclusão na tela de conclusão do processo.
    
    ESTRATÉGIA SIMPLES (legacy approach):
    - Procura botão com 3 estratégias
    - Um ÚNICO clique com scrollIntoView + JS click
    - Deixa que a página navegue naturalmente sem retry

    Args:
        driver: WebDriver instance
        conclusao_tipo: Tipo de conclusão desejado (ex: "Despacho", "Decisão", etc.)

    Returns:
        bool: True se conseguiu escolher o tipo
    """
    try:
        logger.info(f'[CONCLUSÃO] Escolhendo tipo de conclusão: {conclusao_tipo}')

        # Aguardar presença dos botões de conclusão
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-concluso-tarefa-botao'))
            )
        except Exception:
            logger.warning('[CONCLUSÃO] Botões de conclusão não carregaram')

        btn_tipo_conclusao = None

        # Estratégia 1: Procurar em botões estruturados (pje-concluso-tarefa-botao)
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button')
            for btn in candidatos:
                try:
                    txt = (btn.text or '').strip()
                    if txt and conclusao_tipo.lower() in txt.lower() and btn.is_displayed() and btn.is_enabled():
                        btn_tipo_conclusao = btn
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # Estratégia 2: Procurar por texto visível
        if not btn_tipo_conclusao:
            try:
                xpath = f"//button[contains(normalize-space(text()), '{conclusao_tipo}')]"
                btns = driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            aria = (btn.get_attribute('aria-label') or '').lower()
                            # Evitar botões de remoção/chips
                            if 'remover' not in aria and 'fechar' not in aria and 'excluir' not in aria:
                                btn_tipo_conclusao = btn
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        # Estratégia 3: Procurar por aria-label
        if not btn_tipo_conclusao:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, "button[aria-label]")
                for btn in btns:
                    try:
                        aria = (btn.get_attribute('aria-label') or '').lower()
                        if conclusao_tipo.lower() in aria:
                            if 'remover' not in aria and 'fechar' not in aria:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn_tipo_conclusao = btn
                                    break
                    except Exception:
                        continue
            except Exception:
                pass

        if not btn_tipo_conclusao:
            logger.error(f'[CONCLUSÃO] Botão de conclusão "{conclusao_tipo}" não encontrado')
            return False

        # ===== CLIQUE ÚNICO + SIMPLES (legacy approach) =====
        # ScrollIntoView + JavaScript click direto, sem retry logic que interfere com page navigation
        logger.info(f'[CONCLUSÃO] Clicando em tipo de conclusão...')
        try:
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_tipo_conclusao)
            time.sleep(0.3)
            driver.execute_script('arguments[0].click();', btn_tipo_conclusao)
            logger.info(f'[CONCLUSÃO] ✅ Botão de conclusão "{conclusao_tipo}" clicado')
        except Exception as click_err:
            logger.error(f'[CONCLUSÃO] ❌ Erro ao clicar: {click_err}')
            return False

        # Aguardar estabilização
        time.sleep(1)
        return True

    except Exception as e:
        logger.error(f'[CONCLUSÃO] Erro ao escolher tipo de conclusão: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False




def aguardar_transicao_minutar(driver: WebDriver) -> bool:
    """
    Aguarda a transição da tela de conclusão para a tela de minutar.

    Returns:
        bool: True se conseguiu fazer a transição
    """
    try:
        logger.info('[CONCLUSÃO] Aguardando transição para tela de minutar...')

        # Aguardar URL /minutar
        if not esperar_url_conter(driver, '/minutar', timeout=20):
            logger.error(f'[CONCLUSÃO] URL não mudou para /minutar: {driver.current_url}')
            return False

        logger.info('[CONCLUSÃO] Transição para minutar concluída')
        return True

    except Exception as e:
        logger.error(f'[CONCLUSÃO] Erro na transição para minutar: {e}')
        return False


def verificar_estado_atual(driver: WebDriver) -> str:
    """
    Verifica o estado atual do processo baseado na URL.

    Returns:
        str: Estado atual ('assinar', 'minutar', 'conclusao', 'outro')
    """
    current_url = (driver.current_url or '').lower()

    if '/assinar' in current_url:
        return 'assinar'
    elif '/minutar' in current_url:
        return 'minutar'
    elif '/conclusao' in current_url:
        return 'conclusao'
    else:
        return 'outro'


def focar_campo_minutar_se_necessario(driver: WebDriver) -> bool:
    """
    Foca no campo de filtro de modelos se estiver na tela de minutar.

    Returns:
        bool: True se conseguiu focar ou se não era necessário
    """
    try:
        if verificar_estado_atual(driver) == 'minutar':
            logger.info('[CONCLUSÃO] Já em minutar - focando no campo de filtro')
            campo_filtro_modelo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
            )
            driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
            logger.info('[CONCLUSÃO] Foco no campo #inputFiltro realizado')
        return True
    except Exception as e:
        logger.warning(f'[CONCLUSÃO] Erro ao focar campo minutar: {e}')
        return False