"""
judicial_modelos.py - Funções de modelos e conclusões
=====================================================

Funções para inserção e monitoramento de modelos, além de seleção
de tipos de conclusão no editor de atos judiciais.
"""

from Fix.selenium_base.click_operations import aguardar_e_clicar, safe_click_no_scroll
from Fix.selenium_base.element_interaction import safe_click
from Fix.selenium_base.wait_operations import esperar_url_conter
from Fix.log import logger
from Fix.utils import remover_acentos
from Fix import espera
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver


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
        espera.assentar(driver, timeout_segundos, motivo='inserção de modelo')
        logger.info('[MODELO] Timeout de espera concluído')
        return True
    except Exception as e:
        logger.warning(f'[MODELO] Erro na espera: {e}')
        return True  # Retorna True mesmo em caso de erro para não interromper fluxo



def escolher_tipo_conclusao(driver: WebDriver, conclusao_tipo: str) -> bool:
    """
    Escolhe o tipo de conclusão na tela de conclusão do processo.
    
    ESTRATÉGIA (alinhada ao gigs-plugin.js aaDespacho):
    - Estratégia 0: Container pje-concluso-tarefa-botao com remoção de acentos
    - Estratégia 1: Botões internos em pje-concluso-tarefa-botao
    - Estratégia 2: Procurar por texto visível (normalizado)
    - Estratégia 3: Procurar por aria-label
    - Um ÚNICO clique com scrollIntoView + safe_click_no_scroll

    Args:
        driver: WebDriver instance
        conclusao_tipo: Tipo de conclusão desejado (ex: "Despacho", "Decisão", etc.)

    Returns:
        bool: True se conseguiu escolher o tipo
    """
    try:
        conclusao_tipo = (conclusao_tipo or 'Despacho').strip()
        tipo_norm = remover_acentos(conclusao_tipo).lower()
        logger.info(f'[CONCLUSÃO] Escolhendo tipo de conclusão: {conclusao_tipo} (norm: {tipo_norm})')

        # Aguardar presença dos botões de conclusão
        if not espera.ate_aparecer(driver, 'pje-concluso-tarefa-botao', teto=10):
            logger.warning('[CONCLUSÃO] Botões de conclusão não carregaram')

        btn_tipo_conclusao = None

        # Estratégia 0 (Padrão gigs-plugin.js): Container pje-concluso-tarefa-botao comparando texto normalizado
        try:
            ancoras = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao')
            for ancora in ancoras:
                try:
                    txt_ancora = remover_acentos(ancora.text or '').strip().lower()
                    if tipo_norm in txt_ancora:
                        btn_filho = ancora.find_elements(By.CSS_SELECTOR, 'button')
                        if btn_filho and btn_filho[0].is_displayed() and btn_filho[0].is_enabled():
                            btn_tipo_conclusao = btn_filho[0]
                        elif ancora.is_displayed():
                            btn_tipo_conclusao = ancora
                        if btn_tipo_conclusao:
                            logger.info(f'[CONCLUSÃO] Botão encontrado via container pje-concluso-tarefa-botao (Estratégia 0)')
                            break
                except Exception:
                    continue
        except Exception:
            pass

        # Estratégia 1: Procurar em botões estruturados (pje-concluso-tarefa-botao button)
        if not btn_tipo_conclusao:
            try:
                candidatos = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button')
                for btn in candidatos:
                    try:
                        txt = remover_acentos(btn.text or '').strip().lower()
                        if txt and tipo_norm in txt and btn.is_displayed() and btn.is_enabled():
                            btn_tipo_conclusao = btn
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        # Estratégia 2: Procurar por texto visível
        if not btn_tipo_conclusao:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, 'button')
                for btn in btns:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            txt = remover_acentos(btn.text or '').strip().lower()
                            aria = remover_acentos(btn.get_attribute('aria-label') or '').lower()
                            # Evitar botões de remoção/chips
                            if 'remover' in aria or 'fechar' in aria or 'excluir' in aria:
                                continue
                            if tipo_norm in txt or tipo_norm in aria:
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
                        aria = remover_acentos(btn.get_attribute('aria-label') or '').lower()
                        if tipo_norm in aria:
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
        logger.info(f'[CONCLUSÃO] Clicando em tipo de conclusão...')
        try:
            driver.execute_script('arguments[0].scrollIntoView({block: "center", behavior: "instant"});', btn_tipo_conclusao)
            safe_click_no_scroll(driver, btn_tipo_conclusao)
            logger.info(f'[CONCLUSÃO] ✅ Botão de conclusão "{conclusao_tipo}" clicado')
        except Exception as click_err:
            logger.error(f'[CONCLUSÃO] ❌ Erro ao clicar: {click_err}')
            return False

        # Aguardar navegação pós-clique (observer para readyState complete)
        espera.ate_js(driver, "document.readyState === 'complete'", teto=10)
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
    elif '/detalhe' in current_url:
        return 'detalhe'
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
            campo_filtro_modelo = espera.elemento(driver, 'input#inputFiltro', teto=10)
            if not campo_filtro_modelo:
                raise Exception('input#inputFiltro não apareceu')
            driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
            logger.info('[CONCLUSÃO] Foco no campo #inputFiltro realizado')
        return True
    except Exception as e:
        logger.warning(f'[CONCLUSÃO] Erro ao focar campo minutar: {e}')
        return False