"""x.py — Orquestrador unificado PJePlus (executado via `py pw.py`)."""

import logging
import os
import shutil
import sys
import time
from datetime import date, datetime, timedelta
from enum import Enum
from pprint import pformat
from typing import Any, Callable, Dict, Optional, Tuple

from Fix import espera
from Fix.abas import fechar_abas_extras
from Fix.core import criar_driver_pc, criar_driver_vt, finalizar_driver as finalizar_driver_fix
from Fix.diagnostico_runtime import handler_console_sem_pjeplus
from Fix.log import logger
from Fix.tipos import ResultadoFluxo
from Fix.utils import login_cpf, login_manual
from Mandado.entrada_api import processar_mandados_devolvidos_api
from PEC.orquestrador import executar_fluxo_novo_simplificado as pec_fluxo_api
from Peticao.runtime_pet import run_pet
from Prazo import loop_prazo
from Prazo.p2b_gateway import processar_gigs_sem_prazo_p2b, testar_gigs_sem_prazo
from bianca.triagem_engine import run_triagem

LOG_DIR = "logs_execucao"
os.makedirs(LOG_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
PAINEL_URL = "https://pje.trt2.jus.br/pjekz/gigs/meu-painel"
_PJEKZ_URL = "https://pje.trt2.jus.br/pjekz/"
_ERRO_MD_LIMITE_BYTES = 1_500_000


class DriverType(Enum):
    PC_VISIBLE = "pc_visible"
    PC_HEADLESS = "pc_headless"
    VT_VISIBLE = "vt_visible"
    VT_HEADLESS = "vt_headless"


def _driver_vivo(driver) -> bool:
    try:
        return bool(getattr(driver, "current_url", None) or hasattr(driver, "page"))
    except Exception:
        return False


def _executar_com_reset(driver, executor):
    resultado = executor(driver)
    resetar_driver(driver)
    return resultado


def _aguardar_login_manual(driver, timeout: int = 900) -> bool:
    """Mantém o browser aberto até o usuário concluir o login manualmente."""
    logger.warning(
        "[LOGIN] Login automatico falhou. Browser mantido ABERTO — "
        "conclua o login manualmente na janela do navegador."
    )
    inicio = time.time()
    from Fix.utils import sessao_oauth_completa

    while time.time() - inicio < timeout:
        try:
            _ = (driver.current_url or "").lower()
        except Exception:
            logger.error("[LOGIN] Browser indisponivel durante espera do login manual.")
            return False
        if sessao_oauth_completa(driver):
            logger.info("[LOGIN] Login manual detectado (%.0fs). Continuando fluxo.", time.time() - inicio)
            try:
                from Fix.utils import SALVAR_COOKIES_AUTOMATICO, salvar_cookies_sessao
                if SALVAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra="login_manual_pos_falha")
            except Exception:
                pass
            return True
        espera.pausa(driver, 2)
    logger.error("[LOGIN] Timeout (%ds) aguardando login manual.", timeout)
    return False


def _aguardar_sessao_ativa(driver, timeout: int = 60) -> bool:
    """Espera sem navegar até o handshake OAuth gravar o access_token no browser."""
    from Fix.utils import sessao_oauth_completa

    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            if sessao_oauth_completa(driver):
                logger.info("[LOGIN] Sessao OAuth completa confirmada (%.0fs).", time.time() - inicio)
                return True
        except Exception:
            logger.error("[LOGIN] Browser indisponivel ao confirmar sessao.")
            return False
        espera.pausa(driver, 2)
    logger.error("[LOGIN] access_token nao apareceu em %ds — login automatico nao completou.", timeout)
    return False


