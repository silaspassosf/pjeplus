"""Excecoes compativeis com selenium.common.exceptions.

O codigo de negocio do PJePlus captura estas excecoes por nome em ~100 pontos.
Manter a mesma hierarquia permite rodar o projeto sobre Playwright sem editar
nenhum modulo de negocio.
"""


class WebDriverException(Exception):
    def __init__(self, msg=None, screen=None, stacktrace=None):
        super().__init__(msg)
        self.msg = msg
        self.screen = screen
        self.stacktrace = stacktrace

    def __str__(self):
        return f"Message: {self.msg}\n" if self.msg else ""


class InvalidSwitchToTargetException(WebDriverException):
    pass


class NoSuchFrameException(InvalidSwitchToTargetException):
    pass


class NoSuchWindowException(InvalidSwitchToTargetException):
    pass


class NoSuchElementException(WebDriverException):
    pass


class NoSuchAttributeException(WebDriverException):
    pass


class StaleElementReferenceException(WebDriverException):
    pass


class InvalidElementStateException(WebDriverException):
    pass


class UnexpectedAlertPresentException(WebDriverException):
    pass


class NoAlertPresentException(WebDriverException):
    pass


class ElementNotVisibleException(InvalidElementStateException):
    pass


class ElementNotInteractableException(InvalidElementStateException):
    pass


class ElementNotSelectableException(InvalidElementStateException):
    pass


class ElementClickInterceptedException(WebDriverException):
    pass


class TimeoutException(WebDriverException):
    pass


class MoveTargetOutOfBoundsException(WebDriverException):
    pass


class JavascriptException(WebDriverException):
    pass


class InvalidSelectorException(WebDriverException):
    pass


class InvalidArgumentException(WebDriverException):
    pass


class InvalidSessionIdException(WebDriverException):
    pass


class SessionNotCreatedException(WebDriverException):
    pass


class InvalidCookieDomainException(WebDriverException):
    pass


class UnableToSetCookieException(WebDriverException):
    pass


class ScreenshotException(WebDriverException):
    pass


class UnexpectedTagNameException(WebDriverException):
    pass


class InsecureCertificateException(WebDriverException):
    pass


class NoSuchDriverException(WebDriverException):
    pass


class NoSuchShadowRootException(WebDriverException):
    pass


class NoSuchCookieException(WebDriverException):
    pass


# Sinais internos do Playwright que devem virar excecoes Selenium ------------

_DETACHED_HINTS = (
    "element is not attached",
    "node is detached",
    "target closed",
    "element handle is disposed",
)

_INTERCEPTED_HINTS = (
    "intercepts pointer events",
    "element is outside of the viewport",
    "subtree intercepts",
)

_FATAL_HINTS = (
    "browser has been closed",
    "target page, context or browser has been closed",
    "browsing context",
)


def traduzir(exc, seletor=None):
    """Converte uma excecao Playwright na excecao Selenium equivalente."""
    from playwright.sync_api import Error as PWError
    from playwright.sync_api import TimeoutError as PWTimeout

    msg = str(exc)
    baixo = msg.lower()

    if isinstance(exc, PWTimeout):
        return TimeoutException(f"{seletor or ''}: {msg}".strip(": "))
    if any(h in baixo for h in _DETACHED_HINTS):
        return StaleElementReferenceException(msg)
    if any(h in baixo for h in _INTERCEPTED_HINTS):
        return ElementClickInterceptedException(msg)
    if any(h in baixo for h in _FATAL_HINTS):
        return InvalidSessionIdException(msg)
    if isinstance(exc, PWError):
        return WebDriverException(msg)
    return exc
