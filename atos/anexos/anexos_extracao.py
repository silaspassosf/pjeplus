import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def extrair_numero_processo_da_url(driver: Any) -> str:
    try:
        url_atual = getattr(driver, 'current_url', '') or ''
        padroes = [
            r'processo/(\d+)',
            r'processoTrfId=(\d+)',
            r'numeroProcesso=(\d+)',
            r'idProcesso=(\d+)',
        ]
        for padrao in padroes:
            match = re.search(padrao, url_atual)
            if match:
                return match.group(1)
        if 'pje' in url_atual.lower():
            partes = url_atual.split('/')
            for parte in partes:
                if parte.isdigit() and len(parte) > 6:
                    return parte
        return f"URL_{hash(url_atual) % 10000}"
    except Exception as e:
        return f"ERRO_{str(e)[:20]}"

