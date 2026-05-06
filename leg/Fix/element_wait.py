"""Compatibilidade mínima para o namespace legado Fix.element_wait."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ElementWaitPool:
    """Pool mínimo de waits consistente com os consumidores ativos."""

    def __init__(self, driver, explicit_wait: int = 10):
        self.driver = driver
        self.explicit_wait = explicit_wait

    def esperar_elemento(self, selector, timeout=None, by=By.CSS_SELECTOR):
        return WebDriverWait(self.driver, timeout or self.explicit_wait).until(
            EC.presence_of_element_located((by, selector))
        )

    def esperar_visivel(self, selector, timeout=None, by=By.CSS_SELECTOR):
        return WebDriverWait(self.driver, timeout or self.explicit_wait).until(
            EC.visibility_of_element_located((by, selector))
        )

    def esperar_clicavel(self, selector, timeout=None, by=By.CSS_SELECTOR):
        return WebDriverWait(self.driver, timeout or self.explicit_wait).until(
            EC.element_to_be_clickable((by, selector))
        )
