import logging
logger = logging.getLogger(__name__)

"""
@module: Fix.drivers
@responsibility: Criação e gestão de WebDrivers Firefox
@depends_on: selenium.webdriver, Fix.variaveis
@used_by: Fix.session, Prazo, PEC, SISB
@entry_points: criar_driver_PC, criar_driver_sisb_pc, finalizar_driver
@tags: #selenium #webdriver #firefox #driver
"""

# Importar todos os drivers
from .lifecycle import (
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver
)

__all__ = [
    # Drivers principais
    'criar_driver_PC',
    'criar_driver_VT',
    'criar_driver_notebook',
    
    # Drivers SISBAJUD
    'criar_driver_sisb_pc',
    'criar_driver_sisb_notebook',
    
    # Lifecycle
    'finalizar_driver',
]
