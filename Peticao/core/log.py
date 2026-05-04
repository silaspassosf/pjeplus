"""
Thin shim — consolidado em Peticao/suporte_pet.py
Mantido para compatibilidade retroativa.
"""
from ..suporte_pet import (
    LogLevel,
    EmojiValidator,
    PJePlusFormatter,
    PJePlusLogger,
    initialize_logging,
    get_module_logger,
    log_seletor_multiplo,
    tentar_seletores,
    registrar_seletor_correto,
    tentar_seletores_com_registro,
    getmodulelogger,
)
