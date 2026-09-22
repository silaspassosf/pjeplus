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
import shutil
from datetime import date, datetime, timedelta
from pprint import pformat
from typing import Dict, Any, Optional, Tuple, Callable
from Fix.tipos import ResultadoFluxo
from enum import Enum
# WebDriverWait importado lazily em resetar_driver() para garantir shim pjeplay correto
# Imports dos módulos refatorados
from Fix.core import finalizar_driver as finalizar_driver_fix, criar_driver_pc, criar_driver_vt
from Fix.utils import login_cpf, login_manual
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

def _aguardar_login_manual(driver, timeout: int = 900) -> bool:
    """Mantem o browser ABERTO e aguarda o usuario concluir o login manualmente.

    Usado quando o login automatico falha (ex: senha incorreta). O browser NAO
    e fechado — o usuario se autentica na janela aberta e o fluxo continua.
    Retorna True quando detecta sessao ativa; False em timeout/browser morto.
    """
    logger.warning(
        "[LOGIN] Login automatico falhou. Browser mantido ABERTO — "
        "conclua o login manualmente na janela do navegador."
    )
    inicio = time.time()
    from Fix.utils import sessao_oauth_completa
    while time.time() - inicio < timeout:
        try:
            cur = (driver.current_url or '').lower()
        except Exception:
            logger.error("[LOGIN] Browser indisponivel durante espera do login manual.")
            return False
        if sessao_oauth_completa(driver):
            logger.info("[LOGIN] Login manual detectado (%.0fs). Continuando fluxo.",
                        time.time() - inicio)
            try:
                from Fix.utils import SALVAR_COOKIES_AUTOMATICO, salvar_cookies_sessao
                if SALVAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_manual_pos_falha')
            except Exception:
                pass
            return True
        time.sleep(2)
    logger.error("[LOGIN] Timeout (%ds) aguardando login manual.", timeout)
    return False


def _aguardar_sessao_ativa(driver, timeout: int = 60) -> bool:
    """Espera (SEM navegar — não briga com os redirects do PJe/Keycloak) o
    handshake OAuth gravar o access_token no browser após o login automático.
    Se não concluir a tempo, quem chama cai na espera de login manual."""
    from Fix.utils import sessao_oauth_completa
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            if sessao_oauth_completa(driver):
                logger.info("[LOGIN] Sessao OAuth completa confirmada (%.0fs).",
                            time.time() - inicio)
                return True
        except Exception:
            logger.error("[LOGIN] Browser indisponivel ao confirmar sessao.")
            return False
        time.sleep(2)
    logger.error("[LOGIN] access_token nao apareceu em %ds — login automatico "
                 "nao completou (verifique senha/MFA).", timeout)
    return False


