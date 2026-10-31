# -*- coding: utf-8 -*-
"""
bianca/triagem/citacao.py -- Analise de citacao (polo passivo e domicilio eletronico).

Funcoes:
    def_citacao(driver, processo_info)  Analisa polo passivo e define tipo de citacao.
"""

import re
from datetime import date, datetime
from typing import Dict, Any, Optional

from Fix import espera
from Fix.browser_suporte import _sub_elemento
from Fix.variaveis import PjeApiClient, session_from_driver

_FALHA_CITACAO = {
    'gigs_obs': [],
    'pec_wrappers': [],
    'com_domicilio': 0,
    'sem_domicilio': 0,
    'total': 0,
    'sucesso': False,
}


def _parse_data(val: Any) -> Optional[date]:
    """Converte valor de data em objeto date."""
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    if not isinstance(val, str):
        return None
    val = val.strip()
    if not val:
        return None
    # 1. ISO (ex: 2026-11-03T...)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', val)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # 2. DD/MM/AAAA
    m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', val)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


def _dia_semana_audiencia(driver: Any = None, processo_info: Optional[Dict] = None) -> Optional[int]:
    """Retorna o dia da semana da audiencia (0=segunda ... 4=sexta), ou None."""
    # 1. Checa processo_info
    if processo_info:
        for chave in ('data_audiencia', 'dataProximaAudiencia', 'data_proxima_audiencia'):
            d = _parse_data(processo_info.get(chave))
            if d:
                return d.weekday()

    # 2. Fallback: inspeciona dt#audiencias no DOM
    try:
        dt = espera.elemento(driver, "dt#audiencias", teto=1)
        if dt:
            texto = ""
            try:
                parent = _sub_elemento(dt, "./ancestor::*[1]")
                texto = (((getattr(parent, 'text_content', None) and parent.text_content()) or getattr(parent, 'text', '') or '')).strip()
            except Exception:
                pass
            if not texto:
                texto = (((getattr(dt, 'text_content', None) and dt.text_content()) or getattr(dt, 'text', '') or '')).strip()
            if texto:
                d = _parse_data(texto)
                if d:
                    return d.weekday()
    except Exception:
        pass

    return None


def def_citacao(driver: Any, processo_info: Dict) -> Dict:
    """Analisa polo passivo e define tipo de citacao (ord/sum vs ordc/sumc).

    Args:
        driver: Driver na pagina do processo.
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
        nome_p = parte.get('nome', '').strip()
        dom_flag_raw = parte.get('domicilioEletronico') or parte.get('possuiDomicilioEletronico')
        if dom_flag_raw is True:
            print(f"[TRIAGEM/CITACAO] Parte '{nome_p}': dom. eletronico detectado via flag inline")
            com_dom += 1
            continue

        id_parte = str(
            parte.get('id') or parte.get('idParte') or
            parte.get('idParticipante') or ''
        )
        id_pessoa = str(parte.get('idPessoa') or '')

        dom_flag = None
        if id_parte:
            dom_flag = client.domicilio_eletronico(id_parte)
        if dom_flag is not True and id_pessoa and id_pessoa != id_parte:
            dom_flag_pessoa = client.domicilio_eletronico(id_pessoa)
            if dom_flag_pessoa is not None:
                dom_flag = dom_flag_pessoa

        if dom_flag is True:
            print(f"[TRIAGEM/CITACAO] Parte '{nome_p}' (idParte={id_parte}, idPessoa={id_pessoa}): dom. eletronico HABILITADO")
            com_dom += 1
        else:
            print(f"[TRIAGEM/CITACAO] Parte '{nome_p}' (idParte={id_parte}, idPessoa={id_pessoa}): dom. eletronico NAO habilitado ({dom_flag})")
            sem_dom += 1

    dia_sem = _dia_semana_audiencia(driver, processo_info)
    # Grupo segunda (0), terca (1) e sexta (4): acrescenta 'v' nos GIGS
    is_seg_ter_sex = dia_sem in (0, 1, 4)

    if is_seg_ter_sex:
        if com_dom >= 1:
            if base == 'ord':
                gigs_obs = ['xs ordv']
            else:
                gigs_obs = ['xs sumv']
            pec_list = ['pec_%s' % base]
        else:
            if base == 'ord':
                gigs_obs = ['xs ordcv']
            else:
                gigs_obs = ['xs sumcv']
            pec_list = ['pec_%sc' % base]
    else:
        if com_dom >= 1:
            if base == 'ord':
                gigs_obs = ['xs ord']
            else:
                gigs_obs = ['xs sum']
            pec_list = ['pec_%s' % base]
        else:
            if base == 'ord':
                gigs_obs = ['xs ordc']
            else:
                gigs_obs = ['xs sumc']
            pec_list = ['pec_%sc' % base]

    _dias_nomes = {0: 'segunda-feira', 1: 'terça-feira', 2: 'quarta-feira', 3: 'quinta-feira', 4: 'sexta-feira', 5: 'sábado', 6: 'domingo'}
    dia_desc = _dias_nomes.get(dia_sem, f'indefinido ({dia_sem})')
    print(f"[TRIAGEM/CITACAO] Resultado: com_dom={com_dom}, sem_dom={sem_dom}, total={total}, dia_aud={dia_desc}, gigs={gigs_obs}, pec={pec_list}")

    return {
        'gigs_obs': gigs_obs,
        'pec_wrappers': pec_list,
        'com_domicilio': com_dom,
        'sem_domicilio': sem_dom,
        'total': total,
        'sucesso': True,
    }
