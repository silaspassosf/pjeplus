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
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from enum import Enum

# Imports dos mdulos refatorados
from Fix.drivers import criar_driver_PC, criar_driver_VT, finalizar_driver as finalizar_driver_fix
from Fix.utils import login_cpf
from Mandado.core import navegacao as mandado_navegacao, iniciar_fluxo_robusto as mandado_fluxo
from Prazo import loop_prazo
from Prazo.p2b_fluxo import fluxo_pz
from Prazo.p2b_prazo import fluxo_prazo as fluxo_prazo_p2b
from PEC.processamento import executar_fluxo_novo as pec_fluxo

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
    
    print(f"\n Criando driver: {driver_type.value}")
    
    try:
        # Criar driver
        if vt_mode:
            driver = criar_driver_vt(headless=headless)
        else:
            driver = criar_driver_pc(headless=headless)
        
        if not driver:
            print(" Falha ao criar driver")
            return None
        
        # Login
        print(" Fazendo login...")
        if not login_cpf(driver):
            print(" Falha no login")
            finalizar_driver_fix(driver)
            return None
        
        print(" Driver criado e logado com sucesso")
        return driver
        
    except Exception as e:
        print(f" Erro ao criar driver: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# VERIFICAÇÃO DE ACESSO NEGADO - CENTRALIZADA
# ============================================================================

def verificar_acesso_negado(driver, contexto: str = "operação") -> None:
    """
    Verifica se o driver está em página de acesso negado.
    Se detectado, lança exceção para forçar reinício do driver.
    
    Args:
        driver: Instância do WebDriver
        contexto: Nome da operação/módulo para logging
        
    Raises:
        Exception: Com prefixo RESTART_* para forçar reinício
    """
    try:
        url_atual = driver.current_url
        
        # Verificar se é acesso negado
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
            mensagem = f"ACESSO_NEGADO detectado em [{contexto}] - URL: {url_atual}"
            print(f"\n⚠️ {mensagem}")
            print(f"🔄 Lançando exceção para reiniciar driver...\n")
            
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
        print(" Resetando driver...")
        
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
        driver.execute_script("document.body.style.zoom='100%'")
        
        # Navegar para pgina inicial
        driver.get("https://pje.trt2.jus.br/pjekz/")
        time.sleep(2)
        
        print(" Driver resetado")
        return True
        
    except Exception as e:
        print(f" Erro ao resetar driver: {e}")
        return False


def executar_bloco_completo(driver) -> Dict[str, Any]:
    """Bloco Completo: Mandado  Prazo  PEC"""
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
        
        # 1. MANDADO
        resultados["mandado"] = executar_mandado(driver)
        resetar_driver(driver)
        time.sleep(3)
        
        # 2. PRAZO
        resultados["prazo"] = executar_prazo(driver)
        resetar_driver(driver)
        time.sleep(3)
        
        # 3. PEC
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
    print("\n" + "=" * 80)
    print(" MANDADO ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Navegao especfica do Mandado
        if not mandado_navegacao(driver):
            print("[MANDADO]  Falha na navegao")
            return {
                "sucesso": False, 
                "status": "ERRO_NAVEGACAO", 
                "erro": "Falha ao navegar para documentos internos"
            }
        
        # Executar fluxo principal
        resultado = mandado_fluxo(driver)
        
        # Verificar acesso negado após execução
        verificar_acesso_negado(driver, "MANDADO")
        
        resultado = normalizar_resultado(resultado)
        
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        
        if resultado.get("sucesso"):
            print(f"[MANDADO]  Concludo - {resultado.get('processos', 0)} processos")
        else:
            print(f"[MANDADO]  Falha: {resultado.get('erro', 'Desconhecido')}")
        
        return resultado
        
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[MANDADO]  Exceo: {e}")
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
        verificar_acesso_negado(driver, "PRAZO_LOOP")
        
        resultado_loop = normalizar_resultado(resultado_loop)

        if not resultado_loop.get("sucesso"):
            logger.error(f"[PRAZO]  Falha no loop_prazo: {resultado_loop.get('erro')}")
            return resultado_loop
        
        pass
        
        # Executar fluxo_pz (P2B doc-level)
        pass
        resetar_driver(driver)

        fluxo_pz(driver)  # fluxo_pz no retorna valor
        
        # Verificar acesso negado após p2b_fluxo
        verificar_acesso_negado(driver, "PRAZO_P2B")
        
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
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


def executar_pec(driver) -> Dict[str, Any]:
    """PEC Isolado - Processamento de Execuo"""
    print("\n" + "=" * 80)
    print(" PEC ISOLADO")
    print("=" * 80)
    
    inicio = datetime.now()
    
    try:
        # Executar fluxo PEC
        resultado = pec_fluxo(driver)
        
        # Verificar acesso negado após PEC
        verificar_acesso_negado(driver, "PEC")
        
        resultado = normalizar_resultado(resultado)
        
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        
        if resultado.get("sucesso"):
            print(f"[PEC]  Concludo - {resultado.get('processos', 0)} processos")
        else:
            print(f"[PEC]  Falha: {resultado.get('erro', 'Desconhecido')}")
        
        return resultado
        
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[PEC]  Exceo: {e}")
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
        verificar_acesso_negado(driver, "P2B")
        
        tempo = (datetime.now() - inicio).total_seconds()
        
        return {
            'sucesso': True,
            'status': 'SUCESSO',
            'tempo': tempo,
        }
        
    except Exception as e:
        logger.error(f"[P2B]  Erro: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


# ============================================================================
# MENUS
# ============================================================================

def menu_ambiente() -> Optional[DriverType]:
    """Menu 1: Selecionar Ambiente"""
    print("\n" + "=" * 80)
    print(" MENU 1: SELECIONAR AMBIENTE")
    print("=" * 80)
    print("\n  A - PC + Visvel (1.py)")
    print("  B - PC + Headless (1b.py)")
    print("  C - VT + Visvel (2.py)")
    print("  D - VT + Headless (2b.py)")
    print("  X - Cancelar")
    print("=" * 80)
    
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
            print(" Opo invlida!")


def menu_execucao() -> Optional[str]:
    """Menu 2: Selecionar Fluxo"""
    print("\n" + "=" * 80)
    print(" MENU 2: SELECIONAR FLUXO")
    print("=" * 80)
    print("\n  A - Bloco Completo (Mandado + Prazo + PEC)")
    print("  B - Mandado Isolado")
    print("  C - Prazo Isolado (loop + p2b)")
    print("  D - P2B Isolado")
    print("  E - PEC Isolado")
    print("  X - Cancelar")
    print("=" * 80)
    
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
    
    #  NOVO: Inicializar otimizaes
    try:
        from Fix.otimizacao_wrapper import inicializar_otimizacoes
        inicializar_otimizacoes()
    except:
        pass
    
    tee_output = None
    log_file = None
    driver = None
    
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
            
            # Executar fluxo
            max_tentativas = 3
            tentativa = 0
            
            while tentativa < max_tentativas:
                try:
                    inicio = datetime.now()
                    resultado = None
                    
                    if fluxo == "A":
                        resultado = executar_bloco_completo(driver)
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
                        traceback.print_exc()
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
        traceback.print_exc()
    
    finally:
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
