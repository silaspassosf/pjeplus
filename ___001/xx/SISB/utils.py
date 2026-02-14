"""SISB utils - Compat wrapper para SISB.Core e SISB.processamento."""

from .Core.utils_const import SISBAJUD_URLS, TIMEOUTS, SELECTORS
from .Core.utils_js import (
    criar_js_otimizado,
    mutation_observer_script,
    rate_limiting_manager,
    advanced_dom_manipulator,
    consolidated_js_framework,
)
from .Core.utils_web import (
    safe_click,
    simulate_human_movement,
    aguardar_elemento,
    aguardar_e_clicar,
    escolher_opcao_sisbajud,
    aplicar_rate_limiting,
    detectar_captcha,
    anti_detection_measures,
    smart_wait,
)
from .Core.utils_dados import (
    extrair_protocolo,
    validar_numero_processo,
    formatar_valor_monetario,
    calcular_data_limite,
    criar_timestamp,
    log_sisbajud,
    registrar_erro_minuta,
    carregar_dados_processo,
)
from .Core.sessao_helpers import (
    _extrair_dados_pje,
    _criar_driver_sisbajud,
    _realizar_login,
    _navegar_minuta,
)
from .processamento import (
    _validar_dados,
    _preencher_campos_iniciais,
    _processar_reus_otimizado,
    _salvar_minuta,
)

__all__ = [
    'SISBAJUD_URLS',
    'TIMEOUTS',
    'SELECTORS',
    'criar_js_otimizado',
    'mutation_observer_script',
    'rate_limiting_manager',
    'advanced_dom_manipulator',
    'consolidated_js_framework',
    'safe_click',
    'simulate_human_movement',
    'aguardar_elemento',
    'aguardar_e_clicar',
    'escolher_opcao_sisbajud',
    'aplicar_rate_limiting',
    'detectar_captcha',
    'anti_detection_measures',
    'smart_wait',
    'extrair_protocolo',
    'validar_numero_processo',
    'formatar_valor_monetario',
    'calcular_data_limite',
    'criar_timestamp',
    'log_sisbajud',
    'registrar_erro_minuta',
    'carregar_dados_processo',
    '_extrair_dados_pje',
    '_criar_driver_sisbajud',
    '_realizar_login',
    '_navegar_minuta',
    '_validar_dados',
    '_preencher_campos_iniciais',
    '_processar_reus_otimizado',
    '_salvar_minuta',
]
