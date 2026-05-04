#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Peticao/suporte_pet.py — Suporte consolidado do modulo Peticao.

Consolida: core/log.py (logging centralizado, multi-seletor) +
           consolida_delete.py (extracao de processos e geracao de bookmarklet).

Uso:
  from Peticao.suporte_pet import get_module_logger, consolidar_delete_com_bookmarklet
  logger = get_module_logger(__name__)
  consolidar_delete_com_bookmarklet()
"""

import logging
import logging.handlers
import re
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Tuple
from enum import Enum

from selenium.webdriver.remote.webdriver import WebDriver


# ============================================================================
# LOGGING
# ============================================================================

class LogLevel(Enum):
    """Niveis de log customizados para Peticao."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class EmojiValidator:
    """Validador que rejeita mensagens com emojis."""

    EMOJI_PATTERN = re.compile(
        r'[\U0001F600-\U0001F64F'
        r'\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF'
        r'☀-➿'
        r'✀-➿'
        r'\U0001F900-\U0001F9FF'
        r'⭐❌✅⚠️]'
    )

    @classmethod
    def has_emoji(cls, text: str) -> bool:
        return bool(cls.EMOJI_PATTERN.search(text))

    @classmethod
    def remove_emoji(cls, text: str) -> str:
        return cls.EMOJI_PATTERN.sub('', text)


class PJePlusFormatter(logging.Formatter):
    """Formatador customizado para Peticao."""

    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[41m',
        'RESET': '\033[0m',
    }

    def __init__(self, use_color: bool = True, validate_emoji: bool = True):
        super().__init__()
        self.use_color = use_color and self._supports_color()
        self.validate_emoji = validate_emoji

    def format(self, record: logging.LogRecord) -> str:
        if self.validate_emoji and EmojiValidator.has_emoji(record.getMessage()):
            raise ValueError(
                '[EMOJI_VIOLATION] Mensagem contem emoji: %s... Origem: %s:%s' % (
                    record.getMessage()[:50], record.name, record.lineno
                )
            )

        if EmojiValidator.has_emoji(record.getMessage()):
            record.msg = EmojiValidator.remove_emoji(str(record.msg))

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level_name = record.levelname
        module_name = record.name
        line_number = record.lineno
        function_name = record.funcName

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

        if record.exc_info:
            formatted += '\n' + self.formatException(record.exc_info)
        return formatted

    @staticmethod
    def _supports_color() -> bool:
        try:
            return sys.stdout.isatty() and 'TERM' in __import__('os').environ
        except AttributeError:
            return False


class PJePlusLogger:
    """Logger centralizado para Peticao."""

    _instance: Optional['PJePlusLogger'] = None
    _loggers: Dict[str, logging.Logger] = {}

    def __new__(cls, *args, **kwargs):
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
        if self._initialized:
            return
        self.log_level = log_level
        self.log_file = log_file
        self.validate_emoji = validate_emoji
        self.use_color = use_color
        self._setup_root_logger()
        self._initialized = True

    def _setup_root_logger(self):
        root_logger = logging.getLogger('peticao')
        root_logger.setLevel(self.log_level.value)
        root_logger.propagate = False
        root_logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level.value)
        formatter = PJePlusFormatter(
            use_color=self.use_color,
            validate_emoji=self.validate_emoji
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level.value)
            file_formatter = PJePlusFormatter(use_color=False, validate_emoji=self.validate_emoji)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

    def get_logger(self, module_name: str) -> logging.Logger:
        full_name = f'peticao.{module_name}'
        if full_name not in self._loggers:
            logger = logging.getLogger(full_name)
            logger.setLevel(self.log_level.value)
            self._loggers[full_name] = logger
        return self._loggers[full_name]

    def set_level(self, level: LogLevel):
        logging.getLogger('peticao').setLevel(level.value)
        for logger in self._loggers.values():
            logger.setLevel(level.value)


# Singleton global
_logger_instance: Optional[PJePlusLogger] = None


def initialize_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    validate_emoji: bool = True,
) -> PJePlusLogger:
    global _logger_instance
    _logger_instance = PJePlusLogger(
        log_level=log_level,
        log_file=log_file,
        validate_emoji=validate_emoji,
    )
    return _logger_instance


