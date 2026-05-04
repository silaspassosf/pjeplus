"""
SISB Facades e Contratos - Fachadas e contratos públicos consolidados

Consolida as re-exportacoes de __init__.py, o conteudo de standards.py e
o orquestrador de s_orquestrador.py em uma unica unidade.
"""

import logging
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# =============================================================================
# SECAO 1 - SUBPACOTE processamento/ (DEFINIDO ANTES DE core PARA EVITAR
#            CIRCULAR: helpers.py -> validation/__init__ -> facades_contratos)
# =============================================================================

from .processamento.validacao import _validar_dados
from .processamento.integracao import (
    _atualizar_relatorio_com_segundo_protocolo,
    _executar_juntada_pje,
)
from .processamento.navegacao import (
    _voltar_para_lista_ordens_serie,
    _voltar_para_lista_principal,
)
from .processamento.ordens_dados import (
    _carregar_dados_ordem,
    _extrair_ordens_da_serie,
    _identificar_ordens_com_bloqueio,
)
from .processamento.ordens_acao import _aplicar_acao_por_fluxo
from .processamento.relatorios_dados import (
    _agrupar_dados_bloqueios,
    extrair_dados_bloqueios_processados,
)
from .processamento.relatorios_formatacao import (
    gerar_relatorio_bloqueios_processados,
    gerar_relatorio_bloqueios_conciso,
)
from .processamento.relatorios_ordem import _gerar_relatorio_ordem
from .processamento.series_filtro import _filtrar_series
from .processamento.series_navegar import (
    _navegar_e_extrair_ordens_serie,
    _extrair_nome_executado_serie,
)
from .processamento.series_estrategia import _calcular_estrategia_bloqueio
from .processamento.series_fluxo import _processar_series
from .processamento.minutas_prazo import _selecionar_prazo_bloqueio
from .processamento.minutas_campos import _preencher_campos_iniciais
from .processamento.minutas_reus import _processar_reus_otimizado
from .processamento.minutas_salvar import _salvar_minuta
from .processamento.minutas_relatorio import _gerar_relatorio_minuta

# =============================================================================
# SECAO 2 - MODULOS PRINCIPAIS (core, utils, performance, batch, SISB-level)
# =============================================================================

# --- Core (SISB/core.py) ---
from .core import (
    iniciar_sisbajud,
    driver_sisbajud,
    login_automatico_sisbajud,
    login_manual_sisbajud,
    processar_bloqueios,  # usado internamente por executar_sisbajud_completo
)

# --- Utils (SISB/utils.py) ---
from .utils import (
    criar_js_otimizado,
    safe_click,
    aguardar_elemento,
    log_sisbajud,
    validar_numero_processo,
    formatar_valor_monetario,
)

# --- Performance (SISB/performance.py) ---
from .performance import (
    performance_optimizer,
    polling_reducer,
    cache_manager,
    parallel_processor,
)

# --- Batch (SISB/batch.py) ---
from .batch import processar_lote_sisbajud

# --- SISB-level processamento modules ---
from .processamento_minuta import minuta_bloqueio_refatorada
from .processamento_campos_principais import _preencher_campos_principais
from .processamento_campos_reus import (
    _configurar_valor,
    _configurar_opcoes_adicionais,
)
from .processamento_relatorios import (
    _salvar_relatorios,
    _finalizar_minuta,
)
from .processamento_extracao import (
    _extrair_cpf_autor,
    _extrair_nome_autor,
)
from .ordens_execucao import _processar_ordem

# =============================================================================
# SECAO 3 - CONTEUDO DE standards.py (classes, enums, excecoes, utilitarios)
# =============================================================================

# -- Constantes consolidadas --

