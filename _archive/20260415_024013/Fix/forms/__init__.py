import logging
logger = logging.getLogger(__name__)

"""
@module: Fix.forms
@responsibility: Manipulação de formulários e campos PJe
@depends_on: Fix.selenium_base
@used_by: Prazo, SISB, atos
@entry_points: preencher_campos_prazo, preencher_multiplos_campos
@tags: #forms #fields #prazo #validation
"""

from .multiple_fields import preencher_multiplos_campos

__all__ = ['preencher_multiplos_campos']
