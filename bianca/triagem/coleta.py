# -*- coding: utf-8 -*-
"""
bianca/triagem/coleta.py -- Coleta de textos do processo via API PJe.

Extrai da peticao inicial, certidao de distribuicao e anexos
(procuracao, documentos de identidade) usando a API REST do PJe.

Funcoes:
    _coletar_textos_processo(driver)  Funcao principal de coleta.
    _extrair_texto_pdf_api(...)       Extrai texto de PDF via API.
    _parsear_capa(texto)              Extrai campos da certidao de distribuicao.
    _ocr_via_pymupdf(...)             OCR fallback (lazy import).
    _garantir_tessdata_por()          Baixa por.traineddata se necessario.
"""

import io
import logging
import re
from typing import Any, Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from bianca.api_client import PjeApiClient, session_from_driver
from bianca.triagem.preprocess import _strip_cabecalho_rodape
from bianca.triagem.utils import _norm, logger as _parent_logger
from Fix.variaveis import obter_texto_documento

logger = logging.getLogger("bianca.triagem.coleta")


# =============================================================================
# Helpers de URL
# =============================================================================


def _extrair_id_processo_da_url(url: str) -> Optional[str]:
    """Extrai o id numerico do processo da URL atual do PJe."""
    if not url:
        return None
    match = re.search(r'/processo/(\d+)(?:/|$)', url)
    return match.group(1) if match else None


# =============================================================================
# Excecoes customizadas
# =============================================================================


class _ErroAutenticacao401(Exception):
    """401 Unauthorized na API PJe -- sessao expirada, necessario re-auth."""


# =============================================================================
# OCR fallback
# =============================================================================

_TESSDATA_LOCAL = None  # resolvido em tempo de execucao pelo path do modulo


def _garantir_tessdata_por():
    """Garante por.traineddata em cache/tessdata local. Retorna o diretorio ou None."""
    import pathlib
    import urllib.request

    global _TESSDATA_LOCAL
    if _TESSDATA_LOCAL is None:
        _TESSDATA_LOCAL = (
            pathlib.Path(__file__).resolve().parent.parent / "cache" / "tessdata"
        )
    tessdata_dir = _TESSDATA_LOCAL
    tessdata_dir.mkdir(parents=True, exist_ok=True)
    destino = tessdata_dir / "por.traineddata"
    if destino.exists():
        return tessdata_dir
    url = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/por.traineddata"
    logger.debug("OCR: baixando por.traineddata de tessdata_fast...")
    try:
        urllib.request.urlretrieve(url, destino)
        logger.debug("OCR: por.traineddata salvo em %s", destino)
        return tessdata_dir
    except Exception as e:
        logger.error("ERRO em _garantir_tessdata_por: %s: %s", type(e).__name__, e)
        return None


def _ocr_via_pymupdf(
    pdf_bytes: bytes, id_doc: str, fallback: str, fracao: float = 0.5
) -> str:
    """Renderiza a fracao superior de cada pagina com PyMuPDF e extrai texto via tesseract.

    Dependencias pesadas (pytesseract, fitz, PIL) importadas lazy dentro da funcao.
    """
    try:
        import pathlib as _pl
        import os as _os

        import pytesseract  # noqa
        import fitz  # noqa
        from PIL import Image  # noqa

        _tess_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"D:\Tesseract-OCR\tesseract.exe",
        ]
        tess_exe = None
        for _c in _tess_candidates:
            if _pl.Path(_c).exists():
                tess_exe = _pl.Path(_c)
                pytesseract.pytesseract.tesseract_cmd = str(tess_exe)
                break
        if tess_exe is None:
            logger.error("ERRO em _ocr_via_pymupdf: tesseract.exe nao encontrado para %s", id_doc)
            return fallback
        tessdata_dir = _garantir_tessdata_por()
        if tessdata_dir:
            _os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
            lang = "por"
        else:
            _os.environ.setdefault(
                "TESSDATA_PREFIX",
                str(tess_exe.parent / "tessdata"),
            )
            lang = "osd"
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        textos_ocr = []
        for page in doc:
            rect = page.rect
            clip = fitz.Rect(
                rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * fracao
            )
            pix = page.get_pixmap(dpi=300, clip=clip)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            t = pytesseract.image_to_string(img, lang=lang)
            if t.strip():
                textos_ocr.append(t)
        resultado = "\n".join(textos_ocr).strip()
        logger.debug(
            "OCR PyMuPDF %s: %s chars (%s pag, fracao=%s)",
            id_doc,
            len(resultado),
            len(doc),
            fracao,
        )
        return resultado if resultado else fallback
    except ImportError as e:
        logger.error("ERRO em _ocr_via_pymupdf: %s: %s", type(e).__name__, e)
        return fallback
    except Exception as e:
        logger.error("ERRO em _ocr_via_pymupdf: %s: %s", type(e).__name__, e)
        return fallback


