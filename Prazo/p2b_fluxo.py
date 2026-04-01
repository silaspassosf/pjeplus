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
    _encontrar_documento_relevante, _extrair_texto_documento,
    _processar_regras_gerais, _fechar_aba_processo
)

# Logger local para evitar conflitos
logger = logging.getLogger(__name__)

from Fix.selenium_base import aguardar_e_clicar
from Fix.gigs import criar_gigs
from Fix.extracao import extrair_direto, extrair_documento
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
    acao_secundaria = None
    texto = None

    # 1. Encontrar documento relevante na timeline
    doc_encontrado, doc_link, doc_idx = _encontrar_documento_relevante(driver)
    if not doc_encontrado or not doc_link:
        logger.error('[FLUXO_PZ] Nenhum documento relevante encontrado.')
        return

    # Loop para processar documentos (incluindo próximos encontrados por checar_prox)
    while True:
        # 2. Extrair texto do documento
        texto = _extrair_texto_documento(driver, doc_link)
        if texto == "__DOC_NAO_ASSINADO__":
            logger.warning('[FLUXO_PZ] Documento não assinado detectado. Marcando processo como analisado e encerrando.')
            _fechar_aba_processo(driver)
            return

        if not texto:
            logger.error('[FLUXO_PZ] Não foi possível extrair o texto do documento.')
            break

        from Fix.extracao import _extrair_formatar_texto
        texto_formatado = _extrair_formatar_texto(texto)
        pass
        pass

        # 3. Processar regras de negócio
        texto_normalizado = normalizar_texto(texto)
        resultado_checagem = _processar_regras_gerais(driver, texto_normalizado, doc_idx)

        # Log resultado das regras: indicar se checar_prox encontrou próximo documento
        if resultado_checagem and len(resultado_checagem) == 3:
            prox_doc, prox_link, prox_idx = resultado_checagem
            if prox_doc and prox_link:
                logger.info('[FLUXO_PZ] Regras: checar_prox encontrou próximo documento (idx=%s)', prox_idx)
            else:
                logger.info('[FLUXO_PZ] Regras: checar_prox acionado mas nenhum próximo documento retornado')
        else:
            logger.info('[FLUXO_PZ] Regras: nenhuma checagem_prox acionada (verificar logs de regras para ações secundárias)')

        # Se checar_prox encontrou um próximo documento, continuar processando
        if resultado_checagem and len(resultado_checagem) == 3:
            prox_doc, prox_link, prox_idx = resultado_checagem
            if prox_doc and prox_link:
                pass
                doc_encontrado, doc_link, doc_idx = prox_doc, prox_link, prox_idx
                continue  # Processar o próximo documento

        # Se não há próximo documento ou checar_prox não foi acionado, encerrar
        break

    # Cleanup: fechar aba
    _fechar_aba_processo(driver)


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
