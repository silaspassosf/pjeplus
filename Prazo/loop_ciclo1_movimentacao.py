import logging
import time
from typing import Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from .loop_base import *

logger = logging.getLogger(__name__)

def _ciclo1_marcar_todas(driver: WebDriver) -> str:
    """Seleciona todos os processos via botão marcar-todas."""
    logger.info("[CICLO1/MARCAR_TODAS] Iniciando busca e clique")
    
    try:
        # XPath robusto do legado - element_to_be_clickable
        logger.info("[CICLO1/MARCAR_TODAS] Aguardando botão marcar-todas...")
        btn_marcar_todas = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//i[contains(@class, 'marcar-todas')]"))
        )
        html_btn = btn_marcar_todas.get_attribute('outerHTML')
        logger.info(f"[CICLO1/MARCAR_TODAS] Botão encontrado: {html_btn[:200]}")
        
        # JS click direto como no legado
        logger.info("[CICLO1/MARCAR_TODAS] Executando clique via JS...")
        result = driver.execute_script("""
        arguments[0].scrollIntoView(true);
        arguments[0].click();
        return true;
        """, btn_marcar_todas)
        
        if not result:
            logger.error("[CICLO1/MARCAR_TODAS] JS retornou false")
            return "error"
            
        logger.info("[CICLO1/MARCAR_TODAS] Clique executado, aguardando efeito...")
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
        except Exception:
            time.sleep(1)
        
        # Validar checkboxes marcados
        marcados = driver.execute_script(
            "return document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').length;"
        )
        logger.info(f"[CICLO1/MARCAR_TODAS] {marcados} checkbox(es) marcado(s)")
        
        if int(marcados or 0) > 0:
            logger.info("[CICLO1/MARCAR_TODAS] Sucesso")
            return "success"
        else:
            logger.error("[CICLO1/MARCAR_TODAS] Nenhum checkbox marcado após clique")
            return "marcar_todas_not_found_but_continue"
            
    except TimeoutException:
        logger.error("[CICLO1/MARCAR_TODAS] Timeout: botão não encontrado em 5s")
        return "marcar_todas_not_found_but_continue"
    except Exception as e:
        logger.error(f"[CICLO1/MARCAR_TODAS] Exceção: {str(e)[:300]}")
        import traceback
        logger.error(f"[CICLO1/MARCAR_TODAS] Traceback: {traceback.format_exc()[:800]}")
        return "error"

def _ciclo1_abrir_suitcase(driver: WebDriver) -> bool:
    """Abre suitcase para movimentação em lote usando JavaScript click (VERSÃO CORRIGIDA)."""
    from Fix.core import com_retry

    logger.info("[DEBUG] Aguardando suitcase aparecer...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
        )
        logger.info("[DEBUG] Suitcase apareceu na página.")
    except Exception as e:
        logger.info(f"[DEBUG] Suitcase não apareceu: {e}")
        return False

    def _tentar_abrir_suitcase():
        if not pausar_confirmacao('CICLO1/SUITCASE_INTERNO', 'Executar clique no suitcase'):
            return False
        logger.info("[DEBUG] Tentando clicar no suitcase...")
        by = By.CSS_SELECTOR
        seletor = "button[aria-label='Movimentar em Lote'] i.fas.fa-suitcase.icone"
        
        elemento = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((by, seletor))
        )
        
        clicou = driver.execute_script(
            """
            let element = arguments[0];
            let target = element.closest('button, div[role="button"], mat-icon, span') || element;
            target.scrollIntoView({block: 'center'});
            target.click();
            return true;
            """,
            elemento,
        )
        
        if clicou:
            log_seletor_vencedor('CICLO1/SUITCASE', by, seletor)
            logger.info("[DEBUG] Suitcase clicado com sucesso.")
            return True
        
        logger.info("[CICLO1/SUITCASE] Clique falhou com seletor específico")
        return False

    try:
        if com_retry(_tentar_abrir_suitcase, max_tentativas=3, backoff_base=1.5, log=True):
            logger.info("[DEBUG] Suitcase aberto após retry.")
            try:
                from Fix.core import aguardar_renderizacao_nativa
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
            except Exception:
                time.sleep(1)
            return True
        else:
            logger.info("[LOOP_PRAZO] Todas as tentativas de abrir suitcase falharam")
            return False
    except Exception as e:
        logger.info(f"[LOOP_PRAZO] Erro geral em abrir suitcase: {e}")
        return False

