"""Triagem/api.py
API de busca e enriquecimento de processos da Triagem Inicial.
"""
from typing import Any, Dict, List, Optional
from selenium.webdriver.remote.webdriver import WebDriver

URL_LISTA_TRIAGEM = 'https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos'


def _normalizar_lista(dados) -> list:
    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        for chave in ('resultado', 'content', 'data', 'conteudo', 'items'):
            if isinstance(dados.get(chave), list):
                return dados[chave]
    return []


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


def buscar_lista_triagem(driver: WebDriver) -> List[Dict[str, Any]]:
    """Busca todos os itens da fila via execute_async_script."""
    try:
        driver.set_script_timeout(120)
        res = driver.execute_async_script(_JS_BUSCAR_TRIAGEM, 100)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass

    if not res:
        print('[TRIAGEM/API] execute_async_script retornou None')
        return []

    if res.get('erro'):
        print(f'[TRIAGEM/API] Erro do fetch JS: {res["erro"]}')
        return []

    if res.get('aviso'):
        print(f'[TRIAGEM/API] Aviso: {res["aviso"]}')

    lista = res.get('resultado', [])
    print(f'[TRIAGEM/API] Total bruto: {len(lista)} itens')
    return lista


def _is_triagem_inicial(item: Dict) -> bool:
    tarefa = item.get('tarefa') or ''
    if isinstance(tarefa, dict):
        tarefa = str(tarefa.get('nome') or tarefa.get('descricao') or '')
    return 'triagem inicial' in str(tarefa).lower()


def _numero_cnj(item: Dict) -> str:
    return str(item.get('numeroProcesso') or item.get('numero') or item.get('id') or '')


def enriquecer_processo(item: Dict) -> Optional[Dict]:
    id_proc = item.get('id') or item.get('idProcesso')
    numero = _numero_cnj(item)
    if not id_proc:
        return None

    tipo = str(item.get('classeJudicial') or '').upper()
    digital = item.get('juizoDigital') is True or item.get('juizoDigital') == 'true'
    tem_aud = bool(item.get('dataProximaAudiencia'))

    bucket = 'D' if 'HTE' in tipo else ('A' if not tem_aud else ('B' if digital else 'C'))
    return {
        'numero': numero,
        'id_processo': id_proc,
        'tipo': tipo,
        'digital': digital,
        'tem_audiencia': tem_aud,
        'bucket': bucket,
    }


_JS_BUSCAR_COM_FILTROS = """
const tamPag   = arguments[0] || 100;
const filtros  = arguments[1] || {};
const callback = arguments[2];

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
            var payload = {
                pagina: pg, 
                tamanhoPagina: tamPag,
                subCaixa: filtros.sub_caixa || null,
                tipoAtividade: filtros.tipo_atividade || null,
                processos: filtros.processos || null,
                nomeConclusoMagistrado: filtros.nome_concluso || null,
                usuarioResponsavel: filtros.usuario_responsavel || null,
                faseProcessualString: filtros.fase || null,
                numeroProcesso: filtros.numero || null,
                juizoDigital: filtros.juizo_digital !== undefined ? filtros.juizo_digital : null
            };
            
            var r = await window.fetch(url, {
                method: 'PATCH',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-XSRF-TOKEN': xsrf
                },
                body: JSON.stringify(payload)
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


def buscar_painel_com_filtros(
    driver: WebDriver,
    fase: str = None,
    sub_caixa: list = None,
    tipo_atividade: list = None,
    usuario_responsavel: str = None,
    juizo_digital: bool = None,
    numero_processo: str = None,
    tam_pagina: int = 100
) -> List[Dict[str, Any]]:
    """Busca processos no Painel Global filtrando por fase + chips.
    
    Args:
        driver: WebDriver Selenium autenticado
        fase: "Conhecimento", "Execução", "Liquidação" ou None
        sub_caixa: lista de nomes de sub-caixa ou None
        tipo_atividade: lista de tipos de atividade ou None
        usuario_responsavel: nome do usuário responsável ou None
        juizo_digital: True/False/None para filtrar por juízo digital
        numero_processo: número do processo ou None
        tam_pagina: itens por página (padrão: 100)
    
    Returns:
        Lista de dicionários com os processos encontrados
    
    Exemplo:
        >>> processos = buscar_painel_com_filtros(driver, fase="Execução", sub_caixa=["Sub-caixa 1"])
        >>> print(f"Encontrados {len(processos)} processos")
    """
    filtros = {
        'fase': fase,
        'sub_caixa': sub_caixa,
        'tipo_atividade': tipo_atividade,
        'usuario_responsavel': usuario_responsavel,
        'juizo_digital': juizo_digital,
        'numero': numero_processo
    }
    
    try:
        driver.set_script_timeout(120)
        res = driver.execute_async_script(_JS_BUSCAR_COM_FILTROS, tam_pagina, filtros)
    finally:
        try:
            driver.set_script_timeout(30)
        except Exception:
            pass
    
    if not res:
        print('[TRIAGEM/API] execute_async_script retornou None')
        return []
    
    if res.get('erro'):
        print(f'[TRIAGEM/API] Erro: {res["erro"]}')
        return []
    
    lista = res.get('resultado', [])
    if res.get('aviso'):
        print(f'[TRIAGEM/API] Aviso: {res["aviso"]}')
    
    print(f'[TRIAGEM/API] Total de itens: {len(lista)} (relatados: {res.get("total", len(lista))})')
    return lista


__all__ = [
    'buscar_lista_triagem',
    'buscar_painel_com_filtros',
    '_is_triagem_inicial',
    'enriquecer_processo',
    '_numero_cnj',
    '_normalizar_lista',
]
