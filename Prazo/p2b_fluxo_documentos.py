import logging
import re
import time
import unicodedata
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

    # 1. Tenta API REST (universal, igual Mandado/Argos)
    try:
        from Fix.timeline import obter_timeline, encontrar_doc_por_tipo
        m = re.search(r'/processo/(\d+)', driver.current_url)
        id_processo = m.group(1) if m else None
        if id_processo:
            timeline = obter_timeline(driver, id_processo)
            doc = encontrar_doc_por_tipo(timeline, tipos=['Despacho','Decisão','Sentença','Conclusão'], mais_recente=False)
            if doc:
                logger.info('[FLUXO_PZ] Documento relevante encontrado via API: tipo=%r titulo=%r', doc.tipo, doc.titulo)
                return doc, None, -1
    except Exception as e:
        logger.warning('[FLUXO_PZ] Falha ao buscar documento relevante via API: %s', e)

    # 2. Fallback: DOM Selenium (compatibilidade)
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    logger.info('[FLUXO_PZ] Timeline total de itens encontrados: %d', len(itens))

    def _normalizar_texto_para_busca(valor: str) -> str:
        if not valor:
            return ''
        sem_acento = unicodedata.normalize('NFD', valor)
        sem_acento = ''.join(ch for ch in sem_acento if unicodedata.category(ch) != 'Mn')
        return sem_acento.lower().strip()

    # Busca do mais antigo para o mais recente
    for idx, item in enumerate(itens):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            tipo_real = ''
            try:
                primeiro_span = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
                tipo_real = primeiro_span.text.strip() if primeiro_span else ''
            except Exception as e:
                tipo_real = ''
                logger.debug('[FLUXO_PZ] _encontrar_documento_relevante: falha ao ler primeiro span no item %s: %s', idx, e)

            doc_text = link.text.strip()
            tipo_real_norm = _normalizar_texto_para_busca(tipo_real)
            doc_text_norm = _normalizar_texto_para_busca(doc_text)
            logger.debug('[FLUXO_PZ] _encontrar_documento_relevante: item=%s tipo_real=%r tipo_real_norm=%r doc_text=%r doc_text_norm=%r', idx, tipo_real, tipo_real_norm, doc_text, doc_text_norm)

            relevante = False
            if tipo_real_norm and re.search(r'^(despacho|decisao|sentenca|conclusao)', tipo_real_norm):
                relevante = True
            elif re.search(r'despacho|decisao|sentenca|conclusao', doc_text_norm):
                relevante = True

            if relevante:
                logger.info('[FLUXO_PZ] Documento relevante encontrado #%s: tipo_real=%r doc_text=%r', idx, tipo_real, doc_text)
                return item, link, idx

        except Exception as e:
            logger.debug('[FLUXO_PZ] _encontrar_documento_relevante: erro no item %s: %s', idx, e)
            continue

    # Nenhum documento relevante encontrado: coletar amostra dos primeiros itens
    amostra = []
    for idx, item in enumerate(itens[:5]):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            tipo_real = ''
            try:
                primeiro_span = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
                tipo_real = primeiro_span.text.strip() if primeiro_span else ''
            except Exception:
                tipo_real = ''
            doc_text = link.text.strip().replace('\n', ' ').replace('\r', ' ')
            amostra.append({'idx': idx, 'tipo_real': tipo_real, 'doc_text': doc_text[:80]})
        except Exception as e:
            amostra.append({'idx': idx, 'erro': str(e)})

    logger.info('[FLUXO_PZ] Nenhum documento relevante encontrado. Amostra dos primeiros itens: %s', amostra)
    return None, None, 0


def _obter_texto_documento_api(driver: WebDriver, doc_encontrado: Any) -> Optional[str]:
    """
    Extrai texto do documento usando a API de timeline e conteúdo de documento.

    Retorna o texto extraído ou CONTEUDO_PDF se o documento for PDF.
    """
    try:
        from Fix.timeline import obter_conteudo_doc, CONTEUDO_PDF

        m = re.search(r'/processo/(\d+)', driver.current_url)
        id_processo = m.group(1) if m else None
        if not id_processo:
            logger.debug('[FLUXO_PZ] _obter_texto_documento_api: id_processo não encontrado na URL %r', driver.current_url)
            return None

        doc_id = getattr(doc_encontrado, 'id_interno', None) or getattr(doc_encontrado, 'id_unico', None)
        if not doc_id:
            logger.debug('[FLUXO_PZ] _obter_texto_documento_api: documento API sem id_interno/id_unico')
            return None

        texto = obter_conteudo_doc(driver, id_processo, doc_id)
        if texto == CONTEUDO_PDF:
            logger.info('[FLUXO_PZ] _obter_texto_documento_api: documento PDF detectado id=%s', doc_id)
        elif texto:
            logger.info('[FLUXO_PZ] _obter_texto_documento_api: texto extraído via API id=%s length=%d', doc_id, len(texto))
        else:
            logger.info('[FLUXO_PZ] _obter_texto_documento_api: API retornou vazio para documento id=%s', doc_id)
        return texto
    except Exception as e:
        logger.warning('[FLUXO_PZ] _obter_texto_documento_api falhou: %s', e)
        return None


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