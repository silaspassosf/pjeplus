"""
Fix/log.py - Sistema de Logging para PJe Plus

Fornece logger estruturado com controle via variável ambiente PJEPLUS_LOG.

Uso:
    from Fix.log import logger
    logger.info("Mensagem")
    logger.error("Erro detectado")
    logger.warning("Aviso")
    logger.debug("Debug info")

Controle:
    Variável PJEPLUS_LOG:
    - "0" (padrão): INFO + WARNING + ERROR
    - "1" / "true": DEBUG + INFO + WARNING + ERROR
    - "on": DEBUG + INFO + WARNING + ERROR
"""

import os
import logging
import sys
from datetime import datetime


class PJELogger:
    """Logger estruturado para PJe Plus com níveis configuráveis."""
    
    NIVEL_PADRAO = logging.INFO
    
    def __init__(self, nome='pjeplus'):
        """
        Inicializa o logger.
        
        Args:
            nome: Nome do logger
        """
        self.logger = logging.getLogger(nome)
        self._configurar_nivel()
        self._configurar_formatador()
    
    def _configurar_nivel(self):
        """Configura nível de logging baseado em variável ambiente."""
        debug_env = os.getenv('PJEPLUS_DEBUG', '0').lower()
        
        if debug_env in ('1', 'true', 'on'):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(self.NIVEL_PADRAO)
    
    def _configurar_formatador(self):
        """Configura formatador de logging."""
        # Remove handlers existentes
        self.logger.handlers.clear()
        
        # Handler console
        handler = logging.StreamHandler(sys.stdout)
        
        # Formato: [HH:MM:SS] [LEVEL] mensagem
        formatador = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handler.setFormatter(formatador)
        self.logger.addHandler(handler)
    
    def debug(self, mensagem):
        """Log nível DEBUG."""
        self.logger.debug(mensagem)
    
    def info(self, mensagem):
        """Log nível INFO."""
        self.logger.info(mensagem)
    
    def warning(self, mensagem):
        """Log nível WARNING."""
        self.logger.warning(mensagem)
    
    def error(self, mensagem):
        """Log nível ERROR."""
        self.logger.error(mensagem)


# Instância global
logger = PJELogger('pjeplus').logger


def get_module_logger(module_name: str):
    """Compatibilidade para módulos que pedem logger nomeado por módulo."""
    return logging.getLogger(module_name)


def getmodulelogger(module_name: str):
    """Alias legado de get_module_logger."""
    return get_module_logger(module_name)


def _log_info(message: str):
    logger.info(message)


def _log_error(message: str):
    logger.error(message)


def log_seletor_multiplo(prefixo: str, seletor: str, status: str, erro: str = None) -> None:
    if status == 'FALHA' and erro:
        logger.warning(f"{prefixo}[{status}] {seletor} :: {erro}")
        return
    logger.info(f"{prefixo}[{status}] {seletor}")


__all__ = [
    'logger',
    'PJELogger',
    'get_module_logger',
    'getmodulelogger',
    '_log_info',
    '_log_error',
    'log_seletor_multiplo',
]
