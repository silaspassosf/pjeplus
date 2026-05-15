# -*- coding: utf-8 -*-
"""
bianca/triagem/citacao.py -- Analise de citacao (polo passivo e domicilio eletronico).

Funcoes:
    def_citacao(driver, processo_info)  Analisa polo passivo e define tipo de citacao.
"""

import re
from typing import Dict

from selenium.webdriver.remote.webdriver import WebDriver

from bianca.api_client import PjeApiClient, session_from_driver

_FALHA_CITACAO = {
    'gigs_obs': [],
    'pec_wrappers': [],
    'com_domicilio': 0,
    'sem_domicilio': 0,
    'total': 0,
    'sucesso': False,
}


def def_citacao(driver: WebDriver, processo_info: Dict) -> Dict:
    """Analisa polo passivo e define tipo de citacao (ord/sum vs ordc/sumc).

    Args:
        driver: WebDriver na pagina do processo.
        processo_info: Dict com metadados do processo ('tipo').

    Returns:
        Dict com:
            gigs_obs (list[str])  -- observacoes GIGS de citacao.
            pec_wrappers (list[str]) -- wrappers PEC para acao pos-triagem.
            com_domicilio (int)   -- total de reclamados com dom. eletronico.
            sem_domicilio (int)   -- total de reclamados sem dom. eletronico.
            total (int)           -- total de reclamados.
            sucesso (bool)        -- True se analise concluida.
    """
    tipo = (processo_info.get('tipo') or '').upper().strip()
    base = 'sum' if tipo == 'ATSUM' else 'ord'

    try:
        sessao, trt_host = session_from_driver(driver, grau=1)
        client = PjeApiClient(sessao, trt_host, grau=1)
    except Exception as e:
        print(f"[TRIAGEM/CITACAO] ❌ Erro cliente API: {e}")
        return _FALHA_CITACAO

    m = re.search(r'/processo/(\d+)(?:/|$)', driver.current_url)
    if not m:
        print(f"[TRIAGEM/CITACAO] ❌ ID nao encontrado na URL")
        return _FALHA_CITACAO
    id_processo = m.group(1)

    try:
        partes_raw = client.partes(id_processo) or {}
    except Exception as e:
        print(f"[TRIAGEM/CITACAO] ❌ Erro partes: {e}")
        return _FALHA_CITACAO

    passivos = partes_raw.get('PASSIVO') or []
    total = len(passivos)
    if total == 0:
        print(f"[TRIAGEM/CITACAO] 🛑 Polo passivo vazio -- abortando.")
        return _FALHA_CITACAO

    com_dom = 0
    sem_dom = 0

    for parte in passivos:
        id_parte = str(
            parte.get('idPessoa') or parte.get('id') or
            parte.get('idParticipante') or parte.get('idParte') or ''
        )
        dom_flag = None
        if id_parte:
            dom_flag = client.domicilio_eletronico(id_parte)
        if dom_flag is True:
            com_dom += 1
        else:
            sem_dom += 1

    if com_dom >= 1:
        if base == 'ord':
            gigs_obs = ['c.Ord']
        else:
            gigs_obs = ['c.Sum']
        pec_list = ['pec_%s' % base]
    else:
        if base == 'ord':
            gigs_obs = ['c.Ord.AR']
        else:
            gigs_obs = ['c.Sum.AR']
        pec_list = ['pec_%sc' % base]

    print(f"[TRIAGEM/CITACAO] Resultado: com_dom={com_dom}, sem_dom={sem_dom}, total={total}, gigs={gigs_obs}, pec={pec_list}")

    return {
        'gigs_obs': gigs_obs,
        'pec_wrappers': pec_list,
        'com_domicilio': com_dom,
        'sem_domicilio': sem_dom,
        'total': total,
        'sucesso': True,
    }
