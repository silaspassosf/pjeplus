# LEGADO — thin shim de compatibilidade
# Consumidores: orquestrador.py (runtime import)
from .runtime_pet import (
    carregar_progresso_pet,
    marcar_processo_executado_pet,
    processo_ja_executado_pet,
    salvar_progresso_pet,
)
