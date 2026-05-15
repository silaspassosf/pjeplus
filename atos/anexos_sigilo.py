"""
Utilitários para inserção de sigilo individual e visibilidade em lote em anexos.
Especializado em separar sigilo (individual) de visibilidade (lote).
"""

import logging
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
        # Indicador primário para anexos: ícone wpexplorer com classe tl-sigiloso
        try:
            if elemento.find_elements(By.CSS_SELECTOR, 'i.fa-wpexplorer.tl-sigiloso'):
                return True
        except Exception:
            pass
        # Fallback: link com is-sigiloso
        link = _link_documento()
        if not link:
            return False
        classes = (link.get_attribute('class') or '').lower()
        if debug:
            logger.info(f"[SIGILO_INSERIR] Classes link documento: {classes}")
        return 'is-sigiloso' in classes

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
            driver.execute_script('arguments[0].click();', btn_sigilo)
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
    Aplica visibilidade em lote APENAS nos anexos especiais da certidão de pesquisa
    que já receberam sigilo (classe is-sigiloso no link do documento).

    Sequência correta (dentro do painel de anexos, sem tocar na timeline principal):
    1. Ativar múltipla seleção nos anexos (i.fa-check-square.fa-lg.far.icone-sozinho)
    2. Selecionar APENAS os anexos com a.tl-documento.is-sigiloso
    3. Clicar botão de visibilidade dos anexos (i.fas.fa-plus.fa-lg.tl-nao-sigiloso)
    4. No modal: clicar header toggle (i.fa.fa-check.botao-icone-titulo-coluna) para marcar todas as partes
    5. Salvar

    :param driver: A instância do WebDriver.
    :param polo: mantido por compatibilidade, não utilizado (modal usa toggle geral).
    :param log: Ativa logs detalhados.
    :return: True se executou com sucesso, False caso contrário.
    """
    try:
        from Fix.utils_observer import aguardar_renderizacao_nativa

        # 1. Ativar múltipla seleção nos ANEXOS
        if log:
            logger.info('[VISIBILIDADE_LOTE] Ativando múltipla seleção nos anexos...')
        try:
            btn_multi = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]'))
            )
            driver.execute_script("arguments[0].click();", btn_multi)
            time.sleep(0.5)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Falha ao ativar múltipla seleção nos anexos: {e}')
            return False

        # 2. Selecionar APENAS os anexos que receberam sigilo (is-sigiloso)
        if log:
            logger.info('[VISIBILIDADE_LOTE] Selecionando anexos com sigilo inserido...')
        selecionados = 0
        try:
            anexos = driver.find_elements(By.CSS_SELECTOR, '.tl-item-anexo')
            for anexo in anexos:
                if not anexo.find_elements(By.CSS_SELECTOR, 'a.tl-documento.is-sigiloso'):
                    continue
                try:
                    chk = anexo.find_element(By.CSS_SELECTOR, 'span.mat-checkbox-inner-container')
                    driver.execute_script("arguments[0].click();", chk)
                    selecionados += 1
                    time.sleep(0.1)
                except Exception:
                    continue
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Erro ao selecionar checkboxes dos anexos: {e}')
            return False

        if selecionados == 0:
            if log:
                logger.warning('[VISIBILIDADE_LOTE] Nenhum anexo com is-sigiloso encontrado para selecionar')
            return False

        if log:
            logger.info(f'[VISIBILIDADE_LOTE] {selecionados} anexo(s) selecionado(s)')
        time.sleep(0.3)

        # 3. Clicar botão de visibilidade dos anexos selecionados
        if log:
            logger.info('[VISIBILIDADE_LOTE] Abrindo modal de visibilidade...')
        try:
            btn_vis = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-plus.fa-lg.tl-nao-sigiloso'))
            )
            driver.execute_script("arguments[0].click();", btn_vis)
            time.sleep(0.5)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Falha ao clicar botão de visibilidade dos anexos: {e}')
            return False

        # 4. Localizar modal
        modal_container = '.cdk-overlay-container .mat-dialog-container'
        try:
            modal = WebDriverWait(driver, 4, poll_frequency=0.1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, modal_container))
            )
        except TimeoutException:
            if log:
                logger.error('[VISIBILIDADE_LOTE] Modal não apareceu')
            return False

        time.sleep(0.2)

        # 5. Marcar todas as partes via header toggle
        if log:
            logger.info('[VISIBILIDADE_LOTE] Marcando todas as partes no modal...')
        try:
            icone_header = modal.find_element(By.CSS_SELECTOR, 'i.fa.fa-check.botao-icone-titulo-coluna')
            driver.execute_script("arguments[0].click();", icone_header)
            time.sleep(0.2)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE_LOTE] Falha ao marcar partes no modal: {e}')
            return False

        # 6. Salvar
        if log:
            logger.info('[VISIBILIDADE_LOTE] Salvando configuração...')
        try:
            btn_salvar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
            )
            btn_salvar.click()
            aguardar_renderizacao_nativa(driver, 'simple-snack-bar', 'aparecer', 5)
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
