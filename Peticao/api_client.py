# LEGADO — thin shim de compatibilidade
# Consumidores: testpet.py, orquestrador.py (runtime import)
from .runtime_pet import (
    PeticaoAPIClient,
    PeticaoItem,
    _normalizar,
    _JS_FETCH,
)
