"""SISB/api_series.py — leitura das séries da Teimosinha por API."""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

URL_API = 'https://sisbajud.pdpj.jus.br/v1/serie'
TIPO_SITUACAO_ATIVA = 1
TIPO_SITUACAO_ENCERRADA = 2
TIPOS_SITUACAO_VALIDOS = (TIPO_SITUACAO_ATIVA, TIPO_SITUACAO_ENCERRADA)

_MESES = {
    1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL', 5: 'MAIO', 6: 'JUNHO',
    7: 'JULHO', 8: 'AGOSTO', 9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO',
}


def _data_texto(ms):
    """epoch ms -> '10 DE SETEMBRO DE 2026' (mesmo formato que o DOM entrega)."""
    if not ms:
        return ''
    d = datetime.fromtimestamp(ms / 1000.0)
    return '%d DE %s DE %d' % (d.day, _MESES[d.month], d.year)


def _valor_texto(valor):
    """12345.67 -> 'R$ 12.345,67' (mesmo formato que o DOM entrega)."""
    try:
        return 'R$ %s' % format(float(valor), ',.2f').replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return 'R$ 0,00'


def _http_get(url, headers, timeout):
    """GET simples. Isolado para poder ser injetado em teste."""
    import requests
    resp = requests.get(url, headers=headers, timeout=timeout)
    return resp.status_code, resp.text


def ler_series_api(numero_processo, data_limite=None, timeout=20,
                   token=None, http_get=None, log=True):
    """Lê as séries da Teimosinha por API e devolve o mesmo contrato de `_filtrar_series`."""
    digitos = ''.join(ch for ch in str(numero_processo or '') if ch.isdigit())
    if len(digitos) < 15:
        if log:
            logger.info('[SISBAJUD][API] Número inválido: %r', numero_processo)
        return None

    if token is None:
        try:
            from SISB.core import carregar_tokens_sisbajud
            info = carregar_tokens_sisbajud()
            if not info.get('sucesso'):
                if log:
                    logger.info('[SISBAJUD][API] Sem token válido — usando caminho DOM')
                return None
            token = info.get('access_token')
        except Exception as e:
            if log:
                logger.info('[SISBAJUD][API] Falha ao carregar token (%s) — usando caminho DOM', e)
            return None

    if not token:
        return None

    url = '%s?codProcesso=%s' % (URL_API, digitos)
    headers = {'Accept': 'application/json', 'Authorization': 'Bearer %s' % token}
    getter = http_get or _http_get

    try:
        status, texto = getter(url, headers, timeout)
    except Exception as e:
        if log:
            logger.info('[SISBAJUD][API] Erro na chamada (%s) — usando caminho DOM', e)
        return None

    if status != 200:
        if log:
            logger.info('[SISBAJUD][API] HTTP %s — usando caminho DOM', status)
        return None

    try:
        import json
        bruto = json.loads(texto)
    except Exception as e:
        if log:
            logger.info('[SISBAJUD][API] Corpo não-JSON (%s) — usando caminho DOM', e)
        return None

    if not isinstance(bruto, list):
        if log:
            logger.info('[SISBAJUD][API] Corpo inesperado (%s) — usando caminho DOM', type(bruto).__name__)
        return None

    if log:
        logger.info('[SISBAJUD][API] %d série(s) recebida(s) para %s', len(bruto), digitos)

    validas = []
    for serie in bruto:
        try:
            tipo_situacao = serie.get('tipoSituacaoSerie')
            if tipo_situacao not in TIPOS_SITUACAO_VALIDOS:
                continue

            fim_ms = serie.get('dataLimite')
            if not fim_ms and tipo_situacao == TIPO_SITUACAO_ENCERRADA:
                continue

            data_fim = datetime.fromtimestamp(fim_ms / 1000.0) if fim_ms else None
            if data_fim is not None and isinstance(data_limite, datetime) and data_fim < data_limite:
                continue

            ordem = serie.get('ordemOriginal') or {}
            valor_bloqueado = float(serie.get('valorBloqueioRealizado') or 0)
            valor_bloquear = float(serie.get('valorBloqueioTotal') or 0)

            validas.append({
                'id_serie': str(serie.get('codSerie')),
                'protocolo': str(ordem.get('protocolo') or ''),
                'acao': str(ordem.get('descricaoTipoOrdem') or ''),
                'data_conclusao': data_fim,
                'data_conclusao_text': _data_texto(fim_ms),
                'situacao': 'Ativa' if tipo_situacao == TIPO_SITUACAO_ATIVA else 'Encerrada',
                'valor_bloqueado': valor_bloqueado,
                'valor_bloquear': valor_bloquear,
                'valor_bloqueado_text': _valor_texto(valor_bloqueado),
                'valor_bloquear_text': _valor_texto(valor_bloquear),
                'linha_index': None,
            })
        except Exception as e:
            if log:
                logger.info('[SISBAJUD][API] Série ignorada (%s): %r', e, serie.get('codSerie'))
            continue

    if log:
        logger.info('[SISBAJUD][API] %d série(s) válida(s) de %d', len(validas), len(bruto))
    return validas


