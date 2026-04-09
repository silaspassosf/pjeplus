#!/usr/bin/env python3
"""Orquestrador simples para executar aud ou dom."""
import subprocess
import sys
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bianca/orquestrador.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

MODULES = {
    'aud': 'bianca.aud',
    'dom': 'bianca.dom',
}

def run_module(module_name: str) -> bool:
    """Executa um módulo específico."""
    if module_name not in MODULES:
        logger.error(f"Módulo '{module_name}' não encontrado. Opções: {', '.join(MODULES)}")
        return False

    module = MODULES[module_name]
    logger.info(f"Iniciando execução do módulo: {module}")

    try:
        result = subprocess.run(
            [sys.executable, '-m', module],
            cwd=str(Path(__file__).parent.parent),
            timeout=3600,  # 1 hora
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info(f"Módulo '{module_name}' concluído com sucesso.")
            return True
        else:
            logger.error(f"Módulo '{module_name}' falhou (exit code {result.returncode}).")
            if result.stderr:
                logger.error(f"stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Módulo '{module_name}' excedeu o tempo limite de 1 hora.")
        return False
    except Exception as e:
        logger.error(f"Erro ao executar'{module_name}': {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Uso: python x.py <aud|dom>")
        sys.exit(1)

    module_name = sys.argv[1].lower()
    success = run_module(module_name)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
