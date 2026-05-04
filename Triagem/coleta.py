"""Camada de coleta: API / PDF / OCR e construção dos textos brutos do processo.

Move para aqui responsabilidades de extração via PJe API, leitura de PDF,
OCR (quando disponível) e montagem do dicionário de resultados usado pela
triagem principal.
"""
import re
import io
import threading
from typing import List, Dict, Any

import pathlib
from api.variaveis import PjeApiClient, session_from_driver
from Fix.variaveis_helpers import obter_texto_documento
from Triagem.preprocess import _strip_cabecalho_rodape
from Triagem.utils import _norm, _formatar_endereco_parte
from Fix.log import logger

# Diretório local para tessdata — evita gravar em Program Files (requer admin)
_TESSDATA_LOCAL = pathlib.Path(__file__).parent.parent / 'cache' / 'tessdata'


def _extrair_id_processo_da_url(url: str):
    if not url:
        return None
    match = re.search(r'/processo/(\d+)(?:/|$)', url)
    return match.group(1) if match else None


def _eh_peticao_inicial(documento: dict) -> bool:
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    return 'peticao inicial' in tipo or 'peticao inicial' in titulo


def _eh_certidao_distribuicao(documento: dict) -> bool:
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'certidao' in txt and 'distribuicao' in txt and 'redistribuicao' not in txt:
            return True
    return False


def _eh_procuracao(documento: dict) -> bool:
    tipo = _norm(documento.get('tipo') or '')
    titulo = _norm(documento.get('titulo') or '')
    for txt in (tipo, titulo):
        if 'procuracao' in txt or 'procuração' in txt:
            return True
    return False


def _eh_documento_identidade(documento: dict) -> bool:
    titulo = _norm(documento.get('titulo') or '')
    tipo = _norm(documento.get('tipo') or '')
    palavras_chave = [
        'rg', 'cnh', 'identidade', 'cpf', 'passport', 'passaporte',
        'identificacao', 'documento pessoal', 'documento de identificacao',
    ]
    return any(p in titulo or p in tipo for p in palavras_chave)