def _criar_driver_headless_com_login_visivel(driver_type: DriverType, vt_mode: bool) -> Optional[Any]:
    """Headless login: tenta cookies existentes; se inválidos, abre janela visível
    para o usuário fazer login manual, salva cookies e inicia o driver headless.

    Fluxo:
      1. Cria driver headless e tenta restaurar sessão via cookies salvos.
      2. Se OK → retorna driver headless diretamente.
      3. Se não → abre driver VISÍVEL, aguarda URL de painel/avisos (login manual).
      4. Salva cookies → fecha janela visível.
      5. Cria novo driver headless, aplica cookies → retorna.
    """
    from Fix.utils import verificar_e_aplicar_cookies, salvar_cookies_sessao

    # ── Tentativa 1: headless com cookies existentes ──────────────────────────
    driver_hl = None
    try:
        driver_hl = criar_driver_vt(headless=True) if vt_mode else criar_driver_pc(headless=True)
        if driver_hl and verificar_e_aplicar_cookies(driver_hl):
            if _aguardar_sessao_ativa(driver_hl, timeout=10):
                logger.info("[HEADLESS] Sessao restaurada via cookies — sem login manual necessario.")
                return driver_hl
        if driver_hl:
            try:
                finalizar_driver_fix(driver_hl)
            except Exception:
                pass
            driver_hl = None
    except Exception as e:
        logger.warning("[HEADLESS] Falha ao tentar cookies: %s", e)
        if driver_hl:
            try:
                finalizar_driver_fix(driver_hl)
            except Exception:
                pass

    # ── Tentativa 2: janela visível → login manual → cookies → headless ───────
    logger.info("[HEADLESS] Cookies invalidos/expirados — abrindo janela visivel para login manual.")
    logger.info("[HEADLESS] Faca o login na janela que sera aberta. "
                "O headless iniciara automaticamente apos a deteccao da URL de painel.")
    driver_vis = None
    try:
        driver_vis = criar_driver_vt(headless=False) if vt_mode else criar_driver_pc(headless=False)
        if not driver_vis:
            logger.error("[HEADLESS] Nao foi possivel abrir janela visivel para login.")
            return None

        login_manual(driver_vis)  # aguarda meu-painel OU quadro-avisos/visualizar

        if not _aguardar_sessao_ativa(driver_vis, timeout=30):
            logger.error("[HEADLESS] Sessao OAuth nao completou apos login manual.")
            finalizar_driver_fix(driver_vis)
            return None

        salvar_cookies_sessao(driver_vis, info_extra='login_manual_para_headless')
        logger.info("[HEADLESS] Login concluido — fechando janela visivel e iniciando modo headless.")
        finalizar_driver_fix(driver_vis)
        driver_vis = None
    except Exception as e:
        logger.error("[HEADLESS] Erro no login via janela visivel: %s: %s", type(e).__name__, e)
        if driver_vis:
            try:
                finalizar_driver_fix(driver_vis)
            except Exception:
                pass
        return None

    # ── Criar driver headless final com cookies recém-salvos ──────────────────
    try:
        driver_hl = criar_driver_vt(headless=True) if vt_mode else criar_driver_pc(headless=True)
        if not driver_hl:
            logger.error("[HEADLESS] Falha ao criar driver headless apos login.")
            return None
        verificar_e_aplicar_cookies(driver_hl)
        logger.info("[HEADLESS] Driver headless pronto com sessao autenticada.")
        return driver_hl
    except Exception as e:
        logger.error("[HEADLESS] Erro ao criar driver headless final: %s: %s", type(e).__name__, e)
        return None


def criar_e_logar_driver(driver_type: DriverType) -> Optional[Any]:
    """Cria driver e faz login.

    Para modo headless: tenta cookies existentes; se inválidos, abre janela
    visível para login manual, salva cookies e inicia o headless com a sessão.
    Para modo visível: fluxo original (cookies → login manual no browser).
    """
    headless = driver_type in [DriverType.PC_HEADLESS, DriverType.VT_HEADLESS]
    vt_mode = driver_type in [DriverType.VT_VISIBLE, DriverType.VT_HEADLESS]

    logger.debug("criando driver: %s", driver_type.value)

    if headless:
        return _criar_driver_headless_com_login_visivel(driver_type, vt_mode)

    # ── Modo visível: fluxo original ─────────────────────────────────────────
    try:
        driver = criar_driver_vt(headless=False) if vt_mode else criar_driver_pc(headless=False)

        if not driver:
            logger.error("ERRO em criar_e_logar_driver: falha ao criar driver")
            return None

        if not login_manual(driver):
            logger.error("ERRO em criar_e_logar_driver: login nao concluido")
            if not _aguardar_login_manual(driver):
                finalizar_driver_fix(driver)
                return None

        if not _aguardar_sessao_ativa(driver):
            logger.error("ERRO em criar_e_logar_driver: sessao OAuth nao completou "
                         "(access_token ausente apos o login)")
            if not _aguardar_login_manual(driver):
                finalizar_driver_fix(driver)
                return None

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
        logger.error("[%s] ERRO_EXECUCAO (%.1fs): %s: %s",
                     nome.upper(), tempo, type(e).__name__, e)
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
            from selenium.webdriver.support.ui import WebDriverWait as _WDW
            from selenium.webdriver.support import expected_conditions as _EC
            _WDW(driver, 5).until(_EC.url_contains("pjekz"))
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


