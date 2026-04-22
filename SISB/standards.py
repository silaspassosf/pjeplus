"""
SISB Standards - Padrões e constantes consolidadas
Refatoração seguindo padrões do projeto PjePlus
"""

from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

# ===== CONSTANTES CONSOLIDADAS =====

class SISBConstants:
    """Constantes consolidadas do SISBAJUD"""

    # URLs
    URLS = {
        'base': 'https://sisbajud.cnj.jus.br',
        'login': 'https://sisbajud.cnj.jus.br/login',
        'teimosinha': 'https://sisbajud.cnj.jus.br/teimosinha',
        'minuta_cadastrar': 'https://sisbajud.cnj.jus.br/sisbajudweb/pages/minuta/cadastrar'
    }

    # Timeouts padronizados
    TIMEOUTS = {
        'elemento_padrao': 10,
        'elemento_rapido': 5,
        'elemento_lento': 20,
        'pagina_carregar': 30,
        'script_executar': 15,
        'rate_limit': 2  # segundos entre ações
    }

    # Seletores CSS consolidados
    SELECTORS = {
        'input_juiz': 'input[placeholder*="Juiz"]',
        'input_processo': 'input[placeholder="Número do Processo"]',
        'input_cpf': 'input[placeholder*="CPF"]',
        'input_nome_autor': 'input[placeholder="Nome do autor/exequente da ação"]',
        'botao_consultar': 'button.mat-fab.mat-primary',
        'botao_salvar': 'button.mat-fab.mat-primary mat-icon.fa-save',
        'botao_alterar': 'button mat-icon.fa-edit',
        'tabela_ordens': 'table.mat-table',
        'cabecalho_tabela': 'th.cdk-column-sequencial',
        'linhas_tabela': 'tbody tr.mat-row',
        'botao_voltar': 'button[aria-label="Voltar"] i.fa-chevron-left',
        'modal_confirmar': 'button span:contains("Confirmar")',
        'overlay_backdrop': 'div.cdk-overlay-backdrop'
    }

    # Prazos e limites
    PRAZOS = {
        'bloqueio_dias': 30,
        'dias_extras': 2,
        'data_limite_filtro': 15,  # dias para trás
        'valor_minimo_bloqueio': 100.0,
        'valor_maximo_sem_desbloqueio': 1000.0
    }

    # Limites de rate limiting
    RATE_LIMITS = {
        'acoes_por_minuto': 30,
        'delay_minimo': 2000,  # ms
        'delay_maximo': 5000,  # ms
        'pausa_deteccao': 30000  # ms quando detectado
    }

    # Status de processamento
    STATUS_PROCESSAMENTO = {
        'pendente': 'PENDENTE',
        'iniciado': 'INICIADO',
        'sucesso': 'SUCESSO',
        'erro': 'ERRO',
        'cancelado': 'CANCELADO'
    }

    # Tipos de fluxo SISBAJUD
    TIPOS_FLUXO = {
        'negativo': 'NEGATIVO',      # valor_bloqueado = 0
        'positivo': 'POSITIVO',      # bloqueio normal
        'desbloqueio': 'DESBLOQUEIO' # valor baixo + alto a bloquear
    }

    # Códigos de erro padronizados
    ERROS = {
        'ELEMENTO_NAO_ENCONTRADO': 'ELEMENTO_NAO_ENCONTRADO',
        'TIMEOUT_EXCEDIDO': 'TIMEOUT_EXCEDIDO',
        'CAPTCHA_DETECTADO': 'CAPTCHA_DETECTADO',
        'SESSAO_EXPIRADA': 'SESSAO_EXPIRADA',
        'DADOS_INVALIDOS': 'DADOS_INVALIDOS',
        'RATE_LIMIT_EXCEDIDO': 'RATE_LIMIT_EXCEDIDO'
    }

# ===== ENUMS PARA TIPOS =====

class StatusProcessamento(Enum):
    """Status possíveis do processamento SISBAJUD"""
    PENDENTE = "pendente"
    INICIADO = "iniciado"
    SUCESSO = "sucesso"
    ERRO = "erro"
    CANCELADO = "cancelado"

class TipoFluxo(Enum):
    """Tipos de fluxo SISBAJUD"""
    NEGATIVO = "negativo"
    POSITIVO = "positivo"
    DESBLOQUEIO = "desbloqueio"

