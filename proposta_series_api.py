"""proposta_series_api.py — leitura das séries da Teimosinha por API.

PROPOSTA (não aplicada no bot). Substitui a leitura DOM de
`SISB/processamento/series_filtro.py::_filtrar_series` mantendo o MESMO
contrato de saída, para que nada a jusante precise mudar:

    id_serie, protocolo, acao, data_conclusao, data_conclusao_text,
    situacao, valor_bloqueado, valor_bloquear,
    valor_bloqueado_text, valor_bloquear_text, linha_index

Diferenças em relação ao DOM:
  - `linha_index` vem None e NÃO é usado: quando há ordens para processar
    (DESBLOQUEIO e PARCIAL), quem processa é a função DOM existente, que
    refaz o caminho completo por conta própria — pesquisa o processo, lê a
    lista de séries e abre a série com bloqueio pela linha. A API serve só
    para decidir o fluxo (e alimentar a certidão em NEGATIVO/DESBLOQUEIO).
  - `situacao` é sintetizada como 'Encerrada' quando tipoSituacaoSerie == 2,
    para o filtro textual existente ('encerrada' in situacao.lower()) seguir valendo.

Filtro (idêntico ao atual, só muda a fonte da data):
  - encerrada  -> tipoSituacaoSerie == 2
  - recente    -> dataLimite (FIM da série) >= data_limite
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

URL_API = 'https://sisbajud.pdpj.jus.br/v1/serie'
TIPO_SITUACAO_ENCERRADA = 2

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
    """Lê as séries da Teimosinha por API e devolve o mesmo contrato de `_filtrar_series`.

    Args:
        numero_processo: número com ou sem formatação (só os dígitos importam).
        data_limite: datetime de corte; séries com dataLimite anterior são descartadas.
        token: access_token; se None, carrega de ~/.pjeplus/sisbajud_tokens.json.
        http_get: injetável em teste; assinatura (url, headers, timeout) -> (status, texto).

    Returns:
        list[dict] no contrato de `_filtrar_series`, ou None se a API não puder
        ser usada (sem token, HTTP != 200, corpo inesperado) — quem chama deve
        então cair no caminho DOM atual.
    """
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
            if serie.get('tipoSituacaoSerie') != TIPO_SITUACAO_ENCERRADA:
                continue

            fim_ms = serie.get('dataLimite')
            if not fim_ms:
                continue

            data_fim = datetime.fromtimestamp(fim_ms / 1000.0)
            if isinstance(data_limite, datetime) and data_fim < data_limite:
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
                'situacao': 'Encerrada',
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


# ─────────────────────────── decisão do fluxo ───────────────────────────

LIMITE_IRRISORIO = 100.0      # abaixo disto o bloqueado é resíduo (igual ao core.py)
LIMITE_BLOQUEIO = 1000.0      # a partir disto houve ordem relevante (igual ao core.py)


def valor_a_bloquear(series):
    """Referência da comparação: o MAIOR 'a bloquear' entre as séries.

    Cada série é uma ordem repetida do mesmo valor; somar as séries dobraria a
    referência e o bot passaria a transferir acima do devido. Por isso: máximo,
    não soma (a soma é usada só do lado do bloqueado).
    """
    valores = [float(s.get('valor_bloquear') or 0) for s in (series or [])]
    return max(valores) if valores else 0.0


def dados_processo_api(series):
    """Monta o `dados_processo` que `_calcular_estrategia_bloqueio` já espera,
    com o valor vindo da API (valor a bloquear) no lugar da dívida do PJe.
    """
    return {'divida': {'valor': _valor_texto(valor_a_bloquear(series))}}


def decidir_fluxo(series, log=True):
    """NEGATIVO / DESBLOQUEIO / POSITIVO e, no POSITIVO, a estratégia.

    Usa a MESMA função de estratégia do bot (`_calcular_estrategia_bloqueio`),
    só trocando a fonte do valor de referência — nada em series_estrategia.py muda.
    """
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
