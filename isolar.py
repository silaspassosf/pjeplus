from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re

def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    # Indexa e já processa cada processo sequencialmente, sem delay e sem logs intermediários desnecessários.
    print('[FLUXO] Iniciando indexação da lista de processos...', flush=True)
    # Armazena a referência da aba da lista ANTES de qualquer operação
    aba_lista_original = driver.current_window_handle
    print(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')

    # Indexa e obtém as linhas/processos
    linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    print(f'[INDEXAR] Total de processos encontrados: {len(linhas)}')
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []
    for idx, linha in enumerate(linhas):
        try:
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                texto = tds[0].text.strip() if tds else ''
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            processos.append((num_proc, linha))
            print(f'[INDEXAR] {idx+1:02d}: {num_proc}')
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e}')

    print(f'[FLUXO] Indexação concluída. Iniciando processamento da lista de processos...', flush=True)

    def validar_conexao_driver(driver, contexto="GERAL"):
        try:
            if not hasattr(driver, 'session_id') or driver.session_id is None:
                return False
            try:
                current_url = driver.current_url
                window_handles = driver.window_handles
                return True
            except Exception:
                return False
        except Exception:
            return False

    def forcar_fechamento_abas_extras():
        try:
            if not validar_conexao_driver(driver, "LIMPEZA"):
                return False
            abas_atuais = driver.window_handles
            for aba in abas_atuais:
                if aba != aba_lista_original:
                    try:
                        if not validar_conexao_driver(driver, "LIMPEZA_ABA"):
                            return False
                        driver.switch_to.window(aba)
                        driver.close()
                    except Exception:
                        pass
            if aba_lista_original in driver.window_handles:
                if not validar_conexao_driver(driver, "LIMPEZA_RETORNO"):
                    return False
                driver.switch_to.window(aba_lista_original)
                return True
            else:
                return False
        except Exception:
            return False

    processos_processados = 0
    processos_com_erro = 0

    for idx, (proc_id, linha) in enumerate(processos):
        try:
            print(f'[PROCESSO] {idx+1}/{len(processos)}: {proc_id}')
            # Reindexar linha do processo
            linha_atual = None
            try:
                linhas_atuais = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
                for linha_temp in linhas_atuais:
                    try:
                        links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                        texto_linha = ''
                        if links:
                            texto_linha = links[0].text.strip()
                        else:
                            tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                            texto_linha = tds[0].text.strip() if tds else ''
                        if proc_id in texto_linha:
                            linha_atual = linha_temp
                            break
                    except Exception:
                        continue
                if not linha_atual:
                    print(f'[ERRO] Não foi possível reindexar a linha para {proc_id}')
                    processos_com_erro += 1
                    continue
            except Exception as e:
                print(f'[ERRO] Falha na reindexação para {proc_id}: {e}')
                processos_com_erro += 1
                continue
            # Buscar botão/link do processo
            btn = None
            try:
                btn = linha_atual.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
            except Exception:
                try:
                    btn = linha_atual.find_element(By.CSS_SELECTOR, 'button, a')
                except Exception:
                    pass
            if btn is not None:
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                driver.execute_script("arguments[0].click();", btn)
            else:
                print(f'[ERRO] Botão de detalhes não encontrado para {proc_id}')
                processos_com_erro += 1
                continue
            import time
            time.sleep(1)
            abas = driver.window_handles
            nova_aba = None
            for h in abas:
                if h != aba_lista_original:
                    nova_aba = h
                    break
            if not nova_aba:
                print(f'[ERRO] Nova aba do processo {proc_id} não foi aberta.')
                processos_com_erro += 1
                continue
            try:
                driver.switch_to.window(nova_aba)
            except Exception as e:
                print(f'[ERRO] Não foi possível trocar para nova aba do processo {proc_id}: {e}')
                processos_com_erro += 1
                continue
            # Executar callback
            try:
                if callback:
                    callback(driver)
                    processos_processados += 1
                else:
                    processos_processados += 1
            except Exception as e:
                print(f'[ERRO] Callback falhou para {proc_id}: {e}')
                processos_com_erro += 1
            # Retornar à aba da lista usando failsafe robusto
            if not failsafe_retorno_lista(driver, aba_lista_original, proc_id):
                print(f'[ERRO] Failsafe falhou ao retornar à lista para {proc_id}')
            print(f'[LIMPEZA] Processo {proc_id} concluído, retorno à lista')
        except Exception as e:
            print(f'[ERRO] Falha geral ao processar processo {proc_id}: {e}')
            processos_com_erro += 1
            try:
                failsafe_retorno_lista(driver, aba_lista_original, proc_id)
            except:
                pass
            continue
    print(f'[FLUXO] Processamento concluído!')
    print(f'[FLUXO] Processos processados com sucesso: {processos_processados}')
    print(f'[FLUXO] Processos com erro: {processos_com_erro}')
    print(f'[FLUXO] Total de processos: {len(processos)}')
    return processos_processados > 0  # Retorna True se pelo menos um processo foi processado

