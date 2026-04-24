"""
Fix.timeline - Leitura universal de timeline do PJe via API REST.

Substitui lógica Selenium duplicada em Mandado/ e Prazo/p2b/:
  - Mandado/processamento_api.py::_selecionar_doc_via_timeline  (DOM scraping)
  - Prazo/p2b_fluxo_documentos.py::_encontrar_documento_relevante (DOM scraping)
  - Prazo/p2b_fluxo_documentos.py::_extrair_texto_documento       (click+render)

API usada:
  GET /pje-comum-api/api/processos/id/{id}/timeline
  GET /pje-comum-api/api/processos/id/{id}/documentos/id/{id_doc}
  GET /pje-comum-api/api/processos/id/{id}/documentos/id/{id_doc}/conteudo

Respostas confirmadas em produção:
  - campo `tipo`   = tipo genérico ('Certidão', 'Despacho', etc.)
  - campo `titulo` = descrição completa ('Devolução de Ordem de Pesquisa Patrimonial...')
  - conteudo returna HTML ou PDF (PDF sinalizado como '__PDF__' para fallback no caller)
  - id_processo numérico disponível na URL: /pjekz/processo/{id}/detalhe
"""

import html as _html
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import requests
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)

TRT2_HOST = 'https://pje.trt2.jus.br'

# Sinal retornado por obter_conteudo_doc quando o endpoint devolve PDF binário.
# O caller deve usar extração Selenium (extrair_direto / _JS_EXTRAIR_OBJECT).
CONTEUDO_PDF = '__PDF__'


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------

@dataclass
class DocTimeline:
    """Representação de um documento da timeline do PJe."""
    id_interno: Optional[str]          # raw 'id' ou 'idDocumento'
    id_unico: Optional[str]            # raw 'idUnicoDocumento'
    tipo: str                          # tipo genérico: 'Certidão', 'Despacho', etc.
    titulo: str                        # descrição completa exibida na timeline
    data: str                          # ISO ou DD/MM/YYYY
    is_assinado: bool
    polo: Optional[str]                # 'ativo' | 'passivo' | 'terceiro' | None
    nome_peticionante: Optional[str]
    conteudo: Optional[str] = field(default=None)  # preenchido por obter_timeline_com_conteudo


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _normalizar_polo(polo_raw: str) -> Optional[str]:
    p = polo_raw.upper().strip()
    if 'ATIVO' in p:
        return 'ativo'
    if 'PASSIVO' in p:
        return 'passivo'
    if 'TERCEIRO' in p or 'INTERVENIENTE' in p or 'PERITO' in p:
        return 'terceiro'
    return None


def _fazer_doc(raw: Dict[str, Any]) -> DocTimeline:
    polo_raw = (
        raw.get('poloPeticionante') or raw.get('polo') or
        raw.get('parte') or raw.get('peticionante') or ''
    )
    if isinstance(polo_raw, dict):
        polo_raw = polo_raw.get('polo') or polo_raw.get('tipoPolo') or ''
    polo = _normalizar_polo(str(polo_raw)) if polo_raw else None

    titulo = (raw.get('titulo') or '').strip()
    nome = None
    if ' - ' in titulo:
        candidato = titulo.split(' - ', 1)[-1].strip()
        if candidato and not candidato.startswith('ID.'):
            nome = candidato

    # is_assinado: campo booleano explícito ou inverso de documentoNaoAssinado
    assinado = raw.get('assinado')
    if assinado is None:
        assinado = not raw.get('documentoNaoAssinado', False)

    id_interno = raw.get('id') or raw.get('idDocumento')
    id_unico = raw.get('idUnicoDocumento')

    return DocTimeline(
        id_interno=str(id_interno) if id_interno is not None else None,
        id_unico=str(id_unico) if id_unico is not None else None,
        tipo=(raw.get('tipo') or '').strip(),
        titulo=titulo,
        data=(raw.get('data') or raw.get('dataInclusao') or ''),
        is_assinado=bool(assinado),
        polo=polo,
        nome_peticionante=nome,
    )


