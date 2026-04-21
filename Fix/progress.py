# Consolidated progress module (merged from Fix/progress/*)
# Auto-generated during Phase 3 consolidation (B3)

from datetime import datetime
import os
import json
import shutil
import re
import logging
from typing import Optional, Dict, Any, Callable, Tuple
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

# Configurações por tipo de execução
CONFIGURACOES_EXECUCAO = {
    'p2b': {'prefixo_log': '[PROGRESSO_P2B]', 'tipo_sistema': 'P2B'},
    'm1': {'prefixo_log': '[PROGRESSO_M1]', 'tipo_sistema': 'M1'},
    'pec': {'prefixo_log': '[PROGRESSO_PEC]', 'tipo_sistema': 'PEC'},
    'pet': {'prefixo_log': '[PROGRESSO_PET]', 'tipo_sistema': 'PET'},
    'mandado': {'prefixo_log': '[PROGRESSO_MANDADO]', 'tipo_sistema': 'MANDADO'},
    'prov': {'prefixo_log': '[PROGRESSO_PROV]', 'tipo_sistema': 'PROV'},
    'AUD': {'prefixo_log': '[PROGRESSO_AUD]', 'tipo_sistema': 'AUD'},
    'TRIAGEM': {'prefixo_log': '[PROGRESSO_TRIAGEM]', 'tipo_sistema': 'TRIAGEM'},
}

ARQUIVO_PROGRESSO_UNIFICADO = "progresso.json"


# ===== MODELS (merged from Fix/progress/models.py) =====
from enum import Enum
from dataclasses import dataclass, field, asdict


class StatusModulo(Enum):
    NAOINICIADO = "NAO_INICIADO"
    EmProgresso = "EM_PROGRESSO"
    Pausado = "PAUSADO"
    Completo = "COMPLETO"
    Falhado = "FALHADO"
    Recuperacao = "RECUPERACAO"


class NivelLog(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Checkpoint:
    ultimo_item: str
    timestamp: str
    proximo: Optional[str] = None
    contexto: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StatusModuloData:
    status: StatusModulo
    processados: int = 0
    total: int = 0
    tempo_decorrido_segundos: int = 0
    erros: int = 0
    checkpoint: Optional[Checkpoint] = None
    detalhes: Dict[str, Any] = field(default_factory=dict)

    @property
    def percentual(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.processados / self.total) * 100

    def to_dict(self) -> dict:
        data = asdict(self)
        data['status'] = self.status.value
        data['percentual'] = self.percentual
        if self.checkpoint:
            data['checkpoint'] = self.checkpoint.to_dict()
        return data


@dataclass
class RegistroLog:
    timestamp: str
    modulo: str
    nivel: NivelLog
    mensagem: str
    detalhes: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.nivel, str):
            self.nivel = NivelLog(self.nivel)

    def to_dict(self) -> dict:
        data = asdict(self)
        data['nivel'] = self.nivel.value
        return data



def _log_progresso(tipo_execucao: str, mensagem: str, numero_processo: Optional[str] = None):
    config = CONFIGURACOES_EXECUCAO.get(tipo_execucao, {})
    prefixo = config.get('prefixo_log', '[PROGRESSO]')
    if numero_processo:
        print(f"{prefixo}[{numero_processo}] {mensagem}")
    else:
        print(f"{prefixo} {mensagem}")


def _validar_tipo_execucao(tipo_execucao: str) -> bool:
    return tipo_execucao in CONFIGURACOES_EXECUCAO


