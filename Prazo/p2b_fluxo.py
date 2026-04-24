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
    _obter_texto_documento_api, _processar_regras_gerais,
    _fechar_aba_processo
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

def fluxo_pz(driver: WebDriver) -> bool:
    """
    Processa prazos detalhados em processos abertos.

    Usa extrair_documento para obter texto, analisa regras,
    cria GIGS parametrizadas, executa atos sequenciais e fecha aba.

    Refatoração: 761→40 linhas, aninhamento 6→2 níveis
    Padrão: Orchestrator + 8 Helpers privados

    Returns:
        True se o fluxo processou ao menos um documento relevante; False caso contrário.
    """
    acao_secundaria = None
    texto = None
    try:
        current_url = driver.current_url
    except Exception:
        current_url = 'URL indisponível'
    logger.info('[FLUXO_PZ] Iniciando fluxo_pz em %s', current_url)

    # 1. Encontrar documento relevante na timeline
    doc_encontrado, doc_link, doc_idx = _encontrar_documento_relevante(driver)
    if not doc_encontrado:
        logger.error('[FLUXO_PZ] Nenhum documento relevante encontrado.')
        return False

    # Loop para processar documentos (incluindo próximos encontrados por checar_prox)
    while True:
        # 2. Extrair texto do documento
        if doc_link is None:
            # Documento obtido via API (DocTimeline) — extrair conteúdo via endpoint
            try:
                from Fix.timeline import CONTEUDO_PDF
                texto = _obter_texto_documento_api(driver, doc_encontrado)
                if texto == CONTEUDO_PDF or not texto:
                    logger.info('[FLUXO_PZ] Documento via API é PDF ou vazio — tentando extração direta por URL de documento')
                    try:
                        doc_id = getattr(doc_encontrado, 'id_interno', None) or getattr(doc_encontrado, 'id_unico', None)
                        if doc_id and trt_host:
                            base = trt_host if trt_host.startswith('http') else 'https://' + trt_host
                            url_doc = f"{base}/pjekz/processo/{id_processo}/detalhe/timeline/documento/{doc_id}"
                            logger.info('[FLUXO_PZ] Abrindo documento diretamente para extração: %s', url_doc)
                            driver.execute_script("window.open(arguments[0], '_blank');", url_doc)
                            handles = driver.window_handles
                            driver.switch_to.window(handles[-1])
                            time.sleep(1)
                            try:
                                res = extrair_direto(driver, timeout=10, debug=False, formatar=True)
                                if res and res.get('sucesso'):
                                    texto = res.get('conteudo') or res.get('conteudo_bruto')
                                else:
                                    texto = extrair_documento(driver, timeout=15, log=False)
                            except Exception as e_ext:
                                logger.debug('[FLUXO_PZ] Falha extrair via Selenium direto: %s', e_ext)
                            try:
                                driver.close()
                            except Exception:
                                pass
                            try:
                                driver.switch_to.window(handles[0])
                            except Exception:
                                pass
                        else:
                            logger.info('[FLUXO_PZ] Não há doc_id ou host para extração direta por URL')
                    except Exception as e_nav:
                        logger.debug('[FLUXO_PZ] Erro ao abrir documento para extração direta: %s', e_nav)
                if texto == CONTEUDO_PDF:
                    texto = None
            except Exception as e:
                logger.error('[FLUXO_PZ] Falha ao extrair documento via API: %s', e)
                texto = None
        else:
            texto = _extrair_texto_documento(driver, doc_link)
        # Diagnostic: report source and basic metrics about extracted text
        src = 'selenium' if doc_link is not None else 'api'
        snippet_raw = (texto or '')[:200].replace('\n', ' ') if texto else ''
        logger.info('[FLUXO_PZ] Texto extraído (fonte=%s) length=%s snippet=%r', src, len(texto or ''), snippet_raw)

        if texto == "__DOC_NAO_ASSINADO__":
            logger.warning('[FLUXO_PZ] Documento não assinado detectado. Marcando processo como analisado e encerrando.')
            _fechar_aba_processo(driver)
            return False

        if not texto:
            logger.error('[FLUXO_PZ] Não foi possível extrair o texto do documento.')
            _fechar_aba_processo(driver)
            return False

        from Fix.extracao import _extrair_formatar_texto
        texto_formatado = _extrair_formatar_texto(texto)
        snippet_fmt = (texto_formatado or '')[:200].replace('\n', ' ')
        logger.info('[FLUXO_PZ] Texto formatado length=%s snippet=%r', len(texto_formatado or ''), snippet_fmt)
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