def get_module_logger(module_name: str) -> logging.Logger:
    if _logger_instance is None:
        initialize_logging()
    if module_name.startswith('peticao.'):
        module_name = module_name[8:]
    return _logger_instance.get_logger(module_name)


# ============================================================================
# Utilitarios para multiplos seletores
# ============================================================================

def log_seletor_multiplo(prefixo: str, seletor: str, status: str, erro: Optional[str] = None) -> None:
    logger = get_module_logger('Peticao.suporte_pet')
    if status == 'TENTATIVA':
        logger.info("%s[%s] Testando seletor: %s", prefixo, status, seletor)
    elif status == 'SUCESSO':
        logger.info("%s[%s] Seletor funcionou: %s", prefixo, status, seletor)
    elif status == 'FALHA':
        erro_msg = " - %s..." % erro[:50] if erro else ""
        logger.info("%s[%s] Seletor nao funcionou: %s%s", prefixo, status, seletor, erro_msg)


def tentar_seletores(driver: WebDriver, seletores: List[str], funcao_teste: Callable[..., bool],
                     prefixo_log: str, *args: Any, **kwargs: Any) -> Tuple[Optional[str], Optional[bool]]:
    for seletor in seletores:
        try:
            resultado = funcao_teste(driver, seletor, *args, **kwargs)
            if resultado is True:
                logger = get_module_logger('Peticao.suporte_pet')
                logger.info("%s[SUCESSO] Seletor funcionou: %s", prefixo_log, seletor)
                return seletor, resultado
        except Exception:
            continue
    return None, None


def registrar_seletor_correto(arquivo: str, linha: int, acao: str, seletor: str) -> None:
    log_dir = Path('log')
    log_dir.mkdir(exist_ok=True)
    registro_file = log_dir / 'seletores_corretos_peticao.txt'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entrada = f"{timestamp} | {arquivo}:{linha} | {acao} | {seletor}\n"
    try:
        with open(registro_file, 'a', encoding='utf-8') as f:
            f.write(entrada)
    except Exception:
        logger = logging.getLogger(__name__)
        logger.error("[REGISTRO] Erro ao salvar seletor: %s", str(entrada)[:80])


def tentar_seletores_com_registro(driver: WebDriver, seletores: List[str], funcao_teste: Callable[..., bool],
                                  prefixo_log: str, arquivo: str, linha: int, acao: str,
                                  *args: Any, **kwargs: Any) -> Tuple[Optional[str], Optional[bool]]:
    seletor_funcionou, resultado = tentar_seletores(
        driver, seletores, funcao_teste, prefixo_log, *args, **kwargs
    )
    if seletor_funcionou:
        registrar_seletor_correto(arquivo, linha, acao, seletor_funcionou)
    return seletor_funcionou, resultado


# Alias sem underscore para adocao consistente nos modulos
getmodulelogger = get_module_logger


# ============================================================================
# CONSOLIDA DELETE — extracao de processos e geracao de bookmarklet
# ============================================================================

def extrair_processos_delete():
    """Extrai processos de delete.js"""
    delete_file = Path(__file__).parent / "delete.js"
    if not delete_file.exists():
        logger = get_module_logger(__name__)
        logger.error("delete.js nao encontrado.")
        return {}

    delete_processes = {}
    try:
        with open(delete_file, 'r', encoding='utf-8') as f:
            content = f.read()

        start_marker = 'const delete_processes = {'
        end_marker = '};'
        start = content.find(start_marker)
        if start != -1:
            start += len(start_marker)
            end = content.find(end_marker, start)
            if end != -1:
                json_str = content[start:end].strip()
                if json_str:
                    if not json_str.startswith('{'):
                        json_str = '{' + json_str + '}'
                    try:
                        delete_processes = json.loads(json_str)
                    except Exception:
                        pass

        if not delete_processes:
            for linha in content.split('\n'):
                linha = linha.strip()
                if linha and not linha.startswith('//') and not linha.startswith('javascript:'):
                    try:
                        dado = json.loads(linha)
                        if isinstance(dado, dict):
                            delete_processes.update(dado)
                    except Exception:
                        if linha.isdigit():
                            delete_processes[linha] = True

    except Exception as e:
        logger = get_module_logger(__name__)
        logger.error("Erro ao ler delete.js: %s", e)

    return delete_processes


