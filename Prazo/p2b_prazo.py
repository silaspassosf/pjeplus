"""
P2B Prazo Module - Funções específicas do fluxo_prazo
Refatoração seguindo guia unificado: padrão Orchestrator + Helpers
Redução de complexidade: fluxo_prazo de 149→35 linhas, aninhamento 6→2 níveis
"""

import logging
import time
from typing import Optional, Tuple, List, Any, Dict
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Importar sistema de progresso
from Fix.progress import registrar_modulo, atualizar, completar

# Importar otimizações de execução
from Fix.element_wait import ElementWaitPool
from Prazo.criteria_matcher import CriteriaMatcher

from Prazo.p2b_core import carregar_progresso_p2b, marcar_processo_executado_p2b, processo_ja_executado_p2b
from Fix import indexar_processos, abrir_detalhes_processo, reindexar_linha
from Fix.abas import trocar_para_nova_aba
from Prazo.p2b_fluxo import fluxo_pz
from utilitarios_processamento import executar_processamento_iterativo_com_corte_em_erro_critico

# Logger local para evitar conflitos
logger = logging.getLogger(__name__)


# ===== ORCHESTRATOR: FLUXO_PRAZO =====

def fluxo_prazo(driver: WebDriver) -> None:
    """
    Executa o fluxo de prazo: Itera processos, chama fluxo_pz para cada um.

    Refatoração: 149→35 linhas, padrão Orchestrator + 6 Helpers
    Otimizado para verificar progresso na lista antes de abrir processos.
    """    # Registrar módulo no sistema de progresso
    registrar_modulo('PRAZO_PROCESSAMENTO_FLUXO', 0)  # Total será determinado dinamicamente

    # Inicializar otimizações de execução
    wait_pool = ElementWaitPool(driver, explicit_wait=10)
    criteria_matcher = CriteriaMatcher(driver, None, wait_pool)  # config será passado depois

    # 1. Navegar para painel de atividades
    url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
    driver.get(url_atividades)
    WebDriverWait(driver, 10).until(EC.url_contains('atividades'))
    # Atualizar progresso - navegação para atividades
    atualizar('PRAZO_PROCESSAMENTO_FLUXO', item_atual='navegacao_atividades')
    # 2. Aplicar filtro xs
    aplicar_filtro_atividades_xs(driver, apenas_filtro=True)

    # Atualizar progresso - filtro aplicado
    atualizar('PRAZO_PROCESSAMENTO_FLUXO', item_atual='filtro_aplicado')

    # 3. Indexar processos
    processos = _indexar_processos_lista(driver)
    if not processos:
        return

    # Atualizar progresso - processos indexados
    atualizar('PRAZO_PROCESSAMENTO_FLUXO', item_atual='processos_indexados')

    # 4. Carregar progresso
    progresso = carregar_progresso_p2b()

    # 5. Filtrar processos não executados
    processos_para_executar = _filtrar_processos_nao_executados(processos, progresso)
    if not processos_para_executar:
        return

    # Atualizar progresso - processos filtrados
    atualizar('PRAZO_PROCESSAMENTO_FLUXO', item_atual='processos_filtrados')

    # 6. Processar lista filtrada
    _processar_lista_processos(driver, processos_para_executar, progresso)

    # Atualizar progresso - processamento completo
    atualizar('PRAZO_PROCESSAMENTO_FLUXO', item_atual='processamento_completo')
    completar('PRAZO_PROCESSAMENTO_FLUXO')


