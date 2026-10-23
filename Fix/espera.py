"""Módulo de espera explícita com condição."""
import re
import time
import traceback

from Play.pjeplay.locators import By

from Fix.diagnostico_runtime import logger

__all__ = [
    "ate", "ate_aparecer", "ate_sumir", "ate_habilitar", "ate_desabilitar",
    "ate_js", "ate_texto", "assentar", "pausa",
    "elemento", "elementos", "ate_url", "ate_abas", "ate_obsoleto",
]

_INTERVALO_POLL = 0.05


def ate(driver, condicao, teto=10, intervalo=_INTERVALO_POLL):
    """Aguarda até que `condicao(driver)` retorne truthy."""
    limite = time.monotonic() + float(teto)
    while True:
        try:
            res = condicao(driver)
            if res:
                return res
        except Exception:
            pass
        if time.monotonic() >= limite:
            return False
        _dormir(intervalo)


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
    ultimo_erro = None
    while True:
        try:
            if _executar_script(driver, script):
                return True
        except Exception as e:
            ultimo_erro = str(e)
        if time.monotonic() >= limite:
            _log_falha(expressao, teto, ultimo_erro or "timeout")
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


def _fluxo_do_chamador(detalhado=False):
    """Deduz o fluxo (mandado/p2b/pec/...) e o módulo que chamou a busca.

    A telemetria precisa saber ONDE o seletor foi usado; inspecionar um frame
    acima é barato e evita passar o fluxo por 285 chamadores.

    Com `detalhado=True` devolve (fluxo, módulo), e o módulo vai para o campo
    `contexto` — é ele que diz qual arquivo usa o seletor, informação que o
    catálogo precisa e que antes saía sempre como "geral".
    """
    try:
        import sys
        # Percorre a pilha até o primeiro módulo de fluxo conhecido. Não para no
        # primeiro frame estranho: o caminho real passa por Fix/*, Play/*, atos/*
        # e o topo costuma ser o Play — parar ali rotulava tudo como "pjeplay".
        ignorar = ("Fix.", "Play.", "pjeplay")
        f = sys._getframe(1)
        while f:
            nome = f.f_globals.get("__name__", "")
            if nome and not nome.startswith(ignorar):
                fluxo = None
                if nome.startswith(("Mandado",)):
                    fluxo = "mandado"
                elif nome.startswith(("Prazo",)):
                    fluxo = "p2b"
                elif nome.startswith(("PEC", "atos")):
                    fluxo = "pec"
                elif nome.startswith(("SISB",)):
                    fluxo = "sisb"
                elif nome.startswith(("bianca",)):
                    fluxo = "bianca"
                elif nome.startswith(("Triagem",)):
                    fluxo = "triagem"
                elif nome.startswith(("Peticao",)):
                    fluxo = "peticao"
                if fluxo:
                    return (fluxo, nome) if detalhado else fluxo
            f = f.f_back
    except Exception:
        pass
    return ("desconhecido", "") if detalhado else "desconhecido"


_CONTADORES = {}  # (fluxo, seletor, ok) -> [usos, tentativas, ms_total]


def _telemetria_busca(seletor, ok, tentativas=1, ms=0.0):
    """Registra a resolução do seletor na telemetria (nunca levanta).

    Fica aqui, em vez de em cada chamador, porque `elemento`/`elementos` são a
    porta única de busca no DOM — assim todo o código passa a emitir o seletor
    que de fato venceu, sem nenhuma alteração nos fluxos.

    Agrupa por (fluxo, seletor, ok): uma linha por seletor E por fluxo, não uma
    por busca. A primeira gravação já basta para o catálogo saber que aquele
    seletor existe naquele fluxo; as repetições só somam no contador `usos`.
    Antes a chave ignorava o fluxo, então o primeiro `tbody tr` do mandado
    silenciava todo o resto da execução.
    """
    try:
        if not seletor:
            return
        fluxo, modulo = _fluxo_do_chamador(detalhado=True)
        chave = (fluxo, seletor, bool(ok))
        reg = _CONTADORES.get(chave)
        if reg is not None:
            reg[0] += 1
            reg[1] += int(tentativas)
            reg[2] += float(ms)
            return
        _CONTADORES[chave] = [1, int(tentativas), float(ms)]
        from Fix.telemetria_seletores import registrar_resolucao
        # Grava o seletor também quando falha: saber QUAL seletor não achou é o
        # que alimenta a consolidação do catálogo. Antes ia None e virava "".
        registrar_resolucao("busca_dom", seletor,
                            fluxo=fluxo, origem="espera",
                            ok=ok, tentativas=tentativas, ms=ms,
                            contexto=modulo,
                            processo=_processo_do_driver(),
                            erro="" if ok else "elemento não encontrado")
    except Exception:
        pass


