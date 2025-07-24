"""
Módulo responsável pelo setup e configuração inicial do driver Selenium.

Responsabilidades:
- Configuração inicial do driver
- Limpeza de arquivos temporários
- Preparação do ambiente de automação

Funções extraídas do m1.py:
- setup_driver()
"""

from Fix import limpar_temp_selenium
from driver_config import criar_driver

def setup_driver():
    """
    Setup inicial do driver e limpeza.
    
    Returns:
        webdriver: Instância do driver configurado ou None em caso de erro
    """
    limpar_temp_selenium()
    driver = criar_driver(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return None
    return driver
