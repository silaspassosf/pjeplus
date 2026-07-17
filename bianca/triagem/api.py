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
from typing import Any, Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

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


def buscar_lista_triagem(driver: WebDriver) -> List[Dict[str, Any]]:
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


def enriquecer_processo(item: Dict) -> Optional[Dict]:
    """Enriquece um item bruto da lista com metadados processados.

    Retorna dict com:
        numero, id_processo, tipo, digital, tem_audiencia, bucket
    """
    id_proc = item.get('id') or item.get('idProcesso')
    numero = _numero_cnj(item)
    if not id_proc:
        return None

    tipo = str(item.get('classeJudicial') or '').upper()
    digital = item.get('juizoDigital') is True or item.get('juizoDigital') == 'true'
    tem_aud = bool(item.get('dataProximaAudiencia'))

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
        'bucket': bucket,
    }
