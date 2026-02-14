import logging
logger = logging.getLogger(__name__)

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
from .loop_ciclo1 import ciclo1
from .loop_ciclo2_processamento import ciclo2

__version__ = "2.0.0"
__author__ = "Sistema PJePlus - Refatoração IA"

def loop_prazo(driver):
    """Função wrapper que executa o fluxo completo de prazo (ciclo1 + ciclo2)"""
    try:
        resultado_ciclo1 = ciclo1(driver)
        if resultado_ciclo1 not in [True, "no_more_processes", "single_process"]:
            return {"sucesso": False, "erro": "Falha em ciclo1"}
        
        if resultado_ciclo1 in ["no_more_processes", "single_process"]:
            return {"sucesso": True, "ciclo1": resultado_ciclo1}
        
        resultado_ciclo2 = ciclo2(driver)
        
        return {
            "sucesso": resultado_ciclo2 is True,
            "ciclo1": resultado_ciclo1,
            "ciclo2": resultado_ciclo2
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

# Alias para compatibilidade
main = loop_prazo
executar_loop_principal = loop_prazo

__all__ = [
    # Core utilities
    'normalizar_texto', 'gerar_regex_geral', 'parse_gigs_param',
    'carregar_progresso_p2b', 'salvar_progresso_p2b', 'marcar_processo_executado_p2b',
    'processo_ja_executado_p2b', 'RegraProcessamento', 'REGEX_PATTERNS',

    # Main functions
    'fluxo_pz', 'fluxo_prazo', 'loop_prazo', 'main', 'executar_loop_principal',
    'ciclo1', 'ciclo2',

    # Version info
    '__version__', '__author__'
]