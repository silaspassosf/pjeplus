from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from Fix.log import logger


def aguardar_renderizacao_nativa(driver: WebDriver, seletor: str, modo: str = "aparecer", timeout: int = 10) -> bool:
    """
    Injeta um MutationObserver no browser e aguarda o DOM mudar.

    modo: 'aparecer' | 'sumir'
    Retorna True se a condição for atingida dentro do timeout, False caso contrário.
    """
    logger.debug(f"[OBSERVER] Vigiando '{seletor}' (modo: {modo}) timeout={timeout}s")
    try:
        driver.set_script_timeout(timeout + 2)
    except Exception:
        pass

    script_js = r"""
        var seletor = arguments[0];
        var modo = arguments[1];
        var timeoutMs = arguments[2] * 1000;
        var callback = arguments[arguments.length - 1];

        try {
            var elementos = document.querySelectorAll(seletor);
            var visiveis = Array.from(elementos).filter(e => window.getComputedStyle(e).display !== 'none');

            if (modo === 'aparecer' && visiveis.length > 0) { callback(true); return; }
            if (modo === 'sumir' && visiveis.length === 0) { callback(true); return; }

            var observer = new MutationObserver(function(mutations, me) {
                try {
                    var elAgora = document.querySelectorAll(seletor);
                    var visAgora = Array.from(elAgora).filter(e => window.getComputedStyle(e).display !== 'none');
                    if (modo === 'aparecer' && visAgora.length > 0) { me.disconnect(); callback(true); }
                    else if (modo === 'sumir' && visAgora.length === 0) { me.disconnect(); callback(true); }
                } catch (e) {
                    // swallow and continue
                }
            });

            observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class'] });

            setTimeout(function() { try { observer.disconnect(); } catch(e){}; callback(false); }, timeoutMs);
        } catch (err) {
            callback(false);
        }
    """

    try:
        resultado = driver.execute_async_script(script_js, seletor, modo, int(timeout))
        return bool(resultado)
    except TimeoutException:
        logger.debug(f"[OBSERVER] Timeout executando script async para '{seletor}'")
        return False
    except Exception as e:
        logger.error(f"[OBSERVER] Erro ao injetar MutationObserver: {e}")
        return False
