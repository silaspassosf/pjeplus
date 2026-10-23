from typing import Optional, Any, Dict, List, Tuple, TypedDict
from urllib.parse import unquote, urlparse

import requests


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

    def _xsrf_token(self) -> Optional[str]:
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
    ) -> GatewayResult:
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
    ) -> GatewayResult:
        return self.request_gateway('GET', path, params=params, headers=headers, timeout=timeout)

    def gateway_post(
        self,
        path: str,
        *,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
    ) -> GatewayResult:
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
        return self.request_gateway(
            'PATCH',
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
        )

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
        # fallback para endpoint usado na extensão
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

    def partes(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            return None
        return r.json()

    def id_processo_por_numero(self, numero_processo: str) -> Optional[str]:
        """Resolve o ID interno do PJe a partir do número CNJ.
        
        Endpoint baseado na extensão (apis.idProcessoPorNumero):
        GET /pje-comum-api/api/processos?numero={numero}
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
            
            # Se é um inteiro direto, retorna como string
            if isinstance(dados, int):
                return str(dados)
            
            # Se é uma lista com objetos
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
        """Obtém atividades GIGS do processo via API.
        
        Retorna lista de atividades com campos:
        - tipoAtividade: descrição do tipo
        - dataPrazo: data do prazo (formato ISO ou DD/MM/YYYY)
        - statusAtividade: status da atividade
        - observacao: observações
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
        """Obtém partes cadastradas no BNDT (Banco Nacional de Devedores Trabalhistas).
        
        Baseado na função JavaScript obterPartesNoBNDT() do a.py
        Endpoint: GET /pje-comum-api/api/processos/id/{idProcesso}/debitostrabalhistas
        
        Args:
            id_processo: ID do processo (numérico interno)
        
        Returns:
            Lista de dicionários com dados das partes no BNDT ou None em caso de erro.
            Cada item contém pelo menos: {'nomeParte': 'Nome da Parte', ...}
            Lista vazia [] indica que não há partes cadastradas no BNDT.
        
        Exemplo:
            >>> partes_bndt = client.debitos_trabalhistas_bndt('1234567')
            >>> if partes_bndt:
            >>>     for parte in partes_bndt:
            >>>         print(f"Parte no BNDT: {parte.get('nomeParte')}")
            >>> else:
            >>>     print("Nenhuma parte no BNDT")
        """
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

    def domicilio_eletronico(self, id_parte: str) -> Optional[bool]:
        """Verifica domicílio eletrônico (apenas PJ).

        Retorna True se habilitada, False se não, None em erro/404 (PF ou não encontrada).
        """
        if not id_parte or id_parte in ('None', '0', ''):
            return None
        url = self._url(f"/pje-comum-api/api/pessoajuridicadomicilioeletronico/{id_parte}")
        try:
            r = self.sess.get(url, timeout=10)
            if not r.ok:
                return None
            return bool(r.json().get('habilitada', False))
        except Exception:
            return None


def session_from_driver(driver, grau: int = 1) -> Tuple[requests.Session, str]:
    """Cria um `requests.Session` a partir de um driver ativo (Selenium ou PWDriver).

    Retorna (session, trt_host).

    F4: headers endurecidos absorvidos do cliente bianca — X-XSRF-TOKEN evita
    403 CSRF em POST/PATCH e User-Agent real do driver evita bloqueio de WAF
    (Cloudflare/F5) contra UA de biblioteca. Aditivo: nao altera o resto.
    """
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
        # Se o browser estiver fora do PJe (tela de SSO/login em outro host),
        # o netloc da URL nao serve de base para a API — volta ao padrao.
        if 'trt2.jus.br' not in trt_host:
            trt_host = 'pje.trt2.jus.br'
    except Exception:
        raise
    # UA real do driver (sem padrao selenium; fallback defensivo)
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