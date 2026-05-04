"""Fix.selenium_base -- facade publica de operacoes Selenium base."""
from ..core import (
    safe_click, preencher_campo, preencher_campos_prazo, preencher_multiplos_campos,
    esperar_elemento, esperar_url_conter, wait_for_clickable,
    buscar_seletor_robusto, com_retry, selecionar_opcao,
)
from ..browser_suporte import aguardar_e_clicar, safe_click_no_scroll

__all__ = [
    'safe_click', 'preencher_campo', 'preencher_campos_prazo', 'preencher_multiplos_campos',
    'esperar_elemento', 'esperar_url_conter', 'wait_for_clickable',
    'buscar_seletor_robusto', 'com_retry', 'selecionar_opcao',
    'aguardar_e_clicar', 'safe_click_no_scroll',
]
