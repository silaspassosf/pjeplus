import logging
logger = logging.getLogger(__name__)

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from Fix.extracao import extrair_dados_processo


CALENDARIO_DIAS_UTEIS_PATH = Path('dias-uteis-trt2-2025.json')
_CALENDARIO_DIAS_UTEIS = None
_CALENDARIO_INTERVALO = None


def _carregar_calendario_dias_uteis():
    global _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO
    if _CALENDARIO_DIAS_UTEIS is not None:
        return _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO

    dias_calendario = set()
    intervalo = None

    if CALENDARIO_DIAS_UTEIS_PATH.exists():
        try:
            with open(CALENDARIO_DIAS_UTEIS_PATH, 'r', encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
            for entrada in conteudo.get('dias_uteis', []):
                try:
                    data_convertida = datetime.fromisoformat(entrada).date()
                    dias_calendario.add(data_convertida)
                except ValueError:
                    continue
            if dias_calendario:
                intervalo = (min(dias_calendario), max(dias_calendario))
        except Exception:
            dias_calendario = set()
            intervalo = None

    _CALENDARIO_DIAS_UTEIS = dias_calendario
    _CALENDARIO_INTERVALO = intervalo
    return _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO


def _somar_dias_uteis(data_base, quantidade):
    if not data_base or quantidade <= 0:
        return data_base

    dias_calendario, intervalo = _carregar_calendario_dias_uteis()
    data_atual = data_base
    acumulado = 0
    seguranca = 0

    while acumulado < quantidade and seguranca < 1000:
        data_atual += timedelta(days=1)
        seguranca += 1
        dentro_intervalo = intervalo and intervalo[0] <= data_atual <= intervalo[1]

        if dias_calendario and dentro_intervalo:
            if data_atual in dias_calendario:
                acumulado += 1
        else:
            if data_atual.weekday() < 5:
                acumulado += 1

    if acumulado < quantidade:
        return None

    return data_atual


def _parse_data_ecarta(valor):
    if not valor:
        return None

    valor_limpo = valor.strip()
    if not valor_limpo:
        return None

    parte_data = re.split(r'[\sT]', valor_limpo)[0]
    formatos = ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d')

    for fmt in formatos:
        try:
            return datetime.strptime(parte_data, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(parte_data).date()
    except ValueError:
        return None


def _obter_numero_processo(driver, log):
    process_number = None
    try:
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception:
        pass
    try:
        p = Path('dadosatuais.json')
        if p.exists():
            j = json.loads(p.read_text(encoding='utf-8'))
            maybe = j.get('numero') if isinstance(j, dict) else None
            if isinstance(maybe, (list, tuple)) and len(maybe) > 0:
                process_number = maybe[0]
            elif isinstance(maybe, str):
                process_number = maybe
    except Exception as e:
        if log:
            logger.error(f"[CARTA][DADOSATUAIS] Erro ao ler dadosatuais.json: {e}")

    return process_number
