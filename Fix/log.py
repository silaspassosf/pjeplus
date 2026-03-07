#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logger Centralizado para PJePlus - Especificação Completa

Este módulo define a arquitetura de logging centralizado que força boas práticas:
- Rejeita mensagens com emojis
- Formata automaticamente com timestamp
- Separa logs por módulo
- Suporta múltiplos níveis (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Integra com progresso unificado
- Valida tipo hints

Substituir: print() e logger.info() despadronizados
Por: logger_pje.info(), logger_pje.error(), etc
"""

import logging
import logging.handlers
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Tuple
from enum import Enum

# typing for selenium WebDriver used across logging helpers
from selenium.webdriver.remote.webdriver import WebDriver


class LogLevel(Enum):
    """Níveis de log customizados para PJePlus."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class EmojiValidator:
    """Validador que rejeita mensagens com emojis."""

    # Padrão Unicode para emojis
    EMOJI_PATTERN = re.compile(
        r'[\U0001F600-\U0001F64F'  # emoticons
        r'\U0001F300-\U0001F5FF'   # symbols & pictographs
        r'\U0001F680-\U0001F6FF'   # transport & map
        r'\U0001F1E0-\U0001F1FF'   # flags (iOS)
        r'\u2600-\u27BF'           # misc symbols
        r'\u2700-\u27BF'           # dingbats
        r'\U0001F900-\U0001F9FF'   # supplemental symbols
        r'\u2B50\u274C\u2705\u26A0\uFE0F]'  # específicos: , , , 
    )

    @classmethod
    def has_emoji(cls, text: str) -> bool:
        """Verifica se texto contém emoji."""
        return bool(cls.EMOJI_PATTERN.search(text))

    @classmethod
    def remove_emoji(cls, text: str) -> str:
        """Remove todos os emojis do texto."""
        return cls.EMOJI_PATTERN.sub('', text)


class PJePlusFormatter(logging.Formatter):
    """Formatador customizado para PJePlus."""

    # Cores para terminal (ANSI)
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
        'RESET': '\033[0m',       # Reset
    }

    def __init__(self, use_color: bool = True, validate_emoji: bool = True):
        """
        Inicializa formatador.

        Args:
            use_color: Usar cores no terminal
            validate_emoji: Validar e rejeitar emojis
        """
        super().__init__()
        self.use_color = use_color and self._supports_color()
        self.validate_emoji = validate_emoji

    def format(self, record: logging.LogRecord) -> str:
        """
        Formata record de log.

        Args:
            record: Record a formatar

        Returns:
            String formatada
        """
        # Validar emoji
        if self.validate_emoji and EmojiValidator.has_emoji(record.getMessage()):
            raise ValueError(
                f'[EMOJI_VIOLATION] Mensagem contém emoji: {record.getMessage()[:50]}... '
                f'Origem: {record.name}:{record.lineno}'
            )

        # Remover emojis mesmo que não em modo validação rigorosa
        if EmojiValidator.has_emoji(record.getMessage()):
            record.msg = EmojiValidator.remove_emoji(str(record.msg))

        # Formatar base
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level_name = record.levelname
        module_name = record.name
        line_number = record.lineno
        function_name = record.funcName

        # Construir mensagem
        if self.use_color:
            color = self.COLORS.get(level_name, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            formatted = (
                f'{color}[{timestamp}] [{level_name}] '
                f'{module_name}:{function_name}:{line_number} '
                f'{record.getMessage()}{reset}'
            )
        else:
            formatted = (
                f'[{timestamp}] [{level_name}] '
                f'{module_name}:{function_name}:{line_number} '
                f'{record.getMessage()}'
            )

        # Adicionar traceback se houver exception
        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)

        return formatted

    @staticmethod
    def _supports_color() -> bool:
        """Verifica se terminal suporta cores."""
        return sys.stdout.isatty() and 'TERM' in __import__('os').environ


