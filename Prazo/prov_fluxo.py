import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado
)
from Fix.variaveis import PjeApiClient, buscar_atividade_gigs_por_observacao, session_from_driver
from Fix.core import finalizar_driver

from Prazo.loop import (
    _ciclo2_aplicar_filtros,
    _extrair_numero_processo_da_linha,
    _selecionar_processos_por_gigs_aj_jt,
    _ciclo2_processar_livres,
    _ciclo2_criar_atividade_xs
)

from .prov_config import TIPO_EXECUCAO, URL_PAINEL
from .prov_driver import criar_e_logar_driver

logger = logging.getLogger(__name__)


# ============================================================================
# FLUXO REUTILIZÁVEL (SEM DRIVER/LOGIN) - PARA INTEGRAÇÃO EM loop.py
# ============================================================================

def fluxo_prov(driver: WebDriver) -> Dict[str, Any]:
    """
    Fluxo completo de processamento PROV (sem criar driver/login).
    Pode ser integrado diretamente em loop.py após loop_prazo.
    
    Executa:
    1. Carrega progresso permanente (prov.json)
    2. Navega + aplica filtros
    3. Seleciona GIGS + livres
    4. Aplica XS e registra progresso
    
    Args:
        driver: WebDriver já logado
        
    Returns:
        Dict com resultado completo:
        {
            'sucesso': bool,
            'selecao': {'gigs': int, 'livres': int, 'total': int, 'ja_processados': int},
            'processamento': {'processados': int, 'duplicados': int, 'erros': int},
            'tempo_total': float,
            'progresso_atual': int  # Total processado no histórico
        }
    """
    inicio = datetime.now()
    resultado = {
        'sucesso': False,
        'selecao': {'gigs': 0, 'livres': 0, 'total': 0, 'ja_processados': 0},
        'processamento': {'processados': 0, 'duplicados': 0, 'erros': 0},
        'tempo_total': 0,
        'progresso_atual': 0
    }
    
    try:
        logger.info("\n[PROV_FLUXO]  Iniciando fluxo PROV (integrado)...")
        
        # Carregar progresso
        logger.info("[PROV_FLUXO]  Carregando progresso permanente...")
        progresso = carregar_progresso_unificado(TIPO_EXECUCAO)
        
        # Navegar + filtros
        logger.info("[PROV_FLUXO]  Navegando + aplicando filtros...")
        if not navegacao_prov(driver):
            logger.info("[PROV_FLUXO]  Aviso na navegação, continuando...")
        
        # Seleção
        logger.info("[PROV_FLUXO]  Selecionando processos...")
        resultado['selecao'] = selecionar_e_processar(driver, progresso)
        
        # Aplicar XS
        logger.info("[PROV_FLUXO]  Aplicando XS e registrando...")
        resultado['processamento'] = aplicar_xs_e_registrar(driver, progresso)
        
        # Atualizar progresso final
        resultado['progresso_atual'] = len(progresso.get('processos_executados', []))
        resultado['sucesso'] = True
        
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_total'] = tempo_total
        
        logger.info(f"[PROV_FLUXO]  Fluxo concluído em {tempo_total:.2f}s")
        return resultado
        
    except Exception as e:
        logger.info(f"[PROV_FLUXO]  Erro no fluxo: {e}")
        import traceback
        logger.exception("Erro detectado")
        resultado['sucesso'] = False
        return resultado


# ============================================================================
# FUNÇÕES DE ORQUESTRAÇÃO
# ============================================================================

def navegacao_prov(driver: WebDriver) -> bool:
    """
    Navega para o painel de processos e aplica APENAS filtro 100 (sem processos).
    NÃO aplica filtros de fases ou tarefas - isso é feito em loop.py.
    
    Args:
        driver: WebDriver Selenium
        
    Returns:
        True se navegação e filtro aplicados com sucesso
    """
    try:
        logger.info("\n[PROV]  Navegando para painel de processos...")
        driver.get(URL_PAINEL)
        time.sleep(3)
        
        logger.info("[PROV]  Aplicando APENAS filtro 100 (sem processos)...")
        from Fix.core import aplicar_filtro_100
        
        try:
            aplicar_filtro_100(driver)
            logger.info("[PROV]  Filtro 100 aplicado com sucesso")
        except Exception as e:
            logger.info(f"[PROV]  Erro ao aplicar filtro 100: {e}")
            return False
        
        time.sleep(2)
        logger.info("[PROV]  Navegação e filtro concluídos")
        return True
        
    except Exception as e:
        logger.info(f"[PROV]  Erro na navegação: {e}")
        import traceback
        logger.exception("Erro detectado")
        return False


