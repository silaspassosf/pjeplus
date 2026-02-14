import logging
logger = logging.getLogger(__name__)

from .core import *


def def_chip(driver, numero_processo, observacao, debug=False, timeout=10):
    """
    Remove chips de 'Prazo vencido' e 'Prazo vencido pós sentença' do processo.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo (para logs)
        observacao: Observação que disparou a ação (para logs)
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se pelo menos um chip foi removido, False caso contrário
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    chips_removidos = 0

    def log_msg(msg):
        if debug:
            try:
                print(msg)
            except Exception:
                pass

    try:
        chips_para_remover = [
            "Prazo vencido",
            "Prazo vencido pós sentença",
            "SISBAJUD",
        ]
        # Busca todos chips visíveis de uma vez
        chips_xpath = "//mat-chip"
        chip_elements = driver.find_elements(By.XPATH, chips_xpath)
        chips_encontrados = []
        for chip_element in chip_elements:
            try:
                chip_text = chip_element.text.strip()
                # Checa se o chip tem algum dos textos alvo
                if any(rem_text in chip_text for rem_text in chips_para_remover):
                    chips_encontrados.append(chip_element)
            except Exception as e:
                log_msg(f"Erro ao ler chip: {e}")
                continue
        if not chips_encontrados:
            log_msg(" Nenhum chip para remover encontrado - operação concluída com sucesso")
            return True
        for chip_element in chips_encontrados:
            try:
                chip_text = chip_element.text.strip()
                log_msg(f"Removendo chip: {chip_text}")
                botao_remover = chip_element.find_element(
                    By.CSS_SELECTOR,
                    "button[mattooltip*='Remover Chip'], button.etq-botao-excluir"
                )
                botao_remover.click()
                time.sleep(1)
                try:
                    botao_sim = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//button[.//span[contains(text(), 'Sim')]]"
                        ))
                    )
                    log_msg(f"Confirmando remoção do chip '{chip_text}'")
                    botao_sim.click()
                    time.sleep(2)
                    chips_removidos += 1
                    log_msg(f" Chip '{chip_text}' removido com sucesso")
                except Exception as e:
                    log_msg(f" Erro ao confirmar remoção do chip '{chip_text}': {e}")
                    continue
            except Exception as e:
                log_msg(f" Erro ao processar chip: {e}")
                continue
        if chips_removidos > 0:
            log_msg(f" Total de chips removidos: {chips_removidos}")
            return True
        log_msg(" Nenhum chip foi removido")
        return False
    except Exception as e:
        log_msg(f" Erro geral na remoção de chips: {e}")
    return False
