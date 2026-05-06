"""
Fix.abas - Módulo de gerenciamento de abas para PJe automação.

Funções para trocar de abas, validar conexão do driver e gerenciar abas extras.
Migrado de ORIGINAIS/Fix.py para modularização (PARTE 6).
"""

import time
import traceback
import datetime
from typing import Optional

from selenium.common.exceptions import TimeoutException


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
    return ('browsing context has been discarded' in error_str or 
            'no such window' in error_str or 
            'nosuchwindowerror' in error_str or
            'session not created' in error_str or
            'invalid session id' in error_str)


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
            print(f'[{contexto}][CONEXÃO][ERRO] Driver não possui session_id válido')
            return False
        try:
            # Teste 1: Verificar se podemos acessar current_url
            try:
                current_url = driver.current_url
            except Exception as url_err:
                if is_browsing_context_discarded_error(url_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                    print(f'[{contexto}][CONEXÃO][FATAL] Erro: {url_err}')
                    print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                    if proc_id:
                        print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                    # Log em arquivo
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{url_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                    return "FATAL"
                else:
                    print(f'[{contexto}][CONEXÃO][ERRO] Falha ao acessar URL atual: {url_err}')
                    return False
            # Teste 2: Verificar se podemos acessar window_handles
            try:
                window_handles = driver.window_handles
            except Exception as handles_err:
                if is_browsing_context_discarded_error(handles_err):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                    print(f'[{contexto}][CONEXÃO][FATAL] Erro: {handles_err}')
                    print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                    if proc_id:
                        print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                    try:
                        with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{handles_err}\n{traceback.format_exc()}\n\n")
                    except Exception as logerr:
                        print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                    return "FATAL"
                else:
                    print(f'[{contexto}][CONEXÃO][ERRO] Falha ao acessar handles: {handles_err}')
                    return False
            # Se ambos os testes passaram, o driver está OK
            # Log reduzido - apenas em debug
            if contexto and 'DEBUG' in contexto.upper():
                print(f'[{contexto}][CONEXÃO][OK] Driver conectado - URL: {current_url[:50]}... | Abas: {len(window_handles)}')
            return True
        except Exception as connection_test_err:
            if is_browsing_context_discarded_error(connection_test_err):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
                print(f'[{contexto}][CONEXÃO][FATAL] Erro: {connection_test_err}')
                print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
                if proc_id:
                    print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
                try:
                    with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{connection_test_err}\n{traceback.format_exc()}\n\n")
                except Exception as logerr:
                    print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
                return "FATAL"
            else:
                print(f'[{contexto}][CONEXÃO][ERRO] Falha no teste de conexão: {connection_test_err}')
                return False
    except Exception as validation_err:
        if is_browsing_context_discarded_error(validation_err):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f'[{contexto}][CONEXÃO][FATAL] [{timestamp}] Contexto do navegador foi descartado - driver inutilizável')
            print(f'[{contexto}][CONEXÃO][FATAL] Erro: {validation_err}')
            print(f'[{contexto}][CONEXÃO][FATAL] Stacktrace:\n{traceback.format_exc()}')
            if proc_id:
                print(f'[{contexto}][CONEXÃO][FATAL] Processo afetado: {proc_id}')
            try:
                with open("erro_fatal_selenium.log", "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{contexto}] Processo: {proc_id}\n{validation_err}\n{traceback.format_exc()}\n\n")
            except Exception as logerr:
                print(f'[LOG][ERRO] Falha ao registrar erro fatal em arquivo: {logerr}')
            return "FATAL"
        else:
            print(f'[{contexto}][CONEXÃO][ERRO] Falha na validação de conexão: {validation_err}')
            return False


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
        if not validar_conexao_driver(driver, "ABAS"):
            print('[ABAS][ERRO] Driver não está conectado ao tentar trocar de aba')
            return None
            
        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                print('[ABAS][ERRO] Nenhuma aba disponível')
                return None
                
            if len(abas) == 1 and abas[0] == aba_lista_original:
                print('[ABAS][ERRO] Apenas a aba original está disponível, nenhuma nova aba foi aberta')
                return None
                
            # Mostrar informação útil das abas ao invés de IDs longos
            if len(abas) > 1:
                try:
                    aba_atual = driver.current_window_handle
                    outras_abas = [h for h in abas if h != aba_lista_original]
                    print(f'[ABAS] {len(abas)} abas detectadas - {len(outras_abas)} nova(s) disponível(is)')
                except:
                    print(f'[ABAS] {len(abas)} abas detectadas')
        except Exception as e:
            print(f'[ABAS][ERRO] Falha ao obter lista de abas: {e}')
            return None
            
        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    # Verificar se realmente trocamos de aba
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        # Log simplificado com URL útil
                        try:
                            url_atual = driver.current_url
                            # Extrair parte útil da URL
                            from urllib.parse import urlparse
                            parsed = urlparse(url_atual)
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                            else:
                                url_legivel = parsed.path or url_atual[-30:]
                            print(f'[ABAS] ✅ Nova aba aberta: {url_legivel}')
                        except:
                            print(f'[ABAS] ✅ Nova aba aberta')
                        return h
                    else:
                        print(f'[ABAS][ALERTA] Falha na troca de aba')
                except Exception as e:
                    print(f'[ABAS][ERRO] Erro ao trocar para aba {h[:8]}...: {e}')
                    continue
                    
        # Se chegou aqui, não conseguiu trocar para nenhuma nova aba
        print('[ABAS][ERRO] Não foi possível trocar para nenhuma nova aba')
        return None
    except Exception as e:
        print(f'[ABAS][ERRO] Erro geral ao tentar trocar de aba: {e}')
        return None


def aguardar_nova_aba(driver, aba_lista_original: str, timeout: float = 10) -> str:
    """Compatibilidade para aguardar o handle de uma nova aba."""
    limite = time.time() + float(timeout)
    while time.time() < limite:
        try:
            for handle in driver.window_handles:
                if handle != aba_lista_original:
                    return handle
        except Exception:
            break
        time.sleep(0.2)

    raise TimeoutException('Nenhuma nova aba detectada dentro do timeout')


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
            print('[LIMPEZA][FATAL] Contexto do navegador foi descartado - não é possível limpar abas')
            return "FATAL"
        elif not conexao_status:
            print('[LIMPEZA][ERRO] Conexão perdida - não é possível limpar abas')
            return False
            
        # Etapa 1: Obter lista de abas de forma segura
        try:
            abas_atuais = driver.window_handles
            print(f'[LIMPEZA] ========== INÍCIO DA LIMPEZA DE ABAS ==========')
            print(f'[LIMPEZA] Total de abas abertas: {len(abas_atuais)}')
            print(f'[LIMPEZA] Aba da lista (manter): {aba_lista_original[:12]}...')
            
            # Listar todas as abas ANTES da limpeza para diagnóstico
            if len(abas_atuais) > 1:
                print(f'[LIMPEZA] Listando {len(abas_atuais)} abas ANTES da limpeza:')
                for idx, aba in enumerate(abas_atuais, 1):
                    try:
                        driver.switch_to.window(aba)
                        url = driver.current_url[:50] if driver.current_url else "URL não disponível"
                        titulo = driver.title[:30] if driver.title else "Sem título"
                        marcador = " ← MANTER (aba da lista)" if aba == aba_lista_original else " ← FECHAR"
                        print(f'[LIMPEZA]   {idx}. {aba[:12]}... | {titulo} | {url}{marcador}')
                    except Exception as e:
                        print(f'[LIMPEZA]   {idx}. {aba[:12]}... | Erro: {str(e)[:30]}')
        except Exception as e:
            print(f'[LIMPEZA][ERRO] Falha ao obter lista de abas: {e}')
            return False
            
        # Verifica se a aba original ainda existe
        if aba_lista_original not in abas_atuais:
            print('[LIMPEZA][ERRO] Aba original não encontrada entre as abas disponíveis!')
            if len(abas_atuais) > 0:
                print('[LIMPEZA][RECUPERAÇÃO] Usando primeira aba disponível como nova aba principal')
                driver.switch_to.window(abas_atuais[0])
                return True
            else:
                return False
            
        # Etapa 2: Fechar abas extras com tratamento de exceções
        abas_extras = [aba for aba in abas_atuais if aba != aba_lista_original]
        
        if abas_extras:
            print(f'[LIMPEZA] Encontradas {len(abas_extras)} abas extras para fechar')
            
            for idx, aba in enumerate(abas_extras, 1):
                fechou_aba = False
                for tentativa in range(3):
                    try:
                        # Tentar trocar para a aba antes de fechar
                        driver.switch_to.window(aba)
                        time.sleep(0.1)  # Pequena pausa para garantir switch
                        
                        # Obter URL da aba para logging
                        try:
                            url_aba = driver.current_url[:60]
                        except:
                            url_aba = "URL não disponível"
                        
                        driver.close()
                        print(f'[LIMPEZA] ✓ Aba {idx}/{len(abas_extras)} fechada: {aba[:12]}... | URL: {url_aba}')
                        fechou_aba = True
                        break
                    except Exception as e:
                        print(f'[LIMPEZA][WARN] Tentativa {tentativa+1}/3 - Erro ao fechar aba {idx}: {str(e)[:80]}')
                        time.sleep(0.2)
                        if tentativa == 2:
                            print(f'[LIMPEZA][ERRO] ✗ Não foi possível fechar aba {idx} após 3 tentativas')
                
                # Pequena pausa entre fechamentos para estabilidade
                if fechou_aba:
                    time.sleep(0.1)
            
            # SEGUNDO PASSE: Se ainda houver abas extras, tentar fechar novamente
            try:
                time.sleep(0.3)
                abas_atualizadas = driver.window_handles
                abas_ainda_extras = [aba for aba in abas_atualizadas if aba != aba_lista_original]
                
                if abas_ainda_extras:
                    print(f'[LIMPEZA][SEGUNDO PASSE] Ainda restam {len(abas_ainda_extras)} abas extras - tentando fechar novamente')
                    for idx, aba in enumerate(abas_ainda_extras, 1):
                        try:
                            driver.switch_to.window(aba)
                            time.sleep(0.1)
                            driver.close()
                            print(f'[LIMPEZA][SEGUNDO PASSE] ✓ Aba {idx} fechada (segundo passe)')
                            time.sleep(0.1)
                        except Exception as e:
                            print(f'[LIMPEZA][SEGUNDO PASSE][ERRO] Falha ao fechar aba {idx}: {str(e)[:50]}')
            except Exception as e:
                print(f'[LIMPEZA][SEGUNDO PASSE][ERRO] Erro no segundo passe: {e}')
        else:
            print('[LIMPEZA] Nenhuma aba extra detectada para fechar')
        
        # Etapa 3: Verificar novamente as abas e voltar para a original
        try:
            abas_atuais = driver.window_handles
            print(f'[LIMPEZA] Abas restantes após limpeza: {len(abas_atuais)}')
            
            # Se ainda houver abas extras, listar para diagnóstico
            if len(abas_atuais) > 1:
                print(f'[LIMPEZA][ALERTA] Ainda existem {len(abas_atuais)-1} abas extras abertas!')
                for idx, aba in enumerate(abas_atuais):
                    try:
                        driver.switch_to.window(aba)
                        url = driver.current_url[:60]
                        titulo = driver.title[:40] if driver.title else "Sem título"
                        marcador = " ← ABA DA LISTA" if aba == aba_lista_original else ""
                        print(f'[LIMPEZA]   Aba {idx+1}: {aba[:12]}... | {titulo} | {url}{marcador}')
                    except Exception as e:
                        print(f'[LIMPEZA]   Aba {idx+1}: {aba[:12]}... | Erro ao ler: {str(e)[:40]}')
        except Exception as e:
            print(f'[LIMPEZA][ERRO] Falha ao verificar abas após limpeza: {e}')
            return False
            
        if aba_lista_original in abas_atuais:
            try:
                driver.switch_to.window(aba_lista_original)
                print('[LIMPEZA] ✓ Retornou para aba da lista')
                
                # Verificação final de sucesso
                if len(abas_atuais) == 1:
                    print('[LIMPEZA] ✓✓ Limpeza completa: apenas 1 aba restante (aba da lista)')
                    return True
                else:
                    print(f'[LIMPEZA][WARN] Limpeza parcial: {len(abas_atuais)} abas ainda abertas')
                    return True  # Retorna True mesmo assim para não travar o fluxo
            except Exception as e:
                print(f'[LIMPEZA][ERRO] Não foi possível voltar para aba original: {e}')
                return False
        else:
            print('[LIMPEZA][ERRO] Aba da lista original não está mais disponível!')
            return False
    except Exception as e:
        print(f'[LIMPEZA][ERRO] Erro geral na limpeza de abas: {e}')
        return False


__all__ = [
    'validar_conexao_driver',
    'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error'
]
