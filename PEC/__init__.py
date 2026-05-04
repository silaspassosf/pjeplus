import logging
logger = logging.getLogger(__name__)

"""
Modulo PEC - Petices Eletronicas (Refatorado)

Estrutura consolidada:
  runtime_pec.py     — API client, helpers, progresso, carta utils/formatacao, orquestrador
  regras_execucao.py — Regras de bucket/acao e sobrestamento

Shims de compatibilidade (thin shims que reexportam dos consolidados):
  api_client.py, helpers.py, core_progresso.py, carta_utils.py,
  carta_formatacao.py, orquestrador.py, regras_pec.py, sobrestamento.py
"""

# Re-exports dos modulos consolidados
from .runtime_pec import (
    AtividadePEC,
    PECAPIClient,
    PECOrquestrador,
    executar_fluxo_novo_simplificado,
    carregar_progresso_pec,
    salvar_progresso_pec,
    extrair_numero_processo_pec,
    verificar_acesso_negado_pec,
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
)
from .regras_execucao import (
    BUCKET_ORDEM,
    REGRAS,
    determinar_regra,
    def_sob,
)

# Modulos congelados / existentes
from .core_navegacao import (
    navegar_para_atividades,
    aplicar_filtro_xs,
    indexar_processo_atual_gigs,
)
from .core_pos_carta import (
    analisar_documentos_pos_carta,
)
from .regras import (
    determinar_acoes_por_observacao,
)

__all__ = [
    'AtividadePEC',
    'PECAPIClient',
    'PECOrquestrador',
    'executar_fluxo_novo_simplificado',
    'BUCKET_ORDEM',
    'REGRAS',
    'determinar_regra',
    'def_sob',
    'determinar_acoes_por_observacao',
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
