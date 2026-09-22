"""WebDriverWait e expected_conditions compativeis.

Caminho de compatibilidade: preserva os ~241 `WebDriverWait` e ~186 `EC.*` do
codigo atual. O caminho rapido (auto-wait nativo do Playwright) fica em
`pjeplay.nativo`, que substitui os helpers quentes de `Fix/core.py`.
"""
import time

from .errors import (
    NoAlertPresentException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

IGNORADAS_PADRAO = (NoSuchElementException,)


class WebDriverWait:
    def __init__(self, driver, timeout, poll_frequency=0.5,
                 ignored_exceptions=None):
        self._driver = driver
        self._timeout = float(timeout)
        self._poll = max(float(poll_frequency or 0.05), 0.02)
        ignoradas = list(IGNORADAS_PADRAO)
        if ignored_exceptions:
            if isinstance(ignored_exceptions, (list, tuple, set)):
                ignoradas.extend(ignored_exceptions)
            else:
                ignoradas.append(ignored_exceptions)
        self._ignoradas = tuple(ignoradas)

    def _dormir(self):
        """Espera o intervalo de poll cedendo tempo ao loop do Playwright."""
        pulsar = getattr(self._driver, "pulsar", None)
        if pulsar is None:
            time.sleep(self._poll)
        else:
            pulsar(self._poll)

    def until(self, metodo, message=""):
        return self._laco(metodo, message, negar=False)

    def until_not(self, metodo, message=""):
        return self._laco(metodo, message, negar=True)

    def _laco(self, metodo, message, negar):
        ultimo = None
        limite = time.monotonic() + self._timeout
        while True:
            try:
                valor = metodo(self._driver)
                if negar:
                    if not valor:
                        return valor
                elif valor:
                    return valor
            except self._ignoradas as e:
                ultimo = e
                if negar:
                    return True
            except StaleElementReferenceException as e:
                ultimo = e
            if time.monotonic() >= limite:
                break
            self._dormir()
        alvo = message or f"aguardando {getattr(metodo, '__name__', metodo)}"
        raise TimeoutException(f"Timeout apos {self._timeout}s: {alvo}") from ultimo


# --- expected_conditions ---------------------------------------------------

def _achar(driver, locator):
    return driver.find_element(*locator)


def _achar_todos(driver, locator):
    return driver.find_elements(*locator)


def presence_of_element_located(locator):
    def _cond(driver):
        try:
            return _achar(driver, locator)
        except NoSuchElementException:
            return False
    return _cond


def presence_of_all_elements_located(locator):
    def _cond(driver):
        return _achar_todos(driver, locator) or False
    return _cond


def visibility_of_element_located(locator):
    def _cond(driver):
        try:
            el = _achar(driver, locator)
        except NoSuchElementException:
            return False
        return el if el.is_displayed() else False
    return _cond


def visibility_of_all_elements_located(locator):
    def _cond(driver):
        els = _achar_todos(driver, locator)
        return els if els and all(e.is_displayed() for e in els) else False
    return _cond


def visibility_of(elemento):
    def _cond(_driver):
        try:
            return elemento if elemento.is_displayed() else False
        except StaleElementReferenceException:
            return False
    return _cond


def invisibility_of_element_located(locator):
    def _cond(driver):
        try:
            els = _achar_todos(driver, locator)
            return True if not els else not any(e.is_displayed() for e in els)
        except (NoSuchElementException, StaleElementReferenceException):
            return True
    return _cond


invisibility_of_element = invisibility_of_element_located


def element_to_be_clickable(locator_ou_elemento):
    def _cond(driver):
        if isinstance(locator_ou_elemento, (tuple, list)):
            cond = visibility_of_element_located(tuple(locator_ou_elemento))
            el = cond(driver)
        else:
            el = locator_ou_elemento
            if not el.is_displayed():
                return False
        return el if el and el.is_enabled() else False
    return _cond


def text_to_be_present_in_element(locator, texto):
    def _cond(driver):
        try:
            return texto in _achar(driver, locator).text
        except (NoSuchElementException, StaleElementReferenceException):
            return False
    return _cond


def text_to_be_present_in_element_value(locator, texto):
    def _cond(driver):
        try:
            return texto in (_achar(driver, locator).get_attribute("value") or "")
        except (NoSuchElementException, StaleElementReferenceException):
            return False
    return _cond


def element_located_to_be_selected(locator):
    def _cond(driver):
        try:
            return _achar(driver, locator).is_selected()
        except NoSuchElementException:
            return False
    return _cond


element_to_be_selected = element_located_to_be_selected


def element_selection_state_to_be(elemento, estado):
    def _cond(_driver):
        return elemento.is_selected() == estado
    return _cond


def staleness_of(elemento):
    def _cond(_driver):
        try:
            elemento.is_enabled()
            return False
        except (StaleElementReferenceException, WebDriverException):
            return True
    return _cond


def url_contains(trecho):
    def _cond(driver):
        return trecho in (driver.current_url or "")
    return _cond


def url_to_be(url):
    def _cond(driver):
        return driver.current_url == url
    return _cond


def url_matches(padrao):
    import re

    def _cond(driver):
        return bool(re.search(padrao, driver.current_url or ""))
    return _cond


def title_is(titulo):
    def _cond(driver):
        return driver.title == titulo
    return _cond


def title_contains(trecho):
    def _cond(driver):
        return trecho in (driver.title or "")
    return _cond


def number_of_windows_to_be(quantidade):
    def _cond(driver):
        return len(driver.window_handles) == quantidade
    return _cond


def new_window_is_opened(handles_originais):
    def _cond(driver):
        return len(driver.window_handles) > len(handles_originais)
    return _cond


def alert_is_present():
    def _cond(driver):
        try:
            return driver.switch_to.alert
        except NoAlertPresentException:
            return False
    return _cond


def frame_to_be_available_and_switch_to_it(locator):
    def _cond(driver):
        try:
            referencia = locator[1] if isinstance(locator, (tuple, list)) else locator
            driver.switch_to.frame(referencia)
            return True
        except WebDriverException:
            return False
    return _cond


def any_of(*condicoes):
    def _cond(driver):
        for c in condicoes:
            try:
                r = c(driver)
                if r:
                    return r
            except WebDriverException:
                continue
        return False
    return _cond


def all_of(*condicoes):
    def _cond(driver):
        resultados = []
        for c in condicoes:
            try:
                r = c(driver)
            except WebDriverException:
                return False
            if not r:
                return False
            resultados.append(r)
        return resultados
    return _cond


def none_of(*condicoes):
    def _cond(driver):
        for c in condicoes:
            try:
                if c(driver):
                    return False
            except WebDriverException:
                continue
        return True
    return _cond
