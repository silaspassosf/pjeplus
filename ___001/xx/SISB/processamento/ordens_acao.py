import logging
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from ..utils import safe_click

logger = logging.getLogger(__name__)

"""
SISBAJUD Ordens - Selecionar acao por fluxo
"""


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """
    Seleciona a acao correta na pagina /desdobrar baseado no tipo de fluxo.
    (Implementacao completa das linhas 2240-2465)
    """
    try:
        # Determinar acao alvo conforme fluxo
        if tipo_fluxo == 'POSITIVO':
            if valor_parcial:
                acao_alvo = 'Transferir valor e desbloquear saldo remanescente'
            else:
                acao_alvo = 'Transferir valor'
        else:  # DESBLOQUEIO
            acao_alvo = 'Desbloquear valor'

        # Aguardar pagina carregar
        time.sleep(0.5)

        # Buscar todos os mat-selects (pode haver varios na pagina)
        selects = driver.find_elements(By.CSS_SELECTOR, "mat-select")

        if not selects:
            return False

        # Tentar cada dropdown ate encontrar a acao
        for idx, select_element in enumerate(selects):
            try:
                # Verificar se o select esta visivel
                if not select_element.is_displayed():
                    continue

                # Tecnica do a.py: clicar no parentElement.parentElement para abrir dropdown
                try:
                    parent_element = driver.execute_script("return arguments[0].parentElement.parentElement;", select_element)
                    if parent_element:
                        safe_click(driver, parent_element, 'click')
                    else:
                        safe_click(driver, select_element, 'click')
                except Exception:
                    safe_click(driver, select_element, 'click')

                time.sleep(0.8)

                # Aguardar opcoes aparecerem com retry conservador
                opcoes = None
                max_tentativas_opcoes = 2
                for tentativa_opcoes in range(max_tentativas_opcoes):
                    try:
                        opcoes = WebDriverWait(driver, 3.0).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                        )

                        if opcoes and len(opcoes) > 0:
                            break
                        if tentativa_opcoes < max_tentativas_opcoes - 1:
                            time.sleep(1.5)

                    except Exception:
                        if tentativa_opcoes < max_tentativas_opcoes - 1:
                            time.sleep(1.5)
                        else:
                            continue

                if not opcoes or len(opcoes) == 0:
                    # Fechar dropdown
                    try:
                        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    except Exception:
                        continue
                    time.sleep(0.3)
                    continue

                # Iterar opcoes e verificar texto
                for opcao in opcoes:
                    try:
                        texto_opcao = opcao.text.strip()

                        if tipo_fluxo == 'POSITIVO' and valor_parcial is not None and 'remanescente' in texto_opcao.lower():
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.5)

                            # Preencher valor parcial
                            try:
                                campo_valor = WebDriverWait(driver, 2).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Valor'][prefix='R$ ']"))
                                )
                                campo_valor.clear()
                                valor_formatado = f"{valor_parcial:.2f}".replace('.', ',')
                                campo_valor.send_keys(valor_formatado)
                                return True
                            except Exception as e_valor:
                                if log:
                                    logger.error(f"[_aplicar_acao]    Erro ao preencher valor parcial: {e_valor}")
                                return False

                        if tipo_fluxo == 'POSITIVO' and texto_opcao == 'Transferir valor':
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.3)
                            return True

                        if tipo_fluxo == 'DESBLOQUEIO' and 'Desbloquear valor' in texto_opcao:
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.3)
                            return True

                    except Exception as e_opcao:
                        if log:
                            logger.error(f"[_aplicar_acao]   Erro ao processar opcao: {e_opcao}")
                        continue

                # Nenhuma opcao encontrada neste dropdown, fechar e prosseguir
                try:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.3)
                except Exception:
                    continue

            except Exception as e_dropdown:
                if log:
                    logger.error(f"[_aplicar_acao]  Erro ao processar dropdown #{idx+1}: {e_dropdown}")
                try:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                except Exception:
                    continue
                time.sleep(0.3)
                continue

        return False

    except Exception as e:
        if log:
            logger.error(f"[_aplicar_acao]  Erro critico: {e}")
            import traceback
            traceback.print_exc()
        return False