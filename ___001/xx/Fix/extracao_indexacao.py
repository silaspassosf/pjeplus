import re
import time
from typing import Optional
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from Fix.log import logger
from .abas import validar_conexao_driver, forcar_fechamento_abas_extras

try:
    from atos.core import verificar_carregamento_detalhe
    _ATOS_CORE_AVAILABLE = True
except ImportError:
    _ATOS_CORE_AVAILABLE = False

try:
    from PEC.core import reiniciar_driver_e_logar_pje
except Exception:
    reiniciar_driver_e_logar_pje = None


def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                logger.error('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            logger.error('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            logger.error('[ERRO] Painel de opções não apareceu.')
            return False
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            logger.error(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            time.sleep(1)
        except Exception as e:
            logger.error(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        # Generalização da seleção de tarefa
        if tarefas_alvo:
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(By.XPATH, f"//span[contains(text(), '{seletor_tarefa}')]")
            except Exception:
                try:
                    seletor = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                        if seletor_tarefa in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    logger.error(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                    return False
            if not tarefa_element:
                logger.error(f'[ERRO] Não encontrou o seletor de tarefa: {seletor_tarefa}.')
                return False
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            painel = None
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            if not painel or not painel.is_displayed():
                logger.error('[ERRO] Painel de opções de tarefa não apareceu.')
                return False
            tarefas_clicadas = set()
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if tarefa.lower() in texto and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            if len(tarefas_clicadas) == 0:
                logger.error(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                time.sleep(1)
            except Exception as e:
                logger.error(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
    except Exception as e:
        logger.error(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    return True


def indexar_processos(driver):
    """
    Indexa processos de forma mais robusta, evitando problemas de stale elements
    """
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []
    
    # Buscar elementos frescos a cada iteração para evitar stale elements
    def obter_linhas_frescas():
        return driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
    
    linhas = obter_linhas_frescas()
    print(f'[INDEXAR] Encontradas {len(linhas)} linhas para processar')
    
    for idx in range(len(linhas)):
        try:
            # Sempre obter elementos frescos para evitar stale references
            linhas_atuais = obter_linhas_frescas()
            
            # Verificar se o índice ainda é válido
            if idx >= len(linhas_atuais):
                # print(f'[INDEXAR][SKIP] Linha {idx+1}: DOM mudou, menos linhas disponíveis')
                continue
                
            linha = linhas_atuais[idx]
            
            # Extrair texto do processo
            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''
            
            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                if tds:
                    texto = tds[0].text.strip()
            
            # Buscar número do processo
            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem número]'
            
            processos.append((num_proc, linha))
            
        except Exception as e:
            print(f'[INDEXAR][ERRO] Linha {idx+1}: {e} (elemento pode ter ficado stale)')
            # Não tentar reindexar - apenas continuar
            continue
    
    print(f'[INDEXAR] Processamento concluído: {len(processos)} processos indexados')
    return processos


def reindexar_linha(driver, proc_id):
    """
    Reindexar linha quando elemento fica stale.
    Agora com verificação de acesso negado e melhor tratamento de erros.
    NÃO navega automaticamente - respeita a página atual do módulo.
    """
    try:
        # Verificar se ainda estamos em uma página válida do PJE
        url_atual = driver.current_url
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                logger.error(f'ACESSO NEGADO detectado na URL: {url_atual}')
                return None
        
        # Verificar se é uma URL válida do PJE
        if 'pje.trt2.jus.br' not in url_atual:
            logger.error(f'URL não é do PJE: {url_atual}')
            return None
        
        # REMOVIDO: Navegação automática para atividades
        # Cada módulo deve gerenciar sua própria navegação
        print(f'[REINDEXAR] Tentando reindexar na página atual: {url_atual}')
        
        # Buscar linhas na página atual (diferentes seletores dependendo do módulo)
        possible_selectors = [
            'tr.cdk-drag',           # Atividades (PEC)
            'tr',                    # Documentos internos (M1) 
            'tbody tr',              # Outras tabelas
            '.linha-processo',       # Seletor alternativo
        ]
        
        linhas_atuais = []
        for selector in possible_selectors:
            try:
                linhas_temp = driver.find_elements(By.CSS_SELECTOR, selector)
                if linhas_temp:
                    linhas_atuais = linhas_temp
                    print(f'[REINDEXAR] Usando seletor {selector}: {len(linhas_atuais)} linhas encontradas')
                    break
            except:
                continue
        
        if not linhas_atuais:
            logger.error(f'Nenhuma linha encontrada na página com os seletores testados')
            return None
        
        print(f'[REINDEXAR] Buscando {proc_id} entre {len(linhas_atuais)} linhas...')
        for idx, linha_temp in enumerate(linhas_atuais):
            try:
                # Verificar se a linha ainda é válida
                if not linha_temp.is_displayed():
                    continue
                    
                # Buscar número do processo na linha (diferentes estratégias)
                texto_linha = ""
                
                # Estratégia 1: Links
                links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    texto_linha = links[0].text.strip()
                else:
                    # Estratégia 2: Células td
                    tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                    if tds:
                        # Procurar em várias células (processo pode estar em diferentes colunas)
                        for td in tds[:3]:  # Verificar as 3 primeiras colunas
                            td_text = td.text.strip()
                            if proc_id in td_text:
                                texto_linha = td_text
                                break
                        if not texto_linha:
                            texto_linha = tds[0].text.strip()
                    else:
                        # Estratégia 3: Texto geral da linha
                        texto_linha = linha_temp.text.strip()
                
                if proc_id in texto_linha:
                    return linha_temp
                    
            except Exception as e:
                # Não logar erros individuais para não poluir - linha pode estar stale mesmo
                continue
        
        logger.error(f'Processo {proc_id} não encontrado nas {len(linhas_atuais)} linhas da página atual')
        return None
        
    except Exception as e:
        logger.error(f'Erro geral na reindexação: {e}')
        return None


def abrir_detalhes_processo(driver, linha):
    try:
        btn = linha.find_element(By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]')
    except Exception:
        try:
            btn = linha.find_element(By.CSS_SELECTOR, 'button, a')
        except Exception:
            return False
    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    return True


def trocar_para_nova_aba(driver, aba_lista_original):
    """
    Troca para uma nova aba diferente da aba original da lista.
    Inclui tratamento robusto de erros, verificações adicionais e verificação de carregamento.
    
    Args:
        driver: O driver Selenium
        aba_lista_original: O handle da aba original da lista
        
    Returns:
        str: O handle da nova aba se foi bem-sucedido, None caso contrário
    """
    try:
        # Verificar se o driver está conectado
        if not validar_conexao_driver(driver, "ABAS"):
            logger.error('[ABAS][ERRO] Driver não está conectado ao tentar trocar de aba')
            return None
            
        # Obter lista atual de abas
        try:
            abas = driver.window_handles
            if not abas:
                logger.error('[ABAS][ERRO] Nenhuma aba disponível')
                return None
                
            if len(abas) == 1 and abas[0] == aba_lista_original:
                logger.error('[ABAS][ERRO] Apenas a aba original está disponível, nenhuma nova aba foi aberta')
                return None
                
            # Log melhorado - mostrar apenas a quantidade, não os IDs longos
        except Exception as e:
            logger.error(f'[ABAS][ERRO] Falha ao obter lista de abas: {e}')
            return None
            
        # Tentar trocar para uma aba diferente da original
        for h in abas:
            if h != aba_lista_original:
                try:
                    driver.switch_to.window(h)
                    # Verificar se realmente trocamos de aba
                    atual_handle = driver.current_window_handle
                    if atual_handle == h:
                        # Log com URL útil em vez de ID longo
                        try:
                            url_atual = driver.current_url
                            parsed = urlparse(url_atual)
                            path_parts = parsed.path.strip('/').split('/')
                            if len(path_parts) >= 2:
                                url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                            else:
                                url_legivel = parsed.path or url_atual[-30:]
                        except Exception:
                            url_legivel = None
                        # VERIFICAÇÃO DE CARREGAMENTO: Se for página /detalhe, verificar se carregou
                        try:
                            current_url = driver.current_url or ''
                            if '/detalhe' in current_url.lower() and _ATOS_CORE_AVAILABLE:
                                if not verificar_carregamento_detalhe(driver, timeout_inicial=2.0, max_tentativas=3, log=True):
                                    logger.warning('[ABAS][ALERTA] Falha no carregamento da página /detalhe, mas continuando...')
                        except Exception as e:
                            logger.error(f'[ABAS][ALERTA] Erro na verificação de carregamento: {e}')
                        
                        return h
                    else:
                        logger.warning(f'[ABAS][ALERTA] Troca para aba {h} falhou, handle atual é: {atual_handle}')
                except Exception as e:
                    logger.error(f'[ABAS][ERRO] Erro ao trocar para aba {h}: {e}')
                    continue
                    
        # Se chegou aqui, não conseguiu trocar para nenhuma nova aba
        logger.error('[ABAS][ERRO] Não foi possível trocar para nenhuma nova aba')
        return None
    except Exception as e:
        logger.error(f'[ABAS][ERRO] Erro geral ao tentar trocar de aba: {e}')
        return None


def _indexar_preparar_contexto(driver, max_processos=None):
    """Valida conexão e indexa processos, retornando (aba_original, lista_processos) ou (None, None)."""
    import time
    
    conexao_inicial = validar_conexao_driver(driver, "FLUXO")
    if conexao_inicial == "FATAL":
        print('[FLUXO][FATAL] Driver inutilizável no início do processamento!')
        return None, None
    elif not conexao_inicial:
        print('[FLUXO][ERRO] Driver não está conectado no início do processamento!')
        return None, None
    
    try:
        aba_lista_original = driver.current_window_handle
        print(f'[FLUXO] Aba da lista capturada: {aba_lista_original}')
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao capturar aba da lista: {e}')
        return None, None
    
    try:
        processos = indexar_processos(driver)
        if not processos:
            print('[FLUXO][ALERTA] Nenhum processo encontrado para indexação')
            return None, None
    except Exception as e:
        print(f'[FLUXO][ERRO] Falha ao indexar processos: {e}')
        return None, None
    
    if max_processos and max_processos > 0 and max_processos < len(processos):
        processos = processos[:max_processos]
        print(f'[FLUXO] Limitando processamento a {max_processos} processos')
    
    return aba_lista_original, processos


def _indexar_tentar_reindexar(driver: WebDriver, proc_id: str, max_tentativas: int = 3) -> Optional[WebElement]:
    """
    Tenta reindexar linha com múltiplas tentativas.
    
    Args:
        driver: Instância do WebDriver Selenium
        proc_id: ID do processo a reindexar
        max_tentativas: Número máximo de tentativas (padrão 3)
    
    Returns:
        WebElement da linha reindexada ou None se falhar
    """
    import time
    for tent in range(max_tentativas):
        try:
            linha = reindexar_linha(driver, proc_id)
            if linha:
                return linha
            print(f'[PROCESSAR] Tentativa {tent+1}/{max_tentativas} - Reindexando')
            time.sleep(1)
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha na tentativa {tent+1}: {e}')
            time.sleep(1)
    return None


def _indexar_tentar_trocar_aba(driver: WebDriver, aba_original: str, max_tentativas: int = 3) -> Optional[str]:
    """
    Tenta trocar para nova aba com múltiplas tentativas.
    
    Args:
        driver: Instância do WebDriver Selenium
        aba_original: Handle da aba original
        max_tentativas: Número máximo de tentativas (padrão 3)
    
    Returns:
        Handle da nova aba ou None se falhar
    """
    import time
    for tent in range(max_tentativas):
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_original)
            if nova_aba:
                # Log melhorado - mostrar URL em vez de ID
                try:
                    url_atual = driver.current_url
                    parsed = urlparse(url_atual)
                    path_parts = parsed.path.strip('/').split('/')
                    if len(path_parts) >= 2:
                        url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                    else:
                        url_legivel = parsed.path or url_atual[-30:]
                    print(f'[PROCESSAR] Trocado para nova aba: {url_legivel}')
                except:
                    print(f'[PROCESSAR] Trocado para nova aba')
                time.sleep(0.5)
                return nova_aba
        except Exception as e:
            print(f'[PROCESSAR][ERRO] Falha ao trocar aba (tent {tent+1}): {e}')
            time.sleep(1)
    return None