def _limpar_html(texto: str) -> str:
    sem_tags = re.sub(r'<[^>]+>', '', texto)
    sem_tags = _html.unescape(sem_tags)
    return re.sub(r'\s{2,}', ' ', sem_tags).strip()


def _sessao_do_driver(driver: WebDriver, host: str = TRT2_HOST) -> requests.Session:
    """Cria requests.Session autenticada com cookies do Selenium WebDriver."""
    sess = requests.Session()
    sess.headers.update({'Accept': 'application/json', 'Referer': host})
    xsrf = None
    for cookie in driver.get_cookies():
        sess.cookies.set(
            cookie['name'], cookie['value'],
            domain=cookie.get('domain', ''),
        )
        if cookie['name'].lower() == 'xsrf-token':
            xsrf = cookie['value']
    if xsrf:
        sess.headers['X-XSRF-TOKEN'] = xsrf
    return sess


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------


def id_processo_da_url(driver: WebDriver) -> Optional[str]:
    """
    Extrai o ID numérico do processo da URL atual do browser.

    Exemplo: https://pje.trt2.jus.br/pjekz/processo/6451638/detalhe → '6451638'
    """
    m = re.search(r'/processo/(\d+)(?:/|$)', driver.current_url)
    return m.group(1) if m else None


def obter_timeline(
    driver_ou_sessao: Union[WebDriver, requests.Session],
    id_processo: str,
    *,
    host: str = TRT2_HOST,
    buscar_movimentos: bool = False,
    apenas_assinados: bool = False,
) -> List[DocTimeline]:
    """
    1 GET — retorna todos os documentos da timeline em ordem cronológica reversa
    (índice 0 = mais recente). Movimentos são excluídos por padrão.

    Args:
        driver_ou_sessao: WebDriver (extrai cookies automaticamente) ou requests.Session já autenticada.
        id_processo: ID numérico interno do processo (ex: '6451638').
        buscar_movimentos: incluir movimentos processuais na lista.
        apenas_assinados: filtrar apenas documentos assinados.

    Returns:
        Lista de DocTimeline. Vazia se falhar ou timeline vazia.
    """
    if isinstance(driver_ou_sessao, WebDriver):
        sess = _sessao_do_driver(driver_ou_sessao, host)
    else:
        sess = driver_ou_sessao

    url = f"{host}/pje-comum-api/api/processos/id/{id_processo}/timeline"
    params = {
        'somenteDocumentosAssinados': str(apenas_assinados).lower(),
        'buscarMovimentos': str(buscar_movimentos).lower(),
        'buscarDocumentos': 'true',
    }
    try:
        r = sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning('[TIMELINE] GET timeline %s: HTTP %s', id_processo, r.status_code)
            return []
        dados = r.json()
    except Exception as e:
        logger.error('[TIMELINE] Erro ao obter timeline %s: %s', id_processo, e)
        return []

    if not isinstance(dados, list):
        dados = dados.get('resultado') or dados.get('dados') or []

    # Filtrar movimentos (tipo == 'Movimento') — mesmo padrão de Peticao/api/contexto.py
    return [_fazer_doc(it) for it in dados if (it.get('tipo') or '') != 'Movimento']


def encontrar_doc_por_tipo(
    timeline: List[DocTimeline],
    *,
    tipos: Optional[List[str]] = None,
    padrao_regex: Optional[str] = None,
    mais_recente: bool = True,
    ignorar_nao_assinados: bool = True,
) -> Optional[DocTimeline]:
    """
    Filtra e retorna o primeiro DocTimeline que satisfaz os critérios.

    Busca em `{tipo} {titulo}` para capturar tanto o tipo genérico quanto a
    descrição completa (ex: 'Devolução de Ordem de Pesquisa Patrimonial').

    Args:
        tipos: match exato em doc.tipo (case-insensitive).
        padrao_regex: re.search aplicado em '{doc.tipo} {doc.titulo}'.
        mais_recente: True → itera do índice 0 (mais recente); False → do final (mais antigo).
        ignorar_nao_assinados: pular documentos não assinados.

    Nota: apenas um de `tipos` ou `padrao_regex` precisa casar.
    """
    candidatos: Any = reversed(timeline) if not mais_recente else iter(timeline)
    tipos_lower = [t.lower() for t in tipos] if tipos else []

    for doc in candidatos:
        if ignorar_nao_assinados and not doc.is_assinado:
            continue

        texto_busca = f"{doc.tipo} {doc.titulo}".lower()

        if tipos_lower and doc.tipo.lower() in tipos_lower:
            return doc
        if padrao_regex and re.search(padrao_regex, texto_busca, re.IGNORECASE):
            return doc

    return None