def selecionar_e_processar(driver: WebDriver, progresso: Dict[str, Any]) -> Dict[str, int]:
    """
    Seleciona processos via GIGS (AJ-JT/requisição) e livres.
    Verifica progresso para evitar duplicação.
    
    Args:
        driver: WebDriver Selenium
        progresso: Dict com histórico de processos já processados
        
    Returns:
        Dict com contadores: {'gigs': count, 'livres': count, 'total': count, 'ja_processados': count}
    """
    resultado = {
        'gigs': 0,
        'livres': 0,
        'total': 0,
        'ja_processados': 0
    }
    
    try:
        logger.info("\n[PROV]  Iniciando seleção de processos...")
        
        # Criar cliente GIGS
        logger.info("[PROV]  Inicializando cliente GIGS...")
        client = None
        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            logger.info("[PROV]  Cliente GIGS criado com sucesso")
        except Exception as e:
            logger.info(f"[PROV]  Erro ao criar cliente GIGS: {e}")
            import traceback
            logger.exception("Erro detectado")
            client = None
        
        # Selecionar GIGS (AJ-JT - Verificar Pagamento)
        if client:
            logger.info("[PROV]  Selecionando processos com GIGS (AJ-JT - Verificar Pagamento)...")
            try:
                count_gigs = _selecionar_processos_por_gigs_aj_jt(driver, client)
                resultado['gigs'] = count_gigs
                logger.info(f"[PROV]  {count_gigs} processos selecionados via GIGS")
            except Exception as e:
                logger.info(f"[PROV]  Erro ao selecionar GIGS: {e}")
                resultado['gigs'] = 0
        else:
            logger.info("[PROV] ⏭  Pulando seleção GIGS (cliente não disponível)")
            resultado['gigs'] = 0
        
        time.sleep(2)
        
        # Selecionar livres
        logger.info("[PROV]  Selecionando processos livres...")
        try:
            count_livres = _ciclo2_processar_livres(driver, client if client else None)
            resultado['livres'] = count_livres
            logger.info(f"[PROV]  {count_livres} processos livres selecionados")
        except Exception as e:
            logger.info(f"[PROV]  Erro ao selecionar livres: {e}")
            resultado['livres'] = 0
        
        resultado['total'] = resultado['gigs'] + resultado['livres']
        
        # Contar já processados
        ja_processados = len(progresso.get('processos_executados', []))
        resultado['ja_processados'] = ja_processados
        
        logger.info(f"\n[PROV]  Resumo de Seleção:")
        logger.info(f"   GIGS (AJ-JT - Verificar Pagamento): {resultado['gigs']}")
        logger.info(f"   Livres: {resultado['livres']}")
        logger.info(f"   Total a processar: {resultado['total']}")
        logger.info(f"   Já processados antes: {ja_processados}")
        
        return resultado
        
    except Exception as e:
        logger.info(f"[PROV]  Erro na seleção de processos: {e}")
        import traceback
        logger.exception("Erro detectado")
        return resultado


