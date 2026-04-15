"""
judicial_conclusao.py - Funções de escolha e execução de conclusões
===================================================================

Funções para seleção de tipos de conclusão, escolha de magistrados,
verificação de impedimentos e execução final da conclusão.
"""

from Fix.core import aguardar_e_clicar, safe_click, logger, esperar_url_conter
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


def escolher_tipo_conclusao(driver: WebDriver, conclusao_tipo: str) -> bool:
    """
    Escolhe o tipo de conclusão na tela de conclusão do processo.

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

        # Clicar no botão encontrado (usar aguardar_e_clicar em vez de scrollIntoView + click)
        if not aguardar_e_clicar(driver, selector, log=False, timeout=3):
            logger.error(f'[CONCLUSÃO] Falha ao clicar no botão de conclusão "{conclusao_tipo}"')
            return False
        logger.info(f'[CONCLUSÃO] Botão de conclusão "{conclusao_tipo}" clicado')

        time.sleep(1)
        return True

    except Exception as e:
        logger.error(f'[CONCLUSÃO] Erro ao escolher tipo de conclusão: {e}')
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