def _executar_com_reset(driver, executor):
    resultado = executor(driver)
    resetar_driver(driver)
    return resultado


"""
x.py - Orquestrador Unificado PJEPlus (100% STANDALONE)
=========================================================
Consolidao completa e independente de 1.py, 1b.py, 2.py, 2b.py.
NO depende de nenhum dos scripts originais.

Menu 1: Selecionar Ambiente/Driver
  - A: PC + Visvel (1.py)
  - B: PC + Headless (1b.py)
  - C: VT + Visvel (2.py)
  - D: VT + Headless (2b.py)

Menu 2: Selecionar Fluxo de Execuo
    - A: Bloco Completo (Mandado  Prazo  PEC)
    - B: Mandado Isolado
    - C: Prazo Isolado
    - D: P2B Isolado
    - E: PEC Isolado

Autor: Sistema PJEPlus
Data: 04/12/2025
"""

import sys
import time
import logging
import os
from datetime import datetime
from pprint import pformat
from typing import Dict, Any, Optional, Tuple, Callable
from Fix.tipos import ResultadoFluxo
from enum import Enum
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# Imports dos módulos refatorados
from Fix.core import finalizar_driver as finalizar_driver_fix, criar_driver_pc, criar_driver_vt
from Fix.utils import login_cpf
from Prazo import loop_prazo
from PEC.orquestrador import executar_fluxo_novo_simplificado as pec_fluxo_api
from Mandado.entrada_api import processar_mandados_devolvidos_api

from Fix.log import logger

# Imports de fluxos orquestrados — movidos para o topo (Task 9)
from bianca.triagem_engine import run_triagem
from Peticao.runtime_pet import run_pet
from Prazo.p2b_gateway import processar_gigs_sem_prazo_p2b, testar_gigs_sem_prazo

# ============================================================================
# CONFIGURAES GLOBAIS
# ============================================================================

# Diretrio de logs
LOG_DIR = "logs_execucao"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')


class DriverType(Enum):
    """Tipos de drivers suportados"""
    PC_VISIBLE = "pc_visible"
    PC_HEADLESS = "pc_headless"
    VT_VISIBLE = "vt_visible"
    VT_HEADLESS = "vt_headless"


# ============================================================================
# CAPTURA DE PRINTS (TEEOUTPUT)
# ============================================================================

class TeeOutput:
    """Captura stdout/stderr para arquivo e console"""
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log_file = open(file_path, 'a', encoding='utf-8')
        
    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
        
    def close(self):
        self.log_file.close()
        sys.stdout = self.terminal


# ============================================================================
# CRIAR E LOGAR DRIVER
# ============================================================================

