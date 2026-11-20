"""SISB/batch.py — Processamento em lote de operações SISBAJUD com driver compartilhado."""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from Fix.core import aguardar_renderizacao_nativa
from Fix.extracao import criar_gigs, extrair_dados_processo

logger = logging.getLogger(__name__)
URL_MINUTA = "https://sisbajud.cnj.jus.br/minuta"


def _abas(driver: Any) -> List[Any]:
    return list(getattr(driver, "window" + "_handles", []))


def _is_acesso_negado(driver: Any) -> bool:
    try:
        url = (driver.current_url or "").lower()
        return "acesso-negado" in url or "access-denied" in url
    except Exception:
        return False


def _restaurar_aba_lista(driver_pje: Any, aba_lista_pje: str, fechar_extras: bool = True, log: bool = False) -> None:
    try:
        handles = _abas(driver_pje)
        if aba_lista_pje not in handles:
            return
        driver_pje.switch_to.window(aba_lista_pje)
        if fechar_extras:
            for handle in list(handles):
                if handle != aba_lista_pje:
                    try:
                        driver_pje.switch_to.window(handle)
                        driver_pje.close()
                    except Exception:
                        pass
            driver_pje.switch_to.window(aba_lista_pje)
    except Exception as e:
        if log:
            logger.error("   Erro ao fechar abas: %s", e)
        try:
            driver_pje.switch_to.window(aba_lista_pje)
        except Exception:
            pass


def processar_lote_sisbajud(
    driver_pje: Any,
    processos: List[Dict[str, Any]],
    progresso: Dict[str, Any],
    fn_reindexar_linha: Callable[[Any, str], Optional[Any]],
    fn_abrir_detalhes: Callable[[Any, Any], bool],
    fn_trocar_aba: Callable[[Any, str], bool],
    fn_ja_executado: Callable[[str, Dict[str, Any]], bool],
    fn_marcar_executado: Callable[[str, Dict[str, Any]], None],
    log: bool = True,
) -> Dict[str, int]:
    """Processa um lote de processos SISBAJUD com driver compartilhado."""
    from .core import minuta_bloqueio, processar_ordem_sisbajud

    resultados = {'sucesso': 0, 'erro': 0}
    if not processos:
        return resultados

    processos_teimosinha, processos_resultado = [], []
    for proc in processos:
        acoes = proc.get('acoes', [])
        if not acoes:
            continue
        primeira_acao = acoes[0]
        acao_nome = primeira_acao.__name__ if callable(primeira_acao) else str(primeira_acao)
        if 'processar_ordem' in acao_nome:
            processos_resultado.append(proc)
        else:
            processos_teimosinha.append(proc)

    driver_sisbajud = None
    aba_lista_pje = driver_pje.current_window_handle

    try:
        grupos = [
            (processos_teimosinha, 'TEIMOSINHA', lambda ds, dados, dp: minuta_bloqueio(ds, dados_processo=dados, driver_pje=dp, log=log, fechar_driver=False)),
            (processos_resultado, 'RESULTADO', lambda ds, dados, dp: processar_ordem_sisbajud(ds, dados_processo=dados, driver_pje=dp, log=log, fechar_driver=False)),
        ]
        for lista, tipo, fn_exec in grupos:
            if not lista:
                continue
            driver_sisbajud, res = _processar_grupo(
                driver_pje=driver_pje,
                driver_sisbajud=driver_sisbajud,
                processos=lista,
                tipo=tipo,
                fn_executar=fn_exec,
                progresso=progresso,
                aba_lista_pje=aba_lista_pje,
                fn_reindexar_linha=fn_reindexar_linha,
                fn_abrir_detalhes=fn_abrir_detalhes,
                fn_trocar_aba=fn_trocar_aba,
                fn_ja_executado=fn_ja_executado,
                fn_marcar_executado=fn_marcar_executado,
                log=log,
            )
            resultados['sucesso'] += res['sucesso']
            resultados['erro'] += res['erro']
    except Exception as e:
        if log:
            logger.error("[SISBAJUD] Erro geral: %s", e)
        logger.exception("Erro detectado")
    finally:
        if driver_sisbajud:
            try:
                driver_sisbajud.quit()
            except Exception:
                pass

    if log:
        logger.error("[SISBAJUD] Total: %s sucesso | %s erros\n", resultados['sucesso'], resultados['erro'])
    return resultados


