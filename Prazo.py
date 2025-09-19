# prazo.py - Executa loop.py seguido diretamente de p2b.py
from driver_config import criar_driver, login_func
import logging
import subprocess
import sys
import os

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
    """Executa loop.py seguido diretamente de p2b.py."""
    try:
        # Fase 1: Executar loop.py
        logger.info("[SEQUENCIA] Iniciando execução do loop.py...")
        try:
            result = subprocess.run([sys.executable, "loop.py"], capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode == 0:
                logger.info("[SEQUENCIA] loop.py concluído com sucesso.")
                logger.info(result.stdout)
            else:
                logger.error(f"[SEQUENCIA][ERRO] Falha na execução do loop.py: {result.stderr}")
                raise Exception(f"loop.py falhou: {result.stderr}")
        except Exception as e:
            logger.error(f"[SEQUENCIA][ERRO] Falha na execução do loop.py: {e}")
            raise

        # Fase 2: Executar p2b.py diretamente
        logger.info("[SEQUENCIA] Iniciando execução do p2b.py...")
        try:
            result = subprocess.run([sys.executable, "p2b.py"], capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode == 0:
                logger.info("[SEQUENCIA] p2b.py concluído com sucesso.")
                logger.info(result.stdout)
            else:
                logger.error(f"[SEQUENCIA][ERRO] Falha na execução do p2b.py: {result.stderr}")
                raise Exception(f"p2b.py falhou: {result.stderr}")
        except Exception as e:
            logger.error(f"[SEQUENCIA][ERRO] Falha na execução do p2b.py: {e}")
            raise

    except Exception as e:
        logger.error(f"[SEQUENCIA][ERRO] Erro crítico na execução da sequência: {e}")
        raise

if __name__ == "__main__":
    try:
        executar_sequencia()
    except Exception as e:
        logger.error(f"[SEQUENCIA][ERRO] Falha na execução da sequência: {e}")
        raise
