# -*- coding: utf-8 -*-
"""
LOOP PRAZO - Wrapper para manter compatibilidade

Este módulo importa todas as funções dos módulos refatorados para manter
a API original intacta.

Módulos refatorados:
- loop_base.py: Imports, constantes, JS scripts
- loop_ciclo1.py: Funções do ciclo 1
- loop_helpers.py: Funções auxiliares
- loop_api.py: Funções de API
- loop_ciclo2_selecao.py: Seleção do ciclo 2
- loop_ciclo2_processamento.py: Processamento do ciclo 2

Versão: 2.0 - Refatorado para módulos menores
"""

# Wrapper para manter compatibilidade - importa tudo dos módulos refatorados
from .loop_base import *
from .loop_ciclo1 import *
from .loop_helpers import *
from .loop_api import *
from .loop_ciclo2_selecao import *
from .loop_ciclo2_processamento import *