def _validar_e_limpar_progresso(progresso: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(progresso, dict):
        raise ValueError("Progresso deve ser um dicionário")
    progresso_limpo = progresso.copy()
    if "processos_executados" not in progresso_limpo:
        progresso_limpo["processos_executados"] = []
    elif not isinstance(progresso_limpo["processos_executados"], list):
        progresso_limpo["processos_executados"] = []
    else:
        progresso_limpo["processos_executados"] = list(set(
            item for item in progresso_limpo["processos_executados"]
            if isinstance(item, str) and item.strip()
        ))
    for campo in ["session_active"]:
        if campo not in progresso_limpo:
            progresso_limpo[campo] = False
        elif not isinstance(progresso_limpo[campo], bool):
            progresso_limpo[campo] = bool(progresso_limpo[campo])
    campos_temporarios = ["temp_data", "cache", "session_data"]
    for campo in campos_temporarios:
        progresso_limpo.pop(campo, None)
    return progresso_limpo


def carregar_progresso_unificado(tipo_execucao: str, *, suppress_load_log: bool = False) -> Dict[str, Any]:
    if not _validar_tipo_execucao(tipo_execucao):
        raise ValueError(f"Tipo de execução não suportado: {tipo_execucao}")
    try:
        if os.path.exists(ARQUIVO_PROGRESSO_UNIFICADO):
            with open(ARQUIVO_PROGRESSO_UNIFICADO, "r", encoding="utf-8") as f:
                dados_completos = json.load(f)
                if tipo_execucao in dados_completos:
                    dados = dados_completos[tipo_execucao]
                    if not isinstance(dados, dict):
                        raise ValueError("Dados não são um dicionário válido")
                    if "processos_executados" not in dados:
                        dados["processos_executados"] = []
                    if not isinstance(dados["processos_executados"], list):
                        dados["processos_executados"] = []
                    if "session_active" not in dados:
                        dados["session_active"] = True
                    if "last_update" not in dados:
                        dados["last_update"] = None
                    if not suppress_load_log:
                        _log_progresso(tipo_execucao, f" Progresso carregado: {len(dados['processos_executados'])} executados")
                    return dados
                else:
                    _log_progresso(tipo_execucao, "ℹ Seção não encontrada, criando nova")
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        _log_progresso(tipo_execucao, f"[AVISO] Arquivo corrompido ou inválido: {e}")
        _log_progresso(tipo_execucao, "[AVISO] Criando novo arquivo de progresso...")
        try:
            if os.path.exists(ARQUIVO_PROGRESSO_UNIFICADO):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{ARQUIVO_PROGRESSO_UNIFICADO.replace('.json', '')}_backup_{timestamp}.json"
                shutil.copy(ARQUIVO_PROGRESSO_UNIFICADO, backup_path)
                _log_progresso(tipo_execucao, f"📋 Backup criado: {backup_path}")
        except Exception as backup_e:
            _log_progresso(tipo_execucao, f" Erro ao criar backup: {backup_e}")
    except Exception as e:
        _log_progresso(tipo_execucao, f"[AVISO] Erro inesperado ao carregar progresso: {e}")
    dados_limpos = {"processos_executados": [], "session_active": True, "last_update": None}
    try:
        salvar_progresso_unificado(tipo_execucao, dados_limpos)
        _log_progresso(tipo_execucao, " Arquivo de progresso limpo criado")
    except Exception as save_e:
        _log_progresso(tipo_execucao, f" Erro ao salvar progresso limpo: {save_e}")
    return dados_limpos


def salvar_progresso_unificado(tipo_execucao: str, progresso: Dict[str, Any]):
    if not _validar_tipo_execucao(tipo_execucao):
        raise ValueError(f"Tipo de execução não suportado: {tipo_execucao}")
    try:
        progresso_validado = _validar_e_limpar_progresso(progresso)
        dados_completos = {}
        if os.path.exists(ARQUIVO_PROGRESSO_UNIFICADO):
            try:
                with open(ARQUIVO_PROGRESSO_UNIFICADO, "r", encoding="utf-8") as f:
                    dados_completos = json.load(f)
            except (json.JSONDecodeError, ValueError):
                _log_progresso(tipo_execucao, "[AVISO] Arquivo progresso corrompido, recriando...")
                dados_completos = {}
        progresso_validado["last_update"] = datetime.now().isoformat()
        dados_completos[tipo_execucao] = progresso_validado
        with open(ARQUIVO_PROGRESSO_UNIFICADO, "w", encoding="utf-8") as f:
            json.dump(dados_completos, f, ensure_ascii=False, indent=2)
        _log_progresso(tipo_execucao, "💾 Progresso salvo com segurança")
    except Exception as e:
        _log_progresso(tipo_execucao, f"[ERRO] Falha ao salvar progresso: {e}")


def limpar_progresso_corrompido(tipo_execucao: str) -> bool:
    if not _validar_tipo_execucao(tipo_execucao):
        raise ValueError(f"Tipo de execução não suportado: {tipo_execucao}")
    try:
        progresso_limpo = {"processos_executados": [], "session_active": False, "last_update": datetime.now().isoformat()}
        salvar_progresso_unificado(tipo_execucao, progresso_limpo)
        _log_progresso(tipo_execucao, "🧹 Progresso corrompido/temporário limpo com sucesso")
        return True
    except Exception as e:
        _log_progresso(tipo_execucao, f" Erro ao limpar progresso: {e}")
        return False


def extrair_numero_processo_unificado(driver, tipo_execucao: str) -> Optional[str]:
    if not _validar_tipo_execucao(tipo_execucao):
        raise ValueError(f"Tipo de execução não suportado: {tipo_execucao}")
    try:
        url = driver.current_url
        if "processo/" in url:
            match = re.search(r"processo/(\d+)", url)
            if match:
                numero_limpo = match.group(1)
                _log_progresso(tipo_execucao, f" Número extraído da URL: {numero_limpo}", numero_limpo)
                return numero_limpo
        if tipo_execucao == 'pec':
            try:
                numero_js = driver.execute_script("""
                    var textoCompleto = document.body.innerText || document.body.textContent || '';
                    var matches = textoCompleto.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g);
                    if (matches && matches.length > 0) {
                        return matches[0].replace(/[^\\d]/g, '');
                    }
                    var titulo = document.title;
                    var matchTitulo = titulo.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
                    if (matchTitulo) {
                        return matchTitulo[0].replace(/[^\\d]/g, '');
                    }
                    return null;
                """)
                if numero_js:
                    _log_progresso(tipo_execucao, f" Número extraído via JavaScript: {numero_js}", numero_js)
                    return numero_js
            except Exception as js_e:
                _log_progresso(tipo_execucao, f" Erro no JavaScript de extração: {js_e}")
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho, .numero-processo')
            for elemento in candidatos:
                texto = elemento.text.strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_limpo = re.sub(r'[^\d]', '', match.group(1))
                    _log_progresso(tipo_execucao, f" Número extraído do elemento: {numero_limpo}", numero_limpo)
                    return numero_limpo
        except Exception as inner_e:
            _log_progresso(tipo_execucao, f" Erro ao buscar por seletores: {inner_e}")
        _log_progresso(tipo_execucao, " Nenhum número de processo encontrado")
        return None
    except Exception as e:
        _log_progresso(tipo_execucao, f"[ERRO] Falha ao extrair número do processo: {e}")
        return None


def verificar_acesso_negado_unificado(driver, tipo_execucao: str) -> bool:
    if not _validar_tipo_execucao(tipo_execucao):
        raise ValueError(f"Tipo de execução não suportado: {tipo_execucao}")
    try:
        url_atual = driver.current_url
        acesso_negado = "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower()
        if acesso_negado:
            _log_progresso(tipo_execucao, "🚫 Acesso negado detectado")
        return acesso_negado
    except Exception as e:
        _log_progresso(tipo_execucao, f"[ERRO] Falha ao verificar acesso negado: {e}")
        return False


def processo_ja_executado_unificado(numero_processo: str, progresso: Dict[str, Any]) -> bool:
    if not numero_processo:
        return False
    executados = progresso.get("processos_executados", [])
    if numero_processo and re.match(r'^\d{20}$', numero_processo):
        n = numero_processo
        numero_processo = f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:]}"
    return numero_processo in executados