def aplicar_xs_e_registrar(driver: WebDriver, progresso: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica atividade XS aos processos selecionados e registra no progresso.
    
    Args:
        driver: WebDriver Selenium
        progresso: Dict com histórico (será atualizado)
        
    Returns:
        Dict com resultado: {'processados': count, 'erros': count, 'duplicados': count}
    """
    resultado = {
        'processados': 0,
        'erros': 0,
        'duplicados': 0
    }
    
    try:
        logger.info("\n[PROV]  Registrando progresso dos processos XS...")
        
        # NOTA: A atividade XS já foi criada em _ciclo2_processar_livres()
        # Aqui apenas registramos no histórico permanente
        
        time.sleep(1)
        
        # Obter processos selecionados (via tabela)
        logger.info("[PROV]  Extraindo números dos processos selecionados...")
        try:
            linhas_selecionadas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag.selecionado')
            if not linhas_selecionadas:
                # Fallback: tentar encontrar checkboxes marcados
                linhas_selecionadas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
            
            processos_para_registrar = []
            for linha in linhas_selecionadas:
                try:
                    numero_processo = _extrair_numero_processo_da_linha(linha)
                    if numero_processo:
                        processos_para_registrar.append(numero_processo)
                except:
                    continue
            
            logger.info(f"[PROV]  Extraídos {len(processos_para_registrar)} números de processo")
            
        except Exception as e:
            logger.info(f"[PROV]  Erro ao extrair processos selecionados: {e}")
            processos_para_registrar = []
        
        # Registrar cada processo no progresso
        logger.info("[PROV]  Registrando processos em prov.json...")
        for numero_processo in processos_para_registrar:
            try:
                # Verificar se já foi processado
                if numero_processo in progresso.get('processos_executados', []):
                    logger.info(f"[PROV] ⏭  Processo {numero_processo} já estava registrado, pulando")
                    resultado['duplicados'] += 1
                    continue
                
                # Marcar como executado
                marcar_processo_executado_unificado(
                    tipo_execucao=TIPO_EXECUCAO,
                    numero_processo=numero_processo,
                    progresso=progresso,
                    sucesso=True
                )
                
                # Salvar imediatamente (segurança contra crash mid-execution)
                salvar_progresso_unificado(TIPO_EXECUCAO, progresso)
                resultado['processados'] += 1
                
            except Exception as e:
                logger.info(f"[PROV]  Erro ao registrar {numero_processo}: {e}")
                resultado['erros'] += 1
        
        logger.info(f"\n[PROV]  Resumo de Processamento:")
        logger.info(f"   Processados: {resultado['processados']}")
        logger.info(f"   Duplicados (já processados): {resultado['duplicados']}")
        logger.info(f"   Erros: {resultado['erros']}")
        
        return resultado
        
    except Exception as e:
        logger.info(f"[PROV]  Erro ao aplicar XS: {e}")
        import traceback
        logger.exception("Erro detectado")
        return resultado


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal de orquestração"""
    
    driver = None
    
    try:
        
        # ===== INICIALIZAÇÃO =====
        
        # Carregar progresso
        progresso = carregar_progresso_unificado(TIPO_EXECUCAO)
        
        # Criar driver
        driver = criar_e_logar_driver()
        if not driver:
            return False
        
        # ===== NAVEGAÇÃO =====
        
        if not navegacao_prov(driver):
            logger.error("[PROV]  Erro na navegação, mas continuando...")
        
        # ===== SELEÇÃO =====
        
        resultado_selecao = selecionar_e_processar(driver, progresso)
        
        # ===== APLICAÇÃO XS =====
        
        resultado_xs = aplicar_xs_e_registrar(driver, progresso)
        
        # ===== RELATÓRIO FINAL =====
        logger.error(f"   Erros: {resultado_xs['erros']}")
        
        return True
        
    except KeyboardInterrupt:
        logger.error("\n Interrompido pelo usuário (Ctrl+C)")
        return False
    except Exception as e:
        logger.error(f"\n Erro fatal: {e}")
        import traceback
        logger.exception("Erro detectado")
        return False
    
    finally:
        if driver:
            finalizar_driver(driver)


def fluxo_prov_integrado(driver: WebDriver) -> bool:
    """
    Fluxo final de PROV para integração em loop.py.
    
    Executa:
    1. Navegação para painel de cumprimento de providências (painel global 6)
    2. Aplicar filtro 100 (sem processos)
    3. Selecionar processos livres
    4. Aplicar atividade XS uma única vez
    
    Args:
        driver: WebDriver já logado
        
    Returns:
        True se sucesso, False se falha crítica
    """
    try:
        
        # 1. Navegação
        from Prazo.prov import URL_PAINEL
        driver.get(URL_PAINEL)
        time.sleep(3)
        
        # 2. Aplicar filtro 100
        try:
            from Fix.core import aplicar_filtro_100
            aplicar_filtro_100(driver)
        except Exception as e:
            logger.error(f"[PROV_INTEGRADO]  Erro ao aplicar filtro 100: {e}")
            return False
        
        time.sleep(2)
        
        # 3. Selecionar livres
        from Prazo.loop import SCRIPT_SELECAO_LIVRES
        livres_selecionados = driver.execute_script(SCRIPT_SELECAO_LIVRES)
        
        # 4. Aplicar XS se houver processos
        if livres_selecionados > 0:
            from Prazo.loop import _ciclo2_criar_atividade_xs
            _ciclo2_criar_atividade_xs(driver)
        return True
        
    except Exception as e:
        logger.error(f"[PROV_INTEGRADO]  Erro no fluxo: {e}")
        import traceback
        logger.exception("Erro detectado")
        return False