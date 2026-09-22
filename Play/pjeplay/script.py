"""Ponte execute_script / execute_async_script para Playwright.

Selenium injeta os parametros como `arguments[0..n]` e, no modo async, recebe
um callback em `arguments[arguments.length - 1]`. Playwright passa um unico
argumento para uma funcao. A ponte reconstroi a semantica original aplicando o
script dentro de uma `function` classica (que tem `arguments` real) via
`.apply(null, args)` — assim nenhum dos ~295 `execute_script` do projeto precisa
ser reescrito.
"""
from .errors import traduzir

_SYNC = "(__a) => (function(){ %s }).apply(null, __a)"
_ASYNC = (
    "(__a) => new Promise((__resolve, __reject) => {"
    " try { (function(){ %s }).apply(null, __a.concat([__resolve])); }"
    " catch (e) { __reject(e); } })"
)


def _desempacotar(valor):
    """Converte PWElement -> ElementHandle antes de enviar ao browser."""
    from .element import PWElement

    if isinstance(valor, PWElement):
        return valor._handle
    if isinstance(valor, (list, tuple)):
        return [_desempacotar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _desempacotar(v) for k, v in valor.items()}
    return valor


def _reempacotar(handle):
    """Converte o retorno do browser em valor Python / PWElement."""
    from .element import PWElement

    elemento = handle.as_element()
    if elemento is not None:
        return PWElement(elemento)

    try:
        valor = handle.json_value()
    except Exception:
        # Provavel colecao contendo nos DOM: desmonta propriedade a propriedade.
        # Os handles-filhos seguem vivos, por isso o pai nao e descartado aqui.
        try:
            return [_reempacotar(v) for v in handle.get_properties().values()]
        except Exception:
            return None

    try:
        handle.dispose()
    except Exception:
        pass
    return valor


def executar(page, script, args, assincrono=False):
    """Executa `script` no contexto de `page` com semantica Selenium."""
    corpo = (_ASYNC if assincrono else _SYNC) % script
    try:
        handle = page.evaluate_handle(corpo, _desempacotar(list(args)))
    except Exception as e:
        raise traduzir(e) from e
    return _reempacotar(handle)