# =============================================================================
# Helpers de coleta de documentos
# =============================================================================


def _eh_certidao_distribuicao_doc(documento: dict) -> bool:
    """Verifica se o documento e uma certidao de distribuicao."""
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'certidao' in txt and 'distribuicao' in txt and 'redistribuicao' not in txt:
            return True
    return False


def _listar_documentos_timeline(timeline: list) -> list:
    """Lista todos os documentos (inclusive anexos) da timeline."""
    docs = []
    for item in timeline or []:
        if not isinstance(item, dict):
            continue
        docs.append(item)
        for anexo in item.get('anexos') or []:
            if isinstance(anexo, dict):
                docs.append(anexo)
    return docs


# =============================================================================
# Parse de capa (certidao de distribuicao)
# =============================================================================


def _parsear_capa(texto: str) -> dict:
    """Extrai campos estruturados da certidao de distribuicao."""
    dados: Dict[str, Any] = {
        'numero_processo': None, 'segredo_justica': None, 'medida_urgencia': None,
        'rito_declarado': None, 'valor_causa': None, 'classe_judicial': None,
        'reclamante_nome': None, 'reclamante_cpf': None,
        'reclamado_nome': None, 'reclamado_cnpj': None,
        'distribuido_em': None,
    }
    n = _norm(texto)
    m = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
    if m:
        dados['numero_processo'] = m.group(1)
    m = re.search(r'segredo de justic[aç][:\s]+(sim|n[aã]o)', n)
    if m:
        dados['segredo_justica'] = m.group(1).startswith('s')
    m = re.search(r'medida de urgencia[:\s]+(sim|n[aã]o)', n)
    if m:
        dados['medida_urgencia'] = m.group(1).startswith('s')
    m = re.search(r'classe judicial[:\s]+(.+?)(?:\n|\(|\r)', texto, re.IGNORECASE)
    if m:
        dados['classe_judicial'] = m.group(1).strip()
        cl = _norm(dados['classe_judicial'])
        if 'sumarissimo' in cl:
            dados['rito_declarado'] = 'SUMARISSIMO'
        elif 'ordinario' in cl:
            dados['rito_declarado'] = 'ORDINARIO'
    m = re.search(r'valor da causa[:\s]+R\$\s*([\d\.,]+)', texto, re.IGNORECASE)
    if m:
        try:
            dados['valor_causa'] = float(m.group(1).replace('.', '').replace(',', '.'))
        except ValueError:
            pass
    else:
        m2 = re.search(r'valor da causa', texto, re.IGNORECASE)
        if m2:
            trecho = texto[m2.end(): m2.end() + 400]
            mv = re.search(r'R\$\s*([\d\.,]+)', trecho)
            if mv:
                try:
                    dados['valor_causa'] = float(mv.group(1).replace('.', '').replace(',', '.'))
                except ValueError:
                    pass
    m = re.search(r'distribui[íi]d[oa]\s+em\s+(\d{1,2}/\d{2}/\d{4})', texto, re.IGNORECASE)
    if m:
        dados['distribuido_em'] = m.group(1)
    return dados


# =============================================================================
# Extracao de texto de PDF via API
# =============================================================================