def marcar_processo_executado_unificado(tipo_execucao: str, numero_processo: str, progresso: Dict[str, Any], sucesso: bool = True) -> None:
    if not numero_processo or not isinstance(numero_processo, str):
        _log_progresso(tipo_execucao, " Número do processo inválido, ignorando marcação")
        return
    numero_processo = numero_processo.strip()
    if not numero_processo:
        _log_progresso(tipo_execucao, " Número do processo vazio, ignorando marcação")
        return
    if re.match(r'^\d{20}$', numero_processo):
        n = numero_processo
        numero_processo = f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:]}"
        _log_progresso(tipo_execucao, f" Número normalizado para CNJ: {numero_processo}")
    if not re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', numero_processo):
        _log_progresso(tipo_execucao, f" Formato de número do processo inválido: {numero_processo}")
        return
    modificado = False
    if sucesso:
        if numero_processo not in progresso.get("processos_executados", []):
            progresso.setdefault("processos_executados", []).append(numero_processo)
            modificado = True
            _log_progresso(tipo_execucao, " Processo marcado como executado", numero_processo)
        else:
            _log_progresso(tipo_execucao, " Processo já estava marcado como executado", numero_processo)
    else:
        _log_progresso(tipo_execucao, " Processo não marcado (falha - será reexecutado)", numero_processo)
    if modificado:
        salvar_progresso_unificado(tipo_execucao, progresso)
    else:
        _log_progresso(tipo_execucao, "ℹ Nenhuma modificação no progresso", numero_processo)


