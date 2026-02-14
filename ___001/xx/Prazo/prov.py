"""
prov.py - Processamento Isolado com Progresso Permanente
==========================================================
Script executável isoladamente que:
1. Cria driver próprio com login
2. Navega para painel de processos
3. Aplica filtro 100
4. Seleciona processos via GIGS (AJ-JT/requisição) + livres
5. Aplica atividade XS a todos selecionados
6. Registra em arquivo permanente prov.json para evitar duplicação

Autor: Sistema PJEPlus
Data: 04/12/2025
"""

import sys
import os

# Imports dos módulos refatorados (ajuste de path para Prazo/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .prov_config import (
    TIPO_EXECUCAO,
    URL_PAINEL,
    GECKODRIVER_PATH,
    FIREFOX_BINARY,
    FIREFOX_BINARY_ALT,
    VT_PROFILE_PJE,
    VT_PROFILE_PJE_ALT,
    USAR_PERFIL_VT,
)
from .prov_driver import criar_driver, _criar_driver_vt, _criar_driver_pc, criar_e_logar_driver
from .prov_fluxo import (
    fluxo_prov,
    navegacao_prov,
    selecionar_e_processar,
    aplicar_xs_e_registrar,
    main,
    fluxo_prov_integrado,
)


if __name__ == "__main__":
    try:
        sucesso = main()
        if sucesso:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"\n Erro fatal não capturado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