class PJePlusLogger:
    """Logger centralizado para PJePlus."""

    _instance: Optional['PJePlusLogger'] = None
    _loggers: Dict[str, logging.Logger] = {}

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        log_level: LogLevel = LogLevel.INFO,
        log_file: Optional[Path] = None,
        validate_emoji: bool = True,
        use_color: bool = True,
    ):
        """
        Inicializa logger centralizado.

        Args:
            log_level: Nível mínimo de log
            log_file: Caminho do arquivo de log (opcional)
            validate_emoji: Validar e rejeitar emojis
            use_color: Usar cores no terminal
        """
        if self._initialized:
            return

        self.log_level = log_level
        self.log_file = log_file
        self.validate_emoji = validate_emoji
        self.use_color = use_color
        self._setup_root_logger()
        self._initialized = True

    def _setup_root_logger(self):
        """Configura logger raiz."""
        root_logger = logging.getLogger('pjeplus')
        root_logger.setLevel(self.log_level.value)
        root_logger.propagate = False

        # Limpar handlers anteriores
        root_logger.handlers.clear()

        # Handler de console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level.value)
        formatter = PJePlusFormatter(
            use_color=self.use_color,
            validate_emoji=self.validate_emoji
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Handler de arquivo (se configurado)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level.value)
            file_formatter = PJePlusFormatter(use_color=False, validate_emoji=self.validate_emoji)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

    def get_logger(self, module_name: str) -> logging.Logger:
        """
        Obtém logger para um módulo.

        Args:
            module_name: Nome do módulo (ex: 'pjeplus.SISB.series')

        Returns:
            Logger configurado
        """
        full_name = f'pjeplus.{module_name}'

        if full_name not in self._loggers:
            logger = logging.getLogger(full_name)
            logger.setLevel(self.log_level.value)
            self._loggers[full_name] = logger

        return self._loggers[full_name]

    def set_level(self, level: LogLevel):
        """Altera nível de log globalmente."""
        logging.getLogger('pjeplus').setLevel(level.value)
        for logger in self._loggers.values():
            logger.setLevel(level.value)


# Singleton global
_logger_instance: Optional[PJePlusLogger] = None


def initialize_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    validate_emoji: bool = True,
) -> PJePlusLogger:
    """
    Inicializa o sistema de logging.

    Chamar UMA VEZ no início da aplicação.

    Args:
        log_level: Nível mínimo de log
        log_file: Caminho do arquivo de log
        validate_emoji: Validar emojis

    Returns:
        Instância do logger centralizado

    Exemplo:
        initialize_logging(
            log_level=LogLevel.DEBUG,
            log_file=Path('logs/pjeplus.log')
        )
    """
    global _logger_instance
    _logger_instance = PJePlusLogger(
        log_level=log_level,
        log_file=log_file,
        validate_emoji=validate_emoji,
    )
    return _logger_instance


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Obtém logger para um módulo.

    Uso em cada arquivo Python:

    ```python
    from Fix.log import get_module_logger

    logger = get_module_logger(__name__)

    def funcao_exemplo():
        logger.info('Iniciando operação')
        try:
            # fazer algo
            logger.info('Operação concluída com sucesso')
        except Exception as e:
            logger.error(f'Erro na operação: {e}', exc_info=True)
    ```

    Args:
        module_name: Nome do módulo (__name__)

    Returns:
        Logger configurado
    """
    if _logger_instance is None:
        initialize_logging()

    # Remover prefixo 'pjeplus.' se presente
    if module_name.startswith('pjeplus.'):
        module_name = module_name[8:]

    return _logger_instance.get_logger(module_name)


# ============ UTILITÁRIOS PARA MÚLTIPLOS SELETORES ============

def log_seletor_multiplo(prefixo: str, seletor: str, status: str, erro: Optional[str] = None) -> None:
    """
    Logging padronizado para tentativas de múltiplos seletores.

    Args:
        prefixo: Identificador da operação (ex: '[PRAZO]', '[RADIO]')
        seletor: Seletor CSS/XPath testado
        status: 'TENTATIVA', 'SUCESSO', 'FALHA'
        erro: Mensagem de erro (opcional, apenas para FALHA)
    """
    logger = get_module_logger('Fix.log')
    if status == 'TENTATIVA':
        logger.info(f"{prefixo}[{status}] Testando seletor: {seletor}")
    elif status == 'SUCESSO':
        logger.info(f"{prefixo}[{status}] Seletor funcionou: {seletor}")
    elif status == 'FALHA':
        erro_msg = f" - {erro[:50]}..." if erro else ""
        logger.info(f"{prefixo}[{status}] Seletor não funcionou: {seletor}{erro_msg}")


def tentar_seletores(driver: WebDriver, seletores: List[str], funcao_teste: Callable[..., bool], prefixo_log: str, *args: Any, **kwargs: Any) -> Tuple[Optional[str], Optional[bool]]:
    """
    Tenta múltiplos seletores sequencialmente até um funcionar.
    Log apenas o seletor que funcionou.

    Args:
        driver: WebDriver instance
        seletores: Lista de seletores CSS/XPath para tentar
        funcao_teste: Função que recebe (driver, seletor, *args, **kwargs) e retorna bool
        prefixo_log: Prefixo para logging (ex: '[PRAZO]')
        *args, **kwargs: Argumentos extras para funcao_teste

    Returns:
        tuple: (seletor_sucesso, resultado_funcao) ou (None, None) se nenhum funcionou
    """
    for seletor in seletores:
        try:
            resultado = funcao_teste(driver, seletor, *args, **kwargs)
            if resultado is True:
                # Log apenas o sucesso
                logger = get_module_logger('Fix.log')
                logger.info(f"{prefixo_log}[SUCESSO] Seletor funcionou: {seletor}")
                return seletor, resultado
        except Exception:
            # Não logar falhas, apenas continuar tentando
            continue

    return None, None


def registrar_seletor_correto(arquivo: str, linha: int, acao: str, seletor: str) -> None:
    """
    Registra seletor correto em arquivo txt para análise posterior.

    Args:
        arquivo: Nome do arquivo onde foi usado
        linha: Número da linha aproximado
        acao: Descrição da ação (ex: 'preencher_prazo', 'clicar_botao')
        seletor: Seletor que funcionou
    """
    import os
    from datetime import datetime

    # Criar pasta log se não existir
    log_dir = Path('log')
    log_dir.mkdir(exist_ok=True)

    # Arquivo de registro
    registro_file = log_dir / 'seletores_corretos.txt'

    # Formatar entrada
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entrada = f"{timestamp} | {arquivo}:{linha} | {acao} | {seletor}\n"

    # Adicionar ao arquivo
    try:
        with open(registro_file, 'a', encoding='utf-8') as f:
            f.write(entrada)
    except Exception as e:
        # Fallback silencioso se não conseguir escrever
        print(f"[REGISTRO] Erro ao salvar seletor: {e}")


# Função auxiliar para uso automático (chama tentar_seletores + registra)
def tentar_seletores_com_registro(driver: WebDriver, seletores: List[str], funcao_teste: Callable[..., bool], prefixo_log: str,
                                 arquivo: str, linha: int, acao: str, *args: Any, **kwargs: Any) -> Tuple[Optional[str], Optional[bool]]:
    """
    Versão que automaticamente registra o seletor correto.

    Args:
        driver: WebDriver instance
        seletores: Lista de seletores CSS/XPath para tentar
        funcao_teste: Função que recebe (driver, seletor, *args, **kwargs) e retorna bool
        prefixo_log: Prefixo para logging (ex: '[PRAZO]')
        arquivo: Nome do arquivo (__file__)
        linha: Número da linha (__line__)
        acao: Descrição da ação
        *args, **kwargs: Argumentos extras para funcao_teste

    Returns:
        tuple: (seletor_sucesso, resultado_funcao) ou (None, None) se nenhum funcionou
    """
    seletor_funcionou, resultado = tentar_seletores(
        driver, seletores, funcao_teste, prefixo_log, *args, **kwargs
    )

    # Registrar se encontrou um seletor
    if seletor_funcionou:
        registrar_seletor_correto(arquivo, linha, acao, seletor_funcionou)

    return seletor_funcionou, resultado


# ============ EXEMPLO DE USO ============

def example_usage():
    """Exemplo de como usar o logger."""

    # 1. Inicializar no main
    initialize_logging(
        log_level=LogLevel.DEBUG,
        log_file=Path('logs/pjeplus.log')
    )

    # 2. Em cada módulo
    logger = get_module_logger(__name__)

    # 3. Usar
    logger.debug('Mensagem de debug')
    logger.info('Operação iniciada')
    logger.warning('Aviso importante')
    logger.error('Erro detectado')
    logger.critical('Erro crítico!')

    # 4. Com variáveis (sem emojis!)
    processo_id = '0000001-98.2024.8.26.0100'
    logger.info(f'Processando: {processo_id}')

    # 5. Exceções
    try:
        1 / 0
    except Exception:
        logger.error('Erro na divisão', exc_info=True)


# ============ INTEGRAÇÃO COM MÓDULOS EXISTENTES ============

"""
Estratégia de migração dos módulos atuais:

