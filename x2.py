"""
x.py - Orquestrador Unificado PJEPlus (100% STANDALONE)
=========================================================
Consolidao completa e independente de 1.py, 1b.py, 2.py, 2b.py.
NO depende de nenhum dos scripts originais.

Menu 1: Selecionar Ambiente/Driver
  - A: PC + Visvel (1.py)
  - B: PC + Headless (1b.py)
  - C: VT + Visvel (2.py)
  - D: VT + Headless (2b.py)

Menu 2: Selecionar Fluxo de Execuo
    - A: Bloco Completo (Mandado + Prazo + PEC)
    - B: Mandado Isolado
    - C: Prazo Isolado (loop + p2b)
    - D: P2B Isolado
    - E: PEC Isolado

Autor: Sistema PJEPlus
Data: 04/12/2025
"""

import sys
import time
import logging
import os
from dotenv import load_dotenv; load_dotenv()
from datetime import datetime
_last_acesso_negado_log = 0.0
_acesso_negado_log_thresh = 30.0  # seconds

from typing import Dict, Any, Optional, Tuple
from enum import Enum

# Imports dos mdulos refatorados
from Fix.drivers import criar_driver_PC, criar_driver_VT, finalizar_driver as finalizar_driver_fix, _matar_zumbis_geckodriver
from Fix.utils import login_cpf
from Mandado.core import navegacao as mandado_navegacao, iniciar_fluxo_robusto as mandado_fluxo
from Prazo import loop_prazo
from Prazo.p2b_fluxo import fluxo_pz
from Prazo.p2b_prazo import fluxo_prazo as fluxo_prazo_p2b
from Prazo.p2b_prazo import executar_prazo_com_otimizacoes
from PEC.processamento import executar_fluxo_novo as pec_fluxo
# Otimizações de execução integradas
from Fix.element_wait import ElementWaitPool
from Fix.session_pool import SessionPool
from Prazo.criteria_matcher import CriteriaMatcher
# ============================================================================
# CONFIGURAES GLOBAIS
# ============================================================================

logger = logging.getLogger(__name__)

# Diretrio de logs
LOG_DIR = "logs_execucao"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')


class DriverType(Enum):
    """Tipos de drivers suportados"""
    PC_VISIBLE = "pc_visible"
    PC_HEADLESS = "pc_headless"
    VT_VISIBLE = "vt_visible"
    VT_HEADLESS = "vt_headless"


# ============================================================================
# CAPTURA DE PRINTS (TEEOUTPUT)
# ============================================================================

class TeeOutput:
    """Captura stdout/stderr para arquivo e console"""
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log_file = open(file_path, 'a', encoding='utf-8')
        
    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
        
    def close(self):
        self.log_file.close()
        sys.stdout = self.terminal


# ============================================================================
# DRIVERS - PC
# ============================================================================

def criar_driver_pc(headless=False):
    """
    Cria driver Firefox para PC (padro) usando o mdulo refatorado Fix.drivers.
    """
    try:
        driver = criar_driver_PC(headless=headless)
        if not headless and driver:
            try:
                driver.maximize_window()
            except Exception:
                pass
        return driver
    except Exception as e:
        logger.error(f"[DRIVER_PC]  Erro ao criar driver: {e}")
        return None


# ============================================================================
# DRIVERS - VT (Mquina Especfica)
# ============================================================================

def criar_driver_vt(headless=False):
    """
    Cria driver Firefox para VT (mquina especfica) usando Fix.drivers.
    """
    try:
        driver = criar_driver_VT(headless=headless)
        if not headless and driver:
            try:
                driver.maximize_window()
            except Exception:
                pass
        return driver
    except Exception as e:
        logger.error(f"[DRIVER_VT]  Erro ao criar driver: {e}")
        return None


# ============================================================================
# CRIAR E LOGAR DRIVER
# ============================================================================

