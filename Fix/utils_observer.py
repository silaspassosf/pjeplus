import time as _time
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.log import logger


def aguardar_renderizacao_nativa(driver: WebDriver, seletor: str, modo: str = "aparecer", timeout: int = 10) -> bool:
    """
    Aguarda o DOM atingir a condicao desejada via polling de execute_script sincrono.

    Padrao: gigs-plugin.js esperarColecao/esperarElemento — execute_script retorna
    imediatamente a cada check; o Python faz o loop. Nao usa execute_async_script
    (que quebra com "Document was unloaded" em overlays Angular CDK / mat-select).

    modo:
      'aparecer'  - elemento visivel (offsetParent != null)
      'sumir'     - elemento ausente ou invisivel
      'habilitado'- elemento visivel E sem atributo disabled
    """
    logger.debug(f"[OBSERVER] Vigiando '{seletor}' (modo: {modo}) timeout={timeout}s")

    _CHECAR = (
        "var s=arguments[0],m=arguments[1];"
        "var els=Array.from(document.querySelectorAll(s));"
        "if(m==='sumir') return els.every(function(e){return e.offsetParent===null;})||els.length===0;"
        "if(m==='habilitado') return els.some(function(e){return e.offsetParent!==null&&!e.disabled&&!e.hasAttribute('disabled');});"
        "return els.some(function(e){return e.offsetParent!==null;});"
    )

    fim = _time.monotonic() + timeout
    while _time.monotonic() < fim:
        try:
            if driver.execute_script(_CHECAR, seletor, modo):
                return True
        except Exception:
            pass
        _time.sleep(0.05)

    logger.debug(f"[OBSERVER] Timeout '{seletor}' modo={modo} {timeout}s")
    return False


def aguardar_colecao_sync(driver: WebDriver, seletor: str, qtde_minima: int = 1, timeout: int = 10) -> bool:
    """Alias semantico de aguardar_renderizacao_nativa para colecoes com qtde minima."""
    script = "return document.querySelectorAll(arguments[0]).length>=arguments[1];"
    fim = _time.monotonic() + timeout
    while _time.monotonic() < fim:
        try:
            if driver.execute_script(script, seletor, qtde_minima):
                return True
        except Exception:
            pass
        _time.sleep(0.05)
    logger.debug(f"[OBSERVER_SYNC] Timeout '{seletor}' min={qtde_minima} {timeout}s")
    return False