def _criar_driver_headless(driver_type: DriverType, vt_mode: bool) -> Optional[Any]:
    """Cria driver headless e autentica via cookies ou login_cpf (OTP no terminal)."""
    from Fix.utils import salvar_cookies_sessao, verificar_e_aplicar_cookies

    driver_hl = None
    try:
        driver_hl = criar_driver_vt(headless=True) if vt_mode else criar_driver_pc(headless=True)
        if not driver_hl:
            logger.error("[HEADLESS] Falha ao criar driver headless.")
            return None

        if verificar_e_aplicar_cookies(driver_hl):
            if _aguardar_sessao_ativa(driver_hl, timeout=10):
                logger.info("[HEADLESS] Sessao restaurada via cookies — sem login manual necessario.")
                return driver_hl
            logger.info("[HEADLESS] Cookies expirados. Prosseguindo com login automatico headless...")

        if not login_cpf(driver_hl):
            logger.error("[HEADLESS] Falha no login_cpf.")
            finalizar_driver_fix(driver_hl)
            return None

        if not _aguardar_sessao_ativa(driver_hl, timeout=30):
            logger.error("[HEADLESS] Sessao OAuth nao completou apos login.")
            finalizar_driver_fix(driver_hl)
            return None

        salvar_cookies_sessao(driver_hl, info_extra="login_headless")
        logger.info("[HEADLESS] Driver headless pronto com sessao autenticada.")
        return driver_hl
    except Exception as e:
        logger.error("[HEADLESS] Erro ao criar/autenticar driver headless: %s: %s", type(e).__name__, e)
        if driver_hl:
            try:
                finalizar_driver_fix(driver_hl)
            except Exception:
                pass
        return None


