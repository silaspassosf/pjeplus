"""
Fix/otimizacao_wrapper.py
Wrapper minimalista para integrar otimizações nos fluxos existentes
"""
from typing import Callable, Optional, Any
from selenium.webdriver.remote.webdriver import WebDriver


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
            try:
                # Tentar usar sistema de aprendizado
                from selector_learning import use_best_selector, get_recommended_selectors
                
                # Se primeira arg é driver, usar sistema inteligente
                if args and hasattr(args[0], 'find_element'):
                    driver = args[0]
                    selectors = get_recommended_selectors(context, operation, [default_selector])
                    
                    # Tentar com cada seletor recomendado
                    for selector in selectors:
                        try:
                            # Modificar kwargs temporariamente se função aceitar seletor
                            if 'seletor' in kwargs or 'selector' in kwargs:
                                old_selector = kwargs.get('seletor') or kwargs.get('selector')
                                kwargs['seletor'] = selector if 'seletor' in kwargs else kwargs.get('seletor')
                                kwargs['selector'] = selector if 'selector' in kwargs else kwargs.get('selector')
                            
                            result = func(*args, **kwargs)
                            
                            # Registrar sucesso
                            from selector_learning import report_selector_result
                            report_selector_result(context, operation, selector, True)
                            return result
                        except Exception as e:
                            # Registrar falha
                            from selector_learning import report_selector_result
                            report_selector_result(context, operation, selector, False)
                            continue
            except ImportError:
                pass  # Sistema de aprendizado não disponível
            
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
        from Fix.headless_helpers import click_headless_safe
        return click_headless_safe(driver, seletor, timeout=timeout)
    except ImportError:
        # Fallback para aguardar_e_clicar padrão
        from Fix.core import aguardar_e_clicar
        return aguardar_e_clicar(driver, seletor, timeout=timeout)


def inicializar_otimizacoes():
    """
    Inicializa sistemas de otimização no início da execução.
    Chamar uma vez no início do script principal.
    """
    try:
        from selector_learning import get_learning_stats
        stats = get_learning_stats()
        print(f"[OTIMIZAÇÃO] Sistema de aprendizado ativo:")
        print(f"  - Seletores conhecidos: {stats['total_selectors']}")
        print(f"  - Taxa de sucesso: {stats['success_rate']:.1%}")
        print(f"  - Score médio: {stats['avg_score']:.2f}")
        return True
    except ImportError:
        print("[OTIMIZAÇÃO] Sistema de aprendizado não disponível")
        return False


def finalizar_otimizacoes():
    """
    Salva dados de aprendizado no final da execução.
    Chamar no finally do script principal.
    """
    try:
        from selector_learning import save_learning_db, get_learning_stats
        save_learning_db()
        stats = get_learning_stats()
        print(f"[OTIMIZAÇÃO] Base de aprendizado salva ({stats['total_selectors']} seletores)")
        return True
    except ImportError:
        return False
