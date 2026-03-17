"""
Módulo SISB - Automação SISBAJUD/BACEN (Refatorado)
Integra funcionalidades para criação de minutas de bloqueio

Arquitetura Modular:
- core.py: Inicialização, login, configuração
- processamento.py: Lógica de negócio (minutas, ordens)
- utils.py: Utilitários, helpers, validações
- standards.py: Padrões, constantes, tipos
- performance.py: Otimizações de performance
- s_orquestrador.py: Orquestrador principal
"""

# Imports dos módulos core
from .core import (
    iniciar_sisbajud,
    driver_sisbajud,
    login_automatico_sisbajud,
    login_manual_sisbajud
)

# Imports dos módulos de processamento
# from .processamento import (
#     minuta_bloqueio_refatorada,
# )  # Removido - função não existe

# Placeholder
minuta_bloqueio_refatorada = None

# Imports dos utilitários refatorados
from .utils import (
    criar_js_otimizado,
    safe_click,
    aguardar_elemento,
    log_sisbajud,
    validar_numero_processo,
    formatar_valor_monetario
)

# Imports dos padrões
from .standards import (
    SISBConstants,
    StatusProcessamento,
    TipoFluxo,
    DadosProcesso,
    ResultadoProcessamento,
    sisb_logger
)

# Imports das otimizações de performance
from .performance import (
    performance_optimizer,
    polling_reducer,
    cache_manager,
    parallel_processor
)

# Import do orquestrador principal
from .s_orquestrador import executar_sisbajud_completo

# Import do módulo batch para processamento em lote
from .batch import processar_lote_sisbajud

__all__ = [
    # Core
    'iniciar_sisbajud',
    'driver_sisbajud',
    'login_automatico_sisbajud',
    'login_manual_sisbajud',

    # Processamento
    'minuta_bloqueio_refatorada',

    # Utilitários
    'criar_js_otimizado',
    'safe_click',
    'aguardar_elemento',
    'log_sisbajud',
    'validar_numero_processo',
    'formatar_valor_monetario',

    # Padrões
    'SISBConstants',
    'StatusProcessamento',
    'TipoFluxo',
    'DadosProcesso',
    'ResultadoProcessamento',
    'sisb_logger',

    # Performance
    'performance_optimizer',
    'polling_reducer',
    'cache_manager',
    'parallel_processor',

    # Orquestrador
    'executar_sisbajud_completo',
    
    # Batch (lote)
    'processar_lote_sisbajud'
]

__version__ = '3.0.0'