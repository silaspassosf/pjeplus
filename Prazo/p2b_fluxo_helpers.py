"""
P2B Fluxo PZ Helpers - Funções auxiliares do fluxo_pz
Refatoração seguindo abordagem ORIGINAL do p2b.py: lista sequencial de regras
Mantém termos exatos e ordem de precedência do código que FUNCIONA
"""

# ===== CONFIGURAÇÕES DE PERFORMANCE =====
# Número de threads paralelas para verificar processos contra API GIGS
# Valores recomendados:
#   - 5-10: Conexão estável, evita sobrecarga
#   - 15-20: Conexão rápida, processa mais rápido
#   - 3-5: Conexão lenta ou instável
GIGS_API_MAX_WORKERS = 20

import logging
import re
import time
from typing import Optional, Tuple, List, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve, analisar_timeline_prescreve_js_puro
from .p2b_fluxo_documentos import (
    _encontrar_documento_relevante,
    _documento_nao_assinado,
    _extrair_texto_documento,
    _extrair_com_extrair_direto,
    _extrair_com_extrair_documento,
    _fechar_aba_processo,
)
from .p2b_fluxo_regras import _definir_regras_processamento, _processar_regras_gerais
from .p2b_fluxo_cabecalho import (
    _processar_cabecalho_impugnacoes,
    _processar_checar_cabecalho,
    _executar_visibilidade_sigilosos,
)

# ===== VALIDAÇÃO =====

if __name__ == "__main__":
    pass

    # Teste importações
    try:
        from Prazo.p2b_core import normalizar_texto, gerar_regex_geral
        pass

        # Teste funções básicas
        teste = "TESTE ÁCÊNTÖS"
        resultado = normalizar_texto(teste)
        pass

    except ImportError as e:
        logger.error(f" Erro de importação: {e}")

    pass
