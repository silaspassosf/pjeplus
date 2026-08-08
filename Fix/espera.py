"""Esperas com condição explícita — substitui `time.sleep()` sem risco.

Regra de segurança que torna a troca auditável: **toda função aqui é limitada
pelo `teto`, que é a duração do sleep que ela substituiu.** Se a condição nunca
ocorrer, o custo é idêntico ao sleep original. Nunca mais lenta, nunca menos
confiável — só mais rápida quando a condição chega antes.

    time.sleep(2)                    ->  espera.ate_sumir(driver, 'mat-spinner', teto=2)

Vale nos dois motores. Em Selenium usa `aguardar_renderizacao_nativa` (poll);
em Playwright o mesmo nome já foi trocado por auto-wait em `pjeplay.nativo`,
então a mesma linha vira orientada a evento sem precisar de outra versão.

`pausa()` é a saída honesta para o que não tem condição observável — throttle
anti-detecção, job assíncrono no servidor. Mantê-la nomeada deixa esses casos
greppáveis, em vez de escondidos entre centenas de `time.sleep` anônimos.
"""
import time
import traceback

from selenium.webdriver.common.by import By

from Fix.diagnostico_runtime import logger

__all__ = [
    "ate_aparecer", "ate_sumir", "ate_habilitar", "ate_desabilitar",
    "ate_js", "ate_texto", "assentar", "pausa",
    "elemento", "elementos", "ate_url", "ate_abas", "ate_obsoleto",
]

_INTERVALO_POLL = 0.05

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
            if driver.execute_script(script):
                return True
        except Exception as e:
            _log_falha(expressao, teto, str(e))
            return False
        if time.monotonic() >= limite:
            _log_falha(expressao, teto, "timeout")
            return False
        time.sleep(_INTERVALO_POLL)


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
        logger.info("ate_js FALHA (%s, %.1fs) ← %s:%s | %s",
                     motivo, teto, caller.filename.split('\\')[-1], caller.lineno, expr_curta)
    else:
        logger.info("ate_js FALHA (%s, %.1fs)", motivo, teto)


def assentar(driver, teto=2.0, motivo=""):
    """Espera a interface assentar, no máximo `teto` segundos.

    É a substituição mecânica de `time.sleep(teto)` onde a condição exata não
    foi (ainda) identificada. O contrato é o mesmo das demais: **nunca custa
    mais que o sleep que substituiu**.

    Em Selenium não há sinal barato de "assentou" — cada poll é um round-trip —
    então o comportamento é idêntico ao de hoje: dorme `teto`. Em Playwright,
    `pjeplay.nativo` troca esta função por uma que aguarda o Angular estabilizar
    e os spinners sumirem, tipicamente em 50–200 ms.

    É exatamente aqui que o ganho do Playwright aparece sem reescrever fluxo.
    Quando a condição precisa for identificada, trocar por uma `ate_*` é uma
    melhoria adicional — não um pré-requisito.
    """
    if motivo:
        logger.debug("assentar %.1fs: %s", teto, motivo)
    time.sleep(teto)
    return True


def elemento(driver, seletor, teto=10, visivel=True):
    """Espera aparecer elemento de `seletor`; devolve o elemento ou `None`.

    Use o retorno imediatamente: fica obsoleto se a tela re-renderizar.
    """
    by = By.XPATH if e_xpath(seletor) else By.CSS_SELECTOR
    limite = time.monotonic() + float(teto)
    while True:
        try:
            for el in driver.find_elements(by, seletor):
                if not visivel or el.is_displayed():
                    return el
        except Exception as e:
            logger.debug("elemento: %s", e)
            return None
        if time.monotonic() >= limite:
            return None
        time.sleep(_INTERVALO_POLL)


def elementos(driver, seletor, teto=10):
    """Espera aparecer ao menos um elemento de `seletor`; devolve a lista
    (vazia se nada aparecer dentro do teto)."""
    by = By.XPATH if e_xpath(seletor) else By.CSS_SELECTOR
    limite = time.monotonic() + float(teto)
    while True:
        try:
            els = driver.find_elements(by, seletor)
            if els:
                return els
        except Exception as e:
            logger.debug("elementos: %s", e)
            return []
        if time.monotonic() >= limite:
            return []
        time.sleep(_INTERVALO_POLL)


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
        time.sleep(_INTERVALO_POLL)


def ate_abas(driver, quantidade, teto=10):
    """Espera o número de abas/janelas abertas ser exatamente `quantidade`."""
    limite = time.monotonic() + float(teto)
    while True:
        try:
            if len(driver.window_handles) == quantidade:
                return True
        except Exception as e:
            logger.debug("ate_abas: %s", e)
            return False
        if time.monotonic() >= limite:
            return False
        time.sleep(_INTERVALO_POLL)


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
        time.sleep(_INTERVALO_POLL)


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
        time.sleep(segundos)
    return True