def criar_e_logar_driver(driver_type: DriverType) -> Optional[Any]:
    """Cria o driver Playwright (visível ou headless) e conclui a autenticação."""
    headless = driver_type in (DriverType.PC_HEADLESS, DriverType.VT_HEADLESS)
    vt_mode = driver_type in (DriverType.VT_VISIBLE, DriverType.VT_HEADLESS)
    logger.debug("criando driver: %s", driver_type.value)

    if headless:
        return _criar_driver_headless(driver_type, vt_mode)

    try:
        driver = criar_driver_vt(headless=False) if vt_mode else criar_driver_pc(headless=False)
        if not driver:
            logger.error("ERRO em criar_e_logar_driver: falha ao criar driver")
            return None

        # VT visível: login manual sem ler credenciais do keyring do Windows.
        if vt_mode:
            logger.info("[LOGIN] VT visivel: login manual (sem credenciais do sistema)")
            if not login_manual(driver, usar_credenciais=False):
                logger.error("ERRO em criar_e_logar_driver: login manual nao concluido")
                finalizar_driver_fix(driver)
                return None
        elif not login_cpf(driver):
            logger.error("ERRO em criar_e_logar_driver: login nao concluido")
            if not _aguardar_login_manual(driver):
                finalizar_driver_fix(driver)
                return None

        if not _aguardar_sessao_ativa(driver):
            logger.error("ERRO em criar_e_logar_driver: sessao OAuth nao completou")
            if not _aguardar_login_manual(driver):
                finalizar_driver_fix(driver)
                return None

        return driver
    except Exception as e:
        logger.error("ERRO em criar_e_logar_driver: %s: %s", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        return None


def normalizar_resultado(resultado: Any) -> ResultadoFluxo:
    """Normaliza retorno de fluxo para dict padrão."""
    if isinstance(resultado, dict):
        return resultado
    if isinstance(resultado, bool):
        return {"sucesso": resultado, "status": "OK" if resultado else "ERRO"}
    if resultado is None:
        return {"sucesso": False, "status": "ERRO", "erro": "Módulo retornou None"}
    return {"sucesso": False, "status": "ERRO", "erro": str(resultado)}


def _executar_fluxo(
    nome: str,
    fn: Callable[[Any], Any],
    driver: Any,
    normalizar: bool = True,
    on_none_error: Optional[ResultadoFluxo] = None,
) -> ResultadoFluxo:
    """Executa um fluxo com medição de tempo, normalização e log padronizado."""
    start_time = time.time()
    try:
        resultado = fn(driver)
        if resultado is None:
            resultado = (
                on_none_error
                if on_none_error is not None
                else {"sucesso": False, "status": "ERRO", "erro": f"{nome} retornou None"}
            )
        elif normalizar:
            resultado = normalizar_resultado(resultado)
        resultado["tempo"] = time.time() - start_time
        status = "OK" if resultado.get("sucesso", False) else "FALHA"
        logger.info("[%s] %s (%.1fs)", nome.upper(), status, resultado["tempo"])
        if nome.lower() in {"triagem", "domicilio_eletronico"}:
            logger.info("[%s] resultado completo:\n%s", nome.upper(), pformat(resultado, width=120, sort_dicts=False))
        return resultado
    except Exception as e:
        tempo = time.time() - start_time
        logger.error("[%s] ERRO_EXECUCAO (%.1fs): %s: %s", nome.upper(), tempo, type(e).__name__, e)
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": f"{type(e).__name__}: {e}", "tempo": tempo}


def _limpar_acesso_negado(driver) -> int:
    """Fecha abas em acesso-negado e recupera a aba principal se necessário."""
    fechadas = 0
    try:
        handles = list(getattr(driver, "window_handles", []))
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
                if "acesso-negado" in (driver.current_url or "").lower():
                    logger.warning("[X] Aba principal em acesso-negado — navegando para painel...")
                    driver.get(_PJEKZ_URL)
            except Exception:
                pass
    except Exception as e:
        logger.warning("[X] _limpar_acesso_negado erro: %s", e)
    return fechadas


def _resetar_para_url(driver, url: str, aguardar_token: Optional[str] = None) -> bool:
    fechadas = _limpar_acesso_negado(driver)
    if fechadas:
        logger.info("[X] resetar_driver: %d aba(s) acesso-negado fechadas", fechadas)
    fechar_abas_extras(driver)
    try:
        espera.ate_js(driver, "document.body.style.zoom='100%'", teto=0.1)
    except Exception:
        pass
    driver.get(url)
    if aguardar_token:
        try:
            espera.ate_url(driver, aguardar_token, teto=5)
        except Exception:
            pass
    return True


def resetar_driver(driver) -> bool:
    """Fecha abas extras, limpa acesso-negado e retorna para /pjekz/."""
    try:
        logger.debug("resetando driver...")
        _resetar_para_url(driver, _PJEKZ_URL, aguardar_token="pjekz")
        logger.debug("driver resetado")
        return True
    except Exception as e:
        logger.error("ERRO em resetar_driver: %s: %s", type(e).__name__, e)
        return False


def _resetar_para_painel(driver) -> bool:
    """Fecha abas extras e navega para meu-painel para a próxima execução."""
    try:
        return _resetar_para_url(driver, PAINEL_URL)
    except Exception as e:
        logger.warning("[X] _resetar_para_painel: %s", e)
        return False


def executar_bloco_completo(driver, driver_type=None) -> Dict[str, Any]:
    """Executa Mandado -> Prazo -> P2B -> PEC em sequência, recriando driver se morrer."""
    resultados: Dict[str, Any] = {
        "mandado": None,
        "prazo": None,
        "p2b": None,
        "pec": None,
        "sucesso_geral": False,
    }

    def _recriar(nome_modulo: str):
        logger.warning("[BLOCO] driver perdido apos %s — recriando...", nome_modulo)
        if driver_type is None:
            logger.error("[BLOCO] driver_type nao informado — impossivel recriar")
            return None
        try:
            finalizar_driver_fix(driver)
        except Exception:
            pass
        novo = criar_e_logar_driver(driver_type)
        logger.info("[BLOCO] driver recriado com sucesso") if novo else logger.error(
            "[BLOCO] falha ao recriar driver — modulos restantes serao pulados"
        )
        return novo

    etapas = [
        ("mandado", executar_mandado, True),
        ("prazo", executar_prazo, True),
        ("p2b", executar_p2b, True),
        ("pec", executar_pec, False),
    ]
    for nome, fn, com_reset in etapas:
        try:
            resultados[nome] = _executar_com_reset(driver, fn) if com_reset else fn(driver)
        except Exception as e:
            resultados[nome] = {"sucesso": False, "status": "ERRO_DRIVER", "erro": str(e)}
            logger.error("[BLOCO] %s: excecao nao capturada: %s", nome, e)
        if com_reset and not _driver_vivo(driver):
            driver = _recriar(nome)
            if not driver:
                return resultados

    nomes = ("mandado", "prazo", "p2b", "pec")
    todos_sucesso = all((resultados[k] or {}).get("sucesso", False) for k in nomes)
    resultados["sucesso_geral"] = todos_sucesso
    resultados["_driver"] = driver
    resumo = " ".join(f"{k}={'OK' if (resultados[k] or {}).get('sucesso', False) else 'FALHA'}" for k in nomes)
    logger.info("[BLOCO] %s sucesso_geral=%s", resumo, "OK" if todos_sucesso else "FALHAS_PARCIAIS")
    return resultados


def executar_mandado(driver) -> Dict[str, Any]:
    """Mandado isolado via API."""
    def _fluxo(d):
        resultado = normalizar_resultado(processar_mandados_devolvidos_api(d))
        if not resultado.get("sucesso"):
            logger.warning("[MANDADO] falha: %s", resultado.get("erro", "Desconhecido"))
        return resultado

    return _executar_fluxo("Mandado", _fluxo, driver)


def executar_prazo(driver) -> Dict[str, Any]:
    """Prazo isolado (ciclos 1+2+3) seguido de P2B (mesmo se loop falhar)."""
    def _rodar_sub(nome_log, fn, d):
        try:
            res = normalizar_resultado(fn(d))
            if not res.get("sucesso"):
                logger.warning("[PRAZO] %s com falha: %s", nome_log, res.get("erro"))
            return res
        except Exception as e:
            logger.warning("[PRAZO] excecao em %s: %s", nome_log, e)
            return {"sucesso": False, "erro": str(e)}

    def _fluxo(d):
        resultado_loop = _rodar_sub("loop_prazo", loop_prazo, d)
        resultado_p2b = _rodar_sub("P2B", executar_p2b, d)
        sucesso_geral = resultado_loop.get("sucesso", False) and resultado_p2b.get("sucesso", False)
        return {
            "sucesso": sucesso_geral,
            "status": "SUCESSO" if sucesso_geral else "PARCIAL",
            "loop_prazo": resultado_loop,
            "p2b": resultado_p2b,
        }

    return _executar_fluxo("Prazo", _fluxo, driver, normalizar=False)


def executar_pec(driver, filtro_d1: bool = True, data_minima: Optional[str] = None) -> Dict[str, Any]:
    """PEC isolado via API modular."""
    def _fluxo(d):
        resultado = pec_fluxo_api(d, filtro_d1=filtro_d1, data_minima=data_minima)
        total = resultado.get("total", 0)
        erros = resultado.get("erro", 0)
        logger.info("[PEC] total=%s sucesso=%s erro=%s", total, resultado.get("sucesso_count", total - erros), erros)
        return resultado

    resultado = _executar_fluxo("PEC", _fluxo, driver)
    erro_txt = str(resultado.get("erro") or "")
    if not resultado.get("sucesso") and ("RESTART_PEC" in erro_txt or "Nenhuma janela aberta" in erro_txt):
        logger.warning("[PEC] Driver morto durante o batch (%s) — resetando driver...", erro_txt[:120])
        _limpar_acesso_negado(driver)
        resetar_driver(driver)
        return {"sucesso": False, "status": "PARCIAL", "erro": erro_txt, "reset_driver": True}
    return resultado


def executar_triagem(driver) -> Dict[str, Any]:
    """Triagem isolada com retry único após parada crítica."""
    def _log_res(prefixo, res):
        logger.info(
            "%s processados=%s total=%s sucesso=%s",
            prefixo, res.get("processados", 0), res.get("total", "?"), res.get("sucesso_count", "?"),
        )

    def _fluxo(d):
        resultado = run_triagem(d)
        if resultado is None:
            return None
        _log_res("[TRIAGEM]", resultado)
        if resultado.get("critical_stop"):
            logger.warning("[TRIAGEM] Parada critica (%s) — resetando driver e reiniciando...", resultado.get("critical_reason", "?"))
            _limpar_acesso_negado(d)
            resetar_driver(d)
            resultado = run_triagem(d)
            if resultado is None:
                return None
            _log_res("[TRIAGEM] Retry:", resultado)
        return resultado

    return _executar_fluxo(
        "Triagem", _fluxo, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_triagem retornou None"},
    )


def executar_pet_dry_run(driver) -> Dict[str, Any]:
    """Petição DRY RUN — apenas lê o escaninho e relata regras aplicáveis."""
    from Peticao.runtime_pet import executar_dry_run_pet

    res = _executar_fluxo(
        "Peticao_DryRun", executar_dry_run_pet, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "executar_dry_run_pet retornou None"},
    )
    return res if isinstance(res, dict) else {"sucesso": True, "status": "OK", "detalhes": res}


