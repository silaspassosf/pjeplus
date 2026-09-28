from typing import Optional, Any, Dict, List, Tuple
from urllib.parse import urlparse

import requests

from ..core.log import get_module_logger

logger = get_module_logger(__name__)


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
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning(f"[API_CLIENT] Falha ao obter timeline para processo {id_processo}: {r.status_code}")
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
            logger.warning(f"[API_CLIENT] Falha ao obter documento {id_documento} do processo {id_processo}: {r.status_code}")
            return None
        return r.json()

    def execucao_gigs(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-gigs-api/api/execucao/{id_processo}")
        # fallback para endpoint usado na extensão
        alt = self._url(f"/pje-gigs-api/api/processo/{id_processo}")
        r = self.sess.get(alt, timeout=15)
        if not r.ok:
            logger.warning(f"[API_CLIENT] Falha ao obter execução GIGS para processo {id_processo}: {r.status_code}")
            return None
        return r.json()

    def processo_por_id(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            logger.warning(f"[API_CLIENT] Falha ao obter processo {id_processo}: {r.status_code}")
            return None
        return r.json()

    def partes(self, id_processo: str) -> Optional[List[Dict[str, Any]]]:
        url = self._url(f"/pje-comum-api/api/processos/id/{id_processo}/partes")
        r = self.sess.get(url, timeout=15)
        if not r.ok:
            logger.warning(f"[API_CLIENT] Falha ao obter partes do processo {id_processo}: {r.status_code}")
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
                logger.warning(f"[API_CLIENT] Falha ao resolver ID para número {numero_processo}: {r.status_code}")
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
        except Exception as e:
            logger.error(f"[API_CLIENT] Erro ao resolver ID para número {numero_processo}: {e}")
            return None

    def calculos(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/calculos/processo")
        params = {'idProcesso': id_processo, 'pagina': 1, 'tamanhoPagina': 10, 'ordenacaoCrescente': 'true'}
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning(f"[API_CLIENT] Falha ao obter cálculos para processo {id_processo}: {r.status_code}")
            return None
        return r.json()

    def pericias(self, id_processo: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/pje-comum-api/api/pericias")
        params = {'idProcesso': id_processo}
        r = self.sess.get(url, params=params, timeout=15)
        if not r.ok:
            logger.warning(f"[API_CLIENT] Falha ao obter perícias para processo {id_processo}: {r.status_code}")
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
                logger.warning(f"[API_CLIENT] Falha ao obter atividades GIGS para processo {id_processo}: {r.status_code}")
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception as e:
            logger.error(f"[API_CLIENT] Erro ao obter atividades GIGS para processo {id_processo}: {e}")
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
                logger.warning(f"[API_CLIENT] Falha ao obter débitos trabalhistas BNDT para processo {id_processo}: {r.status_code}")
                return None
            dados = r.json()
            if not isinstance(dados, list):
                return None
            return dados
        except Exception as e:
            logger.error(f"[API_CLIENT] Erro ao obter débitos trabalhistas BNDT para processo {id_processo}: {e}")
            return None


def session_from_driver(driver, grau: int = 1) -> Tuple[requests.Session, str]:
    """Cria um `requests.Session` a partir de um Selenium `driver`.

    Retorna (session, trt_host).
    """
    sess = requests.Session()
    try:
        cookies = driver.get_cookies()
        for c in cookies:
            sess.cookies.set(c['name'], c['value'])
        parsed = urlparse(driver.current_url)
        trt_host = parsed.netloc
    except Exception:
        logger.error("[API_CLIENT] Erro ao criar sessão a partir do driver")
        raise
    sess.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Grau-Instancia': str(grau)
    })
    return sess, trt_host