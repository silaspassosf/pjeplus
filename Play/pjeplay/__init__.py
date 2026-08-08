"""pjeplay — backend Playwright para o PJePlus.

Nao e um fork do projeto: e uma camada que implementa a superficie WebDriver
sobre o Playwright. O codigo de negocio (Fix/, atos/, PEC/, Prazo/, Mandado/,
SISB/, Peticao/, Triagem/, bianca/) roda sem uma linha alterada, entao toda
atualizacao feita no projeto Selenium vale automaticamente aqui.

Uso tipico:

    import pjeplay
    pjeplay.iniciar()                      # antes de qualquer import do projeto

    from Fix.core import criar_driver_PC   # ja devolve um driver Playwright
    driver = criar_driver_PC(headless=False)

Ou criando o driver direto pelo launcher, com as opcoes novas:

    driver = pjeplay.criar_driver_PC(headless=True, bloquear_midia=True)
"""
import logging
import sys

from .actions import ActionChains, Select
from .compat import instalar
from .driver import PWDriver
from .element import PWElement
from .launcher import (
    criar_driver,
    criar_driver_notebook,
    criar_driver_PC,
    criar_driver_sisb_pc,
    criar_driver_sisb_vt,
    criar_driver_VT,
    finalizar_driver,
)
from .locators import By, Keys
from .waits import WebDriverWait

__all__ = [
    "iniciar", "instalar", "PWDriver", "PWElement", "By", "Keys",
    "WebDriverWait", "ActionChains", "Select", "criar_driver",
    "criar_driver_PC", "criar_driver_VT", "criar_driver_notebook",
    "criar_driver_sisb_pc", "criar_driver_sisb_vt", "finalizar_driver",
]

__version__ = "1.0.0"

logger = logging.getLogger("pjeplay")


def iniciar(raiz_projeto=None, nativo=True, silencioso=False):
    """Ativa o backend Playwright para o projeto inteiro.

    1. troca `selenium` pelo backend Playwright;
    2. carrega `Fix.core` / `Fix.browser_suporte` ja sobre esse backend;
    3. (nativo=True) troca os helpers quentes pelo auto-wait do Playwright.

    Chame antes de importar qualquer modulo de negocio: `from Fix.core import X`
    fixa o nome no momento do import.
    """
    if raiz_projeto and raiz_projeto not in sys.path:
        sys.path.insert(0, raiz_projeto)

    instalar(silencioso=silencioso)

    import importlib
    for modulo in ("Fix.core", "Fix.browser_suporte", "Fix.utils"):
        try:
            importlib.import_module(modulo)
        except Exception as e:
            logger.warning("iniciar: %s nao carregou (%s)", modulo, e)

    if nativo:
        from .nativo import aplicar
        aplicar()
    return True
