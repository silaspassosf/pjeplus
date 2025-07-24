#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISB_MODULOS/__init__.py
Módulo principal para importação dos submódulos SISB
"""

# Importações dos submódulos
from . import config
from . import drivers
from . import cookies
from . import interface_pje
from . import dados_processo
from . import sisbajud_core
from . import kaizen_interface
from . import preenchimento
from . import bloqueios
from . import minutas
from . import utils

# Versão do módulo
__version__ = '1.0.0'
__author__ = 'PjePlus'
__description__ = 'Módulos de automação SISBAJUD/BACEN refatorados do bacen.py'

# Exportar principais funções para compatibilidade
__all__ = [
    'config',
    'drivers', 
    'cookies',
    'interface_pje',
    'dados_processo',
    'sisbajud_core',
    'kaizen_interface',
    'preenchimento',
    'bloqueios',
    'minutas',
    'utils'
]
