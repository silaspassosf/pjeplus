"""
PEC.anexos.formatacao - Módulo de formatação PEC/anexos.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém funções de formatação de conteúdo.
"""


def formatar_conteudo_ecarta(html_table):
    """
    Formata o conteúdo HTML extraído do e-carta para inserção adequada no editor.
    """
    return html_table