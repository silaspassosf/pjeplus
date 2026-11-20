"""SISB - Fachada de compatibilidade"""
import logging

logger = logging.getLogger(__name__)
__version__ = '3.0.0'

from SISB.facades_contratos import (  # noqa: E402, F401
    iniciar_sisbajud,
    driver_sisbajud,
    login_automatico_sisbajud,
    login_manual_sisbajud,
    is_tela_login_sisbajud,
    is_sessao_ativa_sisbajud,
    salvar_cookies_sisbajud,
    carregar_cookies_sisbajud,
    salvar_sessao_sisbajud,
    restaurar_sessao_sisbajud,
    verificar_e_aplicar_cookies_sisbajud,
    USAR_COOKIES_AUTOMATICO,
    SALVAR_COOKIES_AUTOMATICO,

    criar_js_otimizado,
    safe_click,
    aguardar_elemento,
    log_sisbajud,
    validar_numero_processo,
    formatar_valor_monetario,

    SISBConstants,
    StatusProcessamento,
    TipoFluxo,
    DadosProcesso,
    ResultadoProcessamento,
    sisb_logger,

    performance_optimizer,
    polling_reducer,
    cache_manager,
    parallel_processor,

    executar_sisbajud_completo,

    processar_lote_sisbajud,

    minuta_bloqueio_refatorada,

    minuta_bloqueio,
    minuta_bloqueio_60,
    minuta_bloqueio_amanha,
)

__all__ = [
    'iniciar_sisbajud', 'driver_sisbajud', 'login_automatico_sisbajud', 'login_manual_sisbajud',
    'is_tela_login_sisbajud', 'is_sessao_ativa_sisbajud',
    'salvar_cookies_sisbajud', 'carregar_cookies_sisbajud', 'salvar_sessao_sisbajud', 'restaurar_sessao_sisbajud',
    'verificar_e_aplicar_cookies_sisbajud', 'USAR_COOKIES_AUTOMATICO', 'SALVAR_COOKIES_AUTOMATICO',
    'minuta_bloqueio_refatorada',
    'minuta_bloqueio', 'minuta_bloqueio_60', 'minuta_bloqueio_amanha',
    'criar_js_otimizado', 'safe_click', 'aguardar_elemento', 'log_sisbajud',
    'validar_numero_processo', 'formatar_valor_monetario',
    'SISBConstants', 'StatusProcessamento', 'TipoFluxo', 'DadosProcesso', 'ResultadoProcessamento',
    'sisb_logger',
    'performance_optimizer', 'polling_reducer', 'cache_manager', 'parallel_processor',
    'executar_sisbajud_completo',
    'processar_lote_sisbajud',
]
