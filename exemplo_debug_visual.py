# exemplo_debug_visual.py
"""
Exemplo de como usar debug visual com scripts existentes
Integra com m1.py, loop.py, etc.
"""

from debug_visual_config import criar_driver_visual_debug
import time

def exemplo_m1_com_debug():
    """Exemplo executando m1.py com debug visual"""
    print("=== EXEMPLO M1 COM DEBUG VISUAL ===")
    
    # Cria driver com debug visual
    driver, debug_helper = criar_driver_visual_debug(headless=False)
    
    try:
        debug_helper.log_debug_vscode("Iniciando processo M1 com debug visual")
        
        # Simula login
        debug_helper.capturar_estado_debug("antes_login")
        driver.get("https://pje.trt2.jus.br/primeirograu/login.seam")
        debug_helper.capturar_estado_debug("tela_login")
        
        # Aqui você pode chamar suas funções existentes
        # Por exemplo: from m1 import processar_mandado_m1
        # processar_mandado_m1(driver)
        
        # Aguarda para visualização
        debug_helper.log_debug_vscode("Aguardando para visualização...")
        time.sleep(5)
        
        # Gera relatório final
        relatorio = debug_helper.criar_relatorio_debug()
        debug_helper.log_debug_vscode(f"Relatório gerado: {relatorio}")
        
    except Exception as e:
        debug_helper.log_debug_vscode(f"Erro: {e}", "ERROR")
        debug_helper.capturar_estado_debug("erro_ocorrido")
    finally:
        driver.quit()

def exemplo_argos_com_debug():
    """Exemplo executando fluxo ARGOS com debug visual"""
    print("=== EXEMPLO ARGOS COM DEBUG VISUAL ===")
    
    driver, debug_helper = criar_driver_visual_debug(headless=False)
    
    try:
        debug_helper.log_debug_vscode("Iniciando fluxo ARGOS com debug visual")
        
        # Navega para processo específico
        debug_helper.capturar_estado_debug("inicio_argos")
        
        # Aqui integraria com suas funções do ARGOS
        # from m1 import fluxo_argos
        # fluxo_argos(driver)
        
        debug_helper.log_debug_vscode("Fluxo ARGOS concluído")
        
    except Exception as e:
        debug_helper.log_debug_vscode(f"Erro no ARGOS: {e}", "ERROR")
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Escolha o exemplo:")
    print("1 - M1 com debug visual")
    print("2 - ARGOS com debug visual")
    
    escolha = input("Digite 1 ou 2: ")
    
    if escolha == "1":
        exemplo_m1_com_debug()
    elif escolha == "2":
        exemplo_argos_com_debug()
    else:
        print("Opção inválida")
