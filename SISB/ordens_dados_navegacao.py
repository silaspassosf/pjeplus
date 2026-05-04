"""
SISB Ordens Dados e Navegacao - Dados de ordens e navegacao entre paginas
Consolida SISB/ordens/processor.py e SISB/navigation/navigator.py
"""

import logging
import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import carregar_dados_processo, safe_click

logger = logging.getLogger(__name__)


# =============================================================================
# DADOS DE ORDEM
# =============================================================================


def _carregar_dados_ordem():
    """
    Helper para carregar dados do processo para processamento de ordens.

    Returns:
        tuple: (dados_processo, numero_processo) ou (None, None) se erro
    """
    try:
        dados_arquivo = carregar_dados_processo()
        if not dados_arquivo or not isinstance(dados_arquivo, dict):
            return None, None

        numero_bruto = dados_arquivo.get('numero')
        if isinstance(numero_bruto, list) and len(numero_bruto) > 0:
            numero_processo = numero_bruto[0]
        elif isinstance(numero_bruto, str) and numero_bruto.strip():
            numero_processo = numero_bruto.strip()
        else:
            return None, None
        return dados_arquivo, numero_processo

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao carregar dados: {e}')
        return None, None


def _extrair_ordens_da_serie(driver, log=True):
    """
    Extrai ordens da pagina de detalhes da serie.

    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log

    Returns:
        list: Lista de ordens com estrutura
              {'sequencial', 'data', 'valor_bloquear', 'protocolo', 'linha_el'}
    """
    ordens = []
    try:
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
        )

        linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
        meses = {
            "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
            "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
        }

        for linha in linhas:
            try:
                cols = linha.find_elements(By.CSS_SELECTOR, "td")
                if len(cols) < 6:
                    continue

                sequencial = int(cols[0].text.strip())
                data_txt = cols[2].text.strip()
                protocolo = cols[5].text.strip()

                situacao = ""
                try:
                    all_text = ' '.join([c.text for c in cols]).strip()
                    if 'Respondida com minuta' in all_text:
                        situacao = "Respondida com minuta"
                    elif 'Respondida' in all_text:
                        situacao = "Respondida"
                except Exception:
                    situacao = ""

                valor_txt = cols[4].text.strip()

                data_ordem = None
                if "/" in data_txt:
                    partes = data_txt.split(",")
                    data_parte = partes[0].strip() if len(partes) > 0 else data_txt.strip()
                    data_split = data_parte.split("/")
                    if len(data_split) == 3:
                        try:
                            dia, mes, ano = map(int, data_split)
                            data_ordem = datetime(ano, mes, dia)
                        except Exception:
                            continue

                if not data_ordem:
                    continue

                try:
                    valor = float(
                        valor_txt.replace("R$", "").replace(" ", "")
                        .replace(".", "").replace(",", ".").strip()
                    )
                except Exception:
                    continue

                ordens.append({
                    "sequencial": sequencial,
                    "data": data_ordem,
                    "valor_bloquear": valor,
                    "protocolo": protocolo,
                    "situacao": situacao,
                    "linha_el": linha,
                })

            except Exception as e:
                if log:
                    logger.error(f"[SISBAJUD] Ignorando linha: erro inesperado - {e}")
                continue

        ordens.sort(key=lambda x: x["data"])
        return ordens

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD] Erro ao extrair ordens: {e}")
        return []


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """
    Seleciona a acao correta na pagina /desdobrar baseado no tipo de fluxo.

    Args:
        driver: WebDriver do Selenium
        tipo_fluxo: 'POSITIVO' ou 'DESBLOQUEIO'
        log: Se deve fazer log
        valor_parcial: Valor parcial para transferencia (apenas POSITIVO)

    Returns:
        bool: True se conseguiu aplicar a acao
    """
    try:
        if tipo_fluxo == 'POSITIVO':
            if valor_parcial:
                acao_alvo = 'Transferir valor e desbloquear saldo remanescente'
            else:
                acao_alvo = 'Transferir valor'
        else:  # DESBLOQUEIO
            acao_alvo = 'Desbloquear valor'

        time.sleep(0.5)

        selects = driver.find_elements(By.CSS_SELECTOR, "mat-select")

        if not selects:
            return False

        for idx, select_element in enumerate(selects):
            try:
                if not select_element.is_displayed():
                    continue

                try:
                    parent_element = driver.execute_script(
                        "return arguments[0].parentElement.parentElement;", select_element
                    )
                    if parent_element:
                        safe_click(driver, parent_element, 'click')
                    else:
                        safe_click(driver, select_element, 'click')
                except:
                    safe_click(driver, select_element, 'click')

                time.sleep(0.8)

                opcoes = None
                max_tentativas_opcoes = 2
                for tentativa_opcoes in range(max_tentativas_opcoes):
                    try:
                        opcoes = WebDriverWait(driver, 3.0).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, "mat-option[role='option']")
                            )
                        )
                        if opcoes and len(opcoes) > 0:
                            break
                        else:
                            if tentativa_opcoes < max_tentativas_opcoes - 1:
                                time.sleep(1.5)
                    except Exception:
                        if tentativa_opcoes < max_tentativas_opcoes - 1:
                            time.sleep(1.5)
                        else:
                            continue

                if not opcoes or len(opcoes) == 0:
                    try:
                        driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
                    except:
                        continue
                    time.sleep(0.3)
                    continue

                opcao_encontrada = False
                for opc_idx, opcao in enumerate(opcoes):
                    try:
                        texto_opcao = opcao.text.strip()

                        if (
                            tipo_fluxo == 'POSITIVO'
                            and valor_parcial is not None
                            and 'remanescente' in texto_opcao.lower()
                        ):
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.5)
                            try:
                                campo_valor = WebDriverWait(driver, 2).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR,
                                         "input[placeholder='Valor'][prefix='R$ ']")
                                    )
                                )
                                campo_valor.clear()
                                valor_formatado = f"{valor_parcial:.2f}".replace('.', ',')
                                campo_valor.send_keys(valor_formatado)
                                return True
                            except Exception as e_valor:
                                if log:
                                    logger.error(
                                        f"[_aplicar_acao] Erro ao preencher valor parcial: "
                                        f"{e_valor}"
                                    )
                                return False

                        elif tipo_fluxo == 'POSITIVO' and texto_opcao == 'Transferir valor':
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.3)
                            return True

                        elif (
                            tipo_fluxo == 'DESBLOQUEIO'
                            and 'Desbloquear valor' in texto_opcao
                        ):
                            safe_click(driver, opcao, 'click')
                            time.sleep(0.3)
                            return True

                    except Exception as e_opcao:
                        if log:
                            logger.error(
                                f"[_aplicar_acao] Erro ao processar opcao "
                                f"{opc_idx + 1}: {e_opcao}"
                            )
                        continue

                try:
                    driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
                    time.sleep(0.3)
                except:
                    continue

            except Exception as e_dropdown:
                if log:
                    logger.error(
                        f"[_aplicar_acao] Erro ao processar dropdown #{idx + 1}: "
                        f"{e_dropdown}"
                    )
                try:
                    driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
                except:
                    continue
                time.sleep(0.3)
                continue

        return False

    except Exception as e:
        if log:
            logger.error(f"[_aplicar_acao] Erro critico: {e}")
            import traceback
            logger.exception("Erro detectado")
        return False