def gerar_bookmarklet_apagar(processos):
    """Gera bookmarklet JavaScript com os processos extraidos."""
    delete_json = json.dumps(processos, ensure_ascii=False, separators=(',', ':'))
    checkbox_selector = json.dumps(
        'input[type="checkbox"], mat-checkbox input, input.mat-checkbox-input',
        ensure_ascii=False,
    )

    bookmarklet = (
        'javascript:(function(){'
        'const dp=' + delete_json + ';'
        'function norm(s){return(s||"").toLowerCase().trim();}'
        'function sub(a,b){return!b||a.includes(b)||b.includes(a);}'
        'function matchLinha(num,tipoHtml,descHtml,hrefHtml){'
        'var entradas=dp[num];'
        'if(!entradas)return false;'
        'if(!Array.isArray(entradas))return true;'
        'return entradas.some(function(e){'
        'if(e.id_doc){'
        'return hrefHtml.includes("/"+e.id_doc+"/");'
        '}'
        'var t=norm(e.tipo),d=norm(e.desc);'
        'return sub(tipoHtml,t)&&sub(descHtml,d);'
        '});'
        '}'
        'console.log("[DEL] Iniciando selecao...");'
        'var linhas=document.querySelectorAll("tr.cdk-drag,tr[data-row],tr.ng-star-inserted");'
        'var selecionados=0;'
        'linhas.forEach(function(linha){'
        'try{'
        'var a=linha.querySelector("pje-descricao-processo a,td pje-descricao-processo a");'
        'if(!a||!a.textContent)return;'
        'var num=a.textContent.trim();'
        'if(!dp.hasOwnProperty(num))return;'
        'var eTipo=linha.querySelector("span.texto-preto");'
        'var tipoHtml=eTipo?norm(eTipo.textContent):"";'
        'var aDesc=linha.querySelector("a[accesskey=\\"v\\"] span");'
        'var descHtml=aDesc?norm(aDesc.textContent):"";'
        'var aVis=linha.querySelector("a[accesskey=\\"v\\"]");'
        'var hrefHtml=aVis?(aVis.href||aVis.getAttribute("href")||""):"";'
        'if(!matchLinha(num,tipoHtml,descHtml,hrefHtml))return;'
        'var cb=linha.querySelector(' + checkbox_selector + ');'
        'if(cb){cb.click();selecionados++;'
        'var docId=hrefHtml.match(/\\/documento\\/(\\d+)\\//);'
        'console.log("[DEL] OK:",num,"| doc_id:",docId?docId[1]:"?","| tipo:",tipoHtml);}'
        '}catch(e){console.error("[DEL] erro linha:",e);}'
        '});'
        'alert("Selecionados: "+selecionados+"\\nClique no lixão para remover.");'
        '})();'
    )
    return bookmarklet


def consolidar_delete_com_bookmarklet():
    """Consolida delete.js e insere bookmarklet ao final."""
    logger = get_module_logger(__name__)
    processos = extrair_processos_delete()
    if not processos:
        logger.warning("Nenhum processo encontrado em delete.js")
        return False

    logger.info("Processos extraidos: %s", len(processos))
    bookmarklet = gerar_bookmarklet_apagar(processos)

    delete_file = Path(__file__).parent / "delete.js"
    with open(delete_file, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    linhas_limpas = [
        l for l in conteudo.split('\n')
        if not l.strip().startswith('javascript:')
    ]
    conteudo_novo = '\n'.join(linhas_limpas).rstrip() + '\n' + bookmarklet + '\n'

    with open(delete_file, 'w', encoding='utf-8') as f:
        f.write(conteudo_novo)

    logger.info("Bookmarklet inserido ao final de delete.js")
    logger.info("Arquivo: %s", delete_file.absolute())
    return True


if __name__ == '__main__':
    consolidar_delete_com_bookmarklet()
