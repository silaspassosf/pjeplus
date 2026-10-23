"""Delegado — canonical em api/variaveis_client.py (F4).

Era uma cópia do cliente; não tem importadores no repositório. Mantido como
superfície de compatibilidade para quem importar `Peticao.api.client` no futuro.
"""
from api.variaveis_client import PjeApiClient, session_from_driver  # noqa: F401

__all__ = ["PjeApiClient", "session_from_driver"]