def executar_pet(driver) -> Dict[str, Any]:
    """Petição isolada (delega ao dry run se PJEPLUS_PET_DRYRUN=1)."""
    if os.environ.get("PJEPLUS_PET_DRYRUN") == "1":
        return executar_pet_dry_run(driver)
    return _executar_fluxo(
        "Petição", run_pet, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_pet retornou None"},
    )


def executar_domicilio_eletronico(driver) -> Dict[str, Any]:
    """Domicílio Eletrônico via run_dom_api."""
    from bianca.dom_engine import run_dom_api

    return _executar_fluxo(
        "Domicilio_Eletronico", run_dom_api, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_dom_api retornou None"},
    )


def executar_atualizacao_rapida_fluxo(driver) -> Dict[str, Any]:
    """Atualização Rápida PJe-Calc (env: PJEPLUS_AR_PROCESSO, PJEPLUS_AR_CALCULO, PJEPLUS_AR_DATA)."""
    from Fix.atualizacao_rapida import AtualizacaoRapidaErro, executar_atualizacao_rapida

    numero = (os.environ.get("PJEPLUS_AR_PROCESSO") or "").strip() or None
    id_calculo = (os.environ.get("PJEPLUS_AR_CALCULO") or "").strip() or None
    data = (os.environ.get("PJEPLUS_AR_DATA") or "").strip() or None

    def _fluxo(d):
        try:
            ok = executar_atualizacao_rapida(d, numero, data=data, id_calculo=id_calculo)
            return {"sucesso": bool(ok), "status": "OK" if ok else "FALHA", "processo": numero, "pos_envio": False}
        except AtualizacaoRapidaErro as e:
            return {
                "sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e),
                "fase": e.fase, "pos_envio": e.pos_envio, "processo": numero,
            }

    return _executar_fluxo(
        "Atualizacao_Rapida", _fluxo, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "atualizacao rapida retornou None", "pos_envio": False},
    )