def executar_pec(driver, filtro_d1: bool = False, data_minima: Optional[str] = None) -> Dict[str, Any]:
    """PEC Isolado — API modular (sem navegação DOM inicial)"""
    def _fluxo(d):
        resultado = pec_fluxo_api(d, filtro_d1=filtro_d1, data_minima=data_minima)
        total = resultado.get('total', 0)
        erros = resultado.get('erro', 0)
        sucessos = resultado.get('sucesso_count', total - erros)
        logger.info("[PEC] total=%s sucesso=%s erro=%s", total, sucessos, erros)
        return resultado

    resultado = _executar_fluxo("PEC", _fluxo, driver)

    # Driver morto (última janela fechada) no meio do batch: o PEC para no
    # primeiro erro crítico (run_batch stop_on_critical) e sinaliza RESTART_PEC.
    # O batch não deve repetir "Nenhuma janela aberta" em todo processo restante
    # — uma ocorrência basta, e o launcher é resetado para os próximos módulos.
    erro_txt = str(resultado.get('erro') or '')
    if not resultado.get('sucesso') and ('RESTART_PEC' in erro_txt or 'Nenhuma janela aberta' in erro_txt):
        logger.warning("[PEC] Driver morto durante o batch (%s) — resetando driver...", erro_txt[:120])
        _limpar_acesso_negado(driver)
        resetar_driver(driver)
        return {"sucesso": False, "status": "PARCIAL", "erro": erro_txt, "reset_driver": True}

    return resultado


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


# ── Fluxo Citação ─────────────────────────────────────────────────────────────

_PAUTA_ENDPOINT = "/audapi/rest/pje/audpje/pautas"
_ORGAO_JULGADOR_PAUTA = 187  # orgao do bookmarklet de referencia da pauta
_URL_PROCESSO_DETALHE = "https://pje.trt2.jus.br/pjekz/processo/{}/detalhe"
_PAUTA_MAX_DIAS = 30  # teto de dias avancados ao procurar pauta com audiencias


def _proximo_dia_util(a_partir_de) -> "date":
    """Proximo dia util: sexta-feira -> segunda (pula sabado/domingo)."""
    dia = a_partir_de + timedelta(days=1)
    while dia.weekday() >= 5:  # 5=sabado, 6=domingo
        dia += timedelta(days=1)
    return dia


def _audiencia_cogida(tipo: str) -> bool:
    """Mesmo filtro do bookmarklet de pauta: exclui audiencias de
    julgamento e de encerramento de instrucao (substring, como la)."""
    t = (tipo or "").lower()
    return "julgamento" not in t and "encerramento" not in t


def _pauta_dia_seguinte(client) -> list:
    """Busca a pauta a partir do proximo dia util a execucao.

    Se o dia nao tiver audiencias (apos o filtro do bookmarklet), avanca
    dia a dia ate encontrar uma pauta com audiencias (teto _PAUTA_MAX_DIAS).
    """
    dia = _proximo_dia_util(datetime.now().date())
    for _ in range(_PAUTA_MAX_DIAS):
        dia_iso = dia.strftime("%Y-%m-%d")
        params = {
            "dataInicio": dia_iso,
            "dataFim": dia_iso,
            "orgaoJulgador": _ORGAO_JULGADOR_PAUTA,
        }
        logger.info("[CITACAO] >>> GET %s params=%s", _PAUTA_ENDPOINT, params)
        resp = client.gateway_get(_PAUTA_ENDPOINT, params=params)
        if not resp.get("ok"):
            logger.error("[CITACAO] <<< falha na pauta: %s", resp.get("error"))
            return []
        dados = resp.get("data") or []
        lista = dados if isinstance(dados, list) else (
            dados.get("content") or dados.get("resultado") or dados.get("pautas") or [])
        filtradas = [p for p in lista
                     if _audiencia_cogida(p.get("tipoAudiencia"))]
        logger.info("[CITACAO] <<< pauta %s: %d audiencia(s) brutas, %d apos filtro",
                    dia_iso, len(lista), len(filtradas))
        if filtradas:
            return filtradas
        logger.info("[CITACAO] pauta %s vazia (ou so julgamento/encerramento) "
                    "— avancando para o proximo dia util", dia_iso)
        dia = _proximo_dia_util(dia)
    logger.warning("[CITACAO] nenhuma pauta com audiencias em %d dias", _PAUTA_MAX_DIAS)
    return []


def _reclamada_sem_advogado(partes) -> Optional[dict]:
    """Primeira parte do polo PASSIVO sem representantes (advogado), se houver."""
    for pt in (partes or {}).get("PASSIVO") or []:
        if not (pt.get("representantes") or []):
            return pt
    return None