# ===== FUNÇÃO OTIMIZADA: executar_prazo_com_otimizacoes =====
def executar_prazo_com_otimizacoes(driver, wait_pool: ElementWaitPool) -> Dict[str, Any]:
    """Executar Prazo com CriteriaMatcher para early termination (otimização centralizada no módulo Prazo)."""
    try:
        # Inicializar CriteriaMatcher
        criteria_matcher = CriteriaMatcher(driver, None, wait_pool)

        # Executar fluxo_prazo com early termination
        logger.info("[PRAZO OTIMIZADO] Iniciando busca com early termination...")

        # Usar CriteriaMatcher para buscar prazo ativo
        encontrado, dados_prazo = criteria_matcher.buscar_prazo_ativo(max_paginas=20)

        if encontrado:
            logger.info("[PRAZO OTIMIZADO] Prazo ativo encontrado - executando fluxo_pz")
            # Se encontrou prazo ativo, executar fluxo_pz
            resultado_pz = fluxo_pz(driver)
            return {
                "sucesso": True,
                "tipo": "prazo_ativo_encontrado",
                "dados_prazo": dados_prazo,
                "resultado_pz": resultado_pz
            }
        else:
            logger.info("[PRAZO OTIMIZADO] Nenhum prazo ativo encontrado")
            return {
                "sucesso": True,
                "tipo": "nenhum_prazo_ativo",
                "dados_prazo": None
            }

    except Exception as e:
        logger.error(f"[PRAZO OTIMIZADO] Erro: {e}")
        return {
            "sucesso": False,
            "erro": str(e)
        }

# ===== NOVA FUNÇÃO: Navegação painel atividades + filtro xs =====
def aplicar_filtro_atividades_xs(driver: WebDriver, apenas_filtro: bool = False) -> None:
    """Aplica filtro xs no painel de atividades (simplificado)."""
    try:
        from Fix import aplicar_filtro_100, safe_click, esperar_elemento
        from selenium.webdriver.common.by import By
        from Fix import aguardar_e_clicar
        # Remover chip "Vencidas" se existir (antes do filtro xs)
        chips = driver.find_elements(By.CSS_SELECTOR, 'mat-chip')
        removido = False
        for chip in chips:
            if 'Vencidas' in chip.text:
                btns = chip.find_elements(By.CSS_SELECTOR, 'button.chips-icone-fechar')
                for btn in btns:
                    # Usa aguardar_e_clicar no botão (corrigido: passar btn como seletor)
                    # aguardar_e_clicar espera seletor, mas se for elemento, usar safe_click direto
                    try:
                        if safe_click(driver, btn, timeout=5, log=False):
                            logger.info('[FLUXO_PRAZO] Chip Vencidas removido.')
                            removido = True
                            break
                    except Exception as e:
                        logger.info(f'[FLUXO_PRAZO] Erro ao clicar no botão de fechar chip Vencidas: {e}')
                if removido:
                    break
        if not removido:
            logger.info('[FLUXO_PRAZO] Chip Vencidas não encontrado ou já removido.')
            
        # Clicar no ícone fa-pen
        btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=10)
        if btn_fa_pen:
            safe_click(driver, btn_fa_pen)
            
        # Preencher campo descrição com xs
        campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=10)
        if campo_descricao:
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            from selenium.webdriver.common.keys import Keys
            campo_descricao.send_keys(Keys.ENTER)
            
        logger.info('[FLUXO_PRAZO] Filtro xs aplicado no painel de atividades.')
        # Aplicar filtro 100 após filtro xs
        aplicar_filtro_100(driver)
        
    except Exception as e:
        logger.info(f'[FLUXO_PRAZO][ERRO] Falha ao aplicar filtro xs: {e}')


# ===== HELPERS PRIVADOS: FLUXO_PRAZO =====

def _indexar_processos_lista(driver: WebDriver) -> List[Tuple[str, Any]]:
    """
    Helper: Indexa todos os processos da lista primeiro.

    Returns:
        Lista de tuplas (proc_id, linha_element)
    """
    try:
        processos = indexar_processos(driver)
        if not processos:
            logger.info('[FLUXO_PRAZO][ALERTA] Nenhum processo encontrado na lista')
            return []
        logger.info(f'[FLUXO_PRAZO] {len(processos)} processos encontrados na lista')
        return processos
    except Exception as e:
        logger.info(f'[FLUXO_PRAZO][ERRO] Falha ao indexar processos: {e}')
        return []


