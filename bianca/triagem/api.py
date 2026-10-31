# -*- coding: utf-8 -*-
"""
bianca/triagem/api.py -- Helpers de API para o modulo de triagem.

Busca a lista de processos da fila "Triagem Inicial" via execute_async_script
(fetch do proprio browser, respeitando cookies e XSRF-TOKEN).

Funcoes:
    buscar_lista_triagem(driver)   Busca itens da fila via async JS fetch.
    enriquecer_processo(item)      Enriquece item bruto com metadados.
    _is_triagem_inicial(item)      Filtro de tarefa "Triagem Inicial".
    _is_carta_precatoria(item)     Filtro de Carta Precatória (bucket CP).
    _numero_cnj(item)              Extrai numero CNJ do item.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger("bianca.triagem.api")

# =============================================================================
# JS para buscar triagem via fetch no browser
# =============================================================================

_JS_BUSCAR_TRIAGEM = """
const tamPag   = arguments[0] || 100;
const callback = arguments[1];

var xsrfCookie = document.cookie.split(';')
    .map(function(c) { return c.trim(); })
    .find(function(c) { return c.toLowerCase().indexOf('xsrf-token=') === 0; });
var xsrf = xsrfCookie ? xsrfCookie.split('=').slice(1).join('=') : '';

function normalizar(d) {
    if (!d) return [];
    if (Array.isArray(d)) return d;
    var chaves = ['resultado', 'content', 'data', 'conteudo', 'items', 'processos'];
    for (var i = 0; i < chaves.length; i++) {
        if (Array.isArray(d[chaves[i]])) return d[chaves[i]];
    }
    return [];
}