def executar_citacao(driver) -> Dict[str, Any]:
    """Citacao — pauta do proximo dia util -> reclamada sem advogado -> carta (PEC).

    Para cada processo da pauta (dia seguinte; sexta pula para segunda; se a
    pauta vier vazia, avanca ate achar dia com audiencias): consulta as partes
    via API e, nos que tiverem reclamada sem advogado, abre o processo e
    executa a funcao carta de PEC.carta_execucao.
    """
    def _fluxo(d):
        from api import PjeApiClient, session_from_driver
        from Fix.abas import fechar_abas_extras

        sess, trt_host = session_from_driver(d)
        client = PjeApiClient(sess, trt_host)

        # 1) pauta do dia seguinte
        pauta = _pauta_dia_seguinte(client)
        numeros_por_id = {}
        for p in pauta:
            if p.get("idProcesso"):
                numeros_por_id.setdefault(p["idProcesso"], p.get("numeroProcesso") or "")
        ids = list(numeros_por_id.keys())
        logger.info("[CITACAO] processos unicos na pauta: %d -> %s", len(ids), ids)

        # 2) partes por processo (acumulado) — filtro: reclamada sem advogado
        alvos = []
        for pid in ids:
            endpoint = f"/pje-comum-api/api/processos/id/{pid}/partes"
            logger.info("[CITACAO] >>> GET %s", endpoint)
            resp = client.gateway_get(endpoint)
            if not resp.get("ok"):
                logger.error("[CITACAO] <<< falha (%s) — processo pulado", resp.get("error"))
                continue
            partes = resp.get("data") or {}
            ativos = [pt.get("nome") for pt in (partes.get("ATIVO") or [])]
            passivos = [(pt.get("nome"), bool(pt.get("representantes")))
                        for pt in (partes.get("PASSIVO") or [])]
            logger.info("[CITACAO] <<< ATIVO=%s | PASSIVO(nome, tem_adv)=%s", ativos, passivos)
            sem_adv = _reclamada_sem_advogado(partes)
            if sem_adv:
                logger.info("[CITACAO] *** RECLAMADA SEM ADVOGADO: %s (doc=%s) ***",
                            sem_adv.get("nome"), sem_adv.get("documento"))
                alvos.append((pid, numeros_por_id.get(pid) or "", sem_adv.get("nome")))
            else:
                logger.info("[CITACAO] todas as reclamadas com advogado — pulando")

        logger.info("[CITACAO] %d de %d processos com reclamada sem advogado",
                    len(alvos), len(ids))

        # 3) abrir processo e executar carta (identica PEC)
        sucessos = erros = 0
        for pid, numero, reclamada in alvos:
            try:
                numero_limpo = "".join(filter(str.isdigit, str(numero)))
                chave = numero_limpo if len(numero_limpo) == 20 else pid
                url = _URL_PROCESSO_DETALHE.format(chave)
                d.get(url)
                WebDriverWait(d, 15).until(
                    lambda drv: drv.execute_script("return document.readyState") == "complete"
                )
                if "acesso-negado" in (d.current_url or "").lower():
                    raise RuntimeError(f"acesso negado — {reclamada} ({numero or pid})")
                logger.info("[CITACAO] processo aberto: %s (reclamada: %s)", url, reclamada)
                from PEC.carta_execucao import carta
                carta(d)
                sucessos += 1
            except Exception as exc:
                erros += 1
                logger.error("[CITACAO] erro em %s (%s): %s: %s",
                             reclamada, numero or pid, type(exc).__name__, exc)
            finally:
                try:
                    fechar_abas_extras(d)
                except Exception:
                    pass

        logger.info("[CITACAO] total=%d sucesso=%d erro=%d", len(alvos), sucessos, erros)
        return {"sucesso": erros == 0, "status": "OK" if erros == 0 else "PARCIAL",
                "total": len(alvos), "sucesso_count": sucessos, "erro": erros}

    return _executar_fluxo("Citação", _fluxo, driver,
                          on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO",
                                         "erro": "fluxo citacao retornou None"})


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
        falhas = resultado.get('falhas') or []
        if falhas:
            logger.warning("[P2B] %d processo(s) NAO concluido(s) (serao retentados): %s",
                           len(falhas),
                           [(f.get('numero'), f.get('erro')) for f in falhas])
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
    while True:
        print("\nAmbiente:")
        print("A - PC Visível")
        print("B - PC Headless")
        print("C - VT Visível")
        print("D - VT Headless")
        print("X - Cancelar")
        try:
            opcao = input("> ").strip().upper()
        except EOFError:
            return None

        if not opcao:
            continue  # Enter solto / resíduo de buffer: repete, não cancela

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
        # opção inválida: repete o menu


