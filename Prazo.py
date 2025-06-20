# run_all.py
from driver_config import criar_driver, login_func
import logging
from loop import loop_prazo
from p2 import processar_p2

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('pje_automacao.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def executar_sequencia():
    """Executa loop.py seguido de p2.py usando o mesmo driver."""
    driver = None
    try:
        # Criar e configurar o driver uma única vez
        driver = criar_driver()
        login_func(driver)  # Faz login inicial
        
        # Fase 1: Executar loop_prazo
        logger.info("[SEQUENCIA] Iniciando execução do loop_prazo...")
        try:
            loop_prazo(driver)
            logger.info("[SEQUENCIA] loop_prazo concluído com sucesso.")
        except Exception as e:
            logger.error(f"[SEQUENCIA][ERRO] Falha na execução do loop_prazo: {e}")
            raise
            
        # Fase 2: Executar p2
        logger.info("[SEQUENCIA] Iniciando execução do p2...")
        try:
            processar_p2(driver)  # Função principal do p2.py
            logger.info("[SEQUENCIA] p2 concluído com sucesso.")
        except Exception as e:
            logger.error(f"[SEQUENCIA][ERRO] Falha na execução do p2: {e}")
            raise
            
    except Exception as e:
        logger.error(f"[SEQUENCIA][ERRO] Erro crítico na execução da sequência: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("[SEQUENCIA] Driver fechado com sucesso.")
            except:
                logger.error("[SEQUENCIA][ERRO] Falha ao fechar o driver.")

if __name__ == "__main__":
    try:
        executar_sequencia()
    except Exception as e:
        logger.error(f"[SEQUENCIA][ERRO] Falha na execução da sequência: {e}")
        raise
