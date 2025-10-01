# pje.py
# Script orquestrador que executa m1.py, loop.py, p2b.py e pec.py em sequência compartilhando o mesmo driver

import sys
import time
import logging
from datetime import datetime
from driver_config import criar_driver, login_func
from monitor import monitor

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_sequencial.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def executar_m1(driver):
    """Executa m1.py com navegação específica"""
    try:
        logger.info("[M1] Iniciando execução do M1.PY...")
        
        # Importar função de navegação específica do m1.py
        from m1 import navegacao, iniciar_fluxo
        
        # 1. Navegar para a tela específica do M1 (documentos internos)
        if not navegacao(driver):
            logger.error("[M1] ❌ Falha na navegação específica do M1")
            return False
        
        # 2. Executar o fluxo principal do M1
        resultado = iniciar_fluxo(driver)
        
        if resultado:
            logger.info("[M1] ✅ M1.PY executado com sucesso")
            return True
        else:
            logger.error("[M1] ❌ Falha na execução do fluxo M1")
            return False
            
    except Exception as e:
        logger.error(f"[M1] ❌ Erro na execução do M1.PY: {e}")
        return False

def executar_loop(driver):
    """Executa loop.py com navegação específica"""
    try:
        logger.info("[LOOP] Iniciando execução do LOOP.PY...")
        
        # Importar função específica do loop.py
        from loop import loop_prazo
        
        # loop_prazo já navega para sua URL específica e executa o fluxo completo
        resultado = loop_prazo(driver)
        
        if resultado:
            logger.info("[LOOP] ✅ LOOP.PY executado com sucesso")
            return True
        else:
            logger.error("[LOOP] ❌ Falha na execução do LOOP.PY")
            return False
            
    except Exception as e:
        logger.error(f"[LOOP] ❌ Erro na execução do LOOP.PY: {e}")
        return False

def executar_p2b(driver):
    """Executa p2b.py com navegação específica"""
    try:
        logger.info("[P2B] Iniciando execução do P2B.PY...")
        
        # Importar função específica do p2b.py
        from p2b import processar_p2
        
        # Chama p2b.py passando o driver existente
        resultado = processar_p2(driver_existente=driver)
        
        if resultado:
            logger.info("[P2B] ✅ P2B.PY executado com sucesso")
            return True
        else:
            logger.error("[P2B] ❌ Falha na execução do P2B.PY")
            return False
            
    except Exception as e:
        logger.error(f"[P2B] ❌ Erro na execução do P2B.PY: {e}")
        return False

def executar_pec(driver):
    """Executa pec.py com navegação específica"""
    try:
        logger.info("[PEC] Iniciando execução do PEC.PY...")
        
        # Importar função de navegação específica do pec.py
        from pec import navegar_para_atividades
        
        # 1. Navegar para a tela específica do PEC (atividades)
        if not navegar_para_atividades(driver):
            logger.error("[PEC] ❌ Falha na navegação específica do PEC")
            return False
        
        # 2. Importar e executar o processamento principal do PEC
        from Fix import indexar_e_processar_lista
        
        # Executar o processamento da lista de atividades
        resultado = indexar_e_processar_lista(driver, tipo_lista="atividades")
        
        if resultado:
            logger.info("[PEC] ✅ PEC.PY executado com sucesso")
            return True
        else:
            logger.error("[PEC] ❌ Falha na execução do PEC")
            return False
            
    except Exception as e:
        logger.error(f"[PEC] ❌ Erro na execução do pec.py: {e}")
        return False

def aguardar_confirmacao(etapa):
    """Função desabilitada - execução automática sem confirmações"""
    # Execução automática - sempre retorna True para continuar
    logger.info(f"[AUTO] {etapa} concluída. Continuando automaticamente...")
    return True

