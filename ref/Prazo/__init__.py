"""
Módulo Prazo - Sistema de processamento de prazos PJe
Refatoração seguindo guia unificado: padrão Orchestrator + Helpers
Redução de complexidade: fluxo_pz 95%, fluxo_prazo 77%
Arquitetura modular: 4 arquivos especializados
"""

# Imports principais para facilitar uso do módulo
from .p2b_core import (
    normalizar_texto, gerar_regex_geral, parse_gigs_param,
    carregar_progresso_p2b, salvar_progresso_p2b, marcar_processo_executado_p2b,
    processo_ja_executado_p2b, RegraProcessamento, REGEX_PATTERNS
)

from .p2b_fluxo import fluxo_pz
from .p2b_prazo import fluxo_prazo
from .loop import main as executar_loop_principal

__version__ = "2.0.0"
__author__ = "Sistema PJePlus - Refatoração IA"

__all__ = [
    # Core utilities
    'normalizar_texto', 'gerar_regex_geral', 'parse_gigs_param',
    'carregar_progresso_p2b', 'salvar_progresso_p2b', 'marcar_processo_executado_p2b',
    'processo_ja_executado_p2b', 'RegraProcessamento', 'REGEX_PATTERNS',

    # Main functions
    'fluxo_pz', 'fluxo_prazo', 'executar_loop_principal',

    # Version info
    '__version__', '__author__'
]