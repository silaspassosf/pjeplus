import logging
import time
import random

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

"""
SISB Minutas - Protocolo
"""


def _protocolar_minuta(driver, protocolo_minuta=None, log=True):
    """
    Helper para protocolar/assinar minuta no SISBAJUD.
    """
    try:
        if log:
            _ = protocolo_minuta

        time.sleep(1)

        try:
            script_encontrar_botao = """
            const buttons = Array.from(document.querySelectorAll('button'));
            const protocoloBtn = buttons.find(btn => {
                const spans = btn.querySelectorAll('span.mat-button-wrapper');
                return Array.from(spans).some(span => {
                    const hasIcon = span.querySelector('mat-icon.fa-gavel');
                    const hasText = span.textContent.includes('Protocolar');
                    return hasIcon || hasText;
                });
            });
            if (protocoloBtn) {
                protocoloBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                return true;
            }
            return false;
            """

            encontrado = driver.execute_script(script_encontrar_botao)
            if not encontrado:
                return False

            time.sleep(0.5)

            script_clicar = """
            const buttons = Array.from(document.querySelectorAll('button'));
            const protocoloBtn = buttons.find(btn => {
                const spans = btn.querySelectorAll('span.mat-button-wrapper');
                return Array.from(spans).some(span => {
                    const hasIcon = span.querySelector('mat-icon.fa-gavel');
                    const hasText = span.textContent.includes('Protocolar');
                    return hasIcon || hasText;
                });
            });
            if (protocoloBtn) {
                protocoloBtn.click();
                return true;
            }
            return false;
            """

            clicado = driver.execute_script(script_clicar)
            if not clicado:
                return False

        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao clicar no botao "Protocolar": {e}')
            return False

        time.sleep(1)

        try:
            campo_senha = driver.find_element(By.CSS_SELECTOR, 'input[type="password"][formcontrolname="senha"]')
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", campo_senha)
            time.sleep(0.3)

            campo_senha.click()
            time.sleep(0.3)

            senha = "Fl@quinho182"
            for char in senha:
                if random.random() < 0.05:
                    erro_char = chr(random.randint(33, 126))
                    campo_senha.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    campo_senha.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                campo_senha.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))

        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao digitar senha: {e}')
            return False

        time.sleep(0.6)

        try:
            script_confirmar = """
            const buttons = Array.from(document.querySelectorAll('button[type="submit"][color="primary"]'));
            const confirmBtn = buttons.find(btn => {
                const wrapper = btn.querySelector('span.mat-button-wrapper');
                return wrapper && wrapper.textContent.trim() === 'Confirmar';
            });
            if (confirmBtn) {
                confirmBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                return true;
            }
            return false;
            """

            encontrado = driver.execute_script(script_confirmar)

            if not encontrado:
                script_confirmar_alt = """
                const buttons = Array.from(document.querySelectorAll('button'));
                const confirmBtn = buttons.find(btn => btn.textContent.includes('Confirmar'));
                if (confirmBtn) {
                    confirmBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    return true;
                }
                return false;
                """
                encontrado = driver.execute_script(script_confirmar_alt)

            if not encontrado:
                return False

            time.sleep(0.3)

            script_clicar = """
            const buttons = Array.from(document.querySelectorAll('button[type="submit"][color="primary"]'));
            let confirmBtn = buttons.find(btn => {
                const wrapper = btn.querySelector('span.mat-button-wrapper');
                return wrapper && wrapper.textContent.trim() === 'Confirmar';
            });

            if (!confirmBtn) {
                const allButtons = Array.from(document.querySelectorAll('button'));
                confirmBtn = allButtons.find(btn => btn.textContent.includes('Confirmar'));
            }

            if (confirmBtn) {
                confirmBtn.click();
                return true;
            }
            return false;
            """

            clicado = driver.execute_script(script_clicar)
            if clicado:
                time.sleep(2)

                script_verificar_sucesso = """
                const buttons = Array.from(document.querySelectorAll('button[title="Copiar Dados para Nova Ordem"]'));
                if (buttons.length > 0) {
                    return true;
                }
                const allButtons = Array.from(document.querySelectorAll('button'));
                const copyBtn = allButtons.find(btn => {
                    const icon = btn.querySelector('mat-icon.fa-copy');
                    const text = btn.textContent;
                    return icon && text.includes('Copiar Dados');
                });
                return copyBtn !== undefined;
                """

                sucesso_verificado = False
                for _ in range(10):
                    try:
                        sucesso_verificado = driver.execute_script(script_verificar_sucesso)
                        if sucesso_verificado:
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)

                return bool(sucesso_verificado)

            return False

        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao confirmar: {e}')
            return False

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD][PROTOCOLO]  Erro ao protocolar minuta: {e}')
            import traceback
            traceback.print_exc()
        return False