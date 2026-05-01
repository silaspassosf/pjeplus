"""Compatibilidade para o namespace legado Fix.variaveis_resolvers."""

from api.variaveis_resolvers import (
    obter_codigo_validacao_documento,
    obter_peca_processual_da_timeline,
    resolver_variavel,
    get_all_variables,
    obter_chave_ultimo_despacho_decisao_sentenca,
)

__all__ = [
    "obter_codigo_validacao_documento",
    "obter_peca_processual_da_timeline",
    "resolver_variavel",
    "get_all_variables",
    "obter_chave_ultimo_despacho_decisao_sentenca",
]