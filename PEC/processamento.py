# processamento_base removido — stubs para compatibilidade
def _lazy_import_pec(): return {}
def executar_acao(driver, acao, *a, **kw): return callable(acao) and acao(driver)
def processar_processo_pec_individual(driver): return False
from .processamento_fluxo import (
    executar_fluxo_robusto,
    executar_fluxo_novo,
    _configurar_driver,
    _navegar_atividades,
    _aplicar_filtros,
    _organizar_e_executar_buckets,
)
from .processamento_listas import (
    criar_lista_sisbajud,
    executar_lista_sisbajud_por_abas,
    criar_lista_resto,
)
from .processamento_indexacao import (
    _indexar_todos_processos,
    _filtrar_por_observacao,
    _salvar_amostra_debug_rows,
    _filtrar_por_progresso,
    _filtrar_por_acoes_validas,
    _agrupar_em_buckets,
    _executar_dry_run,
    indexar_e_criar_buckets_unico,
)
from .processamento_buckets import (
    _processar_buckets,
    _processar_bucket_generico,
    _processar_bucket_demais,
    _processar_bucket_sisbajud,
    _imprimir_relatorio_final,
)

__all__ = [
    '_lazy_import_pec',
    'executar_acao',
    'processar_processo_pec_individual',
    'executar_fluxo_robusto',
    'executar_fluxo_novo',
    '_configurar_driver',
    '_navegar_atividades',
    '_aplicar_filtros',
    '_organizar_e_executar_buckets',
    'criar_lista_sisbajud',
    'executar_lista_sisbajud_por_abas',
    'criar_lista_resto',
    '_indexar_todos_processos',
    '_filtrar_por_observacao',
    '_salvar_amostra_debug_rows',
    '_filtrar_por_progresso',
    '_filtrar_por_acoes_validas',
    '_agrupar_em_buckets',
    '_executar_dry_run',
    'indexar_e_criar_buckets_unico',
    '_processar_buckets',
    '_processar_bucket_generico',
    '_processar_bucket_demais',
    '_processar_bucket_sisbajud',
    '_imprimir_relatorio_final',
]


