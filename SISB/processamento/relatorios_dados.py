"""SISB Relatórios — extração e agrupamento de dados de bloqueios processados."""

import logging
import re

from Fix import espera

logger = logging.getLogger(__name__)


def _agrupar_dados_bloqueios(dados_acumulados, dados_novos, log=True):
    """Agrupa dados de bloqueios novos nos dados acumulados."""
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
                bancos_novos = dados_exec.get('bancos_001', [])
                if bancos_novos:
                    exec_acum['bancos_001'] = list(set(exec_acum.get('bancos_001', []) + bancos_novos))
            else:
                dados_acumulados['executados'][chave_executado] = {
                    'nome': dados_exec.get('nome', 'Executado'),
                    'documento': dados_exec.get('documento', ''),
                    'protocolos': list(dados_exec.get('protocolos', [])),
                    'total': float(dados_exec.get('total', 0.0)),
                    'bancos_001': list(set(dados_exec.get('bancos_001', []))),
                }
            dados_acumulados['total_geral'] += dados_exec.get('total', 0.0)
    except Exception as e:
        if log:
            logger.error("[SISBAJUD] Erro ao agrupar dados: %s", e)


def extrair_dados_bloqueios_processados(driver, log=True, protocolo_ordem=None):
    """Extrai dados dos bloqueios processados agrupados por executado."""
    sel_header = 'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
    dados_bloqueios = {'executados': {}, 'total_geral': 0.0}
    try:
        espera.ate_aparecer(driver, sel_header, teto=3)
        espera.assentar(driver, 0.5)
        numero_protocolo = protocolo_ordem or "N/A"
        headers = espera.elementos(driver, sel_header, teto=1)
        if not headers:
            return dados_bloqueios

        for idx, header in enumerate(headers, 1):
            try:
                el_nome = espera.elemento(header, '.col-reu-dados-nome-pessoa', teto=0.2)
                nome_executado = el_nome.text.strip() if el_nome else "Executado nao identificado"
                el_doc = espera.elemento(header, '.col-reu-dados a', teto=0.2)
                documento_executado = el_doc.text.strip() if el_doc else ""

                valor_float = 0.0
                el_val = espera.elemento(header, '.div-description-reu span', teto=0.2)
                if el_val:
                    m = re.search(r'R\$\s*([0-9.,]+)', el_val.text.strip())
                    if m:
                        valor_float = float(m.group(1).replace('.', '').replace(',', '.'))
                if valor_float <= 0:
                    continue

                bancos_001 = []
                for banco_panel in espera.elementos(header, '..//mat-expansion-panel[.//div[contains(@class, "div-title-instituicao")]]', teto=0.2):
                    try:
                        el_nb = espera.elemento(banco_panel, '.div-title-instituicao .col-reu-dados-nome-pessoa', teto=0.1)
                        el_sd = espera.elemento(banco_panel, 'td.cdk-column-saldoRemanescente', teto=0.1)
                        if el_nb and el_sd and '0,01' in el_sd.text:
                            bancos_001.append(el_nb.text.strip())
                    except Exception:
                        continue

                chave = f"{nome_executado}|{documento_executado}"
                alvo = dados_bloqueios['executados'].setdefault(chave, {
                    'nome': nome_executado,
                    'documento': documento_executado,
                    'protocolos': [],
                    'total': 0.0,
                    'bancos_001': [],
                })
                if bancos_001:
                    alvo['bancos_001'] = list(set(alvo['bancos_001'] + bancos_001))
                valor_fmt = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                alvo['protocolos'].append({
                    'numero': numero_protocolo,
                    'valor': valor_float,
                    'valor_formatado': valor_fmt,
                    'erro_bloqueio': None,
                })
                alvo['total'] += valor_float
                dados_bloqueios['total_geral'] += valor_float
            except Exception as e:
                if log:
                    logger.error("[SISBAJUD] Erro ao processar header %s: %s", idx, e)
        return dados_bloqueios
    except Exception:
        return {'executados': {}, 'total_geral': 0.0}