def _identificar_ordens_com_bloqueio(ordens, valor_total_bloqueado_serie=None, log=True):
    """
    Identifica ordens que geraram bloqueio usando logica de diferenca de valores.

    Args:
        ordens: Lista de ordens da serie
        valor_total_bloqueado_serie: Valor total bloqueado da serie (fallback)
        log: Se deve fazer log

    Returns:
        list: Lista de ordens que tem bloqueio
    """
    bloqueios = []

    if not ordens:
        return bloqueios

    # 1. Detectar bloqueios pela diferenca de valor entre ordens consecutivas
    for i in range(len(ordens) - 1):
        valor_atual = ordens[i]["valor_bloquear"]
        valor_posterior = ordens[i + 1]["valor_bloquear"]

        if valor_atual > valor_posterior:
            ordem_com_bloqueio = ordens[i].copy()
            valor_bloqueio = valor_atual - valor_posterior
            ordem_com_bloqueio['valor_bloqueio_esperado'] = valor_bloqueio
            ordem_com_bloqueio['_relatorio'] = {
                'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
                'valor_esperado': valor_bloqueio,
                'status': 'pendente',
                'discriminacao': None,
            }
            bloqueios.append(ordem_com_bloqueio)

    # 2. Verificar ultima ordem usando diferenca de valores
    if len(ordens) > 0:
        ultima_ordem = ordens[-1]
        valor_original_a_bloquear = ordens[0]["valor_bloquear"] if ordens else 0
        valor_efetivamente_bloqueado = valor_total_bloqueado_serie or 0
        valor_ultima_ordem = ultima_ordem["valor_bloquear"]
        diferenca_esperada = valor_original_a_bloquear - valor_efetivamente_bloqueado
        diferenca_absoluta = abs(diferenca_esperada - valor_ultima_ordem)

        if diferenca_absoluta > 0.01:
            if ultima_ordem not in bloqueios:
                ordem_com_bloqueio = ultima_ordem.copy()
                ordem_com_bloqueio['valor_bloqueio_esperado'] = diferenca_esperada
                ordem_com_bloqueio['_relatorio'] = {
                    'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
                    'valor_esperado': diferenca_esperada,
                    'status': 'pendente',
                    'discriminacao': None,
                }
                bloqueios.append(ordem_com_bloqueio)

    # 3. FALLBACK: Se serie tem valor bloqueado mas nenhum bloqueio foi detectado
    if (
        valor_total_bloqueado_serie
        and valor_total_bloqueado_serie > 0
        and len(bloqueios) == 0
        and len(ordens) > 0
    ):
        ultima_ordem = ordens[-1]
        ordem_com_bloqueio = ultima_ordem.copy()
        ordem_com_bloqueio['valor_bloqueio_esperado'] = valor_total_bloqueado_serie
        ordem_com_bloqueio['_relatorio'] = {
            'protocolo': ordem_com_bloqueio.get('protocolo', 'N/A'),
            'valor_esperado': valor_total_bloqueado_serie,
            'status': 'pendente',
            'discriminacao': None,
        }
        bloqueios.append(ordem_com_bloqueio)

    return bloqueios


