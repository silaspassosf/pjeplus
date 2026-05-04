"""
SISB Processamento - Reexports para compatibilidade (lazy via __getattr__)
"""
import importlib as _importlib

_fc = None

def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    global _fc
    if _fc is None:
        _fc = _importlib.import_module('SISB.facades_contratos')
    return getattr(_fc, name)

__all__ = [
    '_validar_dados',
    '_atualizar_relatorio_com_segundo_protocolo',
    '_executar_juntada_pje',
    '_voltar_para_lista_ordens_serie',
    '_voltar_para_lista_principal',
    '_carregar_dados_ordem',
    '_extrair_ordens_da_serie',
    '_identificar_ordens_com_bloqueio',
    '_aplicar_acao_por_fluxo',
    '_agrupar_dados_bloqueios',
    'extrair_dados_bloqueios_processados',
    'gerar_relatorio_bloqueios_processados',
    'gerar_relatorio_bloqueios_conciso',
    '_gerar_relatorio_ordem',
    '_filtrar_series',
    '_navegar_e_extrair_ordens_serie',
    '_extrair_nome_executado_serie',
    '_calcular_estrategia_bloqueio',
    '_processar_series',
    '_selecionar_prazo_bloqueio',
    '_preencher_campos_iniciais',
    '_processar_reus_otimizado',
    '_salvar_minuta',
    '_gerar_relatorio_minuta',
    'minuta_bloqueio_refatorada',
    '_processar_ordem',
]
