"""
atos.anexos - Namespace de anexos para atos.

Espelha a API de PEC/anexos, mantendo compatibilidade total.
"""

from .core import (
    substituir_marcador_por_conteudo,
    salvar_conteudo_clipboard,
    extrair_numero_processo_da_url,
    anex_carta,
    anex_sisbconsulta,
    anex_bloqneg,
    anex_parcial,
    formatar_conteudo_ecarta,
    _obter_conteudo_relatorio_sisbajud,
    _wrapper_sisbajud_generico,
    wrapper_juntada_geral,
    create_juntador,
    executar_juntada_ate_editor,
    executar_juntada,
)

__all__ = [
    'substituir_marcador_por_conteudo',
    'salvar_conteudo_clipboard',
    'extrair_numero_processo_da_url',
    'anex_carta',
    'anex_sisbconsulta',
    'anex_bloqneg',
    'anex_parcial',
    'formatar_conteudo_ecarta',
    '_obter_conteudo_relatorio_sisbajud',
    '_wrapper_sisbajud_generico',
    'wrapper_juntada_geral',
    'create_juntador',
    'executar_juntada_ate_editor',
    'executar_juntada',
]