def _parsear_capa(texto: str) -> dict:
    dados = {
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

    m = re.search(r'Partes[:\s]+(.+?)\s+-\s+([\d\.\-]+)\s+[Xx]\s+(.+?)\s+-\s+([\d\.\/\-]+)', texto)
    if m:
        dados['reclamante_nome'] = m.group(1).strip()
        dados['reclamante_cpf'] = re.sub(r'\D', '', m.group(2))
        dados['reclamado_nome'] = m.group(3).strip()
        dados['reclamado_cnpj'] = re.sub(r'\D', '', m.group(4))
    else:
        mr = re.search(r'RECLAMANTE\s*[\n\r]+\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][^\n\r]+)', texto)
        if mr:
            dados['reclamante_nome'] = mr.group(1).strip()
        md = re.search(r'RECLAMAD[AO]\s*[\n\r]+\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][^\n\r]+)', texto)
        if md:
            dados['reclamado_nome'] = md.group(1).strip()

    m = re.search(r'distribui[íi]d[oa]\s+em\s+(\d{1,2}/\d{2}/\d{4})', texto, re.IGNORECASE)
    if m:
        dados['distribuido_em'] = m.group(1)

    return dados


def _pag_contexto(texto: str, posicao: int, janela: int = 400) -> str:
    pag = 1
    for mp in re.finditer(r'P[aá]gina\s+(\d+)', texto[:posicao], re.IGNORECASE):
        pag = int(mp.group(1))
    inicio = max(0, posicao - janela)
    fim = min(len(texto), posicao + janela)
    trecho = texto[inicio:fim].replace('\n', ' ').strip()
    return f'[pág.{pag}] ...{trecho}...'


class _ErroAutenticacao401(Exception):
    """401 Unauthorized na API PJe — sessão expirada, necessário re-auth."""


def _garantir_tessdata_por() -> 'pathlib.Path | None':
    """Garante por.traineddata em cache/tessdata local. Retorna o diretório ou None."""
    import urllib.request
    tessdata_dir = _TESSDATA_LOCAL
    tessdata_dir.mkdir(parents=True, exist_ok=True)
    destino = tessdata_dir / 'por.traineddata'
    if destino.exists():
        return tessdata_dir
    url = 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/por.traineddata'
    logger.debug('[TRIAGEM] OCR: baixando por.traineddata de tessdata_fast...')
    try:
        urllib.request.urlretrieve(url, destino)
        logger.debug('[TRIAGEM] OCR: por.traineddata salvo em %s', destino)
        return tessdata_dir
    except Exception as e:
        logger.error("ERRO em _garantir_tessdata_por: %s: %s", type(e).__name__, e)
        return None


def _ocr_via_pymupdf(pdf_bytes: bytes, id_doc: str, fallback: str, fracao: float = 0.5) -> str:
    """Renderiza a fração superior de cada página com PyMuPDF e extrai texto via tesseract.

    fracao=0.5 → só metade superior (suficiente para nome do outorgante na procuração).
    """
    try:
        import pytesseract
        import fitz
        from PIL import Image
        import pathlib, os
        _tess_candidates = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'D:\Tesseract-OCR\tesseract.exe',
        ]
        tess_exe = None
        for _c in _tess_candidates:
            if pathlib.Path(_c).exists():
                tess_exe = pathlib.Path(_c)
                pytesseract.pytesseract.tesseract_cmd = str(tess_exe)
                break
        if tess_exe is None:
            logger.error("ERRO em _ocr_via_pymupdf: tesseract.exe nao encontrado para %s", id_doc)
            return fallback
        tessdata_dir = _garantir_tessdata_por()
        if tessdata_dir:
            os.environ['TESSDATA_PREFIX'] = str(tessdata_dir)
            lang = 'por'
        else:
            # fallback: tessdata do próprio tesseract (pode não ter por)
            os.environ.setdefault('TESSDATA_PREFIX', str(tess_exe.parent / 'tessdata'))
            lang = 'osd'
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        textos_ocr = []
        for page in doc:
            rect = page.rect
            clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * fracao)
            pix = page.get_pixmap(dpi=300, clip=clip)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            t = pytesseract.image_to_string(img, lang=lang)
            if t.strip():
                textos_ocr.append(t)
        resultado = '\n'.join(textos_ocr).strip()
        logger.debug('[TRIAGEM] OCR PyMuPDF %s: %s chars (%s pag, fracao=%s)', id_doc, len(resultado), len(doc), fracao)
        return resultado if resultado else fallback
    except ImportError as e:
        logger.error("ERRO em _ocr_via_pymupdf: %s: %s", type(e).__name__, e)
        return fallback
    except Exception as e:
        logger.error("ERRO em _ocr_via_pymupdf: %s: %s", type(e).__name__, e)
        return fallback


def _extrair_texto_pdf_api(client: 'PjeApiClient', id_processo: str, id_doc: str) -> str:
    import time as _t
    LIMIAR = 200  # chars/pagina — abaixo disso tenta OCR (PDF digitalizado/scan)
    tempo_inicio = _t.time()
    
    try:
        import pdfplumber
    except ImportError:
        return ''
    
    url = client._url(
        f'/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo'
    )
    try:
        resp = client.sess.get(url, timeout=60)
        if resp.status_code == 401:
            raise _ErroAutenticacao401(f'401 Unauthorized — doc {id_doc}')
        resp.raise_for_status()
        if 'pdf' not in resp.headers.get('Content-Type', '').lower():
            return ''

        pdf_bytes = resp.content
        textos = []
        total = 0
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total = len(pdf.pages)
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    textos.append(t)

        texto_nativo = '\n'.join(textos).strip()
        media = len(texto_nativo) / total if total else 0
        if media >= LIMIAR:
            logger.debug('[TRIAGEM] PDF %s: texto nativo OK (%s chars, %s pag, media=%.0f)', id_doc, len(texto_nativo), total, media)
            return texto_nativo
        logger.debug('[TRIAGEM] PDF %s: texto nativo insuficiente (%s chars, %s pag, media=%.0f) — tentando OCR via PyMuPDF', id_doc, len(texto_nativo), total, media)

        return _ocr_via_pymupdf(pdf_bytes, id_doc, texto_nativo)
    except _ErroAutenticacao401:
        raise
    except Exception as e:
        logger.error("ERRO em _extrair_texto_pdf_api: %s: %s", type(e).__name__, e)
        return ''


