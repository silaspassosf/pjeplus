"""pjeplay.api_resiliencia - resiliencia global das chamadas API do PJe."""
import logging
import threading

import requests

logger = logging.getLogger("pjeplay")

_lock = threading.Lock()
_driver_ativo = None
_instalado = False

_TENTATIVAS = 2
_PAUSA = 3.0
_HOSTS = ("jus.br",)


def registrar_driver(driver):
    """Registra o driver ativo (chamado pelo launcher ao criar driver)."""
    global _driver_ativo
    _driver_ativo = driver


def _driver():
    d = _driver_ativo
    if d is None:
        return None
    try:
        d.current_url
        return d
    except Exception:
        return None


def _f5_e_aguardar(driver):
    """F5 na pagina ativa e espera o documento recarregar."""
    try:
        url_atual = (getattr(driver, 'current_url', '') or '').lower()
        if 'acesso-negado' in url_atual or 'login' in url_atual:
            logger.warning("api_resiliencia: F5 ignorado pois driver ja esta em tela de erro (%s)", url_atual[:80])
            return
        driver.refresh()
    except Exception as e:
        logger.warning("api_resiliencia: refresh falhou (%s)", e)
        return
    if hasattr(driver, 'page') and driver.page is not None:
        try:
            driver.page.wait_for_load_state("load", timeout=15000)
            return
        except Exception:
            pass
    from Fix import espera  # import tardio: nunca importar Fix antes de pjeplay.iniciar()
    espera.ate_js(driver, "document.readyState === 'complete'", teto=15)


def _ressincronizar_cookies(driver, sess):
    try:
        for c in (driver.get_cookies() or []):
            sess.cookies.set(c.get("name"), c.get("value"), domain=c.get("domain"))
    except Exception:
        pass


def instalar():
    """Envelopa requests.Session.request uma unica vez (idempotente)."""
    global _instalado
    with _lock:
        if _instalado:
            return True
        original = requests.Session.request

        def request(self, method, url, *args, **kwargs):
            resp = original(self, method, url, *args, **kwargs)
            alvo = (url if isinstance(url, str) else str(url)).lower()
            if (
                resp.status_code >= 500
                and str(method).upper() == "GET"
                and any(h in alvo for h in _HOSTS)
            ):
                driver = _driver()
                for tentativa in range(1, _TENTATIVAS + 1):
                    logger.warning(
                        "api_resiliencia: HTTP %d em GET %s - F5 e retry %d/%d",
                        resp.status_code, alvo, tentativa, _TENTATIVAS,
                    )
                    if driver is None:
                        break
                    _f5_e_aguardar(driver)
                    _ressincronizar_cookies(driver, self)
                    from Fix import espera
                    espera.pausa(driver, _PAUSA)
                    resp = original(self, method, url, *args, **kwargs)
                    if resp.status_code < 500:
                        break
            return resp

        requests.Session.request = request
        _instalado = True
        return True
