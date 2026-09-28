"""probe_triagem.py - intercepta XHR/fetch do Angular para descobrir metodo+URL+body exatos.

Estrategia (Firefox-compatible, sem CDP):
  1. Navega para a pagina de triagem e aguarda Angular carregar
  2. Injeta interceptor XHR+fetch via execute_script
  3. Forca re-navegacao Angular via history.pushState + popstate (sem reload de pagina)
     para capturar as chamadas com o interceptor ja ativo
  4. Replica as chamadas capturadas com execute_async_script para confirmar resposta

Executa: py probe_triagem.py (headless)
"""

import json
import time
import traceback

URL_LISTA_TRIAGEM = 'https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos'
URL_OUTRA_ROTA   = 'https://pje.trt2.jus.br/pjekz/painel/global/10'  # rota pai, sem lista

# Interceptor instalado DEPOIS do carregamento inicial.
# Cobre tanto XHR quanto fetch.
JS_INTERCEPTOR = """
window.__pjeCalls = [];
var _xhrOpen = XMLHttpRequest.prototype.open;
var _xhrSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(method, url) {
    this.__pjeMethod = method;
    this.__pjeUrl = url;
    return _xhrOpen.apply(this, arguments);
};
XMLHttpRequest.prototype.send = function(body) {
    if (this.__pjeUrl && this.__pjeUrl.indexOf('pje-comum-api') !== -1) {
        window.__pjeCalls.push({
            type: 'xhr', method: this.__pjeMethod, url: this.__pjeUrl,
            body: body ? body.toString().slice(0, 500) : null
        });
    }
    return _xhrSend.apply(this, arguments);
};
var _fetch = window.fetch;
window.fetch = function(url, opts) {
    opts = opts || {};
    var u = typeof url === 'string' ? url : (url && url.url) || '';
    if (u.indexOf('pje-comum-api') !== -1) {
        window.__pjeCalls.push({
            type: 'fetch', method: (opts.method || 'GET').toUpperCase(),
            url: u,
            body: opts.body ? opts.body.toString().slice(0, 500) : null
        });
    }
    return _fetch.apply(this, arguments);
};
"""

BODIES_POST = []  # nao utilizado


def _shape(dados) -> str:
    if isinstance(dados, list):
        return f'list[{len(dados)}]'
    if isinstance(dados, dict):
        return f'dict{{{", ".join(list(dados.keys())[:8])}}}'
    return type(dados).__name__


def _normalizar(dados) -> list:
    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        for k in ('resultado', 'content', 'data', 'conteudo', 'items', 'processos'):
            if isinstance(dados.get(k), list):
                return dados[k]
    return []


_JS_REPLAY = """
const chamadas = arguments[0];
const callback = arguments[1];

var xsrfCookie = document.cookie.split(';')
    .map(function(c) { return c.trim(); })
    .find(function(c) { return c.toLowerCase().indexOf('xsrf-token=') === 0; });
var xsrf = xsrfCookie ? xsrfCookie.split('=').slice(1).join('=') : '';

(async function() {
    var resultados = [];
    for (var i = 0; i < chamadas.length; i++) {
        var c = chamadas[i];
        try {
            var opts = {
                method: c.method,
                credentials: 'include',
                headers: { 'Accept': 'application/json', 'X-XSRF-TOKEN': xsrf }
            };
            if (c.body) {
                opts.headers['Content-Type'] = 'application/json';
                opts.body = c.body;
            }
            var r = await window.fetch(c.url, opts);
            var txt = await r.text();
            var parsed = null;
            try { parsed = JSON.parse(txt); } catch(e) {}
            resultados.push({ url: c.url, method: c.method, body_enviado: c.body,
                               status: r.status, json: parsed, raw: txt.slice(0, 300) });
        } catch(e) {
            resultados.push({ url: c.url, method: c.method, erro: e.message });
        }
    }
    callback(resultados);
})();
"""