def executar_chipadv(driver) -> ResultadoFluxo:
    """Chip Advogado impedido de Atuar (adv.run_chipadv)."""
    from adv import run_chipadv

    return _executar_fluxo(
        "Chip_Advogado", run_chipadv, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "run_chipadv retornou None"},
    )


_PAUTA_ENDPOINT = "/audapi/rest/pje/audpje/pautas"
_ORGAO_JULGADOR_PAUTA = 187
_URL_PROCESSO_DETALHE = "https://pje.trt2.jus.br/pjekz/processo/{}/detalhe"
_PAUTA_MAX_DIAS = 30


def _proximo_dia_util(a_partir_de) -> "date":
    dia = a_partir_de + timedelta(days=1)
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def _audiencia_cogida(tipo: str) -> bool:
    t = (tipo or "").lower()
    return "julgamento" not in t and "encerramento" not in t


def _pauta_dia_seguinte(client) -> list:
    """Busca a primeira pauta com audiências elegíveis a partir do próximo dia útil."""
    dia = _proximo_dia_util(datetime.now().date())
    for _ in range(_PAUTA_MAX_DIAS):
        dia_iso = dia.strftime("%Y-%m-%d")
        params = {"dataInicio": dia_iso, "dataFim": dia_iso, "orgaoJulgador": _ORGAO_JULGADOR_PAUTA}
        logger.info("[CITACAO] >>> GET %s params=%s", _PAUTA_ENDPOINT, params)
        resp = client.gateway_get(_PAUTA_ENDPOINT, params=params)
        if not resp.get("ok"):
            logger.error("[CITACAO] <<< falha na pauta: %s", resp.get("error"))
            return []
        dados = resp.get("data") or []
        lista = dados if isinstance(dados, list) else (
            dados.get("content") or dados.get("resultado") or dados.get("pautas") or []
        )
        filtradas = [p for p in lista if _audiencia_cogida(p.get("tipoAudiencia"))]
        logger.info("[CITACAO] <<< pauta %s: %d audiencia(s) brutas, %d apos filtro", dia_iso, len(lista), len(filtradas))
        if filtradas:
            return filtradas
        dia = _proximo_dia_util(dia)
    logger.warning("[CITACAO] nenhuma pauta com audiencias em %d dias", _PAUTA_MAX_DIAS)
    return []


def _reclamada_sem_advogado(partes) -> Optional[dict]:
    for pt in (partes or {}).get("PASSIVO") or []:
        if not (pt.get("representantes") or []):
            return pt
    return None


