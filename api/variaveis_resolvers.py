"""api.variaveis_resolvers — re-export canônico de Fix.variaveis."""
from Fix.variaveis import (  # noqa: F401
    get_all_variables,
    obter_chave_ultimo_despacho_decisao_sentenca,
    obter_codigo_validacao_documento,
    obter_peca_processual_da_timeline,
    resolver_variavel,
)

__all__ = [
    'obter_codigo_validacao_documento',
    'obter_peca_processual_da_timeline',
    'resolver_variavel',
    'get_all_variables',
    'obter_chave_ultimo_despacho_decisao_sentenca',
]