SISB/series/processor.py:
    # ANTES
    logger.info(f'[SISBAJUD]  Analisando série {idx}: {id_serie}')
    
    # DEPOIS
    logger = get_module_logger(__name__)
    logger.info(f'Analisando série {idx}: {id_serie}')

SISB/processamento/ordens_acao.py:
    # ANTES
    from ..utils import safe_click
    logger = logging.getLogger(__name__)
    logger.error(f'[_aplicar_acao]    Erro ao preencher valor parcial: {e_valor}')
    
    # DEPOIS
    from Fix.log import get_module_logger
    logger = get_module_logger(__name__)
    logger.error(f'Erro ao preencher valor parcial: {e_valor}', exc_info=True)

PEC/actions/executor.py:
    # ANTES (presumido)
    logger.info('DEBUG:', resultado)
    logger.info('[PEC] Executando ação')
    
    # DEPOIS
    logger = get_module_logger(__name__)
    logger.debug('Resultado', extra={'resultado': resultado})
    logger.info('Executando ação')
"""


if __name__ == '__main__':
    example_usage()

# Backward compatibility: export a default logger
import logging
logger = logging.getLogger('Fix')

# Backward compatibility functions
def _log_info(msg: str):
    """Função de compatibilidade para logging info."""
    logger.info(msg)

def _log_error(msg: str):
    """Função de compatibilidade para logging error."""
    logger.error(msg)

def _audit(msg: str):
    """Função de compatibilidade para audit logging."""
    logger.info(f"[AUDIT] {msg}")