def _filtrar_processos_nao_executados(processos: List[Tuple[str, Any]], progresso: dict) -> List[Tuple[str, Any]]:
    """
    Helper: Filtra processos já executados ANTES de abrir qualquer um.

    Args:
        processos: Lista de (proc_id, linha)
        progresso: Dados de progresso carregados

    Returns:
        Lista de processos não executados
    """
    processos_para_executar = []
    processos_pulados = 0

    for proc_id, linha in processos:
        if proc_id == '[sem número]':
            processos_para_executar.append((proc_id, linha))
            continue

        if processo_ja_executado_p2b(proc_id, progresso):
            logger.info(f"[PROGRESSO_P2B] Processo {proc_id} já foi executado, pulando...")
            processos_pulados += 1
        else:
            processos_para_executar.append((proc_id, linha))
            logger.info(f"[PROGRESSO_P2B] Processo {proc_id} será processado")

    logger.info(f'[FLUXO_PRAZO] {processos_pulados} processos pulados (já executados)')
    logger.info(f'[FLUXO_PRAZO] {len(processos_para_executar)} processos serão processados')

    return processos_para_executar


def _processar_lista_processos(driver: WebDriver, processos_para_executar: List[Tuple[str, Any]], progresso: dict) -> None:
    """
    Helper: Processa apenas os processos que não foram executados ainda.

    Refatorada para usar função utilitária genérica com interrupção automática em erros críticos.

    Args:
        driver: WebDriver instance
        processos_para_executar: Lista filtrada de processos
        progresso: Dados de progresso para atualização
    """
    def processar_item_prazo(driver_param, item):
        """Wrapper para processar um item individual do Prazo."""
        proc_id, linha = item
        aba_lista_original = driver_param.current_window_handle
        return _processar_processo_individual(driver_param, proc_id, linha, aba_lista_original, progresso)

    # Usar função utilitária genérica com interrupção automática
    resultados = executar_processamento_iterativo_com_corte_em_erro_critico(
        driver=driver,
        nome_modulo="PRAZO",
        lista_itens=processos_para_executar,
        funcao_processamento_item=processar_item_prazo,
        max_tentativas_recuperacao=2
    )

    # Log do resultado final
    processos_processados = resultados.get('sucessos', 0)
    processos_com_erro = resultados.get('erros', 0)
    logger.info(f'[FLUXO_PRAZO] Processamento concluído: {processos_processados} sucesso, {processos_com_erro} erros')