class TipoMinuta(Enum):
    """Tipos de minuta SISBAJUD"""
    BLOQUEIO = "bloqueio"
    ENDERECO = "endereco"
    INFORMACOES = "informacoes"

# ===== DATA CLASSES =====

@dataclass
class DadosProcesso:
    """Estrutura padronizada para dados do processo"""
    numero: List[str]
    autor: List[Dict[str, Any]]
    reu: List[Dict[str, Any]]
    sisbajud: Dict[str, Any]
    divida: Optional[Dict[str, Any]] = None
    id_processo: Optional[str] = None

    def __post_init__(self):
        """Validações pós-inicialização"""
        if not self.numero:
            raise ValueError("Número do processo é obrigatório")
        if not self.autor and not self.reu:
            raise ValueError("Pelo menos autor ou réu deve ser informado")

@dataclass
class ResultadoProcessamento:
    """Estrutura padronizada para resultados de processamento"""
    status: StatusProcessamento
    tipo_fluxo: Optional[TipoFluxo] = None
    series_processadas: int = 0
    ordens_processadas: int = 0
    erros: List[str] = None
    detalhes: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        """Inicializações pós-criação"""
        if self.erros is None:
            self.erros = []
        if self.detalhes is None:
            self.detalhes = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class SerieSisbajud:
    """Estrutura padronizada para séries SISBAJUD"""
    id_serie: str
    situacao: str
    data_programada: datetime
    valor_bloqueado: float
    valor_bloquear: float
    vara: str = ""
    juiz: str = ""
    acao: str = ""

    @property
    def valor_bloqueado_text(self) -> str:
        """Valor bloqueado formatado"""
        return f"R$ {self.valor_bloqueado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    @property
    def valor_bloquear_text(self) -> str:
        """Valor a bloquear formatado"""
        return f"R$ {self.valor_bloquear:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

@dataclass
class OrdemSisbajud:
    """Estrutura padronizada para ordens SISBAJUD"""
    sequencial: int
    protocolo: str
    valor_bloquear: float
    data: datetime
    linha_el: Any = None  # WebElement

# ===== LOGGING PADRONIZADO =====

class SISBLogger:
    """Logger padronizado para SISBAJUD"""

    def __init__(self, nome: str = "SISBAJUD"):
        self.logger = logging.getLogger(nome)
        self.logger.setLevel(logging.DEBUG)

        # Criar handler se não existir
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, mensagem: str, nivel: str = "INFO", contexto: Optional[str] = None):
        """Log padronizado com contexto"""
        msg_completa = f"[{contexto}] {mensagem}" if contexto else mensagem

        if nivel == "DEBUG":
            self.logger.debug(msg_completa)
        elif nivel == "INFO":
            self.logger.info(msg_completa)
        elif nivel == "WARNING":
            self.logger.warning(msg_completa)
        elif nivel == "ERROR":
            self.logger.error(msg_completa)
        elif nivel == "CRITICAL":
            self.logger.critical(msg_completa)

    def log_erro(self, erro: Exception, contexto: str):
        """Log específico para erros"""
        self.log(f"Erro em {contexto}: {str(erro)}", "ERROR", contexto)

    def log_sucesso(self, mensagem: str, contexto: str):
        """Log específico para sucessos"""
        self.log(mensagem, "INFO", contexto)

# Instância global do logger
sisb_logger = SISBLogger()

# ===== EXCEÇÕES PADRONIZADAS =====

