"""Mandado - Processamento Automatizado de Mandados PJe TRT2.

Módulo modularizado com 4 submódulos:
- core: Setup, login, navegação e main
- processamento: Fluxos Argos e Outros  
- regras: Estratégias e regras de negócio (Strategy Pattern)
- utils: Funções utilitárias (lembrete, sigilo, intimação)

Uso:
    from Mandado import main, processar_argos, fluxo_mandados_outros
    
    if __name__ == "__main__":
        main()
"""

from .core import (
    setup_driver,
    navegacao,
    iniciar_fluxo_robusto,
    main,
)

from .processamento import (
    processar_argos,
    fluxo_mandados_outros,
    ultimo_mdd,
    fluxo_mandado,
)

from .regras import (
    aplicar_regras_argos,
)

from .utils import (
    lembrete_bloq,
    retirar_sigilo,
    retirar_sigilo_fluxo_argos,
    retirar_sigilo_certidao_devolucao_primeiro,
    retirar_sigilo_demais_documentos_especificos,
    retirar_sigilo_documentos_especificos,
    fechar_intimacao,
)

__all__ = [
    # core
    'setup_driver',
    'navegacao',
    'iniciar_fluxo_robusto',
    'main',
    # processamento
    'processar_argos',
    'fluxo_mandados_outros',
    'ultimo_mdd',
    'fluxo_mandado',
    # regras
    'aplicar_regras_argos',
    # utils
    'lembrete_bloq',
    'retirar_sigilo',
    'retirar_sigilo_fluxo_argos',
    'retirar_sigilo_certidao_devolucao_primeiro',
    'retirar_sigilo_demais_documentos_especificos',
    'retirar_sigilo_documentos_especificos',
    'fechar_intimacao',
]

