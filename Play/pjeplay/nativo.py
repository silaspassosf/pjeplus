"""Caminho rapido: substitui os helpers quentes de Fix/ por versoes nativas.

A camada de compatibilidade sozinha ja faz o projeto rodar, mas mantem o custo
do Selenium: polling de 500ms no WebDriverWait e MutationObserver injetado via
execute_async_script. Aqui esses mesmos helpers passam a usar o auto-wait do
Playwright — mesma assinatura, mesmo contrato de retorno, sem polling.

Cada funcao delega para a implementacao original quando o driver nao e um
PWDriver, entao aplicar isto e seguro mesmo em execucao mista.
"""
import logging

from .driver import PWDriver
from .element import PWElement
from .locators import By
from .locators import traduzir as traduzir_seletor

logger = logging.getLogger("pjeplay")

_ORIGINAIS = {}

# Visibilidade equivalente ao is_displayed() do Selenium.
_VISIVEL = "el => el.getClientRects().length > 0"
_ALGUM_VISIVEL = (
    "sel => Array.from(document.querySelectorAll(sel))"
    ".some(el => el.getClientRects().length > 0)"
)
_NENHUM_VISIVEL = (
    "sel => !Array.from(document.querySelectorAll(sel))"
    ".some(el => el.getClientRects().length > 0)"
)
_ALGUM_HABILITADO = (
    "sel => Array.from(document.querySelectorAll(sel))"
    ".some(el => el.getClientRects().length > 0 && !el.disabled"
    " && el.getAttribute('aria-disabled') !== 'true')"
)
_CLIQUE_JS = (
    "sel => { const el = Array.from(document.querySelectorAll(sel))"
    ".find(e => e.getClientRects().length > 0);"
    " if (!el) return false; el.click(); return true; }"
)


def _ctx(driver):
    """Contexto Playwright do driver, ou None se nao for um PWDriver."""
    return driver._ctx if isinstance(driver, PWDriver) else None


def _ms(timeout):
    return int(float(timeout) * 1000)


def _delegar(nome, *args, **kwargs):
    original = _ORIGINAIS.get(nome)
    if original is None:
        return None
    return original(*args, **kwargs)


# -- esperas ----------------------------------------------------------------

def aguardar_renderizacao_nativa(driver, seletor=None, modo="aparecer", timeout=10):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("aguardar_renderizacao_nativa", driver, seletor, modo, timeout)
    try:
        if not seletor:
            driver.page.wait_for_load_state("load", timeout=_ms(timeout))
            return True
        expressao = {
            "sumir": _NENHUM_VISIVEL,
            "habilitado": _ALGUM_HABILITADO,
        }.get(modo, _ALGUM_VISIVEL)
        ctx.wait_for_function(expressao, arg=seletor, timeout=_ms(timeout))
        return True
    except Exception:
        return False


def wait_for_page_load(driver, timeout=10):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("wait_for_page_load", driver, timeout)
    try:
        driver.page.wait_for_load_state("load", timeout=_ms(timeout))
        return True
    except Exception:
        return False


def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR, log=False):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("esperar_elemento", driver, seletor, texto, timeout, by, log)
    alvo = traduzir_seletor(by, seletor)
    try:
        if texto:
            loc = ctx.locator(alvo).filter(has_text=texto).first
            loc.wait_for(state="attached", timeout=_ms(timeout))
            return PWElement(loc.element_handle(), driver.page)
        handle = ctx.wait_for_selector(alvo, state="attached", timeout=_ms(timeout))
        return PWElement(handle, driver.page) if handle else None
    except Exception:
        if log:
            logger.error("[ESPERAR][ERRO] Elemento nao encontrado: %s", seletor)
        return None


def wait_for_visible(driver, selector, timeout=10, by=None):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("wait_for_visible", driver, selector, timeout, by)
    try:
        handle = ctx.wait_for_selector(
            traduzir_seletor(by or By.CSS_SELECTOR, selector),
            state="visible", timeout=_ms(timeout),
        )
        return PWElement(handle, driver.page) if handle else None
    except Exception:
        return None


