"""pjeplay.api_resiliencia - resiliencia global das chamadas API do PJe.

Envelopa `requests.Session.request` para TODO o processo rodando sob o
pw.py: qualquer fluxo (P2B, PEC, Mandado, SISB, Peticao, bianca, ...) que
receba 5xx da API do PJe em um GET dispara F5 na pagina ativa (reload do
processo), ressincroniza cookies do driver e repete a chamada.

Pontos de ancoragem (nao ha outro lugar a patchear):
- `instalar()`      -> chamado por `pjeplay.iniciar()` (antes de qualquer
                       import de negocio no pw.py).
- `registrar_driver()` -> chamado por `launcher.criar_driver` (funil unico
                       de criacao de drivers).
"""
import logging
import threading
import time

import requests

logger = logging.getLogger("pjeplay")

_lock = threading.Lock()
_driver_ativo = None
_instalado = False

_TENTATIVAS = 2   # retries apos a 1a falha
_PAUSA = 3.0      # segundos antes de cada retry
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
        d.current_url  # sonda: driver vivo?
        return d
    except Exception:
        return None


def _f5_e_aguardar(driver):
    """F5 na pagina ativa e espera o documento recarregar."""
    try:
        driver.refresh()
    except Exception as e:
        logger.warning("api_resiliencia: refresh falhou (%s)", e)
        return
    for _ in range(30):  # ate ~15s
        try:
            if driver.execute_script("return document.readyState") == "complete":
                break
        except Exception:
            pass
        time.sleep(0.5)


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
                    time.sleep(_PAUSA)
                    resp = original(self, method, url, *args, **kwargs)
                    if resp.status_code < 500:
                        break
            return resp

        requests.Session.request = request
        _instalado = True
        return True