def criar_e_logar_driver(driver_type: DriverType) -> Optional[Any]:
    """Cria driver apropriado e faz login"""
    
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]
    
    logger.info(f"\n Criando driver: {driver_type.value}")
    
    try:
        # Criar driver
        if vt_mode:
            driver = criar_driver_vt(headless=headless)
        else:
            driver = criar_driver_pc(headless=headless)
        
        if not driver:
            logger.info(" Falha ao criar driver")
            return None
        
        # Login
        logger.info(" Fazendo login...")
        if not login_cpf(driver):
            logger.info(" Falha no login")
            finalizar_driver_fix(driver)
            return None
        
        logger.info(" Driver criado e logado com sucesso")
        return driver
        
    except Exception as e:
        logger.info(f" Erro ao criar driver: {e}")
        import traceback
        logger.exception("Erro detectado")
        return None


# ============================================================================
# VERIFICAÇÃO DE ACESSO NEGADO - CENTRALIZADA
# ============================================================================

def verificar_acesso_negado(driver, contexto: str = "operação") -> None:
    """
    Verifica se o driver está em página de acesso negado.
    Se detectado, lança exceção para forçar reinício do driver.

    Também trata erros de conexão com o WebDriver (ex.: "Tried to run command without establishing a connection")
    como condição de reinício para garantir recuperação automática.

    Args:
        driver: Instância do WebDriver
        contexto: Nome da operação/módulo para logging

    Raises:
        Exception: Com prefixo RESTART_* para forçar reinício
    """
    try:
        # Acessar driver.current_url pode falhar se o driver estiver desconectado
        try:
            url_atual = driver.current_url
        except Exception as _e:
            # Tratar falha de conexão do WebDriver como motivo para reiniciar
            msg = f"Falha ao obter URL do driver: {_e}"
            logger.warning(f"ACESSO_NEGADO/DRIVER_DISCONNECT detectado em [{contexto}]: {_e}")
            raise Exception(f"RESTART_DRIVER: {msg}")

        # Verificar se é acesso negado
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
            mensagem = f"ACESSO_NEGADO detectado em [{contexto}] - URL: {url_atual}"

            # Rate-limited logging to avoid spamming the logs on bulk failures
            try:
                now = time.time()
                global _last_acesso_negado_log
                if now - _last_acesso_negado_log > _acesso_negado_log_thresh:
                    logger.warning(mensagem)
                    logger.warning("Lançando exceção para reiniciar driver...")
                    _last_acesso_negado_log = now
                else:
                    # Detailed logging suppressed; emit debug-level short marker
                    logger.debug(f"ACESSO_NEGADO (suprimido) em [{contexto}]")
            except Exception:
                # Fallback: always log minimally
                logger.warning(mensagem)

            # Lançar exceção para forçar reinício
            raise Exception(f"RESTART_DRIVER: {mensagem}")

    except Exception as e:
        # Se a exceção já é de RESTART, propagar
        if "RESTART_" in str(e):
            raise
        # Outros erros na verificação, ignorar
        pass


# ============================================================================
# FUNES DE EXECUO
# ============================================================================

def normalizar_resultado(resultado: Any) -> Dict[str, Any]:
    """Normaliza retorno para dict padro"""
    if isinstance(resultado, dict):
        return resultado
    if isinstance(resultado, bool):
        return {"sucesso": resultado, "status": "OK" if resultado else "ERRO"}
    if resultado is None:
        return {"sucesso": False, "status": "ERRO", "erro": "Mdulo retornou None"}
    return {"sucesso": False, "status": "ERRO", "erro": str(resultado)}


