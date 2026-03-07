"""
Ciclo 3: Cumprimento de Providências - Marcar XS em processos LIVRES
Fase final do loop de prazos: processa painel 6 para marcar processos sem GIGS
"""
import logging
import time
from selenium.webdriver.remote.webdriver import WebDriver

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
        time.sleep(3)
        
        # 2. Aplicar filtro 100
        logger.info("[CICLO3] Aplicando filtro 100...")
        try:
            aplicar_filtro_100(driver)
            logger.info("[CICLO3] ✓ Filtro 100 aplicado")
        except Exception as e:
            logger.error(f"[CICLO3] Erro ao aplicar filtro 100: {e}")
            return False
        
        time.sleep(2)
        
        # 3. Selecionar livres
        logger.info("[CICLO3] Selecionando processos livres (sem GIGS)...")
        livres_selecionados = driver.execute_script(SCRIPT_SELECAO_LIVRES)
        logger.info(f"[CICLO3] ✓ {livres_selecionados} processos livres selecionados")
        
        # 4. Aplicar XS se houver processos
        if livres_selecionados > 0:
            logger.info("[CICLO3] Aplicando atividade XS...")
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