def executar_com_monitoramento_unificado(tipo_execucao: str, driver, numero_processo: Optional[str], funcao_processamento: Callable, *args, suppress_load_log: bool = False, **kwargs) -> Tuple[bool, Optional[str]]:
    if not _validar_tipo_execucao(tipo_execucao):
        raise ValueError(f"Tipo de execução não suportado: {tipo_execucao}")
    progresso = carregar_progresso_unificado(tipo_execucao, suppress_load_log=suppress_load_log)
    numero_processo_extraido = numero_processo
    if not numero_processo_extraido:
        numero_processo_extraido = extrair_numero_processo_unificado(driver, tipo_execucao)
    if not numero_processo_extraido:
        _log_progresso(tipo_execucao, " Não foi possível extrair número do processo")
        return False, None
    if processo_ja_executado_unificado(numero_processo_extraido, progresso):
        _log_progresso(tipo_execucao, "⏭ Processo já executado anteriormente", numero_processo_extraido)
        return True, numero_processo_extraido
    if verificar_acesso_negado_unificado(driver, tipo_execucao):
        _log_progresso(tipo_execucao, "🚫 Acesso negado detectado", numero_processo_extraido)
        marcar_processo_executado_unificado(tipo_execucao, numero_processo_extraido, progresso, sucesso=False)
        return False, numero_processo_extraido
    _log_progresso(tipo_execucao, "▶ Iniciando processamento", numero_processo_extraido)
    try:
        resultado = funcao_processamento(driver, *args, **kwargs)
        if isinstance(resultado, tuple) and len(resultado) >= 1:
            sucesso = bool(resultado[0])
        else:
            sucesso = bool(resultado)
        marcar_processo_executado_unificado(tipo_execucao, numero_processo_extraido, progresso, sucesso=sucesso)
        if sucesso:
            _log_progresso(tipo_execucao, " Processamento concluído com sucesso", numero_processo_extraido)
        else:
            _log_progresso(tipo_execucao, " Processamento falhou", numero_processo_extraido)
        return sucesso, numero_processo_extraido
    except Exception as e:
        erro_msg = str(e)
        _log_progresso(tipo_execucao, f"💥 Erro durante processamento: {erro_msg}", numero_processo_extraido)
        try:
            import traceback
            traceback.print_exc()
        except Exception:
            pass
        if 'RESTART_' in erro_msg.upper():
            _log_progresso(tipo_execucao, " 🚨 RESTART_* detectado — propagando para orquestrador", numero_processo_extraido)
            raise
        erros_temporarios = ["timeout", "stale element", "element not found", "connection", "network", "unreachable"]
        erro_temporario = any(temp_err.lower() in erro_msg.lower() for temp_err in erros_temporarios)
        if erro_temporario:
            _log_progresso(tipo_execucao, " Erro temporário detectado, não marcando como erro permanente", numero_processo_extraido)
            return False, numero_processo_extraido
        else:
            _log_progresso(tipo_execucao, " Erro permanente, marcando processo como erro", numero_processo_extraido)
            marcar_processo_executado_unificado(tipo_execucao, numero_processo_extraido, progresso, sucesso=False)
            return False, numero_processo_extraido


