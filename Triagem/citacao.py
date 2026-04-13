"""Triagem/citacao.py
Cálculo de citação e GIGS para Triagem Inicial.
"""
import re
from typing import Dict
from selenium.webdriver.remote.webdriver import WebDriver
from api.variaveis import PjeApiClient, session_from_driver

_FALHA_CITACAO = {
    'gigs_obs': [],
    'pec_wrappers': [],
    'com_domicilio': 0,
    'sem_domicilio': 0,
    'total': 0,
    'sucesso': False,
}


def def_citacao(driver: WebDriver, processo_info: Dict) -> Dict:
    tipo = (processo_info.get('tipo') or '').upper().strip()
    base = 'sum' if tipo == 'ATSUM' else 'ord'

    try:
        sessao, trt_host = session_from_driver(driver, grau=1)
        client = PjeApiClient(sessao, trt_host, grau=1)
    except Exception as e:
        print(f"[TRIAGEM/CITACAO] ERRO cliente API: {e}")
        return _FALHA_CITACAO

    m = re.search(r'/processo/(\d+)(?:/|$)', driver.current_url)
    if not m:
        print("[TRIAGEM/CITACAO] ERRO: ID nao encontrado na URL")
        return _FALHA_CITACAO
    id_processo = m.group(1)

    try:
        partes_raw = client.partes(id_processo) or {}
    except Exception as e:
        print(f"[TRIAGEM/CITACAO] ERRO partes: {e}")
        return _FALHA_CITACAO

    passivos = partes_raw.get('PASSIVO') or []
    total = len(passivos)
    if total == 0:
        print("[TRIAGEM/CITACAO] POLO PASSIVO VAZIO — abortando.")
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

    # Regra unica: se ao menos um passivo tem domicilio eletronico → ord/sum
    # Se nenhum tem → ordc/sumc
    if com_dom >= 1:
        gigs_obs = [f'xs {base}']
        pec_list = [f'pec_{base}']
    else:
        gigs_obs = [f'xs {base}c']
        pec_list = [f'pec_{base}c']

    return {
        'gigs_obs': gigs_obs,
        'pec_wrappers': pec_list,
        'com_domicilio': com_dom,
        'sem_domicilio': sem_dom,
        'total': total,
        'sucesso': True,
    }


__all__ = ['def_citacao', '_FALHA_CITACAO']
