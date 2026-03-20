import logging
import re
import time
from typing import Optional, Tuple, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from .p2b_fluxo_lazy import _lazy_import

logger = logging.getLogger(__name__)


# ===== HELPERS PRIVADOS: FLUXO_PZ =====

def _encontrar_documento_relevante(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], int]:
    """
    Helper: Encontra documento relevante (decisão/despacho/sentença) na timeline.
    
     CORRIGIDO: Busca APENAS no tipo real do documento (primeiro <span> dentro do link),
    não na descrição completa que pode conter termos enganosos.
    
    Exemplo correto: <span>Sentença</span><span>(Prescrição...)</span>
    Exemplo incorreto: <span>Edital</span><span>(Decisão/Sentença)</span> <- o tipo é EDITAL, não Decisão

    Returns:
        Tupla (doc_encontrado, doc_link, doc_idx)
    """
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    pass

    # Busca do mais antigo para o mais recente
    for idx, item in enumerate(itens):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            
            #  CORRIGIDO: Extrair apenas o primeiro <span> (tipo real do documento)
            # Não o texto completo que pode incluir descrição enganosa
            primeiro_span = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
            tipo_real = primeiro_span.text.lower().strip() if primeiro_span else ''
            
            # Verificar se o tipo REAL é um dos procurados
            if tipo_real and re.search(r'^(despacho|decisão|sentença|conclusão)', tipo_real):
                real_idx = idx
                # Mostrar o tipo real encontrado (sem incluir a descrição enganosa)
                pass
                return item, link, real_idx

        except Exception:
            continue

    return None, None, 0


def _documento_nao_assinado(doc_link: Any) -> bool:
    """
    Helper: Detecta se o documento na timeline está marcado como não assinado.
    """
    try:
        item = doc_link.find_element(By.XPATH, './ancestor::li[contains(@class,"tl-item-container")]')
        icones = item.find_elements(By.CSS_SELECTOR, 'i.documento-nao-assinado.fa-unlock')
        for icone in icones:
            try:
                if icone.is_displayed():
                    return True
            except Exception:
                pass
        # Fallback: aria-label direto no ícone (mais restrito)
        icones_label = item.find_elements(By.CSS_SELECTOR, 'i.documento-nao-assinado[aria-label="Documento não assinado"]')
        for icone in icones_label:
            try:
                if icone.is_displayed():
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _extrair_texto_documento(driver: WebDriver, doc_link: Any) -> Optional[str]:
    """
    Helper: Extrai texto do documento usando múltiplas estratégias.

    Args:
        driver: WebDriver instance
        doc_link: Link do documento

    Returns:
        Texto extraído ou None se falhar
    """
    doc_link.click()
    try:
        from Fix.core import aguardar_renderizacao_nativa
        aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
    except Exception:
        time.sleep(2)

    # Estratégia 1: extrair_direto (otimizada)
    texto = _extrair_com_extrair_direto(driver)
    if texto:
        return texto

    # Estratégia 2: extrair_documento (fallback)
    texto = _extrair_com_extrair_documento(driver)
    if texto:
        return texto

    # Se falhou, verificar se o documento está não assinado
    if _documento_nao_assinado(doc_link):
        return "__DOC_NAO_ASSINADO__"

    return None


def _extrair_com_extrair_direto(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_direto."""
    m = _lazy_import()
    extrair_direto = m['extrair_direto']
    
    try:
        # Não ativar debug detalhado do cabeçalho aqui (evita logs verbosos)
        logger.info('[FLUXO_PZ] Tentando extração DIRETA com extrair_direto...')
        resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=True)

        if resultado_direto and resultado_direto.get('sucesso'):
            if resultado_direto.get('conteudo'):
                raw = resultado_direto['conteudo']
                texto = raw.lower()
                snippet = ' '.join(raw.strip().splitlines())[:200]
                logger.info('[FLUXO_PZ]  Extração DIRETA bem-sucedida (snippet=%s...)', snippet)
                return texto
            elif resultado_direto.get('conteudo_bruto'):
                raw = resultado_direto['conteudo_bruto']
                texto = raw.lower()
                snippet = ' '.join(raw.strip().splitlines())[:200]
                logger.info('[FLUXO_PZ]  Extração DIRETA bem-sucedida (bruto snippet=%s...)', snippet)
                return texto

    except Exception as e_direto:
        logger.error(f'[FLUXO_PZ] Erro na extração DIRETA: {e_direto}')

    return None


def _extrair_com_extrair_documento(driver: WebDriver) -> Optional[str]:
    """Helper: Extrai texto usando extrair_documento (fallback)."""
    m = _lazy_import()
    extrair_documento = m['extrair_documento']
    
    try:
        pass
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True)

        if texto_tuple and texto_tuple[0]:
            texto = texto_tuple[0].lower()
            pass
            return texto

    except Exception as e_extrair:
        logger.error(f'[FLUXO_PZ] Erro ao chamar/processar extrair_documento: {e_extrair}')

    return None


def _fechar_aba_processo(driver: WebDriver) -> None:
    """
    Helper: Fecha aba do processo e volta para lista.
    """
    all_windows = driver.window_handles
    main_window = all_windows[0]
    current_window = driver.current_window_handle

    if current_window != main_window and len(all_windows) > 1:
        driver.close()
        try:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            logger.error(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida: {e}")
            try:
                driver.current_url  # Testa se aba está acessível
            except Exception:
                logger.error("[LIMPEZA][ERRO] Tentou acessar aba já fechada.")

    pass