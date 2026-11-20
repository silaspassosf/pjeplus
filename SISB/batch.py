import logging
from selenium.webdriver.remote.webdriver import WebDriver
logger = logging.getLogger(__name__)

"""
SISB/batch.py - Processamento em lote de operações SISBAJUD

Este módulo fornece funções para processar múltiplos processos SISBAJUD
usando um único driver compartilhado, otimizando o tempo de execução.
"""

from typing import Any, Dict, List, Optional, Callable, Tuple
from Fix.core import aguardar_renderizacao_nativa
from Fix.extracao import criar_gigs, extrair_dados_processo

URL_MINUTA = "https://sisbajud.cnj.jus.br/minuta"


def processar_lote_sisbajud(
    driver_pje: WebDriver,
    processos: List[Dict[str, Any]],
    progresso: Dict[str, Any],
    fn_reindexar_linha: Callable[[WebDriver, str], Optional[Any]],
    fn_abrir_detalhes: Callable[[WebDriver, Any], bool],
    fn_trocar_aba: Callable[[WebDriver, str], bool],
    fn_ja_executado: Callable[[str, Dict[str, Any]], bool],
    fn_marcar_executado: Callable[[str, Dict[str, Any]], None],
    log: bool = True
) -> Dict[str, int]:
    """Processa um lote de processos SISBAJUD com driver compartilhado."""
    from .core import iniciar_sisbajud, minuta_bloqueio, processar_ordem_sisbajud

    resultados = {'sucesso': 0, 'erro': 0}

    if not processos:
        return resultados

    processos_teimosinha = []
    processos_resultado = []

    for proc in processos:
        acoes = proc.get('acoes', [])

        if not acoes:
            continue

        primeira_acao = acoes[0]
        acao_nome = primeira_acao.__name__ if callable(primeira_acao) else str(primeira_acao)

        if 'minuta_bloqueio' in acao_nome:
            processos_teimosinha.append(proc)
        elif 'processar_ordem' in acao_nome:
            processos_resultado.append(proc)
        else:
            processos_teimosinha.append(proc)

    if log:
        _ = True

    # ===== ETAPA 2: Armazenar aba da lista e preparar driver SISBAJUD (será criado no primeiro processo) =====
    driver_sisbajud = None
    aba_lista_pje = driver_pje.current_window_handle

    try:

        if processos_teimosinha:
            driver_sisbajud, res = _processar_grupo(
                driver_pje=driver_pje,
                driver_sisbajud=driver_sisbajud,
                processos=processos_teimosinha,
                tipo='TEIMOSINHA',
                fn_executar=lambda d_sisb, dados, d_pje: minuta_bloqueio(d_sisb, dados_processo=dados, driver_pje=d_pje, log=log, fechar_driver=False),
                progresso=progresso,
                aba_lista_pje=aba_lista_pje,
                fn_reindexar_linha=fn_reindexar_linha,
                fn_abrir_detalhes=fn_abrir_detalhes,
                fn_trocar_aba=fn_trocar_aba,
                fn_ja_executado=fn_ja_executado,
                fn_marcar_executado=fn_marcar_executado,
                log=log
            )
            resultados['sucesso'] += res['sucesso']
            resultados['erro'] += res['erro']

        if processos_resultado:
            driver_sisbajud, res = _processar_grupo(
                driver_pje=driver_pje,
                driver_sisbajud=driver_sisbajud,
                processos=processos_resultado,
                tipo='RESULTADO',
                fn_executar=lambda d_sisb, dados, d_pje: processar_ordem_sisbajud(d_sisb, dados_processo=dados, driver_pje=d_pje, log=log, fechar_driver=False),
                progresso=progresso,
                aba_lista_pje=aba_lista_pje,
                fn_reindexar_linha=fn_reindexar_linha,
                fn_abrir_detalhes=fn_abrir_detalhes,
                fn_trocar_aba=fn_trocar_aba,
                fn_ja_executado=fn_ja_executado,
                fn_marcar_executado=fn_marcar_executado,
                log=log
            )
            resultados['sucesso'] += res['sucesso']
            resultados['erro'] += res['erro']

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro geral: {e}")
        import traceback
        logger.exception("Erro detectado")

    finally:
        # ===== ETAPA 5: Fechar driver SISBAJUD =====
        if driver_sisbajud:
            try:
                driver_sisbajud.quit()
            except Exception:
                pass

    if log:
        logger.error(f"[SISBAJUD]  Total: {resultados['sucesso']} sucesso | {resultados['erro']} erros\n")

    return resultados


