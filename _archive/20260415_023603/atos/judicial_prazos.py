"""judicial_prazos.py - Funções de preenchimento de prazos

Este módulo reexporta a função `preencher_prazos_destinatarios` implementada
em `atos.judicial_utils` para evitar duplicação de código.
"""

from Fix.core import logger
from selenium.webdriver.common.by import By

# Reexportar a implementação centralizada em judicial_utils
from atos.judicial_utils import preencher_prazos_destinatarios

__all__ = ["preencher_prazos_destinatarios"]
