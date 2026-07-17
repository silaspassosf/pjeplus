"""
SISB - Fachada de compatibilidade
Reexporta nomes publicos de SISB.facades_contratos
"""
import logging

logger = logging.getLogger(__name__)
__version__ = '3.0.0'

from SISB.facades_contratos import (  # noqa: E402, F401
    # Core
    iniciar_sisbajud,
    driver_sisbajud,
    login_automatico_sisbajud,
    login_manual_sisbajud,

    # Utils
    criar_js_otimizado,
    safe_click,
    aguardar_elemento,
    log_sisbajud,
    validar_numero_processo,
    formatar_valor_monetario,

    # Padroes
    SISBConstants,
    StatusProcessamento,
    TipoFluxo,
    DadosProcesso,
    ResultadoProcessamento,
    sisb_logger,

    # Performance
    performance_optimizer,
    polling_reducer,
    cache_manager,
    parallel_processor,

    # Orquestrador
    executar_sisbajud_completo,

    # Batch
    processar_lote_sisbajud,

    # Processamento
    minuta_bloqueio_refatorada,
)

__all__ = [
    'iniciar_sisbajud', 'driver_sisbajud', 'login_automatico_sisbajud', 'login_manual_sisbajud',
    'minuta_bloqueio_refatorada',
    'criar_js_otimizado', 'safe_click', 'aguardar_elemento', 'log_sisbajud',
    'validar_numero_processo', 'formatar_valor_monetario',
    'SISBConstants', 'StatusProcessamento', 'TipoFluxo', 'DadosProcesso', 'ResultadoProcessamento',
    'sisb_logger',
    'performance_optimizer', 'polling_reducer', 'cache_manager', 'parallel_processor',
    'executar_sisbajud_completo',
    'processar_lote_sisbajud',
]