# =============================================================================
# NAVEGACAO
# =============================================================================


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
        url_atual = driver.current_url.lower()
        if "/desdobrar" not in url_atual:
            if "/detalhes" in url_atual:
                return True
            return False

        time.sleep(1)

        seletores_voltar = [
            "button[aria-label='Voltar'] i.fa-chevron-left",
            "button i.fa-chevron-left",
            ".fa-chevron-left",
            "i.fa-chevron-left",
            "button.btn-voltar",
            "[aria-label='Voltar']",
            "button[title='Voltar']",
        ]

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
            try:
                js_script = """
                var botoes = document.querySelectorAll('button, a, .btn');
                for (var i = 0; i < botoes.length; i++) {
                    var botao = botoes[i];
                    var chevron = botao.querySelector(
                        'i.fa-chevron-left, .fa-chevron-left'
                    );
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

        for _i in range(10):
            time.sleep(0.5)
            if "/desdobrar" not in driver.current_url:
                break

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
            )
            time.sleep(1.5)
        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD] Erro ao aguardar tabela: {e}")
        return True

    except Exception as e:
        if log:
            logger.error(
                f"[SISBAJUD] Erro ao voltar para lista de ordens da serie: {str(e)}"
            )
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
        try:
            overlays = driver.find_elements(
                By.CSS_SELECTOR,
                'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop'
                '.cdk-overlay-backdrop-showing',
            )
            if overlays:
                for overlay in overlays:
                    try:
                        overlay.click()
                        time.sleep(0.5)
                    except Exception:
                        try:
                            driver.execute_script(
                                "arguments[0].style.display = 'none';", overlay
                            )
                        except Exception:
                            pass
                time.sleep(1.0)
        except Exception:
            pass

        url_atual = driver.current_url

        if "/detalhes" in url_atual:
            numero_processo = None
            if "numeroProcesso=" in url_atual:
                numero_processo = url_atual.split("numeroProcesso=")[1].split("&")[0]
            elif hasattr(driver, '_numero_processo_atual'):
                numero_processo = driver._numero_processo_atual

            if numero_processo:
                url_volta = (
                    "https://sisbajud.cnj.jus.br/teimosinha"
                    f"?numeroProcesso={numero_processo}"
                )
            else:
                url_volta = "https://sisbajud.cnj.jus.br/teimosinha"

            driver.get(url_volta)
            time.sleep(3)
            return True

        for _clique in range(2):
            seletores_voltar = [
                'button.mat-icon-button .fa-chevron-left',
                'button[mat-icon-button] .fas.fa-chevron-left',
                'button .mat-icon.fa-chevron-left',
                'button i.fa-chevron-left',
                '.fa-chevron-left',
            ]

            botao_voltar_clicado = False
            for seletor in seletores_voltar:
                try:
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                    except Exception:
                        pass

                    botao_icon = driver.find_element(By.CSS_SELECTOR, seletor)
                    try:
                        botao = botao_icon.find_element(
                            By.XPATH, './ancestor::button[1]'
                        )
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
        else:
            return False

    except Exception as e:
        if log:
            logger.error(
                f"[SISBAJUD] Erro ao voltar para lista principal: {e}"
            )
        return False


# =============================================================================
# ALL
# =============================================================================

__all__ = [
    '_carregar_dados_ordem',
    '_extrair_ordens_da_serie',
    '_aplicar_acao_por_fluxo',
    '_identificar_ordens_com_bloqueio',
    '_voltar_para_lista_ordens_serie',
    '_voltar_para_lista_principal',
]