def criar_e_logar_driver(driver_type: DriverType) -> Optional[Any]:
    """Cria driver apropriado e faz login"""

    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]

    logger.debug("criando driver: %s", driver_type.value)

    try:
        # Criar driver
        if vt_mode:
            driver = criar_driver_vt(headless=headless)
        else:
            driver = criar_driver_pc(headless=headless)

        if not driver:
            logger.error("ERRO em criar_e_logar_driver: falha ao criar driver")
            return None

        # Login
        logger.debug("fazendo login...")
        if not login_cpf(driver):
            logger.error("ERRO em criar_e_logar_driver: falha no login")
            finalizar_driver_fix(driver)
            return None

        # Driver criado e logado com sucesso (silencioso)
        return driver

    except Exception as e:
        logger.error("ERRO em criar_e_logar_driver: %s: %s", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# FUNES DE EXECUO
# ============================================================================

def normalizar_resultado(resultado: Any) -> ResultadoFluxo:
    """Normaliza retorno para dict padro"""
    if isinstance(resultado, dict):
        return resultado
    if isinstance(resultado, bool):
        return {"sucesso": resultado, "status": "OK" if resultado else "ERRO"}
    if resultado is None:
        return {"sucesso": False, "status": "ERRO", "erro": "Mdulo retornou None"}
    return {"sucesso": False, "status": "ERRO", "erro": str(resultado)}


def _executar_fluxo(nome: str, fn: Callable[[Any], Any], driver: Any,
                    normalizar: bool = True, on_none_error: Optional[ResultadoFluxo] = None) -> ResultadoFluxo:
    """Wrapper unificado para execução de fluxos.

    Args:
        nome: Nome do fluxo (para logs)
        fn: Função que recebe driver e retorna resultado
        driver: Driver do Selenium
        normalizar: Se True, normaliza o resultado com normalizar_resultado()
        on_none_error: Dict usado quando fn retorna None (padrão: gera erro genérico)
    """
    start_time = time.time()
    try:
        resultado = fn(driver)
        if resultado is None:
            if on_none_error is not None:
                resultado = on_none_error
            else:
                resultado = {"sucesso": False, "status": "ERRO", "erro": f"{nome} retornou None"}
        elif normalizar:
            resultado = normalizar_resultado(resultado)
        resultado["tempo"] = time.time() - start_time
        status = "OK" if resultado.get("sucesso", False) else "FALHA"
        logger.info("[%s] %s (%.1fs)", nome.upper(), status, resultado['tempo'])
        if nome.lower() in {"triagem", "domicilio_eletronico"}:
            logger.info("[%s] resultado completo:\n%s",
                        nome.upper(),
                        pformat(resultado, width=120, sort_dicts=False))
        return resultado
    except Exception as e:
        tempo = time.time() - start_time
        # Erro ja foi logado pela funcao real (R5)
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": f"{type(e).__name__}: {e}", "tempo": tempo}


def resetar_driver(driver) -> bool:
    """Reseta driver entre módulos"""
    try:
        logger.debug("resetando driver...")

        # Fechar abas com acesso-negado antes de qualquer outra operacao
        fechadas = _limpar_acesso_negado(driver)
        if fechadas:
            logger.info("[X] resetar_driver: %d aba(s) acesso-negado fechadas", fechadas)

        # Fechar abas extras
        abas = driver.window_handles
        if len(abas) > 1:
            for aba in abas[1:]:
                try:
                    driver.switch_to.window(aba)
                    driver.close()
                except Exception as e:
                    logger.warning("ERRO em resetar_driver: %s: %s", type(e).__name__, e)
            driver.switch_to.window(abas[0])

        # Resetar zoom
        driver.execute_script("document.body.style.zoom='100%'")

        # Navegar para página inicial
        driver.get("https://pje.trt2.jus.br/pjekz/")
        try:
            WebDriverWait(driver, 5).until(EC.url_contains("pjekz"))
        except Exception:
            pass

        logger.debug("driver resetado")
        return True

    except Exception as e:
        logger.error("ERRO em resetar_driver: %s: %s", type(e).__name__, e)
        return False


def executar_bloco_completo(driver, driver_type=None) -> Dict[str, Any]:
    """Bloco Completo: Mandado + Prazo + P2B + PEC — resiliente a falhas de driver."""
    resultados = {
        "mandado": None,
        "prazo": None,
        "p2b": None,
        "pec": None,
        "sucesso_geral": False
    }

    def _driver_vivo(d):
        try:
            _ = d.window_handles
            return True
        except Exception:
            return False

    def _recriar(nome_modulo):
        logger.warning("[BLOCO] driver perdido apos %s — recriando...", nome_modulo)
        if driver_type is None:
            logger.error("[BLOCO] driver_type nao informado — impossivel recriar")
            return None
        try:
            finalizar_driver_fix(driver)
        except Exception:
            pass
        novo = criar_e_logar_driver(driver_type)
        if novo:
            logger.info("[BLOCO] driver recriado com sucesso")
        else:
            logger.error("[BLOCO] falha ao recriar driver — modulos restantes serao pulados")
        return novo

    # ── Mandado
    try:
        resultados["mandado"] = _executar_com_reset(driver, executar_mandado)
    except Exception as e:
        resultados["mandado"] = {"sucesso": False, "status": "ERRO_DRIVER", "erro": str(e)}
        logger.error("[BLOCO] mandado: excecao nao capturada: %s", e)
    if not _driver_vivo(driver):
        driver = _recriar("mandado")
        if not driver:
            return resultados

    # ── Prazo
    try:
        resultados["prazo"] = _executar_com_reset(driver, executar_prazo)
    except Exception as e:
        resultados["prazo"] = {"sucesso": False, "status": "ERRO_DRIVER", "erro": str(e)}
        logger.error("[BLOCO] prazo: excecao nao capturada: %s", e)
    if not _driver_vivo(driver):
        driver = _recriar("prazo")
        if not driver:
            return resultados

    # ── P2B
    try:
        resultados["p2b"] = _executar_com_reset(driver, executar_p2b)
    except Exception as e:
        resultados["p2b"] = {"sucesso": False, "status": "ERRO_DRIVER", "erro": str(e)}
        logger.error("[BLOCO] p2b: excecao nao capturada: %s", e)
    if not _driver_vivo(driver):
        driver = _recriar("p2b")
        if not driver:
            return resultados

    # ── PEC
    try:
        resultados["pec"] = executar_pec(driver)
    except Exception as e:
        resultados["pec"] = {"sucesso": False, "status": "ERRO_DRIVER", "erro": str(e)}
        logger.error("[BLOCO] pec: excecao nao capturada: %s", e)

    todos_sucesso = all([
        (resultados["mandado"] or {}).get("sucesso", False),
        (resultados["prazo"] or {}).get("sucesso", False),
        (resultados["p2b"] or {}).get("sucesso", False),
        (resultados["pec"] or {}).get("sucesso", False),
    ])
    resultados["sucesso_geral"] = todos_sucesso
    resultados["_driver"] = driver  # driver final (pode ter sido recriado)

    m_status = "OK" if (resultados["mandado"] or {}).get("sucesso", False) else "FALHA"
    p_status = "OK" if (resultados["prazo"] or {}).get("sucesso", False) else "FALHA"
    b_status = "OK" if (resultados["p2b"] or {}).get("sucesso", False) else "FALHA"
    pec_status = "OK" if (resultados["pec"] or {}).get("sucesso", False) else "FALHA"
    logger.info("[BLOCO] mandado=%s prazo=%s p2b=%s pec=%s sucesso_geral=%s",
                m_status, p_status, b_status, pec_status,
                "OK" if todos_sucesso else "FALHAS_PARCIAIS")
    return resultados


def executar_mandado(driver) -> Dict[str, Any]:
    """Mandado Isolado — API (sem navegação DOM inicial)"""
    def _fluxo(d):
        resultado = normalizar_resultado(processar_mandados_devolvidos_api(d))
        if not resultado.get("sucesso"):
            logger.warning("[MANDADO] falha: %s", resultado.get('erro', 'Desconhecido'))
        return resultado

    return _executar_fluxo("Mandado", _fluxo, driver)


def executar_prazo(driver) -> Dict[str, Any]:
    """Prazo Isolado — loop ciclo1+2+3 + P2B (sempre executa p2b mesmo se loop falhar)."""
    def _fluxo(d):
        resultado_loop = {"sucesso": False, "erro": "nao executado"}
        resultado_p2b = {"sucesso": False, "erro": "nao executado"}

        try:
            logger.debug("[PRAZO] executando loop_prazo (ciclo1 + ciclo2 + ciclo3)...")
            resultado_loop = loop_prazo(d)
            resultado_loop = normalizar_resultado(resultado_loop)
            if not resultado_loop.get("sucesso"):
                logger.warning("[PRAZO] loop_prazo com falha: %s — continuando com P2B",
                              resultado_loop.get('erro'))
        except Exception as e:
            logger.warning("[PRAZO] excecao no loop_prazo: %s — continuando com P2B", e)
            resultado_loop = {"sucesso": False, "erro": str(e)}

        try:
            logger.debug("[PRAZO] executando P2B (atividades sem prazo XS)...")
            resultado_p2b = executar_p2b(d)
            resultado_p2b = normalizar_resultado(resultado_p2b)
            if not resultado_p2b.get("sucesso"):
                logger.warning("[PRAZO] P2B com falha: %s", resultado_p2b.get('erro'))
        except Exception as e:
            logger.warning("[PRAZO] excecao no P2B: %s", e)
            resultado_p2b = {"sucesso": False, "erro": str(e)}

        sucesso_geral = resultado_loop.get("sucesso", False) and resultado_p2b.get("sucesso", False)

        return {
            "sucesso": sucesso_geral,
            "status": "SUCESSO" if sucesso_geral else "PARCIAL",
            "loop_prazo": resultado_loop,
            "p2b": resultado_p2b,
        }

    return _executar_fluxo("Prazo", _fluxo, driver, normalizar=False)


def executar_pec(driver, data_minima: Optional[str] = None) -> Dict[str, Any]:
    """PEC Isolado — API modular (sem navegação DOM inicial)"""
    def _fluxo(d):
        resultado = pec_fluxo_api(d, data_minima=data_minima)
        total = resultado.get('total', 0)
        erros = resultado.get('erro', 0)
        sucessos = resultado.get('sucesso_count', total - erros)
        logger.info("[PEC] total=%s sucesso=%s erro=%s", total, sucessos, erros)
        return resultado

    return _executar_fluxo("PEC", _fluxo, driver)


def _limpar_acesso_negado(driver) -> int:
    """Fecha abas com URL acesso-negado. Retorna numero de abas fechadas."""
    fechadas = 0
    try:
        handles = list(driver.window_handles)
        principal = handles[0] if handles else None
        for h in handles[1:]:
            try:
                driver.switch_to.window(h)
                if "acesso-negado" in (driver.current_url or "").lower():
                    logger.info("[X] Fechando aba acesso-negado: %s", driver.current_url)
                    driver.close()
                    fechadas += 1
            except Exception:
                pass
        if principal:
            try:
                driver.switch_to.window(principal)
            except Exception:
                pass
    except Exception as e:
        logger.warning("[X] _limpar_acesso_negado erro: %s", e)
    return fechadas


def executar_triagem(driver) -> Dict[str, Any]:
    """Triagem Isolada — fluxo completo com análise pós-triagem e ações por alerta."""
    def _fluxo(d):
        resultado = run_triagem(d)
        if resultado is None:
            return None
        logger.info("[TRIAGEM] processados=%s total=%s sucesso=%s",
                    resultado.get('processados', 0),
                    resultado.get('total', '?'),
                    resultado.get('sucesso_count', '?'))

        if resultado.get("critical_stop"):
            motivo = resultado.get("critical_reason", "?")
            logger.warning("[TRIAGEM] Parada critica (%s) — resetando driver e reiniciando...", motivo)
            _limpar_acesso_negado(d)
            resetar_driver(d)

            resultado2 = run_triagem(d)
            if resultado2 is None:
                return None
            logger.info("[TRIAGEM] Retry: processados=%s total=%s sucesso=%s",
                        resultado2.get('processados', 0),
                        resultado2.get('total', '?'),
                        resultado2.get('sucesso_count', '?'))
            return resultado2

        return resultado

    return _executar_fluxo("Triagem", _fluxo, driver,
                          on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_triagem retornou None"})


def executar_pet(driver) -> Dict[str, Any]:
    """Petição Isolada — fluxo completo de petições (escaninho)."""
    def _fluxo(d):
        resultado = run_pet(d)
        if resultado is None:
            return None
        return resultado

    return _executar_fluxo("Petição", _fluxo, driver,
                          on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_pet retornou None"})


def executar_domicilio_eletronico(driver) -> Dict[str, Any]:
    """Domicilio Eletronico — run_dom_api (API: conhecimento + chips DOM 274/275/302)."""
    def _fluxo(d):
        from bianca.dom_engine import run_dom_api
        resultado = run_dom_api(d)
        if resultado is None:
            return None
        return resultado

    return _executar_fluxo("Domicilio_Eletronico", _fluxo, driver,
                          on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_dom_api retornou None"})


def executar_p2b(driver) -> Dict[str, Any]:
    """P2B Isolado (API GIGS sem prazo XS + processamento por processo)"""
    def _fluxo(d):
        # Executar API + fluxo de cada processo (substitui lista antiga)
        logger.debug("[P2B] executando fluxo_prazo via API GIGS sem prazo XS...")
        atividades = testar_gigs_sem_prazo(d, tamanho_pagina=100)
        logger.debug("[P2B] processos encontrados: %s", len(atividades))
        if atividades:
            numeros_processos = [item.get('processo', {}).get('numero') or item.get('numeroProcesso') or item.get('numero') for item in atividades]
            logger.debug("[P2B] numeros dos processos: %s", numeros_processos)

        resultado = processar_gigs_sem_prazo_p2b(d, tamanho_pagina=100, max_processos=0)

        if resultado.get('critical_stop'):
            logger.warning("[P2B] Sessao expirada (401) — resetando driver e retentando")
            resetar_driver(d)
            resultado = processar_gigs_sem_prazo_p2b(d, tamanho_pagina=100, max_processos=0)

        logger.debug("[P2B] processamento individual concluido")
        sucesso = resultado.get('sucesso', False)
        return {
            'sucesso': sucesso,
            'status': 'SUCESSO' if sucesso else 'FALHA',
            'detalhes': resultado,
        }

    return _executar_fluxo("P2B", _fluxo, driver)


# ============================================================================
# MENUS
# ============================================================================

def menu_ambiente() -> Optional[Tuple[DriverType, bool]]:
    """Menu 1: Selecionar Ambiente (versão limpa)."""
    print("\nAmbiente:")
    print("A - PC Visível")
    print("B - PC Headless")
    print("C - VT Visível")
    print("D - VT Headless")
    print("X - Cancelar")
    opcao = input("> ").strip().upper()

    debug_mode = opcao.endswith('D') and len(opcao) > 1
    if debug_mode:
        opcao = opcao[0]

    if opcao == "A":
        return DriverType.PC_VISIBLE, debug_mode
    elif opcao == "B":
        return DriverType.PC_HEADLESS, debug_mode
    elif opcao == "C":
        return DriverType.VT_VISIBLE, debug_mode
    elif opcao == "D":
        return DriverType.VT_HEADLESS, debug_mode
    elif opcao == "X":
        return None
    else:
        return None


def menu_execucao() -> Optional[str]:
    """Menu 2: Selecionar Fluxo (versão limpa)."""
    print("\nFluxo:")
    print("A - Bloco Completo")
    print("B - Mandado")
    print("C - Prazo + P2B")
    print("D - P2B")
    print("E - PEC")
    print("F - Triagem")
    print("G - Petição")
    print("H - Domicílio Eletrônico")
    print("X - Cancelar")
    opcao = input("> ").strip().upper()

    if opcao in ["A","B","C","D","E","F","G","H","X"]:
        return opcao if opcao != "X" else None
    return None


def selecionar_ambiente_e_fluxo() -> Optional[Tuple[DriverType, bool, str]]:
    """Seleciona ambiente e fluxo, repetindo apenas quando o fluxo e cancelado."""
    while True:
        resultado_menu = menu_ambiente()
        if not resultado_menu:
            return None

        driver_type, debug_mode = resultado_menu

        fluxo = menu_execucao()
        if not fluxo:
            logger.info("cancelado")
            continue

        return driver_type, debug_mode, fluxo


# ============================================================================
# CONFIGURAO DE LOGGING
# ============================================================================

def configurar_logging(driver_type: DriverType, debug: bool = False):
    """Configura logging baseado no tipo de driver"""
    
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]
    
    # Suprimir logs ruidosos do urllib3.connectionpool sempre (evita flood no terminal)
    # e reduzir logs do Selenium quando em headless
    logging.getLogger('urllib3.connectionpool').disabled = True
    if headless:
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
    
    # Arquivo de log
    env_name = "VT" if vt_mode else "PC"
    mode_name = "Headless" if headless else "Visible"
    log_file = os.path.join(LOG_DIR, f"x_{env_name}_{mode_name}_{TIMESTAMP}.log")
    
    # Configurar TeeOutput para capturar print()
    tee = TeeOutput(log_file)
    sys.stdout = tee
    
    # Configurar logging (para logger.info(), logger.error(), etc.)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remover handlers antigos se existirem
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Adicionar FileHandler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', 
                                 datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Adicionar StreamHandler para console (vai passar por TeeOutput)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    class _DestaqueConsoleFormatter(logging.Formatter):
        def format(self, record):
            base = '[%(name)s] %(message)s' % {'name': record.name, 'message': record.getMessage()}
            if record.levelno >= logging.ERROR:
                sep = '=' * 60
                return '\n%s\n%s\n%s' % (sep, base, sep)
            return base

    console_handler.setFormatter(_DestaqueConsoleFormatter())
    root_logger.addHandler(console_handler)

    # Handler exclusivo para erros → erro.md na raiz
    _ERRO_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'erro.md')
    erro_handler = logging.FileHandler(_ERRO_MD, encoding='utf-8', mode='a')
    erro_handler.setLevel(logging.ERROR)

    class _ErroMdFormatter(logging.Formatter):
        def format(self, record):
            msg = record.getMessage()
            if record.exc_info:
                import traceback
                msg += '\n```\n' + ''.join(traceback.format_exception(*record.exc_info)).rstrip() + '\n```'
            return (
                '- **%s** `[%s]` `%s:%s` — %s\n' % (
                    record.levelname,
                    self.formatTime(record, '%H:%M:%S'),
                    record.module,
                    record.funcName,
                    msg,
                )
            )

    erro_handler.setFormatter(_ErroMdFormatter())
    root_logger.addHandler(erro_handler)

    # Cabeçalho da sessão no erro.md
    with open(_ERRO_MD, 'a', encoding='utf-8') as _f:
        import datetime as _dt
        _f.write('\n## Execução %s — %s\n\n' % (
            _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            os.path.basename(log_file),
        ))

    return log_file, tee


FLOW_HANDLERS = {
    "A": executar_bloco_completo,
    "B": executar_mandado,
    "C": executar_prazo,
    "D": executar_p2b,
    "E": executar_pec,
    "F": executar_triagem,
    "G": executar_pet,
    "H": executar_domicilio_eletronico,
}


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funo principal"""
    driver = None
    tee_output = None
    log_file = None
    try:
        try:
            from Fix.otimizacao_wrapper import inicializar_otimizacoes
            inicializar_otimizacoes()
        except Exception:
            pass

        selecao = selecionar_ambiente_e_fluxo()
        if not selecao:
            logger.info("cancelado")
            return

        driver_type, debug_mode, fluxo = selecao

        # Configurar logging
        log_file, tee_output = configurar_logging(driver_type, debug=debug_mode)

        logger.info("ORQUESTRADOR UNIFICADO PJEPlus")
        logger.info("data/hora: %s", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        logger.info("ambiente: %s", driver_type.value)
        logger.info("fluxo: %s", fluxo)
        logger.info("log: %s", log_file)

        driver = criar_e_logar_driver(driver_type)
        if not driver:
            logger.error("ERRO em main: falha ao inicializar driver/logar")
            return

        inicio = datetime.now()
        resultado = None
        handler = FLOW_HANDLERS.get(fluxo)
        if not handler:
            raise ValueError(f"Fluxo invalido: {fluxo}")

        if fluxo == "A":
            resultado = executar_bloco_completo(driver, driver_type=driver_type)
            # Se driver foi recriado internamente, garantir que seja finalizado
            _driver_final = resultado.pop("_driver", None)
            if _driver_final is not None and _driver_final is not driver:
                try:
                    finalizar_driver_fix(_driver_final)
                except Exception:
                    pass
        else:
            resultado = handler(driver)
        tempo_total = (datetime.now() - inicio).total_seconds()

        # Relatorio final
        if resultado:
            if 'sucesso_geral' in resultado:
                logger.info("sucesso geral: %s", resultado['sucesso_geral'])
            elif 'sucesso' in resultado:
                logger.info("sucesso: %s", resultado['sucesso'])
        logger.info("tempo total: %.2fs", tempo_total)
        logger.info("encerrando")

    except KeyboardInterrupt:
        logger.warning("interrompido pelo usuario — finalizando de forma cooperativa")
    except Exception as e:
        logger.error("ERRO em main: %s: %s", type(e).__name__, e)
    
    finally:
        if driver:
            try:
                finalizar_driver_fix(driver)
            except Exception:
                pass
        if tee_output:
            try:
                tee_output.close()
            except Exception:
                pass
        
        #  NOVO: Finalizar otimizaes
        try:
            from Fix.otimizacao_wrapper import finalizar_otimizacoes
            finalizar_otimizacoes()
        except Exception:
            pass


if __name__ == "__main__":
    logger.info("ORQUESTRADOR UNIFICADO PJEPlus (x.py)")
    logger.info("executando como: %s", os.path.basename(__file__))
    logger.info("100%% STANDALONE — nao depende de 1.py, 1b.py, 2.py, 2b.py")

    try:
        main()
    except Exception as e:
        logger.error("ERRO: %s: %s", type(e).__name__, e)
        sys.exit(1)
    finally:
        logger.info("orquestrador finalizado")

    sys.exit(0)
