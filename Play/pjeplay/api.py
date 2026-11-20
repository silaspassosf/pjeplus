"""E3 — acesso à API do PJe pelo caminho nativo do Playwright."""
import json as _json
import logging

logger = logging.getLogger("pjeplay")


def requisicao(driver):
    """`APIRequestContext` do contexto do browser (auth compartilhada)."""
    return driver.context.request


def sessao(driver, grau=1):
    """`(requests.Session, trt_host)` — atalho para o caminho compatível."""
    from Fix.variaveis import session_from_driver

    return session_from_driver(driver, grau=grau)


def obter_json(driver, url, **kwargs):
    """GET pelo contexto do browser, devolvendo JSON (ou None)."""
    try:
        resposta = requisicao(driver).get(url, **kwargs)
        if not resposta.ok:
            logger.warning("obter_json %s -> HTTP %s", url, resposta.status)
            return None
        return resposta.json()
    except Exception as e:
        logger.warning("obter_json %s: %s", url, e)
        return None


def esperar_resposta(driver, padrao, acao, timeout=15):
    """Executa `acao` e devolve a resposta de rede que casa com `padrao`."""
    with driver.page.expect_response(padrao, timeout=int(timeout * 1000)) as info:
        acao()
    return info.value


def esperar_conclusao(driver, padrao, acao, timeout=15):
    """Igual a `esperar_resposta`, mas só confirma a conclusão (bool)."""
    try:
        resposta = esperar_resposta(driver, padrao, acao, timeout=timeout)
        return bool(resposta.ok)
    except Exception as e:
        logger.warning("esperar_conclusao %s: %s", padrao, e)
        return False


def corpo(resposta):
    """Corpo da resposta como dict/list, ou texto se não for JSON."""
    try:
        return resposta.json()
    except Exception:
        try:
            return resposta.text()
        except Exception:
            return None


def registrar_trafego(driver, filtro=None):
    """Coleta as respostas da API durante um trecho, para diagnóstico."""
    import contextlib

    coletadas = []

    def _ao_responder(resposta):
        if filtro is None or filtro in resposta.url:
            coletadas.append((resposta.status, resposta.url))

    @contextlib.contextmanager
    def _ctx():
        driver.page.on("response", _ao_responder)
        try:
            yield coletadas
        finally:
            driver.page.remove_listener("response", _ao_responder)

    return _ctx()


__all__ = [
    "requisicao", "sessao", "obter_json", "esperar_resposta",
    "esperar_conclusao", "corpo", "registrar_trafego",
]