def _ciclo1_aguardar_movimentacao_lote(driver: WebDriver) -> bool:
    """Aguarda carregamento da página de movimentação em lote."""
    logger.info("[DEBUG] Aguardando URL /painel/movimentacao-lote...")
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains('/painel/movimentacao-lote')
        )
        logger.info(f"[DEBUG] URL atual: {driver.current_url}")
        if '/painel/movimentacao-lote' not in driver.current_url:
            logger.info(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
            return False
        logger.info(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.2)
        except Exception:
            time.sleep(1.2)
        return True
    except Exception as e:
        logger.info(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False

def _ciclo1_movimentar_destino_providencias(driver: WebDriver) -> bool:
    """Abordagem robusta para 'Cumprimento de providências' (Gabarito)."""
    opcao_destino = 'Cumprimento de providências'
    logger.info(f"[LOOP_PRAZO] Abordagem especial para '{opcao_destino}'")

    from Fix.core import com_retry
    
    def _tentar_selecionar_providencias():
        if not pausar_confirmacao('CICLO1/PROVIDENCIAS_DROPDOWN', 'Abrir dropdown de destino para providências'):
            return False

        seletor_dropdown = "div.mat-select-arrow-wrapper"
        logger.info(f"[CICLO1/PROVIDENCIAS_DROPDOWN] Abrindo dropdown com seletor: {seletor_dropdown}")
        try:
            seta_dropdown = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_dropdown))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seta_dropdown)
            driver.execute_script("arguments[0].click();", seta_dropdown)
            log_seletor_vencedor('CICLO1/PROVIDENCIAS_DROPDOWN', By.CSS_SELECTOR, seletor_dropdown)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Erro ao abrir dropdown de providências com seletor {seletor_dropdown}: {e}")
            return False

        try:
            overlay = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Overlay de providências não apareceu após abrir dropdown: {e}")
            return False

        opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
        logger.info(f"[CICLO1/PROVIDENCIAS_OPCAO] Selecionando opção com xpath: {opcao_xpath}")
        try:
            opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
            log_seletor_vencedor('CICLO1/PROVIDENCIAS_OPCAO', By.XPATH, opcao_xpath)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Opção '{opcao_destino}' não encontrada com xpath {opcao_xpath}: {e}")
            return False

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
        try:
            opcao_elemento.click()
        except Exception:
            driver.execute_script("arguments[0].click();", opcao_elemento)

        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.0)
        except Exception:
            time.sleep(1.0)

        return True

    try:
        if com_retry(_tentar_selecionar_providencias, max_tentativas=3):
            if not pausar_confirmacao('CICLO1/PROVIDENCIAS_MOVIMENTAR', 'Clique no botão Movimentar'):
                return False
            if not clicar_com_multiplos_seletores(
                driver,
                'CICLO1/PROVIDENCIAS_BOTAO_MOVIMENTAR',
                [
                    (By.CSS_SELECTOR, "button.mat-raised-button[color='primary']"),
                    (By.XPATH, "//button[contains(., 'Movimentar')]")
                ],
                timeout=10
            ):
                return False
            logger.info("[LOOP_PRAZO] ✅ Movimentação para providências confirmada.")
            return True
        return False
    except Exception as e:
        logger.info(f"[LOOP_PRAZO][ERRO] Falha em providências: {e}")
        return False

def _ciclo1_movimentar_destino(driver: WebDriver, opcao_destino: str) -> bool:
    """Seleciona destino usando abordagem direta (Gabarito)."""
    if opcao_destino == 'Cumprimento de providências':
        return _ciclo1_movimentar_destino_providencias(driver)
    logger.info(f"[CICLO1/DESTINO] Selecionando destino: '{opcao_destino}' (overlay-only)")
    try:
        if not pausar_confirmacao('CICLO1/DESTINO_ABRIR_DROPDOWN', f'Abrir dropdown para destino={opcao_destino}'):
            return False

        seletor_dropdown = "div.mat-select-arrow-wrapper"
        logger.info(f"[CICLO1/DESTINO_DROPDOWN] Abrindo dropdown com seletor: {seletor_dropdown}")
        try:
            seta_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_dropdown))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seta_dropdown)
            driver.execute_script("arguments[0].click();", seta_dropdown)
            log_seletor_vencedor('CICLO1/DESTINO_DROPDOWN', By.CSS_SELECTOR, seletor_dropdown)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Erro ao abrir dropdown de destino com seletor {seletor_dropdown}: {e}")
            return False

        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.2)
        except Exception:
            time.sleep(1.2)

        overlay = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
        )
        opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
        logger.info(f"[CICLO1/DESTINO_OPCAO] Selecionando opção com xpath: {opcao_xpath}")
        try:
            opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
            log_seletor_vencedor('CICLO1/DESTINO_OPCAO', By.XPATH, opcao_xpath)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Opção '{opcao_destino}' não encontrada com xpath {opcao_xpath}: {e}")
            return False

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, '.cdk-overlay-pane', timeout=0.3)
        except Exception:
            time.sleep(0.3)
        driver.execute_script("arguments[0].click();", opcao_elemento)
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1.0)
        except Exception:
            time.sleep(1.0)

        if not pausar_confirmacao('CICLO1/DESTINO_MOVIMENTAR', 'Clique no botão Movimentar'):
            return False

        seletor_movimentar = "button.mat-raised-button[color='primary']"
        logger.info(f"[CICLO1/DESTINO_BOTAO_MOVIMENTAR] Clicando botão movimentar com seletor: {seletor_movimentar}")
        try:
            btn_movimentar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_movimentar))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_movimentar)
            driver.execute_script("arguments[0].click();", btn_movimentar)
            log_seletor_vencedor('CICLO1/DESTINO_BOTAO_MOVIMENTAR', By.CSS_SELECTOR, seletor_movimentar)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Erro ao clicar botão Movimentar com seletor {seletor_movimentar}: {e}")
            return False

        logger.info(f"[LOOP_PRAZO] ✅ Destino '{opcao_destino}' processado (legacy overlay flow).")
        return True
    except Exception as e:
        logger.info(f"[LOOP_PRAZO][ERRO] Falha ao movimentar para {opcao_destino}: {e}")
        return False

def _ciclo1_retornar_lista(driver: WebDriver) -> None:
    """Retorna graciosamente para a lista de processos."""
    try:
        if not pausar_confirmacao('CICLO1/RETORNO_INTERNO', 'Executar retorno com history.back'):
            return
        logger.info("[DEBUG] Retornando para a lista de processos...")
        driver.execute_script("window.history.back();")
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=2)
        except Exception:
            time.sleep(2)
        # Garantir fechamento de modais se sobrarem
        driver.execute_script("document.querySelectorAll('.cdk-overlay-backdrop').forEach(e => e.click())")
    except Exception as e:
        logger.info(f"[DEBUG] Erro ao retornar: {e}")