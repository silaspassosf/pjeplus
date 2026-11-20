import logging
from Fix.core import safe_click_no_scroll
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from Fix import espera

logger = logging.getLogger(__name__)

"""
SISB Navegacao - Navegacao entre paginas do SISBAJUD
Funcoes para voltar entre listas de ordens e series
"""


def _voltar_para_lista_ordens_serie(driver, log=True):
    """Volta da ordem processada para a lista de ordens da serie."""
    try:
        url_atual = driver.current_url.lower()
        if "/desdobrar" not in url_atual:
            if "/detalhes" in url_atual:
                return True
            return False

        espera.ate_js(driver, "document.readyState === 'complete'", teto=3)

        seletores_voltar = [
            "button[aria-label='Voltar'] i.fa-chevron-left",
            "button i.fa-chevron-left",
            ".fa-chevron-left",
            "i.fa-chevron-left",
            "button.btn-voltar",
            "[aria-label='Voltar']",
            "button[title='Voltar']"
        ]

        botao_encontrado = False
        for seletor in seletores_voltar:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)

                for elemento in elementos:
                    if elemento.is_displayed() and elemento.is_enabled():
                        safe_click_no_scroll(driver, elemento)
                        botao_encontrado = True
                        break

                if botao_encontrado:
                    break

            except Exception:
                continue

        if not botao_encontrado:
            try:
                js_script = """
                var botoes = document.querySelectorAll('button, a, .btn');
                for (var i = 0; i < botoes.length; i++) {
                    var botao = botoes[i];
                    var chevron = botao.querySelector('i.fa-chevron-left, .fa-chevron-left');
                    if (chevron && botao.offsetParent !== null) {
                        botao.click();
                        return 'Clicou via JavaScript';
                    }
                }
                return 'Botao nao encontrado';
                """
                resultado_js = driver.execute_script(js_script)
                botao_encontrado = resultado_js == 'Clicou via JavaScript'
            except Exception:
                pass

        if not botao_encontrado:
            return False

        for _ in range(10):
            espera.ate_js(driver, "!location.href.includes('/desdobrar')", teto=0.5)
            if "/desdobrar" not in driver.current_url:
                break

        if not espera.ate_aparecer(driver, 'table.mat-table', teto=10):
            if log:
                logger.error("[SISBAJUD]  Erro ao aguardar tabela: nao apareceu")
        return True

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao voltar para lista de ordens da serie: {str(e)}")
        return False


def _voltar_para_lista_principal(driver, log=True):
    """Volta para a lista principal de series usando navegacao direta ou botao voltar."""
    try:
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, 'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing')
            if overlays:
                for overlay in overlays:
                    try:
                        overlay.click()
                        espera.ate_sumir(
                            driver,
                            'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing',
                            teto=0.5,
                        )
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].style.display = 'none';", overlay)
                        except Exception:
                            pass
                espera.assentar(driver, 1)
        except Exception:
            pass

        # O Angular gerencia o retorno e preserva o estado sem recarregar a pagina
        url_atual = driver.current_url

        for _ in range(2):
            seletores_voltar = [
                'button.mat-icon-button .fa-chevron-left',
                'button[mat-icon-button] .fas.fa-chevron-left',
                'button .mat-icon.fa-chevron-left',
                'button i.fa-chevron-left',
                '.fa-chevron-left'
            ]

            botao_voltar_clicado = False
            for seletor in seletores_voltar:
                try:
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        espera.ate_sumir(
                            driver,
                            'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing',
                            teto=0.5,
                        )
                    except Exception:
                        pass

                    botao_icon = driver.find_element(By.CSS_SELECTOR, seletor)
                    try:
                        botao = botao_icon.find_element(By.XPATH, './ancestor::button[1]')
                    except Exception:
                        botao = botao_icon

                    safe_click_no_scroll(driver, botao)
                    botao_voltar_clicado = True
                    espera.ate_aparecer(driver, 'table.mat-table', teto=5)
                    break
                except Exception:
                    continue

            if not botao_voltar_clicado:
                break

        if botao_voltar_clicado:
            return True
        return False

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao voltar para lista principal: {e}")
        return False
