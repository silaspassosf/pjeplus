import logging
logger = logging.getLogger(__name__)

"""
@module: Fix.selenium_base
@responsibility: Operações fundamentais Selenium (espera, clique, interação)
@depends_on: selenium.webdriver
@used_by: Todos os módulos do projeto
@entry_points: aguardar_e_clicar, safe_click, selecionar_opcao, com_retry
@tags: #selenium #webdriver #wait #click #interaction
"""

# =============================
# 1. WAIT OPERATIONS
# =============================
from .wait_operations import (
    wait,
    wait_for_visible,
    wait_for_clickable,
    esperar_elemento,
    esperar_url_conter
)

# =============================
# 2. CLICK OPERATIONS
# =============================
from .click_operations import (
    aguardar_e_clicar
)

# =============================
# 2. ELEMENT INTERACTION
# =============================
from .element_interaction import (
    safe_click,
    preencher_campos_prazo
)

# =============================
# 3. FIELD OPERATIONS
# =============================
from .field_operations import (
    preencher_campo
)

# =============================
# 4. DRIVER OPERATIONS
# =============================
from .driver_operations import (
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver,
    salvar_cookies_sessao,
    carregar_cookies_sessao,
    credencial
)

# =============================
# 4. SMART SELECTION
# =============================
from .smart_selection import (
    selecionar_opcao,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente,
    buscar_seletor_robusto
)

# =============================
# 5. JS HELPERS
# =============================
from .js_helpers import (
    js_base
)

# =============================
# 6. RETRY LOGIC
# =============================
from .retry_logic import (
    com_retry
)

__all__ = [
    # wait_operations.py (5 funções)
    'wait',
    'wait_for_visible',
    'wait_for_clickable',
    'esperar_elemento',
    'esperar_url_conter',
    
    # click_operations.py (1 função)
    'aguardar_e_clicar',
    
    # element_interaction.py (2 funções públicas)
    'safe_click',
    'preencher_campos_prazo',
    
    # field_operations.py (1 função)
    'preencher_campo',
    
    # driver_operations.py (9 funções)
    'criar_driver_PC',
    'criar_driver_VT',
    'criar_driver_notebook',
    'criar_driver_sisb_pc',
    'criar_driver_sisb_notebook',
    'finalizar_driver',
    'salvar_cookies_sessao',
    'carregar_cookies_sessao',
    'credencial',
    
    # retry_logic.py (1 função)
    'com_retry',
    
    # smart_selection.py (4 funções)
    'selecionar_opcao',
    'escolher_opcao_inteligente',
    'encontrar_elemento_inteligente',
    'buscar_seletor_robusto',
    
    # js_helpers.py (1 função)
    'js_base',
]
