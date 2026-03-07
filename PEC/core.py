"""Módulo PEC - Processamento de Execução e Cumprimento (PJe)."""

from .core_progresso import (
    carregar_progresso_pec,
    salvar_progresso_pec,
    extrair_numero_processo_pec,
    verificar_acesso_negado_pec,
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
)
from .core_recovery import verificar_e_recuperar_acesso_negado, reiniciar_driver_e_logar_pje
from .core_navegacao import navegar_para_atividades, aplicar_filtro_xs, indexar_processo_atual_gigs
from .core_pos_carta import analisar_documentos_pos_carta
from .core_main import main