_ULTIMO_DRIVER = None


def _processo_do_driver():
    """Número do processo em execução, lido da URL (vazio se não houver).

    Usa o driver visto na última busca: subir a pilha atrás de `driver` falhava
    porque `_telemetria_busca` é chamada de dentro de `elemento`/`elementos`,
    onde a variável já não está no escopo alcançado — e o campo saía sempre "".
    """
    try:
        drv = _ULTIMO_DRIVER
        if drv is None:
            return ""
        url = getattr(drv, "current_url", "") or ""
        m = re.search(r"/processo/(\d+)", url)
        if m:
            return _numero_do_processo(url) or m.group(1)
    except Exception:
        pass
    return ""


def _numero_do_processo(url):
    """Número formatado (NNNNNNN-DD.AAAA.J.TR.OOOO) presente na URL, se houver."""
    try:
        m = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", url or "")
        return m.group(1) if m else ""
    except Exception:
        return ""


def elemento(driver, seletor, teto=10, visivel=True):
    """Espera aparecer elemento de `seletor`; devolve o elemento ou `None`.

    Use o retorno imediatamente: fica obsoleto se a tela re-renderizar.
    """
    global _ULTIMO_DRIVER
    _ULTIMO_DRIVER = driver
    by = By.XPATH if e_xpath(seletor) else By.CSS_SELECTOR
    limite = time.monotonic() + float(teto)
    inicio = time.monotonic()
    tentativas = 0
    while True:
        tentativas += 1
        try:
            for el in _find_elements(driver, by, seletor):
                if not visivel or el.is_displayed():
                    _telemetria_busca(seletor, True, tentativas, (time.monotonic() - inicio) * 1000)
                    return el
        except Exception as e:
            logger.debug("elemento: %s", e)
            _telemetria_busca(seletor, False, tentativas, (time.monotonic() - inicio) * 1000)
            return None
        if time.monotonic() >= limite:
            _telemetria_busca(seletor, False, tentativas, (time.monotonic() - inicio) * 1000)
            return None
        _dormir(_INTERVALO_POLL)


def elementos(driver, seletor, teto=10):
    """Espera aparecer ao menos um elemento de `seletor`; devolve a lista
    (vazia se nada aparecer dentro do teto)."""
    global _ULTIMO_DRIVER
    _ULTIMO_DRIVER = driver
    by = By.XPATH if e_xpath(seletor) else By.CSS_SELECTOR
    limite = time.monotonic() + float(teto)
    inicio = time.monotonic()
    tentativas = 0
    while True:
        tentativas += 1
        try:
            els = _find_elements(driver, by, seletor)
            if els:
                _telemetria_busca(seletor, True, tentativas, (time.monotonic() - inicio) * 1000)
                return els
        except Exception as e:
            logger.debug("elementos: %s", e)
            _telemetria_busca(seletor, False, tentativas, (time.monotonic() - inicio) * 1000)
            return []
        if time.monotonic() >= limite:
            _telemetria_busca(seletor, False, tentativas, (time.monotonic() - inicio) * 1000)
            return []
        _dormir(_INTERVALO_POLL)


def ate_url(driver, trecho, teto=10):
    """Espera a URL corrente conter `trecho`."""
    limite = time.monotonic() + float(teto)
    trecho_alvo = (trecho or "").lower()
    while True:
        try:
            if trecho_alvo in (driver.current_url or "").lower():
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
