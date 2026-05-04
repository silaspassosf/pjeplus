# LEGADO — thin shim de compatibilidade
# Consumidores: testpet.py (ESCANINHO_URL), pet.py (executar_fluxo_pet, runtime import)
from .runtime_pet import (
    PETOrquestrador,
    executar_fluxo_pet,
    ESCANINHO_URL,
    BUCKETS_ORDEM,
    _abrir_processo,
    _classificar,
    _consolidar_delete_bookmarklet,
    _executar_bucket_analise,
    _executar_bucket_apagar,
    _executar_bucket_normal,
    _fechar_abas_extras,
)