def _extrair_texto_pdf_api(
    client: "PjeApiClient", id_processo: str, id_doc: str
) -> str:
    """Extrai texto de PDF via API, com fallback para OCR se texto nativo insuficiente.

    Dependencia pesada (pdfplumber) importada lazy dentro da funcao.
    """
    LIMIAR = 200
    import time as _t

    tempo_inicio = _t.time()

    try:
        import pdfplumber  # noqa
    except ImportError:
        return ""

    url = client._url(
        f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo"
    )
    try:
        resp = client.sess.get(url, timeout=60)
        if resp.status_code == 401:
            raise _ErroAutenticacao401(f"401 Unauthorized -- doc {id_doc}")
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "").lower()
        # Aceita PDF tanto por Content-Type quanto por magic bytes (%PDF-)
        # A API pode retornar application/octet-stream em vez de application/pdf
        is_pdf_by_type  = "pdf" in ctype
        is_pdf_by_magic = resp.content[:5] == b"%PDF-"
        if not is_pdf_by_type and not is_pdf_by_magic:
            logger.warning(
                "_extrair_texto_pdf_api: doc %s nao e PDF (Content-Type=%s, magic=%r)",
                id_doc, ctype, resp.content[:8]
            )
            return ""
        if not is_pdf_by_type and is_pdf_by_magic:
            logger.debug("_extrair_texto_pdf_api: doc %s detectado como PDF por magic bytes (Content-Type=%s)", id_doc, ctype)

        pdf_bytes = resp.content
        textos = []
        total = 0
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total = len(pdf.pages)
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    textos.append(t)

        texto_nativo = "\n".join(textos).strip()
        media = len(texto_nativo) / total if total else 0
        if media >= LIMIAR:
            logger.debug(
                "PDF %s: texto nativo OK (%s chars, %s pag, media=%.0f)",
                id_doc,
                len(texto_nativo),
                total,
                media,
            )
            return texto_nativo
        logger.debug(
            "PDF %s: texto nativo insuficiente (%s chars, %s pag, media=%.0f) -- tentando OCR",
            id_doc,
            len(texto_nativo),
            total,
            media,
        )
        return _ocr_via_pymupdf(pdf_bytes, id_doc, texto_nativo)
    except _ErroAutenticacao401:
        raise
    except Exception as e:
        logger.error("ERRO em _extrair_texto_pdf_api: %s: %s", type(e).__name__, e)
        return ""


# =============================================================================
# Coleta principal
# =============================================================================


