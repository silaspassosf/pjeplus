"""
atos.anexos.wrappers - Wrappers específicos para juntada.

Reexporta de PEC/anexos.anexos_wrappers.
Esta camada será autossuficiente na fase final da migração.
"""

import logging
logger = logging.getLogger(__name__)

from typing import Optional, Callable, Any
from selenium.webdriver.remote.webdriver import WebDriver

from PEC.anexos.anexos_wrappers import (
    anex_carta,
    anex_sisbconsulta,
    anex_bloqneg,
    anex_parcial,
    anex_retifidpj,
)
