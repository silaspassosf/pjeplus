# -*- coding: utf-8 -*-
"""Cliente HTTP para API PJe — extrai cookies do Selenium e faz chamadas REST."""
import html as _html
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from selenium.webdriver.remote.webdriver import WebDriver

from bianca.utils import logger

# =============================================================================
# PjeApiClient — cliente HTTP para API REST do PJe
# =============================================================================


class PjeApiClient:
    """HTTP client for PJe REST API, authenticated via Selenium session cookies."""

    def __init__(self, session: requests.Session, trt_host: str, grau: int = 1):
        self.sess = session
        self.trt_host = trt_host
        self.grau = grau

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Concatena base URL com path."""
        base = self.trt_host
        if not base.startswith('http'):
            base = 'https://' + base
        return f"{base}{path}"

    def _xsrf_token(self) -> Optional[str]:
        """Extrai token XSRF/CSRF dos cookies da sessao."""
        for cookie_name in ('XSRF-TOKEN', 'xsrf-token', 'csrf-token', 'X-CSRF-TOKEN'):
            token = self.sess.cookies.get(cookie_name)
            if token:
                return token
        return None

    def _normalizar_erro(
        self,
        *,
        erro_tipo: str,
        mensagem: str,
        metodo: str,
        path: str,
        status: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retorna dict padrao de erro no formato GatewayResult."""
        return {
            'ok': False,
            'status': status,
            'data': None,
            'error': {
                'type': erro_tipo,
                'message': mensagem,
                'method': metodo.upper(),
                'path': path,
                'status': status,
            },
        }

    # ------------------------------------------------------------------
    # Metodos genericos de request
    # ------------------------------------------------------------------

    def request_gateway(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        """Executa request HTTP generico contra o gateway PJe.

        Retorna dict no formato GatewayResult:
            {'ok': bool, 'status': Optional[int], 'data': Any, 'error': Optional[dict]}
        """
        request_headers: Dict[str, str] = {}
        if headers:
            request_headers.update(headers)

        token = self._xsrf_token()
        if token and 'X-XSRF-TOKEN' not in request_headers:
            request_headers['X-XSRF-TOKEN'] = token

        url = self._url(path)

        try:
            response = self.sess.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            return self._normalizar_erro(
                erro_tipo='request_error',
                mensagem=str(exc),
                metodo=method,
                path=path,
                status=None,
            )

        if not response.ok:
            mensagem = response.text.strip()[:300] if response.text else f'HTTP {response.status_code}'
            return self._normalizar_erro(
                erro_tipo='http_error',
                mensagem=mensagem,
                metodo=method,
                path=path,
                status=response.status_code,
            )

        try:
            parsed = response.json()
        except ValueError:
            parsed = response.text

        return {
            'ok': True,
            'status': response.status_code,
            'data': parsed,
            'error': None,
        }

    def gateway_get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        """GET request via gateway."""
        return self.request_gateway('GET', path, params=params, headers=headers, timeout=timeout)

    def gateway_post(
        self,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        """POST request via gateway."""
        return self.request_gateway(
            'POST',
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )

    def gateway_patch(
        self,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        """PATCH request via gateway."""
        return self.request_gateway(
            'PATCH',
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Endpoints especificos da API PJe
    # ------------------------------------------------------------------

    def timeline(
        self,
        id_processo: str,
        buscarDocumentos: bool = True,
        buscarMovimentos: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """Obtem timeline do processo."""
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/timeline")
        params = {
            'somenteDocumentosAssinados': 'false',
            'buscarMovimentos': str(buscarMovimentos).lower(),
            'buscarDocumentos': str(buscarDocumentos).lower(),
        }
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def documento_por_id(
        self,
        id_processo: str,
        id_documento: str,
        incluirAssinatura: bool = False,
        incluirAnexos: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Obtem dados de um documento especifico."""
        url = self._url(
            f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}"
        )
        params = {
            'incluirAssinatura': str(incluirAssinatura).lower(),
            'incluirAnexos': str(incluirAnexos).lower(),
            'incluirMovimentos': 'false',
            'incluirApreciacao': 'false',
        }
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def execucao_gigs(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Obtem dados de execucao GIGS."""
        # fallback para endpoint usado na extensao
        url = self._url(f"/pje-gigs-api/api/processo/{id_processo}")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def processo_por_id(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Obtem dados do processo pelo ID interno."""
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def partes(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Obtem lista de partes do processo."""
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def id_processo_por_numero(self, numero_processo: str) -> Optional[str]:
        """Resolve o ID interno do PJe a partir do numero CNJ.

        Endpoint: GET /pje-comum-api/api/processos?numero={numero}
        Retorna diretamente o ID (int) ou uma lista com objetos contendo 'id'.
        """
        try:
            r = self.sess.get(
                self._url("/pje-comum-api/api/processos"),
                params={"numero": numero_processo},
                timeout=15,
            )
            if not r.ok:
                return None
            dados = r.json()

            # Se e um inteiro direto, retorna como string
            if isinstance(dados, int):
                return str(dados)

            # Se e uma lista com objetos
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
        """Obtem calculos do processo."""
        url = self._url(f"/pje-comum-api/api/calculos/processo")
        params = {
            'idProcesso': id_processo,
            'pagina': 1,
            'tamanhoPagina': 10,
            'ordenacaoCrescente': 'true',
        }
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def pericias(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Obtem pericias do processo."""
        url = self._url(f"/pje-comum-api/api/pericias")
        params = {'idProcesso': id_processo}
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def atividades_gigs(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Obtem atividades GIGS do processo via API.

        Retorna lista de atividades com campos:
        - tipoAtividade: descricao do tipo
        - dataPrazo: data do prazo (formato ISO ou DD/MM/YYYY)
        - statusAtividade: status da atividade
        - observacao: observacoes
        """
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

    def debitos_trabalhistas_bndt(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Obtem partes cadastradas no BNDT (Banco Nacional de Devedores Trabalhistas).

        Endpoint: GET /pje-comum-api/api/processos/id/{idProcesso}/debitostrabalhistas

        Args:
            id_processo: ID do processo (numerico interno)

        Returns:
            Lista de dicionarios com dados das partes no BNDT ou None em caso de erro.
            Cada item contem pelo menos: {'nomeParte': 'Nome da Parte', ...}
            Lista vazia [] indica que nao ha partes cadastradas no BNDT.
        """
        url = self._url(
            f"/pje-comum-api/api/processos/id/{id_processo}/debitostrabalhistas"
        )
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

    def domicilio_eletronico(self, id_parte: str) -> Optional[bool]:
        """Verifica domicilio eletronico (apenas PJ).

        Retorna True se habilitada, False se nao, None em erro/404 (PF ou nao encontrada).
        """
        if not id_parte or id_parte in ('None', '0', ''):
            return None
        url = self._url(
            f"/pje-comum-api/api/pessoajuridicadomicilioeletronico/{id_parte}"
        )
        try:
            r = self.sess.get(url, timeout=10)
            if not r.ok:
                return None
            return bool(r.json().get('habilitada', False))
        except Exception:
            return None

    # Chip IDs confirmados pelo PJe API Spy (2026-05-12)
    _DOM_CHIP_IDS = (274, 275, 302)  # Resposta Excedido, Ciencia Expirado, Ciencia Automatica

    def buscar_processos_conhecimento_dom(
        self,
        chip_ids: Optional[tuple] = None,
        tamanho_pagina: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retorna processos da fase Conhecimento com chips de Domicilio Eletronico.

        Estrategia confirmada pelo API Spy:
          1. PATCH /pje-comum-api/api/agrupamentotarefas/processos/todos
             body: {faseProcessualString:['Conhecimento'], subCaixa:null, ...}
          2. POST /pje-etiquetas-api/api/etiquetas/etiquetasprocessos em lotes de 100
          3. Filtro client-side: manter processos com etiqueta.id in chip_ids

        Args:
            chip_ids: IDs de etiqueta DOM a filtrar. Default: (274, 275, 302).
            tamanho_pagina: Itens por pagina no PATCH. Max recomendado: 100.

        Returns:
            Lista de dicts de processo. Campos principais: id, numeroProcesso,
            classeJudicial, tarefa, faseProcessual, nomeParteAutora.
        """
        ids_alvo = set(chip_ids if chip_ids is not None else self._DOM_CHIP_IDS)

        # Passo 1: paginar todos os processos de Conhecimento via PATCH
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
                json_data=body,
                timeout=30,
            )
            if not res['ok']:
                logger.error(
                    '[API] buscar_processos_conhecimento_dom p%d: %s',
                    pagina, res.get('error'),
                )
                break
            dados = res['data']
            lista = dados.get('resultado') or []
            todos.extend(lista)
            logger.debug('[API] p%d: %d processos', pagina, len(lista))
            if len(lista) < tamanho_pagina:
                break

        if not todos:
            return []

        # Passo 2: buscar etiquetas em lotes de 100
        mapa: Dict[int, List[int]] = {}  # id_processo -> [id_etiqueta, ...]
        lote_tam = 100
        for i in range(0, len(todos), lote_tam):
            lote = todos[i:i + lote_tam]
            ids_proc = [p['id'] for p in lote if p.get('id')]
            if not ids_proc:
                continue
            res_et = self.gateway_post(
                '/pje-etiquetas-api/api/etiquetas/etiquetasprocessos',
                json_data={'idsProcesso': ids_proc},
                timeout=20,
            )
            if not res_et['ok']:
                logger.warning(
                    '[API] etiquetas lote %d: %s', i // lote_tam + 1, res_et.get('error')
                )
                continue
            for item in (res_et['data'] or []):
                pid = item.get('idProcesso')
                etiquetas = [e['id'] for e in (item.get('etiquetas') or []) if e.get('id')]
                if pid is not None:
                    mapa[pid] = etiquetas

        # Passo 3: filtrar client-side
        filtrados = [
            p for p in todos
            if ids_alvo.intersection(mapa.get(p.get('id'), []))
        ]
        logger.info(
            '[API] buscar_processos_conhecimento_dom: %d/%d com chips %s',
            len(filtrados), len(todos), sorted(ids_alvo),
        )
        return filtrados

    def expedientes_processo(
        self,
        id_processo: str,
        tamanho_pagina: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retorna todos os expedientes de um processo.

        Pagina automaticamente ate esgotar os resultados.

        Args:
            id_processo: ID interno do processo.
            tamanho_pagina: Itens por pagina (max recomendado: 100).

        Returns:
            Lista de dicts com campos: id, nomePessoaParte, tipoExpediente,
            meioExpediente, dataCiencia, fimDoPrazoLegal, fechado, etc.
        """
        todos: List[Dict[str, Any]] = []
        for pagina in range(1, 51):
            res = self.gateway_get(
                f'/pje-comum-api/api/processos/id/{id_processo}/expedientes',
                params={'pagina': pagina, 'tamanhoPagina': tamanho_pagina, 'instancia': 1},
                timeout=15,
            )
            if not res['ok']:
                logger.warning(
                    '[API] expedientes_processo %s p%d: %s',
                    id_processo, pagina, res.get('error'),
                )
                break
            dados = res['data'] or {}
            lista = dados.get('resultado') or []
            todos.extend(lista)
            if len(lista) < tamanho_pagina:
                break
        return todos

# =============================================================================
# session_from_driver — extrai cookies do Selenium
# =============================================================================


def session_from_driver(driver: WebDriver, grau: int = 1) -> Tuple[requests.Session, str]:
    """Cria um ``requests.Session`` a partir de um Selenium ``driver``.

    Extrai todos os cookies ativos do navegador e os aplica a uma sessao
    ``requests``, alem de configurar headers padrao (Accept, Content-Type,
    X-Grau-Instancia).

    Returns:
        Tupla (session, trt_host) onde trt_host e o netloc da URL atual do driver.
    """
    sess = requests.Session()
    cookies = driver.get_cookies()
    for c in cookies:
        sess.cookies.set(c['name'], c['value'])
    parsed = urlparse(driver.current_url)
    trt_host = parsed.netloc
    sess.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Grau-Instancia': str(grau),
    })
    return sess, trt_host


# =============================================================================
# Helpers de paginacao
# =============================================================================


def _erro_gateway(
    tipo: str,
    mensagem: str,
    path: str,
    status: Optional[int] = None,
) -> Dict[str, Any]:
    """Cria dict de erro no formato GatewayResult (uso standalone)."""
    return {
        'ok': False,
        'status': status,
        'data': None,
        'error': {
            'type': tipo,
            'message': mensagem,
            'method': 'GET',
            'path': path,
            'status': status,
        },
    }


def _extrair_itens_pagina(
    payload: Any,
    pagina_atual: int,
    tamanho_pagina: int,
) -> Tuple[List[Any], bool]:
    """Extrai itens de uma resposta paginada e indica se ha mais paginas.

    Tenta varios formatos comuns de resposta:
    - Lista direta
    - Dict com chave 'items', 'itens', 'content', 'resultados', 'resultado', 'data'
    - Dict com 'totalPaginas', 'totalPages', 'ultima' para controle de paginacao

    Returns:
        Tupla (lista_de_itens, tem_mais_paginas).
    """
    if isinstance(payload, list):
        return payload, len(payload) >= tamanho_pagina

    if not isinstance(payload, dict):
        return [], False

    itens = payload.get('items')
    if itens is None:
        itens = payload.get('itens')
    if itens is None:
        itens = payload.get('content')
    if itens is None:
        itens = payload.get('resultados')
    if itens is None:
        itens = payload.get('resultado')
    if itens is None:
        itens = payload.get('data')

    if not isinstance(itens, list):
        itens = []

    total_paginas = payload.get('totalPaginas')
    if isinstance(total_paginas, int):
        return itens, pagina_atual < total_paginas

    total_paginas = payload.get('totalPages')
    if isinstance(total_paginas, int):
        return itens, pagina_atual < total_paginas

    ultima = payload.get('ultima')
    if isinstance(ultima, bool):
        return itens, not ultima

    return itens, len(itens) >= tamanho_pagina


def buscar_todas_paginas(
    client: PjeApiClient,
    path: str,
    *,
    params_base: Optional[Dict[str, Any]] = None,
    page_param: str = 'pagina',
    size_param: str = 'tamanhoPagina',
    pagina_inicial: int = 1,
    tamanho_pagina: int = 100,
    limite_paginas: int = 100,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Itera sobre todas as paginas de um endpoint paginado da API.

    Usa ``GatewayResult`` como formato de retorno (dict com chaves
    ``ok``, ``status``, ``data``, ``error``).

    Args:
        client: Instancia de PjeApiClient configurada.
        path: Caminho do endpoint (ex: ``/pje-comum-api/api/processos``).
        params_base: Parametros de query comuns a todas as paginas.
        page_param: Nome do parametro de numero da pagina (ex: 'pagina').
        size_param: Nome do parametro de tamanho da pagina (ex: 'tamanhoPagina').
        pagina_inicial: Numero da primeira pagina (padrao: 1).
        tamanho_pagina: Itens por pagina (padrao: 100).
        limite_paginas: Maximo de paginas a buscar (padrao: 100).
        timeout: Timeout em segundos para cada request.

    Returns:
        GatewayResult com 'data' contendo a lista completa de itens.
    """
    if limite_paginas < 1:
        return _erro_gateway('pagination_error', 'limite_paginas deve ser >= 1', path)

    itens_total: List[Any] = []
    pagina_atual = pagina_inicial

    for _ in range(limite_paginas):
        params = dict(params_base or {})
        params[page_param] = pagina_atual
        params[size_param] = tamanho_pagina

        resposta = client.gateway_get(path, params=params, timeout=timeout)
        if not resposta.get('ok'):
            erro = resposta.get('error') or {}
            mensagem = erro.get('message') or f'Falha na pagina {pagina_atual}'
            return _erro_gateway(
                erro.get('type') or 'http_error',
                mensagem,
                path,
                resposta.get('status'),
            )

        itens_pagina, tem_mais = _extrair_itens_pagina(
            resposta.get('data'),
            pagina_atual=pagina_atual,
            tamanho_pagina=tamanho_pagina,
        )
        itens_total.extend(itens_pagina)

        if not tem_mais:
            return {
                'ok': True,
                'status': resposta.get('status'),
                'data': itens_total,
                'error': None,
            }

        pagina_atual += 1

    return _erro_gateway(
        'pagination_limit',
        f'Limite de paginas atingido: {limite_paginas}',
        path,
    )


# =============================================================================
# Funcoes de dominio (helpers de negocio)
# =============================================================================


def obter_gigs_com_fase(
    client: PjeApiClient,
    id_processo: str,
) -> Optional[Dict[str, Any]]:
    """Obtem dados GIGS + FASE (Conhecimento/Liquidacao/Execucao) do processo.

    Args:
        client: PjeApiClient configurado.
        id_processo: ID do processo (pode ser CNJ ou ID interno).

    Returns:
        Dict com:
        {
            'id_processo': '1001706-10.2024.5.02.0703',  # CNJ
            'id_interno': 6577647,  # ID interno
            'fase': 'Conhecimento',  # ou 'Liquidacao' ou 'Execucao'
            'atividades_gigs': [ ... ]
        }
        Retorna None se falhar em obter dados do processo.
    """
    try:
        # Resolver ID se necessario
        id_para_busca = id_processo
        if '-' in str(id_processo):  # E CNJ, precisa resolver
            id_resolvido = client.id_processo_por_numero(id_processo)
            if not id_resolvido:
                return None
            id_para_busca = str(id_resolvido)

        # Obter dados do processo (inclui faseProcessual)
        dados_processo = client.processo_por_id(id_para_busca)
        if not dados_processo:
            return None

        # Obter GIGS
        atividades_gigs = client.atividades_gigs(id_para_busca)
        if not atividades_gigs:
            atividades_gigs = []

        # Montar resultado com faseProcessual (campo correto da API)
        resultado = {
            'id_processo': dados_processo.get('numero') or id_processo,
            'id_interno': id_para_busca,
            'fase': dados_processo.get('faseProcessual') or 'Desconhecida',
            'atividades_gigs': atividades_gigs,
        }

        return resultado

    except Exception:
        return None


def obter_texto_documento(
    client: PjeApiClient,
    id_processo: str,
    id_documento: str,
) -> Optional[str]:
    """Obtem o conteudo textual/HTML de um documento via API.

    Estrategia conservadora:
    1. Chama ``documento_por_id`` e procura campos que contenham HTML/texto.
    2. Se nao encontrar, tenta endpoints comuns de 'conteudo' e verifica
       se a resposta contem HTML/texto (descarta PDFs/binarios).

    Retorna o texto limpo (tags removidas, entidades unescaped) ou ``None``.
    """
    try:
        dados = client.documento_por_id(
            id_processo, id_documento, incluirAssinatura=True, incluirAnexos=True
        )
        if dados:
            # campos possiveis que podem conter o HTML/texto
            candidates = [
                'conteudo',
                'conteudoHtml',
                'conteudoTexto',
                'texto',
                'html',
                'previewModeloDocumento',
            ]
            for k in candidates:
                v = dados.get(k)
                if v and isinstance(v, str) and v.strip():
                    text = v
                    # se parecer HTML, remover tags
                    if text.lstrip().startswith('<') or '<p' in text[:200] or '<div' in text[:200]:
                        clean = re.sub(r'<[^>]+>', '', text)
                        clean = _html.unescape(clean)
                        return re.sub(r"\s{2,}", ' ', clean).strip()
                    else:
                        return re.sub(r"\s{2,}", ' ', text).strip()

        # Tentar endpoints alternativos que costumam expor o conteudo
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
            text_body = None
            try:
                text_body = r.text
            except Exception:
                text_body = None

            if text_body:
                if 'html' in ctype or text_body.lstrip().startswith('<'):
                    clean = re.sub(r'<[^>]+>', '', text_body)
                    clean = _html.unescape(clean)
                    return re.sub(r"\s{2,}", ' ', clean).strip()
                # json with nested content
                if 'json' in ctype:
                    try:
                        j = r.json()
                        for k in ['conteudo', 'conteudoHtml', 'texto', 'previewModeloDocumento']:
                            v = j.get(k)
                            if v and isinstance(v, str) and v.strip():
                                if v.lstrip().startswith('<'):
                                    clean = re.sub(r'<[^>]+>', '', v)
                                    clean = _html.unescape(clean)
                                    return re.sub(r"\s{2,}", ' ', clean).strip()
                                return re.sub(r"\s{2,}", ' ', v).strip()
                    except Exception:
                        pass

        return None
    except Exception:
        return None


def buscar_atividade_gigs_por_observacao(
    client: PjeApiClient,
    id_processo: str,
    observacao_patterns: List[str],
    prazo_aberto: bool = True,
) -> Optional[Dict[str, Any]]:
    """Busca uma atividade GIGS especifica por observacao.

    Args:
        client: PjeApiClient configurado.
        id_processo: ID do processo.
        observacao_patterns: Lista de termos/patterns para buscar na observacao
                             (ex: ['AJ-JT'], busca por OR - qualquer um).
        prazo_aberto: Se True, filtra apenas atividades com status de prazo aberto.

    Returns:
        Dict com a atividade encontrada ou None se nao houver match.
        Campos retornados: tipoAtividade, dataPrazo, statusAtividade, observacao.
    """
    try:
        # Resolver CNJ -> id interno se necessario
        id_para_busca = id_processo
        if '-' in id_processo:
            id_resolvido = client.id_processo_por_numero(id_processo)
            if id_resolvido:
                id_para_busca = str(id_resolvido)

        atividades = client.atividades_gigs(id_para_busca)
        if not atividades:
            return None

        # normalizar patterns para lowercase
        patterns_lower = [p.lower() for p in observacao_patterns]

        for atividade in atividades:
            status = (atividade.get('statusAtividade') or '').upper()
            observacao = (atividade.get('observacao') or '').lower()

            # validar status de prazo aberto se solicitado
            if prazo_aberto:
                if any(s in status for s in ['VENCID', 'CONCLU', 'CANCELA']):
                    continue

            # verificar se observacao contem algum dos patterns
            if observacao and any(pattern in observacao for pattern in patterns_lower):
                return atividade

        return None

    except Exception as e:
        logger.debug("Erro em buscar_atividade_gigs_por_observacao: %s", e)
        return None


def obter_todas_atividades_gigs_com_observacao(
    client: PjeApiClient,
    id_processo: str,
    observacao_patterns: List[str],
    prazo_aberto: bool = True,
) -> List[Dict[str, Any]]:
    """Busca TODAS as atividades GIGS que correspondem aos criterios (versao plural).

    Args:
        client: PjeApiClient configurado.
        id_processo: ID do processo.
        observacao_patterns: Lista de termos/patterns para buscar na observacao.
        prazo_aberto: Se True, filtra apenas atividades com prazo aberto.

    Returns:
        Lista de dicts com atividades encontradas, ou lista vazia se nenhuma.
    """
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


def padrao_liq(
    client: PjeApiClient,
    id_processo: str,
    nome_perito: str = 'ROGERIO',
) -> Dict[str, bool]:
    """Extrai dados de liquidacao via API PJe.

    Retorna apenas 2 informacoes essenciais:
    - apenas_uma_com_advogado: bool (True se APENAS UMA reclamada tem advogado)
    - tem_perito: bool (True se existe perito com o nome procurado)

    Args:
        client: PjeApiClient configurado.
        id_processo: ID do processo.
        nome_perito: Nome do perito a procurar (padrao: 'ROGERIO').

    Returns:
        Dict com:
        {
            'apenas_uma_com_advogado': bool,
            'tem_perito': bool,
            'erro': str (opcional, se houver excecao)
        }
    """
    resultado: Dict[str, Any] = {
        'apenas_uma_com_advogado': False,
        'tem_perito': False,
    }

    try:
        # ===== VERIFICAR PERITO =====
        pericias = client.pericias(id_processo)
        if pericias:
            pericias_list = []
            if isinstance(pericias, dict):
                pericias_list = (
                    pericias.get('content')
                    or pericias.get('resultado')
                    or pericias.get('pericias')
                    or []
                )
            elif isinstance(pericias, list):
                pericias_list = pericias

            for pericia in pericias_list:
                nome_perito_api = (
                    pericia.get('nomePerito')
                    or pericia.get('perito')
                    or pericia.get('responsavel')
                    or ''
                )

                if nome_perito.upper() in nome_perito_api.upper():
                    resultado['tem_perito'] = True
                    break

        # ===== VERIFICAR APENAS UMA RECLAMADA COM ADVOGADO =====
        partes = client.partes(id_processo)
        if partes:
            reclamadas_com_advogado = 0

            for parte in partes:
                polo = (parte.get('tipoPolo') or '').upper()

                # Verificar se e reclamada (passivo/reclamado)
                eh_reclamada = any(
                    s in polo for s in ['RECLAMADO', 'PASSIVO', 'REU', 'EXECUTADO']
                )

                if eh_reclamada:
                    # Verificar se tem advogado
                    tem_advogado = bool(
                        parte.get('representante')
                        or parte.get('procuradores')
                        or parte.get('advogado')
                        or parte.get('nomeAdvogado')
                    )

                    if tem_advogado:
                        reclamadas_com_advogado += 1

            # Resultado: True se EXATAMENTE UMA tem advogado
            resultado['apenas_uma_com_advogado'] = (reclamadas_com_advogado == 1)

        return resultado

    except Exception as e:
        resultado['erro'] = str(e)
        return resultado


def verificar_bndt(
    client: PjeApiClient,
    id_processo: str,
) -> Dict[str, Any]:
    """Verifica se ha partes cadastradas no BNDT e retorna informacoes formatadas.

    Args:
        client: PjeApiClient configurado.
        id_processo: ID do processo (numerico interno).

    Returns:
        Dict com:
        {
            'tem_partes': bool,   # True se ha partes no BNDT
            'quantidade': int,     # Numero de partes encontradas
            'partes': List[str],  # Lista com nomes das partes
            'mensagem': str,       # Mensagem formatada para exibicao
            'erro': str (opcional)
        }
    """
    resultado: Dict[str, Any] = {
        'tem_partes': False,
        'quantidade': 0,
        'partes': [],
        'mensagem': '',
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
            resultado['partes'] = [
                parte.get('nomeParte', 'N/A') for parte in partes_bndt
            ]

            # Formatar mensagem
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
