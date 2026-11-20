"""SISB.relatorios_integracao — re-export canônico de SISB/processamento/*."""

from .processamento.integracao import (  # noqa: F401
    _atualizar_relatorio_com_segundo_protocolo,
    _executar_juntada_pje,
)
from .processamento.relatorios_dados import (  # noqa: F401
    _agrupar_dados_bloqueios,
    extrair_dados_bloqueios_processados,
)
from .processamento.relatorios_formatacao import (  # noqa: F401
    gerar_relatorio_bloqueios_conciso,
    gerar_relatorio_bloqueios_processados,
)
from .processamento.relatorios_ordem import _gerar_relatorio_ordem  # noqa: F401

__all__ = [
    '_agrupar_dados_bloqueios',
    'extrair_dados_bloqueios_processados',
    'gerar_relatorio_bloqueios_processados',
    'gerar_relatorio_bloqueios_conciso',
    '_gerar_relatorio_ordem',
    '_executar_juntada_pje',
    '_atualizar_relatorio_com_segundo_protocolo',
]