LIMITE_IRRISORIO = 100.0
LIMITE_BLOQUEIO = 1000.0      # a partir disto houve ordem relevante (igual ao core.py)


def valor_a_bloquear(series):
    """Referência da comparação: o MAIOR 'a bloquear' entre as séries."""
    valores = [float(s.get('valor_bloquear') or 0) for s in (series or [])]
    return max(valores) if valores else 0.0


def dados_processo_api(series):
    """Monta o `dados_processo` que `_calcular_estrategia_bloqueio` já espera,"""
    return {'divida': {'valor': _valor_texto(valor_a_bloquear(series))}}


def decidir_fluxo(series, log=True):
    """NEGATIVO / DESBLOQUEIO / POSITIVO e, no POSITIVO, a estratégia."""
    total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in (series or []))
    total_bloquear = sum(float(s.get('valor_bloquear', 0)) for s in (series or []))

    if total_bloqueado == 0.0:
        tipo_fluxo = 'NEGATIVO'
    elif total_bloqueado < LIMITE_IRRISORIO and total_bloquear >= LIMITE_BLOQUEIO:
        tipo_fluxo = 'DESBLOQUEIO'
    else:
        tipo_fluxo = 'POSITIVO'

    resultado = {
        'tipo_fluxo': tipo_fluxo,
        'total_bloqueado': total_bloqueado,
        'total_bloquear': total_bloquear,
        'valor_a_bloquear': valor_a_bloquear(series),
        'estrategia': None,
    }

    if tipo_fluxo == 'POSITIVO':
        try:
            from SISB.processamento.series_estrategia import _calcular_estrategia_bloqueio
            resultado['estrategia'] = _calcular_estrategia_bloqueio(
                series, dados_processo_api(series), log
            )
        except Exception as e:
            if log:
                logger.info('[SISBAJUD][API] Falha ao calcular estratégia: %s', e)

    return resultado


def _numero_processo(dados_processo):
    numero = (dados_processo or {}).get('numero_processo') or (dados_processo or {}).get('numero')
    if isinstance(numero, list):
        numero = numero[0] if numero else None
    return numero


def _voltar_para_detalhe(driver_pje, aba_detalhe, url_detalhe, log=True):
    """Volta o foco do PJe para /detalhe depois da juntada."""
    try:
        abas = list(getattr(driver_pje, 'window_handles', []) or [])
        if len(abas) > 1:
            from Fix.browser_suporte import forcar_fechamento_abas_extras
            forcar_fechamento_abas_extras(driver_pje, aba_detalhe or abas[0])
            if log:
                logger.info('[SISBAJUD][API] Aba de juntada fechada (%d -> %d abas)',
                            len(abas), len(getattr(driver_pje, 'window_handles', []) or []))

        if '/detalhe' not in (driver_pje.current_url or '') and url_detalhe:
            if log:
                logger.info('[SISBAJUD][API] Aba não está em /detalhe — voltando para: %s', url_detalhe)
            driver_pje.get(url_detalhe)

        if log:
            logger.info('[SISBAJUD][API] Foco na aba /detalhe: %s', driver_pje.current_url)
    except Exception as e:
        if log:
            logger.info('[SISBAJUD][API] Erro ao voltar para a aba /detalhe: %s', e)


