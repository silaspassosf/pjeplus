import logging
logger = logging.getLogger(__name__)

"""
Módulo PEC - Petições Eletrônicas (Refatorado)

[IMPORTANTE] Todos os imports foram desabilitados. Use importações diretas:
- from xx.PEC.rules import determinar_acoes_por_observacao
- from xx.PEC.regras import ... (compatibilidade)
"""

# ===== TODOS OS IMPORTS DESABILITADOS =====
# Motivo: Estrutura xx/PEC/... tem importações absolutas quebradas

# Fornecer stubs para manter compatibilidade básica
# (Compat layer: re-export apenas o que o código legacy `ref/PEC` importa)
from .core import (
    carregar_progresso_pec,
    salvar_progresso_pec,
    extrair_numero_processo_pec,
    verificar_acesso_negado_pec,
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
)
from .core_navegacao import (
    navegar_para_atividades,
    aplicar_filtro_xs,
    indexar_processo_atual_gigs,
)
from .core_pos_carta import (
    analisar_documentos_pos_carta,
)

__all__ = [
    'determinar_acoes_por_observacao',
    'determinar_acao_por_observacao',
    # Compatibility exports for legacy/ref modules
    'carregar_progresso_pec',
    'salvar_progresso_pec',
    'extrair_numero_processo_pec',
    'verificar_acesso_negado_pec',
    'processo_ja_executado_pec',
    'marcar_processo_executado_pec',
    'navegar_para_atividades',
    'aplicar_filtro_xs',
    'indexar_processo_atual_gigs',
    'analisar_documentos_pos_carta',
]