def obter_conteudo_doc(
    driver_ou_sessao: Union[WebDriver, requests.Session],
    id_processo: str,
    id_documento: str,
    *,
    host: str = TRT2_HOST,
) -> Optional[str]:
    """
    1 GET — retorna texto limpo do documento.

    Estratégias em ordem:
    1. GET /documentos/id/{id} → campos inline (conteudo, conteudoHtml, etc.)
    2. GET /documentos/id/{id}/conteudo
    3. GET /documentos/id/{id}/conteudoHtml

    Se o Content-Type for PDF, retorna CONTEUDO_PDF ('__PDF__') como sinal
    para o caller usar extração Selenium (extrair_direto / _JS_EXTRAIR_OBJECT).

    Returns:
        Texto limpo, CONTEUDO_PDF se for PDF, ou None se falhar.
    """
    if isinstance(driver_ou_sessao, WebDriver):
        sess = _sessao_do_driver(driver_ou_sessao, host)
    else:
        sess = driver_ou_sessao

    # 1. documento_por_id — pode trazer conteúdo inline
    url_doc = (
        f"{host}/pje-comum-api/api/processos/id/{id_processo}"
        f"/documentos/id/{id_documento}"
    )
    try:
        r = sess.get(
            url_doc,
            params={
                'incluirAssinatura': 'false',
                'incluirAnexos': 'false',
                'incluirMovimentos': 'false',
                'incluirApreciacao': 'false',
            },
            timeout=15,
        )
        if r.ok:
            dados = r.json()
            for k in ('conteudo', 'conteudoHtml', 'conteudoTexto', 'texto', 'html', 'previewModeloDocumento'):
                v = dados.get(k)
                if isinstance(v, str) and v.strip():
                    return _limpar_html(v)
    except Exception as e:
        logger.debug('[TIMELINE] documento_por_id %s: %s', id_documento, e)

    # 2 + 3. Endpoints de conteúdo direto
    for path in (
        f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/conteudo",
        f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/conteudoHtml",
    ):
        try:
            r = sess.get(f"{host}{path}", timeout=15)
            if not r.ok:
                continue
            ctype = (r.headers.get('Content-Type') or '').lower()
            if 'pdf' in ctype or 'octet-stream' in ctype:
                # Registrar info do response para diagnóstico
                logger.info('[TIMELINE] doc %s returned Content-Type=%s length=%s', id_documento, ctype, len(r.content) if r.content is not None else 0)
                # Tentar extrair texto do PDF em-processo (quando possível) para evitar
                # depender exclusivamente do fallback Selenium. Preferir extratores já
                # existentes no projeto (Triagem.coleta) que usam pdfplumber + OCR.
                try:
                    # 1) Tentativa rápida com PyPDF2 se disponível
                    import io
                    texto_extraido = ''
                    try:
                        from PyPDF2 import PdfReader
                    except Exception:
                        PdfReader = None
                    if PdfReader is not None:
                        try:
                            content_bytes = r.content
                            reader = PdfReader(io.BytesIO(content_bytes))
                            pages = []
                            for p in getattr(reader, 'pages', []):
                                try:
                                    txt = p.extract_text() or ''
                                except Exception as e_page:
                                    logger.debug('[TIMELINE] erro extraindo página PDF %s: %s', getattr(p, 'page_number', '?'), e_page)
                                    txt = ''
                                pages.append(txt)
                            texto_extraido = '\n\n--- PÁGINA ---\n\n'.join(pages).strip()
                        except Exception as e_pdf:
                            logger.debug('[TIMELINE] extração PyPDF2 falhou: %s', e_pdf)

                    # 2) Se PyPDF2 não obteve texto, tentar o extrator robusto do módulo Triagem
                    if not texto_extraido:
                        try:
                            from Triagem.coleta import _extrair_texto_pdf_api
                            try:
                                # Criar cliente leve compatível com o extrator
                                from api.variaveis_client import PjeApiClient
                                client = PjeApiClient(sess, host)
                                texto_triagem = _extrair_texto_pdf_api(client, id_processo, id_documento)
                                if texto_triagem:
                                    logger.info('[TIMELINE] extração via Triagem.coleta bem-sucedida (doc %s)', id_documento)
                                    return texto_triagem
                            except Exception as e_tri:
                                logger.debug('[TIMELINE] erro ao usar Triagem.coleta extractor: %s', e_tri)
                        except Exception:
                            # Triagem não disponível ou import falhou; prosseguir
                            pass

                    if texto_extraido:
                        logger.info('[TIMELINE] extração in-process PDF bem-sucedida (doc %s)', id_documento)
                        return texto_extraido

                except Exception as e_pdf:
                    logger.debug('[TIMELINE] extração in-process PDF falhou (geral): %s', e_pdf)

                logger.info('[TIMELINE] doc %s é PDF — sinalizar para extração Selenium', id_documento)
                return CONTEUDO_PDF
            if 'json' in ctype:
                j = r.json()
                for k in ('conteudo', 'conteudoHtml', 'texto', 'previewModeloDocumento'):
                    v = j.get(k)
                    if isinstance(v, str) and v.strip():
                        return _limpar_html(v)
            elif r.text:
                return _limpar_html(r.text)
        except Exception as e:
            logger.debug('[TIMELINE] conteudo path %s: %s', path, e)

    return None


