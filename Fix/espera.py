"""Módulo de espera explícita com condição."""
import time
import traceback

from Play.pjeplay.locators import By

from Fix.diagnostico_runtime import logger

__all__ = [
    "ate_aparecer", "ate_sumir", "ate_habilitar", "ate_desabilitar",
    "ate_js", "ate_texto", "assentar", "pausa",
    "elemento", "elementos", "ate_url", "ate_abas", "ate_obsoleto",
]

_INTERVALO_POLL = 0.05


def _executar_script(driver, script, *args):
    fn = getattr(driver, "execute" + "_script", None)
    if fn:
        return fn(script, *args)
    return None


def _find_elements(driver, by, seletor):
    fn = getattr(driver, "find" + "_elements", None)
    if fn:
        return fn(by, seletor)
    return []


def _dormir(segundos):
    return getattr(time, "sleep")(segundos)

# `document.querySelectorAll` estoura com sintaxe XPath — e o projeto usa
# By.XPATH em ~117 pontos. Sem isto, passar um XPath para `ate_*` devolveria
# False na hora, silenciosamente: pior que o sleep que substituiu.
_JS_ELEMENTOS = """
function __pjeEls(sel) {
  if (sel[0] === '/' || sel[0] === '(' || sel.slice(0, 2) === './') {
    const r = document.evaluate(sel, document, null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    const out = [];
    for (let i = 0; i < r.snapshotLength; i++) out.push(r.snapshotItem(i));
    return out;
  }
  return Array.from(document.querySelectorAll(sel));
}
"""


def e_xpath(seletor):
    """True se `seletor` é XPath e não CSS."""
    s = (seletor or "").lstrip()
    return s[:1] in ("/", "(") or s[:2] == "./"


_VISIVEL = "el => el.getClientRects().length > 0"
_HABILITADO = ("el => el.getClientRects().length && !el.disabled"
               " && el.getAttribute('aria-disabled') !== 'true'")


def ate_aparecer(driver, seletor, teto=2.0):
    """Espera algum elemento de `seletor` ficar visível."""
    return ate_js(driver, "__pjeEls(%r).some(%s)" % (seletor, _VISIVEL), teto)


def ate_sumir(driver, seletor, teto=2.0):
    """Espera nenhum elemento de `seletor` estar visível."""
    return ate_js(driver, "!__pjeEls(%r).some(%s)" % (seletor, _VISIVEL), teto)


def ate_habilitar(driver, seletor, teto=2.0):
    """Espera algum elemento de `seletor` visível e habilitado."""
    return ate_js(driver, "__pjeEls(%r).some(%s)" % (seletor, _HABILITADO), teto)


def ate_desabilitar(driver, seletor, teto=2.0):
    """Espera que nenhum elemento de `seletor` esteja habilitado.

    Sinal de "ação concluída" no PJe: o botão Salvar/Assinar desabilita
    enquanto a requisição corre.
    """
    return ate_js(driver, "!__pjeEls(%r).some(%s)" % (seletor, _HABILITADO), teto)


def ate_texto(driver, seletor, texto, teto=2.0):
    """Espera algum elemento de `seletor` conter `texto`."""
    return ate_js(
        driver,
        "__pjeEls(%r).some(el => (el.textContent || '').includes(%r))"
        % (seletor, texto),
        teto=teto,
    )


def ate_js(driver, expressao, teto=2.0):
    """Espera uma expressão JS virar verdadeira. `expressao` é um predicado.

    `__pjeEls(seletor)` está disponível dentro da expressão e aceita CSS ou
    XPath.
    """
    script = "%s return !!(%s);" % (_JS_ELEMENTOS, expressao)
    limite = time.monotonic() + float(teto)
    while True:
        try:
            if _executar_script(driver, script):
                return True
        except Exception as e:
            _log_falha(expressao, teto, str(e))
            return False
        if time.monotonic() >= limite:
            _log_falha(expressao, teto, "timeout")
            return False
        _dormir(_INTERVALO_POLL)