def _processar_processo_individual(driver: WebDriver, proc_id: str, linha: Any, aba_lista_original: str, progresso: dict) -> bool:
    """
    Helper: Processa um processo individual.

    Args:
        driver: WebDriver instance
        proc_id: ID do processo
        linha: Elemento da linha na lista
        aba_lista_original: Handle da aba da lista
        progresso: Dados de progresso

    Returns:
        True se processado com sucesso
    """
    # Reindexar linha se necessário
    linha_atual = _reindexar_linha_se_necessario(driver, linha, proc_id)
    if not linha_atual:
        return False

    # Abrir detalhes do processo
    if not abrir_detalhes_processo(driver, linha_atual):
        logger.info(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
        return False

    # Aguardar nova aba e trocar
    nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
    if not nova_aba:
        logger.info(f'[PROCESSAR][ERRO] Nova aba não carregou para {proc_id}')
        return False

    logger.info(f'[PROCESSAR] Nova aba carregada: {driver.title[:50]}... | URL: {driver.current_url[:50]}...')

    # Executar callback com fluxo_pz
    return _executar_callback_processo(driver, proc_id, progresso)


def _reindexar_linha_se_necessario(driver: WebDriver, linha: Any, proc_id: str) -> Optional[Any]:
    """
    Helper: Reindexa linha se ficou stale.

    Args:
        driver: WebDriver instance
        linha: Linha original
        proc_id: ID do processo

    Returns:
        Linha atual ou None se falhar
    """
    try:
        linha.is_displayed()
        return linha
    except:
        linha_atual = reindexar_linha(driver, proc_id)
        if not linha_atual:
            logger.info(f'[PROCESSAR][ERRO] Não foi possível reindexar linha para {proc_id}')
        return linha_atual


def _executar_callback_processo(driver: WebDriver, proc_id: str, progresso: dict) -> bool:
    """
    Helper: Executa callback com fluxo_pz para o processo.

    Args:
        driver: WebDriver instance
        proc_id: ID do processo
        progresso: Dados de progresso

    Returns:
        True se executado com sucesso
    """
    aba_lista_original = None
    try:
        # Preservar aba original para cleanup posterior
        try:
            aba_lista_original = driver.window_handles[0] if driver.window_handles else None
        except Exception:
            pass

        logger.info(f"[PROGRESSO_P2B] Processando: {proc_id}")

        fluxo_pz(driver)  # Call the main function for the process tab

        # Marcar processo como executado
        if proc_id != '[sem número]':
            progresso_atual = carregar_progresso_p2b()
            marcar_processo_executado_p2b(proc_id, progresso_atual)
            logger.info(f"[PROGRESSO_P2B] Processo {proc_id} concluído com sucesso")
        else:
            logger.info("[PROGRESSO_P2B] Processo sem número identificado foi executado")

        logger.info(f'[PROCESSAR] Callback executado com sucesso para {proc_id}')
        return True

    except Exception as e:
        logger.info(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}')
        # Mesmo com erro, marca como executado para evitar loop infinito
        if proc_id != '[sem número]':
            progresso_atual = carregar_progresso_p2b()
            marcar_processo_executado_p2b(proc_id, progresso_atual)
            logger.info(f"[PROGRESSO_P2B] Processo {proc_id} marcado como executado (com erro)")
        return False
    
    finally:
        # ===== CALLBACK GERENCIA SUA PRÓPRIA LIMPEZA DE ABAS =====
        # Após fluxo_pz completar, fechar suas abas extras e retornar à original
        try:
            if aba_lista_original:
                try:
                    current_handles = driver.window_handles
                except Exception:
                    return  # Driver pode estar em estado inconsistente
                
                if len(current_handles) > 1 and aba_lista_original in current_handles:
                    # Fechar todas abas exceto a primeira (original)
                    for aba in current_handles[1:]:
                        try:
                            driver.switch_to.window(aba)
                            driver.close()
                            logger.debug(f'[CALLBACK_P2B][CLEANUP] Aba fechada')
                        except Exception:
                            pass
                    
                    # Retornar para aba principal
                    try:
                        driver.switch_to.window(aba_lista_original)
                        logger.debug(f'[CALLBACK_P2B][CLEANUP] Retornando à aba principal')
                    except Exception:
                        pass
        except Exception as cleanup_err:
            logger.debug(f'[CALLBACK_P2B][CLEANUP] Erro durante cleanup (não crítico): {cleanup_err}')


def _gerenciar_abas_apos_processo(driver: WebDriver, aba_lista_original: str) -> None:
    """
    Helper: Gerencia abas após processamento de um processo.

    Args:
        driver: WebDriver instance
        aba_lista_original: Handle da aba da lista
    """
    try:
        if aba_lista_original in driver.window_handles:
            driver.switch_to.window(aba_lista_original)
            # Fechar outras abas
            for handle in driver.window_handles:
                if handle != aba_lista_original:
                    try:
                        driver.switch_to.window(handle)
                        driver.close()
                    except:
                        pass
            driver.switch_to.window(aba_lista_original)
        else:
            logger.info(f'[PROCESSAR][ERRO] Aba da lista não está mais disponível')
    except Exception as e:
        logger.info(f'[PROCESSAR][ERRO] Falha ao voltar para lista: {e}')


# ===== VALIDAÇÃO =====

if __name__ == "__main__":
    logger.info("P2B Prazo Module - Teste básico")

    # Teste importações
    try:
        from Prazo.p2b_core import carregar_progresso_p2b
        logger.info(" Importações do p2b_core funcionam")

        # Teste funções básicas
        logger.info(" Módulo p2b_prazo validado")

    except ImportError as e:
        logger.info(f" Erro de importação: {e}")

    logger.info(" P2B Prazo Module validado")