def menu_execucao() -> Optional[str]:
    """Menu 2: Selecionar Fluxo (versão limpa)."""
    while True:
        print("\nFluxo:")
        print("A - Bloco Completo")
        print("B - Mandado")
        print("C - Prazo + P2B")
        print("D - P2B")
        print("E - PEC")
        print("F - Triagem")
        print("G - Petição")
        print("H - Domicílio Eletrônico")
        print("I - Citação")
        print("X - Cancelar")
        try:
            opcao = input("> ").strip().upper()
        except EOFError:
            return None

        if not opcao:
            continue  # Enter solto / resíduo de buffer: repete, não cancela

        if opcao in ["A","B","C","D","E","F","G","H","I","X"]:
            return opcao if opcao != "X" else None
        # opção inválida: repete o menu


def selecionar_ambiente_e_fluxo() -> Optional[Tuple[DriverType, bool, str]]:
    """Seleciona ambiente e fluxo, repetindo apenas quando o fluxo e cancelado.

    Modo nao-interativo (CI/agendamento): definir PJEPLUS_DRIVER e PJEPLUS_FLUXO.
    Ex: PJEPLUS_DRIVER=PC_HEADLESS PJEPLUS_FLUXO=A py pw.py
    """
    _env_driver = os.environ.get("PJEPLUS_DRIVER")
    _env_fluxo = os.environ.get("PJEPLUS_FLUXO")
    if _env_driver and _env_fluxo:
        try:
            dt = DriverType[_env_driver]
            if _env_fluxo in FLOW_HANDLERS:
                logger.info("[ENV] PJEPLUS_DRIVER=%s PJEPLUS_FLUXO=%s — pulando menus.",
                            _env_driver, _env_fluxo)
                return dt, False, _env_fluxo
        except KeyError:
            logger.warning("[ENV] PJEPLUS_DRIVER='%s' invalido — usando menus interativos.", _env_driver)

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

_ERRO_MD_LIMITE_BYTES = 1_500_000  # ~1.5MB


def _rotacionar_erro_md(caminho_erro_md):
    """Se erro.md já existir e ultrapassar o limite de tamanho, arquiva o
    conteúdo atual em logs_execucao/erro_AAAAMMDD_HHMMSS.md e libera um
    erro.md novo e limpo para a sessão atual."""
    if not os.path.exists(caminho_erro_md):
        return
    if os.path.getsize(caminho_erro_md) < _ERRO_MD_LIMITE_BYTES:
        return
    destino = os.path.join(LOG_DIR, f"erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    try:
        shutil.move(caminho_erro_md, destino)
    except OSError:
        pass  # se falhar, segue com o erro.md existente (append normal)


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

    # Handler exclusivo para erros → erro.md na raiz (com rotação por tamanho)
    _ERRO_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'erro.md')
    _rotacionar_erro_md(_ERRO_MD)
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
    "I": executar_citacao,
}


PAINEL_URL = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'


def _menu_proximo_fluxo() -> Optional[str]:
    """Após finalizar um fluxo, pergunta qual o próximo (sem recriar driver).

    Retorna None automaticamente em modo nao-interativo (CI/env var/headless sem tty).
    """
    if os.environ.get("PJEPLUS_FLUXO") or not sys.stdin.isatty():
        return None  # modo CI: encerrar apos o fluxo

    print()
    print('─' * 50)
    print('  FLUXO CONCLUÍDO — driver mantido aberto')
    print('─' * 50)
    print('  Próximo fluxo (ou X para fechar o browser):')
    return menu_execucao()


def _resetar_para_painel(driver) -> bool:
    """Fecha abas extras e navega para meu-painel para a próxima execução."""
    try:
        _limpar_acesso_negado(driver)
        handles = driver.window_handles
        if len(handles) > 1:
            primeira = handles[0]
            for h in handles[1:]:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
            handles_restantes = driver.window_handles
            if primeira in handles_restantes:
                driver.switch_to.window(primeira)
            elif handles_restantes:
                driver.switch_to.window(handles_restantes[0])
        try:
            driver.execute_script("document.body.style.zoom='100%'")
        except Exception:
            pass
        driver.get(PAINEL_URL)
        return True
    except Exception as e:
        logger.warning("[X] _resetar_para_painel: %s", e)
        return False