class SISBException(Exception):
    """Exceção base para SISBAJUD"""
    def __init__(self, mensagem: str, codigo: str = None, contexto: Optional[str] = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo or "ERRO_GENERICO"
        self.contexto = contexto

class ElementoNaoEncontradoException(SISBException):
    """Exceção para elementos não encontrados"""
    def __init__(self, seletor: str, contexto: Optional[str] = None):
        super().__init__(
            f"Elemento não encontrado: {seletor}",
            SISBConstants.ERROS['ELEMENTO_NAO_ENCONTRADO'],
            contexto
        )

class TimeoutExcedidoException(SISBException):
    """Exceção para timeouts excedidos"""
    def __init__(self, operacao: str, timeout: int, contexto: Optional[str] = None):
        super().__init__(
            f"Timeout excedido em {operacao}: {timeout}s",
            SISBConstants.ERROS['TIMEOUT_EXCEDIDO'],
            contexto
        )

class CaptchaDetectadoException(SISBException):
    """Exceção para CAPTCHA detectado"""
    def __init__(self, contexto: Optional[str] = None):
        super().__init__(
            "CAPTCHA detectado na página",
            SISBConstants.ERROS['CAPTCHA_DETECTADO'],
            contexto
        )

class SessaoExpiradaException(SISBException):
    """Exceção para sessão expirada"""
    def __init__(self, contexto: Optional[str] = None):
        super().__init__(
            "Sessão do SISBAJUD expirada",
            SISBConstants.ERROS['SESSAO_EXPIRADA'],
            contexto
        )

class DadosInvalidosException(SISBException):
    """Exceção para dados inválidos"""
    def __init__(self, campo: str, valor: Any, contexto: Optional[str] = None):
        super().__init__(
            f"Dados inválidos - {campo}: {valor}",
            SISBConstants.ERROS['DADOS_INVALIDOS'],
            contexto
        )

# ===== UTILITÁRIOS PADRONIZADOS =====

def validar_numero_processo_padronizado(numero: Union[str, List[str]]) -> str:
    """
    Validação padronizada de número do processo com type hints.

    Args:
        numero: Número do processo (string ou lista)

    Returns:
        str: Número validado

    Raises:
        DadosInvalidosException: Se formato inválido
    """
    if isinstance(numero, list) and len(numero) > 0:
        numero = numero[0]
    elif not isinstance(numero, str) or not numero.strip():
        raise DadosInvalidosException("numero_processo", numero, "validacao_numero")

    numero = numero.strip()

    # Regex para formato brasileiro
    import re
    if not re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', numero):
        raise DadosInvalidosException("numero_processo", numero, "formato_brasileiro")

    return numero

def formatar_valor_monetario_padronizado(valor: Union[float, str]) -> str:
    """
    Formatação padronizada de valores monetários brasileiros.

    Args:
        valor: Valor a formatar (float ou string)

    Returns:
        str: Valor formatado (ex: "R$ 1.234,56")
    """
    if isinstance(valor, str):
        # Tentar converter string para float
        valor = float(valor.replace('R$', '').replace('\u00a0', '').replace('.', '').replace(',', '.').strip())

    if not isinstance(valor, (int, float)):
        raise DadosInvalidosException("valor_monetario", valor, "conversao_float")

    # Formatar no padrão brasileiro
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def calcular_data_limite_padronizada(dias_atras: int = 15) -> datetime:
    """
    Cálculo padronizado de data limite para filtros.

    Args:
        dias_atras: Dias para subtrair da data atual

    Returns:
        datetime: Data limite calculada
    """
    from datetime import datetime, timedelta
    return datetime.now() - timedelta(days=dias_atras)

def criar_timestamp_padronizado() -> str:
    """
    Criação padronizada de timestamp para logging.

    Returns:
        str: Timestamp formatado
    """
    return datetime.now().strftime("[%H:%M:%S]")

# ===== DECORATORS PARA PADRÕES =====

def log_operacao(contexto: str):
    """
    Decorator para logging padronizado de operações.

    Args:
        contexto: Contexto da operação para logging
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            sisb_logger.log(f"Iniciando {func.__name__}", "DEBUG", contexto)
            try:
                resultado = func(*args, **kwargs)
                sisb_logger.log_sucesso(f"{func.__name__} concluído", contexto)
                return resultado
            except Exception as e:
                sisb_logger.log_erro(e, contexto)
                raise
        return wrapper
    return decorator

def validar_parametros(*validacoes):
    """
    Decorator para validação de parâmetros.

    Args:
        validacoes: Funções de validação para cada parâmetro
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Implementar validações aqui
            return func(*args, **kwargs)
        return wrapper
    return decorator

def retry_on_failure(max_tentativas: int = 3, delay: float = 1.0):
    """
    Decorator para retry automático em caso de falha.

    Args:
        max_tentativas: Número máximo de tentativas
        delay: Delay entre tentativas em segundos
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            import time
            for tentativa in range(max_tentativas):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if tentativa == max_tentativas - 1:
                        raise e
                    sisb_logger.log(f"Tentativa {tentativa + 1} falhou: {e}", "WARNING", func.__name__)
                    time.sleep(delay)
        return wrapper
    return decorator