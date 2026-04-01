"""
Ciclo 3: Cumprimento de Providências - Marcar XS em processos LIVRES
Fase final do loop de prazos: processa painel 6 para marcar processos sem GIGS
"""
import logging
import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
import math

from .loop_base import (
    logger,
    aplicar_filtro_100,
    SCRIPT_SELECAO_LIVRES
)
from .loop_ciclo2_processamento import _ciclo2_criar_atividade_xs

URL_PAINEL_CUMPRIMENTO = 'https://pje.trt2.jus.br/pjekz/painel/global/6/lista-processos'


def ciclo3(driver: WebDriver) -> bool:
    """
    Ciclo 3: Processar painel de cumprimento de providências (painel 6)
    
    Fluxo:
    1. Navega para painel global 6 (cumprimento de providências)
    2. Aplica filtro 100
    3. Seleciona processos LIVRES (sem GIGS)
    4. Aplica atividade XS se houver processos livres
    
    Args:
        driver: WebDriver já logado
        
    Returns:
        True se sucesso, False se falha crítica
    """
    try:
        logger.info("[CICLO3] Iniciando processamento painel cumprimento providências")
        
        # 1. Navegação
        logger.info(f"[CICLO3] Navegando para painel 6: {URL_PAINEL_CUMPRIMENTO}")
        driver.get(URL_PAINEL_CUMPRIMENTO)
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=3)
        except Exception:
            time.sleep(3)
        
        # 2. Aplicar filtro 100
        logger.info("[CICLO3] Aplicando filtro 100...")
        try:
            aplicar_filtro_100(driver)
            logger.info("[CICLO3] ✓ Filtro 100 aplicado")
        except Exception as e:
            logger.error(f"[CICLO3] Erro ao aplicar filtro 100: {e}")
            return False
        
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=2)
        except Exception:
            time.sleep(2)

        # 3. Selecionar livres: percorrer todas as páginas após aplicar filtro 100
        logger.info("[CICLO3] Selecionando processos livres (sem GIGS) em todas as páginas...")

        # Tentar obter total de processos para calcular número de páginas
        try:
            total_text = driver.find_element(By.CSS_SELECTOR, 'span.total-registros').text
            import re
            m = re.search(r'de\s+(\d+)', total_text)
            total = int(m.group(1)) if m else -1
        except Exception:
            total = -1

        if total > 0:
            paginas = math.ceil(total / 100)
        else:
            paginas = 1

        total_selecionados = 0
        for pagina in range(paginas):
            try:
                selecionados = driver.execute_script(SCRIPT_SELECAO_LIVRES)
                if selecionados == -1:
                    logger.error(f"[CICLO3] ERRO no script de seleção de livres na página {pagina+1}")
                    return False
                elif isinstance(selecionados, int) and selecionados > 0:
                    total_selecionados += selecionados
                    logger.info(f"[CICLO3] Página {pagina+1}: {selecionados} livres selecionados")
                else:
                    logger.info(f"[CICLO3] Página {pagina+1}: 0 livres selecionados")
            except Exception as e:
                logger.error(f"[CICLO3] Erro ao selecionar livres na página {pagina+1}: {e}")

            # Ir para próxima página, se houver
            if pagina < paginas - 1:
                try:
                    btn_next = driver.find_element(By.CSS_SELECTOR, 'mat-paginator button[aria-label="Próxima página"]')
                    driver.execute_script('arguments[0].click();', btn_next)
                    try:
                        from Fix.core import aguardar_renderizacao_nativa
                        aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
                    except Exception:
                        time.sleep(1)
                except Exception:
                    logger.info("[CICLO3] Não foi possível navegar para próxima página (ou última página atingida)")

        logger.info(f"[CICLO3] ✓ Total de processos livres selecionados: {total_selecionados}")

        # 4. Aplicar XS se houver processos
        if total_selecionados > 0:
            logger.info("[CICLO3] Aplicando atividade XS para os processos selecionados...")
            _ciclo2_criar_atividade_xs(driver)
            logger.info("[CICLO3] ✓ Atividade XS aplicada")
        else:
            logger.info("[CICLO3] Nenhum processo livre encontrado")
        
        logger.info("[CICLO3] ✓ Ciclo 3 concluído com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"[CICLO3] Erro no ciclo 3: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
