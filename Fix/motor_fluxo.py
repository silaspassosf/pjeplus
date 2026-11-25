"""Fix/motor_fluxo.py — Motor geral parametrizável (Playwright nativo) para fluxos em lote (P2B, PEC, Mandado, etc.)."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from Fix import espera
from Fix.log import logger
from Fix.variaveis import url_processo_detalhe
from utilitarios_processamento import resultado_falha, resultado_ok, run_batch

_DRIVER_DEAD_TOKENS = (
    "browsing context",
    "no longer exist",
    "has been closed",
    "target closed",
    "failed to decode response from marionette",
    "tried to run command without establishing a connection",
    "no such window",
    "unable to connect to marionette",
    "session deleted",
    "browser_fechado_manualmente",
)


def extrair_id_numero(raw: Any) -> Tuple[Optional[Any], Optional[str]]:
    """Extrai (id_processo, numero_processo) de dicts heterogêneos retornados pelas APIs do PJe."""
    if not isinstance(raw, dict):
        return getattr(raw, "id_processo", None), getattr(raw, "numero_processo", None)
    proc = raw.get("processo") or {}
    id_proc = proc.get("id") or proc.get("idProcesso") or raw.get("idProcesso") or raw.get("id")
    numero = proc.get("numero") or proc.get("numeroProcesso") or raw.get("numeroProcesso") or raw.get("numero")
    return id_proc, numero


def eh_erro_critico_driver(exc_ou_msg: Any, extras: Sequence[str] = ()) -> bool:
    """Detecta falhas fatais de driver/sessão que exigem parada imediata do lote."""
    txt = str(exc_ou_msg or "")
    low = txt.lower()
    if any(k in low for k in _DRIVER_DEAD_TOKENS):
        return True
    if any(extra in txt or extra.lower() in low for extra in extras):
        return True
    try:
        from Fix.browser_suporte import is_browsing_context_discarded_error
        if is_browsing_context_discarded_error(low):
            return True
    except Exception:
        pass
    return False


def _fechar_abas_seguro(driver: Any, ancora: Optional[str] = None) -> None:
    try:
        from Fix.abas import fechar_abas_extras
        if ancora is not None:
            fechar_abas_extras(driver, ancora)
        else:
            fechar_abas_extras(driver)
    except Exception:
        pass
    if ancora is not None:
        try:
            if getattr(driver, "current_window_handle", None) != ancora:
                driver.switch_to.window(ancora)
        except Exception:
            pass


def abrir_detalhe_processo(
    driver: Any,
    url: str,
    *,
    modo_aba: str = "mesma_aba",
    aba_ancora: Optional[str] = None,
    seletor_pronto: Optional[str] = "pje-cabecalho-processo,pje-timeline",
    seletor_pos_load: Optional[str] = None,
    usar_garantir_carregamento: bool = True,
    timeout_load: float = 10.0,
    validar_conexao: bool = True,
    validar_url_invalida: Optional[Callable[[Any], bool]] = None,
    recuperar_sessao: Optional[Callable[[Any], bool]] = None,
    erros_criticos_extras: Sequence[str] = (),
    tag_log: str = "[MOTOR]",
) -> Dict[str, Any]:
    """Abre `/detalhe` do processo de forma resiliente (mesma aba ou nova aba) sobre Playwright."""
    from Fix.abas import validar_conexao_driver
    from Fix.core import aguardar_renderizacao_nativa, garantir_carregamento_pagina, wait_for_page_load

    if validar_conexao and not validar_conexao_driver(driver):
        return resultado_falha("browser_fechado_manualmente", critical=True)

    if modo_aba == "mesma_aba":
        try:
            _fechar_abas_seguro(driver, aba_ancora)
        except Exception as e:
            logger.warning("%s Falha ao limpar abas: %s", tag_log, e)
            if validar_conexao and not validar_conexao_driver(driver):
                return resultado_falha("browser_fechado_manualmente", critical=True)

    try:
        if modo_aba == "nova_aba":
            from Fix.browser_suporte import abrir_url_nova_aba
            abrir_url_nova_aba(driver, url, timeout=timeout_load)
            wait_for_page_load(driver, timeout=min(8.0, timeout_load))
        else:
            driver.get(url)
            if usar_garantir_carregamento and seletor_pronto:
                ok_load = garantir_carregamento_pagina(
                    driver,
                    seletor_esperado=seletor_pronto,
                    timeout_refresh=min(5.0, timeout_load),
                    url_alvo=url,
                )
                if not ok_load:
                    if validar_url_invalida and validar_url_invalida(driver):
                        if recuperar_sessao and recuperar_sessao(driver):
                            driver.get(url)
                            wait_for_page_load(driver, timeout=max(10.0, timeout_load))
                        if validar_url_invalida(driver):
                            return resultado_falha("acesso_negado_sessao", critical=True)
                    else:
                        return resultado_falha("detalhe_nao_carregou")
            else:
                try:
                    aguardar_renderizacao_nativa(driver, seletor=seletor_pronto, timeout=timeout_load)
                except Exception:
                    espera.ate_js(driver, "document.readyState === 'complete'", teto=timeout_load)

        if validar_url_invalida and validar_url_invalida(driver):
            if recuperar_sessao and recuperar_sessao(driver):
                driver.get(url)
                wait_for_page_load(driver, timeout=max(10.0, timeout_load))
            if validar_url_invalida(driver):
                return resultado_falha("acesso_negado_sessao", critical=True)

        if modo_aba == "nova_aba" and seletor_pronto:
            aguardar_renderizacao_nativa(driver, seletor_pronto, timeout=min(5.0, timeout_load))

        if seletor_pos_load:
            espera.ate_aparecer(driver, seletor_pos_load, teto=5)

        return resultado_ok()
    except Exception as exc:
        crit = eh_erro_critico_driver(exc, erros_criticos_extras)
        return resultado_falha(str(exc), critical=crit, _exception=exc)


@dataclass
class FluxoSpec:
    """Especificação declarativa intercambiável para executar qualquer fluxo em lote."""

    nome: str
    executar: Callable[[Any, Any], Any]
    obter_url: Callable[[Any], str] = field(
        default_factory=lambda: (lambda item: url_processo_detalhe(item["id"] if isinstance(item, dict) else item.id_processo))
    )
    obter_chave: Callable[[Any], str] = field(
        default_factory=lambda: (
            lambda item: (
                item.get("chave") or item.get("numero") or str(item.get("id", ""))
                if isinstance(item, dict)
                else str(getattr(item, "numero_processo", None) or getattr(item, "id_processo", ""))
            )
        )
    )
    tag_log: str = "[MOTOR]"
    modulo_progresso: Optional[str] = None
    should_skip: Optional[Callable[[Any], bool]] = None
    persist_result: Optional[Callable[[Any, Dict[str, Any]], None]] = None
    open_item_fn: Optional[Callable[[Any, Any], Dict[str, Any]]] = None
    modo_aba: str = "mesma_aba"
    aba_ancora: Optional[str] = None
    seletor_pronto: Optional[str] = "pje-cabecalho-processo,pje-timeline"
    seletor_pos_load: Optional[str] = None
    usar_garantir_carregamento: bool = True
    timeout_load: float = 10.0
    validar_conexao: bool = True
    validar_url_invalida: Optional[Callable[[Any], bool]] = None
    recuperar_sessao: Optional[Callable[[Any], bool]] = None
    marcar_em_erro: bool = False
    fechar_abas_ao_final: bool = True
    stop_on_critical: bool = True
    erros_criticos_extras: Tuple[str, ...] = ()
    on_critical_exception: Optional[Callable[[Exception], bool]] = None


def _normalizar_execucao(retorno: Any, nome_acao: str = "acao") -> Dict[str, Any]:
    if isinstance(retorno, dict) and "ok" in retorno:
        return retorno
    if retorno is None or retorno is False or (isinstance(retorno, tuple) and not all(retorno)):
        return resultado_falha(f"Acao {nome_acao} retornou {retorno!r}")
    return resultado_ok(retorno=retorno)


def executar_fluxo_lote(
    driver: Any,
    itens: Sequence[Any],
    spec: FluxoSpec,
) -> Dict[str, Any]:
    """Executa um lote de processos usando `FluxoSpec` sobre `run_batch` + Playwright."""
    from Fix.monitoramento_progresso_unificado import (
        carregar_progresso_unificado,
        marcar_processo_executado_unificado,
        processo_ja_executado_unificado,
    )

    progresso = None
    if spec.modulo_progresso and (spec.should_skip is None or spec.persist_result is None):
        progresso = carregar_progresso_unificado(spec.modulo_progresso)

    def _should_skip(item: Any) -> bool:
        if spec.should_skip is not None:
            return bool(spec.should_skip(item))
        if spec.modulo_progresso and progresso is not None:
            chave = spec.obter_chave(item)
            if chave and processo_ja_executado_unificado(chave, progresso):
                logger.info("%s Skip já executado: %s", spec.tag_log, chave)
                return True
        return False

    def _open_item(item: Any) -> Dict[str, Any]:
        if spec.open_item_fn is not None:
            return spec.open_item_fn(driver, item)
        url = spec.obter_url(item)
        res = abrir_detalhe_processo(
            driver,
            url,
            modo_aba=spec.modo_aba,
            aba_ancora=spec.aba_ancora,
            seletor_pronto=spec.seletor_pronto,
            seletor_pos_load=spec.seletor_pos_load,
            usar_garantir_carregamento=spec.usar_garantir_carregamento,
            timeout_load=spec.timeout_load,
            validar_conexao=spec.validar_conexao,
            validar_url_invalida=spec.validar_url_invalida,
            recuperar_sessao=spec.recuperar_sessao,
            erros_criticos_extras=spec.erros_criticos_extras,
            tag_log=spec.tag_log,
        )
        if not res.get("ok") and spec.fechar_abas_ao_final:
            _fechar_abas_seguro(driver, spec.aba_ancora)
        return res

    def _execute_item(item: Any) -> Dict[str, Any]:
        try:
            res = spec.executar(driver, item)
            return _normalizar_execucao(res, getattr(spec.executar, "__name__", spec.nome))
        except Exception as exc:
            crit = bool(spec.on_critical_exception(exc)) if spec.on_critical_exception else False
            crit = crit or eh_erro_critico_driver(exc, spec.erros_criticos_extras)
            logger.error("%s Erro em %s: %s", spec.tag_log, spec.obter_chave(item), exc)
            return resultado_falha(str(exc), critical=crit, _exception=exc)
        finally:
            if spec.fechar_abas_ao_final:
                _fechar_abas_seguro(driver, spec.aba_ancora)

    def _persist_result(item: Any, result: Dict[str, Any]) -> None:
        if spec.persist_result is not None:
            spec.persist_result(item, result)
            return
        if spec.modulo_progresso and progresso is not None:
            chave = spec.obter_chave(item)
            if not chave:
                return
            if result.get("ok"):
                marcar_processo_executado_unificado(spec.modulo_progresso, chave, progresso, sucesso=True)
            elif spec.marcar_em_erro:
                marcar_processo_executado_unificado(spec.modulo_progresso, chave, progresso, sucesso=False)

    stats = run_batch(
        items=list(itens),
        should_skip=_should_skip,
        open_item=_open_item,
        execute_item=_execute_item,
        persist_result=_persist_result,
        stop_on_critical=spec.stop_on_critical,
    )
    falhas = [
        {"numero": (r["item"].get("numero") if isinstance(r["item"], dict) else spec.obter_chave(r["item"])), "erro": r["erro"]}
        for r in stats["itens"]
        if r["status"] == "falha"
    ]
    return {
        "sucesso": stats["falha"] == 0,
        "total": len(itens),
        "processados": stats["sucesso"],
        "pulados": stats["pulados"],
        "erro": stats["falha"],
        "falhas": falhas,
        "critical_stop": stats.get("critical_stop", False),
        "critical_reason": stats.get("critical_reason"),
        "stats": stats,
    }