def _processar_grupo(
    driver_pje: WebDriver,
    driver_sisbajud: Optional[WebDriver],
    processos: List[Dict[str, Any]],
    tipo: str,
    fn_executar: Callable[[WebDriver, Dict[str, Any], WebDriver], Any],
    progresso: Dict[str, Any],
    aba_lista_pje: str,
    fn_reindexar_linha: Callable[[WebDriver, str], Optional[Any]],
    fn_abrir_detalhes: Callable[[WebDriver, Any], bool],
    fn_trocar_aba: Callable[[WebDriver, str], bool],
    fn_ja_executado: Callable[[str, Dict[str, Any]], bool],
    fn_marcar_executado: Callable[[str, Dict[str, Any]], None],
    log: bool = True
) -> Tuple[Optional[WebDriver], Dict[str, int]]:
    """Processa um grupo de processos do mesmo tipo."""

    resultados = {'sucesso': 0, 'erro': 0}

    for idx, proc in enumerate(processos, 1):
        numero_processo = proc.get('numero')

        try:
            if fn_ja_executado(numero_processo, progresso):
                continue

            linha = proc.get('linha')
            try:
                linha.is_displayed()
            except Exception:
                linha = fn_reindexar_linha(driver_pje, numero_processo)

            if not linha:
                try:
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        fn_marcar_executado(numero_processo, progresso)
                        resultados['erro'] += 1
                        continue
                except Exception:
                    pass

                resultados['erro'] += 1
                continue

            if not fn_abrir_detalhes(driver_pje, linha):
                try:
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        fn_marcar_executado(numero_processo, progresso)
                        resultados['erro'] += 1
                        continue
                except Exception:
                    pass

                resultados['erro'] += 1
                continue

            aguardar_renderizacao_nativa(driver_pje, timeout=1)
            nova_aba = fn_trocar_aba(driver_pje, aba_lista_pje)
            if not nova_aba:
                resultados['erro'] += 1
                continue

            aguardar_renderizacao_nativa(driver_pje, timeout=2)

            dados_processo = extrair_dados_processo(driver_pje)
            if not dados_processo:
                try:
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        raise Exception(f"RESTART_SISB: ACESSO_NEGADO detectado para {numero_processo}")
                except Exception as e:
                    if "RESTART_SISB" in str(e):
                        raise

                try:
                    if aba_lista_pje in driver_pje.window_handles:
                        driver_pje.switch_to.window(aba_lista_pje)

                        for handle in list(driver_pje.window_handles):
                            if handle != aba_lista_pje:
                                try:
                                    driver_pje.switch_to.window(handle)
                                    driver_pje.close()
                                except Exception:
                                    pass

                        driver_pje.switch_to.window(aba_lista_pje)
                except Exception:
                    pass

                resultados['erro'] += 1
                continue

            # ===== VERIFICAR VALOR DE BLOQUEIO ANTES DE CRIAR DRIVER SISBAJUD =====
            divida = dados_processo.get('divida', {})
            valor = divida.get('valor')

            if not valor:
                try:
                    criar_gigs(driver_pje, 'Bruna Atualização', log=log)
                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)

                            for handle in list(driver_pje.window_handles):
                                if handle != aba_lista_pje:
                                    try:
                                        driver_pje.switch_to.window(handle)
                                        driver_pje.close()
                                    except Exception:
                                        pass

                            driver_pje.switch_to.window(aba_lista_pje)
                    except Exception:
                        pass

                    resultados['sucesso'] += 1
                    continue

                except Exception as e:
                    if log:
                        logger.error(f'[SISBAJUD_LOTE]  Erro ao criar GIGS para {numero_processo}: {e}')

                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)

                            for handle in list(driver_pje.window_handles):
                                if handle != aba_lista_pje:
                                    try:
                                        driver_pje.switch_to.window(handle)
                                        driver_pje.close()
                                    except Exception:
                                        pass

                            driver_pje.switch_to.window(aba_lista_pje)
                    except Exception:
                        pass

                    resultados['erro'] += 1
                    continue

            if driver_sisbajud is None:
                # Validar conexão do driver PJE antes de iniciar SISBAJUD
                try:
                    from Fix.abas import validar_conexao_driver
                    conex_ok = validar_conexao_driver(driver_pje, 'SISB_INIT', numero_processo)
                    if conex_ok == "FATAL" or not conex_ok:
                        logger.error(f"[SISBAJUD_LOTE] Driver PJE inválido antes de iniciar SISBAJUD for {numero_processo}: {conex_ok}")
                        raise Exception(f"RESTART_SISB: driver PJE inválido antes de iniciar SISBAJUD for {numero_processo}")
                except Exception as e_valid:
                    logger.error(f"[SISBAJUD_LOTE] Validação do driver PJE falhou: {e_valid}")
                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)
                    except Exception:
                        pass
                    resultados['erro'] += 1
                    continue

                from .core import iniciar_sisbajud
                driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje, extrair_dados=False)

                if not driver_sisbajud:
                    logger.error(f"[SISBAJUD_LOTE] iniciar_sisbajud retornou None para {numero_processo}")
                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)
                            for handle in list(driver_pje.window_handles):
                                if handle != aba_lista_pje:
                                    try:
                                        driver_pje.switch_to.window(handle)
                                        driver_pje.close()
                                    except Exception:
                                        pass
                            driver_pje.switch_to.window(aba_lista_pje)
                    except Exception:
                        pass
                    resultados['erro'] += 1
                    continue

                # Validar driver SISBAJUD recém-criado
                try:
                    from Fix.abas import validar_conexao_driver
                    ok_sisb = validar_conexao_driver(driver_sisbajud, 'SISB_DRIVER', numero_processo)
                    if ok_sisb == "FATAL" or not ok_sisb:
                        logger.error(f"[SISBAJUD_LOTE] Driver SISBAJUD inválido após criação for {numero_processo}: {ok_sisb}")
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
                logger.error(f"[SISBAJUD_LOTE] Falha ao navegar para {URL_MINUTA}: {e_get}")
                # Se navegar ao SISBAJUD falhar, tentar recuperar foco no PJE e continuar
                try:
                    if aba_lista_pje in driver_pje.window_handles:
                        driver_pje.switch_to.window(aba_lista_pje)
                except Exception:
                    pass
                resultados['erro'] += 1
                continue

            acoes = proc.get('acoes', [])

            if acoes:
                for acao in acoes:
                    if callable(acao):
                        acao_nome = acao.__name__ if hasattr(acao, '__name__') else str(acao)
                        resultado = acao(driver=driver_sisbajud, dados_processo=dados_processo, driver_pje=driver_pje, log=log, fechar_driver=False)
                    else:
                        continue
            else:
                resultado = fn_executar(driver_sisbajud, dados_processo, driver_pje)

            # Limpar driver SISBAJUD entre processos (evita estado residual da SPA Angular)
            try:
                driver_sisbajud.get("about:blank")
                aguardar_renderizacao_nativa(driver_sisbajud, timeout=2)
            except Exception:
                pass

            # (Evita que abas remanescentes causem confusão entre processos)
            try:
                if aba_lista_pje in driver_pje.window_handles:
                    driver_pje.switch_to.window(aba_lista_pje)

                    for handle in list(driver_pje.window_handles):
                        if handle != aba_lista_pje:
                            try:
                                driver_pje.switch_to.window(handle)
                                driver_pje.close()
                            except Exception:
                                pass

                    driver_pje.switch_to.window(aba_lista_pje)
            except Exception as e:
                if log:
                    logger.error(f"   Erro ao fechar abas: {e}")
                try:
                    driver_pje.switch_to.window(aba_lista_pje)
                except Exception:
                    pass

            sucesso = False
            if isinstance(resultado, dict):
                sucesso = resultado.get('status') == 'concluido'
            elif resultado:
                sucesso = True

            try:
                if aba_lista_pje in driver_pje.window_handles:
                    driver_pje.switch_to.window(aba_lista_pje)

                    for handle in list(driver_pje.window_handles):
                        if handle != aba_lista_pje:
                            try:
                                driver_pje.switch_to.window(handle)
                                driver_pje.close()
                            except Exception:
                                pass

                fn_marcar_executado(numero_processo, progresso)
            except Exception as e:
                if log:
                    logger.error(f"   Erro ao fechar abas: {e}")

            if log:
                pass
            else:
                resultados['erro'] += 1
        except Exception as e:
            if log:
                logger.error(f"   Erro: {e}")
            resultados['erro'] += 1
            try:
                driver_pje.switch_to.window(aba_lista_pje)
            except Exception:
                pass

    return driver_sisbajud, resultados
