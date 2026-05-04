"""Mandado - Processamento Automatizado de Mandados PJe TRT2.

Arquivos consolidados (entrypoints ativos):
- entrada_api: API e entrypoint principal
- fluxo_argos: Processamento Argos e anexos
- apoio_fluxos: Core, utils, sigilo, lembrete, intimacao

Arquivos LEGADO (thin shims de compatibilidade):
- processamento.py, processamento_fluxo.py, core.py
- processamento_api.py, processamento_argos.py, processamento_anexos.py
- processamento_outros.py, utils.py, utils_intimacao.py
- utils_sigilo.py, utils_lembrete.py, regras.py, atos_wrapper.py
"""

from .entrada_api import (
    processar_mandados_devolvidos_api,
    fechar_intimacao,
)

from .fluxo_argos import (
    processar_argos,
    processar_sisbajud,
    tratar_anexos_argos,
)

from .apoio_fluxos import (
    fluxo_mandados_outros,
    lembrete_bloq,
    retirar_sigilo,
    retirar_sigilo_fluxo_argos,
    retirar_sigilo_certidao_devolucao_primeiro,
    retirar_sigilo_demais_documentos_especificos,
    retirar_sigilo_documentos_especificos,
)

__all__ = [
    # entrada_api
    'processar_mandados_devolvidos_api',
    'fechar_intimacao',
    # fluxo_argos
    'processar_argos',
    'processar_sisbajud',
    'tratar_anexos_argos',
    # apoio_fluxos
    'fluxo_mandados_outros',
    'lembrete_bloq',
    'retirar_sigilo',
    'retirar_sigilo_fluxo_argos',
    'retirar_sigilo_certidao_devolucao_primeiro',
    'retirar_sigilo_demais_documentos_especificos',
    'retirar_sigilo_documentos_especificos',
]

