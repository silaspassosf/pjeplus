"""api.variaveis_helpers — re-export canônico de Fix.variaveis."""
from Fix.variaveis import (  # noqa: F401
    _erro_gateway,
    _extrair_itens_pagina,
    buscar_atividade_gigs_por_observacao,
    buscar_todas_paginas,
    obter_gigs_com_fase,
    obter_texto_documento,
    obter_todas_atividades_gigs_com_observacao,
    padrao_liq,
    verificar_bndt,
)

__all__ = [
    '_erro_gateway',
    '_extrair_itens_pagina',
    'buscar_todas_paginas',
    'obter_gigs_com_fase',
    'obter_texto_documento',
    'buscar_atividade_gigs_por_observacao',
    'obter_todas_atividades_gigs_com_observacao',
    'padrao_liq',
    'verificar_bndt',
]
