"""Compatibilidade mínima para o namespace legado Fix.smart_finder."""

from selenium.webdriver.common.by import By


def buscar(driver, cache_key, seletores):
    """Busca sequencial simples por CSS ou XPath.

    `cache_key` é mantido só por compatibilidade de assinatura.
    """
    _ = cache_key
    for seletor in seletores or []:
        try:
            by = By.XPATH if isinstance(seletor, str) and seletor.startswith("//") else By.CSS_SELECTOR
            elementos = driver.find_elements(by, seletor)
            for elemento in elementos:
                try:
                    if elemento.is_displayed():
                        return elemento
                except Exception:
                    continue
            if elementos:
                return elementos[0]
        except Exception:
            continue
    return None


__all__ = ["buscar"]