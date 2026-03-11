import logging
logger = logging.getLogger(__name__)

"""
Módulo Prazo - Sistema de processamento de prazos PJe
Refatoração seguindo guia unificado: padrão Orchestrator + Helpers
Redução de complexidade: fluxo_pz 95%, fluxo_prazo 77%
Arquitetura modular: 4 arquivos especializados
"""

# Imports principais para facilitar uso do módulo
from .p2b_core import (
    normalizar_texto, gerar_regex_geral, parse_gigs_param,
    carregar_progresso_p2b, salvar_progresso_p2b, marcar_processo_executado_p2b,
    processo_ja_executado_p2b, RegraProcessamento, REGEX_PATTERNS
)

from .p2b_fluxo import fluxo_pz
from .p2b_prazo import fluxo_prazo
from .loop_ciclo1 import ciclo1
from .loop_ciclo2_processamento import ciclo2
from .loop_ciclo3 import ciclo3

__version__ = "2.0.0"
__author__ = "Sistema PJePlus - Refatoração IA"

from selenium.webdriver.remote.webdriver import WebDriver
from typing import Dict, Any
from .loop_base import pausar_confirmacao
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def loop_prazo(driver: WebDriver) -> Dict[str, Any]:
    """Função wrapper que executa o fluxo completo de prazo (ciclo1 + ciclo2)"""
    try:
        import time
        # 1. Navegar para Painel Global 14 (Análise)
        url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
        if not pausar_confirmacao('LOOP/NAVEGAR_PAINEL14', f'Navegar para {url_lista}'):
            return {"sucesso": False, "erro": "Abortado pelo usuário em navegar painel 14"}
        logger.info(f'[LOOP_PRAZO] Navegando para Painel Global 14: {url_lista}')
        driver.get(url_lista)
        # Espera dinâmica: aguardar elemento chave do painel de atividades
        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Fase processual')]") )
            )
            logger.info('[LOOP_PRAZO] Elemento "Fase processual" presente - prosseguindo')
        except Exception:
            logger.info('[LOOP_PRAZO] Timeout aguardando elemento "Fase processual" - prosseguindo mesmo assim')

        # FASE 1: Loop para ciclo1 (Análise)
        logger.info("[LOOP_PRAZO] Fase 1: Processando processos no painel 14")
        while True:
            resultado_ciclo1 = ciclo1(driver)
            
            if resultado_ciclo1 == "no_more_processes":
                logger.info("[LOOP_PRAZO] Não há mais processos para processar no ciclo1.")
                break
            elif resultado_ciclo1 == "single_process":
                logger.info("[LOOP_PRAZO] Apenas 1 processo detectado - pulando batch")
                break
            elif resultado_ciclo1 == "complete_single_batch":
                logger.info("[LOOP_PRAZO] ✓ Lote único processado (<20 processos) - não repetir ciclo1")
                break
            elif resultado_ciclo1 is False:
                logger.error("[LOOP_PRAZO] Erro crítico no ciclo1.")
                return {"sucesso": False, "erro": "Falha em ciclo1"}
            elif resultado_ciclo1 in ["go_to_ciclo2", "marcar_todas_not_found_but_continue"]:
                break
            
            logger.info("[LOOP_PRAZO] Ciclo 1 concluído. Verificando se há mais...")
            time.sleep(2)
        
        # 2. Navegar para Painel Global 8 (Cumprimento de providências)
        url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
        if not pausar_confirmacao('LOOP/NAVEGAR_PAINEL8', f'Navegar para {url_painel8}'):
            return {"sucesso": False, "erro": "Abortado pelo usuário em navegar painel 8"}
        logger.info(f'[LOOP_PRAZO] Navegando para Painel Global 8: {url_painel8}')
        driver.get(url_painel8)
        time.sleep(3)
        
        # FASE 2: Ciclo 2
        logger.info("[LOOP_PRAZO] Fase 2: Executando ciclo 2")
        resultado_ciclo2 = ciclo2(driver)
        
        # FASE 3: Ciclo 3 (painel cumprimento providências - livres sem GIGS)
        logger.info("[LOOP_PRAZO] Fase 3: Executando ciclo 3")
        resultado_ciclo3 = ciclo3(driver)
        
        return {
            "sucesso": resultado_ciclo2 is True and resultado_ciclo3 is True,
            "ciclo1": "concluido",
            "ciclo2": resultado_ciclo2,
            "ciclo3": resultado_ciclo3
        }
    except Exception as e:
        logger.error(f'[LOOP_PRAZO] Erro no wrapper: {e}')
        return {"sucesso": False, "erro": str(e)}

# Alias para compatibilidade
main = loop_prazo
executar_loop_principal = loop_prazo

__all__ = [
    # Core utilities
    'normalizar_texto', 'gerar_regex_geral', 'parse_gigs_param',
    'carregar_progresso_p2b', 'salvar_progresso_p2b', 'marcar_processo_executado_p2b',
    'processo_ja_executado_p2b', 'RegraProcessamento', 'REGEX_PATTERNS',

    # Main functions
    'fluxo_pz', 'fluxo_prazo', 'loop_prazo', 'main', 'executar_loop_principal',
    'ciclo1', 'ciclo2', 'ciclo3',

    # Version info
    '__version__', '__author__'
]