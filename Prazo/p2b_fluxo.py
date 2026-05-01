"""
P2B Fluxo Module - Funções de processamento de fluxo
Refatoração seguindo guia unificado: padrão Orchestrator + Helpers
Redução de complexidade: fluxo_pz de 761→40 linhas, aninhamento 6→2 níveis
"""

import logging
import re
import time
from typing import Optional, Tuple, List, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Prazo.p2b_core import normalizar_texto, gerar_regex_geral
from .p2b_fluxo_helpers import (
    _processar_regras_gerais, _fechar_aba_processo
)

# Logger local para evitar conflitos
logger = logging.getLogger(__name__)

from Fix.selenium_base import aguardar_e_clicar
from Fix.gigs import criar_gigs
from atos.judicial import ato_pesquisas, ato_pesqliq, ato_sobrestamento, idpj
from atos.wrappers_mov import mov_arquivar
from PEC.carta import carta


# ===== ORCHESTRATOR: FLUXO_PZ =====

def fluxo_pz(driver: WebDriver) -> None:
    """
    Processa prazos detalhados em processos abertos.

    Usa extrair_documento para obter texto, analisa regras,
    cria GIGS parametrizadas, executa atos sequenciais e fecha aba.

    Refatoração: 761→40 linhas, aninhamento 6→2 níveis
    Padrão: Orchestrator + 8 Helpers privados
    """
    # Extrai documento relevante através do pipeline API+pdfplumber
    try:
        from .p2b_api import extrair_documento_relevante
    except Exception:
        logger.error('[FLUXO_PZ] p2b_api.extrair_documento_relevante não disponível')
        return False

    resultado = extrair_documento_relevante(driver)
    if not resultado or not resultado.get('sucesso'):
        logger.info('[FLUXO_PZ] Nenhum documento relevante extraído: %s', (resultado or {}).get('erro'))
        try:
            _fechar_aba_processo(driver)
        except Exception:
            pass
        return False

    texto = resultado.get('conteudo') or ''

    # Formatar/extrair texto com utilitário se disponível
    try:
        from Fix.extracao import _extrair_formatar_texto
        texto_formatado = _extrair_formatar_texto(texto)
    except Exception:
        texto_formatado = texto

    # Normalizar e aplicar regras
    texto_normalizado = normalizar_texto(texto_formatado)
    try:
        _processar_regras_gerais(driver, texto_normalizado, 0)
    except Exception as e:
        logger.error('[FLUXO_PZ] Erro ao processar regras: %s', e)

    # Fechar aba/processo e retornar
    try:
        _fechar_aba_processo(driver)
    except Exception:
        pass

    return True


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
