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
    from Fix.core import com_retry

    def _tentar_marcar():
        logger.info("[CICLO1/MARCAR_TODAS] Aguardando botão marcar-todas...")
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//i[contains(@class, 'marcar-todas')]") )
        )
        html = btn.get_attribute('outerHTML')
        logger.info(f"[CICLO1/MARCAR_TODAS] Botão encontrado: {html[:200]}")
        logger.info("[CICLO1/MARCAR_TODAS] Executando clique via JS...")
        try:
            result = driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click(); return true;", btn)
        except Exception:
            result = False
        if result:
            try:
                from Fix.core import aguardar_renderizacao_nativa
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
            except Exception:
                time.sleep(1)
        return result

    try:
        if com_retry(_tentar_marcar, max_tentativas=5, backoff_base=1.5, log=True):
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
        else:
            logger.info("[LOOP_PRAZO] Todas as tentativas de marcar-todas falharam")
            return "marcar_todas_not_found_but_continue"
    except Exception as e:
        logger.error(f"[CICLO1/MARCAR_TODAS] Erro geral: {e}")
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
    """Aguarda carregamento da página de movimentação em lote.
    
    Inclui espera pelo spinner 'Recuperando transições possíveis...' (div.carregando)
    desaparecer antes de retornar — garante que o dropdown de destino terá opções.
    """
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

        # ── Aguardar spinner "Recuperando transições possíveis..." desaparecer ──
        # Sem isso, o dropdown de destino não terá opções e o clique nunca funciona
        logger.info("[CICLO1/LOTE] Aguardando transições carregarem (div.carregando sumir)...")
        try:
            WebDriverWait(driver, 25).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.carregando'))
            )
            logger.info("[CICLO1/LOTE] ✅ Transições carregadas (spinner sumiu)")
        except TimeoutException:
            logger.error("[CICLO1/LOTE] ❌ Timeout: spinner 'Recuperando transições possíveis...' não sumiu em 25s")
            logger.error("[CICLO1/LOTE] Algum processo do lote não possui a transição de destino — abortando")
            return False

        time.sleep(0.5)
        return True
    except Exception as e:
        logger.info(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False


def _ciclo1_movimentar_destino_providencias(driver: WebDriver) -> bool:
    """Abordagem robusta para 'Cumprimento de providências' (baseada no legado)."""
    opcao_destino = 'Cumprimento de providências'
    logger.info(f"[LOOP_PRAZO] Abordagem especial para '{opcao_destino}'")

    # ── Passo 1: abrir dropdown (até 8 tentativas, 3 cliques por tentativa) ──
    max_tent_abrir = 8
    dropdown_aberto = False

    for tent in range(1, max_tent_abrir + 1):
        try:
            logger.info(f"[CICLO1/PROVIDENCIAS_DROPDOWN] Tentativa {tent}/{max_tent_abrir}")

            seta_dropdown = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
            )
            time.sleep(1.5)                                                     # legado: dar tempo ao Angular
            driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
            driver.execute_script("document.body.style.zoom='100%'")           # legado: garantir zoom neutro
            time.sleep(0.5)

            # Até 3 cliques por tentativa, verificando se overlay apareceu
            for click_num in range(1, 4):
                try:
                    driver.execute_script("arguments[0].click();", seta_dropdown)
                    logger.info(f"[CICLO1/PROVIDENCIAS_DROPDOWN] Clique {click_num} executado")
                    time.sleep(2.0)                                             # legado: espera generosa

                    overlay = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                    )
                    opcoes = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                    textos = [o.text.strip() for o in opcoes if o.text.strip()]
                    if textos:
                        logger.info(f"[CICLO1/PROVIDENCIAS_DROPDOWN] ✅ {len(textos)} opções: {textos}")
                        dropdown_aberto = True
                        break
                except Exception:
                    time.sleep(1.0)

            if dropdown_aberto:
                break

        except Exception as e:
            logger.warning(f"[CICLO1/PROVIDENCIAS_DROPDOWN] Erro tentativa {tent}: {e}")
            time.sleep(1.0)

    if not dropdown_aberto:
        logger.error(f"[LOOP_PRAZO] Falha ao abrir dropdown de providências após {max_tent_abrir} tentativas")
        return False

    # ── Passo 2: selecionar a opção (até 8 tentativas) ──
    max_tent_opcao = 8
    for tent in range(1, max_tent_opcao + 1):
        try:
            logger.info(f"[CICLO1/PROVIDENCIAS_OPCAO] Tentativa {tent}/{max_tent_opcao}")

            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )
            opcao_elemento = None

            # Busca exata → parcial "Cumprimento" → parcial "providências"
            for xpath in [
                f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']",
                ".//span[contains(@class,'mat-option-text') and contains(text(),'Cumprimento')]",
                ".//span[contains(@class,'mat-option-text') and contains(text(),'provid')]",
            ]:
                try:
                    opcao_elemento = overlay.find_element(By.XPATH, xpath)
                    break
                except Exception:
                    pass

            if opcao_elemento:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opcao_elemento)
                time.sleep(0.5)
                try:
                    opcao_elemento.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", opcao_elemento)
                logger.info(f"[CICLO1/PROVIDENCIAS_OPCAO] ✅ Opção selecionada na tentativa {tent}")
                time.sleep(1.5)
                break
            else:
                logger.warning(f"[CICLO1/PROVIDENCIAS_OPCAO] Opção não encontrada, reabrindo dropdown...")
                if tent < max_tent_opcao:
                    try:
                        driver.execute_script("document.body.click();")
                        time.sleep(0.5)
                        seta = driver.find_element(By.CSS_SELECTOR, "div.mat-select-arrow-wrapper")
                        seta.click()
                        time.sleep(1.5)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"[CICLO1/PROVIDENCIAS_OPCAO] Erro tentativa {tent}: {e}")
            if tent == max_tent_opcao:
                return False
            time.sleep(1.0)

    # ── Passo 3: clicar Movimentar ──
    time.sleep(3.0)                                                             # legado: aguardar botão habilitar
    seletor_btn = "button.mat-raised-button[color='primary']"
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        result = driver.execute_script("arguments[0].click(); return true;", btn)
        if result:
            logger.info("[LOOP_PRAZO] ✅ Botão 'Movimentar processos' clicado")
            time.sleep(2.0)
            return True
        logger.error("[LOOP_PRAZO] JS click no botão Movimentar retornou falso")
        return False
    except Exception as e:
        logger.error(f"[LOOP_PRAZO] Botão Movimentar não encontrado: {e}")
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