import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_angular - Módulo de funções específicas para aplicações Angular no PJe.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import time
from selenium.webdriver.common.by import By

def aguardar_angular_carregar(driver, timeout=30):
    """Aguarda até que o Angular esteja totalmente carregado"""
    try:
        # Verificar se Angular está definido
        angular_pronto = driver.execute_script("""
            return (typeof angular !== 'undefined' &&
                   angular.element(document).injector() &&
                   angular.element(document).injector().get('$http').pendingRequests.length === 0);
        """)

        if angular_pronto:
            return True

        # Aguardar carregamento do Angular
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                pronto = driver.execute_script("""
                    return (typeof angular !== 'undefined' &&
                           angular.element(document).injector() &&
                           angular.element(document).injector().get('$http').pendingRequests.length === 0);
                """)
                if pronto:
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        return False

    except Exception as e:
        logger.error(f"Erro ao aguardar Angular carregar: {e}")
        return False

def aguardar_angular_requests(driver, timeout=30):
    """Aguarda até que não haja requests HTTP pendentes no Angular"""
    try:
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                pending = driver.execute_script("""
                    if (typeof angular !== 'undefined' && angular.element(document).injector()) {
                        return angular.element(document).injector().get('$http').pendingRequests.length;
                    }
                    return 0;
                """)
                if pending == 0:
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        return False

    except Exception as e:
        logger.error(f"Erro ao aguardar Angular requests: {e}")
        return False

def clicar_elemento_angular(driver, seletor, timeout=10):
    """Clica em elemento Angular esperando estabilização"""
    try:
        from .extracao import aguardar_e_clicar

        # Aguardar Angular carregar
        if not aguardar_angular_carregar(driver, timeout=5):
            logger.warning("Angular não carregou completamente")

        # Clicar usando função padrão
        return aguardar_e_clicar(driver, seletor, timeout=timeout)

    except Exception as e:
        logger.error(f"Erro ao clicar elemento Angular {seletor}: {e}")
        return False

def preencher_campo_angular(driver, seletor, valor, timeout=10):
    """Preenche campo Angular esperando estabilização"""
    try:
        from .extracao import preencher_campo

        # Aguardar Angular carregar
        if not aguardar_angular_carregar(driver, timeout=5):
            logger.warning("Angular não carregou completamente")

        # Preencher usando função padrão
        return preencher_campo(driver, seletor, valor, timeout=timeout)

    except Exception as e:
        logger.error(f"Erro ao preencher campo Angular {seletor}: {e}")
        return False

def aguardar_elemento_angular_visivel(driver, seletor, timeout=10):
    """Aguarda elemento Angular ficar visível"""
    try:
        from .extracao import esperar_elemento

        # Aguardar Angular carregar primeiro
        aguardar_angular_carregar(driver, timeout=5)

        # Aguardar elemento
        elemento = esperar_elemento(driver, seletor, timeout=timeout)
        return elemento is not None

    except Exception as e:
        logger.error(f"Erro ao aguardar elemento Angular {seletor}: {e}")
        return False

def verificar_angular_app(driver):
    """Verifica se a página atual usa Angular"""
    try:
        return driver.execute_script("""
            return (typeof angular !== 'undefined' ||
                   document.querySelector('[ng-app]') !== null ||
                   document.querySelector('[ng-controller]') !== null ||
                   document.querySelector('[ng-model]') !== null);
        """)
    except Exception:
        return False

def aguardar_angular_digest(driver, timeout=10):
    """Aguarda o ciclo digest do Angular completar"""
    try:
        inicio = time.time()
        while time.time() - inicio < timeout:
            try:
                # Forçar digest cycle e verificar se está estável
                driver.execute_script("""
                    if (typeof angular !== 'undefined' && angular.element(document).injector()) {
                        var scope = angular.element(document).scope();
                        if (scope && scope.$$phase) {
                            scope.$digest();
                        }
                    }
                """)
                return True
            except Exception:
                pass
            time.sleep(0.5)

        return False

    except Exception as e:
        logger.error(f"Erro ao aguardar Angular digest: {e}")
        return False

def obter_angular_scope(driver, seletor_elemento=None):
    """Obtém o scope Angular de um elemento"""
    try:
        if seletor_elemento:
            script = f"""
                var element = document.querySelector('{seletor_elemento}');
                if (element && typeof angular !== 'undefined') {{
                    return angular.element(element).scope();
                }}
                return null;
            """
        else:
            script = """
                if (typeof angular !== 'undefined') {
                    return angular.element(document).scope();
                }
                return null;
            """

        return driver.execute_script(script)

    except Exception as e:
        logger.error(f"Erro ao obter Angular scope: {e}")
        return None

def executar_angular_expressao(driver, expressao, seletor_contexto=None):
    """Executa uma expressão Angular no contexto de um elemento"""
    try:
        if seletor_contexto:
            script = f"""
                var element = document.querySelector('{seletor_contexto}');
                if (element && typeof angular !== 'undefined') {{
                    var scope = angular.element(element).scope();
                    if (scope) {{
                        return scope.$eval('{expressao}');
                    }}
                }}
                return null;
            """
        else:
            script = f"""
                if (typeof angular !== 'undefined') {{
                    var scope = angular.element(document).scope();
                    if (scope) {{
                        return scope.$eval('{expressao}');
                    }}
                }}
                return null;
            """

        return driver.execute_script(script)

    except Exception as e:
        logger.error(f"Erro ao executar expressão Angular '{expressao}': {e}")
        return None