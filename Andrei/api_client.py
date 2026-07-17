"""Cliente HTTP para a API REST do PJe.

Extrai cookies de uma sessao Selenium e constroi um cliente
para consumir os endpoints JSON do PJe (pje-comum-api, pje-gigs-api).

Uso:
    from Andrei.api_client import PjeApiClient, session_from_driver

    session, host = session_from_driver(driver)
    client = PjeApiClient(session, host, grau=1)
    data = client.processo_por_id("1234567")
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipos auxiliares para o gateway de requisicoes
# ---------------------------------------------------------------------------


class GatewayError(TypedDict):
    type: str
    message: str
    method: str
    path: str
    status: Optional[int]


class GatewayResult(TypedDict):
    ok: bool
    status: Optional[int]
    data: Any
    error: Optional[GatewayError]


# ---------------------------------------------------------------------------
# PjeApiClient
# ---------------------------------------------------------------------------


class PjeApiClient:
    """Cliente HTTP para a API REST do PJe.

    Encapsula as chamadas aos endpoints dos servicos:

      - **pje-comum-api** — processos, documentos, partes, calculos, pericias
      - **pje-gigs-api** — execucao, atividades

    Args:
        session: Sessao ``requests`` autenticada (cookies do PJe).
        trt_host: Host do tribunal (ex.: ``pje.trt1.jus.br``).
        grau: Grau de instancia (1 = primeiro, 2 = segundo).
    """

    def __init__(
        self,
        session: requests.Session,
        trt_host: str,
        grau: int = 1,
    ):
        self.sess = session
        self.trt_host = trt_host
        self.grau = grau

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Monta URL absoluta a partir do *trt_host*."""
        base = self.trt_host
        if not base.startswith('http'):
            base = 'https://' + base
        return f"{base}{path}"

    def _xsrf_token(self) -> Optional[str]:
        """Retorna o token XSRF armazenado nos cookies da sessao."""
        for cookie_name in ('XSRF-TOKEN', 'xsrf-token', 'csrf-token', 'X-CSRF-TOKEN'):
            token = self.sess.cookies.get(cookie_name)
            if token:
                return token
        return None

    # ------------------------------------------------------------------
    # Gateway request helpers
    # ------------------------------------------------------------------

    def _normalizar_erro(
        self,
        *,
        erro_tipo: str,
        mensagem: str,
        metodo: str,
        path: str,
        status: Optional[int] = None,
    ) -> GatewayResult:
        """Normaliza uma resposta de erro no formato padrao do gateway."""
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

    def request_gateway(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> GatewayResult:
        """Dispara uma requisicao HTTP arbitraria contra a API do PJe.

        Injeta automaticamente o header ``X-XSRF-TOKEN`` se o cookie
        correspondente estiver presente na sessao.

        Args:
            method: Metodo HTTP (GET, POST, PATCH, ...).
            path: Caminho do endpoint (ex.: ``/pje-comum-api/api/processos/...``).
            params: Parametros de query string.
            json_data: Corpo da requisicao (serializado como JSON).
            headers: Headers adicionais.
            timeout: Timeout em segundos.

        Returns:
            ``GatewayResult`` com os campos ``ok``, ``status``, ``data`` e ``error``.
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
            mensagem = (
                response.text.strip()[:300]
                if response.text
                else f'HTTP {response.status_code}'
            )
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
    ) -> GatewayResult:
        """Atalho para ``request_gateway('GET', ...)``."""
        return self.request_gateway(
            'GET', path, params=params, headers=headers, timeout=timeout
        )

    def gateway_post(
        self,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> GatewayResult:
        """Atalho para ``request_gateway('POST', ...)``."""
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
    ) -> GatewayResult:
        """Atalho para ``request_gateway('PATCH', ...)``."""
        return self.request_gateway(
            'PATCH',
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Timeline / documentos
    # ------------------------------------------------------------------

    def timeline(
        self,
        id_processo: str,
        buscarDocumentos: bool = True,
        buscarMovimentos: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """Retorna a timeline do processo (documentos e/ou movimentos).

        Endpoint:
            GET /pje-comum-api/api/processos/id/{id}/timeline
        """
        url = self._url(
            f"/pje-comum-api/api/processos/id/{id_processo}/timeline"
        )
        params = {
            'somenteDocumentosAssinados': 'false',
            'buscarMovimentos': str(buscarMovimentos).lower(),
            'buscarDocumentos': str(buscarDocumentos).lower(),
        }
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning(
                "Falha ao obter timeline para processo %s: %s",
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    def documento_por_id(
        self,
        id_processo: str,
        id_documento: str,
        incluirAssinatura: bool = False,
        incluirAnexos: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Retorna os dados de um documento pelo seu ID.

        Endpoint:
            GET /pje-comum-api/api/processos/id/{id}/documentos/id/{id_doc}

        # Diferenca do original Peticao/api/client.py:
        # Andrei possui docstring documentando o endpoint consumido e
        # os parametros, e utiliza formato %%s no logger.warning (vs
        # f-strings no original) para consistencia com o padrao de
        # logging do modulo.
        """
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
            logger.warning(
                "Falha ao obter documento %s do processo %s: %s",
                id_documento,
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    # ------------------------------------------------------------------
    # GIGS
    # ------------------------------------------------------------------

    def execucao_gigs(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Retorna dados de execucao GIGS do processo.

        Usa o endpoint alternativo (``/pje-gigs-api/api/processo/{id}``)
        que e o utilizado pela extensao oficial do PJe.

        Endpoint:
            GET /pje-gigs-api/api/processo/{id}
        """
        alt = self._url(f"/pje-gigs-api/api/processo/{id_processo}")
        r = self.sess.get(alt, timeout=15)
        if not r.ok:
            logger.warning(
                "Falha ao obter execucao GIGS para processo %s: %s",
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    def atividades_gigs(
        self, id_processo: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Retorna as atividades GIGS do processo.

        Endpoint:
            GET /pje-gigs-api/api/atividade/processo/{id}
        """
        url = self._url(
            f"/pje-gigs-api/api/atividade/processo/{id_processo}"
        )
        try:
            r = self.sess.get(url, timeout=15)
            if not r.ok:
                logger.warning(
                    "Falha ao obter atividades GIGS para processo %s: %s",
                    id_processo,
                    r.status_code,
                )
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception as exc:
            logger.error(
                "Erro ao obter atividades GIGS para processo %s: %s",
                id_processo,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Processo
    # ------------------------------------------------------------------

    def processo_por_id(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Retorna os dados principais de um processo pelo ID interno.

        Endpoint:
            GET /pje-comum-api/api/processos/id/{id}
        """
        url = self._url(
            f"/pje-comum-api/api/processos/id/{id_processo}"
        )
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            logger.warning(
                "Falha ao obter processo %s: %s",
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    def id_processo_por_numero(
        self, numero_processo: str
    ) -> Optional[str]:
        """Resolve o ID interno do PJe a partir do numero CNJ.

        Endpoint:
            GET /pje-comum-api/api/processos?numero={numero}

        Retorna:
            O ID interno como string, ou ``None`` se nao foi possivel resolver.
        """
        try:
            r = self.sess.get(
                self._url("/pje-comum-api/api/processos"),
                params={"numero": numero_processo},
                timeout=15,
            )
            if not r.ok:
                logger.warning(
                    "Falha ao resolver ID para numero %s: %s",
                    numero_processo,
                    r.status_code,
                )
                return None
            dados = r.json()

            # Resposta pode ser um inteiro direto
            if isinstance(dados, int):
                return str(dados)

            # Ou uma lista de objetos com 'id' / 'idProcesso' / 'identificador'
            if isinstance(dados, list) and dados:
                primeiro = dados[0]
                id_resolvido = (
                    primeiro.get("id")
                    or primeiro.get("idProcesso")
                    or primeiro.get("identificador")
                )
                return str(id_resolvido) if id_resolvido else None

            return None
        except Exception as exc:
            logger.error(
                "Erro ao resolver ID para numero %s: %s",
                numero_processo,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Partes
    # ------------------------------------------------------------------

    def partes(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        """Retorna a lista de partes vinculadas ao processo.

        Endpoint:
            GET /pje-comum-api/api/processos/id/{id}/partes
        """
        url = self._url(
            f"/pje-comum-api/api/processos/id/{id_processo}/partes"
        )
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            logger.warning(
                "Falha ao obter partes do processo %s: %s",
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    # ------------------------------------------------------------------
    # Calculos / pericias
    # ------------------------------------------------------------------

    def calculos(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Retorna os calculos do processo.

        Endpoint:
            GET /pje-comum-api/api/calculos/processo?idProcesso={id}
        """
        url = self._url("/pje-comum-api/api/calculos/processo")
        params = {
            'idProcesso': id_processo,
            'pagina': 1,
            'tamanhoPagina': 10,
            'ordenacaoCrescente': 'true',
        }
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning(
                "Falha ao obter calculos para processo %s: %s",
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    def pericias(self, id_processo: str) -> Optional[Dict[str, Any]]:
        """Retorna as pericias associadas ao processo.

        Endpoint:
            GET /pje-comum-api/api/pericias?idProcesso={id}
        """
        url = self._url("/pje-comum-api/api/pericias")
        params = {'idProcesso': id_processo}
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning(
                "Falha ao obter pericias para processo %s: %s",
                id_processo,
                r.status_code,
            )
            return None
        return r.json()

    # ------------------------------------------------------------------
    # BNDT
    # ------------------------------------------------------------------

    def debitos_trabalhistas_bndt(
        self, id_processo: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Retorna as partes cadastradas no BNDT para o processo.

        Endpoint:
            GET /pje-comum-api/api/processos/id/{id}/debitostrabalhistas

        Returns:
            Lista de dicionarios com dados das partes no BNDT,
            lista vazia se nao ha registros, ou ``None`` em caso de erro.
        """
        url = self._url(
            f"/pje-comum-api/api/processos/id/{id_processo}/debitostrabalhistas"
        )
        try:
            r = self.sess.get(url, timeout=15)
            if not r.ok:
                logger.warning(
                    "Falha ao obter debitos trabalhistas BNDT "
                    "para processo %s: %s",
                    id_processo,
                    r.status_code,
                )
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception as exc:
            logger.error(
                "Erro ao obter debitos trabalhistas BNDT "
                "para processo %s: %s",
                id_processo,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Domicilio eletronico
    # ------------------------------------------------------------------

    def domicilio_eletronico(self, id_parte: str) -> Optional[bool]:
        """Verifica se a parte (Pessoa Juridica) possui
        domicilio eletronico habilitado.

        Endpoint:
            GET /pje-comum-api/api/pessoajuridicadomicilioeletronico/{id}

        Returns:
            ``True`` se habilitado, ``False`` se desabilitado,
            ``None`` se erro ou parte nao encontrada.
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
        except Exception as exc:
            logger.error(
                "Erro ao verificar domicilio eletronico da parte %s: %s",
                id_parte,
                exc,
            )
            return None


# ---------------------------------------------------------------------------
# session_from_driver
# ---------------------------------------------------------------------------


def session_from_driver(
    driver,
    grau: int = 1,
) -> Tuple[requests.Session, str]:
    """Cria um ``requests.Session`` a partir de um Selenium WebDriver.

    # Diferenca do original Peticao/api/client.py:
    # Andrei possui docstring completa com documentacao de parametros,
    # retorno e excecoes lancadas. O log de erro inclui a mensagem da
    # excecao (logger.error com %%s) para facilitar debug de falhas
    # transientes de sessao — o original usa mensagem estatica.

    Extrai os cookies da sessao autenticada do driver e os injeta
    em uma nova instancia de ``requests.Session`` com os headers
    padrao exigidos pela API do PJe (``X-Grau-Instancia``,
    ``Accept``, ``Content-Type``).

    Args:
        driver: Instancia de ``selenium.webdriver.Remote``
                (ou ``Chrome``, ``Firefox``, etc.) ja autenticada no PJe.
        grau: Grau de instancia (1 = primeiro, 2 = segundo).

    Returns:
        Tupla ``(requests.Session, trt_host)`` onde *trt_host* e o
        netloc extraido da URL atual do driver.

    Raises:
        Qualquer excecao da extracao de cookies ou parse da URL
        e propagada apos logging.
    """
    sess = requests.Session()
    try:
        cookies = driver.get_cookies()
        for c in cookies:
            sess.cookies.set(c['name'], c['value'])
        parsed = urlparse(driver.current_url)
        trt_host = parsed.netloc
    except Exception as exc:
        logger.error(
            "Erro ao criar sessao a partir do driver: %s", exc
        )
        raise

    sess.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Grau-Instancia': str(grau),
    })
    return sess, trt_host
