"""
PEC.anexos.gigs - Módulo de funções específicas GIGS plugin.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém funções específicas do GIGS plugin para manipulação de elementos.
"""

import logging
logger = logging.getLogger(__name__)

import os
import re
import time
from typing import Optional, Dict, Any, Callable, Union, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix.core import (
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
)