(async function() {
    var base = location.origin;
    var url  = base + '/pje-comum-api/api/agrupamentotarefas/10/processos';
    var todos = [];
    var pg = 1;
    var LIMITE = 50;
    while (pg <= LIMITE) {
        try {
            var r = await window.fetch(url, {
                method: 'PATCH',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-XSRF-TOKEN': xsrf
                },
                body: JSON.stringify({
                    pagina: pg, tamanhoPagina: tamPag,
                    subCaixa: null, tipoAtividade: null, processos: null,
                    nomeConclusoMagistrado: null, usuarioResponsavel: null,
                    faseProcessualString: null, numeroProcesso: null,
                    juizoDigital: null
                })
            });
            if (!r.ok) {
                callback({ erro: 'HTTP_' + r.status, resultado: todos, pagina: pg });
                return;
            }
            var data = await r.json();
            var lista = normalizar(data);
            if (!lista.length) {
                callback({ resultado: todos });
                return;
            }
            todos = todos.concat(lista);
            var totalPags = data.qtdPaginas || data.totalPaginas || 1;
            if (pg >= totalPags || lista.length < tamPag) {
                callback({ resultado: todos, total: data.totalRegistros || todos.length });
                return;
            }
            pg++;
        } catch(e) {
            callback({ erro: 'ASYNC_ERR: ' + e.message, resultado: todos });
            return;
        }
    }
    callback({ resultado: todos, aviso: 'limite_paginas' });
})();
"""


# =============================================================================
# Funcoes de busca
# =============================================================================


def buscar_lista_triagem(driver: Any) -> List[Dict[str, Any]]:
    """Busca todos os itens da fila via execute_async_script (fetch no browser).

    O fetch corre dentro do contexto do browser: cookies de sessao e XSRF-TOKEN
    sao tratados automaticamente -- sem depender de requests.Session.
    """
    try:
        driver.set_script_timeout(120)
        res = driver.execute_async_script(_JS_BUSCAR_TRIAGEM, 100)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass

    if not res:
        logger.warning('execute_async_script retornou None')
        return []

    if res.get('erro'):
        logger.error('Erro: %s', res['erro'])
        return []

    if res.get('aviso'):
        logger.warning('Aviso: %s', res['aviso'])

    lista = res.get('resultado', [])
    logger.info('Total bruto: %s itens', len(lista))
    return lista


# =============================================================================
# Enriquecimento de processos
# =============================================================================


def _is_triagem_inicial(item: Dict) -> bool:
    """Verifica se o item pertence a fila 'Triagem Inicial'."""
    tarefa = item.get('tarefa') or ''
    if isinstance(tarefa, dict):
        tarefa = str(tarefa.get('nome') or tarefa.get('descricao') or '')
    return 'triagem inicial' in str(tarefa).lower()


def _is_carta_precatoria(item: Dict) -> bool:
    """Verifica se o processo e uma Carta Precatória.

    Detecta pelos campos classeJudicial ou descricaoProcesso.
    Ex: CartPrecCiv, Carta Precatória, etc.
    """
    classe = str(item.get('classeJudicial') or '').upper()
    if 'CARTPREC' in classe or 'CART_PREC' in classe or 'CARTAPREC' in classe:
        return True
    descricao = str(item.get('descricaoProcesso') or item.get('descricao') or '').upper()
    if 'CARTA PRECATORIA' in descricao or 'CARTAPREC' in descricao:
        return True
    return False


def _numero_cnj(item: Dict) -> str:
    """Extrai o numero CNJ do item."""
    return str(item.get('numeroProcesso') or item.get('numero') or item.get('id') or '')


# Movimento que marca o processo como Juizo 100% Digital na timeline.
MOV_100_DIGITAL_TITULO = 'incluidos os autos no juizo 100% digital'


def parse_data_hora_movimento(val: Any) -> Optional[datetime]:
    """Converte string ISO de data/hora do PJe em datetime."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    try:
        clean = val.rstrip('Zz').split('+')[0]
        if '.' in clean:
            return datetime.strptime(clean[:23], '%Y-%m-%dT%H:%M:%S.%f')
        elif 'T' in clean:
            return datetime.strptime(clean, '%Y-%m-%dT%H:%M:%S')
        elif ' ' in clean:
            if '.' in clean:
                return datetime.strptime(clean[:23], '%Y-%m-%d %H:%M:%S.%f')
            return datetime.strptime(clean, '%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return None


def obter_movimentos_timeline(client: Any, id_processo: str) -> List[Dict]:
    """Obtém a lista de movimentos da timeline do processo via API."""
    if not client or not id_processo:
        return []
    try:
        return client.timeline(
            str(id_processo), buscarDocumentos=False, buscarMovimentos=True
        ) or []
    except Exception as e:
        logger.warning(
            "[TRIAGEM][API] Falha ao ler movimentos de %s: %s", id_processo, e
        )
        return []


def classificar_audiencia_movimentos(
    itens_movimentos: List[Dict],
) -> Tuple[str, Dict[str, Any]]:
    """Classifica a situação de audiência do processo a partir dos movimentos da timeline.

    3 casos:
      (a) 'SEM_AUDIENCIA': não há movimento de audiência designada na timeline.
          -> Fluxo de sempre (marca audiência + despacha).
      (b) 'TEM_AUDIENCIA': há audiência designada com horário muito próximo (<= 180s)
          ao da distribuição do processo (autuação automática).
          -> Fluxo de sempre (Bucket B se 100% digital, Bucket C se presencial).
      (c) 'AUDIENCIA_TARDIA': tem audiência, mas a marcação veio mais tarde que a
          distribuição (> 180s ou data diferente).
          -> Trata como SEM AUDIÊNCIA, mas pula a marcação de pauta.

    Returns:
        Tuple[str, Dict[str, Any]]: (status, detalhes)
    """
    from Fix.utils import normalizar_texto

    mov_distribuicao = None
    dt_dist = None
    mov_audiencia = None
    dt_aud = None

    for item in itens_movimentos:
        if not isinstance(item, dict):
            continue
        titulo = normalizar_texto(str(item.get('titulo') or item.get('textoFinalExterno') or ''))
        cod = 0
        try:
            cod = int(item.get('codEvento') or 0)
        except (TypeError, ValueError):
            pass

        data_str = str(item.get('data') or item.get('dataHora') or item.get('atualizadoEm') or '')
        dt_item = parse_data_hora_movimento(data_str)

        # 1. Identificar movimento de distribuição
        if not mov_distribuicao:
            if cod in (26, 27, 28, 29, 30) or 'distribui' in titulo:
                mov_distribuicao = item
                dt_dist = dt_item

        # 2. Identificar movimento de audiência designada
        if not mov_audiencia:
            if ('audiencia' in titulo and 'designada' in titulo) or ('designad' in titulo and 'audienc' in titulo):
                mov_audiencia = item
                dt_aud = dt_item

    detalhes = {
        'dt_dist': dt_dist,
        'dt_aud': dt_aud,
        'mov_dist': mov_distribuicao,
        'mov_aud': mov_audiencia,
    }

    # Caso (a): Não tem audiência designada na timeline
    if not mov_audiencia:
        return 'SEM_AUDIENCIA', detalhes

    # Se tem audiência e tem distribuição, compara os horários
    if dt_dist and dt_aud:
        delta = abs((dt_aud - dt_dist).total_seconds())
        detalhes['delta_segundos'] = delta
        # Caso (b): Horário muito próximo (até 180s da autuação)
        if dt_dist.date() == dt_aud.date() and delta <= 180:
            return 'TEM_AUDIENCIA', detalhes
        # Caso (c): Veio mais tarde que a distribuição
        return 'AUDIENCIA_TARDIA', detalhes

    # Se tem movimento de audiência mas não foi possível extrair data da distribuição
    return 'AUDIENCIA_TARDIA', detalhes


def processo_e_100_digital(
    client: Any, id_processo: str, itens_movimentos: Optional[List[Dict]] = None
) -> bool:
    """True se a timeline do processo tem o movimento de Juizo 100% Digital."""
    if itens_movimentos is None:
        itens_movimentos = obter_movimentos_timeline(client, id_processo)
    if not itens_movimentos:
        return False
    from Fix.utils import normalizar_texto
    for item in itens_movimentos:
        titulo = normalizar_texto(str(item.get('titulo') or ''))
        if MOV_100_DIGITAL_TITULO in titulo:
            return True
    return False


def enriquecer_processo(item: Dict, client: Any = None) -> Optional[Dict]:
    """Enriquece um item bruto da lista com metadados processados.

    Args:
        item: item bruto da lista de triagem.
        client: PjeApiClient autenticado. Quando informado, o 100% digital e
            os 3 casos de audiência são confirmados pela timeline de movimentos.

    Retorna dict com:
        numero, id_processo, tipo, digital, tem_audiencia, status_audiencia,
        pular_marcar_aud, bucket
    """
    id_proc = item.get('id') or item.get('idProcesso')
    numero = _numero_cnj(item)
    if not id_proc:
        return None

    tipo = str(item.get('classeJudicial') or '').upper()
    itens_mov = obter_movimentos_timeline(client, id_proc) if client is not None else []

    digital = item.get('juizoDigital') is True or item.get('juizoDigital') == 'true'
    if not digital and client is not None:
        digital = processo_e_100_digital(client, id_proc, itens_mov)

    status_aud = 'SEM_AUDIENCIA'
    pular_marcar_aud = False
    tem_aud = False

    if itens_mov:
        status_aud, det = classificar_audiencia_movimentos(itens_mov)
        if status_aud == 'TEM_AUDIENCIA':
            tem_aud = True
            pular_marcar_aud = False
        elif status_aud == 'AUDIENCIA_TARDIA':
            # Caso (c): trata como SEM AUDIÊNCIA pra efeito de fluxo, pulando marcar audiência
            tem_aud = False
            pular_marcar_aud = True
        else:
            # Caso (a): SEM AUDIÊNCIA, fluxo de sempre (marca audiência + despacha)
            tem_aud = False
            pular_marcar_aud = False
    else:
        # Fallback sem API: usa o campo bruto da lista
        tem_aud = bool(item.get('dataProximaAudiencia'))
        pular_marcar_aud = False
        status_aud = 'TEM_AUDIENCIA' if tem_aud else 'SEM_AUDIENCIA'

    if _is_carta_precatoria(item):
        bucket = 'CP'
    elif 'HTE' in tipo:
        bucket = 'D'
    elif not tem_aud:
        bucket = 'A'
    elif digital:
        bucket = 'B'
    else:
        bucket = 'C'

    return {
        'numero': numero,
        'id_processo': id_proc,
        'tipo': tipo,
        'digital': digital,
        'tem_audiencia': tem_aud,
        'status_audiencia': status_aud,
        'pular_marcar_aud': pular_marcar_aud,
        'bucket': bucket,
        'dataProximaAudiencia': item.get('dataProximaAudiencia'),
        'data_audiencia': item.get('dataProximaAudiencia'),
    }
