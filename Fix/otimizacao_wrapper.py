import logging
logger = logging.getLogger(__name__)

"""
Fix/otimizacao_wrapper.py
Wrapper minimalista para integrar otimizações nos fluxos existentes
"""

from typing import Callable, Optional, Any
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.headless_helpers import click_headless_safe
from Fix.core import aguardar_e_clicar
try:
    from selector_learning import use_best_selector, get_recommended_selectors, report_selector_result, get_learning_stats, save_learning_db
except ImportError:
    use_best_selector = None
    get_recommended_selectors = None
    report_selector_result = None
    get_learning_stats = None
    save_learning_db = None

def with_learning(context: str, operation: str, default_selector: str):
    """
    Decorator para adicionar aprendizado a funções de click.
    USO MÍNIMO - não altera assinaturas existentes.
    
    Exemplo:
        @with_learning("prazo", "botao_filtro", "button.filtro")
        def clicar_filtro(driver):
            aguardar_e_clicar(driver, "button.filtro")
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Tentar usar sistema de aprendizado
            if get_recommended_selectors is not None and report_selector_result is not None:
                # Se primeira arg é driver, usar sistema inteligente
                if args and hasattr(args[0], 'find_element'):
                    driver = args[0]
                    selectors = get_recommended_selectors(context, operation, [default_selector])
                    # Tentar com cada seletor recomendado
                    for selector in selectors:
                        try:
                            # Modificar kwargs temporariamente se função aceitar seletor
                            if 'seletor' in kwargs or 'selector' in kwargs:
                                kwargs['seletor'] = selector if 'seletor' in kwargs else kwargs.get('seletor')
                                kwargs['selector'] = selector if 'selector' in kwargs else kwargs.get('selector')
                            result = func(*args, **kwargs)
                            report_selector_result(context, operation, selector, True)
                            return result
                        except Exception:
                            report_selector_result(context, operation, selector, False)
                            continue
            # Fallback para função original
            return func(*args, **kwargs)
        return wrapper
    return decorator

def usar_headless_safe(driver: WebDriver, seletor: str, timeout: int = 10) -> bool:
    """
    Função helper para usar click headless-safe nos fluxos.
    Pode ser usada diretamente ou como wrapper.
    
    Args:
        driver: WebDriver
        seletor: Seletor CSS
        timeout: Timeout em segundos
        
    Returns:
        bool: True se sucesso
    """
    try:
        return click_headless_safe(driver, seletor, timeout=timeout)
    except Exception:
        return aguardar_e_clicar(driver, seletor, timeout=timeout)

def inicializar_otimizacoes():
    """
    Inicializa sistemas de otimização no início da execução.
    Chamar uma vez no início do script principal.
    """
    if get_learning_stats is not None:
        stats = get_learning_stats()
        return True
    return False

def finalizar_otimizacoes():
    """
    Salva dados de aprendizado no final da execução.
    Chamar no finally do script principal.
    """
    if save_learning_db is not None and get_learning_stats is not None:
        save_learning_db()
        stats = get_learning_stats()
        return True
    return False
