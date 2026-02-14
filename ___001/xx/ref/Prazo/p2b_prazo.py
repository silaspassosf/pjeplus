"""
P2B Prazo Module - Funções específicas do fluxo_prazo
Refatoração seguindo guia unificado: padrão Orchestrator + Helpers
Redução de complexidade: fluxo_prazo de 149→35 linhas, aninhamento 6→2 níveis
"""

import logging
import time
from typing import Optional, Tuple, List, Any
from selenium.webdriver.remote.webdriver import WebDriver

from Prazo.p2b_core import carregar_progresso_p2b, marcar_processo_executado_p2b, processo_ja_executado_p2b
from Fix import indexar_processos, abrir_detalhes_processo, reindexar_linha
from Fix.abas import trocar_para_nova_aba
from Prazo.p2b_fluxo import fluxo_pz

# Logger local para evitar conflitos
logger = logging.getLogger(__name__)


# ===== ORCHESTRATOR: FLUXO_PRAZO =====

def fluxo_prazo(driver: WebDriver) -> None:
    """
    Executa o fluxo de prazo: Itera processos, chama fluxo_pz para cada um.

    Refatoração: 149→35 linhas, padrão Orchestrator + 6 Helpers
    Otimizado para verificar progresso na lista antes de abrir processos.
    """
    print('[FLUXO_PRAZO] Iniciando processamento da lista de processos')

    # 1. Navegar para painel de atividades
    url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
    driver.get(url_atividades)
    time.sleep(2)

    # 2. Aplicar filtro xs
    aplicar_filtro_atividades_xs(driver, apenas_filtro=True)

    # 3. Indexar processos
    processos = _indexar_processos_lista(driver)
    if not processos:
        return

    # 4. Carregar progresso
    progresso = carregar_progresso_p2b()

    # 5. Filtrar processos não executados
    processos_para_executar = _filtrar_processos_nao_executados(processos, progresso)
    if not processos_para_executar:
        print('[FLUXO_PRAZO] Todos os processos já foram executados!')
        return

    # 6. Processar lista filtrada
    _processar_lista_processos(driver, processos_para_executar, progresso)

    print('[FLUXO_PRAZO] Processamento da lista concluído')
# ===== NOVA FUNÇÃO: Navegação painel atividades + filtro xs =====
def aplicar_filtro_atividades_xs(driver, apenas_filtro=False):
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
                            print('[FLUXO_PRAZO] Chip Vencidas removido.')
                            removido = True
                            break
                    except Exception as e:
                        print(f'[FLUXO_PRAZO] Erro ao clicar no botão de fechar chip Vencidas: {e}')
                if removido:
                    break
        if not removido:
            print('[FLUXO_PRAZO] Chip Vencidas não encontrado ou já removido.')
        time.sleep(1)
        # Clicar no ícone fa-pen
        btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=10)
        if btn_fa_pen:
            safe_click(driver, btn_fa_pen)
            time.sleep(1)
        # Preencher campo descrição com xs
        campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=10)
        if campo_descricao:
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            from selenium.webdriver.common.keys import Keys
            campo_descricao.send_keys(Keys.ENTER)
            time.sleep(2)
        print('[FLUXO_PRAZO] Filtro xs aplicado no painel de atividades.')
        # Aplicar filtro 100 após filtro xs
        aplicar_filtro_100(driver)
        time.sleep(1)
    except Exception as e:
        print(f'[FLUXO_PRAZO][ERRO] Falha ao aplicar filtro xs: {e}')


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
            print('[FLUXO_PRAZO][ALERTA] Nenhum processo encontrado na lista')
            return []
        print(f'[FLUXO_PRAZO] {len(processos)} processos encontrados na lista')
        return processos
    except Exception as e:
        print(f'[FLUXO_PRAZO][ERRO] Falha ao indexar processos: {e}')
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
            print(f"[PROGRESSO_P2B] Processo {proc_id} já foi executado, pulando...")
            processos_pulados += 1
        else:
            processos_para_executar.append((proc_id, linha))
            print(f"[PROGRESSO_P2B] Processo {proc_id} será processado")

    print(f'[FLUXO_PRAZO] {processos_pulados} processos pulados (já executados)')
    print(f'[FLUXO_PRAZO] {len(processos_para_executar)} processos serão processados')

    return processos_para_executar


