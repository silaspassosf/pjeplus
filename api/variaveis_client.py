"""api.variaveis_client — re-export canônico de Fix.variaveis."""
from Fix.variaveis import (  # noqa: F401
    GatewayError,
    GatewayResult,
    PjeApiClient,
    cliente_para,
    session_from_driver,
)

__all__ = [
    'GatewayError',
    'GatewayResult',
    'PjeApiClient',
    'cliente_para',
    'session_from_driver',
]