def executar_citacao(driver) -> Dict[str, Any]:
    """Citação — pauta do próximo dia útil -> reclamada sem advogado -> carta (PEC)."""
    def _fluxo(d):
        from PEC.carta_execucao import carta
        from api import PjeApiClient, session_from_driver

        sess, trt_host = session_from_driver(d)
        client = PjeApiClient(sess, trt_host)

        numeros_por_id = {}
        for p in _pauta_dia_seguinte(client):
            if p.get("idProcesso"):
                numeros_por_id.setdefault(p["idProcesso"], p.get("numeroProcesso") or "")
        ids = list(numeros_por_id.keys())
        logger.info("[CITACAO] processos unicos na pauta: %d -> %s", len(ids), ids)

        alvos = []
        for pid in ids:
            endpoint = f"/pje-comum-api/api/processos/id/{pid}/partes"
            resp = client.gateway_get(endpoint)
            if not resp.get("ok"):
                logger.error("[CITACAO] <<< falha (%s) — processo pulado", resp.get("error"))
                continue
            partes = resp.get("data") or {}
            sem_adv = _reclamada_sem_advogado(partes)
            if sem_adv:
                logger.info("[CITACAO] *** RECLAMADA SEM ADVOGADO: %s (doc=%s) ***", sem_adv.get("nome"), sem_adv.get("documento"))
                alvos.append((pid, numeros_por_id.get(pid) or "", sem_adv.get("nome")))

        logger.info("[CITACAO] %d de %d processos com reclamada sem advogado", len(alvos), len(ids))

        sucessos = erros = 0
        for pid, numero, reclamada in alvos:
            try:
                numero_limpo = "".join(filter(str.isdigit, str(numero)))
                url = _URL_PROCESSO_DETALHE.format(numero_limpo if len(numero_limpo) == 20 else pid)
                d.get(url)
                espera.ate_js(d, "document.readyState === 'complete'", teto=15)
                if "acesso-negado" in (d.current_url or "").lower():
                    raise RuntimeError(f"acesso negado — {reclamada} ({numero or pid})")
                logger.info("[CITACAO] processo aberto: %s (reclamada: %s)", url, reclamada)
                carta(d)
                sucessos += 1
            except Exception as exc:
                erros += 1
                logger.error("[CITACAO] erro em %s (%s): %s: %s", reclamada, numero or pid, type(exc).__name__, exc)
            finally:
                try:
                    fechar_abas_extras(d)
                except Exception:
                    pass

        logger.info("[CITACAO] total=%d sucesso=%d erro=%d", len(alvos), sucessos, erros)
        return {
            "sucesso": erros == 0,
            "status": "OK" if erros == 0 else "PARCIAL",
            "total": len(alvos),
            "sucesso_count": sucessos,
            "erro": erros,
        }

    return _executar_fluxo(
        "Citação", _fluxo, driver,
        on_none_error={"sucesso": False, "status": "ERRO_EXECUCAO", "erro": "fluxo citacao retornou None"},
    )


def executar_p2b(driver, motor_api: bool = False) -> Dict[str, Any]:
    """P2B isolado (API GIGS sem prazo XS); motor_api=True usa camada API-first."""
    def _fluxo(d):
        atividades = testar_gigs_sem_prazo(d, tamanho_pagina=100)
        logger.debug("[P2B] processos encontrados: %s", len(atividades))

        def _rodar(drv):
            if motor_api:
                from Prazo.p2b_engine_api import processar_p2b_api
                logger.info("[P2B] motor API-first (filtra por regra antes de abrir)")
                return processar_p2b_api(drv, tamanho_pagina=100, max_processos=0)
            return processar_gigs_sem_prazo_p2b(drv, tamanho_pagina=100, max_processos=0)

        resultado = _rodar(d)
        if resultado.get("critical_stop"):
            logger.warning("[P2B] Sessao expirada (401) — resetando driver e retentando")
            resetar_driver(d)
            resultado = _rodar(d)

        falhas = resultado.get("falhas") or []
        if falhas:
            logger.warning(
                "[P2B] %d processo(s) NAO concluido(s): %s",
                len(falhas), [(f.get("numero"), f.get("erro")) for f in falhas],
            )
        sucesso = resultado.get("sucesso", False)
        return {"sucesso": sucesso, "status": "SUCESSO" if sucesso else "FALHA", "detalhes": resultado}

    return _executar_fluxo("P2B", _fluxo, driver)


def executar_p2b_isolado(driver) -> Dict[str, Any]:
    """Fluxo D — P2B isolado com motor API-first."""
    return executar_p2b(driver, motor_api=True)


_MAPA_AMBIENTE = {
    "A": DriverType.PC_VISIBLE,
    "B": DriverType.PC_HEADLESS,
    "C": DriverType.VT_VISIBLE,
    "D": DriverType.VT_HEADLESS,
}

_OPCOES_FLUXO = (
    ("A", "Bloco Completo"),
    ("B", "Mandado"),
    ("C", "Prazo + P2B"),
    ("D", "P2B"),
    ("E", "PEC"),
    ("F", "Triagem"),
    ("G", "Petição"),
    ("H", "Domicílio Eletrônico"),
    ("I", "Citação"),
    ("J", "Chip Advogado impedido de Atuar (CHIPADV)"),
    ("K", "Atualização Rápida (PJe-Calc)"),
    ("P", "Petição DRY RUN (só lê o escaninho e mostra as regras)"),
)