def resetar_driver(driver) -> bool:
    """Reseta driver entre mdulos"""
    try:
        logger.info(" Resetando driver...")
        
        # Fechar abas extras
        abas = driver.window_handles
        if len(abas) > 1:
            for aba in abas[1:]:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except:
                    pass
            driver.switch_to.window(abas[0])
        
        # Resetar zoom
        try:
            driver.execute_script("document.body.style.zoom='100%'")
        except Exception:
            pass

        # Limpar cookies para evitar sessão suja e navegar para página inicial
        try:
            driver.delete_all_cookies()
        except Exception:
            pass

        # Limpar storage (tokens SPA que persistem além dos cookies)
        try:
            driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception:
            pass

        # Navegar para página inicial
        try:
            driver.get("https://pje.trt2.jus.br/pjekz/")
        except Exception:
            pass
        time.sleep(2)

        # Tentar re-login automático (apenas se função de login estiver disponível)
        try:
            from Fix.utils import login_cpf
            # Fazer até 3 tentativas de login com backoff (mais resiliente)
            logged = False
            for attempt in range(3):
                try:
                    if login_cpf(driver, aguardar_url_final=True):
                        logged = True
                        break
                except Exception:
                    pass
                # backoff crescente: 1.0s, 2.5s, 4.0s
                time.sleep(1.0 + attempt * 1.5)

            if logged:
                logger.info(" Driver resetado e re-login efetuado com sucesso")
            else:
                logger.warning(" Driver resetado, mas re-login automático falhou (pode causar ACESSO_NEGADO)")
        except Exception as e:
            logger.warning(f" Reset do driver concluído (re-login não executado): {e}")

        return True
        
    except Exception as e:
        logger.info(f" Erro ao resetar driver: {e}")
        return False


def executar_com_recuperacao(driver, nome_fluxo: str, funcao_execucao, max_tentativas: int = 2) -> Dict[str, Any]:
    """Executa um fluxo com recuperação global de ACESSO_NEGADO.

    Se detectar RESTART_DRIVER, reseta o driver e reexecuta apenas este fluxo.
    """
    tentativa = 0
    while tentativa < max_tentativas:
        try:
            return funcao_execucao(driver)
        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                tentativa += 1
                logger.info(f"[{nome_fluxo}]  ACESSO_NEGADO - resetando driver (tentativa {tentativa}/{max_tentativas})")
                # Reset driver and apply exponential backoff before retry
                resetar_driver(driver)
                backoff = min(8, 2 ** tentativa)
                logger.info(f"[{nome_fluxo}]  Aguardando backoff de {backoff}s antes de nova tentativa")
                time.sleep(backoff)
                continue
            raise
    return {"sucesso": False, "erro": f"ACESSO_NEGADO persistente em {nome_fluxo}"}