def rodar():
    from Fix.utils import driver_pc, login_cpf

    print('[PROBE] Criando driver')
    drv = driver_pc(headless=False)
    if not drv:
        print('[PROBE] Falha ao criar driver')
        return

    try:
        if not login_cpf(drv):
            print('[PROBE] Login falhou')
            return

        # 1. Navega para rota PAI (sem lista) para o Angular ja ter carregado
        print(f'[PROBE] Carregando rota base: {URL_OUTRA_ROTA}')
        drv.get(URL_OUTRA_ROTA)
        time.sleep(4)

        # 2. Instala interceptor com a pagina ja em pe (Firefox-compatible)
        drv.execute_script(JS_INTERCEPTOR)
        print('[PROBE] Interceptor instalado')

        # 3. Navega para a rota de lista via Angular router (SPA navigation = sem reload)
        #    Isso forca o Angular a recarregar o componente e refazer as chamadas HTTP
        drv.execute_script(
            "window.history.pushState({}, '', arguments[0]);"
            "window.dispatchEvent(new PopStateEvent('popstate', {state: {}}));",
            '/pjekz/painel/global/10/lista-processos'
        )
        print('[PROBE] Angular router acionado — aguardando chamadas...')
        time.sleep(6)

        # 4. Coleta chamadas capturadas
        chamadas = drv.execute_script('return window.__pjeCalls || []')
        print(f'\n[PROBE] Chamadas interceptadas (pje-comum-api): {len(chamadas)}')
        for c in chamadas:
            print(f'  {c["type"].upper():5} {c["method"]:7} {c["url"]}')
            if c.get('body'):
                print(f'          body: {c["body"][:200]}')

        if not chamadas:
            print('[PROBE] Nenhuma chamada capturada via SPA navigation')
            print('[PROBE] Tentando navegacao direta para capturar...')
            drv.get(URL_LISTA_TRIAGEM)
            time.sleep(6)
            # Neste caso nao teremos as chamadas iniciais, mas podemos tentar
            # extrair via performance API + replay
            chamadas = drv.execute_script("""
                var r = performance.getEntriesByType('resource');
                return r.filter(function(e){ return e.name.indexOf('pje-comum-api') !== -1; })
                        .map(function(e){ return { method: 'GET', url: e.name, body: null, type: 'perf' }; });
            """) or []
            print(f'[PROBE] URLs via PerformanceAPI: {len(chamadas)}')
            for c in chamadas:
                print(f'  {c["url"]}')

        if not chamadas:
            print('[PROBE] Sem dados suficientes para replay')
            return

        # 5. Replica todas as chamadas unicas
        unicas = {c['url']: c for c in chamadas}.values()
        print(f'\n[PROBE] Replicando {len(list(unicas))} chamadas unicas...')
        drv.set_script_timeout(60)
        resultados = drv.execute_async_script(_JS_REPLAY, list({c['url']: c for c in chamadas}.values()))

        for res in resultados:
            print(f'\n  {res.get("method","?"):7} {res["url"]}')
            if res.get('body_enviado'):
                print(f'  body: {res["body_enviado"][:100]}')
            if res.get('erro'):
                print(f'    ERRO: {res["erro"]}')
                continue
            print(f'    HTTP {res["status"]}')
            if res.get('json') is not None:
                dados = res['json']
                lista = _normalizar(dados)
                print(f'    shape: {_shape(dados)} | lista: {len(lista)} itens')
                if lista:
                    print(f'    *** DADOS! 1o item: {json.dumps(lista[0], ensure_ascii=False, default=str)[:300]} ***')
                else:
                    chaves = list(dados.keys())[:10] if isinstance(dados, dict) else '?'
                    print(f'    chaves raiz: {chaves}')
            else:
                print(f'    raw: {res.get("raw")}')

    except Exception:
        traceback.print_exc()
    finally:
        try:
            drv.quit()
        except Exception:
            pass


if __name__ == '__main__':
    rodar()