def menu_ambiente() -> Optional[Tuple[DriverType, bool]]:
    while True:
        print("\nAmbiente:\nA - PC Visível\nB - PC Headless\nC - VT Visível\nD - VT Headless\nX - Cancelar")
        try:
            opcao = input("> ").strip().upper()
        except EOFError:
            return None
        if not opcao:
            continue
        debug_mode = opcao.endswith("D") and len(opcao) > 1
        if debug_mode:
            opcao = opcao[0]
        if opcao == "X":
            return None
        if opcao in _MAPA_AMBIENTE:
            return _MAPA_AMBIENTE[opcao], debug_mode


def menu_execucao() -> Optional[str]:
    validas = {k for k, _ in _OPCOES_FLUXO} | {"X"}
    while True:
        print("\nFluxo:")
        for k, desc in _OPCOES_FLUXO:
            print(f"{k} - {desc}")
        print("X - Cancelar")
        try:
            opcao = input("> ").strip().upper()
        except EOFError:
            return None
        if not opcao:
            continue
        if opcao in validas:
            return None if opcao == "X" else opcao


def selecionar_ambiente_e_fluxo() -> Optional[Tuple[DriverType, bool, str]]:
    """Seleciona ambiente e fluxo (ou lê PJEPLUS_DRIVER e PJEPLUS_FLUXO em modo CI)."""
    env_driver = os.environ.get("PJEPLUS_DRIVER")
    env_fluxo = os.environ.get("PJEPLUS_FLUXO")
    if env_driver and env_fluxo:
        try:
            dt = DriverType[env_driver]
            if env_fluxo in FLOW_HANDLERS:
                logger.info("[ENV] PJEPLUS_DRIVER=%s PJEPLUS_FLUXO=%s — pulando menus.", env_driver, env_fluxo)
                return dt, False, env_fluxo
        except KeyError:
            logger.warning("[ENV] PJEPLUS_DRIVER='%s' invalido — usando menus interativos.", env_driver)

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


