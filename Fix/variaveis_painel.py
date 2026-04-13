"""Fix/variaveis_painel.py
Busca e filtros para Painel Global PJe
"""
from typing import Any, Dict, List, Optional
from selenium.webdriver.remote.webdriver import WebDriver


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
        print('[PAINEL] execute_async_script retornou None')
        return []
    
    if res.get('erro'):
        print(f'[PAINEL] Erro: {res["erro"]}')
        return []
    
    lista = res.get('resultado', [])
    if res.get('aviso'):
        print(f'[PAINEL] Aviso: {res["aviso"]}')
    
    print(f'[PAINEL] Total de itens: {len(lista)} (relatados: {res.get("total", len(lista))})')
    return lista