def _executar_um_fluxo(driver, fluxo: str, driver_type) -> dict:
    """Executa um único fluxo e devolve o resultado.

    Isolado aqui para que main() possa chamar em loop sem duplicar código.
    """
    handler = FLOW_HANDLERS.get(fluxo)
    if not handler:
        raise ValueError(f"Fluxo invalido: {fluxo}")

    if fluxo == "A":
        resultado = executar_bloco_completo(driver, driver_type=driver_type)
        _driver_final = resultado.pop("_driver", None)
        if _driver_final is not None and _driver_final is not driver:
            try:
                finalizar_driver_fix(_driver_final)
            except Exception:
                pass
    else:
        resultado = handler(driver)

        # Falha imediata (<2s) = sessão de API morta — novo login, reexecuta uma vez
        if (isinstance(resultado, dict)
                and not resultado.get("sucesso", False)
                and float(resultado.get("tempo", 99)) < 2):
            logger.warning(
                "[LOGIN] Fluxo falhou em %.2fs (sessao de API morta?) "
                "— novo login completo (driver aberto) e reexecucao.",
                float(resultado.get("tempo", 0)),
            )
            try:
                try:
                    driver.delete_all_cookies()
                except Exception:
                    pass
                ok = login_cpf(driver, forcar=True) and _aguardar_sessao_ativa(driver)
                if not ok:
                    logger.warning(
                        "[LOGIN] Conclua o login manualmente na janela "
                        "aberta — o fluxo continua assim que a sessao "
                        "completar (access_token)."
                    )
                    ok = _aguardar_login_manual(driver)
                if ok:
                    resultado = handler(driver)
                else:
                    logger.error("[LOGIN] Login nao concluido — mantendo o primeiro resultado.")
            except Exception as e:
                logger.error("[LOGIN] Erro no novo login: %s: %s", type(e).__name__, e)

    return resultado


def main():
    """Função principal — loop de sessão: um driver, múltiplos fluxos."""
    driver = None
    tee_output = None
    log_file = None
    try:
        try:
            from Fix.otimizacao_wrapper import inicializar_otimizacoes
            inicializar_otimizacoes()
        except Exception:
            pass

        # ── Seleção inicial: ambiente + primeiro fluxo ──────────────────────
        selecao = selecionar_ambiente_e_fluxo()
        if not selecao:
            logger.info("cancelado")
            return "cancelado"

        driver_type, debug_mode, fluxo = selecao

        log_file, tee_output = configurar_logging(driver_type, debug=debug_mode)

        logger.info("ORQUESTRADOR UNIFICADO PJEPlus")
        logger.info("data/hora: %s", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        logger.info("ambiente: %s", driver_type.value)
        logger.info("log: %s", log_file)

        driver = criar_e_logar_driver(driver_type)
        if not driver:
            logger.error("ERRO em main: falha ao inicializar driver/logar")
            return

        # ── Loop de fluxos na mesma sessão ─────────────────────────────────
        while fluxo:
            inicio = datetime.now()
            logger.info("── fluxo: %s ──", fluxo)

            resultado = _executar_um_fluxo(driver, fluxo, driver_type)

            tempo_total = (datetime.now() - inicio).total_seconds()

            # Relatório do fluxo concluído
            if resultado:
                if 'sucesso_geral' in resultado:
                    logger.info("sucesso geral: %s", resultado['sucesso_geral'])
                elif 'sucesso' in resultado:
                    logger.info("sucesso: %s", resultado['sucesso'])
            logger.info("tempo: %.2fs", tempo_total)

            # Verifica se o driver ainda está vivo antes de oferecer o loop
            try:
                _ = driver.window_handles
                driver_vivo = True
            except Exception:
                driver_vivo = False

            if not driver_vivo:
                logger.warning("[X] Driver fechou durante o fluxo — encerrando sessão.")
                driver = None
                break

            # Reseta para meu-painel e pergunta próximo fluxo
            _resetar_para_painel(driver)
            fluxo = _menu_proximo_fluxo()

        logger.info("encerrando")
        return "ok"

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