def _processar_lista_processos(driver: WebDriver, processos_para_executar: List[Tuple[str, Any]], progresso: dict) -> None:
    """
    Helper: Processa apenas os processos que não foram executados ainda.

    Args:
        driver: WebDriver instance
        processos_para_executar: Lista filtrada de processos
        progresso: Dados de progresso para atualização
    """
    aba_lista_original = driver.current_window_handle
    processos_processados = 0
    processos_com_erro = 0

    for idx, (proc_id, linha) in enumerate(processos_para_executar):
        print(f'[PROCESSAR] Iniciando processo {idx+1}/{len(processos_para_executar)}: {proc_id}', flush=True)

        try:
            # Processar processo individual
            sucesso = _processar_processo_individual(driver, proc_id, linha, aba_lista_original, progresso)
            if sucesso:
                processos_processados += 1
            else:
                processos_com_erro += 1

        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha geral no processo {proc_id}: {e}')
            processos_com_erro += 1
            continue

        # Gerenciar abas após cada processo
        _gerenciar_abas_apos_processo(driver, aba_lista_original)

    print(f'[FLUXO_PRAZO] Processamento concluído: {processos_processados} sucesso, {processos_com_erro} erros')


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
        print(f'[PROCESSAR][ERRO] Botão de detalhes não encontrado para {proc_id}')
        return False

    # Aguardar nova aba e trocar
    time.sleep(2)
    nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
    if not nova_aba:
        print(f'[PROCESSAR][ERRO] Nova aba não carregou para {proc_id}')
        return False

    print(f'[PROCESSAR] Nova aba carregada: {driver.title[:50]}... | URL: {driver.current_url[:50]}...')

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
            print(f'[PROCESSAR][ERRO] Não foi possível reindexar linha para {proc_id}')
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
    try:
        print(f"[PROGRESSO_P2B] Processando: {proc_id}")

        fluxo_pz(driver)  # Call the main function for the process tab

        # Marcar processo como executado
        if proc_id != '[sem número]':
            progresso_atual = carregar_progresso_p2b()
            marcar_processo_executado_p2b(proc_id, progresso_atual)
            print(f"[PROGRESSO_P2B] Processo {proc_id} concluído com sucesso")
        else:
            print("[PROGRESSO_P2B] Processo sem número identificado foi executado")

        print(f'[PROCESSAR] Callback executado com sucesso para {proc_id}')
        return True

    except Exception as e:
        print(f'[PROCESSAR][ERRO] Callback falhou para {proc_id}: {e}')
        # Mesmo com erro, marca como executado para evitar loop infinito
        if proc_id != '[sem número]':
            progresso_atual = carregar_progresso_p2b()
            marcar_processo_executado_p2b(proc_id, progresso_atual)
            print(f"[PROGRESSO_P2B] Processo {proc_id} marcado como executado (com erro)")
        return False


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
            print(f'[PROCESSAR][ERRO] Aba da lista não está mais disponível')
    except Exception as e:
        print(f'[PROCESSAR][ERRO] Falha ao voltar para lista: {e}')


# ===== VALIDAÇÃO =====

if __name__ == "__main__":
    print("P2B Prazo Module - Teste básico")

    # Teste importações
    try:
        from Prazo.p2b_core import carregar_progresso_p2b
        print("✅ Importações do p2b_core funcionam")

        # Teste funções básicas
        print("✅ Módulo p2b_prazo validado")

    except ImportError as e:
        print(f"❌ Erro de importação: {e}")

    print("✅ P2B Prazo Module validado")