def executar_processamento_iterativo_com_corte_em_erro_critico(
    driver,
    nome_modulo: str,
    lista_itens,
    funcao_processamento_item,
    max_tentativas_recuperacao: int = 2
) -> Dict[str, Any]:
    """
    Executa processamento iterativo com interrupção automática em erros críticos.

    Esta função padroniza o tratamento de erros em todos os módulos que fazem
    processamento em lote, evitando poluição do log com mensagens repetidas.

    Args:
        driver: WebDriver instance
        nome_modulo: Nome do módulo para logging (ex: "DOM", "P2B", "MANDADO")
        lista_itens: Lista de itens a processar (pode ser dict ou list)
        funcao_processamento_item: Função que processa um item individual
        max_tentativas_recuperacao: Máximo de tentativas para recuperação de acesso negado

    Returns:
        Dict com resultados: {"processados": int, "erros": int, "interrompido_por_erro_critico": bool}

    Exemplo de uso:
        def processar_um_processo(driver, proc_id, linha):
            # lógica específica do módulo
            return True

        resultados = executar_processamento_iterativo_com_corte_em_erro_critico(
            driver=driver,
            nome_modulo="DOM",
            lista_itens=processos_dict,
            funcao_processamento_item=lambda driver, item: processar_um_processo(driver, item['id'], item['linha'])
        )
    """
    processados = 0
    erros = 0
    interrompido_por_erro_critico = False

    logger.info(f'[{nome_modulo}] Iniciando processamento de {len(lista_itens)} itens')

    for idx, item in enumerate(lista_itens):
        # Determinar ID do item para logging
        if isinstance(item, dict) and 'id' in item:
            item_id = item['id']
        elif isinstance(item, tuple) and len(item) >= 1:
            item_id = str(item[0])  # Assume que primeiro elemento é ID
        else:
            item_id = f"item_{idx+1}"

        logger.info(f'[{nome_modulo}] Processando {idx+1}/{len(lista_itens)}: {item_id}')

        # Função wrapper para executar_com_recuperacao
        def processar_item_com_recuperacao(driver_param):
            return funcao_processamento_item(driver_param, item)

        try:
            resultado = executar_com_recuperacao(
                driver,
                f"{nome_modulo}_{item_id}",
                processar_item_com_recuperacao,
                max_tentativas=max_tentativas_recuperacao
            )

            if resultado:
                processados += 1
                logger.info(f'[{nome_modulo}] Item {item_id} processado com sucesso')
            else:
                erros += 1
                logger.error(f'[{nome_modulo}] Falha no processamento de {item_id}')

        except Exception as e:
            erros += 1
            error_msg = str(e)
            logger.error(f'[{nome_modulo}] Erro geral no processamento de {item_id}: {error_msg}')

            # DETECÇÃO DE ERROS CRÍTICOS - Interromper processamento para evitar poluição do log
            erros_criticos = [
                "takes 0 positional arguments but 1 was given",  # Erro de assinatura de função
                "RESTART_DRIVER",  # Driver restart forçado
                "Unable to locate element",  # Elemento não encontrado (estrutura mudou)
                "SessionNotCreatedException",  # Sessão do driver inválida
                "InvalidSessionIdException",  # Driver quebrado ou fechado
                "invalid session id",         # Variação do erro de sessão
                "Tried to run command without establishing a connection", # Driver desconectado
                "Failed to decode response from marionette", # Erro crítico do Gecko
            ]

            if any(critico in error_msg for critico in erros_criticos):
                logger.error(f'[{nome_modulo}] ERRO CRÍTICO detectado - interrompendo processamento para evitar poluição do log')
                logger.error(f'[{nome_modulo}] Último erro crítico: {error_msg}')
                interrompido_por_erro_critico = True
                break

            continue

    logger.info(f'[{nome_modulo}] Processamento concluído: {processados} sucesso, {erros} erros')
    if interrompido_por_erro_critico:
        logger.warning(f'[{nome_modulo}] Processamento interrompido por erro crítico - verifique e corrija antes de continuar')

    return {
        "processados": processados,
        "erros": erros,
        "interrompido_por_erro_critico": interrompido_por_erro_critico,
        "total_itens": len(lista_itens)
    }


def executar_bloco_completo(driver, session_pool: SessionPool, session_id: str, wait_pool: ElementWaitPool) -> Dict[str, Any]:
    """Bloco Completo: Mandado → Prazo → PEC com otimizações integradas"""
    resultados = {
        "mandado": None,
        "prazo": None,
        "pec": None,
        "sucesso_geral": False
    }

    try:
        pass
        pass
        pass

        # 1. MANDADO (primeiro módulo)
        # Mandado deve executar no driver ativo (não forçar restauração da sessão aqui)
        # usar o driver atual para garantir a navegação limpa executada por `mandado_navegacao`
        driver_mandado = driver
        resultados["mandado"] = executar_mandado(driver_mandado)

        # Reutilizar sessão para PRAZO (sem reset/time.sleep)
        driver_prazo = session_pool.reutilizar_sessao(session_id, "prazo")
        if driver_prazo:
            # 2. PRAZO (com sessão reutilizada)
            # Garantir contexto correto: navegar/resetar antes de chamar o otimizador
            try:
                resetar_driver(driver_prazo)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"[PRAZO] Falha ao resetar sessão reutilizada para PRAZO: {e}")

            resultados["prazo"] = executar_prazo_com_otimizacoes(driver_prazo, wait_pool)
        else:
            # Fallback: executar normalmente
            resetar_driver(driver)
            time.sleep(3)
            resultados["prazo"] = executar_prazo(driver)

        # Reutilizar sessão para PEC (sem reset/time.sleep)
        driver_pec = session_pool.reutilizar_sessao(session_id, "pec")
        if driver_pec:
            # 3. PEC (com sessão reutilizada)
            resultados["pec"] = executar_pec_com_otimizacoes(driver_pec, wait_pool)
        else:
            # Fallback: executar normalmente
            resetar_driver(driver)
            time.sleep(3)
            resultados["pec"] = executar_pec(driver)
        
        # Verificar sucesso geral
        todos_sucesso = all([
            resultados["mandado"].get("sucesso", False),
            resultados["prazo"].get("sucesso", False),
            resultados["pec"].get("sucesso", False)
        ])
        
        resultados["sucesso_geral"] = todos_sucesso
        
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        
        return resultados
        
    except Exception as e:
        logger.error(f" Erro no bloco completo: {e}")
        resultados["erro_geral"] = str(e)
        return resultados


