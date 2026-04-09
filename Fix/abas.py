
from Fix.exceptions import DriverFatalError, NavegacaoError
import logging
logger = logging.getLogger(__name__)

"""
Fix.abas - Módulo de gerenciamento de abas para PJe automação.

Funções para trocar de abas, validar conexão do driver e gerenciar abas extras.
Migrado de ORIGINAIS/Fix.py para modularização (PARTE 6).
"""

import time
import traceback
import datetime
from typing import Optional

def is_browsing_context_discarded_error(error_message: str) -> bool:
    """
    Verifica se o erro é fatal (browsing context discarded, etc).
    
    Args:
        error_message: Mensagem de erro a verificar
        
    Returns:
        bool: True se é erro fatal, False caso contrário
    """
    if not error_message:
        return False
    error_str = str(error_message).lower()
    # Mensagens conhecidas que indicam que a sessão/driver foi encerrado
    fatal_signals = [
        'browsing context has been discarded',
        'no such window',
        'nosuchwindowerror',
        'session not created',
        'invalid session id',
        'tried to run command without establishing a connection',
        'tried to run command'  # fallback catch-all for this specific driver error
    ]

    return any(sig in error_str for sig in fatal_signals)

def validar_conexao_driver(driver, contexto: str = "GERAL", proc_id: Optional[str] = None):
    """
    Valida se a conexão com o driver Selenium ainda está ativa.
    
    Args:
        driver: WebDriver do Selenium
        contexto: Contexto da validação para logs
        proc_id: ID do processo (opcional)
        
    Returns:
        bool | str: True se conectado, False se erro recuperável, "FATAL" se irrecuperável
    """
    try:
        if not hasattr(driver, 'session_id') or driver.session_id is None:
            logger.error(f'[{contexto}][CONEXÃO][ERRO] Driver não possui session_id válido')
            raise DriverFatalError(f'Driver sem session_id válido (contexto: {contexto})')
        try:
            # Teste 1: Verificar se podemos acessar current_url
            try:
                current_url = driver.current_url
            except Exception as url_err:
                if is_browsing_context_discarded_error(url_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] Erro: {url_err}')
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                    if proc_id:
                        logger.error(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                    # Log em arquivo
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{url_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        logger.error(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                    raise DriverFatalError(f'Contexto do navegador descartado ao acessar URL (contexto: {contexto})')
                else:
                    logger.error(f'[{contexto}][CONEXÃO][ERRO] Falha ao acessar URL atual: {url_err}')
                    raise NavegacaoError(f'Falha ao acessar URL atual (contexto: {contexto}): {url_err}')
            # Teste 2: Verificar se podemos acessar window_handles
            try:
                window_handles = driver.window_handles
            except Exception as handles_err:
                if is_browsing_context_discarded_error(handles_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] Erro: {handles_err}')
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                    if proc_id:
                        logger.error(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{handles_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        logger.error(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                    raise DriverFatalError(f'Contexto do navegador descartado ao acessar handles (contexto: {contexto})')
                else:
                    logger.error(f'[{contexto}][CONEXÃO][ERRO] Falha ao acessar handles: {handles_err}')
                    raise NavegacaoError(f'Falha ao acessar handles (contexto: {contexto}): {handles_err}')
            # Se ambos os testes passaram, o driver está OK
            # Log reduzido - apenas em debug
            if contexto and 'DEBUG' in contexto.upper():
                pass
            return True
        except Exception as connection_test_err:
            if is_browsing_context_discarded_error(connection_test_err):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.error(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                logger.error(f'[{contexto}][CONEXÃO][FATAL] Erro: {connection_test_err}')
                logger.error(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                if proc_id:
                    logger.error(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                try:
                    with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{connection_test_err}\n{traceback.format_exc()}\n\n")
                except Exception as logerr:
                    logger.error(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                raise DriverFatalError(f'Contexto do navegador descartado no teste de conexão (contexto: {contexto})')
            else:
                logger.error(f'[{contexto}][CONEXÃO][ERRO] Falha no teste de conexão: {connection_test_err}')
                raise NavegacaoError(f'Falha no teste de conexão (contexto: {contexto}): {connection_test_err}')
    except Exception as validation_err:
        if is_browsing_context_discarded_error(validation_err):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
            logger.error(f'[{contexto}][CONEXÃO][FATAL] Erro: {validation_err}')
            logger.error(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
            if proc_id:
                logger.error(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
            try:
                with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{validation_err}\n{traceback.format_exc()}\n\n")
            except Exception as logerr:
                logger.error(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
            raise DriverFatalError(f'Contexto do navegador descartado na validação final (contexto: {contexto})')
        else:
            logger.error(f'[{contexto}][CONEXÃO][ERRO] Falha na validação de conexão: {validation_err}')
            raise NavegacaoError(f'Falha na validação de conexão (contexto: {contexto}): {validation_err}')

def aguardar_nova_aba(driver, aba_original: str, timeout: int = 15) -> Optional[str]:
    """
    Aguarda uma nova aba abrir e troca para ela.

    Substitui: WebDriverWait(driver, N).until(lambda d: len(d.window_handles) > 1)
    seguido de driver.switch_to.window.

    Returns:
        str: handle da nova aba
    Raises:
        NavegacaoError: se timeout esgotar sem nova aba
    """
    import time as _time
    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        handles = driver.window_handles
        novas = [h for h in handles if h != aba_original]
        if novas:
            return trocar_para_nova_aba(driver, aba_original)
        _time.sleep(0.3)
    raise NavegacaoError(f'Nenhuma nova aba abriu em {timeout}s')


def trocar_para_nova_aba(driver, aba_lista_original: str) -> Optional[str]:
    """
    Troca para uma nova aba diferente da aba original da lista.
    Inclui tratamento robusto de erros e verificações adicionais.
    
    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista
        
    Returns:
        str: O handle da nova aba se foi bem-sucedido, None caso contrário
    """
    try:
        # Verificar se o driver está conectado
        validar_conexao_driver(driver, "ABAS")
            
        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                logger.error('[ABAS][ERRO] Nenhuma aba disponível')
                raise NavegacaoError('Nenhuma aba disponível')
            if len(abas) == 1 and abas[0] == aba_lista_original:
                logger.error('[ABAS][ERRO] Apenas a aba original está disponível, nenhuma nova aba foi aberta')
                raise NavegacaoError('Apenas a aba original está disponível, nenhuma nova aba foi aberta')
            # Mostrar informação útil das abas ao invés de IDs longos
            if len(abas) > 1:
                try:
                    aba_atual = driver.current_window_handle
                    outras_abas = [h for h in abas if h != aba_lista_original]
                    pass
                except Exception:
                    pass
        except Exception as e:
            logger.error(f'[ABAS][ERRO] Falha ao obter lista de abas: {e}')
            raise NavegacaoError(f'Falha ao obter lista de abas: {e}')
            
        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        try:
                            url_atual = driver.current_url
                            from urllib.parse import urlparse
                            parsed = urlparse(url_atual)
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                            else:
                                url_legivel = parsed.path or url_atual[-30:]
                        except Exception:
                            pass
                        return h
                    else:
                        logger.warning(f'[ABAS][ALERTA] Falha na troca de aba')
                except Exception as e:
                    logger.error(f'[ABAS][ERRO] Erro ao trocar para aba {h[:8]}...: {e}')
                    continue
        logger.error('[ABAS][ERRO] Não foi possível trocar para nenhuma nova aba')
        raise NavegacaoError('Não foi possível trocar para nenhuma nova aba')
    except Exception as e:
        logger.error(f'[ABAS][ERRO] Erro geral ao tentar trocar de aba: {e}')
        raise NavegacaoError(f'Erro geral ao tentar trocar de aba: {e}')

def forcar_fechamento_abas_extras(driver, aba_lista_original: str):
    """
    Fecha todas as abas extras, com tratamento robusto de erros e reconexão.
    
    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista
        
    Returns:
        bool | str: True se sucesso, False se erro recuperável, "FATAL" se irrecuperável
    """
    try:
        # Verifica se o driver ainda está conectado
        conexao_status = validar_conexao_driver(driver, "LIMPEZA")
        if conexao_status == "FATAL":
            logger.error('[LIMPEZA][FATAL] Contexto do navegador foi descartado - não é possível limpar abas')
            return "FATAL"
        elif not conexao_status:
            logger.error('[LIMPEZA][ERRO] Conexão perdida - não é possível limpar abas')
            return False
            
        # Etapa 1: Obter lista de abas de forma segura
        try:
            abas_atuais = driver.window_handles
            pass
            pass
            pass
            
            # Listar todas as abas ANTES da limpeza para diagnóstico
            if len(abas_atuais) > 1:
                pass
                for idx, aba in enumerate(abas_atuais, 1):
                    try:
                        driver.switch_to.window(aba)
                        url = driver.current_url[:50] if driver.current_url else "URL não disponível"
                        titulo = driver.title[:30] if driver.title else "Sem título"
                        marcador = " ← MANTER (aba da lista)" if aba == aba_lista_original else " ← FECHAR"
                        pass
                    except Exception as e:
                        logger.error(f'[LIMPEZA]   {idx}. {aba[:12]}... | Erro: {str(e)[:30]}')
        except Exception as e:
            logger.error(f'[LIMPEZA][ERRO] Falha ao obter lista de abas: {e}')
            return False
            
        # Verifica se a aba original ainda existe
        if aba_lista_original not in abas_atuais:
            logger.error('[LIMPEZA][ERRO] Aba original não encontrada entre as abas disponíveis!')
            if len(abas_atuais) > 0:
                pass
                driver.switch_to.window(abas_atuais[0])
                return True
            else:
                return False
            
        # Etapa 2: Fechar abas extras com tratamento de exceções
        abas_extras = [aba for aba in abas_atuais if aba != aba_lista_original]
        
        if abas_extras:
            pass
            
            for idx, aba in enumerate(abas_extras, 1):
                fechou_aba = False
                for tentativa in range(3):
                    try:
                        # Tentar trocar para a aba antes de fechar
                        driver.switch_to.window(aba)
                        
                        # Obter URL da aba para logging
                        try:
                            url_aba = driver.current_url[:60]
                        except:
                            url_aba = "URL não disponível"
                        
                        driver.close()
                        pass
                        fechou_aba = True
                        break
                    except Exception as e:
                        if tentativa == 2:
                            logger.error(f'[LIMPEZA][ERRO]  Não foi possível fechar aba {idx} após 3 tentativas')
                
                # Pequena pausa entre fechamentos para estabilidade
                if fechou_aba:
                    time.sleep(0.1)
            
            # SEGUNDO PASSE: Se ainda houver abas extras, tentar fechar novamente
            try:
                abas_atualizadas = driver.window_handles
                abas_ainda_extras = [aba for aba in abas_atualizadas if aba != aba_lista_original]
                
                if abas_ainda_extras:
                    for idx, aba in enumerate(abas_ainda_extras, 1):
                        try:
                            driver.switch_to.window(aba)
                            driver.close()
                            pass
                        except Exception as e:
                            logger.error(f'[LIMPEZA][SEGUNDO PASSE][ERRO] Falha ao fechar aba {idx}: {str(e)[:50]}')
            except Exception as e:
                logger.error(f'[LIMPEZA][SEGUNDO PASSE][ERRO] Erro no segundo passe: {e}')
        else:
            pass
        
        # Etapa 3: Verificar novamente as abas e voltar para a original
        try:
            abas_atuais = driver.window_handles
            pass
            
            # Se ainda houver abas extras, listar para diagnóstico
            if len(abas_atuais) > 1:
                logger.warning(f'[LIMPEZA][ALERTA] Ainda existem {len(abas_atuais)-1} abas extras abertas!')
                for idx, aba in enumerate(abas_atuais):
                    try:
                        driver.switch_to.window(aba)
                        url = driver.current_url[:60]
                        titulo = driver.title[:40] if driver.title else "Sem título"
                        marcador = " ← ABA DA LISTA" if aba == aba_lista_original else ""
                        pass
                    except Exception as e:
                        logger.error(f'[LIMPEZA]   Aba {idx+1}: {aba[:12]}... | Erro ao ler: {str(e)[:40]}')
        except Exception as e:
            logger.error(f'[LIMPEZA][ERRO] Falha ao verificar abas após limpeza: {e}')
            return False
            
        if aba_lista_original in abas_atuais:
            try:
                driver.switch_to.window(aba_lista_original)
                pass
                
                # Verificação final de sucesso
                if len(abas_atuais) == 1:
                    pass
                    return True
                else:
                    logger.warning(f'[LIMPEZA][WARN] Limpeza parcial: {len(abas_atuais)} abas ainda abertas')
                    return True  # Retorna True mesmo assim para não travar o fluxo
            except Exception as e:
                logger.error(f'[LIMPEZA][ERRO] Não foi possível voltar para aba original: {e}')
                return False
        else:
            logger.error('[LIMPEZA][ERRO] Aba da lista original não está mais disponível!')
            return False
    except Exception as e:
        logger.error(f'[LIMPEZA][ERRO] Erro geral na limpeza de abas: {e}')
        return False

__all__ = [
    'validar_conexao_driver',
    'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error'
]