def wait_for_clickable(driver, selector, timeout=10, by=None):
    elemento = wait_for_visible(driver, selector, timeout=timeout, by=by)
    if elemento is None or not isinstance(driver, PWDriver):
        return elemento
    return elemento if elemento.is_enabled() else None


def esperar_url_conter(driver, substring, timeout=10):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("esperar_url_conter", driver, substring, timeout)
    try:
        driver.page.wait_for_url(
            lambda url: substring in (url or ""), timeout=_ms(timeout)
        )
        return True
    except Exception:
        return False


# -- cliques ----------------------------------------------------------------

def _clicar(driver, alvo, timeout, log, rotulo):
    """Clique JS-first: espera o elemento existir (attached) e clica via DOM.

    Nao usa o clique nativo do Playwright como caminho principal porque o
    gate de estabilidade dele depende de rAF — aba/janela inativa no Firefox
    nao dispara rAF e o clique trava o timeout inteiro. O clique via DOM
    dispara os handlers igual ao padrao Selenium (execute_script click).
    """
    try:
        handle = driver._ctx.wait_for_selector(
            alvo, state="attached", timeout=_ms(timeout)
        )
        if handle:
            handle.evaluate("el => el.click()")
            return True
    except Exception as e:
        try:
            if driver._ctx.evaluate(_CLIQUE_JS, alvo):
                if log:
                    logger.debug("clique via DOM: %s", rotulo)
                return True
        except Exception:
            pass
        if log:
            logger.error("clique falhou em '%s': %s", rotulo, e)
        return False
    return False


def aguardar_e_clicar(driver, seletor, log=False, timeout=10, by=By.CSS_SELECTOR,
                      usar_js=True, retornar_elemento=False, debug=None):
    if debug is not None:
        log = debug
    if _ctx(driver) is None:
        return _delegar("aguardar_e_clicar", driver, seletor, log, timeout, by,
                        usar_js, retornar_elemento, debug)
    if retornar_elemento:
        return esperar_elemento(driver, seletor, timeout=timeout, by=by, log=log)
    return _clicar(driver, traduzir_seletor(by, seletor), timeout, log, seletor)