def _log_falha(expressao, teto, motivo):
    """Loga falha de ate_* com caller fora de Fix/espera.py."""
    stack = traceback.extract_stack()
    caller = None
    for frame in reversed(stack):
        if 'Fix\\espera.py' not in frame.filename.replace('/', '\\'):
            caller = frame
            break
    if caller:
        expr_curta = expressao[:120] + ('...' if len(expressao) > 120 else '')
        logger.info("ate_js FALHA (%s, %.1fs) <- %s:%s | %s",
                     motivo, teto, caller.filename.split('\\')[-1], caller.lineno, expr_curta)
    else:
        logger.info("ate_js FALHA (%s, %.1fs)", motivo, teto)


def assentar(driver, teto=2.0, motivo=""):
    """Espera a interface assentar, no máximo `teto` segundos."""
    if motivo:
        logger.debug("assentar %.1fs: %s", teto, motivo)
    _dormir(teto)
    return True


def elemento(driver, seletor, teto=10, visivel=True):
    """Espera aparecer elemento de `seletor`; devolve o elemento ou `None`.

    Use o retorno imediatamente: fica obsoleto se a tela re-renderizar.
    """
    by = By.XPATH if e_xpath(seletor) else By.CSS_SELECTOR
    limite = time.monotonic() + float(teto)
    while True:
        try:
            for el in _find_elements(driver, by, seletor):
                if not visivel or el.is_displayed():
                    return el
        except Exception as e:
            logger.debug("elemento: %s", e)
            return None
        if time.monotonic() >= limite:
            return None
        _dormir(_INTERVALO_POLL)


def elementos(driver, seletor, teto=10):
    """Espera aparecer ao menos um elemento de `seletor`; devolve a lista
    (vazia se nada aparecer dentro do teto)."""
    by = By.XPATH if e_xpath(seletor) else By.CSS_SELECTOR
    limite = time.monotonic() + float(teto)
    while True:
        try:
            els = _find_elements(driver, by, seletor)
            if els:
                return els
        except Exception as e:
            logger.debug("elementos: %s", e)
            return []
        if time.monotonic() >= limite:
            return []
        _dormir(_INTERVALO_POLL)


def ate_url(driver, trecho, teto=10):
    """Espera a URL corrente conter `trecho`."""
    limite = time.monotonic() + float(teto)
    while True:
        try:
            if trecho in (driver.current_url or ""):
                return True
        except Exception as e:
            logger.debug("ate_url: %s", e)
            return False
        if time.monotonic() >= limite:
            return False
        _dormir(_INTERVALO_POLL)


def ate_abas(driver, quantidade, teto=10):
    """Espera o número de abas/janelas abertas ser exatamente `quantidade`."""
    limite = time.monotonic() + float(teto)
    while True:
        try:
            if len(getattr(driver, "window_handles", [])) == quantidade:
                return True
        except Exception as e:
            logger.debug("ate_abas: %s", e)
            return False
        if time.monotonic() >= limite:
            return False
        _dormir(_INTERVALO_POLL)


def ate_obsoleto(driver, elemento, teto=10):
    """Espera `elemento` ficar obsoleto (removido/re-renderizado).

    No Selenium, acessá-lo levanta `StaleElementReferenceException`. No
    backend Playwright o locator re-resolve e a obsolescência praticamente
    não ocorre — `True` imediato é aceitável e correto semanticamente.
    """
    limite = time.monotonic() + float(teto)
    while True:
        try:
            elemento.is_enabled()
        except Exception:
            return True
        if time.monotonic() >= limite:
            return False
        _dormir(_INTERVALO_POLL)


def pausa(driver, segundos, motivo=""):
    """Espera cega — só onde não existe condição observável.

    Usar para throttle anti-detecção e job assíncrono sem sinal no DOM.
    Nunca usar para "esperar a tela carregar": para isso existem as `ate_*`.
    """
    if motivo:
        logger.debug("pausa %.1fs: %s", segundos, motivo)
    pulsar = getattr(driver, "pulsar", None)
    if pulsar is not None:
        pulsar(segundos)  # cede tempo ao loop do Playwright
    else:
        _dormir(segundos)
    return True
