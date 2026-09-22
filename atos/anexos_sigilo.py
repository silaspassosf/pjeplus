"""
Utilitários para inserção de sigilo individual e visibilidade em lote em anexos.
Especializado em separar sigilo (individual) de visibilidade (lote).
"""

import logging
from Fix.core import safe_click_no_scroll
import time
from typing import Optional

from selenium.webdriver.common.by import By
from Fix import espera

logger = logging.getLogger(__name__)


def inserir_sigilo_individual(elemento, driver=None, debug=False):
    """
    Insere sigilo INDIVIDUALMENTE em um anexo/documento.
    Padrão INVERSO de retirar_sigilo:
    - retirar_sigilo: sem sigilo → retorna; com sigilo → clica e aguarda DESAPARECER
    - inserir_sigilo: com sigilo → retorna; sem sigilo → clica e aguarda APARECER

    Lógica:
    1. Se JÁ TEM SIGILO (is-sigiloso) → retorna True (não precisa fazer nada)
    2. Se NÃO TEM SIGILO → clica botão para ADICIONAR sigilo
    3. Aguarda aplicação da classe 'is-sigiloso' (confirmação)

    Args:
        elemento: WebElement do documento/anexo na timeline
        driver: WebDriver Selenium
        debug: Exibir logs detalhados

    Returns:
        True se sigilo foi adicionado ou já existia, False em erro
    """
    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent') and hasattr(elemento._parent, 'execute_script'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    def _link_documento():
        links = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        if not links:
            return None
        for link in links:
            role = (link.get_attribute('role') or '').lower()
            target = (link.get_attribute('target') or '').lower()
            if role == 'button' or target != '_blank':
                return link
        return links[-1]

    def _tem_sigilo():
        # Utiliza JavaScript para uma verificação instantânea, ignorando qualquer implicit_wait global do driver
        script = "return arguments[0].querySelector('i.tl-sigiloso, a.is-sigiloso') !== null;"
        try:
            return driver.execute_script(script, elemento)
        except Exception:
            return False

    try:
        # Se JÁ TEM SIGILO, retorna sucesso imediatamente (padrão inverso)
        if _tem_sigilo():
            if debug:
                logger.info('[SIGILO_INSERIR] Já com sigilo (tl-sigiloso/is-sigiloso detectado)')
            return True

        # NÃO TEM SIGILO, precisa buscar botão e clicar
        btn_sigilo = None
        seletores = [
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer',
        ]

        for seletor in seletores:
            try:
                candidato = elemento.find_element(By.CSS_SELECTOR, seletor)
                if candidato.is_displayed():
                    btn_sigilo = candidato
                    break
            except Exception:
                continue

        if not btn_sigilo:
            if debug:
                logger.error('[SIGILO_INSERIR] Botão de sigilo não encontrado')
            return False

        # Clica para ADICIONAR sigilo
        try:
            safe_click_no_scroll(driver, btn_sigilo)
        except Exception:
            btn_sigilo.click()

        # Aguarda sigilo APARECER (via tl-sigiloso ou is-sigiloso)
        for tentativa in range(8):
            time.sleep(0.25)
            try:
                if _tem_sigilo():
                    if debug:
                        logger.info(f'[SIGILO_INSERIR] ✅ Sigilo adicionado após tentativa {tentativa+1}')
                    return True
            except Exception:
                pass

        if debug:
            logger.error('[SIGILO_INSERIR] ❌ Clique executado, mas sigilo não foi detectado')
        return False

    except Exception as e:
        if debug:
            logger.error(f"[SIGILO_INSERIR] ❌ Erro geral: {e}")
        return False


def visibilidade_sigilosos_lote_apenas(driver, polo='ativo', log=False):
    """
    Aplica visibilidade em lote nos anexos que já receberam sigilo.
    Checkboxes já selecionados individualmente na FASE 1 (após cada inserir_sigilo).

    Sequência (múltipla seleção já ativada antes da FASE 1):
    1. Clicar botão "+" de visibilidade (i.fas.fa-plus.fa-lg)
    2. No modal: clicar "Marcar todas" (button.botao-icone-titulo-coluna)
    3. Salvar

    :param driver: A instância do WebDriver.
    :param polo: mantido por compatibilidade, não utilizado (modal usa toggle geral).
    :param log: Ativa logs detalhados.
    :return: True se executou com sucesso, False caso contrário.
    """
    try:
        # 1. Clicar botão "+" de visibilidade (anexos já selecionados via checkboxes na FASE 1)
        if log:
            logger.info('[VISIBILIDADE_LOTE] Abrindo modal de visibilidade...')
        try:
            if not espera.ate_habilitar(driver, 'button[aria-label="Incluir visibilidade para Sigilo"]', teto=5):
                raise Exception('botão de visibilidade não habilitou')
            btn_vis = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Incluir visibilidade para Sigilo"]')
            safe_click_no_scroll(driver, btn_vis)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Falha ao clicar botão de visibilidade: {e}')
            return False

        # 2. Aguardar modal carregar completamente (dump: ~1.8s entre "+" e "Marcar todas")
        #    Espera as linhas da tabela (tr.cdk-drag) aparecerem dentro do modal
        modal_container = '.cdk-overlay-container .mat-dialog-container'
        modal = espera.elemento(driver, modal_container, teto=4, visivel=False)
        linhas_modal = None
        if modal:
            if log:
                logger.info('[VISIBILIDADE_LOTE] Modal detectado, aguardando conteúdo carregar...')
            # Aguarda conteúdo do modal — linhas da tabela de partes (tr.cdk-drag)
            linhas_modal = espera.elemento(driver, f'{modal_container} tr.cdk-drag', teto=5, visivel=False)
        if not linhas_modal and log:
            logger.warning('[VISIBILIDADE_LOTE] Linhas do modal não detectadas, tentando prosseguir...')

        # 3. Marcar todas as partes — aguarda botão ficar clicável
        if log:
            logger.info('[VISIBILIDADE_LOTE] Marcando todas as partes no modal...')
        try:
            seletor_marcar = 'button[aria-label="Marcar todas"], i.fa.fa-check.botao-icone-titulo-coluna'
            if not espera.ate_habilitar(driver, seletor_marcar, teto=5):
                raise Exception('botão Marcar todas não habilitou')
            icone_header = driver.find_element(By.CSS_SELECTOR, seletor_marcar)
            safe_click_no_scroll(driver, icone_header)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Falha ao marcar partes no modal: {e}')
            return False

        # 4. Salvar — aguarda botão ficar clicável
        if log:
            logger.info('[VISIBILIDADE_LOTE] Salvando configuração...')
        try:
            xpath_salvar = '//button[.//span[contains(text(),"Salvar")]]'
            if not espera.ate_habilitar(driver, xpath_salvar, teto=10):
                raise Exception('botão Salvar não habilitou')
            btn_salvar = driver.find_element(By.XPATH, xpath_salvar)
            safe_click_no_scroll(driver, btn_salvar)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Falha ao salvar: {e}')
            return False

        if log:
            logger.info('[VISIBILIDADE_LOTE] ✅ Visibilidade em lote aplicada com sucesso')
        return True

    except Exception as e:
        logger.error(f'[VISIBILIDADE_LOTE][ERRO] Falha ao aplicar visibilidade em lote: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False