class SISBConstants:
    """Constantes consolidadas do SISBAJUD"""

    URLS = {
        'base': 'https://sisbajud.cnj.jus.br',
        'login': 'https://sisbajud.cnj.jus.br/login',
        'teimosinha': 'https://sisbajud.cnj.jus.br/teimosinha',
        'minuta_cadastrar': 'https://sisbajud.cnj.jus.br/sisbajudweb/pages/minuta/cadastrar'
    }

    TIMEOUTS = {
        'elemento_padrao': 10,
        'elemento_rapido': 5,
        'elemento_lento': 20,
        'pagina_carregar': 30,
        'script_executar': 15,
        'rate_limit': 2,
    }

    SELECTORS = {
        'input_juiz': 'input[placeholder*="Juiz"]',
        'input_processo': 'input[placeholder="Numero do Processo"]',
        'input_cpf': 'input[placeholder*="CPF"]',
        'input_nome_autor': 'input[placeholder="Nome do autor/exequente da acao"]',
        'botao_consultar': 'button.mat-fab.mat-primary',
        'botao_salvar': 'button.mat-fab.mat-primary mat-icon.fa-save',
        'botao_alterar': 'button mat-icon.fa-edit',
        'tabela_ordens': 'table.mat-table',
        'cabecalho_tabela': 'th.cdk-column-sequencial',
        'linhas_tabela': 'tbody tr.mat-row',
        'botao_voltar': 'button[aria-label="Voltar"] i.fa-chevron-left',
        'modal_confirmar': 'button span:contains("Confirmar")',
        'overlay_backdrop': 'div.cdk-overlay-backdrop',
    }

    PRAZOS = {
        'bloqueio_dias': 30,
        'dias_extras': 2,
        'data_limite_filtro': 15,
        'valor_minimo_bloqueio': 100.0,
        'valor_maximo_sem_desbloqueio': 1000.0,
    }

    RATE_LIMITS = {
        'acoes_por_minuto': 30,
        'delay_minimo': 2000,
        'delay_maximo': 5000,
        'pausa_deteccao': 30000,
    }

    STATUS_PROCESSAMENTO = {
        'pendente': 'PENDENTE',
        'iniciado': 'INICIADO',
        'sucesso': 'SUCESSO',
        'erro': 'ERRO',
        'cancelado': 'CANCELADO',
    }

    TIPOS_FLUXO = {
        'negativo': 'NEGATIVO',
        'positivo': 'POSITIVO',
        'desbloqueio': 'DESBLOQUEIO',
    }

    ERROS = {
        'ELEMENTO_NAO_ENCONTRADO': 'ELEMENTO_NAO_ENCONTRADO',
        'TIMEOUT_EXCEDIDO': 'TIMEOUT_EXCEDIDO',
        'CAPTCHA_DETECTADO': 'CAPTCHA_DETECTADO',
        'SESSAO_EXPIRADA': 'SESSAO_EXPIRADA',
        'DADOS_INVALIDOS': 'DADOS_INVALIDOS',
        'RATE_LIMIT_EXCEDIDO': 'RATE_LIMIT_EXCEDIDO',
    }


# -- Enums para tipos --

class StatusProcessamento(Enum):
    """Status possiveis do processamento SISBAJUD"""
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


# -- Data classes --

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
        if not self.numero:
            raise ValueError("Numero do processo e obrigatorio")
        if not self.autor and not self.reu:
            raise ValueError("Pelo menos autor ou reu deve ser informado")


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
        if self.erros is None:
            self.erros = []
        if self.detalhes is None:
            self.detalhes = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SerieSisbajud:
    """Estrutura padronizada para series SISBAJUD"""
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
        return f"R$ {self.valor_bloqueado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    @property
    def valor_bloquear_text(self) -> str:
        return f"R$ {self.valor_bloquear:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


@dataclass
class OrdemSisbajud:
    """Estrutura padronizada para ordens SISBAJUD"""
    sequencial: int
    protocolo: str
    valor_bloquear: float
    data: datetime
    linha_el: Any = None  # WebElement


# -- Logger padronizado --

class SISBLogger:
    """Logger padronizado para SISBAJUD"""

    def __init__(self, nome: str = "SISBAJUD"):
        self.logger = logging.getLogger(nome)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, mensagem: str, nivel: str = "INFO", contexto: Optional[str] = None):
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
        self.log(f"Erro em {contexto}: {str(erro)}", "ERROR", contexto)

    def log_sucesso(self, mensagem: str, contexto: str):
        self.log(mensagem, "INFO", contexto)


# Instancia global do logger
sisb_logger = SISBLogger()


# -- Excecoes padronizadas --