def failsafe_retorno_lista(driver, aba_lista_original, proc_id="UNKNOWN"):
        """
        Failsafe que sempre tenta retornar à aba da lista, mesmo em caso de erros críticos.
        Garante que o processamento possa continuar mesmo se houver falhas.
        """
        try:
            print(f'[FAILSAFE] Iniciando recuperação para processo {proc_id}...')
            
            # Estratégia 1: Verificar se a aba da lista ainda existe
            try:
                abas_disponiveis = driver.window_handles
                if aba_lista_original in abas_disponiveis:
                    driver.switch_to.window(aba_lista_original)
                    print(f'[FAILSAFE] Sucesso - retornado à aba da lista para {proc_id}')
                    return True
                else:
                    print(f'[FAILSAFE] ERRO - Aba da lista não existe mais para {proc_id}')
                    return False
            except Exception as e1:
                print(f'[FAILSAFE] Estratégia 1 falhou para {proc_id}: {e1}')
            
            # Estratégia 2: Fechar todas as abas extras e tentar usar a primeira aba
            try:
                abas_atuais = driver.window_handles
                print(f'[FAILSAFE] Tentando estratégia 2 - {len(abas_atuais)} abas encontradas')
                
                # Se há mais de uma aba, fecha todas exceto a primeira
                if len(abas_atuais) > 1:
                    primeira_aba = abas_atuais[0]  # Assume que a primeira é a lista
                    for aba in abas_atuais[1:]:
                        try:
                            driver.switch_to.window(aba)
                            driver.close()
                            print(f'[FAILSAFE] Aba extra fechada: {aba}')
                        except:
                            pass  # Ignora erros individuais
                    
                    # Vai para a primeira aba
                    driver.switch_to.window(primeira_aba)
                    print(f'[FAILSAFE] Sucesso estratégia 2 - usando primeira aba como lista para {proc_id}')
                    return True
                else:
                    # Se só há uma aba, usa ela
                    driver.switch_to.window(abas_atuais[0])
                    print(f'[FAILSAFE] Sucesso estratégia 2 - usando única aba disponível para {proc_id}')
                    return True
                    
            except Exception as e2:
                print(f'[FAILSAFE] Estratégia 2 falhou para {proc_id}: {e2}')
            
            # Estratégia 3: Última tentativa - recarregar página atual
            try:
                driver.refresh()
                print(f'[FAILSAFE] Estratégia 3 - página recarregada para {proc_id}')
                return True
            except Exception as e3:
                print(f'[FAILSAFE] Estratégia 3 falhou para {proc_id}: {e3}')
            
            print(f'[FAILSAFE] TODAS as estratégias falharam para {proc_id}')
            return False
            
        except Exception as failsafe_err:
            print(f'[FAILSAFE] Erro crítico no failsafe para {proc_id}: {failsafe_err}')
            return False