def _coletar_textos_processo(driver) -> Dict[str, Any]:
    """Coleta textos do processo via API PJe para analise de triagem.

    Extrai da peticao inicial, certidao de distribuicao e anexos
    (procuracao, documentos de identidade) usando a API REST do PJe.

    Returns:
        Dict com:
            texto_inicial (str)         -- texto da peticao inicial.
            texto_capa (str)            -- texto da certidao de distribuicao.
            capa_dados (dict)           -- dados parseados da capa + partes.
            anexos (list[dict])         -- anexos relevantes.
            id_processo (str|None)      -- id do processo.
            associados_sistema (list)   -- processos associados.
            erro (str|None)             -- mensagem de erro se houver.
    """
    logger.debug('_coletar_textos_processo: inicializando...')
    resultado: Dict[str, Any] = {
        'texto_inicial': '',
        'texto_capa': '',
        'capa_dados': {},
        'anexos': [],
        'id_processo': None,
        'associados_sistema': [],
        'erro': None,
    }

    try:
        sessao, trt_host = session_from_driver(driver, grau=1)
        client = PjeApiClient(sessao, trt_host, grau=1)
    except Exception as e:
        resultado['erro'] = 'falha ao montar cliente autenticado: %s' % e
        return resultado

    id_processo = _extrair_id_processo_da_url(driver.current_url)
    if not id_processo:
        resultado['erro'] = 'id_processo nao encontrado na URL: %s' % driver.current_url
        return resultado

    resultado['id_processo'] = id_processo

    # Buscar partes via API para enriquecer capa_dados
    try:
        partes_raw = client.partes(id_processo) or {}
    except Exception as e:
        logger.warning("partes_api falhou: %s", e)
        partes_raw = {}

    # Buscar timeline
    try:
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    except Exception as e:
        resultado['erro'] = 'timeline falhou: %s' % e
        return resultado

    if not timeline:
        resultado['erro'] = 'timeline vazia ou indisponivel'
        return resultado

    # Localizar peticao inicial
    peticao = None
    for doc in timeline:
        if not isinstance(doc, dict):
            continue
        tipo = _norm(doc.get('tipo') or '')
        titulo = _norm(doc.get('titulo') or '')
        if 'peticao inicial' in tipo or 'peticao inicial' in titulo:
            peticao = doc
            break

    if not peticao:
        resultado['erro'] = 'peticao inicial nao localizada na timeline'
        return resultado

    # Extrair texto da peticao inicial
    id_inicial = str(peticao.get('id') or peticao.get('idUnicoDocumento') or '')
    if not id_inicial:
        resultado['erro'] = 'id do documento da peticao inicial nao disponivel'
        return resultado

    try:
        # Usar funcao robusta que tenta multiplos campos e endpoints
        texto_inicial = obter_texto_documento(client, id_processo, id_inicial) or ''
        if texto_inicial:
            logger.debug('texto_inicial extraido: %s chars via obter_texto_documento', len(texto_inicial))
        else:
            logger.warning('AVISO: obter_texto_documento retornou vazio para documento %s. Tentando OCR fallback...', id_inicial)
    except Exception as e:
        logger.warning("obter_texto_documento falhou: %s. Tentando OCR...", e)
        texto_inicial = ''

    # fallback OCR -- se API retornou texto vazio
    if not texto_inicial and id_inicial:
        logger.info('FALLBACK: Tentando OCR para documento %s...', id_inicial)
        try:
            texto_inicial = _extrair_texto_pdf_api(client, id_processo, id_inicial) or ''
            if texto_inicial:
                logger.debug('texto_inicial via OCR: %s chars', len(texto_inicial))
            else:
                logger.warning('AVISO: OCR retornou texto vazio para documento %s', id_inicial)
        except Exception as e:
            logger.warning('OCR fallback falhou: %s', e)

    # Stripar cabecalho/rodape
    if texto_inicial:
        texto_antes = len(texto_inicial)
        texto_inicial = _strip_cabecalho_rodape(texto_inicial)
        texto_depois = len(texto_inicial)
        logger.debug('_strip_cabecalho_rodape: %s chars -> %s chars', texto_antes, texto_depois)
        if texto_depois == 0:
            logger.warning('ALERTA: _strip_cabecalho_rodape removeu TODO o conteúdo (tinha %s chars)', texto_antes)
    resultado['texto_inicial'] = texto_inicial

    # Coletar anexos (procuracao, documento identidade)
    documentos_timeline = _listar_documentos_timeline(timeline)
    anexos_raw = peticao.get('anexos') or []
    if not anexos_raw:
        anexos_raw = [d for d in documentos_timeline
                      if isinstance(d, dict) and d.get('idDocumentoPai') == peticao.get('id')]
    anexos_extraidos = []
    for anx in anexos_raw:
        if not isinstance(anx, dict):
            continue
        titulo = _norm(anx.get('titulo') or '')
        tipo = _norm(anx.get('tipo') or '')
        txt = titulo + ' ' + tipo
        is_proc = any(t in txt for t in ['procuracao', 'procuração'])
        is_id = any(t in txt for t in ['rg', 'cnh', 'identidade', 'cpf', 'identificacao'])
        if is_proc or is_id:
            id_anx = str(anx.get('id') or anx.get('idUnicoDocumento') or '')
            texto_anx = ''
            if id_anx:
                try:
                    # Usar funcao robusta que tenta multiplos campos e endpoints
                    texto_anx = obter_texto_documento(client, id_processo, id_anx) or ''
                    if texto_anx:
                        logger.debug('anexo %s extraido: %s chars', id_anx, len(texto_anx))
                except Exception as e:
                    logger.debug('obter_texto_documento para anexo %s falhou: %s', id_anx, e)
                    
                # Fallback: PDF + OCR (apenas para procuracao, para otimizar)
                if not texto_anx and is_proc:
                    try:
                        texto_anx = _extrair_texto_pdf_api(client, id_processo, id_anx) or ''
                        if texto_anx:
                            logger.debug('procuracao OCR fallback %s chars', len(texto_anx))
                    except _ErroAutenticacao401 as e:
                        resultado['erro'] = 'ERRO_CRITICO_401: anexo %s -- %s' % (id_anx, e)
                        return resultado
                    except Exception as e:
                        logger.warning('OCR fallback para procuracao falhou: %s', e)
            anexos_extraidos.append({
                'titulo': anx.get('titulo') or anx.get('tipo') or '',
                'tipo': anx.get('tipo') or '',
                'texto': texto_anx,
            })
    resultado['anexos'] = anexos_extraidos

    # Certidao de distribuicao
    _data_pi = (peticao.get('data') or '')[:10]
    candidatas_cert = [d for d in documentos_timeline if _eh_certidao_distribuicao_doc(d)]
    certidao = None
    if candidatas_cert:
        certidao = next(
            (d for d in candidatas_cert if (d.get('data') or '')[:10] == _data_pi),
            candidatas_cert[0])
    texto_capa = ''
    if certidao:
        id_cert = str(certidao.get('id') or certidao.get('idUnicoDocumento') or '')
        if id_cert:
            try:
                # Tentar via API primeiro (pode ser HTML/texto)
                texto_capa = obter_texto_documento(client, id_processo, id_cert) or ''
                if not texto_capa:
                    # Fallback para PDF via OCR
                    logger.debug('certidao: obter_texto_documento retornou vazio, tentando PDF/OCR')
                    texto_capa = _extrair_texto_pdf_api(client, id_processo, id_cert) or ''
                if texto_capa:
                    logger.debug('certidao_distribuicao: %s chars', len(texto_capa))
            except _ErroAutenticacao401 as e:
                resultado['erro'] = 'ERRO_CRITICO_401: certidao %s -- %s' % (id_cert, e)
                return resultado
    resultado['texto_capa'] = texto_capa

    # Processos associados (prevencao)
    try:
        url_assoc = client._url(
            f'/pje-comum-api/api/processos/id/{id_processo}/processosAssociados')
        r_assoc = client.sess.get(url_assoc, timeout=10)
        if r_assoc.ok:
            _assoc = r_assoc.json()
            resultado['associados_sistema'] = _assoc if isinstance(_assoc, list) else []
            logger.debug('associados_sistema: %s', len(resultado['associados_sistema']))
        else:
            resultado['associados_sistema'] = []
    except Exception as _e_assoc:
        logger.debug('associados_sistema: falha (%s) - continuando', _e_assoc)
        resultado['associados_sistema'] = []

    # Partes com endereco para enriquecimento
    _partes_endereco: dict = {}
    try:
        url_end = client._url(
            f'/pje-comum-api/api/processos/id/{id_processo}/partes?retornaEndereco=true')
        r_end = client.sess.get(url_end, timeout=15)
        if r_end.ok:
            _partes_endereco = r_end.json()
    except Exception as _e_end:
        logger.debug('partes_endereco: falha (%s)', _e_end)

    # Enriquecer capa_dados com certidao + partes
    cd: Dict[str, Any] = _parsear_capa(texto_capa) if texto_capa else {}
    if partes_raw:
        ativos = partes_raw.get('ATIVO') or []
        passivos = partes_raw.get('PASSIVO') or []
        if ativos:
            doc_ativo = re.sub(r'\D', '', ativos[0].get('documento') or '')
            cd['reclamante_nome'] = ativos[0].get('nome', '').strip()
            if len(doc_ativo) == 11:
                cd['reclamante_cpf'] = doc_ativo
            # Municipio/UF do reclamante via partes+endereco
            _ativos_end = (_partes_endereco.get('ATIVO') or [])
            if _ativos_end:
                _end_obj = _ativos_end[0].get('endereco') or {}
                _mun = _norm(_end_obj.get('municipio') or '')
                _uf = _norm(_end_obj.get('uf') or '')
                if _mun or _uf:
                    cd['reclamante_municipio'] = _mun
                    cd['reclamante_uf'] = _uf
                    cd['reclamante_end_fonte'] = 'api'
                else:
                    cd['reclamante_end_fonte'] = 'api_vazio'
            else:
                cd['reclamante_end_fonte'] = 'api_sem_ativo'

        if passivos:
            reclamados_lista = []
            for p in passivos:
                doc_p = re.sub(r'\D', '', p.get('documento') or '')
                reclamados_lista.append({'nome': p.get('nome', '').strip(), 'cpfcnpj': doc_p})

            # Enriquecer reclamados com CEP/endereco + detectar sem_endereco e dom_elet
            reclamadas_sem_endereco = []
            reclamadas_com_dom_elet = 0
            for _parte in (_partes_endereco.get('PASSIVO') or []):
                nome_parte = _parte.get('nome', '').strip()
                if _parte.get('enderecoDesconhecido', False):
                    reclamadas_sem_endereco.append(nome_parte)
                id_parte_pj = str(
                    _parte.get('idPessoa') or _parte.get('id') or
                    _parte.get('idParticipante') or _parte.get('idParte') or '')
                dom_via_api = client.domicilio_eletronico(id_parte_pj) if id_parte_pj else None
                dom_flag_raw = (_parte.get('domicilioEletronico')
                                or _parte.get('possuiDomicilioEletronico'))
                tem_domicilio = dom_via_api if dom_via_api is not None else (dom_flag_raw is True)
                if tem_domicilio:
                    reclamadas_com_dom_elet += 1
                endereco = _parte.get('endereco') or {}
                cep_raw = endereco.get('nroCep') or ''
                cep = re.sub(r'[^\d]', '', cep_raw) if cep_raw else None
                doc_parte = re.sub(r'\D', '', _parte.get('documento') or '')
                if cep and len(cep) == 8:
                    for item in reclamados_lista:
                        if item.get('cpfcnpj') == doc_parte or item.get('nome') == nome_parte:
                            item['cep'] = cep
                            logradouro = endereco.get('logradouro') or endereco.get('descricao') or ''
                            if logradouro:
                                item['endereco'] = logradouro
                            break

            cd['reclamados'] = reclamados_lista
            cd['reclamadas_sem_endereco'] = reclamadas_sem_endereco
            cd['reclamadas_com_dom_elet'] = reclamadas_com_dom_elet
            if reclamados_lista:
                prim = reclamados_lista[0]
                cd['reclamado_nome'] = prim['nome']
                if len(prim['cpfcnpj']) == 14:
                    cd['reclamado_cnpj'] = prim['cpfcnpj']
                elif len(prim['cpfcnpj']) == 11:
                    cd['reclamado_cpf'] = prim['cpfcnpj']

    # juizo_digital e valor_causa via processo_por_id
    try:
        proc_dados = client.processo_por_id(id_processo) or {}
        juizo_digital = proc_dados.get('juizoDigital')
        if isinstance(juizo_digital, str):
            juizo_digital = juizo_digital.lower() == 'true'
        elif juizo_digital is not None:
            juizo_digital = bool(juizo_digital)
        cd['juizo_digital'] = juizo_digital
        valor_api = (proc_dados.get('valorCausa')
                     or proc_dados.get('valorDaCausa')
                     or proc_dados.get('valor'))
        if valor_api is not None and cd.get('valor_causa') is None:
            try:
                cd['valor_causa'] = float(valor_api)
            except (TypeError, ValueError):
                pass
    except Exception as _e_proc:
        logger.debug('processo_por_id: falha (%s)', _e_proc)

    resultado['capa_dados'] = cd
    logger.debug('_coletar_textos_processo: concluido (campos: %s)', list(cd.keys()))
    return resultado
