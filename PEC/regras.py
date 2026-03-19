import logging
logger = logging.getLogger(__name__)

"""
Módulo PEC.regras - COMPATIBILIDADE RETROATIVA

Este arquivo foi refatorado. As funções agora estão nos módulos especializados:
- .rules: Sistema de regras (determinar_acao_por_observacao, etc)
- .actions: Execução de ações (executar_acao_pec, etc)
- .analysis: Análises complexas (def_sob, def_presc, def_ajustegigs)

Este arquivo mantém apenas re-exports para compatibilidade com código existente.
"""

# Re-exports from .matcher (modulo relativo)
from .matcher import (
    determinar_acoes_por_observacao,
    determinar_acao_por_observacao,
    get_action_rules,
    get_cached_rules,
)

# Re-exports from .helpers (modulo relativo)
from .helpers import (
    remover_acentos,
    normalizar_texto,
    gerar_regex_geral,
)

# Re-exports from .actions (modulo relativo)
try:
    from .executor import (
        executar_acao_pec,
        chamar_funcao_com_assinatura_correta,
    )
except ImportError:
    # Se executor não existir, fornecer stubs
    pass

# Re-exports from .analysis (modulo relativo)
try:
    from .sobrestamento import def_sob
    from .prescricao import def_presc
    from .ajuste_gigs import def_ajustegigs
    from .sisbajud_driver import (
        get_or_create_driver_sisbajud,
        fechar_driver_sisbajud_global,
    )
except ImportError:
    # Se os módulos não existirem, fornecer stubs
    pass

# Aliases para compatibilidade
_get_or_create_driver_sisbajud = get_or_create_driver_sisbajud
_remover_acentos = remover_acentos
_normalizar_texto = normalizar_texto
_gerar_regex_geral = gerar_regex_geral

__all__ = [
    # Rules
    'determinar_acoes_por_observacao',
    'determinar_acao_por_observacao',
    'get_action_rules',
    'get_cached_rules',
    'remover_acentos',
    'normalizar_texto',
    'gerar_regex_geral',
    # Actions
    'executar_acao_pec',
    'chamar_funcao_com_assinatura_correta',
    # Analysis
    'def_sob',
    'def_presc',
    'def_ajustegigs',
    'get_or_create_driver_sisbajud',
    'fechar_driver_sisbajud_global',
]