class SISBException(Exception):
    """Excecao base para SISBAJUD"""
    def __init__(self, mensagem: str, codigo: str = None, contexto: Optional[str] = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo or "ERRO_GENERICO"
        self.contexto = contexto


class ElementoNaoEncontradoException(SISBException):
    """Excecao para elementos nao encontrados"""
    def __init__(self, seletor: str, contexto: Optional[str] = None):
        super().__init__(
            f"Elemento nao encontrado: {seletor}",
            SISBConstants.ERROS['ELEMENTO_NAO_ENCONTRADO'],
            contexto,
        )


class TimeoutExcedidoException(SISBException):
    """Excecao para timeouts excedidos"""
    def __init__(self, operacao: str, timeout: int, contexto: Optional[str] = None):
        super().__init__(
            f"Timeout excedido em {operacao}: {timeout}s",
            SISBConstants.ERROS['TIMEOUT_EXCEDIDO'],
            contexto,
        )


class CaptchaDetectadoException(SISBException):
    """Excecao para CAPTCHA detectado"""
    def __init__(self, contexto: Optional[str] = None):
        super().__init__(
            "CAPTCHA detectado na pagina",
            SISBConstants.ERROS['CAPTCHA_DETECTADO'],
            contexto,
        )


class SessaoExpiradaException(SISBException):
    """Excecao para sessao expirada"""
    def __init__(self, contexto: Optional[str] = None):
        super().__init__(
            "Sessao do SISBAJUD expirada",
            SISBConstants.ERROS['SESSAO_EXPIRADA'],
            contexto,
        )


class DadosInvalidosException(SISBException):
    """Excecao para dados invalidos"""
    def __init__(self, campo: str, valor: Any, contexto: Optional[str] = None):
        super().__init__(
            f"Dados invalidos - {campo}: {valor}",
            SISBConstants.ERROS['DADOS_INVALIDOS'],
            contexto,
        )


# -- Utilitarios padronizados --

def validar_numero_processo_padronizado(numero: Union[str, List[str]]) -> str:
    """
    Validacao padronizada de numero do processo.

    Args:
        numero: Numero do processo (string ou lista)

    Returns:
        str: Numero validado

    Raises:
        DadosInvalidosException: Se formato invalido
    """
    if isinstance(numero, list) and len(numero) > 0:
        numero = numero[0]
    elif not isinstance(numero, str) or not numero.strip():
        raise DadosInvalidosException("numero_processo", numero, "validacao_numero")
    numero = numero.strip()
    import re
    if not re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', numero):
        raise DadosInvalidosException("numero_processo", numero, "formato_brasileiro")
    return numero


def formatar_valor_monetario_padronizado(valor: Union[float, str]) -> str:
    """
    Formatacao padronizada de valores monetarios brasileiros.

    Args:
        valor: Valor a formatar (float ou string)

    Returns:
        str: Valor formatado (ex: 'R$ 1.234,56')
    """
    if isinstance(valor, str):
        valor = float(
            valor.replace('R$', '').replace(' ', '')
            .replace('.', '').replace(',', '.').strip()
        )
    if not isinstance(valor, (int, float)):
        raise DadosInvalidosException("valor_monetario", valor, "conversao_float")
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def calcular_data_limite_padronizada(dias_atras: int = 15) -> datetime:
    """Calculo padronizado de data limite para filtros."""
    return datetime.now() - timedelta(days=dias_atras)


def criar_timestamp_padronizado() -> str:
    """Criacao padronizada de timestamp para logging."""
    return datetime.now().strftime("[%H:%M:%S]")


# -- Decorators padronizados --

def log_operacao(contexto: str):
    """Decorator para logging padronizado de operacoes."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            sisb_logger.log(f"Iniciando {func.__name__}", "DEBUG", contexto)
            try:
                resultado = func(*args, **kwargs)
                sisb_logger.log_sucesso(f"{func.__name__} concluido", contexto)
                return resultado
            except Exception as e:
                sisb_logger.log_erro(e, contexto)
                raise
        return wrapper
    return decorator


def validar_parametros(*validacoes):
    """Decorator para validacao de parametros."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def retry_on_failure(max_tentativas: int = 3, delay: float = 1.0):
    """Decorator para retry automatico em caso de falha."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            import time as _time
            for tentativa in range(max_tentativas):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if tentativa == max_tentativas - 1:
                        raise e
                    sisb_logger.log(
                        f"Tentativa {tentativa + 1} falhou: {e}",
                        "WARNING", func.__name__,
                    )
                    _time.sleep(delay)
        return wrapper
    return decorator

# =============================================================================
# SECAO 4 - ORQUESTRADOR PRINCIPAL (de s_orquestrador.py)
# =============================================================================


def executar_sisbajud_completo(dados_processo, driver_pje=None, modo="automatico"):
    """
    Orquestrador principal para execucao completa SISBAJUD.

    Args:
        dados_processo: Dados do processo extraidos
        driver_pje: Driver do PJE (opcional)
        modo: Modo de execucao ("automatico" ou "manual")

    Returns:
        ResultadoProcessamento: Resultado estruturado da operacao
    """
    resultado = ResultadoProcessamento(
        status=StatusProcessamento.PENDENTE,
        detalhes={},
    )

    try:
        sisb_logger.log("=== INICIANDO SISBAJUD COMPLETO (MODULAR) ===", "INFO", "orquestrador")

        # FASE 1: Validacao de dados
        if not dados_processo:
            raise ValueError("Dados do processo nao fornecidos")

        numero_processo = validar_numero_processo(dados_processo.get('numero'))
        if not numero_processo:
            raise ValueError("Numero do processo invalido")

        # FASE 2: Inicializacao
        sisb_logger.log("FASE 1: Inicializacao SISBAJUD", "INFO", "orquestrador")

        driver_sisb = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisb:
            raise Exception("Falha na inicializacao do SISBAJUD")

        resultado.detalhes['driver_inicializado'] = True

        # FASE 3: Processamento principal
        sisb_logger.log("FASE 2: Processamento principal", "INFO", "orquestrador")

        if dados_processo.get('sisbajud', {}).get('tipo') == 'endereco':
            resultado_processamento = processar_bloqueios(driver_pje=driver_pje)
        else:
            resultado_processamento = processar_bloqueios(driver_pje=driver_pje)

        # FASE 4: Analise de resultados
        if resultado_processamento and resultado_processamento.get('status') == 'sucesso':
            resultado.status = StatusProcessamento.SUCESSO
            resultado.tipo_fluxo = TipoFluxo(resultado_processamento.get('tipo_fluxo', 'positivo'))
            resultado.series_processadas = resultado_processamento.get('series_processadas', 0)
            resultado.ordens_processadas = resultado_processamento.get('ordens_processadas', 0)
        else:
            resultado.status = StatusProcessamento.ERRO
            resultado.erros = resultado_processamento.get('erros', ['Erro desconhecido'])

        # FASE 5: Limpeza e finalizacao
        sisb_logger.log("FASE 3: Finalizacao", "INFO", "orquestrador")

        try:
            if 'driver_sisb' in locals() and driver_sisb:
                driver_sisb.quit()
                sisb_logger.log("Driver SISBAJUD finalizado", "INFO", "orquestrador")
        except Exception as e:
            sisb_logger.log(f"Erro na finalizacao: {e}", "WARNING", "orquestrador")

        resultado.detalhes['processamento_concluido'] = True
        sisb_logger.log("=== SISBAJUD COMPLETO FINALIZADO ===", "INFO", "orquestrador")
        return resultado

    except Exception as e:
        sisb_logger.log(f"Erro no orquestrador: {e}", "ERROR", "orquestrador")
        resultado.status = StatusProcessamento.ERRO
        resultado.erros = [str(e)]
        return resultado


# =============================================================================
# SECAO 5 - ALL
# =============================================================================

__all__ = [
    # Core
    'iniciar_sisbajud',
    'driver_sisbajud',
    'login_automatico_sisbajud',
    'login_manual_sisbajud',

    # Utils
    'criar_js_otimizado',
    'safe_click',
    'aguardar_elemento',
    'log_sisbajud',
    'validar_numero_processo',
    'formatar_valor_monetario',

    # Padroes
    'SISBConstants',
    'StatusProcessamento',
    'TipoFluxo',
    'TipoMinuta',
    'DadosProcesso',
    'ResultadoProcessamento',
    'SerieSisbajud',
    'OrdemSisbajud',
    'SISBLogger',
    'sisb_logger',

    # Excecoes
    'SISBException',
    'ElementoNaoEncontradoException',
    'TimeoutExcedidoException',
    'CaptchaDetectadoException',
    'SessaoExpiradaException',
    'DadosInvalidosException',

    # Utilitarios padronizados
    'validar_numero_processo_padronizado',
    'formatar_valor_monetario_padronizado',
    'calcular_data_limite_padronizada',
    'criar_timestamp_padronizado',
    'log_operacao',
    'validar_parametros',
    'retry_on_failure',

    # Performance
    'performance_optimizer',
    'polling_reducer',
    'cache_manager',
    'parallel_processor',

    # Orquestrador
    'executar_sisbajud_completo',

    # Batch
    'processar_lote_sisbajud',

    # Processamento
    'minuta_bloqueio_refatorada',
    '_validar_dados',
    '_preencher_campos_iniciais',
    '_preencher_campos_principais',
    '_processar_reus_otimizado',
    '_configurar_valor',
    '_configurar_opcoes_adicionais',
    '_salvar_minuta',
    '_gerar_relatorio_minuta',
    '_salvar_relatorios',
    '_finalizar_minuta',
    '_extrair_cpf_autor',
    '_extrair_nome_autor',
    '_processar_ordem',
    '_atualizar_relatorio_com_segundo_protocolo',
    '_executar_juntada_pje',
    '_voltar_para_lista_ordens_serie',
    '_voltar_para_lista_principal',
    '_carregar_dados_ordem',
    '_extrair_ordens_da_serie',
    '_identificar_ordens_com_bloqueio',
    '_aplicar_acao_por_fluxo',
    '_agrupar_dados_bloqueios',
    'extrair_dados_bloqueios_processados',
    'gerar_relatorio_bloqueios_processados',
    'gerar_relatorio_bloqueios_conciso',
    '_gerar_relatorio_ordem',
    '_filtrar_series',
    '_navegar_e_extrair_ordens_serie',
    '_extrair_nome_executado_serie',
    '_calcular_estrategia_bloqueio',
    '_processar_series',
    '_selecionar_prazo_bloqueio',
]
