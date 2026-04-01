import logging
logger = logging.getLogger(__name__)

"""Executor de ações - lógica para chamar funções com assinaturas variadas."""

import inspect
import traceback
from typing import Any, Optional, Callable, List, Union, Dict
from selenium.webdriver.remote.webdriver import WebDriver


def chamar_funcao_com_assinatura_correta(
    func: Callable,
    driver: WebDriver,
    numero_processo: str,
    observacao: str,
    destinatarios_override: Optional[List[Dict[str, Any]]] = None,
    driver_sisb: Optional[WebDriver] = None,
    dados_processo: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Helper para chamar função com assinatura correta.
    Detecta automaticamente os parâmetros aceitos pela função.
    """
    try:
        sig = inspect.signature(func)
        params = sig.parameters
        
        # Verificar parâmetros disponíveis
        aceita_observacao = 'observacao' in params
        aceita_destinatarios = 'destinatarios_override' in params
        aceita_debug = 'debug' in params
        aceita_numero_processo = 'numero_processo' in params
        aceita_driver_sisb = 'driver_sisb' in params
        aceita_dados_processo = 'dados_processo' in params
        
        # Chamar com a assinatura apropriada
        if aceita_driver_sisb and driver_sisb is not None:
            return func(driver, driver_sisb=driver_sisb)
        if aceita_dados_processo and dados_processo is not None:
            return func(driver, dados_processo=dados_processo)
        elif aceita_numero_processo and aceita_observacao and aceita_destinatarios:
            # Wrappers de comunicação (pec_ord, pec_sum, pec_decisao, etc.)
            if destinatarios_override is not None:
                return func(driver, numero_processo, observacao, destinatarios_override=destinatarios_override)
            else:
                return func(driver, numero_processo, observacao)
        elif aceita_numero_processo and aceita_observacao:
            # Funções que aceitam observacao
            return func(driver, numero_processo, observacao)
        elif aceita_debug:
            # Funções como mov_sob, def_sob, carta, def_chip
            return func(driver, debug=True)
        else:
            # Funções que aceitam apenas driver
            return func(driver)
    except TypeError as e:
        # Erro de assinatura - tentar fallbacks
        logger.info(f"[AÇÃO]  Erro de assinatura de {func.__name__}: {e}")
        try:
            return func(driver, debug=True)
        except:
            return func(driver)
    except Exception as e:
        # Outros erros (runtime, lógica) - não fazer retry
        logger.error(f"[AÇÃO][ERRO] Falha ao executar {func.__name__}: {e}")
        raise


def executar_acao(
    driver: WebDriver,
    acao: Union[Callable, List[Callable]],
    numero_processo: str,
    observacao: str,
    destinatarios_override: Optional[Any] = None,
    driver_sisb: Optional[Any] = None
) -> bool:
    """
    Executa a ação determinada no processo aberto.
    Suporta funções diretas e listas de funções para execução sequencial.
    Detecta a assinatura de cada função para chamar com os argumentos corretos.
    
    Args:
        driver: WebDriver PJe
        acao: Função ou lista de funções a executar
        numero_processo: Número do processo
        observacao: Observação do processo
        destinatarios_override: Destinatários customizados (opcional)
        driver_sisb: Driver SISBAJUD opcional para reutilização
    
    Returns:
        bool: True se sucesso, False caso contrário
    """
    logger.info(f"[AÇÃO] Executando ação '{acao}' para processo {numero_processo}")

    # Modo lista: executar todas as funções sequencialmente
    if isinstance(acao, list):
        logger.info(f"[AÇÃO]  Detectada lista de {len(acao)} funções para executar sequencialmente")
        for i, func in enumerate(acao, 1):
            logger.info(f"[AÇÃO] Executando função {i}/{len(acao)}: {func.__name__}")
            try:
                resultado = chamar_funcao_com_assinatura_correta(
                    func, driver, numero_processo, observacao, destinatarios_override, driver_sisb
                )
                if not resultado:
                    logger.info(f"[AÇÃO]  Função {func.__name__} falhou - interrompendo sequência")
                    return False
                logger.info(f"[AÇÃO]  Função {func.__name__} executada com sucesso")
            except Exception as e:
                logger.info(f"[AÇÃO]  Erro na função {func.__name__}: {e}")
                logger.exception("Erro detectado")
                return False
        logger.info(f"[AÇÃO]  Todas as {len(acao)} funções executadas com sucesso")
        return True

    # Modo função direta
    if callable(acao):
        try:
            logger.info(f"[AÇÃO]  Chamando função diretamente: {acao.__name__}")
            resultado = chamar_funcao_com_assinatura_correta(
                acao, driver, numero_processo, observacao, destinatarios_override, driver_sisb
            )
            if resultado:
                logger.info(f"[AÇÃO]  Função {acao.__name__} executada com sucesso")
            else:
                logger.info(f"[AÇÃO]  Função {acao.__name__} retornou False")
            return resultado
        except Exception as e:
            from Fix.utils import verificar_driver_ativo
            if not verificar_driver_ativo(driver):
                logger.error(f"[AÇÃO] Driver desconectado detectado. Interrompendo.")
                raise e
            logger.info(f"[AÇÃO]  Erro ao executar função {acao.__name__}: {e}")
            logger.exception("Erro detectado")
            return False

    # Ação inválida
    logger.info(f"[AÇÃO]  Ação '{acao}' não é uma função válida")
    return False


def executar_acao_pec(
    driver: WebDriver,
    acao: Optional[Union[Callable, List[Callable]]],
    numero_processo: Optional[str] = None,
    observacao: Optional[str] = None,
    debug: bool = True,
    driver_sisb: Optional[Any] = None,
    dados_processo: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Executa uma ação (função ou lista de funções).
    Versão simplificada e robusta com múltiplos fallbacks de assinatura.
    
    Args:
        driver: Selenium WebDriver
        acao: Função ou lista de funções para executar, ou None
        numero_processo: Número do processo (opcional)
        observacao: Observação do processo (opcional)
        debug: Flag de debug
    
    Returns:
        bool: True se sucesso, False se falha ou nenhuma ação
    """
    if acao is None:
        if numero_processo:
            logger.info(f"[PEC_EXEC] Nenhuma ação para {numero_processo}")
        return False
    
    # Normalizar: sempre trabalhar com lista
    acoes = acao if isinstance(acao, list) else [acao]
    
    try:
        def _get_func_label(func) -> str:
            if not callable(func):
                return str(func)
            wrapper_id = getattr(func, '_wrapper_id', None)
            if wrapper_id:
                return wrapper_id
            nome_local = getattr(func, '__name__', None) or str(func)
            if nome_local == 'wrapper':
                return f"{func.__module__}.wrapper"
            return nome_local

        def _executar_funcao(func, extra_kwargs=None) -> bool:
            nome_func = _get_func_label(func)
            logger.info(f"[PEC_EXEC] Executando: {nome_func}")

            call_kwargs = {}
            if extra_kwargs:
                call_kwargs.update(extra_kwargs)

            if 'debug' not in call_kwargs:
                call_kwargs['debug'] = debug

            try:
                try:
                    resultado = chamar_funcao_com_assinatura_correta(
                        func,
                        driver,
                        numero_processo or '',
                        observacao or '',
                        call_kwargs.get('destinatarios_override'),
                        driver_sisb,
                        call_kwargs.get('dados_processo')
                    )
                    # Normalizar retorno: algumas funções retornam tuplas (success, flag)
                    # Python interpreta tupla vazia como False, mas tupla não-vazia como True
                    # Precisamos verificar o primeiro elemento se for tupla
                    if isinstance(resultado, tuple):
                        resultado = resultado[0] if resultado else False
                    return bool(resultado)
                except Exception:
                    try:
                        logger.info(f"[PEC_EXEC_CALL] Chamando {nome_func} com kwargs={call_kwargs}")
                        return func(driver, **call_kwargs)
                    except TypeError:
                        try:
                            return func(driver, debug=debug)
                        except TypeError:
                            try:
                                return func(driver, numero_processo, observacao, debug=debug)
                            except TypeError:
                                try:
                                    return func(driver, numero_processo, observacao)
                                except TypeError:
                                    try:
                                        return func(driver, debug=True)
                                    except TypeError:
                                        return func(driver)
            except Exception:
                raise

        for i, raw in enumerate(acoes, 1):
            extra_kwargs = None
            label_resultado = None
            if isinstance(raw, (list, tuple)) and len(raw) == 2 and callable(raw[0]) and isinstance(raw[1], dict):
                func = raw[0]
                extra_kwargs = raw[1].copy()
                label_resultado = _get_func_label(func)
                logger.info(f"[PEC_EXEC] ({i}/{len(acoes)}) Executando: {label_resultado}")
                resultado = _executar_funcao(func, extra_kwargs)
            elif isinstance(raw, list):
                # Lista de itens (pode conter tuplas (func, kwargs) ou funções)
                logger.info(f"[PEC_EXEC] ({i}/{len(acoes)}) Executando lista de {len(raw)} itens")
                resultado = True
                for j, item in enumerate(raw, 1):
                    if isinstance(item, (list, tuple)) and len(item) == 2 and callable(item[0]) and isinstance(item[1], dict):
                        func = item[0]
                        extra_kwargs = item[1].copy()
                        logger.info(f"[PEC_EXEC]   ({j}/{len(raw)}) -> {_get_func_label(func)}")
                        ok = _executar_funcao(func, extra_kwargs)
                        if not ok:
                            logger.info(f"[PEC_EXEC]   ({j}/{len(raw)}) -> {_get_func_label(func)} RETORNOU False")
                            resultado = False
                            break
                    elif callable(item):
                        logger.info(f"[PEC_EXEC]   ({j}/{len(raw)}) -> {_get_func_label(item)}")
                        ok = _executar_funcao(item)
                        if not ok:
                            logger.info(f"[PEC_EXEC]   ({j}/{len(raw)}) -> {_get_func_label(item)} RETORNOU False")
                            resultado = False
                            break
                    else:
                        logger.error(f"[PEC_EXEC] Item {j} não é executável: {item}")
                        resultado = False
                        break
                label_resultado = f"lista_{len(raw)}_itens"
            else:
                func = raw
                label_resultado = _get_func_label(func)
                logger.info(f"[PEC_EXEC] ({i}/{len(acoes)}) Executando: {label_resultado}")
                resultado = _executar_funcao(func)

            if not resultado:
                nome_falha = label_resultado or _get_func_label(func)
                logger.info(f"[PEC_EXEC]  {nome_falha} retornou False")
                return False

            nome_ok = label_resultado or _get_func_label(func)
            logger.info(f"[PEC_EXEC]  {nome_ok} executada")

        return True

    except Exception as e:
        from Fix.utils import verificar_driver_ativo
        if not verificar_driver_ativo(driver):
            logger.error(f"[PEC_EXEC] Driver desconectado detectado. Interrompendo execução global.")
            raise e
        logger.info(f"[PEC_EXEC]  Erro na execução: {e}")
        logger.exception("Erro detectado")
        return False
