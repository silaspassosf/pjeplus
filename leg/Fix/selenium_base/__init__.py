"""Fix.selenium_base package"""
from .element_interaction import safe_click, preencher_campos_prazo
from .click_operations import aguardar_e_clicar, safe_click_no_scroll
from .wait_operations import esperar_elemento, esperar_url_conter
from .retry_logic import buscar_seletor_robusto, com_retry
from ..core import selecionar_opcao, preencher_campo
__all__ = ['safe_click', 'preencher_campos_prazo', 'aguardar_e_clicar', 'safe_click_no_scroll', 'esperar_elemento', 'esperar_url_conter', 'buscar_seletor_robusto', 'com_retry', 'selecionar_opcao', 'preencher_campo']