def main():
    """Função principal que executa toda a sequência"""
    logger.info("="*60)
    logger.info("[PJE_SEQUENCIAL] Iniciando execução sequencial")
    logger.info(f"[PJE_SEQUENCIAL] Timestamp: {datetime.now()}")
    logger.info("="*60)
    
    # Iniciar monitoramento
    monitor.iniciar_monitoramento()
    
    driver = None
    etapas_executadas = []
    
    try:
        # Criar e configurar o driver
        logger.info("[SETUP] Criando driver...")
        driver = criar_driver(headless=False)
        
        if not driver:
            logger.error("[SETUP] ❌ Falha ao criar driver")
            return False
        
        # Realizar login
        logger.info("[LOGIN] Executando login automático...")
        login_ok = login_func(driver)
        
        if not login_ok:
            logger.error("[LOGIN] ❌ Falha no login automático")
            return False
        
        logger.info("[LOGIN] ✅ Login realizado com sucesso")
        
        # === ETAPA 1: M1.PY ===
        logger.info("\n" + "="*50)
        logger.info("[ETAPA 1] Executando M1.PY")
        logger.info("="*50)
        
        monitor.registrar_inicio_etapa("M1.PY")
        sucesso_m1 = executar_m1(driver)
        monitor.registrar_fim_etapa("M1.PY", sucesso_m1)
        
        if sucesso_m1:
            etapas_executadas.append("M1")
            logger.info("[ETAPA 1] ✅ M1.PY executado com sucesso")
        else:
            logger.error("[ETAPA 1] ❌ Falha na execução do M1.PY")
            if not aguardar_confirmacao("M1.PY (com erro)"):
                return False
        
        # === ETAPA 2: LOOP.PY ===
        logger.info("\n" + "="*50)
        logger.info("[ETAPA 2] Executando LOOP.PY")
        logger.info("="*50)
        
        monitor.registrar_inicio_etapa("LOOP.PY")
        sucesso_loop = executar_loop(driver)
        monitor.registrar_fim_etapa("LOOP.PY", sucesso_loop)
        
        if sucesso_loop:
            etapas_executadas.append("LOOP")
            logger.info("[ETAPA 2] ✅ LOOP.PY executado com sucesso")
        else:
            logger.error("[ETAPA 2] ❌ Falha na execução do LOOP.PY")
            if not aguardar_confirmacao("LOOP.PY (com erro)"):
                return False
        
        # === ETAPA 3: P2B.PY ===
        logger.info("\n" + "="*50)
        logger.info("[ETAPA 3] Executando P2B.PY")
        logger.info("="*50)
        
        monitor.registrar_inicio_etapa("P2B.PY")
        sucesso_p2b = executar_p2b(driver)
        monitor.registrar_fim_etapa("P2B.PY", sucesso_p2b)
        
        if sucesso_p2b:
            etapas_executadas.append("P2B")
            logger.info("[ETAPA 3] ✅ P2B.PY executado com sucesso")
        else:
            logger.error("[ETAPA 3] ❌ Falha na execução do P2B.PY")
            if not aguardar_confirmacao("P2B.PY (com erro)"):
                return False
        
        # === ETAPA 4: PEC.PY ===
        logger.info("\n" + "="*50)
        logger.info("[ETAPA 4] Executando PEC.PY")
        logger.info("="*50)
        
        monitor.registrar_inicio_etapa("PEC.PY")
        sucesso_pec = executar_pec(driver)
        monitor.registrar_fim_etapa("PEC.PY", sucesso_pec)
        
        if sucesso_pec:
            etapas_executadas.append("PEC")
            logger.info("[ETAPA 4] ✅ PEC.PY executado com sucesso")
        else:
            logger.error("[ETAPA 4] ❌ Falha na execução do PEC.PY")
        
        # Relatório final
        logger.info("\n" + "="*60)
        logger.info("[RELATÓRIO FINAL] EXECUÇÃO TOTAL")
        logger.info(f"Etapas executadas com sucesso: {', '.join(etapas_executadas)}")
        logger.info(f"Total de etapas: {len(etapas_executadas)}/4")
        
        if len(etapas_executadas) == 4:
            logger.info("🎉 TODAS AS ETAPAS EXECUTADAS COM SUCESSO!")
        else:
            logger.warning("⚠️ Algumas etapas falharam ou foram interrompidas")
        
        logger.info("="*60)
        
        return len(etapas_executadas) == 3
        
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPÇÃO] Execução interrompida pelo usuário (Ctrl+C)")
        return False
        
    except Exception as e:
        logger.error(f"[ERRO CRÍTICO] Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Fechar driver automaticamente sem aguardar confirmação
        if driver:
            try:
                logger.info("[FINALIZAÇÃO] Fechando driver automaticamente...")
                driver.quit()
                logger.info("[FINALIZAÇÃO] ✅ Driver fechado com sucesso")
            except Exception as e:
                logger.error(f"[FINALIZAÇÃO] ❌ Erro ao fechar driver: {e}")

if __name__ == "__main__":
    try:
        # Verificar argumentos de linha de comando
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg in ['--help', '-h']:
                print("""
Uso: python pje.py [opções]

Opções:
  --help, -h     Mostra esta mensagem de ajuda
  
Descrição:
  Executa AUTOMATICAMENTE em sequência os scripts:
  1. M1.PY (documentos internos/mandados devolvidos)
  2. LOOP.PY + P2B.PY (movimentação em lote/prazos)
  3. PEC.PY (atividades GIGS)
  
  Compartilha o mesmo driver e sessão do navegador entre todas as etapas.
  A execução é completamente automática, sem pausas para confirmação.
  Você pode interromper a execução com Ctrl+C a qualquer momento.
                """)
                sys.exit(0)
        
        # Executar sequência principal
        sucesso = main()
        sys.exit(0 if sucesso else 1)
        
    except KeyboardInterrupt:
        print("\n[SAÍDA] Execução interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Erro crítico: {e}")
        sys.exit(1)
