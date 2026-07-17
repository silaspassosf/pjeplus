"""Compatibilidade para o namespace legado Fix.variaveis_client."""

from .facade_publica import PjeApiClient, session_from_driver

__all__ = ["PjeApiClient", "session_from_driver"]
