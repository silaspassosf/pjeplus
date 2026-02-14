"""
SISB Processamento - Reexports para compatibilidade
"""

from .validacao import _validar_dados
from .integracao import _atualizar_relatorio_com_segundo_protocolo, _executar_juntada_pje
from .navegacao import _voltar_para_lista_ordens_serie, _voltar_para_lista_principal
from .ordens_dados import _carregar_dados_ordem, _extrair_ordens_da_serie, _identificar_ordens_com_bloqueio
from .ordens_acao import _aplicar_acao_por_fluxo
from .relatorios_dados import _agrupar_dados_bloqueios, extrair_dados_bloqueios_processados
from .relatorios_formatacao import gerar_relatorio_bloqueios_processados, gerar_relatorio_bloqueios_conciso
from .relatorios_ordem import _gerar_relatorio_ordem
from .series_filtro import _filtrar_series
from .series_navegar import _navegar_e_extrair_ordens_serie, _extrair_nome_executado_serie
from .series_estrategia import _calcular_estrategia_bloqueio
from .series_fluxo import _processar_series
from .minutas_prazo import _selecionar_prazo_bloqueio
from .minutas_campos import _preencher_campos_iniciais
from .minutas_reus import _processar_reus_otimizado
from .minutas_salvar import _salvar_minuta
from .minutas_relatorio import _gerar_relatorio_minuta
from .minutas_protocolo import _protocolar_minuta
from .minutas_copia import _criar_minuta_agendada_por_copia
from .minutas_agendada import _criar_minuta_agendada
from ..processamento_minuta import minuta_bloqueio_refatorada

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
    '_protocolar_minuta',
    '_criar_minuta_agendada_por_copia',
    '_criar_minuta_agendada',
    'minuta_bloqueio_refatorada',
]