def click_headless_safe(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    if _ctx(driver) is None:
        return _delegar("click_headless_safe", driver, selector, by, timeout)
    return _clicar(driver, traduzir_seletor(by, selector), timeout, False, selector)


def safe_click(driver, selector_or_element, timeout=10, by=None, log=False):
    if _ctx(driver) is None:
        return _delegar("safe_click", driver, selector_or_element, timeout, by, log)
    if isinstance(selector_or_element, PWElement):
        return safe_click_no_scroll(driver, selector_or_element, log=log)
    return _clicar(driver, traduzir_seletor(by or By.CSS_SELECTOR, selector_or_element),
                   timeout, log, selector_or_element)


def safe_click_no_scroll(driver, element, log=False):
    if not isinstance(element, PWElement):
        return _delegar("safe_click_no_scroll", driver, element, log)
    try:
        # Estratégia: JS puro primeiro (garantido funcionar mesmo off-viewport),
        # fallback para nativo só se JS falhar (para compatibilidade com listeners especiais).
        # Isto espelha o padrão Selenium (dispatchEvent MouseEvent) que funciona
        # mesmo quando elemento está fora da viewport após scrollIntoView.
        try:
            element._handle.evaluate("el => el.click()")
            return True
        except Exception:
            # Fallback: tentar click nativo (pode falhar off-viewport, mas tenta)
            if element._handle.is_visible():
                element._handle.click(timeout=5000)
            else:
                raise
            return True
    except Exception as e:
        if log:
            logger.error("safe_click_no_scroll: %s", e)
        return False


def scroll_to_element_safe(driver, element):
    if not isinstance(element, PWElement):
        return _delegar("scroll_to_element_safe", driver, element)
    return element.scroll_into_view()


# -- formularios ------------------------------------------------------------

def preencher_campo(driver, seletor, valor, trigger_events=True, limpar=True, log=False):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("preencher_campo", driver, seletor, valor,
                        trigger_events, limpar, log)
    try:
        loc = ctx.locator(seletor).first
        if limpar:
            loc.fill(str(valor))
        else:
            loc.click()
            driver.page.keyboard.type(str(valor))
        if trigger_events:
            # fill ja dispara input/change; o blur fecha o ciclo do Angular.
            loc.evaluate("el => el.dispatchEvent(new Event('blur', {bubbles: true}))")
        return True
    except Exception as e:
        if log:
            logger.warning("preencher_campo '%s': %s", seletor, e)
        return False


def preencher_multiplos_campos(driver, campos_dict, log=False):
    if _ctx(driver) is None:
        return _delegar("preencher_multiplos_campos", driver, campos_dict, log)
    return {
        seletor: preencher_campo(driver, seletor, valor, log=log)
        for seletor, valor in campos_dict.items()
    }


def selecionar_opcao(driver, seletor_dropdown, texto_opcao, timeout=10,
                     exato=False, log=False):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("selecionar_opcao", driver, seletor_dropdown,
                        texto_opcao, timeout, exato, log)
    try:
        dropdown = ctx.locator(seletor_dropdown).first
        dropdown.wait_for(state="visible", timeout=_ms(timeout))

        if (dropdown.evaluate("el => el.tagName.toLowerCase()")) == "select":
            dropdown.select_option(label=texto_opcao)
            return True

        dropdown.click(timeout=_ms(timeout))
        opcoes = driver.page.locator("mat-option, [role='option']")
        opcoes.first.wait_for(state="visible", timeout=_ms(timeout))
        alvo = (opcoes.get_by_text(texto_opcao, exact=True) if exato
                else opcoes.filter(has_text=texto_opcao))
        alvo.first.click(timeout=_ms(timeout))
        return True
    except Exception as e:
        if log:
            logger.error("selecionar_opcao '%s' -> '%s': %s",
                         seletor_dropdown, texto_opcao, e)
        return False


def ate_js(driver, expressao, teto=2.0):
    """Versão orientada a evento de `Fix.espera.ate_js` (rAF, sem poll)."""
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("ate_js", driver, expressao, teto)
    # Import tardio: Fix não pode ser carregado antes de `instalar()`.
    from Fix.espera import _JS_ELEMENTOS
    try:
        ctx.wait_for_function(
            "() => { %s return !!(%s); }" % (_JS_ELEMENTOS, expressao),
            timeout=_ms(teto),
        )
        return True
    except Exception:
        return False


# "Assentou" no PJe = Angular estável e nenhum spinner visível.
#
# A quiescência precisa PERSISTIR. Logo após um clique o Angular fica
# momentaneamente estável — a requisição ainda nem saiu — e um teste
# instantâneo retornaria na hora, entregando ao chamador uma tela que ainda vai
# mudar. O `sleep` que esta função substitui não tinha esse furo. Por isso
# exige-se estabilidade contínua por `_QUIESCENCIA_MS` antes de dar por
# assentado.
_QUIESCENCIA_MS = 150

_JS_ASSENTADO = """
(minimoMs) => {
  const agora = performance.now();
  const spin = document.querySelectorAll('mat-spinner, mat-progress-spinner, .mat-spinner');
  let ocupado = false;
  for (const s of spin) { if (s.getClientRects().length) { ocupado = true; break; } }
  if (!ocupado) {
    // Sem testabilities (build de produção) sobra o spinner — degrada, não trava.
    const t = window.getAllAngularTestabilities?.();
    if (t && t.length) ocupado = !t.every(x => x.isStable());
  }
  if (ocupado) { window.__pjeplayQuietoDesde = null; return false; }
  if (!window.__pjeplayQuietoDesde) { window.__pjeplayQuietoDesde = agora; return false; }
  return (agora - window.__pjeplayQuietoDesde) >= minimoMs;
}
"""


def assentar(driver, teto=2.0, motivo=""):
    """Versão Playwright de `Fix.espera.assentar`: espera assentar de verdade.

    Onde o Selenium dorme o teto inteiro, aqui retorna assim que a interface
    fica quieta de forma sustentada — mesmo teto, custo real bem menor.
    """
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("assentar", driver, teto, motivo)

    minimo = min(_QUIESCENCIA_MS, _ms(teto) // 2)
    try:
        # Zera o marcador: sobra da chamada anterior daria quiescência falsa.
        ctx.evaluate("() => { window.__pjeplayQuietoDesde = null; }")
        ctx.wait_for_function(_JS_ASSENTADO, arg=minimo, timeout=_ms(teto))
        return True
    except Exception:
        return False  # não assentou dentro do teto: mesmo desfecho do sleep


def elemento(driver, seletor, teto=10, visivel=True):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("elemento", driver, seletor, teto, visivel)
    try:
        handle = ctx.wait_for_selector(
            seletor, state="visible" if visivel else "attached", timeout=_ms(teto)
        )
        return PWElement(handle, driver.page) if handle else None
    except Exception:
        return None


def elementos(driver, seletor, teto=10):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("elementos", driver, seletor, teto)
    try:
        ctx.wait_for_selector(seletor, state="attached", timeout=_ms(teto))
    except Exception:
        return []
    try:
        handles = ctx.query_selector_all(seletor)
        return [PWElement(h, driver.page) for h in handles]
    except Exception:
        return []


def ate_url(driver, trecho, teto=10):
    ctx = _ctx(driver)
    if ctx is None:
        return _delegar("ate_url", driver, trecho, teto)
    try:
        driver.page.wait_for_url(lambda u: trecho in (u or ""), timeout=_ms(teto))
        return True
    except Exception:
        return False


def ate_abas(driver, quantidade, teto=10):
    if _ctx(driver) is None:
        return _delegar("ate_abas", driver, quantidade, teto)
    limite = _ms(teto)
    passo = 0.1
    decorrido = 0.0
    while len(driver.window_handles) != quantidade and decorrido * 1000 < limite:
        driver.pulsar(passo)
        decorrido += passo
    return len(driver.window_handles) == quantidade


def ate_obsoleto(driver, elemento, teto=10):
    if _ctx(driver) is None:
        return _delegar("ate_obsoleto", driver, elemento, teto)
    # Locator re-resolve a cada uso: obsolescência praticamente não ocorre.
    return True


def is_headless_mode(driver):
    if isinstance(driver, PWDriver):
        return bool(driver.headless)
    return _delegar("is_headless_mode", driver)


# -- instalacao -------------------------------------------------------------

_ALVOS = {
    "Fix.core": [
        "aguardar_renderizacao_nativa", "wait_for_page_load", "esperar_elemento",
        "wait_for_visible", "wait_for_clickable", "esperar_url_conter",
        "aguardar_e_clicar", "safe_click", "safe_click_no_scroll",
        "preencher_campo", "preencher_multiplos_campos", "selecionar_opcao",
    ],
    "Fix.browser_suporte": [
        "click_headless_safe", "safe_click_no_scroll", "scroll_to_element_safe",
        "is_headless_mode",
    ],
    "Fix.facade_publica": [
        "aguardar_renderizacao_nativa", "esperar_elemento", "aguardar_e_clicar",
        "safe_click",
    ],
    "Fix.utils": ["aguardar_e_clicar"],
    # espera.py liga o nome no import; sem isto ficaria com a versão Selenium.
    "Fix.espera": [
        "ate_js", "assentar", "elemento", "elementos", "ate_url",
        "ate_abas", "ate_obsoleto",
    ],
}


def aplicar():
    """Troca os helpers de Fix/ pelas versoes nativas. Idempotente.

    Deve rodar depois de `import Fix.core` e antes de importar os modulos de
    negocio — quem faz `from Fix.core import esperar_elemento` fixa o nome no
    momento do import.
    """
    import importlib

    trocados = 0
    for modulo, nomes in _ALVOS.items():
        try:
            mod = importlib.import_module(modulo)
        except Exception:
            continue
        for nome in nomes:
            novo = globals().get(nome)
            antigo = getattr(mod, nome, None)
            if novo is None or antigo is novo:
                continue
            _ORIGINAIS.setdefault(nome, antigo)
            setattr(mod, nome, novo)
            trocados += 1
    logger.info("pjeplay: %d helpers trocados pelo caminho nativo", trocados)
    return trocados