def _acoes_pje(series, decisao, numero, driver_pje, log=True):
    """Relatório + juntada + despacho no PJe, sem tocar no driver SISBAJUD."""
    from SISB import helpers

    tipo_fluxo = decisao['tipo_fluxo']
    resultado = {
        'status': 'pendente',
        'tipo_fluxo': tipo_fluxo,
        'origem': 'api',
        'series_processadas': 0,
        'ordens_processadas': 0,
        'erros': [],
        'detalhes': {},
        'total_bloqueado': decisao.get('total_bloqueado', 0.0),
        'valor_a_bloquear': decisao.get('valor_a_bloquear', 0.0),
    }

    if not driver_pje:
        resultado['status'] = 'erro'
        resultado['erros'].append('driver_pje ausente — não é possível juntar/despachar')
        return resultado

    aba_detalhe = None
    url_detalhe = ''
    try:
        aba_detalhe = driver_pje.current_window_handle
        url_detalhe = driver_pje.current_url or ''
    except Exception:
        pass

    relatorio = helpers._gerar_relatorio_ordem(
        tipo_fluxo, 0, 0, resultado['detalhes'], series, None, log,
        numero_processo=numero, estrategia=None
    )
    resultado['relatorio_gerado'] = bool(relatorio)
    if not relatorio:
        resultado['status'] = 'erro'
        resultado['erros'].append('relatório não gerado')
        return resultado

    juntada = helpers._executar_juntada_pje(driver_pje, tipo_fluxo, numero, log)
    resultado['juntada_executada'] = bool(juntada)
    if not juntada:
        resultado['status'] = 'erro'
        resultado['erros'].append('juntada no PJe falhou')
        return resultado

    _voltar_para_detalhe(driver_pje, aba_detalhe, url_detalhe, log)

    try:
        from atos.wrappers_ato import ato_meios
        ato_meios(driver_pje)
        resultado['ato_executado'] = True
        if log:
            logger.info('[SISBAJUD][API] ato_meios executado (fluxo %s)', tipo_fluxo)
    except Exception as e:
        resultado['ato_executado'] = False
        resultado['erros'].append('ato_meios: %s' % e)
        if log:
            logger.info('[SISBAJUD][API] Erro ao executar ato_meios: %s', e)

    resultado['status'] = 'concluido'
    return resultado


def processar_ordem_via_api(driver, dados_processo, driver_pje=None, log=True, fechar_driver=True):
    """Ponto de entrada do fluxo `xs resultado`: a API decide, o DOM executa."""
    from SISB.core import processar_ordem_sisbajud

    numero = _numero_processo(dados_processo)
    data_limite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)

    series = ler_series_api(numero, data_limite, log=log)
    if series is None:
        if log:
            logger.info('[SISBAJUD][API] Sem decisão pela API — seguindo caminho DOM atual')
        return processar_ordem_sisbajud(driver, dados_processo, driver_pje, log, fechar_driver)

    decisao = decidir_fluxo(series, log)
    tipo_fluxo = decisao['tipo_fluxo']

    if log:
        logger.info('[SISBAJUD][API] Fluxo decidido pela API: %s | bloqueado R$ %.2f | a bloquear R$ %.2f',
                    tipo_fluxo, decisao.get('total_bloqueado', 0.0), decisao.get('valor_a_bloquear', 0.0))

    if tipo_fluxo == 'POSITIVO':
        return processar_ordem_sisbajud(driver, dados_processo, driver_pje, log, fechar_driver)

    resultado = _acoes_pje(series, decisao, numero, driver_pje, log)

    if tipo_fluxo == 'DESBLOQUEIO' and resultado.get('juntada_executada'):
        if log:
            logger.info('[SISBAJUD][API] Desbloqueio: despacho concluído, processando as ordens agora')
        processamento = processar_ordem_sisbajud(driver, dados_processo, driver_pje, log, fechar_driver)
        resultado['processamento'] = processamento
        if isinstance(processamento, dict):
            resultado['series_processadas'] = processamento.get('series_processadas', 0)
            resultado['ordens_processadas'] = processamento.get('ordens_processadas', 0)
            resultado['detalhes'] = processamento.get('detalhes', {})
            if processamento.get('status') == 'erro':
                resultado['status'] = 'erro'
                resultado['erros'].extend(processamento.get('erros') or [])

    return resultado