def obter_timeline_com_conteudo(
    driver_ou_sessao: Union[WebDriver, requests.Session],
    id_processo: str,
    *,
    host: str = TRT2_HOST,
    tipos_alvo: Optional[List[str]] = None,
    padrao_regex_alvo: Optional[str] = None,
    max_docs: int = 1,
    mais_recente: bool = True,
) -> List[DocTimeline]:
    """
    1 GET de timeline + até max_docs GETs de conteúdo para documentos que casam.

    Args:
        tipos_alvo: match exato em doc.tipo (case-insensitive).
        padrao_regex_alvo: re.search aplicado em '{doc.tipo} {doc.titulo}'.
        max_docs: limite de documentos com conteúdo baixado (evita N+1 excessivo).
        mais_recente: True → começa pelo mais recente; False → pelo mais antigo.

    Returns:
        Lista de DocTimeline com .conteudo preenchido. Docs que não casam não são incluídos.
    """
    if isinstance(driver_ou_sessao, WebDriver):
        sess = _sessao_do_driver(driver_ou_sessao, host)
    else:
        sess = driver_ou_sessao

    timeline = obter_timeline(sess, id_processo, host=host)
    if not timeline:
        return []

    tipos_lower = [t.lower() for t in tipos_alvo] if tipos_alvo else []
    candidatos: Any = reversed(timeline) if not mais_recente else iter(timeline)

    resultado: List[DocTimeline] = []
    for doc in candidatos:
        if len(resultado) >= max_docs:
            break
        if not doc.id_interno:
            continue

        texto_busca = f"{doc.tipo} {doc.titulo}".lower()
        casou = (
            (tipos_lower and doc.tipo.lower() in tipos_lower) or
            (padrao_regex_alvo and bool(re.search(padrao_regex_alvo, texto_busca, re.IGNORECASE)))
        )
        if casou:
            doc.conteudo = obter_conteudo_doc(sess, id_processo, doc.id_interno, host=host)
            resultado.append(doc)

    return resultado