def _rotacionar_erro_md(caminho_erro_md: str):
    if not os.path.exists(caminho_erro_md) or os.path.getsize(caminho_erro_md) < _ERRO_MD_LIMITE_BYTES:
        return
    destino = os.path.join(LOG_DIR, f"erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    try:
        shutil.move(caminho_erro_md, destino)
    except OSError:
        pass


class _DestaqueConsoleFormatter(logging.Formatter):
    def format(self, record):
        base = f"[{record.name}] {record.getMessage()}"
        if record.levelno >= logging.ERROR:
            sep = "=" * 60
            return f"\n{sep}\n{base}\n{sep}"
        return base


class _ErroMdFormatter(logging.Formatter):
    def format(self, record):
        msg = record.getMessage()
        if record.exc_info:
            import traceback
            msg += "\n```\n" + "".join(traceback.format_exception(*record.exc_info)).rstrip() + "\n```"
        return f"- **{record.levelname}** `[{self.formatTime(record, '%H:%M:%S')}]` `{record.module}:{record.funcName}` - {msg}\n"


def configurar_logging(driver_type: DriverType, debug: bool = False):
    """Configura logging em arquivo de sessão, console e erro.md rotacionado."""
    headless = driver_type in (DriverType.PC_HEADLESS, DriverType.VT_HEADLESS)
    vt_mode = driver_type in (DriverType.VT_VISIBLE, DriverType.VT_HEADLESS)

    logging.getLogger("urllib3.connectionpool").disabled = True
    if headless:
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    log_file = os.path.join(
        LOG_DIR,
        f"x_{'VT' if vt_mode else 'PC'}_{'Headless' if headless else 'Visible'}_{TIMESTAMP}.log",
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(_DestaqueConsoleFormatter())
    # Evita duplicação no console: 'pjeplus' já possui handler próprio em Fix.diagnostico_runtime.
    handler_console_sem_pjeplus(console_handler)
    root_logger.addHandler(console_handler)

    erro_md = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erro.md")
    _rotacionar_erro_md(erro_md)
    erro_handler = logging.FileHandler(erro_md, encoding="utf-8", mode="a")
    erro_handler.setLevel(logging.ERROR)
    erro_handler.setFormatter(_ErroMdFormatter())
    root_logger.addHandler(erro_handler)

    with open(erro_md, "a", encoding="utf-8") as f:
        f.write(f"\n## Execução {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — {os.path.basename(log_file)}\n\n")

    return log_file, None


FLOW_HANDLERS = {
    "A": executar_bloco_completo,
    "B": executar_mandado,
    "C": executar_prazo,
    "D": executar_p2b_isolado,
    "E": executar_pec,
    "F": executar_triagem,
    "G": executar_pet,
    "P": executar_pet_dry_run,
    "H": executar_domicilio_eletronico,
    "I": executar_citacao,
    "J": executar_chipadv,
    "K": executar_atualizacao_rapida_fluxo,
}


def _menu_proximo_fluxo() -> Optional[str]:
    if os.environ.get("PJEPLUS_FLUXO") or not sys.stdin.isatty():
        return None
    print("\n" + "─" * 50 + "\n  FLUXO CONCLUÍDO — driver mantido aberto\n" + "─" * 50)
    print("  Próximo fluxo (ou X para fechar o browser):")
    return menu_execucao()


def _executar_um_fluxo(driver, fluxo: str, driver_type) -> dict:
    handler = FLOW_HANDLERS.get(fluxo)
    if not handler:
        raise ValueError(f"Fluxo invalido: {fluxo}")

    if fluxo == "A":
        resultado = executar_bloco_completo(driver, driver_type=driver_type)
        driver_final = resultado.pop("_driver", None)
        if driver_final is not None and driver_final is not driver:
            try:
                finalizar_driver_fix(driver_final)
            except Exception:
                pass
        return resultado

    resultado = handler(driver)
    # Falha imediata (<2s) indica sessão morta; nunca reexecuta atualização rápida pós-envio.
    if (
        isinstance(resultado, dict)
        and not resultado.get("sucesso", False)
        and not resultado.get("pos_envio", False)
        and float(resultado.get("tempo", 99)) < 2
    ):
        logger.warning("[LOGIN] Fluxo falhou em %.2fs — novo login e reexecucao.", float(resultado.get("tempo", 0)))
        try:
            try:
                driver.delete_all_cookies()
            except Exception:
                pass
            if driver_type == DriverType.VT_VISIBLE:
                ok = login_manual(driver, usar_credenciais=False) and _aguardar_sessao_ativa(driver)
            else:
                ok = login_cpf(driver, forcar=True) and _aguardar_sessao_ativa(driver)
            if not ok:
                ok = _aguardar_login_manual(driver)
            if ok:
                resultado = handler(driver)
            else:
                logger.error("[LOGIN] Login nao concluido — mantendo o primeiro resultado.")
        except Exception as e:
            logger.error("[LOGIN] Erro no novo login: %s: %s", type(e).__name__, e)
    return resultado


def main():
    """Loop de sessão: um driver Playwright, múltiplos fluxos sequenciais."""
    driver = None
    tee_output = None
    try:
        try:
            from Fix.otimizacao_wrapper import inicializar_otimizacoes
            inicializar_otimizacoes()
        except Exception:
            pass

        selecao = selecionar_ambiente_e_fluxo()
        if not selecao:
            logger.info("cancelado")
            return "cancelado"

        driver_type, debug_mode, fluxo = selecao
        log_file, tee_output = configurar_logging(driver_type, debug=debug_mode)
        logger.info("ORQUESTRADOR UNIFICADO PJEPlus | %s | %s | log=%s", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), driver_type.value, log_file)

        driver = criar_e_logar_driver(driver_type)
        if not driver:
            logger.error("ERRO em main: falha ao inicializar driver/logar")
            return

        while fluxo:
            inicio = datetime.now()
            logger.info("── fluxo: %s ──", fluxo)
            resultado = _executar_um_fluxo(driver, fluxo, driver_type)
            tempo_total = (datetime.now() - inicio).total_seconds()
            if resultado:
                chave = "sucesso_geral" if "sucesso_geral" in resultado else ("sucesso" if "sucesso" in resultado else None)
                if chave:
                    logger.info("%s: %s", chave.replace("_", " "), resultado[chave])
            logger.info("tempo: %.2fs", tempo_total)

            if not _driver_vivo(driver):
                logger.warning("[X] Driver fechou durante o fluxo — encerrando sessão.")
                driver = None
                break

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
    try:
        main()
    except Exception as e:
        logger.error("ERRO: %s: %s", type(e).__name__, e)
        sys.exit(1)
    finally:
        logger.info("orquestrador finalizado")
    sys.exit(0)