def _listar_documentos_timeline(timeline: list) -> list:
    documentos = []
    for item in timeline or []:
        if not isinstance(item, dict):
            continue
        documentos.append(item)
        for anexo in item.get('anexos') or []:
            if isinstance(anexo, dict):
                documentos.append(anexo)
    return documentos


def _coletar_textos_processo(driver) -> Dict[str, Any]:
    logger.debug('[TRIAGEM] [_coletar] 1/6 Inicializando cliente API...')
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
        logger.debug('[TRIAGEM] [_coletar] Cliente API inicializado')
    except Exception as e:
        resultado['erro'] = f'falha ao montar cliente autenticado: {e}'
        logger.error("ERRO em _coletar_textos_processo: %s: %s", type(e).__name__, e)
        return resultado

    # Helper: tenta extrair PDF; em caso de 401 renova sessão UMA vez e retenta
    _reauth_done = [False]

    def _extrair_com_reauth(id_doc: str) -> str:
        nonlocal client
        try:
            return _extrair_texto_pdf_api(client, id_processo, id_doc)
        except _ErroAutenticacao401:
            if _reauth_done[0]:
                raise
            logger.debug('ERRO em _coletar_textos_processo: 401 doc %s — renovando sessao (tentativa unica)...', id_doc)
            _reauth_done[0] = True
            try:
                s2, h2 = session_from_driver(driver, grau=1)
                client = PjeApiClient(s2, h2, grau=1)
            except Exception as re_err:
                raise _ErroAutenticacao401(f'falha ao renovar sessao: {re_err}') from re_err
            return _extrair_texto_pdf_api(client, id_processo, id_doc)

    id_processo = _extrair_id_processo_da_url(driver.current_url)
    if not id_processo:
        resultado['erro'] = f'id_processo nao encontrado na URL: {driver.current_url}'
        logger.error("ERRO em _coletar_textos_processo: %s", resultado['erro'])
        return resultado

    logger.debug('[TRIAGEM] [_coletar] 2/6 ID processo extraido: %s', id_processo)
    resultado['id_processo'] = id_processo

    # Buscar partes ANTES de ler qualquer PDF — dados do endpoint são definitivos
    _partes_raw: dict = {}
    _partes_endereco: dict = {}
    try:
        _partes_raw = client.partes(id_processo) or {}
        _qtd_a = len(_partes_raw.get('ATIVO') or [])
        _qtd_p = len(_partes_raw.get('PASSIVO') or [])
        logger.debug('[TRIAGEM] partes_api: %s ativo(s), %s passivo(s)', _qtd_a, _qtd_p)

        url_endereco = client._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes?retornaEndereco=true")
        r_endereco = client.sess.get(url_endereco, timeout=15)
        if r_endereco.ok:
            _partes_endereco = r_endereco.json()
            logger.debug('[TRIAGEM] partes+endereco OK - ativo(s)=%s passivo(s)=%s', len(_partes_endereco.get("ATIVO") or []), len(_partes_endereco.get("PASSIVO") or []))
    except Exception as _e_partes:
        logger.error("ERRO em _coletar_textos_processo: partes_api falha (%s)", _e_partes)

    # Buscar processos associados (prevenção detectada pelo sistema)
    try:
        _associados = client.associados(id_processo) or []
        resultado['associados_sistema'] = _associados
        if _associados:
            logger.debug('[TRIAGEM] associados_sistema: %s associado(s) encontrado(s)', len(_associados))
        else:
            logger.debug('[TRIAGEM] associados_sistema: nenhum')
    except Exception as _e_assoc:
        logger.error("ERRO em _coletar_textos_processo: associados_sistema falha (%s)", _e_assoc)
        resultado['associados_sistema'] = []

    # Buscar timeline com timeout para evitar travamentos
    timeline = None
    timeline_erro = None

    def _buscar_timeline():
        nonlocal timeline, timeline_erro
        try:
            logger.debug('[TRIAGEM] Iniciando busca de timeline com timeout (id=%s)', id_processo)
            timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
            logger.debug('[TRIAGEM] Timeline recebida com sucesso')
        except Exception as e:
            timeline_erro = f'erro ao buscar timeline: {e}'
            logger.error("ERRO em _coletar_textos_processo: %s", timeline_erro)

    thread = threading.Thread(target=_buscar_timeline, daemon=False)
    thread.start()
    thread.join(timeout=30)  # Timeout de 30 segundos

    if thread.is_alive():
        logger.error("ERRO em _coletar_textos_processo: TIMEOUT ao buscar timeline — thread ainda ativa apos 30s")
        resultado['erro'] = 'timeout ao buscar timeline (>30s)'
        return resultado

    if timeline_erro:
        resultado['erro'] = timeline_erro
        return resultado

    if not timeline:
        resultado['erro'] = 'timeline vazia ou indisponivel'
        logger.error("ERRO em _coletar_textos_processo: %s", resultado['erro'])
        return resultado

    logger.debug('[TRIAGEM] [_coletar] 3/6 Timeline obtida, processando documentos...')
    documentos = _listar_documentos_timeline(timeline)
    logger.debug('[TRIAGEM] [_coletar] Documentos processados: %s itens', len(documentos) or 0)

    peticao = next((d for d in documentos if _eh_peticao_inicial(d)), None)
    if not peticao:
        resultado['erro'] = 'peticao inicial nao localizada na timeline'
        logger.error("ERRO em _coletar_textos_processo: %s", resultado['erro'])
        return resultado

    logger.debug('[TRIAGEM] [_coletar] 4/6 Peticao inicial localizada, extraindo texto...')

    id_inicial = str(peticao.get('id') or peticao.get('idUnicoDocumento') or '')
    if not id_inicial:
        resultado['erro'] = 'id do documento da peticao inicial nao disponivel'
        logger.error("ERRO em _coletar_textos_processo: %s", resultado['erro'])
        return resultado

    try:
        resultado['texto_inicial'] = _extrair_com_reauth(id_inicial)
    except _ErroAutenticacao401 as e:
        resultado['erro'] = f'ERRO_CRITICO_401: peticao inicial — {e}'
        resultado['erro_critico'] = True
        logger.error("ERRO CRITICO 401 em _coletar_textos_processo: %s", resultado['erro'])
        return resultado
    chars_bruto = len(resultado['texto_inicial'])
    resultado['texto_inicial'] = _strip_cabecalho_rodape(resultado['texto_inicial'])
    chars_limpo = len(resultado['texto_inicial'])
    logger.debug('[TRIAGEM] [_coletar] Texto da peticao extraido: '
           '%s chars bruto → %s chars apos strip cabecalho/rodape '
           '(%s removidos)', chars_bruto, chars_limpo, chars_bruto - chars_limpo)

    anexos_raw = peticao.get('anexos') or []
    if not anexos_raw:
        anexos_raw = [d for d in documentos if d.get('idDocumentoPai') == peticao.get('id')]
        logger.debug('[TRIAGEM] anexos_raw vazios na peticao; fallback para idDocumentoPai encontrou %s itens', len(anexos_raw))

    logger.debug('[TRIAGEM] anexos_raw: %s itens', len(anexos_raw))


    # Filtrar apenas anexos essenciais: Procuração + Documento de Identidade
    procuracoes = [a for a in anexos_raw if _eh_procuracao(a)]
    docs_identidade = [a for a in anexos_raw if _eh_documento_identidade(a)]
    logger.debug('[TRIAGEM] anexos: procuracao=%s doc_identidade=%s (total=%s)', len(procuracoes), len(docs_identidade), len(anexos_raw))

    anexos_extraidos = []
    for anx in procuracoes:
        id_anx = str(anx.get('id') or anx.get('idUnicoDocumento') or '')
        titulo_anx = (anx.get('titulo') or anx.get('tipo') or '').strip()
        logger.debug('[TRIAGEM] procuracao detectada: id=%s titulo="%s"', id_anx or "(sem id)", titulo_anx)
        # Tenta primeiro via API HTML (documentos digitados no sistema)
        texto_anx = ''
        if id_anx:
            try:
                texto_api = obter_texto_documento(client, id_processo, id_anx)
                if texto_api and len(texto_api) > 100:
                    texto_anx = texto_api
                    logger.debug('[TRIAGEM] procuracao extraida via API HTML: %s chars', len(texto_anx))
            except Exception as _e_api:
                logger.debug('[TRIAGEM] procuracao: API HTML falhou (%s), tentando PDF', _e_api)
        # Fallback: PDF + OCR (documentos digitalizados/escaneados)
        if not texto_anx and id_anx:
            try:
                texto_anx = _extrair_com_reauth(id_anx)
            except _ErroAutenticacao401 as e:
                resultado['erro'] = f'ERRO_CRITICO_401: procuracao {id_anx} — {e}'
                resultado['erro_critico'] = True
                logger.error("ERRO CRITICO 401 em _coletar_textos_processo: %s", resultado['erro'])
                return resultado
        if not texto_anx:
            logger.warning('[TRIAGEM] AVISO procuracao extraida vazia: id=%s titulo="%s"', id_anx or "(sem id)", titulo_anx)
        extrato = texto_anx[:400].replace('\n', ' ').strip() if texto_anx else ''
        logger.debug('[TRIAGEM] procuracao extraida: "%s" %s chars | extrato: %r', titulo_anx, len(texto_anx), extrato)
        anexos_extraidos.append({'titulo': titulo_anx, 'tipo': (anx.get('tipo') or '').strip(), 'texto': texto_anx})
    for anx in docs_identidade:
        titulo_anx = (anx.get('titulo') or anx.get('tipo') or '').strip()
        id_anx = str(anx.get('id') or anx.get('idUnicoDocumento') or '')
        logger.debug('[TRIAGEM] doc_identidade detectado: id=%s titulo="%s"', id_anx or "(sem id)", titulo_anx)
        anexos_extraidos.append({'titulo': titulo_anx, 'tipo': (anx.get('tipo') or '').strip(), 'texto': ''})
    resultado['anexos'] = anexos_extraidos

    # Certidão de distribuição: mesma data da petição inicial (campo 'data' da timeline)
    _data_pi = (peticao.get('data') or '')[:10]
    candidatas = [d for d in documentos if _eh_certidao_distribuicao(d)]
    certidao = None
    if candidatas:
        certidao = next(
            (d for d in candidatas if (d.get('data') or '')[:10] == _data_pi),
            candidatas[0])
    texto_capa = ''
    if certidao:
        id_cert = str(certidao.get('id') or certidao.get('idUnicoDocumento') or '')
        titulo_cert = (certidao.get('titulo') or certidao.get('tipo') or '(sem titulo)').strip()
        logger.debug('[TRIAGEM] certidao_distribuicao: localizada id=%s titulo="%s"', id_cert, titulo_cert)
        if id_cert:
            try:
                texto_capa = _extrair_com_reauth(id_cert)
            except _ErroAutenticacao401 as e:
                resultado['erro'] = f'ERRO_CRITICO_401: certidao {id_cert} — {e}'
                resultado['erro_critico'] = True
                logger.error("ERRO CRITICO 401 em _coletar_textos_processo: %s", resultado['erro'])
                return resultado
            if texto_capa:
                logger.debug('[TRIAGEM] certidao_distribuicao: extracao OK chars=%s', len(texto_capa))
            else:
                logger.warning('[TRIAGEM] certidao_distribuicao: ERRO - texto extraido vazio (PDF sem texto nativo e OCR indisponivel ou falhou)')
        else:
            logger.warning('[TRIAGEM] certidao_distribuicao: ERRO - id do documento nao disponivel na timeline')
    else:
        nomes = [(_norm(d.get('titulo') or d.get('tipo') or '')) for d in documentos[:12]]
        logger.warning('[TRIAGEM] certidao_distribuicao: NAO LOCALIZADA - docs disponiveis (ate 12): %s', nomes)

    resultado['texto_capa'] = texto_capa
    if texto_capa:
        resultado['capa_dados'] = _parsear_capa(texto_capa)
    else:
        resultado['capa_dados'] = {}
        logger.debug('[TRIAGEM] capa_dados: nao extraidos (certidao ausente ou vazia) - B13/rito indisponivel')

    # Enriquecer capa_dados com partes definitivas da API (sobrescreve certidão quando disponível)
    if _partes_raw:
        ativos = _partes_raw.get('ATIVO') or []
        passivos = _partes_raw.get('PASSIVO') or []
        if ativos:
            doc_ativo = re.sub(r'\D', '', ativos[0].get('documento') or '')
            resultado['capa_dados']['reclamante_nome'] = ativos[0].get('nome', '').strip()
            if len(doc_ativo) == 11:
                resultado['capa_dados']['reclamante_cpf'] = doc_ativo
            _ativos_end = _partes_endereco.get('ATIVO') or []
            if _ativos_end:
                _ativo_end_obj = _ativos_end[0].get('endereco') or {}
                _cep_rec_raw = _ativo_end_obj.get('nroCep') or ''
                _cep_rec = re.sub(r'[^\d]', '', _cep_rec_raw) if _cep_rec_raw else None
                if _cep_rec and len(_cep_rec) == 8:
                    resultado['capa_dados']['reclamante_cep'] = _cep_rec
                _mun_rec = _ativo_end_obj.get('municipio') or ''
                _uf_rec = _ativo_end_obj.get('uf') or ''
                if _mun_rec or _uf_rec:
                    resultado['capa_dados']['reclamante_municipio'] = _norm(_mun_rec)
                    resultado['capa_dados']['reclamante_uf'] = _norm(_uf_rec)
                    resultado['capa_dados']['reclamante_end_fonte'] = 'api'
                    logger.debug('[TRIAGEM] reclamante_end_api: municipio=%r uf=%r', _mun_rec, _uf_rec)
                else:
                    resultado['capa_dados']['reclamante_end_fonte'] = 'api_vazio'
                    logger.debug('[TRIAGEM] reclamante_end_api: VAZIO (municipio/uf ausentes no endpoint endereco) - fallback para texto')
            else:
                resultado['capa_dados']['reclamante_end_fonte'] = 'api_sem_ativo'
                logger.debug('[TRIAGEM] reclamante_end_api: ATIVO ausente em partes_endereco - fallback para texto')
        if passivos:
            reclamados_lista = []
            reclamadas_sem_endereco = []
            reclamadas_com_dom_elet = 0
            for _p in passivos:
                _doc = re.sub(r'\D', '', _p.get('documento') or '')
                reclamados_lista.append({'nome': _p.get('nome', '').strip(), 'cpfcnpj': _doc})

            for _parte in (_partes_endereco.get('PASSIVO') or []):
                nome_parte = _parte.get('nome', '').strip()
                if _parte.get('enderecoDesconhecido', False):
                    reclamadas_sem_endereco.append(nome_parte)

                id_parte_pj = str(
                    _parte.get('idPessoa') or _parte.get('id') or
                    _parte.get('idParticipante') or _parte.get('idParte') or '')
                dom_via_api = client.domicilio_eletronico(id_parte_pj) if id_parte_pj else None
                dom_flag_raw = _parte.get('domicilioEletronico') or _parte.get('possuiDomicilioEletronico')
                tem_domicilio = dom_via_api if dom_via_api is not None else (dom_flag_raw is True)
                if tem_domicilio:
                    reclamadas_com_dom_elet += 1

                endereco = _parte.get('endereco') or {}
                cep_raw = endereco.get('nroCep') or ''
                cep = re.sub(r'[^\d]', '', cep_raw) if cep_raw else None
                endereco_desc = _formatar_endereco_parte(endereco)
                _dom_status = 'SIM' if tem_domicilio else ('NAO' if dom_via_api is not None else f'flag={dom_flag_raw}')
                logger.debug('[TRIAGEM] passivo: %s | domicilio=%s | cep=%s | end=%s', nome_parte, _dom_status, cep or "(sem)", endereco_desc[:60] or "(sem)")
                if cep and len(cep) == 8:
                    _doc_parte = re.sub(r'\D', '', _parte.get('documento') or '')
                    for item in reclamados_lista:
                        if item.get('cpfcnpj') == _doc_parte or item.get('nome') == nome_parte:
                            item['cep'] = cep
                            if endereco_desc:
                                item['endereco'] = endereco_desc
                            break

            resultado['capa_dados']['reclamados'] = reclamados_lista
            resultado['capa_dados']['reclamadas_sem_endereco'] = reclamadas_sem_endereco
            resultado['capa_dados']['reclamadas_com_dom_elet'] = reclamadas_com_dom_elet
            _prim = reclamados_lista[0]
            resultado['capa_dados']['reclamado_nome'] = _prim['nome']
            if len(_prim['cpfcnpj']) == 14:
                resultado['capa_dados']['reclamado_cnpj'] = _prim['cpfcnpj']
            elif len(_prim['cpfcnpj']) == 11:
                resultado['capa_dados']['reclamado_cpf'] = _prim['cpfcnpj']

    try:
        proc_dados = client.processo_por_id(id_processo) or {}
        juizo_digital = proc_dados.get('juizoDigital')
        if isinstance(juizo_digital, str):
            juizo_digital = juizo_digital.lower() == 'true'
        elif juizo_digital is not None:
            juizo_digital = bool(juizo_digital)
        resultado['capa_dados']['juizo_digital'] = juizo_digital
        valor_api = (proc_dados.get('valorCausa')
                     or proc_dados.get('valorDaCausa')
                     or proc_dados.get('valor'))
        if valor_api is not None:
            try:
                resultado['capa_dados']['valor_causa'] = float(valor_api)
            except (TypeError, ValueError):
                pass
    except Exception as e_api:
        logger.error("ERRO em _coletar_textos_processo: valor_causa API falha (%s)", e_api)

    cd = resultado['capa_dados']
    logger.debug('[TRIAGEM] capa_dados: valor_causa=%s rito=%s juizo_digital=%s distribuido_em=%s',
            cd.get("valor_causa"), cd.get("rito_declarado"), cd.get("juizo_digital"),
            cd.get("distribuido_em"))
    logger.debug('[TRIAGEM] [_coletar] 6/6 Coleta de textos concluida com sucesso')
    return resultado

__all__ = ['_coletar_textos_processo', '_extrair_texto_pdf_api', '_ErroAutenticacao401']
