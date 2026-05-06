import logging
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

"""
SISB Navegacao - Navegacao entre paginas do SISBAJUD
Funcoes para voltar entre listas de ordens e series
"""


def _voltar_para_lista_ordens_serie(driver, log=True):
    """
    Volta da ordem processada para a lista de ordens da serie.
    Clica apenas uma vez no botao voltar (chevron-left).

    IMPORTANTE: So deve ser chamado quando estiver em /desdobrar!

    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log das operacoes

    Returns:
        bool: True se conseguiu voltar com sucesso
    """
    try:
        # VERIFICAR SE ESTA EM /DESDOBRAR ANTES DE TENTAR VOLTAR
        url_atual = driver.current_url.lower()
        if "/desdobrar" not in url_atual:
            # Se ja esta na lista de ordens (/detalhes), nao precisa voltar
            if "/detalhes" in url_atual:
                return True
            return False

        # Aguardar um pouco para garantir que a pagina esta carregada
        time.sleep(1)

        # Seletores para o botao voltar (chevron-left)
        seletores_voltar = [
            "button[aria-label='Voltar'] i.fa-chevron-left",
            "button i.fa-chevron-left",
            ".fa-chevron-left",
            "i.fa-chevron-left",
            "button.btn-voltar",
            "[aria-label='Voltar']",
            "button[title='Voltar']"
        ]

        # Tentar encontrar e clicar no botao voltar
        botao_encontrado = False
        for seletor in seletores_voltar:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)

                for elemento in elementos:
                    if elemento.is_displayed() and elemento.is_enabled():
                        driver.execute_script("arguments[0].click();", elemento)
                        botao_encontrado = True
                        break

                if botao_encontrado:
                    break

            except Exception:
                continue

        if not botao_encontrado:
            # Ultima tentativa: buscar por JavaScript
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

        # Aguardar URL mudar (sinal de que navegacao iniciou)
        for _ in range(10):
            time.sleep(0.5)
            if "/desdobrar" not in driver.current_url:
                break

        # Aguardar tabela de ordens reaparecer
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
            )
            time.sleep(1.5)
        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD]  Erro ao aguardar tabela: {e}")
        return True

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao voltar para lista de ordens da serie: {str(e)}")
        return False


def _voltar_para_lista_principal(driver, log=True):
    """
    Volta para a lista principal de series usando navegacao direta ou botao voltar.

    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log das operacoes

    Returns:
        bool: True se conseguiu voltar com sucesso
    """
    try:
        # Detectar e fechar overlays/modais que podem bloquear cliques
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, 'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing')
            if overlays:
                for overlay in overlays:
                    try:
                        overlay.click()
                        time.sleep(0.5)
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].style.display = 'none';", overlay)
                        except Exception:
                            pass
                time.sleep(1.0)
        except Exception:
            pass

        # Tentar navegacao direta usando a URL
        url_atual = driver.current_url

        # Se estamos em uma pagina de detalhes de serie, voltar para teimosinha
        if "/detalhes" in url_atual:
            numero_processo = None

            # Tentar extrair numero do processo
            if "numeroProcesso=" in url_atual:
                numero_processo = url_atual.split("numeroProcesso=")[1].split("&")[0]
            elif hasattr(driver, '_numero_processo_atual'):
                numero_processo = driver._numero_processo_atual

            # Construir URL de volta
            if numero_processo:
                url_volta = f"https://sisbajud.cnj.jus.br/teimosinha?numeroProcesso={numero_processo}"
            else:
                url_volta = "https://sisbajud.cnj.jus.br/teimosinha"

            driver.get(url_volta)
            time.sleep(3)
            return True

        # Se nao esta em pagina de detalhes, tentar usar botao voltar (duas vezes)
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
                    # Pressionar ESC antes para fechar possiveis modais
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                    except Exception:
                        pass

                    botao_icon = driver.find_element(By.CSS_SELECTOR, seletor)
                    # Tentar pegar botao pai
                    try:
                        botao = botao_icon.find_element(By.XPATH, './ancestor::button[1]')
                    except Exception:
                        botao = botao_icon

                    driver.execute_script("arguments[0].click();", botao)
                    botao_voltar_clicado = True
                    time.sleep(2)
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