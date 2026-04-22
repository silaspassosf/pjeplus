import logging
import re
import time as time_module

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

"""
SISB Relatorios - Dados de bloqueios
"""


def _agrupar_dados_bloqueios(dados_acumulados, dados_novos, log=True):
    """
    Agrupa dados de bloqueios novos nos dados acumulados.
    Merge por executado (chave = nome|documento).

    Args:
        dados_acumulados: Dict existente {'executados': {...}, 'total_geral': float}
        dados_novos: Dict com novos dados {'executados': {...}, 'total_geral': float}
        log: Se deve fazer log

    Returns:
        None (modifica dados_acumulados in-place)
    """
    try:
        if not dados_novos or not dados_novos.get('executados'):
            return

        for chave_executado, dados_exec in dados_novos['executados'].items():
            if chave_executado in dados_acumulados['executados']:
                exec_acum = dados_acumulados['executados'][chave_executado]

                protocolos_novos = dados_exec.get('protocolos', [])
                if not isinstance(protocolos_novos, list):
                    protocolos_novos = [protocolos_novos] if protocolos_novos else []

                if not isinstance(exec_acum['protocolos'], list):
                    exec_acum['protocolos'] = [exec_acum['protocolos']] if exec_acum['protocolos'] else []

                exec_acum['protocolos'].extend(protocolos_novos)
                exec_acum['total'] += dados_exec.get('total', 0.0)
            else:
                dados_acumulados['executados'][chave_executado] = {
                    'nome': dados_exec.get('nome', 'Executado'),
                    'documento': dados_exec.get('documento', ''),
                    'protocolos': list(dados_exec.get('protocolos', [])),
                    'total': float(dados_exec.get('total', 0.0))
                }

            dados_acumulados['total_geral'] += dados_exec.get('total', 0.0)

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao agrupar dados: {e}")


def extrair_dados_bloqueios_processados(driver, log=True, protocolo_ordem=None):
    """
    Extrai dados dos bloqueios processados agrupados por executado.
    Le diretamente dos headers mat-expansion-panel-header na pagina do SISBAJUD.

    Args:
        driver: WebDriver do SISBAJUD
        log: Se deve fazer log
        protocolo_ordem: Numero do protocolo da ordem (extraido da lista de ordens)

    Returns:
        dict: {'executados': {chave: {nome, documento, protocolos, total}}, 'total_geral': float}
    """
    try:
        # Aguardar headers de executados aparecerem (ate 3s)
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
                ))
            )
        except Exception:
            pass

        time_module.sleep(0.5)

        dados_bloqueios = {
            'executados': {},
            'total_geral': 0.0
        }

        numero_protocolo = protocolo_ordem if protocolo_ordem else "N/A"

        try:
            headers_executados = driver.find_elements(
                By.CSS_SELECTOR,
                'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
            )

            if not headers_executados:
                return dados_bloqueios

            for idx, header in enumerate(headers_executados, 1):
                try:
                    nome_executado = "Executado nao identificado"
                    try:
                        nome_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados-nome-pessoa')
                        nome_executado = nome_element.text.strip()
                    except Exception:
                        pass

                    documento_executado = ""
                    try:
                        documento_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados a')
                        documento_executado = documento_element.text.strip()
                    except Exception:
                        pass

                    valor_float = 0.0
                    try:
                        valor_element = header.find_element(By.CSS_SELECTOR, '.div-description-reu span')
                        valor_text = valor_element.text.strip()

                        valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                        if valor_match:
                            valor_str = valor_match.group(1)
                            valor_float = float(valor_str.replace('.', '').replace(',', '.'))
                    except Exception:
                        pass

                    if valor_float <= 0:
                        continue

                    chave_executado = f"{nome_executado}|{documento_executado}"

                    if chave_executado not in dados_bloqueios['executados']:
                        dados_bloqueios['executados'][chave_executado] = {
                            'nome': nome_executado,
                            'documento': documento_executado,
                            'protocolos': [],
                            'total': 0.0
                        }

                    valor_formatado = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    dados_bloqueios['executados'][chave_executado]['protocolos'].append({
                        'numero': numero_protocolo,
                        'valor': valor_float,
                        'valor_formatado': valor_formatado,
                        'erro_bloqueio': None
                    })

                    dados_bloqueios['executados'][chave_executado]['total'] += valor_float
                    dados_bloqueios['total_geral'] += valor_float

                except Exception as e:
                    if log:
                        logger.error(f"[SISBAJUD]  Erro ao processar header {idx}: {e}")
                    continue

            return dados_bloqueios

        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD]  Erro ao buscar headers: {e}")
            return dados_bloqueios

    except Exception:
        return {'executados': {}, 'total_geral': 0.0}