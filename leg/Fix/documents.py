"""Fix.documents - Re-exporte para Fix.extracao e Fix.core"""
from .extracao import indexar_e_processar_lista, extrair_dados_processo, carregar_destinatarios_cache
from .core import buscar_documentos_sequenciais
__all__ = ['buscar_documentos_sequenciais', 'indexar_e_processar_lista', 'extrair_dados_processo', 'carregar_destinatarios_cache']
