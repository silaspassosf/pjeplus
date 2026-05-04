# LEGADO — thin shim de compatibilidade
# Consumidores: x.py (run_pet), testpet.py, orquestrador.py (runtime imports)
from .runtime_pet import (
    analise_pet,
    classificar,
    extrair_texto_peticao_via_api,
    resolver_acao,
    run_pet,
    _abrir_documento_peticao,
    _Dados,
    _detectar_acao_analise,
    _extrair_texto_doc_pet,
    _run_pet_falha,
    _run_pet_ok,
)
