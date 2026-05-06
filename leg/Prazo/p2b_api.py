"""
Prazo.p2b_api - Módulo auxiliar (API-like) para localizar documento relevante
e extrair seu conteúdo usando funções DOM-based já presentes no projeto.

Funções principais:
- localizar_documento_relevante_api(driver)
- extrair_conteudo_documento_api(driver, doc_link)
- processar_processo_por_id_api(driver, id_processo)

Este módulo não cria lógica nova de extração — ele orquestra as
funções existentes de `Fix.documents` e `Fix.extracao`, com fallbacks DOM.
"""
from typing import Optional, Tuple, Any, Dict
import time
import logging
import re

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


_TIPOS_RELEVANTES = re.compile(r'^(despacho|decis[aã]o|senten[cç]a|conclus[aã]o)', re.IGNORECASE)


def extrair_documento_relevante(driver: WebDriver) -> Dict[str, Any]:
    """Extrai o primeiro documento relevante via API (/timeline + /documentos/.../conteudo).

    Retorna dict com chaves: sucesso, conteudo, tipo, titulo, id_documento, id_processo, erro
    """
    from Fix.variaveis_client import session_from_driver

    # 1) obter id_processo da URL
    m = re.search(r'/processo/(\d+)', driver.current_url)
    if not m:
        return _falha('id_processo não detectado na URL: ' + driver.current_url)
    id_processo = m.group(1)

    sess, host = session_from_driver(driver)
    base = f'https://{host}'

    # 2) timeline via API
    url_timeline = (
        f'{base}/pje-comum-api/api/processos/id/{id_processo}/timeline'
        '?buscarDocumentos=true&buscarMovimentos=false&somenteDocumentosAssinados=false'
    )
    try:
        r = sess.get(url_timeline, timeout=30)
        r.raise_for_status()
        timeline = r.json()
    except Exception as e:
        return _falha(f'timeline HTTP error: {e}')

    doc = next((i for i in timeline if _TIPOS_RELEVANTES.match((i.get('tipo') or '').strip())), None)
    if not doc:
        tipos = list({i.get('tipo', '?') for i in timeline})
        return _falha(f'nenhum documento relevante na timeline. Tipos: {tipos}')

    id_doc = str(doc.get('id') or doc.get('idDocumento') or '')
    tipo = doc.get('tipo', '')
    titulo = doc.get('titulo', '')
    logger.info(f'[p2b_api] doc relevante: tipo={tipo} id={id_doc}')

    # 3) download do conteúdo (PDF esperado)
    url_conteudo = f'{base}/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
    try:
        r = sess.get(url_conteudo, timeout=60, stream=True)
        r.raise_for_status()
        pdf_bytes = r.content
    except Exception as e:
        return _falha(f'/conteudo download error: {e}', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
        return _falha(
            f'/conteudo não é PDF. Content-Type={r.headers.get("content-type")} primeiros bytes={pdf_bytes[:20]!r}',
            id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo,
        )

    # 4) extrair via pdfplumber
    try:
        import io
        import pdfplumber
    except Exception:
        return _falha('pdfplumber não instalado. Execute: pip install pdfplumber', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            paginas = [p.extract_text() or '' for p in pdf.pages]
        texto = '\n\n--- PÁGINA ---\n\n'.join(paginas).strip()
    except Exception as e:
        return _falha(f'pdfplumber erro: {e}', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    if not texto or len(texto) < 20:
        return _falha('PDF sem texto extraível (possivelmente escaneado)', id_processo=id_processo, id_documento=id_doc, tipo=tipo, titulo=titulo)

    logger.info(f'[p2b_api] texto extraído: {len(texto)} chars')
    return {
        'sucesso': True,
        'conteudo': texto,
        'tipo': tipo,
        'titulo': titulo,
        'id_documento': id_doc,
        'id_processo': id_processo,
        'erro': None,
    }


def _falha(msg: str, **extra) -> Dict[str, Any]:
    logger.warning(f'[p2b_api] {msg}')
    return {'sucesso': False, 'conteudo': None, 'tipo': None, 'titulo': None, 'id_documento': None, 'id_processo': None, 'erro': msg, **extra}


def localizar_documento_relevante_api(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], int]:
    """Localiza um documento relevante (decisão/despacho/sentença) na timeline.

    Retorna (elemento_item, elemento_link, indice) ou (None, None, 0).
    Tenta usar `Fix.documents.buscar_documentos_sequenciais` quando disponível
    (comportamento legado). Caso contrário, usa heurística DOM.
    """
    # Tentar usar funções prontas do projeto (legado/refactor)
    try:
        from Fix.documents import buscar_documentos_sequenciais, verificar_documento_decisao_sentenca
        try:
            docs = buscar_documentos_sequenciais(driver, log=False)
            if docs:
                for idx, elem in enumerate(docs):
                    try:
                        try:
                            link = elem.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        except Exception:
                            links = elem.find_elements(By.TAG_NAME, 'a')
                            link = None
                            for l in links:
                                try:
                                    if l.is_displayed():
                                        link = l
                                        break
                                except Exception:
                                    continue
                        if link:
                            return elem, link, idx
                    except Exception:
                        continue
        except Exception:
            # falha na busca sequencial, seguir para heurística DOM
            pass

        try:
            if verificar_documento_decisao_sentenca(driver):
                # a verificação indica presença; prosseguir para heurística DOM
                pass
        except Exception:
            pass

    except Exception:
        # Fix.documents não disponível, usar heurística DOM abaixo
        pass

    # Heurística DOM — vasculhar timeline por tipo textual
    try:
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container') or []
    except Exception:
        itens = []

    for idx, item in enumerate(itens):
        try:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            except Exception:
                links = item.find_elements(By.TAG_NAME, 'a')
                link = None
                for l in links:
                    try:
                        if l.is_displayed():
                            link = l
                            break
                    except Exception:
                        continue
                if link is None:
                    continue

            # extrair tipo real a partir do primeiro span/strong/b
            tipo_real = ''
            try:
                for q in ['span:not(.sr-only)', 'strong', 'b', 'em', 'span']:
                    try:
                        candidate = link.find_element(By.CSS_SELECTOR, q)
                        txt = (candidate.text or '').strip()
                        if txt:
                            tipo_real = txt.lower().strip()
                            break
                    except Exception:
                        continue
                if not tipo_real:
                    tipo_real = (link.text or '').split('(')[0].strip().lower()
            except Exception:
                tipo_real = ''

            if tipo_real and re.search(r'^(despacho|decis[oã]o|senten[çc]a|conclus[oã]o|conclusao)', tipo_real):
                return item, link, idx

        except Exception:
            continue

    return None, None, 0


def extrair_conteudo_documento_api(driver: WebDriver, doc_link: Any, timeout: int = 12) -> Dict[str, Any]:
    """Extrai conteúdo do documento aberto.

    - `doc_link` pode ser um WebElement (link clicável) ou um seletor (str).
    - Retorna dicionário com chaves: sucesso(bool), metodo(str), conteudo(str|None), info(dict)
    """
    # localizar o elemento se for seletor
    el = None
    try:
        if isinstance(doc_link, str):
            el = driver.find_element(By.CSS_SELECTOR, doc_link)
        else:
            el = doc_link
    except Exception:
        el = None

    if el is None:
        return {'sucesso': False, 'metodo': None, 'conteudo': None, 'info': {'erro': 'link_nao_encontrado'}}

    try:
        el.click()
    except Exception:
        try:
            driver.execute_script('arguments[0].click()', el)
        except Exception as e:
            logger.debug(f'[P2B_API] falha ao clicar link: {e}')

    # esperar renderização mínima
    try:
        from Fix.core import aguardar_renderizacao_nativa
        try:
            aguardar_renderizacao_nativa(driver, 'object.conteudo-pdf, .document-viewer, .timeline', timeout=2)
        except Exception:
            time.sleep(1)
    except Exception:
        time.sleep(1)

    # tentar extrair via extrair_direto -> extrair_documento
    try:
        from Fix.extracao import extrair_direto, extrair_documento
    except Exception:
        extrair_direto = None
        extrair_documento = None

    # Estratégia A: extrair_direto
    if extrair_direto:
        try:
            res = extrair_direto(driver, timeout=timeout, debug=False, formatar=True)
            if res and res.get('sucesso'):
                return {'sucesso': True, 'metodo': 'extrair_direto', 'conteudo': res.get('conteudo'), 'info': res.get('info', {})}
        except Exception as e:
            logger.debug(f'[P2B_API] extrair_direto falhou: {e}')

    # Estratégia B: extrair_documento (compat shim que retorna str)
    if extrair_documento:
        try:
            texto = extrair_documento(driver, regras_analise=None, timeout=timeout, log=False)
            if texto:
                return {'sucesso': True, 'metodo': 'extrair_documento', 'conteudo': texto, 'info': {}}
        except Exception as e:
            logger.debug(f'[P2B_API] extrair_documento falhou: {e}')

    # fallback: tentar coletar texto direto do elemento da timeline
    try:
        parent_text = el.find_element(By.XPATH, './ancestor::li').text
        if parent_text and len(parent_text.strip()) > 20:
            return {'sucesso': True, 'metodo': 'dom_text_fallback', 'conteudo': parent_text.strip(), 'info': {}}
    except Exception:
        pass

    # detectar doc nao assinado
    try:
        # procura ícone de desbloqueio/nao assinado
        item = el.find_element(By.XPATH, './ancestor::li[contains(@class, "tl-item-container")]')
        icones = item.find_elements(By.CSS_SELECTOR, 'i.documento-nao-assinado')
        for ic in icones:
            if ic.is_displayed():
                return {'sucesso': False, 'metodo': 'nao_assinado', 'conteudo': None, 'info': {'nao_assinado': True}}
    except Exception:
        pass

    return {'sucesso': False, 'metodo': None, 'conteudo': None, 'info': {'erro': 'nao_extraido'}}


def processar_processo_por_id_api(driver: WebDriver, id_processo: int, host: str = 'pje.trt2.jus.br') -> Dict[str, Any]:
    """Abre detalhe do processo e tenta localizar+extrair documento relevante.

    Retorna dicionário com o resultado da extração e metadados.
    """
    detalhe_url = f'https://{host}/pjekz/processo/{id_processo}/detalhe/'
    logger.info(f'[P2B_API] Abrindo processo id={id_processo} url={detalhe_url}')

    try:
        driver.get(detalhe_url)
    except Exception as e:
        return {'sucesso': False, 'erro': 'nav_failure', 'mensagem': str(e)}

    # pequena espera para carregar timeline
    time.sleep(1.5)

    # Usar exclusivamente o pipeline API-based (timeline -> conteudo -> pdfplumber)
    try:
        resultado = extrair_documento_relevante(driver)
    except Exception as e:
        return {'sucesso': False, 'erro': 'extracao_exception', 'mensagem': str(e)}

    if not resultado or not resultado.get('sucesso'):
        return {'sucesso': False, 'erro': 'nenhum_documento_relevante', 'info': resultado}

    return {
        'sucesso': True,
        'metodo': 'api_pdfplumber',
        'conteudo': resultado.get('conteudo'),
        'info': {k: v for k, v in resultado.items() if k not in ('conteudo',)},
        'indice': 0,
    }


if __name__ == '__main__':
    print('Prazo.p2b_api: funções disponíveis: localizar_documento_relevante_api, extrair_conteudo_documento_api, processar_processo_por_id_api')