# Compatibilidade: funções legadas
def carregar_progresso_p2b():
    return carregar_progresso_unificado('p2b')

def salvar_progresso_p2b(progresso):
    salvar_progresso_unificado('p2b', progresso)

def extrair_numero_processo_p2b(driver):
    return extrair_numero_processo_unificado(driver, 'p2b')

def verificar_acesso_negado_p2b(driver):
    return verificar_acesso_negado_unificado(driver, 'p2b')

def processo_ja_executado_p2b(numero_processo, progresso):
    return processo_ja_executado_unificado(numero_processo, progresso)

def marcar_progresso_executado_p2b(numero_processo, progresso):
    marcar_progresso_executado_unificado('p2b', numero_processo, progresso, sucesso=True)

# M1 aliases
def carregar_progresso():
    return carregar_progresso_unificado('m1')

def salvar_progresso(progresso):
    salvar_progresso_unificado('m1', progresso)

def extrair_numero_processo(driver):
    return extrair_numero_processo_unificado(driver, 'm1')

def verificar_acesso_negado(driver):
    return verificar_acesso_negado_unificado(driver, 'm1')

def processo_ja_executado(numero_processo, progresso):
    return processo_ja_executado_unificado(numero_processo, progresso)

def marcar_progresso_executado(numero_processo, progresso):
    marcar_progresso_executado_unificado('m1', numero_processo, progresso, sucesso=True)

# Mandado
def carregar_progresso_mandado():
    return carregar_progresso_unificado('mandado')

def salvar_progresso_mandado(progresso):
    salvar_progresso_unificado('mandado', progresso)

def extrair_numero_processo_mandado(driver):
    return extrair_numero_processo_unificado(driver, 'mandado')

def verificar_acesso_negado_mandado(driver):
    return verificar_acesso_negado_unificado(driver, 'mandado')

def processo_ja_executado_mandado(numero_processo, progresso):
    return processo_ja_executado_unificado(numero_processo, progresso)

def marcar_progresso_executado_mandado(numero_processo, progresso):
    marcar_progresso_executado_unificado('mandado', numero_processo, progresso, sucesso=True)


class ProgressoUnificado:
    def __init__(self, tipo: str):
        if not _validar_tipo_execucao(tipo):
            raise ValueError(f"Tipo de execução inválido para ProgressoUnificado: {tipo}")
        self.tipo = tipo

    def carregar_progresso(self):
        return carregar_progresso_unificado(self.tipo)

    def salvar_progresso(self, progresso):
        return salvar_progresso_unificado(self.tipo, progresso)

    def processo_ja_executado(self, numero_processo: str, progresso: Optional[Dict[str, Any]] = None) -> bool:
        if progresso is None:
            progresso = self.carregar_progresso()
        return processo_ja_executado_unificado(numero_processo, progresso)

    def marcar_progresso_executado(self, numero_processo: str, status: str = "SUCESSO", detalhes: Optional[str] = None, progresso: Optional[Dict[str, Any]] = None):
        if progresso is None:
            progresso = self.carregar_progresso()
        sucesso = True if (status or "").upper() == "SUCESSO" else False
        marcar_progresso_executado_unificado(self.tipo, numero_processo, progresso, sucesso=sucesso)
        return progresso

    def marcar_processo_executado(self, numero_processo: str, status: str = "SUCESSO", detalhes: Optional[str] = None, progresso: Optional[Dict[str, Any]] = None):
        return self.marcar_progresso_executado(numero_processo, status, detalhes, progresso)