def executar_mandado(driver) -> Dict[str, Any]:
    """Mandado Isolado - Processamento de Documentos Internos"""
    logger.info("\n" + "=" * 80)
    logger.info(" MANDADO ISOLADO")
    logger.info("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Navegao especfica do Mandado
        if not mandado_navegacao(driver):
            logger.info("[MANDADO]  Falha na navegao")
            return {
                "sucesso": False, 
                "status": "ERRO_NAVEGACAO", 
                "erro": "Falha ao navegar para documentos internos"
            }
        
        # Executar fluxo principal
        resultado = mandado_fluxo(driver)
        
        # Verificar acesso negado após execução
        # Envolver em try/except pois driver pode estar em estado inconsistente
        try:
            verificar_acesso_negado(driver, "MANDADO")
        except Exception as e:
            # Se falha apenas na verificação (após fluxo bem-sucedido), logar e continuar
            if "NewConnectionError" in str(e) or "Connection refused" in str(e) or "WinError 10061" in str(e):
                logger.debug(f"Verificação de acesso negado ignorada (erro de conexão): {e}")
            else:
                raise
        
        resultado = normalizar_resultado(resultado)
        
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        
        if resultado.get("sucesso"):
            logger.info(f"[MANDADO]  Concludo - {resultado.get('processos', 0)} processos")
        else:
            logger.info(f"[MANDADO]  Falha: {resultado.get('erro', 'Desconhecido')}")
        
        return resultado
        
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        logger.info(f"[MANDADO]  Exceo: {e}")
        return {
            "sucesso": False, 
            "status": "ERRO_EXECUCAO", 
            "erro": str(e),
            "tempo": tempo
        }


def executar_prazo(driver) -> Dict[str, Any]:
    """Prazo Isolado (loop_prazo + fluxo_pz)"""
    pass
    pass
    pass
    
    inicio = datetime.now()
    
    try:
        # Executar loop_prazo
        pass
        resultado_loop = loop_prazo(driver)
        
        # Verificar acesso negado após loop_prazo
        # Envolver em try/except pois driver pode estar em estado inconsistente
        try:
            verificar_acesso_negado(driver, "PRAZO_LOOP")
        except Exception as e:
            # Se falha apenas na verificação (após fluxo bem-sucedido), logar e continuar
            if "NewConnectionError" in str(e) or "Connection refused" in str(e) or "WinError 10061" in str(e):
                logger.debug(f"Verificação de acesso negado ignorada (erro de conexão): {e}")
            else:
                raise
        
        resultado_loop = normalizar_resultado(resultado_loop)

        if not resultado_loop.get("sucesso"):
            logger.error(f"[PRAZO]  Falha no loop_prazo: {resultado_loop.get('erro')}")
            return resultado_loop
        
        pass
        
        # Executar fluxo_prazo (P2B processamento individual)
        # Otimizado: chama o iterador que percorre a lista de processos
        pass
        resetar_driver(driver)

        fluxo_prazo_p2b(driver)  # fluxo_prazo_p2b no retorna valor
        
        # Verificar acesso negado após p2b_fluxo
        # Envolver em try/except pois driver pode estar em estado inconsistente
        try:
            verificar_acesso_negado(driver, "PRAZO_P2B")
        except Exception as e:
            # Se falha apenas na verificação (após fluxo bem-sucedido), logar e continuar
            if "NewConnectionError" in str(e) or "Connection refused" in str(e) or "WinError 10061" in str(e):
                logger.debug(f"Verificação de acesso negado ignorada (erro de conexão): {e}")
            else:
                raise
        
        pass
        pass
        
        tempo = (datetime.now() - inicio).total_seconds()
        
        return {
            'sucesso': True,
            'status': 'SUCESSO',
            'tempo': tempo,
            'loop_prazo': resultado_loop
        }
        
    except Exception as e:
        logger.error(f"[PRAZO]  Erro: {e}")
        import traceback
        logger.exception("Erro detectado")
        return {'sucesso': False, 'erro': str(e)}


def executar_pec(driver) -> Dict[str, Any]:
    """PEC Isolado - Processamento de Execuo"""
    logger.info("\n" + "=" * 80)
    logger.info(" PEC ISOLADO")
    logger.info("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Executar fluxo PEC
        resultado = pec_fluxo(driver)
        
        # Verificar acesso negado após PEC
        # Envolver em try/except pois driver pode estar em estado inconsistente
        try:
            verificar_acesso_negado(driver, "PEC")
        except Exception as e:
            # Se falha apenas na verificação (após fluxo bem-sucedido), logar e continuar
            if "NewConnectionError" in str(e) or "Connection refused" in str(e) or "WinError 10061" in str(e):
                logger.debug(f"Verificação de acesso negado ignorada (erro de conexão): {e}")
            else:
                raise
        
        resultado = normalizar_resultado(resultado)
        
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        
        if resultado.get("sucesso"):
            logger.info(f"[PEC]  Concludo - {resultado.get('processos', 0)} processos")
        else:
            logger.info(f"[PEC]  Falha: {resultado.get('erro', 'Desconhecido')}")
        
        return resultado
        
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        logger.info(f"[PEC]  Exceo: {e}")
        return {
            "sucesso": False, 
            "status": "ERRO_EXECUCAO", 
            "erro": str(e),
            "tempo": tempo
        }


def executar_p2b(driver) -> Dict[str, Any]:
    """P2B Isolado (apenas fluxo_prazo)"""
    inicio = datetime.now()
    
    try:
        # Executar fluxo_prazo completo (navegação para atividades)
        fluxo_prazo_p2b(driver)  # fluxo_prazo no retorna valor
        
        # Verificar acesso negado após fluxo_prazo
        # Envolver em try/except pois driver pode estar em estado inconsistente
        try:
            verificar_acesso_negado(driver, "P2B")
        except Exception as e:
            # Se falha apenas na verificação (após fluxo bem-sucedido), logar e continuar
            if "NewConnectionError" in str(e) or "Connection refused" in str(e) or "WinError 10061" in str(e):
                logger.debug(f"Verificação de acesso negado ignorada (erro de conexão): {e}")
            else:
                raise
        
        tempo = (datetime.now() - inicio).total_seconds()
        
        return {
            'sucesso': True,
            'status': 'SUCESSO',
            'tempo': tempo,
        }
        
    except Exception as e:
        logger.error(f"[P2B]  Erro: {e}")
        import traceback
        logger.exception("Erro detectado")
        return {'sucesso': False, 'erro': str(e)}


# ============================================================================
# MENUS
# ============================================================================

def menu_ambiente() -> Optional[DriverType]:
    """Menu 1: Selecionar Ambiente"""
    logger.info("\n" + "=" * 80)
    logger.info(" MENU 1: SELECIONAR AMBIENTE")
    logger.info("=" * 80)
    logger.info("\n  A - PC + Visvel (1.py)")
    logger.info("  B - PC + Headless (1b.py)")
    logger.info("  C - VT + Visvel (2.py)")
    logger.info("  D - VT + Headless (2b.py)")
    logger.info("  X - Cancelar")
    logger.info("=" * 80)
    
    while True:
        opcao = input("\n Escolha um ambiente (A/B/C/D/X): ").strip().upper()
        
        if opcao == "X":
            return None
        elif opcao == "A":
            return DriverType.PC_VISIBLE
        elif opcao == "B":
            return DriverType.PC_HEADLESS
        elif opcao == "C":
            return DriverType.VT_VISIBLE
        elif opcao == "D":
            return DriverType.VT_HEADLESS
        else:
            logger.info(" Opo invlida!")


def menu_execucao() -> Optional[str]:
    """Menu 2: Selecionar Fluxo"""
    logger.info("\n" + "=" * 80)
    logger.info(" MENU 2: SELECIONAR FLUXO")
    logger.info("=" * 80)
    logger.info("\n  A - Bloco Completo (Mandado + Prazo + PEC)")
    logger.info("  B - Mandado Isolado")
    logger.info("  C - Prazo Isolado (loop + p2b)")
    logger.info("  D - P2B Isolado")
    logger.info("  E - PEC Isolado")
    logger.info("  X - Cancelar")
    logger.info("=" * 80)
    
    while True:
        opcao = input("\n Escolha um fluxo (A/B/C/D/E/X): ").strip().upper()
        
        if opcao == "X":
            return None
        elif opcao in ["A", "B", "C", "D", "E"]:
            return opcao
        else:
            pass


# ============================================================================
# CONFIGURAO DE LOGGING
# ============================================================================

def configurar_logging(driver_type: DriverType):
    """Configura logging baseado no tipo de driver"""
    
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]
    
    # Suprimir logs de Selenium/urllib3 se headless
    if headless:
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
    
    # Arquivo de log
    env_name = "VT" if vt_mode else "PC"
    mode_name = "Headless" if headless else "Visible"
    log_file = os.path.join(LOG_DIR, f"x_{env_name}_{mode_name}_{TIMESTAMP}.log")
    
    # Configurar TeeOutput
    tee = TeeOutput(log_file)
    sys.stdout = tee
    
    return log_file, tee


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funo principal"""
        # Configurar logging básico
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )    
    # Configurar logger específico
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Limpeza de inicialização: matar geckodriver zumbis e temp orphans
    # Garante que execuções anteriores interrompidas não deixem resíduos
    try:
        _matar_zumbis_geckodriver(limpar_temp=True)
        logger.info('[STARTUP] Limpeza de temp/zumbis concluída')
    except Exception as _e:
        logger.debug(f'[STARTUP] Limpeza ignorada: {_e}')

            # Inicializar otimizações globais
    session_pool = SessionPool(max_sessoes=3, expiracao_minutos=60)
    
    tee_output = None
    log_file = None
    driver = None
    session_id = None
    
    try:
        while True:
            # Menu 1: Ambiente
            resultado_menu = menu_ambiente()
            if not resultado_menu:
                pass
                break
            
            driver_type = resultado_menu
            
            # Menu 2: Fluxo
            fluxo = menu_execucao()
            if not fluxo:
                pass
                continue
            
            # Configurar logging
            log_file, tee_output = configurar_logging(driver_type)
            
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            pass
            
            # Criar driver
            driver = criar_e_logar_driver(driver_type)
            if not driver:
                pass
                if tee_output:
                    tee_output.close()
                continue

            # Criar sessão para reutilização entre módulos
            session_id = session_pool.criar_sessao(driver, driver_type)

            # Inicializar ElementWaitPool para waits otimizados
            wait_pool = ElementWaitPool(driver, explicit_wait=10)
            
            # Executar fluxo
            max_tentativas = 3
            tentativa = 0
            
            while tentativa < max_tentativas:
                try:
                    inicio = datetime.now()
                    resultado = None
                    
                    if fluxo == "A":
                        resultado = executar_bloco_completo(driver, session_pool, session_id, wait_pool)
                    elif fluxo == "B":
                        resultado = executar_mandado(driver)
                    elif fluxo == "C":
                        resultado = executar_prazo(driver)
                    elif fluxo == "D":
                        resultado = executar_p2b(driver)
                    elif fluxo == "E":
                        resultado = executar_pec(driver)
                    
                    tempo_total = (datetime.now() - inicio).total_seconds()
                    
                    # Relatório final
                    pass
                    pass
                    pass
                    if resultado:
                        if 'sucesso_geral' in resultado:
                            pass
                        elif 'sucesso' in resultado:
                            pass
                    pass
                    pass
                    
                    # Execução bem-sucedida, sair do loop de tentativas
                    break
                    
                except Exception as e:
                    # Verificar se é erro de ACESSO_NEGADO que requer restart
                    if "RESTART_" in str(e):
                        tentativa += 1
                        pass
                        pass
                        
                        # Finalizar driver atual
                        if driver:
                            try:
                                finalizar_driver_fix(driver)
                            except:
                                pass
                        
                        # Recriar driver
                        if tentativa < max_tentativas:
                            pass
                            driver = criar_e_logar_driver(driver_type)
                            if not driver:
                                pass
                                break
                            pass
                            time.sleep(3)  # Aguardar estabilização
                        else:
                            pass
                            break
                    else:
                        # Outros erros, não tentar novamente
                        logger.error(f" Erro: {e}")
                        import traceback
                        logger.exception("Erro detectado")
                        break
            
            # Pós-execução: finalizar driver
            try:
                if driver:
                    pass
                    finalizar_driver_fix(driver)
                    driver = None
            except Exception as e:
                logger.error(f" Erro ao finalizar driver: {e}")
            
            # Fechar log
            if tee_output:
                tee_output.close()
            
            # Finalizar após execução
            pass
            break
    
    except KeyboardInterrupt:
        logger.error("\n Interrompido pelo usurio")
    except Exception as e:
        logger.error(f" Erro fatal: {e}")
        import traceback
        logger.exception("Erro detectado")
    
    finally:
        # Finalizar sessão se existir
        if session_id:
            try:
                session_pool.finalizar_sessao(session_id)
            except:
                pass

        if driver:
            try:
                finalizar_driver_fix(driver)
            except:
                pass
        if tee_output:
            tee_output.close()
        
        #  NOVO: Finalizar otimizaes
        try:
            from Fix.otimizacao_wrapper import finalizar_otimizacoes
            finalizar_otimizacoes()
        except:
            pass


if __name__ == "__main__":
    pass
    pass
    pass
    pass
    pass
    pass
    
    try:
        main()
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
    finally:
        pass
        pass
        pass

    sys.exit(0)


# ============================================================================
# FUNÇÕES COM OTIMIZAÇÕES INTEGRADAS
# ============================================================================

# Nota: implementação do fluxo de prazo otimizado foi movida para
# `Prazo.p2b_prazo.executar_prazo_com_otimizacoes` — importe e use a
# função centralizada naquele módulo.


def executar_pec_com_otimizacoes(driver, wait_pool: ElementWaitPool) -> Dict[str, Any]:
    """Executar PEC com ElementWaitPool para waits otimizados"""
    try:
        logger.info("[PEC OTIMIZADO] Iniciando processamento com waits adaptativos...")

        # O ElementWaitPool já está sendo usado internamente no módulo PEC
        # Aqui podemos adicionar validações adicionais se necessário

        resultado = pec_fluxo(driver)

        logger.info("[PEC OTIMIZADO] Processamento concluído")
        return {
            "sucesso": True,
            "resultado": resultado
        }

    except Exception as e:
        logger.error(f"[PEC OTIMIZADO] Erro: {e}")
        return {
            "sucesso": False,
            "erro": str(e)
        }



