"""Fix.variaveis"""
from typing import Optional, Any, Dict, List, Tuple
import requests
import re
import html as _html
import unicodedata
from urllib.parse import unquote, urlparse
from Fix.log import logger


PJE_BASE_URL = "https://pje.trt2.jus.br"


def url_processo_detalhe(id_processo, rota: str = "detalhe") -> str:
    """Constrói URL canônica de acesso a um processo no PJe."""
    return f"{PJE_BASE_URL}/pjekz/processo/{id_processo}/{rota}"


class PjeApiClient:
    def __init__(self, session: requests.Session, trt_host: str, grau: int = 1):
        self.sess = session
        self.trt_host = trt_host
        self.grau = grau

    def _url(self, path: str) -> str:
        base = self.trt_host
        if not base.startswith('http'):
            base = 'https://' + base
        return f"{base}{path}"

    def timeline(self, id_processo: str, buscarDocumentos: bool = True, buscarMovimentos: bool = False) -> Optional[List[Dict[str, Any]]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/timeline")
        params = {
            'somenteDocumentosAssinados': 'false',
            'buscarMovimentos': str(buscarMovimentos).lower(),
            'buscarDocumentos': str(buscarDocumentos).lower()
        }
        r = self.sess.get(url, params=params, timeout=(5, 15))
        if not r.ok:
            return None
        return r.json()

    def documento_por_id(self, id_processo: str, id_documento: str, incluirAssinatura: bool = False, incluirAnexos: bool = False) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}")
        params = {
            'incluirAssinatura': str(incluirAssinatura).lower(),
            'incluirAnexos': str(incluirAnexos).lower(),
            'incluirMovimentos': 'false',
            'incluirApreciacao': 'false'
        }
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def execucao_gigs(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-gigs-api/api/execucao/{id_processo}")
        alt = self._url(f"/pje-gigs-api/api/processo/{id_processo}")
        r = self.sess.get(alt, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def processo_por_id(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def audiencias_processo(self, id_processo: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Audiências (pauta) do processo."""
        if not id_processo:
            return []
        try:
            params = {'status': status} if status else None
            r = self.sess.get(
                self._url(f"/pje-comum-api/api/processos/id/{id_processo}/audiencias"),
                params=params, timeout=15,
            )
            if not r.ok:
                return []
            dados = r.json()
        except Exception as e:
            logger.warning('[API] audiencias_processo %s: %s', id_processo, e)
            return []

        if isinstance(dados, list):
            return dados
        if isinstance(dados, dict):
            for chave in ('content', 'resultado'):
                valor = dados.get(chave)
                if isinstance(valor, list):
                    return valor
        return []

    def data_proxima_audiencia(self, id_processo: str) -> Optional[str]:
        """Data (ISO) da proxima audiencia do processo, pela API de audiencias."""
        for audi in self.audiencias_processo(id_processo):
            if not isinstance(audi, dict):
                continue
            valor = audi.get('dataInicio') or audi.get('dataHoraInicio')
            if valor:
                return str(valor)
        return None

    def partes(self, id_processo: str, com_inativas: bool = False) -> Optional[List[Dict[str, Any]]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes")
        params = {'comInativas': 'true'} if com_inativas else None
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def id_processo_por_numero(self, numero_processo: str) -> Optional[str]:
        """Resolve o ID interno do PJe a partir do número CNJ."""
        try:
            r = self.sess.get(
                self._url("/pje-comum-api/api/processos"),
                params={"numero": numero_processo},
                timeout=15,
            )
            if not r.ok:
                return None
            dados = r.json()

            if isinstance(dados, int):
                return str(dados)

            if isinstance(dados, list) and dados:
                primeiro = dados[0]
                id_resolvido = (
                    primeiro.get("id")
                    or primeiro.get("idProcesso")
                    or primeiro.get("identificador")
                )
                return str(id_resolvido) if id_resolvido else None

            return None
        except Exception:
            return None

    def calculos(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/calculos/processo")
        params = {'idProcesso': id_processo, 'pagina': 1, 'tamanhoPagina': 10, 'ordenacaoCrescente': 'true'}
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def pericias(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/pericias")
        params = {'idProcesso': id_processo}
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def atividades_gigs(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Obtém atividades GIGS do processo via API."""
        url = self._url(f"/pje-gigs-api/api/atividade/processo/{id_processo}")
        try:
            r = self.sess.get(url, timeout=15)
            if not r.ok:
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception:
            return None

    def obrigacoes_pagar(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Obrigações de pagar registradas no processo (crédito exequente)."""
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/obrigacoespagar")
        try:
            r = self.sess.get(url, timeout=15)
            if not r.ok:
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception:
            return None

    def debitos_trabalhistas_bndt(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Obtém partes cadastradas no BNDT (Banco Nacional de Devedores Trabalhistas)."""
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/debitostrabalhistas")
        try:
            r = self.sess.get(url, timeout=15)
            if not r.ok:
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception:
            return None

    def gateway_get(self, path: str, params: Optional[Dict] = None, timeout: int = 20) -> Dict[str, Any]:
        """GET generico com envelope {'ok', 'status', 'data', 'error'}."""
        try:
            r = self.sess.get(self._url(path), params=params, timeout=timeout)
            if r.ok:
                try:
                    data = r.json()
                except Exception:
                    data = r.text
                return {'ok': True, 'status': r.status_code, 'data': data, 'error': None}
            else:
                try:
                    msg = r.text[:200]
                except Exception:
                    msg = str(r.status_code)
                return {
                    'ok': False,
                    'status': r.status_code,
                    'data': None,
                    'error': {'type': 'http_error', 'message': msg, 'method': 'GET', 'path': path, 'status': r.status_code},
                }
        except Exception as exc:
            return {
                'ok': False,
                'status': None,
                'data': None,
                'error': {'type': type(exc).__name__, 'message': str(exc), 'method': 'GET', 'path': path, 'status': None},
            }

    def request_gateway(self, method: str, path: str, *, params: Optional[Dict] = None,
                        json_data: Optional[Any] = None, headers: Optional[Dict[str, str]] = None,
                        timeout: int = 15) -> Dict[str, Any]:
        """Request HTTP generico contra o gateway PJe, com XSRF quando disponivel."""
        request_headers: Dict[str, str] = {}
        if headers:
            request_headers.update(headers)
        if 'X-XSRF-TOKEN' not in request_headers:
            for nome_cookie in ('XSRF-TOKEN', 'xsrf-token', 'csrf-token', 'X-CSRF-TOKEN'):
                try:
                    token = self.sess.cookies.get(nome_cookie)
                except Exception:
                    token = None
                if token:
                    request_headers['X-XSRF-TOKEN'] = unquote(token)
                    break

        try:
            r = self.sess.request(method=method.upper(), url=self._url(path), params=params,
                                  json=json_data, headers=request_headers, timeout=timeout)
            if r.ok:
                try:
                    data = r.json()
                except Exception:
                    data = r.text
                return {'ok': True, 'status': r.status_code, 'data': data, 'error': None}
            try:
                msg = r.text[:300] if r.text else f'HTTP {r.status_code}'
            except Exception:
                msg = str(r.status_code)
            return {
                'ok': False, 'status': r.status_code, 'data': None,
                'error': {'type': 'http_error', 'message': msg, 'method': method.upper(),
                          'path': path, 'status': r.status_code},
            }
        except Exception as exc:
            return {
                'ok': False, 'status': None, 'data': None,
                'error': {'type': 'request_error', 'message': str(exc), 'method': method.upper(),
                          'path': path, 'status': None},
            }

    def gateway_post(self, path: str, *, json_data: Optional[Any] = None,
                     params: Optional[Dict] = None, headers: Optional[Dict[str, str]] = None,
                     timeout: int = 15) -> Dict[str, Any]:
        """POST via gateway."""
        return self.request_gateway('POST', path, params=params, json_data=json_data,
                                    headers=headers, timeout=timeout)

    def gateway_patch(self, path: str, *, json_data: Optional[Any] = None,
                      params: Optional[Dict] = None, headers: Optional[Dict[str, str]] = None,
                      timeout: int = 15) -> Dict[str, Any]:
        """PATCH via gateway."""
        return self.request_gateway('PATCH', path, params=params, json_data=json_data,
                                    headers=headers, timeout=timeout)

    _DOM_CHIP_IDS = (274, 275, 302)

    def buscar_processos_conhecimento_dom(self, chip_ids: Optional[tuple] = None,
                                          tamanho_pagina: int = 100) -> List[Dict[str, Any]]:
        """Processos da fase Conhecimento com chips de Domicilio Eletronico."""
        ids_alvo = set(chip_ids if chip_ids is not None else self._DOM_CHIP_IDS)

        todos: List[Dict[str, Any]] = []
        for pagina in range(1, 201):
            body = {
                'pagina': pagina,
                'tamanhoPagina': tamanho_pagina,
                'subCaixa': None,
                'tipoAtividade': None,
                'processos': None,
                'nomeConclusoMagistrado': None,
                'usuarioResponsavel': None,
                'faseProcessualString': ['Conhecimento'],
                'numeroProcesso': None,
            }
            res = self.gateway_patch(
                '/pje-comum-api/api/agrupamentotarefas/processos/todos',
                json_data=body, timeout=30,
            )
            if not res['ok']:
                logger.error('[API] buscar_processos_conhecimento_dom p%d: %s',
                             pagina, res.get('error'))
                break
            lista = (res['data'] or {}).get('resultado') or []
            todos.extend(lista)
            logger.debug('[API] p%d: %d processos', pagina, len(lista))
            if len(lista) < tamanho_pagina:
                break

        if not todos:
            return []

        mapa: Dict[int, List[int]] = {}
        lote_tam = 100
        for i in range(0, len(todos), lote_tam):
            lote = todos[i:i + lote_tam]
            ids_proc = [p['id'] for p in lote if p.get('id')]
            if not ids_proc:
                continue
            res_et = self.gateway_post(
                '/pje-etiquetas-api/api/etiquetas/etiquetasprocessos',
                json_data={'idsProcesso': ids_proc}, timeout=20,
            )
            if not res_et['ok']:
                logger.warning('[API] etiquetas lote %d: %s', i // lote_tam + 1, res_et.get('error'))
                continue
            for item in (res_et['data'] or []):
                pid = item.get('idProcesso')
                etiquetas = [e['id'] for e in (item.get('etiquetas') or []) if e.get('id')]
                if pid is not None:
                    mapa[pid] = etiquetas

        filtrados = [p for p in todos if ids_alvo.intersection(mapa.get(p.get('id'), []))]
        logger.info('[API] buscar_processos_conhecimento_dom: %d/%d com chips %s',
                    len(filtrados), len(todos), sorted(ids_alvo))
        return filtrados

    def expedientes_processo(self, id_processo: str,
                             tamanho_pagina: int = 100) -> List[Dict[str, Any]]:
        """Todos os expedientes de um processo, paginando ate esgotar."""
        todos: List[Dict[str, Any]] = []
        for pagina in range(1, 51):
            res = self.gateway_get(
                f'/pje-comum-api/api/processos/id/{id_processo}/expedientes',
                params={'pagina': pagina, 'tamanhoPagina': tamanho_pagina, 'instancia': 1},
                timeout=15,
            )
            if not res['ok']:
                logger.warning('[API] expedientes_processo %s p%d: %s',
                               id_processo, pagina, res.get('error'))
                break
            lista = (res['data'] or {}).get('resultado') or []
            todos.extend(lista)
            if len(lista) < tamanho_pagina:
                break
        return todos

    def expediente_partes(self, id_processo: str, id_processo_expediente: Any) -> List[Dict[str, Any]]:
        """Partes/destinatarios de um expediente."""
        if id_processo_expediente in (None, ''):
            return []
        try:
            res = self.gateway_get(
                f'/pje-comum-api/api/processos/id/{id_processo}'
                f'/expedientes/{id_processo_expediente}/partes',
                timeout=15,
            )
        except Exception as e:
            logger.warning('[API] expediente_partes %s/%s: %s',
                           id_processo, id_processo_expediente, e)
            return []
        if not res['ok']:
            logger.warning('[API] expediente_partes %s/%s: %s',
                           id_processo, id_processo_expediente, res.get('error'))
            return []
        dados = res['data']
        if isinstance(dados, list):
            return dados
        if isinstance(dados, dict):
            return dados.get('resultado') or []
        return []

    def domicilio_eletronico(self, id_parte: str) -> Optional[bool]:
        """Verifica se uma parte está habilitada no domicílio eletrônico."""
        if not id_parte or str(id_parte).strip() in ('None', '0', ''):
            return None
        url = self._url(f"/pje-comum-api/api/pessoajuridicadomicilioeletronico/{id_parte}")
        headers = {
            "Content-Type": "application/json",
            "X-Grau-Instancia": str(self.grau)
        }
        try:
            r = self.sess.get(url, headers=headers, timeout=15)
            if r.ok:
                dados = r.json()
                return bool(dados.get('habilitada', False))
            url_alt = self._url(f"/pje-comum-api/api/partes/{id_parte}/domicilio")
            r_alt = self.sess.get(url_alt, headers=headers, timeout=10)
            if r_alt.ok:
                return bool(r_alt.json().get('habilitada', False))
            return None
        except Exception:
            return None


def obter_gigs_com_fase(client: PjeApiClient, id_processo: str) -> Optional[Dict[str, Any]]:
    """Obtém dados GIGS + FASE (Conhecimento/Liquidação/Execução) do processo em uma única chamada."""
    try:
        id_para_busca = id_processo
        if '-' in str(id_processo):
            id_resolvido = client.id_processo_por_numero(id_processo)
            if not id_resolvido:
                return None
            id_para_busca = str(id_resolvido)

        dados_processo = client.processo_por_id(id_para_busca)
        if not dados_processo:
            return None

        atividades_gigs = client.atividades_gigs(id_para_busca)
        if not atividades_gigs:
            atividades_gigs = []

        resultado = {
            'id_processo': dados_processo.get('numero') or id_processo,
            'id_interno': id_para_busca,
            'fase': dados_processo.get('faseProcessual') or 'Desconhecida',
            'atividades_gigs': atividades_gigs
        }

        return resultado

    except Exception:
        return None


def session_from_driver(driver, grau: int = 1) -> Tuple[requests.Session, str]:
    """Cria um `requests.Session` a partir de um driver ativo (Selenium ou PWDriver)."""
    sess = requests.Session()
    try:
        cookies = driver.get_cookies()
        xsrf_token = None
        for c in cookies:
            sess.cookies.set(c['name'], c['value'])
            if c['name'].upper() in ('XSRF-TOKEN', 'XSRF_TOKEN'):
                xsrf_token = unquote(c['value'])
        parsed = urlparse(driver.current_url)
        trt_host = parsed.netloc or 'pje.trt2.jus.br'
        if 'trt2.jus.br' not in trt_host:
            trt_host = 'pje.trt2.jus.br'
    except Exception:
        raise
    user_agent = None
    try:
        fn_js = getattr(driver, 'execute_' + 'script', None)
        if fn_js is None:
            fn_js = getattr(driver, 'evaluate', None)
        if fn_js is not None:
            user_agent = fn_js('return navigator.userAgent;')
    except Exception:
        user_agent = None
    if not user_agent:
        user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    sess.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Grau-Instancia': str(grau),
        'User-Agent': user_agent,
    })
    if xsrf_token:
        sess.headers['X-XSRF-TOKEN'] = xsrf_token
    return sess, trt_host


class _PlaywrightResponseAdapter:
    """Envelopa APIResponse do Playwright para compatibilidade com requests.Response."""

    def __init__(self, resp):
        self._resp = resp

    @property
    def ok(self):
        return getattr(self._resp, 'ok', False)

    @property
    def status_code(self):
        return getattr(self._resp, 'status', 200)

    @property
    def headers(self):
        return getattr(self._resp, 'headers', {})

    @property
    def text(self):
        try:
            fn = getattr(self._resp, 'text', None)
            return fn() if callable(fn) else (fn or "")
        except Exception:
            return ""

    @property
    def content(self):
        try:
            fn = getattr(self._resp, 'body', None)
            if callable(fn):
                return fn()
            return getattr(self._resp, 'content', b'') or b""
        except Exception:
            return b""

    def json(self):
        return self._resp.json()

    def raise_for_status(self):
        if not getattr(self._resp, 'ok', False):
            raise RuntimeError(f"HTTP {getattr(self._resp, 'status', '?')}: {getattr(self._resp, 'status_text', '')}")


class _RequestContextComoSessao:
    """Adapta o `APIRequestContext` do Playwright à fatia de `requests.Session`"""

    def __init__(self, contexto, grau: int = 1):
        self._ctx = contexto
        self._headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': str(grau),
        }

    def get(self, url, params=None, timeout=15, headers=None, **kwargs):
        hdrs = dict(self._headers)
        if headers:
            hdrs.update(headers)
        segundos = timeout[1] if isinstance(timeout, (tuple, list)) else timeout
        timeout_ms = int(segundos * 1000) if segundos is not None else None
        res = self._ctx.get(url, params=params, headers=hdrs, timeout=timeout_ms)
        return _PlaywrightResponseAdapter(res)


def cliente_para(driver, grau: int = 1) -> PjeApiClient:
    """Devolve um `PjeApiClient` adequado ao motor corrente."""
    if hasattr(driver, "page") and hasattr(driver, "context"):
        try:
            from pjeplay import api as _pjeplay_api

            contexto = _pjeplay_api.requisicao(driver)
            trt_host = urlparse(driver.current_url).netloc
            sessao_pw = _RequestContextComoSessao(contexto, grau=grau)
            return PjeApiClient(sessao_pw, trt_host, grau=grau)
        except Exception:
            pass

    sess, trt_host = session_from_driver(driver, grau=grau)
    return PjeApiClient(sess, trt_host, grau=grau)


def obter_codigo_validacao_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Replica a construção de 'chave' feita na extensão."""
    dados = client.documento_por_id(id_processo, id_documento, incluirAssinatura=False, incluirAnexos=False)
    if not dados:
        return None
    data = dados.get('dataInclusaoBin', '')
    idBin = dados.get('idBin')
    if not data or idBin is None:
        return None
    nums = re.sub(r'\D', '', data)
    part = nums[2:17] if len(nums) >= 17 else nums
    chave = part + str(idBin).zfill(14)
    return chave


def obter_peca_processual_da_timeline(client: PjeApiClient, id_processo: str, tipo_label: str, modo: str = 'chave', itens_timeline: Optional[List[Dict]] = None) -> Optional[str]:
    """Resolve o equivalente a obterPecaProcessualDaTimeline do JS."""
    dados = itens_timeline or client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    if not dados:
        return None

    pesquisar_anexos = modo == 'anexos'

    flat = []
    for d in dados:
        flat.append(d)
        if d.get('anexos'):
            for a in d.get('anexos'):
                flat.append(a)

    for docto in flat:
        tipo = (docto.get('tipo') or '').strip()
        titulo = (docto.get('titulo') or '').strip()
        is_chave_acesso = (tipo_label.lower() == 'chave de acesso' and (tipo.lower() == 'chave de acesso' or (tipo.lower() == 'certidão' and 'chave de acesso' in titulo.lower())))
        is_planilha = (tipo_label.lower() == 'planilha de cálculos' and tipo in ['Planilha de Cálculos', 'Planilha de Atualização de Cálculos'])
        if is_chave_acesso or is_planilha or tipo == tipo_label:
            if modo == 'chave':
                doc_id = docto.get('id') or docto.get('idDocumento') or docto.get('idDocumentoPai')
                if not doc_id:
                    doc_id = docto.get('idUnicoDocumento')
                if not doc_id:
                    return None
                return obter_codigo_validacao_documento(client, id_processo, doc_id)
            elif modo == 'id':
                return docto.get('idUnicoDocumento') or docto.get('id')
            elif modo == 'anexos':
                id_pai = docto.get('id')
                anexos = [a for a in flat if a.get('idDocumentoPai') == id_pai]
                lista = ', '.join([f"#id:{a.get('idUnicoDocumento')}" for a in anexos])
                return lista
            else:
                return docto

    return None


def resolver_variavel(client: PjeApiClient, id_processo: str, variavel: str) -> Optional[str]:
    """Recebe nomes como '[maisPje:últimaSentença:chave]' ou 'últimaSentença:chave' e retorna valor."""
    v = variavel
    if v.startswith('[') and v.endswith(']'):
        v = v[1:-1]
    parts = v.split(':')
    if parts[0] == 'maisPje':
        parts = parts[1:]
    tipo_token = parts[0]
    modo = 'chave' if (len(parts) > 1 and parts[1] == 'chave') else ('id' if (len(parts) > 1 and parts[1] == 'id') else ('anexos' if (len(parts) > 1 and parts[1] == 'anexos') else 'chave'))

    mapa = {
        'últimaSentença': 'Sentença',
        'últimoDespacho': 'Despacho',
        'últimaDecisão': 'Decisão',
        'últimoAcórdão': 'Acórdão',
        'últimaAta': 'Ata da Audiência',
        'últimaCertidão': 'Certidão',
        'últimaContestação': 'Contestação',
        'últimaManifestação': 'Manifestação',
        'petiçãoInicial': 'Petição Inicial',
        'chaveDeAcesso': 'Chave de Acesso',
        'últimoCálculo': 'Planilha de Cálculos',
        'último': '*'
    }

    tipo_label = mapa.get(tipo_token, None)
    if tipo_label is None:
        tipo_label = tipo_token

    if tipo_label == '*':
        itens = client.timeline(id_processo)
        if not itens:
            return None
        primeiro = itens[0]
        if modo == 'chave':
            return obter_codigo_validacao_documento(client, id_processo, primeiro.get('id'))
        elif modo == 'id':
            return primeiro.get('idUnicoDocumento') or primeiro.get('id')
        elif modo == 'anexos':
            anexos = primeiro.get('anexos') or []
            return ', '.join([f"#id:{a.get('idUnicoDocumento')}" for a in anexos])
        else:
            return primeiro

    return obter_peca_processual_da_timeline(client, id_processo, tipo_label, modo)


def get_all_variables(client: PjeApiClient, id_processo: str) -> Dict[str, Optional[str]]:
    """Resolve the common set of variables exposed by the extension and"""
    result: Dict[str, Optional[str]] = {}

    proc = client.processo_por_id(id_processo)
    partes = client.partes(id_processo) or []

    exequente = None
    executado = None
    if partes:
        for p in partes:
            polo = (p.get('tipoPolo') or '').lower()
            nome = p.get('nome') or p.get('parte') or p.get('nomeParte')
            if not nome:
                continue
            if 'autor' in polo or 'exequente' in polo or ('polo' in polo and 'autor' in polo):
                exequente = exequente or nome
            if 'reu' in polo or 'executado' in polo or 'demandado' in polo:
                executado = executado or nome

    if not exequente:
        exequente = (proc.get('partes') and proc.get('partes')[0].get('nome')) if proc and proc.get('partes') else None
    if not executado:
        if proc and proc.get('partes') and len(proc.get('partes')) > 1:
            executado = proc.get('partes')[1].get('nome')

    result['exequente'] = exequente
    result['executado'] = executado

    calculos = client.calculos(id_processo)
    valor_divida = None
    if calculos:
        if isinstance(calculos, dict):
            if 'valor' in calculos:
                valor_divida = calculos.get('valor')
            elif calculos.get('totalElements') and calculos.get('content'):
                content = calculos.get('content')
                if content:
                    item = content[0]
                    valor_divida = item.get('valor') or item.get('valorExecucao')

    result['valorDivida'] = valor_divida

    result['justicaGratuita'] = proc.get('justicaGratuita') if proc else None
    result['justicaGratuitaData'] = None

    result['transitoJulgado'] = proc.get('dataTransito') or proc.get('transito') or proc.get('transitoEm') if proc else None

    result['custasArbitradas'] = None

    pericias = client.pericias(id_processo)
    audiencia_data = None
    audiencia_hora = None
    if pericias and isinstance(pericias, dict):
        if pericias.get('content'):
            p = pericias.get('content')[0]
            audiencia_data = p.get('dataPrazo') or p.get('data')
    if not audiencia_data and proc:
        audiencia_data = proc.get('audiencia') or proc.get('dataAudiencia')

    result['audiencia:data'] = audiencia_data
    result['audiencia:hora'] = audiencia_hora

    timeline_tokens = [
        'petiçãoInicial', 'últimaContestação', 'últimaManifestação', 'últimaSentença',
        'últimoAcórdão', 'últimoDespacho', 'últimaDecisão', 'últimaAta', 'últimaCertidão', 'últimoCálculo', 'último'
    ]
    for tok in timeline_tokens:
        key_id = f"{tok}:id"
        key_ch = f"{tok}:chave"
        key_an = f"{tok}:anexos"
        result[key_id] = resolver_variavel(client, id_processo, tok + ':id')
        result[key_ch] = resolver_variavel(client, id_processo, tok + ':chave')
        result[key_an] = resolver_variavel(client, id_processo, tok + ':anexos')

    result['chaveDeAcesso:id'] = resolver_variavel(client, id_processo, 'chaveDeAcesso:id')
    result['chaveDeAcesso:chave'] = resolver_variavel(client, id_processo, 'chaveDeAcesso:chave')

    perito = None
    if pericias and isinstance(pericias, dict) and pericias.get('content'):
        p0 = pericias.get('content')[0]
        perito = p0.get('perito') or p0.get('peritoNome') or p0.get('responsavel')
    result['perito'] = perito

    tel = None
    if partes:
        for p in partes:
            nome = p.get('nome')
            if nome and exequente and nome == exequente:
                tel = p.get('telefone') or p.get('telefoneContato') or p.get('contatos')
                break
    result['exequente:telefone'] = tel

    return result


def condensar_conteudo_documento(conteudo: str, tipo_documento: str, id_documento) -> str:
    """Formata o texto de um documento no mesmo padrão do botão "Copiar" do"""
    texto_condensado = re.sub(r'\s{2,}', ' ', conteudo or '')
    return f'Transcrição do(a) {tipo_documento} (ID {id_documento}): \n"{texto_condensado}"'


def _normalizar_texto_verificacao(texto: str) -> str:
    """Normaliza texto para checagem de exceções: lowercase, remove acentos,
    colapsa qualquer whitespace (incl. nbsp/\\xa0) em um único espaço."""
    if not texto:
        return ''
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', sem_acento.lower()).strip()


PADROES_EXCECAO_LINK_VALIDACAO = (
    'comunique-se por edital',
    'comunique se por edital',
    'comunique-se, por edital',
    'comunique-se por edital,',
    'comunique-se através de edital',
)

PADRAO_CONCOMITANTE = 'de forma concomitante'


def obter_chave_ultimo_despacho_decisao_sentenca(client: PjeApiClient, id_processo: str, tipos: Optional[List[str]] = None, itens_timeline: Optional[List[Dict]] = None, driver = None, incluir_conteudo_condensado: bool = False):
    if tipos is None:
        tipos = ['Sentença', 'Decisão', 'Despacho']

    dados = itens_timeline or client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
    if not dados:
        return None

    flat = []
    for d in dados:
        flat.append(d)
        if d.get('anexos'):
            for a in d.get('anexos'):
                flat.append(a)

    for docto in flat:
        tipo = (docto.get('tipo') or '').strip()
        if not tipo:
            continue
        if tipo in tipos:
            doc_id = docto.get('id') or docto.get('idDocumento') or docto.get('idUnicoDocumento')
            if not doc_id:
                continue

            try:
                conteudo_original = ''
                try:
                    conteudo_original = obter_texto_documento(client, id_processo, doc_id) or ''
                    conteudo_normalizado = _normalizar_texto_verificacao(conteudo_original)
                    if conteudo_normalizado:
                        if tipo == 'Despacho':
                            tem_concomitante = PADRAO_CONCOMITANTE in conteudo_normalizado
                            tem_edital = any(p in conteudo_normalizado for p in PADROES_EXCECAO_LINK_VALIDACAO)
                            if tem_concomitante and tem_edital:
                                logger.debug('[VARIAVEIS] Despacho com "de forma concomitante" + "comunique-se por edital" - pulando para proximo')
                                continue
                    else:
                        logger.warning('[VARIAVEIS][WARN] Conteudo de %s (doc %s) nao pode ser extraido - checagem de excecao NAO aplicada, prosseguindo com risco', tipo, doc_id)
                except Exception as e_check:
                    logger.warning('[VARIAVEIS][WARN] Erro ao verificar conteudo de %s: %s - prosseguindo', tipo, e_check)

                chave = obter_codigo_validacao_documento(client, id_processo, doc_id)
                if not chave:
                    continue
                base = client.trt_host
                if not base.startswith('http'):
                    base = 'https://' + base
                instancia = getattr(client, 'grau', 1)
                link = f"{base}/pjekz/validacao/{chave}?instancia={instancia}"
                if incluir_conteudo_condensado:
                    conteudo_condensado = condensar_conteudo_documento(conteudo_original, tipo, doc_id) if conteudo_original else None
                    return link, conteudo_condensado
                return link
            except Exception:
                continue

    return (None, None) if incluir_conteudo_condensado else None


def obter_texto_documento(client: PjeApiClient, id_processo: str, id_documento: str) -> Optional[str]:
    """Tenta obter o conteúdo textual/HTML de um documento via API, sem abrir a"""
    try:
        dados = client.documento_por_id(id_processo, id_documento, incluirAssinatura=True, incluirAnexos=True)
        if dados:
            candidates = ['conteudo', 'conteudoHtml', 'conteudoTexto', 'texto', 'html', 'previewModeloDocumento']
            for k in candidates:
                v = dados.get(k)
                if v and isinstance(v, str) and v.strip():
                    text = v
                    if text.lstrip().startswith('<') or '<p' in text[:200] or '<div' in text[:200]:
                        clean = re.sub(r'<[^>]+>', ' ', text)
                        clean = _html.unescape(clean)
                        clean = re.sub(r"\s+", ' ', clean).strip()
                        return re.sub(r'\s+([,.;:!?])', r'\1', clean)
                    else:
                        return re.sub(r"\s{2,}", ' ', text).strip()

        possible_paths = [
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/conteudo",
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/conteudoHtml",
            f"/pje-comum-api/api/processos/id/{id_processo}/documento/{id_documento}/conteudo",
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/{id_documento}/conteudo",
        ]
        for path in possible_paths:
            try:
                url = client._url(path)
                r = client.sess.get(url, timeout=15)
            except Exception:
                r = None
            if not r or not getattr(r, 'ok', False):
                continue

            ctype = (r.headers.get('Content-Type') or '').lower()

            raw_content = getattr(r, 'content', b'') or b''
            if raw_content and (raw_content.startswith(b'%PDF') or 'pdf' in ctype):
                try:
                    from Mandado.apoio_fluxos import _extrair_texto_pdf_bytes
                    texto_pdf = _extrair_texto_pdf_bytes(raw_content, log=False)
                    if texto_pdf and len(texto_pdf.strip()) >= 10:
                        corpo = re.sub(
                            r'(?:^\s*(?:PJe\s+)?Documento assinado (?:eletronicamente|digitalmente) por[^\n]*\n?)'
                            r'|(?:^\s*https?://pje[^\n]*\n?)'
                            r'|(?:^\s*N[uú]mero do documento[:\s]+\d+[^\n]*\n?)',
                            '', texto_pdf, flags=re.IGNORECASE | re.MULTILINE
                        ).strip()
                        if len(corpo) >= 20:
                            return texto_pdf.strip()
                except Exception:
                    pass

            text_body = None
            try:
                text_body = r.text
            except Exception:
                text_body = None

            if text_body:
                if 'html' in ctype or text_body.lstrip().startswith('<'):
                    clean = re.sub(r'<[^>]+>', ' ', text_body)
                    clean = _html.unescape(clean)
                    clean = re.sub(r"\s+", ' ', clean).strip()
                    return re.sub(r'\s+([,.;:!?])', r'\1', clean)
                if 'json' in ctype:
                    try:
                        j = r.json()
                        for k in ['conteudo', 'conteudoHtml', 'texto', 'previewModeloDocumento']:
                            v = j.get(k)
                            if v and isinstance(v, str) and v.strip():
                                if v.lstrip().startswith('<'):
                                    clean = re.sub(r'<[^>]+>', ' ', v)
                                    clean = _html.unescape(clean)
                                    clean = re.sub(r"\s+", ' ', clean).strip()
                                    return re.sub(r'\s+([,.;:!?])', r'\1', clean)
                                return re.sub(r"\s{2,}", ' ', v).strip()
                    except Exception:
                        pass

        return None
    except Exception:
        return None


def buscar_atividade_gigs_por_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> Optional[Dict[str, Any]]:
    """Busca uma atividade GIGS específica por observação."""
    try:
        id_para_busca = id_processo
        if '-' in id_processo:
            id_resolvido = client.id_processo_por_numero(id_processo)
            if id_resolvido:
                id_para_busca = str(id_resolvido)

        atividades = client.atividades_gigs(id_para_busca)
        if not atividades:
            return None

        patterns_lower = [p.lower() for p in observacao_patterns]

        for atividade in atividades:
            status = (atividade.get('statusAtividade') or '').upper()
            observacao = (atividade.get('observacao') or '').lower()

            if prazo_aberto:
                if any(s in status for s in ['VENCID', 'CONCLU', 'CANCELA']):
                    continue

            if observacao and any(pattern in observacao for pattern in patterns_lower):
                return atividade

        return None

    except Exception as e:
        return None


def obter_todas_atividades_gigs_com_observacao(client: PjeApiClient, id_processo: str, observacao_patterns: List[str], prazo_aberto: bool = True) -> List[Dict[str, Any]]:
    """Busca TODAS as atividades GIGS que correspondem aos critérios (versão plural)."""
    atividades = client.atividades_gigs(id_processo)
    if not atividades:
        return []

    patterns_lower = [p.lower() for p in observacao_patterns]
    resultado = []

    for atividade in atividades:
        if prazo_aberto:
            status = (atividade.get('statusAtividade') or '').upper()
            if any(s in status for s in ['VENCID', 'CONCLU', 'CANCELA']):
                continue

        observacao = (atividade.get('observacao') or '').lower()
        if observacao and any(pattern in observacao for pattern in patterns_lower):
            resultado.append(atividade)

    return resultado


if __name__ == '__main__':
    logger.debug('Modulo Fix.variaveis: importe e utilize PjeApiClient + resolver_variavel')


def padrao_liq(client: PjeApiClient, id_processo: str, nome_perito: str = 'ROGERIO') -> Dict[str, bool]:
    """Função simples para extrair dados de liquidação via API PJe."""
    resultado = {
        'apenas_uma_com_advogado': False,
        'tem_perito': False
    }

    try:
        pericias = client.pericias(id_processo)
        if pericias:
            pericias_list = []
            if isinstance(pericias, dict):
                pericias_list = pericias.get('content') or pericias.get('resultado') or pericias.get('pericias') or []
            elif isinstance(pericias, list):
                pericias_list = pericias

            for pericia in pericias_list:
                nome_perito_api = (
                    pericia.get('nomePerito') or
                    pericia.get('perito') or
                    pericia.get('responsavel') or
                    ''
                )

                if nome_perito.upper() in nome_perito_api.upper():
                    resultado['tem_perito'] = True
                    break

        partes = client.partes(id_processo)
        if partes:
            reclamadas_com_advogado = 0

            for parte in partes:
                polo = (parte.get('tipoPolo') or '').upper()

                eh_reclamada = any(s in polo for s in ['RECLAMADO', 'PASSIVO', 'REU', 'EXECUTADO'])

                if eh_reclamada:
                    tem_advogado = bool(
                        parte.get('representante') or
                        parte.get('procuradores') or
                        parte.get('advogado') or
                        parte.get('nomeAdvogado')
                    )

                    if tem_advogado:
                        reclamadas_com_advogado += 1

            resultado['apenas_uma_com_advogado'] = (reclamadas_com_advogado == 1)

        return resultado

    except Exception as e:
        resultado['erro'] = str(e)
        return resultado


def verificar_bndt(client: PjeApiClient, id_processo: str) -> Dict[str, Any]:
    """Verifica se há partes cadastradas no BNDT e retorna informações formatadas."""
    resultado = {
        'tem_partes': False,
        'quantidade': 0,
        'partes': [],
        'mensagem': ''
    }

    try:
        partes_bndt = client.debitos_trabalhistas_bndt(id_processo)

        if partes_bndt is None:
            resultado['erro'] = 'Erro ao consultar API BNDT'
            resultado['mensagem'] = 'Erro ao consultar BNDT'
            return resultado

        if len(partes_bndt) > 0:
            resultado['tem_partes'] = True
            resultado['quantidade'] = len(partes_bndt)
            resultado['partes'] = [parte.get('nomeParte', 'N/A') for parte in partes_bndt]

            mensagem = 'Partes cadastradas no BNDT:\n\n'
            for parte in partes_bndt:
                nome = parte.get('nomeParte', 'N/A')
                mensagem += f'{nome}\n'

            resultado['mensagem'] = mensagem.strip()
        else:
            resultado['mensagem'] = 'Sem partes cadastradas no BNDT.'

        return resultado

    except Exception as e:
        resultado['erro'] = str(e)
        resultado['mensagem'] = f'Erro ao verificar BNDT: {e}'
        return resultado


"""
Exemplo de uso das funções BNDT:

# 1. Uso básico com Selenium WebDriver
from Fix.variaveis import session_from_driver, PjeApiClient, verificar_bndt

# Assumindo que você já tem um driver autenticado no PJe
sess, trt = session_from_driver(driver)
client = PjeApiClient(sess, trt)

# Verificar BNDT de um processo
resultado = verificar_bndt(client, id_processo='1234567')

if resultado['tem_partes']:
    print(f"✅ {resultado['quantidade']} parte(s) encontrada(s) no BNDT:")
    for nome in resultado['partes']:
        print(f"   - {nome}")
    print(f"\nMensagem completa:\n{resultado['mensagem']}")
else:
    print("❌ Sem partes cadastradas no BNDT")

# 2. Uso direto do método da API
partes_bndt = client.debitos_trabalhistas_bndt('1234567')
if partes_bndt:
    for parte in partes_bndt:
        print(f"Parte: {parte.get('nomeParte')}")
        # Acessar outros campos retornados pela API
        print(f"  CPF/CNPJ: {parte.get('cpfCnpj', 'N/A')}")
        print(f"  Valor: {parte.get('valorDevido', 'N/A')}")
else:
    print("Nenhuma parte no BNDT ou erro na consulta")

# 3. Integração em fluxo de trabalho
def processar_com_verificacao_bndt(driver, id_processo):
    sess, trt = session_from_driver(driver)
    client = PjeApiClient(sess, trt)
    
    resultado_bndt = verificar_bndt(client, id_processo)
    
    if resultado_bndt.get('erro'):
        print(f"Erro ao consultar BNDT: {resultado_bndt['erro']}")
        return False
    
    if resultado_bndt['tem_partes']:
        # Executar ação específica se há partes no BNDT
        print("⚠️ Processo possui partes no BNDT - aplicando procedimento especial")
        # ... seu código aqui
        return True
    else:
        print("✓ Processo sem partes no BNDT - seguindo fluxo normal")
        return False
"""


def obter_domicilio_eletronico_parte(client: PjeApiClient, id_parte: str, verbose: bool = False) -> Optional[bool]:
    """Helper simplificado para verificar domicílio eletrônico de uma parte."""
    resultado = client.domicilio_eletronico(id_parte)

    if verbose:
        if resultado is True:
            logger.debug("[VARIAVEIS] Parte %s: Domicilio Eletronico SIM", id_parte)
        elif resultado is False:
            logger.debug("[VARIAVEIS] Parte %s: Domicilio Eletronico NAO", id_parte)
        else:
            logger.debug("[VARIAVEIS] Parte %s: Erro ao consultar domicilio", id_parte)

    return resultado


def verificar_domicilio_eletronico_partes(client: PjeApiClient, id_processo: str) -> Dict[str, Any]:
    """Verifica domicílio eletrônico para todas as partes de um processo."""
    resultado = {
        'total_partes': 0,
        'habilitadas': 0,
        'nao_habilitadas': 0,
        'erros': 0,
        'partes': []
    }

    try:
        partes = client.partes(id_processo)
        if not partes:
            resultado['mensagem'] = 'Erro ao obter partes do processo'
            return resultado

        resultado['total_partes'] = len(partes)

        for parte in partes:
            id_parte = parte.get('id') or parte.get('idParte')
            nome_parte = parte.get('nome') or parte.get('nomeParte') or 'N/A'

            if not id_parte:
                continue

            domicilio = client.domicilio_eletronico(str(id_parte))

            if domicilio is True:
                status_texto = 'SIM'
                resultado['habilitadas'] += 1
            elif domicilio is False:
                status_texto = 'NÃO'
                resultado['nao_habilitadas'] += 1
            else:
                status_texto = 'ERRO'
                resultado['erros'] += 1

            resultado['partes'].append({
                'id': str(id_parte),
                'nome': nome_parte,
                'domicilio': domicilio,
                'status_texto': status_texto
            })

        return resultado

    except Exception as e:
        resultado['erro'] = str(e)
        resultado['mensagem'] = f'Erro ao verificar domicílios: {e}'
        return resultado


"""
Exemplo de uso das funções de domicílio eletrônico:

# 1. Verificar uma parte específica
from Fix.variaveis import session_from_driver, PjeApiClient, obter_domicilio_eletronico_parte

sess, trt = session_from_driver(driver)
client = PjeApiClient(sess, trt)

habilitada = obter_domicilio_eletronico_parte(client, '12345')
if habilitada:
    print("✅ Parte habilitada no domicílio eletrônico")
elif habilitada is False:
    print("❌ Parte NÃO habilitada")

# 2. Verificar todas as partes de um processo
resultado = verificar_domicilio_eletronico_partes(client, '1234567')
print(f"Total de partes: {resultado['total_partes']}")
print(f"Habilitadas: {resultado['habilitadas']}")
print(f"Não habilitadas: {resultado['nao_habilitadas']}")

# Listar cada parte
for parte in resultado['partes']:
    print(f"  {parte['nome']}: {parte['status_texto']}")

# 3. Integração em fluxo de trabalho
def processar_partes_com_domicilio(driver, id_processo):
    sess, trt = session_from_driver(driver)
    client = PjeApiClient(sess, trt)
    
    resultado = verificar_domicilio_eletronico_partes(client, id_processo)
    
    if resultado.get('erro'):
        print(f"Erro: {resultado['erro']}")
        return False
    
    for parte in resultado['partes']:
        if parte['domicilio']:
            # Executar ação apenas para partes habilitadas
            print(f"Processando {parte['nome']} (habilitada no domicílio)")
        else:
            print(f"Parte {parte['nome']} não habilitada - pulando")
    
    return True
"""
