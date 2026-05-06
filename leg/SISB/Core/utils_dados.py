import logging
import os
import json
import re
from datetime import datetime, timedelta

from Fix.utils import formatar_moeda_brasileira
from Fix.log import _log_info, _log_error

logger = logging.getLogger(__name__)

"""
SISB Core - Dados e logging
"""


def extrair_protocolo(driver):
    """Extrair protocolo da URL atual."""
    try:
        url = driver.current_url
        match = re.search(r'/(\d{10,})/', url)
        return match.group(1) if match else None
    except Exception as e:
        logger.error(f"[SISBAJUD] Erro ao extrair protocolo: {e}")
        return None


def validar_numero_processo(numero):
    """Validar formato do numero do processo."""
    if isinstance(numero, list) and len(numero) > 0:
        numero = numero[0]
    elif not isinstance(numero, str) or not numero.strip():
        return None

    numero = numero.strip()
    if not re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', numero):
        return None

    return numero


def formatar_valor_monetario(valor_str):
    """Formatar valor monetario brasileiro para float."""
    try:
        valor_formatado = formatar_moeda_brasileira(valor_str)
        if isinstance(valor_formatado, str) and 'R$' in valor_formatado:
            valor_limpo = valor_formatado.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return float(valor_limpo)
        return 0.0
    except Exception:
        return 0.0


def calcular_data_limite(dias_atras=15):
    """Calcular data limite para filtros (hoje - dias_atras)."""
    return datetime.now() - timedelta(days=dias_atras)


def criar_timestamp():
    """Criar timestamp formatado para logging."""
    return datetime.now().strftime("[%H:%M:%S]")


def log_sisbajud(mensagem, nivel="INFO"):
    """Logging padronizado para SISBAJUD."""
    timestamp = criar_timestamp()
    msg_com_timestamp = f"[SISBAJUD]{timestamp} [{nivel}] {mensagem}"

    if nivel.upper() == "ERROR":
        _log_error(msg_com_timestamp)
    else:
        _log_info(msg_com_timestamp)


def registrar_erro_minuta(numero_processo, erro, contexto, continuar=False):
    """Registrar erro de minuta de forma padronizada."""
    mensagem = f"Erro em {contexto}: {str(erro)}"
    log_sisbajud(mensagem, "ERROR")

    if not continuar:
        log_sisbajud(f"Interrompendo processamento do processo {numero_processo}", "ERROR")
        raise erro


def carregar_dados_processo():
    """Carrega os dados do processo do arquivo dadosatuais.json no projeto."""
    try:
        project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dados_path = os.path.join(project_path, 'dadosatuais.json')

        if not os.path.exists(dados_path):
            return None

        with open(dados_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        return dados
    except Exception as e:
        logger.error(f'[SISBAJUD][ERRO] Falha ao carregar dados do processo: {e}')
        return None