def _processar_grupo(
    driver_pje: Any,
    driver_sisbajud: Optional[Any],
    processos: List[Dict[str, Any]],
    tipo: str,
    fn_executar: Callable[[Any, Dict[str, Any], Any], Any],
    progresso: Dict[str, Any],
    aba_lista_pje: str,
    fn_reindexar_linha: Callable[[Any, str], Optional[Any]],
    fn_abrir_detalhes: Callable[[Any, Any], bool],
    fn_trocar_aba: Callable[[Any, str], bool],
    fn_ja_executado: Callable[[str, Dict[str, Any]], bool],
    fn_marcar_executado: Callable[[str, Dict[str, Any]], None],
    log: bool = True,
) -> Tuple[Optional[Any], Dict[str, int]]:
    """Processa um grupo de processos do mesmo tipo."""
    from Fix.abas import validar_conexao_driver
    from .core import iniciar_sisbajud

    resultados = {'sucesso': 0, 'erro': 0}

    for proc in processos:
        numero_processo = proc.get('numero')
        try:
            if fn_ja_executado(numero_processo, progresso):
                continue

            linha = proc.get('linha')
            try:
                linha.is_displayed()
            except Exception:
                linha = fn_reindexar_linha(driver_pje, numero_processo)

            if not linha or not fn_abrir_detalhes(driver_pje, linha):
                if _is_acesso_negado(driver_pje):
                    fn_marcar_executado(numero_processo, progresso)
                resultados['erro'] += 1
                continue

            aguardar_renderizacao_nativa(driver_pje, timeout=1)
            if not fn_trocar_aba(driver_pje, aba_lista_pje):
                resultados['erro'] += 1
                continue

            aguardar_renderizacao_nativa(driver_pje, timeout=2)
            dados_processo = extrair_dados_processo(driver_pje)
            if not dados_processo:
                if _is_acesso_negado(driver_pje):
                    raise Exception(f"RESTART_SISB: ACESSO_NEGADO detectado para {numero_processo}")
                _restaurar_aba_lista(driver_pje, aba_lista_pje)
                resultados['erro'] += 1
                continue

            valor = (dados_processo.get('divida') or {}).get('valor')
            if not valor:
                try:
                    criar_gigs(driver_pje, 'Bruna Atualização', log=log)
                    _restaurar_aba_lista(driver_pje, aba_lista_pje)
                    resultados['sucesso'] += 1
                except Exception as e:
                    if log:
                        logger.error("[SISBAJUD_LOTE] Erro ao criar GIGS para %s: %s", numero_processo, e)
                    _restaurar_aba_lista(driver_pje, aba_lista_pje)
                    resultados['erro'] += 1
                continue

            if driver_sisbajud is None:
                try:
                    conex_ok = validar_conexao_driver(driver_pje, 'SISB_INIT', numero_processo)
                    if conex_ok == "FATAL" or not conex_ok:
                        raise Exception(f"RESTART_SISB: driver PJE inválido antes de iniciar SISBAJUD for {numero_processo}")
                except Exception as e_valid:
                    logger.error("[SISBAJUD_LOTE] Validação do driver PJE falhou: %s", e_valid)
                    _restaurar_aba_lista(driver_pje, aba_lista_pje, fechar_extras=False)
                    resultados['erro'] += 1
                    continue

                driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje, extrair_dados=False)
                if not driver_sisbajud:
                    logger.error("[SISBAJUD_LOTE] iniciar_sisbajud retornou None para %s", numero_processo)
                    _restaurar_aba_lista(driver_pje, aba_lista_pje)
                    resultados['erro'] += 1
                    continue

                try:
                    ok_sisb = validar_conexao_driver(driver_sisbajud, 'SISB_DRIVER', numero_processo)
                    if ok_sisb == "FATAL" or not ok_sisb:
                        logger.error("[SISBAJUD_LOTE] Driver SISBAJUD inválido após criação for %s: %s", numero_processo, ok_sisb)
                        try:
                            driver_sisbajud.quit()
                        except Exception:
                            pass
                        resultados['erro'] += 1
                        continue
                except Exception:
                    pass

            try:
                driver_sisbajud.get(URL_MINUTA)
                aguardar_renderizacao_nativa(driver_sisbajud, timeout=1)
            except Exception as e_get:
                logger.error("[SISBAJUD_LOTE] Falha ao navegar para %s: %s", URL_MINUTA, e_get)
                _restaurar_aba_lista(driver_pje, aba_lista_pje, fechar_extras=False)
                resultados['erro'] += 1
                continue

            acoes = proc.get('acoes', [])
            if acoes:
                for acao in acoes:
                    if callable(acao):
                        acao(driver=driver_sisbajud, dados_processo=dados_processo, driver_pje=driver_pje, log=log, fechar_driver=False)
            else:
                fn_executar(driver_sisbajud, dados_processo, driver_pje)

            # Evita estado residual da SPA Angular entre processos.
            try:
                driver_sisbajud.get("about:blank")
                aguardar_renderizacao_nativa(driver_sisbajud, timeout=2)
            except Exception:
                pass

            _restaurar_aba_lista(driver_pje, aba_lista_pje, log=log)
            try:
                fn_marcar_executado(numero_processo, progresso)
            except Exception as e:
                if log:
                    logger.error("   Erro ao marcar executado: %s", e)

            if not log:
                resultados['erro'] += 1
        except Exception as e:
            if log:
                logger.error("   Erro: %s", e)
            resultados['erro'] += 1
            try:
                driver_pje.switch_to.window(aba_lista_pje)
            except Exception:
                pass

    return driver_sisbajud, resultados
